from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

GEAR_COLUMN = "gear"

GEARBOX_MODES = ("Automatic", "Manual with Suggested Gear", "Manual")


def find_exit_gear(stint: list[dict]) -> dict | None:
    if not stint:
        return None

    last = stint[-1]
    raw = last.get(GEAR_COLUMN)
    if raw is None or str(raw).strip() == "":
        print(
            f"[WARNING] gear data not available: missing or empty column "
            f"'{GEAR_COLUMN}' in telemetry samples"
        )
        return None

    try:
        exit_gear = int(float(raw))
    except (ValueError, TypeError):
        print(
            f"[WARNING] gear data unusable: column '{GEAR_COLUMN}' "
            f"has non-numeric value {raw!r}"
        )
        return None

    def _float(key: str) -> float:
        value = last.get(key)
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    return {
        "exit_gear": exit_gear,
        "distance_m": _float("lap_distance"),
        "session_time": _float("session_time"),
    }


def compute_gear_consistency(exit_gears: list[dict], gearbox_mode: str) -> dict:
    if gearbox_mode not in GEARBOX_MODES:
        raise ValueError(
            f"Unknown gearbox_mode {gearbox_mode!r}; expected one of {GEARBOX_MODES}"
        )

    if gearbox_mode == "Automatic":
        return {
            "gears_used": [],
            "is_consistent": None,
            "attempt_count": len(exit_gears),
            "skipped_reason": (
                "Automatic gearbox - gear choice is not driver-controlled, "
                "consistency metric not applicable"
            ),
        }

    gears = sorted({e["exit_gear"] for e in exit_gears if e})
    return {
        "gears_used": gears,
        "is_consistent": len(gears) == 1,
        "attempt_count": len([e for e in exit_gears if e]),
    }


if __name__ == "__main__":
    from src import corner_detector
    from config.loader import load_track_config

    if len(sys.argv) < 3:
        print(
            "usage: python src/gear_analyzer.py <csv_path> <corner_name> "
            "[gearbox_mode] [track]"
        )
        raise SystemExit(1)

    csv_path = sys.argv[1]
    corner_name = sys.argv[2]
    gearbox_mode = sys.argv[3] if len(sys.argv) > 3 else "Manual with Suggested Gear"
    track_name = sys.argv[4] if len(sys.argv) > 4 else "monza"

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

    print(f"\n=== Exit gear: {corner_name} ({csv_path}) ===")
    print(f"gearbox_mode={gearbox_mode}")
    results: list[dict] = []
    for lap_num in sorted(samples_by_lap):
        stints = samples_by_lap[lap_num]
        if not stints:
            continue
        stint = max(stints, key=len)
        result = find_exit_gear(stint)
        if result is None:
            print(f"  lap {lap_num}: no gear data")
            continue
        results.append(result)
        print(
            f"  lap {lap_num}: exit_gear={result['exit_gear']} "
            f"at {result['distance_m']:.1f}m, t={result['session_time']:.3f}s "
            f"({len(stint)} samples)"
        )

    consistency = compute_gear_consistency(results, gearbox_mode)
    print(
        f"\nConsistency: gears_used={consistency['gears_used']} "
        f"is_consistent={consistency['is_consistent']} "
        f"attempt_count={consistency['attempt_count']}"
    )
    if "skipped_reason" in consistency:
        print(f"Skipped: {consistency['skipped_reason']}")
