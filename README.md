# GAD — Global Actuarial Dashboard

Open-source parametric insurance platform. Live risk monitoring, basis risk scoring, and oracle infrastructure.

## Global Monitor

GAD monitors parametric insurance triggers across **5 peril categories** using free open data:

| Peril | Data Source | Triggers |
|-------|-----------|----------|
| Flight delay | OpenSky Network | BLR, DEL, JFK, LHR |
| Air quality | OpenAQ / WAQI | Delhi, Beijing, Lahore, LA |
| Wildfire | NASA FIRMS | California, NSW, Amazon |
| Drought | CHIRPS | Kenya, Rajasthan |
| Extreme weather | Open-Meteo | Cyclone, flood, heatwave, freeze |

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Fetch live data (runs once, ~30 seconds)
python -m gad.monitor.fetcher

# Launch dashboard
streamlit run dashboard/app.py
```

Open the URL shown in the terminal. Navigate to **Global Monitor** for the live risk map.

## Dashboard pages

- **Global Monitor** — Interactive world map with live trigger status across all perils
- **Guided mode** — Build a custom parametric trigger in 4 steps
- **Expert mode** — YAML editor for advanced trigger design
- **Trigger profile** — Deep-dive on a single trigger's basis risk
- **Compare** — Side-by-side trigger comparison
- **Account** — Saved triggers and subscriptions (Supabase)

## Verify a determination

```python
import requests
from gad.engine import verify_determination
from gad.engine.models import TriggerDetermination

det_json = requests.get(
    "https://oracle.gad.dev/determination/{uuid}?format=json"
).json()
det = TriggerDetermination(**det_json)

keys = requests.get(
    "https://oracle.gad.dev/.well-known/oracle-keys.json"
).json()
pubkey_hex = keys["keys"][0]["public_key_hex"]

print(verify_determination(det, bytes.fromhex(pubkey_hex)))  # True
```

## Layout

- `gad/engine/` — Computation core (AGPL): models, basis_risk, lloyds, oracle, loader
- `gad/monitor/` — Global monitor: data source fetchers, cache, pre-built triggers, security
- `schema/` — Trigger JSON Schema and example YAMLs (MIT)
- `dashboard/` — Streamlit app: home, global monitor, guided mode, expert mode, profile, compare, account
- `supabase/migrations/` — Initial schema
- `oracle_ledger/` — Cloudflare Worker for `/determination/{uuid}` and `/.well-known/oracle-keys.json`
- `docs/` — [Gap analysis](docs/GAP_ANALYSIS_ORACLE.md), [key registry](docs/ORACLE_KEY_REGISTRY.md), [webhook contracts](docs/ORACLE_WEBHOOK_AND_LOG.md), [deployment](docs/DEPLOYMENT.md)

## Security model

The public dashboard makes **zero external API calls**. All data is pre-fetched by a background worker and served from a local cache. Even 10,000 concurrent users cost nothing more in API calls than zero users.

- Background fetcher runs on a 15-minute schedule
- Users read only from cache (no user action triggers an API call)
- Fly.io auto-stop when idle ($0 when no traffic)
- Connection limits cap horizontal scaling
- Cloudflare proxy recommended for DDoS protection

## Tests

```bash
pytest
```

## Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). Dashboard on Fly.io, oracle ledger on Cloudflare Worker + R2.

## Documentation

- [DESIGN.md](DESIGN.md) — Design system (colors, typography, spacing, components)
- [TODOS.md](TODOS.md) — Roadmap and deferred work
- [GAD-design.md](GAD-design.md) — Original design document

## License

- **Engine:** AGPL-3.0 — see [LICENSE](LICENSE) and [LICENSE-engine](LICENSE-engine).
- **Schema:** MIT — see [LICENSE-schema](LICENSE-schema) and [docs/LICENSE-SCHEMA.md](docs/LICENSE-SCHEMA.md).
