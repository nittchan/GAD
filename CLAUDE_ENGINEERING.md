# CLAUDE_ENGINEERING.md

## Purpose

Engineering-focused scope summary for implementation, debugging, and refactor decisions.

## System Boundary

GAD currently operates as a hybrid of:

1. A Streamlit analysis product for parametric trigger quality evaluation.
2. An oracle contract surface for determination retrieval and key registry publication.
3. A Supabase-backed account and event telemetry layer.

The architecture is in a migration phase with two partially overlapping engine stacks.

## Runtime Entry Points

- Primary app: dashboard/app.py
- Alternate app: app.py
- Oracle read surface: oracle_ledger/worker.js

## Core Code Paths

### Path A: package engine (gad/engine/)

- Data model: UUID-centric TriggerDef, BasisRiskReport, TriggerDetermination.
- Compute API: compute_basis_risk(trigger, weather_data)
- Input format: weather_data list of dicts with trigger_value/index_value + loss_proxy/loss_event.
- Risk metrics: Spearman rho, bootstrap CI, p-value, FPR/FNR, Lloyds detail.
- Crypto: canonical-payload Ed25519 sign/verify and local append-only determination persistence.
- Event telemetry: GadEvent writes to Supabase gad_events using service key.

### Path B: manifest engine (gad/engine.py + gad/models.py + gad/io.py)

- Data model: string trigger ids keyed in manifest.
- Compute API: compute_basis_risk(trigger, manifest, data_root)
- Input format: CSV series referenced via data/manifest.yaml.
- Extra behavior: optional bounding box aggregation and explicit zero-trigger-fire warnings.
- Determinism test coverage currently points here.

## Current Architectural Risk

Dual-stack coexistence introduces:

- API signature divergence for compute_basis_risk.
- Model divergence (UUID vs string ids; different TriggerDef fields).
- Test/runtime ambiguity depending on import path resolution.

Refactor prerequisite: choose canonical engine boundary, then align imports and fixtures in one wave.

Recommended direction: canonicalize on gad/engine/ (UUID stack), then migrate manifest loading into gad/engine/loader.py as a compatibility adapter.

## Data Contracts

### Trigger definitions

- Product examples: schema/examples/*.yaml.
- Manifest path triggers: data/triggers/*.yaml.
- JSON contract: schema/trigger.schema.json.

### Series data

- Manifest-mapped datasets: data/series/*.csv.
- Expected columns vary by engine path.

### Oracle determination shape

Common required fields across code/docs:

- determination_id
- policy_id
- trigger_id
- fired
- fired_at
- data_snapshot_hash
- computation_version
- determined_at
- prev_hash
- signature

v0.1 permits empty signature while preserving schema stability.

## Operational Surfaces

### Dashboard pages

- Guided mode: dashboard/pages/1_Guided_mode.py
- Expert mode: dashboard/pages/2_Expert_mode.py
- Trigger profile: dashboard/pages/3_Trigger_profile.py
- Compare: dashboard/pages/4_Compare.py
- Account: dashboard/pages/5_Account.py

### Oracle worker routes

- GET /determination/{uuid}
- GET /.well-known/oracle-keys.json

Storage backend: Cloudflare R2 via ORACLE_BUCKET binding.

## Persistence Layer

Supabase schema in supabase/migrations/001_initial_schema.sql defines:

- profiles
- trigger_defs
- basis_risk_reports
- saved_triggers
- trigger_notifications
- oracle_determinations
- gad_events
- api_keys

RLS is enabled; user writes are constrained; service-role paths are used for system telemetry.

## Test Coverage Snapshot

- Basis risk compute: tests/test_basis_risk.py
- Lloyds checklist scoring: tests/test_lloyds.py
- Oracle signature verification: tests/test_oracle.py
- Deterministic manifest compute: tests/test_reproducibility.py

Notable gaps:

- Dashboard integration behavior.
- Auth/session E2E coverage.
- Pipeline network/raster failure modes.
- Worker contract tests.

## Build and Runtime

- Python: >=3.12
- Packaging: pyproject.toml + requirements.txt
- Dashboard container: dashboard/Dockerfile
- Fly deployment: fly.toml
- Worker deployment: oracle_ledger/wrangler.toml

## Required Environment Variables

- SUPABASE_URL
- SUPABASE_ANON_KEY
- SUPABASE_SERVICE_KEY
- GAD_ORACLE_PRIVATE_KEY_HEX
- GAD_ORACLE_PUBLIC_KEY_HEX
- GAD_ORACLE_KEY_ID

Additional infra credentials are required for Fly/Cloudflare/R2 operations.

## Near-Term Engineering Priorities

1. Decide canonical engine path and retire the duplicate stack.
2. Add integration tests around dashboard compute flows and auth.
3. Move oracle from schema/read-only posture to live signed append pipeline.
4. Harden key lifecycle and registry publication workflow.
5. Expand data ingestion from static bundles to managed live feeds.
