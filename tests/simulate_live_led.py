"""Replay a real session as a live-growing CSV and watch LED state 2 react.

The unit tests in tests/test_corner_approach.py prove the rules in isolation.
This proves the whole Linux-side path against real telemetry, with no PS5, no
UNO Q and no fresh recording session: a writer thread appends rows from one of
the files in data/raw/ into a scratch directory at their original pacing, and
the real LedSignaller polls that directory exactly as it does on the board.

Two things make it a fair test rather than a demo:

  * The writer flushes every 50 rows, like src/session_logger.py, so the reader
    sees the same bursty growth it sees live -- which is what actually bounds how
    fast a zone entry can be noticed.
  * --speed compresses game time, so every wall-clock threshold (staleness,
    rate limit, max cue duration, poll interval) is scaled by the same factor.
    Without that, a replay at 8x would silently suppress later laps' cues by
    running into the 20-second rate limit, and the run would look like a bug.

Usage:

    python3 tests/simulate_live_led.py
    python3 tests/simulate_live_led.py --preview
    python3 tests/simulate_live_led.py --start-at 35 --duration 40 --speed 1 --preview

The matrix preview mirrors the glyph and pulse maths in
mcu/pitwall_led_app/sketch/sketch.ino. It is a visual check of the shape and
rhythm only; the sketch remains the single source of truth for what the hardware
does, and the constants below must be changed with it.
"""

from __future__ import annotations

import argparse
import csv
import sys
import threading
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src import bridge_client

DEFAULT_SOURCE = PROJECT_ROOT / "data" / "raw" / "2026-07-28_025428_session.csv"

# Mirrors sketch.ino: APPROACH_PULSE_PERIOD_MS, APPROACH_MIN/MAX_BRIGHTNESS.
PULSE_PERIOD_S = 1.6
PULSE_MIN = 20
PULSE_MAX = 255

MATRIX_ROWS = 8
MATRIX_COLS = 13

# session_logger.py's flush cadence. Reproduced, not imported, because importing
# it would create a second CSV in the real recording directory on import.
FLUSH_EVERY_ROWS = 50

# Anything shorter than this is a flicker, not a cue a driver could use.
MIN_USEFUL_CUE_S = 0.5

SHADES = " .:-=+*#%@"


def pulse_brightness(elapsed_s: float) -> int:
    """Symmetric triangle wave, same shape as the sketch's pulseBrightness()."""
    half = PULSE_PERIOD_S / 2.0
    phase = elapsed_s % PULSE_PERIOD_S
    if phase >= half:
        phase = PULSE_PERIOD_S - phase
    return int(PULSE_MIN + (phase / half) * (PULSE_MAX - PULSE_MIN))


