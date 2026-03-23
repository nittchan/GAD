"""
CHIRPS drought monitor: uses the existing CHIRPS pipeline to fetch monthly rainfall.
https://data.chc.ucsb.edu/products/CHIRPS-2.0/

Monthly data — fetched every 6 hours (checks for new month).
No API key required.
"""

from __future__ import annotations

from datetime import datetime, timezone

from gad.monitor.cache import write_cache

# Attempt to use the existing pipeline; gracefully degrade if rasterio not installed
try:
    from gad.pipeline import fetch_chirps_monthly, _read_point_from_geotiff
    _HAS_PIPELINE = True
except ImportError:
    _HAS_PIPELINE = False


def fetch_rainfall(lat: float, lon: float, trigger_id: str) -> dict | None:
    """
    Fetch the most recent CHIRPS monthly rainfall for a point.
    Returns dict with: rainfall_mm, period (YYYY-MM), source.
    """
    if not _HAS_PIPELINE:
        result = {
            "rainfall_mm": None,
            "period": None,
            "source": "chirps",
            "status": "missing_dependency",
            "message": "Install rasterio: pip install rasterio",
        }
        write_cache("drought", trigger_id, result, ttl_seconds=21600)
        return result

    now = datetime.now(timezone.utc)
    # CHIRPS has ~1 month latency; fetch previous month
    if now.month == 1:
        year, month = now.year - 1, 12
    else:
        year, month = now.year, now.month - 1

    try:
        raster_path = fetch_chirps_monthly(year, month)
        rainfall_mm = _read_point_from_geotiff(raster_path, lat, lon)

        result = {
            "rainfall_mm": round(rainfall_mm, 1),
            "period": f"{year}-{month:02d}",
            "lat": lat,
            "lon": lon,
            "source": "chirps",
        }

        write_cache("drought", trigger_id, result, ttl_seconds=21600)  # 6h TTL
        return result

    except Exception as e:
        result = {
            "rainfall_mm": None,
            "period": f"{year}-{month:02d}",
            "source": "chirps",
            "status": "fetch_error",
            "message": str(e)[:200],
        }
        write_cache("drought", trigger_id, result, ttl_seconds=3600)  # retry in 1h
        return result


def evaluate_trigger(data: dict, threshold: float) -> dict:
    """Evaluate a drought trigger (fires when rainfall BELOW threshold)."""
    rainfall = data.get("rainfall_mm")
    if rainfall is None:
        return {"fired": False, "value": None, "status": data.get("status", "no_data")}

    fired = rainfall <= threshold
    return {
        "fired": fired,
        "value": round(rainfall, 1),
        "threshold": threshold,
        "unit": "mm rainfall",
        "period": data.get("period"),
        "status": "critical" if fired else "normal",
    }
