"""
GAD Global Monitor — live parametric insurance risk map.
Shows real-time trigger status across 6 peril categories using cached open data.

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
from gad.monitor.sources import openmeteo, openaq, firms, opensky, chirps_monitor, usgs_earthquake, aisstream

import json as _json
from pathlib import Path as _Path

_BASIS_RISK_DIR = _Path(__file__).resolve().parent.parent.parent / "data" / "basis_risk"


@st.cache_data(ttl=3600)
def _load_rho_map() -> dict[str, float | None]:
    """Load precomputed Spearman rho for all triggers. Cached 1 hour."""
    rho_map: dict[str, float | None] = {}
    if not _BASIS_RISK_DIR.is_dir():
        return rho_map
    for p in _BASIS_RISK_DIR.glob("*.json"):
        try:
            d = _json.loads(p.read_text(encoding="utf-8"))
            trigger_id = p.stem
            rho = d.get("spearman_rho")
            if rho is not None and rho == rho:  # exclude NaN
                rho_map[trigger_id] = round(rho, 3)
        except Exception:
            pass
    return rho_map


def _rho_badge(rho: float | None) -> str:
    """Render a small rho badge: green >= 0.7, amber >= 0.4, red < 0.4."""
    if rho is None:
        return ""
    if rho >= 0.7:
        color, bg = "#3fb950", "rgba(63,185,80,0.15)"
    elif rho >= 0.4:
        color, bg = "#d29922", "rgba(210,153,34,0.15)"
    else:
        color, bg = "#f85149", "rgba(248,81,73,0.15)"
    return (
        f'<span style="background:{bg};color:{color};border:1px solid {color};'
        f'border-radius:3px;padding:1px 6px;font-size:10px;font-family:monospace;'
        f'margin-left:6px;">ρ={rho:.2f}</span>'
    )

st.set_page_config(page_title="Parametric Data — Global Monitor", page_icon="🌍", layout="wide", initial_sidebar_state="expanded")

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
    "usgs": "earthquake",
    "aisstream": "marine",
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
    elif trigger.data_source == "usgs":
        return usgs_earthquake.evaluate_trigger(data, trigger.threshold)
    elif trigger.data_source == "aisstream":
        return aisstream.evaluate_trigger(data, trigger.threshold, trigger.threshold_unit)
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


# ── Sidebar ──
st.sidebar.markdown(
    '<div style="padding:8px 0 16px 0;">'
    '<p style="font-size:11px;color:#58a6ff;letter-spacing:2px;text-transform:uppercase;margin-bottom:4px;">parametricdata.io</p>'
    '<p style="font-size:20px;font-weight:700;color:#e6edf3;margin:0;">Parametric Data</p>'
    '</div>',
    unsafe_allow_html=True,
)
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Home", icon="🏠")
st.sidebar.page_link("pages/6_Global_Monitor.py", label="Global Monitor", icon="🌍")
st.sidebar.page_link("pages/1_Guided_mode.py", label="Build your own", icon="✨")
st.sidebar.page_link("pages/2_Expert_mode.py", label="Expert mode", icon="📝")
st.sidebar.page_link("pages/3_Trigger_profile.py", label="Trigger profile", icon="📊")
st.sidebar.page_link("pages/4_Compare.py", label="Compare triggers", icon="⚖️")
st.sidebar.page_link("pages/5_Account.py", label="Account", icon="👤")
st.sidebar.page_link("pages/7_Oracle.py", label="Oracle Ledger", icon="🔐")

# ── Page Header ──
st.markdown(
    '<p style="font-size:11px;color:#58a6ff;letter-spacing:2px;text-transform:uppercase;margin-bottom:4px;">Parametric Data</p>'
    '<h1 style="font-size:28px;font-weight:700;color:#e6edf3;margin-bottom:8px;">Global Monitor</h1>'
    f'<p style="color:#8b949e;font-size:14px;">{len(GLOBAL_TRIGGERS)} live triggers across 144 airports and 6 peril categories. All data from open sources.</p>',
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
        # BUG-03 fix: preserve fired status when data is stale.
        # A fired trigger going stale should still show as critical, not "stale".
        if is_stale and result.get("status") != "critical":
            result["status"] = "stale"
    else:
        result = {"fired": False, "value": None, "status": "no_data"}

    trigger_results[trigger.id] = (trigger, data, result, is_stale)

    # Map marker color
    # critical (fired) = red, even if stale
    # stale (not fired) = amber
    # normal = green
    # no_data = gray
    status = result["status"]
    if status == "critical":
        color = [248, 81, 73, 200]
    elif status == "normal":
        color = [63, 185, 80, 200]
    elif status == "stale":
        color = [210, 153, 34, 200]
    else:
        color = [139, 148, 158, 200]

    # Stale-but-fired: still red marker, but status label indicates staleness
    value = result.get("value")
    unit = result.get("unit", trigger.threshold_unit)
    value_str = f"{value} {unit}" if value is not None else "No data"
    if status == "critical" and is_stale:
        status_label = "TRIGGERED (stale)"
    elif status == "critical":
        status_label = "TRIGGERED"
    elif status == "normal":
        status_label = "NORMAL"
    elif status == "stale":
        status_label = "UPDATING"
    else:
        status_label = "NO DATA"

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

    # No text labels — too dense with 436 triggers. Info shown via hover tooltip.

    view_state = pdk.ViewState(latitude=20, longitude=30, zoom=1.8, pitch=0)

    tooltip = {
        "html": "<div style='font-family:monospace;background:#161b22;padding:10px 14px;border:1px solid #30363d;border-radius:4px;min-width:200px'>"
                "<div style='font-size:13px;font-weight:700;color:#e6edf3;margin-bottom:4px'>{name}</div>"
                "<div style='font-size:11px;color:#8b949e;margin-bottom:6px'>{location}</div>"
                "<div style='font-size:18px;font-weight:700;color:#58a6ff;margin-bottom:2px'>{value_str}</div>"
                "<div style='font-size:11px;font-weight:600;color:#e6edf3'>{status_label}</div>"
                "</div>",
        "style": {"backgroundColor": "transparent", "border": "none"},
    }

    layers = [scatter]
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
rho_map = _load_rho_map()

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
        table_html += '<th style="padding:8px;text-align:right;">Departures</th>'
        table_html += '<th style="padding:8px;text-align:right;">Metric</th><th style="padding:8px;">Status</th></tr>'

        for tid, trigger, data, result, is_stale in peril_triggers:
            status = result.get("status", "no_data")
            value = result.get("value")
            total_flights = result.get("total_flights", data.get("total_flights", 0) if data else 0)
            metric_type = result.get("metric", "avg_delay")

            # Show the right label based on data source metric
            if metric_type == "avg_delay" and value is not None:
                value_str = f"{value} min delay"
            elif metric_type == "departure_count" and value is not None:
                value_str = f"{value} flights"
            else:
                value_str = "—"

            color = "#f85149" if status == "critical" else "#3fb950" if status == "normal" else "#8b949e"

            rho_html = _rho_badge(rho_map.get(tid))
            table_html += f'<tr style="border-bottom:1px solid #21262d;">'
            table_html += f'<td style="padding:8px 12px;color:#e6edf3;font-weight:600;">{trigger.name}{rho_html}</td>'
            table_html += f'<td style="padding:8px;color:#8b949e;font-size:12px;">{trigger.location_label}</td>'
            table_html += f'<td style="padding:8px;text-align:right;color:#8b949e;">{total_flights}</td>'
            table_html += f'<td style="padding:8px;text-align:right;color:{color};font-weight:700;">{value_str}</td>'
            table_html += f'<td style="padding:8px;">{_status_badge(status)}</td>'
            table_html += '</tr>'

        table_html += '</table>'
        st.markdown(table_html, unsafe_allow_html=True)

        # View buttons for flight triggers (Streamlit can't put buttons in HTML tables)
        flight_cols = st.columns(6)
        for i, (tid, trigger, data, result, is_stale) in enumerate(peril_triggers[:6]):
            with flight_cols[i % 6]:
                if st.button(f"View {trigger.name}", key=f"view_{tid}", use_container_width=True):
                    st.session_state["selected_trigger_id"] = tid
                    st.switch_page("pages/3_Trigger_profile.py")

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

                rho_html = _rho_badge(rho_map.get(tid))
                st.markdown(f"""
                <div class="trigger-card">
                    <h4>{trigger.name} {_status_badge(status)}</h4>
                    <div class="location">{trigger.location_label}{rho_html}</div>
                    <div class="value-large" style="color: {color}">{value_display}</div>
                    <div class="value-unit">{unit} (threshold: {trigger.threshold})</div>
                </div>
                """, unsafe_allow_html=True)

                if st.button("View profile →", key=f"view_{tid}", use_container_width=True):
                    st.session_state["selected_trigger_id"] = tid
                    st.switch_page("pages/3_Trigger_profile.py")

# ── Footer ──
from dashboard.components.footer import render_footer
render_footer()
