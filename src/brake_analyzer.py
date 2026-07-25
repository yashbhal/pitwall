from __future__ import annotations

BRAKE_ONSET_THRESHOLD = 0.10
BRAKE_LIFT_THRESHOLD = 0.05


def _float(row: dict, key: str, default: float = 0.0) -> float:
    raw = row.get(key)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except (ValueError, TypeError):
        return default


def find_brake_onset(samples: list[dict]) -> dict | None:
    for row in samples:
        if _float(row, "brake") > BRAKE_ONSET_THRESHOLD:
            return {
                "onset_session_time": _float(row, "session_time"),
                "onset_lap_distance": _float(row, "lap_distance"),
                "onset_speed": _float(row, "speed"),
            }
    return None


def find_brake_reapplications(samples: list[dict]) -> list[dict]:
    reapplications: list[dict] = []
    braking = False
    lifted = False

    for row in samples:
        brake = _float(row, "brake")

        if not braking:
            if brake > BRAKE_ONSET_THRESHOLD:
                braking = True
                lifted = False
            continue

        if brake < BRAKE_LIFT_THRESHOLD:
            lifted = True
            continue

        if lifted and brake > BRAKE_ONSET_THRESHOLD:
            reapplications.append(
                {
                    "session_time": _float(row, "session_time"),
                    "lap_distance": _float(row, "lap_distance"),
                }
            )
            lifted = False

    return reapplications
