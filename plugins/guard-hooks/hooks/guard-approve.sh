#!/bin/bash
# guard-approve.sh — UserPromptSubmit hook
# When the user types "approve" (case-insensitive), creates a time-limited
# approval file that guard-destructive.sh will consume on the next blocked command.
#
# This hook runs on USER input only — the LLM cannot trigger it.

INPUT=$(cat)
PROMPT=$(echo "$INPUT" | jq -r '.prompt // empty')

if [ -z "$PROMPT" ]; then
  exit 0
fi

# Per-session token: keyed by harness session_id so concurrent sessions don't
# trample each other's approvals. Falls back to "default" if absent.
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)
[ -z "$SESSION_ID" ] && SESSION_ID="default"

# Check if the user's message is an approval (just "approve", optionally with whitespace)
if echo "$PROMPT" | grep -qiE '^\s*approve\s*$'; then
  APPROVE_FILE="$HOME/.claude/guard-approve-$SESSION_ID"
  mkdir -p "$(dirname "$APPROVE_FILE")"
  touch "$APPROVE_FILE"
  echo "Guard approval granted. The next blocked command will be allowed (valid for 60 seconds)."
  exit 0
fi

exit 0
