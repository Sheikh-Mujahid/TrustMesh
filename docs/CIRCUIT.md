# ⚡ Trust Mesh Hardware Circuit & Wiring Specification

This document details the exact hardware wiring, pin assignments, electrical ratings, and communication protocols for the **Trust Mesh ESP32 Smart Tracking Node**.

---

## 1. Component Overview & Bill of Materials

| Item | Component | Specification | Function in System |
|---|---|---|---|
| 1 | **Microcontroller** | ESP32 DevKit V1 (30-pin) | Dual-core 240MHz, 2.4GHz Wi-Fi, BLE |
| 2 | **Temperature & Humidity** | DHT22 (AM2302) | -40°C to 80°C (±0.5°C), 0-100% RH (±2%) |
| 3 | **GPS Receiver** | u-blox NEO-6M | High-sensitivity GNSS, NMEA 0183 9600 baud |
| 4 | **Display** | SSD1306 0.96" OLED | 128×64 pixels, monochrome, I2C 0x3C |
| 5 | **Status Indicator** | 5mm Green LED | Device status, Wi-Fi link, transmission pulse |
| 6 | **Audible Alarm** | Active 5V Buzzer | Temperature excursion alert / power alert |
| 7 | **Resistor 1** | 10kΩ 1/4W | Pull-up resistor for DHT22 Data line |
| 8 | **Resistor 2** | 220Ω 1/4W | Current limiting resistor for status LED |
| 9 | **Transistor** | 2N2222 NPN | Buzzer driver circuit |
| 10 | **Power Supply** | Micro-USB or 3.7V Li-Po (18650) | 5V 1A / 3.7V with TP4056 charge board |

---

## 2. Complete Wiring Table

| Component Pin | ESP32 Pin | ESP32 Function | Voltage / Signal | Notes |
|---|---|---|---|---|
| **DHT22 Pin 1 (VCC)** | 3V3 | Power | 3.3V DC | Connect to 3.3V rail |
| **DHT22 Pin 2 (DATA)** | **GPIO 4** | GPIO4 (ADC2_CH0) | 1-Wire Digital | 10kΩ pull-up to 3.3V required |
| **DHT22 Pin 3 (NC)** | — | Unused | — | No connection |
| **DHT22 Pin 4 (GND)** | GND | Ground | 0V | Connect to common GND |
| **NEO-6M VCC** | 3V3 (or VIN 5V) | Power | 3.3V / 5.0V | 3.3V supported on module |
| **NEO-6M GND** | GND | Ground | 0V | Connect to common GND |
| **NEO-6M TX** | **GPIO 16** | RX2 (UART2) | UART 9600 baud | GPS TX connects to ESP RX2 |
| **NEO-6M RX** | **GPIO 17** | TX2 (UART2) | UART 9600 baud | GPS RX connects to ESP TX2 |
| **SSD1306 VCC** | 3V3 | Power | 3.3V DC | Connect to 3.3V rail |
| **SSD1306 GND** | GND | Ground | 0V | Connect to common GND |
| **SSD1306 SCL** | **GPIO 22** | SCL (I2C) | Clock | I2C Address 0x3C |
| **SSD1306 SDA** | **GPIO 21** | SDA (I2C) | Data | I2C Address 0x3C |
| **LED Anode (+)** | **GPIO 2** | GPIO2 | Digital OUT | In series with 220Ω resistor |
| **LED Cathode (-)** | GND | Ground | 0V | Connect to common GND |
| **Buzzer (+)** | VIN (5V) | Power | 5V DC | Positive terminal to 5V |
| **Buzzer (-)** | Collector | Switch | NPN Collector | 2N2222 Collector |
| **2N2222 Base** | **GPIO 25** | GPIO25 | Digital OUT | Via 1kΩ resistor to Base |
| **2N2222 Emitter** | GND | Ground | 0V | Emitter to common GND |

---

## 3. Circuit Schematic Diagram (ASCII)

```
                       ESP32 DevKit V1
                 ┌───────────────────────────┐
                 │                           │
  3.3V ──────────┤ 3V3                   VIN ├────────── +5V (USB / Battery)
                 │                           │            │
  GND ───────────┤ GND                   GND ├──────┐     │
                 │                           │      │     │
  DHT22 DATA ────┤ GPIO 4                    │      │     │
  (10k to 3.3V)  │                           │      │     │
                 │                           │      │     │
  GPS TX ────────┤ GPIO 16 (RX2)             │      │     │
  GPS RX ────────┤ GPIO 17 (TX2)             │      │     │
                 │                           │      │     │
  OLED SDA ──────┤ GPIO 21 (SDA)             │      │     │
  OLED SCL ──────┤ GPIO 22 (SCL)             │      │     │
                 │                           │      │     │
  LED (+) ───────┤ GPIO 2                    │      │     │
  (220Ω to GND)  │                           │      │     │
                 │                           │      │     │
  Buzzer Driver ─┤ GPIO 25                   │      │     │
  (1kΩ to Base)  │                           │      │     │
                 └───────────────────────────┘      │     │
                                                    │     │
                                    Active Buzzer  │     │
                                   ┌──────────────┴┐    │
                                   │  (+)        (-) │   │
                                   └───┬───────────┬─┘   │
                                       │           │     │
                                      +5V          │     │
                                                   ▼     │
                                            Collector    │
                              GPIO 25 ──[1kΩ]───┤ NPN    │
                                            Emitter      │
                                                   │     │
                                                  GND ───┘
```

---

## 4. Arduino IDE Setup & Flashing Instructions

1. **Install Arduino IDE 2.x**
2. **Add ESP32 Board Package**:
   * Open `Preferences` → Additional Board Manager URLs:
   * `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
3. **Install Required Libraries**:
   * `DHT sensor library` by Adafruit
   * `Adafruit Unified Sensor` by Adafruit
   * `TinyGPSPlus` by Mikal Hart
   * `Adafruit SSD1306` & `Adafruit GFX Library`
   * `ArduinoJson` (v6 or v7)
4. **Configure Wi-Fi & Server IP**:
   * Open `esp32/agriledger_firmware.ino`
   * Edit `WIFI_SSID`, `WIFI_PASS`, and `API_HOST` with your local network IP (e.g. `192.168.1.100`).
5. **Select Board**: `ESP32 Dev Module` → Port → Click **Upload**.
