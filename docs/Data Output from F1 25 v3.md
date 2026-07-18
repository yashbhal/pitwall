6 7 258 

@ 4-7 258 

@ 4=7 25H 



<!-- Start of picture text -->
@ 4=7 25H<br><!-- End of picture text -->



Frequency: 2 per second Size: 753 bytes Version: 1 

|`struct MarshalZone`<br>`{`|
|---|
|<br>`float  m_zoneStart;   // Fraction (0..1) of way through the lap the marshal zone starts`<br>`int8   m_zoneFlag;    // -1 = invalid/unknown, 0 = none, 1 = green, 2 = blue, 3 = yellow`<br>|
|`};`|
|`struct WeatherForecastSample`<br>`{`<br>|
|`uint8     m_sessionType;              // 0 = unknown, see appendix`|
|`uint8     m_timeOffset;               // Time in minutes the forecast is for`<br>|
|`uint8     m_weather;                  // Weather - 0 = clear, 1 = light cloud, 2 = overcast`|
|`// 3 = light rain 4 = heavy rain 5 = storm`|
|`,    ,`<br>`int8      m_trackTemperature;         // Track temp. in degrees Celsius`|
|`int8      m_trackTemperatureChange;   // Track temp. change – 0 = up, 1 = down, 2 = no change`<br>|
|`int8      m_airTemperature;           // Air temp. in degrees celsius`<br>`int8      mairTemperatureChange;     // Air temp change – 0 = up 1 = down 2 = no change`|
|`_       .     ,   ,`<br>`uint8     m_rainPercentage;           // Percentage chance of rain (0-100)`|
|`};`|
|`struct PacketSessionData`<br>`{`|
|`PacketHeader    m_header;`<br>`// Header`|
|`uint8           m_weather;`<br>`// Weather - 0 = clear, 1 = light cloud, 2 = overcast`|
|<br> <br>`// 3 = light rain, 4 = heavy rain, 5 = storm`|
|`int8             mtrackTemperature;`<br>`// Track temp. in degrees celsius`|
|`_`<br> <br>`int8             m_airTemperature;`<br>`// Air temp. in degrees celsius`|
|`uint8           mtotalLaps;`<br>`// Total number of laps in this race`|
|`_`<br> <br>`uint16          m_trackLength;`<br>`// Track length in metres`|
|`uint8           msessionType;`<br>`// 0 = unknown, see appendix`|
|`_`<br> <br>`int8            m_trackId;`<br>`// -1 for unknown, see appendix`|
|`uint8           mformula;                   // Formula, 0 = F1 Modern, 1 = F1 Classic, 2 = F2,`|
|`_`<br>`// 3 = F1 Generic, 4 = Beta, 6 = Esports`<br>`// 8 = F1 World, 9 = F1 Elimination`|
|<br>`uint16          m_sessionTimeLeft;`<br>`// Time left in session in seconds`|
|`uint16          m_sessionDuration;`<br>`// Session duration in seconds`|
|<br>`uint8           m_pitSpeedLimit;`<br>`// Pit speed limit in kilometres per hour`<br>|
|`uint8           m_gamePaused;                // Whether the game is paused – network game only`|
|<br>`uint8           m_isSpectating;`<br>`// Whether the player is spectating`<br> <br>|
|`uint8           m_spectatorCarIndex;`<br>`// Index of the car being spectated`|
|<br>`uint8           m_sliProNativeSupport;`<br>`// SLI Pro support, 0 = inactive, 1 = active`<br>|
|`uint8           m_numMarshalZones;          // Number of marshal zones to follow`|
|`MarshalZone     mmarshalZones[21];          // List of marshal zones – max 21`|
|`_`<br>`uint8           m_safetyCarStatus;           // 0 = no safety car, 1 = full`|
|`// 2 = virtual 3 = formation lap`|
|`,`<br>`uint8           m_networkGame;               // 0 = offline, 1 = online`|
|`uint8           mnumWeatherForecastSamples; // Number of weather samples to follow`|
|`_`<br>`WeatherForecastSample m_weatherForecastSamples[64];   // Array of weather forecast samples`|
|`uint8           m_forecastAccuracy;          // 0 = Perfect, 1 = Approximate`<br>|
|`uint8           m_aiDifficulty;              // AI Difficulty rating – 0-110`|
|`uint32          mseasonLinkIdentifier;      // Identifier for season - persists across saves`|
|`_`<br>`uint32          m_weekendLinkIdentifier;     // Identifier for weekend - persists across saves`|
|`uint32          msessionLinkIdentifier;     // Identifier for session - persists across saves`|
|`_`<br>`uint8           m_pitStopWindowIdealLap;     // Ideal lap to pit on for current strategy (player)`|
|`uint8           mpitStopWindowLatestLap;    // Latest lap to pit on for current strategy (player)`|
|`_`<br>`uint8           m_pitStopRejoinPosition;     // Predicted position to rejoin at (player)`|
|`uint8           m_steeringAssist;            // 0 = off, 1 = on`<br>|
|`uint8           m_brakingAssist;             // 0 = off, 1 = low, 2 = medium, 3 = high`|
|`uint8           mgearboxAssist;             // 1 = manual, 2 = manual & suggested gear, 3 = auto`|
|`_`<br>`uint8           m_pitAssist;                 // 0 = off, 1 = on`|
|`uint8           mpitReleaseAssist;          // 0 = off, 1 = on`|
|`_`<br>`uint8           m_ERSAssist;                 // 0 = off, 1 = on`<br>|
|`uint8           mDRSAssist;                 // 0 = off, 1 = on`|
|`_`<br>`uint8           m_dynamicRacingLine;         // 0 = off, 1 = corners only, 2 = full`|
|`uint8           m_dynamicRacingLineType;     // 0 = 2D, 1 = 3D`<br>`i           d                    d id   di`|
|`unt8           m_gameMoe;                  // Game moe  - see appenx`<br>`uint8           m_ruleSet;                   // Ruleset - see appendix`|





