"""
AgriLedger FastAPI Backend v1.2
================================
IoT + Blockchain Supply-Chain Traceability for Agriculture
Supports both MySQL and auto-fallback SQLite for 100% plug-and-play reliability.
Serves both REST API and Frontend static UI directly on port 8000.
"""

import asyncio
import base64
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from io import BytesIO
import os
from pathlib import Path
import random
import sys
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import qrcode

# Add blockchain and backend module to path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR.parent / "blockchain"))
sys.path.insert(0, str(BASE_DIR))

from agri_chain import blockchain_manager, hash_payload
from database import get_db, db_exec, init_database, get_active_engine

# ---------------------------------------------------------------------------
# Directories & Configurations
# ---------------------------------------------------------------------------
QR_DIR = BASE_DIR / "qr_codes"
QR_DIR.mkdir(exist_ok=True)

FRONTEND_DIR = BASE_DIR.parent / "frontend"
FRONTEND_BASE_URL = os.getenv("FRONTEND_URL", "http://localhost:8000")

# Simulation state
_simulation_active = False
_simulation_task: Optional[asyncio.Task] = None


# ---------------------------------------------------------------------------
# Pre-seed Blockchain from DB
# ---------------------------------------------------------------------------
def _init_seed_blockchain():
    """Ensures demo products have genesis and initial event blocks in the blockchain."""
    try:
        conn = get_db()
        products = db_exec(conn, "SELECT product_id, name, origin_location, harvest_date FROM products", fetch="all")
        for prod in (products or []):
            pid = prod["product_id"]
            chain = blockchain_manager.get_or_create_chain(pid)
            if len(chain.chain) <= 1:
                # Add registration block
                blockchain_manager.add_event(
                    product_id=pid,
                    event_type="PRODUCT_REGISTERED",
                    payload=prod,
                )
                # Add existing supply chain events from DB
                events = db_exec(conn, "SELECT * FROM supply_chain_events WHERE product_id = %s ORDER BY id ASC", (pid,), fetch="all")
                for evt in (events or []):
                    blockchain_manager.add_event(
                        product_id=pid,
                        event_type=evt["event_type"],
                        payload=evt,
                    )
        conn.close()
    except Exception as e:
        print(f"[Blockchain] Pre-seed warning: {e}")


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("[Startup] Initializing Trust Mesh Database & Blockchain...")
    init_database()
    _init_seed_blockchain()
    print(f"[Startup] Active Database Engine: {get_active_engine().upper()}")
    print(f"[Startup] Trust Mesh ready at {FRONTEND_BASE_URL}")
    yield
    # Shutdown
    global _simulation_active, _simulation_task
    _simulation_active = False
    if _simulation_task and not _simulation_task.done():
        _simulation_task.cancel()
    print("[Shutdown] Simulation stopped and server cleaned up.")


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Trust Mesh API",
    version="1.2.0",
    description="Trust Mesh: IoT + Blockchain Supply-Chain Traceability for Agriculture (SIH 2026)",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Pydantic Models (Pydantic v2 compatible)
# ---------------------------------------------------------------------------
class SensorPayload(BaseModel):
    device_id:    str
    product_id:   str
    temperature:  float
    humidity:     float
    latitude:     float
    longitude:    float
    timestamp:    Optional[str] = None
    is_simulated: bool = False


class ProductRegister(BaseModel):
    product_id:      str
    farmer_user_id:  str
    device_id:       Optional[str] = None
    name:            str
    category:        Optional[str] = None
    quantity:        Optional[float] = None
    unit:            Optional[str] = "kg"
    harvest_date:    Optional[str] = None
    origin_location: Optional[str] = None


class SupplyEvent(BaseModel):
    product_id:  str
    user_id:     str
    event_type:  str
    location:    Optional[str] = None
    latitude:    Optional[float] = None
    longitude:   Optional[float] = None
    notes:       Optional[str] = None


class TamperTest(BaseModel):
    product_id:  str
    block_index: int
    field:       str = "sensor_data_hash"
    new_value:   str = "aaaa1111deadbeef" * 4


