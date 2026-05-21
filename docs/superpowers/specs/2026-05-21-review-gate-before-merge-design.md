# Review-Gate-Before-Merge

**Date:** 2026-05-21
**Status:** Approved (design only — implementation gated on `project-manifest-001` for Phase B)
**Idea:** [IDEA-016](../../../.taskmaster/ideas/IDEA-016.md)
**Related:** [IDEA-005 Detect-Rebased-Duplicates-Before-Merge](../../../.taskmaster/ideas/IDEA-005.md) (same PreToolUse-on-`git merge` surface; coexists)
**Depends on:** [`project-manifest-001`](../../../.taskmaster/tasks/project-manifest-001.md) (for Phase B only)

---

## Background

Today the taskmaster `review-gate` skill runs quality checks (Claude review, optional Codex pass, tests + build) and transitions a task to `in-review`. The check is voluntary — there is no enforcement that it ran, and nothing connects "the gate passed" to the moment that matters most: merging the feature branch back into the main checkout. A Claude session (or the user) can `git merge feature/foo` directly, skipping the gate entirely, and nothing in the harness notices.

The user wants this enforced as a *configurable* policy: when on, `git merge` is blocked unless the task tied to the source branch has a recorded `review_gate: pass`. The policy must be low-friction (sane bypass for docs-only / hotfix branches), fail-open on infrastructure issues (a buggy hook must never block legitimate work), and produce an audit trail of where each branch has landed (checkout, stage, prod) regardless of whether the policy is enforcing.

## Goals

- Block `git merge` when the policy is on and the relevant task lacks a fresh `review_gate: pass`.
- Always record merge events on the task (audit trail is independent of the enforcement flag).
- Default off per project (opt-in) — surprise nobody on plugin upgrade.
- Strict freshness by default (the recorded gate-commit must equal the source branch tip), with an explicit per-task downgrade for branches where light follow-up commits should not re-trigger the gate.
- Per-task exemption flag for branches the gate cannot meaningfully run on (docs, reverts, generated files).
- One-shot human approval flow for genuine "I want to merge this anyway" moments, modelled on the existing guard-hooks Approve/Deny UX.
- Surface gate state and merge state in the viewer so the user can see at a glance which tasks are gated, passing, and merged where.

## Non-goals

- Replacing the `taskmaster:review-gate` skill itself. This spec adds a *recording* and *enforcement* layer on top of the existing gate.
- Re-running the gate from the hook. The hook checks for a recorded pass; it does not invoke the skill. If the user wants the gate to run, they invoke it.
- PR-level gating. This is local-`git merge`-only. Remote/PR merges go through the user's chosen platform (GitHub, etc.) and have their own protected-branch rules.
- Branch-protection enforcement (force push, push to main). guard-hooks already covers those.
- Auto-detecting "what kind of branch this is" (docs / hotfix / revert). The user marks exemptions explicitly via the task flag.

## Architecture

A two-hook protocol in the **taskmaster** plugin (deliberately not guard-hooks — guard-hooks is for hard safety rails like `rm -rf` and force push; this is project policy enforcement, a different category).

```
                                                        ┌────────────────────────────────┐
                                                        │ taskmaster:review-gate skill   │
                                                        │ (existing — runs quality       │
                                                        │  checks, transitions task to   │
                                                        │  `in-review`)                  │
                                                        └──────────────┬─────────────────┘
                                                                       │ on pass verdict
                                                                       ▼
                                                        ┌────────────────────────────────┐
                                                        │ backlog_record_review_gate     │
                                                        │ (new MCP tool — writes         │
                                                        │  review_gate frontmatter)      │
                                                        └────────────────────────────────┘

  user: git merge feature/foo
        │
        ▼
  ┌─────────────────────────┐    block?    ┌──────────────────────┐
  │ PreToolUse: merge-gate  ├─── yes ───►  │ AskUserQuestion      │
  │ (reads policy + task    │              │ Approve / Deny       │
  │  review_gate + freshness)│              └──────────────────────┘
  └────────┬────────────────┘                        │
           │ allow                                   │ Approve
           ▼                                         ▼
  ┌─────────────────────────┐               (allow, continue)
  │ Bash: git merge         │
  └────────┬────────────────┘
           │ exit 0
           ▼
  ┌─────────────────────────┐
  │ PostToolUse:            │
  │ merge-recorder          │   ──►   backlog_record_merge (new MCP tool)
  │ (identifies target      │         writes merge_status frontmatter
  │  label, records merge)  │
  └─────────────────────────┘
```