|`uint32`<br>|`m_timeOfDay;`<br>|`// Local time of day - minutes since midnight`<br>|
|---|---|---|
|`uint8`|`m_sessionLength;`|`// 0 = None, 2 = Very Short, 3 = Short, 4 = Medium`<br>`// 5 = Medium Long, 6 = Long, 7 = Full`|
|`uint8`|`m_speedUnitsLeadPlayer;`|`// 0 = MPH, 1 = KPH`|
|`uint8`<br>|`m_temperatureUnitsLeadPlayer;`<br>|`// 0 = Celsius, 1 = Fahrenheit`<br>|
|`uint8`|`m_speedUnitsSecondaryPlayer;`|`// 0 = MPH, 1 = KPH`|
|`uint8`|`m_temperatureUnitsSecondaryPlayer;`|`// 0 = Celsius, 1 = Fahrenheit`|
|`uint8`|`m_numSafetyCarPeriods;`|`// Number of safety cars called during session`|
|`uint8`|`m_numVirtualSafetyCarPeriods;`|`// Number of virtual safety cars called`|
|`uint8`|`m_numRedFlagPeriods;`|`// Number of red flags called during session`|
|`uint8`|`m_equalCarPerformance;`|`// 0 = Off, 1 = On`|
|`uint8`|`m_recoveryMode;`|`// 0 = None, 1 = Flashbacks, 2 = Auto-recovery`|
|`uint8`|`m_flashbackLimit;`|`// 0 = Low, 1 = Medium, 2 = High, 3 = Unlimited`|
|`uint8`|`m_surfaceType;`|`// 0 = Simplified, 1 = Realistic`|
|`uint8`|`m_lowFuelMode;`|`// 0 = Easy, 1 = Hard`|
|`uint8`|`m_raceStarts;`|`// 0 = Manual, 1 = Assisted`|
|`uint8`|`m_tyreTemperature;`|`// 0 = Surface only, 1 = Surface & Carcass`|
|`uint8`|`m_pitLaneTyreSim;`|`// 0 = On, 1 = Off`|
|`uint8`|`m_carDamage;`|`// 0 = Off, 1 = Reduced, 2 = Standard, 3 = Simulation`|
|`uint8`|`m_carDamageRate;`|`// 0 = Reduced, 1 = Standard, 2 = Simulation`|
|`uint8`|`m_collisions;`|`// 0 = Off, 1 = Player-to-Player Off, 2 = On`|
|`uint8`|`m_collisionsOffForFirstLapOnly;`|`// 0 = Disabled, 1 = Enabled`|
|`uint8`|`m_mpUnsafePitRelease;`|`// 0 = On, 1 = Off (Multiplayer)`|
|`uint8`|`m_mpOffForGriefing;`|`// 0 = Disabled, 1 = Enabled (Multiplayer)`|
|`uint8`|`m_cornerCuttingStringency;`|`// 0 = Regular, 1 = Strict`|
|`uint8`|`m_parcFermeRules;`|`// 0 = Off, 1 = On`|
|`uint8`|`m_pitStopExperience;`|`// 0 = Automatic, 1 = Broadcast, 2 = Immersive`|
|`uint8`|`m_safetyCar;`|`// 0 = Off, 1 = Reduced, 2 = Standard, 3 = Increased`|
|`uint8`|`m_safetyCarExperience;`|`// 0 = Broadcast, 1 = Immersive`|
|`uint8`|`m_formationLap;`|`// 0 = Off, 1 = On`|
|`uint8`|`m_formationLapExperience;`|`// 0 = Broadcast, 1 = Immersive`|
|`uint8`|`m_redFlags;`|`// 0 = Off, 1 = Reduced, 2 = Standard, 3 = Increased`|
|`uint8`|`m_affectsLicenceLevelSolo;`|`// 0 = Off, 1 = On`|
|`uint8`|`m_affectsLicenceLevelMP;`|`// 0 = Off, 1 = On`|
|`uint8`|`m_numSessionsInWeekend;`|`// Number of session in following array`|
|`uint8`|`m_weekendStructure[12];`|`// List of session types to show weekend`<br>`// structure - see appendix for types`|
|`float`|`m_sector2LapDistanceStart;`|`// Distance in m around track where sector 2 starts`|
|`float`<br>`};`|`m_sector3LapDistanceStart;`|`// Distance in m around track where sector 3 starts`|



### **Lap Data Packet** 

The lap data packet gives details of all the cars in the session. 

Frequency: Rate as specified in menus Size: 1285 bytes Version: 1 

|`struct LapD`<br>|`ata`||
|---|---|---|
|`{`<br>`uint32`|`m_lastLapTimeInMS;`|`// Last lap time in milliseconds`|
|`uint32`|`m_currentLapTimeInMS;`|`// Current time around the lap in milliseconds`|
|`uint16`|`m_sector1TimeMSPart;`|`// Sector 1 time milliseconds part`|
|`uint8`|`m_sector1TimeMinutesPart;`|`// Sector 1 whole minute part`|
|`uint16`<br>`uint8`|`m_sector2TimeMSPart;`<br>`m_sector2TimeMinutesPart;`|`// Sector 2 time milliseconds part`<br>`// Sector 2 whole minute part`|
|`uint16`<br>`uint8`<br>`uint16`|`m_deltaToCarInFrontMSPart;`<br>`m_deltaToCarInFrontMinutesP`<br>`m_deltaToRaceLeaderMSPart;`|`// Time delta to car in front milliseconds part`<br>`art; // Time delta to car in front whole minute part`<br>`// Time delta to race leader milliseconds part`|
|`uint8`<br>`float`|`m_deltaToRaceLeaderMinutesP`<br>`m_lapDistance;`|`art; // Time delta to race leader whole minute part`<br>`// Distance vehicle is around current lap in metres – could`<br>`// be negative if line hasn’t been crossed yet`|
|`float`|`m_totalDistance;`|`// Total distance travelled in session in metres – could`<br>`// be negative if line hasn’t been crossed yet`|
|`float`|`m_safetyCarDelta;`|`// Delta in seconds for safety car`|
|`uint8`|`m_carPosition;`<br>|`// Car race position`|





```
    uint8    m_currentLapNum;  // Current lap number
    uint8    m_pitStatus;              // 0 = none, 1 = pitting, 2 = in pit area
    uint8    m_numPitStops;              // Number of pit stops taken in this race
    uint8    m_sector;                 // 0 = sector1, 1 = sector2, 2 = sector3
    uint8    m_currentLapInvalid;      // Current lap invalid - 0 = valid, 1 = invalid
    uint8    m_penalties;              // Accumulated time penalties in seconds to be added
    uint8    m_totalWarnings;             // Accumulated number of warnings issued
    uint8    m_cornerCuttingWarnings;     // Accumulated number of corner cutting warnings issued
    uint8    m_numUnservedDriveThroughPens;  // Num drive through pens left to serve
    uint8    m_numUnservedStopGoPens;        // Num stop go pens left to serve
    uint8    m_gridPosition;           // Grid position the vehicle started the race in
    uint8    m_driverStatus;           // Status of driver - 0 = in garage, 1 = flying lap
                                          // 2 = in lap, 3 = out lap, 4 = on track
    uint8    m_resultStatus;              // Result status - 0 = invalid, 1 = inactive, 2 = active
                                          // 3 = finished, 4 = didnotfinish, 5 = disqualified
                                          // 6 = not classified, 7 = retired
    uint8    m_pitLaneTimerActive;       // Pit lane timing, 0 = inactive, 1 = active
    uint16   m_pitLaneTimeInLaneInMS;     // If active, the current time spent in the pit lane in ms
    uint16   m_pitStopTimerInMS;          // Time of the actual pit stop in ms
    uint8    m_pitStopShouldServePen;     // Whether the car should serve a penalty at this stop
    float    m_speedTrapFastestSpeed;     // Fastest speed through speed trap for this car in kmph
    uint8    m_speedTrapFastestLap;       // Lap no the fastest speed was achieved, 255 = not set
};
struct PacketLapData
{
    PacketHeader    m_header;              // Header
    LapData         m_lapData[22];         // Lap data for all cars on track
    uint8 m_timeTrialPBCarIdx;  // Index of Personal Best car in time trial (255 if invalid)
    uint8 m_timeTrialRivalCarIdx;  // Index of Rival car in time trial (255 if invalid)
};
```

### **Event Packet** 

This packet gives details of events that happen during the course of a session. 

Frequency: When the event occurs Size: 45 bytes Version: 1 

```
// The event details packet is different for each type of event.
// Make sure only the correct type is interpreted.
union EventDataDetails
{
    struct
    {
        uint8 vehicleIdx; // Vehicle index of car achieving fastest lap
        float lapTime;    // Lap time is in seconds
    } FastestLap;
    struct
    {
        uint8   vehicleIdx; // Vehicle index of car retiring
        uint8   reason;     // Reason - 0 = invalid, 1 = retired, 2 = finished
                    // 3 = terminal damage, 4 = inactive, 5 = not enough laps completed
                    // 6 = black flagged, 7 = red flagged, 8 = mechanical failure
                            // 9 = session skipped, 10 = session simulated
    } Retirement;
    struct
    {
        uint8   reason;     // 0 = Wet track, 1 = Safety car deployed, 2 = Red flag
                            // 3 = Min lap not reached
```



```
    } DRSDisabled;
```

```
    struct
    {
```

```
        uint8   vehicleIdx; // Vehicle index of team mate
    } TeamMateInPits;
```

```
    struct
    {
```

```
        uint8   vehicleIdx; // Vehicle index of the race winner
    } RaceWinner;
```

```
    struct
    {
uint8 penaltyType; // Penalty type – see Appendices
        uint8 infringementType;  // Infringement type – see Appendices
        uint8 vehicleIdx;          // Vehicle index of the car the penalty is applied to
        uint8 otherVehicleIdx;     // Vehicle index of the other car involved
        uint8 time;                // Time gained, or time spent doing action in seconds
        uint8 lapNum;              // Lap the penalty occurred on
        uint8 placesGained;        // Number of places gained by this
    } Penalty;
    struct
    {
        uint8 vehicleIdx; // Vehicle index of the vehicle triggering speed trap
        float speed;       // Top speed achieved in kilometres per hour
        uint8 isOverallFastestInSession; // Overall fastest speed in session = 1, otherwise 0
        uint8 isDriverFastestInSession;  // Fastest speed for driver in session = 1, otherwise 0
        uint8 fastestVehicleIdxInSession;// Vehicle index of the vehicle that is the fastest
// in this session
        float fastestSpeedInSession;      // Speed of the vehicle that is the fastest
 // in this session
    } SpeedTrap;
    struct
    {
        uint8 numLights;  // Number of lights showing
    } StartLIghts;
    struct
    {
        uint8 vehicleIdx;                 // Vehicle index of the vehicle serving drive through
    } DriveThroughPenaltyServed;
    struct
    {
        uint8 vehicleIdx;                 // Vehicle index of the vehicle serving stop go
float stopTime;                   // Time spent serving stop go in seconds
    } StopGoPenaltyServed;
    struct
    {
        uint32 flashbackFrameIdentifier;  // Frame identifier flashed back to
        float flashbackSessionTime;       // Session time flashed back to
    } Flashback;
    struct
    {
        uint32 buttonStatus;              // Bit flags specifying which buttons are being pressed
                                          // currently - see appendices
    } Buttons;
    struct
    {
        uint8 overtakingVehicleIdx;       // Vehicle index of the vehicle overtaking
        uint8 beingOvertakenVehicleIdx;   // Vehicle index of the vehicle being overtaken
    } Overtake;
    struct
    {
        uint8 safetyCarType;              // 0 = No Safety Car, 1 = Full Safety Car
                                          // 2 = Virtual Safety Car, 3 = Formation Lap Safety Car
        uint8 eventType;                  // 0 = Deployed, 1 = Returning, 2 = Returned
```

6-725 



<!-- Start of picture text -->
es<br>se<br>es<br>es<br>es<br>es<br>es<br>es<br>es<br>en<br>Rs<br>Rs<br>Ge<br>se<br>sf<br>sf<br>sf<br>sf<br>sf<br>sf<br>sf<br>se<br><!-- End of picture text -->



Size: 1284 bytes Version: 1 

```
// RGB value of a colour
struct LiveryColour
{
    uint8       red;
    uint8       green;
    uint8       blue;
};
struct ParticipantData
{
    uint8      m_aiControlled;      // Whether the vehicle is AI (1) or Human (0) controlled
    uint8      m_driverId;    // Driver id - see appendix, 255 if network human
    uint8      m_networkId;    // Network id – unique identifier for network players
    uint8      m_teamId;            // Team id - see appendix
    uint8      m_myTeam;            // My team flag – 1 = My Team, 0 = otherwise
    uint8      m_raceNumber;        // Race number of the car
    uint8      m_nationality;       // Nationality of the driver
    char       m_name[32];          // Name of participant in UTF-8 format – null terminated
   // Will be truncated with … (U+2026) if too long
    uint8      m_yourTelemetry;     // The player's UDP setting, 0 = restricted, 1 = public
    uint8      m_showOnlineNames;   // The player's show online names setting, 0 = off, 1 = on
    uint16     m_techLevel;         // F1 World tech level
    uint8      m_platform;          // 1 = Steam, 3 = PlayStation, 4 = Xbox, 6 = Origin, 255 = unknown
    uint8      m_numColours;        // Number of colours valid for this car
    LiveryColour m_liveryColours[4]; // Colours for the car
```

```
struct PacketParticipantsData
{
    PacketHeader    m_header;            // Header
    uint8           m_numActiveCars; // Number of active cars in the data – should match number of
                                         // cars on HUD
    ParticipantData m_participants[22];
};
```

### **Car Setups Packet** 

This packet details the car setups for each vehicle in the session. Note that in multiplayer games, other player cars will appear as blank, you will only be able to see your own car setup, regardless of the “Your Telemetry” setting. Spectators will also not be able to see any car setups. 

Frequency: 2 per second Size: 1133 bytes Version: 1 `struct CarSetupData { uint8     m_frontWing;                // Front wing aero uint8     m_rearWing;                 // Rear wing aero uint8     m_onThrottle;               // Differential adjustment on throttle (percentage) uint8     m_offThrottle;              // Differential adjustment off throttle (percentage) float     m_frontCamber;              // Front camber angle (suspension geometry) float     m_rearCamber;               // Rear camber angle (suspension geometry) float     m_frontToe;                 // Front toe angle (suspension geometry) float     m_rearToe;                  // Rear toe angle (suspension geometry) uint8     m_frontSuspension;          // Front suspension uint8     m_rearSuspension;           // Rear suspension uint8     m_frontAntiRollBar;         // Front anti-roll bar uint8     m_rearAntiRollBar;          // Front anti-roll bar uint8     m_frontSuspensionHeight;    // Front ride height uint8     m_rearSuspensionHeight;     // Rear ride height uint8     m_brakePressure;            // Brake pressure (percentage) uint8     m_brakeBias;                // Brake bias (percentage)` 



```
uint8     m_engineBraking;            // Engine braking (percentage)
    float     m_rearLeftTyrePressure;     // Rear left tyre pressure (PSI)
    float     m_rearRightTyrePressure;    // Rear right tyre pressure (PSI)
    float     m_frontLeftTyrePressure;    // Front left tyre pressure (PSI)
    float     m_frontRightTyrePressure;   // Front right tyre pressure (PSI)
    uint8     m_ballast;                  // Ballast
    float     m_fuelLoad;                 // Fuel load
};
struct PacketCarSetupData
{
    PacketHeader    m_header;            // Header
```

```
    CarSetupData    m_carSetups[22];
```

```
    float         m_nextFrontWingValue; // Value of front wing after next pit stop - player only
};
```

### **Car Telemetry Packet** 

This packet details telemetry for all the cars in the race. It details various values that would be recorded on the car such as speed, throttle application, DRS etc. Note that the rev light configurations are presented separately as well and will mimic real life driver preferences. 

Frequency: Rate as specified in menus Size: 1352 bytes Version: 1 

```
struct CarTelemetryData
{
```

```
    uint16    m_speed;                    // Speed of car in kilometres per hour
    float     m_throttle;                 // Amount of throttle applied (0.0 to 1.0)
    float     m_steer;                    // Steering (-1.0 (full lock left) to 1.0 (full lock right))
    float     m_brake;                    // Amount of brake applied (0.0 to 1.0)
    uint8     m_clutch;                   // Amount of clutch applied (0 to 100)
    int8      m_gear;                     // Gear selected (1-8, N=0, R=-1)
    uint16    m_engineRPM;                // Engine RPM
    uint8     m_drs;                      // 0 = off, 1 = on
    uint8     m_revLightsPercent;         // Rev lights indicator (percentage)
    uint16    m_revLightsBitValue;        // Rev lights (bit 0 = leftmost LED, bit 14 = rightmost LED)
    uint16    m_brakesTemperature[4];     // Brakes temperature (celsius)
    uint8     m_tyresSurfaceTemperature[4]; // Tyres surface temperature (celsius)
    uint8     m_tyresInnerTemperature[4]; // Tyres inner temperature (celsius)
    uint16    m_engineTemperature;        // Engine temperature (celsius)
    float     m_tyresPressure[4];         // Tyres pressure (PSI)
    uint8     m_surfaceType[4];           // Driving surface, see appendices
};
struct PacketCarTelemetryData
{
    PacketHeader     m_header;       // Header
    CarTelemetryData    m_carTelemetryData[22];
    uint8               m_mfdPanelIndex;       // Index of MFD panel open - 255 = MFD closed
                                               // Single player, race – 0 = Car setup, 1 = Pits
                                               // 2 = Damage, 3 =  Engine, 4 = Temperatures
                                               // May vary depending on game mode
    uint8               m_mfdPanelIndexSecondaryPlayer;   // See above
    int8                m_suggestedGear;       // Suggested gear for the player (1-8)
                                               // 0 if no gear suggested
};
```



### **Car Status Packet** 

This packet details car statuses for all the cars in the race. 

Frequency: Rate as specified in menus Size: 1239 bytes Version: 1 

```
struct CarStatusData
{
    uint8       m_tractionControl;          // Traction control - 0 = off, 1 = medium, 2 = full
    uint8       m_antiLockBrakes;           // 0 (off) - 1 (on)
    uint8       m_fuelMix;                  // Fuel mix - 0 = lean, 1 = standard, 2 = rich, 3 = max
    uint8       m_frontBrakeBias;           // Front brake bias (percentage)
    uint8       m_pitLimiterStatus;         // Pit limiter status - 0 = off, 1 = on
    float       m_fuelInTank;               // Current fuel mass
    float       m_fuelCapacity;             // Fuel capacity
    float       m_fuelRemainingLaps;        // Fuel remaining in terms of laps (value on MFD)
    uint16      m_maxRPM;                   // Cars max RPM, point of rev limiter
    uint16      m_idleRPM;                  // Cars idle RPM
    uint8       m_maxGears;                 // Maximum number of gears
    uint8       m_drsAllowed;               // 0 = not allowed, 1 = allowed
    uint16      m_drsActivationDistance;    // 0 = DRS not available, non-zero - DRS will be available
                                            // in [X] metres
    uint8       m_actualTyreCompound;    // F1 Modern - 16 = C5, 17 = C4, 18 = C3, 19 = C2, 20 = C1
   // 21 = C0, 22 = C6, 7 = inter, 8 = wet
   // F1 Classic - 9 = dry, 10 = wet
   // F2 – 11 = super soft, 12 = soft, 13 = medium, 14 = hard
   // 15 = wet
    uint8       m_visualTyreCompound;       // F1 visual (can be different from actual compound)
                                            // 16 = soft, 17 = medium, 18 = hard, 7 = inter, 8 = wet
                                            // F1 Classic – same as above
                                            // F2 ‘20, 15 = wet, 19 – super soft, 20 = soft
                                            // 21 = medium, 22 = hard
    uint8       m_tyresAgeLaps;             // Age in laps of the current set of tyres
    int8        m_vehicleFiaFlags;    // -1 = invalid/unknown, 0 = none, 1 = green
                                            // 2 = blue, 3 = yellow
    float       m_enginePowerICE;           // Engine power output of ICE (W)
    float       m_enginePowerMGUK;          // Engine power output of MGU-K (W)
    float       m_ersStoreEnergy;           // ERS energy store in Joules
    uint8       m_ersDeployMode;            // ERS deployment mode, 0 = none, 1 = medium
   // 2 = hotlap, 3 = overtake
    float       m_ersHarvestedThisLapMGUK;  // ERS energy harvested this lap by MGU-K
    float       m_ersHarvestedThisLapMGUH;  // ERS energy harvested this lap by MGU-H
    float       m_ersDeployedThisLap;       // ERS energy deployed this lap
    uint8       m_networkPaused;            // Whether the car is paused in a network game
};
struct PacketCarStatusData
{
    PacketHeader     m_header;    // Header
    CarStatusData m_carStatusData[22];
};
```

