# Reality Reprojection — Design Tokens

> Complete reference of all CSS custom properties. Use these tokens exclusively — never hardcode raw values.

## Signature Hue (Identity — Cyan)

- `--signature`: `#00d3fa` — Primary brand color, button fills, focus states
- `--signature-vivid`: `#3de6ff` — Hover state for signature elements, lighter variant
- `--signature-muted`: `#0c8ea4` — Border-bottom depth on buttons, light mode text
- `--signature-dim`: `rgba(0, 211, 250, 0.24)` — Translucent signature, toggle active background
- `--signature-glow`: `rgba(0, 211, 250, 0.10)` — Subtle background tint for accent areas
- `--signature-glow-strong`: `rgba(0, 211, 250, 0.20)` — Focus ring glow, interactive highlights
- `--signature-glow-intense`: `rgba(0, 211, 250, 0.35)` — High-visibility glow for emphasis
- `--signature-fill`: `var(--signature)` — Button fill shorthand
- `--signature-fill-hover`: `var(--signature-vivid)` — Button fill hover shorthand
- `--on-signature`: `var(--foreground-on-accent)` — Text on signature background
- `--signature-text`: `var(--signature)` — Signature as text color (muted to `#4f7f89` in light mode)

## Accent Colors (Two Supporting Hues)

The system uses two accent hues alongside the signature for energy, emphasis, and atmospheric effects (frost arenas, gradients, chips).

### Accent Lime (Energy, Positive)
- `--accent-lime`: `#64fa00` — Primary lime accent, chips, swatches
- `--accent-lime-glow`: `rgba(100, 250, 0, 0.10)` — Subtle background tint
- `--accent-lime-glow-strong`: `rgba(100, 250, 0, 0.20)` — Interactive highlight
- `--accent-lime-subtle`: `rgba(100, 250, 0, 0.08)` — Frost card tint, atmospheric use

### Accent Pink (Warmth, Emphasis)
- `--accent-pink`: `#fa017b` — Primary pink accent, chips, swatches
- `--accent-pink-glow`: `rgba(250, 1, 123, 0.10)` — Subtle background tint
- `--accent-pink-glow-strong`: `rgba(250, 1, 123, 0.20)` — Interactive highlight
- `--accent-pink-subtle`: `rgba(250, 1, 123, 0.08)` — Frost card tint, atmospheric use

### Accent Hover Shadows
- `--shadow-hover-lime`: `0 4px 12px rgba(100, 250, 0, 0.25)` — Lime element hover
- `--shadow-hover-pink`: `0 4px 12px rgba(250, 1, 123, 0.25)` — Pink element hover

## Ground Scale (13-Step Warm-Neutral, Off-Extremes)

Dark mode values shown. In light polarity, the scale inverts (0 becomes lightest, 100 becomes darkest).

- `--ground-0`: `#0d0d0c` — Deepest surface, page canvas (dark mode)
- `--ground-5`: `#151514` — Very dark surface, recessed elements
- `--ground-10`: `#1d1d1b` — Dark surface layer, cards at rest
- `--ground-15`: `#272725` — Dark overlay surface, dropdown hover
- `--ground-20`: `#343331` — Dark border/divider, disabled button bg
- `--ground-30`: `#4d4c48` — Medium-dark neutral
- `--ground-40`: `#66645f` — Disabled text color
- `--ground-50`: `#7d7b76` — Mid-tone neutral
- `--ground-60`: `#a09c95` — Subtle text, secondary content
- `--ground-70`: `#bbb8b1` — Light neutral
- `--ground-80`: `#d2cfc8` — Default text color
- `--ground-90`: `#e6e4dd` — Very light surface
- `--ground-100`: `#f5f3ed` — Lightest extreme, bold text, headings

## Semantic Colors

### Success (Favorable Outcome)
- `--color-success`: `#3a9a5b` — Primary success indicator
- `--color-success-subtle`: `rgba(58, 154, 91, 0.12)` — Soft background tint
- `--color-success-bold`: `#2d7a47` — Darker emphasis

### Warning (Needs Attention)
- `--color-warning`: `#c4881d` — Primary warning indicator
- `--color-warning-subtle`: `rgba(196, 136, 29, 0.12)` — Soft background tint
- `--color-warning-bold`: `#a06f14` — Darker emphasis

### Critical (Error, Destructive)
- `--color-critical`: `#d14343` — Primary error/danger indicator
- `--color-critical-subtle`: `rgba(209, 67, 67, 0.12)` — Soft background tint
- `--color-critical-bold`: `#b33030` — Darker emphasis

