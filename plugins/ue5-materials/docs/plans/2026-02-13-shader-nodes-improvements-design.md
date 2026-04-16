# Shader Nodes Plugin Improvements — Design

Date: 2026-02-13

## Problem Statement

The shader-nodes plugin has several issues impacting quality and usability:
- Duplicate commands/skills waste ~170 tokens of context per conversation
- Comment nodes in the Python generator are mispositioned (no `contains` support)
- The HLSL-only fast path skips the Generator, leaving `ue5_clipboard.txt` out of sync
- The HLSL Architect has no self-review step, producing correctness/pattern/creativity issues
- Main context gets polluted with HLSL/YAML/clipboard content that should stay in agent subprocesses

## Design

### 1. Remove Duplicate Commands

Delete all 4 command files that duplicate existing skills:
- `commands/create.md` (duplicates `skills/create/SKILL.md`)
- `commands/edit.md` (duplicates `skills/create/SKILL.md` edit mode)
- `commands/yaml.md` (duplicates `skills/yaml/SKILL.md`)
- `commands/registry.md` (duplicates `skills/registry/SKILL.md`)

Remove from both plugin source and plugin cache. Saves ~170 tokens per conversation.

### 2. Always Regenerate After HLSL Changes

Remove the "skip Generator" fast path from `skills/create/SKILL.md`.

**Before:** HLSL-only changes skip the Node Generator. User manually pastes code into Custom node.
**After:** ALL changes run Architect -> Generator -> Python converter. User always gets a fresh `ue5_clipboard.txt`.

The iteration classification table remains (tells the Architect whether it's a small tweak or full redesign), but the Generator always runs afterward.

Update affected files:
- `skills/create/SKILL.md` — Remove Phase 4 HLSL-only fast path, update iteration table
- `skills/create/hlsl-architect-prompt.md` — Keep hlsl_only mode for the Architect (it still does targeted edits), but the orchestrator always dispatches Generator after

### 3. Fix Comment Positioning in Python Generator

#### 3a. `contains` property on Comment nodes

YAML format:
```yaml
- name: Comment_Inputs
  type: Comment
  text: "Confetti Inputs"
  contains: [In1_CompX, In1_CompY, In1_PackName, UV, Time]
  color: [0.15, 0.15, 0.15]
```

Implementation in `ue5_material_generator.py`:
- Add `contains_nodes: List[str]` field to `CommentNode`
- Exclude Comment nodes from the depth-based layout algorithm
- After `_compute_layout()` positions all regular nodes, run a post-layout pass:
  1. For each Comment with `contains_nodes`, compute bounding box of contained nodes
  2. `pos_x = min_x - padding`, `pos_y = min_y - padding - title_height`
  3. `size_x = max_x - min_x + node_width_estimate + padding`
  4. `size_y = max_y - min_y + node_height_estimate + padding`
  5. Padding ~80px, title_height ~40px, node_width_estimate ~200px, node_height_estimate ~100px
- Comments without `contains` and without manual `pos_x`/`pos_y` use auto-grouping fallback

#### 3b. Auto-grouping fallback

When a Comment has no `contains` and no manual position:
1. **Naming convention** (primary): `In1_*`, `In2_*` prefix nodes -> input group. `Out_*` prefix -> output group. Custom nodes -> own group.
2. **Connectivity** (secondary): Trace connection chains for ungrouped nodes and wrap connected subgraphs.
3. Explicit `contains` always wins over auto-detection.

The Node Generator agent should always write explicit `contains` lists. Auto-grouping is a safety net.

#### 3c. Additional generator fixes from code review

- **Silent pin fallback -> warning**: When a connection pin name doesn't match, log a warning instead of silently falling back to the first pin
- **Array length validation**: Validate `value` array length for Constant3Vector (3) and Constant4Vector (4)
- **Null-check on yaml_data**: After `yaml.safe_load()`, check for None before accessing

### 4. HLSL Architect Self-Review

Add a mandatory self-review step in `skills/create/hlsl-architect-prompt.md`, after writing HLSL and before returning:

1. **Correctness check** — Walk through the math. Are SDF calculations correct? Do animations trigger at the right time? Edge cases (UV boundaries, time=0, division by zero)?
2. **UE5 patterns check** — Using `saturate()` not `clamp(0,1)`? Float4 packing logical? No `fwidth()`/`smoothstep()` for AA (raw SDF output)? Y-axis direction correct for UV space?
3. **Creativity check** — Is this the most interesting approach? Could a different technique produce a better result?
4. **Revise if needed** — Fix any issues found, save final files

#### UE5 UV Space Convention

Add to both the self-review checklist and `hlsl-conventions.md`:

> UE5 UV Y-axis is inverted compared to standard math — Y=0 is at the TOP, Y increases DOWNWARD.
> - "Up" visually = negative Y direction
> - Gravity "down" = positive Y direction
> - Launch/velocity "up" = negative Y component
> - All physics simulations, particle motion, and directional animations must account for this

Self-review must explicitly verify: "Are all Y-direction calculations correct for UE5's top-down UV space?"

#### Deferred to future iteration
- More rigorous UE5 conventions documentation
- Real shader examples as few-shot reference for the Architect

### 5. Context Isolation

#### Already in place:
- `load-shader-nodes` SKILL.md uses `<EXTREMELY-IMPORTANT>` tags and red flags table to force skill invocation
- `create/SKILL.md` dispatches agents via Task tool with context isolation

#### Updates needed:
- **Phase 3 (Report to User)** in `create/SKILL.md`: "Do NOT paste HLSL code or YAML into the main conversation. Report only the summary table and file paths."
- **NEVER read `ue5_clipboard.txt`** in any agent or main context — these are 100KB+ files. Only read if user explicitly requests for debugging or direct editing.
- Node Generator verifies the file exists and is non-empty, but does NOT read back full contents.

## Files to Modify

| File | Change |
|------|--------|
| `commands/create.md` | DELETE |
| `commands/edit.md` | DELETE |
| `commands/yaml.md` | DELETE |
| `commands/registry.md` | DELETE |
| `skills/create/SKILL.md` | Remove HLSL-only skip, add context isolation rules, add clipboard read prohibition |
| `skills/create/hlsl-architect-prompt.md` | Add self-review step, add UV Y-axis convention |
| `skills/create/hlsl-conventions.md` | Add UV Y-axis convention |
| `skills/create/node-generator-prompt.md` | Add `contains` usage for comments, add clipboard read prohibition |
| `ue5_material_generator.py` | Comment `contains` support, auto-grouping, pin warning, validation fixes |
| `~/.claude/skills/load-shader-nodes/SKILL.md` | Already updated (no further changes) |

## Implementation Order

1. Delete duplicate commands (instant, no dependencies)
2. Update `create/SKILL.md` (remove HLSL-only path, add context rules)
3. Update `hlsl-architect-prompt.md` (self-review + UV convention)
4. Update `hlsl-conventions.md` (UV convention)
5. Update `node-generator-prompt.md` (contains usage + clipboard rule)
6. Fix `ue5_material_generator.py` (comment positioning + validation fixes)
7. Sync all changes to plugin cache
