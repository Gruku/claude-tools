---
name: convert
description: "Convert existing HTML/CSS to use Reality Reprojection design system tokens, classes, and patterns"
argument-hint: [file path or 'current file']
---

# Reality Reprojection — Convert Code

You transform existing HTML/CSS code to conform to the Reality Reprojection design system. Every raw value gets mapped to a system token. Every generic pattern gets replaced with a system component class.

## Step 1: Load Compact Lookup, Then Assess

**First:** Load `${CLAUDE_PLUGIN_ROOT}/reference/compact-lookup.md` (~1.5k tokens) for component class patterns.

The mapping tables in Step 3 below handle 90% of CSS value conversions. The compact lookup handles HTML class replacements.

### Decision Tree

```
1. Converting CSS values only (colors, spacing, radii, easing)?
   → Use the mapping tables in Step 3. Compact lookup is enough.

2. Converting HTML classes to system component classes?
   → Compact lookup has all 22 components. Generate class replacements from it.

3. Encountering values not in the mapping tables?
   → Load: ${CLAUDE_PLUGIN_ROOT}/reference/design-tokens.md ONLY (~4k tokens)

4. Converting a full page layout?
   → Load: ${CLAUDE_PLUGIN_ROOT}/reference/composition-recipes.md ONLY (~4k tokens)

NEVER load multiple reference files. Mapping tables + one file if needed.
```

### Deep Reference — Gated (rare)

```
GATE: ALL THREE must be "yes":
  1. Have I checked the mapping tables AND the compact lookup?
  2. Is there a specific value/pattern I still cannot map?
  3. Can I name the exact file/section I need?
If any "no" → STOP. You have enough.
```

## Step 2: Read Target Files

Read the file(s) specified in `$ARGUMENTS` using the Read tool. If a directory is given, use Glob to find all `.html`, `.css`, `.jsx`, `.tsx`, `.vue`, `.svelte` files.

## Step 3: Map Values Using Built-in Tables

### Color Mapping (Hex/RGB → Token)

| Raw Value (approximate) | System Token |
|------------------------|-------------|
| `#000`, `#111`, `#0d0d0c` | `var(--ground-0)` |
| `#1a1a1a`, `#1d1d1b` | `var(--ground-10)` |
| `#222`, `#272725` | `var(--ground-15)` |
| `#333`, `#343331` | `var(--ground-20)` |
| `#555`, `#4d4c48` | `var(--ground-30)` |
| `#666`, `#66645f` | `var(--ground-40)` |
| `#888`, `#7d7b76` | `var(--ground-50)` |
| `#999`, `#aaa`, `#a09c95` | `var(--ground-60)` |
| `#bbb`, `#bbb8b1` | `var(--ground-70)` |
| `#ccc`, `#ddd`, `#d2cfc8` | `var(--ground-80)` |
| `#eee`, `#e6e4dd` | `var(--ground-90)` |
| `#fff`, `#f5f3ed` | `var(--ground-100)` |
| Any cyan ~`#00d3fa` | `var(--signature)` |
| Any lime-green ~`#64fa00` | `var(--accent-lime)` |
| Any hot-pink ~`#fa017b` | `var(--accent-pink)` |
| Green ~`#3a9a5b` | `var(--color-success)` |
| Orange ~`#c4881d` | `var(--color-warning)` |
| Red ~`#d14343` | `var(--color-critical)` |
| Blue ~`#5b8fc7` | `var(--color-info)` |

### Font Mapping

| Raw Value | System Token |
|-----------|-------------|
| `font-family: sans-serif`, `Arial`, `Helvetica` | `var(--font-narrator)` |
| `font-family: monospace`, `Courier`, `Consolas` | `var(--font-technical)` |
| `font-weight: 800` or `900` | `var(--font-declaration-weight)` |
| `font-weight: 400` or `normal` | `var(--font-narrator-weight-light)` |
| `font-weight: 500` or `600` | `var(--font-narrator-weight)` |
| `font-weight: 700` or `bold` | `var(--font-narrator-weight-semi)` |

