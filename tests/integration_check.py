import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src import corner_detector, brake_analyzer, coach
from config.loader import load_track_config


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python tests/integration_check.py <path_to_session_csv>")

    csv_path = sys.argv[1]

    print("Loading Monza zones...")
    zones = load_track_config("monza")
    turn1_zone = zones["Turn 1"]

    print(f"\nExtracting Turn 1 samples from: {csv_path}")
    samples_by_lap = corner_detector.extract_corner_samples(csv_path, turn1_zone)

    print("\nSamples are grouped by lap number:")
    for lap_num in sorted(samples_by_lap):
        stints = samples_by_lap[lap_num]
        print(f"  lap {lap_num}: {len(stints)} stint(s)")

    chosen = input("\nEnter lap number to analyze: ").strip()
    try:
        chosen_lap = int(chosen)
    except ValueError:
        raise SystemExit(f"Invalid lap number: {chosen!r}")

    if chosen_lap not in samples_by_lap:
        raise SystemExit(
            f"Lap {chosen_lap} not found. Available: {list(samples_by_lap.keys())}"
        )

    stints = samples_by_lap[chosen_lap]

    if len(stints) > 1:
        print(f"\nLap {chosen_lap} has {len(stints)} stints:")
        for i, stint in enumerate(stints, start=1):
            times = [float(r.get("session_time") or 0) for r in stint]
            start_time = min(times) if times else 0.0
            end_time = max(times) if times else 0.0
            print(
                f"  stint {i}: {len(stint)} samples, "
                f"t={start_time:.3f}s -> {end_time:.3f}s"
            )
        chosen_stint_str = input("\nEnter stint number to analyze: ").strip()
        try:
            chosen_stint = int(chosen_stint_str)
        except ValueError:
            raise SystemExit(f"Invalid stint number: {chosen_stint_str!r}")
    else:
        chosen_stint = 1

    if chosen_stint < 1 or chosen_stint > len(stints):
        raise SystemExit(
            f"Stint {chosen_stint} not found. Available: 1..{len(stints)}"
        )

    samples = stints[chosen_stint - 1]

    onset = brake_analyzer.find_brake_onset(samples)
    reapplications = brake_analyzer.find_brake_reapplications(samples)

    print("\n--- brake_analyzer output ---")
    print(f"Onset: {onset}")
    print(f"Reapplications: {reapplications}")

    if onset is not None:
        onset_for_coach = {
            "distance_m": onset["onset_lap_distance"],
            "speed_kmh": onset["onset_speed"],
        }
    else:
        onset_for_coach = None

    reapps_for_coach = [{"distance_m": r["lap_distance"]} for r in reapplications]

    feedback = coach.generate_corner_feedback(
        "Turn 1", onset_for_coach, reapps_for_coach
    )

    print("\n--- coach.generate_corner_feedback output ---")
    print(feedback)


if __name__ == "__main__":
    main()
