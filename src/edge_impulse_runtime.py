#!/usr/bin/env python3
"""Run one real inference of the deployed anomaly model and show it on the LED.

This is a one-shot proof that the Edge Impulse Linux runtime works on the
board, not a live pipeline: it feeds a single braking window from an already
exported CSV (src/edge_impulse_export.py) into the .eim binary, prints whatever
the SDK gives back, and turns the anomaly score into one LED state.

The impulse was trained on 1.45 s windows at 20 Hz, so it expects exactly
29 timesteps x 6 axes = 174 float32 features, flattened time-major:
    [brake_0, throttle_0, steer_0, speed_0, engine_rpm_0, gear_0,
     brake_1, ... , gear_28]
Axis order must match EI_FEATURE_COLS from the exporter. Exported CSVs are
already sampled at 50 ms, so the first 29 rows are used as-is -- no resampling.

The LED half reuses src/bridge_client.py's transport and state codes rather than
touching Bridge directly, so there is still exactly one definition of the wire
protocol (mcu/bridge_protocol.md). A clean window sends state 1 (connected,
matrix dark); an anomalous one sends state 5, the circle fade. Colour is not
used: the matrix is monochrome blue and states are encoded as glyph and rhythm.

The sketch raises the error state after 3 s without a heartbeat, so the result
is re-sent every second for HOLD_SECONDS and then handed back as idle. Without
that, a one-shot send would show the result briefly and then flash an error.

Real LED output needs arduino.app_utils, which only imports inside the App Lab
container, so run this from the App folder that scripts/sync_led_app.sh mirrors.
Elsewhere -- laptop, or plain SSH on the board -- bridge_client falls back to
printing the state instead of pretending an LED changed. The pitwall-led app's
own loop must not be running at the same time: it re-sends its own state every
second and would immediately overwrite this one.

    python3 src/edge_impulse_runtime.py
    python3 src/edge_impulse_runtime.py data/edge_impulse_export/normal.<...>.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from edge_impulse_linux.runner import ImpulseRunner

from src.bridge_client import (
    STATE_ANOMALY,
    STATE_CONNECTED,
    STATE_IDLE,
    STATE_NAMES,
    open_transport,
)
from src.edge_impulse_export import EI_FEATURE_COLS

MODEL_PATH = PROJECT_ROOT / "data" / "pitwall-linux-aarch64-v1-impulse-#1.eim"
DEFAULT_CSV = (
    PROJECT_ROOT
    / "data"
    / "edge_impulse_export"
    / "normal.2026-07-18_211538_turn_1_1.csv"
)
WINDOW_ROWS = 29

# Measured on the exported Turn 1 windows this impulse was trained on: normal
# laps score 0.6-1.7 and the one visibly odd window scores 13.8. 3.0 sits in the
# empty gap between them, so it is not tuned to either end. One recording is
# thin evidence for a cutoff -- treat this as a demo threshold, not a calibrated
# one, and re-derive it once more sessions are scored.
ANOMALY_CUTOFF = 3.0

# Long enough to look at and point to, short enough that nobody is left holding
# a stale cue. The heartbeat below keeps the sketch's watchdog quiet meanwhile.
HOLD_SECONDS = 10.0
HEARTBEAT_SECONDS = 1.0


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


def anomaly_score(result: dict) -> float:
    """Pull the anomaly score out of the SDK's result dict.

    Missing it means the .eim is not the anomaly impulse we think it is, which
    is worth failing on rather than defaulting to "looks fine".
    """
    try:
        return float(result["result"]["anomaly"])
    except (KeyError, TypeError, ValueError) as exc:
        raise SystemExit(f"no anomaly score in result {result!r}: {exc}")


def state_for_score(score: float) -> int:
    """Map an anomaly score to an LED state code from mcu/bridge_protocol.md."""
    return STATE_ANOMALY if score > ANOMALY_CUTOFF else STATE_CONNECTED


def hold_state(transport, code: int) -> None:
    """Show *code* for HOLD_SECONDS, heartbeating, then hand back idle.

    The sketch shows the error state after STATE_TIMEOUT_MS of silence, so the
    re-send is what keeps a held cue from decaying into a false error. Idle on
    the way out means the LED does not keep asserting a result after the process
    that measured it has gone.
    """
    print(f"[led] {STATE_NAMES.get(code, code)} for {HOLD_SECONDS:.0f}s")
    deadline = time.monotonic() + HOLD_SECONDS
    try:
        while True:
            transport.send_state(code)
            if time.monotonic() >= deadline:
                break
            time.sleep(HEARTBEAT_SECONDS)
    except KeyboardInterrupt:
        print()
    finally:
        print(f"[led] {STATE_NAMES[STATE_IDLE]}")
        transport.send_state(STATE_IDLE)


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
        result = runner.classify(features)
        print(result)
    finally:
        runner.stop()

    score = anomaly_score(result)
    state = state_for_score(score)
    verdict = "ANOMALY" if state == STATE_ANOMALY else "normal"
    print(f"anomaly:  {score:.2f} (cutoff {ANOMALY_CUTOFF:.1f}) -> {verdict}")

    transport = open_transport()
    print(f"[led] transport: {transport.name}")
    hold_state(transport, state)


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