### Spacing Mapping

| Raw Value (approximate) | System Token |
|------------------------|-------------|
| `4px` | `var(--space-micro)` |
| `8px` | `var(--space-xs)` |
| `12px` | `var(--space-sm)` |
| `16px` | `var(--space-md)` |
| `24px` | `var(--space-lg)` |
| `32px` | `var(--space-xl)` |
| `48px` | `var(--space-2xl)` |
| `64px` | `var(--space-3xl)` |

### Radius Mapping

| Raw Value | System Token |
|-----------|-------------|
| `1px`-`2px` | `var(--radius-xs)` (2px) |
| `3px` | `var(--radius-sm)` (3px) |
| `4px`-`5px` | `var(--radius-md)` (4px) |
| `6px`-`7px` | `var(--radius-lg)` (6px) |
| `8px`-`16px` | `var(--radius-xl)` (8px) |
| `50%`, `999px`, `9999px` | `var(--radius-full)` (9999px) |

### Shadow Mapping

| Pattern | System Token |
|---------|-------------|
| Small, subtle shadow | `var(--shadow-sm)` |
| Medium elevation | `var(--shadow-md)` |
| Large, prominent | `var(--shadow-lg)` |
| Heavy, dialog/modal | `var(--shadow-elevated)` |
| Inset/pressed | `var(--shadow-inset)` |
| Input channel feel | `var(--shadow-recessed)` |

### Easing Mapping

| Raw Value | System Token |
|-----------|-------------|
| `ease`, `ease-in-out` | `var(--ease-hourglass)` |
| `ease-out` | `var(--ease-hourglass)` |
| `ease-in` | `var(--ease-bell)` |
| `linear` | `var(--ease-pendulum)` |
| Any raw `cubic-bezier()` | Closest named easing |

### Duration Mapping

| Raw Value | System Token |
|-----------|-------------|
| `50ms`-`100ms` | `var(--dur-micro)` (80ms) |
| `150ms`-`300ms` | `var(--dur-standard)` (200ms) |
| `350ms`-`600ms` | `var(--dur-macro)` (400ms) |

## Step 4: Replace HTML Classes

Where existing HTML patterns match system components, replace generic classes using the compact lookup:

- Generic button markup → `.btn .btn--primary` etc.
- Generic card/box → `.card .card__header .card__body`
- Generic form fields → `.form-group .form-label .input`
- Generic nav → `.nav .nav-item`
- Generic badge/tag → `.badge .badge--success` or `.tag .tag--signature`

## Step 5: Add System Infrastructure

If the Reality Reprojection CSS is not already in the project:

1. **CSS Bundle:** Copy `${CLAUDE_PLUGIN_ROOT}/bundle/reality-reprojection.css` to project CSS dir
2. **Font imports:** Add Google Fonts link to `<head>` (Syne 800, DM Sans 400/600/700, JetBrains Mono 600)
3. **Link CSS:** `<link rel="stylesheet" href="[path-to]/reality-reprojection.css">`
4. **Polarity:** `data-polarity="dark"` (or `"light"`) on `<html>`

Or tell the user to run `/reality-reprojection:setup`.

## Step 6: Present Diff for Approval

Show changes as before/after diff. **Do NOT apply without user confirmation.**

```markdown
## Conversion Report: [filename]

### Changes Summary
- X color values → system tokens
- X font declarations → system voices
- X spacing/radius/shadow/easing values → system tokens
- X HTML class replacements

### Diff Preview
```diff
- color: #333;
+ color: var(--foreground-default);

- border-radius: 12px;
+ border-radius: var(--radius-xl);
```

### Ready to apply?
```

## Rules

- Map to the NEAREST system token, not an exact match. `#444` → `--ground-30`.
- When a value has no reasonable token match, leave it and note it in the report.
- Preserve the code's structure and logic. Only change values, not architecture.
- If the code uses a CSS framework (Tailwind, Bootstrap), note conflicts in the report.
- Font size conversions must result in whole pixels.
