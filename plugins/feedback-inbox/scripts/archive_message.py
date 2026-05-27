"""Move a pending message to processed/<year>/ and update its frontmatter."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml

VALID_ARCHIVE_STATUS = {"processed", "promoted", "dropped"}


def _split(text: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        raise ValueError("no frontmatter")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError("unterminated frontmatter")
    data = yaml.safe_load(text[4:end])
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError(f"frontmatter is not a mapping: {type(data).__name__}")
    body = text[end + len("\n---\n"):]
    return data, body


def archive(path: Path, status: str, promoted_to: str | None = None) -> Path:
    if status not in VALID_ARCHIVE_STATUS:
        raise ValueError(
            f"invalid archive status: {status!r} (expected one of {sorted(VALID_ARCHIVE_STATUS)})"
        )

    # Idempotency: if path is already under processed/<year>/, just update frontmatter in place.
    # Check grandparent name so an inbox directory literally named "processed" does not
    # trigger a false-positive (a file at <inbox>/processed/<file>.md has parent.parent == tmp,
    # whereas a genuinely archived file at <inbox>/processed/<year>/<file>.md has parent.parent.name == "processed").
    if path.parent.parent.name == "processed":
        target = path
    else:
        # Pick year from the file's frontmatter `created` field; fall back to current year.
        text = path.read_text(encoding="utf-8")
        fm, body = _split(text)
        year = _year_of(fm.get("created"))
        target_dir = path.parent / "processed" / year
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / path.name

    # Re-read so we update whichever file is now authoritative.
    text = (target if target.exists() else path).read_text(encoding="utf-8")
    fm, body = _split(text)
    fm["status"] = status
    fm["processed_at"] = datetime.now(tz=timezone.utc).isoformat()
    if promoted_to is not None:
        fm["promoted_to"] = promoted_to

    new_text = "---\n" + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True).strip() + "\n---\n" + body

    target.write_text(new_text, encoding="utf-8")
    if path != target and path.exists():
        path.unlink()
    return target


def _year_of(created) -> str:
    if isinstance(created, datetime):
        return f"{created.year:04d}"
    if isinstance(created, str) and len(created) >= 4 and created[:4].isdigit():
        return created[:4]
    return f"{datetime.now(tz=timezone.utc).year:04d}"
