# CLAUDE_ENGINEERING.md

## Purpose

Engineering-focused scope summary for implementation, debugging, and refactor decisions.

## System Boundary

GAD operates as four integrated layers:

1. **Global Monitor** — live risk dashboard with 14 peril categories, background data fetching, cache-based reads.
2. **Basis risk engine** — Spearman correlation, bootstrap CI, Lloyd's checklist, PDF export.
3. **Oracle infrastructure** — Ed25519 signed determinations, hash-chained log, Cloudflare Worker read surface.
4. **Account/telemetry** — Supabase-backed auth, saved triggers, activity events.

Engine canonicalized on gad/engine/. Legacy modules deleted (2026-03-23). Global Monitor built (2026-03-23).

## Runtime Entry Points

- Dashboard: `streamlit run dashboard/app.py`
- Background fetcher: `python -m gad.monitor.fetcher` (cron) or `python -m gad.monitor.fetcher --loop` (continuous)
- Oracle read surface: oracle_ledger/worker.js
- REST API: `uvicorn gad.api.main:app` (port 8502, OpenAPI at /v1/docs)

## Package Structure

### gad/api/ — REST API
- main.py: FastAPI app with 14+ routes (triggers, basis-risk, determinations, model-history, model-drift, status, ports, perils, intelligence/peril-patterns, intelligence/location, intelligence/climate-zone). API key auth opt-in. Response models in models.py.
- models.py: Pydantic response models for auto-generated OpenAPI schemas.

### gad/mcp/ — MCP Server (Model Context Protocol)
- server.py: JSON-RPC 2.0 stdio server exposing 4 tools for AI agents (check_trigger_status, list_triggers_by_location, get_basis_risk, list_perils). Run: `python -m gad.mcp.server`

### gad/engine/ — Compute core
- models.py: TriggerDef, BasisRiskReport, TriggerDetermination, TriggerObservation, ModelVersion, PolicyBinding, GadEvent
- db.py: DuckDB schema (8 tables), singleton connection
- db_write.py: Write helpers (8 functions, try/except wrapped)
- db_read.py: Read helpers (7 query functions)
- timeseries.py: Observation read abstraction (stats, series, threshold checks)
- model_registry.py: Append-only model versioning with R2 backup
- backup.py: DuckDB backup (CHECKPOINT + gzip + R2 upload + prune)
- distribution_tracker.py: Rolling 90d/365d distribution computation with model versioning
- drift_detector.py: CUSUM drift detection (mean shift, firing rate, variance change)
- threshold_optimizer.py: Frequency matching + KS separability, evidence gating
- peer_index.py: Cosine similarity peer matching (top-5), outlier detection (>2σ)
- cold_start.py: Weighted-average inference from peers for triggers with <30 observations
- correlation_matrix.py: Co-firing phi coefficient with 2000km geographic bounding, lead-lag analysis
- proximity_alerts.py: Triggers within 20% of threshold (daily digest integration)
- user_annotations.py: User watchlist with firing_rate snapshots and drift detection
- webhook.py: HMAC-SHA256 signed webhook delivery with retry + dead-letter queue

### gad/monitor/ — Global Monitor
- climate_zones.py: Koppen climate zone lookup (rule-based approximation)
- basis_risk.py: Spearman rho, bootstrap CI, confusion matrix, Lloyd's integration
- lloyds.py: Lloyd's checklist scoring
- oracle.py: Ed25519 sign/verify, hash chain, append-only log
- loader.py: CSV → weather_data, manifest adapter
- pdf_export.py: Lloyd's-formatted PDF reports
- analytics.py: Supabase event writes
- r2_upload.py: Optional Cloudflare R2 upload for signed determinations

