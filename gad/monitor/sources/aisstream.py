"""
AISstream: real-time AIS vessel tracking via WebSocket.
https://aisstream.io/documentation

Connects to wss://stream.aisstream.io/v0/stream, subscribes to a bounding box,
collects position reports for a time window, and returns vessel statistics.

Requires env var AISSTREAM_API_KEY.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

from gad.monitor.cache import write_cache

log = logging.getLogger("gad.monitor.sources.aisstream")

AISSTREAM_WS_URL = "wss://stream.aisstream.io/v0/stream"
DEFAULT_WINDOW_SECONDS = 90


def fetch_port_vessels(
    port_id: str,
    anchor_bbox: tuple[float, float, float, float],
    window_seconds: int = DEFAULT_WINDOW_SECONDS,
) -> dict | None:
    """
    Connect to AISstream WebSocket, subscribe to a bounding box, collect
    vessel position reports for `window_seconds`, then return statistics.

    anchor_bbox: (lat_min, lon_min, lat_max, lon_max)

    Returns dict with:
      vessel_count, vessels_at_anchor, mmsi_list, mean_speed, source
    """
    api_key = os.environ.get("AISSTREAM_API_KEY", "")
    if not api_key:
        log.debug("AISSTREAM_API_KEY not set, skipping marine fetch")
        return None

    try:
        import websockets.sync.client as ws_client
    except ImportError:
        log.warning("websockets package not installed — pip install websockets")
        return None

    lat_min, lon_min, lat_max, lon_max = anchor_bbox

    # AISstream expects [[lat_min, lon_min], [lat_max, lon_max]]
    subscription = {
        "APIKey": api_key,
        "BoundingBoxes": [[[lat_min, lon_min], [lat_max, lon_max]]],
        "FilterMessageTypes": ["PositionReport"],
    }

    vessels: dict[int, dict] = {}  # MMSI -> latest data

    try:
        with ws_client.connect(AISSTREAM_WS_URL, open_timeout=10, close_timeout=5) as conn:
            conn.send(json.dumps(subscription))

            deadline = time.time() + window_seconds
            conn.settimeout(window_seconds + 5)

            while time.time() < deadline:
                try:
                    conn.settimeout(max(1, deadline - time.time()))
                    raw = conn.recv()
                    msg = json.loads(raw)

                    msg_type = msg.get("MessageType")
                    if msg_type != "PositionReport":
                        continue

                    meta = msg.get("MetaData", {})
                    mmsi = meta.get("MMSI")
                    if not mmsi:
                        continue

                    position = msg.get("Message", {}).get("PositionReport", {})
                    nav_status = position.get("NavigationalStatus", -1)
                    sog = position.get("Sog", 0)  # speed over ground in knots

                    vessels[mmsi] = {
                        "mmsi": mmsi,
                        "ship_name": meta.get("ShipName", "").strip(),
                        "nav_status": nav_status,
                        "sog": sog,
                        "lat": position.get("Latitude"),
                        "lon": position.get("Longitude"),
                        "timestamp": meta.get("time_utc"),
                    }

                except TimeoutError:
                    break
                except Exception:
                    break

    except Exception as e:
        log.warning(f"AISstream WebSocket error for {port_id}: {e}")
        return None

    if not vessels:
        result = {
            "vessel_count": 0,
            "vessels_at_anchor": 0,
            "mmsi_list": [],
            "mean_speed": 0.0,
            "source": "aisstream",
        }
        write_cache("marine", port_id, result, ttl_seconds=1800)
        return result

    # NavigationalStatus == 1 means "At anchor"
    at_anchor = sum(1 for v in vessels.values() if v.get("nav_status") == 1)
    speeds = [v["sog"] for v in vessels.values() if v.get("sog") is not None]
    mean_speed = sum(speeds) / len(speeds) if speeds else 0.0

    result = {
        "vessel_count": len(vessels),
        "vessels_at_anchor": at_anchor,
        "mmsi_list": list(vessels.keys()),
        "mean_speed": round(mean_speed, 1),
        "source": "aisstream",
    }

    write_cache("marine", port_id, result, ttl_seconds=1800)  # 30 min TTL
    return result


def evaluate_trigger(data: dict, threshold: float, threshold_unit: str = "vessels") -> dict:
    """
    Evaluate a marine trigger.
    - Congestion (vessels): fires when vessel_count > threshold
    - Dwell time (hours): not computable from a single snapshot — uses vessel_count as proxy
    """
    if threshold_unit == "vessels":
        vessel_count = data.get("vessels_at_anchor", data.get("vessel_count", 0))
        fired = vessel_count > threshold
        return {
            "fired": fired,
            "value": vessel_count,
            "threshold": threshold,
            "unit": "vessels at anchor",
            "status": "critical" if fired else "normal",
            "total_vessels": data.get("vessel_count", 0),
            "mean_speed": data.get("mean_speed", 0),
        }
    elif threshold_unit == "hours":
        # Dwell time requires tracking vessels over multiple snapshots.
        # For now, use vessel count as a congestion proxy.
        vessel_count = data.get("vessels_at_anchor", data.get("vessel_count", 0))
        # Heuristic: if many vessels at anchor, dwell time is likely high
        fired = vessel_count > 15  # proxy threshold
        return {
            "fired": fired,
            "value": vessel_count,
            "threshold": threshold,
            "unit": "vessels (dwell proxy)",
            "status": "critical" if fired else "normal",
            "total_vessels": data.get("vessel_count", 0),
        }
    else:
        return {"fired": False, "value": None, "status": "no_data"}
