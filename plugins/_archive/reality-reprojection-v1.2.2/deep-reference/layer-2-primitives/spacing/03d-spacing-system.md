# REALITY REPROJECTION

## Layer 2: Visual Primitives — Spacing & Grid
### System, Voices & Rules

**Version:** 0.1
**Date:** 2026-02-10
**Part of:** Spacing & Grid Primitive
**See also:** [Overview](03a-spacing-overview.md), [Framing](03b-spacing-framing.md), [Composition](03c-spacing-composition.md), [Survivalist](03e-spacing-survivalist.md)

---

## Spatial Voices — How Typography Inhabits Space

Each typographic voice carries an inherent spatial personality. These are not spacing *values* (those are Layer 3 decisions) but spatial *behaviors* — the characteristic way each voice relates to its frame and to its neighbors.

**The Declaration** claims territory. It demands generous framing — wide margins between itself and the container edges. It demands generous composition — significant distance between itself and whatever comes next. It is the element on the box face that sits centered with room to breathe on all sides. Its spatial behavior is centripetal: it draws space *toward* itself.

**The Narrator** shares space. Its framing is comfortable but not extravagant — enough margin that reading never feels cramped, never so much that the text feels isolated. Its composition is sequential and flowing — paragraphs at consistent proximity, sections at wider intervals. The Narrator's spatial behavior is *rhythmic*: regular intervals that create a reading cadence the eye can trust.

**The Technical** packs dense. Its framing is tight — a terminal fills its window, a data table uses its available space efficiently. Its composition is grid-aligned — characters in columns, data in rows, alignment as structural logic. The Technical's spatial behavior is *efficient*: maximum information per unit of space, but with enough spatial order that density reads as organization rather than clutter.

These spatial behaviors interact with composition. When Declaration and Narrator appear together, the Declaration's territorial claim creates a clear boundary — you see the Declaration first, then cross a spatial threshold into the Narrator's rhythmic flow. When Narrator and Technical appear together, the shift in spatial density *is* the signal that the voice has changed. The spatial contrast between voices reinforces the typographic contrast.

---

## Quiet Mischief in Spacing

Spatial mischief follows the principle established in Typography and Color: **functional play** — the delight and the meaning arrive together.

In spacing, mischief lives as **intentional boundary intrusion** — an element that crosses a spatial boundary the system normally respects. A pull quote that bleeds into the margin. An image that breaks the column grid. A notification that overlaps a zone it would normally sit beside. These are not misaligned elements — they are deliberate violations that work *because* the boundaries are otherwise consistently respected. The regularity is what gives the exception its meaning.

For spatial mischief to function, the system's spatial structure must be clearly felt. If margins are inconsistent, an element that breaks the margin is just another inconsistency. If the grid is not perceivable, breaking the grid is not a signal. Mischief requires order to play against — the wink only works if the straight face is established first.

---

## Spacing Non-Negotiables

*Rules that hold regardless of medium, context, or project.*

### 1. Every spatial decision is intentional

No default margins. No inherited padding accepted without evaluation. No spacing values that exist because "that's what the framework gave me." Every distance in the system has a reason.

### 2. Framing is always present

Even on the most constrained display, content is framed — not crammed to the edges. The margin may be minimal, but it exists.

### 3. Proximity is consistent within a context

Equal relationships get equal spacing. If two pairs of label-and-value have the same semantic relationship, they have the same spatial proximity.

### 4. Spatial hierarchy must function independently of other primitives

Strip color and reduce type to a single weight. If the hierarchy is not still legible through spatial relationships alone, the composition is broken.

### 5. Voices' spatial behaviors are respected

The Declaration gets its territory. The Narrator gets its rhythm. The Technical gets its density.

### 6. Empty space has purpose

Whitespace is not filler, leftover, or default. If a region of empty space cannot be explained, it does not belong.

### 7. The structure survives inhabitation

The spatial system is built to accommodate the conditions of real use: viewport resizing, content overflow, user customization, assistive technology adjustments.

---

## How This Connects to Layer 1

| Layer 1 Element | Spatial Expression |
|---|---|
| **Constraints generate clarity** | Every spatial decision is intentional. The constraint that nothing is arbitrary forces every distance to become meaningful. |
| **Progressive revelation** | Position-based hierarchy surfaces the most important content first. Depth layers organize content by access level. |
| **Craftsmanship as respect** | Framing that communicates care. Generous margins that say "someone thought about the person reading this." |
| **Medium as collaborator** | Trim and safe area adapt to the physical reality of the medium. |
| **Monumental ↔ Intimate** | Declaration's territorial claim (Monumental) vs. tight precision of Technical spatial density (Intimate). |
| **Utilitarian ↔ Sensorial** | Grid-aligned structure serving function (Utilitarian) with breathing room and rhythm making the tool feel good (Sensorial). |
| **Constrained ↔ Expansive** | A 128×64 OLED showing a fragment through the lens vs. a full multi-zone layout with HUD and layered canvas. |
| **Technical ↔ Human** | Terminal density and column alignment (Technical) vs. generous framing and comfortable reading margins (Human). |
| **Confident ↔ Inviting** | Bold compositional hierarchy — clear primary element, unmistakable spatial structure (Confident) vs. approachable spacing inviting exploration (Inviting). |
| **Quiet mischief** | Intentional boundary intrusion. The element that crosses a spatial line and the crossing *is* the signal. |
| **Dials system** | Framing tightness, compositional density, depth complexity — all respond to dial position. |

---

## Open Questions for Layer 3

1. **Base unit and spacing scale** — The specific increment system and the named scale of spacing values
2. **Grid systems per medium** — Column counts, gutter widths, and structural grids per medium
3. **Responsive deformation rules** — The order of operations when pressure is applied
4. **Voice spacing values** — Specific framing and composition values for each typographic voice
5. **Zone definitions** — The specific spatial zones within a canvas
6. **Depth mechanics** — Rules for layered content
7. **HUD specifications** — What the HUD contains at minimum per medium
8. **Bounded vs. unbounded canvas behaviors** — How the grid differs between bounded and unbounded canvases
9. **Spatial tokens** — Naming conventions for spacing values
10. **Cross-primitive spatial interactions** — How spacing scale relates to typographic scale
11. **AR and spatial computing** — How framing and composition extend to three-dimensional space

---

## Evolution Log

| Version | Date | Change |
|---------|------|--------|
| 0.1 | 2026-02-10 | System documented — spatial voices, quiet mischief, non-negotiables, L1 connections, open questions |

---

**See also:**
- [Survivalist](03e-spacing-survivalist.md) — How spacing survives on constrained displays
- [System README](README.md) — Complete overview
