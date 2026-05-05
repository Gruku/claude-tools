# Viewer Redesign — Handoff after Plan 4 fully complete (36/36)

**Date:** 2026-04-30
**Branch:** `feature/taskmaster-v3` (worktree at `.worktrees/taskmaster-v3`, local-only — never pushed)
**Plan 4 status:** **36/36.** Server, unit, and Playwright suites all green. No tag yet — Plan 5 is bigger than Plan 3 was, so the next checkpoint is naturally at Plan 5a complete.

---

## Resume prompt

> "Resuming the viewer redesign at the start of Plan 5a (Sessions / Handovers + Recap). Plan 4 (Dashboard) is fully complete (36/36) — all suites green. Read `docs/superpowers/plans/2026-04-30-viewer-redesign-plan4-complete-resume-plan5.md` for what landed and the gotchas, then start Plan 5a at T1 in `2026-04-26-viewer-redesign-plan-5a-sessions-recap.md`. Branch: `feature/taskmaster-v3` in worktree `.worktrees/taskmaster-v3`. Plan 5 is split: 5a = 33 tasks (sessions/recap, server entities + shared components + 2 screens), 5b = 32 tasks (lessons/issues screens). Run them sequentially — 5a first, since 5b reuses the `RightRail` / `Timeline` / `RecapReceiptsGrid` / `DiffRow` components that 5a introduces."

---

## What landed this session

Full Plan 4 (Dashboard) end-to-end. ~70 commits on top of the Plan 3 tag. Highlights:

### M1+M2 (T4.1–T4.10) — Foundation

- `dashboard.css` — bento grid (left rail / center board / right rail / bottom row), widget frame, edit-mode chrome, picker, drop-target outline.
- `dashboard-grid.js` — pure-data layout engine: `computePlacements`, `addWidget`, `removeWidget`, `moveWidget`. Unit tests cover ordering invariants.
- `widget-frame.js` — common chrome with size cycler.
- `briefing-strip.js`, `board-surface.js`, `widget-catalog.js` (registry).
- `screens/dashboard.js` — orchestrator skeleton.

### M3 (T4.11–T4.23) — 13 widgets

`suggested-next`, `phase-deliverables`, `newly-unblocked`, `what-changed`, `last-session`, `open-issues`, `build-test-pulse`, `lessons-digest`, `quick-capture`, `recent-commits`, `agent-activity`, `stale-tasks`, `auto-mode-stepper`.

All match the widget shape `{ meta: {id,label,sizes,defaultSize,defaultRail}, mount(el, ctx) }` and the catalog drives both the seed layout and the +Add picker.

### M4 (T4.24–T4.28) — Edit mode

`edit-mode.js` — `createEditMode`, `createAddTile`, `attachRailDropTarget`, picker overlay. Drag/drop, +Add, red-X remove, size cycler. Persistence via `api.savePrefs({ dashboard: { layout } })`.

Playwright suite (`tests/dashboard.spec.js`): 5 tests — mounts, default-seed-of-10, edit toggle reveals chrome, remove persists across reload, add-via-picker.

### M5 (T4.29–T4.32) — Server / API

- `_compute_recent_events()` + `GET /api/dashboard/recent-events?since=<iso>` in `backlog_server.py` with 3 pytest tests.
- `api.js` extensions: `getRecentEvents`, `getLastSession`, `listIssues`, `listLessons`, `getRecentCommits`, `getBuildTestPulse`, `getAutoState`, `quickCapture`.
- Last-seen timestamp stamped on screen unmount so the next visit's briefing reflects the prior visit.

### M6 (T4.33–T4.36) — Integration

Playwright initially blocked. Triaged three integration mismatches (see "Bugs fixed" below). Final sweep:

```
server  pytest                              220/220 PASS  (3 new for /api/dashboard/recent-events)
unit    npm run test:unit                    36/36  PASS  (6 new for dashboard-grid)
e2e     npx playwright test dashboard.spec    5/5   PASS
```

### Bugs fixed during M6 (the interesting bits)

1. **`renderMinimalCard` / `renderFullCard` not exported from `card.js`** — the 13 widgets imported these names, but Plan 2 shipped `renderCard({ density })`. Plan-2-vs-Plan-4 naming gap. Added shim aliases in `card.js`. Commit `6c39e39`.
2. **`createAutoModeStrip` not exported from `auto-mode-strip.js`** — `dashboard.js` imported a name that didn't exist; module load crashed silently and all 5 Playwright tests failed with no obvious signal. Wrote a factory wrapping `renderAutoModeStrip` / `updateAutoModeStrip` / `destroyAutoModeStrip` plus store subscriptions for `autoState` and `backlog`, returning `{ root, destroy }`. Commit `4c92634`.
3. **Dashboard read prefs from the patcher, not the data** — same bug Plan 3 hit (commit `e74c521`). `prefs.dashboard.layout` was always undefined → re-seeded the default 10 widgets on every load → "removing a widget persists across reload" test failed. Fixed by sourcing layout from `store.getPrefs()` at mount time, then mirroring back onto the patcher so subsequent in-session reads still resolve. Commit `4c92634`.
4. **Playwright test order leakage** — "seeds default layout with at least 10 widgets" expected exactly 10 but found 11 from the prior test that added a stale-tasks widget. Same fix pattern as Plan 3: `beforeEach` `PUT /api/viewer/prefs { dashboard: { layout: [] } }`. Commit `4c92634`.

### Files touched this session (high-level)

```
plugins/taskmaster/backlog_server.py                                 # +recent-events route
plugins/taskmaster/tests/test_server_dashboard_events.py             # NEW
plugins/taskmaster/viewer/js/api.js                                  # +8 helpers
plugins/taskmaster/viewer/js/screens/dashboard.js                    # NEW orchestrator
plugins/taskmaster/viewer/js/components/dashboard-grid.js            # NEW
plugins/taskmaster/viewer/js/components/widget-frame.js              # NEW
plugins/taskmaster/viewer/js/components/widget-catalog.js            # NEW
plugins/taskmaster/viewer/js/components/briefing-strip.js            # NEW
plugins/taskmaster/viewer/js/components/board-surface.js             # NEW
plugins/taskmaster/viewer/js/components/edit-mode.js                 # NEW
plugins/taskmaster/viewer/js/components/widgets/*.js                 # 13 NEW
plugins/taskmaster/viewer/js/components/auto-mode-strip.js           # +createAutoModeStrip factory
plugins/taskmaster/viewer/js/components/card.js                      # +renderMinimalCard/renderFullCard shims
plugins/taskmaster/viewer/css/screens/dashboard.css                  # NEW
plugins/taskmaster/viewer/tests/dashboard.spec.js                    # NEW (5 tests)
plugins/taskmaster/viewer/tests/unit/dashboard-grid.test.js          # NEW (6 tests)
docs/superpowers/plans/PROGRESS.md                                   # Plan 4 ticks
docs/superpowers/plans/2026-04-26-viewer-redesign-plan-4-dashboard.md # all 36 ticks
```

---

## Repo / state at handoff

- **Branch:** `feature/taskmaster-v3`. Local only — **never pushed**. ~260 commits ahead of `master`.
- **Tags (local only):** `viewer-redesign-plan-3-complete` (created this session at `eb8bae0`). No Plan 4 tag yet — see "Open question" below.
- **Untracked (expected, do not commit):**
  ```
  .fixture-kanban/                                       # locally-enriched test fixture
  plugins/taskmaster/.taskmaster/                        # local taskmaster state
  plugins/taskmaster/viewer/test-results/                # Playwright artifacts
  plugins/taskmaster/viewer/tests/test-results/
  plugins/taskmaster/viewer/tests/package-lock.json
  ```
- **Background dev server** may still be running on `:8765` from this session (orphaned `python` process). Not blocking — Plan 5a's first server work is in `taskmaster_v3.py`, server-side tests run via pytest with a `running_server` fixture so the orphaned one only matters if you go to run Playwright. Kill via Task Manager or `netstat -ano | findstr :8765` if needed.

---

## Plan 5 shape — what you're walking into

Plan 5 is split into two files:

| Plan | Tasks | Scope |
|---|---|---|
| **5a — Sessions / Recap** | 33 | Server entities (`recap_*`, `list_sessions`, `snapshot_diff`); 4 shared components (`right-rail`, `timeline`, `recap-receipts-grid`, `diff-row`); 2 screens (`sessions`, `recap`). |
| **5b — Lessons / Issues** | 32 | Server (`lesson_reinforce`, `compute_lesson_shelf`, `compute_issue_aging`, extended list endpoints); shared components (`severity-glyph`, `aging-bar`, `sparkline`, `dot-meter`, `anchor-pills`); 2 screens (`lessons`, `issues`). |

**Run order:** 5a first. 5b's screens import the `RightRail` / `Timeline` / `RecapReceiptsGrid` / `DiffRow` components that 5a introduces. If you flip the order you'll be re-implementing those.

### 5a milestone breakdown

