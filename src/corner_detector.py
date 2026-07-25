import csv
from pathlib import Path


def extract_corner_samples(
    csv_path: str, zone: tuple[float, float]
) -> dict[int, list[list[dict]]]:
    """
    Read a session CSV, print a TEL idle-row summary and non-idle stint
    boundaries, then return telemetry rows (packet_id 6) grouped by lap
    number whose nearest preceding LAP row (packet_id 2) has a
    lap_distance inside *zone*. LAP rows that are too old are treated
    as stale and ignored, preventing idle/paused TEL rows from being
    misclassified.

    Within each lap, samples are further split into contiguous stints
    based on session_time gaps larger than MAX_GAP_SECONDS. This handles
    flashbacks/restarts where the same lap_num appears in multiple
    non-contiguous windows.
    """
    STALE_FRAME_THRESHOLD = 5
    IDLE_ZERO_THRESHOLD = 20
    MAX_GAP_SECONDS = 2.0

    path = Path(csv_path)
    with path.open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # --- TEL idle-row summary --------------------------------------------
    tel_points: list[tuple[float, float]] = []
    idle_rows = 0
    for row in rows:
        if row.get("packet_id", "").strip() != "6":
            continue

        try:
            speed = float(row.get("speed") or 0)
        except ValueError:
            speed = 0.0
        try:
            session_time = float(row.get("session_time") or 0)
        except ValueError:
            session_time = 0.0

        if speed == 0.0:
            idle_rows += 1
        tel_points.append((session_time, speed))

    # --- Group TEL rows into non-idle stints ----------------------------
    stints: list[dict] = []
    current_start: float | None = None
    last_nonzero_time: float | None = None
    zero_count = 0

    for session_time, speed in tel_points:
        if speed != 0.0:
            if zero_count > IDLE_ZERO_THRESHOLD and current_start is not None:
                if last_nonzero_time is not None:
                    stints.append({"start": current_start, "end": last_nonzero_time})
                current_start = None
            if current_start is None:
                current_start = session_time
            zero_count = 0
            last_nonzero_time = session_time
        else:
            zero_count += 1
            if zero_count > IDLE_ZERO_THRESHOLD and current_start is not None:
                if last_nonzero_time is not None:
                    stints.append({"start": current_start, "end": last_nonzero_time})
                current_start = None

    if current_start is not None and last_nonzero_time is not None:
        stints.append({"start": current_start, "end": last_nonzero_time})

    print(f"\nTotal idle rows skipped: {idle_rows}")
    print(f"Found {len(stints)} non-idle stint(s)")
    for i, stint in enumerate(stints, start=1):
        print(
            f"  stint {i}: start={stint['start']:.3f}s, end={stint['end']:.3f}s"
        )
    print()

    # --- Corner extraction (distance + lap group) -------------------------
    samples_by_lap: dict[int, list[dict]] = {}
    stale_excluded = 0
    start, end = zone
    last_lap_distance: float | None = None
    last_lap_num: int | None = None
    last_lap_frame: int | None = None

    for row in rows:
        packet_id = row.get("packet_id", "").strip()
        lap_distance_raw = row.get("lap_distance", "").strip()
        frame_raw = row.get("frame_identifier", "").strip()

        try:
            frame = int(float(frame_raw)) if frame_raw else None
        except ValueError:
            frame = None

        if packet_id == "2" and lap_distance_raw:
            try:
                last_lap_distance = float(lap_distance_raw)
                lap_num_raw = row.get("current_lap_num", "").strip()
                if lap_num_raw:
                    last_lap_num = int(float(lap_num_raw))
                last_lap_frame = frame
            except ValueError:
                continue

        if packet_id == "6" and last_lap_distance is not None:
            if frame is None or last_lap_frame is None:
                stale_excluded += 1
                continue
            if abs(frame - last_lap_frame) > STALE_FRAME_THRESHOLD:
                stale_excluded += 1
                continue

            try:
                speed = float(row.get("speed") or 0)
            except ValueError:
                speed = 0.0

            # Drop idle/stationary rows regardless of zone match
            if speed < 5.0:
                continue

            if start <= last_lap_distance <= end and last_lap_num is not None:
                annotated = dict(row)
                annotated["lap_distance"] = last_lap_distance
                samples_by_lap.setdefault(last_lap_num, []).append(annotated)

    print(f"Excluded {stale_excluded} samples due to stale lap_distance")

    # --- Split each lap into contiguous stints -----------------------------
    for lap_num in samples_by_lap:
        rows = sorted(
            samples_by_lap[lap_num],
            key=lambda r: float(r.get("session_time") or 0),
        )
        stints_for_lap: list[list[dict]] = []
        current_stint: list[dict] = []
        for r in rows:
            t = float(r.get("session_time") or 0)
            if not current_stint:
                current_stint.append(r)
                continue
            prev_t = float(current_stint[-1].get("session_time") or 0)
            if t - prev_t > MAX_GAP_SECONDS:
                stints_for_lap.append(current_stint)
                current_stint = [r]
            else:
                current_stint.append(r)
        if current_stint:
            stints_for_lap.append(current_stint)
        samples_by_lap[lap_num] = stints_for_lap

    print("\nCorner samples per lap (split into stints):")
    for lap_num in sorted(samples_by_lap):
        stints = samples_by_lap[lap_num]
        total = sum(len(s) for s in stints)
        print(f"  lap {lap_num}: {len(stints)} stint(s), {total} samples")
        for i, stint in enumerate(stints, start=1):
            times: list[float] = []
            speeds: list[float] = []
            for r in stint:
                try:
                    t = float(r.get("session_time") or 0)
                except ValueError:
                    t = 0.0
                times.append(t)

                try:
                    s = float(r.get("speed") or 0)
                except ValueError:
                    s = 0.0
                speeds.append(s)

            start_time = min(times) if times else 0.0
            end_time = max(times) if times else 0.0
            min_speed = min(speeds) if speeds else 0.0
            max_speed = max(speeds) if speeds else 0.0

            idle_flag = " --- contains idle rows -- investigate" if min_speed == 0.0 else ""
            print(
                f"    stint {i}: {len(stint)} samples, "
                f"t={start_time:.3f}s -> {end_time:.3f}s, "
                f"speed {min_speed:.1f} -> {max_speed:.1f}{idle_flag}"
            )

    # --- Lap 2 traces ------------------------------------------------------
    if 2 in samples_by_lap:
        for i, stint in enumerate(samples_by_lap[2], start=1):
            print(f"\nLap 2 stint {i} session_time / lap_distance trace:")
            for r in stint:
                try:
                    t = float(r.get("session_time") or 0)
                except ValueError:
                    t = 0.0
                try:
                    lap_dist = float(r.get("lap_distance", 0.0))
                except (ValueError, TypeError):
                    lap_dist = 0.0
                print(f"  {t:.3f}s  {lap_dist:.2f}m")

    return samples_by_lap
