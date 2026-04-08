# UE5 Material Node Type Reference

Complete specification for all material graph node types.

## Node Structure Anatomy

Every material node follows this hierarchy:

```
Begin Object Class=/Script/UnrealEd.MaterialGraphNode[_Type] Name="[NodeName]" ExportPath="[Path]"
   Begin Object Class=/Script/Engine.MaterialExpression[Type] Name="[ExpressionName]" ExportPath="[Path]"
   End Object
   Begin Object Name="[ExpressionName]" ExportPath="[Path]"
      [Expression Properties]
   End Object
   MaterialExpression="[ExpressionPath]"
   [Node Properties]
   CustomProperties Pin ([Pin Properties])
End Object
```

---

## Constant Nodes

### MaterialExpressionConstant (Scalar)
Single float value.

```
Class: /Script/UnrealEd.MaterialGraphNode
Expression: /Script/Engine.MaterialExpressionConstant

Properties:
   R=[float]                    // The constant value
   MaterialExpressionEditorX=[int]
   MaterialExpressionEditorY=[int]
   MaterialExpressionGuid=[GUID]
   Material="[MaterialPath]"

Output Pin:
   PinName="Output"
   PinType.PinCategory=""
   Direction="EGPD_Output"
```

### MaterialExpressionConstant3Vector (Color/Vector3)
RGB or Vector3 value.

```
Class: /Script/UnrealEd.MaterialGraphNode
Expression: /Script/Engine.MaterialExpressionConstant3Vector

Properties:
   Constant=(R=[float],G=[float],B=[float],A=0.000000)
   MaterialExpressionEditorX=[int]
   MaterialExpressionEditorY=[int]
   MaterialExpressionGuid=[GUID]
   Material="[MaterialPath]"

Output Pins:
   PinName="Output" (RGB)
   PinName="R", PinType.PinSubCategory="red"
   PinName="G", PinType.PinSubCategory="green"
   PinName="B", PinType.PinSubCategory="blue"
```

### MaterialExpressionConstant4Vector (RGBA/Vector4)
RGBA or Vector4 value.

```
Properties:
   Constant=(R=[float],G=[float],B=[float],A=[float])
```

---

## Named Reroute System

### MaterialExpressionNamedRerouteDeclaration
Declares a named variable (setter).

```
Class: /Script/UnrealEd.MaterialGraphNode
Expression: /Script/Engine.MaterialExpressionNamedRerouteDeclaration

Properties:
   Input=(Expression="[SourceExpression]")
   Name="[VariableName]"
   NodeColor=(R=[float],G=[float],B=[float],A=1.000000)
   VariableGuid=[GUID]
   MaterialExpressionEditorX=[int]
   MaterialExpressionEditorY=[int]
   MaterialExpressionGuid=[GUID]
   Material="[MaterialPath]"

Node Properties:
   bCanRenameNode=True

Pins:
   Input: PinType.PinCategory="required"
   Output: Direction="EGPD_Output"
```

### MaterialExpressionNamedRerouteUsage
Uses a named variable (getter).

```
Class: /Script/UnrealEd.MaterialGraphNode
Expression: /Script/Engine.MaterialExpressionNamedRerouteUsage

Properties:
   Declaration="[DeclarationPath]"
   DeclarationGuid=[MatchingVariableGuid]
   MaterialExpressionEditorX=[int]
   MaterialExpressionEditorY=[int]
   MaterialExpressionGuid=[GUID]
   Material="[MaterialPath]"

Output Pin:
   Direction="EGPD_Output"
```

---

## Custom HLSL Node

### MaterialExpressionCustom
Executes custom HLSL code.

```
Class: /Script/UnrealEd.MaterialGraphNode_Custom
Expression: /Script/Engine.MaterialExpressionCustom

Properties:
   Code="[HLSL Code with \r\n line endings]"
   Description="[Node Title]"
   OutputType=CMOT_Float1|CMOT_Float2|CMOT_Float3|CMOT_Float4

   Inputs(0)=(InputName="[Name]",Input=(Expression="[SourcePath]"))
   Inputs(1)=(InputName="[Name]",Input=(Expression="[SourcePath]"))
   ...

   AdditionalOutputs(0)=(OutputName="[Name]")
   AdditionalOutputs(1)=(OutputName="[Name]",OutputType=CMOT_Float2)
   ...

   ShowCode=True|False
   MaterialExpressionEditorX=[int]
   MaterialExpressionEditorY=[int]
   MaterialExpressionGuid=[GUID]
   Material="[MaterialPath]"
   bShowOutputNameOnPin=True|False

   Outputs(0)=(OutputName="return")
   Outputs(1)=(OutputName="[AdditionalOutput1]")
   ...

Input Pins:
   PinType.PinCategory="required"

Output Pins:
   PinName="[OutputName]"
   Direction="EGPD_Output"
```

