"""
GDACS (Global Disaster Alert and Coordination System).
Free, no API key. RSS feed with earthquake, flood, cyclone, volcano, drought alerts.
https://www.gdacs.org/
"""
from __future__ import annotations

import logging
import math
import xml.etree.ElementTree as ET

import httpx

from gad.monitor.cache import write_cache

log = logging.getLogger("gad.monitor.sources.gdacs")
GDACS_RSS_URL = "https://www.gdacs.org/xml/rss.xml"
TIMEOUT = 20


def fetch_disasters(lat: float, lon: float, trigger_id: str, radius_km: int = 500) -> dict | None:
    """Fetch recent GDACS disaster alerts near a location."""
    try:
        resp = httpx.get(GDACS_RSS_URL, timeout=TIMEOUT)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)

        events: list[dict] = []
        for item in root.findall(".//item"):
            title = item.findtext("title", "")
            # GDACS uses georss:point for coordinates
            point = item.findtext("{http://www.georss.org/georss}point", "")
            alert_level = item.findtext("{http://www.gdacs.org}alertlevel", "")
            event_type = item.findtext("{http://www.gdacs.org}eventtype", "")
            pub_date = item.findtext("pubDate", "")

            if point:
                parts = point.strip().split()
                if len(parts) == 2:
                    try:
                        elat, elon = float(parts[0]), float(parts[1])
                    except ValueError:
                        continue
                    dist = _haversine_km(lat, lon, elat, elon)
                    if dist <= radius_km:
                        events.append({
                            "title": title,
                            "event_type": event_type,
                            "alert_level": alert_level,
                            "distance_km": round(dist, 1),
                            "lat": elat,
                            "lon": elon,
                            "pub_date": pub_date,
                        })

        result = {
            "event_count": len(events),
            "events": events[:5],
            "nearest_distance_km": min((e["distance_km"] for e in events), default=None),
            "source": "gdacs",
            "value": len(events),
        }
        write_cache("disaster", trigger_id, result, ttl_seconds=3600)
        return result
    except Exception as e:
        log.warning(f"GDACS fetch failed: {e}")
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
    """Fires when disaster event count >= threshold within radius."""
    count = data.get("event_count", 0)
    fired = count >= threshold
    return {
        "fired": fired,
        "value": count,
        "threshold": threshold,
        "unit": "disaster events",
        "status": "critical" if fired else "normal",
    }
