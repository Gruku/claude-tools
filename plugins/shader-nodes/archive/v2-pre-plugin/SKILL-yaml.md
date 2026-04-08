---
name: ue5-shader-yaml
description: Generate UE5 Material Graph nodes from shader code or descriptions. Outputs ready-to-paste UE5 clipboard format. Use this for custom HLSL nodes, animation systems, or any material graph setup.
user-invocable: true
argument-hint: [shader code or description]
---

# UE5 Shader Node Generator

Generate material graph nodes ready to paste into UE5 Material Editor.

## Workflow

1. **You provide**: Shader code or description of what you need
2. **Claude generates**: YAML definition internally
3. **Claude runs**: Python script to convert to UE5 format
4. **Claude outputs**: Ready-to-paste clipboard format
5. **You paste**: Ctrl+V in UE5 Material Editor

## IMPORTANT: Execution Steps

When generating nodes, Claude MUST:

1. **Write YAML** to `ue5_nodes.yaml` in the working directory
2. **Run the converter script** with output to file:
   ```bash
   python ~/.claude/skills/ue5-custom-shader-nodes/ue5_material_generator.py ue5_nodes.yaml -o ue5_clipboard.txt
   ```
3. **Confirm to user**: "Output written to `ue5_clipboard.txt` - open and copy contents to paste into UE5"

## Output Files (always created)

- `ue5_nodes.yaml` - Human-readable node definition (can edit and re-run)
- `ue5_clipboard.txt` - Ready to copy-paste into UE5 Material Editor

## Script Location

```
~/.claude/skills/ue5-custom-shader-nodes/ue5_material_generator.py
```

## Requirements

Ensure pyyaml is installed:
```bash
pip install pyyaml
```

---

## Available Node Types

### Built-in Types (special handling)
- `Constant` - Scalar float
- `Constant3Vector` - RGB/Vector3
- `Constant4Vector` - RGBA/Vector4
- `Time` - Game time
- `MakeFloat2`, `MakeFloat3`, `MakeFloat4` - Pack scalars
- `Custom` - HLSL code
- `NamedRerouteDeclaration` - Named variable
- `Comment` - Comment box
- `Generic` - Full flexibility (define any node)

### Registry Types (extensible via node_registry.yaml)

**Math:**
`Add`, `Subtract`, `Multiply`, `Divide`, `Power`, `SquareRoot`, `Abs`, `Negate`, `OneMinus`, `Fmod`, `Floor`, `Ceil`, `Frac`, `Round`, `Min`, `Max`

**Interpolation:**
`Lerp`, `Clamp`, `Saturate`, `Smoothstep`, `Step`

**Trigonometry:**
`Sine`, `Cosine`, `Tangent`, `Arcsine`, `Arccosine`, `Arctangent`, `Arctangent2`

**Vector:**
`DotProduct`, `CrossProduct`, `Normalize`, `Length`, `Distance`, `AppendVector`, `ComponentMask`

**Comparison:**
`If`

**Coordinates:**
`TextureCoordinate`, `ScreenPosition`, `ViewSize`, `PixelPosition`, `WorldPosition`, `ObjectPosition`, `ActorPosition`, `CameraPosition`

**Texture:**
`TextureSample`, `TextureObject`

**Parameters:**
`ScalarParameter`, `VectorParameter`

**Derivatives:**
`DDX`, `DDY`

**Noise:**
`Noise`

---

## YAML Format Reference

### Basic Structure
```yaml
material_path: "/Script/UnrealEd.PreviewMaterial'/Engine/Transient.M_MyMaterial'"
position_start: [6240, 192]    # Top-left origin for the graph
spacing_x: 256                 # Horizontal spacing between columns
spacing_y: 96                  # Vertical spacing between nodes in a column

nodes:
  - name: NodeName
    type: NodeType
    # ... type-specific properties

connections:
  - SourceNode -> TargetNode.InputPin
```

**Layout behavior:** Nodes are auto-positioned into columns by graph depth. Constants/inputs go in column 0, their consumers in column 1, etc. Non-leaf nodes are vertically centered relative to their inputs. Override with per-node `pos_x`/`pos_y`.

---

## Node Examples

### Constant (Scalar)
```yaml
- name: MyValue
  type: Constant
  value: 0.5
  desc: "Optional comment bubble"
```

### Constant3Vector (RGB)
```yaml
- name: MyColor
  type: Constant3Vector
  value: [1.0, 0.5, 0.2]
```

### Time
```yaml
- name: CurrentTime
  type: Time
  ignore_pause: false
```

### MakeFloat4
```yaml
- name: PackedParams
  type: MakeFloat4
  desc: "float4(X, Y, Z, W)"
```

### Math Nodes (Registry)
```yaml
- name: Result
  type: Multiply  # or Add, Divide, Lerp, etc.
  const_a: 1.0    # default value if A not connected
  const_b: 2.0    # default value if B not connected
  desc: "A * B"
```

### Lerp
```yaml
- name: BlendResult
  type: Lerp
  const_a: 0.0
  const_b: 1.0
  const_alpha: 0.5
```

### NamedRerouteDeclaration
```yaml
- name: OutputVar
  type: NamedRerouteDeclaration
  var_name: "MyOutput"
  color: [0.2, 0.8, 0.3]
```

### Custom HLSL
```yaml
- name: MyLogic
  type: Custom
  output_type: CMOT_Float4
  desc: "Calculates something"
  inputs:
    - name: InputA
    - name: InputB
  additional_outputs:
    - name: SecondOutput
      type: CMOT_Float2
  code: |
    float result = InputA * InputB.x;
    return float4(result, result, result, 1);
```

### Generic (Full Flexibility)
For nodes not in the registry:
```yaml
- name: MyNode
  type: Generic
  expression_class: MaterialExpressionSomeNewNode
  inputs:
    - name: Input1
      category: required
    - name: Input2
      category: optional
  outputs:
    - name: Output
  properties:
    SomeProperty: 1.0
    AnotherProperty: "value"
```

### Comment Box
```yaml
- name: Section1
  type: Comment
  text: "Animation System"
  size_x: 800
  size_y: 400
  color: [0.2, 0.3, 0.4]
```

---

## Connection Syntax

```yaml
connections:
  # Default output to default input
  - ConstantNode -> MultiplyNode

  # Specific pins
  - ConstantA -> MultiplyNode.A
  - ConstantB -> MultiplyNode.B

  # Named outputs
  - CustomNode.SecondOutput -> NextNode
```

---

## Extending the Registry

To add new node types, edit `~/.claude/skills/ue5-custom-shader-nodes/node_registry.yaml`:

```yaml
MyNewNode:
  expression_class: MaterialExpressionMyNewNode
  inputs:
    - name: Input1
      category: required
    - name: Input2
      category: optional
  outputs:
    - name: Output
  properties:
    DefaultProp: 1.0
  property_mappings:
    yaml_key: UE5PropertyName
```

**Ask Claude to add new node definitions** when you encounter nodes not in the registry.

---

## Complete Example

```yaml
material_path: "/Script/UnrealEd.PreviewMaterial'/Engine/Transient.M_Example'"
position_start: [1000, 100]
spacing_y: 100

nodes:
  - name: ValueA
    type: Constant
    value: 0.5

  - name: ValueB
    type: Constant
    value: 2.0

  - name: MultResult
    type: Multiply
    desc: "A * B"

  - name: AddOffset
    type: Add
    const_b: 0.1

  - name: FinalClamp
    type: Saturate

  - name: Output
    type: NamedRerouteDeclaration
    var_name: "Result"
    color: [0.8, 0.4, 0.1]

connections:
  - ValueA -> MultResult.A
  - ValueB -> MultResult.B
  - MultResult -> AddOffset.A
  - AddOffset -> FinalClamp
  - FinalClamp -> Output
```

---

## Output

When asked to create shader nodes:

1. Write YAML to `ue5_nodes.yaml`
2. Run script to generate `ue5_clipboard.txt`
3. Tell user: "Open `ue5_clipboard.txt`, copy all, paste into UE5 Material Editor"

Files are always saved in the current working directory.
