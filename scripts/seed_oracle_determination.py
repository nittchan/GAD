"""
Run once to publish the first signed oracle determination to R2.

Usage:
    python scripts/seed_oracle_determination.py
"""

from __future__ import annotations

import json
import os
import subprocess
import uuid
from datetime import datetime, timezone

import boto3
from dotenv import load_dotenv

from gad.engine.models import DataSourceProvenance, TriggerDef, TriggerDetermination
from gad.engine.oracle import (
    GENESIS_HASH,
    append_to_oracle_log,
    data_snapshot_hash,
    sign_determination,
)


def main() -> None:
    load_dotenv()

    trigger = TriggerDef(
        trigger_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        name="Kenya Drought - Marsabit (Demo)",
        description=(
            "Parametric drought trigger: payout when 30-day cumulative CHIRPS "
            "rainfall at Marsabit falls below 50mm."
        ),
        peril="drought",
        threshold=50.0,
        threshold_unit="mm rainfall in 30 days",
        data_source="CHIRPS v2.0",
        geography={"type": "Point", "coordinates": [37.9899, 2.3284]},
        provenance=DataSourceProvenance(
            primary_source="CHIRPS v2.0",
            primary_url="https://data.chc.ucsb.edu/products/CHIRPS-2.0/",
            max_data_latency_seconds=86400,
            historical_years_available=40,
        ),
        is_public=True,
    )

    raw_observation = (
        b'{"source":"CHIRPS-2.0","lat":2.3284,"lon":37.9899,'
        b'"month":"2023-11","rainfall_mm":31.4}'
    )
    snapshot_hash = data_snapshot_hash(raw_observation)

    try:
        git_hash = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        git_hash = "0.1.0"

    det = TriggerDetermination(
        policy_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        trigger_id=trigger.trigger_id,
        fired=True,
        fired_at=datetime(2023, 11, 30, tzinfo=timezone.utc),
        data_snapshot_hash=snapshot_hash,
        computation_version=git_hash,
        determined_at=datetime(2023, 11, 30, 6, 0, 0, tzinfo=timezone.utc),
        prev_hash=GENESIS_HASH,
        signature="",
    )

    private_key_hex = os.environ["GAD_ORACLE_PRIVATE_KEY_HEX"]
    private_key_bytes = bytes.fromhex(private_key_hex)
    signed_det = sign_determination(det, private_key_bytes, det.prev_hash)

    print(f"Determination ID: {signed_det.determination_id}")
    print(f"Signature: {signed_det.signature[:32]}...")

    local_hash = append_to_oracle_log(signed_det)
    print(f"Written locally. Hash: {local_hash}")

    s3 = boto3.client(
        "s3",
        endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )

    bucket = os.environ.get("R2_BUCKET_NAME", "gad-oracle-determinations")
    det_key = f"determinations/{signed_det.determination_id}.json"
    s3.put_object(
        Bucket=bucket,
        Key=det_key,
        Body=signed_det.model_dump_json(indent=2).encode(),
        ContentType="application/json",
    )
    print(f"Uploaded to R2: {det_key}")

    key_id = os.environ["GAD_ORACLE_KEY_ID"]
    pub_key_hex = os.environ["GAD_ORACLE_PUBLIC_KEY_HEX"]
    keys_payload = {
        "keys": [
            {
                "key_id": key_id,
                "algorithm": "Ed25519",
                "public_key_hex": pub_key_hex,
                "valid_from": "2026-04-01T00:00:00Z",
                "valid_until_inclusive": "2026-06-30T23:59:59Z",
                "revoked": False,
            }
        ]
    }
    s3.put_object(
        Bucket=bucket,
        Key="oracle-keys.json",
        Body=json.dumps(keys_payload, indent=2).encode(),
        ContentType="application/json",
    )

    print("Uploaded oracle-keys.json")
    print("=== URLS ===")
    print(f"https://oracle.parametricdata.io/determination/{signed_det.determination_id}")
    print("https://oracle.parametricdata.io/.well-known/oracle-keys.json")
    print("https://oracle.parametricdata.io")


if __name__ == "__main__":
    main()
