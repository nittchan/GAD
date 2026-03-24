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
    h1, h2, h3 { font-family: 'Fraunces', Georgia, serif !important; letter-spacing: -0.02em; color: #1E1B18 !important; }
    h1 { font-size: 2rem !important; font-weight: 700 !important; }
    p, span, label, div, li, td, th { font-family: 'Instrument Sans', system-ui, sans-serif; }
    code, pre, .stCode { font-family: 'JetBrains Mono', ui-monospace, monospace !important; }

    /* ── Chrome hide ── */
    [data-testid="stSidebarNav"] { display: none; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    [data-testid="stDecoration"] { display: none; }
</style>
"""

THEME_BLOCK = GOOGLE_FONTS_LINK + THEME_CSS


def inject_theme(st):
    """Call once at the top of each page after set_page_config."""
    st.markdown(THEME_BLOCK, unsafe_allow_html=True)
