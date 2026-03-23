"""Lloyd's checklist with red left border on fails."""

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
            border_color = "#059669"
            badge = "PASS"
            badge_color = "#059669"
        elif passed is False:
            border_color = "#dc2626"
            badge = "FAIL"
            badge_color = "#dc2626"
        else:
            border_color = "#d97706"
            badge = "?"
            badge_color = "#d97706"
        st.markdown(
            f'<div style="border-left:3px solid {border_color}; '
            f'padding:8px 12px; margin-bottom:4px; background:#111827;">'
            f'<span style="color:{badge_color};font-weight:700;'
            f'font-family:\'JetBrains Mono\',monospace;font-size:11px;">'
            f'{badge}</span> '
            f'<span style="color:#f9fafb;font-size:13px;">'
            f'{criterion.replace("_", " ").title()}</span><br>'
            f'<span style="color:#6b7280;font-size:11px;">{reason}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
