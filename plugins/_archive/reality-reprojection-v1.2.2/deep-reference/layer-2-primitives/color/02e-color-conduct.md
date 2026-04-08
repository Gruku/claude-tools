# REALITY REPROJECTION

## Layer 2: Visual Primitives — Color
### Conduct, Mischief, & Rules

**Version:** 0.3
**Date:** 2026-02-10
**Part of:** Color Primitive
**See also:** [Overview](02a-color-overview.md), [Dimensions](02b-color-dimensions.md), [Attributes](02c-color-attributes.md), [Dimensional Map](02d-color-dimensional-map.md)

---

## Color Conduct

*How the system uses color as a whole — the etiquette of deployment.*

Where dimensions describe what color is made of and attributes describe what color does, Color Conduct describes how color **behaves**. These are the instincts that govern the system's relationship with color across any context.

### Neutrality is the default field

The majority of any Reality Reprojection interface is neutral — value and temperature doing the work, with hue absent or minimal. This is not a rule about percentages. It is a principle about signal: color means more when it arrives into a field that isn't already saturated with color. The neutral field is what gives semantic and identity hues their force.

### Color is deployed, not applied

Color does not fill in a layout after the structure is built. It is a structural decision — placed with the same intentionality as a typographic voice choice. "What color should this be?" is the wrong question. "Does this element need color, and if so, what job is color doing here?" is the right one.

### Consistency within, variation between

Within a single context, color assignments are strict. A hue that means "success" in one place means "success" everywhere. Between contexts — different projects, different media, different mood settings — the palette can shift entirely. The roles and dimensions remain; the specific expressions change.

### Less color, more meaning

When in doubt, remove a color. If the system still communicates clearly, the color was not earning its place. This is the color expression of "every element exists because it must" — applied to hue and saturation specifically. A single well-placed accent communicates more than a palette of five competing hues.

---

## Quiet Mischief in Color

Color mischief follows the same principle established in typography: **functional play** — the delight and the meaning arrive together.

In color, mischief lives at the outer dimensions. An unexpected moment of saturation in an otherwise muted context — a loading indicator that briefly flares vivid, a success confirmation that pulses warmer before settling. A temperature shift that rewards attention — a hovered element gaining a subtle warmth that the resting state didn't carry. The signature hue appearing somewhere small and surprising — a scrollbar track, a cursor accent, a selection highlight.

Mischief does not violate the concentric model. It uses it — briefly pushing an outer dimension further than the context's resting state, then returning. The surprise is the excursion. The function is the signal.

What mischief is not: random color. Decorative gradients. Rainbow effects. Color applied for visual interest without carrying information. The system's playfulness is precise — a wink, not a costume.

---

## Color Non-Negotiables

*Rules that hold regardless of medium, context, or project.*

### 1. The system must be complete at every dimensional depth

A context using only D1 is not degraded. It is the color system operating at its foundation. Completeness is not a function of how many dimensions are active.

### 2. Value hierarchy must function independently of hue

Strip all hue and saturation. If the hierarchy, emphasis, and states are not still readable through value contrast alone, the color system is broken.

### 3. Color must never be the sole carrier of meaning

Every semantic distinction communicated through hue must have a non-hue fallback — iconography, labeling, position, or pattern. This is a structural consequence of the concentric model, not an accessibility patch.

### 4. Temperature must be consistent within a context

Warm and cool do not mix within a single context. Temperature is a global setting. Tonal inconsistency reads as error, not variety.

### 5. Every hue present must have a job

No decorative hue. No color "for balance." If a hue cannot be assigned to a role — structural, semantic, or identity — it does not belong.

### 6. Saturation at full intensity must be earned

Full saturation is reserved for moments of maximum intent. If everything is vivid, nothing is.

### 7. Outer dimensions must respect inner dimensions

Hue does not override value hierarchy. Saturation does not break contrast requirements. Each dimension modulates the ones beneath it — it does not overrule them.

---

## How This Connects to Layer 1

| Layer 1 Element | Color Expression |
|---|---|
| **Constraints generate clarity** | Four dimensions ordered by priority, not a flat palette. Fewer hues with clearer jobs. Restraint as default instinct. |
| **Progressive revelation** | Value reads first, temperature is felt, hue communicates meaning, saturation rewards attention. The dimensions *are* progressive revelation. |
| **Craftsmanship as respect** | Value hierarchy that reads at a glance. Generous contrast. The twenty-minute equivalent: color that never creates friction between the user and the content. |
| **Medium as collaborator** | Dimensional depth adapts to medium capability. An OLED at D1 is not fighting its constraints — it is the system collaborating with them. |
| **Monumental ↔ Intimate** | Full saturation at display scale (Monumental) vs. subtle value distinctions at detail scale (Intimate). The dynamic range between Declaration-level color and Whisper-level color. |
| **Utilitarian ↔ Sensorial** | Structural roles carrying function (Utilitarian) with temperature and saturation adding material quality (Sensorial). |
| **Constrained ↔ Expansive** | D1-only on a monochrome display (Constrained) vs. full four-dimension deployment on a rich interface (Expansive). Same system, different depth. |
| **Technical ↔ Human** | Cool temperature, restrained saturation, monospace context (Technical) vs. warm temperature, signature hue, organic moments (Human). |
| **Confident ↔ Inviting** | High contrast and vivid accent (Confident) vs. approachable warmth and subtle emphasis (Inviting). |
| **Quiet mischief** | Saturation flares, temperature shifts, the signature hue in unexpected places. Functional play at the outer dimensions. |

---

## Open Questions for Layer 3

1. **The System Algorithm** — The process for applying the Dimensional Map to specific contexts is a system-wide pattern. Layer 3 should formalize this as a unified decision process.

2. **Mood** — The meta-setting that positions all dimension dials simultaneously for a given context. The dimensions do not operate in isolation. Layer 3 should define specific moods, their dial positions, and per-medium applicability.

3. **Specific palette casting** — Actual values for signature hue, semantic roles, neutral scale.

4. **Token architecture** — Naming convention, encoding of dimensional decisions.

5. **Per-medium dimensional availability** — Explicit mapping of which dimensions are available on which media.

6. **Polarity mapping** — How values map between light-ground and dark-ground orientations.

7. **Data visualization palette** — Categorical and sequential palettes generated from the dimensional model.

8. **Signature hue selection** — Casting criteria, relationship to earlier explorations.

9. **Color and typography interaction** — How color attributes map to typographic voices.

10. **State specifics** — Value shifts, hue assignments, and transition behaviors for each interactive state.

---

## Color Casting (Placeholder)

*The casting process — selecting specific color values that fulfill the roles — is a separate exercise.*

| Role | Value | Rationale |
|---|---|---|
| Signature Hue | *TBD* | |
| Neutral Scale (warm) | *TBD* | |
| Neutral Scale (cool) | *TBD* | |
| Success | *TBD* | |
| Warning | *TBD* | |
| Critical | *TBD* | |
| Informational | *TBD* | |
| Categorical Palette | *TBD* | |

---

## Evolution Log

| Version | Date | Change |
|---------|------|--------|
| 0.3 | 2026-02-10 | Complete draft — conduct, mischief, non-negotiables, Layer 1 connections, open questions |

---

*Color is the second primitive of Layer 2. Every choice made here should be traceable to Layer 1, and compatible with the typography decisions that preceded it.*
