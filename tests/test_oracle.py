"""Round-trip sign/verify, tamper detection, and hash chain genesis."""

import os
import tempfile
from datetime import datetime, timezone
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from gad.engine import sign_determination, verify_determination
from gad.engine.models import TriggerDetermination
from gad.engine.oracle import (
    GENESIS_HASH,
    append_to_oracle_log,
    read_last_hash,
    verify_chain,
)


def test_verify_determination_round_trip():
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    private_bytes = private_key.private_bytes_raw()
    public_bytes = public_key.public_bytes_raw()

    det = TriggerDetermination(
        determination_id=uuid4(),
        policy_id=uuid4(),
        trigger_id=uuid4(),
        fired=True,
        fired_at=datetime.now(timezone.utc),
        data_snapshot_hash="a" * 64,
        computation_version="abc123",
        determined_at=datetime.now(timezone.utc),
        prev_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        signature="",
    )
    signed = sign_determination(det, private_bytes, det.prev_hash)
    assert signed.signature
    assert verify_determination(signed, public_bytes) is True


def test_verify_determination_tampered_returns_false():
    private_key = Ed25519PrivateKey.generate()
    public_bytes = private_key.public_key().public_bytes_raw()
    private_bytes = private_key.private_bytes_raw()

    det = TriggerDetermination(
        determination_id=uuid4(),
        policy_id=uuid4(),
        trigger_id=uuid4(),
        fired=True,
        fired_at=datetime.now(timezone.utc),
        data_snapshot_hash="a" * 64,
        computation_version="abc123",
        determined_at=datetime.now(timezone.utc),
        prev_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        signature="",
    )
    signed = sign_determination(det, private_bytes, det.prev_hash)
    tampered = signed.model_copy(update={"fired": False})
    assert verify_determination(tampered, public_bytes) is False


def test_verify_determination_empty_signature_returns_false():
    det = TriggerDetermination(
        determination_id=uuid4(),
        policy_id=uuid4(),
        trigger_id=uuid4(),
        fired=True,
        fired_at=None,
        data_snapshot_hash="a" * 64,
        computation_version="abc123",
        determined_at=datetime.now(timezone.utc),
        prev_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        signature="",
    )
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    pub = Ed25519PrivateKey.generate().public_key().public_bytes_raw()
    assert verify_determination(det, pub) is False


def _make_det(**overrides) -> TriggerDetermination:
    defaults = dict(
        determination_id=uuid4(), policy_id=uuid4(), trigger_id=uuid4(),
        fired=True, fired_at=datetime.now(timezone.utc),
        data_snapshot_hash="a" * 64, computation_version="test",
        determined_at=datetime.now(timezone.utc), prev_hash="", signature="",
    )
    defaults.update(overrides)
    return TriggerDetermination(**defaults)


def test_read_last_hash_returns_genesis_for_empty_log():
    """BUG-04a: empty log must return GENESIS_HASH, not None or empty string."""
    tmpdir = tempfile.mkdtemp()
    log_dir = os.path.join(tmpdir, "determinations")
    os.makedirs(log_dir)
    assert read_last_hash(log_dir) == GENESIS_HASH


def test_first_entry_uses_genesis_hash():
    """BUG-04a: first signed determination must have prev_hash == GENESIS_HASH."""
    priv = Ed25519PrivateKey.generate()
    priv_bytes = priv.private_bytes_raw()
    key_id = str(uuid4())

    tmpdir = tempfile.mkdtemp()
    log_dir = os.path.join(tmpdir, "determinations")
    os.makedirs(log_dir)

    prev = read_last_hash(log_dir)
    det = _make_det()
    signed = sign_determination(det, priv_bytes, prev, key_id)

    assert signed.prev_hash == GENESIS_HASH


def test_verify_chain_checks_genesis():
    """BUG-04b: verify_chain must validate first entry's prev_hash == GENESIS_HASH."""
    priv = Ed25519PrivateKey.generate()
    priv_bytes = priv.private_bytes_raw()
    key_id = str(uuid4())

    tmpdir = tempfile.mkdtemp()
    log_dir = os.path.join(tmpdir, "determinations")
    os.makedirs(log_dir)

    # Write 3 chained determinations
    prev = read_last_hash(log_dir)
    for _ in range(3):
        det = _make_det()
        signed = sign_determination(det, priv_bytes, prev, key_id)
        prev = append_to_oracle_log(signed, log_dir)

    valid, count, msg = verify_chain(log_dir)
    assert valid is True
    assert count == 3


def test_verify_chain_detects_broken_genesis():
    """BUG-04b: chain must fail if first entry has wrong prev_hash."""
    import json

    tmpdir = tempfile.mkdtemp()
    log_dir = os.path.join(tmpdir, "determinations")
    os.makedirs(log_dir)
    jsonl_path = os.path.join(log_dir, "..", "oracle_log.jsonl")

    # Write a fake entry with wrong prev_hash
    bad_entry = {
        "determination_id": str(uuid4()),
        "policy_id": str(uuid4()),
        "trigger_id": str(uuid4()),
        "fired": True,
        "fired_at": datetime.now(timezone.utc).isoformat(),
        "data_snapshot_hash": "a" * 64,
        "computation_version": "test",
        "determined_at": datetime.now(timezone.utc).isoformat(),
        "prev_hash": "0000000000000000000000000000000000000000000000000000000000000000",
        "key_id": None,
    }
    with open(jsonl_path, "w") as f:
        f.write(json.dumps(bad_entry, sort_keys=True, separators=(",", ":")) + "\n")

    valid, count, msg = verify_chain(log_dir)
    assert valid is False
    assert "Chain broken" in msg
