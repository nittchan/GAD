"""
Trigger profile — full view of any trigger from the 436-trigger registry.
Shows live data, trigger details, and basis risk analysis when available.

Accessed via:
1. Direct navigation (sidebar selectbox)
2. Click-through from Global Monitor (session_state["selected_trigger_id"])
3. URL param: ?trigger=flight-delay-del
"""

from __future__ import annotations

import streamlit as st

from dashboard.components.theme import inject_theme
from dashboard.components.trigger_selector import build_trigger_options
from gad.monitor.triggers import GLOBAL_TRIGGERS, PERIL_LABELS, MonitorTrigger, get_trigger_by_id
from gad.monitor.cache import read_cache_with_staleness
from gad.monitor.sources import openmeteo, openaq, firms, opensky, chirps_monitor, usgs_earthquake, aisstream, noaa_flood, noaa_nhc, ndvi, noaa_swpc, who_don

st.set_page_config(page_title="Trigger Profile | Parametric Data", layout="wide", initial_sidebar_state="collapsed")
inject_theme(st)

# ── Page-specific styles ──
st.markdown("""
<style>
    .stApp { background-color: #F5F0EB; }
    [data-testid="stSidebar"] { background: #EDE7E0; border-right: 1px solid #D4CCC0; }
    header[data-testid="stHeader"] { background: transparent; }
    .detail-card { background: #EDE7E0; border: 1px solid #D4CCC0; border-radius: 8px; padding: 20px; margin-bottom: 16px; }
    .detail-label { color: #7A7267; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; }
    .detail-value { color: #1E1B18; font-size: 20px; font-weight: 700; font-family: 'JetBrains Mono', ui-monospace, monospace; }
    .detail-value-small { color: #1E1B18; font-size: 14px; }
    .status-critical { color: #A63D40; }
    .status-normal { color: #2E8B6F; }
    .status-no-data { color: #7A7267; }

    /* Dark-themed dropdowns */
    [data-testid="stSelectbox"] [data-baseweb="select"] { background-color: #EDE7E0 !important; border-color: #D4CCC0 !important; color: #1E1B18 !important; }
    [data-baseweb="popover"] li { color: #1E1B18 !important; }
    [data-baseweb="popover"] li:hover { background-color: #F5EDEA !important; }
    [data-testid="stSidebar"] a { min-height: 44px !important; display: flex !important; align-items: center !important; }
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
st.sidebar.page_link("app.py", label="Home", icon="🏠")
st.sidebar.page_link("pages/6_Global_Monitor.py", label="Global Monitor", icon="🌍")
st.sidebar.page_link("pages/1_Guided_mode.py", label="Build your own", icon="✨")
st.sidebar.page_link("pages/2_Expert_mode.py", label="Expert mode", icon="📝")
st.sidebar.page_link("pages/3_Trigger_profile.py", label="Trigger profile", icon="📊")
st.sidebar.page_link("pages/4_Compare.py", label="Compare triggers", icon="⚖️")
st.sidebar.page_link("pages/5_Account.py", label="Account", icon="👤")
st.sidebar.page_link("pages/7_Oracle.py", label="Oracle Ledger", icon="🔐")
st.sidebar.page_link("pages/8_Digest.py", label="Daily Digest", icon="📨")

# ── Trigger selector ──
SOURCE_KEY_MAP = {
    "openmeteo": "weather", "openaq": "aqi", "firms": "fire",
    "opensky": "flights", "chirps": "drought", "usgs": "earthquake",
    "aisstream": "marine",
    "usgs_water": "flood",
    "noaa_nhc": "cyclone",
    "ndvi": "ndvi",
    "noaa_swpc": "solar",
    "who_don": "health",
}

# Check if navigated from Global Monitor or URL deep link
pre_selected = st.query_params.get("trigger") or st.session_state.get("selected_trigger_id")

# Build searchable trigger list (rich labels: "Delhi DEL — Flight Delay")
option_labels, trigger_options = build_trigger_options()

# Find default index
default_idx = 0
if pre_selected:
    for i, label in enumerate(option_labels):
        if trigger_options.get(label) == pre_selected:
            default_idx = i
            break

st.sidebar.markdown("---")
selected_label = st.sidebar.selectbox(
    "Select trigger",
    options=option_labels,
    index=default_idx,
    placeholder="Type to search by city, peril, or name...",
)

trigger_id = trigger_options.get(selected_label)

# Sync URL query param for deep linking / bookmarking
if trigger_id:
    st.query_params["trigger"] = trigger_id

trigger = get_trigger_by_id(trigger_id) if trigger_id else None

if not trigger:
    st.info("Select a trigger from the sidebar.")
    st.stop()

# ── Load cached data ──
source_key = SOURCE_KEY_MAP.get(trigger.data_source, trigger.data_source)
data, is_stale = read_cache_with_staleness(source_key, trigger.id)


def _evaluate(trigger: MonitorTrigger, data: dict) -> dict:
    if trigger.data_source == "openmeteo":
        return openmeteo.evaluate_trigger(data, trigger.threshold, trigger.threshold_unit, trigger.fires_when_above)
    elif trigger.data_source == "openaq":
        return openaq.evaluate_trigger(data, trigger.threshold)
    elif trigger.data_source == "firms":
        return firms.evaluate_trigger(data, trigger.threshold)
    elif trigger.data_source == "opensky":
        return opensky.evaluate_trigger(data, trigger.threshold)
    elif trigger.data_source == "chirps":
        return chirps_monitor.evaluate_trigger(data, trigger.threshold)
    elif trigger.data_source == "usgs":
        return usgs_earthquake.evaluate_trigger(data, trigger.threshold)
    elif trigger.data_source == "aisstream":
        return aisstream.evaluate_trigger(data, trigger.threshold, trigger.threshold_unit)
    elif trigger.data_source == "usgs_water":
        return noaa_flood.evaluate_trigger(data, trigger.threshold)
    elif trigger.data_source == "noaa_nhc":
        return noaa_nhc.evaluate_trigger(data, trigger.threshold)
    elif trigger.data_source == "ndvi":
        return ndvi.evaluate_trigger(data, trigger.threshold)
    elif trigger.data_source == "noaa_swpc":
        return noaa_swpc.evaluate_trigger(data, trigger.threshold)
    elif trigger.data_source == "who_don":
        return who_don.evaluate_trigger(data, trigger.threshold)
    return {"fired": False, "value": None, "status": "no_data"}


if data is not None:
    result = _evaluate(trigger, data)
    if is_stale:
        result["status"] = "stale"
else:
    result = {"fired": False, "value": None, "status": "no_data"}

status = result.get("status", "no_data")
value = result.get("value")
unit = result.get("unit", trigger.threshold_unit)

# ── Page Header ──
status_color = "#A63D40" if status == "critical" else "#2E8B6F" if status == "normal" else "#7A7267"
status_label = "TRIGGERED" if status == "critical" else "NORMAL" if status == "normal" else "UPDATING" if status == "stale" else "NO DATA"

st.markdown(
    f'<p style="font-size:11px;color:#C8553D;letter-spacing:2px;text-transform:uppercase;margin-bottom:4px;">{PERIL_LABELS[trigger.peril]}</p>'
    f'<h1 style="font-size:32px;font-weight:700;color:#1E1B18;margin-bottom:4px;">{trigger.name}</h1>'
    f'<p style="color:#7A7267;font-size:14px;margin-bottom:24px;">{trigger.location_label}</p>',
    unsafe_allow_html=True,
)

# ── Live Status Card ──
col1, col2, col3 = st.columns(3)

with col1:
    value_display = f"{value}" if value is not None else "—"
    st.markdown(f"""
    <div class="detail-card">
        <div class="detail-label">Current Value</div>
        <div class="detail-value" style="color:{status_color}">{value_display}</div>
        <div style="color:#7A7267;font-size:12px;margin-top:4px;">{unit}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="detail-card">
        <div class="detail-label">Threshold</div>
        <div class="detail-value">{trigger.threshold}</div>
        <div style="color:#7A7267;font-size:12px;margin-top:4px;">{trigger.threshold_unit} · fires when {'above' if trigger.fires_when_above else 'below'}</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="detail-card">
        <div class="detail-label">Status</div>
        <div class="detail-value" style="color:{status_color}">{status_label}</div>
        <div style="color:#7A7267;font-size:12px;margin-top:4px;">{'Data source: ' + (data.get('source', trigger.data_source) if data else trigger.data_source)}</div>
    </div>
    """, unsafe_allow_html=True)

# ── Trigger Details ──
st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
st.markdown("### Trigger Definition")

d1, d2 = st.columns(2)
with d1:
    st.markdown(f"""
    <div class="detail-card">
        <div class="detail-label">Description</div>
        <div class="detail-value-small">{trigger.description}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="detail-card">
        <div class="detail-label">Geography</div>
        <div class="detail-value-small">Lat: {trigger.lat:.4f} · Lon: {trigger.lon:.4f}</div>
    </div>
    """, unsafe_allow_html=True)

with d2:
    st.markdown(f"""
    <div class="detail-card">
        <div class="detail-label">Peril Type</div>
        <div class="detail-value-small">{PERIL_LABELS[trigger.peril]}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="detail-card">
        <div class="detail-label">Data Source</div>
        <div class="detail-value-small">{trigger.data_source}</div>
    </div>
    """, unsafe_allow_html=True)

# ── Save to Watchlist ──
try:
    _wl_session = st.session_state.get("supabase_session")
    _wl_user = getattr(_wl_session, "user", None) if _wl_session else None
    if _wl_user:
        _wl_note = st.text_input("Note (optional)", key="wl_note", placeholder="e.g. monitoring for Q2 renewal")
        if st.button("Save to Watchlist", key="save_watchlist"):
            from gad.engine.user_annotations import save_trigger_annotation
            _wl_result = save_trigger_annotation(_wl_user.id, trigger.id, note=_wl_note)
            if _wl_result:
                st.success(f"Saved {trigger.name} to your watchlist.")
            else:
                st.warning("Could not save — check that Supabase is configured.")
    else:
        st.caption("Sign in to save this trigger to your watchlist.")
except Exception:
    pass  # Never crash the page if watchlist save fails

# ── Raw Data ──
if data:
    st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
    with st.expander("Raw data from source", expanded=False):
        st.json(data)
    if is_stale:
        st.warning("Data is stale — background fetch will update this automatically.")
else:
    st.info("No data cached yet. The background fetcher will populate this automatically.")

# ── Basis Risk Analysis ──
# Priority: 1) Precomputed JSON, 2) Legacy CSV, 3) Placeholder
from gad.config import BASIS_RISK_DIR as PRECOMPUTED_DIR, SERIES_DIR
import json as _json


@st.cache_data(ttl=3600)
def _load_precomputed_report(trigger_id: str) -> dict | None:
    """Load precomputed basis risk JSON. Cached 1 hour (static data)."""
    path = PRECOMPUTED_DIR / f"{trigger_id}.json"
    if path.is_file():
        return _json.loads(path.read_text(encoding="utf-8"))
    return None


LEGACY_CSV_MAP = {
    "flight-delay-blr": SERIES_DIR / "flight_delay_indigo.csv",
    "drought-kenya-marsabit": SERIES_DIR / "kenya_drought.csv",
}

precomputed_path = PRECOMPUTED_DIR / f"{trigger.id}.json"
csv_path = LEGACY_CSV_MAP.get(trigger.id)

if precomputed_path.is_file():
    # ── Precomputed basis risk (from scripts/precompute_basis_risk.py) ──
    st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
    st.markdown("### Basis Risk Analysis")
    st.caption("Precomputed historical back-test using the GAD engine")

    with st.spinner("Loading basis risk analysis..."):
        try:
            from gad.engine.models import BasisRiskReport
            from dashboard.components import (
                render_score_card, timeline_fig, scatter_fig,
                confusion_matrix_fig, confusion_matrix_markdown,
                chart_summary, render_lloyds_checklist,
            )

            report_data = _load_precomputed_report(trigger.id)
            report = BasisRiskReport(**report_data)

            render_score_card(report)
            c1, c2 = st.columns(2)
            with c1:
                st.plotly_chart(timeline_fig(report), use_container_width=True, config={"displayModeBar": False})
                st.caption(chart_summary(report))
            with c2:
                st.plotly_chart(scatter_fig(report), use_container_width=True, config={"displayModeBar": False})
                st.caption(chart_summary(report))

            st.plotly_chart(confusion_matrix_fig(report), use_container_width=True, config={"displayModeBar": False})
            st.markdown(confusion_matrix_markdown(report))
            render_lloyds_checklist(report)

            # PDF export if engine trigger can be built
            try:
                from gad.engine import TriggerDef
                from gad.engine.models import DataSourceProvenance
                from gad.engine.pdf_export import generate_lloyds_report

                engine_trigger = TriggerDef(
                    name=trigger.name,
                    peril=trigger.peril,
                    threshold=trigger.threshold,
                    threshold_unit=trigger.threshold_unit,
                    data_source=trigger.data_source,
                    geography={"type": "Point", "coordinates": [trigger.lon, trigger.lat]},
                    provenance=DataSourceProvenance(
                        primary_source=trigger.data_source,
                        primary_url="https://parametricdata.io",
                        max_data_latency_seconds=3600,
                        historical_years_available=5,
                    ),
                    trigger_fires_when_above=trigger.fires_when_above,
                )
                pdf_bytes = generate_lloyds_report(engine_trigger, report)
                st.download_button(
                    "Download Lloyd's PDF",
                    data=pdf_bytes,
                    file_name=f"parametricdata_report_{trigger.id}.pdf",
                    mime="application/pdf",
                )
            except Exception:
                pass  # PDF export is optional
        except Exception as e:
            st.error(f"Failed to load precomputed report: {e}")

elif csv_path and csv_path.is_file():
    # ── Legacy CSV path (2 original triggers) ──
    st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
    st.markdown("### Basis Risk Analysis")
    st.caption("Historical back-test using the GAD engine")

    with st.spinner("Loading basis risk analysis..."):
        try:
            from gad.engine import TriggerDef, compute_basis_risk
            from gad.engine.loader import load_weather_data_from_csv
            from gad.engine.models import DataSourceProvenance
            from dashboard.components import (
                render_score_card, timeline_fig, scatter_fig,
                confusion_matrix_fig, confusion_matrix_markdown,
                chart_summary, render_lloyds_checklist,
            )
            from gad.engine.pdf_export import generate_lloyds_report

            engine_trigger = TriggerDef(
                name=trigger.name,
                peril=trigger.peril,
                threshold=trigger.threshold,
                threshold_unit=trigger.threshold_unit,
                data_source=trigger.data_source,
                geography={"type": "Point", "coordinates": [trigger.lon, trigger.lat]},
                provenance=DataSourceProvenance(
                    primary_source=trigger.data_source,
                    primary_url="https://parametricdata.io",
                    max_data_latency_seconds=3600,
                    historical_years_available=5,
                ),
                trigger_fires_when_above=trigger.fires_when_above,
            )

            weather_data = load_weather_data_from_csv(csv_path)
            report = compute_basis_risk(engine_trigger, weather_data)

            render_score_card(report)
            c1, c2 = st.columns(2)
            with c1:
                st.plotly_chart(timeline_fig(report), use_container_width=True, config={"displayModeBar": False})
                st.caption(chart_summary(report))
            with c2:
                st.plotly_chart(scatter_fig(report), use_container_width=True, config={"displayModeBar": False})
                st.caption(chart_summary(report))

            st.plotly_chart(confusion_matrix_fig(report), use_container_width=True, config={"displayModeBar": False})
            st.markdown(confusion_matrix_markdown(report))
            render_lloyds_checklist(report)

            pdf_bytes = generate_lloyds_report(engine_trigger, report)
            st.download_button(
                "Download Lloyd's PDF",
                data=pdf_bytes,
                file_name=f"parametricdata_report_{trigger.id}.pdf",
                mime="application/pdf",
            )
        except Exception as e:
            st.error(f"Basis risk computation failed: {e}")
else:
    # SL-06b: Try cold-start inference before showing NO DATA
    _cold_start_shown = False
    try:
        from gad.engine.cold_start import infer_cold_start, check_graduation

        _grad = check_graduation(trigger.id)
        if not _grad["graduated"]:
            _cs = infer_cold_start(trigger.id)
            if _cs and _cs["peers_used"] > 0:
                _cold_start_shown = True
                st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
                st.markdown("### Basis Risk Estimate")
                st.caption("Cold-start estimate -- will switch to direct measurement at 30 observations")

                _cs_c1, _cs_c2, _cs_c3 = st.columns(3)
                with _cs_c1:
                    st.markdown(f"""
                    <div class="detail-card">
                        <div class="detail-label">Inferred Mean</div>
                        <div class="detail-value">{_cs['inferred_mean']:.2f}</div>
                        <div style="color:#7A7267;font-size:12px;margin-top:4px;">from {_cs['peers_used']} peers</div>
                    </div>
                    """, unsafe_allow_html=True)
                with _cs_c2:
                    st.markdown(f"""
                    <div class="detail-card">
                        <div class="detail-label">Inferred Firing Rate</div>
                        <div class="detail-value">{_cs['inferred_firing_rate']*100:.1f}%</div>
                        <div style="color:#7A7267;font-size:12px;margin-top:4px;">weighted average</div>
                    </div>
                    """, unsafe_allow_html=True)
                with _cs_c3:
                    _obs_count = _grad.get("observations", 0)
                    st.markdown(f"""
                    <div class="detail-card">
                        <div class="detail-label">Data Progress</div>
                        <div class="detail-value">{_obs_count} / 30</div>
                        <div style="color:#7A7267;font-size:12px;margin-top:4px;">{_grad['progress']:.0f}% to direct measurement</div>
                    </div>
                    """, unsafe_allow_html=True)

                st.progress(min(_grad["progress"] / 100.0, 1.0))
                st.info(f"Inferred from {_cs['peers_used']} peers. Collecting observations -- direct measurement begins at 30.")
    except Exception:
        pass  # SL-06b: Never crash the page if cold-start fails

    if not _cold_start_shown:
        st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="detail-card" style="border-color:#D4CCC0;">
            <div class="detail-label">Basis Risk Analysis</div>
            <div class="detail-value-small" style="color:#7A7267;">
                Historical basis risk analysis requires time-series data for this location.
                Currently showing live monitoring data. Full Spearman &#x3C1;, back-test, and Lloyd's
                scoring will be available when historical data is loaded for this trigger.
            </div>
        </div>
        """, unsafe_allow_html=True)

