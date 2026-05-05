# Milestone → Phase Rename + Sequential Phase Enhancements

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename "milestone" to "phase" throughout the taskmaster plugin, enforce sequential numbering, add prev/next phase context to descriptions, and redesign the viewer's phase visual to emphasize the current phase and show consecutive flow.

**Architecture:** Pure rename + enhancement across 3 layers: Python MCP server (`backlog_server.py`), HTML/CSS/JS viewer (`backlog-viewer.html`), and markdown skill/reference files. No schema migration tool yet — this changes the canonical schema going forward. Existing `backlog.yaml` files will need the top-level `milestones:` key and task-level `milestone:` fields renamed manually or via a future migration tool.

**Tech Stack:** Python (MCP server), HTML/CSS/JS (viewer), Markdown (skills/docs)

---

### Task 1: Rename helpers and constants in backlog_server.py

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py:137-172` (helper functions)
- Modify: `plugins/taskmaster/backlog_server.py:1538` (ALLOWED_FIELDS set)
- Modify: `plugins/taskmaster/backlog_server.py:1712-1713` (constants)

- [ ] **Step 1: Rename the 4 helper functions and their internals**

Replace in `backlog_server.py`:

```python
# Line 137-171: rename all 4 helpers

def _find_phase(data: dict, phase_id: str) -> dict | None:
    for ph in data.get("phases", []):
        if ph["id"] == phase_id:
            return ph
    return None


def _active_phase(data: dict) -> dict | None:
    """Return the currently active phase, or None."""
    for ph in data.get("phases", []):
        if ph.get("status") == "active":
            return ph
    return None


def _phase_task_ids(data: dict, phase_id: str) -> set[str]:
    """Get all task IDs assigned to a phase."""
    ids = set()
    for epic in data["epics"]:
        for t in epic.get("tasks", []):
            if t.get("phase") == phase_id:
                ids.add(t["id"])
    return ids


def _phase_stats(data: dict, phase_id: str) -> dict:
    """Compute stats for a specific phase."""
    counts = {"todo": 0, "in-progress": 0, "in-review": 0, "done": 0, "blocked": 0, "archived": 0}
    for epic in data["epics"]:
        for t in epic.get("tasks", []):
            if t.get("phase") == phase_id:
                s = t.get("status", "todo")
                counts[s] = counts.get(s, 0) + 1
    total = sum(counts.values()) - counts["archived"]
    return {"total": total, **counts}
```

- [ ] **Step 2: Rename the constants at line 1712-1713**

```python
VALID_PHASE_STATUSES = {"planned", "active", "done", "archived"}
ALLOWED_PHASE_FIELDS = {"name", "status", "description", "order", "target_date", "start_date"}
```

- [ ] **Step 3: Rename "milestone" to "phase" in the ALLOWED_FIELDS set at line 1538**

```python
ALLOWED_FIELDS = {"title", "status", "priority", "notes", "branch", "worktree", "blockers", "docs", "depends_on", "sub_repo", "stage", "estimate", "locked_by", "review_instructions", "phase"}
```

- [ ] **Step 4: Verify the file parses**

Run: `python -c "import ast; ast.parse(open('plugins/taskmaster/backlog_server.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py
git commit -m "refactor(taskmaster): rename milestone helpers and constants to phase"
```

---

### Task 2: Rename context update and dashboard functions in backlog_server.py

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py:278-290` (_update_context milestone block)
- Modify: `plugins/taskmaster/backlog_server.py:330-350` (regenerate_progress_dashboard milestone block)
- Modify: `plugins/taskmaster/backlog_server.py:496-518` (backlog_status milestone block)

- [ ] **Step 1: Rename _update_context milestone block (lines 278-290)**

```python
    # Phase context
    active_ph = _active_phase(data)
    if active_ph:
        ph_stats = _phase_stats(data, active_ph["id"])
        data["context"]["active_phase"] = {
            "id": active_ph["id"],
            "name": active_ph["name"],
            "stats": ph_stats,
            "target_date": active_ph.get("target_date"),
            "start_date": active_ph.get("start_date"),
        }
    else:
        data["context"]["active_phase"] = None
```

- [ ] **Step 2: Rename regenerate_progress_dashboard milestone block (lines 330-350)**

```python
    # Phase progress
    phases = data.get("phases", [])
    if phases:
        active_ph = _active_phase(data)
        if active_ph:
            ph_stats = _phase_stats(data, active_ph["id"])
            ph_done = ph_stats["done"]
            ph_total = ph_stats["total"]
            remaining = _time_remaining(active_ph.get("target_date"))
            target_info = f" — target: {active_ph['target_date']}" if active_ph.get("target_date") else ""
            if remaining:
                target_info += f" ({remaining})"
            lines.append(f"**Active Phase:** {active_ph['name']} ({ph_done}/{ph_total} done){target_info}")
        # List all phases briefly
        ph_summary = []
        for ph in sorted(phases, key=lambda m: m.get("order", 999)):
            s = ph.get("status", "planned")
            if s == "archived":
                continue
            label = {"active": ">>", "done": "done", "planned": "..."}.get(s, s)
```

(Continue renaming the variable `ms` → `ph` and `milestones` → `phases` through the rest of this block.)

