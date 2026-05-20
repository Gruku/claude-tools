---
id: 2026-05-20-issue-bar-audit-migration
date: '2026-05-20'
created: '2026-05-20T00:00:00+00:00'
tldr: Audited 12 ISS-* entries against the new bug-tier bar (recurring/systemic/outstanding) — ISS-004 stays as Issue (systemic, evidence backfilled); ISS-005 through ISS-015 demoted to B-001..B-011 with status mapping preserved.
next_action: Bug-tier audit migration complete — branch ready for review/merge.
task_ids:
- issue-bar-audit-001
session_kind: migration
status: done
status_changed: '2026-05-20T00:00:00+00:00'
---

## TLDR

Audited 12 issues against the new bar (recurring/systemic/outstanding). 1 qualified as an Issue (ISS-004 — systemic, evidence backfilled); 11 were demoted to Bugs B-001..B-011.

## Context note: file-state delta from plan

The plan described per-ISS `.taskmaster/issues/ISS-*.md` files, but in this repo issues lived only as index entries in `backlog.yaml` (no on-disk files). The migration first materializes the on-disk file for stays (using the index entry as source) so the canonical state matches what the rest of the v3 surface (MCP `read_issue`, viewer, sync helpers) expects. Without this, the next MCP call to update an issue would fail with "file not found."

## Per-ISS verdicts

| ID | Verdict | Reason | New ID |
|---|---|---|---|
| ISS-004 | STAY | Systemic — same Path()/backlog_path.parent class-of-defect across handover writer + handover/lesson/issue readers; 3 components (taskmaster, viewer, v3) | — |
| ISS-005 | DEMOTE | P2 fixed; single function (`compute_issue_aging`) date-parser bug | B-001 |
| ISS-006 | DEMOTE | P2 fixed; single component (viewer) status-key normalization, no recurrence cited | B-002 |
| ISS-007 | DEMOTE | "Test issue" — no body, no impact | B-003 |
| ISS-008 | DEMOTE | P2; single component (guard-hooks); design issue but no ≥2 components, no recurrence cited | B-004 |
| ISS-009 | DEMOTE | P2; single component (guard-hooks); localized to one matcher | B-005 |
| ISS-010 | DEMOTE | P2 fixed; single function (`list_handover_ids`) sort tiebreaker; "handovers" is a sub-area of taskmaster, not a separate component | B-006 |
| ISS-011 | DEMOTE | P3; single function-pair (`parse_frontmatter`/`render_frontmatter`) trailing-newline asymmetry | B-007 |
| ISS-012 | DEMOTE | P2 investigating; single component (guard-hooks); security-relevant but P2 doesn't meet outstanding bar (P0/P1 only) | B-008 |
| ISS-013 | DEMOTE | P3; single regex matcher false-positive | B-009 |
| ISS-014 | DEMOTE | P3; single file freshness-check gap | B-010 |
| ISS-015 | DEMOTE | P3; one default-value mismatch between MCP and viewer; localized fix | B-011 |

## Evidence backfilled (STAYS)

For ISS-004 the `evidence:` field added reads:

> Systemic: same defect class (Path() literal vs backlog_path.parent) spans handover writer plus handover/lesson/issue readers — affects the taskmaster MCP, the v3 file layout, and the viewer reads.

`_validate_issue(ISS-004)` returns OK.

## Status mapping for demotes

`STATUS_MAP` collapsed source ISS status into Bug status:

- `open` → `open`
- `investigating` → `open` (Bug tier has no "investigating" — open is the working state)
- `fixed` → `fixed` (with `fix_commit="migrated-no-sha"` as backfill marker since original commits are not recoverable per-ISS)
- `wontfix` / `duplicate` → `shelved` (would have appended a "see body for rationale" note; none of today's ISSes carried these)

Per-bug status today:
- B-001, B-002, B-006: fixed (were ISS-005, ISS-006, ISS-010)
- B-008: open (was ISS-012 investigating → collapsed to open)
- All others: open

## Reference sweep summary

Within `.taskmaster/`: no real cross-references needed updating. The remaining matches were:

- `bugs/B-*.md` — migration provenance notes (KEPT)
- `tasks/issue-bar-audit-001.md` — the migration task itself; refers to pre-migration state (KEPT)
- `backlog.yaml` historical task titles like "Fix ISS-005: compute_issue_aging crashes ..." and recap tldrs referencing ISS IDs (KEPT — immutable session history)

Within `docs/` and `plugins/taskmaster/skills/`: the only matches are example IDs in skill documentation and the canonical ISS-015 anti-example references in:

- `plugins/taskmaster/skills/issue/references/issue-bar.md` (KEPT — anti-example)
- `plugins/taskmaster/skills/bug/references/bug-vs-issue.md` (KEPT — anti-example)
- `plugins/taskmaster/skills/issue/SKILL.md` (KEPT — points at the anti-example doc)
- `plugins/taskmaster/skills/pick-task/SKILL.md`, `taskmaster/SKILL.md`, `issue/references/entry-point-flows.md` — illustrative example IDs in skill prose (KEPT)

Nothing was mass-replaced.

## Acceptance check

- [x] All remaining ISS-* files have non-empty `evidence:` (`ISS-004` validates OK)
- [x] Each demoted ISS converted to B-NNN with correct status mapping
- [x] Reference sweep complete (anti-example refs preserved)
- [x] Full test suite passes — `1049 passed in 99.93s`

## Judgment calls

- **ISS-010**: components list includes both `taskmaster` and `handovers` which on the surface looks like ≥2. Treated `handovers` as a sub-area of taskmaster (not an independent component) — the actual defect is in one function. Demoted.
- **ISS-012**: security-shaped (per-token sibling guard bypass) but only P2 and one component. Demote was the default because the outstanding bar requires P0/P1 and concrete blast-radius (data-loss / outage / security exposure). If the user judges this should be Outstanding, it can be promoted later via the bug→issue path.
- **ISS-006**: title says "Kanban + table grouping" which could read as two surfaces; both live within the `viewer` component. Demoted.
- Pre-audit guidance in the task prompt referenced "ISS-015 — handover status pill cosmetic, one-character fix" but the actual ISS-015 in this repo is `list_sessions defaults missing handover.status to "open" but viewer expects "todo"` — different content, same demote verdict (P3, localized).
