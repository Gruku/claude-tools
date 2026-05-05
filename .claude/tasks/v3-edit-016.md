---
notes: 'The Phase A plan called for an `edit-task.spec.js` Playwright E2E covering
  create/inline/conflict flows under Task 13 and Task 14. Unit tests fully cover the
  wiring contract for both, but a real-browser E2E would catch regressions the units
  miss (focus trap, modal positioning, autosave debounce timing in a real event loop,
  conflict banner CSS layout).


  Deferred during Phase A execution because the unit tests give us the TDD gate and
  the E2E adds runtime + browser dependency. Worth adding once Phase A is fully landed
  and we want to lock in the contract.


  Suggested coverage:

  - Open kanban, click `+ Task`, fill required fields, Save — confirm task appears
  in column

  - Open Task Detail, click `✎ Edit`, change field, Save — confirm Task Detail re-renders

  - Click a field on Task Detail (after Task 14), edit inline, Enter — confirm autosave
  + status indicator

  - Two simultaneous edits (set ETag stale) — confirm conflict banner with Keep mine
  / Use server'
id: v3-edit-016
title: Add Playwright E2E coverage for + Task / ✎ Edit modal flow
---
