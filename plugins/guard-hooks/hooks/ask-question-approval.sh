#!/bin/bash
# ask-question-approval.sh — PostToolUse hook for AskUserQuestion
# Creates a time-limited approval file when the user picks the "Approve" option.
#
# Protocol: guard-destructive.sh and guard-edits.sh instruct the LLM (via their
# block messages) to call AskUserQuestion with exactly two labels — "Approve"
# and "Deny". This hook only recognizes the literal "Approve" label. Any other
# answer (including free-form text, "Deny", or unrelated AskUserQuestion calls
# that don't follow the protocol) is ignored — no approval file is created.
#
# Strict matching is intentional: the block message dictates the question shape,
# so we don't have to guess whether a natural-language response is affirmative.
#
# PostToolUse payload uses .tool_response (not .tool_output).
# For AskUserQuestion, tool_response may be:
#   - A string directly
#   - An object with .answers (map of question -> answer)
# We flatten all values and check if any equal "Approve".

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

# Strict match: the answer must be exactly "Approve" (case-insensitive) as
# its own token. Anything else — "Deny", free-form text, unrelated AskUserQuestion
# responses — is ignored. The guard block messages dictate this label, so if the
# LLM followed the protocol the answer will be exactly "Approve".
if echo "$ANSWER" | grep -qiE '^[[:space:]]*approve([[:space:]:,.!?—-]|$)'; then
  APPROVE_FILE="$HOME/.claude/guard-approve"
  mkdir -p "$(dirname "$APPROVE_FILE")"
  touch "$APPROVE_FILE"
fi

exit 0
