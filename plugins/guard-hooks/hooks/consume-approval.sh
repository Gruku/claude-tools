#!/bin/bash
# consume-approval.sh — PostToolUse hook for Bash / Edit / Write / MultiEdit /
# NotebookEdit. Deletes the user-approval and AI-ack files after the gated
# tool has actually executed.
#
# Why this lives in PostToolUse rather than the PreToolUse guard:
#
#   PreToolUse used to consume the approval the moment the hook saw it,
#   *before* the standard permission layer ran. If the user then denied the
#   command at that permission prompt, the approval was already gone and the
#   user had to re-approve from scratch. Moving the consumption to
#   PostToolUse means the approval only burns when the tool actually ran;
#   denials leave the approval intact for a retry within the 60s window.
#
# Both files (~/.claude/guard-approve and ~/.claude/guard-ack) are deleted
# unconditionally if present. This hook never blocks anything — it just
# cleans up. Exit 0 always.

# Per-session token: only delete tokens for THIS session, so concurrent
# Claude Code sessions on the same host don't trample each other's approvals.
INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)
[ -z "$SESSION_ID" ] && SESSION_ID="default"

APPROVE_FILE="$HOME/.claude/guard-approve-$SESSION_ID"
ACK_FILE="$HOME/.claude/guard-ack-$SESSION_ID"

[ -f "$APPROVE_FILE" ] && rm -f "$APPROVE_FILE"
[ -f "$ACK_FILE" ] && rm -f "$ACK_FILE"

exit 0
