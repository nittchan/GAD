# GAD Design System

Source of truth for UI and export visuals. Target: developers who value trust and rigor — "Bloomberg terminal meets modern data tool", not generic SaaS. Light theme, system fonts, sub-200ms load.

## Color palette

### Backgrounds
| Token       | Hex       | Use                    |
|------------|-----------|------------------------|
| `bg-app`   | `#ffffff` | Page background        |
| `bg-card`  | `#f6f8fa` | Score card, panels     |
| `bg-plot`  | `#ffffff` | Chart background       |

### Borders & surfaces
| Token     | Hex       | Use              |
|-----------|-----------|------------------|
| `border`  | `#d1d9e0` | Card border      |
| `border-subtle` | `#e1e4e8` | Table rows |
| `muted`   | `#656d76` | Captions, labels |

### Semantic (data & status)
| Token   | Hex       | Background | Use                          |
|---------|-----------|------------|------------------------------|
| `green` | `#1a7f37` | `#dafbe1`  | ρ > 0.7, Lloyd's pass, normal |
| `amber` | `#9a6700` | `#fff8c5`  | 0.4 ≤ \|ρ\| ≤ 0.7, stale     |
| `red`   | `#d1242f` | `#ffebe9`  | \|ρ\| < 0.4, Lloyd's fail, critical |
| `accent`| `#0969da` | `#ddf4ff`  | Links, primary actions       |
| `neutral` | `#8b949e` | `#f6f8fa` | Neutral markers (e.g. TN)   |

### Text
| Token    | Hex       | Use           |
|----------|-----------|---------------|
| `text`   | `#1f2328` | Body          |
| `text-muted` | `#656d76` | Secondary text |

## Typography

- **UI / headings:** System sans-serif (`sans-serif`). Streamlit default. No external font loading.
- **Data / numbers / code:** System monospace (`ui-monospace, monospace`). No JetBrains Mono CDN.
- **Scale:** Title ~1.75rem; section ~1rem; body 0.875rem; captions 0.75rem; data block 2rem for headline ρ.
- **Performance:** Zero external font requests. All fonts are system fonts → sub-200ms load.

## Theme

Configured in `.streamlit/config.toml`:
```toml
[theme]
base = "light"
primaryColor = "#0969da"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f6f8fa"
textColor = "#1f2328"
font = "sans serif"
```

This eliminates most CSS overrides. Streamlit dropdowns, selects, buttons, and form elements render correctly with zero custom CSS.

## Spacing

- **Grid:** 8px base. Use multiples (8, 16, 24, 32) for padding and gaps.
- **Score card:** Padding ~1rem 1.25rem; margin-bottom 0.75rem.
- **Checklist items:** 6px vertical margin; 12px left padding for pass/fail border.

## Components

### Score card
- Background `bg-card`, border `border`, rounded 6px.
- Headline: Spearman ρ (large, monospace), color by semantic (green/amber/red).
- Sub: 95% CI and Lloyd's pass rate (e.g. 8/10).

### Lloyd's checklist
- Each row: criterion ID + name, pass/fail badge, one-line explanation.
- **Pass:** left border `green` (4px).
- **Fail:** left border `red` (4px).

### Status badges
- Inline monospace badges with semantic background colors:
  - `TRIGGERED`: red text on `#ffebe9` bg
  - `NORMAL`: green text on `#dafbe1` bg
  - `NO DATA`: muted text on `#f6f8fa` bg
  - `UPDATING`: amber text on `#fff8c5` bg

### Charts (Plotly)
- Theme: light. `paper_bgcolor` / `plot_bgcolor` = `#ffffff`.
- Bar colors: trigger `#0969da`, loss `#8250df`, mismatch `#d1242f`.
- Scatter quadrant colors: TP green, FP red, FN amber, TN neutral.

### Buttons & links
- Primary actions use `accent`. Destructive actions use `red`.

## Accessibility

- Chart alt text on every Plotly figure.
- Color-blind safe: pair color with icons or labels.
- WCAG AA: contrast >= 4.5:1 normal text, >= 3:1 large.
- Touch targets >= 44px on interactive elements.

## Responsive

- **Desktop (>1024px):** Sidebar collapsed by default (user can expand).
- **Tablet (768-1024px):** Sidebar collapsed; content full-width.
- **Mobile (<768px):** Sidebar collapsed; cards stack; tables scroll horizontally.
- All pages use `initial_sidebar_state="collapsed"` for mobile-first layout.

## Performance

- **Target:** Sub-200ms initial load (excluding Streamlit framework overhead).
- **Fonts:** System only — zero external font requests.
- **CSS:** Minimal inline styles. Streamlit theme handles base colors.
- **No external assets:** No CDN fonts, no icon libraries, no decorative images.

## Export (PDF)

- Use Helvetica for body and tables; keep layout compact.
- Reuse semantic intent (e.g. pass/fail) via table styling, not only color.

## Global Monitor

- **Map:** PyDeck ScatterplotLayer. Marker colors use semantic tokens.
- **Trigger cards:** Use `bg-card` background, `border` border, 6px rounded corners.
- **Layout:** Full-width map above trigger cards in 3-column grid per peril category.
- **Tooltips:** White card with shadow, monospace text.

## Oracle / settlement

Oracle status page on Cloudflare Worker (`oracle.parametricdata.io`) retains its own dark palette (`#0a0e1a` background, `#00d4d4` accent). The dashboard Oracle Ledger page uses the standard light theme.
