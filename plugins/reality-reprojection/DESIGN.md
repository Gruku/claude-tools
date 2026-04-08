# DESIGN.md — Reality Reprojection

A design system built on the premise that interfaces are environments, not pages. Every surface carries material weight — grain texture, frosted glass, manufactured edges — grounded on a 13-step warm-neutral scale that deliberately avoids pure black and pure white. The darkest ground is `#0d0d0c`; the lightest is `#f5f3ed`. Between them, a warm-tinted progression with just enough amber to feel human without feeling warm. Dark and light polarities are co-equal native states: the ground scale inverts, signal hues persist, shadows adapt. Neither mode is primary. Neither is an afterthought.

The system is organized around three typographic voices, each with its own spatial signature. **Declaration** (Syne, weight 800, always uppercase) commands attention and claims territory — its spacing field radiates 96px. **Narrator** (DM Sans, weights 400/600/700) carries content and conversation at a 24px rhythm. **Technical** (JetBrains Mono, weight 600) marks data, metadata, and precision with tight 8px density. These voices are not just fonts — they are the organizing principle of every layout. Spacing is the spatial signature of a voice, not an arbitrary margin.

Surfaces have physical texture. Five grain profiles — from barely-perceptible edge noise to coarse architectural concrete — encode material hierarchy before any text is read. Three frost levels create atmospheric depth through backdrop blur and translucent layering. Four named motion characters govern all transitions: **Hourglass** for smooth continuous flow, **Hourglass-Settle** for elastic snap, **Pendulum** for metered sequential rhythm, and **Bell** for sharp impact. The system also defines a survivalist degradation mode — a 0-to-100 dial that progressively strips grain, blur, shadows, motion, and eventually color, proving that the structure holds without any decoration.

### Key Characteristics

- **Off-extremes:** Darkest `#0d0d0c`, lightest `#f5f3ed` — never pure `#000000` or `#ffffff`. Warm-neutral bias throughout.
- **Dual polarity:** `[data-polarity="dark"]` and `[data-polarity="light"]` on `<html>`. Ground scale inverts. Signal hues persist. Both modes receive equal specification.
- **Signature cyan:** `#00d3fa` — the primary interactive signal, focus indicator, and brand mark. Adjusts to `#00b6d6` in light polarity for contrast.
- **Three signal hues:** Cyan `#00d3fa`, lime `#64fa00`, pink `#fa017b` — deployed with precision, never decoratively.
- **Six manufactured radii:** `{2, 3, 4, 6, 8, 9999}px` only. The gaps are intentional. These are LEGO-like edges, not pillowy curves.
- **Voice-driven spacing:** Declaration emits 96px fields. Narrator emits 24px. Technical emits 8px. Spacing follows voice, not arbitrary values.
- **Named motion:** Hourglass (`cubic-bezier(0.4, 0, 0.2, 1)`), Hourglass-Settle (`cubic-bezier(0.34, 1.56, 0.64, 1)`), Pendulum (`cubic-bezier(0.25, 0.1, 0.25, 1)`), Bell (`cubic-bezier(0.0, 0.0, 0.2, 1)`). No other easing values exist in the system.
- **Material hierarchy:** No grain = baseline. Fine grain = elevated. Coarse grain = premium. Concrete = architectural. Material communicates tier before text.
- **Survivalist mode:** `[data-mode="survivalist"]` strips the system to its structural core — semantic shapes, token colors, system fonts, no blur, no grain. If the design works in survivalist mode, the structure is sound.
- **Decision test:** Does every element exist because it must? Can the user go deeper if they want to? Does this feel like someone cared about making it?

---

## 1. Visual Theme & Atmosphere

See above. The opening section serves as both theme description and design philosophy.

---

## 2. Color Palette & Roles

### Ground Scale (13 Steps, Warm-Neutral, Off-Extremes)

Dark polarity values shown. In light polarity, the scale inverts: step 0 becomes the lightest surface, step 100 becomes the darkest text.

| Step | Hex | Dark Role | Light Role |
|------|-----|-----------|------------|
| `--ground-0` | `#0d0d0c` | Page canvas, deepest surface | Lightest extreme (inverts to `#f5f3ed`) |
| `--ground-5` | `#151514` | Very dark surface, recessed elements | Near-lightest surface |
| `--ground-10` | `#1d1d1b` | Cards at rest, dark surface layer | Light card surface |
| `--ground-15` | `#272725` | Overlay surface, dropdown hover | Light overlay |
| `--ground-20` | `#343331` | Borders, dividers, disabled button bg | Light border/divider |
| `--ground-30` | `#4d4c48` | Medium-dark neutral | Medium-light neutral |
| `--ground-40` | `#66645f` | Disabled text | Disabled text |
| `--ground-50` | `#7d7b76` | Mid-tone neutral | Mid-tone neutral |
| `--ground-60` | `#a09c95` | Subtle text, secondary content | Subtle text |
| `--ground-70` | `#bbb8b1` | Light neutral | Dark neutral |
| `--ground-80` | `#d2cfc8` | Default text color | Near-darkest text |
| `--ground-90` | `#e6e4dd` | Very light surface | Very dark surface |
| `--ground-100` | `#f5f3ed` | Lightest extreme, bold text | Deepest surface (inverts to `#0d0d0c`) |

### Signal Hues

#### Signature Cyan (Identity)

