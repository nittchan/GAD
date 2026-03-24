"""Oracle Ledger — recent signed determinations and chain status."""

from __future__ import annotations

import json
import os
from pathlib import Path

import streamlit as st

from dashboard.components.theme import inject_theme
from gad.engine.oracle import GENESIS_HASH, ORACLE_JSONL_PATH, ORACLE_LOG_PATH, verify_chain

st.set_page_config(page_title="Oracle | Parametric Data", layout="wide", initial_sidebar_state="collapsed")
inject_theme(st)

# ── Page-specific styles ──
st.markdown("""
<style>
    .stApp { background-color: #F5F0EB; }
    [data-testid="stSidebar"] { background: #EDE7E0; border-right: 1px solid #D4CCC0; }
    header[data-testid="stHeader"] { background: transparent; }
    .stat-card { background: #EDE7E0; border: 1px solid #D4CCC0; border-radius: 8px; padding: 20px; text-align: center; }
    .stat-num { font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 32px; font-weight: 700; color: #467B6B; }
    .stat-lbl { color: #7A7267; font-size: 12px; margin-top: 4px; }
    .seal-valid { background: #E8F0ED; border: 1px solid #467B6B; color: #467B6B;
                  padding: 12px 20px; border-radius: 4px; font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 13px; }
    .seal-invalid { background: #F8EAEA; border: 1px solid #A63D40; color: #A63D40;
                    padding: 12px 20px; border-radius: 4px; font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 13px; }
    .det-row { background: #EDE7E0; border: 1px solid #D4CCC0; border-radius: 6px;
               padding: 14px 18px; margin-bottom: 8px; font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 12px; }
    .det-id { color: #467B6B; font-size: 11px; }
    .det-fired { color: #A63D40; font-weight: 700; }
    .det-normal { color: #2E8B6F; }
    .det-meta { color: #7A7267; font-size: 11px; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──
st.sidebar.markdown(
    '<div style="padding:8px 0 16px 0;">'
    '<p style="font-size:11px;color:#C8553D;letter-spacing:2px;text-transform:uppercase;margin-bottom:4px;">parametricdata.io</p>'
    '<p style="font-size:20px;font-weight:700;color:#1E1B18;margin:0;">Parametric Data</p>'
    '</div>', unsafe_allow_html=True,
)
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Home")
st.sidebar.page_link("pages/6_Global_Monitor.py", label="Global Monitor")
st.sidebar.page_link("pages/1_Guided_mode.py", label="Build your own")
st.sidebar.page_link("pages/2_Expert_mode.py", label="Expert mode")
st.sidebar.page_link("pages/3_Trigger_profile.py", label="Trigger profile")
st.sidebar.page_link("pages/4_Compare.py", label="Compare triggers")
st.sidebar.page_link("pages/5_Account.py", label="Account")
st.sidebar.page_link("pages/7_Oracle.py", label="Oracle Ledger")

# ── Header ──
st.markdown(
    '<p style="font-size:11px;color:#C8553D;letter-spacing:2px;text-transform:uppercase;margin-bottom:4px;">Parametric Data</p>'
    '<h1 style="font-size:28px;font-weight:700;color:#1E1B18;margin-bottom:8px;">Oracle Ledger</h1>'
    '<p style="color:#7A7267;font-size:14px;">Cryptographically signed trigger determinations. Every evaluation is Ed25519 signed and hash-chained.</p>',
    unsafe_allow_html=True,
)

st.markdown('<div style="height:24px"></div>', unsafe_allow_html=True)


# ── Load JSONL log ──
def _load_recent_determinations(max_entries: int = 20) -> list[dict]:
    """Read the most recent entries from the oracle JSONL log."""
    jsonl_path = Path(ORACLE_LOG_PATH).parent / "oracle_log.jsonl"
    if not jsonl_path.exists():
        return []

    try:
        with open(jsonl_path, "r") as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        # Most recent last → reverse
        entries = []
        for line in reversed(lines[-max_entries:]):
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return entries
    except Exception:
        return []


def _count_determinations() -> int:
    """Count total entries in the JSONL log."""
    jsonl_path = Path(ORACLE_LOG_PATH).parent / "oracle_log.jsonl"
    if not jsonl_path.exists():
        return 0
    try:
        with open(jsonl_path, "r") as f:
            return sum(1 for l in f if l.strip())
    except Exception:
        return 0


# ── Chain verification ──
valid, count, msg = verify_chain()
total = _count_determinations()
recent = _load_recent_determinations(20)

# ── Stats row ──
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f'<div class="stat-card"><div class="stat-num">{total}</div><div class="stat-lbl">Total Determinations</div></div>', unsafe_allow_html=True)
with c2:
    fired_count = sum(1 for e in recent if e.get("fired"))
    st.markdown(f'<div class="stat-card"><div class="stat-num">{fired_count}</div><div class="stat-lbl">Fired (last {len(recent)})</div></div>', unsafe_allow_html=True)
with c3:
    signing_enabled = os.environ.get("GAD_ORACLE_PRIVATE_KEY_HEX") is not None
    status_text = "ACTIVE" if signing_enabled else "INACTIVE"
    status_color = "#2E8B6F" if signing_enabled else "#7A7267"
    st.markdown(f'<div class="stat-card"><div class="stat-num" style="color:{status_color};font-size:24px;">{status_text}</div><div class="stat-lbl">Oracle Signing</div></div>', unsafe_allow_html=True)

st.markdown('<div style="height:24px"></div>', unsafe_allow_html=True)

# ── Chain verification status ──
if valid:
    st.markdown(
        f'<div class="seal-valid">CHAIN VALID — {count} entries verified. '
        f'Genesis: {GENESIS_HASH[:16]}...</div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        f'<div class="seal-invalid">CHAIN BROKEN — {msg}</div>',
        unsafe_allow_html=True,
    )

st.markdown('<div style="height:24px"></div>', unsafe_allow_html=True)

# ── Recent determinations ──
st.markdown("### Recent Determinations")

if not recent:
    st.info("No determinations yet. The background fetcher will produce signed determinations when oracle keys are configured.")
else:
    oracle_base_url = "https://oracle.parametricdata.io/determination"

    for entry in recent:
        det_id = entry.get("determination_id", "unknown")
        fired = entry.get("fired", False)
        fired_at = entry.get("fired_at", "")
        determined_at = entry.get("determined_at", "")
        trigger_id = entry.get("trigger_id", "")
        snapshot = entry.get("data_snapshot_hash", "")[:16]
        prev_hash = entry.get("prev_hash", "")[:16]
        key_id = entry.get("key_id", "")

        fired_badge = '<span class="det-fired">FIRED</span>' if fired else '<span class="det-normal">NOT FIRED</span>'
        time_str = fired_at if fired else determined_at

        st.markdown(f"""
        <div class="det-row">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <span class="det-id">{det_id}</span>
                {fired_badge}
            </div>
            <div class="det-meta" style="margin-top:6px;">
                trigger: {trigger_id[:16]}... &nbsp;|&nbsp;
                snapshot: {snapshot}... &nbsp;|&nbsp;
                prev: {prev_hash}... &nbsp;|&nbsp;
                {time_str}
            </div>
            <div class="det-meta" style="margin-top:4px;">
                <a href="{oracle_base_url}/{det_id}" target="_blank" style="color:#467B6B;text-decoration:none;">
                    View on Oracle Ledger &rarr;
                </a>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ── Footer ──
st.markdown('<div style="height:48px"></div>', unsafe_allow_html=True)
st.markdown(
    '<p style="color:#9B9286;font-size:11px;text-align:center;">'
    'World\'s first open-source actuarial data platform. '
    'Powered by <a href="https://orbitcover.com" style="color:#6b7280;">OrbitCover</a> '
    '(MedPiper — backed by Y Combinator). '
    'Built by Nitthin Chandran Nair using Claude Code.</p>',
    unsafe_allow_html=True,
)
