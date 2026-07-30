from __future__ import annotations

import statistics
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src import brake_analyzer, coach, corner_detector
from config.loader import load_thresholds, load_track_config

# Attempt-validity limits. These stay local constants because they are not part
# of the plan's threshold list in config/thresholds.yaml; the brake and drill
# tuning values are loaded from there.
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


def _analyze_passes(
    passes: list[list[dict]], thresholds: dict
) -> tuple[list[dict], list[dict]]:
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

            onset = brake_analyzer.find_brake_onset(fragment["stint"], thresholds)
            if onset is None:
                rejection["reason"] = "no_sustained_brake_onset"
                pass_rejections.append(rejection)
                continue

            reapps = brake_analyzer.find_brake_reapplications(
                fragment["stint"], thresholds, onset=onset
            )
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


def _priority_key(data: dict) -> tuple[int, float, int, float]:
    """Rank corners worst-consistency-first.

    onset_variation_m is the headline metric in pitwall-plan.md section 11, so
    it leads: a wider spread of brake onsets is a higher priority. Corners
    whose variation could not be measured (fewer than two valid attempts) sort
    below every measured corner rather than being treated as perfectly
    consistent, matching the plan's warning against drawing conclusions from
    too little data. Among those, reapplication_count then onset_delta_abs
    still break the tie.

    Higher key means higher priority, so callers sort descending.
    """
    variation = data["onset_variation_m"]
    return (
        0 if variation is None else 1,
        0.0 if variation is None else variation,
        data["reapplication_count"],
        data["onset_delta_abs"],
    )


def rank_corners(all_corners: dict[str, dict]) -> list[dict]:
    """Order every corner by priority, highest first.

    Corners with a detectable brake onset get ranks 1..N from _priority_key.
    Corners with no valid attempt at all were never ranked before and still
    are not: they carry rank None and trail the list, because there is no
    metric to rank them on. Each entry repeats the three signals the ordering
    was decided by so a caller can explain a rank without re-deriving it.

    The sort is stable and descending, so corners with identical keys keep
    their track-config order and entry 1 is the same corner the previous
    max()-based selection returned.
    """
    ok_names = [
        name for name, data in all_corners.items() if data["status"] == "ok"
    ]
    ok_names.sort(key=lambda name: _priority_key(all_corners[name]), reverse=True)

    entries = [
        {
            "corner": name,
            "rank": position,
            "status": all_corners[name]["status"],
            "onset_variation_m": all_corners[name]["onset_variation_m"],
            "reapplication_count": all_corners[name]["reapplication_count"],
            "onset_delta_abs": all_corners[name]["onset_delta_abs"],
        }
        for position, name in enumerate(ok_names, start=1)
    ]

    entries.extend(
        {
            "corner": name,
            "rank": None,
            "status": data["status"],
            "onset_variation_m": data["onset_variation_m"],
            "reapplication_count": data["reapplication_count"],
            "onset_delta_abs": data["onset_delta_abs"],
        }
        for name, data in all_corners.items()
        if data["status"] != "ok"
    )

    return entries


