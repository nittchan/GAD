"""Lloyd's checklist with red left border on fails."""

from __future__ import annotations

import streamlit as st

from gad.engine.models import BasisRiskReport


def render_lloyds_checklist(report: BasisRiskReport) -> None:
    st.subheader("Lloyd's checklist")
    detail = report.lloyds_detail
    for criterion, data in detail.items():
        if data.get("pass") is None:
            continue
        passed = data.get("pass") is True
        reason = data.get("reason", "")
        border = "4px solid #10b981" if passed else "4px solid #ef4444"
        st.markdown(
            f'<div style="border-left:{border};padding-left:12px;margin:6px 0;">'
            f'<span style="font-family:JetBrains Mono,monospace;">{criterion}</span> — '
            f'<b>{"PASS" if passed else "FAIL"}</b><br/>'
            f'<span style="color:#6b7280;">{reason}</span></div>',
            unsafe_allow_html=True,
        )
