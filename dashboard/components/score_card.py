"""Score card: ρ, CI, Lloyd's pass rate — parchment theme."""

from __future__ import annotations

import streamlit as st

from gad.engine.models import BasisRiskReport

COLORS = {
    "green": "#2E8B6F",   # verdigris
    "amber": "#D4A017",   # signal amber
    "red": "#A63D40",     # deep carmine
    "muted": "#9B9286",   # warm gray
}


def rho_color(rho: float) -> str:
    if rho >= 0.7:
        return COLORS["green"]
    if rho >= 0.4:
        return COLORS["amber"]
    return COLORS["red"]


def render_score_card(report: BasisRiskReport) -> None:
    rho = report.spearman_rho
    color = rho_color(rho) if (rho is not None and not (rho != rho)) else COLORS["muted"]
    passing = sum(1 for v in report.lloyds_detail.values() if v.get("pass") is True)
    total = sum(1 for v in report.lloyds_detail.values() if v.get("pass") is not None)
    st.markdown(
        f'<div style="background:#EDE7E0;border:1px solid #D4CCC0;border-radius:6px;padding:1rem 1.25rem;margin-bottom:0.75rem;">'
        f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:11px;font-weight:500;color:#7A7267;text-transform:uppercase;letter-spacing:0.08em;font-variant-numeric:tabular-nums;">HEADLINE SPEARMAN</div>'
        f'<div title="Spearman correlation headline value" style="font-family:\'JetBrains Mono\',monospace;font-size:2rem;font-weight:600;color:{color};font-variant-numeric:tabular-nums;">ρ = {rho:.3f}</div>'
        f'<div style="font-family:\'JetBrains Mono\',monospace;color:#7A7267;font-size:14px;font-variant-numeric:tabular-nums;">95% CI [{report.spearman_ci_lower:.3f}, {report.spearman_ci_upper:.3f}]</div>'
        f'<div style="font-family:\'JetBrains Mono\',monospace;margin-top:8px;color:#7A2E1F;font-variant-numeric:tabular-nums;">Lloyd\'s {passing}/{total}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )
