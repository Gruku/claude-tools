# Reality Reprojection — Material Treatments

> Materials give surfaces their physical character. Applied selectively per-element, never globally.

## Grain

Grain adds tactile texture via an SVG noise pattern applied as a `::before` pseudo-element. It encodes material hierarchy — more grain means more premium/critical.

### Grain Texture

```css
--grain-texture: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
```

### Grain Base Pattern (shared by all variants)

```css
.mat-grain-* {
  position: relative;
  isolation: isolate;
}

.mat-grain-*::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image: var(--grain-texture);
  background-size: 256px 256px;
  pointer-events: none;
  z-index: 1;
  border-radius: inherit;
  mix-blend-mode: soft-light;
  filter: contrast(0.85);
  will-change: opacity;
  backface-visibility: hidden;
  transform: translateZ(0);
}
```

### Grain Profiles

| Class | Opacity | Purpose | Use On |
|-------|---------|---------|--------|
| `.mat-grain-fine` | `0.025` | Injection-molded feel | Cards, quotes, settings headers |
| `.mat-grain-coarse` | `0.04` | Brushed aluminum authority | Dashboard headers, elevated panels |
| `.mat-grain-concrete` | `0.03` | Architectural foundation | Section backgrounds |
| `.mat-grain-gradient` | `0.02` | Universal anti-banding | Every gradient element (required) |
| `.mat-grain-edge` | `0.015` | Barely visible at borders | Edge treatment, felt-not-seen |

### Material Hierarchy

- **No grain (matte)** = baseline, standard surface
- **Fine grain** = elevated, professional quality
- **Coarse grain** = premium, mission-critical
- **Concrete** = architectural foundation, section-level

### Custom Grain Application

To add grain to a custom element without utility classes:

```css
.my-element {
  position: relative;
  isolation: isolate;
}

.my-element::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image: var(--grain-texture);
  background-size: 256px 256px;
  opacity: 0.025; /* fine */
  mix-blend-mode: soft-light;
  filter: contrast(0.85);
  pointer-events: none;
  z-index: 1;
  border-radius: inherit;
  will-change: opacity;
  backface-visibility: hidden;
  transform: translateZ(0);
}
```

## Frost (Backdrop Blur)

Frost creates translucent glass surfaces. Requires four properties working together: backdrop-filter blur + translucent background + border + shadow.

### Frost Tokens

```css
/* Blur amounts */
--frost-blur-light: 8px;
--frost-blur-medium: 16px;
--frost-blur-heavy: 24px;

/* Dark mode backgrounds */
--frost-bg-light: rgba(13, 13, 12, 0.6);
--frost-bg-medium: rgba(13, 13, 12, 0.75);
--frost-bg-heavy: rgba(13, 13, 12, 0.85);

/* Light mode backgrounds */
--frost-bg-light: rgba(245, 243, 237, 0.6);    /* [data-polarity="light"] */
--frost-bg-medium: rgba(245, 243, 237, 0.75);   /* [data-polarity="light"] */
--frost-bg-heavy: rgba(245, 243, 237, 0.85);    /* [data-polarity="light"] */
```

### Frost Classes

| Class | Blur | Background Opacity | Use For |
|-------|------|-------------------|---------|
| `.mat-frost-light` | `8px` | `0.6` | Subtle depth, floating panels |
| `.mat-frost-medium` | `16px` | `0.75` | Headers, navigation bars |
| `.mat-frost-heavy` | `24px` | `0.85` | Modals, full overlays |

All frost classes automatically include: `border: 1px solid var(--border-subtle)`

### Custom Frost Application

```css
.my-frosted-element {
  background: var(--frost-bg-medium);
  backdrop-filter: blur(var(--frost-blur-medium));
  -webkit-backdrop-filter: blur(var(--frost-blur-medium));
  border: 1px solid var(--border-subtle);
  box-shadow: var(--shadow-md);
}
```

### Accent-Tinted Frost

