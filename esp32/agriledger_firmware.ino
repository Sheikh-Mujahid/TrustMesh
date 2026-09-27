/*
 * AgriLedger ESP32 Firmware v1.0
 * ===============================
 * Hardware:
 *   - ESP32 DevKit v1
 *   - DHT22 Temperature + Humidity Sensor
 *   - NEO-6M GPS Module (Serial2)
 *   - SSD1306 OLED 128x64 (I2C)
 *   - Status LED (Green)
 *   - Buzzer (Active)
 *
 * WIRING SUMMARY
 * ==========================================
 * Component       ESP32 Pin   Power   GND   Protocol
 * -------------------------------------------------------
 * DHT22 Data      GPIO 4      3.3V    GND   1-Wire Digital
 * GPS TX  → ESP32 GPIO 16 (RX2) 3.3V  GND   UART Serial2
 * GPS RX  ← ESP32 GPIO 17 (TX2) 3.3V  GND   UART Serial2
 * OLED SDA        GPIO 21     3.3V    GND   I2C
 * OLED SCL        GPIO 22     3.3V    GND   I2C
 * LED (+)         GPIO 2      3.3V    GND   Digital Out
 * Buzzer (+)      GPIO 25     3.3V    GND   Digital Out
 * ==========================================
 * All GNDs connected to ESP32 GND.
 * GPS VCC → 3.3V (NEO-6M supports 3.3V directly).
 */

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <DHT.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <TinyGPS++.h>
#include <HardwareSerial.h>
#include <time.h>

// ──────────────────────────────────────────────────────────────────────────
// PIN DEFINITIONS
// ──────────────────────────────────────────────────────────────────────────
#define DHT_PIN       4
#define DHT_TYPE      DHT22
#define LED_PIN       2
#define BUZZER_PIN    25
#define GPS_RX_PIN    16      // ESP32 RX ← GPS TX
#define GPS_TX_PIN    17      // ESP32 TX → GPS RX
#define GPS_BAUD      9600

// OLED
#define OLED_SDA      21
#define OLED_SCL      22
#define SCREEN_WIDTH  128
#define SCREEN_HEIGHT 64
#define OLED_RESET    -1
#define OLED_ADDR     0x3C

// ──────────────────────────────────────────────────────────────────────────
// CONFIGURATION  ← CHANGE THESE
// ──────────────────────────────────────────────────────────────────────────
const char* WIFI_SSID       = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD   = "YOUR_WIFI_PASSWORD";
const char* SERVER_URL      = "http://192.168.1.100:8000/api/sensor-data";  // FastAPI host
const char* DEVICE_ID       = "DEVICE-001";
const char* PRODUCT_ID      = "AGRI-001";
const int   SEND_INTERVAL_S = 10;   // seconds between data sends

// NTP
const char* NTP_SERVER      = "pool.ntp.org";
const long  GMT_OFFSET_S    = 19800;   // IST = UTC+5:30
const int   DST_OFFSET_S    = 0;

// ──────────────────────────────────────────────────────────────────────────
// OBJECTS
// ──────────────────────────────────────────────────────────────────────────
DHT             dht(DHT_PIN, DHT_TYPE);
Adafruit_SSD1306 oled(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);
TinyGPSPlus     gps;
HardwareSerial  GPSSerial(2);   // UART2

// ──────────────────────────────────────────────────────────────────────────
// GLOBALS
// ──────────────────────────────────────────────────────────────────────────
float    g_temp     = 0.0f;
float    g_humidity = 0.0f;
double   g_lat      = 20.0059;   // default (Nashik) used if GPS cold
double   g_lon      = 73.7897;
bool     g_gpsFixed = false;
bool     g_wifiOk   = false;
bool     g_apiOk    = false;
uint32_t g_lastSend = 0;
int      g_sendCount = 0;

// ──────────────────────────────────────────────────────────────────────────
// OLED HELPERS
// ──────────────────────────────────────────────────────────────────────────
void oledClear() {
  oled.clearDisplay();
  oled.setCursor(0, 0);
  oled.setTextSize(1);
  oled.setTextColor(SSD1306_WHITE);
}

void oledLine(int y, const String& txt, int size = 1) {
  oled.setTextSize(size);
  oled.setCursor(0, y);
  oled.print(txt);
}

void showBoot() {
  oledClear();
  oled.setTextSize(2);
  oled.setCursor(10, 5);
  oled.println("AgriLedger");
  oled.setTextSize(1);
  oled.setCursor(20, 30);
  oled.println("IoT v1.0");
  oled.setCursor(8, 45);
  oled.println("Connecting Wi-Fi...");
  oled.display();
}

void showStatus() {
  oledClear();
  // Row 0
  oledLine(0,  "DEVICE: " + String(DEVICE_ID));
  oledLine(10, "WiFi: " + String(g_wifiOk ? "CONNECTED" : "FAIL"));
  // Temp/Humidity
  oledLine(20, "T:" + String(g_temp, 1) + "C  H:" + String(g_humidity, 1) + "%");
  // GPS
  if (g_gpsFixed) {
    oledLine(30, "GPS:" + String(g_lat, 4) + "," + String(g_lon, 4));
  } else {
    oledLine(30, "GPS: Acquiring...");
  }
  // API status
  oledLine(40, "API: " + String(g_apiOk ? "OK" : "FAIL"));
  oledLine(50, "Sent:" + String(g_sendCount) + "  Pkt");
  oled.display();
}