### gad/monitor/ — Global Monitor
- airports.py: Master airport registry (50 Indian + 94 global = 144 airports). Each airport has `lat`/`lon` (runway) and optional `city_lat`/`city_lon` (city centre). AQI triggers use city coordinates via `effective_city_lat`/`effective_city_lon` properties; flight/weather triggers use airport coordinates.
- ports.py: Port registry (10 tier-1 global ports with anchorage bounding boxes)
- triggers.py: Auto-generates triggers for 14 perils: flight delay, weather, AQI, earthquake, marine, flood, cyclone, crop/NDVI, solar, health, disaster/GDACS, natural events/EONET (536 triggers)
- cache.py: JSON file cache with TTL, staleness detection
- fetcher.py: Background worker fetches all sources on schedule. Auto-bootstraps historical weather data on first deploy (idempotent — skips if ≥50 CSVs exist).
- security.py: Rate limiter, input sanitization, key management
- sources/faa_atcscc.py: US airport delays — real delay minutes from FAA ATCSCC (free, no key, tier-0 for US)
- sources/opensky.py: Flight departure data (OpenSky Network API — departure count, global fallback)
- sources/openaq.py: Air quality (OpenAQ v3 + WAQI fallback, 15km radius from city centre). AirNow is tried first for US airports (see airnow.py).
- sources/airnow.py: Air quality (US EPA authoritative, 15mi radius from city centre)
- sources/firms.py: Wildfire detection (NASA FIRMS)
- sources/openmeteo.py: Weather forecasts (Open-Meteo)
- sources/aisstream.py: Marine vessel tracking (AISstream WebSocket — vessel count, anchor status, speed)
- sources/noaa_flood.py: Flood river gauge data (USGS Water Services API — free, no key)
- sources/noaa_nhc.py: Tropical cyclone tracking (NOAA NHC GeoJSON — free, no key)
- sources/ndvi.py: Crop / vegetation health (Copernicus/MODIS NDVI — free, no key)
- sources/gdacs.py: Disaster alerts (GDACS RSS — volcanoes, tsunamis, floods — free, no key)
- sources/nasa_eonet.py: Natural events (NASA EONET API — 13 categories — free, no key)
- sources/noaa_swpc.py: Solar/space weather (NOAA SWPC — free, no key)
- sources/who_don.py: Health/pandemic alerts (WHO Disease Outbreak News — free, no key)
- risk_index.py: Parametric Risk Exposure Index (PREI) computation per country

### Data Architecture

**Rule: The browser and dashboard compute nothing. All math, fetching, and risk calculation happens server-side. The dashboard only reads precomputed results.**

