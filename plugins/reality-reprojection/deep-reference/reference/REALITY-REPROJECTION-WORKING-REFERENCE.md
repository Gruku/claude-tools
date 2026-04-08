# REALITY REPROJECTION — Working Reference

## Part 0: System Architecture

The four-layer structure of Reality Reprojection, clarified through development.

### The Minecraft Analogy

- **Layer 1 — Beliefs.** What the system believes to be true. Philosophy, character, tensions. The bedrock that nothing else contradicts.
- **Layer 2 — Primitives.** What the system is made of. The building blocks — their structures, their rules, their non-negotiables. The block types in the Minecraft analogy.
- **Layer 3 — The World Generator.** How the system generates. The algorithm, the dials, the moods, the casting process, the token architecture, the per-medium rules. L3 could produce a *family* of related design languages that all share L1 beliefs and L2 structures but look different because different seeds were planted. L3 is medium-agnostic and identity-agnostic — it defines the process, not the specific output.
- **Layer 4 — The Seed.** What the system *is*, specifically. This exact seed — these exact fonts, these exact colors, these exact spacing values — tuned and branded as *the* Reality Reprojection. L4 is where Volo's taste becomes the final filter. The last mile where "this could work" becomes "this is *mine*."

**The key distinction:** L3 will inevitably leave room — "pick a signature hue that fulfills these criteria," "cast a Declaration font that passes these tests." Those are instructions that could produce multiple valid answers. L4 is the answer you actually chose, and the rationale for *why this one and not the other valid options.*

