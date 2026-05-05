# Archive Epic Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow archiving entire epics (with cascade to all their tasks), hiding them from the board and default listings.

**Architecture:** New `backlog_archive_epic` MCP tool mirrors existing `backlog_archive_task`. Viewer gets an "Archived Epics" collapsible section mirroring the existing archived tasks section. Server listings skip archived epics by default.

**Tech Stack:** Python (MCP server), HTML/CSS/JS (single-file viewer)

**Spec:** `docs/superpowers/specs/2026-03-31-archive-epic-design.md`

---

### Task 1: Add `backlog_archive_epic` MCP tool

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py:1758` (VALID_EPIC_STATUSES constant)
- Modify: `plugins/taskmaster/backlog_server.py:1787` (insert new tool after `backlog_update_epic`)

- [ ] **Step 1: Add "archived" to VALID_EPIC_STATUSES**

At line 1758, change:
```python
VALID_EPIC_STATUSES = {"active", "planned", "done"}
```
to:
```python
VALID_EPIC_STATUSES = {"active", "planned", "done", "archived"}
```

- [ ] **Step 2: Add the `backlog_archive_epic` tool**

Insert after the `backlog_update_epic` function (after line 1786), before the next `@mcp.tool()`:

```python
@mcp.tool()
def backlog_archive_epic(epic_id: str, reason: str = "done") -> str:
    """Archive an epic and all its tasks — hides the epic from the board and default listings.
    Cascades: every non-archived task in the epic is also archived with the same reason.

    Args:
        epic_id: The epic ID (e.g., "features", "infra")
        reason: Why the epic is being archived. One of: done, deprecated, duplicate, wont-fix, superseded. Default: done.
    """
    if reason not in VALID_ARCHIVE_REASONS:
        return f"Error: invalid reason `{reason}`. Valid: {', '.join(sorted(VALID_ARCHIVE_REASONS))}"

    data = _load()
    epic = _find_epic(data, epic_id)
    if not epic:
        return f"Error: epic `{epic_id}` not found"

    if epic.get("status") == "archived":
        return f"Error: epic `{epic_id}` is already archived"

    now = _now()
    epic["status"] = "archived"
    epic["archive_reason"] = reason
    epic["archived"] = now

    cascaded = 0
    for task in epic.get("tasks", []):
        if task.get("status") != "archived":
            task["status"] = "archived"
            task["archive_reason"] = reason
            task["archived"] = now
            task.pop("locked_by", None)
            cascaded += 1

    _mutate_and_save(data)
    return f"Archived epic `{epic_id}` — {epic.get('name', epic_id)} ({cascaded} tasks cascaded, reason: {reason})"
```

- [ ] **Step 3: Verify the tool loads**

Run: `cd plugins/taskmaster && python -c "import backlog_server; print('OK')"`
Expected: `OK` (no import errors)

- [ ] **Step 4: Commit**

```bash
git add plugins/taskmaster/backlog_server.py
git commit -m "feat(taskmaster): add backlog_archive_epic MCP tool with cascade"
```

---

### Task 2: Update `backlog_status` to skip archived epics

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py:464` (epic loop in `backlog_status`)

- [ ] **Step 1: Add archived epic filter**

At line 464, the epic loop currently reads:

```python
    for epic in data["epics"]:
        tasks = epic.get("tasks", [])
```

Change to:

```python
    for epic in data["epics"]:
        if epic.get("status") == "archived":
            continue
        tasks = epic.get("tasks", [])
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/backlog_server.py
git commit -m "fix(taskmaster): hide archived epics from backlog_status dashboard"
```

---

### Task 3: Update `backlog_list_tasks` to skip archived epics by default

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py:598` (epic loop in `backlog_list_tasks`)

- [ ] **Step 1: Add archived epic filter**

At line 598, the epic loop currently reads:

```python
    for ep in data["epics"]:
        if epic and ep["id"] != epic:
            continue
