"""Live corner-approach tests. Run: python3 -m unittest tests.test_corner_approach

Pins the three properties LED state 2 is only trustworthy with:

  * the tail reads only what was appended, not the whole growing file
  * a distance sitting on a zone boundary cannot toggle the cue
  * one corner cannot produce repeated flashes

Time is injected everywhere, so hysteresis and rate limiting are exercised
without a multi-lap recording and without waiting 20 seconds per assertion.
"""

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src import bridge_client
from src.corner_approach import CornerApproachMonitor, LapDistanceTail

HEADER = (
    "timestamp,packet_id,session_time,frame_identifier,lap_distance,"
    "current_lap_num,car_position,speed,throttle,brake,steer,gear,engine_rpm"
)

# The two real calibrated Monza zones, restated so a config change cannot make
# these tests silently stop testing what they claim to.
ZONES = {
    "Turn 1": {"zone": (700.0, 950.0)},
    "Roggia": {"zone": (1650.0, 2200.0)},
}


class FakeClock:
    """Monotonic clock the test advances by hand."""

    def __init__(self, start: float = 1000.0):
        self.now = float(start)

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += float(seconds)


def lap_row(session_time: float, distance: float, lap: int = 1) -> str:
    return f"2026-01-01T00:00:00,2,{session_time},{int(session_time * 20)},{distance},{lap},1,,,,,,"


def telemetry_row(session_time: float) -> str:
    return (
        f"2026-01-01T00:00:00,6,{session_time},{int(session_time * 20)},"
        f",,,250,0.9,0.0,0.0,7,11000"
    )


class LapDistanceTailTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "2026-01-01_000000_session.csv"
        self.path.write_text(HEADER + "\n", encoding="utf-8")
        self.clock = FakeClock()
        self.tail = LapDistanceTail(max_age_s=3.0, clock=self.clock)

    def append(self, *lines: str) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write("".join(line + "\n" for line in lines))

    def test_returns_newest_lap_distance(self):
        self.append(lap_row(1.0, 700.0), telemetry_row(1.0), lap_row(1.05, 750.0))
        self.assertEqual(750.0, self.tail.latest_distance(self.path))

    def test_ignores_telemetry_rows_without_distance(self):
        self.append(lap_row(1.0, 812.5), telemetry_row(1.05), telemetry_row(1.1))
        self.assertEqual(812.5, self.tail.latest_distance(self.path))

    def test_only_appended_bytes_are_read(self):
        self.append(*[lap_row(i * 0.05, 100.0 + i) for i in range(400)])
        self.tail.latest_distance(self.path)
        after_first = self.tail.bytes_read
        self.assertGreater(after_first, 0)

        addition = lap_row(99.0, 1700.0)
        self.append(addition)
        self.assertEqual(1700.0, self.tail.latest_distance(self.path))

        # Only the one new row crossed the read boundary, not the file again.
        self.assertLessEqual(self.tail.bytes_read - after_first, len(addition) + 2)

    def test_distance_is_retained_between_flush_bursts(self):
        # session_logger.py flushes every 50 rows, so polls in between see no
        # new bytes. The cue must not drop out during that gap.
        self.append(lap_row(1.0, 800.0))
        self.assertEqual(800.0, self.tail.latest_distance(self.path))
        self.clock.advance(1.0)
        self.assertEqual(800.0, self.tail.latest_distance(self.path))

    def test_distance_expires_once_older_than_max_age(self):
        self.append(lap_row(1.0, 800.0))
        self.assertEqual(800.0, self.tail.latest_distance(self.path))
        self.clock.advance(3.5)
        self.assertIsNone(self.tail.latest_distance(self.path))

    def test_partial_final_row_is_completed_on_the_next_poll(self):
        self.append(lap_row(1.0, 700.0))
        self.tail.latest_distance(self.path)

        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(lap_row(1.05, 900.0)[:20])  # row still being written
        self.assertEqual(700.0, self.tail.latest_distance(self.path))

        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(lap_row(1.05, 900.0)[20:] + "\n")
        self.assertEqual(900.0, self.tail.latest_distance(self.path))

    def test_switching_to_a_new_recording_resets_position(self):
        self.append(lap_row(1.0, 800.0))
        self.assertEqual(800.0, self.tail.latest_distance(self.path))

        other = self.path.parent / "2026-01-02_000000_session.csv"
        other.write_text(HEADER + "\n" + lap_row(1.0, 1700.0) + "\n", encoding="utf-8")
        self.assertEqual(1700.0, self.tail.latest_distance(other))

    def test_attaching_to_a_large_file_reads_only_its_tail(self):
        self.append(*[lap_row(i * 0.05, 100.0 + i) for i in range(4000)])
        tail = LapDistanceTail(initial_tail_bytes=2048, clock=self.clock)
        self.assertEqual(4099.0, tail.latest_distance(self.path))
        self.assertLess(tail.bytes_read, 4096)

    def test_no_file_means_no_position(self):
        self.assertIsNone(self.tail.latest_distance(None))

    def test_headerless_file_is_reported_once_and_not_guessed(self):
        broken = self.path.parent / "2026-01-03_000000_session.csv"
        broken.write_text("nonsense\n1,2,3\n", encoding="utf-8")
        self.assertIsNone(self.tail.latest_distance(broken))


