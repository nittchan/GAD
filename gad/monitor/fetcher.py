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

import fcntl
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
from gad.monitor.sources import noaa_flood, noaa_nhc, ndvi, noaa_swpc, who_don, faa_atcscc
from gad.monitor.ports import ALL_PORTS, get_port_by_id
from gad.engine.oracle import (
    sign_determination, append_to_oracle_log, read_last_hash,
    data_snapshot_hash, _load_private_key, GENESIS_HASH,
)
from gad.engine.models import TriggerDetermination
from gad.engine.r2_upload import upload_determination as r2_upload, upload_to_r2_key
from gad.engine.version import get_gad_version

from gad.config import DATA_ROOT

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("gad.monitor.fetcher")


# ── DB-01d: Volume health check ──
def _check_volume_health() -> None:
    """Write/read/delete test file to verify volume is mounted and writable."""
    test_file = DATA_ROOT / ".health_check"
    try:
        test_file.write_text("ok")
        assert test_file.read_text() == "ok"
        test_file.unlink()
        log.info(f"Volume health check: OK (DATA_ROOT={DATA_ROOT})")
    except Exception as e:
        log.critical(f"Volume health check FAILED: {e}. DATA_ROOT={DATA_ROOT}")


# ── DB-01x: File lock to prevent concurrent fetcher instances ──
_lock_fd = None


