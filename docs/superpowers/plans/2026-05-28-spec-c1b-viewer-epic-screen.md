# Spec C1b — Viewer Epic Screen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the viewer a first-class epic surface — a `load_v3`-backed `GET /api/epic/<id>` endpoint, a reusable `mountEpicDetail` component (rollup + components + design-lock + narrative + tasks), a `/epic/<id>` detail screen, an `/epics` list screen, and a sidebar entry — so epics stop being filter-labels and become a readable command center.

**Architecture:** The C1a backend already stores epic heavy fields (`description`/`docs`/`components`) in `epics/<id>.md` and merges them on `load_v3`. But the viewer's polled `/api/backlog` (`_serve_json`, `backlog_server.py:7678`) uses raw `yaml.safe_load` and serves **slim** epics without those fields. So C1b adds a per-epic endpoint that goes through `_load()` (which calls `_load_v3`) — mirroring the existing `/api/task/<id>` → `_load_task_full` seam. The render logic lives in a mountable component `mountEpicDetail(container, {epic, …, chrome})` authored **embedded-aware from day one** (per the entity-detail-modals spec-review) so the upcoming modal feature reuses it unchanged; the `/epic/<id>` route screen is a thin fetch→mount wrapper, exactly like `task-detail.js` → `mountTaskDetailDocument`.

**Tech Stack:** Python 3 + http.server handler (no FastMCP change — this is an HTTP route, not an MCP tool); vanilla ES-module viewer (no build step), `marked@12` for markdown; pytest for the endpoint; `node:test` for pure JS helpers; Playwright for screen e2e.

**Scope guardrails:**
- C1 content only. The **C2 generated component diagram is out of scope** — `mountEpicDetail` leaves a named extension point where the diagram will mount.
- Navigation entry points that belong to the **modal feature** (kanban epic `↗`, card-click switch, settings toggle) are NOT in this plan — but the `/epics` list rows and the sidebar entry ARE (a reachable front door is part of C1b).
- Run pytest from repo root: `python -m pytest plugins/taskmaster/tests/ -q`. Run JS units with `node --test`. Run e2e via `plugins/taskmaster/viewer/tests/run_smoke.sh` (boots `_make_server`, then `npx playwright test`).
- The pre-existing `smoke.spec.js` sidebar-link-count assertion is **already stale** (it expects 7; the live sidebar has 13) and is not gating — do not try to "fix" it here; add dedicated specs instead.

**Reference (verbatim ground truth used by this plan):**
- `backlog_server.py`: `_load` (349, uses `_load_v3`), `_find_epic` (433), `_component_rollup` (491), `_epic_stats` (5906), `_load_task_full` (6599, the route-loader pattern to mirror), `do_GET` dispatch with `/api/task/` block (7387–7406) and `/api/backlog`→`_serve_json` (7407, 7678), `_send_json(code, obj, etag=…)` usage (e.g. 7404), `compute_etag` import-from-`taskmaster_v3` pattern (7402).
- `taskmaster_v3.py`: `EPIC_HEAVY_FIELDS = ("description","docs","components")` (424).
- Viewer: `api.js` `getTask` (62–69) + `api` object (80–98); `main.js` `registerScreen` block (11–26); `sidebar.js` `SECTIONS` (8–32) + route-changed active sync (90–101); `index.html` screen CSS `<link>`s (11–24); `lib/epics.js` `assignEpicColors`/`epicCssVar` (16–46); `components/markdown.js` `mountMarkdown`; `screens/issue-detail.js` (mount pattern), `screens/task-detail.js` (fetch→mount-component pattern); `tests/conftest.py` `tmp_taskmaster` (24) + `tm_epic_phase` (95); `tests/unit/epics.test.js` (node:test pattern).

---

## Phase 1 — Backend: `load_v3`-backed epic endpoint

### Task 1: `_load_epic_full(epic_id)` loader

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py` (add `_load_epic_full` near `_load_task_full`, after line ~6650; it only needs `_load`/`_find_epic`/`_epic_stats`/`_component_rollup`, all defined earlier in the module)
- Test: `plugins/taskmaster/tests/test_epic_detail_endpoint.py` (new)

- [ ] **Step 1: Write the failing test**

```python
# plugins/taskmaster/tests/test_epic_detail_endpoint.py
import json
from backlog_server import (
    backlog_add_epic, backlog_add_task, backlog_update_task,
    backlog_update_epic, _load_epic_full,
)


def test_load_epic_full_unknown_returns_none(tmp_taskmaster):
    assert _load_epic_full("ghost") is None


def test_load_epic_full_merges_heavy_fields_and_rollup(tm_epic_phase):
    # heavy fields (description/components) live in epics/<id>.md and must come
    # back through load_v3 — the whole point of the endpoint.
    backlog_update_epic("test-epic", "design_status", "locked")
    backlog_update_epic("test-epic", "description", "Ingest + thumbnail + CDN.")
    backlog_update_epic("test-epic", "components",
                        json.dumps({"core": {"title": "Core", "after": []}}))
    for tid, status in [("E-1", "done"), ("E-2", "in-progress"), ("E-3", "todo")]:
        backlog_add_task(epic="test-epic", task_id=tid, title=tid, phase="dev")
        backlog_update_task(tid, "component", "core")
        backlog_update_task(tid, "status", status)

    out = _load_epic_full("test-epic")
    assert out["id"] == "test-epic"
    assert out["design_status"] == "locked"
    assert out["description"].startswith("Ingest")          # merged via load_v3
    assert out["components"]["core"]["title"] == "Core"
    assert out["stats"]["total"] == 3 and out["stats"]["done"] == 1
    assert out["component_rollup"]["core"]["total"] == 3
    assert {t["id"] for t in out["tasks"]} == {"E-1", "E-2", "E-3"}
    # tasks are slim — no heavy _body leaking into the list
    assert all("_body" not in t for t in out["tasks"])


