"""Discovery of recorded session CSVs.

The only module that knows where session recordings live on disk. Keeping
resolution here means the web layer never builds a filesystem path from user
input itself.
"""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SESSION_DIR = PROJECT_ROOT / "data" / "raw"
SESSION_SUFFIX = ".csv"

SESSION_DIR_ENV_VAR = "PITWALL_SESSION_DIR"


class SessionNotFound(Exception):
    """Raised when a requested session name is not an available recording."""


def resolve_session_dir(explicit: Path | str | None = None) -> Path:
    """Return the recording directory, preferring the most specific source.

    Order is explicit argument, then ``PITWALL_SESSION_DIR``, then the path
    beside this checkout. The writer (``session_logger.py``) and the readers
    (``bridge_client.py``, the dashboard) all resolve through here, so pointing
    them at a shared directory is one environment variable rather than a
    coincidence of which copy of the code is running -- which matters on the
    UNO Q, where the LED App runs in a container that only sees its own App
    folder.
    """
    if explicit is not None:
        return Path(explicit).expanduser()

    from_env = os.environ.get(SESSION_DIR_ENV_VAR, "").strip()
    if from_env:
        return Path(from_env).expanduser()

    return DEFAULT_SESSION_DIR


def list_sessions(session_dir: Path = DEFAULT_SESSION_DIR) -> list[str]:
    """Return available session file names, newest-looking name first.

    Names are sorted in reverse so the timestamp-prefixed recordings
    (``2026-07-28_032105_session.csv``) come out most-recent-first without
    hitting the filesystem for mtimes.
    """
    if not session_dir.is_dir():
        return []

    return sorted(
        (
            entry.name
            for entry in session_dir.iterdir()
            if entry.is_file() and entry.suffix == SESSION_SUFFIX
        ),
        reverse=True,
    )


def resolve_session(
    filename: str, session_dir: Path = DEFAULT_SESSION_DIR
) -> Path:
    """Resolve *filename* to a path inside *session_dir*.

    The name must match an entry in :func:`list_sessions` exactly. Whitelisting
    against the real directory listing is what makes traversal (``../``),
    absolute paths and nested paths unreachable, rather than trying to sanitize
    the string.
    """
    if filename not in set(list_sessions(session_dir)):
        raise SessionNotFound(f"No session recording named {filename!r}")

    return session_dir / filename
