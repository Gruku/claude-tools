# Plan 2 Handoff — M1 + M2 complete, resume at M3 (Card Component)

**Date:** 2026-04-27
**Branch:** `feature/taskmaster-v3` (worktree at `.worktrees/taskmaster-v3` — NOT master)
**Tip:** `d524fad`
**Plan 2 progress:** 8/33 (~24%) — M1 (Tasks 1–4) + M2 (Tasks 5–8) complete; M3 (Tasks 9–13) is next.
**Plan 1:** 28/28 + hygiene sweep complete. Closed by SHA `25eb42a` + sweep commits `95477f5..4e59836`.
**Tests at handoff:** pytest **212/212** · Playwright **12/12** · node `--test` **25/25**

---

## Resume prompt for the next session

> "Resuming the Taskmaster viewer redesign. Plan 1 is fully closed (28/28 + hygiene sweep). Plan 2 M1 + M2 are complete (8/33). Read `docs/superpowers/plans/2026-04-27-viewer-redesign-plan2-m2-complete-resume-m3.md` for current state, dispatch templates, and known follow-ups. Then read the M3 task block in `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-2-kanban-cards.md` (Tasks 9–13, lines 974–1611) before dispatching the first implementer. Confirm in `PROGRESS.md` that the next unchecked task is T2.9. Branch: `feature/taskmaster-v3` in worktree `.worktrees/taskmaster-v3` — NOT master. Use `superpowers:subagent-driven-development`: per-task loop is implementer subagent → spec reviewer subagent → code-quality reviewer subagent → tick PROGRESS.md + plan-file checkboxes → next task. Pause for human checkpoint after T2.13 (M3 wraps with a 'render two cards in dev console' visual sanity step that benefits from an eyeball check)."

---

## What got done in this session

### M1 — Auto-mode HTTP Read (Tasks 1–4)

| Task | Impl SHA | Tick SHA | Spec | Code |
|---|---|---|---|---|
| T2.1 `_load_auto_state` helper | `1ff9185` | `6212a52` | ✅ | ✅ |
| T2.2 `GET /api/auto/state` route | `be399d0` | `e058126` | ✅ | ✅ |
| T2.3 `api.autoState()` | `789fd20` | `61615a7` | (one-liner — combined inspection) |
| T2.4 `pollAutoStateForever` | `afc46ac` | `b26683b` | ✅ | ✅ |

Notable adaptation: T2.4's `pollAutoStateForever` was extended beyond the plan's verbatim minimal body to mirror the hygiene-sweep'd `pollBacklogForever` shape — visibility-aware pause + exponential backoff capped at 60s. The plan was written pre-sweep; spec reviewer accepted the polish as the team-standard pattern. Plan-prescribed core behaviors (call `api.autoState()`, set on success, console.error + set-null on error) all preserved.

### M2 — Pure-Logic Libraries (Tasks 5–8)

| Task | Impl SHA | Tick SHA | Tests added |
|---|---|---|---|
| T2.5 `lib/time.js` | `cfa30e5` | `d474ff3` | 7 (node) |
| T2.6 `lib/epics.js` | `afa56dc` | `196ec1e` | 6 (node) |
| T2.7 `lib/filters.js` | `c28d1dc` | `98a5b2a` | 12 (node) |
| T2.8 `lib/copy.js` + components.css | `e236e6b` | `d524fad` | 0 (Playwright in T2.31) |

Combined spec + code-quality review: ✅ APPROVED — verbatim implementations, no real bugs.

Notable adaptation (T2.5): added `"type": "module"` to pre-existing `plugins/taskmaster/viewer/tests/package.json` to suppress Node's `MODULE_TYPELESS_PACKAGE_JSON` warning on ESM test files. Plan didn't mention the file — outside the verbatim block but pragmatic and accepted.

---

## Bounce-back / failure log

**Zero bounce-backs across M1 + M2.** All 8 tasks passed both review gates on first attempt. TDD discipline confirmed across T2.1, T2.2, T2.5, T2.6, T2.7 — implementer captured the expected RED error each time.

---

## Plan 2 state — what's left after this handoff

Plan 2 has **7 milestones / 33 tasks**. After this session: **M1 ✓ M2 ✓** → 25 tasks remaining across **M3 → M7**.

| Milestone | Tasks | Theme | Estimated session size |
|---|---|---|---|
| M3 — Card Component | 9–13 | kanban.css skeleton, Minimal + Full + Variant E card CSS, `components/card.js`, `components/auto-mode-live-block.js`, dev-console sanity | 1 session (5 tasks, mostly mechanical) |
| M4 — Auto-mode UI | 14–16 | Spinner + strip CSS, `auto-mode-strip.js`, session-timer ticks | 1 session (3 tasks) |
| M5 — Kanban Controls | 17–22 | priority-chips, phase-stepper, epic-chips, group-by + sort dropdowns, board surface CSS, density toggle | 1–2 sessions (6 tasks) |
| M6 — Kanban Screen | 23–28 | screen module integration + manual smoke + density round-trip + group-by/+task/click-to-copy smoke | 1–2 sessions (6 tasks) |
| M7 — Tests + Polish | 29–33 | Playwright kanban-aware fixture, kanban smoke, auto-mode strip smoke, full-suite run, plan-level commit | 1 session (5 tasks) |

