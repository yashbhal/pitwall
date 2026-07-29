from __future__ import annotations

import statistics
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src import brake_analyzer, coach, corner_detector
from config.loader import load_track_config

# Attempt-validity thresholds. Intentionally local constants for now:
# config/thresholds.yaml is currently unwired and hooking it up is a
# separate change.
MIN_STINT_SAMPLES = 20
MAX_STINT_SAMPLES = 900
MIN_MID_STINT_SPEED_KMH = 30.0


def _float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _stint_window(stint: list[dict]) -> tuple[float, float]:
    times = [_float(row.get("session_time")) for row in stint]
    return (min(times), max(times)) if times else (0.0, 0.0)


def _stint_min_speed(stint: list[dict]) -> float:
    speeds = [_float(row.get("speed")) for row in stint]
    return min(speeds) if speeds else 0.0


def _stint_distance_range(stint: list[dict]) -> tuple[float, float]:
    distances = [_float(row.get("lap_distance")) for row in stint]
    return (min(distances), max(distances)) if distances else (0.0, 0.0)


def check_stint_validity(stint: list[dict]) -> tuple[bool, str | None]:
    """Rough validity filter for a single stint.

    Pure function over one stint. Returns (is_valid, reason) where reason is
    None when valid. Uses only signals already present in the telemetry rows:
    sample count and minimum speed within the stint.
    """
    sample_count = len(stint)

    if sample_count < MIN_STINT_SAMPLES:
        return False, f"too_few_samples: {sample_count} < {MIN_STINT_SAMPLES}"

    if sample_count > MAX_STINT_SAMPLES:
        return (
            False,
            f"anomalous_sample_count: {sample_count} > {MAX_STINT_SAMPLES}",
        )

    min_speed = _stint_min_speed(stint)
    if min_speed < MIN_MID_STINT_SPEED_KMH:
        return (
            False,
            f"near_zero_mid_stint_speed: {min_speed:.1f} km/h "
            f"< {MIN_MID_STINT_SPEED_KMH:.1f} km/h",
        )

    return True, None


def _build_fragments(samples_by_lap: dict[int, list[list[dict]]]) -> list[dict]:
    """Flatten samples_by_lap into time-ordered fragment records."""
    fragments: list[dict] = []
    for lap_num, stints in samples_by_lap.items():
        for stint in stints:
            start_time, end_time = _stint_window(stint)
            min_distance, max_distance = _stint_distance_range(stint)
            fragments.append(
                {
                    "lap_num": lap_num,
                    "stint": stint,
                    "sample_count": len(stint),
                    "start_time": start_time,
                    "end_time": end_time,
                    "min_distance_m": min_distance,
                    "max_distance_m": max_distance,
                    "min_speed_kmh": _stint_min_speed(stint),
                }
            )
    fragments.sort(key=lambda f: (f["lap_num"], f["start_time"]))
    return fragments


def _group_into_passes(fragments: list[dict]) -> list[list[dict]]:
    """Group fragments into one group per real pass through the corner.

    Two fragments belong to the same pass only if they are in the same lap and
    their lap_distance ranges are sequential and non-overlapping: the car moves
    forward through the zone exactly once per pass, so a fragment that starts
    beyond where the previous one ended is a continuation (e.g. a spin split
    the samples). Overlapping ranges mean the car re-entered the zone from the
    start, which is a flashback replay and therefore a separate pass.
    """
    passes: list[list[dict]] = []
    current: list[dict] = []
    current_max_distance = 0.0

    for fragment in fragments:
        if not current:
            current = [fragment]
            current_max_distance = fragment["max_distance_m"]
            continue

        same_lap = fragment["lap_num"] == current[-1]["lap_num"]
        sequential = fragment["min_distance_m"] > current_max_distance

        if same_lap and sequential:
            current.append(fragment)
            current_max_distance = max(
                current_max_distance, fragment["max_distance_m"]
            )
        else:
            passes.append(current)
            current = [fragment]
            current_max_distance = fragment["max_distance_m"]

    if current:
        passes.append(current)

    return passes


def _analyze_passes(passes: list[list[dict]]) -> tuple[list[dict], list[dict]]:
    """Turn grouped fragments into valid attempt records plus rejections.

    A pass yields at most one attempt: the earliest fragment that survives
    the validity filter and has a detectable brake onset. Fragments that fail
    are recorded in the rejection list with a reason.
    """
    attempts: list[dict] = []
    rejected: list[dict] = []

    for pass_index, fragments in enumerate(passes, start=1):
        valid_records: list[dict] = []
        pass_rejections: list[dict] = []

        for fragment in fragments:
            rejection = {
                "pass_index": pass_index,
                "lap_num": fragment["lap_num"],
                "sample_count": fragment["sample_count"],
                "min_speed_kmh": fragment["min_speed_kmh"],
                "start_time": fragment["start_time"],
                "end_time": fragment["end_time"],
            }

            is_valid, reason = check_stint_validity(fragment["stint"])
            if not is_valid:
                rejection["reason"] = reason
                pass_rejections.append(rejection)
                continue

            onset = brake_analyzer.find_brake_onset(fragment["stint"])
            if onset is None:
                rejection["reason"] = "no_brake_onset"
                pass_rejections.append(rejection)
                continue

            reapps = brake_analyzer.find_brake_reapplications(fragment["stint"])
            reapplications = [{"distance_m": r["lap_distance"]} for r in reapps]

            valid_records.append(
                {
                    "pass_index": pass_index,
                    "lap_num": fragment["lap_num"],
                    "onset_distance_m": onset["onset_lap_distance"],
                    "onset_speed_kmh": onset["onset_speed"],
                    "onset_session_time": onset["onset_session_time"],
                    "sample_count": fragment["sample_count"],
                    "min_speed_kmh": fragment["min_speed_kmh"],
                    "start_time": fragment["start_time"],
                    "end_time": fragment["end_time"],
                    "reapplication_count": len(reapplications),
                    "reapplications": reapplications,
                }
            )

        pass_kept = bool(valid_records)
        for rejection in pass_rejections:
            rejection["pass_kept"] = pass_kept
        rejected.extend(pass_rejections)

        if valid_records:
            attempt = min(valid_records, key=lambda r: r["start_time"])
            attempt["fragment_count"] = len(fragments)
            attempts.append(attempt)

    return attempts, rejected


