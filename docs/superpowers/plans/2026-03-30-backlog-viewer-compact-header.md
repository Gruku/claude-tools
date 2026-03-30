# Backlog Viewer Compact Header Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce the backlog viewer header from 7 rows to 3 rows, add settings dropdown, and enrich task cards with a proper header zone showing status/time/branch.

**Architecture:** Single-file change to `plugins/taskmaster/backlog-viewer.html`. All CSS, HTML, and JS changes happen in this one file. Tasks are organized by logical area: header restructure, settings dropdown, card enrichment, and cleanup.

**Tech Stack:** Vanilla HTML/CSS/JS (no build step, no framework)

---

### Task 1: Add Settings Dropdown CSS & Card Header CSS

Add all new CSS styles needed for the settings dropdown and the enriched card header. Do this first so subsequent HTML/JS changes render correctly.

**Files:**
- Modify: `plugins/taskmaster/backlog-viewer.html:1281-1299` (after theme-toggle styles)
- Modify: `plugins/taskmaster/backlog-viewer.html:1050-1177` (task card styles)

- [ ] **Step 1: Add settings dropdown CSS**

After the `.theme-toggle:hover` / `.theme-toggle.active` rules (line ~1299), add:

```css
    /* ── Settings dropdown ─────────────────────────────────── */
    .settings-wrapper {
      position: relative;
      flex-shrink: 0;
    }

    .settings-btn {
      width: 32px;
      height: 32px;
      border-radius: 8px;
      border: 1.5px solid var(--border);
      background: var(--surface2);
      color: var(--text-muted);
      font-size: 16px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: border-color 0.2s, background 0.2s;
      flex-shrink: 0;
    }

    .settings-btn:hover { border-color: var(--accent); background: var(--surface3); }

    .settings-dropdown {
      position: absolute;
      top: calc(100% + 8px);
      right: 0;
      background: var(--surface);
      border: 1.5px solid var(--border);
      border-radius: 10px;
      padding: 8px;
      box-shadow: 0 12px 40px rgba(0,0,0,0.4);
      z-index: 200;
      min-width: 200px;
      display: none;
    }

    .settings-dropdown.open { display: block; }

    .settings-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 8px 10px;
      border-radius: 6px;
      font-size: var(--fs-base);
      color: var(--text);
      cursor: pointer;
      transition: background 0.15s;
      user-select: none;
    }

    .settings-item:hover { background: var(--surface2); }

    .settings-item-label {
      font-weight: 500;
    }

    .settings-item-value {
      font-size: var(--fs-sm);
      color: var(--text-muted);
      font-weight: 600;
    }
```

- [ ] **Step 2: Add enriched card header CSS**

Replace the existing `.task-card` padding and add the card header styles. Find the `.task-card` rule (line ~1051) and update it, then add new card header rules after `.task-card:last-child`:

```css
    .task-card {
      background: var(--surface2);
      border: 1.5px solid var(--border);
      border-radius: 8px;
      margin-bottom: 6px;
      transition: border-color 0.2s, background 0.2s;
      cursor: pointer;
      overflow: hidden;
    }

    .task-card:hover {
      border-color: var(--card-hover-border);
      background: var(--surface3);
    }

    .task-card:last-child { margin-bottom: 0; }

    /* ── Card header zone ─────────────────────────────────── */
    .task-card-header {
      background: var(--surface3);
      padding: 10px 14px 8px;
      border-bottom: 1px solid var(--border-subtle);
    }

    .task-card-header-row1 {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 6px;
      margin-bottom: 4px;
    }

    .task-card-header-row2 {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: var(--fs-sm);
      flex-wrap: wrap;
    }

    .card-status-label {
      font-weight: 700;
      font-size: var(--fs-sm);
      text-transform: capitalize;
    }

    .card-status-label.cs-todo     { color: var(--text-dim); }
    .card-status-label.cs-progress { color: var(--accent); }
    .card-status-label.cs-review   { color: var(--p1); }
    .card-status-label.cs-done     { color: var(--stat-done-color); }
    .card-status-label.cs-blocked  { color: var(--stat-blocked-color); }
    .card-status-label.cs-archived { color: var(--stat-archived-color); }

    .card-time-in-status {
      color: var(--text-dim);
      font-size: var(--fs-xs);
      font-weight: 600;
    }

    .card-branch {
      font-family: "SFMono-Regular", Consolas, monospace;
      font-size: var(--fs-xs);
      color: var(--progress);
      font-weight: 600;
      max-width: 160px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .card-header-sep {
      color: var(--text-dim);
      font-size: var(--fs-xs);
    }

    /* ── Card body (below header) ─────────────────────────── */
    .task-card-body {
      padding: 10px 14px 12px;
    }
```

