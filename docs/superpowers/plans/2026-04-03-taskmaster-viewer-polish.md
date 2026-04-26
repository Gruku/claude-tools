# Taskmaster Viewer Polish — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix sorting, add phase deliverables checklist, improve phase discovery/enforcement, add archived scroll, docs zoom, and progress bar polish.

**Architecture:** All viewer UI changes happen in `backlog-viewer.html` (single-file viewer app). Server-side changes in `backlog_server.py` for phase enforcement, deliverables, and docs zoom. YAML schema gains `phases[].deliverables` array field.

**Tech Stack:** Python (backlog_server.py), vanilla JS/HTML/CSS (backlog-viewer.html), YAML (backlog.yaml)

---

## File Map

| File | Changes |
|------|---------|
| `plugins/taskmaster/backlog-viewer.html` | Sort fix, phase deliverables UI, "No phase" filter, archived scroll, progress bar polish, phase overflow |
| `plugins/taskmaster/backlog_server.py` | Fuzzy `_find_phase`, phase enforcement on add_task, deliverables field support, `backlog_advance_phase` blocking, docs zoom template, backfill `created` |
| `plugins/taskmaster/backlog.yaml` | No direct edits — schema changes via server tools |

---

### Task 1: Fix timestamp-based sorting in viewer

The sort comparators for `created`, `started`, `completed`, and `updated` access single fields. Most tasks only have 1-2 of these populated, so within a kanban column most pairs return `0` (both empty → no reorder). Fix: use a fallback chain so every task resolves to _some_ timestamp.

**Files:**
- Modify: `plugins/taskmaster/backlog-viewer.html:2554-2584`

- [ ] **Step 1: Replace the `tsCompare` function and `sorters` object**

Find the sort block at line 2554 and replace it entirely:

```javascript
  // Sort — all modes support ascending/descending via sortAsc toggle
  const pOrder = { P0: 0, P1: 1, P2: 2, P3: 3 };
  const dir = sortAsc ? 1 : -1;
  // Resolve the best available timestamp for a task given a preferred field
  const tsResolve = (task, pref) => {
    if (pref === 'created')   return task.created || task.started || task.completed || '';
    if (pref === 'started')   return task.started || task.created || task.completed || '';
    if (pref === 'completed') return task.completed || task.started || task.created || '';
    return task.completed || task.started || task.created || '';
  };
  const tsCompare = (field) => (a, b) => {
    const av = tsResolve(a, field);
    const bv = tsResolve(b, field);
    // Push empty values to the end regardless of direction
    if (!av && bv) return 1;
    if (av && !bv) return -1;
    if (!av && !bv) return 0;
    return dir * av.localeCompare(bv);
  };
  const sorters = {
    'priority': (a, b) => dir * ((pOrder[a.priority?.toUpperCase()] ?? 3) - (pOrder[b.priority?.toUpperCase()] ?? 3)),
    'created':   tsCompare('created'),
    'started':   tsCompare('started'),
    'completed': tsCompare('completed'),
    'updated': (a, b) => {
      const aTs = tsResolve(a, 'updated');
      const bTs = tsResolve(b, 'updated');
      if (!aTs && bTs) return 1;
      if (aTs && !bTs) return -1;
      if (!aTs && !bTs) return 0;
      return dir * aTs.localeCompare(bTs);
    },
    'alpha': (a, b) => dir * (a.title || '').localeCompare(b.title || ''),
  };
  if (sorters[sortMode]) {
    tasks = [...tasks].sort(sorters[sortMode]);
  }
```

- [ ] **Step 2: Verify in browser**

Open the viewer, switch sort to "Created", confirm tasks reorder visibly within columns. Switch to "Started", "Completed", "Updated" — each should produce visible ordering. Priority and Alpha should still work as before.

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/backlog-viewer.html
git commit -m "fix(taskmaster): sort by created/started/completed uses fallback timestamp chain"
```

---

### Task 2: Backfill missing `created` timestamps on server load

Tasks added before `created` was implemented lack the field. Backfill them during `_load()` so all tasks have a `created` value. Use the task's `started` or `completed` date, or fall back to the epoch of the oldest task in the backlog.

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py:95-135` (the `_load` function area)