def _acquire_lock() -> bool:
    """Acquire an exclusive flock. Returns False if another instance holds it."""
    global _lock_fd
    lock_path = DATA_ROOT / ".fetcher.lock"
    _lock_fd = open(lock_path, "w")
    try:
        fcntl.flock(_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        log.warning("Another fetcher instance is running — exiting")
        return False


# ── CEO-05: Per-source rate limiter ──
# (max_calls, window_seconds) — sources not listed are unlimited
RATE_LIMITS: dict[str, tuple[int, int]] = {
    "firms": (5000, 600),         # 5000 transactions per 10 minutes
    "waqi": (1000, 86400),        # 1000 requests per day
    "openaq": (1000, 86400),      # 1000 requests per day (same API under the hood)
    "aviationstack": (16, 86400), # 500 req/month ≈ 16/day
    "opensky": (3000, 86400),     # 4000 credits/day — leave headroom
}

# Timestamps of recent calls per source
_source_call_counts: dict[str, list[float]] = {}


def _check_rate_limit(source: str) -> bool:
    """Return True if the source is within its rate limit, False if over."""
    if source not in RATE_LIMITS:
        return True
    max_calls, window_seconds = RATE_LIMITS[source]
    now = time.time()
    timestamps = _source_call_counts.get(source, [])
    # Prune timestamps outside the window
    cutoff = now - window_seconds
    timestamps = [t for t in timestamps if t > cutoff]
    _source_call_counts[source] = timestamps
    if len(timestamps) >= max_calls:
        log.debug(f"Rate limit: {source} at {len(timestamps)}/{max_calls} in window")
        return False
    return True


def _record_call(source: str) -> None:
    """Record a call timestamp for rate limiting."""
    if source not in RATE_LIMITS:
        return
    _source_call_counts.setdefault(source, []).append(time.time())


# ── CEO-04: Source recovery cooldown ──
# Tracks cycles remaining before oracle signing resumes after source recovery.
# When a source recovers from failure, set cooldown to 2 (= 30 min at 15-min cycles).
_source_recovery_cooldown: dict[str, int] = {}

# Track which sources failed in the previous cycle
_source_failed_last_cycle: set[str] = set()


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
    """Multi-source flight delay: FAA ATCSCC (US) → AviationStack (tier-1) → OpenSky (all)."""
    iata = _get_iata(trigger)

    sources = []

    # FAA ATCSCC: US airports only — real delay minutes, free, no key
    if _is_us_airport(trigger):
        sources.append(SourceConfig(
            name="faa_atcscc", priority=0,
            fetch_fn=lambda: faa_atcscc.fetch_airport_status(iata, trigger.id),
            rate_limit_note="free, no limit",
        ))

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


# ── CEO-01: R2 as API fallback ──
def _write_r2_snapshot(trigger_id: str, result: dict) -> None:
    """Write trigger evaluation snapshot to R2 for CF Workers fallback.

    Writes to ``trigger-status/{trigger_id}.json`` so Cloudflare Workers can
    serve cached trigger status when Redis is unavailable.  Wrapped in
    try/except so it never blocks the fetcher.
    """
    try:
        snapshot = {
            "trigger_id": trigger_id,
            "data": result,
            "snapshot_at": datetime.now(timezone.utc).isoformat(),
        }
        upload_to_r2_key(
            f"trigger-status/{trigger_id}.json",
            json.dumps(snapshot, default=str),
        )
    except Exception as e:
        log.debug(f"R2 snapshot write skipped for {trigger_id}: {e}")


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


def _update_recovery_cooldowns(
    succeeded: set[str], failed: set[str]
) -> None:
    """CEO-04: Update recovery cooldown state at end of each fetch cycle.

    - If a source was failing last cycle and succeeded this cycle, enter cooldown.
    - Decrement existing cooldowns each cycle.
    - Track which sources failed for next cycle's comparison.
    """
    global _source_failed_last_cycle

    # Detect recoveries: source failed last cycle but succeeded this cycle
    for source in succeeded:
        if source in _source_failed_last_cycle and source not in _source_recovery_cooldown:
            _source_recovery_cooldown[source] = 2
            log.info(
                f"Source {source} recovered — cooldown 2 cycles before oracle signing resumes"
            )

    # Decrement existing cooldowns
    expired = []
    for source in list(_source_recovery_cooldown):
        _source_recovery_cooldown[source] -= 1
        if _source_recovery_cooldown[source] <= 0:
            expired.append(source)

    for source in expired:
        del _source_recovery_cooldown[source]
        log.info(f"Source {source} recovery cooldown complete — oracle signing resumed")

    # Update failure tracking for next cycle
    _source_failed_last_cycle = failed


def fetch_all(diagnostic: bool = False) -> dict:
    """Fetch all triggers that need updating. Sign determinations if key is available."""
    global _oracle_signing_enabled

    # DB-01d: Verify volume is healthy before anything else
    _check_volume_health()

    # DB-01x: Prevent concurrent fetcher instances
    if not _acquire_lock():
        return {"skipped": "lock held"}

    _log_data_source_health()

    if not _oracle_signing_enabled:
        _init_oracle_signing()

    fetched = 0
    skipped = 0
    errors = 0
    signed = 0
    rate_limited = 0
    cooldown_skipped = 0

    # Diagnostic mode: track AQI trigger results
    aqi_diag_rows: list[dict] = []
    aqi_total = 0
    aqi_got_data = 0

    prev_hash = read_last_hash() if _oracle_signing_enabled else GENESIS_HASH

    # CEO-04: Track which sources succeeded/failed this cycle for recovery detection
    sources_failed_this_cycle: set[str] = set()
    sources_succeeded_this_cycle: set[str] = set()

    for trigger in GLOBAL_TRIGGERS:
        if not _should_fetch(trigger.data_source, trigger.id):
            skipped += 1
            continue

        fetch_fn = FETCH_MAP.get(trigger.data_source)
        if not fetch_fn:
            errors += 1
            continue

        # CEO-05: Check rate limit before fetching
        if not _check_rate_limit(trigger.data_source):
            rate_limited += 1
            skipped += 1
            continue

        try:
            # CEO-05: Record the call for rate limiting
            _record_call(trigger.data_source)

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
                sources_succeeded_this_cycle.add(trigger.data_source)

                # CEO-01: Write trigger status snapshot to R2 (API fallback)
                _write_r2_snapshot(trigger.id, result)

                # SL-01b: Write observation to DuckDB (never crashes the fetcher)
                try:
                    from gad.engine.db_write import write_observation
                    value = result.get("value") if isinstance(result.get("value"), (int, float)) else None
                    write_observation(trigger.id, value, _evaluate_fired(trigger, result), trigger.data_source, result)
                except Exception as e:
                    log.debug(f"Observation write skipped for {trigger.id}: {e}")

                # Oracle signing: create and sign a determination for every evaluation
                if _oracle_signing_enabled and _private_key:
                    # CEO-04: Skip signing if source is in recovery cooldown
                    cd = _source_recovery_cooldown.get(trigger.data_source, 0)
                    if cd > 0:
                        cooldown_skipped += 1
                        log.debug(
                            f"Skipping oracle signing for {trigger.id}: "
                            f"source {trigger.data_source} in recovery cooldown ({cd} cycles left)"
                        )
                    else:
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
                sources_failed_this_cycle.add(trigger.data_source)
        except Exception as e:
            errors += 1
            sources_failed_this_cycle.add(trigger.data_source)
            log.error(f"Error fetching {trigger.id}: {e}")

        time.sleep(1.0)  # 1s between triggers to avoid rate limiting (521 triggers)

    # CEO-04: Detect source recovery and manage cooldowns
    _update_recovery_cooldowns(sources_succeeded_this_cycle, sources_failed_this_cycle)

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

    # DB-06b: Run daily/weekly jobs if due
    if _should_run_daily_jobs():
        try:
            _run_daily_jobs()
        except Exception as e:
            log.warning(f"Daily jobs failed: {e}")
    if _should_run_weekly_jobs():
        try:
            _run_weekly_jobs()
        except Exception as e:
            log.warning(f"Weekly jobs failed: {e}")

    summary = {
        "fetched": fetched,
        "skipped": skipped,
        "errors": errors,
        "signed": signed,
        "rate_limited": rate_limited,
        "cooldown_skipped": cooldown_skipped,
    }
    log.info(f"Fetch complete: {summary}")
    return summary


# ── DB-06a: Daily/weekly flag file pattern ──

def _should_run_daily_jobs() -> bool:
    """Check if daily jobs should run (23-hour debounce via flag file)."""
    from gad.config import DATA_ROOT
    flag = DATA_ROOT / ".last_daily_run"
    if not flag.exists():
        return True
    last_run = datetime.fromtimestamp(flag.stat().st_mtime, tz=timezone.utc)
    return (datetime.now(timezone.utc) - last_run).total_seconds() > 82800  # 23 hours


def _mark_daily_done():
    """Touch the daily flag file."""
    from gad.config import DATA_ROOT
    (DATA_ROOT / ".last_daily_run").write_text(datetime.now(timezone.utc).isoformat())


def _should_run_weekly_jobs() -> bool:
    """Check if weekly jobs should run (6.5-day debounce via flag file)."""
    from gad.config import DATA_ROOT
    flag = DATA_ROOT / ".last_weekly_run"
    if not flag.exists():
        return True
    last_run = datetime.fromtimestamp(flag.stat().st_mtime, tz=timezone.utc)
    return (datetime.now(timezone.utc) - last_run).total_seconds() > 561600  # 6.5 days


def _mark_weekly_done():
    """Touch the weekly flag file."""
    from gad.config import DATA_ROOT
    (DATA_ROOT / ".last_weekly_run").write_text(datetime.now(timezone.utc).isoformat())


# ── DB-06b: Daily and weekly job runners ──

def _run_daily_jobs():
    """Run once per day: backup, distributions, drift detection."""
    log.info("Running daily jobs...")
    try:
        from gad.engine.backup import backup_to_r2, prune_old_backups
        backup_to_r2()
        prune_old_backups(keep_days=30)
    except Exception as e:
        log.warning(f"Daily backup failed: {e}")

    # SL-02a: Compute distributions for all triggers (90d + 365d)
    try:
        from gad.engine.distribution_tracker import compute_all_distributions
        dist_result = compute_all_distributions()
        log.info(f"Distribution tracker: {dist_result}")
    except Exception as e:
        log.warning(f"Distribution computation failed: {e}")

    # SL-03a: Run drift detection for all triggers
    try:
        from gad.engine.drift_detector import detect_all_drift
        drift_result = detect_all_drift()
        log.info(f"Drift detector: {drift_result}")
    except Exception as e:
        log.warning(f"Drift detection failed: {e}")

    _mark_daily_done()
    log.info("Daily jobs complete.")


def _run_weekly_jobs():
    """Run once per week: threshold optimization, peer calibration, correlation matrix."""
    log.info("Running weekly jobs...")

    # SL-04a: Threshold optimization for all triggers with sufficient data
    try:
        from gad.engine.threshold_optimizer import optimize_all_thresholds
        opt_result = optimize_all_thresholds()
        log.info(f"Threshold optimizer: {len(opt_result)} triggers optimized")
    except Exception as e:
        log.warning(f"Threshold optimization failed: {e}")

    # SL-05b: Compute peer index for all triggers with sufficient observations
    try:
        from gad.engine.peer_index import compute_all_peers
        compute_all_peers()
    except Exception as e:
        log.warning(f"Peer index computation failed: {e}")

    # SL-05c: Detect outlier triggers (>2 sigma from peer median firing rate)
    try:
        from gad.engine.peer_index import detect_outliers
        outliers = detect_outliers()
        if outliers:
            log.info(f"Outlier triggers: {[o['trigger_id'] for o in outliers]}")
    except Exception as e:
        log.warning(f"Outlier detection failed: {e}")

    # SL-07a: Co-firing correlation matrix (phi coefficient, 2000km bounding)
    try:
        from gad.engine.correlation_matrix import compute_correlations
        corr_results = compute_correlations()
        log.info(f"Correlation matrix: {len(corr_results)} pairs computed")
    except Exception as e:
        log.warning(f"Correlation matrix computation failed: {e}")

    _mark_weekly_done()
    log.info("Weekly jobs complete.")


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
