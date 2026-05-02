#!/bin/bash
# guard-database.sh — PreToolUse hook for Bash commands targeting databases.
# Two-tier severity: HARD (user-approval only) and SOFT (AI may self-acknowledge).
# Exit 2 = block (stderr to model). Exit 0 = allow.

APPROVE_FILE="$HOME/.claude/guard-approve"   # user-only
ACK_FILE="$HOME/.claude/guard-ack"           # AI-allowed

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if [ -z "$COMMAND" ]; then
  exit 0
fi

# --- AI must not create the user-only approval file ---
if echo "$COMMAND" | grep -qE 'guard-approve'; then
  cat >&2 <<'EOF'
GUARD HOOK BLOCKED THIS COMMAND.
Reason: You cannot create or manipulate the user-only approval file. Only the user may do this manually.
EOF
  exit 2
fi

# --- Time-limited file consumption (60s TTL, one-shot) ---
file_recent() {
  local f="$1"
  [ -f "$f" ] || return 1
  local age
  age=$(( $(date +%s) - $(stat -c %Y "$f" 2>/dev/null || stat -f %m "$f" 2>/dev/null || echo 0) ))
  if [ "$age" -le 60 ] 2>/dev/null; then
    rm -f "$f"
    return 0
  fi
  rm -f "$f"
  return 1
}

check_user_approval() { file_recent "$APPROVE_FILE"; }
check_ai_ack()        { file_recent "$ACK_FILE"; }

block_hard() {
  if check_user_approval; then exit 0; fi
  cat >&2 <<EOF
GUARD HOOK BLOCKED THIS COMMAND (HARD).
Reason: $1
Recovery: $2
Command: $COMMAND

ACTION REQUIRED: This is a destructive database operation. Use AskUserQuestion with:
  options:
    - label: "Approve"  description: "Run the command as shown"
    - label: "Deny"     description: "Cancel"
On "Approve", the USER must run \`touch ~/.claude/guard-approve\` in another terminal, then you re-run the command. You may NOT create that file yourself.
EOF
  exit 2
}

block_soft() {
  if check_user_approval || check_ai_ack; then exit 0; fi
  cat >&2 <<EOF
GUARD HOOK BLOCKED THIS COMMAND (SOFT).
Reason: $1
Recovery: $2
Command: $COMMAND

DESTRUCTIVE DB OPERATION REMINDER:
  - Data loss from this command is scoped but real.
  - Verify you intend exactly this scope (table, collection, container, volume).
  - If a backup matters here, take one before proceeding.

To proceed: \`touch ~/.claude/guard-ack\` then re-run this exact command.
The ack is one-shot and expires in 60 seconds.
EOF
  exit 2
}

# --- pattern matchers (filled in by later tasks) ---

exit 0
