/*
 * PerLap v2.0 - Cronómetro de vueltas RC 1/43 - Triple Validación
 * Hardware: Arduino Mega 2560 (CH340)
 *
 * Sistema de 3 capas:
 *   1. MAGNÉTICA  - 4x Hall A3144 bajo el tatami (tiempo base)
 *   2. FOTÓNICA   - Láser + LDR de muro a muro (precisión de corte)
 *   3. ÓPTICA     - TCS3200 en puente superior (ID por color de sticker)
 *
 * Salida: Serial USB a 115200 baud (formato JSON)
 * Extras: Buzzer piezoeléctrico + 3 LEDs (semáforo R/Y/G)
 *
 * Conexiones Arduino Mega:
 * ─────────────────────────────────────────────────
 *  Componente        Pin(es)          Notas
 * ─────────────────────────────────────────────────
 *  Hall A3144 (x4)   2 (INT0)         Paralelo, pull-up 10k externo
 *  LDR (analógico)   A0               Divisor de voltaje con R 10k
 *  Láser puntero     7                Encender/apagar vía transistor
 *  TCS3200 S0        22               Escalado de frecuencia
 *  TCS3200 S1        23               Escalado de frecuencia
 *  TCS3200 S2        24               Filtro de color
 *  TCS3200 S3        25               Filtro de color
 *  TCS3200 OUT       26               Salida de frecuencia
 *  TCS3200 OE        27               Output Enable (LOW = activo)
 *  LED Rojo          8                Con resistencia 220Ω
 *  LED Amarillo      9                Con resistencia 220Ω
 *  LED Verde         10               Con resistencia 220Ω
 *  Buzzer            11               Pasivo (PWM)
 *  Trigger Cámara    12               Pulso HIGH para foto-finish
 * ─────────────────────────────────────────────────
 */

// =====================================================================
//  CONFIGURACIÓN DE PINES
// =====================================================================

// --- Sensores Hall (magnético) ---
const int PIN_HALL       = 2;    // INT0 en Mega - los 4 sensores en paralelo

// --- Láser + LDR (fotónico) ---
const int PIN_LDR        = A0;   // Lectura analógica del fotorresistor
const int PIN_LASER       = 7;   // Control del puntero láser

// --- Sensor de Color TCS3200 (óptico) ---
const int PIN_TCS_S0      = 22;
const int PIN_TCS_S1      = 23;
const int PIN_TCS_S2      = 24;
const int PIN_TCS_S3      = 25;
const int PIN_TCS_OUT     = 26;
const int PIN_TCS_OE      = 27;

// --- Indicadores ---
const int PIN_LED_RED     = 8;
const int PIN_LED_YELLOW  = 9;
const int PIN_LED_GREEN   = 10;
const int PIN_BUZZER      = 11;
const int PIN_CAM_TRIGGER = 12;

// =====================================================================
//  CONSTANTES DE CALIBRACIÓN
// =====================================================================

const unsigned long SERIAL_BAUD    = 115200;

// Tiempos
const unsigned long MIN_LAP_MS     = 2000;   // Mínimo entre vueltas (ms)
const unsigned long DEBOUNCE_MS    = 30;      // Debounce Hall (ms)
const unsigned long LDR_COOLDOWN_MS = 100;    // Cooldown del láser tras corte (ms)
const unsigned long CAM_PULSE_MS   = 50;      // Duración pulso trigger cámara (ms)

// LDR
const int LDR_THRESHOLD            = 300;     // Umbral: por debajo = haz cortado
                                               // (calibrar con Serial Plotter)

// TCS3200 - Umbrales de color (calibrar con cada sticker)
// Estos son valores iniciales, se ajustan con el comando "CAL"
const int COLOR_MARGIN              = 30;      // Margen de tolerancia para matching

// =====================================================================
//  ESTRUCTURAS DE DATOS
// =====================================================================

