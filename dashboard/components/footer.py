"""
Shared footer for all dashboard pages.
"""

from __future__ import annotations

import streamlit as st

FOOTER_HTML = """
<div style="margin-top:48px;padding:24px 0;border-top:1px solid #30363d;">
    <p style="color:#58a6ff;font-size:12px;font-weight:600;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px;">
        World's first open-source actuarial data platform
    </p>
    <p style="color:#8b949e;font-size:12px;line-height:1.8;margin-bottom:12px;">
        Powered by <a href="https://orbitcover.com" style="color:#58a6ff;text-decoration:none;">OrbitCover</a>
        (MedPiper Technologies — backed by <a href="https://www.ycombinator.com" style="color:#58a6ff;text-decoration:none;">Y Combinator</a>).<br>
        Built and maintained by <strong style="color:#e6edf3;">Nitthin Chandran Nair</strong>
        using <a href="https://claude.ai/claude-code" style="color:#58a6ff;text-decoration:none;">Claude Code</a>.<br>
        Data from
        <a href="https://opensky-network.org" style="color:#8b949e;">OpenSky</a>,
        <a href="https://openaq.org" style="color:#8b949e;">OpenAQ</a>,
        <a href="https://firms.modaps.eosdis.nasa.gov" style="color:#8b949e;">NASA FIRMS</a>,
        <a href="https://open-meteo.com" style="color:#8b949e;">Open-Meteo</a>,
        <a href="https://www.chc.ucsb.edu/data/chirps" style="color:#8b949e;">CHIRPS</a>.
    </p>
    <p style="color:#484f58;font-size:11px;">
        Open-source under AGPL-3.0 (engine) and MIT (schema).
        This page makes zero external API calls — all data is pre-fetched and cached.
    </p>
</div>
"""


def render_footer() -> None:
    """Render the shared footer. Call at the bottom of every page."""
    st.markdown(FOOTER_HTML, unsafe_allow_html=True)
