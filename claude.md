# CLAUDE.md

## Scope Variants

- Quick context version: CLAUDE_QUICK.md
- Engineering-focused version: CLAUDE_ENGINEERING.md
- Contributor onboarding version: CLAUDE_ONBOARDING.md

## Project Scope: GAD (Get Actuary Done)

GAD is an open-source parametric insurance platform with three integrated layers:

1. Basis risk analytics dashboard for trigger design and evaluation.
2. Oracle infrastructure for signed, hash-chained trigger determinations.
3. Practitioner intelligence and account activity layer via Supabase.

The product goal is to move from pre-trade actuarial analysis (v0.1) toward treaty-grade, independently verifiable post-trade determinations (v0.2+).

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

## Highest-Risk Blocker Before v0.2 (Resolved In Working Tree)

The dual engine/model stack was the primary architectural risk in this repository:

- gad/engine/ package stack
  - UUID-based models, dashboard-integrated compute path.
- gad/_engine_legacy.py + gad/_models_legacy.py + gad/_io_legacy.py stack
  - Retired legacy manifest-driven compute path kept only for one migration safety window.

What was blocker-level:

- Different entrypoints can execute different computation/model contracts.
- tests/test_reproducibility.py previously validated the manifest path, not the dashboard path.
- Oracle work on top of split compute paths risks non-equivalent determinations.

Resolution applied:

- Option A selected: canonicalized on gad/engine/ (UUID stack)
  - Retired gad/engine.py, gad/models.py, gad/io.py to *_legacy.py files.
  - Rewrote reproducibility test to canonical package path + weather_data contract.
  - Added manifest compatibility adapter load_from_manifest() to gad/engine/loader.py.
  - Marked root app.py as deprecated and pinned it to explicit legacy imports.

- Option B rejected: canonicalize on gad/engine.py (manifest stack)
  - Not aligned with dashboard, oracle models, or Supabase-oriented UUID contracts.

Migration status: retirement is complete in the current working tree; delete *_legacy.py files in the follow-up cleanup commit after one safety cycle.
Retirement landing commit: a21e66f4c19ae37561cc44bd552d3edf450f55a2

## Option A migration checklist (engine canonicalization)

Execute in order. Each step should leave tests passing before moving to the next.

### 1. Verify canonical imports compile

- [x] `from gad.engine import compute_basis_risk, TriggerDef, BasisRiskReport` resolves to `gad/engine/__init__.py`, not `gad/engine.py`.
- [x] Confirm with:

```bash
python -c "import gad.engine; print(gad.engine.__file__)"
```

Expected: `.../gad/engine/__init__.py`

### 2. Rewrite test_reproducibility.py

- [x] Replace `from gad.engine import ...` + `from gad.io import ...` + `from gad.models import ...` with `from gad.engine import ...`.
- [x] Replace manifest-driven `compute_basis_risk(trigger, manifest, data_root)` calls with loader-driven `compute_basis_risk(trigger_def, weather_data)`.
- [x] Confirm test passes:

```bash
pytest tests/test_reproducibility.py -v
```

### 3. Move manifest adapter into gad/engine/loader.py

- [x] Add `load_from_manifest(manifest_path, trigger_key, data_root) -> list[dict]` that reads manifest YAML and returns `weather_data` list.
- [x] Confirm existing loader tests still pass.

### 4. Audit root app.py

- [x] List every import from `gad.engine` (module), `gad.models`, `gad.io`.
- [x] Either rewrite to use `gad.engine` (package) or mark file as deprecated with a header comment: `# DEPRECATED: use dashboard/app.py`.
- [x] Do not delete yet; confirm nothing in CI depends on it.

### 5. Retire legacy files (only after steps 1-4 pass)

- [x] `git mv gad/engine.py gad/_engine_legacy.py` (rename, do not delete in the same commit).
- [x] `git mv gad/models.py gad/_models_legacy.py`.
- [x] `git mv gad/io.py gad/_io_legacy.py`.
- [x] Run full test suite:

```bash
pytest tests/ -v
```

- [x] Verify no remaining imports reach legacy path:

```bash
grep -r "from gad\.engine import\|from gad\.models import\|from gad\.io import" \
  --include="*.py" . \
  | grep -v "_legacy\|#"
```

Expected: zero lines of `from gad.models import` or `from gad.io import` outside approved fixture exceptions.

- [ ] If clean: delete the `_legacy` files in the next commit.

### 6. Update CLAUDE.md

- [x] Move Highest-Risk Blocker section to resolved status after retirement lands.
- [x] Update Alternate manifest path section to Legacy path (retired).
- [x] Note the git commit hash where retirement landed: a21e66f4c19ae37561cc44bd552d3edf450f55a2.

