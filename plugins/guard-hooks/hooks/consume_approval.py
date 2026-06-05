#!/usr/bin/env python3
"""consume_approval.py — PostToolUse hook for Bash / Edit / Write /
MultiEdit / NotebookEdit. Deletes the user-approval and AI-ack files after
the gated tool has actually executed.

Why this lives in PostToolUse rather than the PreToolUse guard:

  PreToolUse used to consume the approval the moment the hook saw it,
  *before* the standard permission layer ran. If the user then denied the
  command at that permission prompt, the approval was already gone and the
  user had to re-approve from scratch. Consuming in PostToolUse means the
  approval only burns when the tool actually ran; denials leave the approval
  intact for a retry within the 60s window.

Both files are deleted unconditionally if present. This hook never blocks
anything — it just cleans up. Exit 0 always.
"""

import sys

import _guard_common as common


def main():
    # Per-session token: only delete tokens for THIS session, so concurrent
    # Claude Code sessions on the same host don't trample each other's
    # approvals.
    data = common.read_hook_input()
    sid = common.session_id(data)
    common.remove_if_present(common.approve_file(sid))
    common.remove_if_present(common.ack_file(sid))
    sys.exit(0)


if __name__ == "__main__":
    main()
