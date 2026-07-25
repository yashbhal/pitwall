import importlib


def load_track_config(track_name: str) -> dict:
    """Load a track's TURN_ZONES dict from config.<track_name>.

    This is the only place that should know how config files are loaded.
    corner_detector.py and coach.py must never import config modules directly.
    """
    module_name = f"config.{track_name}"
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        raise ValueError(f"No track config found for '{track_name}'") from exc

    return module.TURN_ZONES
