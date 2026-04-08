# REALITY REPROJECTION

## Layer 2: Visual Primitives — Color
### Overview

**Version:** 0.3
**Date:** 2026-02-10
**Status:** In development — second primitive of Layer 2
**Depends on:** Layer 1: Core Identity v1.2, Layer 2: Typography v0.1

---

## Preamble

Color is typography's equal instrument in Reality Reprojection. Type gives the system its voice. Color gives it atmosphere, signaling, and emotional register. Neither is subordinate — they are tuned to each other, but each carries weight the other cannot.

Some commitments are already made. The typography document established off-white and off-black base tones, value-driven hierarchy independent of hue, a warm default instinct, and the principle that color must never be the sole carrier of meaning. This document inherits those and builds the full structure around them.

This document defines **dimensions** — the fundamental properties of color, ordered by foundational priority — and **attributes** — the semantic tools that describe what color does. Specific palettes are cast into these structures the way typefaces are cast into voices; the structure is durable, the selections are replaceable.

---

## The Concentric Model

Most color systems begin with hue. Reality Reprojection begins with **value** and builds outward through **temperature**, **hue**, and **saturation**. Each dimension wraps around the ones beneath it — modulating them, not just adding to them.

This ordering is a capability stack driven by a core belief: **the system must be complete at every dimensional depth.** A 1-bit display running only value is not degraded — it is the color system at Dimension 1. Each outer dimension enriches without creating dependency. Strip one away and the inner ones remain coherent.

The concentric structure also means each outer dimension reshapes everything beneath it. Temperature shifts every value. Hue interacts with the temperature bias. Saturation modulates how strongly hue reads against the value structure. Where a given context sits on each dimension — and which dimensions are available at all — is governed by the medium, the context, and the tension dials from Layer 1.

---

## The Four Dimensions (Quick Reference)

| Dimension | Layer | Property | Character | Availability |
|-----------|-------|----------|-----------|--------------|
| **D1 — Value** | Foundation | Light and dark | Calibrated, deliberate steps | All contexts |
| **D2 — Temperature** | Identity | Warm or cool | Slightly warm default | Most contexts |
| **D3 — Hue** | Semantic | Actual colors | Earned, restrained, meaningful | Rich contexts |
| **D4 — Saturation** | Emphasis | Intensity | Surgical, vivid for maximum intent | Full-featured contexts |

Each dimension builds on the previous. Each is complete unto itself. Strip away D3 and D4, and the system still functions perfectly in monochrome.

---

## Key Principles

1. **Value provides structure** — The foundation that everything else modulates
2. **Temperature provides identity** — The fingerprint that makes it feel like Reality Reprojection
3. **Hue provides meaning** — Semantic differentiation through color
4. **Saturation provides emphasis** — How loudly each color speaks
5. **Complete at every depth** — The system works at D1 (monochrome), D2 (warm/cool), D3 (full color), and D4 (saturated accents)

---

## How to Use This Primitive

### If you're designing with color
1. Read this [Overview](02a-color-overview.md)
2. Read [Dimensions](02b-color-dimensions.md) to understand each layer
3. Read [Attributes](02c-color-attributes.md) for semantic roles
4. Read [Dimensional Map](02d-color-dimensional-map.md) to see how they work together
5. Check [Conduct & Rules](02e-color-conduct.md) for constraints and Layer 1 connections

### If you're implementing color
1. Skim [Overview](02a-color-overview.md) for context
2. Read [Dimensional Map](02d-color-dimensional-map.md) to understand capability mapping
3. Read [Conduct & Rules](02e-color-conduct.md) for non-negotiables
4. Check Feedback & Patterns (main reference) for concrete implementation examples

### If you're building tools or code
1. The four dimensions are the primary unit of organization
2. Each dimension has specific roles and capabilities
3. The Dimensional Map is the algorithm for determining what's available at each depth
4. Use the matrix to answer: "What can color do in this context?"

---

## Connection to Layer 1

The concentric model embodies Layer 1's **Constraints generate clarity**. The system doesn't use unlimited hue — it uses a structural foundation that supports meaning at every depth.

The dimensional ordering reflects **Progressive revelation** — value reads first, temperature is felt, hue communicates meaning, saturation rewards attention.

The principle that color alone cannot carry meaning connects to **Craftsmanship as respect** — every color is backed by non-color fallbacks.

---

## What's Next

- **[Dimensions](02b-color-dimensions.md)** — Deep dive into each of the four dimensions
- **[Attributes](02c-color-attributes.md)** — The semantic jobs color performs
- **[Dimensional Map](02d-color-dimensional-map.md)** — The matrix showing what becomes available at each depth
- **[Conduct & Rules](02e-color-conduct.md)** — How to use color consistently, non-negotiables, Layer 1 connections

---

## Evolution Log

| Version | Date | Change |
|---------|------|--------|
| 0.1 | 2026-02-10 | Initial draft — concentric dimensional model, four dimensions defined |
| 0.2 | 2026-02-10 | Tightened — reduced repeated language, shortened character sections |
| 0.3 | 2026-02-10 | Complete draft — structure finalized, cross-references established |

---

*Color is the second primitive of Layer 2. Every choice made here should be traceable to Layer 1, and compatible with the typography decisions that preceded it.*
