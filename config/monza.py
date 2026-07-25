# Monza corner zone boundaries in lap_distance meters.
#
# This file holds only Monza's TURN_ZONES dict, calibrated from real driving
# data. New tracks should get their own config file (e.g. config/silverstone.py)
# with the same TURN_ZONES dict shape; config.loader.load_track_config is the
# single place that knows how to load them.

TURN_ZONES = {
    "Turn 1": (700.0, 950.0),  # calibrated from real brake onset at
                               # ~786.5m across two passes (clean +
                               # messy), see pitwall-plan.md section 20
}
