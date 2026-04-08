# UE5 Node Connection Syntax - Definitive Reference

Based on analysis of production shader node files.

---

## ⚠️ CRITICAL: Why Connections Fail

**The #1 cause of "unconnected" nodes is missing `LinkedTo=` in CustomProperties Pin.**

The Material Editor uses TWO separate systems:
1. **Expression references** (inner object) → Data flow (shader compilation)
2. **LinkedTo references** (CustomProperties Pin) → Visual wires in editor

**If you only have Expression references but no LinkedTo, nodes will:**
- ✗ Appear visually disconnected (no wires)
- ✓ But may still compile (data exists)

**To see wires in the editor, you MUST have LinkedTo in BOTH pins.**

---

## The Golden Rule: Three-Part Connections

**Every A → B connection requires ALL THREE:**

```
1. SOURCE OUTPUT PIN (draws wire FROM this node):
   CustomProperties Pin (PinId=AAAA...,PinName="Output",Direction="EGPD_Output",...,LinkedTo=(B_NodeName B_InputPinId,),...)

2. TARGET INPUT PIN (draws wire TO this node):
   CustomProperties Pin (PinId=BBBB...,PinName="InputName",...,LinkedTo=(A_NodeName A_OutputPinId,),...)

3. TARGET INNER OBJECT (data reference):
   Input=(Expression="/Script/Engine.[Type]'A_NodeName.A_ExpressionName'")
```

**Missing ANY of these = broken connection.**

---

## Minimal Working Example: Constant → NamedReroute

```
// SOURCE: Constant node
Begin Object Class=/Script/UnrealEd.MaterialGraphNode Name="MaterialGraphNode_1"
   Begin Object Class=/Script/Engine.MaterialExpressionConstant Name="MaterialExpressionConstant_0"
   End Object
   Begin Object Name="MaterialExpressionConstant_0"
      R=1.000000
      MaterialExpressionEditorX=0
      MaterialExpressionEditorY=0
      MaterialExpressionGuid=11111111111111111111111111111111
   End Object
   MaterialExpression="/Script/Engine.MaterialExpressionConstant'MaterialExpressionConstant_0'"
   NodePosX=0
   NodePosY=0
   NodeGuid=22222222222222222222222222222222
   CustomProperties Pin (PinId=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA1,PinName="Output",Direction="EGPD_Output",PinType.PinCategory="",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,LinkedTo=(MaterialGraphNode_2 BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB1,),PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False,)
End Object

// TARGET: NamedRerouteDeclaration
Begin Object Class=/Script/UnrealEd.MaterialGraphNode Name="MaterialGraphNode_2"
   Begin Object Class=/Script/Engine.MaterialExpressionNamedRerouteDeclaration Name="MaterialExpressionNamedRerouteDeclaration_0"
   End Object
   Begin Object Name="MaterialExpressionNamedRerouteDeclaration_0"
      Input=(Expression="/Script/Engine.MaterialExpressionConstant'MaterialGraphNode_1.MaterialExpressionConstant_0'")
      Name="MyVariable"
      VariableGuid=33333333333333333333333333333333
      MaterialExpressionEditorX=200
      MaterialExpressionEditorY=0
      MaterialExpressionGuid=44444444444444444444444444444444
   End Object
   MaterialExpression="/Script/Engine.MaterialExpressionNamedRerouteDeclaration'MaterialExpressionNamedRerouteDeclaration_0'"
   NodePosX=200
   NodePosY=0
   NodeGuid=55555555555555555555555555555555
   CustomProperties Pin (PinId=BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB1,PinName="Input",PinType.PinCategory="wildcard",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,LinkedTo=(MaterialGraphNode_1 AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA1,),PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False,)
   CustomProperties Pin (PinId=BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB2,PinName="Output",Direction="EGPD_Output",PinType.PinCategory="wildcard",PinType.PinSubCategory="",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False,)
End Object
```

**Key connection points in above example:**
| Location | What to check |
|----------|---------------|
| MaterialGraphNode_1 output pin | `LinkedTo=(MaterialGraphNode_2 BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB1,)` |
| MaterialGraphNode_2 input pin | `LinkedTo=(MaterialGraphNode_1 AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA1,)` |
| MaterialExpressionNamedRerouteDeclaration_0 | `Input=(Expression="...MaterialGraphNode_1.MaterialExpressionConstant_0'")` |