Plans 3–6 follow Plan 2; same `feature/taskmaster-v3` branch.

---

## M3 — what to do next (Tasks 9–13)

Plan source: `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-2-kanban-cards.md`, lines 974–1611.

### Quick task summary

- **T2.9** — Create `viewer/css/screens/kanban.css` with the page-layout/head/search/group-btn/sort-btn/add-btn styles + per-screen tokens. Link the new CSS from `index.html`. Single commit. (~60 lines CSS.)
- **T2.10** — Append card CSS to `kanban.css`: Minimal density, Full density, Variant E (per-epic chip + ID color, NO edge stripes / NO body wash). Includes `--card-recent-glow` highlight, click-to-copy span style. Single commit.
- **T2.11** — Create `viewer/js/components/card.js` — pure render function `mountCard(taskNode, ctx)` returning a DOM element. Uses `lib/time.formatTimeInStatus`, `lib/epics.epicCssVar`, `lib/copy.bindCopy`. Single commit. (Pure-logic + DOM — no unit test in this task; rendered later in T2.13 + T2.30 Playwright.)
- **T2.12** — Create `viewer/js/components/auto-mode-live-block.js` — per-card live block when this card is the auto-mode target. Uses `lib/time.formatElapsed`. Reads `store.getAutoState()`.
- **T2.13** — Sanity step: open `/v3` in browser, paste a snippet into the dev console that imports the card module and renders two demo cards into `<body>`. Verify visual fidelity vs the mockups in `.superpowers/brainstorm/15283-1777223061/content/card-views.html` and `card-experiments.html`. **This is a human eyeball checkpoint.** Document any visual divergence; fix in T2.10 if structural, defer to a hygiene candidate if cosmetic.

### Dispatch template (M3 tasks)

Use the same per-task pattern as M1/M2:

```
[Implementer dispatch — Sonnet]
Working dir: C:\Users\gruku\Files\Claude\claude-tools\.worktrees\taskmaster-v3
Branch: feature/taskmaster-v3 (do NOT push)

Task: T2.<X> — <verbatim from plan>
- Read the plan task in full from lines <start>–<end>.
- Real TDD where the plan prescribes tests; pure file creation otherwise.
- After commit, tick step checkboxes in the plan file + T2.<X> in PROGRESS.md.
  Use `git add -f` for both (docs/superpowers/ is gitignored).
- Don't modify files outside the task's "Files" block.
- Run pytest after each task → must stay at 212. Run node --test where applicable.
- Heredoc for commit messages.
- Status: DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED.

[Spec reviewer — Sonnet]
Verbatim text from plan. Check impl SHA matches. Check tick SHA only flips checkboxes.
Output: ✅ SPEC COMPLIANT or ❌ ISSUES.
NOT a code-quality review.

[Code reviewer — superpowers:code-reviewer (Sonnet)]
Diff in <impl SHA> only. Flag REAL bugs. Don't re-flag plan-prescribed style or known hygiene candidates.
Output: ✅ APPROVED with optional candidates, or ❌ BLOCKING.
```

For tasks like T2.11 / T2.12 that mostly mount DOM with no unit test, lean on read-throughs of the actual file rather than test gates. T2.13 is human-eyeball — the orchestrator can run the server + open the browser, OR delegate to `claude-in-chrome` MCP to drive it.

### Skip-able TDD steps in M3

- T2.9, T2.10, T2.13 are CSS / browser-only — no test step. Plan doesn't prescribe one.
- T2.11, T2.12 are DOM components — plan prescribes Playwright coverage in T2.30 / T2.31, NOT inline unit tests. Don't invent tests.

---

## Hygiene-sweep candidates (carry into Plan-2 wrap)

