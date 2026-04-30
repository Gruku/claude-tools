# Taskmaster Viewer Redesign — Plan 4: Dashboard

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the redesigned Dashboard screen end-to-end: briefing strip, auto-mode strip reuse, 3-col bento grid (left rail | center board surface | right rail), bottom row, all 12 customizable widgets + the `auto-mode-stepper` slot reserved for Plan 6, edit-mode UX (drag/×/“+ Add widget”), persistence to `viewer.dashboard.layout`, and the `GET /api/dashboard/recent-events` server endpoint that powers the briefing + “What changed” widget.

**Architecture:** `js/screens/dashboard.js` is the orchestrator. It reads `prefs.dashboard.layout`, seeds a sensible default if empty, computes a CSS-Grid bento via `js/components/dashboard-grid.js`, mounts each widget through `js/components/widget-frame.js` from the registry in `js/components/widget-catalog.js`. Edit mode lives in `js/components/edit-mode.js`, persisting changes back through `api.savePrefs`. Each widget is a standalone module under `js/components/widgets/` with a `meta` export and a `mount(el, ctx)` function that returns a cleanup callback. Cards reuse Plan 2’s `js/components/card.js` (Minimal+Full); the auto-mode strip reuses Plan 2’s `js/components/auto-mode-strip.js`.

**Tech Stack:** Vanilla HTML/CSS/JS ES modules (no bundler), Python 3 + `BaseHTTPRequestHandler` (existing server, extended in Plan 1), pytest with the `running_server` fixture introduced in Plan 1, `node --test` for pure-JS layout-engine tests, Playwright for UI smoke.

**Spec reference:** `docs/superpowers/specs/2026-04-26-taskmaster-viewer-redesign.md` §3.4 (Dashboard), §3.15 (`auto-mode-stepper` widget reserved here), §3.16 (the “since you last looked” recap rule used by the briefing + “What changed” widget).

**Depends on:**
- Plan 1 — viewer skeleton, `tokens.css`, router, store, `api.js`, `prefs.js`, `/api/viewer/prefs`, `/api/backlog`, `/api/identity`, `/api/auto/state`, the `running_server` pytest fixture, `_send_json` helper, ViewerPrefs deep-merge.
- Plan 2 — `js/components/card.js` (Minimal+Full renderers), `js/components/auto-mode-strip.js`, `js/components/auto-mode-live-block.js`, `js/components/priority-chips.js`. The Dashboard reuses these.

---

## File Structure

**New files (created in this plan):**

```
plugins/taskmaster/viewer/
├── css/
│   └── screens/
│       └── dashboard.css                       # Dashboard layout, briefing strip, bento, board surface, edit-mode chrome
├── js/
│   ├── screens/
│   │   └── dashboard.js                        # Replaces the Plan 1 stub; orchestrates bento + edit mode
│   └── components/
│       ├── dashboard-grid.js                   # Pure layout engine: widgets[] → CSS Grid placements
│       ├── widget-frame.js                     # Common chrome: header label, body slot, edit-mode handles
│       ├── widget-catalog.js                   # Registers all 13 widgets; size + default-layout helpers
│       ├── edit-mode.js                        # Toggle, drag/reorder, "+ Add widget" picker, persistence
│       ├── briefing-strip.js                   # Italic-serif “Welcome back…” strip + ⌘K hint
│       ├── board-surface.js                    # Center 2-col preview (Up next + In progress, max 4 each)
│       └── widgets/
│           ├── suggested-next.js
│           ├── phase-deliverables.js
│           ├── newly-unblocked.js
│           ├── what-changed.js
│           ├── last-session.js
│           ├── open-issues.js
│           ├── build-test-pulse.js
│           ├── lessons-digest.js
│           ├── quick-capture.js
│           ├── recent-commits.js
│           ├── agent-activity.js
│           ├── stale-tasks.js
│           └── auto-mode-stepper.js            # Plan 4 stub; Plan 6 fills in
└── tests/
    ├── dashboard.spec.js                       # Playwright UI smoke (mounts, edit mode, add/remove)
    └── unit/
        └── dashboard-grid.test.js              # node --test for the layout engine
plugins/taskmaster/tests/
└── test_server_dashboard_events.py             # pytest for /api/dashboard/recent-events
```

**Files modified (in this plan):**
- `plugins/taskmaster/backlog_server.py` — add `GET /api/dashboard/recent-events?since=<iso>` route in `_Handler.do_GET`.
- `plugins/taskmaster/viewer/index.html` — load `css/screens/dashboard.css` (the screen-CSS list grows here).
- `plugins/taskmaster/viewer/js/screens/dashboard.js` — full replacement of the Plan 1 stub.

**Files left untouched (in this plan):** all other Plan 1 / Plan 2 / Plan 3 modules. No changes to `tokens.css` (per Plan 1 architectural conventions); dashboard-local design tokens go into `css/screens/dashboard.css` under the `--dash-*` namespace.

---

## Architectural Conventions

**Inherited verbatim from Plan 1 (`docs/superpowers/plans/2026-04-26-viewer-redesign-plan-1-foundation.md`, “Architectural Conventions”).** This plan does NOT redefine module style, screen module shape, CSS naming, state/API rules, routing, persistence, or test rules. Refer to Plan 1 for those.

**Plan-4-local conventions (additive only):**

### Widget module shape

Every file under `js/components/widgets/` exports:

```js
export const meta = {
  id: 'suggested-next',          // unique, kebab-case; matches widget instance.type
  label: 'Suggested next',       // human label rendered in widget-frame header + add picker
  sizes: ['small', 'medium'],    // allowed size variants for this widget
  defaultSize: 'medium',         // initial size when added via picker
  defaultRail: 'left',           // 'left' | 'right' | 'bottom' — used when seeding default layout
};

export async function mount(el, { store, api, prefs, size, instance }) {
  // Render into `el` (the widget-frame body slot, NOT the outer frame).
  // `instance` is the `{id, type, size, rail, index}` entry from prefs.dashboard.layout.
  // Return an async () => void cleanup, or undefined if there is nothing to clean up.
}
```

The catalog (`widget-catalog.js`) is the single source of truth for which widgets exist and which sizes they support. The grid engine and the Add-Widget picker both read from it.

### Layout-engine contract

`dashboard-grid.js` exports three pure functions:

```js
export function computePlacements(layout, options); // → [{instance, gridArea}]
export function addWidget(layout, type, options);   // → new layout with type appended in next free slot
export function removeWidget(layout, instanceId);   // → new layout without that instance
export function moveWidget(layout, instanceId, target); // → new layout with instance moved to {rail, index}
```

`layout` is `prefs.dashboard.layout` — an array of `{id, type, size, rail, index}`. `computePlacements` is deterministic, side-effect-free, and unit-tested.

### Edit-mode persistence

Every layout mutation (add / remove / move / size-change) immediately calls `api.savePrefs({dashboard: {layout: newLayout}})`. The store re-emits, dashboard re-renders. There is no “Save” button — edit mode is just a chrome toggle.

---

## Milestones

- **M1 — Layout engine + grid CSS** (Tasks 1–7): pure layout engine with unit tests, `dashboard-grid.js`, `widget-frame.js`, dashboard.css skeleton.
- **M2 — Widget catalog scaffold** (Tasks 8–10): `widget-catalog.js`, default-layout seeder, briefing strip + board surface (non-widget pieces).
- **M3 — Widget implementations** (Tasks 11–23): one task per widget (13 widgets including the `auto-mode-stepper` stub).
- **M4 — Edit mode UX** (Tasks 24–28): toggle, drag/reorder, “+ Add widget” picker, red ×, size cycler, persistence.
- **M5 — Server events endpoint** (Tasks 29–32): `/api/dashboard/recent-events` route + tests + wiring into briefing + “What changed”.
- **M6 — Integration + spec-coverage walk** (Tasks 33–36): Playwright smoke per major widget, spec §3.4 walkthrough, default 150% zoom verification, final commit.

---

## M1 — Layout Engine + Grid CSS

### Task 1: Read mockups + seed dashboard.css with bento grid skeleton

**Files:**
- Create: `plugins/taskmaster/viewer/css/screens/dashboard.css`
- Modify: `plugins/taskmaster/viewer/index.html`

- [x] **Step 1: Read all five dashboard mockups for visual reference (no code yet)**

Read in full:
- `.superpowers/brainstorm/15283-1777223061/content/dashboard-v1.html`
- `.superpowers/brainstorm/15283-1777223061/content/dashboard-v2.html`
- `.superpowers/brainstorm/15283-1777223061/content/dashboard-v3-zoomed.html` (the v3 file in this dir is suffixed `-zoomed`; spec referred to `dashboard-v3.html`)
- `.superpowers/brainstorm/15283-1777223061/content/dashboard-v4.html`
- `.superpowers/brainstorm/15283-1777223061/content/dashboard-v5.html`

Confirm by listing the structural pieces you saw: briefing strip, auto-mode strip, 3-col bento (left rail / center board surface / right rail), bottom row, edit-mode dashed borders, drag handle top-left, red × top-right, “+ Add widget” tile.

- [x] **Step 2: Create the CSS skeleton**

Create `plugins/taskmaster/viewer/css/screens/dashboard.css`:

```css
/* ===== Dashboard screen ===== */
.dash {
  --dash-rail-w: 280px;
  --dash-gap: 16px;
  --dash-board-min: 520px;
  --dash-pad: 20px;
  --dash-card-bg: var(--bg-card);
  --dash-card-bg-edit: color-mix(in oklab, var(--bg-card) 92%, transparent);
  --dash-card-border: var(--line-1);
  --dash-card-border-edit: 1px dashed var(--accent-edit, #6ea8ff);
  --dash-board-bg: linear-gradient(180deg, #161b24 0%, #181d28 100%);
  --dash-board-grid-mask: repeating-linear-gradient(
    0deg, transparent 0 31px, rgba(110, 168, 255, 0.045) 31px 32px
  ), repeating-linear-gradient(
    90deg, transparent 0 31px, rgba(110, 168, 255, 0.045) 31px 32px
  );
  display: flex;
  flex-direction: column;
  gap: var(--dash-gap);
  padding: var(--dash-pad);
}

.dash-briefing {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 24px;
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-style: italic;
  font-size: 16px;
  color: var(--ink-1);
  padding: 10px 4px;
}
.dash-briefing__sentence em { color: var(--ink-0); font-style: italic; }
.dash-briefing__meta {
  font-family: var(--font-mono);
  font-style: normal;
  font-size: 11px;
  color: var(--ink-3);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.dash-briefing__kbd {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 2px 8px; border-radius: 4px;
  background: var(--bg-deep); color: var(--ink-2);
  font-family: var(--font-mono); font-size: 11px; font-style: normal;
  border: 1px solid var(--line-1);
}

.dash-automode { /* Slot for Plan 2's auto-mode-strip; only renders when ≥1 task running */ }

.dash-bento {
  display: grid;
  grid-template-columns: var(--dash-rail-w) minmax(var(--dash-board-min), 1fr) var(--dash-rail-w);
  grid-auto-rows: min-content;
  gap: var(--dash-gap);
  align-items: start;
}
.dash-bento__rail { display: flex; flex-direction: column; gap: var(--dash-gap); }
.dash-bento__rail--left { grid-column: 1; }
.dash-bento__rail--right { grid-column: 3; }

.dash-board {
  grid-column: 2;
  position: relative;
  border-radius: 12px;
  background: var(--dash-board-bg);
  border: 1px solid var(--line-1);
  padding: 14px 14px 18px;
  min-height: 320px;
  isolation: isolate;
}
.dash-board::before {
  content: '';
  position: absolute; inset: 0;
  background: var(--dash-board-grid-mask);
  pointer-events: none;
  border-radius: inherit;
  z-index: 0;
}
.dash-board > * { position: relative; z-index: 1; }
.dash-board__head {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 10px;
}
.dash-board__title {
  font-family: var(--font-serif); font-style: italic;
  font-size: 14px; color: var(--ink-1);
}
.dash-board__cols {
  display: grid; grid-template-columns: 1fr 1fr; gap: 12px;
}
.dash-board__col-head {
  font-family: var(--font-mono); font-size: 10px; letter-spacing: 0.08em;
  text-transform: uppercase; color: var(--ink-3); margin-bottom: 6px;
}
.dash-board__expand,
.dash-board__open {
  background: transparent; border: 1px solid var(--line-1);
  color: var(--ink-2); font-size: 11px; padding: 4px 8px; border-radius: 6px;
  cursor: pointer;
}
.dash-board__expand:hover,
.dash-board__open:hover { color: var(--ink-0); border-color: var(--ink-3); }

.dash-bottom {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--dash-gap);
}

/* ===== Widget frame ===== */
.widget {
  background: var(--dash-card-bg);
  border: 1px solid var(--dash-card-border);
  border-radius: 10px;
  display: flex; flex-direction: column;
  min-height: 80px;
  position: relative;
}
.widget__head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 12px 6px;
}
.widget__label {
  font-family: var(--font-mono); font-size: 10px; letter-spacing: 0.08em;
  text-transform: uppercase; color: var(--ink-3);
}
.widget__body { padding: 4px 12px 12px; }
.widget--small { /* sized by grid; visual density tightening lives here */ }
.widget--medium { }
.widget--wide { }

/* ===== Edit mode chrome ===== */
.dash[data-edit='1'] .widget {
  border: var(--dash-card-border-edit);
  background: var(--dash-card-bg-edit);
}
.widget__drag,
.widget__remove {
  position: absolute; top: 6px;
  width: 18px; height: 18px;
  display: none; align-items: center; justify-content: center;
  border-radius: 4px; cursor: grab;
  font-size: 11px; color: var(--ink-2);
  background: var(--bg-deep); border: 1px solid var(--line-1);
}
.widget__drag { left: 6px; }
.widget__remove { right: 6px; cursor: pointer; color: #e87a85; }
.dash[data-edit='1'] .widget__drag,
.dash[data-edit='1'] .widget__remove { display: inline-flex; }
.widget__remove:hover { background: #2a1418; }

.dash-add-tile {
  display: none;
  border: 1px dashed var(--ink-3); border-radius: 10px;
  align-items: center; justify-content: center;
  color: var(--ink-3); font-size: 12px; min-height: 64px;
  cursor: pointer; background: transparent;
  font-family: var(--font-sans);
}
.dash[data-edit='1'] .dash-add-tile { display: flex; }
.dash-add-tile:hover { color: var(--ink-1); border-color: var(--ink-1); }

.dash-edit-toggle {
  align-self: flex-end;
  padding: 6px 10px; border-radius: 6px;
  background: transparent; color: var(--ink-2);
  border: 1px solid var(--line-1);
  font-size: 12px; cursor: pointer;
}
.dash-edit-toggle[aria-pressed='true'] {
  color: var(--ink-0);
  border-color: var(--accent-edit, #6ea8ff);
  background: color-mix(in oklab, var(--accent-edit, #6ea8ff) 12%, transparent);
}

/* ===== Add-widget picker ===== */
.dash-picker {
  position: absolute; z-index: 30;
  background: var(--bg-card); border: 1px solid var(--line-1);
  border-radius: 8px; padding: 6px;
  display: grid; grid-template-columns: repeat(2, 200px); gap: 4px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.45);
}
.dash-picker__item {
  display: flex; flex-direction: column; gap: 2px;
  padding: 8px 10px; border-radius: 6px;
  background: transparent; color: var(--ink-1); cursor: pointer;
  border: none; text-align: left; font-family: var(--font-sans);
}
.dash-picker__item:hover { background: var(--bg-deep); }
.dash-picker__item-label { font-size: 12px; }
.dash-picker__item-sub { font-size: 10px; color: var(--ink-3); }
```

- [x] **Step 3: Wire dashboard.css into the shell**

Open `plugins/taskmaster/viewer/index.html`, locate the `<link rel="stylesheet" href="css/screens/_placeholders.css">` line added in Plan 1, and add immediately below it:

```html
<link rel="stylesheet" href="css/screens/dashboard.css">
```

- [x] **Step 4: Verify the file loads**

Run from the repo root:

```bash
python -m http.server --directory plugins/taskmaster/viewer 0 >/dev/null 2>&1 &
SERVER_PID=$!
sleep 0.3
PORT=$(ss -tlnp 2>/dev/null | grep "$SERVER_PID" | sed -E 's/.*:([0-9]+) .*/\1/' | head -n1)
curl -s -o /dev/null -w "%{http_code}\n" "http://127.0.0.1:${PORT}/css/screens/dashboard.css"
kill $SERVER_PID
```
Expected output: `200`

- [x] **Step 5: Commit**

```bash
git add plugins/taskmaster/viewer/css/screens/dashboard.css plugins/taskmaster/viewer/index.html
git commit -m "feat(viewer): scaffold dashboard.css bento + widget frame skeleton"
```

---

### Task 2: `dashboard-grid.js` — `computePlacements` (pure)

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/dashboard-grid.js`
- Create: `plugins/taskmaster/viewer/tests/unit/dashboard-grid.test.js`

- [x] **Step 1: Write the failing test**

Create `plugins/taskmaster/viewer/tests/unit/dashboard-grid.test.js`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  computePlacements,
  addWidget,
  removeWidget,
  moveWidget,
} from '../../js/components/dashboard-grid.js';

test('computePlacements groups widgets by rail and orders by index', () => {
  const layout = [
    { id: 'a', type: 'suggested-next',    size: 'medium', rail: 'left',   index: 0 },
    { id: 'b', type: 'phase-deliverables',size: 'medium', rail: 'left',   index: 1 },
    { id: 'c', type: 'open-issues',       size: 'medium', rail: 'right',  index: 0 },
    { id: 'd', type: 'recent-commits',    size: 'small',  rail: 'bottom', index: 0 },
  ];
  const out = computePlacements(layout);
  assert.equal(out.length, 4);
  const left = out.filter(p => p.instance.rail === 'left').map(p => p.instance.id);
  assert.deepEqual(left, ['a', 'b']);
  const right = out.filter(p => p.instance.rail === 'right').map(p => p.instance.id);
  assert.deepEqual(right, ['c']);
  const bottom = out.filter(p => p.instance.rail === 'bottom').map(p => p.instance.id);
  assert.deepEqual(bottom, ['d']);
});

test('computePlacements assigns deterministic order for missing index', () => {
  const layout = [
    { id: 'a', type: 'x', size: 'medium', rail: 'left' },
    { id: 'b', type: 'y', size: 'medium', rail: 'left' },
  ];
  const out = computePlacements(layout);
  assert.deepEqual(out.map(p => p.instance.id), ['a', 'b']);
});
```

- [x] **Step 2: Run the test to verify it fails**

```bash
node --test plugins/taskmaster/viewer/tests/unit/dashboard-grid.test.js
```
Expected: FAIL with `ERR_MODULE_NOT_FOUND` for `dashboard-grid.js`.

- [x] **Step 3: Implement `computePlacements`**

Create `plugins/taskmaster/viewer/js/components/dashboard-grid.js`:

```js
// Pure layout engine for the dashboard bento. No DOM, no I/O.

const RAILS = ['left', 'right', 'bottom'];

function normalizeInstance(inst, fallbackIndex) {
  return {
    id: inst.id,
    type: inst.type,
    size: inst.size || 'medium',
    rail: RAILS.includes(inst.rail) ? inst.rail : 'left',
    index: typeof inst.index === 'number' ? inst.index : fallbackIndex,
  };
}

export function computePlacements(layout) {
  const normalized = (layout || []).map((inst, i) => normalizeInstance(inst, i));
  // Stable order by (rail, index, original position).
  const ordered = normalized
    .map((inst, i) => ({ inst, i }))
    .sort((a, b) => {
      if (a.inst.rail !== b.inst.rail) return RAILS.indexOf(a.inst.rail) - RAILS.indexOf(b.inst.rail);
      if (a.inst.index !== b.inst.index) return a.inst.index - b.inst.index;
      return a.i - b.i;
    })
    .map(({ inst }) => inst);

  return ordered.map((inst) => ({
    instance: inst,
    gridArea: null, // Rails are flex columns; bottom is a 4-col grid. No explicit gridArea today.
  }));
}

export function addWidget(layout, type, options = {}) {
  const rail = options.rail || 'left';
  const size = options.size || 'medium';
  const id = options.id || `${type}-${Date.now().toString(36)}-${Math.floor(Math.random() * 1e4).toString(36)}`;
  const railSiblings = (layout || []).filter((i) => (i.rail || 'left') === rail);
  const index = railSiblings.length;
  const next = [...(layout || []), { id, type, size, rail, index }];
  return next;
}

export function removeWidget(layout, instanceId) {
  return (layout || []).filter((i) => i.id !== instanceId).map((inst, idx) => ({ ...inst, index: idx }));
}

export function moveWidget(layout, instanceId, target) {
  const list = (layout || []).map((i) => ({ ...i }));
  const item = list.find((i) => i.id === instanceId);
  if (!item) return layout;
  const newRail = target.rail || item.rail || 'left';
  const newIndex = typeof target.index === 'number' ? target.index : 0;
  // Strip from old rail
  const others = list.filter((i) => i.id !== instanceId);
  const sameRail = others.filter((i) => (i.rail || 'left') === newRail)
    .sort((a, b) => (a.index ?? 0) - (b.index ?? 0));
  const otherRails = others.filter((i) => (i.rail || 'left') !== newRail);
  const reflowed = [];
  let inserted = false;
  for (let i = 0; i < sameRail.length; i++) {
    if (i === newIndex) { reflowed.push({ ...item, rail: newRail, index: reflowed.length }); inserted = true; }
    reflowed.push({ ...sameRail[i], index: reflowed.length });
  }
  if (!inserted) reflowed.push({ ...item, rail: newRail, index: reflowed.length });
  return [...otherRails, ...reflowed];
}

export const __RAILS__ = RAILS;
```

- [x] **Step 4: Run the test to verify it passes**

```bash
node --test plugins/taskmaster/viewer/tests/unit/dashboard-grid.test.js
```
Expected: `# tests 2  # pass 2  # fail 0`.

- [x] **Step 5: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/dashboard-grid.js plugins/taskmaster/viewer/tests/unit/dashboard-grid.test.js
git commit -m "feat(viewer): pure dashboard-grid layout engine + computePlacements"
```

---

### Task 3: `dashboard-grid.js` — `addWidget` / `removeWidget` / `moveWidget` tests

**Files:**
- Modify: `plugins/taskmaster/viewer/tests/unit/dashboard-grid.test.js`

- [x] **Step 1: Append additional tests**

Append to `plugins/taskmaster/viewer/tests/unit/dashboard-grid.test.js`:

```js
test('addWidget appends to end of target rail and assigns new index', () => {
  const layout = [
    { id: 'a', type: 'suggested-next', size: 'medium', rail: 'left', index: 0 },
  ];
  const out = addWidget(layout, 'open-issues', { rail: 'left', id: 'b' });
  assert.equal(out.length, 2);
  assert.equal(out[1].id, 'b');
  assert.equal(out[1].rail, 'left');
  assert.equal(out[1].index, 1);
});

test('removeWidget drops the instance and re-indexes survivors', () => {
  const layout = [
    { id: 'a', type: 'x', size: 'medium', rail: 'left', index: 0 },
    { id: 'b', type: 'y', size: 'medium', rail: 'left', index: 1 },
    { id: 'c', type: 'z', size: 'medium', rail: 'left', index: 2 },
  ];
  const out = removeWidget(layout, 'b');
  assert.deepEqual(out.map(i => i.id), ['a', 'c']);
  assert.deepEqual(out.map(i => i.index), [0, 1]);
});

test('moveWidget across rails reorders both rails consistently', () => {
  const layout = [
    { id: 'a', type: 'x', size: 'medium', rail: 'left',  index: 0 },
    { id: 'b', type: 'y', size: 'medium', rail: 'left',  index: 1 },
    { id: 'c', type: 'z', size: 'medium', rail: 'right', index: 0 },
  ];
  const out = moveWidget(layout, 'a', { rail: 'right', index: 0 });
  const right = out.filter(i => i.rail === 'right').sort((p, q) => p.index - q.index).map(i => i.id);
  assert.deepEqual(right, ['a', 'c']);
  const left = out.filter(i => i.rail === 'left').sort((p, q) => p.index - q.index).map(i => i.id);
  assert.deepEqual(left, ['b']);
});
```

- [x] **Step 2: Run tests to verify they pass**

```bash
node --test plugins/taskmaster/viewer/tests/unit/dashboard-grid.test.js
```
Expected: `# tests 5  # pass 5  # fail 0`.