- [ ] **Step 1: Find the `_load` function and add backfill logic**

The `_load()` function returns parsed YAML data. Add a backfill pass after loading. Find where `_load` returns and add this before the return:

```python
    # Backfill missing 'created' on tasks
    for epic in data.get("epics", []):
        for t in epic.get("tasks", []):
            if not t.get("created"):
                t["created"] = t.get("started") or t.get("completed") or "2025-01-01T00:00"
```

This is a read-time backfill — it does NOT write to disk. The field appears in API responses and viewer data but doesn't mutate the YAML until the task is next saved via a mutation operation.

- [ ] **Step 2: Verify by hitting `/api/backlog` and checking that all tasks have `created`**

```bash
curl -s http://127.0.0.1:<PORT>/api/backlog | python -c "import sys,json; data=json.load(sys.stdin); missing=[t['id'] for e in data['epics'] for t in e.get('tasks',[]) if not t.get('created')]; print(f'{len(missing)} tasks missing created') if missing else print('All tasks have created')"
```

Expected: `All tasks have created`

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/backlog_server.py
git commit -m "fix(taskmaster): backfill missing created timestamps on load"
```

---

### Task 3: Phase deliverables — YAML model + MCP tools

Add `deliverables` field to phases. Each deliverable is `{text: str, done: bool}`. Update `backlog_update_phase` to manage them. Make `backlog_advance_phase` block when unchecked deliverables remain (with override flag).

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py:1876-1877` (constants)
- Modify: `plugins/taskmaster/backlog_server.py:1948-1993` (`backlog_update_phase`)
- Modify: `plugins/taskmaster/backlog_server.py:2131-2205` (`backlog_advance_phase`)
- Modify: `plugins/taskmaster/backlog_server.py:1997-2127` (`backlog_phase_status`)

- [ ] **Step 1: Add `deliverables` to `ALLOWED_PHASE_FIELDS`**

At line 1877, change:

```python
ALLOWED_PHASE_FIELDS = {"name", "status", "description", "order", "target_date", "start_date"}
```

to:

```python
ALLOWED_PHASE_FIELDS = {"name", "status", "description", "order", "target_date", "start_date", "deliverables"}
```

- [ ] **Step 2: Add deliverables handling in `backlog_update_phase`**

In `backlog_update_phase`, before the final `else: ph[field] = value` fallback (around line 1990), add a new `elif` branch:

```python
    elif field == "deliverables":
        # value is a JSON string: {"action": "add"|"remove"|"toggle"|"set", ...}
        import json as _json
        try:
            cmd = _json.loads(value)
        except (ValueError, TypeError):
            return "Error: deliverables value must be JSON — {\"action\": \"add\", \"text\": \"...\"}"

        deliverables = ph.setdefault("deliverables", [])
        action = cmd.get("action", "")

        if action == "add":
            text = cmd.get("text", "").strip()
            if not text:
                return "Error: deliverable text is required"
            deliverables.append({"text": text, "done": False})
        elif action == "remove":
            idx = cmd.get("index")
            if idx is None or not isinstance(idx, int) or idx < 0 or idx >= len(deliverables):
                return f"Error: invalid index {idx} — phase has {len(deliverables)} deliverables"
            deliverables.pop(idx)
        elif action == "toggle":
            idx = cmd.get("index")
            if idx is None or not isinstance(idx, int) or idx < 0 or idx >= len(deliverables):
                return f"Error: invalid index {idx} — phase has {len(deliverables)} deliverables"
            deliverables[idx]["done"] = not deliverables[idx]["done"]
        elif action == "set":
            # Replace entire list — value.items is [{text, done}, ...]
            items = cmd.get("items", [])
            ph["deliverables"] = [{"text": str(d.get("text", "")), "done": bool(d.get("done", False))} for d in items]
        else:
            return f"Error: unknown deliverables action `{action}`. Use: add, remove, toggle, set"
```

- [ ] **Step 3: Add deliverables rendering in `backlog_phase_status`**

