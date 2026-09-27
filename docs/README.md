# 🌾 Trust Mesh — IoT + Blockchain Agricultural Supply Chain

> **SIH 2026 Student Innovation Project**
> ESP32 · DHT22 · GPS · FastAPI · MySQL · SHA-256 Blockchain · Web Dashboard · QR Verification

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  PHYSICAL LAYER                                                 │
│  ┌──────────┐  ┌───────┐  ┌──────────┐  ┌──────┐  ┌────────┐  │
│  │  DHT22   │  │NEO-6M │  │   OLED   │  │ LED  │  │ Buzzer │  │
│  │Temp/Hum  │  │  GPS  │  │SSD1306   │  │GPIO2 │  │ GPIO25 │  │
│  └────┬─────┘  └───┬───┘  └────┬─────┘  └──────┘  └────────┘  │
│       │            │            │                                │
│  ┌────▼────────────▼────────────▼──────────────────────────┐   │
│  │              ESP32 DevKit V1                             │   │
│  │  GPIO4(DHT) · GPIO16/17(UART2-GPS) · GPIO21/22(I2C)     │   │
│  │  Reads sensors every 10s → HTTP POST to FastAPI          │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│                           │ Wi-Fi 2.4GHz                       │
└───────────────────────────┼─────────────────────────────────────┘
                            │
                 ┌──────────▼──────────┐
                 │  FastAPI Backend     │
                 │  Python + Uvicorn   │
                 │  localhost:8000     │
                 └────────┬────────────┘
                          │
              ┌───────────┼────────────┐
              │           │            │
    ┌─────────▼──┐   ┌────▼─────┐  ┌──▼──────────────┐
    │  MySQL 8.0  │   │ Local    │  │  QR Code Gen     │
    │  agriledger │   │Blockchain│  │  /qr_codes/      │
    │  6 tables   │   │SHA-256   │  │  PIL + qrcode    │
    └─────────────┘   └──────────┘  └─────────────────┘
              │
    ┌─────────▼──────────────────────────────────────────┐
    │            Web Dashboard (HTML + JS)                │
    │  index · farmer · hardware · monitor · supply       │
    │  blockchain · verify · admin                        │
    │  localhost:5500 (Live Server / file://)             │
    └────────────────────────────────────────────────────┘
```

---

## Hardware Block Diagram

```
[USB Power 5V]
      │
 ┌────┴────────────────────────────────────────────────┐
 │              ESP32 DevKit V1                        │
 │                                                     │
 │  GPIO 4  ──────────────── DHT22 Data               │
 │                           (10kΩ pull-up to 3.3V)   │
 │                                                     │
 │  GPIO 16 (RX2) ◄────────── NEO-6M GPS TX           │
 │  GPIO 17 (TX2) ─────────── NEO-6M GPS RX           │
 │                                                     │
 │  GPIO 21 (SDA) ─────────── SSD1306 OLED SDA        │
 │  GPIO 22 (SCL) ─────────── SSD1306 OLED SCL        │
 │                                                     │
 │  GPIO 2  ──── 220Ω ──────── LED (+)                │
 │  GPIO 25 ──── NPN ──────── Buzzer (+)              │
 │                                                     │
 │  3.3V  ─────────────────── DHT22 VCC               │
 │  3.3V  ─────────────────── GPS VCC                 │
 │  3.3V  ─────────────────── OLED VCC                │
 │  GND   ─────────────────── All GNDs                │
 └─────────────────────────────────────────────────────┘
```

---

## Wiring Specification

| Component | ESP32 Pin | Power | GND | Protocol | Notes |
|-----------|-----------|-------|-----|----------|-------|
| DHT22 Data | GPIO 4 | 3.3V | GND | 1-Wire Digital | 10kΩ pull-up resistor |
| NEO-6M TX → ESP RX | GPIO 16 (RX2) | 3.3V | GND | UART 9600 | GPS TX → ESP GPIO 16 |
| NEO-6M RX ← ESP TX | GPIO 17 (TX2) | 3.3V | GND | UART 9600 | GPS RX ← ESP GPIO 17 |
| OLED SDA | GPIO 21 | 3.3V | GND | I²C 0x3C | Standard I2C bus |
| OLED SCL | GPIO 22 | 3.3V | GND | I²C 0x3C | Standard I2C bus |
| LED (+) | GPIO 2 | via 220Ω | GND | Digital OUT | 220Ω series resistor |
| Buzzer | GPIO 25 | via NPN | GND | Digital OUT | 2N2222 NPN transistor |

---

## Project Structure

```
agriledger/
├── frontend/
│   ├── index.html          # Landing page
│   ├── farmer.html         # Farmer product registration
│   ├── hardware.html       # ESP32 device dashboard + wiring
│   ├── monitor.html        # Live sensor graphs
│   ├── supply.html         # Supply chain timeline
│   ├── blockchain.html     # Blockchain explorer
│   ├── verify.html         # QR product verification
│   ├── admin.html          # Admin + SIH demo + tamper test
│   ├── css/main.css        # Complete design system
│   └── js/
│       ├── api.js          # API client module
│       └── app.js          # Charts, polling, demo mode
│
├── backend/
│   ├── main.py             # FastAPI application
│   └── requirements.txt    # Python dependencies
│
├── esp32/
│   └── agriledger_firmware.ino  # Arduino C++ firmware
│
├── blockchain/
│   └── agri_chain.py      # SHA-256 blockchain implementation
│
├── database/
│   └── agriledger.sql     # MySQL schema + seed data
│
└── docs/
    └── README.md           # This file
```

---

## Quick Start (Windows)

### Step 1 — Install Dependencies

```powershell
# Python 3.10+
cd agriledger/backend
pip install -r requirements.txt

# MySQL 8.0 must be running
```

### Step 2 — Create MySQL Database

```powershell
mysql -u root -p < ..\database\agriledger.sql
```

### Step 3 — Configure Backend

Edit `backend/main.py` — update `DB_CONFIG` if needed:
```python
DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "YOUR_MYSQL_PASSWORD",
    "database": "agriledger",
}
```

Or use environment variables:
```powershell
$env:DB_PASSWORD = "yourpassword"
```

### Step 4 — Start FastAPI Backend

```powershell
cd agriledger/backend
python main.py
# OR
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Visit `http://localhost:8000/docs` for Swagger UI.

