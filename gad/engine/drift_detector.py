"""
SL-03a: Drift detector — detects statistical drift in trigger observations.

Compares a recent 30-day window against the prior 60-day window to identify
three types of drift:
  - Mean shift: recent mean differs from prior mean by >1.5 standard deviations
  - Firing rate change: absolute difference >3 percentage points
  - Variance change: recent std / prior std > 1.5 or < 0.67
"""

from __future__ import annotations

import logging

import numpy as np

from gad.engine.db_read import get_observations
from gad.engine.db_write import write_drift_alert

log = logging.getLogger("gad.engine.drift_detector")

# Minimum observations per window to run drift detection
MIN_OBSERVATIONS = 10


def detect_drift(trigger_id: str) -> list[dict]:
    """
    Detect drift by comparing recent 30d window vs prior 60d window.

    Parameters
    ----------
    trigger_id : str
        Registry trigger ID.

    Returns
    -------
    list[dict]
        List of drift alerts (may be empty). Each dict has:
        drift_type, old_value, new_value, severity.
    """
    # Get 90 days of observations (recent 30d + prior 60d)
    df = get_observations(trigger_id, days=90)
    if df is None or len(df) < MIN_OBSERVATIONS * 2:
        return []

    # Sort by observed_at ascending
    df = df.sort_values("observed_at")

    # Split into recent 30d and prior 60d based on row position
    # Find the cutoff: rows in last 30 days vs rows before that
    from datetime import datetime, timedelta, timezone
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)

    # Handle timezone-aware vs naive timestamps
    observed_col = df["observed_at"]
    try:
        recent = df[observed_col >= cutoff]
        prior = df[observed_col < cutoff]
    except TypeError:
        # If timestamps are naive, compare without timezone
        cutoff_naive = cutoff.replace(tzinfo=None)
        recent = df[observed_col >= cutoff_naive]
        prior = df[observed_col < cutoff_naive]

    if len(recent) < MIN_OBSERVATIONS or len(prior) < MIN_OBSERVATIONS:
        return []

    recent_values = recent["value"].dropna().to_numpy(dtype=float)
    prior_values = prior["value"].dropna().to_numpy(dtype=float)

    if len(recent_values) < MIN_OBSERVATIONS or len(prior_values) < MIN_OBSERVATIONS:
        return []

    alerts: list[dict] = []

    recent_mean = float(np.mean(recent_values))
    prior_mean = float(np.mean(prior_values))
    prior_std = float(np.std(prior_values, ddof=1)) if len(prior_values) > 1 else 0.0
    recent_std = float(np.std(recent_values, ddof=1)) if len(recent_values) > 1 else 0.0

    # ── Mean shift detection ──
    if prior_std > 0 and abs(recent_mean - prior_mean) > 1.5 * prior_std:
        alert = {
            "drift_type": "mean_shift",
            "old_value": round(prior_mean, 4),
            "new_value": round(recent_mean, 4),
            "severity": "high" if abs(recent_mean - prior_mean) > 2.5 * prior_std else "medium",
        }
        alerts.append(alert)
        write_drift_alert(trigger_id, alert["drift_type"], alert["old_value"], alert["new_value"], alert["severity"])

    # ── Firing rate change detection ──
    recent_fired = float(recent["fired"].sum()) if "fired" in recent.columns else 0
    prior_fired = float(prior["fired"].sum()) if "fired" in prior.columns else 0
    recent_rate = recent_fired / len(recent) if len(recent) > 0 else 0
    prior_rate = prior_fired / len(prior) if len(prior) > 0 else 0

    if abs(recent_rate - prior_rate) > 0.03:  # 3 percentage points
        alert = {
            "drift_type": "firing_rate_change",
            "old_value": round(prior_rate, 4),
            "new_value": round(recent_rate, 4),
            "severity": "high" if abs(recent_rate - prior_rate) > 0.10 else "medium",
        }
        alerts.append(alert)
        write_drift_alert(trigger_id, alert["drift_type"], alert["old_value"], alert["new_value"], alert["severity"])

    # ── Variance change detection ──
    if prior_std > 0 and recent_std > 0:
        variance_ratio = recent_std / prior_std
        if variance_ratio > 1.5 or variance_ratio < 0.67:
            alert = {
                "drift_type": "variance_change",
                "old_value": round(prior_std, 4),
                "new_value": round(recent_std, 4),
                "severity": "high" if variance_ratio > 2.0 or variance_ratio < 0.5 else "medium",
            }
            alerts.append(alert)
            write_drift_alert(trigger_id, alert["drift_type"], alert["old_value"], alert["new_value"], alert["severity"])

    if alerts:
        log.info(f"Drift detected for {trigger_id}: {[a['drift_type'] for a in alerts]}")

    return alerts


def detect_all_drift() -> dict:
    """
    Run drift detection for all triggers in the global registry.

    Returns
    -------
    dict
        Summary: {"triggers_checked": int, "alerts_raised": int, "errors": int}
    """
    from gad.monitor.triggers import GLOBAL_TRIGGERS

    triggers_checked = 0
    alerts_raised = 0
    errors = 0

    for trigger in GLOBAL_TRIGGERS:
        try:
            alerts = detect_drift(trigger.id)
            triggers_checked += 1
            alerts_raised += len(alerts)
        except Exception as e:
            errors += 1
            log.warning(f"Drift detection failed for {trigger.id}: {e}")

    log.info(
        f"Drift detector: {triggers_checked} triggers checked, "
        f"{alerts_raised} alerts raised, {errors} errors"
    )
    return {
        "triggers_checked": triggers_checked,
        "alerts_raised": alerts_raised,
        "errors": errors,
    }
