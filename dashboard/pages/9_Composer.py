"""
Product Composer — combine 2-3 perils into a composite parametric product.

The key differentiator vs Parametrix: multi-peril product composition with
AND/OR logic, live evaluation against cached data, and at-a-glance status.
"""

from __future__ import annotations

import streamlit as st

from dashboard.components.theme import inject_theme
from dashboard.components.trigger_selector import build_trigger_options
from gad.monitor.triggers import PERIL_LABELS, get_trigger_by_id

st.set_page_config(
    page_title="Product Composer | Parametric Data",
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

    .composer-card {
        background: #EDE7E0;
        border: 1px solid #D4CCC0;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 16px;
    }
    .composer-label {
        color: #7A7267;
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 4px;
    }
    .composer-value {
        font-family: 'JetBrains Mono', ui-monospace, monospace;
        font-size: 20px;
        font-weight: 700;
        color: #1E1B18;
    }
    .trigger-row {
        background: #F5F0EB;
        border: 1px solid #D4CCC0;
        border-radius: 6px;
        padding: 14px 16px;
        margin-bottom: 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .trigger-row-name {
        font-weight: 600;
        color: #1E1B18;
        font-size: 14px;
    }
    .trigger-row-meta {
        color: #7A7267;
        font-size: 12px;
        margin-top: 2px;
    }
    .status-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 3px;
        font-size: 11px;
        font-weight: 600;
        font-family: 'JetBrains Mono', ui-monospace, monospace;
    }
    .badge-critical { background: #F8EAEA; color: #A63D40; border: 1px solid #A63D40; }
    .badge-normal { background: #E4F2EC; color: #2E8B6F; border: 1px solid #2E8B6F; }
    .badge-no-data { background: #EDE7E0; color: #7A7267; border: 1px solid #D4CCC0; }
    .badge-stale { background: #FDF5E0; color: #D4A017; border: 1px solid #D4A017; }
    .composite-result {
        border-radius: 8px;
        padding: 24px;
        margin: 20px 0;
        text-align: center;
    }
    .composite-fired {
        background: #F8EAEA;
        border: 2px solid #A63D40;
    }
    .composite-normal {
        background: #E4F2EC;
        border: 2px solid #2E8B6F;
    }
    .composite-result-label {
        font-size: 14px;
        font-weight: 600;
        letter-spacing: 1px;
        text-transform: uppercase;
        margin-bottom: 4px;
    }
    .composite-result-value {
        font-family: 'JetBrains Mono', ui-monospace, monospace;
        font-size: 32px;
        font-weight: 700;
    }
    .logic-explain {
        color: #7A7267;
        font-size: 13px;
        margin-top: 8px;
        font-style: italic;
    }
    [data-testid="stSidebar"] a {
        min-height: 44px !important;
        display: flex !important;
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
st.sidebar.page_link("pages/9_Composer.py", label="Product Composer", icon="\U0001f9e9")

# ── Header ──
st.markdown(
    '<p style="font-size:11px;color:#C8553D;letter-spacing:2px;text-transform:uppercase;margin-bottom:4px;">Parametric Data</p>'
    '<h1 style="font-size:28px;font-weight:700;color:#1E1B18;margin-bottom:8px;">Product Composer</h1>'
    '<p style="color:#7A7267;font-size:14px;">Combine 2-3 perils into a composite parametric product. Choose AND (all must fire) or OR (any fires).</p>',
    unsafe_allow_html=True,
)

st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)

# ── Step 1: Name the product ──
st.markdown(
    '<div class="composer-card">'
    '<div class="composer-label">Step 1 — Name your product</div>'
    '</div>',
    unsafe_allow_html=True,
)
product_name = st.text_input(
    "Product name",
    value="My Composite Product",
    placeholder="e.g. Airport Resilience Bundle",
    label_visibility="collapsed",
)

st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

# ── Step 2: Select triggers ──
st.markdown(
    '<div class="composer-card">'
    '<div class="composer-label">Step 2 — Select 2-3 triggers from different perils</div>'
    '</div>',
    unsafe_allow_html=True,
)

sorted_labels, label_to_id = build_trigger_options()

selected_labels = st.multiselect(
    "Select triggers to combine",
    options=sorted_labels,
    default=[],
    max_selections=3,
    placeholder="Type to search by city, peril, or airport code...",
    label_visibility="collapsed",
)

selected_ids = [label_to_id[label] for label in selected_labels]

# Show selected trigger summary
if selected_ids:
    perils_in_product = set()
    for tid in selected_ids:
        t = get_trigger_by_id(tid)
        if t:
            perils_in_product.add(t.peril)

    peril_labels = [PERIL_LABELS.get(p, p) for p in sorted(perils_in_product)]
    st.markdown(
        f'<p style="color:#7A7267;font-size:12px;margin-top:4px;">'
        f'{len(selected_ids)} trigger(s) selected across {len(perils_in_product)} peril(s): '
        f'<strong>{", ".join(peril_labels)}</strong></p>',
        unsafe_allow_html=True,
    )

st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

# ── Step 3: Choose logic ──
st.markdown(
    '<div class="composer-card">'
    '<div class="composer-label">Step 3 — Choose composite logic</div>'
    '</div>',
    unsafe_allow_html=True,
)

logic = st.radio(
    "Composite logic",
    options=["AND", "OR"],
    horizontal=True,
    label_visibility="collapsed",
    help="AND = product fires only when ALL triggers fire. OR = product fires when ANY trigger fires.",
)

logic_explain = {
    "AND": "The product fires only when ALL selected triggers fire simultaneously. Lower payout frequency, lower premium.",
    "OR": "The product fires when ANY selected trigger fires. Higher payout frequency, higher premium.",
}
st.markdown(
    f'<p class="logic-explain">{logic_explain[logic]}</p>',
    unsafe_allow_html=True,
)

st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)

# ── Step 4: Evaluate ──
if len(selected_ids) >= 2:
    st.markdown(
        '<div class="composer-card">'
        '<div class="composer-label">Step 4 — Composite evaluation</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    from gad.engine.product_composer import CompositeProduct, evaluate_composite

    product = CompositeProduct(
        name=product_name,
        triggers=selected_ids,
        logic=logic,
    )
    result = evaluate_composite(product)

    # Composite result banner
    if result.fired:
        st.markdown(f"""
        <div class="composite-result composite-fired">
            <div class="composite-result-label" style="color:#A63D40;">Composite Product Status</div>
            <div class="composite-result-value" style="color:#A63D40;">TRIGGERED</div>
            <p style="color:#A63D40;font-size:13px;margin-top:8px;">
                {result.triggers_fired}/{result.trigger_count} triggers fired
                ({logic} logic)
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="composite-result composite-normal">
            <div class="composite-result-label" style="color:#2E8B6F;">Composite Product Status</div>
            <div class="composite-result-value" style="color:#2E8B6F;">NORMAL</div>
            <p style="color:#2E8B6F;font-size:13px;margin-top:8px;">
                {result.triggers_fired}/{result.trigger_count} triggers fired
                ({logic} logic)
            </p>
        </div>
        """, unsafe_allow_html=True)

    # Individual trigger details
    st.markdown("#### Component Triggers")

    for detail in result.trigger_details:
        # Status badge
        if detail.status == "critical":
            badge_cls = "badge-critical"
            badge_text = "TRIGGERED"
        elif detail.status == "normal":
            badge_cls = "badge-normal"
            badge_text = "NORMAL"
        elif detail.status == "stale":
            badge_cls = "badge-stale"
            badge_text = "STALE"
        else:
            badge_cls = "badge-no-data"
            badge_text = "NO DATA"

        # Value display
        if detail.value is not None:
            value_str = f"{detail.value} {detail.unit}"
            threshold_str = f"threshold: {detail.threshold} {detail.unit}"
        else:
            value_str = "No data"
            threshold_str = ""

        st.markdown(f"""
        <div class="trigger-row">
            <div>
                <div class="trigger-row-name">{detail.trigger_name}</div>
                <div class="trigger-row-meta">{detail.peril_label} &middot; {detail.location}</div>
            </div>
            <div style="text-align:right;">
                <span class="status-badge {badge_cls}">{badge_text}</span>
                <div style="font-family:'JetBrains Mono',monospace;font-size:16px;font-weight:700;color:#1E1B18;margin-top:4px;">
                    {value_str}
                </div>
                <div style="color:#7A7267;font-size:11px;">{threshold_str}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Product summary card
    st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
    st.markdown("#### Product Summary")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown(f"""
        <div class="composer-card">
            <div class="composer-label">Product Name</div>
            <div class="composer-value" style="font-size:16px;">{product_name}</div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div class="composer-card">
            <div class="composer-label">Perils Covered</div>
            <div class="composer-value" style="font-size:16px;">{len(result.perils_covered)}</div>
            <div style="color:#7A7267;font-size:12px;margin-top:4px;">
                {", ".join(PERIL_LABELS.get(p, p) for p in result.perils_covered)}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div class="composer-card">
            <div class="composer-label">Logic</div>
            <div class="composer-value" style="font-size:16px;">{logic}</div>
            <div style="color:#7A7267;font-size:12px;margin-top:4px;">
                {"All must fire" if logic == "AND" else "Any can fire"}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # JSON export
    with st.expander("View product definition (JSON)"):
        import json

        export = {
            "name": product_name,
            "logic": logic,
            "triggers": selected_ids,
            "perils_covered": result.perils_covered,
            "trigger_count": result.trigger_count,
        }
        st.code(json.dumps(export, indent=2), language="json")

elif selected_ids:
    st.info("Select at least 2 triggers to compose a multi-peril product.")

else:
    st.markdown("""
    <div class="composer-card">
        <div class="composer-label">Getting started</div>
        <div style="color:#7A7267;font-size:14px;margin-top:8px;">
            Select 2-3 triggers from different peril categories above to compose a
            multi-peril parametric product. For example, combine a flight delay trigger
            with an air quality trigger and a weather trigger for comprehensive
            airport disruption coverage.
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── Footer ──
from dashboard.components.footer import render_footer
render_footer()