- [x] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/tests/unit/dashboard-grid.test.js
git commit -m "test(viewer): cover dashboard-grid add/remove/move semantics"
```

---

### Task 4: `widget-frame.js` — common chrome

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/widget-frame.js`

- [x] **Step 1: Implement `widget-frame.js`**

Create `plugins/taskmaster/viewer/js/components/widget-frame.js`:

```js
// Common chrome for every dashboard widget.
// Returns { root, body, destroy(removeFromLayout: boolean) } so the screen can mount widget content.

export function createWidgetFrame({ instance, label, onRemove, onSizeCycle }) {
  const root = document.createElement('section');
  root.className = `widget widget--${instance.size || 'medium'}`;
  root.dataset.instanceId = instance.id;
  root.dataset.widgetType = instance.type;

  const drag = document.createElement('button');
  drag.type = 'button';
  drag.className = 'widget__drag';
  drag.title = 'Drag to reorder';
  drag.setAttribute('aria-label', 'Drag handle');
  drag.textContent = '⋮⋮';
  drag.draggable = true;
  drag.addEventListener('dragstart', (e) => {
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', instance.id);
    root.classList.add('is-dragging');
  });
  drag.addEventListener('dragend', () => root.classList.remove('is-dragging'));

  const remove = document.createElement('button');
  remove.type = 'button';
  remove.className = 'widget__remove';
  remove.title = 'Remove widget';
  remove.setAttribute('aria-label', 'Remove widget');
  remove.textContent = '×';
  remove.addEventListener('click', (e) => {
    e.stopPropagation();
    if (typeof onRemove === 'function') onRemove(instance.id);
  });

  const head = document.createElement('header');
  head.className = 'widget__head';
  const labelEl = document.createElement('span');
  labelEl.className = 'widget__label';
  labelEl.textContent = label;
  head.appendChild(labelEl);

  if (typeof onSizeCycle === 'function') {
    const sizeBtn = document.createElement('button');
    sizeBtn.type = 'button';
    sizeBtn.className = 'widget__size';
    sizeBtn.title = 'Cycle size';
    sizeBtn.textContent = '◐';
    sizeBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      onSizeCycle(instance.id);
    });
    head.appendChild(sizeBtn);
  }

  const body = document.createElement('div');
  body.className = 'widget__body';

  root.append(drag, remove, head, body);

  return {
    root,
    body,
    setLabel(text) { labelEl.textContent = text; },
    setSize(size) {
      root.classList.remove('widget--small', 'widget--medium', 'widget--wide');
      root.classList.add(`widget--${size}`);
    },
  };
}
```

- [x] **Step 2: Smoke-load via node module syntax check**

```bash
node --input-type=module -e "import('./plugins/taskmaster/viewer/js/components/widget-frame.js').then(m => console.log(typeof m.createWidgetFrame))"
```
Expected output: `function`

- [x] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/widget-frame.js
git commit -m "feat(viewer): widget-frame chrome with drag handle + remove button"
```

---

### Task 5: Briefing strip component

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/briefing-strip.js`

- [x] **Step 1: Implement**

Create `plugins/taskmaster/viewer/js/components/briefing-strip.js`:

```js
// Italic-serif "Welcome back…" strip per spec §3.4.
// Pulls counts from /api/dashboard/recent-events; falls back to a calm placeholder while loading.

export function createBriefingStrip({ store, api, prefs }) {
  const root = document.createElement('section');
  root.className = 'dash-briefing';

  const sentence = document.createElement('div');
  sentence.className = 'dash-briefing__sentence';
  sentence.innerHTML = '<em>Welcome back.</em> Loading recent activity…';

  const meta = document.createElement('div');
  meta.className = 'dash-briefing__meta';
  meta.innerHTML = '<span class="dash-briefing__project"></span> · <span class="dash-briefing__phase"></span> · <span class="dash-briefing__kbd">⌘K</span>';

  root.append(sentence, meta);

  async function refresh() {
    try {
      const since = (prefs && prefs.dashboard && prefs.dashboard.last_seen_at) || new Date(Date.now() - 24 * 3600 * 1000).toISOString();
      const events = await api.getRecentEvents(since);
      const closed = events.filter(e => e.kind === 'task_closed').length;
      const issues = events.filter(e => e.kind === 'issue_opened').length;
      const lessons = events.filter(e => e.kind === 'lesson_promoted').length;
      sentence.innerHTML = `<em>Welcome back.</em> Since you left, <em>${closed}</em> tasks closed, <em>${issues}</em> new issues, <em>${lessons}</em> lessons promoted.`;
    } catch (err) {
      sentence.innerHTML = '<em>Welcome back.</em> No recent-events feed available yet.';
    }
    const backlog = (store.getBacklog && store.getBacklog()) || {};
    const project = (backlog.meta && backlog.meta.project) || 'untitled';
    const activePhase = (backlog.phases || []).find(p => p.status === 'active');
    root.querySelector('.dash-briefing__project').textContent = project;
    root.querySelector('.dash-briefing__phase').textContent = activePhase ? activePhase.name : 'no active phase';
  }

  refresh();
  const unsub = store.subscribe ? store.subscribe('backlog', refresh) : () => {};

  return {
    root,
    refresh,
    destroy() { if (typeof unsub === 'function') unsub(); },
  };
}
```

- [x] **Step 2: Smoke-load**

```bash
node --input-type=module -e "import('./plugins/taskmaster/viewer/js/components/briefing-strip.js').then(m => console.log(typeof m.createBriefingStrip))"
```
Expected output: `function`

- [x] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/briefing-strip.js
git commit -m "feat(viewer): dashboard briefing strip (italic-serif + ⌘K hint)"
```

---

### Task 6: Center board surface component (preview of Up next + In progress)

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/board-surface.js`

- [x] **Step 1: Implement**

Create `plugins/taskmaster/viewer/js/components/board-surface.js`:

```js
// Center board surface: 2-col preview (Up next + In progress only),
// active phase, max 4 cards each. ⤢ inline-expand affordance toggles a
// "expanded" class; "open full board →" navigates to #/kanban.
// Reuses Plan 2's card.js Minimal renderer.

import { renderMinimalCard } from './card.js';

export function createBoardSurface({ store }) {
  const root = document.createElement('section');
  root.className = 'dash-board';
  root.setAttribute('aria-label', 'Board preview');

  const head = document.createElement('header');
  head.className = 'dash-board__head';

  const title = document.createElement('div');
  title.className = 'dash-board__title';
  title.textContent = 'Board preview';

  const actions = document.createElement('div');
  actions.className = 'dash-board__actions';

  const expand = document.createElement('button');
  expand.type = 'button';
  expand.className = 'dash-board__expand';
  expand.title = 'Expand inline';
  expand.textContent = '⤢';
  expand.addEventListener('click', () => root.classList.toggle('is-expanded'));

  const open = document.createElement('a');
  open.className = 'dash-board__open';
  open.href = '#/kanban';
  open.textContent = 'open full board →';

  actions.append(expand, open);
  head.append(title, actions);

  const cols = document.createElement('div');
  cols.className = 'dash-board__cols';

  function makeCol(label) {
    const col = document.createElement('div');
    col.className = 'dash-board__col';
    const h = document.createElement('div');
    h.className = 'dash-board__col-head';
    h.textContent = label;
    const list = document.createElement('div');
    list.className = 'dash-board__list';
    col.append(h, list);
    return { col, list };
  }
  const upnext = makeCol('Up next');
  const inprog = makeCol('In progress');
  cols.append(upnext.col, inprog.col);

  root.append(head, cols);

  function refresh() {
    const backlog = (store.getBacklog && store.getBacklog()) || { tasks: [] };
    const active = (backlog.phases || []).find(p => p.status === 'active');
    const phaseId = active ? active.id : null;
    const tasks = (backlog.tasks || []).filter(t => !phaseId || t.phase === phaseId);
    const upn = tasks.filter(t => t.status === 'todo' || t.status === 'ready').slice(0, 4);
    const ipg = tasks.filter(t => t.status === 'in-progress' || t.status === 'in_progress').slice(0, 4);
    upnext.list.replaceChildren(...upn.map(t => renderMinimalCard(t, { backlog })));
    inprog.list.replaceChildren(...ipg.map(t => renderMinimalCard(t, { backlog })));
    title.textContent = active ? `Phase: ${active.name}` : 'Board preview';
  }

  refresh();
  const unsub = store.subscribe ? store.subscribe('backlog', refresh) : () => {};

  return {
    root,
    refresh,
    destroy() { if (typeof unsub === 'function') unsub(); },
  };
}
```

- [x] **Step 2: Smoke-load**

