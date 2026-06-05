#!/usr/bin/env python3
"""guard_edits.py — PreToolUse hook for Edit/Write operations.

Python port (perf) of guard-edits.sh. Blocks writes to sensitive files.
Exit 2 = block (stderr sent to Claude as feedback). Exit 0 = allow.
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


def main():
    data = common.read_hook_input()
    file_path = common.jq_str(data, "tool_input", "file_path")
    if not file_path:
        sys.exit(0)

    sid = common.session_id(data)
    approve_path = common.approve_file(sid)

    def block_hard(reason):
        """Unconditional block, no approval bypass (guard-approve file,
        git internals, OS system paths)."""
        common.write_stderr(
            "⛔ GUARD HOOK BLOCKED THIS EDIT.\n"
            "Reason: {}\n"
            "File: {}\n"
            "\n"
            "This file cannot be written by Claude under any circumstances.\n"
            .format(reason, file_path)
        )
        sys.exit(2)

    def block(reason):
        """Approvable block — checks for user approval before blocking.
        Approval is NOT consumed here; consume_approval.py (PostToolUse)
        deletes it after the tool actually runs."""
        if common.file_recent(approve_path):
            sys.exit(0)
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
            "Only the exact label \"Approve\" is recognized as authorization.\n"
            "Do NOT re-run automatically. Do NOT create the approval file yourself.\n"
            .format(reason, file_path)
        )
        sys.exit(2)

    # --- Guard approval file (only the user can create this) ---
    if RE_APPROVE_FILE.search(file_path):
        block_hard("You cannot create or modify the guard approval file. Only the user can do this manually.")

    # --- Environment / secrets files ---
    if RE_TEMPLATE_FILE.search(file_path):
        pass  # safe template file — fall through
    elif RE_SECRETS_FILE.search(file_path):
        block("This looks like a sensitive file containing secrets.")

    # --- Lock files (should not be hand-edited) ---
    if RE_LOCK_FILE.search(file_path):
        block("Lockfile detected. Use the package manager instead of editing directly.")

    # --- Git internals ---
    if RE_BLESS_MARKER.search(file_path):
        pass  # allowed: the review-gate blessing marker
    elif RE_GIT_INTERNALS.search(file_path):
        block_hard("Cannot write to git internals.")

    # --- OS system paths (Windows + Unix-like) ---
    # Writing into these paths via Edit/Write is never legitimate. The Bash
    # guard (guard_bash.py) covers Bash; this covers Edit/Write tool calls.
    if RE_WIN_SYS_PATH.search(file_path):
        block_hard("Cannot write to a Windows system path (C:\\Windows, C:\\Program Files).")
    if RE_UNIX_SYS_PATH.search(file_path):
        block_hard("Cannot write to a Unix system path (/bin, /sbin, /usr/bin, /etc, /boot, /lib, /System/Library).")

    sys.exit(0)


if __name__ == "__main__":
    main()
