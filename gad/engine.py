from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from gad.models import (
    BacktestResult,
    BacktestRow,
    BasisRiskReport,
    ConfusionCounts,
    DataManifest,
    LloydCriterionResult,
    LloydsResult,
    SpearmanBlock,
    TriggerDef,
    TriggerKind,
)


def _aggregate_regional(df: pd.DataFrame, trigger: TriggerDef) -> pd.DataFrame:
    """Filter by bounding_box and aggregate to one row per period (spatial average)."""
    bbox = trigger.bounding_box
    if bbox is None or "lat" not in df.columns or "lon" not in df.columns:
        return df
    mask = (
        (df["lat"] >= bbox.min_lat)
        & (df["lat"] <= bbox.max_lat)
        & (df["lon"] >= bbox.min_lon)
        & (df["lon"] <= bbox.max_lon)
    )
    df = df.loc[mask]
    if df.empty:
        raise ValueError("No rows inside bounding box")
    agg = df.groupby("period", as_index=False).agg(
        index_value=("index_value", "mean"),
        spatial_ref=("spatial_ref", "mean"),
        loss_proxy=("loss_proxy", "mean"),
        loss_event=("loss_event", "max"),
    )
    return agg


def _fires(index: np.ndarray, kind: TriggerKind, threshold: float) -> np.ndarray:
    if kind is TriggerKind.threshold_above:
        return index > threshold
    return index < threshold


def _spearman_block(x: np.ndarray, y: np.ndarray, *, n_boot: int = 1000, seed: int = 42) -> SpearmanBlock:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    n = int(x.size)
    if n < 3:
        return SpearmanBlock(rho=float("nan"), ci_low=float("nan"), ci_high=float("nan"), p_value=1.0, n=n)
    rho, p = stats.spearmanr(x, y)
    rho_f = float(rho) if np.isfinite(rho) else float("nan")
    p_f = float(p) if np.isfinite(p) else 1.0
    rng = np.random.default_rng(seed)
    boot: list[float] = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        xs, ys = x[idx], y[idx]
        if np.unique(xs).size < 2 or np.unique(ys).size < 2:
            continue
        r, _ = stats.spearmanr(xs, ys)
        if np.isfinite(r):
            boot.append(float(r))
    if len(boot) < 50:
        ci_lo = ci_hi = rho_f
    else:
        ci_lo, ci_hi = np.percentile(boot, [2.5, 97.5]).astype(float).tolist()
    return SpearmanBlock(rho=rho_f, ci_low=float(ci_lo), ci_high=float(ci_hi), p_value=p_f, n=n)


def compute_basis_risk(
    trigger: TriggerDef,
    manifest: DataManifest,
    data_root: str | Path,
) -> BasisRiskReport:
    """
    Load series from manifest paths under data_root, run Spearman blocks, back-test, and Lloyd's checklist.
    """
    data_root = Path(data_root)
    if trigger.id not in manifest.triggers:
        raise KeyError(f"Trigger id {trigger.id!r} not found in data manifest")

    ref = manifest.triggers[trigger.id]
    primary_path = data_root / ref.primary_series_csv
    if not primary_path.is_file():
        raise FileNotFoundError(str(primary_path))

    df = pd.read_csv(primary_path)
    required = {"period", "index_value", "spatial_ref", "loss_event"}
    miss = required - set(df.columns)
    if miss:
        raise ValueError(f"Primary CSV {primary_path.name} missing columns: {sorted(miss)}")

    if ref.spatial_reference_csv:
        sp_path = data_root / ref.spatial_reference_csv
        if not sp_path.is_file():
            raise FileNotFoundError(str(sp_path))
        sdf = pd.read_csv(sp_path)
        if "period" not in sdf.columns or "spatial_ref" not in sdf.columns:
            raise ValueError("spatial_reference_csv must include period and spatial_ref")
        df = df.drop(columns=["spatial_ref"], errors="ignore").merge(
            sdf[["period", "spatial_ref"]], on="period", how="inner"
        )

    if "loss_proxy" not in df.columns:
        df = df.copy()
        df["loss_proxy"] = df["loss_event"].astype(float)

    df = _aggregate_regional(df, trigger)

    df = df.copy()
    df["pdate"] = pd.to_datetime(df["period"], errors="coerce")
    if df["pdate"].isna().any():
        bad = df.loc[df["pdate"].isna(), "period"].tolist()
        raise ValueError(f"Invalid period values: {bad[:5]!r}")

    start = pd.Timestamp(trigger.date_range.start)
    end = pd.Timestamp(trigger.date_range.end)
    df = df.loc[(df["pdate"] >= start) & (df["pdate"] <= end)].sort_values("pdate")
    if len(df) < 5:
        raise ValueError("Insufficient periods after date_range filter (need ≥5).")

    idx = df["index_value"].to_numpy(dtype=float)
    spatial = df["spatial_ref"].to_numpy(dtype=float)
    loss_event = df["loss_event"].to_numpy(dtype=int)
    loss_proxy = df["loss_proxy"].to_numpy(dtype=float)

    fired = _fires(idx, trigger.trigger_logic.kind, trigger.trigger_logic.threshold)

    tp = int(np.sum(fired & (loss_event == 1)))
    fp = int(np.sum(fired & (loss_event == 0)))
    fn = int(np.sum(~fired & (loss_event == 1)))
    tn = int(np.sum(~fired & (loss_event == 0)))

    zero_fires = bool(np.sum(fired) == 0)
    warnings: list[str] = []
    if zero_fires:
        warnings.append(
            "Trigger never fired in the historical window — adjust threshold or window; "
            "confusion-matrix payout metrics are degenerate."
        )

    spearman_spatial = _spearman_block(idx, spatial)
    spearman_loss_proxy: SpearmanBlock | None
    if np.nanstd(loss_proxy) < 1e-12:
        spearman_loss_proxy = None
    else:
        spearman_loss_proxy = _spearman_block(idx, loss_proxy)

    if spearman_loss_proxy is not None and np.isfinite(spearman_loss_proxy.rho):
        headline = spearman_loss_proxy
        headline_label = "loss_proxy"
    else:
        headline = spearman_spatial
        headline_label = "spatial_basis"

    rows: list[BacktestRow] = []
    for i in range(len(df)):
        rows.append(
            BacktestRow(
                period=str(df["period"].iloc[i]),
                index_value=float(idx[i]),
                spatial_ref=float(spatial[i]),
                trigger_fired=bool(fired[i]),
                loss_occurred=bool(int(loss_event[i]) == 1),
            )
        )

    backtest = BacktestResult(
        rows=rows,
        confusion=ConfusionCounts(
            true_positive=tp,
            false_positive=fp,
            false_negative=fn,
            true_negative=tn,
        ),
        zero_trigger_fires=zero_fires,
    )

    temp = BasisRiskReport(
        trigger_id=trigger.id,
        trigger_name=trigger.name,
        spearman_spatial=spearman_spatial,
        spearman_loss_proxy=spearman_loss_proxy,
        headline_rho=headline.rho,
        headline_ci_low=headline.ci_low,
        headline_ci_high=headline.ci_high,
        headline_p_value=headline.p_value,
        headline_label=headline_label,
        backtest=backtest,
        warnings=warnings,
        lloyds=LloydsResult(criteria=[], passed_count=0, total_count=0),
    )
    return temp.model_copy(update={"lloyds": lloyds_check(temp, trigger)})


