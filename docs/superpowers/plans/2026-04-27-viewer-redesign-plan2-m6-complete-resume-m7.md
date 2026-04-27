# Plan 2 Handoff — M3 + M4 + M5 + M6 visual locked, resume at T2.25 (round-trip + Playwright)

**Date:** 2026-04-27
**Branch:** `feature/taskmaster-v3` (worktree at `.worktrees/taskmaster-v3` — NOT master)
**Tip:** `5e20a03`
**Plan 2 progress:** 25/35 tasks (~71%). M1+M2+M3+M4+M5 closed; M6 *partially* closed through T2.24 (manual smoke + design alignment). Remaining: T2.25–T2.33.
**Tests at handoff:** pytest **212/212** · node `--test` **25/25** · Playwright not run since M2 (~handoff window).

---

## Resume prompt for the next session

> "Resuming the Taskmaster viewer redesign. Plan 2 is at 25/35 — M3-M5 complete plus T2.23 + T2.24 (manual smoke + design alignment); user signed off on the kanban visual. Read `docs/superpowers/plans/2026-04-27-viewer-redesign-plan2-m6-complete-resume-m7.md` for current state, then read T2.25–T2.28 in `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-2-kanban-cards.md` (lines ~2768–2870) before dispatching anything. Confirm in `PROGRESS.md` that the next unchecked task is T2.25. Branch: `feature/taskmaster-v3` in worktree `.worktrees/taskmaster-v3`. Use `superpowers:subagent-driven-development`. T2.25–T2.28 are MANUAL smoke checkpoints (no commits) — boot the server with the `.fixture-kanban/backlog.yaml`, walk through each step, then advance to T2.29 (Playwright config). Pause for human at the T2.28 boundary before T2.29 to discuss whether to write the Playwright fixture inline or split it across a fresh session."

---

## Session changelog

This session advanced Plan 2 from 8/33 → 25/35. The total task count grew by 2 because T2.24α and T2.24β were inserted as new sub-tasks of the M6 manual-smoke checkpoint when design feedback surfaced.

### Per-milestone summary

| Milestone | Tasks | Status |
|---|---|---|
| M3 — Card Component (T2.9–T2.13) | 5 | ✅ closed (visual sanity verified) |
| M4 — Auto-mode strip (T2.14–T2.16) | 3 | ✅ closed |
| M5 — Kanban Controls (T2.17–T2.22) | 6 | ✅ closed |
| M6 — Kanban Screen (T2.23–T2.28) | 6 + 2 inserted | T2.23 ✅, T2.24 ✅ (with α + β alignment work), T2.25–T2.28 next |
| M7 — Tests + Polish (T2.29–T2.33) | 5 | not started |

### Notable inserted tasks

**T2.24α — Zoom removal + 1.5× source CSS rescale.** The viewer originally applied CSS `zoom: var(--shell-zoom: 1.5)` per spec §3.4 to bake in 150%. User decided this hack should go. We removed the CSS zoom and rescaled every spatial token + literal across `tokens.css`, `shell.css`, `components.css`, `_placeholders.css`, `kanban.css` by × 1.5. Visual output unchanged. Spec §3.4 effectively rewritten ("1.5× baked into source CSS values, not via CSS zoom").

**T2.24β — Signal alignment + collapsible columns + prefs default.** Once zoom was gone, we applied:
- Signal-reference palette alignment: `--bg-canvas`, `--bg-board-col`, `--bg-card`, `--ink-2`, `--border` re-toned. Added `--bg-card-hover`, `--ink-4`.
- Column-header weight bumped to 18px / 600 with subtle dot halo (`color-mix(in oklch ...)`).
- Board viewport-fill (`.main`, `.kanban-page`, `.kanban-board`, `.kanban-col` flex chain).
- Drop redundant inline kanban title (later restored, then re-routed into the topbar — see iteration log below).
- Collapsible columns with prefs persistence (`prefs.kanban.collapsed_columns`).
- `VIEWER_PREFS_DEFAULTS["zoom"]: 1.5 → 1.0`. Updated 2 stale snapshot tests.

### Iteration log (post-T2.24β smoke fixes)

