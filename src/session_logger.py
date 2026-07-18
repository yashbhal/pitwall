import csv
import datetime
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

SESSION_TIMESTAMP = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
CSV_PATH = RAW_DIR / f"{SESSION_TIMESTAMP}_session.csv"

COLUMNS = [
    "timestamp", "packet_id", "session_time", "frame_identifier",
    "lap_distance", "current_lap_num", "car_position",
    "speed", "throttle", "brake", "steer", "gear", "engine_rpm",
]

_file = open(CSV_PATH, "w", newline="", encoding="utf-8")
_writer = csv.DictWriter(_file, fieldnames=COLUMNS)
_writer.writeheader()
_rows_written = 0
_last_header = {}


def record_header(header: dict):
    _last_header.clear()
    _last_header.update(header)


def _maybe_flush():
    global _rows_written
    _rows_written += 1
    if _rows_written % 50 == 0:
        _file.flush()


def log_row(parsed_lap_data: dict | None, parsed_telemetry: dict | None):
    if not _last_header:
        return

    row = {
        "timestamp": datetime.datetime.now().isoformat(),
        "packet_id": _last_header["packetId"],
        "session_time": _last_header["sessionTime"],
        "frame_identifier": _last_header["frameIdentifier"],
        "lap_distance": parsed_lap_data.get("lapDistance") if parsed_lap_data else "",
        "current_lap_num": parsed_lap_data.get("currentLapNum") if parsed_lap_data else "",
        "car_position": parsed_lap_data.get("carPosition") if parsed_lap_data else "",
        "speed": parsed_telemetry.get("speed") if parsed_telemetry else "",
        "throttle": parsed_telemetry.get("throttle") if parsed_telemetry else "",
        "brake": parsed_telemetry.get("brake") if parsed_telemetry else "",
        "steer": parsed_telemetry.get("steer") if parsed_telemetry else "",
        "gear": parsed_telemetry.get("gear") if parsed_telemetry else "",
        "engine_rpm": parsed_telemetry.get("engineRPM") if parsed_telemetry else "",
    }
    _writer.writerow(row)
    _maybe_flush()
