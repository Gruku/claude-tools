# REALITY REPROJECTION

## Layer 2: Visual Primitives — Material & Vocabulary
### The Material Properties

**Version:** 0.1
**Date:** 2026-02-14
**Part of:** Material & Vocabulary Primitive

---

## The Material Properties

*The optical characteristics that define what the field — and anything in it — is made of.*

### Material as Field Property

The field is not empty space with objects placed in it — it is a *medium* with substance. Elements exist *within* that medium, inheriting its material properties and able to selectively override them.

This means:
- **The ground has material** — not void, but substance with optical character
- **Depth layers have material at their boundaries** — how you perceive layering
- **Elements inherit field material** — can selectively override it
- **Material varies across the field** — responds to field structure

---

## Opacity

*How much of what lies beneath is visible through a surface.*

Opacity is the most fundamental material property. The system's resting instinct is **not fully opaque**. Default surfaces carry translucency that allows the field beneath to bleed through, filtered.

Opacity carries meaning:
- **Permanence** — Permanent elements tend opaque; temporary ones tend translucent
- **Hierarchy** — Primary working surface more opaque than supporting surfaces
- **Depth** — Translucent over opaque is how the eye perceives layering

---

## Blur

*How the field is distorted when seen through a translucent surface.*

Blur is opacity's companion. Translucent surfaces blur what lies beneath — creating frosted quality (not transparent).

Blur amount ties to purpose:
- **Light blur** — Preserves context sense
- **Heavy blur** — Isolates the surface into its own world
- **No blur** — Creates transparency (for overlays)

**Note:** Blur is medium-dependent. Fallback is increased opacity.

---

## Surface Finish

*The tactile quality of the surface itself — what it feels like to the eye.*

The system's default finish is **matte** — quality matte (like injection-molded plastic, not flat cheap).

Finishes available:
- **Matte** — The resting state, quality finish
- **Satin** — Step toward reflectivity, subtle sheen
- **Grain** — Subtle texture that grounds material, procedural not photographic

---

## Edge Treatment

*How elements meet their surroundings — the boundary between figure and field.*

The system's instinct is **clean, considered edges** — consistent with the Manufactured trait.

Edge treatment tools:
- **Value shift** — Element at different value than ground (cleanest)
- **Border** — Thin, defined line, precise and minimal
- **Shadow** — Depth expressed as darkening, tight and considered
- **Separation through space** — No treatment, field structure creates boundary

---

## Depth Expression

*How the field's depth layers become visible.*

Depth expression combines the properties above:
- Surface at higher depth may be **more opaque**
- Surface below may be **blurred**
- Upper surface may cast a **shadow**
- Upper surface may have **different finish**

**Critical rule:** Depth must function at Color's D1 (monochrome). Strip hue and saturation — if depth is not still perceivable, it's broken.

---

## Evolution Log

| Version | Date | Change |
|---------|------|--------|
| 0.1 | 2026-02-14 | Properties documented — Opacity, Blur, Finish, Edge, Depth |

---

**See also:** [System & Rules](04c-material-system.md) for non-negotiables
