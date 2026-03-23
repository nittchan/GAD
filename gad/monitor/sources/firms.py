"""
NASA FIRMS: Fire Information for Resource Management System.
https://firms.modaps.eosdis.nasa.gov/api/

Free API key required (request at https://firms.modaps.eosdis.nasa.gov/api/area/).
Falls back to CSV download if no key is set.
"""

from __future__ import annotations

import math
import os

import httpx

from gad.monitor.cache import write_cache

FIRMS_API_BASE = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
FIRMS_MAP_KEY = os.getenv("NASA_FIRMS_MAP_KEY", "")
TIMEOUT = 30
RADIUS_KM = 100


def fetch_fires(lat: float, lon: float, trigger_id: str, radius_km: int = RADIUS_KM) -> dict | None:
    """
    Fetch active fire count near (lat, lon) from NASA FIRMS.
    Returns dict with: fire_count, fires (list), source.
    """
    if not FIRMS_MAP_KEY:
        # No API key — return a degraded result with instructions
        result = {
            "fire_count": None,
            "fires": [],
            "source": "firms",
            "status": "no_api_key",
            "message": "Set NASA_FIRMS_MAP_KEY env var. Free at firms.modaps.eosdis.nasa.gov/api/area/",
        }
        write_cache("fire", trigger_id, result, ttl_seconds=7200)
        return result

    try:
        # FIRMS API v2: path-based parameters
        # URL format: /api/area/csv/{MAP_KEY}/{SOURCE}/{BBOX}/{DAY_RANGE}
        dlat = radius_km / 111.0
        dlon = radius_km / (111.0 * math.cos(math.radians(lat)))
        bbox = f"{lon - dlon},{lat - dlat},{lon + dlon},{lat + dlat}"

        # Fetch from both VIIRS and MODIS satellites, merge results
        all_fires = []
        for satellite in ["VIIRS_SNPP_NRT", "MODIS_NRT"]:
            url = f"{FIRMS_API_BASE}/{FIRMS_MAP_KEY}/{satellite}/{bbox}/1"
            try:
                sat_resp = httpx.get(url, timeout=TIMEOUT)
                if sat_resp.status_code == 200:
                    all_fires.extend(_parse_csv_fires(sat_resp.text, satellite))
            except Exception:
                pass

        # Deduplicate fires within ~1km of each other
        fires = _deduplicate_fires(all_fires)
        fire_count = len(fires)

        result = {
            "fire_count": fire_count,
            "fires": fires[:50],
            "source": "firms",
            "satellites": ["VIIRS", "MODIS"],
            "radius_km": radius_km,
            "lat": lat,
            "lon": lon,
        }
        write_cache("fire", trigger_id, result, ttl_seconds=3600)
        return result

    except Exception:
        return None


def _parse_csv_fires(csv_text: str, satellite: str) -> list[dict]:
    """Parse FIRMS CSV response into fire dicts."""
    lines = csv_text.strip().split("\n")
    if len(lines) <= 1:
        return []

    fires = []
    headers = lines[0].split(",")
    lat_idx = headers.index("latitude") if "latitude" in headers else 0
    lon_idx = headers.index("longitude") if "longitude" in headers else 1
    conf_idx = headers.index("confidence") if "confidence" in headers else -1

    for line in lines[1:]:
        parts = line.split(",")
        try:
            fire = {
                "lat": float(parts[lat_idx]),
                "lon": float(parts[lon_idx]),
                "satellite": satellite.split("_")[0],
            }
            if conf_idx >= 0 and conf_idx < len(parts):
                fire["confidence"] = parts[conf_idx]
            fires.append(fire)
        except (ValueError, IndexError):
            continue
    return fires


def _deduplicate_fires(fires: list[dict], threshold_km: float = 1.0) -> list[dict]:
    """Remove duplicate fire detections within threshold_km of each other."""
    if not fires:
        return []

    unique = [fires[0]]
    for fire in fires[1:]:
        is_dup = False
        for existing in unique:
            dlat = abs(fire["lat"] - existing["lat"]) * 111.0
            dlon = abs(fire["lon"] - existing["lon"]) * 111.0 * math.cos(math.radians(fire["lat"]))
            if math.sqrt(dlat**2 + dlon**2) < threshold_km:
                is_dup = True
                break
        if not is_dup:
            unique.append(fire)
    return unique


def evaluate_trigger(data: dict, threshold: float) -> dict:
    """Evaluate a wildfire trigger."""
    fire_count = data.get("fire_count")
    if fire_count is None:
        return {"fired": False, "value": None, "status": "no_data"}

    fired = fire_count >= threshold
    return {
        "fired": fired,
        "value": fire_count,
        "threshold": int(threshold),
        "unit": "active fires",
        "status": "critical" if fired else "normal",
    }
