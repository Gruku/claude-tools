# Entity Detail Modals + Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a modal overlay the default way task/epic detail opens (settable to full-page via a new `#/settings` screen), reusing the exact same mountable detail components the full routes render, with a kanban epic-open affordance — without duplicating rendering or breaking refresh/new-tab/deep-linking.

**Architecture:** Per `docs/superpowers/specs/2026-05-28-entity-detail-modals-design.md` (Approach A, spec-reviewed). One `openDetail(kind,id)` entry point reads `ui.detail_view_mode` (default `modal`): full → set hash; modal → `pushState` + `openDetailModal`. A document-level **capturing click interceptor** catches `<a href="#/task|epic/…">` clicks (plain left-click only) so existing links get modal behavior with zero per-link edits, while real `href`s keep refresh/new-tab on the full route. The modal host mounts the **same** components the routes use — `mountTaskDetailDocument` (refactored to render its action bar into a caller host instead of `claimTopbar()`) and `mountEpicDetail` (from C1b, already embedded-aware). `router.js` listens only to `hashchange`, so the modal owns `popstate` (Back closes it) with no collision.

**Tech Stack:** Vanilla ES-module viewer (no build); `node:test` for pure logic; Playwright for e2e (`run_smoke.sh` boots `_make_server`). No Python/MCP change — the view-mode pref rides the existing free-form `/api/viewer/prefs` blob.

**Dependency & phasing:** The **task half needs no C1b**. Phases 1–4 ship a fully working task modal + settings against the existing task detail. Phase 5 adds the epic kind and the kanban `↗` and is **blocked on Plan C1b** landing `mountEpicDetail` + `getEpic`.

**Scope guardrails:**
- Does NOT touch the field-**edit** modal (`components/edit/entity-modal.js`); this is a separate read-only **detail** modal.
- In `chrome:'embedded'` mode the task detail **omits the Edit/Archive actions** (no edit-modal stacked over detail-modal in v1).
- Leave the stale `smoke.spec.js` sidebar count alone (out of scope).

**Reference (verbatim ground truth):**
- `components/task-detail-document.js`: `mountTaskDetailDocument(root, ctx)` (25), `mountTopbar({prefs,onToggleVariant,task,onEdit})` calling `claimTopbar()` (53–70).
- `lib/topbar.js`: `claimTopbar` (6), `tmSegmented` (94), `tmAction` (124).
- `components/card.js`: card click `location.hash = '#/task/'+id` (47–50).
- `components/epic-chips.js`: `chipFor(ep, selSet, onToggleEpics)` builds each `<button>` (127–140).
- `components/edit/entity-modal.js`: overlay conventions — `#entity-modal-host`, `.em-overlay`, scrim/Esc close, `body.em-open`, returns `doClose` (the read modal mirrors these).
- `screens/task-detail.js`: fetch→mount-component wrapper (the route, unchanged); `onToggleVariant` reload path stays route-only.
- `main.js`: `registerScreen` block (11–26), `boot()` mounts sidebar/router (78–94); `store`/`api`/`prefs` singletons (1–3).
- `router.js`: `window.addEventListener('hashchange', go)` — **no popstate listener** (24).
- `js/api.js`: `getTaskFull`/`getTaskRelatedFull` via `store.js` (`getTaskFull` is in `store.js`), `getEpic` (added by C1b).
- `js/store.js`: `store.getPrefs()`, `store.subscribe(key, fn)`, `store.getBacklog()` singleton.

---

## Phase 1 — Pure foundations (node:test)

### Task 1: `view-mode.js` — selector, href parser, interceptor predicate

**Files:**
- Create: `plugins/taskmaster/viewer/js/lib/view-mode.js`
- Test: `plugins/taskmaster/viewer/tests/unit/view-mode.test.js` (new)

- [ ] **Step 1: Write the failing test**

