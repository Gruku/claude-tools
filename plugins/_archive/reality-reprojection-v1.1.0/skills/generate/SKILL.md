---
name: generate
description: "Generate new HTML/CSS components following the Reality Reprojection design system from natural language descriptions"
argument-hint: [component description, e.g. "login form with email and password"]
---

# Reality Reprojection — Generate Component

You generate HTML and CSS components that conform to the Reality Reprojection design system. Every element you produce must use system tokens, classes, and patterns.

## Step 1: Load References

Read reference files using the Read tool. You have a context budget — respect it.

**CONTEXT BUDGET: Stay under 16k reference tokens. Tier 1 alone is sufficient for 90% of requests.**

### Tier 1 — Load these. (~10k tokens)
- `${CLAUDE_PLUGIN_ROOT}/reference/design-tokens.md` — All CSS custom properties
- `${CLAUDE_PLUGIN_ROOT}/reference/component-catalog.md` — All 22 components with classes, variants, states, HTML
- `${CLAUDE_PLUGIN_ROOT}/reference/typography.md` — Voice assignments per component

**After loading Tier 1, STOP and ask yourself: "Do I have enough to complete this request?"** If yes — proceed to Step 2. Do not load more.

### Tier 2 — Load one of these ONLY IF the request specifically requires it. (~2-5k tokens each)
- `${CLAUDE_PLUGIN_ROOT}/reference/composition-recipes.md` — ONLY for full page layouts (dashboard, settings page, article). A single button, card, or form does NOT need this.
- `${CLAUDE_PLUGIN_ROOT}/reference/material-treatments.md` — ONLY if the user explicitly mentions grain, frost, or chromatic effects.
- `${CLAUDE_PLUGIN_ROOT}/reference/design-rules.md` — ONLY if you need to verify a rule not already in this skill file's Rules section below.

### Tier 3 — Restricted. Read the gate below before touching these.

```
GATE: You MUST answer ALL THREE questions with "yes" before loading ANY Tier 3 file:
  1. Have I loaded and fully read the relevant Tier 1 and Tier 2 files?
  2. Is there a specific question I cannot answer from those files?
  3. Can I name the exact section/file I need, rather than browsing?
If any answer is "no" → do NOT load Tier 3. Return to the files you have.
```

- `${CLAUDE_PLUGIN_ROOT}/reference/bible.html` — 31k tokens. The full canonical demo page. NEVER load the whole file. If you pass the gate, read ONLY the specific line range: lines 1584-1884 (component patterns) or lines 1889-2112 (page compositions).
- `${CLAUDE_PLUGIN_ROOT}/deep-reference/` — 65k tokens across 38 files. NEVER load multiple files. If you pass the gate, read ONLY the single most relevant file (e.g., `deep-reference/layer-2-primitives/motion/05a-motion-overview.md`).

**Examples of correct loading decisions:**
- "Generate a login form" → Tier 1 only. Catalog has forms, tokens has values. Done.
- "Build a dashboard page with sidebar" → Tier 1 + composition-recipes.md. Recipes has the dashboard pattern.
- "Create a frosted glass card with grain texture" → Tier 1 + material-treatments.md. Materials has frost + grain specs.
- "I need to understand the philosophy behind the easing system" → Tier 1 + one deep-reference motion file. This is rare.

## Step 2: Parse the Request

Read the user's component description from `$ARGUMENTS`. Identify:

- What type of component(s) are needed
- What variants or states are required
- What content will be displayed
- Whether materials (grain, frost) are involved

## Step 3: Check the Catalog

Search the component catalog for existing components that match or overlap with the request.

- **If a match exists:** Compose from existing classes. Do NOT reinvent what already exists.
- **If partial match:** Extend with custom CSS that uses system tokens exclusively.
- **If no match:** Build from system primitives (tokens, voices, spacing, motion).

## Step 4: Generate HTML

Use the system's class naming conventions:

- **Base class:** `.component-name` (e.g., `.card`, `.btn`, `.form-group`)
- **Variants:** `.component-name--variant` (e.g., `.card--elevated`, `.btn--primary`)
- **Sub-elements:** `.component-name__child` (e.g., `.card__header`, `.alert__body`)
- **States:** `.is-active`, `.is-expanded`, `.is-disabled`, `.is-current`, `.is-loading`

Assign typographic voices correctly:
- Headlines/titles → Declaration classes (`.declaration`, `.declaration--h3`)
- Body text/descriptions → Narrator classes (`.narrator`, `.narrator--small`)
- Labels/metadata/data → Technical classes (`.technical`, `.technical--small`)

## Step 5: Generate Custom CSS (only if needed)

If existing system classes don't fully cover the component, write custom CSS that:

- Uses ONLY system tokens for all values (colors, spacing, shadows, radii, motion, fonts)
- Follows the design rules:
  - Easing: only `var(--ease-hourglass)`, `var(--ease-pendulum)`, `var(--ease-bell)`, `var(--ease-hourglass-settle)`
  - Hover: `translateY(-1px)` for buttons, `translateX(2px)` for tags/nav items
  - Radii: only 2/3/4/6/8/9999px via tokens
  - Font sizes: whole pixels only
  - No `scale()` on hover. No `ease` or `ease-in-out`.
- Includes `[data-polarity="light"]` overrides where needed
- Includes `@media (prefers-reduced-motion: reduce)` fallbacks for animations
- Uses `--foreground-on-accent` for any text on colored backgrounds

## Step 6: Present Output

Format your response as:

```markdown
## Generated: [Component Name]

### HTML
```html
[Complete HTML markup with system classes]
```

### Custom CSS (if needed)
```css
[CSS using only system tokens]
```

### CSS Setup
The project needs the Reality Reprojection CSS bundle. If not already set up:
- Run `/reality-reprojection:setup` to bootstrap the full design system
- Or manually: copy `${CLAUDE_PLUGIN_ROOT}/bundle/reality-reprojection.css` into the project
- Font import required:
  ```html
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@800&family=DM+Sans:ital,wght@0,400;0,600;0,700&family=JetBrains+Mono:wght@600&display=swap" rel="stylesheet">
  ```
- Set `<html data-polarity="dark">` (or `"light"`)

### Integration Notes
- Polarity: [Does this work in both dark/light? Any custom overrides?]
- Motion: [What hover/transition behavior is included?]
- Accessibility: [Reduced motion support? Focus states?]
- Voices: [Which typographic voices are used where?]
```

## Rules — Non-Negotiable

- NEVER hardcode colors. Use `var(--token-name)`.
- NEVER use `ease`, `ease-in-out`, or raw cubic-bezier. Use system easing tokens.
- NEVER use `scale()` on hover.
- NEVER use fractional font sizes.
- NEVER use radii outside {2, 3, 4, 6, 8, 9999}px.
- ALWAYS support both polarities.
- ALWAYS include reduced-motion fallbacks for animations.
- ALWAYS use the correct typographic voice for the context.
- Prefer existing component classes over custom CSS.
- Do NOT write to files. Present the code for the user/agent to place.
