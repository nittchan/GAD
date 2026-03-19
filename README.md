# GAD — Get Actuary Done

Open-source oracle infrastructure for parametric insurance.

## Verify a determination

```python
import requests
from gad.engine import verify_determination
from gad.engine.models import TriggerDetermination

det_json = requests.get(
    "https://oracle.gad.dev/determination/{uuid}?format=json"
).json()
det = TriggerDetermination(**det_json)

# Fetch OrbitCover's published public key
keys = requests.get(
    "https://oracle.gad.dev/.well-known/oracle-keys.json"
).json()
pubkey_hex = keys["keys"][0]["public_key_hex"]

print(verify_determination(det, bytes.fromhex(pubkey_hex)))  # True
```

## What is GAD

GAD is three things:

1. **A basis risk dashboard** — Pick any parametric trigger, see its Spearman correlation score, historical back-test, and Lloyd's alignment rating.
2. **An oracle infrastructure layer** — Every trigger determination is cryptographically signed, hash-chained, and published to a permanent public ledger at `/determination/{uuid}`.
3. **A practitioner intelligence layer** — User accounts, saved triggers, and an activity event log (Supabase).

Two entry points into the same engine: **Guided mode** (4-step wizard, plain English) and **Expert mode** (YAML editor). Both produce the same `TriggerDef` and `BasisRiskReport`. Lloyd's-formatted PDF export and activity tracking (e.g. `trigger_viewed`, `report_computed`, `report_downloaded_pdf`) ship with the dashboard.

## Live dashboard

Run the spec-aligned dashboard (first-run: Kenya drought in under 10 seconds):

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run dashboard/app.py
```

Open the URL shown in the terminal. **Home** shows a hero and two CTAs: **Try a sample trigger** (loads Kenya drought profile) or **Build your own** (guided wizard). **Expert mode** offers the YAML editor; **Trigger profile** and **Compare** run the basis risk engine.

## Trigger registry

Example triggers live in `schema/examples/`:

- `kenya-drought-chirps.yaml` — Drought, CHIRPS v2.0, Marsabit
- `flight-delay-indigo.yaml` — Flight delay, DGCA + OpenSky, Kempegowda
- `india-flood-imd.yaml` — Flood, IMD gridded, Patna

## Score a new trigger

Use the dashboard sidebar to select one or two triggers. Add your own trigger YAML under `schema/examples/` (see `schema/trigger.schema.json` for the schema) and ensure a corresponding series CSV exists under `data/series/` (columns: `period`, `index_value`, `loss_proxy`).

## Tests

```bash
pytest
```

## Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for DNS (gad.dev), Cloudflare Worker (oracle ledger), R2, and Fly.io dashboard (fly.toml, dashboard/Dockerfile).

## Layout

- `gad/engine/` — Computation core (AGPL): models, basis_risk, lloyds, oracle, loader
- `schema/` — Trigger JSON Schema and example YAMLs (MIT)
- `dashboard/` — Streamlit app (home, guided mode, expert mode, trigger profile, compare, account) and components (score card, charts, Lloyd's checklist, auth)
- `supabase/migrations/` — Initial schema (profiles, trigger_defs, basis_risk_reports, saved_triggers, gad_events, etc.)
- `oracle_ledger/` — Cloudflare Worker for `/determination/{uuid}` and `/.well-known/oracle-keys.json`
- `registry/determinations/` — Local oracle log (flat JSON); production uses R2
- `docs/` — Gap analysis, key registry, webhook and OracleLog contracts

## v0.1 must-have checklist

- [x] `TriggerDetermination` schema frozen with `data_snapshot_hash`, `computation_version`, `prev_hash`, `signature` (empty string in v0.1)
- [x] `PolicyBinding` and `DataSourceProvenance` in trigger schema
- [x] `LICENSE-engine` (AGPL-3.0) and `LICENSE-schema` (MIT) present
- [ ] `oracle.gad.dev` domain registered, DNS live, Cloudflare proxy active
- [ ] Cloudflare Worker deployed — `/determination/` returns 404 gracefully when no determinations
- [ ] `/.well-known/oracle-keys.json` returns `{"keys":[]}` (v0.1)
- [x] `verify_determination()` is the first code example in README
- [x] Three example triggers pre-loaded in dashboard on first visit
- [ ] Supabase project created, `001_initial_schema.sql` run, Google OAuth configured
- [x] Guided mode wizard (4 steps) and expert mode (YAML); Lloyd's PDF export
- [x] Activity events (`gad_events`) via `engine/analytics.py` (use `SUPABASE_SERVICE_KEY` for writes)

## License

- **Engine:** AGPL-3.0 — see [LICENSE](LICENSE) and [LICENSE-engine](LICENSE-engine).
- **Schema:** MIT — see [LICENSE-schema](LICENSE-schema) and [docs/LICENSE-SCHEMA.md](docs/LICENSE-SCHEMA.md).
