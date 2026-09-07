"""Cross-checks the sketch's state 2 maths. Run: python3 -m unittest tests.test_sketch_glyph

The UNO Q core cannot be assumed present on a development laptop, so the sketch
cannot be compiled here. But the two functions that decide what state 2 looks
like -- triangleUpPixel() and pulseBrightness() -- are pure integer arithmetic
with no Arduino dependency, so they can be lifted out of the real .ino and
compiled with g++.

That matters for two reasons:

  * pulseBrightness() does unsigned long arithmetic and integer division. A
    truncation or overflow there would be invisible in review and would only show
    up as a wrong-looking LED.
  * tests/simulate_live_led.py reimplements both in Python so the pulse can be
    previewed in a terminal. That duplication is only safe if something checks
    the two agree, which is what this does.

The C++ is extracted from mcu/pitwall_led_app/sketch/sketch.ino by name rather
than copied here, so this test cannot pass against a stale copy.
"""

import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tests.simulate_live_led import (
    MATRIX_COLS,
    MATRIX_ROWS,
    PULSE_MAX,
    PULSE_MIN,
    PULSE_PERIOD_S,
    pulse_brightness,
    triangle_up_rows,
)

SKETCH = PROJECT_ROOT / "mcu" / "pitwall_led_app" / "sketch" / "sketch.ino"

CONSTANTS = (
    "MATRIX_ROWS",
    "MATRIX_COLS",
    "APPROACH_PULSE_PERIOD_MS",
    "APPROACH_MIN_BRIGHTNESS",
    "APPROACH_MAX_BRIGHTNESS",
)

FUNCTIONS = ("triangleUpPixel", "pulseBrightness")

HARNESS = """
#include <cstdio>
#include <cstdint>

%(extracted)s

int main() {
  for (uint8_t row = 0; row < MATRIX_ROWS; row++) {
    for (uint8_t col = 0; col < MATRIX_COLS; col++) {
      printf("%%d", triangleUpPixel(row, col) ? 1 : 0);
    }
    printf("\\n");
  }
  for (unsigned long ms = 0; ms < 2 * APPROACH_PULSE_PERIOD_MS; ms += 10) {
    printf("%%lu %%u\\n", ms, (unsigned)pulseBrightness(ms));
  }
  return 0;
}
"""


def extract_constant(source: str, name: str) -> str:
    match = re.search(rf"^static const [^\n]*\b{name}\s*=[^;]+;", source, re.M)
    if match is None:
        raise AssertionError(f"{name} not found in {SKETCH.name}")
    return match.group(0)


def extract_function(source: str, name: str) -> str:
    """Pull a whole static function definition out by brace matching."""
    match = re.search(rf"^static [\w:]+ {name}\([^)]*\)\s*\{{", source, re.M)
    if match is None:
        raise AssertionError(f"{name}() not found in {SKETCH.name}")

    depth = 0
    for index in range(match.end() - 1, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[match.start() : index + 1]
    raise AssertionError(f"unbalanced braces in {name}()")


def build_program() -> str:
    source = SKETCH.read_text(encoding="utf-8")
    parts = [extract_constant(source, name) for name in CONSTANTS]
    parts += [extract_function(source, name) for name in FUNCTIONS]
    # uint8_t/uint16_t come from <cstdint>; nothing else Arduino-specific is used.
    return HARNESS % {"extracted": "\n\n".join(parts)}


@unittest.skipUnless(shutil.which("g++"), "g++ not available")
class SketchGlyphTest(unittest.TestCase):
    """Compiles the real sketch's glyph and pulse functions and runs them."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        directory = Path(cls._tmp.name)
        source = directory / "glyph.cpp"
        source.write_text(build_program(), encoding="utf-8")
        binary = directory / "glyph"

        subprocess.run(
            ["g++", "-std=c++17", "-Wall", "-Werror", "-o", str(binary), str(source)],
            check=True,
            capture_output=True,
        )
        output = subprocess.run(
            [str(binary)], check=True, capture_output=True, text=True
        ).stdout.splitlines()

        cls.glyph = output[:MATRIX_ROWS]
        cls.pulse = [
            (int(ms), int(value))
            for ms, value in (line.split() for line in output[MATRIX_ROWS:])
        ]

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_compiles_without_warnings(self):
        # Proven by setUpClass's -Werror build; asserted so the intent is visible.
        self.assertEqual(MATRIX_ROWS, len(self.glyph))

    def test_glyph_is_a_filled_triangle_pointing_up(self):
        widths = [row.count("1") for row in self.glyph]

        # Apex at the top, full width at the bottom, never narrowing downwards.
        self.assertEqual(1, widths[0])
        self.assertEqual(MATRIX_COLS, widths[-1])
        self.assertEqual(widths, sorted(widths))

        for row in self.glyph:
            lit = [index for index, pixel in enumerate(row) if pixel == "1"]
            # Contiguous (filled, not an outline) and centred.
            self.assertEqual(list(range(lit[0], lit[-1] + 1)), lit)
            self.assertEqual(MATRIX_COLS - 1 - lit[-1], lit[0])

    def test_glyph_matches_the_python_preview(self):
        preview = triangle_up_rows(PULSE_MAX)
        expected = ["".join("1" if char != " " else "0" for char in row) for row in preview]
        self.assertEqual(expected, self.glyph)

    def test_pulse_stays_inside_its_declared_range(self):
        values = [value for _ms, value in self.pulse]
        self.assertEqual(PULSE_MIN, min(values))
        self.assertEqual(PULSE_MAX, max(values))

    def test_pulse_never_goes_dark(self):
        # A cue that reaches zero cannot be told apart from the cue having ended.
        self.assertGreater(min(value for _ms, value in self.pulse), 0)

    def test_pulse_is_dim_bright_dim_once_per_period(self):
        period_ms = int(PULSE_PERIOD_S * 1000)
        first = [value for ms, value in self.pulse if ms < period_ms]

        peak = first.index(max(first))
        self.assertEqual(first[:peak], sorted(first[:peak]))
        self.assertEqual(first[peak:], sorted(first[peak:], reverse=True))

        # Peak at the half period, so the fade up and down take equal time.
        self.assertAlmostEqual(period_ms // 2, self.pulse[peak][0], delta=10)

    def test_pulse_repeats_every_period(self):
        period_ms = int(PULSE_PERIOD_S * 1000)
        by_ms = dict(self.pulse)
        for ms, value in self.pulse:
            if ms + period_ms in by_ms:
                self.assertEqual(value, by_ms[ms + period_ms])

    def test_pulse_matches_the_python_preview(self):
        for ms, value in self.pulse:
            with self.subTest(ms=ms):
                # Integer millisecond maths versus float seconds: one step of
                # rounding difference is expected, more means a real divergence.
                self.assertLessEqual(abs(value - pulse_brightness(ms / 1000.0)), 1)


if __name__ == "__main__":
    unittest.main()