- [ ] **Step 3: Rename backlog_status milestone block (lines 496-518)**

```python
    # Phase info
    phases = data.get("phases", [])
    active_ph = _active_phase(data)
    if active_ph:
        ph_stats = _phase_stats(data, active_ph["id"])
        ph_done = ph_stats["done"]
        ph_total = ph_stats["total"]
        remaining = _time_remaining(active_ph.get("target_date"))
        time_note = f" — {remaining}" if remaining else ""
        lines.append(f"\n**Active Phase:** {active_ph['name']} — {ph_done}/{ph_total} tasks done{time_note}")
        if active_ph.get("description"):
            lines.append(f"  {active_ph['description']}")
    if phases:
        lines.append("\n**Phases:**")
        for ph in sorted(phases, key=lambda m: m.get("order", 999)):
            s = ph.get("status", "planned")
            if s == "archived":
                continue
            ph_st = _phase_stats(data, ph["id"])
            marker = {"active": "▶", "done": "✓", "planned": "○"}.get(s, "?")
            target_note = f", target: {ph.get('target_date')}" if ph.get("target_date") else ""
            lines.append(f"- {marker} **{ph['name']}** ({ph_st['done']}/{ph_st['total']}) — {s}{target_note}")
```

- [ ] **Step 4: Verify the file parses**

Run: `python -c "import ast; ast.parse(open('plugins/taskmaster/backlog_server.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py
git commit -m "refactor(taskmaster): rename milestone to phase in context/dashboard functions"
```

---

### Task 3: Rename query tools in backlog_server.py

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py:523-568` (backlog_list_tasks)
- Modify: `plugins/taskmaster/backlog_server.py:586-596` (backlog_get_task)
- Modify: `plugins/taskmaster/backlog_server.py:766-838` (backlog_next_available)
- Modify: `plugins/taskmaster/backlog_server.py:929-935` (backlog_validate)

- [ ] **Step 1: Rename backlog_list_tasks parameter and filter**

Change parameter `milestone: str = ""` → `phase: str = ""`, update docstring, and rename all internal references:

```python
@mcp.tool()
def backlog_list_tasks(epic: str = "", status: str = "", priority: str = "", phase: str = "") -> str:
    """List tasks with optional filters. All params optional — defaults to showing all tasks.

    Args:
        epic: Filter by epic ID (e.g., "ue-plugin", "desktop-app")
        status: Filter by status: todo, in-progress, in-review, done, blocked
        priority: Filter by priority: P0, P1, P2, P3
        phase: Filter by phase ID
    """
```

At line 546: `if phase and t.get("phase") != phase:`
At lines 563-564: `if phase:` / `filters.append(f"phase={phase}")`

- [ ] **Step 2: Rename backlog_get_task display line**

At line 592: `("Phase", task.get("phase", "—"))`

- [ ] **Step 3: Rename backlog_next_available**

At line 770: `active_ph = _active_phase(data)`
At line 788: `if active_ph and task.get("phase") != active_ph["id"]:`
At line 808: `f"*Filtered to phase: **{active_ph['name']}***\n"`
At line 816: `f"No tasks available in phase **{active_ph['name']}**..."`
At line 833: `not task.get("phase")`
At line 836: `f"\n*{len(unassigned)} todo tasks are not assigned to any phase.*"`

- [ ] **Step 4: Rename backlog_validate**

At lines 929-935:
```python
    # 7. Phase validation
    for task, epic in all_tasks:
        tid = task["id"]
        # 8. Phase references that don't exist
        task_ph = task.get("phase")
        if task_ph and not _find_phase(data, task_ph):
            issues.append(f"`{tid}`: phase `{task_ph}` does not exist")
```

- [ ] **Step 5: Verify the file parses**

Run: `python -c "import ast; ast.parse(open('plugins/taskmaster/backlog_server.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add plugins/taskmaster/backlog_server.py
git commit -m "refactor(taskmaster): rename milestone to phase in query tools"
```

---

### Task 4: Rename mutation tools in backlog_server.py

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py:1010` (backlog_init)
- Modify: `plugins/taskmaster/backlog_server.py:1030-1097` (backlog_add_task)
- Modify: `plugins/taskmaster/backlog_server.py:1544-1622` (backlog_update_task)
- Modify: `plugins/taskmaster/backlog_server.py:2110-2117` (backlog_batch_update)

- [ ] **Step 1: Rename backlog_init schema**

At line 1010: `"phases": [],` (was `"milestones": []`)

- [ ] **Step 2: Rename backlog_add_task parameter and logic**

Parameter: `milestone: str = ""` → `phase: str = ""`
Docstring: `phase: Optional phase ID to assign this task to`
At lines 1094-1097:
```python
    if phase:
        if not _find_phase(data, phase):
            return f"Error: phase `{phase}` not found"
        new_task["phase"] = phase
```

- [ ] **Step 3: Rename backlog_update_task field handling**

At line 1550 docstring: `phase` instead of `milestone`
At line 1558: `- phase: phase ID to assign, or "" to clear`
At lines 1616-1622:
```python
    elif field == "phase":
        if value == "" or value.lower() == "none":
            task.pop("phase", None)
        else:
            if not _find_phase(data, value):
                return f"Error: phase `{value}` not found"
            task["phase"] = value
```

