# Reality Reprojection — Documentation Architecture

This document explains how the design system documentation is organized, why it's structured this way, and how different sections relate to each other.

---

## Overview: Three Layers + Reference

The documentation follows a three-layer architecture, each building on the previous:

```
Layer 1: Core Identity
  ↓ builds on
Layer 2: Visual Primitives
  ↓ builds on
Layer 3: Implementation (pending)

+ Reference: Patterns, feedback, working notes
```

---

## Layer 1 — Core Identity

**File:** `layer-1-core/01-core-identity.md`
**Version:** 1.2
**Status:** Stable (foundational)

### What It Is

The philosophical foundation. Everything else derives from Layer 1.

It defines:
- **The Manifesto** — What Reality Reprojection *is*
- **Stratum A (Philosophy)** — Five core beliefs about design
- **Stratum B (Character)** — The system's personality and presence
- **Stratum C (Tensions)** — Five productive oppositions that give the language energy
- **The Decision Test** — Five questions to validate design work

### Why It Exists

Without a foundational layer, design systems become recipe books — "use this color, this spacing, this font" without understanding *why*. Layer 1 is the "why." It is the scaffolding that allows AI, tools, and multiple designers to produce coherent work even when they're not sitting in the same room.

### Who Should Read It

**Everyone** — but especially:
- Designers new to the system
- Anyone making design decisions that affect multiple mediums
- People writing code or building tools for the system
- AI agents tasked with generating designs in this language

### What NOT to Find Here

- Specific colors or measurements
- Typography font names
- Spacing scales or grid systems
- Implementation rules for web, embedded, or physical

Those belong in Layer 2.

---

## Layer 2 — Visual Primitives

**Directory:** `layer-2-primitives/`
**Status:** In development (rolling out sequentially)

### What It Is

Concrete, medium-agnostic definitions of the system's visual building blocks. Each primitive translates a belief from Layer 1 into actionable decisions.

### The Five Primitives

| Primitive | File | Status | Purpose |
|-----------|------|--------|---------|
| **Typography** | `01-typography.md` | v0.1 (draft) | Three voices (Declaration, Narrator, Technical) and how they relate |
| **Color** | `02-color.md` | v0.1 (draft) | Palette, semantic colors, signature hue, and the concentric color model |
| **Spacing & Grid** | `03-spacing-grid.md` | v0.1 (draft) | Field system, proportions, and spatial rhythm |
| **Material & Vocabulary** | `04-material-vocabulary.md` | v0.1 (draft) | Grain, texture, surface qualities, and material hierarchy |
| **Motion** | `05-motion.md` | v0.1 (draft) | Animation principles and the Clockwork Collection (easing, durations) |

### How They're Organized

Each Layer 2 document follows a consistent structure:

1. **Preamble** — Why this primitive matters to the system
2. **Core definitions** — The actual substance (voices, colors, spacing rules)
3. **Relationships** — How this primitive connects to others
4. **Layer 1 connections** — How this primitive embodies Layer 1 beliefs
5. **Open questions** — What Layer 3 will need to address
6. **Evolution log** — Version history and changes

### Dependencies

Layer 2 sections build on each other:
- **Typography** is foundational (affects all other primitives)
- **Color** stands alone but is enhanced by understanding Material & Vocabulary
- **Spacing & Grid** works with Typography to establish rhythm
- **Material & Vocabulary** uses Color and Spacing
- **Motion** can be applied to any of the above

### Who Should Read Layer 2

**Designers & implementers:**
- Typography specialist → read `01-typography.md`
- Color decisions → read `02-color.md`
- Layout work → read `03-spacing-grid.md`
- Material/texture work → read `04-material-vocabulary.md`
- Animation/interaction → read `05-motion.md`

**Multi-disciplinary work:**
- Read Typography first (it affects everything)
- Then read the 2-3 primitives relevant to your project
- Refer to Feedback & Patterns for concrete examples

---

## Layer 3 — Implementation (Pending)

**Directory:** `layer-3-implementation/`
**Status:** Not yet written

### What It Will Be

Medium-specific guidance. Where Layer 1 + Layer 2 are universal, Layer 3 will be:
- Web (HTML, CSS, component patterns)
- Embedded (OLED displays, Arduino, constrained environments)
- Physical (print, materials, 3D)
- Extended reality (3D environments, AR/VR)

Each will translate the universal principles into the constraints and affordances of its medium.

### Example Structure (Anticipated)

```
layer-3-implementation/
├── web/
│   ├── component-library.md
│   ├── responsive-behavior.md
│   └── accessibility.md
├── embedded/
│   ├── constrained-displays.md
│   └── offline-behavior.md
├── physical/
│   ├── print-guidelines.md
│   └── material-selection.md
└── 3d/
    └── spatial-principles.md
```

### Open Questions Being Addressed

From Layer 2:
- Which voice combinations are permitted per medium?
- What are actual size steps and scale systems?
- How do systems degrade on constrained hardware?
- What is the font fallback chain?
- When does a variant (e.g., Declaration Mode B) activate?

---

## Reference — Patterns & Feedback

**Directory:** `reference/`

### Feedback & Patterns

