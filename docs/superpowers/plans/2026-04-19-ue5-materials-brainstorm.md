# UE5 Materials Brainstorm Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Insert `superpowers:brainstorming` as an interactive gate at the front of new-shader flows in `ue5-materials:author`, and update generator guidance to eliminate UE5-crashing Comment nodes, use Named Reroutes aggressively, and apply a fixed-column positioning convention.

**Architecture:** All changes are prompt-file and skill-markdown edits — no Python, no new skills. The `author` skill gains a Phase 0a that invokes `superpowers:brainstorming` via the `Skill` tool with two in-context overrides (spec location, terminal handoff). The resulting `material_brief.md` feeds the HLSL Architect as authoritative design context. Generator guidance changes eliminate Comment-node emission and formalize layout + Named Reroute use.

**Tech Stack:** Markdown, YAML, Bash, Python 3 (for verification only).

**Spec:** `docs/superpowers/specs/2026-04-19-ue5-materials-brainstorm-design.md` (gitignored, local).

**Scope note:** The spec lists `plugins/ue5-materials/node_registry.yaml` as a file to change. Verified during planning: that file has no `Comment` entry (Comment support lives in `ue5_material_generator.py` as a dormant Python class). The prompt-template change in Task 2 prevents the Generator agent from ever emitting a Comment node, which makes the Python class dormant. No YAML change required.

---

### Task 1: Mark Comment node type as DO NOT USE in node-types.md

**Files:**
- Modify: `plugins/ue5-materials/skills/author/node-types.md:337-338`

- [ ] **Step 1: Read the current Comment section**

Run: `sed -n '337,362p' plugins/ue5-materials/skills/author/node-types.md`

Expected output starts with:
```
### MaterialExpressionComment
Comment box for organization.
```

- [ ] **Step 2: Replace the section header and description with a DO NOT USE banner**

Edit `plugins/ue5-materials/skills/author/node-types.md` — find:

```
### MaterialExpressionComment
Comment box for organization.
```

Replace with:

```
### MaterialExpressionComment — DO NOT USE

> **⚠ Crashes UE5.** Emitting a `Comment` node in a material graph triggers `UMaterialGraphNode_Comment::ResizeNode()` on mouse move (`EXCEPTION_ACCESS_VIOLATION writing address 0x00000000000000c8`). Do NOT include `Comment` nodes in generated YAML. Use Named Reroutes and the positioning convention (see `node-generator-prompt.md`) for visual grouping instead.
>
> The reference below is kept for historical context only. The `node-generator-prompt.md` template does not emit these, and the Generator agent must not add them.

Comment box for organization.
```

- [ ] **Step 3: Verify the banner is present**

Run: `grep -n "DO NOT USE" plugins/ue5-materials/skills/author/node-types.md`

Expected: one match on the `### MaterialExpressionComment — DO NOT USE` line.

Run: `grep -c "UMaterialGraphNode_Comment::ResizeNode" plugins/ue5-materials/skills/author/node-types.md`

Expected: `1`

- [ ] **Step 4: Confirm node comment bubbles section is unchanged**

Run: `grep -n "^## Node Comment Bubbles" plugins/ue5-materials/skills/author/node-types.md`

Expected: one match. Node Comment Bubbles (the `Desc=`/`NodeComment=` attached to any node) are a different, safe feature and must remain documented.

- [ ] **Step 5: Commit**

```bash
git add plugins/ue5-materials/skills/author/node-types.md
git commit -m "docs(ue5-materials): mark Comment node as DO NOT USE (UE5 crash)"
```

---

### Task 2: Update node-generator-prompt.md — remove Comment Boxes, add Named Reroute Strategy, add Positioning Convention, add red-flag

**Files:**
- Modify: `plugins/ue5-materials/skills/author/node-generator-prompt.md`

- [ ] **Step 1: Remove the "COMMENT BOXES" block from the YAML template**

Edit `plugins/ue5-materials/skills/author/node-generator-prompt.md` — find this exact block (lines 111–131 in current file):

