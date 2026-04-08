# REALITY REPROJECTION

## Layer 2: Visual Primitives — Color
### The Four Dimensions

**Version:** 0.3
**Date:** 2026-02-10
**Part of:** Color Primitive
**See also:** [Overview](02a-color-overview.md), [Attributes](02c-color-attributes.md), [Dimensional Map](02d-color-dimensional-map.md), [Conduct & Rules](02e-color-conduct.md)

---

## Introduction

The dimensions are the building blocks of color in Reality Reprojection. Each dimension is a distinct property of color, ordered by foundational priority. Understanding each dimension separately is essential before seeing how they work together.

**Read the dimensions sequentially** — D2 depends on understanding D1, D3 builds on D1+D2, and D4 completes the stack.

---

## Dimension 1 — Value

*Light and dark. The foundation that everything else modulates.*

### The Job

Value is the system's most fundamental color property — the difference between light and dark, independent of any hue or temperature. It is the first thing the eye reads: before you register that something is red or warm, you register that it is lighter or darker than what surrounds it.

In Reality Reprojection, value does the structural work. It establishes foreground and background, separates surfaces, communicates what to read first and what to find later, signals whether something is active or disabled. Every other dimension builds on this scaffolding — and if it is weak, no amount of hue or saturation will rescue it.

Value is also the survivalist dimension. On a 1-bit OLED, a monochrome e-ink display, a single-color print run — value is all there is. The system must be fully functional here, in the same sense that a well-designed black and white photograph is not a degraded color photograph. It is complete.

### The Character

Value in Reality Reprojection is calibrated, not neutral. The system's resting tones sit slightly inward from the absolute extremes — pure black and pure white are available but reserved. The darkest darks retain a trace of air. The lightest lights carry a trace of substance. This is a value-level decision that temperature will later resolve fully — but even in a strictly monochrome context, the range feels considered rather than mechanical.

Between the extremes, value steps are deliberate. Each step exists to create a specific distinction — a surface from its background, a card from its surface, an element from its card. No accidental mid-tones. This connects to Craftsmanship as Respect: hierarchy reads at a glance, not puzzled over. And to Constraints Generate Clarity: a limited number of well-chosen value steps communicates more than a continuous gradient where nothing quite separates.

The value structure must be coherent in both polarities — light ground with dark foreground, and the inverse. These are not "light mode" and "dark mode" as implementation concerns. They are two orientations of the same hierarchy, and both must feel equally considered. The system does not have a primary polarity with a derived alternate. It has two native states.

Value contributes to the sense of physical weight that Layer 1 describes. An element at definite contrast against its surface begins to feel *placed*.

### At This Depth

Value alone unlocks:
- Structural hierarchy
- Emphasis spectrum (boldest to subtlest)
- Elevation through value steps
- Basic states (resting, active, disabled)
- Figure-ground relationship

---

## Dimension 2 — Temperature

*Warm or cool. The dimension that gives the system its fingerprint.*

### The Job

Temperature is the bias in the neutral tones — the difference between a gray that leans amber and one that leans blue, between an off-black that feels like charcoal and one that feels like ink. It does not introduce new colors. It tints the entire value structure from Dimension 1, shifting every tone along a warm–cool axis.

Where value builds the scaffolding, temperature makes it feel like it belongs to someone. This is the dimension that resolves the off-white/off-black instinct established at D1 into a specific identity.

Temperature is the quietest dimension. Most users will never consciously register it. They will not think "this interface feels warm." They will think "this feels good" or "this feels like the same system I used yesterday." It operates below the threshold of attention — which is exactly why it is so effective as an identity carrier.

### The Character

Reality Reprojection's default temperature leans warm — slightly. Inherited directly from Layer 1: "the slight warmth of Anthropic's own design, not the orange glow of a fireplace." A tendency, not a mandate.

The neutral tones carry a faint warmth — grays lean a degree toward amber, toward stone, toward human. This is the color equivalent of the Narrator's humanist curves: functional, not decorative, but unmistakably not machine-plotted.

This warmth is the system's resting state. A project dialed hard toward Technical can and should push temperature toward cool or fully neutral. The warm default is the system relaxed. Cool temperature is the system at attention. Both are authentic.

**Temperature must be consistent within a context.** A warm interface with a single cool-tinted panel feels broken. A deliberately cool interface is fine — a tonally inconsistent one is not. Temperature is a global setting, not a per-element choice.

### At This Depth

Temperature does not unlock new attributes. It transforms everything from D1 — hierarchy, emphasis, elevation, states all gain tonal identity. At D1, the system could belong to anyone. At D2, it becomes recognizable as Reality Reprojection.

---

## Dimension 3 — Hue

*The actual colors. The dimension where meaning through color becomes possible.*

### The Job

