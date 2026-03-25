"""
Oracle signing and verification. Ed25519; canonical payload; append-only log.
Supports both per-file JSON (for Cloudflare Worker) and JSONL (for hash chain).
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from gad.config import ORACLE_DIR, ORACLE_LOG_DIR
from gad.engine.models import TriggerDetermination

ORACLE_LOG_PATH = str(ORACLE_LOG_DIR)
ORACLE_JSONL_PATH = str(ORACLE_DIR / "oracle_log.jsonl")

# Genesis hash — the prev_hash for the very first determination in the log.
# This is a fixed constant. Do NOT change it after the first determination is written.
GENESIS_HASH = hashlib.sha256(b"GAD_ORACLE_LOG_GENESIS").hexdigest()


def _load_private_key() -> bytes | None:
    hex_key = os.getenv("GAD_ORACLE_PRIVATE_KEY_HEX")
    if not hex_key:
        return None
    return bytes.fromhex(hex_key)


def _load_public_key() -> bytes | None:
    hex_key = os.getenv("GAD_ORACLE_PUBLIC_KEY_HEX")
    if not hex_key:
        return None
    return bytes.fromhex(hex_key)


def data_snapshot_hash(raw_bytes: bytes) -> str:
    """SHA-256 of the raw API response. Pin this before any parsing."""
    return hashlib.sha256(raw_bytes).hexdigest()


def _canonical_json(det: TriggerDetermination) -> bytes:
    """
    Canonical JSON for signing and hashing.
    Excludes 'signature' — you sign everything else.
    Sorted keys, no whitespace — deterministic across implementations.
    """
    payload = {
        "determination_id": str(det.determination_id),
        "policy_id": str(det.policy_id),
        "trigger_id": str(det.trigger_id),
        "fired": det.fired,
        "fired_at": det.fired_at.isoformat() if det.fired_at else None,
        "data_snapshot_hash": det.data_snapshot_hash,
        "computation_version": det.computation_version,
        "determined_at": det.determined_at.isoformat(),
        "prev_hash": det.prev_hash,
        "key_id": str(det.key_id) if det.key_id else None,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


# Keep old name for backward compatibility
_determination_payload = _canonical_json


def sign_determination(
    det: TriggerDetermination,
    private_key_bytes: bytes,
    prev_determination_hash: str,
    key_id: str | None = None,
) -> TriggerDetermination:
    """
    Signs a TriggerDetermination with Ed25519.
    Returns a new TriggerDetermination with signature, prev_hash, and key_id populated.
    """
    updates = {"prev_hash": prev_determination_hash}
    if key_id:
        from uuid import UUID
        updates["key_id"] = UUID(key_id)

    det_with_chain = det.model_copy(update=updates)
    payload = _canonical_json(det_with_chain)
    private_key = Ed25519PrivateKey.from_private_bytes(private_key_bytes)
    sig = private_key.sign(payload).hex()
    return det_with_chain.model_copy(update={"signature": sig})


def verify_determination(
    det: TriggerDetermination,
    public_key_bytes: bytes,
) -> bool:
    """
    Verifies a TriggerDetermination signature.
    Returns True if valid, False if signature does not match.
    An empty signature (v0.1 unsigned) always returns False.
    """
    if not det.signature:
        return False
    payload = _canonical_json(det)
    public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
    try:
        public_key.verify(bytes.fromhex(det.signature), payload)
        return True
    except InvalidSignature:
        return False


def canonical_hash(det: TriggerDetermination) -> str:
    """SHA-256 of the canonical JSON. Used as prev_hash for the next determination."""
    return hashlib.sha256(_canonical_json(det)).hexdigest()


def append_to_oracle_log(det: TriggerDetermination, log_dir: str | None = None) -> str:
    """
    Dual write: per-file JSON (for Cloudflare Worker) + JSONL (for hash chain).
    Returns the canonical hash — use as prev_hash for the next determination.
    """
    base = log_dir or ORACLE_LOG_PATH
    os.makedirs(base, exist_ok=True)

    # 1. Per-file JSON (pretty-printed, for Worker reads)
    json_path = os.path.join(base, f"{det.determination_id}.json")
    pretty_json = det.model_dump_json(indent=2)
    with open(json_path, "w") as f:
        f.write(pretty_json)

    # 2. JSONL append (canonical JSON, for hash chain — source of truth)
    jsonl_path = os.path.join(base, "..", "oracle_log.jsonl")
    canonical = _canonical_json(det).decode("utf-8")
    with open(jsonl_path, "a") as f:
        f.write(canonical + "\n")

    # Return canonical hash (not hash of pretty JSON)
    return canonical_hash(det)


def read_last_hash(log_dir: str | None = None) -> str:
    """
    Read the hash of the last entry in the JSONL log.
    Returns GENESIS_HASH if the log is empty or doesn't exist.
    """
    base = log_dir or ORACLE_LOG_PATH
    jsonl_path = os.path.join(base, "..", "oracle_log.jsonl")
    if not os.path.exists(jsonl_path):
        return GENESIS_HASH

    try:
        with open(jsonl_path, "rb") as f:
            # Read last non-empty line
            f.seek(0, 2)  # end of file
            pos = f.tell()
            if pos == 0:
                return GENESIS_HASH
            # Walk backwards to find last newline
            while pos > 0:
                pos -= 1
                f.seek(pos)
                if f.read(1) == b"\n" and pos < f.seek(0, 2) - 1:
                    break
            if pos > 0:
                f.seek(pos + 1)
            else:
                f.seek(0)
            last_line = f.readline().strip()
            if not last_line:
                return GENESIS_HASH
            return hashlib.sha256(last_line).hexdigest()
    except Exception:
        return GENESIS_HASH


def verify_chain(log_dir: str | None = None) -> tuple[bool, int, str]:
    """
    Verify the JSONL oracle log hash chain.
    Returns (is_valid, entry_count, error_message).
    """
    base = log_dir or ORACLE_LOG_PATH
    jsonl_path = os.path.join(base, "..", "oracle_log.jsonl")
    if not os.path.exists(jsonl_path):
        return True, 0, "Log empty"

    try:
        with open(jsonl_path, "r") as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]

        if not lines:
            return True, 0, "Log empty"

        prev_hash = GENESIS_HASH
        for i, line in enumerate(lines):
            entry = json.loads(line)
            if entry.get("prev_hash") != prev_hash:
                return False, i, f"Chain broken at entry {i}: expected prev_hash={prev_hash[:16]}..."
            prev_hash = hashlib.sha256(line.encode("utf-8")).hexdigest()

        return True, len(lines), "Chain valid"
    except Exception as e:
        return False, 0, f"Verification error: {e}"