- [ ] **Step 4: Rename backlog_batch_update field handling**

At lines 2110-2117:
```python
            elif field == "phase":
                if value == "" or value.lower() == "none":
                    task.pop("phase", None)
                else:
                    if not _find_phase(data, value):
                        errors.append(f"`{task_id}`: phase `{value}` not found")
                        continue
                    task["phase"] = value
```

- [ ] **Step 5: Verify the file parses**

Run: `python -c "import ast; ast.parse(open('plugins/taskmaster/backlog_server.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add plugins/taskmaster/backlog_server.py
git commit -m "refactor(taskmaster): rename milestone to phase in mutation tools"
```

---

### Task 5: Rename the 4 milestone MCP tools + enhance with sequential numbering and prev/next context

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py:1717-1779` (backlog_add_milestone → backlog_add_phase)
- Modify: `plugins/taskmaster/backlog_server.py:1783-1828` (backlog_update_milestone → backlog_update_phase)
- Modify: `plugins/taskmaster/backlog_server.py:1832-1942` (backlog_milestone_status → backlog_phase_status)
- Modify: `plugins/taskmaster/backlog_server.py:1946-2020` (backlog_advance_milestone → backlog_advance_phase)

- [ ] **Step 1: Rename and enhance backlog_add_phase**

```python
@mcp.tool()
def backlog_add_phase(
    phase_id: str, name: str, description: str = "", order: int | None = None,
    target_date: str = "", start_date: str = "",
) -> str:
    """Create a new phase. Phases are sequential blocks of work — only one is active at a time.
    Phases are temporal attention scopes for sequential ordering, NOT feature groupings — features belong in epics.
    Tasks are assigned to phases to control focus.

    Args:
        phase_id: Short kebab-case identifier (e.g., "p1", "foundation", "mvp"). Must be unique.
        name: Human-readable name (e.g., "Phase 1: Foundation", "Phase 2: Core Features")
        description: Brief description of THIS phase's goals. Frame it relative to what came before and what comes next.
        order: Position in the sequence (1, 2, 3...). Auto-assigned if omitted.
        target_date: Optional target completion date (YYYY-MM-DD format)
        start_date: Optional start date (YYYY-MM-DD format). Auto-set to today if status is active and omitted.
    """
    # Validate ID format
    if not phase_id or not all(c.isalnum() or c == "-" for c in phase_id) or phase_id != phase_id.lower():
        return f"Error: phase_id must be lowercase kebab-case (e.g., 'p1', 'foundation'), got `{phase_id}`"

    data = _load()

    if _find_phase(data, phase_id):
        return f"Error: phase `{phase_id}` already exists"

    if "phases" not in data:
        data["phases"] = []

    # Auto-assign order (sequential)
    if order is None:
        existing_orders = [ph.get("order", 0) for ph in data["phases"]]
        order = max(existing_orders, default=0) + 1

    # Validate dates if provided
    if target_date and not _validate_date(target_date):
        return f"Error: target_date must be YYYY-MM-DD format, got `{target_date}`"
    if start_date and not _validate_date(start_date):
        return f"Error: start_date must be YYYY-MM-DD format, got `{start_date}`"

    # Auto-activate if this is the first phase
    status = "planned"
    if not any(ph.get("status") == "active" for ph in data["phases"]):
        status = "active"

    new_phase = {
        "id": phase_id,
        "name": name,
        "status": status,
        "description": description,
        "order": order,
        "created": _now(),
    }
    if target_date:
        new_phase["target_date"] = target_date
    if start_date:
        new_phase["start_date"] = start_date
    elif status == "active":
        new_phase["start_date"] = _today()

    data["phases"].append(new_phase)
    _mutate_and_save(data)

    status_note = f" (auto-activated — first phase)" if status == "active" else ""
    return f"Created phase `{phase_id}` — {name} (order: {order}){status_note}"
```

- [ ] **Step 2: Rename backlog_update_phase**

```python
@mcp.tool()
def backlog_update_phase(phase_id: str, field: str, value: str) -> str:
    """Update a single field on a phase.

    Args:
        phase_id: The phase ID (e.g., "p1", "foundation")
        field: Field to update — one of: name, status, description, order, target_date, start_date
        value: New value. For status: planned, active, done, archived. For order: integer. For dates: YYYY-MM-DD or empty to clear.
    """
    if field not in ALLOWED_PHASE_FIELDS:
        return f"Error: field `{field}` not allowed. Allowed: {', '.join(sorted(ALLOWED_PHASE_FIELDS))}"

    data = _load()
    ph = _find_phase(data, phase_id)
    if not ph:
        return f"Error: phase `{phase_id}` not found"

    if field == "status":
        if value not in VALID_PHASE_STATUSES:
            return f"Error: invalid status `{value}`. Valid: {', '.join(sorted(VALID_PHASE_STATUSES))}"
        # If activating, deactivate any currently active phase
        if value == "active":
            for other_ph in data.get("phases", []):
                if other_ph["id"] != phase_id and other_ph.get("status") == "active":
                    other_ph["status"] = "planned"
            if not ph.get("start_date"):
                ph["start_date"] = _today()
        if value == "done":
            ph["completed"] = _now()
        ph["status"] = value
    elif field == "order":
        try:
            ph["order"] = int(value)
        except ValueError:
            return f"Error: order must be an integer, got `{value}`"
    elif field in ("target_date", "start_date"):
        if value == "":
            ph.pop(field, None)
        else:
            if not _validate_date(value):
                return f"Error: {field} must be YYYY-MM-DD format, got `{value}`"
            ph[field] = value
    else:
        ph[field] = value

    _mutate_and_save(data)
    return f"Updated phase `{phase_id}` field `{field}` → {value}"