**The test:** L3's test is "can someone who has never seen your work follow this algorithm and produce something that *feels* like Reality Reprojection?" L4's test is "does this feel like *the* Reality Reprojection?" — not "does this follow the rules" (that's L3), but "is this *the thing*."

### L2 Primitive List (Revised)

The L2 primitives are:

1. **Typography** (v0.3) — Voice. Three instruments with distinct jobs and ranges.
2. **Color** (v0.3) — Atmosphere and signaling. Four concentric dimensions.
3. **Spacing & Grid** (v0.2) — The field. Spatial substrate and structure.
4. **Motion** (v0.1) — Time. The clockwork that makes the system alive and reactive.
5. **Material Vocabulary** (not yet started) — Surface quality. How things feel optically — translucency, texture, blur, the sense of what things are "made of."

**Signature Elements** has been reclassified out of L2. It is not a primitive — it is an emergent property. The thing that happens when all five primitives are calibrated and working together. You don't *define* it at L2; you *verify* it at L3/L4. It fits the Minecraft analogy: Signature Elements was never a block type (L2). It's the recognizable terrain that tells you "this is *that* world" — which emerges from the world generator (L3) placing the right blocks in the right configuration.

### What Lives Where

| Concern | Layer |
|---|---|
| Beliefs, philosophy, tensions, character | L1 |
| Primitive structures, organizing metaphors, non-negotiables | L2 |
| System algorithm (assess medium → set dials → assign → apply) | L3 |
| Mood presets (specific dial positions for named contexts) | L3 |
| Token architecture and naming conventions | L3 |
| Casting process (methodology for choosing fonts, colors, values) | L3 |
| Per-medium rules and responsive behavior | L3 |
| Cross-primitive integration and choreography | L3 |
| Signature Elements (verification that the system is recognizable) | L3 |
| Specific typeface selections | L4 |
| Specific color values (hex, HSL) | L4 |
| Specific spacing scale values | L4 |
| Specific easing curves and durations | L4 |
| Canonical examples and proof-of-concepts | L4 |

---

## Part 1: Primitive Development Framework

The methodology that emerged across L1 and all L2 primitives. Use this to tackle remaining primitives and L3 work.

### The Sequence

**Step 1 — Gather what already exists.**
Read L1 and all completed L2 primitives for implicit commitments the new primitive must inherit. Previous primitives always contain DNA of future ones (e.g., Typography contained color decisions, Color contained spatial decisions, both contained motion promises). Extract these first — they are constraints, not suggestions.

**Step 2 — Find the organizing metaphor.**
Each primitive needs its own structural metaphor appropriate to its nature. Do not force parallel structures across primitives:
- Typography → **Voices** (parallel instruments with jobs)
- Color → **Dimensions** (concentric capability stack)
- Spacing & Grid → **Field** (spatial substrate with lattice, emitters, interference)
- Motion → **Clockwork** (engineered precision you stop to admire, with a Collection of timepieces)
- Material Vocabulary → *TBD — to be discovered through exploration*

The metaphor is found through open-ended exploration, not prescribed. Ask: "What is this primitive *made of* at the most fundamental level?" and "What analogy captures how it works?"

**Step 3 — Interview for instincts.**
Start from Volo's raw preferences and intuitions before introducing structure. Ask open-ended questions. The goal is raw material that gets distilled into principles. Volo responds better to describing what he likes than what he dislikes. Use analogies to physical objects, spaces, and experiences to draw out spatial and sensory instincts.

**Step 4 — Survey industry standards.**
Look at how existing design systems handle the same primitive (Material Design, Apple HIG, IBM Carbon, Atlassian, Polaris, etc.). Identify what's common infrastructure (likely needed at L3) vs. what's missing (opportunity for RP's unique contribution). This step sharpens what RP believes differently.

**Step 5 — Define the L2/L3 boundary.**
Explicitly separate what belongs in L2 (beliefs, identity, structure, non-negotiables) from L3 (specific values, responsive rules, implementation) and L4 (the specific branded selections). When in doubt: "Is this about what the system *believes*?" → L2. "Is this about how the system *generates*?" → L3. "Is this *the* specific answer?" → L4.

**Step 6 — Draft iteratively.**
Build section by section, conversationally. Review the draft structure (skeleton) before filling content. Each section should be traceable to L1. The document structure follows a consistent pattern:
- Preamble (frames the primitive, establishes relationship to predecessors)
- Cross-primitive trait (the instinct that governs all decisions within this primitive)
- Core content (the organizing metaphor, fully developed)
- Quiet Mischief territory
- Non-Negotiables
- Connection to L1 (table mapping L1 elements to this primitive's expressions)
- Open Questions for L3

### Recurring Patterns

- **The survivalist test** — every primitive must define what happens on the most constrained medium (128×64 OLED, 1-bit display). This is not an edge case; it's a fundamental requirement.
- **Cross-primitive trait** — each primitive has one unifying instinct. Found during exploration, not prescribed:
  - Typography: "Presence over Delicacy"
  - Color: Concentric independence (complete at every dimensional depth)
  - Spacing & Grid: "Space is a Field"
  - Motion: "Motion is Clockwork" (engineered precision you stop to admire)
- **Mischief territory** — every primitive defines where quiet mischief lives and what it is not. Mischief is always functional play — delight and meaning arrive together.
- **Non-negotiables** — rules that hold regardless of medium, context, or project. Violations mean the work doesn't belong to Reality Reprojection.
- **The L1 connection table** — explicit mapping proving every choice traces back to a Layer 1 principle.
- **Casting placeholders** — specific selections (fonts, hex values, spacing scales, easing curves) are documented as empty tables, signaling that the structure is durable and the selections are replaceable. These tables are filled at L4.

### Pitfalls to Avoid

- Going in circles at the conceptual level — set a limit on exploration before drafting.
- Drifting into L3 territory (specific values, responsive rules, implementation details).
- Drifting into L4 territory (specific branded selections that belong in casting).
- Forcing parallel structure across primitives — each finds its own metaphor.
- Overthinking naming before the concept is solid — names can be refined in later versions.

---

## Part 2: Volo's Design Preferences & Instincts

Compiled from all conversations across L1 and L2 development. These are the raw inputs that informed the system's principles.

### Visual Preferences

**Typography**
- Big bold text appearing on top of content (like the game "Control" — huge letters in Bold/Black Avant Garde Gothic)
- Prefers text slightly thicker/bigger than convention — makes reading easier, translates to generous readability as a principle
- Declaration can use both uppercase and lowercase; authority comes from weight and scale, not just caps
- Bold for emphasis, italic for personality/warmth/personal voice
- Fan of Terminal User Interfaces — they look good no matter what
- Calm fonts for reading; the Narrator should disappear into content
- Technical/monospace voice should be the most readable for individual character clarity

**Color**
- Bold, saturated, bright colors — but reserved for "wow" factor or specific accents, not widespread
- Warmer tones for grays (orange-ish tint)
- Blacks aren't pure black — slight tint
- Flat white is acceptable but not pure clinical white
- High-contrast silhouettes
- Color is equal to typography, not subordinate
- Default warm temperature, but context-dependent — cool is valid when dialed toward Technical
- Restraint with hue, not minimalism — context-dependent deployment
- Inspired by: electric violet/purple with fluorescent orange (acid poster aesthetic), deep forest green duotone, amber-orange warm glow

**Spacing & Structure**
- Workbench analogy — things are where they are for a reason
- HUD/Canvas spatial model — HUD fixed to viewer, Canvas is the world beneath
- Viewport as lens revealing structure beneath
- Space should be engineered but allow user inhabitation
- Elements can be pinned to HUD (sticky note on astronaut's helmet) and returned to canvas
- Structure should protect itself from chaos but allow user arrangement
- Hierarchy through position — big text with subordinate below showing relationship
- Proximity as meaning — distance between elements is semantic

**Materials & Surfaces**
- Semi-translucent matte things that blur objects behind them
- Hint of textured backgrounds to ground elements (wireframe texture, concrete)
- Not skeuomorphic — material *quality* not material *imitation*
- Modern Apple materials pushed slightly further in some contexts
- Machined aluminum, sleek physical products (Parker pen, LEGO bricks)

**Motion & Interaction**
- Likes interactive things, playful interactivity, reactivity to user actions
- Animations that make sense and look good — not decorative
- Hates laggy, unintuitive touch controls (especially in cars)
- Likes physical knobs, dials, and the feedback they give
- Diegetic UI in games — exists in the world, or highly stylized and intentional
- Professional background in 3D motion graphics for web — significant source material
- Split-flap displays, mechanical clocks, hourglasses — motion with visible mechanism
- Watches, clockwork — the craft of precision timekeeping as an aesthetic

**General Aesthetic**
- "Retro" appeal comes from limitations that made design intentional, not from nostalgia
- Graphic design of posters, 60s-80s era
- Art Deco influence
- Architecture of past spaces — buildings and the feelings they evoke
- NASA Lunar and Mars missions — imagining designs for those contexts
- Ghibli-inspired painted style for environments
- Things that know what they are and know how to present themselves
- Deliberateness is the core quality — things feel like someone cared
- Excitement from physical items and their high quality manufacturing
- Tiny details and attention to them
- Quirky stuff in small amounts — flavor, not theme

### Dislikes & Rejections

- Clutter — especially strategy/4x game UIs with elements everywhere
- The generic "LLM-generated look" — the entire motivation for this project
- Decorative elements that don't serve a function
- Gratuitous ornamentation or whimsy without purpose
- Laggy, unintuitive interfaces
- UIs that require hard learning even with tutorials
- Pure neutrality without personality
- Pastiche — referencing a style without understanding it

### How Volo Works Best

- Easier to describe what he likes than what he dislikes
- Responds well to analogies (physical objects, spaces, speakers at lecterns)
- Prefers guided exploration with open-ended questions over blank-page starts
- Wants to see draft structures/skeletons before filling content
- Values the interview-then-synthesize approach
- Appreciates when connections to L1 are made explicit
- Catches L2/L3 boundary drift — will call it out
- Needs the "why" for each structural choice, not just the "what"

### Contexts & Inspirations

- Wants the system applicable to: web apps, Arduino/OLED displays, physical products, posters, 3D environments, plugins, AR/spatial computing
- Pinterest board with collected references (not yet shared in detail)
- 3D environment art experience — has foundation he may not have articulated yet
- Railway station project inspired by overgrown late 19th century + Ghibli painted style
- NASA mission design inspiration — things designed for missions, seen by many, meant to inspire
- The game "Control" as a typographic and UI reference
- Blender's interface as a spatial/zone reference
