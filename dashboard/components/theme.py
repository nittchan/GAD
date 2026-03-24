"""
Shared theme CSS for all dashboard pages.
Loads Google Fonts and applies the parchment + burnt vermillion design system.
"""

GOOGLE_FONTS_LINK = (
    '<link href="https://fonts.googleapis.com/css2?family='
    'Fraunces:ital,opsz,wght@0,9..144,300..800;1,9..144,400&'
    'family=Instrument+Sans:wght@400;500;600;700&'
    'family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">'
)

THEME_CSS = """
<style>
    /* ── Fonts ── */
    h1, h2, h3 { font-family: 'Fraunces', Georgia, serif !important; letter-spacing: -0.02em; color: #1E1B18 !important; text-wrap: balance; }
    h1 { font-size: 1.5rem !important; font-weight: 600 !important; }
    h2 { font-size: 1.25rem !important; font-weight: 600 !important; }
    p, span, label, div, li, td, th { font-family: 'Instrument Sans', system-ui, sans-serif; }
    code, pre, .stCode { font-family: 'JetBrains Mono', ui-monospace, monospace !important; font-variant-numeric: tabular-nums; }

    /* ── Chrome hide ── */
    [data-testid="stSidebarNav"] { display: none; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    [data-testid="stDecoration"] { display: none; }

    /* ── Sidebar surface-2 ── */
    [data-testid="stSidebar"] { background: #E3DCD3 !important; }

    /* ── Form inputs ── */
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stTextArea"] textarea {
        font-family: 'JetBrains Mono', ui-monospace, monospace !important;
        font-variant-numeric: tabular-nums;
        border-radius: 3px !important;
    }
    [data-testid="stTextInput"] input:focus,
    [data-testid="stNumberInput"] input:focus {
        border-color: #C8553D !important;
        box-shadow: 0 0 0 2px rgba(200,85,61,0.12) !important;
    }

    /* ── Buttons ── */
    .stButton > button {
        border-radius: 3px !important;
        font-family: 'Instrument Sans', sans-serif !important;
        text-transform: uppercase;
        font-size: 13px !important;
        letter-spacing: 0.04em;
    }
    .stButton > button:hover {
        background-color: #A8432E !important;
        border-color: #A8432E !important;
    }

    /* ── Data typography ── */
    .data-copper { color: #7A2E1F; font-family: 'JetBrains Mono', monospace; font-variant-numeric: tabular-nums; }
    .data-hash { color: #467B6B; font-family: 'JetBrains Mono', monospace; font-variant-numeric: tabular-nums; }
    .data-coord { color: #5E5A54; font-family: 'JetBrains Mono', monospace; font-variant-numeric: tabular-nums; }
    .data-time { color: #7A7267; font-family: 'JetBrains Mono', monospace; font-variant-numeric: tabular-nums; }

    /* ── Count-up animation ── */
    @keyframes countUp {
        from { opacity: 0; transform: translateY(8px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .stat-animate { animation: countUp 150ms ease-out; }
</style>
"""

THEME_BLOCK = GOOGLE_FONTS_LINK + THEME_CSS


def inject_theme(st):
    """Call once at the top of each page after set_page_config."""
    st.markdown(THEME_BLOCK, unsafe_allow_html=True)
