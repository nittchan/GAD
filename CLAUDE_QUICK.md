# CLAUDE_QUICK.md

## Purpose

Fast context file for agents and contributors who need the essentials in under a minute.

## What GAD Is

GAD is an open-source parametric insurance platform with three layers:

1. Basis risk analytics dashboard.
2. Oracle determination and verification surface.
3. Account and activity layer via Supabase.

## Stage

- Current: v0.1 analysis product is functional.
- In progress: v0.2 oracle runtime hardening and real-time monitoring.

## Main Entry Points

- Primary UI: dashboard/app.py
- Alternate UI: app.py
- Oracle read API: oracle_ledger/worker.js

## Critical Architecture Fact

There are two active compute stacks:

1. gad/engine/ package stack (UUID-centric, dashboard-facing).
2. gad/engine.py + gad/models.py + gad/io.py stack (manifest/data-root driven).

Any refactor must pick a canonical stack first, then align imports/tests.

Recommended default: canonicalize on gad/engine/ and keep manifest loading as an adapter layer.

## User Flows in Dashboard

- Guided mode: build trigger in 4 steps and compute report.
- Expert mode: YAML edit and compute.
- Trigger profile: inspect one sample trigger.
- Compare: side-by-side trigger comparison.
- Account: auth, saved triggers, subscriptions.

## Data and Contracts

- Trigger schema: schema/trigger.schema.json
- Trigger examples: schema/examples/
- Demo series: data/series/
- Manifest map: data/manifest.yaml
- Oracle models: gad/oracle_models.py

## Oracle Surface (v0.1)

- GET /determination/{uuid}
- GET /.well-known/oracle-keys.json
- Signature field is schema-stable; may be empty in v0.1 artifacts.

## Supabase Core Tables

- profiles
- trigger_defs
- basis_risk_reports
- saved_triggers
- trigger_notifications
- oracle_determinations
- gad_events
- api_keys

## Tests That Matter

- tests/test_basis_risk.py
- tests/test_lloyds.py
- tests/test_oracle.py
- tests/test_reproducibility.py

## Env Vars

- SUPABASE_URL
- SUPABASE_ANON_KEY
- SUPABASE_SERVICE_KEY
- GAD_ORACLE_PRIVATE_KEY_HEX
- GAD_ORACLE_PUBLIC_KEY_HEX
- GAD_ORACLE_KEY_ID

## Deploy Surfaces

- Fly.io for dashboard (fly.toml, dashboard/Dockerfile)
- Cloudflare Worker + R2 for oracle ledger (oracle_ledger/wrangler.toml)

## Near-Term Priorities

1. Resolve dual-engine boundary.
2. Enable live signing with managed operational key and published key id.
3. Add integration coverage for worker contracts and pipeline failure paths.
4. Implement live trigger monitor and signed determination pipeline.
