# CLAUDE.md

## Scope Variants

- Quick context version: CLAUDE_QUICK.md
- Engineering-focused version: CLAUDE_ENGINEERING.md
- Contributor onboarding version: CLAUDE_ONBOARDING.md

## Project Scope: GAD (Global Actuarial Dashboard)

GAD is an open-source global parametric insurance platform — the "WorldMonitor for parametric insurance."

1. **Global Monitor** — live risk map across 5 peril categories (flights, AQI, wildfire, drought, weather) with 17 pre-built triggers using free open data.
2. **Basis risk engine** — Spearman correlation scoring, Lloyd's checklist, PDF export, guided/expert modes.
3. **Oracle infrastructure** — cryptographically signed, hash-chained trigger determinations (v0.2.2+).
4. **Account layer** — user auth, saved triggers, activity events via Supabase.

The product goal: become THE default global parametric insurance monitor. v0.2 ships the visible public dashboard; oracle signing layers underneath in v0.2.2+.

## Current Stage and Product Shape

Version indicators in the repository point to v0.1.x with partial v0.2 groundwork:

- v0.1 delivered:
  - Trigger schemas and sample triggers.
  - Basis risk computation with Spearman metrics and back-test outputs.
  - Lloyds-style checklist and PDF report export.
  - Dashboard with guided, expert, profile, compare, and account pages.
  - Oracle determination schema and verification primitives.
  - Cloudflare Worker surface for determination retrieval and key registry endpoint.

- v0.2 groundwork already present:
  - Oracle event and determination models.
  - Key registry and webhook/log contracts documented.
  - CHIRPS live data pipeline helpers.

- Not fully complete yet:
  - Real-time trigger monitor/event loop.
  - Fully operational policy-bound settlement pipeline.
  - Productionized key lifecycle and rotation workflows.

## Engine Migration (Completed 2026-03-23)

Canonicalized on gad/engine/ (UUID stack). Legacy modules (`gad/engine.py`, `gad/models.py`, `gad/io.py`), deprecated root `app.py`, `gad/pdf_export.py`, and `gad/registry.py` all deleted. Manifest format remains usable via `load_from_manifest()` adapter in `gad/engine/loader.py`. Landing commit: a21e66f4c19ae37561cc44bd552d3edf450f55a2.

## Repository Topology

Top-level domains and responsibilities:

- dashboard/
  - Primary Streamlit product UI.
  - app.py home/landing + multipage navigation.
  - pages/ global monitor, guided, expert, profile, compare, account.
  - components/ auth and visual rendering helpers.

- gad/
  - Core Python package.
  - gad/engine/ — compute core (basis risk, lloyds, oracle, models, loader, analytics, pdf_export).
  - gad/monitor/ — global monitor (triggers, cache, fetcher, security, data sources).
  - gad/monitor/sources/ — API fetchers (opensky, openaq, firms, openmeteo).
  - gad/pipeline.py — CHIRPS raster fetch and extraction.

- data/
  - Manifest and demo/reference series.
  - CHIRPS cache directory for pipeline artifacts.
  - monitor_cache/ — cached live data from background fetcher (gitignored).

- schema/
  - JSON schema and canonical example triggers.

- docs/
  - Deployment, oracle architecture, key registry, webhook/log contract, and gap analysis.

- oracle_ledger/
  - Cloudflare Worker that serves determinations and public keys from R2.

- supabase/
  - SQL migrations and seed.

- tests/
  - Basis risk, Lloyds, oracle signing/verification, and reproducibility tests.

## Runtime Surfaces

### Surface A: Dashboard App (primary)

Entry point: dashboard/app.py

User flows:

0. Global Monitor (dashboard/pages/6_Global_Monitor.py)
   - Interactive world map with 17 pre-built triggers across 5 perils.
   - Reads from local cache only — zero external API calls.
   - Trigger status cards with live values and threshold evaluation.
   - Background fetcher: `python -m gad.monitor.fetcher`

1. Guided mode (dashboard/pages/1_Guided_mode.py)
   - 4-step plain-English wizard.
   - Builds TriggerDef from user choices.
   - Computes basis risk using sample-mapped CSV.
   - Renders score card, timeline, scatter, confusion matrix, Lloyds checklist.
   - Exports Lloyds PDF.
   - Emits analytics events.

2. Expert mode (dashboard/pages/2_Expert_mode.py)
   - YAML editor path.
   - Validates trigger schema and computes report.
   - Same render and PDF pipeline as guided mode.

3. Trigger profile (dashboard/pages/3_Trigger_profile.py)
   - Single trigger deep profile from schema/examples and mapped series CSV.
   - Cached report computation.

4. Compare (dashboard/pages/4_Compare.py)
   - Side-by-side comparison of up to two triggers.

