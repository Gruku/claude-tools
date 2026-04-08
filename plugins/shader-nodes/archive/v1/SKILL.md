---
name: ue5-custom-shader-nodes
description: Generate UE5.5 Material Graph node structures for copy-paste into the Material Editor. Use this skill when creating shader nodes, custom HLSL nodes, material functions, or wiring node graphs. Essential for UI shader development with animation systems.
user-invocable: true
argument-hint: [node-type or description]
---

# UE5 Custom Shader Node Generator

Generate production-ready Unreal Engine 5.5 Material Graph node structures that can be directly copy-pasted into the Material Editor.

## RECOMMENDED: Use YAML Workflow

For reliable node generation, prefer the **YAML + Python script** approach:

1. **Generate YAML** using `/ue5-shader-yaml` skill
2. **Convert to UE5** format with `ue5_material_generator.py`
3. **Paste** into Material Editor

See [SKILL-yaml.md](SKILL-yaml.md) for details.

## IMPORTANT: Check Node Registry First

Before generating nodes, **always check if the node type exists**:

1. Use `/ue5-node-registry [NodeType]` to check/add nodes
2. Registry location: `node_registry.yaml`
3. 50+ common nodes pre-defined (Add, Multiply, Lerp, DDX, etc.)
4. Use `Generic` type for nodes not in registry

## CRITICAL: Output Format Rules

1. **Output ONLY raw node text** - No explanatory text outside the node structures
2. **Use node comment bubbles** for documentation:
   - `Desc="..."` and `bCommentBubbleVisible=True` in inner object
   - `NodeComment="..."` and `bCommentBubbleVisible=True` in outer node
   - Best for documenting Float4 packing: `"In1_Shape : float4 (X, Y, Z, W)"`
3. **All connections require THREE things** (missing any = no wire visible):
   - `LinkedTo=(TargetNodeName TargetPinId,)` in SOURCE node's output pin
   - `LinkedTo=(SourceNodeName SourcePinId,)` in TARGET node's input pin
   - `Expression="/Script/Engine.[Type]'NodeName.ExprName'"` in TARGET's inner object
4. **⚠️ NamedRerouteUsage Declaration= path is DIFFERENT:**
   - `Declaration=` does NOT include MaterialGraphNode: `'MaterialExpressionNamedRerouteDeclaration_1'`
   - `Input=` DOES include MaterialGraphNode: `'MaterialGraphNode_16.MaterialExpressionNamedRerouteUsage_1'`
   - Getting this wrong causes "Invalid Named Reroute" errors!
5. See [connection-syntax.md](connection-syntax.md) for the complete connection reference

## Core Principles

### 1. Animation-First Design
- Animations use **input time triggers** where the animation plays from a set time
- Provide **exit time triggers** that fire another animation or reverse back to initial state
- Example: `EnterStart=-1` (inactive) → set to current time to begin → `ExitStart` triggers reverse

### 2. Parameter Packing
- Pack logically grouped parameters into **Float4** to preserve memory bandwidth
- Example: `In1_Sector = float4(StartAngle, ArcAngle, Radius, Thickness)`
- Document each component in HLSL header comments

### 3. UE5.5 Best Practices
- Use `saturate()` instead of `clamp(x, 0, 1)`
- Prefer `lerp()` for smooth interpolation
- Use `step()` for hard cutoffs
- Apply derivatives (`ddx`/`ddy`) for antialiasing - see `/ue5-ui-shader-antialiasing` skill

## Auto-Layout System

The YAML generator (`ue5_material_generator.py`) automatically positions nodes using **topology-based column layout**:

### How It Works

1. **Column assignment**: Nodes are assigned to columns based on their graph depth (longest path from root/input nodes). Leaf nodes (constants, time) go in column 0, their consumers in column 1, etc.
2. **Horizontal spacing**: Columns are separated by `spacing_x` (default: 256px)
3. **Vertical spacing**: Nodes within a column use `spacing_y` (default: 96px), preserving YAML definition order
4. **Centering**: Non-leaf nodes are vertically centered relative to their input nodes (e.g., a MakeFloat4 centers between its 4 input constants)
5. **Overlap resolution**: Nodes that would overlap after centering are pushed apart by `spacing_y`

### Typical Column Layout

| Column (Depth) | Content | Example X |
|----------------|---------|-----------|
| 0 (leftmost) | Constants, Time, TexCoord | 5000 |
| 1 | MakeFloat4/3/2, Math ops | 5256 |
| 2 | Custom HLSL nodes | 5512 |
| 3 (rightmost) | Output Named Reroutes | 5768 |

### Manual Position Override

Override auto-layout for specific nodes with `pos_x` / `pos_y` in YAML:
```yaml
nodes:
  - name: MyNode
    type: Constant
    value: 1.0
    pos_x: 4000    # Explicit position — auto-layout won't touch this node
    pos_y: 500
```

### Comment Bubbles on Float4 Outputs

