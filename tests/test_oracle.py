"""Round-trip sign/verify and tamper detection."""

from datetime import datetime, timezone
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from gad.engine import sign_determination, verify_determination
from gad.engine.models import TriggerDetermination


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
