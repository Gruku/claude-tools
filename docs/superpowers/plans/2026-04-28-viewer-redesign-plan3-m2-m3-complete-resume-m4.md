# Viewer Redesign — Handoff after Plan 3 M2 + M3 complete

**Date:** 2026-04-28
**Branch:** `feature/taskmaster-v3` (worktree at `.worktrees/taskmaster-v3`)
**Plan 3 status:** **17/46 — M2 + M3 complete.** Pure-data graph layout is implemented and unit-tested; shared client plumbing (markdown render, api extension, store cache, right-rail) is in place. Resume at **T3.18** (M4 — Variant A / Document).

---

## Resume prompt

> "Resuming the viewer redesign at Plan 3 M4 — Variant A (Document). M2 + M3 are complete (17/46): `dependency-graph.js` is unit-tested (5/5 via `npm run test:unit`), `markdown.js` is wired with marked@12.0.2 CDN + allowlist sanitiser, `api.getTask`/`getTaskRelated` and `store.getTaskFull`/`getTaskRelatedFull`/`invalidateTask` are in place, and `right-rail.js` (Docs · Lessons · Handovers · Issues · Deps+Unblocks · Blockers) is built. Read `docs/superpowers/plans/2026-04-28-viewer-redesign-plan3-m2-m3-complete-resume-m4.md` for what landed, then jump to T3.18 in `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-3-task-detail.md` (~line 1505). Confirm via `PROGRESS.md` that T3.18 is the next unchecked task. Branch: `feature/taskmaster-v3` in worktree `.worktrees/taskmaster-v3`. Don't touch the kanban or phase stepper unless the user asks."

---

## What landed in this session

### M2 — Pure-Data Graph Layout (T3.7 – T3.13, all green)

`computeGraphLayout({ center, upstream, downstream, width, height })` — pure-data, no DOM, no fetch. Returns `{ columns, nodes, edges }` ready for SVG rendering by Variant B in M5.

- 5 columns at depths −2…+2; center column x = canvas midpoint.
- Nodes laid out per side with vertical stacking + ROW_GAP; siblings never overlap.
- Edges: L±1 → center direct; L±2 → through L±1 sibling if present, else center.
- Faded flag set on L±2 nodes.
- Cycle handling: a task id appearing on both sides is rendered once (upstream wins). Center-id refs on either side are dropped.
- Cubic-bezier path strings with horizontal pull at 60% on each control point; `sameRow` flag if endpoints share y.

Tests in `plugins/taskmaster/viewer/tests/unit/dependency-graph.test.js`:
1. empty graph (center only, columns shape)
2. deep upstream chain (L−2 chains through L−1)
3. deep downstream chain (mirror)
4. mixed graph (siblings stack without overlap, every L±1 connects to center)
5. cycle handling (dedup, upstream wins)

`npm run test:unit` (from `plugins/taskmaster/viewer/`) → **30/30 pass** (5 graph + 25 prior — epics/filters/time).

### M3 — Shared Client Plumbing (T3.14 – T3.17)

- **`markdown.js`** — `renderMarkdown(src)` + `mountMarkdown(el, src)`. Wraps global `window.marked`; falls back to `<pre>`-wrapped escape if marked isn't loaded. Sanitiser walks the parsed template via `TreeWalker`, drops anything outside `ALLOWED_TAGS`, strips attributes outside `ALLOWED_ATTRS`, and removes `javascript:` hrefs. Tags removed are unwrapped (children kept).
- **`index.html`** — added `<script src="https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js" integrity="sha384-..." crossorigin="anonymous">` and `<link rel="stylesheet" href="css/screens/task-detail.css">` (the css file lands in M4 T3.18; the link is a harmless 404 until then).
- **`api.js`** — added named exports `getTask(id)` and `getTaskRelated(id)`, both 404-aware (throws `Error(body.error || ...)`); also surfaced through the existing `api` object for legacy callers.
- **`store.js`** — added `_taskCache` + `_relatedCache` Maps, exported `getTaskFull(id, {force})`, `getTaskRelatedFull(id, {force})`, `invalidateTask(id)`. Surfaced through the `store` object literal too. Module is import-clean (verified via dynamic import).
- **`right-rail.js`** — `mountRightRail(root, { task, related, onNavigate })` renders six panels: Docs, Lessons in scope, Handovers, Issues, Dependencies + Unblocks, Blockers. Returns a cleanup fn. Lessons/Handovers/Issues/Blockers panels collapse to `td-empty` placeholder when empty. Deps panel is always shown (even if both lists empty) since it's the navigational backbone.

### Files touched / created

| File | Action |
|---|---|
| `plugins/taskmaster/viewer/js/components/dependency-graph.js` | new |
| `plugins/taskmaster/viewer/tests/unit/dependency-graph.test.js` | new |
| `plugins/taskmaster/viewer/package.json` | new (script `test:unit` quotes the glob for Node 22 Windows) |
| `plugins/taskmaster/viewer/js/components/markdown.js` | new |
| `plugins/taskmaster/viewer/js/components/right-rail.js` | new |
| `plugins/taskmaster/viewer/index.html` | added marked CDN script + task-detail.css link |
| `plugins/taskmaster/viewer/js/api.js` | + `getTask`, `getTaskRelated` (named + on `api`) |
| `plugins/taskmaster/viewer/js/store.js` | + cache slices, + `import { getTask, getTaskRelated }` |
| `docs/superpowers/plans/PROGRESS.md` | T3.7 – T3.17 ticked, header `(17/46)` |

### Commits this session (on `feature/taskmaster-v3`)

```
4160470  test(viewer): pending dependency-graph layout (empty case)              T3.7
eceeb94  feat(viewer): dependency-graph layout (empty + L0-only cases)           T3.8
c3af37a  test(viewer): deep upstream chain layout                                T3.9
0049855  test(viewer): deep downstream chain layout                              T3.10
b2da1f1  test(viewer): mixed graph siblings stack without overlap                T3.11
a58ea15  fix(viewer): dedupe nodes that appear on both sides of the dep graph   T3.12
c2034f4  chore(viewer): wire dependency-graph unit tests into npm test:unit      T3.13
b1fada7  docs(plans): tick T3.7-T3.13 — Plan 3 M2 complete (13/46)
6910f08  feat(viewer): markdown render helper with allowlist sanitiser           T3.14
9899542  feat(viewer): api.getTask + api.getTaskRelated                          T3.15
1951797  feat(viewer): store.getTaskFull + getTaskRelatedFull cache slices       T3.16
f3c5cc0  feat(viewer): shared right-rail component for task detail               T3.17
f2168f3  docs(plans): tick T3.14-T3.17 — Plan 3 M3 complete (17/46)
```

### Test snapshot

```
plugins/taskmaster/tests/test_server_api.py          — 10/10 PASS  (carry-over from M1)
plugins/taskmaster/tests/test_server_task_detail.py  —  5/5  PASS  (carry-over from M1)
                                              server total: 15/15

npm run test:unit (Node 22 / Windows)                — 30/30 PASS
  ├─ dependency-graph.test.js: 5
  ├─ epics.test.js, filters.test.js, time.test.js: 25
```

---

## Decisions / non-obvious choices this session

