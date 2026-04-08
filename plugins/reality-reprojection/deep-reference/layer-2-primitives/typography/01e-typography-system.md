# REALITY REPROJECTION

## Layer 2: Visual Primitives — Typography
### System & Relationships

**Version:** 0.1 (Draft)
**Date:** 2026-02-07
**Part of:** Typography Primitive
**References:** [Overview](01a-typography-overview.md), [Declaration](01b-typography-declaration.md), [Narrator](01c-typography-narrator.md), [Technical](01d-typography-technical.md)

---

## Relationships Between Voices

### Contrast is the Engine

The energy of the type system comes from the *distance* between voices, not from any single voice in isolation. The Declaration's weight against the Narrator's calm. The Narrator's organic curves against the Technical's grid. These contrasts make each voice more itself.

**Principle:** If two voices start to feel similar in a layout, something is miscalibrated. Each voice should be immediately distinguishable at a glance — not through decoration, but through fundamental character.

### Hierarchy is Shared, Identity is Not

All three voices participate in establishing visual hierarchy, but they do not blend into each other. The Declaration can appear above the Narrator. The Technical can appear within Narrator-led content. But the Declaration does not gradually become the Narrator through intermediate weights — the transition is a clean handoff, not a gradient.

### Pairing Rules

These are structural principles. Specific mixing rules per medium are a Layer 3 concern.

- **Declaration + Narrator** is the primary pairing. The Declaration opens. The Narrator continues. This is the most common combination.
- **Narrator + Technical** is the secondary pairing. The Narrator provides context. The Technical provides specifics. Documentation, tutorials, data-rich content.
- **Declaration + Technical** is a high-contrast pairing — dramatic and precise. Use with intention. This combination dials both Monumental and Technical simultaneously.
- **Declaration Mode A + Declaration Mode B** are alternate modes, not companions. They do not appear together. One or the other, per project or context.
- **Narrator + Narrator Sibling** are skins, not partners. The Sibling replaces the Narrator; it does not accompany it.

---

## Typographic Non-Negotiables

*Rules that hold regardless of medium, context, or project. If these are violated, the typography does not belong to Reality Reprojection.*

### 1. Weight is intentional, never decorative

Every weight change — from Regular to Bold, from Standard to Header — must serve hierarchy or emphasis. The system does not use semibold because it's "in between." It does not use Light because it looks elegant. Each weight has a job. If it doesn't have a job, it doesn't appear.

### 2. Readability is generous

The system errs on the side of *more* readable, not less. Slightly larger body sizes. Slightly more line height. Slightly heavier base weight. This is not a rule about specific numbers — it is an instinct. When in doubt, make it easier to read.

### 3. Spacing communicates structure

Letter-spacing and line-spacing are structural tools, not aesthetic ones. Tracked-out uppercase in the Declaration signals a specific mode (monumental, architectural). Tight leading in the Technical voice signals density and code. These are not stylistic preferences — they are part of the grammar.

### 4. Type does not fight the medium

On a 128×64 OLED, the system may use a single weight of a single voice. On a poster, the Declaration may fill 80% of the surface. The type system adapts to what the medium can support — it does not force all three voices into every context.

### 5. The Declaration must pass the self-sufficiency test

Any typeface cast as the Declaration must work as 1–3 letters on an otherwise empty surface and still carry identity. If it needs surrounding design elements to feel complete, it is not a Declaration — it is a headline face.

### 6. The Narrator must pass the twenty-minute test

Any typeface cast as the Narrator must be comfortable to read for twenty minutes of continuous prose. If the reader notices the typeface, it fails.

### 7. The Technical must pass the ambiguity test

Any typeface cast as the Technical voice must clearly differentiate: 0 vs O, 1 vs l vs I, rn vs m, { vs (, " vs ", and any other commonly confused pairs in code. Failure is not a style issue — it is a functional defect.

---

## How This Connects to Layer 1

| Layer 1 Element | Typographic Expression |
|---|---|
| **Constraints generate clarity** | Three voices, not five. Each voice earns its place by doing a job no other voice can. |
| **Progressive revelation** | The Declaration draws you in. The Narrator carries you. The Whisper rewards closer inspection. Hierarchy *is* progressive revelation. |
| **Craftsmanship as respect** | Generous readability. The twenty-minute test. The Whisper that's still legible, still considered. |
| **Medium as collaborator** | Type adapts to medium constraints — fewer voices on constrained surfaces, full ensemble on expansive ones. |
| **Monumental ↔ Intimate** | Declaration at viewport scale vs. Whisper Narrator at caption scale. The gap between them is the tension. |
| **Utilitarian ↔ Sensorial** | Narrator's functional clarity with humanist warmth. Technical's precision with crafted details. |
| **Technical ↔ Human** | Technical voice (monospace, code) balanced by the Narrator's organic curves and the Declaration's presence. |
| **Confident ↔ Inviting** | Declaration is bold without intimidating. Narrator is inviting without being casual. |
| **Dials system** | Declaration Modes A/B. Narrator/Sibling skins. The same structure, different positions on the spectrum. |

---

## Open Questions for Layer 3

These decisions depend on medium and context. They are noted here as territory that Layer 3 must address:

1. **Specific mixing rules** — Which voice combinations are permitted per medium? Can Declaration + Technical coexist on a data dashboard? What about on an OLED?
2. **Scale systems** — What are the actual size steps per medium? What is the ratio between Declaration and Narrator sizes?
3. **Weight inventories** — Which weights of each voice are available per medium? A poster might use three weights of the Declaration. An OLED might use one weight of the Technical.
4. **Fallback and degradation** — When a medium cannot render the chosen typefaces, what happens? What is the system font fallback chain?
5. **The Sibling selection** — What criteria distinguish the Narrator Sibling from arbitrary font swapping? How much personality drift is too much?
6. **Declaration mode selection** — What contexts trigger Mode A vs. Mode B? Is this always a manual choice, or can the system suggest?

---

## Evolution Log

| Version | Date | Change |
|---------|------|--------|
| 0.1 | 2026-02-07 | System document — relationships, non-negotiables, Layer 1 connections, open questions |

---

*Typography is the first test of whether Layer 1's beliefs can become concrete decisions. Every choice made here should be traceable to a principle established there.*
