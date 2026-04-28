#include <SD.h>
#include <SPI.h>
#include <HX711_ADC.h>
#define RELAY_ON  HIGH
#define RELAY_OFF LOW

// ---------------- Pins -----------------------//

//--------sd chip pin------------
const int SDchipSelect = 2;

//-------Relay------------
const int RelayInterlock = 23;
const int RelayPowerPin = 3;
const int RelayR1Pin = 4;
const int RelayR2Pin = 5;

//--------Motor Control Pin
const int Motor6 = 6;
const int Motor7 = 7;
const int Motor8 = 8;
const int Motor9 = 9;

//---------led------------
const int ledsd = 12;
const int ledHioki = 11;

//----------LoadSensor--------------------
const int HX711_data = 53;
const int HX711_CLK  = 52;
HX711_ADC LoadCell(HX711_data, HX711_CLK);
float calFactor = 602.0;

//--------Analog current sense Pin--------------------
const int TestMaxPin = A11;

// ================================================================
//  GLOBALS
// ================================================================
int cycleCount = 1;   // counts how many cycles completed
int selectedStep = 0;  // fixed step label set by user (e.g. 3 = 50%)

// ---------------- Test selection ----------------
int  selectedTest = 0;   // 0 = not chosen, 1 = TM only, 2 = TM + Other
bool testLocked   = false;

// ---------------- Analog / Current ----------------
const float analogRefVoltage = 3.3;
const int   adcResolution    = 4095;
const float shuntResistance  = 0.422;
float currentZeroOffset         = 0.0;
float resistanceZeroOffsetTM    = 280;
float resistanceZeroOffsetOther = 0.0;

// ---------------- Relay helpers ----------------
bool powerRelayState     = false;
bool interlockRelayState = false;

void setInterlockRelay(bool on) {
  digitalWrite(RelayInterlock, on ? HIGH : LOW);
  interlockRelayState = on;
}
void setPowerRelay(bool on) {
  digitalWrite(RelayPowerPin, on ? HIGH : LOW);
  powerRelayState = on;
}
void setRelayR1(bool on) { digitalWrite(RelayR1Pin, on ? HIGH : LOW); }
void setRelayR2(bool on) { digitalWrite(RelayR2Pin, on ? HIGH : LOW); }

void allRelaysOff() {
  setInterlockRelay(false);
  setPowerRelay(false);
  setRelayR1(false);
  setRelayR2(false);
}

// ---------------- SD ----------------
String folderName = "";
bool   folderReady = false;
bool   sdReady     = false;

// ---------------- App control ----------------
String input    = "";
bool   runArmed = false;

// ================================================================
//  NON-BLOCKING TEST STATE MACHINE
// ================================================================
float measuredCurrent = 0;
float resTM           = NAN;
float resOther        = NAN;
float measuredForce   = NAN;

enum TestState {
  T_IDLE,
  T_INTERLOCK_ON,
  T_WAIT_INTERLOCK_ON,
  T_POWER_ON,
  T_WAIT_STABLE,
  T_MEASURE_CURRENT,
  T_POWER_OFF,
  T_INTERLOCK_OFF,
  T_WAIT_INTERLOCK_OFF,
  T_R1_ON,
  T_WAIT_R1,
  T_READ_R1,
  T_R1_OFF,
  T_R2_ON,
  T_WAIT_R2,
  T_READ_R2,
  T_R2_OFF,
  T_MEASURE_FORCE,
  T_SAVE,
  T_DONE
};

TestState     testState   = T_IDLE;
unsigned long testTimer   = 0;
bool          testRunning = false;

const unsigned long T_INTERLOCK_SETTLE = 100;
const unsigned long T_POWER_STABLE     = 1000;
const unsigned long T_REED_SETTLE      = 300;

// ================================================================
//  FORWARD DECLARATIONS
// ================================================================
void handleSerialInput();
void processCommand(String cmd);
void updateTestSequence();
void startOneCycle();

float ReadCurrentValue();
float ReadResistanceValue(bool isTM);
float ReadForceValue();
void  CalibrateCurrentZero();

void writeToSdCard(String data);
bool ensureSdReady();
bool ensureFolderReady();
String makeFilePath();

