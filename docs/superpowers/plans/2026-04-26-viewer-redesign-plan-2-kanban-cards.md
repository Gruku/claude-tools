# Taskmaster Viewer Redesign — Plan 2: Kanban + Cards

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Kanban screen end-to-end — header (search + priority chips + group/sort/+task), phase stepper, epic chips, board surface with five status columns (or grouped by phase/epic), Minimal & Full cards (Variant E per-epic color), per-card auto-mode live block, top-of-page auto-mode strip, and the read-only `/api/auto/state` endpoint that feeds it. Filter and view state persists to `viewer.kanban.*` per Plan 1 conventions.

**Architecture:** A single screen module (`js/screens/kanban.js`) owns the page, with shared rendering split into pure-function components under `js/components/`. CSS is a single screen file (`css/screens/kanban.css`) plus tiny additions to existing files only where genuinely shared. The auto-mode panel is a thin HTTP read of `.taskmaster/auto/state.json`; mutating endpoints are scope of Plan 6.

**Tech Stack:** Vanilla HTML/CSS/JS modules, Python 3 + `BaseHTTPRequestHandler` (extending Plan 1's `_make_server` + `_send_json`), pytest with the `running_server` fixture from Plan 1, Playwright for screen smoke, Node's built-in `node --test` for pure-logic unit tests.

**Spec reference:** `docs/superpowers/specs/2026-04-26-taskmaster-viewer-redesign.md` §3.3 (auto-mode display), §3.5 (kanban screen), §3.6 (cards), §3.7 (per-epic Variant E), §3.8 (card additions/drops). Mockups under `.superpowers/brainstorm/15283-1777223061/content/`: `kanban-filters-v2.html`, `card-views.html`, `full-card-polish.html`, `card-experiments.html`, `auto-mode-on-kanban.html`, `auto-mode-merged.html`, `auto-mode-motion.html`, `auto-mode-spinner.html`.

**Architectural Conventions:** Inherited from Plan 1 §"Architectural Conventions (locked for Plans 2–6)". Not redefined here. In particular: ES modules with relative imports, screen module shape (`mount(root, deps)` + `meta`), CSS class prefixes (`.kanban-*` for screen-local, `.cmp-*` for shared, `.card-*` for the shared card component), state via `store.js`, mutations via `api.js`, prefs via debounced `prefs.patch({...})`, hash routing, atomic JSON writes, pytest with `tmp_path`, Playwright smoke (no visual regression).

---

## File Structure

**Created in this plan:**

```
plugins/taskmaster/viewer/
├── css/
│   └── screens/
│       └── kanban.css                      # Kanban-only styles + per-epic color tokens
├── js/
│   ├── components/
│   │   ├── card.js                         # Shared task card (Minimal + Full densities)
│   │   ├── auto-mode-strip.js              # Light header strip (live dot + per-run pcts)
│   │   ├── auto-mode-live-block.js         # Per-card live block (pulse + step + bar + elapsed)
│   │   ├── phase-stepper.js                # All-phases + per-phase progress cells, click filter
│   │   ├── epic-chips.js                   # Inline epic chip row, click toggle, count + clear-all
│   │   └── priority-chips.js               # Critical/High/Medium/Low toggle chips
│   ├── lib/
│   │   ├── filters.js                      # Pure filter/sort/group helpers (testable in node)
│   │   ├── time.js                         # time-in-status / elapsed formatters
│   │   ├── epics.js                        # Epic palette + auto-assignment
│   │   └── copy.js                         # click-to-copy with green-flash UX
│   └── screens/
│       └── kanban.js                       # (replaces stub) full kanban screen
└── tests/
    ├── kanban.spec.js                      # Playwright smoke for kanban
    └── unit/
        ├── filters.test.js                 # node --test
        ├── time.test.js                    # node --test
        └── epics.test.js                   # node --test
plugins/taskmaster/tests/
└── test_server_auto_state.py               # /api/auto/state HTTP tests
```

**Modified in this plan:**

- `plugins/taskmaster/backlog_server.py` — add `GET /api/auto/state` route + `_load_auto_state()` helper
- `plugins/taskmaster/viewer/index.html` — `<link>` line for `css/screens/kanban.css`
- `plugins/taskmaster/viewer/css/components.css` — minor: add `.cmp-flash-copied` + `.cmp-icon-btn` (used by card click-to-copy and footer icons)

**Untouched in this plan:** all other screen stubs, Plan 1 server endpoints, dashboard widgets.

---

## Milestones

- **M1 — Auto-mode HTTP read** (Tasks 1–4): `_load_auto_state` + `GET /api/auto/state` + `api.autoState()` + store wiring + 3-second poll
- **M2 — Pure-logic libraries** (Tasks 5–8): `lib/time.js`, `lib/filters.js`, `lib/epics.js`, `lib/copy.js` with node-test coverage
- **M3 — Card component** (Tasks 9–13): Minimal card, Full card, Variant E styling, click-to-copy, recently-moved highlight
- **M4 — Auto-mode UI components** (Tasks 14–16): live block under cards, header strip with conic spinner, motion (pulse + shimmer)
- **M5 — Kanban controls** (Tasks 17–22): priority chips, phase stepper, epic chips, group-by, sort dropdown, search, +Task button stub
- **M6 — Kanban screen integration** (Tasks 23–28): screen module, layout, board surface, status / phase / epic groupings, prefs round-trip
- **M7 — Tests + polish** (Tasks 29–33): Playwright smoke, console-error guard, integration smoke, plan-level verification + commit

---

## M1 — Auto-mode HTTP Read

### Task 1: Helper to load `.taskmaster/auto/state.json`

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py` (add helper near other loaders)
- Create: `plugins/taskmaster/tests/test_server_auto_state.py`

- [x] **Step 1: Write the failing test**

Create `plugins/taskmaster/tests/test_server_auto_state.py`:

```python
"""Tests for /api/auto/state read-only endpoint and helper."""
import json
import threading
import time
import urllib.request
import urllib.error
import pytest


@pytest.fixture
def running_server(tmp_path, monkeypatch):
    """Spin up backlog_server on an ephemeral port — same shape as Plan 1's fixture."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".taskmaster").mkdir()
    (tmp_path / "backlog.yaml").write_text(
        "meta:\n  project: test\nepics: []\nphases: []\n"
    )

    from backlog_server import _make_server
    server, port = _make_server(host="127.0.0.1", port=0)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    base = f"http://127.0.0.1:{port}"
    for _ in range(20):
        try:
            urllib.request.urlopen(f"{base}/api/identity", timeout=0.5).read()
            break
        except Exception:
            time.sleep(0.05)
    yield base, server
    server.shutdown()
    server.server_close()


def test_load_auto_state_returns_none_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".taskmaster").mkdir()
    from backlog_server import _load_auto_state
    assert _load_auto_state() is None


def test_load_auto_state_returns_parsed_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    auto_dir = tmp_path / ".taskmaster" / "auto"
    auto_dir.mkdir(parents=True)
    payload = {
        "mode": "running",
        "target": "v3-009",
        "started_at": "2026-04-26T10:00:00Z",
        "cursor": {"task_id": "v3-009", "stage": "IMPLEMENT", "model": "sonnet"},
        "completed": [],
        "pending": ["v3-011", "v3-012"],
        "failed": [],
        "models": {},
        "config": {},
    }
    (auto_dir / "state.json").write_text(json.dumps(payload))
    from backlog_server import _load_auto_state
    got = _load_auto_state()
    assert got["mode"] == "running"
    assert got["cursor"]["stage"] == "IMPLEMENT"
    assert got["pending"] == ["v3-011", "v3-012"]


def test_load_auto_state_returns_none_on_corrupt_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    auto_dir = tmp_path / ".taskmaster" / "auto"
    auto_dir.mkdir(parents=True)
    (auto_dir / "state.json").write_text("{ this is not json")
    from backlog_server import _load_auto_state
    assert _load_auto_state() is None
```

- [x] **Step 2: Run tests to verify they fail**

Run: `python -m pytest plugins/taskmaster/tests/test_server_auto_state.py -v -k load_auto_state`
Expected: FAIL with `ImportError: cannot import name '_load_auto_state'`

- [x] **Step 3: Implement `_load_auto_state` in `backlog_server.py`**

Add near other v3 loader helpers (e.g., right after `load_viewer_prefs` re-export or near the imports of other loaders):

```python
def _load_auto_state():
    """Read .taskmaster/auto/state.json, return parsed dict or None.

    Returns None when the file is missing OR contains invalid JSON.
    Used by GET /api/auto/state. Mutating writes are out of scope for Plan 2.
    """
    import json
    from pathlib import Path
    p = Path(".taskmaster") / "auto" / "state.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
```

- [x] **Step 4: Run tests to verify they pass**

Run: `python -m pytest plugins/taskmaster/tests/test_server_auto_state.py -v -k load_auto_state`
Expected: 3 PASS.

- [x] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_server_auto_state.py
git commit -m "feat(taskmaster): _load_auto_state helper for .taskmaster/auto/state.json"
```

---

### Task 2: HTTP endpoint `GET /api/auto/state`

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py` (add route in `_Handler.do_GET`)
- Modify: `plugins/taskmaster/tests/test_server_auto_state.py`

- [x] **Step 1: Write the failing test**

Append to `plugins/taskmaster/tests/test_server_auto_state.py`:

```python
def test_get_auto_state_returns_null_body_when_file_missing(running_server):
    base, _ = running_server
    resp = urllib.request.urlopen(f"{base}/api/auto/state")
    assert resp.status == 200
    assert resp.headers.get("Content-Type", "").startswith("application/json")
    assert resp.headers.get("Access-Control-Allow-Origin") == "*"
    body = json.loads(resp.read())
    assert body == {"state": None}


def test_get_auto_state_returns_state_object(running_server, tmp_path):
    base, _ = running_server
    auto_dir = tmp_path / ".taskmaster" / "auto"
    auto_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "mode": "running",
        "target": "v3-009",
        "started_at": "2026-04-26T10:00:00Z",
        "cursor": {"task_id": "v3-009", "stage": "IMPLEMENT", "model": "sonnet"},
        "completed": ["v3-008"],
        "pending": ["v3-011"],
        "failed": [],
        "models": {"sonnet": 1},
        "config": {},
    }
    (auto_dir / "state.json").write_text(json.dumps(payload))
    resp = urllib.request.urlopen(f"{base}/api/auto/state")
    body = json.loads(resp.read())
    assert body["state"]["mode"] == "running"
    assert body["state"]["cursor"]["stage"] == "IMPLEMENT"
```

- [x] **Step 2: Run tests to verify they fail**

Run: `python -m pytest plugins/taskmaster/tests/test_server_auto_state.py -v -k get_auto_state`
Expected: FAIL — 404 from `/api/auto/state`.

- [x] **Step 3: Implement the route**

In `plugins/taskmaster/backlog_server.py`, inside `_Handler.do_GET`, add **before** the existing `/api/viewer/prefs` block (so route ordering stays predictable; the Plan 1 file orders specific paths first):

```python
if self.path == "/api/auto/state":
    self._send_json(200, {"state": _load_auto_state()})
    return
```

- [x] **Step 4: Run tests to verify they pass**

Run: `python -m pytest plugins/taskmaster/tests/test_server_auto_state.py -v`
Expected: 5 PASS (3 helper + 2 endpoint).

- [x] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_server_auto_state.py
git commit -m "feat(taskmaster): GET /api/auto/state read-only endpoint"
```

---

### Task 3: Add `api.autoState()` and store wiring

**Files:**
- Modify: `plugins/taskmaster/viewer/js/api.js`

- [x] **Step 1: Add `autoState` to the `api` object**

Open `plugins/taskmaster/viewer/js/api.js`. Replace the entire `export const api = { ... };` block with:

```js
export const api = {
  identity:        ()    => http('GET', '/api/identity'),
  backlog:         ()    => http('GET', '/api/backlog'),
  backlogYaml:     ()    => http('GET', '/backlog.yaml'),
  prefs:           ()    => http('GET', '/api/viewer/prefs'),
  savePrefs:       (p)   => http('PUT', '/api/viewer/prefs', p),
  autoState:       ()    => http('GET', '/api/auto/state').then(r => r && r.state),
  // Plans 5/6 add: reinforceLesson, getRecap, putRecap, putAutoState, etc.
};
```

The store key `autoState` already exists in Plan 1's `store.js` (`getAutoState` / `setAutoState`). No store edit needed.

- [x] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/api.js
git commit -m "feat(viewer): api.autoState() reads /api/auto/state"
```

---

### Task 4: Poll auto-mode state from `main.js`

**Files:**
- Modify: `plugins/taskmaster/viewer/js/main.js`

- [x] **Step 1: Add an auto-state poll loop**

Open `plugins/taskmaster/viewer/js/main.js`. Find the line `pollBacklogForever();` near the end of `boot()`. Replace that single line with:

```js
  pollBacklogForever();
  pollAutoStateForever();
```

Then directly **above** the line `const sleep = ms => new Promise(r => setTimeout(r, ms));`, insert this new function:

```js
const AUTO_STATE_POLL_MS = 3000;

async function pollAutoStateForever() {
  while (true) {
    try {
      const auto = await api.autoState();
      store.setAutoState(auto);
    } catch (e) {
      console.error('auto state poll failed', e);
      store.setAutoState(null);
    }
    await sleep(AUTO_STATE_POLL_MS);
  }
}
```

- [x] **Step 2: Manual smoke**

Run from `plugins/taskmaster/`:

```bash
python -c "from backlog_server import _make_server; s, p = _make_server(host='127.0.0.1', port=0); print(f'http://127.0.0.1:{p}/v3'); s.serve_forever()"
```

Open the printed URL in a browser. In DevTools Network tab, confirm a `GET /api/auto/state` request fires every ~3s. Body is `{"state": null}` until you create `.taskmaster/auto/state.json`.

Expected: no console errors.

- [x] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/js/main.js
git commit -m "feat(viewer): poll /api/auto/state every 3s into store"
```

---

## M2 — Pure-Logic Libraries

### Task 5: `lib/time.js` (time-in-status + elapsed formatters)

**Files:**
- Create: `plugins/taskmaster/viewer/js/lib/time.js`
- Create: `plugins/taskmaster/viewer/tests/unit/time.test.js`

- [ ] **Step 1: Write the failing test**

Create `plugins/taskmaster/viewer/tests/unit/time.test.js`:

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { formatTimeInStatus, formatElapsed, classifyTimeInStatus, isoToMs } from '../../js/lib/time.js';

test('formatTimeInStatus — under an hour returns minutes', () => {
  const now = Date.parse('2026-04-26T12:00:00Z');
  const ts  = Date.parse('2026-04-26T11:30:00Z');
  assert.equal(formatTimeInStatus(ts, now), '30m');
});

test('formatTimeInStatus — under a day returns hours', () => {
  const now = Date.parse('2026-04-26T12:00:00Z');
  const ts  = Date.parse('2026-04-26T05:00:00Z');
  assert.equal(formatTimeInStatus(ts, now), '7h');
});

test('formatTimeInStatus — multi-day returns Nd', () => {
  const now = Date.parse('2026-04-26T12:00:00Z');
  const ts  = Date.parse('2026-04-24T12:00:00Z');
  assert.equal(formatTimeInStatus(ts, now), '2d');
});

test('formatTimeInStatus — null/undefined input returns empty string', () => {
  assert.equal(formatTimeInStatus(null), '');
  assert.equal(formatTimeInStatus(undefined), '');
});

test('classifyTimeInStatus — fresh / aging / stale per spec', () => {
  const now = Date.parse('2026-04-26T12:00:00Z');
  assert.equal(classifyTimeInStatus(Date.parse('2026-04-26T11:30:00Z'), now), 'fresh');
  assert.equal(classifyTimeInStatus(Date.parse('2026-04-25T12:00:00Z'), now), 'fresh');  // 1d
  assert.equal(classifyTimeInStatus(Date.parse('2026-04-24T12:00:00Z'), now), 'fresh');  // 2d
  assert.equal(classifyTimeInStatus(Date.parse('2026-04-22T12:00:00Z'), now), 'stale');  // 4d (>=4d turns amber per spec §3.8)
  assert.equal(classifyTimeInStatus(Date.parse('2026-04-20T12:00:00Z'), now), 'stale');  // 6d
});

test('formatElapsed — HH:MM:SS for >= 1 hour, else MM:SS', () => {
  assert.equal(formatElapsed(0),         '00:00');
  assert.equal(formatElapsed(45_000),    '00:45');
  assert.equal(formatElapsed(90_000),    '01:30');
  assert.equal(formatElapsed(3_600_000), '01:00:00');
  assert.equal(formatElapsed(6_125_000), '01:42:05');
});

test('isoToMs — parses ISO8601 string, returns null for falsy', () => {
  assert.equal(isoToMs('2026-04-26T10:00:00Z'), Date.parse('2026-04-26T10:00:00Z'));
  assert.equal(isoToMs(null),       null);
  assert.equal(isoToMs(undefined),  null);
  assert.equal(isoToMs(''),         null);
});
```

- [ ] **Step 2: Run test (it should fail with ENOENT for the lib file)**

Run: `node --test plugins/taskmaster/viewer/tests/unit/time.test.js`
Expected: FAIL — `Cannot find module '.../js/lib/time.js'`.

- [ ] **Step 3: Implement `lib/time.js`**

Create `plugins/taskmaster/viewer/js/lib/time.js`:

```js
// Pure-logic time helpers. No DOM. Imported by browser AND node tests.

const MIN_MS  = 60 * 1000;
const HOUR_MS = 60 * MIN_MS;
const DAY_MS  = 24 * HOUR_MS;

/** Parse an ISO8601 timestamp to ms; null/undefined/empty → null. */
export function isoToMs(iso) {
  if (!iso) return null;
  const t = Date.parse(iso);
  return Number.isFinite(t) ? t : null;
}

/** Compact time-in-status: "30m" / "7h" / "2d". Returns '' for null/undefined. */
export function formatTimeInStatus(tsMs, nowMs = Date.now()) {
  if (tsMs == null) return '';
  const delta = Math.max(0, nowMs - tsMs);
  if (delta < HOUR_MS) return Math.floor(delta / MIN_MS) + 'm';
  if (delta < DAY_MS)  return Math.floor(delta / HOUR_MS) + 'h';
  return Math.floor(delta / DAY_MS) + 'd';
}

/** Per spec §3.8: fresh < 4d, stale >= 4d. Future tier "aging" is reserved. */
export function classifyTimeInStatus(tsMs, nowMs = Date.now()) {
  if (tsMs == null) return 'fresh';
  const days = (nowMs - tsMs) / DAY_MS;
  if (days >= 4) return 'stale';
  return 'fresh';
}

/** "MM:SS" or "HH:MM:SS" for elapsed-since strings on auto-mode runs. */
export function formatElapsed(ms) {
  if (ms == null || !Number.isFinite(ms) || ms < 0) ms = 0;
  const total = Math.floor(ms / 1000);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const pad = n => String(n).padStart(2, '0');
  if (h > 0) return `${pad(h)}:${pad(m)}:${pad(s)}`;
  return `${pad(m)}:${pad(s)}`;
}
```

- [ ] **Step 4: Run test to verify pass**

Run: `node --test plugins/taskmaster/viewer/tests/unit/time.test.js`
Expected: All pass — `# pass 7`.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/viewer/js/lib/time.js plugins/taskmaster/viewer/tests/unit/time.test.js
git commit -m "feat(viewer): lib/time.js with formatters and tests"
```

---

### Task 6: `lib/epics.js` (epic palette + auto-assignment)

**Files:**
- Create: `plugins/taskmaster/viewer/js/lib/epics.js`
- Create: `plugins/taskmaster/viewer/tests/unit/epics.test.js`

- [ ] **Step 1: Write the failing test**

Create `plugins/taskmaster/viewer/tests/unit/epics.test.js`:

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { EPIC_PALETTE, assignEpicColors, epicColor, epicCssVar } from '../../js/lib/epics.js';

test('EPIC_PALETTE is the locked spec §5 palette', () => {
  assert.deepEqual(EPIC_PALETTE, [
    '#6ea8ff', '#b585e8', '#5fcdb8', '#e8a34d', '#e87a85', '#a8c958',
  ]);
});

test('assignEpicColors — auto-assigns palette in order, wraps after 6', () => {
  const epics = [
    { id: 'viewer-redesign', name: 'viewer-redesign' },
    { id: 'narrative-continuity', name: 'narrative-continuity' },
    { id: 'filter-bar', name: 'filter-bar' },
    { id: 'migration-tooling', name: 'migration-tooling' },
    { id: 'blast-radius', name: 'blast-radius' },
    { id: 'spec-review', name: 'spec-review' },
    { id: 'extra-7', name: 'extra-7' },
  ];
  const map = assignEpicColors(epics);
  assert.equal(map['viewer-redesign'], '#6ea8ff');
  assert.equal(map['narrative-continuity'], '#b585e8');
  assert.equal(map['spec-review'],     '#a8c958');
  assert.equal(map['extra-7'],         '#6ea8ff'); // wraps
});

test('assignEpicColors — respects explicit color on epic record', () => {
  const epics = [
    { id: 'a', color: '#abcdef' },
    { id: 'b', name: 'b' },
  ];
  const map = assignEpicColors(epics);
  assert.equal(map['a'], '#abcdef');
  assert.equal(map['b'], '#6ea8ff');
});

test('epicColor — returns assigned color or fallback ink-3', () => {
  const map = { foo: '#6ea8ff' };
  assert.equal(epicColor('foo', map), '#6ea8ff');
  assert.equal(epicColor('missing', map), '#7c8290');
  assert.equal(epicColor(null, map), '#7c8290');
});

test('epicCssVar — returns inline style with --epic and --epic-soft', () => {
  const style = epicCssVar('#6ea8ff');
  assert.match(style, /--epic:\s*#6ea8ff/);
  assert.match(style, /--epic-soft:\s*rgba\(110, ?168, ?255, ?0\.14\)/);
});

test('epicCssVar — null color falls back to ink-3', () => {
  const style = epicCssVar(null);
  assert.match(style, /--epic:\s*#7c8290/);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test plugins/taskmaster/viewer/tests/unit/epics.test.js`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `lib/epics.js`**

Create `plugins/taskmaster/viewer/js/lib/epics.js`:

```js
// Epic color palette — spec §5. Auto-assigned in declaration order
// unless the epic record carries an explicit `color` field.

export const EPIC_PALETTE = [
  '#6ea8ff', // viewer-redesign (blue)
  '#b585e8', // narrative-continuity (purple)
  '#5fcdb8', // filter-bar (teal)
  '#e8a34d', // migration-tooling (amber)
  '#e87a85', // blast-radius (coral)
  '#a8c958', // spec-review (lime)
];

const FALLBACK = '#7c8290'; // var(--ink-3)

/** Build {epicId → hexColor} for the epic list. */
export function assignEpicColors(epics) {
  const map = {};
  if (!Array.isArray(epics)) return map;
  let idx = 0;
  for (const ep of epics) {
    if (!ep || !ep.id) continue;
    if (ep.color) {
      map[ep.id] = ep.color;
    } else {
      map[ep.id] = EPIC_PALETTE[idx % EPIC_PALETTE.length];
      idx += 1;
    }
  }
  return map;
}

export function epicColor(epicId, colorMap) {
  if (!epicId) return FALLBACK;
  return (colorMap && colorMap[epicId]) || FALLBACK;
}

/** Inline style string defining --epic and --epic-soft (14% alpha tint). */
export function epicCssVar(hex) {
  const c = hex || FALLBACK;
  // Parse #rrggbb to "r, g, b" for rgba().
  const m = /^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(c);
  let rgbStr = '124, 130, 144';
  if (m) {
    rgbStr = `${parseInt(m[1], 16)}, ${parseInt(m[2], 16)}, ${parseInt(m[3], 16)}`;
  }
  return `--epic: ${c}; --epic-soft: rgba(${rgbStr}, 0.14)`;
}
```

- [ ] **Step 4: Run test to verify pass**

Run: `node --test plugins/taskmaster/viewer/tests/unit/epics.test.js`
Expected: 6 pass.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/viewer/js/lib/epics.js plugins/taskmaster/viewer/tests/unit/epics.test.js
git commit -m "feat(viewer): lib/epics.js palette + auto-assignment"
```

---

### Task 7: `lib/filters.js` (apply filters + sort + group)

**Files:**
- Create: `plugins/taskmaster/viewer/js/lib/filters.js`
- Create: `plugins/taskmaster/viewer/tests/unit/filters.test.js`

- [ ] **Step 1: Write the failing test**

Create `plugins/taskmaster/viewer/tests/unit/filters.test.js`:

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { applyFilters, sortTasks, groupTasks, STATUS_ORDER } from '../../js/lib/filters.js';

const TASKS = [
  { id: 'v3-001', title: 'A',          status: 'done',        priority: 'low',      estimate: 'S', phase: 'P-01', epic: 'viewer-redesign',     started: '2026-04-25T10:00:00Z' },
  { id: 'v3-002', title: 'B',          status: 'in_progress', priority: 'critical', estimate: 'L', phase: 'P-03', epic: 'viewer-redesign',     started: '2026-04-26T10:00:00Z' },
  { id: 'v3-003', title: 'Auth thing', status: 'todo',        priority: 'high',     estimate: 'M', phase: 'P-03', epic: 'narrative-continuity',started: null },
  { id: 'v3-004', title: 'Other',      status: 'blocked',     priority: 'medium',   estimate: 'S', phase: null,   epic: null,                  started: null },
];

test('applyFilters — empty filters returns all tasks', () => {
  const out = applyFilters(TASKS, {});
  assert.equal(out.length, 4);
});

test('applyFilters — by priorities (multi)', () => {
  const out = applyFilters(TASKS, { priorities: ['critical', 'high'] });
  assert.deepEqual(out.map(t => t.id), ['v3-002', 'v3-003']);
});

test('applyFilters — by epics (multi, no-epic only matches when "" included)', () => {
  const out = applyFilters(TASKS, { epics: ['viewer-redesign'] });
  assert.deepEqual(out.map(t => t.id), ['v3-001', 'v3-002']);
});

test('applyFilters — by phase (single)', () => {
  const out = applyFilters(TASKS, { phase: 'P-03' });
  assert.deepEqual(out.map(t => t.id), ['v3-002', 'v3-003']);
});

test('applyFilters — phase: orphans selects null/undefined phase', () => {
  const out = applyFilters(TASKS, { phase: '__orphans__' });
  assert.deepEqual(out.map(t => t.id), ['v3-004']);
});

test('applyFilters — search matches id, title, branch (case-insensitive)', () => {
  const out = applyFilters(TASKS, { search: 'auth' });
  assert.deepEqual(out.map(t => t.id), ['v3-003']);
  const out2 = applyFilters(TASKS, { search: 'V3-002' });
  assert.deepEqual(out2.map(t => t.id), ['v3-002']);
});

test('sortTasks — priority desc puts critical first', () => {
  const out = sortTasks(TASKS, { by: 'priority', dir: 'desc' });
  assert.equal(out[0].id, 'v3-002');
  assert.equal(out[3].id, 'v3-001');
});

test('sortTasks — size asc returns S/M/L order', () => {
  const out = sortTasks(TASKS, { by: 'size', dir: 'asc' });
  assert.equal(out[0].estimate, 'S');
  assert.equal(out[out.length - 1].estimate, 'L');
});

test('sortTasks — started desc puts most recent first; null last', () => {
  const out = sortTasks(TASKS, { by: 'started', dir: 'desc' });
  assert.equal(out[0].id, 'v3-002');                 // most recent start
  assert.equal(out[out.length - 1].started, null);   // nulls sorted last
});

test('groupTasks — by status uses STATUS_ORDER', () => {
  const groups = groupTasks(TASKS, 'status');
  assert.deepEqual(groups.map(g => g.key), STATUS_ORDER);
  const inProg = groups.find(g => g.key === 'in_progress');
  assert.deepEqual(inProg.tasks.map(t => t.id), ['v3-002']);
});

test('groupTasks — by epic with __none__ bucket for missing epic', () => {
  const groups = groupTasks(TASKS, 'epic');
  const ids = groups.map(g => g.key);
  assert.ok(ids.includes('__none__'));
  const none = groups.find(g => g.key === '__none__');
  assert.deepEqual(none.tasks.map(t => t.id), ['v3-004']);
});

test('groupTasks — by phase keeps phase order from input list', () => {
  const groups = groupTasks(TASKS, 'phase', ['P-01', 'P-02', 'P-03']);
  assert.deepEqual(groups.map(g => g.key), ['P-01', 'P-02', 'P-03', '__orphans__']);
});
```

- [ ] **Step 2: Run test (fails)**

Run: `node --test plugins/taskmaster/viewer/tests/unit/filters.test.js`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `lib/filters.js`**

Create `plugins/taskmaster/viewer/js/lib/filters.js`:

```js
// Pure-logic filter / sort / group for the kanban board.
// No DOM. Tested via node --test.

export const STATUS_ORDER = ['blocked', 'todo', 'in_progress', 'in_review', 'done'];

const PRIORITY_RANK = { critical: 4, high: 3, medium: 2, low: 1 };
const SIZE_RANK     = { XS: 1, S: 2, M: 3, L: 4, XL: 5 };

export function applyFilters(tasks, f) {
  if (!Array.isArray(tasks)) return [];
  f = f || {};
  const pri    = Array.isArray(f.priorities) ? f.priorities : [];
  const epics  = Array.isArray(f.epics) ? f.epics : [];
  const phase  = f.phase || null;
  const search = (f.search || '').trim().toLowerCase();

  return tasks.filter(t => {
    if (pri.length && !pri.includes(String(t.priority || '').toLowerCase())) return false;
    if (epics.length && !epics.includes(t.epic || '__none__')) return false;
    if (phase) {
      if (phase === '__orphans__') {
        if (t.phase) return false;
      } else if (t.phase !== phase) {
        return false;
      }
    }
    if (search) {
      const hay = [t.id, t.title, t.branch].filter(Boolean).join(' ').toLowerCase();
      if (!hay.includes(search)) return false;
    }
    return true;
  });
}

export function sortTasks(tasks, sort) {
  const arr = (tasks || []).slice();
  const by  = sort?.by  || 'priority';
  const dir = sort?.dir === 'asc' ? 1 : -1;

  const cmpStr = (a, b) => (a < b ? -1 : a > b ? 1 : 0);

  arr.sort((a, b) => {
    let av, bv;
    switch (by) {
      case 'priority':
        av = PRIORITY_RANK[String(a.priority || '').toLowerCase()] || 0;
        bv = PRIORITY_RANK[String(b.priority || '').toLowerCase()] || 0;
        return (av - bv) * dir;
      case 'size':
        av = SIZE_RANK[String(a.estimate || '').toUpperCase()] || 0;
        bv = SIZE_RANK[String(b.estimate || '').toUpperCase()] || 0;
        return (av - bv) * dir;
      case 'created':
      case 'started':
      case 'completed':
      case 'touched': {
        const field = by === 'touched' ? 'started' : by;
        av = a[field] ? Date.parse(a[field]) : null;
        bv = b[field] ? Date.parse(b[field]) : null;
        if (av == null && bv == null) return 0;
        if (av == null) return 1;        // nulls always last
        if (bv == null) return -1;
        return (av - bv) * dir;
      }
      default:
        return cmpStr(a.id, b.id) * dir;
    }
  });
  return arr;
}

/** Returns array of {key, label, tasks} preserving spec order. */
export function groupTasks(tasks, by, phaseOrder) {
  if (by === 'status') {
    return STATUS_ORDER.map(key => ({
      key,
      label: STATUS_LABELS[key],
      tasks: (tasks || []).filter(t => (t.status || 'todo') === key),
    }));
  }
  if (by === 'phase') {
    const order = (Array.isArray(phaseOrder) && phaseOrder.length) ? phaseOrder.slice() : [];
    // Add any phases present in tasks that aren't in declared order.
    for (const t of tasks || []) {
      if (t.phase && !order.includes(t.phase)) order.push(t.phase);
    }
    const groups = order.map(key => ({
      key,
      label: key,
      tasks: (tasks || []).filter(t => t.phase === key),
    }));
    const orphans = (tasks || []).filter(t => !t.phase);
    groups.push({ key: '__orphans__', label: 'Orphans', tasks: orphans });
    return groups;
  }
  if (by === 'epic') {
    const seen = new Map();
    for (const t of tasks || []) {
      const k = t.epic || '__none__';
      if (!seen.has(k)) seen.set(k, []);
      seen.get(k).push(t);
    }
    return [...seen.entries()].map(([key, ts]) => ({
      key,
      label: key === '__none__' ? '— no epic —' : key,
      tasks: ts,
    }));
  }
  // Fallback: single group.
  return [{ key: 'all', label: 'All', tasks: tasks || [] }];
}

export const STATUS_LABELS = {
  blocked: 'Blocked',
  todo: 'Todo',
  in_progress: 'In Progress',
  in_review: 'In Review',
  done: 'Done',
};
```

- [ ] **Step 4: Run test to verify pass**

Run: `node --test plugins/taskmaster/viewer/tests/unit/filters.test.js`
Expected: 12 pass.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/viewer/js/lib/filters.js plugins/taskmaster/viewer/tests/unit/filters.test.js
git commit -m "feat(viewer): lib/filters.js (filter + sort + group, fully tested)"
```

---

### Task 8: `lib/copy.js` (click-to-copy with green flash)

**Files:**
- Create: `plugins/taskmaster/viewer/js/lib/copy.js`

(No unit test — depends on `navigator.clipboard` and DOM. Covered by Playwright in Task 31.)

- [ ] **Step 1: Implement**

Create `plugins/taskmaster/viewer/js/lib/copy.js`:

```js
// Click-to-copy helper. Adds a green-flash via class swap.
//
// Usage:
//   const span = document.createElement('span');
//   span.textContent = 'v3-014';
//   span.classList.add('cmp-copy');
//   bindCopy(span, 'v3-014');

const FLASH_MS = 1200;

export async function copyToClipboard(text) {
  if (!text) return false;
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch (e) {
    // fall through to legacy
  }
  // Fallback: invisible textarea + execCommand.
  try {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.setAttribute('readonly', '');
    ta.style.cssText = 'position:absolute;left:-9999px;top:0;opacity:0;';
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    ta.remove();
    return true;
  } catch (e) {
    console.error('copy failed', e);
    return false;
  }
}

export function bindCopy(el, text, opts = {}) {
  const flashClass = opts.flashClass || 'cmp-flash-copied';
  el.style.cursor = 'copy';
  el.addEventListener('click', async (ev) => {
    ev.stopPropagation();
    const ok = await copyToClipboard(text);
    if (ok) {
      el.classList.add(flashClass);
      setTimeout(() => el.classList.remove(flashClass), FLASH_MS);
    }
  });
}
```

- [ ] **Step 2: Add the `.cmp-flash-copied` style + `.cmp-icon-btn` to `components.css`**

Append to `plugins/taskmaster/viewer/css/components.css`:

```css
/* ────── click-to-copy flash + small icon button ────── */
.cmp-flash-copied {
  background: rgba(95, 174, 110, 0.18) !important;
  color: var(--green) !important;
}
.cmp-flash-copied::after {
  content: ' copied';
  font-family: var(--font-sans);
  font-size: var(--text-xs);
}

.cmp-icon-btn {
  appearance: none;
  background: transparent;
  border: 0;
  color: var(--ink-3);
  font-size: var(--text-md);
  line-height: 1;
  cursor: pointer;
  padding: 2px 4px;
  border-radius: var(--r-sm);
  transition: color var(--t-fast) var(--ease), background var(--t-fast) var(--ease);
}
.cmp-icon-btn:hover {
  color: var(--ink);
  background: rgba(255, 255, 255, 0.05);
}
```

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/js/lib/copy.js plugins/taskmaster/viewer/css/components.css
git commit -m "feat(viewer): lib/copy.js + cmp-flash-copied/cmp-icon-btn styles"
```

---

## M3 — Card Component

### Task 9: Initial `kanban.css` skeleton + per-epic tokens

**Files:**
- Create: `plugins/taskmaster/viewer/css/screens/kanban.css`
- Modify: `plugins/taskmaster/viewer/index.html` (link the CSS)

- [ ] **Step 1: Create `kanban.css` with the structural / token block**

Create `plugins/taskmaster/viewer/css/screens/kanban.css`:

```css
/* Kanban screen — owns its layout, stepper, chips, board, and card visuals.
   Per Plan 1 conventions: screen-local tokens use the --kanban-* / --card-* prefix.
   Per spec §3.7 (Variant E): NO edge stripes, NO body wash. Color goes on chip + ID only. */

:root {
  --kanban-board-bg-grad: radial-gradient(120% 100% at 0% 0%, rgba(74,158,255,0.05), transparent 60%),
                          linear-gradient(180deg, #1a1f29 0%, #161a22 100%);
  --kanban-board-border:  #2e3a4d;
  --card-bg-auto-grad:    linear-gradient(180deg, rgba(74,158,255,0.03), transparent 40%);
  --card-recent-glow:     0 0 0 1px rgba(127,179,240,0.4), 0 0 18px rgba(74,158,255,0.12);
}

/* ─────────── PAGE LAYOUT ─────────── */
.kanban-page { display: flex; flex-direction: column; gap: var(--sp-5); min-width: 0; }

.kanban-head {
  display: flex; align-items: center; gap: var(--sp-4);
  padding-bottom: var(--sp-4);
  border-bottom: 1px solid var(--border);
  flex-wrap: wrap;
}
.kanban-head .title    { font-size: 18px; font-weight: 600; letter-spacing: -0.01em; }
.kanban-head .subcount { font-size: var(--text-sm); color: var(--ink-3); padding-right: var(--sp-3); border-right: 1px solid var(--border); }

.kanban-search {
  display: inline-flex; align-items: center; gap: var(--sp-2);
  flex: 1 1 240px; min-width: 200px;
  background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--r-md);
  padding: 4px var(--sp-3);
}
.kanban-search input {
  background: transparent; border: 0; outline: 0;
  color: var(--ink); font-size: var(--text-base);
  flex: 1; font-family: var(--font-sans);
}
.kanban-search input::placeholder { color: var(--ink-3); }
.kanban-search .icon { color: var(--ink-3); }

.kanban-head-right { margin-left: auto; display: flex; align-items: center; gap: var(--sp-2); }
.kanban-group-btn,
.kanban-sort-btn,
.kanban-add-btn {
  background: var(--bg-card); border: 1px solid var(--border); color: var(--ink-2);
  font-size: var(--text-sm); padding: 4px var(--sp-3); border-radius: var(--r-md);
  cursor: pointer; display: inline-flex; align-items: center; gap: var(--sp-1);
  font-family: var(--font-sans);
}
.kanban-group-btn:hover,
.kanban-sort-btn:hover { color: var(--ink); border-color: var(--border-strong); }
.kanban-add-btn { background: var(--accent-soft); border-color: rgba(74,158,255,0.4); color: var(--accent); }

.kanban-reset-link { color: var(--ink-3); cursor: pointer; font-size: var(--text-xs); }
.kanban-reset-link:hover { color: var(--red); }
```

- [ ] **Step 2: Link the new CSS in `index.html`**

Open `plugins/taskmaster/viewer/index.html`. After the existing `<link rel="stylesheet" href="css/screens/_placeholders.css">` line, add:

```html
  <link rel="stylesheet" href="css/screens/kanban.css">
```

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/css/screens/kanban.css plugins/taskmaster/viewer/index.html
git commit -m "feat(viewer): kanban.css scaffold + page-head/search styles"
```

---

### Task 10: Card CSS (Minimal + Full + Variant E)

**Files:**
- Modify: `plugins/taskmaster/viewer/css/screens/kanban.css`

- [ ] **Step 1: Append card styles**

Append to `plugins/taskmaster/viewer/css/screens/kanban.css`:

```css
/* ─────────── CARD (Minimal + Full) ───────────
   Variant E: no edge stripes, no body wash.
   The epic color paints ONLY the .card-chip (epic chip swatch + bg) and the .card-id text.
   --epic + --epic-soft are set inline per-card by JS (see lib/epics.js). */

.card-task {
  position: relative;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--r-md);
  margin-bottom: var(--sp-2);
  cursor: pointer;
  transition: background var(--t-fast) var(--ease), border-color var(--t-fast) var(--ease);
}
.card-task:hover {
  background: #23252b;
  border-color: var(--border-strong);
  /* Spec §3.6: no movement / no transform on hover. */
}
.card-task.recent { box-shadow: var(--card-recent-glow); }

.card-task.auto {
  border-color: rgba(74, 158, 255, 0.35);
}
.card-task.auto .card-body {
  background: var(--card-bg-auto-grad);
  border-radius: var(--r-md) var(--r-md) 0 0;
}

.card-body { padding: 8px 10px 9px; }

/* Header band: id · priority · size · time-in-status */
.card-meta {
  display: flex; align-items: center; gap: var(--sp-2);
  font-size: var(--text-xs);
  margin-bottom: 5px;
}
.card-id {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--epic, var(--ink-3));   /* Variant E: ID picks up epic color */
  padding: 1px 5px;
  border-radius: var(--r-sm);
  user-select: none;
  display: inline-flex; align-items: center; gap: 4px;
  transition: background var(--t-fast) var(--ease);
}
.card-id:hover { background: var(--epic-soft, rgba(255,255,255,0.05)); }
.card-id .copy-glyph { opacity: 0; font-size: 10px; transition: opacity var(--t-fast) var(--ease); }
.card-id:hover .copy-glyph { opacity: 0.7; }

.card-pri {
  font-size: var(--text-xs); padding: 1px 6px; border-radius: var(--r-sm);
  font-weight: 600; letter-spacing: 0.02em;
}
.card-pri.critical { background: rgba(214,107,95,0.22); color: var(--red); }
.card-pri.high     { background: rgba(214,164,95,0.22); color: var(--amber); }
.card-pri.medium   { background: rgba(74,158,255,0.18); color: var(--accent); }
.card-pri.low      { background: rgba(127,179,240,0.12); color: var(--accent-2); }

.card-size {
  font-family: var(--font-mono);
  font-size: var(--text-xs); color: var(--ink-3);
  border: 1px solid var(--border); padding: 1px 5px; border-radius: var(--r-sm);
}
.card-tis {
  margin-left: auto;
  font-family: var(--font-mono); font-size: var(--text-xs); color: var(--ink-3);
}
.card-tis.stale { color: var(--amber); }

/* Title */
.card-title {
  font-size: var(--text-md);
  font-weight: 500;
  color: var(--ink);
  line-height: 1.35;
  letter-spacing: -0.005em;
  margin: 0;
}

/* ─── FULL-only rows ─── */
.card-task.full .card-title { margin-bottom: var(--sp-2); }

.card-chip-row {
  display: flex; align-items: center; gap: var(--sp-2);
  margin-bottom: var(--sp-2);
  flex-wrap: wrap;
}
.card-epic-chip {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 2px 7px;
  background: var(--epic-soft, rgba(124,130,144,0.14));
  color: var(--epic, var(--ink-2));
  border-radius: 999px;
  font-size: var(--text-xs);
}
.card-epic-chip .swatch {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--epic, var(--ink-3));
}
.card-spec-badge {
  font-size: var(--text-xs); padding: 2px 6px; border-radius: var(--r-sm);
  font-weight: 600; display: inline-flex; align-items: center; gap: 3px;
}
.card-spec-badge.pass { background: rgba(95,174,110,0.18); color: var(--green); }
.card-spec-badge.warn { background: rgba(214,164,95,0.22); color: var(--amber); }
.card-spec-badge.fail { background: rgba(214,107,95,0.22); color: var(--red); }
.card-dep-badge {
  font-size: var(--text-xs); color: var(--ink-3);
  display: inline-flex; align-items: center; gap: 3px;
}
.card-dep-badge.blocking { color: var(--red); font-weight: 500; }
.card-subrepo-chip {
  font-size: var(--text-xs); padding: 2px 6px; border-radius: var(--r-sm);
  background: rgba(255,255,255,0.04); color: var(--ink-3);
  font-family: var(--font-mono);
}

.card-footer {
  display: flex; align-items: center; gap: var(--sp-2);
  padding-top: var(--sp-2);
  border-top: 1px solid var(--border-soft);
  font-size: var(--text-xs);
}
.card-branch {
  color: var(--accent-2);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  display: inline-flex; align-items: center; gap: 4px;
  min-width: 0;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  padding: 1px 5px; border-radius: var(--r-sm);
  transition: background var(--t-fast) var(--ease);
}
.card-branch:hover { background: rgba(74,158,255,0.10); }
.card-branch.empty { color: var(--ink-3); }
.card-branch .glyph { opacity: 0.7; flex: 0 0 auto; }

.card-actions { margin-left: auto; display: flex; align-items: center; gap: var(--sp-2); }

.card-callout {
  margin: var(--sp-2) -10px -9px;
  padding: 5px 10px;
  font-size: var(--text-xs);
  display: flex; align-items: center; gap: 5px;
  border-top: 1px solid var(--border-soft);
}
.card-callout.warn { background: rgba(214,107,95,0.10); color: var(--red); }

/* Status label rendered when grouped by phase or epic (per spec §3.8 — drop on status grouping). */
.card-status-pill {
  font-size: var(--text-xs);
  padding: 1px 6px; border-radius: 999px;
  background: rgba(255,255,255,0.04); color: var(--ink-2);
  display: inline-flex; align-items: center; gap: 4px;
}
.card-status-pill .dot { width: 5px; height: 5px; border-radius: 50%; background: var(--ink-3); }
.card-status-pill.todo .dot         { background: var(--ink-3); }
.card-status-pill.in_progress .dot  { background: var(--accent); }
.card-status-pill.in_review .dot    { background: var(--amber); }
.card-status-pill.done .dot         { background: var(--green); }
.card-status-pill.blocked .dot      { background: var(--red); }
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/css/screens/kanban.css
git commit -m "feat(viewer): card styles (Minimal + Full + Variant E)"
```

---

### Task 11: Implement `components/card.js`

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/card.js`

- [ ] **Step 1: Write the file**

Create `plugins/taskmaster/viewer/js/components/card.js`:

```js
// Shared task card. Renders Minimal or Full density.
//
// Usage:
//   const el = renderCard({ task, density: 'full', epicColors, autoState, groupBy, now });
//
// Inputs:
//   task         — backlog task object (v3 schema)
//   density      — 'minimal' | 'full'
//   epicColors   — {epicId → hex} from lib/epics.js#assignEpicColors
//   autoState    — current auto-mode state object (or null) — used to attach a live block
//   groupBy      — 'status' | 'phase' | 'epic' (drives whether status pill renders)
//   now          — ms (for time-in-status) — defaults to Date.now()

import { formatTimeInStatus, classifyTimeInStatus, isoToMs, formatElapsed } from '../lib/time.js';
import { epicColor, epicCssVar } from '../lib/epics.js';
import { bindCopy } from '../lib/copy.js';
import { renderAutoModeLiveBlock } from './auto-mode-live-block.js';

const PRIORITY_LABELS = { critical: 'Critical', high: 'High', medium: 'Medium', low: 'Low' };
const STATUS_LABELS   = { blocked: 'Blocked', todo: 'Todo', in_progress: 'In Progress', in_review: 'In Review', done: 'Done' };

export function renderCard({ task, density = 'full', epicColors = {}, autoState = null, groupBy = 'status', now = Date.now() } = {}) {
  if (!task || !task.id) return document.createComment('empty card');

  const card = document.createElement('div');
  card.className = 'card-task ' + density;
  card.dataset.taskId = task.id;

  const isAuto = !!(autoState && autoState.mode && autoState.cursor && autoState.cursor.task_id === task.id);
  if (isAuto) card.classList.add('auto');

  // Recently-moved highlight: 24h after status change (spec §3.6).
  const startedMs = isoToMs(task.started);
  if (startedMs && (now - startedMs) < 24 * 60 * 60 * 1000) {
    card.classList.add('recent');
  }

  // Inline epic CSS variables.
  card.setAttribute('style', epicCssVar(epicColor(task.epic, epicColors)));

  const body = document.createElement('div');
  body.className = 'card-body';
  card.appendChild(body);

  // Click navigates to task detail.
  card.addEventListener('click', (ev) => {
    if (ev.target.closest('.card-id') || ev.target.closest('.card-branch') || ev.target.closest('.cmp-icon-btn')) return;
    location.hash = '#/task/' + encodeURIComponent(task.id);
  });

  // ── Meta line: id · priority · size · time-in-status ──
  const meta = document.createElement('div');
  meta.className = 'card-meta';

  const id = document.createElement('span');
  id.className = 'card-id';
  id.innerHTML = `<span class="label-text">${escapeHtml(task.id)}</span><span class="copy-glyph">⧉</span>`;
  bindCopy(id, task.id);
  meta.appendChild(id);

  const sep = document.createElement('span');
  sep.style.cssText = 'color:var(--ink-3); opacity:0.4;';
  sep.textContent = '·';
  meta.appendChild(sep);

  const pri = String(task.priority || 'medium').toLowerCase();
  const priEl = document.createElement('span');
  priEl.className = 'card-pri ' + pri;
  priEl.textContent = PRIORITY_LABELS[pri] || PRIORITY_LABELS.medium;
  meta.appendChild(priEl);

  if (task.estimate) {
    const sz = document.createElement('span');
    sz.className = 'card-size';
    sz.textContent = task.estimate;
    meta.appendChild(sz);
  }

  // Time-in-status — anchored at started (or created).
  const tisAnchor = startedMs || isoToMs(task.created);
  const tisText   = formatTimeInStatus(tisAnchor, now);
  if (tisText) {
    const tis = document.createElement('span');
    tis.className = 'card-tis ' + classifyTimeInStatus(tisAnchor, now);
    tis.textContent = tisText;
    meta.appendChild(tis);
  }
  body.appendChild(meta);

  // ── Title ──
  const title = document.createElement('div');
  title.className = 'card-title';
  title.textContent = task.title || '(untitled)';
  body.appendChild(title);

  // Minimal density stops here (plus auto live block + status pill if grouped non-status).
  if (density === 'minimal') {
    if (groupBy !== 'status' && task.status) appendStatusPill(body, task.status);
    if (isAuto) appendLiveBlock(card, autoState);
    return card;
  }

  // ── Chip row: epic · spec-review · deps · sub-repo ──
  const chipRow = document.createElement('div');
  chipRow.className = 'card-chip-row';
  let chipRowHasContent = false;

  if (task.epic) {
    const ec = document.createElement('span');
    ec.className = 'card-epic-chip';
    ec.innerHTML = `<span class="swatch"></span>${escapeHtml(task.epic)}`;
    chipRow.appendChild(ec);
    chipRowHasContent = true;
  }
  if (task.spec_review) {
    const verdict = task.spec_review.verdict || task.spec_review;
    const known = ['pass', 'warn', 'fail'];
    if (known.includes(verdict)) {
      const sb = document.createElement('span');
      sb.className = 'card-spec-badge ' + verdict;
      const glyph = verdict === 'pass' ? '✓' : verdict === 'warn' ? '!' : '✗';
      sb.textContent = `${glyph} spec`;
      chipRow.appendChild(sb);
      chipRowHasContent = true;
    }
  }
  if (typeof task.depends_on_unmet_count === 'number' && task.depends_on_unmet_count > 0) {
    const db = document.createElement('span');
    db.className = 'card-dep-badge' + (task.status !== 'done' ? ' blocking' : '');
    db.textContent = `↳ ${task.depends_on_unmet_count} unmet`;
    chipRow.appendChild(db);
    chipRowHasContent = true;
  } else if (Array.isArray(task.depends_on) && task.depends_on.length) {
    const db = document.createElement('span');
    db.className = 'card-dep-badge';
    db.textContent = `↳ ${task.depends_on.length}`;
    chipRow.appendChild(db);
    chipRowHasContent = true;
  }
  if (task.sub_repo) {
    const sr = document.createElement('span');
    sr.className = 'card-subrepo-chip';
    sr.textContent = task.sub_repo;
    chipRow.appendChild(sr);
    chipRowHasContent = true;
  }
  if (groupBy !== 'status' && task.status) {
    appendStatusPill(chipRow, task.status);
    chipRowHasContent = true;
  }
  if (chipRowHasContent) body.appendChild(chipRow);

  // ── Footer: branch + action icons ──
  const footer = document.createElement('div');
  footer.className = 'card-footer';

  const branch = document.createElement('span');
  branch.className = 'card-branch' + (task.branch ? '' : ' empty');
  branch.innerHTML = `<span class="glyph">⎇</span>${escapeHtml(task.branch || '— no branch —')}`;
  if (task.branch) bindCopy(branch, task.branch);
  footer.appendChild(branch);

  const actions = document.createElement('span');
  actions.className = 'card-actions';
  if (task.docs && Object.keys(task.docs).length) {
    const docsBtn = document.createElement('button');
    docsBtn.className = 'cmp-icon-btn';
    docsBtn.title = 'Open primary doc';
    docsBtn.textContent = '📄';
    docsBtn.addEventListener('click', (ev) => {
      ev.stopPropagation();
      const first = Object.values(task.docs)[0];
      if (first) window.open(first, '_blank', 'noopener');
    });
    actions.appendChild(docsBtn);
  }
  footer.appendChild(actions);
  body.appendChild(footer);

  // ── Callout: blocked + unmet deps ──
  if (task.status === 'blocked' && Array.isArray(task.blockers) && task.blockers.length) {
    const callout = document.createElement('div');
    callout.className = 'card-callout warn';
    callout.textContent = `⛔ blocked: ${task.blockers.length} unmet`;
    body.appendChild(callout);
  }

  // ── Auto-mode live block ──
  if (isAuto) appendLiveBlock(card, autoState);

  return card;
}

function appendStatusPill(parent, status) {
  const pill = document.createElement('span');
  pill.className = 'card-status-pill ' + status;
  pill.innerHTML = `<span class="dot"></span>${STATUS_LABELS[status] || status}`;
  parent.appendChild(pill);
}

function appendLiveBlock(card, autoState) {
  const block = renderAutoModeLiveBlock({ autoState });
  if (block) card.appendChild(block);
}

function escapeHtml(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/card.js
git commit -m "feat(viewer): components/card.js (Minimal + Full)"
```

---

### Task 12: Implement `components/auto-mode-live-block.js`

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/auto-mode-live-block.js`
- Modify: `plugins/taskmaster/viewer/css/screens/kanban.css`

- [ ] **Step 1: Append live-block CSS**

Append to `plugins/taskmaster/viewer/css/screens/kanban.css`:

```css
/* ─────────── PER-CARD AUTO-MODE LIVE BLOCK ─────────── */
.card-live {
  margin-top: var(--sp-2);
  padding: 7px 10px;
  background: rgba(74, 158, 255, 0.05);
  border-top: 1px solid rgba(74, 158, 255, 0.15);
  border-radius: 0 0 var(--r-md) var(--r-md);
}
.card-live-row {
  display: flex; align-items: center; gap: var(--sp-2);
  font-size: var(--text-xs);
  color: #8fb6e8;
}
.card-live-row .pulse {
  width: 5px; height: 5px; border-radius: 50%;
  background: var(--accent);
  animation: pulse 1.6s ease-in-out infinite;
}
.card-live-row .step-text { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.card-live-row .elapsed { margin-left: auto; color: var(--ink-3); font-family: var(--font-mono); }
.card-live-bar {
  margin-top: 5px; height: 3px;
  background: rgba(255,255,255,0.06); border-radius: 2px; overflow: hidden;
  position: relative;
}
.card-live-bar > i {
  display: block; height: 100%;
  background: linear-gradient(90deg, var(--accent), var(--accent-2));
  transition: width var(--t-base) var(--ease);
}
/* Shimmer overlay — passes left → right every 2.4s. */
.card-live-bar::after {
  content: ''; position: absolute; inset: 0;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.18), transparent);
  background-size: 40% 100%;
  background-repeat: no-repeat;
  animation: shimmer 2.4s ease-in-out infinite;
}
@keyframes shimmer {
  0%   { background-position: -50% 0; }
  100% { background-position: 150% 0; }
}
```

- [ ] **Step 2: Create the component**

Create `plugins/taskmaster/viewer/js/components/auto-mode-live-block.js`:

```js
// Per-card auto-mode live block.
// Shows: pulse · step text (e.g. "step 3/5 · IMPLEMENT") · step bar · elapsed.

import { formatElapsed, isoToMs } from '../lib/time.js';

const STAGE_ORDER = ['PICK', 'IMPLEMENT', 'REVIEW', 'HANDOVER_STUB', 'COMPLETE'];

export function renderAutoModeLiveBlock({ autoState, now = Date.now() } = {}) {
  if (!autoState || !autoState.cursor) return null;

  const stage    = autoState.cursor.stage || 'PICK';
  const stageIdx = Math.max(0, STAGE_ORDER.indexOf(stage));
  const total    = STAGE_ORDER.length;
  const pct      = Math.round(((stageIdx + 0.5) / total) * 100);

  const startedMs = isoToMs(autoState.started_at);
  const elapsedMs = startedMs ? Math.max(0, now - startedMs) : 0;

  const wrap = document.createElement('div');
  wrap.className = 'card-live';

  const row = document.createElement('div');
  row.className = 'card-live-row';
  row.innerHTML = `
    <span class="pulse"></span>
    <span class="step-text">step ${stageIdx + 1}/${total} · ${escapeHtml(stage)}</span>
    <span class="elapsed">${formatElapsed(elapsedMs)}</span>
  `;
  wrap.appendChild(row);

  const bar = document.createElement('div');
  bar.className = 'card-live-bar';
  bar.innerHTML = `<i style="width:${pct}%"></i>`;
  wrap.appendChild(bar);

  return wrap;
}

function escapeHtml(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
```

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/auto-mode-live-block.js plugins/taskmaster/viewer/css/screens/kanban.css
git commit -m "feat(viewer): per-card auto-mode live block + shimmer bar"
```

---

### Task 13: Quick visual sanity — render two cards in dev console

(Informational; no commit.)

- [ ] **Step 1: Boot the server**

```bash
python -c "from backlog_server import _make_server; s, p = _make_server(host='127.0.0.1', port=0); print(f'http://127.0.0.1:{p}/v3'); s.serve_forever()"
```

- [ ] **Step 2: Open `/v3` in a browser. In DevTools console:**

```js
const { renderCard } = await import('/static/v3/js/components/card.js');
const t = { id: 'v3-014', title: 'Auto-mode status indicator', status: 'todo', priority: 'high', estimate: 'M', epic: 'viewer-redesign', branch: 'feat/auto-mode-strip', started: '2026-04-24T10:00:00Z' };
const ec = { 'viewer-redesign': '#6ea8ff' };
const root = document.getElementById('screen-mount');
root.innerHTML = '';
root.appendChild(renderCard({ task: t, density: 'full', epicColors: ec, groupBy: 'status' }));
root.appendChild(renderCard({ task: { ...t, id: 'v3-009', title: 'Wire viewer to v3', priority: 'critical', status: 'in_progress', estimate: 'L' }, density: 'full', epicColors: ec, groupBy: 'status', autoState: { mode: 'running', cursor: { task_id: 'v3-009', stage: 'IMPLEMENT' }, started_at: new Date(Date.now() - 90_000).toISOString() } }));
```

Expected: Two cards. First: muted, no live block. Second: live block with "step 2/5 · IMPLEMENT", elapsed "01:30", a faint shimmer on the bar. ID text on each card is blue (#6ea8ff). No edge stripes anywhere.

If anything is off (extra borders, wrong colors), debug `card.js` / `kanban.css` before continuing.

---

## M4 — Auto-mode UI Components (Strip)

### Task 14: Spinner + strip CSS

**Files:**
- Modify: `plugins/taskmaster/viewer/css/screens/kanban.css`

- [ ] **Step 1: Append strip styles**

Append to `plugins/taskmaster/viewer/css/screens/kanban.css`:

```css
/* ─────────── AUTO-MODE STRIP (light, top of page) ─────────── */
.kanban-strip {
  display: flex; align-items: center; gap: var(--sp-5);
  padding: var(--sp-2) var(--sp-3) var(--sp-3);
  border-bottom: 1px solid var(--border);
  font-size: var(--text-base);
  flex-wrap: wrap;
}
.kanban-strip[hidden] { display: none; }

.kanban-strip-title {
  display: inline-flex; align-items: center; gap: var(--sp-2);
  font-size: var(--text-sm); text-transform: uppercase; letter-spacing: 0.08em;
  color: #8fb6e8;
}
.kanban-strip-title .live-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--accent);
  animation: pulse 1.6s ease-in-out infinite;
}

/* Conic-gradient sweep spinner — 12px, smooth (spec §3.3). */
.kanban-strip-spinner {
  width: 12px; height: 12px; border-radius: 50%;
  background: conic-gradient(from 0deg, transparent 0deg, var(--accent) 280deg, transparent 359deg);
  -webkit-mask: radial-gradient(circle at center, transparent 4px, #000 5px);
          mask: radial-gradient(circle at center, transparent 4px, #000 5px);
  animation: spin 1.4s linear infinite;
  flex: 0 0 auto;
}
@keyframes spin { to { transform: rotate(360deg); } }

.kanban-strip-session-time {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--ink-3);
}

.kanban-strip-runs {
  display: flex; gap: var(--sp-6);
  flex: 1 1 auto; overflow: hidden;
  min-width: 0;
}
.kanban-strip-run {
  display: flex; align-items: center; gap: var(--sp-2);
  font-size: var(--text-base); color: var(--ink-2);
  min-width: 0;
}
.kanban-strip-run + .kanban-strip-run { border-left: 1px solid var(--border); padding-left: var(--sp-5); }
.kanban-strip-run .id   { color: var(--ink-3); font-family: var(--font-mono); font-size: var(--text-sm); }
.kanban-strip-run .name { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 180px; }
.kanban-strip-run .pct  { color: #8fb6e8; font-variant-numeric: tabular-nums; font-size: var(--text-sm); }
.kanban-strip-run .mini-bar {
  width: 64px; height: 3px; background: rgba(255,255,255,0.06); border-radius: 2px; overflow: hidden;
  position: relative;
}
.kanban-strip-run .mini-bar > i {
  display: block; height: 100%;
  background: linear-gradient(90deg, var(--accent), var(--accent-2));
}
.kanban-strip-run .mini-bar::after {
  content: ''; position: absolute; inset: 0;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.18), transparent);
  background-size: 40% 100%;
  background-repeat: no-repeat;
  animation: shimmer 2.4s ease-in-out infinite;
}
.kanban-strip-run .elapsed { color: var(--ink-3); font-family: var(--font-mono); font-size: var(--text-xs); }

.kanban-strip-action {
  font-size: var(--text-sm); color: var(--ink-3); cursor: pointer;
  flex: 0 0 auto;
}
.kanban-strip-action:hover { color: var(--ink-2); }
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/css/screens/kanban.css
git commit -m "feat(viewer): kanban auto-mode strip styles + conic spinner"
```

---

### Task 15: Implement `components/auto-mode-strip.js`

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/auto-mode-strip.js`

- [ ] **Step 1: Write the component**

Create `plugins/taskmaster/viewer/js/components/auto-mode-strip.js`:

```js
// Light auto-mode strip across the top of the kanban (spec §3.3).
// Shows: conic spinner · "Auto-mode · N running" · session timer · per-run pills · "view all →"
//
// Render-only: takes a normalized list of runs. Updates in place via update().

import { formatElapsed, isoToMs } from '../lib/time.js';

const STAGE_ORDER = ['PICK', 'IMPLEMENT', 'REVIEW', 'HANDOVER_STUB', 'COMPLETE'];

/** Convert raw auto state → run rows the strip can render.
 *  Plan 6 will return multiple parallel runs; Plan 2 derives a single-run list from cursor. */
export function runsFromAutoState(autoState, backlog) {
  if (!autoState || !autoState.cursor) return { runs: [], sessionStartedMs: null };
  const tid = autoState.cursor.task_id;
  const task = (backlog?.tasks || []).find(t => t.id === tid);
  const stageIdx = Math.max(0, STAGE_ORDER.indexOf(autoState.cursor.stage || 'PICK'));
  const pct = Math.round(((stageIdx + 0.5) / STAGE_ORDER.length) * 100);
  const startedMs = isoToMs(autoState.started_at);
  return {
    sessionStartedMs: startedMs,
    runs: [{
      id: tid,
      name: task?.title || tid,
      pct,
      startedMs,
    }],
  };
}

export function renderAutoModeStrip({ autoState, backlog, onViewAll, now = Date.now() }) {
  const wrap = document.createElement('div');
  wrap.className = 'kanban-strip';
  wrap.dataset.cmp = 'auto-mode-strip';
  paintStrip(wrap, { autoState, backlog, onViewAll, now });
  return wrap;
}

export function updateAutoModeStrip(el, { autoState, backlog, onViewAll, now = Date.now() }) {
  if (!el) return;
  paintStrip(el, { autoState, backlog, onViewAll, now });
}

function paintStrip(el, { autoState, backlog, onViewAll, now }) {
  const { runs, sessionStartedMs } = runsFromAutoState(autoState, backlog);
  el.replaceChildren();

  if (!autoState || !autoState.mode || !runs.length) {
    el.hidden = true;
    return;
  }
  el.hidden = false;

  const title = document.createElement('div');
  title.className = 'kanban-strip-title';
  title.innerHTML = `
    <span class="kanban-strip-spinner" aria-hidden="true"></span>
    <span class="live-dot"></span>
    Auto-mode · ${runs.length} running
  `;
  el.appendChild(title);

  if (sessionStartedMs) {
    const t = document.createElement('div');
    t.className = 'kanban-strip-session-time';
    t.textContent = `running ${formatElapsed(now - sessionStartedMs)}`;
    el.appendChild(t);
  }

  const runsEl = document.createElement('div');
  runsEl.className = 'kanban-strip-runs';
  for (const r of runs) {
    const row = document.createElement('div');
    row.className = 'kanban-strip-run';
    row.innerHTML = `
      <span class="id">${escapeHtml(r.id || '?')}</span>
      <span class="name">${escapeHtml(r.name || '')}</span>
      <span class="mini-bar"><i style="width:${r.pct}%"></i></span>
      <span class="pct">${r.pct}%</span>
      <span class="elapsed">${r.startedMs ? formatElapsed(now - r.startedMs) : ''}</span>
    `;
    row.addEventListener('click', () => {
      if (r.id) location.hash = '#/task/' + encodeURIComponent(r.id);
    });
    runsEl.appendChild(row);
  }
  el.appendChild(runsEl);

  const action = document.createElement('div');
  action.className = 'kanban-strip-action';
  action.textContent = 'view all →';
  action.addEventListener('click', () => {
    if (onViewAll) onViewAll();
    else location.hash = '#/auto';
  });
  el.appendChild(action);
}

function escapeHtml(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/auto-mode-strip.js
git commit -m "feat(viewer): components/auto-mode-strip.js (light header strip)"
```

---

### Task 16: Strip session-timer ticks every second

**Files:**
- Modify: `plugins/taskmaster/viewer/js/components/auto-mode-strip.js`

(The strip currently renders "running 01:42:08" only on store updates — every 3s. The session timer should tick every 1s for smoothness.)

- [ ] **Step 1: Add a 1s repaint cadence**

Replace the entire `renderAutoModeStrip` and `updateAutoModeStrip` exports in `auto-mode-strip.js` with:

```js
export function renderAutoModeStrip({ autoState, backlog, onViewAll }) {
  const wrap = document.createElement('div');
  wrap.className = 'kanban-strip';
  wrap.dataset.cmp = 'auto-mode-strip';

  // Cache deps on the element so the per-second tick can use them.
  wrap._deps = { autoState, backlog, onViewAll };
  paintStrip(wrap, { ...wrap._deps, now: Date.now() });

  // 1-Hz tick to keep the elapsed counters smooth.
  const tick = setInterval(() => {
    paintStrip(wrap, { ...wrap._deps, now: Date.now() });
  }, 1000);
  wrap._tick = tick;
  return wrap;
}

export function updateAutoModeStrip(el, { autoState, backlog, onViewAll }) {
  if (!el) return;
  el._deps = { autoState, backlog, onViewAll };
  paintStrip(el, { ...el._deps, now: Date.now() });
}

export function destroyAutoModeStrip(el) {
  if (el && el._tick) {
    clearInterval(el._tick);
    el._tick = null;
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/auto-mode-strip.js
git commit -m "feat(viewer): strip session timer ticks at 1Hz"
```

---

## M5 — Kanban Controls

### Task 17: `priority-chips.js` + CSS

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/priority-chips.js`
- Modify: `plugins/taskmaster/viewer/css/screens/kanban.css`

- [ ] **Step 1: Append CSS**

Append to `plugins/taskmaster/viewer/css/screens/kanban.css`:

```css
/* ─────────── PRIORITY CHIPS ─────────── */
.kanban-pri-row { display: inline-flex; gap: 4px; flex: 0 0 auto; }
.kanban-pri-tog {
  appearance: none;
  padding: 3px 9px;
  font-size: var(--text-sm);
  border-radius: var(--r-sm);
  cursor: pointer;
  font-weight: 500;
  border: 1px solid var(--border);
  background: var(--bg-card);
  color: var(--ink-3);
  font-family: var(--font-sans);
}
.kanban-pri-tog.critical.on { background: rgba(214,107,95,0.22); border-color: var(--red);   color: var(--red); }
.kanban-pri-tog.high.on     { background: rgba(214,164,95,0.22); border-color: var(--amber); color: var(--amber); }
.kanban-pri-tog.medium.on   { background: rgba(74,158,255,0.18); border-color: var(--accent);color: var(--accent); }
.kanban-pri-tog.low.on      { background: rgba(127,179,240,0.12); border-color: var(--accent-2); color: var(--accent-2); }
```

- [ ] **Step 2: Implement the component**

Create `plugins/taskmaster/viewer/js/components/priority-chips.js`:

```js
const PRIORITIES = [
  { key: 'critical', label: 'Critical' },
  { key: 'high',     label: 'High' },
  { key: 'medium',   label: 'Medium' },
  { key: 'low',      label: 'Low' },
];

export function renderPriorityChips({ active = [], onToggle }) {
  const wrap = document.createElement('div');
  wrap.className = 'kanban-pri-row';
  wrap.dataset.cmp = 'priority-chips';
  wrap._active = new Set(active);

  for (const p of PRIORITIES) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = `kanban-pri-tog ${p.key}` + (wrap._active.has(p.key) ? ' on' : '');
    btn.dataset.key = p.key;
    btn.textContent = p.label;
    btn.addEventListener('click', () => {
      if (wrap._active.has(p.key)) wrap._active.delete(p.key);
      else                          wrap._active.add(p.key);
      btn.classList.toggle('on');
      if (onToggle) onToggle([...wrap._active]);
    });
    wrap.appendChild(btn);
  }
  return wrap;
}

export function updatePriorityChips(el, { active }) {
  if (!el) return;
  el._active = new Set(active || []);
  el.querySelectorAll('.kanban-pri-tog').forEach(btn => {
    btn.classList.toggle('on', el._active.has(btn.dataset.key));
  });
}
```

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/priority-chips.js plugins/taskmaster/viewer/css/screens/kanban.css
git commit -m "feat(viewer): components/priority-chips.js"
```

---

### Task 18: `phase-stepper.js` + CSS

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/phase-stepper.js`
- Modify: `plugins/taskmaster/viewer/css/screens/kanban.css`

- [ ] **Step 1: Append CSS**

Append to `plugins/taskmaster/viewer/css/screens/kanban.css`:

```css
/* ─────────── PHASE STEPPER ─────────── */
.kanban-phase-stepper {
  display: flex; align-items: stretch; gap: 0;
  background: var(--bg-panel);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  padding: 4px;
}
.kanban-phase-step {
  appearance: none; background: transparent; color: inherit; text-align: left;
  flex: 1; min-width: 0;
  padding: 8px var(--sp-5) 9px;
  cursor: pointer;
  border: 0;
  border-radius: var(--r-md);
  position: relative;
  display: flex; flex-direction: column; gap: 5px;
  transition: background var(--t-fast) var(--ease);
  font-family: var(--font-sans);
}
.kanban-phase-step:hover  { background: rgba(255,255,255,0.02); }
.kanban-phase-step.active { background: rgba(74,158,255,0.08); }
.kanban-phase-step.all-step,
.kanban-phase-step.orphans-step,
.kanban-phase-step.history-toggle { flex: 0 0 auto; min-width: 60px; }
.kanban-phase-step + .kanban-phase-step::before {
  content: ''; position: absolute; left: -1px; top: 14px; bottom: 14px; width: 1px;
  background: var(--border-soft);
}
.kanban-phase-step .ph-head { display: flex; align-items: baseline; gap: var(--sp-2); }
.kanban-phase-step .ph-name { font-size: var(--text-base); font-weight: 500; color: var(--ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.kanban-phase-step.done   .ph-name { color: var(--ink-2); }
.kanban-phase-step.future .ph-name { color: var(--ink-3); }
.kanban-phase-step .ph-stat { font-size: 9px; color: var(--ink-3); margin-left: auto; font-variant-numeric: tabular-nums; }
.kanban-phase-step .ph-bar  { height: 3px; background: #262932; border-radius: 2px; overflow: hidden; }
.kanban-phase-step .ph-bar > i { display: block; height: 100%; }
.kanban-phase-step.done   .ph-bar > i { background: var(--green); width: 100%; }
.kanban-phase-step.active .ph-bar > i { background: linear-gradient(90deg, var(--accent), var(--accent-2)); }
.kanban-phase-step.future .ph-bar > i { background: var(--border); width: 0%; }
.kanban-phase-step .check { color: var(--green); font-size: 10px; }
.kanban-phase-step .dot   { width: 6px; height: 6px; border-radius: 50%; background: var(--accent); animation: pulse 1.6s ease-in-out infinite; }
```

- [ ] **Step 2: Implement the component**

Create `plugins/taskmaster/viewer/js/components/phase-stepper.js`:

```js
// Phase stepper. Reads phases from backlog + a doneCount/total per phase.
//   phases: [{id, name, status: 'done'|'active'|'future', done, total}]
//   active: phase id (string), '__all__', or '__orphans__'
//   onSelect(phaseKey): callback when a cell is clicked.

export function renderPhaseStepper({ phases = [], active = '__all__', onSelect, showHistory = false }) {
  const wrap = document.createElement('div');
  wrap.className = 'kanban-phase-stepper';
  wrap.dataset.cmp = 'phase-stepper';

  // Optional history toggle (leftmost). Plan 2 wires only the toggle visual; behaviour is best-effort.
  const histBtn = document.createElement('button');
  histBtn.type = 'button';
  histBtn.className = 'kanban-phase-step history-toggle';
  histBtn.title = 'Show past phases';
  histBtn.innerHTML = `<div class="ph-head"><span class="ph-name">⤺</span></div>`;
  histBtn.addEventListener('click', () => {
    showHistory = !showHistory;
    wrap.querySelectorAll('.kanban-phase-step.done').forEach(el => {
      el.style.display = showHistory ? '' : 'none';
    });
  });
  wrap.appendChild(histBtn);

  // All-phases cell
  const allDone  = phases.reduce((s, p) => s + (p.done || 0), 0);
  const allTotal = phases.reduce((s, p) => s + (p.total || 0), 0);
  const allPct   = allTotal ? Math.round((allDone / allTotal) * 100) : 0;
  const allBtn = document.createElement('button');
  allBtn.type = 'button';
  allBtn.className = 'kanban-phase-step all-step' + (active === '__all__' ? ' active' : '');
  allBtn.dataset.key = '__all__';
  allBtn.innerHTML = `
    <div class="ph-head"><span class="ph-name">All phases</span><span class="ph-stat">${allDone}/${allTotal}</span></div>
    <div class="ph-bar"><i style="background:var(--ink-3); width:${allPct}%"></i></div>
  `;
  allBtn.addEventListener('click', () => onSelect && onSelect('__all__'));
  wrap.appendChild(allBtn);

  for (const ph of phases) {
    const cls = ph.status || 'future';
    const isActive = active === ph.id;
    const cell = document.createElement('button');
    cell.type = 'button';
    cell.className = 'kanban-phase-step ' + cls + (isActive ? ' active' : '');
    cell.dataset.key = ph.id;
    if (cls === 'done' && !showHistory) cell.style.display = 'none';
    const lead =
      cls === 'done'   ? '<span class="check">✓</span>'
    : cls === 'active' ? '<span class="dot"></span>'
    : '';
    const pct = (ph.total ? Math.round(((ph.done || 0) / ph.total) * 100) : 0);
    const statText =
      cls === 'active' ? `${ph.done || 0}/${ph.total || 0} · ${pct}%`
                       : `${ph.done || 0}/${ph.total || 0}`;
    const widthAttr = cls === 'active' ? ` style="width:${pct}%"` : '';
    cell.innerHTML = `
      <div class="ph-head">${lead}<span class="ph-name">${escapeHtml(ph.name || ph.id)}</span><span class="ph-stat">${statText}</span></div>
      <div class="ph-bar"><i${widthAttr}></i></div>
    `;
    cell.addEventListener('click', () => onSelect && onSelect(ph.id));
    wrap.appendChild(cell);
  }

  // Orphans cell (rightmost)
  const orphansBtn = document.createElement('button');
  orphansBtn.type = 'button';
  orphansBtn.className = 'kanban-phase-step orphans-step' + (active === '__orphans__' ? ' active' : '');
  orphansBtn.dataset.key = '__orphans__';
  orphansBtn.innerHTML = `<div class="ph-head"><span class="ph-name">Orphans</span></div><div class="ph-bar"><i></i></div>`;
  orphansBtn.addEventListener('click', () => onSelect && onSelect('__orphans__'));
  wrap.appendChild(orphansBtn);

  return wrap;
}

function escapeHtml(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
```

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/phase-stepper.js plugins/taskmaster/viewer/css/screens/kanban.css
git commit -m "feat(viewer): components/phase-stepper.js"
```

---

### Task 19: `epic-chips.js` + CSS

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/epic-chips.js`
- Modify: `plugins/taskmaster/viewer/css/screens/kanban.css`

- [ ] **Step 1: Append CSS**

Append to `plugins/taskmaster/viewer/css/screens/kanban.css`:

```css
/* ─────────── EPIC CHIPS ROW ─────────── */
.kanban-epic-row {
  display: flex; align-items: center; gap: var(--sp-2); flex-wrap: wrap;
  padding: var(--sp-2) var(--sp-4);
  background: var(--bg-panel);
  border: 1px solid var(--border);
  border-radius: var(--r-md);
}
.kanban-epic-row .label {
  font-size: 9px; text-transform: uppercase; letter-spacing: 0.08em;
  color: var(--ink-3);
  margin-right: 4px;
}
.kanban-epic-chip {
  appearance: none; background: var(--bg-card);
  border: 1px solid var(--border); color: var(--ink-2);
  display: inline-flex; align-items: center; gap: 5px;
  padding: 3px 9px; font-size: var(--text-sm);
  border-radius: var(--r-sm); cursor: pointer;
  font-family: var(--font-sans);
  transition: color var(--t-fast) var(--ease), border-color var(--t-fast) var(--ease);
}
.kanban-epic-chip:hover { border-color: var(--ink-3); color: var(--ink); }
.kanban-epic-chip .marker { width: 6px; height: 6px; border-radius: 50%; background: var(--ec, var(--ink-3)); }
.kanban-epic-chip.on {
  background: var(--ec-soft, rgba(74,158,255,0.12));
  border-color: var(--ec, var(--accent));
  color: var(--ec, var(--accent));
}
.kanban-epic-chip .count { color: inherit; opacity: 0.75; font-size: 10px; margin-left: 2px; font-variant-numeric: tabular-nums; }

.kanban-epic-row .right { margin-left: auto; display: flex; align-items: center; gap: var(--sp-3); font-size: var(--text-sm); color: var(--ink-3); }
.kanban-epic-row .filter-count {
  background: rgba(74,158,255,0.15); color: var(--accent);
  padding: 1px 6px; border-radius: 8px; font-size: 10px; font-family: var(--font-mono);
}
```

- [ ] **Step 2: Implement the component**

Create `plugins/taskmaster/viewer/js/components/epic-chips.js`:

```js
import { epicCssVar } from '../lib/epics.js';

/**
 * epics: [{id, name, color, count}]
 * active: array of epic ids (strings) selected
 */
export function renderEpicChips({ epics = [], active = [], filterCount = 0, onToggle, onClear }) {
  const wrap = document.createElement('div');
  wrap.className = 'kanban-epic-row';
  wrap.dataset.cmp = 'epic-chips';
  const set = new Set(active);

  const lbl = document.createElement('span');
  lbl.className = 'label';
  lbl.textContent = 'Epic';
  wrap.appendChild(lbl);

  // "All" chip → clears the epics filter only (other filters untouched).
  const all = document.createElement('button');
  all.type = 'button';
  all.className = 'kanban-epic-chip' + (set.size === 0 ? ' on' : '');
  all.dataset.key = '__all__';
  all.textContent = 'All';
  all.addEventListener('click', () => {
    if (onToggle) onToggle([]);
  });
  wrap.appendChild(all);

  for (const ep of epics) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'kanban-epic-chip' + (set.has(ep.id) ? ' on' : '');
    btn.dataset.key = ep.id;
    btn.setAttribute('style', epicCssVar(ep.color).replace(/--epic:/g, '--ec:').replace(/--epic-soft:/g, '--ec-soft:'));
    btn.innerHTML = `<span class="marker"></span>${escapeHtml(ep.name || ep.id)}<span class="count">${ep.count || 0}</span>`;
    btn.addEventListener('click', () => {
      if (set.has(ep.id)) set.delete(ep.id);
      else                set.add(ep.id);
      if (onToggle) onToggle([...set]);
    });
    wrap.appendChild(btn);
  }

  const right = document.createElement('div');
  right.className = 'right';
  if (filterCount > 0) {
    const fc = document.createElement('span');
    fc.className = 'filter-count';
    fc.textContent = `${filterCount} filters`;
    right.appendChild(fc);

    const clr = document.createElement('span');
    clr.className = 'kanban-reset-link';
    clr.textContent = 'clear all';
    clr.addEventListener('click', () => onClear && onClear());
    right.appendChild(clr);
  }
  wrap.appendChild(right);

  return wrap;
}

function escapeHtml(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
```

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/epic-chips.js plugins/taskmaster/viewer/css/screens/kanban.css
git commit -m "feat(viewer): components/epic-chips.js"
```

---

### Task 20: Group-by + sort dropdowns (popover-free)

**Files:**
- Modify: `plugins/taskmaster/viewer/css/screens/kanban.css`

(The dropdowns are inline-rendered: a `<select>` styled as a button — no popover plumbing needed in Plan 2.)

- [ ] **Step 1: Append CSS for the styled selects**

Append to `plugins/taskmaster/viewer/css/screens/kanban.css`:

```css
/* ─────────── GROUP / SORT DROPDOWNS ─────────── */
.kanban-select {
  appearance: none;
  -webkit-appearance: none;
  background: var(--bg-card) url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'><path d='M1 1l4 4 4-4' stroke='%23bfc4cc' stroke-width='1.2' fill='none' stroke-linecap='round'/></svg>") no-repeat right 8px center;
  border: 1px solid var(--border); color: var(--ink-2);
  font-size: var(--text-sm);
  font-family: var(--font-sans);
  padding: 4px 22px 4px var(--sp-3);
  border-radius: var(--r-md);
  cursor: pointer;
  outline: none;
}
.kanban-select:hover { color: var(--ink); border-color: var(--border-strong); }
.kanban-select:focus { border-color: var(--accent); }
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/css/screens/kanban.css
git commit -m "feat(viewer): styled <select> for kanban group/sort dropdowns"
```

---

### Task 21: Board surface + columns CSS

**Files:**
- Modify: `plugins/taskmaster/viewer/css/screens/kanban.css`

- [ ] **Step 1: Append CSS**

Append to `plugins/taskmaster/viewer/css/screens/kanban.css`:

```css
/* ─────────── BOARD SURFACE + COLUMNS ─────────── */
.kanban-board {
  position: relative;
  background: var(--kanban-board-bg-grad);
  border: 1px solid var(--kanban-board-border);
  border-radius: var(--r-lg);
  padding: var(--sp-4) var(--sp-5) var(--sp-5);
  box-shadow: 0 0 0 1px rgba(74,158,255,0.04) inset, 0 8px 30px rgba(0,0,0,0.4);
}
.kanban-board::before {
  content: ''; position: absolute; inset: 0; pointer-events: none;
  border-radius: var(--r-lg);
  background-image: linear-gradient(rgba(255,255,255,0.012) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(255,255,255,0.012) 1px, transparent 1px);
  background-size: 12px 12px;
  -webkit-mask-image: radial-gradient(120% 80% at 50% 0%, #000 30%, transparent 80%);
          mask-image: radial-gradient(120% 80% at 50% 0%, #000 30%, transparent 80%);
}
.kanban-board-grid {
  position: relative;
  display: grid; gap: var(--sp-3);
}
.kanban-board-grid.status { grid-template-columns: repeat(5, 1fr); }
.kanban-board-grid.phase  { grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); }
.kanban-board-grid.epic   { grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }

.kanban-col {
  background: var(--bg-board-col);
  border: 1px solid rgba(74,158,255,0.06);
  border-radius: var(--r-md);
  padding: var(--sp-3);
  min-height: 340px;
}
.kanban-col-head {
  display: flex; align-items: center; gap: 5px;
  margin-bottom: var(--sp-3);
  padding-bottom: 5px;
  border-bottom: 1px solid var(--border-soft);
}
.kanban-col-head .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--ink-3); }
.kanban-col-head .lbl { font-size: var(--text-sm); font-weight: 500; flex: 1; }
.kanban-col-head .tnum { color: var(--ink-3); font-size: var(--text-xs); font-variant-numeric: tabular-nums; }
.kanban-col-empty { text-align: center; color: var(--ink-3); font-size: var(--text-sm); padding: 30px 0; }

.kanban-col-head.blocked     .dot { background: var(--red); }
.kanban-col-head.todo        .dot { background: var(--ink-3); }
.kanban-col-head.in_progress .dot { background: var(--accent); }
.kanban-col-head.in_review   .dot { background: var(--amber); }
.kanban-col-head.done        .dot { background: var(--green); }
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/css/screens/kanban.css
git commit -m "feat(viewer): board surface + status/phase/epic column grids"
```

---

### Task 22: Density-toggle CSS for the page header

**Files:**
- Modify: `plugins/taskmaster/viewer/css/screens/kanban.css`

- [ ] **Step 1: Append CSS**

Append to `plugins/taskmaster/viewer/css/screens/kanban.css`:

```css
/* ─────────── DENSITY TOGGLE (icon segmented) ─────────── */
.kanban-density {
  display: inline-flex; gap: 0;
  border: 1px solid var(--border); border-radius: var(--r-md);
  background: var(--bg-card);
  overflow: hidden;
}
.kanban-density button {
  appearance: none; background: transparent; border: 0; color: var(--ink-3);
  padding: 4px var(--sp-3); font-size: var(--text-sm); cursor: pointer;
  font-family: var(--font-sans);
}
.kanban-density button + button { border-left: 1px solid var(--border); }
.kanban-density button.on {
  background: rgba(74,158,255,0.12);
  color: var(--accent);
}
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/css/screens/kanban.css
git commit -m "feat(viewer): density-toggle styles"
```

---

## M6 — Kanban Screen Integration

### Task 23: Kanban screen — header skeleton

**Files:**
- Modify: `plugins/taskmaster/viewer/js/screens/kanban.js` (replaces stub)

- [ ] **Step 1: Replace the stub with the screen module skeleton**

Open `plugins/taskmaster/viewer/js/screens/kanban.js` and replace its **entire contents** with:

```js
// Kanban screen — full implementation.
// Mounts the page-head, phase stepper, epic chips, board surface, and auto-mode strip.
// Subscribes to store(backlog), store(autoState), and store(prefs); all writes go through prefs.patch(...).

import { renderCard }                        from '../components/card.js';
import { renderAutoModeStrip,
         updateAutoModeStrip,
         destroyAutoModeStrip }              from '../components/auto-mode-strip.js';
import { renderPriorityChips,
         updatePriorityChips }               from '../components/priority-chips.js';
import { renderPhaseStepper }                from '../components/phase-stepper.js';
import { renderEpicChips }                   from '../components/epic-chips.js';
import { applyFilters, sortTasks, groupTasks, STATUS_LABELS } from '../lib/filters.js';
import { assignEpicColors }                  from '../lib/epics.js';

export const meta = { title: 'Kanban', icon: '▦', sidebarKey: 'kanban' };

const DEFAULT_FILTERS = {
  priorities: [],
  epics: [],
  phase: '__all__',
  group_by: 'status',
  sort: { by: 'priority', dir: 'desc' },
  search: '',
};

export async function mount(root, { store, prefs }) {
  // ──────────────────────────────────────────────────────────────
  // Local state — sourced from prefs but mutated by UI events.
  // Persisted via prefs.patch({...}) (debounced).
  // ──────────────────────────────────────────────────────────────
  const persisted = (store.getPrefs() && store.getPrefs().kanban && store.getPrefs().kanban.filters) || {};
  const state = {
    filters: { ...DEFAULT_FILTERS, ...persisted },
    density: (store.getPrefs() && store.getPrefs().card_density) || 'full',
  };

  // Layout
  const page = document.createElement('div');
  page.className = 'kanban-page';

  // 1) Auto-mode strip (above page header, hidden when no run)
  const strip = renderAutoModeStrip({
    autoState: store.getAutoState(),
    backlog:   store.getBacklog(),
    onViewAll: () => { location.hash = '#/auto'; },
  });
  page.appendChild(strip);

  // 2) Page header
  const head = document.createElement('div');
  head.className = 'kanban-head';

  const title = document.createElement('span');
  title.className = 'title';
  title.textContent = 'Kanban';
  head.appendChild(title);

  const subcount = document.createElement('span');
  subcount.className = 'subcount';
  subcount.textContent = '… tasks';
  head.appendChild(subcount);

  // Search
  const search = document.createElement('div');
  search.className = 'kanban-search';
  search.innerHTML = `<span class="icon">⌕</span><input placeholder="Find by title, id, or branch…" /><span class="cmp-kbd">⌘K</span>`;
  const searchInput = search.querySelector('input');
  searchInput.value = state.filters.search || '';
  let searchTimer = null;
  searchInput.addEventListener('input', () => {
    if (searchTimer) clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      state.filters.search = searchInput.value;
      paint(); savePrefs();
    }, 180);
  });
  head.appendChild(search);

  // Priority chips
  const pri = renderPriorityChips({
    active: state.filters.priorities,
    onToggle: (next) => { state.filters.priorities = next; paint(); savePrefs(); },
  });
  head.appendChild(pri);

  const right = document.createElement('div');
  right.className = 'kanban-head-right';

  // Density toggle
  const dens = document.createElement('div');
  dens.className = 'kanban-density';
  for (const k of ['minimal', 'full']) {
    const b = document.createElement('button');
    b.type = 'button';
    b.dataset.key = k;
    b.textContent = k === 'minimal' ? '▤ minimal' : '▦ full';
    if (state.density === k) b.classList.add('on');
    b.addEventListener('click', () => {
      state.density = k;
      dens.querySelectorAll('button').forEach(x => x.classList.toggle('on', x.dataset.key === k));
      paint(); prefs.patch({ card_density: k });
    });
    dens.appendChild(b);
  }
  right.appendChild(dens);

  // Group dropdown
  const group = document.createElement('select');
  group.className = 'kanban-select';
  for (const opt of [['status','Group: Status'],['phase','Group: Phase'],['epic','Group: Epic']]) {
    const o = document.createElement('option');
    o.value = opt[0]; o.textContent = opt[1];
    if (state.filters.group_by === opt[0]) o.selected = true;
    group.appendChild(o);
  }
  group.addEventListener('change', () => { state.filters.group_by = group.value; paint(); savePrefs(); });
  right.appendChild(group);

  // Sort dropdown
  const sort = document.createElement('select');
  sort.className = 'kanban-select';
  const SORT_OPTS = [
    ['priority:desc', 'Sort: priority ↓'],
    ['priority:asc',  'Sort: priority ↑'],
    ['size:desc',     'Sort: size ↓'],
    ['size:asc',      'Sort: size ↑'],
    ['created:desc',  'Sort: created ↓'],
    ['created:asc',   'Sort: created ↑'],
    ['started:desc',  'Sort: started ↓'],
    ['started:asc',   'Sort: started ↑'],
    ['touched:desc',  'Sort: touched ↓'],
    ['touched:asc',   'Sort: touched ↑'],
  ];
  for (const [v, label] of SORT_OPTS) {
    const o = document.createElement('option');
    o.value = v; o.textContent = label;
    const cur = `${state.filters.sort?.by || 'priority'}:${state.filters.sort?.dir || 'desc'}`;
    if (v === cur) o.selected = true;
    sort.appendChild(o);
  }
  sort.addEventListener('change', () => {
    const [by, dir] = sort.value.split(':');
    state.filters.sort = { by, dir };
    paint(); savePrefs();
  });
  right.appendChild(sort);

  // + Task button (Plan 2 stub: navigates to a hash that future plans will handle).
  const addBtn = document.createElement('button');
  addBtn.className = 'kanban-add-btn';
  addBtn.type = 'button';
  addBtn.textContent = '＋ Task';
  addBtn.addEventListener('click', () => { location.hash = '#/task/new'; });
  right.appendChild(addBtn);

  head.appendChild(right);
  page.appendChild(head);

  // 3) Phase stepper container (rendered in paint())
  const stepperHost = document.createElement('div');
  page.appendChild(stepperHost);

  // 4) Epic chips container
  const epicHost = document.createElement('div');
  page.appendChild(epicHost);

  // 5) Board surface
  const board = document.createElement('div');
  board.className = 'kanban-board';
  const boardGrid = document.createElement('div');
  boardGrid.className = 'kanban-board-grid';
  board.appendChild(boardGrid);
  page.appendChild(board);

  root.appendChild(page);

  // ──────────────────────────────────────────────────────────────
  // PAINT: full repaint from current state + store data.
  // ──────────────────────────────────────────────────────────────
  function paint() {
    const backlog = store.getBacklog() || { tasks: [], epics: [], phases: [] };
    const tasks   = Array.isArray(backlog.tasks) ? backlog.tasks : [];
    const epicsArr  = Array.isArray(backlog.epics) ? backlog.epics : [];
    const phasesArr = Array.isArray(backlog.phases) ? backlog.phases : [];
    const epicColors = assignEpicColors(epicsArr);

    // 1) Apply filters
    const filtered = applyFilters(tasks, state.filters);
    const sorted   = sortTasks(filtered, state.filters.sort);

    // 2) Subcount
    subcount.textContent = `${tasks.length} tasks · ${filtered.length} visible`;

    // 3) Phase stepper data
    const phaseRows = phasesArr.map(ph => {
      const total = tasks.filter(t => t.phase === ph.id).length;
      const done  = tasks.filter(t => t.phase === ph.id && t.status === 'done').length;
      let stat = (ph.status || '').toLowerCase();
      if (!stat) stat = (done >= total && total > 0) ? 'done' : (done > 0 ? 'active' : 'future');
      return { id: ph.id, name: ph.name || ph.id, status: stat, done, total };
    });
    stepperHost.replaceChildren(renderPhaseStepper({
      phases: phaseRows,
      active: state.filters.phase,
      onSelect: (key) => { state.filters.phase = key; paint(); savePrefs(); },
    }));

    // 4) Epic chips data
    const epicRows = epicsArr.map(ep => ({
      id:    ep.id,
      name:  ep.name || ep.id,
      color: epicColors[ep.id],
      count: tasks.filter(t => t.epic === ep.id).length,
    }));
    const filterCount =
      state.filters.priorities.length +
      state.filters.epics.length +
      (state.filters.phase && state.filters.phase !== '__all__' ? 1 : 0) +
      (state.filters.search ? 1 : 0);
    epicHost.replaceChildren(renderEpicChips({
      epics: epicRows,
      active: state.filters.epics,
      filterCount,
      onToggle: (next) => { state.filters.epics = next; paint(); savePrefs(); },
      onClear:  ()    => { state.filters = { ...DEFAULT_FILTERS }; searchInput.value = ''; updatePriorityChips(pri, { active: [] }); paint(); savePrefs(); },
    }));

    // 5) Group + render columns
    const groupKeyArg = state.filters.group_by === 'phase' ? phasesArr.map(p => p.id) : undefined;
    const groups = groupTasks(sorted, state.filters.group_by, groupKeyArg);
    boardGrid.className = 'kanban-board-grid ' + state.filters.group_by;
    boardGrid.replaceChildren();

    for (const g of groups) {
      const col = document.createElement('div');
      col.className = 'kanban-col';
      const head = document.createElement('div');
      head.className = 'kanban-col-head ' + (state.filters.group_by === 'status' ? g.key : '');
      head.innerHTML = `<span class="dot"></span><span class="lbl">${escapeHtml(state.filters.group_by === 'status' ? STATUS_LABELS[g.key] : g.label)}</span><span class="tnum">${g.tasks.length}</span>`;
      col.appendChild(head);

      if (!g.tasks.length) {
        const empty = document.createElement('div');
        empty.className = 'kanban-col-empty';
        empty.textContent = '— filtered out —';
        col.appendChild(empty);
      } else {
        for (const t of g.tasks) {
          col.appendChild(renderCard({
            task: t,
            density: state.density,
            epicColors,
            autoState: store.getAutoState(),
            groupBy: state.filters.group_by,
          }));
        }
      }
      boardGrid.appendChild(col);
    }
  }

  // Persist filter changes via debounced prefs.patch
  function savePrefs() {
    prefs.patch({ kanban: { filters: state.filters } });
  }

  // ──────────────────────────────────────────────────────────────
  // Subscriptions: backlog & autoState
  // ──────────────────────────────────────────────────────────────
  const unsubBacklog = store.subscribe('backlog', () => paint());
  const unsubAuto    = store.subscribe('autoState', (auto) => {
    updateAutoModeStrip(strip, {
      autoState: auto,
      backlog:   store.getBacklog(),
      onViewAll: () => { location.hash = '#/auto'; },
    });
    paint(); // re-render cards so live-blocks attach/detach
  });

  // Initial paint
  paint();

  // Cleanup
  return () => {
    if (searchTimer) clearTimeout(searchTimer);
    unsubBacklog();
    unsubAuto();
    destroyAutoModeStrip(strip);
  };
}

function escapeHtml(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/screens/kanban.js
git commit -m "feat(viewer): kanban screen — full integration of header, stepper, chips, board, strip"
```

---

### Task 24: Manual smoke — open `/v3#/kanban` against a fixture backlog

(Informational; no commit.)

- [ ] **Step 1: Create a fixture backlog**

In `C:\Users\gruku\Files\Claude\claude-tools` root (or any temp dir), edit/create a `backlog.yaml` containing at minimum:

```yaml
meta:
  project: viewer-redesign-fixture
phases:
  - {id: P-01, name: Foundations, status: done}
  - {id: P-02, name: Migration,   status: done}
  - {id: P-03, name: Visual Redesign, status: active}
  - {id: P-04, name: Polish,      status: future}
  - {id: P-05, name: Launch,      status: future}
epics:
  - {id: viewer-redesign,      name: viewer-redesign}
  - {id: narrative-continuity, name: narrative-continuity}
  - {id: filter-bar,           name: filter-bar}
tasks:
  - {id: v3-009, title: "Wire viewer to v3 schema",       status: in_progress, priority: critical, estimate: L, phase: P-03, epic: viewer-redesign,      branch: "feat/wire-viewer", started: "2026-04-26T10:00:00Z"}
  - {id: v3-011, title: "Lesson digest sidebar",          status: in_progress, priority: high,     estimate: M, phase: P-03, epic: viewer-redesign,      branch: "feat/lesson-digest"}
  - {id: v3-012, title: "Issue panel",                    status: in_review,   priority: high,     estimate: M, phase: P-03, epic: narrative-continuity, branch: "feat/issue-panel"}
  - {id: v3-014, title: "Auto-mode status indicator",     status: todo,        priority: high,     estimate: M, phase: P-03, epic: viewer-redesign,      branch: "feat/auto-mode-strip"}
  - {id: v3-021, title: "Hook compact recap on PreCompact", status: blocked,   priority: high,     estimate: S, phase: P-03, epic: narrative-continuity}
```

- [ ] **Step 2: Boot the server from that working dir**

```bash
python -c "from backlog_server import _make_server; s, p = _make_server(host='127.0.0.1', port=0); print(f'http://127.0.0.1:{p}/v3#/kanban'); s.serve_forever()"
```

- [ ] **Step 3: Open the URL**

Expected:
- Page header: "Kanban · 5 tasks · 5 visible · search · priority chips · density · group · sort · ＋ Task"
- Phase stepper with 5 phases (Foundations done, Visual Redesign active with pulse)
- Epic chip row (viewer-redesign 3, narrative-continuity 2, filter-bar 0)
- Board with 5 status columns
- Auto-mode strip is hidden (no `state.json`).

- [ ] **Step 4: Drop a state file and refresh**

```bash
mkdir -p .taskmaster/auto
echo '{"mode":"running","target":"v3-009","started_at":"2026-04-26T10:00:00Z","cursor":{"task_id":"v3-009","stage":"IMPLEMENT","model":"sonnet"},"completed":[],"pending":["v3-011"],"failed":[],"models":{},"config":{}}' > .taskmaster/auto/state.json
```

Reload. Expected: strip appears at top with one run; the v3-009 card carries a live block.

If anything fails, debug before continuing.

---

### Task 25: Persist density toggle round-trip via Playwright (TDD)

(Tests deferred to M7. Manual confirmation only here — no commit.)

- [ ] **Step 1: Toggle density to "minimal" in the browser**

- [ ] **Step 2: Reload the page**

Expected: density-toggle still on "minimal", filters persist (search box still has its value).

If not, inspect Network tab for a `PUT /api/viewer/prefs` after each change. If the patch didn't go out, debug `prefs.patch` in `main.js` and confirm the test expectations from Plan 1's Task 25 still hold.

---

### Task 26: Group-by phase + epic visual sanity

(Informational; no commit.)

- [ ] **Step 1: Switch group dropdown to Phase**

Expected: columns are P-01 / P-02 / P-03 / P-04 / P-05 / Orphans, cards distributed by phase, status pill renders inside each card's chip row.

- [ ] **Step 2: Switch group dropdown to Epic**

Expected: columns are viewer-redesign / narrative-continuity / filter-bar / — no epic — (if any). Status pill still renders.

If status pill is missing or rendering when group is `status`, debug `card.js` `groupBy` branch.

---

### Task 27: Prefs reset behavior

(Informational; no commit.)

- [ ] **Step 1: Apply a few filters, hit "clear all"**

Expected: priorities, epics, phase, search, group, sort all reset to defaults. Filter count chip disappears.

---

### Task 28: Click-to-copy IDs and branches

(Informational; no commit.)

- [ ] **Step 1: Click an ID on a card**

Expected: green flash on the chip with " copied" label for ~1.2s; clipboard contains the id.

- [ ] **Step 2: Click a branch in a card footer**

Expected: same green flash; clipboard contains the branch.

---

## M7 — Tests + Polish

### Task 29: Playwright config addition (kanban-aware fixture)

**Files:**
- Create: `plugins/taskmaster/viewer/tests/fixtures/kanban.yaml`
- Modify: `plugins/taskmaster/viewer/tests/playwright.config.js`

- [ ] **Step 1: Write the fixture file**

Create `plugins/taskmaster/viewer/tests/fixtures/kanban.yaml` with the same content as Task 24 Step 1.

- [ ] **Step 2: Add a webServer to playwright.config.js**

Open `plugins/taskmaster/viewer/tests/playwright.config.js`. Replace the entire file with:

```js
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: '.',
  testMatch: /.*\.spec\.js/,
  timeout: 20_000,
  retries: 0,
  webServer: {
    // Start backlog_server in a fixture cwd (kanban.yaml as backlog).
    command: 'node fixtures/start_server.js',
    url:     'http://127.0.0.1:8765/api/identity',
    reuseExistingServer: !process.env.CI,
    timeout: 20_000,
  },
  use: {
    baseURL: process.env.VIEWER_BASE_URL || 'http://127.0.0.1:8765',
    headless: true,
  },
});
```

- [ ] **Step 3: Write the server-launcher node helper**

Create `plugins/taskmaster/viewer/tests/fixtures/start_server.js`:

```js
// Boot the python backlog_server in a temp dir seeded with the kanban fixture.
import { mkdtempSync, mkdirSync, copyFileSync, writeFileSync } from 'node:fs';
import { tmpdir }   from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawn } from 'node:child_process';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PLUGIN_DIR = join(__dirname, '..', '..', '..');  // plugins/taskmaster
const TMP = mkdtempSync(join(tmpdir(), 'tm-viewer-'));
mkdirSync(join(TMP, '.taskmaster'), { recursive: true });
copyFileSync(join(__dirname, 'kanban.yaml'), join(TMP, 'backlog.yaml'));

const py = spawn(
  process.platform === 'win32' ? 'python' : 'python3',
  ['-c',
    `import sys; sys.path.insert(0, r'${PLUGIN_DIR.replace(/\\/g, '\\\\')}'); ` +
    `import os; os.chdir(r'${TMP.replace(/\\/g, '\\\\')}'); ` +
    `from backlog_server import _make_server; ` +
    `s, p = _make_server(host='127.0.0.1', port=8765); ` +
    `print(f'serving on {p}', flush=True); ` +
    `s.serve_forever()`,
  ],
  { stdio: 'inherit' },
);

process.on('SIGTERM', () => py.kill('SIGTERM'));
process.on('exit',    () => py.kill('SIGTERM'));
```

- [ ] **Step 4: Commit**

```bash
git add plugins/taskmaster/viewer/tests/fixtures/kanban.yaml plugins/taskmaster/viewer/tests/fixtures/start_server.js plugins/taskmaster/viewer/tests/playwright.config.js
git commit -m "test(viewer): kanban fixture + node-launched python webServer"
```

---

### Task 30: Playwright smoke for kanban

**Files:**
- Create: `plugins/taskmaster/viewer/tests/kanban.spec.js`

- [ ] **Step 1: Write the spec**

Create `plugins/taskmaster/viewer/tests/kanban.spec.js`:

```js
import { test, expect } from '@playwright/test';

async function gotoKanban(page) {
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));
  page.on('console', msg => {
    if (msg.type() === 'error') errors.push(msg.text());
  });
  await page.goto('/v3#/kanban');
  await expect(page.locator('#page-title')).toHaveText('Kanban');
  await expect(page.locator('.kanban-page')).toBeVisible();
  return errors;
}

test.describe('Kanban screen smoke', () => {
  test('renders header, stepper, epic chips, and 5 status columns', async ({ page }) => {
    const errors = await gotoKanban(page);
    await expect(page.locator('.kanban-head .title')).toHaveText('Kanban');
    await expect(page.locator('.kanban-search input')).toBeVisible();
    await expect(page.locator('.kanban-pri-tog')).toHaveCount(4);
    await expect(page.locator('.kanban-phase-stepper')).toBeVisible();
    await expect(page.locator('.kanban-epic-row')).toBeVisible();
    await expect(page.locator('.kanban-board-grid.status > .kanban-col')).toHaveCount(5);
    expect(errors).toEqual([]);
  });

  test('search filters the board', async ({ page }) => {
    await gotoKanban(page);
    await page.fill('.kanban-search input', 'lesson');
    // debounced 180ms
    await page.waitForTimeout(300);
    const visibleCards = page.locator('.card-task');
    await expect(visibleCards).toHaveCount(1);
    await expect(visibleCards.first().locator('.card-id .label-text')).toHaveText('v3-011');
  });

  test('priority chips toggle and persist', async ({ page }) => {
    await gotoKanban(page);
    await page.locator('.kanban-pri-tog.critical').click();
    await page.waitForTimeout(500); // prefs debounce + fetch
    await expect(page.locator('.card-task')).toHaveCount(1);
    await expect(page.locator('.card-id .label-text')).toHaveText('v3-009');

    await page.reload();
    await expect(page.locator('.kanban-pri-tog.critical')).toHaveClass(/on/);
    await expect(page.locator('.card-task')).toHaveCount(1);

    // Reset for other tests
    await page.locator('.kanban-pri-tog.critical').click();
    await page.waitForTimeout(500);
  });

  test('group-by phase repaints columns and shows status pill on cards', async ({ page }) => {
    await gotoKanban(page);
    await page.selectOption('.kanban-head-right .kanban-select:nth-of-type(1)', 'phase');
    await expect(page.locator('.kanban-board-grid.phase')).toBeVisible();
    await expect(page.locator('.card-task .card-status-pill').first()).toBeVisible();

    // restore
    await page.selectOption('.kanban-head-right .kanban-select:nth-of-type(1)', 'status');
    await page.waitForTimeout(500);
  });

  test('phase stepper click filters board to that phase', async ({ page }) => {
    await gotoKanban(page);
    // Click the active step (Visual Redesign — id P-03).
    await page.locator('.kanban-phase-step[data-key="P-03"]').click();
    await expect(page.locator('.kanban-phase-step[data-key="P-03"]')).toHaveClass(/active/);
    // All 5 fixture tasks live in P-03, so card count holds steady.
    await expect(page.locator('.card-task')).toHaveCount(5);
    // Reset
    await page.locator('.kanban-phase-step[data-key="__all__"]').click();
  });

  test('density toggle switches to minimal and back', async ({ page }) => {
    await gotoKanban(page);
    await page.locator('.kanban-density button[data-key="minimal"]').click();
    await expect(page.locator('.card-task.minimal').first()).toBeVisible();
    await expect(page.locator('.card-task.full')).toHaveCount(0);
    await page.locator('.kanban-density button[data-key="full"]').click();
    await page.waitForTimeout(500);
  });

  test('id click-to-copy flashes green', async ({ page, browserName }) => {
    test.skip(browserName === 'webkit', 'clipboard perms differ on webkit headless');
    await gotoKanban(page);
    const id = page.locator('.card-id').first();
    await id.click();
    await expect(id).toHaveClass(/cmp-flash-copied/);
  });

  test('auto-mode strip appears when state.json is present', async ({ page, request }) => {
    await gotoKanban(page);
    // The fixture cwd has no state.json → strip is hidden.
    await expect(page.locator('.kanban-strip')).toBeHidden();
    // We can't write state.json from the browser, so assert the hidden state only;
    // helper-level coverage of the strip is in the python tests for /api/auto/state.
  });
});
```

- [ ] **Step 2: Run the spec**

Run from `plugins/taskmaster/viewer/tests/`:

```bash
npx playwright test kanban.spec.js
```

Expected: 8 PASS (one may skip on webkit). If npm/playwright is unavailable, document and skip — Python tests still cover endpoint behavior.

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/tests/kanban.spec.js
git commit -m "test(viewer): playwright smoke for kanban (header, search, filters, density, copy)"
```

---

### Task 31: Auto-mode strip Playwright smoke (state.json injected by node fixture)

**Files:**
- Modify: `plugins/taskmaster/viewer/tests/kanban.spec.js`
- Modify: `plugins/taskmaster/viewer/tests/fixtures/start_server.js`

- [ ] **Step 1: Update the fixture launcher to expose the temp dir**

Open `plugins/taskmaster/viewer/tests/fixtures/start_server.js`. Replace the line `print(f'serving on {p}', flush=True);` inside the python `-c` arg with:

```
print(f'TMPDIR=${TMP.replace(/\\/g, '\\\\')}', flush=True);
print(f'serving on {p}', flush=True);
```

Then before the `process.on('SIGTERM', ...)` line, add:

```js
// Expose tempdir so specs can write state.json into it.
process.env.TM_FIXTURE_TMP = TMP;
writeFileSync(join(__dirname, '.last-tmpdir'), TMP);
```

- [ ] **Step 2: Append the strip test**

Append to `plugins/taskmaster/viewer/tests/kanban.spec.js`:

```js
import { readFileSync, writeFileSync, mkdirSync, rmSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));

function getFixtureTmp() {
  const p = join(__dirname, 'fixtures', '.last-tmpdir');
  return existsSync(p) ? readFileSync(p, 'utf-8').trim() : null;
}

test('strip renders + ticks when state.json is present', async ({ page }) => {
  const tmp = getFixtureTmp();
  test.skip(!tmp, 'fixture tmpdir not available');

  const autoDir = join(tmp, '.taskmaster', 'auto');
  mkdirSync(autoDir, { recursive: true });
  const stateFile = join(autoDir, 'state.json');
  writeFileSync(stateFile, JSON.stringify({
    mode: 'running',
    target: 'v3-009',
    started_at: new Date(Date.now() - 90_000).toISOString(),
    cursor: { task_id: 'v3-009', stage: 'IMPLEMENT', model: 'sonnet' },
    completed: [], pending: ['v3-011'], failed: [], models: {}, config: {},
  }));

  await page.goto('/v3#/kanban');
  // Auto-state polls every 3s; allow time for the first cycle.
  await expect(page.locator('.kanban-strip')).toBeVisible({ timeout: 6000 });
  await expect(page.locator('.kanban-strip-title')).toContainText('Auto-mode · 1 running');
  await expect(page.locator('.kanban-strip-spinner')).toBeVisible();
  await expect(page.locator('.kanban-strip-run')).toHaveCount(1);
  await expect(page.locator('.kanban-strip-run .id')).toHaveText('v3-009');
  // The v3-009 card should have a live block.
  await expect(page.locator('.card-task[data-task-id="v3-009"] .card-live')).toBeVisible();

  // Cleanup
  rmSync(stateFile, { force: true });
});
```

- [ ] **Step 3: Run the spec**

Run from `plugins/taskmaster/viewer/tests/`:

```bash
npx playwright test kanban.spec.js -g "strip renders"
```

Expected: PASS (or skip if fixture tmpdir not exposed).

- [ ] **Step 4: Commit**

```bash
git add plugins/taskmaster/viewer/tests/kanban.spec.js plugins/taskmaster/viewer/tests/fixtures/start_server.js
git commit -m "test(viewer): strip + per-card live block playwright coverage"
```

---

### Task 32: Run all server + unit + smoke tests in sequence

(Informational — verifies the plan's test discipline holds end-to-end.)

- [ ] **Step 1: Server tests**

Run: `python -m pytest plugins/taskmaster/tests/test_server_auto_state.py -v`
Expected: 5 PASS.

- [ ] **Step 2: Node unit tests**

Run from project root:

```bash
node --test plugins/taskmaster/viewer/tests/unit/time.test.js plugins/taskmaster/viewer/tests/unit/epics.test.js plugins/taskmaster/viewer/tests/unit/filters.test.js
```

Expected: All tests pass — 7 + 6 + 12 = 25 PASS.

- [ ] **Step 3: Playwright**

Run from `plugins/taskmaster/viewer/tests/`:

```bash
npx playwright test
```

Expected: kanban.spec.js + Plan 1's smoke.spec.js all pass.

- [ ] **Step 4: Plan-1 regression**

Run: `python -m pytest plugins/taskmaster/tests/test_server_api.py -v`
Expected: All pass (Plan 1's existing tests still green).

If anything fails, debug before completing the plan.

---

### Task 33: Final integration smoke + plan-level verification commit

**Files:**
- (no source changes — plan completion marker)

- [ ] **Step 1: Verify the spec coverage matrix**

Walk through each section of the spec and confirm:

| Spec § | Requirement | Implemented in |
|---|---|---|
| §3.3 | Strip + cards (light, no boxed bg) | Tasks 14–16, 23 |
| §3.3 | Conic spinner glyph | Task 14 |
| §3.3 | Pulse + shimmer (no scanner/spotlight) | Tasks 12, 14 |
| §3.3 | Session-level total timer + per-run elapsed | Task 16 |
| §3.5 | Header (title, count, search, priority words, group, +Task) | Task 23 |
| §3.5 | Phase stepper (clickable, dot, gradient bar, all-phases, orphans, history) | Task 18, 23 |
| §3.5 | Epic chips (one-click, multi, count, clear-all) | Task 19, 23 |
| §3.5 | Group-by Status / Phase / Epic | Tasks 7, 23 |
| §3.5 | Sort dropdown (priority/size/created/started/touched, asc/desc) | Tasks 7, 23 |
| §3.5 | Words everywhere (Critical / High / Medium / Low; phase names) | Tasks 11, 17, 18 |
| §3.6 | Minimal & Full cards, density toggle persisted | Tasks 11, 22, 23 |
| §3.6 | Click-to-copy id + branch with green flash | Tasks 8, 11 |
| §3.6 | Recently-moved highlight (24h) | Task 11 |
| §3.6 | Hover state — bg only, no movement | Task 10 |
| §3.7 | Variant E — chip + ID color, no edge stripes | Tasks 6, 10, 11 |
| §3.8 | Time-in-status (4d → amber) | Tasks 5, 11 |
| §3.8 | Branch click-to-copy in footer | Tasks 8, 11 |
| §3.8 | Spec-review badge | Task 11 |
| §3.8 | Dependency count badge | Task 11 |
| §3.8 | Sub-repo chip | Task 11 |
| §3.8 | Docs icon in footer | Task 11 |
| §3.8 | Drop stage chip / anchors / status-when-status / last-touched | Task 11 (omitted by design) |

If any row is missing, add a hotfix task before merging.

- [ ] **Step 2: Run a full clean smoke**

```bash
python -m pytest plugins/taskmaster/tests/test_server_auto_state.py plugins/taskmaster/tests/test_server_api.py -v
node --test plugins/taskmaster/viewer/tests/unit/*.test.js
( cd plugins/taskmaster/viewer/tests && npx playwright test )
```

Expected: all green.

- [ ] **Step 3: Plan-completion commit**

```bash
git commit --allow-empty -m "chore(viewer): plan 2 complete — kanban + cards + auto-mode strip live

Spec coverage: §3.3, §3.5, §3.6, §3.7, §3.8.
Adds: GET /api/auto/state, lib/{time,filters,epics,copy}.js, components/{card,auto-mode-strip,auto-mode-live-block,phase-stepper,epic-chips,priority-chips}.js, screens/kanban.js, css/screens/kanban.css, kanban.spec.js + 3 unit suites.
"
```

Plan 2 is complete. Plan 3 (Task Detail Variants A + B) builds on the card and copy infrastructure introduced here.
