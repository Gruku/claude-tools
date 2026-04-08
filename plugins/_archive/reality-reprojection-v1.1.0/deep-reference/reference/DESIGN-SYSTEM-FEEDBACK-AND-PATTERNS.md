# Reality Reprojection — Feedback & Pattern Reference

Crystallized from design review sessions, Volo's feedback, and codebase exploration. This is the "taste document" — what to do, what NOT to do, and why.

---

## 1. Text Sizes Must Be Stable Whole Pixels

**The problem:** Using rem at a 22.4px base produces fractional pixel values (0.72rem = 16.128px). Browsers sub-pixel render these inconsistently. Text feels unstable across the experience.

**The rule:** Define all type sizes in px. No `.something` endings.

```css
/* BAD — produces 16.128px, 13.44px, 10.752px */
--size-narrator-default: 0.72rem;
--size-narrator-whisper: 0.6rem;
--size-section-label: 0.48rem;

/* GOOD — clean, predictable rendering */
--size-narrator-default: 16px;
--size-narrator-whisper: 13px;
--size-section-label: 10px;
```

The 140% scale (22.4px html) is still the conceptual base for the system's proportions — but tokens express sizes as whole px.

---

## 2. Grain Is Selective, Never Global

**Volo's feedback:** Grain everywhere flattens the hierarchy. It should be a material *choice*, not a default.

**The rule:** No `body::after` grain overlay. Apply grain only to specific elements that earn it.

```css
/* BAD — global grain on everything */
body::after {
  content: '';
  position: fixed;
  inset: 0;
  opacity: 0.028;
  background-image: var(--grain-fine);
}

/* GOOD — grain as a deliberate material decision */
.mat-grain-fine::before { opacity: 0.025; }   /* Cards, quotes, settings headers */
.mat-grain-coarse::before { opacity: 0.04; }  /* Dashboard headers, elevated surfaces */
.mat-concrete::before { opacity: 0.03; }      /* Section backgrounds */
.mat-gradient-grain::before { opacity: 0.02; } /* EVERY gradient (breaks banding) */
.mat-edge-grain::before { opacity: 0.015; }   /* Barely visible at borders */
```

**Where grain belongs:**
- Gradients (always — breaks CSS banding, the "secret ingredient")
- Elevated cards and panels (fine grain = injection-molded feel)
- Dashboard/app headers (coarse grain = brushed aluminum authority)
- Full-width section dividers (concrete = architectural)
- Card borders (edge grain — "barely visible, but felt")

**Where grain does NOT belong:**
- Body/page background (the ground is substance through *color*, not texture)
- Reading surfaces (article body, settings content areas)
- Over photography or illustrations
- Globally, on everything

---

## 3. Radii Must Feel Manufactured, Not Soft

**The problem:** Default radii (4/6/10/14px) feel rounded and organic — like a theme, not a material.

**The rule:** Use root's tighter manufactured scale. Think LEGO, machined aluminum, etched glass edges.

```css
/* FEELS SOFT (AI default) */
--radius-sm: 4px;
--radius-md: 6px;
--radius-lg: 10px;
--radius-xl: 14px;

/* FEELS MANUFACTURED (correct) */
--radius-xs: 2px;
--radius-sm: 3px;
--radius-md: 4px;
--radius-lg: 6px;
--radius-xl: 8px;
```

The difference between 6px and 8px radius is the difference between "rounded rectangle" and "precisely machined edge." RP chooses the latter.

---

## 4. Hover Animations Must NOT Feel AI-Default

**Volo's feedback:** Generic CSS transitions (ease, 300ms, scale) are the first sign of AI-generated design. Every interaction needs a named character.

**The rule:** Use the Clockwork Collection easing. Never `ease` or `ease-in-out`. Every hover has a specific physical metaphor.

```css
/* BAD — generic AI-default hover */
.card:hover {
  transform: scale(1.02);
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  transition: all 0.3s ease;
}

/* GOOD — Hourglass character with manufactured feel */
.btn--primary:hover {
  transform: translateY(-1px);  /* lift, not scale */
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.2),
              0 4px 16px rgba(91,110,245,0.3);
  transition: all var(--dur-standard) var(--ease-hourglass);
}
.btn--primary:active {
  transform: translateY(0);  /* snap back */
  box-shadow: inset 0 2px 4px rgba(0,0,0,0.2);
  transition-duration: var(--dur-micro);  /* micro-duration snap */
}
```

**Hover cheat sheet:**
| Element | Hover Effect | Easing | NOT This |
|---------|-------------|--------|----------|
| Buttons | translateY(-1px) + shadow | Hourglass | scale(1.05) |
| Button active | translateY(0) + inset shadow | dur-micro snap | scale(0.95) |
| Cards | border-color + shadow deepen | Hourglass | transform anything |
| Value cards | signature glow + translateY(-3px) | dur-macro Hourglass | scale or rotate |
| Tags/chips | translateX(2px) | dur-standard | color change only |
| Links | color to signature | dur-micro | underline appear |
| Card--tilt ONLY | ±2deg perspective rotation | Hourglass-settle | Applied broadly |

**Key principle:** `translateY(-1px)` feels like a physical button lifting. `scale(1.02)` feels like a CSS demo. The inner top highlight (`inset 0 1px 0 rgba(255,255,255,0.15)`) on primary buttons is the manufactured-feel signature.

---

## 5. 3D Tilt Is a Signature Effect, Not a Default

**Volo's feedback:** "Signature effect for separate element" — tilt should be reserved, not applied broadly.

**The rule:** Only `.card--tilt` gets perspective rotation. Regular cards NEVER transform on hover.

```html
<!-- WRONG — tilt on every card -->
<div class="card" data-tilt>...</div>

<!-- RIGHT — tilt is an opt-in signature -->
<div class="card">Regular card — border + shadow hover only</div>
<div class="card card--tilt">Value showcase card — this one tilts</div>
```

Tilt parameters when used: ±2deg max, perspective 1000px, Hourglass easing on move, Hourglass-settle (overshoot) on leave. Subtle enough to feel curious, not carnival.

---

## 6. The Signature Hue Is Evolved Blue-Violet

**The decision:** Cyan — bright, confident, distinct. Two supporting accents: lime for energy, pink for warmth.

```css
--signature: #00d3fa;        /* The identity — cyan */
--signature-vivid: #3de6ff;   /* Highlights, active states */
--signature-muted: #0c8ea4;   /* Pressed states, borders */
--signature-dim: rgba(0, 211, 250, 0.24); /* Backgrounds, recessed */
--accent-lime: #64fa00;       /* Energy, positive emphasis */
--accent-pink: #fa017b;       /* Warmth, secondary emphasis */
```

**Why this matters:** Cyan reads as "confident technology with warmth underneath." The two accents create a three-point color identity that drives atmospheric effects (frost arenas, gradients) and gives the system chromatic range without losing focus.

The glow variants (`--signature-glow` at 0.1 opacity, `--signature-glow-strong` at 0.2, `--signature-glow-intense` at 0.35) create atmosphere without overwhelming. Glow is atmospheric light, not neon.

---

## 7. Three Typographic Voices — Each Has ONE Job

**The principle:** Energy comes from the *distance* between voices, not from having many weights.

| Voice | Font | Weight | Job | Never Used For |
|-------|------|--------|-----|---------------|
| Declaration | Syne 800 | Heavy | Commands, headlines, names | Body text, descriptions |
| Narrator | DM Sans 500 | Medium | Reading, explaining, describing | Labels, timestamps |
| Technical | JetBrains Mono 500 | Mono | Measuring, labeling, code | Headlines, body text |

**Font selector experiment:** Declaration font can be swapped live between Syne (default), Bebas Neue, Archivo Black, Anton, Oswald, and Barlow Condensed. Each needs a different weight map:

```javascript
const fontWeights = {
  "'Syne', sans-serif": 800,
  "'Bebas Neue', sans-serif": 400,
  "'Archivo Black', sans-serif": 400,
  "'Anton', sans-serif": 400,
  "'Oswald', sans-serif": 600,
  "'Barlow Condensed', sans-serif": 800,
};
```

---

## 8. Hero Text Must Fit the Viewport

**Volo's feedback:** "Words didn't fit into the page fully."

**The rule:** At 140% scale, hero text must be responsive-first. Break deliberately.

```css
/* Responsive clamp that actually fits */
--size-declaration-hero: clamp(56px, 9vw, 112px);
```

```html
<!-- Deliberate line break, not overflow -->
<h1 class="declaration declaration--hero">Reality<br>Reprojection</h1>
```

Test at: 320px, 768px, 1024px, 1440px, 1920px. At every width, the title should feel *placed*, not crammed.

---

## 9. Polarity Is Two Native States, Not Primary/Alternate

**The principle:** Dark mode is not "the real one" with light as an afterthought. Both are equally considered.

```css
/* Light mode shadows are RICHER — they're the star here */
[data-polarity="light"] {
  --shadow-elevated: 0 4px 14px rgba(40,37,31,0.10),
                     0 2px 4px rgba(40,37,31,0.06),
                     0 0 0 1px rgba(40,37,31,0.03);
}
```

**What changes between polarities:**
- Ground scale inverts (dark 0→100 becomes light 100→0)
- Shadow composition changes (dark: deeper black, light: warm layered)
- Frost backgrounds swap (dark: rgba(20,18,16), light: rgba(248,244,235))
- Everything else (signature hue, semantic colors, spacing, motion) stays identical

---

## 10. The Survivalist Dial Is a Proof of System Integrity

**The concept:** A continuous slider from 0 (full experience) to 100 (survivalist mode). If the system works at both ends, it works.

**Degradation levels:**
| Range | Name | What happens |
|-------|------|-------------|
| 0–25 | Full | All materials, grain, blur, shadows, full motion |
| 25–50 | Rich | Grain reduces, blur thins, shadows flatten |
| 50–75 | Reduced | No grain, no blur, no shadows, motion collapses to Tick |
| 75–100 | Survivalist | Monochrome (D1 only), single weight, filled vs outlined |

**Why this matters:** If a design system can't degrade gracefully, it's decoration, not structure. The concentric color model (D1→D2→D3→D4) means you can strip outer dimensions and inner ones remain coherent. Survivalist mode is the proof.

---

## 11. Non-Hue Fallbacks Are Non-Negotiable

**The principle:** Color is never the sole carrier of meaning. Every semantic state has a shape fallback.

```css
/* Success: filled circle ● */
.badge--success::before { content: '\25CF\00a0'; }

/* Warning: triangle ▲ */
.badge--warning::before { content: '\25B2\00a0'; }

/* Critical: diamond ◆ + heavier border */
.badge--critical { border-width: 2px; }
.badge--critical::before { content: '\25C6\00a0'; }
```

In survivalist mode (monochrome), these shapes are the ONLY way to distinguish success from warning from critical. The shapes must be visible and distinct even without color.

---

## 12. Material Hierarchy Encodes Meaning

**The pattern (from pricing tiers):**
- **Matte** (no grain) = baseline, standard, free tier
- **Fine grain** = elevated, professional, recommended
- **Coarse grain** = premium, mission-critical, enterprise

This isn't arbitrary. Each grain density carries physical metaphor:
- Matte = smooth plastic (commodity)
- Fine = injection-molded (precision-manufactured)
- Coarse = brushed aluminum (industrial strength)
- Concrete = poured concrete (architectural foundation)

Material choice IS content. A card with coarse grain says "this is serious" before you read a word.

---

## 13. Spacing Is a Field, Not Padding

**The principle:** Elements are emitters with spatial influence. Space is equilibrium, not arbitrary margins.

```css
/* Declaration pushes neighbors away — 96px field */
--emitter-declaration: 96px;

/* Narrator creates rhythmic, periodic spacing — 24px field */
--emitter-narrator: 24px;

/* Technical permits dense packing — 8px field */
--emitter-technical: 8px;
```

A Declaration headline next to body text doesn't need "margin-bottom: 48px." It needs its natural emitter strength. The spacing IS the voice's spatial signature.

---

## 14. Architecture: Modular CSS Cascade

**28 files in strict cascade order via `css/system.css`:**

```
css/system.css           — Master import (cascade order is critical)
  foundations/            — Tokens: reset, fonts, colors, typography, spacing, motion
  materials/             — Surface: grain, frost, shadows, radii
  modes/                 — Context: polarity (light/dark), survivalist (degradation)
  components/            — Elements: buttons, cards, badges, forms, navigation,
                           modals, tables, lists, headers, footers, toggles, tags, tabs
  utilities/             — Overrides: layout, visibility, states
```

```
demo/rr-test.html        — Component catalogue (all primitives)
demo/preview-landing.html — Real-world: monumental character
demo/preview-dashboard.html — Real-world: utilitarian character
demo/preview-article.html   — Real-world: intimate character
demo/preview-settings.html  — Real-world: constrained character
```

This separation means:
- An AI agent can read `foundations/colors.css` to understand the palette
- An AI agent can read `system.css` imports to know what components exist
- A designer can change `--signature: #00d3fa` to `--signature: #E05252` and the entire system adapts
- The survivalist dial works because degradation rules live in `modes/survivalist.css`, not scattered across markup

---

## 15. Things That Look Small But Matter Enormously

- **Inner top highlight on buttons:** `inset 0 1px 0 rgba(255,255,255,0.15)` — the manufactured-feel signature
- **Warm-biased grays:** Grays lean amber, NOT blue. `#a8a298` not `#a0a0a0`
- **Off-extremes:** Darkest is `#0d0d0c` not `#000000`. Lightest is `#f5f3ed` not `#ffffff`. Pure extremes feel digital; off-extremes feel material.
- **Selection color:** Uses signature surface tint, not browser default blue
- **Scrollbar styling:** Warm, considered, rounded — matches the ground
- **Polarity transition on body:** Background and color transition with `--dur-standard` and `--ease-hourglass` — the switch feels like a physical flip, not a flash
- **Edge grain mask:** CSS `mask-image` constrains grain to borders only — felt, not seen
- **Gradient grain on EVERY gradient:** The universal anti-banding treatment. Without it, CSS gradients look cheap.