```bash
node --input-type=module -e "import('./plugins/taskmaster/viewer/js/components/board-surface.js').then(m => console.log(typeof m.createBoardSurface)).catch(e => { console.error(e.message); process.exit(1); })"
```
Expected output: `function` (Plan 2's `card.js` is assumed present; if running ahead of Plan 2 the import will error — that is acceptable in isolation, integration smoke runs in M6).

- [x] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/board-surface.js
git commit -m "feat(viewer): dashboard center board surface (Up next + In progress preview)"
```

---

### Task 7: Replace `js/screens/dashboard.js` stub with the orchestrator skeleton (no widgets yet)

**Files:**
- Modify: `plugins/taskmaster/viewer/js/screens/dashboard.js`

- [x] **Step 1: Replace the Plan 1 stub**

Overwrite `plugins/taskmaster/viewer/js/screens/dashboard.js` with:

```js
import { computePlacements } from '../components/dashboard-grid.js';
import { createBriefingStrip } from '../components/briefing-strip.js';
import { createBoardSurface } from '../components/board-surface.js';

export const meta = { title: 'Dashboard', icon: '◧', sidebarKey: 'dashboard' };

export async function mount(root, { store, api, prefs }) {
  root.classList.add('dash');
  root.dataset.edit = '0';

  const briefing = createBriefingStrip({ store, api, prefs });
  root.appendChild(briefing.root);

  const automode = document.createElement('section');
  automode.className = 'dash-automode';
  root.appendChild(automode); // M3 fills this in via Plan 2's auto-mode-strip

  const bento = document.createElement('section');
  bento.className = 'dash-bento';
  root.appendChild(bento);

  const railLeft   = document.createElement('div'); railLeft.className   = 'dash-bento__rail dash-bento__rail--left';
  const railRight  = document.createElement('div'); railRight.className  = 'dash-bento__rail dash-bento__rail--right';
  const board = createBoardSurface({ store });
  bento.append(railLeft, board.root, railRight);

  const bottom = document.createElement('section');
  bottom.className = 'dash-bottom';
  root.appendChild(bottom);

  // Placeholder placements; widget mounting added in M2/M3.
  const placements = computePlacements((prefs && prefs.dashboard && prefs.dashboard.layout) || []);
  console.debug('[dashboard] placements', placements.length);

  return async () => {
    briefing.destroy();
    board.destroy();
  };
}
```

- [x] **Step 2: Verify it loads in the browser flow**

Start the server (Plan 1’s `_make_server`) and visit `/v3#/dashboard`. The page should render the briefing strip, an empty auto-mode slot, the board preview, and an empty bottom row. Run:

```bash
python -c "import sys; sys.path.insert(0, 'plugins/taskmaster'); from backlog_server import _make_server; s, p = _make_server(host='127.0.0.1', port=0); print('PORT=' + str(p))"
```
Expected output: a line like `PORT=53123`. (The dashboard render is verified visually here; Playwright smoke comes in M6.)

- [x] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/js/screens/dashboard.js
git commit -m "feat(viewer): dashboard orchestrator skeleton (briefing + bento + board)"
```

---

## M2 — Widget Catalog Scaffold

### Task 8: `widget-catalog.js` — empty registry + helpers

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/widget-catalog.js`

- [ ] **Step 1: Implement the catalog skeleton**

Create `plugins/taskmaster/viewer/js/components/widget-catalog.js`:

```js
// Single source of truth for which widgets exist on the dashboard.
// Widget modules are registered here; the catalog feeds the Add-Widget picker
// and the orchestrator's mount loop.

const REGISTRY = new Map();

export function registerWidget(mod) {
  if (!mod || !mod.meta || !mod.meta.id) {
    throw new Error('registerWidget: module must export `meta` with an id');
  }
  if (typeof mod.mount !== 'function') {
    throw new Error(`registerWidget(${mod.meta.id}): module must export an async mount()`);
  }
  REGISTRY.set(mod.meta.id, mod);
}

export function getWidget(id) {
  return REGISTRY.get(id);
}

export function listWidgets() {
  return Array.from(REGISTRY.values()).map(m => m.meta);
}

export function defaultLayout() {
  // Sensible first-run seed. Mirrors the dashboard-v5 mockup.
  return [
    { id: 'sn-0',  type: 'suggested-next',     size: 'medium', rail: 'left',   index: 0 },
    { id: 'pd-0',  type: 'phase-deliverables', size: 'medium', rail: 'left',   index: 1 },
    { id: 'nu-0',  type: 'newly-unblocked',    size: 'medium', rail: 'left',   index: 2 },
    { id: 'wc-0',  type: 'what-changed',       size: 'medium', rail: 'right',  index: 0 },
    { id: 'ls-0',  type: 'last-session',       size: 'medium', rail: 'right',  index: 1 },
    { id: 'oi-0',  type: 'open-issues',        size: 'medium', rail: 'right',  index: 2 },
    { id: 'btp-0', type: 'build-test-pulse',   size: 'small',  rail: 'bottom', index: 0 },
    { id: 'ld-0',  type: 'lessons-digest',     size: 'small',  rail: 'bottom', index: 1 },
    { id: 'rc-0',  type: 'recent-commits',     size: 'small',  rail: 'bottom', index: 2 },
    { id: 'aa-0',  type: 'agent-activity',     size: 'small',  rail: 'bottom', index: 3 },
  ];
}
```

- [ ] **Step 2: Smoke-load**

```bash
node --input-type=module -e "import('./plugins/taskmaster/viewer/js/components/widget-catalog.js').then(m => { console.log(typeof m.registerWidget, m.listWidgets().length, m.defaultLayout().length); })"
```
Expected output: `function 0 10`

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/widget-catalog.js
git commit -m "feat(viewer): widget-catalog registry + default-layout seeder"
```

---

### Task 9: Wire briefing strip + auto-mode-strip + catalog mounting into `dashboard.js`

**Files:**
- Modify: `plugins/taskmaster/viewer/js/screens/dashboard.js`

- [ ] **Step 1: Update orchestrator**

Overwrite `plugins/taskmaster/viewer/js/screens/dashboard.js` with:

```js
import { computePlacements } from '../components/dashboard-grid.js';
import { createBriefingStrip } from '../components/briefing-strip.js';
import { createBoardSurface } from '../components/board-surface.js';
import { createWidgetFrame } from '../components/widget-frame.js';
import { getWidget, defaultLayout, listWidgets } from '../components/widget-catalog.js';
import { createAutoModeStrip } from '../components/auto-mode-strip.js';

// Eager-import widget modules so they self-register via widget-catalog.
import './../components/widgets/suggested-next.js';
import './../components/widgets/phase-deliverables.js';
import './../components/widgets/newly-unblocked.js';
import './../components/widgets/what-changed.js';
import './../components/widgets/last-session.js';
import './../components/widgets/open-issues.js';
import './../components/widgets/build-test-pulse.js';
import './../components/widgets/lessons-digest.js';
import './../components/widgets/quick-capture.js';
import './../components/widgets/recent-commits.js';
import './../components/widgets/agent-activity.js';
import './../components/widgets/stale-tasks.js';
import './../components/widgets/auto-mode-stepper.js';

export const meta = { title: 'Dashboard', icon: '◧', sidebarKey: 'dashboard' };

export async function mount(root, { store, api, prefs }) {
  root.classList.add('dash');
  root.dataset.edit = '0';

  const cleanups = [];

  const briefing = createBriefingStrip({ store, api, prefs });
  root.appendChild(briefing.root);
  cleanups.push(() => briefing.destroy());

  const autoSlot = document.createElement('section');
  autoSlot.className = 'dash-automode';
  root.appendChild(autoSlot);
  const autoStrip = createAutoModeStrip({ store, api, mode: 'dashboard' });
  if (autoStrip && autoStrip.root) {
    autoSlot.appendChild(autoStrip.root);
    cleanups.push(() => autoStrip.destroy && autoStrip.destroy());
  }

  const bento = document.createElement('section');
  bento.className = 'dash-bento';
  root.appendChild(bento);

  const railLeft  = document.createElement('div'); railLeft.className  = 'dash-bento__rail dash-bento__rail--left';
  const railRight = document.createElement('div'); railRight.className = 'dash-bento__rail dash-bento__rail--right';
  const board = createBoardSurface({ store });
  bento.append(railLeft, board.root, railRight);
  cleanups.push(() => board.destroy());

  const bottom = document.createElement('section');
  bottom.className = 'dash-bottom';
  root.appendChild(bottom);

  // Seed layout if empty
  let layout = (prefs && prefs.dashboard && prefs.dashboard.layout) || [];
  if (!layout.length) {
    layout = defaultLayout();
    await api.savePrefs({ dashboard: { layout } });
  }

  const placements = computePlacements(layout);
  const widgetCleanups = new Map();

  for (const { instance } of placements) {
    const mod = getWidget(instance.type);
    if (!mod) {
      console.warn('[dashboard] unknown widget type', instance.type);
      continue;
    }
    const frame = createWidgetFrame({
      instance,
      label: mod.meta.label,
      onRemove: () => {/* M4 wires this to edit-mode */},
    });
    const target =
      instance.rail === 'right'  ? railRight :
      instance.rail === 'bottom' ? bottom    : railLeft;
    target.appendChild(frame.root);

    const cleanup = await mod.mount(frame.body, { store, api, prefs, size: instance.size, instance });
    widgetCleanups.set(instance.id, cleanup);
  }

  return async () => {
    for (const fn of cleanups) await fn?.();
    for (const fn of widgetCleanups.values()) await fn?.();
  };
}
```

- [ ] **Step 2: Smoke-load**

```bash
node --input-type=module -e "import('./plugins/taskmaster/viewer/js/screens/dashboard.js').then(m => console.log(typeof m.mount)).catch(e => { console.error(e.message); process.exit(1); })"
```
Expected: errors about missing widget modules — that's expected at this point, the widget files are added in M3. The orchestrator file itself should parse cleanly. Confirm the error message names `widgets/suggested-next.js` (or similar), proving the import path resolves to the right place.

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/js/screens/dashboard.js
git commit -m "feat(viewer): wire briefing + auto-mode strip + catalog mounting"
```

---

### Task 10: Default-layout seeding test

**Files:**
- Modify: `plugins/taskmaster/viewer/tests/unit/dashboard-grid.test.js`

- [ ] **Step 1: Append default-layout sanity test**

Append:

```js
test('defaultLayout: every entry has rail, type, and unique id', async () => {
  const { defaultLayout } = await import('../../js/components/widget-catalog.js');
  const seed = defaultLayout();
  assert.ok(seed.length >= 10);
  const ids = new Set(seed.map(i => i.id));
  assert.equal(ids.size, seed.length);
  for (const inst of seed) {
    assert.ok(inst.type, `instance missing type: ${JSON.stringify(inst)}`);
    assert.ok(['left', 'right', 'bottom'].includes(inst.rail), `bad rail: ${inst.rail}`);
    assert.ok(['small', 'medium', 'wide'].includes(inst.size), `bad size: ${inst.size}`);
  }
});
```

- [ ] **Step 2: Run tests**

```bash
node --test plugins/taskmaster/viewer/tests/unit/dashboard-grid.test.js
```
Expected: `# tests 6  # pass 6  # fail 0`.

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/tests/unit/dashboard-grid.test.js
git commit -m "test(viewer): default-layout sanity (rails, ids, sizes)"
```

---

## M3 — Widget Implementations

> Each task in M3 follows the same pattern: create the file, register with the catalog, render content read from store/api. Mount signature is `mount(el, { store, api, prefs, size, instance })` returning a cleanup. Sizes follow Plan-4 conventions (small/medium/wide); widgets that don't accept all three list only those they support.

### Task 11: Widget — `suggested-next.js`

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/widgets/suggested-next.js`

- [ ] **Step 1: Implement**

```js
import { registerWidget } from '../widget-catalog.js';
import { renderFullCard } from '../card.js';

export const meta = {
  id: 'suggested-next',
  label: 'Suggested next',
  sizes: ['medium', 'wide'],
  defaultSize: 'medium',
  defaultRail: 'left',
};

export async function mount(el, { store }) {
  function pick(backlog) {
    const tasks = (backlog.tasks || []).filter(t => t.status === 'ready' || t.status === 'todo');
    // Highest priority, then smallest size (so it's actionable now).
    const order = { Critical: 0, High: 1, Medium: 2, Low: 3 };
    return tasks.sort((a, b) => (order[a.priority] ?? 9) - (order[b.priority] ?? 9))[0];
  }

  function render() {
    const backlog = (store.getBacklog && store.getBacklog()) || { tasks: [] };
    const t = pick(backlog);
    el.replaceChildren();
    if (!t) {
      const empty = document.createElement('div');
      empty.className = 'widget__empty';
      empty.textContent = 'Nothing queued.';
      el.appendChild(empty);
      return;
    }
    const card = renderFullCard(t, { backlog });
    el.appendChild(card);
    const reasons = document.createElement('div');
    reasons.className = 'widget__reasons';
    reasons.style.cssText = 'margin-top:8px;font-size:11px;color:var(--ink-3);';
    reasons.textContent = `Reason: ${t.priority || 'Medium'} priority · ${t.estimate || 'M'} size · status ${t.status}`;
    el.appendChild(reasons);
  }

  render();
  const unsub = store.subscribe ? store.subscribe('backlog', render) : () => {};
  return () => unsub();
}

registerWidget({ meta, mount });
```

- [ ] **Step 2: Smoke-load**

```bash
node --input-type=module -e "import('./plugins/taskmaster/viewer/js/components/widgets/suggested-next.js').then(m => console.log(m.meta.id))"
```
Expected output: `suggested-next` (or an import error from `card.js` if running before Plan 2 lands; that's acceptable — integration smoke is in M6).

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/widgets/suggested-next.js
git commit -m "feat(viewer): widget — suggested-next (Full card + reason line)"
```

---

### Task 12: Widget — `phase-deliverables.js`

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/widgets/phase-deliverables.js`

- [ ] **Step 1: Implement**

```js
import { registerWidget } from '../widget-catalog.js';

export const meta = {
  id: 'phase-deliverables',
  label: 'Phase deliverables',
  sizes: ['small', 'medium'],
  defaultSize: 'medium',
  defaultRail: 'left',
};

export async function mount(el, { store }) {
  function render() {
    const backlog = (store.getBacklog && store.getBacklog()) || {};
    const active = (backlog.phases || []).find(p => p.status === 'active');
    el.replaceChildren();
    if (!active) {
      const empty = document.createElement('div');
      empty.className = 'widget__empty';
      empty.textContent = 'No active phase.';
      el.appendChild(empty);
      return;
    }
    const list = document.createElement('ul');
    list.style.cssText = 'list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:6px;';
    const tasks = (backlog.tasks || []).filter(t => t.phase === active.id);
    for (const t of tasks) {
      const li = document.createElement('li');
      const done = t.status === 'done' || t.status === 'completed';
      li.style.cssText = 'display:flex;gap:8px;align-items:baseline;font-size:12px;';
      li.innerHTML = `<span style="color:${done ? '#5fcdb8' : 'var(--ink-3)'};width:14px;">${done ? '✓' : '○'}</span><span class="mono" style="color:var(--ink-3);">${t.id}</span><span style="color:${done ? 'var(--ink-3)' : 'var(--ink-1)'};${done ? 'text-decoration:line-through;' : ''}">${t.title || ''}</span>`;
      list.appendChild(li);
    }
    el.appendChild(list);
  }
  render();
  const unsub = store.subscribe ? store.subscribe('backlog', render) : () => {};
  return () => unsub();
}

registerWidget({ meta, mount });
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/widgets/phase-deliverables.js
git commit -m "feat(viewer): widget — phase-deliverables checklist"
```

---

### Task 13: Widget — `newly-unblocked.js`

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/widgets/newly-unblocked.js`

- [ ] **Step 1: Implement**

```js
import { registerWidget } from '../widget-catalog.js';

export const meta = {
  id: 'newly-unblocked',
  label: 'Newly unblocked',
  sizes: ['small', 'medium'],
  defaultSize: 'medium',
  defaultRail: 'left',
};

export async function mount(el, { store }) {
  function render() {
    const backlog = (store.getBacklog && store.getBacklog()) || {};
    const tasks = (backlog.tasks || []).filter(t => {
      const deps = t.depends_on || [];
      const allDone = deps.every(id => {
        const dep = (backlog.tasks || []).find(x => x.id === id);
        return dep && (dep.status === 'done' || dep.status === 'completed');
      });
      return deps.length > 0 && allDone && (t.status === 'todo' || t.status === 'ready');
    }).slice(0, 5);

    el.replaceChildren();
    if (!tasks.length) {
      const empty = document.createElement('div');
      empty.className = 'widget__empty';
      empty.textContent = 'Nothing newly unblocked.';
      el.appendChild(empty);
      return;
    }
    for (const t of tasks) {
      const row = document.createElement('a');
      row.href = `#/task/${t.id}`;
      row.style.cssText = 'display:flex;gap:8px;align-items:baseline;padding:4px 0;text-decoration:none;color:inherit;font-size:12px;';
      row.innerHTML = `<span class="mono" style="color:var(--ink-3);">${t.id}</span><span>${t.title || ''}</span>`;
      el.appendChild(row);
    }
  }
  render();
  const unsub = store.subscribe ? store.subscribe('backlog', render) : () => {};
  return () => unsub();
}

registerWidget({ meta, mount });
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/widgets/newly-unblocked.js
git commit -m "feat(viewer): widget — newly-unblocked"
```

---

### Task 14: Widget — `what-changed.js`

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/widgets/what-changed.js`

- [ ] **Step 1: Implement**

```js
import { registerWidget } from '../widget-catalog.js';

const ICONS = {
  task_moved:       '↳',
  issue_opened:     '!',
  lesson_promoted:  '✦',
  task_closed:      '▮',
  phase_advanced:   '⎇',
};

export const meta = {
  id: 'what-changed',
  label: 'What changed',
  sizes: ['medium', 'wide'],
  defaultSize: 'medium',
  defaultRail: 'right',
};

export async function mount(el, { api, prefs }) {
  const since = (prefs && prefs.dashboard && prefs.dashboard.last_seen_at) || new Date(Date.now() - 24 * 3600 * 1000).toISOString();
  el.textContent = 'Loading…';
  let events = [];
  try { events = await api.getRecentEvents(since); } catch (_) { events = []; }
  el.replaceChildren();
  if (!events.length) {
    const empty = document.createElement('div');
    empty.className = 'widget__empty';
    empty.textContent = 'Nothing since you last looked.';
    el.appendChild(empty);
    return () => {};
  }
  for (const ev of events.slice(0, 12)) {
    const row = document.createElement('div');
    row.style.cssText = 'display:flex;gap:8px;align-items:baseline;font-size:12px;padding:3px 0;';
    row.innerHTML = `<span style="width:14px;color:var(--ink-2);">${ICONS[ev.kind] || '·'}</span><span style="color:var(--ink-1);">${ev.summary || ev.kind}</span><span style="margin-left:auto;color:var(--ink-3);font-family:var(--font-mono);font-size:10px;">${ev.at || ''}</span>`;
    el.appendChild(row);
  }
  return () => {};
}

registerWidget({ meta, mount });
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/widgets/what-changed.js
git commit -m "feat(viewer): widget — what-changed (semantic icons ↳ ! ✦ ▮ ⎇)"
```

---

### Task 15: Widget — `last-session.js`

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/widgets/last-session.js`

- [ ] **Step 1: Implement**

```js
import { registerWidget } from '../widget-catalog.js';

export const meta = {
  id: 'last-session',
  label: 'Last session',
  sizes: ['medium', 'wide'],
  defaultSize: 'medium',
  defaultRail: 'right',
};

export async function mount(el, { api }) {
  el.textContent = 'Loading…';
  let session = null;
  try { session = await api.getLastSession(); } catch (_) { session = null; }
  el.replaceChildren();
  if (!session) {
    const empty = document.createElement('div');
    empty.className = 'widget__empty';
    empty.textContent = 'No prior session yet.';
    el.appendChild(empty);
    return () => {};
  }
  const head = document.createElement('div');
  head.style.cssText = 'font-family:var(--font-mono);font-size:10px;color:var(--ink-3);letter-spacing:0.04em;';
  head.textContent = `${session.id || ''} · ${session.ended_at || session.started_at || ''}`;
  const quote = document.createElement('blockquote');
  quote.style.cssText = 'margin:8px 0;padding:6px 10px;border-left:1px solid var(--line-1);font-family:var(--font-serif);font-style:italic;color:var(--ink-1);font-size:13px;';
  quote.textContent = session.handover_quote || session.title || '—';
  el.append(head, quote);
  return () => {};
}

registerWidget({ meta, mount });
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/widgets/last-session.js
git commit -m "feat(viewer): widget — last-session with italic-serif handover quote"
```

---

### Task 16: Widget — `open-issues.js`

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/widgets/open-issues.js`

- [ ] **Step 1: Implement**

```js
import { registerWidget } from '../widget-catalog.js';

const SEV_COLOR = { Critical: '#e87a85', High: '#e8a34d', Medium: '#a8c958', Low: '#8a93a3' };

export const meta = {
  id: 'open-issues',
  label: 'Open issues',
  sizes: ['small', 'medium'],
  defaultSize: 'medium',
  defaultRail: 'right',
};

export async function mount(el, { api, store }) {
  let issues = [];
  try { issues = await api.listIssues({ status: 'open' }); } catch (_) { issues = []; }
  el.replaceChildren();
  if (!issues.length) {
    const empty = document.createElement('div');
    empty.className = 'widget__empty';
    empty.textContent = 'No open issues.';
    el.appendChild(empty);
    return () => {};
  }
  for (const i of issues.slice(0, 8)) {
    const row = document.createElement('a');
    row.href = `#/issues?focus=${encodeURIComponent(i.id)}`;
    row.style.cssText = 'display:flex;gap:8px;align-items:baseline;padding:4px 0;text-decoration:none;color:inherit;font-size:12px;';
    row.innerHTML = `<span style="color:${SEV_COLOR[i.severity] || 'var(--ink-3)'};font-family:var(--font-mono);">${i.id}</span><span>${i.title || ''}</span>`;
    el.appendChild(row);
  }
  return () => {};
}

