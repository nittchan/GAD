"""Lloyd's checklist with semantic left border — parchment theme."""

from __future__ import annotations

import streamlit as st

from gad.engine.models import BasisRiskReport


def render_lloyds_checklist(report: BasisRiskReport) -> None:
    st.subheader("Lloyd's checklist")
    detail = report.lloyds_detail
    for criterion, data in detail.items():
        passed = data.get("pass")
        reason = data.get("reason", "Cannot evaluate")
        if passed is True:
            border_color = "#2E8B6F"  # verdigris
            badge = "PASS"
            badge_color = "#2E8B6F"
        elif passed is False:
            border_color = "#A63D40"  # carmine
            badge = "FAIL"
            badge_color = "#A63D40"
        else:
            border_color = "#D4A017"  # amber
            badge = "?"
            badge_color = "#D4A017"
        st.markdown(
            f'<div style="border-left:4px solid {border_color}; '
            f'padding:8px 12px; margin-bottom:4px; background:#EDE7E0;">'
            f'<span style="color:{badge_color};font-weight:700;'
            f"font-family:'JetBrains Mono',monospace;font-size:11px;"
            f'font-variant-numeric:tabular-nums;">'
            f'{badge}</span> '
            f'<span style="color:#1E1B18;font-size:13px;font-family:\'Instrument Sans\',sans-serif;">'
            f'{criterion.replace("_", " ").title()}</span><br>'
            f'<span style="color:#7A7267;font-size:11px;font-family:\'Instrument Sans\',sans-serif;">{reason}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
