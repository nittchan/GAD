"""
Shared footer for all dashboard pages.
"""

from __future__ import annotations

import streamlit as st

MOBILE_NAV_HTML = """
<div class="mobile-nav">
    <a href="/Global_Monitor">🌍 Monitor</a>
    <a href="/Guided_mode">✨ Build</a>
    <a href="/Trigger_profile">📊 Profile</a>
    <a href="/Oracle">🔐 Oracle</a>
</div>
"""

FOOTER_HTML = """
<div style="margin-top:48px;padding:24px 0;border-top:1px solid #D4CCC0;">
    <p style="color:#C8553D;font-size:12px;font-weight:600;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px;font-family:'Instrument Sans',sans-serif;">
        World's first open-source actuarial data platform
    </p>
    <p style="color:#7A7267;font-size:12px;line-height:1.8;margin-bottom:12px;font-family:'Instrument Sans',sans-serif;">
        Powered by <a href="https://orbitcover.com" style="color:#C8553D;text-decoration:none;">OrbitCover</a>
        (MedPiper Technologies — backed by <a href="https://www.ycombinator.com" style="color:#C8553D;text-decoration:none;">Y Combinator</a>).<br>
        Built and maintained by <strong style="color:#1E1B18;">Nitthin Chandran Nair</strong>
        using <a href="https://claude.ai/claude-code" style="color:#C8553D;text-decoration:none;">Claude Code</a>.<br>
        Data from
        <a href="https://opensky-network.org" style="color:#7A7267;">OpenSky</a>,
        <a href="https://openaq.org" style="color:#7A7267;">OpenAQ</a>,
        <a href="https://firms.modaps.eosdis.nasa.gov" style="color:#7A7267;">NASA FIRMS</a>,
        <a href="https://open-meteo.com" style="color:#7A7267;">Open-Meteo</a>,
        <a href="https://www.chc.ucsb.edu/data/chirps" style="color:#7A7267;">CHIRPS</a>,
        <a href="https://waterservices.usgs.gov" style="color:#7A7267;">USGS</a>,
        <a href="https://www.nhc.noaa.gov" style="color:#7A7267;">NOAA NHC</a>.
    </p>
    <p style="color:#9B9286;font-size:11px;font-family:'Instrument Sans',sans-serif;">
        Open-source under AGPL-3.0 (engine) and MIT (schema).
        This page makes zero external API calls — all data is pre-fetched and cached.
    </p>
</div>
"""


def render_footer() -> None:
    """Render the shared footer. Call at the bottom of every page."""
    st.markdown(MOBILE_NAV_HTML, unsafe_allow_html=True)
    st.markdown(FOOTER_HTML, unsafe_allow_html=True)
