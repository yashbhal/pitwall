# PitWall Bridge Protocol (Linux MPU to STM32 MCU)

## Why a single integer

Linux sends **one small integer** naming the current situation. The MCU decides
what that situation looks like and animates it locally.

The rejected alternative was pushing the 104-pixel frame from Linux. Two
reasons not to:

1. Array payloads over Bridge RPC on the UNO Q are unreliable in practice.
   Reported failure: `Request 'test_array_num1' failed: Wrong type parameter in
   position: 0 (253)`, with people resorting to packing booleans into strings.
   Single ints and bools cross reliably.
2. Animating a pulse from Linux needs ~30 calls/second forever. State codes need
   ~1/second. Bridge calls are synchronous and have real per-call overhead.

## Method

| | |
|---|---|
| Method name | `pitwall_led_state` |
| Direction | Linux calls, MCU provides |
| Argument | one `int` state code |
| Return | the accepted code, echoed, so Linux can confirm the round trip |

Linux is always the caller. This deliberately avoids the known UNO Q startup
race where the MCU runs before the Python side exists and early messages are
lost, so no MCU-side handshake loop is needed.

Defined in `src/bridge_client.py` (`BRIDGE_METHOD`, `STATE_*`) and
`mcu/pitwall_led_app/sketch/sketch.ino`. Both must be edited together.

## Hardware reality: the matrix has no colour, and colour is not used

The UNO Q's 8x13 matrix is a **monochrome blue** 104-pixel matrix driven by the
STM32U585 (datasheet ABX00162). It cannot render green, yellow, orange, red or
purple. `docs/pitwall-plan.md` section 13 assumes a colour matrix; that part of
the plan is not physically achievable.

The board also has MCU-driven RGB LEDs (RGB LED 3, D27401,
`LED3_R`/`LED3_G`/`LED3_B`, active-low), so colour was technically available.
**It is deliberately not used anywhere.** Only the blue channel of RGB LED 3 is
driven; red and green are held off. Dropping colour means accessibility is
satisfied structurally rather than needing a per-state colour audit, and blue
keeps the two output devices visually consistent.

States are distinguished by **which device lights up**, **glyph shape**, **flash
rhythm**, and **brightness** (`setGrayscaleBits(8)`, which also enables smooth
fades). Plan section 13's "blue, solid" for the connected state is still met
incidentally, since blue is the only colour either device has.

## Output split: status versus driving cues

The two devices have different physical strengths, so they carry different kinds
of information.

| Device | Carries | Why |
|---|---|---|
| Side RGB LED 3 (blue only) | session **status**: idle, connected, error | ~2 mm and side-mounted, so unreadable mid-corner, but perfectly adequate for something you check before and after a stint |
| 8x13 matrix | **in-the-moment driving cues** only | larger and more central, the only output with a chance of registering in peripheral vision at speed |

The matrix is therefore kept blank for states 0, 1 and 7. Nothing competes with a
driving cue for that space, and a dark matrix during normal running also means an
illuminated matrix always means "something just happened".

## State table

Codes 3-6 are the proposed vocabulary and are **not implemented**. The fastest
rhythm is reserved exclusively for the error state, so urgency reads through
speed alone.

| Code | State | Device | Glyph | Rhythm | Status |
|---|---|---|---|---|---|
| 0 | Idle / not recording | side LED | — | off | implemented |
| 1 | Connected, logging normally | side LED | — | steady on | implemented |
| 2 | Approaching focus corner | matrix | filled triangle pointing up | slow pulse, dim-bright-dim | implemented |
| 3 | Brake reapplication event | matrix | X (diagonal cross) | fast sharp flash, 2-3 blinks then stop | proposed |
| 4 | Manual upshift cue (optional) | matrix | upward arrow / chevron | single quick blink | proposed |
| 5 | Edge Impulse anomaly | matrix | filled circle, centred | slow fade in/out | proposed |
| 6 | Lap complete / session update | matrix | full-width horizontal bar | sweeps across once, then off | proposed |
| 7 | Error / connection lost | side LED | — | fast alternating flash, 80 ms, reserved | implemented |

State 2's pulse is a symmetric triangle wave over `APPROACH_PULSE_PERIOD_MS`
(1600 ms), between brightness 20 and 255. It is deliberately the slowest rhythm
on the board, and it never reaches zero: a cue that goes fully dark is
indistinguishable from the cue having ended.

