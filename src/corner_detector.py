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
    TURN_1_ZONE.
    """
    path = Path(csv_path)
    samples: list[dict] = []
    last_lap_distance: float | None = None

    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            packet_id = row.get("packet_id", "").strip()
            lap_distance_raw = row.get("lap_distance", "").strip()

            if packet_id == "2" and lap_distance_raw:
                try:
                    last_lap_distance = float(lap_distance_raw)
                except ValueError:
                    continue

            if packet_id == "6" and last_lap_distance is not None:
                if is_in_turn1(last_lap_distance):
                    samples.append(row)

    return samples
