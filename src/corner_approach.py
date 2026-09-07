"""Live "am I approaching a focus corner right now" detection.

Everything else in this project analyses a session after it has finished:
corner_detector.py reads a complete CSV and finds corner zones retrospectively.
LED state 2 needs the opposite answer, while telemetry is still arriving, so this
module tails the recording that session_logger.py is currently writing and
answers from its newest rows.

Two pieces:

    LapDistanceTail        newest lap_distance from a growing CSV, reading only
                           the bytes appended since the previous poll
    CornerApproachMonitor  which zone (if any) that distance means we are in,
                           with hysteresis and rate limiting

Zone boundaries are not defined here. They come from config/monza.py through
config.loader.load_track_config(), the same calibrated numbers the post-session
analysis uses, so the live cue and the report cannot disagree about where a
corner is.

Nothing here imports the analysis code, the dashboard or session_logger.py.
"""

from __future__ import annotations

import csv
import time
from pathlib import Path

# packet_id 2 is the F1 25 Lap Data packet: the only one carrying lap_distance.
LAP_PACKET_ID = "2"

DEFAULT_HYSTERESIS_M = 25.0
DEFAULT_CUE_MIN_INTERVAL_S = 20.0
DEFAULT_CUE_MAX_DURATION_S = 14.0
DEFAULT_TAIL_BYTES = 65536


class LapDistanceTail:
    """Newest lap_distance from a session CSV that is still being written.

    Reads incrementally: a byte offset is carried between polls, so a poll costs
    the few hundred bytes that arrived since the last one rather than a re-parse
    of a file that reaches ~1.7 MB over five laps.

    The last distance seen is retained for *max_age_s* rather than being
    forgotten the moment a poll finds no new rows. session_logger.py flushes
    every 50 rows, so at ~40 rows/second the file grows in bursts roughly every
    1.2 seconds; without that retention the cue would drop out between flushes.
    That flush interval, not the poll interval, sets how quickly a zone entry can
    possibly be noticed.
    """

    def __init__(
        self,
        initial_tail_bytes: int = DEFAULT_TAIL_BYTES,
        max_age_s: float = 3.0,
        clock=time.time,
    ):
        self._initial_tail_bytes = int(initial_tail_bytes)
        self._max_age_s = float(max_age_s)
        self._clock = clock

        self._path: Path | None = None
        self._offset = 0
        self._partial = ""
        self._need_line_sync = False
        self._packet_index: int | None = None
        self._distance_index: int | None = None
        self._warned_columns = False

        self._last_distance: float | None = None
        self._last_distance_at = 0.0

        # Diagnostic, and the hook the tests use to prove reads are incremental.
        self.bytes_read = 0

    def reset(self) -> None:
        """Forget file position and last reading, keeping nothing cached."""
        self._path = None
        self._offset = 0
        self._partial = ""
        self._need_line_sync = False
        self._packet_index = None
        self._distance_index = None
        self._last_distance = None
        self._last_distance_at = 0.0

    def latest_distance(self, path: Path | None) -> float | None:
        """Return the newest lap_distance in metres, or None if there is none.

        None means "position is unknown", which callers must treat as "no cue"
        rather than as "not in a zone": an unreadable or stalled file is not
        evidence about where the car is.
        """
        if path is None:
            self.reset()
            return None

        self._poll(Path(path))

        if self._last_distance is None:
            return None
        if (self._clock() - self._last_distance_at) > self._max_age_s:
            return None
        return self._last_distance

    def _poll(self, path: Path) -> None:
        if self._path is None or path != self._path:
            self._attach(path)
            if self._path is None:
                return

        try:
            size = path.stat().st_size
        except OSError:
            return

        # A smaller file than our offset means a different file at the same
        # path, so the offset is meaningless and must be rebuilt.
        if size < self._offset:
            self._attach(path)
            if self._path is None:
                return
            try:
                size = path.stat().st_size
            except OSError:
                return

        if size <= self._offset:
            return

        try:
            with path.open("rb") as handle:
                handle.seek(self._offset)
                chunk = handle.read()
        except OSError:
            return

        self._offset += len(chunk)
        self.bytes_read += len(chunk)

        text = self._partial + chunk.decode("utf-8", "replace")
        self._partial = ""

        # After attaching mid-file the first fragment is the tail of a row we
        # never saw the start of; drop up to the first newline.
        if self._need_line_sync:
            newline = text.find("\n")
            if newline < 0:
                return
            text = text[newline + 1 :]
            self._need_line_sync = False

        lines = text.split("\n")
        self._partial = lines.pop()  # incomplete final row, completed next poll

        distance = self._newest_distance(lines)
        if distance is not None:
            self._last_distance = distance
            self._last_distance_at = self._clock()

    def _attach(self, path: Path) -> None:
        """Read the header for column positions, then jump near the end.

        Opened in binary mode deliberately: text-mode tell() returns an opaque
        cookie that cannot be compared against st_size or arithmetic'd.
        """
        self._path = None
        self._offset = 0
        self._partial = ""
        self._need_line_sync = False
        self._last_distance = None

        try:
            size = path.stat().st_size
            with path.open("rb") as handle:
                header_line = handle.readline()
                header_end = handle.tell()
        except OSError:
            return

        columns = next(csv.reader([header_line.decode("utf-8", "replace")]), [])
        try:
            self._packet_index = columns.index("packet_id")
            self._distance_index = columns.index("lap_distance")
        except ValueError:
            if not self._warned_columns:
                print(f"[led] {path.name}: no packet_id/lap_distance columns")
                self._warned_columns = True
            return

        self._path = path
        start = max(header_end, size - self._initial_tail_bytes)
        self._offset = start
        self._need_line_sync = start > header_end

    def _newest_distance(self, lines: list[str]) -> float | None:
        """Scan newest-first and stop at the first usable lap row."""
        for line in reversed(lines):
            if not line.strip():
                continue
            fields = next(csv.reader([line]), [])
            if len(fields) <= max(self._packet_index, self._distance_index):
                continue
            if fields[self._packet_index].strip() != LAP_PACKET_ID:
                continue
            raw = fields[self._distance_index].strip()
            if not raw:
                continue
            try:
                return float(raw)
            except ValueError:
                continue
        return None