| Token | Dark | Light | Role |
|-------|------|-------|------|
| `--signature` | `#00d3fa` | `#00b6d6` | Primary brand, button fills, focus states |
| `--signature-vivid` | `#3de6ff` | `#00d3fa` | Hover state for signature elements |
| `--signature-muted` | `#0c8ea4` | `#0f7f93` | Border-bottom depth, light-mode text |
| `--signature-dim` | `rgba(0, 211, 250, 0.24)` | `rgba(0, 182, 214, 0.2)` | Translucent, toggle active bg |
| `--signature-glow` | `rgba(0, 211, 250, 0.10)` | — | Subtle background tint |
| `--signature-glow-strong` | `rgba(0, 211, 250, 0.20)` | — | Focus ring glow, interactive highlights |
| `--signature-glow-intense` | `rgba(0, 211, 250, 0.35)` | — | High-visibility glow for emphasis |
| `--signature-fill` | `var(--signature)` | `#00b5d1` | Button fill shorthand |
| `--signature-fill-hover` | `var(--signature-vivid)` | `#00c7e4` | Button fill hover shorthand |
| `--signature-text` | `#00d3fa` | `#4f7f89` | Signature as text color (muted in light) |
| `--on-signature` | `#f5f3ed` | `#04212a` | Text on signature fills (inverts per polarity) |

#### Accent Lime (Energy, Positive)

| Token | Hex | Role |
|-------|-----|------|
| `--accent-lime` | `#64fa00` | Chips, swatches, positive emphasis |
| `--accent-lime-glow` | `rgba(100, 250, 0, 0.10)` | Subtle background tint |
| `--accent-lime-glow-strong` | `rgba(100, 250, 0, 0.20)` | Interactive highlight |
| `--accent-lime-subtle` | `rgba(100, 250, 0, 0.08)` | Frost card tint, atmospheric |

#### Accent Pink (Warmth, Emphasis)

| Token | Hex | Role |
|-------|-----|------|
| `--accent-pink` | `#fa017b` | Chips, swatches, warm emphasis |
| `--accent-pink-glow` | `rgba(250, 1, 123, 0.10)` | Subtle background tint |
| `--accent-pink-glow-strong` | `rgba(250, 1, 123, 0.20)` | Interactive highlight |
| `--accent-pink-subtle` | `rgba(250, 1, 123, 0.08)` | Frost card tint, atmospheric |

### Semantic Colors (4 Families, 3 Tiers Each)

| Family | Base | Subtle (bg tint) | Bold (darker emphasis) |
|--------|------|-------------------|------------------------|
| **Success** | `#3a9a5b` | `rgba(58, 154, 91, 0.12)` | `#2d7a47` |
| **Warning** | `#c4881d` | `rgba(196, 136, 29, 0.12)` | `#a06f14` |
| **Critical** | `#d14343` | `rgba(209, 67, 67, 0.12)` | `#b33030` |
| **Info** | `#5b8fc7` | `rgba(91, 143, 199, 0.12)` | `#4574a6` |

Semantic colors require non-hue shape fallbacks: circle for success, triangle for warning, diamond for critical, info-i for info. Color alone must never be the only signal.

### Foreground (Text & Icons)

| Token | Maps To | Role |
|-------|---------|------|
| `--foreground-bold` | `--ground-100` | Highest contrast, headings |
| `--foreground-default` | `--ground-80` | Standard body text |
| `--foreground-subtle` | `--ground-60` | Secondary text, hints |
| `--foreground-disabled` | `--ground-40` | Disabled states |
| `--foreground-on-accent` | `#f5f3ed` | Text on colored backgrounds — **same in BOTH polarities** |

### Surface (Layered Elevation)

| Token | Maps To | Role |
|-------|---------|------|
| `--surface-ground` | `--ground-0` | Page background |
| `--surface-raised` | `--ground-10` | Cards, elevated panels |
| `--surface-overlay` | `--ground-15` | Modals, popovers, dropdowns |
| `--surface-recessed` | `--ground-5` | Milled channel: inputs, toggle tracks, progress tracks |

### Border

| Token | Maps To | Role |
|-------|---------|------|
| `--border-default` | `--ground-20` | Standard dividers, form borders |
| `--border-subtle` | `--ground-15` | Light visual separation |
| `--border-strong` | `--ground-30` | Heavy emphasis, active states |
| `--border-focus` | `--signature` | Focus ring color (`#00d3fa`) |

### Polarity Inversion Rule

When `[data-polarity="light"]` is set on `<html>`, the ground scale inverts: `--ground-0` becomes `#f5f3ed` (lightest) and `--ground-100` becomes `#0d0d0c` (darkest). All intermediate steps invert correspondingly. Semantic tokens (`--foreground-bold`, `--surface-raised`, etc.) automatically map to the correct ground step. Shadows shift from pure-black rgba to warmer `rgba(38, 37, 35, ...)` tones at lower opacities. Frost backgrounds swap from dark translucent to light translucent. `--foreground-on-accent` does NOT change — it stays `#f5f3ed` in both polarities.

---

## 3. Typography Rules

Three voices. Each with purpose. Never mix within a single element. Never deviate to other fonts. No italic — emphasis through weight variation only. All sizes must be whole pixels (never `13.5px`, never `0.875rem` that resolves to a fraction).

### Declaration Voice — Syne, Weight 800

The system's authority. Commands attention. Always uppercase. Tight letter-spacing pulls the boldness together.

| Role | Size | Weight | Line Height | Letter Spacing | Notes |
|------|------|--------|-------------|----------------|-------|
| Hero | `clamp(56px, 9vw, 112px)` | 800 | 1.15 | -0.02em | Responsive hero heading |
| H1 | 48px | 800 | 1.15 | -0.02em | Major page sections |
| H2 | 36px | 800 | 1.15 | -0.02em | Section headings |
| H3 | 28px | 800 | 1.15 | -0.02em | Subsection headings |
| H4 | 22px | 800 | 1.15 | -0.02em | Minor headings |
| H5 | 18px | 800 | 1.15 | -0.02em | Label headings, card titles |

**Font stack:** `'Syne', system-ui, -apple-system, sans-serif`
**Always:** `text-transform: uppercase`
**Spacing field:** 96px — Declaration claims territory around itself.

### Narrator Voice — DM Sans, Weights 400/600/700

The system's conversational voice. Carries content, guidance, and interface text.

