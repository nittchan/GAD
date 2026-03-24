#!/usr/bin/env python3
"""
Publish oracle-keys.json to Cloudflare R2.

Reads GAD_ORACLE_PUBLIC_KEY_HEX and GAD_ORACLE_KEY_ID from environment,
builds the key registry JSON, and uploads to the gad-oracle-determinations
R2 bucket. The Cloudflare Worker serves this at:
  https://oracle.parametricdata.io/.well-known/oracle-keys.json

Required env vars:
  GAD_ORACLE_PUBLIC_KEY_HEX — Ed25519 public key (hex)
  GAD_ORACLE_KEY_ID — UUID for the key
  R2_ACCOUNT_ID — Cloudflare account ID
  R2_ACCESS_KEY_ID — R2 API token access key
  R2_SECRET_ACCESS_KEY — R2 API token secret key

Optional:
  R2_BUCKET_NAME — defaults to "gad-oracle-determinations"
  ORACLE_KEY_VALID_FROM — ISO 8601 start date (default: today)
  ORACLE_KEY_VALID_UNTIL — ISO 8601 end date (default: 90 days from today)

Usage:
    python3 scripts/publish_oracle_key.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone

try:
    import boto3
except ImportError:
    print("ERROR: boto3 is required. Install with: pip install boto3")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def main() -> None:
    pub_hex = os.environ.get("GAD_ORACLE_PUBLIC_KEY_HEX")
    key_id = os.environ.get("GAD_ORACLE_KEY_ID")

    if not pub_hex or not key_id:
        print("ERROR: GAD_ORACLE_PUBLIC_KEY_HEX and GAD_ORACLE_KEY_ID must be set.")
        sys.exit(1)

    for var in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY"):
        if not os.environ.get(var):
            print(f"ERROR: {var} must be set.")
            sys.exit(1)

    now = datetime.now(timezone.utc)
    valid_from = os.environ.get(
        "ORACLE_KEY_VALID_FROM",
        now.strftime("%Y-%m-%dT00:00:00Z"),
    )
    valid_until = os.environ.get(
        "ORACLE_KEY_VALID_UNTIL",
        (now + timedelta(days=90)).strftime("%Y-%m-%dT23:59:59Z"),
    )

    keys_payload = {
        "keys": [
            {
                "key_id": key_id,
                "algorithm": "Ed25519",
                "public_key_hex": pub_hex,
                "valid_from": valid_from,
                "valid_until_inclusive": valid_until,
                "revoked": False,
            }
        ]
    }

    body = json.dumps(keys_payload, indent=2)
    print(f"Key registry payload:\n{body}\n")

    s3 = boto3.client(
        "s3",
        endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )

    bucket = os.environ.get("R2_BUCKET_NAME", "gad-oracle-determinations")
    s3.put_object(
        Bucket=bucket,
        Key="oracle-keys.json",
        Body=body.encode(),
        ContentType="application/json",
    )

    print(f"Uploaded oracle-keys.json to R2 bucket '{bucket}'")
    print("Accessible at: https://oracle.parametricdata.io/.well-known/oracle-keys.json")


if __name__ == "__main__":
    main()
