#!/usr/bin/env python3
"""
Generate an Ed25519 key pair for oracle signing.

Prints the private key, public key, and key ID. Set these as environment
variables (or Fly.io secrets) — NEVER commit them to the repository.

Usage:
    python3 scripts/generate_oracle_keypair.py

Then set on Fly.io:
    fly secrets set GAD_ORACLE_PRIVATE_KEY_HEX=<private_hex>
    fly secrets set GAD_ORACLE_PUBLIC_KEY_HEX=<public_hex>
    fly secrets set GAD_ORACLE_KEY_ID=<key_id>
"""

import uuid

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)


def main() -> None:
    priv = Ed25519PrivateKey.generate()
    priv_hex = priv.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()).hex()
    pub_hex = priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
    key_id = str(uuid.uuid4())

    print("=== Ed25519 Oracle Key Pair ===")
    print(f"GAD_ORACLE_PRIVATE_KEY_HEX={priv_hex}")
    print(f"GAD_ORACLE_PUBLIC_KEY_HEX={pub_hex}")
    print(f"GAD_ORACLE_KEY_ID={key_id}")
    print()
    print("Set these as Fly.io secrets (staging + production):")
    print(f"  fly secrets set GAD_ORACLE_PRIVATE_KEY_HEX={priv_hex} --app gad-dashboard-staging")
    print(f"  fly secrets set GAD_ORACLE_PUBLIC_KEY_HEX={pub_hex} --app gad-dashboard-staging")
    print(f"  fly secrets set GAD_ORACLE_KEY_ID={key_id} --app gad-dashboard-staging")
    print()
    print(f"  fly secrets set GAD_ORACLE_PRIVATE_KEY_HEX={priv_hex} --app gad-dashboard")
    print(f"  fly secrets set GAD_ORACLE_PUBLIC_KEY_HEX={pub_hex} --app gad-dashboard")
    print(f"  fly secrets set GAD_ORACLE_KEY_ID={key_id} --app gad-dashboard")
    print()
    print("NEVER commit these values to the repository.")


if __name__ == "__main__":
    main()
