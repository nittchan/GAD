"""
Background data fetcher. Runs on a schedule (cron or Fly.io scheduled machine).
Fetches all data sources and writes to cache. The dashboard reads ONLY from cache.

Security model:
- Users NEVER trigger API calls
- This script runs on a timer, not on user request
- Rate limits are respected by controlling fetch frequency here
- Even if someone hammers the dashboard, they only get cached data

Usage:
    python -m gad.monitor.fetcher          # Run once (for cron)
    python -m gad.monitor.fetcher --loop   # Run continuously (for Fly.io)
"""

from __future__ import annotations

import logging
import sys
import time

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from gad.monitor.cache import read_cache_with_staleness
from gad.monitor.triggers import GLOBAL_TRIGGERS, MonitorTrigger
from gad.monitor.sources import openmeteo, openaq, firms, opensky, chirps_monitor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("gad.monitor.fetcher")

# Fetch interval per source (seconds) — respects rate limits
# With 200+ airports, we need longer TTLs to stay within API limits
# OpenSky: 4000 credits/day → ~3 fetches/airport/day (every 8h)
# OpenAQ/WAQI: generous but 150+ cities → every 2h
# Open-Meteo: free, no limits → every 1h
# FIRMS: 5000 txn/10min → generous for 8 fire zones
# CHIRPS: monthly data → every 6h
INTERVALS = {
    "openmeteo": 3600,    # 1 hour — free, no limits
    "openaq": 7200,       # 2 hours — 150+ cities
    "firms": 3600,        # 1 hour — only ~8 fire zones
    "opensky": 28800,     # 8 hours — 200+ airports, 4000 credits/day
    "chirps": 21600,      # 6 hours — monthly data
}


def _should_fetch(source: str, trigger_id: str) -> bool:
    """Check if we should fetch (cache expired or missing)."""
    data, is_stale = read_cache_with_staleness(source, trigger_id)
    return data is None or is_stale


def fetch_trigger(trigger: MonitorTrigger) -> dict | None:
    """Fetch data for a single trigger from its data source."""
    source = trigger.data_source

    if source == "openmeteo":
        return openmeteo.fetch_weather(trigger.lat, trigger.lon, trigger.id)
    elif source == "openaq":
        return openaq.fetch_aqi(trigger.lat, trigger.lon, trigger.id)
    elif source == "firms":
        return firms.fetch_fires(trigger.lat, trigger.lon, trigger.id)
    elif source == "opensky":
        icao = opensky.AIRPORT_ICAO_MAP.get(trigger.id)
        if icao:
            return opensky.fetch_departures(icao, trigger.id)
        return None
    elif source == "chirps":
        return chirps_monitor.fetch_rainfall(trigger.lat, trigger.lon, trigger.id)
    else:
        log.warning(f"Unknown source: {source} for trigger {trigger.id}")
        return None


def fetch_all() -> dict:
    """Fetch all triggers that need updating. Returns summary."""
    fetched = 0
    skipped = 0
    errors = 0

    for trigger in GLOBAL_TRIGGERS:
        source_key = {
            "openmeteo": "weather",
            "openaq": "aqi",
            "firms": "fire",
            "opensky": "flights",
            "chirps": "drought",
        }.get(trigger.data_source, trigger.data_source)

        if not _should_fetch(source_key, trigger.id):
            skipped += 1
            continue

        try:
            result = fetch_trigger(trigger)
            if result is not None:
                fetched += 1
                log.info(f"Fetched {trigger.id} ({trigger.data_source})")
            else:
                errors += 1
                log.warning(f"No data for {trigger.id} ({trigger.data_source})")
        except Exception as e:
            errors += 1
            log.error(f"Error fetching {trigger.id}: {e}")

        # Small delay between API calls to be polite
        time.sleep(0.5)

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
        interval = 900  # 15 minutes default
        for i, arg in enumerate(sys.argv):
            if arg == "--interval" and i + 1 < len(sys.argv):
                interval = int(sys.argv[i + 1])
        run_loop(interval)
    else:
        fetch_all()
