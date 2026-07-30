"""Corner ranking tests. Run: python3 -m unittest tests.test_ranking -v

Covers src.session_analyzer.rank_corners in isolation: no CSVs, no analysis.
These pin the ordering contract so the dashboard can trust rank numbers.
"""

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.session_analyzer import rank_corners


def corner(
    variation=None, reapplications=0, delta_abs=0.0, status="ok"
) -> dict:
    return {
        "status": status,
        "onset_variation_m": variation,
        "reapplication_count": reapplications,
        "onset_delta_abs": delta_abs,
    }


def names(entries) -> list:
    return [e["corner"] for e in entries]


def ranks(entries) -> dict:
    return {e["corner"]: e["rank"] for e in entries}


class RankCornersTest(unittest.TestCase):
    def test_widest_variation_ranks_first(self):
        entries = rank_corners(
            {
                "Roggia": corner(variation=8.5),
                "Turn 1": corner(variation=32.2),
                "Lesmo 1": corner(variation=18.3),
            }
        )
        self.assertEqual(["Turn 1", "Lesmo 1", "Roggia"], names(entries))
        self.assertEqual([1, 2, 3], [e["rank"] for e in entries])

    def test_unmeasured_variation_ranks_below_every_measured_corner(self):
        entries = rank_corners(
            {
                "Roggia": corner(variation=None, reapplications=9),
                "Turn 1": corner(variation=0.0),
            }
        )
        self.assertEqual(["Turn 1", "Roggia"], names(entries))
        self.assertEqual({"Turn 1": 1, "Roggia": 2}, ranks(entries))

    def test_reapplications_break_a_variation_tie(self):
        entries = rank_corners(
            {
                "Turn 1": corner(variation=20.0, reapplications=1),
                "Roggia": corner(variation=20.0, reapplications=4),
            }
        )
        self.assertEqual(["Roggia", "Turn 1"], names(entries))

    def test_onset_delta_breaks_a_remaining_tie(self):
        entries = rank_corners(
            {
                "Turn 1": corner(variation=20.0, delta_abs=2.0),
                "Roggia": corner(variation=20.0, delta_abs=25.0),
            }
        )
        self.assertEqual(["Roggia", "Turn 1"], names(entries))

    def test_identical_keys_keep_track_config_order(self):
        entries = rank_corners(
            {"Turn 1": corner(variation=20.0), "Roggia": corner(variation=20.0)}
        )
        self.assertEqual(["Turn 1", "Roggia"], names(entries))

    def test_corners_without_data_trail_the_list_unranked(self):
        entries = rank_corners(
            {
                "Roggia": corner(status="no_data"),
                "Turn 1": corner(variation=None),
                "Lesmo 1": corner(variation=5.0),
            }
        )
        self.assertEqual(["Lesmo 1", "Turn 1", "Roggia"], names(entries))
        self.assertEqual(
            {"Lesmo 1": 1, "Turn 1": 2, "Roggia": None}, ranks(entries)
        )

    def test_entries_carry_the_signals_the_order_was_decided_by(self):
        entries = rank_corners(
            {"Turn 1": corner(variation=32.2, reapplications=2, delta_abs=15.5)}
        )
        self.assertEqual(
            {
                "corner": "Turn 1",
                "rank": 1,
                "status": "ok",
                "onset_variation_m": 32.2,
                "reapplication_count": 2,
                "onset_delta_abs": 15.5,
            },
            entries[0],
        )

    def test_empty_input(self):
        self.assertEqual([], rank_corners({}))


if __name__ == "__main__":
    unittest.main()
