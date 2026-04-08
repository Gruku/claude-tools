---
name: review
description: "Audit HTML/CSS for Reality Reprojection design system compliance — reports violations with severity and suggested fixes"
argument-hint: [file path or directory to audit]
---

# Reality Reprojection — Review Compliance

You audit HTML/CSS code for compliance with the Reality Reprojection design system. You scan for violations, categorize them by severity, and suggest specific fixes.

## Step 1: Load Compact Lookup, Then Assess

**First:** Load `${CLAUDE_PLUGIN_ROOT}/reference/compact-lookup.md` (~1.5k tokens) for component class validation.

The violation rules are embedded below in Step 3. Combined with the compact lookup, this is sufficient for most audits.

### Decision Tree

```
1. Auditing CSS values (colors, easing, radii, spacing)?
   → Use the violation tables in Step 3. Compact lookup is enough.

2. Need to verify an exact token name you're unsure about?
   → Load: ${CLAUDE_PLUGIN_ROOT}/reference/design-tokens.md ONLY (~4k tokens)

3. Auditing HTML class correctness?
   → Compact lookup has all 22 components. Validate against it.
   → If unsure about a specific component: load ${CLAUDE_PLUGIN_ROOT}/reference/component-catalog.md ONLY

NEVER load bible.html, deep-reference, composition-recipes, or material-treatments for reviews.
A review checks values against rules — it does not need layout recipes or design philosophy.
```

## Step 2: Read Target Files

Read the file(s) specified in `$ARGUMENTS`.

- If a single file path: read that file
- If a directory: use Glob to find all `.html`, `.css`, `.jsx`, `.tsx`, `.vue`, `.svelte` files
- If "current file" or no path: ask the user which file to audit

## Step 3: Scan for Violations

### Critical Violations (Must Fix)

These break the design system's core identity:

| Rule | What to Detect | Suggested Fix |
|------|---------------|---------------|
| No scale on hover | `transform: scale(...)` on `:hover`, `.hover`, mouseover handlers | Replace with `translateY(-1px)` for buttons, `translateX(2px)` for tags/nav |
| System easing only | `ease`, `ease-in`, `ease-out`, `ease-in-out`, `linear` in transitions/animations | Replace with `var(--ease-hourglass)`, `var(--ease-pendulum)`, or `var(--ease-bell)` |
| Token colors only | Raw hex (`#xxx`), `rgb()`, `rgba()` for semantic colors (not in custom property definitions) | Map to nearest system token |
| System fonts only | `font-family` declarations not using `var(--font-*)` | Replace with `var(--font-declaration)`, `var(--font-narrator)`, or `var(--font-technical)` |

### Warning Violations (Should Fix)

| Rule | What to Detect | Suggested Fix |
|------|---------------|---------------|
| Whole pixel sizes | Fractional font sizes (`13.5px`, `0.875rem` = 14px) | Round to nearest whole pixel |
| Manufactured radii | `border-radius` not in {2, 3, 4, 6, 8, 9999}px | Map to `var(--radius-xs)` through `var(--radius-full)` |
| No global grain | Grain applied to `body`, `html`, `*`, or root `::before` | Move to specific elements only |
| Polarity support | Custom colors without `[data-polarity="light"]` overrides | Add light mode overrides |
| System shadows | Raw `box-shadow` values that could use tokens | Replace with `var(--shadow-sm)` through `var(--shadow-elevated)` |
| Wrong hover pattern | `translateY` on tags/nav, `translateX` on buttons | Use correct motion per component type |

### Info Violations (Nice to Fix)

| Rule | What to Detect | Suggested Fix |
|------|---------------|---------------|
| Token spacing | Hardcoded `px` matching system spacing (4, 8, 12, 16, 24, 32, 48, 64px) | Replace with `var(--space-*)` tokens |
| Reduced motion | Animations without `@media (prefers-reduced-motion: reduce)` | Add reduced-motion fallback |
| System durations | Raw `ms` values (300ms, 0.3s) | Replace with `var(--dur-micro)`, `var(--dur-standard)`, `var(--dur-macro)` |
| Voice assignment | Typography in wrong context (Declaration for body text) | Reassign to correct voice |
| Token letter-spacing | Raw `letter-spacing` values | Replace with `var(--tracking-*)` tokens |
| Token line-height | Raw `line-height` values | Replace with `var(--leading-*)` tokens |

## Step 4: Produce Compliance Report

```markdown
## Design System Compliance Report

**File:** `[path/to/file]`
**Score:** X/Y rules checked — Z violations found
**Compliance:** XX%

---

### Critical (X violations)

| Line | Property | Current Value | Fix |
|------|----------|--------------|-----|
| 42 | `transition-timing-function` | `ease-in-out` | `var(--ease-hourglass)` |

### Warnings (X violations)

| Line | Property | Current Value | Fix |
|------|----------|--------------|-----|
| 15 | `border-radius` | `12px` | `var(--radius-xl)` (8px) |

### Info (X violations)

| Line | Property | Current Value | Fix |
|------|----------|--------------|-----|
| 5 | `padding` | `16px` | `var(--space-md)` |

---

### Summary
[1-2 sentence assessment. Most impactful changes first.]

### Quick Wins
[3-5 highest-impact changes]
```

## Rules

- Be thorough. Check EVERY property in the file.
- Don't flag CSS custom property definitions (`:root { --my-color: #333 }` is fine — usage matters).
- Don't flag inline SVG colors or data URIs.
- Don't flag third-party library styles — note them separately.
- If reviewing HTML: check class names against the compact lookup for correctness.
- Report line numbers when possible.
- Be constructive, not punitive.
