"""List pending messages in the inbox (top-level only; excludes processed/)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class PendingMessage:
    path: Path
    id: str
    source: str
    category: str
    project: str
    component: str
    summary: str
    created: str


@dataclass
class ListResult:
    messages: list[PendingMessage] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def _parse_frontmatter(text: str) -> dict:
    if not text.startswith("---\n"):
        raise ValueError("no frontmatter")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError("unterminated frontmatter")
    return yaml.safe_load(text[4:end]) or {}


def list_pending(inbox: Path) -> ListResult:
    result = ListResult()
    if not inbox.is_dir():
        return result

    for path in sorted(inbox.glob("*.md")):
        if not path.is_file():
            continue
        try:
            fm = _parse_frontmatter(path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, ValueError, OSError) as e:
            result.warnings.append(f"{path.name}: {e}")
            continue

        if fm.get("status", "pending") != "pending":
            continue

        category = str(fm.get("category", "unknown"))
        result.messages.append(
            PendingMessage(
                path=path,
                id=str(fm.get("id", "")),
                source=str(fm.get("source", "")),
                category=category,
                project=str(fm.get("project", "")),
                component=str(fm.get("component", "")),
                summary=str(fm.get("summary", "")),
                created=str(fm.get("created", "")),
            )
        )
        result.counts[category] = result.counts.get(category, 0) + 1

    return result
