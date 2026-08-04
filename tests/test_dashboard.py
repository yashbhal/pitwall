"""Dashboard tests. Run: python3 -m unittest tests.test_dashboard -v

No telemetry CSVs and no real analysis are needed: the analyzer is injected as
a stub, so these tests cover only the web and presentation layers.
"""

import os
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src import report_view, session_store
from src.web_app import create_app

REPORT = {
    "all_corners": {
        "Turn 1": {
            "status": "ok",
            "valid_attempts": 3,
            "reapplication_count": 1,
            "reapplication_total": 4,
            "onset_delta_abs": 11.8,
            "onset_distance_m": 774.7,
            "onset_speed_kmh": 330.0,
            "onset_variation_m": 36.4,
            "onset_stdev_m": 15.5,
            "attempts_detail": [],
            "rejected_attempts": [{"reason": "too_few_samples: 4 < 20"}],
            "feedback": "Turn 1: brake onset at 774.7 m.",
            "drill": "Focus: Turn 1 brake consistency.",
        },
        "Roggia": {
            "status": "ok",
            "valid_attempts": 1,
            "reapplication_count": 0,
            "reapplication_total": 0,
            "onset_delta_abs": 0.0,
            "onset_distance_m": 2011.1,
            "onset_speed_kmh": 310.0,
            "onset_variation_m": None,
            "onset_stdev_m": None,
            "attempts_detail": [],
            "rejected_attempts": [],
            "feedback": "Roggia: brake onset at 2011.1 m.",
            "drill": "Not enough data for a Roggia drill yet.",
        },
    },
    "priority_corner": "Turn 1",
    "priority_feedback": "Turn 1: brake onset at 774.7 m.",
    "priority_drill": "Focus: Turn 1 brake consistency.",
}


class SessionStoreTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.session_dir = Path(self._tmp.name)
        (self.session_dir / "b_session.csv").write_text("x", encoding="utf-8")
        (self.session_dir / "a_session.csv").write_text("x", encoding="utf-8")
        (self.session_dir / "notes.txt").write_text("x", encoding="utf-8")
        self.addCleanup(self._tmp.cleanup)

    def test_lists_only_csvs_newest_name_first(self):
        self.assertEqual(
            ["b_session.csv", "a_session.csv"],
            session_store.list_sessions(self.session_dir),
        )

    def test_missing_directory_lists_nothing(self):
        self.assertEqual(
            [], session_store.list_sessions(self.session_dir / "nope")
        )

    def test_resolves_known_session(self):
        self.assertEqual(
            self.session_dir / "a_session.csv",
            session_store.resolve_session("a_session.csv", self.session_dir),
        )

    def test_rejects_traversal_and_unknown_names(self):
        for name in (
            "../../etc/passwd",
            "..",
            "/etc/passwd",
            "sub/a_session.csv",
            "notes.txt",
            "missing.csv",
            "",
        ):
            with self.subTest(name=name):
                with self.assertRaises(session_store.SessionNotFound):
                    session_store.resolve_session(name, self.session_dir)


