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
st.sidebar.page_link("pages/9_Composer.py", label="Product Composer", icon="🧩")

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
    "disaster": "disaster", "eonet": "eonet",
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

# ── Data Source Freshness (FRESH-01b) ──
st.markdown('<div style="height:24px"></div>', unsafe_allow_html=True)
st.markdown("### Data Source Freshness")

try:
    import json as _json
    import time as _time
    from datetime import datetime as _dt, timezone as _tz
    from gad.config import CACHE_DIR as _CACHE_DIR

    _SOURCE_NAMES = {
        "flights": "Flight Delay (FAA/AviationStack/OpenSky)",
        "aqi": "Air Quality (AirNow/WAQI/OpenAQ)",
        "weather": "Weather (Open-Meteo)",
        "fire": "Wildfire (NASA FIRMS)",
        "drought": "Drought (CHIRPS/GPM IMERG)",
        "earthquake": "Earthquake (USGS)",
        "marine": "Marine (AISstream)",
        "flood": "Flood (USGS Water Services)",
        "cyclone": "Cyclone (NOAA NHC)",
        "ndvi": "Crop/NDVI (Copernicus/MODIS)",
        "solar": "Solar (NOAA SWPC)",
        "health": "Health (WHO DON)",
    }

    _FRESHNESS_COLORS = {"green": "#2E8B6F", "amber": "#D4A017", "red": "#A63D40"}

    @st.cache_data(ttl=120)
    def _compute_source_freshness() -> list[dict]:
        """Scan cache dir and compute per-source freshness. Cached 2 min."""
        now = _time.time()
        buckets: dict[str, list[dict]] = {p: [] for p in _SOURCE_NAMES}

        if _CACHE_DIR.is_dir():
            for path in _CACHE_DIR.glob("*.json"):
                try:
                    entry = _json.loads(path.read_text(encoding="utf-8"))
                except (ValueError, OSError):
                    continue
                fname = path.stem
                for prefix in _SOURCE_NAMES:
                    if fname.startswith(prefix + "_"):
                        buckets[prefix].append(entry)
                        break

        rows = []
        for prefix, entries in buckets.items():
            fc = len(entries)
            if fc == 0:
                rows.append({
                    "name": _SOURCE_NAMES[prefix], "last_fetch_rel": "—",
                    "fresh": 0, "stale": 0, "freshness": "red",
                })
                continue

            fresh = sum(1 for e in entries if e.get("expires_at", 0) > now)
            stale = fc - fresh
            latest = max(e.get("cached_at", 0) for e in entries)
            age = now - latest if latest > 0 else None

            # Relative time string
            if age is None:
                rel = "—"
            elif age < 60:
                rel = f"{int(age)}s ago"
            elif age < 3600:
                rel = f"{int(age // 60)} min ago"
            elif age < 86400:
                rel = f"{int(age // 3600)}h ago"
            else:
                rel = f"{int(age // 86400)}d ago"

            pct = fresh / fc
            if pct > 0.8:
                freshness = "green"
            elif pct > 0.5:
                freshness = "amber"
            else:
                freshness = "red"

            rows.append({
                "name": _SOURCE_NAMES[prefix], "last_fetch_rel": rel,
                "fresh": fresh, "stale": stale, "freshness": freshness,
            })
        return rows

    _freshness_rows = _compute_source_freshness()

    # Render as a styled HTML table
    _table_rows_html = ""
    for _r in _freshness_rows:
        _color = _FRESHNESS_COLORS.get(_r["freshness"], "#A63D40")
        _badge = _r["freshness"].upper()
        _table_rows_html += f"""
        <tr>
            <td style="padding:8px 12px;border-bottom:1px solid #D4CCC0;color:#1E1B18;font-size:13px;">{_r['name']}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #D4CCC0;font-family:monospace;font-size:13px;color:#7A7267;">{_r['last_fetch_rel']}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #D4CCC0;font-family:monospace;font-size:13px;color:#2E8B6F;">{_r['fresh']}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #D4CCC0;font-family:monospace;font-size:13px;color:#D4A017;">{_r['stale']}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #D4CCC0;text-align:center;">
                <span style="background:{_color};color:#fff;padding:2px 10px;border-radius:10px;font-size:11px;font-weight:600;letter-spacing:1px;">{_badge}</span>
            </td>
        </tr>"""

    st.markdown(f"""
    <div style="overflow-x:auto;">
    <table style="width:100%;border-collapse:collapse;background:#EDE7E0;border:1px solid #D4CCC0;border-radius:8px;">
        <thead>
            <tr style="background:#E5DFD8;">
                <th style="padding:10px 12px;text-align:left;font-size:12px;color:#7A7267;text-transform:uppercase;letter-spacing:1px;border-bottom:2px solid #D4CCC0;">Source</th>
                <th style="padding:10px 12px;text-align:left;font-size:12px;color:#7A7267;text-transform:uppercase;letter-spacing:1px;border-bottom:2px solid #D4CCC0;">Last Fetch</th>
                <th style="padding:10px 12px;text-align:left;font-size:12px;color:#7A7267;text-transform:uppercase;letter-spacing:1px;border-bottom:2px solid #D4CCC0;">Fresh</th>
                <th style="padding:10px 12px;text-align:left;font-size:12px;color:#7A7267;text-transform:uppercase;letter-spacing:1px;border-bottom:2px solid #D4CCC0;">Stale</th>
                <th style="padding:10px 12px;text-align:center;font-size:12px;color:#7A7267;text-transform:uppercase;letter-spacing:1px;border-bottom:2px solid #D4CCC0;">Status</th>
            </tr>
        </thead>
        <tbody>
            {_table_rows_html}
        </tbody>
    </table>
    </div>
    """, unsafe_allow_html=True)