// Colores registrados para identificar autos
struct CarColor {
  char name[12];       // Nombre del auto (ej: "P1", "ROJO", etc.)
  int red;             // Frecuencia componente roja
  int green;           // Frecuencia componente verde
  int blue;            // Frecuencia componente azul
  bool active;         // ¿Slot ocupado?
};

const int MAX_CARS = 6;
CarColor cars[MAX_CARS];

// Estado de cada auto
struct CarState {
  unsigned long lastLapTime;   // Timestamp última vuelta
  int lapCount;                // Vueltas completadas
  bool started;                // ¿Ya cruzó la meta al menos una vez?
  unsigned long bestLap;       // Mejor vuelta (ms)
};

CarState carStates[MAX_CARS];

// =====================================================================
//  VARIABLES GLOBALES
// =====================================================================

// --- Hall (interrupción) ---
volatile bool hallTriggered = false;
volatile unsigned long hallTriggerTime = 0;

// --- LDR ---
unsigned long lastLdrCut = 0;

// --- Sistema ---
bool systemReady = false;
int ldrBaseline = 0;           // Lectura base del LDR con láser encendido (sin obstrucción)

// =====================================================================
//  INTERRUPCIÓN - Sensor Hall
// =====================================================================

void hallISR() {
  hallTriggerTime = millis();
  hallTriggered = true;
}

// =====================================================================
//  SETUP
// =====================================================================

void setup() {
  // --- Serial ---
  Serial.begin(SERIAL_BAUD);
  while (!Serial) { ; }  // Esperar conexión USB (necesario en algunos Mega CH340)

  // --- Pines Hall ---
  pinMode(PIN_HALL, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(PIN_HALL), hallISR, FALLING);

  // --- Pines Láser + LDR ---
  pinMode(PIN_LASER, OUTPUT);
  digitalWrite(PIN_LASER, HIGH);  // Encender láser
  pinMode(PIN_LDR, INPUT);

  // --- Pines TCS3200 ---
  pinMode(PIN_TCS_S0, OUTPUT);
  pinMode(PIN_TCS_S1, OUTPUT);
  pinMode(PIN_TCS_S2, OUTPUT);
  pinMode(PIN_TCS_S3, OUTPUT);
  pinMode(PIN_TCS_OUT, INPUT);
  pinMode(PIN_TCS_OE, OUTPUT);

  // Escalado de frecuencia al 20% (S0=HIGH, S1=LOW)
  digitalWrite(PIN_TCS_S0, HIGH);
  digitalWrite(PIN_TCS_S1, LOW);

  // Apagar sensor de color por defecto (OE HIGH = deshabilitado)
  digitalWrite(PIN_TCS_OE, HIGH);

  // --- Indicadores ---
  pinMode(PIN_LED_RED, OUTPUT);
  pinMode(PIN_LED_YELLOW, OUTPUT);
  pinMode(PIN_LED_GREEN, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_CAM_TRIGGER, OUTPUT);

  // --- Inicializar arrays ---
  for (int i = 0; i < MAX_CARS; i++) {
    cars[i].active = false;
    resetCarState(i);
  }

  // --- Secuencia de arranque (semáforo) ---
  startupSequence();

  // --- Calibrar LDR baseline ---
  delay(200);
  ldrBaseline = analogRead(PIN_LDR);

  // --- Listo ---
  systemReady = true;
  sendEvent("READY", "{\"ldr_baseline\":" + String(ldrBaseline) + "}");
}

// =====================================================================
//  LOOP PRINCIPAL
// =====================================================================