- **M1 (T1–T9)** — server entities in `taskmaster_v3.py`: `RECAP_SCHEMA_VERSION`, recap path/format helpers, `save_recap` / `load_recap` / `list_recaps`, `save_session_snapshot`, `snapshot_diff`, `list_sessions` (synthesised from `PROGRESS.md` + handovers), `get_session_detail`.
- **M2 (T10–T14)** — MCP tools + HTTP routes: `recap_get/set/list`, `snapshot_diff`; `GET /api/sessions[/<sid>]`, `GET|PUT /api/recap/<sid>`, `GET /api/snapshots/diff`. New pytest files: `test_v3_recap.py`, `test_v3_snapshot_diff.py`, `test_v3_sessions.py`, `test_server_sessions_recap.py`.
- **M3 (T15–T22)** — shared client components + `node --test` unit tests for the cluster algorithm and the snapshot-diff mirror, plus `api.js` extensions.
- **M4 (T23–T27)** — `sessions.js` + CSS + Playwright smoke. Wires `viewer:prefs-patch` event into store/api (a small infra change).
- **M5 (T28–T33)** — `recap.js` + CSS + Playwright smoke; receipt filter chips; hero stat-strip exclusion of handovers; right-rail close-on-Escape / outside-click.

### 5b milestone breakdown

- **M1–M2 (T1–T8)** — server: `reinforce_events` schema extension, `lesson_reinforce`, extended list endpoints with `compute_lesson_shelf` and `compute_issue_aging`.
- **M3 (T9–T17)** — shared components (`severity-glyph` SVG hex, `aging-bar`, `sparkline`, `dot-meter`, `anchor-pills`) + `node --test` unit tests + `api.js` extensions.
- **M4 (T18–T21)** — `lessons.js` screen + `lesson-card`.
- **M5 (T22–T25)** — `issues.js` screen + `issue-card`.
- **M6 (T26–T32)** — integration smoke + spec coverage walk.

---

## Carried-forward gotchas (still load-bearing)

These bit Plan 3 *and* Plan 4. Plan 5 will most likely hit them too:

1. **`prefs` injected into screen `mount(...)` is the patch helper, not data.** Use `store.getPrefs()` for any read side. Both Plan 3 (`task-detail.js`) and Plan 4 (`dashboard.js`) shipped this bug in their first cut. Whenever a Plan 5 screen reads a persisted setting (recap picker selection, lessons threshold overrides, issues aging overrides, sessions filters), do the read from `store.getPrefs()` and mirror back onto `prefs` for in-session writes.
2. **Playwright tests must reset prefs in `beforeEach`** — `viewer.json` persists across runs, so a test that mutates prefs leaks into the next test. Pattern:
   ```js
   test.beforeEach(async ({ request }) => {
     await request.put(`${BASE}/api/viewer/prefs`, { data: { /* the slice this spec touches */ } });
   });
   ```
3. **`mountRightRail` (and any deferred-render component) runs inside `queueMicrotask`.** Playwright counts/clicks must `await expect(...).toBeVisible()` first.
4. **`_load_task_full` and friends read `Path(...)` relative to cwd, ignoring `TASKMASTER_ROOT`.** Always `cd` into `.fixture-kanban/` before booting the server. Snippet at end of this doc.
5. **`docs/superpowers/` is gitignored** — `git add -f` REQUIRED for plan files and `PROGRESS.md` ticks.
6. **`node --test` glob workaround on Node 22:** `node --test "plugins/taskmaster/viewer/tests/unit/*.test.js"`. Quote the glob.
7. **Playwright `webServer` is not configured** — bring the dev server up yourself before `npx playwright test`. `Error: locator: Test timeout` usually means "server isn't running on 8765". Confirm with `curl http://127.0.0.1:8765/api/identity`.
8. **Run Playwright from `plugins/taskmaster/viewer/tests/`** (where `node_modules` lives), not from `viewer/`.
9. **Plan-2-vs-Plan-N naming gap may strike again.** When a Plan 5 component imports a name from `card.js` / `right-rail.js` / etc, sanity-check the export exists *before* dispatching widget agents. The `createAutoModeStrip` and `renderMinimalCard` cases this session both manifested as silent module-load failures with no obvious test signal.

---

## How to bring up the dev server (carries forward)

```bash
cd .worktrees/taskmaster-v3/.fixture-kanban
python -u -c "
import sys, threading, time
sys.path.insert(0, r'C:/Users/gruku/Files/Claude/claude-tools/.worktrees/taskmaster-v3/plugins/taskmaster')
from backlog_server import _make_server
s, p = _make_server(host='127.0.0.1', port=8765)
print(f'SERVER_UP http://127.0.0.1:{p}/v3#/dashboard', flush=True)
t = threading.Thread(target=s.serve_forever, daemon=True); t.start()
while True: time.sleep(3600)
"
```

For Plan 5a Playwright tests you'll likely want both `/v3#/sessions` and `/v3#/recap` routes — Plan 1 already stubs both.

---

## Open questions for the next session

