#!/bin/bash
# guard-destructive.sh — PreToolUse hook for Bash commands
# Blocks destructive operations that could cause data loss.
# Exit 2 = block (stderr sent to Claude as feedback)
# Exit 0 = allow
#
# Set GUARD_OVERRIDE=1 in the command to bypass after user approval.
# e.g.: GUARD_OVERRIDE=1 git push origin master

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if [ -z "$COMMAND" ]; then
  exit 0
fi

# --- User-approved override ---
if echo "$COMMAND" | grep -qE '(^|\s)GUARD_OVERRIDE=1(\s|$)'; then
  exit 0
fi

block() {
  cat >&2 <<EOF
⛔ GUARD HOOK BLOCKED THIS COMMAND.
Reason: $1
Command: $COMMAND

ACTION REQUIRED: You MUST use the AskUserQuestion tool to ask the user for explicit permission before proceeding. Do NOT re-run automatically. Do NOT assume approval.
If the user explicitly approves, re-run the command with GUARD_OVERRIDE=1 prefixed. Example: GUARD_OVERRIDE=1 <original command>
If the user denies or does not respond, do NOT run this command.
EOF
  exit 2
}

# --- File deletion ---
if echo "$COMMAND" | grep -qEi '(^|\s|&&|\|)(rm\s+-rf|rm\s+-r\s|rm\s+--recursive|rmdir|shred|unlink)\s'; then
  block "Destructive file deletion ('$COMMAND'). Use 'git worktree remove' for worktrees."
fi

# --- Git force push ---
if echo "$COMMAND" | grep -qE 'git\s+push\s+.*(-f|--force)'; then
  block "Force push detected. This can overwrite remote history."
fi

# --- Git push to main/master (explicit or implicit via bare `git push`) ---
if echo "$COMMAND" | grep -qE 'git\s+push\s+.*(main|master)(\s|$)'; then
  block "Pushing directly to main/master. Create a PR instead."
fi
if echo "$COMMAND" | grep -qE 'git\s+push\s*$'; then
  CURRENT_BRANCH=$(git branch --show-current 2>/dev/null)
  if [ "$CURRENT_BRANCH" = "main" ] || [ "$CURRENT_BRANCH" = "master" ]; then
    block "Bare 'git push' on $CURRENT_BRANCH. Create a PR instead."
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