| Role | Size | Weight | Line Height | Letter Spacing | Notes |
|------|------|--------|-------------|----------------|-------|
| Large | 20px | 600 | 1.6 | 0 | Lead paragraphs, prominent interface text |
| Default | 16px | 600 | 1.6 | 0 | Standard body text |
| Small | 14px | 600 | 1.6 | 0 | Secondary text, compact interface |
| Whisper | 13px | 600 | 1.6 | 0 | Very small text — **weight bumped to 600 for readability** |

**Font stack:** `'DM Sans', system-ui, -apple-system, sans-serif`
**Weights:** 400 (light body), 600 (default/medium), 700 (semi-bold emphasis, alert titles, accordion headers)
**Spacing field:** 24px — Narrator breathes at a comfortable reading rhythm.

### Technical Voice — JetBrains Mono, Weight 600

The system's precision voice. Marks code, data, metadata, and labels.

| Role | Size | Weight | Line Height | Letter Spacing | Notes |
|------|------|--------|-------------|----------------|-------|
| Default | 14px | 600 | 1.15 | 0.04em | Standard code, table data |
| Small | 12px | 600 | 1.15 | 0.04em | Compact labels, badge text |
| Label | 11px | 600 | 1.15 | 0.04em | Minimal labels, section markers |
| Section Label | 10px | 800 | 1.15 | 0.12em | Ultra-small, uppercase, maximum spread |

**Font stack:** `'JetBrains Mono', ui-monospace, 'Cascadia Code', 'Fira Code', monospace`
**Spacing field:** 8px — Technical packs tight, tolerates density.

### Typography Principles

- **Whole pixels only.** Never `13.5px`. Never `0.875rem` that resolves to a fraction on any viewport.
- **No voice mixing.** A single text element uses one voice. A card title is Declaration; the card body is Narrator. Never both in one `<p>`.
- **No italic.** Emphasis through weight variation only (400 → 600 → 700 → 800).
- **Whisper rule:** Narrator at 13px always gets bumped to weight 600 for legibility at small size.
- **Section labels:** Technical voice at 10-11px, `letter-spacing: 0.12em`, `text-transform: uppercase`, weight 800.

### Voice Assignment by Component

| Position | Voice | Size | Modifiers |
|----------|-------|------|-----------|
| Page title | Declaration H1-H2 | 48-36px | |
| Section label | Technical label | 10-11px | uppercase, 0.12em tracking, signature color |
| Section heading | Declaration H3-H4 | 28-22px | |
| Description | Narrator default | 16px | `--foreground-subtle`, max-width ~600px |
| Card title | Declaration H5 | 18px | |
| Card body | Narrator small-whisper | 14-13px | |
| Stat value | Declaration H3 | 28px | `--signature-text` color |
| Stat label | Technical small | 12px | `--foreground-subtle` |
| Button label | Declaration | varies | uppercase |
| Form label | Technical | 14px | |
| Form input | Narrator default | 16px | |
| Form help/error | Narrator whisper | 13px | weight 600 |
| Table header | Technical | 12px | uppercase, 0.12em tracking |
| Table cell | Narrator or Technical | 14px | Context-dependent |
| Badge text | Technical small | 12px | |
| Tag text | Technical small | 12px | |
| Breadcrumbs | Technical small | 12px | |
| Pagination | Technical | 14px | |
| Tooltip | Narrator whisper | 13px | weight 400 (light) |
| Alert title | Narrator semi | 16px | weight 700 |
| Alert body | Narrator | 16px | weight 600 |
| Alert meta | Technical small | 12px | |
| Dropdown item | Narrator small | 14px | |
| Dropdown shortcut | Technical small | 12px | |
| Accordion header | Narrator semi | 16px | weight 700 |
| Footer meta | Technical small | 12px | |
| Footer links | Narrator whisper | 13px | |
| Header brand | Declaration H5 | 18px | |
| Avatar initials | Declaration | varies | `--signature` bg, `--on-signature` text |

---

## 4. Component Stylings

The system defines 26 components. The following 10 represent the core patterns; remaining components derive from these foundations. Full list at the end of this section.

### Button `.btn`

**Variants:** `--primary`, `--secondary`, `--ghost`, `--critical` | `--sm`, `--lg`, `--icon`

| Property | Default (primary) | Hover | Active | Disabled |
|----------|-------------------|-------|--------|----------|
| Background | dark: `--signature-fill` / light: `#00b5d1` | dark: `--signature-fill-hover` / light: `#00c7e4` | same + `--shadow-inset` | `--ground-20` |
| Text | `--on-signature` | same | same | `--ground-40` |
| Border | `1px solid --signature-muted` (bottom) | same | same | `--ground-20` |
| Shadow | `--shadow-sm` + `--highlight-inner` | `--shadow-hover-signature` | `--shadow-inset` | none |
| Transform | none | `translateY(-1px)` | `translateY(0)` | none |
| Radius | `--radius-md` (4px) | | | |
| Motion | Hourglass, `--dur-standard` (200ms) | | Bell, `--dur-micro` (80ms) | |
| Voice | Declaration, uppercase | | | |

**Small variant** (`.btn--sm`): hover transform suppressed entirely.
**Secondary:** `--surface-raised` bg, `--foreground-default` text, `--border-default` border.
**Ghost:** transparent bg, `--foreground-default` text, no border.
**Critical:** `--color-critical` bg, hover shadow `--shadow-hover-critical`.

### Card `.card`

**Variants:** `--elevated`, `--interactive`, `--tilt`, `--compact`, `--signature`, `--flat`

| Property | Default | Hover (interactive) | Tilt Hover |
|----------|---------|---------------------|------------|
| Background | `--surface-raised` | same | same |
| Border | `1px solid --border-default` | `--border-strong` | same |
| Shadow | `--shadow-sm` | `--shadow-md` | `--shadow-lg` |
| Transform | none | `translateY(-2px)` | `perspective(1000px) rotateY(2deg) translateY(-3px)` |
| Radius | `--radius-lg` (6px) | | |
| Grain | `.mat-grain-fine` recommended | | |
| Padding | `--space-lg` (24px) | | |

