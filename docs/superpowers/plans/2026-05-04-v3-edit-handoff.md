# V3 Edit-in-UI — Phase A Execution Handoff

**For:** the next agent starting Phase A subagent-driven execution
**From:** the brainstorming + planning session of 2026-05-04 (gruku + Opus 4.7)
**Branch:** `feature/taskmaster-v3` (worktree at `.worktrees/taskmaster-v3`)
**Worktree status:** clean except local scratch files (test-results/, start_server.py, .taskmaster/ runtime dirs — all session-local)

## Read first (in this order)

1. **The design spec** — `docs/superpowers/specs/2026-05-04-v3-edit-in-ui-design.md` (commit `7685adf`). 7 locked decisions, full architecture, per-entity field maps, 3-phase build order. ~265 lines.
2. **The implementation plan** — `docs/superpowers/plans/2026-05-04-v3-edit-phase-a.md` (commit `fd6351d`). 15 TDD-structured tasks covering v3-edit-001 through v3-edit-009 with full code blocks and exact file paths. ~4682 lines.
3. **This handoff** — for orientation, pre-flight checklist, traps to avoid.

You should not need to re-derive design decisions. They're locked. If something feels wrong while executing, that's a flag to surface to the user, not to redesign.

## State of the branch — what's already committed

Recent commits (newest first):
```
c279802  chore(taskmaster): file v3-polish-029..033 — bugs discovered while dogfooding v3 viewer
c0e1447  fix(taskmaster): Task Detail md sections overflow on long unbroken strings (v3-polish-031)
df366a4  fix(taskmaster): v3 viewer ↔ server contract — flat tasks + configurable backlog_path
fd6351d  docs(taskmaster): v3-edit Phase A implementation plan
7685adf  docs(taskmaster): v3 edit-in-UI epic design spec
```

The two `fix(taskmaster)` commits are preconditions for Phase A — without them, the v3 viewer's task list and task detail screens are broken. Phase A's plan assumes both are landed.

