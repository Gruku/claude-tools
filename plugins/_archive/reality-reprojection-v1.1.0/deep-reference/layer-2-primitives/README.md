# Layer 2: Visual Primitives

**Version:** 0.1+ (Rolling out sequentially)
**Status:** In development
**Depends on:** Layer 1: Core Identity v1.2

---

## Overview

Layer 2 defines the visual building blocks of Reality Reprojection. Each primitive translates Layer 1's beliefs into concrete, actionable design decisions.

The system is designed so each primitive is independent yet complementary. You can read them sequentially or focus on the primitives relevant to your work.

---

## The Primitives

Each primitive is broken into focused sub-documents for easier navigation and reference.

### [1. Typography](typography/)

**Status:** v0.1 (Draft)
**Documents:** 5 + index

Typography is the most load-bearing element. The system uses **three voices** — Declaration, Narrator, and Technical — each with its own job, character, and expressive range.

- [Overview & Quick Start](typography/01a-typography-overview.md)
- [Declaration Voice](typography/01b-typography-declaration.md)
- [Narrator Voice](typography/01c-typography-narrator.md)
- [Technical Voice](typography/01d-typography-technical.md)
- [System & Relationships](typography/01e-typography-system.md)
- [Typography Index](typography/README.md)

**Key principles:**
- Three voices, not five
- Weight is intentional
- Readability is generous
- The Declaration must pass the self-sufficiency test
- The Narrator must pass the twenty-minute test
- The Technical must pass the ambiguity test

---

### [2. Color](color/)

**Status:** v0.3 (Complete draft)
**Documents:** 5 + index

Color uses a **four-dimensional concentric model**: Value (foundation) → Temperature (identity) → Hue (meaning) → Saturation (emphasis). Each dimension is complete unto itself.

- [Overview & Quick Start](color/02a-color-overview.md)
- [The Four Dimensions](color/02b-color-dimensions.md)
- [Color Attributes](color/02c-color-attributes.md)
- [Dimensional Map](color/02d-color-dimensional-map.md)
- [Conduct, Mischief & Rules](color/02e-color-conduct.md)
- [Color Index](color/README.md)

**Key principles:**
- System must be complete at every dimensional depth
- Value hierarchy independent of hue
- Color never sole carrier of meaning
- Temperature consistent within context
- Less color, more meaning
- Outer dimensions respect inner dimensions

---

### [3. Spacing & Grid](03-spacing-grid.md)

**Status:** v0.1 (Draft)
**Documents:** Currently monolithic (to be split)

*Coming soon:* Breakdown of this document into focused sub-documents covering:
- Overview & spatial philosophy
- Fundamental 1: Framing
- Fundamental 2: Composition
- Grid systems & scales
- System & constraints

---

### [4. Material & Vocabulary](04-material-vocabulary.md)

**Status:** v0.1 (Draft)
**Documents:** Currently monolithic (to be split)

*Coming soon:* Breakdown of this document into focused sub-documents covering:
- Overview & material philosophy
- Grain types & application
- Surface hierarchies
- Texture & depth
- System & patterns

---

### [5. Motion](05-motion.md)

**Status:** v0.1 (Draft)
**Documents:** Currently monolithic (to be split)

*Coming soon:* Breakdown of this document into focused sub-documents covering:
- Overview & motion philosophy
- The Clockwork Collection (easing)
- Duration scales
- Interaction patterns
- System & principles

---

## How to Use Layer 2

### If you're new to the system
1. Read [Layer 1: Core Identity](../layer-1-core/01-core-identity.md) first
2. Read [Typography Overview](typography/01a-typography-overview.md)
3. Read [Color Overview](color/02a-color-overview.md)
4. Then dive into specific primitives as needed

### If you're designing
1. Identify which primitives affect your work
2. Read the overview for each primitive
3. Read the specific sub-documents relevant to your task
4. Check [Feedback & Patterns](../reference/feedback-and-patterns.md) for implementation examples

### If you're implementing
1. Start with [Feedback & Patterns](../reference/feedback-and-patterns.md) — it has concrete rules
2. Reference the specific Layer 2 primitives you need
3. Use the non-negotiables as guardrails
4. Refer back to Layer 1 for intent when unsure

### If you're building tools or systems
1. Parse the primitive structures to understand the system's vocabulary
2. Implement support for each primitive's core concepts
3. The Dimensional Map (in Color) is the algorithm pattern
4. Extend this pattern to other primitives

---

## Primitive Dependencies

The primitives are organized by foundational priority:

```
Layer 1: Core Identity (all primitives depend on this)
  ↓
1. Typography (establishes voice and hierarchy)
  ↓
2. Color (inherits from typography, adds meaning)
  ↓
3. Spacing & Grid (uses typography for rhythm)
  ↓
4. Material & Vocabulary (uses all above)
  ↓
5. Motion (uses all above for timing)
```

However, you can read them in any order. Each stands alone and works independently.

---

## Evolution & Status

Each primitive has:
- **Version number** (e.g., 0.1, 0.3)
- **Status** (Draft, In development, Complete draft)
- **Evolution log** tracking changes

**Current scope:**
- Typography and Color are complete drafts (ready for Layer 3 work)
- Spacing & Grid, Material & Vocabulary, Motion are currently monolithic documents
- These will be split into sub-documents as Layer 3 development progresses

---

## What Layer 3 Will Address

Layer 3 will handle medium-specific implementations:
- **Web** (HTML, CSS, components)
- **Embedded** (OLED, Arduino, constrained displays)
- **Physical** (print, materials, 3D)
- **Extended Reality** (3D, AR/VR, spatial)

Each will translate Layer 1 + Layer 2 into the constraints and affordances of its medium.

---

## Connection to Reference

- **[Feedback & Patterns](../reference/feedback-and-patterns.md)** — Crystallized implementation rules from design reviews
- **[Volo Feedback](../reference/volo-feedback.md)** — Design review notes that shaped the system
- **[Working References](../reference/)** — Draft explorations and emerging ideas

---

## Evolution Log

| Version | Date | Change |
|---------|------|--------|
| 0.1+ | 2026-02-10 | Layer 2 structure finalized. Typography and Color fully split into sub-documents. |

---

**See also:**
- [Documentation Overview](../README.md)
- [Documentation Structure](../STRUCTURE.md) — Explains how all documentation fits together
- [Layer 1: Core Identity](../layer-1-core/01-core-identity.md) — The philosophical foundation
