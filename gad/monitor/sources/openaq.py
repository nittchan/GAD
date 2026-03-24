"""
OpenAQ: free air quality data API.
https://docs.openaq.org/

Falls back to WAQI (World Air Quality Index) if OpenAQ has no nearby station.
No API key required for basic OpenAQ access.
"""

from __future__ import annotations

import os

import httpx

from gad.monitor.cache import write_cache

OPENAQ_V3_URL = "https://api.openaq.org/v3/locations"
WAQI_URL = "https://api.waqi.info/feed/geo:{lat};{lon}/"
TIMEOUT = 15
RADIUS_KM = 15  # tightened from 50km — queries now use city centre coordinates (BUG-01)


def fetch_aqi(lat: float, lon: float, trigger_id: str) -> dict | None:
    """
    Fetch latest AQI reading near (lat, lon).
    Returns dict with: aqi, pm25, pm10, station_name, source.
    """
    result = _try_openaq(lat, lon)
    if result is None:
        result = _try_waqi_demo(lat, lon)

    if result:
        result["lat"] = lat
        result["lon"] = lon
        write_cache("aqi", trigger_id, result, ttl_seconds=3600)  # 1h TTL

    return result


def _try_openaq(lat: float, lon: float) -> dict | None:
    """Try OpenAQ v3 API for nearest station (requires API key)."""
    api_key = os.environ.get("OPENAQ_API_KEY", "")
    if not api_key:
        return None
    try:
        params = {
            "coordinates": f"{lat},{lon}",
            "radius": RADIUS_KM * 1000,  # meters
            "limit": 1,
            "order_by": "distance",
        }
        headers = {"X-API-Key": api_key}
        resp = httpx.get(OPENAQ_V3_URL, params=params, headers=headers, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        results = data.get("results", [])
        if not results:
            return None

        location = results[0]
        # Extract latest measurements
        sensors = location.get("sensors", [])
        pm25 = None
        pm10 = None
        for sensor in sensors:
            param = sensor.get("parameter", {})
            if param.get("name") == "pm25":
                pm25 = sensor.get("summary", {}).get("avg")
            elif param.get("name") == "pm10":
                pm10 = sensor.get("summary", {}).get("avg")

        # Approximate AQI from PM2.5 (EPA breakpoints, simplified)
        aqi = _pm25_to_aqi(pm25) if pm25 is not None else None

        return {
            "aqi": aqi,
            "pm25": round(pm25, 1) if pm25 else None,
            "pm10": round(pm10, 1) if pm10 else None,
            "station_name": location.get("name", "Unknown"),
            "source": "openaq",
        }
    except Exception:
        return None


def _try_waqi_demo(lat: float, lon: float) -> dict | None:
    """Fallback: WAQI with token from env or demo (rate-limited)."""
    try:
        token = os.environ.get("WAQI_API_TOKEN", "demo")
        url = f"https://api.waqi.info/feed/geo:{lat};{lon}/?token={token}"
        resp = httpx.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "ok":
            return None

        d = data.get("data", {})
        iaqi = d.get("iaqi", {})

        return {
            "aqi": d.get("aqi"),
            "pm25": iaqi.get("pm25", {}).get("v"),
            "pm10": iaqi.get("pm10", {}).get("v"),
            "station_name": d.get("city", {}).get("name", "Unknown"),
            "source": "waqi",
        }
    except Exception:
        return None


def _pm25_to_aqi(pm25: float) -> int:
    """Simplified EPA PM2.5 to AQI conversion."""
    breakpoints = [
        (0.0, 12.0, 0, 50),
        (12.1, 35.4, 51, 100),
        (35.5, 55.4, 101, 150),
        (55.5, 150.4, 151, 200),
        (150.5, 250.4, 201, 300),
        (250.5, 500.4, 301, 500),
    ]
    for bp_lo, bp_hi, aqi_lo, aqi_hi in breakpoints:
        if bp_lo <= pm25 <= bp_hi:
            return round(((aqi_hi - aqi_lo) / (bp_hi - bp_lo)) * (pm25 - bp_lo) + aqi_lo)
    return 500 if pm25 > 500 else 0


def evaluate_trigger(data: dict, threshold: float) -> dict:
    """Evaluate an AQI trigger."""
    aqi = data.get("aqi")
    if aqi is None:
        return {"fired": False, "value": None, "status": "no_data"}

    fired = aqi >= threshold
    return {
        "fired": fired,
        "value": aqi,
        "threshold": threshold,
        "unit": "AQI",
        "status": "critical" if fired else "normal",
        "pm25": data.get("pm25"),
        "station": data.get("station_name"),
    }
