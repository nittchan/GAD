"""
NOAA/USGS Water Services: real-time river gauge data.
https://waterservices.usgs.gov/

Free, no API key. Returns instantaneous gauge height (parameter 00065)
and discharge (00060) for any USGS monitoring site.
"""

from __future__ import annotations

import logging

import httpx

from gad.monitor.cache import write_cache

log = logging.getLogger("gad.monitor.sources.noaa_flood")

USGS_IV_URL = "https://waterservices.usgs.gov/nwis/iv/"
TIMEOUT = 20


def fetch_gauge(site_id: str, trigger_id: str) -> dict | None:
    """
    Fetch current gauge height from USGS Water Services.
    Parameter 00065 = gauge height in feet.
    Returns dict with: gauge_height_ft, gauge_height_m, site_id, site_name, source.
    """
    try:
        params = {
            "sites": site_id,
            "parameterCd": "00065",
            "format": "json",
            "siteStatus": "active",
        }
        resp = httpx.get(USGS_IV_URL, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        ts_list = data.get("value", {}).get("timeSeries", [])
        if not ts_list:
            return None

        ts = ts_list[0]
        site_name = ts.get("sourceInfo", {}).get("siteName", "Unknown")
        values = ts.get("values", [{}])[0].get("value", [])

        if not values:
            return None

        latest = values[-1]
        height_ft = float(latest.get("value", 0))
        height_m = round(height_ft * 0.3048, 2)
        timestamp = latest.get("dateTime", "")

        result = {
            "gauge_height_ft": round(height_ft, 2),
            "gauge_height_m": height_m,
            "site_id": site_id,
            "site_name": site_name,
            "timestamp": timestamp,
            "source": "usgs_water",
        }

        write_cache("flood", trigger_id, result, ttl_seconds=1800)
        return result

    except Exception as e:
        log.warning(f"USGS gauge fetch failed for {site_id}: {e}")
        return None


def evaluate_trigger(data: dict, threshold: float) -> dict:
    """Evaluate a flood trigger. Fires when gauge height exceeds threshold (metres)."""
    height = data.get("gauge_height_m")
    if height is None:
        return {"fired": False, "value": None, "status": "no_data"}

    fired = height >= threshold
    return {
        "fired": fired,
        "value": height,
        "threshold": threshold,
        "unit": "metres",
        "status": "critical" if fired else "normal",
        "site_name": data.get("site_name"),
        "gauge_height_ft": data.get("gauge_height_ft"),
    }
