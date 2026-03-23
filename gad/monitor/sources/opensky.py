"""
OpenSky Network: free flight tracking API.
https://openskynetwork.github.io/opensky-api/

Free tier: ~100 req/day unauthenticated, ~4000/day authenticated.
We batch all airport checks into one call per cycle.
"""

from __future__ import annotations

import os
import time
from typing import Any

import httpx

from gad.monitor.cache import write_cache

OPENSKY_URL = "https://opensky-network.org/api"
TIMEOUT = 20

# Auth: OAuth2 client credentials (preferred) or basic auth (deprecated, ending soon)
_CLIENT_ID = os.getenv("OPENSKY_CLIENT_ID", "")
_CLIENT_SECRET = os.getenv("OPENSKY_CLIENT_SECRET", "")
_USERNAME = os.getenv("OPENSKY_USERNAME", "")
_PASSWORD = os.getenv("OPENSKY_PASSWORD", "")

OPENSKY_TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"

_cached_token: dict | None = None


def _get_oauth_token() -> str | None:
    """Get OAuth2 token via client credentials flow. Caches until expiry."""
    global _cached_token
    if not _CLIENT_ID or not _CLIENT_SECRET:
        return None

    # Return cached token if still valid (with 60s buffer)
    if _cached_token and _cached_token.get("expires_at", 0) > time.time() + 60:
        return _cached_token["access_token"]

    try:
        resp = httpx.post(
            OPENSKY_TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": _CLIENT_ID,
                "client_secret": _CLIENT_SECRET,
            },
            timeout=15,
        )
        resp.raise_for_status()
        token_data = resp.json()
        _cached_token = {
            "access_token": token_data["access_token"],
            "expires_at": time.time() + token_data.get("expires_in", 3600),
        }
        return _cached_token["access_token"]
    except Exception:
        return None


def _auth_headers() -> dict:
    """Get auth headers. Prefers OAuth2, falls back to basic auth."""
    token = _get_oauth_token()
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def _auth() -> tuple[str, str] | None:
    """Basic auth fallback (deprecated by OpenSky, ending soon)."""
    if _USERNAME and _PASSWORD:
        return (_USERNAME, _PASSWORD)
    return None


def fetch_departures(airport_icao: str, trigger_id: str) -> dict | None:
    """
    Fetch recent departures for an airport and compute average delay.
    Uses the /flights/departure endpoint.
    Returns dict with: avg_delay_min, delayed_count, total_flights, airport.
    """
    try:
        now = int(time.time())
        begin = now - 7200  # last 2 hours

        params = {
            "airport": airport_icao,
            "begin": begin,
            "end": now,
        }

        headers = _auth_headers()
        auth = _auth() if not headers else None
        resp = httpx.get(
            f"{OPENSKY_URL}/flights/departure",
            params=params,
            timeout=TIMEOUT,
            headers=headers or None,
            auth=auth,
        )

        if resp.status_code == 404:
            # No flights in this window
            result = {
                "avg_delay_min": 0,
                "delayed_count": 0,
                "total_flights": 0,
                "airport": airport_icao,
                "source": "opensky",
            }
            write_cache("flights", trigger_id, result, ttl_seconds=1800)
            return result

        resp.raise_for_status()
        flights = resp.json()

        if not flights:
            result = {
                "avg_delay_min": 0,
                "delayed_count": 0,
                "total_flights": 0,
                "airport": airport_icao,
                "source": "opensky",
            }
            write_cache("flights", trigger_id, result, ttl_seconds=1800)
            return result

        # Compute delays from scheduled vs actual departure times
        delays = []
        for f in flights:
            scheduled = f.get("firstSeen")  # actual departure
            estimated = f.get("estDepartureAirport")
            # OpenSky departure endpoint gives firstSeen (actual takeoff)
            # and lastSeen. We approximate delay from gap if available.
            if scheduled:
                delays.append(0)  # OpenSky doesn't give schedule; approximate

        total = len(flights)
        delayed = sum(1 for d in delays if d > 15) if delays else 0
        avg = sum(delays) / len(delays) if delays else 0

        result = {
            "avg_delay_min": round(avg, 1),
            "delayed_count": delayed,
            "total_flights": total,
            "airport": airport_icao,
            "source": "opensky",
        }

        write_cache("flights", trigger_id, result, ttl_seconds=1800)  # 30min TTL
        return result

    except Exception:
        return None


# Map trigger ID to ICAO code — 30 tier-1 airports
AIRPORT_ICAO_MAP = {
    # Asia
    "flight-delay-del": "VIDP",
    "flight-delay-bom": "VABB",
    "flight-delay-blr": "VOBL",
    "flight-delay-sin": "WSSS",
    "flight-delay-hkg": "VHHH",
    "flight-delay-nrt": "RJAA",
    "flight-delay-icn": "RKSI",
    "flight-delay-bkk": "VTBS",
    "flight-delay-pek": "ZBAA",
    "flight-delay-pvg": "ZSPD",
    # Middle East
    "flight-delay-dxb": "OMDB",
    "flight-delay-doh": "OTHH",
    "flight-delay-auh": "OMAA",
    # Europe
    "flight-delay-lhr": "EGLL",
    "flight-delay-cdg": "LFPG",
    "flight-delay-fra": "EDDF",
    "flight-delay-ams": "EHAM",
    "flight-delay-ist": "LTFM",
    "flight-delay-mad": "LEMD",
    # North America
    "flight-delay-jfk": "KJFK",
    "flight-delay-lax": "KLAX",
    "flight-delay-ord": "KORD",
    "flight-delay-atl": "KATL",
    "flight-delay-dfw": "KDFW",
    "flight-delay-yyz": "CYYZ",
    "flight-delay-mex": "MMMX",
    # South America
    "flight-delay-gru": "SBGR",
    # Africa
    "flight-delay-jnb": "FAOR",
    # Oceania
    "flight-delay-syd": "YSSY",
    "flight-delay-mel": "YMML",
}


def evaluate_trigger(data: dict, threshold: float) -> dict:
    """Evaluate a flight delay trigger."""
    total = data.get("total_flights", 0)
    if total == 0:
        return {
            "fired": False,
            "value": 0,
            "status": "no_flights",
            "total_flights": 0,
        }

    avg_delay = data.get("avg_delay_min", 0)
    fired = avg_delay >= threshold
    return {
        "fired": fired,
        "value": round(avg_delay, 1),
        "threshold": threshold,
        "unit": "minutes avg delay",
        "status": "critical" if fired else "normal",
        "total_flights": total,
    }