### Informational (Guidance)
- `--color-info`: `#5b8fc7` — Primary info indicator
- `--color-info-subtle`: `rgba(91, 143, 199, 0.12)` — Soft background tint
- `--color-info-bold`: `#4574a6` — Darker emphasis

## Foreground (Text & Icons)

- `--foreground-bold`: `var(--ground-100)` — Highest contrast, headings
- `--foreground-default`: `var(--ground-80)` — Standard body text
- `--foreground-subtle`: `var(--ground-60)` — Secondary text, hints
- `--foreground-disabled`: `var(--ground-40)` — Disabled states
- `--foreground-on-accent`: `#f5f3ed` — Text on colored backgrounds (same in BOTH polarities)

## Surface (Layered Elevation)

- `--surface-ground`: `var(--ground-0)` — Base page background
- `--surface-raised`: `var(--ground-10)` — Cards, elevated panels
- `--surface-overlay`: `var(--ground-15)` — Modals, popovers, dropdowns
- `--surface-recessed`: `var(--ground-5)` — Milled channel for inputs, toggle tracks, progress tracks

## Border

- `--border-default`: `var(--ground-20)` — Standard dividers, form borders
- `--border-subtle`: `var(--ground-15)` — Light visual separation
- `--border-strong`: `var(--ground-30)` — Heavy emphasis, active states
- `--border-focus`: `var(--signature)` — Focus ring color (`#00d3fa`)

## Overlay

- `--overlay-bg`: `rgba(13, 13, 12, 0.6)` — Modal/dialog backdrop (dark mode)

## Shadows — Elevation Scale

- `--shadow-sm`: `0 1px 2px rgba(0, 0, 0, 0.25), 0 0 0 1px rgba(0, 0, 0, 0.08)` — Cards at rest
- `--shadow-md`: `0 2px 8px rgba(0, 0, 0, 0.30), 0 1px 2px rgba(0, 0, 0, 0.15)` — Elevated cards, dropdowns
- `--shadow-lg`: `0 8px 24px rgba(0, 0, 0, 0.35), 0 2px 6px rgba(0, 0, 0, 0.18)` — Prominent surfaces
- `--shadow-elevated`: `0 12px 40px rgba(0, 0, 0, 0.40), 0 4px 12px rgba(0, 0, 0, 0.20), 0 0 0 1px rgba(0, 0, 0, 0.05)` — Modals, active dialogs

## Shadows — Accent & Semantic Hover

- `--shadow-signature`: `0 4px 16px rgba(0, 211, 250, 0.25), 0 1px 4px rgba(0, 211, 250, 0.12)` — Brand element glow
- `--shadow-hover-signature`: `0 4px 16px rgba(0, 211, 250, 0.30)` — Signature button hover
- `--shadow-hover-signature-subtle`: `0 4px 12px rgba(0, 211, 250, 0.15)` — Subtle signature hover
- `--shadow-hover-success`: `0 4px 12px rgba(58, 154, 91, 0.25)` — Success button hover
- `--shadow-hover-warning`: `0 4px 12px rgba(196, 136, 29, 0.25)` — Warning button hover
- `--shadow-hover-critical`: `0 4px 12px rgba(209, 67, 67, 0.25)` — Critical button hover
- `--shadow-hover-info`: `0 4px 12px rgba(91, 143, 199, 0.25)` — Info button hover

## Shadows — Soul Pass (Inset & Glow)

- `--shadow-inset`: `inset 0 2px 4px rgba(0, 0, 0, 0.20)` — Pressed/active state
- `--shadow-recessed`: `inset 0 1px 3px rgba(0, 0, 0, 0.15), inset 0 0 0 1px rgba(0, 0, 0, 0.05)` — Milled channel for inputs, toggle tracks
- `--shadow-inner-glow`: `inset 0 1px 0 rgba(255, 255, 255, 0.2)` — Active toggle thumbs, filled progress
- `--highlight-inner`: `inset 0 1px 0 rgba(255, 255, 255, 0.15)` — Manufacturing feel on buttons

## Spacing

### Base Unit
- `--space-base`: `8px` — All spacing derives from this

