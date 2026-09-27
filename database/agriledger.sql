-- ============================================================
-- AgriLedger Database Schema
-- MySQL 8.0+
-- ============================================================

CREATE DATABASE IF NOT EXISTS agriledger
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE agriledger;

-- ============================================================
-- TABLE: users
-- ============================================================
CREATE TABLE users (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    user_id         VARCHAR(50)  NOT NULL UNIQUE,
    name            VARCHAR(100) NOT NULL,
    role            ENUM('farmer','warehouse','transport','retailer','admin','consumer') NOT NULL DEFAULT 'farmer',
    email           VARCHAR(150) NOT NULL UNIQUE,
    phone           VARCHAR(20),
    location        VARCHAR(200),
    aadhaar_hash    VARCHAR(64),
    is_active       TINYINT(1)   NOT NULL DEFAULT 1,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_role  (role),
    INDEX idx_email (email)
) ENGINE=InnoDB;

-- ============================================================
-- TABLE: devices
-- ============================================================
CREATE TABLE devices (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    device_id       VARCHAR(50)  NOT NULL UNIQUE,
    owner_user_id   VARCHAR(50)  NOT NULL,
    firmware_ver    VARCHAR(20)  DEFAULT '1.0.0',
    mac_address     VARCHAR(17),
    is_active       TINYINT(1)   NOT NULL DEFAULT 1,
    last_seen       DATETIME,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY fk_device_user (owner_user_id) REFERENCES users(user_id) ON UPDATE CASCADE,
    INDEX idx_owner (owner_user_id)
) ENGINE=InnoDB;

-- ============================================================
-- TABLE: products
-- ============================================================
CREATE TABLE products (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    product_id      VARCHAR(50)  NOT NULL UNIQUE,
    device_id       VARCHAR(50),
    farmer_user_id  VARCHAR(50)  NOT NULL,
    name            VARCHAR(150) NOT NULL,
    category        VARCHAR(100),
    quantity        DECIMAL(10,2),
    unit            VARCHAR(20),
    harvest_date    DATE,
    origin_location VARCHAR(200),
    qr_code_url     TEXT,
    status          ENUM('registered','in_transit','warehouse','retail','delivered') NOT NULL DEFAULT 'registered',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY fk_product_user   (farmer_user_id) REFERENCES users(user_id) ON UPDATE CASCADE,
    FOREIGN KEY fk_product_device (device_id)      REFERENCES devices(device_id) ON UPDATE CASCADE ON DELETE SET NULL,
    INDEX idx_farmer   (farmer_user_id),
    INDEX idx_status   (status)
) ENGINE=InnoDB;

-- ============================================================
-- TABLE: sensor_data
-- ============================================================
CREATE TABLE sensor_data (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    device_id       VARCHAR(50)  NOT NULL,
    product_id      VARCHAR(50)  NOT NULL,
    temperature     DECIMAL(5,2),
    humidity        DECIMAL(5,2),
    latitude        DECIMAL(10,7),
    longitude       DECIMAL(10,7),
    data_hash       VARCHAR(64)  NOT NULL,
    is_simulated    TINYINT(1)   NOT NULL DEFAULT 0,
    received_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sensor_ts       DATETIME     NOT NULL,
    INDEX idx_device    (device_id),
    INDEX idx_product   (product_id),
    INDEX idx_received  (received_at),
    FOREIGN KEY fk_sensor_device  (device_id)  REFERENCES devices(device_id) ON UPDATE CASCADE,
    FOREIGN KEY fk_sensor_product (product_id) REFERENCES products(product_id) ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ============================================================
-- TABLE: supply_chain_events
-- ============================================================
CREATE TABLE supply_chain_events (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    event_id        VARCHAR(50)  NOT NULL UNIQUE,
    product_id      VARCHAR(50)  NOT NULL,
    user_id         VARCHAR(50)  NOT NULL,
    event_type      ENUM(
                        'FARM_HARVESTED',
                        'COLLECTION_CENTER_RECEIVED',
                        'TRANSPORT_DISPATCHED',
                        'WAREHOUSE_RECEIVED',
                        'RETAILER_RECEIVED',
                        'CONSUMER_DELIVERED'
                    ) NOT NULL,
    location        VARCHAR(200),
    latitude        DECIMAL(10,7),
    longitude       DECIMAL(10,7),
    notes           TEXT,
    data_hash       VARCHAR(64)  NOT NULL,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY fk_event_product (product_id) REFERENCES products(product_id) ON UPDATE CASCADE,
    FOREIGN KEY fk_event_user    (user_id)    REFERENCES users(user_id) ON UPDATE CASCADE,
    INDEX idx_event_product (product_id),
    INDEX idx_event_type    (event_type)
) ENGINE=InnoDB;

-- ============================================================
-- TABLE: blockchain_transactions
-- ============================================================
CREATE TABLE blockchain_transactions (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    block_index     INT          NOT NULL,
    product_id      VARCHAR(50)  NOT NULL,
    event_id        VARCHAR(50),
    event_type      VARCHAR(100) NOT NULL,
    sensor_data_hash VARCHAR(64),
    previous_hash   VARCHAR(64)  NOT NULL,
    current_hash    VARCHAR(64)  NOT NULL UNIQUE,
    nonce           BIGINT       NOT NULL DEFAULT 0,
    block_timestamp DATETIME     NOT NULL,
    is_genesis      TINYINT(1)   NOT NULL DEFAULT 0,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY fk_block_product (product_id) REFERENCES products(product_id) ON UPDATE CASCADE,
    INDEX idx_block_product (product_id),
    INDEX idx_block_index   (block_index),
    INDEX idx_block_hash    (current_hash)
) ENGINE=InnoDB;

-- ============================================================
-- SEED DATA
-- ============================================================

INSERT INTO users (user_id, name, role, email, phone, location) VALUES
('USER-ADMIN-001',     'AgriLedger Admin',  'admin',     'admin@agriledger.in',     '9000000001', 'Mumbai, Maharashtra'),
('USER-FARMER-001',    'Ramesh Patil',      'farmer',    'ramesh@agriledger.in',    '9000000002', 'Nashik, Maharashtra'),
('USER-WAREHOUSE-001', 'Godown Manager',    'warehouse', 'warehouse@agriledger.in', '9000000003', 'Pune, Maharashtra'),
('USER-TRANSPORT-001', 'Suresh Transport',  'transport', 'transport@agriledger.in', '9000000004', 'Nashik, Maharashtra'),
('USER-RETAILER-001',  'City Retailer',     'retailer',  'retailer@agriledger.in',  '9000000005', 'Mumbai, Maharashtra');

INSERT INTO devices (device_id, owner_user_id, firmware_ver, mac_address) VALUES
('DEVICE-001', 'USER-FARMER-001', '1.0.0', 'AA:BB:CC:DD:EE:01'),
('DEVICE-002', 'USER-FARMER-001', '1.0.0', 'AA:BB:CC:DD:EE:02');

INSERT INTO products (product_id, device_id, farmer_user_id, name, category, quantity, unit, harvest_date, origin_location, status) VALUES
('AGRI-001', 'DEVICE-001', 'USER-FARMER-001', 'Organic Tomatoes', 'Vegetable', 500.00,  'kg', '2026-09-20', 'Nashik, Maharashtra', 'registered'),
('AGRI-002', 'DEVICE-002', 'USER-FARMER-001', 'Fresh Onions',     'Vegetable', 1000.00, 'kg', '2026-09-22', 'Nashik, Maharashtra', 'registered');