```javascript
// plugins/taskmaster/viewer/tests/unit/view-mode.test.js
import test from 'node:test';
import assert from 'node:assert/strict';
import { detailViewMode, parseDetailHref, shouldInterceptDetailLink } from '../../js/lib/view-mode.js';

test('detailViewMode — default modal, explicit full, malformed→modal', () => {
  assert.equal(detailViewMode(undefined), 'modal');
  assert.equal(detailViewMode({}), 'modal');
  assert.equal(detailViewMode({ ui: { detail_view_mode: 'full' } }), 'full');
  assert.equal(detailViewMode({ ui: { detail_view_mode: 'nonsense' } }), 'modal');
});

test('parseDetailHref — extracts {kind,id} for task/epic, null otherwise', () => {
  assert.deepEqual(parseDetailHref('#/task/T-1'), { kind: 'task', id: 'T-1' });
  assert.deepEqual(parseDetailHref('#/epic/asset-engine'), { kind: 'epic', id: 'asset-engine' });
  assert.deepEqual(parseDetailHref('#/task/T%2D1'), { kind: 'task', id: 'T-1' }); // decoded
  assert.equal(parseDetailHref('#/kanban'), null);
  assert.equal(parseDetailHref('#/task/'), null);  // no id
  assert.equal(parseDetailHref('#/task/T-1/related'), null); // sub-path, leave alone
});

test('shouldInterceptDetailLink — modal + plain left-click on a detail href only', () => {
  const base = { href: '#/task/T-1', mode: 'modal', button: 0,
                 metaKey: false, ctrlKey: false, shiftKey: false, altKey: false };
  assert.equal(shouldInterceptDetailLink(base), true);
  assert.equal(shouldInterceptDetailLink({ ...base, mode: 'full' }), false);      // full mode
  assert.equal(shouldInterceptDetailLink({ ...base, button: 1 }), false);          // middle-click
  assert.equal(shouldInterceptDetailLink({ ...base, metaKey: true }), false);      // cmd-click
  assert.equal(shouldInterceptDetailLink({ ...base, ctrlKey: true }), false);      // ctrl-click
  assert.equal(shouldInterceptDetailLink({ ...base, href: '#/lessons' }), false);  // not a detail href
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `node --test plugins/taskmaster/viewer/tests/unit/view-mode.test.js`
Expected: FAIL — `ERR_MODULE_NOT_FOUND` (`view-mode.js` missing).

- [ ] **Step 3: Implement `view-mode.js`**

```javascript
// plugins/taskmaster/viewer/js/lib/view-mode.js
// Pure helpers for the detail modal-vs-full presentation. No DOM/imports —
// node:test-covered, consumed by open-detail.js and the settings screen.

const MODES = new Set(['modal', 'full']);

export function detailViewMode(prefs) {
  const m = prefs?.ui?.detail_view_mode;
  return MODES.has(m) ? m : 'modal';
}

// '#/task/<id>' | '#/epic/<id>'  ->  {kind,id} ; anything else (incl. sub-paths) -> null
export function parseDetailHref(href) {
  const m = /^#\/(task|epic)\/([^/]+)$/.exec(String(href || ''));
  if (!m) return null;
  let id;
  try { id = decodeURIComponent(m[2]); } catch { id = m[2]; }
  if (!id) return null;
  return { kind: m[1], id };
}