void loop() {
  // Procesar comandos desde la PC
  processSerialCommands();

  if (!systemReady) return;

  // --- Capa 1: Sensor Hall (interrupción) ---
  if (hallTriggered) {
    hallTriggered = false;
    unsigned long triggerTime = hallTriggerTime;

    // Debounce
    static unsigned long lastHallProcess = 0;
    if ((triggerTime - lastHallProcess) < DEBOUNCE_MS) return;
    lastHallProcess = triggerTime;

    processLapCrossing(triggerTime, "HALL");
  }

  // --- Capa 2: Láser + LDR (polling rápido) ---
  int ldrValue = analogRead(PIN_LDR);
  unsigned long now = millis();

  if (ldrValue < LDR_THRESHOLD && (now - lastLdrCut) > LDR_COOLDOWN_MS) {
    lastLdrCut = now;
    // Solo registrar como referencia de precisión, no como trigger independiente
    // El Hall es el trigger principal; el LDR refina el timestamp
    sendEvent("LDR_CUT", "{\"ldr\":" + String(ldrValue) + ",\"t\":" + String(now) + "}");
  }
}

// =====================================================================
//  PROCESAMIENTO DE CRUCE DE META
// =====================================================================

void processLapCrossing(unsigned long triggerTime, const char* source) {
  // Feedback inmediato
  digitalWrite(PIN_LED_GREEN, HIGH);
  buzzShort();

  // --- Capa 3: Leer color del auto ---
  int colorId = readCarColor();
  char carName[12] = "UNKNOWN";

  if (colorId >= 0 && colorId < MAX_CARS && cars[colorId].active) {
    strncpy(carName, cars[colorId].name, sizeof(carName) - 1);
  }

  // --- Trigger cámara para foto-finish ---
  triggerCamera();

  // --- Calcular tiempo de vuelta ---
  if (colorId >= 0 && colorId < MAX_CARS) {
    CarState &cs = carStates[colorId];

    if (!cs.started) {
      // Primera pasada de este auto
      cs.started = true;
      cs.lastLapTime = triggerTime;
      cs.lapCount = 0;

      sendEvent("START", "{\"car\":\"" + String(carName) +
                "\",\"id\":" + String(colorId) +
                ",\"src\":\"" + String(source) + "\"}");
    } else {
      unsigned long elapsed = triggerTime - cs.lastLapTime;

      if (elapsed < MIN_LAP_MS) {
        digitalWrite(PIN_LED_GREEN, LOW);
        return;  // Demasiado rápido, ignorar
      }

      cs.lastLapTime = triggerTime;
      cs.lapCount++;

      // Mejor vuelta
      if (elapsed < cs.bestLap) {
        cs.bestLap = elapsed;
      }

      // Formato del tiempo
      unsigned long secs = elapsed / 1000;
      unsigned long ms   = elapsed % 1000;

      sendEvent("LAP", "{\"car\":\"" + String(carName) +
                "\",\"id\":" + String(colorId) +
                ",\"lap\":" + String(cs.lapCount) +
                ",\"time\":" + String(elapsed) +
                ",\"time_fmt\":\"" + String(secs) + "." + zeroPad(ms, 3) + "\"" +
                ",\"best\":" + String(cs.bestLap) +
                ",\"src\":\"" + String(source) + "\"}");
    }
  } else {
    // Auto no identificado - registrar igual con el Hall
    static unsigned long unknownLastLap = 0;
    static int unknownLapCount = 0;
    static bool unknownStarted = false;

    if (!unknownStarted) {
      unknownStarted = true;
      unknownLastLap = triggerTime;
      unknownLapCount = 0;
      sendEvent("START", "{\"car\":\"UNKNOWN\",\"id\":-1,\"src\":\"" + String(source) + "\"}");
    } else {
      unsigned long elapsed = triggerTime - unknownLastLap;
      if (elapsed < MIN_LAP_MS) {
        digitalWrite(PIN_LED_GREEN, LOW);
        return;
      }
      unknownLastLap = triggerTime;
      unknownLapCount++;

      unsigned long secs = elapsed / 1000;
      unsigned long ms   = elapsed % 1000;

      sendEvent("LAP", "{\"car\":\"UNKNOWN\",\"id\":-1"
                ",\"lap\":" + String(unknownLapCount) +
                ",\"time\":" + String(elapsed) +
                ",\"time_fmt\":\"" + String(secs) + "." + zeroPad(ms, 3) + "\"" +
                ",\"src\":\"" + String(source) + "\"}");
    }
  }

  delay(80);
  digitalWrite(PIN_LED_GREEN, LOW);
}

