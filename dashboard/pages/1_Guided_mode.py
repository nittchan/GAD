"""Build a trigger in 4 steps — plain English, no YAML unless toggled."""

from pathlib import Path
from uuid import UUID

import streamlit as st
import yaml
from pydantic import ValidationError

from gad.engine import TriggerDef, compute_basis_risk
from gad.engine.loader import load_weather_data_from_csv
from gad.engine.models import BasisRiskReport, DataSourceProvenance
from gad.engine.analytics import track, get_or_create_session_id
from gad.pipeline import PipelineError, fetch_chirps_series
from dashboard.components.auth import current_user
from dashboard.components import (
    chart_summary,
    confusion_matrix_markdown,
    render_score_card,
    timeline_fig,
    scatter_fig,
    confusion_matrix_fig,
    render_lloyds_checklist,
)
from gad.engine.pdf_export import generate_lloyds_report

ROOT = Path(__file__).resolve().parent.parent.parent
SCHEMA_EXAMPLES = ROOT / "schema" / "examples"
DATA_SERIES = ROOT / "data" / "series"
EXAMPLE_TO_CSV = {
    "kenya-drought-chirps": DATA_SERIES / "kenya_drought.csv",
    "flight-delay-indigo": DATA_SERIES / "flight_delay_indigo.csv",
    "india-flood-imd": DATA_SERIES / "india_flood_imd.csv",
}

PERIL_CONFIG = {
    "flight_delay": {"label": "Flight delay", "icon": "✈", "unit": "minutes", "default_threshold": 60.0, "hint": "Payout when flight arrives more than X minutes late.", "data_source": "DGCA API + OpenSky"},
    "drought": {"label": "Drought", "icon": "☀", "unit": "mm rainfall in 30 days", "default_threshold": 50.0, "hint": "Payout when 30-day rainfall falls below X mm.", "data_source": "CHIRPS v2.0"},
    "flood": {"label": "Flood", "icon": "🌊", "unit": "mm rainfall in 24 hours", "default_threshold": 150.0, "hint": "Payout when 24-hour rainfall exceeds X mm.", "data_source": "IMD gridded rainfall"},
    "wind": {"label": "Wind", "icon": "💨", "unit": "knots", "default_threshold": 50.0, "hint": "Payout when wind speed exceeds X knots.", "data_source": "NOAA / ERA5"},
    "earthquake": {"label": "Earthquake", "icon": "🌍", "unit": "MMI intensity", "default_threshold": 6.0, "hint": "Payout when MMI exceeds X at location.", "data_source": "USGS ShakeMap"},
}


def _load_sample_csv(stem: str) -> list[dict]:
    csv_path = EXAMPLE_TO_CSV.get(stem)
    if not csv_path or not csv_path.is_file():
        raise FileNotFoundError(f"Sample data not found for {stem}")
    return load_weather_data_from_csv(csv_path)


def get_weather_data_for_trigger(trigger: TriggerDef) -> tuple[list[dict], str]:
    """
    Returns (weather_data, source_label).
    Falls back to sample CSV if live fetch fails.
    """
    if trigger.peril in ("drought", "flood"):
        try:
            lat = float(trigger.geography["coordinates"][1])
            lon = float(trigger.geography["coordinates"][0])
            weather_data = fetch_chirps_series(
                lat=lat,
                lon=lon,
                years=list(range(2010, 2024)),
                threshold=trigger.threshold,
                fires_when_above=trigger.trigger_fires_when_above,
            )
            return weather_data, f"CHIRPS v2.0 live data ({lat:.2f}°, {lon:.2f}°)"
        except PipelineError as e:
            return _load_sample_csv("kenya-drought-chirps"), f"Sample data (live fetch failed: {e})"

    return _load_sample_csv("kenya-drought-chirps"), "Illustrative sample data (Kenya drought series)"


