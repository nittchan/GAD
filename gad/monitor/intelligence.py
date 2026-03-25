"""
AI risk brief generator for parametric insurance triggers.

Generates plain-English risk briefs per trigger using the Anthropic API,
with template-based fallback when the API key is missing or calls fail.

Also produces a daily global digest summarising fired, approaching, and
elevated-peril triggers.
"""

from __future__ import annotations

import json
import os
import time
from datetime import date, datetime, timezone
from typing import Optional

from gad.config import INTELLIGENCE_CACHE_DIR, DIGEST_DIR

# Peril labels (duplicated from triggers to avoid circular import)
_PERIL_DISPLAY = {
    "flight_delay": "Flight Delay",
    "air_quality": "Air Quality",
    "wildfire": "Wildfire",
    "drought": "Drought",
    "extreme_weather": "Extreme Weather",
    "earthquake": "Earthquake",
    "marine": "Marine / Shipping",
    "flood": "Flood",
    "cyclone": "Cyclone",
    "crop": "Crop / NDVI",
}

# ── System prompt for the LLM ──────────────────────────────────────────────

_SYSTEM_PROMPT = (
    "You are an actuarial intelligence analyst for a parametric insurance platform. "
    "Your job is to write concise, plain-English risk briefs for parametric insurance "
    "triggers. Each brief should be 2-3 sentences explaining what the trigger monitors, "
    "its current status relative to threshold, and the practical risk implication for "
    "an insurance underwriter or portfolio manager. Use precise language. "
    "Do not use bullet points or markdown formatting — just plain sentences. "
    "Do not start with 'This trigger' — vary your opening."
)


# ── Template-based fallback ────────────────────────────────────────────────

def _template_brief(
    trigger_name: str,
    peril: str,
    current_status: str,
    threshold: float,
    value: Optional[float],
    rho: Optional[float],
) -> str:
    """Generate a deterministic template brief when the API is unavailable."""
    peril_label = _PERIL_DISPLAY.get(peril, peril)
    direction = "above" if current_status == "critical" else "below"

    if current_status == "critical":
        status_text = (
            f"{trigger_name} is currently in TRIGGERED state — "
            f"the observed value ({value}) has crossed the {threshold} threshold. "
            f"Immediate settlement evaluation is warranted for {peril_label.lower()} exposure at this location."
        )
    elif current_status == "normal":
        status_text = (
            f"{trigger_name} is operating within normal parameters. "
            f"Current value ({value}) remains {direction} the {threshold} threshold. "
            f"No {peril_label.lower()} settlement action required at this time."
        )
    else:
        status_text = (
            f"{trigger_name} monitors {peril_label.lower()} risk. "
            f"Data is currently unavailable or stale — threshold is set at {threshold}. "
            f"Monitor status should be verified before underwriting decisions."
        )

    if rho is not None:
        status_text += f" Basis risk correlation (Spearman rho) is {rho:.3f}."

    return status_text


# ── Cache helpers ──────────────────────────────────────────────────────────

def _cache_path(trigger_id: str, for_date: date) -> Path:
    return INTELLIGENCE_CACHE_DIR / f"{trigger_id}_{for_date.isoformat()}.txt"


def _read_cache(trigger_id: str, for_date: date) -> Optional[str]:
    p = _cache_path(trigger_id, for_date)
    if p.is_file():
        return p.read_text(encoding="utf-8")
    return None


def _write_cache(trigger_id: str, for_date: date, brief: str) -> None:
    INTELLIGENCE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _cache_path(trigger_id, for_date).write_text(brief, encoding="utf-8")


# ── Main API ───────────────────────────────────────────────────────────────

