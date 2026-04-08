# Color — Layer 2 Primitive

**Version:** 0.3
**Date:** 2026-02-10
**Status:** In development — second primitive of Layer 2
**Depends on:** Layer 1: Core Identity v1.2, Layer 2: Typography

---

## Overview

Color is typography's equal instrument in Reality Reprojection. Type gives the system its voice. Color gives it atmosphere, signaling, and emotional register.

The system uses a **four-dimensional concentric model**:
- **D1 — Value** (light and dark) — The foundation
- **D2 — Temperature** (warm and cool) — The identity
- **D3 — Hue** (actual colors) — Semantic meaning
- **D4 — Saturation** (intensity) — Emphasis refinement

Each dimension is complete unto itself. You can build a full, functional interface using only D1. Add D2 for identity. Add D3 for semantic color. Add D4 for refined emphasis. Nothing is dependent on the next layer.

---

## Quick Navigation

### Start Here
- [Overview](02a-color-overview.md) — The concentric model, four dimensions at a glance

### Core Concepts
- [Dimensions](02b-color-dimensions.md) — Deep dive into D1–D4, what each does and why
- [Attributes](02c-color-attributes.md) — Roles, emphasis, states, properties
- [Dimensional Map](02d-color-dimensional-map.md) — The matrix showing what's available at each depth

### System & Rules
- [Conduct & Rules](02e-color-conduct.md) — How to use color consistently, non-negotiables, Layer 1 connections

---

## The Four Dimensions

| Dimension | Layer | What It Does | Character | Availability |
|-----------|-------|--------------|-----------|--------------|
| **D1 — Value** | Foundation | Light and dark | Calibrated, deliberate steps | All contexts |
| **D2 — Temperature** | Identity | Warm or cool tint | Slightly warm default | Most contexts |
| **D3 — Hue** | Semantic | Actual colors | Earned, restrained, meaningful | Rich contexts |
| **D4 — Saturation** | Emphasis | Intensity | Surgical, vivid for maximum intent | Full-featured contexts |

---

## The Color Attributes

| Attribute | Examples | What It Is |
|-----------|----------|-----------|
| **Roles** | Surface, Foreground, Accent (structural); Success, Warning, Critical (semantic) | Why the color is there |
| **Emphasis** | Bold, Default, Subtle | How loudly it speaks |
| **States** | Resting, Hovered, Pressed, Focused, Disabled | What's happening to the element |
| **Properties** | Text, Fill, Ground, Border, Icon | What element receives the color |

---

## Key Principles

1. **Neutrality is the default field** — Most of the interface is neutral (value + temperature), with hue held in reserve
2. **Color is deployed, not applied** — Every color is a structural decision with a job
3. **Complete at every depth** — D1 alone is a fully functional color system, not degraded
4. **Value hierarchy independent** — Strip hue and saturation; if hierarchy doesn't work, something's wrong
5. **Less color, more meaning** — When in doubt, remove a color
6. **Consistency within, variation between** — Strict within a context, flexible between contexts

---

## Core Rules (Non-Negotiables)

- The system must be complete at every dimensional depth
- Value hierarchy must work independently of hue
- Color must never be the sole carrier of meaning (needs fallbacks)
- Temperature must be consistent within a context
- Every hue present must have a job
- Full saturation must be earned (reserved for maximum intent)
- Outer dimensions must respect inner dimensions

---

## How to Use This Primitive

### If you're designing with color
1. Read [Overview](02a-color-overview.md) for context
2. Read [Dimensions](02b-color-dimensions.md) to understand each layer
3. Read [Attributes](02c-color-attributes.md) for semantic roles and meaning
4. Read [Dimensional Map](02d-color-dimensional-map.md) — this is the algorithm
5. Check [Conduct & Rules](02e-color-conduct.md) for constraints

### If you're implementing color
1. Start with [Dimensional Map](02d-color-dimensional-map.md) to understand capability mapping
2. Read [Conduct & Rules](02e-color-conduct.md) for non-negotiables
3. Check Feedback & Patterns (main reference) for implementation examples
4. Refer to [Dimensions](02b-color-dimensions.md) when evaluating color choices

### If you're building tools or code
1. The four dimensions are the primary unit of organization
2. The Dimensional Map is the algorithm for determining what's available at each depth
3. Attributes define the semantic jobs colors perform
4. Use the matrix: "What can color do in this context?" Answer via Dimensional Map

---

## Color Casting (Pending)

This section is intentionally empty. The structure and rules are defined. The actual palette — specific values for hues, saturation levels, value steps — will be documented when colors are selected.

---

## Connection to Other Primitives

- **Typography:** Inherits the off-white/off-black base established in Typography
- **Spacing & Grid:** Value steps establish rhythm and hierarchy alongside spatial rhythm
- **Material & Vocabulary:** Temperature and saturation interact with grain and texture
- **Motion:** Animation timing and easing complement color transitions

All primitives work together through the foundational Layer 1 principles.

---

## Evolution Log

| Version | Date | Change |
|---------|------|--------|
| 0.1 | 2026-02-10 | Initial draft — concentric model, four dimensions |
| 0.2 | 2026-02-10 | Tightened — reduced repetition, streamlined sections |
| 0.3 | 2026-02-10 | Complete — attributes, dimensional map, conduct, rules fully documented |

---

**See also:**
- [Layer 2 Primitives Index](../README.md)
- [Feedback & Patterns](../../reference/feedback-and-patterns.md) for implementation guidance
- [Layer 1: Core Identity](../../layer-1-core/01-core-identity.md) for philosophical foundation