def lloyds_check(report: BasisRiskReport, trigger: TriggerDef) -> LloydsResult:
    """
    Fixed Phase-1 Lloyd's-style checklist. Each criterion is explicit; score = passed / total.
    """
    criteria: list[LloydCriterionResult] = []

    def add(cid: str, name: str, passed: bool, explanation: str) -> None:
        criteria.append(
            LloydCriterionResult(criterion_id=cid, name=name, passed=passed, explanation=explanation)
        )

    add(
        "L1",
        "Objective index & threshold",
        bool(trigger.variable and np.isfinite(trigger.trigger_logic.threshold)),
        "Trigger references a defined hazard variable and numeric threshold.",
    )
    add(
        "L2",
        "Coverage location specified",
        True,
        f"Point location documented (lat={trigger.location.lat:.4f}, lon={trigger.location.lon:.4f}).",
    )
    add(
        "L3",
        "Payout mechanism described",
        len(trigger.payout_formula_summary.strip()) >= 8,
        "Non-trivial payout summary is present for audit.",
    )
    add(
        "L4",
        "Historical sample adequate",
        len(report.backtest.rows) >= 10,
        f"n={len(report.backtest.rows)} periods in window (target ≥10).",
    )
    add(
        "L5",
        "Basis risk quantified (Spearman)",
        np.isfinite(report.spearman_spatial.rho) and report.spearman_spatial.n >= 5,
        "Spatial basis Spearman computed on ≥5 paired observations.",
    )
    add(
        "L6",
        "Spatial basis materiality",
        np.isfinite(report.spearman_spatial.rho) and abs(report.spearman_spatial.rho) >= 0.15,
        "|ρ_spatial| ≥ 0.15 suggests measurable co-movement with regional reference.",
    )
    lp = report.spearman_loss_proxy
    if lp is None:
        loss_ok = True
        loss_expl = "loss_proxy constant in sample — alignment check not applicable."
    else:
        loss_ok = bool(np.isfinite(lp.rho))
        loss_expl = f"Loss-proxy Spearman ρ={lp.rho:.3f} (n={lp.n})."
    add(
        "L7",
        "Loss alignment assessed (when proxy varies)",
        loss_ok,
        loss_expl,
    )
    mat = np.isfinite(report.headline_rho) and abs(report.headline_rho) >= 0.4
    add(
        "L8",
        "Headline correlation materiality",
        mat,
        f"Headline Spearman ρ={report.headline_rho:.3f} (target |ρ|≥0.4 for 'pass').",
    )
    add(
        "L9",
        "Back-test not degenerate (fires)",
        not report.backtest.zero_trigger_fires,
        "At least one trigger fire in history (or explicit warning acknowledged in UI).",
    )
    add(
        "L10",
        "Reproducibility window bounded",
        trigger.date_range.start.year >= 1980 and trigger.date_range.end.year <= 2100,
        "Analysis window falls within documented bounds.",
    )

    passed = sum(1 for c in criteria if c.passed)
    return LloydsResult(criteria=criteria, passed_count=passed, total_count=len(criteria))