In `backlog_phase_status`, after the progress bar rendering (around line 2095), add deliverables display:

```python
    # Deliverables checklist
    deliverables = ph.get("deliverables", [])
    if deliverables:
        lines.append("")
        lines.append("**Deliverables:**")
        for i, d in enumerate(deliverables):
            check = "x" if d.get("done") else " "
            lines.append(f"  - [{check}] {d['text']}")
        done_count = sum(1 for d in deliverables if d.get("done"))
        lines.append(f"  ({done_count}/{len(deliverables)} complete)")
```

- [ ] **Step 4: Add deliverables gate in `backlog_advance_phase`**

In `backlog_advance_phase`, after finding the active phase and computing stats (around line 2143), add a blocking check before the warning for incomplete tasks:

```python
    # Block if deliverables are incomplete (unless force=True)
    deliverables = active_ph.get("deliverables", [])
    unchecked = [d for d in deliverables if not d.get("done")]
    if unchecked and not force:
        items = "\n".join(f"  - [ ] {d['text']}" for d in unchecked)
        return (
            f"**Blocked:** {len(unchecked)} unchecked deliverable(s) in phase "
            f"**{active_ph['name']}**:\n{items}\n\n"
            f"Check them off with `backlog_update_phase(phase_id=\"{active_ph['id']}\", "
            f"field=\"deliverables\", value='{{\"action\":\"toggle\",\"index\":N}}')` "
            f"or advance with force=True."
        )
```

Also add `force: bool = False` parameter to the function signature:

```python
@mcp.tool()
def backlog_advance_phase(force: bool = False) -> str:
    """Complete the active phase and activate the next one in sequence.
    Archives all 'done' tasks in the completed phase. Activates the next 'planned' phase by order.
    Blocks if phase has unchecked deliverables unless force=True.

    Args:
        force: If True, advance even if deliverables are incomplete.
    """
```

- [ ] **Step 5: Verify deliverables flow via MCP**

```
backlog_update_phase(phase_id="p1", field="deliverables", value='{"action":"add","text":"All parsers tested"}')
backlog_update_phase(phase_id="p1", field="deliverables", value='{"action":"add","text":"Demo recorded"}')
backlog_phase_status(phase_id="p1")
# Should show two unchecked deliverables
backlog_update_phase(phase_id="p1", field="deliverables", value='{"action":"toggle","index":0}')
backlog_phase_status(phase_id="p1")
# First deliverable should now be [x]
backlog_advance_phase()
# Should block: 1 unchecked deliverable
```

- [ ] **Step 6: Commit**

```bash
git add plugins/taskmaster/backlog_server.py
git commit -m "feat(taskmaster): phase deliverables checklist with advance-blocking gate"
```

---

### Task 4: Phase deliverables — viewer UI

Render the deliverables checklist in the phase banner area. Clicking a checkbox toggles the deliverable via the server API.

**Files:**
- Modify: `plugins/taskmaster/backlog-viewer.html:2201-2224` (active phase banner rendering)
- Modify: `plugins/taskmaster/backlog-viewer.html` (CSS section, around line 434)

- [ ] **Step 1: Add deliverables CSS**

After the `.phase-banner .ms-stats` rule (around line 484), add:

```css
.phase-deliverables {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 6px 0 2px;
  width: 100%;
}

.phase-deliverable-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--fs-xs);
  color: var(--text-muted);
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
  transition: background 0.15s;
}

.phase-deliverable-item:hover {
  background: var(--surface2);
}