Hue is the first dimension that adds capability rather than transforming what exists. At Dimensions 1 and 2, the system can communicate hierarchy, emphasis, and identity — but it cannot say "this is an error" or "these are different categories" or "this element belongs to the brand" through color alone. Hue makes that possible.

This is a significant threshold. Everything below hue is structural and tonal. Hue introduces *semantic differentiation*: the ability for two elements at identical value and temperature to carry entirely different meanings. This is why hue is the third dimension rather than the first — the structural and tonal foundation must already be in place.

Hue carries the highest risk of any dimension. It is the easiest to overuse, the most culturally loaded, and the most likely to create accessibility failures. Every hue introduced is a commitment — it claims a meaning, and that meaning must be consistent or the system erodes.

### The Character

Hue in Reality Reprojection is **earned**. It arrives into a context that is already working and adds meaning that the lower dimensions could not provide alone. It does not arrive to make things prettier. It arrives because something needs to be *said*.

Hue operates in two territories:

**Hue as meaning.** Semantic differentiation — "this is an error," "these are different categories," "this requires attention." Fully defined in the Attributes section. Functional, constrained, governed by convention.

**Hue as identity.** The signature accent that appears at moments of brand expression — a progress bar, a selected state, a single vivid element that says "this belongs to Reality Reprojection." Where temperature carries identity below the threshold of attention, a signature hue carries it *above* that threshold. It is the color equivalent of the Declaration voice. The specific hue is a casting decision; the principle that the system *has* one is a dimension-level truth.

How both territories are expressed — how many hues, how prominently — is governed by context. A terminal interface might express identity through temperature alone and use a single semantic hue sparingly. A poster might deploy a rich palette where hue carries atmosphere as much as meaning. The principle is not "use few colors" or "use many" — it is "every color present is doing something."

The system's default instinct with hue is restraint. Not minimalism — restraint. Minimalism removes color as a principle. Restraint holds color in reserve so that when it appears, it carries force.

### At This Depth

Hue unlocks semantic differentiation through color — roles, categories, brand identity. Contexts operating at D2 or below cannot rely on hue-based meaning; semantic roles that require hue must have non-hue fallbacks (iconography, labeling, position).

---

## Dimension 4 — Saturation

*Intensity. The dimension that controls how loudly hue speaks.*

### The Job

Saturation is the volume knob for Dimension 3. It determines whether a hue whispers or shouts — whether a blue is a muted steel or an electric signal, whether a red is a quiet blush or an urgent alarm. Without saturation control, every hue arrives at the same intensity, and the system loses its ability to modulate emphasis within color itself.

Saturation is the outermost dimension — the last to be added, the first to be stripped. It completes the concentric model's promise: value provides structure, temperature provides identity, hue provides meaning, saturation provides *emphasis within meaning*. The ability to say not just "this is a warning" but "this is an urgent warning" or "this is a gentle caution."

### The Character

Saturation in Reality Reprojection is surgical — a word from Layer 1 that finds its home here. High saturation is a resource to be spent deliberately, not a default to be dialed back from.

The resting state of most color in the system is **moderately desaturated**. This creates the field that makes moments of high saturation powerful. A vivid accent against a muted context is dramatic. The same accent against other vivid colors is noise.

Full saturation is the Declaration of the color system — reserved for moments of maximum intent: a primary action, a signature brand element, a critical alert. Low saturation is the Whisper — desaturated hues that carry meaning quietly, still communicating but without competing.

### At This Depth

Saturation unlocks emphasis within a single hue and atmospheric depth — the perception that some elements are closer and more active while others recede. At D3, an error is red. At D4, an error can be urgently red or cautiously red.

---

## How the Dimensions Interact

Each dimension modulates the previous one rather than sitting alongside it:

- **D1** is the structure
- **D2** tints all of D1
- **D3** adds meaning to the D1+D2 structure
- **D4** modulates emphasis within D1+D2+D3

Removing an outer dimension doesn't break the system. A monochrome display removes D2, D3, and D4 — but D1 still works perfectly. Stripping hue and saturation from a full-color interface leaves a warm monochrome system that communicates hierarchy, emphasis, and state with perfect clarity.

This is the concentric model's fundamental strength: **nothing is dependent on the next layer. Each dimension adds capability without creating new requirements.**

---

## Evolution Log

| Version | Date | Change |
|---------|------|--------|
| 0.3 | 2026-02-10 | Dimensions documented — four-dimensional model with jobs, character, at-this-depth capabilities |

---

**See also:**
- [Attributes](02c-color-attributes.md) — The semantic jobs each dimension performs
- [Dimensional Map](02d-color-dimensional-map.md) — The matrix showing capability availability
- [Conduct & Rules](02e-color-conduct.md) — How to use these dimensions consistently
