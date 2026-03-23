"""
Parametric Data — parametricdata.io. Home page.
"""

from __future__ import annotations

import streamlit as st
from dotenv import load_dotenv

from dashboard.components.auth import handle_oauth_callback

load_dotenv()

st.set_page_config(
    page_title="Parametric Data — Global Insurance Monitor",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)
handle_oauth_callback()

# ── Global dark theme ──
st.markdown("""
<style>
    .stApp { background-color: #0d1117; }
    [data-testid="stSidebar"] { background: #161b22; }
    h1, h2, h3, h4, p, span, label, div { color: #e6edf3; }
    .hero-tag { color: #58a6ff; font-size: 12px; letter-spacing: 2px;
                text-transform: uppercase; margin-bottom: 8px; font-weight: 600; }
    .hero-title { font-size: 40px; font-weight: 700; color: #e6edf3;
                  line-height: 1.2; margin-bottom: 12px; }
    .hero-sub { font-size: 16px; color: #8b949e; max-width: 560px; line-height: 1.6; }
    .feature-card { background: #161b22; border: 1px solid #30363d; border-radius: 6px;
                    padding: 20px; height: 100%; }
    .feature-card h4 { color: #e6edf3; margin: 0 0 8px 0; font-size: 15px; }
    .feature-card p { color: #8b949e; font-size: 13px; margin: 0; line-height: 1.5; }
    .stat-number { font-family: 'JetBrains Mono', monospace; font-size: 28px;
                   font-weight: 700; color: #58a6ff; }
    .stat-label { color: #8b949e; font-size: 12px; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar nav ──
st.sidebar.markdown(
    '<p style="font-size:11px;color:#8b949e;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:4px;">Parametric Data</p>'
    '<p style="font-size:18px;font-weight:700;color:#e6edf3;margin-bottom:0;">Global Monitor</p>',
    unsafe_allow_html=True,
)
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Home", icon="🏠")
st.sidebar.page_link("pages/6_Global_Monitor.py", label="Global Monitor", icon="🌍")
st.sidebar.page_link("pages/1_Guided_mode.py", label="Build your own", icon="✨")
st.sidebar.page_link("pages/2_Expert_mode.py", label="Expert mode", icon="📝")
st.sidebar.page_link("pages/3_Trigger_profile.py", label="Trigger profile", icon="📊")
st.sidebar.page_link("pages/4_Compare.py", label="Compare triggers", icon="⚖️")
st.sidebar.page_link("pages/5_Account.py", label="Account", icon="👤")

# ── Hero ──
st.markdown("""
<div style="padding: 48px 0 24px 0;">
    <p class="hero-tag">The global parametric insurance monitor</p>
    <h1 class="hero-title">Live risk data.<br>Open actuarial math.<br>Verifiable oracle.</h1>
    <p class="hero-sub">
        426 parametric triggers across 144 airports (50 Indian + 94 global), air quality, wildfire, drought, and extreme weather —
        all scored with Spearman basis risk, Lloyd's alignment, and cryptographic attestation.
        Open-source. Free forever.
    </p>
</div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns([2, 2, 3])
with col1:
    if st.button("🌍  Open Global Monitor", use_container_width=True, type="primary"):
        st.switch_page("pages/6_Global_Monitor.py")
with col2:
    if st.button("✨  Build your own trigger", use_container_width=True):
        st.switch_page("pages/1_Guided_mode.py")

# ── Stats bar ──
st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)
s1, s2, s3, s4 = st.columns(4)
with s1:
    st.markdown('<div class="stat-number">426</div><div class="stat-label">Live triggers</div>', unsafe_allow_html=True)
with s2:
    st.markdown('<div class="stat-number">5</div><div class="stat-label">Peril categories</div>', unsafe_allow_html=True)
with s3:
    st.markdown('<div class="stat-number">4</div><div class="stat-label">Open data sources</div>', unsafe_allow_html=True)
with s4:
    st.markdown('<div class="stat-number">Ed25519</div><div class="stat-label">Oracle signing</div>', unsafe_allow_html=True)

# ── Features ──
st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("""
    <div class="feature-card">
        <h4>Spearman Basis Risk</h4>
        <p>How well does your trigger correlate with actual losses?
        Bootstrap confidence intervals. Confusion matrix. All auditable.</p>
    </div>
    """, unsafe_allow_html=True)
with c2:
    st.markdown("""
    <div class="feature-card">
        <h4>Lloyd's Alignment</h4>
        <p>10-point checklist mapped to Lloyd's parametric product standards.
        Failed criteria shown with remediation. PDF export.</p>
    </div>
    """, unsafe_allow_html=True)
with c3:
    st.markdown("""
    <div class="feature-card">
        <h4>Oracle Ledger</h4>
        <p>Every trigger determination cryptographically signed, hash-chained,
        and published to a permanent public ledger. Independently verifiable.</p>
    </div>
    """, unsafe_allow_html=True)

# ── Footer ──
st.markdown("<div style='height:48px'></div>", unsafe_allow_html=True)
st.markdown(
    '<p style="color:#484f58;font-size:12px;text-align:center;">'
    'Open-source under AGPL-3.0 (engine) and MIT (schema). '
    'Data from OpenSky, OpenAQ, NASA FIRMS, Open-Meteo, CHIRPS.</p>',
    unsafe_allow_html=True,
)
