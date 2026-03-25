"""
Co-firing correlation matrix using phi coefficient.
Geographic bounding: only compute for pairs within 2000km (eng review).
Weekly recompute.
"""
import logging
import math

import numpy as np

from gad.engine.db_read import get_observations
from gad.engine.db_write import write_correlation
from gad.engine.model_registry import register_model_version
from gad.monitor.triggers import GLOBAL_TRIGGERS

log = logging.getLogger("gad.engine.correlation_matrix")


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points in km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _phi_coefficient(fired_a: list[bool], fired_b: list[bool]) -> float | None:
    """Compute phi coefficient between two boolean arrays.

    Returns None if fewer than 10 observations overlap.
    """
    n = len(fired_a)
    if n < 10:
        return None
    a = np.array(fired_a, dtype=bool)
    b = np.array(fired_b, dtype=bool)
    n11 = int(np.sum(a & b))
    n10 = int(np.sum(a & ~b))
    n01 = int(np.sum(~a & b))
    n00 = int(np.sum(~a & ~b))
    denom = math.sqrt((n11 + n10) * (n01 + n00) * (n11 + n01) * (n10 + n00))
    if denom == 0:
        return 0.0
    return float((n11 * n00 - n10 * n01) / denom)


def compute_correlations(
    max_distance_km: int = 2000, min_overlap: int = 100
) -> list[dict]:
    """Compute phi coefficient for all trigger pairs within distance threshold.

    Parameters
    ----------
    max_distance_km : int
        Geographic bounding — only pairs within this radius are evaluated.
    min_overlap : int
        Minimum number of overlapping daily observations required.

    Returns
    -------
    list[dict]
        Significant correlations with trigger_a, trigger_b, phi, overlap.
    """
    # Build fired arrays for each trigger
    trigger_data: dict[str, dict] = {}
    for t in GLOBAL_TRIGGERS:
        try:
            df = get_observations(t.id, days=365)
            if df is not None and len(df) >= min_overlap:
                # Daily fired status
                df["date"] = df["observed_at"].dt.date
                daily = df.groupby("date")["fired"].any().reset_index()
                trigger_data[t.id] = {
                    "trigger": t,
                    "dates": dict(zip(daily["date"], daily["fired"])),
                }
        except Exception:
            continue

    trigger_ids = list(trigger_data.keys())
    results: list[dict] = []

    for i, id_a in enumerate(trigger_ids):
        ta = trigger_data[id_a]
        for id_b in trigger_ids[i + 1 :]:
            tb = trigger_data[id_b]

            # Geographic bounding
            dist = _haversine_km(
                ta["trigger"].lat,
                ta["trigger"].lon,
                tb["trigger"].lat,
                tb["trigger"].lon,
            )
            if dist > max_distance_km:
                continue

            # Find overlapping dates
            common_dates = set(ta["dates"].keys()) & set(tb["dates"].keys())
            if len(common_dates) < min_overlap:
                continue

            sorted_dates = sorted(common_dates)
            fired_a = [ta["dates"][d] for d in sorted_dates]
            fired_b = [tb["dates"][d] for d in sorted_dates]

            phi = _phi_coefficient(fired_a, fired_b)
            if phi is not None and abs(phi) > 0.1:
                write_correlation(id_a, id_b, phi, len(common_dates))
                results.append(
                    {
                        "trigger_a": id_a,
                        "trigger_b": id_b,
                        "phi": round(phi, 4),
                        "overlap": len(common_dates),
                    }
                )

    log.info(
        f"Correlation matrix: {len(results)} significant pairs "
        f"from {len(trigger_ids)} triggers"
    )
    register_model_version(
        None,
        "correlation_matrix",
        {"max_distance_km": max_distance_km, "min_overlap": min_overlap},
        {"pairs_found": len(results)},
    )
    return results


# ── SL-07d: Lead-lag analysis ──


def find_lead_lag(
    trigger_a: str, trigger_b: str, max_lag_days: int = 7
) -> dict | None:
    """Check if one trigger leads the other by 1-7 days.

    Shifts the fired array of trigger_b by 1..max_lag_days and recomputes phi
    at each lag.  Returns the lag with the highest absolute phi, or None if
    no observations are available.

    Parameters
    ----------
    trigger_a : str
        Trigger ID for the first trigger.
    trigger_b : str
        Trigger ID for the second trigger.
    max_lag_days : int
        Maximum lag to test (default 7).

    Returns
    -------
    dict | None
        ``{"best_lag": int, "phi_at_lag": float, "direction": str}``
        where direction is "a_leads_b" (positive lag) or "b_leads_a" (negative lag)
        or "simultaneous" (lag 0). Returns None if insufficient data.
    """
    from datetime import timedelta

    try:
        df_a = get_observations(trigger_a, days=365)
        df_b = get_observations(trigger_b, days=365)
        if df_a is None or df_b is None or len(df_a) < 30 or len(df_b) < 30:
            return None
    except Exception:
        return None

    # Build daily fired maps
    df_a["date"] = df_a["observed_at"].dt.date
    df_b["date"] = df_b["observed_at"].dt.date
    daily_a = dict(
        zip(
            df_a.groupby("date")["fired"].any().reset_index()["date"],
            df_a.groupby("date")["fired"].any().reset_index()["fired"],
        )
    )
    daily_b = dict(
        zip(
            df_b.groupby("date")["fired"].any().reset_index()["date"],
            df_b.groupby("date")["fired"].any().reset_index()["fired"],
        )
    )

    best_lag = 0
    best_phi = 0.0

    for lag in range(-max_lag_days, max_lag_days + 1):
        # For positive lag: shift b forward (a leads b)
        # For negative lag: shift b backward (b leads a)
        common = set(daily_a.keys()) & {
            d + timedelta(days=lag) for d in daily_b.keys()
        }
        if len(common) < 30:
            continue

        sorted_dates = sorted(common)
        fa = [daily_a[d] for d in sorted_dates]
        fb = [daily_b.get(d - timedelta(days=lag), False) for d in sorted_dates]

        phi = _phi_coefficient(fa, fb)
        if phi is not None and abs(phi) > abs(best_phi):
            best_phi = phi
            best_lag = lag

    if abs(best_phi) < 0.05:
        return None

    if best_lag > 0:
        direction = "a_leads_b"
    elif best_lag < 0:
        direction = "b_leads_a"
    else:
        direction = "simultaneous"

    return {
        "best_lag": best_lag,
        "phi_at_lag": round(best_phi, 4),
        "direction": direction,
    }
