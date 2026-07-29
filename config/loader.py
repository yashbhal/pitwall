import importlib
from functools import lru_cache
from pathlib import Path

THRESHOLDS_PATH = Path(__file__).resolve().parent / "thresholds.yaml"


def _parse_scalar(raw: str) -> int | float | str:
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        return raw[1:-1]
    return raw


def _parse_flat_yaml(text: str, source: str) -> dict[str, int | float | str]:
    """Parse a flat 'key: scalar' config file.

    Deliberately minimal so the UNO Q does not need PyYAML installed. Only
    top-level scalar keys are supported; indentation, lists and nested maps
    raise instead of being silently misread.
    """
    values: dict[str, int | float | str] = {}

    for lineno, line in enumerate(text.splitlines(), start=1):
        content = line.split("#", 1)[0].rstrip()
        if not content.strip():
            continue

        if content[0].isspace():
            raise ValueError(
                f"{source}:{lineno}: indented lines are not supported; "
                f"only flat 'key: value' pairs can be parsed"
            )

        if content.lstrip().startswith("- "):
            raise ValueError(
                f"{source}:{lineno}: list items are not supported; "
                f"only flat 'key: value' pairs can be parsed"
            )

        key, separator, raw = content.partition(":")
        key = key.strip()
        raw = raw.strip()

        if not separator or not key:
            raise ValueError(f"{source}:{lineno}: expected 'key: value', got {line!r}")

        if not raw:
            raise ValueError(
                f"{source}:{lineno}: key '{key}' has no scalar value; "
                f"nested maps are not supported"
            )

        if key in values:
            raise ValueError(f"{source}:{lineno}: duplicate key '{key}'")

        values[key] = _parse_scalar(raw)

    return values


@lru_cache(maxsize=1)
def _cached_thresholds() -> dict[str, int | float | str]:
    if not THRESHOLDS_PATH.exists():
        raise ValueError(f"No thresholds file found at {THRESHOLDS_PATH}")
    return _parse_flat_yaml(
        THRESHOLDS_PATH.read_text(encoding="utf-8"), THRESHOLDS_PATH.name
    )


def load_thresholds() -> dict[str, int | float | str]:
    """Load config/thresholds.yaml as a dict of tuning constants.

    This is the only place that should know where thresholds live. Returns a
    fresh copy each call so callers cannot mutate the cached parse.
    """
    return dict(_cached_thresholds())


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
