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

st.set_page_config(page_title="Parametric Data — Global Monitor", page_icon="🌍", layout="wide")

# ── Dark theme CSS ──
st.markdown("""
<style>
    /* Hide Streamlit default chrome */
    [data-testid="stSidebarNav"] { display: none; }
    header[data-testid="stHeader"] { background: transparent; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    [data-testid="stDecoration"] { display: none; }

    .stApp { background-color: #0d1117; }
    [data-testid="stSidebar"] { background: #161b22; border-right: 1px solid #30363d; }
    h1, h2, h3 { color: #e6edf3 !important; }
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
st.markdown(
    '<p style="font-size:11px;color:#58a6ff;letter-spacing:2px;text-transform:uppercase;margin-bottom:4px;">Parametric Data</p>'
    '<h1 style="font-size:28px;font-weight:700;color:#e6edf3;margin-bottom:8px;">Global Monitor</h1>'
    f'<p style="color:#8b949e;font-size:14px;">{len(GLOBAL_TRIGGERS)} live triggers across 144 airports and 5 peril categories. All data from open sources.</p>',
    unsafe_allow_html=True,
)

# ── Filters ──
filter_col1, filter_col2 = st.columns([1, 1])
with filter_col1:
    peril_options = list(PERIL_LABELS.keys())
    selected_perils = st.multiselect(
        "Filter by peril",
        options=peril_options,
        default=peril_options,
        format_func=lambda x: PERIL_LABELS[x],
    )
with filter_col2:
    from gad.monitor.airports import ALL_AIRPORTS
    countries = sorted(set(a.country for a in ALL_AIRPORTS))
    selected_countries = st.multiselect(
        "Filter by country (flights/weather/AQI)",
        options=countries,
        default=[],
        placeholder="All countries",
    )

# ── Build country lookup for airport-derived triggers ──
_airport_country = {}
for _a in ALL_AIRPORTS:
    _airport_country[_a.iata.lower()] = _a.country

def _trigger_country(trigger: MonitorTrigger) -> str | None:
    """Get country for an airport-derived trigger."""
    for suffix in [trigger.id.split("-")[-1]]:
        if suffix in _airport_country:
            return _airport_country[suffix]
    return None

# ── Build map data ──
map_rows = []
trigger_results = {}

for trigger in GLOBAL_TRIGGERS:
    if trigger.peril not in selected_perils:
        continue

    # Apply country filter (only for airport-derived triggers)
    if selected_countries:
        country = _trigger_country(trigger)
        if country is not None and country not in selected_countries:
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

    value = result.get("value")
    unit = result.get("unit", trigger.threshold_unit)
    value_str = f"{value} {unit}" if value is not None else "No data"
    status_label = "TRIGGERED" if result["status"] == "critical" else \
                   "NORMAL" if result["status"] == "normal" else \
                   "UPDATING" if result["status"] == "stale" else "NO DATA"

    map_rows.append({
        "lat": trigger.lat,
        "lon": trigger.lon,
        "name": trigger.name,
        "location": trigger.location_label,
        "value_str": value_str,
        "status_label": status_label,
        "status": result["status"],
        "color_r": color[0],
        "color_g": color[1],
        "color_b": color[2],
        "color_a": color[3],
        "size": 80000 if result["status"] == "critical" else 50000,
    })

# ── Map ──
if map_rows:
    import pydeck as pdk

    df = pd.DataFrame(map_rows)

    # Main markers
    scatter = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position=["lon", "lat"],
        get_fill_color=["color_r", "color_g", "color_b", "color_a"],
        get_radius="size",
        pickable=True,
        radius_min_pixels=8,
        radius_max_pixels=24,
        opacity=0.85,
    )

    # Outer glow ring for triggered alerts
    triggered = df[df["status"] == "critical"]
    glow = pdk.Layer(
        "ScatterplotLayer",
        data=triggered,
        get_position=["lon", "lat"],
        get_fill_color=[248, 81, 73, 60],
        get_radius=160000,
        radius_min_pixels=16,
        radius_max_pixels=40,
        pickable=False,
    ) if len(triggered) > 0 else None

    # Labels
    text = pdk.Layer(
        "TextLayer",
        data=df,
        get_position=["lon", "lat"],
        get_text="name",
        get_color=[230, 237, 243, 200],
        get_size=11,
        get_alignment_baseline="'top'",
        get_pixel_offset=[0, 14],
        pickable=False,
    )

    view_state = pdk.ViewState(latitude=20, longitude=30, zoom=1.6, pitch=0)

    tooltip = {
        "html": "<div style='font-family:monospace;background:#161b22;padding:10px 14px;border:1px solid #30363d;border-radius:4px;min-width:180px'>"
                "<div style='font-size:13px;font-weight:700;color:#e6edf3;margin-bottom:4px'>{name}</div>"
                "<div style='font-size:11px;color:#8b949e;margin-bottom:6px'>{location}</div>"
                "<div style='font-size:16px;font-weight:700;color:#58a6ff;margin-bottom:2px'>{value_str}</div>"
                "<div style='font-size:11px;font-weight:600;color:#e6edf3'>{status_label}</div>"
                "</div>",
        "style": {"backgroundColor": "transparent", "border": "none"},
    }

    layers = [scatter, text]
    if glow is not None:
        layers.insert(0, glow)

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
        tooltip=tooltip,
    )
    st.pydeck_chart(deck, use_container_width=True, height=500)
else:
    st.info("No triggers match the selected filters.")

# ── Trigger Display ──
for peril in selected_perils:
    peril_triggers = [(tid, t, d, r, s) for tid, (t, d, r, s) in trigger_results.items() if t.peril == peril]
    if not peril_triggers:
        continue

    st.markdown(f'<div class="peril-header">{PERIL_LABELS[peril]} ({len(peril_triggers)})</div>', unsafe_allow_html=True)

    # Flight delay: compact table (144 airports — cards don't scale)
    if peril == "flight_delay":
        table_html = '<table style="width:100%;border-collapse:collapse;font-size:13px;font-family:monospace;">'
        table_html += '<tr style="border-bottom:1px solid #30363d;color:#8b949e;text-align:left;">'
        table_html += '<th style="padding:8px 12px;">Airport</th><th style="padding:8px;">Location</th>'
        table_html += '<th style="padding:8px;text-align:right;">Flights</th>'
        table_html += '<th style="padding:8px;text-align:right;">Avg Delay</th><th style="padding:8px;">Status</th></tr>'

        for tid, trigger, data, result, is_stale in peril_triggers:
            status = result.get("status", "no_data")
            value = result.get("value")
            total_flights = result.get("total_flights", data.get("total_flights", 0) if data else 0)
            value_str = f"{value} min" if value is not None else "—"
            color = "#f85149" if status == "critical" else "#3fb950" if status == "normal" else "#8b949e"

            table_html += f'<tr style="border-bottom:1px solid #21262d;">'
            table_html += f'<td style="padding:8px 12px;color:#e6edf3;font-weight:600;">{trigger.name}</td>'
            table_html += f'<td style="padding:8px;color:#8b949e;font-size:12px;">{trigger.location_label}</td>'
            table_html += f'<td style="padding:8px;text-align:right;color:#8b949e;">{total_flights}</td>'
            table_html += f'<td style="padding:8px;text-align:right;color:{color};font-weight:700;">{value_str}</td>'
            table_html += f'<td style="padding:8px;">{_status_badge(status)}</td>'
            table_html += '</tr>'

        table_html += '</table>'
        st.markdown(table_html, unsafe_allow_html=True)

    # Other perils: card layout (fewer items, richer display)
    else:
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
from dashboard.components.footer import render_footer
render_footer()
