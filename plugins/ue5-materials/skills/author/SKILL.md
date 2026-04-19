---
name: author
description: Author UE5 materials from a plain-text description or a known YAML spec. Produces a YAML file that `apply_material.py` applies to Unreal — live via MCPBridge when the Editor is running, or as T3D clipboard text when it isn't. Dispatches HLSL Architect (Opus) and Node Generator (Sonnet) agents for complex designs; falls through to a direct-YAML path for simple, known node setups. Invoke whenever the user asks to build, change, or iterate on a UE5 material, material function, or shader effect.
---

# UE5 Materials — Author

Produce UE5 Material Graph shaders from plain-text descriptions or known YAML specs. Dispatches specialized agents for HLSL design (Opus) and UE5 node generation (Sonnet) when the request needs design work, and falls through to a direct YAML path when the user already knows the nodes. Output is always a `ue5_nodes.yaml` file; `apply_material.py` handles the hand-off to UE5 in either live (MCPBridge) or clipboard (T3D paste) mode.

## Choosing a Path

Identify the scenario before starting:

- **Direct YAML path** — user already knows the nodes ("wire a TextureCoordinate into a Lerp", "add a Multiply by 2"). Skip agents. Write YAML directly, run `apply_material.py`.
- **Agent chain** — user describes a visual effect, asks for HLSL changes, or pastes HLSL. Dispatch Architect → Generator.

If in doubt, use the agent chain — a minute of extra time is cheaper than a broken graph. In particular, when the user's phrasing sounds like an **idea** ("I want…", "make a…", "build a…") rather than a **wiring instruction** ("connect X to Y", "add a Multiply"), treat it as Entry Point A — which now means Phase 0a brainstorm before the Architect.

## Working Directory

All output files for a material live in a per-material folder under the user's current working directory:

```
<cwd>/ue5-materials/<material-name>/
```

