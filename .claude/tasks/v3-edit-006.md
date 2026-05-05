---
notes: 'Plan Task 6 (spec v3-edit-001 — primitives). Pure function `runSchema(values,
  schema)` returning `{ok, errors: {field: msg}}`. Handles per-field `validate()`
  calls + `crossField` rules at the schema level (e.g. "completed must be ≥ started").
  Layer 2 of the three-layer validation stack.'
docs:
  plan: docs/superpowers/plans/2026-05-04-v3-edit-phase-a.md
  spec: docs/superpowers/specs/2026-05-04-v3-edit-in-ui-design.md
id: v3-edit-006
title: Schema validation runner
---