.phase-deliverable-item input[type="checkbox"] {
  accent-color: var(--accent);
  cursor: pointer;
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

.phase-deliverable-item.done {
  text-decoration: line-through;
  color: var(--text-dim);
}

.phase-deliverable-summary {
  font-size: var(--fs-xs);
  color: var(--text-dim);
  font-weight: 600;
  padding-top: 2px;
}
```

- [ ] **Step 2: Render deliverables in the phase banner**

In `renderPhases()`, inside the active/planned phase branch (after the `banner.innerHTML +=` block around line 2222), add deliverables rendering. Find the closing of the phase-banner template literal and add after it:

```javascript
    // Render deliverables if present
    const deliverables = displayed.deliverables || [];
    if (deliverables.length > 0) {
      const doneCount = deliverables.filter(d => d.done).length;
      let delHtml = '<div class="phase-deliverables">';
      deliverables.forEach((d, i) => {
        const checked = d.done ? 'checked' : '';
        const doneCls = d.done ? ' done' : '';
        delHtml += `<label class="phase-deliverable-item${doneCls}">` +
          `<input type="checkbox" ${checked} data-del-phase="${esc(displayed.id)}" data-del-idx="${i}">` +
          `<span>${esc(d.text)}</span></label>`;
      });
      delHtml += `<span class="phase-deliverable-summary">${doneCount}/${deliverables.length} deliverables complete</span>`;
      delHtml += '</div>';
      banner.innerHTML += delHtml;
    }
```

- [ ] **Step 3: Add click handler for deliverable checkboxes**

After the phase step click handler section (around line 3180), add:

```javascript
// ── Deliverable checkbox toggle ──────────────────────────
document.getElementById('phase-banner').addEventListener('change', async (e) => {
  const cb = e.target;
  if (!cb.dataset.delPhase) return;
  const phaseId = cb.dataset.delPhase;
  const idx = parseInt(cb.dataset.delIdx, 10);
  try {
    const resp = await fetch(`/api/backlog`, { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tool: 'backlog_update_phase', args: { phase_id: phaseId, field: 'deliverables', value: JSON.stringify({ action: 'toggle', index: idx }) } })
    });
    // Refresh data
    await refreshData();
  } catch (err) {
    console.error('Failed to toggle deliverable:', err);
    cb.checked = !cb.checked; // revert on failure
  }
});
```

**Note:** This requires a POST endpoint on the server. Check if one exists — if not, the toggle needs to work via a different mechanism. Alternative: use a WebSocket or simply refetch data and re-render. The simplest approach may be to add a minimal POST handler. Check how the viewer currently communicates with the server — if it's read-only (only GET `/api/backlog`), we need to add a POST route. If there's no mutation API, an alternative is to show deliverables as read-only in the viewer (toggle via MCP only).

**Decision point:** If the viewer is read-only (no POST API), render deliverables as read-only display in the viewer. The MCP tools handle mutations. Add a tooltip: "Toggle via Claude: backlog_update_phase(...)". This avoids adding a mutation API to the viewer server, which is currently read-only by design.

- [ ] **Step 4: Verify in browser**

Open the viewer. If the active phase has deliverables (added in Task 3 step 5), they should appear below the progress bar as a checklist. Visual check: items are compact, checked items have line-through styling.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog-viewer.html
git commit -m "feat(taskmaster): render phase deliverables checklist in viewer banner"
```

---

### Task 5: Phase discovery — fuzzy matching in `_find_phase`

Change `_find_phase` to match by name (case-insensitive, whitespace-normalized) when exact ID match fails. This fixes the pain from the log where `"pre-alpha"` and `"before-plugin-deployment"` failed but `"p1"` worked.

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py:137-141`

- [ ] **Step 1: Replace `_find_phase` with fuzzy version**

Replace lines 137-141:

```python
def _find_phase(data: dict, phase_id: str) -> dict | None:
    """Find a phase by ID (exact) or name (case-insensitive, whitespace-normalized)."""
    phases = data.get("phases", [])
    # Exact ID match first
    for ph in phases:
        if ph["id"] == phase_id:
            return ph
    # Fuzzy: case-insensitive name match
    needle = phase_id.strip().lower().replace("-", " ").replace("_", " ")
    for ph in phases:
        name = ph.get("name", "").strip().lower().replace("-", " ").replace("_", " ")
        if name == needle:
            return ph
    # Partial: needle is a substring of the name
    for ph in phases:
        name = ph.get("name", "").strip().lower().replace("-", " ").replace("_", " ")
        if needle in name or name in needle:
            return ph
    return None