// ================================================================
//  SETUP
// ================================================================
void setup() {
  pinMode(ledHioki, OUTPUT);
  pinMode(ledsd, OUTPUT);
  pinMode(RelayPowerPin, OUTPUT);
  pinMode(RelayR1Pin, OUTPUT);
  pinMode(RelayR2Pin, OUTPUT);
  pinMode(RelayInterlock, OUTPUT);
  pinMode(Motor6, OUTPUT);
  pinMode(Motor7, OUTPUT);
  pinMode(Motor8, OUTPUT);
  pinMode(Motor9, OUTPUT);

  // Safe state
  digitalWrite(ledHioki, LOW);
  digitalWrite(ledsd, LOW);
  allRelaysOff();
  digitalWrite(Motor6, LOW);
  digitalWrite(Motor7, LOW);
  digitalWrite(Motor8, LOW);
  digitalWrite(Motor9, LOW);

  analogReadResolution(12);
  Serial.begin(38400);

  //--------Loadcell setup-----------
  LoadCell.begin();
  Serial.println("Taring load cell...");
  LoadCell.start(2000, true);
  LoadCell.setCalFactor(calFactor);
  Serial.println("Load cell tare complete.");

  //------Current zero offset calibration---------
  CalibrateCurrentZero();
  Serial.print("Current ZERO offset = ");
  Serial.println(currentZeroOffset, 4);

  //----------SD setup----------------------------
  Serial.println("SD card Initializing...");
  if (SD.begin(SDchipSelect)) {
    sdReady = true;
    Serial.println("SD card initialized.");
    digitalWrite(ledsd, HIGH);
    delay(300);
  } else {
    sdReady = false;
    Serial.println("SD card initialization failed!");
  }

  //---------------Hioki meter setup-----------------------
  Serial.println("Checking connection from Hioki...");
  Serial3.begin(38400);
  delay(300);

  while (Serial3.available()) Serial3.read();
  Serial3.print("*IDN?\r\n");

  String responseBack = "";
  unsigned long deadline = millis() + 1000;
  while (millis() < deadline) {
    while (Serial3.available()) responseBack += (char)Serial3.read();
  }

  if (responseBack.length() > 0) {
    responseBack.trim();
    Serial.println("Hioki RM3545-02 Response:");
    Serial.println(responseBack);
    digitalWrite(ledHioki, HIGH);
  } else {
    Serial.println("No response from Hioki!");
  }

  Serial.println("Ready. Send FOLDER:name, 1 or 2 to select test, then START.");
}

// ================================================================
//  LOOP
// ================================================================
void loop() {
  handleSerialInput();
  updateTestSequence();
}

// ================================================================
//  START ONE CYCLE
// ================================================================
void startOneCycle() {
  if (!runArmed) return;
  if (testRunning) return;

  measuredCurrent = 0;
  resTM           = NAN;
  resOther        = NAN;
  measuredForce   = NAN;

  Serial.print(String(selectedStep) + ",");

  testState   = T_INTERLOCK_ON;
  testRunning = true;
}

// ================================================================
//  NON-BLOCKING TEST SEQUENCE ENGINE
// ================================================================
void updateTestSequence() {
  if (!testRunning) {
    // If armed and idle → immediately start next cycle
    if (runArmed) startOneCycle();
    return;
  }

  unsigned long now = millis();

  switch (testState) {

    case T_INTERLOCK_ON:
      setInterlockRelay(true);
      testTimer = now;
      testState = T_WAIT_INTERLOCK_ON;
      break;

    case T_WAIT_INTERLOCK_ON:
      if (now - testTimer >= T_INTERLOCK_SETTLE) testState = T_POWER_ON;
      break;

    case T_POWER_ON:
      setPowerRelay(true);
      testTimer = now;
      testState = T_WAIT_STABLE;
      break;

    case T_WAIT_STABLE:
      if (now - testTimer >= T_POWER_STABLE) testState = T_MEASURE_CURRENT;
      break;

    case T_MEASURE_CURRENT:
      if (selectedTest == 1) {
        measuredCurrent = ReadCurrentValue();
      } else {
        measuredCurrent = ReadCurrentValue() / 2.0f;
      }
      Serial.print(" Current: ");
      Serial.print(measuredCurrent, 4);
      Serial.print(" A");
      testState = T_POWER_OFF;
      break;

    case T_POWER_OFF:
      setPowerRelay(false);
      testState = T_INTERLOCK_OFF;
      break;

    case T_INTERLOCK_OFF:
      setInterlockRelay(false);
      testTimer = now;
      testState = T_WAIT_INTERLOCK_OFF;
      break;

    case T_WAIT_INTERLOCK_OFF:
      if (now - testTimer >= T_INTERLOCK_SETTLE) testState = T_R1_ON;
      break;

    case T_R1_ON:
      setRelayR1(true);
      testTimer = now;
      testState = T_WAIT_R1;
      break;

    case T_WAIT_R1:
      if (now - testTimer >= T_REED_SETTLE) testState = T_READ_R1;
      break;

    case T_READ_R1:
      resTM     = ReadResistanceValue(true);
      testState = T_R1_OFF;
      break;

    case T_R1_OFF:
      setRelayR1(false);
      testState = (selectedTest == 1) ? T_MEASURE_FORCE : T_R2_ON;
      break;

    case T_R2_ON:
      setRelayR2(true);
      testTimer = now;
      testState = T_WAIT_R2;
      break;

    case T_WAIT_R2:
      if (now - testTimer >= T_REED_SETTLE) testState = T_READ_R2;
      break;

    case T_READ_R2:
      resOther  = ReadResistanceValue(false);
      testState = T_R2_OFF;
      break;

    case T_R2_OFF:
      setRelayR2(false);
      testState = T_MEASURE_FORCE;
      break;

    case T_MEASURE_FORCE:
      measuredForce = ReadForceValue();
      testState     = T_SAVE;
      break;

    case T_SAVE: {
      String line = "";
      line += "Step" + String(selectedStep) + ",";
      line += "Current: " + String(measuredCurrent, 4) + " A,";
      line += "ResTM: ";
      line += isnan(resTM) ? "NA" : String(resTM, 3) + " mOhm";

      if (selectedTest == 2) {
        line += ",ResOther: ";
        line += isnan(resOther) ? "NA" : String(resOther, 3) + " mOhm";
      }

      line += ",Force: " + String(measuredForce, 0) + " g";

      writeToSdCard(line);
      Serial.println();

      cycleCount++;
      testState = T_DONE;
      break;
    }

    case T_DONE:
      allRelaysOff();
      CalibrateCurrentZero();   // recalibrate zero offset after each cycle

      testRunning = false;
      testState   = T_IDLE;
      // loop() will immediately call startOneCycle() again if still armed
      break;

    case T_IDLE:
      break;
  }
}

