# Plan 2 Handoff — kanban polish + sidebar collapse landed; phase stepper deferred; resume at T2.29 (M7)

**Date:** 2026-04-28
**Branch:** `feature/taskmaster-v3` (worktree at `.worktrees/taskmaster-v3`)
**Tip:** `c0e31f2`
**Plan 2 progress:** 29/35 (T2.25–T2.28 ticked previous session; M7 not started). This session was an *enhancement* detour — none of it is on Plan 2 itself.
**Tests at handoff:** pytest **212/212** · node `--test` not re-run · Playwright not run.

---

## Resume prompt for the next session

> "Resuming Plan 2. M3-M6 closed. The previous session did an unscheduled UX pass — sidebar collapse toggle, kanban column-collapse animation, card polish, topbar refactor, filter-bar restructure, phase-stepper utility buttons + connector arrows + a deep brainstorm exploration of a redesigned phase stepper (V1-V12C) that has NOT been ported into the live kanban. Read `docs/superpowers/plans/2026-04-28-viewer-redesign-plan2-stepper-detour-resume-m7.md` for the detour summary. Then **return to Plan 2 M7**: read T2.29-T2.33 in `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-2-kanban-cards.md` (lines ~2872+) and dispatch implementers via `superpowers:subagent-driven-development`. Do **not** continue iterating on the phase stepper unless the user asks. Branch: `feature/taskmaster-v3` in worktree `.worktrees/taskmaster-v3`."

---

## What landed live (committed in c0e31f2)

### Sidebar collapse
- `ui.sidebar_collapsed: false` added to `VIEWER_PREFS_DEFAULTS`. Snapshot test updated.
- Toggle button (chevron) at top-right of `.sidebar-logo`. Click flips `.shell.sidebar-collapsed`, persists via `prefs.patch`.
- Collapsed CSS: `grid-template-columns: 72px 1fr`, smooth transition, section labels become hairline dividers (`font-size: 0` + `border-bottom`), link text + version + footer label fade out.
- Icons centered horizontally in collapsed state via `gap: 0` on the link in the collapsed scope.

