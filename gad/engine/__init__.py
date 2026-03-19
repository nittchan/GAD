"""
GAD computation engine (AGPL-3.0).
Spec-aligned models, basis risk, Lloyd's checklist, and oracle signing.
"""

from gad.engine.basis_risk import compute_basis_risk
from gad.engine.lloyds import lloyds_check
from gad.engine.models import (
    BacktestRow,
    BasisRiskReport,
    DataSourceProvenance,
    GadEvent,
    PolicyBinding,
    TriggerDef,
    TriggerDetermination,
)
from gad.engine.pdf_export import generate_lloyds_report
from gad.engine.oracle import (
    append_to_oracle_log,
    data_snapshot_hash,
    sign_determination,
    verify_determination,
)

__all__ = [
    "BacktestRow",
    "BasisRiskReport",
    "GadEvent",
    "DataSourceProvenance",
    "PolicyBinding",
    "TriggerDef",
    "TriggerDetermination",
    "compute_basis_risk",
    "lloyds_check",
    "generate_lloyds_report",
    "data_snapshot_hash",
    "sign_determination",
    "verify_determination",
    "append_to_oracle_log",
]
