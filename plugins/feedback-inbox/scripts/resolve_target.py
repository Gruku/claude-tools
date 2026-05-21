"""Resolve the feedback-inbox target from ~/.claude/inbox-target.json.

Never raises. All failure modes are returned as ``Resolved(enabled=False, reason=...)``
so the producer can no-op silently.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Resolved:
    inbox: Path | None
    enabled: bool
    reason: str | None


def _home() -> Path:
    # Honour HOME (POSIX) or USERPROFILE (Windows). Falls back to Path.home().
    for key in ("HOME", "USERPROFILE"):
        v = os.environ.get(key)
        if v:
            return Path(v)
    return Path.home()


def _config_path() -> Path:
    return _home() / ".claude" / "inbox-target.json"


def resolve_target() -> Resolved:
    cfg = _config_path()
    if not cfg.is_file():
        return Resolved(
            inbox=None,
            enabled=False,
            reason=f"feedback-inbox not configured: {cfg} missing. Run /feedback-inbox-setup.",
        )

    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return Resolved(inbox=None, enabled=False, reason=f"feedback-inbox config invalid JSON: {e}")
    except OSError as e:
        return Resolved(inbox=None, enabled=False, reason=f"feedback-inbox config unreadable: {e}")

    if not isinstance(data, dict):
        return Resolved(inbox=None, enabled=False, reason="feedback-inbox config invalid: not an object")

    if data.get("enabled", True) is False:
        return Resolved(inbox=None, enabled=False, reason="feedback-inbox disabled in config")

    inbox_str = data.get("inbox")
    if not isinstance(inbox_str, str) or not inbox_str.strip():
        return Resolved(inbox=None, enabled=False, reason="feedback-inbox config missing 'inbox' path")

    inbox = Path(inbox_str)
    try:
        inbox.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return Resolved(inbox=None, enabled=False, reason=f"feedback-inbox path uncreatable: {e}")

    return Resolved(inbox=inbox, enabled=True, reason=None)
