---
notes: 'Superseded by v3-edit-009 — auto-stamping logic is folded into Phase A''s
  `update_task` primitive. Will close when v3-edit-009 lands.


  Original notes:

  User-reported: Task Detail''s dates row shows `Started —` and `Completed —` for
  tasks that were definitely started and finished (e.g. v3-skills-002 "in-review",
  v3-polish-027 "in-review"). Only `Created` is reliably populated. Server-side: `backlog_update_task`
  (and/or pick-task / end-session paths) should auto-stamp `started` on the first
  transition into `in-progress`, and `completed` on transition into `done`. Don''t
  overwrite if already set. Discovered 2026-05-04 while dogfooding the v3 viewer.'
id: v3-polish-033
title: Task transitions don't capture `started`/`completed` timestamps — Task Detail
  dates row shows "—"
---
