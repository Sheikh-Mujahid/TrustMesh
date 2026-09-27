"""
AgriLedger Database Adapter
============================
Unified database access layer supporting both MySQL and SQLite.
Auto-detects MySQL; gracefully falls back to SQLite if MySQL is unavailable.
Automatically provisions tables and seed data if database is empty.
"""

import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# MySQL support (optional / dynamic)
try:
    import mysql.connector
    from mysql.connector import Error as MySQLError
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    MySQLError = Exception

DB_DIR = Path(__file__).parent.parent / "database"
DB_DIR.mkdir(exist_ok=True)
SQLITE_PATH = DB_DIR / "agriledger.db"

# Configuration from env
DB_ENGINE = os.getenv("DB_ENGINE", "auto").lower()  # "mysql", "sqlite", "auto"
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "agriledger")

_ACTIVE_ENGINE = "sqlite"  # determined during init


def get_active_engine() -> str:
    return _ACTIVE_ENGINE


class DBConnection:
    """Wrapper that normalizes MySQL and SQLite connections."""
    def __init__(self, conn, engine: str):
        self.conn = conn
        self.engine = engine

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()


def _get_mysql_raw():
    if not MYSQL_AVAILABLE:
        raise RuntimeError("mysql-connector-python not installed")
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4",
        autocommit=False,
        connection_timeout=3,
    )


def _get_sqlite_raw():
    conn = sqlite3.connect(str(SQLITE_PATH), timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db() -> DBConnection:
    global _ACTIVE_ENGINE
    if _ACTIVE_ENGINE == "mysql":
        try:
            raw = _get_mysql_raw()
            return DBConnection(raw, "mysql")
        except Exception as e:
            # Fallback to SQLite if MySQL dropped
            print(f"[DB] MySQL connection error ({e}). Falling back to SQLite.")
            raw = _get_sqlite_raw()
            return DBConnection(raw, "sqlite")
    else:
        raw = _get_sqlite_raw()
        return DBConnection(raw, "sqlite")


def db_exec(conn: DBConnection, sql: str, params=None, fetch: str = "none") -> Any:
    """
    Executes a SQL statement on either MySQL or SQLite.
    Normalizes %s to ? for SQLite and handles INSERT IGNORE / INSERT OR IGNORE.
    """
    params = params or ()
    # Convert list/tuple params if needed
    if isinstance(params, (list, tuple)):
        params = tuple(params)

    if conn.engine == "sqlite":
        # Transform MySQL syntax to SQLite syntax
        sqlite_sql = sql.replace("%s", "?")
        sqlite_sql = sqlite_sql.replace("INSERT IGNORE", "INSERT OR IGNORE")
        
        cur = conn.conn.cursor()
        cur.execute(sqlite_sql, params)
        if fetch == "one":
            row = cur.fetchone()
            result = dict(row) if row is not None else None
        elif fetch == "all":
            rows = cur.fetchall()
            result = [dict(r) for r in rows]
        else:
            result = cur.lastrowid
        cur.close()
        return result
    else:
        # MySQL
        cur = conn.conn.cursor(dictionary=True)
        cur.execute(sql, params)
        if fetch == "one":
            result = cur.fetchone()
        elif fetch == "all":
            result = cur.fetchall()
        else:
            result = cur.lastrowid
        cur.close()
        return result


def init_database():
    """Initializes tables and seeds data on startup if not present."""
    global _ACTIVE_ENGINE

    # Try MySQL if requested or auto
    if DB_ENGINE in ("mysql", "auto") and MYSQL_AVAILABLE:
        try:
            # First check if MySQL server is reachable & create DB if missing
            root_conn = mysql.connector.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD,
                connection_timeout=3,
            )
            root_cur = root_conn.cursor()
            root_cur.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            root_cur.close()
            root_conn.close()

            # Now test connecting to the database
            test_conn = _get_mysql_raw()
            _ACTIVE_ENGINE = "mysql"
            print(f"[DB] Connected to MySQL database '{DB_NAME}' at {DB_HOST}:{DB_PORT}")
            
            # Run schema checks for MySQL
            _init_mysql_schema(test_conn)
            test_conn.close()
            return
        except Exception as e:
            print(f"[DB] MySQL not available ({e}). Using local SQLite database.")
            _ACTIVE_ENGINE = "sqlite"
    else:
        _ACTIVE_ENGINE = "sqlite"

    print(f"[DB] Using local SQLite database at {SQLITE_PATH}")
    conn = _get_sqlite_raw()
    _init_sqlite_schema(conn)
    conn.close()