```

- [ ] **Step 3: Rename and enhance backlog_phase_status with prev/next context**

```python
@mcp.tool()
def backlog_phase_status(phase_id: str = "") -> str:
    """Show detailed progress for a phase. Defaults to the active phase.
    Phases are sequential — this shows where you are in the sequence with context about previous and next phases.

    Args:
        phase_id: Phase ID. If omitted, shows the active phase.
    """
    data = _load()

    if phase_id:
        ph = _find_phase(data, phase_id)
        if not ph:
            return f"Error: phase `{phase_id}` not found"
    else:
        ph = _active_phase(data)
        if not ph:
            return "No active phase. Create one with `backlog_add_phase`."

    stats = _phase_stats(data, ph["id"])

    # Get all phases sorted by order for sequential context
    all_phases = sorted(data.get("phases", []), key=lambda p: p.get("order", 999))
    current_idx = next((i for i, p in enumerate(all_phases) if p["id"] == ph["id"]), -1)
    prev_phase = all_phases[current_idx - 1] if current_idx > 0 else None
    next_phase = all_phases[current_idx + 1] if current_idx < len(all_phases) - 1 else None

    # Phase sequence header
    phase_num = current_idx + 1
    total_phases = len(all_phases)
    lines = [f"## Phase {phase_num}/{total_phases}: {ph['name']}\n"]

    if ph.get("description"):
        lines.append(f"{ph['description']}\n")

    # Previous/next phase context
    if prev_phase:
        prev_status = "completed" if prev_phase.get("status") == "done" else prev_phase.get("status", "planned")
        lines.append(f"**Previous:** {prev_phase['name']} ({prev_status})")
    if next_phase:
        lines.append(f"**Next up:** {next_phase['name']} — {next_phase.get('description', 'no description')}")
    if prev_phase or next_phase:
        lines.append("")
```

Then continue with the rest of the existing status display logic (retrospective for done, active progress bar, task listing, unassigned hint) — but with all `milestone` references renamed to `phase`, `ms` → `ph`, `_milestone_stats` → `_phase_stats`, `_find_milestone` → `_find_phase`, `t.get("milestone")` → `t.get("phase")`, and string literals updated ("milestone" → "phase").

The unassigned hint at the end becomes:
```python
    if unassigned_count:
        lines.append(f"*{unassigned_count} active tasks are not assigned to any phase.*")
```

- [ ] **Step 4: Rename and enhance backlog_advance_phase with next-phase context**

```python
@mcp.tool()
def backlog_advance_phase() -> str:
    """Complete the active phase and activate the next one in sequence.
    Archives all 'done' tasks in the completed phase. Activates the next 'planned' phase by order.
    """
    data = _load()
    active_ph = _active_phase(data)
    if not active_ph:
        return "No active phase to advance."

    ph_stats = _phase_stats(data, active_ph["id"])

    # Warn if there are incomplete tasks
    incomplete = ph_stats["todo"] + ph_stats["in-progress"] + ph_stats["in-review"] + ph_stats["blocked"]
    warning = ""
    if incomplete > 0:
        warning = (
            f"\n\n**Warning:** {incomplete} tasks in this phase are not done "
            f"(todo: {ph_stats['todo']}, in-progress: {ph_stats['in-progress']}, "
            f"in-review: {ph_stats['in-review']}, blocked: {ph_stats['blocked']}). "
            f"They will remain in their current status but the phase will be marked done."
        )

    # Mark active phase as done
    active_ph["status"] = "done"
    active_ph["completed"] = _now()

    # Archive done tasks in this phase
    archived_count = 0
    for epic in data["epics"]:
        for t in epic.get("tasks", []):
            if t.get("phase") == active_ph["id"] and t.get("status") == "done":
                t["status"] = "archived"
                t["archive_reason"] = "done"
                t["archived"] = _now()
                archived_count += 1

    # Find and activate next planned phase by order
    planned = [ph for ph in data.get("phases", []) if ph.get("status") == "planned"]
    planned.sort(key=lambda p: p.get("order", 999))
    next_ph = planned[0] if planned else None

    if next_ph:
        next_ph["status"] = "active"
        if not next_ph.get("start_date"):
            next_ph["start_date"] = _today()

    _mutate_and_save(data)

    result = f"Completed phase **{active_ph['name']}** — archived {archived_count} done tasks."
    if active_ph.get("start_date"):
        try:
            start = datetime.strptime(str(active_ph["start_date"]), "%Y-%m-%d").date()
            duration = (date.today() - start).days
            result += f" Duration: {duration}d."
        except ValueError:
            pass
    if active_ph.get("target_date"):
        try:
            target = datetime.strptime(str(active_ph["target_date"]), "%Y-%m-%d").date()
            delta = (date.today() - target).days
            if delta <= 0:
                result += " Completed on time."
            else:
                result += f" Completed {delta}d past target."
        except ValueError:
            pass
    if next_ph:
        next_stats = _phase_stats(data, next_ph["id"])
        result += f"\n\nActivated next phase: **{next_ph['name']}** ({next_stats['total']} tasks, order: {next_ph.get('order', '?')})"
        if next_ph.get("description"):
            result += f"\n{next_ph['description']}"
    else:
        result += "\n\nNo more planned phases. Create one with `backlog_add_phase`."

    return result + warning
