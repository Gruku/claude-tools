# Viewer Redesign — Handoff after Plan 3 M1 (server endpoints) complete

**Date:** 2026-04-28
**Branch:** `feature/taskmaster-v3` (worktree at `.worktrees/taskmaster-v3`)
**Plan 3 status:** **6/46 — M1 complete.** All server endpoints for Task Detail are in. Resume at **T3.7** (M2 — Pure-Data Graph Layout).

---

## Resume prompt

> "Resuming the viewer redesign at Plan 3 M2 — Pure-Data Graph Layout. M1 is complete (6/46): server endpoints `GET /api/task/<id>` + `/related` are implemented and tested (15/15 server tests green). Read `docs/superpowers/plans/2026-04-28-viewer-redesign-plan3-m1-complete-resume-m2.md` for what landed, then read T3.7–T3.13 in `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-3-task-detail.md`. Confirm via `PROGRESS.md` that T3.7 is the next unchecked task. Branch: `feature/taskmaster-v3` in worktree `.worktrees/taskmaster-v3`. Use `superpowers:subagent-driven-development` if dispatching; the M2 tasks are JS-land (Node `--test`) authoring a `dependency-graph.js` layout function. Don't touch the kanban or phase stepper unless the user asks."

---

## What landed in this session

### M1 — Server Endpoints (T3.1 – T3.6, all green)

**`GET /api/task/<id>`** — merges the `backlog.yaml` index entry with the per-task markdown file at `.taskmaster/tasks/<id>.md`.
- Frontmatter keys merged into the response: `docs`, `review_instructions`, `patchnote`, `release`, `worktree`, `spec_review`, `locked_by`.
- Body sections (`## Description`, `## Notes`, `## Specification`, `## Plan`, `## Review instructions`, `## Activity`, `## Patchnote`) are split out as top-level keys (lowercased, spaces → underscores).
- Raw body preserved as `_body`.
- 404 with `{"ok": false, "error": "task <id> not found"}` for unknown ids; empty path falls through to default 404.

**`GET /api/task/<id>/related`** — builds the right-rail payload:
- `lessons` — anchor-matched (glob overlap via `fnmatch`, both directions).
- `handovers` — `.taskmaster/handovers/*.md` whose `task_ids` contains the id.
- `issues` — `.taskmaster/issues/*.md` whose `task_ids` contains the id.
- `dependencies` — forward (`me.depends_on`).
- `unblocks` — reverse (any task whose `depends_on` contains me).

**Forward-compat round-trip pinned** for `spec_review`, `patchnote`, `worktree`, `release`, `locked_by` so the v3 schema rev can land without changing the server.

### Files touched

| File | What |
|---|---|
| `plugins/taskmaster/backlog_server.py` | Added `_load_task_full`, `_load_related_for_task`, route branch in `do_GET` for `/api/task/...` (placed before `/api/backlog`). |
| `plugins/taskmaster/tests/test_server_task_detail.py` | New file. 5 tests, fixture spins up `_make_server` on a free port and seeds `backlog.yaml` + `.taskmaster/`. |
| `docs/superpowers/plans/PROGRESS.md` | T3.1 – T3.6 ticked, header now `(6/46)`. |

### Commits this session (on `feature/taskmaster-v3`)

```
ac1abfb test(taskmaster): pending GET /api/task/<id> contract                     (T3.1)
fc56336 feat(taskmaster): GET /api/task/<id> merges index + markdown body         (T3.2)
720c7ce test(taskmaster): 404 paths for GET /api/task/<id>                        (T3.3)
cacfa33 feat(taskmaster): GET /api/task/<id>/related                              (T3.4)
f87f79c test(taskmaster): pin forward-compat task fields in GET /api/task/<id>    (T3.5)
478fd46 docs(plans): tick T3.1
a60cd85 docs(plans): tick T3.2-T3.4
e38f396 docs(plans): tick T3.5-T3.6 — Plan 3 M1 complete
```

### Test snapshot

```
plugins/taskmaster/tests/test_server_api.py        — 10/10 PASS
plugins/taskmaster/tests/test_server_task_detail.py — 5/5  PASS
                                            total: 15/15 server tests green
```

---

## What's next — Plan 3 M2 (T3.7 – T3.13)

**M2 = Pure-Data Graph Layout.** Author `plugins/taskmaster/viewer/js/components/dependency-graph.js` as a deterministic, side-effect-free layout function. TDD via Node `--test` (no Playwright, no DOM).

Task list (from PROGRESS.md):

