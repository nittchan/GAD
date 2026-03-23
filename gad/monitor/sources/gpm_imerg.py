"""
NASA GPM IMERG: daily precipitation satellite data.
https://gpm.nasa.gov/data/imerg

IMERG Early Run provides near-real-time daily precipitation at 0.1° resolution.
Requires NASA Earthdata token. Free.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import httpx

from gad.monitor.cache import write_cache

# PMM API for IMERG Early Run daily data
IMERG_API_URL = "https://pmmpublisher.pps.eosdis.nasa.gov/opensearch"
TIMEOUT = 30


def fetch_precipitation(lat: float, lon: float, trigger_id: str) -> dict | None:
    """
    Fetch recent daily precipitation for a point from GPM IMERG.
    Returns dict with: precipitation_mm, date, source.
    """
    token = os.environ.get("NASA_EARTHDATA_TOKEN", "")
    if not token:
        return None

    try:
        # Get yesterday's date (IMERG Early has ~4h latency)
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

        params = {
            "q": "GPM_3IMERGDE",
            "lat": lat,
            "lon": lon,
            "limit": 1,
            "startTime": yesterday,
            "endTime": yesterday,
        }
        headers = {"Authorization": f"Bearer {token}"}

        resp = httpx.get(IMERG_API_URL, params=params, headers=headers, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        # Parse the response — PMM API returns GeoJSON-like features
        items = data.get("items", [])
        if not items:
            # Fallback: try the direct data endpoint
            return _try_direct_endpoint(lat, lon, yesterday, token, trigger_id)

        # Extract precipitation value
        precip = items[0].get("properties", {}).get("precipitation")
        if precip is not None:
            result = {
                "precipitation_mm": round(float(precip), 2),
                "date": yesterday,
                "lat": lat,
                "lon": lon,
                "source": "gpm_imerg",
            }
            write_cache("drought", trigger_id, result, ttl_seconds=21600)  # 6h TTL
            return result

        return None

    except Exception:
        return None


def _try_direct_endpoint(
    lat: float, lon: float, date: str, token: str, trigger_id: str
) -> dict | None:
    """Fallback: try the OPeNDAP-style direct data access."""
    try:
        # Use the simpler Giovanni-style API
        url = "https://giovanni.gsfc.nasa.gov/giovanni/daac-bin/service_manager.py"
        params = {
            "service": "ArAvTs",
            "starttime": f"{date}T00:00:00Z",
            "endtime": f"{date}T23:59:59Z",
            "bbox": f"{lon-0.1},{lat-0.1},{lon+0.1},{lat+0.1}",
            "data": "GPM_3IMERGDF_07_precipitation",
            "portal": "GIOVANNI",
            "format": "json",
        }
        headers = {"Authorization": f"Bearer {token}"}
        resp = httpx.get(url, params=params, headers=headers, timeout=TIMEOUT)

        if resp.status_code == 200:
            # Parse whatever format comes back
            result = {
                "precipitation_mm": None,
                "date": date,
                "lat": lat,
                "lon": lon,
                "source": "gpm_imerg",
                "status": "api_response_received",
            }
            write_cache("drought", trigger_id, result, ttl_seconds=21600)
            return result

        return None
    except Exception:
        return None


def evaluate_trigger(data: dict, threshold: float) -> dict:
    """Evaluate a drought trigger using daily precipitation."""
    precip = data.get("precipitation_mm")
    if precip is None:
        # Fall through to CHIRPS
        return {"fired": False, "value": None, "status": data.get("status", "no_data")}

    fired = precip <= threshold
    return {
        "fired": fired,
        "value": round(precip, 1),
        "threshold": threshold,
        "unit": "mm/day",
        "date": data.get("date"),
        "status": "critical" if fired else "normal",
    }
