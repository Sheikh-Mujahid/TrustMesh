"""
AgriLedger - Blockchain Unit Tests
===================================
Run with: python -m pytest blockchain/test_chain.py -v
"""

import sys
import hashlib
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from agri_chain import Block, AgriChain, BlockchainManager, hash_payload


def test_genesis_block():
    chain = AgriChain("TEST-001")
    assert len(chain.chain) == 1
    block = chain.chain[0]
    assert block.index == 0
    assert block.event_type == "GENESIS"
    assert block.previous_hash == "0" * 64


def test_add_block():
    chain = AgriChain("TEST-002")
    block = chain.add_block("FARM_HARVESTED", hash_payload({"test": "data"}))
    assert block.index == 1
    assert block.event_type == "FARM_HARVESTED"
    assert block.previous_hash == chain.chain[0].current_hash


def test_chain_valid():
    chain = AgriChain("TEST-003")
    chain.add_block("WAREHOUSE_RECEIVED", hash_payload({"loc": "Pune"}))
    chain.add_block("RETAILER_RECEIVED", hash_payload({"loc": "Mumbai"}))
    assert chain.is_valid() is True


def test_tamper_detection():
    chain = AgriChain("TEST-004")
    chain.add_block("SENSOR_DATA", hash_payload({"temp": 25.4}))

    # Tamper: mutate a stored field without updating hash
    chain.chain[1].sensor_data_hash = "aaaaaaaabbbbbbbbcccccccc" * 3

    assert chain.is_valid() is False

    report = chain.full_verification_report()
    tampered = [b for b in report["blocks"] if b["status"] == "TAMPERED"]
    assert len(tampered) >= 1


def test_hash_determinism():
    payload = {"product_id": "AGRI-001", "temp": 25.4, "hum": 67.0}
    h1 = hash_payload(payload)
    h2 = hash_payload(payload)
    assert h1 == h2
    assert len(h1) == 64


def test_proof_of_work():
    chain = AgriChain("TEST-005")
    block = chain.chain[0]
    # Difficulty 2 means hash must start with "00"
    assert block.current_hash.startswith("00")


def test_manager():
    mgr = BlockchainManager()
    b1 = mgr.add_event("PROD-A", "FARM_HARVESTED", {"farmer": "Ramesh"})
    b2 = mgr.add_event("PROD-A", "WAREHOUSE_RECEIVED", {"loc": "Pune"})
    assert b1.index == 1
    assert b2.index == 2

    result = mgr.verify_product("PROD-A")
    assert result["chain_valid"] is True


def test_tamper_demo_via_manager():
    mgr = BlockchainManager()
    mgr.add_event("PROD-B", "FARM_HARVESTED", {"farmer": "Suresh"})

    result = mgr.tamper_test("PROD-B", 1, "sensor_data_hash", "badbadbad" * 8)
    any_tampered = any(b["status"] == "TAMPERED" for b in result["report"]["blocks"])
    assert any_tampered is True


if __name__ == "__main__":
    tests = [
        test_genesis_block, test_add_block, test_chain_valid,
        test_tamper_detection, test_hash_determinism,
        test_proof_of_work, test_manager, test_tamper_demo_via_manager,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  [PASS] {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  [FAIL] {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  [ERR ] {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed}/{passed+failed} tests passed.")

