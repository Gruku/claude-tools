#!/bin/bash
# guard-edits.sh — PreToolUse hook for Edit/Write operations
# Blocks writes to sensitive files.
# Exit 2 = block (stderr sent to Claude as feedback)
# Exit 0 = allow

APPROVE_FILE="$HOME/.claude/guard-approve"

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

# --- Time-limited user approval (shared with guard-destructive.sh) ---
check_approval() {
  if [ -f "$APPROVE_FILE" ]; then
    if [ "$(uname)" = "Linux" ] || [ "$(uname)" = "Darwin" ]; then
      FILE_AGE=$(( $(date +%s) - $(stat -c %Y "$APPROVE_FILE" 2>/dev/null || stat -f %m "$APPROVE_FILE" 2>/dev/null) ))
    else
      FILE_AGE=$(( $(date +%s) - $(stat -c %Y "$APPROVE_FILE" 2>/dev/null || echo 0) ))
    fi
    if [ "$FILE_AGE" -le 60 ] 2>/dev/null; then
      rm -f "$APPROVE_FILE"
      return 0
    fi
    rm -f "$APPROVE_FILE"
  fi
  return 1
}

# block_hard: unconditional block, no approval bypass (guard-approve file, git internals)
block_hard() {
  cat >&2 <<EOF
⛔ GUARD HOOK BLOCKED THIS EDIT.
Reason: $1
File: $FILE_PATH

This file cannot be written by Claude under any circumstances.
EOF
  exit 2
}

# block: approvable block — checks for user approval before blocking
block() {
  if check_approval; then
    exit 0
  fi

  cat >&2 <<EOF
⛔ GUARD HOOK BLOCKED THIS EDIT.
Reason: $1
File: $FILE_PATH

ACTION REQUIRED: You MUST use the AskUserQuestion tool to ask the user for explicit permission before proceeding.
Do NOT re-run automatically. Do NOT assume approval.
If the user denies or does not respond, do NOT write to this file.
EOF
  exit 2
}

# --- Guard approval file (only the user can create this) ---
# Match only the actual approval file at ~/.claude/guard-approve, not source files
if echo "$FILE_PATH" | grep -qE '\.claude/guard-approve$'; then
  block_hard "You cannot create or modify the guard approval file. Only the user can do this manually."
fi

# --- Environment / secrets files ---
# Allow template/example env files (they contain only placeholders, not real secrets)
if echo "$FILE_PATH" | grep -qEi '\.(example|sample|template|defaults)$'; then
  : # safe template file — fall through
elif echo "$FILE_PATH" | grep -qEi '(\.env$|\.env\.|credentials|secrets|\.pem$|\.key$|id_rsa)'; then
  block "This looks like a sensitive file containing secrets."
fi

# --- Lock files (should not be hand-edited) ---
if echo "$FILE_PATH" | grep -qEi '(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|uv\.lock)$'; then
  block "Lockfile detected. Use the package manager instead of editing directly."
fi

# --- Git internals ---
if echo "$FILE_PATH" | grep -qE '\.git/'; then
  block_hard "Cannot write to git internals."
fi

exit 0
