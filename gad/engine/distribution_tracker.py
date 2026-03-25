"""
SL-02a: Distribution tracker — computes statistical distributions for triggers.

Reads observations from DuckDB, computes summary statistics (mean, std,
median, percentiles, firing rate), and writes results back to DuckDB.
Registers each computation as a model version for audit trail.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import numpy as np

from gad.engine.db_read import get_observations
from gad.engine.db_write import write_distribution
from gad.engine.model_registry import register_model_version

log = logging.getLogger("gad.engine.distribution_tracker")

# Minimum observations required to compute a distribution
MIN_OBSERVATIONS = 10

# Supported time windows mapped to days
_WINDOW_DAYS = {
    "90d": 90,
    "365d": 365,
}


def compute_distribution(trigger_id: str, time_window: str = "90d") -> dict | None:
    """
    Compute distribution statistics for a trigger over a time window.

    Parameters
    ----------
    trigger_id : str
        Registry trigger ID (e.g. "flight-delay-del").
    time_window : str
        One of "90d" (90 days) or "365d" (1 year).

    Returns
    -------
    dict or None
        Distribution summary dict, or None if insufficient data.
    """
    days = _WINDOW_DAYS.get(time_window)
    if days is None:
        log.warning(f"Unsupported time_window '{time_window}' for {trigger_id}")
        return None

    df = get_observations(trigger_id, days=days)
    if df is None or len(df) < MIN_OBSERVATIONS:
        log.debug(
            f"Insufficient observations for {trigger_id} ({time_window}): "
            f"{0 if df is None else len(df)} < {MIN_OBSERVATIONS}"
        )
        return None

    values = df["value"].dropna()
    if len(values) < MIN_OBSERVATIONS:
        log.debug(f"Insufficient non-null values for {trigger_id} ({time_window})")
        return None

    arr = values.to_numpy(dtype=float)
    fired_count = int(df["fired"].sum()) if "fired" in df.columns else 0
    total_count = len(df)

    result = {
        "trigger_id": trigger_id,
        "time_window": time_window,
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0,
        "median": float(np.median(arr)),
        "p5": float(np.percentile(arr, 5)),
        "p25": float(np.percentile(arr, 25)),
        "p75": float(np.percentile(arr, 75)),
        "p95": float(np.percentile(arr, 95)),
        "firing_rate": float(fired_count / total_count) if total_count > 0 else 0.0,
        "observation_count": total_count,
    }

    # Write to DuckDB
    write_distribution(
        trigger_id=trigger_id,
        time_window=time_window,
        mean=result["mean"],
        std=result["std"],
        median=result["median"],
        p5=result["p5"],
        p25=result["p25"],
        p75=result["p75"],
        p95=result["p95"],
        firing_rate=result["firing_rate"],
        observation_count=result["observation_count"],
    )

    # Register model version for audit trail
    try:
        register_model_version(
            trigger_id=trigger_id,
            model_type="distribution",
            parameters={"time_window": time_window, "min_observations": MIN_OBSERVATIONS},
            metrics=result,
        )
    except Exception as e:
        log.debug(f"Model version registration skipped for {trigger_id}: {e}")

    return result


def compute_all_distributions() -> dict:
    """
    Compute 90d + 365d distributions for all triggers in the global registry.

    Returns
    -------
    dict
        Summary: {"computed": int, "skipped": int, "errors": int}
    """
    from gad.monitor.triggers import GLOBAL_TRIGGERS

    computed = 0
    skipped = 0
    errors = 0

    for trigger in GLOBAL_TRIGGERS:
        for window in ("90d", "365d"):
            try:
                result = compute_distribution(trigger.id, window)
                if result is not None:
                    computed += 1
                else:
                    skipped += 1
            except Exception as e:
                errors += 1
                log.warning(f"Distribution computation failed for {trigger.id} ({window}): {e}")

    log.info(f"Distribution tracker: {computed} computed, {skipped} skipped, {errors} errors")
    return {"computed": computed, "skipped": skipped, "errors": errors}
