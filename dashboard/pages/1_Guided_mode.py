"""Build a custom trigger in 4 steps — adds to the Global Monitor registry."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from gad.engine import TriggerDef, compute_basis_risk
from gad.engine.loader import load_weather_data_from_csv
from gad.engine.models import DataSourceProvenance
from gad.engine.pdf_export import generate_lloyds_report
from gad.monitor.triggers import MonitorTrigger, PERIL_LABELS
from dashboard.components import (
    chart_summary, confusion_matrix_markdown, render_score_card,
    timeline_fig, scatter_fig, confusion_matrix_fig, render_lloyds_checklist,
)

st.set_page_config(page_title="Build Trigger | Parametric Data", layout="wide", initial_sidebar_state="expanded")

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

# ── Config ──
ROOT = Path(__file__).resolve().parent.parent.parent
DATA_SERIES = ROOT / "data" / "series"
SAMPLE_CSV = {
    "drought": DATA_SERIES / "kenya_drought.csv",
    "flight_delay": DATA_SERIES / "flight_delay_indigo.csv",
    "flood": DATA_SERIES / "india_flood_imd.csv",
}

PERIL_CONFIG = {
    "flight_delay": {"label": "Flight Delay", "icon": "✈️", "unit": "minutes", "default": 60.0, "above": True, "source": "opensky"},
    "air_quality": {"label": "Air Quality", "icon": "🌫️", "unit": "AQI", "default": 150.0, "above": True, "source": "openaq"},
    "drought": {"label": "Drought", "icon": "☀️", "unit": "mm rainfall", "default": 50.0, "above": False, "source": "chirps"},
    "extreme_weather": {"label": "Extreme Weather", "icon": "🌪️", "unit": "celsius", "default": 42.0, "above": True, "source": "openmeteo"},
    "wildfire": {"label": "Wildfire", "icon": "🔥", "unit": "fire count", "default": 10.0, "above": True, "source": "firms"},
    "earthquake": {"label": "Earthquake", "icon": "🌍", "unit": "magnitude", "default": 5.0, "above": True, "source": "usgs"},
    "marine": {"label": "Marine / Shipping", "icon": "⚓", "unit": "vessels", "default": 20.0, "above": True, "source": "aisstream"},
}

# ── Header ──
st.markdown(
    '<p style="font-size:11px;color:#58a6ff;letter-spacing:2px;text-transform:uppercase;margin-bottom:4px;">Parametric Data</p>'
    '<h1 style="font-size:28px;font-weight:700;color:#e6edf3;margin-bottom:8px;">Build a Trigger</h1>'
    '<p style="color:#8b949e;font-size:14px;">Four steps. Plain English. About 60 seconds.</p>',
    unsafe_allow_html=True,
)

step = st.session_state.get("wizard_step", 1)
st.progress(step / 4, text=f"Step {step} of 4")
st.divider()

# ── Step 1: Peril ──
if step == 1:
    st.markdown("### What are you covering?")
    cols = st.columns(len(PERIL_CONFIG))
    for i, (key, cfg) in enumerate(PERIL_CONFIG.items()):
        with cols[i]:
            if st.button(f"{cfg['icon']}\n\n{cfg['label']}", key=f"peril_{key}", use_container_width=True):
                st.session_state["wizard_peril"] = key
                st.session_state["wizard_step"] = 2
                st.rerun()

# ── Step 2: Location ──
elif step == 2:
    peril = st.session_state.get("wizard_peril", "drought")
    cfg = PERIL_CONFIG[peril]
    st.markdown(f"### Where? ({cfg['icon']} {cfg['label']})")

    # Airport picker — searchable dropdown from the 144 airport registry
    from gad.monitor.airports import ALL_AIRPORTS
    airport_options = {f"{a.city} — {a.name} ({a.iata})": a for a in ALL_AIRPORTS}
    airport_labels = ["Custom location..."] + list(airport_options.keys())

    selected_airport = st.selectbox("Select an airport or city", airport_labels, index=0)

    if selected_airport != "Custom location..." and selected_airport in airport_options:
        airport = airport_options[selected_airport]
        location_name = f"{airport.city} ({airport.iata})"
        lat = airport.lat
        lon = airport.lon
        st.success(f"Selected: {airport.name}, {airport.city} ({airport.lat:.4f}, {airport.lon:.4f})")
    else:
        st.caption("Or enter coordinates manually:")
        location_name = st.text_input("Location name", placeholder="e.g. Dubai, Marsabit")
        lat = st.number_input("Latitude", value=25.2532, format="%.4f")
        lon = st.number_input("Longitude", value=55.3657, format="%.4f")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("← Back", use_container_width=True):
            st.session_state["wizard_step"] = 1
            st.rerun()
    with c2:
        if st.button("Next →", use_container_width=True, type="primary"):
            st.session_state["wizard_location"] = {"name": location_name or "Location", "lat": lat, "lon": lon}
            st.session_state["wizard_step"] = 3
            st.rerun()

# ── Step 3: Threshold ──
elif step == 3:
    peril = st.session_state.get("wizard_peril", "drought")
    cfg = PERIL_CONFIG[peril]
    st.markdown("### When should the payout trigger?")
    threshold = st.number_input(f"Threshold ({cfg['unit']})", value=float(cfg["default"]), min_value=0.0)
    direction = "above" if cfg["above"] else "below"
    st.info(f"Trigger fires when **{cfg['label'].lower()}** is **{direction} {threshold} {cfg['unit']}**.")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("← Back", use_container_width=True):
            st.session_state["wizard_step"] = 2
            st.rerun()
    with c2:
        if st.button("Build trigger →", use_container_width=True, type="primary"):
            st.session_state["wizard_threshold"] = threshold
            st.session_state["wizard_step"] = 4
            st.rerun()

# ── Step 4: Result ──
elif step == 4:
    peril = st.session_state.get("wizard_peril", "drought")
    cfg = PERIL_CONFIG[peril]
    loc = st.session_state.get("wizard_location", {"name": "Location", "lat": 28.55, "lon": 77.10})
    threshold = st.session_state.get("wizard_threshold", cfg["default"])

    # Build MonitorTrigger
    trigger_id = f"custom-{peril}-{loc['name'].lower().replace(' ', '-')}"
    monitor_trigger = MonitorTrigger(
        id=trigger_id,
        name=f"{cfg['label']} — {loc['name']}",
        peril=peril,
        lat=loc["lat"], lon=loc["lon"],
        location_label=loc["name"],
        threshold=threshold,
        threshold_unit=cfg["unit"],
        fires_when_above=cfg["above"],
        data_source=cfg["source"],
        description=f"Custom trigger: fires when {cfg['label'].lower()} is {'above' if cfg['above'] else 'below'} {threshold} {cfg['unit']} at {loc['name']}.",
    )

    st.markdown("### Your Trigger")
    st.markdown(f"""
    <div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:20px;margin-bottom:16px;">
        <div style="font-size:18px;font-weight:700;color:#e6edf3;margin-bottom:4px;">{monitor_trigger.name}</div>
        <div style="color:#8b949e;font-size:13px;margin-bottom:8px;">{monitor_trigger.description}</div>
        <div style="color:#58a6ff;font-size:12px;">
            {PERIL_LABELS[peril]} · Threshold: {threshold} {cfg['unit']} · Fires when {'above' if cfg['above'] else 'below'}
        </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("← Edit", use_container_width=True):
            st.session_state["wizard_step"] = 3
            st.rerun()
    with c2:
        if st.button("View on map →", use_container_width=True):
            st.session_state["selected_trigger_id"] = trigger_id
            st.switch_page("pages/3_Trigger_profile.py")
    with c3:
        compute = st.button("Compute basis risk", use_container_width=True, type="primary")

    if compute:
        # Build engine TriggerDef for basis risk computation
        engine_trigger = TriggerDef(
            name=monitor_trigger.name,
            peril=peril,
            threshold=threshold,
            threshold_unit=cfg["unit"],
            data_source=cfg["source"],
            geography={"type": "Point", "coordinates": [loc["lon"], loc["lat"]]},
            provenance=DataSourceProvenance(
                primary_source=cfg["source"],
                primary_url="https://parametricdata.io",
                max_data_latency_seconds=3600,
                historical_years_available=5,
            ),
            trigger_fires_when_above=cfg["above"],
        )

        # Try to get weather data — use sample CSV if available
        sample_csv = SAMPLE_CSV.get(peril)
        if sample_csv and sample_csv.is_file():
            try:
                weather_data = load_weather_data_from_csv(sample_csv)
                report = compute_basis_risk(engine_trigger, weather_data)
                st.session_state["wizard_report"] = report
                st.session_state["wizard_engine_trigger"] = engine_trigger
            except Exception as e:
                st.error(f"Computation failed: {e}")
        else:
            st.info("Historical data not available for this peril/location. Showing trigger definition only.")

    # Show report if computed
    if st.session_state.get("wizard_report") and st.session_state.get("wizard_engine_trigger"):
        report = st.session_state["wizard_report"]
        engine_trigger = st.session_state["wizard_engine_trigger"]

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
        st.download_button("Download Lloyd's PDF", data=pdf_bytes, file_name=f"parametricdata_report_{trigger_id}.pdf", mime="application/pdf")

# ── Footer ──
from dashboard.components.footer import render_footer
render_footer()
