# Remove Auto Mode → Hand Off to Goals + Ultracode

**Date:** 2026-06-11 (spec-reviewed & revised 2026-06-14)
**Status:** Spec-reviewed — revised to clear spec-review findings; ready for writing-plans
**Plugin:** taskmaster
**Version target:** 3.16.1 → 3.17.0 — **minor by explicit decision** (auto treated as effectively
internal/unshipped), consciously overriding the repo rule "removed surface → major". **Condition of
that decision:** `marketplace.json`'s `description` string (which today advertises the auto state
machines) MUST be scrubbed of auto, and the CHANGELOG MUST state both the removed surface and the
minor-over-removed-surface call, so the "unshipped" framing stays honest.

## Problem

Taskmaster ships a bespoke "auto mode" subsystem: a custom state machine that drives
tasks/epics/phases through lane-specific lifecycle stages, with its own MCP tools, HTTP
endpoints, session/event storage, three driver skills, and a full viewer screen.

Autonomous epic/task completion now routes through a different path entirely: the user
**defines a goal** and **runs it through ultracode** (the multi-agent `Workflow`
orchestration). The in-plugin auto state machine is therefore redundant — it duplicates,
more narrowly, what ultracode does generally. Maintaining it costs surface area, tokens,
test weight, and viewer complexity for no remaining benefit.

**Goal:** Remove auto mode from taskmaster completely. Replace the user-facing entry with a
*thin redirect* — when someone expresses auto/autopilot intent, the taskmaster router
suggests the goals + ultracode path instead of running an in-plugin machine.

## Non-goals

- Building or specifying the goals/ultracode path itself. That path exists outside
  taskmaster; this work only hands off to it.
- Redesigning the draft goal/auto-brainstorm spec onto the new substrate. Those docs are
  marked superseded, not rewritten (a future effort owns that).
- Any change to non-auto taskmaster surfaces (gates, lanes as a task field, merge ladder,
  handovers, lessons, etc.) beyond removing their auto-mode references.

## Decisions (from brainstorming)

| Decision | Choice |
|---|---|
| New path the redirect points at | Ultracode workflows; taskmaster hands off, does not own it |
| Fate of goal/auto-brainstorm spec + plan | Keep on disk, add a "superseded" header |
| Backend removal depth | Full — state machine, MCP tools, HTTP endpoints, skills, tests |
| Viewer | Remove live surfaces; preserve presentational components dormant |
| Stub skills for `/auto-*` | None — router copy only; `/auto-*` slash commands stop resolving |
| Version bump | Minor → 3.17.0 (auto treated as internal/unshipped) |
| Dormant component preservation | Move to `viewer/js/_dormant/` + a short README |

## Architecture of the change

The change is a **subtractive refactor** plus one **small additive redirect**. There is no
new runtime component. The pieces:

1. **Backend removal** — delete the auto state machine and its MCP/HTTP surface.
2. **Skill removal + redirect** — delete the three driver skills; add a router redirect row.
3. **Viewer teardown + archive** — remove live auto surfaces; relocate reusable presentational
   components to `_dormant/`.
4. **Docs/tests/versioning** — supersede goal docs, delete/adjust tests, bump version.

### 1. Backend removal

**`plugins/taskmaster/taskmaster_v3.py`** — delete the auto state-machine block (~lines
4132–4780):

- Constants: `AUTO_MODES`, `AUTO_STAGES`, `AUTO_STAGE_GATE`, `_LANE_STAGE_SEQUENCE`,
  `AUTO_TASK_STATUSES`, `AUTO_FAIL_REASONS`, `AUTO_MODELS`, `AUTO_DIR`, `AUTO_SESSIONS_DIR`,
  `AUTO_HOOKS_LOG`, `AUTO_LEGACY_STATE`.
- Functions: `auto_stages_for_lane`, `init_auto_run`, `read_auto_state`, `write_auto_state`,
  `clear_auto_state`, `advance_stage`, `next_planned_stage`, `complete_current_task`,
  `auto_run_summary`, `compute_budget`, `read_hook_events`, `append_auto_event_bp`,
  `read_auto_events`, `append_auto_event`, `_migrate_legacy_state_for_bp`,
  `migrate_auto_state_to_sessions`, and any `list_auto_sessions` / `load_auto_session` /
  `save_auto_session` helpers in the same block.
