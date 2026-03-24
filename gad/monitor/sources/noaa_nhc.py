"""
NOAA National Hurricane Center: active tropical cyclone tracking.
https://www.nhc.noaa.gov/

Free, no API key. Returns active storms from NHC CurrentStorms JSON.
Evaluates proximity of storm positions to trigger locations using haversine.
"""

from __future__ import annotations

import logging
import math

import httpx

from gad.monitor.cache import write_cache

log = logging.getLogger("gad.monitor.sources.noaa_nhc")

NHC_ACTIVE_URL = "https://www.nhc.noaa.gov/CurrentSurges.json"
NHC_CURRENT_URL = "https://www.nhc.noaa.gov/CurrentStorms.json"
TIMEOUT = 20
RADIUS_KM = 200  # proximity threshold for trigger evaluation


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance in km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def fetch_active_storms(trigger_lat: float, trigger_lon: float, trigger_id: str) -> dict | None:
    """
    Fetch active tropical storms from NHC and check proximity to trigger location.
    Returns dict with: nearest storm info, distance, max wind.
    """
    try:
        resp = httpx.get(NHC_CURRENT_URL, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        active_storms = data.get("activeStorms", [])
        if not active_storms:
            result = {
                "active_storm_count": 0,
                "nearest_storm": None,
                "nearest_distance_km": None,
                "max_wind_knots": 0,
                "source": "noaa_nhc",
            }
            write_cache("cyclone", trigger_id, result, ttl_seconds=1800)
            return result

        nearest_storm = None
        nearest_dist = float("inf")
        max_wind = 0

        for storm in active_storms:
            storm_lat = storm.get("latitudeNumeric")
            storm_lon = storm.get("longitudeNumeric")
            wind = storm.get("intensity", 0) or 0

            if storm_lat is None or storm_lon is None:
                continue

            dist = _haversine_km(trigger_lat, trigger_lon, storm_lat, storm_lon)

            if dist < nearest_dist:
                nearest_dist = dist
                nearest_storm = {
                    "name": storm.get("name", "Unknown"),
                    "classification": storm.get("classification", ""),
                    "lat": storm_lat,
                    "lon": storm_lon,
                    "wind_knots": wind,
                    "movement": storm.get("movementDir", ""),
                    "pressure_mb": storm.get("pressure"),
                }

            if wind > max_wind:
                max_wind = wind

        result = {
            "active_storm_count": len(active_storms),
            "nearest_storm": nearest_storm,
            "nearest_distance_km": round(nearest_dist, 1) if nearest_dist < float("inf") else None,
            "max_wind_knots": max_wind,
            "source": "noaa_nhc",
        }

        write_cache("cyclone", trigger_id, result, ttl_seconds=1800)
        return result

    except Exception as e:
        log.warning(f"NHC fetch failed for {trigger_id}: {e}")
        return None


def evaluate_trigger(data: dict, threshold: float) -> dict:
    """
    Evaluate a cyclone trigger.
    Fires when any active storm has wind >= threshold knots within RADIUS_KM.
    """
    nearest = data.get("nearest_storm")
    distance = data.get("nearest_distance_km")
    storm_count = data.get("active_storm_count", 0)

    if storm_count == 0 or nearest is None:
        return {
            "fired": False,
            "value": 0,
            "threshold": threshold,
            "unit": "knots (no active storms)",
            "status": "normal",
            "active_storms": 0,
        }

    wind = nearest.get("wind_knots", 0)
    within_range = distance is not None and distance <= RADIUS_KM
    fired = within_range and wind >= threshold

    if within_range:
        status = "critical" if fired else "normal"
        unit = f"knots ({nearest['name']}, {round(distance)}km away)"
    else:
        status = "normal"
        unit = f"knots (nearest: {nearest['name']}, {round(distance)}km away)"

    return {
        "fired": fired,
        "value": wind if within_range else 0,
        "threshold": threshold,
        "unit": unit,
        "status": status,
        "active_storms": storm_count,
        "nearest_storm_name": nearest.get("name"),
        "nearest_distance_km": distance,
    }
