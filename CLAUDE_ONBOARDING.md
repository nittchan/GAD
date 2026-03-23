# CLAUDE_ONBOARDING.md

## What This Project Is

GAD (Global Actuarial Dashboard) is an open-source parametric insurance platform — think "WorldMonitor for parametric insurance." It monitors real-world risks (flight delays, air quality, wildfire, drought, extreme weather) and evaluates how well parametric insurance triggers would perform against those risks.

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
- dashboard/pages/1-5: guided mode, expert mode, trigger profile, compare, account.
- dashboard/components/: score cards, charts, checklist, auth helpers.

### Global Monitor (gad/monitor/)
- gad/monitor/triggers.py: 17 pre-built triggers across 5 perils with real coordinates.
- gad/monitor/cache.py: local JSON cache — dashboard reads from here, never from APIs.
- gad/monitor/fetcher.py: background worker that fetches data from external APIs on a schedule.
- gad/monitor/sources/: API connectors (OpenSky, OpenAQ, NASA FIRMS, Open-Meteo).
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

## Safe Contribution Workflow

1. Compute code: target gad/engine/. Monitor code: target gad/monitor/.
2. Update or add tests nearest to the behavior you changed.
3. Run `pytest` before opening a PR.
4. If you change contracts, update docs in docs/ and claude.md.

## Testing Map

- tests/test_basis_risk.py: core compute.
- tests/test_lloyds.py: checklist behavior.
- tests/test_oracle.py: sign/verify.
- tests/test_reproducibility.py: deterministic outputs.
- tests/test_import_hygiene.py: no legacy imports.

## Environment Variables

Required for full functionality:
- SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY

Optional (improve Global Monitor data quality):
- NASA_FIRMS_MAP_KEY — wildfire data (free at firms.modaps.eosdis.nasa.gov)
- WAQI_API_TOKEN — air quality (free at aqicn.org/api)
- OPENSKY_USERNAME, OPENSKY_PASSWORD — flight data (free at opensky-network.org)

## Deployment

- Dashboard: Fly.io (fly.toml, dashboard/Dockerfile).
- Oracle endpoints: Cloudflare Worker + R2 (oracle_ledger/wrangler.toml).
- DNS/DDoS: Cloudflare proxy recommended.

## Good First Tasks

1. Add a new peril category (earthquake via USGS API).
2. Wire CHIRPS drought data to the monitor fetcher.
3. Add integration tests for the Global Monitor page.
4. Add contract tests for oracle worker response behavior.
5. Add more pre-built triggers to gad/monitor/triggers.py.