**Title voice:** Declaration H5. **Body voice:** Narrator small/whisper.
**Signature variant:** `--signature-glow` border tint.
**Card Glow** (`.card-glow`): Mouse-tracking radial gradient + border glow via JS-driven `--glow-x`/`--glow-y` custom properties.

### Input / Form `.form-group` `.input`

| Property | Default | Focus | Error | Disabled |
|----------|---------|-------|-------|----------|
| Background | `--surface-recessed` | `--surface-ground` (lifts) | same | `--ground-5` |
| Border | `1px solid --border-default` | `2px solid --border-focus` | `2px solid --color-critical` | `--ground-20` |
| Shadow | `--shadow-recessed` | `--signature-glow-strong` ring | none | none |
| Text | `--foreground-default` | same | same | `--foreground-disabled` |
| Radius | `--radius-md` (4px) | | | |

**Label voice:** Technical, 14px. **Input voice:** Narrator default, 16px. **Help/error voice:** Narrator whisper, 13px.
**Error animation:** `.input--shake` — horizontal shake, `--ease-bell`.

### Navigation `.nav`

**Variants:** `--horizontal` (default), `--vertical`

| Property | Default | Hover | Active |
|----------|---------|-------|--------|
| Text | `--foreground-subtle` | `--foreground-default` | `--signature` |
| Background | transparent | `--ground-15` | `--signature-glow` |
| Transform | none | `translateX(2px)` | none |
| Motion | Hourglass, `--dur-standard` | | |

**Active (vertical):** Left 2px signature bar via `::before`.
**Section labels:** `.nav-label` — Technical voice, ultra tracking, uppercase.
**Item voice:** Narrator, 14px.

### Badge `.badge`

**Variants:** `--success`, `--warning`, `--critical`, `--info`, `--accent`, `--lime`, `--pink` | `--sm`, `--lg`, `--pill`, `--pulse`

| Variant | Background | Text | Border |
|---------|-----------|------|--------|
| Success | `--color-success-subtle` | `--color-success` | `1px solid rgba(58, 154, 91, 0.2)` |
| Warning | `--color-warning-subtle` | `--color-warning` | `1px solid rgba(196, 136, 29, 0.2)` |
| Critical | `--color-critical-subtle` | `--color-critical` | `1px solid rgba(209, 67, 67, 0.2)` |
| Info | `--color-info-subtle` | `--color-info` | `1px solid rgba(91, 143, 199, 0.2)` |
| Accent | `--signature-glow` | `--signature` | `1px solid rgba(0, 211, 250, 0.2)` |

**Radius:** `--radius-sm` (3px); `--pill` uses `--radius-full` (9999px).
**Voice:** Technical, 12px, `--tracking-wide`.
**Pulse:** Clockwork rhythm animation, 2s loop, `--ease-pendulum`.

### Tag `.tag`

**Variants:** `--default`, `--signature`, `--success`, `--warning`, `--critical` | `--interactive`, `--pill`

| Property | Default | Hover (interactive) |
|----------|---------|---------------------|
| Background | `--ground-15` | `--ground-20` |
| Text | `--foreground-default` | same |
| Transform | none | `translateX(2px)` |

**Dismiss button:** `.tag__dismiss` — icon button, hover: `--color-critical-subtle` bg.
**Voice:** Technical, 12px. **Radius:** `--radius-sm` (3px).
**Signature variant:** `--signature-glow` bg, `--signature` text.

### Modal `.modal`

**Sizes:** `--sm` (400px), default (560px), `--lg` (720px), `--full`

| Property | Value |
|----------|-------|
| Overlay | `--overlay-bg`: dark `rgba(13, 13, 12, 0.6)` / light `rgba(245, 243, 237, 0.6)` |
| Background | `--surface-raised` |
| Border | `1px solid --border-default` |
| Shadow | `--shadow-elevated` |
| Radius | `--radius-xl` (8px) |
| Frost | `.mat-frost-medium` on overlay recommended |

**Enter animation:** `translateY(16px) -> 0` + opacity fade, Hourglass easing, `--dur-macro` (400ms).
**Header voice:** Declaration H4. **Body voice:** Narrator. **Footer:** action buttons left-to-right: ghost/secondary → primary.

### Toggle `.toggle`

| Property | Inactive | Active |
|----------|----------|--------|
| Track bg | `--surface-recessed` | `--signature-dim` |
| Track shadow | `--shadow-recessed` | inner signature glow |
| Thumb bg | `--ground-50` | `--signature-vivid` |
| Thumb highlight | none | `--highlight-inner` |
| Thumb position | `translateX(0)` | `translateX(16px)` |

**Motion:** Hourglass-Settle (`cubic-bezier(0.34, 1.56, 0.64, 1)`) — elastic snap with damping, `--dur-micro` (80ms).
**Small variant:** `.toggle--sm` — 28x16px track, 10x10px thumb.

### Tooltip `.tooltip`

| Property | Value |
|----------|-------|
| Background | `--surface-overlay` |
| Text | Narrator whisper (13px, weight 400) |
| Shadow | `--shadow-md` |
| Radius | `--radius-md` (4px) |
| Arrow | 6x6px rotated 45deg square |
| Positions | `--top` (default), `--bottom`, `--left`, `--right` |

**Enter:** Pendulum easing, `opacity 0 -> 1` + `translateY(4px -> 0)`, `--dur-standard` (200ms).

### Alert `.alert`

**Variants:** `--success`, `--warning`, `--critical`, `--info` | `--toast`

| Property | Value |
|----------|-------|
| Background | `--surface-raised` |
| Left border | 3px solid semantic base color |
| Shadow | `--shadow-sm` |
| Radius | `--radius-lg` (6px) |

