"""
Basis risk computation: Spearman, bootstrap CI, confusion matrix, Lloyd's.
Functional: same inputs always produce same output.
"""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
from scipy import stats

from gad.engine.lloyds import lloyds_check
from gad.engine.models import BacktestRow, BasisRiskReport, TriggerDef
from gad.engine.version import get_gad_version


def _bootstrap_spearman_ci(
    x: list[float],
    y: list[float],
    *,
    n_boot: int = 1000,
    seed: int = 42,
) -> tuple[float, float]:
    xa = np.asarray(x, dtype=float)
    ya = np.asarray(y, dtype=float)
    mask = np.isfinite(xa) & np.isfinite(ya)
    xa, ya = xa[mask], ya[mask]
    n = int(xa.size)
    if n < 3:
        return (float("nan"), float("nan"))
    rho, _ = stats.spearmanr(xa, ya)
    rho_f = float(rho) if np.isfinite(rho) else float("nan")
    rng = np.random.default_rng(seed)
    boot: list[float] = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        xs, ys = xa[idx], ya[idx]
        if np.unique(xs).size < 2 or np.unique(ys).size < 2:
            continue
        r, _ = stats.spearmanr(xs, ys)
        if np.isfinite(r):
            boot.append(float(r))
    if len(boot) < 50:
        return (rho_f, rho_f)
    lo, hi = np.percentile(boot, [2.5, 97.5]).astype(float).tolist()
    return (lo, hi)


def compute_basis_risk(
    trigger: TriggerDef,
    weather_data: list[dict],
) -> BasisRiskReport:
    """
    Functional. No side effects. Same inputs always produce same output.
    weather_data must have >= 10 periods or raises ValueError.
    Each dict: period (datetime or str), trigger_value (float), loss_proxy (float).
    """
    if len(weather_data) < 10:
        raise ValueError(
            f"Insufficient data: need >= 10 periods, got {len(weather_data)}"
        )

    trigger_vals = [d["trigger_value"] for d in weather_data]
    loss_vals = [d["loss_proxy"] for d in weather_data]

    rho, p_value = stats.spearmanr(trigger_vals, loss_vals)
    rho_f = float(rho) if np.isfinite(rho) else float("nan")
    p_f = float(p_value) if np.isfinite(p_value) else 1.0

    ci_lower, ci_upper = _bootstrap_spearman_ci(trigger_vals, loss_vals)

    above = getattr(trigger, "trigger_fires_when_above", True)
    tp = fp = fn = tn = 0
    rows = []
    for d in weather_data:
        tv = d["trigger_value"]
        triggered = (tv >= trigger.threshold) if above else (tv <= trigger.threshold)
        loss_occurred = d["loss_proxy"] > 0
        rows.append(
            {
                "period": str(d.get("period", "")),
                "trigger_value": tv,
                "trigger_fired": triggered,
                "loss_occurred": loss_occurred,
            }
        )
        if triggered and loss_occurred:
            tp += 1
        elif triggered and not loss_occurred:
            fp += 1
        elif not triggered and loss_occurred:
            fn += 1
        else:
            tn += 1

    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0

    period_keys = [d.get("period") for d in weather_data]
    if period_keys and period_keys[0] is not None:
        try:
            if isinstance(period_keys[0], str):
                start = datetime.fromisoformat(
                    str(period_keys[0]).replace("Z", "+00:00")
                )
                end = datetime.fromisoformat(
                    str(period_keys[-1]).replace("Z", "+00:00")
                )
            else:
                start = period_keys[0]
                end = period_keys[-1]
        except Exception:
            start = datetime.now(timezone.utc)
            end = datetime.now(timezone.utc)
    else:
        start = datetime.now(timezone.utc)
        end = datetime.now(timezone.utc)

    lloyds = lloyds_check(trigger, rho_f, fpr, fnr)

    return BasisRiskReport(
        trigger_id=trigger.trigger_id,
        spearman_rho=rho_f,
        spearman_ci_lower=ci_lower,
        spearman_ci_upper=ci_upper,
        p_value=p_f,
        false_positive_rate=fpr,
        false_negative_rate=fnr,
        backtest_periods=len(weather_data),
        backtest_start=start,
        backtest_end_inclusive=end,
        lloyds_score=lloyds["score"],
        lloyds_detail=lloyds["detail"],
        independent_verifiable=bool(trigger.provenance),
        backtest_rows=[BacktestRow(**r) for r in rows],
        gad_version=get_gad_version(),
    )
