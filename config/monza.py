# Monza corner zone boundaries in lap_distance meters.
#
# This file holds only Monza's TURN_ZONES dict, calibrated from real driving
# data. New tracks should get their own config file (e.g. config/silverstone.py)
# with the same TURN_ZONES dict shape; config.loader.load_track_config is the
# single place that knows how to load them.

TURN_ZONES = {
    "Turn 1": {
        "zone": (700.0, 950.0),  # calibrated from real brake onset at
                                  # ~786.5m across two passes (clean +
                                  # messy), see pitwall-plan.md section 20
        "reference": None,
    },
    "Roggia": {
        # calibrated from real driving data; clean pass onset ~2018.4m @ 313 km/h
        # (segment 2, t=596.044s), messy pass first threshold crossing ~1787.6m
        # @ 304 km/h with a spin/full-stop ~2060.8m (segment 1, t=536.419-545.344s);
        # both passes from data/raw/2026-07-18_211538_session.csv
        "zone": (1650.0, 2200.0),
        "reference": {"distance_m": 2018.0, "speed_kmh": 313.0},
    },
}
