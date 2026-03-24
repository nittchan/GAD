"""
Parametric Risk Exposure Index (PREI) per country.

PREI = (fired_triggers / total_triggers) * 100 + (near_threshold_triggers / total_triggers) * 30
Normalised to 0-100. Higher = more risk exposure.
"""

from __future__ import annotations

from gad.monitor.airports import ALL_AIRPORTS
from gad.monitor.triggers import GLOBAL_TRIGGERS


def _trigger_country(trigger_id: str) -> str | None:
    """Map a trigger to its country. Returns None for standalone triggers without a country."""
    # Airport-derived triggers: flight-delay-{iata}, weather-{type}-{iata}, aqi-{iata}
    parts = trigger_id.split("-")
    if len(parts) >= 2:
        iata = parts[-1].upper()
        for a in ALL_AIRPORTS:
            if a.iata == iata:
                return a.country
    return None


def compute_prei(trigger_results: dict) -> dict[str, dict]:
    """
    Compute PREI for each country from trigger evaluation results.

    Args:
        trigger_results: dict of trigger_id -> (trigger, data, result, is_stale)
                         as built by the Global Monitor page.

    Returns:
        dict of country -> {prei, total, fired, near_threshold, normal, no_data}
    """
    country_stats: dict[str, dict] = {}

    for tid, (trigger, data, result, is_stale) in trigger_results.items():
        country = _trigger_country(tid)
        if not country:
            continue

        if country not in country_stats:
            country_stats[country] = {
                "total": 0, "fired": 0, "near_threshold": 0,
                "normal": 0, "no_data": 0,
            }

        stats = country_stats[country]
        stats["total"] += 1

        status = result.get("status", "no_data")
        if status == "critical":
            stats["fired"] += 1
        elif status == "normal":
            # Check if value is near threshold (within 20%)
            value = result.get("value")
            threshold = trigger.threshold
            if value is not None and threshold != 0:
                if trigger.fires_when_above:
                    proximity = value / threshold if threshold > 0 else 0
                else:
                    proximity = threshold / value if value > 0 else 0
                if proximity >= 0.8:
                    stats["near_threshold"] += 1
                else:
                    stats["normal"] += 1
            else:
                stats["normal"] += 1
        else:
            stats["no_data"] += 1

    # Compute PREI score
    result = {}
    for country, stats in country_stats.items():
        total = stats["total"]
        if total == 0:
            continue
        prei = (stats["fired"] / total) * 100 + (stats["near_threshold"] / total) * 30
        prei = min(100, round(prei, 1))
        result[country] = {**stats, "prei": prei}

    return result
