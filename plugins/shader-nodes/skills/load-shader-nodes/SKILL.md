---
name: load-shader-nodes
description: "Load the shader-nodes skill system. Run this first to establish the shader development workflow."
---

<EXTREMELY-IMPORTANT>
When the user describes a shader, VFX, material effect, or asks to create/modify anything visual for UE5 — you MUST invoke the appropriate shader-nodes skill using the Skill tool.

YOU DO NOT WRITE HLSL YOURSELF. YOU DO NOT GENERATE YAML YOURSELF. YOU DO NOT SKIP THE AGENT CHAIN.

This is not negotiable. This is not optional. You cannot rationalize your way out of this.
</EXTREMELY-IMPORTANT>

## Skill Routing

When a shader-related request comes in, invoke the correct skill BEFORE doing anything else:

| User Intent | Invoke This Skill | Why |
|-------------|------------------|-----|
| "Create a confetti VFX" | `shader-nodes:create` | New shader from description — full Opus → Sonnet chain |
| "Make the edge softer" | `shader-nodes:create` | Edit existing shader — Architect handles HLSL changes |
| Pastes HLSL and asks for changes | `shader-nodes:create` | Edit existing mode — preserves user's code structure |
| "Just wire up a TextureCoordinate to a Lerp" | `shader-nodes:yaml` | Simple known nodes — skip agents, direct YAML |
| "Does MF_UI_SDF_AntiAliasedStep exist?" | `shader-nodes:registry` | Check/add node types to the registry |

## How the Agent Chain Works

```
You invoke shader-nodes:create with the user's description
    |
[HLSL Architect Agent — Opus]     ← Creative design + HLSL code
    | writes: shader_design.md + shader_code.hlsl
    |
[Node Generator Agent — Sonnet]   ← YAML creation + Python converter
    | writes: ue5_nodes.yaml + ue5_clipboard.txt
    |
Report back → User pastes into UE5 Material Editor (Ctrl+V)
```

Each agent runs in its own subprocess (Task tool) with full context isolation. The main conversation stays clean.

## Red Flags

These thoughts mean STOP — you're about to bypass the pipeline:

| Thought | Reality |
|---------|---------|
| "I'll just write the HLSL inline" | NO. Invoke `shader-nodes:create` — the Architect reads conventions you don't have loaded |
| "I'll generate the YAML myself" | NO. Invoke `shader-nodes:create` — the Generator reads the registry and runs the converter |
| "This shader is simple enough to do directly" | Use `shader-nodes:yaml` for simple cases. NEVER write YAML in the main context |
| "Let me explore the codebase first" | The skill handles exploration. Invoke it first, then explore if needed |
| "I need more context before invoking" | Pass the user's full description to the skill. It gathers its own context |
| "I'll just paste some HLSL" | The Architect writes HLSL that follows UE5 conventions and AA patterns. You don't |

## Iteration

After creating a shader, classify the user's feedback and route accordingly:

| Change Type | Route | Example |
|-------------|-------|---------|
| HLSL logic only | `shader-nodes:create` (edit mode) | "Make the edge softer" |
| Topology change | `shader-nodes:create` (full rebuild) | "Add a glow output" |
| Value tweak | Edit YAML directly, re-run converter | "Set radius to 0.5" |

## Key Principles

- **Opus for creativity** — HLSL design runs on the most capable model
- **Sonnet for mechanics** — Node generation is structured conversion
- **Context isolation** — Each agent runs in its own subprocess
- **SDF AA via Material Function** — HLSL outputs raw SDF, `MF_UI_SDF_AntiAliasedStep` handles AA in graph
