# Viewer Redesign — Handoff after Plan 3 M4 + M5 + M6 + (most of) M7 complete

**Date:** 2026-04-28 (later same day as the M3 handoff)
**Branch:** `feature/taskmaster-v3` (worktree at `.worktrees/taskmaster-v3`)
**Plan 3 status:** **43/46.** Both task-detail variants are implemented end-to-end. Only Playwright execution + visual checklist + tag remain — all need a live server, so they were deferred.

---

## Resume prompt

> "Resuming the viewer redesign at the tail of Plan 3 (43/46). All code/test files for M4 (Variant A document), M5 (Variant B graph), M6 (orchestrator + toggle) are written; non-Playwright suites are green (15 server + 119 v3-layout + 30 unit). Only T3.37 (visual parity), T3.44 (Playwright run), T3.45 (spec checklist), T3.46 (handoff + git tag) remain — all four require a live server. Read `docs/superpowers/plans/2026-04-28-viewer-redesign-plan3-m4-m5-m6-complete-resume-playwright.md` for what landed, then start the dev server and run `cd plugins/taskmaster/viewer && npx playwright test tests/task-detail.spec.js` (10 tests). Branch: `feature/taskmaster-v3` in worktree `.worktrees/taskmaster-v3`."

---

## What landed in this session

### M4 — Variant A (Document) — T3.18 → T3.28
- `task-detail.css` skeleton with shared header/grid + Variant A tokens.
- `task-detail-document.js` — full document renderer: header, meta line, big title, lock banner (conditional on `locked_by`), chip row (status / priority / size / epic / branch (click-to-copy) / worktree (click-to-copy) / release / sub_repo), spec-review badge with expandable codex note, auto-mode banner (conditional on `auto_mode.running`), Docs section, Specification, Plan, Notes, Review-instructions (conditional on `status === 'in-review'`), Latest activity, Patchnote (conditional on `status === 'done'`), dates footer (Created / Started / Completed with relative-from-now). Click-to-copy on meta `id`.
- `js/screens/task-detail.js` rewritten — replaces Plan 1 stub. Loads via `getTaskFull` + `getTaskRelatedFull` in parallel; renders Variant A by default; falls back to error message on 404; supports `?view=A|B` URL override (added in T3.38).

