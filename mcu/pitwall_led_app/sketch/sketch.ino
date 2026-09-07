// PitWall LED state renderer for the Arduino UNO Q (STM32U585 side).
//
// Receives one small state code from the Linux side over Bridge RPC and owns
// all glyph and animation timing locally. Linux never sends pixels: see
// mcu/bridge_protocol.md for why, and for the state code table.
//
// Output is split by whether a state matters WHILE DRIVING:
//
//   Side RGB LED 3 -- session status you check before/after a stint
//                     (idle, connected, error). Small and peripheral, which is
//                     fine for status. Driven blue only; no colour coding.
//   8x13 matrix    -- reserved exclusively for in-the-moment driving cues.
//                     States 2 (approaching focus corner) and 5 (Edge Impulse
//                     anomaly) are implemented; states 3, 4 and 6 are not.
//
// Colour carries no meaning anywhere in this design. The matrix is MONOCHROME
// BLUE (UNO Q datasheet ABX00162) and states are encoded as glyph shape, flash
// rhythm and brightness, so nothing needs re-auditing for colour vision
// deficiency.
//
// This is the MCU half of the Arduino App in mcu/pitwall_led_app; arduino-app-cli
// compiles and flashes it when the App is started.

#include <Arduino_LED_Matrix.h>
#include <Arduino_RouterBridge.h>

// ---------------------------------------------------------------------------
// Wire protocol. Keep in sync with src/bridge_client.py.
// ---------------------------------------------------------------------------
static const char *BRIDGE_METHOD = "pitwall_led_state";

static const int STATE_IDLE = 0;       // nothing being recorded: LED off
static const int STATE_CONNECTED = 1;  // logging normally: LED steady on
static const int STATE_APPROACH = 2;   // approaching focus corner: matrix pulse
static const int STATE_ANOMALY = 5;    // Edge Impulse anomaly: matrix circle
static const int STATE_ERROR = 7;      // connection lost: LED fast alternating

// Codes 2-6 are matrix driving cues (see mcu/bridge_protocol.md); 3, 4 and 6 are
// not implemented yet. Every one of them proves Linux is alive, so all are
// treated as "connected" on the status LED rather than as unknown. States 2 and
// 5 must not disturb the status LED: an odd braking window is still a connected
// session.

// Linux re-sends the current state as a heartbeat. Silence past this means the
// Linux side died, which is exactly STATE_ERROR -- Linux cannot report its own
// death, so the MCU raises it. Must stay comfortably longer than
// bridge_state_resend_ms in config/led_feedback.yaml.
static const unsigned long STATE_TIMEOUT_MS = 3000;

// Fastest rhythm on the board, reserved exclusively for STATE_ERROR so urgency
// reads through speed alone. No other state may flash this fast.
static const unsigned long ERROR_FLASH_INTERVAL_MS = 80;

static const unsigned long RENDER_INTERVAL_MS = 10;

// State 2's rhythm: one dim-bright-dim cycle per period, deliberately the
// slowest thing on the board so it reads as ambient information in peripheral
// vision rather than as an alarm. Nothing may approach ERROR_FLASH_INTERVAL_MS.
static const unsigned long APPROACH_PULSE_PERIOD_MS = 1600;

// Never fully dark at the bottom of the pulse: a cue that reaches zero is
// indistinguishable from the cue having ended.
static const uint8_t APPROACH_MIN_BRIGHTNESS = 20;
static const uint8_t APPROACH_MAX_BRIGHTNESS = 255;

// State 5's rhythm: slower than state 2's pulse, so the two read differently in
// peripheral vision even before the glyph is recognised. Still nowhere near
// ERROR_FLASH_INTERVAL_MS, since an anomaly is information, not an alarm.
static const unsigned long ANOMALY_FADE_PERIOD_MS = 2400;
static const uint8_t ANOMALY_MIN_BRIGHTNESS = 20;
static const uint8_t ANOMALY_MAX_BRIGHTNESS = 255;

// Radius of state 5's circle in HALF-pixels, so the centre can sit between rows
// (3.5, 6) without floating point. 7 gives a disc 8 rows tall and 7 columns
// wide: as large as the matrix allows vertically while staying round.
static const int ANOMALY_RADIUS_HALF_PIXELS = 7;

