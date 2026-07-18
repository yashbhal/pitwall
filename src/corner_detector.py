import csv
from pathlib import Path

# Placeholder window for Monza Turn 1 (Variante del Rettifilo) braking zone.
# Calibrate against clean lap_distance values once real data is available.
TURN_1_ZONE: tuple[float, float] = (500.0, 750.0)


def is_in_turn1(lap_distance: float) -> bool:
    """Return True if *lap_distance* falls within the Turn 1 zone."""
    start, end = TURN_1_ZONE
    return start <= lap_distance <= end


def extract_turn1_samples(csv_path: str) -> list[dict]:
    """
    Read a session CSV and return telemetry rows (packet_id 6) whose
    nearest preceding LAP row (packet_id 2) has a lap_distance inside
    TURN_1_ZONE. LAP rows that are too old are treated as stale and
    ignored, preventing idle/paused TEL rows from being misclassified.
    """
    STALE_FRAME_THRESHOLD = 5

    path = Path(csv_path)
    samples: list[dict] = []
    stale_excluded = 0
    last_lap_distance: float | None = None
    last_lap_frame: int | None = None

    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
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
                if is_in_turn1(last_lap_distance):
                    samples.append(row)

    print(f"Excluded {stale_excluded} samples due to stale lap_distance")
    return samples
