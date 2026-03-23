"""
Verify an oracle determination from a URL or local file.

Usage:
    python -m gad.verify https://oracle.parametricdata.io/determination/{uuid}
    python -m gad.verify determination.json
    python -m gad.verify --chain registry/     # verify the full JSONL log
"""

from __future__ import annotations

import json
import sys

import httpx

from gad.engine.models import TriggerDetermination
from gad.engine.oracle import verify_determination, verify_chain


def _fetch_determination(source: str) -> dict:
    """Fetch determination from URL or local file."""
    if source.startswith("http://") or source.startswith("https://"):
        url = source if "format=json" in source else f"{source}?format=json"
        resp = httpx.get(url, timeout=15)
        resp.raise_for_status()
        return resp.json()
    else:
        with open(source) as f:
            return json.load(f)


def _fetch_public_key(key_registry_url: str, key_id: str | None = None) -> bytes | None:
    """Fetch public key from the key registry."""
    try:
        resp = httpx.get(key_registry_url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        keys = data.get("keys", [])
        if not keys:
            return None
        if key_id:
            for k in keys:
                if k.get("key_id") == key_id:
                    return bytes.fromhex(k["public_key_hex"])
        # Return first key if no key_id specified
        return bytes.fromhex(keys[0]["public_key_hex"])
    except Exception:
        return None


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m gad.verify <url-or-file>")
        print("  python -m gad.verify --chain <log-dir>")
        print()
        print("Examples:")
        print("  python -m gad.verify https://oracle.parametricdata.io/determination/{uuid}")
        print("  python -m gad.verify determination.json")
        print("  python -m gad.verify --chain registry/")
        sys.exit(1)

    # Chain verification mode
    if sys.argv[1] == "--chain":
        log_dir = sys.argv[2] if len(sys.argv) > 2 else None
        is_valid, count, msg = verify_chain(log_dir)
        if is_valid:
            print(f"CHAIN VALID — {count} entries verified")
        else:
            print(f"CHAIN BROKEN — {msg}")
            sys.exit(1)
        sys.exit(0)

    # Single determination verification
    source = sys.argv[1]
    print(f"Fetching determination from: {source}")

    try:
        det_json = _fetch_determination(source)
    except Exception as e:
        print(f"ERROR: Could not fetch determination: {e}")
        sys.exit(1)

    try:
        det = TriggerDetermination(**det_json)
    except Exception as e:
        print(f"ERROR: Invalid determination format: {e}")
        sys.exit(1)

    print(f"  Determination ID: {det.determination_id}")
    print(f"  Trigger ID:       {det.trigger_id}")
    print(f"  Fired:            {det.fired}")
    print(f"  Determined at:    {det.determined_at}")
    print(f"  Signature:        {det.signature[:20]}..." if det.signature else "  Signature:        (unsigned)")
    print(f"  Key ID:           {det.key_id}" if det.key_id else "  Key ID:           (none)")
    print(f"  Prev hash:        {det.prev_hash[:20]}...")
    print()

    if not det.signature:
        print("UNSIGNED — This is a v0.1 determination (no signature).")
        print("Verification not applicable for unsigned determinations.")
        sys.exit(0)

    # Try to fetch public key from key registry
    key_registry = "https://oracle.parametricdata.io/.well-known/oracle-keys.json"
    print(f"Fetching public key from: {key_registry}")

    key_id_str = str(det.key_id) if det.key_id else None
    public_key = _fetch_public_key(key_registry, key_id_str)

    if not public_key:
        print("WARNING: Could not fetch public key from registry.")
        print("Provide the public key hex manually:")
        print("  python -c \"from gad.verify import verify_determination; ...\"")
        sys.exit(1)

    result = verify_determination(det, public_key)
    if result:
        print("VERIFIED — Signature is valid.")
    else:
        print("FAILED — Signature does not match.")
        sys.exit(1)


if __name__ == "__main__":
    main()
