# Entity Detail Modals + Settings

**Date:** 2026-05-28
**Status:** Approved (design) — ready for implementation plan
**Depends on:**
- [2026-05-27 Task & Epic Protocol](2026-05-27-task-epic-protocol-design.md) — Spec C1b ships the epic detail screen this feature renders in a modal. The epic side of this feature is blocked on C1b's `mountEpicDetail` component + `GET /api/epic/<id>` endpoint.

> **Relationship to C1b:** C1b (epic detail: endpoint + `mountEpicDetail` component + `/epic/<id>` screen + `/epics` list) is a separate, independently-shippable plan. This spec is the *presentation layer* over it (and over the existing task detail). Build order: **C1b → this feature.**

---

## Background

The viewer presents entity detail (tasks, and soon epics via C1b) only as full-page routes (`#/task/<id>`, `#/epic/<id>`). Opening a detail means leaving the board; getting back means navigating back. For a kanban-centric workflow — glance at the board, peek at a card, return — a full-page hop is heavyweight, and there is no way to glance at an epic's design/rollup at all (epics are filter labels only today).

Two enabling facts make a modal layer cheap:

1. **Detail rendering is already componentized.** `viewer/js/screens/task-detail.js` (the route) is a thin wrapper that fetches data and delegates to `mountTaskDetailDocument(root, {…})`. The render logic lives in a mountable component, not the route. C1b will author the epic detail the same way (`mountEpicDetail`).
2. **Overlay conventions already exist.** `viewer/js/components/edit/entity-modal.js` (the field-edit modal) establishes the host pattern: mount into a dedicated `#…-host`, `.em-overlay`/`.em-modal` with `role=dialog`/`aria-modal`, scrim-click + Escape to close, `body.em-open`, returns a `doClose()`. A *read-only* detail modal can mirror these mechanics minus the form/validation/save machinery.

## Goal

Make the **modal overlay the default way detail opens** (settable to full-page), reusing the exact same detail components the full routes render, with kanban entry points and a real settings surface — without duplicating any rendering or breaking deep-linking, refresh, or open-in-new-tab.

## Non-goals

