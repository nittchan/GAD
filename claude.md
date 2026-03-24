# CLAUDE.md

**World's first open-source actuarial data platform.**
Author: Nitthin Chandran Nair. Built with Claude Code. Powered by OrbitCover (MedPiper — YC-backed).

## Scope Variants

- Quick context version: CLAUDE_QUICK.md
- Engineering-focused version: CLAUDE_ENGINEERING.md
- Contributor onboarding version: CLAUDE_ONBOARDING.md

## Development Workflow

```
dev branch        → local development (no auto-deploy)
                      ↓ merge
staging branch    → auto-deploys to gad-dashboard-staging.fly.dev
                      ↓ verify, then merge
main branch       → auto-deploys to parametricdata.io (production)
```

**Rules:**
- All work happens on `dev` (or feature branches off `dev`).
- Never push directly to `staging` or `main`.
- Merge `dev` → `staging` to test. Merge `staging` → `main` to ship.
- See docs/DEPLOYMENT.md for full deployment details.

## Project Scope: Parametric Data (parametricdata.io)

GAD is an open-source global parametric insurance platform — the "WorldMonitor for parametric insurance."

1. **Global Monitor** — live risk map across 6 peril categories (flights, AQI, wildfire, drought, weather, earthquake) with 436 triggers across 144 airports (50 Indian + 94 global), data-driven from airport registry (`gad/monitor/airports.py`). AQI triggers use city centre coordinates (not airport runway) for accurate monitoring station proximity.
2. **Basis risk engine** — Spearman correlation scoring, Lloyd's checklist, PDF export, guided/expert modes.
3. **Oracle infrastructure** — cryptographically signed, hash-chained trigger determinations (v0.2.2+).
4. **Account layer** — user auth, saved triggers, activity events via Supabase.

The product goal: become THE default global parametric insurance monitor. v0.2 ships the visible public dashboard; oracle signing layers underneath in v0.2.2+.

## Current Stage and Product Shape

**v0.2.1 is live at parametricdata.io.** The product has evolved significantly from v0.1:

- v0.1 (2026-03-19): Basis risk dashboard with 3 sample triggers, guided/expert modes, PDF export.
- v0.2.0 (2026-03-23): Global Monitor with 426 triggers across 144 airports, 5 perils, interactive map.
- v0.2.1 (2026-03-23): Multi-source data connectors (AviationStack, AirNow, FIRMS dual satellite, GPM IMERG). All pages unified under the 426-trigger registry.

Current capabilities:
  - Global Monitor: live risk map with 436 triggers, hover tooltips, peril/country filters.
  - Multi-source fetcher: priority fallback across 9 data sources.
  - All pages wired to the trigger registry (Trigger Profile, Compare, Guided Mode, Expert Mode, Monitor Status).
  - Oracle signing primitives exist (Ed25519 sign/verify) but not yet wired to live monitor (v0.2.2).
  - Deployed at parametricdata.io with Cloudflare DDoS protection.

Not yet complete (v0.2.2+):
  - Oracle signing wired to live monitor (Ed25519 primitives exist, not yet connected).
  - Determination status page upgrade (verification proof UI).
  - Historical basis risk precomputed for 221 triggers (144 weather + 72 AQI + legacy). Rho badges on Global Monitor. Trigger Profile shows full reports.
  - New perils: shipping (AIS), health (WHO), solar (NOAA SWPC).
  - Parametric Data Pro (enterprise tier).

## Engine Migration (Completed 2026-03-23)

Canonicalized on gad/engine/ (UUID stack). Legacy modules (`gad/engine.py`, `gad/models.py`, `gad/io.py`), deprecated root `app.py`, `gad/pdf_export.py`, and `gad/registry.py` all deleted. Manifest format remains usable via `load_from_manifest()` adapter in `gad/engine/loader.py`. Landing commit: a21e66f4c19ae37561cc44bd552d3edf450f55a2.

## Repository Topology

Top-level domains and responsibilities:

- dashboard/
  - Primary Streamlit product UI.
  - app.py home/landing + multipage navigation.
  - pages/ global monitor, guided, expert, profile, compare, account, oracle.
  - components/ auth and visual rendering helpers.

