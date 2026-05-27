# feedback-inbox Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a `feedback-inbox` plugin so any Claude instance on this machine can drop tagged feedback messages into a configurable inbox, and the user can triage them in `claude-tools` with one slash command.

**Architecture:** New plugin under `plugins/feedback-inbox/`. Producer skill (`feedback`) writes one markdown-with-YAML-frontmatter file per message to an inbox path resolved from `~/.claude/inbox-target.json`. Triage skill (`inbox-triage`) lists pending messages, walks them, and routes accepted items to `taskmaster:add-idea` or `taskmaster:bug`; processed messages move to `inbox/processed/<year>/`. Four small Python scripts (resolve, write, list, archive) carry the IO; the skills are prose wrappers.

**Tech Stack:** Python 3.11+, PyYAML, pytest. Same conventions as `plugins/taskmaster/` (per-plugin `tests/` dir + `conftest.py` that sets `sys.path`).

**Spec:** `docs/superpowers/specs/2026-05-21-feedback-inbox-design.md`

---

## File structure

```
plugins/feedback-inbox/
├── .claude-plugin/
│   └── plugin.json
├── README.md
├── scripts/
│   ├── __init__.py
│   ├── resolve_target.py
│   ├── write_message.py
│   ├── list_pending.py
│   └── archive_message.py
├── skills/
│   ├── feedback/SKILL.md
│   └── inbox-triage/SKILL.md
├── commands/
│   ├── feedback.md
│   ├── inbox.md
│   └── feedback-inbox-setup.md
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_resolve_target.py
    ├── test_write_message.py
    ├── test_list_pending.py
    ├── test_archive_message.py
    └── test_round_trip.py
```

Each script has one responsibility (resolve config / write a message / list pending / archive one). Skills are prose-only — no Python in skill files. The setup command embeds inline bash + a tiny Python one-liner; it doesn't import the scripts above.

---

## Task 1: Plugin scaffold

**Files:**
- Create: `plugins/feedback-inbox/.claude-plugin/plugin.json`
- Create: `plugins/feedback-inbox/README.md`
- Create: `plugins/feedback-inbox/scripts/__init__.py` (empty)
- Create: `plugins/feedback-inbox/tests/__init__.py` (empty)
- Create: `plugins/feedback-inbox/tests/conftest.py`

- [ ] **Step 1: Create the plugin manifest**

Write `plugins/feedback-inbox/.claude-plugin/plugin.json`:

```json
{
  "name": "feedback-inbox",
  "description": "Live feedback channel from any Claude instance back to the claude-tools toolmaker. Producer writes tagged messages to a configurable inbox; triage routes them into the taskmaster backlog.",
  "version": "0.1.0",
  "author": {
    "name": "gruku"
  }
}
```

- [ ] **Step 2: Create the README**

Write `plugins/feedback-inbox/README.md`:

```markdown
# feedback-inbox

Lightweight inbox so any Claude Code instance on this machine can drop a feedback message about claude-tools components (taskmaster skills, hooks, MCP tools, etc.), and the user can triage them in one place.

## One-time setup

In a session running anywhere on this machine:

```
/feedback-inbox-setup
```

This writes `~/.claude/inbox-target.json` and creates the inbox directory.

## Use

- `/feedback <text>` — log a message explicitly.
- Claude may also invoke the `feedback` skill silently when it hits friction with a claude-tools-shipped component (no confirmation needed; the user can review during triage).
- `/inbox` — in this repo: list pending messages and walk them, promoting useful ones to `taskmaster:add-idea` or `taskmaster:bug`.

See `docs/superpowers/specs/2026-05-21-feedback-inbox-design.md` for the design.
```

- [ ] **Step 3: Create empty `__init__.py` files**

Write `plugins/feedback-inbox/scripts/__init__.py` with content `""` (empty file).
Write `plugins/feedback-inbox/tests/__init__.py` with content `""` (empty file).

- [ ] **Step 4: Create test conftest**

Write `plugins/feedback-inbox/tests/conftest.py`:

```python
# plugins/feedback-inbox/tests/conftest.py
"""Shared pytest fixtures for feedback-inbox tests."""
from __future__ import annotations

import sys
from pathlib import Path

# Make `from scripts.resolve_target import ...` work from anywhere.
PLUGIN_ROOT = Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))
```

- [ ] **Step 5: Verify pytest discovers the empty test dir**

