"""
AgriLedger Comprehensive Automated Test Suite
=============================================
Tests all system layers:
1. Database connectivity & schemas (MySQL & SQLite)
2. Blockchain cryptographic engine & tamper detection
3. REST API endpoints (all CRUD + telemetry routes)
4. Frontend static assets delivery & QR generation
5. IoT simulated data loop
"""

import sys
import os
from pathlib import Path

# Fix Windows console UTF-8 encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
sys.path.insert(0, str(PROJECT_ROOT / "blockchain"))

from fastapi.testclient import TestClient
from main import app
from database import get_db, db_exec, get_active_engine
from agri_chain import blockchain_manager, hash_payload, Block, AgriChain

def test_system():
    print("\n" + "=" * 65)
    print("  AGRILEDGER AUTOMATED SYSTEM & INTEGRATION TEST SUITE")
    print("=" * 65 + "\n")

    passed_tests = 0
    total_tests = 0

    def assert_test(name, condition, details=""):
        nonlocal passed_tests, total_tests
        total_tests += 1
        if condition:
            passed_tests += 1
            print(f"  [PASS] {name} {details}")
        else:
            print(f"  [FAIL] {name} {details}")
            raise AssertionError(f"Test failed: {name} -> {details}")

    # =========================================================================
    # 1. DATABASE & SCHEMA TESTS
    # =========================================================================
    print("--- 1. DATABASE & SCHEMA TESTS ---")
    conn = get_db()
    assert_test("Database Connection", conn is not None, f"Engine: {get_active_engine().upper()}")
    
    users = db_exec(conn, "SELECT COUNT(*) as c FROM users", fetch="one")
    assert_test("Users Table Seeded", users and users["c"] >= 5, f"Found {users['c']} users")

    products = db_exec(conn, "SELECT COUNT(*) as c FROM products", fetch="one")
    assert_test("Products Table Seeded", products and products["c"] >= 2, f"Found {products['c']} products")

    devices = db_exec(conn, "SELECT COUNT(*) as c FROM devices", fetch="one")
    assert_test("Devices Table Seeded", devices and devices["c"] >= 2, f"Found {devices['c']} devices")
    conn.close()

    # =========================================================================
    # 2. BLOCKCHAIN ENGINE TESTS
    # =========================================================================
    print("\n--- 2. BLOCKCHAIN CRYPTOGRAPHY & TAMPER DETECTION ---")
    chain = AgriChain("TEST-PROD-001")
    assert_test("Genesis Block Created", len(chain.chain) == 1 and chain.chain[0].event_type == "GENESIS")
    assert_test("Genesis Block Hash Integrity", chain.chain[0].current_hash.startswith("00"), f"Hash: {chain.chain[0].current_hash[:16]}...")

    b1 = chain.add_block("FARM_HARVESTED", "hash1111" * 8)
    assert_test("Block 1 Mined & Linked", b1.index == 1 and b1.previous_hash == chain.chain[0].current_hash)
    assert_test("Chain Validity (Pre-tamper)", chain.is_valid() == True)

    # Tamper simulation test
    orig_hash = b1.sensor_data_hash
    b1.sensor_data_hash = "tampered_data_hash_9999" * 4
    assert_test("Tamper Detection (Hash Mismatch)", chain.is_valid() == False, "Tampered block successfully detected!")
    b1.sensor_data_hash = orig_hash
    assert_test("Chain Restored to Valid", chain.is_valid() == True)

    # =========================================================================
    # 3. REST API ENDPOINTS & INTEGRATION TESTS
    # =========================================================================
    print("\n--- 3. FASTAPI REST API INTEGRATION TESTS ---")
    with TestClient(app) as client:
        # GET /api/health
        res = client.get("/api/health")
        assert_test("GET /api/health", res.status_code == 200 and res.json().get("status") == "ok")

        # GET /api/dashboard/stats
        res = client.get("/api/dashboard/stats")
        data = res.json()
        assert_test("GET /api/dashboard/stats", res.status_code == 200 and data.get("products", 0) >= 2, f"Stats: {data['products']} prods, {data['sensor_readings']} readings")

        # POST /api/register-product
        new_prod_id = f"AGRI-UNIT-{os.urandom(3).hex().upper()}"
        res = client.post("/api/register-product", json={
            "product_id": new_prod_id,
            "farmer_user_id": "USER-FARMER-001",
            "device_id": "DEVICE-001",
            "name": "Organic Golden Wheat",
            "category": "Grain",
            "quantity": 2500.0,
            "unit": "kg",
            "harvest_date": "2026-09-27",
            "origin_location": "Punjab, India"
        })
        assert_test("POST /api/register-product", res.status_code == 200 and res.json().get("success") == True, f"Created {new_prod_id}")

        # GET /api/product/{id}
        res = client.get(f"/api/product/{new_prod_id}")
        assert_test("GET /api/product/{id}", res.status_code == 200 and res.json().get("name") == "Organic Golden Wheat")

        # POST /api/sensor-data (IoT telemetry)
        res = client.post("/api/sensor-data", json={
            "device_id": "DEVICE-001",
            "product_id": new_prod_id,
            "temperature": 23.8,
            "humidity": 62.4,
            "latitude": 30.9010,
            "longitude": 75.8573,
            "is_simulated": False
        })
        assert_test("POST /api/sensor-data", res.status_code == 200 and res.json().get("success") == True, f"Hash: {res.json().get('data_hash')[:16]}...")

        # POST /api/supply-event (Chain movement)
        res = client.post("/api/supply-event", json={
            "product_id": new_prod_id,
            "user_id": "USER-WAREHOUSE-001",
            "event_type": "WAREHOUSE_RECEIVED",
            "location": "Ludhiana Silo Unit 2",
            "latitude": 30.9050,
            "longitude": 75.8600,
            "notes": "Moisture level inspected: 12% optimal"
        })
        assert_test("POST /api/supply-event", res.status_code == 200 and res.json().get("success") == True, f"Block #{res.json().get('block_index')}")

        # GET /api/verify/{id} (Consumer verification)
        res = client.get(f"/api/verify/{new_prod_id}")
        v_data = res.json()
        assert_test("GET /api/verify/{id}", res.status_code == 200 and v_data.get("verified") == True, f"Verified: {v_data.get('verified')}, Journey events: {len(v_data.get('supply_journey', []))}")

        # POST /api/tamper-test
        res = client.post("/api/tamper-test", json={
            "product_id": new_prod_id,
            "block_index": 1,
            "field": "sensor_data_hash",
            "new_value": "0000badf00d0000" * 4
        })
        tamper_res = res.json()
        is_tamper_detected = tamper_res.get("report", {}).get("chain_valid") == False
        assert_test("POST /api/tamper-test", res.status_code == 200 and is_tamper_detected, "Tamper simulation detected by verification engine")

        # GET /api/devices
        res = client.get("/api/devices")
        assert_test("GET /api/devices", res.status_code == 200 and len(res.json().get("devices", [])) >= 2)

        # GET /api/qr/{id}
        res = client.get(f"/api/qr/{new_prod_id}")
        assert_test("GET /api/qr/{id} (PNG File)", res.status_code == 200 and res.headers.get("content-type") == "image/png")

        # Simulation Start & Stop
        res = client.post("/api/simulate/start")
        assert_test("POST /api/simulate/start", res.status_code == 200)
        res = client.post("/api/simulate/stop")
        assert_test("POST /api/simulate/stop", res.status_code == 200)

        # =====================================================================
        # 4. FRONTEND STATIC ASSETS & PAGES
        # =====================================================================
        print("\n--- 4. FRONTEND STATIC ASSETS & WEB DASHBOARD ---")
        pages = [
            ("/", "Landing Page"),
            ("/index.html", "Home HTML"),
            ("/farmer.html", "Farmer Portal"),
            ("/hardware.html", "Hardware & Circuit Dashboard"),
            ("/monitor.html", "Live Sensors Telemetry"),
            ("/supply.html", "Supply Chain Timeline"),
            ("/blockchain.html", "Blockchain Explorer"),
            ("/verify.html", "Consumer QR Verification"),
            ("/admin.html", "Admin & Diagnostics"),
            ("/css/main.css", "Design System Stylesheet"),
            ("/js/api.js", "API Client JS"),
            ("/js/app.js", "App Logic JS"),
        ]
        for path, label in pages:
            res = client.get(path)
            assert_test(f"Serve {label} ({path})", res.status_code == 200, f"Size: {len(res.content)} bytes")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 65)
    print(f"  TEST RESULTS: {passed_tests}/{total_tests} TESTS PASSED (100% SUCCESS)")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    test_system()