```

- [ ] **Step 2: Verify fuzzy matching**

Test with the exact scenario from the log:
```
backlog_update_task(task_id="<any-task>", field="phase", value="pre-alpha")
```
This should now resolve to the phase named "Pre-Alpha" (or similar) instead of returning "Error: phase `pre-alpha` not found".

Also test that exact ID matching still works:
```
backlog_update_task(task_id="<any-task>", field="phase", value="p1")
```

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/backlog_server.py
git commit -m "feat(taskmaster): fuzzy phase matching by name when exact ID fails"
```

---

### Task 6: Phase enforcement — require phase on `backlog_add_task` + "No phase" filter in viewer

Make `backlog_add_task` reject tasks without a phase. Add a "No phase" filter option in the viewer to surface orphaned tasks.

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py:1171-1174`
- Modify: `plugins/taskmaster/backlog-viewer.html` (phase dropdown area, around line 3190)

- [ ] **Step 1: Enforce phase in `backlog_add_task`**

Replace lines 1171-1174:

```python
    if not phase:
        return "Error: `phase` is required — every task must belong to a phase. Use `backlog_phase_status()` to see available phases."
    if not _find_phase(data, phase):
        return f"Error: phase `{phase}` not found. Use `backlog_phase_status()` to see available phases."
    new_task["phase"] = phase
```

Note: `_find_phase` now does fuzzy matching (Task 5), so users can pass phase names too.

- [ ] **Step 2: Add "No phase" option in the viewer phase dropdown**

In the phase dropdown population code (around line 3200 in `populatePhaseDropdown()`), add a "No phase" option. Find where phase options are generated and add after the "All phases" option:

```javascript
    // Add "No phase" option to surface orphaned tasks
    const noPhaseCount = allTasks.filter(t => !t.phase && colKey(t.status) !== 'archived').length;
    if (noPhaseCount > 0) {
      const opt = document.createElement('div');
      opt.className = 'phase-dropdown-item' + (activePhase === '__none__' ? ' active' : '');
      opt.dataset.phaseId = '__none__';
      opt.innerHTML = `<span style="color:var(--text-dim);font-style:italic">No phase</span> <span class="phase-dropdown-count">${noPhaseCount}</span>`;
      dropdown.appendChild(opt);
    }
```

- [ ] **Step 3: Handle `__none__` filter in the render function**

In the `render()` function's phase filtering (around line 2529), add handling for the `__none__` sentinel:

```javascript
  // Phase filter
  if (activePhase === '__none__') {
    tasks = tasks.filter(t => !t.phase);
  } else if (activePhase !== 'all') {
    tasks = tasks.filter(t => t.phase === activePhase);
  }
```

- [ ] **Step 4: Verify**

1. Try `backlog_add_task(title="Test", epic="...")` without phase — should get error message.
2. Try `backlog_add_task(title="Test", epic="...", phase="Pre-Alpha")` — should work via fuzzy match.
3. Open viewer — if any tasks lack a phase, the "No phase" option should appear in the phase dropdown. Clicking it should filter to only those tasks.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/backlog-viewer.html
git commit -m "feat(taskmaster): require phase on task creation + 'No phase' viewer filter"
```

---

### Task 7: Archived tasks scroll

The archived grid uses `max-height: 2000px` when open, which shows everything at once with no scroll. With many archived tasks, this pushes the page down excessively. Add a capped height with scroll.

**Files:**
- Modify: `plugins/taskmaster/backlog-viewer.html` (CSS around line 1115)

- [ ] **Step 1: Change archived grid CSS**

Find the `.archived-grid.open` rule (around line 1115):

```css
.archived-grid.open {
  max-height: 2000px;
}
```

Replace with:

```css
.archived-grid.open {
  max-height: 50vh;
  overflow-y: auto;
}
```

Also do the same for `.archived-epics-grid.open` (around line 1155):

```css
.archived-epics-grid.open {
  max-height: 50vh;
  overflow-y: auto;
}
```

- [ ] **Step 2: Add scrollbar styling for dark theme**

After the archived grid rules, add:

```css
.archived-grid::-webkit-scrollbar,
.archived-epics-grid::-webkit-scrollbar {
  width: 6px;
}

.archived-grid::-webkit-scrollbar-thumb,
.archived-epics-grid::-webkit-scrollbar-thumb {
  background: var(--border);
  border-radius: 3px;
}

.archived-grid::-webkit-scrollbar-track,
.archived-epics-grid::-webkit-scrollbar-track {
  background: transparent;
}
```

- [ ] **Step 3: Verify in browser**

Open the viewer, expand the archived section. If there are many archived tasks, the section should cap at 50% viewport height with a scrollbar. If few tasks, no scrollbar appears.

- [ ] **Step 4: Commit**

```bash
git add plugins/taskmaster/backlog-viewer.html
git commit -m "feat(taskmaster): scrollable archived section capped at 50vh"
```

---

### Task 8: Docs preview zoom with localStorage persistence

The markdown preview served at `/file/*.md` has no zoom controls. Add `+`/`-`/reset buttons in the topbar and persist the zoom level in `localStorage`.

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py:2619-2661` (`_MD_TEMPLATE`)

- [ ] **Step 1: Replace the `_MD_TEMPLATE` with zoom-enabled version**

Replace the entire `_MD_TEMPLATE` string (lines 2619-2661) with:

```python
_MD_TEMPLATE = """<!DOCTYPE html>
<html><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{TITLE}}</title>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#141920;color:#d4dae3;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;font-size:14px;line-height:1.6;padding:0}
.topbar{background:#1c222b;border-bottom:1px solid #363e4a;padding:10px 24px;display:flex;align-items:center;gap:10px;position:sticky;top:0;z-index:10}
.topbar a{color:#58a6ff;text-decoration:none;font-size:13px;font-weight:600}
.topbar a:hover{text-decoration:underline}
.topbar .path{color:#97a0ad;font-family:"SFMono-Regular",Consolas,monospace;font-size:12px;flex:1}
.open-editor{background:#232a34;border:1px solid #363e4a;border-radius:4px;padding:4px 10px;font-size:12px !important;white-space:nowrap}
.open-editor:hover{background:#363e4a}
.zoom-controls{display:flex;align-items:center;gap:4px}
.zoom-btn{background:#232a34;border:1px solid #363e4a;border-radius:4px;padding:2px 8px;color:#d4dae3;cursor:pointer;font-size:13px;font-weight:600;line-height:1.4;min-width:26px;text-align:center}
.zoom-btn:hover{background:#363e4a}
.zoom-label{color:#97a0ad;font-size:11px;font-family:"SFMono-Regular",Consolas,monospace;min-width:36px;text-align:center}
.content{max-width:860px;margin:0 auto;padding:32px 24px;transition:font-size 0.15s ease}
h1,h2,h3,h4{color:#d4dae3;margin:20px 0 10px;line-height:1.3}
h1{font-size:1.7em;border-bottom:1px solid #363e4a;padding-bottom:8px}
h2{font-size:1.4em;border-bottom:1px solid #363e4a;padding-bottom:6px}
h3{font-size:1.15em}h4{font-size:1em;color:#97a0ad}
p{margin:8px 0}
a{color:#58a6ff}
code{font-family:"SFMono-Regular",Consolas,monospace;font-size:0.85em;background:#232a34;border:1px solid #363e4a;padding:1px 5px;border-radius:3px;color:#58a6ff}
pre{background:#0d1117;border:1px solid #363e4a;border-radius:6px;padding:14px 18px;overflow-x:auto;margin:12px 0}
pre code{background:none;border:none;padding:0;color:#d4dae3}
ul,ol{margin:8px 0;padding-left:22px}
li{margin:3px 0}
table{width:100%;border-collapse:collapse;margin:12px 0;font-size:0.93em}
th{text-align:left;padding:8px 12px;background:#232a34;border:1px solid #363e4a;font-weight:600}
td{padding:8px 12px;border:1px solid #363e4a}
tr:hover td{background:#1c222b}
blockquote{border-left:3px solid #58a6ff;padding:6px 14px;margin:10px 0;color:#97a0ad;background:#1c222b;border-radius:0 4px 4px 0}
hr{border:none;border-top:1px solid #363e4a;margin:20px 0}
strong{color:#d4dae3}
img{max-width:100%}
</style>
</head><body>
<div class="topbar">
  <a href="/">&larr; Backlog</a>
  <span class="path">{{TITLE}}</span>
  <div class="zoom-controls">
    <button class="zoom-btn" id="zoom-out" title="Zoom out">&minus;</button>
    <span class="zoom-label" id="zoom-label">100%</span>
    <button class="zoom-btn" id="zoom-in" title="Zoom in">+</button>
    <button class="zoom-btn" id="zoom-reset" title="Reset zoom">&#x21bb;</button>
  </div>
  <a href="vscode://file/{{FULL_PATH}}" class="open-editor">&#x1F4DD; Open in VSCode</a>
</div>
<div class="content" id="content"></div>
<script>
const raw = decodeURIComponent(atob("{{B64CONTENT}}").split('').map(c=>'%'+('00'+c.charCodeAt(0).toString(16)).slice(-2)).join(''));
document.getElementById('content').innerHTML = marked.parse(raw);

// Zoom
const ZOOM_KEY = 'taskmaster-docs-zoom';
const ZOOM_STEP = 10;
const ZOOM_MIN = 60;
const ZOOM_MAX = 200;
const BASE_SIZE = 14;
let zoomPct = parseInt(localStorage.getItem(ZOOM_KEY) || '100', 10);

function applyZoom() {
  zoomPct = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, zoomPct));
  document.getElementById('content').style.fontSize = (BASE_SIZE * zoomPct / 100) + 'px';
  document.getElementById('zoom-label').textContent = zoomPct + '%';
  localStorage.setItem(ZOOM_KEY, String(zoomPct));
}

document.getElementById('zoom-in').addEventListener('click', () => { zoomPct += ZOOM_STEP; applyZoom(); });
document.getElementById('zoom-out').addEventListener('click', () => { zoomPct -= ZOOM_STEP; applyZoom(); });
document.getElementById('zoom-reset').addEventListener('click', () => { zoomPct = 100; applyZoom(); });
applyZoom();
</script>
</body></html>"""
```

Key changes from the original:
- Heading sizes now use `em` units (relative to content font-size) instead of fixed `px` — so they scale with zoom
- `code` and `table` font sizes use `em` too
- `.content` gets `transition: font-size 0.15s ease` for smooth zoom
- Zoom controls in topbar: `−`, `+`, reset (`↻`), and percentage label
- `localStorage` key `taskmaster-docs-zoom` persists globally across all doc previews
- Range: 60%–200% in 10% steps

- [ ] **Step 2: Verify in browser**

Open any doc link from a task card. The topbar should show `− 100% + ↻` controls. Click `+` — text should grow. Refresh the page — zoom should persist. Open a different doc — same zoom level.

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/backlog_server.py
git commit -m "feat(taskmaster): docs preview zoom controls with localStorage persistence"
```