Already catalogued during M1+M2 reviews — log these for a Plan-2 hygiene sweep at the end of Plan 2 (or fold into Plan 1's standalone tickets if behavioral):

1. **`running_server` fixture duplicated** between `test_server_api.py` and `test_server_auto_state.py` → consolidate into `tests/conftest.py`.
2. **Polling helpers shape-duplicate** — `pollBacklogForever` and `pollAutoStateForever` share visibility-aware + backoff structure. Extract `pollForever(label, fn, intervalMs)` helper. (Low priority; both functions are read-only loops.)
3. **`AUTO_STATE_POLL_MS` placement** — declared mid-file in `main.js` rather than near `BACKLOG_POLL_MS` at top.
4. **`epics.js epicCssVar` regex fall-through** — silent FALLBACK rgb on non-`#rrggbb` input. Not reachable today (palette is all 6-digit hex), but a guard or comment would harden.
5. **`filters.js groupByPhase`** — always appends `__orphans__` even when empty. Caller (kanban screen) needs to hide zero-count groups OR add a one-line note documenting that contract.
6. **`test_server_auto_state.py` symmetry** — second endpoint test doesn't assert Content-Type / CORS header (the first does). Spot-check robustness gap.

**Behavioral, not in sweep:**
- `load_viewer_prefs` malformed-JSON guard (carried over from Plan 1 backlog — still its own ticket).

---

## Known repo gotchas (carry-forward)

- **`docs/superpowers/` is gitignored.** `git add -f` is REQUIRED for plan-file and PROGRESS.md ticks. Don't skip the tick commit on the false claim that they "can't be committed".
- **The worktree is the only place this work happens.** All implementer subagents must use the worktree path (`C:\Users\gruku\Files\Claude\claude-tools\.worktrees\taskmaster-v3`).
- **`viewer/tests/package.json` now declares `"type": "module"`** (added in T2.5 to suppress ESM warnings). Future tests can use ESM imports without warnings; mind this if any future task adds CJS code under `viewer/tests/`.
- **node `--test` directory:** `plugins/taskmaster/viewer/tests/unit/`. Three test files at handoff: `time.test.js`, `epics.test.js`, `filters.test.js`. Run with `node --test plugins/taskmaster/viewer/tests/unit/`.
- **Server boot for human smoke:**
  ```bash
  python -u -c "from backlog_server import _make_server; s, p = _make_server(host='127.0.0.1', port=0); print(f'http://127.0.0.1:{p}/v3'); s.serve_forever()"
  ```
  (Run from `plugins/taskmaster/`.)
- **Playwright smoke runner:** `bash plugins/taskmaster/viewer/tests/run_smoke.sh` (already adapted in hygiene sweep — daemon=True + main-thread sleep).

---

## Files of interest

| Purpose | Path (relative to worktree root) |
|---|---|
| Plan being executed | `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-2-kanban-cards.md` |
| Progress index | `docs/superpowers/plans/PROGRESS.md` |
| Original execution handoff (full 271-task picture) | `docs/superpowers/plans/2026-04-27-viewer-redesign-execution-handoff.md` |
| Plan 1 close handoff (M3 → M4) | `docs/superpowers/plans/2026-04-27-viewer-redesign-m3-complete-resume-m4.md` |
| **This handoff** | `docs/superpowers/plans/2026-04-27-viewer-redesign-plan2-m2-complete-resume-m3.md` |
| Server module | `plugins/taskmaster/backlog_server.py` |
| Auto-state helper + route | added in T2.1 / T2.2 (around line 106 / line 3923) |
| Static viewer | `plugins/taskmaster/viewer/` |
| Pure-logic libs created in M2 | `plugins/taskmaster/viewer/js/lib/{time,epics,filters,copy}.js` |
| Unit tests | `plugins/taskmaster/viewer/tests/unit/{time,epics,filters}.test.js` |
| Server tests | `plugins/taskmaster/tests/test_server_auto_state.py` (new in T2.1+T2.2) |
| Hygiene-sweep ledger | This file's "Hygiene-sweep candidates" section |
| Memory pointers | `MEMORY.md` → `project_superpowers_local_tracking.md`, `reference_python_env_quirks.md` |

---

## Session start checklist (next session)

1. Read this file end-to-end.
2. `git -C C:\Users\gruku\Files\Claude\claude-tools\.worktrees\taskmaster-v3 status` — must be clean. Tip should be `d524fad`. Untracked `.taskmaster/`, `viewer/tests/package-lock.json`, `viewer/tests/test-results/` are pre-existing — ignore.
3. `python -m pytest plugins/taskmaster/tests/ -q` from worktree root — must show 212 passing.
4. `node --test plugins/taskmaster/viewer/tests/unit/` — must show 25 passing.
5. `bash plugins/taskmaster/viewer/tests/run_smoke.sh` — must show 12/12 (boots server, runs Playwright).
6. `head -40 docs/superpowers/plans/PROGRESS.md` — confirm T2.8 ticked, T2.9 unticked.
7. Skim `Architectural Conventions` of Plan 1 (its preamble) — JS / CSS conventions still apply for M3 onward.
8. Read M3 in full: lines 974–1611 of the plan file.
9. Dispatch the T2.9 implementer using the template above.
10. Run the loop through T2.13. Stop after T2.13 for the next human checkpoint (the in-browser visual sanity render).

---

## Big picture — what's left after Plan 2

After Plan 2 completes (33 tasks across M3–M7), the natural break point is **Plan 3 (Task Detail, 46 tasks)**. Plans 3–6 share the architectural conventions defined at the top of Plan 1; re-read before each new plan begins.

Total backlog after this session: **243 / 271** still pending (Plan 2 has 25 left after M2; Plans 3–6 = 210; post-execution housekeeping = 4 + 4 in this hygiene ledger).
