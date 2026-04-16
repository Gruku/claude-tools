# Agent Orchestration for UE5 Node Generation

Due to the verbosity of UE5 material node structures (~90k characters for complex graphs), efficient generation requires delegating work to specialized agents.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    MAIN CLAUDE INSTANCE                      │
│  - Requirements gathering                                    │
│  - Design decisions                                         │
│  - Agent coordination                                       │
│  - Final assembly & validation                              │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  INPUT AGENT    │ │  LOGIC AGENT    │ │  OUTPUT AGENT   │
│                 │ │                 │ │                 │
│ - Constants     │ │ - Custom HLSL   │ │ - Final wiring  │
│ - Reroutes      │ │ - Math nodes    │ │ - Validation    │
│ - Parameters    │ │ - Connections   │ │ - File output   │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

## Phase 1: Design (Main Instance)

Before spawning agents, the main instance should:

1. **Clarify Requirements**
   - What inputs are needed?
   - What processing logic?
   - What outputs?
   - Animation behavior?

2. **Design the Graph**
   - List all nodes needed
   - Plan Float4 packing
   - Define connection topology
   - Assign node positions

3. **Generate GUID Pool**
   - Pre-generate all GUIDs needed
   - Assign to specific purposes
   - Share with agents

### GUID Pool Generation

```
Generate GUIDs for:
- Input nodes: [N] constants × 2 GUIDs each
- Reroute declarations: [N] × 3 GUIDs each
- Reroute usages: [M] × 2 GUIDs each
- Custom nodes: [N] × (2 + inputs + outputs) GUIDs each
- Connections: [N] pin GUIDs
```

## Phase 2: Parallel Agent Generation

### Agent 1: Input Parameters

**Task**: Generate all input parameter nodes (constants + reroute declarations)

**Prompt Template**:
```
Generate UE5 material graph nodes for these input parameters:

Material Name: [MATERIAL_NAME]
Starting Node Number: [N]

Parameters:
1. Name: [NAME], Value: [VALUE], Color: [R,G,B]
   GUIDs: ConstExpr=[...], ConstNode=[...], ConstPin=[...],
          DeclExpr=[...], DeclNode=[...], VarGuid=[...], DeclInPin=[...], DeclOutPin=[...]
2. ...

Position: Start at X=-5440, Y=1024, spacing Y+96

Use the templates from /ue5-custom-shader-nodes skill.
Output only the node structures, no explanation.
```

### Agent 2: Reroute Usages

**Task**: Generate usage nodes for reading parameters

**Prompt Template**:
```
Generate UE5 Named Reroute Usage nodes:

Material Name: [MATERIAL_NAME]
Starting Node Number: [N]

Usages:
1. Variable: [VAR_NAME], VarGuid: [GUID], Position: (X, Y)
   GUIDs: UsageExpr=[...], UsageNode=[...], OutPin=[...]
   Links To: [TARGET_NODE] [TARGET_PIN]
2. ...

Use the templates from /ue5-custom-shader-nodes skill.
Output only the node structures.
```

### Agent 3: Custom HLSL Nodes

**Task**: Generate custom code nodes

**Prompt Template**:
```
Generate UE5 Custom HLSL nodes:

Material Name: [MATERIAL_NAME]
Node Number: [N]

Node Configuration:
- Description: [TITLE]
- Inputs: [LIST_WITH_SOURCES]
- Outputs: [LIST_WITH_TYPES]
- Code: [HLSL_CODE]
- Position: (X, Y)
- GUIDs: [ALL_REQUIRED_GUIDS]

Use templates from /ue5-custom-shader-nodes skill.
Format HLSL with \r\n line endings.
```

### Agent 4: Wiring Validation

**Task**: Verify all connections are valid

**Prompt Template**:
```
Validate connections in this UE5 material graph:

[ASSEMBLED_GRAPH]

Check:
1. All LinkedTo references point to existing nodes/pins
2. All VarGuid/DeclarationGuid pairs match
3. All Expression paths are valid
4. No orphaned pins

Report any issues found.
```

## Phase 3: Assembly (Main Instance)

1. **Collect Agent Outputs**
   - Merge all generated node blocks
   - Maintain order for readability

2. **Add Comment Boxes**
   - Group related nodes
   - Apply color coding

3. **Final Validation**
   - Run wiring validation
   - Check for duplicate GUIDs

4. **Output**
   - Write to appropriate files
   - Provide copy-paste instructions

## File Organization Strategy

For large graphs, split into files:

```
output/
├── 01-input-parameters.txt     # Constants + Declarations
├── 02-reroute-usages.txt       # Usage nodes
├── 03-custom-logic.txt         # Custom HLSL nodes
├── 04-math-operations.txt      # Add, Multiply, Lerp, etc.
├── 05-outputs.txt              # Final output connections
├── 06-comments.txt             # Comment boxes
└── full-graph.txt              # Complete assembled graph
```

## Parallel Execution Pattern

For maximum efficiency, launch independent agents in parallel:

```
# Agents that can run in parallel:
- Input Agent: Generates constants + declarations
- Usage Agent: Generates usage nodes (needs VarGuids from design)
- Logic Agent: Generates custom nodes (needs input references from design)

# Sequential agents:
- Validation Agent: Runs after assembly
```

## Error Recovery

If an agent produces invalid output:

1. Identify the specific error (missing GUID, bad reference)
2. Provide corrected GUIDs/references
3. Re-run only the affected agent
4. Re-validate

## Token Efficiency

### Reduce Output Size
- Agents output only node structures, no explanations
- Use placeholders for repeated boilerplate
- Post-process to expand placeholders

### Minimize Context
- Each agent receives only what it needs
- Reference skill documents, don't copy them
- Use specific node numbers to avoid conflicts

## Example Workflow

**User Request**: "Create an animation node that fades in an element over 0.5 seconds"

**Main Instance Design**:
```
Nodes needed:
1. Constant: EnterStart = -1.0 (inactive)
2. Constant: Duration = 0.5
3. Time node
4. Custom: Ramp01 function
5. Output reroute: AnimationProgress

GUIDs:
- EnterStart: GUID1-GUID8
- Duration: GUID9-GUID16
- Time: GUID17-GUID18
- Custom: GUID19-GUID26
- Output: GUID27-GUID32
```

**Launch Agents**:
1. Input Agent: Generate EnterStart, Duration constants
2. Custom Agent: Generate Ramp01 custom node
3. Output Agent: Generate AnimationProgress reroute

**Assembly**:
- Merge outputs
- Validate connections
- Output final graph

## Best Practices

1. **Always pre-generate GUIDs** before spawning agents
2. **Define clear boundaries** between agent responsibilities
3. **Use consistent node numbering** across agents
4. **Validate early and often** to catch connection errors
5. **Document the design** before implementation
6. **Keep HLSL code separate** from structure generation
7. **Test incremental outputs** by pasting partial graphs

## Integration with Claude Skills

This orchestration pattern works with:
- `/ue5-custom-shader-nodes` - Main skill
- `/ue5-ui-shader-antialiasing` - For AA patterns in HLSL
- Custom project skills for specific material types