1. **Tag Plan 4 separately, or roll it into a Plan 5a checkpoint?** The Plan 3 tag exists as a recovery point; Plan 4's body of work is comparable. If you want symmetry, ask the user to OK `viewer-redesign-plan-4-complete` before starting 5a:
   ```bash
   git -C .worktrees/taskmaster-v3 tag -a viewer-redesign-plan-4-complete \
     -m "Plan 4 (Dashboard) complete: bento + 13 widgets + edit mode + tests"
   ```
2. **Open follow-ups parked** (still not addressed):
   - `marked` CDN integrity blocked — vendor it locally as `viewer/vendor/marked.min.js`.
   - `renderRaw` is JSON, not YAML (Plan 3 carry-over).
   - Graph control stubs (`depth` / `show-all`) are non-functional.
   - Plan 2 T2.29-T2.33 Playwright still skipped per user.
   - Phase stepper past-chip carousel scroll mirror (carryover).
   - Density toggle icons as inline SVG (carryover).
   - **NEW:** T4.34 spec deviation — plan called for a `--shell-zoom` CSS variable in `tokens.css`, but earlier tasks baked the 1.5× factor into literal values. Sub-agent flagged, not blocking, but worth normalising before Plan 5 widgets pick the same shortcut.
3. **`.fixture-kanban/` still untracked** and now relied on by *both* Plan 3 (`v3-009` enriched task) *and* Plan 4 (the seeded `viewer.json` for the dashboard layout reset). If you nuke the worktree you'll need to recreate.

---

## Files of interest

| Purpose | Path |
|---|---|
| **Plan 4 (Dashboard) — done** | `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-4-dashboard.md` |
| **Plan 5a (Sessions/Recap) — next** | `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-5a-sessions-recap.md` |
| **Plan 5b (Lessons/Issues) — after 5a** | `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-5b-lessons-issues.md` |
| Progress index | `docs/superpowers/plans/PROGRESS.md` |
| **This handoff** | `docs/superpowers/plans/2026-04-30-viewer-redesign-plan4-complete-resume-plan5.md` |
| Previous handoff (Plan 3 → Plan 4) | `docs/superpowers/plans/2026-04-29-viewer-redesign-plan3-complete-resume-plan4.md` |
| Dashboard orchestrator | `plugins/taskmaster/viewer/js/screens/dashboard.js` |
| Layout engine (pure data) | `plugins/taskmaster/viewer/js/components/dashboard-grid.js` |
| Widget catalog (registry) | `plugins/taskmaster/viewer/js/components/widget-catalog.js` |
| Widget frame chrome | `plugins/taskmaster/viewer/js/components/widget-frame.js` |
| Edit mode + picker + drop target | `plugins/taskmaster/viewer/js/components/edit-mode.js` |
| 13 widgets | `plugins/taskmaster/viewer/js/components/widgets/*.js` |
| Auto-mode-strip (now exports `createAutoModeStrip`) | `plugins/taskmaster/viewer/js/components/auto-mode-strip.js` |
| Card with shims | `plugins/taskmaster/viewer/js/components/card.js` |
| Server route added | `plugins/taskmaster/backlog_server.py` (+ `_compute_recent_events`) |
| Playwright dashboard suite | `plugins/taskmaster/viewer/tests/dashboard.spec.js` |
| Local fixture (still untracked) | `.fixture-kanban/backlog.yaml` |

---

## Session-start checklist (next session)

1. Confirm branch + worktree:
   ```bash
   git -C C:\Users\gruku\Files\Claude\claude-tools\.worktrees\taskmaster-v3 branch --show-current
   ```
   Expect `feature/taskmaster-v3`.

2. `git status` — clean except known untracked: `.fixture-kanban/`, `plugins/taskmaster/.taskmaster/`, `viewer/test-results/`, `viewer/tests/test-results/`, `viewer/tests/package-lock.json`.

3. Sanity (all should be green):
   ```bash
   python -m pytest plugins/taskmaster/tests/ -q
   cd plugins/taskmaster/viewer && npm run test:unit
   ```
   Expected: 220 server PASS, 36 unit PASS.

4. Optional: Playwright sweep across all suites that exist so far (kanban, task-detail, dashboard) before adding more — confirms nothing regressed since the last green state.

5. Decide with the user:
   - Tag `viewer-redesign-plan-4-complete` first? (recommended — small, recoverable, mirrors Plan 3 hygiene)
   - Then dispatch Plan 5a M1 (T1–T9, server entities) to a `sonnet` sub-agent via `superpowers:subagent-driven-development`. M1 is mostly mechanical TDD against a clear schema — Sonnet's wheelhouse.
   - Hold M3 component work for Opus only if a sub-agent flags ambiguity in the parallel-block clustering algorithm (T16/T17). Otherwise Sonnet.
