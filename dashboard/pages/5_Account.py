"""Account & monitor status."""

from __future__ import annotations

import streamlit as st

from dashboard.components.theme import inject_theme
from gad.monitor.triggers import GLOBAL_TRIGGERS, PERIL_LABELS, get_triggers_by_peril
from gad.monitor.cache import read_cache_with_staleness, list_cached_entries
from gad.monitor.airports import ALL_AIRPORTS, INDIA_AIRPORTS, GLOBAL_AIRPORTS

st.set_page_config(page_title="Account | Parametric Data", layout="wide", initial_sidebar_state="collapsed")
inject_theme(st)

# ── Page-specific styles ──
st.markdown("""
<style>
    .stApp { background-color: #F5F0EB; }
    [data-testid="stSidebar"] { background: #EDE7E0; border-right: 1px solid #D4CCC0; }
    header[data-testid="stHeader"] { background: transparent; }
    .stat-card { background: #EDE7E0; border: 1px solid #D4CCC0; border-radius: 8px; padding: 20px; text-align: center; }
    .stat-num { font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 32px; font-weight: 700; color: #C8553D; }
    .stat-lbl { color: #7A7267; font-size: 12px; margin-top: 4px; }
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
st.sidebar.page_link("app.py", label="Home", icon="🏠")
st.sidebar.page_link("pages/6_Global_Monitor.py", label="Global Monitor", icon="🌍")
st.sidebar.page_link("pages/1_Guided_mode.py", label="Build your own", icon="✨")
st.sidebar.page_link("pages/2_Expert_mode.py", label="Expert mode", icon="📝")
st.sidebar.page_link("pages/3_Trigger_profile.py", label="Trigger profile", icon="📊")
st.sidebar.page_link("pages/4_Compare.py", label="Compare triggers", icon="⚖️")
st.sidebar.page_link("pages/5_Account.py", label="Account", icon="👤")
st.sidebar.page_link("pages/7_Oracle.py", label="Oracle Ledger", icon="🔐")
st.sidebar.page_link("pages/8_Digest.py", label="Daily Digest", icon="📨")

# ── Header ──
st.markdown(
    '<p style="font-size:11px;color:#C8553D;letter-spacing:2px;text-transform:uppercase;margin-bottom:4px;">Parametric Data</p>'
    '<h1 style="font-size:28px;font-weight:700;color:#1E1B18;margin-bottom:8px;">Monitor Status</h1>'
    '<p style="color:#7A7267;font-size:14px;">Platform overview and data source health.</p>',
    unsafe_allow_html=True,
)

# ── Stats ──
s1, s2, s3, s4 = st.columns(4)
with s1:
    st.markdown(f'<div class="stat-card"><div class="stat-num">{len(GLOBAL_TRIGGERS)}</div><div class="stat-lbl">Total triggers</div></div>', unsafe_allow_html=True)
with s2:
    st.markdown(f'<div class="stat-card"><div class="stat-num">{len(ALL_AIRPORTS)}</div><div class="stat-lbl">Airports monitored</div></div>', unsafe_allow_html=True)
with s3:
    st.markdown(f'<div class="stat-card"><div class="stat-num">{len(INDIA_AIRPORTS)}</div><div class="stat-lbl">Indian airports</div></div>', unsafe_allow_html=True)
with s4:
    st.markdown(f'<div class="stat-card"><div class="stat-num">{len(GLOBAL_AIRPORTS)}</div><div class="stat-lbl">Global airports</div></div>', unsafe_allow_html=True)

# ── Per-peril breakdown ──
st.markdown('<div style="height:24px"></div>', unsafe_allow_html=True)
st.markdown("### Triggers by Peril")

_SOURCE_KEY_MAP = {
    "flight_delay": "flights", "air_quality": "aqi", "wildfire": "fire",
    "drought": "drought", "extreme_weather": "weather", "earthquake": "earthquake",
    "marine": "marine", "flood": "flood", "cyclone": "cyclone",
    "crop": "ndvi", "solar": "solar", "health": "health",
}


@st.cache_data(ttl=300)
def _compute_peril_stats() -> dict[str, dict]:
    """Compute per-peril cache freshness stats. Cached 5 min."""
    stats: dict[str, dict] = {}
    for peril_key in PERIL_LABELS:
        triggers = get_triggers_by_peril(peril_key)
        source_key = _SOURCE_KEY_MAP.get(peril_key, peril_key)
        cached = stale = no_data = 0
        for t in triggers:
            data, is_stale = read_cache_with_staleness(source_key, t.id)
            if data is None:
                no_data += 1
            elif is_stale:
                stale += 1
            else:
                cached += 1
        total = len(triggers)
        pct = int(cached / total * 100) if total > 0 else 0
        stats[peril_key] = {"cached": cached, "stale": stale, "no_data": no_data, "total": total, "pct": pct}
    return stats


with st.spinner("Loading monitor status..."):
    peril_stats = _compute_peril_stats()

for peril_key, label in PERIL_LABELS.items():
    s = peril_stats[peril_key]
    st.markdown(f"""
    <div style="background:#EDE7E0;border:1px solid #D4CCC0;border-radius:6px;padding:12px 16px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center;">
        <div>
            <span style="font-weight:600;color:#1E1B18;">{label}</span>
            <span style="color:#7A7267;font-size:12px;margin-left:8px;">{s['total']} triggers</span>
        </div>
        <div style="font-family:monospace;font-size:13px;">
            <span style="color:#2E8B6F;">{s['cached']} fresh</span> ·
            <span style="color:#D4A017;">{s['stale']} stale</span> ·
            <span style="color:#7A7267;">{s['no_data']} no data</span> ·
            <span style="color:#C8553D;font-weight:600;">{s['pct']}%</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── Data sources ──
st.markdown('<div style="height:24px"></div>', unsafe_allow_html=True)
st.markdown("### Data Sources")
st.markdown("""
| Source | Type | Status | Rate Limit |
|--------|------|--------|------------|
| FAA ATCSCC | US airport delays (real minutes) | No key needed | Unlimited |
| OpenSky Network | Flight departures (global) | OAuth2 authenticated | 4000 credits/day |
| AviationStack | Flight schedules (tier-1) | API key | 500 req/month |
| WAQI | Air quality (global) | API key | Generous |
| AirNow EPA | Air quality (US) | API key | Generous |
| OpenAQ v3 | Air quality (open data) | API key | Generous |
| NASA FIRMS VIIRS+MODIS | Wildfire detection | MAP key | 5000 txn/10min |
| Open-Meteo | Weather forecasts | No key needed | Unlimited |
| CHIRPS v2.0 | Monthly rainfall | No key needed | Unlimited |
| NASA GPM IMERG | Daily precipitation | Earthdata token | Generous |
| USGS | Earthquake detection | No key needed | Unlimited |
| AISstream | Marine vessel tracking | API key | WebSocket |
| USGS Water Services | River gauge height | No key needed | Unlimited |
| NOAA NHC | Tropical cyclone tracking | No key needed | Unlimited |\n| Copernicus/MODIS | Crop NDVI vegetation index | No key needed | 16-day composite |
| NOAA SWPC | Solar/space weather Kp index | No key needed | Unlimited |
| WHO DON | Disease outbreak news | No key needed | RSS feed (2hr TTL) |
""")

# ── Account (future) ──
st.markdown('<div style="height:24px"></div>', unsafe_allow_html=True)
st.markdown("### Account")
st.info("User accounts, saved triggers, and notification subscriptions will be available in a future update. Currently all features are free and open to everyone.")

# ── Footer ──
from dashboard.components.footer import render_footer
render_footer()