### **Final Classification Packet** 

This packet details the final classification at the end of the race, and the data will match with the post race results screen. This is especially useful for multiplayer games where it is not always possible to send lap times on the final frame because of network delay. 

Frequency: Once at the end of a race Size: 1042 bytes 



##### Version: 1 

```
struct FinalClassificationData
{
    uint8     m_position;          // Finishing position
    uint8     m_numLaps;           // Number of laps completed
    uint8     m_gridPosition;      // Grid position of the car
    uint8     m_points;            // Number of points scored
    uint8     m_numPitStops;       // Number of pit stops made
    uint8     m_resultStatus;      // Result status - 0 = invalid, 1 = inactive, 2 = active
                                   // 3 = finished, 4 = didnotfinish, 5 = disqualified
                                   // 6 = not classified, 7 = retired
    uint8     m_resultReason;      // Result reason - 0 = invalid, 1 = retired, 2 = finished
                                   // 3 = terminal damage, 4 = inactive, 5 = not enough laps completed
                                   // 6 = black flagged, 7 = red flagged, 8 = mechanical failure
                                   // 9 = session skipped, 10 = session simulated
    uint32    m_bestLapTimeInMS;       // Best lap time of the session in milliseconds
    double    m_totalRaceTime;         // Total race time in seconds without penalties
    uint8     m_penaltiesTime;         // Total penalties accumulated in seconds
    uint8     m_numPenalties;          // Number of penalties applied to this driver
    uint8     m_numTyreStints;         // Number of tyres stints up to maximum
    uint8     m_tyreStintsActual[8];   // Actual tyres used by this driver
    uint8     m_tyreStintsVisual[8];   // Visual tyres used by this driver
    uint8     m_tyreStintsEndLaps[8];  // The lap number stints end on
};
struct PacketFinalClassificationData
{
    PacketHeader    m_header;                      // Header
    uint8                      m_numCars;          // Number of cars in the final classification
    FinalClassificationData    m_classificationData[22];
};
```

### **Lobby Info Packet** 

This packet details the players currently in a multiplayer lobby. It details each player’s selected car, any AI involved in the game and also the ready status of each of the participants. 

Frequency: Two every second when in the lobby Size: 954 bytes Version: 1 

```
struct LobbyInfoData
{
    uint8     m_aiControlled;      // Whether the vehicle is AI (1) or Human (0) controlled
    uint8     m_teamId;            // Team id - see appendix (255 if no team currently selected)
    uint8     m_nationality;       // Nationality of the driver
    uint8     m_platform;          // 1 = Steam, 3 = PlayStation, 4 = Xbox, 6 = Origin, 255 = unknown
    char      m_name[32];   // Name of participant in UTF-8 format – null terminated
                                   // Will be truncated with ... (U+2026) if too long
    uint8     m_carNumber;         // Car number of the player
uint8     m_yourTelemetry;     // The player's UDP setting, 0 = restricted, 1 = public
    uint8     m_showOnlineNames;   // The player's show online names setting, 0 = off, 1 = on
    uint16    m_techLevel;         // F1 World tech level
    uint8     m_readyStatus;       // 0 = not ready, 1 = ready, 2 = spectating
};
struct PacketLobbyInfoData
{
    PacketHeader    m_header;                       // Header
    // Packet specific data
    uint8               m_numPlayers;               // Number of players in the lobby data
    LobbyInfoData       m_lobbyPlayers[22];
};
```



### **Car Damage Packet** 

This packet details car damage parameters for all the cars in the race. 

Frequency: 10 per second Size: 1041 bytes Version: 1 

```
struct CarDamageData
{
    float     m_tyresWear[4];                     // Tyre wear (percentage)
    uint8     m_tyresDamage[4];                   // Tyre damage (percentage)
    uint8     m_brakesDamage[4];                  // Brakes damage (percentage)
    uint8     m_tyreBlisters[4];                  // Tyre blisters value (percentage)
    uint8     m_frontLeftWingDamage;              // Front left wing damage (percentage)
    uint8     m_frontRightWingDamage;             // Front right wing damage (percentage)
    uint8     m_rearWingDamage;                   // Rear wing damage (percentage)
    uint8     m_floorDamage;                      // Floor damage (percentage)
    uint8     m_diffuserDamage;                   // Diffuser damage (percentage)
    uint8     m_sidepodDamage;                    // Sidepod damage (percentage)
    uint8     m_drsFault;                         // Indicator for DRS fault, 0 = OK, 1 = fault
    uint8     m_ersFault;                         // Indicator for ERS fault, 0 = OK, 1 = fault
    uint8     m_gearBoxDamage;                    // Gear box damage (percentage)
    uint8     m_engineDamage;                     // Engine damage (percentage)
    uint8     m_engineMGUHWear;                   // Engine wear MGU-H (percentage)
    uint8     m_engineESWear;                     // Engine wear ES (percentage)
    uint8     m_engineCEWear;                     // Engine wear CE (percentage)
    uint8     m_engineICEWear;                    // Engine wear ICE (percentage)
    uint8     m_engineMGUKWear;                   // Engine wear MGU-K (percentage)
    uint8     m_engineTCWear;                     // Engine wear TC (percentage)
    uint8     m_engineBlown;                      // Engine blown, 0 = OK, 1 = fault
    uint8     m_engineSeized;                     // Engine seized, 0 = OK, 1 = fault
}
struct PacketCarDamageData
{
    PacketHeader    m_header;               // Header
    CarDamageData   m_carDamageData[22];
};
```