def analyze_session(csv_path: str, track_name: str) -> dict:
    """Analyze a session CSV and produce per-corner feedback plus one priority.

    The returned dict has three keys:
      - all_corners: dict mapping corner name to its metrics/feedback.
      - priority_corner: the single highlighted corner.
      - priority_feedback: the human-readable recommendation for that corner.

    Every stint in the session is scored, not just the longest one. Stints are
    grouped into real passes, filtered for validity, and the spread of brake
    onset distances across the surviving attempts is reported alongside a
    single representative attempt used for the feedback text.

    Ranking is unchanged: prefer more brake reapplications first, then break
    ties with larger absolute onset-distance deviation from the configured
    reference (if any). Both are taken from the representative attempt.
    """
    zones = load_track_config(track_name)
    all_corners: dict[str, dict] = {}

    for corner_name, cfg in zones.items():
        zone = cfg["zone"]
        reference = cfg.get("reference")

        samples_by_lap = corner_detector.extract_corner_samples(csv_path, zone)

        fragments = _build_fragments(samples_by_lap)
        passes = _group_into_passes(fragments)
        attempts, rejected = _analyze_passes(passes)

        onset_distances = [a["onset_distance_m"] for a in attempts]

        if len(onset_distances) >= 2:
            onset_variation_m = max(onset_distances) - min(onset_distances)
            onset_stdev_m = statistics.pstdev(onset_distances)
        else:
            # None, not 0.0: "not enough data" must stay distinguishable from
            # "perfectly consistent".
            onset_variation_m = None
            onset_stdev_m = None

        if attempts:
            median_onset = statistics.median(onset_distances)
            representative = min(
                attempts,
                key=lambda a: (
                    abs(a["onset_distance_m"] - median_onset),
                    a["pass_index"],
                ),
            )
        else:
            representative = None

        print(
            f"[DEBUG] corner={corner_name} "
            f"fragments={len(fragments)} passes={len(passes)} "
            f"valid_attempts={len(attempts)} rejected={len(rejected)}"
        )
        if representative is not None:
            print(
                f"[DEBUG] corner={corner_name} REPRESENTATIVE: "
                f"lap={representative['lap_num']} "
                f"onset={representative['onset_distance_m']:.1f}m "
                f"samples={representative['sample_count']} "
                f"(median onset {median_onset:.1f}m)"
            )

        if representative is not None:
            onset_for_coach = {
                "distance_m": representative["onset_distance_m"],
                "speed_kmh": representative["onset_speed_kmh"],
            }

            if reference is not None:
                onset_delta_abs = abs(
                    onset_for_coach["distance_m"] - reference["distance_m"]
                )
            else:
                onset_delta_abs = 0.0

            feedback = coach.generate_corner_feedback(
                corner_name,
                onset_for_coach,
                representative["reapplications"],
                reference=reference,
            )

            all_corners[corner_name] = {
                "status": "ok",
                "valid_attempts": len(attempts),
                "reapplication_count": representative["reapplication_count"],
                "onset_delta_abs": onset_delta_abs,
                "onset_distance_m": onset_for_coach["distance_m"],
                "onset_speed_kmh": onset_for_coach["speed_kmh"],
                "onset_variation_m": onset_variation_m,
                "onset_stdev_m": onset_stdev_m,
                "attempts_detail": attempts,
                "rejected_attempts": rejected,
                "feedback": feedback,
            }
        else:
            all_corners[corner_name] = {
                "status": "no_data",
                "valid_attempts": 0,
                "reapplication_count": 0,
                "onset_delta_abs": 0.0,
                "onset_distance_m": None,
                "onset_speed_kmh": None,
                "onset_variation_m": None,
                "onset_stdev_m": None,
                "attempts_detail": [],
                "rejected_attempts": rejected,
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

        variation = data["onset_variation_m"]
        stdev = data["onset_stdev_m"]
        variation_text = (
            "n/a (needs 2+ valid attempts)"
            if variation is None
            else f"{variation:.1f} m (stdev {stdev:.1f} m)"
        )
        print(
            f"Valid attempts: {data['valid_attempts']} | "
            f"onset variation: {variation_text} | "
            f"rejected fragments: {len(data['rejected_attempts'])}"
        )

    print()
    print("=" * 60)
    print("PRIORITY")
    print("=" * 60)
    print(f"Priority corner: {report['priority_corner']}")
    print()
    print(report["priority_feedback"])