# ── Distribution Section (SL-02b) ──
try:
    from gad.engine.db_read import get_distribution as _get_dist
    from gad.engine.timeseries import get_trigger_timeseries as _get_ts

    _dist_df = _get_dist(trigger.id, "90d")
    if _dist_df is not None and not _dist_df.empty:
        _dist = _dist_df.iloc[0]

        st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
        st.markdown("### Distribution")
        st.caption("Statistical profile from the last 90 days of observations")

        dc1, dc2, dc3, dc4 = st.columns(4)
        with dc1:
            st.markdown(f"""
            <div class="detail-card">
                <div class="detail-label">Observations</div>
                <div class="detail-value">{int(_dist.get('observation_count', 0))}</div>
            </div>
            """, unsafe_allow_html=True)
        with dc2:
            _mean_val = _dist.get('mean')
            st.markdown(f"""
            <div class="detail-card">
                <div class="detail-label">Mean</div>
                <div class="detail-value">{f'{_mean_val:.2f}' if _mean_val is not None else '---'}</div>
            </div>
            """, unsafe_allow_html=True)
        with dc3:
            _std_val = _dist.get('std')
            st.markdown(f"""
            <div class="detail-card">
                <div class="detail-label">Std Dev</div>
                <div class="detail-value">{f'{_std_val:.2f}' if _std_val is not None else '---'}</div>
            </div>
            """, unsafe_allow_html=True)
        with dc4:
            _fr_val = _dist.get('firing_rate')
            st.markdown(f"""
            <div class="detail-card">
                <div class="detail-label">Firing Rate</div>
                <div class="detail-value">{f'{_fr_val*100:.1f}%' if _fr_val is not None else '---'}</div>
            </div>
            """, unsafe_allow_html=True)

        # Histogram of observation values
        _ts_data = _get_ts(trigger.id, days=90)
        if _ts_data:
            import plotly.graph_objects as go

            _obs_values = [r["value"] for r in _ts_data if r.get("value") is not None]
            if _obs_values:
                _hist_fig = go.Figure()
                _hist_fig.add_trace(go.Histogram(
                    x=_obs_values,
                    marker_color="#C8553D",
                    opacity=0.85,
                    name="Observations",
                ))
                # Threshold vertical line
                _hist_fig.add_vline(
                    x=trigger.threshold,
                    line_dash="dash",
                    line_color="#A63D40",
                    line_width=2,
                    annotation_text=f"Threshold: {trigger.threshold}",
                    annotation_position="top right",
                    annotation_font_color="#A63D40",
                    annotation_font_size=11,
                )
                _hist_fig.update_layout(
                    plot_bgcolor="#F5F0EB",
                    paper_bgcolor="#F5F0EB",
                    font_color="#1E1B18",
                    xaxis_title=trigger.threshold_unit,
                    yaxis_title="Count",
                    showlegend=False,
                    margin=dict(l=40, r=20, t=30, b=40),
                    height=300,
                    xaxis=dict(gridcolor="#E3DCD3"),
                    yaxis=dict(gridcolor="#E3DCD3"),
                )
                st.plotly_chart(_hist_fig, use_container_width=True, config={"displayModeBar": False})