// =====================================================================
//  SENSOR DE COLOR TCS3200
// =====================================================================

int readColorFrequency(bool s2, bool s3) {
  digitalWrite(PIN_TCS_S2, s2);
  digitalWrite(PIN_TCS_S3, s3);
  delayMicroseconds(100);  // Estabilizar filtro
  return (int)pulseIn(PIN_TCS_OUT, LOW, 50000);  // Timeout 50ms
}

void readRGB(int &r, int &g, int &b) {
  // Habilitar sensor
  digitalWrite(PIN_TCS_OE, LOW);
  delayMicroseconds(200);

  r = readColorFrequency(LOW, LOW);    // Filtro rojo
  g = readColorFrequency(HIGH, HIGH);  // Filtro verde
  b = readColorFrequency(LOW, HIGH);   // Filtro azul

  // Deshabilitar sensor
  digitalWrite(PIN_TCS_OE, HIGH);
}

int readCarColor() {
  int r, g, b;
  readRGB(r, g, b);

  // Buscar coincidencia en autos registrados
  for (int i = 0; i < MAX_CARS; i++) {
    if (!cars[i].active) continue;

    if (abs(r - cars[i].red) < COLOR_MARGIN &&
        abs(g - cars[i].green) < COLOR_MARGIN &&
        abs(b - cars[i].blue) < COLOR_MARGIN) {
      return i;
    }
  }

  return -1;  // No identificado
}

// =====================================================================
//  CÁMARA TRIGGER
// =====================================================================

void triggerCamera() {
  digitalWrite(PIN_CAM_TRIGGER, HIGH);
  delay(CAM_PULSE_MS);
  digitalWrite(PIN_CAM_TRIGGER, LOW);
}

// =====================================================================
//  COMUNICACIÓN SERIAL (JSON)
// =====================================================================

void sendEvent(const char* type, String data) {
  Serial.print("{\"event\":\"");
  Serial.print(type);
  Serial.print("\",\"ms\":");
  Serial.print(millis());
  Serial.print(",\"data\":");
  Serial.print(data);
  Serial.println("}");
}

void processSerialCommands() {
  if (!Serial.available()) return;

  String cmd = Serial.readStringUntil('\n');
  cmd.trim();

  if (cmd.startsWith("REG ")) {
    // Registrar auto: REG <slot> <nombre>
    // Ejemplo: REG 0 ROJO
    cmdRegisterCar(cmd);

  } else if (cmd == "CAL") {
    // Calibrar color del auto actualmente sobre el sensor
    cmdCalibrate();

  } else if (cmd.startsWith("CAL ")) {
    // Calibrar slot específico: CAL <slot>
    cmdCalibrateSlot(cmd);

  } else if (cmd == "LDR") {
    // Leer valor actual del LDR
    sendEvent("LDR_READ", "{\"value\":" + String(analogRead(PIN_LDR)) +
              ",\"baseline\":" + String(ldrBaseline) + "}");

  } else if (cmd == "RGB") {
    // Leer color actual del TCS3200
    int r, g, b;
    readRGB(r, g, b);
    sendEvent("RGB_READ", "{\"r\":" + String(r) + ",\"g\":" + String(g) +
              ",\"b\":" + String(b) + "}");

  } else if (cmd == "RESET") {
    // Reiniciar estados
    cmdReset();

  } else if (cmd == "STATUS") {
    // Enviar estado de todos los autos
    cmdStatus();

  } else if (cmd == "PING") {
    sendEvent("PONG", "{}");

  } else {
    sendEvent("ERROR", "{\"msg\":\"Comando desconocido: " + cmd + "\"}");
  }
}