---

### Task 9: Progress bar polish + phase overflow handling

The progress bar is too short for phases with many tasks (2% of a small bar is invisible). Also, when there are many phases, the step chips can overflow.

**Files:**
- Modify: `plugins/taskmaster/backlog-viewer.html` (CSS around lines 434-530)

- [ ] **Step 1: Add minimum width to progress fill**

Find `.phase-banner .ms-progress-fill` (around line 475):

```css
.phase-banner .ms-progress-fill {
  height: 100%;
  background: var(--progress);
  border-radius: 4px;
  transition: width 0.4s ease;
}
```

Replace with:

```css
.phase-banner .ms-progress-fill {
  height: 100%;
  background: var(--progress);
  border-radius: 4px;
  transition: width 0.4s ease;
  min-width: 4px;
}
```

- [ ] **Step 2: Make the progress bar wider**

The progress bar has `flex: 1` and `min-width: 112px`. The issue is that `.ms-label`, `.ms-name`, and `.ms-stats` are all `white-space: nowrap` and eat up space. Increase the min-width and give the bar more priority.

Find `.phase-banner .ms-progress-bar` (around line 464):

```css
.phase-banner .ms-progress-bar {
  flex: 1;
  height: 8px;
  background: var(--border-subtle);
  border-radius: 4px;
  overflow: hidden;
  min-width: 112px;
}
```

