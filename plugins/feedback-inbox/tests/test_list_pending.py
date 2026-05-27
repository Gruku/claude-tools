from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from scripts.list_pending import list_pending
from scripts.write_message import MessagePayload, write_message


def _payload(category: str, summary: str) -> MessagePayload:
    return MessagePayload(
        source="claude",
        category=category,
        summary=summary,
        body="body",
        created=datetime(2026, 5, 21, 14, 30, tzinfo=timezone.utc),
    )


def test_empty_inbox(tmp_path):
    r = list_pending(tmp_path)
    assert r.messages == []
    assert r.counts == {}
    assert r.warnings == []


def test_mixed_categories(tmp_path):
    write_message(tmp_path, _payload("friction", "a"))
    write_message(tmp_path, _payload("friction", "b"))
    write_message(tmp_path, _payload("bug", "c"))
    r = list_pending(tmp_path)
    assert len(r.messages) == 3
    assert r.counts == {"friction": 2, "bug": 1}


def test_excludes_processed_subdir(tmp_path):
    write_message(tmp_path, _payload("friction", "live"))
    processed = tmp_path / "processed" / "2026"
    processed.mkdir(parents=True)
    (processed / "old.md").write_text("---\nid: x\nstatus: processed\n---\n", encoding="utf-8")
    r = list_pending(tmp_path)
    assert len(r.messages) == 1
    assert r.messages[0].summary == "live"


def test_corrupt_frontmatter_is_skipped_with_warning(tmp_path):
    write_message(tmp_path, _payload("friction", "good"))
    (tmp_path / "bad.md").write_text("---\nnot: [valid\n---\nbody\n", encoding="utf-8")
    r = list_pending(tmp_path)
    assert len(r.messages) == 1
    assert any("bad.md" in w for w in r.warnings)


def test_missing_inbox_directory(tmp_path):
    r = list_pending(tmp_path / "does-not-exist")
    assert r.messages == []
    assert r.counts == {}


def test_non_dict_frontmatter_is_skipped_with_warning(tmp_path):
    write_message(tmp_path, _payload("friction", "good"))
    (tmp_path / "list.md").write_text("---\n- a\n- b\n---\nbody\n", encoding="utf-8")
    r = list_pending(tmp_path)
    assert len(r.messages) == 1
    assert any("list.md" in w for w in r.warnings)
