"""
Background data fetcher with multi-source fallback.

Each peril has multiple data sources tried in priority order. If the primary
source fails or is rate-limited, the fetcher falls back to the next source.

Security model:
- Users NEVER trigger API calls
- This script runs on a timer, not on user request
- Even if someone hammers the dashboard, they only get cached data

Usage:
    python -m gad.monitor.fetcher          # Run once (for cron)
    python -m gad.monitor.fetcher --loop   # Run continuously (for Fly.io)
"""

from __future__ import annotations

import logging
import os
import sys
import time

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

from gad.monitor.cache import read_cache_with_staleness
from gad.monitor.triggers import GLOBAL_TRIGGERS, MonitorTrigger
from gad.monitor.protocol import SourceConfig, fetch_with_fallback
from gad.monitor.sources import openmeteo, openaq, firms, opensky, chirps_monitor
from gad.monitor.sources import aviationstack, airnow, gpm_imerg, usgs_earthquake, aisstream
from gad.monitor.sources import noaa_flood, noaa_nhc, ndvi, noaa_swpc
from gad.monitor.sources import noaa_flood, noaa_nhc, ndvi, who_don
from gad.monitor.ports import ALL_PORTS, get_port_by_id
from gad.engine.oracle import (
    sign_determination, append_to_oracle_log, read_last_hash,
    data_snapshot_hash, _load_private_key, GENESIS_HASH,
)
from gad.engine.models import TriggerDetermination
from gad.engine.r2_upload import upload_determination as r2_upload
from gad.engine.version import get_gad_version

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("gad.monitor.fetcher")


# ── Source configurations per peril ──
# Lower priority number = tried first

def _is_us_airport(trigger: MonitorTrigger) -> bool:
    """Check if trigger is at a US airport (for AirNow)."""
    from gad.monitor.airports import ALL_AIRPORTS
    iata = trigger.id.split("-")[-1].upper()
    return any(a.iata == iata and a.country == "USA" for a in ALL_AIRPORTS)


def _is_tier1_airport(trigger: MonitorTrigger) -> bool:
    """Check if trigger is at a tier-1 airport (for AviationStack rate limits)."""
    from gad.monitor.airports import ALL_AIRPORTS
    iata = trigger.id.split("-")[-1].upper()
    return any(a.iata == iata and a.tier == 1 for a in ALL_AIRPORTS)


def _get_iata(trigger: MonitorTrigger) -> str:
    return trigger.id.split("-")[-1].upper()


def fetch_flight_delay(trigger: MonitorTrigger) -> dict | None:
    """Multi-source flight delay: AviationStack (tier-1) → OpenSky (all)."""
    iata = _get_iata(trigger)

    sources = []

    # AviationStack: only for tier-1 (500 req/mo free = ~16/day)
    if _is_tier1_airport(trigger) and os.environ.get("AVIATIONSTACK_API_KEY"):
        sources.append(SourceConfig(
            name="aviationstack", priority=1,
            fetch_fn=lambda: aviationstack.fetch_departures(iata, trigger.id),
            rate_limit_note="500 req/mo free",
        ))

    # OpenSky: all airports (4000 credits/day with OAuth2)
    icao = opensky.AIRPORT_ICAO_MAP.get(trigger.id)
    if icao:
        sources.append(SourceConfig(
            name="opensky", priority=2,
            fetch_fn=lambda: opensky.fetch_departures(icao, trigger.id),
            rate_limit_note="4000 credits/day",
        ))

    if not sources:
        return None

    result = fetch_with_fallback(sources)
    if result.data:
        log.debug(f"  {trigger.id}: used {result.source_used} (tried {result.sources_tried})")
    return result.data


def fetch_air_quality(trigger: MonitorTrigger) -> dict | None:
    """Multi-source AQI: AirNow (US) → WAQI → OpenAQ."""
    sources = []

    # AirNow: US airports only (authoritative)
    if _is_us_airport(trigger) and os.environ.get("AIRNOW_API_KEY"):
        sources.append(SourceConfig(
            name="airnow", priority=1,
            fetch_fn=lambda: airnow.fetch_aqi(trigger.lat, trigger.lon, trigger.id),
        ))

    # WAQI: global (good coverage with real token)
    sources.append(SourceConfig(
        name="waqi", priority=2,
        fetch_fn=lambda: openaq.fetch_aqi(trigger.lat, trigger.lon, trigger.id),
    ))

    result = fetch_with_fallback(sources)
    if result.data:
        log.debug(f"  {trigger.id}: used {result.source_used}")
    return result.data


def fetch_wildfire(trigger: MonitorTrigger) -> dict | None:
    """Multi-source wildfire: FIRMS VIIRS+MODIS (already merged in firms.py)."""
    return firms.fetch_fires(trigger.lat, trigger.lon, trigger.id)


