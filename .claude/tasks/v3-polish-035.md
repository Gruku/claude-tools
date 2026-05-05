---
notes: 'Discovered 2026-05-05 while running the full pytest suite as part of v3-edit-009
  (task write API). 3 tests fail in `test_server_task_detail.py`. The Task 9 subagent
  confirmed these are pre-existing (`git stash` on Task 9''s edits → same 3 failures).
  They are NOT caused by the v3-edit work and don''t block Phase A.


  Action: Run `pytest plugins/taskmaster/tests/test_server_task_detail.py -v` and
  triage the 3 failing test names. Likely related to v2 vs v3 fixture data shape mismatch
  or to the v3-polish-029/030 patches (configurable backlog_path) changing what the
  test fixtures see.


  Surface area: server''s `/api/task/<id>` and `/api/task/<id>/related` endpoints.
  The fixes for those landed in commit `df366a4` and may have broken assumptions in
  the older test file. Worth checking if the test fixtures still set up the paths
  the loaders now expect.


  Not blocking — 359/362 tests pass and all NEW v3-edit tests pass cleanly. Park here,
  fix during pre-release polish.'
id: v3-polish-035
title: 3 pre-existing failures in test_server_task_detail.py
---
