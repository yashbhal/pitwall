# PitWall

## F1 25 Beginner Sim-Racing Practice Coach

**Project reference document**  
**Status:** Final MVP plan before build  
**Target build time:** 2 weeks  
**Primary track:** Monza  
**Game/platform:** EA SPORTS F1 25 on PS5  
**Input hardware:** Logitech steering wheel and pedals  
**Core board:** Arduino UNO Q  
**Required platforms:** Arduino App Lab and Edge Impulse

---

## 1. One-Sentence Description

PitWall is a beginner-friendly sim-racing practice coach that receives live F1 25 telemetry from a PS5, identifies repeatable braking and shifting habits, gives one focused drill after each practice session, and measures whether the driver improves.

---

## 2. Problem

F1 25 provides a racing line, lap delta, suggested gears, and post-race information. These can show that a driver is slower, but they do not turn a beginner's telemetry into a simple answer to:

> What should I practice next, and did that practice actually help?

Raw telemetry graphs are difficult for beginners to interpret. PitWall converts session data into one clear, measurable practice objective at a time.

---

## 3. Product Goal

PitWall should help a beginner improve through a repeatable practice loop:

text

`Drive a baseline stint         ↓ Measure braking and shifting patterns by corner         ↓ Identify one highest-priority issue         ↓ Give one simple drill and success metric         ↓ Drive a focused follow-up stint         ↓ Measure improvement and choose the next focus`

## Example

text

`Baseline: Turn 1 brake onset varied by 22 m. Brake was reapplied 4 times. Practice drill: Use the 150 m board as a reference. Brake once, firmly, then release smoothly before turning. Complete 5 laps without brake reapplication. Follow-up: Brake onset variation: 22 m → 9 m Brake reapplications: 4 → 1 Sector 1: 0.24 s faster`

---

## 4. MVP Definition

## The MVP must do all of this

1. Receive F1 25 telemetry from PS5 over the local network.
    
2. Log telemetry to CSV or SQLite.
    
3. Identify the current lap and selected Monza corner.
    
4. Measure braking onset, brake reapplication, RPM-limiter dwell, and gear consistency.
    
5. Produce one prioritized post-session practice drill.
    
6. Show a physical live cue with the UNO Q LED matrix.
    
7. Run one Edge Impulse model locally on the UNO Q.
    
8. Use Arduino App Lab for deployment and visible project integration.
    
9. Demonstrate a baseline session and a follow-up session with a measurable change.
    

## The MVP does not need to do this

- Control or modify the Logitech wheel
    
- Use haptic motors
    
- Tell the user the universally perfect brake point
    
- Tell the user the universally perfect gear
    
- Use an LLM
    
- Analyze multiple tracks
    
- Compare against real drivers or online ghosts
    
- Use AI opponents as a reference
    
- Build a custom physical enclosure
    
- Build a custom screen
    

---

## 5. What PitWall Claims

## Valid claims

- PitWall identifies repeated braking and shifting behaviors.
    
- PitWall helps beginners focus on one practice skill at a time.
    
- PitWall measures consistency and improvement across practice stints.
    
- PitWall uses Edge Impulse to detect telemetry windows that differ from the driver's established baseline.
    
- PitWall uses the UNO Q's Linux processor for telemetry analysis and its microcontroller for live physical feedback.
    

## Claims to avoid

- “PitWall knows the optimal racing line.”
    
- “PitWall knows the universally perfect braking point.”
    
- “PitWall knows the perfect gear for every corner.”
    
- “High anomaly score means bad driving.”
    
- “PitWall replaces a professional racing coach.”
    
- “PitWall guarantees a faster lap time.”
    

---

## 6. User Story

## Beginner user

A player has F1 25 on PS5 and drives with a Logitech wheel. They may still use assists such as ABS, traction control, racing line, and Manual with Suggested Gear.

1. They power PitWall and open its dashboard on a laptop or phone.
    
2. They choose Monza and select their assist profile.
    
3. They drive 8 normal baseline laps.
    
4. PitWall quietly logs the session and gives limited LED feedback.
    
5. At session end, PitWall identifies one priority, such as Turn 1 brake consistency.
    
6. PitWall gives a specific drill and measurable target.
    
7. The player completes 5 to 10 focused laps.
    
8. PitWall compares the follow-up result against baseline.
    
9. The player sees whether they improved before moving to another skill.
    

---

## 7. System Architecture

text

