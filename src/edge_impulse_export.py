#!/usr/bin/env python3
"""
Export valid Turn 1 braking windows to Edge Impulse CSV format.

For each valid attempt identified by the existing corner/attempt pipeline,
extract a ~1.5-second window (±0.75 s) centred on brake onset and write it
as one CSV file ready for Edge Impulse upload.

Edge Impulse format requirements (time-series anomaly detection):
  - First column:  "timestamp" in integer milliseconds, starting at 0,
                   with CONSTANT step = measured telemetry sample interval.
  - Remaining cols: one per feature, in the same order every file.
  - Filename prefix "normal." tells Edge Impulse these are baseline-class
    samples.

Columns available in our session CSVs (from session_logger.py):
  brake, throttle, steer, speed, engine_rpm, gear
  (no g-force: session_logger.py does not log it)

Note: the session_logger column is "steer" (not "steering") and
      "engine_rpm" (not "rpm").  Edge Impulse uses whatever column header
      you give it, so we preserve the logged names verbatim.

Usage:
    python src/edge_impulse_export.py
    python src/edge_impulse_export.py --dry-run   # print plan, write nothing
"""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.loader import load_thresholds, load_track_config
from src import corner_detector
from src.session_analyzer import (
    _analyze_passes,
    _build_fragments,
    _group_into_passes,
)

# ── Configuration ─────────────────────────────────────────────────────────────

RAW_DIR = PROJECT_ROOT / "data" / "raw"
OUTPUT_DIR = PROJECT_ROOT / "data" / "edge_impulse_export"
TRACK_NAME = "monza"
# Section 15 of pitwall-plan.md: start with Turn 1 only.
TARGET_CORNER = "Turn 1"

# Window half-width: total window = 2 × HALF_WINDOW_S = 1.5 s.
# This satisfies the plan's "1–2 second windows" requirement and gives
# 30 samples at 20 Hz (15 before onset + 15 after).
HALF_WINDOW_S = 0.75

# Feature columns, in the order they appear in every exported CSV.
# These are the exact header names written by session_logger.py.
EI_FEATURE_COLS = ["brake", "throttle", "steer", "speed", "engine_rpm", "gear"]


# ── Helpers ───────────────────────────────────────────────────────────────────


def _compute_sample_interval_ms(rows: list[dict]) -> float:
    """Return the median gap between consecutive telemetry rows, in ms.

    Uses only packet_id=6 rows and the first 200 gaps to avoid a slow
    full-file scan.  Falls back to 50.0 ms (20 Hz) if data is sparse.
    """
    times: list[float] = []
    for row in rows:
        if row.get("packet_id", "").strip() != "6":
            continue
        raw = row.get("session_time", "").strip()
        if not raw:
            continue
        try:
            times.append(float(raw))
        except ValueError:
            pass

    if len(times) < 2:
        return 50.0  # fallback

    gaps_ms = [
        (times[i + 1] - times[i]) * 1000.0
        for i in range(min(200, len(times) - 1))
        if times[i + 1] > times[i]  # skip any backwards jumps (flashbacks)
    ]
    return statistics.median(gaps_ms) if gaps_ms else 50.0


def _extract_window(
    all_rows: list[dict],
    onset_time: float,
    half_window_s: float,
) -> list[dict]:
    """Return packet_id=6 rows within [onset_time ± half_window_s], time-sorted.

    Pulls from the full session (not just corner-zone rows) so the pre-onset
    portion of the window is never truncated by zone boundaries.
    Speed < 5 km/h rows are excluded to match corner_detector's filter and
    avoid polluting the feature space with idle/stationary frames.
    """
    lo = onset_time - half_window_s
    hi = onset_time + half_window_s

    bucket: list[tuple[float, dict]] = []
    for row in all_rows:
        if row.get("packet_id", "").strip() != "6":
            continue
        raw_t = row.get("session_time", "")
        if not raw_t:
            continue
        try:
            t = float(raw_t)
        except ValueError:
            continue
        if not (lo <= t <= hi):
            continue
        try:
            speed = float(row.get("speed") or 0)
        except ValueError:
            speed = 0.0
        if speed < 5.0:
            continue
        bucket.append((t, row))

    bucket.sort(key=lambda x: x[0])
    return [r for _, r in bucket]