// ================================================================
//  SD CARD HELPERS
// ================================================================
void writeToSdCard(String data) {
  if (!sdReady || !folderReady) {
    if (!ensureFolderReady()) {
      Serial.println("SD ERR: folder not ready");
      return;
    }
  }

  String path = makeFilePath();
  File file   = SD.open(path.c_str(), FILE_WRITE);

  if (!file) {
    Serial.println("SD write failed!");
    sdReady = false;
    digitalWrite(ledsd, LOW);
    return;
  }

  if (file.size() == 0) {
    if (selectedTest == 1)
      file.println("Cycle,Current(A),ResTM(mOhm),Force(g)");
    else
      file.println("Cycle,Current(A),ResTM(mOhm),ResOther(mOhm),Force(g)");
  }

  file.println(data);
  file.close();
}

bool ensureSdReady() {
  if (sdReady) return true;
  if (SD.begin(SDchipSelect)) {
    sdReady = true;
    digitalWrite(ledsd, HIGH);
    return true;
  }
  sdReady = false;
  digitalWrite(ledsd, LOW);
  return false;
}

bool ensureFolderReady() {
  if (!ensureSdReady()) return false;
  if (folderReady && folderName.length() > 0) return true;
  if (folderName.length() == 0) return false;
  if (!SD.exists(folderName.c_str())) {
    if (!SD.mkdir(folderName.c_str())) {
      folderReady = false;
      return false;
    }
  }
  folderReady = true;
  return true;
}

String makeFilePath() {
  // Single file per session inside folder
  return folderName + "/DATA.CSV";
}

// ================================================================
//  SERIAL COMMAND HANDLER
// ================================================================
void handleSerialInput() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      input.trim();
      if (input.length() > 0) processCommand(input);
      input = "";
    } else {
      input += c;
      if (input.length() > 16) input = "";
    }
  }
}