- [ ] **Step 3: Replace recently-moved left-border with background glow**

Replace the existing `.task-card.recently-moved` rules (lines ~1169-1176):

```css
    /* ── Recently moved cards ──────────────────────────────── */
    .task-card.recently-moved {
      box-shadow: inset 0 0 0 1px var(--accent), 0 0 12px color-mix(in srgb, var(--accent) 15%, transparent);
    }

    .col-done .task-card.recently-moved {
      box-shadow: inset 0 0 0 1px #3fb950, 0 0 12px rgba(63, 185, 80, 0.15);
    }
```

- [ ] **Step 4: Update header CSS for new layout**

Update `.header-search` width (line ~278) from `200px` to `240px` to make it wider:

```css
    .header-search {
      background: var(--surface2);
      border: 1px solid var(--border);
      border-radius: 8px;
      color: var(--text);
      padding: 6px 12px;
      font-size: var(--fs-base);
      outline: none;
      transition: border-color 0.2s, box-shadow 0.2s;
      width: 240px;
    }
```

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog-viewer.html
git commit -m "style(viewer): add CSS for settings dropdown, enriched card header, and updated layout"
```

---

### Task 2: Restructure Header HTML — Row 1

Replace the header HTML to remove stat chips, move search into the controls area, add settings dropdown, and remove the toolbar row.

**Files:**
- Modify: `plugins/taskmaster/backlog-viewer.html:1656-1731` (header + toolbar HTML)

- [ ] **Step 1: Replace header HTML**

Replace the entire `<header>` block (lines 1657-1681) with the new compact header:

```html
<!-- Header — Row 1: branding + controls -->
<header class="header">
  <div class="header-left">
    <div class="project-badge" id="project-badge">
      <div class="header-logo" id="project-icon" title="Click to change icon">
        <span class="logo-emoji" id="logo-emoji"></span>
      </div>
      <div>
        <div class="header-title" id="project-name">Taskmaster</div>
        <div class="header-subtitle" id="project-updated">Task Management</div>
      </div>
    </div>
    <span class="read-only-badge">READ-ONLY · AI Workflow Viewer</span>
  </div>
  <div class="header-right">
    <span class="load-indicator" id="load-status">Trying fetch…</span>
    <input type="text" class="header-search" id="search-input" placeholder="Search tasks…  /" />
    <div class="filter-group">
      <div class="priority-toggles" id="priority-toggles">
        <button class="priority-btn active" data-p="P0">P0</button>
        <button class="priority-btn active" data-p="P1">P1</button>
        <button class="priority-btn active" data-p="P2">P2</button>
        <button class="priority-btn active" data-p="P3">P3</button>
      </div>
    </div>
    <div class="filter-group">
      <select class="filter-select" id="sort-select">
        <option value="priority">Priority</option>
        <option value="created">Created</option>
        <option value="started">Started</option>
        <option value="completed">Completed</option>
        <option value="updated">Last updated</option>
        <option value="alpha">Alphabetical</option>
      </select>
      <button class="sort-dir-btn" id="sort-dir-btn" title="Toggle sort direction">↓</button>
    </div>
    <div class="settings-wrapper" id="settings-wrapper">
      <button class="settings-btn" id="settings-btn" title="Settings">⚙</button>
      <div class="settings-dropdown" id="settings-dropdown">
        <div class="settings-item" id="settings-theme">
          <span class="settings-item-label">Theme</span>
          <span class="settings-item-value" id="settings-theme-value">Dark</span>
        </div>
        <div class="settings-item" id="settings-color">
          <span class="settings-item-label">Project color</span>
          <span class="settings-item-value" id="settings-color-value">On</span>
        </div>
      </div>
    </div>
  </div>