static const uint8_t MATRIX_ROWS = 8;
static const uint8_t MATRIX_COLS = 13;
static const uint16_t MATRIX_PIXELS = MATRIX_ROWS * MATRIX_COLS;

// RGB LED 3 (D27401) is active-low: LOW turns a channel on. Only the blue
// channel is used; red and green are held off so no colour can appear.
static const uint8_t STATUS_LED_PIN = LED3_B;

Arduino_LED_Matrix matrix;

static volatile int g_state = STATE_IDLE;
static volatile unsigned long g_stateReceivedAt = 0;
static volatile bool g_everHeardFromLinux = false;

static int g_loggedState = -1;  // -1 forces the first log line
static bool g_matrixLit = false;  // avoids re-pushing a blank frame every pass

static void setStatusLed(bool on) {
  digitalWrite(STATUS_LED_PIN, on ? LOW : HIGH);
}

static void drawBlank() {
  uint8_t frame[MATRIX_PIXELS];
  memset(frame, 0, sizeof(frame));
  matrix.draw(frame);
}

// Filled triangle pointing up: single-pixel apex on the top row widening to the
// full width on the bottom row. Chosen for state 2 because a solid mass reads at
// a glance and shares no shape with any other planned cue.
//
// Assumes the flat frame array is row-major with MATRIX_COLS per row, which is
// how drawBlank() has always addressed it. If the layout is actually
// column-major the glyph appears rotated -- the one thing worth eyeballing the
// first time this runs on hardware.
static bool triangleUpPixel(uint8_t row, uint8_t col) {
  const int centre = MATRIX_COLS / 2;             // 6
  const int halfWidth = (row * centre) / (MATRIX_ROWS - 1);
  const int offset = (int)col - centre;
  return (offset >= -halfWidth) && (offset <= halfWidth);
}

static void drawTriangleUp(uint8_t brightness) {
  uint8_t frame[MATRIX_PIXELS];
  for (uint8_t row = 0; row < MATRIX_ROWS; row++) {
    for (uint8_t col = 0; col < MATRIX_COLS; col++) {
      frame[row * MATRIX_COLS + col] =
          triangleUpPixel(row, col) ? brightness : 0;
    }
  }
  matrix.draw(frame);
}

// Filled circle, centred: the shape with no corners and no direction, which is
// why state 5 uses it. "Something about this window was unusual" points nowhere,
// unlike state 2's triangle.
//
// Half-pixel coordinates put the centre at row 3.5, col 6 -- the true centre of
// an 8x13 grid -- using integers only. Same row-major assumption as
// triangleUpPixel().
static bool circlePixel(uint8_t row, uint8_t col) {
  const int dRow = 2 * (int)row - (MATRIX_ROWS - 1);
  const int dCol = 2 * (int)col - (MATRIX_COLS - 1);
  const int radius = ANOMALY_RADIUS_HALF_PIXELS;
  return (dRow * dRow + dCol * dCol) <= (radius * radius);
}

static void drawCircle(uint8_t brightness) {
  uint8_t frame[MATRIX_PIXELS];
  for (uint8_t row = 0; row < MATRIX_ROWS; row++) {
    for (uint8_t col = 0; col < MATRIX_COLS; col++) {
      frame[row * MATRIX_COLS + col] = circlePixel(row, col) ? brightness : 0;
    }
  }
  matrix.draw(frame);
}

// Symmetric triangle wave, so the fade up and the fade down take equal time and
// the cue has no visible "snap" back to dim. Derived from millis() alone, so no
// phase state has to be kept or reset between states.
static uint8_t triangleWave(unsigned long now,
                           unsigned long period,
                           uint8_t minBrightness,
                           uint8_t maxBrightness) {
  const unsigned long half = period / 2;
  unsigned long phase = now % period;
  if (phase >= half) {
    phase = period - phase;  // descending half
  }

  const unsigned long span = maxBrightness - minBrightness;
  return (uint8_t)(minBrightness + (phase * span) / half);
}

static uint8_t pulseBrightness(unsigned long now) {
  return triangleWave(now, APPROACH_PULSE_PERIOD_MS, APPROACH_MIN_BRIGHTNESS,
                      APPROACH_MAX_BRIGHTNESS);
}