# ---------------------------------------------------------------------------
# QR Code Helper
# ---------------------------------------------------------------------------
def generate_qr(product_id: str) -> str:
    url = f"{FRONTEND_BASE_URL}/verify.html?id={product_id}"
    img = qrcode.make(url)
    buf = BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    img.save(QR_DIR / f"{product_id}.png")
    return b64


# ---------------------------------------------------------------------------
# Core: Store Sensor Data (Sync & Async Safe)
# ---------------------------------------------------------------------------
def store_sensor_data_sync(payload: SensorPayload) -> str:
    ts = payload.timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    data_hash = hash_payload(payload.model_dump())
    conn = get_db()
    try:
        db_exec(conn,
            """INSERT INTO sensor_data
               (device_id, product_id, temperature, humidity, latitude, longitude,
                data_hash, is_simulated, sensor_ts)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (payload.device_id, payload.product_id, payload.temperature,
             payload.humidity, payload.latitude, payload.longitude,
             data_hash, 1 if payload.is_simulated else 0, ts),
        )
        conn.commit()

        # Record on blockchain
        blockchain_manager.add_event(
            product_id=payload.product_id,
            event_type="SENSOR_DATA",
            payload=payload.model_dump(),
            timestamp=ts,
        )

        # Update device last_seen
        try:
            db_exec(conn,
                "UPDATE devices SET last_seen=%s WHERE device_id=%s",
                (datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), payload.device_id),
            )
            conn.commit()
        except Exception:
            pass
    finally:
        conn.close()
    return data_hash


# ---------------------------------------------------------------------------
# Simulation Loop (Async)
# ---------------------------------------------------------------------------
async def _run_simulation():
    global _simulation_active
    print("[SIM] IoT Simulation engine started.")
    while _simulation_active:
        conn = get_db()
        try:
            products = db_exec(conn, "SELECT product_id FROM products", fetch="all") or [{"product_id": "AGRI-001"}]
        except Exception:
            products = [{"product_id": "AGRI-001"}]
        finally:
            conn.close()

        loop = asyncio.get_running_loop()
        for p in products:
            if not _simulation_active:
                break
            pid = p["product_id"] if isinstance(p, dict) else p[0]
            payload = SensorPayload(
                device_id="DEVICE-SIM-001",
                product_id=pid,
                temperature=round(24.0 + random.uniform(-2.5, 4.0), 2),
                humidity=round(65.0 + random.uniform(-8.0, 8.0), 2),
                latitude=round(20.0059 + random.uniform(-0.002, 0.002), 6),
                longitude=round(73.7897 + random.uniform(-0.002, 0.002), 6),
                timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                is_simulated=True,
            )
            try:
                await loop.run_in_executor(None, store_sensor_data_sync, payload)
            except Exception as e:
                print(f"[SIM] Error recording reading for {pid}: {e}")

        await asyncio.sleep(5)


# ---------------------------------------------------------------------------
# REST API Endpoints
# ---------------------------------------------------------------------------

# ---- Register Product -------------------------------------------------------
@app.post("/api/register-product")
async def register_product(data: ProductRegister):
    conn = get_db()
    try:
        existing = db_exec(conn,
            "SELECT product_id FROM products WHERE product_id=%s",
            (data.product_id,), fetch="one")
        if existing:
            raise HTTPException(status_code=409, detail="Product already registered")

        db_exec(conn,
            """INSERT INTO products
               (product_id, device_id, farmer_user_id, name, category, quantity, unit,
                harvest_date, origin_location, status)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'registered')""",
            (data.product_id, data.device_id, data.farmer_user_id, data.name,
             data.category, data.quantity, data.unit,
             data.harvest_date, data.origin_location),
        )
        conn.commit()

        # Genesis + registration block on blockchain
        blockchain_manager.get_or_create_chain(data.product_id)
        blockchain_manager.add_event(
            product_id=data.product_id,
            event_type="PRODUCT_REGISTERED",
            payload=data.model_dump(),
        )

        # QR Code
        qr_b64 = generate_qr(data.product_id)
        qr_url = f"{FRONTEND_BASE_URL}/verify.html?id={data.product_id}"
        db_exec(conn,
            "UPDATE products SET qr_code_url=%s WHERE product_id=%s",
            (qr_url, data.product_id),
        )
        conn.commit()

        return {
            "success":    True,
            "product_id": data.product_id,
            "qr_url":     qr_url,
            "qr_base64":  qr_b64,
            "message":    f"Product {data.product_id} registered and genesis block created.",
        }
    finally:
        conn.close()


# ---- Sensor Data ------------------------------------------------------------
@app.post("/api/sensor-data")
async def receive_sensor_data(payload: SensorPayload):
    if not (-90 <= payload.latitude <= 90) or not (-180 <= payload.longitude <= 180):
        raise HTTPException(status_code=422, detail="Invalid GPS coordinates")
    if not (-40 <= payload.temperature <= 85):
        raise HTTPException(status_code=422, detail="Temperature out of sensor range")
    if not (0 <= payload.humidity <= 100):
        raise HTTPException(status_code=422, detail="Humidity out of range")

    loop = asyncio.get_running_loop()
    data_hash = await loop.run_in_executor(None, store_sensor_data_sync, payload)
    return {
        "success":   True,
        "data_hash": data_hash,
        "message":   "Sensor data recorded and hashed on blockchain.",
    }


# ---- Supply Event -----------------------------------------------------------
VALID_EVENTS = [
    "FARM_HARVESTED", "COLLECTION_CENTER_RECEIVED",
    "TRANSPORT_DISPATCHED", "WAREHOUSE_RECEIVED",
    "RETAILER_RECEIVED", "CONSUMER_DELIVERED",
]
STATUS_MAP = {
    "FARM_HARVESTED":               "registered",
    "COLLECTION_CENTER_RECEIVED":   "in_transit",
    "TRANSPORT_DISPATCHED":         "in_transit",
    "WAREHOUSE_RECEIVED":           "warehouse",
    "RETAILER_RECEIVED":            "retail",
    "CONSUMER_DELIVERED":           "delivered",
}

@app.post("/api/supply-event")
async def record_supply_event(data: SupplyEvent):
    if data.event_type not in VALID_EVENTS:
        raise HTTPException(status_code=422, detail=f"event_type must be one of {VALID_EVENTS}")

    import uuid
    event_id   = f"EVT-{uuid.uuid4().hex[:12].upper()}"
    event_hash = hash_payload(data.model_dump())
    conn = get_db()
    try:
        db_exec(conn,
            """INSERT INTO supply_chain_events
               (event_id, product_id, user_id, event_type, location,
                latitude, longitude, notes, data_hash)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (event_id, data.product_id, data.user_id, data.event_type,
             data.location, data.latitude, data.longitude, data.notes, event_hash),
        )
        db_exec(conn,
            "UPDATE products SET status=%s WHERE product_id=%s",
            (STATUS_MAP.get(data.event_type, "in_transit"), data.product_id),
        )
        conn.commit()

        block = blockchain_manager.add_event(
            product_id=data.product_id,
            event_type=data.event_type,
            payload={**data.model_dump(), "event_id": event_id},
        )

        # Persist block to DB
        db_exec(conn,
            """INSERT INTO blockchain_transactions
               (block_index, product_id, event_id, event_type, sensor_data_hash,
                previous_hash, current_hash, nonce, block_timestamp)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (block.index, data.product_id, event_id, data.event_type,
             block.sensor_data_hash, block.previous_hash, block.current_hash,
             block.nonce, block.timestamp),
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "success":       True,
        "event_id":      event_id,
        "block_index":   block.index,
        "current_hash":  block.current_hash,
        "previous_hash": block.previous_hash,
        "message":       f"Event {data.event_type} recorded and mined into block #{block.index}.",
    }


# ---- Get Product ------------------------------------------------------------
@app.get("/api/product/{product_id}")
async def get_product(product_id: str):
    conn = get_db()
    try:
        product = db_exec(conn,
            """SELECT p.*, u.name as farmer_name, u.phone as farmer_phone,
                      u.location as farmer_location
               FROM products p
               JOIN users u ON p.farmer_user_id = u.user_id
               WHERE p.product_id = %s""",
            (product_id,), fetch="one")
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return product
    finally:
        conn.close()


# ---- Sensor History ---------------------------------------------------------
@app.get("/api/sensor-history/{product_id}")
async def sensor_history(product_id: str, limit: int = Query(50, ge=1, le=500)):
    conn = get_db()
    try:
        rows = db_exec(conn,
            """SELECT * FROM sensor_data
               WHERE product_id=%s ORDER BY received_at DESC LIMIT %s""",
            (product_id, limit), fetch="all")
        return {"product_id": product_id, "count": len(rows or []), "data": rows or []}
    finally:
        conn.close()


# ---- Blockchain Explorer ----------------------------------------------------
@app.get("/api/blockchain/{product_id}")
async def get_blockchain(product_id: str):
    chain = blockchain_manager.get_chain(product_id)
    if not chain:
        raise HTTPException(status_code=404, detail="No blockchain found for this product")
    return {"product_id": product_id, "blocks": chain, "total": len(chain)}


# ---- Verify Product ---------------------------------------------------------
@app.get("/api/verify/{product_id}")
async def verify_product(product_id: str):
    conn = get_db()
    try:
        product = db_exec(conn,
            """SELECT p.*, u.name as farmer_name, u.location as farmer_location,
                      u.phone as farmer_phone
               FROM products p
               JOIN users u ON p.farmer_user_id = u.user_id
               WHERE p.product_id = %s""",
            (product_id,), fetch="one")
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        events = db_exec(conn,
            """SELECT e.*, u.name as actor_name
               FROM supply_chain_events e
               JOIN users u ON e.user_id = u.user_id
               WHERE e.product_id=%s ORDER BY e.created_at ASC""",
            (product_id,), fetch="all")

        sensor_summary = db_exec(conn,
            """SELECT
                 MIN(temperature) as min_temp, MAX(temperature) as max_temp,
                 AVG(temperature) as avg_temp,
                 MIN(humidity)    as min_hum,  MAX(humidity)    as max_hum,
                 AVG(humidity)    as avg_hum,
                 COUNT(*)         as readings
               FROM sensor_data WHERE product_id=%s""",
            (product_id,), fetch="one")

        chain_report = blockchain_manager.verify_product(product_id)

        return {
            "verified":       chain_report.get("chain_valid", False),
            "product":        product,
            "supply_journey": events or [],
            "sensor_summary": sensor_summary or {},
            "blockchain":     chain_report,
        }
    finally:
        conn.close()


# ---- Tamper Test ------------------------------------------------------------
@app.post("/api/tamper-test")
async def tamper_test(data: TamperTest):
    result = blockchain_manager.tamper_test(
        data.product_id, data.block_index, data.field, data.new_value
    )
    return result


# ---- Dashboard Stats --------------------------------------------------------
@app.get("/api/dashboard/stats")
async def dashboard_stats():
    conn = get_db()
    try:
        prod_res = db_exec(conn, "SELECT COUNT(*) as c FROM products", fetch="one")
        read_res = db_exec(conn, "SELECT COUNT(*) as c FROM sensor_data", fetch="one")
        evt_res  = db_exec(conn, "SELECT COUNT(*) as c FROM supply_chain_events", fetch="one")
        blk_res  = db_exec(conn, "SELECT COUNT(*) as c FROM blockchain_transactions", fetch="one")
        recent   = db_exec(conn, "SELECT * FROM sensor_data ORDER BY received_at DESC LIMIT 1", fetch="one")
        
        products = prod_res["c"] if prod_res else 0
        readings = read_res["c"] if read_res else 0
        events   = evt_res["c"] if evt_res else 0
        blocks   = blk_res["c"] if blk_res else 0

        return {
            "products":        products,
            "sensor_readings": readings,
            "supply_events":   events,
            "blockchain_txns": blocks,
            "latest_reading":  recent,
            "simulation_mode": _simulation_active,
            "db_engine":       get_active_engine(),
        }
    finally:
        conn.close()


# ---- Devices ----------------------------------------------------------------
@app.get("/api/devices")
async def list_devices():
    conn = get_db()
    try:
        rows = db_exec(conn,
            """SELECT d.*, u.name as owner_name
               FROM devices d JOIN users u ON d.owner_user_id = u.user_id""",
            fetch="all")
        return {"devices": rows or []}
    finally:
        conn.close()


# ---- Simulation Control -----------------------------------------------------
@app.post("/api/simulate/start")
async def start_simulation():
    global _simulation_active, _simulation_task
    if _simulation_active:
        return {"status": "already_running", "message": "Simulation already active."}

    conn = get_db()
    try:
        exists = db_exec(conn,
            "SELECT device_id FROM devices WHERE device_id='DEVICE-SIM-001'",
            fetch="one")
        if not exists:
            db_exec(conn,
                """INSERT IGNORE INTO devices
                   (device_id, owner_user_id, firmware_ver, mac_address)
                   VALUES ('DEVICE-SIM-001','USER-FARMER-001','SIM-1.0','FF:FF:FF:FF:FF:00')""")
            conn.commit()
    finally:
        conn.close()

    _simulation_active = True
    _simulation_task = asyncio.create_task(_run_simulation())
    return {"status": "started", "message": "Simulation active. Sending live IoT data every 5s for AGRI-001."}


@app.post("/api/simulate/stop")
async def stop_simulation():
    global _simulation_active, _simulation_task
    _simulation_active = False
    if _simulation_task and not _simulation_task.done():
        _simulation_task.cancel()
    _simulation_task = None
    return {"status": "stopped", "message": "Simulation paused."}


# ---- QR Code Image ----------------------------------------------------------
@app.get("/api/qr/{product_id}")
async def get_qr(product_id: str):
    path = QR_DIR / f"{product_id}.png"
    if not path.exists():
        generate_qr(product_id)
    return FileResponse(path, media_type="image/png")


# ---- Health Check -----------------------------------------------------------
@app.get("/api/health")
async def health():
    return {
        "status":      "ok",
        "version":     "1.2.0",
        "sim_active":  _simulation_active,
        "db_engine":   get_active_engine(),
        "timestamp":   datetime.now(timezone.utc).isoformat(),
    }


ESP32_DIR = BASE_DIR.parent / "esp32"
if ESP32_DIR.exists():
    app.mount("/esp32", StaticFiles(directory=str(ESP32_DIR)), name="esp32")

if FRONTEND_DIR.exists():
    app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")
    app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")
    
    # Specific HTML routes so user can visit directly
    @app.get("/index.html")
    @app.get("/")
    async def serve_index():
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/farmer.html")
    async def serve_farmer():
        return FileResponse(FRONTEND_DIR / "farmer.html")

    @app.get("/supply.html")
    async def serve_supply():
        return FileResponse(FRONTEND_DIR / "supply.html")

    @app.get("/monitor.html")
    async def serve_monitor():
        return FileResponse(FRONTEND_DIR / "monitor.html")

    @app.get("/blockchain.html")
    async def serve_blockchain_page():
        return FileResponse(FRONTEND_DIR / "blockchain.html")

    @app.get("/verify.html")
    async def serve_verify():
        return FileResponse(FRONTEND_DIR / "verify.html")

    @app.get("/admin.html")
    async def serve_admin():
        return FileResponse(FRONTEND_DIR / "admin.html")

    @app.get("/hardware.html")
    async def serve_hardware():
        return FileResponse(FRONTEND_DIR / "hardware.html")


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("  Trust Mesh IoT + Blockchain Platform v1.2")
    print("  Web App & Dashboard : http://localhost:8000")
    print("  Interactive Swagger : http://localhost:8000/docs")
    print("=" * 60)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