export function shouldInterceptDetailLink({ href, mode, button, metaKey, ctrlKey, shiftKey, altKey }) {
  if (mode !== 'modal') return false;
  if (button !== 0) return false;
  if (metaKey || ctrlKey || shiftKey || altKey) return false;
  return parseDetailHref(href) !== null;
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `node --test plugins/taskmaster/viewer/tests/unit/view-mode.test.js`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/viewer/js/lib/view-mode.js plugins/taskmaster/viewer/tests/unit/view-mode.test.js
git commit -m "feat(viewer): view-mode selector + detail-href parser + interceptor predicate"
```

---

## Phase 2 — Embedded-chrome refactor of task detail

### Task 2: `mountTaskDetailDocument` renders actions into a caller host when embedded

**Files:**
- Modify: `plugins/taskmaster/viewer/js/components/task-detail-document.js` (`mountTaskDetailDocument` ctx pass-through, line 29–37; `mountTopbar`, 53–70)
- Test: existing `plugins/taskmaster/viewer/tests/task-detail.spec.js` must still pass (page mode unchanged); embedded mode is exercised by the modal e2e in Task 4.

> The route (`screens/task-detail.js`) passes no `chrome`, so it defaults to `'page'` and behaves exactly as today. Only the modal will pass `chrome:'embedded'` + `actionsHost`.

- [ ] **Step 1: Parameterize `mountTopbar`**

In `task-detail-document.js`, replace `mountTopbar` (lines 53–70) with:

```javascript
function mountTopbar({ prefs, onToggleVariant, task, onEdit, chrome = 'page', actionsHost = null }) {
  // 'page' → claim the global topbar (route screen). 'embedded' → render into
  // the caller-supplied host (modal header) and OMIT Edit/Archive (no stacked
  // edit modal in v1). Never claimTopbar() when embedded.
  const host = chrome === 'embedded' ? actionsHost : claimTopbar();
  if (!host) return;
  const view = prefs?.screens?.task_detail?.view === 'B' ? 'B' : 'A';
  const seg = tmSegmented(
    [
      { key: 'A', label: 'Document' },
      { key: 'B', label: 'Graph' },
    ],
    { value: view, onChange: (v) => onToggleVariant?.(v) },
  );
  host.append(seg);
  if (chrome === 'embedded') return;  // modal shows no Edit/Archive in v1
  const editBtn = tmAction({
    icon: '✎', label: 'Edit', title: 'Edit task',
    onClick: () => onEdit?.(),
  });
  const archiveBtn = tmAction({ icon: '✕', label: 'Archive', title: 'Archive task — coming soon', disabled: true });
  host.append(editBtn, archiveBtn);
}
```

- [ ] **Step 2: Thread `chrome`/`actionsHost` through the mount entry**

In `mountTaskDetailDocument` (line 29), the `mountTopbar({ ...ctx, onEdit: … })` call already spreads `ctx`, so `chrome` and `actionsHost` flow through automatically once callers pass them. No change needed there beyond confirming the spread. Verify the call reads:

```javascript
  mountTopbar({
    ...ctx,
    onEdit: () => {
      import('./edit/task-actions.js').then(({ openTaskEditModal }) => {
        openTaskEditModal({ store: ctx.store, api: ctx.api, task: ctx.task });
      });
    },
  });
```

(`...ctx` carries `chrome`/`actionsHost` when the modal supplies them; the route omits them → defaults apply.)

- [ ] **Step 3: Verify the route is unregressed**

Run: `bash plugins/taskmaster/viewer/tests/run_smoke.sh` (focus: `task-detail.spec.js`).
Expected: PASS — page mode still claims the topbar and shows Document/Graph + Edit + Archive exactly as before.

- [ ] **Step 4: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/task-detail-document.js
git commit -m "feat(viewer): task detail renders actions into a caller host in embedded mode"
```

---

## Phase 3 — Detail modal host + open-detail (tasks)

### Task 3: `detail-modal.js` overlay host

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/detail-modal.js`
- Create: `plugins/taskmaster/viewer/css/components/detail-modal.css`
- Modify: `plugins/taskmaster/viewer/index.html` (add `<div id="detail-modal-host"></div>` beside the existing `#entity-modal-host`; add the CSS `<link>` near the other `css/components/*.css` links, line ~27)
- Test: covered by the e2e in Task 4 (the host has no entry point until `open-detail` wires it).

- [ ] **Step 1: Implement the host**

```javascript
// plugins/taskmaster/viewer/js/components/detail-modal.js
// Read-only detail overlay. Mirrors entity-modal.js mechanics (scrim/Esc close,
// dedicated host, body class) but mounts a detail COMPONENT and adds Open-full.
// One modal at a time; peeking a linked entity swaps content in place.
import { store } from '../store.js';
import { api } from '../api.js';

const HOST_ID = 'detail-modal-host';
let active = null; // { overlay, close } — single instance

function esc(s) {
  return String(s == null ? '' : s)
    .replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}

export function openDetailModal({ kind, id }) {
  // If a modal is already open, just swap its content (no new history entry).
  if (active) { active.load(kind, id); return active.close; }

  const host = document.getElementById(HOST_ID);
  if (!host) throw new Error(`#${HOST_ID} not found in DOM`);

  const overlay = document.createElement('div');
  overlay.className = 'dm-overlay';
  overlay.tabIndex = -1;
  const modal = document.createElement('div');
  modal.className = 'dm-modal';
  modal.setAttribute('role', 'dialog');
  modal.setAttribute('aria-modal', 'true');

  const header = document.createElement('div');
  header.className = 'dm-header';
  const titleEl = document.createElement('span');
  titleEl.className = 'dm-title';
  const actions = document.createElement('div');
  actions.className = 'dm-actions';            // detail component renders its action row here
  const openFull = document.createElement('a');
  openFull.className = 'dm-openfull';
  openFull.textContent = 'Open full ↗';
  const closeBtn = document.createElement('button');
  closeBtn.type = 'button';
  closeBtn.className = 'dm-close';
  closeBtn.setAttribute('aria-label', 'close');
  closeBtn.textContent = '✕';
  header.append(titleEl, actions, openFull, closeBtn);

  const bodyEl = document.createElement('div');
  bodyEl.className = 'dm-body';

  modal.append(header, bodyEl);
  overlay.appendChild(modal);
  host.appendChild(overlay);
  document.body.classList.add('dm-open');

  let disposeComponent = null;
  let cur = { kind, id };

  function route(k, i) { return `#/${k}/${encodeURIComponent(i)}`; }

  async function load(k, i) {
    cur = { kind: k, id: i };
    openFull.setAttribute('href', route(k, i));
    titleEl.textContent = i;
    actions.replaceChildren();
    bodyEl.replaceChildren();
    bodyEl.classList.add('dm-loading');
    if (disposeComponent) { disposeComponent(); disposeComponent = null; }
    try {
      if (k === 'epic') {
        const { getEpic } = await import('../api.js');
        const { mountEpicDetail } = await import('./epic-detail-document.js');
        const epic = await getEpic(i);
        titleEl.textContent = epic.name || i;
        disposeComponent = mountEpicDetail(bodyEl, {
          epic, store, chrome: 'embedded', actionsHost: actions,
          onNavigate: (tid) => load('task', tid),
        });
      } else {
        const { getTaskFull, getTaskRelatedFull } = await import('../store.js');
        const { mountTaskDetailDocument } = await import('./task-detail-document.js');
        const [task, related] = await Promise.all([getTaskFull(i), getTaskRelatedFull(i)]);
        titleEl.textContent = task?.title || i;
        disposeComponent = mountTaskDetailDocument(bodyEl, {
          task, related, prefs: store.getPrefs(), store, api,
          chrome: 'embedded', actionsHost: actions,
          onNavigate: (tid) => load('task', tid),
          // swap modal body in place instead of reloading the page
          onToggleVariant: (v) => {
            api.savePrefs({ screens: { task_detail: { view: v } } }).catch(() => {});
            load('task', i);
          },
        });
      }
    } catch (e) {
      bodyEl.innerHTML = `<div class="dm-error">Could not load ${esc(i)}: ${esc(e.message)}. `
        + `<a href="${route(k, i)}">Open full</a>.</div>`;
    } finally {
      bodyEl.classList.remove('dm-loading');
    }
  }

  function destroy() {
    if (disposeComponent) { try { disposeComponent(); } catch {} disposeComponent = null; }
    overlay.remove();
    document.body.classList.remove('dm-open');
    document.removeEventListener('keydown', onKey);
    window.removeEventListener('popstate', onPop);
    window.removeEventListener('hashchange', onHash);
    active = null;
  }

  // Esc/scrim/✕ go through history.back() so the pushed entry is consumed
  // consistently; popstate is the single real close path.
  function requestClose() { history.back(); }
  function onKey(e) { if (e.key === 'Escape') { e.preventDefault(); requestClose(); } }
  function onPop() { destroy(); }
  function onHash() { destroy(); }   // sidebar nav while open → close, don't linger

  overlay.addEventListener('click', (e) => { if (e.target === overlay) requestClose(); });
  closeBtn.addEventListener('click', requestClose);
  openFull.addEventListener('click', (e) => {
    e.preventDefault();
    history.replaceState(null, '');          // drop the modal entry
    window.removeEventListener('hashchange', onHash); // this hash change is intentional
    destroy();
    location.hash = route(cur.kind, cur.id);
  });
  document.addEventListener('keydown', onKey);
  window.addEventListener('popstate', onPop);
  window.addEventListener('hashchange', onHash);

  active = { overlay, close: destroy, load };
  queueMicrotask(() => overlay.focus());
  load(kind, id);
  return destroy;
}
```

- [ ] **Step 2: Create the CSS** (mirrors `em-` overlay; no shadow/no left-rail/no hover-motion)

```css
/* plugins/taskmaster/viewer/css/components/detail-modal.css */
body.dm-open { overflow: hidden; }
.dm-overlay {
  position: fixed; inset: 0; z-index: 60;
  display: flex; align-items: flex-start; justify-content: center;
  padding: 5vh 16px; background: rgba(6, 7, 10, 0.62);
}
.dm-modal {
  width: min(960px, 100%); max-height: 90vh; display: flex; flex-direction: column;
  background: var(--bg-shell); border: 1px solid rgba(255,255,255,0.10); border-radius: 12px;
  overflow: hidden;
}
.dm-header {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 14px; border-bottom: 1px solid rgba(255,255,255,0.07); background: var(--bg-panel);
}
.dm-title { font-weight: 600; color: var(--ink-1); margin-right: auto; min-width: 0;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.dm-actions { display: inline-flex; align-items: center; gap: 8px; }
.dm-openfull { color: var(--accent); text-decoration: none; font-size: var(--text-sm); }
.dm-close { background: none; border: none; color: var(--ink-3); font-size: 16px; cursor: pointer; }
.dm-close:hover { color: var(--ink-1); }
.dm-body { overflow: auto; padding: 0; }
.dm-body.dm-loading::after { content: 'Loading…'; display: block; padding: 24px; color: var(--ink-3); }
.dm-error { padding: 24px; color: var(--ink-2); }
.dm-error a { color: var(--accent); }
```

- [ ] **Step 3: Add the host + CSS link to index.html**

In `index.html`, near the existing `<div id="entity-modal-host">` (search for it), add a sibling:

```html
  <div id="detail-modal-host"></div>
```

And after the `conflict-banner.css` link (line ~27), add:

```html
  <link rel="stylesheet" href="css/components/detail-modal.css">
```

- [ ] **Step 4: Sanity-parse the module**

Run: `node --input-type=module -e "import('./plugins/taskmaster/viewer/js/components/detail-modal.js').then(m => { if (typeof m.openDetailModal !== 'function') throw new Error('missing'); console.log('ok'); })"`
Expected: prints `ok`.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/detail-modal.js plugins/taskmaster/viewer/css/components/detail-modal.css plugins/taskmaster/viewer/index.html
git commit -m "feat(viewer): read-only detail modal host (task + epic kinds)"
```

---

### Task 4: `open-detail.js` — entry point, interceptor, history; wire card click

**Files:**
- Create: `plugins/taskmaster/viewer/js/lib/open-detail.js`
- Modify: `plugins/taskmaster/viewer/js/main.js` (call `installDetailInterceptor()` in `boot()` after the router init, ~line 89)
- Modify: `plugins/taskmaster/viewer/js/components/card.js` (replace the click handler at 47–50)
- Test: `plugins/taskmaster/viewer/tests/detail-modal.spec.js` (new Playwright spec)

- [ ] **Step 1: Write the failing e2e test**

```javascript
// plugins/taskmaster/viewer/tests/detail-modal.spec.js
import { test, expect } from '@playwright/test';

async function setMode(page, mode) {
  await page.evaluate(async (m) => {
    await fetch('/api/viewer/prefs', {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ui: { detail_view_mode: m } }),
    });
  }, mode);
}

test.describe('Detail modal (task)', () => {
  test('modal mode: clicking a kanban card opens the overlay, Esc closes it', async ({ page }) => {
    await setMode(page, 'modal');
    await page.goto('/v3');
    await page.evaluate(() => location.hash = '#/kanban');
    const card = page.locator('.card-task').first();
    await card.waitFor();
    await card.click();
    await expect(page.locator('.dm-overlay')).toBeVisible();
    await expect(page).toHaveURL(/#\/kanban$/);          // overlay, not a route change
    await page.keyboard.press('Escape');
    await expect(page.locator('.dm-overlay')).toHaveCount(0);
  });

  test('modal mode: Open full navigates to the route and closes the overlay', async ({ page }) => {
    await setMode(page, 'modal');
    await page.goto('/v3');
    await page.evaluate(() => location.hash = '#/kanban');
    await page.locator('.card-task').first().click();
    await page.locator('.dm-openfull').click();
    await expect(page).toHaveURL(/#\/task\//);
    await expect(page.locator('.dm-overlay')).toHaveCount(0);
  });

  test('full mode: clicking a card navigates to the route, no overlay', async ({ page }) => {
    await setMode(page, 'full');
    await page.goto('/v3');
    await page.evaluate(() => location.hash = '#/kanban');
    await page.locator('.card-task').first().click();
    await expect(page).toHaveURL(/#\/task\//);
    await expect(page.locator('.dm-overlay')).toHaveCount(0);
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `bash plugins/taskmaster/viewer/tests/run_smoke.sh` (focus `detail-modal.spec.js`).
Expected: FAIL — card click still hard-navigates (no `.dm-overlay`), interceptor not installed.

- [ ] **Step 3: Implement `open-detail.js`**

```javascript
// plugins/taskmaster/viewer/js/lib/open-detail.js
// Single entry point for opening task/epic detail, honoring ui.detail_view_mode.
import { store } from '../store.js';
import { detailViewMode, parseDetailHref, shouldInterceptDetailLink } from './view-mode.js';

function routeHash(kind, id) { return `#/${kind}/${encodeURIComponent(id)}`; }

export function openDetail(kind, id) {
  const mode = detailViewMode(store.getPrefs());
  if (mode === 'full') { location.hash = routeHash(kind, id); return; }
  history.pushState({ detailModal: { kind, id } }, '');
  import('../components/detail-modal.js').then(({ openDetailModal }) => openDetailModal({ kind, id }));
}

let installed = false;
export function installDetailInterceptor() {
  if (installed) return;
  installed = true;
  document.addEventListener('click', (e) => {
    const a = e.target.closest && e.target.closest('a[href]');
    if (!a) return;
    const href = a.getAttribute('href') || '';
    const mode = detailViewMode(store.getPrefs());
    if (!shouldInterceptDetailLink({
      href, mode, button: e.button,
      metaKey: e.metaKey, ctrlKey: e.ctrlKey, shiftKey: e.shiftKey, altKey: e.altKey,
    })) return;
    const parsed = parseDetailHref(href);
    if (!parsed) return;
    e.preventDefault();
    openDetail(parsed.kind, parsed.id);
  }, true); // capture: run before screens' own link handlers
}
```

- [ ] **Step 4: Install the interceptor in `main.js`**

In `boot()`, after `routerInit({...})` (ends line 89), add:

```javascript
  // Detail-modal interception (delegated <a> clicks → openDetail when mode=modal).
  import('./lib/open-detail.js').then(({ installDetailInterceptor }) => installDetailInterceptor());
```

- [ ] **Step 5: Switch the kanban card click to `openDetail`**

In `card.js`, replace the click handler (lines 47–50) with:

```javascript
  // Click opens task detail (modal or full per ui.detail_view_mode).
  card.addEventListener('click', (ev) => {
    if (ev.target.closest('.card-id') || ev.target.closest('.card-branch') || ev.target.closest('.cmp-icon-btn')) return;
    import('../lib/open-detail.js').then(({ openDetail }) => openDetail('task', task.id));
  });
```

- [ ] **Step 6: Run the e2e to verify it passes**

Run: `bash plugins/taskmaster/viewer/tests/run_smoke.sh`
Expected: PASS — modal opens on card click in modal mode; Esc closes; Open full routes; full mode navigates with no overlay.

- [ ] **Step 7: Commit**

```bash
git add plugins/taskmaster/viewer/js/lib/open-detail.js plugins/taskmaster/viewer/js/main.js plugins/taskmaster/viewer/js/components/card.js plugins/taskmaster/viewer/tests/detail-modal.spec.js
git commit -m "feat(viewer): openDetail + delegated link interceptor; kanban card uses it"
```

---

## Phase 4 — Settings screen + pref

### Task 5: `#/settings` screen with the detail-view toggle

**Files:**
- Create: `plugins/taskmaster/viewer/js/screens/settings.js`
- Create: `plugins/taskmaster/viewer/css/screens/settings.css`
- Modify: `plugins/taskmaster/viewer/js/main.js` (register `/settings`)
- Modify: `plugins/taskmaster/viewer/js/components/sidebar.js` (new bottom section)
- Modify: `plugins/taskmaster/viewer/index.html` (CSS link)
- Test: `plugins/taskmaster/viewer/tests/settings.spec.js` (new Playwright spec)

- [ ] **Step 1: Write the failing e2e test**

```javascript
// plugins/taskmaster/viewer/tests/settings.spec.js
import { test, expect } from '@playwright/test';

test.describe('Settings', () => {
  test('toggling detail view to Full persists across reload', async ({ page }) => {
    await page.goto('/v3');
    await page.evaluate(() => location.hash = '#/settings');
    await expect(page.locator('#page-title')).toHaveText('Settings');
    await page.locator('.set-detail-view input[value="full"]').check();
    // Persisted to the prefs API.
    await page.waitForTimeout(600); // debounced savePrefs
    await page.reload();
    const prefs = await page.evaluate(async () => (await fetch('/api/viewer/prefs')).json());
    expect(prefs.ui.detail_view_mode).toBe('full');
    await page.evaluate(() => location.hash = '#/settings');
    await expect(page.locator('.set-detail-view input[value="full"]')).toBeChecked();
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `bash plugins/taskmaster/viewer/tests/run_smoke.sh` (focus `settings.spec.js`).
Expected: FAIL — `#/settings` unregistered.

> Note: this test mutates the live prefs file (`detail_view_mode: 'full'`). Add a final cleanup step in the spec if other specs assume the default — or set mode explicitly in each dependent spec (the Task 4 spec already calls `setMode`).

- [ ] **Step 3: Implement the settings screen**

```javascript
// plugins/taskmaster/viewer/js/screens/settings.js
import { claimTopbar } from '../lib/topbar.js';
import { detailViewMode } from '../lib/view-mode.js';

export const meta = { title: 'Settings', icon: '⚙', sidebarKey: 'settings' };

export async function mount(root, { store, prefs }) {
  root.innerHTML = '';
  root.classList.add('settings');
  claimTopbar();

  const current = detailViewMode(store.getPrefs());

  const sec = document.createElement('section');
  sec.className = 'set-block set-detail-view';
  sec.innerHTML = `
    <h2 class="set-h">Detail view</h2>
    <p class="set-desc">How task and epic detail opens when you click it.</p>`;

  for (const [val, label, hint] of [
    ['modal', 'Open in modal', 'A quick overlay on top of the current screen.'],
    ['full', 'Open full page', 'Navigate to the dedicated detail route.'],
  ]) {
    const row = document.createElement('label');
    row.className = 'set-radio';
    const input = document.createElement('input');
    input.type = 'radio';
    input.name = 'detail_view_mode';
    input.value = val;
    input.checked = current === val;
    input.addEventListener('change', () => {
      if (input.checked) prefs.patch({ ui: { detail_view_mode: val } });
    });
    const txt = document.createElement('span');
    txt.className = 'set-radio__txt';
    txt.innerHTML = `<span class="set-radio__label">${label}</span><span class="set-radio__hint">${hint}</span>`;
    row.append(input, txt);
    sec.appendChild(row);
  }

  root.appendChild(sec);
  return () => { root.classList.remove('settings'); };
}
```

- [ ] **Step 4: CSS, route, sidebar, link**

Create `plugins/taskmaster/viewer/css/screens/settings.css`:

```css
.settings { padding: 20px 24px; max-width: 720px; }
.set-block { margin-bottom: 28px; }
.set-h { font-size: var(--text-lg); margin: 0 0 4px; }
.set-desc { color: var(--ink-3); font-size: var(--text-sm); margin: 0 0 12px; }
.set-radio { display: flex; gap: 10px; align-items: flex-start; padding: 10px 12px; border: 1px solid rgba(255,255,255,0.07); border-radius: 8px; margin-bottom: 8px; cursor: pointer; }
.set-radio:hover { background: var(--bg-card-hover); }
.set-radio input { margin-top: 3px; }
.set-radio__label { display: block; color: var(--ink-1); font-weight: 600; }
.set-radio__hint { display: block; color: var(--ink-3); font-size: var(--text-xs); }
```

In `main.js` registerScreen block, add:

```javascript
registerScreen('/settings',   () => import('./screens/settings.js'));
```

In `sidebar.js`, append a new section after the `Structure` group (after line 31):

```javascript
  { label: 'System', items: [
    { key: 'settings', icon: '⚙', label: 'Settings', hash: '#/settings' },
  ]},
```

In `index.html`, add after the epic-detail CSS link (added by C1b) or alongside the other screen links:

```html
  <link rel="stylesheet" href="css/screens/settings.css">
```

- [ ] **Step 5: Run the e2e to verify it passes**

Run: `bash plugins/taskmaster/viewer/tests/run_smoke.sh`
Expected: PASS — Settings renders, radio flips the pref, persists across reload.

- [ ] **Step 6: Commit**

```bash
git add plugins/taskmaster/viewer/js/screens/settings.js plugins/taskmaster/viewer/css/screens/settings.css plugins/taskmaster/viewer/js/main.js plugins/taskmaster/viewer/js/components/sidebar.js plugins/taskmaster/viewer/index.html plugins/taskmaster/viewer/tests/settings.spec.js
git commit -m "feat(viewer): #/settings screen with detail-view-mode toggle"
```

---

## Phase 5 — Epic kind + kanban entry (BLOCKED ON PLAN C1b)

> Do not start until Plan C1b has merged `mountEpicDetail` (`components/epic-detail-document.js`) and `getEpic` (`api.js`). The modal host (Task 3) already imports both lazily for `kind === 'epic'`; this phase only adds the kanban entry point and an epic e2e.

### Task 6: Kanban epic `↗` open affordance + epic modal e2e

**Files:**
- Modify: `plugins/taskmaster/viewer/js/components/epic-chips.js` (`chipFor`, lines 127–140)
- Modify: `plugins/taskmaster/viewer/css/screens/kanban.css` (style `.kanban-epic-chip__open`)
- Test: `plugins/taskmaster/viewer/tests/epic-modal.spec.js` (new)

- [ ] **Step 1: Write the failing e2e test**

```javascript
// plugins/taskmaster/viewer/tests/epic-modal.spec.js
import { test, expect } from '@playwright/test';

test('modal mode: the ↗ on an epic filter chip opens the epic modal', async ({ page }) => {
  await page.evaluate(() => {}); // no-op to keep structure parallel
  await page.goto('/v3');
  // ensure modal mode
  await page.evaluate(async () => {
    await fetch('/api/viewer/prefs', { method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ui: { detail_view_mode: 'modal' } }) });
  });
  await page.evaluate(() => location.hash = '#/kanban');
  const open = page.locator('.kanban-epic-chip__open').first();
  await open.waitFor();
  await open.click();
  await expect(page.locator('.dm-overlay')).toBeVisible();
  await expect(page.locator('.dm-overlay .ed-root')).toBeVisible(); // epic detail component
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `bash plugins/taskmaster/viewer/tests/run_smoke.sh` (focus `epic-modal.spec.js`).
Expected: FAIL — no `.kanban-epic-chip__open` element exists yet.

- [ ] **Step 3: Add the `↗` affordance to `chipFor`**

In `epic-chips.js`, replace `chipFor` (lines 127–140) with:

```javascript
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
  // Open-epic affordance: a real anchor so modified-click → full route.
  const open = document.createElement('a');
  open.className = 'kanban-epic-chip__open';
  open.href = `#/epic/${encodeURIComponent(ep.id)}`;
  open.title = `Open epic ${ep.name || ep.id}`;
  open.setAttribute('aria-label', `Open epic ${ep.name || ep.id}`);
  open.textContent = '↗';
  open.addEventListener('click', (ev) => {
    ev.stopPropagation();          // don't toggle the filter
    ev.preventDefault();
    import('../lib/open-detail.js').then(({ openDetail }) => openDetail('epic', ep.id));
  });
  btn.appendChild(open);
  return btn;
}
```

- [ ] **Step 4: Style the affordance**

Append to `plugins/taskmaster/viewer/css/screens/kanban.css`:

```css
.kanban-epic-chip__open {
  margin-left: 6px; color: inherit; opacity: 0.55; text-decoration: none; font-size: 0.9em;
}
.kanban-epic-chip__open:hover { opacity: 1; }
```

- [ ] **Step 5: Run the e2e to verify it passes**

Run: `bash plugins/taskmaster/viewer/tests/run_smoke.sh`
Expected: PASS — `↗` opens the epic modal showing `.ed-root` (the `mountEpicDetail` component), without toggling the filter.

- [ ] **Step 6: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/epic-chips.js plugins/taskmaster/viewer/css/screens/kanban.css plugins/taskmaster/viewer/tests/epic-modal.spec.js
git commit -m "feat(viewer): kanban epic ↗ opens the epic detail modal"
```