```

- [ ] **Step 5: Verify the file parses**

Run: `python -c "import ast; ast.parse(open('plugins/taskmaster/backlog_server.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add plugins/taskmaster/backlog_server.py
git commit -m "refactor(taskmaster): rename milestone MCP tools to phase, add sequential context"
```

---

### Task 6: Rename all milestone references in backlog-viewer.html (CSS + HTML)

**Files:**
- Modify: `plugins/taskmaster/backlog-viewer.html:629-720` (CSS classes)
- Modify: `plugins/taskmaster/backlog-viewer.html:1658-1706` (HTML elements)

- [ ] **Step 1: Rename CSS classes**

Find-replace in the CSS block (lines 629-720):
- `.milestone-banner` → `.phase-banner`
- `.milestone-steps` → `.phase-steps`
- All `.ms-label`, `.ms-name`, `.ms-progress-bar`, `.ms-progress-fill`, `.ms-stats` stay as-is (they're short aliases, not user-facing)
- `.ms-step`, `.ms-active`, `.ms-done`, `.ms-selected` stay as-is (internal CSS)

Actually, the `ms-` prefix originally stood for "milestone" but it's short enough to be a reasonable abbreviation for any concept. Rename only the `.milestone-*` classes since those are the semantically named ones:

```css
/* ── Phase banner ──────────────────────────────────── */
.phase-banner {
```
```css
.phase-steps {
```

- [ ] **Step 2: Rename HTML element IDs and labels**

At lines 1658-1662:
```html
<div class="filter-group" id="phase-filter-group" style="display:none;">
    <span class="filter-label">Phase</span>
    <select class="filter-select" id="phase-filter">
      <option value="all">All phases</option>
    </select>
  </div>
```

At lines 1705-1706:
```html
<div class="epics-section" id="phase-section" style="display:none;">
  <div id="phase-banner"></div>
</div>
```

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/backlog-viewer.html
git commit -m "refactor(taskmaster): rename milestone to phase in viewer CSS and HTML"
```

---

### Task 7: Rename and redesign JavaScript in backlog-viewer.html — phase visuals

This is the most significant visual change. The steps indicator currently shows phases as equal-weight pills with arrows between them. The new design should:
1. Show phase **numbers** (1, 2, 3...) prominently
2. Emphasize the **current phase** with a larger, highlighted treatment
3. Show **done phases** as compact, faded
4. Show **future phases** as compact, dim
5. Use a **connecting line** between phases to emphasize sequential flow
6. Show the banner label as "Phase N/Total" instead of just "Milestone"

**Files:**
- Modify: `plugins/taskmaster/backlog-viewer.html:629-720` (CSS — add new phase-step styles)
- Modify: `plugins/taskmaster/backlog-viewer.html:1769` (JS variable)
- Modify: `plugins/taskmaster/backlog-viewer.html:1927-1958` (populate logic)
- Modify: `plugins/taskmaster/backlog-viewer.html:2013-2225` (renderMilestones → renderPhases)
- Modify: `plugins/taskmaster/backlog-viewer.html:2228-2234` (isViewingDoneMilestone → isViewingDonePhase)
- Modify: `plugins/taskmaster/backlog-viewer.html:2272-2275` (render filter)
- Modify: `plugins/taskmaster/backlog-viewer.html:2374-2375` (kanban filter)
- Modify: `plugins/taskmaster/backlog-viewer.html:2431-2433` (stats filter)
- Modify: `plugins/taskmaster/backlog-viewer.html:2917-2923` (event listener)

- [ ] **Step 1: Add new CSS for the redesigned phase steps indicator**

Add/replace CSS for the phase steps to create a numbered, connected, current-phase-emphasized layout:

```css
/* ── Phase steps (sequential indicator) ────────────── */
.phase-steps {
  display: flex;
  align-items: center;
  gap: 0;
  flex-wrap: wrap;
  margin-top: 6px;
}

.phase-steps .ph-connector {
  width: 24px;
  height: 2px;
  background: var(--border);
  flex-shrink: 0;
}

.phase-steps .ph-connector.ph-done-connector {
  background: var(--stat-done-color);
  opacity: 0.5;
}

.ms-step {
  font-size: var(--fs-xs);
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
  border: 1px solid var(--border);
  background: var(--surface2);
  color: var(--text-dim);
  cursor: pointer;
  transition: all 0.15s;
  position: relative;
}

.ms-step .ph-num {
  display: inline-block;
  width: 16px;
  height: 16px;
  line-height: 16px;
  text-align: center;
  border-radius: 50%;
  font-size: 10px;
  font-weight: 700;
  margin-right: 4px;
  background: var(--surface2);
  border: 1px solid var(--border);
  color: var(--text-dim);
}

/* Active phase — large, prominent */
.ms-step.ms-active {
  border-color: var(--accent);
  background: var(--p2-bg);
  color: var(--accent);
  font-size: var(--fs-sm);
  padding: 4px 12px;
  box-shadow: 0 0 0 1px var(--accent), 0 2px 8px rgba(0,0,0,0.15);
}

.ms-step.ms-active .ph-num {
  background: var(--accent);
  border-color: var(--accent);
  color: var(--surface);
}

/* Done phase — compact, faded */
.ms-step.ms-done {
  border-color: var(--stat-done-border);
  background: var(--stat-done-bg);
  color: var(--stat-done-color);
  opacity: 0.6;
}

.ms-step.ms-done:hover {
  opacity: 1;
}

.ms-step.ms-done .ph-num {
  background: var(--stat-done-color);
  border-color: var(--stat-done-color);
  color: var(--surface);
}

/* Selected (clicked) phase */
.ms-step.ms-selected {
  box-shadow: 0 0 0 2px var(--accent);
  opacity: 1;
}
```

- [ ] **Step 2: Rename JS variable and populate logic**

At line 1769: `let activePhase = 'all';`

At lines 1927-1958 (the populate logic in the data-load handler):
```javascript
  // Phase dropdown — populate and auto-select active phase
  const phSel = document.getElementById('phase-filter');
  const phGroup = document.getElementById('phase-filter-group');
  const phases = (data.phases || []).filter(m => m.status !== 'archived');
  const prevPh = activePhase;
  while (phSel.options.length > 1) phSel.remove(1);
  if (phases.length) {
    phGroup.style.display = '';
    for (const ph of phases) {
      const opt = document.createElement('option');
      opt.value = ph.id;
      opt.textContent = ph.name || ph.id;
      phSel.appendChild(opt);
    }
    if (prevPh !== 'all' && phases.some(p => p.id === prevPh)) {
      activePhase = prevPh;
      phSel.value = prevPh;
    } else {
      const activePh = phases.find(p => p.status === 'active');
      if (activePh) {
        activePhase = activePh.id;
        phSel.value = activePh.id;
      } else {
        activePhase = 'all';
        phSel.value = 'all';
      }
    }
  } else {
    phGroup.style.display = 'none';
    activePhase = 'all';
  }

  renderPhases();
```

- [ ] **Step 3: Rewrite renderPhases function with numbered, emphasized design**

Replace `renderMilestones()` with `renderPhases()`. Key changes:
- Banner label shows "Phase N/Total" instead of "Milestone"
- Steps indicator uses numbered circles with connecting lines
- Active phase is visually larger/brighter
- Done phases are compact
- Completed phase banner says "Completed Phase" instead of "Completed Milestone"

```javascript
function renderPhases() {
  const section = document.getElementById('phase-section');
  const banner = document.getElementById('phase-banner');
  const phases = (loadedData && loadedData.phases) || [];
  banner.innerHTML = '';

  if (!phases.length) { section.style.display = 'none'; return; }
  section.style.display = '';

  const sorted = [...phases].sort((a, b) => (a.order || 999) - (b.order || 999));
  const active = sorted.find(m => m.status === 'active');
  const donePhases = sorted.filter(m => m.status === 'done');

  const displayed = (activePhase !== 'all')
    ? sorted.find(m => m.id === activePhase)
    : active;

  if (displayed) {
    // Find position in sequence
    const phaseIdx = sorted.findIndex(m => m.id === displayed.id);
    const phaseNum = phaseIdx + 1;
    const totalPhases = sorted.length;

    if (displayed.status === 'done') {
      // Completed phase banner
      let completedCount = 0;
      for (const t of allTasks) {
        if (t.phase === displayed.id) {
          const s = colKey(t.status);
          if (s === 'done' || s === 'archived') completedCount++;
        }
      }
      let durationHtml = '';
      if (displayed.start_date && displayed.completed) {
        const start = parseDateStr(displayed.start_date);
        const end = parseDateStr(displayed.completed);
        if (start && end) {
          const days = daysBetween(end, start);
          durationHtml = `<span class="ms-stats">${days}d duration</span>`;
        }
      }
      let ontimeHtml = '';
      if (displayed.target_date && displayed.completed) {
        const target = parseDateStr(displayed.target_date);
        const end = parseDateStr(displayed.completed);
        if (target && end) {
          const diff = daysBetween(end, target);
          if (diff <= 0) {
            const early = Math.abs(diff);
            ontimeHtml = `<span class="ms-history-stat ms-ontime">${early > 0 ? `${early}d early` : 'on time'}</span>`;
          } else {
            ontimeHtml = `<span class="ms-history-stat ms-late">${diff}d late</span>`;
          }
        }
      }
      const completedDateHtml = displayed.completed
        ? `<span class="ms-date-info">Completed: ${esc(fmtDate(displayed.completed))}</span>`
        : '';
      const descHtml = displayed.description
        ? `<div style="font-size:var(--fs-sm);color:var(--text-muted);margin-top:4px">${esc(displayed.description)}</div>`
        : '';

      banner.innerHTML += `
        <div class="phase-banner">
          <span class="ms-label" style="color:var(--stat-done-color)">Completed Phase ${phaseNum}/${totalPhases}</span>
          <span class="ms-name">${esc(displayed.name)}</span>
          <div class="ms-progress-bar"><div class="ms-progress-fill" style="width:100%;background:var(--stat-done-color)"></div></div>
          <span class="ms-stats">${completedCount} tasks completed</span>
          ${durationHtml}
          ${completedDateHtml}
          ${ontimeHtml}
          ${descHtml}
        </div>
      `;
    } else {
      // Active/planned phase banner
      let total = 0, done = 0;
      for (const t of allTasks) {
        if (t.phase === displayed.id) {
          const s = colKey(t.status);
          if (s === 'archived') continue;
          total++;
          if (s === 'done') done++;
        }
      }
      const pct = total > 0 ? Math.round((done / total) * 100) : 0;
      const dateInfoHtml = msDateInfoHtml(displayed);

      banner.innerHTML += `
        <div class="phase-banner">
          <span class="ms-label">Phase ${phaseNum}/${totalPhases}</span>
          <span class="ms-name">${esc(displayed.name)}</span>
          <div class="ms-progress-bar"><div class="ms-progress-fill" style="width:${pct}%"></div></div>
          <span class="ms-stats">${done}/${total} done (${pct}%)</span>
          ${dateInfoHtml}
        </div>
      `;
    }
  }

  // Steps indicator — numbered, connected, current-phase emphasized
  if (sorted.length > 1) {
    const visibleSteps = sorted.filter(m => m.status !== 'archived');
    let stepsHtml = '<div class="phase-steps">';
    for (let i = 0; i < visibleSteps.length; i++) {
      const ph = visibleSteps[i];
      const phNum = i + 1;
      const statusCls = ph.status === 'active' ? 'ms-active' : ph.status === 'done' ? 'ms-done' : '';
      const selectedCls = activePhase === ph.id ? ' ms-selected' : '';
      const icon = ph.status === 'done' ? '✓' : phNum;
      const connectorCls = ph.status === 'done' ? ' ph-done-connector' : '';
      stepsHtml += `<span class="ms-step ${statusCls}${selectedCls}" data-ms-id="${esc(ph.id)}"><span class="ph-num">${icon}</span>${esc(ph.name)}</span>`;
      if (i < visibleSteps.length - 1) stepsHtml += `<span class="ph-connector${connectorCls}"></span>`;
    }
    stepsHtml += '</div>';
    banner.innerHTML += stepsHtml;
```

Then continue with the history section and click handlers, renaming all `activeMilestone` → `activePhase`, `milestone-filter` → `phase-filter`, `renderMilestones` → `renderPhases`, and `t.milestone` → `t.phase`.

- [ ] **Step 4: Rename isViewingDonePhase helper**

```javascript
function isViewingDonePhase() {
  if (activePhase === 'all') return false;
  const phases = (loadedData && loadedData.phases) || [];
  const ph = phases.find(p => p.id === activePhase);
  return ph && ph.status === 'done';
}
```

- [ ] **Step 5: Rename all filter references in render(), renderEpics(), and stats**

At line 2272-2275 (render):
```javascript
  if (activePhase !== 'all') {
    tasks = tasks.filter(t => t.phase === activePhase);
  }
  if (isViewingDonePhase()) {
```

At line 2267 (renderEpics): `const viewingDone = isViewingDonePhase();`
At line 2271-2273 (renderEpics):
```javascript
    if (activePhase !== 'all') {
      tasks = tasks.filter(t => t.phase === activePhase);
```

At line 2431-2433 (stats):
```javascript
  if (activePhase !== 'all') statsSource = statsSource.filter(t => t.phase === activePhase);
```

At line 2917-2923 (event listener):
```javascript
document.getElementById('phase-filter').addEventListener('change', function() {
  activePhase = this.value;
  renderPhases();
  renderEpics();
  render();
});
```

- [ ] **Step 6: Commit**

```bash
git add plugins/taskmaster/backlog-viewer.html
git commit -m "refactor(taskmaster): rename milestone to phase in viewer JS, redesign phase visuals"
```

---

### Task 8: Rename milestone references in skill files

**Files:**
- Modify: `plugins/taskmaster/skills/taskmaster/SKILL.md:28-30`
- Modify: `plugins/taskmaster/skills/start-session/SKILL.md:25-27`
- Modify: `plugins/taskmaster/skills/pick-task/SKILL.md:17-18`
- Modify: `plugins/taskmaster/skills/init-taskmaster/SKILL.md:10,56,106,119,122-123`
- Modify: `plugins/taskmaster/skills/check-todos/SKILL.md:123,129`

- [ ] **Step 1: Update taskmaster/SKILL.md routing table**

Lines 28-30:
```markdown
| "Create a phase", "plan the next phase", "set up phases" | Direct tool call — use `backlog_add_phase` |
| "Show phase progress", "where are we in the phase?" | Direct tool call — use `backlog_phase_status` |
| "Advance to next phase", "this phase is done" | Direct tool call — use `backlog_advance_phase` |
```

- [ ] **Step 2: Update start-session/SKILL.md**

Line 25: `- **Phase progress** — if an active phase exists, show it prominently: "**Phase: {name}** — {done}/{total} tasks done". This gives the user a sense of where they are in the project's arc.`
Line 27: `filtered to the active phase`

- [ ] **Step 3: Update pick-task/SKILL.md**

Line 17: `When a phase is active, this only returns tasks from that phase`
Line 18: `If no available tasks: the phase may be complete (suggest \`/advance-phase\`), or suggest adding work.`

- [ ] **Step 4: Update init-taskmaster/SKILL.md**

Line 10: `backlog_add_phase` (in the critical warning)
Line 56: `Suggest creating a phase to organize the first batch of work.`
Line 94: `**Proposed Phase:** "Cleanup & Foundation"`
Line 106: `"Add the proposed epics, tasks, and phase to the backlog"`
Lines 119-123:
```
- `backlog_add_phase` for the initial phase
- Assign tasks to the phase
```

- [ ] **Step 5: Update check-todos/SKILL.md**

Line 123: `If a phase is active, ask if new tasks should be assigned to it`
Line 129: `Run at the start of a new phase to catch untracked work`

- [ ] **Step 6: Commit**

```bash
git add plugins/taskmaster/skills/
git commit -m "refactor(taskmaster): rename milestone to phase in all skill files"
```

---

### Task 9: Rename milestone references in docs and hooks

**Files:**
- Modify: `plugins/taskmaster/references/task-lifecycle.md:53-64`
- Modify: `plugins/taskmaster/docs/TASKMASTER.md` (all ~25 occurrences)
- Modify: `plugins/taskmaster/hooks/session-start.sh:44`

- [ ] **Step 1: Update task-lifecycle.md**

Lines 53-64 — rename all milestone references to phase:
```markdown
| **One active at a time** | Only one phase can be `active`. `backlog_next_available` only shows tasks from the active phase. |
| **Tasks belong to phases** | Each task has an optional `phase` field. Tasks without a phase are "unassigned" and shown separately. |
| **Advancing** | When a phase's work is complete, `backlog_advance_phase` marks it done, archives its done tasks, and activates the next planned phase by order. |
| **Cross-cutting** | A phase can contain tasks from multiple epics. Epics are thematic (auth, api, ux); phases are temporal (foundation, core features, polish). |

### Phase + Task Workflow

1. Create phases in order: `backlog_add_phase("p1", "Phase 1: Foundation", order=1)`
2. Assign tasks: `backlog_update_task("auth-001", "phase", "p1")`
3. Work through the active phase's tasks
4. When done: `backlog_advance_phase` — archives done tasks, activates next
5. Repeat until all phases complete
```

- [ ] **Step 2: Update docs/TASKMASTER.md**

Replace all ~25 occurrences of "milestone" with "phase" throughout the file:
- "milestone-based sprint planning" → "phase-based sequential planning"
- "one milestone" → "one phase"
- `backlog_add_milestone` → `backlog_add_phase`
- `backlog_update_milestone` → `backlog_update_phase`
- `backlog_milestone_status` → `backlog_phase_status`
- `backlog_advance_milestone` → `backlog_advance_phase`
- `active_milestone` → `active_phase`
- `milestone: "m1"` → `phase: "m1"`
- `milestones:` → `phases:`
- All prose references

- [ ] **Step 3: Update hooks/session-start.sh**

Line 44:
```bash
Phase tools: backlog_add_phase, backlog_phase_status, backlog_advance_phase.
```

- [ ] **Step 4: Commit**

```bash
git add plugins/taskmaster/references/ plugins/taskmaster/docs/ plugins/taskmaster/hooks/
git commit -m "refactor(taskmaster): rename milestone to phase in docs, references, and hooks"
```

---

### Task 10: Verify no remaining "milestone" references and test

- [ ] **Step 1: Search for any remaining "milestone" references in the plugin**

Run: `grep -ri "milestone" plugins/taskmaster/ --include="*.py" --include="*.html" --include="*.md" --include="*.sh" | grep -v "_archive" | grep -v "design-v2.md" | grep -v "node_modules"`

Expected: Zero results (the design doc is excluded since it's the source spec).

- [ ] **Step 2: Verify Python server starts without errors**

Run: `cd plugins/taskmaster && python -c "import backlog_server; print('Server module loads OK')"`
Expected: `Server module loads OK`

- [ ] **Step 3: Verify no syntax errors in viewer**

Open `plugins/taskmaster/backlog-viewer.html` in a browser and confirm:
- Phase filter dropdown renders
- Phase banner renders with "Phase N/Total" label
- Phase steps show numbered circles with connecting lines
- Active phase step is visually larger/brighter
- Done phase steps are compact/faded
- Clicking phase steps toggles filtering

- [ ] **Step 4: Final commit if any fixups needed**

```bash
git add -A plugins/taskmaster/
git commit -m "refactor(taskmaster): final cleanup for milestone-to-phase rename"
```
