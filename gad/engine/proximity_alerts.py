"""Trigger proximity alerts — notify when value is within 20% of threshold."""
import logging
from gad.monitor.triggers import GLOBAL_TRIGGERS
from gad.monitor.cache import read_cache_with_staleness

log = logging.getLogger("gad.engine.proximity_alerts")

SOURCE_KEY_MAP = {
    "opensky": "flights", "openaq": "aqi", "firms": "fire",
    "openmeteo": "weather", "chirps": "drought", "usgs": "earthquake",
    "aisstream": "marine", "usgs_water": "flood", "noaa_nhc": "cyclone",
    "ndvi": "ndvi", "noaa_swpc": "solar", "who_don": "health",
    "faa_atcscc": "flights",
}


def check_proximity_alerts(threshold_pct=0.8):
    """Find triggers whose current value is within 20% of threshold."""
    alerts = []
    for t in GLOBAL_TRIGGERS:
        try:
            source_key = SOURCE_KEY_MAP.get(t.data_source, t.data_source)
            data, _ = read_cache_with_staleness(source_key, t.id)
            if data is None:
                continue
            value = data.get("value") or data.get("avg_delay_min") or data.get("aqi") or data.get("gauge_height_m")
            if value is None or t.threshold == 0:
                continue

            if t.fires_when_above:
                proximity = value / t.threshold
            else:
                proximity = t.threshold / value if value > 0 else 0

            if proximity >= threshold_pct and proximity < 1.0:
                alerts.append({
                    "trigger_id": t.id,
                    "name": t.name,
                    "peril": t.peril,
                    "value": value,
                    "threshold": t.threshold,
                    "proximity_pct": round(proximity * 100, 1),
                })
        except Exception:
            continue
    return alerts
