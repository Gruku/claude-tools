"""_guard_common.py — shared helpers for the guard-hooks Python hooks.

Approval flow (shared across guard-hooks):
  The AI calls AskUserQuestion with labels "Approve"/"Deny". On "Approve",
  the PostToolUse hook on AskUserQuestion creates
  ~/.claude/guard-approve-<session_id> automatically. The user can also type
  "approve" as a chat message (UserPromptSubmit hook).

Lifecycle: the approval is valid for 60 seconds. PreToolUse hooks only
CHECK the file's freshness — they don't delete it on use. The PostToolUse
hook (consume_approval.py) deletes the file after the tool actually runs,
so a denial at the standard permission layer leaves the approval intact
for a retry within the window. Expired files ARE removed here (cleanup).

Imported via same-directory import: the script's directory is on sys.path
when a hook is run as `python path/to/script.py`.
"""

import json
import sys
import time
from pathlib import Path

TTL_SECONDS = 60


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