def fetch_weather(trigger: MonitorTrigger) -> dict | None:
    """Weather: Open-Meteo (free, no limits)."""
    return openmeteo.fetch_weather(trigger.lat, trigger.lon, trigger.id)


def fetch_drought(trigger: MonitorTrigger) -> dict | None:
    """Multi-source drought: GPM IMERG (daily) → CHIRPS (monthly)."""
    sources = []

    if os.environ.get("NASA_EARTHDATA_TOKEN"):
        sources.append(SourceConfig(
            name="gpm_imerg", priority=1,
            fetch_fn=lambda: gpm_imerg.fetch_precipitation(trigger.lat, trigger.lon, trigger.id),
        ))

    sources.append(SourceConfig(
        name="chirps", priority=2,
        fetch_fn=lambda: chirps_monitor.fetch_rainfall(trigger.lat, trigger.lon, trigger.id),
    ))

    result = fetch_with_fallback(sources)
    if result.data:
        log.debug(f"  {trigger.id}: used {result.source_used}")
    return result.data


def fetch_earthquake(trigger: MonitorTrigger) -> dict | None:
    """Earthquake: USGS (free, no key, real-time)."""
    return usgs_earthquake.fetch_earthquakes(trigger.lat, trigger.lon, trigger.id)


def fetch_marine(trigger: MonitorTrigger) -> dict | None:
    """Marine: AISstream WebSocket (requires API key)."""
    # Extract port ID from trigger ID: "marine-congestion-port-singapore" -> "port-singapore"
    parts = trigger.id.split("-", 2)  # ["marine", "congestion", "port-singapore"]
    if len(parts) < 3:
        return None
    port_id = parts[2]
    port = get_port_by_id(port_id)
    if not port:
        return None
    return aisstream.fetch_port_vessels(port.id, port.anchor_bbox)


def fetch_flood(trigger: MonitorTrigger) -> dict | None:
    """Flood: USGS river gauge (free, no key)."""
    site_id = trigger.id.replace("flood-", "")
    return noaa_flood.fetch_gauge(site_id, trigger.id)


def fetch_cyclone(trigger: MonitorTrigger) -> dict | None:
    """Tropical cyclone: NOAA NHC active storms (free, no key)."""
    return noaa_nhc.fetch_active_storms(trigger.lat, trigger.lon, trigger.id)


def fetch_crop_ndvi(trigger: MonitorTrigger) -> dict | None:
    """Crop/NDVI: Copernicus or MODIS (free, no key)."""
    return ndvi.fetch_ndvi(trigger.lat, trigger.lon, trigger.id)


def fetch_solar(trigger: MonitorTrigger) -> dict | None:
    """Solar/Space Weather: NOAA SWPC Kp index (free, no key)."""
    return noaa_swpc.fetch_kp_index(trigger.id)
def fetch_health(trigger: MonitorTrigger) -> dict | None:
    """Health/Pandemic: WHO Disease Outbreak News (free, no key)."""
    return who_don.fetch_outbreaks(trigger.lat, trigger.lon, trigger.id)


# ── Peril → fetch function mapping ──
FETCH_MAP = {
    "opensky": fetch_flight_delay,
    "openaq": fetch_air_quality,
    "firms": fetch_wildfire,
    "openmeteo": fetch_weather,
    "chirps": fetch_drought,
    "usgs": fetch_earthquake,
    "aisstream": fetch_marine,
    "usgs_water": fetch_flood,
    "noaa_nhc": fetch_cyclone,
    "ndvi": fetch_crop_ndvi,
    "noaa_swpc": fetch_solar,
    "who_don": fetch_health,
}

# ── Cache TTL per source type (seconds) ──
SOURCE_CACHE_KEY = {
    "opensky": "flights",
    "openaq": "aqi",
    "firms": "fire",
    "openmeteo": "weather",
    "chirps": "drought",
    "usgs": "earthquake",
    "aisstream": "marine",
    "usgs_water": "flood",
    "noaa_nhc": "cyclone",
    "ndvi": "ndvi",
    "noaa_swpc": "solar",
    "who_don": "health",
}


_health_logged = False