- No bespoke/condensed modal content. The modal renders the *same* component as the full route; they cannot drift.
- No change to the field-**edit** modal (`entity-modal.js`). This is a separate, read-only **detail** modal.
- No server changes. The view-mode preference rides the existing free-form `/api/viewer/prefs` blob.
- No modal for entities beyond task + epic in v1 (the host is generic enough that issues/bugs can adopt it later, but that's out of scope).
- The C2 epic diagram is not built here; when C1b/C2 add it to `mountEpicDetail`, it appears in both modal and full automatically.

---

## Architecture (Approach A — shared components + thin modal host + delegated link interception)

### Module map

```
NEW
  viewer/js/components/epic-detail-document.js
                                        mountEpicDetail(container,{epic,deps}) — authored by C1b,
                                        consumed by BOTH the /epic/<id> screen and the modal
                                        (named to mirror components/task-detail-document.js, so it
                                        never collides with screens/epic-detail.js)
  viewer/js/components/detail-modal.js  openDetailModal({kind,id,deps}) — overlay host; fetch + mount
  viewer/js/lib/open-detail.js          openDetail(kind,id,deps) — reads ui.detail_view_mode;
                                        installDetailInterceptor(deps) — delegated <a> click handler
  viewer/js/screens/settings.js         #/settings screen (detail_view_mode radio + future prefs)
  viewer/js/screens/epics.js            epic list (C1b)
  viewer/js/screens/epic-detail.js      /epic/<id> route wrapper (C1b)

EDIT
  viewer/index.html                     + <div id="detail-modal-host">; settings/epic CSS links
  viewer/js/main.js                     register /epics /epic /settings; installDetailInterceptor()
  viewer/js/components/sidebar.js       + 'Epics' (C1b) + 'Settings' entries
  viewer/js/components/epic-chips.js    + ↗ open glyph per chip -> openDetail('epic', id)
  viewer/js/components/card.js          card primary click -> openDetail('task', id) (was hash nav)
  backlog_server.py                     + GET /api/epic/<id> (C1b; load_v3-backed)
```

### Component contract

Every detail component shares one shape:

```
mount<Entity>Detail(container, { <entity>, related?, prefs, store, api, onNavigate, onToggleVariant? })
  -> cleanup: () => void
```

- `mountTaskDetailDocument` already conforms (`{task, related, prefs, store, api, onNavigate, onToggleVariant}`).
- `mountEpicDetail` (C1b) is authored to conform (`{epic, prefs, store, api, onNavigate}`).

The route screens and the modal host are both just **"fetch → mount component → return cleanup."** No rendering logic lives in either; it lives only in the component. This is what guarantees modal and full can never diverge.

### Detail modal host (`detail-modal.js`)

`openDetailModal({kind, id, deps})`:

1. Mounts `.dm-overlay > .dm-modal` (role=dialog, aria-modal) into `#detail-modal-host`; adds `body.dm-open`.
2. Header: entity id/title + an **Open full** button + a `✕` close.
3. Fetches via the same client functions the routes use (`getEpic(id)` / `getTaskFull(id)`+`getTaskRelatedFull(id)`), shows a lightweight loading state, then mounts the matching component into `.dm-body`. `onNavigate` from inside the modal re-targets the modal to the new id (peeking a linked task swaps modal content rather than stacking overlays).
4. Returns `doClose()`.

Mechanics mirror `entity-modal.js`: scrim-click closes, Escape closes, `✕` closes. No dirty-check/confirm (read-only).

### Navigation & history (`open-detail.js`)

`openDetail(kind, id, deps)` reads `store.getPrefs()?.ui?.detail_view_mode` (default `'modal'`):

- `'full'` → `location.hash = '#/' + kind + '/' + id` (`task`/`epic`). Existing route behavior, unchanged.
- `'modal'` → `history.pushState({detailModal:{kind,id}}, '')` then `openDetailModal({kind,id,deps})`.

`installDetailInterceptor(deps)` (called once in `main.js`): a **capturing document `click` listener** matches `a[href^="#/task/"]` and `a[href^="#/epic/"]`. When `detail_view_mode==='modal'` and it's a plain left-click (no modifier keys, button 0), it `preventDefault()`s, parses `{kind,id}` from the href, and calls `openDetail`. Because the anchors keep real `href`s:

- middle-click / ⌘/Ctrl-click / "open in new tab" → browser follows the href → **full route** (no interception of modified clicks).
- refresh / paste URL / external link → loads the **full route** (fresh load is never a modal; the modal is only ever opened by an in-app action).

This makes "modal everywhere" work for *every* existing detail link (issue-detail link pills, epics-list rows, task-detail relations) with **zero per-link changes** — only programmatic navigators (the kanban card click) switch to `openDetail()`.

### Close paths & history consistency

- **Browser Back** (`popstate`): opening pushed exactly one entry; Back pops it. The modal listens for `popstate` and closes — returning to the board with no route change.
- **Esc / scrim / ✕**: call `history.back()` (which triggers the same `popstate` close), keeping the history stack clean.
- **Open full** (button in modal header): `history.replaceState(null,'')` then `location.hash = route` — replaces the dangling modal entry with the real route instead of leaving an orphan in the stack.

---

## Settings screen & preference

- New preference: `ui.detail_view_mode ∈ {"modal","full"}`, default `"modal"`. Stored in the existing free-form viewer-prefs JSON via `prefs.patch({ui:{detail_view_mode:…}})`; read with `store.getPrefs()`. **No server schema change.**
- `#/settings` screen (`meta={title:'Settings', sidebarKey:'settings'}`): a "Detail view" radio group — `● Open in modal / ○ Open full page` — bound to the pref. Structured to grow (theme, density, polling) but ships with this one control.
- Sidebar gains a **Settings** entry (its own bottom section) and an **Epics** entry (C1b).
- A pure selector `detailViewMode(prefs) -> 'modal'|'full'` (default-applying) is the single read path, used by `openDetail`, the interceptor predicate, and the settings radio — so default logic lives in one testable place.

## Kanban entry points

- `epic-chips.js`: filter chips keep click = filter; each gains a small `↗` button → `openDetail('epic', id, deps)`. The `↗` is a real `<a href="#/epic/<id>">` so modified-click still opens the full route.
- `card.js`: the card's primary open action switches from `location.hash = '#/task/'+id` to `openDetail('task', id, deps)`. Drag and other handlers are untouched.

## Data flow

Modal and route share fetches — no new endpoints beyond C1b's `GET /api/epic/<id>`:

```
openDetail('epic', id)  --modal-->  openDetailModal --> getEpic(id)          --> /api/epic/<id> (load_v3)
                        --full -->   #/epic/<id> screen --> getEpic(id)       --> /api/epic/<id>
openDetail('task', id)  --modal-->  openDetailModal --> getTaskFull(id)+related
                        --full -->   #/task/<id> screen --> getTaskFull(id)+related
```

The modal fetches on open (no extra caching beyond the store's existing behavior).

## Error handling

- Modal fetch failure → the modal body shows an inline error with an "Open full" link (the full route renders its own richer empty/error state). The overlay still closes normally.
- Unknown id → `/api/epic/<id>` returns 404; modal shows "not found" with a back-to-list link; the full route already handles this.
- `#detail-modal-host` missing → `openDetailModal` throws (developer error, same as `entity-modal.js`); guarded by index.html adding the host.

## Testing

- **pytest** (C1b, listed here for completeness): `_load_epic_full` / `GET /api/epic/<id>` on the `tm_epic_phase` fixture — heavy-field merge via `load_v3`, component rollup, attention list, 404.
- **node:test (pure units):**
  - `epic-format.js` helpers (C1b): design badge, component glyph, progress percent, task grouping.
  - `detailViewMode(prefs)` selector — default `'modal'`, explicit `'full'`, malformed prefs.
  - interceptor predicate `shouldInterceptDetailLink({href, mode, button, modifiers})` — matches task/epic hrefs only when mode `modal` + plain left-click; ignores modified clicks and other hrefs.
- **Playwright e2e** (dedicated specs; the already-stale `smoke.spec.js` sidebar-count is left untouched, out of scope):
  - epic full route `#/epic/<id>` resolves & renders; `/epics` list renders; `/settings` radio flips the pref and it persists across reload.
  - modal opens from a kanban epic `↗`; Esc, scrim-click, and browser Back each close it; "Open full" lands on `#/epic/<id>` and leaves no extra Back entry.
  - with `detail_view_mode='full'`, a kanban card click navigates to `#/task/<id>` (no overlay).

## Decomposition & sequencing

| Plan | Scope | Depends on |
|---|---|---|
| **C1b — Epic detail** (separate spec/plan) | `GET /api/epic/<id>`; `mountEpicDetail` component; `/epic/<id>` screen; `/epics` list; sidebar Epics entry; `epic-format.js` | — |
| **Entity Detail Modals + Settings** (this spec) | `detail-modal.js`; `open-detail.js` + interceptor + history; `#/settings` + `detail_view_mode` pref + sidebar Settings entry; kanban epic `↗`; card-click switch | C1b (epic side); existing task detail |

Each plan ends with a **taskmaster version bump** (plugin.json + marketplace.json + CHANGELOG) per the repo's plugin-versioning protocol, since both touch `plugins/taskmaster/` source.

## Open questions (deferred, not blocking)

- **Modal for other entities** (issues/bugs/lessons): the host is generic; adopting it elsewhere is a later, additive step.
- **Per-entity view-mode** (separate task vs epic defaults): v1 uses one global toggle (opinionated default). Split only if a real need appears.
- **Focus trap / a11y polish** inside the detail modal: mirror `entity-modal.js`'s focus-first behavior in v1; a full focus-trap is a follow-up if needed.