Always add `desc:` to MakeFloat4 nodes to document what each component contains. The generator creates comment bubbles on both inner and outer nodes automatically.

Format: `"[ParamName] : float4 ([X], [Y], [Z], [W])"`

## Workflow: Multi-Agent Node Generation

Due to the verbosity of UE5 node structures (~90k characters for complex nodes), use a **delegated agent approach**:

### Step 1: Design Phase (Main Claude)
- Understand requirements
- Define inputs/outputs
- Plan node topology
- Write HLSL logic

### Step 2: Structure Generation (Agents)
Delegate to agents for parallel node generation:

```
Launch agents in parallel for:
- Input parameter nodes (constants, reroutes)
- Custom node structure
- Output wiring
- Comment boxes
```

### Step 3: Assembly (Main Claude)
- Validate connections via PinId matching
- Verify GUID uniqueness
- Arrange node positions
- Output final pasteable structure

## Node Structure Reference

For detailed node type specifications, see [node-types.md](node-types.md).

## GUID Generation

Every node requires unique GUIDs. Format: `XXXXXXXX4XXXXYXXXXYXXXXXXXXXXXXXXX` where:
- All characters are hex (0-9, A-F)
- Position 8 should be '4'
- Positions 12-13 should be '4' followed by 8-B

Generate GUIDs that are:
- 32 characters total
- Uppercase hex
- Unique within the same graph

## Template Quick Reference

### Constant Float Node
```
Begin Object Class=/Script/UnrealEd.MaterialGraphNode Name="MaterialGraphNode_[N]"
   Begin Object Class=/Script/Engine.MaterialExpressionConstant Name="MaterialExpressionConstant_[NAME]"
   End Object
   Begin Object Name="MaterialExpressionConstant_[NAME]"
      R=[VALUE]
      MaterialExpressionEditorX=[X]
      MaterialExpressionEditorY=[Y]
      MaterialExpressionGuid=[GUID1]
      Material="[MATERIAL_PATH]"
   End Object
   MaterialExpression="/Script/Engine.MaterialExpressionConstant'MaterialExpressionConstant_[NAME]'"
   NodePosX=[X]
   NodePosY=[Y]
   NodeGuid=[GUID2]
   CustomProperties Pin (PinId=[PIN_GUID],PinName="Value",PinType.PinCategory="optional",PinType.PinSubCategory="red"...)
   CustomProperties Pin (PinId=[OUTPUT_PIN_GUID],PinName="Output",Direction="EGPD_Output"...)
End Object
```

### Custom HLSL Node
See [templates/custom-node.md](templates/custom-node.md) for the full template.

### Named Reroute (Variable Declaration)
See [templates/named-reroute.md](templates/named-reroute.md) for the full template.

## Pin Connection System (CRITICAL - READ THIS!)

**⚠️ The #1 cause of broken nodes is missing `LinkedTo=` in CustomProperties Pin.**

**Every A → B connection requires THREE things:**

### 1. Source Output Pin - LinkedTo (draws wire FROM)
```
// In node A's CustomProperties:
CustomProperties Pin (PinId=AAAA...,PinName="Output",Direction="EGPD_Output",...,LinkedTo=(B_NodeName B_PinId,),...)
```

### 2. Target Input Pin - LinkedTo (draws wire TO)
```
// In node B's CustomProperties:
CustomProperties Pin (PinId=BBBB...,PinName="Input",...,LinkedTo=(A_NodeName A_PinId,),...)
```

### 3. Target Inner Object - Expression (data reference)
```
// In node B's inner object:
Input=(Expression="/Script/Engine.[Type]'A_NodeName.A_ExpressionName'")
```

### Why This Matters
| What you have | Result |
|---------------|--------|
| Expression only | ✗ No visible wire, may compile |
| LinkedTo in one pin only | ✗ No visible wire |
| All three | ✓ Wire visible AND compiles |

**ALWAYS verify LinkedTo exists in BOTH the source output pin AND target input pin.**

See [connection-syntax.md](connection-syntax.md) for complete examples and templates.

## Practical Workflow

When asked to create a shader node system:

1. **Clarify requirements**: What inputs, outputs, behavior?
2. **Plan structure**:
   - List all required nodes (constants, reroutes, custom nodes)
   - Define connection topology
3. **Generate in phases**:
   - Phase 1: Input parameter nodes
   - Phase 2: Logic/custom nodes
   - Phase 3: Output/reroute nodes
   - Phase 4: Wire connections
4. **Validate**: Ensure all LinkedTo references exist

## File Organization

For complex materials, output to separate files:
- `inputs.txt` - Parameter nodes
- `logic.txt` - Custom HLSL nodes
- `wiring.txt` - Connection definitions
- `full-graph.txt` - Complete assembled structure

## Examples

For working examples extracted from production shaders, see [examples.md](examples.md).

## HLSL Conventions

For UE5-specific HLSL patterns and antialiasing, see [hlsl-conventions.md](hlsl-conventions.md).
