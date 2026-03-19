"""Score card: ρ, CI, Lloyd's pass rate."""

from __future__ import annotations

import streamlit as st

from gad.engine.models import BasisRiskReport

COLORS = {
    "green": "#10b981",
    "amber": "#f59e0b",
    "red": "#ef4444",
    "muted": "#6b7280",
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
        f'<div style="background:#111827;border:1px solid #1f2937;border-radius:6px;padding:1rem 1.25rem;margin-bottom:0.75rem;">'
        f'<div style="font-family:JetBrains Mono,monospace;font-size:0.75rem;color:#6b7280;">HEADLINE SPEARMAN</div>'
        f'<div style="font-family:JetBrains Mono,monospace;font-size:2rem;font-weight:600;color:{color};">ρ = {rho:.3f}</div>'
        f'<div style="font-family:JetBrains Mono,monospace;color:#6b7280;">95% CI [{report.spearman_ci_lower:.3f}, {report.spearman_ci_upper:.3f}]</div>'
        f'<div style="font-family:JetBrains Mono,monospace;margin-top:8px;">Lloyd\'s {passing}/{total}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )
