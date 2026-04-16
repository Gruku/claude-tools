# SDF Antialiasing in UE5 UI Shaders

## The Rule

**Do NOT apply antialiasing inside Custom HLSL nodes.**

Custom nodes should output **raw SDF values**. Antialiasing is handled by the `MF_UI_SDF_AntiAliasedStep` Material Function node, placed after the Custom node in the material graph.

## MF_UI_SDF_AntiAliasedStep

A Material Function that takes a raw SDF and produces an antialiased mask.

**Path:** `/Game/UI/_Common/_Materials/_MaterialFunctions/MF_UI_SDF_AntiAliasedStep`

**Inputs:**
| Pin | Type | Category | Description |
|-----|------|----------|-------------|
| SDF | Scalar | required | Raw signed distance field value |
| Offset | Scalar | optional | Threshold offset (default 0) |

**Output:**
| Pin | Type | Description |
|-----|------|-------------|
| Result | Scalar | Antialiased mask (0 or 1 with smooth edge) |

## How It Fits in the Graph

```
[Custom HLSL Node]
    ├── Main output (color/float4) → ...
    └── SDF output (raw float) → [MF_UI_SDF_AntiAliasedStep] → Mask
                                         ↑
                                  [Offset Constant] (optional)
```

The Node Generator should place this Material Function call node after each SDF output from Custom nodes.

## HLSL Implications

**In your Custom HLSL code:**
- Output raw SDF values as additional outputs (e.g., `SDFMask`, `BorderSDF`)
- Do NOT call `fwidth()`, `ddx()`, `ddy()`, or `smoothstep()` for edge AA
- Do NOT apply `1.0 - smoothstep(...)` patterns for SDF edges
- Use `step()` freely for internal non-visible calculations

**Example — correct approach:**
```hlsl
// Custom node outputs raw SDF
float circleSDF = length(uv - 0.5) - radius;
SDFMask = circleSDF;  // Additional output — raw, no AA

return float4(color, 1.0);
// AA is applied by MF_UI_SDF_AntiAliasedStep in the graph
```

**Example — WRONG (old approach, do not use):**
```hlsl
// DON'T do this — AA belongs in the graph, not HLSL
float AA = fwidth(circleSDF);
float mask = 1.0 - smoothstep(-AA, AA, circleSDF);
```

## UE5 Node Structure Reference

The Material Function call node for copy-paste reference:

```
Begin Object Class=/Script/UnrealEd.MaterialGraphNode Name="MaterialGraphNode_AAStep"
   Begin Object Class=/Script/Engine.MaterialExpressionMaterialFunctionCall Name="MaterialExpressionMaterialFunctionCall_AAStep"
   End Object
   Begin Object Name="MaterialExpressionMaterialFunctionCall_AAStep"
      MaterialFunction="/Script/Engine.MaterialFunction'/Game/UI/_Common/_Materials/_MaterialFunctions/MF_UI_SDF_AntiAliasedStep.MF_UI_SDF_AntiAliasedStep'"
      FunctionInputs(0)=(ExpressionInputId=CD8D4C304B7C5834BCE9D0B68D9EBABF,Input=(InputName="SDF"))
      FunctionInputs(1)=(ExpressionInputId=331D83DD4732738FE4AEB68BBF52EBCF,Input=(InputName="Offset"))
      FunctionOutputs(0)=(ExpressionOutputId=316498974FE1CAA2A690E68BC0EB4CF3,Output=(OutputName="Result"))
   End Object
   MaterialExpression="/Script/Engine.MaterialExpressionMaterialFunctionCall'MaterialExpressionMaterialFunctionCall_AAStep'"
   CustomProperties Pin (PinId=...,PinName="SDF (S)",PinType.PinCategory="required",...)
   CustomProperties Pin (PinId=...,PinName="Offset (S)",PinType.PinCategory="optional",...)
   CustomProperties Pin (PinId=...,PinName="Result",Direction="EGPD_Output",...)
End Object
```

**Fixed ExpressionInputIds** (these are constants defined by the Material Function):
- SDF input: `CD8D4C304B7C5834BCE9D0B68D9EBABF`
- Offset input: `331D83DD4732738FE4AEB68BBF52EBCF`
- Result output: `316498974FE1CAA2A690E68BC0EB4CF3`

## Compositing (Still Relevant)

After getting antialiased masks from `MF_UI_SDF_AntiAliasedStep`, compositing rules still apply:

**Color compositing (in HLSL or graph):**
```hlsl
float3 color = background;
color = lerp(color, layer1_color, layer1_mask);
color = lerp(color, layer2_color, layer2_mask);
```

**Pre-multiply color by alpha for correct edge blending:**
```hlsl
Output.RGB = color * alpha;
Output.A = alpha;
```

## Texture Settings (Still Relevant)

**Disable sRGB for:**
- Distance fields, gradients, masks, any texture used for math

**Enable mip maps for:**
- Icons and UI elements that scale dynamically
