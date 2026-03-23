"""
Parametric Data — parametricdata.io
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
    initial_sidebar_state="collapsed",
)
handle_oauth_callback()

# ── Hide Streamlit default chrome ──
st.markdown("""
<style>
    /* Hide default Streamlit page nav */
    [data-testid="stSidebarNav"] { display: none; }
    header[data-testid="stHeader"] { background: transparent; }

    /* Dark theme */
    .stApp { background-color: #0d1117; }
    [data-testid="stSidebar"] { background: #161b22; border-right: 1px solid #30363d; }

    /* Typography */
    h1, h2, h3, h4, p, span, label, div { color: #e6edf3; }

    /* Hero */
    .hero-tag { color: #58a6ff; font-size: 13px; letter-spacing: 3px;
                text-transform: uppercase; margin-bottom: 12px; font-weight: 600; }
    .hero-title { font-size: 48px; font-weight: 800; color: #e6edf3;
                  line-height: 1.15; margin-bottom: 16px; letter-spacing: -0.02em; }
    .hero-sub { font-size: 17px; color: #8b949e; max-width: 580px; line-height: 1.7; }

    /* Stats */
    .stats-row { display: flex; gap: 48px; margin: 32px 0; }
    .stat-item { }
    .stat-number { font-family: 'JetBrains Mono', ui-monospace, monospace;
                   font-size: 32px; font-weight: 700; color: #58a6ff;
                   letter-spacing: -0.02em; }
    .stat-label { color: #8b949e; font-size: 12px; margin-top: 2px; }

    /* Feature cards */
    .feature-card { background: #161b22; border: 1px solid #30363d; border-radius: 8px;
                    padding: 24px; height: 100%; transition: border-color 0.2s; }
    .feature-card:hover { border-color: #58a6ff; }
    .feature-card h4 { color: #e6edf3; margin: 0 0 10px 0; font-size: 16px; font-weight: 600; }
    .feature-card p { color: #8b949e; font-size: 13px; margin: 0; line-height: 1.6; }

    /* Buttons */
    .stButton > button[kind="primary"] {
        background: #58a6ff !important; color: #0d1117 !important;
        border: none !important; font-weight: 600 !important;
        border-radius: 6px !important; padding: 12px 24px !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: #79b8ff !important;
    }
    .stButton > button:not([kind="primary"]) {
        background: transparent !important; color: #e6edf3 !important;
        border: 1px solid #30363d !important; border-radius: 6px !important;
        padding: 12px 24px !important;
    }
    .stButton > button:not([kind="primary"]):hover {
        border-color: #58a6ff !important; color: #58a6ff !important;
    }

    /* Hide Streamlit branding */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    [data-testid="stDecoration"] { display: none; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──
st.sidebar.markdown(
    '<div style="padding:8px 0 16px 0;">'
    '<p style="font-size:11px;color:#58a6ff;letter-spacing:2px;text-transform:uppercase;margin-bottom:4px;">parametricdata.io</p>'
    '<p style="font-size:20px;font-weight:700;color:#e6edf3;margin:0;">Parametric Data</p>'
    '<p style="font-size:12px;color:#8b949e;margin-top:4px;">Global Insurance Monitor</p>'
    '</div>',
    unsafe_allow_html=True,
)
st.sidebar.markdown("---")
st.sidebar.page_link("pages/6_Global_Monitor.py", label="Global Monitor", icon="🌍")
st.sidebar.page_link("pages/1_Guided_mode.py", label="Build your own", icon="✨")
st.sidebar.page_link("pages/2_Expert_mode.py", label="Expert mode", icon="📝")
st.sidebar.page_link("pages/3_Trigger_profile.py", label="Trigger profile", icon="📊")
st.sidebar.page_link("pages/4_Compare.py", label="Compare triggers", icon="⚖️")
st.sidebar.page_link("pages/5_Account.py", label="Account", icon="👤")

# ── Hero ──
st.markdown('<div style="padding:56px 0 8px 0;">', unsafe_allow_html=True)
st.markdown('<p class="hero-tag">The Global Parametric Insurance Monitor</p>', unsafe_allow_html=True)
st.markdown(
    '<h1 class="hero-title">Live risk data.<br>Open actuarial math.<br>Verifiable oracle.</h1>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="hero-sub">'
    '426 parametric triggers across 144 airports (50 Indian + 94 global), '
    'air quality, wildfire, drought, and extreme weather — '
    'all scored with Spearman basis risk, Lloyd\'s alignment, and '
    'cryptographic attestation. Open-source. Free forever.'
    '</p>',
    unsafe_allow_html=True,
)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns([2, 2, 3])
with col1:
    if st.button("🌍  Open Global Monitor", use_container_width=True, type="primary"):
        st.switch_page("pages/6_Global_Monitor.py")
with col2:
    if st.button("✨  Build your own trigger", use_container_width=True):
        st.switch_page("pages/1_Guided_mode.py")

# ── Stats ──
st.markdown("""
<div class="stats-row">
    <div class="stat-item">
        <div class="stat-number">426</div>
        <div class="stat-label">Live triggers</div>
    </div>
    <div class="stat-item">
        <div class="stat-number">144</div>
        <div class="stat-label">Airports monitored</div>
    </div>
    <div class="stat-item">
        <div class="stat-number">5</div>
        <div class="stat-label">Peril categories</div>
    </div>
    <div class="stat-item">
        <div class="stat-number">Ed25519</div>
        <div class="stat-label">Oracle signing</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Features ──
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
from dashboard.components.footer import render_footer
render_footer()