def _log_data_source_health() -> None:
    """Log availability of every data source on first run. Never crashes."""
    global _health_logged
    if _health_logged:
        return
    _health_logged = True

    # Each entry: (env_var, source_label, required)
    sources = [
        ("SUPABASE_URL", "Supabase (auth/analytics)", True),
        ("SUPABASE_ANON_KEY", "Supabase anon key", True),
        ("SUPABASE_SERVICE_KEY", "Supabase service key", True),
        ("NASA_FIRMS_MAP_KEY", "FIRMS wildfire (VIIRS+MODIS)", False),
        ("WAQI_API_TOKEN", "WAQI air quality", False),
        ("OPENSKY_CLIENT_ID", "OpenSky flights (OAuth2)", False),
        ("OPENSKY_CLIENT_SECRET", "OpenSky flights (secret)", False),
        ("AVIATIONSTACK_API_KEY", "AviationStack flight delays", False),
        ("OPENAQ_API_KEY", "OpenAQ v3 air quality", False),
        ("AIRNOW_API_KEY", "AirNow US AQI", False),
        ("NASA_EARTHDATA_TOKEN", "GPM IMERG precipitation", False),
        ("AISSTREAM_API_KEY", "AISstream marine data", False),
        ("GAD_ORACLE_PRIVATE_KEY_HEX", "Oracle signing (private key)", False),
        ("GAD_ORACLE_PUBLIC_KEY_HEX", "Oracle signing (public key)", False),
        ("GAD_ORACLE_KEY_ID", "Oracle key ID", False),
        ("R2_ACCOUNT_ID", "R2 upload (account)", False),
        ("R2_ACCESS_KEY_ID", "R2 upload (access key)", False),
        ("R2_SECRET_ACCESS_KEY", "R2 upload (secret key)", False),
        ("ANTHROPIC_API_KEY", "AI risk briefs", False),
    ]

    available = 0
    total = len(sources)

    for env_var, label, required in sources:
        try:
            if os.environ.get(env_var):
                log.info(f"  [OK] {label} ({env_var})")
                available += 1
            else:
                level = "REQUIRED" if required else "optional"
                log.warning(f"  [--] {label} ({env_var}) — {level}, not set")
        except Exception:
            log.warning(f"  [--] {label} ({env_var}) — error checking")

    log.info(f"Data sources: {available}/{total} available")


def _should_fetch(source: str, trigger_id: str) -> bool:
    cache_key = SOURCE_CACHE_KEY.get(source, source)
    data, is_stale = read_cache_with_staleness(cache_key, trigger_id)
    return data is None or is_stale


def _evaluate_fired(trigger: MonitorTrigger, data: dict) -> bool:
    """Quick evaluation: did the trigger fire?"""
    if trigger.data_source == "openmeteo":
        r = openmeteo.evaluate_trigger(data, trigger.threshold, trigger.threshold_unit, trigger.fires_when_above)
    elif trigger.data_source == "openaq":
        r = openaq.evaluate_trigger(data, trigger.threshold)
    elif trigger.data_source == "firms":
        r = firms.evaluate_trigger(data, trigger.threshold)
    elif trigger.data_source == "opensky":
        r = opensky.evaluate_trigger(data, trigger.threshold)
    elif trigger.data_source == "chirps":
        r = chirps_monitor.evaluate_trigger(data, trigger.threshold)
    elif trigger.data_source == "usgs":
        r = usgs_earthquake.evaluate_trigger(data, trigger.threshold)
    elif trigger.data_source == "aisstream":
        r = aisstream.evaluate_trigger(data, trigger.threshold, trigger.threshold_unit)
    elif trigger.data_source == "usgs_water":
        r = noaa_flood.evaluate_trigger(data, trigger.threshold)
    elif trigger.data_source == "noaa_nhc":
        r = noaa_nhc.evaluate_trigger(data, trigger.threshold)
    elif trigger.data_source == "ndvi":
        r = ndvi.evaluate_trigger(data, trigger.threshold)
    elif trigger.data_source == "noaa_swpc":
        r = noaa_swpc.evaluate_trigger(data, trigger.threshold)
    elif trigger.data_source == "who_don":
        r = who_don.evaluate_trigger(data, trigger.threshold)
    else:
        return False
    return r.get("fired", False)


def _create_determination(trigger: MonitorTrigger, data: dict, fired: bool) -> TriggerDetermination:
    """Create a TriggerDetermination from a fetch result."""
    raw_bytes = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
    return TriggerDetermination(
        determination_id=uuid4(),
        policy_id=UUID("00000000-0000-0000-0000-000000000000"),  # no policy binding in v0.2
        trigger_id=UUID(int=hash(trigger.id) % (2**128)),  # deterministic UUID from trigger ID
        fired=fired,
        fired_at=datetime.now(timezone.utc) if fired else None,
        data_snapshot_hash=data_snapshot_hash(raw_bytes),
        computation_version=get_gad_version(),
        prev_hash=GENESIS_HASH,  # placeholder, updated during signing
    )


# Oracle signing state
_oracle_signing_enabled = False
_private_key: bytes | None = None
_key_id: str | None = None


