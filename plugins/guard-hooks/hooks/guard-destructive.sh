#!/bin/bash
# guard-destructive.sh — PreToolUse hook for Bash commands
# Blocks destructive operations that could cause data loss.
# Exit 2 = block (stderr sent to Claude as feedback)
# Exit 0 = allow
#
# Approval flow (shared with the rest of guard-hooks):
#   The AI calls AskUserQuestion with labels "Approve"/"Deny". On "Approve",
#   the PostToolUse hook on AskUserQuestion creates ~/.claude/guard-approve
#   automatically. The user can also type "approve" as a chat message
#   (UserPromptSubmit hook).
#
# Lifecycle: the approval is valid for 60 seconds. PreToolUse hooks only
# CHECK the file's freshness — they don't delete it on use. The PostToolUse
# hook (consume-approval.sh) deletes the file after the tool actually runs,
# so a denial at the standard permission layer leaves the approval intact
# for a retry within the window.

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# Per-session approval token: keyed by harness session_id so concurrent
# Claude Code sessions on the same host don't trample each other's approvals.
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)
[ -z "$SESSION_ID" ] && SESSION_ID="default"
APPROVE_FILE="$HOME/.claude/guard-approve-$SESSION_ID"

# Hook's reported cwd of the calling shell, used to resolve relative paths
# during the worktree-removal pre-flight (P3 in the postmortem). Optional —
# absent in older hook payloads.
HOOK_CWD=$(echo "$INPUT" | jq -r '.cwd // empty' 2>/dev/null)

# Debug logging — uncomment to diagnose hook bypass issues
# LOG_FILE="$HOME/.claude/guard-debug.log"
# echo "[$(date '+%Y-%m-%d %H:%M:%S')] COMMAND: $COMMAND" >> "$LOG_FILE"

if [ -z "$COMMAND" ]; then
  exit 0
fi

# --- Block LLM from creating the approval file ---
# Detect actual mutations (touch / echo > / cp / mv / Set-Content / etc.)
# whose target ends with the guard-approve token name. A bare mention of
# the literal string in a commit message or an `ls` arg is fine.
if echo "$COMMAND" | grep -qE '(touch|echo[^|;&]*>|cat[^|;&]*>|cp|mv|Set-Content|Add-Content|Out-File|New-Item)[^|;&]*guard-approve(-[A-Za-z0-9_-]+)?($|[[:space:]"'"'"'])'; then
  cat >&2 <<'EOF'
⛔ GUARD HOOK BLOCKED THIS COMMAND.
Reason: You cannot create or manipulate the guard approval file. Only the user can do this manually.
EOF
  exit 2
fi

# --- Time-limited user approval ---
# Approval is NOT consumed here. The PostToolUse hook (consume-approval.sh)
# deletes the file after the tool actually runs, so a denial at the standard
# permission layer leaves the approval intact for a retry within the window.
# Expired tokens ARE removed here (cleanup). Stale tokens we couldn't stat
# are left in place so the user's later attempt still works.
check_approval() {
  if [ -f "$APPROVE_FILE" ]; then
    # Check if file was modified within the last 60 seconds
    if [ "$(uname)" = "Linux" ] || [ "$(uname)" = "Darwin" ]; then
      FILE_AGE=$(( $(date +%s) - $(stat -c %Y "$APPROVE_FILE" 2>/dev/null || stat -f %m "$APPROVE_FILE" 2>/dev/null) ))
    else
      # Windows (Git Bash / MSYS2) — stat -c works
      FILE_AGE=$(( $(date +%s) - $(stat -c %Y "$APPROVE_FILE" 2>/dev/null || echo 0) ))
    fi
    if [ "$FILE_AGE" -le 60 ] 2>/dev/null; then
      return 0
    fi
    # Expired — clean up
    rm -f "$APPROVE_FILE"
  fi
  return 1
}

block() {
  # Check for valid user approval before blocking
  if check_approval; then
    exit 0
  fi

  cat >&2 <<EOF
⛔ GUARD HOOK BLOCKED THIS COMMAND.
Reason: $1
Command: $COMMAND

ACTION REQUIRED: Use the AskUserQuestion tool with EXACTLY this shape:
  question: one short sentence describing the destructive action
  options (use these labels verbatim — do not rename, translate, or add more):
    - label: "Approve"  description: "Run the command as shown"
    - label: "Deny"     description: "Cancel; do not run the command"

After the user responds:
  - "Approve" → rerun the ORIGINAL command unchanged
  - "Deny" or no response → do NOT run the command

Only the exact label "Approve" is recognized as authorization.
Do NOT re-run automatically. Do NOT create the approval file yourself.
EOF
  exit 2
}

# --- File deletion ---
if echo "$COMMAND" | grep -qEi '(^|\s|&&|\|)(rm\s+-rf|rm\s+-r\s|rm\s+--recursive|rmdir|shred|unlink)\s'; then
  block "Destructive file deletion ('$COMMAND'). Use 'git worktree remove' for worktrees."
