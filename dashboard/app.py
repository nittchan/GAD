"""
GAD Dashboard — oracle.parametricdata.io. Home: hero + two CTAs (Try sample / Build your own).
"""

from __future__ import annotations

import streamlit as st
from dotenv import load_dotenv

from dashboard.components.auth import handle_oauth_callback

load_dotenv()

COLORS = {"bg": "#0a0e1a", "surface": "#111827", "text": "#f9fafb", "muted": "#6b7280", "teal": "#00a8a8"}
CSS = f"""
<style>
.stApp {{ background-color: {COLORS["bg"]}; color: {COLORS["text"]}; }}
[data-testid="stSidebar"] {{ background: {COLORS["surface"]}; }}
</style>
"""


def main() -> None:
    st.set_page_config(page_title="GAD — Get Actuary Done", layout="wide", initial_sidebar_state="expanded")
    handle_oauth_callback()
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        '<p style="font-size:0.75rem;color:#6b7280;margin-bottom:0;">Get Actuary Done</p>'
        '<p style="font-size:1.75rem;font-weight:700;margin-bottom:0;">GAD</p>'
        '<p style="color:#6b7280;margin-top:0;">Basis risk & oracle ledger</p>',
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("---")
    st.sidebar.page_link("app.py", label="Home", icon="🏠")
    st.sidebar.page_link("pages/1_Guided_mode.py", label="Build your own (wizard)", icon="✨")
    st.sidebar.page_link("pages/2_Expert_mode.py", label="Expert mode (YAML)", icon="📝")
    st.sidebar.page_link("pages/3_Trigger_profile.py", label="Trigger profile", icon="📊")
    st.sidebar.page_link("pages/4_Compare.py", label="Compare triggers", icon="⚖️")
    st.sidebar.page_link("pages/5_Account.py", label="Account", icon="👤")

    # Hero
    st.markdown(
        """
    <div style="padding: 48px 0 32px 0;">
        <p style="color:#00a8a8; font-size:12px; letter-spacing:2px; text-transform:uppercase; margin-bottom:8px;">
            Open-source parametric infrastructure
        </p>
        <h1 style="font-size:36px; font-weight:700; color:#0a1628; line-height:1.2; margin-bottom:12px;">
            Score any parametric trigger<br>in 60 seconds.
        </h1>
        <p style="font-size:16px; color:#6b7280; max-width:520px;">
            Spearman basis risk. Historical back-test. Lloyd's alignment.
            All transparent. All verifiable. All open-source.
        </p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([2, 2, 3])
    with col1:
        if st.button("Try a sample trigger", use_container_width=True, type="primary"):
            st.session_state["load_sample"] = "kenya-drought-chirps"
            st.switch_page("pages/3_Trigger_profile.py")
    with col2:
        if st.button("Build your own", use_container_width=True):
            st.switch_page("pages/1_Guided_mode.py")

    st.divider()
    st.markdown("### What you get")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**Spearman rho**")
        st.caption("How well does your trigger correlate with actual losses? Auditable.")
    with c2:
        st.markdown("**Lloyd's alignment**")
        st.caption("10-point checklist. Failed criteria shown with remediation hints.")
    with c3:
        st.markdown("**Oracle ledger**")
        st.caption("Every determination signed, hash-chained, and published permanently.")


if __name__ == "__main__":
    main()