- Remove the `"auto_mode": {"view": "A"}` entry from `VIEWER_PREFS_DEFAULTS.screens`.

**`plugins/taskmaster/backlog_server.py`** — delete:

- The 6 registered tools: `backlog_auto_start`, `backlog_auto_status`, `backlog_auto_advance`,
  `backlog_auto_complete_task`, `backlog_auto_finish`, `backlog_auto_abort`.
- The 5 culled (non-`@mcp.tool`) helpers: `auto_state_get`, `auto_pause`, `auto_stop`,
  `auto_history`, `auto_event_log`.
- `_load_auto_state`.
- The 7 HTTP handlers: `GET /api/auto/state`, `/api/auto/sessions`, `/api/auto/sessions/<sid>`,
  `/api/auto/events`, `/api/auto/budget/<sid>`, `POST /api/auto/pause`, `POST /api/auto/stop`.
- The `_init_storage` `AUTO_SESSIONS_DIR.mkdir(...)` + migration call.
- The auto-state import block and the three `.get("auto_model", "sonnet")` reads.

**On-disk state** (`.taskmaster/auto/`): no migration or cleanup code is written. Existing
project `.taskmaster/auto/` directories simply become orphaned and ignored. (They are
per-project user data, not shipped by the plugin.)

### 2. Skill removal + router redirect

**Delete entirely:** `plugins/taskmaster/skills/auto-task/`, `skills/auto-epic/`,
`skills/auto-phase/` (including all `references/` files). This removes the `/auto-task`,
`/auto-epic`, `/auto-phase` slash commands.

**Edit:**

- `skills/end-session/SKILL.md` — remove the `references/auto-mode.md` reference (line ~87)
  and the auto-status-check behavior; delete `skills/end-session/references/auto-mode.md`.
- `skills/pick-task/references/v3-context-loading.md` — remove the "called from auto mode"
  section.
- `skills/taskmaster/SKILL.md` — remove "auto-mode" / auto references from the `description`
  field and the body's intent table.
- `skills/taskmaster/references/routing-table.md` — replace the three auto routing rows
  (~lines 51–53) with **one redirect row**:

  | Intent Signal | Route To |
  |---|---|
  | "auto this task", "autopilot", "auto-epic X", "auto T-001" | Redirect: auto mode removed — suggest **ultracode** (Workflow orchestration) |

**Also triage (grep-confirmed auto references beyond the files above):**

- `skills/migrate-v3/SKILL.md` + `references/v2-vs-v3.md` + `references/migration-steps.md` — remove
  the "turn on auto-mode" trigger phrase and any auto-mode migration step; auto is no longer a v3
  opt-in feature.
- `skills/handover/references/session-kinds.md` — drop the auto session-kind entry.
- `skills/init-taskmaster/SKILL.md` + `references/analysis-mode.md` — remove auto-mode mentions.
- **Not a target:** `skills/decision/references/auto-resolution.md` — "auto-resolution" is decision
  auto-resolve, unrelated to auto mode. Left untouched (false positive).

**Redirect copy** (the "thin suggestion"), emitted by the router when auto/autopilot intent
is detected:

> Auto mode has been removed from taskmaster. To drive a task or epic autonomously, run it
> through **ultracode** — the multi-agent `Workflow` orchestration — instead of an in-plugin
> state machine. (A dedicated taskmaster goals surface is not yet built; ultracode is the
> supported autonomous path today.)

The redirect deliberately points only at **ultracode/`Workflow`, which exists today**. It does not
promise a taskmaster "/goal" surface — that path is still planned (the Auto-Brainstorm + /goal epic
is unbuilt, `goal-judge` agent pending). Accepted capability gap: ultracode is more general but is
not lane/gate-aware the way auto's per-task lifecycle driving was; the brainstorm decision accepts
this loss.

No stub skills are kept. `/auto-*` as literal slash commands stop resolving — that is the
intended outcome.

### 3. Viewer teardown + dormant archive

**Remove live surfaces** (these reference state/endpoints that no longer exist):

- `viewer/js/main.js` — drop the `registerScreen('/auto', ...)` route, the `mountAutoStatus`
  import + mount, and the `/api/auto/state` poller.
- `viewer/js/components/sidebar.js` — remove the `auto_mode` nav link + its live-dot +
  `autoState` subscription.
