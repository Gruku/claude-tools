# Viewer Redesign — Handoff after Plans 5a + 5b complete (70/70)

**Date:** 2026-04-30
**Branch:** `feature/taskmaster-v3` (worktree at `.worktrees/taskmaster-v3`, local-only — never pushed)
**Plan 5a status:** **38/38**
**Plan 5b status:** **32/32**
**Next:** Plan 6 (Auto-mode) — 58 tasks across 8 milestones. The last plan; no Plan 7 exists.

---

## Resume prompt

> "Resuming the viewer redesign at the start of Plan 6 (Auto-mode). Plans 5a (Sessions/Recap, 38/38) and 5b (Lessons/Issues, 32/32) are fully complete — all suites green: 268 server, 64 unit, 19+ Playwright (sessions, recap, lessons, issues). Read `docs/superpowers/plans/2026-04-30-viewer-redesign-plan5-complete-resume-plan6.md` for what landed and the gotchas, then start Plan 6 at T1 in `2026-04-26-viewer-redesign-plan-6-auto-mode.md`. Branch: `feature/taskmaster-v3` in worktree `.worktrees/taskmaster-v3`. Plan 6 is the largest plan yet (58 tasks, 8 milestones, ~4080 plan lines). Dispatch milestone-by-milestone via Sonnet sub-agents — that pattern carried Plans 5a and 5b cleanly."

---

## What landed this session

Two full plans end-to-end (~80 commits on top of the Plan 4 tag).

### Plan 5a — Sessions / Handovers + Recap (38/38)

| Milestone | Tasks | What |
|---|---|---|
| M1 | T1–T9 | Server entities in `taskmaster_v3.py`: `RECAP_SCHEMA_VERSION`, `HANDOVER_KIND_TO_VIEWER_KIND`, `recap_path`/`_format_recap_markdown`/`_parse_recap_markdown`, `save_recap`/`load_recap`/`list_recaps`, `save_session_snapshot`, `snapshot_diff`, `list_sessions` (synthesised from `PROGRESS.md` + handovers), `get_session_detail`. |
| M2 | T10–T14 | MCP tools + HTTP routes: `recap_get`/`set`/`list`, `snapshot_diff`; `GET /api/sessions[/<sid>]`, `GET|PUT /api/recap/<sid>`, `GET /api/snapshots/diff`. |
| M3 | T15–T22 | 4 shared client components: `diff-row.js`, `timeline.js` (with parallel-block clustering), `right-rail.js` (factory wrapper around existing `mountRightRail`), `recap-receipts-grid.js` + client-side `snapshot-diff.js` mirror + `node --test` units (parallel-block clustering, snapshot-diff mirror) + `api.js` extensions. Added `jsdom` dev dep. |
| M4 | T23–T27 | Sessions screen: `sessions.css`, `sessions.js` (needed prefs-from-store fix), Playwright smoke 3/3, `viewer:prefs-patch` event wired through `main.js` patcher and exposed `savePrefs` on `api.js`. |
| M5 | T28–T34 | Recap screen: `recap.css`, `recap.js` (picker + prev/next + hero + receipts + edit), Playwright smoke +5 (filter chips, stat-strip handover exclusion, Escape close, outside-click). Reads from `params.id`, no patcher fix needed. |
| M6 | T35–T38 | Spec §3.12 + §3.16 coverage walks, Sessions→Recap deep-link integration test, final empty handoff commit. |

**Bugs found & fixed during 5a:**
1. **T8 (`list_sessions`)** — plan's strict overlap check `s_start <= o_end and o_start <= s_end` failed for single-handover sessions close in time but not truly overlapping. Sub-agent expanded each session's end timestamp by `SESSION_GAP_MINUTES` so single-point sessions within the clustering gap detect each other as parallel.
2. **T11–T13 (HTTP routes)** — `_parse_iso8601` in `taskmaster_v3.py` failed when YAML auto-parsed ISO datetime strings as `datetime` objects. Added `isinstance(s, datetime)` guard.
3. **M4 `sessions.js`** — read `prefs?.screens?.sessions?.view` from the patcher (data is undefined). Predicted gotcha; fixed by reading `store.getPrefs()`, mirroring back. Same bug as Plan 3 `task-detail.js` (e74c521) and Plan 4 `dashboard.js` (4c92634).
4. **M5 fixture seed** — sessions list was empty until I added `.fixture-kanban/.taskmaster/handovers/2026-04-26-stitched-worktree-review-gate.md` to seed `SES-0001`.

