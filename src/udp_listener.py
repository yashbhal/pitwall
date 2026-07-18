import socket
from pathlib import Path
from packet_parser import parse_header, parse_lap_data, parse_car_telemetry
import session_logger

CONFIG = Path(__file__).resolve().parent.parent / "config" / "network.yaml"


def load_udp_port():
    for line in CONFIG.read_text().splitlines():
        if line.startswith("udp_port:"):
            return int(line.split(":", 1)[1].strip())
    raise ValueError("udp_port not found in config/network.yaml")


def main():
    port = load_udp_port()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", port))
    print(f"Listening for F1 25 UDP telemetry on port {port}...")
    _dumped_lap = False

    while True:
        data, addr = sock.recvfrom(2048)
        header = parse_header(data)
        session_logger.record_header(header)
        summary = (
            f"{addr[0]}:{addr[1]} | id={header['packetId']} | "
            f"format={header['packetFormat']} year={header['gameYear']} | "
            f"time={header['sessionTime']:.3f} frame={header['frameIdentifier']} | "
            f"player={header['playerCarIndex']}"
        )

        if header["packetId"] == 2:
            lap = parse_lap_data(data, header["playerCarIndex"])
            if not _dumped_lap:
                print(f"LAP HEX first 40 bytes: {data[29:69].hex()}")
                _dumped_lap = True
            print(
                f"{summary} | LAP dist={lap['lapDistance']:.2f} "
                f"lap={lap['currentLapNum']} pos={lap['carPosition']} "
                f"last={lap['lastLapTimeInMS']} cur={lap['currentLapTimeInMS']}"
            )
            session_logger.log_row(lap, None)
        elif header["packetId"] == 6:
            tel = parse_car_telemetry(data, header["playerCarIndex"])
            print(
                f"{summary} | TEL speed={tel['speed']} "
                f"throttle={tel['throttle']:.2f} brake={tel['brake']:.2f} "
                f"steer={tel['steer']:.2f} gear={tel['gear']} rpm={tel['engineRPM']}"
            )
            session_logger.log_row(None, tel)
        else:
            print(summary)


if __name__ == "__main__":
    main()
