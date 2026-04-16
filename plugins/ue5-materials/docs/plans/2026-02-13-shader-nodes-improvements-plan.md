# Shader Nodes Plugin Improvements — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix duplicate skills wasting context, broken comment positioning, missing self-review, HLSL-only desync, and context pollution in the shader-nodes plugin.

**Architecture:** Plugin source at `C:/Users/gruku/Files/Claude/claude-tools/plugins/shader-nodes/`. All changes go to source first, then synced to cache at `C:/Users/gruku/.claude/plugins/cache/gruku-tools/shader-nodes/2.0.0/`.

**Tech Stack:** Markdown (skill prompts), Python (generator script), YAML (node definitions)

---

### Task 1: Delete Duplicate Commands

**Files:**
- Delete: `commands/create.md`
- Delete: `commands/edit.md`
- Delete: `commands/yaml.md`
- Delete: `commands/registry.md`

**Step 1: Delete command files from plugin source**

```bash
rm commands/create.md commands/edit.md commands/yaml.md commands/registry.md
```

**Step 2: Delete from plugin cache**

```bash
rm ~/.claude/plugins/cache/gruku-tools/shader-nodes/2.0.0/commands/create.md
rm ~/.claude/plugins/cache/gruku-tools/shader-nodes/2.0.0/commands/edit.md
rm ~/.claude/plugins/cache/gruku-tools/shader-nodes/2.0.0/commands/yaml.md
rm ~/.claude/plugins/cache/gruku-tools/shader-nodes/2.0.0/commands/registry.md
```

**Step 3: Verify no commands remain**

```bash
ls commands/
ls ~/.claude/plugins/cache/gruku-tools/shader-nodes/2.0.0/commands/
```

Expected: Both directories either empty or nonexistent.

---

### Task 2: Update `skills/create/SKILL.md` — Remove HLSL-Only Skip + Add Context Rules

**Files:**
- Modify: `skills/create/SKILL.md`

**Step 1: Update Phase 2 to always run after Phase 1**

In Phase 4 (Iteration), remove the "HLSL-only" fast path that skips the Generator. Change all iteration paths to always dispatch Generator after Architect:

Old iteration table section "2. For HLSL-only changes (fast path)" — remove the instruction to skip Generator. Replace with: "Re-dispatch Architect with hlsl_only: true, then ALWAYS dispatch Generator afterward to regenerate ue5_clipboard.txt."

Old iteration table section "3. For topology changes" — keep as-is (full chain).

**Step 2: Add context isolation rules to Phase 3 (Report to User)**

After the report template, add:

```markdown
**Context Isolation Rules:**
- Do NOT paste HLSL code, YAML, or clipboard content into the main conversation
- Report ONLY the summary table and file paths — the user reads files directly
- NEVER read `ue5_clipboard.txt` — these are 100KB+ files that destroy context
- Only read clipboard files if the user explicitly requests it for debugging
```

**Step 3: Update the iteration classification table**

The table should show that ALL paths end with Generator:

| User Says | Scope | What to Re-dispatch |
|-----------|-------|-------------------|
| "Make the edge softer" | HLSL only | Architect (hlsl_only) → Generator |
| "Add a glow output" | Topology change | Architect (full) → Generator |
| "Change the default radius to 0.5" | Constant value | Edit YAML directly, re-run converter |

---

### Task 3: Update `skills/create/hlsl-architect-prompt.md` — Add Self-Review

**Files:**
- Modify: `skills/create/hlsl-architect-prompt.md`

**Step 1: Add self-review step between Step 2 (Write HLSL) and Step 3 (Save Files)**

Insert as new "Step 2.5: Self-Review" after the HLSL writing step:

```markdown
### Step 2.5: Self-Review (MANDATORY)

Before saving files, review your own work against these checklists. Fix any issues found.

**Correctness:**
- [ ] Walk through the math — are SDF calculations geometrically correct?
- [ ] Do animations trigger at the right time and reach correct end states?
- [ ] Edge cases: UV at 0 and 1 boundaries, time=0, duration=0, division by zero?
- [ ] Are all output values in expected ranges (0-1 for masks, valid SDF distances)?

**UE5 Patterns:**
- [ ] Using `saturate()` not `clamp(x, 0, 1)`?
- [ ] Using `lerp()` not manual interpolation?
- [ ] Float4 packing groups related parameters logically?
- [ ] NO `fwidth()`, `ddx()`, `ddy()`, `smoothstep()` for edge AA — output raw SDF instead?
- [ ] Y-axis direction: UE5 UV has Y=0 at TOP, Y increases DOWNWARD
  - "Up" visually = negative Y
  - Gravity "down" = positive Y
  - Launch/velocity "up" = negative Y component
  - Verify ALL directional calculations account for this

**Quality:**
- [ ] Is this the most effective technique for the request?
- [ ] Could SDF combinations, polar coordinates, or noise improve the result?
- [ ] Are variable names descriptive and consistent with the design spec?
- [ ] Is the code well-structured with logical sections?

If any check fails, revise the code before proceeding to Step 3.
```

---

### Task 4: Update `skills/create/hlsl-conventions.md` — Add UV Y-Axis Convention

**Files:**
- Modify: `skills/create/hlsl-conventions.md`

**Step 1: Add UV Y-axis warning to the UV Space Conventions section**

After the existing "Standard UE5 UV" subsection (line 176-179), add:

```markdown
### Y-Axis Direction (CRITICAL)

UE5 UV Y-axis is inverted compared to standard math conventions:

| Visual Direction | UV Direction | Y Value |
|-----------------|-------------|---------|
| Up on screen | Negative Y | Decreasing |
| Down on screen | Positive Y | Increasing |

This affects ALL directional calculations:
- **Gravity** pulling down = positive Y delta
- **Launch/velocity** going up = negative Y component
- **Particle motion** upward = subtract from Y
- **Light coming from above** = negative Y direction

```hlsl
// CORRECT: Particle launching upward then falling with gravity
float2 velocity = float2(launchDirX, -abs(launchDirY));  // Negative Y = up
float2 gravity = float2(0.0, gravityStrength);            // Positive Y = down
float2 pos = startPos + velocity * t + 0.5 * gravity * t * t;

// WRONG: Standard math convention (Y-up)
// float2 velocity = float2(launchDirX, abs(launchDirY));  // Would go DOWN
// float2 gravity = float2(0.0, -gravityStrength);          // Would pull UP
```

**Self-review requirement:** After writing any shader with directional motion, explicitly verify Y-axis directions are correct for UE5's top-down UV space.
```

---

### Task 5: Update `skills/create/node-generator-prompt.md` — Add `contains` + Clipboard Rules

**Files:**
- Modify: `skills/create/node-generator-prompt.md`

**Step 1: Update Comment node YAML template**

In the YAML template section, update the Comment node example to use `contains`:

```yaml
  # --- COMMENT BOXES ---
  # Comments auto-position around their contained nodes.
  # ALWAYS specify `contains` with the list of node names this comment should wrap.
  - name: Comment_Inputs
    type: Comment
    text: "Shader Inputs"
    contains: [In1_CompX, In1_CompY, In1_CompZ, In1_CompW, In1_PackName, UV, Time]
    color: [0.15, 0.15, 0.15]

  - name: Comment_CustomNode
    type: Comment
    text: "ShaderName Custom Node"
    contains: [NodeName]
    color: [0.15, 0.15, 0.15]

  - name: Comment_Outputs
    type: Comment
    text: "Outputs"
    contains: [Out_OutputVarName, Out_SomeOther]
    color: [0.15, 0.15, 0.15]
```

Remove any hardcoded `size_x`/`size_y` from comment examples — the generator computes these automatically.

**Step 2: Add clipboard read prohibition**

After the "Step 5: Verify Output" section, add:

```markdown
### IMPORTANT: Do NOT Read Clipboard Files

After generating `ue5_clipboard.txt`, verify it exists and check file size only:

```bash
ls -la ue5_clipboard.txt
```

Do NOT read the file contents. These files are 100KB+ and will destroy agent context. Only read them if explicitly asked for debugging.
```

---

### Task 6: Fix `ue5_material_generator.py` — Comment Positioning + Validation

**Files:**
- Modify: `ue5_material_generator.py`

This is the largest task. The changes are:

**Step 1: Add `contains_nodes` to CommentNode**

In the `CommentNode` class constructor (around line 730), add a `contains_nodes` parameter:

```python
class CommentNode(MaterialNode):
    def __init__(self, name, text, node_index, size_x=400, size_y=300,
                 color=(1, 1, 1), contains_nodes=None, **kwargs):
        # ... existing init ...
        self.contains_nodes = contains_nodes or []
```

**Step 2: Exclude Comments from depth-based layout**

In `_compute_layout()` (around line 830), skip Comment nodes when building the depth graph:

```python
# Build adjacency only for non-Comment nodes
for name, node in self.nodes.items():
    if isinstance(node, CommentNode):
        continue
    # ... existing depth logic ...
```

**Step 3: Add post-layout comment positioning pass**

After `_compute_layout()` positions all regular nodes, add a new method `_position_comments()`:

```python
def _position_comments(self):
    PADDING = 80
    TITLE_HEIGHT = 40
    NODE_WIDTH_EST = 250
    NODE_HEIGHT_EST = 150

    for name, node in self.nodes.items():
        if not isinstance(node, CommentNode):
            continue
        if self._manual_positions.get(name, False):
            continue  # User specified explicit position

        if node.contains_nodes:
            # Compute bounding box from contained nodes
            contained = [self.nodes[n] for n in node.contains_nodes if n in self.nodes]
            if not contained:
                print(f"Warning: Comment '{name}' contains no valid nodes")
                continue
            min_x = min(n.pos_x for n in contained)
            min_y = min(n.pos_y for n in contained)
            max_x = max(n.pos_x for n in contained)
            max_y = max(n.pos_y for n in contained)

            node.pos_x = min_x - PADDING
            node.pos_y = min_y - PADDING - TITLE_HEIGHT
            node.size_x = (max_x - min_x) + NODE_WIDTH_EST + PADDING * 2
            node.size_y = (max_y - min_y) + NODE_HEIGHT_EST + PADDING * 2 + TITLE_HEIGHT
        else:
            # Auto-grouping fallback
            self._auto_group_comment(node)
```

**Step 4: Add auto-grouping fallback**

```python
def _auto_group_comment(self, comment_node):
    """Fallback: group nodes by naming convention or connectivity."""
    PADDING = 80
    TITLE_HEIGHT = 40
    NODE_WIDTH_EST = 250
    NODE_HEIGHT_EST = 150

    text_lower = comment_node.text.lower()
    matched = []

    # Naming convention matching
    for name, node in self.nodes.items():
        if isinstance(node, CommentNode):
            continue
        if 'input' in text_lower and (name.startswith('In') or isinstance(node, (ConstantNode, MakeFloatNode))):
            matched.append(node)
        elif 'output' in text_lower and name.startswith('Out'):
            matched.append(node)
        elif 'custom' in text_lower and isinstance(node, CustomNode):
            matched.append(node)

    if not matched:
        # Connectivity fallback: find the largest connected subgraph not covered by other comments
        # For now, leave unpositioned with a warning
        print(f"Warning: Comment '{comment_node.name}' could not auto-detect contained nodes")
        return

    min_x = min(n.pos_x for n in matched)
    min_y = min(n.pos_y for n in matched)
    max_x = max(n.pos_x for n in matched)
    max_y = max(n.pos_y for n in matched)

    comment_node.pos_x = min_x - PADDING
    comment_node.pos_y = min_y - PADDING - TITLE_HEIGHT
    comment_node.size_x = (max_x - min_x) + NODE_WIDTH_EST + PADDING * 2
    comment_node.size_y = (max_y - min_y) + NODE_HEIGHT_EST + PADDING * 2 + TITLE_HEIGHT
```