### Plan 5b — Lessons / Issues (32/32)

| Milestone | Tasks | What |
|---|---|---|
| M1 | T1–T4 | Lesson schema extended with `reinforce_events: [{at, source ∈ {user|claude|skill}, note}]`. `lesson_reinforce()` helper, MCP tool, `POST /api/lessons/<id>/reinforce` endpoint. |
| M2 | T5–T8 | `compute_lesson_shelf` (core/active/retired by reinforcement count + recency), `compute_issue_aging` ({percent, tier ∈ Fresh/Aging/Stale}), `lesson_list_extended` + `GET /api/lessons`, `issue_list_extended` + `GET /api/issues?include_resolved=`. Also added cwd-relative wrappers `list_lesson_ids_cwd`/`list_issue_ids_cwd` since the plan referenced bare names that didn't exist in the codebase. |
| M3 | T9–T17 | 5 components (`severity-glyph` SVG hex defs, `aging-bar`, `sparkline`, `dot-meter`, `anchor-pills`) + 3 utility helpers (`computeShelfPlacement`, `computeBlocksCount`, `severityLabel`) + `api.js` extensions (`getLessons`, `reinforceLesson`, `getIssues`). |
| M4 | T18–T21 | Lessons screen with three shelves, `lesson-card` with all signals, Playwright 3/3. Needed prefs-from-store fix + `_reinforcedIds` set so the `is-fired` button class survives re-renders. Seeded 4 lesson fixtures in `.fixture-kanban/.taskmaster/lessons/`. |
| M5 | T22–T25 | Issues screen hybrid layout, `issue-card` bug-report flavor, Playwright 4/4 including repro expand. Same prefs-from-store fix. Seeded 3 issue fixtures (P0/P1/P2 + fixed). |
| M6 | T26–T32 | Spec §3.13 + §3.14 coverage assertions, cross-screen routing, threshold + aging override end-to-end, reinforce source enforcement (`source ∈ {user, claude, skill}`), final handoff commit. |

**Bug I had to fix mid-stream (commit `05bcc0f`):**
M2's plan code added `from taskmaster_v3 import (… load_viewer_prefs …)` *inside* `do_GET` at the new `/api/lessons` and `/api/issues` branches. Python sees that as a function-local binding, so `load_viewer_prefs` becomes local for the entire `do_GET` scope — and the earlier `/api/viewer/prefs` branch (line 4184), which used the module-level import, started raising `UnboundLocalError`. Killed 4 unrelated tests. Fixed by removing the redundant `load_viewer_prefs` from the local imports — it's already imported at module level (line 101). **Add this to the gotchas list — Plan 6 will keep adding routes inside `do_GET` and the same trap is one careful re-import away.**

---

## Repo / state at handoff

- **Branch:** `feature/taskmaster-v3`. Local only — **never pushed**. ~340 commits ahead of `master`.
- **Tags (local only):**
  ```
  viewer-redesign-plan-3-complete       (eb8bae0)
  viewer-redesign-plan-4-complete       (76f53e9)
  viewer-redesign-plan-5a-complete      (after Plan 5a M6)
  viewer-redesign-plan-5b-complete      (after Plan 5b M6) — current HEAD baseline
  ```
- **Untracked (expected, do not commit):**
  ```
  .fixture-kanban/                                        # locally-enriched test fixtures
  plugins/taskmaster/.taskmaster/
  plugins/taskmaster/viewer/test-results/
  plugins/taskmaster/viewer/tests/test-results/
  plugins/taskmaster/viewer/tests/package-lock.json
  ```
- **Background dev server** likely still running on `:8765` from this session. `curl http://127.0.0.1:8765/api/identity` to check; if it's responding from `.fixture-kanban/`, reuse it. If stale/wrong-tree: `netstat -ano | findstr :8765` then `taskkill /PID <pid> /F`.
- **Final test counts at handoff:**
  - Server pytest: **268/268**
  - Unit `node --test`: **64/64**
  - Playwright: **dashboard 5/5, sessions 3/3, recap 6/6, sessions↔recap integration 3/3, lessons 3/3, issues 4/4** (+ task-detail 10/10 and kanban suite from prior plans)