`┌──────────────────────────────┐ │ PS5 running EA SPORTS F1 25  │ │ Logitech wheel and pedals    │ └──────────────┬───────────────┘                │               │ F1 25 UDP telemetry over local Wi-Fi               │               ▼ ┌──────────────────────────────────────────────┐ │ Arduino UNO Q: Qualcomm Linux MPU             │ │                                              │ │ - Python UDP telemetry listener              │ │ - Packet parser                              │ │ - Session logger: CSV or SQLite              │ │ - Corner segmentation                        │ │ - Rule-based metrics engine                  │ │ - Practice drill recommender                 │ │ - Flask dashboard                            │ │ - Edge Impulse anomaly inference             │ └────────────────┬─────────────────────────────┘                  │                 │ Arduino Bridge RPC                 │                 ▼ ┌──────────────────────────────────────────────┐ │ Arduino UNO Q: STM32 MCU                      │ │                                              │ │ - Built-in 13x8 RGB LED matrix               │ │ - Live state and focus-corner feedback       │ └──────────────────────────────────────────────┘`

The UNO Q combines a Linux-capable MPU with an STM32 microcontroller and Arduino Bridge RPC, making the MPU/MCU split appropriate for this project.[[docs.arduino](https://docs.arduino.cc/hardware/uno-q)]

---

## 8. Hardware

## Required

|Item|Purpose|
|---|---|
|Arduino UNO Q|Main compute board|
|USB-C power supply|Powers UNO Q|
|PS5 with F1 25|Telemetry source|
|Logitech wheel and pedals|Existing driving controls|
|Home Wi-Fi network|Connects PS5 and UNO Q|
|Laptop or phone|Opens browser dashboard|
|USB-C data cable|Initial setup and debugging|

## No extra hardware required for MVP

The UNO Q's built-in LED matrix is the physical output. Do not buy an OLED, motors, motor drivers, or an enclosure for Version 1.

## Phase 2 hardware

- I2C OLED display
    
- Vibration motors on wheel rim or pedals
    
- Motor driver/transistor circuit
    
- 3D printed enclosure
    
- Rotary encoder for selecting training modes
    

---

## 9. Telemetry Inputs

The F1 game UDP system supports output for external applications and hardware, and available community parsers support F1 25 telemetry layouts.[[forums.ea](https://forums.ea.com/t5/s/tghpe58374/attachments/tghpe58374/f1-games-game-info-hub-en/61/4/Data%20Output%20from%20F1%2025%20v3.pdf)]

PitWall should initially log only the fields needed for the MVP.

|Data|Why it is useful|
|---|---|
|Timestamp|Synchronizes data and events|
|Lap number|Groups data into laps|
|Lap distance|Identifies approximate track position and corner|
|Speed|Measures approach and minimum speed|
|Brake percentage|Detects brake onset and reapplication|
|Throttle percentage|Later use for exit smoothness|
|Steering angle|Context for braking and turning|
|Gear|Measures gear consistency|
|Engine RPM|Detects limiter dwell and shift timing|
|Wheel speeds, if available|Future lockup/wheelspin logic|
|Longitudinal/lateral G-force|Future braking and cornering analysis|
|Lap validity / invalidation|Filters unusable attempts|
|Track ID|Ensures the correct track profile is loaded|
|Session type|Distinguishes practice/time trial/race contexts|

**Important:** Confirm exact field names, units, packet IDs, and packet rate against the official F1 25 UDP specification during implementation. Do not hardcode assumptions from old F1 game versions.

---

## 10. Assist-Aware Design

PitWall must ask the user to set their assist profile at the beginning of a session.

## Assist profile fields

text

`Gearbox: - Automatic - Manual with Suggested Gear - Manual ABS: - On - Off Traction control: - Full - Medium - Off Racing line: - Full - Corners only - Off`

## Coaching by skill level

|User profile|PitWall focus|
|---|---|
|Automatic + ABS + Full TC|Brake consistency, steering smoothness, track familiarity|
|Manual with Suggested Gear + ABS|Shift consistency, brake release, throttle smoothness|
|Manual + Medium/Off TC|Shift timing, wheelspin, braking control|
|Manual + ABS off + TC off|Lockups, wheelspin, trail braking, advanced consistency|

Do not score lockups aggressively when ABS is enabled or wheelspin aggressively when full traction control is enabled. Assists can hide those physical events.

---

## 11. Rule-Based Coaching Engine

The core coaching engine is rule-based, transparent, and independent of ML.

## Required Version 1 metrics

|Metric|Detection logic|Coaching value|
|---|---|---|
|Brake onset|First sustained brake input above threshold within a corner approach window|Measures consistency|
|Brake onset variation|Spread of brake-onset locations across valid attempts|Teaches use of a repeatable marker|
|Brake reapplication|Brake decreases then rises again during a braking phase|Identifies corrective/pulsed braking|
|RPM-limiter dwell|RPM remains near limiter while throttle is high before upshift|Helps manual upshift timing|
|Gear consistency|Minimum or exit gear varies across similar attempts|Helps learner use repeatable gears|
|Invalid attempts|Invalid lap/off-track/spin event|Exclude from clean comparison set|
|Corner attempt count|Number of valid tries per corner|Avoids conclusions from too little data|

## Suggested initial thresholds

These are starting points only. Store them in a configuration file so they can be tuned later.

text

`brake_onset_threshold: 0.10 minimum_brake_duration_ms: 150 brake_reapplication_gap_ms: 150 brake_reapplication_window_ms: 2000 rpm_limiter_margin_rpm: 300 rpm_limiter_dwell_ms: 300 minimum_valid_attempts_for_drill: 5 brake_variation_warning_meters: 15`

---

## 12. Coaching Templates

Use fixed templates. Do not use a free-form LLM in the MVP.

## Brake consistency

text

`Focus: Turn {corner} brake consistency. Your brake start varied by {variation_m} m across {attempts} valid entries. Drill: Choose one visual braking marker. For the next {lap_count} laps, begin braking within the same target window. Do not chase lap time. Prioritize repeatability.`

## Brake reapplication

text

`Focus: Turn {corner} brake release. You reapplied the brake {count} times across {attempts} attempts. Drill: Brake once in a straight line. As steering increases, release brake pressure smoothly. Aim for zero brake reapplications over the next {lap_count} laps.`

## Late upshift / limiter dwell

text

`Focus: upshift timing. You spent {dwell_ms} ms near the RPM limiter before upshifting. Drill: Upshift before holding the limiter. For the next {lap_count} laps, aim to reduce limiter time on the selected straight.`

## Gear inconsistency

text

`Focus: Turn {corner} gear consistency. You used {gear_options} as the corner gear across similar attempts. Drill: Use {recommended_gear} for the next {lap_count} attempts. Compare exit stability and exit speed before changing again.`

## Unusual telemetry pattern

text

`Notice: Turn {corner} differed from your current normal pattern. This does not automatically mean the attempt was bad. Review brake, steering, and gear traces after the session.`

---

## 13. Live Feedback

Live feedback should be minimal. The driver should not need to read or analyze a screen while driving.

## UNO Q LED Matrix States

|Color / pattern|Meaning|
|---|---|
|Green|System connected and logging normally|
|Yellow|Approaching current focus corner|
|Red flash|Brake reapplication or major detected event|
|Blue flash|Optional manual upshift cue|
|Purple|Edge Impulse anomaly score above current threshold|
|White pulse|Lap complete / session state update|
|Red/blue alternating|Error or telemetry connection lost|

## Live feedback rules

- Do not show long text while driving.
    
- Do not give an exact braking-point command in the MVP.
    
- Do not fire feedback constantly.
    
- Rate-limit alerts so a single corner cannot produce repeated distracting flashes.
    
- Prefer post-lap and post-session analysis for detailed advice.
    

---

## 14. Dashboard

## Technology

**Primary dashboard:** Flask or FastAPI web application hosted on the UNO Q Linux MPU.

Access it from a browser on the same local network:

text

`http://<uno-q-ip-address>:<port>`

## Required dashboard screens

## Session setup

- Track
    
- Assist profile
    
- Gearbox mode
    
- Start/stop recording
    
- Connection status
    

## Live session view

- Current lap number
    
- Current gear and RPM
    
- Brake and throttle bars
    
- Current corner
    
- Event count
    
- Current session focus
    

## Post-session report

- Highest-priority issue
    
- Drill recommendation
    
- Per-corner summary
    
- Brake onset variation
    
- Brake reapplication counts
    
- RPM-limiter dwell
    
- Gear consistency
    
- Baseline versus follow-up comparison
    
- Edge Impulse anomaly trend, if enabled
    

## Dashboard design principle

The primary screen must answer:

1. What should I practice?
    
2. Why was that chosen?
    
3. What measurable target should I hit?
    
4. Did I improve?
    

---

## 15. Edge Impulse Plan

## Required use

Edge Impulse must be used as a visible, real part of the project because it is a hackathon partner.

## Selected model type

**Time-series anomaly detection using GMM or K-means.**

The model learns a representation of nominal behavior and scores new telemetry windows according to how much they differ from that learned baseline.[[docs.edgeimpulse](https://docs.edgeimpulse.com/studio/projects/learning-blocks/blocks/anomaly-detection-custom)]

## Correct role

Edge Impulse is an additional signal, not the sole source of coaching advice.

text

`Rule-based metrics: - Tell the user what is concrete and measurable Edge Impulse anomaly score: - Flags an attempt that differs from the user's normal baseline Combined: - The rule engine assigns drills - Edge Impulse adds a "this was unusual" signal`

## Training dataset

- One track only: Monza
    
- One selected corner initially: Turn 1
    
- 20 to 30 laps of normal practice target
    
- Use 1 to 2 second telemetry windows around braking onset
    
- Inputs: brake, throttle, steering, speed, RPM, gear, G-force, wheel speeds if stable/available
    
- Exclude obviously invalid/off-track attempts where possible
    
- Do not claim the training data is objectively “good driving”
    
- Call it a **personal nominal baseline**
    

## Model output

text

`anomaly_score: float threshold: float is_unusual: boolean`

## Validation language

Use this language in the project:

> “The Edge Impulse model identifies telemetry windows that are unusual relative to the driver's established baseline. Rule-based telemetry metrics provide the actionable coaching explanation.”

Do not call an anomaly score a “bad-driving score.”

## Deployment

Deploy the model to UNO Q using the App Lab and Edge Impulse integration flow, then verify the deployed model is the custom PitWall model rather than a sample/default model. Edge Impulse documents UNO Q deployment through App Lab.[[docs.edgeimpulse](https://docs.edgeimpulse.com/hardware/deployments/run-arduino-app-lab)]

---

## 16. Arduino App Lab Plan

App Lab must be used visibly and meaningfully, but it should not become a single point of failure.

## App Lab responsibilities

- Initial UNO Q setup
    
- Build/deploy MCU code for LED matrix behavior
    
- Create or import the Edge Impulse model integration
    
- Deploy and run the UNO Q application
    
- Capture screenshots/video proving App Lab use for the final submission
    

## Development fallback

If App Lab becomes unstable:

- Use SSH to access the UNO Q Linux environment directly.
    
- Run Python telemetry/logger/dashboard software directly.
    
- Use command-line tools and documented deployment paths where possible.
    
- Keep App Lab involved for the MCU/LED and Edge Impulse integration evidence if possible.
    

Official Arduino documentation supports SSH access to the UNO Q.[[docs.arduino](https://docs.arduino.cc/tutorials/uno-q/ssh)]

## Rule

Once a working App Lab version is confirmed, do not update it during the build unless necessary.

---

## 17. Development Stack

text

`Board: - Arduino UNO Q MPU: - Debian Linux - Python 3 - UDP sockets - CSV and/or SQLite - Flask or FastAPI - Edge Impulse runtime/deployment MCU: - Arduino/C++ or App Lab MCU project - Built-in LED matrix control - Arduino Bridge RPC Networking: - PS5 and UNO Q connected to same local Wi-Fi network Game: - EA SPORTS F1 25 on PS5 - UDP telemetry configured to send to UNO Q local IP`

---

## 18. Folder Structure

text

`pitwall/ ├── README.md ├── docs/ │   ├── architecture.md │   ├── telemetry-fields.md │   ├── test-plan.md │   └── demo-script.md ├── config/ │   ├── monza_corners.yaml │   ├── thresholds.yaml │   └── assist_profiles.yaml ├── data/ │   ├── raw/ │   ├── processed/ │   └── sessions/ ├── src/ │   ├── udp_listener.py │   ├── packet_parser.py │   ├── session_logger.py │   ├── corner_segmenter.py │   ├── metrics.py │   ├── detectors.py │   ├── coaching.py │   ├── edge_impulse_runtime.py │   ├── bridge_client.py │   └── web_app.py ├── mcu/ │   ├── led_matrix_controller/ │   └── bridge_protocol.md ├── edge_impulse/ │   ├── dataset_notes.md │   └── model_version.txt └── tests/     ├── test_detectors.py    ├── test_corner_segmenter.py    └── replay_telemetry.py`

---

## 19. Data Model

## Session record

json

`{   "session_id": "2026-07-XX_monza_baseline_01",  "track": "Monza",  "game": "F1 25",  "platform": "PS5",  "wheel": "Logitech",  "gearbox_mode": "Manual with Suggested Gear",  "abs": true,  "traction_control": "Medium",  "racing_line": "Corners only",  "start_time": "ISO-8601 timestamp",  "lap_count": 8 }`

## Corner attempt record

json

`{   "session_id": "session-id",  "lap_number": 3,  "corner_id": "T1",  "valid_attempt": true,  "brake_onset_distance_m": 147.2,  "brake_reapplication_count": 1,  "minimum_gear": 2,  "minimum_speed_kph": 82,  "limiter_dwell_ms": 0,  "edge_impulse_anomaly_score": 0.18,  "events": [] }`

---

## 20. Monza Scope

## Initial corner focus

Start with **Monza Turn 1** because it has:

- A clear, heavy braking zone
    
- Useful brake-onset data
    
- A common beginner braking challenge
    
- A natural visual braking-marker concept
    
- Enough repeated attempts per session to build a dataset quickly
    

## Later Monza corners

- Turn 4 / Roggia: braking and downshift consistency
    
- Lesmo 1: entry and gear consistency
    
- Ascari: throttle and stability
    
- Parabolica/Alboreto: smooth throttle exit
    

Do not implement these until Turn 1 works.

---

## 21. Two-Week Schedule

## Day 1: Environment Validation

## Goals

- Boot UNO Q
    
- Confirm Wi-Fi
    
- Confirm SSH
    
- Confirm App Lab detection
    
- Run LED matrix example
    
- Run a simple Bridge RPC example
    

## Exit criteria

text

`[ ] UNO Q boots reliably [ ] SSH access works [ ] App Lab can discover the board [ ] LED matrix can be controlled [ ] MCU and MPU can exchange a simple Bridge message`

---

## Days 2 to 4: Telemetry Pipeline

## Goals

- Configure F1 25 UDP telemetry on PS5
    
- Receive packets on UNO Q
    
- Parse required fields
    
- Save raw and parsed telemetry
    
- Record at least one real Monza session
    

## Exit criteria

text

`[ ] PS5 sends telemetry to UNO Q [ ] Python listener receives data reliably [ ] CSV files are created [ ] Speed, brake, throttle, gear, RPM, lap distance are correct [ ] Data can be replayed from saved CSV without PS5 running`

---

## Days 5 to 7: Metrics and Coaching

## Goals

- Implement Turn 1 segmentation
    
- Implement brake onset
    
- Implement brake onset variation
    
- Implement brake reapplication
    
- Implement limiter dwell
    
- Implement gear consistency
    
- Generate one post-session drill
    

## Exit criteria

text

`[ ] Turn 1 attempts are identified [ ] Brake onset is logged per attempt [ ] Brake reapplication count is logged [ ] Gear/RPM metrics are logged [ ] A session produces one drill recommendation`

---

## Days 8 to 9: Dashboard and LED Feedback

## Goals

- Build Flask/FastAPI dashboard
    
- Add session summary page
    
- Add baseline versus follow-up comparison
    
- Add LED matrix state messages via Bridge RPC
    

## Exit criteria

text

`[ ] Dashboard loads from phone/laptop browser [ ] Dashboard shows session metrics [ ] LED is green during normal collection [ ] LED indicates focus corner/event state [ ] Dashboard produces a readable drill card`

---

## Day 10: Core Demonstration

## Goals

- Run baseline stint
    
- Receive a drill
    
- Run follow-up stint
    
- Capture metrics
    
- Record screen/gameplay/video proof
    

## Exit criteria

text

`[ ] Baseline data saved [ ] Follow-up data saved [ ] At least one measurable metric changed [ ] A complete end-to-end demo exists without Edge Impulse`

This is the core project. Protect this milestone.

---

## Days 11 to 12: Edge Impulse

## Goals

- Prepare normal telemetry windows
    
- Train GMM/K-means anomaly model
    
- Deploy custom model to UNO Q through App Lab integration
    
- Log anomaly score during replay/live inference
    

## Exit criteria

text

`[ ] Edge Impulse project exists [ ] Model trains successfully [ ] Custom model deploys to UNO Q [ ] Model output/anomaly score is visible in logs/dashboard [ ] App Lab screenshots demonstrate integration`

---

## Day 13: Polish and Documentation

## Goals

- Clean dashboard text
    
- Create architecture diagram
    
- Take build photos
    
- Prepare code repository
    
- Write Hackster project documentation
    
- Capture screenshots of App Lab and Edge Impulse
    

---

## Day 14: Demo Video and Submission

## Goals

- Record final video in a known-good network environment
    
- Do not add major features
    
- Upload documentation and source code
    
- Submit before deadline
    

---

## 22. Acceptance Tests

## Connectivity

text

`[ ] PS5 UDP packets arrive at UNO Q [ ] Packet loss does not prevent session logging [ ] UNO Q dashboard is reachable from local network [ ] Telemetry replay works from stored file`

## Metrics

text

`[ ] Brake onset is detected for Turn 1 [ ] Brake onset variation changes when intentionally varying braking [ ] Brake reapplication increases when intentionally braking twice [ ] Limiter dwell increases when intentionally holding a gear too long [ ] Gear consistency metric reflects deliberate gear changes`

## Physical output

text

`[ ] LED matrix turns green when telemetry is healthy [ ] LED changes near focus corner [ ] LED flashes when a brake reapplication is detected [ ] MCU receives message from Linux MPU through Bridge RPC`

## Edge Impulse

text

`[ ] Model is trained on PitWall telemetry [ ] Model is deployed to UNO Q [ ] Model produces a live/replayed anomaly score [ ] Dashboard displays score without calling it “bad driving”`

## Product outcome

text

`[ ] A baseline session produces one prioritized drill [ ] Follow-up session is compared against baseline [ ] At least one metric is visibly improved or honestly reported as unchanged`

---

## 23. Risk Register

|Risk|Impact|Mitigation|
|---|---|---|
|App Lab bug/regression|Development blocked|Validate Day 1, use SSH/Python/Flask fallback|
|PS5 telemetry not arriving|Core project blocked|Test by Day 4; validate IP, port, Wi-Fi, game settings|
|Incorrect packet parser|Metrics wrong|Log raw packets, compare fields to official specification|
|Dashboard takes too long|Delays core demo|Build simple HTML first, polish later|
|Edge Impulse deployment issue|ML requirement at risk|Start model work by Day 11; keep core independent; verify custom model version|
|Anomaly model gives unclear result|Weak coaching|Keep drills rule-based; anomaly score is secondary|
|Assist settings hide lockups/spin|Some detectors unusable|Focus on brake consistency, reapplication, RPM, gear metrics|
|Feature creep|Project not finished|No haptics, OLED, LLM, AI ghosts, or extra tracks before core demo|
|Wi-Fi unreliable at demo|Live demo fails|Record controlled demo video; keep CSV replay mode|
|No improvement in follow-up|Weak story|Report honestly; demonstrate measurable consistency even if lap time does not improve|

---

## 24. Phase 2 Roadmap

Only begin after MVP is complete.

1. Haptic vibration motors on Logitech wheel rim or pedals
    
2. OLED display with short text cues
    
3. Additional Monza corners
    
4. More circuits
    
5. Manual-shifting training mode
    
6. Wheelspin and lockup analysis for reduced-assist drivers
    
7. AI Reference Mode using a selected high-difficulty AI lap
    
8. Optional comparison against verified fast-player telemetry
    
9. Personal progress profiles across sessions
    
10. Community practice drill library
    

---

## 25. Final Scope Lock

## Build first

text

`Monza Turn 1 PS5 UDP telemetry UNO Q logger Brake onset variation Brake reapplication detection RPM limiter dwell Gear consistency Flask dashboard LED matrix via Bridge RPC One drill recommendation Baseline vs follow-up comparison One Edge Impulse anomaly model App Lab deployment evidence`

## Do not build first

text

`Haptics OLED Voice assistant LLM coaching Perfect brake points Perfect gear recommendations External ground truth AI ghost reference More than one track More than one Edge Impulse model`

---

## 26. Definition of Done

PitWall is complete when a beginner can:

1. Connect the UNO Q and PS5 to the same Wi-Fi network.
    
2. Enable F1 25 UDP telemetry.
    
3. Drive a baseline Monza practice stint.
    
4. View a clear post-session coaching drill.
    
5. Complete a focused second stint.
    
6. See a measurable comparison between sessions.
    
7. See a real Edge Impulse anomaly score running locally on the UNO Q.
    
8. See the UNO Q LED matrix respond to live telemetry or coaching state.
    
9. Understand the project in under one minute from the demo video.
    

---

## 27. Final Principle

> Build a useful practice coach, not an impossible omniscient race engineer.

PitWall succeeds if it helps the user make one driving behavior more repeatable, provides evidence of the change, and does so using real F1 25 telemetry, Arduino UNO Q hardware, App Lab, and Edge Impulse.