- gad/
  - Core Python package.
  - gad/engine/ — compute core (basis risk, lloyds, oracle, models, loader, analytics, pdf_export).
  - gad/monitor/ — global monitor (triggers, cache, fetcher, security, data sources).
  - gad/monitor/sources/ — API fetchers (opensky, aviationstack, airnow, openaq, firms, openmeteo, imerg).
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
   - Interactive world map with 436 triggers across 144 airports and 6 perils.
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
   - JSON editor. Validates as MonitorTrigger.
   - Computes basis risk with sample data when available.

3. Trigger profile (dashboard/pages/3_Trigger_profile.py)
   - Single trigger deep profile from schema/examples and mapped series CSV.
   - Cached report computation.

4. Compare (dashboard/pages/4_Compare.py)
   - Side-by-side comparison of up to two triggers.

5. Account (dashboard/pages/5_Account.py)
   - OAuth callback/session management.
   - Reads saved triggers and notification subscriptions from Supabase.

6. Oracle Ledger (dashboard/pages/7_Oracle.py)
   - Chain verification status, total determinations, recent entries.
   - Links to Cloudflare Worker URLs for each determination.

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
  - Genesis hash validation, hash chain verification, broken-genesis detection.

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

## Roadmap

### v0.2.0 — Global Monitor (SHIPPED 2026-03-23)
- 426 triggers across 144 airports (50 Indian + 94 global), 5 perils.
- Background fetcher, cache-based security, interactive map. Deployed to parametricdata.io.

### v0.2.1 — Multi-Source Data (SHIPPED 2026-03-23)
- Multi-source connectors: AviationStack, AirNow, FIRMS VIIRS+MODIS, GPM IMERG, OpenAQ v3.
- Priority fallback protocol. All 8 API keys configured. All pages unified under registry.

### v0.2 remaining
- Historical basis risk for all 436 triggers.
- NOAA HRRR Smoke, NOAA GFS weather, NOAA SPI drought.

### v0.2.2 (oracle layer — next milestone)
- Ed25519 signed determinations wired to live monitor.
- Determination status page upgrade (verification proof).
- OracleLog dual write, key_id field, genesis hash.

### v0.3 (platform)
- New perils: shipping (AIS), health (WHO), solar (NOAA SWPC).
- Verification SDK + CLI, webhook delivery, Deploy to Oracle button.
- Parametric Data Pro (enterprise tier).

## Operational Environment Variables

Required:
- SUPABASE_URL
- SUPABASE_ANON_KEY
- SUPABASE_SERVICE_KEY (for analytics writes)

Global Monitor data sources (all configured):
- NASA_FIRMS_MAP_KEY (wildfire — VIIRS + MODIS)
- WAQI_API_TOKEN (air quality — global)
- OPENSKY_CLIENT_ID, OPENSKY_CLIENT_SECRET (flights — OAuth2, 4000 credits/day)
- AVIATIONSTACK_API_KEY (flight schedules — tier-1 airports, 500 req/mo)
- OPENAQ_API_KEY (air quality — open data)
- AIRNOW_API_KEY (air quality — US EPA authoritative)
- NASA_EARTHDATA_TOKEN (GPM IMERG — daily precipitation)

Oracle (v0.2.2+):
- GAD_ORACLE_PRIVATE_KEY_HEX (Ed25519 operational key for signing)
- GAD_ORACLE_PUBLIC_KEY_HEX (matching Ed25519 public key)
- GAD_ORACLE_KEY_ID (UUID used in key-registry metadata)

Additional runtime credentials/configs are required for full production deployment of Fly, Cloudflare Worker, and R2.

## Practical Definition of Done

### v0.1 (complete 2026-03-19)
- Dashboard with 3 sample triggers, guided/expert modes, PDF export.

### v0.2.1 (complete 2026-03-23)
- [x] Global Monitor with 426 triggers across 144 airports, 5 perils
- [x] Multi-source data connectors with priority fallback (8 APIs)
- [x] All pages wired to 426-trigger registry
- [x] Deployed to parametricdata.io with Cloudflare DDoS
- [x] Dev → staging → production workflow
- [x] All 8 API keys configured on Fly.io

### v0.2.2 (next)
- [ ] Oracle signing wired to live monitor
- [ ] Determination status page with verification proof
- [ ] Historical basis risk for all triggers