Run:
```
pytest plugins/feedback-inbox/tests -q
```
Expected: `no tests ran in 0.0Xs` (success, no failures). If pytest itself isn't on PATH, use `python -m pytest plugins/feedback-inbox/tests -q`.

- [ ] **Step 6: Commit**

```bash
git add plugins/feedback-inbox/
git commit -m "feat(feedback-inbox): plugin scaffold + plugin.json + README"
```

---

## Task 2: `resolve_target.py` — read and validate the config

**Files:**
- Create: `plugins/feedback-inbox/scripts/resolve_target.py`
- Test: `plugins/feedback-inbox/tests/test_resolve_target.py`

**Behaviour:** Reads `~/.claude/inbox-target.json`. Returns a small dataclass `Resolved(inbox: Path | None, enabled: bool, reason: str | None)`. Never raises — every error becomes a `reason` string.

- [ ] **Step 1: Write the failing tests**

Write `plugins/feedback-inbox/tests/test_resolve_target.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.resolve_target import resolve_target


def _write_config(home: Path, payload: dict) -> Path:
    cfg_dir = home / ".claude"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg = cfg_dir / "inbox-target.json"
    cfg.write_text(json.dumps(payload), encoding="utf-8")
    return cfg


def test_missing_config_returns_disabled_with_reason(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))  # Windows fallback
    r = resolve_target()
    assert r.enabled is False
    assert r.inbox is None
    assert r.reason is not None and "not configured" in r.reason.lower()


def test_disabled_flag_returns_disabled(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    _write_config(tmp_path, {"inbox": str(tmp_path / "inbox"), "enabled": False})
    r = resolve_target()
    assert r.enabled is False
    assert "disabled" in r.reason.lower()


def test_valid_config_resolves_and_creates_inbox(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    inbox_path = tmp_path / "inbox"
    _write_config(tmp_path, {"inbox": str(inbox_path), "enabled": True})
    r = resolve_target()
    assert r.enabled is True
    assert r.inbox == inbox_path
    assert inbox_path.is_dir()
    assert r.reason is None


def test_malformed_json_returns_disabled(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    cfg_dir = tmp_path / ".claude"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "inbox-target.json").write_text("{not json", encoding="utf-8")
    r = resolve_target()
    assert r.enabled is False
    assert "parse" in r.reason.lower() or "invalid" in r.reason.lower()


def test_missing_inbox_key_returns_disabled(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    _write_config(tmp_path, {"enabled": True})
    r = resolve_target()
    assert r.enabled is False
    assert "inbox" in r.reason.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```
pytest plugins/feedback-inbox/tests/test_resolve_target.py -v
```
Expected: All 5 tests FAIL with `ModuleNotFoundError: No module named 'scripts.resolve_target'`.

- [ ] **Step 3: Write the implementation**

Write `plugins/feedback-inbox/scripts/resolve_target.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```
pytest plugins/feedback-inbox/tests/test_resolve_target.py -v
```
Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/feedback-inbox/scripts/resolve_target.py plugins/feedback-inbox/tests/test_resolve_target.py
git commit -m "feat(feedback-inbox): resolve_target reads ~/.claude/inbox-target.json"
```

---

## Task 3: `write_message.py` — serialize one message to disk

**Files:**
- Create: `plugins/feedback-inbox/scripts/write_message.py`
- Test: `plugins/feedback-inbox/tests/test_write_message.py`

**Behaviour:** Public function `write_message(inbox: Path, payload: MessagePayload) -> Path` returns the path it wrote. Generates filename `YYYY-MM-DD-HHMM-<slug>.md`. Collisions get `-2`, `-3`, etc. Slug is kebab-case, ≤ 40 chars. Frontmatter uses PyYAML.

- [ ] **Step 1: Write the failing tests**

Write `plugins/feedback-inbox/tests/test_write_message.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```
pytest plugins/feedback-inbox/tests/test_write_message.py -v
```
Expected: All 4 tests FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write the implementation**

Write `plugins/feedback-inbox/scripts/write_message.py`:

```python
"""Serialize one feedback message to the inbox as a markdown file with YAML frontmatter."""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
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

    ts = payload.created.astimezone()  # local-time stamp for filename readability
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```
pytest plugins/feedback-inbox/tests/test_write_message.py -v
```
Expected: All 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/feedback-inbox/scripts/write_message.py plugins/feedback-inbox/tests/test_write_message.py
git commit -m "feat(feedback-inbox): write_message serializes payload to inbox/<slug>.md"
```