// ──────────────────────────────────────────────────────────────────────────
// LED / BUZZER
// ──────────────────────────────────────────────────────────────────────────
void ledOn()  { digitalWrite(LED_PIN, HIGH); }
void ledOff() { digitalWrite(LED_PIN, LOW);  }

void beep(int ms = 100) {
  digitalWrite(BUZZER_PIN, HIGH);
  delay(ms);
  digitalWrite(BUZZER_PIN, LOW);
}

void beepSuccess() { beep(80); delay(60); beep(80); }
void beepError()   { beep(400); }

// ──────────────────────────────────────────────────────────────────────────
// WI-FI
// ──────────────────────────────────────────────────────────────────────────
void connectWiFi() {
  Serial.print("[WiFi] Connecting to ");
  Serial.println(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int tries = 0;
  while (WiFi.status() != WL_CONNECTED && tries < 30) {
    delay(500);
    Serial.print(".");
    tries++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    g_wifiOk = true;
    Serial.println("\n[WiFi] Connected: " + WiFi.localIP().toString());
    beepSuccess();
    configTime(GMT_OFFSET_S, DST_OFFSET_S, NTP_SERVER);
  } else {
    g_wifiOk = false;
    Serial.println("\n[WiFi] FAILED — running offline");
    beepError();
  }
}

// ──────────────────────────────────────────────────────────────────────────
// TIMESTAMP
// ──────────────────────────────────────────────────────────────────────────
String getTimestamp() {
  struct tm ti;
  if (getLocalTime(&ti)) {
    char buf[30];
    strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", &ti);
    return String(buf);
  }
  // Fallback: uptime seconds
  return "1970-01-01T00:00:" + String(millis() / 1000) + "Z";
}

// ──────────────────────────────────────────────────────────────────────────
// SENSORS
// ──────────────────────────────────────────────────────────────────────────
bool readDHT() {
  float h = dht.readHumidity();
  float t = dht.readTemperature();

  if (isnan(h) || isnan(t)) {
    Serial.println("[DHT22] Read failed");
    return false;
  }
  if (t < -40 || t > 85 || h < 0 || h > 100) {
    Serial.println("[DHT22] Out-of-range reading");
    return false;
  }
  g_temp     = t;
  g_humidity = h;
  return true;
}

void readGPS() {
  unsigned long start = millis();
  while (millis() - start < 500) {           // collect 500ms of NMEA
    while (GPSSerial.available()) {
      char c = GPSSerial.read();
      gps.encode(c);
    }
  }
  if (gps.location.isValid() && gps.location.age() < 2000) {
    g_lat    = gps.location.lat();
    g_lon    = gps.location.lng();
    g_gpsFixed = true;
  } else {
    g_gpsFixed = false;
    // Keep last known or default
  }
}

// ──────────────────────────────────────────────────────────────────────────
// HTTP POST
// ──────────────────────────────────────────────────────────────────────────
bool sendToServer() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[HTTP] No Wi-Fi");
    return false;
  }

  StaticJsonDocument<256> doc;
  doc["device_id"]   = DEVICE_ID;
  doc["product_id"]  = PRODUCT_ID;
  doc["temperature"] = g_temp;
  doc["humidity"]    = g_humidity;
  doc["latitude"]    = g_lat;
  doc["longitude"]   = g_lon;
  doc["timestamp"]   = getTimestamp();
  doc["is_simulated"] = false;

  String body;
  serializeJson(doc, body);

  HTTPClient http;
  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(8000);

  int code = http.POST(body);
  String resp = http.getString();
  http.end();

  Serial.printf("[HTTP] POST → %d | %s\n", code, resp.c_str());

  if (code == 200) {
    g_sendCount++;
    g_apiOk = true;
    return true;
  } else {
    g_apiOk = false;
    Serial.println("[HTTP] Server error or timeout");
    return false;
  }
}

// ──────────────────────────────────────────────────────────────────────────
// SETUP
// ──────────────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN,    OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  ledOff();

  // OLED
  Wire.begin(OLED_SDA, OLED_SCL);
  if (!oled.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
    Serial.println("[OLED] INIT FAILED");
  }
  oled.clearDisplay();
  oled.display();
  showBoot();

  // DHT
  dht.begin();
  delay(2000);   // DHT22 needs 2s warmup

  // GPS on UART2
  GPSSerial.begin(GPS_BAUD, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);

  // Wi-Fi
  connectWiFi();

  ledOn();
  beepSuccess();
  Serial.println("[BOOT] AgriLedger device ready");
}

// ──────────────────────────────────────────────────────────────────────────
// LOOP
// ──────────────────────────────────────────────────────────────────────────
void loop() {
  // Reconnect Wi-Fi if dropped
  if (WiFi.status() != WL_CONNECTED) {
    g_wifiOk = false;
    connectWiFi();
  }

  readGPS();

  uint32_t now = millis() / 1000;
  if (now - g_lastSend >= SEND_INTERVAL_S) {
    g_lastSend = now;

    ledOn();
    bool dhtOk  = readDHT();
    bool sentOk = false;

    if (dhtOk) {
      sentOk = sendToServer();
      if (sentOk) {
        beepSuccess();
      } else {
        beepError();
      }
    } else {
      beepError();
    }

    ledOff();
  }

  showStatus();
  delay(100);
}
