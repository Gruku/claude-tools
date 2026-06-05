#!/usr/bin/env python3
"""guard_approve.py — UserPromptSubmit hook.

When the user types "approve" (case-insensitive), creates a time-limited
approval file that the PreToolUse guards will honor on the next blocked
command.

This hook runs on USER input only — the LLM cannot trigger it.
"""

import re
import sys

import _guard_common as common

# The user's message is an approval if some line is just "approve"
# (optionally surrounded by whitespace) — mirrors grep's per-line matching.
RE_APPROVE = re.compile(r'^[ \t\r]*approve[ \t\r]*$', re.IGNORECASE | re.MULTILINE)


def main():
    data = common.read_hook_input()
    prompt = common.jq_str(data, "prompt")
    if not prompt:
        sys.exit(0)

    if RE_APPROVE.search(prompt):
        # Per-session token: keyed by harness session_id so concurrent
        # sessions don't trample each other's approvals.
        common.touch(common.approve_file(common.session_id(data)))
        print("Guard approval granted. The next blocked command will be allowed (valid for 60 seconds).")
        sys.exit(0)

    sys.exit(0)


if __name__ == "__main__":
    main()