```
  # --- COMMENT BOXES ---
  # Comments auto-position around their contained nodes.
  # ALWAYS specify `contains` with the list of node names this comment should wrap.
  # Do NOT specify size_x/size_y — the generator computes these automatically.
  - name: Comment_Inputs
    type: Comment
    text: "Shader Inputs"
    contains: [In1_CompX, In1_CompY, In1_CompZ, In1_CompW, In1_PackName, UV, Time]
    color: [0.15, 0.15, 0.15]

  - name: Comment_CustomNode
    type: Comment
    text: "ShaderName Custom Node"
    contains: [NodeName]
    color: [0.15, 0.15, 0.15]

  - name: Comment_Outputs
    type: Comment
    text: "Outputs"
    contains: [Out_OutputVarName, Out_SomeOther]
    color: [0.15, 0.15, 0.15]

```

Replace with:

```
  # --- NO COMMENT BOXES ---
  # Do NOT emit `Comment` / `MaterialExpressionComment` nodes.
  # UE5 crashes in `UMaterialGraphNode_Comment::ResizeNode()` on mouse move.
  # Use Named Reroutes (strategy below) and the Positioning Convention (below)
  # for visual grouping instead.

```

- [ ] **Step 2: Update Step 1 "Read the Design" bullet about comment groups**

In the same file, find:

```
- What comment groups to create and which nodes each contains
```

Replace with:

```
- Which values deserve Named Reroutes (see Named Reroute Strategy below)
```

- [ ] **Step 3: Update the YAML template's input-pack section to show Named Reroute Declarations**

In the same file, find the existing `# --- FLOAT4 PACKING ---` / `# --- STANDALONE INPUTS` blocks and insert a new `# --- INPUT NAMED REROUTES ---` section right after FLOAT4 PACKING. Find this block:

```
  # --- FLOAT4 PACKING ---
  - name: In1_PackName
    type: MakeFloat4
    desc: "In1_PackName : float4 (CompX, CompY, CompZ, CompW)"

  # --- STANDALONE INPUTS (source nodes created) ---
```

Replace with:

```
  # --- FLOAT4 PACKING ---
  - name: In1_PackName_Raw
    type: MakeFloat4
    desc: "In1_PackName : float4 (CompX, CompY, CompZ, CompW)"

  # --- INPUT NAMED REROUTES ---
  # Every input pack gets a NamedRerouteDeclaration at the graph's left edge.
  # The Custom node reads from a NamedRerouteUsage co-located with it (handled
  # by the connection topology — declarations flow into usages via the graph).
  - name: In1_PackName
    type: NamedRerouteDeclaration
    var_name: "In1_PackName"
    color: [0.3, 0.5, 0.8]

  # --- STANDALONE INPUTS (source nodes created) ---
```

- [ ] **Step 4: Update the connections section to wire raw pack → Named Reroute Declaration**

In the same file, find:

```
connections:
  # Constants to MakeFloat4
  - In1_CompX -> In1_PackName.X
  - In1_CompY -> In1_PackName.Y
  - In1_CompZ -> In1_PackName.Z
  - In1_CompW -> In1_PackName.A

  # Inputs to Custom node — ONLY for nodes we created
  - In1_PackName -> NodeName.In1_PackName
```

Replace with:

```
connections:
  # Constants to MakeFloat4 (raw pack)
  - In1_CompX -> In1_PackName_Raw.X
  - In1_CompY -> In1_PackName_Raw.Y
  - In1_CompZ -> In1_PackName_Raw.Z
  - In1_CompW -> In1_PackName_Raw.A

  # Raw pack → Named Reroute Declaration
  - In1_PackName_Raw -> In1_PackName

  # Inputs to Custom node — ONLY for nodes we created
  # (the declaration name is also the reroute variable — Custom node input resolves to it)
  - In1_PackName -> NodeName.In1_PackName
```