except Exception as _freshness_err:
    st.warning(f"Could not load source freshness: {_freshness_err}")

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

# ── Watchlist ──
st.markdown('<div style="height:24px"></div>', unsafe_allow_html=True)
st.markdown("### Watchlist")

try:
    _session = st.session_state.get("supabase_session")
    _user = getattr(_session, "user", None) if _session else None

    if _user:
        from gad.engine.user_annotations import get_watchlist_drift, delete_trigger_annotation

        _drift_items = get_watchlist_drift(_user.id)

        if _drift_items:
            st.caption(f"{len(_drift_items)} saved trigger(s) — showing firing rate drift since save")

            for _item in _drift_items:
                _saved_rate = _item.get("saved_firing_rate")
                _current_rate = _item.get("current_firing_rate")
                _drift = _item.get("drift")
                _saved_at = _item.get("saved_at", "")[:10] if _item.get("saved_at") else "—"

                # Drift indicator
                if _drift is not None:
                    if _drift > 0.01:
                        _drift_color = "#A63D40"  # red — worse (higher firing)
                        _drift_label = f"+{_drift*100:.1f}%"
                        _drift_arrow = "&#9650;"
                    elif _drift < -0.01:
                        _drift_color = "#2E8B6F"  # green — improved (lower firing)
                        _drift_label = f"{_drift*100:.1f}%"
                        _drift_arrow = "&#9660;"
                    else:
                        _drift_color = "#7A7267"
                        _drift_label = "0.0%"
                        _drift_arrow = "&#8212;"
                else:
                    _drift_color = "#7A7267"
                    _drift_label = "—"
                    _drift_arrow = ""

                _saved_pct = f"{_saved_rate*100:.1f}%" if _saved_rate is not None else "—"
                _current_pct = f"{_current_rate*100:.1f}%" if _current_rate is not None else "—"
                _note_text = f' — <em>{_item["note"]}</em>' if _item.get("note") else ""

                _wl_col1, _wl_col2 = st.columns([5, 1])
                with _wl_col1:
                    st.markdown(f"""
                    <div style="background:#EDE7E0;border:1px solid #D4CCC0;border-radius:6px;padding:12px 16px;margin-bottom:8px;">
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <div>
                                <span style="font-weight:600;color:#1E1B18;">{_item['trigger_id']}</span>
                                <span style="color:#7A7267;font-size:12px;margin-left:8px;">saved {_saved_at}</span>
                                {f'<span style="color:#7A7267;font-size:12px;">{_note_text}</span>' if _note_text else ''}
                            </div>
                            <div style="font-family:monospace;font-size:13px;">
                                <span style="color:#7A7267;">{_saved_pct}</span>
                                <span style="color:#7A7267;"> &#8594; </span>
                                <span style="color:#1E1B18;">{_current_pct}</span>
                                <span style="color:{_drift_color};font-weight:600;margin-left:8px;">{_drift_arrow} {_drift_label}</span>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                with _wl_col2:
                    if st.button("Remove", key=f"rm_{_item['trigger_id']}"):
                        delete_trigger_annotation(_user.id, _item["trigger_id"])
                        st.rerun()
        else:
            st.info("No triggers saved to your watchlist yet. Visit a Trigger Profile and click 'Save to Watchlist' to start tracking.")
    else:
        st.info("Sign in to save triggers to your watchlist.")
except Exception as _wl_err:
    st.warning(f"Could not load watchlist: {_wl_err}")

# ── Account (future) ──
st.markdown('<div style="height:24px"></div>', unsafe_allow_html=True)
st.markdown("### Account")
st.info("User accounts, saved triggers, and notification subscriptions will be available in a future update. Currently all features are free and open to everyone.")

# ── Footer ──
from dashboard.components.footer import render_footer
render_footer()