Migration note: `data/manifest.yaml` is not retired by this migration. The manifest format remains valid input through `load_from_manifest()` in `gad/engine/loader.py`; only direct legacy Python module usage is retired.

## Repository Topology

Top-level domains and responsibilities:

- app.py
  - Legacy/alternate Streamlit app surface rooted at repository level.
  - Explicitly pinned to gad/_models_legacy.py, gad/_io_legacy.py, gad/_engine_legacy.py.

- dashboard/
  - Primary Streamlit product UI.
  - app.py home/landing + multipage navigation.
  - pages/ guided, expert, profile, compare, account experiences.
  - components/ auth and visual rendering helpers.

- gad/
  - Core Python package.
  - Canonical model/engine track:
    - gad/engine/ package (spec-aligned, UUID-centered, dashboard-integrated).
  - Retired legacy compatibility files:
    - gad/_engine_legacy.py + gad/_models_legacy.py + gad/_io_legacy.py.
  - Also includes oracle models, pdf export, pipeline, and registry adapters.

- data/
  - Manifest and demo/reference series.
  - Trigger YAML definitions for manifest-driven path.
  - CHIRPS cache directory for pipeline artifacts.

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

### Surface B: Root App (alternate)

Entry point: app.py

- Uses manifest-trigger mapping and gad.engine.py compute path.
- Includes CHIRPS live pipeline helper hooks and local registry path.
- Appears to coexist with dashboard app, likely as older or parallel implementation track.

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

### Legacy manifest path (retired)

The retired compatibility path defines:

- Trigger ids as lowercase string keys (not UUIDs).
- DataManifest mapping trigger ids -> series refs.
- compute_basis_risk(trigger, manifest, data_root) using CSV columns:
  - period, index_value, spatial_ref, loss_event, optional loss_proxy.
- Optional bounding-box regional aggregation.
- Zero-trigger-fire warnings and checklist criterion for degeneracy.

This path is no longer the canonical compute/test path. tests/test_reproducibility.py now validates the package engine API and uses load_from_manifest() adapter output as weather_data input.

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
- production routes target oracle.gad.dev for determination and well-known key endpoint.

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

Canonical engine boundary is now set to gad/engine/.

Legacy manifest modules were renamed to *_legacy.py and retained temporarily for migration safety only.

Any new compute, oracle, and test work should target gad/engine/ and gad/engine/loader.py.

Next cleanup action: remove *_legacy.py modules in the follow-up commit once import-sweep and runtime confidence checks remain clean.

## v0.2 Readiness and Dependency Order

Status snapshot:

- Real-time trigger monitor: not functional.
- Ed25519 signing in production flow: primitives exist, live key-managed signing not complete.
- CHIRPS live pipeline: partial helpers implemented, hardening/tests incomplete.
- Policy-bound settlement pipeline: schema groundwork present, runtime not complete.
- Notification automation: schema groundwork present, delivery runtime not complete.
- SQLite trigger/report registry: roadmap only.

Recommended dependency order:

1. Resolve dual-stack into one canonical engine path.
2. Enable live signing with managed operational key and published key id/public key flow.
3. Harden CHIRPS pipeline with failure-path tests.
4. Build real-time trigger monitor emitting TriggerDetermination artifacts.
5. Wire notification delivery and scheduling runtime.

## Roadmap Signals (from TODOS and docs)

Near-term intended expansions include:

- SQLite-backed trigger/report registry.
- Regional/spatial trigger support beyond point-only simplification.
- Automated open-data ingestion pipelines.
- Robust handling when trigger never fires in back-tests.
- Full live oracle runtime with policy-bound monitoring and signed settlement delivery.

## Operational Environment Variables

Expected env vars across runtime surfaces:

- SUPABASE_URL
- SUPABASE_ANON_KEY
- SUPABASE_SERVICE_KEY (for analytics writes)
- GAD_ORACLE_PRIVATE_KEY_HEX (Ed25519 operational key for signing, v0.2)
- GAD_ORACLE_PUBLIC_KEY_HEX (matching Ed25519 public key, v0.2)
- GAD_ORACLE_KEY_ID (UUID used in key-registry metadata, v0.2)

Additional runtime credentials/configs are required for full production deployment of Fly, Cloudflare Worker, and R2.

## Practical Definition of Done for v0.1 in this Repo

From code and documentation, v0.1 is considered complete when:

- Dashboard computes and displays basis risk for sample triggers.
- Lloyds checklist and PDF export are available.
- Determination schema is fixed and verification function exists.
- Ledger read path and key registry endpoint contracts are public.
- Core tests pass for basis risk, Lloyds, oracle signing, and determinism.

What remains is mainly production hardening and v0.2 real-time oracle behaviors.
