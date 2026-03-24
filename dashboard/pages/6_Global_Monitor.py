"""
GAD Global Monitor — live parametric insurance risk map.
Shows real-time trigger status across 7 peril categories using cached open data.

Security: This page reads ONLY from the local cache. It NEVER calls external APIs.
All data is pre-fetched by the background fetcher (gad.monitor.fetcher).
"""

from __future__ import annotations

import streamlit as st
import pandas as pd

from dashboard.components.theme import inject_theme

from gad.monitor.triggers import (
    GLOBAL_TRIGGERS,
    PERIL_LABELS,
    MonitorTrigger,
    get_triggers_by_peril,
)
from gad.monitor.cache import read_cache_with_staleness
from gad.monitor.sources import openmeteo, openaq, firms, opensky, chirps_monitor, usgs_earthquake, aisstream, noaa_flood, noaa_nhc, ndvi

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
        color, bg = "#2E8B6F", "#E4F2EC"
    elif rho >= 0.4:
        color, bg = "#D4A017", "#FDF5E0"
    else:
        color, bg = "#A63D40", "#F8EAEA"
    return (
        f'<span style="background:{bg};color:{color};border:1px solid {color};'
        f"border-radius:3px;padding:1px 6px;font-size:10px;font-family:'JetBrains Mono',ui-monospace,monospace;"
        f'margin-left:6px;">ρ={rho:.2f}</span>'
    )

st.set_page_config(page_title="Parametric Data — Global Monitor", page_icon="🌍", layout="wide", initial_sidebar_state="collapsed")
inject_theme(st)

