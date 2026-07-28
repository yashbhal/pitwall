from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src import brake_analyzer, coach, corner_detector
from config.loader import load_track_config


def analyze_session(csv_path: str, track_name: str) -> dict:
    """Analyze a session CSV and produce per-corner feedback plus one priority.

    The returned dict has three keys:
      - all_corners: dict mapping corner name to its metrics/feedback.
      - priority_corner: the single highlighted corner.
      - priority_feedback: the human-readable recommendation for that corner.

    Ranking uses the existing logic: prefer more brake reapplications first,
    then break ties with larger absolute onset-distance deviation from the
    configured reference (if any).
    """
    zones = load_track_config(track_name)
    all_corners: dict[str, dict] = {}

    for corner_name, cfg in zones.items():
        zone = cfg["zone"]
        reference = cfg.get("reference")

        samples_by_lap = corner_detector.extract_corner_samples(csv_path, zone)

        valid_attempts = 0
        reapplications_all: list[dict] = []

        all_stints = [
            stint
            for stints in samples_by_lap.values()
            for stint in stints
        ]

        selected_stint = (
            max(all_stints, key=len) if all_stints else None
        )

        if selected_stint:
            rejected_count = len(all_stints) - 1
            first_t = float(selected_stint[0].get("session_time") or 0)
            last_t = float(selected_stint[-1].get("session_time") or 0)
            print(
                f"[DEBUG] corner={corner_name} SELECTED stint: "
                f"samples={len(selected_stint)} "
                f"first_t={first_t:.2f} last_t={last_t:.2f} "
                f"(rejected {rejected_count} other stint(s))"
            )

        onset = (
            brake_analyzer.find_brake_onset(selected_stint)
            if selected_stint
            else None
        )

        if onset is not None:
            valid_attempts = 1
            reapps = brake_analyzer.find_brake_reapplications(selected_stint)
            reapplications_all = [
                {"distance_m": r["lap_distance"]} for r in reapps
            ]

        if onset is not None:
            onset_for_coach = {
                "distance_m": onset["onset_lap_distance"],
                "speed_kmh": onset["onset_speed"],
            }

            if reference is not None:
                onset_delta_abs = abs(
                    onset_for_coach["distance_m"] - reference["distance_m"]
                )
            else:
                onset_delta_abs = 0.0

            reapplication_count = len(reapplications_all)

            feedback = coach.generate_corner_feedback(
                corner_name,
                onset_for_coach,
                reapplications_all,
                reference=reference,
            )

            all_corners[corner_name] = {
                "status": "ok",
                "attempts": valid_attempts,
                "reapplication_count": reapplication_count,
                "onset_delta_abs": onset_delta_abs,
                "onset_distance_m": onset_for_coach["distance_m"],
                "onset_speed_kmh": onset_for_coach["speed_kmh"],
                "feedback": feedback,
            }
        else:
            all_corners[corner_name] = {
                "status": "no_data",
                "attempts": 0,
                "reapplication_count": 0,
                "onset_delta_abs": 0.0,
                "onset_distance_m": None,
                "onset_speed_kmh": None,
                "feedback": None,
            }

    ok_corners = [
        name for name, data in all_corners.items() if data["status"] == "ok"
    ]

    if ok_corners:
        priority_corner = max(
            ok_corners,
            key=lambda name: (
                all_corners[name]["reapplication_count"],
                all_corners[name]["onset_delta_abs"],
            ),
        )
        priority_feedback = all_corners[priority_corner]["feedback"]
    else:
        priority_corner = None
        priority_feedback = "No valid corner data available."

    return {
        "all_corners": all_corners,
        "priority_corner": priority_corner,
        "priority_feedback": priority_feedback,
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        raise SystemExit(
            "Usage: python src/session_analyzer.py <csv_path> <track_name>"
        )

    csv_path = sys.argv[1]
    track_name = sys.argv[2]

    report = analyze_session(csv_path, track_name)

    print("=" * 60)
    print("PER-CORNER FEEDBACK")
    print("=" * 60)
    for corner_name, data in report["all_corners"].items():
        print()
        print(f"--- {corner_name} ---")
        if data["feedback"] is None:
            print("  No valid onset data.")
        else:
            print(data["feedback"])

    print()
    print("=" * 60)
    print("PRIORITY")
    print("=" * 60)
    print(f"Priority corner: {report['priority_corner']}")
    print()
    print(report["priority_feedback"])
