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


# ── Peril → fetch function mapping ──
FETCH_MAP = {
    "opensky": fetch_flight_delay,
    "openaq": fetch_air_quality,
    "firms": fetch_wildfire,
    "openmeteo": fetch_weather,
    "chirps": fetch_drought,
    "usgs": fetch_earthquake,
    "aisstream": fetch_marine,
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
}


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


def fetch_all() -> dict:
    """Fetch all triggers that need updating. Sign determinations if key is available."""
    global _oracle_signing_enabled

    if not _oracle_signing_enabled:
        _init_oracle_signing()

    fetched = 0
    skipped = 0
    errors = 0
    signed = 0

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
    if "--loop" in sys.argv:
        interval = 900
        for i, arg in enumerate(sys.argv):
            if arg == "--interval" and i + 1 < len(sys.argv):
                interval = int(sys.argv[i + 1])
        run_loop(interval)
    else:
        fetch_all()
