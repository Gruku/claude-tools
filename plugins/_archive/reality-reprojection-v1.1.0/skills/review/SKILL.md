---
name: review
description: "Audit HTML/CSS for Reality Reprojection design system compliance — reports violations with severity and suggested fixes"
argument-hint: [file path or directory to audit]
---

# Reality Reprojection — Review Compliance

You audit HTML/CSS code for compliance with the Reality Reprojection design system. You scan for violations, categorize them by severity, and suggest specific fixes.

## Step 1: Load References

Read reference files using the Read tool. Reviews are the leanest workflow — keep it that way.

**CONTEXT BUDGET: Stay under 10k reference tokens. Tier 1 is sufficient for all compliance audits.**

### Tier 1 — Load these. (~5k tokens)
- `${CLAUDE_PLUGIN_ROOT}/reference/design-rules.md` — Rules to enforce
- `${CLAUDE_PLUGIN_ROOT}/reference/design-tokens.md` — Valid token values

This is enough. The rules file lists every violation pattern. The tokens file lists every valid value. Proceed to Step 2.

### Tier 2 — Load ONLY IF the audit includes checking HTML class correctness (not just CSS values).
- `${CLAUDE_PLUGIN_ROOT}/reference/component-catalog.md` — Correct class names, variants, sub-elements.

### Tier 3 — Off-limits for reviews.

`bible.html`, `deep-reference/`, `composition-recipes.md`, and `material-treatments.md` are irrelevant to compliance auditing. A review checks values against rules — it does not need layout recipes, design philosophy, or visual references. Do not load them.

## Step 2: Read Target Files

Read the file(s) specified in `$ARGUMENTS`.

- If a single file path: read that file
- If a directory: use Glob to find all `.html`, `.css`, `.jsx`, `.tsx`, `.vue`, `.svelte` files, then read each
- If "current file" or no path: ask the user which file to audit

## Step 3: Scan for Violations

Check every line against the design system rules. Categorize findings:

### Critical Violations (Must Fix)

These break the design system's core identity:

| Rule | What to Detect | Suggested Fix |
|------|---------------|---------------|
| No scale on hover | `transform: scale(...)` on `:hover`, `.hover`, mouseover handlers | Replace with `translateY(-1px)` for buttons, `translateX(2px)` for tags/nav |
| System easing only | `ease`, `ease-in`, `ease-out`, `ease-in-out`, `linear` in transitions/animations | Replace with `var(--ease-hourglass)`, `var(--ease-pendulum)`, or `var(--ease-bell)` |
| Token colors only | Raw hex (`#xxx`), `rgb()`, `rgba()` for semantic colors (not in custom properties definition) | Map to nearest system token (see design-tokens.md) |
| System fonts only | `font-family` declarations not using `var(--font-*)` | Replace with `var(--font-declaration)`, `var(--font-narrator)`, or `var(--font-technical)` |

### Warning Violations (Should Fix)

These degrade visual coherence:

| Rule | What to Detect | Suggested Fix |
|------|---------------|---------------|
| Whole pixel sizes | Fractional font sizes (`13.5px`, `0.875rem` = 14px) | Round to nearest whole pixel |
| Manufactured radii | `border-radius` values not in {2, 3, 4, 6, 8, 9999}px | Map to nearest: `var(--radius-xs)` through `var(--radius-full)` |
| No global grain | Grain/noise applied to `body`, `html`, `*`, or `::before` on root | Move to specific elements only |
| Polarity support | Custom colors without `[data-polarity="light"]` overrides | Add light mode overrides |
| System shadows | Raw `box-shadow` values that could use tokens | Replace with `var(--shadow-sm)` through `var(--shadow-elevated)` |
| Wrong hover pattern | `translateY` on tags/nav (should be `translateX`), `translateX` on buttons (should be `translateY`) | Use correct motion pattern per component type |

### Info Violations (Nice to Fix)

These are improvement opportunities:

| Rule | What to Detect | Suggested Fix |
|------|---------------|---------------|
| Token spacing | Hardcoded `px` values matching system spacing (4, 8, 12, 16, 24, 32, 48, 64px) | Replace with `var(--space-*)` tokens |
| Reduced motion | Animations/transitions without `@media (prefers-reduced-motion: reduce)` | Add reduced-motion fallback |
| System durations | Raw `ms` values (e.g., `300ms`, `0.3s`) | Replace with `var(--dur-micro)`, `var(--dur-standard)`, or `var(--dur-macro)` |
| Voice assignment | Typography used in wrong context (e.g., Declaration for body text) | Reassign to correct voice per component |
| Token letter-spacing | Raw `letter-spacing` values | Replace with `var(--tracking-*)` tokens |
| Token line-height | Raw `line-height` values | Replace with `var(--leading-*)` tokens |

## Step 4: Produce Compliance Report

Format your output as:

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
| 87 | `transform` (hover) | `scale(1.05)` | `translateY(-1px)` |
| 103 | `color` | `#333333` | `var(--foreground-default)` |

### Warnings (X violations)

| Line | Property | Current Value | Fix |
|------|----------|--------------|-----|
| 15 | `border-radius` | `12px` | `var(--radius-xl)` (8px) |
| 28 | `font-size` | `13.5px` | `14px` (`--size-narrator-small`) |

### Info (X violations)

| Line | Property | Current Value | Fix |
|------|----------|--------------|-----|
| 5 | `padding` | `16px` | `var(--space-md)` |
| 67 | `margin-bottom` | `24px` | `var(--space-lg)` |

---

### Summary

[1-2 sentence assessment of overall compliance. Note the most impactful changes to make first.]

### Quick Wins
[List the 3-5 changes that would have the biggest impact on compliance]
```

## Rules

- Be thorough. Check EVERY property in the file.
- Don't flag CSS custom property definitions themselves (`:root { --my-color: #333 }` is fine — it's the USAGE that matters).
- Don't flag inline SVG colors or data URIs.
- Don't flag third-party library styles (Bootstrap, Tailwind utilities, etc.) — note them separately.
- If reviewing HTML: check class names against the component catalog for correctness.
- If reviewing JSX/TSX: check both inline styles and className values.
- Report line numbers when possible for easy navigation.
- Be constructive, not punitive. The goal is to help teams adopt the system.