def generate_trigger_brief(
    trigger_id: str,
    trigger_name: str,
    peril: str,
    current_status: str,
    threshold: float,
    value: Optional[float],
    rho: Optional[float] = None,
) -> str:
    """
    Generate a 2-3 sentence AI risk brief for a trigger.

    Uses Anthropic API (claude-sonnet-4-6) when ANTHROPIC_API_KEY is set.
    Falls back to template-based brief on missing key or API failure.
    Results are cached per trigger per day.

    Parameters
    ----------
    trigger_id : str
        Registry trigger ID (e.g. "flight-delay-blr").
    trigger_name : str
        Human-readable name (e.g. "Bangalore BLR").
    peril : str
        Peril type key (e.g. "flight_delay").
    current_status : str
        One of "critical", "normal", "stale", "no_data".
    threshold : float
        Trigger threshold value.
    value : float or None
        Current observed value.
    rho : float or None
        Spearman rho from basis risk analysis, if available.

    Returns
    -------
    str
        Plain-English risk brief (2-3 sentences).
    """
    today = date.today()

    # Check cache first
    cached = _read_cache(trigger_id, today)
    if cached:
        return cached

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        brief = _template_brief(trigger_name, peril, current_status, threshold, value, rho)
        _write_cache(trigger_id, today, brief)
        return brief

    # Build the user prompt
    peril_label = _PERIL_DISPLAY.get(peril, peril)
    rho_info = f"  Spearman rho (basis risk): {rho:.3f}" if rho is not None else ""
    user_prompt = (
        f"Write a 2-3 sentence risk brief for this parametric insurance trigger:\n"
        f"  Trigger: {trigger_name}\n"
        f"  Peril: {peril_label}\n"
        f"  Status: {current_status}\n"
        f"  Threshold: {threshold}\n"
        f"  Current value: {value}\n"
        f"{rho_info}\n"
    )

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=256,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        brief = message.content[0].text.strip()
    except Exception:
        brief = _template_brief(trigger_name, peril, current_status, threshold, value, rho)

    _write_cache(trigger_id, today, brief)
    return brief


# ── Global digest ──────────────────────────────────────────────────────────

