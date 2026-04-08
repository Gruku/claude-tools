# CSS Implementation Map

**Version:** 1.0
**Status:** Living document
**Last Updated:** 2026-02-14

> This document maps every Layer 2 concept to its CSS realization.
> When the documentation says something, this map shows where the code lives.

---

## System Architecture

**Master import:** `css/system.css` (28 files, cascade order critical)

```
Foundations (tokens — WHAT values are)
  reset.css ........... Browser normalization, scrollbar styling
  fonts.css ........... Font stacks, weight tokens
  colors.css .......... Ground scale, signature, semantics, foreground, border, surface
  typography.css ...... Voice classes, size tokens, line-height, tracking
  spacing.css ......... Container widths, gap/padding/margin scale, emitter strengths
  motion.css .......... Easing curves, durations, stagger rates, transition utilities

Materials (surface — HOW things look)
  grain.css ........... 5 grain variants via ::before pseudo
  frost.css ........... Backdrop-blur levels, polarity-aware backgrounds
  shadows.css ......... Shadow scale (sm→elevated), glow, inset
  radii.css ........... Manufactured radii (2/3/4/6/8px), utility classes

Modes (context — WHERE it renders)
  polarity.css ........ Ground inversion, shadow adaptation, frost swap
  survivalist.css ..... Continuous 0-100 degradation dial

Components (elements — WHAT users interact with)
  buttons.css ......... Primary, secondary, ghost, critical + sizes
  cards.css ........... Flat, elevated, compact, spacious, tilt, interactive, signature
  badges.css .......... Semantic indicators (success, warning, critical, info, accent) + pulse
  forms.css ........... Input, select, textarea, checkbox, radio + validation shake
  navigation.css ...... Horizontal/vertical nav, active states, dividers
  modals.css .......... Overlay, modal sizes (sm, lg, full), enter animation
  tables.css .......... Striped, hoverable, compact, bordered, responsive wrap
  lists.css ........... Bordered, compact, flush, nested, with-icon
  headers.css ......... Brand, nav, actions, transparent/sticky/frost variants
  footers.css ......... Minimal, stacked variants
  toggles.css ......... Switch with clockwork thumb, signature active
  tags.css ............ Interactive chips, translateX(2px) hover, semantic variants
  tabs.css ............ Signature underline, vertical variant, panel toggling

Utilities (overrides — LAST in cascade)
  layout.css .......... Grid, flex, stack, cluster, center, full-bleed
  visibility.css ...... Hidden, sr-only, overflow, truncate, responsive hide
  states.css .......... Disabled, active, loading, aria-*, focus, reveal/stagger
```

---

## Typography → CSS

| Doc Concept | CSS Token / Class | File |
|---|---|---|
| Declaration voice | `--font-declaration: 'Syne'` | `fonts.css:11` |
| Declaration weight | `--font-declaration-weight: 800` | `fonts.css:12` |
| Narrator voice | `--font-narrator: 'DM Sans'` | `fonts.css:15` |
| Narrator base weight | `--font-narrator-weight: 600` | `fonts.css:16` |
| Narrator light | `--font-narrator-weight-light: 400` | `fonts.css:17` |
| Narrator medium | `--font-narrator-weight-medium: 600` | `fonts.css:18` |
| Narrator semi | `--font-narrator-weight-semi: 700` | `fonts.css:19` |
| Technical voice | `--font-technical: 'JetBrains Mono'` | `fonts.css:22` |
| Technical weight | `--font-technical-weight: 600` | `fonts.css:23` |
| Declaration class | `.declaration`, `.declaration--hero` through `--h5` | `typography.css:56-69` |
| Narrator class | `.narrator`, `.narrator--large` through `--whisper` | `typography.css:72-90` |
| Technical class | `.technical`, `.technical--default/small/label` | `typography.css:93-102` |
| Section label | `.section-label` (technical voice, ultra tracking) | `typography.css:105-112` |
| Size: whole px only | All `--size-*` tokens in px | `typography.css:16-36` |
| Leading tight | `--leading-tight: 1.15` | `typography.css:39` |
| Leading body | `--leading-body: 1.6` | `typography.css:41` |
| Tracking wide | `--tracking-wide: 0.04em` | `typography.css:47` |
| Tracking ultra | `--tracking-ultra: 0.12em` | `typography.css:48` |

---

## Color → CSS

