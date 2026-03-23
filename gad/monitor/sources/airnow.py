"""
AirNow EPA: authoritative US air quality data.
https://docs.airnowapi.org/

Free API key. Used only for US airports (country="USA").
"""

from __future__ import annotations

import os

import httpx

from gad.monitor.cache import write_cache

AIRNOW_URL = "https://www.airnowapi.org/aq/observation/latLong/current"
TIMEOUT = 15


def fetch_aqi(lat: float, lon: float, trigger_id: str) -> dict | None:
    """
    Fetch current AQI from AirNow for a US location.
    Returns dict with: aqi, pm25, parameter, station_name, source.
    """
    api_key = os.environ.get("AIRNOW_API_KEY", "")
    if not api_key:
        return None

    try:
        params = {
            "format": "application/json",
            "latitude": lat,
            "longitude": lon,
            "distance": 50,  # miles
            "API_KEY": api_key,
        }
        resp = httpx.get(AIRNOW_URL, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        if not data:
            return None

        # Find PM2.5 reading (most relevant for health AQI)
        pm25_reading = None
        best_reading = None
        for obs in data:
            if obs.get("ParameterName") == "PM2.5":
                pm25_reading = obs
            if best_reading is None or obs.get("AQI", 0) > best_reading.get("AQI", 0):
                best_reading = obs

        reading = pm25_reading or best_reading
        if not reading:
            return None

        result = {
            "aqi": reading.get("AQI"),
            "pm25": reading.get("AQI") if reading.get("ParameterName") == "PM2.5" else None,
            "pm10": None,
            "parameter": reading.get("ParameterName"),
            "category": reading.get("Category", {}).get("Name"),
            "station_name": reading.get("ReportingArea", "Unknown"),
            "source": "airnow",
            "lat": lat,
            "lon": lon,
        }
        write_cache("aqi", trigger_id, result, ttl_seconds=3600)
        return result

    except Exception:
        return None
