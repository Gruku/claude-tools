# Kanban Header Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Polish the Kanban header — surface archived phases via a dropdown, give archived tasks their own screen, replace flat Epic chips with a single-row pin+dropdown design, and preserve phase carousel scroll position across filter changes.

**Architecture:** Vanilla JS, ES modules. Pure-logic helpers (ranking, bucketing) live under `viewer/js/lib/` and are unit-tested with `node --test`. DOM components stay in `viewer/js/components/` and `viewer/js/screens/`; their wiring is exercised by the existing Playwright smoke. Carousel offsets become a kanban-owned `viewState` object passed into the stepper, so re-renders preserve scroll.

**Tech Stack:** Vanilla JS (ES modules), `node --test` for unit tests, Playwright for e2e smoke. CSS in `viewer/css/screens/kanban.css`. No build step.

**Spec:** `docs/superpowers/specs/2026-05-09-kanban-header-improvements-design.md`

---

## File Structure

| File | Status | Responsibility |
|---|---|---|
| `viewer/js/lib/epic-ranking.js` | NEW | Pure logic: rank epics, compute quick-vs-dropdown split, multi-key sort |
| `viewer/js/lib/phase-buckets.js` | NEW | Pure logic: split phases into archived / past / active / future |
| `viewer/js/components/phase-stepper.js` | MODIFY | Recognize `archived`, render `Archived (N)` dropdown, accept external `viewState`, auto-scroll to selected |
| `viewer/js/components/archived-phases-dropdown.js` | NEW | Standalone popover component with archived phase list |
| `viewer/js/components/epic-chips.js` | REWRITE | Single-row layout: quick chips + `+N more` trigger + dropdown panel with filter/sort/multiselect/pin |
| `viewer/js/components/epic-dropdown.js` | NEW | The dropdown panel sub-component (filter input, list, sort selector, footer) |
| `viewer/js/screens/kanban.js` | MODIFY | Hold stepper viewState, hold pinnedEpics from prefs, pass tasks-by-status to epic chips for ranking |
| `viewer/js/screens/archived.js` | NEW | Archived tasks screen — list grouped by epic |
| `viewer/js/router.js` | (no change) | Hash router already supports new screens via `registerScreen` |
| `viewer/js/main.js` | MODIFY | Register `/archived` screen |
| `viewer/js/components/sidebar.js` | MODIFY | Add `Archived` sidebar entry |
| `viewer/css/screens/kanban.css` | MODIFY | Styles for archived phase pill, popover, epic dropdown trigger + panel |
| `viewer/css/screens/archived.css` | NEW | Styles for archived tasks screen |
| `viewer/index.html` | MODIFY | Link `archived.css` |
| `viewer/tests/unit/epic-ranking.test.js` | NEW | Unit tests for ranking helpers |
| `viewer/tests/unit/phase-buckets.test.js` | NEW | Unit tests for phase bucketing |

---

## Task 1: `phase-buckets` library — pure phase bucketing logic

**Files:**
- Create: `plugins/taskmaster/viewer/js/lib/phase-buckets.js`
- Test: `plugins/taskmaster/viewer/tests/unit/phase-buckets.test.js`

This extracts the past/active/future split logic out of the stepper, adding the archived bucket. Tested in isolation so the stepper rewrite has a known-correct primitive.

- [ ] **Step 1: Write the failing tests**

```javascript
// plugins/taskmaster/viewer/tests/unit/phase-buckets.test.js
import test from 'node:test';
import assert from 'node:assert/strict';
import { bucketPhases } from '../../js/lib/phase-buckets.js';

test('bucketPhases — splits done/active/future/archived correctly', () => {
  const phases = [
    { id: 'p1', status: 'done' },
    { id: 'p2', status: 'archived' },
    { id: 'p3', status: 'active' },
    { id: 'p4', status: 'planned' },
    { id: 'p5', status: 'future' },
  ];
  const out = bucketPhases(phases);
  assert.deepEqual(out.past.map(p => p.id),     ['p1']);
  assert.deepEqual(out.active?.id,              'p3');
  assert.deepEqual(out.future.map(p => p.id),   ['p4', 'p5']);
  assert.deepEqual(out.archived.map(p => p.id), ['p2']);
});

test('bucketPhases — archived between done and active is still archived (not past)', () => {
  const phases = [
    { id: 'p1', status: 'done' },
    { id: 'p2', status: 'archived' },
    { id: 'p3', status: 'done' },
    { id: 'p4', status: 'active' },
  ];
  const out = bucketPhases(phases);
  assert.deepEqual(out.past.map(p => p.id),     ['p1', 'p3']);
  assert.deepEqual(out.archived.map(p => p.id), ['p2']);
  assert.equal(out.active.id, 'p4');
});

test('bucketPhases — no active phase: past = done, future = planned/future, archived stays separate', () => {
  const phases = [
    { id: 'p1', status: 'done' },
    { id: 'p2', status: 'archived' },
    { id: 'p3', status: 'planned' },
  ];
  const out = bucketPhases(phases);
  assert.deepEqual(out.past.map(p => p.id),     ['p1']);
  assert.deepEqual(out.future.map(p => p.id),   ['p3']);
  assert.deepEqual(out.archived.map(p => p.id), ['p2']);
  assert.equal(out.active, null);
});

test('bucketPhases — case-insensitive status', () => {
  const phases = [
    { id: 'p1', status: 'ARCHIVED' },
    { id: 'p2', status: 'Active' },
  ];
  const out = bucketPhases(phases);
  assert.deepEqual(out.archived.map(p => p.id), ['p1']);
  assert.equal(out.active.id, 'p2');
});

test('bucketPhases — empty input returns empty buckets', () => {
  const out = bucketPhases([]);
  assert.deepEqual(out.past, []);
  assert.deepEqual(out.future, []);
  assert.deepEqual(out.archived, []);
  assert.equal(out.active, null);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd plugins/taskmaster/viewer && node --test tests/unit/phase-buckets.test.js`
Expected: FAIL — `Cannot find module '.../lib/phase-buckets.js'`.

- [ ] **Step 3: Implement `bucketPhases`**

```javascript
// plugins/taskmaster/viewer/js/lib/phase-buckets.js
// Split a phase array into past / active / future / archived buckets.
// Status values: 'done' | 'active' | 'planned' | 'future' | 'archived' (case-insensitive).
// `archived` is filtered out FIRST so it never appears in past/future regions.
// Then the first 'active' phase wins; everything before it (still done) is past,
// everything after is future. With no active phase, done → past, planned/future → future.

export function bucketPhases(phases) {
  const list = Array.isArray(phases) ? phases : [];
  const norm = (s) => String(s || '').toLowerCase();

  const archived = list.filter(p => norm(p.status) === 'archived');
  const nonArchived = list.filter(p => norm(p.status) !== 'archived');

  const activeIdx = nonArchived.findIndex(p => norm(p.status) === 'active');
  if (activeIdx >= 0) {
    return {
      past:    nonArchived.slice(0, activeIdx),
      active:  nonArchived[activeIdx],
      future:  nonArchived.slice(activeIdx + 1),
      archived,
    };
  }
  return {
    past:    nonArchived.filter(p => norm(p.status) === 'done'),
    active:  null,
    future:  nonArchived.filter(p => {
      const s = norm(p.status);
      return s === 'future' || s === 'planned';
    }),
    archived,
  };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd plugins/taskmaster/viewer && node --test tests/unit/phase-buckets.test.js`
