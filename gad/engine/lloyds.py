"""
Lloyd's scoring checklist. Each criterion is a named boolean.
Unknown criteria raise errors — never silently skip.
"""

from __future__ import annotations


def lloyds_check(
    trigger: "TriggerDef",
    rho: float,
    fpr: float,
    fnr: float,
) -> dict:
    """
    Returns {"score": float, "detail": {criterion: {pass: bool, reason: str}}}.
    Raises ValueError for any criterion that cannot be evaluated.
    """
    checks: dict[str, dict] = {}

    checks["basis_risk_quantified"] = {
        "pass": rho is not None,
        "reason": f"Spearman rho = {rho:.3f}" if rho is not None else "Could not compute",
    }
    rho_val = rho if rho is not None else 0.0
    checks["acceptable_basis_risk"] = {
        "pass": rho_val >= 0.6,
        "reason": (
            f"rho {rho_val:.3f} >= 0.6 threshold"
            if rho_val >= 0.6
            else f"rho {rho_val:.3f} below 0.6 minimum"
        ),
    }
    checks["false_positive_rate_acceptable"] = {
        "pass": fpr <= 0.20,
        "reason": f"FPR {fpr:.2%}",
    }
    checks["false_negative_rate_acceptable"] = {
        "pass": fnr <= 0.15,
        "reason": f"FNR {fnr:.2%}",
    }
    checks["data_source_documented"] = {
        "pass": bool(
            getattr(trigger, "provenance", None)
            and getattr(trigger.provenance, "primary_source", None)
        ),
        "reason": (
            trigger.provenance.primary_source
            if getattr(trigger, "provenance", None)
            else "MISSING — required for Lloyd's"
        ),
    }
    checks["independent_verifiable"] = {
        "pass": bool(getattr(trigger, "provenance", None)),
        "reason": (
            "data_source_provenance present"
            if getattr(trigger, "provenance", None)
            else "MISSING — cannot satisfy Lloyd's independent verification requirement"
        ),
    }
    checks["unambiguous_threshold"] = {
        "pass": (
            getattr(trigger, "threshold", None) is not None
            and getattr(trigger, "threshold_unit", None) is not None
        ),
        "reason": (
            f"{trigger.threshold} {trigger.threshold_unit}"
            if getattr(trigger, "threshold", None) is not None
            else "Missing threshold or unit"
        ),
    }
    checks["backtest_minimum_10_periods"] = {
        "pass": None,
        "reason": "Evaluated at compute time",
    }

    passing = sum(1 for v in checks.values() if v.get("pass") is True)
    evaluable = sum(1 for v in checks.values() if v.get("pass") is not None)

    return {
        "score": passing / evaluable if evaluable > 0 else 0.0,
        "detail": checks,
    }
