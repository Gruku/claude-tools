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
/* Cyan tint */
background: rgba(13, 235, 255, 0.09); /* on top of frost base */

/* Lime tint */
background: rgba(184, 255, 51, 0.08);

/* Pink tint */
background: rgba(250, 0, 119, 0.08);

/* Orange tint */
background: rgba(255, 102, 13, 0.08);
```

Light mode adjusts these opacities proportionally lower.

## Chromatic Aberration — REMOVED

> **Status:** Removed from the CSS cascade as of 2026-02-20. The `chromatic.css` file exists for reference but is NOT imported by `system.css`.

The pink/lime text-shadow fringe effect only worked at hero-scale declaration text. On smaller text, badges, edges, and interactive elements it distracted from content and hurt readability. If revisited, scope exclusively to `.declaration` elements at 48px+ sizes.

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

## Frost + Grain — The Gold Standard

The recommended default for premium surfaces. Frost provides translucent depth; grain adds tactile roughness. The `.mat-frost-grain` class combines both with optimized parameters.

### Gold Standard Parameters

```css
.mat-frost-grain::before {
  /* Grain layer */
  background-size: 512px 512px;       /* larger scale than standalone grain */
  mix-blend-mode: overlay;             /* not soft-light — overlay for frost context */
  opacity: 0.185;                      /* higher than standalone grain */
  filter: contrast(0.75);              /* softer contrast on frost */
}
```

### Usage

```html
<!-- Gold standard frosted card -->
<div class="card mat-frost-medium mat-frost-grain">
  <div class="card__body" style="position: relative; z-index: 3;">Content</div>
</div>

<!-- With dot halftone accent (opt-in, not default) -->
<div class="card mat-frost-medium mat-frost-grain mat-grain-dot">
  <div class="card__body" style="position: relative; z-index: 3;">Content</div>
</div>
```

### Tuning Guidelines

| Background Alpha | Grain | Blur |
|-----------------|-------|------|
| Low (0.6) | Full density (0.185), 512px | Any blur level looks good |
| Medium (0.75) | Full density, 512px | Low to medium blur |
| High (0.85+) | Reduced density (`.mat-frost-grain--dense`, 0.12, 384px) | Low blur only |

### Tinted Frost

All four tint variants work well with frost-grain:

```css
/* None (default) — just frost bg */
/* Cyan */    background: rgba(13, 235, 255, 0.09);
/* Lime */    background: rgba(184, 255, 51, 0.08);
/* Pink */    background: rgba(250, 0, 119, 0.08);
/* Orange */  background: rgba(255, 102, 13, 0.08);
```

Light mode adjusts these opacities proportionally lower.

## Dot Halftone

A radial-gradient dot pattern with edge-band masking — a thematic accent, NOT a default treatment. Applied as `::after` on `.mat-grain-dot` containers.

**Rules:**
- Dot halftone is opt-in only — never apply by default
- Works best with low blur + low background alpha
- Small dot size + medium gap + low opacity = best results
- Use as thematic accent on feature cards, not every surface

### Parameters

```css
.mat-grain-dot::after {
  background-image: radial-gradient(circle at center, rgba(255,255,255,1) 0 1.5px, transparent 2.3px);
  background-size: 11px 11px;          /* medium gap */
  opacity: 0.13;                        /* low opacity */
  mix-blend-mode: soft-light;
  /* Edge-band mask — dots concentrated at edges */
  mask-image: radial-gradient(ellipse at center, transparent calc(100% - 80px), black 100%);
}
```

## Combining Materials

Materials can be layered on the same element:

```html
<!-- Gold standard frosted card with grain -->
<div class="card mat-frost-medium mat-frost-grain">
  <div class="card__body" style="position: relative; z-index: 3;">Content</div>
</div>

<!-- Chromatic heading on frosted surface -->
<h2 class="declaration mat-chromatic-text">Title</h2>
```

### Layering Rules

- **Frost + grain is the recommended default** for premium surfaces (use `.mat-frost-grain`)
- Grain goes on top of frost (z-index: 1 for grain pseudo-element)
- Dot halftone goes above grain (z-index: 2) — opt-in only via `.mat-grain-dot`
- Never combine more than one grain profile on the same element
- Chromatic is removed from the system — do not use `.mat-chromatic-*` classes
- Content inside frost-grain elements needs `position: relative; z-index: 3` to sit above material layers

## Shimmer Pass

A directional light sweep for frosted surfaces. Different from skeleton shimmer — this is a continuous decorative effect.

```css
.shimmer-pass {
  background: linear-gradient(105deg,
    transparent 40%,
    rgba(255,255,255,0.02) 45%,
    rgba(255,255,255,0.04) 50%,
    rgba(255,255,255,0.02) 55%,
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
