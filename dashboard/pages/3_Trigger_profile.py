"""
Trigger profile — full view of any trigger from the 436-trigger registry.
Shows live data, trigger details, and basis risk analysis when available.

Accessed via:
1. Direct navigation (sidebar selectbox)
2. Click-through from Global Monitor (session_state["selected_trigger_id"])
3. URL param: ?trigger=flight-delay-del
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from dashboard.components.theme import inject_theme
from gad.monitor.triggers import GLOBAL_TRIGGERS, PERIL_LABELS, MonitorTrigger, get_trigger_by_id
from gad.monitor.cache import read_cache_with_staleness
from gad.monitor.sources import openmeteo, openaq, firms, opensky, chirps_monitor, usgs_earthquake, aisstream, noaa_flood, noaa_nhc, ndvi

st.set_page_config(page_title="Trigger Profile | Parametric Data", layout="wide", initial_sidebar_state="collapsed")
inject_theme(st)

# ── Page-specific styles ──
st.markdown("""
<style>
    .stApp { background-color: #F5F0EB; }
    [data-testid="stSidebar"] { background: #EDE7E0; border-right: 1px solid #D4CCC0; }
    header[data-testid="stHeader"] { background: transparent; }
    .detail-card { background: #EDE7E0; border: 1px solid #D4CCC0; border-radius: 8px; padding: 20px; margin-bottom: 16px; }
    .detail-label { color: #7A7267; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; }
    .detail-value { color: #1E1B18; font-size: 20px; font-weight: 700; font-family: 'JetBrains Mono', ui-monospace, monospace; }
    .detail-value-small { color: #1E1B18; font-size: 14px; }
    .status-critical { color: #A63D40; }
    .status-normal { color: #2E8B6F; }
    .status-no-data { color: #7A7267; }

    /* Dark-themed dropdowns */
    [data-testid="stSelectbox"] [data-baseweb="select"] { background-color: #EDE7E0 !important; border-color: #D4CCC0 !important; color: #1E1B18 !important; }
    [data-baseweb="popover"] li { color: #1E1B18 !important; }
    [data-baseweb="popover"] li:hover { background-color: #F5EDEA !important; }
    [data-testid="stSidebar"] a { min-height: 44px !important; display: flex !important; align-items: center !important; }
</style>
""", unsafe_allow_html=True)

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

# ── Trigger selector ──
SOURCE_KEY_MAP = {
    "openmeteo": "weather", "openaq": "aqi", "firms": "fire",
    "opensky": "flights", "chirps": "drought", "usgs": "earthquake",
    "aisstream": "marine",
    "usgs_water": "flood",
    "noaa_nhc": "cyclone",
    "ndvi": "ndvi",
}

# Check if navigated from Global Monitor
pre_selected = st.session_state.get("selected_trigger_id")

# Build searchable trigger list
trigger_options = {f"{t.name} ({PERIL_LABELS[t.peril]})": t.id for t in GLOBAL_TRIGGERS}
option_labels = list(trigger_options.keys())

# Find default index
default_idx = 0
if pre_selected:
    for i, (label, tid) in enumerate(trigger_options.items()):
        if tid == pre_selected:
            default_idx = i
            break

st.sidebar.markdown("---")
selected_label = st.sidebar.selectbox(
    "Select trigger",
    options=option_labels,
    index=default_idx,
    placeholder="Search triggers...",
)

trigger_id = trigger_options.get(selected_label)
trigger = get_trigger_by_id(trigger_id) if trigger_id else None

if not trigger:
    st.info("Select a trigger from the sidebar.")
    st.stop()

# ── Load cached data ──
source_key = SOURCE_KEY_MAP.get(trigger.data_source, trigger.data_source)
data, is_stale = read_cache_with_staleness(source_key, trigger.id)


def _evaluate(trigger: MonitorTrigger, data: dict) -> dict:
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


if data is not None:
    result = _evaluate(trigger, data)
    if is_stale:
        result["status"] = "stale"
else:
    result = {"fired": False, "value": None, "status": "no_data"}

status = result.get("status", "no_data")
value = result.get("value")
unit = result.get("unit", trigger.threshold_unit)

# ── Page Header ──
status_color = "#A63D40" if status == "critical" else "#2E8B6F" if status == "normal" else "#7A7267"
status_label = "TRIGGERED" if status == "critical" else "NORMAL" if status == "normal" else "UPDATING" if status == "stale" else "NO DATA"

st.markdown(
    f'<p style="font-size:11px;color:#C8553D;letter-spacing:2px;text-transform:uppercase;margin-bottom:4px;">{PERIL_LABELS[trigger.peril]}</p>'
    f'<h1 style="font-size:32px;font-weight:700;color:#1E1B18;margin-bottom:4px;">{trigger.name}</h1>'
    f'<p style="color:#7A7267;font-size:14px;margin-bottom:24px;">{trigger.location_label}</p>',
    unsafe_allow_html=True,
)

# ── Live Status Card ──
col1, col2, col3 = st.columns(3)

with col1:
    value_display = f"{value}" if value is not None else "—"
    st.markdown(f"""
    <div class="detail-card">
        <div class="detail-label">Current Value</div>
        <div class="detail-value" style="color:{status_color}">{value_display}</div>
        <div style="color:#7A7267;font-size:12px;margin-top:4px;">{unit}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="detail-card">
        <div class="detail-label">Threshold</div>
        <div class="detail-value">{trigger.threshold}</div>
        <div style="color:#7A7267;font-size:12px;margin-top:4px;">{trigger.threshold_unit} · fires when {'above' if trigger.fires_when_above else 'below'}</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="detail-card">
        <div class="detail-label">Status</div>
        <div class="detail-value" style="color:{status_color}">{status_label}</div>
        <div style="color:#7A7267;font-size:12px;margin-top:4px;">{'Data source: ' + (data.get('source', trigger.data_source) if data else trigger.data_source)}</div>
    </div>
    """, unsafe_allow_html=True)

# ── Trigger Details ──
st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
st.markdown("### Trigger Definition")

d1, d2 = st.columns(2)
with d1:
    st.markdown(f"""
    <div class="detail-card">
        <div class="detail-label">Description</div>
        <div class="detail-value-small">{trigger.description}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="detail-card">
        <div class="detail-label">Geography</div>
        <div class="detail-value-small">Lat: {trigger.lat:.4f} · Lon: {trigger.lon:.4f}</div>
    </div>
    """, unsafe_allow_html=True)

with d2:
    st.markdown(f"""
    <div class="detail-card">
        <div class="detail-label">Peril Type</div>
        <div class="detail-value-small">{PERIL_LABELS[trigger.peril]}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="detail-card">
        <div class="detail-label">Data Source</div>
        <div class="detail-value-small">{trigger.data_source}</div>
    </div>
    """, unsafe_allow_html=True)

# ── Raw Data ──
if data:
    st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
    with st.expander("Raw data from source", expanded=False):
        st.json(data)
    if is_stale:
        st.warning("Data is stale — background fetch will update this automatically.")
else:
    st.info("No data cached yet. The background fetcher will populate this automatically.")

# ── Basis Risk Analysis ──
# Priority: 1) Precomputed JSON, 2) Legacy CSV, 3) Placeholder
ROOT = Path(__file__).resolve().parent.parent.parent
PRECOMPUTED_DIR = ROOT / "data" / "basis_risk"
LEGACY_CSV_MAP = {
    "flight-delay-blr": ROOT / "data" / "series" / "flight_delay_indigo.csv",
    "drought-kenya-marsabit": ROOT / "data" / "series" / "kenya_drought.csv",
}

precomputed_path = PRECOMPUTED_DIR / f"{trigger.id}.json"
csv_path = LEGACY_CSV_MAP.get(trigger.id)

if precomputed_path.is_file():
    # ── Precomputed basis risk (from scripts/precompute_basis_risk.py) ──
    st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
    st.markdown("### Basis Risk Analysis")
    st.caption("Precomputed historical back-test using the GAD engine")

    try:
        import json as _json
        from gad.engine.models import BasisRiskReport
        from dashboard.components import (
            render_score_card, timeline_fig, scatter_fig,
            confusion_matrix_fig, confusion_matrix_markdown,
            chart_summary, render_lloyds_checklist,
        )

        report_data = _json.loads(precomputed_path.read_text(encoding="utf-8"))
        report = BasisRiskReport(**report_data)

        render_score_card(report)
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(timeline_fig(report), use_container_width=True, config={"displayModeBar": False})
            st.caption(chart_summary(report))
        with c2:
            st.plotly_chart(scatter_fig(report), use_container_width=True, config={"displayModeBar": False})
            st.caption(chart_summary(report))

        st.plotly_chart(confusion_matrix_fig(report), use_container_width=True, config={"displayModeBar": False})
        st.markdown(confusion_matrix_markdown(report))
        render_lloyds_checklist(report)

        # PDF export if engine trigger can be built
        try:
            from gad.engine import TriggerDef
            from gad.engine.models import DataSourceProvenance
            from gad.engine.pdf_export import generate_lloyds_report

            engine_trigger = TriggerDef(
                name=trigger.name,
                peril=trigger.peril,
                threshold=trigger.threshold,
                threshold_unit=trigger.threshold_unit,
                data_source=trigger.data_source,
                geography={"type": "Point", "coordinates": [trigger.lon, trigger.lat]},
                provenance=DataSourceProvenance(
                    primary_source=trigger.data_source,
                    primary_url="https://parametricdata.io",
                    max_data_latency_seconds=3600,
                    historical_years_available=5,
                ),
                trigger_fires_when_above=trigger.fires_when_above,
            )
            pdf_bytes = generate_lloyds_report(engine_trigger, report)
            st.download_button(
                "Download Lloyd's PDF",
                data=pdf_bytes,
                file_name=f"parametricdata_report_{trigger.id}.pdf",
                mime="application/pdf",
            )
        except Exception:
            pass  # PDF export is optional
    except Exception as e:
        st.error(f"Failed to load precomputed report: {e}")

elif csv_path and csv_path.is_file():
    # ── Legacy CSV path (2 original triggers) ──
    st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
    st.markdown("### Basis Risk Analysis")
    st.caption("Historical back-test using the GAD engine")

    try:
        from gad.engine import TriggerDef, compute_basis_risk
        from gad.engine.loader import load_weather_data_from_csv
        from gad.engine.models import DataSourceProvenance
        from dashboard.components import (
            render_score_card, timeline_fig, scatter_fig,
            confusion_matrix_fig, confusion_matrix_markdown,
            chart_summary, render_lloyds_checklist,
        )
        from gad.engine.pdf_export import generate_lloyds_report

        engine_trigger = TriggerDef(
            name=trigger.name,
            peril=trigger.peril,
            threshold=trigger.threshold,
            threshold_unit=trigger.threshold_unit,
            data_source=trigger.data_source,
            geography={"type": "Point", "coordinates": [trigger.lon, trigger.lat]},
            provenance=DataSourceProvenance(
                primary_source=trigger.data_source,
                primary_url="https://parametricdata.io",
                max_data_latency_seconds=3600,
                historical_years_available=5,
            ),
            trigger_fires_when_above=trigger.fires_when_above,
        )

        weather_data = load_weather_data_from_csv(csv_path)
        report = compute_basis_risk(engine_trigger, weather_data)

        render_score_card(report)
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(timeline_fig(report), use_container_width=True, config={"displayModeBar": False})
            st.caption(chart_summary(report))
        with c2:
            st.plotly_chart(scatter_fig(report), use_container_width=True, config={"displayModeBar": False})
            st.caption(chart_summary(report))

        st.plotly_chart(confusion_matrix_fig(report), use_container_width=True, config={"displayModeBar": False})
        st.markdown(confusion_matrix_markdown(report))
        render_lloyds_checklist(report)

        pdf_bytes = generate_lloyds_report(engine_trigger, report)
        st.download_button(
            "Download Lloyd's PDF",
            data=pdf_bytes,
            file_name=f"parametricdata_report_{trigger.id}.pdf",
            mime="application/pdf",
        )
    except Exception as e:
        st.error(f"Basis risk computation failed: {e}")
else:
    st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="detail-card" style="border-color:#D4CCC0;">
        <div class="detail-label">Basis Risk Analysis</div>
        <div class="detail-value-small" style="color:#7A7267;">
            Historical basis risk analysis requires time-series data for this location.
            Currently showing live monitoring data. Full Spearman ρ, back-test, and Lloyd's
            scoring will be available when historical data is loaded for this trigger.
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── Back to map ──
st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
if st.button("← Back to Global Monitor"):
    st.switch_page("pages/6_Global_Monitor.py")

# ── Footer ──
from dashboard.components.footer import render_footer
render_footer()
