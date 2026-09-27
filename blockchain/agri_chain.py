"""
AgriLedger - Local Blockchain Implementation
=============================================
SHA-256 based proof-of-work blockchain for supply-chain traceability.
This is a LOCAL prototype. It is designed so that a permissioned DLT
(Hyperledger Fabric / IOTA Tangle) can replace this layer later.

OFF-CHAIN  : product info, user data, sensor history, operational data
ON-CHAIN   : block index, timestamp, event_type, data_hash, prev_hash, current_hash
"""

import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Block
# ---------------------------------------------------------------------------

class Block:
    """A single immutable record in the AgriLedger chain."""

    def __init__(
        self,
        index: int,
        product_id: str,
        event_type: str,
        sensor_data_hash: str,
        previous_hash: str,
        timestamp: Optional[str] = None,
        nonce: int = 0,
    ):
        self.index            = index
        self.product_id       = product_id
        self.event_type       = event_type
        self.sensor_data_hash = sensor_data_hash   # SHA-256 of off-chain payload
        self.previous_hash    = previous_hash
        self.timestamp        = timestamp or datetime.now(timezone.utc).isoformat()
        self.nonce            = nonce
        self.current_hash     = self._compute_hash()

    # ------------------------------------------------------------------
    # Hashing
    # ------------------------------------------------------------------
    def _compute_hash(self) -> str:
        payload = {
            "index":            self.index,
            "product_id":       self.product_id,
            "event_type":       self.event_type,
            "sensor_data_hash": self.sensor_data_hash,
            "previous_hash":    self.previous_hash,
            "timestamp":        self.timestamp,
            "nonce":            self.nonce,
        }
        raw = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def recompute_hash(self) -> str:
        """Re-derive hash from current fields (used for tamper detection)."""
        return self._compute_hash()

    # ------------------------------------------------------------------
    # Proof-of-Work (lightweight, difficulty=2 for demo speed)
    # ------------------------------------------------------------------
    def mine(self, difficulty: int = 2) -> None:
        target = "0" * difficulty
        while not self.current_hash.startswith(target):
            self.nonce += 1
            self.current_hash = self._compute_hash()

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "index":            self.index,
            "product_id":       self.product_id,
            "event_type":       self.event_type,
            "sensor_data_hash": self.sensor_data_hash,
            "previous_hash":    self.previous_hash,
            "current_hash":     self.current_hash,
            "timestamp":        self.timestamp,
            "nonce":            self.nonce,
        }

    def __repr__(self) -> str:
        return (
            f"\n{'='*60}\n"
            f"  BLOCK {self.index:>4}\n"
            f"  Product   : {self.product_id}\n"
            f"  Event     : {self.event_type}\n"
            f"  Timestamp : {self.timestamp}\n"
            f"  Prev Hash : {self.previous_hash[:16]}...\n"
            f"  Curr Hash : {self.current_hash[:16]}...\n"
            f"  Nonce     : {self.nonce}\n"
            f"{'='*60}\n"
        )


# ---------------------------------------------------------------------------
# AgriChain  –  per-product blockchain
# ---------------------------------------------------------------------------

