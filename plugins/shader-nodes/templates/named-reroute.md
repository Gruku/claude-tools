# Named Reroute (Variable) Template

Named reroutes act as variables in the material graph - declare once, use anywhere.

## Declaration Node (Setter)

```
Begin Object Class=/Script/UnrealEd.MaterialGraphNode Name="MaterialGraphNode_[N]" ExportPath="/Script/UnrealEd.MaterialGraphNode'/Engine/Transient.[MaterialName]:MaterialGraph_0.MaterialGraphNode_[N]'"
   Begin Object Class=/Script/Engine.MaterialExpressionNamedRerouteDeclaration Name="MaterialExpressionNamedRerouteDeclaration_[VarName]" ExportPath="/Script/Engine.MaterialExpressionNamedRerouteDeclaration'/Engine/Transient.[MaterialName]:MaterialGraph_0.MaterialGraphNode_[N].MaterialExpressionNamedRerouteDeclaration_[VarName]'"
   End Object
   Begin Object Name="MaterialExpressionNamedRerouteDeclaration_[VarName]" ExportPath="/Script/Engine.MaterialExpressionNamedRerouteDeclaration'/Engine/Transient.[MaterialName]:MaterialGraph_0.MaterialGraphNode_[N].MaterialExpressionNamedRerouteDeclaration_[VarName]'"
      Input=(Expression="/Script/Engine.[SourceExpressionType]'[SourceNodeName].[SourceExpressionName]'")
      Name="[DisplayName]"
      NodeColor=(R=[R],G=[G],B=[B],A=1.000000)
      VariableGuid=[VARIABLE_GUID]
      MaterialExpressionEditorX=[X]
      MaterialExpressionEditorY=[Y]
      MaterialExpressionGuid=[EXPRESSION_GUID]
      Material="/Script/UnrealEd.PreviewMaterial'/Engine/Transient.[MaterialName]'"
   End Object
   MaterialExpression="/Script/Engine.MaterialExpressionNamedRerouteDeclaration'MaterialExpressionNamedRerouteDeclaration_[VarName]'"
   NodePosX=[X]
   NodePosY=[Y]
   bCanRenameNode=True
   NodeGuid=[NODE_GUID]
   CustomProperties Pin (PinId=[INPUT_PIN],PinName="Input",PinFriendlyName=NSLOCTEXT("MaterialGraphNode", "Space", " "),PinType.PinCategory="required",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,LinkedTo=([SourceNode] [SourcePin],),PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False,)
   CustomProperties Pin (PinId=[OUTPUT_PIN],PinName="Output",PinFriendlyName=NSLOCTEXT("MaterialGraphNode", "Space", " "),Direction="EGPD_Output",PinType.PinCategory="",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False,)
End Object
```

## Usage Node (Getter)

**⚠️ CRITICAL: The `Declaration=` path must NOT include the MaterialGraphNode prefix!**

```
Begin Object Class=/Script/UnrealEd.MaterialGraphNode Name="MaterialGraphNode_[N]" ExportPath="/Script/UnrealEd.MaterialGraphNode'/Engine/Transient.[MaterialName]:MaterialGraph_0.MaterialGraphNode_[N]'"
   Begin Object Class=/Script/Engine.MaterialExpressionNamedRerouteUsage Name="MaterialExpressionNamedRerouteUsage_[N]" ExportPath="/Script/Engine.MaterialExpressionNamedRerouteUsage'/Engine/Transient.[MaterialName]:MaterialGraph_0.MaterialGraphNode_[N].MaterialExpressionNamedRerouteUsage_[N]'"
   End Object
   Begin Object Name="MaterialExpressionNamedRerouteUsage_[N]" ExportPath="/Script/Engine.MaterialExpressionNamedRerouteUsage'/Engine/Transient.[MaterialName]:MaterialGraph_0.MaterialGraphNode_[N].MaterialExpressionNamedRerouteUsage_[N]'"
      Declaration="/Script/Engine.MaterialExpressionNamedRerouteDeclaration'MaterialExpressionNamedRerouteDeclaration_[DECL_N]'"
      DeclarationGuid=[MATCHING_VARIABLE_GUID]
      MaterialExpressionEditorX=[X]
      MaterialExpressionEditorY=[Y]
      MaterialExpressionGuid=[EXPRESSION_GUID]
      Material="/Script/UnrealEd.PreviewMaterial'/Engine/Transient.[MaterialName]'"
   End Object
   MaterialExpression="/Script/Engine.MaterialExpressionNamedRerouteUsage'MaterialExpressionNamedRerouteUsage_[N]'"
   NodePosX=[X]
   NodePosY=[Y]
   NodeGuid=[NODE_GUID]
   CustomProperties Pin (PinId=[OUTPUT_PIN],PinName="Output",PinFriendlyName=NSLOCTEXT("MaterialGraphNode", "Space", " "),Direction="EGPD_Output",PinType.PinCategory="",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,LinkedTo=([TargetNode] [TargetPin],),PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False,)
End Object
```