---

## Pattern 1: Constant → NamedRerouteDeclaration

**Source: Constant Node**
```
Begin Object Class=/Script/UnrealEd.MaterialGraphNode Name="MaterialGraphNode_283" ...
   Begin Object Class=/Script/Engine.MaterialExpressionConstant Name="MaterialExpressionConstant_SizeAnim_EnterStart" ...
   End Object
   Begin Object Name="MaterialExpressionConstant_SizeAnim_EnterStart" ...
      R=1.000000
      ...
   End Object
   ...
   CustomProperties Pin (PinId=A8EC246A4A84DA0A9A184EACC9675938,PinName="Output",Direction="EGPD_Output",...,LinkedTo=(MaterialGraphNode_284 81E0B199496CD0FE7B2410B0D2C63F23,),...)
End Object
```

**Target: NamedRerouteDeclaration**
```
Begin Object Class=/Script/UnrealEd.MaterialGraphNode Name="MaterialGraphNode_284" ...
   Begin Object Class=/Script/Engine.MaterialExpressionNamedRerouteDeclaration Name="MaterialExpressionNamedRerouteDeclaration_SizeAnim_EnterStart" ...
   End Object
   Begin Object Name="MaterialExpressionNamedRerouteDeclaration_SizeAnim_EnterStart" ...
      Input=(Expression="/Script/Engine.MaterialExpressionConstant'MaterialGraphNode_283.MaterialExpressionConstant_SizeAnim_EnterStart'")
      Name="CircleEnterStart"
      VariableGuid=EE6C4204437F85D9D42E5BB8491D5D53
      ...
   End Object
   ...
   CustomProperties Pin (PinId=81E0B199496CD0FE7B2410B0D2C63F23,PinName="Input",...,LinkedTo=(MaterialGraphNode_283 A8EC246A4A84DA0A9A184EACC9675938,),...)
End Object
```

**Connection Points:**
| Location | Property | Value |
|----------|----------|-------|
| Constant Output Pin | `LinkedTo=` | `(MaterialGraphNode_284 81E0B199496CD0FE7B2410B0D2C63F23,)` |
| Declaration Input Pin | `LinkedTo=` | `(MaterialGraphNode_283 A8EC246A4A84DA0A9A184EACC9675938,)` |
| Declaration Expression | `Input=` | `(Expression="/Script/Engine.MaterialExpressionConstant'MaterialGraphNode_283.MaterialExpressionConstant_SizeAnim_EnterStart'")` |

---

## Pattern 2: NamedRerouteUsage → Custom Node

**Source: NamedRerouteUsage**
```
Begin Object Name="MaterialExpressionNamedRerouteUsage_SizeAnim_CurrentTime" ...
   Declaration="/Script/Engine.MaterialExpressionNamedRerouteDeclaration'MaterialExpressionNamedRerouteDeclaration_12'"
   DeclarationGuid=3976BE5B4151EE37E5D1A2934E0F6320
   ...
End Object
...
   CustomProperties Pin (PinId=8D8E810B4232823207A22BBD159424A4,PinName="Output",Direction="EGPD_Output",...,LinkedTo=(MaterialGraphNode_Custom_10 05BB7CA04F83F58162A7FB99FCA2F94A,),...)
```

**Target: Custom Node**
```
Begin Object Name="MaterialExpressionCustom_11" ...
   Code="..."
   Inputs(0)=(InputName="CurrentTime",Input=(Expression="/Script/Engine.MaterialExpressionNamedRerouteUsage'MaterialExpressionNamedRerouteUsage_SizeAnim_CurrentTime'"))
   Inputs(1)=(InputName="EnterStart",Input=(Expression="/Script/Engine.MaterialExpressionNamedRerouteUsage'MaterialExpressionNamedRerouteUsage_SizeAnim_EnterStart'"))
   ...
End Object
...
   CustomProperties Pin (PinId=05BB7CA04F83F58162A7FB99FCA2F94A,PinName="CurrentTime",PinType.PinCategory="required",...,LinkedTo=(MaterialGraphNode_309 8D8E810B4232823207A22BBD159424A4,),...)
```

