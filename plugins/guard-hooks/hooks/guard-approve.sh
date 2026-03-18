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

# Check if the user's message is an approval (just "approve", optionally with whitespace)
if echo "$PROMPT" | grep -qiE '^\s*approve\s*$'; then
  APPROVE_FILE="$HOME/.claude/guard-approve"
  mkdir -p "$(dirname "$APPROVE_FILE")"
  touch "$APPROVE_FILE"
  echo "Guard approval granted. The next blocked command will be allowed (valid for 60 seconds)."
  exit 0
fi

exit 0