```

Change to:

```python
    for ep in data["epics"]:
        if epic and ep["id"] != epic:
            continue
        # Hide tasks in archived epics unless explicitly filtering for archived status
        if not status and ep.get("status") == "archived":
            continue
```

This mirrors the existing task-level archived filter at line 604-606: tasks in archived epics are hidden by default, but visible when `status="archived"` is explicitly passed.

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/backlog_server.py
git commit -m "fix(taskmaster): hide archived epic tasks from backlog_list_tasks"
```

---

### Task 4: Add "Archived Epics" collapsible section to viewer

**Files:**
- Modify: `plugins/taskmaster/backlog-viewer.html:1139` (CSS — after archived-grid styles)
- Modify: `plugins/taskmaster/backlog-viewer.html:1747` (HTML — after epics-section)
- Modify: `plugins/taskmaster/backlog-viewer.html:1810` (JS state — add `showArchivedEpics`)
- Modify: `plugins/taskmaster/backlog-viewer.html:2317` (JS — `renderEpics()` function)

- [ ] **Step 1: Add CSS for archived epics section**

After line 1139 (after `.archived-grid .task-title { color: var(--text-dim); }`), add:

```css
    /* Archived epics section */
    .archived-epics-section {
      padding: 0 24px 8px;
      flex-shrink: 0;
    }

    .archived-epics-header {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 6px 0;
      cursor: pointer;
      user-select: none;
    }

    .archived-epics-header:hover .archived-epics-title { color: var(--text); }

    .archived-epics-chevron {
      color: var(--text-dim);
      font-size: var(--fs-card-tag);
      transition: transform 0.2s;
      display: inline-block;
    }

    .archived-epics-chevron.open { transform: rotate(90deg); }

    .archived-epics-title {
      font-size: var(--fs-card-tag);
      font-weight: 700;
      color: var(--text-dim);
      text-transform: uppercase;
      letter-spacing: 0.06em;
      transition: color 0.2s;
    }

    .archived-epics-grid {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-bottom: 4px;
      max-height: 0;
      overflow: hidden;
      transition: max-height 0.3s ease;
    }

    .archived-epics-grid.open {
      max-height: 2000px;
    }

    .archived-epics-grid .epic-card {
      opacity: 0.65;
    }

    .archived-epics-grid .epic-card:hover {
      opacity: 0.85;
    }
```

- [ ] **Step 2: Add HTML for archived epics section**

After line 1747 (`</div>` closing epics-section), before the `<!-- Board -->` comment, add:

```html
<!-- Archived epics section -->
<div class="archived-epics-section" id="archived-epics-section" style="display:none;">
  <div class="archived-epics-header" id="archived-epics-header">
    <span class="archived-epics-chevron" id="archived-epics-chevron">&#9654;</span>
    <span class="archived-epics-title">Archived Epics</span>
    <span class="archived-count" id="archived-epics-count">0</span>
  </div>
  <div class="archived-epics-grid" id="archived-epics-grid"></div>
</div>
```

- [ ] **Step 3: Add state variable and toggle handler**

After line 1810 (`let showArchived = false;`), add:

```javascript
let showArchivedEpics = false;
```

After the existing archive toggle handler block (after line 2554), add:

```javascript
// ── Archived epics toggle handler ───────────────────────
document.getElementById('archived-epics-header').addEventListener('click', () => {
  showArchivedEpics = !showArchivedEpics;
  const grid = document.getElementById('archived-epics-grid');
  const chevron = document.getElementById('archived-epics-chevron');
  grid.classList.toggle('open', showArchivedEpics);
  chevron.classList.toggle('open', showArchivedEpics);
});
```

- [ ] **Step 4: Update `renderEpics()` to filter archived epics and render them separately**

Replace the entire `renderEpics()` function (lines 2317–2390) with:

```javascript
function renderEpics() {
  const section = document.getElementById('epics-section');
  const grid    = document.getElementById('epics-grid');
  grid.innerHTML = '';

  const archivedSection = document.getElementById('archived-epics-section');
  const archivedGrid    = document.getElementById('archived-epics-grid');
  const archivedCountEl = document.getElementById('archived-epics-count');
  archivedGrid.innerHTML = '';

  if (!allEpics.length) {
    section.style.display = 'none';
    archivedSection.style.display = 'none';
    return;
  }

  const viewingDone = isViewingDonePhase();
  let visibleCount = 0;
  const archivedEpics = [];

  for (const epic of allEpics) {
    // Separate archived epics
    if (epic.status === 'archived') {
      archivedEpics.push(epic);
      continue;
    }

    let tasks = (epic.tasks || []);
    // When a phase is selected, only show epics that have tasks in that phase
    if (activePhase !== 'all') {
      tasks = tasks.filter(t => t.phase === activePhase);
      if (!tasks.length) continue; // hide epic entirely
    }
    // When viewing a done phase, treat archived tasks as done (shallow copy, no mutation)
    if (viewingDone) {
      tasks = tasks.map(t => colKey(t.status) === 'archived' ? { ...t, status: 'done' } : t);
    }
    visibleCount++;
    const archived = viewingDone ? 0 : tasks.filter(t => colKey(t.status) === 'archived').length;
    const activeTasks = tasks.filter(t => colKey(t.status) !== 'archived');
    const total = activeTasks.length;
    const done  = activeTasks.filter(t => colKey(t.status) === 'done').length;
    const pct   = total > 0 ? Math.round((done / total) * 100) : 0;

    const card = document.createElement('div');
    card.className = 'epic-card' + (activeEpic === epic.id ? ' active-filter' : '');
    card.dataset.epicId = epic.id;

    const statusClass = {
      active:   'status-active',
      planned:  'status-planned',
      done:     'status-done',
    }[epic.status] || 'status-planned';

    const inProg = activeTasks.filter(t => colKey(t.status) === 'progress').length;
    const inRev  = activeTasks.filter(t => colKey(t.status) === 'review').length;
    const todo   = total - done - inProg - inRev;

    const breakdownParts = [];
    if (done)     breakdownParts.push(`<span style="color:var(--stat-done-color,#3fb950)">${done} done</span>`);
    if (inProg)   breakdownParts.push(`<span style="color:var(--accent)">${inProg} active</span>`);
    if (inRev)    breakdownParts.push(`<span style="color:var(--p1)">${inRev} review</span>`);
    if (todo)     breakdownParts.push(`<span style="color:var(--text-dim)">${todo} todo</span>`);
    if (archived) breakdownParts.push(`<span style="color:var(--stat-archived-color)">${archived} archived</span>`);

    card.innerHTML = `
      <div class="epic-card-header">
        <div class="epic-name">${esc(epic.name || epic.id)}</div>
        <div class="epic-status-pill ${statusClass}">${esc(epic.status || 'planned')}</div>
      </div>
      <div class="epic-progress-bar">
        ${done ? `<div class="epic-progress-fill done${pct===100?' full':''}" style="width:${total?Math.round(done/total*100):0}%"></div>` : ''}
        ${inRev ? `<div class="epic-progress-fill review" style="width:${total?Math.round(inRev/total*100):0}%"></div>` : ''}
        ${inProg ? `<div class="epic-progress-fill inprog" style="width:${total?Math.round(inProg/total*100):0}%"></div>` : ''}
      </div>
      <div class="epic-progress-text">${breakdownParts.join(' · ')} &mdash; ${pct}%</div>
    `;

    card.addEventListener('click', () => {
      activeEpic = (activeEpic === epic.id) ? 'all' : epic.id;
      updateEpicUI();
      populateEpicDropdown();
      render();
    });

    grid.appendChild(card);
  }

  // Hide epics section if phase filter hides all epics
  section.style.display = visibleCount ? '' : 'none';

  // Render archived epics section
  if (!archivedEpics.length) {
    archivedSection.style.display = 'none';
    return;
  }

  archivedSection.style.display = '';
  archivedCountEl.textContent = archivedEpics.length;

  for (const epic of archivedEpics) {
    const tasks = epic.tasks || [];
    const total = tasks.length;

    const card = document.createElement('div');
    card.className = 'epic-card';
    card.dataset.epicId = epic.id;

    card.innerHTML = `
      <div class="epic-card-header">
        <div class="epic-name">${esc(epic.name || epic.id)}</div>
        <div class="epic-status-pill status-archived">archived</div>
      </div>
      <div class="epic-progress-bar">
        <div class="epic-progress-fill done full" style="width:100%"></div>
      </div>
      <div class="epic-progress-text"><span style="color:var(--stat-archived-color)">${total} tasks</span> &mdash; ${esc(epic.archive_reason || 'done')}</div>
    `;

    archivedGrid.appendChild(card);
  }

  // Apply open/closed state
  const chevron = document.getElementById('archived-epics-chevron');
  if (showArchivedEpics) {
    archivedGrid.classList.add('open');
    chevron.classList.add('open');
  } else {
    archivedGrid.classList.remove('open');
    chevron.classList.remove('open');
  }
}
```

