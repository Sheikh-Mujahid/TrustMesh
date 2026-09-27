# 📡 Trust Mesh REST API Reference

The Trust Mesh backend is built with FastAPI and runs by default at `http://localhost:8000`.

Interactive Swagger UI is available at `http://localhost:8000/docs` and ReDoc at `http://localhost:8000/redoc`.

---

## Base URLs
* **Local Backend**: `http://localhost:8000`
* **CORS**: Enabled for all origins `*`

---

## 1. System & Diagnostics

### `GET /api/health`
Health check endpoint returning system status, active database engine, and simulation state.
```json
{
  "status": "ok",
  "version": "1.2.0",
  "sim_active": false,
  "db_engine": "sqlite",
  "timestamp": "2026-09-27T08:19:51.470602+00:00"
}
```

### `GET /api/dashboard/stats`
Summary statistics for dashboard widgets.
```json
{
  "products": 2,
  "sensor_readings": 4,
  "supply_events": 3,
  "blockchain_txns": 6,
  "latest_reading": { ... },
  "simulation_mode": false,
  "db_engine": "sqlite"
}
```

---

## 2. Product Management

### `POST /api/register-product`
Registers a new agricultural batch and initializes its genesis block on the blockchain.
**Request Body**:
```json
{
  "product_id": "AGRI-001",
  "farmer_user_id": "USER-FARMER-001",
  "device_id": "DEVICE-001",
  "name": "Organic Tomatoes",
  "category": "Vegetable",
  "quantity": 500.0,
  "unit": "kg",
  "harvest_date": "2026-09-20",
  "origin_location": "Nashik, Maharashtra"
}
```
**Response**:
```json
{
  "success": true,
  "product_id": "AGRI-001",
  "qr_url": "http://localhost:8000/verify.html?id=AGRI-001",
  "qr_base64": "iVBORw0KGgo...",
  "message": "Product AGRI-001 registered and genesis block created."
}
```

### `GET /api/product/{product_id}`
Fetch full product metadata and owner info.

---

## 3. IoT Sensor Telemetry

### `POST /api/sensor-data`
Endpoint called by ESP32 microcontrollers to upload sensor readings.
**Request Body**:
```json
{
  "device_id": "DEVICE-001",
  "product_id": "AGRI-001",
  "temperature": 24.5,
  "humidity": 68.2,
  "latitude": 20.0059,
  "longitude": 73.7897,
  "timestamp": "2026-09-27T10:00:00Z",
  "is_simulated": false
}
```
**Response**:
```json
{
  "success": true,
  "data_hash": "d4e5f6a1b2c302030405060708090a1b2c3d4e5f60718293a4b5c6d7e8f90333",
  "message": "Sensor data recorded and hashed on blockchain."
}
```

### `GET /api/sensor-history/{product_id}?limit=50`
Returns recent sensor history ordered chronologically.

---

## 4. Supply Chain Journey

### `POST /api/supply-event`
Records an off-chain supply chain transit event and mines a new block on the blockchain.
**Valid Events**:
* `FARM_HARVESTED`
* `COLLECTION_CENTER_RECEIVED`
* `TRANSPORT_DISPATCHED`
* `WAREHOUSE_RECEIVED`
* `RETAILER_RECEIVED`
* `CONSUMER_DELIVERED`

**Request Body**:
```json
{
  "product_id": "AGRI-001",
  "user_id": "USER-WAREHOUSE-001",
  "event_type": "WAREHOUSE_RECEIVED",
  "location": "Pune Cold Storage Unit 3",
  "latitude": 18.5204,
  "longitude": 73.8567,
  "notes": "Quality check passed, stored at 4°C"
}
```

---

## 5. Blockchain Verification & Tamper Detection

### `GET /api/blockchain/{product_id}`
Returns the entire block sequence for a product.

### `GET /api/verify/{product_id}`
Comprehensive verification report returning:
* Verification flag (`verified: true/false`)
* Product info
* Supply chain journey events
* Environmental sensor summary (min/max/avg temperature & humidity)
* Blockchain cryptographic audit

### `POST /api/tamper-test`
Simulates an attack modifying off-chain records and tests if blockchain detects hash mismatch.
**Request Body**:
```json
{
  "product_id": "AGRI-001",
  "block_index": 1,
  "field": "sensor_data_hash",
  "new_value": "deadbeefdeadbeefdeadbeefdeadbeef"
}
```