except Exception:
    pass  # SL-02b: Never crash the page if distribution section fails

# ── Threshold Advisor (SL-04c) ──
try:
    from gad.engine.db_read import get_threshold_suggestion as _get_thresh

    _thresh_df = _get_thresh(trigger.id)
    if _thresh_df is not None and not _thresh_df.empty:
        _ts = _thresh_df.iloc[0]
        _suggested = _ts.get("suggested_threshold")
        _conf = _ts.get("confidence", "---")
        _method = _ts.get("method", "---")
        _obs_n = int(_ts.get("observation_count", 0))
        _current = _ts.get("current_threshold", trigger.threshold)

        # Confidence badge color
        _badge_colors = {"high": "#2E8B6F", "medium": "#C8553D", "low": "#7A7267"}
        _badge_color = _badge_colors.get(_conf, "#7A7267")

        st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
        st.markdown("### Threshold Advisor")
        st.caption("AI-optimized threshold suggestion based on historical observations")

        st.markdown(f"""
        <div style="background:#EDE7E0;border:1px solid #D4CCC0;border-radius:8px;padding:20px;margin-bottom:16px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
                <span style="font-size:14px;font-weight:700;color:#1E1B18;">Optimal Threshold Suggestion</span>
                <span style="background:{_badge_color};color:#fff;padding:2px 10px;border-radius:12px;font-size:11px;text-transform:uppercase;letter-spacing:1px;">{_conf}</span>
            </div>
            <div style="display:flex;gap:32px;margin-bottom:12px;">
                <div>
                    <div style="color:#7A7267;font-size:11px;text-transform:uppercase;letter-spacing:1px;">Current</div>
                    <div style="font-size:20px;font-weight:700;color:#1E1B18;font-family:'JetBrains Mono',ui-monospace,monospace;">{_current}</div>
                </div>
                <div style="display:flex;align-items:center;color:#7A7267;font-size:20px;">&#8594;</div>
                <div>
                    <div style="color:#7A7267;font-size:11px;text-transform:uppercase;letter-spacing:1px;">Suggested</div>
                    <div style="font-size:20px;font-weight:700;color:#C8553D;font-family:'JetBrains Mono',ui-monospace,monospace;">{_suggested:.4f if isinstance(_suggested, float) else _suggested}</div>
                </div>
            </div>
            <div style="color:#7A7267;font-size:12px;">
                Method: {_method} &middot; Based on {_obs_n:,} observations
            </div>
        </div>
        """, unsafe_allow_html=True)
