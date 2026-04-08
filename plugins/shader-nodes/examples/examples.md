# UE5 Shader Node Examples

Production examples from UI shader development.

## Example 1: Animation Ramp Function

A time-based animation ramp that returns 0→1 progress.

### HLSL Code
```hlsl
// Ramp01_FromStartAndDuration
// Inputs: StartTimeSec, DurationSec, TimeSec
// Output: 0..1 (clamped)

float startT = StartTimeSec;
float dur    = max(DurationSec, 1e-4);
float now    = TimeSec;

// If not started yet (use -1 before triggering), stay at 0
if (startT < 0.0) return 0.0;

// Progress since start, normalized and clamped
float phase = (now - startT) / dur;
return saturate(phase);
```

### Node Structure
```
Begin Object Class=/Script/UnrealEd.MaterialGraphNode_Custom Name="MaterialGraphNode_Custom_1" ExportPath="..."
   Begin Object Class=/Script/Engine.MaterialExpressionCustom Name="MaterialExpressionCustom_1" ExportPath="..."
   End Object
   Begin Object Name="MaterialExpressionCustom_1" ExportPath="..."
      Code="// Ramp01_FromStartAndDuration\r\n// Inputs: StartTimeSec, DurationSec, TimeSec\r\n// Output: 0..1 (clamped)\r\n\r\nfloat startT = StartTimeSec;\r\nfloat dur    = max(DurationSec, 1e-4);\r\nfloat now    = TimeSec;\r\n\r\n// If not started yet (use -1 before triggering), stay at 0\r\nif (startT < 0.0) return 0.0;\r\n\r\n// Progress since start, normalized and clamped\r\nfloat phase = (now - startT) / dur;\r\nreturn saturate(phase);\r\n"
      Inputs(0)=(InputName="StartTimeSec",Input=(Expression="[NamedRerouteUsage]"))
      Inputs(1)=(InputName="DurationSec",Input=(Expression="[Constant]"))
      Inputs(2)=(InputName="TimeSec",Input=(Expression="[TimeNode]"))
      ShowCode=True
      ...
   End Object
   ...
End Object
```

### Usage Pattern
- Set `StartTimeSec=-1` initially (inactive)
- When triggering, set `StartTimeSec=CurrentTime`
- Animation plays over `DurationSec` seconds
- Output: 0 (start) → 1 (complete)

---

## Example 2: SDF Size Animation with Overshoot

Advanced animation with enter/exit phases and easing.

### HLSL Code
```hlsl
// Inputs:
//   CurrentTime     : float   - Current game/UI time
//   EnterStart      : float   - When enter begins (-1 = inactive)
//   ExitStart       : float   - When exit begins (-1 = inactive)
//   AnimDuration    : float   - Duration of each phase
//   LayerDelay      : float   - Delay offset for this layer
//   StartSize       : float   - Initial size (e.g., 3.0 = beyond screen)
//   MidSize         : float   - Resting size (e.g., 1.0 = touches top/bottom)
//   EndSize         : float   - Final size (e.g., 0.0 = shrunk away)
//   OvershootAmount : float   - Overshoot intensity (0 = none, 1 = standard)

float size = MidSize;

float enterTime = EnterStart + LayerDelay;
float exitTime  = ExitStart + LayerDelay;

// Overshoot easing constants
float c1 = 1.70158 * OvershootAmount;
float c3 = c1 + 1.0;

// Exit phase: MidSize -> EndSize
if (ExitStart > -0.5 && CurrentTime >= exitTime)
{
    float t = saturate((CurrentTime - exitTime) / max(AnimDuration, 0.001));
    float eased = c3 * t * t * t - c1 * t * t;
    size = lerp(MidSize, EndSize, eased);
}
// Enter phase: StartSize -> MidSize
else if (EnterStart > -0.5 && CurrentTime >= enterTime)
{
    float t = saturate((CurrentTime - enterTime) / max(AnimDuration, 0.001));
    float tm1 = t - 1.0;
    float eased = 1.0 + c3 * tm1 * tm1 * tm1 + c1 * tm1 * tm1;
    size = lerp(StartSize, MidSize, eased);
}
// Before enter: hold at StartSize
else if (EnterStart > -0.5 && CurrentTime < enterTime)
{
    size = StartSize;
}

return size;
```

### Design Notes
- Uses -1 as "inactive" sentinel value
- LayerDelay enables staggered animations
- Overshoot easing creates bounce effect
- Can interrupt exit during enter (and vice versa)

---

## Example 3: Float4 Parameter Packing

Pack related parameters into Float4 for efficiency.

### Sector Parameters
```hlsl
// In1_Sector : float4  (StartAngle, ArcAngle, Radius, Thickness)

float StartAngle = In1_Sector.x;
float ArcAngle   = In1_Sector.y;
float Radius     = In1_Sector.z;
float Thickness  = In1_Sector.w;
```

### Atlas Parameters
```hlsl
// In2_Atlas : float4  (Cols, Rows, IconIndex, CellPadFrac)

float Cols        = In2_Atlas.x;
float Rows        = In2_Atlas.y;
float IconIndex   = In2_Atlas.z;
float CellPadFrac = In2_Atlas.w;
```

