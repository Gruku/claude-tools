# Reality Reprojection — Design Rules

> These rules are non-negotiable. Violating any creates visual incoherence with the system.

## Motion Rules

- ONLY use system easing tokens — never raw CSS easing keywords or cubic-bezier values:
  - `--ease-hourglass`: `cubic-bezier(0.4, 0, 0.2, 1)` — Smooth continuous flow, default for most transitions
  - `--ease-hourglass-settle`: `cubic-bezier(0.34, 1.56, 0.64, 1)` — Slight overshoot before rest, toggle snaps
  - `--ease-pendulum`: `cubic-bezier(0.25, 0.1, 0.25, 1)` — Even metered swing, staggered reveals, progress bars
  - `--ease-bell`: `cubic-bezier(0.0, 0.0, 0.2, 1)` — Sharp impact, alerts entering, modal snap
- NEVER use `ease`, `ease-in`, `ease-out`, `ease-in-out`, `linear`, or raw `cubic-bezier()` values
- `scale()` is ONLY allowed inside Bell impact `@keyframes`. NEVER on hover. NEVER on any interactive state.
- Hover transforms by component type:
  - Buttons, pagination: `translateY(-1px)` — vertical micro-lift
  - Tags, nav items, dropdown items: `translateX(2px)` — horizontal rightward shift
  - Cards (tilt variant): `perspective(1000px) rotateY(2deg) translateY(-3px)` — 3D rotation
  - Cards (standard): `translateY(-2px)` — gentle float
  - Small variants (`.btn--sm`): hover transform suppressed entirely
- Duration tiers:
  - `--dur-micro` (`80ms`) — Snappy feedback: button press, toggle snap, active state
  - `--dur-standard` (`200ms`) — Considered transition: hover, color shift, focus
  - `--dur-macro` (`400ms`) — Spatial journey: panel open, modal enter, accordion expand

## Typography Rules

- All font sizes MUST be whole pixels. Never fractional (no `13.5px`, no `0.875rem` that resolves to a fraction).
- Three voices only:
  - **Declaration** = Syne, weight 800, for headings/titles/commands. Always uppercase.
  - **Narrator** = DM Sans, weights 400/600/700, for body/interface text.
  - **Technical** = JetBrains Mono, weight 600, for code/data/labels.
- No other fonts. No italic styling. Emphasis through weight variation only.
- Narrator whisper (13px) gets bumped to weight 600 for readability at small sizes.
- Section labels: Technical voice at 10-11px, `--tracking-ultra` (0.12em), uppercase, weight 800.

## Radius Rules

- Only allowed values:
  - `--radius-xs`: `2px`
  - `--radius-sm`: `3px`
  - `--radius-md`: `4px`
  - `--radius-lg`: `6px`
  - `--radius-xl`: `8px`
  - `--radius-full`: `9999px` (pills, fully rounded)
- These are manufactured, LEGO-like edges. Never "pillowy" or organic.
- No other radius values. If a design needs rounding, pick the nearest allowed value.

## Color Rules

- NEVER hardcode hex/rgb/rgba colors. Always use system tokens.
- `--foreground-on-accent` (`#f5f3ed`) for text on colored backgrounds — stays light in BOTH polarities.
- Signature is `#00d3fa` (cyan). Two accent hues: lime `#64fa00` and pink `#fa017b`.
- Ground scale has warm-neutral bias (not pure gray). Off-extremes: darkest `#0d0d0c`, lightest `#f5f3ed`.
- Semantic colors have three tiers: base, subtle (background tint), bold (darker emphasis).

## Material Rules

- Grain is selective per-element via `::before` pseudo-element. NEVER a global page overlay on body/html.
- Frost requires all four: `backdrop-filter: blur()` + translucent background + subtle border + box-shadow.
- Chromatic aberration is subtle — pink channel shifts left, lime channel shifts right.
- GPU performance: grain elements need `will-change: opacity`, `backface-visibility: hidden`, `transform: translateZ(0)`.

## Polarity Rules

- Support both dark and light via `[data-polarity]` attribute on `<html>`.
- Dark is NOT primary — both modes are equally considered.
- Shadow values change between modes (lighter, warmer `rgba(38, 37, 35, ...)` tones in light mode).
- `--foreground-on-accent` does NOT change between modes (stays `#f5f3ed`).
- Ground scale inverts: `--ground-0` is darkest in dark mode, lightest in light mode.
- Frost backgrounds switch from dark translucent to light translucent.

## Accessibility Rules

- All animations MUST have `@media (prefers-reduced-motion: reduce)` fallbacks.
- Reduced motion: disable transforms and movement, keep opacity fades only.
- Focus states use `--border-focus` (signature color `#00d3fa`) with visible focus ring.
- Interactive elements must have clear hover/focus/active state differentiation.
- Skeleton loaders disable shimmer animation in reduced-motion.

## Anti-Patterns

| Wrong | Correct | Rule |
|-------|---------|------|
| `transition: all 0.3s ease` | `transition: all var(--dur-standard) var(--ease-hourglass)` | System easing only |
| `transition: all 0.15s linear` | `transition: all var(--dur-micro) var(--ease-hourglass)` | System durations + curves |
| `transform: scale(1.05)` on hover | `transform: translateY(-1px)` on hover | No scale on hover |
| `.btn:hover { transform: scale(1.02) }` | `.btn:hover { transform: translateY(-1px) }` | Buttons lift, never scale |
| `.tag:hover { transform: translateY(-1px) }` | `.tag:hover { transform: translateX(2px) }` | Tags shift right, not up |
| `font-size: 13.5px` | `font-size: 14px` | Whole pixels only |
| `font-size: 0.875rem` | `font-size: 14px` | Whole pixels, prefer px |
| `border-radius: 12px` | `border-radius: var(--radius-xl)` (8px) | Manufactured radii only |
| `border-radius: 50%` | `border-radius: var(--radius-full)` (9999px) | Use token, not percentage |
| `color: #333` | `color: var(--foreground-default)` | Token colors only |
| `color: #00d3fa` | `color: var(--signature)` | Even signature uses token |
| `font-family: Arial, sans-serif` | `font-family: var(--font-narrator)` | System voices only |
| `background: rgba(0,0,0,0.5)` on body | `.element::before { background: var(--grain-texture) }` | Selective grain, not global |
| No `[data-polarity="light"]` overrides | Add light mode section with adjusted tokens | Both polarities required |
| Animation without reduced-motion | Add `@media (prefers-reduced-motion: reduce) { }` | Accessibility required |