def generate_global_digest() -> str:
    """
    Produce a markdown digest summarising the current global risk state.

    Covers:
    - Triggers fired (critical) in the last 24h
    - Triggers approaching threshold (value within 20% of threshold)
    - Perils with elevated activity

    Saves to data/digest/YYYY-MM-DD.md and returns the markdown string.
    """
    from gad.monitor.triggers import GLOBAL_TRIGGERS, PERIL_LABELS
    from gad.monitor.cache import read_cache_with_staleness
    from gad.monitor.sources import (
        openmeteo, openaq, firms, opensky, chirps_monitor,
        usgs_earthquake, aisstream, noaa_flood, noaa_nhc, ndvi,
    )

    _SOURCE_KEY_MAP = {
        "openmeteo": "weather", "openaq": "aqi", "firms": "fire",
        "opensky": "flights", "chirps": "drought", "usgs": "earthquake",
        "aisstream": "marine", "usgs_water": "flood",
        "noaa_nhc": "cyclone", "ndvi": "ndvi",
    }

    _EVALUATORS = {
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
    }

    fired: list[dict] = []
    approaching: list[dict] = []
    peril_counts: dict[str, int] = {}

    for trigger in GLOBAL_TRIGGERS:
        source_key = _SOURCE_KEY_MAP.get(trigger.data_source, trigger.data_source)
        data, _ = read_cache_with_staleness(source_key, trigger.id)
        if data is None:
            continue

        evaluator = _EVALUATORS.get(trigger.data_source)
        if not evaluator:
            continue

        try:
            result = evaluator(data, trigger)
        except Exception:
            continue

        status = result.get("status", "no_data")
        value = result.get("value")

        if status == "critical":
            fired.append({
                "id": trigger.id,
                "name": trigger.name,
                "peril": trigger.peril,
                "value": value,
                "threshold": trigger.threshold,
            })
            peril_counts[trigger.peril] = peril_counts.get(trigger.peril, 0) + 1

        elif value is not None and trigger.threshold != 0:
            ratio = abs(value / trigger.threshold) if trigger.threshold else 0
            if trigger.fires_when_above and 0.8 <= ratio <= 1.0:
                approaching.append({
                    "id": trigger.id,
                    "name": trigger.name,
                    "peril": trigger.peril,
                    "value": value,
                    "threshold": trigger.threshold,
                    "ratio": ratio,
                })
            elif not trigger.fires_when_above and 1.0 <= ratio <= 1.2:
                approaching.append({
                    "id": trigger.id,
                    "name": trigger.name,
                    "peril": trigger.peril,
                    "value": value,
                    "threshold": trigger.threshold,
                    "ratio": ratio,
                })

    # Sort approaching by proximity
    approaching.sort(key=lambda x: abs(1 - x.get("ratio", 0)))

    today = date.today()
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        f"# Parametric Data — Daily Digest",
        f"**{today.isoformat()}** | Generated {now_utc}",
        "",
        "---",
        "",
        f"## Triggers Fired ({len(fired)})",
        "",
    ]

    if fired:
        for t in fired:
            peril_label = PERIL_LABELS.get(t["peril"], t["peril"])
            lines.append(
                f"- **{t['name']}** ({peril_label}) — "
                f"value {t['value']} crossed threshold {t['threshold']}"
            )
    else:
        lines.append("No triggers currently in fired state.")

    lines += [
        "",
        f"## Approaching Threshold ({len(approaching)})",
        "",
    ]

    if approaching:
        for t in approaching[:20]:  # cap at 20
            peril_label = PERIL_LABELS.get(t["peril"], t["peril"])
            pct = abs(1 - t.get("ratio", 0)) * 100
            lines.append(
                f"- **{t['name']}** ({peril_label}) — "
                f"value {t['value']} is {pct:.0f}% from threshold {t['threshold']}"
            )
    else:
        lines.append("No triggers currently approaching threshold.")

    lines += [
        "",
        "## Elevated Perils",
        "",
    ]

    if peril_counts:
        for peril, count in sorted(peril_counts.items(), key=lambda x: -x[1]):
            peril_label = PERIL_LABELS.get(peril, peril)
            lines.append(f"- **{peril_label}**: {count} trigger(s) fired")
    else:
        lines.append("No perils showing elevated activity.")

    # SL-03c: Drift alerts section
    lines += ["", "## Drift Alerts", ""]
    try:
        from gad.engine.db_read import get_drift_alerts
        from gad.monitor.triggers import get_trigger_by_id

        _DRIFT_LABELS = {
            "mean_shift": "Mean Shift",
            "firing_rate_change": "Firing Rate Change",
            "variance_change": "Variance Change",
        }

        drift_items = []
        for trigger in GLOBAL_TRIGGERS:
            try:
                df = get_drift_alerts(trigger.id, days=1)
                if df is not None and not df.empty:
                    for _, row in df.iterrows():
                        drift_items.append({
                            "name": trigger.name,
                            "drift_type": row.get("drift_type", "unknown"),
                            "old_value": row.get("old_value"),
                            "new_value": row.get("new_value"),
                        })
            except Exception:
                continue

        if drift_items:
            for d in drift_items:
                dtype_label = _DRIFT_LABELS.get(d["drift_type"], d["drift_type"])
                lines.append(
                    f"- **{d['name']}** — {dtype_label}: "
                    f"{d['old_value']} -> {d['new_value']}"
                )
        else:
            lines.append("No drift alerts in the last 24 hours.")
    except Exception:
        lines.append("Drift detection unavailable (DuckDB not configured).")

    lines += [
        "",
        "---",
        f"*Generated by Parametric Data intelligence engine. {len(GLOBAL_TRIGGERS)} triggers monitored.*",
    ]

    digest = "\n".join(lines)

    # Save to disk
    DIGEST_DIR.mkdir(parents=True, exist_ok=True)
    digest_path = DIGEST_DIR / f"{today.isoformat()}.md"
    digest_path.write_text(digest, encoding="utf-8")

    return digest