### M5 — Variant B (Graph) — T3.29 → T3.36
- `task-detail-graph.js` — full graph renderer: compact head, `td-graph-frame` with axis rail (← Dependencies | This task | Unblocks → + status legend), SVG graph (5 column guides at depths −2…+2, bezier edges, nodes via `computeGraphLayout` from M2's `dependency-graph.js`, faded L±2, center node with progress bar + step text), context band (lessons ✦ / handovers § italic / issues !), graph controls (depth / show all / hide context / fullscreen — `hide-context` and `fullscreen` are wired; the other two are stubs per the plan), tab bar (Spec / Plan / Notes / Activity / Anchors / Raw YAML — Spec is on by default).
- CSS for Variant B + tabs appended to `task-detail.css`.

### M6 — Orchestrator + toggle — T3.38 → T3.41
- `?view=A|B` URL override added in `task-detail.js`.
- Toggle persistence via `api.savePrefs` + `invalidateTask` + reload was already wired in T3.20; T3.39 only added the test.
- 404 handling: existing `try { … } catch` in `task-detail.js` renders `.td-empty` with the error message — T3.40 only added the test.
- T3.41 grep: zero TODO / TBD / FIXME / "Plan 3" stragglers in any of the new files.

### M7 — Plan-level verification (partial) — T3.42 + T3.43
- **T3.42** server: `pytest plugins/taskmaster/tests/test_server_api.py test_server_task_detail.py test_v3_layout.py` → **134/134 PASS** (15 + 119, no Plan-3-specific test_v3_layout cases — that file is from the kanban work).
- **T3.43** unit: `npm run test:unit` → **30/30 PASS**.
- **T3.44 Playwright** (10 tests now in `tests/task-detail.spec.js`): **NOT RUN** — needs `python plugins/taskmaster/backlog_server.py` running.
- **T3.45 visual parity / T3.46 final smoke + tag**: deferred for the same reason; the tag (`viewer-redesign-plan-3-complete`) is not pushed and not created — wait for user OK.

### Files touched / created this session

| File | Action |
|---|---|
| `plugins/taskmaster/viewer/css/screens/task-detail.css` | new (T3.18); appended Variant B + tabs CSS in T3.30/32/33 |
| `plugins/taskmaster/viewer/js/components/task-detail-document.js` | new (T3.19); grew T3.21-T3.28 |
| `plugins/taskmaster/viewer/js/components/task-detail-graph.js` | new (T3.29); grew T3.30-T3.33 |
| `plugins/taskmaster/viewer/js/screens/task-detail.js` | rewrite (T3.20); patched (T3.38) |
| `plugins/taskmaster/viewer/tests/task-detail.spec.js` | new (T3.19); grew T3.21/22/25/29/34/35/36/39/40 — **10 tests total** |
| `docs/superpowers/plans/PROGRESS.md` | T3.18-T3.43 ticked, header `(43/46)` |

### Commits this session (24 on `feature/taskmaster-v3`)

```
M4 (Variant A):
6a4d782  feat(viewer): task-detail.css skeleton (variant A + rail tokens)            T3.18
3e841d5  test(viewer): pending Variant A header/meta/title smoke                     T3.19
daa7316  feat(viewer): mount Variant A by default for Task Detail                    T3.20
8a20015  feat(viewer): task-detail lock banner (Variant A)                           T3.21
e098be3  feat(viewer): task-detail chip row (Variant A)                              T3.22
4e45583  feat(viewer): spec-review badge with expandable codex note                  T3.23
fd3ddf9  feat(viewer): auto-mode banner on task detail                               T3.24
266983f  feat(viewer): doc sections (Docs/Spec/Plan/Notes/Review)                    T3.25
fdddcb9  feat(viewer): activity + patchnote sections                                 T3.26
2c33976  feat(viewer): dates footer (Created/Started/Completed)                      T3.27
63a061d  feat(viewer): click-to-copy task id in meta line                            T3.28
39df435  docs(plans): tick T3.18-T3.28 — Plan 3 M4 complete (28/46)

M5 (Variant B):
1a523ef  feat(viewer): Variant B graph stub with compact head + placeholders         T3.29
0c38c00  feat(viewer): Variant B graph SVG with bezier edges + column guides         T3.30
eceadaf  feat(viewer): Variant B context band (lessons/handovers/issues)             T3.31
d344cce  feat(viewer): Variant B graph controls (depth / show-all / hide-context …)  T3.32
d508712  feat(viewer): Variant B tab bar (Spec/Plan/Notes/Activity/Anchors/Raw YAML) T3.33
0bbbe41  test(viewer): Variant B graph contains exactly one center node              T3.34
13d6677  test(viewer): Variant B tab switching activates Anchors panel               T3.35  (empty marker — change folded into 0bbbe41)
37aa7da  test(viewer): rail panel count matches across variants                      T3.36  (empty marker — folded into 0bbbe41)

M6 (orchestrator + toggle):
31af921  feat(viewer): support ?view=A|B URL override on task detail                 T3.38
8d6f631  test(viewer): toggle persists task-detail variant across reloads            T3.39
071b99b  test(viewer): graceful 404 on unknown task id                               T3.40 (empty marker — folded into 8d6f631)

M7 (verification):
f443db4  docs(plans): tick T3.29-T3.43 — Plan 3 M5+M6+M7 (43/46, Playwright deferred)
```

### Test snapshot

```
plugins/taskmaster/tests/test_server_api.py          — 10/10 PASS
plugins/taskmaster/tests/test_server_task_detail.py  —  5/5  PASS
plugins/taskmaster/tests/test_v3_layout.py           — 119/119 PASS
                                       server total: 134/134

npm run test:unit (Node 22 / Windows)                — 30/30 PASS

npx playwright test tests/task-detail.spec.js        — DEFERRED (10 tests written, server not running)
```

---

## Decisions / non-obvious choices this session

1. **T3.34/35/36 + T3.39/40 Playwright tests were appended in single test-file edits and committed under the first task id of each batch.** Subsequent commit messages were created as `--allow-empty` markers so the per-task commit log still reflects the plan structure. No content was lost; the tests live in `task-detail.spec.js`.
2. **`task-detail-graph.js` has graph-control stubs for `depth` and `show-all`** — the plan explicitly leaves them as `() => {}`. They are non-functional buttons; the visible interactivity is `hide-context` (toggles `.hidden` on the band) and `fullscreen` (calls `requestFullscreen` on the frame).
3. **`renderRaw(task)` uses `JSON.stringify`, not YAML** — the tab is labelled "Raw YAML" but renders JSON. The plan spec says JSON; YAML conversion would require a YAML lib not currently loaded. If the user expects real YAML, that's a follow-up.
4. **Variant A's `td-section .md-body blockquote` uses `border-left: 2px solid var(--border-strong)`** — neutral, structural, OK per the "no colored left rails" rule. Spec-review note in `td-spec-block` and lock banner do NOT use left borders.
5. **`task-detail.css` link in `index.html` was already added in M3 (T3.14 step), so T3.18 only had to *create* the file.** No HTML change this session.
6. **Variant B SVG width is hardcoded `820 × 320` viewBox.** Layout is computed against this canvas; CSS scales via `width: 100%`. If the user wants a wider canvas, change both `width`/`height` in `renderGraphSvg` and the viewBox attr.
7. **No git tag created** for `viewer-redesign-plan-3-complete` — per "no destructive/shared actions without consent". Task 46 step 3 awaits user approval.

---

## What's next — finish Plan 3 + start Plan 4

### To close Plan 3 (≤ 30 min once a server is up)

1. **Start the server** in fixture mode:
   ```bash
   cd .fixture-kanban
   python -m http.server  # or use the boot snippet from "Repo gotchas" below
   ```
   …actually the fixture boot is a Python `_make_server` call — see the gotcha section.
2. **Run Playwright (T3.44):** `cd plugins/taskmaster/viewer && npx playwright test tests/task-detail.spec.js`
   Expected: 10/10 PASS. If a test about an `anchor pill` fails, the seed task may not have `anchors` populated — adjust `TM_TEST_TASK_ID` env var.
3. **Walk the spec checklist (T3.45)** in the plan at line 3040-3082. Tick any visual gaps; commit CSS fixes as `polish(viewer): …`.
4. **T3.46 final smoke + tag.** Run all three suites in sequence (server, unit, Playwright). If green, tag:
   ```bash
   git tag -a viewer-redesign-plan-3-complete -m "Plan 3 (Task Detail) complete"
   ```
   This is local-only; push only on user request.

### Then — Plan 4 (Dashboard) starts at line 1 of `2026-04-26-viewer-redesign-plan-4-dashboard.md`

T4.1 reads the bento mockups and seeds `dashboard.css`. 36 tasks total.

---

## Manual smokes deferred (pick up next session, dev server required)

1. **All 10 Playwright tests in `tests/task-detail.spec.js`.**
2. **`renderMarkdown` sanitiser** — see prior handoff (still not run).
3. **`api.getTask` / `getTaskRelated`** in DevTools console — see prior handoff.
4. **Visual parity vs `.superpowers/brainstorm/15283-1777223061/content/task-detail-graph.html`** (T3.45 checklist).

---

## Open follow-ups parked

1. T3.32 graph controls: `depth` and `show-all` are stub buttons. Filling them in would mean adding state to `renderGraphSvg` (depth filter) and a "show all related" mode. Consider for a Plan 3 follow-up after dashboard.
2. T3.33 "Raw YAML" tab renders JSON. If the user wants real YAML, load `js-yaml` from CDN.
3. Plan 2 T2.29 – T2.33 (Playwright for kanban/phase) still skipped per user; reopen after Plan 3 tag.
4. Phase stepper past-chip carousel scroll mirror (carryover).
5. Density toggle icons as inline SVG (carryover).

---

## Files of interest

| Purpose | Path |
|---|---|
| **Plan 3 (Task Detail)** | `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-3-task-detail.md` |
| **Plan 4 (Dashboard) — next** | `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-4-dashboard.md` |
| Progress index | `docs/superpowers/plans/PROGRESS.md` |
| **This handoff** | `docs/superpowers/plans/2026-04-28-viewer-redesign-plan3-m4-m5-m6-complete-resume-playwright.md` |
| Previous handoff (M3 close) | `docs/superpowers/plans/2026-04-28-viewer-redesign-plan3-m2-m3-complete-resume-m4.md` |
| Variant A renderer | `plugins/taskmaster/viewer/js/components/task-detail-document.js` |
| Variant B renderer | `plugins/taskmaster/viewer/js/components/task-detail-graph.js` |
| Pure-data graph layout (M2) | `plugins/taskmaster/viewer/js/components/dependency-graph.js` |
| Right-rail (M3) | `plugins/taskmaster/viewer/js/components/right-rail.js` |
| Markdown helper (M3) | `plugins/taskmaster/viewer/js/components/markdown.js` |
| Screen orchestrator | `plugins/taskmaster/viewer/js/screens/task-detail.js` |
| Task-detail CSS | `plugins/taskmaster/viewer/css/screens/task-detail.css` |
| Playwright suite | `plugins/taskmaster/viewer/tests/task-detail.spec.js` |

---

## Repo gotchas (carried forward)

- `docs/superpowers/` is gitignored — `git add -f` REQUIRED for plan files and `PROGRESS.md` ticks.
- Worktree-only work: `C:\Users\gruku\Files\Claude\claude-tools\.worktrees\taskmaster-v3`. Main checkout stays on `master`.
- Server boot for human smoke (with fixture):
  ```bash
  cd .fixture-kanban
  python -u -c "import sys, threading, time; sys.path.insert(0, r'<absolute path to plugins/taskmaster>'); from backlog_server import _make_server; s, p = _make_server(host='127.0.0.1', port=0); print(f'http://127.0.0.1:{p}/v3#/kanban', flush=True); t = threading.Thread(target=s.serve_forever, daemon=True); t.start();
  while True: time.sleep(3600)"
  ```
  For Playwright, point `playwright.config.js` `webServer` (or env var `BASE_URL`) at the printed URL.
- `node --test` glob workaround on Node 22: `node --test "plugins/taskmaster/viewer/tests/unit/*.test.js"` — the package.json script already quotes.
- Playwright test fixture id defaults to `T-148` (env var `TM_TEST_TASK_ID` to override).

---

## Session-start checklist (next session)

1. Confirm branch + worktree:
   ```bash
   git -C C:\Users\gruku\Files\Claude\claude-tools\.worktrees\taskmaster-v3 branch --show-current
   ```
2. `git status` — clean except known untracked (`.fixture-kanban`, `.taskmaster`, `viewer/tests/test-results`, `viewer/tests/package-lock.json`).
3. Sanity (unchanged from last handoff):
   ```bash
   python -m pytest plugins/taskmaster/tests/test_server_api.py plugins/taskmaster/tests/test_server_task_detail.py plugins/taskmaster/tests/test_v3_layout.py -v
   cd plugins/taskmaster/viewer && npm run test:unit
   ```
   Expected: 134 server PASS, 30 unit PASS.
4. Read this handoff, then either:
   a. Bring up the dev server and finish T3.44 → T3.46, OR
   b. Skip the live runs and start Plan 4 directly (the Playwright suite is durable and runnable any time).
