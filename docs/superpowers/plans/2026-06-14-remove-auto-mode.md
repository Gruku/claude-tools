# Remove Auto Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove taskmaster's in-plugin "auto mode" subsystem (state machine, MCP tools, HTTP endpoints, 3 driver skills, viewer surfaces, tests) and replace the user-facing entry with a thin router redirect to ultracode; ship as 3.17.0.

**Architecture:** Subtractive refactor + one small additive redirect. No new runtime component. Each task bundles a source removal *with* its test updates so the suite stays green at every commit (except the deliberate TDD-red guard in Task 1). Reusable presentational viewer components are preserved dormant; goal design docs are superseded, not deleted.

**Tech Stack:** Python (FastMCP server + stdlib HTTP viewer), vanilla ES-module viewer JS/CSS, pytest, `node --test`, Playwright.

**Spec:** `docs/superpowers/specs/2026-06-11-remove-auto-mode-design.md` (spec-review PASS, revised 2026-06-14).

**Conventions:**
- All `pytest` commands run from `plugins/taskmaster/`.
- All `npm`/Playwright commands run from `plugins/taskmaster/viewer/`.
- The auto block in `taskmaster_v3.py` is **two sub-ranges** with a **non-auto `VIEWER_PREFS_DEFAULTS` island between them** — delete by symbol boundary, never by a single line span.
- Relocate every deletion by **symbol**, not the line numbers below (they are hints and will drift as siblings land).

**Sequencing note (from spec edge-cases):** `v3-release-010` and `project-manifest-001` are in-progress in `taskmaster_v3.py`. Land this work *after* they merge, or expect a large conflict on Task 2.

---

## Task 1: Negative-guard test (TDD red)

Write the regression guard first. It fails now (auto tools still registered) and turns green when Task 2 removes them. Committed red per the project's TDD-first convention.

**Files:**
- Modify: `tests/test_dead_tool_cull.py`

- [ ] **Step 1: Add the guard test**

Append to `tests/test_dead_tool_cull.py` (it already imports `_list_tool_names` from `test_mcp_v3_exposure` and uses `pytest`):

```python
@pytest.mark.parametrize("tool_name", [
    "backlog_auto_start",
    "backlog_auto_status",
    "backlog_auto_advance",
    "backlog_auto_complete_task",
    "backlog_auto_finish",
    "backlog_auto_abort",
])
def test_auto_mode_tools_removed(tool_name):
    """Regression guard: no backlog_auto_* tool may be registered after auto removal."""
    assert tool_name not in _list_tool_names()
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `python -m pytest tests/test_dead_tool_cull.py::test_auto_mode_tools_removed -q`
Expected: FAIL (6 params) — tools are still registered.

- [ ] **Step 3: Commit the red guard**

```bash
git add plugins/taskmaster/tests/test_dead_tool_cull.py
git commit -m "test(taskmaster): failing negative-guard for auto-mode tool removal (remove-auto-mode-001)"
```

---

## Task 2: Backend removal — `taskmaster_v3.py` + `backlog_server.py` + backend tests

Delete the state machine and its MCP/HTTP surface; update/delete backend tests; the Task 1 guard goes green.

**Files:**
- Modify: `taskmaster_v3.py`
- Modify: `backlog_server.py`
- Modify: `tests/test_mcp_v3_exposure.py`
- Modify: `tests/test_dead_tool_cull.py`
- Delete: `tests/test_server_auto_mode.py`, `tests/test_server_auto_state.py`, `tests/test_auto_lane_aware.py`, `tests/test_auto_lane_driver.py`

- [ ] **Step 1: Delete the auto block in `taskmaster_v3.py` (two sub-ranges, preserve the island)**

Sub-range 1 — from the section comment `# ── Auto mode (state machine) ──` (hint: line 4132) through the end of `migrate_auto_state_to_sessions` (hint: ~line 4340). This covers constants `AUTO_MODES`, `AUTO_STAGES`, `AUTO_STAGE_GATE`, `_LANE_STAGE_SEQUENCE`, `AUTO_TASK_STATUSES`, `AUTO_FAIL_REASONS`, `AUTO_MODELS`, `AUTO_DIR`, `AUTO_SESSIONS_DIR`, `AUTO_HOOKS_LOG`, `AUTO_LEGACY_STATE`, and functions `auto_stages_for_lane`, `auto_session_path`, `auto_events_path`, `save_auto_session`, `load_auto_session`, `list_auto_sessions`, `append_auto_event`, `read_auto_events`, `compute_budget`, `read_hook_events`, `migrate_auto_state_to_sessions`.