</header>
```

- [ ] **Step 2: Remove the toolbar HTML**

Delete the entire toolbar block (lines 1693-1731):

```html
<!-- Toolbar (filters) -->
<div class="toolbar" id="toolbar">
  ...entire block...
</div>
```

- [ ] **Step 3: Remove Active Session and Now Working On banner HTML**

Delete these two blocks (lines 1733-1744):

```html
<!-- Active Session banner -->
<div class="active-session" id="active-session" style="display:none;">
  ...entire block...
</div>

<!-- Now Working On banner -->
<div class="now-working" id="now-working" style="display:none;">
  ...entire block...
</div>
```

- [ ] **Step 4: Commit**

```bash
git add plugins/taskmaster/backlog-viewer.html
git commit -m "feat(viewer): restructure header to single row with integrated controls"
```

---

### Task 3: Update JavaScript — Settings Dropdown & Remove Deleted Elements

Wire up the settings dropdown, remove references to deleted elements (stat chips, active session, now working on, toolbar dropdowns).

**Files:**
- Modify: `plugins/taskmaster/backlog-viewer.html` (script section)

- [ ] **Step 1: Replace theme toggle JS**

Replace the theme toggle IIFE (lines 3003-3042) with a new version that uses the settings dropdown:

```javascript
// ── Settings dropdown + Theme toggles ─────────────────
(function() {
  let base = localStorage.getItem('backlog-base') || 'dark';
  let colored = localStorage.getItem('backlog-colored') !== 'false';

  function applyTheme() {
    const theme = colored ? (base === 'light' ? 'light-colored' : 'colored') : base;
    document.documentElement.setAttribute('data-theme', theme);
    document.getElementById('settings-theme-value').textContent = base === 'dark' ? 'Dark' : 'Light';
    document.getElementById('settings-color-value').textContent = colored ? 'On' : 'Off';
    localStorage.setItem('backlog-base', base);
    localStorage.setItem('backlog-colored', colored);
  }

  // Migrate legacy 'backlog-theme' setting
  const legacy = localStorage.getItem('backlog-theme');
  if (legacy) {
    if (legacy === 'light') { base = 'light'; colored = false; }
    else if (legacy === 'colored') { base = 'dark'; colored = true; }
    else if (legacy === 'light-colored') { base = 'light'; colored = true; }
    else { base = 'dark'; colored = true; }
    localStorage.removeItem('backlog-theme');
  }

  document.getElementById('settings-theme').addEventListener('click', function() {
    base = base === 'dark' ? 'light' : 'dark';
    applyTheme();
  });

  document.getElementById('settings-color').addEventListener('click', function() {
    colored = !colored;
    applyTheme();
  });

  // Settings dropdown open/close
  const btn = document.getElementById('settings-btn');
  const dropdown = document.getElementById('settings-dropdown');
  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    dropdown.classList.toggle('open');
  });
  document.addEventListener('click', () => dropdown.classList.remove('open'));
  dropdown.addEventListener('click', (e) => e.stopPropagation());
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') dropdown.classList.remove('open');
  });

  applyTheme();
})();
```

- [ ] **Step 2: Remove stat chip updates from render()**

In the `render()` function (around lines 2489-2495), delete these lines:

```javascript
  document.getElementById('stat-total').textContent    = stats.total;
  document.getElementById('stat-done').textContent     = stats.done;
  document.getElementById('stat-progress').textContent = stats.in_progress;
  document.getElementById('stat-todo').textContent     = stats.todo;
  document.getElementById('stat-blocked').textContent  = stats.blocked;
  document.getElementById('stat-blocked-wrapper').style.display = stats.blocked ? '' : 'none';
```

Also remove the `statsSource` computation block (lines 2482-2489) and the `computeStats` call since stats are no longer displayed in the header. Keep the `computeStats` function itself for the archive count logic.

Actually, the archive toggle count still uses `stats.archived`, so keep the stats computation but only use it for the archive count. Simplify to:

```javascript
  // Archive count — only for bottom archive section
  let statsSource = allTasks;
  if (activePhase !== 'all') statsSource = statsSource.filter(t => t.phase === activePhase);
  if (activeEpic !== 'all') statsSource = statsSource.filter(t => t._epicId === activeEpic);
  if (isViewingDonePhase()) {
    statsSource = statsSource.map(t => colKey(t.status) === 'archived' ? { ...t, status: 'done' } : t);
  }
  const stats = computeStats(statsSource);
