# Hook Spawn-Cost Reduction — Design / Decision Record

**Date:** 2026-06-14
**Status:** Partially applied (if-gating live after restart); Defender exclusions pending user action
**Scope:** `~/.claude/settings.json` (user) + `C:\Users\gruku\Files\Work\CodeMaestro\.claude\settings.local.json` (project) + Windows Defender config. **Not** claude-tools repo source.

> This is a *change + decision record*, not a forward design — the if-gating was applied before this doc existed. It is written so the change, the open security decision, and the verification protocol get the same adversarial review as a normal spec. Cluster 3 of the 2026-06-14 triage.

## Problem

Every `Bash` tool call fans out to the registered PreToolUse/Stop hooks. Several guard hooks spawn a Python or bash subprocess **per command**, and on Windows each spawn is scanned by Defender real-time AV. The dominant cost is not the hook logic — it is (a) interpreter spawn + (b) AV scan-on-spawn, paid even for read-only commands (`git status`, `git log`, `ls`, `cat`, builds, tests) that no guard cares about. The original symptom was multi-second stalls; the 2-minute stalls in the source log were actually `sleep; cat` polling (harness-blocked foreground sleep), a separate issue.

**Goal:** Stop guards from spawning on commands they will never act on, and reduce the residual per-spawn AV cost for the guards that *must* inspect every command.

## What was changed (applied, live after a Claude restart)

Hook registrations snapshot at SessionStart, so none of this is active until Claude restarts.

### `~/.claude/settings.json`
- `push-review-gate-guard.py` and `mr-stage-freshness-guard.py` are now `if`-gated to the relevant commands only:
  - push-review-gate → `Bash(git push:*)` and `Bash(git * push:*)`
  - mr-stage-freshness → `Bash(git push:*)`, `Bash(git * push:*)`, `Bash(glab mr create:*)`, `Bash(gh pr create:*)`
- Effect: `git log`/`status`/`diff`/`add`/`commit`, `cat`, `ls`, builds, tests, `python`, `npm`, `dotnet` match none of these patterns → zero spawns of these two guards.

### `CodeMaestro/.claude/settings.local.json`
- `guard-worktree-remove.sh` → gated to `Bash(git worktree remove:*)` / `Bash(git * worktree remove:*)` (+ `PowerShell(...)` variants).
- `guard-api-push-develop.sh` → gated to `Bash(git push:*)` / `Bash(git * push:*)` (+ `PowerShell(...)`).
- The PowerShell merge-guard that was missing its `if` was fixed (`PowerShell(git merge:*)`).

Both JSON files validated. Confirmed live in both files via grep on 2026-06-14.

## Decision — Windows Defender exclusions: PATH-ONLY (decided 2026-06-14)

The #1 remaining lever for the *irreducible* hooks (the guard-hooks core `guard_bash.py` must inspect every command and cannot be gated).

**Decision: path exclusions only — no process/interpreter exclusions.** The user chose the conservative option: capture most of the git-tree-walk win without weakening malware coverage on interpreters. To be run in an elevated PowerShell:

- **Path exclusions (APPROVED):** `~/.claude`, claude-tools (`C:\Users\gruku\Files\Claude\claude-tools`), CodeMaestro (`C:\Users\gruku\Files\Work\CodeMaestro`) — stop file-scan on git tree-walks in hot repos.
- **Process exclusions (REJECTED):** `python.exe`/`node.exe`/`bash.exe`/etc. were considered and **declined** — excluding interpreters from real-time scanning is a genuine reduction in AV coverage (malware favors living in interpreters); not worth the exposure.

```powershell
# Path exclusions only (run elevated)
'C:\Users\gruku\.claude',
'C:\Users\gruku\Files\Claude\claude-tools',
'C:\Users\gruku\Files\Work\CodeMaestro' |
  ForEach-Object { Add-MpPreference -ExclusionPath $_ }
Get-MpPreference | Select-Object -ExpandProperty ExclusionPath   # verify
```

## Deliberately NOT done

- **Did not gate the taskmaster plugin hooks** — already zero-subprocess on the hot path; gating would drop `git -C <path>` merge coverage for all users. Defender exclusions handle their residual cost instead.
- **Did not touch the guard-hooks core blocker or `run_hook.sh` launcher** — load-bearing; must see every command.

## Risks / open questions (for review)

- **`Bash(git * push:*)` mid-wildcard is best-effort.** It is meant to catch `git -C <path> push`, but the permission-rule matcher's handling of a wildcard between `git` and `push` is not certain to span an arbitrary `-C <path>`. If it doesn't match, the push guard silently stops firing on `git -C … push` — a *coverage loss*, not a false block. Must be verified post-restart; fallback is to widen the blocking guards to `Bash(git *)` (certain, slightly slower on git reads).
- **PowerShell `if` syntax is inferred.** The `PowerShell(...)` matcher form was inferred by analogy to `Bash(...)`. If the harness doesn't support it, the PowerShell-path guards either never fire (coverage loss) or always fire (no perf win). Must be verified by triggering a guard via the PowerShell tool once.
- **Fail-open posture.** If a gated guard misfires, the failure mode should be fail-open (command proceeds) per the launcher contract — confirm no gating change converted a fail-open into a fail-closed (accidental DENY).

## Verification protocol (post-restart — REQUIRED before considering this done)

1. **Read-path is quiet:** run `git status` / `git log` and confirm none of the four gated guards fire (no guard stderr).
2. **`git -C <path> push` still guarded:** `git -C "…/code-maestro-api" push --dry-run origin <feature-branch>` → guard stderr must still fire. If not, the `git * push:*` pattern isn't spanning the path → widen to `Bash(git *)` on the blocking guards.
3. **PowerShell `if` works:** trigger a develop-push (or worktree-remove) via the PowerShell tool once; if not caught, the inferred `PowerShell(...)` syntax failed → revert those matchers to ungated.
4. **Fail-open preserved:** force one gated guard to fire and error (e.g. a transient bad state); confirm the Bash command still proceeds (PreToolUse exits non-deny). A gating edit must never convert a fail-open guard into a fail-closed DENY.
5. **Defender (path-only, decided):** after running the path-exclusion block in an elevated shell, `Get-MpPreference | Select -ExpandProperty ExclusionPath` lists the three hot-repo paths. (No process exclusions expected — that option was declined.)

## Rollback

Fully reversible by hand — the change only *added* `if` fields to existing hook registrations. To revert a guard to always-fire, delete its `if` line. If a `git -C`/PowerShell guard shows coverage loss (verification 2-3), prefer widening the pattern over reverting. Recommend keeping a copy of the pre-change `settings.json` / `settings.local.json` blocks (these files are not version-controlled) so the exact prior state is recoverable.

## Done criteria

- Post-restart verification steps 1-3 pass (read-path quiet; push + worktree guards still fire on both `git -C` and PowerShell forms).
- Defender path-only exclusions applied in an elevated shell + verified (step 5). (Decision already made: path-only; process exclusions declined.)
- Any coverage loss found in steps 2-3 is repaired (widen pattern / revert matcher) before close.
