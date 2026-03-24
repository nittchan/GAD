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
    Fetch recent departures for an airport.
    Uses the /flights/departure endpoint.

    OpenSky provides observed departure times (firstSeen/lastSeen) but NOT
    scheduled times, so actual delay cannot be computed. The useful metric
    from OpenSky is departure count — 0 departures in 2 hours indicates
    airport disruption.

    Returns dict with: departure_count, total_flights, airport, source.
    avg_delay_min is None (unknown from OpenSky).
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
            # No flights in this window — potential disruption
            result = {
                "avg_delay_min": None,
                "departure_count": 0,
                "total_flights": 0,
                "airport": airport_icao,
                "source": "opensky",
            }
            write_cache("flights", trigger_id, result, ttl_seconds=1800)
            return result

        resp.raise_for_status()
        flights = resp.json()

        total = len(flights) if flights else 0

        result = {
            "avg_delay_min": None,  # OpenSky cannot compute delay (no scheduled times)
            "departure_count": total,
            "total_flights": total,
            "airport": airport_icao,
            "source": "opensky",
        }

        write_cache("flights", trigger_id, result, ttl_seconds=1800)  # 30min TTL
        return result

    except Exception:
        return None


# Auto-generate ICAO map from airport registry
def _build_icao_map() -> dict[str, str]:
    from gad.monitor.airports import ALL_AIRPORTS
    return {f"flight-delay-{a.iata.lower()}": a.icao for a in ALL_AIRPORTS}

AIRPORT_ICAO_MAP = _build_icao_map()


def evaluate_trigger(data: dict, threshold: float) -> dict:
    """
    Evaluate a flight trigger. Source-aware:
    - AviationStack: evaluate avg delay in minutes vs threshold.
    - OpenSky: evaluate departure count (disruption proxy). Fires when
      0 departures observed in the 2-hour window.
    """
    source = data.get("source", "opensky")
    total = data.get("total_flights", 0)

    # AviationStack provides real delay data
    if source == "aviationstack":
        avg_delay = data.get("avg_delay_min", 0)
        if avg_delay is None:
            avg_delay = 0
        if total == 0:
            return {
                "fired": False,
                "value": 0,
                "status": "no_flights",
                "total_flights": 0,
                "metric": "avg_delay",
            }
        fired = avg_delay >= threshold
        return {
            "fired": fired,
            "value": round(avg_delay, 1),
            "threshold": threshold,
            "unit": "min avg delay",
            "status": "critical" if fired else "normal",
            "total_flights": total,
            "metric": "avg_delay",
        }

    # OpenSky: departure count only (no scheduled times → no delay computation)
    departure_count = data.get("departure_count", total)
    if departure_count == 0:
        return {
            "fired": True,
            "value": 0,
            "threshold": 1,
            "unit": "departures (2h)",
            "status": "critical",
            "total_flights": 0,
            "metric": "departure_count",
        }
    return {
        "fired": False,
        "value": departure_count,
        "threshold": 1,
        "unit": "departures (2h)",
        "status": "normal",
        "total_flights": departure_count,
        "metric": "departure_count",
    }
