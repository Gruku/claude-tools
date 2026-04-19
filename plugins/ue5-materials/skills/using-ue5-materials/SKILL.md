---
name: using-ue5-materials
description: Route any UE5 / Unreal Engine material, shader, or material-graph authoring request to the correct ue5-materials sub-skill. Invoke this whenever the user asks to build, edit, tweak, or debug a UE5 material, shader effect, or Material Editor graph — even if they don't explicitly name the skill or say "shader". Covers both live editing via MCPBridge and clipboard-paste T3D workflows.
---

# UE5 Materials — Router

Any request to create, modify, or debug a **UE5 Material** or **Material Graph** — whether the user says "shader", "VFX", "material", "material function", or just describes a visual effect — must route through this plugin's sub-skills. Don't write HLSL inline, don't write YAML inline, don't guess node wiring in the main conversation.

## Routing Table

| User Intent | Invoke | Why |
|---|---|---|
| "Create a confetti VFX" / "I want a glowing edge" | `ue5-materials:author` | Plain-text description → full material graph |
| "Make the edge softer" / "use a different easing" | `ue5-materials:author` (iterate) | HLSL change on an existing shader |
| Pastes HLSL, asks for changes | `ue5-materials:author` (edit mode) | Edits preserve existing input/output signature |
| "Wire a TextureCoordinate into a Lerp" / simple graph | `ue5-materials:author` (direct YAML path) | Known nodes, no design work needed |
| "Does MF_UI_SDF_AntiAliasedStep exist?" | `ue5-materials:registry` | Look up or register a node type |
| "Check if MCPBridge is up" / "apply this YAML live" | run `apply_material.py` directly | CLI — no sub-skill needed |

## Execution Modes

This plugin has two paths for getting a YAML spec into UE5:

- **Live mode** — when the Unreal Editor is running with MCPBridge available at `localhost:13580`, `apply_material.py --mode live` drives `create_material` + `add_material_expressions` + `connect_material_pins` directly. The material appears in the Editor without paste.
- **Clipboard mode** — `apply_material.py --mode clipboard` emits T3D text. User copies it, opens the Material Editor, Ctrl+V.
- **Auto mode (default)** — probes the bridge, uses live if up, clipboard otherwise.

The `author` skill produces YAML; the user or Claude then runs `apply_material.py` to apply it. Live mode is preferred when available; clipboard is the fallback.

## Red Flags

| Thought | Reality |
|---|---|
| "I'll write the HLSL inline, it's simple" | Invoke `ue5-materials:author`. HLSL conventions live inside sub-agent prompts. |
| "I'll generate the YAML myself in the main context" | Invoke `ue5-materials:author`. The YAML format has subtle rules. |
| "This is just a quick wire-up" | Still invoke `author` — it has a direct-YAML path for simple cases. |
| "I should explore the codebase first" | The skill does its own exploration. Invoke first. |

## Key Principles

- **Brainstorm before build** — new shaders (Entry Point A inside `author`) start with `superpowers:brainstorming` to lock the idea before silent agents design it. Entry Points B, C, D, Phase 4 iterations, and direct-YAML path skip the gate.
- **Opus for shader design**, Sonnet for node mechanics, agent subprocesses keep the main context clean.
- **File-based handoff** — agents write `material_brief.md`, `shader_design.md`, `shader_code.hlsl`, `ue5_nodes.yaml`. The main context only sees summary tables.
- **YAML is the durable artifact** — it survives edits, diffs cleanly, replays in either mode.
- **Live and clipboard modes are interchangeable outputs** of the same YAML; pick based on what's running.
- **No Comment boxes** — Generator never emits `Comment` nodes; they crash UE5 on resize. Named Reroutes + column positioning replace them.
