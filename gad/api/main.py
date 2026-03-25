"""
Parametric Data REST API.

Routes:
  GET /v1/triggers                    — all triggers with current status
  GET /v1/triggers/{id}               — single trigger full profile
  GET /v1/triggers/{id}/basis-risk    — precomputed basis risk report
  GET /v1/triggers/{id}/determinations — last 20 signed determinations
  GET /v1/status                      — data source health per peril
  GET /v1/health                      — per-source data freshness with traffic-light status
  GET /v1/ports                       — marine port list
  GET /v1/perils                      — peril categories
  GET /v1/intelligence/peril-patterns — firing rates and drift per peril
  GET /v1/intelligence/location/{lat}/{lon} — triggers near a point
  GET /v1/intelligence/climate-zone/{zone}  — triggers in a climate zone (Phase 3)
  GET /v1/triggers/{id}/model-drift   — model drift status for a trigger

Auto-generated OpenAPI docs at /v1/docs.
"""

from __future__ import annotations

import json
import math
import os
from typing import Optional

from fastapi import FastAPI, HTTPException, Security, Depends, Path, Query
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware

from gad.monitor.triggers import GLOBAL_TRIGGERS, PERIL_LABELS, get_trigger_by_id, get_triggers_by_peril
from gad.monitor.cache import read_cache_with_staleness
from gad.monitor.ports import ALL_PORTS
from gad.api.models import (
    TriggerListResponse,
    TriggerDetailResponse,
    BasisRiskResponse,
    DeterminationsResponse,
    StatusResponse,
    PortListResponse,
    PerilListResponse,
    ModelHistoryResponse,
    PerilPatternEntry,
    PerilPatternsResponse,
    LocationIntelligenceResponse,
    LocationTriggerEntry,
    ClimateZoneResponse,
    ModelDriftResponse,
    HealthResponse,
)