**Semantic shapes (`.alert__icon`):** Success = circle, Warning = triangle, Critical = diamond, Info = info-i.
**Enter:** Bell easing (`cubic-bezier(0.0, 0.0, 0.2, 1)`), `translateY(-8px) -> 0` + opacity, `--dur-standard`.
**Toast exit:** `translateX(100%)` + opacity fade.
**Title voice:** Narrator semi (700). **Body voice:** Narrator default. **Meta voice:** Technical small.

### All 26 Components

Button, Card, Badge, Form (input/select/textarea/checkbox/radio), Navigation, Modal, Table, List, Toggle, Tag, Tabs, Tooltip, Dropdown, Progress, Alert, Breadcrumbs, Pagination, Accordion, Avatar, Skeleton Loader, Header, Footer, Card Glow, Chip, Frost Backdrop, Frost Material Utilities.

---

## 5. Layout Principles

### Spacing Scale

All spacing derives from an 8px base unit.

| Token | Value | Use |
|-------|-------|-----|
| `--space-micro` | 4px | Half-base, tight Technical gaps |
| `--space-xs` | 8px | 1x base, minimum meaningful space |
| `--space-sm` | 12px | 1.5x base, compact grouping, label → heading |
| `--space-md` | 16px | 2x base, standard element spacing, form groups |
| `--space-lg` | 24px | 3x base, section gaps, Narrator rhythm, card padding |
| `--space-xl` | 32px | 4x base, generous separation, description → content |
| `--space-2xl` | 48px | 6x base, major section breaks |
| `--space-3xl` | 64px | 8x base, page-level breathing room, section padding |

### Voice Emitters

Spacing is the spatial signature of a voice. When a voice appears, the surrounding whitespace should match its character.

| Voice | Emitter Field | Meaning |
|-------|---------------|---------|
| Declaration | 96px | Commands territory — generous vertical margins around headings |
| Narrator | 24px | Comfortable reading rhythm — standard content spacing |
| Technical | 8px | Dense packing — tight label-to-value gaps |

### Spacing Cheatsheet

| Between | Token | px |
|---------|-------|----|
| Section label → heading | `--space-sm` | 12 |
| Heading → description | `--space-sm` | 12 |
| Description → content | `--space-xl` | 32 |
| Cards in grid | `--space-lg` | 24 |
| Form groups (stacked) | `--space-md` | 16 |
| Fieldset sections | `--space-xl` | 32 |
| Page sections (padding) | `--space-3xl` | 64 |
| Action bar top border gap | `--space-lg` | 24 |

### Border Radius

Six manufactured values. No others exist.

| Token | Value | Use |
|-------|-------|-----|
| `--radius-xs` | 2px | Minimal rounding, precise edges |
| `--radius-sm` | 3px | Small rounding, badges, tags |
| `--radius-md` | 4px | Standard — buttons, inputs, most elements |
| `--radius-lg` | 6px | Cards, modals, alerts |
| `--radius-xl` | 8px | Maximum manufactured rounding |
| `--radius-full` | 9999px | Pills, fully rounded toggles |

### Grid & Containers

| Token | Value | Use |
|-------|-------|-----|
| `--container-max` | 1200px | Standard max-width |
| `--container-narrow` | 720px | Tight column (forms, articles) |
| `--container-wide` | 1440px | Extra-wide layouts |
| `--container-padding` | 24px (`--space-lg`) | Horizontal padding |

**Common grids:**
- Responsive cards: `grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: var(--space-lg)`
- Content + sidebar: `grid-template-columns: 1fr 260px; gap: var(--space-2xl)`
- Dashboard: Sidebar (220px fixed) + main (flex-1)

### Section Rhythm

Every content section follows: **technical label → declaration title → narrator description → content**.

---

## 6. Depth & Elevation

### Elevation Scale

| Level | Token | Dark Shadow | Use |
|-------|-------|-------------|-----|
| Rest | `--shadow-sm` | `0 1px 2px rgba(0,0,0,0.25), 0 0 0 1px rgba(0,0,0,0.08)` | Cards at rest, subtle lift |
| Elevated | `--shadow-md` | `0 2px 8px rgba(0,0,0,0.30), 0 1px 2px rgba(0,0,0,0.15)` | Elevated cards, dropdowns |
| Prominent | `--shadow-lg` | `0 8px 24px rgba(0,0,0,0.35), 0 2px 6px rgba(0,0,0,0.18)` | Popovers, prominent surfaces |
| Dialog | `--shadow-elevated` | `0 12px 40px rgba(0,0,0,0.40), 0 4px 12px rgba(0,0,0,0.20), 0 0 0 1px rgba(0,0,0,0.05)` | Modals, active dialogs |

### Light Polarity Shadows

In light polarity, shadows shift to warmer `rgba(38, 37, 35, ...)` tones at lower opacities:

| Token | Light Shadow |
|-------|-------------|
| `--shadow-sm` | `0 1px 3px rgba(38,37,35,0.08), 0 0 0 1px rgba(38,37,35,0.04)` |
| `--shadow-md` | `0 2px 8px rgba(38,37,35,0.10), 0 1px 3px rgba(38,37,35,0.06)` |
| `--shadow-lg` | `0 4px 14px rgba(38,37,35,0.10), 0 2px 4px rgba(38,37,35,0.06), 0 0 0 1px rgba(38,37,35,0.03)` |
| `--shadow-elevated` | `0 8px 30px rgba(38,37,35,0.12), 0 4px 10px rgba(38,37,35,0.08), 0 0 0 1px rgba(38,37,35,0.03)` |

### Inset & Soul Pass Shadows

| Token | Value | Use |
|-------|-------|-----|
| `--shadow-inset` | `inset 0 2px 4px rgba(0,0,0,0.20)` | Pressed/active button state |
| `--shadow-recessed` | `inset 0 1px 3px rgba(0,0,0,0.15), inset 0 0 0 1px rgba(0,0,0,0.05)` | Milled channel: inputs, toggle tracks, progress tracks |
| `--shadow-inner-glow` | `inset 0 1px 0 rgba(255,255,255,0.2)` | Active toggle thumbs, filled progress bars |
| `--highlight-inner` | `inset 0 1px 0 rgba(255,255,255,0.15)` | Button manufacturing feel, pagination current page |

