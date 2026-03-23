"""
Open-Meteo: free weather API — no API key required.
https://open-meteo.com/en/docs

Fetches current weather + 24h history for extreme weather triggers.
"""

from __future__ import annotations

import httpx

from gad.monitor.cache import write_cache

OPENMETEO_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT = 15


def fetch_weather(lat: float, lon: float, trigger_id: str) -> dict | None:
    """
    Fetch current weather for a location. Returns dict with:
    - temperature_c, wind_speed_kmh, rain_mm_24h, weather_code
    """
    try:
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,wind_speed_10m,rain,weather_code",
            "hourly": "temperature_2m,rain",
            "past_hours": 24,
            "forecast_hours": 0,
            "timezone": "UTC",
        }
        resp = httpx.get(OPENMETEO_URL, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        current = data.get("current", {})
        hourly = data.get("hourly", {})

        # Sum 24h rainfall from hourly data
        rain_24h = 0.0
        if "rain" in hourly and hourly["rain"]:
            rain_24h = sum(r for r in hourly["rain"] if r is not None)

        result = {
            "temperature_c": current.get("temperature_2m"),
            "wind_speed_kmh": current.get("wind_speed_10m"),
            "rain_mm_1h": current.get("rain"),
            "rain_mm_24h": rain_24h,
            "weather_code": current.get("weather_code"),
            "lat": lat,
            "lon": lon,
        }

        write_cache("weather", trigger_id, result, ttl_seconds=1800)  # 30min TTL
        return result

    except Exception:
        return None


def evaluate_trigger(data: dict, threshold: float, unit: str, fires_when_above: bool) -> dict:
    """Evaluate a weather trigger against fetched data."""
    if unit == "celsius":
        value = data.get("temperature_c")
    elif unit == "km/h_wind":
        value = data.get("wind_speed_kmh")
    elif unit == "mm_rainfall_24h":
        value = data.get("rain_mm_24h")
    else:
        value = None

    if value is None:
        return {"fired": False, "value": None, "status": "no_data"}

    if fires_when_above:
        fired = value >= threshold
    else:
        fired = value <= threshold

    return {
        "fired": fired,
        "value": round(value, 1),
        "threshold": threshold,
        "unit": unit,
        "status": "critical" if fired else "normal",
    }