- `viewer/js/screens/kanban.js` — remove the auto-mode strip mount and the `autoState`
  subscription / board pass-through.
- `viewer/js/components/task-detail-document.js` — remove `renderAutoBanner` and its call.
- `viewer/js/api.js` — remove `autoListSessions`, `autoSession`, `autoPause`, `autoStop`,
  `autoEvents`, `autoBudget`.
- `viewer/js/store.js` — remove the `autoState` key, `getAutoState`, `setAutoState`,
  `setActiveAutoSession`.
- `viewer.json` + `VIEWER_PREFS_DEFAULTS` — remove the `auto_mode` screen-prefs entry.
- Delete the always-on/active-only wrappers that are not reusable: `components/auto-status.js`
  (header pill), `components/auto-mode-strip.js` (kanban strip), `components/sessions-strip.js`
  (parallel-session tabs), `lib/auto-state.js` (`isAutoRunning` predicate). These are tied to
  the removed live state, not reusable presentation.

**Remove CSS + markup** (grep-confirmed; absent from the original draft):

- Delete `viewer/css/screens/auto-mode.css` entirely.
- Remove auto-mode rules from `viewer/css/shell.css`, `css/screens/kanban.css`,
  `css/screens/task-detail.css`, `css/screens/desk.css`, and the auto token(s) in `css/tokens.css`.
- `viewer/index.html` — remove the `auto-mode.css` `<link>` and any auto nav/markup node.

**Preserve dormant** — move to `viewer/js/_dormant/` with a `README.md`:

- `quest-spine.js`
- `auto-spine-layout.js`
- `flight-log.js`
- `auto-side-panels.js`
- `auto-mode-live-block.js`
- `screens/auto-mode.js` (kept as a reference assembly of the above)

`_dormant/README.md` states: these are archived presentational components from the removed
auto-mode screen, kept for a possible future goals dashboard; they reference removed
`api.js`/`store.js`/`lib` modules and **must be rewired** before reuse; nothing imports them
today.

### 4. Docs, tests, versioning

**Goal docs — supersede (do not delete):** prepend a header to both
`docs/superpowers/specs/2026-05-10-auto-brainstorm-goal-design.md` and
`docs/superpowers/plans/2026-05-10-auto-brainstorm-goal.md`:

> ⚠ **Superseded (2026-06-11).** This design builds on taskmaster's auto-mode state machine,
> which has been removed. Autonomous execution now routes through goals + ultracode. The
> substrate assumed below no longer exists; treat this as historical until redesigned.

`CLAUDE.md` — the `agents/goal-judge.md` "pending" line gets a one-line note that the goal
design is superseded pending a goals+ultracode redesign.

**Tests — delete:**

- `tests/test_server_auto_mode.py`
- `tests/test_server_auto_state.py`
- `tests/test_auto_lane_aware.py`
- `tests/test_auto_lane_driver.py`
- `tests/test_auto_epic_skill_lint.py`
- `tests/test_auto_phase_skill_lint.py`
- `tests/test_auto_task_skill_lint.py`
- `viewer/tests/auto-mode.spec.js`

**Tests — edit:**

- `tests/test_mcp_v3_exposure.py` — remove the parametrized `backlog_auto_*` registration
  assertions (~lines 156–161).
- `tests/test_dead_tool_cull.py` — remove `auto_state_get`, `auto_pause`, `auto_stop`,
  `auto_history`, `auto_event_log` from the culled list (the functions no longer exist, so
  asserting they are "culled but present" is wrong).
- `viewer/tests/smoke.spec.js` — remove the `route-auto-resolves` smoke case.

**Tests — add (negative guard):** a small test asserting **no** `backlog_auto_*` tool is
registered in the MCP surface and `.taskmaster/auto` is not created by `_init_storage`. This
prevents silent re-introduction.

**Versioning (3 parts move together, per repo protocol):**

- `plugins/taskmaster/.claude-plugin/plugin.json` → `3.17.0`
- `.claude-plugin/marketplace.json` → taskmaster `3.17.0` **and** edit the `description` string to
  remove the "auto-task / auto-epic / auto-phase state machines" advertising (a condition of the
  minor-bump decision — see header).