registerWidget({ meta, mount });
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/widgets/open-issues.js
git commit -m "feat(viewer): widget — open-issues with severity color"
```

---

### Task 17: Widget — `build-test-pulse.js`

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/widgets/build-test-pulse.js`

- [ ] **Step 1: Implement**

```js
import { registerWidget } from '../widget-catalog.js';

export const meta = {
  id: 'build-test-pulse',
  label: 'Build & test pulse',
  sizes: ['small', 'medium'],
  defaultSize: 'small',
  defaultRail: 'bottom',
};

export async function mount(el, { api }) {
  let pulse = { build: 'unknown', tests: { passed: 0, failed: 0, total: 0 }, ts: null };
  try { pulse = await api.getBuildTestPulse(); } catch (_) { /* keep defaults */ }
  el.replaceChildren();
  const dot = (color) => `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${color};margin-right:6px;vertical-align:middle;"></span>`;
  const buildColor = pulse.build === 'pass' ? '#5fcdb8' : pulse.build === 'fail' ? '#e87a85' : '#8a93a3';
  const testColor  = (pulse.tests.failed || 0) === 0 ? '#5fcdb8' : '#e87a85';
  const wrap = document.createElement('div');
  wrap.style.cssText = 'display:flex;flex-direction:column;gap:4px;font-size:12px;';
  wrap.innerHTML = `
    <div>${dot(buildColor)}<span>Build: <strong>${pulse.build}</strong></span></div>
    <div>${dot(testColor)}<span>Tests: ${pulse.tests.passed}/${pulse.tests.total} passed</span></div>
    <div style="font-family:var(--font-mono);color:var(--ink-3);font-size:10px;">${pulse.ts || ''}</div>
  `;
  el.appendChild(wrap);
  return () => {};
}

registerWidget({ meta, mount });
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/widgets/build-test-pulse.js
git commit -m "feat(viewer): widget — build-test pulse"
```

---

### Task 18: Widget — `lessons-digest.js`

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/widgets/lessons-digest.js`

- [ ] **Step 1: Implement**

```js
import { registerWidget } from '../widget-catalog.js';

export const meta = {
  id: 'lessons-digest',
  label: 'Lessons digest',
  sizes: ['small', 'medium'],
  defaultSize: 'small',
  defaultRail: 'bottom',
};

export async function mount(el, { api }) {
  let lessons = [];
  try { lessons = await api.listLessons({ shelf: 'core' }); } catch (_) { lessons = []; }
  el.replaceChildren();
  if (!lessons.length) {
    const empty = document.createElement('div');
    empty.className = 'widget__empty';
    empty.textContent = 'No core lessons yet.';
    el.appendChild(empty);
    return () => {};
  }
  for (const l of lessons.slice(0, 6)) {
    const row = document.createElement('a');
    row.href = `#/lessons?focus=${encodeURIComponent(l.id)}`;
    row.style.cssText = 'display:flex;gap:8px;align-items:baseline;padding:3px 0;text-decoration:none;color:inherit;font-size:12px;';
    row.innerHTML = `<span class="mono" style="color:#d4a72c;">${l.id}</span><span style="flex:1;">${l.title || l.summary || ''}</span><span style="font-family:var(--font-mono);color:var(--ink-3);font-size:10px;">×${l.reinforce_count || 0}</span>`;
    el.appendChild(row);
  }
  return () => {};
}

registerWidget({ meta, mount });
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/widgets/lessons-digest.js
git commit -m "feat(viewer): widget — lessons-digest with reinforcement counters"
```

---

### Task 19: Widget — `quick-capture.js`

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/widgets/quick-capture.js`

- [ ] **Step 1: Implement**

```js
import { registerWidget } from '../widget-catalog.js';

export const meta = {
  id: 'quick-capture',
  label: 'Quick capture',
  sizes: ['small', 'medium'],
  defaultSize: 'medium',
  defaultRail: 'right',
};

export async function mount(el, { api }) {
  el.replaceChildren();
  const form = document.createElement('form');
  form.style.cssText = 'display:flex;flex-direction:column;gap:6px;';
  const ta = document.createElement('textarea');
  ta.rows = 3;
  ta.placeholder = 'Capture a thought, todo, or note…';
  ta.style.cssText = 'background:var(--bg-deep);color:var(--ink-1);border:1px solid var(--line-1);border-radius:6px;padding:6px;font-family:var(--font-sans);font-size:12px;resize:vertical;';
  const btn = document.createElement('button');
  btn.type = 'submit';
  btn.textContent = '＋ Capture';
  btn.style.cssText = 'align-self:flex-end;background:transparent;color:var(--ink-1);border:1px solid var(--line-1);border-radius:6px;padding:4px 10px;cursor:pointer;font-size:12px;';
  const status = document.createElement('div');
  status.style.cssText = 'font-size:10px;color:var(--ink-3);min-height:14px;';
  form.append(ta, btn, status);
  el.appendChild(form);
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!ta.value.trim()) return;
    status.textContent = 'Saving…';
    try {
      await api.quickCapture(ta.value.trim());
      ta.value = '';
      status.textContent = 'Captured.';
      setTimeout(() => { status.textContent = ''; }, 2000);
    } catch (err) {
      status.textContent = `Error: ${err.message || err}`;
    }
  });
  return () => {};
}

registerWidget({ meta, mount });
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/widgets/quick-capture.js
git commit -m "feat(viewer): widget — quick-capture inbox"
```

---

### Task 20: Widget — `recent-commits.js`

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/widgets/recent-commits.js`

- [ ] **Step 1: Implement**

```js
import { registerWidget } from '../widget-catalog.js';

export const meta = {
  id: 'recent-commits',
  label: 'Recent commits',
  sizes: ['small', 'medium'],
  defaultSize: 'small',
  defaultRail: 'bottom',
};

export async function mount(el, { api }) {
  let commits = [];
  try { commits = await api.getRecentCommits({ limit: 8 }); } catch (_) { commits = []; }
  el.replaceChildren();
  if (!commits.length) {
    const empty = document.createElement('div');
    empty.className = 'widget__empty';
    empty.textContent = 'No commits yet.';
    el.appendChild(empty);
    return () => {};
  }
  for (const c of commits) {
    const row = document.createElement('div');
    row.style.cssText = 'display:flex;gap:8px;align-items:baseline;padding:3px 0;font-size:12px;';
    row.innerHTML = `<span class="mono" style="color:var(--ink-3);">${(c.sha || '').slice(0, 7)}</span><span style="flex:1;color:var(--ink-1);">${c.subject || ''}</span><span style="font-family:var(--font-mono);color:var(--ink-3);font-size:10px;">${c.relative_time || ''}</span>`;
    el.appendChild(row);
  }
  return () => {};
}

