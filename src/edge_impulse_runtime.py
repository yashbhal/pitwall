#!/usr/bin/env python3
"""Run one real inference of the deployed anomaly model on the UNO Q.

This is a one-shot proof that the Edge Impulse Linux runtime works on the
board, not a live pipeline: it feeds a single braking window from an already
exported CSV (src/edge_impulse_export.py) into the .eim binary and prints
whatever the SDK gives back, anomaly score included.

The impulse was trained on 1.45 s windows at 20 Hz, so it expects exactly
29 timesteps x 6 axes = 174 float32 features, flattened time-major:
    [brake_0, throttle_0, steer_0, speed_0, engine_rpm_0, gear_0,
     brake_1, ... , gear_28]
Axis order must match EI_FEATURE_COLS from the exporter. Exported CSVs are
already sampled at 50 ms, so the first 29 rows are used as-is -- no resampling.

Run on the board (model path and default CSV both resolve inside the repo):

    python3 src/edge_impulse_runtime.py
    python3 src/edge_impulse_runtime.py data/edge_impulse_export/normal.<...>.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from edge_impulse_linux.runner import ImpulseRunner

from src.edge_impulse_export import EI_FEATURE_COLS

MODEL_PATH = PROJECT_ROOT / "data" / "pitwall-linux-aarch64-v1-impulse-#1.eim"
DEFAULT_CSV = (
    PROJECT_ROOT
    / "data"
    / "edge_impulse_export"
    / "normal.2026-07-18_211538_turn_1_1.csv"
)
WINDOW_ROWS = 29


def load_features(csv_path: Path) -> list[float]:
    """Flatten the first WINDOW_ROWS rows of an exported CSV into one window.

    The timestamp column is dropped; only EI_FEATURE_COLS are read, in the
    training order, so column reordering in the file cannot silently shuffle
    the axes.
    """
    with csv_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))[:WINDOW_ROWS]

    if len(rows) < WINDOW_ROWS:
        raise SystemExit(
            f"{csv_path.name}: need {WINDOW_ROWS} rows, found {len(rows)}"
        )

    return [float(row[col]) for row in rows for col in EI_FEATURE_COLS]


def main(csv_path: Path) -> None:
    features = load_features(csv_path)
    print(f"model:    {MODEL_PATH}")
    print(f"window:   {csv_path.name}")
    print(f"features: {len(features)} ({WINDOW_ROWS} x {len(EI_FEATURE_COLS)})")

    runner = ImpulseRunner(str(MODEL_PATH))
    try:
        info = runner.init()
        print(
            f"impulse:  {info['project']['owner']} / {info['project']['name']} "
            f"(v{info['project']['deploy_version']})"
        )
        print(runner.classify(features))
    finally:
        runner.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "csv_path",
        nargs="?",
        type=Path,
        default=DEFAULT_CSV,
        help=f"exported Edge Impulse window CSV (default: {DEFAULT_CSV.name})",
    )
    main(parser.parse_args().csv_path)
