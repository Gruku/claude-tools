---
name: safe-worktree-removal
description: Use BEFORE running `git worktree remove`, `git worktree prune`, or any worktree cleanup on Windows or against worktrees that contain submodules or have long paths. Routes through the safe deinit-first procedure to prevent the dotfile-cascade incident where `--force` removal wipes top-level `.git/`, `.gitignore`, `.gitmodules`, `.env*`, `.github/`, `.vscode/`, `.ai/design/` in the PARENT checkout. Invoke when the user says "remove this worktree", "clean up worktrees", "delete the worktree", "prune worktrees", or when guard-hooks blocks a worktree-remove command.
---

# Safe Worktree Removal

Removing a git worktree on Windows can cascade-delete top-level dotfiles in the parent checkout when the worktree contains submodules or has paths near `MAX_PATH`. Confirmed in a 2026-05-19 incident; see `docs/reflect/2026-05-19-git-destruction-postmortem.md` in `claude-tools`.

## When to invoke this skill

- Any `git worktree remove <path>` command, force or not
- Any `git worktree prune` after a partial removal
- After a worktree-remove command was blocked by `guard-hooks`
- When the user asks to clean up `.worktrees/` directories
- After merging feature branches whose worktrees you want to delete

## The procedure

### Step 1 — Inspect the worktree

```bash
git -C <worktree-path> status
git -C <worktree-path> submodule status
ls -la <worktree-path>
```

Note:
- Does the worktree have a `.gitmodules` file at its root? (submodule cascade risk)
- Is the absolute path length near 200 characters? (MAX_PATH cascade risk)
- Are you currently `cd`'d INTO the worktree? (you must not be — `cd` to the parent first)

### Step 2 — Deinit submodules if any

If `git submodule status` returned any rows:

```bash
git -C <worktree-path> submodule deinit -f --all
```

This unhooks the submodule working tree from the worktree's `.git/modules/` without affecting the parent repo's submodule state.

### Step 3 — Remove the worktree (no `--force`)

```bash
git worktree remove <worktree-path>
```

If this succeeds, you're done.

### Step 4 — If step 3 fails

| Failure | Action |
|---|---|
| "working trees containing submodules cannot be moved or removed" | You skipped step 2. Go back to step 2. |
| "Filename too long" / Windows MAX_PATH error | **STOP.** Do NOT retry with `--force`. Do NOT `rm -rf`. Leave the worktree dir on disk. Read step 5. |
| "is not a working tree" | The worktree metadata is gone but the dir survived. Run `git worktree prune` from the parent repo to clean the registry; the dir on disk can be deleted manually with `rm -rf` ONLY after `git worktree list` confirms it is no longer tracked. |
| "modified or untracked files" | Commit, stash, or copy out the changes first. Then retry step 3. |

### Step 5 — Recovering from a MAX_PATH failure

1. **Stop all further git operations on this checkout.** Even read-only `git status` is fine, but never run another `git worktree` subcommand here until step 6 confirms the parent is healthy.
2. From a NEW shell, immediately verify the parent checkout is intact:
   ```bash
   ls -la <parent-checkout-root>
   ```
   Look for `.git/`, `.gitignore`, `.gitmodules`, `.env*`, `.github/`, `.vscode/`. If any of these are missing, **the cascade has already started** — read the postmortem before doing anything else.
3. If the parent is intact, enable long-path support globally and retry from a fresh shell:
   ```bash
   git config --global core.longpaths true
   ```
   Then re-run step 3 from the parent's location, not from inside `.worktrees/`.
4. Alternatively, move the worktree to a shorter path (`mv <worktree-path> /short/path` from the OS, then `git worktree repair`) before retrying.

## Anti-patterns

| Thought | Reality |
|---|---|
| "I'll just add `--force`" | Confirmed-destructive on Windows. Blocked by `guard-hooks`. |
| "I'll fall back to `rm -rf`" | Same cascade as `--force` on Windows. Blocked by `guard-hooks`. |
| "I'll chain three removes with `&&`" | `&&` does not short-circuit through `| tail` and a partial failure runs silently. One worktree at a time, no line filter. |
| "I'll run from inside the worktree" | Many failure modes lock the cwd. Always `cd` to the parent repo first. |
| "I'll delete the orphaned dir with `rm -rf`" | Only after `git worktree list` confirms the dir is no longer tracked, AND only from outside the dir, AND on a path with no submodules left. When in doubt, ask the user. |

## What the guard-hooks plugin enforces

- **HARD BLOCK** (no approval bypass): direct write/delete of `.git/` from Bash (any verb).
- **APPROVAL-GATED**:
  - `git worktree remove --force` / `-f` (Windows cascade)
  - `git worktree remove <path>` where the target contains `.gitmodules` (submodule pre-flight)
  - Any destructive git op piped into `| tail`/`| head`/`| grep`/`| awk`/`| sed`/`| wc`/`| cut` (failure-masking)
- A SessionStart banner reminds Claude of these rules at the start of every session.

If the hook blocks a command, read the block message — it includes the recovery step for that specific failure.