**Output Types:**
- `CMOT_Float1` - Scalar
- `CMOT_Float2` - Vector2
- `CMOT_Float3` - Vector3/RGB
- `CMOT_Float4` - Vector4/RGBA
- `CMOT_MaterialAttributes` - Material attributes

---

## Function Nodes

### MaterialExpressionFunctionInput
Input parameter for a Material Function.

```
Class: /Script/UnrealEd.MaterialGraphNode
Expression: /Script/Engine.MaterialExpressionFunctionInput

Properties:
   InputName="[Name]"
   Id=[GUID]
   InputType=FunctionInput_Scalar|FunctionInput_Vector2|FunctionInput_Vector3|FunctionInput_Vector4|FunctionInput_Texture2D
   SortPriority=[int]  // Order in function call
   Preview=(Expression="[OptionalPreviewExpression]")
   bCollapsed=True|False
   MaterialExpressionEditorX=[int]
   MaterialExpressionEditorY=[int]
   MaterialExpressionGuid=[GUID]
   Material="[MaterialPath]"

Pins:
   Input: PinName="Preview" (optional preview connection)
   Output: Direction="EGPD_Output"
```

**Input Types:**
- `FunctionInput_Scalar` - float
- `FunctionInput_Vector2` - float2
- `FunctionInput_Vector3` - float3
- `FunctionInput_Vector4` - float4
- `FunctionInput_Texture2D` - Texture object
- `FunctionInput_TextureCube` - Cubemap
- `FunctionInput_StaticBool` - Static bool

### MaterialExpressionMaterialFunctionCall
Calls another Material Function.

```
Class: /Script/UnrealEd.MaterialGraphNode
Expression: /Script/Engine.MaterialExpressionMaterialFunctionCall

Properties:
   MaterialFunction="[FunctionAssetPath]"
   FunctionInputs(0)=(ExpressionInputId=[GUID],Input=(Expression="[SourcePath]",InputName="[Name]"))
   FunctionOutputs(0)=(ExpressionOutputId=[GUID],Output=(OutputName="[Name]"))
   MaterialExpressionEditorX=[int]
   MaterialExpressionEditorY=[int]
   MaterialExpressionGuid=[GUID]
   Material="[MaterialPath]"
   Desc="[Comment Text]"              // Shows in comment bubble
   bCommentBubbleVisible=True         // Enable comment bubble
   Outputs(0)=(OutputName="[Name]")

Node Properties (outer):
   bCommentBubbleVisible=True
   NodeComment="[Comment Text]"       // Must match Desc
```

**Use for documenting Float4 packing:**
```
Desc="In1_Shape : float4 (AspectRatio, StarRadius, InnerRatio, Points)"
```

---

## Math Nodes

### MaterialExpressionMultiply
```
Expression: /Script/Engine.MaterialExpressionMultiply

Properties:
   A=(Expression="[SourceA]")
   B=(Expression="[SourceB]")
   ConstA=[float]  // Default if A not connected
   ConstB=[float]  // Default if B not connected
```

### MaterialExpressionAdd
```
Expression: /Script/Engine.MaterialExpressionAdd

Properties:
   A=(Expression="[SourceA]")
   B=(Expression="[SourceB]")
   ConstA=[float]
   ConstB=[float]
```

### MaterialExpressionLinearInterpolate (Lerp)
```
Expression: /Script/Engine.MaterialExpressionLinearInterpolate

Properties:
   A=(Expression="[SourceA]")
   B=(Expression="[SourceB]")
   Alpha=(Expression="[AlphaSource]")
   ConstA=[float]
   ConstB=[float]
   ConstAlpha=[float]
```

---

## Texture Nodes

### MaterialExpressionTextureSample
```
Class: /Script/UnrealEd.MaterialGraphNode
Expression: /Script/Engine.MaterialExpressionTextureSample

Properties:
   Coordinates=(Expression="[UVSource]")
   TextureObject=(Expression="[TextureObjectSource]")
   Texture="[TextureAssetPath]"
   SamplerType=SAMPLERTYPE_Color|SAMPLERTYPE_Grayscale|SAMPLERTYPE_Alpha|...
   MaterialExpressionEditorX=[int]
   MaterialExpressionEditorY=[int]
   MaterialExpressionGuid=[GUID]
   Material="[MaterialPath]"

Input Pins:
   PinName="UVs"
   PinName="Tex"

Output Pins:
   PinName="RGB", PinType.PinSubCategory="mask"
   PinName="R", PinType.PinSubCategory="red"
   PinName="G", PinType.PinSubCategory="green"
   PinName="B", PinType.PinSubCategory="blue"
   PinName="A", PinType.PinSubCategory="alpha"
   PinName="RGBA", PinType.PinSubCategory="rgba"
```

