# Design language — extracted from the user's HTML 10

Source of truth for the five-screen front end. **Do not substitute values from
the previous workspace styling.** This is a light theme; the retired workspace
was dark. Everything below is copied verbatim from the user's file.

## Type
| Role | Family | Notes |
|---|---|---|
| Display / headings | `'Playfair Display', Georgia, serif` | 600/700, italic 600 available |
| Body / UI | `'Plus Jakarta Sans', 'Inter', -apple-system, sans-serif` | 400–800 |
| Numerics / technical | `'Roboto Mono', monospace` | telemetry values, IDs, formulas |

Hero 34px serif 700 / line-height 1.25. Section title 22px serif 700.
Body 13.5–14px sans. Labels 10–11.5px sans 700 uppercase, letter-spacing 0.4–0.5px.

## Colour tokens
```
--m3-canvas:            #F8F9FA
--m3-surface:           #FFFFFF
--m3-surface-subtle:    #F1F3F4
--m3-surface-variant:   #E8EAED

--m3-border:            #DADCE0
--m3-border-subtle:     #ECEFF1
--m3-border-strong:     #BDC1C6

--m3-primary:           #1A73E8
--m3-primary-hover:     #1557B0
--m3-primary-container: #E8F0FE
--m3-on-primary-container: #174EA6

--m3-critical:          #D93025
--m3-critical-container:#FCE8E6
--m3-on-critical:       #C5221F

--m3-success:           #1E8E3E
--m3-success-container: #E6F4EA

--m3-text-primary:      #202124
--m3-text-secondary:    #5F6368
--m3-text-tertiary:     #80868B
```

## Elevation and radius
```
--shadow-xs: 0 1px 2px rgba(60,64,67,0.05)
--shadow-sm: 0 1px 3px rgba(60,64,67,0.08), 0 1px 2px rgba(60,64,67,0.04)
--shadow-md: 0 4px 6px -1px rgba(60,64,67,0.1), 0 2px 4px -1px rgba(60,64,67,0.06)
--radius-sm: 6px   --radius-md: 8px   --radius-lg: 12px   --radius-full: 9999px
```

## Layout grammar
- Header: 56px, sticky, `z-index:200`, surface bg, 1px bottom border, 0 28px padding.
- Nav: 5 tabs, 24px gap, 13.5px/600. Active = `--m3-primary` + 2.5px bottom border.
- Main: `max-width:1200px`, `margin:0 auto`, `padding:36px 24px 80px`.
- Screen panes: `.screen-pane` / `.screen-pane.active`, fadeIn 0.2s, translateY(4px).
- Grids: headwinds 3-col, levers 4-col, outcomes 4-col, telemetry 3-col, all 16–24px gap.

## Component vocabulary
- `.card` — surface, 1px border, radius-md, 24px padding, shadow-xs.
- `.badge` — pill, 4px 10px, 11.5px/700 uppercase, letter-spacing 0.2px.
  Variants: `badge-optimal`, `badge-critical`, `badge-stable`, `badge-primary`.
- `.btn` / `.btn-primary` — 8px 16px, radius-sm, 13px/600.
- Section eyebrow: 11px/700 primary, uppercase, letter-spacing 0.5px.
- Left-rule heading: `::before` 3px x 18px primary block, 10px gap.
- Dark code/formula box: bg `#202124`, text `#E8EAED`, mono 11–11.5px.
- Slide-over drawer: 440px, fixed right, `translateX(100%)` → `0`,
  `cubic-bezier(0.16,1,0.3,1)` 0.25s, `-8px 0 28px rgba(0,0,0,0.18)`.

## Motion
Quiet by rule. Entry animations last 0.24-0.32s and travel no more than 5px;
hover lifts are 1px. Motion is spent where it carries meaning the static layout
cannot, and nowhere else.

- `fadeIn` 0.2s ease-in-out on pane activation.
- `pulseAlert` 1.2s infinite on critical node dot.
- `riseIn` 0.28s staggered 38ms across the architecture stack — the layers
  assemble top-down, which is the order the screen's argument is made in. Runs
  once, on first sight.
- `riseIn` 0.24s staggered 45ms across a decision's five stages, on each deep
  dive, because a decision is a sequence.
- `seamDrift` 3.4s alternate on the stack's seam arrows — 2px, and the two
  arrows move apart, which is the whole reason both are drawn. The only
  continuous motion on the architecture screen.
- `layerIn` 0.32s on the data graph once its layout settles, so it arrives
  rather than snaps.
- Hover lifts: `translateY(-1px)` + primary border + coloured shadow.
- Particle canvas at 60fps over an SVG connector layer, `requestAnimationFrame`.

Entry animations are applied by adding `.motion-playing` and **removing it when
the run ends**. Left on, the rule's `opacity: 0` re-applies every time the pane
is shown again — `display: none` restarts CSS animations — so the element
replays and briefly vanishes on each visit.

Everything above is switched off under `prefers-reduced-motion: reduce`,
including the inherited `fadeIn` and `pulseAlert`: a guard that covers only the
newest additions is not honouring the setting.

## Nav / routing contract
Five tabs, hash-routed: `macro`, `schematic`, `personas`, `ecosystem`, `architecture`.
`#governance` is the fifth screen's former name and redirects to `#architecture`.
Panes are `#pane-<id>`, tabs are `#tab-<id>`, `role="tab"` + `aria-selected`.
`switchScreen(id)` validates against the whitelist and falls back to `macro`.
