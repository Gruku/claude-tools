---
id: 2026-05-21-shipped-taskmaster-bug-tier-new-bug-arti
date: '2026-05-21'
created: '2026-05-21T00:33:29.313100+00:00'
tldr: 'Shipped taskmaster bug-tier: new Bug artifact + tightened Issue bar; PR #24
  merged at f3f50c0.'
next_action: Fast-forward local master onto origin (handle WIP collision on .taskmaster/backlog.yaml).
task_ids: []
session_kind: milestone
status: open
status_changed: '2026-05-21T00:33:29.313100+00:00'
status_user_set: false
branch: master
tip_commit: dc02ffe
open_decisions: []
resolved_this_session: []
links:
- type: references
  target: IDEA-014
- type: references
  target: ISS-004
- type: references
  target: ISS-015
---
## Resume prompt

> Work is shipped — PR #24 merged at origin/master `f3f50c0`. Worktree + branch already cleaned up. Local master is at `dc02ffe` (one local-only docs commit ahead of origin/master at the divergence point). To catch local up: `git stash push -m 'pre-master-sync'`, then `git rebase origin/master`, then `git stash pop` and resolve the `.taskmaster/backlog.yaml` conflict (the migration extensively touched it). Spec + plan live locally at `docs/superpowers/{specs,plans}/2026-05-20-taskmaster-bug-tier*` (gitignored, never pushed).

## Where execution stands

