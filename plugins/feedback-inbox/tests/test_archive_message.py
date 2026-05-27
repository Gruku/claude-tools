from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from scripts.archive_message import archive
from scripts.write_message import MessagePayload, write_message


def _write(tmp_path: Path) -> Path:
    return write_message(
        tmp_path,
        MessagePayload(
            source="claude",
            category="friction",
            summary="hello world",
            body="body",
            created=datetime(2026, 5, 21, 14, 30, tzinfo=timezone.utc),
        ),
    )


def _read_fm(p: Path) -> dict:
    text = p.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    end = text.index("\n---\n", 4)
    return yaml.safe_load(text[4:end])


def test_archive_moves_to_processed_year_dir(tmp_path):
    src = _write(tmp_path)
    new = archive(src, status="processed")
    assert not src.exists()
    assert new.exists()
    assert new.parent.name == "2026"
    assert new.parent.parent.name == "processed"


def test_archive_sets_status_and_processed_at(tmp_path):
    src = _write(tmp_path)
    new = archive(src, status="processed")
    fm = _read_fm(new)
    assert fm["status"] == "processed"
    assert "processed_at" in fm and fm["processed_at"]


def test_archive_with_promoted_to(tmp_path):
    src = _write(tmp_path)
    new = archive(src, status="promoted", promoted_to="IDEA-042")
    fm = _read_fm(new)
    assert fm["status"] == "promoted"
    assert fm["promoted_to"] == "IDEA-042"


def test_archive_is_idempotent_for_already_archived(tmp_path):
    src = _write(tmp_path)
    once = archive(src, status="processed")
    twice = archive(once, status="processed")
    assert once == twice
    assert once.exists()


def test_archive_invalid_status_rejected(tmp_path):
    src = _write(tmp_path)
    with pytest.raises(ValueError):
        archive(src, status="bogus")


# --- B-013: idempotency guard must not false-positive when an ancestor dir is named "processed" ---

def test_archive_pending_in_dir_named_processed_is_not_treated_as_already_archived(tmp_path):
    # Inbox directory is literally named "processed" -- simulates an ancestor named "processed".
    # The pending file lives directly inside it (NOT under processed/<year>/),
    # so the archive call should MOVE it, not update in-place.
    inbox = tmp_path / "processed"
    inbox.mkdir()
    src = _write(inbox)
    assert src.parent.name == "processed"  # confirm setup: parent is "processed"

    result = archive(src, status="processed")

    # The result must be inside a <year> subdirectory whose parent is named "processed".
    assert result.parent.parent.name == "processed", (
        "archived file should land in processed/<year>/, not stay in the inbox dir"
    )
    assert result.parent.name.isdigit(), "year directory name should be numeric"
    # The original pending file must have been moved (not still at src).
    assert not src.exists(), "pending file should have been moved away from the inbox dir"


def test_archive_idempotent_for_file_genuinely_in_processed_year_dir(tmp_path):
    # Write a message normally, archive it once to get it into processed/<year>/.
    src = _write(tmp_path)
    once = archive(src, status="processed")
    assert once.parent.parent.name == "processed"

    # Archiving the already-archived file again must be idempotent: same path returned.
    twice = archive(once, status="processed")
    assert once == twice
    assert once.exists()