### Scale
- `--space-micro`: `4px` — Half-base, tight Technical gaps
- `--space-xs`: `8px` — 1x base, minimum meaningful space
- `--space-sm`: `12px` — 1.5x base, compact grouping
- `--space-md`: `16px` — 2x base, standard element spacing
- `--space-lg`: `24px` — 3x base, section gaps, Narrator rhythm
- `--space-xl`: `32px` — 4x base, generous separation
- `--space-2xl`: `48px` — 6x base, major section breaks
- `--space-3xl`: `64px` — 8x base, page-level breathing room

### Voice Emitters
- `--emitter-declaration`: `96px` — Declaration voice claims territory
- `--emitter-narrator`: `24px` — Narrator rhythm (same as `--space-lg`)
- `--emitter-technical`: `8px` — Technical dense packing (same as `--space-xs`)

### Containers
- `--container-max`: `1200px` — Standard max-width
- `--container-narrow`: `720px` — Tight column
- `--container-wide`: `1440px` — Extra-wide layouts
- `--container-padding`: `var(--space-lg)` — Horizontal padding (24px)

## Motion — Easing

- `--ease-hourglass`: `cubic-bezier(0.4, 0, 0.2, 1)` — Smooth flow, default for most transitions
- `--ease-hourglass-settle`: `cubic-bezier(0.34, 1.56, 0.64, 1)` — Elastic snap with damping, toggle thumbs
- `--ease-pendulum`: `cubic-bezier(0.25, 0.1, 0.25, 1)` — Even metered swing, staggered reveals
- `--ease-bell`: `cubic-bezier(0.0, 0.0, 0.2, 1)` — Sharp impact, alerts, modals

## Motion — Durations

- `--dur-micro`: `80ms` — Snappy feedback: button press, toggle snap
- `--dur-standard`: `200ms` — Considered transition: hover, color shift
- `--dur-macro`: `400ms` — Spatial journey: panel open, modal enter

## Motion — Stagger

- `--stagger-base`: `50ms` — Default stagger interval
- `--stagger-fast`: `30ms` — Quick sequential animation
- `--stagger-slow`: `80ms` — Slow deliberate reveals

## Typography — Font Families

- `--font-declaration`: `'Syne', system-ui, -apple-system, sans-serif` — Authority voice
- `--font-narrator`: `'DM Sans', system-ui, -apple-system, sans-serif` — Conversational voice
- `--font-technical`: `'JetBrains Mono', ui-monospace, 'Cascadia Code', 'Fira Code', monospace` — Precision voice

## Typography — Weights

- `--font-declaration-weight`: `800` — Declaration (Syne)
- `--font-narrator-weight`: `600` — Narrator default (DM Sans)
- `--font-narrator-weight-light`: `400` — Narrator light
- `--font-narrator-weight-medium`: `600` — Narrator medium (same as default)
- `--font-narrator-weight-semi`: `700` — Narrator semi-bold
- `--font-technical-weight`: `600` — Technical (JetBrains Mono)

## Typography — Sizes

### Declaration (always uppercase)
- `--size-declaration-hero`: `clamp(56px, 9vw, 112px)` — Responsive hero
- `--size-declaration-h1`: `48px` — Major sections
- `--size-declaration-h2`: `36px` — Section headings
- `--size-declaration-h3`: `28px` — Subsections
- `--size-declaration-h4`: `22px` — Minor headings
- `--size-declaration-h5`: `18px` — Label headings

### Narrator
- `--size-narrator-large`: `20px` — Prominent interface
- `--size-narrator-default`: `16px` — Standard body
- `--size-narrator-small`: `14px` — Secondary text
- `--size-narrator-whisper`: `13px` — Very small (weight bumped to 600)

### Technical
- `--size-technical-default`: `14px` — Standard code/labels
- `--size-technical-small`: `12px` — Compact labels
- `--size-technical-label`: `11px` — Minimal labels, badges

### Section Label
- `--size-section-label`: `10px` — Ultra-small uppercase

## Typography — Line Heights

- `--leading-tight`: `1.15` — Headlines, Declaration voice
- `--leading-heading`: `1.2` — Subheadings
- `--leading-body`: `1.6` — Body text, Narrator voice
- `--leading-loose`: `1.8` — Very loose, accessibility

## Typography — Letter Spacing

- `--tracking-tight`: `-0.02em` — Declaration headlines
- `--tracking-normal`: `0` — Body text default
- `--tracking-wide`: `0.04em` — Technical voice
- `--tracking-ultra`: `0.12em` — Section labels (uppercase small text)

## Frost (Frosted Glass)

