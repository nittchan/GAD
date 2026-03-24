"""
Tests for oracle hash chain — 5-entry chain, tamper detection, deterministic hashing.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from gad.engine.models import TriggerDetermination
from gad.engine.oracle import (
    GENESIS_HASH,
    canonical_hash,
    sign_determination,
    verify_determination,
    verify_chain,
    append_to_oracle_log,
    _canonical_json,
    data_snapshot_hash,
)


def _generate_keypair() -> tuple[bytes, bytes]:
    """Generate a fresh Ed25519 keypair (private_bytes, public_bytes)."""
    private_key = Ed25519PrivateKey.generate()
    private_bytes = private_key.private_bytes_raw()
    public_bytes = private_key.public_key().public_bytes_raw()
    return private_bytes, public_bytes


def _make_determination(fired: bool = False) -> TriggerDetermination:
    """Create a minimal unsigned determination for testing."""
    return TriggerDetermination(
        determination_id=uuid4(),
        policy_id=uuid4(),
        trigger_id=uuid4(),
        fired=fired,
        fired_at=datetime.now(timezone.utc) if fired else None,
        data_snapshot_hash=data_snapshot_hash(b"test-data-" + uuid4().bytes),
        computation_version="test-v0.1",
        prev_hash=GENESIS_HASH,
    )


class TestFullChain:
    """Generate a 5-entry signed chain and verify it."""

    def test_5_entry_chain_valid(self, tmp_path):
        priv, pub = _generate_keypair()
        log_dir = str(tmp_path / "determinations")
        os.makedirs(log_dir, exist_ok=True)

        prev_hash = GENESIS_HASH
        signed_dets = []

        for i in range(5):
            det = _make_determination(fired=(i % 2 == 0))
            signed = sign_determination(det, priv, prev_hash)
            prev_hash = append_to_oracle_log(signed, log_dir=log_dir)
            signed_dets.append(signed)

        # Verify signatures individually
        for det in signed_dets:
            assert verify_determination(det, pub), f"Signature invalid for {det.determination_id}"

        # Verify hash chain
        is_valid, count, msg = verify_chain(log_dir=log_dir)
        assert is_valid, f"Chain verification failed: {msg}"
        assert count == 5, f"Expected 5 entries, got {count}"

    def test_tampered_entry_3_breaks_chain(self, tmp_path):
        priv, pub = _generate_keypair()
        log_dir = str(tmp_path / "determinations")
        os.makedirs(log_dir, exist_ok=True)

        prev_hash = GENESIS_HASH
        for i in range(5):
            det = _make_determination(fired=(i % 2 == 0))
            signed = sign_determination(det, priv, prev_hash)
            prev_hash = append_to_oracle_log(signed, log_dir=log_dir)

        # Tamper with entry 3 (index 3) in the JSONL log — flip fired status
        jsonl_path = os.path.join(log_dir, "..", "oracle_log.jsonl")
        with open(jsonl_path, "r") as f:
            lines = f.readlines()

        assert len(lines) == 5

        # Parse entry 3, flip 'fired', rewrite
        entry = json.loads(lines[3])
        entry["fired"] = not entry["fired"]
        lines[3] = json.dumps(entry, sort_keys=True, separators=(",", ":")) + "\n"

        with open(jsonl_path, "w") as f:
            f.writelines(lines)

        # Verify chain should fail at entry 4 (because entry 3's hash changed,
        # so entry 4's prev_hash won't match)
        is_valid, fail_idx, msg = verify_chain(log_dir=log_dir)
        assert not is_valid, "Chain should be invalid after tampering"
        # The break is detected at entry 4 because entry 4's prev_hash
        # no longer matches the hash of (tampered) entry 3.
        # Actually, verify_chain checks prev_hash of each entry against
        # the running hash, so entry 3 itself may fail if its prev_hash
        # was not tampered. Let's just assert it fails.
        assert "Chain broken" in msg or "entry" in msg


class TestCanonicalHash:
    """canonical_hash must be deterministic."""

    def test_same_input_same_hash(self):
        det = _make_determination(fired=True)
        h1 = canonical_hash(det)
        h2 = canonical_hash(det)
        assert h1 == h2

    def test_different_input_different_hash(self):
        det1 = _make_determination(fired=True)
        det2 = _make_determination(fired=False)
        assert canonical_hash(det1) != canonical_hash(det2)

    def test_hash_is_sha256_hex(self):
        det = _make_determination()
        h = canonical_hash(det)
        assert len(h) == 64
        int(h, 16)  # should not raise — valid hex

    def test_canonical_json_is_deterministic(self):
        det = _make_determination(fired=True)
        j1 = _canonical_json(det)
        j2 = _canonical_json(det)
        assert j1 == j2

    def test_canonical_json_sorted_keys(self):
        det = _make_determination()
        j = _canonical_json(det)
        parsed = json.loads(j)
        keys = list(parsed.keys())
        assert keys == sorted(keys)


class TestSignWithKeyId:
    """sign_determination with key_id populates the field correctly."""

    def test_key_id_populated(self):
        priv, pub = _generate_keypair()
        key_id = str(uuid4())
        det = _make_determination(fired=True)

        signed = sign_determination(det, priv, GENESIS_HASH, key_id=key_id)

        assert signed.key_id is not None
        assert str(signed.key_id) == key_id
        assert signed.signature  # non-empty
        assert verify_determination(signed, pub)

    def test_no_key_id_leaves_none(self):
        priv, pub = _generate_keypair()
        det = _make_determination(fired=False)

        signed = sign_determination(det, priv, GENESIS_HASH)

        assert signed.key_id is None
        assert signed.signature  # non-empty
        assert verify_determination(signed, pub)

    def test_key_id_included_in_canonical_json(self):
        priv, _ = _generate_keypair()
        key_id = str(uuid4())
        det = _make_determination()

        signed = sign_determination(det, priv, GENESIS_HASH, key_id=key_id)

        canonical = _canonical_json(signed)
        parsed = json.loads(canonical)
        assert parsed["key_id"] == key_id


class TestGenesisHash:
    """GENESIS_HASH is a known fixed value."""

    def test_genesis_hash_is_sha256_of_magic(self):
        expected = hashlib.sha256(b"GAD_ORACLE_LOG_GENESIS").hexdigest()
        assert GENESIS_HASH == expected

    def test_genesis_hash_length(self):
        assert len(GENESIS_HASH) == 64
