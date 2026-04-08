# REALITY REPROJECTION

## Layer 2: Visual Primitives — Color
### The Color Attributes

**Version:** 0.3
**Date:** 2026-02-10
**Part of:** Color Primitive
**See also:** [Overview](02a-color-overview.md), [Dimensions](02b-color-dimensions.md), [Dimensional Map](02d-color-dimensional-map.md), [Conduct & Rules](02e-color-conduct.md)

---

## What Are Attributes?

Where dimensions describe what color *is made of*, attributes describe the jobs color performs. They are the system's vocabulary for talking about color decisions: why a color is there (role), how loud it is (emphasis), what condition it's in (state), and what element it's applied to (property).

Attributes and dimensions are not parallel systems — they are perpendicular. Every color decision is an intersection: a role at an emphasis level in a state applied to a property, expressed through whatever dimensions the context supports.

---

## Roles — Why This Color Is Here

*The intention behind a color — the reason it exists in the interface.*

A role is the semantic or structural job a color performs. Every color in the system must be assignable to a role. A color without a role is a color without a job.

### Structural Roles

Operate at every dimensional depth (D1 and beyond):

- **Surface** — The ground. Backgrounds, containers, the spatial field elements sit within.
- **Foreground** — What sits on the surface. Text, icons, elements that carry content.
- **Accent** — The system's identity marker. At D1–D2, this is a value or temperature distinction. At D3+, this becomes the signature hue.

### Semantic Roles

Require Dimension 3 (hue) to function fully but must have D1–D2 fallbacks:

- **Success** — A favorable outcome, completion, confirmation.
- **Warning** — Something needs attention. Not blocking, but not ignorable.
- **Critical** — An error, a destructive action, an urgent problem. The loudest semantic signal.
- **Informational** — Neutral guidance, tips, supplementary context. Present but not urgent.
- **Categorical** — Differentiation without hierarchy. Data series, tags, groups where the distinction matters but no category outranks another.

This list is a foundation, not a ceiling. Specific contexts may require additional roles (a "magic" role for AI-driven features, a "new" role for recent additions). Any added role must have a job that existing roles cannot cover and a non-hue fallback for contexts below D3.

---

## Emphasis — How Loudly This Color Speaks

*The contrast between an element and its surroundings.*

Emphasis is the contrast between an element and its context — how much it pulls attention. It operates on a continuous spectrum, but the system recognizes named positions:

- **Bold** — Maximum contrast. The thing you see first. Primary actions, critical alerts.
- **Default** — The working level. Body text, standard controls, the majority of the interface.
- **Subtle** — Reduced contrast. Secondary information, supporting elements, metadata.

Emphasis is primarily a Dimension 1 phenomenon — expressed through value contrast first. At higher dimensions, temperature, hue, and saturation reinforce it, but value does the structural work.

**Key principle:** If emphasis doesn't read in grayscale, it doesn't work.

---

## States — What Is Happening Right Now

*The interactive condition of an element.*

States describe an element's relationship to the user at a given moment:

- **Resting** — The default. No interaction occurring.
- **Hovered** — The user's attention is on this element but has not committed.
- **Pressed** — Active engagement. The moment of commitment.
- **Focused** — Selected for keyboard or assistive interaction. Must be visually distinct from hover.
- **Disabled** — Unavailable. The element exists but cannot be acted upon.

**The dimensional principle for states:** States are expressed through the lowest available dimension that creates a clear distinction. At D1, states are value shifts. At D2+, temperature reinforces these. At D3+, hue can mark specific states. At D4, saturation modulates urgency within states.

---

## Properties — Where This Color Is Applied

*The type of element receiving the color.*

Properties describe the target of a color decision — the type of element:

- **Text** — The strictest contrast requirements. Must be legible against its surface at all emphasis levels.
- **Fill** — Backgrounds of interactive elements (buttons, badges, chips). More chromatic freedom than text.
- **Ground** — The spatial field. Large areas where subtle value and temperature distinctions create depth.
- **Border** — Delineation. Often at lower contrast than text or fill.
- **Icon** — Follows text contrast rules when accompanying text, slightly more freedom when standalone.

Properties interact with emphasis: a bold-emphasis text color and a bold-emphasis surface color are not the same value — they are the same *intention* expressed through different contrast requirements.

---

## The Attributes Matrix

| Attribute | Examples | Dimension Availability |
|-----------|----------|------------------------|
| **Roles** | Surface, Foreground, Accent (structural); Success, Warning, Critical, Informational, Categorical (semantic) | Structural: All depths; Semantic: D3+ |
| **Emphasis** | Bold, Default, Subtle | All depths (via value-first principle) |
| **States** | Resting, Hovered, Pressed, Focused, Disabled | All depths (lowest dimension that distinguishes) |
| **Properties** | Text, Fill, Ground, Border, Icon | All depths (contrast requirements vary) |

---

## How to Read Attributes with Dimensions

For any given context:
1. Determine the available dimensional depth
2. Identify the role (why the color is there)
3. Choose the emphasis (how loud it is)
4. Express through the state (what's happening)
5. Apply to the property (what element it colors)
6. Use available dimensions to express this decision

Example: "Success state in text at default emphasis on a light ground at D3 = a saturated green hue with strong value contrast."

Example: "Critical state in fill at bold emphasis on a dark ground at D2 (no hue) = maximum value contrast with a warm-tinted surface."

---

## Evolution Log

| Version | Date | Change |
|---------|------|--------|
| 0.3 | 2026-02-10 | Attributes documented — roles, emphasis, states, properties with dimensional relationships |

---

**See also:**
- [Dimensional Map](02d-color-dimensional-map.md) — The matrix showing which attributes become available at each depth
- [Conduct & Rules](02e-color-conduct.md) — How to use attributes consistently