Light polarity strengthens inner-glow and highlight: `rgba(255,255,255,0.35)` and `rgba(255,255,255,0.25)` respectively.

### Accent & Semantic Hover Shadows

| Token | Value | Trigger |
|-------|-------|---------|
| `--shadow-signature` | `0 4px 16px rgba(0,211,250,0.25), 0 1px 4px rgba(0,211,250,0.12)` | Signature elements at rest |
| `--shadow-hover-signature` | `0 4px 16px rgba(0,211,250,0.30)` | Signature button hover |
| `--shadow-hover-success` | `0 4px 12px rgba(58,154,91,0.25)` | Success button hover |
| `--shadow-hover-warning` | `0 4px 12px rgba(196,136,29,0.25)` | Warning button hover |
| `--shadow-hover-critical` | `0 4px 12px rgba(209,67,67,0.25)` | Critical button hover |
| `--shadow-hover-info` | `0 4px 12px rgba(91,143,199,0.25)` | Info button hover |
| `--shadow-hover-lime` | `0 4px 12px rgba(100,250,0,0.25)` | Lime element hover |
| `--shadow-hover-pink` | `0 4px 12px rgba(250,1,123,0.25)` | Pink element hover |

### Frost (Atmospheric Depth)

Frost creates translucent glass surfaces through backdrop blur. Every frost application requires all four properties: `backdrop-filter: blur()` + translucent background + subtle border + box-shadow.

| Level | Class | Blur | Background (dark) | Background (light) | Use |
|-------|-------|------|-------------------|---------------------|-----|
| Light | `.mat-frost-light` | 8px | `rgba(13,13,12,0.6)` | `rgba(245,243,237,0.6)` | Subtle depth, floating panels |
| Medium | `.mat-frost-medium` | 16px | `rgba(13,13,12,0.75)` | `rgba(245,243,237,0.75)` | Headers, navigation bars |
| Heavy | `.mat-frost-heavy` | 24px | `rgba(13,13,12,0.85)` | `rgba(245,243,237,0.85)` | Modals, full overlays |

All frost classes include: `border: 1px solid var(--border-subtle)`.

**Accent-tinted frost** for atmospheric surfaces: cyan `rgba(13, 235, 255, 0.09)`, lime `rgba(184, 255, 51, 0.08)`, pink `rgba(250, 0, 119, 0.08)`.

### Grain (Surface Texture)

Grain adds tactile texture via SVG noise applied as a `::before` pseudo-element. Applied selectively per-element — never as a global page overlay on body or html. GPU performance attributes required: `will-change: opacity`, `backface-visibility: hidden`, `transform: translateZ(0)`.

| Profile | Class | Opacity | Purpose | Use On |
|---------|-------|---------|---------|--------|
| Fine | `.mat-grain-fine` | 0.025 | Injection-molded feel | Cards, quotes, settings headers |
| Coarse | `.mat-grain-coarse` | 0.04 | Brushed aluminum authority | Dashboard headers, elevated panels |
| Concrete | `.mat-grain-concrete` | 0.03 | Architectural foundation | Section backgrounds |
| Gradient | `.mat-grain-gradient` | 0.02 | Anti-banding (required on all gradients) | Every gradient element |
| Edge | `.mat-grain-edge` | 0.015 | Barely visible at borders | Edge treatment, felt-not-seen |

**Material hierarchy:** No grain = baseline surface. Fine = elevated quality. Coarse = premium/mission-critical. Concrete = architectural foundation. Material communicates tier before any words are read.

### Frost + Grain Gold Standard

The recommended default for premium surfaces. Combines frost and grain with optimized parameters:

```css
.mat-frost-grain::before {
  background-size: 512px 512px;       /* larger scale than standalone grain */
  mix-blend-mode: overlay;             /* not soft-light — overlay for frost context */
  opacity: 0.185;                      /* higher than standalone grain */
  filter: contrast(0.75);              /* softer contrast on frost */
}
```

Content inside frost-grain elements needs `position: relative; z-index: 3` to sit above material layers.

### Shadow Philosophy

Shadows in Reality Reprojection serve two roles: structural elevation (how far a surface sits above the ground plane) and chromatic identity (accent-colored hover shadows that tie depth to meaning). In dark polarity, shadows are pure-black rgba at high opacity — darkness on darkness, differentiated by blur radius and spread. In light polarity, shadows warm to `rgba(38, 37, 35, ...)` at lower opacities — present but never harsh. The system never uses neutral gray shadows or drop-shadow values outside the defined scale.

---

## 7. Do's and Don'ts

### Do

- Use off-extreme grounds (`#0d0d0c` / `#f5f3ed`) — never pure black or white
- Match typographic voice to spacing: Declaration → 96px field, Narrator → 24px, Technical → 8px
- Apply grain profiles to elevated surfaces — even subtle fine grain on cards adds material quality
- Use signature cyan (`#00d3fa`) as the primary interactive signal in both polarities
- Design for both polarities simultaneously — dark and light are co-equal
- Use only the 6 manufactured radii: {2, 3, 4, 6, 8, 9999}px
- Apply frost to all overlapping surfaces (modals, dropdowns, sticky headers)
- Use system easing tokens exclusively — Hourglass, Hourglass-Settle, Pendulum, or Bell
- Include `@media (prefers-reduced-motion: reduce)` fallback for every animation
- Test the Decision Test: Does every element exist because it must? Does it feel cared about?

### Don't

