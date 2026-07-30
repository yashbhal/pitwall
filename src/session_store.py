"""Discovery of recorded session CSVs.

The only module that knows where session recordings live on disk. Keeping
resolution here means the web layer never builds a filesystem path from user
input itself.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SESSION_DIR = PROJECT_ROOT / "data" / "raw"
SESSION_SUFFIX = ".csv"


class SessionNotFound(Exception):
    """Raised when a requested session name is not an available recording."""


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