registerWidget({ meta, mount });
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/widgets/recent-commits.js
git commit -m "feat(viewer): widget — recent-commits"
```

---

### Task 21: Widget — `agent-activity.js`

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/widgets/agent-activity.js`

- [ ] **Step 1: Implement**

```js
import { registerWidget } from '../widget-catalog.js';

export const meta = {
  id: 'agent-activity',
  label: 'Agent activity',
  sizes: ['small', 'medium'],
  defaultSize: 'small',
  defaultRail: 'bottom',
};

export async function mount(el, { api }) {
  let state = { running: [], hooks: {} };
  try { state = await api.getAutoState(); } catch (_) { /* keep defaults */ }
  el.replaceChildren();
  const total = (state.running || []).length;
  const summary = document.createElement('div');
  summary.style.cssText = 'font-size:12px;color:var(--ink-1);margin-bottom:6px;';
  summary.innerHTML = total
    ? `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#6ea8ff;margin-right:6px;"></span>${total} auto-mode session${total === 1 ? '' : 's'} running`
    : 'No agents running.';
  el.appendChild(summary);

  for (const r of (state.running || []).slice(0, 4)) {
    const row = document.createElement('div');
    row.style.cssText = 'display:flex;gap:8px;align-items:baseline;font-size:11px;padding:2px 0;';
    row.innerHTML = `<span class="mono" style="color:var(--ink-3);">${r.task_id || ''}</span><span style="flex:1;">${r.step_text || r.step || ''}</span><span style="font-family:var(--font-mono);color:var(--ink-3);">${r.elapsed || ''}</span>`;
    el.appendChild(row);
  }
  return () => {};
}

registerWidget({ meta, mount });
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/widgets/agent-activity.js
git commit -m "feat(viewer): widget — agent-activity"
```

---

### Task 22: Widget — `stale-tasks.js`

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/widgets/stale-tasks.js`

- [ ] **Step 1: Implement**

```js
import { registerWidget } from '../widget-catalog.js';

const STALE_DAYS = 4;

export const meta = {
  id: 'stale-tasks',
  label: 'Stale tasks',
  sizes: ['small', 'medium'],
  defaultSize: 'small',
  defaultRail: 'bottom',
};

function daysSince(iso) {
  if (!iso) return 0;
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return 0;
  return Math.floor((Date.now() - t) / 86400000);
}

export async function mount(el, { store }) {
  function render() {
    const backlog = (store.getBacklog && store.getBacklog()) || {};
    const stale = (backlog.tasks || [])
      .filter(t => t.status === 'in-progress' || t.status === 'in_progress')
      .map(t => ({ t, age: daysSince(t.started || t.touched || t.created) }))
      .filter(x => x.age >= STALE_DAYS)
      .sort((a, b) => b.age - a.age)
      .slice(0, 6);

    el.replaceChildren();
    if (!stale.length) {
      const empty = document.createElement('div');
      empty.className = 'widget__empty';
      empty.textContent = 'Nothing stale.';
      el.appendChild(empty);
      return;
    }
    for (const { t, age } of stale) {
      const row = document.createElement('a');
      row.href = `#/task/${t.id}`;
      row.style.cssText = 'display:flex;gap:8px;align-items:baseline;padding:3px 0;text-decoration:none;color:inherit;font-size:12px;';
      row.innerHTML = `<span class="mono" style="color:var(--ink-3);">${t.id}</span><span style="flex:1;">${t.title || ''}</span><span style="color:#e8a34d;font-family:var(--font-mono);font-size:10px;">${age}d</span>`;
      el.appendChild(row);
    }
  }
  render();
  const unsub = store.subscribe ? store.subscribe('backlog', render) : () => {};
  return () => unsub();
}

registerWidget({ meta, mount });
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/widgets/stale-tasks.js
git commit -m "feat(viewer): widget — stale-tasks (in-progress > 4d)"
```

---

### Task 23: Widget — `auto-mode-stepper.js` stub (Plan 6 fills in)

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/widgets/auto-mode-stepper.js`

- [ ] **Step 1: Implement stub**

```js
import { registerWidget } from '../widget-catalog.js';

export const meta = {
  id: 'auto-mode-stepper',
  label: 'Auto Mode · stepper',
  sizes: ['medium', 'wide'],
  defaultSize: 'medium',
  defaultRail: 'right',
};

export async function mount(el) {
  el.replaceChildren();
  const note = document.createElement('div');
  note.style.cssText = 'font-size:12px;color:var(--ink-3);font-family:var(--font-sans);';
  note.textContent = '(implemented in Plan 6 — Auto Mode page)';
  el.appendChild(note);
  return () => {};
}

registerWidget({ meta, mount });
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/widgets/auto-mode-stepper.js
git commit -m "feat(viewer): widget — auto-mode-stepper slot reserved (Plan 6 fills)"
```

---

## M4 — Edit Mode UX

### Task 24: `edit-mode.js` — toggle + remove

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/edit-mode.js`

- [ ] **Step 1: Implement**

Create `plugins/taskmaster/viewer/js/components/edit-mode.js`:

```js
import { addWidget, removeWidget, moveWidget } from './dashboard-grid.js';
import { listWidgets, getWidget } from './widget-catalog.js';

export function createEditMode({ root, api, prefs, refresh }) {
  let editing = false;

  const toggle = document.createElement('button');
  toggle.type = 'button';
  toggle.className = 'dash-edit-toggle';
  toggle.textContent = '✎ Edit layout';
  toggle.setAttribute('aria-pressed', 'false');
  toggle.addEventListener('click', () => {
    editing = !editing;
    toggle.setAttribute('aria-pressed', String(editing));
    toggle.textContent = editing ? '✓ Done' : '✎ Edit layout';
    root.dataset.edit = editing ? '1' : '0';
  });

  async function onRemove(instanceId) {
    const layout = (prefs.dashboard && prefs.dashboard.layout) || [];
    const next = removeWidget(layout, instanceId);
    await api.savePrefs({ dashboard: { layout: next } });
    prefs.dashboard.layout = next;
    refresh();
  }

  async function onAdd(rail, type) {
    const layout = (prefs.dashboard && prefs.dashboard.layout) || [];
    const next = addWidget(layout, type, { rail });
    await api.savePrefs({ dashboard: { layout: next } });
    prefs.dashboard.layout = next;
    refresh();
  }

  async function onMove(instanceId, target) {
    const layout = (prefs.dashboard && prefs.dashboard.layout) || [];
    const next = moveWidget(layout, instanceId, target);
    await api.savePrefs({ dashboard: { layout: next } });
    prefs.dashboard.layout = next;
    refresh();
  }

  function isEditing() { return editing; }

  return { toggle, onRemove, onAdd, onMove, isEditing };
}

export function createAddTile({ rail, onAdd }) {
  const tile = document.createElement('button');
  tile.type = 'button';
  tile.className = 'dash-add-tile';
  tile.textContent = '＋ Add widget';
  tile.addEventListener('click', () => {
    showPicker(tile, rail, onAdd);
  });
  return tile;
}

function showPicker(anchor, rail, onAdd) {
  const existing = document.querySelector('.dash-picker');
  if (existing) existing.remove();
  const picker = document.createElement('div');
  picker.className = 'dash-picker';
  for (const meta of listWidgets()) {
    const item = document.createElement('button');
    item.type = 'button';
    item.className = 'dash-picker__item';
    item.innerHTML = `<span class="dash-picker__item-label">${meta.label}</span><span class="dash-picker__item-sub">${meta.id}</span>`;
    item.addEventListener('click', async () => {
      picker.remove();
      await onAdd(rail, meta.id);
    });
    picker.appendChild(item);
  }
  document.body.appendChild(picker);
  const r = anchor.getBoundingClientRect();
  picker.style.left = `${r.left}px`;
  picker.style.top = `${r.bottom + 4}px`;
  setTimeout(() => {
    document.addEventListener('mousedown', function close(e) {
      if (!picker.contains(e.target)) {
        picker.remove();
        document.removeEventListener('mousedown', close);
      }
    });
  }, 0);
}
```

- [ ] **Step 2: Smoke-load**

```bash
node --input-type=module -e "import('./plugins/taskmaster/viewer/js/components/edit-mode.js').then(m => console.log(typeof m.createEditMode, typeof m.createAddTile)).catch(e => { console.error(e.message); process.exit(1); })"
```
Expected output: `function function`

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/edit-mode.js
git commit -m "feat(viewer): edit-mode toggle, add tile + picker, persistence wiring"
```

---

### Task 25: Wire edit mode into the dashboard orchestrator

**Files:**
- Modify: `plugins/taskmaster/viewer/js/screens/dashboard.js`

- [ ] **Step 1: Update orchestrator**

Replace the body of `mount()` in `plugins/taskmaster/viewer/js/screens/dashboard.js` to call `createEditMode` and re-render via a `refresh()` closure. Overwrite the file with:

```js
import { computePlacements } from '../components/dashboard-grid.js';
import { createBriefingStrip } from '../components/briefing-strip.js';
import { createBoardSurface } from '../components/board-surface.js';
import { createWidgetFrame } from '../components/widget-frame.js';
import { getWidget, defaultLayout } from '../components/widget-catalog.js';
import { createAutoModeStrip } from '../components/auto-mode-strip.js';
import { createEditMode, createAddTile } from '../components/edit-mode.js';

import './../components/widgets/suggested-next.js';
import './../components/widgets/phase-deliverables.js';
import './../components/widgets/newly-unblocked.js';
import './../components/widgets/what-changed.js';
import './../components/widgets/last-session.js';
import './../components/widgets/open-issues.js';
import './../components/widgets/build-test-pulse.js';
import './../components/widgets/lessons-digest.js';
import './../components/widgets/quick-capture.js';
import './../components/widgets/recent-commits.js';
import './../components/widgets/agent-activity.js';
import './../components/widgets/stale-tasks.js';
import './../components/widgets/auto-mode-stepper.js';

export const meta = { title: 'Dashboard', icon: '◧', sidebarKey: 'dashboard' };

export async function mount(root, { store, api, prefs }) {
  root.classList.add('dash');
  root.dataset.edit = '0';

  const briefing = createBriefingStrip({ store, api, prefs });
  const autoSlot = document.createElement('section'); autoSlot.className = 'dash-automode';
  const autoStrip = createAutoModeStrip({ store, api, mode: 'dashboard' });
  if (autoStrip && autoStrip.root) autoSlot.appendChild(autoStrip.root);

  const bento  = document.createElement('section'); bento.className  = 'dash-bento';
  const bottom = document.createElement('section'); bottom.className = 'dash-bottom';
  const railLeft  = document.createElement('div'); railLeft.className  = 'dash-bento__rail dash-bento__rail--left';
  const railRight = document.createElement('div'); railRight.className = 'dash-bento__rail dash-bento__rail--right';
  const board = createBoardSurface({ store });
  bento.append(railLeft, board.root, railRight);

  let widgetCleanups = [];

  const edit = createEditMode({
    root, api, prefs,
    refresh: () => render(),
  });

  // Header row holds the edit toggle.
  const headerRow = document.createElement('header');
  headerRow.style.cssText = 'display:flex;justify-content:flex-end;';
  headerRow.appendChild(edit.toggle);

  root.replaceChildren(headerRow, briefing.root, autoSlot, bento, bottom);

  // Seed layout if empty.
  let layout = (prefs && prefs.dashboard && prefs.dashboard.layout) || [];
  if (!layout.length) {
    layout = defaultLayout();
    await api.savePrefs({ dashboard: { layout } });
    prefs.dashboard = prefs.dashboard || {};
    prefs.dashboard.layout = layout;
  }

  async function render() {
    // Tear down current widgets.
    for (const fn of widgetCleanups) await fn?.();
    widgetCleanups = [];
    railLeft.replaceChildren();
    railRight.replaceChildren();
    bottom.replaceChildren();

    const placements = computePlacements(prefs.dashboard.layout || []);
    for (const { instance } of placements) {
      const mod = getWidget(instance.type);
      if (!mod) continue;
      const frame = createWidgetFrame({
        instance,
        label: mod.meta.label,
        onRemove: async (id) => { await edit.onRemove(id); },
      });
      const target =
        instance.rail === 'right'  ? railRight :
        instance.rail === 'bottom' ? bottom    : railLeft;
      target.appendChild(frame.root);
      const cleanup = await mod.mount(frame.body, { store, api, prefs, size: instance.size, instance });
      widgetCleanups.push(cleanup);
    }

    // Add tiles per rail (visible only in edit mode via CSS).
    railLeft.appendChild(createAddTile({ rail: 'left',  onAdd: edit.onAdd }));
    railRight.appendChild(createAddTile({ rail: 'right', onAdd: edit.onAdd }));
    bottom.appendChild(createAddTile({ rail: 'bottom', onAdd: edit.onAdd }));
  }

  await render();

  return async () => {
    briefing.destroy();
    board.destroy();
    autoStrip && autoStrip.destroy && autoStrip.destroy();
    for (const fn of widgetCleanups) await fn?.();
  };
}
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/screens/dashboard.js
git commit -m "feat(viewer): wire edit mode + add tiles + per-rail rendering"
```