- [ ] **Step 5: Insert the Named Reroute Strategy subsection**

In the same file, find the line `### Step 3: Embed HLSL Code` and insert this block immediately before it (after the closing ``` of the YAML template block):

```
### Named Reroute Strategy

Named Reroute Declarations (`NamedRerouteDeclaration`) are the preferred way to label and anchor values in the graph. They replace Comment boxes for visual grouping.

**Emit a Named Reroute Declaration for:**
- **Every input pack** — the Float4 result of `MakeFloat4` goes through a declaration named after the pack (`In1_PackName`, `In_UV`, `In_Time`, etc.). The raw `MakeFloat4` node is suffixed `_Raw` and never consumed directly.
- **Every output** — already the existing pattern (`Out_OutputVarName`). Keep this.
- **Intermediate values consumed in 2+ places** — if the shader design lists a value as used multiple times downstream, promote it to a declaration. Single-use intermediates stay as direct wires.

**Do NOT emit a declaration for:**
- **External reroute inputs** — user already has these in their graph. Leave the Custom node pin unconnected as before.
- **Single-use intermediates** — wire them directly, keep the graph simple.

### Node Positioning Convention

Use a fixed column-based layout. Tall graphs stay in single columns — no dynamic flow.

| Column | X | Contents |
|--------|---|----------|
| 0 | 0 | Input `NamedRerouteDeclaration` nodes |
| 1 | 400 | Input source nodes (Constants, `TextureCoordinate`, `Time`, `MakeFloat4` raw packs) |
| 2 | 800 | Packing / intermediate nodes |
| 3 | 1200 | Custom HLSL node (centerpiece) |
| 4 | 1600 | Output `NamedRerouteDeclaration` nodes |

**Vertical rule:** each column stacks top-to-bottom, 200px per row, no overlaps. Related values (e.g. RGBA components of one pack) sit contiguously. Set `position_start: [0, 0]` and let column X values drive horizontal placement; each node's Y increments by 200 within its column.

When emitting node positions in YAML, set each node's `x` explicitly to the column value above and `y` to the next free 200px slot in that column.

```

- [ ] **Step 6: Add a red-flag at the end of the file**

In the same file, find the final `## What This Agent Does NOT Do` section and append this subsection right before it:

```
## Red Flags

| Thought | Reality |
|---------|---------|
| "A Comment box would make this cleaner" | **NEVER** emit `Comment` nodes. UE5 crashes on `UMaterialGraphNode_Comment::ResizeNode()`. Use Named Reroutes + positioning. |
| "Single-use intermediate deserves a reroute for clarity" | Single-use stays as direct wire. Reroutes are for 2+ consumers or pack/output boundaries. |
| "I'll let nodes stack anywhere" | Use the 5-column convention. 200px rows, no overlaps. |

```

- [ ] **Step 7: Verify all changes are present**

Run each of these and confirm the expected counts:

```bash
grep -c "NO COMMENT BOXES" plugins/ue5-materials/skills/author/node-generator-prompt.md
```
Expected: `1`

```bash
grep -c "type: Comment" plugins/ue5-materials/skills/author/node-generator-prompt.md
```
Expected: `0`

```bash
grep -c "Named Reroute Strategy" plugins/ue5-materials/skills/author/node-generator-prompt.md
```
Expected: `1`

```bash
grep -c "Node Positioning Convention" plugins/ue5-materials/skills/author/node-generator-prompt.md
```
Expected: `1`

```bash
grep -c "UMaterialGraphNode_Comment::ResizeNode" plugins/ue5-materials/skills/author/node-generator-prompt.md
```
Expected: `2` (one in template comment, one in Red Flags table)

- [ ] **Step 8: Commit**

```bash
git add plugins/ue5-materials/skills/author/node-generator-prompt.md
git commit -m "feat(ue5-materials): replace Comment boxes with Named Reroutes + column layout"
```

---

### Task 3: Update hlsl-architect-prompt.md — material_brief input + intermediate flagging

**Files:**
- Modify: `plugins/ue5-materials/skills/author/hlsl-architect-prompt.md`

- [ ] **Step 1: Add material_brief to the prompt template's input section**

Edit `plugins/ue5-materials/skills/author/hlsl-architect-prompt.md` — find:

```
## Request

[USER'S PLAIN TEXT DESCRIPTION]

## Existing Code (only if edit_existing: true)
```

Replace with:

```
## Request

[USER'S PLAIN TEXT DESCRIPTION]

## Material Brief (only if Entry Point A — new shader from description)

material_brief: [path to material_brief.md, or "none"]

If a `material_brief` path is provided:
- Read that file FIRST, BEFORE interpreting the user's plain-text description.
- Treat the brief as the **authoritative design intent** — it was produced by interactive brainstorming with the user and reflects their confirmed decisions on look, motion, inputs, scope, and target use.
- Use the raw user description only to resolve ambiguities not covered by the brief.
- If the brief and the raw description contradict, the brief wins.

## Existing Code (only if edit_existing: true)
```

- [ ] **Step 2: Add intermediate-flagging instruction to Step 1: Design**

In the same file, find:

```
### Step 1: Design the Shader Architecture

Think through:
- What does the shader need to compute?
- What inputs are needed? Group into Float4s by logical category
- How many Custom HLSL nodes? (prefer fewer, more capable nodes)
- What outputs? (as Named Reroutes for clean graph readability)
- Which outputs are raw SDF values? (these get `MF_UI_SDF_AntiAliasedStep` in the graph)
- Any animation behavior? (time-triggered enter/exit)
```

Replace with:

```
### Step 1: Design the Shader Architecture

Think through:
- What does the shader need to compute?
- What inputs are needed? Group into Float4s by logical category
- How many Custom HLSL nodes? (prefer fewer, more capable nodes)
- What outputs? (as Named Reroutes for clean graph readability)
- Which outputs are raw SDF values? (these get `MF_UI_SDF_AntiAliasedStep` in the graph)
- Any animation behavior? (time-triggered enter/exit)
- **Which intermediate values are consumed in 2+ downstream places?** — list these explicitly in `shader_design.md` under `intermediate_reroutes`. The Node Generator will promote them to Named Reroute Declarations. Single-use intermediates do NOT need this treatment.
```

- [ ] **Step 3: Add intermediate_reroutes to the shader_design.md template**

In the same file, find:

```
custom_nodes:
  - name: "NodeName"
    description: "What this node computes"
    output_type: CMOT_Float4  # CMOT_Float1, CMOT_Float2, CMOT_Float3, CMOT_Float4
    inputs:
      - In1_PackName
      - UV
      - Time
    additional_outputs:
      - name: OutputName
        type: CMOT_Float1
    code_file: shader_code.hlsl

outputs:
```

Replace with:

```
custom_nodes:
  - name: "NodeName"
    description: "What this node computes"
    output_type: CMOT_Float4  # CMOT_Float1, CMOT_Float2, CMOT_Float3, CMOT_Float4
    inputs:
      - In1_PackName
      - UV
      - Time
    additional_outputs:
      - name: OutputName
        type: CMOT_Float1
    code_file: shader_code.hlsl

# Intermediate values consumed in 2+ downstream places — promoted to Named Reroutes
# by the Node Generator. Omit or leave empty when all intermediates are single-use.
intermediate_reroutes: []
  # Example:
  # - name: "ShapeMask"
  #   source: "NodeName.ShapeMask"
  #   type: float
  #   description: "Used by body fill and border AA"

outputs:
```

- [ ] **Step 4: Verify all changes are present**

```bash
grep -c "material_brief:" plugins/ue5-materials/skills/author/hlsl-architect-prompt.md
```
Expected: `1`

```bash
grep -c "intermediate_reroutes" plugins/ue5-materials/skills/author/hlsl-architect-prompt.md
```
Expected: `2` (one in Step 1 prose, one in the YAML template)

```bash
grep -c "authoritative design intent" plugins/ue5-materials/skills/author/hlsl-architect-prompt.md
```
Expected: `1`

- [ ] **Step 5: Commit**

```bash
git add plugins/ue5-materials/skills/author/hlsl-architect-prompt.md
git commit -m "feat(ue5-materials): wire material_brief and intermediate_reroutes into Architect"
```

---

### Task 4: Add Phase 0a (Brainstorm Idea) to author/SKILL.md

**Files:**
- Modify: `plugins/ue5-materials/skills/author/SKILL.md`

- [ ] **Step 1: Update the "How It Works" ASCII diagram**

Edit `plugins/ue5-materials/skills/author/SKILL.md` — find:

```
## How It Works

```
You describe a shader in plain text
    |
[HLSL Architect Agent - Opus]    <- Creative design + HLSL code
    | shader_design.md + shader_code.hlsl
[Node Generator Agent - Sonnet]  <- YAML creation + Python converter
    | ue5_nodes.yaml + ue5_clipboard.txt
Report back to you
    |
You paste full graph into UE5 Material Editor (Ctrl+V)
    |
    +-- "Add a new output"       -> Full chain: Architect -> Generator (topology change)
    +-- "Make the edge softer"   -> HLSL-only: Architect updates shader_code.hlsl
                                    You paste just the code into Custom node
```
```

Replace with:

```
## How It Works

```
You describe a shader in plain text
    |
[Brainstorm — superpowers:brainstorming]   <- Interactive idea gate (Entry Point A only)
    | material_brief.md
[HLSL Architect Agent - Opus]    <- Creative design + HLSL code (reads brief first)
    | shader_design.md + shader_code.hlsl
[Node Generator Agent - Sonnet]  <- YAML creation + Python converter
    | ue5_nodes.yaml + ue5_clipboard.txt
Report back to you
    |
You paste full graph into UE5 Material Editor (Ctrl+V)
    |
    +-- "Add a new output"       -> Full chain: Architect -> Generator (topology change, NO re-brainstorm)
    +-- "Make the edge softer"   -> HLSL-only: Architect updates shader_code.hlsl
                                    You paste just the code into Custom node
```
```

- [ ] **Step 2: Insert Phase 0a section between Entry Points and Phase 0**

In the same file, find the first line of Phase 0 (Gather Context):

```
### Phase 0: Gather Context
```

Insert this entire block immediately BEFORE that line:

```
### Phase 0a: Brainstorm Idea (Entry Point A only)

For Entry Point A — **and only Entry Point A** — run an interactive brainstorm with the user BEFORE dispatching any silent agent. Entry Points B, C, D, the direct-YAML path, and all Phase 4 iterations skip this step.

**Steps:**

1. **Determine the material name.** Extract from the user's description or propose one (`M_<Purpose>` or `M_<Purpose>_VFX`). Confirm with the user if ambiguous.

2. **Check for brief collision.** If `<cwd>/ue5-materials/<material-name>/material_brief.md` already exists:
   - If the user's intent is iteration on an existing material, route to Phase 4 — do NOT re-brainstorm, do NOT overwrite the brief.
   - If the user intends a NEW material with the same name, ask: *"`<material-name>` already has a brief at `<path>`. Rename the new material or overwrite?"* Wait for confirmation. Never silently overwrite.

3. **Create the working directory** `<cwd>/ue5-materials/<material-name>/` if it doesn't exist.

4. **Invoke `superpowers:brainstorming` via the `Skill` tool** with two in-context directives:
   - **Spec location override:** *"Save the design doc to `<absolute-path-to-working-dir>/material_brief.md`. Do not use the default `docs/superpowers/specs/…` path."*
   - **Terminal handoff override:** *"When the user approves the design, do NOT invoke `superpowers:writing-plans`. Return control to the `ue5-materials:author` skill — the HLSL Architect is the next step, not a general implementation plan."*

5. **Wait for brainstorming to complete** and the user to approve the brief.

6. **Fallback — if the brief landed at the default path** (`docs/superpowers/specs/YYYY-MM-DD-<name>-design.md`) despite the override, move it to `<working-dir>/material_brief.md` before proceeding.

7. **User abandons mid-brainstorm** ("nevermind, just do it"): save whatever has been captured to `material_brief.md` with a one-line disclaimer at the top: *"User declined further brainstorming — proceeding with minimal brief."* Then proceed.

8. **Hand off to Phase 0** (gather external reroutes / existing HLSL context) with the brief path available for Phase 1.

```

- [ ] **Step 3: Add material_brief.md to the Output Files table**

In the same file, find the "Output Files (created in working directory)" table:

```
### Output Files (created in working directory)
| File | Purpose | When to paste |
|------|---------|---------------|
| `shader_design.md` | Design spec -- inputs, outputs, topology | Not pasted -- reference only |
| `shader_code.hlsl` | HLSL source code (standalone) | **HLSL-only updates:** paste into Custom node code field |
| `ue5_nodes.yaml` | YAML node definition (editable, re-runnable) | Not pasted -- intermediate format |
| `ue5_clipboard.txt` | Full graph in UE5 clipboard format | **First-time / topology changes:** Ctrl+V in Material Editor |
```

Replace with:

```
### Output Files (created in working directory)
| File | Purpose | When to paste |
|------|---------|---------------|
| `material_brief.md` | Design brief from Phase 0a brainstorm (Entry Point A only) | Not pasted -- feeds HLSL Architect as authoritative design intent |
| `shader_design.md` | Design spec -- inputs, outputs, topology | Not pasted -- reference only |
| `shader_code.hlsl` | HLSL source code (standalone) | **HLSL-only updates:** paste into Custom node code field |
| `ue5_nodes.yaml` | YAML node definition (editable, re-runnable) | Not pasted -- intermediate format |
| `ue5_clipboard.txt` | Full graph in UE5 clipboard format | **First-time / topology changes:** Ctrl+V in Material Editor |
```

- [ ] **Step 3.5: Extend the "Choosing a Path" guidance to flag idea-shaped direct-YAML requests**

Find the "Choosing a Path" section near the top of the same file:

```
## Choosing a Path

Identify the scenario before starting:

- **Direct YAML path** — user already knows the nodes ("wire a TextureCoordinate into a Lerp", "add a Multiply by 2"). Skip agents. Write YAML directly, run `apply_material.py`.
- **Agent chain** — user describes a visual effect, asks for HLSL changes, or pastes HLSL. Dispatch Architect → Generator.

If in doubt, use the agent chain — a minute of extra time is cheaper than a broken graph.
```

Replace with:

```
## Choosing a Path

Identify the scenario before starting:

- **Direct YAML path** — user already knows the nodes ("wire a TextureCoordinate into a Lerp", "add a Multiply by 2"). Skip agents. Write YAML directly, run `apply_material.py`.
- **Agent chain** — user describes a visual effect, asks for HLSL changes, or pastes HLSL. Dispatch Architect → Generator.

If in doubt, use the agent chain — a minute of extra time is cheaper than a broken graph. In particular, when the user's phrasing sounds like an **idea** ("I want…", "make a…", "build a…") rather than a **wiring instruction** ("connect X to Y", "add a Multiply"), treat it as Entry Point A — which now means Phase 0a brainstorm before the Architect.
```

- [ ] **Step 4: Add a Red Flags row about skipping brainstorm**

In the same file, find the existing Red Flags table:

```
## Red Flags

| Thought | Reality |
|---------|---------|
| "I'll just write the HLSL inline" | Dispatch the Architect agent -- it reads the conventions |
| "I'll generate YAML in the main context" | Dispatch the Generator agent -- keeps context clean |
| "This shader is too simple for agents" | Use `ue5-materials:author (direct YAML path)` directly for simple cases |
| "I'll skip the review" | Fine for simple shaders, but review complex ones |
| "I'll fix the HLSL myself" | Re-dispatch Architect with adjustment context |
```

Replace with:

```
## Red Flags

| Thought | Reality |
|---------|---------|
| "I'll skip brainstorming, the user described it clearly" | Entry Point A always brainstorms. The Architect does silent design; brainstorming is the interactive gate. |
| "I'll just write the HLSL inline" | Dispatch the Architect agent -- it reads the conventions |
| "I'll generate YAML in the main context" | Dispatch the Generator agent -- keeps context clean |
| "This shader is too simple for agents" | Use `ue5-materials:author (direct YAML path)` directly for simple cases |
| "I'll skip the review" | Fine for simple shaders, but review complex ones |
| "I'll fix the HLSL myself" | Re-dispatch Architect with adjustment context |
| "I'll emit a Comment box for this section" | **NEVER.** UE5 crashes on `UMaterialGraphNode_Comment::ResizeNode()`. Use Named Reroutes + column positioning. |
```

- [ ] **Step 5: Verify all changes are present**

```bash
grep -c "Phase 0a: Brainstorm Idea" plugins/ue5-materials/skills/author/SKILL.md
```
Expected: `1`

```bash
grep -c "material_brief.md" plugins/ue5-materials/skills/author/SKILL.md
```
Expected: at least `3` (diagram, Phase 0a body, Output Files table)

```bash
grep -c "superpowers:brainstorming" plugins/ue5-materials/skills/author/SKILL.md
```
Expected: `1`

```bash
grep -c "skip brainstorming" plugins/ue5-materials/skills/author/SKILL.md
```
Expected: `1`

- [ ] **Step 6: Commit**

```bash
git add plugins/ue5-materials/skills/author/SKILL.md
git commit -m "feat(ue5-materials): add Phase 0a brainstorm gate to author skill"
```

---

### Task 5: Add brainstorm principle to using-ue5-materials router

**Files:**
- Modify: `plugins/ue5-materials/skills/using-ue5-materials/SKILL.md:40-45`

- [ ] **Step 1: Add the one-line note to Key Principles**

Edit `plugins/ue5-materials/skills/using-ue5-materials/SKILL.md` — find:

```
## Key Principles

- **Opus for shader design**, Sonnet for node mechanics, agent subprocesses keep the main context clean.
- **File-based handoff** — agents write `shader_design.md`, `shader_code.hlsl`, `ue5_nodes.yaml`. The main context only sees summary tables.
- **YAML is the durable artifact** — it survives edits, diffs cleanly, replays in either mode.
- **Live and clipboard modes are interchangeable outputs** of the same YAML; pick based on what's running.
```

Replace with:

```
## Key Principles

- **Brainstorm before build** — new shaders (Entry Point A inside `author`) start with `superpowers:brainstorming` to lock the idea before silent agents design it. Iterations, HLSL edits, and direct-YAML path skip the gate.
- **Opus for shader design**, Sonnet for node mechanics, agent subprocesses keep the main context clean.
- **File-based handoff** — agents write `material_brief.md`, `shader_design.md`, `shader_code.hlsl`, `ue5_nodes.yaml`. The main context only sees summary tables.
- **YAML is the durable artifact** — it survives edits, diffs cleanly, replays in either mode.
- **Live and clipboard modes are interchangeable outputs** of the same YAML; pick based on what's running.
- **No Comment boxes** — Generator never emits `Comment` nodes; they crash UE5 on resize. Named Reroutes + column positioning replace them.
```

- [ ] **Step 2: Verify changes are present**

```bash
grep -c "Brainstorm before build" plugins/ue5-materials/skills/using-ue5-materials/SKILL.md
```
Expected: `1`

```bash
grep -c "No Comment boxes" plugins/ue5-materials/skills/using-ue5-materials/SKILL.md
```
Expected: `1`

```bash
grep -c "material_brief.md" plugins/ue5-materials/skills/using-ue5-materials/SKILL.md
```
Expected: `1`

- [ ] **Step 3: Commit**

```bash
git add plugins/ue5-materials/skills/using-ue5-materials/SKILL.md
git commit -m "docs(ue5-materials): router mentions brainstorm gate and no-Comment rule"
```

---

### Task 6: End-to-end verification

**Files:**
- No modifications. Verification only.

- [ ] **Step 1: Confirm no `type: Comment` guidance remains in any prompt template**

```bash
grep -n "type: Comment" plugins/ue5-materials/skills/author/*.md
```
Expected: no output (zero matches).

- [ ] **Step 2: Confirm Comment warning is present in node-types.md**

```bash
grep -n "DO NOT USE" plugins/ue5-materials/skills/author/node-types.md
```
Expected: one match on the `### MaterialExpressionComment — DO NOT USE` heading.

- [ ] **Step 3: Confirm Node Comment Bubbles section still exists (it's a different, safe feature)**

```bash
grep -n "^## Node Comment Bubbles" plugins/ue5-materials/skills/author/node-types.md
```
Expected: one match. Bubbles are attached `Desc=`/`NodeComment=` properties on any node — these do NOT trigger the crash and must remain documented.

- [ ] **Step 4: Confirm brainstorm Phase 0a is wired everywhere expected**

```bash
grep -l "superpowers:brainstorming" plugins/ue5-materials/skills/author/SKILL.md plugins/ue5-materials/skills/using-ue5-materials/SKILL.md
```
Expected: both paths listed.

- [ ] **Step 5: Confirm Named Reroute Strategy and Positioning Convention are in node-generator-prompt.md**

```bash
grep -nE "Named Reroute Strategy|Node Positioning Convention" plugins/ue5-materials/skills/author/node-generator-prompt.md
```
Expected: two matches, one for each heading.

- [ ] **Step 6: Confirm material_brief wiring in Architect prompt**

```bash
grep -nE "material_brief|authoritative design intent|intermediate_reroutes" plugins/ue5-materials/skills/author/hlsl-architect-prompt.md
```
Expected: at least 4 matches across the three patterns.

- [ ] **Step 7: Re-read each touched file quickly for structural sanity**

```bash
wc -l plugins/ue5-materials/skills/author/SKILL.md plugins/ue5-materials/skills/author/node-generator-prompt.md plugins/ue5-materials/skills/author/hlsl-architect-prompt.md plugins/ue5-materials/skills/author/node-types.md plugins/ue5-materials/skills/using-ue5-materials/SKILL.md
```
Each file should be larger than before — confirm no accidental truncation.

- [ ] **Step 8: Verify `node_registry.yaml` has no Comment entry (no action required)**

```bash
grep -c "Comment" plugins/ue5-materials/node_registry.yaml
```
Expected: `0`. If non-zero, flag to the user — the spec said the file had no Comment entry; a hit means the spec was wrong and we need a follow-up decision.

- [ ] **Step 9: Confirm the working tree is clean after all commits**

```bash
git status --short
```
Expected: empty output (all 5 commits from tasks 1–5 landed clean).

- [ ] **Step 10: Print commit log summary**

```bash
git log --oneline -n 6
```
Expected: the 5 new commits on top of the starting HEAD, in reverse order of this plan.

---

## Success criteria (from spec)

- For a new-shader request, brainstorming runs and `material_brief.md` lands in the per-material folder → Task 4 + Task 3.
- HLSL Architect treats the brief as authoritative → Task 3.
- Iteration flows, HLSL edits, and direct-YAML path are unchanged → Task 4 (Phase 0a explicitly scoped to Entry Point A).
- Router delegates unchanged → Task 5 (no routing-table change, only principles).
- Generated graphs contain no Comment nodes → Tasks 1, 2, 4, 5 (four reinforcing locations).
- Input packs appear as Named Reroute Declarations → Task 2.
- Node positions follow fixed column convention → Task 2.
