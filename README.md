# GAD — Global Actuarial Dashboard (Phase 1)

Parametric insurance basis-risk audit: Spearman metrics, back-test, and a Lloyd’s-style checklist over bundled open-data-style CSVs.

**License:** This project is under **AGPL-3.0** (see [LICENSE](LICENSE)). The trigger definition schema (YAML structure and schema docs) is additionally offered under **MIT** for ecosystem use — see [docs/LICENSE-SCHEMA.md](docs/LICENSE-SCHEMA.md). Anyone running a modified GAD oracle must open-source their modifications under the AGPL.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Open the URL shown in the terminal. By default **Kenya drought** is selected.

## Tests

```bash
pytest
```

## Layout

- `gad/` — Pydantic models, YAML I/O, `compute_basis_risk()` + `lloyds_check()`, registry, PDF export, open-data pipeline (CHIRPS skeleton)
- `data/triggers/` — example trigger YAML (drought, flood, earthquake, regional Kenya)
- `data/series/` — monthly demo time series referenced by `data/manifest.yaml`
- `DESIGN.md` — design system (colors, typography, spacing, components)
- `docs/GAP_ANALYSIS_ORACLE.md` — oracle / settlement direction (v0.2+); `docs/ORACLE_KEY_REGISTRY.md` for key registry; `docs/ORACLE_WEBHOOK_AND_LOG.md` for webhook and OracleLog contracts.

**Phase 2:** SQLite registry (Save/Load from registry in UI), regional triggers (bounding box + spatial averaging), PDF download per report, CHIRPS fetch skeleton in `gad/pipeline.py`.