class CornerApproachMonitorTest(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.monitor = CornerApproachMonitor(
            ZONES,
            hysteresis_m=25.0,
            min_interval_s=20.0,
            max_duration_s=6.0,
            clock=self.clock,
        )

    def test_cue_starts_inside_the_zone_and_names_the_corner(self):
        self.assertIsNone(self.monitor.update(600.0))
        self.assertEqual("Turn 1", self.monitor.update(720.0))

    def test_cue_ends_only_past_the_hysteresis_margin(self):
        self.monitor.update(720.0)
        self.assertEqual("Turn 1", self.monitor.update(960.0))   # past edge
        self.assertEqual("Turn 1", self.monitor.update(974.0))   # still in band
        self.assertIsNone(self.monitor.update(976.0))            # clear of band

    def test_jitter_across_the_entry_boundary_does_not_flicker(self):
        states = []
        for distance in (699.0, 701.0, 698.0, 702.0, 690.0, 705.0):
            states.append(self.monitor.update(distance))
            self.clock.advance(0.25)
        # One transition only: off then on, never alternating.
        self.assertEqual([None, "Turn 1", "Turn 1", "Turn 1", "Turn 1", "Turn 1"], states)

    def test_reentry_within_the_rate_limit_is_refused(self):
        self.assertEqual("Turn 1", self.monitor.update(720.0))
        self.clock.advance(3.0)
        self.assertIsNone(self.monitor.update(1000.0))  # clear of the band
        self.clock.advance(1.0)
        # A flashback that rewinds to before the corner is a legitimate approach
        # by direction, so only the rate limit stops it re-flashing.
        self.assertIsNone(self.monitor.update(300.0))
        self.assertIsNone(self.monitor.update(720.0))

    def test_the_next_lap_cues_the_same_corner_again(self):
        self.assertEqual("Turn 1", self.monitor.update(720.0))
        self.monitor.update(1000.0)
        self.clock.advance(90.0)  # one Monza lap
        self.monitor.update(120.0)  # across the start line onto the next lap
        self.assertEqual("Turn 1", self.monitor.update(720.0))

    def test_arriving_from_the_far_end_is_not_an_approach(self):
        # data/raw/2026-07-28_025428 lap 4: duplicated rows rewind lap_distance
        # from Roggia's exit back into the zone. Going backwards is not an
        # approach, and this produced a second Roggia cue in one lap before the
        # direction rule existed.
        self.assertEqual("Roggia", self.monitor.update(1700.0))
        self.assertIsNone(self.monitor.update(2260.0))  # clear of the band
        self.clock.advance(21.0)  # past the rate limit, so only direction saves us
        self.assertIsNone(self.monitor.update(2153.0))
        self.assertIsNone(self.monitor.update(2160.0))  # forward again, still inside

    def test_first_reading_inside_a_zone_still_cues(self):
        # Starting the LED app mid-lap gives no previous position to compare
        # against; refusing to cue at all there would be worse than trusting it.
        self.assertEqual("Turn 1", self.monitor.update(780.0))

    def test_rate_limit_is_per_corner_not_global(self):
        self.assertEqual("Turn 1", self.monitor.update(720.0))
        self.clock.advance(4.0)
        self.monitor.update(1000.0)
        self.clock.advance(13.0)  # T1 to Roggia is ~17 s; well inside 20 s
        self.assertEqual("Roggia", self.monitor.update(1700.0))

    def test_a_cue_held_too_long_cancels_itself(self):
        self.assertEqual("Turn 1", self.monitor.update(800.0))
        self.clock.advance(6.5)  # stopped or spun inside the zone (cap is 6 s here)
        self.assertIsNone(self.monitor.update(800.0))
        self.clock.advance(30.0)
        self.assertIsNone(self.monitor.update(800.0))  # still not re-armed

    def test_cancelled_cue_rearms_on_the_next_approach(self):
        self.monitor.update(800.0)
        self.clock.advance(6.5)
        self.assertIsNone(self.monitor.update(800.0))
        self.clock.advance(25.0)
        self.assertIsNone(self.monitor.update(1200.0))  # finished the corner
        self.assertIsNone(self.monitor.update(400.0))   # next lap, before the zone
        self.assertEqual("Turn 1", self.monitor.update(800.0))

    def test_unknown_position_drops_the_cue(self):
        self.assertEqual("Turn 1", self.monitor.update(720.0))
        self.assertIsNone(self.monitor.update(None))

    def test_negative_distance_before_the_start_line_is_not_a_corner(self):
        self.assertIsNone(self.monitor.update(-5677.6))

    def test_forgetting_position_does_not_forget_the_rate_limit(self):
        # A recorder restarting mid-stint starts a new file, but the corner it
        # just cued must still not re-flash.
        self.assertEqual("Turn 1", self.monitor.update(720.0))
        self.monitor.forget_position()
        self.clock.advance(2.0)
        self.assertIsNone(self.monitor.update(780.0))

    def test_position_history_does_not_block_a_later_session(self):
        self.assertEqual("Roggia", self.monitor.update(1700.0))
        self.monitor.update(2300.0)  # finished the corner, well past the zone
        self.monitor.forget_position()
        self.clock.advance(600.0)  # a new session, ten minutes later
        self.assertEqual("Roggia", self.monitor.update(1700.0))

    def test_reset_drops_the_cue_but_keeps_the_rate_limit(self):
        self.assertEqual("Turn 1", self.monitor.update(720.0))
        self.monitor.reset()
        self.assertIsNone(self.monitor.active_corner)
        self.clock.advance(2.0)
        self.assertIsNone(self.monitor.update(720.0))


class ShippedConfigTest(unittest.TestCase):
    """Guards the two numbers a bad edit would break silently on hardware.

    The slowest real pass through the widened band in data/raw/ is 10.8 s at
    Roggia, so a max duration near it cancels normal cues part-way through the
    corner -- which is exactly what tests/simulate_live_led.py caught at 6 s.
    """

    SLOWEST_REAL_PASS_MS = 10800

    def setUp(self):
        from config.loader import load_led_feedback_config

        self.config = load_led_feedback_config()

    def test_max_cue_duration_clears_the_slowest_real_pass(self):
        self.assertGreater(
            float(self.config["corner_cue_max_duration_ms"]),
            self.SLOWEST_REAL_PASS_MS,
        )

    def test_rate_limit_outlasts_a_cue(self):
        # Otherwise a self-cancelled cue could restart on the same pass.
        self.assertGreater(
            float(self.config["corner_cue_min_interval_ms"]),
            float(self.config["corner_cue_max_duration_ms"]),
        )

    def test_position_is_never_older_than_the_staleness_window(self):
        # The tail retains its last distance for exactly this long, so a stalled
        # recording cannot keep cueing a corner the car has long since left.
        self.assertIn("telemetry_stale_after_ms", self.config)
        self.assertGreater(float(self.config["telemetry_stale_after_ms"]), 0)


class LedSignallerStateTwoTest(unittest.TestCase):
    """The state machine end to end, with a real file and a real directory."""

    CONFIG = {
        "led_state_poll_interval_ms": 250,
        "telemetry_stale_after_ms": 3000,
        "bridge_state_resend_ms": 1000,
        "bridge_call_timeout_ms": 1000,
        "focus_track": "monza",
        "corner_approach_hysteresis_m": 25,
        "corner_cue_min_interval_ms": 20000,
        "corner_cue_max_duration_ms": 14000,
        "corner_tail_initial_bytes": 65536,
    }

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.session_dir = Path(self._tmp.name)
        self.path = self.session_dir / "2026-01-01_000000_session.csv"
        self.path.write_text(HEADER + "\n", encoding="utf-8")

        self.sent: list[int] = []

        class Recorder:
            name = "test"

            def send_state(_self, code: int) -> bool:
                self.sent.append(code)
                return True

        self.signaller = bridge_client.LedSignaller(
            Recorder(), self.session_dir, dict(self.CONFIG)
        )

    def append(self, *lines: str) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write("".join(line + "\n" for line in lines))

    def test_outside_a_zone_is_connected(self):
        self.append(lap_row(1.0, 300.0))
        self.assertEqual(bridge_client.STATE_CONNECTED, self.signaller.tick())

    def test_inside_turn_one_is_state_two(self):
        self.append(lap_row(1.0, 780.0))
        self.assertEqual(bridge_client.STATE_APPROACH_CORNER, self.signaller.tick())
        self.assertEqual("Turn 1", self.signaller.active_corner)

    def test_inside_roggia_is_state_two(self):
        self.append(lap_row(1.0, 2018.0))
        self.assertEqual(bridge_client.STATE_APPROACH_CORNER, self.signaller.tick())
        self.assertEqual("Roggia", self.signaller.active_corner)

    def test_no_recording_at_all_is_idle(self):
        self.path.unlink()
        self.assertEqual(bridge_client.STATE_IDLE, self.signaller.tick())

    def test_a_newer_recording_can_cue_from_its_first_position(self):
        # The previous session ended past Turn 1; the new one starts inside it.
        # Comparing the two positions would wrongly suppress the new cue.
        self.append(lap_row(1.0, 1400.0))
        self.assertEqual(bridge_client.STATE_CONNECTED, self.signaller.tick())

        newer = self.session_dir / "2026-01-02_000000_session.csv"
        newer.write_text(
            HEADER + "\n" + lap_row(1.0, 780.0) + "\n", encoding="utf-8"
        )
        self.assertEqual(bridge_client.STATE_APPROACH_CORNER, self.signaller.tick())
        self.assertEqual("Turn 1", self.signaller.active_corner)

    def test_a_broken_track_config_still_reports_connected(self):
        config = dict(self.CONFIG)
        config["focus_track"] = "not_a_track"

        class Recorder:
            name = "test"

            def send_state(self, code: int) -> bool:
                return True

        signaller = bridge_client.LedSignaller(Recorder(), self.session_dir, config)
        self.append(lap_row(1.0, 780.0))
        self.assertEqual(bridge_client.STATE_CONNECTED, signaller.tick())


if __name__ == "__main__":
    unittest.main()
