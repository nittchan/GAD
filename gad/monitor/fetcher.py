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

from gad.monitor.cache import read_cache_with_staleness
from gad.monitor.triggers import GLOBAL_TRIGGERS, MonitorTrigger
from gad.monitor.protocol import SourceConfig, fetch_with_fallback
from gad.monitor.sources import openmeteo, openaq, firms, opensky, chirps_monitor
from gad.monitor.sources import aviationstack, airnow, gpm_imerg

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


# ── Peril → fetch function mapping ──
FETCH_MAP = {
    "opensky": fetch_flight_delay,
    "openaq": fetch_air_quality,
    "firms": fetch_wildfire,
    "openmeteo": fetch_weather,
    "chirps": fetch_drought,
}

# ── Cache TTL per source type (seconds) ──
SOURCE_CACHE_KEY = {
    "opensky": "flights",
    "openaq": "aqi",
    "firms": "fire",
    "openmeteo": "weather",
    "chirps": "drought",
}


def _should_fetch(source: str, trigger_id: str) -> bool:
    cache_key = SOURCE_CACHE_KEY.get(source, source)
    data, is_stale = read_cache_with_staleness(cache_key, trigger_id)
    return data is None or is_stale


def fetch_all() -> dict:
    """Fetch all triggers that need updating. Returns summary."""
    fetched = 0
    skipped = 0
    errors = 0

    for trigger in GLOBAL_TRIGGERS:
        if not _should_fetch(trigger.data_source, trigger.id):
            skipped += 1
            continue

        fetch_fn = FETCH_MAP.get(trigger.data_source)
        if not fetch_fn:
            log.warning(f"No fetch function for source: {trigger.data_source}")
            errors += 1
            continue

        try:
            result = fetch_fn(trigger)
            if result is not None:
                fetched += 1
                if fetched % 20 == 0:
                    log.info(f"Progress: {fetched} fetched, {skipped} skipped, {errors} errors")
            else:
                errors += 1
        except Exception as e:
            errors += 1
            log.error(f"Error fetching {trigger.id}: {e}")

        # Small delay between API calls to be polite
        time.sleep(0.3)

    summary = {"fetched": fetched, "skipped": skipped, "errors": errors}
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