def _init_oracle_signing() -> None:
    """Initialize oracle signing if private key is available."""
    global _oracle_signing_enabled, _private_key, _key_id
    _private_key = _load_private_key()
    _key_id = os.environ.get("GAD_ORACLE_KEY_ID")
    _oracle_signing_enabled = _private_key is not None
    if _oracle_signing_enabled:
        log.info(f"Oracle signing ENABLED (key_id={_key_id})")
    else:
        log.info("Oracle signing DISABLED (no GAD_ORACLE_PRIVATE_KEY_HEX)")


def fetch_all(diagnostic: bool = False) -> dict:
    """Fetch all triggers that need updating. Sign determinations if key is available."""
    global _oracle_signing_enabled

    _log_data_source_health()

    if not _oracle_signing_enabled:
        _init_oracle_signing()

    fetched = 0
    skipped = 0
    errors = 0
    signed = 0

    # Diagnostic mode: track AQI trigger results
    aqi_diag_rows: list[dict] = []
    aqi_total = 0
    aqi_got_data = 0

    prev_hash = read_last_hash() if _oracle_signing_enabled else GENESIS_HASH

    for trigger in GLOBAL_TRIGGERS:
        if not _should_fetch(trigger.data_source, trigger.id):
            skipped += 1
            continue

        fetch_fn = FETCH_MAP.get(trigger.data_source)
        if not fetch_fn:
            errors += 1
            continue

        try:
            result = fetch_fn(trigger)

            # Diagnostic: collect AQI trigger info
            if diagnostic and trigger.data_source == "openaq":
                aqi_total += 1
                if result is not None:
                    aqi_got_data += 1
                    aqi_diag_rows.append({
                        "trigger_id": trigger.id,
                        "source": result.get("source", "unknown"),
                        "station": result.get("station_name", "—"),
                        "lat": trigger.lat,
                        "lon": trigger.lon,
                    })
                else:
                    aqi_diag_rows.append({
                        "trigger_id": trigger.id,
                        "source": "none",
                        "station": "—",
                        "lat": trigger.lat,
                        "lon": trigger.lon,
                    })

            if result is not None:
                fetched += 1

                # Oracle signing: create and sign a determination for every evaluation
                if _oracle_signing_enabled and _private_key:
                    try:
                        fired = _evaluate_fired(trigger, result)
                        det = _create_determination(trigger, result, fired)
                        signed_det = sign_determination(det, _private_key, prev_hash, _key_id)
                        prev_hash = append_to_oracle_log(signed_det)
                        signed += 1
                        # Upload to R2 (optional — skipped if no R2 credentials)
                        r2_upload(
                            str(signed_det.determination_id),
                            signed_det.model_dump_json(indent=2),
                        )
                    except Exception as e:
                        log.warning(f"Oracle signing failed for {trigger.id}: {e}")

                if fetched % 50 == 0:
                    log.info(f"Progress: {fetched} fetched, {signed} signed, {errors} errors")
            else:
                errors += 1
        except Exception as e:
            errors += 1
            log.error(f"Error fetching {trigger.id}: {e}")

        time.sleep(0.3)

    # Diagnostic: print AQI table and summary
    if diagnostic and aqi_diag_rows:
        print("\n── AQI Diagnostic ──")
        print(f"{'TRIGGER_ID':<25} {'SOURCE':<10} {'STATION':<40} COORDS")
        print("─" * 100)
        for row in aqi_diag_rows:
            print(f"{row['trigger_id']:<25} {row['source']:<10} {row['station']:<40} {row['lat']},{row['lon']}")
        print("─" * 100)
        aqi_no_data = aqi_total - aqi_got_data
        print(f"AQI summary: {aqi_total} total, {aqi_got_data} got data, {aqi_no_data} no data\n")

    summary = {"fetched": fetched, "skipped": skipped, "errors": errors, "signed": signed}
    log.info(f"Fetch complete: {summary}")
    return summary


def run_loop(interval_seconds: int = 900) -> None:
    """Run fetch_all in a loop. For Fly.io continuous process."""
    log.info(f"Starting fetch loop (interval={interval_seconds}s)")
    while True:
        try:
            fetch_all()
        except Exception as e:
            log.error(f"Fetch loop error: {e}")
        time.sleep(interval_seconds)


if __name__ == "__main__":
    _diagnostic_mode = "--diagnostic" in sys.argv
    if "--loop" in sys.argv:
        interval = 900
        for i, arg in enumerate(sys.argv):
            if arg == "--interval" and i + 1 < len(sys.argv):
                interval = int(sys.argv[i + 1])
        run_loop(interval)
    else:
        fetch_all(diagnostic=_diagnostic_mode)
