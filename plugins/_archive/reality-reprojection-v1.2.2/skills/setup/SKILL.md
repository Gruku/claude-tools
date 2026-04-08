---
name: setup
description: "Bootstrap the Reality Reprojection design system into a target project — copies CSS bundle, adds font imports, sets polarity"
argument-hint: [project directory or 'current project']
---

# Reality Reprojection — Setup

You bootstrap the Reality Reprojection design system into a target web project. This copies the CSS bundle, adds required font imports, and configures the HTML entry point.

## Step 1: Identify Target Project

From `$ARGUMENTS`, determine the target project directory.

- If a directory path is given: use it
- If "current project" or no path: use the current working directory
- If ambiguous: ask the user

Use Glob to find the project's HTML entry point(s) (e.g., `index.html`, `*.html`) and any existing CSS directory structure.

## Step 2: Copy the CSS Bundle

The bundled design system is a single CSS file containing all 36 modules in cascade order.

**Source:** `${CLAUDE_PLUGIN_ROOT}/bundle/reality-reprojection.css`

Read the bundle file, then write it to the target project. Choose the destination based on project structure:

| Project Has | Write To |
|-------------|----------|
| `css/` or `styles/` directory | `css/reality-reprojection.css` or `styles/reality-reprojection.css` |
| `public/` directory | `public/css/reality-reprojection.css` |
| `src/assets/` directory | `src/assets/css/reality-reprojection.css` |
| `static/` directory | `static/css/reality-reprojection.css` |
| No clear structure | `css/reality-reprojection.css` (create the directory) |

Tell the user where you placed the file.

## Step 3: Add Font Imports

The design system requires three Google Fonts. Add this to the `<head>` of the HTML entry point(s):

```html
<!-- Reality Reprojection — Required Fonts -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@800&family=DM+Sans:ital,wght@0,400;0,600;0,700&family=JetBrains+Mono:wght@600&display=swap" rel="stylesheet">
```

If the project uses a build tool or framework, suggest the appropriate method instead:

| Framework | Method |
|-----------|--------|
| React/Next.js | Add `<link>` tags to `public/index.html`, `_document.tsx`, or `app/layout.tsx` |
| Vue/Nuxt | Add to `index.html` or `nuxt.config` head section |
| Svelte/SvelteKit | Add to `app.html` |
| Astro | Add to `Layout.astro` or similar base layout |
| Plain HTML | Add directly to `<head>` |

## Step 4: Link the CSS

Add the stylesheet link after the font imports:

```html
<!-- Reality Reprojection Design System -->
<link rel="stylesheet" href="[path-to-reality-reprojection.css]">
```

Use the correct relative path based on where you placed the file in Step 2.

## Step 5: Set Polarity

Add `data-polarity` to the `<html>` element:

```html
<html data-polarity="dark">
```

Default to `dark`. If the user's project already has a light theme or preference, use `light` instead.

## Step 6: Confirm Setup

Present a summary:

```markdown
## Reality Reprojection — Setup Complete

**CSS Bundle:** `[destination path]` (single file, all 36 modules)
**Fonts:** Added Syne 800, DM Sans 400/600/700, JetBrains Mono 600
**Stylesheet:** Linked in `[html file]`
**Polarity:** `dark` (set on `<html>`)

### Quick Start

Use system classes directly in your HTML:

```html
<h1 class="declaration declaration--h2">HEADING</h1>
<p class="narrator">Body text here.</p>
<button class="btn btn--primary">ACTION</button>
<span class="badge badge--signature">Label</span>
```

### Next Steps

- `/reality-reprojection:generate` — Create new components
- `/reality-reprojection:convert` — Convert existing code to use system tokens
- `/reality-reprojection:review` — Audit code for compliance
```

## Rules

- ALWAYS show the user what you're about to write/modify before doing it
- If the project already has a `reality-reprojection.css`, ask before overwriting
- Do NOT modify existing stylesheets — only add the system CSS alongside them
- Respect the project's existing directory conventions
