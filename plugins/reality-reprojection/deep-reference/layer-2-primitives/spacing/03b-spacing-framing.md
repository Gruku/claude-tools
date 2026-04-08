# REALITY REPROJECTION

## Layer 2: Visual Primitives — Spacing & Grid
### Fundamental 1: Framing

**Version:** 0.1
**Date:** 2026-02-10
**Part of:** Spacing & Grid Primitive
**See also:** [Overview](03a-spacing-overview.md), [Composition](03c-spacing-composition.md), [System & Rules](03d-spacing-system.md)

---

## Framing

*How content relates to its container. The relationship between what's inside and the boundaries that hold it.*

### The Job

Framing is the most fundamental spatial act — placing content within a bounded space and managing the relationship between that content and the edges of its container. Before any element relates to another element, it relates to the space it occupies. The margins of a poster. The safe area of a phone screen. The padding within a card. The few pixels of breathing room on a 128×64 OLED. All of these are framing decisions.

Framing is what makes content feel *placed* rather than crammed or lost. Too tight to the edges and the content feels trapped — like text running into the binding of a cheap paperback. Too far from the edges and the content feels adrift — unmoored in a sea of whitespace. Considered framing communicates that someone thought about the person on the other end, which connects directly to Craftsmanship as Respect.

### The Lineage

Print design has the most mature vocabulary for framing, and Reality Reprojection inherits its principles:

**Trim** — the actual boundary of the container. The edge of the screen, the edge of the page, the physical perimeter of the object. The trim is a fact of the medium, not a design choice.

**Safe area** — the zone within the trim where content can reliably exist. On a phone, this accounts for notches, rounded corners, and gesture zones. On a printed piece, this accounts for production tolerances. On a physical object, this accounts for curvature and viewing angle. The safe area is the *usable* boundary.

**Margin** — the breathing room between content and the safe area. This is the active design decision — the space that separates content from the edge and gives the composition its sense of containment. Margins are not uniform across voices: the Declaration demands generous margins (the logo on the box face doesn't crowd the edges), the Narrator needs comfortable margins (reading shouldn't feel cramped against a boundary), and the Technical accepts tighter margins (a terminal fills its window more completely, density is character). But even the Technical has margins — the framing is tighter, not absent.

**Bleed** — content that intentionally extends past the trim, sacrificed at the cut. In digital contexts, this translates to content that extends to or beyond the viewport edge — a full-bleed image, a background color that runs to the edges. Bleed is a deliberate compositional choice: the system *choosing* to break the frame for expressive purposes.

These concepts are medium-agnostic. A 128×64 OLED has a trim (the physical screen edge), a safe area (probably inset by a pixel or two), margins (the breathing room that makes content feel framed rather than clipped), and the potential for bleed (an element that runs to the screen edge). A poster has the same. An AR panel floating in space has the same — its boundaries are defined by the panel's own geometry rather than a physical screen, but the framing relationship is identical.

### The HUD and the Canvas

Within Framing, two distinct spatial behaviors emerge based on *what the content is framed against*:

**The HUD** — content framed against the viewport itself. Fixed, persistent, traveling with the viewer regardless of what lies beneath. Navigation, status indicators, identity marks, system controls. The HUD belongs to the *viewer*, not to the content. Its minimum form is the essential controls that a medium requires — the window management icons of an operating system, the back button on a mobile device. The HUD can be expanded (a persistent toolbar, a status bar) or reduced (fullscreen video, a poster with no navigational need), but its resting state is minimal.

The HUD can accept promoted content — a pinned element, a persistent reference, a sticky note on the astronaut's helmet. Content migrates from canvas to HUD and back. This migration is an explicit spatial action: the user (or the system) is saying "this needs to travel with me."

**The Canvas** — the territory that content inhabits, revealed through the viewport. The canvas can be **bounded** (a magazine spread, a blueprint, a dashboard that fits its viewport — complete, nothing hidden) or **unbounded** (a scrolling feed, a long document, an AR environment — extending beyond what the viewport reveals). Whether bounded or unbounded is a type set by the design and the nature of the content, not a responsive behavior.

The canvas is the world beneath the lens. The viewport reveals a portion of it. On a poster, the viewport and canvas are identical — the lens shows everything. On a phone displaying a long article, the viewport is a small frame moving across a tall canvas. On an AR headset, the viewport is the user's field of view and the canvas is the spatial environment around them.

The relationship between viewport and canvas is the lens metaphor: the structure exists whether the viewport is showing it or not. The grid is there. The hierarchy is there. The user navigates through it, and the framing ensures that whatever portion is visible feels composed — not arbitrarily cropped.

### Depth in Framing

Framing has a depth axis. Content can be framed at different levels within the same viewport — a card framed within a page, a modal framed above the page, a dropdown framed above a toolbar. Each layer establishes its own framing relationship: the modal has its own margins, its own safe area, its own spatial logic. Depth in framing is the stacking of containers, each with considered boundaries.

This connects to Color's value-based elevation: the value steps that separate surfaces from backgrounds are the color expression of framing depth. A card that sits at a different value than its surrounding surface is simultaneously a color decision (value separation) and a spatial decision (framed at a different depth).

---

## Evolution Log

| Version | Date | Change |
|---------|------|--------|
| 0.1 | 2026-02-10 | Framing documented — job, lineage (trim/safe/margin/bleed), HUD/Canvas, depth |

---

**See also:**
- [Composition](03c-spacing-composition.md) — How elements relate within the frame
- [System & Rules](03d-spacing-system.md) — Non-negotiables and L1 connections