### **Session History Packet** 

This packet contains lap times and tyre usage for the session. **This packet works slightly differently to other packets. To reduce CPU and bandwidth, each packet relates to a specific vehicle and is sent every 1/20 s, and the vehicle being sent is cycled through. Therefore in a 20 car race you should receive an update for each vehicle at least once per second.** 

Note that at the end of the race, after the final classification packet has been sent, a final bulk update of all the session histories for the vehicles in that session will be sent. 

Frequency: 20 per second but cycling through cars Size: 1460 bytes Version: 1 

```
struct LapHistoryData
{
    uint32    m_lapTimeInMS;           // Lap time in milliseconds
    uint16    m_sector1TimeMSPart;        // Sector 1 milliseconds part
```



```
    uint8     m_sector1TimeMinutesPart;   // Sector 1 whole minute part
    uint16    m_sector2TimeMSPart;        // Sector 2 time milliseconds part
    uint8     m_sector2TimeMinutesPart;   // Sector 2 whole minute part
    uint16    m_sector3TimeMSPart;        // Sector 3 time milliseconds part
    uint8     m_sector3TimeMinutesPart;   // Sector 3 whole minute part
    uint8     m_lapValidBitFlags;      // 0x01 bit set-lap valid,      0x02 bit set-sector 1 valid
                                       // 0x04 bit set-sector 2 valid, 0x08 bit set-sector 3 valid
};
struct TyreStintHistoryData
{
    uint8     m_endLap;                // Lap the tyre usage ends on (255 of current tyre)
    uint8     m_tyreActualCompound;    // Actual tyres used by this driver
    uint8     m_tyreVisualCompound;    // Visual tyres used by this driver
};
struct PacketSessionHistoryData
{
    PacketHeader  m_header;                   // Header
    uint8         m_carIdx;                   // Index of the car this lap data relates to
    uint8         m_numLaps;                  // Num laps in the data (including current partial lap)
    uint8         m_numTyreStints;            // Number of tyre stints in the data
    uint8         m_bestLapTimeLapNum;        // Lap the best lap time was achieved on
    uint8         m_bestSector1LapNum;        // Lap the best Sector 1 time was achieved on
    uint8         m_bestSector2LapNum;        // Lap the best Sector 2 time was achieved on
    uint8         m_bestSector3LapNum;        // Lap the best Sector 3 time was achieved on
    LapHistoryData          m_lapHistoryData[100]; // 100 laps of data max
    TyreStintHistoryData    m_tyreStintsHistoryData[8];
};
```

### **Tyre Sets Packet** 

This packets gives a more in-depth details about tyre sets assigned to a vehicle during the session. 

Frequency: 20 per second but cycling through cars Size: 231 bytes Version: 1 

```
struct TyreSetData
{
    uint8     m_actualTyreCompound;    // Actual tyre compound used
    uint8     m_visualTyreCompound;    // Visual tyre compound used
    uint8     m_wear;                  // Tyre wear (percentage)
    uint8     m_available;             // Whether this set is currently available
    uint8     m_recommendedSession;    // Recommended session for tyre set, see appendix
    uint8     m_lifeSpan;              // Laps left in this tyre set
    uint8     m_usableLife;            // Max number of laps recommended for this compound
    int16     m_lapDeltaTime;          // Lap delta time in milliseconds compared to fitted set
    uint8     m_fitted;                // Whether the set is fitted or not
};
struct PacketTyreSetsData
{
    PacketHeader    m_header;            // Header
    uint8           m_carIdx;            // Index of the car this data relates to
    TyreSetData     m_tyreSetData[20]; // 13 (dry) + 7 (wet)
    uint8           m_fittedIdx;         // Index into array of fitted tyre
};
```



### **Motion Ex Packet** 

The motion packet gives extended data for the car being driven with the goal of being able to drive a motion platform setup. 

Frequency: Rate as specified in menus Size: 273 bytes Version: 1 

|`struct PacketMoti`<br>`{`<br>|`onExData`<br>||
|---|---|---|
|`PacketHeader`|`m_header;`|`// Header`|
|`// Extra play`<br>|`er car ONLY data`<br>||
|`float`|`m_suspensionPosition[4];`|`// Note: All wheel arrays have the following order:`|
|`float`|`m_suspensionVelocity[4];`|`// RL, RR, FL, FR`|
|`float`|`m_suspensionAcceleration[4];`|`// RL, RR, FL, FR`|
|`float`|`m_wheelSpeed[4];`|`// Speed of each wheel`|
|`float`|`m_wheelSlipRatio[4];`|`// Slip ratio for each wheel`|
|`float`|`m_wheelSlipAngle[4];`|`// Slip angles for each wheel`|
|`float`|`m_wheelLatForce[4];`|`// Lateral forces for each wheel`|
|`float`|`m_wheelLongForce[4];`|`// Longitudinal forces for each wheel`|
|`float`|`m_heightOfCOGAboveGround;`|`// Height of centre of gravity above ground`|
|`float`<br>|`m_localVelocityX;`<br>|`// Velocity in local space – metres/s`<br>|
|`float`|`m_localVelocityY;`|`// Velocity in local space`|
|`float`|`m_localVelocityZ;`|`// Velocity in local space`|
|`float`|`m_angularVelocityX;`|`// Angular velocity x-component – radians/s`|
|`float`|`m_angularVelocityY;`|`// Angular velocity y-component`|
|`float`|`m_angularVelocityZ;`|`// Angular velocity z-component`|
|`float`|`m_angularAccelerationX;`|`// Angular acceleration x-component – radians/s/s`|
|`float`|`m_angularAccelerationY;`|`// Angular acceleration y-component`|
|`float`|`m_angularAccelerationZ;`|`// Angular acceleration z-component`|
|`float`|`m_frontWheelsAngle;`|`// Current front wheels angle in radians`|
|`float`|`m_wheelVertForce[4];`|`// Vertical forces for each wheel`|
|`float`|`m_frontAeroHeight;`|`// Front plank edge height above road surface`|
|`float`|`m_rearAeroHeight;`|`// Rear plank edge height above road surface`|
|`float`|`m_frontRollAngle;`|`// Roll angle of the front suspension`|
|`float`|`m_rearRollAngle;`|`// Roll angle of the rear suspension`|
|`float`|`m_chassisYaw;`|`// Yaw angle of the chassis relative to the direction`<br>`// of motion - radians`|
|`float`|`m_chassisPitch;`|`// Pitch angle of the chassis relative to the`<br>`// direction of motion – radians`|
|`float`|`m_wheelCamber[4];`|`// Camber of each wheel in radians`|
|`float`|`m_wheelCamberGain[4];`|`// Camber gain for each wheel in radians, difference`|
|||`// between active camber and dynamic camber`|



