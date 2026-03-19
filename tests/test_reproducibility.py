"""Same trigger + manifest + data => identical BasisRiskReport (excluding object identity)."""

from pathlib import Path

from gad.engine import compute_basis_risk
from gad.io import load_data_manifest, load_trigger_def


def test_compute_is_deterministic():
    root = Path(__file__).resolve().parent.parent / "data"
    manifest = load_data_manifest(root / "manifest.yaml")
    for tid in ("kenya_drought", "vietnam_flood", "japan_earthquake"):
        t = load_trigger_def(root / "triggers" / f"{tid}.yaml")
        a = compute_basis_risk(t, manifest, root).model_dump()
        b = compute_basis_risk(t, manifest, root).model_dump()
        assert a == b
