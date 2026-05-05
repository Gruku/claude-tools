---
notes: 'Plan Task 9 (spec v3-edit-004 — write API). The keystone. `update_task(task_id,
  patch, backlog_path=None)`, `create_task(payload)`, `archive_task(id)` in `taskmaster_v3.py`
  — shared between MCP write tools and HTTP API. Auto-stamps `started` on first transition
  into in-progress and `completed` on first transition into done; never overwrites.
  Folds in v3-polish-033 (timestamp capture). HTTP wrappers in `backlog_server.py`:
  POST/PATCH/PUT/POST-archive. Per-file `with_file_lock`. Most complex task — budget
  extra review.'
docs:
  plan: docs/superpowers/plans/2026-05-04-v3-edit-phase-a.md
  spec: docs/superpowers/specs/2026-05-04-v3-edit-in-ui-design.md
id: v3-edit-009
title: Task write API + v3 primitives
---