# ── Page-specific styles ──
st.markdown("""
<style>
    .trigger-card {
        background: #EDE7E0;
        border: 1px solid #D4CCC0;
        border-radius: 6px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .trigger-card h4 { margin: 0 0 8px 0; color: #1E1B18; font-size: 14px; }
    .trigger-card .location { color: #7A7267; font-size: 12px; margin-bottom: 8px; }
    .status-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 3px;
        font-size: 11px;
        font-weight: 600;
        font-family: 'JetBrains Mono', ui-monospace, monospace;
    }
    .status-critical { background: #F8EAEA; color: #A63D40; border: 1px solid #A63D40; }
    .status-normal { background: #E4F2EC; color: #2E8B6F; border: 1px solid #2E8B6F; }
    .status-no-data { background: #EDE7E0; color: #7A7267; border: 1px solid #D4CCC0; }
    .status-stale { background: #FDF5E0; color: #D4A017; border: 1px solid #D4A017; }
    .value-large {
        font-family: 'JetBrains Mono', ui-monospace, monospace;
        font-size: 28px;
        font-weight: 700;
        color: #1E1B18;
        margin: 4px 0;
    }
    .value-unit { color: #7A7267; font-size: 12px; }

    /* Peril filter pills — parchment style */
    [data-testid="stMultiSelect"] [data-baseweb="tag"] {
        background: #EDE7E0 !important;
        border: 1px solid #D4CCC0 !important;
        color: #1E1B18 !important;
        border-radius: 3px !important;
        font-family: 'Instrument Sans', sans-serif !important;
        font-size: 12px !important;
    }
    [data-testid="stMultiSelect"] [data-baseweb="tag"] span { color: #1E1B18 !important; }
    [data-testid="stMultiSelect"] [data-baseweb="tag"] svg { fill: #7A7267 !important; }
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
    "usgs_water": "flood",
    "noaa_nhc": "cyclone",
    "ndvi": "ndvi",
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
    elif trigger.data_source == "usgs_water":
        return noaa_flood.evaluate_trigger(data, trigger.threshold)
    elif trigger.data_source == "noaa_nhc":
        return noaa_nhc.evaluate_trigger(data, trigger.threshold)
    elif trigger.data_source == "ndvi":
        return ndvi.evaluate_trigger(data, trigger.threshold)
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
        "data_source_unavailable": "NO STATION",
    }
    css_class = {
        "critical": "status-critical",
        "normal": "status-normal",
        "no_data": "status-no-data",
        "no_flights": "status-no-data",
        "stale": "status-stale",
        "no_api_key": "status-no-data",
        "data_source_unavailable": "status-no-data",
    }
    label = labels.get(status, status.upper())
    cls = css_class.get(status, "status-no-data")
    return f'<span class="status-badge {cls}">{label}</span>'


# ── Sidebar ──
st.sidebar.markdown(
    '<div style="padding:8px 0 16px 0;">'
    '<p style="font-size:11px;color:#C8553D;letter-spacing:2px;text-transform:uppercase;margin-bottom:4px;">parametricdata.io</p>'
    '<p style="font-size:20px;font-weight:700;color:#1E1B18;margin:0;">Parametric Data</p>'
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
st.sidebar.page_link("pages/8_Digest.py", label="Daily Digest", icon="📨")

# ── Page Header ──
st.markdown(
    '<p style="font-size:11px;color:#C8553D;letter-spacing:2px;text-transform:uppercase;margin-bottom:4px;">Parametric Data</p>'
    '<h1 style="font-size:28px;font-weight:700;color:#1E1B18;margin-bottom:8px;">Global Monitor</h1>'
    f'<p style="color:#7A7267;font-size:14px;">{len(GLOBAL_TRIGGERS)} live triggers across {len(PERIL_LABELS)} peril categories. All data from open sources.</p>',
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
    elif status == "data_source_unavailable":
        status_label = "NO STATION"
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
if not map_rows:
    st.info("No cached data yet. The background fetcher runs every 15 minutes and populates the map automatically. Run `python -m gad.monitor.fetcher` to fetch immediately.")

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
        "html": "<div style='font-family:JetBrains Mono,ui-monospace,monospace;background:#F5F0EB;padding:10px 14px;border:1px solid #D4CCC0;border-radius:4px;min-width:200px;box-shadow:0 1px 3px rgba(0,0,0,0.12)'>"
                "<div style='font-size:13px;font-weight:700;color:#1E1B18;margin-bottom:4px'>{name}</div>"
                "<div style='font-size:11px;color:#7A7267;margin-bottom:6px'>{location}</div>"
                "<div style='font-size:18px;font-weight:700;color:#C8553D;margin-bottom:2px'>{value_str}</div>"
                "<div style='font-size:11px;font-weight:600;color:#1E1B18'>{status_label}</div>"
                "</div>",
        "style": {"backgroundColor": "transparent", "border": "none"},
    }

    layers = [scatter]
    if glow is not None:
        layers.insert(0, glow)

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_style="light",
        tooltip=tooltip,
    )
    st.pydeck_chart(deck, use_container_width=True, height=500)
else:
    st.info("No triggers match the selected filters.")

# ── Country Risk Index (PREI) ──
from gad.monitor.risk_index import compute_prei

prei_data = compute_prei(trigger_results)
if prei_data:
    with st.expander("Country Risk Exposure Index (PREI)", expanded=False):
        st.caption("PREI = (fired/total)*100 + (near-threshold/total)*30. Higher = more risk exposure.")
        prei_sorted = sorted(prei_data.items(), key=lambda x: x[1]["prei"], reverse=True)

        table = '<table style="width:100%;border-collapse:collapse;font-size:13px;">'
        table += '<tr style="border-bottom:1px solid #D4CCC0;color:#7A7267;"><th style="padding:6px 10px;text-align:left;">Country</th><th style="padding:6px;text-align:right;">PREI</th><th style="padding:6px;text-align:right;">Triggers</th><th style="padding:6px;text-align:right;">Fired</th><th style="padding:6px;text-align:right;">Near</th></tr>'

        for country, stats in prei_sorted:
            prei_val = stats["prei"]
            if prei_val >= 50:
                prei_color = "#A63D40"
            elif prei_val >= 20:
                prei_color = "#D4A017"
            else:
                prei_color = "#2E8B6F"
            table += f'<tr style="border-bottom:1px solid #E3DCD3;">'
            table += f'<td style="padding:6px 10px;">{country}</td>'
            table += f'<td style="padding:6px;text-align:right;font-weight:700;color:{prei_color};font-family:JetBrains Mono,ui-monospace,monospace;">{prei_val}</td>'
            table += f'<td style="padding:6px;text-align:right;color:#7A7267;">{stats["total"]}</td>'
            table += f'<td style="padding:6px;text-align:right;color:#A63D40;">{stats["fired"]}</td>'
            table += f'<td style="padding:6px;text-align:right;color:#D4A017;">{stats["near_threshold"]}</td>'
            table += '</tr>'

        table += '</table>'
        st.markdown(table, unsafe_allow_html=True)

# ── Trigger Display ──
rho_map = _load_rho_map()

for peril in selected_perils:
    peril_triggers = [(tid, t, d, r, s) for tid, (t, d, r, s) in trigger_results.items() if t.peril == peril]
    if not peril_triggers:
        continue

    with st.expander(f"{PERIL_LABELS[peril]} ({len(peril_triggers)})", expanded=False):
        # Flight delay: compact table (144 airports — cards don't scale)
        if peril == "flight_delay":
            table_html = '<table style="width:100%;border-collapse:collapse;font-size:13px;font-family:monospace;">'
            table_html += '<tr style="border-bottom:1px solid #D4CCC0;color:#7A7267;text-align:left;">'
            table_html += '<th style="padding:8px 12px;">Airport</th><th style="padding:8px;">Location</th>'
            table_html += '<th style="padding:8px;text-align:right;">Departures</th>'
            table_html += '<th style="padding:8px;text-align:right;">Metric</th><th style="padding:8px;">Status</th></tr>'

            for tid, trigger, data, result, is_stale in peril_triggers:
                status = result.get("status", "no_data")
                value = result.get("value")
                total_flights = result.get("total_flights", data.get("total_flights", 0) if data else 0)
                metric_type = result.get("metric", "avg_delay")

                if metric_type == "avg_delay" and value is not None:
                    value_str = f"{value} min delay"
                elif metric_type == "departure_count" and value is not None:
                    value_str = f"{value} flights"
                else:
                    value_str = "—"

                color = "#A63D40" if status == "critical" else "#2E8B6F" if status == "normal" else "#7A7267"

                rho_html = _rho_badge(rho_map.get(tid))
                table_html += f'<tr style="border-bottom:1px solid #E3DCD3;">'
                table_html += f'<td style="padding:8px 12px;color:#1E1B18;font-weight:600;">{trigger.name}{rho_html}</td>'
                table_html += f'<td style="padding:8px;color:#7A7267;font-size:12px;">{trigger.location_label}</td>'
                table_html += f'<td style="padding:8px;text-align:right;color:#7A7267;">{total_flights}</td>'
                table_html += f'<td style="padding:8px;text-align:right;color:{color};font-weight:700;">{value_str}</td>'
                table_html += f'<td style="padding:8px;">{_status_badge(status)}</td>'
                table_html += '</tr>'

            table_html += '</table>'
            st.markdown(table_html, unsafe_allow_html=True)

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
                    color = "#A63D40" if status == "critical" else "#2E8B6F" if status == "normal" else "#7A7267"

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
