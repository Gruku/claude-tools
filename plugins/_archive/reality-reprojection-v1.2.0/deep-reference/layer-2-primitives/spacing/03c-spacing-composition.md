# REALITY REPROJECTION

## Layer 2: Visual Primitives — Spacing & Grid
### Fundamental 2: Composition

**Version:** 0.1
**Date:** 2026-02-10
**Part of:** Spacing & Grid Primitive
**See also:** [Overview](03a-spacing-overview.md), [Framing](03b-spacing-framing.md), [System & Rules](03d-spacing-system.md)

---

## Composition

*How elements relate to each other within the frame. The spatial relationships that create hierarchy, grouping, and meaning.*

### The Job

Composition is the arrangement of elements in relation to each other — their positions, their distances, their groupings, and the spatial hierarchy those arrangements create. Where framing establishes the container, composition fills it with intent.

Composition answers: What do you see first? What belongs together? What is separate? What is primary and what is subordinate? These questions are answered through spatial relationships before any other primitive contributes — position and proximity communicate hierarchy even in the absence of typographic weight or color emphasis.

### Position as Hierarchy

Elements communicate their importance through where they are placed. A heading above body text. A primary action at the prominent position in a layout. A logo at the top of a page. These are compositional hierarchies — established by position, reinforced by other primitives.

Position-based hierarchy is the spatial expression of Progressive Revelation. The surface of a composition shows the most important elements in the most prominent positions. Secondary elements occupy subordinate positions. Deeper content — the details available on request — exists at positions that require user action to reach (scrolling, navigating, opening).

The workbench principle governs this: **things are where they are for a reason.** A bolt on the work surface is immediately accessible. A bolt in the labeled drawer requires a deliberate action to reach but is findable because the drawers are organized. The spatial structure communicates both the hierarchy (surface vs. drawer) and the navigability (the labels on the drawers). Nothing is placed arbitrarily. Every position is a statement about importance and access.

### Proximity as Meaning

The distance between elements is a semantic tool. Elements that are close together are perceived as related. Elements that are far apart are perceived as separate. This is not a design convention — it is a perceptual fact (Gestalt proximity), and Reality Reprojection treats it as foundational.

Proximity operates at multiple scales: tight spacing between a label and its input field (these belong together), moderate spacing between form groups (these are related but distinct), generous spacing between page sections (these are separate topics). The consistency of these spatial relationships is what allows the user to read the structure without consciously analyzing it.

Proximity is where composition intersects with typographic voice. The Declaration's territorial whitespace is a proximity statement: *I am separate from what comes next.* The Narrator's line height is a proximity statement: *these lines belong to the same thought.* The Technical voice's dense packing is a proximity statement: *this information is a cohesive unit.* The voices don't just have spatial preferences — they have spatial *meanings* that composition must respect.

### Grouping and Separation

Beyond proximity between individual elements, composition organizes content into groups — clusters of related elements that function as a unit. A card. A toolbar. A form section. A data table. These groups are defined spatially: the internal spacing within a group is tighter than the external spacing around it. The ratio between internal and external spacing is what makes a group read as a group.

Separation — the complement of grouping — is the space that defines boundaries between groups. This can be empty space alone (the system's default instinct), a visible divider (a rule, a border), or a value shift (a change in background tone). The spatial separation is the primary mechanism; visual separators are reinforcements, not replacements. If removing a divider line causes two groups to merge perceptually, the spacing is insufficient — the space should do the work on its own.

### Depth in Composition

Elements can be composed not only in the plane but in depth — layered above or below each other within the same framing context. A dropdown appears above its trigger. A tooltip floats above the content it annotates. A sidebar slides over the main content. These are compositional depth relationships — the relative z-position of elements communicating their relationship and priority.

Compositional depth is distinct from framing depth. Framing depth is about nested containers (a card within a page). Compositional depth is about elements occupying different planes within the same container (a modal above the page content). In practice, both are at work simultaneously — a modal has compositional depth (it floats above) *and* its own framing (it has internal margins and padding).

Depth in composition also carries the access hierarchy: content at the topmost layer demands immediate attention (a dialog, an alert). Content at the resting layer is the default working context. Content below — collapsed panels, closed drawers, content beyond the viewport — exists at depth that requires action to surface. This is the spatial encoding of Progressive Revelation: the layers are always there, and the user decides when to go deeper or bring something forward.

---

## Evolution Log

| Version | Date | Change |
|---------|------|--------|
| 0.1 | 2026-02-10 | Composition documented — position, proximity, grouping, depth |

---

**See also:**
- [Framing](03b-spacing-framing.md) — How content relates to containers
- [System & Rules](03d-spacing-system.md) — Non-negotiables and spatial voices