| Doc Concept | CSS Token | File |
|---|---|---|
| D1: Value (ground scale) | `--ground-0` through `--ground-100` | `colors.css:27-39` |
| D2: Temperature | Warm bias baked into ground hex values | `colors.css:27-39` |
| D3: Hue (semantic) | `--color-success`, `--color-warning`, `--color-critical`, `--color-info` | `colors.css:47-64` |
| D4: Saturation | `--signature` → `--signature-vivid` (dim→muted→base→vivid) | `colors.css:11-14` |
| Signature identity | `--signature: #00d3fa` | `colors.css:11` |
| Signature vivid | `--signature-vivid: #3de6ff` | `colors.css:12` |
| Signature muted | `--signature-muted: #0c8ea4` | `colors.css:13` |
| Signature dim | `--signature-dim: rgba(0, 211, 250, 0.24)` | `colors.css:14` |
| Accent lime | `--accent-lime: #64fa00` | `colors.css` |
| Accent pink | `--accent-pink: #fa017b` | `colors.css` |
| Glow (atmospheric) | `--signature-glow` (0.10), `--signature-glow-strong` (0.20), `--signature-glow-intense` (0.35) | `colors.css:17-19` |
| Foreground hierarchy | `--foreground-bold/default/subtle/disabled` | `colors.css:69-72` |
| Surface elevation | `--surface-ground/raised/overlay` | `colors.css:77-79` |
| Border hierarchy | `--border-default/subtle/strong/focus` | `colors.css:84-87` |
| Off-extremes | `--ground-0: #0d0d0c` (not #000), `--ground-100: #f5f3ed` (not #fff) | `colors.css:27,39` |
| Contrast-safe text | `--foreground-on-accent: #f5f3ed` (stays light in both polarities) | `colors.css:105` |
| Polarity inversion | `[data-polarity="light"]` overrides all `--ground-*` | `polarity.css` |
| Light shadows richer | Shadow RGBA uses warmer values in light mode | `polarity.css:70-89` |

---

## Spacing → CSS

| Doc Concept | CSS Token / Class | File |
|---|---|---|
| Lattice constant (8px) | Base unit for all spacing tokens | `spacing.css` |
| Emitter: Declaration | `--emitter-declaration` (96px territorial claim) | `spacing.css` |
| Emitter: Narrator | `--emitter-narrator` (24px rhythmic intervals) | `spacing.css` |
| Emitter: Technical | `--emitter-technical` (8px dense packing) | `spacing.css` |
| Container widths | `.container`, `.container--narrow`, `.container--wide` | `spacing.css` |
| Gap utilities | `.gap-micro` through `.gap-3xl` | `spacing.css` |
| Margin utilities | `.mb-xs` through `.mb-3xl`, `.mb-declaration/narrator/technical` | `spacing.css` |
| Padding utilities | `.p-micro` through `.p-3xl` | `spacing.css` |

---

## Material → CSS

| Doc Concept | CSS Token / Class | File |
|---|---|---|
| Manufactured not natural | Radii: 2/3/4/6/8px (not 10/14/20) | `radii.css` |
| Grain: selective | `.mat-grain-fine/coarse/concrete/gradient/edge` (::before) | `grain.css` |
| Grain: never global | No body::after — grain applied per-element | `grain.css:3` |
| Grain hierarchy | matte=baseline, fine=elevated, coarse=premium, concrete=architectural | `grain.css:81-87` |
| Frost (frosted glass) | `.mat-frost-light/medium/heavy` (backdrop-filter) | `frost.css` |
| Shadow scale | `--shadow-sm/md/lg/elevated` | `shadows.css` |
| Shadow glow | `--shadow-glow` (signature-tinted) | `shadows.css` |
| Inner highlight | `--highlight-inner: inset 0 1px 0 rgba(255,255,255,0.15)` | `colors.css:102` |
| Radii tokens | `--radius-xs:2` `--radius-sm:3` `--radius-md:4` `--radius-lg:6` `--radius-xl:8` | `radii.css` |

---

## Motion → CSS

| Doc Concept | CSS Token | File |
|---|---|---|
| Hourglass (mass + damping) | `--ease-hourglass: cubic-bezier(0.16, 1, 0.3, 1)` | `motion.css:14` |
| Hourglass Settle (overshoot) | `--ease-hourglass-settle: cubic-bezier(0.34, 1.56, 0.64, 1)` | `motion.css:18` |
| Pendulum (metered) | `--ease-pendulum: cubic-bezier(0.25, 0.1, 0.25, 1)` | `motion.css:22` |
| Bell (impact) | `--ease-bell: cubic-bezier(0.0, 0.0, 0.2, 1)` | `motion.css:26` |
| Duration: micro | `--dur-micro: 80ms` (button press, toggle snap) | `motion.css:33` |
| Duration: standard | `--dur-standard: 200ms` (hover, color shift) | `motion.css:36` |
| Duration: macro | `--dur-macro: 400ms` (panel open, modal enter) | `motion.css:39` |
| Stagger: base | `--stagger-base: 50ms` | `motion.css:44` |
| Stagger: fast | `--stagger-fast: 30ms` | `motion.css:45` |
| Stagger: slow | `--stagger-slow: 80ms` | `motion.css:46` |
| Transition utilities | `.transition-colors/transform/shadow/all` | `motion.css:52-74` |
| Stagger utility | `.stagger-children > *` with `--i` CSS var | `motion.css:79-81` |
| Scroll reveal | `.reveal` + `.is-visible` (IntersectionObserver) | `states.css` |
| Reveal stagger | `.reveal-stagger > .reveal:nth-child(N)` (50ms increments) | `states.css` |
| FORBIDDEN | `ease`, `ease-in-out`, `linear` — NEVER used anywhere | `motion.css:4` |

---

## Component Primitive Usage

Which primitives each component uses:

| Component | Typography | Color | Spacing | Material | Motion |
|---|---|---|---|---|---|
| **Buttons** | Declaration | Signature, foreground-on-accent | space-sm/lg | Inner highlight | Hourglass hover, micro active |
| **Cards** | — | Border, surface | space-lg/xl | Grain (fine), frost | Hourglass hover, macro tilt |
| **Badges** | Technical | Semantic (success/warn/crit) | space-xs | — | Pendulum pulse |
| **Forms** | Narrator labels, Technical inputs | Border-focus=signature | space-sm/md | — | Hourglass focus, Alarm shake |
| **Navigation** | Narrator | Signature active | space-sm/md | — | Hourglass hover |
| **Modals** | — | Overlay-bg, surface | space-xl | Frost | Macro enter |
| **Tables** | Technical headers | Striped ground, semantic badges | space-sm | — | Hourglass row hover |
| **Toggles** | Narrator label | Signature active, ground track | space-sm | — | Hourglass-settle thumb |
| **Tags** | Technical | Semantic variants | space-micro/sm | — | Hourglass translateX(2px) |
| **Tabs** | Narrator | Signature underline | space-sm/md | — | Hourglass color |

---

## Live Preview Pages

Each page exercises the system at a different point on the productive tensions dial:

| Page | Primary Voice | Dial Position | Demonstrates |
|---|---|---|---|
| `rr-test.html` | All three | Catalogue | Every primitive in isolation |
| `preview-landing.html` | Declaration | Monumental + Sensorial | Hero, SVG graphics, motion demos, grain, frost |
| `preview-dashboard.html` | Technical | Utilitarian + Technical | Dense data, tables, badges, toggles, live status |
| `preview-article.html` | Narrator | Intimate + Human | Reading comfort, generous spacing, warm ground |
| `preview-settings.html` | Mixed | Constrained + Technical | Forms, validation, tabs, toggles, danger zone |

---

## Polarity Behavior

How tokens transform between dark and light modes:

| Category | Dark Polarity (default) | Light Polarity |
|---|---|---|
| Ground scale | As defined (dark→light) | Inverted (light→dark) |
| Foreground | Light text on dark ground | Dark text on light ground |
| Shadows | Deep black, subtle | Warm layered, RICHER |
| Frost | `rgba(13,13,12, ...)` base | `rgba(245,243,237, ...)` base |
| Signature | Unchanged | Unchanged |
| Semantic colors | Unchanged | Unchanged |
| foreground-on-accent | `#f5f3ed` (light) | `#f5f3ed` (stays light) |

---

## Survivalist Degradation

How the system degrades along the 0-100 dial:

| Range | What's Available | What's Lost |
|---|---|---|
| 0-25 (Full) | All materials, grain, blur, shadows, full motion | Nothing |
| 25-50 (Rich) | Reduced grain, thinner blur, flatter shadows | Fine texture detail |
| 50-75 (Reduced) | No grain, no blur, no shadows; motion→Tick only | All materials, most motion |
| 75-100 (Survivalist) | Monochrome D1, single weight, filled vs. outlined | Color, typography range, all surfaces |

**Implementation:** `modes/survivalist.css` — `[data-mode="survivalist"]` selector
