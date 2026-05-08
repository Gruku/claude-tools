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

exit 0
