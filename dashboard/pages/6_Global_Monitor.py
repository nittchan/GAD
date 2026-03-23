"""
GAD Global Monitor — live parametric insurance risk map.
Shows real-time trigger status across 5 peril categories using cached open data.

Security: This page reads ONLY from the local cache. It NEVER calls external APIs.
All data is pre-fetched by the background fetcher (gad.monitor.fetcher).
"""

from __future__ import annotations

import streamlit as st
import pandas as pd

from gad.monitor.triggers import (
    GLOBAL_TRIGGERS,
    PERIL_LABELS,
    MonitorTrigger,
    get_triggers_by_peril,
)
from gad.monitor.cache import read_cache_with_staleness
from gad.monitor.sources import openmeteo, openaq, firms, opensky, chirps_monitor

st.set_page_config(page_title="GAD Global Monitor", page_icon="🌍", layout="wide")

# ── Dark theme CSS ──
st.markdown("""
<style>
    .trigger-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 6px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .trigger-card h4 { margin: 0 0 8px 0; color: #e6edf3; font-size: 14px; }
    .trigger-card .location { color: #8b949e; font-size: 12px; margin-bottom: 8px; }
    .status-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 3px;
        font-size: 11px;
        font-weight: 600;
        font-family: 'JetBrains Mono', monospace;
    }
    .status-critical { background: rgba(248,81,73,0.15); color: #f85149; border: 1px solid #f85149; }
    .status-normal { background: rgba(63,185,80,0.15); color: #3fb950; border: 1px solid #3fb950; }
    .status-no-data { background: rgba(139,148,158,0.15); color: #8b949e; border: 1px solid #8b949e; }
    .status-stale { background: rgba(210,153,34,0.15); color: #d29922; border: 1px solid #d29922; }
    .value-large {
        font-family: 'JetBrains Mono', monospace;
        font-size: 28px;
        font-weight: 700;
        margin: 4px 0;
    }
    .value-unit { color: #8b949e; font-size: 12px; }
    .peril-header {
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: #8b949e;
        margin: 24px 0 12px 0;
    }
</style>
""", unsafe_allow_html=True)


# ── Helper functions ──

SOURCE_KEY_MAP = {
    "openmeteo": "weather",
    "openaq": "aqi",
    "firms": "fire",
    "opensky": "flights",
    "chirps": "drought",
}


def _get_trigger_data(trigger: MonitorTrigger) -> tuple[dict | None, bool]:
    """Get cached data for a trigger. Returns (data, is_stale)."""
    source_key = SOURCE_KEY_MAP.get(trigger.data_source, trigger.data_source)
    return read_cache_with_staleness(source_key, trigger.id)


def _evaluate_trigger(trigger: MonitorTrigger, data: dict) -> dict:
    """Evaluate a trigger against its cached data."""
    if trigger.data_source == "openmeteo":
        return openmeteo.evaluate_trigger(data, trigger.threshold, trigger.threshold_unit, trigger.fires_when_above)
    elif trigger.data_source == "openaq":
        return openaq.evaluate_trigger(data, trigger.threshold)
    elif trigger.data_source == "firms":
        return firms.evaluate_trigger(data, trigger.threshold)
    elif trigger.data_source == "opensky":
        return opensky.evaluate_trigger(data, trigger.threshold)
    elif trigger.data_source == "chirps":
        return chirps_monitor.evaluate_trigger(data, trigger.threshold)
    return {"fired": False, "value": None, "status": "no_data"}


def _status_badge(status: str) -> str:
    """Render a status badge."""
    labels = {
        "critical": "TRIGGERED",
        "normal": "NORMAL",
        "no_data": "NO DATA",
        "no_flights": "NO FLIGHTS",
        "stale": "UPDATING",
        "no_api_key": "NO API KEY",
    }
    css_class = {
        "critical": "status-critical",
        "normal": "status-normal",
        "no_data": "status-no-data",
        "no_flights": "status-no-data",
        "stale": "status-stale",
        "no_api_key": "status-no-data",
    }
    label = labels.get(status, status.upper())
    cls = css_class.get(status, "status-no-data")
    return f'<span class="status-badge {cls}">{label}</span>'


# ── Page Header ──
st.markdown("# Global Actuarial Dashboard")
st.markdown("Live parametric insurance risk monitoring across **5 peril categories** using open data.")