Expected: PASS, 5 tests.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/viewer/js/lib/phase-buckets.js plugins/taskmaster/viewer/tests/unit/phase-buckets.test.js
git commit -m "feat(viewer): phase-buckets lib — split phases by status incl archived"
```

---

## Task 2: `epic-ranking` library — pure ranking + sort logic

**Files:**
- Create: `plugins/taskmaster/viewer/js/lib/epic-ranking.js`
- Test: `plugins/taskmaster/viewer/tests/unit/epic-ranking.test.js`

Encapsulates: counting active tasks per epic, ranking, splitting into quick + dropdown, and applying the dropdown sort options.

- [ ] **Step 1: Write the failing tests**

```javascript
// plugins/taskmaster/viewer/tests/unit/epic-ranking.test.js
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  countActiveTasksByEpic,
  rankEpics,
  splitQuickAndDropdown,
  sortEpicsForDropdown,
  ACTIVE_TASK_STATUSES,
} from '../../js/lib/epic-ranking.js';

const TASKS = [
  { epic: 'a', status: 'todo' },
  { epic: 'a', status: 'in_progress' },
  { epic: 'a', status: 'done' },        // doesn't count
  { epic: 'b', status: 'in_review' },
  { epic: 'b', status: 'archived' },    // doesn't count
  { epic: 'c', status: 'todo' },
  { epic: null, status: 'todo' },       // orphan, ignored
];

const EPICS = [
  { id: 'a', name: 'Alpha',   status: 'active' },
  { id: 'b', name: 'Bravo',   status: 'active' },
  { id: 'c', name: 'Charlie', status: 'done',   last_referenced: '2026-05-01' },
  { id: 'd', name: 'Delta',   status: 'active', last_referenced: '2026-05-08' },
  { id: 'e', name: 'Echo',    status: 'archived' },
];

test('ACTIVE_TASK_STATUSES — todo, in_progress, in_review (not done, not archived)', () => {
  assert.deepEqual([...ACTIVE_TASK_STATUSES].sort(), ['in_progress', 'in_review', 'todo']);
});

test('countActiveTasksByEpic — counts only todo+in-progress+in-review per epic', () => {
  const out = countActiveTasksByEpic(TASKS);
  assert.equal(out.get('a'), 2);
  assert.equal(out.get('b'), 1);
  assert.equal(out.get('c'), 1);
  assert.equal(out.has('d'), false);
});

test('countActiveTasksByEpic — accepts hyphenated status (in-progress)', () => {
  const out = countActiveTasksByEpic([{ epic: 'x', status: 'in-progress' }]);
  assert.equal(out.get('x'), 1);
});

test('rankEpics — sorts by active task count desc, then last_referenced desc, then alpha', () => {
  const counts = countActiveTasksByEpic(TASKS);
  const ranked = rankEpics(EPICS, counts);
  // a (2) > b (1) tied with c (1) — break by last_referenced (c=2026-05-01) vs missing on b → c first
  // d (0) ties with e (0); break by alpha "Delta" < "Echo" → d first
  assert.deepEqual(ranked.map(e => e.id), ['a', 'c', 'b', 'd', 'e']);
});

test('splitQuickAndDropdown — pinned first (in pin order), then top-N by ranking, max 5', () => {
  const counts = countActiveTasksByEpic(TASKS);
  const ranked = rankEpics(EPICS, counts);
  const out = splitQuickAndDropdown(ranked, ['e', 'b'], 5);
  // Quick: pinned e, b first; then ranked filling remaining slots with non-pinned: a, c, d
  assert.deepEqual(out.quick.map(e => e.id), ['e', 'b', 'a', 'c', 'd']);
  assert.deepEqual(out.dropdown.map(e => e.id), []);
});

test('splitQuickAndDropdown — overflow goes to dropdown', () => {
  const epics = [
    { id: '1' }, { id: '2' }, { id: '3' }, { id: '4' }, { id: '5' }, { id: '6' }, { id: '7' },
  ];
  const out = splitQuickAndDropdown(epics, [], 5);
  assert.deepEqual(out.quick.map(e => e.id),    ['1', '2', '3', '4', '5']);
  assert.deepEqual(out.dropdown.map(e => e.id), ['6', '7']);
});

test('splitQuickAndDropdown — pin id not present in input is ignored', () => {
  const out = splitQuickAndDropdown([{ id: 'a' }, { id: 'b' }], ['ghost', 'a'], 5);
  assert.deepEqual(out.quick.map(e => e.id), ['a', 'b']);
});

test('sortEpicsForDropdown — count', () => {
  const counts = new Map([['a', 5], ['b', 1], ['c', 3]]);
  const out = sortEpicsForDropdown([{ id: 'a' }, { id: 'b' }, { id: 'c' }], 'count', counts);
  assert.deepEqual(out.map(e => e.id), ['a', 'c', 'b']);
});

test('sortEpicsForDropdown — status: active → done → archived', () => {
  const out = sortEpicsForDropdown(EPICS, 'status', new Map());
  // Active group (a, b, d), then done (c), then archived (e). Stable inside groups.
  assert.deepEqual(out.map(e => e.id), ['a', 'b', 'd', 'c', 'e']);
});

test('sortEpicsForDropdown — recent: last_referenced desc; missing goes last', () => {
  const out = sortEpicsForDropdown(EPICS, 'recent', new Map());
  assert.equal(out[0].id, 'd');     // 2026-05-08
  assert.equal(out[1].id, 'c');     // 2026-05-01
  // a, b, e have no last_referenced — order is stable input order (a, b, e)
  assert.deepEqual(out.slice(2).map(e => e.id), ['a', 'b', 'e']);
});

