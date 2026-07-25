"""Ad-hoc scratch script — NOT part of the permanent codebase.

Prints raw TEL (packet_id=6) samples in a wide provisional lap_distance
window around Roggia, so we can eyeball real brake/speed data and find the
actual brake onset distance (same manual process used to calibrate Turn 1).

Note: TEL rows don't carry lap_distance directly in the CSV (only LAP rows,
packet_id=2, do — see src/session_logger.py). This script forward-fills the
most recent LAP row's lap_distance/current_lap_num onto each TEL row, same
approach as src/corner_detector.extract_corner_samples.

Usage:
    python tests/scratch_roggia_zone.py <path_to_session_csv>
"""

import csv
import sys

ZONE_START_M = 1650
ZONE_END_M = 2200


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python tests/scratch_roggia_zone.py <path_to_session_csv>")

    csv_path = sys.argv[1]

    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    last_lap_distance = None
    last_lap_num = None
    printed = 0

    for row in rows:
        packet_id = row.get("packet_id", "").strip()

        if packet_id == "2":
            lap_distance_raw = row.get("lap_distance", "").strip()
            if lap_distance_raw:
                try:
                    last_lap_distance = float(lap_distance_raw)
                except ValueError:
                    continue
                lap_num_raw = row.get("current_lap_num", "").strip()
                if lap_num_raw:
                    try:
                        last_lap_num = int(float(lap_num_raw))
                    except ValueError:
                        last_lap_num = None
            continue

        if packet_id != "6" or last_lap_distance is None:
            continue

        if ZONE_START_M <= last_lap_distance <= ZONE_END_M:
            session_time = row.get("session_time", "")
            speed = row.get("speed", "")
            brake = row.get("brake", "")
            print(
                f"t={session_time}  lap_distance={last_lap_distance:.2f}  "
                f"speed={speed}  brake={brake}  current_lap_num={last_lap_num}"
            )
            printed += 1

    print(f"\nPrinted {printed} TEL rows in [{ZONE_START_M}, {ZONE_END_M}] m")


if __name__ == "__main__":
    main()