def main():
    st.set_page_config(page_title="Build trigger | GAD", layout="wide")
    session_id = get_or_create_session_id()
    user = current_user()
    user_id = UUID(str(user.id)) if user and getattr(user, "id", None) else None

    st.markdown("## Build a trigger")
    st.caption("Four steps. Plain English. About 60 seconds.")

    step = st.session_state.get("wizard_step", 1)
    st.progress(step / 4, text=f"Step {step} of 4")
    st.divider()

    if step == 1:
        st.markdown("### What are you covering?")
        cols = st.columns(5)
        for i, (peril_key, config) in enumerate(PERIL_CONFIG.items()):
            with cols[i]:
                if st.button(f"{config['icon']}\n\n{config['label']}", key=f"peril_{peril_key}", use_container_width=True):
                    st.session_state["wizard_peril"] = peril_key
                    st.session_state["wizard_step"] = 2
                    track("wizard_peril_selected", session_id, user_id=user_id, metadata={"peril": peril_key})
                    st.rerun()

    elif step == 2:
        peril = st.session_state.get("wizard_peril", "drought")
        config = PERIL_CONFIG[peril]
        st.markdown(f"### Where? ({config['icon']} {config['label']})")
        st.caption(config["hint"])
        location_name = st.text_input("Location name", placeholder="e.g. Marsabit, Bengaluru")
        lat = st.number_input("Latitude", value=2.3284, format="%.4f")
        lon = st.number_input("Longitude", value=37.9899, format="%.4f")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Back", use_container_width=True):
                st.session_state["wizard_step"] = 1
                st.rerun()
        with col2:
            if st.button("Next", use_container_width=True, type="primary"):
                st.session_state["wizard_location"] = {"name": location_name or "Location", "lat": lat, "lon": lon}
                st.session_state["wizard_step"] = 3
                st.rerun()

    elif step == 3:
        peril = st.session_state.get("wizard_peril", "drought")
        config = PERIL_CONFIG[peril]
        st.markdown("### When should the payout trigger?")
        st.caption(config["hint"])
        threshold = st.number_input(f"Threshold ({config['unit']})", value=float(config["default_threshold"]), min_value=0.0)
        st.info(f"Payout triggers when **{peril.replace('_', ' ')}** exceeds **{threshold} {config['unit']}** at the selected location.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Back", use_container_width=True):
                st.session_state["wizard_step"] = 2
                st.rerun()
        with col2:
            if st.button("Compute basis risk", use_container_width=True, type="primary"):
                st.session_state["wizard_threshold"] = threshold
                st.session_state["wizard_step"] = 4
                st.rerun()

    elif step == 4:
        peril = st.session_state.get("wizard_peril", "drought")
        config = PERIL_CONFIG[peril]
        loc = st.session_state.get("wizard_location", {"name": "Location", "lat": 2.33, "lon": 37.99})
        threshold = st.session_state.get("wizard_threshold", 50.0)
        trigger = TriggerDef(
            name=f"{config['label']} — {loc['name']}",
            description=f"Parametric trigger: payout when {peril.replace('_', ' ')} exceeds {threshold} {config['unit']} at {loc['name']}.",
            peril=peril,
            threshold=threshold,
            threshold_unit=config["unit"],
            data_source=config["data_source"],
            geography={"type": "Point", "coordinates": [loc["lon"], loc["lat"]]},
            provenance=DataSourceProvenance(
                primary_source=config["data_source"],
                primary_url="https://oracle.parametricdata.io/sources",
                max_data_latency_seconds=300,
                historical_years_available=30,
            ),
            created_by=user_id,
        )
        st.markdown("### Your trigger")
        st.markdown(f"**{trigger.name}**")
        st.markdown(trigger.description)
        if st.toggle("Show YAML (for developers)"):
            st.code(trigger.model_dump_json(indent=2), language="json")
            track("yaml_toggled", session_id, user_id=user_id, trigger_id=trigger.trigger_id)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Back", use_container_width=True):
                st.session_state["wizard_step"] = 3
                st.rerun()
        with col2:
            if st.button("Compute basis risk", use_container_width=True, type="primary"):
                try:
                    weather_data, source_label = get_weather_data_for_trigger(trigger)
                    report = compute_basis_risk(trigger, weather_data)
                    st.session_state["wizard_report"] = report
                    st.session_state["wizard_trigger"] = trigger
                    st.session_state["wizard_source_label"] = source_label
                    track("report_computed", session_id, user_id=user_id, trigger_id=trigger.trigger_id, report_id=report.report_id)
                except Exception as e:
                    st.error(str(e))
                st.rerun()

        if st.session_state.get("wizard_report") and st.session_state.get("wizard_trigger"):
            report = st.session_state["wizard_report"]
            trigger = st.session_state["wizard_trigger"]
            source_label = st.session_state.get("wizard_source_label", "Unknown data source")
            st.markdown(
                '<div style="background:#1e3a5f;border:1px solid #3b82f6;border-radius:6px;padding:12px 16px;margin-bottom:16px;">'
                f'<strong>Data source: {source_label}</strong><br/>'
                '<span style="color:#94a3b8;font-size:0.9em;">Your trigger definition (<b>' + trigger.name + '</b>) is unchanged. '
                'Live-source failures degrade gracefully to sample data.</span>'
                '</div>',
                unsafe_allow_html=True,
            )
            render_score_card(report)
            c1, c2 = st.columns(2)
            with c1:
                st.plotly_chart(timeline_fig(report), use_container_width=True, config={"displayModeBar": False})
                st.caption(chart_summary(report))
            with c2:
                st.plotly_chart(scatter_fig(report), use_container_width=True, config={"displayModeBar": False})
                st.caption(chart_summary(report))
            st.plotly_chart(confusion_matrix_fig(report), use_container_width=True, config={"displayModeBar": False})
            st.caption(chart_summary(report))
            st.markdown(confusion_matrix_markdown(report))
            render_lloyds_checklist(report)
            pdf_bytes = generate_lloyds_report(trigger, report)
            st.download_button("Download Lloyd's PDF", data=pdf_bytes, file_name=f"gad_report_{trigger.trigger_id}.pdf", mime="application/pdf")
            track("report_downloaded_pdf", session_id, user_id=user_id, report_id=report.report_id, metadata={"trigger_id": str(trigger.trigger_id)})


if __name__ == "__main__":
    main()

# ── Footer ──
from dashboard.components.footer import render_footer
render_footer()