---

## Task 4: `list_pending.py` — enumerate the inbox

**Files:**
- Create: `plugins/feedback-inbox/scripts/list_pending.py`
- Test: `plugins/feedback-inbox/tests/test_list_pending.py`

**Behaviour:** `list_pending(inbox: Path) -> ListResult` where `ListResult.messages: list[PendingMessage]` and `ListResult.counts: dict[str, int]` (by category). Reads only top-level `*.md` files (excludes `processed/`). Corrupt frontmatter → message is skipped, an entry appears in `warnings`.

- [ ] **Step 1: Write the failing tests**

Write `plugins/feedback-inbox/tests/test_list_pending.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```
pytest plugins/feedback-inbox/tests/test_list_pending.py -v
```
Expected: All 5 tests FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write the implementation**

Write `plugins/feedback-inbox/scripts/list_pending.py`:

```python
"""List pending messages in the inbox (top-level only; excludes processed/)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

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
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```
pytest plugins/feedback-inbox/tests/test_list_pending.py -v
```
Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/feedback-inbox/scripts/list_pending.py plugins/feedback-inbox/tests/test_list_pending.py
git commit -m "feat(feedback-inbox): list_pending enumerates inbox by category"
```

---

## Task 5: `archive_message.py` — move and update frontmatter

**Files:**
- Create: `plugins/feedback-inbox/scripts/archive_message.py`
- Test: `plugins/feedback-inbox/tests/test_archive_message.py`

**Behaviour:** `archive(path: Path, status: str, promoted_to: str | None = None) -> Path` returns the new path under `processed/<year>/`. Updates frontmatter: sets `status`, adds `processed_at` (ISO timestamp), and `promoted_to` if provided. Idempotent: if the source file is already inside `processed/`, returns its path unchanged.

- [ ] **Step 1: Write the failing tests**

Write `plugins/feedback-inbox/tests/test_archive_message.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```
pytest plugins/feedback-inbox/tests/test_archive_message.py -v
```
Expected: All 5 tests FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write the implementation**

Write `plugins/feedback-inbox/scripts/archive_message.py`:

```python
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
    fm = yaml.safe_load(text[4:end]) or {}
    body = text[end + len("\n---\n"):]
    return fm, body


def archive(path: Path, status: str, promoted_to: str | None = None) -> Path:
    if status not in VALID_ARCHIVE_STATUS:
        raise ValueError(
            f"invalid archive status: {status!r} (expected one of {sorted(VALID_ARCHIVE_STATUS)})"
        )

    # Idempotency: if path is already under processed/, just update frontmatter in place.
    if "processed" in path.parts:
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```
pytest plugins/feedback-inbox/tests/test_archive_message.py -v
```
Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/feedback-inbox/scripts/archive_message.py plugins/feedback-inbox/tests/test_archive_message.py
git commit -m "feat(feedback-inbox): archive moves to processed/<year>/ and updates frontmatter"
```

---

## Task 6: Round-trip integration test

**Files:**
- Create: `plugins/feedback-inbox/tests/test_round_trip.py`

This is a pure-Python integration test that exercises the four scripts together. No skill content is involved.

- [ ] **Step 1: Write the test**

Write `plugins/feedback-inbox/tests/test_round_trip.py`:

```python
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
```

- [ ] **Step 2: Run the test**

Run:
```
pytest plugins/feedback-inbox/tests/test_round_trip.py -v
```
Expected: PASS.

- [ ] **Step 3: Run the full plugin test suite for confidence**

Run:
```
pytest plugins/feedback-inbox/tests -v
```
Expected: All tests PASS (5 + 4 + 5 + 5 + 1 = 20 tests).

- [ ] **Step 4: Commit**

```bash
git add plugins/feedback-inbox/tests/test_round_trip.py
git commit -m "test(feedback-inbox): end-to-end round-trip via the four scripts"
```

---

## Task 7: `feedback` producer skill

**Files:**
- Create: `plugins/feedback-inbox/skills/feedback/SKILL.md`
- Create: `plugins/feedback-inbox/commands/feedback.md`

No new Python. The skill is prose; the command is a thin wrapper.

- [ ] **Step 1: Write the producer skill**

Write `plugins/feedback-inbox/skills/feedback/SKILL.md`:

```markdown
---
name: feedback
description: Drop a feedback message into the claude-tools feedback inbox. Use when the user explicitly requests it ('/feedback', 'log this as feedback', 'send this to claude-tools', 'report this back', 'feedback to the toolmaker') AND proactively, on your own initiative, when you observe friction with a claude-tools-shipped component during a session — a taskmaster skill that errored, a guard-hook that blocked the wrong command, an MCP tool that returned a confusing shape, a skill description that didn't match its behaviour, a slash command that did the wrong thing. Do not fire for generic project friction or external-tool friction; only for claude-tools components (taskmaster, reflect-auto-improve, guard-hooks, statusline, feedback-inbox itself, ue5-materials, etc.). Silent on success — no user confirmation needed; the user reviews during /inbox triage.
---

# feedback — Producer

You drop one feedback message into the configured inbox. One invocation = one message. Never bundle multiple unrelated complaints into one message.

## Scope guard (read before deciding to invoke proactively)

Fire ONLY for friction with components shipped from `claude-tools`:
- taskmaster (any skill, command, MCP tool, hook)
- reflect-auto-improve
- guard-hooks
- statusline
- feedback-inbox itself
- ue5-materials, image-gen, codex-dispatch, reality-reprojection, shader-nodes

DO NOT fire for:
- Bugs in the user's project code.
- Friction with external tools (git, pytest, Node, language servers).
- General confusion that isn't tied to a specific claude-tools component.

If in doubt, don't fire. The user can always invoke `/feedback` explicitly.

## Procedure

1. **Resolve the target.** The plugin is installed at `${CLAUDE_PLUGIN_ROOT}` in every session that has it enabled, regardless of cwd. Probe the config with:

   ```bash
   python -c "import sys, json; sys.path.insert(0, r'${CLAUDE_PLUGIN_ROOT}'); from scripts.resolve_target import resolve_target; r = resolve_target(); print(json.dumps({'enabled': r.enabled, 'inbox': str(r.inbox) if r.inbox else None, 'reason': r.reason}))"
   ```

   If `enabled: false`, emit ONE line to the conversation: `feedback-inbox: <reason> — skipping.` Then stop. Do not raise, do not retry.

2. **Compose the message.** Pick:
   - `source`: `claude` if you're invoking proactively; `user` if the user explicitly dictated text.
   - `category`: `bug` (something is broken) | `friction` (works, but awkward) | `idea` (improvement suggestion) | `praise` (something worked well) | `question` (you want the toolmaker to clarify something).
   - `summary`: one-line, ≤ 120 chars. Lead with the component name (e.g. "taskmaster:pick-task hangs on long worktree paths").
   - `component`: the specific claude-tools subsystem, e.g. `taskmaster/pick-task`, `guard-hooks`, `reflect-auto-improve/harvest`. Required when `source=claude`.
   - `project` + `project_path`: derive from the current working directory — `Path.cwd().name` and the absolute cwd. Leave empty if you can't determine them; do not block.
   - `body`: freeform markdown. Two sections is the convention:
     - `## What happened` — concrete observation, with exact tool calls or error messages if available.
     - `## Suggested fix` — your best guess at what would help. Optional but valued.

3. **Write the message.** Run:

   ```bash
   python -c "
   import sys, json
   from datetime import datetime, timezone
   from pathlib import Path
   sys.path.insert(0, r'${CLAUDE_PLUGIN_ROOT}')
   from scripts.resolve_target import resolve_target
   from scripts.write_message import MessagePayload, write_message
   r = resolve_target()
   if not r.enabled:
       print(f'feedback-inbox: {r.reason} — skipping.'); sys.exit(0)
   payload = MessagePayload(
       source='<claude|user>',
       category='<bug|friction|idea|praise|question>',
       summary='<your one-line summary>',
       body='''<your multi-line body>''',
       project=Path.cwd().name,
       project_path=str(Path.cwd()),
       component='<claude-tools/component>',
       created=datetime.now(tz=timezone.utc),
   )
   path = write_message(r.inbox, payload)
   print(f'feedback-inbox: logged \"{payload.summary}\" → {path.name}')
   "
   ```

   Substitute the angle-bracketed placeholders with your composed values. Be careful to escape any single quotes inside the body, or use a heredoc / temp file if the body is long.

4. **Emit one line to the conversation.** Whatever the write script prints. Do not say more. The user reviews during `/inbox` triage, not now.

## Failure handling

- If the write script errors (permissions, disk full, malformed input), emit one line: `feedback-inbox: write failed — <error>`. Do not retry. Do not raise.
- If you can't determine `component` for a `source=claude` message, don't fire. The whole point of the scope guard is to tie observations to specific subsystems; an untagged message is noise.

## Anti-patterns

- Bundling multiple unrelated observations into one message. One issue per message.
- Firing for friction with the user's project code (not a claude-tools component).
- Asking the user "should I log this as feedback?" — proactive invocation is silent by design.
- Re-logging the same observation a second time in the same session. If you already wrote one, you're done.
```

- [ ] **Step 2: Write the slash command wrapper**

Write `plugins/feedback-inbox/commands/feedback.md`:

```markdown
---
description: Log a message into the claude-tools feedback inbox.
argument-hint: "<freeform feedback text>"
---

Invoke the `feedback-inbox:feedback` skill with the user-dictated message in `$ARGUMENTS`.

- Set `source=user` (the user explicitly asked, not a proactive Claude observation).
- Choose `category` from `$ARGUMENTS` content; default to `friction` if unclear.
- Choose `component` from context if obvious (e.g. user is in a taskmaster command transcript); leave empty if unclear.
- `summary` = first line of `$ARGUMENTS` (≤ 120 chars).
- `body` = rest of `$ARGUMENTS` formatted as a `## What happened` section.

Then proceed with the skill procedure (resolve target → write → one-line confirmation).
```

- [ ] **Step 3: Commit**

```bash
git add plugins/feedback-inbox/skills/feedback/ plugins/feedback-inbox/commands/feedback.md
git commit -m "feat(feedback-inbox): feedback skill + /feedback slash command"
```

---

## Task 8: `inbox-triage` reader skill

**Files:**
- Create: `plugins/feedback-inbox/skills/inbox-triage/SKILL.md`
- Create: `plugins/feedback-inbox/commands/inbox.md`

- [ ] **Step 1: Write the triage skill**

Write `plugins/feedback-inbox/skills/inbox-triage/SKILL.md`:

```markdown
---
name: inbox-triage
description: List and walk pending messages in the claude-tools feedback inbox, routing accepted items to taskmaster:add-idea or taskmaster:bug and archiving the rest. Invoke when the user says '/inbox', 'triage the inbox', 'process feedback', 'what's in the inbox', 'any feedback to look at', or sits down in the claude-tools repo and asks what's new. Reads messages written by the feedback-inbox:feedback producer. Non-destructive — processed messages move to inbox/processed/<year>/, never deleted.
---

# inbox-triage — Reader

You walk pending feedback messages in the configured inbox, present each one, and let the user pick an action.

## Procedure

1. **List pending.** Run:

   ```bash
   python -c "
   import sys, json
   sys.path.insert(0, r'${CLAUDE_PLUGIN_ROOT}')
   from scripts.resolve_target import resolve_target
   from scripts.list_pending import list_pending
   r = resolve_target()
   if not r.enabled:
       print(f'feedback-inbox: {r.reason}'); sys.exit(0)
   res = list_pending(r.inbox)
   print(json.dumps({
       'count': len(res.messages),
       'counts': res.counts,
       'warnings': res.warnings,
       'messages': [{'path': str(m.path), 'id': m.id, 'category': m.category,
                     'component': m.component, 'summary': m.summary, 'source': m.source,
                     'project': m.project, 'created': m.created} for m in res.messages],
   }, indent=2))
   "
   ```

   Empty inbox → emit `feedback-inbox: inbox is empty.` and stop.

2. **Show the dashboard.** Print a one-screen summary:

   ```
   feedback-inbox: 7 pending  (friction: 3, bug: 2, idea: 1, praise: 1)
   ```

   Plus any warnings on a separate line (corrupt frontmatter, etc.).

3. **Walk messages one by one.** For each message, in order:
   1. Read the file with `Read` and show frontmatter + body to the user.
   2. Use `AskUserQuestion` with four options:
      - **Promote → idea** — invokes the `taskmaster:add-idea` skill with the message body prefilled as the idea body and `summary` as the title. After the idea is created, archive the message: status `promoted`, `promoted_to: IDEA-NNN`.
      - **Promote → bug** — invokes the `taskmaster:bug` skill similarly. Archive with status `promoted`, `promoted_to: B-NNN`.
      - **Archive** — non-actionable but worth keeping. Archive with status `processed`.
      - **Drop** — noise. Archive with status `dropped`.
   3. Perform the chosen action.

4. **Archive via the script:**

   ```bash
   python -c "
   import sys
   from pathlib import Path
   sys.path.insert(0, r'${CLAUDE_PLUGIN_ROOT}')
   from scripts.archive_message import archive
   new_path = archive(Path(r'<message path>'), status='<processed|promoted|dropped>', promoted_to='<id or None>')
   print(f'archived → {new_path}')
   "
   ```

5. **Summarize.** After the walk, emit one line:

   ```
   inbox triage: <N> promoted, <M> archived, <K> dropped.
   ```

## Fallback when taskmaster isn't available

If you can't invoke `taskmaster:add-idea` or `taskmaster:bug` (e.g. user is running triage outside a taskmaster project), the **Promote** options fall back to archive-only with status `processed`. Emit one line explaining the fallback: `taskmaster not available here — archiving as processed instead of promoting.`

## Anti-patterns

- Skipping the per-message walk and bulk-archiving everything. Each message gets a decision.
- Deleting messages. Never. Archive only.
- Re-creating ideas/bugs from messages you've already archived in this session. If a message is moved out of `inbox/*.md`, it's done.
```

- [ ] **Step 2: Write the slash command wrapper**

Write `plugins/feedback-inbox/commands/inbox.md`:

```markdown
---
description: Triage pending feedback messages in the claude-tools inbox.
argument-hint: ""
---

Invoke the `feedback-inbox:inbox-triage` skill.
```

- [ ] **Step 3: Commit**

```bash
git add plugins/feedback-inbox/skills/inbox-triage/ plugins/feedback-inbox/commands/inbox.md
git commit -m "feat(feedback-inbox): inbox-triage skill + /inbox slash command"
```

---

## Task 9: `/feedback-inbox-setup` one-shot setup

**Files:**
- Create: `plugins/feedback-inbox/commands/feedback-inbox-setup.md`

This command writes `~/.claude/inbox-target.json`, creates the inbox dir, and (if the inbox sits inside a git repo) appends `inbox/` to that repo's `.gitignore`.

- [ ] **Step 1: Write the setup command**

Write `plugins/feedback-inbox/commands/feedback-inbox-setup.md`:

```markdown
---
description: One-shot setup for feedback-inbox — writes ~/.claude/inbox-target.json and creates the inbox dir.
argument-hint: "[--inbox <path>] [--disable]"
---

Run the feedback-inbox setup.

## Procedure

1. **Parse `$ARGUMENTS`:**
   - `--inbox <path>` → explicit inbox path. If absent, ask the user with `AskUserQuestion`, offering two options:
     - **Inside this repo:** `<absolute path to claude-tools repo>/inbox`
     - **Outside any repo:** `~/.claude/inbox`
   - `--disable` → write `{"inbox": "<existing-or-default>", "enabled": false}` and stop.

2. **Resolve the path.** Expand `~` to the user home. Convert to absolute. Make sure no trailing slash.

3. **Write the config** at `~/.claude/inbox-target.json`:

   ```bash
   python -c "
   import json, os
   from pathlib import Path
   home = Path(os.environ.get('USERPROFILE') or os.environ.get('HOME') or Path.home())
   cfg = home / '.claude' / 'inbox-target.json'
   cfg.parent.mkdir(parents=True, exist_ok=True)
   cfg.write_text(json.dumps({'inbox': r'<resolved path>', 'enabled': True}, indent=2), encoding='utf-8')
   print(f'wrote {cfg}')
   "
   ```

4. **Create the inbox dir** (`mkdir -p <resolved path>`).

5. **Gitignore step (conditional).** If the inbox path sits inside a git working tree, append `inbox/` to that repo's `.gitignore` if and only if no existing line starts with `inbox/`. Skip silently otherwise.

   ```bash
   python -c "
   import subprocess, sys
   from pathlib import Path
   inbox = Path(r'<resolved path>')
   try:
       repo_root = subprocess.check_output(
           ['git', '-C', str(inbox.parent), 'rev-parse', '--show-toplevel'],
           stderr=subprocess.DEVNULL, text=True).strip()
   except subprocess.CalledProcessError:
       print('inbox is outside any git repo — no .gitignore edit needed'); sys.exit(0)
   repo_root = Path(repo_root)
   gi = repo_root / '.gitignore'
   existing = gi.read_text(encoding='utf-8') if gi.exists() else ''
   # Compute the path relative to the repo root; use forward slashes.
   rel = inbox.relative_to(repo_root).as_posix().rstrip('/') + '/'
   if any(line.strip() == rel for line in existing.splitlines()):
       print(f'.gitignore already has {rel}'); sys.exit(0)
   with gi.open('a', encoding='utf-8') as f:
       if existing and not existing.endswith('\n'):
           f.write('\n')
       f.write(f'\n# feedback-inbox\n{rel}\n')
   print(f'appended {rel} to {gi}')
   "
   ```

6. **Verify.** Run `python -c "import sys; sys.path.insert(0, r'${CLAUDE_PLUGIN_ROOT}'); from scripts.resolve_target import resolve_target; r = resolve_target(); print('ok' if r.enabled else f'fail: {r.reason}')"`. If it prints `ok`, emit:

   ```
   feedback-inbox set up. Inbox: <resolved path>. Use /feedback to log a message, /inbox to triage.
   ```

   Otherwise emit the failure reason.
```

- [ ] **Step 2: Commit**

```bash
git add plugins/feedback-inbox/commands/feedback-inbox-setup.md
git commit -m "feat(feedback-inbox): /feedback-inbox-setup writes config and seeds inbox"
```

---

## Task 10: Manual smoke test on this machine

This task is not automated — it verifies the plugin works end-to-end in real Claude Code sessions on the current machine.

- [ ] **Step 1: Reload Claude Code so it picks up the new plugin**

In the running Claude Code session, run `/plugins` to confirm `feedback-inbox` is listed. If not, restart the session.

- [ ] **Step 2: Run the setup command**

```
/feedback-inbox-setup
```

When prompted, choose **Inside this repo** so the inbox lands at `<claude-tools>/inbox/`. Confirm:
- `~/.claude/inbox-target.json` exists and contains the expected JSON.
- `<claude-tools>/inbox/` directory exists.
- `<claude-tools>/.gitignore` has an `inbox/` line at the bottom.

- [ ] **Step 3: Log a test message explicitly**

```
/feedback feedback-inbox first smoke test — checking the round trip works
```

Confirm:
- A file `inbox/YYYY-MM-DD-HHMM-feedback-inbox-first-smoke-test-….md` appears.
- Its frontmatter has `source: user`, `category: friction` (or similar), `summary` and `body` populated.

- [ ] **Step 4: Triage the inbox**

```
/inbox
```

The triage walk should show the smoke-test message. Choose **Drop**. Confirm:
- The message moves to `inbox/processed/2026/<original-name>.md`.
- Frontmatter now has `status: dropped` and a `processed_at` timestamp.
- `/inbox` rerun shows `inbox is empty`.

- [ ] **Step 5: Proactive smoke from another project**

In a fresh Claude Code session in a different project on this machine (e.g. CodeMaestro), ask Claude to invoke the `feedback-inbox:feedback` skill explicitly with a `source=claude` test message and `component=taskmaster/pick-task`. Confirm the file lands in `<claude-tools>/inbox/` with `project` set to the foreign project's basename and `source: claude`.

- [ ] **Step 6: Commit any final touch-ups**

If the smoke test surfaced any small fixes (wording in skill files, error messages, etc.), commit them:

```bash
git add -A
git commit -m "chore(feedback-inbox): smoke-test fixups"
```

If no fixups were needed, skip this step.

---

## Spec coverage check

| Spec section | Implementing task(s) |
|---|---|
| Plugin layout | Task 1 |
| `resolve_target.py` behaviour + failure modes | Task 2 |
| Message format / frontmatter | Task 3 |
| `list_pending.py` behaviour | Task 4 |
| Lifecycle table / `archive_message.py` | Task 5 |
| Round-trip / integration testing | Task 6 |
| `feedback` skill trigger surface + scope guard | Task 7 |
| `/feedback` slash command | Task 7 |
| `inbox-triage` skill + 4 actions + taskmaster fallback | Task 8 |
| `/inbox` slash command | Task 8 |
| `/feedback-inbox-setup` config writer + gitignore handling | Task 9 |
| Manual smoke (foreign Claude → triage round trip) | Task 10 |

All spec sections are covered. No placeholders remain in the plan.
