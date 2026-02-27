/*
 * LaserLapTimer - Firmware simplificado para cronometraje por laser
 * Hardware: Arduino Mega 2560 + KY-008 Laser + LDR con resistencia 20K
 *
 * Circuito LDR (divisor de voltaje):
 *   5V ---[LDR]---+---[20K]--- GND
 *                 |
 *                 A0
 *
 * KY-008: S→D13, +→5V, -→GND
 *
 * Protocolo serial: 115200 baud, JSON
 */

// ─── Pines ───
const int PIN_LASER = 13;
const int PIN_LDR   = A0;

// ─── Constantes ───
const unsigned long SERIAL_BAUD       = 115200;
const unsigned long MIN_LAP_MS        = 2000;    // Cooldown entre cortes
const unsigned long STREAM_INTERVAL_MS = 100;    // ~10 Hz streaming
const int           CALIBRATION_SAMPLES = 10;    // Muestras para baseline
const unsigned long STARTUP_DELAY_MS  = 500;     // Espera estabilizacion laser

// ─── Estado ───
int           baseline     = 0;
int           threshold    = 0;
bool          laserOn      = true;
bool          streamOn     = false;
unsigned long lastCutMs    = 0;
unsigned long lastStreamMs = 0;
String        cmdBuffer    = "";

// ─── Helpers JSON ───

void sendEvent(const char* event, const String& dataJson) {
  Serial.print("{\"event\":\"");
  Serial.print(event);
  Serial.print("\",\"ms\":");
  Serial.print(millis());
  Serial.print(",\"data\":{");
  Serial.print(dataJson);
  Serial.println("}}");
}

// ─── Calibracion ───

void calibrate() {
  long sum = 0;
  for (int i = 0; i < CALIBRATION_SAMPLES; i++) {
    sum += analogRead(PIN_LDR);
    delay(20);
  }
  baseline = sum / CALIBRATION_SAMPLES;
  threshold = baseline / 2;
}

// ─── Comandos ───

void processCommand(const String& cmd) {
  String c = cmd;
  c.trim();
  c.toUpperCase();

  if (c == "LDR") {
    int val = analogRead(PIN_LDR);
    String data = "\"value\":" + String(val) +
                  ",\"baseline\":" + String(baseline) +
                  ",\"threshold\":" + String(threshold);
    sendEvent("LDR_READ", data);
  }
  else if (c.startsWith("THRESHOLD ")) {
    int val = c.substring(10).toInt();
    if (val >= 0 && val <= 1023) {
      threshold = val;
      sendEvent("THRESHOLD_SET", "\"threshold\":" + String(threshold));
    } else {
      sendEvent("ERROR", "\"msg\":\"Threshold debe ser 0-1023\"");
    }
  }
  else if (c == "LASER ON") {
    laserOn = true;
    digitalWrite(PIN_LASER, HIGH);
    sendEvent("LASER", "\"state\":\"ON\"");
  }
  else if (c == "LASER OFF") {
    laserOn = false;
    digitalWrite(PIN_LASER, LOW);
    sendEvent("LASER", "\"state\":\"OFF\"");
  }
  else if (c == "STREAM ON") {
    streamOn = true;
    sendEvent("STREAM", "\"state\":\"ON\"");
  }
  else if (c == "STREAM OFF") {
    streamOn = false;
    sendEvent("STREAM", "\"state\":\"OFF\"");
  }
  else if (c == "PING") {
    sendEvent("PONG", "");
  }
  else if (c == "RESET") {
    lastCutMs = 0;
    calibrate();
    sendEvent("READY", "\"baseline\":" + String(baseline) +
                        ",\"threshold\":" + String(threshold));
  }
  else if (c.length() > 0) {
    sendEvent("ERROR", "\"msg\":\"Comando desconocido: " + cmd + "\"");
  }
}

// ─── Setup ───

void setup() {
  Serial.begin(SERIAL_BAUD);
  while (!Serial) { ; }

  pinMode(PIN_LASER, OUTPUT);
  digitalWrite(PIN_LASER, HIGH);
  laserOn = true;

  delay(STARTUP_DELAY_MS);

  calibrate();

  sendEvent("READY", "\"baseline\":" + String(baseline) +
                      ",\"threshold\":" + String(threshold));
}

// ─── Loop ───

void loop() {
  unsigned long now = millis();

  // Leer LDR
  int ldrValue = analogRead(PIN_LDR);

  // Detectar corte de haz
  if (ldrValue < threshold && (now - lastCutMs) >= MIN_LAP_MS) {
    lastCutMs = now;
    sendEvent("LDR_CUT", "\"value\":" + String(ldrValue));
  }

  // Streaming periodico
  if (streamOn && (now - lastStreamMs) >= STREAM_INTERVAL_MS) {
    lastStreamMs = now;
    sendEvent("LDR_STREAM", "\"value\":" + String(ldrValue));
  }

  // Procesar comandos serial
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (cmdBuffer.length() > 0) {
        processCommand(cmdBuffer);
        cmdBuffer = "";
      }
    } else {
      cmdBuffer += c;
    }
  }
}
