#!/bin/bash
# guard-edits.sh — PreToolUse hook for Edit/Write operations
# Blocks writes to sensitive files.
# Exit 2 = block (stderr sent to Claude as feedback)
# Exit 0 = allow

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

block() {
  cat >&2 <<EOF
⛔ GUARD HOOK BLOCKED THIS EDIT.
Reason: $1
File: $FILE_PATH

ACTION REQUIRED: You MUST use the AskUserQuestion tool to ask the user for explicit permission before proceeding. Do NOT re-run automatically. Do NOT assume approval.
If the user denies or does not respond, do NOT write to this file.
EOF
  exit 2
}

# --- Guard approval file (only the user can create this) ---
# Match only the actual approval file at ~/.claude/guard-approve, not source files
if echo "$FILE_PATH" | grep -qE '\.claude/guard-approve$'; then
  block "You cannot create or modify the guard approval file. Only the user can do this manually."
fi

# --- Environment / secrets files ---
if echo "$FILE_PATH" | grep -qEi '(\.env$|\.env\.|credentials|secrets|\.pem$|\.key$|id_rsa)'; then
  block "This looks like a sensitive file containing secrets."
fi

# --- Lock files (should not be hand-edited) ---
if echo "$FILE_PATH" | grep -qEi '(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|uv\.lock)$'; then
  block "Lockfile detected. Use the package manager instead of editing directly."
fi

# --- Git internals ---
if echo "$FILE_PATH" | grep -qE '\.git/'; then
  block "Cannot write to git internals."
fi

exit 0
