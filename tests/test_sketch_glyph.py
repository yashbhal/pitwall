"""Cross-checks the sketch's matrix cue maths. Run: python3 -m unittest tests.test_sketch_glyph

The UNO Q core cannot be assumed present on a development laptop, so the sketch
cannot be compiled here. But the functions that decide what the matrix cues look
like -- triangleUpPixel() and pulseBrightness() for state 2, circlePixel() and
fadeBrightness() for state 5 -- are pure integer arithmetic with no Arduino
dependency, so they can be lifted out of the real .ino and compiled with g++.

That matters for two reasons:

  * triangleWave(), which both brightness functions call, does unsigned long
    arithmetic and integer division. A truncation or overflow there would be
    invisible in review and would only show up as a wrong-looking LED.
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
    "ANOMALY_FADE_PERIOD_MS",
    "ANOMALY_MIN_BRIGHTNESS",
    "ANOMALY_MAX_BRIGHTNESS",
    "ANOMALY_RADIUS_HALF_PIXELS",
)

FUNCTIONS = (
    "triangleUpPixel",
    "circlePixel",
    "triangleWave",
    "pulseBrightness",
    "fadeBrightness",
)

# Both glyphs are printed as MATRIX_ROWS lines of 0/1, then the state 2 pulse
# over two of its periods, then the state 5 fade over two of its own.
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
  for (uint8_t row = 0; row < MATRIX_ROWS; row++) {
    for (uint8_t col = 0; col < MATRIX_COLS; col++) {
      printf("%%d", circlePixel(row, col) ? 1 : 0);
    }
    printf("\\n");
  }
  for (unsigned long ms = 0; ms < 2 * APPROACH_PULSE_PERIOD_MS; ms += 10) {
    printf("%%lu %%u\\n", ms, (unsigned)pulseBrightness(ms));
  }
  printf("--\\n");
  for (unsigned long ms = 0; ms < 2 * ANOMALY_FADE_PERIOD_MS; ms += 10) {
    printf("%%lu %%u\\n", ms, (unsigned)fadeBrightness(ms));
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


def constant_value(name: str) -> int:
    """Read a numeric ``static const`` out of the sketch by name.

    Keeps the state 5 expectations below from drifting away from the .ino the
    same way the extracted functions cannot.
    """
    declaration = extract_constant(SKETCH.read_text(encoding="utf-8"), name)
    match = re.search(r"=\s*(\d+)", declaration)
    if match is None:
        raise AssertionError(f"{name} is not a plain integer: {declaration}")
    return int(match.group(1))


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
        cls.circle = output[MATRIX_ROWS : 2 * MATRIX_ROWS]

        waves = output[2 * MATRIX_ROWS :]
        split_at = waves.index("--")
        cls.pulse = cls._parse_wave(waves[:split_at])
        cls.fade = cls._parse_wave(waves[split_at + 1 :])

    @staticmethod
    def _parse_wave(lines):
        return [
            (int(ms), int(value))
            for ms, value in (line.split() for line in lines)
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

    # ── State 5: Edge Impulse anomaly ────────────────────────────────────────

    def test_circle_is_filled_and_centred(self):
        widths = [row.count("1") for row in self.circle]

        # Vertically symmetric, and no empty row: the disc spans the full height.
        self.assertEqual(widths, widths[::-1])
        self.assertGreater(min(widths), 0)

        for row in self.circle:
            lit = [index for index, pixel in enumerate(row) if pixel == "1"]
            # Contiguous (filled, not a ring) and centred on the middle column.
            self.assertEqual(list(range(lit[0], lit[-1] + 1)), lit)
            self.assertEqual(MATRIX_COLS - 1 - lit[-1], lit[0])

    def test_circle_is_widest_in_the_middle(self):
        widths = [row.count("1") for row in self.circle]
        middle = MATRIX_ROWS // 2

        # Monotonic out to the waist from either end, which is what makes it
        # read as round rather than as a bar or a diamond.
        self.assertEqual(widths[:middle], sorted(widths[:middle]))
        self.assertEqual(max(widths), widths[middle])

    def test_circle_shares_no_shape_with_the_triangle(self):
        # bridge_protocol.md's distinguishability rule: no two matrix cues may
        # share both a glyph and a rhythm.
        self.assertNotEqual(self.glyph, self.circle)

    def test_circle_radius_bounds_the_glyph(self):
        radius = constant_value("ANOMALY_RADIUS_HALF_PIXELS")
        widest = max(row.count("1") for row in self.circle)

        # Half-pixel units: the widest row cannot exceed the diameter, and the
        # disc must be big enough to be a shape rather than a dot.
        self.assertLessEqual(widest, radius + 1)
        self.assertGreaterEqual(widest, 3)

    def test_fade_stays_inside_its_declared_range(self):
        values = [value for _ms, value in self.fade]
        self.assertEqual(constant_value("ANOMALY_MIN_BRIGHTNESS"), min(values))
        self.assertEqual(constant_value("ANOMALY_MAX_BRIGHTNESS"), max(values))

    def test_fade_never_goes_dark(self):
        # Same reason as the pulse: reaching zero looks like the cue ending.
        self.assertGreater(min(value for _ms, value in self.fade), 0)

    def test_fade_is_dim_bright_dim_once_per_period(self):
        period_ms = constant_value("ANOMALY_FADE_PERIOD_MS")
        first = [value for ms, value in self.fade if ms < period_ms]

        peak = first.index(max(first))
        self.assertEqual(first[:peak], sorted(first[:peak]))
        self.assertEqual(first[peak:], sorted(first[peak:], reverse=True))
        self.assertAlmostEqual(period_ms // 2, self.fade[peak][0], delta=10)

    def test_fade_is_slower_than_the_approach_pulse(self):
        # The two slowest rhythms on the board, and they must not be confusable
        # with each other or come anywhere near the error flash.
        approach_ms = constant_value("APPROACH_PULSE_PERIOD_MS")
        anomaly_ms = constant_value("ANOMALY_FADE_PERIOD_MS")
        self.assertGreater(anomaly_ms, approach_ms)
        self.assertGreater(anomaly_ms, 10 * constant_value("ERROR_FLASH_INTERVAL_MS"))


if __name__ == "__main__":
    unittest.main()