except Exception:
    pass  # SL-04c: Never crash the page if threshold advisor fails

# ── Correlated Triggers (SL-07c) ──
try:
    from gad.engine.db_read import get_correlations as _get_corr
    from gad.monitor.triggers import get_trigger_by_id as _get_trig_by_id

    _corr_df = _get_corr(trigger.id, min_phi=0.1)
    if _corr_df is not None and not _corr_df.empty:
        # Show top-5
        _top_corr = _corr_df.head(5)

        st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
        st.markdown("### Correlated Triggers")
        st.caption("Triggers that co-fire with this one (phi coefficient, within 2,000 km)")

        _ct_table = (
            '<div style="background:#EDE7E0;border:1px solid #D4CCC0;border-radius:8px;padding:16px;margin-bottom:16px;">'
            '<table style="width:100%;border-collapse:collapse;font-size:13px;">'
            '<tr style="border-bottom:1px solid #D4CCC0;color:#7A7267;">'
            '<th style="padding:6px 10px;text-align:left;">Trigger</th>'
            '<th style="padding:6px;text-align:right;">Phi</th>'
            '<th style="padding:6px;text-align:right;">Overlap</th>'
            '</tr>'
        )
        for _, _cr in _top_corr.iterrows():
            # Show the *other* trigger in the pair
            _other_id = _cr["trigger_b"] if _cr["trigger_a"] == trigger.id else _cr["trigger_a"]
            _other_t = _get_trig_by_id(_other_id)
            _other_name = f"{_other_t.name} ({_other_t.peril.replace('_', ' ').title()})" if _other_t else _other_id
            _phi_val = _cr["phi_coefficient"]
            _phi_c = "#2E8B6F" if _phi_val >= 0.5 else "#D4A017" if _phi_val >= 0.3 else "#7A7267"
            _ct_table += (
                f'<tr style="border-bottom:1px solid #E3DCD3;">'
                f'<td style="padding:6px 10px;">{_other_name}</td>'
                f'<td style="padding:6px;text-align:right;font-weight:700;color:{_phi_c};'
                f"font-family:'JetBrains Mono',ui-monospace,monospace;\">{_phi_val:.3f}</td>"
                f'<td style="padding:6px;text-align:right;color:#7A7267;">{int(_cr["overlap_count"])}</td>'
                f'</tr>'
            )
        _ct_table += '</table></div>'
        st.markdown(_ct_table, unsafe_allow_html=True)