5. Account (dashboard/pages/5_Account.py)
   - OAuth callback/session management.
   - Reads saved triggers and notification subscriptions from Supabase.

## Core Engine and Data Contracts

### Engine package path (gad/engine/)

Main exports in gad/engine/__init__.py:

- compute_basis_risk
- lloyds_check
- generate_lloyds_report
- TriggerDef, TriggerDetermination, BasisRiskReport, GadEvent
- sign_determination, verify_determination, append_to_oracle_log, data_snapshot_hash

Primary models in gad/engine/models.py:

- TriggerDef
  - UUID trigger_id, peril, threshold logic, geography, provenance, optional policy binding.
- BasisRiskReport
  - Spearman rho + CI + p-value, FPR/FNR, period bounds, Lloyds score/details.
- TriggerDetermination
  - UUID identifiers, fired status/time, data_snapshot_hash, computation_version, prev_hash, signature.
- GadEvent
  - Append-only activity event shape for analytics.

Computation in gad/engine/basis_risk.py:

- Deterministic functional compute path.
- Requires at least 10 periods.
- Spearman correlation + bootstrap CI.
- Trigger fire simulation by threshold direction.
- Confusion-derived FPR/FNR.
- Lloyds scoring integration.

Loader in gad/engine/loader.py:

- CSV -> weather_data list conversion.
- Supports index_value/trigger_value and loss_proxy/loss_event normalization.

Oracle primitives in gad/engine/oracle.py:

- SHA-256 snapshot hashing.
- Canonical payload generation.
- Ed25519 signing and verification.
- Local append to registry/determinations as JSON files.

Analytics in gad/engine/analytics.py:

- Fire-and-forget tracking to Supabase gad_events.
- Uses SUPABASE_SERVICE_KEY for insert bypass of RLS.
- Session id helper for Streamlit flows.

### Legacy manifest path (deleted)

The legacy manifest-driven compute path (`gad/engine.py`, `gad/models.py`, `gad/io.py`) was deleted on 2026-03-23. The manifest YAML format remains usable through `load_from_manifest()` in `gad/engine/loader.py`, which converts manifest data into the canonical `weather_data` input format.

## Oracle and Ledger Scope

### Oracle data models

- gad/oracle_models.py defines TriggerEvent and TriggerDetermination as schema-first settlement artifacts.
- v0.1 permits empty signature while preserving final field set for forward compatibility.

### Cloudflare Worker

Path: oracle_ledger/worker.js

Responsibilities:

- GET /determination/{uuid}
  - Reads determinations/{uuid}.json from R2.
  - Returns JSON (Accept: application/json or ?format=json) or formatted HTML.

- GET /.well-known/oracle-keys.json
  - Returns oracle-keys.json from R2 or fallback {"keys":[]}.

Infra config:

- wrangler.toml binds ORACLE_BUCKET to gad-oracle-determinations.
- production routes target oracle.parametricdata.io for determination and well-known key endpoint.

### Oracle protocol documentation

- docs/GAP_ANALYSIS_ORACLE.md: strategy and architecture gap mapping.
- docs/ORACLE_KEY_REGISTRY.md: key registry JSON contract and verifier behavior.
- docs/ORACLE_WEBHOOK_AND_LOG.md: webhook interface and append-only OracleLog contract.

## Data and Schema Scope

### Trigger schema and examples

- schema/trigger.schema.json for trigger definition contract.
- schema/examples contains canonical examples:
  - kenya-drought-chirps.yaml
  - flight-delay-indigo.yaml
  - india-flood-imd.yaml

### Data bundles and manifest

- data/manifest.yaml maps trigger keys to series CSV paths for manifest-driven engine.
- data/series contains historical/demo datasets.
- data/triggers contains YAML trigger defs for manifest path.
- data/cache/chirps is pipeline cache.

### Pipeline scope

- gad/pipeline.py supports CHIRPS raster fetch and extraction to engine series CSV.
- Includes range fetch, point extraction, CSV normalization, and live manifest constructor.
- ERA5/NOAA pathways are intended but not fully implemented here.

## Supabase Scope

Migration: supabase/migrations/001_initial_schema.sql

Tables and responsibilities:

- profiles
- trigger_defs
- basis_risk_reports
- saved_triggers
- trigger_notifications
- oracle_determinations
- gad_events
- api_keys

Security model:

- RLS enabled across user-facing tables.
- Owner/public policies on trigger/report resources.
- gad_events and oracle_determinations restricted to service/system write paths.

App integration:

- dashboard/components/auth.py handles OAuth and magic link flows.
- account page reads saved triggers and subscriptions.
- analytics path emits event logs.

## Testing Scope

Current tests cover:

- tests/test_basis_risk.py
  - Basis report generation and insufficient data guardrails.

