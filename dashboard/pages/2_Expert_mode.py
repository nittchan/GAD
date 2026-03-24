"""Expert mode — JSON editor for trigger definitions. Full schema control."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st
from pydantic import ValidationError

from gad.engine import TriggerDef, compute_basis_risk
from gad.engine.loader import load_weather_data_from_csv
from gad.engine.models import DataSourceProvenance
from gad.engine.pdf_export import generate_lloyds_report
from gad.monitor.triggers import MonitorTrigger, PERIL_LABELS
from dashboard.components import (
    chart_summary, confusion_matrix_markdown, render_score_card,
    timeline_fig, scatter_fig, confusion_matrix_fig, render_lloyds_checklist,
)

st.set_page_config(page_title="Expert Mode | Parametric Data", layout="wide", initial_sidebar_state="collapsed")

# ── Theme ──
st.markdown("""
<style>
    [data-testid="stSidebarNav"] { display: none; }
    header[data-testid="stHeader"] { background: transparent; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .stApp { background-color: #0d1117; }
    [data-testid="stSidebar"] { background: #161b22; border-right: 1px solid #30363d; }
    h1, h2, h3, h4, p, span, label, div { color: #e6edf3; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──
st.sidebar.markdown(
    '<div style="padding:8px 0 16px 0;">'
    '<p style="font-size:11px;color:#58a6ff;letter-spacing:2px;text-transform:uppercase;margin-bottom:4px;">parametricdata.io</p>'
    '<p style="font-size:20px;font-weight:700;color:#e6edf3;margin:0;">Parametric Data</p>'
    '</div>', unsafe_allow_html=True,
)
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Home", icon="🏠")
st.sidebar.page_link("pages/6_Global_Monitor.py", label="Global Monitor", icon="🌍")
st.sidebar.page_link("pages/1_Guided_mode.py", label="Build your own", icon="✨")
st.sidebar.page_link("pages/2_Expert_mode.py", label="Expert mode", icon="📝")
st.sidebar.page_link("pages/3_Trigger_profile.py", label="Trigger profile", icon="📊")
st.sidebar.page_link("pages/4_Compare.py", label="Compare triggers", icon="⚖️")

# ── Sample data ──
ROOT = Path(__file__).resolve().parent.parent.parent
DATA_SERIES = ROOT / "data" / "series"
SAMPLE_CSV = {
    "drought": DATA_SERIES / "kenya_drought.csv",
    "flight_delay": DATA_SERIES / "flight_delay_indigo.csv",
    "flood": DATA_SERIES / "india_flood_imd.csv",
}

# ── Header ──
st.markdown(
    '<p style="font-size:11px;color:#58a6ff;letter-spacing:2px;text-transform:uppercase;margin-bottom:4px;">Parametric Data</p>'
    '<h1 style="font-size:28px;font-weight:700;color:#e6edf3;margin-bottom:8px;">Expert Mode</h1>'
    '<p style="color:#8b949e;font-size:14px;">Edit trigger JSON directly. Full schema control. Same engine as guided mode.</p>',
    unsafe_allow_html=True,
)

# ── Sample trigger JSON ──
SAMPLE_JSON = json.dumps({
    "name": "Delhi AQI Alert",
    "peril": "air_quality",
    "threshold": 150,
    "threshold_unit": "AQI",
    "data_source": "openaq",
    "lat": 28.6139,
    "lon": 77.2090,
    "location_label": "New Delhi, India",
    "fires_when_above": True,
    "description": "Parametric trigger fires when AQI exceeds 150 (unhealthy) at Delhi."
}, indent=2)

json_text = st.text_area(
    "Trigger JSON",
    value=st.session_state.get("expert_json", SAMPLE_JSON),
    height=300,
    key="expert_json_editor",
)
st.session_state["expert_json"] = json_text

c1, c2 = st.columns(2)
with c1:
    validate_btn = st.button("Validate trigger", use_container_width=True, type="primary")
with c2:
    compute_btn = st.button("Validate + compute basis risk", use_container_width=True)

if validate_btn or compute_btn:
    try:
        raw = json.loads(json_text)
        if not isinstance(raw, dict):
            st.error("JSON root must be an object.")
            st.stop()

        # Validate as MonitorTrigger
        trigger_id = f"expert-{raw.get('name', 'unnamed').lower().replace(' ', '-')}"
        monitor_trigger = MonitorTrigger(
            id=trigger_id,
            name=raw.get("name", "Unnamed"),
            peril=raw.get("peril", "drought"),
            lat=raw.get("lat", 0.0),
            lon=raw.get("lon", 0.0),
            location_label=raw.get("location_label", "Unknown"),
            threshold=float(raw.get("threshold", 0)),
            threshold_unit=raw.get("threshold_unit", ""),
            fires_when_above=raw.get("fires_when_above", True),
            data_source=raw.get("data_source", "openmeteo"),
            description=raw.get("description", ""),
        )

        st.success(f"Valid trigger: **{monitor_trigger.name}** ({PERIL_LABELS.get(monitor_trigger.peril, monitor_trigger.peril)})")
        st.session_state["expert_monitor_trigger"] = monitor_trigger

        st.markdown(f"""
        <div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:16px;margin:12px 0;">
            <div style="font-size:15px;font-weight:600;color:#e6edf3;">{monitor_trigger.name}</div>
            <div style="color:#8b949e;font-size:12px;margin-top:4px;">
                {monitor_trigger.location_label} · {PERIL_LABELS.get(monitor_trigger.peril, '')} ·
                Threshold: {monitor_trigger.threshold} {monitor_trigger.threshold_unit} ·
                Fires when {'above' if monitor_trigger.fires_when_above else 'below'}
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("View trigger profile →"):
            st.session_state["selected_trigger_id"] = trigger_id
            st.switch_page("pages/3_Trigger_profile.py")

        if compute_btn:
            # Build engine TriggerDef
            engine_trigger = TriggerDef(
                name=monitor_trigger.name,
                peril=monitor_trigger.peril,
                threshold=monitor_trigger.threshold,
                threshold_unit=monitor_trigger.threshold_unit,
                data_source=monitor_trigger.data_source,
                geography={"type": "Point", "coordinates": [monitor_trigger.lon, monitor_trigger.lat]},
                provenance=DataSourceProvenance(
                    primary_source=monitor_trigger.data_source,
                    primary_url="https://parametricdata.io",
                    max_data_latency_seconds=3600,
                    historical_years_available=5,
                ),
                trigger_fires_when_above=monitor_trigger.fires_when_above,
            )

            sample_csv = SAMPLE_CSV.get(monitor_trigger.peril)
            if sample_csv and sample_csv.is_file():
                weather_data = load_weather_data_from_csv(sample_csv)
                report = compute_basis_risk(engine_trigger, weather_data)
                st.session_state["expert_report"] = report
                st.session_state["expert_engine_trigger"] = engine_trigger
            else:
                st.info(f"No sample historical data for {monitor_trigger.peril}. Showing trigger definition only.")

    except json.JSONDecodeError as e:
        st.error(f"Invalid JSON: {e}")
    except (ValidationError, ValueError, TypeError) as e:
        st.error(f"Validation error: {e}")

# ── Show basis risk report ──
if st.session_state.get("expert_report") and st.session_state.get("expert_engine_trigger"):
    report = st.session_state["expert_report"]
    engine_trigger = st.session_state["expert_engine_trigger"]

    st.divider()
    st.markdown("### Basis Risk Analysis")
    st.caption("Using sample historical data")
    render_score_card(report)
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(timeline_fig(report), use_container_width=True, config={"displayModeBar": False})
    with c2:
        st.plotly_chart(scatter_fig(report), use_container_width=True, config={"displayModeBar": False})
    st.plotly_chart(confusion_matrix_fig(report), use_container_width=True, config={"displayModeBar": False})
    st.markdown(confusion_matrix_markdown(report))
    render_lloyds_checklist(report)
    pdf_bytes = generate_lloyds_report(engine_trigger, report)
    st.download_button("Download Lloyd's PDF", data=pdf_bytes, file_name=f"parametricdata_report_expert.pdf", mime="application/pdf")

# ── Footer ──
from dashboard.components.footer import render_footer
render_footer()