### MaterialExpressionTextureObject
Passes a texture as an object reference.

```
Expression: /Script/Engine.MaterialExpressionTextureObject

Properties:
   Texture="[TextureAssetPath]"
   SamplerType=SAMPLERTYPE_Color|...
```

---

## Utility Nodes

### MaterialExpressionTime
Current game time.

```
Expression: /Script/Engine.MaterialExpressionTime

Properties:
   bIgnorePause=True|False
   bOverride_Period=True|False
   Period=[float]
```

### MaterialExpressionComment
Comment box for organization.

```
Class: /Script/UnrealEd.MaterialGraphNode_Comment
Expression: /Script/Engine.MaterialExpressionComment

Properties:
   SizeX=[int]
   SizeY=[int]
   Text="[Comment Text]"
   CommentColor=(R=[float],G=[float],B=[float],A=1.000000)
   bCommentBubbleVisible_InDetailsPanel=True|False
   bColorCommentBubble=True|False
   MaterialExpressionEditorX=[int]
   MaterialExpressionEditorY=[int]
   MaterialExpressionGuid=[GUID]
   Material="[MaterialPath]"

Node Properties:
   CommentColor=(R=[float],G=[float],B=[float],A=1.000000)
   bColorCommentBubble=True|False
   NodeWidth=[int]
   NodeHeight=[int]
   NodeComment="[Comment Text]"
```

---

## Pin Properties Reference

### Common Pin Properties

```
CustomProperties Pin (
   PinId=[GUID],
   PinName="[Name]",
   PinFriendlyName=NSLOCTEXT("MaterialGraphNode", "Space", " "),
   Direction="EGPD_Input"|"EGPD_Output",
   PinType.PinCategory="required"|"optional"|"mask"|"",
   PinType.PinSubCategory=""|"red"|"green"|"blue"|"alpha"|"rgba"|"byte",
   PinType.PinSubCategoryObject=None|"[EnumPath]",
   PinType.PinSubCategoryMemberReference=(),
   PinType.PinValueType=(),
   PinType.ContainerType=None,
   PinType.bIsReference=False,
   PinType.bIsConst=False,
   PinType.bIsWeakPointer=False,
   PinType.bIsUObjectWrapper=False,
   PinType.bSerializeAsSinglePrecisionFloat=False,
   DefaultValue="[Value]",
   LinkedTo=([TargetNode] [TargetPinId],...),
   PersistentGuid=00000000000000000000000000000000,
   bHidden=False,
   bNotConnectable=False|True,
   bDefaultValueIsReadOnly=False,
   bDefaultValueIsIgnored=False,
   bAdvancedView=False|True,
   bOrphanedPin=False
)
```

### Pin Categories
- `"required"` - Must be connected
- `"optional"` - Can use default value
- `"mask"` - Output component mask (RGB, R, G, B, A)
- `""` - Default output

---

## Node Comment Bubbles

Any node can display a comment bubble above it. Requires THREE properties:

### In the Inner Expression Object
```
Desc="[Comment Text]"
bCommentBubbleVisible=True
```

### In the Outer Node Properties
```
bCommentBubbleVisible=True
NodeComment="[Comment Text]"
```

**Example - Documenting Float4 packing:**
```
Begin Object Name="MaterialExpressionMaterialFunctionCall_1" ...
   ...
   Desc="In1_Shape : float4 (AspectRatio, StarRadius, InnerRatio, Points)"
   bCommentBubbleVisible=True
   ...
End Object
MaterialExpression="..."
NodePosX=...
NodePosY=...
bCommentBubbleVisible=True
NodeComment="In1_Shape : float4 (AspectRatio, StarRadius, InnerRatio, Points)"
NodeGuid=...
```

**Best Practice:** Use for MakeFloat4 nodes to document what each component represents.

---

## Material Path Formats

### Preview Material (in-editor)
```
"/Script/UnrealEd.PreviewMaterial'/Engine/Transient.[MaterialName]'"
```

### Saved Material
```
"/Script/Engine.Material'/Game/Path/To/M_MaterialName.M_MaterialName'"
```

### Material Function
```
"/Script/Engine.MaterialFunction'/Game/Path/To/MF_FunctionName.MF_FunctionName'"
```

### Engine Function
```
"/Script/Engine.MaterialFunction'/Engine/Functions/Engine_MaterialFunctions02/Utility/MakeFloat4.MakeFloat4'"
```
