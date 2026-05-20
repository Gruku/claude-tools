---
id: IDEA-016
title: Review-Gate-Before-Merge hook (taskmaster)
created: '2026-05-20T22:42:55Z'
created_by: user
status: candidate
tags:
- plugin:taskmaster
- plugin:guard-hooks
- kind:hook
- kind:policy
- blocked-by:project-manifest-001
- related:IDEA-005
related_tasks:
- project-manifest-001
related_issues: []
related_lessons: []
promoted_to: null
archived: false
tldr: 'PreToolUse hook on `git merge` that blocks the merge unless the task tied to
  the branch being merged has a `review_gate: pass` record.'
tldr_autogen: true
links:
- type: relates_to
  target: project-manifest-001
- type: references
  target: IDEA-005
---
PreToolUse hook on `git merge` that blocks the merge unless the task tied to the branch being merged has a `review_gate: pass` record. Configurable per project (default off until validated).

**Setting location:** `.taskmaster/project.yaml` under `meta.policies.review_gate_required_for_merge` — depends on `project-manifest-001` landing. Temporary fallback: `meta.policies` in `backlog.yaml` if we want to ship before the manifest merges.

**New task fields:**
- `review_gate` — { status: pass | fail | not-run, ran_at, commit_sha } — written by `taskmaster:review-gate` skill on completion.
- `merge_status` — per-target map: `{ checkout: { merged_at, merge_commit }, stage: {...}, prod: {...} }` — written by PostToolUse hook.

**Hook behavior:**
- PreToolUse on `Bash` matching `git merge`: identify branch being merged → look up task via `branch` field in `backlog.yaml in_progress` → check `review_gate.status == pass` AND `commit_sha` matches branch tip → block with remediation if not. Low-friction bypass via explicit task flag (`skip_merge_gate: true`) for docs-only / revert branches.
- PostToolUse on `Bash` matching `git merge`: always records the merge target into `merge_status` (audit trail is always on, independent of the policy setting).

**Branch labels (checkout vs stage vs prod):**
- Built-in defaults: `master`/`main` = checkout, `stage`/`staging` = stage.
- Per-project override in `project.yaml.meta.policies.merge_targets`.

**Related:**
- IDEA-005 (Detect-Rebased-Duplicates-Before-Merge) — same PreToolUse-on-git-merge surface; should coexist (run both checks).
- `project-manifest-001` — blocker for the canonical setting location.
- `taskmaster:review-gate` skill — gets a new responsibility: write the `review_gate` record on pass.
