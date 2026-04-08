# REALITY REPROJECTION

## Layer 2: Visual Primitives — Color
### The Dimensional Map

**Version:** 0.3
**Date:** 2026-02-10
**Part of:** Color Primitive
**See also:** [Overview](02a-color-overview.md), [Dimensions](02b-color-dimensions.md), [Attributes](02c-color-attributes.md), [Conduct & Rules](02e-color-conduct.md)

---

## What Is the Dimensional Map?

The Dimensional Map is the structural heart of the color system's algorithmic approach. It formalizes which attributes become available at each dimensional depth and how design decisions cascade across depths.

For any given context:
1. Determine the available dimensional depth (what the medium supports)
2. Read across the map to that depth
3. Everything to the right is unavailable
4. The system must be complete and functional using only what's available

---

## The Matrix

| Attribute | **D1 — Value** | **D2 — Temperature** | **D3 — Hue** | **D4 — Saturation** |
|-----------|---|---|---|---|
| **Roles** | Structural roles only (surface, foreground, accent via value contrast) | Structural roles gain tonal identity | Semantic roles emerge (success, warning, critical, informational, categorical). Accent becomes signature hue | All roles gain intensity modulation — urgency within a role |
| **Emphasis** | Full bold→subtle spectrum via value contrast | Emphasis shifts gain warmth/coolness | Hue can reinforce emphasis (signature hue at bold, desaturated at subtle) | Saturation becomes a second emphasis axis — vivid for bold, muted for subtle |
| **States** | Value shifts: hover lightens/darkens, active increases contrast, disabled reduces contrast | State shifts gain tonal consistency | Hue can mark specific states (signature hue for focus ring, critical hue for error state) | Saturation can modulate urgency within states (pressed = more saturated than hovered) |
| **Properties** | Text/ground contrast established. Fill and border distinguished by value. Icon follows text rules | All properties gain temperature. Ground warmth/coolness defines the spatial feel | Fill and border can carry semantic hue. Text remains value-governed but can receive hue for links or semantic labels | Fill saturation distinguishes primary from secondary actions. Ground saturation creates atmospheric depth |

---

## Key Transitions

### D1 → D2: The Subtlest Transition

Nothing new becomes available — everything transforms. The shift is felt rather than seen.

**The practical consequence:** A D2 context uses the same attribute structure as D1, but every value in the system now carries a temperature bias. Design decisions don't change in kind, only in character.

**Example:** In D1, a button is distinguished from the background through value contrast. In D2, that same contrast now has a warm or cool character — the same contrast, but with identity.

### D2 → D3: The Most Significant Threshold

Semantic roles become possible for the first time. This is where the system gains its ability to communicate meaning through color rather than just hierarchy through value. It is also where the risk increases — every hue added is a commitment.

**The practical consequence:** At D3, the design question shifts from "how much contrast?" to "what does this color *mean*?"

**Example:** At D2, error states are distinguished by value (a darker or lighter background). At D3, the error can *become red* — semantic meaning through color.

### D3 → D4: The Refinement Layer

Nothing new becomes categorically available — but everything gains a volume knob. Roles can be expressed urgently or gently. Emphasis gains a second axis. States can signal intensity of engagement.

**The practical consequence:** D4 is where "good color" becomes "considered color" — the difference between a system that uses hue correctly and one that uses it *beautifully*.

**Example:** At D3, a success state is green. At D4, a success can be vivid green (urgent success) or muted green (gentle confirmation).

---

## Reading the Map for a Context

The map reads top-to-bottom as a capability accumulation:

1. **Determine the maximum dimensional depth** the medium supports
   - Monochrome e-ink display? D1 only
   - Color terminal? Probably D1–D3 (or D3 with limited saturation control)
   - Full web interface? D1–D4
   - Smart watch? D1–D3

2. **Read every column up to and including that depth**
   - All attributes listed in that column are available
   - You can use them freely

3. **Everything to the right is unavailable**
   - You cannot use D4 attributes in a D3 context
   - You must find D1–D3 solutions for all color decisions

4. **The system must be complete without the unavailable dimensions**
   - This is the non-negotiable

---

## Examples of Map Reading

### Example 1: Monochrome OLED (D1 Only)

**Available:** Value only
**Unavailable:** Temperature, hue, saturation

- Roles: Structural only (surface, foreground, accent through value contrast)
- Emphasis: Bold/default/subtle via value steps
- States: Resting/hovered/pressed/focused/disabled via value shifts
- Properties: Text and fill contrast established through value

**Design approach:** Build the entire interface using value steps. Ensure that every distinction—structural, emphatic, state-based—reads through light and dark only.

### Example 2: Color Terminal (D1–D3)

**Available:** Value, temperature, hue
**Unavailable:** Saturation control (or very limited)

- Roles: All structural roles + semantic roles (error = red, success = green)
- Emphasis: Value + hue reinforcement
- States: Value shifts + hue marking
- Properties: Full range, but color meaning must be backed by value distinctness

**Design approach:** Use value as the primary distinction, temperature for consistency, hue for semantic meaning. Don't rely on saturation differences.

### Example 3: Full Web Interface (D1–D4)

**Available:** All four dimensions

- Roles: Full structural + semantic + identity accents at variable saturation
- Emphasis: Value + temperature + hue + saturation all working together
- States: Rich expression of interactive states through all dimensions
- Properties: Maximum chromatic freedom while respecting value hierarchy

**Design approach:** Use all four dimensions. Let value establish hierarchy, temperature provide consistency, hue communicate meaning, saturation add refinement.

---

## The Algorithm

For any context, the process is:

1. Assess the dimensional depth available
2. Identify the color roles required (what jobs color needs to do)
3. Map each role to the appropriate emphasis and state
4. Use available dimensions to express each decision
5. Verify: Does this work if you strip away all unavailable dimensions?

If step 5 fails, something is dependent on an outer dimension when it should be independent. Restructure.

---

## Evolution Log

| Version | Date | Change |
|---------|------|--------|
| 0.3 | 2026-02-10 | Dimensional Map matrix — all attributes and their availability at each depth |

---

**See also:**
- [Dimensions](02b-color-dimensions.md) — Understanding what each dimension does
- [Attributes](02c-color-attributes.md) — Understanding what each attribute means
- [Conduct & Rules](02e-color-conduct.md) — How to apply the map consistently
