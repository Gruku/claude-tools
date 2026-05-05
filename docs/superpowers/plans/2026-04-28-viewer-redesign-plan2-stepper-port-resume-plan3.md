# Viewer Redesign — Handoff after V12C phase-stepper port + kanban layout fixes

**Date:** 2026-04-28
**Branch:** `feature/taskmaster-v3` (worktree at `.worktrees/taskmaster-v3`)
**Plan 2 status:** Same as before this session — T2.25–T2.28 ticked, T2.29–T2.33 (Playwright) **deliberately skipped per user**. Plan 2 is effectively closed for execution; the remaining tasks are deferred.
**Next:** **Plan 3 — Task Detail (46 tasks).** See `2026-04-26-viewer-redesign-plan-3-task-detail.md`.

---

## Resume prompt

> "Resuming the viewer redesign at Plan 3 — Task Detail. Plan 2 is effectively closed; T2.29–T2.33 (Playwright) skipped per user. Read `docs/superpowers/plans/2026-04-28-viewer-redesign-plan2-stepper-port-resume-plan3.md` for what landed in the previous session, then read the full plan at `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-3-task-detail.md`. Confirm with `PROGRESS.md` that the next unchecked task is T3.1. Branch: `feature/taskmaster-v3` in worktree `.worktrees/taskmaster-v3`. Use `superpowers:subagent-driven-development` and dispatch implementers per task. Don't continue iterating on the kanban or phase-stepper unless the user asks."

---

## What landed in this session

### V12C phase stepper ported live
The brainstorm from `viewer/brainstorm-phases-v12c.html` is now the live phase stepper at the top of the kanban filter bar.

- **3-region timeline:** past chips region (content-sized) · fixed-width active card · future-region with translateX scroll carousel.
- **Past chips** are 36px green circles that morph into amber pills with name reveal on selection. Animation duration scales with phase-name length (`--anim-dur: 220ms + 16ms × len`).
- **Future cards** live in a single `transform: translateX` strip inside an `overflow: hidden` viewport. Card width is JS-computed via `ResizeObserver` so exactly 3 fit the viewport.
- **Slide buttons** are circles with corner badges showing the count of hidden chips/cards. They fade out when nothing is hidden in that direction.
- **Connector arrows** between past chips and into the active card render as `::before`/`::after` segments, providing the time-arrow language.
- **No `transform: scale` on selection states** anywhere, so the `overflow: hidden` viewport can never clip a grown chip/card.

The `renderPhaseStepper({ phases, active, onSelect })` public API is unchanged from before; only the internal DOM/CSS swapped. Callers (`kanban.js`) didn't need to change.

### Kanban layout: Done column finally fits
The single root cause was missing `box-sizing: border-box` on `.kanban-col`. JS assigned width via `style.width = floor(...)`, the browser added border (1px each side) + padding (`var(--sp-3)` × 2 = 24px) on top, total +26px per column × 5 cols = +130px overflow → Done off-screen. Codex sub-agent diagnosed it cleanly.

Defensive layout fixes that landed alongside:
- `.shell` grid: `1fr` → `minmax(0, 1fr)` for both expanded and collapsed sidebar variants. Removes the implicit min-content floor on the main grid track.
- `.main` got `min-width: 0`.
- `.screen-mount` got `min-width: 0`.
- `.kanban-board-grid` got `min-width: 0` and `width: 100%`.
- `.kanban-board` overflow flipped from `auto` to `hidden`.
- `updateGridTemplate` now `Math.floor`s each width and gives the last expanded column the leftover, so sub-pixel rounding can't accumulate to overflow.

### Phase chip click toggles back to "all"
Previously the "All phases" pill was the only way to clear a phase filter. With the V12C port we removed that pill (it duplicated the default unfiltered state). The bug: clicking the active phase didn't clear; you were stuck on whatever phase you last picked.
Fix: clicking the currently-selected phase chip/card now sets `state.filters.phase = '__all__'` (toggle behavior). Also fixed `applyFilters` in `lib/filters.js` to treat `'__all__'` as no-filter (it was treating `__all__` as truthy and matching no tasks).

### Topbar: one row even when tight
- `.topbar-actions` is now `flex-wrap: nowrap` with `container-type: inline-size`.
- `.kanban-search { flex: 1 1 280px; min-width: 0 }` — search bar shrinks freely instead of pinning the row wide.
- Priority labels are **always** the 2-letter codes: `Cr / Hi / Me / Lo` (was `Critical / High / Medium / Low`). The full label survives as `title` for hover.
- Density toggle is icon-only: `▤` / `▦` (32×32 squares).
- `.kanban-add-btn`, `.kanban-group-btn`, `.kanban-sort-btn` got `white-space: nowrap; flex: 0 0 auto` so the "+ Task" plus icon never wraps to a second line.
- Container query at `max-width: 1100px` still tightens the group/sort button padding for very narrow viewports.