- [ ] T3.7  Author the layout function with a failing Node test (empty graph)
- [ ] T3.8  Implement empty + L0-only layout
- [ ] T3.9  Add the deep-upstream-chain test
- [ ] T3.10 Add the deep-downstream-chain test
- [ ] T3.11 Add the mixed-graph test
- [ ] T3.12 Add the cycle-handling test (deduplicated nodes)
- [ ] T3.13 Wire `node --test` into a `package.json` script

Plan section starts at line 664 of `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-3-task-detail.md`.

The exact failing test for T3.7 is in the plan (around line 670–730). Subsequent tasks layer cases on top until the layout passes the cycle-handling test in T3.12.

After T3.13, M2 closes and we move into **M3 — Shared Client Plumbing** (markdown.js, api.js extension, store cache, right-rail.js).

---

## Repo gotchas (carried forward)

- `docs/superpowers/` is gitignored — `git add -f` REQUIRED for plan files and PROGRESS.md ticks.
- Worktree-only: `C:\Users\gruku\Files\Claude\claude-tools\.worktrees\taskmaster-v3`. The main checkout is on `master`.
- Server boot for human smoke (with fixture):
  ```bash
  cd .fixture-kanban
  python -u -c "import sys, threading, time; sys.path.insert(0, r'<absolute path to plugins/taskmaster>'); from backlog_server import _make_server; s, p = _make_server(host='127.0.0.1', port=0); print(f'http://127.0.0.1:{p}/v3#/kanban', flush=True); t = threading.Thread(target=s.serve_forever, daemon=True); t.start(); \nwhile True: time.sleep(3600)"
  ```
- `node --test` glob workaround on Node 22: quote the glob — `node --test "plugins/taskmaster/viewer/tests/unit/*.test.js"`. **This is directly relevant for M2 — the new tests live there.**
- Pytest fixtures here use `monkeypatch.chdir(tmp_path)` and seed `.taskmaster/{tasks,lessons,handovers,issues}` + `backlog.yaml`. The `_load_task_full` and `_load_related_for_task` helpers all use `Path("backlog.yaml")` and `Path(".taskmaster")` relative to cwd, so any test that wants a different fixture just needs its own `monkeypatch.chdir`.
- Brainstorm files (V1–V12C) served at `/static/v3/brainstorm-phases*.html` if you need them as design reference.

---

## Open follow-ups parked from this session

None new from M1. The previously parked items still apply:

1. Phase stepper past-chip carousel doesn't yet mirror future's translateX scroll — only port if the user reports jitter.
2. No keyboard undo on column collapse — future enhancement.
3. Density toggle icons are unicode glyphs — consider inline SVG for cross-platform parity.

---

## Files of interest

| Purpose | Path |
|---|---|
| **Plan 3 (Task Detail)** | `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-3-task-detail.md` |
| Progress index | `docs/superpowers/plans/PROGRESS.md` |
| **This handoff** | `docs/superpowers/plans/2026-04-28-viewer-redesign-plan3-m1-complete-resume-m2.md` |
| Previous handoff (Plan 2 close) | `docs/superpowers/plans/2026-04-28-viewer-redesign-plan2-stepper-port-resume-plan3.md` |
| Server: task detail helpers + route | `plugins/taskmaster/backlog_server.py` (search `_load_task_full` and `/api/task/`) |
| Server: task detail tests | `plugins/taskmaster/tests/test_server_task_detail.py` |
| **Where M2 will create files** | `plugins/taskmaster/viewer/js/components/dependency-graph.js` (new), `plugins/taskmaster/viewer/tests/unit/dependency-graph.test.js` (new) |

---

## Session-start checklist (next session)

1. Confirm branch + worktree:
   ```bash
   git -C C:\Users\gruku\Files\Claude\claude-tools\.worktrees\taskmaster-v3 branch --show-current
   ```
2. `git status` — clean except known untracked (`.fixture-kanban`, `.taskmaster`, `viewer/tests/test-results`, `viewer/tests/package-lock.json`).
3. Sanity: re-run the server suite to confirm M1 still green:
   ```bash
   python -m pytest plugins/taskmaster/tests/test_server_api.py plugins/taskmaster/tests/test_server_task_detail.py -v
   ```
   Expected: 15 passed.
4. Read this handoff, then jump to T3.7 in `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-3-task-detail.md` (line ~666).
5. Confirm via `PROGRESS.md` that T3.7 is the next unchecked task.
6. M2 is small and self-contained — direct execution is fine; no need for subagent dispatch unless the user prefers it.
7. After T3.13, this handoff is stale — write a new one for M3.
