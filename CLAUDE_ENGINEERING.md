# CLAUDE_ENGINEERING.md

## Purpose

Engineering-focused scope summary for implementation, debugging, and refactor decisions.

## System Boundary

GAD operates as four integrated layers:

1. **Global Monitor** — live risk dashboard with 6 peril categories, background data fetching, cache-based reads.
2. **Basis risk engine** — Spearman correlation, bootstrap CI, Lloyd's checklist, PDF export.
3. **Oracle infrastructure** — Ed25519 signed determinations, hash-chained log, Cloudflare Worker read surface.
4. **Account/telemetry** — Supabase-backed auth, saved triggers, activity events.

Engine canonicalized on gad/engine/. Legacy modules deleted (2026-03-23). Global Monitor built (2026-03-23).

## Runtime Entry Points

- Dashboard: `streamlit run dashboard/app.py`
- Background fetcher: `python -m gad.monitor.fetcher` (cron) or `python -m gad.monitor.fetcher --loop` (continuous)
- Oracle read surface: oracle_ledger/worker.js

## Package Structure

### gad/engine/ — Compute core
- models.py: TriggerDef, BasisRiskReport, TriggerDetermination, PolicyBinding, GadEvent
- basis_risk.py: Spearman rho, bootstrap CI, confusion matrix, Lloyd's integration
- lloyds.py: Lloyd's checklist scoring
- oracle.py: Ed25519 sign/verify, hash chain, append-only log
- loader.py: CSV → weather_data, manifest adapter
- pdf_export.py: Lloyd's-formatted PDF reports
- analytics.py: Supabase event writes

### gad/monitor/ — Global Monitor
- airports.py: Master airport registry (50 Indian + 94 global = 144 airports)
- triggers.py: Auto-generates flight delay, weather, AQI, and earthquake triggers for all airports (436 triggers across 6 perils)
- cache.py: JSON file cache with TTL, staleness detection
- fetcher.py: Background worker fetches all sources on schedule
- security.py: Rate limiter, input sanitization, key management
- sources/opensky.py: Flight delay data (OpenSky Network API)
- sources/openaq.py: Air quality (OpenAQ v3 + WAQI fallback)
- sources/firms.py: Wildfire detection (NASA FIRMS)
- sources/openmeteo.py: Weather forecasts (Open-Meteo)

### Security model
```
Users → Dashboard → Cache (local JSON files) → Response
                     ↑
Background fetcher → External APIs → Cache
(cron, 15 min)

Users NEVER trigger API calls. Cost is fixed regardless of traffic.
```

## Dashboard Pages

- Global Monitor: dashboard/pages/6_Global_Monitor.py (interactive map + trigger cards)
- Guided mode: dashboard/pages/1_Guided_mode.py (4-step wizard)
- Expert mode: dashboard/pages/2_Expert_mode.py (JSON editor)
- Trigger profile: dashboard/pages/3_Trigger_profile.py
- Compare: dashboard/pages/4_Compare.py
- Account: dashboard/pages/5_Account.py

## Data Contracts

### Monitor triggers (gad/monitor/triggers.py)
Data-driven triggers auto-generated from airport registry (`gad/monitor/airports.py`): id, name, peril, lat/lon, threshold, unit, data_source, description.
436 triggers across 6 perils (144 flight delay + 125 AQI + 8 wildfire + 5 drought + 144 weather + 10 earthquake). Add new airports to the registry to expand coverage.

### Monitor cache (data/monitor_cache/)
JSON files with: source, key, data, cached_at, expires_at. Gitignored. Created by fetcher.

### Engine models (gad/engine/models.py)
UUID-centric TriggerDef, BasisRiskReport, TriggerDetermination. Pydantic v2.

### Oracle determination shape
determination_id, policy_id, trigger_id, fired, fired_at, data_snapshot_hash, computation_version, determined_at, prev_hash, signature. v0.1: empty signature. v0.2.2: signed + key_id.

## Test Coverage

- tests/test_basis_risk.py: core compute
- tests/test_lloyds.py: checklist scoring
- tests/test_oracle.py: sign/verify round-trip
- tests/test_reproducibility.py: deterministic outputs
- tests/test_import_hygiene.py: no legacy imports

Notable gaps:
- Monitor fetcher integration tests
- Dashboard page smoke tests
- CHIRPS pipeline error paths
- Worker contract tests

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

## Build and Runtime

- Python: >=3.12
- Packaging: pyproject.toml + requirements.txt
- Dashboard container: dashboard/Dockerfile
- Fly deployment: fly.toml (auto-stop, connection limits, 1GB)
- Worker deployment: oracle_ledger/wrangler.toml

## Environment Variables

Required:
- SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY

Optional (improve data quality):
- NASA_FIRMS_MAP_KEY — free wildfire data
- WAQI_API_TOKEN — better AQI geo accuracy
- OPENSKY_USERNAME, OPENSKY_PASSWORD — higher rate limits

Oracle (v0.2.2+):
- GAD_ORACLE_PRIVATE_KEY_HEX, GAD_ORACLE_PUBLIC_KEY_HEX, GAD_ORACLE_KEY_ID

## Near-Term Engineering Priorities

1. Historical basis risk for all 436 triggers (download historical series, pre-compute).
2. NOAA data sources: HRRR Smoke (wildfire), GFS (weather), SPI (drought).
3. Oracle signing (v0.2.2): wire Ed25519 to live monitor, determination status page.
4. New perils: shipping (AIS), health (WHO), solar (NOAA SWPC).
5. Parametric Data Pro: premium data sources, API access, enterprise features.
