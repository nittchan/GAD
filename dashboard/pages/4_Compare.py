"""Side-by-side comparison (max 2 triggers)."""

from pathlib import Path

import streamlit as st
import yaml
from pydantic import ValidationError

from gad.engine import TriggerDef, compute_basis_risk
from gad.engine.loader import load_weather_data_from_csv
from gad.engine.models import BasisRiskReport
from dashboard.components import (
    chart_summary,
    render_score_card,
    timeline_fig,
    scatter_fig,
    confusion_matrix_fig,
    render_lloyds_checklist,
)

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
    raw = yaml.safe_load(yaml_path.read_text())
    trigger = TriggerDef.model_validate(raw)
    weather_data = load_weather_data_from_csv(EXAMPLE_TO_CSV[example_stem])
    report = compute_basis_risk(trigger, weather_data)
    return report, trigger


def main():
    st.set_page_config(page_title="Compare | GAD", layout="wide")
    examples = list(SCHEMA_EXAMPLES.glob("*.yaml")) if SCHEMA_EXAMPLES.is_dir() else []
    stems = [p.stem for p in examples]
    if len(stems) < 2:
        st.info("Add at least two triggers in schema/examples/ to compare.")
        return
    choice = st.sidebar.multiselect("Select two triggers", options=stems, default=stems[:2], max_selections=2)
    if len(choice) != 2:
        st.info("Select exactly two triggers in the sidebar.")
        return
    try:
        r1, t1 = cached_report(choice[0])
        r2, t2 = cached_report(choice[1])
    except (FileNotFoundError, ValidationError) as e:
        st.error(str(e))
        return
    col1, col2 = st.columns(2)
    with col1:
        render_score_card(r1)
        st.plotly_chart(timeline_fig(r1), use_container_width=True, config={"displayModeBar": False})
        st.caption(chart_summary(r1))
        st.plotly_chart(scatter_fig(r1), use_container_width=True, config={"displayModeBar": False})
        st.caption(chart_summary(r1))
        render_lloyds_checklist(r1)
    with col2:
        render_score_card(r2)
        st.plotly_chart(timeline_fig(r2), use_container_width=True, config={"displayModeBar": False})
        st.caption(chart_summary(r2))
        st.plotly_chart(scatter_fig(r2), use_container_width=True, config={"displayModeBar": False})
        st.caption(chart_summary(r2))
        render_lloyds_checklist(r2)
    st.markdown("#### Comparison")
    st.markdown(
        f"| | {t1.name} | {t2.name} | Δ |\n"
        f"|---|---:|---:|---:|\n"
        f"| ρ | {r1.spearman_rho:.3f} | {r2.spearman_rho:.3f} | {r2.spearman_rho - r1.spearman_rho:+.3f} |\n"
        f"| Lloyd's score | {r1.lloyds_score:.2f} | {r2.lloyds_score:.2f} | {r2.lloyds_score - r1.lloyds_score:+.2f} |\n"
    )


if __name__ == "__main__":
    main()

# ── Footer ──
from dashboard.components.footer import render_footer
render_footer()
