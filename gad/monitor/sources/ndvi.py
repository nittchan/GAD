"""
NDVI (Normalized Difference Vegetation Index) via Copernicus Land Service.

Free, no authentication required. Uses the MODIS-based NDVI product
via the Copernicus Global Land Service WCS endpoint.

NDVI ranges: 0.2-0.5 = sparse vegetation, 0.5-0.7 = moderate, >0.7 = dense.
For crop insurance: NDVI < 0.3 during growing season = crop stress / drought.
"""

from __future__ import annotations

import logging

import httpx

from gad.monitor.cache import write_cache

log = logging.getLogger("gad.monitor.sources.ndvi")

# Copernicus Global Land Service — free, no auth
# Alternative: use MODIS MOD13A2 via NASA AppEEARS (requires Earthdata token)
COPERNICUS_WCS_URL = "https://land.copernicus.vgt.vito.be/geoserver/ows"
TIMEOUT = 30


def fetch_ndvi(lat: float, lon: float, trigger_id: str) -> dict | None:
    """
    Fetch current NDVI value for a point location.
    Uses Copernicus Global Land Service WCS (free, no auth).
    Falls back to a simple MODIS proxy if Copernicus is unavailable.
    """
    result = _try_copernicus(lat, lon)
    if result is None:
        result = _try_modis_proxy(lat, lon)

    if result:
        result["lat"] = lat
        result["lon"] = lon
        write_cache("ndvi", trigger_id, result, ttl_seconds=86400)  # 24h TTL (16-day composite)

    return result


def _try_copernicus(lat: float, lon: float) -> dict | None:
    """Try Copernicus Global Land Service for NDVI."""
    try:
        # WCS GetCoverage for a single point — returns the NDVI value
        # Use a tiny bbox around the point (0.01 degree ~ 1km)
        bbox_size = 0.05
        params = {
            "service": "WCS",
            "version": "2.0.1",
            "request": "GetCoverage",
            "CoverageId": "BIOPAR_NDVI_V2_GLOBAL",
            "subset": f"Long({lon - bbox_size},{lon + bbox_size})",
            "subsettingcrs": "http://www.opengis.net/def/crs/EPSG/0/4326",
            "format": "application/json",
        }
        # Add latitude subset
        params["subset"] = [
            f"Long({lon - bbox_size},{lon + bbox_size})",
            f"Lat({lat - bbox_size},{lat + bbox_size})",
        ]

        resp = httpx.get(COPERNICUS_WCS_URL, params=params, timeout=TIMEOUT)
        if resp.status_code == 200:
            data = resp.json()
            # Extract NDVI value from response
            values = data.get("range", {}).get("values", [])
            if values:
                ndvi = float(values[0]) / 250.0  # Scale factor for Copernicus NDVI
                if -1 <= ndvi <= 1:
                    return {
                        "ndvi": round(ndvi, 3),
                        "source": "copernicus",
                    }
        return None
    except Exception as e:
        log.debug(f"Copernicus NDVI failed: {e}")
        return None


def _try_modis_proxy(lat: float, lon: float) -> dict | None:
    """
    Fallback: use NASA MODIS NDVI via the MODIS Web Service (free, no auth).
    Returns the most recent 16-day NDVI composite.
    """
    try:
        # MODIS Web Service — provides NDVI for any lat/lon
        url = f"https://modis.ornl.gov/rst/api/v1/MOD13A2/subset"
        params = {
            "latitude": lat,
            "longitude": lon,
            "startDate": "A2025001",  # Recent date
            "endDate": "A2026365",
            "kmAboveBelow": 0,
            "kmLeftRight": 0,
        }
        headers = {"Accept": "application/json"}
        resp = httpx.get(url, params=params, headers=headers, timeout=TIMEOUT)

        if resp.status_code != 200:
            return None

        data = resp.json()
        subsets = data.get("subset", [])
        if not subsets:
            return None

        # Get the most recent valid NDVI value
        latest = subsets[-1]
        ndvi_raw = latest.get("data", [None])[0]
        if ndvi_raw is None or ndvi_raw < -2000:
            return None

        ndvi = ndvi_raw * 0.0001  # MODIS scale factor
        if -1 <= ndvi <= 1:
            return {
                "ndvi": round(ndvi, 3),
                "source": "modis",
                "date": latest.get("calendar_date"),
            }
        return None
    except Exception as e:
        log.debug(f"MODIS NDVI failed: {e}")
        return None


def evaluate_trigger(data: dict, threshold: float) -> dict:
    """
    Evaluate an NDVI trigger. Fires when NDVI drops below threshold
    (indicating crop stress / vegetation loss).
    """
    ndvi = data.get("ndvi")
    if ndvi is None:
        return {"fired": False, "value": None, "status": "no_data"}

    fired = ndvi <= threshold
    return {
        "fired": fired,
        "value": ndvi,
        "threshold": threshold,
        "unit": "NDVI",
        "status": "critical" if fired else "normal",
        "source": data.get("source"),
    }