---

## Plan 6 shape — what you're walking into

`docs/superpowers/plans/2026-04-26-viewer-redesign-plan-6-auto-mode.md` — 4081 lines, 58 tasks, 8 milestones. The Auto-mode screen with the "quest spine" SVG, flight log, sessions strip, side panels, plus a real dashboard stepper widget replacing Plan 4's stub.

| M | Tasks | Scope |
|---|---|---|
| **M1 — Server Storage Refactor** | T1–T6 | Auto-session storage layout constants, `load_auto_session`/`save_auto_session`/`list_auto_sessions`, **one-time migration** of legacy `state.json` → `sessions/<sid>.json` wired into server startup, `append_auto_event`/`read_auto_events`, `read_hook_events` (read-only scrape). |
| **M2 — Server HTTP** | T7–T14 | `tests/test_server_auto_mode.py` skeleton, `GET /api/auto/sessions/<sid>`, `GET /api/auto/state` (Plan-2 compat shim returning most-recent session), `POST /api/auto/pause`+`/api/auto/stop`, `GET /api/auto/events?sid=&since=`, `GET /api/auto/budget/<sid>` + `compute_budget`, MCP tools (`auto_state_get`, `auto_pause`, `auto_stop`, `auto_history`, `auto_event_log`), `api.js` wrappers. |
| **M3 — Spine layout (pure)** | T15–T19 | `js/components/auto-spine-layout.js` — pure data: function signatures, locked node radii (active=18, others=10), connector geometry, satellite bezier control points, edge case for paused/stopped sessions. |
| **M4 — Quest Spine SVG renderer** | T20–T28 | `quest-spine.js` SVG renderer, `auto-mode.css` deep-recess frame, mount inside auto-mode screen, Spine\|Log toggle wired to `prefs.screens.auto_mode.view`, pause/stop buttons, first-visit helper note (persisted dismissal), title + worktree, empty state, sidebar live-dot via `store.autoState` setter. |
| **M5 — Flight Log** | T29–T33 | Flight-log component + styles, wire into Log view branch, 3-second polling cadence, Playwright Spine\|Log toggle. |
| **M6 — Sessions Strip + Side Panels** | T34–T43 | Sessions strip (multiple parallel runs), `store.setActiveAutoSession`/`getActiveAutoSession`, budget meter, left+right side-panels, hook_counts in session detail, Playwright sessions strip + pause button. |
| **M7 — Dashboard Stepper Widget** | T44–T51 | **Replaces Plan 4's stub `auto-mode-stepper.js` with the real widget.** Stepper styles (circles, labels, footer), unit test for stepper connector geometry, widget catalog registration verification, dashboard widget click navigates to `#/auto`, hides/shows calm placeholder when no session, "+1 more" pill for multiple sessions. |
| **M8 — Integration Smoke** | T52–T58 | Sidebar live-dot Playwright, helper-note dismissal, spine node count assertion, stop-confirm flow, full auto-mode green-bar, plan handoff doc, final visual review checklist. |

### Order to dispatch

Strictly sequential — later milestones import names introduced earlier. M7 (stepper widget) explicitly *replaces* the Plan 4 stub, so M1–M6 must land first.

### Recommended models

- **M1, M2, M3, M5, M6, M8** → `sonnet` (mechanical TDD against clear spec, what 5a/5b ran on cleanly).
- **M4 (Quest Spine SVG renderer)** → start with `sonnet` but **be ready to escalate to `opus`** if the SVG geometry / coordinate-system work surfaces ambiguity. T15–T19 already lock the geometry as pure-data, so M4 should mostly be wiring; if Sonnet flounders, escalate.
- **M7 (Stepper widget)** → `sonnet`. Mostly pattern-matching the Plan 4 widget shape with real data.

---

## Carried-forward gotchas (still load-bearing — Plan 6 will hit them)

These bit Plans 3, 4, 5a, *and* 5b. Plan 6 will likely hit them too:

1. **`prefs` injected into screen `mount(...)` is the patch helper, not data.** Use `store.getPrefs()` to read. Plans 3, 4, 5a, 5b each shipped this bug in their first cut. Auto-mode reads `prefs.screens.auto_mode.view`, `prefs.screens.auto_mode.first_visit_dismissed`, etc — guaranteed to bite at T23 / T25 unless the agent is briefed.

2. **Playwright tests must reset prefs in `beforeEach`** — `viewer.json` persists across runs:
   ```js
   test.beforeEach(async ({ request }) => {
     await request.put(`${BASE}/api/viewer/prefs`, { data: { /* the slice this spec touches */ } });
   });
   ```

3. **`mountRightRail` and any `queueMicrotask`-deferred render** — Playwright counts/clicks must `await expect(...).toBeVisible()` first. Auto-mode side panels likely use the same pattern.

4. **Re-render wipes transient UI state.** Plan 5b lessons hit it (`is-fired` class). Auto-mode flight-log may hit it too if it re-renders during polling — persist scroll position / expanded rows on the screen module if needed.

5. **`_load_task_full` and friends read `Path(...)` relative to cwd, ignoring `TASKMASTER_ROOT`.** Always `cd` into `.fixture-kanban/` before booting the server.

6. **`docs/superpowers/` is gitignored** — `git add -f` REQUIRED for plan files and `PROGRESS.md` ticks.

7. **`node --test` glob workaround on Node 22:** `node --test "plugins/taskmaster/viewer/tests/unit/*.test.js"` — quote the glob. `npm run test:unit` already does this; prefer it.

8. **Run Playwright from `plugins/taskmaster/viewer/tests/`** (where `node_modules` lives), not from `viewer/`.

9. **Playwright `webServer` is not configured** — bring the dev server up yourself before `npx playwright test`. `Error: locator: Test timeout` usually means the server isn't running. `curl http://127.0.0.1:8765/api/identity` to verify.

10. **Plan-2-vs-Plan-N export-name gap.** When a Plan 6 component imports a name from an existing file, sanity-check the export FIRST. Module-load failures are silent and torch all Playwright tests in one go. Plan 4 (`createAutoModeStrip`, `renderMinimalCard`) and Plan 5 (`prefs.getPrefs()`) each lost time to this.

11. **NEW from Plan 5b M2 — local-import-shadow trap.** When adding a route in `_BacklogHandler.do_GET`, do **not** locally re-import a name that's already imported at module level (especially `load_viewer_prefs`). Python treats the name as function-local for the entire `do_GET` scope, breaking earlier branches that used the module-level binding with `UnboundLocalError`. If you need a new symbol, import only the new symbol locally; leave existing module-level imports alone.

12. **NEW — fixture seeding.** Plan 5a needed `.fixture-kanban/.taskmaster/handovers/SES-0001.md`; Plan 5b needed `.taskmaster/lessons/L-{001..004}.md` and `.taskmaster/issues/ISS-{001..003}.md`. Plan 6 will probably need at least one running auto-session fixture (`.taskmaster/auto/sessions/<sid>.json`) and a hook-events log to drive Playwright. Document any fixture you add in the milestone report.

---

## How to bring up the dev server (carries forward)

```bash
cd .worktrees/taskmaster-v3/.fixture-kanban
python -u -c "
import sys, threading, time
sys.path.insert(0, r'C:/Users/gruku/Files/Claude/claude-tools/.worktrees/taskmaster-v3/plugins/taskmaster')
from backlog_server import _make_server
s, p = _make_server(host='127.0.0.1', port=8765)
print(f'SERVER_UP http://127.0.0.1:{p}/v3#/auto', flush=True)
t = threading.Thread(target=s.serve_forever, daemon=True); t.start()
while True: time.sleep(3600)
"
```

Cwd MUST be `.fixture-kanban/`. The server may already be running from this session — check first.

---

## Open follow-ups parked (not requested, not blocking)

