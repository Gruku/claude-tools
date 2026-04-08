---
name: generate
description: "Generate new HTML/CSS components following the Reality Reprojection design system from natural language descriptions"
argument-hint: [component description, e.g. "login form with email and password"]
---

# Reality Reprojection — Generate Component

You generate HTML and CSS components that conform to the Reality Reprojection design system. Every element you produce must use system tokens, classes, and patterns.

## Step 1: Load Compact Lookup, Assess, Go Deeper Only If Needed

**First:** Load `${CLAUDE_PLUGIN_ROOT}/reference/compact-lookup.md` (~1.5k tokens). This has HTML patterns, variants, component token names, override patterns, and rules for all 22 components.

**Then assess:** Is the compact lookup sufficient for this request?

### Decision Tree

```
1. Is this a standard component (button, card, badge, form, table, etc.)?
   → Compact lookup is enough. Generate immediately.

2. Does it involve materials (grain, frost, chromatic, shimmer)?
   → Load: ${CLAUDE_PLUGIN_ROOT}/reference/material-treatments.md ONLY (~3k tokens)

3. Does it involve a full page layout (dashboard, article, settings page)?
   → Load: ${CLAUDE_PLUGIN_ROOT}/reference/composition-recipes.md ONLY (~4k tokens)

4. Is it a novel component not in the compact lookup?
   → Load: ${CLAUDE_PLUGIN_ROOT}/reference/component-catalog.md ONLY (~5k tokens)

5. Do you need exact token CSS values (rare — only if building custom tokens)?
   → Load: ${CLAUDE_PLUGIN_ROOT}/reference/design-tokens.md ONLY (~4k tokens)

NEVER load multiple reference files for a single request.
Compact lookup + one targeted file handles 99% of requests.
```

### Deep Reference — Gated (rare)

```
GATE: ALL THREE must be "yes":
  1. Have I checked the compact lookup AND loaded the one relevant reference file?
  2. Is there a specific question I still cannot answer?
  3. Can I name the exact file/section I need?
If any "no" → STOP. You have enough.
```

- `${CLAUDE_PLUGIN_ROOT}/reference/bible.html` — 31k tokens. NEVER load whole. Lines 1584-1884 (components) or 1889-2112 (compositions) only.
- `${CLAUDE_PLUGIN_ROOT}/deep-reference/` — 65k tokens across 38 files. ONE specific file only.

### Examples

- "Generate a primary button" → Compact lookup. Load nothing. Instant.
- "Generate a login form" → Compact lookup has form-group pattern. Load nothing.
- "Build a dashboard with sidebar" → Load composition-recipes.md only.
- "Create a frosted card with grain" → Load material-treatments.md only.
- "Build a data table I haven't seen before" → Load component-catalog.md only.

## Step 2: Parse the Request

Read the user's component description from `$ARGUMENTS`. Identify:

- What type of component(s) are needed
- What variants or states are required
- What content will be displayed
- Whether materials (grain, frost) are involved

## Step 3: Generate HTML

Use the system's class naming conventions:

- **Base class:** `.component-name` (e.g., `.card`, `.btn`, `.form-group`)
- **Variants:** `.component-name--variant` (e.g., `.card--elevated`, `.btn--primary`)
- **Sub-elements:** `.component-name__child` (e.g., `.card__header`, `.alert__body`)
- **States:** `.is-active`, `.is-expanded`, `.is-disabled`, `.is-current`, `.is-loading`

Assign typographic voices correctly:
- Headlines/titles → Declaration classes (`.declaration`, `.declaration--h3`)
- Body text/descriptions → Narrator classes (`.narrator`, `.narrator--small`)
- Labels/metadata/data → Technical classes (`.technical`, `.technical--small`)

## Step 4: Generate Custom CSS (only if needed)

If existing system classes don't fully cover the component, write custom CSS that:

- Uses ONLY system tokens for all values (colors, spacing, shadows, radii, motion, fonts)
- Uses component tokens for overrideable properties (e.g., `--btn-bg: var(--signature-fill)`)
- Follows the design rules:
  - Easing: only `var(--ease-hourglass)`, `var(--ease-pendulum)`, `var(--ease-bell)`, `var(--ease-hourglass-settle)`
  - Hover: `translateY(-1px)` for buttons, `translateX(2px)` for tags/nav items
  - Radii: only 2/3/4/6/8/9999px via tokens
  - Font sizes: whole pixels only
  - No `scale()` on hover. No `ease` or `ease-in-out`.
- Includes `[data-polarity="light"]` overrides where needed
- Includes `@media (prefers-reduced-motion: reduce)` fallbacks for animations
- Uses `--foreground-on-accent` for any text on colored backgrounds

## Step 5: Present Output

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