def analyze_session(csv_path: str, track_name: str) -> dict:
    """Analyze a session CSV and produce per-corner feedback plus one priority.

    The returned dict has these keys:
      - all_corners: dict mapping corner name to its metrics/feedback.
      - ranked_corners: every corner as {corner, rank, ...ranking signals},
        ordered highest priority first; see rank_corners.
      - priority_corner: the single highlighted corner, i.e. rank 1.
      - priority_feedback: the human-readable recommendation for that corner.
      - priority_drill: the drill for that corner.

    Every stint in the session is scored, not just the longest one. Stints are
    grouped into real passes, filtered for validity, and the spread of brake
    onset distances across the surviving attempts is reported alongside a
    single representative attempt used for the feedback text.

    Ranking prefers the corner with the widest brake onset variation, since
    that is the headline consistency metric. Corners whose variation could not
    be measured rank last; reapplication_count and absolute onset-distance
    deviation from the configured reference remain as tiebreakers.
    """
    zones = load_track_config(track_name)
    thresholds = load_thresholds()
    minimum_valid_attempts = int(thresholds["minimum_valid_attempts_for_drill"])
    variation_warning_m = float(thresholds["brake_variation_warning_meters"])

    # Parse the CSV once and share the rows across every zone. Each corner used
    # to re-read the whole file, so an N-corner track cost N full parses.
    rows = corner_detector.read_session_rows(csv_path)
    all_corners: dict[str, dict] = {}

    for corner_name, cfg in zones.items():
        zone = cfg["zone"]
        reference = cfg.get("reference")

        samples_by_lap = corner_detector.extract_corner_samples(
            csv_path, zone, rows=rows
        )

        fragments = _build_fragments(samples_by_lap)
        passes = _group_into_passes(fragments)
        attempts, rejected = _analyze_passes(passes, thresholds)

        onset_distances = [a["onset_distance_m"] for a in attempts]
        reapplication_total = sum(a["reapplication_count"] for a in attempts)

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

            corner_metrics = {
                "status": "ok",
                "valid_attempts": len(attempts),
                "reapplication_count": representative["reapplication_count"],
                "reapplication_total": reapplication_total,
                "onset_delta_abs": onset_delta_abs,
                "onset_distance_m": onset_for_coach["distance_m"],
                "onset_speed_kmh": onset_for_coach["speed_kmh"],
                "onset_variation_m": onset_variation_m,
                "onset_stdev_m": onset_stdev_m,
                "attempts_detail": attempts,
                "rejected_attempts": rejected,
                "feedback": feedback,
            }
            corner_metrics["drill"] = coach.generate_drill(
                corner_name,
                corner_metrics,
                minimum_valid_attempts=minimum_valid_attempts,
                variation_warning_m=variation_warning_m,
            )
            all_corners[corner_name] = corner_metrics
        else:
            all_corners[corner_name] = {
                "status": "no_data",
                "valid_attempts": 0,
                "reapplication_count": 0,
                "reapplication_total": 0,
                "onset_delta_abs": 0.0,
                "onset_distance_m": None,
                "onset_speed_kmh": None,
                "onset_variation_m": None,
                "onset_stdev_m": None,
                "attempts_detail": [],
                "rejected_attempts": rejected,
                "feedback": None,
                "drill": None,
            }

    ranked_corners = rank_corners(all_corners)
    ranked_with_data = [e for e in ranked_corners if e["rank"] is not None]

    if ranked_with_data:
        priority_corner = ranked_with_data[0]["corner"]
        priority_feedback = all_corners[priority_corner]["feedback"]
        priority_drill = all_corners[priority_corner]["drill"]
    else:
        priority_corner = None
        priority_feedback = "No valid corner data available."
        priority_drill = "No valid corner data available."

    return {
        "all_corners": all_corners,
        "ranked_corners": ranked_corners,
        "priority_corner": priority_corner,
        "priority_feedback": priority_feedback,
        "priority_drill": priority_drill,
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
            f"reapplications: {data['reapplication_total']} | "
            f"rejected fragments: {len(data['rejected_attempts'])}"
        )

    print()
    print("=" * 60)
    print("RANKED CORNERS")
    print("=" * 60)
    for entry in report["ranked_corners"]:
        rank = "-" if entry["rank"] is None else str(entry["rank"])
        variation = entry["onset_variation_m"]
        variation_text = (
            "n/a (needs 2+ valid attempts)"
            if variation is None
            else f"{variation:.1f} m"
        )
        print(
            f"  #{rank:<3} {entry['corner']:<12} "
            f"variation={variation_text:<30} "
            f"reapplications={entry['reapplication_count']} "
            f"onset_delta_abs={entry['onset_delta_abs']:.1f} m "
            f"[{entry['status']}]"
        )

    print()
    print("=" * 60)
    print("PRIORITY")
    print("=" * 60)
    print(f"Priority corner: {report['priority_corner']}")
    print()
    print(report["priority_feedback"])
    print()
    print("-" * 60)
    print("DRILL")
    print("-" * 60)
    print(report["priority_drill"])
