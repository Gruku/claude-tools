---
notes: 'Server <-> v3 viewer contract mismatch.


  `backlog_server._serve_json` (line 4651) returns the raw YAML, which keeps tasks
  nested under `epics[].tasks[]`. The v3 viewer''s kanban (`kanban.js:187`), table
  (`table.js:260`), and board-surface (`board-surface.js:63`) only read `backlog.tasks`
  (flat top-level array). Result: every list/board screen renders 0 tasks even though
  `/api/backlog` carries all of them.


  `load_v3` does NOT flatten either — it preserves the v2 nested shape under epics.
  So migrating to v3 schema does not fix this.


  Repro: open the v3 viewer (use_v3=true) on any backlog with epics[].tasks. Kanban
  shows "0 tasks · 0 visible" with all status columns empty.


  Fix landed in this worktree (hot-patch on feature/taskmaster-v3): in `_serve_json`,
  if `data["tasks"]` isn''t a list, derive it by flattening `epics[].tasks` and stamping
  each task with its parent epic id (so `t.epic` is always present for filtering).
  ~6 lines, no client-side changes.


  Validate: curl `/api/backlog | jq ''.tasks | length''` should match the sum of `epics[].tasks`.
  Then reload the v3 kanban — task counts should populate, all status columns render
  cards, epic chip counts non-zero.


  Discovered while dogfooding the v3 viewer for this feature branch on 2026-05-04.'
id: v3-polish-029
title: v3 viewer reads empty task list — `/api/backlog` doesn't expose flat top-level
  `tasks`
---
