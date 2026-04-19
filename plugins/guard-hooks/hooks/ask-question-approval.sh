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
# PostToolUse payload for AskUserQuestion has tool_response with BOTH:
#   - .questions — the question spec, including option labels like "Approve"/"Deny"
#   - .answers   — a map of question text -> the label the user picked
#
# We MUST only inspect .answers values. A naive flatten of tool_response sees
# "Approve" in every payload (it's a literal option label) and would either
# false-positive on Deny or, with a start-anchored regex, always fail.

INPUT=$(cat)

# Emit each answer value on its own line.
ANSWERS=$(echo "$INPUT" | jq -r '
  (.tool_response.answers // .tool_output.answers // {}) as $a
  | if ($a | type) == "object" then ($a | to_entries | map(.value) | .[])
    elif ($a | type) == "string" then $a
    else empty
    end
')

if [ -z "$ANSWERS" ]; then
  exit 0
fi

# Any answer exactly equal to "Approve" (case-insensitive, whitespace-trimmed)
# triggers the approval file. grep matches per line.
if echo "$ANSWERS" | grep -qiE '^[[:space:]]*approve[[:space:]]*$'; then
  APPROVE_FILE="$HOME/.claude/guard-approve"
  mkdir -p "$(dirname "$APPROVE_FILE")"
  touch "$APPROVE_FILE"
fi

exit 0