void processCommand(String cmd) {
  cmd.trim();
  cmd.toUpperCase();

  // ---------- STEP ----------
  if (cmd.startsWith("STEP:")) {
    selectedStep = cmd.substring(5).toInt();
    Serial.print("OK STEP ");
    Serial.println(selectedStep);
    return;
  }

  // ---------- FOLDER ----------
  if (cmd.startsWith("FOLDER:")) {
    if (!ensureSdReady()) {
      Serial.println("SD ERR: init failed");
      folderReady = false;
      return;
    }
    folderName = cmd.substring(7);
    folderName.trim();
    folderName.replace("/", "_");
    folderName.replace("\\", "_");
    folderName.replace(":", "_");
    folderName.replace(" ", "_");
    if (folderName.length() > 8) folderName = folderName.substring(0, 8);
    if (folderName.length() == 0) folderName = "SESSION";

    if (!SD.exists(folderName.c_str())) {
      if (!SD.mkdir(folderName.c_str())) {
        Serial.println("ERR MKDIR");
        folderReady = false;
        return;
      }
    }
    folderReady = true;
    Serial.print("OK FOLDER ");
    Serial.println(folderName);
    return;
  }

  // ---------- TEST SELECT ----------
  if (!runArmed && !testLocked) {
    if (cmd == "1" || cmd == "2") {
      selectedTest = (cmd == "1") ? 1 : 2;
      if (selectedTest == 1) {
        Serial.println("OK TEST 1 - TM Pin Only");
      } else {
        Serial.println("OK TEST 2 - TM + Other Pins");
      }
      return;
    }
  } else {
    if (cmd == "1" || cmd == "2") {
      Serial.println("ERR TEST_LOCKED");
      return;
    }
  }

  // ---------- START ----------
  if (cmd == "START") {
    if (!folderReady) { Serial.println("ERR: Please Set Folder First"); return; }
    if (selectedTest == 0) { Serial.println("ERR: Please Select Test Mode First"); return; }
    if (selectedStep == 0) { Serial.println("ERR: Please Set Step First. Send STEP:3"); return; }

    cycleCount = 1;
    CalibrateCurrentZero();   // recalibrate current zero at start

    runArmed   = true;
    testLocked = true;

    Serial.print("OK START - ");
    Serial.println(selectedTest == 1 ? "TM Pin Only" : "TM + Other Pins");
    return;
  }

  // ---------- STOP ----------
  if (cmd == "STOP") {
    runArmed    = false;
    testRunning = false;
    testState   = T_IDLE;
    allRelaysOff();
    Serial.println("OK STOP");
    Serial.print("Total Cycles Completed: ");
    Serial.println(cycleCount - 1);
    selectedTest = 0;
    testLocked   = false;
    return;
  }

  // ---------- SERVO ON ----------
  if (cmd == "SERVOON") {
    digitalWrite(Motor9, HIGH);
    delay(1500);
    digitalWrite(Motor9, LOW);
    return;
  }

  // ---------- SERVO OFF ----------
  if (cmd == "SERVOOFF") {
    digitalWrite(Motor7, HIGH);
    delay(1500);
    digitalWrite(Motor7, LOW);
    return;
  }

  // ---------- HiokiOnTM / HiokiOffTM / HiokiOnOther / HiokiOffOther ----------
  if (cmd == "HIOKIONTM") {
    setRelayR1(true);
    setRelayR2(false);
    Serial.println("Hioki reading TestMax pin resistance.");
    return;
  }

  if (cmd == "HIOKIOFFTM") {
    setRelayR1(false);
    Serial.println("Hioki Off.");
    return;
  }

  if (cmd == "HIOKIONOTHER") {
    setRelayR2(true);
    setRelayR1(false);
    Serial.println("Hioki Meter reading Other pin resistance.");
    return;
  }

  if (cmd == "HIOKIOFFOTHER") {
    setRelayR2(false);
    Serial.println("Hioki Off.");
    return;
  }

  // ---------- 0ADJTM — record TM zero offset (use after HiokiOnTM) ----------
  if (cmd == "0ADJTM") {
    // R1 should already be ON from HIKION — just read Hioki
    while (Serial3.available()) Serial3.read();
    Serial3.print("READ?\r\n");
    delay(150);
    while (Serial3.available()) Serial3.read();
    Serial3.print("READ?\r\n");

    String raw = "";
    unsigned long t0 = millis();
    while (millis() - t0 < 800) {
      while (Serial3.available()) {
        raw += (char)Serial3.read();
        t0 = millis();
      }
    }

    raw.trim();
    if (raw.length() > 0) {
      resistanceZeroOffsetTM = raw.toFloat() * 1000.0f;
      Serial.print("TestMax Pin Zero Offset OK: ");
      Serial.print(resistanceZeroOffsetTM, 4);
      Serial.println(" mOhm");
      Serial.println("Press HiokiOff when done monitoring.");
    } else {
      Serial.println("0AdjTM ERROR: no data");
    }
    // Put Hioki back to continuous live reading mode
    Serial3.print(":INIT:CONT ON\r\n");
    return;
  }

  // ---------- 0ADJOTHER — record Other zero offset (R2 must be ON from HiokiOnOther) ----------
  if (cmd == "0ADJOTHER") {
    while (Serial3.available()) Serial3.read();
    Serial3.print("READ?\r\n");
    delay(150);
    while (Serial3.available()) Serial3.read();
    Serial3.print("READ?\r\n");

    String raw = "";
    unsigned long t0 = millis();
    while (millis() - t0 < 800) {
      while (Serial3.available()) {
        raw += (char)Serial3.read();
        t0 = millis();
      }
    }

    raw.trim();
    if (raw.length() > 0) {
      resistanceZeroOffsetOther = raw.toFloat() * 1000.0f;
      Serial.print("0AdjOther OK: ");
      Serial.print(resistanceZeroOffsetOther, 4);
      Serial.println(" mOhm");
    } else {
      Serial.println("0AdjOther ERROR: no data");
    }
    // Put Hioki back to continuous live reading mode
    Serial3.print(":INIT:CONT ON\r\n");
    return;
  }

// ---------- CurrentOn / CurrentOff ----------
  if (cmd == "CURRENTON") {
    setRelayR1(false);          // strictly OFF resistance path
    setRelayR2(false);          // strictly OFF resistance path
    delay(50);
    setInterlockRelay(true);    // interlock ON → 12V to power relay VCC
    delay(100);                 // wait for interlock to physically switch
    setPowerRelay(true);        // power relay ON → current flows
    Serial.println("CurrentOn: Current path OPEN. Resistance path OFF.");
    return;
  }

  if (cmd == "CURRENTOFF") {
    setPowerRelay(false);
    setInterlockRelay(false);
    Serial.println("CurrentOff: Current path CLOSED.");
    return;
  }

}


