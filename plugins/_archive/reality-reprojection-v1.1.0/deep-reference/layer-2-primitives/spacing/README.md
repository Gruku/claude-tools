# Spacing & Grid — Layer 2 Primitive

**Version:** 0.1
**Date:** 2026-02-10
**Status:** In development — third primitive of Layer 2
**Depends on:** Layer 1: Core Identity, Layer 2: Typography, Layer 2: Color

---

## Overview

Spacing & Grid gives the system **structure**. It defines two fundamentals:
- **Framing**: How content relates to its container
- **Composition**: How elements relate to each other

Together, these create the spatial identity of the system across every medium — from a poster to an OLED to an AR environment.

---

## Quick Navigation

- [Overview](03a-spacing-overview.md) — Intro to the two fundamentals
- [Framing](03b-spacing-framing.md) — Container relationships (Trim, Safe Area, Margin, Bleed, HUD/Canvas, Depth)
- [Composition](03c-spacing-composition.md) — Element relationships (Position, Proximity, Grouping, Depth)
- [System & Rules](03d-spacing-system.md) — Spatial Voices, Non-Negotiables, Layer 1 connections
- [Survivalist](03e-spacing-survivalist.md) — How spacing survives on constrained displays

---

## The Two Fundamentals

| Fundamental | Focus | Core Concept |
|-------------|-------|-------------|
| **Framing** | Container boundary | Trim → Safe Area → Margin → Bleed |
| **Composition** | Element relationships | Position → Proximity → Grouping → Depth |

---

## Core Principle: Space is Engineered

**Authored with intent.** Every distance, every margin, every gap is a deliberate decision — not a default, not a leftover.

**Inhabited with flexibility.** The structure is precise, but it's built to survive when users zoom, hide elements, customize the layout.

**Active, not absent.** Empty space does a job. If space isn't working, it doesn't belong.

---

## Key Rules (Non-Negotiables)

- Every spatial decision is intentional
- Framing is always present (even minimal)
- Proximity is consistent within a context
- Spatial hierarchy works without color or typography
- Voices' spatial behaviors are respected
- Empty space has a purpose
- The structure survives real-world conditions

---

## Spatial Voices

How each typographic voice inhabits space:

- **Declaration**: Claims territory (generous margins, separate from next element)
- **Narrator**: Shares space rhythmically (comfortable margins, sequential flow)
- **Technical**: Packs efficiently (tight margins, dense but organized)

---

## The Survivalist

On a 128×64 OLED or any constrained display, the spatial system survives through:
- **Element relations** — Hierarchy through position and proportion
- **Lens navigation** — Viewport reveals structure that extends beyond it

Structure is not a luxury of large screens. It persists under constraint.

---

## How to Use This Primitive

### If you're designing layouts
1. Read [Framing](03b-spacing-framing.md)
2. Read [Composition](03c-spacing-composition.md)
3. Respect the spatial voices and non-negotiables

### If you're building responsive systems
1. Read [System & Rules](03d-spacing-system.md) for principles
2. Check [Survivalist](03e-spacing-survivalist.md) for constraints
3. Remember: Framing is always present, composition always intentional

### If you're working with constrained displays
1. Start with [Survivalist](03e-spacing-survivalist.md)
2. Use element relations and lens navigation
3. Ensure minimal framing (even pixel or two of margin)

---

## Connection to Layer 1

- **Constraints generate clarity**: Every spatial decision is intentional
- **Progressive revelation**: Position-based hierarchy, depth layers for access
- **Craftsmanship as respect**: Framing that communicates care
- **Medium as collaborator**: Trim/safe/margin adapt to the medium
- **Monumental ↔ Intimate**: Declaration's territory vs. Technical's density
- **Quiet mischief**: Intentional boundary intrusion (element that breaks the grid because boundaries are otherwise respected)

---

## Connection to Other Primitives

- **Typography**: Voices have spatial behaviors (Declaration's territory, Narrator's rhythm, Technical's density)
- **Color**: Value-based elevation mirrors framing depth
- **Material**: Spacing defines zones; material expresses them
- **Motion**: Movement through spatial structure (HUD/Canvas, depth layers)

---

## Evolution Log

| Version | Date | Change |
|---------|------|--------|
| 0.1 | 2026-02-10 | Complete draft — Framing, Composition, Spatial Voices, Survivalist, Non-Negotiables |

---

**See also:**
- [Layer 2 Primitives Index](../README.md)
- [Feedback & Patterns](../../reference/feedback-and-patterns.md) for implementation guidance
- [Layer 1: Core Identity](../../layer-1-core/01-core-identity.md) for philosophical foundation