app = FastAPI(
    title="Parametric Data API",
    description=(
        f"World's first open-source actuarial data platform for parametric insurance. "
        f"{len(GLOBAL_TRIGGERS)} triggers, {len(PERIL_LABELS)} perils, 15 data sources. "
        f"All open. All free."
    ),
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

from gad.config import BASIS_RISK_DIR, ORACLE_DIR, CACHE_DIR

# ORACLE_LOG_DIR used locally for the JSONL path — points to the oracle root
_ORACLE_LOG_DIR = ORACLE_DIR


# ── Routes ──

@app.get("/v1/triggers", tags=["Triggers"], response_model=TriggerListResponse)
async def list_triggers(
    peril: Optional[str] = Query(
        None,
        description="Filter by peril type (e.g. 'earthquake', 'flood', 'flight_delay', 'air_quality')",
    ),
    _key=Depends(verify_api_key),
):
    """
    List all parametric insurance triggers with their current cached status.

    Optionally filter by peril type. Returns trigger metadata (id, name, peril,
    location, threshold) and data availability status for each trigger.

    Example response:
    ```json
    {
      "triggers": [{"id": "flight-delay-del", "name": "Flight Delay — DEL", "peril": "flight_delay", ...}],
      "count": 521
    }
    ```
    """
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


@app.get("/v1/triggers/{trigger_id}", tags=["Triggers"], response_model=TriggerDetailResponse)
async def get_trigger(
    trigger_id: str = Path(
        ...,
        description="Trigger identifier, e.g. 'flight-delay-del' or 'earthquake-tokyo'",
    ),
    _key=Depends(verify_api_key),
):
    """
    Get a single trigger with its full profile and most recent cached data.

    Returns all trigger metadata including peril label, threshold direction,
    description, and the latest cached observation value. Use this endpoint
    to build detailed trigger profile views.

    Example response:
    ```json
    {
      "id": "flight-delay-del",
      "peril": "flight_delay",
      "peril_label": "Flight Delay",
      "threshold": 30.0,
      "fires_when_above": true,
      "cached_data": {"value": 12.5},
      "is_stale": false
    }
    ```
    """
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


@app.get("/v1/triggers/{trigger_id}/basis-risk", tags=["Triggers"], response_model=BasisRiskResponse)
async def get_basis_risk(
    trigger_id: str = Path(
        ...,
        description="Trigger identifier, e.g. 'weather-heat-del'",
    ),
    _key=Depends(verify_api_key),
):
    """
    Get the precomputed basis risk report for a trigger.

    The report includes Spearman correlation coefficient with confidence interval,
    false positive/negative rates, Lloyd's alignment score, and the number of
    observation periods analysed. Not all triggers have precomputed reports.

    Example response:
    ```json
    {
      "trigger_id": "weather-heat-del",
      "report": {"spearman_rho": 0.87, "fpr": 0.05, "fnr": 0.08, "lloyds_score": 85}
    }
    ```
    """
    report_path = BASIS_RISK_DIR / f"{trigger_id}.json"
    if not report_path.is_file():
        raise HTTPException(status_code=404, detail=f"No basis risk report for '{trigger_id}'")

    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        return {"trigger_id": trigger_id, "report": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/triggers/{trigger_id}/determinations", tags=["Oracle"], response_model=DeterminationsResponse)
async def get_determinations(
    trigger_id: str = Path(
        ...,
        description="Trigger identifier, e.g. 'flight-delay-del'",
    ),
    limit: int = Query(
        20,
        ge=1,
        le=100,
        description="Maximum number of determinations to return (1-100, default 20)",
    ),
    _key=Depends(verify_api_key),
):
    """
    Get recent cryptographically signed oracle determinations for a trigger.

    Returns the most recent Ed25519-signed determinations in reverse chronological
    order. Each determination includes a data snapshot hash and signature that can
    be independently verified against the oracle public key.

    Example response:
    ```json
    {
      "trigger_id": "flight-delay-del",
      "determinations": [{"fired": true, "timestamp": "2026-03-25T10:00:00Z", "signature": "ed25519:..."}],
      "count": 1
    }
    ```
    """
    jsonl_path = _ORACLE_LOG_DIR / "oracle_log.jsonl"
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


@app.get("/v1/status", tags=["Status"], response_model=StatusResponse)
async def get_status(_key=Depends(verify_api_key)):
    """
    Get data source health across all peril categories.

    Returns per-peril statistics showing how many triggers have fresh cached data,
    stale data, or no data at all. Use this endpoint to monitor overall platform
    health and data freshness.

    Example response:
    ```json
    {
      "perils": {"flight_delay": {"label": "Flight Delay", "total": 144, "cached": 130, "stale": 10, "no_data": 4, "coverage_pct": 90}},
      "total_triggers": 521
    }
    ```
    """
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


# ── Source-level freshness (FRESH-01a) ──

SOURCE_NAMES = {
    "flights": "Flight Delay (FAA/AviationStack/OpenSky)",
    "aqi": "Air Quality (AirNow/WAQI/OpenAQ)",
    "weather": "Weather (Open-Meteo)",
    "fire": "Wildfire (NASA FIRMS)",
    "drought": "Drought (CHIRPS/GPM IMERG)",
    "earthquake": "Earthquake (USGS)",
    "marine": "Marine (AISstream)",
    "flood": "Flood (USGS Water Services)",
    "cyclone": "Cyclone (NOAA NHC)",
    "ndvi": "Crop/NDVI (Copernicus/MODIS)",
    "solar": "Solar (NOAA SWPC)",
    "health": "Health (WHO DON)",
}


@app.get("/v1/health", tags=["Status"], response_model=HealthResponse)
async def get_health(_key=Depends(verify_api_key)):
    """
    Per-source data freshness with traffic-light status.

    Scans the monitor cache directory and groups files by source prefix.
    For each source, computes freshness metrics including the most recent
    fetch time, fresh/stale file counts, and a traffic-light indicator
    (green >80% fresh, amber >50%, red otherwise).

    Example response:
    ```json
    {
      "sources": [
        {"source": "flights", "name": "Flight Delay (FAA/AviationStack/OpenSky)",
         "last_fetch": "2026-03-25T10:05:00Z", "age_seconds": 120,
         "file_count": 144, "fresh_count": 140, "stale_count": 4, "freshness": "green"}
      ],
      "total_files": 521,
      "overall_freshness": "green"
    }
    ```
    """
    import time as _time
    from datetime import datetime, timezone

    now = _time.time()
    source_buckets: dict[str, list[dict]] = {prefix: [] for prefix in SOURCE_NAMES}

    # Scan all JSON files in cache directory
    if CACHE_DIR.is_dir():
        for path in sorted(CACHE_DIR.glob("*.json")):
            try:
                entry = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue

            fname = path.stem  # e.g. "flights_flight-delay-del"
            matched = False
            for prefix in SOURCE_NAMES:
                if fname.startswith(prefix + "_"):
                    source_buckets[prefix].append(entry)
                    matched = True
                    break
            # Files that don't match any known prefix are ignored

    sources = []
    total_files = 0
    total_fresh = 0

    for prefix, entries in source_buckets.items():
        file_count = len(entries)
        total_files += file_count

        if file_count == 0:
            sources.append({
                "source": prefix,
                "name": SOURCE_NAMES[prefix],
                "last_fetch": None,
                "age_seconds": None,
                "file_count": 0,
                "fresh_count": 0,
                "stale_count": 0,
                "freshness": "red",
            })
            continue

        fresh_count = sum(1 for e in entries if e.get("expires_at", 0) > now)
        stale_count = file_count - fresh_count
        total_fresh += fresh_count

        # Most recent cached_at across all files for this source
        latest_ts = max(e.get("cached_at", 0) for e in entries)
        age_seconds = round(now - latest_ts, 1) if latest_ts > 0 else None
        last_fetch_iso = (
            datetime.fromtimestamp(latest_ts, tz=timezone.utc).isoformat()
            if latest_ts > 0 else None
        )

        pct = fresh_count / file_count
        if pct > 0.8:
            freshness = "green"
        elif pct > 0.5:
            freshness = "amber"
        else:
            freshness = "red"

        sources.append({
            "source": prefix,
            "name": SOURCE_NAMES[prefix],
            "last_fetch": last_fetch_iso,
            "age_seconds": age_seconds,
            "file_count": file_count,
            "fresh_count": fresh_count,
            "stale_count": stale_count,
            "freshness": freshness,
        })

    # Overall freshness
    if total_files == 0:
        overall = "red"
    else:
        overall_pct = total_fresh / total_files
        if overall_pct > 0.8:
            overall = "green"
        elif overall_pct > 0.5:
            overall = "amber"
        else:
            overall = "red"

    return {"sources": sources, "total_files": total_files, "overall_freshness": overall}


@app.get("/v1/ports", tags=["Marine"], response_model=PortListResponse)
async def list_ports(_key=Depends(verify_api_key)):
    """
    List all monitored marine ports with coordinates and identifiers.

    Returns port metadata including UN/LOCODE, geographic coordinates, and tier
    classification. Tier-1 ports are the 10 highest-volume global ports with
    anchorage bounding boxes for vessel tracking.

    Example response:
    ```json
    {
      "ports": [{"id": "port-sgp-jurong", "name": "Port of Singapore (Jurong)", "un_locode": "SGSIN", "tier": "tier1"}],
      "count": 10
    }
    ```
    """
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


@app.get("/v1/triggers/{trigger_id}/model-history", tags=["Learning"], response_model=ModelHistoryResponse)
async def get_model_history(
    trigger_id: str = Path(
        ...,
        description="Trigger identifier, e.g. 'flight-delay-del'",
    ),
    limit: int = Query(
        20,
        ge=1,
        le=100,
        description="Maximum number of model versions to return (1-100, default 20)",
    ),
    _key=Depends(verify_api_key),
):
    """
    Get machine learning model version history for a trigger.

    Returns a chronological list of model versions trained for this trigger,
    including accuracy metrics and training metadata. Model history is only
    available for triggers that have sufficient historical data.

    Example response:
    ```json
    {
      "trigger_id": "flight-delay-del",
      "versions": [{"version": 1, "accuracy": 0.92, "trained_at": "2026-03-20T12:00:00Z"}],
      "count": 1
    }
    ```
    """
    try:
        from gad.engine.db_read import get_model_versions
        rows = get_model_versions(trigger_id, limit=limit)
        if rows is None or rows.empty:
            return {"trigger_id": trigger_id, "versions": [], "count": 0}
        return {"trigger_id": trigger_id, "versions": rows.to_dict("records"), "count": len(rows)}
    except Exception as e:
        return {"trigger_id": trigger_id, "versions": [], "count": 0, "error": str(e)}


@app.get("/v1/perils", tags=["Status"], response_model=PerilListResponse)
async def list_perils(_key=Depends(verify_api_key)):
    """
    List all peril categories with their display labels.

    Returns a mapping of peril keys (used in API filters) to human-readable
    labels. Use the keys from this endpoint as values for the `peril` query
    parameter on other endpoints.

    Example response:
    ```json
    {
      "perils": {"flight_delay": "Flight Delay", "earthquake": "Earthquake"},
      "count": 12
    }
    ```
    """
    return {"perils": {k: v for k, v in PERIL_LABELS.items()}, "count": len(PERIL_LABELS)}


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


# ── Intelligence endpoints (SL-08a-d) ──

@app.get("/v1/intelligence/peril-patterns", tags=["Intelligence"], response_model=PerilPatternsResponse)
async def get_peril_patterns(_key=Depends(verify_api_key)):
    """
    Peril-level pattern analysis across all triggers.

    Aggregates firing rates and data freshness per peril category. For each
    peril, returns the number of triggers that are currently triggered (fired),
    normal, stale, or missing data, plus the overall firing rate.

    Example response:
    ```json
    {
      "patterns": {
        "earthquake": {"label": "Earthquake", "total": 30, "fired": 2, "normal": 25, "stale": 2, "no_data": 1, "firing_rate": 0.067}
      },
      "total_triggers": 521
    }
    ```
    """
    patterns: dict[str, dict] = {}

    for peril_key, label in PERIL_LABELS.items():
        triggers = get_triggers_by_peril(peril_key)
        fired = 0
        normal = 0
        stale = 0
        no_data = 0

        for t in triggers:
            source_key = SOURCE_KEY_MAP.get(t.data_source, t.data_source)
            data, is_stale = read_cache_with_staleness(source_key, t.id)

            if data is None:
                no_data += 1
                continue

            if is_stale:
                stale += 1
                continue

            # Evaluate whether the trigger has fired
            value = data.get("value") if isinstance(data, dict) else None
            if value is not None:
                trigger_fired = (value > t.threshold) if t.fires_when_above else (value < t.threshold)
                if trigger_fired:
                    fired += 1
                else:
                    normal += 1
            else:
                normal += 1

        total = len(triggers)
        evaluable = fired + normal
        firing_rate = round(fired / evaluable, 4) if evaluable > 0 else 0.0

        patterns[peril_key] = {
            "label": label,
            "total": total,
            "fired": fired,
            "normal": normal,
            "stale": stale,
            "no_data": no_data,
            "firing_rate": firing_rate,
        }

    return {"patterns": patterns, "total_triggers": len(GLOBAL_TRIGGERS)}


@app.get("/v1/intelligence/location/{lat}/{lon}", tags=["Intelligence"], response_model=LocationIntelligenceResponse)
async def get_location_intelligence(
    lat: float = Path(..., description="Latitude of search centre"),
    lon: float = Path(..., description="Longitude of search centre"),
    radius_km: float = Query(500, ge=1, le=20000, description="Search radius in kilometres (default 500)"),
    _key=Depends(verify_api_key),
):
    """
    All triggers within radius_km of a geographic point, with their current status.

    Returns triggers sorted by distance from the search centre. Each entry includes
    the trigger's cached data availability and distance in km.

    Example response:
    ```json
    {
      "lat": 28.56,
      "lon": 77.10,
      "radius_km": 200,
      "triggers": [{"id": "flight-delay-del", "distance_km": 12.3, "peril": "flight_delay"}],
      "count": 8
    }
    ```
    """
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
                "peril_label": PERIL_LABELS.get(t.peril, t.peril),
                "lat": t.lat,
                "lon": t.lon,
                "location_label": t.location_label,
                "distance_km": round(dist, 1),
                "threshold": t.threshold,
                "threshold_unit": t.threshold_unit,
                "data_source": t.data_source,
                "has_data": data is not None,
                "is_stale": is_stale,
            })

    matches.sort(key=lambda m: m["distance_km"])
    return {"lat": lat, "lon": lon, "radius_km": radius_km, "triggers": matches, "count": len(matches)}