class CornerApproachMonitor:
    """Turns a stream of lap distances into at most one corner cue at a time.

    Bare zone containment is not usable as a cue directly. Three things have to
    be added on top:

    Hysteresis -- leaving a zone requires travelling *hysteresis_m* past the
    boundary, so a car sitting on the edge, or a distance value that jitters
    across it, cannot toggle the matrix.

    Direction -- a cue only arms on a crossing into the zone from *before* its
    start. Arriving in a zone from its far end is going backwards, which is a
    flashback or a duplicated telemetry block, not an approach.
    data/raw/2026-07-28_025428_session.csv contains exactly that on lap 4: a
    block of rows replays Roggia's exit, rewinding lap_distance from ~2230 m to
    ~2153 m, which is inside the zone. Without this rule that produced a second
    Roggia cue in one lap.

    Rate limiting -- plan section 13 requires that a single corner cannot
    produce repeated distracting flashes. On top of the direction rule, a fresh
    cue is refused for *min_interval_s* after the previous one at that corner
    started, which covers a flashback that rewinds far enough to re-approach the
    corner legitimately within seconds.

    All timing is wall clock. session_time in the CSV runs backwards across those
    duplicated blocks and cannot be used to measure elapsed time.
    """

    def __init__(
        self,
        zones: dict,
        hysteresis_m: float = DEFAULT_HYSTERESIS_M,
        min_interval_s: float = DEFAULT_CUE_MIN_INTERVAL_S,
        max_duration_s: float = DEFAULT_CUE_MAX_DURATION_S,
        clock=time.time,
    ):
        self._bounds: dict[str, tuple[float, float]] = {}
        for name, config in zones.items():
            start, end = config["zone"]
            self._bounds[name] = (float(start), float(end))

        self._hysteresis_m = float(hysteresis_m)
        self._min_interval_s = float(min_interval_s)
        self._max_duration_s = float(max_duration_s)
        self._clock = clock

        self._active: str | None = None
        self._active_since = 0.0
        self._last_cue_at: dict[str, float] = {}
        self._disarmed: set[str] = set()
        self._last_distance: float | None = None

    @property
    def active_corner(self) -> str | None:
        return self._active

    def reset(self) -> None:
        """Drop the current cue because telemetry stopped.

        Rate-limit history is deliberately kept: a recording that pauses and
        resumes inside a corner should not be able to re-flash it.
        """
        self._active = None

    def forget_position(self) -> None:
        """Discard where the car was, because it is now a different recording.

        The direction rule compares against the previous distance, and a distance
        from a finished session says nothing about the new one -- left in place it
        could suppress the new session's first cue. Rate-limit history is kept
        even here, so a recorder that restarts mid-stint still cannot re-flash a
        corner it has just cued.
        """
        self._last_distance = None
        self._active = None

    def update(self, distance_m: float | None, now: float | None = None) -> str | None:
        """Feed one distance reading; return the corner to cue, or None."""
        moment = self._clock() if now is None else now

        if distance_m is None:
            self._active = None
            return None

        previous = self._last_distance
        self._last_distance = distance_m

        # A corner suppressed for over-running its cue becomes eligible again
        # once the car is genuinely clear of it.
        for name in list(self._disarmed):
            if not self._in_band(distance_m, name):
                self._disarmed.discard(name)

        if self._active is not None:
            if not self._in_band(distance_m, self._active):
                self._active = None
            elif (moment - self._active_since) > self._max_duration_s:
                # Stopped, spun or crawling inside the zone. Stop pulsing and
                # do not resume until the car has left the band.
                self._disarmed.add(self._active)
                self._active = None
            else:
                return self._active

        for name, (start, end) in self._bounds.items():
            if not (start <= distance_m <= end):
                continue
            if name in self._disarmed:
                continue
            # Entering from the far end means the car went backwards. Only an
            # unknown previous position (the first reading after startup) is
            # given the benefit of the doubt.
            if previous is not None and previous >= start:
                continue
            last_cue = self._last_cue_at.get(name)
            if last_cue is not None and (moment - last_cue) < self._min_interval_s:
                continue
            self._active = name
            self._active_since = moment
            self._last_cue_at[name] = moment
            return name

        return None

    def _in_band(self, distance_m: float, name: str) -> bool:
        """Zone widened by the hysteresis margin: the band a cue survives in."""
        start, end = self._bounds[name]
        return (start - self._hysteresis_m) <= distance_m <= (end + self._hysteresis_m)