def test_load_epic_full_attention_lists_blocked(tm_epic_phase):
    backlog_add_task(epic="test-epic", task_id="B-1", title="blocked one", phase="dev")
    backlog_update_task("B-1", "status", "blocked")
    backlog_update_task("B-1", "blockers", "waiting on CDN creds")
    out = _load_epic_full("test-epic")
    assert any(a["id"] == "B-1" and a["blocked"] and "CDN creds" in a["why"]
               for a in out["attention"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest plugins/taskmaster/tests/test_epic_detail_endpoint.py -q`
Expected: FAIL with `ImportError: cannot import name '_load_epic_full'`.

- [ ] **Step 3: Implement `_load_epic_full`**

In `backlog_server.py`, after `_load_task_full` (ends ~line 6650), add:

```python
def _load_epic_full(epic_id: str) -> dict | None:
    """Epic with heavy fields (description/docs/components) merged from
    epics/<id>.md via load_v3, plus derived status counts, per-component
    rollup, a blocked/blockers attention list, and a slim task list.

    Returns None if the epic id is unknown. Mirrors _load_task_full but
    routes through _load() (which calls _load_v3) so heavy fields that
    /api/backlog strips are present here.
    """
    if not _backlog_path().exists():
        return None
    data = _load()
    epic = _find_epic(data, epic_id)
    if epic is None:
        return None

    out = {k: v for k, v in epic.items() if k != "tasks"}
    out.setdefault("description", "")
    out.setdefault("docs", {})
    out.setdefault("components", {})
    out.setdefault("design_status", "exploring")
    out["stats"] = _epic_stats(data, epic_id)
    out["component_rollup"] = _component_rollup(data, epic_id)

    attention = []
    for t in epic.get("tasks", []):
        if t.get("status") == "blocked":
            attention.append({"id": t.get("id"), "title": t.get("title"),
                              "blocked": True, "why": t.get("blockers", "")})
        elif t.get("blockers"):
            attention.append({"id": t.get("id"), "title": t.get("title"),
                              "blocked": False, "why": t.get("blockers")})
    out["attention"] = attention

    out["tasks"] = [
        {"id": t.get("id"), "title": t.get("title"),
         "status": t.get("status", "todo"), "component": t.get("component"),
         "priority": t.get("priority"), "phase": t.get("phase"),
         "design_change": t.get("design_change")}
        for t in epic.get("tasks", [])
    ]
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest plugins/taskmaster/tests/test_epic_detail_endpoint.py -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_epic_detail_endpoint.py
git commit -m "feat(taskmaster): _load_epic_full loader (load_v3-backed) (C1b)"
```

---

### Task 2: `GET /api/epic/<id>` route

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py` (`do_GET`, insert a branch immediately after the `/api/task/` block at line 7406, before `elif clean_path == "/api/backlog":` at 7407)
- Test: covered end-to-end by the Playwright spec in Task 9; the data logic is unit-tested in Task 1. The route is 8 lines of glue mirroring the proven `/api/task/` dispatch (which itself has no pytest, only `_load_task_full` does).

- [ ] **Step 1: Add the route branch**

In `do_GET`, after the `/api/task/` block's closing `self.send_error(HTTPStatus.NOT_FOUND)` (line 7406) and before `elif clean_path == "/api/backlog":`, insert:

```python
        elif clean_path.startswith("/api/epic/"):
            eid = clean_path[len("/api/epic/"):].rstrip("/")
            if eid and "/" not in eid:
                full = _load_epic_full(eid)
                if full is None:
                    self._send_json(404, {"ok": False, "error": f"epic {eid} not found"})
                    return
                from taskmaster_v3 import compute_etag
                etag = compute_etag(_backlog_path())
                self._send_json(200, full, etag=etag)
                return
            self.send_error(HTTPStatus.NOT_FOUND)
```

- [ ] **Step 2: Verify no regressions + manual smoke**

Run: `python -m pytest plugins/taskmaster/tests/ -q`
Expected: PASS (full suite — the new branch can't affect other routes).

Manual smoke (optional, requires a backlog with an epic): start the server and curl the route:
```bash
python -c "from backlog_server import _make_server; s,p=_make_server(port=8799); import threading; threading.Thread(target=s.serve_forever,daemon=True).start(); import urllib.request,sys; print(urllib.request.urlopen('http://127.0.0.1:8799/api/epic/task-epic-protocol').read()[:200])"
```
Expected: a JSON blob containing `"id": "task-epic-protocol"` and a `"stats"` key (or a 404 line if that epic id isn't present locally — either proves the route is wired).

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/backlog_server.py
git commit -m "feat(taskmaster): GET /api/epic/<id> route (C1b)"
```

---

## Phase 2 — Pure render helpers (node:test)

### Task 3: `epic-format.js`

**Files:**
- Create: `plugins/taskmaster/viewer/js/lib/epic-format.js`
- Test: `plugins/taskmaster/viewer/tests/unit/epic-format.test.js` (new; mirrors `tests/unit/epics.test.js`)

- [ ] **Step 1: Write the failing test**

```javascript
// plugins/taskmaster/viewer/tests/unit/epic-format.test.js
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  designBadge, componentGlyph, progressPercent, tasksForComponent,
} from '../../js/lib/epic-format.js';

test('designBadge — locked carries a lock flag and label', () => {
  const b = designBadge('locked');
  assert.equal(b.locked, true);
  assert.equal(b.label, 'Locked');
  assert.equal(b.cls, 'locked');
});

test('designBadge — unknown/empty falls back to exploring', () => {
  assert.equal(designBadge('bogus').cls, 'exploring');
  assert.equal(designBadge(undefined).cls, 'exploring');
});

test('componentGlyph — per-status glyph, default for unknown', () => {
  assert.equal(componentGlyph('done'), '●');
  assert.equal(componentGlyph('in-progress'), '◐');
  assert.equal(componentGlyph('blocked'), '✗');
  assert.equal(componentGlyph('todo'), '○');
  assert.equal(componentGlyph(undefined), '○');
});

test('progressPercent — (done+archived)/total, 0 when empty', () => {
  assert.equal(progressPercent({ total: 4, done: 1, archived: 1 }), 50);
  assert.equal(progressPercent({ total: 0 }), 0);
  assert.equal(progressPercent(undefined), 0);
});

test('tasksForComponent — key match, and _unassigned = no component', () => {
  const tasks = [
    { id: 'a', component: 'core' },
    { id: 'b', component: 'ui' },
    { id: 'c' },
  ];
  assert.deepEqual(tasksForComponent(tasks, 'core').map(t => t.id), ['a']);
  assert.deepEqual(tasksForComponent(tasks, '_unassigned').map(t => t.id), ['c']);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test plugins/taskmaster/viewer/tests/unit/epic-format.test.js`
Expected: FAIL — module `epic-format.js` does not exist (`ERR_MODULE_NOT_FOUND`).

- [ ] **Step 3: Implement `epic-format.js`**

```javascript
// plugins/taskmaster/viewer/js/lib/epic-format.js
// Pure formatting helpers for the epic detail/list views. No DOM, no imports —
// unit-tested with node:test, consumed by mountEpicDetail + the epics list.

const DESIGN_STATUS = {
  exploring: { label: 'Exploring', cls: 'exploring', locked: false },
  proposed:  { label: 'Proposed',  cls: 'proposed',  locked: false },
  locked:    { label: 'Locked',    cls: 'locked',    locked: true  },
  revising:  { label: 'Revising',  cls: 'revising',  locked: false },
};

export function designBadge(status) {
  return DESIGN_STATUS[status] || { label: 'Exploring', cls: 'exploring', locked: false };
}

const COMPONENT_GLYPH = { done: '●', 'in-progress': '◐', blocked: '✗', todo: '○' };

export function componentGlyph(status) {
  return COMPONENT_GLYPH[status] || '○';
}

export function progressPercent(stats) {
  const total = stats?.total || 0;
  if (!total) return 0;
  const done = (stats.done || 0) + (stats.archived || 0);
  return Math.round((done / total) * 100);
}

export function tasksForComponent(tasks, key) {
  const list = Array.isArray(tasks) ? tasks : [];
  if (key === '_unassigned') return list.filter(t => !t.component);
  return list.filter(t => t.component === key);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test plugins/taskmaster/viewer/tests/unit/epic-format.test.js`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/viewer/js/lib/epic-format.js plugins/taskmaster/viewer/tests/unit/epic-format.test.js
git commit -m "feat(taskmaster): epic-format pure render helpers (C1b)"
```

---

## Phase 3 — API client, routing, sidebar

### Task 4: `api.getEpic(id)`

**Files:**
- Modify: `plugins/taskmaster/viewer/js/api.js` (add a named export beside `getTask` at line 62; add `getEpic,` to the `api` object near line 91)
- Test: exercised by the e2e specs in Tasks 6 & 9 (the viewer's `api.js` has no unit harness; `getTask` likewise is covered only by e2e).

- [ ] **Step 1: Add the client function**

In `api.js`, after `getTask` (ends line 69), add:

```javascript
export async function getEpic(id) {
  const resp = await fetch(`/api/epic/${encodeURIComponent(id)}`);
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body.error || `epic ${id} not found`);
  }
  return resp.json();
}
```

In the `api` object literal, add `getEpic,` immediately after the `getTask,` line (line 91):

```javascript
  getTask,
  getEpic,
```

- [ ] **Step 2: Verify it imports cleanly**

Run: `node --input-type=module -e "import('./plugins/taskmaster/viewer/js/api.js').then(m => { if (typeof m.getEpic !== 'function') throw new Error('getEpic missing'); console.log('ok'); })"`
Expected: prints `ok` (module parses and exports `getEpic`).

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/js/api.js
git commit -m "feat(taskmaster): api.getEpic client (C1b)"
```

---

### Task 5: Register routes, sidebar entry, CSS links

**Files:**
- Modify: `plugins/taskmaster/viewer/js/main.js` (registerScreen block, after line 14)
- Modify: `plugins/taskmaster/viewer/js/components/sidebar.js` (`SECTIONS`, Frontdoor group lines 9–14)
- Modify: `plugins/taskmaster/viewer/index.html` (screen CSS links, after line 14)
- Test: verified by the Playwright specs in Tasks 6 & 9.

- [ ] **Step 1: Register the screens**

In `main.js`, after `registerScreen('/task', …)` (line 14), add:

```javascript
registerScreen('/epics',      () => import('./screens/epics.js'));
registerScreen('/epic',       () => import('./screens/epic-detail.js'));
```

- [ ] **Step 2: Add the sidebar entry**

In `sidebar.js`, in the `Frontdoor` group (after the `task` item, line 13), add:

```javascript
    { key: 'epics',     icon: '⬡', label: 'Epics',     hash: '#/epics' },
```

- [ ] **Step 3: Add the CSS links**

In `index.html`, after the `task-detail.css` link (line 14), add:

```html
  <link rel="stylesheet" href="css/screens/epics.css">
  <link rel="stylesheet" href="css/screens/epic-detail.css">
```

- [ ] **Step 4: Commit**

```bash
git add plugins/taskmaster/viewer/js/main.js plugins/taskmaster/viewer/js/components/sidebar.js plugins/taskmaster/viewer/index.html
git commit -m "feat(taskmaster): register epic screens + sidebar entry + css links (C1b)"
```

(The two CSS files are created in Tasks 6 & 7; a missing stylesheet link is a no-op until then, so committing the link now is safe.)

---

## Phase 4 — Screens & component

### Task 6: `/epics` list screen

**Files:**
- Create: `plugins/taskmaster/viewer/js/screens/epics.js`
- Create: `plugins/taskmaster/viewer/css/screens/epics.css`
- Test: `plugins/taskmaster/viewer/tests/epics.spec.js` (new Playwright spec)

- [ ] **Step 1: Write the failing e2e test**

```javascript
// plugins/taskmaster/viewer/tests/epics.spec.js
import { test, expect } from '@playwright/test';

test.describe('Epics list', () => {
  test('route #/epics resolves and renders the list container', async ({ page }) => {
    const errors = [];
    page.on('pageerror', e => errors.push(String(e)));
    await page.goto('/v3');
    await page.evaluate(() => location.hash = '#/epics');
    await expect(page.locator('#page-title')).toHaveText('Epics');
    await expect(page.locator('.epics')).toBeVisible();
    await expect(page.locator('.sidebar-link[data-key="epics"]')).toHaveClass(/active/);
    expect(errors).toEqual([]);
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd plugins/taskmaster/viewer/tests && VIEWER_BASE_URL="http://127.0.0.1:8765" npx playwright test epics.spec.js`
(Start the server first per `run_smoke.sh`, or just run `bash plugins/taskmaster/viewer/tests/run_smoke.sh` which boots it.)
Expected: FAIL — `#/epics` is unregistered/empty, `.epics` never appears, page-title not "Epics".

- [ ] **Step 3: Implement the list screen**

```javascript
// plugins/taskmaster/viewer/js/screens/epics.js
import { claimTopbar } from '../lib/topbar.js';
import { assignEpicColors, epicCssVar } from '../lib/epics.js';
import { progressPercent } from '../lib/epic-format.js';

export const meta = { title: 'Epics', icon: '⬡', sidebarKey: 'epics' };

function esc(s) {
  return String(s == null ? '' : s)
    .replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}

export async function mount(root, { store }) {
  root.innerHTML = '';
  root.classList.add('epics');
  claimTopbar();
  const unsub = store.subscribe('backlog', render);
  render();

  function render() {
    const bl = store.getBacklog() || {};
    const epics = bl.epics || [];
    const tasks = bl.tasks || [];
    const colors = assignEpicColors(epics);
    root.replaceChildren();

    if (!epics.length) {
      const empty = document.createElement('div');
      empty.className = 'epics-empty';
      empty.textContent = 'No epics yet.';
      root.appendChild(empty);
      return;
    }

    const list = document.createElement('div');
    list.className = 'epics-list';
    for (const ep of epics) {
      const mine = tasks.filter(t => t.epic === ep.id);
      const stats = {
        total: mine.length,
        done: mine.filter(t => t.status === 'done').length,
        archived: mine.filter(t => t.status === 'archived').length,
      };
      const pct = progressPercent(stats);
      const a = document.createElement('a');
      a.className = 'epic-row';
      a.href = `#/epic/${encodeURIComponent(ep.id)}`;
      a.setAttribute('style', epicCssVar(colors[ep.id]));
      a.innerHTML = `
        <span class="epic-row__swatch"></span>
        <span class="epic-row__name">${esc(ep.name || ep.id)}</span>
        <span class="epic-row__ds">${esc(ep.design_status || 'exploring')}</span>
        <span class="epic-row__count">${stats.done}/${stats.total}</span>
        <span class="epic-row__bar"><span style="width:${pct}%"></span></span>`;
      list.appendChild(a);
    }
    root.appendChild(list);
  }

  return () => { unsub(); root.classList.remove('epics'); };
}
```

- [ ] **Step 4: Create the CSS** (honors no-left-rails / no-shadow / no-hover-motion)

```css
/* plugins/taskmaster/viewer/css/screens/epics.css */
.epics { padding: 16px 20px; }
.epics-empty { color: var(--ink-3); padding: 24px; }
.epics-list { display: flex; flex-direction: column; gap: 8px; max-width: 920px; }
.epic-row {
  display: grid;
  grid-template-columns: 12px 1fr auto auto 160px;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  background: var(--bg-card);
  border: 1px solid var(--bl, rgba(255,255,255,0.06));
  border-radius: 8px;
  text-decoration: none;
  color: var(--ink-1);
}
.epic-row:hover { background: var(--bg-card-hover); border-color: var(--epic, rgba(255,255,255,0.18)); }
.epic-row__swatch { width: 10px; height: 10px; border-radius: 3px; background: var(--epic); }
.epic-row__name { font-weight: 600; }
.epic-row__ds { font-size: var(--text-xs); color: var(--ink-3); text-transform: capitalize; }
.epic-row__count { font-family: var(--font-mono); font-size: var(--text-xs); color: var(--ink-2); }
.epic-row__bar { height: 6px; background: var(--bg-deep); border-radius: 3px; overflow: hidden; }
.epic-row__bar > span { display: block; height: 100%; background: var(--epic); }
```

- [ ] **Step 5: Run the e2e test to verify it passes**

Run: `bash plugins/taskmaster/viewer/tests/run_smoke.sh` (or the targeted `npx playwright test epics.spec.js` against a running server).
Expected: PASS (route resolves, `.epics` visible, sidebar link active).

- [ ] **Step 6: Commit**

```bash
git add plugins/taskmaster/viewer/js/screens/epics.js plugins/taskmaster/viewer/css/screens/epics.css plugins/taskmaster/viewer/tests/epics.spec.js
git commit -m "feat(taskmaster): epics list screen (C1b)"
```

---

### Task 7: `mountEpicDetail` component — header, badge, progress, narrative, empty/error (embedded-aware)

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/epic-detail-document.js`
- Create: `plugins/taskmaster/viewer/css/screens/epic-detail.css`
- Test: covered by the route e2e in Task 9 (the component is exercised through the `/epic/<id>` screen).

> **Why embedded-aware now:** the entity-detail-modals spec-review requires detail components to render their actions into a caller-supplied host rather than `claimTopbar()`, so the modal can reuse them. `mountEpicDetail` has no topbar actions in C1 (no A/B variant, no Edit yet), so "embedded mode" here simply means it **never touches the page topbar/sidebar/title** and confines all output to `container`. The `chrome`/`actionsHost` params are accepted for forward-compatibility and currently only gate a future actions row.

- [ ] **Step 1: Implement the component (header + narrative + states)**

```javascript
// plugins/taskmaster/viewer/js/components/epic-detail-document.js
// Render an epic's C1 detail into `container`. Pure of page chrome: it never
// calls claimTopbar() and writes nothing outside `container`, so it drops
// cleanly into both the /epic/<id> screen and the detail modal.
import { mountMarkdown } from './markdown.js';
import { assignEpicColors, epicCssVar } from '../lib/epics.js';
import {
  designBadge, componentGlyph, progressPercent, tasksForComponent,
} from '../lib/epic-format.js';

function esc(s) {
  return String(s == null ? '' : s)
    .replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}

// chrome: 'page' (route screen) | 'embedded' (modal). actionsHost: optional
// element to receive an actions row (none in C1). onNavigate(taskId): jump to a task.
export function mountEpicDetail(container, { epic, store, onNavigate, chrome = 'page' } = {}) {
  container.classList.add('ed-root');
  const colors = assignEpicColors((store?.getBacklog?.() || {}).epics || [{ id: epic.id }]);
  container.setAttribute('style', epicCssVar(colors[epic.id]));

  const go = onNavigate || ((tid) => { location.hash = `#/task/${encodeURIComponent(tid)}`; });

  container.replaceChildren();

  // crumb (only meaningful as a screen; harmless in modal)
  if (chrome === 'page') {
    const crumb = document.createElement('div');
    crumb.className = 'ed-crumb';
    crumb.innerHTML = `<a class="ed-back" href="#/epics">‹ Epics</a>`;
    container.appendChild(crumb);
  }

  // header
  const badge = designBadge(epic.design_status);
  const pct = progressPercent(epic.stats);
  const head = document.createElement('header');
  head.className = 'ed-head';
  head.innerHTML = `
    <div class="ed-meta">
      <span class="ed-swatch"></span>
      <span class="ed-id">${esc(epic.id)}</span>
      <span class="ed-ds ed-ds--${badge.cls}">${badge.locked ? '🔒 ' : ''}${esc(badge.label)}</span>
      <span class="ed-epic-status">${esc(epic.status || 'active')}</span>
    </div>
    <h1 class="ed-title">${esc(epic.name || epic.id)}</h1>
    <div class="ed-progress">
      <span class="ed-progress__bar"><span style="width:${pct}%"></span></span>
      <span class="ed-progress__label">${(epic.stats?.done || 0)}/${(epic.stats?.total || 0)} done · ${pct}%</span>
    </div>`;
  container.appendChild(head);

  const grid = document.createElement('div');
  grid.className = 'ed-grid';
  const main = document.createElement('div'); main.className = 'ed-main';
  const side = document.createElement('aside'); side.className = 'ed-side';
  grid.append(main, side);
  container.appendChild(grid);

  // narrative (description field + body markdown)
  const narrative = [epic.description, epic._body].filter(Boolean).join('\n\n');
  if (narrative) {
    const sec = document.createElement('section');
    sec.className = 'ed-narrative';
    const h = document.createElement('h2'); h.className = 'ed-h'; h.textContent = 'Design';
    const md = document.createElement('div'); md.className = 'ed-md';
    mountMarkdown(md, narrative);
    sec.append(h, md);
    main.appendChild(sec);
  }

  // Component / task / attention / docs sections are filled by Task 8; this
  // task ships the header + narrative + the empty-narrative case. The diagram
  // (C2) will mount into a `.ed-diagram` node added here later (extension point).
  mountEpicDetail._fillBody?.(container, { epic, main, side, go });

  return () => { container.classList.remove('ed-root'); container.replaceChildren(); };
}
```

> Task 8 fills `main`/`side` by replacing the `mountEpicDetail._fillBody?.(…)` line with the actual section-building code. (Using a real call site now keeps Task 7 runnable and Task 8 a clean inline replacement — no dead hook ships.)

- [ ] **Step 2: Create the CSS**

```css
/* plugins/taskmaster/viewer/css/screens/epic-detail.css */
.ed-root { padding: 16px 20px; max-width: 1100px; }
.ed-crumb { margin-bottom: 8px; }
.ed-back { color: var(--ink-3); text-decoration: none; font-size: var(--text-sm); }
.ed-back:hover { color: var(--accent); }
.ed-head { border-bottom: 1px solid rgba(255,255,255,0.07); padding-bottom: 14px; margin-bottom: 16px; }
.ed-meta { display: flex; align-items: center; gap: 10px; font-size: var(--text-xs); }
.ed-swatch { width: 10px; height: 10px; border-radius: 3px; background: var(--epic); }
.ed-id { font-family: var(--font-mono); color: var(--ink-2); }
.ed-ds { padding: 1px 8px; border-radius: 999px; background: var(--epic-soft); color: var(--epic); text-transform: capitalize; }
.ed-ds--locked { background: color-mix(in srgb, var(--amber) 16%, transparent); color: var(--amber); }
.ed-ds--revising { background: color-mix(in srgb, var(--accent) 16%, transparent); color: var(--accent); }
.ed-epic-status { color: var(--ink-3); }
.ed-title { font-size: var(--text-2xl); margin: 8px 0 12px; }
.ed-progress { display: flex; align-items: center; gap: 10px; }
.ed-progress__bar { flex: 1; max-width: 360px; height: 6px; background: var(--bg-deep); border-radius: 3px; overflow: hidden; }
.ed-progress__bar > span { display: block; height: 100%; background: var(--epic); }
.ed-progress__label { font-family: var(--font-mono); font-size: var(--text-xs); color: var(--ink-2); }
.ed-grid { display: grid; grid-template-columns: 1fr 280px; gap: 20px; }
.ed-main { min-width: 0; }
.ed-h { font-size: var(--text-sm); text-transform: uppercase; letter-spacing: 0.04em; color: var(--ink-3); margin: 0 0 8px; }
.ed-narrative { margin-bottom: 20px; }
.ed-md { color: var(--ink-1); line-height: 1.55; }
@media (max-width: 760px) { .ed-grid { grid-template-columns: 1fr; } }
```

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/epic-detail-document.js plugins/taskmaster/viewer/css/screens/epic-detail.css
git commit -m "feat(taskmaster): mountEpicDetail header/narrative (embedded-aware) (C1b)"
```

---

### Task 8: `mountEpicDetail` — components, tasks-by-component, attention, docs

**Files:**
- Modify: `plugins/taskmaster/viewer/js/components/epic-detail-document.js` (replace the `mountEpicDetail._fillBody?.(…)` call site)
- Modify: `plugins/taskmaster/viewer/css/screens/epic-detail.css` (append component/attention/docs styles)
- Test: covered by the route e2e in Task 9.

- [ ] **Step 1: Replace the body-fill call site**

In `epic-detail-document.js`, replace the single line:

```javascript
  mountEpicDetail._fillBody?.(container, { epic, main, side, go });
```

with:

```javascript
  // ---- Components + tasks grouped by component (main column)
  const comps = epic.components || {};
  const roll = epic.component_rollup || {};
  const compSec = document.createElement('section');
  compSec.className = 'ed-components';
  const ch = document.createElement('h2'); ch.className = 'ed-h'; ch.textContent = 'Components';
  compSec.appendChild(ch);

  const keys = Object.keys(comps);
  if (!keys.length) {
    const none = document.createElement('p');
    none.className = 'ed-body'; none.textContent = 'No components declared.';
    compSec.appendChild(none);
  }
  const groups = [...keys.map(k => [k, comps[k]?.title || k]), ['_unassigned', 'Unassigned']];
  for (const [key, title] of groups) {
    const b = roll[key] || { total: 0, done: 0, status: 'todo' };
    if (key === '_unassigned' && !b.total) continue;
    const block = document.createElement('div'); block.className = 'ed-comp';
    const hd = document.createElement('div');
    hd.className = `ed-comp__head ed-comp__head--${b.status || 'todo'}`;
    hd.innerHTML = `<span class="ed-comp__glyph">${componentGlyph(b.status)}</span>`
      + `<span class="ed-comp__title">${esc(title)}</span>`
      + `<span class="ed-comp__count">${b.done || 0}/${b.total || 0}</span>`;
    block.appendChild(hd);

    const ul = document.createElement('ul'); ul.className = 'ed-comp__tasks';
    for (const t of tasksForComponent(epic.tasks || [], key)) {
      const li = document.createElement('li');
      li.className = 'ed-task';
      const a = document.createElement('a');
      a.className = 'ed-task__link';
      a.href = `#/task/${encodeURIComponent(t.id)}`;
      a.addEventListener('click', (e) => { e.preventDefault(); go(t.id); });
      a.innerHTML = `<span class="ed-task__st ed-task__st--${esc(t.status || 'todo')}"></span>`
        + `<span class="ed-task__id">${esc(t.id)}</span>`
        + `<span class="ed-task__title">${esc(t.title || '')}</span>`;
      li.appendChild(a);
      ul.appendChild(li);
    }
    block.appendChild(ul);
    compSec.appendChild(block);
  }
  main.appendChild(compSec);
  // C2 diagram extension point: a `.ed-diagram` node mounts above compSec here.

  // ---- Attention (side column)
  if ((epic.attention || []).length) {
    const sec = document.createElement('section'); sec.className = 'ed-side-block';
    const h = document.createElement('h2'); h.className = 'ed-h'; h.textContent = 'Attention';
    sec.appendChild(h);
    const ul = document.createElement('ul'); ul.className = 'ed-attn';
    for (const a of epic.attention) {
      const li = document.createElement('li');
      const link = document.createElement('a');
      link.href = `#/task/${encodeURIComponent(a.id)}`;
      link.addEventListener('click', (e) => { e.preventDefault(); go(a.id); });
      link.textContent = a.id;
      li.append(
        document.createTextNode(`${a.blocked ? '⏸ ' : '⚠ '}`),
        link,
        document.createTextNode(a.why ? `: ${a.why}` : ''),
      );
      ul.appendChild(li);
    }
    sec.appendChild(ul);
    side.appendChild(sec);
  }

  // ---- Docs (side column)
  const docs = epic.docs || {};
  if (Object.keys(docs).length) {
    const sec = document.createElement('section'); sec.className = 'ed-side-block';
    const h = document.createElement('h2'); h.className = 'ed-h'; h.textContent = 'Docs';
    sec.appendChild(h);
    const ul = document.createElement('ul'); ul.className = 'ed-docs';
    for (const [k, path] of Object.entries(docs)) {
      const li = document.createElement('li');
      const a = document.createElement('a');
      a.href = `/file/${path}`; a.target = '_blank'; a.rel = 'noopener';
      a.textContent = k;
      li.append(a, document.createTextNode(` — ${path}`));
      ul.appendChild(li);
    }
    sec.appendChild(ul);
    side.appendChild(sec);
  }
```

- [ ] **Step 2: Append the CSS**

Append to `epic-detail.css`:

```css
.ed-body { color: var(--ink-2); }
.ed-comp { margin-bottom: 14px; border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; overflow: hidden; }
.ed-comp__head { display: flex; align-items: center; gap: 8px; padding: 8px 12px; background: var(--bg-panel); }
.ed-comp__head--done { color: var(--green, #5fcdb8); }
.ed-comp__head--blocked { color: var(--red, #e87a85); }
.ed-comp__head--in-progress { color: var(--amber, #e8a34d); }
.ed-comp__glyph { width: 1em; text-align: center; }
.ed-comp__title { font-weight: 600; color: var(--ink-1); }
.ed-comp__count { margin-left: auto; font-family: var(--font-mono); font-size: var(--text-xs); color: var(--ink-3); }
.ed-comp__tasks { list-style: none; margin: 0; padding: 4px 0; }
.ed-task__link { display: flex; align-items: center; gap: 8px; padding: 5px 12px; text-decoration: none; color: var(--ink-1); }
.ed-task__link:hover { background: var(--bg-card-hover); }
.ed-task__st { width: 8px; height: 8px; border-radius: 50%; background: var(--ink-3); }
.ed-task__st--done { background: var(--green, #5fcdb8); }
.ed-task__st--in-progress { background: var(--amber, #e8a34d); }
.ed-task__st--blocked { background: var(--red, #e87a85); }
.ed-task__id { font-family: var(--font-mono); font-size: var(--text-xs); color: var(--ink-2); }
.ed-side-block { margin-bottom: 18px; }
.ed-attn, .ed-docs { list-style: none; margin: 0; padding: 0; font-size: var(--text-sm); }
.ed-attn li, .ed-docs li { margin-bottom: 6px; color: var(--ink-2); }
.ed-attn a, .ed-docs a { color: var(--accent); text-decoration: none; }
```

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/epic-detail-document.js plugins/taskmaster/viewer/css/screens/epic-detail.css
git commit -m "feat(taskmaster): epic detail components/attention/docs sections (C1b)"
```

---

### Task 9: `/epic/<id>` route screen + e2e

**Files:**
- Create: `plugins/taskmaster/viewer/js/screens/epic-detail.js`
- Test: `plugins/taskmaster/viewer/tests/epic-detail.spec.js` (new Playwright spec)

- [ ] **Step 1: Write the failing e2e test**

```javascript
// plugins/taskmaster/viewer/tests/epic-detail.spec.js
import { test, expect } from '@playwright/test';

test.describe('Epic detail', () => {
  test('route #/epic resolves with page-title Epic', async ({ page }) => {
    const errors = [];
    page.on('pageerror', e => errors.push(String(e)));
    await page.goto('/v3');
    await page.evaluate(() => location.hash = '#/epic/__none__');
    await expect(page.locator('#page-title')).toHaveText('Epic');
    expect(errors).toEqual([]);
  });

  test('unknown epic id shows a not-found state with a back link', async ({ page }) => {
    await page.goto('/v3');
    await page.evaluate(() => location.hash = '#/epic/__definitely_missing__');
    await expect(page.locator('.ed-empty')).toContainText('not found');
    await expect(page.locator('.ed-empty a[href="#/epics"]')).toBeVisible();
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `bash plugins/taskmaster/viewer/tests/run_smoke.sh` (or targeted `npx playwright test epic-detail.spec.js`).
Expected: FAIL — `#/epic` unregistered route → no page-title "Epic", no `.ed-empty`.

- [ ] **Step 3: Implement the route screen**

```javascript
// plugins/taskmaster/viewer/js/screens/epic-detail.js
import { getEpic } from '../api.js';
import { claimTopbar } from '../lib/topbar.js';
import { mountEpicDetail } from '../components/epic-detail-document.js';

export const meta = { title: 'Epic', icon: '⬡', sidebarKey: 'epics' };

function esc(s) {
  return String(s == null ? '' : s)
    .replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}

export async function mount(root, { subpath, params, store, prefs }) {
  const id = subpath?.[0] || params?.id || null;
  root.innerHTML = '';
  claimTopbar();
  const cleanup = () => { root.replaceChildren(); };

  if (!id) {
    root.innerHTML = `<div class="ed-empty">No epic selected. <a href="#/epics">Back to Epics</a>.</div>`;
    return cleanup;
  }
  if (prefs?.patch) prefs.patch({ ui: { last_epic_id: id } });

  let epic;
  try {
    epic = await getEpic(id);
  } catch (e) {
    root.innerHTML = `<div class="ed-empty">Epic <code>${esc(id)}</code> not found. `
      + `<a href="#/epics">Back to Epics</a>.</div>`;
    return cleanup;
  }

  const dispose = mountEpicDetail(root, {
    epic, store,
    onNavigate: (tid) => { location.hash = `#/task/${encodeURIComponent(tid)}`; },
    chrome: 'page',
  });
  return () => { dispose(); cleanup(); };
}
```

- [ ] **Step 4: Run the e2e to verify it passes**

Run: `bash plugins/taskmaster/viewer/tests/run_smoke.sh`
Expected: PASS (page-title "Epic"; unknown id shows `.ed-empty` with the back link).

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/viewer/js/screens/epic-detail.js plugins/taskmaster/viewer/tests/epic-detail.spec.js
git commit -m "feat(taskmaster): /epic/<id> detail screen + e2e (C1b)"
```

---

## Phase 5 — Release

### Task 10: Version bump (plugin protocol)

**Files:**
- Modify: `plugins/taskmaster/.claude-plugin/plugin.json` (`version`)
- Modify: `.claude-plugin/marketplace.json` (taskmaster `version` — must equal plugin.json)
- Modify: `plugins/taskmaster/CHANGELOG.md` (new section)

C1b adds an HTTP endpoint + viewer surface (additive) → **minor** bump per SemVer rules in `CLAUDE.md`.

- [ ] **Step 1: Read current version**

Run: `python -c "import json; print(json.load(open('plugins/taskmaster/.claude-plugin/plugin.json'))['version'])"`
Note the value `X.Y.Z`; the new version is `X.(Y+1).0`.

- [ ] **Step 2: Bump all three parts**

- `plugin.json`: set `"version": "X.(Y+1).0"`.
- `marketplace.json`: set taskmaster's `version` to the same.
- `CHANGELOG.md`: add a `## X.(Y+1).0` section:
  ```
  ## X.(Y+1).0
  - feat(viewer): epic detail surface — GET /api/epic/<id> (load_v3-backed),
    mountEpicDetail component (rollup + components + design-lock + narrative),
    /epic/<id> detail screen, /epics list, sidebar Epics entry. (Spec C1b)
  ```

- [ ] **Step 3: Run the version-bump check**

Run: `python scripts/check_plugin_version_bump.py --base origin/master`
Expected: exit 0 (plugin.json/marketplace.json in sync; changed plugin bumped; CHANGELOG entry present).

- [ ] **Step 4: Full suite + commit**

```bash
python -m pytest plugins/taskmaster/tests/ -q
git add plugins/taskmaster/.claude-plugin/plugin.json .claude-plugin/marketplace.json plugins/taskmaster/CHANGELOG.md
git commit -m "chore(taskmaster): bump version for C1b epic viewer surface"
```

---

## Self-Review

**Spec coverage** (against `2026-05-27-task-epic-protocol-design.md` Viewer surface + `2026-05-28-entity-detail-modals-design.md` dependency):
- "Epic detail screen: component list, progress rollup, risk/attention list, design_status lock badge, design narrative/docs" → Tasks 7–8 (`mountEpicDetail`) + Task 9 (screen). Diagram explicitly deferred to C2 (named extension point in Task 8).
- "C1b must read heavy fields via a `load_v3`-backed path, NOT raw `/api/backlog`" (the C1a handover's seam warning) → Tasks 1–2 (`_load_epic_full` → `_load()` → `_load_v3`; verified by `test_load_epic_full_merges_heavy_fields_and_rollup`).
- "front door" → `/epics` list (Task 6) + sidebar entry (Task 5).
- Modal-feature dependency: `mountEpicDetail` authored embedded-aware (`chrome`/`actionsHost`, never claims topbar) → Task 7, satisfying the entity-detail-modals spec-review requirement.

**Placeholder scan:** none. Every code step shows the full insertion with exact anchors; the one forward-reference (`mountEpicDetail._fillBody?.(…)` in Task 7) is a *real, runnable* call site that Task 8 replaces inline — not a dead stub.

**Type consistency:** `_load_epic_full` returns `{id,name,status,design_status,description,docs,components,stats,component_rollup,attention,tasks}`; `mountEpicDetail` reads exactly those keys (`epic.stats`, `epic.component_rollup`, `epic.attention`, `epic.tasks`, `epic.description`, `epic._body`, `epic.docs`, `epic.components`). `epic-format.js` exports (`designBadge`,`componentGlyph`,`progressPercent`,`tasksForComponent`) match every call site in Tasks 6–8. `getEpic` (Task 4) is the single client used by both the screen (Task 9) and — later — the modal.

**Known follow-ups (named, not silent):** C2 diagram (extension point in Task 8); the modal/settings feature (separate plan, reuses `mountEpicDetail` + `getEpic`); the stale `smoke.spec.js` sidebar count (out of scope, noted).