**Key: `[DECL_N]` is the number suffix from the Declaration's expression name, NOT the MaterialGraphNode number.**

## Complete Pair Example

### Constant + Declaration + Usage Pattern

```
// 1. Constant Value Node
Begin Object Class=/Script/UnrealEd.MaterialGraphNode Name="MaterialGraphNode_283" ExportPath="..."
   Begin Object Class=/Script/Engine.MaterialExpressionConstant Name="MaterialExpressionConstant_CircleEnterStart" ExportPath="..."
   End Object
   Begin Object Name="MaterialExpressionConstant_CircleEnterStart" ExportPath="..."
      R=1.000000
      MaterialExpressionEditorX=-5440
      MaterialExpressionEditorY=1024
      MaterialExpressionGuid=D207B0D848A6B61B7B21EE88AA7E76F2
      Material="/Script/UnrealEd.PreviewMaterial'/Engine/Transient.M_UI_MVP_Screen'"
   End Object
   MaterialExpression="/Script/Engine.MaterialExpressionConstant'MaterialExpressionConstant_CircleEnterStart'"
   NodePosX=-5440
   NodePosY=1024
   NodeGuid=88165C254A72674F35FA33A238203A48
   CustomProperties Pin (PinId=ECD53C2C4A4EE7F3BDDD289C819F9F55,PinName="Value",...)
   CustomProperties Pin (PinId=A8EC246A4A84DA0A9A184EACC9675938,PinName="Output",Direction="EGPD_Output",LinkedTo=(MaterialGraphNode_284 81E0B199496CD0FE7B2410B0D2C63F23,),...)
End Object

// 2. Declaration Node (stores the constant as a named variable)
Begin Object Class=/Script/UnrealEd.MaterialGraphNode Name="MaterialGraphNode_284" ExportPath="..."
   Begin Object Class=/Script/Engine.MaterialExpressionNamedRerouteDeclaration Name="MaterialExpressionNamedRerouteDeclaration_CircleEnterStart" ExportPath="..."
   End Object
   Begin Object Name="MaterialExpressionNamedRerouteDeclaration_CircleEnterStart" ExportPath="..."
      Input=(Expression="/Script/Engine.MaterialExpressionConstant'MaterialGraphNode_283.MaterialExpressionConstant_CircleEnterStart'")
      Name="CircleEnterStart"
      NodeColor=(R=1.000000,G=0.632813,B=0.000000,A=1.000000)
      VariableGuid=EE6C4204437F85D9D42E5BB8491D5D53
      MaterialExpressionEditorX=-5216
      MaterialExpressionEditorY=1024
      MaterialExpressionGuid=9E35D2B44976B948A77A4ABBE446575F
      Material="/Script/UnrealEd.PreviewMaterial'/Engine/Transient.M_UI_MVP_Screen'"
   End Object
   MaterialExpression="/Script/Engine.MaterialExpressionNamedRerouteDeclaration'MaterialExpressionNamedRerouteDeclaration_CircleEnterStart'"
   NodePosX=-5216
   NodePosY=1024
   bCanRenameNode=True
   NodeGuid=AA0BE98448A0D225E1289B9BD35F2A87
   CustomProperties Pin (PinId=81E0B199496CD0FE7B2410B0D2C63F23,PinName="Input",LinkedTo=(MaterialGraphNode_283 A8EC246A4A84DA0A9A184EACC9675938,),...)
   CustomProperties Pin (PinId=92DECCD340937299E2C6AFBADA4C34ED,PinName="Output",Direction="EGPD_Output",...)
End Object

// 3. Usage Node (reads the variable wherever needed)
Begin Object Class=/Script/UnrealEd.MaterialGraphNode Name="MaterialGraphNode_285" ExportPath="..."
   Begin Object Class=/Script/Engine.MaterialExpressionNamedRerouteUsage Name="MaterialExpressionNamedRerouteUsage_CircleEnterStart" ExportPath="..."
   End Object
   Begin Object Name="MaterialExpressionNamedRerouteUsage_CircleEnterStart" ExportPath="..."
      Declaration="/Script/Engine.MaterialExpressionNamedRerouteDeclaration'MaterialExpressionNamedRerouteDeclaration_CircleEnterStart'"
      DeclarationGuid=EE6C4204437F85D9D42E5BB8491D5D53
      MaterialExpressionEditorX=-4800
      MaterialExpressionEditorY=1200
      MaterialExpressionGuid=3D11E0FD4A28668AE61BE19167F5196C
      Material="/Script/UnrealEd.PreviewMaterial'/Engine/Transient.M_UI_MVP_Screen'"
   End Object
   MaterialExpression="/Script/Engine.MaterialExpressionNamedRerouteUsage'MaterialExpressionNamedRerouteUsage_CircleEnterStart'"
   NodePosX=-4800
   NodePosY=1200
   NodeGuid=...
   CustomProperties Pin (PinId=3D11E0FD4A28668AE61BE19167F5196C,PinName="Output",Direction="EGPD_Output",LinkedTo=([TargetNode] [TargetPin],),...)
End Object
```