```

- [ ] **Step 3: Remove renderNowWorking() function and its call**

Delete the `renderNowWorking()` function (lines 2394-2415) and remove the `renderNowWorking()` call from `render()` (line 2420).

- [ ] **Step 4: Remove active session polling**

Delete the `fetchSession()` function (lines 3090-3119) and the `setInterval(fetchSession, 3000)` and `fetchSession()` calls (lines 3124, 3126). Also delete the `_lastSessionId` variable (line 3088).

- [ ] **Step 5: Remove epic-filter and phase-filter dropdown event listeners**

Delete the event listeners for `epic-filter` change and `phase-filter` change (lines 2963-2977). The epic cards and phase pills handle filtering directly — these dropdowns no longer exist in the HTML.

Also in `ingestData()`, remove the code that populates the epic dropdown (lines 1949-1966) and the phase dropdown (lines 1968-2000). Keep the `activeEpic` and `activePhase` state management but remove the select element references. Replace with simpler logic:

```javascript
  // Preserve epic filter across live reloads
  if (activeEpic !== 'all' && !allEpics.some(e => e.id === activeEpic)) {
    activeEpic = 'all';
  }

  // Preserve phase filter — auto-select active phase on first load
  const phases = (data.phases || []).filter(m => m.status !== 'archived');
  if (activePhase !== 'all' && !phases.some(m => m.id === activePhase)) {
    const activePh = phases.find(m => m.status === 'active');
    activePhase = activePh ? activePh.id : 'all';
  } else if (activePhase === 'all' && !_lastYamlText) {
    // First load — auto-select active phase
    const activePh = phases.find(m => m.status === 'active');
    if (activePh) activePhase = activePh.id;
  }