Replace with:

```css
.phase-banner .ms-progress-bar {
  flex: 2;
  height: 8px;
  background: var(--border-subtle);
  border-radius: 4px;
  overflow: hidden;
  min-width: 180px;
}
```

`flex: 2` gives it double the growth factor compared to other flex items. `min-width: 180px` ensures visibility even on narrow screens.

- [ ] **Step 3: Make phase step chips horizontally scrollable on overflow**

Find `.phase-steps` (around line 486):

```css
.phase-steps {
  display: flex;
  gap: 4px;
  align-items: center;
  flex-wrap: wrap;
  margin-top: 0;
}
```

Replace with:

```css
.phase-steps {
  display: flex;
  gap: 4px;
  align-items: center;
  flex-wrap: nowrap;
  margin-top: 0;
  overflow-x: auto;
  max-width: 100%;
  scrollbar-width: thin;
}

.phase-steps::-webkit-scrollbar {
  height: 4px;
}

.phase-steps::-webkit-scrollbar-thumb {
  background: var(--border);
  border-radius: 2px;
}

.phase-steps::-webkit-scrollbar-track {
  background: transparent;
}
```

`flex-wrap: nowrap` + `overflow-x: auto` means chips stay in a single row and scroll horizontally when they overflow. The thin scrollbar keeps it subtle.

- [ ] **Step 4: Fix phase-row-left overflow**

The `.phase-row-left` is `position: absolute; left: 50%; transform: translateX(-50%)` which can overflow the container when there are many phases. Add overflow handling:

Find `.phase-row-left` (around line 515):

```css
.phase-row-left {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
}
```

Replace with:

```css
.phase-row-left {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: nowrap;
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  max-width: 60%;
  overflow-x: auto;
  scrollbar-width: none;
}

.phase-row-left::-webkit-scrollbar {
  display: none;
}
```

`max-width: 60%` prevents the centered step chips from overlapping the right-side banner. Hidden scrollbar keeps it clean — users scroll with trackpad/mousewheel.

- [ ] **Step 5: Update progress fill rendering to always show non-zero progress**

In `renderPhases()` (around line 2216), the fill width is `style="width:${pct}%"`. When `pct` rounds to `0` but there are done tasks, the CSS `min-width: 4px` handles it. But let's also make the percentage calculation more precise for the stats text:

Find the percentage calculation in `renderPhases()`:

```javascript
      const pct = total > 0 ? Math.round((done / total) * 100) : 0;
```

Replace with:

```javascript
      const pctRaw = total > 0 ? (done / total) * 100 : 0;
      const pct = total > 0 ? Math.max(done > 0 ? 1 : 0, Math.round(pctRaw)) : 0;
```

This ensures that if there's at least 1 done task, the percentage shows at least `1%` instead of rounding to `0%`.

- [ ] **Step 6: Verify in browser**

Open the viewer with a phase that has many tasks (e.g., 90 tasks, 2 done). The progress bar should be visibly wider than before, the fill should show a thin sliver (4px min + 1% width), and the stats should read "2/90 done (2%)". If you have many phases, the step chips should be scrollable horizontally without overflowing into the banner.

- [ ] **Step 7: Commit**

```bash
git add plugins/taskmaster/backlog-viewer.html
git commit -m "feat(taskmaster): wider progress bar with min-fill, scrollable phase chips"
```

---

## Execution Order

Tasks 1-2 (sorting) are independent of Tasks 3-6 (phases) and Tasks 7-9 (visual polish). Within each group:

- **Tasks 1-2:** Sequential (viewer fix first, then server backfill)
- **Tasks 3-4:** Sequential (server tools first, then viewer UI)
- **Tasks 5-6:** Sequential (fuzzy matching first, then enforcement relies on it)
- **Tasks 7, 8, 9:** Independent of each other

Parallel groups:
- Group A: Tasks 1, 2
- Group B: Tasks 3, 4, 5, 6
- Group C: Tasks 7, 8, 9

Groups A, B, C can run in parallel if using worktrees.