---

## Phase 6 — Release

### Task 7: Version bump (plugin protocol)

**Files:**
- Modify: `plugins/taskmaster/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `plugins/taskmaster/CHANGELOG.md`

Additive viewer surface (modal, settings, interceptor) → **minor** bump.

- [ ] **Step 1: Bump all three parts** (mirror Plan C1b Task 10 mechanics)

- `plugin.json` + `marketplace.json`: next minor `X.(Y+1).0` (built on whatever C1b shipped).
- `CHANGELOG.md`:
  ```
  ## X.(Y+1).0
  - feat(viewer): entity detail modals — task/epic detail opens in a modal
    overlay by default (settable to full-page via the new #/settings screen);
    delegated link interception + history-aware close; kanban epic ↗ entry.
  ```

- [ ] **Step 2: Run the check + full JS/e2e + commit**

```bash
python scripts/check_plugin_version_bump.py --base origin/master
node --test plugins/taskmaster/viewer/tests/unit/
bash plugins/taskmaster/viewer/tests/run_smoke.sh
git add plugins/taskmaster/.claude-plugin/plugin.json .claude-plugin/marketplace.json plugins/taskmaster/CHANGELOG.md
git commit -m "chore(taskmaster): bump version for entity detail modals + settings"
```

---

## Self-Review

**Spec coverage** (against `2026-05-28-entity-detail-modals-design.md`):
- Modal as default presentation, full as escape → Tasks 4 (`openDetail` + mode) & 3 (`detail-modal` + Open-full).
- Same components, no drift → Task 2 (task embedded-chrome) + Task 3 mounting `mountTaskDetailDocument`/`mountEpicDetail`.
- Delegated `<a>` interception, real hrefs keep refresh/new-tab → Task 1 predicate + Task 4 interceptor (capture-phase, modified-click bypass).
- Back/Esc/scrim/hashchange close; Open-full uses replaceState; no router collision → Task 3 (`onPop`/`onKey`/`onHash`/`openFull`).
- `#/settings` + `detail_view_mode` pref, no server change → Task 5.
- Kanban epic `↗`, card-click switch → Tasks 6 & 4.
- Embedded-chrome spec-review finding (no `claimTopbar()` in modal; omit Edit in v1) → Task 2.
- Internal phasing: task-half (Phases 1–4) has no C1b dependency; epic (Phase 5) gated → matches spec.

**Placeholder scan:** none. Every step shows full code with exact anchors. The `kanban.css`/`index.html` link insertions reference existing sibling lines; `#detail-modal-host` is placed beside the existing `#entity-modal-host` (executor verifies the line, placement is non-critical — any body-level div works).

**Type consistency:** `openDetail(kind,id)` / `openDetailModal({kind,id})` / `parseDetailHref → {kind,id}` agree. `mountTaskDetailDocument` and `mountEpicDetail` are both called as `mount…(container, { …, chrome:'embedded', actionsHost })` returning a dispose fn. `detailViewMode(prefs)` is the single mode reader used by `openDetail`, the interceptor, and the settings radio. The modal's epic branch consumes `mountEpicDetail`'s `.ed-root` (Plan C1b Task 7) — asserted by the Phase-5 e2e.

**Known risks/follow-ups (named):** the settings spec mutates live prefs (cleanup noted in Task 5 Step 2); a full focus-trap is deferred (queueMicrotask focus only, matching `entity-modal.js`); edit-from-modal deferred (Edit omitted in embedded mode); shared overlay primitive between `em-`/`dm-` deferred (accepted duplication).
