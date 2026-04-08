# Custom HLSL Node Template

Complete template for generating Custom HLSL nodes with inputs and multiple outputs.

## Minimal Custom Node

```
Begin Object Class=/Script/UnrealEd.MaterialGraphNode_Custom Name="MaterialGraphNode_Custom_[N]" ExportPath="/Script/UnrealEd.MaterialGraphNode_Custom'/Engine/Transient.[MaterialName]:MaterialGraph_0.MaterialGraphNode_Custom_[N]'"
   Begin Object Class=/Script/Engine.MaterialExpressionCustom Name="MaterialExpressionCustom_[N]" ExportPath="/Script/Engine.MaterialExpressionCustom'/Engine/Transient.[MaterialName]:MaterialGraph_0.MaterialGraphNode_Custom_[N].MaterialExpressionCustom_[N]'"
   End Object
   Begin Object Name="MaterialExpressionCustom_[N]" ExportPath="/Script/Engine.MaterialExpressionCustom'/Engine/Transient.[MaterialName]:MaterialGraph_0.MaterialGraphNode_Custom_[N].MaterialExpressionCustom_[N]'"
      Code="[HLSL_CODE]"
      Description="[NODE_TITLE]"
      OutputType=[OUTPUT_TYPE]
      Inputs(0)=(InputName="[INPUT_NAME]",Input=(Expression="[SOURCE_EXPRESSION_PATH]"))
      ShowCode=True
      MaterialExpressionEditorX=[X]
      MaterialExpressionEditorY=[Y]
      MaterialExpressionGuid=[GUID1]
      Material="/Script/UnrealEd.PreviewMaterial'/Engine/Transient.[MaterialName]'"
   End Object
   MaterialExpression="/Script/Engine.MaterialExpressionCustom'MaterialExpressionCustom_[N]'"
   NodePosX=[X]
   NodePosY=[Y]
   NodeGuid=[GUID2]
   CustomProperties Pin (PinId=[INPUT_PIN_GUID],PinName="[INPUT_NAME]",PinType.PinCategory="required",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,LinkedTo=([SOURCE_NODE] [SOURCE_PIN],),PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False,)
   CustomProperties Pin (PinId=[OUTPUT_PIN_GUID],PinName="Output",PinFriendlyName=NSLOCTEXT("MaterialGraphNode", "Space", " "),Direction="EGPD_Output",PinType.PinCategory="",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,LinkedTo=([TARGET_NODE] [TARGET_PIN],),PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False,)
End Object
```

## Custom Node with Multiple Outputs

```
Begin Object Class=/Script/UnrealEd.MaterialGraphNode_Custom Name="MaterialGraphNode_Custom_[N]" ExportPath="/Script/UnrealEd.MaterialGraphNode_Custom'/Engine/Transient.[MaterialName]:MaterialGraph_0.MaterialGraphNode_Custom_[N]'"
   Begin Object Class=/Script/Engine.MaterialExpressionCustom Name="MaterialExpressionCustom_[N]" ExportPath="/Script/Engine.MaterialExpressionCustom'/Engine/Transient.[MaterialName]:MaterialGraph_0.MaterialGraphNode_Custom_[N].MaterialExpressionCustom_[N]'"
   End Object
   Begin Object Name="MaterialExpressionCustom_[N]" ExportPath="/Script/Engine.MaterialExpressionCustom'/Engine/Transient.[MaterialName]:MaterialGraph_0.MaterialGraphNode_Custom_[N].MaterialExpressionCustom_[N]'"
      Code="// Header comment documenting inputs/outputs\r\n// Input0: Description\r\n// Output: Description\r\n// Additional Output 'Name': Description\r\n\r\n[HLSL_CODE]\r\n\r\n// Assign additional outputs\r\n[OUTPUT_NAME] = [value];\r\n\r\nreturn [main_return_value];"
      Description="[NODE_TITLE]"
      OutputType=[MAIN_OUTPUT_TYPE]
      Inputs(0)=(InputName="[INPUT0_NAME]",Input=(Expression="[SOURCE0_PATH]"))
      Inputs(1)=(InputName="[INPUT1_NAME]",Input=(Expression="[SOURCE1_PATH]"))
      AdditionalOutputs(0)=(OutputName="[EXTRA_OUTPUT1_NAME]")
      AdditionalOutputs(1)=(OutputName="[EXTRA_OUTPUT2_NAME]",OutputType=CMOT_Float2)
      ShowCode=True
      MaterialExpressionEditorX=[X]
      MaterialExpressionEditorY=[Y]
      MaterialExpressionGuid=[GUID1]
      Material="/Script/UnrealEd.PreviewMaterial'/Engine/Transient.[MaterialName]'"
      bShowOutputNameOnPin=True
      Outputs(0)=(OutputName="return")
      Outputs(1)=(OutputName="[EXTRA_OUTPUT1_NAME]")
      Outputs(2)=(OutputName="[EXTRA_OUTPUT2_NAME]")
   End Object
   MaterialExpression="/Script/Engine.MaterialExpressionCustom'MaterialExpressionCustom_[N]'"
   NodePosX=[X]
   NodePosY=[Y]
   NodeGuid=[GUID2]
   CustomProperties Pin (PinId=[INPUT0_PIN],PinName="[INPUT0_NAME]",PinType.PinCategory="required"...)
   CustomProperties Pin (PinId=[INPUT1_PIN],PinName="[INPUT1_NAME]",PinType.PinCategory="required"...)
   CustomProperties Pin (PinId=[RETURN_PIN],PinName="return",Direction="EGPD_Output"...)
   CustomProperties Pin (PinId=[OUTPUT1_PIN],PinName="[EXTRA_OUTPUT1_NAME]",Direction="EGPD_Output"...)
   CustomProperties Pin (PinId=[OUTPUT2_PIN],PinName="[EXTRA_OUTPUT2_NAME]",Direction="EGPD_Output"...)
End Object
```

## Output Type Reference

| Type | Value | Use Case |
|------|-------|----------|
| Scalar | `CMOT_Float1` | Single float, alpha, mask |
| Vector2 | `CMOT_Float2` | UV coordinates, 2D vectors |
| Vector3 | `CMOT_Float3` | RGB color, 3D position |
| Vector4 | `CMOT_Float4` | RGBA, packed parameters |

## HLSL Code Formatting

- Use `\r\n` for line breaks
- Escape quotes if needed
- Document inputs at the top as comments
- Use proper indentation with spaces (not tabs)

Example formatted code:
```
"// MyNode - Description\r\n// Inputs:\r\n//   Value : float - Input value\r\n// Returns: float - Processed value\r\n\r\nfloat result = Value * 2.0;\r\nreturn saturate(result);"
```

## Placeholder Reference

| Placeholder | Description |
|-------------|-------------|
| `[N]` | Node index number |
| `[MaterialName]` | Material asset name (e.g., `M_UI_MVP_Screen`) |
| `[GUID1]`, `[GUID2]` | 32-char uppercase hex GUIDs |
| `[X]`, `[Y]` | Node position in editor |
| `[HLSL_CODE]` | HLSL code with `\r\n` line endings |
| `[NODE_TITLE]` | Display name for the node |
| `[INPUT_NAME]` | Name of input pin |
| `[OUTPUT_TYPE]` | `CMOT_Float1`, `CMOT_Float2`, etc. |
| `[SOURCE_EXPRESSION_PATH]` | Full path to source expression |
| `[SOURCE_NODE]` | Source node name |
| `[SOURCE_PIN]` | Source pin GUID |
