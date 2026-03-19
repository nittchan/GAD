"""Full basis risk profile for one trigger. Auto-loads sample on first visit."""

from pathlib import Path
from uuid import UUID

import streamlit as st
import yaml
from pydantic import ValidationError

from gad.engine import TriggerDef, compute_basis_risk
from gad.engine.loader import load_weather_data_from_csv
from gad.engine.models import BasisRiskReport
from gad.engine.analytics import track, get_or_create_session_id
from dashboard.components.auth import current_user
from dashboard.components import (
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


@st.cache_data(show_spinner=False)
def cached_report(example_stem: str) -> tuple[BasisRiskReport, TriggerDef]:
    yaml_path = SCHEMA_EXAMPLES / f"{example_stem}.yaml"
    if not yaml_path.is_file():
        raise FileNotFoundError(str(yaml_path))
    raw = yaml.safe_load(yaml_path.read_text())
    trigger = TriggerDef.model_validate(raw)
    csv_path = EXAMPLE_TO_CSV.get(example_stem)
    if not csv_path or not csv_path.is_file():
        raise FileNotFoundError(f"No CSV for {example_stem}")
    weather_data = load_weather_data_from_csv(csv_path)
    report = compute_basis_risk(trigger, weather_data)
    return report, trigger


def main():
    st.set_page_config(page_title="Trigger profile | GAD", layout="wide")
    session_id = get_or_create_session_id()
    user = current_user()
    user_id = UUID(str(user.id)) if user and getattr(user, "id", None) else None

    examples = list(SCHEMA_EXAMPLES.glob("*.yaml")) if SCHEMA_EXAMPLES.is_dir() else []
    stems = [p.stem for p in examples]
    default = "kenya-drought-chirps" if "kenya-drought-chirps" in stems else (stems[0] if stems else None)

    load_sample = st.session_state.get("load_sample")
    if load_sample and load_sample in stems:
        selected = load_sample
        del st.session_state["load_sample"]
    else:
        selected = st.sidebar.selectbox("Trigger", stems, index=stems.index(default) if default and default in stems else 0)

    if not selected:
        st.info("No schema examples found. Add YAMLs under schema/examples/.")
        return

    try:
        report, trigger = cached_report(selected)
        track("trigger_viewed", session_id, user_id=user_id, trigger_id=trigger.trigger_id)
    except (FileNotFoundError, ValidationError) as e:
        st.error(str(e))
        return

    st.markdown(f"### {trigger.name}")
    if trigger.description:
        st.caption(trigger.description)
    st.caption(f"{trigger.peril} · {trigger.threshold} {trigger.threshold_unit}")
    render_score_card(report)
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(timeline_fig(report), use_container_width=True, config={"displayModeBar": False})
    with c2:
        st.plotly_chart(scatter_fig(report), use_container_width=True, config={"displayModeBar": False})
    st.plotly_chart(confusion_matrix_fig(report), use_container_width=True, config={"displayModeBar": False})
    render_lloyds_checklist(report)
    with st.expander("Methodology", expanded=False):
        st.markdown(
            "Spearman rank correlation between trigger index and loss proxy. "
            "Bootstrap 95% CI. Lloyd's checklist: basis risk quantified, FPR/FNR limits, "
            "data source documented, independent verifiable."
        )
    pdf_bytes = generate_lloyds_report(trigger, report)
    st.download_button(
        "Download Lloyd's PDF",
        data=pdf_bytes,
        file_name=f"gad_report_{trigger.trigger_id}.pdf",
        mime="application/pdf",
    )


if __name__ == "__main__":
    main()