**Connection Points:**
| Location | Property | Value |
|----------|----------|-------|
| Usage Output Pin | `LinkedTo=` | `(MaterialGraphNode_Custom_10 05BB7CA04F83F58162A7FB99FCA2F94A,)` |
| Custom Input Pin | `LinkedTo=` | `(MaterialGraphNode_309 8D8E810B4232823207A22BBD159424A4,)` |
| Custom Inputs Array | `Input=` | `(Expression="/Script/Engine.MaterialExpressionNamedRerouteUsage'...'")` |

---

## Pattern 3: Constants → MakeFloat4

**MakeFloat4 uses pin names: X (S), Y (S), Z (S), A (S)**

**Source Constants:**
```
MaterialGraphNode_40 (X=0.07):
   CustomProperties Pin (PinId=AF111A8147907BD2C6F58B86135E370E,PinName="Output",...,LinkedTo=(MaterialGraphNode_41 1DA96F724308740FCC1102AAEB583131,),...)

MaterialGraphNode_42 (Y=-0.2):
   CustomProperties Pin (...,LinkedTo=(MaterialGraphNode_41 D0571B7C4145C78149D260A987FE3F39,),...)

MaterialGraphNode_43 (Z=0.8):
   CustomProperties Pin (...,LinkedTo=(MaterialGraphNode_41 024389BC4E6F5E1FC669D78B46CE1C19,),...)

MaterialGraphNode_44 (A=0.7):
   CustomProperties Pin (...,LinkedTo=(MaterialGraphNode_41 68E7E1294A1FB4E877A8B8B5E1476E37,),...)
```

**Target: MakeFloat4 Node**
```
Begin Object Name="MaterialExpressionMaterialFunctionCall_18" ...
   MaterialFunction="/Script/Engine.MaterialFunction'/Engine/Functions/Engine_MaterialFunctions02/Utility/MakeFloat4.MakeFloat4'"
   FunctionInputs(0)=(ExpressionInputId=529C1D96441E07EB03A9E59B8A7F67B6,Input=(Expression="/Script/Engine.MaterialExpressionConstant'MaterialGraphNode_40.MaterialExpressionConstant_23'",InputName="X"))
   FunctionInputs(1)=(ExpressionInputId=B5BD7D1B494F6928732CCDA1C63D8E15,Input=(Expression="/Script/Engine.MaterialExpressionConstant'MaterialGraphNode_42.MaterialExpressionConstant_24'",InputName="Y"))
   FunctionInputs(2)=(ExpressionInputId=050F17B8471570B47A802CB7CAA5A201,Input=(Expression="/Script/Engine.MaterialExpressionConstant'MaterialGraphNode_43.MaterialExpressionConstant_28'",InputName="Z"))
   FunctionInputs(3)=(ExpressionInputId=4302C68A4D3ABCFB34DE619C2867A488,Input=(Expression="/Script/Engine.MaterialExpressionConstant'MaterialGraphNode_44.MaterialExpressionConstant_31'",InputName="A"))
   FunctionOutputs(0)=(ExpressionOutputId=0DD6F9954C067C3E5DDBBBA0D6910DD2,Output=(OutputName="Result"))
   Outputs(0)=(OutputName="Result")
End Object
...
   CustomProperties Pin (PinId=1DA96F724308740FCC1102AAEB583131,PinName="X (S)",...,LinkedTo=(MaterialGraphNode_40 AF111A8147907BD2C6F58B86135E370E,),...)
   CustomProperties Pin (PinId=D0571B7C4145C78149D260A987FE3F39,PinName="Y (S)",...,LinkedTo=(MaterialGraphNode_42 ...),...)
   CustomProperties Pin (PinId=024389BC4E6F5E1FC669D78B46CE1C19,PinName="Z (S)",...,LinkedTo=(MaterialGraphNode_43 ...),...)
   CustomProperties Pin (PinId=68E7E1294A1FB4E877A8B8B5E1476E37,PinName="A (S)",...,LinkedTo=(MaterialGraphNode_44 ...),...)
   CustomProperties Pin (PinId=C125F340484451D375D7BB94EF2D52D7,PinName="Result",Direction="EGPD_Output",...,LinkedTo=(NextNode NextPinId,),...)
```

