# CLAUDE_QUICK.md

## Purpose

Fast context file for agents and contributors who need the essentials in under a minute.

## What GAD Is

GAD is an open-source global parametric insurance platform — the "WorldMonitor for parametric insurance."

1. **Global Monitor** — live risk map across 9 peril categories (flights, AQI, wildfire, drought, weather, earthquake, marine/shipping, flood, cyclone) using free open data.
2. **Basis risk engine** — Spearman correlation scoring, Lloyd's checklist, PDF export.
3. **Oracle infrastructure** — cryptographically signed, hash-chained trigger determinations (v0.2.2+).
4. **Account layer** — user auth, saved triggers, activity events via Supabase.

## Stage

- v0.1 (2026-03-19): Basis risk dashboard with 3 sample triggers.
- v0.2.1 (2026-03-23, CURRENT): Global Monitor live at parametricdata.io. 496 triggers, 144 airports + 10 ports, multi-source data (12 APIs), all pages unified.
- v0.2.2 (next): Oracle signing layer under the visible dashboard.
- v0.3: New perils (health, solar), enterprise tier.

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
  → Fetches from OpenSky, AviationStack, AirNow, OpenAQ, WAQI, NASA FIRMS, Open-Meteo, GPM IMERG, USGS, AISstream, USGS Water Services, NOAA NHC
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
- gad/monitor/sources/ — API fetchers (opensky, aviationstack, airnow, openaq, firms, openmeteo, gpm_imerg, usgs_earthquake, aisstream, noaa_flood, noaa_nhc)
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

## Env Vars

- SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY
- NASA_FIRMS_MAP_KEY, WAQI_API_TOKEN, OPENSKY_CLIENT_ID, OPENSKY_CLIENT_SECRET
- AVIATIONSTACK_API_KEY, OPENAQ_API_KEY, AIRNOW_API_KEY, NASA_EARTHDATA_TOKEN
- AISSTREAM_API_KEY — marine vessel tracking
- GAD_ORACLE_PRIVATE_KEY_HEX, GAD_ORACLE_PUBLIC_KEY_HEX, GAD_ORACLE_KEY_ID (v0.2.2)

## Near-Term Priorities

1. Basis risk precomputed for 221 triggers (done). Flight history (DATA-01c) and remaining AQI coverage pending.
2. Oracle signing + R2 upload + Oracle Ledger page (done).
3. Marine peril live with 10 ports (done). Flood (USGS Water Services) and cyclone (NOAA NHC) live. Next: crop/NDVI.
4. REST API (FastAPI) + MCP server.
5. Parametric Data Pro (enterprise tier).