1. **`marked` CDN integrity blocked** — vendor it locally as `viewer/vendor/marked.min.js`. Symptom: `console` warns of SRI mismatch; Playwright `pageerror` listeners filter it out, but it's noise.
2. **`renderRaw` is JSON, not YAML** (Plan 3 carry-over).
3. **Graph control stubs** (`depth` / `show-all`) are non-functional `() => {}` from Plan 3.
4. **Plan 2 T2.29-T2.33 Playwright** still skipped per user.
5. **T4.34 `--shell-zoom` CSS variable** — Plan 4 baked the 1.5× factor into literal values instead. Worth normalising before Plan 6 widgets pick the same shortcut.
6. **Phase stepper past-chip carousel scroll mirror** (carryover).
7. **Density toggle icons as inline SVG** (carryover).
8. **`.fixture-kanban/` still untracked** and now relied on by Plans 3, 4, 5a, 5b. If you nuke the worktree you'll need to recreate. Consider a one-time commit of the fixture content under a separate `--force` ignore-busting commit if this becomes painful.

---

## Files of interest

| Purpose | Path |
|---|---|
| **Plan 5a — done** | `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-5a-sessions-recap.md` |
| **Plan 5b — done** | `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-5b-lessons-issues.md` |
| **Plan 6 (Auto-mode) — next** | `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-6-auto-mode.md` |
| Progress index | `docs/superpowers/plans/PROGRESS.md` |
| **This handoff** | `docs/superpowers/plans/2026-04-30-viewer-redesign-plan5-complete-resume-plan6.md` |
| Previous handoff | `docs/superpowers/plans/2026-04-30-viewer-redesign-plan4-complete-resume-plan5.md` |
| Sessions screen | `plugins/taskmaster/viewer/js/screens/sessions.js` |
| Recap screen | `plugins/taskmaster/viewer/js/screens/recap.js` |
| Lessons screen | `plugins/taskmaster/viewer/js/screens/lessons.js` |
| Issues screen | `plugins/taskmaster/viewer/js/screens/issues.js` |
| Shared: right-rail (factory `RightRail` + legacy `mountRightRail`) | `plugins/taskmaster/viewer/js/components/right-rail.js` |
| Shared: timeline (parallel-block clustering) | `plugins/taskmaster/viewer/js/components/timeline.js` |
| Shared: recap-receipts-grid | `plugins/taskmaster/viewer/js/components/recap-receipts-grid.js` |
| Shared: diff-row | `plugins/taskmaster/viewer/js/components/diff-row.js` |
| Shared: severity-glyph (SVG hex defs) | `plugins/taskmaster/viewer/js/components/severity-glyph.js` |
| Shared: aging-bar | `plugins/taskmaster/viewer/js/components/aging-bar.js` |
| Shared: sparkline | `plugins/taskmaster/viewer/js/components/sparkline.js` |
| Shared: dot-meter | `plugins/taskmaster/viewer/js/components/dot-meter.js` |
| Shared: anchor-pills | `plugins/taskmaster/viewer/js/components/anchor-pills.js` |
| Util: lesson-shelf / issue-blocks / severity-label | `plugins/taskmaster/viewer/js/util/*.js` |
| Server: recap + sessions + snapshot diff + lesson reinforce + extended lists | `plugins/taskmaster/taskmaster_v3.py`, `plugins/taskmaster/backlog_server.py` |
| **Plan 4 stub auto-mode-stepper (M7 replaces this)** | `plugins/taskmaster/viewer/js/components/widgets/auto-mode-stepper.js` |
| **Existing auto-mode strip (compatible with Plan 6 M2 shim)** | `plugins/taskmaster/viewer/js/components/auto-mode-strip.js` |
| Local fixtures (untracked) | `.fixture-kanban/.taskmaster/{handovers,lessons,issues}/...` |

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
   Expected: **268 server PASS, 64 unit PASS**.

4. Optional Playwright sweep across all suites to confirm no regression since the `viewer-redesign-plan-5b-complete` tag.

5. Decide with the user whether to:
   - Just dive into Plan 6 M1 immediately, or
   - First do a manual browser walkthrough of the four new screens (sessions, recap, lessons, issues) — they all just landed without browser eyeballs.

6. When ready: dispatch Plan 6 M1 (T1–T6, server storage refactor) to a `sonnet` sub-agent via `superpowers:subagent-driven-development`. M1 is mechanical TDD with one risky bit (T3 migration of legacy `state.json`) — brief the agent to dry-run-check the migration is idempotent before writing files.

7. After M1: continue milestone-by-milestone. Allow ~7–8 sub-agent dispatches for Plan 6 (one per milestone, M4 may want to split if Sonnet struggles with the SVG geometry).