**Fixed ExpressionInputId GUIDs for MakeFloat4:**
| Input | ExpressionInputId |
|-------|-------------------|
| X | `529C1D96441E07EB03A9E59B8A7F67B6` |
| Y | `B5BD7D1B494F6928732CCDA1C63D8E15` |
| Z | `050F17B8471570B47A802CB7CAA5A201` |
| A | `4302C68A4D3ABCFB34DE619C2867A488` |
| Result | `0DD6F9954C067C3E5DDBBBA0D6910DD2` |

---

## Pattern 4: Custom Node → NamedRerouteDeclaration

**Source: Custom Node Output**
```
CustomProperties Pin (PinId=0DA0BCC845511790C3C124A429B8D0C6,PinName="Output",Direction="EGPD_Output",...,LinkedTo=(MaterialGraphNode_393 DF0999A845E2D59143181F94C1D14EF1,),...)
```

**Target: NamedRerouteDeclaration**
```
Begin Object Name="MaterialExpressionNamedRerouteDeclaration_17" ...
   Input=(Expression="/Script/Engine.MaterialExpressionCustom'MaterialGraphNode_Custom_1.MaterialExpressionCustom_1'")
   Name="StartAnimationLerp"
   VariableGuid=7887A45046D505792D9746917F574593
   ...
End Object
...
   CustomProperties Pin (PinId=DF0999A845E2D59143181F94C1D14EF1,PinName="Input",...,LinkedTo=(MaterialGraphNode_Custom_1 0DA0BCC845511790C3C124A429B8D0C6,),...)
```

---

## Pattern 5: Time Node → Custom Node

**Source: Time Node**
```
Begin Object Name="MaterialExpressionTime_1" ...
End Object
...
   CustomProperties Pin (PinId=D24067D740E58E013BC9D6BA883545CB,PinName="Output",Direction="EGPD_Output",...,LinkedTo=(MaterialGraphNode_Custom_1 CFC6354447067E25F56630A4A231BBDA,),...)
```

**Target: Custom Node**
```
Inputs(2)=(InputName="TimeSec",Input=(Expression="/Script/Engine.MaterialExpressionTime'MaterialGraphNode_391.MaterialExpressionTime_1'"))
...
   CustomProperties Pin (PinId=CFC6354447067E25F56630A4A231BBDA,PinName="TimeSec",PinType.PinCategory="required",...,LinkedTo=(MaterialGraphNode_391 D24067D740E58E013BC9D6BA883545CB,),...)
```

---

## Expression Path Format

```
/Script/Engine.[ExpressionClass]'[NodeName].[ExpressionName]'
```

**Examples:**
```
/Script/Engine.MaterialExpressionConstant'MaterialGraphNode_283.MaterialExpressionConstant_SizeAnim_EnterStart'
/Script/Engine.MaterialExpressionNamedRerouteUsage'MaterialGraphNode_309.MaterialExpressionNamedRerouteUsage_22'
/Script/Engine.MaterialExpressionCustom'MaterialGraphNode_Custom_1.MaterialExpressionCustom_1'
/Script/Engine.MaterialExpressionTime'MaterialGraphNode_391.MaterialExpressionTime_1'
/Script/Engine.MaterialExpressionMaterialFunctionCall'MaterialGraphNode_1.MaterialExpressionMaterialFunctionCall_36'
```

---

## Connection Checklist (MANDATORY)

**For EVERY A → B connection, verify ALL of these:**

### Step 1: Source Node (A) - Output Pin
```
CustomProperties Pin (PinId=AAAA...,PinName="Output",Direction="EGPD_Output",...,LinkedTo=(B_NodeName B_PinId,),...)
                                                                                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                                                                 MUST point to target node + pin
```

### Step 2: Target Node (B) - Input Pin
```
CustomProperties Pin (PinId=BBBB...,PinName="InputName",...,LinkedTo=(A_NodeName A_PinId,),...)
                                                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                                            MUST point back to source node + pin
```

### Step 3: Target Node (B) - Inner Object Expression
```
Input=(Expression="/Script/Engine.[Type]'A_NodeName.A_ExpressionName'")
                                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                        MUST reference source node.expression
```

### Validation Checklist
- [ ] **LinkedTo in A's output** → Points to B's input pin ID
- [ ] **LinkedTo in B's input** → Points to A's output pin ID
- [ ] **Expression in B's inner object** → References A's expression name
- [ ] **Pin IDs are unique** 32-char uppercase hex (no duplicates!)
- [ ] **Node names match exactly** (case-sensitive, no typos)
- [ ] **Expression names match** inner object names exactly

