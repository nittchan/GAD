# CLAUDE_QUICK.md

## Purpose

Fast context file for agents and contributors who need the essentials in under a minute.

## What GAD Is

GAD is an open-source global parametric insurance platform — the "WorldMonitor for parametric insurance."

1. **Global Monitor** — live risk map across 12 peril categories (flights, AQI, wildfire, drought, weather, earthquake, marine/shipping, flood, cyclone, crop/NDVI, solar/space weather, health/pandemic) using free open data.
2. **Basis risk engine** — Spearman correlation scoring, Lloyd's checklist, PDF export.
3. **Oracle infrastructure** — cryptographically signed, hash-chained trigger determinations (v0.2.2+).
4. **Account layer** — user auth, saved triggers, activity events via Supabase.

## Stage

- v0.1 (2026-03-19): Basis risk dashboard with 3 sample triggers.
- v0.2.1 (2026-03-23, CURRENT): Global Monitor live at parametricdata.io. 521 triggers, 144 airports + 10 ports, multi-source data (16 APIs), all pages unified.
- v0.2.2 (next): Oracle signing layer under the visible dashboard.
- v0.3: Self-Learning Actuary — DuckDB analytical datastore, distribution tracking, drift detection, threshold optimization, peer calibration, correlation matrix.
- v0.4: Platform — API on CF Workers (community service), Redis for API cache, verification SDK.

## Development Workflow

```
dev → staging (gad-dashboard-staging.fly.dev) → main (parametricdata.io)
```

All work on `dev`. Merge to `staging` to test. Merge to `main` to ship. GitHub Actions auto-deploy.

## Main Entry Points

- Dashboard: dashboard/app.py (Streamlit)
- Global Monitor page: dashboard/pages/6_Global_Monitor.py
- Background fetcher: python -m gad.monitor.fetcher
- Oracle read API: oracle_ledger/worker.js

## Architecture

```
Background fetcher (cron every 15 min)
  → Fetches from FAA ATCSCC, OpenSky, AviationStack, AirNow, OpenAQ, WAQI, NASA FIRMS, Open-Meteo, GPM IMERG, USGS, AISstream, USGS Water Services, NOAA NHC, Copernicus/MODIS NDVI, NOAA SWPC, WHO DON
  → Writes to data/monitor_cache/ (JSON files)

Dashboard (Streamlit)
  → Reads from cache ONLY (zero external API calls)
  → Users never trigger API calls
  → Even 10,000 users = same API cost as 0

Compute engine: gad/engine/ package
  → Basis risk, Spearman, Lloyd's, oracle signing
```

## Key Packages

- gad/engine/ — compute core (basis risk, lloyds, oracle, models)
- gad/monitor/ — global monitor (triggers, cache, fetcher, security, data sources)
- gad/monitor/sources/ — API fetchers (opensky, aviationstack, airnow, openaq, firms, openmeteo, gpm_imerg, usgs_earthquake, aisstream, noaa_flood, noaa_nhc, ndvi, noaa_swpc, who_don)
- dashboard/ — Streamlit app with 7 pages
- oracle_ledger/ — Cloudflare Worker

## Data Sources (all free)

| Source | API | Key needed? |
|--------|-----|------------|
| OpenSky | Flight departures | OAuth2 (configured) |
| AviationStack | Flight schedules (tier-1) | API key (configured) |
| WAQI | Air quality (global) | API key (configured) |
| AirNow EPA | Air quality (US) | API key (configured) |
| OpenAQ v3 | Air quality (open data) | API key (configured) |
| NASA FIRMS | Wildfire (VIIRS+MODIS) | MAP key (configured) |
| Open-Meteo | Weather forecasts | No key needed |
| CHIRPS | Monthly rainfall | No key needed |
| NASA GPM IMERG | Daily precipitation | Earthdata token (configured) |
| AISstream | Marine vessel tracking | API key (required) |
| USGS Earthquake | Earthquake detection | No key needed |
| USGS Water Services | Flood river gauge levels | No key needed |
| NOAA NHC | Tropical cyclone tracking | No key needed |
| Copernicus/MODIS | Crop / NDVI vegetation health | No key needed |
| NOAA SWPC | Solar/space weather alerts | No key needed |
| WHO DON | Health/pandemic outbreak alerts | No key needed |
| FAA ATCSCC | US airport delays (real minutes) | No key needed |

## Env Vars

- SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY
- NASA_FIRMS_MAP_KEY, WAQI_API_TOKEN, OPENSKY_CLIENT_ID, OPENSKY_CLIENT_SECRET
- AVIATIONSTACK_API_KEY, OPENAQ_API_KEY, AIRNOW_API_KEY, NASA_EARTHDATA_TOKEN
- AISSTREAM_API_KEY — marine vessel tracking
- GAD_ORACLE_PRIVATE_KEY_HEX, GAD_ORACLE_PUBLIC_KEY_HEX, GAD_ORACLE_KEY_ID (v0.2.2)

## Near-Term Priorities

1. Basis risk precomputed for 221 triggers (done). Flight history and remaining AQI coverage pending.
2. Oracle signing + R2 upload + Oracle Ledger page (done).
3. All 12 perils live (flight, AQI, wildfire, drought, weather, earthquake, marine, flood, cyclone, crop, solar, health).
4. v0.3 Self-Learning Actuary — DuckDB, distribution tracking, drift detection, threshold optimization.
5. v0.4 Platform — API layer (CF Workers), community service model.
5. Parametric Data Pro (enterprise tier).