**PRESERVE the island** that follows: `VIEWER_PREFS_SCHEMA_VERSION`, `VIEWER_PREFS_DEFAULTS`, `viewer_prefs_path`, `load_viewer_prefs`, `save_viewer_prefs` (hint: lines 4343–4449). Do not touch these except Step 2.

Sub-range 2 — from `auto_sessions_dir` (hint: line 4451) through the end of `auto_run_summary` (hint: line 4780, the last line before `format_recap`). This covers `auto_sessions_dir`, `auto_session_path_bp`, `auto_events_path_bp`, `append_auto_event_bp`, `_migrate_legacy_state_for_bp`, `auto_state_path`, `read_auto_state`, `write_auto_state`, `clear_auto_state`, `init_auto_run`, `next_planned_stage`, `advance_stage`, `complete_current_task`, `auto_run_summary`.

- [ ] **Step 2: Remove the `auto_mode` prefs default**

In `VIEWER_PREFS_DEFAULTS["screens"]` (hint: line 4360) delete the single entry:
```python
"auto_mode":   {"view": "A"},   # spine | log
```
Keep the surrounding `screens` dict and the trailing comma on the preceding `"issues"` entry.

- [ ] **Step 3: Remove auto imports + helpers + tools + endpoints in `backlog_server.py`**

