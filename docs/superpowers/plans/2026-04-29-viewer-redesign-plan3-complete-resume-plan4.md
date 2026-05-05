# Viewer Redesign — Handoff after Plan 3 fully complete (46/46)

**Date:** 2026-04-29
**Branch:** `feature/taskmaster-v3` (worktree at `.worktrees/taskmaster-v3`)
**Plan 3 status:** **46/46.** All deferred Playwright + visual + smoke work landed this session. Tag pending user OK.

---

## Resume prompt

> "Resuming the viewer redesign at the start of Plan 4 (Dashboard). Plan 3 is fully complete (46/46) — all suites green. Read `docs/superpowers/plans/2026-04-29-viewer-redesign-plan3-complete-resume-plan4.md` for what landed, then either (a) ask the user to OK the `viewer-redesign-plan-3-complete` git tag, or (b) start Plan 4 directly at T4.1 in `2026-04-26-viewer-redesign-plan-4-dashboard.md`. Branch: `feature/taskmaster-v3` in worktree `.worktrees/taskmaster-v3`."

---

## What landed this session

### T3.44 — Playwright suite — 10/10 PASS

Brought up the dev server against the kanban fixture on port 8765, ran `npx playwright test tests/task-detail.spec.js`. Two real issues surfaced and were fixed:

1. **Bug in `task-detail.js`** — the screen was reading `prefs?.screens?.task_detail?.view`, but the injected `prefs` dep is the *patch helper* (`{ patch }` from `main.js`), not the data. Actual prefs live in `store.getPrefs()`. Result: persisted `view: 'B'` never took effect; only the `?view=B` URL override worked. Fixed by reading `store.getPrefs()` and forwarding the resolved data to both renderers.
2. **Order-leakage in the spec** — tests 5/6/7 set prefs to `view: 'B'` and the value persisted on disk (in `viewer.json`) across runs, so on the second run tests 1–4 saw Variant B instead of A and failed. Fixed with a `beforeEach` that resets `view` to `'A'`.
3. **Race in the rail-parity test** — `mountRightRail` fires inside a `queueMicrotask`. The test was calling `.count()` synchronously after navigation; it occasionally returned 0. Replaced with `await expect(rail.first()).toBeVisible()` before counting.

Commit: `e74c521 fix(viewer): task-detail reads prefs from store, not from patcher`

### T3.45 — Spec coverage audit — all items present

Wrote a one-shot Playwright probe that walked the §3.9 checklist by selector and printed a `[x]/[ ]` report for both variants + the rail. Probe was deleted after audit (one-shot, not a permanent test). Live findings:

- Variant A: header back/breadcrumb/view-toggle/Edit/Archive · meta · click-to-copy id · title · chip row (status/priority/size/epic/branch) · sec-spec · sec-notes · dates footer — **all present**.
- Right rail: 6 panels (Docs, Lessons in scope, Handovers, Issues, Deps + Unblocks, Blockers) — **all present**, both variants.
- Variant B: compact head · graph frame · graph SVG with center node · edges (`path.edge-path`) · 5 column guides · axis rail (`.td-graph-rail .axis`) · status legend · context band (`.td-graph-context-band`) · 4 graph controls (depth/show-all/hide-context/fullscreen) · 6 tabs (Spec/Plan/Notes/Activity/Anchors/Raw YAML) — **all present**.
- **Only `sec-docs` was missing**, correctly — the renderer returns `null` when `task.docs` is empty, and the fixture task has no docs. Not a bug.

### T3.46 — Final integration smoke

```
server  pytest test_server_task_detail.py     5/5  PASS
unit    npm run test:unit                     30/30 PASS
e2e     npx playwright test task-detail.spec  10/10 PASS
```

`grep -RIn "TODO\|TBD\|FIXME\|implement later"` over the seven Plan 3 source files: zero matches.

**Tag NOT created.** Per the user's autonomous-mode rule about destructive/shared actions, `viewer-redesign-plan-3-complete` is held for explicit OK. Tag command:

```bash
git -C .worktrees/taskmaster-v3 tag -a viewer-redesign-plan-3-complete \
  -m "Plan 3 (Task Detail) complete: Variant A + B + rail + tests"
```

