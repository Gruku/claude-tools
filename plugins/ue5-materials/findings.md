# UE5 Material Node Generation - Research Findings

Research conducted: January 2025

## Problem Statement

Generating UE5 Material Graph nodes programmatically is challenging because:
- Even simple node setups require ~5,000-90,000 characters
- Connections require bidirectional references (LinkedTo in both pins + Expression path)
- GUIDs must be unique and properly formatted
- Agent-based generation still requires careful assembly by main instance

## The Clipboard Format

The "Begin Object...End Object" format used for copy-paste in UE5:
- Based on the legacy T3D serialization format
- **T3D file import was removed** in UE4 v4.13.0 (caused crashes)
- **Clipboard paste still works** in UE5.5 - this is what we use
- Not officially documented but widely used in the community

**Key insight:** We're not using T3D files - we're generating text that gets pasted directly into the Material Editor via clipboard.

---

## Existing Tools & Approaches

### TAPython / PythonMaterialLib
**Source:** [TAColor.xyz Documentation](https://www.tacolor.xyz/Howto/Manipulate_Material_Expression_Nodes_Of_Material_With_Python_In_UE.html)

**Capabilities:**
- Export material content to JSON: `unreal.PythonMaterialLib.get_material_content(my_mat)`
- Create material expressions programmatically
- Connect nodes via `MaterialEditingLibrary`
- Get HLSL code and shader map info

**Code Example:**
```python
# Export to JSON
content_in_json = unreal.PythonMaterialLib.get_material_content(my_mat)
with open("material.json", 'w') as f:
    f.write(content_in_json)

# Create material programmatically
asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
my_mat = asset_tools.create_asset("M_CreatedByPython", "/Game/CreatedByPython",
                                   unreal.Material, unreal.MaterialFactoryNew())

# Add and connect nodes
node_tex = unreal.MaterialEditingLibrary.create_material_expression(
    my_mat, unreal.MaterialExpressionTextureSampleParameter2D,
    node_pos_x=-600, node_pos_y=0)
unreal.MaterialEditingLibrary.connect_material_expressions(
    from_expression=node_tex, to_expression=node_add, to_input_name="A")
```

**Limitation:** Runs inside UE5's Python environment only. Cannot generate clipboard-pasteable text externally.

---

### blender_t3d (GitHub)
**Source:** [github.com/crapola/blender_t3d](https://github.com/crapola/blender_t3d)

Python-based Blender add-on that can export to clipboard for pasting into UE5.

**Useful for:** Reference implementation of clipboard format generation in Python.

**Limitation:** Focused on mesh geometry, not material graphs.

---

### UE5-Clipboard Plugin
**Source:** [github.com/lasyushachan/UE5-Clipboard](https://github.com/lasyushachan/UE5-Clipboard)

UE5.4.4 plugin for copy/paste clipboard node handling.

**Confirms:** Clipboard paste format still actively used in UE5.4+

---

### JsonAsAsset Plugin
**Source:** [github.com/hengtek/JsonAsAsset-1](https://github.com/hengtek/JsonAsAsset-1)

UE5 plugin that converts JSON to Unreal Engine assets.

**Limitation:** Requires installation as UE5 plugin. Not a standalone converter.

---

### MaterialVault (2024)
**Source:** [CG Channel Article](https://www.cgchannel.com/2024/01/free-tool-materialvault-for-unreal-engine/)

Open-source material library interface for browsing/editing materials in UE5.

**Limitation:** UI tool, not a programmatic generator.

---

## Gap Analysis

| Need | Existing Solution? |
|------|-------------------|
| Generate clipboard-pasteable material nodes | **No** |
| Simple input format (YAML/JSON) → Clipboard format | **No** |
| Auto-generate unique GUIDs | **No** (manual or UE5-internal) |
| Auto-wire bidirectional connections | **No** |
| Standalone tool (no UE5 required) | **No** |

---

## Proposed Solution

Create a custom Python script that:

### Input Format (Simple YAML)
```yaml
material: M_UI_MVP_Screen
position_start: [6240, 192]

nodes:
  - name: EnterStart
    type: Constant
    value: -1.0

  - name: ExitStart
    type: Constant
    value: -1.0

  - name: Duration
    type: Constant
    value: 0.5

  - name: Overshoot
    type: Constant
    value: 0.8

  - name: AnimParams
    type: MakeFloat4
    desc: "In1_Anim : float4 (EnterStart, ExitStart, Duration, Overshoot)"
    inputs:
      X: EnterStart
      Y: ExitStart
      Z: Duration
      A: Overshoot

connections:
  - EnterStart -> AnimParams.X
  - ExitStart -> AnimParams.Y
  - Duration -> AnimParams.Z
  - Overshoot -> AnimParams.A
```

### Output: Full Clipboard Format
- Complete `Begin Object...End Object` blocks
- Auto-generated unique GUIDs
- Bidirectional `LinkedTo=` in both source and target pins
- Proper `Expression=` paths in target nodes
- `FunctionInputs` with fixed ExpressionInputId GUIDs for engine functions
- Comment bubbles (`Desc=`, `NodeComment=`, `bCommentBubbleVisible=True`)
- Calculated node positions with proper spacing

### Script Responsibilities

1. **GUID Generation**
   - Generate valid 32-char uppercase hex GUIDs
   - Track all GUIDs to ensure uniqueness
   - Use fixed GUIDs for engine functions (MakeFloat4, etc.)

2. **Connection Wiring**
   - For each connection A → B:
     - Add `LinkedTo=(B_NodeName B_PinId,)` to A's output pin
     - Add `LinkedTo=(A_NodeName A_PinId,)` to B's input pin
     - Add `Input=(Expression="...")` to B's expression property

3. **Node Templates**
   - Constant nodes
   - MakeFloat4/MakeFloat3/MakeFloat2
   - Custom HLSL nodes
   - NamedRerouteDeclaration/Usage
   - Time node
   - Comment boxes

4. **Layout Calculation**
   - Auto-position nodes in columns
   - Proper spacing (256 horizontal, 64-96 vertical)

### Skill Integration

The Claude Skill's role becomes:
1. Understand user requirements
2. Generate the simple YAML format
3. (User runs script to expand to full clipboard format)
4. User pastes into UE5 Material Editor

This separates **design decisions** (Claude) from **format generation** (script).

---

## Fixed GUIDs Reference

### MakeFloat4 ExpressionInputIds
These are constants defined by the engine function:

| Input | ExpressionInputId |
|-------|-------------------|
| X | `529C1D96441E07EB03A9E59B8A7F67B6` |
| Y | `B5BD7D1B494F6928732CCDA1C63D8E15` |
| Z | `050F17B8471570B47A802CB7CAA5A201` |
| A | `4302C68A4D3ABCFB34DE619C2867A488` |
| Result (output) | `0DD6F9954C067C3E5DDBBBA0D6910DD2` |

### MakeFloat4 MaterialFunction Path
```
/Script/Engine.MaterialFunction'/Engine/Functions/Engine_MaterialFunctions02/Utility/MakeFloat4.MakeFloat4'
```

---

## Connection Syntax Summary

### The Golden Rule
Every connection requires THREE entries:

```
Source Node Output Pin:
   LinkedTo=(TargetNodeName TargetPinId,)

Target Node Input Pin:
   LinkedTo=(SourceNodeName SourcePinId,)

Target Node Expression Property:
   Input=(Expression="/Script/Engine.[Type]'SourceNodeName.SourceExpressionName'")
```

### Expression Path Format
```
/Script/Engine.[ExpressionClass]'[NodeName].[ExpressionName]'
```

Examples:
```
/Script/Engine.MaterialExpressionConstant'MaterialGraphNode_283.MaterialExpressionConstant_EnterStart'
/Script/Engine.MaterialExpressionCustom'MaterialGraphNode_Custom_1.MaterialExpressionCustom_1'
/Script/Engine.MaterialExpressionTime'MaterialGraphNode_391.MaterialExpressionTime_1'
```

---

## Next Steps

1. **Build the Python script** - YAML → Clipboard format converter
2. **Update the Claude Skill** - Output YAML format instead of raw clipboard text
3. **Test with production examples** - Validate against existing working files
4. **Document the workflow** - User guide for the complete pipeline

---

## Sources

- [TAPython Material Manipulation](https://www.tacolor.xyz/Howto/Manipulate_Material_Expression_Nodes_Of_Material_With_Python_In_UE.html)
- [blender_t3d GitHub](https://github.com/crapola/blender_t3d) - Confirms clipboard paste works in UE5
- [UE5-Clipboard GitHub](https://github.com/lasyushachan/UE5-Clipboard) - UE5.4.4 clipboard handling
- [JsonAsAsset GitHub](https://github.com/hengtek/JsonAsAsset-1)
- [MaterialVault - CG Channel](https://www.cgchannel.com/2024/01/free-tool-materialvault-for-unreal-engine/)
