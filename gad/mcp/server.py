"""
MCP server for Parametric Data — exposes GAD as tools for AI agents.

Run:  python -m gad.mcp.server

Protocol: JSON-RPC 2.0 over stdin/stdout (MCP transport).
"""

from __future__ import annotations

import json
import math
import sys
from typing import Any

from gad.monitor.triggers import GLOBAL_TRIGGERS, PERIL_LABELS, get_trigger_by_id, get_triggers_by_peril
from gad.monitor.cache import read_cache_with_staleness
from gad.config import BASIS_RISK_DIR

# ── Source key mapping (mirrors gad/api/main.py) ──

SOURCE_KEY_MAP = {
    "opensky": "flights", "openaq": "aqi", "firms": "fire",
    "openmeteo": "weather", "chirps": "drought", "usgs": "earthquake",
    "aisstream": "marine", "usgs_water": "flood", "noaa_nhc": "cyclone",
    "ndvi": "ndvi", "noaa_swpc": "solar", "who_don": "health",
}

# ── Geo helpers ──

def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two (lat, lon) points."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# ── Tool implementations ──

def _check_trigger_status(trigger_id: str) -> dict[str, Any]:
    """Look up a single trigger and return its current cached status."""
    trigger = get_trigger_by_id(trigger_id)
    if not trigger:
        return {"content": [{"type": "text", "text": json.dumps({"error": f"Trigger '{trigger_id}' not found"})}]}

    source_key = SOURCE_KEY_MAP.get(trigger.data_source, trigger.data_source)
    data, is_stale = read_cache_with_staleness(source_key, trigger.id)

    fired = None
    if data is not None:
        value = data.get("value") if isinstance(data, dict) else None
        if value is not None:
            fired = (value > trigger.threshold) if trigger.fires_when_above else (value < trigger.threshold)

    result = {
        "id": trigger.id,
        "name": trigger.name,
        "peril": trigger.peril,
        "peril_label": PERIL_LABELS.get(trigger.peril, trigger.peril),
        "lat": trigger.lat,
        "lon": trigger.lon,
        "location_label": trigger.location_label,
        "threshold": trigger.threshold,
        "threshold_unit": trigger.threshold_unit,
        "fires_when_above": trigger.fires_when_above,
        "data_source": trigger.data_source,
        "description": trigger.description,
        "has_data": data is not None,
        "is_stale": is_stale,
        "cached_data": data,
        "fired": fired,
    }
    return {"content": [{"type": "text", "text": json.dumps(result, default=str)}]}


def _list_by_location(lat: float, lon: float, radius_km: float = 500) -> dict[str, Any]:
    """Return all triggers within *radius_km* of (lat, lon)."""
    matches = []
    for t in GLOBAL_TRIGGERS:
        dist = _haversine_km(lat, lon, t.lat, t.lon)
        if dist <= radius_km:
            source_key = SOURCE_KEY_MAP.get(t.data_source, t.data_source)
            data, is_stale = read_cache_with_staleness(source_key, t.id)
            matches.append({
                "id": t.id,
                "name": t.name,
                "peril": t.peril,
                "lat": t.lat,
                "lon": t.lon,
                "location_label": t.location_label,
                "distance_km": round(dist, 1),
                "threshold": t.threshold,
                "threshold_unit": t.threshold_unit,
                "has_data": data is not None,
                "is_stale": is_stale,
            })

    matches.sort(key=lambda m: m["distance_km"])
    result = {"lat": lat, "lon": lon, "radius_km": radius_km, "triggers": matches, "count": len(matches)}
    return {"content": [{"type": "text", "text": json.dumps(result, default=str)}]}


def _get_basis_risk(trigger_id: str) -> dict[str, Any]:
    """Return the precomputed basis risk report JSON for a trigger."""
    trigger = get_trigger_by_id(trigger_id)
    if not trigger:
        return {"content": [{"type": "text", "text": json.dumps({"error": f"Trigger '{trigger_id}' not found"})}]}

    report_path = BASIS_RISK_DIR / f"{trigger_id}.json"
    if not report_path.is_file():
        return {"content": [{"type": "text", "text": json.dumps({"trigger_id": trigger_id, "report": None, "message": "No precomputed basis risk report available for this trigger"})}]}

    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        return {"content": [{"type": "text", "text": json.dumps({"trigger_id": trigger_id, "report": report}, default=str)}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": json.dumps({"error": str(e)})}]}


# ── MCP protocol handler ──

TOOLS = [
    {
        "name": "check_trigger_status",
        "description": "Get current status of a parametric insurance trigger by its ID. Returns cached observation data, threshold evaluation, and staleness info.",
        "inputSchema": {
            "type": "object",
            "properties": {"trigger_id": {"type": "string", "description": "Trigger identifier, e.g. 'flight-delay-del'"}},
            "required": ["trigger_id"],
        },
    },
    {
        "name": "list_triggers_by_location",
        "description": "Find all parametric insurance triggers within a radius of a geographic point. Returns triggers sorted by distance.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "lat": {"type": "number", "description": "Latitude of the search centre"},
                "lon": {"type": "number", "description": "Longitude of the search centre"},
                "radius_km": {"type": "number", "description": "Search radius in kilometres (default 500)", "default": 500},
            },
            "required": ["lat", "lon"],
        },
    },
    {
        "name": "get_basis_risk",
        "description": "Get the precomputed Spearman correlation basis risk report for a trigger. Includes rho, confidence interval, FPR/FNR, and Lloyd's score.",
        "inputSchema": {
            "type": "object",
            "properties": {"trigger_id": {"type": "string", "description": "Trigger identifier, e.g. 'weather-heat-del'"}},
            "required": ["trigger_id"],
        },
    },
    {
        "name": "list_perils",
        "description": "List all peril categories monitored by Parametric Data (flight delay, earthquake, wildfire, etc.).",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def handle_request(request: dict) -> dict:
    """Route a single MCP JSON-RPC request and return the result payload."""
    method = request.get("method", "")
    params = request.get("params", {})

    if method == "initialize":
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "parametric-data", "version": "0.1.0"},
        }

    if method == "tools/list":
        return {"tools": TOOLS}

    if method == "tools/call":
        tool_name = params.get("name", "")
        args = params.get("arguments", {})

        if tool_name == "check_trigger_status":
            return _check_trigger_status(args["trigger_id"])
        if tool_name == "list_triggers_by_location":
            return _list_by_location(args["lat"], args["lon"], args.get("radius_km", 500))
        if tool_name == "get_basis_risk":
            return _get_basis_risk(args["trigger_id"])
        if tool_name == "list_perils":
            return {"content": [{"type": "text", "text": json.dumps(dict(PERIL_LABELS))}]}

        return {"error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}}

    # Unknown method
    return {"error": {"code": -32601, "message": f"Unknown method: {method}"}}


# ── Stdio transport ──

def main() -> None:
    """Run the MCP server on stdin/stdout (JSON-RPC 2.0, one object per line)."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
            continue

        req_id = request.get("id")
        result = handle_request(request)

        if "error" in result:
            response = {"jsonrpc": "2.0", "id": req_id, "error": result["error"]}
        else:
            response = {"jsonrpc": "2.0", "id": req_id, "result": result}

        sys.stdout.write(json.dumps(response, default=str) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
