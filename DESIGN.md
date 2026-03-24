# Design System — Parametric Data

Source of truth for all visual and UI decisions. Read this before making any design changes.

## Product Context
- **What this is:** The world's first open-source actuarial data platform for parametric insurance
- **Who it's for:** Underwriters, risk analysts, reinsurers, and actuaries who value trust, rigor, and verifiability
- **Space/industry:** Parametric insurance, insurtech, financial data infrastructure
- **Project type:** Data-dense monitoring dashboard (Streamlit) with oracle verification layer
- **Positioning:** "Lloyd's of London meets open-source craftsmanship" — warm, precise, authoritative

## Aesthetic Direction
- **Direction:** Industrial-Editorial — the quiet confidence of a published risk ledger, not a SaaS dashboard
- **Decoration level:** Intentional — thin rules, hairline borders, subtle embossed oracle stamps. No blobs, no gradients, no decorative shapes.
- **Mood:** Warm and material where competitors are cold and digital. Authority through legibility and daylight, not darkness. The product should feel like a freshly printed actuarial report on fine paper — not a screen in a bunker.
- **Reference sites:** WorldMonitor.app (dark OSINT command center — we deliberately counter this), Exante.io (generic insurtech — we avoid this), OpenBB (dark minimalist), Bloomberg Terminal (density inspiration)
- **Anti-patterns:** No purple gradients, no 3-column icon grids, no centered everything, no decorative blobs, no oversized rounded cards, no generic fintech blue.

## Typography
- **Display/Hero:** Fraunces (variable serif, Google Fonts) — the signature typeface. Quirky ball terminals at display size, serious at text size. No insurtech competitor uses a serif with this character. It says "we've been right for 300 years." Use optical size axis for different roles.
- **Body/UI:** Instrument Sans (Google Fonts) — clean, modern geometric sans. Pairs with Fraunces without fighting it. Used for navigation, labels, body text, buttons.
- **Data/Tables/Hashes:** JetBrains Mono (Google Fonts) — tabular figures (`font-variant-numeric: tabular-nums`), ligatures off. Every number aligned, every hash readable. Copper-tinted (`#7A2E1F`) for data emphasis.
- **Code:** JetBrains Mono
- **Loading:** Google Fonts CDN — `Fraunces:ital,opsz,wght@0,9..144,300..800;1,9..144,400`, `Instrument+Sans:wght@400;500;600;700`, `JetBrains+Mono:wght@400;500;600`
- **Scale:**
  - Hero: 3rem (48px), Fraunces 700, letter-spacing -0.03em
  - Section title: 1.5rem (24px), Fraunces 600, letter-spacing -0.02em
  - Body: 15px, Instrument Sans 400, line-height 1.6
  - UI labels: 13px, Instrument Sans 600, uppercase, letter-spacing 0.04em
  - Data labels: 11px, JetBrains Mono 500, uppercase, letter-spacing 0.08em
  - Data values: 14px, JetBrains Mono 400
  - Headline data (ρ, counts): 28-32px, JetBrains Mono 600
  - Captions: 12px, Instrument Sans 400

**Font blacklist** (never use): Inter, Roboto, Arial, Helvetica, Open Sans, Lato, Montserrat, Poppins, Papyrus, Comic Sans, system-ui as primary.

## Color

- **Approach:** Restrained — warm copper signature with muted operational semantics. Not SaaS blue.

### Core palette
| Token | Name | Hex | Use |
|-------|------|-----|-----|
| `bg` | Parchment | `#F5F0EB` | Page background — warm, never pure white |
| `surface` | Vellum | `#EDE7E0` | Cards, panels, score cards |
| `surface-2` | Stone | `#E3DCD3` | Topbars, secondary surfaces |
| `text` | Obsidian Ink | `#1E1B18` | Primary text — near-black with warmth |
| `text-muted` | Graphite | `#7A7267` | Secondary text, captions, labels |
| `accent` | Burnt Vermillion | `#C8553D` | Primary actions, links, brand accent |
| `accent-strong` | Deep Vermillion | `#A8432E` | Hover/active states |
| `rule` | Sandstone | `#D4CCC0` | Borders, dividers, table rules |

