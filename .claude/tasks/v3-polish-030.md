---
notes: '`/api/task/<id>` and `/api/task/<id>/related` always 404 in projects whose
  backlog isn''t at `./backlog.yaml` with v3-flat tasks under `.taskmaster/`.


  Three bugs in `_load_task_full` and `_load_related_for_task` (`backlog_server.py`
  ~4152 / ~4212):


  1. Hardcoded `Path("backlog.yaml")` — ignores `_resolve_paths()` / `.claude/taskmaster.json`.
  claude-tools'' own backlog at `.claude/backlog.yaml` is invisible.

  2. Reads `backlog.get("tasks")` flat — same v3-slim-index assumption as `_serve_json`
  (covered by v3-polish-029). v2 nested `epics[].tasks[]` reads as empty.

  3. Sidecar dirs hardcoded to `Path(".taskmaster") / {tasks,lessons,handovers,issues}`.
  claude-tools keeps these under `.claude/`, so per-task markdown bodies and related-entity
  payloads always come back empty.


  Repro: open the v3 viewer, click any task card → "Could not load <id>: task <id>
  not found".


  Hot-patch landed on feature/taskmaster-v3:

  - Use `_backlog_path()` (already resolves via `.claude/taskmaster.json`).

  - Same epics-flatten fallback as in v3-polish-029.

  - Derive `sidecar_root = backlog_path.parent` and resolve `lessons/`, `handovers/`,
  `issues/`, and `tasks/<id>.md` under it.


  Validate: `curl /api/task/v3-skills-004` → 200 with title/body. Click any kanban
  card in the v3 viewer → task detail screen renders. Related panel populates lessons/handovers/issues
  for tasks that have anchor matches.


  Discovered 2026-05-04 while dogfooding v3 viewer right after fixing v3-polish-029.'
id: v3-polish-030
title: Task-detail loaders ignore configured backlog_path + assume v3 flat-tasks +
  .taskmaster sidecar dirs
---