// ================================================================
//  CURRENT CALIBRATION
// ================================================================
void CalibrateCurrentZero() {
  const int N = 200;
  long sum = 0;
  delay(100);
  for (int i = 0; i < N; i++) {
    sum += analogRead(TestMaxPin);
    delayMicroseconds(20);
  }
  float adc     = sum / (float)N;
  float voltage = adc * (analogRefVoltage / (float)adcResolution);
  currentZeroOffset = voltage / shuntResistance;
}

// ================================================================
//  SENSOR READINGS
// ================================================================
float ReadCurrentValue() {
  const int N = 200;
  long sum = 0;
  delay(100);
  for (int i = 0; i < N; i++) {
    sum += analogRead(TestMaxPin);
    delayMicroseconds(20);
  }
  float adc     = sum / (float)N;
  float voltage = adc * (analogRefVoltage / (float)adcResolution);
  float current = (voltage / shuntResistance) - currentZeroOffset;
  return current;
}

float ReadResistanceValue(bool isTM) {
  while (Serial3.available()) Serial3.read();

  Serial3.print("READ?\r\n");
  delay(400);
  while (Serial3.available()) Serial3.read();

  Serial3.print("READ?\r\n");

  String raw = "";
  unsigned long deadline = millis() + 1500;
  while (millis() < deadline) {
    while (Serial3.available()) raw += (char)Serial3.read();
  }

  raw.trim();
  if (raw.length() == 0) {
    Serial.print(isTM ? " | ResTM: NA" : " | ResOther: NA");
    return NAN;
  }

  float mOhm = (raw.toFloat() * 1000.0f) - (isTM ? resistanceZeroOffsetTM : resistanceZeroOffsetOther);

  Serial.print(isTM ? " | ResTM: " : " | ResOther: ");
  Serial.print(mOhm, 3);
  Serial.print(" mOhm");

  return mOhm;
}

float ReadForceValue() {
  const int   STABLE_COUNT = 10;
  const float STABLE_DELTA = 2.0;
  const int   AVG_SAMPLES  = 10;
  const unsigned long SETTLE_TIME = 1500;
  const unsigned long TIMEOUT     = 7000;

  delay(SETTLE_TIME);

  float last        = 0;
  int   stableCount = 0;
  unsigned long t0  = millis();

  while (millis() - t0 < TIMEOUT) {
    if (LoadCell.update()) {
      float val = LoadCell.getData();
      stableCount = (abs(val - last) <= STABLE_DELTA) ? stableCount + 1 : 0;
      last = val;
      if (stableCount >= STABLE_COUNT) break;
    }
  }

  float sum  = 0;
  int   count = 0;
  while (count < AVG_SAMPLES && (millis() - t0) < TIMEOUT) {
    if (LoadCell.update()) {
      sum += LoadCell.getData();
      count++;
    }
  }

  if (count == 0) {
    Serial.print(" | Force: NA");
    return NAN;
  }

  float avg = sum / count;
  if (avg < 0) avg = 0;

  Serial.print(" | Force: ");
  Serial.print(avg, 0);
  Serial.print(" g");

  return avg;
}
