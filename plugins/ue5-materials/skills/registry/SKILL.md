---
name: registry
description: Look up UE5 material-graph node types in node_registry.yaml and add missing ones. Invoke before generating YAML when you hit an unfamiliar expression class (e.g. ComponentMask, Fresnel, CustomRotator) or when the user asks whether a node or Material Function is already registered. This is the authoritative catalogue of node shapes the clipboard-mode generator can emit.
---

# UE5 Node Registry Manager

This skill checks if a node type exists in `node_registry.yaml` and creates it if missing.

## Registry Location

```
../../node_registry.yaml
```

(Relative to this skill's base directory -- at the plugin root.)

## When to Use

**ALWAYS check the registry BEFORE generating shader YAML** when:
- User mentions a node type you're unsure about
- You need a node that might not be in the registry
- User asks for a specific UE5 node by name

## Workflow

1. **Check** if node exists in registry
2. **If missing**, determine the node specification:
   - Expression class name
   - Input pins (names, categories)
   - Output pins
   - Default properties
3. **Add** to `../../node_registry.yaml`
4. **Confirm** the node is now available

## How to Determine Node Specification

### Method 1: From UE5 Documentation
Look up the MaterialExpression class in UE5 docs to find:
- Input/output pin names
- Property names and defaults

### Method 2: From User's Existing Nodes
Ask the user to copy-paste an example of the node from their material.

### Method 3: Common Patterns
Most nodes follow patterns:
- Single input -> Single output (Abs, Floor, Saturate)
- Two inputs A,B -> Single output (Add, Multiply, Dot)
- Special inputs (Lerp: A, B, Alpha)

## Node Definition Format

```yaml
NodeTypeName:
  expression_class: MaterialExpressionNodeTypeName
  inputs:
    - name: InputName
      category: required|optional
      pin_name: "Display Name"  # optional, if different from name
  outputs:
    - name: Output
      subcategory: ""  # or "red", "green", "blue", "alpha", "mask"
  properties:
    DefaultProperty: value
  property_mappings:
    yaml_key: UE5PropertyName  # maps simple YAML keys to UE5 property names
```

## Common Node Patterns

### Single Input Node (like Abs, Floor, Saturate)
```yaml
NodeName:
  expression_class: MaterialExpressionNodeName
  inputs:
    - name: Input
      category: required
  outputs:
    - name: Output
```

### Two Input Node (like Add, Multiply)
```yaml
NodeName:
  expression_class: MaterialExpressionNodeName
  inputs:
    - name: A
      category: optional
    - name: B
      category: optional
  outputs:
    - name: Output
  properties:
    ConstA: 0.0
    ConstB: 1.0
```

### Coordinate Node (like TexCoord, ScreenPosition)
```yaml
NodeName:
  expression_class: MaterialExpressionNodeName
  outputs:
    - name: Output
  properties:
    SomeDefault: value
```

## Procedure

When invoked with a node type name:

### Step 1: Read Current Registry
Read `../../node_registry.yaml`

### Step 2: Check if Node Exists
- If exists: Report "Node type X is available" with its definition
- If missing: Proceed to Step 3

### Step 3: Determine Specification
Ask user or use known patterns:
- What is the expression class? (Usually `MaterialExpression` + NodeName)
- What inputs does it have?
- What outputs?
- Any default properties?

### Step 4: Add to Registry
Append the new node definition to `../../node_registry.yaml`

### Step 5: Confirm
Report the new node is available and show example usage.

## Examples of Nodes to Add

### Fresnel
```yaml
Fresnel:
  expression_class: MaterialExpressionFresnel
  inputs:
    - name: ExponentIn
      category: optional
    - name: BaseReflectFractionIn
      category: optional
    - name: Normal
      category: optional
  outputs:
    - name: Output
  properties:
    Exponent: 5.0
    BaseReflectFraction: 0.04
```

### SphereMask
```yaml
SphereMask:
  expression_class: MaterialExpressionSphereMask
  inputs:
    - name: A
      category: required
    - name: B
      category: required
    - name: Radius
      category: optional
    - name: Hardness
      category: optional
  outputs:
    - name: Output
  properties:
    AttenuationRadius: 256.0
    HardnessPercent: 100.0
```

## Output Format

When checking a node, respond with:

**If exists:**
```
Node type "Multiply" exists in registry.

Definition:
  expression_class: MaterialExpressionMultiply
  inputs: A (optional), B (optional)
  outputs: Output
  properties: ConstA=0.0, ConstB=1.0

Example usage in YAML:
  - name: MyMultiply
    type: Multiply
    const_a: 2.0
```

**If missing and added:**
```
Node type "Fresnel" not found in registry.

Adding to node_registry.yaml...

Added definition:
  expression_class: MaterialExpressionFresnel
  inputs: ExponentIn (optional), BaseReflectFractionIn (optional), Normal (optional)
  outputs: Output
  properties: Exponent=5.0, BaseReflectFraction=0.04

Node type "Fresnel" is now available.

Example usage in YAML:
  - name: MyFresnel
    type: Fresnel
    properties:
      Exponent: 3.0
```
