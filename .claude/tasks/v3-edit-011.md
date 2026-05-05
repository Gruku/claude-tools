---
notes: 'Plan Task 11 (spec v3-edit-006 — conflict UX). Two surfaces: (1) field-level
  banner — single-field "Keep mine / Use server" inline with the field; (2) modal-level
  multi-field diff — per-field choices in the modal footer. Server''s 409 payload
  carries `last_modified_by` for the "modified by claude (session abc)" line. Imported
  lazily by inline-field.js so cold-path code stays out of the hot bundle.'
docs:
  plan: docs/superpowers/plans/2026-05-04-v3-edit-phase-a.md
  spec: docs/superpowers/specs/2026-05-04-v3-edit-in-ui-design.md
id: v3-edit-011
title: Conflict banner + inline-field 409 handling
---
