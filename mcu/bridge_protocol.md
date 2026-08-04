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
`mcu/led_matrix_controller/sketch.ino`. Both must be edited together.

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

Codes 2-6 are the proposed vocabulary and are **not implemented**. The fastest
rhythm is reserved exclusively for the error state, so urgency reads through
speed alone.

| Code | State | Device | Glyph | Rhythm | Status |
|---|---|---|---|---|---|
| 0 | Idle / not recording | side LED | — | off | implemented |
| 1 | Connected, logging normally | side LED | — | steady on | implemented |
| 2 | Approaching focus corner | matrix | filled triangle pointing up | slow pulse, dim-bright-dim | proposed |
| 3 | Brake reapplication event | matrix | X (diagonal cross) | fast sharp flash, 2-3 blinks then stop | proposed |
| 4 | Manual upshift cue (optional) | matrix | upward arrow / chevron | single quick blink | proposed |
| 5 | Edge Impulse anomaly | matrix | filled circle, centred | slow fade in/out | proposed |
| 6 | Lap complete / session update | matrix | full-width horizontal bar | sweeps across once, then off | proposed |
| 7 | Error / connection lost | side LED | — | fast alternating flash, 80 ms, reserved | implemented |

Distinguishability check: no two matrix cues share both a glyph and a rhythm.
The three most consequential distinctions are also the sharpest -- state 3 (X,
fast blinks) versus state 2 (triangle, slow pulse) differ on shape, rhythm and
duration simultaneously, and the two status states differ on steady versus
fastest-flash.

Code 0 is an addition to the plan's table. Without it there is no honest way to
show "not recording", and the LED would keep claiming "connected" after a
session ends.

### Codes 2-6 imply "connected"

The protocol carries one code at a time, but "connected" and "approaching a
corner" are simultaneously true. Rather than add a second Bridge channel, the
MCU treats codes 2-6 as implying connected and holds the status LED steady while
rendering the matrix cue. Receiving a cue is itself proof that Linux is alive.

So Linux sends e.g. `2` on approach and reverts to `1` afterwards; the status LED
never flickers across that transition.

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
growing*. `src/bridge_client.py` stats the newest file in `data/raw/` and
compares its mtime against `telemetry_stale_after_ms`.

This reads the existing logger's real output. It does not import, wrap or modify
`session_logger.py`, `session_analyzer.py`, `brake_analyzer.py`, `coach.py` or
the Flask dashboard.

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
  therefore be added as glyph plus phase functions without restructuring.