---

### Task 26: Drag-and-drop reorder within a rail

**Files:**
- Modify: `plugins/taskmaster/viewer/js/components/edit-mode.js`
- Modify: `plugins/taskmaster/viewer/js/screens/dashboard.js`

- [ ] **Step 1: Add drop handler helper to `edit-mode.js`**

Append to `plugins/taskmaster/viewer/js/components/edit-mode.js`:

```js
export function attachRailDropTarget(railEl, rail, onMove) {
  railEl.addEventListener('dragover', (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    railEl.classList.add('is-drop-target');
  });
  railEl.addEventListener('dragleave', () => {
    railEl.classList.remove('is-drop-target');
  });
  railEl.addEventListener('drop', async (e) => {
    e.preventDefault();
    railEl.classList.remove('is-drop-target');
    const id = e.dataTransfer.getData('text/plain');
    if (!id) return;
    // Find drop index by counting widgets above the cursor.
    const widgets = Array.from(railEl.querySelectorAll('.widget'));
    const cursorY = e.clientY;
    let index = widgets.length;
    for (let i = 0; i < widgets.length; i++) {
      const r = widgets[i].getBoundingClientRect();
      if (cursorY < r.top + r.height / 2) { index = i; break; }
    }
    await onMove(id, { rail, index });
  });
}
```

- [ ] **Step 2: Wire it from `dashboard.js`**

In `plugins/taskmaster/viewer/js/screens/dashboard.js`, add the import:

```js
import { createEditMode, createAddTile, attachRailDropTarget } from '../components/edit-mode.js';
```

And after the `await render();` line in `mount()`, attach drop targets:

```js
attachRailDropTarget(railLeft,  'left',   edit.onMove);
attachRailDropTarget(railRight, 'right',  edit.onMove);
attachRailDropTarget(bottom,    'bottom', edit.onMove);
```

- [ ] **Step 3: Add a drop-target visual to dashboard.css**

Append to `plugins/taskmaster/viewer/css/screens/dashboard.css`:

```css
.dash[data-edit='1'] .dash-bento__rail.is-drop-target,
.dash[data-edit='1'] .dash-bottom.is-drop-target {
  outline: 2px dashed var(--accent-edit, #6ea8ff);
  outline-offset: 4px;
  border-radius: 8px;
}
```

- [ ] **Step 4: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/edit-mode.js plugins/taskmaster/viewer/js/screens/dashboard.js plugins/taskmaster/viewer/css/screens/dashboard.css
git commit -m "feat(viewer): drag-drop widget reorder across rails"
```

---

### Task 27: Size cycler on widget frame

**Files:**
- Modify: `plugins/taskmaster/viewer/js/components/widget-frame.js`
- Modify: `plugins/taskmaster/viewer/js/screens/dashboard.js`

- [ ] **Step 1: Update `widget-frame.js`**

The frame already exposes `setSize`. Verify the size button is present (it is, when `onSizeCycle` is passed). No edit needed in that file.

- [ ] **Step 2: Wire size cycling in `dashboard.js`**

Inside the `render()` function in `dashboard.js`, change the `createWidgetFrame` call to pass `onSizeCycle`:

```js
const frame = createWidgetFrame({
  instance,
  label: mod.meta.label,
  onRemove: async (id) => { await edit.onRemove(id); },
  onSizeCycle: async (id) => {
    const layout = (prefs.dashboard.layout || []).map(i => ({ ...i }));
    const inst = layout.find(x => x.id === id);
    if (!inst) return;
    const sizes = (mod.meta.sizes && mod.meta.sizes.length) ? mod.meta.sizes : ['small', 'medium', 'wide'];
    const cur = sizes.indexOf(inst.size);
    inst.size = sizes[(cur + 1) % sizes.length];
    await api.savePrefs({ dashboard: { layout } });
    prefs.dashboard.layout = layout;
    render();
  },
});
```

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/js/screens/dashboard.js
git commit -m "feat(viewer): cycle widget size from frame chrome"
```

---

### Task 28: Edit-mode tests (Playwright)

**Files:**
- Create: `plugins/taskmaster/viewer/tests/dashboard.spec.js`

- [ ] **Step 1: Write the smoke test**

Create `plugins/taskmaster/viewer/tests/dashboard.spec.js`:

```js
import { test, expect } from '@playwright/test';

const BASE = process.env.VIEWER_BASE || 'http://127.0.0.1:8765';

test.describe('dashboard', () => {
  test('mounts the briefing strip and bento', async ({ page }) => {
    await page.goto(`${BASE}/v3#/dashboard`);
    await expect(page.locator('.dash-briefing')).toBeVisible();
    await expect(page.locator('.dash-bento')).toBeVisible();
    await expect(page.locator('.dash-board')).toBeVisible();
  });

  test('seeds default layout with at least 10 widgets', async ({ page }) => {
    await page.goto(`${BASE}/v3#/dashboard`);
    const widgets = page.locator('.widget');
    await expect(widgets).toHaveCount(10, { timeout: 5000 });
  });

  test('edit toggle reveals add tiles and remove buttons', async ({ page }) => {
    await page.goto(`${BASE}/v3#/dashboard`);
    await page.locator('.dash-edit-toggle').click();
    await expect(page.locator('.dash-add-tile').first()).toBeVisible();
    await expect(page.locator('.widget__remove').first()).toBeVisible();
  });

  test('removing a widget persists across reload', async ({ page }) => {
    await page.goto(`${BASE}/v3#/dashboard`);
    await page.locator('.dash-edit-toggle').click();
    const before = await page.locator('.widget').count();
    await page.locator('.widget__remove').first().click();
    await page.waitForTimeout(300);
    const after = await page.locator('.widget').count();
    expect(after).toBe(before - 1);
    await page.reload();
    await expect(page.locator('.widget')).toHaveCount(after);
  });

  test('add tile picker adds a stale-tasks widget', async ({ page }) => {
    await page.goto(`${BASE}/v3#/dashboard`);
    await page.locator('.dash-edit-toggle').click();
    await page.locator('.dash-add-tile').first().click();
    await page.locator('.dash-picker__item:has-text("Stale tasks")').click();
    await expect(page.locator('[data-widget-type="stale-tasks"]').last()).toBeVisible();
  });
});
```

- [ ] **Step 2: Run the test (assumes a running dev server with seeded backlog)**

```bash
npx playwright test plugins/taskmaster/viewer/tests/dashboard.spec.js
```
Expected output: `5 passed`. If the suite fails because no viewer dev server is running, start one with the Plan 1 `_make_server` runner first.

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/tests/dashboard.spec.js
git commit -m "test(viewer): dashboard mount + edit-mode add/remove smoke"
```

---

## M5 — Server: `/api/dashboard/recent-events`

### Task 29: pytest scaffolding for the new endpoint

**Files:**
- Create: `plugins/taskmaster/tests/test_server_dashboard_events.py`

- [ ] **Step 1: Write the failing test**

Create `plugins/taskmaster/tests/test_server_dashboard_events.py`:

```python
"""Tests for GET /api/dashboard/recent-events."""
import json
import urllib.parse
import urllib.request
import pytest

# Reuse the running_server fixture from Plan 1.
from tests.test_server_api import running_server  # noqa: F401


def test_recent_events_returns_list(running_server):
    base, _ = running_server
    since = "2025-01-01T00:00:00Z"
    qs = urllib.parse.urlencode({"since": since})
    resp = urllib.request.urlopen(f"{base}/api/dashboard/recent-events?{qs}")
    assert resp.status == 200
    body = json.loads(resp.read())
    assert isinstance(body, list)
    for ev in body:
        assert "kind" in ev
        assert "at" in ev
        assert "summary" in ev


def test_recent_events_rejects_missing_since(running_server):
    base, _ = running_server
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(f"{base}/api/dashboard/recent-events")
    assert exc.value.code == 400


def test_recent_events_filters_by_since(running_server, tmp_path):
    """Events older than `since` are excluded."""
    base, _ = running_server
    far_future = "2999-01-01T00:00:00Z"
    qs = urllib.parse.urlencode({"since": far_future})
    resp = urllib.request.urlopen(f"{base}/api/dashboard/recent-events?{qs}")
    body = json.loads(resp.read())
    assert body == []
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
python -m pytest plugins/taskmaster/tests/test_server_dashboard_events.py -v
```
Expected output: 3 FAIL with HTTP 404 on the new endpoint.

- [ ] **Step 3: Commit (test only — RED)**

```bash
git add plugins/taskmaster/tests/test_server_dashboard_events.py
git commit -m "test(taskmaster): pytest for /api/dashboard/recent-events (red)"
```

---

### Task 30: Implement the endpoint

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py`

- [ ] **Step 1: Add a helper that synthesizes events from the backlog**

In `plugins/taskmaster/backlog_server.py`, add (near the other synthesis helpers — look for any `_load_backlog`-adjacent block):

```python
def _compute_recent_events(since_iso: str) -> list:
    """Synthesize a 'since you last looked' event stream from the backlog.

    Plan 4 stub: derive events from backlog state. Plan 5+ may swap in a
    persisted event log.
    Event shape: {kind, at, summary, ref?}
    Kinds: task_closed, task_moved, issue_opened, lesson_promoted, phase_advanced.
    """
    from datetime import datetime
    try:
        since = datetime.fromisoformat(since_iso.replace("Z", "+00:00"))
    except Exception as e:
        raise ValueError(f"invalid since: {e}")

    backlog = _load_backlog_yaml()  # existing helper from Plan 1
    events: list = []

    def _parse(s):
        if not s:
            return None
        try:
            return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        except Exception:
            return None

    for t in (backlog.get("tasks") or []):
        completed = _parse(t.get("completed"))
        if completed and completed >= since and t.get("status") in ("done", "completed"):
            events.append({
                "kind": "task_closed",
                "at": t["completed"],
                "summary": f"{t.get('id','')}: {t.get('title','')}",
                "ref": t.get("id"),
            })
        started = _parse(t.get("started"))
        if started and started >= since and t.get("status") in ("in-progress", "in_progress"):
            events.append({
                "kind": "task_moved",
                "at": t["started"],
                "summary": f"{t.get('id','')} → in progress",
                "ref": t.get("id"),
            })

    for ph in (backlog.get("phases") or []):
        advanced = _parse(ph.get("advanced_at") or ph.get("started"))
        if advanced and advanced >= since and ph.get("status") == "active":
            events.append({
                "kind": "phase_advanced",
                "at": ph.get("advanced_at") or ph.get("started"),
                "summary": f"phase {ph.get('id','')}: {ph.get('name','')}",
                "ref": ph.get("id"),
            })

    # Sort newest first, drop None ats.
    events = [e for e in events if e.get("at")]
    events.sort(key=lambda e: e["at"], reverse=True)
    return events
