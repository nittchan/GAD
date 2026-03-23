"""Expert mode — YAML editor, full schema control."""

from pathlib import Path

import streamlit as st
import yaml
from pydantic import ValidationError

from gad.engine import TriggerDef, compute_basis_risk
from gad.engine.loader import load_weather_data_from_csv
from gad.engine.models import BasisRiskReport
from gad.engine.analytics import track, get_or_create_session_id
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


def main():
    st.set_page_config(page_title="Expert mode | GAD", layout="wide")
    session_id = get_or_create_session_id()
    user = current_user()

    st.markdown("## Expert mode")
    st.caption("Edit trigger YAML. Full schema control. Same engine as guided mode.")

    examples = list(SCHEMA_EXAMPLES.glob("*.yaml")) if SCHEMA_EXAMPLES.is_dir() else []
    stems = [p.stem for p in examples]
    default_yaml = ""
    if stems:
        default_stem = "kenya-drought-chirps" if "kenya-drought-chirps" in stems else stems[0]
        default_yaml = (SCHEMA_EXAMPLES / f"{default_stem}.yaml").read_text()

    yaml_text = st.text_area(
        "Trigger YAML",
        value=st.session_state.get("expert_yaml", default_yaml),
        height=280,
        key="expert_yaml_editor",
    )
    st.session_state["expert_yaml"] = yaml_text

    if st.button("Validate and compute"):
        try:
            raw = yaml.safe_load(yaml_text)
            if not isinstance(raw, dict):
                st.error("YAML root must be a mapping.")
                return
            trigger = TriggerDef.model_validate(raw)
            st.success(f"Valid: **{trigger.name}**")
            example_stem = None
            for s in stems:
                p = SCHEMA_EXAMPLES / f"{s}.yaml"
                if p.read_text().strip() == yaml_text.strip():
                    example_stem = s
                    break
            if not example_stem and stems:
                example_stem = "kenya-drought-chirps"
            if example_stem and EXAMPLE_TO_CSV.get(example_stem) and (EXAMPLE_TO_CSV[example_stem]).is_file():
                weather_data = load_weather_data_from_csv(EXAMPLE_TO_CSV[example_stem])
                report = compute_basis_risk(trigger, weather_data)
                track("report_computed", session_id, trigger_id=trigger.trigger_id, report_id=report.report_id)
                st.session_state["expert_report"] = report
                st.session_state["expert_trigger"] = trigger
            else:
                st.warning("No CSV mapped for this trigger. Use a schema example or add data.")
        except ValidationError as e:
            st.error(f"Validation: {e}")
        except Exception as e:
            st.error(str(e))

    if st.session_state.get("expert_report") and st.session_state.get("expert_trigger"):
        report = st.session_state["expert_report"]
        trigger = st.session_state["expert_trigger"]
        st.divider()
        st.markdown(f"### {trigger.name}")
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


if __name__ == "__main__":
    main()
