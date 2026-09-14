# PitWall

A practice coach for beginner sim racers. PitWall reads live telemetry from F1 25
on a PS5, measures how consistently you brake into a corner, and turns that into
one specific drill to work on next.

The idea is that raw telemetry graphs tell a beginner they were slow but not what
to practice. PitWall answers a narrower question: what should I fix next, and did
the practice help?

Currently calibrated for Monza, Turn 1 and Roggia. The full project plan is in
`docs/pitwall-plan.md`.

## How it works

The game broadcasts UDP telemetry packets on the local network. From there:

1. `src/udp_listener.py` receives packets and `src/packet_parser.py` unpacks them
   according to the F1 25 UDP spec.
2. `src/session_logger.py` appends every packet to a CSV in `data/raw/`.
3. `src/corner_detector.py` finds the samples belonging to each corner, splits
   them into individual passes, and discards passes that are not real attempts
   (spins, flashbacks, pit laps).
4. `src/brake_analyzer.py` measures brake onset distance and counts genuine brake
   reapplications, ignoring ABS chatter and pedal modulation.
5. `src/session_analyzer.py` combines this into per corner metrics, ranks the
   corners worst first, and asks `src/coach.py` for a drill.
6. `src/web_app.py` serves the result as a read only report page.

Analysis runs after a session, not during it. Nothing here tries to coach you
mid corner.

## Hardware feedback

An Arduino UNO Q drives a status LED and an 8x13 LED matrix. The Linux side sends
a single small integer state code over Bridge RPC and the sketch owns all glyph
and animation timing locally. The wire protocol and the full state table are
documented in `mcu/bridge_protocol.md`, which is worth reading before changing
either side.

Note that the matrix is monochrome blue and colour carries no meaning anywhere in
the design. States are distinguished by which device lights up, glyph shape, and
flash rhythm.

## Anomaly detection

An Edge Impulse model scores a braking window as normal or unusual, as a second
opinion alongside the rule based metrics. The rule based engine always works
without it.

- `src/edge_impulse_export.py` exports labelled braking windows for training.
- `src/edge_impulse_runtime.py` runs one inference on the board and shows the
  result on the LED matrix.

## Running it

Point F1 25 at this machine's IP with UDP telemetry enabled on port 20777
(see `config/network.yaml`), then record a session:

```
python3 src/udp_listener.py
```

Analyse a recording from the terminal:

```
python3 src/session_analyzer.py data/raw/<file>_session.csv monza
```

Or read the same report in a browser at `http://localhost:5001`:

```
pip install -r requirements.txt
python3 src/web_app.py
```

Run the tests:

```
python3 -m unittest discover -s tests -p 'test_*.py'
```

`tests/` also holds a few interactive harnesses that are not unit tests, such as
`simulate_live_led.py`, which previews the LED cues in a terminal.

## On the board

The LED code runs as an Arduino App, which means it lives in a container that can
only see its own App folder. `scripts/sync_led_app.sh` mirrors this checkout into
that folder:

```
scripts/sync_led_app.sh
arduino-app-cli app start ~/ArduinoApps/pitwall-led
```

Two things the sync deliberately does not copy, because it must never delete your
recordings or overwrite a model:

- Session CSVs in `python/data/`.
- The `.eim` model file, which has to be copied across by hand.

Set `PITWALL_SESSION_DIR` so the recorder and the LED app agree on one recording
directory. Without it they can end up reading and writing different folders.

## Layout

```
src/          telemetry capture, analysis, coaching, dashboard
config/       tuning thresholds and calibrated corner boundaries
mcu/          the UNO Q Arduino App and its Bridge protocol doc
tests/        unit tests plus a few manual harnesses
docs/         project plan and the F1 25 telemetry spec
data/raw/     recorded sessions
scripts/      board side deployment helper
```

Tuning values live in `config/`, never in the analysis code. Corner boundaries in
`config/monza.py` were calibrated from real driving data, and the comments there
record which session and lap each number came from.