### Animation Parameters
```hlsl
// In6_Anim : float4  (ExpandStart, CollapseStart, AnimDuration, RadiusMagnitude)

float ExpandStart   = In6_Anim.x;
float CollapseStart = In6_Anim.y;
float AnimDuration  = In6_Anim.z;
float RadiusMag     = In6_Anim.w;
```

### Node Input Definition
```
Inputs(0)=(InputName="In0_Screen",Input=(Expression="..."))
Inputs(1)=(InputName="In1_Sector",Input=(Expression="..."))
Inputs(2)=(InputName="In2_Atlas",Input=(Expression="..."))
Inputs(3)=(InputName="In3_Icon",Input=(Expression="..."))
Inputs(4)=(InputName="In4_Shared2",Input=(Expression="..."))
Inputs(5)=(InputName="In5_Bias",Input=(Expression="..."))
Inputs(6)=(InputName="In6_Anim",Input=(Expression="..."))
Inputs(7)=(InputName="In7_Time",Input=(Expression="..."))
```

---

## Example 4: Multiple Output Custom Node

Custom node with main return + additional outputs.

### HLSL Structure
```hlsl
// Returns: float2 (atlas UV)
// Additional Outputs:
//   IconMask     : float
//   IconCenterUV : float2
//   LocalUV      : float2
//   IconSizeUV   : float

// ... calculation logic ...

// Assign additional outputs
IconMask     = iconMask;
IconCenterUV = iconCenterUV;
LocalUV      = localUV;
IconSizeUV   = iconSize;

// Main return
return atlasUV;
```

### Node Definition
```
AdditionalOutputs(0)=(OutputName="IconMask")
AdditionalOutputs(1)=(OutputName="IconCenterUV",OutputType=CMOT_Float2)
AdditionalOutputs(2)=(OutputName="LocalUV",OutputType=CMOT_Float2)
AdditionalOutputs(3)=(OutputName="IconSizeUV")
bShowOutputNameOnPin=True
Outputs(0)=(OutputName="return")
Outputs(1)=(OutputName="IconMask")
Outputs(2)=(OutputName="IconCenterUV")
Outputs(3)=(OutputName="LocalUV")
Outputs(4)=(OutputName="IconSizeUV")
```

---

## Example 5: Comment Box Organization

Group related nodes with colored comment boxes.

```
Begin Object Class=/Script/UnrealEd.MaterialGraphNode_Comment Name="MaterialGraphNode_Comment_48" ExportPath="..."
   Begin Object Class=/Script/Engine.MaterialExpressionComment Name="MaterialExpressionComment_9" ExportPath="..."
   End Object
   Begin Object Name="MaterialExpressionComment_9" ExportPath="..."
      SizeX=1070
      SizeY=540
      Text="StartAnimation"
      CommentColor=(R=0.424721,G=0.696296,B=1.000000,A=1.000000)
      bCommentBubbleVisible_InDetailsPanel=True
      bColorCommentBubble=True
      MaterialExpressionEditorX=-2880
      MaterialExpressionEditorY=-448
      MaterialExpressionGuid=[GUID]
      Material="[MaterialPath]"
   End Object
   MaterialExpressionComment="/Script/Engine.MaterialExpressionComment'MaterialExpressionComment_9'"
   CommentColor=(R=0.424721,G=0.696296,B=1.000000,A=1.000000)
   bColorCommentBubble=True
   NodePosX=-2880
   NodePosY=-448
   NodeWidth=1070
   NodeHeight=540
   NodeComment="StartAnimation"
   NodeGuid=[GUID]
End Object
```

### Position Notes
- Comment box position is top-left corner
- SizeX/SizeY define the box dimensions
- NodeWidth/NodeHeight mirror SizeX/SizeY
- Place at Y-50 above the content nodes

---

## Example 6: Material Function Input

Function input with type and sort priority.

```
Begin Object Class=/Script/UnrealEd.MaterialGraphNode Name="MaterialGraphNode_4" ExportPath="..."
   Begin Object Class=/Script/Engine.MaterialExpressionFunctionInput Name="MaterialExpressionFunctionInput_1" ExportPath="..."
   End Object
   Begin Object Name="MaterialExpressionFunctionInput_1" ExportPath="..."
      InputName="Sector"
      Id=689537234327F38E560E46912C74D1B9
      InputType=FunctionInput_Vector4
      SortPriority=10
      MaterialExpressionEditorX=-576
      MaterialExpressionEditorY=-208
      MaterialExpressionGuid=[GUID]
      Material="[MaterialPath]"
      bCollapsed=True
   End Object
   ...
End Object
```

### Sort Priority
- Lower values appear first in the function call node
- Use increments of 10 for easy insertion later
- Example: 0, 10, 20, 30...

---

## Layout Guidelines

### Node Spacing
- Horizontal: 256 units between nodes
- Vertical: 128 units between rows
- Group related nodes in columns

### Common Positions
```
Input Parameters:    X = -1024 to -768
Processing Nodes:    X = -512 to 0
Output Nodes:        X = 256 to 512
```

### Comment Box Sizing
- Small (2-3 nodes): SizeX=400, SizeY=200
- Medium (4-6 nodes): SizeX=700, SizeY=350
- Large (7+ nodes): SizeX=1000+, SizeY=500+
