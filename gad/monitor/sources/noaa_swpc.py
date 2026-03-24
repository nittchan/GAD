"""
NOAA Space Weather Prediction Center: planetary K-index (Kp).
https://www.swpc.noaa.gov/products/planetary-k-index

Free, no API key required. Updates every 3 hours.
Kp ranges 0-9: measures geomagnetic disturbance.
  Kp >= 5: minor storm (G1)
  Kp >= 6: moderate storm (G2)
  Kp >= 7: strong storm (G3)
  Kp >= 8: severe storm (G4)
  Kp >= 9: extreme storm (G5)
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

from gad.monitor.cache import write_cache

SWPC_KP_URL = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
TIMEOUT = 15


def _classify_storm(kp: float) -> str:
    """Classify geomagnetic storm level from Kp value."""
    if kp >= 9:
        return "extreme"
    if kp >= 8:
        return "severe"
    if kp >= 7:
        return "strong"
    if kp >= 6:
        return "moderate"
    if kp >= 5:
        return "minor"
    return "quiet"


def fetch_kp_index(trigger_id: str) -> dict | None:
    """
    Fetch the latest planetary Kp index from NOAA SWPC.

    The JSON endpoint returns a list of lists:
    [["time_tag", "Kp", "a_running", "station_count"], ["2026-03-24 00:00:00.000", "2.00", ...], ...]

    Returns dict with: kp_value, timestamp, storm_level, source.
    """
    try:
        resp = httpx.get(SWPC_KP_URL, timeout=TIMEOUT)
        resp.raise_for_status()
        rows = resp.json()

        if not rows or len(rows) < 2:
            return None

        # First row is header, last row is most recent
        latest = rows[-1]
        timestamp_str = latest[0]
        kp_str = latest[1]

        kp_value = float(kp_str)
        storm_level = _classify_storm(kp_value)

        result = {
            "kp_value": round(kp_value, 2),
            "timestamp": timestamp_str,
            "storm_level": storm_level,
            "source": "noaa_swpc",
        }

        write_cache("solar", trigger_id, result, ttl_seconds=3600)  # 1h TTL
        return result

    except Exception:
        return None


def evaluate_trigger(data: dict, threshold: float) -> dict:
    """Evaluate a solar/space weather trigger (fires when Kp >= threshold)."""
    kp = data.get("kp_value", 0)
    storm_level = data.get("storm_level", "quiet")

    fired = kp >= threshold
    return {
        "fired": fired,
        "value": round(kp, 2),
        "threshold": threshold,
        "unit": f"Kp ({storm_level})",
        "status": "critical" if fired else "normal",
        "storm_level": storm_level,
    }