Commit: `38ab3a2 docs(plans): tick T3.44-T3.46 — Plan 3 complete (46/46)`

### Files touched this session

| File | Action |
|---|---|
| `plugins/taskmaster/viewer/js/screens/task-detail.js` | bugfix: read prefs from `store.getPrefs()` |
| `plugins/taskmaster/viewer/tests/task-detail.spec.js` | beforeEach reset; rail-parity await-then-count |
| `docs/superpowers/plans/PROGRESS.md` | T3.44/45/46 ticked, header `46/46` |
| `.fixture-kanban/backlog.yaml` | **untracked** — locally enriched task `v3-009` with description, notes, depends_on, unblocks, anchors so Playwright tests have data to assert on |

### Commits this session (2 on `feature/taskmaster-v3`)

```
e74c521  fix(viewer): task-detail reads prefs from store, not from patcher
38ab3a2  docs(plans): tick T3.44-T3.46 — Plan 3 complete (46/46)
```

---

## How to bring up the dev server (carries forward)

The handoff before this had a snippet that didn't quite work — the loader uses *relative* `Path("backlog.yaml")`, so cwd matters. Working incantation:

```bash
cd .worktrees/taskmaster-v3/.fixture-kanban
python -u -c "
import sys, threading, time
sys.path.insert(0, r'C:/Users/gruku/Files/Claude/claude-tools/.worktrees/taskmaster-v3/plugins/taskmaster')
from backlog_server import _make_server
s, p = _make_server(host='127.0.0.1', port=8765)
print(f'SERVER_UP http://127.0.0.1:{p}/v3#/kanban', flush=True)
t = threading.Thread(target=s.serve_forever, daemon=True); t.start()
while True: time.sleep(3600)
"
```

Notes:
- **Cwd MUST be the data dir** containing `backlog.yaml` and `.taskmaster/`. `TASKMASTER_ROOT` env var sets `ROOT` for identity-checks/file serving but the YAML loader reads `Path("backlog.yaml")` relative to cwd.
- Playwright config defaults to `http://127.0.0.1:8765`, override via `VIEWER_BASE_URL`.
- Run Playwright from `plugins/taskmaster/viewer/tests/` (where `node_modules` lives), **not** `viewer/`.
- Set `TM_TEST_TASK_ID=v3-009` to point tests at the enriched fixture task.
- The fixture task `v3-009` was hand-enriched in this session with description / notes / depends_on / unblocks / anchors — keep it that way or the Playwright suite will partially fail.

---

## What's next

### Option A — Close out Plan 3 cleanly (≤ 5 min)

1. User OKs the tag.
2. `git tag -a viewer-redesign-plan-3-complete -m "Plan 3 (Task Detail) complete: Variant A + B + rail + tests"`
3. Optional empty marker commit per plan T3.46 step 4.

### Option B — Start Plan 4 (Dashboard)

`docs/superpowers/plans/2026-04-26-viewer-redesign-plan-4-dashboard.md`, 36 tasks. T4.1 reads the bento mockups and seeds `dashboard.css`. Plan 4 doesn't depend on the tag.

---

## Open follow-ups parked

1. **`marked` CDN integrity blocked** in headless Chromium (logged in console). The CDN responds with a different SHA-384 than the SRI hash pinned in `index.html`. Symptom: `marked.min.js` is blocked, so any markdown body falls back to plain text. Fix path: vendor `marked@12.0.2` under `plugins/taskmaster/viewer/vendor/marked.min.js` and drop the integrity attribute (or refresh the SRI). Filed in Plan 3's "Open questions" section already.
2. **`renderRaw` is JSON, not YAML** (T3.33 carry-over). If the user wants real YAML, load `js-yaml` from CDN.
3. **Graph control stubs** — `depth` and `show-all` are non-functional `() => {}` per Plan 3 spec. Real depth filtering would need state in `renderGraphSvg`.
4. **`.fixture-kanban/` is untracked.** It carries the locally-enriched `v3-009` that the Playwright + audit tests rely on. If a future session needs to recreate it, the enriched yaml block is in this commit's `task-detail.spec.js` test fixture body or recoverable from the worktree's working copy.
5. **Plan 2 T2.29-T2.33 Playwright** still skipped per user; reopen after the Plan 3 tag if desired.
6. Phase stepper past-chip carousel scroll mirror (carryover).
7. Density toggle icons as inline SVG (carryover).

