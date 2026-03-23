# CLAUDE_QUICK.md

## Purpose

Fast context file for agents and contributors who need the essentials in under a minute.

## What GAD Is

GAD is an open-source global parametric insurance platform — the "WorldMonitor for parametric insurance."

1. **Global Monitor** — live risk map across 5 peril categories (flights, AQI, wildfire, drought, weather) using free open data.
2. **Basis risk engine** — Spearman correlation scoring, Lloyd's checklist, PDF export.
3. **Oracle infrastructure** — cryptographically signed, hash-chained trigger determinations (v0.2.2+).
4. **Account layer** — user auth, saved triggers, activity events via Supabase.

## Stage

- v0.1: Basis risk dashboard with guided/expert modes. Functional and deployed.
- v0.2.0 (current): Global Monitor with 17 triggers across 5 perils. Background fetcher + cache-based security. Built, needs deployment.
- v0.2.2 (next): Oracle signing layer under the visible dashboard.

## Main Entry Points

- Dashboard: dashboard/app.py (Streamlit)
- Global Monitor page: dashboard/pages/6_Global_Monitor.py
- Background fetcher: python -m gad.monitor.fetcher
- Oracle read API: oracle_ledger/worker.js

## Architecture

```
Background fetcher (cron every 15 min)
  → Fetches from OpenSky, OpenAQ, NASA FIRMS, Open-Meteo
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
- gad/monitor/sources/ — API fetchers (opensky, openaq, firms, openmeteo)
- dashboard/ — Streamlit app with 6 pages
- oracle_ledger/ — Cloudflare Worker

## Data Sources (all free)

| Source | API | Key needed? |
|--------|-----|------------|
| OpenSky | Flight departures | Optional (higher rate limits) |
| OpenAQ / WAQI | Air quality index | Optional (better geo accuracy) |
| NASA FIRMS | Active fire detection | Yes (free registration) |
| Open-Meteo | Weather forecasts | No |
| CHIRPS | Rainfall (drought) | No |

## Env Vars

- SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY
- GAD_ORACLE_PRIVATE_KEY_HEX, GAD_ORACLE_PUBLIC_KEY_HEX, GAD_ORACLE_KEY_ID
- NASA_FIRMS_MAP_KEY (optional), WAQI_API_TOKEN (optional), OPENSKY_USERNAME/PASSWORD (optional)

## Near-Term Priorities

1. Get free API keys (FIRMS, WAQI, OpenSky) for full data quality.
2. Wire CHIRPS drought data to the background fetcher.
3. Deploy to Fly.io with Cloudflare proxy.
4. Add more peril categories and pre-built triggers.
5. Layer oracle signing (v0.2.2) under the visible dashboard.