def triangle_up_rows(brightness: int) -> list[str]:
    """ASCII render of the sketch's filled up-triangle at *brightness*."""
    centre = MATRIX_COLS // 2
    shade = SHADES[min(len(SHADES) - 1, brightness * len(SHADES) // 256)]
    rows = []
    for row in range(MATRIX_ROWS):
        half_width = (row * centre) // (MATRIX_ROWS - 1)
        rows.append(
            "".join(
                shade if abs(col - centre) <= half_width else " "
                for col in range(MATRIX_COLS)
            )
        )
    return rows


class SessionWriter:
    """Appends a recorded session into a new CSV at its original pacing."""

    def __init__(self, source: Path, target: Path, speed: float,
                 start_at: float, duration: float | None):
        self._target = target
        self._speed = speed
        self._stop = threading.Event()
        self.finished = threading.Event()
        self.rows_written = 0
        self.last_distance: float | None = None
        self.game_time = 0.0

        with source.open("r", newline="", encoding="utf-8") as handle:
            lines = handle.read().splitlines()

        self._header = lines[0]
        self._schedule = self._build_schedule(lines[1:], start_at, duration)

    def _build_schedule(self, rows: list[str], start_at: float,
                        duration: float | None) -> list[tuple[float, str, float | None]]:
        """Pair each row with its offset in game seconds and its lap distance.

        Elapsed time is accumulated from positive deltas only, and deltas are
        clamped: real recordings contain paused stretches and, in
        2026-07-28_025428, a block of duplicated rows where session_time runs
        backwards. Neither should turn into a sleep or a rewind here.
        """
        schedule: list[tuple[float, float, str, float | None]] = []
        elapsed = 0.0
        previous: float | None = None

        for line in rows:
            fields = next(csv.reader([line]), [])
            if len(fields) < 5:
                continue
            try:
                session_time = float(fields[2])
            except ValueError:
                continue

            if previous is not None:
                delta = session_time - previous
                if 0.0 < delta <= 1.0:
                    elapsed += delta
            previous = session_time

            distance = None
            if fields[1].strip() == "2" and fields[4].strip():
                try:
                    distance = float(fields[4])
                except ValueError:
                    distance = None

            schedule.append((elapsed, session_time, line, distance))

        end = None if duration is None else start_at + duration
        return [
            (elapsed - start_at, line, distance)
            for elapsed, _session_time, line, distance in schedule
            if elapsed >= start_at and (end is None or elapsed <= end)
        ]

    @property
    def game_seconds_total(self) -> float:
        return self._schedule[-1][0] if self._schedule else 0.0

    @property
    def row_count(self) -> int:
        return len(self._schedule)

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        started = time.monotonic()
        with self._target.open("w", newline="", encoding="utf-8") as handle:
            handle.write(self._header + "\n")
            handle.flush()

            for offset, line, distance in self._schedule:
                if self._stop.is_set():
                    break

                due = started + offset / self._speed
                delay = due - time.monotonic()
                if delay > 0:
                    time.sleep(delay)

                handle.write(line + "\n")
                self.rows_written += 1
                self.game_time = offset
                if distance is not None:
                    self.last_distance = distance

                # Same flush cadence as session_logger.py, so the reader sees
                # data appear in bursts rather than row by row.
                if self.rows_written % FLUSH_EVERY_ROWS == 0:
                    handle.flush()

            handle.flush()

        self.finished.set()


def scaled_config(speed: float) -> dict:
    """Real config with every wall-clock duration divided by *speed*."""
    from config.loader import load_led_feedback_config

    config = load_led_feedback_config()
    for key in (
        "led_state_poll_interval_ms",
        "telemetry_stale_after_ms",
        "bridge_state_resend_ms",
        "corner_cue_min_interval_ms",
        "corner_cue_max_duration_ms",
    ):
        config[key] = float(config[key]) / speed
    return config


class Recorder:
    """Transport that keeps every code sent, so the run can be judged after."""

    name = "simulation (no Bridge)"

    def __init__(self):
        self.codes: list[int] = []

    def send_state(self, code: int) -> bool:
        self.codes.append(code)
        return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", nargs="?", type=Path, default=DEFAULT_SOURCE,
                        help="session CSV to replay (default: 2026-07-28_025428)")
    parser.add_argument("--speed", type=float, default=8.0,
                        help="game seconds per wall second (default: 8)")
    parser.add_argument("--start-at", type=float, default=0.0,
                        help="skip this many game seconds before replaying")
    parser.add_argument("--duration", type=float, default=None,
                        help="replay only this many game seconds")
    parser.add_argument("--preview", action="store_true",
                        help="draw the matrix glyph and pulse in the terminal")
    parser.add_argument("--session-dir", type=Path, default=None,
                        help="scratch directory to write the replay into "
                             "(default: data/sessions/led_sim)")
    args = parser.parse_args(argv)

    if not args.source.is_file():
        raise SystemExit(f"File not found: {args.source}")
    if args.speed <= 0:
        raise SystemExit("--speed must be positive")

    session_dir = args.session_dir or (PROJECT_ROOT / "data" / "sessions" / "led_sim")
    session_dir.mkdir(parents=True, exist_ok=True)
    for stale in session_dir.glob("*.csv"):
        stale.unlink()

    target = session_dir / "2026-01-01_000000_session.csv"
    config = scaled_config(args.speed)
    poll_interval = config["led_state_poll_interval_ms"] / 1000.0

    recorder = Recorder()
    signaller = bridge_client.LedSignaller(recorder, session_dir, config)

    writer = SessionWriter(args.source, target, args.speed, args.start_at, args.duration)
    if writer.row_count == 0:
        raise SystemExit("nothing to replay in that time window")

    print(f"source     : {args.source.name}")
    print(f"replaying  : {writer.game_seconds_total:.0f} game seconds "
          f"at {args.speed:g}x -> {writer.game_seconds_total / args.speed:.0f} wall seconds")
    print(f"scratch dir: {session_dir}")
    print(f"thresholds : hysteresis {config['corner_approach_hysteresis_m']:g} m, "
          f"rate limit {config['corner_cue_min_interval_ms'] / 1000:.2f} s wall "
          f"({config['corner_cue_min_interval_ms'] * args.speed / 1000:.0f} s game), "
          f"poll {poll_interval:.3f} s")
    print("Ctrl-C to stop early\n")

    thread = threading.Thread(target=writer.run, daemon=True)
    thread.start()

    episodes: list[dict] = []
    state: int | None = None
    previous_state: int | None = None
    next_poll = time.monotonic()
    preview_lines = 0

    # After the replay ends the file stops growing, so keep polling long enough
    # for the staleness path to run and close any open cue.
    drain_until: float | None = None
    drain_s = config["telemetry_stale_after_ms"] / 1000.0 + poll_interval * 2

    def clear_preview() -> None:
        nonlocal preview_lines
        if preview_lines:
            sys.stdout.write(f"\x1b[{preview_lines}A\x1b[J")
            preview_lines = 0

    try:
        while drain_until is None or time.monotonic() < drain_until:
            now = time.monotonic()
            if drain_until is None and writer.finished.is_set():
                drain_until = now + drain_s

            if now >= next_poll:
                next_poll = now + poll_interval
                state = signaller.tick()
                corner = signaller.active_corner

                if state != previous_state:
                    clear_preview()
                    stamp = f"t={writer.game_time:7.1f}s game"
                    distance = writer.last_distance
                    where = "d=   n/a" if distance is None else f"d={distance:7.1f}m"
                    if state == bridge_client.STATE_APPROACH_CORNER:
                        print(f"{stamp}  {where}  state 2  CUE ON   {corner}")
                        episodes.append({
                            "corner": corner,
                            "started": now,
                            "entry_m": distance,
                            "entry_game_s": writer.game_time,
                        })
                    else:
                        label = bridge_client.STATE_NAMES.get(state, state)
                        if episodes and "ended" not in episodes[-1]:
                            episodes[-1]["ended"] = now
                            episodes[-1]["exit_m"] = distance
                        print(f"{stamp}  {where}  state {state}  cue off  ({label})")
                    previous_state = state

            if args.preview and state == bridge_client.STATE_APPROACH_CORNER:
                clear_preview()
                brightness = pulse_brightness(time.monotonic() * args.speed)
                block = triangle_up_rows(brightness)
                header = (f"  matrix: {signaller.active_corner}  "
                          f"brightness {brightness:3d}/255")
                sys.stdout.write(header + "\n")
                for row in block:
                    sys.stdout.write("  |" + row + "|\n")
                sys.stdout.flush()
                preview_lines = len(block) + 1

            time.sleep(0.05 / args.speed)
    except KeyboardInterrupt:
        writer.stop()
        print("\nstopped early")

    clear_preview()

    if episodes and "ended" not in episodes[-1]:
        episodes[-1]["ended"] = time.monotonic()
        episodes[-1]["exit_m"] = writer.last_distance

    print("\ncue episodes")
    print(f"  {'corner':<8} {'game t':>8} {'entry m':>9} {'exit m':>9} {'held':>8}")
    flickers = 0
    for episode in episodes:
        held = episode["ended"] - episode["started"]
        game_held = held * args.speed
        if game_held < MIN_USEFUL_CUE_S:
            flickers += 1
        entry = episode.get("entry_m")
        exit_m = episode.get("exit_m")
        print(f"  {episode['corner']:<8} {episode['entry_game_s']:>8.1f} "
              f"{'n/a' if entry is None else f'{entry:9.1f}'} "
              f"{'n/a' if exit_m is None else f'{exit_m:9.1f}'} "
              f"{game_held:>7.2f}s")

    per_corner: dict[str, int] = {}
    for episode in episodes:
        per_corner[episode["corner"]] = per_corner.get(episode["corner"], 0) + 1

    print("\nsummary")
    print(f"  episodes      : {len(episodes)}")
    for corner, count in sorted(per_corner.items()):
        print(f"    {corner:<12}: {count}")
    print(f"  state codes   : {sorted(set(recorder.codes))}")
    print(f"  flicker cues  : {flickers} (episodes under {MIN_USEFUL_CUE_S}s of game time)")
    print(f"  verdict       : {'FLICKER DETECTED' if flickers else 'no flicker'}")

    return 1 if flickers else 0


if __name__ == "__main__":
    raise SystemExit(main())
