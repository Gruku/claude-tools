# Task Bundle — Design

**Date:** 2026-06-11
**Status:** Revised 2026-06-14 to clear design-review (9 gaps resolved — see "Design-review resolutions"); ready for writing-plans
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

**Slug format:** `^[a-z0-9][a-z0-9-]{1,40}$` (lowercase kebab, 2–41 chars). Validated wherever `bundle` is written (`backlog_add_task`, `backlog_update_task`, `backlog_batch_update`) so a typo can't silently create a broken half-bundle.

**Field plumbing (all required for the slug to be visible/writable):**
- `taskmaster_v3.py` `SLIM_FIELDS["task"]` — add `bundle` (else it's stripped from every slim read; the viewer badge and pick-task never see it).
- `backlog_server.py` `ALLOWED_FIELDS` — add `bundle` (the validation gate for `backlog_update_task` *and* `backlog_batch_update`).
- `backlog_add_task` — add a `bundle` param (this tool has its own explicit param list, separate from `ALLOWED_FIELDS`).

**Birth-time `sub_repo` validation:** when `backlog_add_task` / `backlog_update_task` sets `bundle` and other members already exist, reject a `sub_repo` mismatch *at write time* (not only at pick). One worktree = one repo; a cross-repo bundle should never be representable, not merely unpickable.

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

## Design-review resolutions (2026-06-14)

These resolve the gaps the design-review found between this spec and the current code. They are the opinionated defaults; the build follows them.

**C1 — Multi-member session context.** `_session_task` is a single slot today. Add a parallel `_session_bundle` slot holding `{slug, sub_repo, branch, worktree, members: [task_id]}`. `backlog_pick_task` on a bundle sets `_session_task` to the *picked* member (so existing "current task" inference still works) **and** populates `_session_bundle`. A new `_get_session_bundle()` lets review-gate / end-session iterate members. No tool that reads `_get_session_task()` changes behavior.

**C2 — Merge fan-out = skill loop, no new tool.** There is no batch merge tool and the merge-recorder hook is single-task. The merge skill calls `backlog_record_merge(member, rung, sha)` once per completing member (N load/save cycles — acceptable at bundle sizes; cheaper than a new tool surface). The PostToolUse merge-recorder hook stays single-task; the *skill* owns the fan-out loop, reading members from `_session_bundle`.

**C3 — Find-by-bundle helper.** Add `_find_tasks_by_bundle(data, slug)` in `backlog_server.py` (scan all epics' tasks for `task.get("bundle") == slug`). Used by `backlog_pick_task` binding. Internal helper, not a new MCP tool.

**I1 — Descope.** `in-progress → todo` is a legal transition (confirmed in `LEGAL_STATUS_TRANSITIONS`), so descope is: `backlog_update_task(member, "bundle", "")` + `backlog_update_task(member, "status", "todo")` + clear `branch`/`worktree`. "Remove spec claims" = Claude edits the shared spec doc to excise that member's section (a documented manual editor step in review-gate — there is no document-mutation MCP tool, by design).

**I2 — Lane.** Do **not** mutate each member's per-task `lane`. `backlog_pick_task` computes the strictest member lane (`full > standard > express`) and returns it as the *bundle execution lane*; the pick-task skill routes the shared lifecycle (which gates run) at that lane. Per-task `lane` stays as authored, so post-merge per-task records remain truthful.

**I3 — `backlog_batch_preview`.** It has no `update` op and previewing a bundle assignment isn't needed. Drop the `batch_preview` claim; `backlog_batch_update` alone sets `bundle` across members.

**I4 — Structured detection data.** `backlog_blast_radius(mode="predictive")` returns markdown; parsing it for the fallback is fragile. Add a structured variant (a `structured=True` flag, or expose `analyze_predictive` as a thin MCP tool returning the `overlapping_tasks` list) so the pick-task fallback consumes `[{task_id, status, shared_paths}]` directly and filters `status == "todo"`.

**I5 — End-session timing + per-member records.** Each completing member gets its own real completion record via `backlog_complete_task(member)` (override the `edge-cases.md` "secondary = update-status-only" shortcut for bundles — the spec mandates own records). The shared `.worktrees/<slug>` is removed **only when the last member leaves the bundle** (all members `done` or descoped) — end-session checks `_session_bundle` membership before offering cleanup.

**I6 — Locking.** All members get `locked_by = SESSION_ID` at bind. The lock-conflict error in `backlog_pick_task` gains a bundle-aware message ("`<id>` is a member of bundle `<slug>` locked by another session") so a second session understands the bundle-level lock.

## Changes by location (corrected)

| Where | Change |
|---|---|
| `taskmaster_v3.py` `SLIM_FIELDS["task"]` | add `bundle` |
| `backlog_server.py` `ALLOWED_FIELDS` | add `bundle` + slug-format validation |
| `backlog_add_task` | add `bundle` param + slug-format + birth-time `sub_repo` validation |
| `backlog_batch_update` | sets `bundle` (via `ALLOWED_FIELDS`). **`backlog_batch_preview` unchanged** — no `update` op, not needed |
| `backlog_server.py` `_find_tasks_by_bundle()` | **new helper** — find members by slug (C3) |
| `backlog_server.py` `_session_bundle` + `_get_session_bundle()` | **new** — multi-member session context (C1) |
| `backlog_pick_task` + `_build_worktree_instruction()` | bundle-aware: detect slug, bind all members (status/lock/branch/worktree), shared `.worktrees/<slug>` + `feature/<slug>`, validate `sub_repo`, compute strictest lane, idempotent re-pick, bundle-aware lock error |
| `blast_radius.py` / `backlog_blast_radius` | add structured predictive output for the detection-fallback (I4) |
| `skills/pick-task/SKILL.md` | bundle pickup replaces the per-task worktree mandate when slug present; detection-fallback step via structured predictive blast-radius |
| `skills/review-gate/SKILL.md` | per-member N-verdict mode + descope path (slug/status/branch clear + manual spec-claim excision) |
| `skills/end-session/SKILL.md` | per-member `backlog_complete_task`; merge fan-out loop; worktree cleanup gated on last member (C2, I5) |
| Viewer `card.js` / `kanban.js` | bundle badge on cards sharing a slug (depends on `bundle` in `SLIM_FIELDS`); no new screen |

## Out of scope / adjacent

- **Triage skill** (feedback dump → structured tasks) — the natural bundle-hint writer, but its own feature. Logged as an idea.
- **Auto-mode integration** — moot; auto-epic / auto-task are being removed.
- **Cross-repo bundles** — explicitly rejected; one worktree = one repo.

## Testing

- Unit — data/validation: slug round-trip through `backlog_add_task` / `backlog_update_task`; bad slug rejected (format rule); `sub_repo` mismatch rejected **at birth** and at pick; `bundle` present in slim reads (in `SLIM_FIELDS`); descope clears slug + resets status to `todo` + clears branch/worktree.
- Unit — primitives: `_find_tasks_by_bundle(slug)` returns exactly the members; `backlog_pick_task` on a member binds all members (status/lock/branch/worktree), returns member list + shared instruction (`.worktrees/<slug>`, `feature/<slug>`) + computed strictest lane; idempotent re-pick of an already-bound bundle; bundle-aware lock-conflict error for a second session; `_session_bundle` populated while `_session_task` is the picked member.
- Unit — detection: structured predictive blast-radius returns `[{task_id, status, shared_paths}]`; fallback filters `todo`.
- Behavioral (skill-level): pick-on-member binds whole bundle; review-gate emits N per-member verdicts in one report; a failing member blocks the merge until fix-up or descope; merge fan-out loop records the same rung/sha on every completing member; end-session writes a real completion record per member and only offers worktree cleanup once the last member leaves the bundle.
