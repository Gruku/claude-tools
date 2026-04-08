# REALITY REPROJECTION — Working Reference

## Part 1: Primitive Development Framework

The methodology that emerged across L1, L2 Typography, L2 Color, and L2 Spacing & Grid. Use this to tackle remaining primitives and L3 work.

### The Sequence

**Step 1 — Gather what already exists.**
Read L1 and all completed L2 primitives for implicit commitments the new primitive must inherit. Previous primitives always contain DNA of future ones (e.g., Typography contained color decisions, Color contained spatial decisions). Extract these first — they are constraints, not suggestions.

**Step 2 — Find the organizing metaphor.**
Each primitive needs its own structural metaphor appropriate to its nature. Do not force parallel structures across primitives:
- Typography → **Voices** (parallel instruments with jobs)
- Color → **Dimensions** (concentric capability stack)
- Spacing & Grid → **Fundamentals** (Framing + Composition)
- Each future primitive should discover its own

The metaphor is found through open-ended exploration, not prescribed. Ask: "What is this primitive *made of* at the most fundamental level?" and "What analogy captures how it works?"

**Step 3 — Interview for instincts.**
Start from Volo's raw preferences and intuitions before introducing structure. Ask open-ended questions. The goal is raw material that gets distilled into principles. Volo responds better to describing what he likes than what he dislikes. Use analogies to physical objects, spaces, and experiences to draw out spatial and sensory instincts.

**Step 4 — Survey industry standards.**
Look at how existing design systems handle the same primitive (Material Design, Apple HIG, IBM Carbon, Atlassian, Polaris, etc.). Identify what's common infrastructure (likely needed at L3) vs. what's missing (opportunity for RP's unique contribution). This step sharpens what RP believes differently.

**Step 5 — Define the L2/L3 boundary.**
Explicitly separate what belongs in L2 (beliefs, identity, structure, non-negotiables) from L3 (specific values, responsive rules, implementation). When in doubt, ask: "Is this about what the system *believes* or how it *behaves in a specific context*?" Beliefs = L2. Context-specific behavior = L3.

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
- **Cross-primitive trait** — each primitive has one unifying instinct (Typography: "Presence over Delicacy," Color: concentric independence, Spacing: "Space is Engineered"). Found during exploration, not prescribed.
- **Mischief territory** — every primitive defines where quiet mischief lives and what it is not. Mischief is always functional play — delight and meaning arrive together.
- **Non-negotiables** — rules that hold regardless of medium, context, or project. Violations mean the work doesn't belong to Reality Reprojection.
- **The L1 connection table** — explicit mapping proving every choice traces back to a Layer 1 principle.
- **Casting placeholders** — specific selections (fonts, hex values, spacing scales) are documented as empty tables, signaling that the structure is durable and the selections are replaceable.

### Pitfalls to Avoid

- Going in circles at the conceptual level — set a limit on exploration before drafting.
- Drifting into L3 territory (specific values, responsive rules, implementation details).
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