The chore commit captures backlog metadata for the five bugs discovered while dogfooding (029, 030, 031 — patched; 032, 033 — open; 033 is folded into Phase A's `update_task` primitive).

The two `docs(taskmaster)` commits are force-added under `docs/superpowers/` — that path is gitignored per project convention but committed locally. Don't try to "fix" the gitignore. Per memory note: archive-and-re-ignore before any push.

## Pre-execution checklist (do these before starting Task 1)

The user explicitly deferred these so they could decide ordering. Confirm with the user before proceeding past any of them:

- [ ] **Create the `v3-edit` epic** in `.claude/backlog.yaml` via `mcp__plugin_taskmaster_taskmaster__backlog_add_epic`. Suggested fields:
    - id: `v3-edit`
    - name: `V3 Edit-in-UI`
    - status: `active`
    - description: full edit/create surface inside the v3 viewer for tasks, issues, lessons, handovers, epics, phases — see spec at `docs/superpowers/specs/2026-05-04-v3-edit-in-ui-design.md`.

- [ ] **File the 15 Phase A tasks** under `v3-edit` so progress is trackable in the kanban. Use `backlog_add_task` for each. Map plan-task numbers to backlog IDs:

    | Plan Task | Spec ID | Title (suggested) |
    |---|---|---|
    | 1 | v3-edit-001 | Shared `h()` factory + edit-components demo page |
    | 2 | v3-edit-001 | TextField field renderer |
    | 3 | v3-edit-001 | MdField, EnumSelect, NumberField, DateField renderers |
    | 4 | v3-edit-001 | ChipInput field renderer |
    | 5 | v3-edit-001 | RelationPicker over ChipInput + backlog sources |
    | 6 | v3-edit-001 | Schema validation runner |
    | 7 | v3-edit-002 | entity-modal shell |
    | 8 | v3-edit-003 | inline-field wrapper with autosave |
    | 9 | v3-edit-004 | Task write API + v3 primitives |
    | 10 | v3-edit-005 | ETag/If-Match concurrency for task writes |
    | 11 | v3-edit-006 | Conflict banner + inline-field 409 handling |
    | 12 | v3-edit-007 | Task entity schema |
    | 13 | v3-edit-007 | Wire `+ Task` / `✎ Edit` buttons to entity modal |
    | 14 | v3-edit-008 | Inline-edit retrofit on Task Detail |
    | 15 | v3-edit-009 | Server-side validation pipeline |

    Tasks 1–6 share the spec ID `v3-edit-001` (field-renderer primitives bundle); split into 6 backlog tasks for tracking granularity. Add `phase: ship-v3` and appropriate `priority` for each.

- [ ] **Verify dependent task statuses** — `v3-polish-029`, `v3-polish-030`, `v3-polish-031` should be transitioned to `done` (the patches are committed). `v3-polish-032` stays `todo` (right rail empty-state, deferred). `v3-polish-033` should be marked as `superseded-by v3-edit-009` or similar — its work is folded into Phase A's `update_task` primitive.

- [ ] **Confirm the backlog server can start** — run `python start_server.py` from the worktree root. It should bind to 127.0.0.1:8765 and serve the v3 viewer with `use_v3: true`. Hit `http://127.0.0.1:8765/api/backlog` and `http://127.0.0.1:8765/api/task/v3-skills-004` to verify both endpoints return 200 with real data (regression test for the just-committed v3-polish-029/030 fixes).

## Locked design decisions (so you don't re-litigate them)

From the brainstorming session, these are settled — surface them to the user only if the implementation has a real conflict, not as "have we considered…":

1. **Scope:** all six v3 entities (tasks, issues, lessons, handovers, epics, phases). Phase A delivers TASKS only.
2. **Architecture:** hybrid — shared shell (`entity-modal.js`, `inline-field.js`) + shared field renderers + per-entity composition file (`forms/*-form.js`).
3. **Edit model:** inline click-to-edit per field on detail screens (autosave, 600ms debounce) + centered-overlay modal for create/full-edit (explicit Save).
4. **Affordance:** dotted underline at all times for editable fields + hover pencil ✎. Read-only fields have no underline.
5. **Relation pickers:** chip-input with autocomplete everywhere, plus a custom `AnchorEditor` for lesson glob anchors (Phase B only — not Phase A).
6. **Concurrency:** optimistic ETag/If-Match. 409 returns the current entity + new etag. Inline path uses field-level conflict banner; modal path uses multi-field diff with per-field "keep mine / use server".
7. **Modal:** centered overlay (NOT side drawer, NOT full-page route). Backdrop/Esc cancels-with-confirm if dirty. Save closes on success.
8. **Auth/identity:** localhost-only, no user auth. Server records `last_modified_by` from `/api/identity` for the conflict banner's *"modified by claude (session abc)"* line.
9. **Validation:** three layers — field renderer (`validate(value, spec)`), schema cross-field rules, server-side `backlog_validate` integration.

## Cross-cutting coordination

Phase A's write primitives (`update_task`, `create_task`, `archive_task` in `taskmaster_v3.py`) are shared with future MCP write tools. They are NOT a v3-edit-only concern.

- **`v3-skills-002`** (handover skill — currently `in-review`) and **`v3-skills-003`** (lesson skill — currently `in-review`): if you find yourself adding `update_handover` / `update_lesson` while building Phase A, stop. That's Phase B/C territory. Phase A is task-only.
- **`v3-skills-004`** (issue skill — `todo`, critical): same — coordinate with the issue skill's owner before adding issue write primitives. Plan defers this to Phase B.
- **`v3-edit-008` and `v3-polish-033`** (started/completed auto-stamping) are folded into the same code path. The plan's Task 9 implements `update_task` with the auto-stamp logic; Task 14 verifies it end-to-end via Playwright. Don't accidentally write a separate fix for v3-polish-033 — it's done as part of Task 9.

## Known traps

- **Don't run interactive git commands** via the Bash tool — `git add -i`, `git rebase -i`, `git add -p` will hang. Stage files explicitly by path.
- **`docs/superpowers/` is gitignored.** New plans/specs need `git add -f`. The existing convention works — see how the spec and plan got committed.
- **The dev server doesn't reload Python changes** after edits to `backlog_server.py` or `taskmaster_v3.py`. Restart via TaskStop on the running task + relaunch `start_server.py`. CSS edits ARE reloaded fresh by the static handler — no restart needed for those.
- **`use_v3: true` lives in `.taskmaster/viewer.json`** — already set on this worktree. If the agent boots a fresh viewer prefs file, it'll default to v3=false and the agent will think the v3 viewer is broken. Check the prefs first if you see the legacy viewer.
- **CSS Grid `min-width: auto` foot-gun.** When adding any new grid layout with text content inside, set `min-width: 0` on grid tracks that should be shrinkable. We hit this in v3-polish-031 — don't repeat it.
- **MCP tools call into `taskmaster_v3.py` write primitives** — those primitives must remain backward-compatible. Don't refactor function signatures (`update_task(task_id, patch)`, `create_task(payload)`) without coordinating with MCP wrappers.
- **Test isolation matters.** The pytest `running_server` fixture uses `monkeypatch.chdir(tmp_path)` to isolate state. New tests should follow the pattern. NEVER let tests mutate the real `.claude/backlog.yaml`.
- **The viewer's existing test infra is split** — `npm run test:unit` runs `node --test` on `tests/unit/*.test.js` (jsdom-based, fast). `npx playwright test` runs Playwright on `tests/*.spec.js` (real browser, slower, requires the server up). The plan creates BOTH per task type. Don't conflate them.
- **`task-actions.js` placement.** The plan creates `viewer/js/components/edit/task-actions.js` AND has `task-detail-document.js` import it via `./edit/task-actions.js`. The relative path is correct because both files are under `viewer/js/components/`. Verify with the actual file structure before running tests.

## Recommended execution flow

The plan recommends **subagent-driven development**. Concretely:

1. Read the plan top to bottom once. Don't skim — every code block matters.
2. For each numbered task, spawn a fresh Sonnet subagent via `Agent({ subagent_type: 'general-purpose' })` with:
    - Plan path + task number
    - Brief context (this branch, worktree, dependencies on prior task IDs)
    - Explicit instruction: "Follow the plan steps exactly. Run the tests as specified. Commit at the end of the task. Report back with the commit SHA and test output."
3. After each task: skim the diff + read the test output. If it passes and matches the plan, move on. If something diverged, decide: was the plan wrong (update plan + adjust), or did the subagent improvise (re-spawn with stricter instructions)?
4. Plan tasks 4 (ChipInput) and 9 (HTTP write API + write primitives) are the most complex. Budget extra review time for those.
5. After Task 15, run the full test sweep: `pytest tests/ && npm run test:unit && playwright test`.

If you prefer **inline execution** instead, use `superpowers:executing-plans`. Slower but lets you redirect mid-task.

## Acceptance — what "Phase A done" looks like

1. `+ Task` button on kanban opens a centered modal. Filling required fields + Save creates the task; it appears in the kanban without a manual reload.
2. `✎ Edit` button on Task Detail opens the same modal prefilled with the current task. Editing a field + Save updates the task.
3. Clicking the title on Task Detail enters inline-edit mode. Typing + Enter saves it. The dotted-underline + hover-pencil affordance is visible on every editable field.
4. Inline-editing status from `todo` → `in-progress` triggers an auto-stamp of `started` (visible in the dates row immediately after the next backlog poll, ~3 seconds).
5. Concurrent writes (e.g. an MCP `update_task` call from a Claude session at the same time as inline edit) surface a conflict banner with `Keep mine` / `Use server` actions. No silent data loss.
6. Server returns 422 with `{errors: {field: msg}}` on schema-invalid writes. Modal shows the error in the footer. Inline-field shows ✕ with tooltip.
7. All unit tests green. All Playwright E2E tests green. No regressions in the existing test suite.

## When Phase A is done — proceeding to Phase B

1. Run the brainstorming skill again? No — Phase B/C are already specified in the design spec. Just write a Phase B implementation plan via `superpowers:writing-plans`.
2. The Phase B plan WILL need a fresh brainstorming pass for the `AnchorEditor` UX (live "matches N tasks" feedback) since that's the one bespoke component.
3. Coordinate with `v3-skills-002/003/004` owners before adding handover/lesson/issue write primitives — those skills may have already landed primitives we can consume.

## If you get stuck

- **Plan ambiguity:** flag it to the user. Don't guess at design intent.
- **Test failure that doesn't match the plan's expected output:** the plan was written before any code was run. Some asserts might be slightly off. Adjust the test, not the implementation, only after confirming the implementation is correct against the spec. Document the divergence.
- **`docs/superpowers/` not where you expect:** check the gitignore. The directory is force-added.
- **Backlog metadata stale:** run `mcp__plugin_taskmaster_taskmaster__backlog_status` to see current state.
- **Lost track of what's been committed:** `git log --oneline -20` from this worktree shows the trail.
