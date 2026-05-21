from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from scripts.archive_message import archive
from scripts.list_pending import list_pending
from scripts.resolve_target import resolve_target
from scripts.write_message import MessagePayload, write_message


def test_round_trip(tmp_path, monkeypatch):
    # 1. Configure inbox-target.json pointing at tmp_path/inbox.
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    inbox_path = tmp_path / "inbox"
    (tmp_path / ".claude").mkdir(parents=True)
    (tmp_path / ".claude" / "inbox-target.json").write_text(
        json.dumps({"inbox": str(inbox_path), "enabled": True}), encoding="utf-8"
    )

    # 2. resolve_target() finds the inbox and creates it.
    r = resolve_target()
    assert r.enabled and r.inbox == inbox_path

    # 3. write_message() drops two messages.
    p1 = write_message(r.inbox, MessagePayload(
        source="claude", category="friction", summary="first issue", body="b1",
        created=datetime(2026, 5, 21, 14, 30, tzinfo=timezone.utc),
    ))
    p2 = write_message(r.inbox, MessagePayload(
        source="user", category="bug", summary="second issue", body="b2",
        created=datetime(2026, 5, 21, 14, 31, tzinfo=timezone.utc),
    ))

    # 4. list_pending() sees both.
    pending = list_pending(r.inbox)
    assert len(pending.messages) == 2
    assert pending.counts == {"friction": 1, "bug": 1}

    # 5. archive() the first as promoted, the second as dropped.
    archive(p1, status="promoted", promoted_to="IDEA-042")
    archive(p2, status="dropped")

    # 6. list_pending() is now empty.
    pending = list_pending(r.inbox)
    assert pending.messages == []

    # 7. Both archives sit under processed/2026/.
    archived = list((r.inbox / "processed" / "2026").glob("*.md"))
    assert len(archived) == 2