```

- [ ] **Step 6: Update phase step click handler to not reference phSel**

In `renderPhases()`, the click handlers for phase steps and history items reference `document.getElementById('phase-filter')` to sync the dropdown. Remove those references. Replace:

```javascript
      step.addEventListener('click', () => {
        const msId = step.dataset.msId;
        const phSel = document.getElementById('phase-filter');
        if (activePhase === msId) {
          activePhase = 'all';
          phSel.value = 'all';
        } else {
          activePhase = msId;
          phSel.value = msId;
        }
```

With:

```javascript
      step.addEventListener('click', () => {
        const msId = step.dataset.msId;
        if (activePhase === msId) {
          activePhase = 'all';
        } else {
          activePhase = msId;
        }
```

Do the same for the history item click handler.

- [ ] **Step 7: Update epic card click handler to not reference sel**

In `renderEpics()`, the click handler references `document.getElementById('epic-filter')`. Replace:

```javascript
    card.addEventListener('click', () => {
      const sel = document.getElementById('epic-filter');
      if (activeEpic === epic.id) {
        activeEpic = 'all';
        sel.value  = 'all';
      } else {
        activeEpic = epic.id;
        sel.value  = epic.id;
      }
```

With:

```javascript
    card.addEventListener('click', () => {
      if (activeEpic === epic.id) {
        activeEpic = 'all';
      } else {
        activeEpic = epic.id;
      }
```

- [ ] **Step 8: Remove archive-toggle toolbar button handler**

Delete the event listener for `archive-toggle` click (lines 2585-2596). The archive toggle button in the toolbar has been removed. The `archived-header` click handler (lines 2577-2583) remains — it controls the bottom-of-page toggle.

Also remove the `archive-toggle` show/hide from `render()`:

```javascript
  const archiveToggle = document.getElementById('archive-toggle');
  const archiveCount = stats.archived;
  document.getElementById('archive-toggle-count').textContent = archiveCount;
  archiveToggle.style.display = archiveCount ? '' : 'none';
```

Replace with just keeping the archived section visibility logic in `renderArchived()` which already handles this.

- [ ] **Step 9: Commit**

```bash
git add plugins/taskmaster/backlog-viewer.html
git commit -m "feat(viewer): wire settings dropdown, remove stat chips and session polling"
```

---

### Task 4: Update makeCard() — Enriched Card Header

Replace the `makeCard()` function to produce the new card structure with a header zone.

**Files:**
- Modify: `plugins/taskmaster/backlog-viewer.html:2853-2906` (makeCard function)

- [ ] **Step 1: Add time-in-status helper function**

Add this before `makeCard()`:

```javascript
// ── Time in status helper ──────────────────────────────
function timeInStatus(task) {
  const now = new Date();
  const statusKey = colKey(task.status);
  let since = null;
  if (statusKey === 'done') since = task.completed;
  else if (statusKey === 'progress' || statusKey === 'review') since = task.started;
  else since = task.created;
  if (!since) return '';
  try {
    const d = new Date(since);
    const days = Math.floor((now - d) / 86400000);
    if (days < 1) return '<1d';
    if (days < 30) return days + 'd';
    if (days < 365) return Math.floor(days / 30) + 'mo';
    return Math.floor(days / 365) + 'y';
  } catch(e) { return ''; }
}

function statusDisplayLabel(task) {
  const st = (task.status || 'todo').toLowerCase();
  const map = {
    'todo': 'Todo', 'to-do': 'Todo',
    'in-progress': 'In Progress', 'in progress': 'In Progress',
    'in-review': 'In Review', 'in review': 'In Review',
    'done': 'Done', 'completed': 'Done', 'closed': 'Done',
    'blocked': 'Blocked',
    'archived': 'Archived',
  };
  return map[st] || st;
}
```

- [ ] **Step 2: Replace makeCard() function**

Replace the entire `makeCard()` function with:

```javascript
function makeCard(task) {
  const card = document.createElement('div');
  card.className = 'task-card';
  card.addEventListener('click', () => openTaskModal(task.id));

  // Highlight recently moved cards (started or completed within last 2 days)
  const now = new Date();
  const twoDaysAgo = new Date(now);
  twoDaysAgo.setDate(twoDaysAgo.getDate() - 2);
  const movedDate = task.completed || task.started;
  if (movedDate) {
    try {
      const d = new Date(movedDate);
      if (d >= twoDaysAgo) card.classList.add('recently-moved');
    } catch(e) {}
  }

  const p = (task.priority || '').toUpperCase();
  const pClass = { P0:'p0-badge', P1:'p1-badge', P2:'p2-badge', P3:'p3-badge' }[p] || 'p3-badge';

  // Card header — status info
  const statusKey = colKey(task.status);
  const statusLabel = statusDisplayLabel(task);
  const timeStr = timeInStatus(task);
  const branchHtml = task.branch
    ? `<span class="card-header-sep">·</span><span class="card-branch" title="${esc(task.branch)}">${esc(task.branch)}${worktreesByBranch[task.branch] ? ' (wt)' : ''}</span>`
    : '';

  // Card body
  const date = task.completed || task.started || task.created || '';
  const hasTags = task.sub_repo || task.stage != null || task.estimate;
  const depsCount = task.depends_on ? (Array.isArray(task.depends_on) ? task.depends_on.length : 1) : 0;
  const anchorsHtml = (task.anchors && task.anchors.length)
    ? `<div class="task-anchors" style="font-size:var(--fs-xs);color:var(--text-dim);margin-top:2px">📌 ${task.anchors.map(a => esc(a)).join(', ')}</div>`
    : '';

  card.innerHTML = `
    <div class="task-card-header">
      <div class="task-card-header-row1">
        <span class="task-id">${esc(task.id || '—')}</span>
        ${p ? `<span class="priority-badge ${pClass}">${esc(p)}</span>` : ''}
      </div>
      <div class="task-card-header-row2">
        <span class="card-status-label cs-${statusKey}">${esc(statusLabel)}</span>
        ${timeStr ? `<span class="card-header-sep">·</span><span class="card-time-in-status">${esc(timeStr)}</span>` : ''}
        ${branchHtml}
      </div>
    </div>
    <div class="task-card-body">
      <div class="task-title">${esc(task.title || 'Untitled')}</div>
      ${anchorsHtml}
      ${hasTags ? `<div class="task-card-tags">
        ${task.stage != null ? `<span class="tag-stage">S${esc(String(task.stage))}</span>` : ''}
        ${task.estimate ? `<span class="tag-estimate">${esc(task.estimate)}</span>` : ''}
        ${task.sub_repo ? `<span class="tag-subrepo">${esc(task.sub_repo)}</span>` : ''}
      </div>` : ''}
      <div class="task-card-footer">
        ${task._epicName ? `<span class="epic-tag">${esc(task._epicName)}</span>` : ''}
        ${task.archive_reason ? `<span class="epic-tag" style="color:var(--stat-archived-color);border-color:var(--stat-archived-border);">${esc(task.archive_reason)}</span>` : ''}
        ${task.docs ? `<span class="epic-tag" style="color:var(--accent);border-color:var(--p2-border);">docs</span>` : ''}
        ${depsCount ? `<span class="epic-tag" style="color:var(--p1);border-color:var(--p1-border);">${depsCount} dep${depsCount > 1 ? 's' : ''}</span>` : ''}
        ${date ? `<span class="task-date">${fmtTs(date)}</span>` : ''}
      </div>
    </div>
  `;

  return card;
}
```

Note: branch and worktree tags are removed from the footer — they now appear in the card header row 2.

- [ ] **Step 3: Update task-title margin for new structure**

The `.task-title` CSS has `margin-bottom: 8px` (line ~1108). This stays the same, but we need to remove the old `.task-card-top` margin since it no longer exists. Find:

```css
    .task-card-top {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 6px;
      margin-bottom: 6px;
    }
```

Replace with (keep it for any remaining references, or just remove it since it's replaced by `.task-card-header-row1`):

Delete the `.task-card-top` CSS rule entirely — it's replaced by `.task-card-header-row1`.

Also update `.task-card` to remove the old padding (since padding is now on `.task-card-header` and `.task-card-body`):

The `.task-card` rule was already updated in Task 1 Step 2 to have no padding and use `overflow: hidden`.

- [ ] **Step 4: Commit**

```bash
git add plugins/taskmaster/backlog-viewer.html
git commit -m "feat(viewer): enriched card headers with status, time-in-status, and branch"
```

---

### Task 5: CSS Cleanup — Remove Unused Styles

Remove CSS for elements that no longer exist.

**Files:**
- Modify: `plugins/taskmaster/backlog-viewer.html` (style section)

- [ ] **Step 1: Remove stat chip CSS**

Delete the `.stat-chip` styles (lines ~576-594):

```css
    .stat-chip { ... }
    .stat-chip .stat-num { ... }
    .stat-total { ... }
    .stat-done { ... }
    .stat-progress { ... }
    .stat-todo { ... }
    .stat-blocked { ... }
```

- [ ] **Step 2: Remove active session banner CSS**

Delete the `.active-session` styles (lines ~457-518):

```css
    .active-session { ... }
    [data-theme="light"] .active-session, ... { ... }
    .active-session-pulse { ... }
    @keyframes pulse { ... }
    .active-session-label { ... }
    .active-session-task { ... }
    .active-session-task .as-id { ... }
    .active-session-task .as-epic { ... }
```

- [ ] **Step 3: Remove now-working banner CSS**

Delete the `.now-working` styles (lines ~520-574):

```css
    .now-working { ... }
    [data-theme="light"] .now-working, ... { ... }
    .now-working-label { ... }
    .now-working-tasks { ... }
    .now-working-item { ... }
    .now-working-item .nw-id { ... }
    .now-working-item .nw-epic { ... }
```

- [ ] **Step 4: Remove toolbar CSS**

Delete the `.toolbar` styles (lines ~353-455):

```css
    .toolbar { ... }
    .filter-group { ... }
    .filter-label { ... }
    .filter-select { ... }
    .filter-select:focus { ... }
    .priority-toggles { ... }
    .priority-btn { ... } (and all variants)
    .toolbar-sep { ... }
    .archive-toggle { ... } (and all variants)
```

Wait — `.filter-group`, `.filter-select`, `.priority-toggles`, `.priority-btn`, and `.sort-dir-btn` are still used in the new header. Keep those. Only delete:

- `.toolbar` (the container — no longer exists)
- `.filter-label` (no longer used — labels removed from the compact layout)
- `.toolbar-sep` (no longer exists)
- `.archive-toggle` and `.archive-toggle:hover`, `.archive-toggle.active`, `.archive-toggle .archive-count` (button removed from toolbar)

- [ ] **Step 5: Remove .task-card-top CSS**

Delete the rule:

```css
    .task-card-top {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 6px;
      margin-bottom: 6px;
    }
```

- [ ] **Step 6: Remove old theme-toggle button CSS**

The `.theme-toggle` CSS (lines ~1282-1299) can be removed — replaced by `.settings-btn`. Delete:

```css
    .theme-toggle { ... }
    .theme-toggle:hover { ... }
    .theme-toggle.active { ... }
```

- [ ] **Step 7: Update responsive CSS**

In the `@media (max-width: 768px)` block (lines ~1634-1651), remove references to `.toolbar`, `.stats-row`, `.now-working`:

Replace:

```css
    @media (max-width: 768px) {
      .header { padding: 10px 16px; }
      .toolbar, .epics-section, .board-wrapper, .archived-section, .stats-row { padding-left: 16px; padding-right: 16px; }
      .board { flex-direction: column; }
      body { overflow: auto; }
      .board-wrapper { flex: none; }
      .column-body { min-height: 200px; max-height: none; }
      .header-search { width: 140px; }
      .epics-grid { gap: 8px; }
      .epic-card { max-width: 100%; }
      .now-working { padding: 8px 16px; gap: 10px; flex-direction: column; align-items: flex-start; }
      .archived-grid { grid-template-columns: 1fr; }
    }
```

With:

```css
    @media (max-width: 768px) {
      .header { padding: 10px 16px; flex-wrap: wrap; }
      .epics-section, .board-wrapper, .archived-section { padding-left: 16px; padding-right: 16px; }
      .board { flex-direction: column; }
      body { overflow: auto; }
      .board-wrapper { flex: none; }
      .column-body { min-height: 200px; max-height: none; }
      .header-search { width: 140px; }
      .epics-grid { gap: 8px; }
      .epic-card { max-width: 100%; }
      .archived-grid { grid-template-columns: 1fr; }
    }
```

- [ ] **Step 8: Commit**

```bash
git add plugins/taskmaster/backlog-viewer.html
git commit -m "chore(viewer): remove unused CSS for deleted header elements"
```

---

### Task 6: Remove Unused CSS Variables & Final Verification

Clean up any CSS variables that were only used by deleted elements, and verify the file is consistent.

**Files:**
- Modify: `plugins/taskmaster/backlog-viewer.html` (CSS variables section)

- [ ] **Step 1: Remove stat-specific CSS variables that are only used by deleted stat chips**

The `--stat-total-*` variables (line ~43) are only used by `.stat-total` which was deleted. Remove them from all theme blocks:

```css
      --stat-total-bg: ...; --stat-total-border: ...;
```

Actually — check if any remaining elements use these. The `--stat-done-*`, `--stat-progress-*`, `--stat-todo-*`, `--stat-blocked-*`, and `--stat-archived-*` variables are used by status chips in the modal and card header. Only `--stat-total-*` is exclusively used by the deleted stat chip. Remove only `--stat-total-bg` and `--stat-total-border` from all four theme blocks (dark, light, colored, light-colored).

- [ ] **Step 2: Verify — Open the viewer in a browser**

Open `plugins/taskmaster/backlog-viewer.html` in a browser with a sample `backlog.yaml` and verify:

1. Row 1 shows: logo, project name, read-only badge, search, priority toggles, sort, settings gear
2. Settings gear opens dropdown with Theme and Project color toggles
3. Row 2 shows phase pills (if phases exist)
4. Row 3 shows epic cards (if epics exist)
5. No stat chips, no active session banner, no "now working on" banner
6. Cards have enriched header with ID, priority, status label, time-in-status, branch
7. Card body has title, anchors, tags, footer (no branch in footer)
8. Recently moved cards show glow instead of left border
9. Archive section at bottom works with its own toggle
10. Theme/color toggles work from settings dropdown
11. Search, priority toggles, sort all work from header row

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/backlog-viewer.html
git commit -m "chore(viewer): remove unused CSS variables and finalize compact header"
```