### Kanban column collapse animation
- Replaced `flex` shorthand transitions (which don't animate width redistribution reliably) with explicit JS-managed pixel widths.
- `kanban.js#updateGridTemplate(animate)` reads viewport width, computes `cardW = expandedCount > 0 ? (vw - gaps - collapsedCount*66) / expandedCount : 0`, and writes `el.style.width` per column.
- `.no-anim` class on `.kanban-board-grid` skips animation for initial paint and ResizeObserver-driven recomputes; only user-initiated toggles animate.
- Toggle handler updates classes and calls `updateGridTemplate(true)` instead of repainting — DOM survives so transitions actually run.

### Card layout
- `.card-pri` is now `position: absolute; top: 12px; right: 12px;` (top-right corner).
- `.card-meta` and `.card-title` reserve `padding-right: 100px` so absolute pri chip doesn't overlap.
- Copy glyph `.copy-glyph` always visible at 0.4 opacity, 0.9 on hover, on both `card-id` and `card-branch`.
- `.card-branch { user-select: none; }` to match `.card-id`.
- Branch markup includes a `.copy-glyph` icon when `task.branch` is present.

### Topbar refactor
- `index.html` has `<div class="topbar-actions" id="topbar-actions">` slot beside the page-title h1.
- Topbar uses `flex-wrap: nowrap` with `align-items: center`; topbar-actions has `flex: 1 1 0; flex-wrap: wrap; justify-content: flex-end` so the title stays inline and controls cluster at the right.
- Kanban screen no longer renders its own header row; `kanban.js#mount` injects subcount + search + priority chips + density + group + sort + +Task into `#topbar-actions` and clears on cleanup.

### Filter bar
- Phase stepper + epic chips merged into a single `.kanban-filterbar` panel (one border, one padding) with phases stacked over epics, separated by a hairline `border-top` on the second row.

### Phase stepper polish (the live one — pre-brainstorm version)
- Utility buttons (history / all / orphans) are now pill-style with dashed borders, distinct from real phase cards.
- History toggle uses `↺ History` (was unclear `⤺`).
- All-phases shows `⌂ All phases  N/T · X%`. Orphans shows `⚲ Orphans`.
- Real phase cards keep full borders. Connector arrows between consecutive real phases (matched via `[data-key]` adjacency selector) are solid `var(--ink-3)` line + chevron — not the prior gradient hairline.

### Smoke fixture
- `.fixture-kanban/backlog.yaml` expanded to 24 tasks across status mix (4 done, 3 in_progress, 2 in_review, 12 todo, 2 blocked) so columns overflow and per-column scroll exercises.

---

## Brainstorm artifacts (NOT ported live, kept for reference)

Four HTML files dropped into `plugins/taskmaster/viewer/`:

| File | Served at | Purpose |
|---|---|---|
| `brainstorm-phases.html` | `/static/v3/brainstorm-phases.html` | V1-V12 visualization concepts (timeline rail, fill-progress cards, active-dominant, numbered-with-arrow, etc.) |
| `brainstorm-phases-iterations.html` | `/static/v3/brainstorm-phases-iterations.html` | V12B animation iterations A-D (morph pill / circle+callout / vertical card / inline pill) |
| `brainstorm-phases-v12b.html` | `/static/v3/brainstorm-phases-v12b.html` | Single-flex-row interactive: past chips (circle → amber pill morph with name-reveal), per-chip animation duration keyed to name length, future carousel via flex-basis transitions, active card fixed 580px |
| `brainstorm-phases-v12c.html` | `/static/v3/brainstorm-phases-v12c.html` | 3-region anchored layout (past-region right-anchored 380px, active 580px center, future-region flex 1). Future uses **true translateX scroll** (overflow-hidden viewport + inner strip + transform), card width JS-computed to fit 3 cards exactly. Past chips still use morph approach. |

### Open issues with the brainstorm versions

These are unresolved at handoff — captured here so the next session knows the landing zone is not "perfect":

1. **Past chip carousel doesn't yet mirror future's translateX scroll.** v12c future uses a real strip; past still uses individual flex-basis collapse/expand. The user wanted past to feel like the same scroll. Implementing this would require: past-region wraps a `.past-viewport`, all chips in a `.past-strip`, fixed slot widths, `transform: translateX` driven by `pastOffset`. Past chip name-reveal still works inside its slot, but if it widens beyond slot, gets clipped by overflow:hidden.
2. **Selected-state size shifts conflict with overflow:hidden.** Past chips growing into a wider amber pill, future cards growing on selection — both clip when overflow:hidden gates the surrounding region. Current v12c drops `transform: scale` to avoid this; selection signal is now just bg + border + box-shadow.
3. **Past chip animation on quick-clicks (chip A → chip B) still feels slightly jittery** because the row width changes mid-animation as A collapses + B expands. The future carousel is smoother because all motion is `transform`, which doesn't reflow.
4. **Active card narrows when a past phase is filtered** in some variants (510px instead of 620px) to compensate for past-region growth. v12c removed this since 3-region layout absorbs it; v12b kept it.

### Recommendation for porting

When (if) the next session decides to port one of these into the live `viewer/js/components/phase-stepper.js`:
- **V12C is the closest to a final design.** 3-region layout, true translateX future carousel, past expand-on-select, selection signals via color only.
- The required code changes touch `phase-stepper.js` (rewrite the renderer to emit the 3-region structure + strip + slide buttons), `kanban.css` (the styles in v12c's `<style>` block, integrated into the `.kanban-phase-stepper` namespace), and `kanban.js` (pass phase-state from store, wire `prefs.kanban.phase_offset` if you want offsets persisted).
- `prefs.kanban.collapsed_columns` migration pattern (`load_viewer_prefs` deep-merge) is the model — no hard migration needed.

---

## Plan 2 state — what's still left

| Task | Type | Effort | Notes |
|---|---|---|---|
| T2.29 | Playwright config: kanban-aware fixture | impl | ~1h | seed phases + epics + tasks; extend existing fixture |
| T2.30 | Playwright smoke for kanban | TDD | ~1.5h | columns, cards, density, group-by |
| T2.31 | Auto-mode strip Playwright smoke | TDD | ~1.5h | covers deferred T2.24 step 4 (state.json injection) |
| T2.32 | Run all server + unit + smoke + Playwright in sequence | run | 5m | regression check |
| T2.33 | Final integration smoke + plan-close commit | meta | 5m | tick + spec-coverage audit |

After Plan 2 closes (5 tasks left), Plan 3 (Task Detail, 46 tasks) is next.

---

## Hygiene-sweep candidates accumulated this session

Add to the running list (already had items 1-14 carried into Plan-2 wrap):

15. **Phase-stepper redesign port.** Decide: ship v12c into the live kanban as a follow-up plan, or shelve. Brainstorm files can stay in `viewer/` as design-doc references or be moved to `docs/superpowers/`.
16. **Brainstorm files served from production viewer.** `brainstorm-phases*.html` files live in `plugins/taskmaster/viewer/` and are served via `/static/v3/`. Should be moved to `docs/superpowers/brainstorms/` (gitignored) or guarded behind `?dev=1` query param so they don't ship to users.
17. **`ui.sidebar_collapsed` migration.** Like `kanban.collapsed_columns` before it, no explicit migration needed (deep-merge handles it). Verify after a release that existing prefs.json files load cleanly.
18. **Card priority chip overlaps the size badge** when card has both `card-pri.critical` and `card-size: L` because of the 100px right-padding reservation. Verified working in fixture but smoke-test edge cases on real data.
19. **Topbar h1 default text "Loading…" briefly visible** on cold boot. Replace with empty string or current screen name.

---

## Repo gotchas (carried forward)

- `docs/superpowers/` is gitignored — `git add -f` REQUIRED for plan files and PROGRESS.md ticks.
- Worktree-only: `C:\Users\gruku\Files\Claude\claude-tools\.worktrees\taskmaster-v3`.
- Server boot for human smoke (with fixture):
  ```bash
  cd .fixture-kanban
  python -u -c "import sys, threading, time; sys.path.insert(0, r'<absolute path to plugins/taskmaster>'); from backlog_server import _make_server; s, p = _make_server(host='127.0.0.1', port=0); print(f'http://127.0.0.1:{p}/v3#/kanban', flush=True); t = threading.Thread(target=s.serve_forever, daemon=True); t.start(); import time; \nwhile True: time.sleep(3600)"
  ```
- `node --test` glob workaround: `node --test "plugins/taskmaster/viewer/tests/unit/*.test.js"` (must quote the glob on Node 22).
- Brainstorm files served at `/static/v3/brainstorm-phases*.html`.

---

## Files of interest

| Purpose | Path |
|---|---|
| Plan 2 (kanban + cards) | `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-2-kanban-cards.md` |
| Progress index | `docs/superpowers/plans/PROGRESS.md` |
| Last handoff (M6→M7 boundary) | `docs/superpowers/plans/2026-04-27-viewer-redesign-plan2-m6-complete-resume-m7.md` |
| **This handoff** | `docs/superpowers/plans/2026-04-28-viewer-redesign-plan2-stepper-detour-resume-m7.md` |
| Sidebar component | `plugins/taskmaster/viewer/js/components/sidebar.js` |
| Phase stepper (live) | `plugins/taskmaster/viewer/js/components/phase-stepper.js` |
| Kanban screen | `plugins/taskmaster/viewer/js/screens/kanban.js` |
| Kanban CSS | `plugins/taskmaster/viewer/css/screens/kanban.css` |
| Shell CSS (sidebar collapse) | `plugins/taskmaster/viewer/css/shell.css` |
| Card component | `plugins/taskmaster/viewer/js/components/card.js` |
| Prefs schema | `plugins/taskmaster/taskmaster_v3.py` `VIEWER_PREFS_DEFAULTS` |
| Brainstorm sandbox | `plugins/taskmaster/viewer/brainstorm-phases*.html` |

---

## Session start checklist (next session)

1. Read this handoff end-to-end.
2. `git status` — clean except known untracked (`.fixture-kanban`, `.taskmaster`, `viewer/tests/test-results`).
3. Tip should be `c0e31f2`.
4. `python -m pytest plugins/taskmaster/tests/ -q` — must show 212.
5. `node --test "plugins/taskmaster/viewer/tests/unit/*.test.js"` — should show 25.
6. Read T2.29-T2.33 in the plan file. **Do not iterate on the phase stepper** unless the user explicitly asks.
7. Dispatch implementers for M7 via `superpowers:subagent-driven-development`.
