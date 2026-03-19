# CLAUDE_ONBOARDING.md

## What This Project Is

GAD (Get Actuary Done) helps teams design and evaluate parametric insurance triggers, then publish oracle-style trigger determinations that can be independently verified.

Today, the strongest production-ready capability is trigger analysis and reporting. Oracle runtime pieces exist as contracts and partial implementations.

## First 15 Minutes

1. Create and activate a Python virtual environment.
2. Install dependencies from requirements.txt.
3. Run the dashboard app at dashboard/app.py.
4. Open Guided mode and compute a sample report.
5. Run tests with pytest.

## Where To Start In The Codebase

### Product UI

- dashboard/app.py: home page and navigation.
- dashboard/pages/: main user flows.
- dashboard/components/: score cards, charts, checklist, auth helpers.

### Compute and Models

- gad/engine/: package-style compute, models, lloyds, oracle helpers.
- gad/engine.py + gad/models.py + gad/io.py: alternate manifest-based compute path.

### Data and Schemas

- schema/trigger.schema.json: trigger schema contract.
- schema/examples/: example triggers used in dashboard flows.
- data/series/: sample historical time series.
- data/manifest.yaml: mapping for manifest-driven compute.

### Oracle Layer

- gad/oracle_models.py: settlement-oriented model definitions.
- oracle_ledger/worker.js: public determination/key endpoints.
- docs/ORACLE_KEY_REGISTRY.md: key publication format.
- docs/ORACLE_WEBHOOK_AND_LOG.md: webhook and append log contracts.

### Persistence and Auth

- supabase/migrations/001_initial_schema.sql: DB schema and RLS.
- dashboard/components/auth.py: sign-in and session handling.
- gad/engine/analytics.py: activity event writes.

## Main User Journeys

1. Guided mode: build trigger in plain English and compute basis risk.
2. Expert mode: edit YAML directly and compute.
3. Trigger profile: inspect one sample trigger in depth.
4. Compare: side-by-side trigger comparison.
5. Account: view saved triggers and notification subscriptions.

## Key Concepts You Need To Know

- Basis risk is quantified with Spearman correlation and back-test mismatch rates.
- Lloyds-style checklist is deterministic and explicit; pass/fail criteria are visible.
- Trigger determinations are designed to be cryptographically signed and hash-chained.
- Independent verifiability depends on stable schemas, pinned data snapshots, and published keys.

## Known Nuance Before You Change Anything

There are two active compute/model paths in the repo. Before refactoring or adding shared functionality, decide which path your change should target and verify affected tests.

If you touch imports named gad.engine, confirm whether callers expect the package path or the module path behavior.

## Safe Contribution Workflow

1. Pick one runtime surface (dashboard or root app) and keep scope local.
2. Update or add tests nearest to the behavior you changed.
3. Run pytest before opening a PR.
4. If you change contracts, update docs in docs/ and main claude.md.

## Testing Map

- tests/test_basis_risk.py: core compute shape and guardrails.
- tests/test_lloyds.py: checklist behavior.
- tests/test_oracle.py: sign/verify and tamper checks.
- tests/test_reproducibility.py: deterministic manifest-based outputs.

## Environment Variables

- SUPABASE_URL
- SUPABASE_ANON_KEY
- SUPABASE_SERVICE_KEY

Without these, authentication and event logging features are limited.

## Deployment Surfaces

- Dashboard: Fly.io (fly.toml, dashboard/Dockerfile).
- Oracle read endpoints: Cloudflare Worker + R2 (oracle_ledger/wrangler.toml).
- DNS/TLS expectations: docs/DEPLOYMENT.md.

## Good First Tasks

1. Add integration tests for one dashboard page flow.
2. Add contract tests for oracle worker response behavior.
3. Improve auth/session error handling in account page.
4. Document one canonical compute path and align imports incrementally.