fi

# --- Git push guards (force push, push to main/master, bare push) ---
# Extract the git push portion, accounting for global flags like -C <path>
# between 'git' and 'push'. Stops at && | or ; to avoid false positives
# from words like "main/master" appearing in commit messages.
# Uses two patterns: one for flags-with-args (like -C path), one for simpler forms.
PUSH_CMD=$(echo "$COMMAND" | grep -oE 'git\s+((-[a-zA-Z]+\s+\S+|--[a-z-]+)\s+)*push(\s+[^;&|]+)?' | head -1)
if [ -n "$PUSH_CMD" ]; then
  # Extract just the args after "push" for cleaner matching
  PUSH_ARGS=$(echo "$PUSH_CMD" | sed 's/.*push//')
  if echo "$PUSH_ARGS" | grep -qE '(-f|--force)'; then
    block "Force push detected. This can overwrite remote history."
  fi

  # Protected-branch detection.
  # The previous implementation matched main/master ANYWHERE in PUSH_ARGS,
  # which false-positived on `git push origin master:feature-branch` (master
  # is the SOURCE; feature-branch is the destination). Walk the positional
  # args, drop flags and the remote name, and check only the destination
  # side of each refspec — `[+]<src>[:<dst>]` -> dst is right of colon, or
  # the whole ref if no colon. Bare deletes (`:dst`) still flag if dst is
  # protected. `+` force-prefix is stripped before checking.
  protected_dst_hit=0
  saw_remote=0
  # Iterate PUSH_ARGS as space-separated tokens.
  for token in $PUSH_ARGS; do
    case "$token" in
      -*) continue ;;            # flag — skip
    esac
    if [ "$saw_remote" = "0" ]; then
      saw_remote=1                # first non-flag positional is the remote
      continue
    fi
    refspec="${token#+}"          # strip force prefix
    if echo "$refspec" | grep -q ':'; then
      dst="${refspec##*:}"
    else
      dst="$refspec"
    fi
    dst="${dst#refs/heads/}"
    if [ "$dst" = "main" ] || [ "$dst" = "master" ]; then
      protected_dst_hit=1
      break
    fi
  done
  if [ "$protected_dst_hit" = "1" ]; then
    block "Pushing to main/master. Create a PR instead."
  fi

  # Bare push (no args after "push") — check current branch
  if [ -z "$(echo "$PUSH_ARGS" | tr -d '[:space:]')" ]; then
    CURRENT_BRANCH=$(git branch --show-current 2>/dev/null)
    if [ "$CURRENT_BRANCH" = "main" ] || [ "$CURRENT_BRANCH" = "master" ]; then
      block "Bare 'git push' on $CURRENT_BRANCH. Create a PR instead."
    fi
  fi
fi

# --- Git reset --hard ---
if echo "$COMMAND" | grep -qE 'git\s+reset\s+--hard'; then
  block "'git reset --hard' discards uncommitted work. Commit or stash first."
fi

# --- Git clean (deletes untracked files) ---
if echo "$COMMAND" | grep -qE 'git\s+clean\s+-[a-zA-Z]*f'; then
  block "'git clean -f' permanently deletes untracked files."
fi

