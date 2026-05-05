---
notes: Plan Task 13 (spec v3-edit-007 — task form, action wiring). `task-actions.js`
  exports `openCreateTaskModal()` and `openEditTaskModal(task)`. Kanban toolbar adds
  `+ Task` button; Task Detail header adds `✎ Edit` button. On Save, optimistically
  refresh the affected screens (kanban moves card to new column, Task Detail re-renders).
docs:
  plan: docs/superpowers/plans/2026-05-04-v3-edit-phase-a.md
  spec: docs/superpowers/specs/2026-05-04-v3-edit-in-ui-design.md
id: v3-edit-013
title: Wire `+ Task` / `✎ Edit` buttons to entity modal
---
