---
name: using-reality-reprojection
description: "Load the Reality Reprojection design system context without taking action — use when starting a session that will involve design work"
---

# Using Reality Reprojection

You have loaded the Reality Reprojection design system context. This skill does NOT take action — it establishes awareness of the system so you can use it throughout the conversation.

## Available Skills

When the user needs design system work, invoke the appropriate skill:

| Skill | Purpose |
|-------|---------|
| `reality-reprojection:setup` | Bootstrap CSS bundle, fonts, polarity into a project |
| `reality-reprojection:generate` | Create new components from natural language descriptions |
| `reality-reprojection:convert` | Transform existing HTML/CSS to use system tokens |
| `reality-reprojection:review` | Audit code for design system compliance |
| `reality-reprojection:apply` | Auto-detect intent and route to the correct skill above |
| `reality-reprojection:log-design-feedback` | Log feedback and observations from any project to the canonical RR feedback log |

## Quick Reference

**Three fonts:** Syne 800 (declarations), DM Sans 400/600/700 (narrator/body), JetBrains Mono 600 (technical)

**Polarity:** `data-polarity="dark"` or `data-polarity="light"` on `<html>`

**Core classes:**
- Typography: `.declaration`, `.narrator`, `.technical`
- Buttons: `.btn`, `.btn--primary`, `.btn--ghost`, `.btn--danger`
- Badges: `.badge`, `.badge--signature`, `.badge--muted`
- Cards: `.card`, `.card--elevated`, `.card--inset`
- Materials: `.grain`, `.frost`, `.shimmer-pass`

**Design tokens:** All spacing, color, and typography use CSS custom properties (e.g., `--space-md`, `--color-signature`, `--font-declaration`)

## How to Use in This Session

1. When the user asks you to build, modify, or style UI — invoke the relevant skill above
2. When writing CSS directly — use system tokens, never raw values
3. When reviewing — check against design system compliance
4. For reference during conversation — load `${CLAUDE_PLUGIN_ROOT}/reference/compact-lookup.md` for the full token/class reference

## Rules

- Never guess at class names or tokens — use the compact lookup or invoke a skill
- Every component must use system classes, not custom CSS where a system class exists
- Materials (grain, frost, shimmer-pass) are additive overlays, not replacements
- Chromatic aberration is REMOVED from the system — do not use `.mat-chromatic-*` classes
- Polarity (dark/light) is handled by the system — never hardcode colors
- No emojis — use SVG icons, icon fonts, or Unicode symbols (◐, ✕, →)
