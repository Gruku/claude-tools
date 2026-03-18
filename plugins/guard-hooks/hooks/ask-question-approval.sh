#!/bin/bash
# ask-question-approval.sh — PostToolUse hook for AskUserQuestion
# When the user answers "approve" (case-insensitive) via AskUserQuestion,
# creates a time-limited approval file that guard-destructive.sh will consume.
#
# This complements guard-approve.sh (UserPromptSubmit) so approval works
# regardless of whether the user types directly or answers a question.

INPUT=$(cat)
ANSWER=$(echo "$INPUT" | jq -r '.tool_output // empty')

if [ -z "$ANSWER" ]; then
  exit 0
fi

# Check if the user's answer is an approval
if echo "$ANSWER" | grep -qiE '(^|\s)approve(\s|$)'; then
  APPROVE_FILE="$HOME/.claude/guard-approve"
  mkdir -p "$(dirname "$APPROVE_FILE")"
  touch "$APPROVE_FILE"
fi

exit 0
