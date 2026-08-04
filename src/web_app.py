"""Read-only Flask dashboard for recorded PitWall sessions.

Renders src.session_analyzer.analyze_session() output. No analysis happens
here: the view layer formats what the analyzer returns and nothing more.
Static render per page load; there is no live data source.
"""

from __future__ import annotations

import os
import re
import sys
import traceback
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask, render_template, request

from src import session_store
from src.report_view import build_session_view
from src.session_analyzer import analyze_session

DEFAULT_TRACK = "monza"

# Port 5000 is taken by AirPlay Receiver on macOS, so default to 5001 and allow
# an override for the UNO Q.
DEFAULT_PORT = 5001

# load_track_config() feeds this into importlib.import_module, so restrict it to
# a plain module-name shape before it ever gets there.
TRACK_NAME_PATTERN = re.compile(r"[a-z0-9_]{1,40}")


def create_app(
    analyzer=analyze_session,
    session_dir: Path | None = None,
    default_track: str = DEFAULT_TRACK,
) -> Flask:
    """Build the dashboard app.

    *analyzer* and *session_dir* are injected so routes can be tested without
    real telemetry CSVs. Left unset, the recording directory is resolved the
    same way the logger and LED client resolve it.
    """
    session_dir = session_store.resolve_session_dir(session_dir)
    app = Flask(__name__)

    def render_error(title: str, detail: str, status: int):
        return (
            render_template("error.html", title=title, detail=detail),
            status,
        )

    @app.route("/")
    def index():
        return render_template(
            "index.html",
            sessions=session_store.list_sessions(session_dir),
            session_dir=session_dir,
            track_name=default_track,
        )

    @app.route("/sessions/<filename>")
    def session_report(filename: str):
        try:
            csv_path = session_store.resolve_session(filename, session_dir)
        except session_store.SessionNotFound:
            return render_error(
                "Session not found",
                f"There is no recording named {filename!r} in {session_dir}.",
                404,
            )

        track_name = request.args.get("track", default_track)
        if not TRACK_NAME_PATTERN.fullmatch(track_name):
            return render_error(
                "Invalid track name",
                f"{track_name!r} is not a valid track name. Track names are "
                f"lowercase letters, digits and underscores.",
                400,
            )

        try:
            report = analyzer(str(csv_path), track_name)
        except Exception as exc:  # analysis has known rough edges
            traceback.print_exc()
            return render_error(
                "Analysis failed",
                f"{type(exc).__name__}: {exc}\n\n"
                f"The full traceback was printed to the server console.",
                500,
            )

        view = build_session_view(report, filename, track_name)
        return render_template("session.html", view=view)

    @app.errorhandler(404)
    def not_found(_error):
        return render_error("Page not found", "No such page.", 404)

    return app


if __name__ == "__main__":
    # host=0.0.0.0 so the dashboard is reachable from a phone/laptop on the
    # same network as the UNO Q, per pitwall-plan.md section 14.
    create_app().run(
        host=os.environ.get("PITWALL_HOST", "0.0.0.0"),
        port=int(os.environ.get("PITWALL_PORT", DEFAULT_PORT)),
        debug=False,
    )
