"""
Cache layer for the global monitor. All data sources write to a local JSON cache.
The dashboard reads ONLY from cache — never hits external APIs.

Security: Users cannot trigger API calls. Background workers pre-fetch and cache.
Cost: External API calls happen on a schedule, not per-user-request.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Optional

from gad.config import CACHE_DIR


def _ensure_cache_dir() -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR


def cache_key_path(source: str, key: str) -> Path:
    """Path for a cache entry. source=peril category, key=specific location/trigger."""
    safe_key = key.replace("/", "_").replace(" ", "_").lower()
    return _ensure_cache_dir() / f"{source}_{safe_key}.json"


def write_cache(source: str, key: str, data: Any, ttl_seconds: int = 3600) -> None:
    """Write data to cache with a TTL."""
    path = cache_key_path(source, key)
    entry = {
        "source": source,
        "key": key,
        "data": data,
        "cached_at": time.time(),
        "expires_at": time.time() + ttl_seconds,
    }
    path.write_text(json.dumps(entry, default=str), encoding="utf-8")


def read_cache(source: str, key: str) -> Optional[dict]:
    """
    Read from cache. Returns None if missing or expired.
    Expired entries return None — the dashboard shows 'data updating' instead.
    """
    path = cache_key_path(source, key)
    if not path.exists():
        return None
    try:
        entry = json.loads(path.read_text(encoding="utf-8"))
        if time.time() > entry.get("expires_at", 0):
            return None
        return entry.get("data")
    except (json.JSONDecodeError, KeyError):
        return None


def read_cache_with_staleness(source: str, key: str) -> tuple[Optional[dict], bool]:
    """
    Read from cache. Returns (data, is_stale).
    Stale data is still returned for display — better than nothing.
    """
    path = cache_key_path(source, key)
    if not path.exists():
        return None, True
    try:
        entry = json.loads(path.read_text(encoding="utf-8"))
        data = entry.get("data")
        is_stale = time.time() > entry.get("expires_at", 0)
        return data, is_stale
    except (json.JSONDecodeError, KeyError):
        return None, True


def list_cached_entries(source: str) -> list[dict]:
    """List all cached entries for a source, including stale ones."""
    _ensure_cache_dir()
    results = []
    for path in CACHE_DIR.glob(f"{source}_*.json"):
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
            entry["_is_stale"] = time.time() > entry.get("expires_at", 0)
            results.append(entry)
        except (json.JSONDecodeError, KeyError):
            continue
    return results


def clear_expired(max_age_hours: int = 48) -> int:
    """Remove cache files older than max_age_hours. Run periodically."""
    _ensure_cache_dir()
    cutoff = time.time() - (max_age_hours * 3600)
    removed = 0
    for path in CACHE_DIR.glob("*.json"):
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
            if entry.get("cached_at", 0) < cutoff:
                path.unlink()
                removed += 1
        except Exception:
            pass
    return removed