Distinguishability check: no two matrix cues share both a glyph and a rhythm.
The three most consequential distinctions are also the sharpest -- state 3 (X,
fast blinks) versus state 2 (triangle, slow pulse) differ on shape, rhythm and
duration simultaneously, and the two status states differ on steady versus
fastest-flash.

Code 0 is an addition to the plan's table. Without it there is no honest way to
show "not recording", and the LED would keep claiming "connected" after a
session ends.

## How "approaching a focus corner" is determined

State 2 is the first state that needs to know where the car is *right now*, not
whether telemetry is arriving. `src/corner_approach.py` provides both halves:

`LapDistanceTail` tails the same growing CSV that drives states 0 and 1, reading
only the bytes appended since the previous poll and scanning them newest-first
for a `packet_id == 2` row's `lap_distance`. `CornerApproachMonitor` checks that
against the zones in `config/monza.py`, loaded through
`config.loader.load_track_config()` — the same calibrated boundaries the
post-session analysis uses, so the live cue and the report cannot disagree about
where a corner is. `bridge_client.py` wires them together and only consults them
while the recording is fresh, so a stale session cannot cue a corner.

Three rules turn zone containment into something usable, all tuned in
`config/led_feedback.yaml`:

- **Hysteresis** (`corner_approach_hysteresis_m`, 25 m). Leaving requires
  travelling past the boundary by that margin, so a distance value that jitters
  across the edge cannot toggle the matrix.
- **Direction.** A cue arms only on a crossing into the zone from *before* its
  start. Arriving from the far end means the car went backwards.
  `data/raw/2026-07-28_025428_session.csv` contains that on lap 4 — a block of
  duplicated rows rewinds `lap_distance` from ~2230 m to ~2153 m, inside Roggia —
  and it produced a second Roggia cue in one lap until this rule existed.
- **Rate limiting** (`corner_cue_min_interval_ms`, 20 s), which is plan section
  13's "a single corner cannot produce repeated distracting flashes". It covers
  the case direction cannot: a flashback that rewinds far enough to re-approach
  the same corner legitimately within seconds.

`corner_cue_max_duration_ms` (14 s) cancels a cue that outlives any real pass,
which means stopped, spun or crawling inside the zone rather than approaching it.
Measured across all five recordings in `data/raw/`, a real pass through the
widened band takes 4.3-7.8 s at Turn 1 and 6.6-10.8 s at Roggia. **It must stay
above ~11 s and below `corner_cue_min_interval_ms`.** At 6 s it silently cut
normal cues short part-way through the corner; `tests/simulate_live_led.py`
caught that, and `tests/test_corner_approach.py` now pins both bounds.

Two consequences worth knowing:

- Latency is bounded by `session_logger.py`'s flush every 50 rows, not by
  `led_state_poll_interval_ms`. The file grows in ~1.2 s bursts, so the cue
  typically lights 30-70 m into the zone rather than exactly at its edge. For the
  same reason the tail *retains* its last distance for
  `telemetry_stale_after_ms`; without that the cue would drop out between
  flushes.
- Both Monza zones currently cue, not just one "focus" corner. Roggia's zone is
  550 m long, so its cue runs 8-10 s, which is long for a driving cue. Narrowing
  it is a zone-calibration decision, not an LED one.

### Codes 2-6 imply "connected"

The protocol carries one code at a time, but "connected" and "approaching a
corner" are simultaneously true. Rather than add a second Bridge channel, the
MCU treats codes 2-6 as implying connected and holds the status LED steady while
rendering the matrix cue. Receiving a cue is itself proof that Linux is alive.

So Linux sends e.g. `2` on approach and reverts to `1` afterwards; the status LED
never flickers across that transition. In the sketch this is not special-cased:
`renderStatusLed()`'s `default:` branch already holds the LED steady for any code
that is not idle or error.

An unknown code (anything outside 0-7) holds the status LED steady and logs a
warning, rather than being silently ignored, so a protocol mismatch is visible.

## Open design question for state 3

Brake reapplication (3) will frequently occur **while** approaching the focus
corner (2) -- at Monza T1 that is the expected case, not the exception. One code
at a time cannot express both.

Two options, to be decided when state 3 is built:

1. **Priority ordering** on the MCU: an event cue pre-empts the approach cue for
   the duration of its burst, then the approach cue resumes. No protocol change.
2. **A second Bridge method** for cues, separate from status. Still single-value
   calls, so the reliability constraint holds, but it doubles heartbeat traffic
   and needs a second watchdog.