// --- Comandos ---

void cmdRegisterCar(String cmd) {
  // REG <slot> <nombre>
  int slot = cmd.substring(4, 5).toInt();
  String name = cmd.substring(6);
  name.trim();

  if (slot < 0 || slot >= MAX_CARS) {
    sendEvent("ERROR", "{\"msg\":\"Slot inválido (0-" + String(MAX_CARS - 1) + ")\"}");
    return;
  }

  name.toCharArray(cars[slot].name, sizeof(cars[slot].name));
  cars[slot].active = true;
  resetCarState(slot);

  sendEvent("CAR_REG", "{\"slot\":" + String(slot) + ",\"name\":\"" + name + "\"}");
}

void cmdCalibrate() {
  int r, g, b;
  readRGB(r, g, b);
  sendEvent("CAL_READ", "{\"r\":" + String(r) + ",\"g\":" + String(g) +
            ",\"b\":" + String(b) +
            ",\"hint\":\"Usa CAL <slot> para asignar a un auto\"}");
}

void cmdCalibrateSlot(String cmd) {
  int slot = cmd.substring(4).toInt();

  if (slot < 0 || slot >= MAX_CARS || !cars[slot].active) {
    sendEvent("ERROR", "{\"msg\":\"Slot inválido o no registrado\"}");
    return;
  }

  int r, g, b;
  readRGB(r, g, b);

  cars[slot].red = r;
  cars[slot].green = g;
  cars[slot].blue = b;

  sendEvent("CAL_SET", "{\"slot\":" + String(slot) +
            ",\"name\":\"" + String(cars[slot].name) + "\"" +
            ",\"r\":" + String(r) + ",\"g\":" + String(g) + ",\"b\":" + String(b) + "}");
}

void cmdReset() {
  for (int i = 0; i < MAX_CARS; i++) {
    resetCarState(i);
  }
  sendEvent("RESET", "{}");
  buzzShort();
}

void cmdStatus() {
  for (int i = 0; i < MAX_CARS; i++) {
    if (!cars[i].active) continue;
    CarState &cs = carStates[i];
    sendEvent("STATUS", "{\"slot\":" + String(i) +
              ",\"name\":\"" + String(cars[i].name) + "\"" +
              ",\"laps\":" + String(cs.lapCount) +
              ",\"best\":" + String(cs.bestLap) +
              ",\"started\":" + String(cs.started ? "true" : "false") + "}");
  }
}

// =====================================================================
//  UTILIDADES
// =====================================================================

void resetCarState(int i) {
  carStates[i].lastLapTime = 0;
  carStates[i].lapCount = 0;
  carStates[i].started = false;
  carStates[i].bestLap = 999999UL;
}

String zeroPad(unsigned long val, int width) {
  String s = String(val);
  while ((int)s.length() < width) s = "0" + s;
  return s;
}

void buzzShort() {
  tone(PIN_BUZZER, 2000, 60);
}

void buzzLong() {
  tone(PIN_BUZZER, 1500, 300);
}

void startupSequence() {
  // Secuencia tipo semáforo F1: Rojo -> Amarillo -> Verde
  int delayStep = 500;

  // Rojo
  digitalWrite(PIN_LED_RED, HIGH);
  tone(PIN_BUZZER, 800, 200);
  delay(delayStep);

  // Rojo + Amarillo
  digitalWrite(PIN_LED_YELLOW, HIGH);
  tone(PIN_BUZZER, 1000, 200);
  delay(delayStep);

  // Verde (apagar los demás)
  digitalWrite(PIN_LED_RED, LOW);
  digitalWrite(PIN_LED_YELLOW, LOW);
  digitalWrite(PIN_LED_GREEN, HIGH);
  tone(PIN_BUZZER, 1500, 400);
  delay(delayStep);

  digitalWrite(PIN_LED_GREEN, LOW);
}
