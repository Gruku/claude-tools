---
name: create
description: Create UE5 shaders from plain text descriptions. Dispatches HLSL Architect (Opus) and Node Generator (Sonnet) agents for a full material graph you can paste into the Material Editor.
---

# UE5 Shader Node Creator

Create production-ready UE5 Material Graph shaders from plain text descriptions. Dispatches specialized agents for HLSL design (Opus) and UE5 node generation (Sonnet), keeping the main context clean.

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
  python ../../ue5_material_generator.py ue5_nodes.yaml -o ue5_clipboard.txt
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
| `/shader-yaml` | Direct YAML workflow (skip the agent chain) |
| `/shader-registry` | Add new node types to the registry |

### Output Files (created in working directory)
| File | Purpose | When to paste |
|------|---------|---------------|
| `shader_design.md` | Design spec -- inputs, outputs, topology | Not pasted -- reference only |
| `shader_code.hlsl` | HLSL source code (standalone) | **HLSL-only updates:** paste into Custom node code field |
| `ue5_nodes.yaml` | YAML node definition (editable, re-runnable) | Not pasted -- intermediate format |
| `ue5_clipboard.txt` | Full graph in UE5 clipboard format | **First-time / topology changes:** Ctrl+V in Material Editor |

### Python Converter
```bash
python ../../ue5_material_generator.py ue5_nodes.yaml -o ue5_clipboard.txt
```
Requires: `pip install pyyaml`

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
| "I'll just write the HLSL inline" | Dispatch the Architect agent -- it reads the conventions |
| "I'll generate YAML in the main context" | Dispatch the Generator agent -- keeps context clean |
| "This shader is too simple for agents" | Use `/shader-yaml` directly for simple cases |
| "I'll skip the review" | Fine for simple shaders, but review complex ones |
| "I'll fix the HLSL myself" | Re-dispatch Architect with adjustment context |

## When NOT to Use This Workflow

For **simple, direct YAML generation** (you already know exactly what nodes you need):
- Use `/shader-yaml` instead -- skip the agent chain entirely
- Write YAML manually, run the converter, paste

For **adding new node types to the registry**:
- Use `/shader-registry` to check/add node definitions
