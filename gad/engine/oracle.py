"""
Oracle signing and verification. Ed25519; canonical payload; append-only log.
"""

from __future__ import annotations

import hashlib
import json
import os

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from gad.engine.models import TriggerDetermination

ORACLE_LOG_PATH = "registry/determinations"


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


def _determination_payload(det: TriggerDetermination) -> bytes:
    """
    Canonical JSON payload for signing.
    Excludes 'signature' field by design — you sign everything else.
    Field order is sorted — never rely on insertion order.
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
    }
    return json.dumps(payload, sort_keys=True).encode("utf-8")


def sign_determination(
    det: TriggerDetermination,
    private_key_bytes: bytes,
    prev_determination_hash: str,
) -> TriggerDetermination:
    """
    Signs a TriggerDetermination with Ed25519.
    Returns a new TriggerDetermination with signature and prev_hash populated.
    """
    det_with_chain = det.model_copy(update={"prev_hash": prev_determination_hash})
    payload = _determination_payload(det_with_chain)
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
    An empty signature (v0.1 unsigned) always returns False — do not treat as valid.
    """
    if not det.signature:
        return False
    payload = _determination_payload(det)
    public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
    try:
        public_key.verify(bytes.fromhex(det.signature), payload)
        return True
    except InvalidSignature:
        return False


def append_to_oracle_log(det: TriggerDetermination, log_dir: str | None = None) -> str:
    """
    Writes a determination to the local oracle log (flat JSON files in v0.1).
    Returns the SHA-256 hash of the written determination — use as prev_hash for next.
    log_dir defaults to ORACLE_LOG_PATH relative to cwd; in production writes to R2 via Worker.
    """
    base = log_dir or ORACLE_LOG_PATH
    os.makedirs(base, exist_ok=True)
    path = os.path.join(base, f"{det.determination_id}.json")
    content = det.model_dump_json(indent=2)
    with open(path, "w") as f:
        f.write(content)
    return hashlib.sha256(content.encode()).hexdigest()