def _init_sqlite_schema(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         TEXT NOT NULL UNIQUE,
        name            TEXT NOT NULL,
        role            TEXT NOT NULL DEFAULT 'farmer',
        email           TEXT NOT NULL UNIQUE,
        phone           TEXT,
        location        TEXT,
        aadhaar_hash    TEXT,
        is_active       INTEGER NOT NULL DEFAULT 1,
        created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS devices (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id       TEXT NOT NULL UNIQUE,
        owner_user_id   TEXT NOT NULL,
        firmware_ver    TEXT DEFAULT '1.0.0',
        mac_address     TEXT,
        is_active       INTEGER NOT NULL DEFAULT 1,
        last_seen       DATETIME,
        created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS products (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id      TEXT NOT NULL UNIQUE,
        device_id       TEXT,
        farmer_user_id  TEXT NOT NULL,
        name            TEXT NOT NULL,
        category        TEXT,
        quantity        REAL,
        unit            TEXT DEFAULT 'kg',
        harvest_date    TEXT,
        origin_location TEXT,
        qr_code_url     TEXT,
        status          TEXT NOT NULL DEFAULT 'registered',
        created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS sensor_data (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id       TEXT NOT NULL,
        product_id      TEXT NOT NULL,
        temperature     REAL,
        humidity        REAL,
        latitude        REAL,
        longitude       REAL,
        data_hash       TEXT NOT NULL,
        is_simulated    INTEGER NOT NULL DEFAULT 0,
        received_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        sensor_ts       DATETIME NOT NULL
    );

    CREATE TABLE IF NOT EXISTS supply_chain_events (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id        TEXT NOT NULL UNIQUE,
        product_id      TEXT NOT NULL,
        user_id         TEXT NOT NULL,
        event_type      TEXT NOT NULL,
        location        TEXT,
        latitude        REAL,
        longitude       REAL,
        notes           TEXT,
        data_hash       TEXT NOT NULL,
        created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS blockchain_transactions (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        block_index     INTEGER NOT NULL,
        product_id      TEXT NOT NULL,
        event_id        TEXT,
        event_type      TEXT NOT NULL,
        sensor_data_hash TEXT,
        previous_hash   TEXT NOT NULL,
        current_hash    TEXT NOT NULL UNIQUE,
        nonce           INTEGER NOT NULL DEFAULT 0,
        block_timestamp DATETIME NOT NULL,
        is_genesis      INTEGER NOT NULL DEFAULT 0,
        created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Check if seed users exist
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        print("[DB] Seeding default database records...")
        cur.executescript("""
        INSERT OR IGNORE INTO users (user_id, name, role, email, phone, location) VALUES
        ('USER-ADMIN-001',     'AgriLedger Admin',  'admin',     'admin@agriledger.in',     '9000000001', 'Mumbai, Maharashtra'),
        ('USER-FARMER-001',    'Ramesh Patil',      'farmer',    'ramesh@agriledger.in',    '9000000002', 'Nashik, Maharashtra'),
        ('USER-WAREHOUSE-001', 'Godown Manager',    'warehouse', 'warehouse@agriledger.in', '9000000003', 'Pune, Maharashtra'),
        ('USER-TRANSPORT-001', 'Suresh Transport',  'transport', 'transport@agriledger.in', '9000000004', 'Nashik, Maharashtra'),
        ('USER-RETAILER-001',  'City Retailer',     'retailer',  'retailer@agriledger.in',  '9000000005', 'Mumbai, Maharashtra');

        INSERT OR IGNORE INTO devices (device_id, owner_user_id, firmware_ver, mac_address) VALUES
        ('DEVICE-001', 'USER-FARMER-001', '1.0.0', 'AA:BB:CC:DD:EE:01'),
        ('DEVICE-002', 'USER-FARMER-001', '1.0.0', 'AA:BB:CC:DD:EE:02'),
        ('DEVICE-SIM-001', 'USER-FARMER-001', 'SIM-1.0', 'FF:FF:FF:FF:FF:00');

        INSERT OR IGNORE INTO products (product_id, device_id, farmer_user_id, name, category, quantity, unit, harvest_date, origin_location, status, qr_code_url) VALUES
        ('AGRI-001', 'DEVICE-001', 'USER-FARMER-001', 'Organic Tomatoes', 'Vegetable', 500.00,  'kg', '2026-09-20', 'Nashik, Maharashtra', 'in_transit', 'http://localhost:8000/verify.html?id=AGRI-001'),
        ('AGRI-002', 'DEVICE-002', 'USER-FARMER-001', 'Alphonso Mangoes',  'Fruit',     1200.00, 'kg', '2026-09-18', 'Ratnagiri, Maharashtra', 'registered', 'http://localhost:8000/verify.html?id=AGRI-002');

        INSERT OR IGNORE INTO supply_chain_events (event_id, product_id, user_id, event_type, location, latitude, longitude, notes, data_hash) VALUES
        ('EVT-001-HARVEST',   'AGRI-001', 'USER-FARMER-001',    'FARM_HARVESTED',             'Nashik Farm Field #4', 20.0059000, 73.7897000, 'Harvested at optimal ripeness', 'a1b2c3d4e5f60102030405060708090a1b2c3d4e5f60718293a4b5c6d7e8f900'),
        ('EVT-002-COLLECTION', 'AGRI-001', 'USER-WAREHOUSE-001', 'COLLECTION_CENTER_RECEIVED', 'Nashik APMC Market',   20.0110000, 73.7920000, 'Quality inspected and sorted grade A', 'b2c3d4e5f6a102030405060708090a1b2c3d4e5f60718293a4b5c6d7e8f90111'),
        ('EVT-003-TRANSPORT',  'AGRI-001', 'USER-TRANSPORT-001', 'TRANSPORT_DISPATCHED',      'Nashik-Pune Highway',  19.8500000, 73.8100000, 'Refrigerated truck #MH-15-AB-1234', 'c3d4e5f6a1b202030405060708090a1b2c3d4e5f60718293a4b5c6d7e8f90222');

        INSERT OR IGNORE INTO sensor_data (device_id, product_id, temperature, humidity, latitude, longitude, data_hash, is_simulated, sensor_ts) VALUES
        ('DEVICE-001', 'AGRI-001', 24.50, 68.20, 20.0059000, 73.7897000, 'd4e5f6a1b2c302030405060708090a1b2c3d4e5f60718293a4b5c6d7e8f90333', 0, '2026-09-20 08:30:00'),
        ('DEVICE-001', 'AGRI-001', 25.10, 67.80, 20.0062000, 73.7899000, 'e5f6a1b2c3d402030405060708090a1b2c3d4e5f60718293a4b5c6d7e8f90444', 0, '2026-09-20 09:00:00'),
        ('DEVICE-001', 'AGRI-001', 26.00, 65.40, 20.0070000, 73.7905000, 'f6a1b2c3d4e502030405060708090a1b2c3d4e5f60718293a4b5c6d7e8f90555', 0, '2026-09-20 09:30:00'),
        ('DEVICE-001', 'AGRI-001', 25.80, 66.10, 20.0090000, 73.7915000, 'a2b3c4d5e6f102030405060708090a1b2c3d4e5f60718293a4b5c6d7e8f90666', 0, '2026-09-20 10:00:00');
        """)
        conn.commit()
    cur.close()


def _init_mysql_schema(conn):
    sql_path = DB_DIR / "agriledger.sql"
    if sql_path.exists():
        with open(sql_path, "r", encoding="utf-8") as f:
            sql_script = f.read()
        cur = conn.cursor()
        for statement in sql_script.split(";"):
            stmt = statement.strip()
            if stmt and not stmt.lower().startswith("create database") and not stmt.lower().startswith("use"):
                try:
                    cur.execute(stmt)
                except Exception:
                    pass
        conn.commit()
        cur.close()
