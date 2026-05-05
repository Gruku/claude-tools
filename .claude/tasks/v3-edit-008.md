---
notes: Plan Task 8 (spec v3-edit-003 — inline edit). Wraps a field renderer with read↔edit
  swap + 600ms autosave debounce + status indicator (●→✓/✕). Enter/blur commits, Esc
  reverts. Calls `save(value)` async — the save callback returns the patch to PATCH;
  on 409 dynamically imports conflict-banner.js and surfaces the field-level conflict
  UI.
docs:
  plan: docs/superpowers/plans/2026-05-04-v3-edit-phase-a.md
  spec: docs/superpowers/specs/2026-05-04-v3-edit-in-ui-design.md
id: v3-edit-008
title: inline-field wrapper with autosave
---