```
};
```

### **Time Trial Packet** 

The time trial data gives extra information only relevant to time trial game mode. This packet will not be sent in other game modes. 

Frequency: 1 per second Size: 101 bytes Version: 1 

```
struct TimeTrialDataSet
{
    uint8     m_carIdx;                   // Index of the car this data relates to
    uint8     m_teamId;                   // Team id - see appendix
    uint32    m_lapTimeInMS;              // Lap time in milliseconds
    uint32    m_sector1TimeInMS;          // Sector 1 time in milliseconds
    uint32    m_sector2TimeInMS;          // Sector 2 time in milliseconds
```



```
    uint32    m_sector3TimeInMS;          // Sector 3 time in milliseconds
    uint8     m_tractionControl;          // 0 = assist off, 1 = assist on
    uint8     m_gearboxAssist;            // 0 = assist off, 1 = assist on
    uint8     m_antiLockBrakes;           // 0 = assist off, 1 = assist on
    uint8     m_equalCarPerformance;      // 0 = Realistic, 1 = Equal
    uint8     m_customSetup;              // 0 = No, 1 = Yes
    uint8     m_valid;                    // 0 = invalid, 1 = valid
};
struct PacketTimeTrialData
{
    PacketHeader    m_header;                // Header
    TimeTrialDataSet    m_playerSessionBestDataSet;     // Player session best data set
    TimeTrialDataSet    m_personalBestDataSet;          // Personal best data set
    TimeTrialDataSet    m_rivalDataSet;                 // Rival data set
};
```

### **Lap Positions Packet** 

The lap positions data indicates which position each car was on at the start of each lap. Using this information a lap positions chart can be constructed. Note that only a maximum of 50 laps will be transmitted in a packet. If more than 50 laps have occurred then two packets will be transmitted, with different m_lapStart parameters. The whole lap position history can be recreated merging both of these. 

Frequency: 1 per second Size: 1131 bytes Version: 1 

```
struct PacketLapPositionsData
{
    PacketHeader    m_header;                   // Header
    // Packet specific data
    uint8           m_numLaps;                  // Number of laps in the data
    uint8           m_lapStart;                 // Index of the lap where the data starts, 0 indexed
```

```
    // Array holding the position of the car in a given lap, 0 if no record
    uint8           m_positionForVehicleIdx[50][cs_maxNumCarsInUDPData];
};
```



### **Restricted data (Your Telemetry setting)** 

There is some data in the UDP that you may not want other players seeing if you are in a multiplayer game. This is controlled by the “Your Telemetry” setting in the Telemetry options. The options are: 

- Restricted (Default) – other players viewing the UDP data will not see values for your car 

- Public – all other players can see all the data for your car 

Note: You can always see the data for the car you are driving regardless of the setting. 

The following data items are set to zero if the player driving the car in question has their “Your Telemetry” set to “Restricted”: 

#### **_Car status packet_** 

- m_fuelInTank 

- m_fuelCapacity 

- m_fuelMix 

- m_fuelRemainingLaps 

- m_frontBrakeBias 

- m_ersDeployMode 

- m_ersStoreEnergy 

- m_ersDeployedThisLap 

- m_ersHarvestedThisLapMGUK 

- m_ersHarvestedThisLapMGUH 

- m_enginePowerICE 

- m_enginePowerMGUK 

#### **_Car damage packet_** 

- m_frontLeftWingDamage 

- m_frontRightWingDamage 

- m_rearWingDamage 

- m_floorDamage 

- m_diffuserDamage 

- m_sidepodDamage 

- m_engineDamage 

- m_gearBoxDamage 

- m_tyresWear (All four wheels) 

- m_tyresDamage (All four wheels) 

- m_brakesDamage (All four wheels) 

- • m_drsFault 

- m_engineMGUHWear 

- m_engineESWear 

- m_engineCEWear 

- m_engineICEWear 

- m_engineMGUKWear 



- m_engineTCWear 

#### **_Tyre set packet_** 

- All data within this packet for player car 

To allow other players to view your online ID in their UDP output during an online session, you must enable the “Show online ID / gamertags” option. Selecting this will bring up a confirmation box that must be confirmed before this option is enabled. 

Please note that all options can be changed during a game session and will take immediate effect. 

## **<u>FAQS</u>** 

### **How do I enable the UDP Telemetry Output?** 

In F1 25, UDP telemetry output is controlled via the in-game menus. To enable this, enter the options menu from the main menu (triangle / Y), then enter the settings menu - the UDP option will be at the bottom of the list. From there you will be able to enable / disable the UDP output, configure the IP address and port for the receiving application, toggle broadcast mode and set the send rate. Broadcast mode transmits the data across the network subnet to allow multiple devices on the same subnet to be able to receive this information. When using broadcast mode it is not necessary to set a target IP address, just a target port for applications to listen on. 

_Advanced PC Users_ : You can additionally edit the game’s configuration XML file to configure UDP output. The file is located here (after an initial boot of the game): 

```
...\Documents\My Games\<game_folder>\hardwaresettings\hardware_settings_config.xml
```

You should see the tag: 

```
<motion>
  ...
  <udp enabled="false" broadcast=”false” ip="127.0.0.1" port="20777" sendRate=”20”
format=”2025” yourTelemetry=”restricted” onlineNames="off" />
```

```
  ...
</motion>
```

Here you can set the values manually. Note that any changes made within the game when it is running will overwrite any changes made manually. Note the enabled flag is now a state. 

### **What has changed since last year?** 

F1® 25 sees the following changes to the UDP specification: 

- Added stop-go penalty time to the event packet 

- Tyre blister percentage has been added to the car damage packet 

- Chassis pitch has been added to the Motion Ex packet 

- Added car colours to the participants packet ( **and reduced name size to 32 chars, 48 chars seemed excessive** ) 

- Reduced name size in lobby packet as per above 

- Add wheel camber and wheel camber gain to Motion Ex packet 



- Added more detailed reason for DRS being disabled 

- Added retirement reason to the Retirement event 

- Added a new Lap Positions packet 

