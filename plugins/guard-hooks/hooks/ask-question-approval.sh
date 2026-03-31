#!/bin/bash
# ask-question-approval.sh — PostToolUse hook for AskUserQuestion
# When the user answers "approve" (case-insensitive) via AskUserQuestion,
# creates a time-limited approval file that guard-destructive.sh will consume.
#
# This complements guard-approve.sh (UserPromptSubmit) so approval works
# regardless of whether the user types directly or answers a question.
#
# PostToolUse payload uses .tool_response (not .tool_output).
# For AskUserQuestion, tool_response may be:
#   - A string directly
#   - An object with .answers (map of question -> answer)
# We flatten all values and check if any contain "approve".

INPUT=$(cat)

# Extract all string values from tool_response (handles both flat strings and nested objects)
ANSWER=$(echo "$INPUT" | jq -r '
  .tool_response //
  .tool_output //
  empty |
  if type == "string" then .
  elif type == "object" then [.. | strings] | join(" ")
  else tostring
  end
')

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
