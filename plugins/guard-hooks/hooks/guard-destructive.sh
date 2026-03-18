#!/bin/bash
# guard-destructive.sh — PreToolUse hook for Bash commands
# Blocks destructive operations that could cause data loss.
# Exit 2 = block (stderr sent to Claude as feedback)
# Exit 0 = allow
#
# To approve a blocked command, the USER (not the LLM) must run in another terminal:
#   touch ~/.claude/guard-approve
# The approval is valid for 60 seconds and consumed on use.

APPROVE_FILE="$HOME/.claude/guard-approve"

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if [ -z "$COMMAND" ]; then
  exit 0
fi

# --- Block LLM from creating the approval file ---
if echo "$COMMAND" | grep -qE 'guard-approve'; then
  cat >&2 <<'EOF'
⛔ GUARD HOOK BLOCKED THIS COMMAND.
Reason: You cannot create or manipulate the guard approval file. Only the user can do this manually.
EOF
  exit 2
fi

# --- Time-limited user approval ---
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
      # Consume the approval (one-time use)
      rm -f "$APPROVE_FILE"
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

ACTION REQUIRED: You MUST use the AskUserQuestion tool to ask the user for explicit permission.
Tell the user: "To approve, run this in another terminal: touch ~/.claude/guard-approve"
Then retry the ORIGINAL command (without any override prefix).
Do NOT attempt to create the approval file yourself.
Do NOT re-run automatically without user approval.
EOF
  exit 2
}

# --- File deletion ---
if echo "$COMMAND" | grep -qEi '(^|\s|&&|\|)(rm\s+-rf|rm\s+-r\s|rm\s+--recursive|rmdir|shred|unlink)\s'; then
  block "Destructive file deletion ('$COMMAND'). Use 'git worktree remove' for worktrees."
fi

# --- Git push guards (force push, push to main/master, bare push) ---
# Extract just the git push portion (before any && or | or ;) to avoid
# false positives from words like "main/master" appearing in commit messages.
PUSH_CMD=$(echo "$COMMAND" | grep -oE 'git\s+push(\s+[^;&|]+)?' | head -1)
if [ -n "$PUSH_CMD" ]; then
  if echo "$PUSH_CMD" | grep -qE '(-f|--force)'; then
    block "Force push detected. This can overwrite remote history."
  fi
  if echo "$PUSH_CMD" | grep -qE '\b(main|master)\b'; then
    block "Pushing directly to main/master. Create a PR instead."
  fi
  # Bare `git push` with no args — check current branch
  if echo "$PUSH_CMD" | grep -qE 'git\s+push\s*$'; then
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
