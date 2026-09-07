"""Linux-side sender for PitWall LED matrix states over Arduino Bridge RPC.

Sends a single small integer state code to the STM32, which owns all rendering
and animation timing (see mcu/bridge_protocol.md). Nothing here draws pixels:
full 104-pixel grid pushes over Bridge are unreliable on the UNO Q and would
need ~30 calls/second to animate, so this module only answers "which situation
are we in".

States 0, 1 and 7 appear on the side status LED. State 2 is the first matrix
driving cue: approaching a focus corner. States 3-6 are not implemented yet.

State is derived from the real recording activity of session_logger.py -- the
newest CSV in the recording directory growing means UDP telemetry is arriving,
and the newest lap_distance in that same file says where the car is right now
(src/corner_approach.py). This module never imports the analysis or dashboard
code and never modifies it.

Which directory that is comes from session_store.resolve_session_dir(), so
--session-dir or PITWALL_SESSION_DIR points the reader and the writer at the
same folder explicitly.

Run standalone (falls back to printing state changes if Bridge is unavailable):

    python3 src/bridge_client.py

Bridge only exists inside an Arduino App's managed container, so for real LED
output this module is driven by mcu/pitwall_led_app/python/main.py, started with
``arduino-app-cli app start ~/ArduinoApps/pitwall-led``.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.loader import load_led_feedback_config, load_track_config
from src import session_store
from src.corner_approach import CornerApproachMonitor, LapDistanceTail

# Wire protocol. Keep in sync with mcu/bridge_protocol.md and the sketch.
BRIDGE_METHOD = "pitwall_led_state"

STATE_IDLE = 0
STATE_CONNECTED = 1

# First matrix driving cue. The MCU treats it as implying connected, so the side
# status LED stays steady across the 1 <-> 2 transition (bridge_protocol.md).
STATE_APPROACH_CORNER = 2

# Codes 3-6 are further matrix cues, not yet implemented.

# Never sent from here. The MCU raises it locally when the heartbeat stops,
# because a dead Linux process cannot report its own death. Defined so logs and
# the code table stay consistent across both sides.
STATE_ERROR = 7

STATE_NAMES = {
    STATE_IDLE: "idle",
    STATE_CONNECTED: "connected",
    STATE_APPROACH_CORNER: "approaching corner",
    STATE_ERROR: "error (MCU-raised)",
}


class PrintTransport:
    """Fallback transport that reports state changes to stdout.

    Lets the state machine be exercised on a laptop, or on the UNO Q before the
    sketch is flashed, without pretending an LED was updated.
    """

    name = "print (no Bridge)"

    def send_state(self, code: int) -> bool:
        print(f"[led] would send state {code} ({STATE_NAMES.get(code, '?')})")
        return True


class BridgeTransport:
    """Real Arduino Bridge RPC transport.

    Bridge.call() is synchronous, so a sketch that is not yet listening shows up
    as an exception here rather than as silent data loss. Failures are reported
    and swallowed: a missing LED must not stop a driving session.
    """

    name = "Arduino Bridge RPC"

    def __init__(self, bridge, method: str = BRIDGE_METHOD):
        self._bridge = bridge
        self._method = method
        self._warned = False

    def send_state(self, code: int) -> bool:
        try:
            self._bridge.call(self._method, int(code))
        except Exception as exc:  # transport errors must not kill the loop
            if not self._warned:
                print(f"[led] Bridge call {self._method!r} failed: {exc}")
                self._warned = True
            return False

        if self._warned:
            print(f"[led] Bridge call {self._method!r} recovered")
            self._warned = False
        return True


def open_transport(force_print: bool = False):
    """Return a Bridge transport if this process can reach one, else printing.

    The arduino.app_utils package is supplied by the App Lab app environment, so
    whether it imports depends on how this script was launched.
    """
    if force_print:
        return PrintTransport()

    try:
        from arduino.app_utils import Bridge
    except ImportError as exc:
        print(f"[led] arduino.app_utils unavailable ({exc}); printing instead")
        return PrintTransport()

    return BridgeTransport(Bridge)


def latest_session_path(session_dir: Path) -> Path | None:
    """Return the most recent recording, or None if there are no recordings.

    session_store.list_sessions() is already newest-name-first, and names are
    timestamp-prefixed, so a session being recorded right now sorts first.
    """
    names = session_store.list_sessions(session_dir)
    if not names:
        return None
    return session_dir / names[0]


def build_approach_monitor(config: dict, clock=time.time) -> CornerApproachMonitor | None:
    """Build the corner monitor from config, or None if the track is unusable.

    A missing or broken track config must cost the driver the corner cue only.
    States 0, 1 and 7 are the honesty-critical ones and keep working.
    """
    track = str(config.get("focus_track", "")).strip()
    if not track:
        print("[led] no focus_track configured; corner cue disabled")
        return None

    try:
        zones = load_track_config(track)
    except (ValueError, AttributeError, KeyError) as exc:
        print(f"[led] cannot load track {track!r} ({exc}); corner cue disabled")
        return None

    if not zones:
        print(f"[led] track {track!r} defines no zones; corner cue disabled")
        return None

    return CornerApproachMonitor(
        zones,
        hysteresis_m=float(config["corner_approach_hysteresis_m"]),
        min_interval_s=float(config["corner_cue_min_interval_ms"]) / 1000.0,
        max_duration_s=float(config["corner_cue_max_duration_ms"]) / 1000.0,
        clock=clock,
    )


class LedSignaller:
    """Decides the current LED state and keeps the MCU informed of it."""

    def __init__(
        self,
        transport,
        session_dir: Path = session_store.DEFAULT_SESSION_DIR,
        config: dict | None = None,
        clock=time.time,
        approach_monitor: CornerApproachMonitor | None = None,
    ):
        cfg = config if config is not None else load_led_feedback_config()
        self._transport = transport
        self._session_dir = session_dir
        self._clock = clock
        self._stale_after_s = float(cfg["telemetry_stale_after_ms"]) / 1000.0
        self._resend_after_s = float(cfg["bridge_state_resend_ms"]) / 1000.0
        self._sent_state: int | None = None
        self._sent_at = 0.0

        if approach_monitor is None:
            approach_monitor = build_approach_monitor(cfg, clock=clock)
        self._approach = approach_monitor

        # A distance older than the staleness window is not evidence of position,
        # for the same reason a frozen file is not evidence of a live session.
        self._tail = LapDistanceTail(
            initial_tail_bytes=int(cfg["corner_tail_initial_bytes"]),
            max_age_s=self._stale_after_s,
            clock=clock,
        )
        self._active_corner: str | None = None
        self._watched_path: Path | None = None

    @property
    def active_corner(self) -> str | None:
        """Corner currently being cued, for logs and the simulation harness."""
        return self._active_corner

    def telemetry_age_seconds(self, path: Path | None = None) -> float | None:
        """Seconds since the active recording last grew, or None if no file.

        session_logger.py flushes periodically, so mtime advances while packets
        arrive and freezes when they stop.

        *path* is accepted so one tick can stat the recording it already located
        instead of listing the directory twice.
        """
        if path is None:
            path = latest_session_path(self._session_dir)
        if path is None:
            return None

        try:
            mtime = path.stat().st_mtime
        except OSError:
            return None

        return max(0.0, self._clock() - mtime)

    def desired_state(self) -> int:
        path = latest_session_path(self._session_dir)
        age = self.telemetry_age_seconds(path)

        if age is None or age > self._stale_after_s:
            # Not recording. Drop any cue, but keep the rate-limit history so a
            # pause inside a corner cannot be used to re-flash it.
            if self._approach is not None:
                self._approach.reset()
            self._active_corner = None
            return STATE_IDLE

        if self._approach is None:
            self._active_corner = None
            return STATE_CONNECTED

        # A different recording means the previous position belongs to a
        # finished session and must not be compared against this one.
        if path != self._watched_path:
            self._approach.forget_position()
            self._watched_path = path

        distance = self._tail.latest_distance(path)
        self._active_corner = self._approach.update(distance)

        if self._active_corner is not None:
            return STATE_APPROACH_CORNER
        return STATE_CONNECTED

    def tick(self) -> int:
        """Evaluate state once and send it if it changed or the heartbeat is due.

        The resend is what lets the sketch's watchdog distinguish "still
        logging" from "the Linux side died", so it is not redundant traffic.
        """
        state = self.desired_state()
        now = self._clock()
        changed = state != self._sent_state
        heartbeat_due = (now - self._sent_at) >= self._resend_after_s

        if changed or heartbeat_due:
            if changed:
                previous = STATE_NAMES.get(self._sent_state, "unset")
                label = STATE_NAMES.get(state, state)
                if self._active_corner is not None:
                    label = f"{label} ({self._active_corner})"
                print(f"[led] {previous} -> {label}")
            if self._transport.send_state(state):
                self._sent_state = state
                self._sent_at = now

        return state


def build_applab_loop(session_dir: Path | None = None):
    """Return a no-argument callable for App Lab's ``App.run(user_loop=...)``.

    App Lab calls user_loop as fast as it returns, so the sleep belongs here
    rather than in tick().

    There are no command-line arguments in the App Lab path, so the directory
    comes from the caller or PITWALL_SESSION_DIR.
    """
    config = load_led_feedback_config()
    transport = open_transport()
    directory = session_store.resolve_session_dir(session_dir)
    signaller = LedSignaller(transport, directory, config)
    interval = float(config["led_state_poll_interval_ms"]) / 1000.0

    print(f"[led] transport: {transport.name}")
    print(f"[led] watching: {directory}")
    print(f"[led] corner cue track: {config.get('focus_track')}")

    def loop() -> None:
        signaller.tick()
        time.sleep(interval)

    return loop


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--print-only",
        action="store_true",
        help="never touch Bridge; print the state machine's decisions",
    )
    parser.add_argument(
        "--session-dir",
        type=Path,
        default=None,
        help=(
            "directory holding session CSVs; overrides "
            f"${session_store.SESSION_DIR_ENV_VAR} and the default data/raw"
        ),
    )
    args = parser.parse_args(argv)

    config = load_led_feedback_config()
    transport = open_transport(force_print=args.print_only)
    session_dir = session_store.resolve_session_dir(args.session_dir)
    signaller = LedSignaller(transport, session_dir, config)
    interval = float(config["led_state_poll_interval_ms"]) / 1000.0

    print(f"[led] transport: {transport.name}")
    print(f"[led] watching: {session_dir}")
    print(f"[led] corner cue track: {config.get('focus_track')}")
    print(f"[led] polling every {interval:.2f}s; Ctrl-C to stop")

    try:
        while True:
            signaller.tick()
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n[led] stopping; sending idle")
        transport.send_state(STATE_IDLE)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