1. In the `from taskmaster_v3 import (...)` block (hint: lines 57–178), delete the 16 auto names: `AUTO_MODES`, `AUTO_STAGES`, `AUTO_STAGE_GATE as _AUTO_STAGE_GATE`, `auto_stages_for_lane as _auto_stages_for_lane`, `AUTO_TASK_STATUSES`, `AUTO_FAIL_REASONS`, `init_auto_run as _init_auto_run`, `read_auto_state as _read_auto_state`, `write_auto_state as _write_auto_state`, `clear_auto_state as _clear_auto_state`, `append_auto_event_bp as _append_auto_event_bp`, `advance_stage as _advance_stage`, `next_planned_stage as _next_planned_stage`, `complete_current_task as _complete_current_task`, `auto_run_summary as _auto_run_summary`, `read_hook_events as _read_hook_events`. Keep `load_viewer_prefs`, `save_viewer_prefs`, `load_recap`, etc.
2. Delete `_load_auto_state` (hint: lines 256–273) entirely.
3. Delete the 6 `@mcp.tool()` functions (contiguous, hint: lines 4337–4592): `backlog_auto_start`, `backlog_auto_status`, `backlog_auto_advance`, `backlog_auto_complete_task`, `backlog_auto_finish`, `backlog_auto_abort`. (Note: `backlog_auto_advance` calls `backlog_record_gate` — that's an outbound call; `backlog_record_gate` itself stays.)
4. Delete the 5 non-tool helpers (contiguous, hint: lines 9201–9257): `auto_state_get`, `auto_pause`, `auto_stop`, `auto_history`, `auto_event_log`.
5. In `do_GET`, delete the 5 auto `elif` clauses (hint: lines 7888–7958): `/api/auto/sessions`, `/api/auto/sessions/<sid>`, `/api/auto/state`, `/api/auto/events`, `/api/auto/budget/<sid>`. Ensure the next surviving clause (`/api/viewer/prefs`) remains a valid `elif` attached to the prior surviving `elif`.
6. In `do_POST`, delete the `if self.path in ("/api/auto/pause", "/api/auto/stop"):` block (hint: lines 8402–8429).
7. In `_init_storage`, remove the auto body lines (hint: 9042–9044): the inline `from taskmaster_v3 import migrate_auto_state_to_sessions, AUTO_SESSIONS_DIR`, the `AUTO_SESSIONS_DIR.mkdir(...)`, and the `migrate_auto_state_to_sessions()` call. Keep the `_init_storage` function (called from `_start_viewer_server`); if its body becomes empty, leave the remaining non-auto setup or add `pass` only if nothing else remains.

- [ ] **Step 4: Delete the 4 backend auto test files**

```bash
git rm plugins/taskmaster/tests/test_server_auto_mode.py \
       plugins/taskmaster/tests/test_server_auto_state.py \
       plugins/taskmaster/tests/test_auto_lane_aware.py \
       plugins/taskmaster/tests/test_auto_lane_driver.py
```

- [ ] **Step 5: Edit `tests/test_mcp_v3_exposure.py`**

1. Delete the entire `test_auto_mode_tools_exposed` group (comment + `@pytest.mark.parametrize` + function, hint: lines 152–165).
2. In `test_full_v3_surface_count` remove `"auto_"` from the keyword tuple (hint: line 204).
3. Lower the floor (hint: line 208) by 6 (currently `>= 36` → `>= 30`); update the adjacent comment to note the auto removal.

- [ ] **Step 6: Edit `tests/test_dead_tool_cull.py`**

Remove the 5 auto entries from the `CULLED` list (hint: lines 27–31): `"auto_state_get"`, `"auto_pause"`, `"auto_stop"`, `"auto_history"`, `"auto_event_log"`. (Their functions no longer exist; the Task 1 guard now covers the auto tools.) Leave `KEPT` and all other entries.

- [ ] **Step 7: Run the guard + the affected suites**

Run: `python -m pytest tests/test_dead_tool_cull.py tests/test_mcp_v3_exposure.py -q`
Expected: PASS (guard `test_auto_mode_tools_removed` now green; surface-count test passes at new floor).

- [ ] **Step 8: Run the full Python suite**

Run: `python -m pytest tests/ -q`
Expected: PASS — no import errors, no references to deleted symbols. (Skill-lint auto tests still exist here; they pass because the skill dirs are deleted in Task 3.)

- [ ] **Step 9: Commit**

```bash
git add -A plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/
git commit -m "refactor(taskmaster): remove auto state machine + MCP tools + HTTP endpoints (remove-auto-mode-001)"
```

---

## Task 3: Skills removal + edits + skill-lint cleanup

Delete the 3 driver skills and their lint tests; update the hardcoded `SKILL_BUDGETS`; scrub auto references from the remaining skills and add the router redirect.

**Files:**
- Delete: `skills/auto-task/`, `skills/auto-epic/`, `skills/auto-phase/` (whole dirs), `skills/end-session/references/auto-mode.md`, `tests/test_auto_epic_skill_lint.py`, `tests/test_auto_phase_skill_lint.py`, `tests/test_auto_task_skill_lint.py`
- Modify: `tests/skill_budget_helper.py`, `skills/end-session/SKILL.md`, `skills/pick-task/references/v3-context-loading.md`, `skills/taskmaster/SKILL.md`, `skills/taskmaster/references/routing-table.md`, `skills/taskmaster/references/disambiguation.md`, `skills/migrate-v3/SKILL.md`, `skills/migrate-v3/references/v2-vs-v3.md`, `skills/migrate-v3/references/migration-steps.md`, `skills/handover/SKILL.md`, `skills/handover/references/session-kinds.md`, `skills/init-taskmaster/SKILL.md`, `skills/init-taskmaster/references/analysis-mode.md`

- [ ] **Step 1: Delete the 3 driver skills + 3 lint tests + the end-session auto reference doc**

```bash
git rm -r plugins/taskmaster/skills/auto-task plugins/taskmaster/skills/auto-epic plugins/taskmaster/skills/auto-phase
git rm plugins/taskmaster/skills/end-session/references/auto-mode.md
git rm plugins/taskmaster/tests/test_auto_epic_skill_lint.py \
       plugins/taskmaster/tests/test_auto_phase_skill_lint.py \
       plugins/taskmaster/tests/test_auto_task_skill_lint.py
```

- [ ] **Step 2: Remove auto entries from `SKILL_BUDGETS`**

In `tests/skill_budget_helper.py` delete the three dict entries (hint: lines 19, 22, 23): `"auto-task": 1_500`, `"auto-epic": 1_200`, `"auto-phase": 1_200`. (This dict is the hardcoded source for `test_skill_body_budgets.py`, `test_skill_description_budgets.py`, `test_skill_catalog_smoke.py` — they fail with `FileNotFoundError` if the entries remain after the dirs are deleted.)

- [ ] **Step 3: Add the router redirect + scrub `skills/taskmaster/`**

In `skills/taskmaster/references/routing-table.md` replace the three auto rows (hint: lines 51–53) with one redirect row:
```
| (v3) "auto this task", "autopilot", "auto-epic X", "auto T-001" | Redirect: auto mode removed — suggest **ultracode** (Workflow orchestration) |
```
In `skills/taskmaster/SKILL.md`:
- Frontmatter `description` (line 3): change `…lessons, auto-mode). The only…` → `…lessons). The only…`.
- Body intent table (hint: lines 27–28): delete the two rows `| "Auto this task", "autopilot T-001" | ... |` and `| "Auto-epic <id>", "auto-phase <id>" | ... |`. Add one redirect row in their place:
```
| "auto this task", "autopilot", "auto-epic/phase X" | Redirect to ultracode (auto removed) |
```
- Disambiguation pointer (hint: line 47): change `(handover vs end-session, issue vs task, lesson vs note, auto-task vs pick-task)` → `(handover vs end-session, issue vs task, lesson vs note)`.

In `skills/taskmaster/references/disambiguation.md` delete the `## auto-task vs pick-task` section (heading + 2 bullets, hint: lines 28–31).

- [ ] **Step 4: Scrub `end-session` and `pick-task`**

`skills/end-session/SKILL.md` (hint: line 87): delete the bullet ``- `references/auto-mode.md` - behavior when `backlog_auto_status` reports an active run.``

`skills/pick-task/references/v3-context-loading.md` (hint: lines 24–27): delete the `## When auto modes call this skill` section (heading + 3 paragraphs). Keep the preceding token-budget section.

- [ ] **Step 5: Scrub `migrate-v3` (3 files)**

`skills/migrate-v3/SKILL.md`:
- Line 3: remove `'turn on auto-mode', ` from the trigger list in `description`.
- Body (hint: line 8): `…issues, recap, and auto-mode.` → `…issues, and recap.`

`skills/migrate-v3/references/v2-vs-v3.md`:
- Delete the `| `auto/` | `state.json` — auto-mode execution cursor | Yes |` table row (hint: ~line 61).
- Prose (hint: line 63): ``snapshots/` and `auto/` hold runtime state…offers to add them` → ``snapshots/` holds runtime state…offers to add it`.

`skills/migrate-v3/references/migration-steps.md`:
- Step 8 (hint: line 41): `Check whether .gitignore contains .taskmaster/snapshots/ and .taskmaster/auto/. If either is missing…add them` → `Check whether .gitignore contains .taskmaster/snapshots/. If missing…add it`. Also remove `.taskmaster/auto/` from the gitignore content block appended in that step (hint: lines 43–45 — read carefully when editing).
- Step 9 (hint: line 53): delete the bullet `- Auto modes -- taskmaster:auto-task, auto-epic, auto-phase for state-machine-driven execution.`

- [ ] **Step 6: Scrub `handover` (2 files) + `init-taskmaster` (2 files)**

`skills/handover/SKILL.md` (hint: line 22): remove `; from auto-task loop -> \`auto-stage\`` from the `session_kind` override list.

`skills/handover/references/session-kinds.md`:
- Delete the `| `auto-stage` | Written by `auto-task`… |` table row (hint: line 10).
- Delete selection-algorithm item `1. Invoked by `auto-task`? → `auto-stage`.` (hint: line 16) and renumber the remaining items.

`skills/init-taskmaster/SKILL.md`:
- Line 29: `…issues, recap, auto-mode."` → `…issues, and recap."`.
- Line 45: `If v3, gitignore `.taskmaster/snapshots/` and `.taskmaster/auto/`.` → `If v3, gitignore `.taskmaster/snapshots/`.`

`skills/init-taskmaster/references/analysis-mode.md` (hint: line 43): delete the `- Auto modes -- taskmaster:auto-task, auto-epic, auto-phase…` bullet.

(Do NOT touch `skills/decision/references/auto-resolution.md` — confirmed false positive: it covers decision auto-resolve, not auto mode.)

- [ ] **Step 7: Run the skill-lint + catalog suites**

Run: `python -m pytest tests/test_skill_body_budgets.py tests/test_skill_description_budgets.py tests/test_skill_catalog_smoke.py -q`
Expected: PASS — no `FileNotFoundError` for the deleted skills.

- [ ] **Step 8: Run the full Python suite**

Run: `python -m pytest tests/ -q`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add -A plugins/taskmaster/skills/ plugins/taskmaster/tests/
git commit -m "refactor(taskmaster): delete auto driver skills + redirect router to ultracode (remove-auto-mode-001)"
```

---

## Task 4: Viewer JS teardown + dormant archive

Unwire live JS surfaces, delete the non-reusable wrappers, move reusable components to `_dormant/`, and handle the one unit test coupled to a moved file.

**Files:**
- Modify: `viewer/js/main.js`, `viewer/js/components/sidebar.js`, `viewer/js/screens/kanban.js`, `viewer/js/components/task-detail-document.js`, `viewer/js/api.js`, `viewer/js/store.js`, `viewer/js/components/card.js`, `viewer/js/screens/desk.js`, `viewer/js/lib/topbar.js`
- Delete: `viewer/js/components/auto-status.js`, `viewer/js/components/auto-mode-strip.js`, `viewer/js/components/sessions-strip.js`, `viewer/js/lib/auto-state.js`, `viewer/tests/unit/auto-spine-layout.test.js`
- Move (to `viewer/js/_dormant/`): `quest-spine.js`, `auto-spine-layout.js`, `flight-log.js`, `auto-side-panels.js`, `auto-mode-live-block.js`, `screens/auto-mode.js`
- Create: `viewer/js/_dormant/README.md`

- [ ] **Step 1: Unwire `main.js`**

Remove: the `import { mountAutoStatus } from './components/auto-status.js';` (line 5); the `registerScreen('/auto', …)` route (line 25); the `mountAutoStatus(...)` call (line 85); the `pollAutoStateForever()` function + `AUTO_STATE_POLL_MS` const (lines 137–174); and the `pollAutoStateForever();` call inside `boot()` (line 99).

- [ ] **Step 2: Unwire `sidebar.js`**

Remove: `import { isAutoRunning } from '../lib/auto-state.js';` (line 6); the entire `Structural` nav section containing the `auto_mode` link (lines 17–18); the `const unsubAutoState = store.subscribe('autoState', …)` block (lines 124–131); and `if (typeof unsubAutoState === 'function') unsubAutoState();` in teardown (line 221).

- [ ] **Step 3: Unwire `kanban.js`**

Remove: the 3-name import from `../components/auto-mode-strip.js` (lines 6–8); the `strip = renderAutoModeStrip({...})` + `page.appendChild(strip)` block (lines 57–62); the `autoState: store.getAutoState()` property passed to `renderCard` in `paint()` (line 403); the `store.subscribe('autoState', …)` block (lines 469–476); and `destroyAutoModeStrip(strip);` in cleanup (line 491).

- [ ] **Step 4: Unwire `task-detail-document.js`, `card.js`, `desk.js`, `topbar.js`**

`task-detail-document.js`: remove `renderAutoBanner` (lines 212–221) and its call `children.push(renderAutoBanner(task));` (line 131).

`card.js`: remove imports `isAutoRunning` (line 17) and `renderAutoModeLiveBlock` (line 18); the `const isAuto = …` + `if (isAuto) card.classList.add('auto');` (lines 32–33); both `if (isAuto) appendLiveBlock(card, autoState);` calls (lines 102, 228); the `appendLiveBlock` helper (lines 240–243); and the `autoState = null` parameter from `renderCard`'s signature (line 25).

`desk.js`: remove `import { createAutoModeStrip } from '../components/auto-mode-strip.js';` (line 3); the `autoSlot`/`strip` block (lines 25–27); and change `root.replaceChildren(autoSlot, boardEl, bandEl);` → `root.replaceChildren(boardEl, bandEl);` (line 31).

`lib/topbar.js`: remove the `.auto-status-pill` preservation lines inside `claimTopbar()` (lines 9–11: the `const pill = root.querySelector('.auto-status-pill');` and `if (pill) root.appendChild(pill);`). Keep `claimTopbar()` itself.

- [ ] **Step 5: Unwire `api.js` and `store.js`**

`api.js`: remove the `// ---- Auto Mode (Plan 6)` section with `autoListSessions`, `autoSession`, `autoPause`, `autoStop`, `autoEvents`, `autoBudget` (lines 264–310); the `async getAutoState()` method (lines 151–155); and the `api.autoState` entry (line 99).

`store.js`: remove `autoState`/`activeAutoSessionId` state fields (lines 11–12); the `getAutoState`/`getActiveAutoSession` getters (lines 52–53); the `setAutoState`/`setActiveAutoSession` setters (lines 61–62); the three named exports `setAutoState`/`setActiveAutoSession`/`getActiveAutoSession` (lines 104–114); and the stale comment on line 3.

- [ ] **Step 6: Delete the 4 non-reusable wrappers**

```bash
git rm plugins/taskmaster/viewer/js/components/auto-status.js \
       plugins/taskmaster/viewer/js/components/auto-mode-strip.js \
       plugins/taskmaster/viewer/js/components/sessions-strip.js \
       plugins/taskmaster/viewer/js/lib/auto-state.js
```

- [ ] **Step 7: Move the 6 reusable components to `_dormant/`**

```bash
mkdir -p plugins/taskmaster/viewer/js/_dormant
git mv plugins/taskmaster/viewer/js/components/quest-spine.js        plugins/taskmaster/viewer/js/_dormant/quest-spine.js
git mv plugins/taskmaster/viewer/js/components/auto-spine-layout.js  plugins/taskmaster/viewer/js/_dormant/auto-spine-layout.js
git mv plugins/taskmaster/viewer/js/components/flight-log.js         plugins/taskmaster/viewer/js/_dormant/flight-log.js
git mv plugins/taskmaster/viewer/js/components/auto-side-panels.js   plugins/taskmaster/viewer/js/_dormant/auto-side-panels.js
git mv plugins/taskmaster/viewer/js/components/auto-mode-live-block.js plugins/taskmaster/viewer/js/_dormant/auto-mode-live-block.js
git mv plugins/taskmaster/viewer/js/screens/auto-mode.js            plugins/taskmaster/viewer/js/_dormant/auto-mode.js
```

- [ ] **Step 8: Write `_dormant/README.md`**

Create `viewer/js/_dormant/README.md`:
```markdown
# Dormant viewer components (archived from auto mode)

These are presentational components from the removed auto-mode screen, kept for a
possible future goals dashboard. **Nothing imports them today.** They reference
removed modules and MUST be rewired before reuse:

- `auto-mode.js` — imports six deleted `api.js` auto functions (`autoListSessions`,
  `autoEvents`, `autoSession`, `autoBudget`, `autoPause`, `autoStop`) and two removed
  store keys (`getAutoState`, `setActiveAutoSession`); also imported the deleted
  `sessions-strip.js`. Relative imports to the components below need depth fix-ups.
- `quest-spine.js` → `auto-spine-layout.js` (co-located here; import resolves).
- `auto-side-panels.js` → `../components/budget-meter.js` (path now broken).
- `auto-mode-live-block.js` → `../lib/time.js` (path now broken).
- `flight-log.js`, `auto-spine-layout.js` — pure render/data, no external imports.

Build/test globs do not pick up `_dormant/` (unit glob is `tests/unit/*.test.js`;
Playwright `testDir` is `tests/`). Do not add imports from live code into this dir.
```

- [ ] **Step 9: Delete the coupled unit test**

`tests/unit/auto-spine-layout.test.js` imports `../../js/components/auto-spine-layout.js`, which has moved. Delete it (the component is dormant, not live):
```bash
git rm plugins/taskmaster/viewer/tests/unit/auto-spine-layout.test.js
```

- [ ] **Step 10: Run viewer unit tests**

Run (from `plugins/taskmaster/viewer/`): `npm run test:unit`
Expected: PASS — no unresolved imports. (`stepper-line.test.js` still passes here; its CSS dependency is removed in Task 5.)

- [ ] **Step 11: Commit**

```bash
git add -A plugins/taskmaster/viewer/js/ plugins/taskmaster/viewer/tests/
git commit -m "refactor(taskmaster): unwire auto-mode viewer JS, archive reusable components to _dormant (remove-auto-mode-001)"
```

---

## Task 5: Viewer CSS + HTML + prefs + viewer specs

Remove auto CSS, the stylesheet link, the on-disk prefs key, and the auto viewer tests.

**Files:**
- Delete: `viewer/css/screens/auto-mode.css`, `viewer/tests/unit/stepper-line.test.js`, `viewer/tests/auto-mode.spec.js`
- Modify: `viewer/css/shell.css`, `viewer/css/screens/kanban.css`, `viewer/css/screens/task-detail.css`, `viewer/css/screens/desk.css`, `viewer/index.html`, `viewer.json`, `viewer/tests/smoke.spec.js`

- [ ] **Step 1: Delete the auto stylesheet + its coupled unit test**

```bash
git rm plugins/taskmaster/viewer/css/screens/auto-mode.css
git rm plugins/taskmaster/viewer/tests/unit/stepper-line.test.js
```
(`stepper-line.test.js` reads `../../css/screens/auto-mode.css` from disk; it tests deleted CSS.)

- [ ] **Step 2: Trim auto rules from shared CSS**

`css/shell.css`: remove `.sidebar-footer.auto-running .pulse {…}` (line 131); remove `.auto-page,` from the two scroll-region selector groups (lines 335, 355); remove the entire `/* Header auto-status pill */` block (lines 374–410).

`css/screens/kanban.css`: remove `--card-bg-auto-grad` from `:root` (line 8); the `.card-task.auto {…}` rules (lines 88–92); the `/* PER-CARD AUTO-MODE LIVE BLOCK */` section (lines ~298–335); the `/* AUTO-MODE STRIP */` section (lines ~341–415); and the mobile `/* Auto-mode strip: compact on mobile */` block (line ~1027).

`css/screens/task-detail.css`: remove the `/* auto-mode banner */` block (lines 182–187) and the mobile `.td-auto-banner .td-auto-bar {…}` rule (lines 377–378).

`css/screens/desk.css`: remove the `/* Auto-mode strip slot */` comment + `.dk-auto:empty {…}` (lines 11–12).

(`css/tokens.css` needs no rule change — only a harmless comment mentions Auto Mode; optionally trim it.)

- [ ] **Step 3: Remove the stylesheet link from `index.html`**

Delete line 24: `<link rel="stylesheet" href="css/screens/auto-mode.css">`. Keep `#topbar-actions` (line 41) — it hosts other topbar controls.

- [ ] **Step 4: Remove the `auto_mode` prefs key from `viewer.json`**

Delete the `screens.auto_mode` block (hint: lines 23–27, the `"view"/"helper_dismissed"/"active_sid"` object). Keep the rest of `screens`.

- [ ] **Step 5: Remove auto viewer specs**

```bash
git rm plugins/taskmaster/viewer/tests/auto-mode.spec.js
```
In `viewer/tests/smoke.spec.js`: remove the `route-auto-resolves` smoke case.

- [ ] **Step 6: Run viewer unit tests**

Run (from `plugins/taskmaster/viewer/`): `npm run test:unit`
Expected: PASS — `stepper-line.test.js` gone; no test reads the deleted CSS.

- [ ] **Step 7: Run the trustworthy viewer specs + check for 404s**

Run (from `plugins/taskmaster/viewer/`): `npm run test:e2e -- smoke.spec.js`
Expected: PASS for the smoke spec; no console 404 from a stray `/api/auto/state` poller. (Per ISS-025 the full e2e suite is known-red on master — only assert the smoke + route-mocked subset here.)

- [ ] **Step 8: Commit**

```bash
git add -A plugins/taskmaster/viewer/
git commit -m "refactor(taskmaster): remove auto-mode viewer CSS/markup/prefs + specs (remove-auto-mode-001)"
```

---

## Task 6: Docs — supersede goal docs + CLAUDE.md note

**Files:**
- Modify: `docs/superpowers/specs/2026-05-10-auto-brainstorm-goal-design.md`, `docs/superpowers/plans/2026-05-10-auto-brainstorm-goal.md`, `CLAUDE.md` (repo root)

- [ ] **Step 1: Prepend the superseded header to both goal docs**

At the top of each of `docs/superpowers/specs/2026-05-10-auto-brainstorm-goal-design.md` and `docs/superpowers/plans/2026-05-10-auto-brainstorm-goal.md`, insert:
```markdown
> ⚠ **Superseded (2026-06-11).** This design builds on taskmaster's auto-mode state machine,
> which has been removed (see docs/superpowers/specs/2026-06-11-remove-auto-mode-design.md).
> Autonomous execution now routes through goals + ultracode. The substrate assumed below no
> longer exists; treat this as historical until redesigned.
```

- [ ] **Step 2: Note the supersession in `CLAUDE.md`**

Find the `agents/goal-judge.md` "pending" line (in the "Agents" orientation bullet) and append a one-line note: that the goal design is superseded pending a goals+ultracode redesign.

- [ ] **Step 3: Commit (force-add — specs/plans dir is gitignored-but-tracked)**

```bash
git add -f docs/superpowers/specs/2026-05-10-auto-brainstorm-goal-design.md docs/superpowers/plans/2026-05-10-auto-brainstorm-goal.md
git add CLAUDE.md
git commit -m "docs(taskmaster): supersede auto-brainstorm goal docs after auto-mode removal (remove-auto-mode-001)"
```

---

## Task 7: Versioning — bump to 3.17.0

Three parts move together (repo protocol). Minor by explicit decision; honesty conditions baked in.

**Files:**
- Modify: `plugins/taskmaster/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `plugins/taskmaster/CHANGELOG.md`

- [ ] **Step 1: Bump `plugin.json`**

`plugins/taskmaster/.claude-plugin/plugin.json`: `"version": "3.16.1"` → `"version": "3.17.0"`.

- [ ] **Step 2: Bump `marketplace.json` + scrub auto from the description**

`.claude-plugin/marketplace.json` (taskmaster entry): version → `"3.17.0"`, and edit the `description` string to remove the clause advertising `auto-task / auto-epic / auto-phase state machines` (condition of the minor decision).

- [ ] **Step 3: Add the CHANGELOG section**

In `plugins/taskmaster/CHANGELOG.md`, under `## [Unreleased]` add a `## 3.17.0 — Remove auto mode (2026-06-14)` section. It must state the removed surface (6 MCP tools, 7 HTTP endpoints, 3 driver skills, viewer auto screen) and the redirect to ultracode, and explicitly note the **minor-over-removed-surface** decision (auto treated as effectively internal/unshipped).

- [ ] **Step 4: Run the version-bump check**

Run (from repo root): `python scripts/check_plugin_version_bump.py --base origin/master`
Expected: exit 0 — plugin.json/marketplace.json in sync; CHANGELOG entry present.

- [ ] **Step 5: Run the full Python suite once more**

Run (from `plugins/taskmaster/`): `python -m pytest tests/ -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add plugins/taskmaster/.claude-plugin/plugin.json .claude-plugin/marketplace.json plugins/taskmaster/CHANGELOG.md
git commit -m "chore(taskmaster): bump to 3.17.0 — remove auto mode (remove-auto-mode-001)"
```

---

## Task 8: Backlog hygiene — moot / orphaned tasks

Auto removal invalidates existing backlog work. Done via taskmaster MCP tools (not code) so the dashboard reflects reality.

- [ ] **Step 1: Archive now-impossible tasks**

`backlog_archive_task("tm-audit-004")` (auto state-machine completion bug — the machine is gone) and `backlog_archive_task("v3-polish-006")` (slim auto-mode header — surface deleted).

- [ ] **Step 2: Close the in-review auto task**

`v3-polish-028` (auto-mode strip copy) is in-review against a deleted surface. Archive it with a note that the auto strip was removed wholesale (`backlog_archive_task("v3-polish-028")`).

- [ ] **Step 3: Rescope the auto-anchored tasks**

For `v3-teams-006`, `tm-audit-009`, `tm-audit-010`, `tm-audit-018`, `agentic-os-001`: use `backlog_update_task(..., anchors=...)` to drop the `skills/auto-*` anchors and any auto-only scope wording, leaving the non-auto remainder intact.

- [ ] **Step 4: Verify the dashboard**

`backlog_status()` — confirm no in-review/todo task still references the removed auto surface.

- [ ] **Step 5: Commit the backlog changes**

```bash
git add -A .taskmaster/
git commit -m "chore(taskmaster): archive/rescope auto-mode-moot backlog tasks (remove-auto-mode-001)"
```

---

## Final verification (before review-gate)

- [ ] Full Python suite green: `python -m pytest tests/ -q` (from `plugins/taskmaster/`).
- [ ] Viewer unit green: `npm run test:unit` (from `viewer/`).
- [ ] Smoke spec green + no `/api/auto/*` 404: `npm run test:e2e -- smoke.spec.js`.
- [ ] No live import resolves to a deleted module: `grep -rn "auto-status\|auto-mode-strip\|sessions-strip\|lib/auto-state" plugins/taskmaster/viewer/js` returns only `_dormant/` self-references (documented).
- [ ] No stray backend reference: `grep -rn "backlog_auto_\|AUTO_SESSIONS_DIR\|read_auto_state" plugins/taskmaster/*.py` returns nothing.
- [ ] Version check exit 0: `python scripts/check_plugin_version_bump.py --base origin/master`.
- [ ] Then run `taskmaster:review-gate remove-auto-mode-001`.

---

## Self-Review (against spec)

**Spec coverage:** §1 Backend → Task 2. §2 Skills + redirect → Task 3. §3 Viewer (JS + the added CSS/index.html) → Tasks 4–5. §4 Docs/tests/versioning → tests folded into Tasks 2/3/4/5, docs → Task 6, versioning → Task 7. §5 Backlog hygiene → Task 8. Negative guard (§ Testing strategy) → Task 1. Edge cases (in-flight collision, persisted prefs, symbol-not-line, `_dormant` glob exclusion) → addressed in conventions + Task 5 Step 4 + Task 4 Step 8 / final verification.

**Beyond-spec targets folded in (from exploration):** the `VIEWER_PREFS_DEFAULTS` island inside the auto block (Task 2 Step 1); `card.js`/`desk.js`/`topbar.js` (Task 4 Step 4); the hardcoded `SKILL_BUDGETS` + `disambiguation.md` (Task 3); the two coupled unit tests `auto-spine-layout.test.js`/`stepper-line.test.js` (Tasks 4/5); `test_full_v3_surface_count` floor (Task 2 Step 5).

**Placeholder scan:** none — every edit names exact file + symbol + quoted target.

**Type/name consistency:** tool names, symbol names, and file paths match the three exploration manifests verbatim.