- `<cwd>` is the directory Claude Code is invoked from (typically the user's project root).
- `<material-name>` matches the YAML `material:` field (e.g., `M_SpinningTintedTexture`).
- All output files (`shader_design.md`, `shader_code.hlsl`, `ue5_nodes.yaml`, `ue5_clipboard.txt`) live together here.
- Create the folder if it doesn't exist before writing any files. Pass its absolute path to dispatched agents so their outputs land there.

**Do NOT write working files inside the plugin directory** (e.g., the plugin's `scratch/` folder). The plugin is shared infrastructure; per-material artifacts belong with the user's project so they can be committed, diffed, and re-applied later.

## Applying the YAML

After the YAML exists (either path), apply it:

```bash
python <PLUGIN_DIR>/apply_material.py <working-dir>/ue5_nodes.yaml
# --mode auto (default): live if MCPBridge is up, clipboard otherwise
# --mode live:            force MCPBridge — fails if unreachable
# --mode clipboard:       force T3D; use `-o <working-dir>/ue5_clipboard.txt` to capture to a file
```

`<PLUGIN_DIR>` is the plugin root — two levels above this SKILL.md (`./../../`). Resolve it to an absolute path before invoking, since the working directory is outside the plugin.

Every run archives the YAML under `<PLUGIN_DIR>/.ue5-materials-history/` for replay or diff.

**When the user doesn't care about live vs clipboard**, run with `--mode auto` and tell them which mode ran.

### Live-mode limitations

Live mode (MCPBridge) is the fast path but has narrower node-type support than clipboard. The Unreal C++ bridge recognises these types natively with value/parameter plumbing:

- `Constant`, `Constant3Vector`, `ScalarParameter`, `VectorParameter`, `TextureSample`, `Add`, `Multiply`, `Lerp` (aka `LinearInterpolate`)

Other types (`Time`, `Custom`, `MakeFloat4`, `NamedRerouteDeclaration`, most of the registry) still *create* through the dynamic UClass fallback, but their special properties (Custom HLSL code, MakeFloat4 MaterialFunction binding, named reroute vars) are NOT set. For those, use clipboard mode. The direct-YAML path is usually fine for live; the agent chain usually needs clipboard.

Pin wiring in live mode identifies target pins by **integer index** (`A -> B.0`), not by name. Root material inputs (`BaseColor`, `Metallic`, `Roughness`, `Normal`, `Opacity`, etc.) are resolved by name as usual.

## File Locations

All paths below are relative to THIS skill's base directory (the directory containing this SKILL.md).

- Agent prompts: `./hlsl-architect-prompt.md`, `./node-generator-prompt.md`, `./shader-reviewer-prompt.md`
- HLSL reference: `./hlsl-conventions.md`, `./antialiasing-reference.md`
- Generator reference: `./connection-syntax.md`, `./node-types.md`
- Shared files (plugin root): `../../node_registry.yaml`, `../../ue5_material_generator.py`

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

## Entry Points

This skill handles several starting scenarios. Before dispatching agents, identify which applies:

### A. New Shader from Description (default)
User describes what they want in plain text. Full chain: Architect -> Generator.

### B. Edit Existing HLSL
User pastes or links existing HLSL code and asks for changes. Dispatch Architect in `edit_existing` mode -- it reads the provided code, makes the requested changes, and saves updated `shader_code.hlsl`. Then decide:
- If inputs/outputs unchanged -> **HLSL-only** -- user pastes code into Custom node
- If inputs/outputs changed -> dispatch Generator for full graph rebuild

### C. Working with External Reroutes
User already has Named Reroutes in their material graph (e.g., `UV`, `customTime`, `AnimEnterStart`). They provide these by:
- **Telling you**: "I already have UV and customTime reroutes"
- **Pasting UE5 node text**: extract NamedRerouteDeclaration names from it
- **Listing them**: "External reroutes: UV (float2), customTime (float), AnimParams (float4)"

When external reroutes are present:
1. Pass them to the Architect as `external_reroutes` in the prompt
2. Architect uses them as HLSL input names (same as any other input)
3. Node Generator **skips creating source nodes** for these -- no TextureCoordinate, no Time node
4. Instead, the generated graph leaves those Custom node input pins **unconnected**
5. User manually wires their existing reroutes to these pins after pasting

This is the practical approach -- UE5 NamedRerouteUsage nodes require matching VarGuids that only exist at paste time, so leaving pins unwired for manual connection is faster and more reliable.

### D. Combination: Existing Code + External Reroutes
User pastes HLSL that references inputs from their existing reroute system. Both B and C apply. The Architect preserves external input names so the code stays compatible with the user's existing graph.

---

## The Workflow

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

### Phase 0: Gather Context

Before dispatching agents, collect:

1. **External reroutes** -- Ask or extract from pasted UE5 text:
   - What Named Reroutes already exist in the user's graph?
   - What type is each? (float, float2, float3, float4)
   - These become `external_reroutes` in the agent prompt

2. **Existing HLSL** -- If the user pasted or linked code:
   - Save it to `shader_code.hlsl` in the working directory
   - Set `edit_existing: true` in the Architect prompt

### Phase 1: Dispatch HLSL Architect (Opus)

Read the agent prompt template:
```
./hlsl-architect-prompt.md
```

**IMPORTANT:** Before dispatching, replace all `SKILL_DIR` references in the agent prompt with the absolute path to THIS skill's base directory. This ensures agents can read reference files at the correct location.

Dispatch a `general-purpose` agent with `model: opus`:
- Pass the user's plain text shader description (or `edit_existing: true` + path to existing code)
- Pass `external_reroutes` list if the user has existing Named Reroutes
- Agent reads `./hlsl-conventions.md` and `./antialiasing-reference.md`
- Agent designs shader architecture and writes HLSL code
- Agent saves `shader_design.md` + `shader_code.hlsl` in working directory
- Agent reports: shader summary, input packing table, outputs, files written

**Wait for the agent to complete.** Review the report before proceeding.

### Phase 2: Dispatch Node Generator (Sonnet)

Read the agent prompt template:
```
./node-generator-prompt.md
```

**IMPORTANT:** Before dispatching, replace all `SKILL_DIR` references in the agent prompt with the absolute path to THIS skill's base directory.

Dispatch a `general-purpose` agent with `model: sonnet`:
- Pass paths to `shader_design.md` and `shader_code.hlsl`
- Agent reads `./connection-syntax.md`, `./node-types.md` for YAML format reference
- Agent reads `../../node_registry.yaml` for available node types
- Agent creates `ue5_nodes.yaml` with all nodes and connections
- Agent runs `../../ue5_material_generator.py` to produce `ue5_clipboard.txt`
- Agent reports: success/failure, node count, file locations

**If failed:** Read the error, fix the issue description, re-dispatch.

### Phase 3: Report to User

Present a clean summary:

```
## Shader: [Name]

[1-2 sentence description of what the shader does]

### Inputs
| Pack | Components | Defaults |
|------|-----------|----------|
| In1_Name | X, Y, Z, W | 0.0, 0.0, 0.0, 0.0 |

### Outputs
| Name | Type | Description |
|------|------|-------------|
| OutputName | float4 | What it provides |

### Files
- `shader_design.md` -- Design spec (human-readable)
- `shader_code.hlsl` -- HLSL source code
- `ue5_nodes.yaml` -- Node definition (editable, re-runnable)
- `ue5_clipboard.txt` -- **Full graph: open, Ctrl+A, Ctrl+C, then Ctrl+V in UE5 Material Editor**
```

### Context Isolation Rules

- Do NOT paste HLSL code, YAML, or clipboard content into the main conversation
- Report ONLY the summary table and file paths — the user reads files directly
- NEVER read `ue5_clipboard.txt` — these are 100KB+ files that destroy context. Only read if the user explicitly requests it for debugging or direct editing
- Keep the main conversation clean — all heavy content stays in agent subprocesses and output files

### Phase 4: Iteration (On User Feedback)

When the user requests adjustments:

**1. Classify the change scope:**

| User Says | Scope | What to Re-dispatch |
|-----------|-------|-------------------|
| "Make the edge softer" | HLSL only | Architect (Opus, hlsl_only) → Generator (Sonnet) |
| "Use a different easing function" | HLSL only | Architect (Opus, hlsl_only) → Generator (Sonnet) |
| "Fix the AA on the border" | HLSL only | Architect (Opus, hlsl_only) → Generator (Sonnet) |
| "Add a glow output" | Topology change | Architect (Opus) → Generator (Sonnet) |
| "Add an animation trigger" | Design + HLSL | Architect (Opus) → Generator (Sonnet) |
| "Change the default radius to 0.5" | Constant value | Edit YAML directly, re-run converter |
| "Move the nodes to the left" | Layout only | Edit YAML `position_start`, re-run converter |

**2. For HLSL-only changes:**
- Re-dispatch Architect with `hlsl_only: true` in the prompt
- Agent reads previous `shader_code.hlsl`, makes targeted changes
- Agent saves updated `shader_code.hlsl`
- **ALWAYS dispatch Generator afterward** to regenerate `ue5_nodes.yaml` and `ue5_clipboard.txt`
- This keeps all output files in sync

**3. For topology changes (new inputs/outputs/nodes):**
- Re-dispatch Architect with "Adjustment Context" section filled in:
  - Previous design: path to existing `shader_design.md`
  - Previous HLSL: path to existing `shader_code.hlsl`
  - User feedback: exactly what the user said
- Then re-dispatch Generator with updated design files
- Full graph rebuild -- user pastes entire `ue5_clipboard.txt`

**4. For value-only changes:**
- Edit `ue5_nodes.yaml` directly (change the `value:` field)
- Re-run the converter:
  ```bash
  python <PLUGIN_DIR>/apply_material.py <working-dir>/ue5_nodes.yaml  # or --mode clipboard -o <working-dir>/ue5_clipboard.txt
  ```
- Report the update

### Phase 5: Optional Review

For complex shaders, dispatch the reviewer agent:
```
./shader-reviewer-prompt.md
```

Use when:
- Multiple Custom HLSL nodes
- Advanced techniques (SDF, polar coords, multi-pass animation)
- User explicitly requests review
- Generator reported warnings

## Quick Reference

### Agent Prompt Templates
| Agent | File | Model | Purpose |
|-------|------|-------|---------|
| HLSL Architect | `./hlsl-architect-prompt.md` | Opus | Shader design + HLSL code |
| Node Generator | `./node-generator-prompt.md` | Sonnet | YAML + UE5 converter |
| Shader Reviewer | `./shader-reviewer-prompt.md` | Sonnet | Quality validation |

### Reference Files (loaded by agents, not main context)
| File | Used By | Content |
|------|---------|---------|
| `./hlsl-conventions.md` | Architect | UE5 HLSL patterns, intrinsics, animation |
| `./antialiasing-reference.md` | Architect | AA via MF_UI_SDF_AntiAliasedStep Material Function |
| `./connection-syntax.md` | Generator | Pin connection rules |
| `./node-types.md` | Generator | Node structure specs |
| `../../node_registry.yaml` | Generator | 50+ node type definitions |

### Other Skills
| Skill | Purpose |
|-------|---------|
| `ue5-materials:author (direct YAML path)` | Direct YAML workflow (skip the agent chain) |
| `ue5-materials:registry` | Add new node types to the registry |

### Output Files (created in working directory)
| File | Purpose | When to paste |
|------|---------|---------------|
| `material_brief.md` | Design brief from Phase 0a brainstorm (Entry Point A only) | Not pasted -- feeds HLSL Architect as authoritative design intent |
| `shader_design.md` | Design spec -- inputs, outputs, topology | Not pasted -- reference only |
| `shader_code.hlsl` | HLSL source code (standalone) | **HLSL-only updates:** paste into Custom node code field |
| `ue5_nodes.yaml` | YAML node definition (editable, re-runnable) | Not pasted -- intermediate format |
| `ue5_clipboard.txt` | Full graph in UE5 clipboard format | **First-time / topology changes:** Ctrl+V in Material Editor |

### Python Converter
```bash
python <PLUGIN_DIR>/apply_material.py <working-dir>/ue5_nodes.yaml  # or --mode clipboard -o <working-dir>/ue5_clipboard.txt
```
Requires: `pip install pyyaml`. `<PLUGIN_DIR>` = plugin root (two levels above this SKILL.md). `<working-dir>` = `<cwd>/ue5-materials/<material-name>/` per the **Working Directory** section.

## Design Principles

| Principle | Implementation |
|-----------|---------------|
| **Opus for creativity** | HLSL Architect runs on Opus -- the hardest creative work |
| **Sonnet for mechanics** | Node Generator runs on Sonnet -- structured conversion |
| **Context isolation** | Each agent runs in its own Task -- no main context pollution |
| **File-based handoff** | Agents communicate via files, not returned text |
| **Structured reports** | Each agent returns a summary table, not raw output |
| **Iterative by default** | Adjustment context baked into prompt templates |
| **Scope-aware iteration** | Classify changes to minimize re-work |
| **SDF AA via Material Function** | HLSL outputs raw SDF -- `MF_UI_SDF_AntiAliasedStep` handles AA in graph |

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

## When NOT to Use This Workflow

For **simple, direct YAML generation** (you already know exactly what nodes you need):
- Use `ue5-materials:author (direct YAML path)` instead -- skip the agent chain entirely
- Write YAML manually, run the converter, paste

For **adding new node types to the registry**:
- Use `ue5-materials:registry` to check/add node definitions