Option 1 is preferred unless overlapping cues turn out to be genuinely
simultaneous rather than merely concurrent.

## Heartbeat and watchdog

Linux re-sends the current state every `bridge_state_resend_ms`
(`config/led_feedback.yaml`) even when nothing changed. If the sketch hears
nothing for `STATE_TIMEOUT_MS` it shows **state 7**, not state 0.

Reason: if the Python process dies while the LED shows "connected", the LED is
lying about a safety-relevant fact. The heartbeat is what makes "still logging"
distinguishable from "Linux died". State 7 is the one state Linux can never send
about itself, so the MCU has to raise it -- which is what makes it reachable at
all.

Three details that keep this honest:

- **Before Linux has ever called, the state is 0, not 7.** A board powered up
  with no PitWall running is idle, not broken.
- **A clean shutdown sends 0 explicitly** (`bridge_client.py` does this on
  Ctrl-C), so quitting deliberately shows idle rather than an error.
- Recovery is automatic: the timeout is evaluated from the last-received
  timestamp without overwriting the received code, so one heartbeat restores the
  real state.

**`STATE_TIMEOUT_MS` in the sketch must stay comfortably longer than
`bridge_state_resend_ms` in config.** The sketch cannot read the YAML file, so
this pairing is enforced by this document, not by code. Current values: resend
1000 ms, timeout 3000 ms.

## How "connected" is determined

State 1 means *the session CSV that `src/session_logger.py` is writing is still
growing*. `src/bridge_client.py` stats the newest file in the recording
directory and compares its mtime against `telemetry_stale_after_ms`.

Both sides resolve that directory through `session_store.resolve_session_dir()`
(explicit argument, then `PITWALL_SESSION_DIR`, then `data/raw` beside the
checkout). This matters on the UNO Q: `arduino-app-cli` bind-mounts only the App
folder to `/app`, so the LED App cannot see a recording directory outside it.
Set `PITWALL_SESSION_DIR` for the recorder to a directory inside the App folder
rather than relying on which copy of the code is running.

This reads the existing logger's real output. `bridge_client.py` does not import
or wrap `session_logger.py`, `session_analyzer.py`, `brake_analyzer.py`,
`coach.py` or the Flask dashboard, and does not change how any of them behave.
The logger's only change is that its output directory now comes from
`resolve_session_dir()` instead of a hardcoded path; its default is unchanged.

Consequence to be aware of: `session_logger.py` flushes every 50 rows, so mtime
lags packet arrival slightly. `telemetry_stale_after_ms` is 3000 ms to absorb
that. If it were set below roughly 1500 ms the LED would flicker between
connected and idle during a healthy session.

## Notes

- Do not drive the matrix during the first 20-30 seconds after power-on. The
  boot logo is rendering and the datasheet warns that accessing the matrix
  before Linux startup completes can interfere with MCU operation. Not an issue
  when App Lab flashes the sketch after boot.
- `Arduino_LED_Matrix` ships with the UNO Q Zephyr core. Do not install it from
  the library manager.
- `loop()` renders every pass from `millis()` rather than only on state change,
  which state 7's flash already requires. The matrix cues in states 2-6 can
  therefore be added as glyph plus phase functions without restructuring. State 2
  confirmed this: it needed only `triangleUpPixel()`, `drawTriangleUp()`,
  `pulseBrightness()` and one `renderMatrix()` call in `loop()`.
- `drawTriangleUp()` assumes the flat 104-byte frame is **row-major with 13
  columns per row**, which is how `drawBlank()` has always addressed it but which
  nothing in the repo verifies. If the layout is column-major the glyph appears
  rotated. This is the one thing to eyeball the first time state 2 runs on
  hardware; only the glyph is affected, not the state machine.
- The matrix is blanked once on leaving state 2 rather than every pass, so an
  unchanged dark matrix costs no Bridge or SPI traffic.
- `tests/test_sketch_glyph.py` extracts `triangleUpPixel()` and
  `pulseBrightness()` from this .ino by name, compiles them with `g++ -Werror`
  and checks the glyph shape and the pulse's integer arithmetic. That is also
  what keeps the terminal preview in `tests/simulate_live_led.py` honest, since
  it reimplements both in Python. It skips itself where `g++` is absent, and it
  is not a substitute for compiling the sketch: the UNO Q core is usually not
  installed on a development laptop.
