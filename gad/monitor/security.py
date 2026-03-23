"""
Security utilities for the public-facing dashboard.

DDoS / cost protection strategy:
1. Cloudflare proxy (first line) — rate limiting, bot detection, DDoS mitigation
2. Streamlit server resource limits — max connections, memory caps
3. Cache-only reads — users NEVER trigger API calls
4. No user-submitted data processed on the public map page
5. Rate limiting at the application level for any future API endpoints

Cost protection:
- External API calls happen ONLY in the background fetcher (cron)
- The fetcher runs on a fixed schedule regardless of user traffic
- Even 10,000 concurrent users cost nothing more in API calls than 1 user
- Fly.io auto-scaling is capped (see fly.toml)
"""

from __future__ import annotations

import hashlib
import os
import time
from functools import wraps
from typing import Any, Callable


# ── Rate Limiter (in-memory, per-process) ──
# Used for any future API endpoints, NOT for the dashboard pages

class RateLimiter:
    """Simple token bucket rate limiter. Thread-safe enough for Streamlit."""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self._requests: dict[str, list[float]] = {}

    def is_allowed(self, key: str) -> bool:
        """Check if a request is allowed for the given key."""
        now = time.time()
        if key not in self._requests:
            self._requests[key] = []

        # Clean old entries
        self._requests[key] = [t for t in self._requests[key] if now - t < self.window]

        if len(self._requests[key]) >= self.max_requests:
            return False

        self._requests[key].append(now)
        return True


# Global rate limiter instance
_limiter = RateLimiter(max_requests=60, window_seconds=60)


def rate_limit(key: str) -> bool:
    """Check rate limit. Returns True if allowed, False if throttled."""
    return _limiter.is_allowed(key)


# ── Content Security ──

def sanitize_user_input(text: str, max_length: int = 1000) -> str:
    """Sanitize any user-provided text. Strip HTML, limit length."""
    if not isinstance(text, str):
        return ""
    # Strip HTML tags
    import re
    clean = re.sub(r"<[^>]+>", "", text)
    # Limit length
    return clean[:max_length].strip()


# ── API Key Management ──

def get_api_key(name: str) -> str | None:
    """Get an API key from environment. Never expose in client-side code."""
    return os.environ.get(name)


def mask_key(key: str) -> str:
    """Mask an API key for logging (show first 4 and last 4 chars)."""
    if not key or len(key) < 12:
        return "****"
    return f"{key[:4]}...{key[-4:]}"