- Added result reason to the Final Classifications packet 

- Added C6 compound tyre to documentation 

### **What is the order of the wheel arrays?** 

All wheel arrays are in the following order: 

```
   0 – Rear Left (RL)
```

```
   1 – Rear Right (RR)
```

```
   2 – Front Left (FL)
   3 – Front Right (FR)
```

### **Do the vehicle indices change?** 

During a session, each car is assigned a vehicle index. This will not change throughout the session and all the arrays that are sent use this vehicle index to dereference the correct piece of data. 

### **What are the co-ordinate systems used?** 

Here is a visual representation of the co-ordinate system used with the F1 telemetry data. 





### **What encoding format is used?** 

All values are encoded using Little Endian format. 

### **Are the data structures packed?** 

Yes, all data is packed, there is no padding used. 

### **How many cars are in the data structures?** 



The maximum number of cars in the data structures is 22, to allow for certain game modes, although the data is not always filled in. 

You should always check the data item called `m_numActiveCars` in the participants packet which tells you how many cars are active in the race. However, you should check the individual result status of each car in the lap data to see if that car is actively providing data. If it is not “ `Invalid` ” or “ `Inactive` ” then the corresponding vehicle index has valid data. 

### **How often are updated packets sent?** 

For the packets which get updated at “Rate as specified in the menus” you can be guaranteed that on the frame that these get sent they will all get sent together and will never be separated across frames. This of course relies on the reliability of your network as to whether they are received correctly as everything is sent via UDP. Other packets that get sent at specific rates can arrive on any frame. 

If you are connected to the game when it starts transmitting the first frame will contain the following information to help initialise data structures on the receiving application: 

##### **Packets sent on Frame 1: (All packets sent on this frame have “Session timestamp” 0.000)** 

- Session 

- Participants 

- Car Setups 

- Lap Data 

- Motion Data 

- Car Telemetry 

- Car Status 

- Car Damage 

- Motion Ex Data 

As an example, assuming that you are running at 60Hz with 60Hz update rate selected in the menus then you would expect to see the following packets and timestamps: 

##### **Packets sent on Frame 2: (All packets sent on this frame have “Session timestamp” 0.016)** 

- Lap Data 

- Motion Data 

- Car Telemetry 

- Car Status 

- Motion Ex Data 

… 

##### **Packets sent on Frame 31: (All packets sent on this frame have “Session timestamp” 0.5)** 

- Session (since 2 updates per second) 

- Car Setups (since 2 updates per second) 

- Lap Data 

- Motion Data 

@ AZ 2542 



The `sliProNativeSupport` flag controls the output to SLI Pro devices. The `fanatecNativeSupport` flag controls the output to Fanatec (and some related) steering wheel LEDs. Set the values for any of these to `“false”` to disable them and avoid conflicts with your own device manager. 

Please note there is an additional flag to manually control the LED brightness on the SLI Pro: 

```
<led_display sliProForceBrightness="127" />
```

This option (using value in the range 0-255) will be ignored when setting the `sliProNativeSupport` flag to `“false”` . 

Also note it is now possible to edit these values on the fly via the `Game Options->Settings->UDP Telemetry Settings` menu. 

### **Can I configure the UDP output using an XML File?** 

PC users can edit the game’s configuration XML file to configure UDP output. The file is located here (after an initial boot of the game): 

```
...\Documents\My Games\<game_folder>\hardwaresettings\hardware_settings_config.xml
```

You should see the tag: 

```
   <motion>
```

```
     ...
```

```
     <udp enabled="false" broadcast=”false” ip="127.0.0.1" port="20777" sendRate=”20”
format=”2025” yourTelemetry="restricted" onlineNames="off" />
```

```
     ...
```

```
   </motion>
```

Here you can set the values manually. Note that any changes made within the game when it is running will overwrite any changes made manually. 

I4—) 

|~~ee~~<br>~~i ee~~<br>~~ee~~<br>~~eeee~~<br>~~ee~~<br>~~i ee~~<br>~~eeee~~<br>~~eeee~~<br>~~ee~~<br>~~eeee~~<br>~~ee~~<br>~~eeee~~<br>~~ee~~<br>~~eeee~~<br>~~ee~~<br>~~eeee~~<br>~~ee~~<br>~~eeee~~<br>~~ee~~<br>~~i ee~~<br>~~ee~~<br>~~i ee~~<br>~~ee~~<br>~~i ee~~<br>~~ee~~<br>~~i ee~~<br>~~ee~~<br>~~i ee~~<br>~~ee~~<br>~~i ee~~<br>~~ee~~<br>~~i ee~~<br>~~ee~~<br>~~i ee~~<br>~~ee~~<br>~~i ee~~<br>~~ee~~|
|---|



6 AZ25 



<!-- Start of picture text -->
ee ee<br>Oe<br>GG<br>Ge<br>GG<br>Ge<br>GG<br>Ge<br>GG<br>Ge<br>po<br>GG<br>po<br>GG<br>po<br>GG<br>po<br>GG<br>po<br>GG<br>po<br>Ge<br>po<br>GG<br>po<br>GG<br>po<br>GG<br>po<br>GG<br>po<br>GG<br>po<br>GG<br>IGO<br>Ge<br>IGO<br>GG<br><!-- End of picture text -->

0-725 

|~~i-—~~~<br>~~TE~~<br>~~se~~<br>~~TS~~<br>~~TE~~<br>~~TS~~<br>~~TE~~<br>~~TS~~<br>~~se~~<br>~~TE~~<br>~~se~~<br>~~se~~<br>~~se~~<br>~~se~~<br>~~TS~~<br>~~se~~<br>~~se~~<br>~~se~~<br>~~se~~<br>~~se~~<br>~~—se~~<br>~~se~~<br>~~se~~<br>~~se~~<br>~~se~~<br>~~——~~|
|---|



0-725 



<!-- Start of picture text -->
Le<br>a<br>a<br>a<br>a<br>a<br>a<br>a<br>a<br>a<br>a<br>a<br>a<br>a<br>a<br>a<br>a<br>a<br>a<br>a<br>a<br>a<br>a<br>a<br>a<br>a<br>a<br>a<br>a<br>a<br>a<br><!-- End of picture text -->



# © A= 25H 



<!-- Start of picture text -->
—<br><!-- End of picture text -->



0-725 

~~a Sg~~ ~~<u>a</u> a Sg a Sg a a Sg a Sg~~ ~~<u>a a a a a a a a a a a a a a a a a a a a a a a a a a a a a a a a</u>~~ 

© A= 25H 

