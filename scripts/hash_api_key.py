"""Generate hashed API key for CF Workers KV storage."""
import hashlib
import secrets
import json
import sys


def generate_api_key():
    key = f"pk_{secrets.token_hex(24)}"
    hashed = hashlib.sha256(key.encode()).hexdigest()
    print(f"API Key (give to user):  {key}")
    print(f"SHA-256 hash (store in KV): {hashed}")
    print(f"\nKV entry: {json.dumps({'hash': hashed, 'tier': 'free', 'user_id': 'user-uuid-here'})}")
    return key, hashed


if __name__ == "__main__":
    generate_api_key()
