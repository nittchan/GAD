"""
USGS Earthquake Hazards: real-time earthquake detection.
https://earthquake.usgs.gov/fdsnws/event/1/

Free, no API key, GeoJSON format. Updates every minute.
"""

from __future__ import annotations

import math

import httpx

from gad.monitor.cache import write_cache

USGS_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
TIMEOUT = 15
RADIUS_KM = 200


def fetch_earthquakes(lat: float, lon: float, trigger_id: str, radius_km: int = RADIUS_KM) -> dict | None:
    """
    Fetch earthquakes within radius_km of (lat, lon) in the last 24 hours.
    Returns dict with: max_magnitude, earthquake_count, earthquakes (list), source.
    """
    try:
        params = {
            "format": "geojson",
            "latitude": lat,
            "longitude": lon,
            "maxradiuskm": radius_km,
            "starttime": "now-24hours",
            "minmagnitude": 2.0,
            "orderby": "magnitude",
            "limit": 20,
        }
        resp = httpx.get(USGS_URL, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        features = data.get("features", [])
        earthquakes = []
        max_mag = 0.0

        for f in features:
            props = f.get("properties", {})
            coords = f.get("geometry", {}).get("coordinates", [])
            eq = {
                "magnitude": props.get("mag", 0),
                "place": props.get("place", ""),
                "time": props.get("time"),
                "depth_km": coords[2] if len(coords) > 2 else None,
                "lat": coords[1] if len(coords) > 1 else None,
                "lon": coords[0] if len(coords) > 0 else None,
            }
            earthquakes.append(eq)
            if eq["magnitude"] and eq["magnitude"] > max_mag:
                max_mag = eq["magnitude"]

        result = {
            "max_magnitude": round(max_mag, 1),
            "earthquake_count": len(earthquakes),
            "earthquakes": earthquakes[:10],
            "radius_km": radius_km,
            "lat": lat,
            "lon": lon,
            "source": "usgs",
        }
        write_cache("earthquake", trigger_id, result, ttl_seconds=1800)  # 30min TTL
        return result

    except Exception:
        return None


def evaluate_trigger(data: dict, threshold: float) -> dict:
    """Evaluate an earthquake trigger (fires when magnitude >= threshold)."""
    max_mag = data.get("max_magnitude", 0)
    count = data.get("earthquake_count", 0)

    if count == 0:
        return {
            "fired": False,
            "value": 0,
            "threshold": threshold,
            "unit": "magnitude (24h)",
            "status": "normal",
            "earthquake_count": 0,
        }

    fired = max_mag >= threshold
    return {
        "fired": fired,
        "value": max_mag,
        "threshold": threshold,
        "unit": f"magnitude ({count} quakes/24h)",
        "status": "critical" if fired else "normal",
        "earthquake_count": count,
    }
