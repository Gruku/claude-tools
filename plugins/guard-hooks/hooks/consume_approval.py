#!/usr/bin/env python3
"""consume_approval.py — PostToolUse hook for Bash / PowerShell / Edit /
Write / MultiEdit / NotebookEdit. Burns the user-approval and AI-ack tokens
after the APPROVED action has actually executed.

Why this lives in PostToolUse rather than the PreToolUse guard:

  PreToolUse used to consume the approval the moment the hook saw it,
  *before* the standard permission layer ran. If the user then denied the
  command at that permission prompt, the approval was already gone and the
  user had to re-approve from scratch. Consuming in PostToolUse means the
  approval only burns when the tool actually ran.

Why the burn is conditional (v2.8.0 — the guard-hooks-002 friction fix):

  This hook fires after EVERY matched tool call. Burning unconditionally
  meant any benign intermediate command (a `git status` between the user's
  Approve and the retry of the blocked command) silently ate the token and
  forced a re-approval. Now:

  * A SCOPED approval (armed from a pending block) burns only when the tool
    input's hash matches the approved scope — i.e. the approved action ran.
  * An UNSCOPED approval (legacy empty token, or typed "approve" with
    nothing pending) burns only when the tool input would itself have
    tripped a guard — i.e. some gated action ran under it.
  * The ack token burns only when a guarded command ran. In particular the
    `: guard-ack-self` sentinel no longer burns the ack it just created
    (pre-2.8.0 the soft-ack flow was broken end-to-end because of this).

This hook never blocks anything. Exit 0 always.
"""

import sys

import _guard_common as common
import guard_bash
import guard_edits

COMMAND_TOOLS = ("Bash", "PowerShell")


def main():
    # Per-session tokens: only touch tokens for THIS session, so concurrent
    # Claude Code sessions on the same host don't trample each other.
    data = common.read_hook_input()
    sid = common.session_id(data)
    tool = common.jq_str(data, "tool_name")
    if tool in COMMAND_TOOLS:
        text = common.jq_str(data, "tool_input", "command")
    else:
        text = common.jq_str(data, "tool_input", "file_path")
    hook_cwd = common.jq_str(data, "cwd")

    gated = None  # lazy: evaluating guards costs a few regex passes

    def ran_gated_action():
        nonlocal gated
        if gated is None:
            if not text:
                gated = False
            elif tool in COMMAND_TOOLS:
                gated = guard_bash.would_block(text, hook_cwd)
            else:
                gated = guard_edits.would_block(text)
        return gated

    approve = common.approve_file(sid)
    if approve.is_file():
        scope = common.read_scope(approve)
        if scope.get("hash"):
            if text and common.hash_text(text) == scope["hash"]:
                common.remove_if_present(approve)
        elif ran_gated_action():
            common.remove_if_present(approve)

    ack = common.ack_file(sid)
    if ack.is_file() and tool in COMMAND_TOOLS and ran_gated_action():
        common.remove_if_present(ack)

    sys.exit(0)


if __name__ == "__main__":
    main()
