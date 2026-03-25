"""
Threshold optimizer: finds optimal trigger thresholds using two objectives:
1. Frequency matching — target a specific annual firing rate (e.g. 5%)
2. Distributional separability — maximize KS statistic between fired/not-fired distributions
"""
import logging

import numpy as np
from scipy import stats as scipy_stats

from gad.engine.db_read import get_observations
from gad.engine.db_write import write_threshold_suggestion
from gad.engine.model_registry import register_model_version

log = logging.getLogger("gad.engine.threshold_optimizer")


def optimize_threshold(
    trigger_id: str,
    current_threshold: float,
    fires_when_above: bool = True,
    target_firing_rate: float = 0.05,
) -> dict | None:
    """
    Compute an optimal threshold for a trigger based on historical observations.

    Returns dict with: suggested_threshold, method, confidence, observation_count, metrics
    or None if insufficient data.
    """
    df = get_observations(trigger_id, days=365)
    if df is None or len(df) < 30:
        return None

    values = df["value"].dropna().values
    if len(values) < 30:
        return None

    # Method 1: Frequency matching — find threshold that gives target_firing_rate
    sorted_vals = np.sort(values)
    if fires_when_above:
        # threshold at (1 - target_firing_rate) percentile
        freq_threshold = float(
            np.percentile(sorted_vals, (1 - target_firing_rate) * 100)
        )
    else:
        freq_threshold = float(
            np.percentile(sorted_vals, target_firing_rate * 100)
        )

    # Method 2: KS separability — find threshold that maximizes KS statistic
    # between values above and below threshold
    best_ks = 0.0
    ks_threshold = freq_threshold
    candidates = np.percentile(sorted_vals, np.arange(10, 91, 5))
    for candidate in candidates:
        if fires_when_above:
            above = values[values >= candidate]
            below = values[values < candidate]
        else:
            above = values[values <= candidate]
            below = values[values > candidate]
        if len(above) >= 5 and len(below) >= 5:
            ks_stat, _ = scipy_stats.ks_2samp(above, below)
            if ks_stat > best_ks:
                best_ks = ks_stat
                ks_threshold = float(candidate)

    # Combine: weighted average (frequency matching 60%, KS 40%)
    suggested = freq_threshold * 0.6 + ks_threshold * 0.4

    # Evidence gating (SL-04b)
    n = len(values)
    if n < 30:
        confidence = None
    elif n < 100:
        confidence = "low"
    elif n < 500:
        confidence = "medium"
    else:
        confidence = "high"

    # Write to DuckDB
    write_threshold_suggestion(
        trigger_id, current_threshold, suggested,
        "frequency_ks_combined", confidence, n,
    )

    # Register model version
    register_model_version(
        trigger_id,
        "threshold_optimizer",
        {
            "method": "frequency_ks_combined",
            "target_firing_rate": target_firing_rate,
        },
        {
            "suggested": suggested,
            "freq_threshold": freq_threshold,
            "ks_threshold": ks_threshold,
            "ks_stat": best_ks,
            "n": n,
        },
    )

    return {
        "trigger_id": trigger_id,
        "current_threshold": current_threshold,
        "suggested_threshold": round(suggested, 4),
        "freq_threshold": round(freq_threshold, 4),
        "ks_threshold": round(ks_threshold, 4),
        "ks_statistic": round(best_ks, 4),
        "method": "frequency_ks_combined",
        "confidence": confidence,
        "observation_count": n,
    }


def optimize_all_thresholds() -> list[dict]:
    """Run threshold optimization for all triggers with sufficient data."""
    from gad.monitor.triggers import GLOBAL_TRIGGERS

    results = []
    for t in GLOBAL_TRIGGERS:
        try:
            result = optimize_threshold(t.id, t.threshold, t.fires_when_above)
            if result:
                results.append(result)
        except Exception as e:
            log.debug(f"Threshold optimization skipped for {t.id}: {e}")
    log.info(f"Threshold optimization: {len(results)} triggers optimized")
    return results
