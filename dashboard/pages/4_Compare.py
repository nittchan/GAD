"""Compare any two triggers from the 436-trigger registry side-by-side."""

from __future__ import annotations

import streamlit as st

from gad.monitor.triggers import GLOBAL_TRIGGERS, PERIL_LABELS, MonitorTrigger, get_trigger_by_id
from gad.monitor.cache import read_cache_with_staleness
from gad.monitor.sources import openmeteo, openaq, firms, opensky, chirps_monitor, usgs_earthquake, aisstream, noaa_flood, noaa_nhc

st.set_page_config(page_title="Compare | Parametric Data", layout="wide", initial_sidebar_state="collapsed")

# ── Theme ──
st.markdown("""
<style>
    [data-testid="stSidebarNav"] { display: none; }
    header[data-testid="stHeader"] { background: transparent; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .stApp { background-color: #ffffff; }
    [data-testid="stSidebar"] { background: #f6f8fa; border-right: 1px solid #d1d9e0; }
    h1, h2, h3, h4, p, span, label, div { color: #1f2328; }
    .compare-card { background: #f6f8fa; border: 1px solid #d1d9e0; border-radius: 8px; padding: 20px; }
    .compare-label { color: #656d76; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }
    .compare-value { font-family: ui-monospace, monospace; font-size: 24px; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──
st.sidebar.markdown(
    '<div style="padding:8px 0 16px 0;">'
    '<p style="font-size:11px;color:#0969da;letter-spacing:2px;text-transform:uppercase;margin-bottom:4px;">parametricdata.io</p>'
    '<p style="font-size:20px;font-weight:700;color:#1f2328;margin:0;">Parametric Data</p>'
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

# ── Helpers ──
SOURCE_KEY_MAP = {
    "openmeteo": "weather", "openaq": "aqi", "firms": "fire",
    "opensky": "flights", "chirps": "drought", "usgs": "earthquake",
    "aisstream": "marine",
    "usgs_water": "flood",
    "noaa_nhc": "cyclone",
}

def _evaluate(trigger, data):
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
    return {"fired": False, "value": None, "status": "no_data"}

def _get_data(trigger):
    source_key = SOURCE_KEY_MAP.get(trigger.data_source, trigger.data_source)
    data, is_stale = read_cache_with_staleness(source_key, trigger.id)
    if data:
        result = _evaluate(trigger, data)
        if is_stale:
            result["status"] = "stale"
        return data, result
    return None, {"fired": False, "value": None, "status": "no_data"}

# ── Header ──
st.markdown(
    '<p style="font-size:11px;color:#0969da;letter-spacing:2px;text-transform:uppercase;margin-bottom:4px;">Parametric Data</p>'
    '<h1 style="font-size:28px;font-weight:700;color:#1f2328;margin-bottom:8px;">Compare Triggers</h1>'
    '<p style="color:#656d76;font-size:14px;">Select any two triggers to compare side-by-side.</p>',
    unsafe_allow_html=True,
)

# ── Trigger selectors ──
trigger_labels = {f"{t.name} ({PERIL_LABELS[t.peril]})": t.id for t in GLOBAL_TRIGGERS}
labels = list(trigger_labels.keys())

sel_col1, sel_col2 = st.columns(2)
with sel_col1:
    label1 = st.selectbox("Trigger A", options=labels, index=0, key="compare_a")
with sel_col2:
    label2 = st.selectbox("Trigger B", options=labels, index=min(1, len(labels)-1), key="compare_b")

t1 = get_trigger_by_id(trigger_labels[label1])
t2 = get_trigger_by_id(trigger_labels[label2])

if not t1 or not t2:
    st.stop()

data1, result1 = _get_data(t1)
data2, result2 = _get_data(t2)

# ── Comparison ──
st.markdown('<div style="height:24px"></div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

for col, trigger, data, result in [(col1, t1, data1, result1), (col2, t2, data2, result2)]:
    with col:
        status = result.get("status", "no_data")
        value = result.get("value")
        unit = result.get("unit", trigger.threshold_unit)
        color = "#d1242f" if status == "critical" else "#1a7f37" if status == "normal" else "#656d76"
        status_label = "TRIGGERED" if status == "critical" else "NORMAL" if status == "normal" else "NO DATA"

        st.markdown(f"""
        <div class="compare-card" style="margin-bottom:16px;">
            <div style="font-size:18px;font-weight:700;color:#1f2328;margin-bottom:4px;">{trigger.name}</div>
            <div style="color:#656d76;font-size:12px;margin-bottom:12px;">{trigger.location_label} · {PERIL_LABELS[trigger.peril]}</div>
            <div class="compare-label">Current Value</div>
            <div class="compare-value" style="color:{color}">{value if value is not None else '—'}</div>
            <div style="color:#656d76;font-size:12px;">{unit}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="compare-card">
            <div class="compare-label">Threshold</div>
            <div style="font-size:16px;font-weight:600;color:#1f2328;">{trigger.threshold} {trigger.threshold_unit}</div>
            <div style="color:#656d76;font-size:12px;margin-top:8px;">Fires when {'above' if trigger.fires_when_above else 'below'} · Status: <span style="color:{color};font-weight:600;">{status_label}</span></div>
        </div>
        """, unsafe_allow_html=True)

        if data:
            with st.expander("Raw data"):
                st.json(data)

# ── Comparison table ──
st.markdown('<div style="height:24px"></div>', unsafe_allow_html=True)

v1 = result1.get("value")
v2 = result2.get("value")
v1_str = str(v1) if v1 is not None else "—"
v2_str = str(v2) if v2 is not None else "—"

if v1 is not None and v2 is not None:
    try:
        delta = float(v2) - float(v1)
        delta_str = f"{delta:+.1f}"
    except (TypeError, ValueError):
        delta_str = "—"
else:
    delta_str = "—"

st.markdown(f"""
| | {t1.name} | {t2.name} | Δ |
|---|---:|---:|---:|
| Current value | {v1_str} | {v2_str} | {delta_str} |
| Threshold | {t1.threshold} {t1.threshold_unit} | {t2.threshold} {t2.threshold_unit} | — |
| Peril | {PERIL_LABELS[t1.peril]} | {PERIL_LABELS[t2.peril]} | — |
| Data source | {data1.get('source', t1.data_source) if data1 else t1.data_source} | {data2.get('source', t2.data_source) if data2 else t2.data_source} | — |
""")

# ── Footer ──
from dashboard.components.footer import render_footer
render_footer()
