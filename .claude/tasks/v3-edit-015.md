---
notes: 'Plan Task 15 (spec v3-edit-009 — validation). `validate_task_write(task_id,
  patch, backlog)` — checks epic/phase existence, dep cycle detection via `_has_cycle_to(adj,
  target)`, status enum, priority enum, and any cross-field rules. Returns 422 with
  `{errors: {field: msg}}` on failure. Layer 3 of the validation stack, the safety
  net behind field-level + schema-level checks.'
docs:
  plan: docs/superpowers/plans/2026-05-04-v3-edit-phase-a.md
  spec: docs/superpowers/specs/2026-05-04-v3-edit-in-ui-design.md
id: v3-edit-015
title: Server-side validation pipeline
---