## Color Coding Reference

Common colors for organization:

| Category | R | G | B | Hex |
|----------|---|---|---|-----|
| Animation/Time | 1.0 | 0.632813 | 0.0 | Orange |
| Input Parameters | 0.0 | 1.0 | 0.5 | Green |
| UV/Position | 0.5 | 0.5 | 1.0 | Blue |
| Mask/Alpha | 1.0 | 0.0 | 0.5 | Pink |
| Result/Output | 1.0 | 1.0 | 0.0 | Yellow |

## Critical GUID Matching

The `VariableGuid` in the Declaration must EXACTLY match the `DeclarationGuid` in all Usage nodes. This is how UE5 links them.

```
Declaration:
   VariableGuid=EE6C4204437F85D9D42E5BB8491D5D53

Usage:
   DeclarationGuid=EE6C4204437F85D9D42E5BB8491D5D53  // Must match!
```

## ⚠️ CRITICAL: Declaration Path Format

**The `Declaration=` path in Usage nodes must NOT include the outer MaterialGraphNode!**

```
// ✓ CORRECT - Expression name only:
Declaration="/Script/Engine.MaterialExpressionNamedRerouteDeclaration'MaterialExpressionNamedRerouteDeclaration_1'"

// ✗ WRONG - Do NOT include MaterialGraphNode:
Declaration="/Script/Engine.MaterialExpressionNamedRerouteDeclaration'MaterialGraphNode_4.MaterialExpressionNamedRerouteDeclaration_1'"
```

**This is different from `Input=` references which DO include MaterialGraphNode:**
```
// Input references use full path:
Input=(Expression="/Script/Engine.MaterialExpressionNamedRerouteUsage'MaterialGraphNode_16.MaterialExpressionNamedRerouteUsage_1'")
```

Getting this wrong causes "Invalid Named Reroute" errors!
