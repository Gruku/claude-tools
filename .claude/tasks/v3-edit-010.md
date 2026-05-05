---
notes: Plan Task 10 (spec v3-edit-005 — concurrency). `compute_etag(path) = sha1(mtime
  + content)[:16]`. GET response carries ETag header; PATCH/PUT require If-Match.
  Mismatch → 409 with `{current, current_etag}`. No If-Match in dev mode allowed (passive
  — log a warning).
docs:
  plan: docs/superpowers/plans/2026-05-04-v3-edit-phase-a.md
  spec: docs/superpowers/specs/2026-05-04-v3-edit-in-ui-design.md
id: v3-edit-010
title: ETag/If-Match concurrency for task writes
---