- tests/test_lloyds.py
  - Lloyds scoring/detail expectations.

- tests/test_oracle.py
  - Ed25519 sign/verify round-trip and tamper detection.

- tests/test_reproducibility.py
  - Deterministic compute outputs for selected trigger/data inputs.

Coverage gaps likely remain around:

1. Worker-level contract tests (highest risk)
  - Validate /determination/{uuid} html/json behavior, error handling, and key registry fallback contract.
2. CHIRPS pipeline network and raster error paths
  - Validate timeout, 404, corrupt raster, and out-of-bounds extraction behavior.
3. Dashboard page interaction flows and auth integration
  - Validate guided/expert/profile/account flows and session handling.
4. Supabase migration compatibility checks
  - Validate fresh-project migration execution and policy compatibility in CI.

## Deployment Scope

Primary docs and configs:

- docs/DEPLOYMENT.md
- fly.toml
- dashboard/Dockerfile
- oracle_ledger/wrangler.toml

Target architecture:

- Dashboard hosted on Fly.io.
- Ledger and key registry on Cloudflare Worker + R2.
- DNS and TLS managed in Cloudflare.

## Dependencies and Tooling

Python and package metadata:

- Python >= 3.12
- pyproject.toml and requirements.txt maintained.

Major libraries:

- pydantic, scipy, numpy, pandas
- streamlit, plotly, streamlit-ace
- cryptography, httpx, requests, rasterio
- reportlab
- supabase

Quality/dev tools (optional dev deps):

- pytest, pytest-asyncio, ruff, mypy

## Architectural Status

Canonical engine boundary is gad/engine/. Legacy modules deleted (2026-03-23).

All new compute, oracle, and test work targets gad/engine/ and gad/engine/loader.py.

## v0.2 Roadmap — Global Monitor

### v0.2.0 (built, needs deployment)
- Global Monitor with 17 triggers across 5 perils (flights, AQI, wildfire, drought, weather).
- Background fetcher with cache-based security (users never trigger API calls).
- Interactive world map with trigger status cards.
- 15/17 triggers fetch real data. 2 drought triggers need CHIRPS wiring.

### v0.2.1 (next)
- Wire CHIRPS drought data to fetcher.
- Get free API keys (FIRMS, WAQI, OpenSky) for full data quality.
- Deploy to Fly.io with Cloudflare proxy.
- Add more peril categories and pre-built triggers.
- Pre-compute historical basis risk for global triggers.

### v0.2.2 (oracle layer)
- Ed25519 signed determinations under the visible dashboard.
- Determination status page upgrade (verification proof page).
- OracleLog dual write (JSONL + per-file JSON).
- key_id field and genesis hash constant.

### v0.3 (platform)
- DataSourceConnector protocol for community-contributed sources.
- Verification SDK and CLI.
- Webhook delivery with HMAC-SHA256 auth.
- Deploy to Oracle button in dashboard.

## Operational Environment Variables

Required:
- SUPABASE_URL
- SUPABASE_ANON_KEY
- SUPABASE_SERVICE_KEY (for analytics writes)

Optional (improve Global Monitor data quality):
- NASA_FIRMS_MAP_KEY (free wildfire data — firms.modaps.eosdis.nasa.gov)
- WAQI_API_TOKEN (better AQI geo accuracy — aqicn.org/api)
- OPENSKY_USERNAME, OPENSKY_PASSWORD (higher rate limits — opensky-network.org)

Oracle (v0.2.2+):
- GAD_ORACLE_PRIVATE_KEY_HEX (Ed25519 operational key for signing)
- GAD_ORACLE_PUBLIC_KEY_HEX (matching Ed25519 public key)
- GAD_ORACLE_KEY_ID (UUID used in key-registry metadata)

Additional runtime credentials/configs are required for full production deployment of Fly, Cloudflare Worker, and R2.

## Practical Definition of Done

### v0.1 (complete)
- Dashboard computes and displays basis risk for sample triggers.
- Lloyds checklist and PDF export are available.
- Determination schema is fixed and verification function exists.
- Core tests pass for basis risk, Lloyds, oracle signing, and determinism.

### v0.2.0 (built, pending deployment)
- Global Monitor page with interactive world map and 17 triggers.
- Background fetcher pulling live data from 4 free APIs.
- Cache-based security model (users never trigger API calls).
- 15/17 triggers returning real data.

### v0.2.0 deployment checklist
- [ ] Get free API keys: NASA FIRMS, WAQI, OpenSky
- [ ] Wire CHIRPS drought data to fetcher
- [ ] Deploy to Fly.io (`fly deploy`)
- [ ] Add Cloudflare proxy for DDoS protection
- [ ] Verify all 17 triggers show live data