Both hooks resolve "source branch → task" by reading `backlog.yaml`'s `meta.in_progress[*].branch` field (and, when present, scanning archived/done tasks with a recorded `branch`).

## Components

### 1. Schema additions to `.taskmaster/project.yaml`

Under `meta.policies`:

```yaml
meta:
  policies:
    review_gate_required_for_merge: false   # default — opt-in per project
    merge_targets:                           # defaults below if absent
      checkout: [master, main]
      stage:    [stage, staging]
      prod:     [release, production]
```

`merge_targets` is a label-to-branch-names map. Defaults are baked into the loader so projects with standard branch names need zero config. A project that overrides `merge_targets` partially still gets the built-in defaults for un-overridden labels (merge, don't replace).

This block is read only by the hooks and by `backlog_record_merge` (for target-label resolution). When `project.yaml` is absent, both behave as if the policy is off and only built-in `merge_targets` defaults apply.

### 2. Task frontmatter additions

```yaml
review_gate:
  status: pass | fail | not-run      # default not-run if absent
  ran_at: "2026-05-21T14:23:00Z"
  commit_sha: "abc1234..."           # HEAD of the task branch at the moment the gate ran
merge_status:
  checkout:
    merged_at: "2026-05-21T16:02:11Z"
    merge_commit: "def5678..."
  stage:
    merged_at: "..."
    merge_commit: "..."
skip_merge_gate: false               # per-task exemption (docs / revert / generated)
merge_gate_freshness: strict         # strict (default) | any
```

All four fields are optional on existing tasks. Defaults apply when absent.

### 3. New MCP tools

| Tool | Purpose | Caller |
|---|---|---|
| `backlog_record_review_gate(task_id, status, commit_sha)` | Write the `review_gate` block on a task. Sets `ran_at` to now. | `taskmaster:review-gate` skill |
| `backlog_record_merge(task_id, target_label, merge_commit)` | Write `merge_status[target_label]` on a task. Sets `merged_at` to now. | PostToolUse `merge-recorder` hook |

Both are thin wrappers over the existing `backlog_update_task` write path (atomic write, yaml sort_keys=False to keep diff stable).

### 4. Skill update — `taskmaster:review-gate`

Currently the skill ends with "transition to `in-review` if all blocking gates passed." Add one new responsibility immediately before the transition: when the verdict is **pass**, call `backlog_record_review_gate(task_id, status="pass", commit_sha=<HEAD of current branch>)`. On **fail**, record `status="fail"` with the same `commit_sha` so the viewer can show "gate failed at this commit."

The skill body grows by one step; no other behavior changes.

### 5. Hooks — `plugins/taskmaster/hooks/`

Two bash hooks, registered via `plugin.json`:

**`merge-gate.sh` (PreToolUse, matcher: `Bash`)**

Decision table (first matching row wins, in order):

| Condition | Action |
|---|---|
| Command does not match `^git merge\b` (with normal whitespace/flag variants) | allow (not our concern) |
| Cannot read `backlog.yaml` | allow + stderr warn |
| Cannot read `project.yaml` OR `review_gate_required_for_merge != true` | allow (policy off) |
| Cannot parse a source branch from the merge command (anonymous merge / SHA) | allow + stderr warn |
| No task found whose `branch` matches the source branch | allow (untracked work — not gating) |
| Task has `skip_merge_gate: true` | allow |
| Task has `review_gate.status == pass` AND (`merge_gate_freshness == any` OR `review_gate.commit_sha == HEAD of source branch`) | allow |
| Otherwise | **block** with remediation message + AskUserQuestion(Approve / Deny) |

The block message includes: task ID, the specific reason (no gate run / gate failed / gate commit_sha mismatch), and the exact remediation command (`/taskmaster:review-gate`). On Approve, the hook exits 0 and the merge proceeds.

**`merge-recorder.sh` (PostToolUse, matcher: `Bash`)**

Decision table:

| Condition | Action |
|---|---|
| Command did not match `^git merge\b` | exit (not our concern) |
| Exit code != 0 | exit (merge failed, nothing to record) |
| Cannot parse source branch | exit + stderr warn |
| No task for the source branch | exit (untracked) |
| Current branch (the target) does not match any label in `merge_targets` (after defaults) | record under label `branch:<name>` (raw branch name) so audit is preserved |
| Current branch matches a label | call `backlog_record_merge(task_id, label, HEAD)` |

PostToolUse never blocks (Claude Code semantics — exit code is advisory only); its job is purely to record.

### 6. Viewer surface

On task cards:

- A small **gate badge** in the corner: `✓` green when `review_gate.status == pass` and fresh (commit_sha matches latest known branch tip); `!` amber when pass but stale; `✗` red when fail; empty when not-run.
- A small **merge ladder**: dots labelled `co | st | pr` (checkout / stage / prod), filled when the corresponding `merge_status[label]` is set.

On task detail panel:

- Full `review_gate` block (status, ran_at, commit_sha).
- Full `merge_status` block (per-target merged_at and merge_commit).
- Toggle controls for `skip_merge_gate` and `merge_gate_freshness` so the user can adjust without editing the frontmatter directly.

Visual rules (per `CLAUDE.md`): no colored left rails on cards; no hover motion; tinted backgrounds / top borders only.

## Data Flow — Worked Example

1. User runs `/taskmaster:pick-task v3-polish-042` → status becomes `in-progress`, branch `feature/v3-polish-042` exists, working in a worktree.
2. User does work, commits.
3. User runs `/taskmaster:review-gate` → all gates green → skill calls `backlog_record_review_gate("v3-polish-042", "pass", "abc1234")` → task frontmatter gets the `review_gate` block.
4. User returns to main checkout, runs `git merge feature/v3-polish-042`.
5. **PreToolUse `merge-gate.sh`:**
   - Matches `git merge`, source branch = `feature/v3-polish-042`.
   - Looks up task → `v3-polish-042`.
   - `review_gate_required_for_merge = true`, `skip_merge_gate = false`.
   - `review_gate.status = pass`, `commit_sha = abc1234`. Reads `git rev-parse feature/v3-polish-042` → `abc1234`. Match → allow.
6. `git merge` runs, succeeds, exit 0.
7. **PostToolUse `merge-recorder.sh`:**
   - Current branch (target) = `master` → matches label `checkout`.
   - Calls `backlog_record_merge("v3-polish-042", "checkout", "<new merge commit SHA>")`.
8. Task frontmatter now shows `merge_status.checkout`. Viewer ladder lights up the `co` dot.

Failure-path example (stale gate):

5a. Same as above, but the user added one commit after running the gate, so `feature/v3-polish-042` tip is now `def5678`, and `review_gate.commit_sha == abc1234`.
   - Mismatch → block. Message: "v3-polish-042: review_gate recorded at abc1234, but source branch tip is def5678. Re-run `/taskmaster:review-gate` or set `merge_gate_freshness: any` on the task."
   - AskUserQuestion offers Approve / Deny. Approve = merge proceeds (recorded by PostToolUse, with the stale gate state).

## Edge Cases — All Fail-Open

| Scenario | Behavior | Rationale |
|---|---|---|
| `project.yaml` does not exist | allow | Policy can't be on if there's no manifest |
| `backlog.yaml` does not exist | allow + warn | No backlog = not a taskmaster project |
| Source branch parse fails (`git merge HEAD~1`, SHA, etc.) | allow + warn | Anonymous merge — can't map to a task |
| Task lookup throws (corrupt yaml, IO error) | allow + warn | Don't block on infrastructure |
| `merge_targets` references a branch that doesn't exist | label still applies if current branch name matches | Match is by string, not by branch existence |
| Hook script itself errors (syntax error, missing dep) | allow (Claude Code default for hook non-zero) | Buggy hook ≠ unsafe merge |
| User is mid-rebase / mid-conflict-resolution running `git merge --continue` | allow | Not the initial merge; gate already evaluated upstream |

**Rule:** the hook's burden of proof is "I am certain this should be blocked." Any uncertainty resolves to allow.

## Testing

### Phase A tests (ship now)

- Unit tests for `backlog_record_review_gate` and `backlog_record_merge`: round-trip frontmatter, idempotent, atomic write, sort_keys preserved.
- Skill test: `taskmaster:review-gate` calls the MCP tool with correct args on pass / fail / skip.
- Viewer unit tests: gate badge renders correctly per status; merge ladder renders per `merge_status` shape.

### Phase B tests (after `project-manifest-001`)

- Hook decision-table unit tests: 16 combinations of (policy on/off × pass/fail/not-run × freshness strict/any × skip on/off). Pure shell, mocked git + yaml inputs.
- Integration test: temp repo, real `git merge`, hook installed, verifies block / allow / record behaviour.
- AskUserQuestion bypass test: simulate Approve, verify merge proceeds and is still recorded.
- Fail-open tests: every edge case in the table above produces allow + appropriate warning.

## Phasing — Relative to `project-manifest-001`

The hooks and policy enforcement require `project.yaml` to read `meta.policies.review_gate_required_for_merge` and `meta.policies.merge_targets`. Everything else can ship independently.

**Phase A — ships now (no `project.yaml` dependency):**

1. This design doc (committed).
2. Task frontmatter additions documented in convention (loader tolerates the new fields — they round-trip via existing yaml read/write).
3. New MCP tools: `backlog_record_review_gate`, `backlog_record_merge`.
4. `taskmaster:review-gate` skill update — call the recording tool on pass/fail verdict.
5. Viewer surface — gate badge on task card, merge ladder, detail-panel controls for `skip_merge_gate` and `merge_gate_freshness`.

After Phase A, the data exists, the skill writes it, the viewer shows it. No enforcement yet — but a user can already see which tasks have a recorded pass and which have merged where.

**Phase B — waits for `project-manifest-001` to land:**

6. Schema additions to `project.yaml` (the two policy keys).
7. `hooks/merge-gate.sh` + `hooks/merge-recorder.sh`.
8. Plugin manifest registration (PreToolUse + PostToolUse entries in `plugin.json`).
9. Hook decision-table tests + E2E integration test.

Phase B is a small bolt-on: each hook is ~100 lines of shell, the schema additions are 6 yaml lines, and the loader changes are 2 keys. Estimated effort: half a day, vs. Phase A's 1–2 days.

## Open Questions (deferred, not blocking)

- **Stale-gate auto-rerun:** should the block message offer a `/taskmaster:review-gate --rerun` shortcut? Probably yes in v1.1.
- **Gate-result archival:** when a task is archived, the `review_gate` and `merge_status` should travel with it (already handled by existing archive flow since they're plain frontmatter). Confirm in Phase A testing.
- **Multi-branch merges (octopus):** `git merge branch1 branch2 branch3`. v1 handles the first source branch only; treats the rest as untracked. Document as a known limitation.
- **Sub-repo / submodule merges:** out of scope for v1. Each sub-repo has its own `.taskmaster/`; the hook respects whichever `.taskmaster/` is rooted in the current working directory.