### Sidebar collapse: narrower + aligned
- Collapsed width: 72px → **56px**.
- Root cause of the icon misalignment: collapsed sidebar switched the `.sidebar-logo` to `flex-direction: column`, stacking the logo mark above the toggle button — adding a full row of height that pushed every link below into a different vertical position than expanded.
- Fix: collapsed `.sidebar-logo` keeps `flex-direction: row`, **hides the logo mark**, and shows only the toggle button centered. Row height now matches expanded mode → all links and section dividers align row-for-row.
- Section dividers in collapsed mode use `color: transparent` (preserves the original padding box) and `box-shadow: inset 0 -1px 0` (so the hairline doesn't add to the box height).

### Kanban scrollbar, deliberate
- `.kanban-col-body { scrollbar-gutter: stable; padding-right: 4px; }` — gutter reserved even when content doesn't overflow, so cards don't shift left/right when items appear/disappear.
- `::-webkit-scrollbar` widened to 8px with subtle track + padding-clipped thumb.

### Collapsed columns clickable
Click anywhere on a collapsed column body now expands it. The toggle button still works; it `stopPropagation`s so clicks don't double-fire.

---

## What's left in Plan 2 (deferred, not started)

- T2.29 Playwright config (kanban-aware fixture)
- T2.30 Playwright kanban smoke
- T2.31 Auto-mode strip Playwright smoke (covers deferred T2.24 step 4)
- T2.32 Run server + unit + smoke + Playwright in sequence
- T2.33 Final integration smoke + plan-close commit

User explicitly said "skip Playwright and other things" before transitioning to Plan 3. These can be picked back up after Plan 3 if/when there's appetite.

---

## Open follow-ups parked from this session

1. **Phase stepper past-chip carousel** doesn't yet mirror future's translateX scroll — past still uses the chip-hidden-flex-collapse pattern. Visually OK after the V12C port, but if the user reports jitter switching past phases, port the same translateX strip pattern over.
2. **No undo on column collapse via keyboard** — only mouse click. Future enhancement.
3. **Density toggle icons are unicode glyphs** — fine on most platforms but font-dependent. Consider switching to inline SVG for guaranteed parity.

---

## Repo gotchas (carried forward)

- `docs/superpowers/` is gitignored — `git add -f` REQUIRED for plan files and PROGRESS.md ticks.
- Worktree-only: `C:\Users\gruku\Files\Claude\claude-tools\.worktrees\taskmaster-v3`.
- Server boot for human smoke (with fixture):
  ```bash
  cd .fixture-kanban
  python -u -c "import sys, threading, time; sys.path.insert(0, r'<absolute path to plugins/taskmaster>'); from backlog_server import _make_server; s, p = _make_server(host='127.0.0.1', port=0); print(f'http://127.0.0.1:{p}/v3#/kanban', flush=True); t = threading.Thread(target=s.serve_forever, daemon=True); t.start(); \nwhile True: time.sleep(3600)"
  ```
- `node --test` glob workaround on Node 22: quote the glob — `node --test "plugins/taskmaster/viewer/tests/unit/*.test.js"`.
- Brainstorm files (V1–V12C) served at `/static/v3/brainstorm-phases*.html` if you need them as design reference for Plan 3.
- `.fixture-kanban/backlog.yaml` was expanded to 11 phases (5 done, 1 active, 5 future) so the V12C past + future carousels can both exercise scrolling.

---

## Files of interest

| Purpose | Path |
|---|---|
| **Plan 3 (Task Detail)** | `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-3-task-detail.md` |
| Progress index | `docs/superpowers/plans/PROGRESS.md` |
| **This handoff** | `docs/superpowers/plans/2026-04-28-viewer-redesign-plan2-stepper-port-resume-plan3.md` |
| Previous handoff (stepper detour) | `docs/superpowers/plans/2026-04-28-viewer-redesign-plan2-stepper-detour-resume-m7.md` |
| Phase stepper component | `plugins/taskmaster/viewer/js/components/phase-stepper.js` |
| Phase stepper styles | `plugins/taskmaster/viewer/css/screens/kanban.css` (search `PHASE STEPPER (V12C` ) |
| Kanban screen | `plugins/taskmaster/viewer/js/screens/kanban.js` |
| Shell layout (sidebar + grid) | `plugins/taskmaster/viewer/css/shell.css` |
| Filter logic (phase `__all__` fix) | `plugins/taskmaster/viewer/js/lib/filters.js` |
| Brainstorm reference | `plugins/taskmaster/viewer/brainstorm-phases-v12c.html` |

---

## Session-start checklist (next session)

1. Confirm branch + worktree:
   ```bash
   git -C C:\Users\gruku\Files\Claude\claude-tools\.worktrees\taskmaster-v3 branch --show-current
   ```
2. `git status` — clean except known untracked (`.fixture-kanban`, `.taskmaster`, `viewer/tests/test-results`, `viewer/tests/package-lock.json`).
3. Read this handoff, then `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-3-task-detail.md`.
4. Confirm via `PROGRESS.md` that T3.1 is the next unchecked task.
5. Use `superpowers:subagent-driven-development`. Dispatch implementer per task; review after each (spec → code quality).
6. Don't touch the phase stepper or kanban unless the user asks.