- **Remote:** `origin/master` at `f3f50c0` (Merge PR #24). Source branch `feature/taskmaster-bug-tier` deleted on GitHub.
- **Local:** parent checkout on `master` at `dc02ffe` (your pre-existing unpushed docs commit). Worktree `.worktrees/feature-taskmaster-bug-tier/` removed cleanly via `git worktree remove` (no --force). Local branch `feature/taskmaster-bug-tier` deleted via `git branch -d`.
- **Tests:** 1049/1049 passing on the merged branch. 7 pre-existing failures (decision_skill_lint + end_session_decision_sweep — missing skill file) unrelated to this work.
- **WIP untouched:** 7 modified files in working tree from unrelated prior session (`.claude/settings.json`, `.gitignore`, `.taskmaster/backlog.yaml`, `.taskmaster/handovers/2026-05-18-...`, `.taskmaster/ideas/IDEA-014.md`, `.taskmaster/tasks/project-manifest-001.md`, `docs/superpowers/specs/2026-05-09-agentic-os-architecture-design.md`).

## What shipped this session

| # | What | Where |
|---|------|-------|
| 1 | Brainstormed + designed bug-tier model (Bug = sink, Issue = elevated with mandatory `evidence:` field) | `docs/superpowers/specs/2026-05-20-taskmaster-bug-tier-design.md` (local-only) |
| 2 | Wrote 22-task implementation plan | `docs/superpowers/plans/2026-05-20-taskmaster-bug-tier.md` (local-only) |
| 3 | Backend (10 commits): bug primitives, schema, archive, index, pattern scanner, atomic promote, mandatory Issue evidence, 7 MCP tools + HTTP routes, complete_task close-gate + auto-archive | Phase 1 commits in PR #24 |
| 4 | Skills (4 commits): new `taskmaster:bug`, tightened `taskmaster:issue` (deleted `flag-from-conversation`, renamed `severity-heuristics.md` → `issue-bar.md`), word-agnostic router, `review-gate`+`end-session` bug-gate | Phase 2 commits |
| 5 | Viewer (5 commits): Bugs screen with filter chips, bug detail with disposition actions, Linked Bugs subsection on task rail, evidence column on Issues | Phase 3 commits |
| 6 | Migration (2 commits): audited 12 ISSes; 1 stays (ISS-004 — systemic), 11 demoted to B-001..B-011; audit handover written | Phase 4 commits |
| 7 | PR opened + rebased to drop spec/plan commit + merged | PR #24, merge at `f3f50c0` |
| 8 | Worktree + local branch cleanup (safe, no --force) | `git worktree remove`, `git branch -d` |

## What's next

1. Sync local `master` to `origin/master` (rebase the local-only `dc02ffe` docs commit onto the merged tip).
2. Decide what to do with the dirty WIP — likely commit on a new branch or stash for later.
3. Optional: manually exercise the new MCP surface (`backlog_bug_create`, `backlog_bug_promote`) and the Bugs viewer screen to validate the model in practice.
4. Optional: investigate the test-fixture leak (see "Important non-obvious things" #4) — partial fix in commit `998a205` didn't catch every code path.
5. Optional: clean up `/tmp/bug-tier-test-debris-<ts>/` if you don't want the moved-aside test artifacts.

## Files of interest

| Group | Path | What | Why next session needs it |
|---|---|---|---|
| Touched | `plugins/taskmaster/taskmaster_v3.py` | New `# ── Bugs ──` region (helpers, schema, archive, index, scanner, promote); `_validate_issue` now requires `evidence`; `write_issue` accepts `evidence` kwarg | Anchor for any backend tweak to the Bug surface |
| Touched | `plugins/taskmaster/backlog_server.py` | 7 new `backlog_bug_*` MCP tools at ~line 2785; modified `backlog_issue_create` (now requires `evidence`); `backlog_complete_task` now has Bug close-gate + post-transition archive sweep | HTTP+MCP surface for bugs |
| Touched | `plugins/taskmaster/skills/bug/` (new) | New skill with 5 entry points, `bug-vs-issue.md` (canonical routing reference + ISS-015 anti-example) | Trigger surface for any user-flagged bug intake |
| Touched | `plugins/taskmaster/skills/issue/` | Description narrowed, `flag-from-conversation` deleted, `severity-heuristics.md` renamed to `issue-bar.md`, new `promote-from-bug` entry point in flows | Routing for elevated-tier Issues only |
| Touched | `plugins/taskmaster/skills/taskmaster/references/word-agnostic-intake.md` (new) | Algorithm for routing "log an issue" → Bug or Issue based on evidence | Read before changing intake routing |
| Touched | `plugins/taskmaster/viewer/js/screens/bugs.js` + `bug-detail.js` + `components/bug-card.js` + `css/screens/bugs.css` (all new) | New Bugs screen with Open/Shelved/Archive chips; detail with disposition actions | Frontend entry point |
| Touched | `.taskmaster/issues/ISS-004.md` (now sole Issue), `.taskmaster/bugs/B-001..B-011.md` (demoted), `.taskmaster/handovers/2026-05-20-issue-bar-audit-migration.md` | Post-migration state | Reference if any ISS-XX is mentioned in old handovers/recap |
| Touched | `scripts/migrate_iss_to_bug.py` | One-off migration helper, committed for audit trail | Safe to delete later; kept as reproducibility artifact |
| Relevant | `docs/superpowers/specs/2026-05-20-taskmaster-bug-tier-design.md` (local-only) | The design spec — has the dialogue/rationale that the PR description abbreviated | Read if you need to re-derive a design choice |
| Relevant | `docs/superpowers/plans/2026-05-20-taskmaster-bug-tier.md` (local-only) | 22-task implementation plan with all code blocks | Reference for "why was X done this way" |

## Important non-obvious things

1. **Spec + plan are local-only.** `docs/superpowers/` is gitignored (line 26). They were force-added to the feature branch, then dropped from history via `git rebase --onto 23cd4e7 ffde4f3` before push. Parent checkout still has them. If you ever need to push them, follow the archive-and-re-ignore convention (memory `project_superpowers_local_tracking.md`).
2. **Pattern scanner uses Jaccard ≥0.5 clustering, NOT exact-tuple match.** The plan specified exact-tuple, but a subagent caught that two real-world bugs with overlapping titles ("Path mismatch in v3 reader" + "Path mismatch in v3 reader (handover)") would never group under exact match. Jaccard ≥0.5 was the smallest deviation that made the grouping test pass. Surface contract preserved (returns `{signature, bug_ids}` groups).
3. **Word-agnostic intake.** User saying "log an issue" no longer force-routes to `taskmaster:issue`. The router parses for evidence first and falls back to `taskmaster:bug` (with an explanation echo) when evidence is absent. Lives in `skills/taskmaster/references/word-agnostic-intake.md`.
4. **Test fixture leak — `running_server` partial fix.** Commit `998a205` added monkeypatches to `running_server` for `ROOT`, `CONFIG_PATH`, `LEGACY_CONFIG_PATH` to keep test writes inside `tmp_path`. The fix was incomplete: some HTTP write paths still leaked to the plugin's real `.taskmaster/bugs/` dir during T9 and T17 test runs. Evidence: `B-001..B-014.md` accumulated in `plugins/taskmaster/bugs/` (moved to `/tmp/bug-tier-test-debris-<ts>` to allow safe worktree removal). If you run the test suite again without the leak being fully patched, debris will reappear.
5. **`gh pr merge` from a worktree fails.** When master is checked out in the parent checkout, `gh pr merge 24 --delete-branch` from inside a worktree fails because gh tries to switch to master locally. Workaround: run gh from the parent checkout. After the failed worktree attempt, the merge still landed on GitHub — only the local branch-delete step failed. Re-running from the parent gave `! Pull request was already merged` (idempotent).
6. **No backlog task tracked the work.** This entire 22-task plan was driven by `docs/superpowers/{specs,plans}/` + the session's TodoWrite. The only formally-tracked artifact was the migration sub-task `issue-bar-audit-001` (marked done by T21). If you want this kind of work tracked as a backlog task next time, create it before kicking off the plan.
7. **Local master diverged.** Origin/master is at `f3f50c0` (3 merges ahead: PRs #22, #23, #24). Local master is at `dc02ffe` (1 commit ahead of the common ancestor — a docs commit for Review-Gate-Before-Merge that you made earlier). Resync requires rebase, not fast-forward. WIP on `.taskmaster/backlog.yaml` will collide with the migration's changes to that file.
8. **Anti-example references preserved.** `plugins/taskmaster/skills/issue/references/issue-bar.md` and `plugins/taskmaster/skills/bug/references/bug-vs-issue.md` BOTH keep the literal string `ISS-015` as the canonical "this is a Bug, NOT an Issue" anti-example. Do NOT sweep-replace these — even though ISS-015 itself was demoted to `B-NNN` during the migration.
