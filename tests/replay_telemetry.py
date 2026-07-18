import argparse
import csv
import time
from pathlib import Path


def format_lap_time(ms):
    """Format milliseconds as M:SS.mmm (matches udp_listener.py)."""
    if not ms or str(ms).strip() == "":
        return "--:--.---"
    total_ms = int(float(str(ms).strip()))
    minutes = total_ms // 60000
    remainder = total_ms % 60000
    seconds = remainder // 1000
    millis = remainder % 1000
    return f"{minutes}:{seconds:02d}.{millis:03d}"


def print_row(row):
    """Print a CSV row using the same LAP/TEL summary style as udp_listener.py."""
    packet_id = int(float(row.get("packet_id") or 0))
    session_time = float(row.get("session_time") or 0)
    frame = int(float(row.get("frame_identifier") or 0))

    summary = (
        f"id={packet_id} "
        f"time={session_time:.3f} "
        f"frame={frame}"
    )

    if packet_id == 2:
        dist = float(row.get("lap_distance") or 0)
        lap = row.get("current_lap_num") or ""
        pos = row.get("car_position") or ""
        print(
            f"{summary} | LAP dist={dist:.2f} "
            f"lap={lap} pos={pos}"
        )
    elif packet_id == 6:
        speed = float(row.get("speed") or 0)
        throttle = float(row.get("throttle") or 0)
        brake = float(row.get("brake") or 0)
        steer = float(row.get("steer") or 0)
        gear = row.get("gear") or ""
        rpm = row.get("engine_rpm") or ""
        print(
            f"{summary} | TEL speed={speed:.0f} "
            f"throttle={throttle:.2f} brake={brake:.2f} "
            f"steer={steer:.2f} gear={gear} rpm={rpm}"
        )
    else:
        print(summary)


def main():
    parser = argparse.ArgumentParser(
        description="Replay a raw F1 25 telemetry CSV from data/raw/."
    )
    parser.add_argument(
        "csv_path",
        type=Path,
        help="Path to the CSV file to replay",
    )
    args = parser.parse_args()

    if not args.csv_path.is_file():
        raise SystemExit(f"File not found: {args.csv_path}")

    with open(args.csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        prev_time = None

        for row in reader:
            session_time = float(row.get("session_time") or 0)

            if prev_time is not None:
                gap = session_time - prev_time
                if gap > 0:
                    time.sleep(gap)

            prev_time = session_time
            print_row(row)


if __name__ == "__main__":
    main()