test('sortEpicsForDropdown — alpha by name (case-insensitive)', () => {
  const out = sortEpicsForDropdown(EPICS, 'alpha', new Map());
  assert.deepEqual(out.map(e => e.id), ['a', 'b', 'c', 'd', 'e']);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd plugins/taskmaster/viewer && node --test tests/unit/epic-ranking.test.js`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `epic-ranking`**

```javascript
// plugins/taskmaster/viewer/js/lib/epic-ranking.js
// Pure helpers for the Kanban epic chip row. No DOM.

export const ACTIVE_TASK_STATUSES = new Set(['todo', 'in_progress', 'in_review']);

const normStatus = (s) => String(s || '').toLowerCase().replace(/-/g, '_');

export function countActiveTasksByEpic(tasks) {
  const counts = new Map();
  for (const t of (tasks || [])) {
    if (!t.epic) continue;
    if (!ACTIVE_TASK_STATUSES.has(normStatus(t.status))) continue;
    counts.set(t.epic, (counts.get(t.epic) || 0) + 1);
  }
  return counts;
}

export function rankEpics(epics, activeCounts) {
  const arr = Array.isArray(epics) ? epics.slice() : [];
  const lr = (e) => e.last_referenced ? Date.parse(e.last_referenced) : 0;
  const nm = (e) => String(e.name || e.id || '').toLowerCase();
  arr.sort((a, b) => {
    const ca = activeCounts.get(a.id) || 0;
    const cb = activeCounts.get(b.id) || 0;
    if (ca !== cb) return cb - ca;
    const la = lr(a), lb = lr(b);
    if (la !== lb) return lb - la;
    return nm(a).localeCompare(nm(b));
  });
  return arr;
}

export function splitQuickAndDropdown(rankedEpics, pinnedIds, capacity) {
  const cap = Math.max(0, capacity | 0);
  const all = Array.isArray(rankedEpics) ? rankedEpics : [];
  const byId = new Map(all.map(e => [e.id, e]));
  const pinSet = new Set();
  const quick = [];

  // 1. Pinned first (in pin order), skipping ghosts.
  for (const id of (Array.isArray(pinnedIds) ? pinnedIds : [])) {
    if (quick.length >= cap) break;
    const e = byId.get(id);
    if (!e || pinSet.has(id)) continue;
    quick.push(e);
    pinSet.add(id);
  }

  // 2. Fill remaining slots with top-ranked non-pinned.
  for (const e of all) {
    if (quick.length >= cap) break;
    if (pinSet.has(e.id)) continue;
    quick.push(e);
  }

  // 3. Everything else goes to dropdown (preserving ranked order).
  const quickIds = new Set(quick.map(e => e.id));
  const dropdown = all.filter(e => !quickIds.has(e.id));

  return { quick, dropdown };
}

export function sortEpicsForDropdown(epics, sortKey, activeCounts) {
  const arr = Array.isArray(epics) ? epics.slice() : [];
  const counts = activeCounts || new Map();
  const norm = (s) => String(s || '').toLowerCase();

  if (sortKey === 'count') {
    arr.sort((a, b) => (counts.get(b.id) || 0) - (counts.get(a.id) || 0));
    return arr;
  }
  if (sortKey === 'status') {
    const rank = { active: 0, planned: 1, future: 1, done: 2, archived: 3 };
    arr.sort((a, b) => {
      const ra = rank[norm(a.status)] ?? 4;
      const rb = rank[norm(b.status)] ?? 4;
      return ra - rb;
    });
    return arr;
  }
  if (sortKey === 'recent') {
    const lr = (e) => e.last_referenced ? Date.parse(e.last_referenced) : 0;
    arr.sort((a, b) => {
      const la = lr(a), lb = lr(b);
      if (la === 0 && lb === 0) return 0;       // preserve input order for missing
      if (la === 0) return 1;
      if (lb === 0) return -1;
      return lb - la;
    });
    return arr;
  }
  // 'alpha'
  const nm = (e) => String(e.name || e.id || '').toLowerCase();
  arr.sort((a, b) => nm(a).localeCompare(nm(b)));
  return arr;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd plugins/taskmaster/viewer && node --test tests/unit/epic-ranking.test.js`
Expected: PASS, 11 tests.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/viewer/js/lib/epic-ranking.js plugins/taskmaster/viewer/tests/unit/epic-ranking.test.js
git commit -m "feat(viewer): epic-ranking lib — count active tasks, rank, split quick/dropdown, sort"
```

---

## Task 3: Phase stepper — refactor to use `bucketPhases` and accept `viewState`

**Files:**
- Modify: `plugins/taskmaster/viewer/js/components/phase-stepper.js`
- Modify: `plugins/taskmaster/viewer/js/screens/kanban.js`

Two changes wired together: (a) stepper uses `bucketPhases` to split out archived; (b) past/future offsets become an externally-owned `viewState` object so they survive re-renders.

- [ ] **Step 1: Update stepper to import `bucketPhases` and accept `viewState`**

In `plugins/taskmaster/viewer/js/components/phase-stepper.js`, replace the existing splitting logic (lines 25–30) and the local `view` declaration:

```javascript
// At top, after existing constants:
import { bucketPhases } from '../lib/phase-buckets.js';

// Replace renderPhaseStepper signature + bucket lines:
export function renderPhaseStepper({ phases = [], active = '__all__', viewState, onSelect }) {
  const wrap = document.createElement('div');
  wrap.className = 'kanban-phase-stepper v12c';
  wrap.dataset.cmp = 'phase-stepper';

  const buckets = bucketPhases(phases);
  const pastPhases    = buckets.past;
  const futurePhases  = buckets.future;
  const activePhase   = buckets.active;
  const archivedPhases = buckets.archived;

  // Carousel offsets — owned by caller via `viewState` so re-renders preserve scroll.
  // Falls back to a fresh local object when no caller state is provided (tests, standalone use).
  const view = viewState || { pastOffset: 0, futureOffset: 0 };
  if (typeof view.pastOffset !== 'number')   view.pastOffset = 0;
  if (typeof view.futureOffset !== 'number') view.futureOffset = 0;

  // Clamp offsets in case the phase set shrank between renders.
  view.pastOffset   = Math.max(0, Math.min(view.pastOffset,   Math.max(0, pastPhases.length   - VISIBLE_PAST)));
  view.futureOffset = Math.max(0, Math.min(view.futureOffset, Math.max(0, futurePhases.length - VISIBLE_FUTURE)));
```

Leave everything else in the file unchanged (the rest already uses `view.pastOffset` / `view.futureOffset`).

- [ ] **Step 2: Update kanban.js to own the viewState**

In `plugins/taskmaster/viewer/js/screens/kanban.js`, after the `state` declaration around line 41, add:

```javascript
  // Carousel offsets that survive re-renders (filter changes, backlog refresh).
  const stepperViewState = { pastOffset: 0, futureOffset: 0 };
```

Then update the `renderPhaseStepper` call (around line 228) to pass it:

```javascript
    stepperHost.replaceChildren(renderPhaseStepper({
      phases: phaseRows,
      active: state.filters.phase,
      viewState: stepperViewState,
      onSelect: (key) => {
        const next = (state.filters.phase === key) ? '__all__' : key;
        state.filters.phase = next;
        paint(); savePrefs();
      },
    }));
```

- [ ] **Step 3: Manual smoke — run viewer, scroll past carousel, change phase filter**

Run: `cd plugins/taskmaster && python backlog_server.py` (or however the viewer is normally started in this repo — see `viewer/README.md` if unsure).
Open the kanban. Click the past slide arrow until offset is non-zero. Click any past phase. Verify the carousel does NOT snap back to home.

- [ ] **Step 4: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/phase-stepper.js plugins/taskmaster/viewer/js/screens/kanban.js
git commit -m "feat(viewer): phase stepper preserves carousel offsets across re-renders"
```

---

## Task 4: Phase stepper — auto-scroll to bring selected phase into view

**Files:**
- Modify: `plugins/taskmaster/viewer/js/components/phase-stepper.js`

When the user picks a phase from outside the visible window (e.g. via the new archived dropdown later, or by clicking an off-screen orphans link), the carousel slides to bring it in.

- [ ] **Step 1: Add `ensureSelectedVisible` and call it in `repaint`**

In `plugins/taskmaster/viewer/js/components/phase-stepper.js`, immediately before `function repaint()` add:

```javascript
  function ensureSelectedVisible() {
    if (!active || active === '__all__' || active === '__orphans__') return;

    // Past region: window covers indices [pastLen - VISIBLE_PAST - pastOffset, pastLen - pastOffset)
    const pastIdx = pastPhases.findIndex(p => p.id === active);
    if (pastIdx >= 0) {
      const pastLen = pastPhases.length;
      const visStart = Math.max(0, pastLen - VISIBLE_PAST - view.pastOffset);
      const visEnd   = Math.max(0, pastLen - view.pastOffset);
      if (pastIdx < visStart || pastIdx >= visEnd) {
        // Centre the index in the window when possible.
        const desiredVisStart = Math.max(0, pastIdx - Math.floor(VISIBLE_PAST / 2));
        const newOffset = Math.max(0, pastLen - VISIBLE_PAST - desiredVisStart);
        view.pastOffset = Math.max(0, Math.min(newOffset, Math.max(0, pastLen - VISIBLE_PAST)));
      }
      return;
    }

    // Future region: window covers indices [futureOffset, futureOffset + VISIBLE_FUTURE)
    const futureIdx = futurePhases.findIndex(p => p.id === active);
    if (futureIdx >= 0) {
      const visStart = view.futureOffset;
      const visEnd   = view.futureOffset + VISIBLE_FUTURE;
      if (futureIdx < visStart || futureIdx >= visEnd) {
        const newOffset = Math.max(0, futureIdx - Math.floor(VISIBLE_FUTURE / 2));
        const maxOffset = Math.max(0, futurePhases.length - VISIBLE_FUTURE);
        view.futureOffset = Math.max(0, Math.min(newOffset, maxOffset));
        applyFutureScroll();
      }
    }
  }
```

Then call it as the first line of `repaint`:

```javascript
  function repaint() {
    ensureSelectedVisible();
    const pastLen = pastPhases.length;
    // ... rest unchanged
```

- [ ] **Step 2: Manual smoke**

Run viewer. With many past phases, click ‹ to scroll past carousel right. Then click on an old past phase (off-screen). Verify carousel slides to centre the selected phase.

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/phase-stepper.js
git commit -m "feat(viewer): phase stepper auto-scrolls carousel to selected phase"
```

---

## Task 5: Archived phases dropdown component

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/archived-phases-dropdown.js`
- Modify: `plugins/taskmaster/viewer/js/components/phase-stepper.js`
- Modify: `plugins/taskmaster/viewer/css/screens/kanban.css`

A pill labeled `Archived (N)` rendered at the leftmost edge of the stepper. Click opens a popover listing archived phases as filterable rows.

- [ ] **Step 1: Implement the dropdown component**

```javascript
// plugins/taskmaster/viewer/js/components/archived-phases-dropdown.js
// Standalone pill+popover for archived phases. Hidden when phases is empty.

export function renderArchivedPhasesDropdown({ phases = [], active = '__all__', onSelect }) {
  const root = document.createElement('div');
  root.className = 'phs-archived';
  root.dataset.cmp = 'archived-phases';

  if (!phases.length) {
    root.classList.add('hidden');
    return root;
  }

  const isActiveSelection = phases.some(p => p.id === active);

  const trigger = document.createElement('button');
  trigger.type = 'button';
  trigger.className = 'phs-archived-trigger' + (isActiveSelection ? ' filtered' : '');
  trigger.title = `${phases.length} archived ${phases.length === 1 ? 'phase' : 'phases'}`;
  trigger.innerHTML = `
    <span class="ic">⌫</span>
    <span class="lbl">Archived</span>
    <span class="count">${phases.length}</span>
  `;
  root.appendChild(trigger);

  const pop = document.createElement('div');
  pop.className = 'phs-archived-pop';
  pop.hidden = true;
  root.appendChild(pop);

  for (const p of phases) {
    const row = document.createElement('button');
    row.type = 'button';
    row.className = 'phs-archived-row' + (active === p.id ? ' on' : '');
    const reason = p.archived_reason ? `<span class="reason">${escapeHtml(p.archived_reason)}</span>` : '';
    const stat = `${p.done || 0}/${p.total || 0}`;
    row.innerHTML = `
      <span class="name">${escapeHtml(p.name || p.id)}</span>
      <span class="meta"><span class="stat">${stat}</span>${reason}</span>
    `;
    row.addEventListener('click', () => {
      pop.hidden = true;
      if (onSelect) onSelect(p.id);
    });
    pop.appendChild(row);
  }

  trigger.addEventListener('click', (e) => {
    e.stopPropagation();
    pop.hidden = !pop.hidden;
  });

  // Close popover on outside click.
  document.addEventListener('click', (e) => {
    if (!root.contains(e.target)) pop.hidden = true;
  });

  return root;
}

function escapeHtml(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
```

- [ ] **Step 2: Mount the dropdown in the stepper at the leftmost edge**

In `plugins/taskmaster/viewer/js/components/phase-stepper.js`, add the import at top:

```javascript
import { renderArchivedPhasesDropdown } from './archived-phases-dropdown.js';
```

After the `wrap` is created and before `pastRegion` is appended, insert:

```javascript
  // ── Archived dropdown (left bookend, before past region) ──
  const archivedEl = renderArchivedPhasesDropdown({
    phases: archivedPhases,
    active,
    onSelect: (id) => onSelect && onSelect(id),
  });
  wrap.appendChild(archivedEl);
```

- [ ] **Step 3: Add styles**

Append to `plugins/taskmaster/viewer/css/screens/kanban.css`:

```css
/* ── Archived phases dropdown ────────────────────────────────────────── */
.kanban-phase-stepper .phs-archived {
  position: relative;
  display: flex;
  align-items: center;
  margin-right: var(--sp-2);
}
.kanban-phase-stepper .phs-archived.hidden { display: none; }

.kanban-phase-stepper .phs-archived-trigger {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-2);
  padding: 4px 10px;
  height: 28px;
  border: 1px dashed var(--bl);
  border-radius: var(--radius-pill);
  background: transparent;
  color: var(--ink-3);
  font-size: var(--text-xs);
  cursor: pointer;
}
.kanban-phase-stepper .phs-archived-trigger:hover {
  color: var(--ink-1);
  border-style: solid;
}
.kanban-phase-stepper .phs-archived-trigger.filtered {
  border-color: var(--amber);
  color: var(--amber);
  border-style: solid;
}
.kanban-phase-stepper .phs-archived-trigger .ic { opacity: 0.7; }
.kanban-phase-stepper .phs-archived-trigger .count {
  font-variant-numeric: tabular-nums;
  background: var(--s2);
  border-radius: var(--radius-pill);
  padding: 0 6px;
  min-width: 18px;
  text-align: center;
}

.kanban-phase-stepper .phs-archived-pop {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  z-index: 10;
  min-width: 280px;
  max-height: 360px;
  overflow-y: auto;
  background: var(--s3);
  border: 1px solid var(--bl);
  border-radius: var(--radius-md);
  padding: 4px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.kanban-phase-stepper .phs-archived-row {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px 10px;
  background: transparent;
  border: 0;
  text-align: left;
  color: var(--ink-2);
  cursor: pointer;
  border-radius: var(--radius-sm);
}
.kanban-phase-stepper .phs-archived-row:hover  { background: var(--s2); color: var(--ink-1); }
.kanban-phase-stepper .phs-archived-row.on     { background: var(--s2); color: var(--amber); }
.kanban-phase-stepper .phs-archived-row .name  { font-size: var(--text-sm); font-weight: 500; }
.kanban-phase-stepper .phs-archived-row .meta  { display: flex; gap: var(--sp-2); font-size: var(--text-xs); color: var(--ink-3); }
.kanban-phase-stepper .phs-archived-row .reason {
  font-style: italic;
}
```

- [ ] **Step 4: Manual smoke**

Run viewer. In a project that has archived phases (CodeMaestro), check:
- Pill `Archived (N)` shows on the left of the carousel.
- Clicking opens the popover.
- Clicking a row sets the filter; pill highlights amber.
- Archived phases NO LONGER appear in past or future regions.
- In a project without archived phases (e.g. claude-tools today), the pill is hidden.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/archived-phases-dropdown.js plugins/taskmaster/viewer/js/components/phase-stepper.js plugins/taskmaster/viewer/css/screens/kanban.css
git commit -m "feat(viewer): archived phases dropdown at left edge of stepper"
```

---

## Task 6: Epic dropdown panel component

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/epic-dropdown.js`

Standalone panel with filter input, sort selector, multiselect rows with pin/unpin. Used by the rewritten epic chips in Task 7.

- [ ] **Step 1: Implement the panel**

```javascript
// plugins/taskmaster/viewer/js/components/epic-dropdown.js
// Dropdown panel for the epic filter row. Used by epic-chips.js.
// Stateless from the caller's perspective: caller passes { epics, selectedIds, pinnedIds, sort, ... }
// and gets callbacks for: onToggleEpic, onPinToggle, onSortChange, onClearAll, onClose.

import { sortEpicsForDropdown } from '../lib/epic-ranking.js';
import { epicCssVar } from '../lib/epics.js';

const SORT_OPTIONS = [
  { key: 'count',  label: 'Task count' },
  { key: 'status', label: 'Status (active → archived)' },
  { key: 'recent', label: 'Recent activity' },
  { key: 'alpha',  label: 'Alphabetical' },
];

export function renderEpicDropdown({
  epics = [],
  selectedIds = [],
  pinnedIds = [],
  activeCounts = new Map(),
  sort = 'count',
  onToggleEpic,
  onPinToggle,
  onSortChange,
  onClearAll,
  onClose,
}) {
  const panel = document.createElement('div');
  panel.className = 'kanban-epic-dropdown';
  panel.dataset.cmp = 'epic-dropdown';

  // Header: sort selector + filter input
  const head = document.createElement('div');
  head.className = 'ed-head';

  const filterInput = document.createElement('input');
  filterInput.type = 'search';
  filterInput.className = 'ed-filter';
  filterInput.placeholder = 'Filter epics…';
  head.appendChild(filterInput);

  const sortSel = document.createElement('select');
  sortSel.className = 'ed-sort';
  for (const opt of SORT_OPTIONS) {
    const o = document.createElement('option');
    o.value = opt.key; o.textContent = opt.label;
    if (opt.key === sort) o.selected = true;
    sortSel.appendChild(o);
  }
  sortSel.addEventListener('change', () => onSortChange && onSortChange(sortSel.value));
  head.appendChild(sortSel);

  panel.appendChild(head);

  // List
  const list = document.createElement('div');
  list.className = 'ed-list';
  panel.appendChild(list);

  // Footer
  const foot = document.createElement('div');
  foot.className = 'ed-foot';
  const clearBtn = document.createElement('button');
  clearBtn.type = 'button';
  clearBtn.className = 'ed-clear';
  clearBtn.textContent = 'Clear all';
  clearBtn.addEventListener('click', () => onClearAll && onClearAll());
  const closeBtn = document.createElement('button');
  closeBtn.type = 'button';
  closeBtn.className = 'ed-close';
  closeBtn.textContent = 'Close';
  closeBtn.addEventListener('click', () => onClose && onClose());
  foot.appendChild(clearBtn);
  foot.appendChild(closeBtn);
  panel.appendChild(foot);

  const selectedSet = new Set(selectedIds);
  const pinnedSet   = new Set(pinnedIds);

  function renderList() {
    const q = filterInput.value.trim().toLowerCase();
    const sorted = sortEpicsForDropdown(epics, sort, activeCounts);
    const filtered = q ? sorted.filter(e => String(e.name || e.id || '').toLowerCase().includes(q)) : sorted;
    list.replaceChildren();
    if (!filtered.length) {
      const empty = document.createElement('div');
      empty.className = 'ed-empty';
      empty.textContent = q ? `No epics match "${q}"` : 'No epics';
      list.appendChild(empty);
      return;
    }
    for (const ep of filtered) {
      const row = document.createElement('div');
      row.className = 'ed-row';
      row.style.cssText = epicCssVar(ep.color).replace(/--epic:/g, '--ec:').replace(/--epic-soft:/g, '--ec-soft:');

      const cb = document.createElement('input');
      cb.type = 'checkbox';
      cb.checked = selectedSet.has(ep.id);
      cb.className = 'ed-check';
      cb.addEventListener('change', () => onToggleEpic && onToggleEpic(ep.id, cb.checked));
      row.appendChild(cb);

      const swatch = document.createElement('span');
      swatch.className = 'ed-swatch';
      row.appendChild(swatch);

      const name = document.createElement('span');
      name.className = 'ed-name';
      name.textContent = ep.name || ep.id;
      row.appendChild(name);

      const status = document.createElement('span');
      status.className = 'ed-status ed-status--' + (String(ep.status || 'active').toLowerCase());
      status.textContent = ep.status || 'active';
      row.appendChild(status);

      const cnt = document.createElement('span');
      cnt.className = 'ed-count';
      cnt.textContent = String(activeCounts.get(ep.id) || 0);
      row.appendChild(cnt);

      const pin = document.createElement('button');
      pin.type = 'button';
      pin.className = 'ed-pin' + (pinnedSet.has(ep.id) ? ' on' : '');
      pin.title = pinnedSet.has(ep.id) ? 'Unpin' : 'Pin';
      pin.textContent = pinnedSet.has(ep.id) ? '★' : '☆';
      pin.addEventListener('click', () => onPinToggle && onPinToggle(ep.id, !pinnedSet.has(ep.id)));
      row.appendChild(pin);

      list.appendChild(row);
    }
  }

  filterInput.addEventListener('input', renderList);
  renderList();

  // Stop propagation so clicks inside the panel don't close it.
  panel.addEventListener('click', (e) => e.stopPropagation());

  return panel;
}
```

- [ ] **Step 2: Verify imports — no test yet, this is wired in Task 7**

Run: `cd plugins/taskmaster/viewer && node --check js/components/epic-dropdown.js`
Expected: clean (no syntax errors).

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/epic-dropdown.js
git commit -m "feat(viewer): epic-dropdown panel — filter + multiselect + sort + pin"
```

---

## Task 7: Rewrite epic-chips for single-row + dropdown trigger

**Files:**
- Modify: `plugins/taskmaster/viewer/js/components/epic-chips.js`

Replace the flat-list rendering with: `All` chip → up to 5 quick chips → `+N more` trigger that opens the panel from Task 6.

- [ ] **Step 1: Rewrite the component**

Replace the entire contents of `plugins/taskmaster/viewer/js/components/epic-chips.js` with:

```javascript
// Single-row epic filter: All + up to 5 quick chips + dropdown trigger.
// Quick chips = pinned (in pin order) + top-ranked non-pinned, capped at QUICK_CAP.
// Dropdown shows the rest with filter/sort/multiselect/pin.
//
// Inputs:
//   epics:        full ranked list, each { id, name, color, status, count, last_referenced }
//   selectedIds:  array of currently-active epic filter ids
//   pinnedIds:    array of pinned epic ids (from prefs)
//   activeCounts: Map(epicId → number of todo+in-progress+in-review tasks)
//   sort:         current dropdown sort key ('count' | 'status' | 'recent' | 'alpha')
//   filterCount:  badge count for the right-side "N filters · clear all" link
//   onToggleEpics, onPinToggle, onSortChange, onClearFilters

import { epicCssVar } from '../lib/epics.js';
import { pluralize } from '../util/pluralize.js';
import { chipClickNext, CHIP_CLICK_HINT } from '../util/chip-toggle.js';
import { splitQuickAndDropdown } from '../lib/epic-ranking.js';
import { renderEpicDropdown } from './epic-dropdown.js';

export const QUICK_CAP = 5;

export function renderEpicChips({
  epics = [],
  selectedIds = [],
  pinnedIds = [],
  activeCounts = new Map(),
  sort = 'count',
  filterCount = 0,
  onToggleEpics,
  onPinToggle,
  onSortChange,
  onClearFilters,
}) {
  const wrap = document.createElement('div');
  wrap.className = 'kanban-epic-row';
  wrap.dataset.cmp = 'epic-chips';
  const sel = new Set(selectedIds);

  const lbl = document.createElement('span');
  lbl.className = 'label';
  lbl.textContent = 'Epic';
  wrap.appendChild(lbl);

  // All chip (clears epic filter only)
  const all = document.createElement('button');
  all.type = 'button';
  all.className = 'kanban-epic-chip' + (sel.size === 0 ? ' on' : '');
  all.dataset.key = '__all__';
  all.textContent = 'All';
  all.addEventListener('click', () => onToggleEpics && onToggleEpics([]));
  wrap.appendChild(all);

  // Quick chips
  const { quick, dropdown } = splitQuickAndDropdown(epics, pinnedIds, QUICK_CAP);
  for (const ep of quick) {
    const btn = chipFor(ep, sel, onToggleEpics);
    wrap.appendChild(btn);
  }

  // Dropdown trigger
  const trigger = document.createElement('button');
  trigger.type = 'button';
  trigger.className = 'kanban-epic-more';
  // The trigger always exists if there is any epic at all — even when N=0 it
  // gives access to pinning/sort. Hide only on a fully empty backlog.
  if (!epics.length) trigger.classList.add('hidden');
  trigger.innerHTML = `<span class="lbl">More</span><span class="count">${dropdown.length}</span><span class="chev">▾</span>`;
  wrap.appendChild(trigger);

  // Panel (rendered lazily, attached to wrap, toggled by trigger)
  let panel = null;
  trigger.addEventListener('click', (e) => {
    e.stopPropagation();
    if (panel && panel.isConnected) {
      panel.remove();
      panel = null;
      return;
    }
    panel = renderEpicDropdown({
      epics,                        // full list — dropdown applies its own sort/filter
      selectedIds: [...sel],
      pinnedIds,
      activeCounts,
      sort,
      onToggleEpic: (id, checked) => {
        if (checked) sel.add(id); else sel.delete(id);
        onToggleEpics && onToggleEpics([...sel]);
      },
      onPinToggle: (id, pinned) => onPinToggle && onPinToggle(id, pinned),
      onSortChange: (next) => onSortChange && onSortChange(next),
      onClearAll:   () => { sel.clear(); onToggleEpics && onToggleEpics([]); },
      onClose:      () => { if (panel) { panel.remove(); panel = null; } },
    });
    wrap.appendChild(panel);
  });

  // Close panel on outside click.
  document.addEventListener('click', (e) => {
    if (!panel) return;
    if (!wrap.contains(e.target)) { panel.remove(); panel = null; }
  });

  // Right side: filter count + clear-all link
  const right = document.createElement('div');
  right.className = 'right';
  if (filterCount > 0) {
    const fc = document.createElement('span');
    fc.className = 'filter-count';
    fc.textContent = `${filterCount} ${pluralize(filterCount, 'filter', 'filters')}`;
    right.appendChild(fc);

    const clr = document.createElement('span');
    clr.className = 'kanban-reset-link';
    clr.textContent = 'clear all';
    clr.addEventListener('click', () => onClearFilters && onClearFilters());
    right.appendChild(clr);
  }
  wrap.appendChild(right);

  return wrap;
}

function chipFor(ep, selSet, onToggleEpics) {
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'kanban-epic-chip' + (selSet.has(ep.id) ? ' on' : '');
  btn.dataset.key = ep.id;
  btn.title = CHIP_CLICK_HINT;
  btn.setAttribute('style', epicCssVar(ep.color).replace(/--epic:/g, '--ec:').replace(/--epic-soft:/g, '--ec-soft:'));
  btn.innerHTML = `<span class="marker"></span>${escapeHtml(ep.name || ep.id)}<span class="count">${ep.count || 0}</span>`;
  btn.addEventListener('click', (ev) => {
    const next = chipClickNext(ev, selSet, ep.id);
    if (onToggleEpics) onToggleEpics(next);
  });
  return btn;
}

function escapeHtml(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
```

- [ ] **Step 2: Add styles for trigger + dropdown panel**

Append to `plugins/taskmaster/viewer/css/screens/kanban.css`:

```css
/* ── Epic row: enforce single row, never wrap ────────────────────────── */
.kanban-filterbar .kanban-epic-row {
  flex-wrap: nowrap;
  overflow-x: auto;
}

/* Dropdown trigger */
.kanban-epic-more {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 26px;
  padding: 0 10px;
  background: transparent;
  border: 1px dashed var(--bl);
  border-radius: var(--radius-pill);
  color: var(--ink-3);
  font-size: var(--text-xs);
  cursor: pointer;
  flex: 0 0 auto;
}
.kanban-epic-more:hover { color: var(--ink-1); border-style: solid; }
.kanban-epic-more.hidden { display: none; }
.kanban-epic-more .count {
  font-variant-numeric: tabular-nums;
  background: var(--s2);
  border-radius: var(--radius-pill);
  padding: 0 6px;
  min-width: 16px;
  text-align: center;
}
.kanban-epic-more .chev { opacity: 0.7; }

/* Dropdown panel — anchored under the epic row */
.kanban-epic-row { position: relative; }
.kanban-epic-dropdown {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  z-index: 12;
  min-width: 360px;
  max-width: 520px;
  max-height: 420px;
  display: flex;
  flex-direction: column;
  background: var(--s3);
  border: 1px solid var(--bl);
  border-radius: var(--radius-md);
}
.kanban-epic-dropdown .ed-head {
  display: flex;
  gap: var(--sp-2);
  padding: var(--sp-2);
  border-bottom: 1px solid var(--bl);
}
.kanban-epic-dropdown .ed-filter {
  flex: 1 1 auto;
  background: var(--s2);
  border: 1px solid var(--bl);
  border-radius: var(--radius-sm);
  padding: 4px 8px;
  color: var(--ink-1);
  font-size: var(--text-sm);
}
.kanban-epic-dropdown .ed-sort {
  flex: 0 0 auto;
  background: var(--s2);
  border: 1px solid var(--bl);
  border-radius: var(--radius-sm);
  padding: 4px 8px;
  color: var(--ink-1);
  font-size: var(--text-xs);
}
.kanban-epic-dropdown .ed-list {
  flex: 1 1 auto;
  overflow-y: auto;
  padding: 4px;
}
.kanban-epic-dropdown .ed-empty {
  padding: 16px;
  text-align: center;
  color: var(--ink-3);
  font-size: var(--text-xs);
}
.kanban-epic-dropdown .ed-row {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  padding: 6px 8px;
  border-radius: var(--radius-sm);
}
.kanban-epic-dropdown .ed-row:hover { background: var(--s2); }
.kanban-epic-dropdown .ed-check { flex: 0 0 auto; }
.kanban-epic-dropdown .ed-swatch {
  flex: 0 0 auto;
  width: 10px; height: 10px;
  border-radius: 50%;
  background: var(--ec, var(--ink-3));
}
.kanban-epic-dropdown .ed-name {
  flex: 1 1 auto;
  color: var(--ink-1);
  font-size: var(--text-sm);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.kanban-epic-dropdown .ed-status {
  flex: 0 0 auto;
  font-size: var(--text-xs);
  color: var(--ink-3);
  text-transform: lowercase;
}
.kanban-epic-dropdown .ed-status--archived { color: var(--ink-4, var(--ink-3)); opacity: 0.7; }
.kanban-epic-dropdown .ed-count {
  flex: 0 0 auto;
  font-variant-numeric: tabular-nums;
  font-size: var(--text-xs);
  color: var(--ink-3);
  min-width: 24px;
  text-align: right;
}
.kanban-epic-dropdown .ed-pin {
  flex: 0 0 auto;
  background: transparent;
  border: 0;
  color: var(--ink-4, var(--ink-3));
  cursor: pointer;
  padding: 4px;
  font-size: 14px;
}
.kanban-epic-dropdown .ed-pin.on { color: var(--amber); }
.kanban-epic-dropdown .ed-foot {
  display: flex;
  justify-content: space-between;
  padding: var(--sp-2);
  border-top: 1px solid var(--bl);
}
.kanban-epic-dropdown .ed-clear,
.kanban-epic-dropdown .ed-close {
  background: transparent;
  border: 1px solid var(--bl);
  border-radius: var(--radius-sm);
  color: var(--ink-2);
  font-size: var(--text-xs);
  padding: 4px 10px;
  cursor: pointer;
}
.kanban-epic-dropdown .ed-clear:hover,
.kanban-epic-dropdown .ed-close:hover { color: var(--ink-1); border-color: var(--accent); }
```

- [ ] **Step 3: Commit (kanban.js wiring comes next; this leaves callers temporarily broken)**

The next task wires kanban.js to the new prop names. Commit the component change in isolation so kanban.js wiring is its own logical commit:

```bash
git add plugins/taskmaster/viewer/js/components/epic-chips.js plugins/taskmaster/viewer/css/screens/kanban.css
git commit -m "feat(viewer): epic-chips single-row layout with dropdown trigger and panel"
```

---

## Task 8: Wire epic chips into kanban.js — pinned state in prefs, ranked input

**Files:**
- Modify: `plugins/taskmaster/viewer/js/screens/kanban.js`

The new component takes different props than the old one: `selectedIds`, `pinnedIds`, `activeCounts`, `sort`, `onPinToggle`, `onSortChange`. Wire them up using `prefs.patch` for persistence.

- [ ] **Step 1: Update imports and pull pinned/sort from prefs**

In `plugins/taskmaster/viewer/js/screens/kanban.js`, add the import near the others at the top:

```javascript
import { countActiveTasksByEpic, rankEpics } from '../lib/epic-ranking.js';
```

In the local `state` block (around line 36), add:

```javascript
  const persistedKan = (store.getPrefs() && store.getPrefs().kanban) || {};
  // ... existing persisted/state setup ...
```

Then below the existing `state` declaration, append:

```javascript
  // Pinned epics — pin order matters; "All" stays first.
  state.pinnedEpics = Array.isArray(persistedKan.pinnedEpics) ? persistedKan.pinnedEpics.slice() : [];
  state.epicSort    = (typeof persistedKan.epicSort === 'string') ? persistedKan.epicSort : 'count';
```

(Adjust to match the existing variable names; `persistedKan` may already be defined as `persisted` — reuse it.)

- [ ] **Step 2: Replace the `renderEpicChips` call site**

Find the existing call (around line 257) and replace it with:

```javascript
    // Compute active-task counts using full task list (NOT phase-scoped — counts
    // are global to give pinning a stable signal, while the chip's `count` field
    // remains phase-scoped so quick chips reflect the current view's volume).
    const activeCounts = countActiveTasksByEpic(tasks);
    const ranked = rankEpics(epicsArr.map(ep => ({
      id: ep.id,
      name: ep.name || ep.id,
      color: epicColors[ep.id],
      status: ep.status || 'active',
      last_referenced: ep.last_referenced,
      count: tasksInPhase.filter(t => t.epic === ep.id).length,
    })), activeCounts);

    epicHost.replaceChildren(renderEpicChips({
      epics: ranked,
      selectedIds: state.filters.epics,
      pinnedIds: state.pinnedEpics,
      activeCounts,
      sort: state.epicSort,
      filterCount,
      onToggleEpics: (next) => { state.filters.epics = next; paint(); savePrefs(); },
      onPinToggle: (id, pinned) => {
        const list = state.pinnedEpics.filter(x => x !== id);
        if (pinned) list.push(id);
        state.pinnedEpics = list;
        prefs.patch({ kanban: { pinnedEpics: list } });
        paint();
      },
      onSortChange: (next) => {
        state.epicSort = next;
        prefs.patch({ kanban: { epicSort: next } });
        paint();
      },
      onClearFilters: () => {
        state.filters = { ...DEFAULT_FILTERS };
        state.collapsed = new Set();
        searchInput.value = '';
        updatePriorityChips(pri, { active: [] });
        prefs.patch({ kanban: { collapsed_columns: [] } });
        paint(); savePrefs();
      },
    }));
```

(Note: this is the same wiring the old `onClear` had, just renamed.)

- [ ] **Step 3: Manual smoke**

Run viewer. Verify:
- Epic row stays on a single line.
- Up to 5 quick chips visible. The rest reachable via `More N`.
- Open the dropdown — filter, sort, multiselect, and pin all work.
- Pinning an epic in the dropdown promotes it to the quick chips on next paint.
- Reload the page — pinned epics and sort selection persist.

- [ ] **Step 4: Commit**

```bash
git add plugins/taskmaster/viewer/js/screens/kanban.js
git commit -m "feat(viewer): wire epic-chips ranking + pinning + sort to prefs"
```

---

## Task 9: Archived screen — sidebar entry + route + screen module

**Files:**
- Create: `plugins/taskmaster/viewer/js/screens/archived.js`
- Create: `plugins/taskmaster/viewer/css/screens/archived.css`
- Modify: `plugins/taskmaster/viewer/js/main.js`
- Modify: `plugins/taskmaster/viewer/js/components/sidebar.js`
- Modify: `plugins/taskmaster/viewer/index.html`

- [ ] **Step 1: Create the screen**

```javascript
// plugins/taskmaster/viewer/js/screens/archived.js
// Archived tasks — list of all tasks with status === 'archived', grouped by epic.
// Read-only. No filters apart from search.

import { claimTopbar } from '../lib/topbar.js';
import { pluralize } from '../util/pluralize.js';
import { emptyState } from '../components/empty-state.js';

export const meta = { title: 'Archived', icon: '⌫', sidebarKey: 'archived' };

export async function mount(root, { store }) {
  const page = document.createElement('div');
  page.className = 'archived-page';

  const head = claimTopbar();
  const subcount = document.createElement('span');
  subcount.className = 'tm-subcount';
  subcount.textContent = '… archived tasks';
  head.appendChild(subcount);

  const search = document.createElement('div');
  search.className = 'tm-search';
  search.innerHTML = `<span class="icon">⌕</span><input placeholder="Filter by title or id…" /><span class="cmp-kbd">⌘K</span>`;
  const searchInput = search.querySelector('input');
  let q = '';
  let timer = null;
  searchInput.addEventListener('input', () => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => { q = searchInput.value.trim().toLowerCase(); paint(); }, 180);
  });
  head.appendChild(search);

  const list = document.createElement('div');
  list.className = 'archived-list';
  page.appendChild(list);

  root.appendChild(page);

  function paint() {
    const backlog = store.getBacklog() || { tasks: [], epics: [] };
    const tasks = (Array.isArray(backlog.tasks) ? backlog.tasks : [])
      .filter(t => String(t.status || '').toLowerCase() === 'archived');

    const filtered = q
      ? tasks.filter(t => `${t.id} ${t.title || ''}`.toLowerCase().includes(q))
      : tasks;

    subcount.textContent = `${filtered.length} ${pluralize(filtered.length, 'archived task', 'archived tasks')}`;

    list.replaceChildren();
    if (!filtered.length) {
      list.appendChild(emptyState({
        headline: q ? `No archived tasks match "${q}"` : 'No archived tasks yet',
      }));
      return;
    }

    // Group by epic id; "(no epic)" bucket for orphans.
    const groups = new Map();
    for (const t of filtered) {
      const key = t.epic || '__none__';
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(t);
    }

    for (const [epicId, items] of groups) {
      const grp = document.createElement('section');
      grp.className = 'arch-group';
      const h = document.createElement('h3');
      h.className = 'arch-group-h';
      h.textContent = epicId === '__none__' ? '— no epic —' : epicId;
      const cnt = document.createElement('span');
      cnt.className = 'arch-group-count';
      cnt.textContent = `${items.length}`;
      h.appendChild(cnt);
      grp.appendChild(h);

      for (const t of items) {
        const row = document.createElement('a');
        row.className = 'arch-row';
        row.href = `#/task/${encodeURIComponent(t.id)}`;
        row.innerHTML = `
          <span class="arch-id">${escapeHtml(t.id)}</span>
          <span class="arch-title">${escapeHtml(t.title || '')}</span>
          <span class="arch-meta">${t.phase ? escapeHtml(t.phase) : '—'}</span>
          <span class="arch-reason">${escapeHtml(t.archived_reason || '')}</span>
        `;
        grp.appendChild(row);
      }
      list.appendChild(grp);
    }
  }

  const unsub = store.subscribe('backlog', paint);
  paint();

  return () => {
    if (timer) clearTimeout(timer);
    unsub();
  };
}

function escapeHtml(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
```

- [ ] **Step 2: Create CSS**

```css
/* plugins/taskmaster/viewer/css/screens/archived.css */
.archived-page {
  padding: var(--sp-4);
}
.archived-list {
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
}
.arch-group {
  background: var(--s1);
  border: 1px solid var(--bl);
  border-radius: var(--radius-md);
  padding: var(--sp-2);
}
.arch-group-h {
  display: flex;
  align-items: baseline;
  gap: var(--sp-2);
  margin: 0 0 var(--sp-2);
  padding: var(--sp-1) var(--sp-2);
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--ink-2);
}
.arch-group-count {
  font-variant-numeric: tabular-nums;
  color: var(--ink-3);
  font-weight: 400;
}
.arch-row {
  display: grid;
  grid-template-columns: 110px minmax(220px, 1fr) 90px 1fr;
  gap: var(--sp-2);
  padding: 6px var(--sp-2);
  border-radius: var(--radius-sm);
  text-decoration: none;
  color: var(--ink-2);
  align-items: baseline;
}
.arch-row:hover { background: var(--s2); color: var(--ink-1); }
.arch-id     { font-family: var(--mono, monospace); font-size: var(--text-xs); color: var(--ink-3); }
.arch-title  { color: var(--ink-1); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.arch-meta   { font-size: var(--text-xs); color: var(--ink-3); }
.arch-reason { font-size: var(--text-xs); color: var(--ink-3); font-style: italic; }
```

- [ ] **Step 3: Register the route in main.js**

In `plugins/taskmaster/viewer/js/main.js`, add the line right after the other `registerScreen` calls:

```javascript
registerScreen('/archived',   () => import('./screens/archived.js'));
```

- [ ] **Step 4: Add the sidebar entry**

In `plugins/taskmaster/viewer/js/components/sidebar.js`, in the `SECTIONS` array, append a new section at the end (or add to Knowledge — choose Knowledge for consistency):

```javascript
  { label: 'Knowledge', items: [
    { key: 'lessons',  icon: '✦', label: 'Lessons',  hash: '#/lessons' },
    { key: 'issues',   icon: '⚠', label: 'Issues',   hash: '#/issues' },
    { key: 'archived', icon: '⌫', label: 'Archived', hash: '#/archived' },
  ]},
```

- [ ] **Step 5: Link the CSS**

In `plugins/taskmaster/viewer/index.html`, find the existing `<link rel="stylesheet">` lines for screen CSS and add:

```html
<link rel="stylesheet" href="css/screens/archived.css">
```

(Place it next to the other `css/screens/*.css` includes.)

- [ ] **Step 6: Manual smoke**

Run viewer. Sidebar shows `Archived` under Knowledge. Click — page renders with archived tasks grouped by epic. Search filters live.

- [ ] **Step 7: Commit**

```bash
git add plugins/taskmaster/viewer/js/screens/archived.js plugins/taskmaster/viewer/css/screens/archived.css plugins/taskmaster/viewer/js/main.js plugins/taskmaster/viewer/js/components/sidebar.js plugins/taskmaster/viewer/index.html
git commit -m "feat(viewer): archived tasks screen + sidebar entry + route"
```

---

## Task 10: Run all unit tests + Playwright smoke

**Files:** none (verification only)

- [ ] **Step 1: Run unit tests**

Run: `cd plugins/taskmaster/viewer && npm run test:unit`
Expected: PASS, including new `phase-buckets` and `epic-ranking` suites.

- [ ] **Step 2: Run Playwright smoke**

Run: `cd plugins/taskmaster/viewer && npm run test:e2e -- tests/smoke.spec.js`
Expected: PASS. (If it fails because the new dropdown/sidebar entry shifts coordinates, update the smoke selectors as needed.)

- [ ] **Step 3: Manual end-to-end check on a real backlog (e.g. CodeMaestro)**

Switch to a project with archived phases (e.g. `C:\Users\gruku\Files\Work\CodeMaestro`). Verify:
- Archived phases pill on the left of the carousel; popover opens on click; selection sets the filter.
- No archived phases in the past or future regions.
- Epic row sits on a single line. `More N` opens the dropdown panel.
- Filter input narrows the dropdown list. Each sort option reorders correctly.
- Pinning bubbles an epic into the quick chips.
- Selecting a far past phase keeps the past carousel scrolled to that phase, not snapping back home.
- Sidebar `Archived` link goes to a new screen listing archived tasks grouped by epic.

- [ ] **Step 4: Commit any test-touch-ups**

If selectors or fixtures changed:

```bash
git add plugins/taskmaster/viewer/tests/
git commit -m "test(viewer): update smoke selectors for new header layout"
```

---

## Self-Review

- **Spec coverage:**
  - Archived phases dropdown — Tasks 1, 5.
  - Archived tasks screen — Task 9.
  - Epic dropdown rewrite — Tasks 2, 6, 7, 8.
  - Phase scroll preservation — Tasks 3, 4.
- **Placeholders:** none.
- **Type consistency:** `viewState` shape `{ pastOffset, futureOffset }` consistent in stepper and kanban; `pinnedIds`/`pinnedEpics` consistent (component prop is `pinnedIds`; kanban state is `pinnedEpics`); `activeCounts` is a `Map<string, number>` everywhere.
- **Naming:** `renderEpicChips` keeps its name but its props change from `{epics, active, filterCount, onToggle, onClear}` to `{epics, selectedIds, pinnedIds, activeCounts, sort, filterCount, onToggleEpics, onPinToggle, onSortChange, onClearFilters}`. Task 7 commits the component; Task 8 commits the call-site update — between those two commits, the kanban screen is broken at HEAD. This is intentional (the diffs stay coherent) but worth noting for execution.