# --- Git worktree remove --force (Windows cascade hazard) ---
# Observed 2026-05-19 in the CodeMaestro monorepo: 'git worktree remove --force'
# on a worktree containing submodules with paths near Windows MAX_PATH did NOT
# just remove the worktree — it cascade-deleted top-level dot-prefixed entries
# in the PARENT checkout (.git/, .gitignore, .gitmodules, .dockerignore, .env*,
# .github/, .vscode/, .ai/design/, contents of .config/). All branches,
# reflogs, stashes, and unpushed commits were lost.
#
# The non-force version exits cleanly with "working trees containing submodules
# cannot be moved or removed" — that is the correct trigger to run
# 'git submodule deinit -f <name>' inside the worktree, NOT to escalate to
# --force. We block the --force form here so an approval is required.
if echo "$COMMAND" | grep -qE 'git[[:space:]]+([^|;&]*[[:space:]])?worktree[[:space:]]+remove'; then
  # Isolate the portion from 'worktree remove' to the next chain operator so a
  # later '--force' flag in an unrelated chained command doesn't false-positive.
  REMOVE_SEG=$(echo "$COMMAND" | grep -oE 'worktree[[:space:]]+remove[^;&|]*' | head -1)
  # Match --force or short -f / -fq / -qf style flags. Flag-token boundary
  # (whitespace or start) prevents matching '-f' embedded in a path like
  # '.worktrees/desktop-app-258'.
  if echo "$REMOVE_SEG" | grep -qE '(^|[[:space:]])(--force|-[a-zA-Z]*f[a-zA-Z]*)([[:space:]]|=|$)'; then
    block "'git worktree remove --force' can cascade-delete top-level dotfiles in the PARENT checkout (.git/, .gitignore, .gitmodules, .env*, .github/, .vscode/, …) when the worktree contains submodules or has long paths on Windows. Confirmed in a 2026-05-19 incident. Try 'git -C <worktree> submodule deinit -f <submodule>' first, then 'git worktree remove' without --force."
  fi

  # --- Submodule pre-flight ---
  # Even without --force, a worktree containing submodules fails partway
  # through removal and leaves the parent in a fragile state. The recovery
  # path is the same: deinit submodules from inside the worktree first.
  # We approval-gate (not hard-block) — there are legitimate cases on
  # non-Windows or after the user has already deinit'd.
  #
  # Extract the first non-flag positional after 'remove'. Resolve relative
  # paths against the hook's reported cwd. If the directory exists and
  # contains a .gitmodules file at its root, treat that as the cascade
  # precondition.
  TARGET=""
  # Pull tokens after 'remove' up to chain operator, then walk them.
  POST_REMOVE=$(echo "$REMOVE_SEG" | sed -E 's/^worktree[[:space:]]+remove[[:space:]]+//')
  for token in $POST_REMOVE; do
    case "$token" in
      -*) continue ;;
      *) TARGET="$token"; break ;;
    esac
  done
  if [ -n "$TARGET" ]; then
    # Strip surrounding quotes if any.
    TARGET="${TARGET#\"}"; TARGET="${TARGET%\"}"
    TARGET="${TARGET#\'}"; TARGET="${TARGET%\'}"
    ABS_TARGET="$TARGET"
    case "$TARGET" in
      /*|?:[/\\]*) : ;;  # absolute (POSIX or Windows drive-letter)
      *) [ -n "$HOOK_CWD" ] && ABS_TARGET="$HOOK_CWD/$TARGET" ;;
    esac
    if [ -d "$ABS_TARGET" ] && [ -e "$ABS_TARGET/.gitmodules" ]; then
      block "Worktree '$TARGET' contains submodules ('.gitmodules' present). Even without --force, removal will fail partway and can leave the parent in a fragile state. Run 'git -C \"$TARGET\" submodule deinit -f --all' first, then retry 'git worktree remove $TARGET'."
    fi
  fi
fi

# --- Git branch -D (force delete) ---
if echo "$COMMAND" | grep -qE 'git\s+branch\s+-D\s'; then
  block "'git branch -D' force-deletes a branch. Use 'git branch -d' (safe delete)."
fi

# --- Git checkout/restore that discards all changes ---
if echo "$COMMAND" | grep -qE 'git\s+(checkout|restore)\s+\.\s*$'; then
  block "This discards all uncommitted changes. Commit or stash first."
fi

# --- Git stash clear / drop all ---
if echo "$COMMAND" | grep -qE 'git\s+stash\s+(clear|drop\s+--all)'; then
  block "This destroys stash entries permanently."
fi

# --- Windows destructive commands ---
if echo "$COMMAND" | grep -qEi '(^|\s|&&|\|)(del\s+/[sfq]|rd\s+/s|format\s|diskpart)'; then
  block "Destructive Windows command detected."
fi

# --- Failure-masking pattern: destructive git op piped through tail/head/grep ---
# Observed 2026-05-19: `git worktree remove --force A 2>&1 | tail -2 \
#   && git worktree remove --force B 2>&1 | tail -2 \
#   && git worktree remove --force C 2>&1 | tail -2`
# The 'tail -2' overwrites the upstream exit code, so the `&&` chain does NOT
# short-circuit on the first command's failure — all three run regardless, and
# the truncated output hides the cascade in progress.
#
# We approval-gate any mutating git subcommand piped into a line-filter
# (tail/head/grep/awk/sed/wc/cut). This forces the AI to either run the
# command without the filter (so it sees the real output) or to ask the user
# for explicit approval to mask the failure.
DESTRUCTIVE_GIT_RE='git[[:space:]]+([^|;&]*[[:space:]])?(worktree[[:space:]]+remove|push|reset|clean|branch[[:space:]]+-D|stash[[:space:]]+(clear|drop)|rebase|merge|submodule[[:space:]]+deinit)'
LINE_FILTER_RE='\|[[:space:]]*(tail|head|grep|awk|sed|wc|cut)([[:space:]]|$)'
if echo "$COMMAND" | grep -qE "$DESTRUCTIVE_GIT_RE" && \
   echo "$COMMAND" | grep -qE "$LINE_FILTER_RE"; then
  block "Destructive git operation piped into a line filter (tail/head/grep/awk/sed/wc/cut). This masks the upstream exit code so '&&' chains do not short-circuit on failure — a partial-failure cascade can run silently. Re-run without the filter so the real output is visible."
fi

exit 0
