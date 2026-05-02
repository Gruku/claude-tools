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

# --- SQL schema destruction ---
# Case-insensitive match anywhere in the command string.
if echo "$COMMAND" | grep -qiE 'DROP[[:space:]]+(DATABASE|SCHEMA)\b'; then
  block_hard "DROP DATABASE/SCHEMA detected — entire database/schema removal." \
             "Restore from a recent dump: pg_dump / mysqldump / .dump for SQLite."
fi
if echo "$COMMAND" | grep -qiE 'DROP[[:space:]]+TABLE\b'; then
  block_soft "DROP TABLE detected — table and all its data will be removed." \
             "If you have a recent dump, restore via psql -f / mysql < / sqlite3 .read."
fi
if echo "$COMMAND" | grep -qiE '\bTRUNCATE\b'; then
  block_soft "TRUNCATE detected — all rows in the table will be removed." \
             "Wrap in BEGIN; ... ROLLBACK; first to test, or take a dump."
fi

# --- Unbounded DELETE / UPDATE (no WHERE before terminator) ---
# Best-effort: matches DELETE FROM <table> ... ; or end-of-string,
# with no WHERE keyword between FROM/SET and the terminator.
if echo "$COMMAND" | grep -qiE 'DELETE[[:space:]]+FROM[[:space:]]+[a-zA-Z_][a-zA-Z0-9_."]*[[:space:]]*(;|"|$)'; then
  if ! echo "$COMMAND" | grep -qiE 'DELETE[[:space:]]+FROM[[:space:]]+[^;"]*\bWHERE\b'; then
    block_soft "Unbounded DELETE detected — every row in the table will be removed." \
               "Add a WHERE clause, or wrap in BEGIN; ... ROLLBACK; to verify scope."
  fi
fi
if echo "$COMMAND" | grep -qiE 'UPDATE[[:space:]]+[a-zA-Z_][a-zA-Z0-9_."]*[[:space:]]+SET\b'; then
  if ! echo "$COMMAND" | grep -qiE 'UPDATE[[:space:]]+[^;"]*\bWHERE\b'; then
    block_soft "Unbounded UPDATE detected — every row in the table will be modified." \
               "Add a WHERE clause, or wrap in BEGIN; ... ROLLBACK; to verify scope."
  fi
fi

# --- Mongo destructive ops ---
if echo "$COMMAND" | grep -qE '\bdropDatabase[[:space:]]*\('; then
  block_hard "Mongo dropDatabase() — entire database removed." \
             "Restore from a mongodump (mongorestore --drop)."
fi
if echo "$COMMAND" | grep -qE '\.drop[[:space:]]*\([[:space:]]*\)'; then
  block_soft "Mongo collection .drop() — collection and all its documents removed." \
             "Restore the collection from mongodump if needed."
fi
if echo "$COMMAND" | grep -qE 'deleteMany[[:space:]]*\([[:space:]]*\{[[:space:]]*\}[[:space:]]*\)'; then
  block_soft "Mongo deleteMany({}) — every document in the collection removed." \
             "Use a non-empty filter, or take a mongodump first."
fi

# --- Redis nukes ---
if echo "$COMMAND" | grep -qiE '\bredis-cli\b[^|;&]*\bflushall\b'; then
  block_hard "Redis FLUSHALL — every key in every database wiped, cluster-wide." \
             "If a snapshot exists, restore via SAVE/BGSAVE artifacts and a restart."
fi
if echo "$COMMAND" | grep -qiE '\bredis-cli\b[^|;&]*\bflushdb\b'; then
  block_soft "Redis FLUSHDB — every key in the selected database wiped." \
             "If a snapshot exists, restore via SAVE/BGSAVE artifacts."
fi

exit 0
