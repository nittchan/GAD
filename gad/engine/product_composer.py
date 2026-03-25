"""
Multi-peril product composer — combine triggers into composite parametric products.

Supports AND/OR logic, live evaluation against cached data, and backtesting
against historical observations. This is the key differentiator vs Parametrix:
users can combine 2-3 perils into a single composite parametric product.

Examples:
  - "Airport Resilience Bundle": flight delay AND air quality (both must fire)
  - "Natural Catastrophe Cover": earthquake OR wildfire OR flood (any fires)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Literal

from gad.monitor.triggers import get_trigger_by_id, PERIL_LABELS, MonitorTrigger
from gad.monitor.cache import read_cache_with_staleness

log = logging.getLogger("gad.engine.product_composer")

# ── Source key mapping (mirrors monitor page) ──

SOURCE_KEY_MAP = {
    "openmeteo": "weather",
    "openaq": "aqi",
    "firms": "fire",
    "opensky": "flights",
    "chirps": "drought",
    "usgs": "earthquake",
    "aisstream": "marine",
    "usgs_water": "flood",
    "noaa_nhc": "cyclone",
    "ndvi": "ndvi",
    "noaa_swpc": "solar",
    "who_don": "health",
}


@dataclass
class CompositeProduct:
    """A multi-peril parametric product combining 2-3 triggers."""

    name: str
    triggers: list[str]  # trigger IDs
    logic: Literal["AND", "OR"]  # AND = all must fire, OR = any fires
    description: str = ""


@dataclass
class TriggerEvaluation:
    """Evaluation result for a single trigger within a composite product."""

    trigger_id: str
    trigger_name: str
    peril: str
    peril_label: str
    location: str
    fired: bool
    value: float | None = None
    threshold: float | None = None
    unit: str = ""
    status: str = "no_data"
    has_data: bool = False


@dataclass
class CompositeEvaluation:
    """Full evaluation result for a composite product."""

    product_name: str
    logic: Literal["AND", "OR"]
    fired: bool
    trigger_count: int
    triggers_fired: int
    trigger_details: list[TriggerEvaluation] = field(default_factory=list)
    perils_covered: list[str] = field(default_factory=list)


def _evaluate_single_trigger(trigger: MonitorTrigger, data: dict) -> dict:
    """Evaluate a single trigger against cached data. Returns status dict."""
    from gad.monitor.sources import (
        openmeteo, openaq, firms, opensky,
        chirps_monitor, usgs_earthquake, aisstream,
        noaa_flood, noaa_nhc, ndvi, noaa_swpc, who_don,
    )

    evaluators = {
        "openmeteo": lambda d, t: openmeteo.evaluate_trigger(d, t.threshold, t.threshold_unit, t.fires_when_above),
        "openaq": lambda d, t: openaq.evaluate_trigger(d, t.threshold),
        "firms": lambda d, t: firms.evaluate_trigger(d, t.threshold),
        "opensky": lambda d, t: opensky.evaluate_trigger(d, t.threshold),
        "chirps": lambda d, t: chirps_monitor.evaluate_trigger(d, t.threshold),
        "usgs": lambda d, t: usgs_earthquake.evaluate_trigger(d, t.threshold),
        "aisstream": lambda d, t: aisstream.evaluate_trigger(d, t.threshold, t.threshold_unit),
        "usgs_water": lambda d, t: noaa_flood.evaluate_trigger(d, t.threshold),
        "noaa_nhc": lambda d, t: noaa_nhc.evaluate_trigger(d, t.threshold),
        "ndvi": lambda d, t: ndvi.evaluate_trigger(d, t.threshold),
        "noaa_swpc": lambda d, t: noaa_swpc.evaluate_trigger(d, t.threshold),
        "who_don": lambda d, t: who_don.evaluate_trigger(d, t.threshold),
    }

    evaluator = evaluators.get(trigger.data_source)
    if evaluator:
        return evaluator(data, trigger)
    return {"fired": False, "value": None, "status": "no_data"}


def evaluate_composite(product: CompositeProduct) -> CompositeEvaluation:
    """
    Evaluate a composite product against current cached trigger data.

    Reads from cache only — no external API calls.
    """
    details: list[TriggerEvaluation] = []
    fired_flags: list[bool] = []
    perils_seen: set[str] = set()

    for tid in product.triggers:
        trigger = get_trigger_by_id(tid)
        if not trigger:
            log.warning("Trigger %s not found in registry", tid)
            details.append(TriggerEvaluation(
                trigger_id=tid,
                trigger_name=f"Unknown ({tid})",
                peril="unknown",
                peril_label="Unknown",
                location="",
                fired=False,
                status="not_found",
            ))
            fired_flags.append(False)
            continue

        perils_seen.add(trigger.peril)
        source_key = SOURCE_KEY_MAP.get(trigger.data_source, trigger.data_source)
        data, is_stale = read_cache_with_staleness(source_key, trigger.id)

        if data is not None:
            result = _evaluate_single_trigger(trigger, data)
            is_fired = result.get("status") == "critical"
            value = result.get("value")
            status = result.get("status", "no_data")
            if is_stale and status != "critical":
                status = "stale"
        else:
            is_fired = False
            value = None
            status = "no_data"

        details.append(TriggerEvaluation(
            trigger_id=tid,
            trigger_name=trigger.name,
            peril=trigger.peril,
            peril_label=PERIL_LABELS.get(trigger.peril, trigger.peril),
            location=trigger.location_label,
            fired=is_fired,
            value=value,
            threshold=trigger.threshold,
            unit=trigger.threshold_unit,
            status=status,
            has_data=data is not None,
        ))
        fired_flags.append(is_fired)

    # Apply composite logic
    if product.logic == "AND":
        composite_fired = all(fired_flags) if fired_flags else False
    else:  # OR
        composite_fired = any(fired_flags)

    return CompositeEvaluation(
        product_name=product.name,
        logic=product.logic,
        fired=composite_fired,
        trigger_count=len(product.triggers),
        triggers_fired=sum(fired_flags),
        trigger_details=details,
        perils_covered=sorted(perils_seen),
    )


def evaluate_composite_from_dict(
    trigger_ids: list[str],
    logic: str = "AND",
    name: str = "Composite Product",
) -> dict:
    """
    Convenience function for the API layer. Returns a plain dict.
    """
    product = CompositeProduct(
        name=name,
        triggers=trigger_ids,
        logic=logic.upper(),  # type: ignore[arg-type]
    )
    result = evaluate_composite(product)
    return {
        "product_name": result.product_name,
        "logic": result.logic,
        "fired": result.fired,
        "trigger_count": result.trigger_count,
        "triggers_fired": result.triggers_fired,
        "perils_covered": result.perils_covered,
        "trigger_details": [
            {
                "trigger_id": d.trigger_id,
                "trigger_name": d.trigger_name,
                "peril": d.peril,
                "peril_label": d.peril_label,
                "location": d.location,
                "fired": d.fired,
                "value": d.value,
                "threshold": d.threshold,
                "unit": d.unit,
                "status": d.status,
                "has_data": d.has_data,
            }
            for d in result.trigger_details
        ],
    }