- Don't use pure `#000000` or `#ffffff` — the off-extremes are the system's anchors
- Don't mix typographic voices within a single element — Declaration title, Narrator body, never blended
- Don't use border-radii outside the 6 manufactured values — no `10px`, no `12px`, no `50%`
- Don't use `scale()` on hover — ever. Buttons: `translateY(-1px)`. Tags/nav: `translateX(2px)`. No exceptions.
- Don't hardcode hex/rgb/rgba colors — always reference system tokens
- Don't apply grain globally on body or html — grain is selective, per-element via `::before`
- Don't use CSS easing keywords (`ease`, `ease-in-out`, `linear`) or raw `cubic-bezier()` — only named system easings
- Don't use chromatic aberration classes — removed from system (2026-02-20)
- Don't use emoji characters — use SVG icons or Unicode symbols (`>`, `X`, `...`)
- Don't use italic — emphasis through weight variation only
- Don't add left/right colored accent borders on cards — use material (grain, frost, shadow) instead

### Anti-Pattern Table

| Wrong | Correct | Rule |
|-------|---------|------|
| `transition: all 0.3s ease` | `transition: all var(--dur-standard) var(--ease-hourglass)` | System easing + duration tokens only |
| `transform: scale(1.05)` on hover | `transform: translateY(-1px)` on hover | Buttons lift, never scale |
| `.tag:hover { translateY(-1px) }` | `.tag:hover { translateX(2px) }` | Tags/nav shift right, not up |
| `font-size: 13.5px` | `font-size: 14px` | Whole pixels only |
| `font-size: 0.875rem` | `font-size: 14px` | Whole pixels, prefer px |
| `border-radius: 12px` | `border-radius: var(--radius-xl)` (8px) | Manufactured radii only |
| `border-radius: 50%` | `border-radius: var(--radius-full)` (9999px) | Token, not percentage |
| `color: #333` | `color: var(--foreground-default)` | Token colors only |
| `color: #00d3fa` | `color: var(--signature)` | Even signature uses token |
| `font-family: Arial` | `font-family: var(--font-narrator)` | System voices only |
| `body::before { grain }` | `.element::before { grain }` | Selective grain, not global |
| No `[data-polarity="light"]` | Always include light overrides | Both polarities required |
| Animation without reduced-motion | Add `@media (prefers-reduced-motion)` | Accessibility required |
| Using emoji (🎨 ✅ 🔴) | SVG or Unicode symbols (> X ...) | No emojis — ever |

---

## 8. Responsive Behavior

### Breakpoints

| Name | Width | Key Changes |
|------|-------|-------------|
| Mobile | < 640px | Single column, Declaration hero → 56px min, sidebar collapses, hamburger nav |
| Tablet | 640-1024px | 2-column grids, sidebar as drawer, touch-sized targets |
| Desktop | 1024-1280px | Full layout, sidebars visible, all grid columns |
| Large | > 1280px | `--container-wide` available, extra whitespace |

### Voice Scaling

| Voice | Scaling Behavior |
|-------|-----------------|
| Declaration | Hero `clamp(56px, 9vw, 112px)` scales fluidly. H1-H5 step down by one level on mobile (H1 → H2, etc.). 96px emitter compresses to 48px on mobile. |
| Narrator | Reflows naturally. Default 16px holds. Large (20px) may drop to default on mobile. Line length constrained to ~600px max. |
| Technical | Stays rigid. Monospace does not reflow well. Table headers may need horizontal scroll (`.table-wrap`). |

### Touch Targets

- Minimum interactive size: 44x44px (even if visual element is smaller)
- Technical-voice elements (badges, tags, small buttons) must have adequate tap padding
- Toggle thumb: minimum 44px tap area even when visually 16px

### Motion Degradation

| Context | Behavior |
|---------|----------|
| `prefers-reduced-motion: reduce` | Disable all transforms and movement. Keep opacity fades only. Skeleton shimmer disabled (solid fill). |
| Hourglass | Falls back to instant transition |
| Hourglass-Settle | Falls back to instant snap (no elastic overshoot) |
| Pendulum | Falls back to fade-only |
| Bell | Falls back to opacity-only appearance |

### Survivalist Mode

When `[data-mode="survivalist"]` is set on `<html>`, the system progressively strips:
1. Grain (all profiles → removed)
2. Frost blur (`backdrop-filter` → solid backgrounds)
3. Custom shadows → simplified single-layer shadows
4. Custom fonts → system font stack
5. Motion → instant transitions
6. Color saturation reduces toward monochrome

Semantic shapes (circle/triangle/diamond/info-i) survive — status must never rely solely on color or decoration.

---

## 9. Agent Prompt Guide

### Quick Color Reference

| Token | Dark Hex | Light Hex | Role |
|-------|----------|-----------|------|
| `--ground-0` | `#0d0d0c` | `#f5f3ed` | Page canvas |
| `--ground-10` | `#1d1d1b` | (inverted) | Card surface |
| `--ground-100` | `#f5f3ed` | `#0d0d0c` | Bold text |
| `--signature` | `#00d3fa` | `#00b6d6` | Brand, interactive |
| `--accent-lime` | `#64fa00` | same | Energy, positive |
| `--accent-pink` | `#fa017b` | same | Warmth, emphasis |
| `--color-success` | `#3a9a5b` | same | Favorable outcome |
| `--color-warning` | `#c4881d` | same | Needs attention |
| `--color-critical` | `#d14343` | same | Error, destructive |
| `--color-info` | `#5b8fc7` | same | Guidance |
| `--foreground-bold` | `#f5f3ed` | `#0d0d0c` | Headings |
| `--foreground-default` | `#d2cfc8` | (inverted) | Body text |
| `--foreground-on-accent` | `#f5f3ed` | `#f5f3ed` | On colored bg (BOTH polarities) |

### Quick Font Reference

| Voice | Font | Weight | Transform | Spacing |
|-------|------|--------|-----------|---------|
| Declaration | Syne | 800 | uppercase | -0.02em |
| Narrator | DM Sans | 400/600/700 | none | 0 |
| Technical | JetBrains Mono | 600 | none | 0.04em |

### Quick Material Reference