- `plugins/taskmaster/CHANGELOG.md` → new `## 3.17.0` section. Minor (not major) by explicit
  decision: auto mode is treated as effectively internal/unshipped. The CHANGELOG entry must
  state the removed surface (6 MCP tools, 7 endpoints, 3 skills) and the redirect, so the
  delta is honest even though the bump is minor.

Run `python scripts/check_plugin_version_bump.py --base origin/master` before opening a PR.

### 5. Backlog hygiene — moot / orphaned tasks

Removing auto invalidates existing backlog work. As part of this task:

- **Archive (now impossible / irrelevant):** `tm-audit-004` (auto state-machine completion bug),
  `v3-polish-006` (slim auto-mode header).
- **Pull back + close:** `v3-polish-028` (auto-mode strip copy) — currently *in-review* against a
  surface being deleted.
- **Rescope (auto-skill anchors shrink):** `v3-teams-006`, `tm-audit-009`, `tm-audit-010`,
  `tm-audit-018`, `agentic-os-001` — drop the `skills/auto-*` anchors / auto scope from each.

## Error handling / edge cases

- **In-flight collision on core files:** `v3-release-010` and `project-manifest-001` are in-progress
  and edit `taskmaster_v3.py`; this task deletes ~650 lines from the same file. Sequence this task
  *after* those merge (or coordinate) to avoid a large conflict. Relocate every deletion by **symbol**,
  not the line numbers quoted above (they drift as siblings land).
- **Persisted viewer prefs:** real projects' `viewer.json` may still carry an `auto_mode` screen key
  after the default is dropped. Confirm the prefs loader ignores unknown screen keys (no crash on a
  stale key), not only that the default is removed.
- **Hook events:** `AUTO_HOOKS_LOG` implies auto event logging; grep found no `hooks/` references, so
  no registered plugin hook appears to write it — verify during implementation before assuming clean.

- **Orphaned `.taskmaster/auto/` dirs** in real projects: left as-is, ignored. No reader code
  remains to trip on them. Acceptable — they are user data, not plugin-shipped.
- **Dangling imports in `_dormant/`:** intentional and documented in the README. Nothing
  imports `_dormant/`, so no runtime breakage; lint/bundler globs must exclude `_dormant/` if
  they would otherwise flag it (verify the viewer build/test globs during implementation).
- **Router muscle memory:** users typing `/auto-epic` get "unknown command." The redirect row
  catches natural-language auto/autopilot intent through `taskmaster:taskmaster`, which is the
  supported entry. Accepted tradeoff (router-copy-only decision).
- **`skill-lint` tests** that iterate all skills must not expect the three deleted skills.
  Verify the skill-lint harness discovers skills dynamically (it should, post-deletion) rather
  than from a hardcoded list.

## Testing strategy

- **Removal correctness:** the existing Python suite (minus deleted auto tests) must stay
  green. `test_mcp_v3_exposure.py` and `test_dead_tool_cull.py` pass after edits.
- **Negative guard:** new test asserts auto tools are gone and no auto storage is created.
- **Viewer:** `viewer/tests/` suite (the trustworthy unit + route-mocked subset — note the
  e2e suite is known-red on master per ISS-025) must pass with auto routes/components removed;
  no console 404s from a stray poller. Confirm no remaining import resolves to a deleted
  module.
- **Version guard:** `check_plugin_version_bump.py` exits 0.

## Build sequence (high level — detailed plan follows in writing-plans)

1. Backend: remove state machine (`taskmaster_v3.py`) + tools/endpoints (`backlog_server.py`).
2. Tests: delete/edit Python auto tests; add negative guard; get suite green.
3. Skills: delete three driver skills; edit end-session/pick-task/taskmaster + routing-table redirect;
   triage migrate-v3 / handover / init-taskmaster auto references.
4. Viewer: unwire live JS surfaces; delete/trim auto CSS + `index.html` link/markup; move dormant
   components + README; fix prefs.
5. Viewer tests: delete/edit specs; confirm green + no 404s.
6. Docs: supersede goal docs; note in CLAUDE.md.
7. Versioning: bump 3 parts to 3.17.0; scrub auto from `marketplace.json` description; CHANGELOG
   states removed surface + justifies the minor; run check script.
8. Backlog hygiene: archive / close / rescope moot tasks (see §5).

Each step is independently committable and leaves the suite green.
