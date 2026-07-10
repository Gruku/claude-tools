"""_guard_common.py — shared helpers for the guard-hooks Python hooks.

Approval flow (shared across guard-hooks), scoped as of v2.8.0:
  When a guard blocks an approvable action it records WHAT was blocked in
  ~/.claude/guard-pending-<session_id> (guard name + a hash of the action).
  The AI then calls AskUserQuestion with labels "Approve"/"Deny". On
  "Approve", the PostToolUse hook on AskUserQuestion arms
  ~/.claude/guard-approve-<session_id> with that pending scope. The user can
  also type "approve" as a chat message (UserPromptSubmit hook).

Lifecycle: the approval is valid for TTL_SECONDS (5 minutes) and covers
exactly the pending action — a different guarded action still blocks
(B-008/ISS-012), and rerunning the same action within the window doesn't
re-prompt (B-004). PreToolUse hooks only CHECK the file — they don't delete
it on use. The PostToolUse hook (consume_approval.py) burns it only after
the APPROVED action actually ran (scope-hash match), so benign intermediate
commands no longer eat the token, and a denial at the standard permission
layer leaves the approval intact for a retry within the window. An approve
file with no scope (typed "approve" with nothing pending, or a token written
by an external project hook) behaves like the pre-2.8.0 universal token.
Expired files ARE removed here (cleanup).

Imported via same-directory import: the script's directory is on sys.path
when a hook is run as `python path/to/script.py`.
"""

import hashlib
import json
import sys
import time
from pathlib import Path

TTL_SECONDS = 300


def home_dir() -> Path:
    """User home — replaces $HOME in the bash hooks. Works on Windows
    (USERPROFILE) and POSIX (HOME)."""
    return Path.home()


def claude_dir() -> Path:
    return home_dir() / ".claude"


def read_hook_input() -> dict:
    """Parse the hook JSON payload from stdin.

    Fail open: malformed/empty stdin returns {} (the caller then finds no
    command/file_path and exits 0), mirroring the bash hooks' behavior where
    jq on bad input yields empty strings.
    """
    try:
        raw = sys.stdin.read()
    except Exception:
        return {}
    if not raw or not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def jq_str(data, *keys) -> str:
    """Equivalent of `jq -r '.a.b // empty'` — returns "" for missing/null
    fields or non-string values."""
    cur = data
    for key in keys:
        if not isinstance(cur, dict):
            return ""
        cur = cur.get(key)
    return cur if isinstance(cur, str) else ""


def session_id(data) -> str:
    """Per-session approval token key: keyed by harness session_id so
    concurrent Claude Code sessions on the same host don't trample each
    other's approvals. Falls back to "default" if absent."""
    sid = jq_str(data, "session_id")
    return sid if sid else "default"


def approve_file(sid: str) -> Path:
    """User-only approval token file."""
    return claude_dir() / "guard-approve-{}".format(sid)


def ack_file(sid: str) -> Path:
    """AI-allowed self-ack token file (soft DB blocks)."""
    return claude_dir() / "guard-ack-{}".format(sid)


def pending_file(sid: str) -> Path:
    """Pending-block scope file: records which guard blocked what, so the
    next Approve arms exactly that action and nothing else."""
    return claude_dir() / "guard-pending-{}".format(sid)


def hash_text(text: str) -> str:
    """Whitespace-normalized action identity. The same logical command rerun
    with incidental whitespace differences still matches its approval."""
    norm = " ".join(text.split())
    return hashlib.sha1(norm.encode("utf-8", "replace")).hexdigest()


def read_scope(path: Path) -> dict:
    """Parse a scope file ({"guard": ..., "hash": ...}). Empty, missing, or
    non-JSON content (including pre-2.8.0 empty token files) returns {} —
    the universal, unscoped legacy semantics."""
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except OSError:
        return {}
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def write_scope(path: Path, scope: dict) -> None:
    """Write a scope file; failures are swallowed (a guard must never crash
    on a token write — worst case the approval degrades to unscoped)."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(scope), encoding="utf-8")
    except OSError:
        pass


def approval_grants(approve_path: Path, guard_name: str, action_hash: str) -> bool:
    """True if a fresh approval covers this guard + action. An unscoped
    approval (no hash) covers anything, preserving pre-2.8.0 behavior for
    externally written tokens."""
    if not file_recent(approve_path):
        return False
    scope = read_scope(approve_path)
    if not scope.get("hash"):
        return True
    return scope.get("guard") == guard_name and scope.get("hash") == action_hash


def arm_approval(sid: str) -> None:
    """Turn a fresh pending-block scope (if any) into an armed approval.
    Stale or absent pending (B-010) arms an unscoped approval instead — a
    later unrelated Approve must not be attributed to an old block."""
    pending = pending_file(sid)
    scope = read_scope(pending) if file_recent(pending) else {}
    remove_if_present(pending)
    write_scope(approve_file(sid), scope)


def file_recent(path: Path) -> bool:
    """True if `path` exists and was modified within the last 60 seconds.

    Expired files are removed (cleanup). Files whose mtime can't be stat'd
    are left in place and treated as not-recent, so the user's later attempt
    still works. The file is never consumed on successful check — that's the
    PostToolUse consumer's job.
    """
    try:
        if not path.is_file():
            return False
        mtime = path.stat().st_mtime
    except OSError:
        return False
    age = time.time() - mtime
    if age <= TTL_SECONDS:
        return True
    # Expired — clean up
    try:
        path.unlink()
    except OSError:
        pass
    return False


def touch(path: Path) -> None:
    """mkdir -p the parent and touch the file (updates mtime if it exists)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


def remove_if_present(path: Path) -> None:
    try:
        path.unlink()
    except OSError:
        pass


def write_stderr(text: str) -> None:
    """Write a block message to stderr as UTF-8 bytes.

    On Windows, a piped sys.stderr defaults to the ANSI codepage; the block
    messages contain characters (⛔, →, —) that aren't encodable there, which
    would crash the hook with a UnicodeEncodeError instead of blocking.
    """
    try:
        sys.stderr.buffer.write(text.encode("utf-8"))
        sys.stderr.buffer.flush()
    except (AttributeError, OSError):
        sys.stderr.write(text)


def timestamp() -> str:
    """`date '+%Y-%m-%d %H:%M:%S'` equivalent."""
    return time.strftime("%Y-%m-%d %H:%M:%S")


def log_denied(log_file: Path, reason: str, command: str) -> None:
    """Append a denial line to a guard log; failures are swallowed (the bash
    hooks redirected logging errors to /dev/null)."""
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(str(log_file), "a", encoding="utf-8", errors="replace") as fh:
            fh.write("[{}] {} | CMD: {}\n".format(timestamp(), reason, command))
    except OSError:
        pass