- [ ] **Step 5: Add `.status-archived` pill CSS**

Find the existing status pill classes (search for `.status-done` in the epic pill styles) and add after them:

```css
    .epic-status-pill.status-archived {
      background: var(--stat-archived-bg);
      color: var(--stat-archived-color);
      border-color: var(--stat-archived-border);
    }
```

- [ ] **Step 6: Commit**

```bash
git add plugins/taskmaster/backlog-viewer.html
git commit -m "feat(taskmaster): add archived epics collapsible section to viewer"
```

---

### Task 5: Block `backlog_update_epic` from setting status to "archived" directly

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py:1779-1781` (status validation in `backlog_update_epic`)

Since we added "archived" to `VALID_EPIC_STATUSES` (so the YAML schema accepts it), we need to prevent users from bypassing the archive tool by setting `status=archived` directly via `backlog_update_epic`. Archiving should only happen through `backlog_archive_epic` to ensure cascade behavior.

- [ ] **Step 1: Add guard in `backlog_update_epic`**

At lines 1779-1781, change:

```python
    if field == "status":
        if value not in VALID_EPIC_STATUSES:
            return f"Error: invalid epic status `{value}`. Valid: {', '.join(sorted(VALID_EPIC_STATUSES))}"
```

to:

```python
    if field == "status":
        if value == "archived":
            return "Error: use `backlog_archive_epic` to archive an epic (it cascades to tasks)"
        if value not in VALID_EPIC_STATUSES:
            return f"Error: invalid epic status `{value}`. Valid: {', '.join(sorted(VALID_EPIC_STATUSES))}"
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/backlog_server.py
git commit -m "fix(taskmaster): block direct archived status via backlog_update_epic"
```

---

### Task 6: Verify end-to-end

- [ ] **Step 1: Start the server and open the viewer**

Run: `cd plugins/taskmaster && python backlog_server.py`
Open `backlog-viewer.html` in a browser.

- [ ] **Step 2: Test the archive epic tool**

Call `backlog_archive_epic` with an epic that has tasks. Verify:
- Epic status changes to "archived" with reason and timestamp
- All non-archived tasks in the epic are also archived
- The response shows the correct cascade count

- [ ] **Step 3: Verify viewer**

Reload the viewer and verify:
- The archived epic no longer appears in the main epics grid
- An "Archived Epics" collapsible section appears below the epics grid
- Clicking the chevron expands/collapses the section
- The archived epic card shows the "archived" pill and reason
- The count badge shows the correct number

- [ ] **Step 4: Verify listings**

Call `backlog_status` — archived epic should not appear in the dashboard table.
Call `backlog_list_tasks` — tasks in the archived epic should be hidden by default.
Call `backlog_list_tasks(status="archived")` — all archived tasks (including cascaded ones) should appear.

- [ ] **Step 5: Final commit (if any fixes needed)**

```bash
git add -A
git commit -m "fix(taskmaster): address archive-epic verification findings"
```