Update this section after any TODO that adds a data source, store, compute job, or read path.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL DATA SOURCES                        │
│  18 APIs — all free tier, fetched server-side only                  │
│                                                                     │
│  Flight:    FAA ATCSCC · AviationStack · OpenSky                    │
│  AQI:       AirNow EPA · OpenAQ · WAQI                             │
│  Weather:   Open-Meteo                                              │
│  Wildfire:  NASA FIRMS (VIIRS + MODIS)                              │
│  Drought:   CHIRPS · NASA GPM IMERG                                 │
│  Earthquake: USGS                                                   │
│  Marine:    AISstream (WebSocket)                                   │
│  Flood:     USGS Water Services                                     │
│  Cyclone:   NOAA NHC                                                │
│  Crop:      Copernicus/MODIS NDVI                                   │
│  Solar:     NOAA SWPC                                               │
│  Health:    WHO DON                                                 │
│  Disaster:  GDACS RSS                                               │
│  Events:    NASA EONET                                              │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ fetched every 15 min
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     WRITE PATH (server-side only)                   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────┐        │
│  │  Background Fetcher  (gad/monitor/fetcher.py)           │        │
│  │  Runs: every 15 min (--loop) or cron                    │        │
│  │                                                         │        │
│  │  For each of 536 triggers:                              │        │
│  │    1. Fetch live value from priority source chain        │        │
│  │    2. Evaluate fired/not-fired against threshold         │        │
│  │    3. Write to JSON cache ──────────────────────► [A]    │        │
│  │    4. Write observation to DuckDB ──────────────► [B]    │        │
│  │    5. Sign determination (Ed25519) ─────────────► [C]    │        │
│  └─────────────────────────────────────────────────────────┘        │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────┐        │
│  │  Historical Backfill  (one-time on first deploy)        │        │
│  │  Auto-bootstraps if <50 weather CSVs exist              │        │
│  │                                                         │        │
│  │  scripts/fetch_historical_openmeteo.py → 5yr weather    │        │
│  │  scripts/fetch_historical_openaq.py   → 2yr AQI        │        │
│  │  scripts/fetch_bts_transtats.py       → 3yr US flights  │        │
│  │  scripts/fetch_opensky_zenodo.py      → 4yr departures  │        │
│  │                                                         │        │
│  │  Output: CSV series files ──────────────────────► [D]    │        │
│  └─────────────────────────────────────────────────────────┘        │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────┐        │
│  │  Precompute  (scripts/precompute_basis_risk.py)         │        │
│  │  Runs: after backfill, or on-demand (--force)           │        │
│  │                                                         │        │
│  │  Reads CSV series [D]                                   │        │
│  │  Computes: Spearman rho, bootstrap CI, FPR/FNR,        │        │
│  │            confusion matrix, Lloyd's checklist score    │        │
│  │  Output: JSON reports ──────────────────────────► [E]    │        │
│  └─────────────────────────────────────────────────────────┘        │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────┐        │
│  │  Daily Jobs  (fetcher._run_daily_jobs)                  │        │
│  │  Reads DuckDB observations [B], writes results to [B]   │        │
│  │                                                         │        │
│  │  • Distribution tracker — 90d/365d rolling stats        │        │
│  │  • Drift detector — CUSUM (mean shift, firing rate)     │        │
│  │  • DuckDB backup → R2                                   │        │
│  └─────────────────────────────────────────────────────────┘        │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────┐        │
│  │  Weekly Jobs  (fetcher._run_weekly_jobs)                │        │
│  │  Reads DuckDB observations [B], writes results to [B]   │        │
│  │                                                         │        │
│  │  • Threshold optimizer — frequency matching + KS test   │        │
│  │  • Peer calibration — cosine similarity, top-5 peers    │        │
│  │  • Correlation matrix — phi coefficient, lead-lag       │        │
│  └─────────────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                         DATA STORES                                 │
│                                                                     │
│  [A] JSON Cache         data/monitor_cache/*.json                   │
│      Live trigger status. TTL-based. Gitignored.                    │
│      Written by: fetcher (every 15 min)                             │
│      Read by: dashboard, REST API                                   │
│                                                                     │
│  [B] DuckDB             data/gad.duckdb                             │
│      8 tables: trigger_observations, trigger_distributions,         │
│      drift_alerts, threshold_suggestions, trigger_peers,            │
│      trigger_correlations, model_versions, seasonal_profiles        │
│      Written by: fetcher (observations), daily/weekly jobs          │
│      Read by: REST API, daily/weekly jobs                           │
│      Single-writer pattern (fetcher process holds flock)            │
│                                                                     │
│  [C] Oracle Ledger      data/oracle/ + Cloudflare R2                │
│      Signed determinations (Ed25519), hash-chained JSONL.           │
│      Written by: fetcher (on each evaluation)                       │
│      Read by: Oracle Ledger page, Cloudflare Worker, verify CLI     │
│                                                                     │
│  [D] CSV Series         data/series/{weather,aqi,flights}/*.csv     │
│      Historical time series. One-time backfill, persistent.         │
│      Written by: historical backfill scripts (one-time)             │
│      Read by: precompute_basis_risk.py                              │
│                                                                     │
│  [E] Basis Risk JSON    data/basis_risk/{trigger_id}.json           │
│      Precomputed Spearman reports. One per trigger.                 │
│      Written by: precompute_basis_risk.py                           │
│      Read by: dashboard (Trigger Profile), REST API                 │
│                                                                     │
│  [F] Supabase           (external, cloud-hosted)                    │
│      User profiles, saved triggers, activity events, API keys.      │
│      Written by: dashboard (auth), analytics.py                     │
│      Read by: dashboard (Account page), API (auth)                  │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    READ PATH (zero computation)                     │
│                                                                     │
│  Dashboard (Streamlit, port 8501)                                   │
│    Global Monitor    → reads [A] JSON cache                         │
│    Trigger Profile   → reads [A] cache + [E] basis risk JSON        │
│    Compare           → reads [A] cache + [E] basis risk JSON        │
│    Guided/Expert     → reads [A] cache                              │
│    Oracle Ledger     → reads [C] oracle log                         │
│    Digest            → reads [A] cache + [B] DuckDB                 │
│    Composer          → reads [A] cache + [B] DuckDB                 │
│                                                                     │
│  REST API (FastAPI, port 8502)                                      │
│    /v1/triggers      → reads [A] cache                              │
│    /v1/basis-risk    → reads [E] basis risk JSON                    │
│    /v1/intelligence  → reads [B] DuckDB                             │
│    /v1/health        → reads [A] cache metadata                     │
│    /v1/model-drift   → reads [B] DuckDB                             │
│                                                                     │
│  Browser does ZERO computation, ZERO external API calls.            │
│  Users NEVER trigger data fetches. Cost is fixed.                   │
│  10,000 concurrent users = same API cost as zero users.             │
└─────────────────────────────────────────────────────────────────────┘
```

## Dashboard Pages

- Global Monitor: dashboard/pages/6_Global_Monitor.py (interactive map + trigger cards)
- Guided mode: dashboard/pages/1_Guided_mode.py (4-step wizard)
- Expert mode: dashboard/pages/2_Expert_mode.py (JSON editor)
- Trigger profile: dashboard/pages/3_Trigger_profile.py
- Compare: dashboard/pages/4_Compare.py
- Account: dashboard/pages/5_Account.py
- Oracle Ledger: dashboard/pages/7_Oracle.py (chain status, recent determinations)

## Data Contracts

### Monitor triggers (gad/monitor/triggers.py)
Data-driven triggers auto-generated from airport registry (`gad/monitor/airports.py`) and port registry (`gad/monitor/ports.py`): id, name, peril, lat/lon, threshold, unit, data_source, description.
536 triggers across 14 perils (144 flight delay + 125 AQI + 8 wildfire + 5 drought + 144 weather + 10 earthquake + 20 marine + 20 flood + 20 cyclone + 10 crop/NDVI + 5 solar + 10 health + 10 disaster/GDACS + 5 natural events/EONET). Add new airports/ports to the registries to expand coverage.
**Coordinate split:** AQI triggers use city centre coordinates (where AQI monitors are); flight/weather triggers use airport runway coordinates. When adding an airport far from its city (>15km), set `city_lat`/`city_lon` on the Airport entry.
**Flight delay dual metric:** Evaluation is source-aware. AviationStack (tier-1 airports) provides real delay in minutes — fires when avg delay exceeds threshold. OpenSky (all airports, fallback) provides departure count only — fires when 0 departures in 2h (airport disruption proxy). The `evaluate_trigger` result includes a `metric` field (`"avg_delay"` or `"departure_count"`) so the UI shows the correct label.

### Monitor cache (data/monitor_cache/)
JSON files with: source, key, data, cached_at, expires_at. Gitignored. Created by fetcher.

### Engine models (gad/engine/models.py)
UUID-centric TriggerDef, BasisRiskReport, TriggerDetermination. Pydantic v2.

### Oracle determination shape
determination_id, policy_id, trigger_id, fired, fired_at, data_snapshot_hash, computation_version, determined_at, prev_hash, signature. v0.1: empty signature. v0.2.2: signed + key_id.

## Test Coverage (2209 tests)

- tests/test_basis_risk.py: core compute (2 tests)
- tests/test_lloyds.py: checklist scoring (2 tests)
- tests/test_oracle.py: sign/verify, genesis hash, chain verification (7 tests)
- tests/test_oracle_chain.py: 5-entry chain, tamper detection, canonical hash (12 tests)
- tests/test_reproducibility.py: deterministic outputs (1 test)
- tests/test_import_hygiene.py: no legacy imports (1 test)
- tests/test_monitor_fetcher.py: evaluate_fired all 14 sources, FETCH_MAP, determination creation, rate limiter, recovery cooldown (48 tests)
- tests/test_aqi_coordinates.py: all airports city coords, haversine sanity, AQI coord verification (~700 tests)
- tests/test_triggers.py: 536 count, unique IDs, field validation, marine/flood/cyclone/crop/solar/health integrity (~1500 tests)
- tests/test_risk_index.py: PREI formula, near-threshold, edge cases (17 tests)

Remaining gaps:
- Worker contract tests (requires Wrangler CLI)
- Marine AISstream mock WebSocket tests
- Dashboard page smoke tests

## Development Workflow

```
dev → staging (gad-dashboard-staging.fly.dev) → main (parametricdata.io)
```

All work on `dev`. Never push to `staging` or `main` directly. GitHub Actions auto-deploy on merge.

| Environment | Fly App | URL | Branch |
|-------------|---------|-----|--------|
| Development | — | localhost:8501 | dev |
| Staging | gad-dashboard-staging | gad-dashboard-staging.fly.dev | staging |
| Production | gad-dashboard | parametricdata.io | main |

## Design System
Always read `DESIGN.md` before making any visual or UI decisions. All font choices, colors, spacing, and aesthetic direction are defined there. Do not deviate without explicit user approval. In QA mode, flag any code that doesn't match DESIGN.md.

## Build and Runtime

- Python: >=3.12
- Packaging: pyproject.toml + requirements.txt
- Dashboard container: dashboard/Dockerfile
- Fly deployment: fly.toml (auto-stop, connection limits, 1GB)
- Worker deployment: oracle_ledger/wrangler.toml

## Environment Variables

Required:
- SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY

Global Monitor data sources (all configured):
- NASA_FIRMS_MAP_KEY — wildfire (VIIRS + MODIS)
- WAQI_API_TOKEN — air quality (global)
- OPENSKY_CLIENT_ID, OPENSKY_CLIENT_SECRET — flights (OAuth2, 4000 credits/day)
- AVIATIONSTACK_API_KEY — flight schedules (tier-1 airports)
- OPENAQ_API_KEY — air quality (open data)
- AIRNOW_API_KEY — air quality (US EPA authoritative)
- NASA_EARTHDATA_TOKEN — GPM IMERG (daily precipitation)
- AISSTREAM_API_KEY — marine vessel tracking (AISstream WebSocket)
- (no key) NOAA SWPC — solar/space weather (free public API)
- (no key) WHO DON — health/pandemic alerts (free public API)

Oracle (v0.2.2+):
- GAD_ORACLE_PRIVATE_KEY_HEX, GAD_ORACLE_PUBLIC_KEY_HEX, GAD_ORACLE_KEY_ID

## Historical Data Pipeline Scripts

- `scripts/fetch_historical_openmeteo.py`: Download 5yr daily weather for all 144 airports. Free, no key. Output: `data/series/weather/{IATA}_daily.csv`. Supports `--airports` and `--years` flags.
- `scripts/fetch_historical_openaq.py`: Download 2yr daily AQI for tier 1-2 airports. OpenAQ v3 API (requires API key). Probes for best PM2.5 sensor per city. Output: `data/series/aqi/{IATA}_aqi_daily.csv`. Writes `_station_mapping.csv` for audit.
- `scripts/fetch_bts_transtats.py`: Download US on-time flight performance from BTS TranStats. Real delay minutes for 15 US airports, 3yr history. Free, no key.
- `scripts/fetch_opensky_zenodo.py`: Download global departure counts from OpenSky Zenodo Parquet dumps. All 144 airports, 4yr history. Free, no key.
- `scripts/fetch_eurocontrol.py`: European airport delays from Eurocontrol ANS. 25 airports, 3 modes (CSV/API/weather-proxy). Free.
- `scripts/fetch_dgca_india.py`: Indian airport delays from DGCA monthly reports. 10 airports, PDF parse/template import modes.
- `scripts/precompute_basis_risk.py`: Batch compute basis risk for all triggers with historical data (weather + AQI + flights). Output: `data/basis_risk/{trigger_id}.json`. Supports `--peril` and `--force` flags.

## Oracle Scripts

- `scripts/generate_oracle_keypair.py`: Generate Ed25519 key pair. Run once, set as Fly.io secrets.
- `scripts/publish_oracle_key.py`: Upload `oracle-keys.json` to R2. Run after key generation.
- `scripts/seed_oracle_determination.py`: Publish a single demo determination to R2. Run once for bootstrapping.

## Near-Term Engineering Priorities

1. **v0.2 remaining:** Historical basis risk for all 536 triggers. Oracle signing wired to live monitor.
2. **v0.3 — Self-Learning Actuary:** DuckDB on Fly.io persistent volume (+$1.50/mo). Single-writer pattern (fetcher). TriggerObservation time series. Distribution tracker (90d + 365d rolling). Drift detector (CUSUM). Seasonal decomposition (STL). Threshold optimizer. Peer calibration (Koppen zones). Cold-start inference. Co-firing correlation matrix. Model versioning. See TODOS.md P8 for full task breakdown.
3. **v0.4 — Platform:** API product layer on CF Workers (community service). Redis (Upstash) for API cache + rate limiting. Verification SDK + CLI.

**Storage decision:** DuckDB supersedes Redis for all analytical data. Redis deferred to v0.4 API layer (CF Workers can't read DuckDB).