except Exception:
    pass  # SL-07c: Never crash the page if correlation section fails

# ── Risk Brief (AI-generated) ──
try:
    from datetime import datetime, timezone
    from gad.monitor.intelligence import generate_trigger_brief

    st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
    st.markdown("### Risk Brief (AI-generated)")

    brief = generate_trigger_brief(
        trigger_id=trigger.id,
        trigger_name=trigger.name,
        peril=trigger.peril,
        current_status=status,
        threshold=trigger.threshold,
        value=value,
        rho=None,  # rho populated when precomputed report is available
    )

    # If we have a precomputed report, try to pass rho
    if precomputed_path.is_file():
        try:
            import json as _json2
            _rho_data = _json2.loads(precomputed_path.read_text(encoding="utf-8"))
            _rho_val = _rho_data.get("spearman_rho")
            if _rho_val is not None and _rho_val == _rho_val:  # exclude NaN
                brief = generate_trigger_brief(
                    trigger_id=trigger.id,
                    trigger_name=trigger.name,
                    peril=trigger.peril,
                    current_status=status,
                    threshold=trigger.threshold,
                    value=value,
                    rho=_rho_val,
                )
        except Exception:
            pass

    gen_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    st.markdown(f"""
    <div class="detail-card">
        <div style="color:#1E1B18;font-size:14px;line-height:1.7;">{brief}</div>
        <div style="color:#7A7267;font-size:11px;margin-top:12px;">Generated {gen_time}</div>
    </div>
    """, unsafe_allow_html=True)
except Exception:
    pass  # Never crash the page if intelligence fails

# ── Back to map ──
st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
if st.button("← Back to Global Monitor"):
    st.switch_page("pages/6_Global_Monitor.py")

# ── Footer ──
from dashboard.components.footer import render_footer
render_footer()