@app.get("/v1/intelligence/climate-zone/{zone}", tags=["Intelligence"], response_model=ClimateZoneResponse)
async def get_climate_zone(
    zone: str = Path(..., description="Climate zone identifier, e.g. 'Af' (Koppen)"),
    _key=Depends(verify_api_key),
):
    """
    Triggers in a Koppen climate zone (placeholder — needs Koppen data from Phase 3).

    This endpoint will return triggers located in the specified Koppen climate
    zone once the zone classification data is integrated in Phase 3.
    Currently returns an empty trigger list with a status message.
    """
    return {
        "zone": zone,
        "message": "Climate zone lookup available after Phase 3 (Koppen zone classification)",
        "triggers": [],
        "count": 0,
    }


# ── Model drift endpoint (SL-09d) ──

@app.get("/v1/triggers/{trigger_id}/model-drift", tags=["Learning"], response_model=ModelDriftResponse)
async def get_model_drift(
    trigger_id: str = Path(..., description="Trigger identifier, e.g. 'flight-delay-del'"),
    _key=Depends(verify_api_key),
):
    """
    Get model drift status for a trigger.

    Checks whether the most recent model version for a trigger shows
    performance degradation compared to earlier versions. Drift is flagged
    when accuracy drops by more than 5 percentage points.

    Example response:
    ```json
    {
      "trigger_id": "flight-delay-del",
      "drift_detected": false,
      "current_accuracy": 0.92,
      "baseline_accuracy": 0.94,
      "message": "No significant drift detected"
    }
    ```
    """
    trigger = get_trigger_by_id(trigger_id)
    if not trigger:
        raise HTTPException(status_code=404, detail=f"Trigger '{trigger_id}' not found")

    try:
        from gad.engine.db_read import get_model_versions
        rows = get_model_versions(trigger_id, limit=10)
        if rows is None or rows.empty or len(rows) < 2:
            return {
                "trigger_id": trigger_id,
                "drift_detected": False,
                "current_accuracy": None,
                "baseline_accuracy": None,
                "message": "Insufficient model history for drift analysis",
            }

        # Compare latest version accuracy against the baseline (first version)
        baseline_acc = float(rows.iloc[0].get("accuracy", 0))
        current_acc = float(rows.iloc[-1].get("accuracy", 0))
        drift = baseline_acc - current_acc > 0.05

        return {
            "trigger_id": trigger_id,
            "drift_detected": drift,
            "current_accuracy": round(current_acc, 4),
            "baseline_accuracy": round(baseline_acc, 4),
            "message": "Drift detected — accuracy dropped >5pp" if drift else "No significant drift detected",
        }
    except Exception:
        return {
            "trigger_id": trigger_id,
            "drift_detected": False,
            "current_accuracy": None,
            "baseline_accuracy": None,
            "message": "Model history not available",
        }
