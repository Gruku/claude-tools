# Input Constant + Named Reroute Template

Complete template for creating an input parameter as a named variable.

## Single Parameter Pattern

This creates:
1. Constant node with value
2. Named reroute declaration (setter)
3. Named reroute usage (getter) - create as many as needed

### Template

Replace placeholders:
- `[MATERIAL]` - Material name (e.g., `M_UI_MVP_Screen`)
- `[NODE_N]` - Unique node number
- `[PARAM_NAME]` - Parameter name (e.g., `CircleEnterStart`)
- `[VALUE]` - Float value (e.g., `1.000000`)
- `[X]`, `[Y]` - Node position
- `[GUID_*]` - Unique 32-char hex GUIDs
- `[R]`, `[G]`, `[B]` - Node color (0.0-1.0)

```
Begin Object Class=/Script/UnrealEd.MaterialGraphNode Name="MaterialGraphNode_[NODE_N]" ExportPath="/Script/UnrealEd.MaterialGraphNode'/Engine/Transient.[MATERIAL]:MaterialGraph_0.MaterialGraphNode_[NODE_N]'"
   Begin Object Class=/Script/Engine.MaterialExpressionConstant Name="MaterialExpressionConstant_[PARAM_NAME]" ExportPath="/Script/Engine.MaterialExpressionConstant'/Engine/Transient.[MATERIAL]:MaterialGraph_0.MaterialGraphNode_[NODE_N].MaterialExpressionConstant_[PARAM_NAME]'"
   End Object
   Begin Object Name="MaterialExpressionConstant_[PARAM_NAME]" ExportPath="/Script/Engine.MaterialExpressionConstant'/Engine/Transient.[MATERIAL]:MaterialGraph_0.MaterialGraphNode_[NODE_N].MaterialExpressionConstant_[PARAM_NAME]'"
      R=[VALUE]
      MaterialExpressionEditorX=[X]
      MaterialExpressionEditorY=[Y]
      MaterialExpressionGuid=[GUID_CONST_EXPR]
      Material="/Script/UnrealEd.PreviewMaterial'/Engine/Transient.[MATERIAL]'"
   End Object
   MaterialExpression="/Script/Engine.MaterialExpressionConstant'MaterialExpressionConstant_[PARAM_NAME]'"
   NodePosX=[X]
   NodePosY=[Y]
   NodeGuid=[GUID_CONST_NODE]
   CustomProperties Pin (PinId=[GUID_CONST_VALUE_PIN],PinName="Value",PinType.PinCategory="optional",PinType.PinSubCategory="red",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,DefaultValue="[VALUE]",PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=True,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False,)
   CustomProperties Pin (PinId=[GUID_CONST_OUT_PIN],PinName="Output",PinFriendlyName=NSLOCTEXT("MaterialGraphNode", "Space", " "),Direction="EGPD_Output",PinType.PinCategory="",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,LinkedTo=(MaterialGraphNode_[DECL_NODE_N] [GUID_DECL_IN_PIN],),PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False,)
End Object
Begin Object Class=/Script/UnrealEd.MaterialGraphNode Name="MaterialGraphNode_[DECL_NODE_N]" ExportPath="/Script/UnrealEd.MaterialGraphNode'/Engine/Transient.[MATERIAL]:MaterialGraph_0.MaterialGraphNode_[DECL_NODE_N]'"
   Begin Object Class=/Script/Engine.MaterialExpressionNamedRerouteDeclaration Name="MaterialExpressionNamedRerouteDeclaration_[PARAM_NAME]" ExportPath="/Script/Engine.MaterialExpressionNamedRerouteDeclaration'/Engine/Transient.[MATERIAL]:MaterialGraph_0.MaterialGraphNode_[DECL_NODE_N].MaterialExpressionNamedRerouteDeclaration_[PARAM_NAME]'"
   End Object
   Begin Object Name="MaterialExpressionNamedRerouteDeclaration_[PARAM_NAME]" ExportPath="/Script/Engine.MaterialExpressionNamedRerouteDeclaration'/Engine/Transient.[MATERIAL]:MaterialGraph_0.MaterialGraphNode_[DECL_NODE_N].MaterialExpressionNamedRerouteDeclaration_[PARAM_NAME]'"
      Input=(Expression="/Script/Engine.MaterialExpressionConstant'MaterialGraphNode_[NODE_N].MaterialExpressionConstant_[PARAM_NAME]'")
      Name="[DISPLAY_NAME]"
      NodeColor=(R=[R],G=[G],B=[B],A=1.000000)
      VariableGuid=[GUID_VARIABLE]
      MaterialExpressionEditorX=[X+224]
      MaterialExpressionEditorY=[Y]
      MaterialExpressionGuid=[GUID_DECL_EXPR]
      Material="/Script/UnrealEd.PreviewMaterial'/Engine/Transient.[MATERIAL]'"
   End Object
   MaterialExpression="/Script/Engine.MaterialExpressionNamedRerouteDeclaration'MaterialExpressionNamedRerouteDeclaration_[PARAM_NAME]'"
   NodePosX=[X+224]
   NodePosY=[Y]
   bCanRenameNode=True
   NodeGuid=[GUID_DECL_NODE]
   CustomProperties Pin (PinId=[GUID_DECL_IN_PIN],PinName="Input",PinFriendlyName=NSLOCTEXT("MaterialGraphNode", "Space", " "),PinType.PinCategory="required",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,LinkedTo=(MaterialGraphNode_[NODE_N] [GUID_CONST_OUT_PIN],),PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False,)
   CustomProperties Pin (PinId=[GUID_DECL_OUT_PIN],PinName="Output",PinFriendlyName=NSLOCTEXT("MaterialGraphNode", "Space", " "),Direction="EGPD_Output",PinType.PinCategory="",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False,)
End Object
```

