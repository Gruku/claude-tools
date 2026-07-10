#!/usr/bin/env python3
"""ask_question_approval.py — PostToolUse hook for AskUserQuestion.

Creates a time-limited approval file when the user picks the "Approve" option.

Protocol: the PreToolUse guards instruct the LLM (via their block messages)
to call AskUserQuestion with exactly two labels — "Approve" and "Deny". This
hook only recognizes the literal "Approve" label. Any other answer (including
free-form text, "Deny", or unrelated AskUserQuestion calls that don't follow
the protocol) is ignored — no approval file is created.

PostToolUse payload for AskUserQuestion has tool_response with BOTH:
  - .questions — the question spec, including option labels like "Approve"/"Deny"
  - .answers   — a map of question text -> the label the user picked

We MUST only inspect .answers values. A naive flatten of tool_response sees
"Approve" in every payload (it's a literal option label) and would either
false-positive on Deny or, with a start-anchored regex, always fail.
"""

import re
import sys

import _guard_common as common

RE_APPROVE = re.compile(r'^[ \t\r]*approve[ \t\r]*$', re.IGNORECASE | re.MULTILINE)


def _answers(data):
    """Collect answer values: jq `(.tool_response.answers // .tool_output.answers
    // {})` — object -> its values, string -> itself, anything else -> empty."""
    answers = None
    for container in ("tool_response", "tool_output"):
        obj = data.get(container)
        if isinstance(obj, dict):
            val = obj.get("answers")
            # jq // falls through on null/false
            if val is not None and val is not False:
                answers = val
                break
    if isinstance(answers, dict):
        return [v for v in answers.values() if isinstance(v, str)]
    if isinstance(answers, str):
        return [answers]
    return []


def main():
    data = common.read_hook_input()

    # Any answer exactly equal to "Approve" (case-insensitive,
    # whitespace-trimmed) triggers the approval file.
    for answer in _answers(data):
        if RE_APPROVE.search(answer):
            # Per-session token: keyed by harness session_id so concurrent
            # Claude Code sessions don't trample each other's approvals.
            # Arms the pending block's scope when one is fresh (v2.8.0).
            common.arm_approval(common.session_id(data))
            break

    sys.exit(0)


if __name__ == "__main__":
    main()