**File:** `feedback-and-patterns.md`
**Purpose:** Crystallized decisions from design reviews

This is the "taste document" — what to do, what NOT to do, and why. It contains:
- 15 concrete patterns extracted from recent work
- Real examples of right vs. wrong implementations
- Checklists for common design tasks
- Material hierarchy rules
- Hover interaction patterns
- Polarity (light/dark mode) guidance

**When to read it:**
- You're implementing something concrete
- You're unsure about a specific decision
- You want to understand the "flavor" of the system

### Volo Feedback

**File:** `volo-feedback.md`
**Purpose:** Design review notes that shaped the system

Specific feedback from collaborative reviews that changed how the system evolved. Useful for understanding *why* certain decisions were made.

### Working References

**Directory:** `reference/`
**Files:** `REALITY-REPROJECTION-WORKING-REFERENCE*.md`
**Purpose:** Draft explorations and emerging ideas

These are not "official" yet — they're working documents, experiments, and thoughts-in-progress. Useful for understanding the system's evolution but may be superceded by Layer 3 work.

---

## How to Navigate

### I want to understand the system philosophy
1. Start: `README.md`
2. Then: `layer-1-core/01-core-identity.md`
3. Reference: `STRUCTURE.md` (this document) if confused about organization

### I'm designing something specific
1. Read the relevant Layer 2 primitive(s)
2. Check `reference/feedback-and-patterns.md` for implementation rules
3. Use Layer 1's Decision Test to validate your work

### I'm building a tool or AI system
1. Skim `layer-1-core/01-core-identity.md` for context
2. Read the specific Layer 2 primitives you'll need to implement
3. **Start with `reference/feedback-and-patterns.md`** — it has the concrete rules
4. Refer back to Layer 1 when unsure about intent or edge cases

### I'm extending the system to a new medium
1. Read all of Layer 1 thoroughly
2. Read all of Layer 2 (or at least the relevant sections)
3. Understand the patterns in `reference/feedback-and-patterns.md`
4. Create a new Layer 3 section following the same structure and rigor

---

## Design Principles for the Documentation

The documentation itself follows Reality Reprojection's principles:

1. **Constraints generate clarity**
   - Three-layer structure, not a flat list
   - Each document has one clear purpose
   - No redundancy between layers

2. **Progressive revelation**
   - `README.md` gives you the overview
   - Each layer adds detail only as needed
   - You can read selectively or sequentially

3. **Craftsmanship as respect**
   - Consistent structure across documents
   - Clear navigation and cross-references
   - Version numbers and evolution logs

4. **The medium is a collaborator**
   - Markdown structure allows version control and diffs
   - Cross-linking supports both sequential and random-access reading
   - Separate files enable parallel exploration

5. **Design is alive**
   - Evolution logs in every document
   - Explicit version numbers
   - "Living document" status on all pages

---

## File Naming Conventions

### Layer 1
- Single file, numbered: `01-core-identity.md`

### Layer 2
- Numbered by reading order: `01-typography.md`, `02-color.md`, etc.
- Descriptive names that match content
- Versioned documents kept: `03-spacing-grid-v0.2.md` alongside `03-spacing-grid.md`

### Reference
- Descriptive, clear purpose: `feedback-and-patterns.md`, `volo-feedback.md`
- Working documents may have timestamps or iteration numbers

---

## Adding New Content

### To Layer 1
- Layer 1 is foundational and rarely changes
- Changes should be made only if a core belief is being added or refined
- Update the evolution log and version number
- Notify anyone relying on Layer 1 for their work

### To Layer 2
- New primitives go in `layer-2-primitives/` with a new number
- Follow the consistent structure: preamble, definitions, relationships, Layer 1 connections, open questions, evolution log
- Ensure new primitives don't contradict existing Layer 1 or Layer 2 content
- Note dependencies (which primitives must be read first)

### To Reference
- New feedback goes in `feedback-and-patterns.md` with rationale
- Major design reviews go in new feedback documents (e.g., `name-feedback.md`)
- Working explorations go in `reference/working-references/`

### To Layer 3 (when ready)
- Maintain the three-layer structure
- Each medium gets its own subdirectory
- Follow the same documentation standards as Layer 1 & 2

---

## Version Control & Evolution

Each document has:
- **Version number** (e.g., 1.2, 0.1)
- **Date** of last update
- **Status** (Stable, Living document, In development, Pending)
- **Evolution log** showing all changes

Breaking changes are marked clearly in evolution logs. Non-breaking enhancements may not require major version bumps.

---

## For AI & Code Systems

If building automated tools, parsers, or AI agents that use this documentation:

1. Parse Layer 1 for belief statements
2. Parse Layer 2 section headers to discover components
3. Extract concrete rules from `reference/feedback-and-patterns.md`
4. Use the relationships and dependencies to understand cascading changes
5. When a decision conflicts with multiple sources, preference order:
   - Layer 1 (foundational beliefs)
   - Feedback & Patterns (concrete recent decisions)
   - Layer 2 (general guidance)
   - Working References (experimental, not binding)

---

*This structure enables the design system to be both coherent and flexible, both universal and medium-specific, both foundational and living.*
