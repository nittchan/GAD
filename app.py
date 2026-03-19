"""
GAD — Global Actuarial Dashboard (Streamlit Phase 1).
"""

# DEPRECATED: use dashboard/app.py

from __future__ import annotations

from pathlib import Path

import plotly.graph_objects as go
import streamlit as st
import yaml
from plotly.subplots import make_subplots
from pydantic import ValidationError

from gad._engine_legacy import compute_basis_risk
from gad._io_legacy import discover_triggers, load_data_manifest, load_trigger_def
from gad._models_legacy import BasisRiskReport, TriggerDef
from gad.pdf_export import build_pdf
from gad.pipeline import build_chirps_series_for_trigger, make_live_manifest
from gad.registry import Registry, get_report, get_trigger, list_trigger_ids_with_reports, save_report, upsert_trigger

DATA_DIR = Path(__file__).resolve().parent / "data"
TRIGGERS_DIR = DATA_DIR / "triggers"
MANIFEST_PATH = DATA_DIR / "manifest.yaml"
REGISTRY_PATH = DATA_DIR / "gad_registry.db"
CHIRPS_CACHE_DIR = DATA_DIR / "cache" / "chirps"

# Bloomberg-ish dark tokens
CSS = """
<style>
    .stApp { background-color: #0d1117; color: #e6edf3; }
    .gad-header { font-family: ui-sans-serif, system-ui; letter-spacing: -0.02em; }
    .gad-mono { font-family: "JetBrains Mono", "Fira Code", ui-monospace, monospace; }
    .score-card {
        background: #161b22; border: 1px solid #30363d; border-radius: 6px;
        padding: 1rem 1.25rem; margin-bottom: 0.75rem;
    }
    .rho-green { color: #3fb950; }
    .rho-amber { color: #d29922; }
    .rho-red { color: #f85149; }
    .lloyd-fail { border-left: 4px solid #f85149; padding-left: 12px; margin: 6px 0; }
    .lloyd-pass { border-left: 4px solid #3fb950; padding-left: 12px; margin: 6px 0; }
</style>
"""


def rho_class(rho: float) -> str:
    a = abs(rho)
    if a > 0.7:
        return "rho-green"
    if a >= 0.4:
        return "rho-amber"
    return "rho-red"


@st.cache_data(show_spinner=False)
def cached_manifest():
    return load_data_manifest(MANIFEST_PATH)


@st.cache_data(show_spinner=False)
def cached_report(trigger_path: str):
    manifest = cached_manifest()
    trigger = load_trigger_def(trigger_path)
    return compute_basis_risk(trigger, manifest, DATA_DIR), trigger


def load_trigger_list() -> list[Path]:
    return discover_triggers(TRIGGERS_DIR)


def try_parse_trigger_yaml(text: str) -> TriggerDef:
    raw = yaml.safe_load(text)
    if not isinstance(raw, dict):
        raise ValueError("YAML root must be a mapping.")
    return TriggerDef.model_validate(raw)


def confusion_matrix_fig(c) -> go.Figure:
    z = [[c.true_negative, c.false_positive], [c.false_negative, c.true_positive]]
    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=["Loss no", "Loss yes"],
            y=["Trigger no", "Trigger yes"],
            colorscale=[[0, "#21262d"], [1, "#238636"]],
            showscale=False,
            text=[[str(z[0][0]), str(z[0][1])], [str(z[1][0]), str(z[1][1])]],
            texttemplate="%{text}",
            textfont={"color": "#e6edf3", "size": 14},
        )
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0d1117",
        plot_bgcolor="#0d1117",
        margin=dict(l=40, r=20, t=40, b=40),
        title="Confusion (period-level)",
        height=280,
    )
    return fig