### Common Mistakes
| Symptom | Cause | Fix |
|---------|-------|-----|
| No wire visible | Missing `LinkedTo=` in one or both pins | Add LinkedTo to BOTH pins |
| Wire exists but node errors | Wrong Expression path | Check inner object name matches |
| "Unknown pin" error | Pin ID mismatch | Ensure LinkedTo uses exact PinId from target |
| Node compiles but wrong data | OutputIndex missing for multi-output nodes | Add `OutputIndex=N` to FunctionInputs |

---

## ⚠️ CRITICAL: Expression Path Differences by Context

**Different properties use DIFFERENT path formats!**

### Input/Expression References (in Custom nodes, Declarations, etc.)
**INCLUDE the outer MaterialGraphNode:**
```
Input=(Expression="/Script/Engine.MaterialExpressionConstant'MaterialGraphNode_5.MaterialExpressionConstant_BarHeight'")
Input=(Expression="/Script/Engine.MaterialExpressionNamedRerouteUsage'MaterialGraphNode_16.MaterialExpressionNamedRerouteUsage_1'")
Input=(Expression="/Script/Engine.MaterialExpressionTextureCoordinate'MaterialGraphNode_15.MaterialExpressionTextureCoordinate_2'")
```

### Declaration Reference (in NamedRerouteUsage only)
**Do NOT include the outer MaterialGraphNode:**
```
Declaration="/Script/Engine.MaterialExpressionNamedRerouteDeclaration'MaterialExpressionNamedRerouteDeclaration_1'"
```

### Why This Matters
| Property | Include MaterialGraphNode? | Example |
|----------|---------------------------|---------|
| `Input=(Expression="...")` | ✓ YES | `'MaterialGraphNode_5.MaterialExpressionConstant_1'` |
| `Declaration="..."` | ✗ NO | `'MaterialExpressionNamedRerouteDeclaration_1'` |

**Getting this wrong causes "Invalid Named Reroute" errors!**

---

## NamedReroute Complete Example (Production-Verified)

### Declaration Node
```
Begin Object Class=/Script/UnrealEd.MaterialGraphNode Name="MaterialGraphNode_4"
   Begin Object Class=/Script/Engine.MaterialExpressionNamedRerouteDeclaration Name="MaterialExpressionNamedRerouteDeclaration_1"
   End Object
   Begin Object Name="MaterialExpressionNamedRerouteDeclaration_1"
      Input=(Expression="/Script/Engine.MaterialExpressionAppendVector'MaterialGraphNode_3.MaterialExpressionAppendVector_Pos'")
      Name="Position"
      NodeColor=(R=0.500000,G=0.500000,B=1.000000,A=1.000000)
      VariableGuid=A4A4A4A44A4A4A4A4A4A4A4A4A4A4A01
      MaterialExpressionEditorX=-2048
      MaterialExpressionEditorY=-368
      MaterialExpressionGuid=A4A4A4A44A4A4A4A4A4A4A4A4A4A4A03
   End Object
   ...
End Object
```

### Usage Node (References Declaration WITHOUT MaterialGraphNode prefix)
```
Begin Object Class=/Script/UnrealEd.MaterialGraphNode Name="MaterialGraphNode_16"
   Begin Object Class=/Script/Engine.MaterialExpressionNamedRerouteUsage Name="MaterialExpressionNamedRerouteUsage_1"
   End Object
   Begin Object Name="MaterialExpressionNamedRerouteUsage_1"
      Declaration="/Script/Engine.MaterialExpressionNamedRerouteDeclaration'MaterialExpressionNamedRerouteDeclaration_1'"
      DeclarationGuid=A4A4A4A44A4A4A4A4A4A4A4A4A4A4A01
      ...
   End Object
   ...
End Object
```

### Custom Node Input (References Usage WITH MaterialGraphNode prefix)
```
Inputs(1)=(InputName="Position",Input=(Expression="/Script/Engine.MaterialExpressionNamedRerouteUsage'MaterialGraphNode_16.MaterialExpressionNamedRerouteUsage_1'"))
```

### Key Points
1. **VariableGuid** in Declaration must match **DeclarationGuid** in Usage
2. **Declaration=** path uses expression name ONLY (no MaterialGraphNode)
3. **Input=** paths always include MaterialGraphNode.ExpressionName
