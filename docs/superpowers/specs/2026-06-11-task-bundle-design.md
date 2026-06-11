# Task Bundle — Design

**Date:** 2026-06-11
**Status:** Approved (brainstorm session 2026-06-11)
**Context:** auto-epic / auto-task are being removed; bundles target the normal interactive flow (pick → work → review-gate → merge).

## Problem

Discrete backlog tasks frequently touch the same surface and the same files, yet the protocol mandates one worktree, one branch, and one full lifecycle per task (`pick-task` Step 8: "a dedicated worktree per task is mandatory"). For a cluster of small same-surface tasks this manufactures N worktrees, N branches, N serial lifecycles, and N merge-ladder climbs where a capable model would sweep all the changes in a handful of coherent edits. The isolation the protocol buys is worthless here — the changes are not independent; that is the defining property of the cluster.

## Concept

A **bundle** is a shared execution slug, not a new entity. Tasks sharing the slug execute together in one worktree with one merged lifecycle, while remaining fully discrete in the backlog (own ID, status, gates, completion record).

Positioning against existing grouping constructs:

| Construct | Groups by |
|---|---|
| `epic` | theme |
| `phase` | time / delivery |
| **`bundle`** | **surface affinity (same files)** |

Bundles are orthogonal to epics and phases — members may span epics. Members MUST share the same `sub_repo` (one worktree = one repo); this is validated at bind time.

## Data model

One new slim task field:

- `bundle: <slug>` — e.g. `bundle: asset-contract-ux`. Tasks sharing the slug are bundle members.

No bundle file, no new YAML collection, no new viewer screen. The slug serves as both the *hint* (written at birth) and the *binding* (consumed at pick). Cleared on descope.

## Lifecycle

### Formation — hinted at birth, bound at pick

**At birth:** any flow that creates several same-surface tasks in one sitting (a triage conversation, a brainstorm fan-out) sets the same `bundle` slug on them, plus `anchors`. Cheap, because the creator already knows the cluster.

**At pick (binding):** picking any member picks up the whole bundle:

1. One worktree `.worktrees/<bundle-slug>`, one branch `feature/<bundle-slug>`.
2. All members → `in-progress`, with the shared `branch` / `worktree` recorded on each.
3. Claude announces membership: "Picking bundle `asset-contract-ux`: ps-163, ps-174, ps-176."

**Detection fallback:** when a picked task has no slug but `backlog_blast_radius(mode="predictive")` shows strong anchor overlap with other `todo` tasks, Claude bundles them on its own authority, announcing in one line ("also sweeping ps-177 in, same files") — the announcement is the veto window. The slug is set on the spot.

### Execution — one sweep

- **One combined spec/plan**: a section per member (goal + acceptance criteria) plus one shared "surface" section. The shared spec path is recorded on every member's gate record.
- **One test-writing pass, one implementation sweep, one test run.**
- **Lane = strictest member's lane** (full > standard > express).
- **Commits reference the task IDs they advance** (`feat(ps-163,ps-174): …`). No pretense that edits decompose per task.

### Verification & merge — per task, atomic branch

- The review gate runs **once** but verifies **each member's acceptance criteria separately** — N verdicts, one report.
- Passing members complete individually (own completion records, own gate verdicts).
- A failing member does not drag down the others' records, but the branch merges atomically, so it blocks the merge until either:
  - **(a) fix-up pass** inside the same worktree, or
  - **(b) descope**: slug cleared, status back to `todo`, its claims removed from the spec; the bundle merges without it.
- One merge event fans `backlog_record_merge` out to all completing members (same rung, same sha).

## Decisions (forged in brainstorm)

1. **Hybrid formation** — hint at birth, bind at pick. Rejected: pure execution-time grouping (loses the free signal triage has at creation); first-class persisted entity (reinvents epics, heavy for what is an execution concern).
2. **One sweep, per-task verify** — rejected: fully fused lifecycle (one weak member blocks all, thin per-task history); shared-worktree-with-per-task-stages (keeps most of the serial overhead).
3. **Always auto-bundle** — interactive announce, no consent ceremony. The user is present in normal flow; the announcement is the veto window.
4. **Slug, not entity** — strongest call. A bundle has no independent life: it is born from a slug, becomes a worktree, dies at merge.
5. **Descope rule** — strongest call. Atomic branch + individual records means a failing member must be fixed or descoped; descope is explicit (slug cleared, spec claims removed), never silent.

## Changes by location

| Where | Change |
|---|---|
| `taskmaster_v3.py` `SLIM_FIELDS["task"]` | add `bundle` |
| `backlog_server.py` `ALLOWED_FIELDS` | add `bundle` |
| `backlog_add_task` | accept `bundle` param |
| `backlog_batch_update` / `backlog_batch_preview` | support setting `bundle` |
| `backlog_pick_task` + `_build_worktree_instruction()` | bundle-aware: detect slug on picked task, return member list + shared worktree instruction (`.worktrees/<slug>`, `feature/<slug>`); validate all members share `sub_repo`; idempotent re-pick when bundle already in progress |
| `skills/pick-task/SKILL.md` | bundle pickup protocol replaces the per-task worktree mandate when slug present; detection-fallback step via `backlog_blast_radius(mode="predictive")` |
| `skills/review-gate/SKILL.md` | per-member verdict mode + descope path |
| `skills/end-session/SKILL.md` | handle multiple members completing off one branch |
| `blast_radius.py` | unchanged — `find_overlapping_tasks()` is already the detection kernel |
| Viewer kanban | bundle badge on cards sharing a slug (no new screen) |

## Out of scope / adjacent

- **Triage skill** (feedback dump → structured tasks) — the natural bundle-hint writer, but its own feature. Logged as an idea.
- **Auto-mode integration** — moot; auto-epic / auto-task are being removed.
- **Cross-repo bundles** — explicitly rejected; one worktree = one repo.

## Testing

- Unit: slug round-trip through `backlog_add_task` / `backlog_update_task`; `backlog_pick_task` returns member list + shared instruction; `sub_repo` mismatch rejected; descope clears slug and resets status.
- Behavioral (skill-level): pick-on-member binds whole bundle; review gate emits N verdicts; merge fan-out records the same rung/sha on all completing members.