class SessionDirResolutionTest(unittest.TestCase):
    """The writer and the LED reader must land on the same directory."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_dir = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_defaults_to_checkout_path_without_override(self):
        with unittest.mock.patch.dict(
            os.environ, {}, clear=False
        ) as environ:
            environ.pop(session_store.SESSION_DIR_ENV_VAR, None)
            self.assertEqual(
                session_store.DEFAULT_SESSION_DIR,
                session_store.resolve_session_dir(),
            )

    def test_environment_variable_overrides_default(self):
        with unittest.mock.patch.dict(
            os.environ, {session_store.SESSION_DIR_ENV_VAR: str(self.tmp_dir)}
        ):
            self.assertEqual(
                self.tmp_dir, session_store.resolve_session_dir()
            )

    def test_explicit_argument_wins_over_environment_variable(self):
        with unittest.mock.patch.dict(
            os.environ, {session_store.SESSION_DIR_ENV_VAR: "/not/used"}
        ):
            self.assertEqual(
                self.tmp_dir, session_store.resolve_session_dir(self.tmp_dir)
            )

    def test_blank_environment_variable_is_ignored(self):
        with unittest.mock.patch.dict(
            os.environ, {session_store.SESSION_DIR_ENV_VAR: "   "}
        ):
            self.assertEqual(
                session_store.DEFAULT_SESSION_DIR,
                session_store.resolve_session_dir(),
            )


class ReportViewTest(unittest.TestCase):
    def setUp(self):
        self.view = report_view.build_session_view(
            REPORT, "a_session.csv", "monza"
        )

    def test_unmeasured_variation_is_not_blank_or_zero(self):
        roggia = next(c for c in self.view.corners if c.name == "Roggia")
        self.assertEqual(report_view.NOT_MEASURED, roggia.onset_variation)
        self.assertEqual(report_view.NOT_MEASURED, roggia.onset_stdev)
        self.assertFalse(roggia.is_measured)

    def test_zero_variation_is_shown_as_zero(self):
        corner = report_view.build_corner_view(
            "Turn 1", {"status": "ok", "onset_variation_m": 0.0}, False
        )
        self.assertEqual("0.0 m", corner.onset_variation)
        self.assertTrue(corner.is_measured)

    def test_corner_order_matches_analyzer_order(self):
        self.assertEqual(
            ["Turn 1", "Roggia"], [c.name for c in self.view.corners]
        )

    def test_priority_flag_and_counts(self):
        turn_one = self.view.corners[0]
        self.assertTrue(turn_one.is_priority)
        self.assertEqual(1, turn_one.reapplication_count)
        self.assertEqual(4, turn_one.reapplication_total)
        self.assertEqual(1, turn_one.rejected_count)

    def test_priority_reason_cites_variation(self):
        self.assertIn("36.4 m", self.view.priority_reason)
        self.assertIn("primary ranking signal", self.view.priority_reason)

    def test_priority_reason_without_measured_variation(self):
        report = dict(REPORT, priority_corner="Roggia")
        reason = report_view.build_session_view(
            report, "a_session.csv", "monza"
        ).priority_reason
        self.assertIn("could not be measured", reason)

    def test_no_priority_corner(self):
        report = {
            "all_corners": {},
            "priority_corner": None,
            "priority_feedback": "No valid corner data available.",
            "priority_drill": "No valid corner data available.",
        }
        view = report_view.build_session_view(report, "a.csv", "monza")
        self.assertIn("nothing was ranked", view.priority_reason)


class WebAppTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.session_dir = Path(self._tmp.name)
        (self.session_dir / "a_session.csv").write_text("x", encoding="utf-8")
        self.addCleanup(self._tmp.cleanup)
        self.calls = []

    def client(self, analyzer=None):
        def default_analyzer(csv_path, track_name):
            self.calls.append((csv_path, track_name))
            return REPORT

        app = create_app(
            analyzer=analyzer or default_analyzer,
            session_dir=self.session_dir,
        )
        app.config["TESTING"] = True
        return app.test_client()

    def test_index_lists_sessions(self):
        response = self.client().get("/")
        self.assertEqual(200, response.status_code)
        self.assertIn("a_session.csv", response.get_data(as_text=True))

    def test_report_renders_metrics_and_drill(self):
        response = self.client().get("/sessions/a_session.csv")
        body = response.get_data(as_text=True)
        self.assertEqual(200, response.status_code)
        self.assertIn("36.4 m", body)
        self.assertIn(report_view.NOT_MEASURED, body)
        self.assertIn("Focus: Turn 1 brake consistency.", body)
        self.assertIn("Gear consistency", body)
        self.assertEqual(
            [(str(self.session_dir / "a_session.csv"), "monza")], self.calls
        )

    def test_unknown_session_is_a_readable_404(self):
        response = self.client().get("/sessions/nope.csv")
        self.assertEqual(404, response.status_code)
        self.assertIn("Session not found", response.get_data(as_text=True))

    def test_traversal_attempt_does_not_reach_analyzer(self):
        response = self.client().get("/sessions/..%2F..%2Fetc%2Fpasswd")
        self.assertIn(response.status_code, (404, 400))
        self.assertEqual([], self.calls)

    def test_invalid_track_is_rejected(self):
        response = self.client().get("/sessions/a_session.csv?track=../evil")
        self.assertEqual(400, response.status_code)
        self.assertEqual([], self.calls)

    def test_analyzer_failure_shows_message_not_traceback(self):
        def boom(csv_path, track_name):
            raise ValueError("no thresholds file found")

        response = self.client(analyzer=boom).get("/sessions/a_session.csv")
        body = response.get_data(as_text=True)
        self.assertEqual(500, response.status_code)
        self.assertIn("Analysis failed", body)
        self.assertIn("ValueError: no thresholds file found", body)
        self.assertNotIn("Traceback (most recent call last)", body)


if __name__ == "__main__":
    unittest.main()