### Semantic (status & data)
| Token | Name | Hex | Background | Use |
|-------|------|-----|------------|-----|
| `success` | Verdigris | `#2E8B6F` | `#E4F2EC` | ρ > 0.7, Lloyd's pass, NORMAL status |
| `warning` | Signal Amber | `#D4A017` | `#FDF5E0` | 0.4 ≤ |ρ| ≤ 0.7, STALE, approaching threshold |
| `danger` | Deep Carmine | `#A63D40` | `#F8EAEA` | |ρ| < 0.4, Lloyd's fail, TRIGGERED |
| `oracle` | Patina Green | `#467B6B` | `#E8F0ED` | Oracle verification, chain status, Ed25519 |
| `neutral` | Warm Gray | `#9B9286` | `#F0ECE7` | Neutral markers (TN), NO DATA |

### Data typography colors
| Token | Hex | Use |
|-------|-----|-----|
| `data-copper` | `#7A2E1F` | Trigger values, ρ scores, measurements |
| `data-coord` | `#5E5A54` | Coordinates, geographic data |
| `data-hash` | `#467B6B` | Oracle hashes, signatures, key IDs |
| `data-time` | `#7A7267` | Timestamps, durations |

### Dark mode
Strategy: invert surfaces, reduce saturation 10-20%, warm up backgrounds.
| Token | Light | Dark |
|-------|-------|------|
| `bg` | `#F5F0EB` | `#1A1714` |
| `surface` | `#EDE7E0` | `#242019` |
| `surface-2` | `#E3DCD3` | `#2E2A22` |
| `text` | `#1E1B18` | `#E8E2D9` |
| `text-muted` | `#7A7267` | `#9B9286` |
| `accent` | `#C8553D` | `#D4704A` |
| `rule` | `#D4CCC0` | `#3D3730` |

## Spacing
- **Base unit:** 8px
- **Density:** Comfortable — generous for long analysis sessions, tight in data zones
- **Scale:** 2xs(2) xs(4) sm(8) md(16) lg(24) xl(32) 2xl(48) 3xl(64)
- **Score card:** Padding 20px 24px; margin-bottom 12px
- **Checklist items:** 6px vertical margin; 12px left padding for pass/fail border
- **Data tables:** 10px 14px cell padding

## Layout
- **Approach:** Grid-disciplined with editorial tension
- **Grid:** Full-width on Streamlit; content max-width 1120px where applicable
- **Border radius:** Hierarchical — sm: 3px (badges, inputs), md: 6px (cards, panels). Never above 6px. Rectangles should feel cut, not bubbly.
- **Headers:** Left-aligned, never centered. Section titles flush to grid edge.
- **Whitespace:** Directional — more space above and left, tighter in data zones. Density contrast: one large analytical canvas, then narrow evidence columns.

## Motion
- **Approach:** Minimal-functional — mechanical and measured, never floaty
- **Easing:** enter(ease-out) exit(ease-in) move(ease-in-out)
- **Duration:** micro(50-100ms) short(150-250ms) medium(250-400ms)
- **Allowed:** Count-up animations for trigger totals and monitored assets. Panel reveals left-to-right. Map transitions mechanical.
- **Forbidden:** Bouncy/spring animations, decorative transitions, floaty entrances.

## Streamlit Theme

Configured in `.streamlit/config.toml`:
```toml
[theme]
base = "light"
primaryColor = "#C8553D"
backgroundColor = "#F5F0EB"
secondaryBackgroundColor = "#EDE7E0"
textColor = "#1E1B18"
font = "sans serif"
```

Custom CSS loads Fraunces, Instrument Sans, and JetBrains Mono from Google Fonts for headings, body, and data elements respectively.

## Components

### Score card
- Background `surface`, border `rule`, rounded 6px.
- Headline: Spearman ρ (large, JetBrains Mono, `data-copper`), color by semantic (verdigris/amber/carmine).
- Sub: 95% CI and Lloyd's pass rate in `text-muted`.

### Lloyd's checklist
- Each row: criterion ID + name, pass/fail badge, one-line explanation.
- **Pass:** left border `success` (4px).
- **Fail:** left border `danger` (4px).

### Status badges
- Inline JetBrains Mono badges, 11px, uppercase, with semantic background colors:
  - `TRIGGERED`: carmine text on `#F8EAEA` bg
  - `NORMAL`: verdigris text on `#E4F2EC` bg
  - `NO DATA`: warm gray text on `#F0ECE7` bg
  - `STALE`: amber text on `#FDF5E0` bg
  - `VERIFIED ✓`: patina green text on `#E8F0ED` bg

