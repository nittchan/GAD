"""
NASA EONET (Earth Observatory Natural Event Tracker).
Free, no API key. Returns active natural events in 13 categories.
https://eonet.gsfc.nasa.gov/api/v3/events

Categories include: wildfires, severe storms, volcanoes, floods,
earthquakes, drought, dust/haze, sea/lake ice, landslides, etc.
"""
from __future__ import annotations

import logging
import math

import httpx

from gad.monitor.cache import write_cache

log = logging.getLogger("gad.monitor.sources.nasa_eonet")
EONET_URL = "https://eonet.gsfc.nasa.gov/api/v3/events"
TIMEOUT = 20


def fetch_events(lat: float, lon: float, trigger_id: str, radius_km: int = 500, days: int = 7) -> dict | None:
    """Fetch recent EONET natural events near a location.

    Args:
        lat, lon: Centre point for proximity filter.
        trigger_id: Cache key.
        radius_km: Maximum distance to include events.
        days: Look-back window in days.

    Returns:
        dict with event_count, events, nearest_distance_km, source.
    """
    try:
        params = {
            "status": "open",
            "days": days,
            "limit": 50,
        }
        resp = httpx.get(EONET_URL, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        events: list[dict] = []
        for ev in data.get("events", []):
            title = ev.get("title", "")
            categories = [c.get("title", "") for c in ev.get("categories", [])]
            category_ids = [c.get("id", "") for c in ev.get("categories", [])]

            # EONET geometries: each event can have multiple geometry entries
            for geom in ev.get("geometry", []):
                coords = geom.get("coordinates", [])
                if not coords or not isinstance(coords, list):
                    continue
                # Point geometry: [lon, lat]
                if isinstance(coords[0], (int, float)):
                    elon, elat = coords[0], coords[1] if len(coords) > 1 else 0
                    dist = _haversine_km(lat, lon, elat, elon)
                    if dist <= radius_km:
                        events.append({
                            "title": title,
                            "categories": categories,
                            "category_ids": category_ids,
                            "distance_km": round(dist, 1),
                            "lat": elat,
                            "lon": elon,
                            "date": geom.get("date", ""),
                        })
                        break  # One match per event is enough

        result = {
            "event_count": len(events),
            "events": events[:5],
            "nearest_distance_km": min((e["distance_km"] for e in events), default=None),
            "source": "nasa_eonet",
            "value": len(events),
        }
        write_cache("eonet", trigger_id, result, ttl_seconds=3600)
        return result
    except Exception as e:
        log.warning(f"NASA EONET fetch failed: {e}")
        return None


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points in kilometres."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def evaluate_trigger(data: dict, threshold: float) -> dict:
    """Fires when natural event count >= threshold within radius."""
    count = data.get("event_count", 0)
    fired = count >= threshold
    return {
        "fired": fired,
        "value": count,
        "threshold": threshold,
        "unit": "natural events",
        "status": "critical" if fired else "normal",
    }
