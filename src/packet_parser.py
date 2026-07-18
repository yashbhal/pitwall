import struct

# F1 25 UDP spec v3 — PacketHeader is 29 bytes, little endian.
# byte offsets: packetFormat=0, gameYear=2, packetVersion=5, packetId=6,
#               sessionUID=7, sessionTime=15, frameIdentifier=19, playerCarIndex=27

def parse_header(data: bytes):
    (
        packet_format,
        game_year,
        _game_major_version,
        _game_minor_version,
        packet_version,
        packet_id,
        session_uid,
        session_time,
        frame_identifier,
        _overall_frame_identifier,
        player_car_index,
        _secondary_player_car_index,
    ) = struct.unpack("<HBBBBBQfIIBB", data[:29])
    return {
        "packetFormat": packet_format,
        "gameYear": game_year,
        "packetVersion": packet_version,
        "packetId": packet_id,
        "sessionUID": session_uid,
        "sessionTime": session_time,
        "frameIdentifier": frame_identifier,
        "playerCarIndex": player_car_index,
    }


# F1 25 UDP spec v3 — LapData is 57 bytes per car.
LAP_DATA_SIZE = 57
# Offsets for the fields we need: lastLapTimeInMS=0, currentLapTimeInMS=4,
# lapDistance=20, carPosition=32, currentLapNum=33.
_LAP_DATA_FMT = "<IIHBBHBBHBBfffBB"
_LAP_DATA_FIELDS = [
    "lastLapTimeInMS", "currentLapTimeInMS",
    "_sector1TimeMSPart", "_sector1TimeMinutesPart",
    "_sector2TimeMSPart", "_sector2TimeMinutesPart",
    "_deltaToCarInFrontMSPart", "_deltaToCarInFrontMinutesPart",
    "_deltaToRaceLeaderMSPart", "_deltaToRaceLeaderMinutesPart",
    "lapDistance", "_totalDistance", "_safetyCarDelta",
    "carPosition", "currentLapNum",
]

def parse_lap_data(data: bytes, player_car_index: int):
    start = 29 + player_car_index * LAP_DATA_SIZE
    values = struct.unpack_from(_LAP_DATA_FMT, data, start)
    return dict(zip(_LAP_DATA_FIELDS, values))


# F1 25 UDP spec v3 — CarTelemetryData is 60 bytes per car.
CAR_TELEMETRY_SIZE = 60
# Offsets for the fields we need: speed=0, throttle=2, steer=6, brake=10,
# gear=15, engineRPM=16.
_CAR_TELEMETRY_FMT = "<HfffBbH"
_CAR_TELEMETRY_FIELDS = [
    "speed", "throttle", "steer", "brake",
    "_clutch", "gear", "engineRPM",
]

def parse_car_telemetry(data: bytes, player_car_index: int):
    start = 29 + player_car_index * CAR_TELEMETRY_SIZE
    values = struct.unpack_from(_CAR_TELEMETRY_FMT, data, start)
    return dict(zip(_CAR_TELEMETRY_FIELDS, values))