class AgriChain:
    """
    An independent chain per product_id.
    Each product gets its own genesis block and block sequence.
    """

    DIFFICULTY = 2

    def __init__(self, product_id: str):
        self.product_id = product_id
        self.chain: List[Block] = []
        self._create_genesis()

    # ------------------------------------------------------------------
    # Genesis
    # ------------------------------------------------------------------
    def _create_genesis(self) -> None:
        genesis = Block(
            index=0,
            product_id=self.product_id,
            event_type="GENESIS",
            sensor_data_hash="0" * 64,
            previous_hash="0" * 64,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        genesis.mine(self.DIFFICULTY)
        self.chain.append(genesis)

    # ------------------------------------------------------------------
    # Add block
    # ------------------------------------------------------------------
    def add_block(
        self,
        event_type: str,
        sensor_data_hash: str,
        timestamp: Optional[str] = None,
    ) -> Block:
        last = self.chain[-1]
        new_block = Block(
            index=len(self.chain),
            product_id=self.product_id,
            event_type=event_type,
            sensor_data_hash=sensor_data_hash,
            previous_hash=last.current_hash,
            timestamp=timestamp,
        )
        new_block.mine(self.DIFFICULTY)
        self.chain.append(new_block)
        return new_block

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def is_valid(self) -> bool:
        for i in range(1, len(self.chain)):
            curr = self.chain[i]
            prev = self.chain[i - 1]

            # 1. Hash integrity
            if curr.current_hash != curr.recompute_hash():
                return False
            # 2. Chain linkage
            if curr.previous_hash != prev.current_hash:
                return False
        return True

    def verify_block(self, block_index: int) -> Dict[str, Any]:
        """Verify a single block and return a detailed report."""
        if block_index >= len(self.chain):
            return {"status": "NOT_FOUND", "detail": "Block index out of range"}

        block = self.chain[block_index]
        recomputed = block.recompute_hash()

        hash_ok = recomputed == block.current_hash
        chain_ok = True
        if block_index > 0:
            prev = self.chain[block_index - 1]
            chain_ok = block.previous_hash == prev.current_hash

        status = "VALID" if (hash_ok and chain_ok) else "TAMPERED"
        return {
            "status":        status,
            "block_index":   block_index,
            "product_id":    block.product_id,
            "event_type":    block.event_type,
            "stored_hash":   block.current_hash,
            "recomputed":    recomputed,
            "hash_match":    hash_ok,
            "chain_link_ok": chain_ok,
        }

    def full_verification_report(self) -> Dict[str, Any]:
        """Verify entire chain and return summary."""
        results = []
        all_valid = True
        for i in range(len(self.chain)):
            r = self.verify_block(i)
            results.append(r)
            if r["status"] != "VALID":
                all_valid = False
        return {
            "product_id":  self.product_id,
            "chain_valid": all_valid,
            "total_blocks": len(self.chain),
            "blocks":      results,
        }

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------
    def to_dict(self) -> List[Dict[str, Any]]:
        return [b.to_dict() for b in self.chain]


# ---------------------------------------------------------------------------
# BlockchainManager  –  manages chains for all products
# ---------------------------------------------------------------------------

class BlockchainManager:
    """
    Singleton-style manager.
    In production replace storage with a permissioned DLT (Hyperledger / IOTA).
    """

    def __init__(self):
        self._chains: Dict[str, AgriChain] = {}

    # ------------------------------------------------------------------
    def get_or_create_chain(self, product_id: str) -> AgriChain:
        if product_id not in self._chains:
            self._chains[product_id] = AgriChain(product_id)
        return self._chains[product_id]

    def add_event(
        self,
        product_id: str,
        event_type: str,
        payload: Dict[str, Any],
        timestamp: Optional[str] = None,
    ) -> Block:
        """Hash the off-chain payload and record it on-chain."""
        raw = json.dumps(payload, sort_keys=True, default=str)
        payload_hash = hashlib.sha256(raw.encode()).hexdigest()
        chain = self.get_or_create_chain(product_id)
        return chain.add_block(event_type, payload_hash, timestamp)

    def verify_product(self, product_id: str) -> Dict[str, Any]:
        if product_id not in self._chains:
            return {"status": "NO_CHAIN", "product_id": product_id}
        return self._chains[product_id].full_verification_report()

    def get_chain(self, product_id: str) -> List[Dict[str, Any]]:
        if product_id not in self._chains:
            return []
        return self._chains[product_id].to_dict()

    def tamper_test(self, product_id: str, block_index: int, field: str, new_value: Any) -> Dict[str, Any]:
        """
        DEMO ONLY: Simulate tampering by mutating a stored block field.
        Then run verification to demonstrate detection.
        """
        chain = self._chains.get(product_id)
        if not chain or block_index >= len(chain.chain):
            return {"error": "Block not found"}

        block = chain.chain[block_index]
        original = getattr(block, field, None)
        # Mutate the stored data (simulating an attacker editing the DB)
        setattr(block, field, new_value)
        # Do NOT recompute current_hash – attacker didn't know to update it
        report = chain.full_verification_report()
        # Restore
        setattr(block, field, original)
        return {
            "tamper_demo": True,
            "mutated_field": field,
            "report": report,
        }


# ---------------------------------------------------------------------------
# SHA-256 utility
# ---------------------------------------------------------------------------

def hash_payload(payload: Dict[str, Any]) -> str:
    """Produce a deterministic SHA-256 hash of any JSON-serialisable dict."""
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Module-level singleton (imported by FastAPI app)
# ---------------------------------------------------------------------------
blockchain_manager = BlockchainManager()