**Step 5: Wire up the new pass in `build()`**

In the `build()` method, call `_position_comments()` after `_compute_layout()`:

```python
def build(self):
    self._create_nodes()
    self._wire_connections()
    self._compute_layout()
    self._position_comments()  # NEW
    return self._generate_output()
```

**Step 6: Update `_create_node()` for Comment `contains` parameter**

In the Comment case of `_create_node()` (around line 1012), pass `contains_nodes`:

```python
elif node_type == 'Comment':
    node = CommentNode(
        name=name,
        text=node_def.get('text', ''),
        node_index=self.comment_index,
        size_x=node_def.get('size_x', 400),
        size_y=node_def.get('size_y', 300),
        color=tuple(node_def.get('color', [1, 1, 1])),
        contains_nodes=node_def.get('contains', []),
        **common_kwargs
    )
```

**Step 7: Add pin name mismatch warning**

In `_connect_nodes()`, after the fallback to first pin (around line 1101-1106), add a warning:

```python
if not source_pin:
    for pin in source.pins:
        if pin.direction == "EGPD_Output":
            source_pin = pin
            print(f"Warning: Output '{source_output}' not found on '{source_name}', falling back to first output pin '{pin.pin_name}'")
            break
```

Same for target pin fallback (around line 1122-1127):

```python
if not target_pin:
    for pin in target.pins:
        if pin.direction == "EGPD_Input":
            target_pin = pin
            print(f"Warning: Input '{target_input}' not found on '{target_name}', falling back to first input pin '{pin.pin_name}'")
            break
```

**Step 8: Add array length validation**

Before Constant3Vector creation (around line 941):

```python
elif node_type == 'Constant3Vector':
    value = node_def.get('value', [0, 0, 0])
    if len(value) < 3:
        print(f"Warning: Constant3Vector '{name}' needs 3 values, got {len(value)}. Padding with zeros.")
        value = list(value) + [0] * (3 - len(value))
```

Before Constant4Vector creation (around line 952):

```python
elif node_type == 'Constant4Vector':
    value = node_def.get('value', [0, 0, 0, 0])
    if len(value) < 4:
        print(f"Warning: Constant4Vector '{name}' needs 4 values, got {len(value)}. Padding with zeros.")
        value = list(value) + [0] * (4 - len(value))
```

**Step 9: Add null-check on yaml_data**

At the top of `build()` or `__init__()`, after `yaml.safe_load()`:

```python
yaml_data = yaml.safe_load(f)
if yaml_data is None:
    raise ValueError(f"YAML file is empty or invalid: {yaml_path}")
```

---

### Task 7: Sync All Changes to Plugin Cache

**Files:**
- All modified files in source → copy to cache

**Step 1: Sync all modified files**

```bash
# From plugin source to cache
SRC="C:/Users/gruku/Files/Claude/claude-tools/plugins/shader-nodes"
CACHE="C:/Users/gruku/.claude/plugins/cache/gruku-tools/shader-nodes/2.0.0"

cp "$SRC/skills/create/SKILL.md" "$CACHE/skills/create/SKILL.md"
cp "$SRC/skills/create/hlsl-architect-prompt.md" "$CACHE/skills/create/hlsl-architect-prompt.md"
cp "$SRC/skills/create/hlsl-conventions.md" "$CACHE/skills/create/hlsl-conventions.md"
cp "$SRC/skills/create/node-generator-prompt.md" "$CACHE/skills/create/node-generator-prompt.md"
cp "$SRC/ue5_material_generator.py" "$CACHE/ue5_material_generator.py"
```

**Step 2: Verify sync**

```bash
diff -r "$SRC/skills" "$CACHE/skills"
diff "$SRC/ue5_material_generator.py" "$CACHE/ue5_material_generator.py"
```

Expected: No differences.