Three rounds of user-driven visual refinement, each followed a manual smoke:

**Round 1 — smoke fixes (commits `0b9d988…1f81e4b`):**
1. Title moved inline into kanban-head (topbar h1 hidden while on kanban) — solved A1.
2. `body { overflow: hidden }`, `.shell { height: 100vh; overflow: hidden }`, `.sidebar { overflow-y: auto }` — page was scrolling because `.shell` was `min-height: 100vh`.
3. Removed `.kanban-board::before` dot-grid + radial-mask pseudo-element (visual artifact).
4. Switched `.kanban-board-grid` from CSS grid to flex so collapsed columns redistribute.

**Round 2 — collapse-redistribution + v1 column pattern (commits `08e9bc5..9c6dd31`):**
5. CSS specificity bug fixed: the rule `.kanban-board-grid.status > .kanban-col` (specificity 0,2,1) was beating `.kanban-col.collapsed` (0,2,0) and overriding `flex` and `min-width`. Refactored to base `.kanban-col { flex: 1 1 0; min-width: 0; }` and `.kanban-col.collapsed { flex: 0 0 66px }` — clean specificity beat (0,2,0 > 0,1,0).
6. Adopted v1's `.column / .column-body` pattern: each column has internal `.kanban-col-body { flex: 1; overflow-y: auto; }` for per-column scroll instead of board-level scroll. Kanban.js paint() now wraps cards in `.kanban-col-body` div.
7. Collapse width 66px (= v1's 44px × 1.5, matching the rescale).

**Round 3 — column stretch + neutral darker board (commits `2619ff7..d6dd0fc`):**
8. `.kanban-board-grid` got `flex: 1 1 auto; min-height: 0` and `.kanban-board { display: flex; flex-direction: column }` so columns stretch to bottom of available height.
9. Neutralized the kanban-board: `--kanban-board-bg-grad` → flat `--kanban-board-bg: #101113`; `--kanban-board-border` → `var(--border)`; column border `rgba(74,158,255,0.06)` → `var(--border)`; dropped the blue inset box-shadow.

**Round 4 — topbar refactor (commits `e9d122a..09fa86a`):**
10. `index.html` got `<div id="topbar-actions">` slot beside the page-title `<h1>`.
11. `.topbar` is now `flex-wrap` with `min-height: 48px` and a flexible actions slot. Acts as the unified screen header.
12. Kanban no longer renders its own `.kanban-head` row inside the page — its controls (subcount + search + priority chips + density + group + sort + +Task) inject into `#topbar-actions` on mount and clear on unmount.
13. Removed the inline `.title` (topbar h1 carries it). Removed the topbar h1 hide/restore from kanban.js. Renamed `.subcount` to `.kanban-head-subcount` to drop the `.kanban-head` selector dependency. Deleted `.kanban-head { ... }` CSS rule entirely.

**Round 5 — unified filter bar (commits `527fd66..70aaf58`):**
14. Phase stepper + epic chips merged into ONE container `.kanban-filterbar` (single panel, single border, single padding). Inner panel chrome stripped from `.kanban-phase-stepper` and `.kanban-epic-row` when nested under `.kanban-filterbar`.
15. Stacked layout: phases (top row) over epics (bottom row), separated by hairline `border-top` on the second row. Removed the vertical divider element.

**Round 6 — final surface lift (commit `5e20a03`):**
16. `--bg-board-col: #131316 → #1c1d22`. Column now sits subtly above the page (`#181a20`), card (`#26262b`) clearly above column. Hierarchy reads page < column < card.

### Bounce-back / failure log

- **Zero spec-review bounce-backs across the entire 35-task block.** All TDD/spec-prescribed code landed verbatim on first review.
- **Six visual smoke rounds**, each opened by user feedback. The iterations exposed real bugs (CSS specificity beat; missing flex chain; double-encoded "Kanban" title; blue tint trapped in 5+ places) that no automated review would have caught.

---

## Plan 2 state — what's left

| Task | Type | Effort | Notes |
|---|---|---|---|
| T2.25 — density toggle round-trip via Playwright | manual confirm only (no commit) | 2 min | Toggle minimal/full in browser, reload, confirm persists. Inspect Network for `PUT /api/viewer/prefs`. |
| T2.26 — group-by phase + epic visual sanity | manual confirm | 2 min | Switch group dropdown to phase, then to epic. Confirm columns + status pill rendering on cards. |
| T2.27 — prefs reset behavior | manual confirm | 1 min | Apply filters, hit "clear all". Confirm reset cascade works (priorities, epics, phase, search, group, sort, AND collapsed columns). |
| T2.28 — click-to-copy IDs and branches | manual confirm | 1 min | Click a card's ID → "copied" green flash. Click branch → same. Confirm clipboard populated. |
| T2.29 — Playwright config: kanban-aware fixture | implementation | ~1 h | Extend the existing fixture to seed a backlog with phases + epics + tasks. |
| T2.30 — Playwright smoke for kanban | TDD-style | ~1.5 h | Assert column count, card count, density toggle, group-by switching, etc. |
| T2.31 — Auto-mode strip Playwright smoke | TDD-style | ~1.5 h | Inject `.taskmaster/auto/state.json` via fixture, assert strip + per-card live block render. **This is the one that exercises the deferred T2.24 step 4 — auto-state visual sanity.** |
| T2.32 — Run all server + unit + smoke tests in sequence | run + record | 5 min | One-shot regression check. |
| T2.33 — Final integration smoke + plan-level verification commit | meta | 5 min | Final tick + spec-coverage audit + plan-close commit. |

**T2.24 step 4 carried forward:** the original T2.24 smoke step 4 was "drop a state.json and confirm strip + live block render" — not visually verified this session because design feedback took over. Will be covered by T2.31 Playwright. Logged here so it isn't forgotten.

---

## Hygiene-sweep candidates (carry into Plan-2 wrap)

Add to the Plan-2 hygiene sweep already started in M1+M2:

7. **`.kanban-search` width on narrow viewports.** Now that controls flex-wrap inside the topbar, the search input can collapse to its `min-width: 200px`. Acceptable but might want explicit responsive treatment.
8. **`.topbar-actions` empty-state hide.** Has `:empty { display: none }` rule but child rendering can leave whitespace text nodes — flag if any visual gap appears on non-kanban screens.
9. **Auto-mode strip auto-cleanup contract.** Strip's 1Hz `setInterval` is created in `renderAutoModeStrip` and cleared via `destroyAutoModeStrip(strip)`. Kanban screen DOES call this on cleanup (added in T2.23). Confirm by Playwright test in T2.31 that screen-switch unmounts the interval (no zombie ticks).
10. **`.kanban-col.collapsed` cursor-pointer covers the whole column** — including the chevron toggle. Click is captured by toggle's stopPropagation, but on the column body (which is hidden) there's no other action. Could change `cursor: pointer` to `cursor: default` on the body to avoid misleading affordance. Minor.
11. **`#101113` board background literal in kanban.css `:root`.** Should it be a global token? Currently lives only in kanban scope. Probably fine — board surface is genuinely kanban-specific.
12. **Specificity tooling:** the bug that made `.kanban-col.collapsed` lose to `.kanban-board-grid > .kanban-col` consumed a smoke round. Worth a one-off lint pass to flag any other `.X .Y` rules that beat `.X.Z` rules in the codebase.
13. **Topbar h1 default text "Loading…":** while the router resolves the screen, the h1 briefly shows "Loading…". Replace with empty string or current screen name from URL hash if present.
14. **`prefs.kanban.collapsed_columns` not migrated for users with old prefs.json.** No migration code; new key is added by deep-merge in `load_viewer_prefs`. Verify deep-merge handles list defaults correctly (it should — VIEWER_PREFS_DEFAULTS deep-merge tested in pytest).

---

## Known repo gotchas (carry-forward)

- **`docs/superpowers/` is gitignored.** `git add -f` REQUIRED for plan-file and PROGRESS.md ticks. (Carried over from prior handoff.)
- **The worktree is the only place this work happens.** `C:\Users\gruku\Files\Claude\claude-tools\.worktrees\taskmaster-v3`.
- **Server boot for human smoke (with fixture):**
  ```bash
  cd .fixture-kanban   # contains backlog.yaml seeded with the canonical 5-task fixture
  python -u -c "import sys, threading, time; sys.path.insert(0, r'<absolute path to plugins/taskmaster>'); from backlog_server import _make_server; s, p = _make_server(host='127.0.0.1', port=0); print(f'http://127.0.0.1:{p}/v3#/kanban', flush=True); t = threading.Thread(target=s.serve_forever, daemon=True); t.start(); import time; \nwhile True: time.sleep(3600)"
  ```
  (PYTHONPATH does NOT pass through to the python -c subprocess; insert the path explicitly via `sys.path.insert`.)
- **node `--test` glob workaround on Node 22:** `node --test "plugins/taskmaster/viewer/tests/unit/*.test.js"` (must quote the glob — passing the directory hits a "Cannot find module" error on Node 22.x).
- **`viewer/tests/package.json` declares `"type": "module"`.** Future tests can use ESM imports.
- **The CSS `zoom` mechanism is gone.** All v3 viewer CSS values are now in source-pixel space, scaled 1.5× over the original Plan 1 design. This is invisible to most code but will surprise anyone diffing v1's px values against v3's.

---

## Files of interest

| Purpose | Path |
|---|---|
| Plan 2 (kanban + cards) | `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-2-kanban-cards.md` |
| Progress index | `docs/superpowers/plans/PROGRESS.md` |
| Design feedback capture (Signal alignment) | `docs/superpowers/plans/2026-04-27-plan2-design-feedback-signal-alignment.md` |
| Plan 2 mid-handoff (this session start) | `docs/superpowers/plans/2026-04-27-viewer-redesign-plan2-m2-complete-resume-m3.md` |
| **This handoff** | `docs/superpowers/plans/2026-04-27-viewer-redesign-plan2-m6-complete-resume-m7.md` |
| Kanban screen module | `plugins/taskmaster/viewer/js/screens/kanban.js` |
| Kanban CSS | `plugins/taskmaster/viewer/css/screens/kanban.css` |
| Tokens (post-rescale + Signal palette + neutral surfaces) | `plugins/taskmaster/viewer/css/tokens.css` |
| Shell (post-zoom-removal + topbar slot) | `plugins/taskmaster/viewer/css/shell.css` + `viewer/index.html` |
| Smoke fixture | `.fixture-kanban/backlog.yaml` (worktree-local, gitignored) |
| Prefs schema | `plugins/taskmaster/taskmaster_v3.py` `VIEWER_PREFS_DEFAULTS` |

---

## Session start checklist (next session)

1. Read this handoff end-to-end.
2. `git -C C:\Users\gruku\Files\Claude\claude-tools\.worktrees\taskmaster-v3 status` — should be clean (untracked `.fixture-kanban/`, `.taskmaster/`, `viewer/tests/test-results/` are pre-existing — ignore).
3. Tip should be `5e20a03` (or the new tick commit if you tick T2.24 first).
4. `python -m pytest plugins/taskmaster/tests/ -q` from worktree root — must show 212.
5. `node --test "plugins/taskmaster/viewer/tests/unit/*.test.js"` — must show 25.
6. `bash plugins/taskmaster/viewer/tests/run_smoke.sh` — must show 12/12.
7. Skim `2026-04-27-plan2-design-feedback-signal-alignment.md` for the visual decisions if you need to recall surface tokens / palette / column-collapse contract.
8. Read T2.25–T2.28 in the plan file (small, manual-smoke tasks).
9. Boot the server with the fixture, walk T2.25→T2.28 yourself or via claude-in-chrome, then tick.
10. Pause for human at T2.28 → T2.29 boundary if you want to confirm Playwright fixture scope before writing tests.

---

## Big picture — what's left after Plan 2

After Plan 2 closes (10 tasks remaining), Plan 3 (Task Detail, 46 tasks) is next. Architectural conventions defined in Plan 1 still apply.

Total backlog after this session: **236 / 273** still pending (Plan 2 has 10 left; Plans 3–6 = 210; original post-execution housekeeping items = 4; 14 hygiene candidates accumulated).