### Step 5 — Start Frontend

**Option A — VS Code Live Server:**
Right-click `frontend/index.html` → Open with Live Server

**Option B — Python HTTP Server:**
```powershell
cd agriledger/frontend
python -m http.server 5500
```

Open `http://localhost:5500`

### Step 6 — Flash ESP32 (Physical Hardware)

1. Open Arduino IDE 2.x
2. Add ESP32 board: `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
3. Install libraries via Library Manager:
   - `ArduinoJson` by Benoit Blanchon (v6.x)
   - `DHT sensor library` by Adafruit
   - `Adafruit GFX Library`
   - `Adafruit SSD1306`
   - `TinyGPS++` by Mikal Hart
4. Edit `esp32/agriledger_firmware.ino`:
   ```cpp
   const char* WIFI_SSID     = "YOUR_WIFI";
   const char* WIFI_PASSWORD = "YOUR_PASSWORD";
   const char* SERVER_URL    = "http://YOUR_PC_IP:8000/api/sensor-data";
   ```
5. Select board: **ESP32 Dev Module**, port: your COM port
6. Upload

---

## Testing

### Test Sensor Data (PowerShell)

```powershell
$body = @{
  device_id   = "DEVICE-001"
  product_id  = "AGRI-001"
  temperature = 25.4
  humidity    = 67.0
  latitude    = 20.0059
  longitude   = 73.7897
  timestamp   = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
  is_simulated = $false
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/sensor-data" -Method POST -Body $body -ContentType "application/json"
```

### Test Blockchain

```powershell
# Register product
Invoke-RestMethod -Uri "http://localhost:8000/api/register-product" -Method POST -Body '{"product_id":"AGRI-001","farmer_user_id":"USER-FARMER-001","name":"Organic Tomatoes","category":"Vegetable","quantity":500,"unit":"kg","harvest_date":"2026-09-20","origin_location":"Nashik, Maharashtra"}' -ContentType "application/json"

# View blockchain
Invoke-RestMethod -Uri "http://localhost:8000/api/blockchain/AGRI-001"

# Verify product
Invoke-RestMethod -Uri "http://localhost:8000/api/verify/AGRI-001"
```

### Test QR Verification

1. Open `http://localhost:5500/verify.html?id=AGRI-001`
2. Should show **PRODUCT VERIFIED ✓**

### Run Simulation Mode (No Hardware)

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/simulate/start" -Method POST
```

Or click **▶ Start Simulation** on the Admin page.

---

## SIH Demonstration Flow

Follow this sequence on the Admin dashboard (`/admin.html#demo`):

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Connect ESP32 | OLED shows IP, DEVICE-001 connected |
| 2 | Show Device Connected | Hardware dashboard shows CONNECTED ✓ |
| 3 | Register AGRI-001 | Farmer dashboard → product created |
| 4 | Generate QR | QR code displayed, scan opens /verify |
| 5 | Start Sensor Monitoring | Live sensor chart activated |
| 6 | Send Sensor Data | ESP32 POSTs T=25.4°C, H=67% |
| 7 | Display Live Values | Monitor page shows real-time graph |
| 8 | Record Supply Event | FARM_HARVESTED added to chain |
| 9 | Generate Block Hash | Blockchain block #1 mined with SHA-256 |
| 10 | Verify Product | /verify/AGRI-001 → ✅ PRODUCT VERIFIED |
| 11 | Run Tamper Test | Admin mutates block in memory |
| 12 | Show DATA TAMPERED | Chain shows ⚠️ TAMPERED alert |

---

## Blockchain Architecture

```
OFF-CHAIN (MySQL)                  ON-CHAIN (Local SHA-256 Ledger)
─────────────────                  ───────────────────────────────
Product info          ──Hash──►   block_index
Farmer details                    event_type
Sensor history                    sensor_data_hash  (SHA-256 of off-chain payload)
Supply events                     previous_hash
User data                         current_hash
                                  nonce
                                  timestamp

Each block: SHA-256(index + product_id + event_type + payload_hash + prev_hash + timestamp + nonce)
Difficulty:  "00..." (2 leading zeros proof-of-work)
```

**Production Integration:**
Replace `BlockchainManager` with Hyperledger Fabric SDK or IOTA client.
The off-chain/on-chain split is already in place.

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/register-product` | Register product + genesis block + QR |
| POST | `/api/sensor-data` | Ingest sensor reading from ESP32 |
| POST | `/api/supply-event` | Record supply chain event |
| GET  | `/api/product/{id}` | Product details with farmer info |
| GET  | `/api/sensor-history/{id}` | Historical sensor readings |
| GET  | `/api/blockchain/{id}` | All blocks for product |
| GET  | `/api/verify/{id}` | Full verification report |
| POST | `/api/tamper-test` | Simulate and detect tampering |
| GET  | `/api/dashboard/stats` | System-wide statistics |
| POST | `/api/simulate/start` | Start hardware simulation |
| POST | `/api/simulate/stop` | Stop hardware simulation |
| GET  | `/api/qr/{product_id}` | QR code PNG image |

Full Swagger: `http://localhost:8000/docs`

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Microcontroller | ESP32 DevKit V1 |
| Temperature/Humidity | DHT22 |
| Location | NEO-6M GPS (UART) |
| Display | SSD1306 OLED 128×64 (I²C) |
| Backend | Python FastAPI + Uvicorn |
| Database | MySQL 8.0 (off-chain) |
| Blockchain | Local SHA-256 PoW (on-chain) |
| QR Generation | Python `qrcode[pil]` |
| Frontend | HTML5 + Vanilla CSS + JavaScript |
| Charts | Chart.js 4.x |
| Fonts | Inter + JetBrains Mono |

---

## Notes

- This is a **local prototype**. The blockchain is not a decentralised network.
- Data clearly labelled **SIM** when generated by simulation mode.
- The system is architected for permissioned DLT (Hyperledger Fabric / IOTA) integration.
- All SHA-256 hashes are computed server-side using Python `hashlib`.
- No private keys or wallets are used in this prototype.