static uint8_t fadeBrightness(unsigned long now) {
  return triangleWave(now, ANOMALY_FADE_PERIOD_MS, ANOMALY_MIN_BRIGHTNESS,
                      ANOMALY_MAX_BRIGHTNESS);
}

static void renderMatrix(int state, unsigned long now) {
  if (state == STATE_APPROACH) {
    drawTriangleUp(pulseBrightness(now));
    g_matrixLit = true;
    return;
  }

  if (state == STATE_ANOMALY) {
    drawCircle(fadeBrightness(now));
    g_matrixLit = true;
    return;
  }

  // Every other state keeps the matrix dark, so an illuminated matrix always
  // means something is happening right now.
  if (g_matrixLit) {
    drawBlank();
    g_matrixLit = false;
  }
}

// Bridge callback. Returns the code it accepted so the Linux side can confirm
// the round trip rather than assuming the message landed.
static int setPitwallState(int code) {
  g_state = code;
  g_stateReceivedAt = millis();
  g_everHeardFromLinux = true;
  return code;
}

// Resolve what to show now, without mutating g_state. Keeping the received code
// intact means a heartbeat arriving after a timeout recovers on its own.
static int resolveState(unsigned long now) {
  // Before Linux has ever called, nothing is wrong -- it just is not running.
  // That is idle, not an error.
  if (!g_everHeardFromLinux) {
    return STATE_IDLE;
  }

  if ((now - g_stateReceivedAt) > STATE_TIMEOUT_MS) {
    return STATE_ERROR;
  }

  return g_state;
}

static void renderStatusLed(int state, unsigned long now) {
  switch (state) {
    case STATE_ERROR:
      setStatusLed(((now / ERROR_FLASH_INTERVAL_MS) % 2) == 0);
      break;

    case STATE_IDLE:
      setStatusLed(false);
      break;

    default:
      // STATE_CONNECTED and the matrix cue codes 2-6 all mean Linux is logging.
      setStatusLed(true);
      break;
  }
}

static void logStateChange(int state) {
  switch (state) {
    case STATE_IDLE:
      Monitor.println("state 0: idle, not recording (status LED off)");
      break;
    case STATE_CONNECTED:
      Monitor.println("state 1: connected, logging (status LED steady)");
      break;
    case STATE_APPROACH:
      Monitor.println(
          "state 2: approaching focus corner (triangle pulse, LED still steady)");
      break;
    case STATE_ANOMALY:
      Monitor.println(
          "state 5: braking anomaly (circle fade, LED still steady)");
      break;
    case STATE_ERROR:
      Monitor.println("state 7: connection lost (status LED fast flash)");
      break;
    default:
      Monitor.print("state ");
      Monitor.print(state);
      Monitor.println(": matrix cue not implemented; treated as connected");
      break;
  }
}

void setup() {
  // Red and green are driven off permanently; only blue is ever used.
  pinMode(LED3_R, OUTPUT);
  pinMode(LED3_G, OUTPUT);
  pinMode(LED3_B, OUTPUT);
  digitalWrite(LED3_R, HIGH);
  digitalWrite(LED3_G, HIGH);
  setStatusLed(false);

  // The matrix is reserved for driving cues and is dark whenever none is
  // active. 8-bit grayscale is what makes state 2's fade smooth rather than a
  // two-level blink.
  matrix.begin();
  matrix.setGrayscaleBits(8);
  drawBlank();
  g_matrixLit = false;

  Bridge.begin();
  Monitor.begin();

  // Linux is the only caller, so nothing is sent before Python is up and no
  // startup handshake is needed here.
  Bridge.provide(BRIDGE_METHOD, setPitwallState);

  Monitor.println("PitWall LED renderer ready; waiting for state from Linux");
}

void loop() {
  // Rendered every pass, not only on change, so animated rhythms are possible.
  unsigned long now = millis();
  int state = resolveState(now);

  if (state != g_loggedState) {
    logStateChange(state);
    g_loggedState = state;
  }

  renderStatusLed(state, now);
  renderMatrix(state, now);

  delay(RENDER_INTERVAL_MS);
}
