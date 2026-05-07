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

APPROVE_FILE="$HOME/.claude/guard-approve"
ACK_FILE="$HOME/.claude/guard-ack"

# Drain stdin so the harness doesn't see a broken pipe; we don't need it.
cat >/dev/null

[ -f "$APPROVE_FILE" ] && rm -f "$APPROVE_FILE"
[ -f "$ACK_FILE" ] && rm -f "$ACK_FILE"

exit 0
