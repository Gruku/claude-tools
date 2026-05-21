---
id: issue-bar-audit-001
title: "Audit existing ISS-* against new bug-tier bar; convert non-qualifiers to Bugs"
status: done
priority: high
epic: taskmaster-quality
docs:
  spec: docs/superpowers/specs/2026-05-20-taskmaster-bug-tier-design.md
  plan: docs/superpowers/plans/2026-05-20-taskmaster-bug-tier.md
notes: |
  Walk every open `.taskmaster/issues/ISS-*.md` and judge against the new bar:
  
  - **Recurring** (≥2 prior occurrences cited)
  - **Systemic** (≥2 affected components / class-of-defect)
  - **Outstanding** (P0/P1 with concrete blast-radius)
  
  Qualifiers stay as Issues (backfill mandatory `evidence:` field). Non-qualifiers convert to Bugs.

  **Pre-audit verdicts (best-guess, subject to final judgment)**
  | ID | Verdict | Reason |
  |---|---|---|
  | ISS-004 | Stays | Systemic — same defect across multiple readers |
  | ISS-015 | Demote | Cosmetic single-location |
  | ISS-005–014 | Per-file | Mixed |
  
  **Steps**
  1. List all `.taskmaster/issues/ISS-*.md`.
  2. For each, apply the bar criteria; record verdict.
  3. For stays: extract evidence sentence from body; add `evidence:` field; `_validate_issue` passes.
  4. For demotes: create `B-NNN.md`; copy title, body, components, location; map status (open→open, investigating→open, fixed→fixed, wontfix→shelved, duplicate→shelved); delete original `ISS-NNN.md`.
  5. Sweep `grep -rn "ISS-NNN" .taskmaster/ docs/` for each demoted ID; replace with the new `B-NNN`.
  6. Write the migration handover with the audit log.
---

## Goal

Walk every open `.taskmaster/issues/ISS-*.md` and judge against the new bar:

- **Recurring** (≥2 prior occurrences cited)
- **Systemic** (≥2 affected components / class-of-defect)
- **Outstanding** (P0/P1 with concrete blast-radius)

Qualifiers stay as Issues (backfill mandatory `evidence:` field). Non-qualifiers convert to Bugs.

## Acceptance

- Every remaining `ISS-*.md` has a non-empty `evidence:` field.
- Each demoted ISS is converted to a `B-NNN.md` with appropriate status mapping.
- Every reference to a demoted ISS-NNN in `.taskmaster/` and `docs/` is updated to its new `B-NNN` id.
- A migration handover documents per-ISS verdicts.
