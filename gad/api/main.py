"""
Parametric Data REST API.

Routes:
  GET /v1/triggers                    — all triggers with current status
  GET /v1/triggers/{id}               — single trigger full profile
  GET /v1/triggers/{id}/basis-risk    — precomputed basis risk report
  GET /v1/triggers/{id}/determinations — last 20 signed determinations
  GET /v1/status                      — data source health per peril
  GET /v1/ports                       — marine port list

Auto-generated OpenAPI docs at /v1/docs.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware

from gad.monitor.triggers import GLOBAL_TRIGGERS, PERIL_LABELS, get_trigger_by_id, get_triggers_by_peril
from gad.monitor.cache import read_cache_with_staleness
from gad.monitor.ports import ALL_PORTS

app = FastAPI(
    title="Parametric Data API",
    description="World's first open-source actuarial data platform for parametric insurance. "
                "521 triggers, 12 perils, 15 data sources. All open. All free.",
    version="0.1.0",
    docs_url="/v1/docs",
    redoc_url="/v1/redoc",
    openapi_url="/v1/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ── Auth ──

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
REQUIRE_AUTH = os.environ.get("API_REQUIRE_AUTH", "false").lower() == "true"


async def verify_api_key(api_key: Optional[str] = Security(API_KEY_HEADER)):
    """Verify API key. Currently open — auth enforced when API_REQUIRE_AUTH=true."""
    if not REQUIRE_AUTH:
        return None
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")
    # TODO: validate against Supabase api_keys table
    # For now, check against a simple env var
    valid_key = os.environ.get("API_MASTER_KEY", "")
    if valid_key and api_key != valid_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key


# ── Source key mapping ──

SOURCE_KEY_MAP = {
    "opensky": "flights", "openaq": "aqi", "firms": "fire",
    "openmeteo": "weather", "chirps": "drought", "usgs": "earthquake",
    "aisstream": "marine", "usgs_water": "flood", "noaa_nhc": "cyclone",
    "ndvi": "ndvi", "noaa_swpc": "solar", "who_don": "health",
}

BASIS_RISK_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "basis_risk"
ORACLE_LOG_DIR = Path(__file__).resolve().parent.parent.parent / "registry"


# ── Routes ──

@app.get("/v1/triggers", tags=["Triggers"])
async def list_triggers(
    peril: Optional[str] = None,
    _key=Depends(verify_api_key),
):
    """List all triggers with current cached status."""
    triggers = GLOBAL_TRIGGERS
    if peril:
        triggers = get_triggers_by_peril(peril)
        if not triggers:
            raise HTTPException(status_code=404, detail=f"No triggers for peril '{peril}'")

    results = []
    for t in triggers:
        source_key = SOURCE_KEY_MAP.get(t.data_source, t.data_source)
        data, is_stale = read_cache_with_staleness(source_key, t.id)
        results.append({
            "id": t.id,
            "name": t.name,
            "peril": t.peril,
            "lat": t.lat,
            "lon": t.lon,
            "location_label": t.location_label,
            "threshold": t.threshold,
            "threshold_unit": t.threshold_unit,
            "data_source": t.data_source,
            "has_data": data is not None,
            "is_stale": is_stale,
        })
    return {"triggers": results, "count": len(results)}


@app.get("/v1/triggers/{trigger_id}", tags=["Triggers"])
async def get_trigger(trigger_id: str, _key=Depends(verify_api_key)):
    """Get a single trigger with full profile and cached data."""
    trigger = get_trigger_by_id(trigger_id)
    if not trigger:
        raise HTTPException(status_code=404, detail=f"Trigger '{trigger_id}' not found")

    source_key = SOURCE_KEY_MAP.get(trigger.data_source, trigger.data_source)
    data, is_stale = read_cache_with_staleness(source_key, trigger.id)

    return {
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
        "cached_data": data,
        "is_stale": is_stale,
    }


@app.get("/v1/triggers/{trigger_id}/basis-risk", tags=["Triggers"])
async def get_basis_risk(trigger_id: str, _key=Depends(verify_api_key)):
    """Get precomputed basis risk report for a trigger."""
    report_path = BASIS_RISK_DIR / f"{trigger_id}.json"
    if not report_path.is_file():
        raise HTTPException(status_code=404, detail=f"No basis risk report for '{trigger_id}'")

    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        return {"trigger_id": trigger_id, "report": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/triggers/{trigger_id}/determinations", tags=["Oracle"])
async def get_determinations(trigger_id: str, limit: int = 20, _key=Depends(verify_api_key)):
    """Get recent oracle determinations for a trigger."""
    jsonl_path = ORACLE_LOG_DIR / "oracle_log.jsonl"
    if not jsonl_path.is_file():
        return {"trigger_id": trigger_id, "determinations": [], "count": 0}

    try:
        matches = []
        with open(jsonl_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if trigger_id in str(entry.get("trigger_id", "")):
                    matches.append(entry)

        recent = matches[-limit:]
        recent.reverse()
        return {"trigger_id": trigger_id, "determinations": recent, "count": len(recent)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/status", tags=["Status"])
async def get_status(_key=Depends(verify_api_key)):
    """Data source health per peril."""
    peril_status = {}
    for peril_key, label in PERIL_LABELS.items():
        triggers = get_triggers_by_peril(peril_key)
        cached = 0
        stale = 0
        no_data = 0
        for t in triggers:
            source_key = SOURCE_KEY_MAP.get(t.data_source, t.data_source)
            data, is_stale = read_cache_with_staleness(source_key, t.id)
            if data is None:
                no_data += 1
            elif is_stale:
                stale += 1
            else:
                cached += 1
        total = len(triggers)
        peril_status[peril_key] = {
            "label": label,
            "total": total,
            "cached": cached,
            "stale": stale,
            "no_data": no_data,
            "coverage_pct": round(cached / total * 100) if total > 0 else 0,
        }
    return {"perils": peril_status, "total_triggers": len(GLOBAL_TRIGGERS)}


@app.get("/v1/ports", tags=["Marine"])
async def list_ports(_key=Depends(verify_api_key)):
    """List all monitored ports."""
    return {
        "ports": [
            {
                "id": p.id,
                "name": p.name,
                "city": p.city,
                "country": p.country,
                "lat": p.lat,
                "lon": p.lon,
                "un_locode": p.un_locode,
                "tier": p.tier,
            }
            for p in ALL_PORTS
        ],
        "count": len(ALL_PORTS),
    }


@app.get("/v1/perils", tags=["Status"])
async def list_perils(_key=Depends(verify_api_key)):
    """List all peril categories."""
    return {"perils": {k: v for k, v in PERIL_LABELS.items()}, "count": len(PERIL_LABELS)}