def timeline_fig(report: BasisRiskReport) -> go.Figure:
    rows = report.backtest.rows
    periods = [r.period for r in rows]
    fire = [1 if r.trigger_fired else 0 for r in rows]
    loss = [1 if r.loss_occurred else 0 for r in rows]
    mismatch = [1 if (r.trigger_fired != r.loss_occurred) else 0 for r in rows]
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.2, 0.2, 0.2], vertical_spacing=0.08)
    fig.add_trace(
        go.Bar(x=periods, y=fire, name="Trigger fired", marker_color="#58a6ff", showlegend=True),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Bar(x=periods, y=loss, name="Loss event", marker_color="#a371f7", showlegend=True),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Bar(x=periods, y=mismatch, name="Mismatch", marker_color="#f85149", showlegend=True),
        row=3,
        col=1,
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0d1117",
        plot_bgcolor="#0d1117",
        height=320,
        margin=dict(l=40, r=20, t=30, b=40),
        barmode="overlay",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    fig.update_yaxes(range=[0, 1.05], row=1, col=1)
    fig.update_yaxes(range=[0, 1.05], row=2, col=1)
    fig.update_yaxes(range=[0, 1.05], row=3, col=1)
    return fig


def scatter_fig(report: BasisRiskReport) -> go.Figure:
    rows = report.backtest.rows
    x = [r.index_value for r in rows]
    y = [1.0 if r.loss_occurred else 0.0 for r in rows]
    colors = []
    for r in rows:
        if r.trigger_fired and r.loss_occurred:
            colors.append("#3fb950")
        elif r.trigger_fired and not r.loss_occurred:
            colors.append("#f85149")
        elif not r.trigger_fired and r.loss_occurred:
            colors.append("#d29922")
        else:
            colors.append("#484f58")
    fig = go.Figure(
        go.Scatter(
            x=x,
            y=y,
            mode="markers",
            marker=dict(size=10, color=colors),
            name="periods",
        )
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0d1117",
        plot_bgcolor="#0d1117",
        height=360,
        margin=dict(l=40, r=20, t=40, b=40),
        title="Index vs loss (quadrant colors: TP green, FP red, FN amber, TN gray)",
        xaxis_title="Hazard index",
        yaxis_title="Loss occurred",
    )
    fig.update_yaxes(range=[-0.1, 1.1])
    return fig


def render_score_card(report: BasisRiskReport):
    rc = rho_class(report.headline_rho)
    st.markdown(
        f"""
        <div class="score-card">
            <div class="gad-mono" style="font-size:0.75rem;color:#8b949e;">HEADLINE SPEARMAN ({report.headline_label})</div>
            <div class="gad-mono {rc}" style="font-size:2rem;font-weight:600;">ρ = {report.headline_rho:.3f}</div>
            <div class="gad-mono" style="color:#8b949e;">95% bootstrap CI [{report.headline_ci_low:.3f}, {report.headline_ci_high:.3f}]</div>
            <div class="gad-mono" style="margin-top:8px;">Lloyd's pass rate: <b>{report.lloyds.passed_count}/{report.lloyds.total_count}</b></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.expander("P-value and secondary Spearman blocks", expanded=False):
        st.markdown(
            f"**Headline p-value:** `{report.headline_p_value:.4g}`  \n"
            f"**Spatial ρ** = `{report.spearman_spatial.rho:.3f}` (n={report.spearman_spatial.n})  \n"
        )
        if report.spearman_loss_proxy:
            lp = report.spearman_loss_proxy
            st.markdown(f"**Loss-proxy ρ** = `{lp.rho:.3f}` (n={lp.n})")
        else:
            st.markdown("_Loss-proxy Spearman omitted (constant proxy)._")


def render_lloyds(report: BasisRiskReport):
    st.subheader("Lloyd's-style checklist (Phase 1)")
    for c in report.lloyds.criteria:
        badge = "PASS" if c.passed else "FAIL"
        cls = "lloyd-pass" if c.passed else "lloyd-fail"
        st.markdown(
            f'<div class="{cls}"><span class="gad-mono">{c.criterion_id}</span> — <b>{c.name}</b> '
            f'<span class="gad-mono">[{badge}]</span><br/><span style="color:#8b949e">{c.explanation}</span></div>',
            unsafe_allow_html=True,
        )


def render_panel(path: Path | None = None, report: BasisRiskReport | None = None, trigger: TriggerDef | None = None):
    if path is not None:
        report, trigger = cached_report(str(path))
    elif report is not None and trigger is not None:
        pass
    else:
        raise ValueError("Provide path or (report, trigger)")
    st.markdown(f"### {trigger.name}")
    st.caption(f"`{trigger.id}` · {trigger.peril.value} · {trigger.variable}")
    for w in report.warnings:
        st.warning(w)
    render_score_card(report)
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(timeline_fig(report), use_container_width=True, config={"displayModeBar": False})
    with c2:
        st.plotly_chart(scatter_fig(report), use_container_width=True, config={"displayModeBar": False})
    st.plotly_chart(
        confusion_matrix_fig(report.backtest.confusion),
        use_container_width=True,
        config={"displayModeBar": False},
    )
    render_lloyds(report)
    st.download_button(
        "Download PDF report",
        data=build_pdf(report, trigger),
        file_name=f"gad_report_{trigger.id}.pdf",
        mime="application/pdf",
    )
    with st.expander("Methodology (Phase 1)", expanded=False):
        st.markdown(
            """
            - **Spatial basis risk:** Spearman rank correlation between the index station value and an open-data
              regional reference series (bundled CSV columns `index_value` vs `spatial_ref`).
            - **Loss alignment:** When `loss_proxy` varies, Spearman ρ vs `loss_proxy`; otherwise headline falls back
              to spatial basis.
            - **Back-test:** Period-level trigger fired vs `loss_event` binary labels from open proxies (synthetic demo).
            - **Lloyd's checklist:** Deterministic Phase-1 underwriting-style gates; not a substitute for formal filing.
            """
        )


def main():
    st.set_page_config(page_title="GAD", layout="wide", initial_sidebar_state="expanded")
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        '<p class="gad-header" style="font-size:1.75rem;font-weight:700;margin-bottom:0;">GAD</p>'
        '<p style="color:#8b949e;margin-top:0;">Global Actuarial Dashboard · parametric basis risk (open data, Phase 1)</p>',
        unsafe_allow_html=True,
    )

    paths = load_trigger_list()
    id_to_path = {p.stem: p for p in paths}
    if not paths:
        st.error(f"No triggers found under `{TRIGGERS_DIR}`.")
        return

    st.sidebar.markdown("### Trigger source")
    source = st.sidebar.radio("Load triggers from", ["YAML files", "Registry"], horizontal=True)

    if source == "YAML files":
        st.sidebar.markdown("### Triggers")
        default_ids = ["kenya_drought"] if "kenya_drought" in id_to_path else [paths[0].stem]
        choice = st.sidebar.multiselect(
            "Select up to two for comparison",
            options=sorted(id_to_path.keys()),
            default=default_ids,
            max_selections=2,
        )
        reg_choice = None
    else:
        with Registry(REGISTRY_PATH) as conn:
            reg_ids = list_trigger_ids_with_reports(conn)
        if not reg_ids:
            st.sidebar.info("No triggers in registry. Compute from YAML, then use **Save to registry**.")
            choice = []
            reg_choice = None
        else:
            st.sidebar.markdown("### Registry triggers")
            reg_choice = st.sidebar.multiselect(
                "Select up to two",
                options=sorted(reg_ids),
                default=[reg_ids[0]] if reg_ids else [],
                max_selections=2,
            )
            choice = reg_choice or []

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Upload YAML")
    uploaded = st.sidebar.text_area(
        "Paste trigger definition (validated; must exist in manifest)",
        height=180,
        placeholder="id: my_trigger\nname: ...",
    )
    if st.sidebar.button("Validate uploaded YAML"):
        try:
            trig = try_parse_trigger_yaml(uploaded)
            manifest = cached_manifest()
            if trig.id not in manifest.triggers:
                st.sidebar.error(f"id `{trig.id}` not in data/manifest.yaml — add a series mapping first.")
            else:
                st.sidebar.success(f"Valid: `{trig.id}` — select it in the list to compute.")
        except (ValueError, yaml.YAMLError, ValidationError) as e:
            st.sidebar.error(f"Validation error: {e}")

    if source == "YAML files" and choice and len(choice) == 1:
        report, trigger = cached_report(str(id_to_path[choice[0]]))
        if st.sidebar.button("Save to registry"):
            with Registry(REGISTRY_PATH) as conn:
                upsert_trigger(conn, trigger)
                save_report(conn, trigger.id, report)
            st.sidebar.success(f"Saved `{trigger.id}` to registry.")

    if not choice:
        st.info("Select at least one trigger in the sidebar.")
        return

    if source == "YAML files":
        if len(choice) == 1:
            data_source = st.radio(
                "Data source",
                ["Preset", "Live CHIRPS"],
                horizontal=True,
                help="Preset uses bundled CSVs; Live CHIRPS fetches from CHIRPS 2.0 and computes basis risk.",
            )
            if data_source == "Preset":
                render_panel(path=id_to_path[choice[0]])
            else:
                trigger = load_trigger_def(id_to_path[choice[0]])
                try:
                    with st.spinner("Fetching CHIRPS…"):
                        series_path = build_chirps_series_for_trigger(
                            trigger, cache_dir=CHIRPS_CACHE_DIR
                        )
                    manifest = make_live_manifest(trigger.id, series_path, DATA_DIR)
                    with st.spinner("Computing basis risk…"):
                        report = compute_basis_risk(trigger, manifest, DATA_DIR)
                    st.caption(
                        "Live CHIRPS: spatial ref = index (no regional mean). "
                        "Loss proxy = 0 (not from CHIRPS)."
                    )
                    render_panel(report=report, trigger=trigger)
                except Exception as e:
                    st.error(f"Live data failed: {e}")
                    st.info("Showing preset data instead.")
                    render_panel(path=id_to_path[choice[0]])
        else:
            a, b = choice[0], choice[1]
            col1, col2 = st.columns(2)
            with col1:
                render_panel(path=id_to_path[a])
            with col2:
                render_panel(path=id_to_path[b])
            r1, t1 = cached_report(str(id_to_path[a]))
            r2, t2 = cached_report(str(id_to_path[b]))
            st.markdown("#### Comparison deltas")
            d_rho = r2.headline_rho - r1.headline_rho
            d_l = r2.lloyds.passed_count - r1.lloyds.passed_count
            st.markdown(
                f"| | `{t1.id}` | `{t2.id}` | Δ (2−1) |\n"
                f"|---|---:|---:|---:|\n"
                f"| Headline ρ | {r1.headline_rho:.3f} | {r2.headline_rho:.3f} | {d_rho:+.3f} |\n"
                f"| Lloyd's passes | {r1.lloyds.passed_count} | {r2.lloyds.passed_count} | {d_l:+d} |\n"
            )
    else:
        with Registry(REGISTRY_PATH) as conn:
            if len(choice) == 1:
                t = get_trigger(conn, choice[0])
                r = get_report(conn, choice[0])
                if t is not None and r is not None:
                    render_panel(report=r, trigger=t)
                else:
                    st.error("Trigger or report missing in registry.")
            else:
                a, b = choice[0], choice[1]
                t1, t2 = get_trigger(conn, a), get_trigger(conn, b)
                r1, r2 = get_report(conn, a), get_report(conn, b)
                if all(x is not None for x in (t1, t2, r1, r2)):
                    col1, col2 = st.columns(2)
                    with col1:
                        render_panel(report=r1, trigger=t1)
                    with col2:
                        render_panel(report=r2, trigger=t2)
                    st.markdown("#### Comparison deltas")
                    d_rho = r2.headline_rho - r1.headline_rho
                    d_l = r2.lloyds.passed_count - r1.lloyds.passed_count
                    st.markdown(
                        f"| | `{t1.id}` | `{t2.id}` | Δ (2−1) |\n"
                        f"|---|---:|---:|---:|\n"
                        f"| Headline ρ | {r1.headline_rho:.3f} | {r2.headline_rho:.3f} | {d_rho:+.3f} |\n"
                        f"| Lloyd's passes | {r1.lloyds.passed_count} | {r2.lloyds.passed_count} | {d_l:+d} |\n"
                    )
                else:
                    st.error("One or more triggers/reports missing in registry.")


if __name__ == "__main__":
    main()