For colored frost surfaces (as seen in the bible's frost cards):

```css
/* Blue tint */
background: rgba(0, 211, 250, 0.09); /* on top of frost base */

/* Lime tint */
background: rgba(100, 250, 0, 0.08);

/* Pink tint */
background: rgba(250, 1, 123, 0.08);
```

Light mode adjusts these opacities proportionally lower.

## Chromatic Aberration

Subtle RGB channel split effect — creates a prism-edge quality. Pink channel shifts left, lime/signature channel shifts right.

### Chromatic Tokens

```css
--chromatic-a: var(--accent-pink);     /* Left fringe color (default: #fa017b) */
--chromatic-b: var(--accent-lime);     /* Right fringe color (default: #64fa00) */
--chromatic-offset-lg: 0.7px;           /* Hero-scale split */
--chromatic-offset-sm: 0.4px;           /* Subtle split */
```

Override `--chromatic-a` and `--chromatic-b` per page for custom accent palettes.

### Chromatic Classes

| Class | Effect | Use For |
|-------|--------|---------|
| `.mat-chromatic-text` | Strong text-shadow split (0.7px) | Hero headings, display text |
| `.mat-chromatic-text--subtle` | Subtle text-shadow split (0.4px) | Section headings, smaller declarations |
| `.mat-chromatic-edge` | Box-shadow fringe (always visible) | Badges, cards at rest |
| `.mat-chromatic-edge--hover` | Box-shadow fringe (hover only) | Interactive elements |
| `.mat-chromatic-glow` | Box-shadow fringe + 4px spread | Neon lines, glowing elements |

### How It Works

```css
/* Text: offset text-shadows in opposite directions */
.mat-chromatic-text {
  text-shadow:
    -0.7px 0 var(--chromatic-a),  /* pink/muted shifts left */
     0.7px 0 var(--chromatic-b);  /* vivid shifts right */
}

/* Edge: offset box-shadows */
.mat-chromatic-edge {
  box-shadow:
    -0.4px 0 0 var(--chromatic-a),
     0.4px 0 0 var(--chromatic-b);
}
```

### Reduced Motion

All chromatic effects are removed under `prefers-reduced-motion: reduce` — text-shadow and box-shadow set to `none`.

## Shadow Scale

Shadows create the elevation hierarchy. They encode depth and importance.

### Elevation Shadows (Dark Mode)

| Token | Value | Use For |
|-------|-------|---------|
| `--shadow-sm` | `0 1px 2px rgba(0,0,0,0.25), 0 0 0 1px rgba(0,0,0,0.08)` | Cards at rest, subtle lift |
| `--shadow-md` | `0 2px 8px rgba(0,0,0,0.30), 0 1px 2px rgba(0,0,0,0.15)` | Elevated cards, dropdowns |
| `--shadow-lg` | `0 8px 24px rgba(0,0,0,0.35), 0 2px 6px rgba(0,0,0,0.18)` | Prominent surfaces, popovers |
| `--shadow-elevated` | `0 12px 40px rgba(0,0,0,0.40), 0 4px 12px rgba(0,0,0,0.20), 0 0 0 1px rgba(0,0,0,0.05)` | Modals, active dialogs |

### Accent Shadow

| Token | Value | Use For |
|-------|-------|---------|
| `--shadow-signature` | `0 4px 16px rgba(0,211,250,0.25), 0 1px 4px rgba(0,211,250,0.12)` | Brand elements, signature glow |

### Soul Pass Shadows (Manufactured Depth)

| Token | Value | Use For |
|-------|-------|---------|
| `--shadow-inset` | `inset 0 2px 4px rgba(0,0,0,0.20)` | Pressed/active button state |
| `--shadow-recessed` | `inset 0 1px 3px rgba(0,0,0,0.15), inset 0 0 0 1px rgba(0,0,0,0.05)` | Milled channel: inputs, toggle tracks, progress tracks |
| `--shadow-inner-glow` | `inset 0 1px 0 rgba(255,255,255,0.2)` | Active thumbs, filled progress bars |
| `--highlight-inner` | `inset 0 1px 0 rgba(255,255,255,0.15)` | Button manufacturing feel, pagination current |

### Light Mode Shadow Adjustments

In light polarity, shadows use warmer `rgba(38, 37, 35, ...)` tones instead of pure black, and at lower opacities:

| Token | Light Mode Value |
|-------|-----------------|
| `--shadow-sm` | `0 1px 3px rgba(38,37,35,0.08), 0 0 0 1px rgba(38,37,35,0.04)` |
| `--shadow-md` | `0 2px 8px rgba(38,37,35,0.10), 0 1px 3px rgba(38,37,35,0.06)` |
| `--shadow-lg` | `0 4px 14px rgba(38,37,35,0.10), 0 2px 4px rgba(38,37,35,0.06), 0 0 0 1px rgba(38,37,35,0.03)` |
| `--shadow-elevated` | `0 8px 30px rgba(38,37,35,0.12), 0 4px 10px rgba(38,37,35,0.08), 0 0 0 1px rgba(38,37,35,0.03)` |
| `--shadow-recessed` | `inset 0 1px 3px rgba(38,37,35,0.10), inset 0 0 0 1px rgba(38,37,35,0.04)` |
| `--shadow-inner-glow` | `inset 0 1px 0 rgba(255,255,255,0.35)` (stronger) |
| `--highlight-inner` | `inset 0 1px 0 rgba(255,255,255,0.25)` (stronger) |

## Combining Materials

Materials can be layered on the same element:

```html
<!-- Frosted card with fine grain -->
<div class="card mat-frost-medium mat-grain-fine">
  Content with both frost and grain texture
</div>

<!-- Chromatic heading on frosted surface -->
<h2 class="declaration mat-chromatic-text">Title</h2>
```

### Layering Rules

- Grain goes on top of frost (z-index: 1 for grain pseudo-element)
- Chromatic is independent (text-shadow or box-shadow, no pseudo-elements)
- Never combine more than one grain profile on the same element
- Frost + grain is the most common premium combination
- Chromatic is reserved for hero/display elements — don't overuse

## Dot Halftone

A radial-gradient dot pattern with edge-band masking — a defining v3 material treatment. Applied as `::after` on `.mat-grain-dot` containers, it creates a subtle perforated effect concentrated at the edges.

### Dot Halftone Base

```css
.mat-grain-dot::after {
  background-image: radial-gradient(circle at center, rgba(255,255,255,1) 0 1.5px, transparent 2.3px);
  background-size: 11px 11px;
  opacity: 0.13;
  mix-blend-mode: soft-light;
  mask-image: radial-gradient(ellipse at center, transparent calc(100% - 80px), black 100%);
}
```

### Grain Profiles (with dot halftone)

Four named profiles with configurable custom properties for both grain and dot layers:

| Profile | Class | Grain Scale | Grain Opacity | Contrast | Dot Gap | Dot Opacity | Dot Band |
|---------|-------|------------|---------------|----------|---------|-------------|----------|
| Fine | `.mat-profile-fine` | 420px | 0.045 | 0.9 | 13px | 0.055 | 66px |
| Coarse | `.mat-profile-coarse` | 512px | 0.065 | 0.8 | 11px | 0.07 | 80px |
| Concrete | `.mat-profile-concrete` | 360px | 0.08 | 1.05 (multiply) | 15px | 0.05 | 90px |
| Edge | `.mat-profile-edge` | 384px | 0.06 | 0.88 | 10px | 0.06 | 56px |

### Usage

```html
<!-- Card with fine grain profile + dot halftone -->
<div class="card mat-grain-dot mat-profile-fine">
  Content with grain + dot halftone
</div>
```

## Shimmer Pass

A directional light sweep for frosted surfaces. Different from skeleton shimmer — this is a continuous decorative effect.

```css
.shimmer-pass {
  background: linear-gradient(105deg,
    transparent 40%,
    rgba(255,255,255,0.04) 45%,
    rgba(255,255,255,0.08) 50%,
    rgba(255,255,255,0.04) 55%,
    transparent 60%);
  background-size: 250% 100%;
  animation: shimmer-sweep 6s var(--ease-hourglass) infinite;
}
```

Used inside frost-backed cards to add a subtle light sweep.

## Frost Backdrop

Tri-color radial gradient atmospheric container using all three identity colors (cyan, pink, lime).

```html
<div class="frost-backdrop">
  <!-- Content automatically z-index: 2 above gradient + grain -->
  <div class="card">...</div>
</div>
```

The `.section-frost-bg` variant provides a subtler section-level atmospheric tint with gradient orbs.

## Entrance Animation

Scroll-triggered float-in with blur-to-sharp transition.

```html
<div class="material-float-in" style="--i: 0;">Content</div>
<!-- JS adds .is-visible via IntersectionObserver -->
```

Stagger via `--i` custom property (80ms intervals)
