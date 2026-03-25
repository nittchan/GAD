# CLAUDE_ONBOARDING.md

## What This Project Is

GAD (Global Actuarial Dashboard) is an open-source parametric insurance platform — think "WorldMonitor for parametric insurance." It monitors real-world risks (flight delays, air quality, wildfire, drought, extreme weather, earthquake, marine shipping, flood, cyclone, crop/NDVI, solar/space weather, health/pandemic) and evaluates how well parametric insurance triggers would perform against those risks.

The strongest production-ready capability is the Global Monitor (live risk map) and basis risk analysis. Oracle signing infrastructure exists as contracts and partial implementations.

## First 15 Minutes

1. Create and activate a Python virtual environment.
2. Install dependencies from requirements.txt.
3. Fetch live data: `python -m gad.monitor.fetcher`
4. Run the dashboard: `streamlit run dashboard/app.py`
5. Navigate to **Global Monitor** to see the live risk map.
6. Try **Guided mode** to build a custom trigger and compute basis risk.
7. Run tests with `pytest`.

## Where To Start In The Codebase

### Product UI (dashboard/)
- dashboard/app.py: home page and navigation.
- dashboard/pages/6_Global_Monitor.py: live risk map — the main public-facing page.
- dashboard/pages/1-7: guided mode, expert mode, trigger profile, compare, account, global monitor, oracle ledger.
- dashboard/components/: score cards, charts, checklist, auth helpers.

### Global Monitor (gad/monitor/)
- gad/monitor/airports.py: Master airport registry (50 Indian + 94 global = 144 airports). Each airport has runway coordinates (`lat`/`lon`) and optional city centre coordinates (`city_lat`/`city_lon`) — AQI triggers use city coordinates since AQI monitors are in urban areas, not at airfields.
- gad/monitor/ports.py: Port registry (10 tier-1 global ports with anchorage bounding boxes).
- gad/monitor/triggers.py: Auto-generates 521 triggers across 12 perils from the airport and port registries.
- gad/monitor/cache.py: local JSON cache — dashboard reads from here, never from APIs.
- gad/monitor/fetcher.py: background worker that fetches data from external APIs on a schedule.
- gad/monitor/sources/: API connectors (FAA ATCSCC, OpenSky, AviationStack, AirNow, OpenAQ, WAQI, NASA FIRMS, Open-Meteo, GPM IMERG, AISstream, USGS Water Services, NOAA NHC, Copernicus/MODIS NDVI, NOAA SWPC, WHO DON).
- gad/monitor/security.py: rate limiting, input sanitization.

### Compute Engine (gad/engine/)
- gad/engine/: canonical compute package — models, basis_risk, lloyds, oracle, loader, analytics, pdf_export.
- Single compute stack. No legacy alternatives.

### Data and Schemas
- schema/trigger.schema.json: trigger schema contract.
- schema/examples/: example triggers used in dashboard flows.
- data/series/: sample historical time series.
- data/monitor_cache/: cached live data from the fetcher (gitignored).

### Oracle Layer
- gad/engine/oracle.py: Ed25519 signing, verification, hash chain.
- oracle_ledger/worker.js: public determination/key endpoints.
- docs/: oracle architecture docs.

### Persistence and Auth
- supabase/migrations/001_initial_schema.sql: DB schema and RLS.
- dashboard/components/auth.py: sign-in and session handling.

## Key Concepts

- **Parametric insurance** pays when a trigger fires (e.g., rainfall below 50mm), not when damage is assessed.
- **Basis risk** is the gap between "trigger fired" and "actual loss occurred." Measured with Spearman correlation.
- **Global Monitor** shows live trigger status using real data from free public APIs.
- **Background fetcher** pre-fetches all data — users never trigger API calls (security/cost protection).
- **Oracle determinations** are cryptographically signed attestations that a trigger fired (v0.2.2+).

## Development Workflow

```
dev → staging (gad-dashboard-staging.fly.dev) → main (parametricdata.io)
```

1. All work happens on the `dev` branch.
2. Never push directly to `staging` or `main`.
3. Merge `dev` → `staging` to test at gad-dashboard-staging.fly.dev.
4. Merge `staging` → `main` to ship to parametricdata.io.
5. GitHub Actions auto-deploy on merge.

## Safe Contribution Workflow

1. Compute code: target gad/engine/. Monitor code: target gad/monitor/.
2. Update or add tests nearest to the behavior you changed.
3. Run `pytest` before opening a PR.
4. If you change contracts, update docs in docs/ and claude.md.

## Testing Map

- tests/test_basis_risk.py: core compute.
- tests/test_lloyds.py: checklist behavior.
- tests/test_oracle.py: sign/verify, genesis hash, chain verification.
- tests/test_reproducibility.py: deterministic outputs.
- tests/test_import_hygiene.py: no legacy imports.

## Environment Variables

Required for full functionality:
- SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY

Global Monitor data sources (all configured):
- NASA_FIRMS_MAP_KEY, WAQI_API_TOKEN, OPENSKY_CLIENT_ID, OPENSKY_CLIENT_SECRET
- AVIATIONSTACK_API_KEY, OPENAQ_API_KEY, AIRNOW_API_KEY, NASA_EARTHDATA_TOKEN

## Deployment

- Dashboard: Fly.io (fly.toml, dashboard/Dockerfile).
- Oracle endpoints: Cloudflare Worker + R2 (oracle_ledger/wrangler.toml).
- DNS/DDoS: Cloudflare proxy recommended.

## Good First Tasks

1. Add airports to `gad/monitor/airports.py` (auto-generates triggers). Set `city_lat`/`city_lon` if the airport is >15km from the city centre.
2. Add a new data source connector in `gad/monitor/sources/`.
3. Add integration tests for the Global Monitor page.
4. Add contract tests for oracle worker response behavior.
5. Run `python3 scripts/audit_airport_city_distance.py` to check for airports missing city coordinates.
