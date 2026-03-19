# GAD — Global Actuarial Dashboard (Phase 1)

Parametric insurance basis-risk audit: Spearman metrics, back-test, and a Lloyd’s-style checklist over bundled open-data-style CSVs.

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

- `gad/` — Pydantic models, YAML I/O, `compute_basis_risk()` + `lloyds_check()`
- `data/triggers/` — example trigger YAML (drought, flood, earthquake)
- `data/series/` — monthly demo time series referenced by `data/manifest.yaml`