# ── Peril filter ──
peril_options = list(PERIL_LABELS.keys())
peril_labels_list = list(PERIL_LABELS.values())
selected_perils = st.multiselect(
    "Filter by peril",
    options=peril_options,
    default=peril_options,
    format_func=lambda x: PERIL_LABELS[x],
)

# ── Build map data ──
map_rows = []
trigger_results = {}

for trigger in GLOBAL_TRIGGERS:
    if trigger.peril not in selected_perils:
        continue

    data, is_stale = _get_trigger_data(trigger)

    if data is not None:
        result = _evaluate_trigger(trigger, data)
        if is_stale:
            result["status"] = "stale"
    else:
        result = {"fired": False, "value": None, "status": "no_data"}

    trigger_results[trigger.id] = (trigger, data, result, is_stale)

    # Map marker color: red=triggered, green=normal, gray=no data
    color = [248, 81, 73, 200] if result["status"] == "critical" else \
            [63, 185, 80, 200] if result["status"] == "normal" else \
            [210, 153, 34, 200] if result["status"] == "stale" else \
            [139, 148, 158, 200]

    map_rows.append({
        "lat": trigger.lat,
        "lon": trigger.lon,
        "name": trigger.name,
        "status": result["status"],
        "color_r": color[0],
        "color_g": color[1],
        "color_b": color[2],
        "color_a": color[3],
        "size": 80000 if result["status"] == "critical" else 50000,
    })

# ── Map ──
if map_rows:
    df = pd.DataFrame(map_rows)
    st.pydeck_chart(
        {
            "initialViewState": {
                "latitude": 20,
                "longitude": 40,
                "zoom": 1.5,
                "pitch": 0,
            },
            "layers": [
                {
                    "@@type": "ScatterplotLayer",
                    "data": df.to_dict("records"),
                    "getPosition": "@@=[lon, lat]",
                    "getFillColor": "@@=[color_r, color_g, color_b, color_a]",
                    "getRadius": "@@=size",
                    "pickable": True,
                    "radiusMinPixels": 6,
                    "radiusMaxPixels": 20,
                },
            ],
            "mapStyle": "mapbox://styles/mapbox/dark-v11",
        },
        use_container_width=True,
        height=450,
    )
else:
    st.info("No triggers match the selected filters.")

# ── Trigger Cards ──
for peril in selected_perils:
    peril_triggers = [(tid, t, d, r, s) for tid, (t, d, r, s) in trigger_results.items() if t.peril == peril]
    if not peril_triggers:
        continue

    st.markdown(f'<div class="peril-header">{PERIL_LABELS[peril]}</div>', unsafe_allow_html=True)

    cols = st.columns(min(len(peril_triggers), 3))
    for i, (tid, trigger, data, result, is_stale) in enumerate(peril_triggers):
        with cols[i % len(cols)]:
            value = result.get("value")
            unit = result.get("unit", trigger.threshold_unit)
            status = result.get("status", "no_data")

            value_display = f"{value}" if value is not None else "—"
            color = "#f85149" if status == "critical" else "#3fb950" if status == "normal" else "#8b949e"

            st.markdown(f"""
            <div class="trigger-card">
                <h4>{trigger.name} {_status_badge(status)}</h4>
                <div class="location">{trigger.location_label}</div>
                <div class="value-large" style="color: {color}">{value_display}</div>
                <div class="value-unit">{unit} (threshold: {trigger.threshold})</div>
            </div>
            """, unsafe_allow_html=True)

            with st.expander("Details"):
                st.markdown(f"**Description:** {trigger.description}")
                st.markdown(f"**Data source:** {trigger.data_source}")
                st.markdown(f"**Threshold:** {trigger.threshold} {trigger.threshold_unit}")
                st.markdown(f"**Fires when:** {'above' if trigger.fires_when_above else 'below'} threshold")
                if data:
                    st.json(data)
                if is_stale:
                    st.warning("Data is stale — background fetch in progress.")
                if status == "no_data":
                    st.info("No data yet. Run `python -m gad.monitor.fetcher` to fetch.")

# ── Footer ──
st.markdown("---")
st.markdown(
    "Data from [OpenSky](https://opensky-network.org), "
    "[OpenAQ](https://openaq.org), "
    "[NASA FIRMS](https://firms.modaps.eosdis.nasa.gov), "
    "[Open-Meteo](https://open-meteo.com), "
    "[CHIRPS](https://www.chc.ucsb.edu/data/chirps). "
    "All data is pre-fetched and cached — this page makes **zero** external API calls."
)
