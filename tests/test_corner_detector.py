"""Corner extraction tests. Run: python3 -m unittest tests.test_corner_detector

Pins the two contracts the row-reuse and verbose changes depend on: extraction
must be silent by default, and passing pre-parsed rows must give byte-identical
results to reading the file.
"""

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src import corner_detector

HEADER = (
    "timestamp,packet_id,session_time,frame_identifier,lap_distance,"
    "current_lap_num,car_position,speed,throttle,brake,steer,gear,engine_rpm"
)
ZONE = (700.0, 950.0)


def write_session_csv(path: Path, sample_count: int = 30) -> None:
    """Write a minimal two-packet session: LAP rows carry distance, TEL speed."""
    lines = [HEADER]
    for i in range(sample_count):
        session_time = i * 0.05
        lap_distance = 700.0 + i * 5.0
        lines.append(
            f"2026-01-01T00:00:00,2,{session_time},{i},{lap_distance},1,1,,,,,,"
        )
        lines.append(
            f"2026-01-01T00:00:00,6,{session_time},{i},,,,200,0.5,0.0,0.0,7,11000"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class CornerDetectorTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.csv_path = Path(self._tmp.name) / "session.csv"
        # 60 samples span 700m to 995m, so the tail falls outside ZONE.
        write_session_csv(self.csv_path, sample_count=60)

    def extract(self, **kwargs):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            samples = corner_detector.extract_corner_samples(
                str(self.csv_path), ZONE, **kwargs
            )
        return samples, buffer.getvalue()

    def test_extracts_in_zone_samples_as_one_contiguous_stint(self):
        samples, _ = self.extract()
        self.assertEqual([1], list(samples))
        self.assertEqual(1, len(samples[1]))
        self.assertEqual(51, len(samples[1][0]))

    def test_silent_by_default(self):
        _, output = self.extract()
        self.assertEqual("", output)

    def test_verbose_prints_diagnostics(self):
        _, output = self.extract(verbose=True)
        self.assertIn("Corner samples per lap", output)

    def test_verbose_does_not_change_results(self):
        quiet, _ = self.extract()
        loud, _ = self.extract(verbose=True)
        self.assertEqual(quiet, loud)

    def test_preloaded_rows_give_identical_results(self):
        from_file, _ = self.extract()
        rows = corner_detector.read_session_rows(str(self.csv_path))
        from_rows, _ = self.extract(rows=rows)
        self.assertEqual(from_file, from_rows)

    def test_shared_rows_survive_repeated_extraction(self):
        rows = corner_detector.read_session_rows(str(self.csv_path))
        row_count = len(rows)
        first, _ = self.extract(rows=rows)
        second, _ = self.extract(rows=rows)
        self.assertEqual(first, second)
        self.assertEqual(row_count, len(rows))

    def test_out_of_zone_samples_are_excluded(self):
        samples, _ = self.extract()
        distances = [float(row["lap_distance"]) for row in samples[1][0]]
        self.assertTrue(all(ZONE[0] <= d <= ZONE[1] for d in distances))
        self.assertEqual(950.0, max(distances))


if __name__ == "__main__":
    unittest.main()
