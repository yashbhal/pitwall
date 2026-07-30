from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

RPM_COLUMN = "engine_rpm"

GEARBOX_MODES = ("Automatic", "Manual with Suggested Gear", "Manual")


def _rpm(row: dict) -> float | None:
    raw = row.get(RPM_COLUMN)
    if raw is None or str(raw).strip() == "":
        return None
    try:
        return float(raw)
    except (ValueError, TypeError):
        return None


def _float(row: dict, key: str) -> float:
    try:
        return float(row.get(key))
    except (ValueError, TypeError):
        return 0.0


def find_limiter_dwell(
    stint: list[dict],
    rpm_limiter_threshold: float,
    gearbox_mode: str,
    margin: float = 300,
) -> dict | None:
    if gearbox_mode not in GEARBOX_MODES:
        raise ValueError(
            f"Unknown gearbox_mode {gearbox_mode!r}; expected one of {GEARBOX_MODES}"
        )

    if gearbox_mode == "Automatic":
        return {
            "dwell_ms": None,
            "skipped_reason": (
                "Automatic gearbox - upshift timing is not driver-controlled, "
                "dwell metric not applicable"
            ),
        }

    if not stint:
        return None

    if all(_rpm(row) is None for row in stint):
        print(
            f"[WARNING] RPM data not available: missing or empty column "
            f"'{RPM_COLUMN}' in telemetry samples"
        )
        return None

    cutoff = rpm_limiter_threshold - margin

    best: list[dict] = []
    current: list[dict] = []
    for row in stint:
        rpm = _rpm(row)
        if rpm is not None and rpm >= cutoff:
            current.append(row)
        else:
            if len(current) > len(best):
                best = current
            current = []
    if len(current) > len(best):
        best = current

    if not best:
        return {"dwell_ms": 0.0, "start_distance_m": None, "end_distance_m": None}

    start_t = _float(best[0], "session_time")
    end_t = _float(best[-1], "session_time")

    return {
        "dwell_ms": (end_t - start_t) * 1000.0,
        "start_distance_m": _float(best[0], "lap_distance"),
        "end_distance_m": _float(best[-1], "lap_distance"),
    }


if __name__ == "__main__":
    from src import corner_detector
    from config.loader import load_track_config

    if len(sys.argv) < 3:
        print(
            "usage: python src/rpm_analyzer.py <csv_path> <corner_name> "
            "[rpm_limiter_threshold] [gearbox_mode] [track]"
        )
        raise SystemExit(1)

    csv_path = sys.argv[1]
    corner_name = sys.argv[2]
    threshold = float(sys.argv[3]) if len(sys.argv) > 3 else 12000.0
    gearbox_mode = sys.argv[4] if len(sys.argv) > 4 else "Manual with Suggested Gear"
    track_name = sys.argv[5] if len(sys.argv) > 5 else "monza"

    if gearbox_mode not in GEARBOX_MODES:
        print(f"Unknown gearbox_mode {gearbox_mode!r}; expected one of {GEARBOX_MODES}")
        raise SystemExit(1)

    zones = load_track_config(track_name)
    if corner_name not in zones:
        print(f"Unknown corner '{corner_name}'. Available: {list(zones)}")
        raise SystemExit(1)

    samples_by_lap = corner_detector.extract_corner_samples(
        csv_path, zones[corner_name]["zone"], verbose=True
    )

    print(f"\n=== RPM limiter dwell: {corner_name} ({csv_path}) ===")
    print(f"threshold={threshold:.0f} margin=300 -> cutoff={threshold - 300:.0f}")
    print(f"gearbox_mode={gearbox_mode}")

    all_rpms = [
        r
        for stints in samples_by_lap.values()
        for stint in stints
        for r in [_rpm(row) for row in stint]
        if r is not None
    ]
    if all_rpms:
        print(
            f"Sanity check: max RPM in corner samples = {max(all_rpms):.0f}, "
            f"min = {min(all_rpms):.0f}"
        )
    else:
        print(f"Sanity check: no '{RPM_COLUMN}' values found in corner samples")

    for lap_num in sorted(samples_by_lap):
        stints = samples_by_lap[lap_num]
        if not stints:
            continue
        stint = max(stints, key=len)
        result = find_limiter_dwell(stint, threshold, gearbox_mode)
        if result is None:
            print(f"  lap {lap_num}: no RPM data")
            continue
        if "skipped_reason" in result:
            print(
                f"  lap {lap_num}: dwell_ms=None SKIPPED - "
                f"{result['skipped_reason']}"
            )
            continue
        if result["start_distance_m"] is None:
            print(f"  lap {lap_num}: no samples at/above cutoff (dwell 0 ms)")
            continue
        print(
            f"  lap {lap_num}: dwell={result['dwell_ms']:.1f}ms "
            f"from {result['start_distance_m']:.1f}m "
            f"to {result['end_distance_m']:.1f}m "
            f"({len(stint)} samples)"
        )