| Material | Default | Class |
|----------|---------|-------|
| Grain | Fine (opacity 0.025) | `.mat-grain-fine` |
| Frost | Medium (blur 16px, bg 0.75) | `.mat-frost-medium` |
| Shadow | Rest (sm) | `--shadow-sm` |
| Gold Standard | Frost-medium + grain (overlay, 0.185) | `.mat-frost-medium .mat-frost-grain` |

### Quick Motion Reference

| Character | Easing | Use | Default Duration |
|-----------|--------|-----|-----------------|
| Hourglass | `cubic-bezier(0.4, 0, 0.2, 1)` | Most transitions, hover, focus | `--dur-standard` (200ms) |
| Hourglass-Settle | `cubic-bezier(0.34, 1.56, 0.64, 1)` | Toggle snaps, elastic bounce | `--dur-micro` (80ms) |
| Pendulum | `cubic-bezier(0.25, 0.1, 0.25, 1)` | Staggered reveals, progress, tab underline | `--dur-standard` (200ms) |
| Bell | `cubic-bezier(0.0, 0.0, 0.2, 1)` | Alerts entering, modal snap, sharp impact | `--dur-standard` (200ms) |

### Example Component Prompts

**1. Dark Hero Section**
> Create a dark-polarity hero section. Background `#0d0d0c`. Centered layout, max-width 1200px. Declaration voice hero heading (`clamp(56px, 9vw, 112px)`, Syne 800, uppercase, `#f5f3ed`). Narrator large description (20px, DM Sans 600, `#a09c95`, max-width 600px, centered). Two CTAs: primary button (signature cyan `#00d3fa` fill, `#f5f3ed` text, 4px radius, inset highlight) and secondary (raised surface, default border). Section padding 64px vertical. Gap: heading → description 12px, description → CTAs 32px.

**2. Content Card (Both Polarities)**
> Build a content card. Dark: background `#1d1d1b`, border `1px solid #343331`, shadow `0 1px 2px rgba(0,0,0,0.25)`. Light: background inverted ground-10, border inverted ground-20, shadow `0 1px 3px rgba(38,37,35,0.08)`. Radius 6px. Padding 24px. Fine grain overlay (opacity 0.025, mix-blend-mode soft-light). Card title: Declaration H5 (18px, Syne 800, uppercase). Card body: Narrator small (14px, DM Sans 600). Hover: `translateY(-2px)`, shadow deepens to md level. Transition: Hourglass 200ms.

**3. Code Block**
> Design a code block. Background: `--surface-recessed` (dark: `#151514`). Border: `1px solid #272725`. Inset shadow: `inset 0 1px 3px rgba(0,0,0,0.15)`. Radius 6px. Padding 24px. Technical voice: JetBrains Mono 600, 14px, letter-spacing 0.04em, line-height 1.15. Text color: `#d2cfc8`. Monospace, no word-wrap. Horizontal scroll on overflow.

**4. Modal with Frost**
> Create a modal dialog. Overlay: `rgba(13, 13, 12, 0.6)` with frost-medium (backdrop-filter blur 16px). Modal: background `#1d1d1b`, border `1px solid #272725`, shadow `0 12px 40px rgba(0,0,0,0.40)`, radius 8px. Header: Declaration H4 (22px, uppercase). Body: Narrator default (16px). Footer: ghost cancel button left, primary action button right. Enter animation: `translateY(16px) -> 0`, opacity fade, Hourglass easing, 400ms duration.

**5. Semantic Toast (Critical)**
> Build a critical toast notification. Background: `--surface-raised`. Left border: 3px solid `#d14343`. Shadow: `--shadow-sm`. Radius 6px. Icon: diamond shape in `#d14343` via `::before`. Title: Narrator semi (16px, DM Sans 700). Body: Narrator default (16px, DM Sans 600). Meta timestamp: Technical small (12px, JetBrains Mono 600). Dismiss button: ghost icon button. Enter: Bell easing, `translateY(-8px) -> 0` + opacity, 200ms. Exit: `translateX(100%)` + opacity fade.

**6. Polarity Switch**
> To convert any dark-polarity component to light polarity: invert the ground scale (step N becomes `13 - N` in the scale, so `--ground-0` flips from `#0d0d0c` to `#f5f3ed`). Keep signal hues (cyan, lime, pink) unchanged. Shift shadows from `rgba(0,0,0,...)` to `rgba(38,37,35,...)` at ~40% lower opacity. Swap frost backgrounds from `rgba(13,13,12,X)` to `rgba(245,243,237,X)`. Signature adjusts: `#00d3fa` → `#00b6d6`. On-signature text inverts: `#f5f3ed` → `#04212a`. `--foreground-on-accent` stays `#f5f3ed` in both polarities.

### Iteration Guide

1. **Start with voice selection.** Every element belongs to exactly one voice: Declaration (headings), Narrator (content), or Technical (data). Choose first, then size and spacing follow.
2. **Match spacing to voice.** Declaration elements get generous surrounding space (64-96px). Narrator content breathes at 24px intervals. Technical labels pack at 8px density.
3. **Pick a grain profile.** Baseline surfaces get no grain. Elevated cards get fine. Premium/dashboard headers get coarse. Section backgrounds get concrete. All gradients require gradient grain (anti-banding).
4. **Choose elevation.** Rest (sm) for cards. Elevated (md) for dropdowns. Prominent (lg) for popovers. Dialog (elevated) for modals. Each level has a corresponding shadow token.
5. **Test both polarities.** Design in dark, then verify light. The ground scale inverts; shadows warm; frost backgrounds swap. If it breaks in either polarity, the structure is wrong.
6. **Check motion character.** Hourglass for general transitions. Pendulum for sequential/staggered. Bell for alerts and modals. Hourglass-Settle for toggle snaps. Never use CSS keywords or raw cubic-bezier.
7. **Run the Decision Test.** Is every element here because it must be? Can the user go deeper? Does it feel cared about? Does it hold its tensions — bold and detailed, precise and warm, structured and alive?