### Usage Node (Add for each place you need to read the value)

```
Begin Object Class=/Script/UnrealEd.MaterialGraphNode Name="MaterialGraphNode_[USAGE_NODE_N]" ExportPath="/Script/UnrealEd.MaterialGraphNode'/Engine/Transient.[MATERIAL]:MaterialGraph_0.MaterialGraphNode_[USAGE_NODE_N]'"
   Begin Object Class=/Script/Engine.MaterialExpressionNamedRerouteUsage Name="MaterialExpressionNamedRerouteUsage_[PARAM_NAME]" ExportPath="/Script/Engine.MaterialExpressionNamedRerouteUsage'/Engine/Transient.[MATERIAL]:MaterialGraph_0.MaterialGraphNode_[USAGE_NODE_N].MaterialExpressionNamedRerouteUsage_[PARAM_NAME]'"
   End Object
   Begin Object Name="MaterialExpressionNamedRerouteUsage_[PARAM_NAME]" ExportPath="/Script/Engine.MaterialExpressionNamedRerouteUsage'/Engine/Transient.[MATERIAL]:MaterialGraph_0.MaterialGraphNode_[USAGE_NODE_N].MaterialExpressionNamedRerouteUsage_[PARAM_NAME]'"
      Declaration="/Script/Engine.MaterialExpressionNamedRerouteDeclaration'MaterialExpressionNamedRerouteDeclaration_[PARAM_NAME]'"
      DeclarationGuid=[GUID_VARIABLE]
      MaterialExpressionEditorX=[USAGE_X]
      MaterialExpressionEditorY=[USAGE_Y]
      MaterialExpressionGuid=[GUID_USAGE_EXPR]
      Material="/Script/UnrealEd.PreviewMaterial'/Engine/Transient.[MATERIAL]'"
   End Object
   MaterialExpression="/Script/Engine.MaterialExpressionNamedRerouteUsage'MaterialExpressionNamedRerouteUsage_[PARAM_NAME]'"
   NodePosX=[USAGE_X]
   NodePosY=[USAGE_Y]
   NodeGuid=[GUID_USAGE_NODE]
   CustomProperties Pin (PinId=[GUID_USAGE_OUT_PIN],PinName="Output",PinFriendlyName=NSLOCTEXT("MaterialGraphNode", "Space", " "),Direction="EGPD_Output",PinType.PinCategory="",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,LinkedTo=([TARGET_NODE] [TARGET_PIN],),PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False,)
End Object
```

## GUID Checklist

For each parameter, you need these unique GUIDs:

| Purpose | Placeholder | Notes |
|---------|-------------|-------|
| Constant expression | `[GUID_CONST_EXPR]` | MaterialExpressionGuid |
| Constant node | `[GUID_CONST_NODE]` | NodeGuid |
| Constant value pin | `[GUID_CONST_VALUE_PIN]` | Input pin (not connected) |
| Constant output pin | `[GUID_CONST_OUT_PIN]` | Links to declaration input |
| Declaration expression | `[GUID_DECL_EXPR]` | MaterialExpressionGuid |
| Declaration node | `[GUID_DECL_NODE]` | NodeGuid |
| Variable GUID | `[GUID_VARIABLE]` | Shared between decl and usage |
| Declaration input pin | `[GUID_DECL_IN_PIN]` | Receives from constant |
| Declaration output pin | `[GUID_DECL_OUT_PIN]` | (Usually not connected) |
| Usage expression | `[GUID_USAGE_EXPR]` | MaterialExpressionGuid |
| Usage node | `[GUID_USAGE_NODE]` | NodeGuid |
| Usage output pin | `[GUID_USAGE_OUT_PIN]` | Links to consumer |

**Critical**: `[GUID_VARIABLE]` in Declaration's `VariableGuid` must match Usage's `DeclarationGuid`.

## Position Calculations

Standard layout:
- Constant node at `(X, Y)`
- Declaration at `(X + 224, Y)` - 224 units right
- Usage nodes placed near their consumers

Vertical spacing for multiple parameters:
- Y offset: `+ 96` per parameter

## Quick Reference

### Required GUIDs per Parameter
- 9-11 unique GUIDs (depending on usage count)

### Required Connections
1. Constant Output → Declaration Input
2. Usage Output → Consumer Input

### Critical Matching
- `VariableGuid` = `DeclarationGuid` (exact match)
- `LinkedTo` pin references must exist
