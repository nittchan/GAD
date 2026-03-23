# GAD Design System

Source of truth for UI and export visuals. Target: developers who value trust and rigor — "Bloomberg terminal meets modern data tool", not generic SaaS.

## Color palette

### Backgrounds
| Token       | Hex       | Use                    |
|------------|-----------|------------------------|
| `bg-app`   | `#0d1117` | Page background (dark) |
| `bg-card`  | `#161b22` | Score card, panels     |
| `bg-plot`  | `#0d1117` | Chart background       |

### Borders & surfaces
| Token     | Hex       | Use              |
|-----------|-----------|------------------|
| `border`  | `#30363d` | Card border      |
| `muted`   | `#8b949e` | Captions, labels |

### Semantic (data & status)
| Token   | Hex       | Use                          |
|---------|-----------|------------------------------|
| `green` | `#3fb950` | ρ > 0.7, Lloyd's pass        |
| `amber` | `#d29922` | 0.4 ≤ \|ρ\| ≤ 0.7            |
| `red`   | `#f85149` | \|ρ\| < 0.4, Lloyd's fail    |
| `accent`| `#58a6ff` | Links, primary actions       |
| `purple`| `#a371f7` | Secondary series (e.g. loss) |
| `neutral` | `#484f58` | Neutral markers (e.g. TN)  |

### Text
| Token    | Hex       | Use           |
|----------|-----------|---------------|
| `text`   | `#e6edf3` | Body          |
| `text-muted` | `#8b949e` | Secondary text |

## Typography

- **UI / headings:** System sans-serif (`ui-sans-serif`, `system-ui`). Headings: tight letter-spacing (-0.02em).
- **Data / numbers / code:** Monospace — JetBrains Mono, Fira Code, then `ui-monospace`, `monospace`. Use for ρ, CI, trigger IDs, file paths.
- **Scale (minimum viable):** Title ~1.75rem; section ~1rem; body 0.875rem; captions 0.75rem; data block 2rem for headline ρ.

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
- Never hide or silently skip unknown criteria; raise explicit errors.

### Charts (Plotly)
- Theme: dark (`template="plotly_dark"`, `paper_bgcolor` / `plot_bgcolor` = `#0d1117`).
- No 3D. Bar colors: trigger `#58a6ff`, loss `#a371f7`, mismatch `#f85149`.
- Scatter quadrant colors: TP green, FP red, FN amber, TN neutral.

### Buttons & links
- Primary actions use `accent`. Destructive actions use `red`.

## Accessibility

- Chart alt text on every Plotly figure.
- ARIA: sidebar = navigation, main = main, score card = region.
- Color-blind safe: pair color with icons (✓/✗) or labels.
- WCAG AA: contrast ≥ 4.5:1 normal text, ≥ 3:1 large.
- Touch targets ≥ 44px where applicable.

## Responsive

- **Desktop (>1024px):** Sidebar + main panel.
- **Tablet (768–1024px):** Sidebar collapsible; comparison stacks vertically.
- **Mobile (<768px):** Charts stack; score card 2-column grid; timeline horizontal scroll.

## Export (PDF)

- Use Helvetica for body and tables; keep layout compact.
- Reuse semantic intent (e.g. pass/fail) via table styling, not only color.
- One report per trigger: definition, score card, confusion matrix, Lloyd's checklist, short methodology note.

## Global Monitor (v0.2)

The Global Monitor page (`dashboard/pages/6_Global_Monitor.py`) uses the same design system:
- **Map:** PyDeck ScatterplotLayer on `mapbox://styles/mapbox/dark-v11`. Marker colors use semantic tokens: `red` for triggered, `green` for normal, `amber` for stale, `muted` for no data.
- **Trigger cards:** Use `bg-card` background, `border` border, same 6px rounded corners as score cards. Large value in monospace (`JetBrains Mono`), color by semantic status.
- **Status badges:** Inline monospace badges — `TRIGGERED` (red), `NORMAL` (green), `NO DATA` (muted), `UPDATING` (amber).
- **Layout:** Full-width map (450px height) above trigger cards in 3-column grid per peril category.
- **Data:** All data from local cache. Zero external API calls. Footer credits data sources.

## Oracle / settlement (v0.2.2+)

Architecture for signed trigger determinations and the oracle standard is documented in **docs/GAP_ANALYSIS_ORACLE.md**. Data structures: **gad/oracle_models.py** (TriggerEvent, TriggerDetermination). Public key registry: **docs/ORACLE_KEY_REGISTRY.md**. Oracle status page uses a separate palette: `#0a0e1a` background, `#00d4d4` accent (deliberate divergence from dashboard). Review at each version milestone.