### Blur Levels
- `--frost-blur-light`: `8px` — Gentle defocus
- `--frost-blur-medium`: `16px` — Standard frosted glass
- `--frost-blur-heavy`: `24px` — Deep frosted glass

### Background Levels (Dark Mode)
- `--frost-bg-light`: `rgba(13, 13, 12, 0.6)` — Lightest frost tint
- `--frost-bg-medium`: `rgba(13, 13, 12, 0.75)` — Standard frost background
- `--frost-bg-heavy`: `rgba(13, 13, 12, 0.85)` — Densest frost background

### Background Levels (Light Mode)
- `--frost-bg-light`: `rgba(245, 243, 237, 0.6)` — Lightest frost tint
- `--frost-bg-medium`: `rgba(245, 243, 237, 0.75)` — Standard frost background
- `--frost-bg-heavy`: `rgba(245, 243, 237, 0.85)` — Densest frost background

### Utility Classes
- `.mat-frost-light` — Light frost: `--frost-bg-light` + `blur(--frost-blur-light)`
- `.mat-frost-medium` — Standard frost: `--frost-bg-medium` + `blur(--frost-blur-medium)`
- `.mat-frost-heavy` — Dense frost: `--frost-bg-heavy` + `blur(--frost-blur-heavy)`

## Radii

- `--radius-xs`: `2px` — Minimal rounding, precise edges
- `--radius-sm`: `3px` — Small rounding
- `--radius-md`: `4px` — Standard, most elements
- `--radius-lg`: `6px` — Cards, modals
- `--radius-xl`: `8px` — Maximum manufactured rounding
- `--radius-full`: `9999px` — Pills, fully rounded

## Polarity Overrides (Light Mode)

When `[data-polarity="light"]` is set:

### Ground Scale Inverts
- `--ground-0`: `#f5f3ed` (was darkest, now lightest)
- `--ground-100`: `#0d0d0c` (was lightest, now darkest)
- All intermediate values invert correspondingly

### Shadows Soften (warmer tones)
- `--shadow-sm`: `0 1px 3px rgba(38, 37, 35, 0.08), 0 0 0 1px rgba(38, 37, 35, 0.04)`
- `--shadow-md`: `0 2px 8px rgba(38, 37, 35, 0.10), 0 1px 3px rgba(38, 37, 35, 0.06)`
- `--shadow-lg`: `0 4px 14px rgba(38, 37, 35, 0.10), 0 2px 4px rgba(38, 37, 35, 0.06), 0 0 0 1px rgba(38, 37, 35, 0.03)`
- `--shadow-elevated`: `0 8px 30px rgba(38, 37, 35, 0.12), 0 4px 10px rgba(38, 37, 35, 0.08), 0 0 0 1px rgba(38, 37, 35, 0.03)`
- `--shadow-recessed`: `inset 0 1px 3px rgba(38, 37, 35, 0.10), inset 0 0 0 1px rgba(38, 37, 35, 0.04)`
- `--shadow-inner-glow`: `inset 0 1px 0 rgba(255, 255, 255, 0.35)` (stronger)
- `--highlight-inner`: `inset 0 1px 0 rgba(255, 255, 255, 0.25)` (stronger)

### Semantic Hover Shadows (softer)
- `--shadow-hover-success`: `0 4px 12px rgba(58, 154, 91, 0.20)`
- `--shadow-hover-warning`: `0 4px 12px rgba(196, 136, 29, 0.20)`
- `--shadow-hover-info`: `0 4px 12px rgba(91, 143, 199, 0.20)`

### Signature Adapts for Light Ground
- `--signature`: `#00b6d6` — Slightly deeper cyan for light backgrounds
- `--signature-vivid`: `#00d3fa` — Vivid shifts to match dark mode base
- `--signature-muted`: `#0f7f93` — Deeper muted for contrast
- `--signature-dim`: `rgba(0, 182, 214, 0.2)` — Translucent dim
- `--signature-fill`: `#00b5d1` — Button fill on light ground
- `--signature-fill-hover`: `#00c7e4` — Button fill hover on light ground
- `--on-signature`: `#04212a` — Dark text on signature fills (inverts from dark mode)

### Other Overrides
- `--overlay-bg`: `rgba(245, 243, 237, 0.6)` — Light translucent backdrop
- `--signature-text`: `#4f7f89` — Muted for comfortable reading on light backgrounds
- `--foreground-on-accent`: `#f5f3ed` — UNCHANGED (stays light in both polarities)
