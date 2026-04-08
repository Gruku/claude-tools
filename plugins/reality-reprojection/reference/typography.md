# Reality Reprojection — Typography

> Three voices, each with purpose. Never mix within a single element. Never deviate to other fonts.

## The Three Voices

### Declaration (Syne 800)

**Purpose:** Headlines, titles, commands attention. The system's authority voice.
**Font:** `--font-declaration`: `'Syne', system-ui, -apple-system, sans-serif`
**Weight:** `--font-declaration-weight`: `800`
**Transform:** Always `text-transform: uppercase`
**Letter-spacing:** `--tracking-tight` (`-0.02em`)
**Line-height:** `--leading-tight` (`1.15`)

**Sizes:**
- `--size-declaration-hero`: `clamp(56px, 9vw, 112px)` — Responsive hero heading
- `--size-declaration-h1`: `48px` — Major page sections
- `--size-declaration-h2`: `36px` — Section headings
- `--size-declaration-h3`: `28px` — Subsection headings
- `--size-declaration-h4`: `22px` — Minor headings
- `--size-declaration-h5`: `18px` — Label headings

**Classes:**
- `.declaration` — Base Declaration styling
- `.declaration--h1` through `.declaration--h5` — Size variants
- Hero size applied inline or with custom class

**When to use:** Section titles, hero text, stat card values, call-to-action labels, brand identity text

### Narrator (DM Sans 400/600/700)

**Purpose:** Body text, interface explanations, guidance. The system's conversational voice.
**Font:** `--font-narrator`: `'DM Sans', system-ui, -apple-system, sans-serif`
**Letter-spacing:** `--tracking-normal` (`0`)
**Line-height:** `--leading-body` (`1.6`) for body, `--leading-heading` (`1.2`) for titles

**Weights:**
- `--font-narrator-weight-light`: `400` — Light body text, secondary content
- `--font-narrator-weight` / `--font-narrator-weight-medium`: `600` — Default body, interface text
- `--font-narrator-weight-semi`: `700` — Semi-bold emphasis, alert titles, accordion headers

**Sizes:**
- `--size-narrator-large`: `20px` — Prominent interface text, lead paragraphs
- `--size-narrator-default`: `16px` — Standard body text
- `--size-narrator-small`: `14px` — Secondary text, compact interface
- `--size-narrator-whisper`: `13px` — Very small text (weight bumped to 600 for readability)

**Classes:**
- `.narrator` — Base Narrator styling
- `.narrator--large`, `.narrator--default`, `.narrator--small`, `.narrator--whisper` — Size variants

**When to use:** Paragraphs, descriptions, form inputs, captions, card body text, alert body, modal body, tooltip content

### Technical (JetBrains Mono 600)

**Purpose:** Code, data precision, metadata, labels. The system's precision voice.
**Font:** `--font-technical`: `'JetBrains Mono', ui-monospace, 'Cascadia Code', 'Fira Code', monospace`
**Weight:** `--font-technical-weight`: `600`
**Letter-spacing:** `--tracking-wide` (`0.04em`)
**Line-height:** `--leading-tight` (`1.15`)

**Sizes:**
- `--size-technical-default`: `14px` — Standard code, table data
- `--size-technical-small`: `12px` — Compact labels, badge text
- `--size-technical-label`: `11px` — Minimal labels, section markers

**Section label special:** `--size-section-label`: `10px` with `--tracking-ultra` (`0.12em`), uppercase, weight 800

**Classes:**
- `.technical` — Base Technical styling
- `.technical--default`, `.technical--small`, `.technical--label` — Size variants

**When to use:** Color codes (#00d3fa), CSS tokens, measurements (14px, 200ms), timestamps, keyboard shortcuts, table headers, badge text, breadcrumbs, pagination numbers, progress labels, tag text, footer metadata, dropdown shortcut hints

## Line Heights

- `--leading-tight`: `1.15` — Headlines, Declaration, Technical labels
- `--leading-heading`: `1.2` — Subheadings, card titles
- `--leading-body`: `1.6` — Body text, Narrator reading comfort
- `--leading-loose`: `1.8` — Very loose, accessibility-first contexts

## Letter Spacing (Tracking)

- `--tracking-tight`: `-0.02em` — Declaration headlines (negative, pulls letters together)
- `--tracking-normal`: `0` — Body text, Narrator voice (default)
- `--tracking-wide`: `0.04em` — Technical voice (spreads for precision)
- `--tracking-ultra`: `0.12em` — Section labels (uppercase small text, maximum spread)

## Composition Rules

1. Headlines and titles: Declaration voice, tight leading, tight tracking, uppercase
2. Body text and descriptions: Narrator voice, body leading, normal tracking
3. Labels, metadata, and data: Technical voice, tight leading, wide tracking
4. Section labels: Technical at 10-11px, ultra tracking, uppercase, weight 800
5. Never mix voices within a single text element
6. All sizes must be whole pixels — NEVER fractional (no 13.5px, no 0.875rem)
7. No italic. Emphasis through weight variation only.
8. Narrator whisper (13px): always bump to weight 600 for readability at small size

## Voice Assignment by Component

| Component | Primary Voice | Notes |
|-----------|--------------|-------|
| Buttons | Declaration | Uppercase, tracking-wide |
| Cards (title) | Declaration | Body uses Narrator |
| Cards (body) | Narrator | |
| Badges | Technical | Small size, tracking-wide |
| Form labels | Technical | |
| Form inputs | Narrator | Default size |
| Form help text | Narrator whisper | Weight 600 |
| Navigation items | Narrator | Medium weight |
| Nav section labels | Technical | Ultra tracking, uppercase |
| Table headers | Technical | Uppercase, ultra tracking |
| Table cells | Narrator or Technical | Context-dependent |
| Breadcrumbs | Technical | Small size, tracking-wide |
| Pagination numbers | Technical | |
| Tooltips | Narrator whisper | Light weight (400) |
| Alerts (title) | Narrator semi (700) | |
| Alerts (body) | Narrator | Default weight |
| Alerts (meta) | Technical | Small size |
| Dropdowns (items) | Narrator | Small size |
| Dropdowns (shortcuts) | Technical | Small size |
| Dropdown headers | Technical | Label size, tracking-wide |
| Accordion headers | Narrator semi (700) | |
| Progress labels | Technical | Small size |
| Progress values | Technical | |
| Tags | Technical | Small size |
| Footer meta | Technical | Small size |
| Footer links | Narrator | Whisper size |
| Header brand | Declaration | H5 size |
| Skeleton | — | No text (placeholder shapes) |
| Avatar initials | Declaration | Signature bg + on-accent text |