```

If `_load_backlog_yaml` is not the existing helper name, use whatever the file already exposes (search for an existing `/api/backlog` handler — it will already load the yaml; reuse that path).

- [ ] **Step 2: Add the route to `_Handler.do_GET`**

In `plugins/taskmaster/backlog_server.py`, add to `_Handler.do_GET` **before** the unknown-path 404 fallback:

```python
if self.path.startswith("/api/dashboard/recent-events"):
    import urllib.parse
    parsed = urllib.parse.urlparse(self.path)
    qs = urllib.parse.parse_qs(parsed.query)
    since = (qs.get("since") or [None])[0]
    if not since:
        self._send_json(400, {"ok": False, "error": "missing 'since' query param"})
        return
    try:
        events = _compute_recent_events(since)
    except ValueError as e:
        self._send_json(400, {"ok": False, "error": str(e)})
        return
    self._send_json(200, events)
    return
```

- [ ] **Step 3: Run tests to verify they pass**

```bash
python -m pytest plugins/taskmaster/tests/test_server_dashboard_events.py -v
```
Expected output: `3 passed`.

- [ ] **Step 4: Commit**

```bash
git add plugins/taskmaster/backlog_server.py
git commit -m "feat(taskmaster): GET /api/dashboard/recent-events (synth from backlog)"
```

---

### Task 31: Add `api.getRecentEvents()` to `js/api.js`

**Files:**
- Modify: `plugins/taskmaster/viewer/js/api.js`

- [ ] **Step 1: Locate the existing API methods**

Open `plugins/taskmaster/viewer/js/api.js` (created in Plan 1).

- [ ] **Step 2: Add helper methods**

Inside the exported `api` object, alongside `getBacklog`, `savePrefs`, etc., add:

```js
async getRecentEvents(since) {
  const u = new URL('/api/dashboard/recent-events', location.origin);
  u.searchParams.set('since', since);
  const r = await fetch(u);
  if (!r.ok) throw new Error(`recent-events: ${r.status}`);
  return r.json();
},

async getLastSession() {
  const r = await fetch('/api/sessions/last');
  if (!r.ok) return null;
  return r.json();
},

async listIssues(filter = {}) {
  const u = new URL('/api/issues', location.origin);
  for (const [k, v] of Object.entries(filter)) u.searchParams.set(k, v);
  const r = await fetch(u);
  if (!r.ok) return [];
  return r.json();
},

async listLessons(filter = {}) {
  const u = new URL('/api/lessons', location.origin);
  for (const [k, v] of Object.entries(filter)) u.searchParams.set(k, v);
  const r = await fetch(u);
  if (!r.ok) return [];
  return r.json();
},

async getRecentCommits({ limit = 8 } = {}) {
  const r = await fetch(`/api/git/commits?limit=${limit}`);
  if (!r.ok) return [];
  return r.json();
},

async getBuildTestPulse() {
  const r = await fetch('/api/build-test-pulse');
  if (!r.ok) return { build: 'unknown', tests: { passed: 0, failed: 0, total: 0 }, ts: null };
  return r.json();
},

async getAutoState() {
  const r = await fetch('/api/auto/state');
  if (!r.ok) return { running: [], hooks: {} };
  return r.json();
},

async quickCapture(text) {
  const r = await fetch('/api/quick-capture', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });
  if (!r.ok) throw new Error(`quick-capture: ${r.status}`);
  return r.json();
},
```

Note: endpoints other than `/api/dashboard/recent-events` and `/api/auto/state` may not yet exist in this plan's scope. Widgets that consume them are designed to fall back gracefully (the `try/catch` blocks in M3 widgets already swallow the failures). Plan 5 fills in lessons/issues/sessions endpoints; Plan 6 fills in any missing auto-mode bits.

- [ ] **Step 3: Smoke-load**

```bash
node --input-type=module -e "import('./plugins/taskmaster/viewer/js/api.js').then(m => console.log(typeof m.api.getRecentEvents)).catch(e => { console.error(e.message); process.exit(1); })"
```
Expected output: `function`

- [ ] **Step 4: Commit**

```bash
git add plugins/taskmaster/viewer/js/api.js
git commit -m "feat(viewer): api.js — recent-events + dashboard widget data fetchers"
```

---

### Task 32: Stamp `last_seen_at` on dashboard mount

**Files:**
- Modify: `plugins/taskmaster/viewer/js/screens/dashboard.js`

- [ ] **Step 1: Update `mount()`**

At the end of `mount()` in `plugins/taskmaster/viewer/js/screens/dashboard.js`, **before** the `return async () => …` cleanup, add:

```js
  // Stamp the previous "last looked" timestamp so the next visit sees this session's events.
  // Capture-on-cleanup so this visit's briefing reflects the prior timestamp.
  const prevSeen = (prefs.dashboard && prefs.dashboard.last_seen_at) || null;
  const stampOnLeave = async () => {
    try {
      await api.savePrefs({ dashboard: { last_seen_at: new Date().toISOString() } });
    } catch (_) { /* ignore */ }
  };
```

And modify the cleanup `return` block to call `stampOnLeave`:

```js
  return async () => {
    await stampOnLeave();
    briefing.destroy();
    board.destroy();
    autoStrip && autoStrip.destroy && autoStrip.destroy();
    for (const fn of widgetCleanups) await fn?.();
    void prevSeen;
  };
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/screens/dashboard.js
git commit -m "feat(viewer): stamp dashboard.last_seen_at on screen unmount"
```

---

## M6 — Integration + Spec-Coverage Walk

### Task 33: Spec §3.4 coverage walkthrough

**Files:** none modified — this is a verification task.

- [ ] **Step 1: Walk the spec checklist**

For each line in spec §3.4, point to the code that satisfies it. Confirm by running, against your local checkout:

```bash
ls plugins/taskmaster/viewer/js/components/widgets/ | sort
```
Expected output (alphabetic):
```
agent-activity.js
auto-mode-stepper.js
build-test-pulse.js
last-session.js
lessons-digest.js
newly-unblocked.js
open-issues.js
phase-deliverables.js
quick-capture.js
recent-commits.js
stale-tasks.js
suggested-next.js
what-changed.js
```

That is **13 widgets** — the 12 from §3.4 plus the `auto-mode-stepper` slot reserved here per §3.15.

Spec → file mapping (verify each):
- Briefing strip → `js/components/briefing-strip.js`
- Auto-mode strip → reused from Plan 2 via `createAutoModeStrip` in `dashboard.js`
- 3-col bento → `.dash-bento` in `dashboard.css` (left rail / board / right rail)
- Center board surface (Up next + In progress, max 4 each, gradient + grid mask, ⤢ + open full board) → `js/components/board-surface.js` + `.dash-board*` styles
- Bottom row → `.dash-bottom` 4-col grid
- 12 widgets → see list above
- Edit mode UX (dashed borders, drag handle top-left, red × top-right, "+ Add widget") → `widget-frame.js` + `edit-mode.js` + dashboard.css `.dash[data-edit='1']` rules
- Persistence to `viewer.dashboard` → `api.savePrefs({dashboard:{layout}})` in `edit-mode.js`
- Default 150% zoom → already in Plan 1's `tokens.css` (`--shell-zoom: 1.5`)

- [ ] **Step 2: Manual placeholder/TBD scan**

```bash
git ls-files 'plugins/taskmaster/viewer/js/screens/dashboard.js' 'plugins/taskmaster/viewer/js/components/widget-*' 'plugins/taskmaster/viewer/js/components/widgets/*' 'plugins/taskmaster/viewer/js/components/edit-mode.js' 'plugins/taskmaster/viewer/js/components/briefing-strip.js' 'plugins/taskmaster/viewer/js/components/board-surface.js' 'plugins/taskmaster/viewer/css/screens/dashboard.css' | xargs grep -nE 'TODO|TBD|FIXME|placeholder|similar to' || echo OK
```
Expected output: `OK` (or only the literal text `(implemented in Plan 6 — Auto Mode page)` from `auto-mode-stepper.js`, which is intentional).

- [ ] **Step 3: Commit (no-op if clean)**

No changes expected. If the placeholder scan flagged anything, fix it now and commit:

```bash
git commit -am "chore(viewer): scrub dashboard placeholders"
```

---

### Task 34: 150% zoom verification

**Files:** none modified.

- [ ] **Step 1: Confirm Plan 1 token**

```bash
grep -n -- '--shell-zoom' plugins/taskmaster/viewer/css/tokens.css
```
Expected output: a single line setting `--shell-zoom: 1.5` (Plan 1 defines it).

- [ ] **Step 2: Inspect the dashboard at 1.5x in a browser**

Open `http://127.0.0.1:<port>/v3#/dashboard` and confirm:
- Briefing strip reads cleanly (italic serif, no clipping)
- Bento rails do not horizontally overflow at the default viewport width (≥ 1280 CSS px)
- Drag handles + remove × hit-targets remain clickable

If any element clips or the rails wrap unexpectedly, narrow `--dash-rail-w` or relax `--dash-board-min` in `dashboard.css`. Document the verification in your session notes.

- [ ] **Step 3: No commit needed unless adjustments were made**

---

### Task 35: Final integration smoke

**Files:** none modified.

- [ ] **Step 1: Run all Plan-4 tests in one go**

```bash
python -m pytest plugins/taskmaster/tests/test_server_dashboard_events.py -v
node --test plugins/taskmaster/viewer/tests/unit/dashboard-grid.test.js
npx playwright test plugins/taskmaster/viewer/tests/dashboard.spec.js
```
Expected output:
- pytest: `3 passed`
- node --test: `# tests 6  # pass 6  # fail 0`
- Playwright: `5 passed`

- [ ] **Step 2: Run the full server test suite to catch regressions**

```bash
python -m pytest plugins/taskmaster/tests -v
```
Expected output: all tests pass. If a Plan 1 test regressed, fix it before continuing.

- [ ] **Step 3: No commit needed if clean**

---

### Task 36: Plan handoff — type/contract self-review

**Files:** none modified — this is a final review task.

- [ ] **Step 1: Re-verify the three contracts**

Confirm by reading these files end-to-end:
- `js/components/widget-catalog.js` — every widget self-registers via `registerWidget({meta, mount})`.
- `js/components/dashboard-grid.js` — `computePlacements`, `addWidget`, `removeWidget`, `moveWidget` are pure and unit-tested.
- `js/screens/dashboard.js` — `mount(root, {store, api, prefs})` returns an async cleanup that calls every widget's cleanup.

- [ ] **Step 2: Type-shape consistency check**

For each widget file in `js/components/widgets/*.js`, confirm:
- `meta.id` matches the filename (kebab-case, no extension)
- `meta.sizes` is a non-empty array of `'small' | 'medium' | 'wide'`
- `mount` accepts `(el, ctx)` where `ctx.size` and `ctx.instance` are present
- the function returns either `undefined` or an `() => void` cleanup

Run:

```bash
node --input-type=module -e "
import('./plugins/taskmaster/viewer/js/components/widget-catalog.js').then(async cat => {
  const { listWidgets, getWidget } = cat;
  const files = ['suggested-next','phase-deliverables','newly-unblocked','what-changed','last-session','open-issues','build-test-pulse','lessons-digest','quick-capture','recent-commits','agent-activity','stale-tasks','auto-mode-stepper'];
  for (const f of files) await import('./plugins/taskmaster/viewer/js/components/widgets/' + f + '.js');
  for (const meta of listWidgets()) {
    if (!Array.isArray(meta.sizes) || meta.sizes.length === 0) throw new Error('bad sizes for ' + meta.id);
    const mod = getWidget(meta.id);
    if (typeof mod.mount !== 'function') throw new Error('mount missing for ' + meta.id);
  }
  console.log('OK', listWidgets().length);
}).catch(e => { console.error(e.message); process.exit(1); });
"
```
Expected output: `OK 13`

- [ ] **Step 3: Plan-4 done. Commit a checkpoint marker if your team uses one**

```bash
git commit --allow-empty -m "chore(viewer): plan-4 dashboard complete"
```

---

## Self-Review (author checklist)

- [x] Every spec §3.4 requirement maps to a task: briefing (Task 5), auto-mode strip (Tasks 9, 25), 3-col bento (Tasks 1, 7, 9), board surface (Task 6), 12 widgets + auto-mode-stepper slot (Tasks 11–23), edit-mode UX (Tasks 24–28), persistence (Task 25, 26, 27), default 150% zoom (Task 34).
- [x] Placeholder scan: only intentional “(implemented in Plan 6 — Auto Mode page)” text remains, in `auto-mode-stepper.js`.
- [x] Type consistency: widget `meta` shape (id/label/sizes/defaultSize/defaultRail), `mount(el, {store, api, prefs, size, instance})`, layout-engine function names (`computePlacements`, `addWidget`, `removeWidget`, `moveWidget`).