---

## Files of interest

| Purpose | Path |
|---|---|
| **Plan 3 (Task Detail) — done** | `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-3-task-detail.md` |
| **Plan 4 (Dashboard) — next** | `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-4-dashboard.md` |
| Progress index | `docs/superpowers/plans/PROGRESS.md` |
| **This handoff** | `docs/superpowers/plans/2026-04-29-viewer-redesign-plan3-complete-resume-plan4.md` |
| Previous handoff (Plan 3 M4-M7) | `docs/superpowers/plans/2026-04-28-viewer-redesign-plan3-m4-m5-m6-complete-resume-playwright.md` |
| Variant A renderer | `plugins/taskmaster/viewer/js/components/task-detail-document.js` |
| Variant B renderer | `plugins/taskmaster/viewer/js/components/task-detail-graph.js` |
| Pure-data graph layout | `plugins/taskmaster/viewer/js/components/dependency-graph.js` |
| Right-rail | `plugins/taskmaster/viewer/js/components/right-rail.js` |
| Markdown helper | `plugins/taskmaster/viewer/js/components/markdown.js` |
| **Screen orchestrator (now reads `store.getPrefs()`)** | `plugins/taskmaster/viewer/js/screens/task-detail.js` |
| Task-detail CSS | `plugins/taskmaster/viewer/css/screens/task-detail.css` |
| Playwright suite (10 tests, beforeEach resets prefs) | `plugins/taskmaster/viewer/tests/task-detail.spec.js` |
| Local fixture (untracked, enriched) | `.fixture-kanban/backlog.yaml` |

---

## Repo gotchas (carried forward, plus session learnings)

- `docs/superpowers/` is gitignored — `git add -f` REQUIRED for plan files and `PROGRESS.md` ticks.
- Worktree-only work: `C:\Users\gruku\Files\Claude\claude-tools\.worktrees\taskmaster-v3`. Main checkout stays on `master`.
- `node --test` glob workaround on Node 22: `node --test "plugins/taskmaster/viewer/tests/unit/*.test.js"` — the package.json script already quotes.
- **NEW:** Playwright's `webServer` is not configured; you must bring the server up yourself before `npx playwright test`. The `Error: locator: Test timeout` for `[data-test="meta"]` typically means "server isn't running on 8765" — `curl http://127.0.0.1:8765/api/identity` to confirm.
- **NEW:** `_load_task_full` reads `Path("backlog.yaml")` *relative to cwd*, ignoring `TASKMASTER_ROOT`. Always `cd` into the data dir before booting the server.
- **NEW:** `prefs` injected into screen `mount(...)` is the patch helper, not data. Use `store.getPrefs()` for the read side.
- **NEW:** `mountRightRail` runs inside `queueMicrotask` — Playwright tests that count panels must `await expect(...).toBeVisible()` first or the count is racy.

---

## Session-start checklist (next session)

1. Confirm branch + worktree:
   ```bash
   git -C C:\Users\gruku\Files\Claude\claude-tools\.worktrees\taskmaster-v3 branch --show-current
   ```
2. `git status` — clean except known untracked: `.fixture-kanban/`, `plugins/taskmaster/.taskmaster/`, `viewer/test-results/`, `viewer/tests/test-results/`, `viewer/tests/package-lock.json`.
3. Sanity (all should be green):
   ```bash
   python -m pytest plugins/taskmaster/tests/test_server_api.py plugins/taskmaster/tests/test_server_task_detail.py plugins/taskmaster/tests/test_v3_layout.py -q
   cd plugins/taskmaster/viewer && npm run test:unit
   ```
   Expected: 134 server PASS, 30 unit PASS.
4. Decide: tag-and-stop, or jump into Plan 4 T4.1.
