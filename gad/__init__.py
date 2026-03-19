"""GAD — Global Actuarial Dashboard (parametric insurance basis risk)."""

from gad.engine import compute_basis_risk, lloyds_check
from gad.io import load_data_manifest, load_trigger_def

__all__ = [
    "compute_basis_risk",
    "lloyds_check",
    "load_data_manifest",
    "load_trigger_def",
]
