"""
Daily Digest — AI-generated global risk summary.

Shows fired triggers, approaching-threshold triggers, and elevated perils.
Reads from the most recent digest file or generates one on demand.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import streamlit as st

from dashboard.components.theme import inject_theme

st.set_page_config(
    page_title="Daily Digest | Parametric Data",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_theme(st)

# ── Page-specific styles ──
st.markdown("""
<style>
    .stApp { background-color: #F5F0EB; }
    [data-testid="stSidebar"] { background: #EDE7E0; border-right: 1px solid #D4CCC0; }
    header[data-testid="stHeader"] { background: transparent; }
    .digest-card {
        background: #EDE7E0; border: 1px solid #D4CCC0; border-radius: 8px;
        padding: 20px; margin-bottom: 16px;
    }
    .digest-label {
        color: #7A7267; font-size: 12px; text-transform: uppercase;
        letter-spacing: 1px; margin-bottom: 4px;
    }
    .digest-value {
        color: #1E1B18; font-size: 20px; font-weight: 700;
        font-family: 'JetBrains Mono', ui-monospace, monospace;
    }
    .digest-fired { color: #A63D40; }
    .digest-normal { color: #2E8B6F; }
    .digest-approaching { color: #B8860B; }
    [data-testid="stSidebar"] a {
        min-height: 44px !important; display: flex !important;
        align-items: center !important;
    }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──
st.sidebar.markdown(
    '<div style="padding:8px 0 16px 0;">'
    '<p style="font-size:11px;color:#C8553D;letter-spacing:2px;text-transform:uppercase;margin-bottom:4px;">parametricdata.io</p>'
    '<p style="font-size:20px;font-weight:700;color:#1E1B18;margin:0;">Parametric Data</p>'
    '</div>',
    unsafe_allow_html=True,
)
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Home", icon="\U0001f3e0")
st.sidebar.page_link("pages/6_Global_Monitor.py", label="Global Monitor", icon="\U0001f30d")
st.sidebar.page_link("pages/1_Guided_mode.py", label="Build your own", icon="\u2728")
st.sidebar.page_link("pages/2_Expert_mode.py", label="Expert mode", icon="\U0001f4dd")
st.sidebar.page_link("pages/3_Trigger_profile.py", label="Trigger profile", icon="\U0001f4ca")
st.sidebar.page_link("pages/4_Compare.py", label="Compare triggers", icon="\u2696\ufe0f")
st.sidebar.page_link("pages/5_Account.py", label="Account", icon="\U0001f464")
st.sidebar.page_link("pages/7_Oracle.py", label="Oracle Ledger", icon="\U0001f510")
st.sidebar.page_link("pages/8_Digest.py", label="Daily Digest", icon="\U0001f4e8")

# ── Header ──
st.markdown(
    '<p style="font-size:11px;color:#C8553D;letter-spacing:2px;text-transform:uppercase;margin-bottom:4px;">Parametric Data</p>'
    '<h1 style="font-size:28px;font-weight:700;color:#1E1B18;margin-bottom:8px;">Daily Digest</h1>'
    '<p style="color:#7A7267;font-size:14px;">AI-generated global risk summary. Fired triggers, approaching thresholds, and elevated perils.</p>',
    unsafe_allow_html=True,
)

st.markdown('<div style="height:24px"></div>', unsafe_allow_html=True)

# ── Load or generate digest ──
ROOT = Path(__file__).resolve().parent.parent.parent
DIGEST_DIR = ROOT / "data" / "digest"


@st.cache_data(ttl=300)
def _find_latest_digest() -> tuple[str | None, str | None]:
    """Find the most recent digest file. Cached 5 min. Returns (content, filename) or (None, None)."""
    if not DIGEST_DIR.is_dir():
        return None, None
    files = sorted(DIGEST_DIR.glob("*.md"), reverse=True)
    if not files:
        return None, None
    return files[0].read_text(encoding="utf-8"), files[0].name


# Try loading existing digest first
with st.spinner("Loading latest digest..."):
    digest_content, digest_file = _find_latest_digest()
today_str = date.today().isoformat()
is_today = digest_file == f"{today_str}.md" if digest_file else False

# Generate button
col_gen, col_status = st.columns([1, 3])
with col_gen:
    if st.button("Generate Today's Digest", type="primary"):
        with st.spinner("Scanning all triggers and generating digest..."):
            try:
                from gad.monitor.intelligence import generate_global_digest
                digest_content = generate_global_digest()
                digest_file = f"{today_str}.md"
                is_today = True
                st.success("Digest generated.")
            except Exception as e:
                st.error(f"Failed to generate digest: {e}")

with col_status:
    if digest_file:
        freshness = "Today's digest" if is_today else f"Most recent: {digest_file}"
        color = "#2E8B6F" if is_today else "#B8860B"
        st.markdown(
            f'<p style="color:{color};font-size:13px;margin-top:8px;">{freshness}</p>',
            unsafe_allow_html=True,
        )

st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)

# ── Render digest ──
if digest_content:
    # Parse the markdown to extract sections for styled rendering
    lines = digest_content.split("\n")

    fired_lines: list[str] = []
    approaching_lines: list[str] = []
    elevated_lines: list[str] = []
    current_section = None

    for line in lines:
        if "## Triggers Fired" in line:
            current_section = "fired"
            continue
        elif "## Approaching Threshold" in line:
            current_section = "approaching"
            continue
        elif "## Elevated Perils" in line:
            current_section = "elevated"
            continue
        elif line.startswith("---") or line.startswith("# ") or line.startswith("*Generated"):
            if line.startswith("*Generated"):
                continue
            current_section = None
            continue

        if current_section == "fired" and line.strip().startswith("- "):
            fired_lines.append(line.strip()[2:].replace("**", ""))
        elif current_section == "approaching" and line.strip().startswith("- "):
            approaching_lines.append(line.strip()[2:].replace("**", ""))
        elif current_section == "elevated" and line.strip().startswith("- "):
            elevated_lines.append(line.strip()[2:].replace("**", ""))

    # Summary cards
    c1, c2, c3 = st.columns(3)

    fired_count = len(fired_lines) if fired_lines and fired_lines[0] != "No triggers currently in fired state." else 0
    approaching_count = len(approaching_lines) if approaching_lines and approaching_lines[0] != "No triggers currently approaching threshold." else 0
    elevated_count = len(elevated_lines) if elevated_lines and elevated_lines[0] != "No perils showing elevated activity." else 0

    with c1:
        color = "#A63D40" if fired_count > 0 else "#2E8B6F"
        st.markdown(f"""
        <div class="digest-card">
            <div class="digest-label">Triggers Fired</div>
            <div class="digest-value" style="color:{color}">{fired_count}</div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        color = "#B8860B" if approaching_count > 0 else "#2E8B6F"
        st.markdown(f"""
        <div class="digest-card">
            <div class="digest-label">Approaching Threshold</div>
            <div class="digest-value" style="color:{color}">{approaching_count}</div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        color = "#A63D40" if elevated_count > 0 else "#2E8B6F"
        st.markdown(f"""
        <div class="digest-card">
            <div class="digest-label">Elevated Perils</div>
            <div class="digest-value" style="color:{color}">{elevated_count}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)

    # Fired triggers detail
    st.markdown("### Triggers Fired")
    if fired_count > 0:
        for item in fired_lines:
            st.markdown(f"""
            <div class="digest-card" style="border-left:4px solid #A63D40;">
                <span style="color:#A63D40;font-weight:600;">{item}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="digest-card"><span style="color:#2E8B6F;">No triggers currently in fired state.</span></div>',
            unsafe_allow_html=True,
        )

    # Approaching threshold detail
    st.markdown("### Approaching Threshold")
    if approaching_count > 0:
        for item in approaching_lines:
            st.markdown(f"""
            <div class="digest-card" style="border-left:4px solid #B8860B;">
                <span style="color:#B8860B;font-weight:600;">{item}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="digest-card"><span style="color:#2E8B6F;">No triggers currently approaching threshold.</span></div>',
            unsafe_allow_html=True,
        )

    # Elevated perils detail
    st.markdown("### Elevated Perils")
    if elevated_count > 0:
        for item in elevated_lines:
            st.markdown(f"""
            <div class="digest-card" style="border-left:4px solid #C8553D;">
                <span style="color:#C8553D;font-weight:600;">{item}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="digest-card"><span style="color:#2E8B6F;">No perils showing elevated activity.</span></div>',
            unsafe_allow_html=True,
        )

    # Full markdown in expander
    with st.expander("View raw digest markdown"):
        st.code(digest_content, language="markdown")

else:
    st.markdown("""
    <div class="digest-card">
        <div class="digest-label">No digest available</div>
        <div style="color:#7A7267;font-size:14px;margin-top:8px;">
            Click "Generate Today's Digest" to scan all triggers and produce a risk summary.
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── Footer ──
from dashboard.components.footer import render_footer
render_footer()
