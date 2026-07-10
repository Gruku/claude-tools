#!/usr/bin/env python3
"""guard_edits.py — PreToolUse hook for Edit/Write operations.

Python port (perf) of guard-edits.sh. Blocks writes to sensitive files.
Exit 2 = block (stderr sent to Claude as feedback). Exit 0 = allow.

As of v2.8.0 the approvable rules participate in the scoped approval flow:
a block records {"guard": "edits", "hash": <file_path hash>} in the
per-session guard-pending file; Approve arms exactly that file, and
consume_approval.py burns the token only after that file was written.
"""

import re
import sys

import _guard_common as common

# --- Guard approval file (only the user can create this) ---
# Match only the actual approval file at ~/.claude/guard-approve, not source files
RE_APPROVE_FILE = re.compile(r'\.claude/guard-approve$')
# Allow template/example env files (they contain only placeholders, not real secrets)
RE_TEMPLATE_FILE = re.compile(r'\.(example|sample|template|defaults)$', re.IGNORECASE)
RE_SECRETS_FILE = re.compile(
    r'(\.env$|\.env\.|credentials|secrets|\.pem$|\.key$|id_rsa)', re.IGNORECASE
)
RE_LOCK_FILE = re.compile(
    r'(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|uv\.lock)$', re.IGNORECASE
)
# Allowlist: the review-gate blessing marker (.git/CLAUDE_REVIEW_GATE_OK).
# Pairs with ~/.claude/hooks/push-review-gate-guard.py — see guard_bash.py
# (git-internals guard) for the matching Bash-side exception.
RE_BLESS_MARKER = re.compile(r'\.git[/\\]CLAUDE_REVIEW_GATE_OK$')
RE_GIT_INTERNALS = re.compile(r'\.git/')
# OS system paths (Windows + Unix-like) — block_hard, no approval bypass.
RE_WIN_SYS_PATH = re.compile(
    r'([cC]:[\\/]+[wW]indows([\\/]|$)'
    r'|[cC]:[\\/]+[pP]rogram\s+[fF]iles(\s+\(x86\))?([\\/]|$)'
    r'|^/c/[wW]indows/)',
    re.IGNORECASE,
)
RE_UNIX_SYS_PATH = re.compile(
    r'^/(bin|sbin|etc|boot|lib|lib64)/'
    r'|^/usr/(bin|sbin|lib|lib64|local/bin|local/sbin)/'
    r'|^/System/Library/'
)


def classify(file_path):
    """Returns None (allow), ("hard", reason) — no approval bypass — or
    ("soft", reason) — approvable. Mirrors the rule order of main()."""
    if RE_APPROVE_FILE.search(file_path):
        return ("hard", "You cannot create or modify the guard approval file. "
                        "Only the user can do this manually.")
    if not RE_TEMPLATE_FILE.search(file_path):
        if RE_SECRETS_FILE.search(file_path):
            return ("soft", "This looks like a sensitive file containing secrets.")
    if RE_LOCK_FILE.search(file_path):
        return ("soft", "Lockfile detected. Use the package manager instead of "
                        "editing directly.")
    if not RE_BLESS_MARKER.search(file_path):
        if RE_GIT_INTERNALS.search(file_path):
            return ("hard", "Cannot write to git internals.")
    if RE_WIN_SYS_PATH.search(file_path):
        return ("hard", "Cannot write to a Windows system path "
                        "(C:\\Windows, C:\\Program Files).")
    if RE_UNIX_SYS_PATH.search(file_path):
        return ("hard", "Cannot write to a Unix system path (/bin, /sbin, "
                        "/usr/bin, /etc, /boot, /lib, /System/Library).")
    return None


def would_block(file_path):
    """True if writing `file_path` would trip any edit rule with no approval
    present. Used by consume_approval.py."""
    return bool(file_path) and classify(file_path) is not None


def main():
    data = common.read_hook_input()
    file_path = common.jq_str(data, "tool_input", "file_path")
    if not file_path:
        sys.exit(0)

    verdict = classify(file_path)
    if verdict is None:
        sys.exit(0)
    kind, reason = verdict

    if kind == "hard":
        common.write_stderr(
            "⛔ GUARD HOOK BLOCKED THIS EDIT.\n"
            "Reason: {}\n"
            "File: {}\n"
            "\n"
            "This file cannot be written by Claude under any circumstances.\n"
            .format(reason, file_path)
        )
        sys.exit(2)

    # Approvable block — honor a fresh approval covering THIS file. Approval
    # is NOT consumed here; consume_approval.py (PostToolUse) burns it after
    # the write actually runs.
    sid = common.session_id(data)
    action_hash = common.hash_text(file_path)
    if common.approval_grants(common.approve_file(sid), "edits", action_hash):
        sys.exit(0)
    common.write_scope(
        common.pending_file(sid), {"guard": "edits", "hash": action_hash}
    )
    common.write_stderr(
        "⛔ GUARD HOOK BLOCKED THIS EDIT.\n"
        "Reason: {}\n"
        "File: {}\n"
        "\n"
        "ACTION REQUIRED: Use the AskUserQuestion tool with EXACTLY this shape:\n"
        "  question: one short sentence describing what will be written and why it's sensitive\n"
        "  options (use these labels verbatim — do not rename, translate, or add more):\n"
        "    - label: \"Approve\"  description: \"Write the file as proposed\"\n"
        "    - label: \"Deny\"     description: \"Cancel; do not write this file\"\n"
        "\n"
        "After the user responds:\n"
        "  - \"Approve\" → rerun the ORIGINAL Write/Edit unchanged\n"
        "  - \"Deny\" or no response → do NOT write this file\n"
        "\n"
        "The approval covers exactly this file for 5 minutes and is consumed\n"
        "when the write runs — it does not authorize any other guarded action.\n"
        "Only the exact label \"Approve\" is recognized as authorization.\n"
        "Do NOT re-run automatically. Do NOT create the approval file yourself.\n"
        .format(reason, file_path)
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
