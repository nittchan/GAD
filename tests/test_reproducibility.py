"""Same trigger + weather_data => identical BasisRiskReport (excluding object identity)."""

from pathlib import Path

import yaml

from gad.engine import BasisRiskReport, DataSourceProvenance, TriggerDef, compute_basis_risk
from gad.engine.loader import load_from_manifest


def _load_trigger_def(path: Path) -> TriggerDef:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Trigger YAML root must be a mapping")
    trigger_logic = raw.get("trigger_logic")
    if not isinstance(trigger_logic, dict):
        raise ValueError("Legacy trigger must include trigger_logic mapping")
    location = raw.get("location")
    if not isinstance(location, dict):
        raise ValueError("Legacy trigger must include location mapping")

    return TriggerDef(
        name=str(raw.get("name", raw.get("id", "trigger"))),
        peril=str(raw["peril"]),
        threshold=float(trigger_logic["threshold"]),
        threshold_unit=str(raw.get("variable", "index_value")),
        data_source="legacy_manifest",
        trigger_fires_when_above=(str(trigger_logic.get("kind")) == "threshold_above"),
        geography={
            "type": "Point",
            "coordinates": [float(location["lon"]), float(location["lat"])],
        },
        provenance=DataSourceProvenance(
            primary_source="legacy_manifest",
            primary_url="file://data/manifest.yaml",
            max_data_latency_seconds=0,
            historical_years_available=50,
        ),
    )


def test_compute_is_deterministic():
    root = Path(__file__).resolve().parent.parent / "data"
    for tid in ("kenya_drought", "kenya_regional", "vietnam_flood", "japan_earthquake"):
        t = _load_trigger_def(root / "triggers" / f"{tid}.yaml")
        weather_data = load_from_manifest(root / "manifest.yaml", tid, root)
        a: dict = compute_basis_risk(t, weather_data).model_dump()
        b: dict = compute_basis_risk(t, weather_data).model_dump()

        # object identity fields vary between runs and are not part of determinism checks
        a.pop("report_id", None)
        a.pop("computed_at", None)
        a.pop("backtest_start", None)
        a.pop("backtest_end_inclusive", None)
        b.pop("report_id", None)
        b.pop("computed_at", None)
        b.pop("backtest_start", None)
        b.pop("backtest_end_inclusive", None)

        assert isinstance(compute_basis_risk(t, weather_data), BasisRiskReport)
        assert a == b