def _safe_float(row: dict, key: str) -> float:
    """Parse a telemetry field as float, returning 0.0 on any failure."""
    raw = row.get(key)
    if raw is None:
        return 0.0
    raw = str(raw).strip()
    if not raw:
        return 0.0
    try:
        return float(raw)
    except ValueError:
        return 0.0


def _write_ei_csv(
    path: Path, window_rows: list[dict], interval_ms: float
) -> None:
    """Write one Edge Impulse CSV file for a single braking window.

    Timestamp column: integer milliseconds, starting at 0, with a CONSTANT
    step equal to interval_ms rounded to the nearest millisecond.  Using an
    integer step avoids floating-point drift that would produce non-constant
    gaps (e.g. …500, 551, 601… instead of …500, 550, 600…) and ensures Edge
    Impulse infers the correct sample rate from the timestamps.
    """
    step_ms = round(interval_ms)  # e.g. 50.05 ms → 50 ms
    fieldnames = ["timestamp"] + EI_FEATURE_COLS
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for i, row in enumerate(window_rows):
            out: dict = {"timestamp": i * step_ms}
            for col in EI_FEATURE_COLS:
                out[col] = _safe_float(row, col)
            writer.writerow(out)


# ── Main ──────────────────────────────────────────────────────────────────────


def main(dry_run: bool = False) -> None:
    if not dry_run:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    thresholds = load_thresholds()
    zones = load_track_config(TRACK_NAME)

    if TARGET_CORNER not in zones:
        raise SystemExit(
            f"Corner '{TARGET_CORNER}' not found in {TRACK_NAME} config."
        )

    zone = zones[TARGET_CORNER]["zone"]
    # Sanitise corner name for use in filenames: "Turn 1" → "turn_1"
    corner_slug = TARGET_CORNER.lower().replace(" ", "_")

    session_files = sorted(RAW_DIR.glob("*_session.csv"))
    if not session_files:
        raise SystemExit(f"No session files found in {RAW_DIR}")

    total_windows = 0
    example_path: Path | None = None

    for csv_path in session_files:
        # session_id: stem minus the trailing "_session" suffix
        session_id = csv_path.stem[: -len("_session")]

        print(f"\n── {session_id} ──")

        rows = corner_detector.read_session_rows(str(csv_path))
        interval_ms = _compute_sample_interval_ms(rows)
        print(f"   sample interval: {interval_ms:.1f} ms  ({1000/interval_ms:.1f} Hz)")

        samples_by_lap = corner_detector.extract_corner_samples(
            str(csv_path), zone, rows=rows
        )
        fragments = _build_fragments(samples_by_lap)
        passes_list = _group_into_passes(fragments)
        attempts, rejected = _analyze_passes(passes_list, thresholds)

        print(
            f"   valid attempts: {len(attempts)}  |  "
            f"rejected fragments: {len(rejected)}"
        )

        for attempt_num, attempt in enumerate(attempts, start=1):
            onset_time = attempt["onset_session_time"]
            window_rows = _extract_window(rows, onset_time, HALF_WINDOW_S)

            if not window_rows:
                print(
                    f"   [WARN] attempt {attempt_num}: empty window at "
                    f"t={onset_time:.3f}s — skipping"
                )
                continue

            fname = f"normal.{session_id}_{corner_slug}_{attempt_num}.csv"
            out_path = OUTPUT_DIR / fname

            if not dry_run:
                _write_ei_csv(out_path, window_rows, interval_ms)

            total_windows += 1
            if example_path is None:
                example_path = out_path

            print(
                f"   {'[DRY] ' if dry_run else ''}→ {fname}"
                f"  ({len(window_rows)} rows"
                f"  onset={onset_time:.3f}s"
                f"  dist={attempt['onset_distance_m']:.1f}m"
                f"  lap={attempt['lap_num']})"
            )

    # ── Summary ──────────────────────────────────────────────────────────────

    print(f"\n{'═' * 60}")
    print(f"Total windows exported : {total_windows}")
    if dry_run:
        print("(dry-run: no files written)")
    else:
        print(f"Output directory       : {OUTPUT_DIR}")

    if example_path is not None and not dry_run and example_path.exists():
        print(f"\nExample file: {example_path.name}")
        print()
        print(example_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Export valid Turn 1 braking windows to Edge Impulse CSV format."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be exported without writing any files.",
    )
    args = parser.parse_args()
    main(dry_run=args.dry_run)
