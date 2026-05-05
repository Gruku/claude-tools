# Taskmaster Viewer Redesign — Execution Handoff

**Date opened:** 2026-04-27
**Status:** Brainstorm + spec + 7 implementation plans complete · ready for subagent-driven execution
**Prior phase:** Two-session brainstorm (2026-04-26), spec at `docs/superpowers/specs/2026-04-26-taskmaster-viewer-redesign.md`, plan-writing across 6 parallel Opus agents.

---

## Resume prompt for next session

> "Continuing the Taskmaster viewer redesign — execution phase. Read `docs/superpowers/plans/2026-04-27-viewer-redesign-execution-handoff.md` for current state, the recommended execution order, and the cross-plan reconciliation flags. The 7 plans are at `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-{1,2,3,4,5a,5b,6}-*.md` (271 tasks total). Use `superpowers:subagent-driven-development` to execute them plan-by-plan: dispatch a fresh Sonnet subagent per task, two-stage review (code-reviewer subagent then human gate), checkpoint between plans. Progress is tracked at `docs/superpowers/plans/PROGRESS.md` — read it first to see where the previous session stopped, then resume from the first unchecked task."

---

## What's done (don't redo)

- ✅ Spec: `docs/superpowers/specs/2026-04-26-taskmaster-viewer-redesign.md` (locked, all 5 screens + dashboard + kanban + cards + task detail + sidebar; thresholds, file formats, ID conventions all spec'd)
- ✅ Plan 1 — Foundation (28 tasks): shell + tokens + sidebar + router + viewer-prefs HTTP API
- ✅ Plan 2 — Kanban + Cards (33 tasks)
- ✅ Plan 3 — Task Detail (46 tasks): Variants A and B + dependency-graph layout
- ✅ Plan 4 — Dashboard (36 tasks): bento + 13 widgets + edit mode
- ✅ Plan 5a — Sessions + Recap (38 tasks)
- ✅ Plan 5b — Lessons + Issues (32 tasks)
- ✅ Plan 6 — Auto Mode (58 tasks): Quest Spine + Flight Log + parallel sessions
- ✅ Brainstorm handoff doc: `docs/superpowers/specs/2026-04-26-taskmaster-viewer-redesign-HANDOFF-v2.md`
- ✅ 30+ visual mockups under `.superpowers/brainstorm/<active-session>/content/` (the latest dir is the canonical one; earlier dirs are synced copies)

**Total scope:** 271 tasks · ~22,500 lines of plan markdown

## What's open (do next)

Execute the 7 plans in the recommended order via the **subagent-driven-development** skill. See "Execution strategy" below.

---

## Execution strategy — subagent-driven, plan-by-plan

Per `superpowers:subagent-driven-development`, the loop for each task is:

```
┌──────────────────────────────────────────────────────────────────────┐
│ For each unchecked task in the current plan:                         │
│                                                                      │
│   1. Orchestrator (Opus) reads the next task block.                  │
│   2. Dispatch a fresh Sonnet "implementer" subagent with the task    │
│      block verbatim + working dir + the relevant plan file path.     │
│   3. Implementer writes failing test → impl → passing test → commit. │
│   4. Dispatch a Sonnet "code-reviewer" subagent (use the             │
│      superpowers:code-reviewer agent type) reviewing only the diff   │
│      since the last green commit, against the task's acceptance      │
│      criteria.                                                       │
│   5. If reviewer flags blocking issues: bounce back to a fresh       │
│      implementer subagent with the review notes. Repeat 4–5 up to    │
│      twice; if still blocked, escalate to the human (orchestrator    │
│      asks the user how to proceed).                                  │
│   6. Tick the task checkbox in the plan file AND in PROGRESS.md.     │
│   7. Move to the next task.                                          │
│                                                                      │
│ After each plan completes:                                           │
│   • Run the plan's full test suite (pytest + Playwright smoke).      │
│   • Human checkpoint: orchestrator pauses, summarises what landed,   │
│     and asks the user to either continue or stop the session.        │
└──────────────────────────────────────────────────────────────────────┘
```

### Dispatch templates

**Implementer subagent prompt (template):**

```
You are implementing one task in the Taskmaster viewer redesign.

Working dir: C:\Users\gruku\Files\Claude\claude-tools
Plan: docs/superpowers/plans/<plan-file>.md
Task: Task <N> — <name>

Read the plan file end-to-end first. Then execute Task <N> step-by-step.
Follow each numbered step exactly: write failing test, run to confirm it
fails, write implementation, run to confirm it passes, commit.

Architectural conventions (Plan 1 §"Architectural Conventions") are in force
across all plans. Re-read them if you didn't before this task.

Hard rules:
- Do not skip any step. The TDD discipline is the point.
- Do not push to remote. Commit locally only.
- Do not modify files outside this task's "Files" block unless a step
  explicitly requires it.
- If a step's expected output doesn't match what you observe, stop and
  reply with the divergence — do not improvise.

When done, reply with: (a) the commit SHA, (b) the test command output
(last 20 lines), (c) any divergence from the plan you needed to make,
(d) one sentence on what to verify in code review.
```

**Reviewer subagent prompt (template):**

```
You are reviewing a single-task implementation in the Taskmaster viewer
redesign.

Working dir: C:\Users\gruku\Files\Claude\claude-tools
Plan: docs/superpowers/plans/<plan-file>.md
Task: Task <N> — <name>

Read Task <N> in the plan to learn the acceptance criteria, then read the
diff: `git show HEAD` (or `git diff HEAD~1..HEAD` if multiple commits).

Check:
1. Every step in Task <N> appears to have been executed (tests exist, code
   exists, commit message matches the plan's hint).
2. The new code matches Plan 1's architectural conventions (module style,
   screen module shape, CSS naming, state+API, routing, persistence).
3. No "TBD"/"TODO" introduced. No dead code. No unrelated changes.
4. Tests cover the behaviour the task claims to deliver.

Report blocking issues (must fix before merge) and non-blocking nits
separately. Be concise — under 200 words. If everything passes, just say
"approved" and list one thing the orchestrator should sanity-check.
```

### Orchestrator responsibilities

The orchestrator (Opus, in the main session) is the only thing that:
- Reads `PROGRESS.md` to find the next task
- Dispatches the implementer subagent
- Waits, reads the result
- Dispatches the reviewer subagent
- Decides: tick the box, bounce back to implementer, or escalate to user
- Updates `PROGRESS.md` after each task completes
- Pauses for the human gate at every plan boundary

The orchestrator does NOT itself write implementation code. That's the implementer's job. This keeps the main context lean across hundreds of tasks.

---

## Recommended execution order

1. **Plan 1 — Foundation** (28 tasks; everything depends on it)
2. **Plan 2 — Kanban + Cards** (33 tasks; usable on its own; replaces legacy viewer)
3. **Plan 3 — Task Detail** (46 tasks; depends on Plan 1 only; slots in cleanly)
4. **Plan 4 — Dashboard** (36 tasks; depends on Plans 1+2 for shared card/strip components)
5. **Plan 5a — Sessions + Recap** (38 tasks; depends on Plan 1)
6. **Plan 5b — Lessons + Issues** (32 tasks; depends on Plan 1; can run parallel to 5a since they only share `right-rail.js`/`diff-row.js` which 5a owns)
7. **Plan 6 — Auto Mode** (58 tasks; depends on Plans 1+4; refactors `/api/auto/state` from Plan 2's read-only minimum)

**Hard dependencies are 1 → all and 2 → 4. Everything else is soft. If executing serially, follow the order above. If you want to parallelise, only Plans 5a and 5b are safely independent of each other; the rest are at least loosely sequenced.**

---

## Cross-plan reconciliation (apply BEFORE starting execution)

Three real conflicts surfaced from the parallel plan-writing. Resolve them by editing the plan files **before** the first execution session, so the implementer subagents work from a coherent contract.

### 1. Dashboard layout shape — Plan 1 ↔ Plan 4

- **Plan 1** specs `prefs.dashboard.layout[*] = {id, type, size, row, col}`
- **Plan 4** used `{id, type, size, index}` (per-rail flex order — simpler)

**Fix:** Update Plan 1's `VIEWER_PREFS_DEFAULTS` (Task 1, M1) to use `{rails: [{name, items: [{id, type, size}]}]}` or `{layout: [{id, type, size, rail, index}]}`. Pick whichever matches Plan 4's actual usage; copy the exact field set from Plan 4's first widget-render task. Update the Plan 1 defaults test accordingly.

**Estimated edit time:** 5 min.

### 2. prefs API shape — Plan 1 ↔ Plan 6

- **Plan 1** exposes `prefs.patch({...deep-merge object})`
- **Plan 6** referenced `prefs.get('screens.auto_mode.view') / prefs.set(path, value)` (dotted-path style)

**Fix:** Plan 6 should rewrite its three affected tasks (M3 view-toggle wiring, M7 widget-meta read, integration smoke) to use `prefs.patch({screens: {auto_mode: {view: 'B'}}})` style. Mechanical change.

**Estimated edit time:** 10 min.

### 3. `/api/auto/state` shape — Plan 2 ↔ Plan 6

- **Plan 2** introduces a read-only minimum reading from the legacy single `state.json`
- **Plan 6** refactors storage to per-session `.taskmaster/auto/sessions/<sid>.json` files

**Fix:** No edit needed if executed in order. Plan 2 must run first (Plan 6 explicitly replaces Plan 2's `/api/auto/state` handler at its Task 9). When Plan 6 runs, ensure the implementer subagent for that task verifies no other consumer broke (the kanban auto-mode strip is the only known consumer).

**Estimated edit time:** 0 min if order is followed.

### Minor flags — accepted as-is

- Plan 4 mockup ref: `dashboard-v3-zoomed.html` (real filename) instead of `dashboard-v3.html`
- Plan 3 uses `marked@12` CDN with vendored fallback documented
- Plan 2's `spec_review` shape accepts string-or-object — Plan 6 will pin
- Plan 5a regenerate button discards unsaved edits; true LLM regenerate deferred
- Plan 5b dot-meter renders 0 if `anchor_matches_7d` not computed
- Plan 6's hook log producer is consumer-only

---

## Progress tracking

`PROGRESS.md` is the single source of truth for execution state. Schema:

```
# Viewer Redesign — Progress

**Total:** 271 tasks · 7 plans · 0% complete

## Plan 1 — Foundation (0/28)
- [ ] Task 1: Define ViewerPrefs schema constants and defaults
- [ ] Task 2: Implement load_viewer_prefs() and save_viewer_prefs()
- [ ] Task 3: Add viewer_prefs_get and viewer_prefs_set MCP tools
- ... (one line per task)

## Plan 2 — Kanban + Cards (0/33)
- [ ] Task 1: ...
...
```

**Two-place truth:** the same checkbox lives in the plan file (where the task code is) AND in PROGRESS.md (the index). The orchestrator updates both after each task.

The orchestrator's first action in every session is `Read PROGRESS.md` and find the first unchecked line — that's the next task to dispatch.

`PROGRESS.md` will be created as the first execution-session step, alongside the cross-plan reconciliation edits.

---

## Per-plan checkpoints

After each plan completes (last task ticked), the orchestrator pauses and runs the plan's full validation:

- **Plan 1:** `python -m pytest plugins/taskmaster/tests/ -v` + `bash plugins/taskmaster/viewer/tests/run_smoke.sh` — 12 Playwright smoke tests should pass
- **Plan 2:** kanban renders with phase stepper / epic chips / both card densities / auto-mode strip + card live block
- **Plan 3:** `#/task/T-XXX` opens, both Variant A/B render, view-toggle persists across reload
- **Plan 4:** dashboard renders with 12 widgets, edit-mode toggle works, layout persists
- **Plan 5a:** sessions diary renders with parallel-block, recap screen renders one session
- **Plan 5b:** lessons three shelves correctly classified, issues hybrid layout with aging bar
- **Plan 6:** auto-mode page renders both Spine + Log views, sessions strip handles parallel runs

After all 7 plans land:
- Final smoke: every screen renders without console errors, every prefs round-trip persists, no regressions in legacy `backlog-viewer.html` (legacy stays available at `/legacy` for fallback during a soak window).
- Flip the `viewer.use_v3` flag to `true` to make the new viewer default at `/`.

---

## Risks + escalations

**When to escalate to the human (don't try to resolve as orchestrator):**
- Implementer reports diverging from a step's expected output
- Reviewer bounces a task twice without resolution
- A test that "should pass" fails on a fresh run with no code changes (likely environmental — node/playwright/pytest version drift)
- Spec ambiguity surfaces during implementation that wasn't caught in self-review
- Cross-plan contract breaks discovered mid-execution (e.g., Plan 4 widget shape doesn't match Plan 1's data after the reconciliation edit)

**Known fragility:**
- Playwright requires Chromium install. If `npx playwright install chromium` fails in the user's environment, the UI smoke tests skip. Python tests still cover the server. Document the skip.
- The `js-yaml` CDN is loaded at runtime by `main.js`. If offline, the viewer breaks. Plan 1 Task 17 has the load function — easy to swap for a vendored copy if needed.
- The `marked` CDN (Plan 3) has the same offline risk.

**Soak strategy:**
- After each plan, leave the new viewer at `/v3` and keep the legacy viewer at `/`. Don't flip `use_v3` until all 7 plans land and a manual smoke session passes.

---

## Files of interest

| Purpose | Path |
|---|---|
| Spec | `docs/superpowers/specs/2026-04-26-taskmaster-viewer-redesign.md` |
| Brainstorm handoff (v2) | `docs/superpowers/specs/2026-04-26-taskmaster-viewer-redesign-HANDOFF-v2.md` |
| Plan 1 | `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-1-foundation.md` |
| Plan 2 | `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-2-kanban-cards.md` |
| Plan 3 | `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-3-task-detail.md` |
| Plan 4 | `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-4-dashboard.md` |
| Plan 5a | `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-5a-sessions-recap.md` |
| Plan 5b | `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-5b-lessons-issues.md` |
| Plan 6 | `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-6-auto-mode.md` |
| Execution handoff | `docs/superpowers/plans/2026-04-27-viewer-redesign-execution-handoff.md` (this file) |
| Progress index | `docs/superpowers/plans/PROGRESS.md` (created at first execution session) |
| Mockups | `.superpowers/brainstorm/<active-session>/content/*.html` |
| Existing viewer (legacy reference) | `plugins/taskmaster/backlog-viewer.html` |

---

## First execution session — opening checklist

When the next session starts:

1. Read this handoff in full
2. Read `PROGRESS.md` (or create it from the seed below if absent)
3. Apply the three cross-plan reconciliation edits (estimated 15 min total)
4. Commit the reconciliation edits: `chore(plans): cross-plan reconciliation pre-execution`
5. Invoke `superpowers:subagent-driven-development` with: "Execute Plan 1 from `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-1-foundation.md`. Use the dispatch templates in the handoff doc. Stop after Task 28 for human checkpoint."
6. Run the loop until either Plan 1 completes or the human pauses.

### `PROGRESS.md` seed (copy this into a new file at first session)

```markdown
# Viewer Redesign — Progress

**Total:** 271 tasks · 7 plans · 0% complete

## Pre-execution
- [ ] Plan 1 layout-shape reconciliation applied
- [ ] Plan 6 prefs-API reconciliation applied
- [ ] Reconciliation commit landed

## Plan 1 — Foundation (0/28)
*See `2026-04-26-viewer-redesign-plan-1-foundation.md` for task definitions.*
- [ ] T1.1 ViewerPrefs schema constants
- [ ] T1.2 load_viewer_prefs / save_viewer_prefs
- [ ] T1.3 viewer_prefs_get/set MCP tools
- [ ] T1.4 GET /api/viewer/prefs
- [ ] T1.5 PUT /api/viewer/prefs
- [ ] T1.6 Unify _send_json helper
- [ ] T1.7 Scaffold viewer/ + tokens.css
- [ ] T1.8 shell.css + _placeholders.css
- [ ] T1.9 components.css
- [ ] T1.10 index.html shell
- [ ] T1.11 /v3 + /static/v3 routes
- [ ] T1.12 Manual smoke /v3
- [ ] T1.13 api.js
- [ ] T1.14 store.js
- [ ] T1.15 router.js
- [ ] T1.16 sidebar.js
- [ ] T1.17 main.js boot + polling
- [ ] T1.18 dashboard stub
- [ ] T1.19 kanban/task-detail/sessions stubs
- [ ] T1.20 lessons/issues/auto-mode/recap stubs
- [ ] T1.21 Manual smoke nav resolves
- [ ] T1.22 viewer.use_v3 flag at root
- [ ] T1.23 Playwright setup
- [ ] T1.24 smoke.spec.js
- [ ] T1.25 prefs round-trip integration
- [ ] T1.26 viewer/README.md
- [ ] T1.27 Full test suite green
- [ ] T1.28 Plan 1 deliverables verified

## Plan 2 — Kanban + Cards (0/33)
*See `2026-04-26-viewer-redesign-plan-2-kanban-cards.md` for task definitions.*
- [ ] T2.1 — T2.33 (one line per task; copy from plan headings)

## Plan 3 — Task Detail (0/46)
- [ ] T3.1 — T3.46

## Plan 4 — Dashboard (0/36)
- [ ] T4.1 — T4.36

## Plan 5a — Sessions + Recap (0/38)
- [ ] T5a.1 — T5a.38

## Plan 5b — Lessons + Issues (0/32)
- [ ] T5b.1 — T5b.32

## Plan 6 — Auto Mode (0/58)
- [ ] T6.1 — T6.58

## Post-execution
- [ ] All 7 plans complete
- [ ] Manual end-to-end smoke pass
- [ ] viewer.use_v3 flipped to true
- [ ] Soak window (1 week) before retiring legacy viewer
```

The first execution-session task is to expand `T2.1 — T2.33` etc. by reading each plan's task headings and pasting them in. (The first session can have the orchestrator do this in one shot.)

---

## Memory rules from this round

No new memory rules. Existing rules (`memory/feedback_no_left_borders.md`) continue to apply.

---

## Open questions for the user (none blocking)

None. The plans are self-contained. Reconciliation flags are mechanical.

If the user wants to defer the auto-mode page (Plan 6), the redesign can ship Plans 1–5b first; auto-mode would still work via the legacy viewer until Plan 6 lands.

---

**End of handoff.**
