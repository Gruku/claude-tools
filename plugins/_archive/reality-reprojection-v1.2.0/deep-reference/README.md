# Reality Reprojection — Design System Documentation

**Version:** 1.2 (Layer 1) + 0.1 (Layer 2)
**Status:** Living document — actively evolving
**Last Updated:** 2026-02-14

---

## What This Is

Reality Reprojection is a design language and protocol. It is not a theme or a palette swap. It is a set of beliefs about how designed things should relate to the people who encounter them, structured enough to guide human designers and AI-generated interfaces equally.

This documentation defines:
- **Layer 1**: The core philosophy and beliefs that underpin all decisions
- **Layer 2**: Visual primitives — the concrete expressions of those beliefs (typography, color, spacing, material, motion)
- **Layer 3**: Implementation maps (CSS token/class mapping to every Layer 2 concept)
- **Reference**: Feedback patterns, working notes, and decision logs

---

## Quick Navigation

### Start Here
- **New to the system?** Read [Layer 1: Core Identity](layer-1-core/01-core-identity.md) first. It explains *why* the system exists and *how* to think about using it.

### Layer 1 — The Foundation
- [Core Identity](layer-1-core/01-core-identity.md) — Philosophy, character, tensions, and decision tests

### Layer 2 — Visual Primitives
Each primitive builds on Layer 1 and defines a concrete piece of the system:
- [Typography](layer-2-primitives/01-typography.md) — The three voices: Declaration, Narrator, Technical
- [Color](layer-2-primitives/02-color.md) — Palette, semantic colors, and the signature hue
- [Spacing & Grid](layer-2-primitives/03-spacing-grid.md) — The spatial field system
- [Material & Vocabulary](layer-2-primitives/04-material-vocabulary.md) — Grain, surfaces, and material hierarchy
- [Motion](layer-2-primitives/05-motion.md) — Animation principles and the Clockwork Collection

### Reference & Patterns
- [Feedback & Patterns](reference/feedback-and-patterns.md) — Crystallized decisions from design reviews. Start here if you're *implementing*.
- [Volo Feedback](reference/volo-feedback.md) — Specific feedback that shaped recent evolutions
- [Working References](reference/) — Draft explorations and evolving thoughts

---

## How to Use This

### If you're designing
1. Read Layer 1 to understand the philosophy
2. Read the Layer 2 primitive most relevant to your work
3. Check Feedback & Patterns for implementation rules
4. Use the Decision Test from Layer 1 to validate your work

### If you're implementing (code, AI, tooling)
1. Skim Layer 1 for context
2. Read the specific Layer 2 primitives you need
3. **Start with Feedback & Patterns** — it has the rules and concrete examples
4. Refer back to Layer 1 when unsure about intent

### If you're extending the system
1. Read all of Layer 1 thoroughly
2. Read the Layer 2 sections that relate to your extension
3. Check if any decisions in Feedback & Patterns affect your work
4. Document your decisions with the same structure and rigor

---

## Architecture

```
documentation/
├── README.md (you are here)
├── STRUCTURE.md (detailed architecture explanation)
│
├── layer-1-core/
│   └── 01-core-identity.md
│       (Philosophy, character, tensions, decision tests)
│
├── layer-2-primitives/
│   ├── 01-typography.md
│   ├── 02-color.md
│   ├── 03-spacing-grid.md
│   ├── 04-material-vocabulary.md
│   └── 05-motion.md
│
├── layer-3-implementation/
│   └── css-implementation-map.md (maps every L2 concept → CSS file/token)
│
└── reference/
    ├── feedback-and-patterns.md (implementation rules)
    ├── volo-feedback.md (design review notes)
    └── working-references/ (drafts & explorations)
```

---

## Key Principles

These are the beliefs that hold the system together:

1. **Constraints generate clarity** — Limitations force intentionality
2. **Progressive revelation over information dumping** — Depth is available on demand
3. **Craftsmanship as respect** — Design communicates care for the user
4. **The medium is a collaborator** — Work with the nature of each medium
5. **Design is alive until it stops changing** — The system evolves

The system also maintains five productive tensions (dials):
- **Monumental ↔ Intimate**
- **Utilitarian ↔ Sensorial**
- **Constrained ↔ Expansive**
- **Technical ↔ Human**
- **Confident ↔ Inviting**

See [Layer 1](layer-1-core/01-core-identity.md) for full context.

---

## Evolution & Versioning

Each section has its own version number and evolution log. Check the document headers for:
- **Version**: Current version (e.g., 1.2)
- **Date**: Last update
- **Status**: Living document / In development / Stable

Changes that affect multiple layers are tracked here:
- Layer 1 v1.2 (2026-02-06): Added AI as medium/collaborator, design as protocol
- Layer 2 v0.1 (2026-02-07+): Visual primitives rolling out in sequence

---

## CSS Implementation Map

Each documentation topic maps to specific CSS files in `css/`:

| Documentation | CSS File(s) | Notes |
|---|---|---|
| **Typography** — Three voices | `foundations/fonts.css` `foundations/typography.css` | Syne 800, DM Sans 600, JetBrains Mono 600 |
| **Color** — Concentric model | `foundations/colors.css` | Signature `#00d3fa`, accents lime `#64fa00` + pink `#fa017b`, ground scale, semantics |
| **Color** — Polarity | `modes/polarity.css` | Light/dark ground inversion, shadow adaptation |
| **Spacing** — Lattice & emitters | `foundations/spacing.css` | 8px base, emitter strengths |
| **Material** — Grain | `materials/grain.css` | 5 variants: fine, coarse, concrete, gradient, edge |
| **Material** — Frost | `materials/frost.css` | 3 levels: light, medium, heavy |
| **Material** — Shadows | `materials/shadows.css` | sm→elevated + glow + inset |
| **Material** — Radii | `materials/radii.css` | 2/3/4/6/8px manufactured |
| **Motion** — Clockwork | `foundations/motion.css` | 4 easings, 3 durations, 3 staggers |
| **Feedback #1** — Buttons | `components/buttons.css` | translateY(-1px), inner highlight |
| **Feedback #2** — Cards | `components/cards.css` | Interactive, tilt, material variants |
| **Feedback #6** — Toggles | `components/toggles.css` | Hourglass-settle thumb, signature active |
| **Feedback #6** — Tags | `components/tags.css` | translateX(2px) hover, semantic variants |
| **Feedback #6** — Tabs | `components/tabs.css` | Signature underline, narrator voice |
| **Survivalist** — Degradation | `modes/survivalist.css` | Continuous 0-100 dial |

**Master import:** `css/system.css` (28 files in cascade order)

**Live previews:**
- `demo/rr-test.html` — Component catalogue (all primitives)
- `demo/preview-landing.html` — Landing page (monumental character)
- `demo/preview-dashboard.html` — Telemetry dashboard (utilitarian character)
- `demo/preview-article.html` — Long-form reading (intimate character)
- `demo/preview-settings.html` — Configuration panel (constrained character)

---

## For AI & Tooling

If you're building tools, agents, or interfaces that use Reality Reprojection:
1. Read Layer 1 section on "AI as a creative medium"
2. Reference the specific Layer 2 primitives you need
3. **Read Feedback & Patterns for concrete implementation rules**
4. Use the Decision Test to validate generated output

The system is designed to be protocol-like — explicit enough that code can implement it, but flexible enough to adapt to new contexts.

---

## Contributing

When making changes to this documentation:
- Amend with intent, not impulse
- Every principle should justify itself by its necessity
- Tag breaking changes clearly in evolution logs
- Ensure changes don't contradict foundational beliefs in Layer 1

---

*This is the calibration manual for the reprojector. Everything that follows builds on what's in Layer 1.*
