"""Serialize one feedback message to the inbox as a markdown file with YAML frontmatter."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

VALID_SOURCES = {"claude", "user"}
VALID_CATEGORIES = {"bug", "friction", "idea", "praise", "question"}
MAX_SLUG_LEN = 40


@dataclass
class MessagePayload:
    source: str           # "claude" | "user"
    category: str         # bug | friction | idea | praise | question
    summary: str          # one-line, <= 120 chars
    body: str             # freeform markdown
    project: str = ""
    project_path: str = ""
    component: str = ""
    created: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))


def _slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    if not text:
        return "untitled"
    if len(text) > MAX_SLUG_LEN:
        text = text[:MAX_SLUG_LEN].rstrip("-")
    return text


def _validate(p: MessagePayload) -> None:
    if p.source not in VALID_SOURCES:
        raise ValueError(f"invalid source: {p.source!r} (expected one of {sorted(VALID_SOURCES)})")
    if p.category not in VALID_CATEGORIES:
        raise ValueError(f"invalid category: {p.category!r} (expected one of {sorted(VALID_CATEGORIES)})")
    if not p.summary.strip():
        raise ValueError("summary must not be empty")
    if p.created.tzinfo is None or p.created.utcoffset() is None:
        raise ValueError("created must be timezone-aware (naive datetime is ambiguous)")


def _pick_filename(inbox: Path, stem: str) -> Path:
    candidate = inbox / f"{stem}.md"
    if not candidate.exists():
        return candidate
    n = 2
    while True:
        candidate = inbox / f"{stem}-{n}.md"
        if not candidate.exists():
            return candidate
        n += 1


def write_message(inbox: Path, payload: MessagePayload) -> Path:
    _validate(payload)
    inbox.mkdir(parents=True, exist_ok=True)

    ts = payload.created.astimezone(timezone.utc)  # UTC stamp for filename determinism across hosts
    stem = f"{ts.strftime('%Y-%m-%d-%H%M')}-{_slugify(payload.summary)}"
    path = _pick_filename(inbox, stem)

    msg_id = f"msg-{path.stem}"
    frontmatter = {
        "id": msg_id,
        "source": payload.source,
        "category": payload.category,
        "project": payload.project,
        "project_path": payload.project_path,
        "component": payload.component,
        "summary": payload.summary,
        "status": "pending",
        "created": payload.created.isoformat(),
    }

    fm_yaml = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True).strip()
    body = payload.body.rstrip() + "\n"
    text = f"---\n{fm_yaml}\n---\n\n{body}"

    path.write_text(text, encoding="utf-8")
    return path
