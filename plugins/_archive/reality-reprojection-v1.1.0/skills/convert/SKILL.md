---
name: convert
description: "Convert existing HTML/CSS to use Reality Reprojection design system tokens, classes, and patterns"
argument-hint: [file path or 'current file']
---

# Reality Reprojection — Convert Code

You transform existing HTML/CSS code to conform to the Reality Reprojection design system. Every raw value gets mapped to a system token. Every generic pattern gets replaced with a system component class.

## Step 1: Load References

Read reference files using the Read tool. You have a context budget — respect it.

**CONTEXT BUDGET: Stay under 16k reference tokens. Tier 1 alone handles most conversions.**

### Tier 1 — Load these. (~10k tokens)
- `${CLAUDE_PLUGIN_ROOT}/reference/design-tokens.md` — Token values for mapping
- `${CLAUDE_PLUGIN_ROOT}/reference/design-rules.md` — Rules to enforce
- `${CLAUDE_PLUGIN_ROOT}/reference/component-catalog.md` — Component class patterns

**After loading Tier 1, STOP and ask yourself: "Do I have enough to complete this conversion?"** The mapping tables in Step 3 below combined with Tier 1 cover the vast majority of conversions. If yes — proceed. Do not load more.

### Tier 2 — Load ONLY IF converting a full page layout, not a single file or component.
- `${CLAUDE_PLUGIN_ROOT}/reference/composition-recipes.md` — Page-level layout patterns, spacing rhythm, voice hierarchy.

### Tier 3 — Restricted. Read the gate below before touching these.

```
GATE: You MUST answer ALL THREE questions with "yes" before loading ANY Tier 3 file:
  1. Have I loaded and fully read the relevant Tier 1 and Tier 2 files?
  2. Is there a specific question I cannot answer from those files?
  3. Can I name the exact section/file I need, rather than browsing?
If any answer is "no" → do NOT load Tier 3. Return to the files you have.
```

- `${CLAUDE_PLUGIN_ROOT}/reference/bible.html` — 31k tokens. NEVER load whole file. If gated: lines 1584-1884 (components) or lines 1889-2112 (compositions) only.
- `${CLAUDE_PLUGIN_ROOT}/deep-reference/` — 65k tokens total. NEVER load multiple files. One specific file only if gated.

**Examples of correct loading decisions:**
- "Convert my styles.css to use system tokens" → Tier 1 only. Tokens + rules + mapping tables.
- "Convert my entire index.html to Reality Reprojection" → Tier 1 + composition-recipes. Page needs layout guidance.
- "Convert this React component's inline styles" → Tier 1 only. Token mapping is sufficient.

## Step 2: Read Target Files

Read the file(s) specified in `$ARGUMENTS` using the Read tool. If a directory is given, use Glob to find all `.html`, `.css`, `.jsx`, `.tsx`, `.vue`, `.svelte` files.

## Step 3: Analyze Existing Code

Scan for all raw values that should become tokens:

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

Where existing HTML patterns match system components, replace generic classes:

- Generic button markup → `.btn .btn--primary` etc.
- Generic card/box → `.card .card__header .card__body`
- Generic form fields → `.form-group .form-label .input`
- Generic nav → `.nav .nav-item`
- Generic badge/tag → `.badge .badge--success` or `.tag .tag--signature`

## Step 5: Add System Infrastructure

If the Reality Reprojection CSS is not already in the project, set it up:

1. **CSS Bundle:** Read `${CLAUDE_PLUGIN_ROOT}/bundle/reality-reprojection.css` and write it to the project's CSS directory. This single file contains all 36 design system modules in cascade order.
2. **Font imports:** Add to `<head>`:
   ```html
   <link href="https://fonts.googleapis.com/css2?family=Syne:wght@800&family=DM+Sans:ital,wght@0,400;0,600;0,700&family=JetBrains+Mono:wght@600&display=swap" rel="stylesheet">
   ```
3. **Link CSS:** `<link rel="stylesheet" href="[path-to]/reality-reprojection.css">`
4. **Polarity:** `data-polarity="dark"` (or `"light"`) on `<html>` element
5. **Reduced motion:** `@media (prefers-reduced-motion: reduce)` blocks for any animations

Alternatively, tell the user to run `/reality-reprojection:setup` for automated bootstrapping.

## Step 6: Present Diff for Approval

Show the changes as a before/after diff:

```markdown
## Conversion Report: [filename]

### Changes Summary
- X color values → system tokens
- X font declarations → system voices
- X spacing values → system tokens
- X radius values → system tokens
- X shadow values → system tokens
- X easing values → system curves
- X HTML class replacements

### Diff Preview
```diff
- color: #333;
+ color: var(--foreground-default);

- font-family: Arial, sans-serif;
+ font-family: var(--font-narrator);

- border-radius: 12px;
+ border-radius: var(--radius-xl);
```

### Ready to apply?
[Wait for user confirmation before using Edit tool to modify files]
```

**CRITICAL:** Do NOT apply changes without showing the diff first and getting approval. The user must see and confirm what will change.

## Rules

- Map to the NEAREST system token, not an exact match. `#444` is closer to `--ground-30` than `--ground-20`.
- When a value has no reasonable token match, leave it and note it in the report.
- Preserve the code's structure and logic. Only change values, not architecture.
- If the code uses a CSS framework (Tailwind, Bootstrap), note conflicts in the report.
- Font size conversions must result in whole pixels.
