from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from scripts.write_message import MessagePayload, write_message, _slugify


def _payload(**overrides) -> MessagePayload:
    base = MessagePayload(
        source="claude",
        category="friction",
        project="CodeMaestro",
        project_path="C:/Users/gruku/Files/Work/CodeMaestro",
        component="taskmaster/pick-task",
        summary="pick-task hangs on worktree creation when path > 200 chars",
        body="## What happened\nIt hung.\n",
        created=datetime(2026, 5, 21, 14, 30, tzinfo=timezone.utc),
    )
    for k, v in overrides.items():
        setattr(base, k, v)
    return base


def test_writes_file_with_expected_frontmatter(tmp_path):
    path = write_message(tmp_path, _payload())
    assert path.exists()
    assert path.parent == tmp_path

    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    fm_end = text.index("\n---\n", 4)
    fm = yaml.safe_load(text[4:fm_end])
    body = text[fm_end + len("\n---\n"):]

    assert fm["source"] == "claude"
    assert fm["category"] == "friction"
    assert fm["project"] == "CodeMaestro"
    assert fm["component"] == "taskmaster/pick-task"
    assert fm["status"] == "pending"
    assert fm["summary"].startswith("pick-task hangs")
    assert fm["id"].startswith("msg-2026-05-21-1430-")
    assert "It hung" in body


def test_filename_collision_appends_suffix(tmp_path):
    p1 = write_message(tmp_path, _payload())
    p2 = write_message(tmp_path, _payload())
    p3 = write_message(tmp_path, _payload())
    names = sorted(p.name for p in (p1, p2, p3))
    # Two of the three should have a -2 / -3 suffix.
    assert any(n.endswith("-2.md") for n in names)
    assert any(n.endswith("-3.md") for n in names)


def test_slugify_truncates_and_kebabs():
    assert _slugify("Hello, World! This is A Test") == "hello-world-this-is-a-test"
    s = _slugify("a" * 80)
    assert len(s) <= 40
    assert _slugify("    ") == "untitled"


def test_creates_parent_directory_if_missing(tmp_path):
    nested = tmp_path / "deep" / "inbox"
    path = write_message(nested, _payload())
    assert path.exists()
    assert path.parent == nested
