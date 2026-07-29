from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.loader import load_thresholds

# Not part of the plan's threshold list: this is the hysteresis floor used to
# decide the brake has actually been released, as opposed to merely eased.
BRAKE_LIFT_THRESHOLD = 0.05


def _float(row: dict, key: str, default: float = 0.0) -> float:
    raw = row.get(key)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except (ValueError, TypeError):
        return default


def _brake_thresholds(thresholds: dict | None) -> tuple[float, float, float, float]:
    """Resolve the four brake tuning values, loading config only if needed."""
    values = load_thresholds() if thresholds is None else thresholds
    return (
        float(values["brake_onset_threshold"]),
        float(values["minimum_brake_duration_ms"]),
        float(values["brake_reapplication_gap_ms"]),
        float(values["brake_reapplication_window_ms"]),
    )


def find_brake_onset(
    samples: list[dict], thresholds: dict | None = None
) -> dict | None:
    """Find the first *sustained* brake application in a stint.

    A single frame above the brake threshold is not an onset: a brief brush of
    the pedal, or sensor noise, would otherwise set the onset far earlier than
    the driver's real braking point and inflate onset variation. A candidate
    only counts once brake stays above the threshold for at least
    minimum_brake_duration_ms.

    The measured duration is conservative: it spans the first to the last
    consecutive above-threshold sample, so at a 20 Hz packet rate a 150 ms
    requirement needs roughly four consecutive braking samples. Runs that are
    still ongoing when the stint ends are measured only up to the final sample.
    """
    onset_threshold, minimum_duration_ms, _, _ = _brake_thresholds(thresholds)

    index = 0
    total = len(samples)

    while index < total:
        if _float(samples[index], "brake") <= onset_threshold:
            index += 1
            continue

        start_time = _float(samples[index], "session_time")
        last_time = start_time
        end = index
        while end < total and _float(samples[end], "brake") > onset_threshold:
            last_time = _float(samples[end], "session_time")
            end += 1

        sustained_ms = (last_time - start_time) * 1000.0
        if sustained_ms >= minimum_duration_ms:
            row = samples[index]
            return {
                "onset_session_time": start_time,
                "onset_lap_distance": _float(row, "lap_distance"),
                "onset_speed": _float(row, "speed"),
                "sustained_ms": sustained_ms,
            }

        index = end if end > index else index + 1

    return None


def find_brake_reapplications(
    samples: list[dict],
    thresholds: dict | None = None,
    onset: dict | None = None,
) -> list[dict]:
    """Count genuine brake reapplications within the braking phase.

    Two filters from the plan's threshold list keep this from counting pedal
    modulation as driver error:

    - brake_reapplication_gap_ms: the release must last at least this long
      before a renewed press counts. ABS chatter and pedal pumping release for
      only a few tens of milliseconds, so a pulse train collapses to zero
      events rather than one per pulse.
    - brake_reapplication_window_ms: only presses within this window after the
      sustained onset belong to the same braking phase. A later, separate brake
      application further around the corner is not a reapplication.

    Pass *onset* to reuse an already-computed onset instead of recomputing it.
    """
    onset_threshold, _, gap_ms, window_ms = _brake_thresholds(thresholds)

    if onset is None:
        onset = find_brake_onset(samples, thresholds)
    if onset is None:
        return []

    phase_start = onset["onset_session_time"]
    phase_end = phase_start + window_ms / 1000.0

    reapplications: list[dict] = []
    lift_start: float | None = None

    for row in samples:
        sample_time = _float(row, "session_time")
        if sample_time < phase_start:
            continue
        if sample_time > phase_end:
            break

        brake = _float(row, "brake")

        if brake < BRAKE_LIFT_THRESHOLD:
            if lift_start is None:
                lift_start = sample_time
            continue

        if lift_start is not None and brake > onset_threshold:
            lift_ms = (sample_time - lift_start) * 1000.0
            if lift_ms >= gap_ms:
                reapplications.append(
                    {
                        "session_time": sample_time,
                        "lap_distance": _float(row, "lap_distance"),
                        "lift_ms": lift_ms,
                    }
                )
            lift_start = None

    return reapplications