### Oracle determination — notarial artifact
The most distinctive UI element. Each signed determination renders as an embossed certificate:
- Container: `surface` background, `rule` border, 6px radius
- **Corner crop marks:** 16px L-shaped borders in `oracle` color (0.4 opacity) at top-left and bottom-right corners. CSS `::before` and `::after` pseudo-elements.
- **Stamp header:** Circle icon (⊕) + "CRYPTOGRAPHICALLY SIGNED DETERMINATION" in JetBrains Mono 10px, uppercase, letterspaced 0.15em, `oracle` color.
- **Headline:** Fraunces 1.3rem for trigger ID and determination result.
- **Fields grid:** 2-column grid showing determination ID, trigger ID, status, timestamp, data snapshot hash, previous hash. All in JetBrains Mono with `data-hash` color.
- **Signature block:** Divider, then Ed25519 signature prefix + key_id in JetBrains Mono 11px, with "CHAIN VERIFIED ✓" badge.
- **Feel:** Stamped, notarized, physical. Not a green checkmark, not a blockchain glow.

### Charts (Plotly)
- Theme: light. `paper_bgcolor` / `plot_bgcolor` = `#F5F0EB`.
- Bar colors: trigger `#C8553D`, loss `#467B6B`, mismatch `#A63D40`.
- Scatter quadrant colors: TP verdigris, FP carmine, FN amber, TN neutral.
- Font: Instrument Sans for labels, JetBrains Mono for tick values.

### Buttons
- Primary: `accent` background, white text. Uppercase, 13px, letterspaced.
- Secondary: `surface-2` background, `text` color, `rule` border.
- Ghost: transparent, `accent` text and border.
- Oracle: `oracle` background, white text.
- Danger: `danger` background, white text.
- Border radius: 3px. Never rounded-full.

### Form inputs
- JetBrains Mono for values. `bg` background, `rule` border, 3px radius.
- Focus: `accent` border with 2px rgba(200,85,61,0.12) ring.

### Alerts
- Left border 3px, semantic color. Background uses semantic-bg token.
- Text in semantic color. 13px Instrument Sans.

## Accessibility
- Chart alt text on every Plotly figure.
- Color-blind safe: always pair color with text labels or icons (never color-only).
- WCAG AA: contrast >= 4.5:1 normal text, >= 3:1 large text. Parchment background (#F5F0EB) with obsidian ink (#1E1B18) = 14.2:1.
- Touch targets >= 44px on interactive elements.

## Responsive
- **Desktop (>1024px):** Sidebar collapsed by default (user can expand).
- **Tablet (768-1024px):** Sidebar collapsed; content full-width.
- **Mobile (<768px):** Sidebar collapsed; cards stack; tables scroll horizontally; oracle fields grid collapses to 1 column.
- All pages use `initial_sidebar_state="collapsed"` for mobile-first layout.

## Performance
- **Fonts:** 3 Google Fonts loaded via `<link>` with `display=swap`. Adds ~100-150ms but provides brand identity. Acceptable tradeoff vs. system fonts.
- **CSS:** Minimal inline styles via Streamlit `st.markdown`. Theme handles base colors.
- **No heavy assets:** No icon libraries, no decorative images, no animations beyond count-up.

## Export (PDF)
- Use Helvetica for body and tables (ReportLab built-in); keep layout compact.
- Reuse semantic intent (pass/fail) via table styling, not only color.
- Accent color in headers and key metrics.

## Global Monitor
- **Map:** PyDeck ScatterplotLayer. Marker colors use semantic tokens (verdigris normal, carmine triggered, amber stale).
- **Trigger cards:** `surface` background, `rule` border, 6px rounded corners.
- **Layout:** Full-width map above trigger data. Each peril category wrapped in a collapsible `st.expander` (collapsed by default). PREI country risk index also collapsible.
- **Tooltips:** Parchment card with subtle shadow, JetBrains Mono text.

## Oracle / Settlement
Oracle status page on Cloudflare Worker (`oracle.parametricdata.io`) retains its own dark palette — this is the verification endpoint, not the dashboard. The dashboard Oracle Ledger page uses the standard parchment theme with the notarial artifact component for determinations.

## Decisions Log
| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-19 | Initial design system — system fonts, GitHub Primer palette | v0.1 launch, speed over identity |
| 2026-03-24 | Identity upgrade — Fraunces + Instrument Sans + JetBrains Mono, parchment + burnt vermillion palette, oracle notarial artifact | Competitive research showed gap: no one owns "warm, authoritative, light" in insurance/data. Informed by Codex + Claude subagent independent proposals. All three voices converged on warm surfaces, copper accents, editorial serif, and physical-feeling oracle stamps. |