1. **Glob quoting in `test:unit`** — Node 22 on Windows can't take a bare directory as `node --test` input (errors `MODULE_NOT_FOUND` on the dir path). Script reads `node --test "tests/unit/*.test.js"` with the glob explicitly quoted. The same gotcha was already noted in the previous handoff.
2. **`store.js` function-declaration ordering** — the `store` object literal references `getTaskFull` etc. before the `function` declarations textually appear. This is fine: function declarations hoist, the Maps are only touched at call time, and the dynamic-import smoke confirmed both named and `store.*` keys are exported correctly.
3. **`right-rail.js` always renders the Deps panel** even if both lists are empty (it doesn't drop to `td-empty` like the others) because it is the navigational backbone of the rail and "this task gates nothing" is meaningful copy.
4. **Browser-console smokes (T3.14 step 3, T3.15 step 2) were not run** — no live server in this session. They're sanity checks, not gates; the sanitiser logic is straightforward and the sub-tasks are committed. Run them next time the dev server is up.

---

## What's next — Plan 3 M4 (T3.18 – T3.28)

**M4 = Variant A (Document).** Build the task detail document layout — the prose-first variant — on top of the M3 plumbing.

- [ ] T3.18 Create `task-detail.css` skeleton (Variants A + B share)
- [ ] T3.19 Stub `task-detail-document.js` and a failing Playwright test for header + meta
- [ ] T3.20 Wire `task-detail.js` to mount the document renderer (so T3.19's test passes)
- [ ] T3.21 Add the lock banner (conditional on `locked_by`)
- [ ] T3.22 Add the chip row (status / priority / size / epic / branch / worktree / release / sub_repo)
- [ ] T3.23 Add the spec-review badge with click-to-expand codex note
- [ ] T3.24 Add the auto-mode banner (conditional)
- [ ] T3.25 Add Docs / Specification / Plan / Notes / Review-instructions sections
- [ ] T3.26 Add Latest activity + Patchnote sections (conditional)
- [ ] T3.27 Add the dates footer block (Created / Started / Completed)
- [ ] T3.28 Add click-to-copy on the meta `id` chip

Plan section starts at line 1505 of `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-3-task-detail.md`. T3.18 is the CSS skeleton; T3.19 introduces a failing Playwright test which T3.20 makes pass by mounting `task-detail-document.js`.

After T3.28, M4 closes and we move into **M5 — Variant B (Graph Canvas)** — T3.29 onwards, where the `dependency-graph.js` from M2 finally gets a renderer.

---

## Repo gotchas (carried forward)

- `docs/superpowers/` is gitignored — `git add -f` REQUIRED for plan files and `PROGRESS.md` ticks.
- Worktree-only work: `C:\Users\gruku\Files\Claude\claude-tools\.worktrees\taskmaster-v3`. Main checkout stays on `master`.
- Server boot for human smoke (with fixture):
  ```bash
  cd .fixture-kanban
  python -u -c "import sys, threading, time; sys.path.insert(0, r'<absolute path to plugins/taskmaster>'); from backlog_server import _make_server; s, p = _make_server(host='127.0.0.1', port=0); print(f'http://127.0.0.1:{p}/v3#/kanban', flush=True); t = threading.Thread(target=s.serve_forever, daemon=True); t.start(); \nwhile True: time.sleep(3600)"
  ```
- `node --test` glob workaround on Node 22: the `package.json` script already quotes the glob, but ad-hoc CLI runs need it too — `node --test "plugins/taskmaster/viewer/tests/unit/*.test.js"`.
- `plugins/taskmaster/viewer/index.html` already has `<link rel="stylesheet" href="css/screens/task-detail.css">` and the marked CDN — T3.18 only needs to *create* the CSS file at that path.

---

## Manual smokes deferred (pick up next session, dev server required)

1. **`renderMarkdown` sanitiser** — open `/v3` in browser, run `import('/static/v3/js/components/markdown.js').then(m => console.log(m.renderMarkdown('# Hi\\n\\n**bold** [x](javascript:alert(1)) <script>alert(2)</script>')))` in DevTools console. Expect script tag stripped, `javascript:` href stripped, `bold` preserved.
2. **`api.getTask` / `getTaskRelated`** — `import('/static/v3/js/api.js').then(api => api.getTask('T-148'))` against a fixture backlog with `T-148` (or any real id). Expect merged JSON.

---

## Open follow-ups parked from this session

None new from M2 / M3. Previously parked items still apply:

1. Phase stepper past-chip carousel doesn't yet mirror future's translateX scroll — only port if the user reports jitter.
2. No keyboard undo on column collapse — future enhancement.
3. Density toggle icons are unicode glyphs — consider inline SVG for cross-platform parity.
4. Plan 2 T2.29 – T2.33 (Playwright) deliberately skipped per user; reopen after Plan 3 if appetite returns.

---

## Files of interest

| Purpose | Path |
|---|---|
| **Plan 3 (Task Detail)** | `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-3-task-detail.md` |
| Progress index | `docs/superpowers/plans/PROGRESS.md` |
| **This handoff** | `docs/superpowers/plans/2026-04-28-viewer-redesign-plan3-m2-m3-complete-resume-m4.md` |
| Previous handoff (M1 close) | `docs/superpowers/plans/2026-04-28-viewer-redesign-plan3-m1-complete-resume-m2.md` |
| Pure-data graph layout | `plugins/taskmaster/viewer/js/components/dependency-graph.js` |
| Graph layout tests | `plugins/taskmaster/viewer/tests/unit/dependency-graph.test.js` |
| Viewer test runner | `plugins/taskmaster/viewer/package.json` |
| Markdown helper | `plugins/taskmaster/viewer/js/components/markdown.js` |
| Right-rail component | `plugins/taskmaster/viewer/js/components/right-rail.js` |
| Viewer entry HTML | `plugins/taskmaster/viewer/index.html` (marked CDN + task-detail.css link) |
| API client | `plugins/taskmaster/viewer/js/api.js` |
| Store | `plugins/taskmaster/viewer/js/store.js` |
| **Where M4 will create files** | `plugins/taskmaster/viewer/css/screens/task-detail.css` (new — T3.18), `plugins/taskmaster/viewer/js/components/task-detail-document.js` (new — T3.19), `plugins/taskmaster/viewer/js/screens/task-detail.js` (existing stub from Plan 1 — gets the real renderer in T3.20) |

---

## Session-start checklist (next session)

1. Confirm branch + worktree:
   ```bash
   git -C C:\Users\gruku\Files\Claude\claude-tools\.worktrees\taskmaster-v3 branch --show-current
   ```
2. `git status` — clean except known untracked (`.fixture-kanban`, `.taskmaster`, `viewer/tests/test-results`, `viewer/tests/package-lock.json`).
3. Sanity:
   ```bash
   # server
   python -m pytest plugins/taskmaster/tests/test_server_api.py plugins/taskmaster/tests/test_server_task_detail.py -v
   # unit
   cd plugins/taskmaster/viewer && npm run test:unit
   ```
   Expected: 15 server pass, 30 unit pass.
4. Read this handoff, then jump to T3.18 in the plan (~line 1505).
5. Confirm via `PROGRESS.md` that T3.18 is the next unchecked task.
6. M4 introduces a Playwright test at T3.19 — Plan 1 already has Playwright wired (`viewer/tests/playwright.config.js` + `smoke.spec.js`). Add the new spec alongside `smoke.spec.js`.
7. After T3.28, this handoff is stale — write a fresh one for M5.
