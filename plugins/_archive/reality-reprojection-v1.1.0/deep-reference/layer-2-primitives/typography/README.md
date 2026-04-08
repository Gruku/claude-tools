# Typography — Layer 2 Primitive

**Version:** 0.1 (Draft)
**Date:** 2026-02-07
**Status:** In development — first primitive of Layer 2
**Depends on:** Layer 1: Core Identity v1.2

---

## Overview

Typography is the most load-bearing element in Reality Reprojection. Before color, before layout, before motion — type is where the identity becomes visible.

The system uses **three voices** — the Declaration, the Narrator, and the Technical — each with its own job, character, and expressive range. This is not five fonts doing five jobs. It is three voices that stretch across multiple scales and contexts.

---

## Quick Navigation

### Start Here
- [Overview](01a-typography-overview.md) — The three voices at a glance

### Individual Voices
- [Declaration](01b-typography-declaration.md) — Headlines, identity, monumental moments
- [Narrator](01c-typography-narrator.md) — Reading, explaining, structure
- [Technical](01d-typography-technical.md) — Code, data, precision

### System & Rules
- [System & Relationships](01e-typography-system.md) — How voices work together, non-negotiables, Layer 1 connections

---

## The Three Voices

| Voice | Job | Character | Range |
|-------|-----|-----------|-------|
| **Declaration** | Headlines, identity, monumental moments | Heavy, present, authoritative, crafted | Display sizes, statement-making |
| **Narrator** | Reading, explaining, interface structure | Calm, humanist, generous readability | Body text, labels, interface |
| **Technical** | Code, data, terminals, precision | Monospace, unambiguous, metric | Small-to-medium, constrained contexts |

---

## Key Principles

1. **Weight is intentional** — Every weight change serves hierarchy or emphasis
2. **Readability is generous** — Slightly larger, slightly heavier, slightly more comfortable
3. **Spacing communicates** — Letter-spacing and line-spacing are structure tools
4. **Type adapts** — Fewer voices on constrained surfaces, full ensemble on expansive ones
5. **Voices are distinct** — Each must be immediately recognizable at a glance

---

## Core Rules (Non-Negotiables)

- **Declaration:** Must pass the self-sufficiency test (1-3 letters, no supporting elements)
- **Narrator:** Must pass the twenty-minute test (comfortable for sustained reading)
- **Technical:** Must pass the ambiguity test (0/O, 1/l/I, rn/m all clearly distinct)

---

## How to Use This Primitive

### If you're designing with typography
1. Read [Overview](01a-typography-overview.md)
2. Read the individual voice documents relevant to your work
3. Check [System & Relationships](01e-typography-system.md) for pairing rules and non-negotiables
4. Use the voice specifications to evaluate typeface candidates

### If you're implementing typography
1. Read all voice documents
2. Read [System & Relationships](01e-typography-system.md) thoroughly
3. Check Feedback & Patterns (main reference) for concrete implementation examples
4. Refer back to individual voices when making casting decisions

### If you're building tools or code
1. Parse the voice definitions to understand the system's vocabulary
2. The three voices are the primary unit of organization
3. Weight, emphasis, and size relationships are Layer 3 concerns
4. Non-negotiables are system-level rules that cannot be violated

---

## Connection to Other Primitives

- **Color:** Inherits the off-white/off-black base established in Typography
- **Spacing & Grid:** Uses typography's voices to establish rhythm and hierarchy
- **Material & Vocabulary:** Texture and grain interact with typographic weight
- **Motion:** Animation easing should match the character of each voice

All primitives work together through the foundational Layer 1 principles.

---

## Evolution Log

| Version | Date | Change |
|---------|------|--------|
| 0.1 | 2026-02-07 | Initial draft — three voices defined, structure established |

---

**See also:**
- [Layer 2 Primitives Index](../README.md)
- [Feedback & Patterns](../../reference/feedback-and-patterns.md) for implementation rules
- [Layer 1: Core Identity](../../layer-1-core/01-core-identity.md) for philosophical foundation
