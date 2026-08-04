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
//   8x13 matrix    -- reserved exclusively for in-the-moment driving cues
//                     (states 2-6, not yet implemented).
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
static const int STATE_ERROR = 7;      // connection lost: LED fast alternating

// Codes 2-6 are matrix driving cues (see mcu/bridge_protocol.md). They are not
// implemented yet, but receiving one already proves Linux is alive, so they are
// treated as "connected" on the status LED rather than as unknown.

// Linux re-sends the current state as a heartbeat. Silence past this means the
// Linux side died, which is exactly STATE_ERROR -- Linux cannot report its own
// death, so the MCU raises it. Must stay comfortably longer than
// bridge_state_resend_ms in config/led_feedback.yaml.
static const unsigned long STATE_TIMEOUT_MS = 3000;

// Fastest rhythm on the board, reserved exclusively for STATE_ERROR so urgency
// reads through speed alone. No other state may flash this fast.
static const unsigned long ERROR_FLASH_INTERVAL_MS = 80;

static const unsigned long RENDER_INTERVAL_MS = 10;

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

static void setStatusLed(bool on) {
  digitalWrite(STATUS_LED_PIN, on ? LOW : HIGH);
}

static void drawBlank() {
  uint8_t frame[MATRIX_PIXELS];
  memset(frame, 0, sizeof(frame));
  matrix.draw(frame);
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

  // The matrix is reserved for driving cues (states 2-6) and stays blank until
  // the first of those is implemented.
  matrix.begin();
  matrix.setGrayscaleBits(8);
  drawBlank();

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

  delay(RENDER_INTERVAL_MS);
}
