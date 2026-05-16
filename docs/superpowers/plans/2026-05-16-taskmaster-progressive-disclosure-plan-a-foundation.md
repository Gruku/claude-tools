# Plan A — Foundation (tldr schema + slim-default MCP) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a required `tldr` field to every entity (tasks, issues, lessons) and make every `_get` / `_list` MCP tool return a slim view by default, with `verbose=true` / `sections=[...]` / `expand_links=true` flags for deeper retrieval.

**Architecture:** Two-layer change. (1) Data layer in `plugins/taskmaster/taskmaster_v3.py` gains a tldr-extraction helper, slim-view extractor, and canonical-section resolver. (2) FastMCP wrapper layer in `plugins/taskmaster/backlog_server.py` exposes new params on every `_get` and `_list` tool. Backward-compatible: `verbose=true` reproduces today's output bit-for-bit.

**Tech Stack:** Python 3.11+, FastMCP, PyYAML, pytest. No new deps.

**Spec:** `docs/superpowers/specs/2026-05-15-taskmaster-progressive-disclosure-design.md` §1–§2.

---

## File Structure

**Modify:**
- `plugins/taskmaster/taskmaster_v3.py` — add `extract_tldr()`, `slim_entity()`, `resolve_sections()`, `expand_link_ids()`, `CANONICAL_SECTIONS` constants, update `HEAVY_FIELDS` exclusion of `tldr`/`next_step`
- `plugins/taskmaster/backlog_server.py` — add `verbose`/`sections`/`expand_links` params on `backlog_get_task` (L900), `backlog_handover_get` (L1751), `backlog_issue_get` (L1966), `backlog_lesson_get` (L2351), `backlog_status` (L713), `backlog_list_tasks` (L848); add list-slim mode to `backlog_handover_list` / `backlog_issue_list` / `backlog_lesson_list`
- `plugins/taskmaster/backlog_server.py` — `backlog_add_task`, `backlog_update_task`, `backlog_issue_create`, `backlog_lesson_create`, `backlog_idea_create` enforce `tldr` (autogen with `tldr_autogen` flag if absent)
- `plugins/taskmaster/backlog_server.py` — `backlog_validate` reports missing tldrs (warning only during grace period)
- `plugins/taskmaster/CHANGELOG.md` — entry for v3.X foundation release

**Create:**
- `plugins/taskmaster/tests/test_tldr_extraction.py`
- `plugins/taskmaster/tests/test_tldr_required_on_create.py`
- `plugins/taskmaster/tests/test_tldr_backfill.py`
- `plugins/taskmaster/tests/test_slim_get_task.py`
- `plugins/taskmaster/tests/test_slim_handover_get.py`
- `plugins/taskmaster/tests/test_slim_issue_get.py`
- `plugins/taskmaster/tests/test_slim_lesson_get.py`
- `plugins/taskmaster/tests/test_slim_list_tools.py`
- `plugins/taskmaster/tests/test_sections_parameter.py`
- `plugins/taskmaster/tests/test_expand_links.py`
- `plugins/taskmaster/tests/test_backlog_status_slim.py`
- `plugins/taskmaster/tests/test_validate_tldr_warning.py`
- `plugins/taskmaster/tests/test_foundation_smoke.py`
- `plugins/taskmaster/scripts/backfill_tldr.py` — one-shot migration CLI

---

## Phase 1 — Utilities and constants

### Task 1: Add `extract_tldr()` helper

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py` (add near top, after `atomic_write`)
- Test: `plugins/taskmaster/tests/test_tldr_extraction.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# plugins/taskmaster/tests/test_tldr_extraction.py
from plugins.taskmaster.taskmaster_v3 import extract_tldr


def test_extract_tldr_from_first_sentence():
    body = "Fix the auth middleware. It currently stores tokens in localStorage."
    assert extract_tldr(body) == "Fix the auth middleware."


def test_extract_tldr_strips_markdown_headings():
    body = "## Why\n\nFix the auth middleware. More detail follows."
    assert extract_tldr(body) == "Fix the auth middleware."


def test_extract_tldr_caps_at_200_chars():
    long_sentence = "A" * 250 + "."
    result = extract_tldr(long_sentence)
    assert len(result) <= 200
    assert result.endswith("…")


def test_extract_tldr_empty_body_returns_none():
    assert extract_tldr("") is None
    assert extract_tldr("   \n\n   ") is None


def test_extract_tldr_collapses_whitespace():
    body = "Fix   the\nauth\n\nmiddleware."
    assert extract_tldr(body) == "Fix the auth middleware."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_tldr_extraction.py -v`
Expected: FAIL with `ImportError: cannot import name 'extract_tldr'`

- [ ] **Step 3: Implement `extract_tldr()`**

Add to `plugins/taskmaster/taskmaster_v3.py` after the `atomic_write()` function (~line 47):

```python
# ── tldr extraction ───────────────────────────────────────────

TLDR_MAX_CHARS = 200

_HEADING_RE = re.compile(r"^#{1,6}\s+.*$", re.MULTILINE)
_SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s+")
_WHITESPACE_RE = re.compile(r"\s+")


def extract_tldr(body: str | None) -> str | None:
    """Extract a tldr from markdown body text.

    Strategy: strip markdown headings, collapse whitespace, take the first
    sentence (split on .!?), cap at TLDR_MAX_CHARS with an ellipsis if needed.
    Returns None if the body is empty or all whitespace.
    """
    if not body or not body.strip():
        return None
    text = _HEADING_RE.sub("", body).strip()
    text = _WHITESPACE_RE.sub(" ", text)
    if not text:
        return None
    parts = _SENTENCE_END_RE.split(text, maxsplit=1)
    first = parts[0].strip()
    if len(first) > TLDR_MAX_CHARS:
        first = first[: TLDR_MAX_CHARS - 1].rstrip() + "…"
    return first or None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_tldr_extraction.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_tldr_extraction.py
git commit -m "feat(taskmaster): add extract_tldr() utility for auto-generating tldrs from body"
```

---

### Task 2: Add `CANONICAL_SECTIONS` constants

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py`
- Test: `plugins/taskmaster/tests/test_canonical_sections.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# plugins/taskmaster/tests/test_canonical_sections.py
from plugins.taskmaster.taskmaster_v3 import CANONICAL_SECTIONS


def test_canonical_sections_per_entity_type():
    assert "spec" in CANONICAL_SECTIONS["task"]
    assert "plan" in CANONICAL_SECTIONS["task"]
    assert "notes" in CANONICAL_SECTIONS["task"]
    assert "review_instructions" in CANONICAL_SECTIONS["task"]

    assert set(CANONICAL_SECTIONS["handover"]) == {"decisions", "notes", "blockers", "where_id_start"}
    assert set(CANONICAL_SECTIONS["issue"]) == {"repro", "investigation", "notes"}
    assert set(CANONICAL_SECTIONS["lesson"]) == {"why", "what_to_do", "examples"}


def test_task_sections_include_docs_keys():
    expected_doc_keys = {"plan", "spec", "design", "analysis", "roadmap"}
    assert expected_doc_keys.issubset(set(CANONICAL_SECTIONS["task"]))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_canonical_sections.py -v`
Expected: FAIL with `ImportError: cannot import name 'CANONICAL_SECTIONS'`

- [ ] **Step 3: Add constants**

Add to `plugins/taskmaster/taskmaster_v3.py` (after `TLDR_MAX_CHARS`):

```python
# Canonical section names per entity type.
# For tasks: 'notes' and 'review_instructions' are inline frontmatter fields;
# 'spec'/'plan'/'design'/'analysis'/'roadmap' are resolved from task.docs.<key>
# (external file paths in the docs dict).
CANONICAL_SECTIONS: dict[str, tuple[str, ...]] = {
    "task": ("notes", "review_instructions", "spec", "plan", "design", "analysis", "roadmap"),
    "handover": ("decisions", "notes", "blockers", "where_id_start"),
    "issue": ("repro", "investigation", "notes"),
    "lesson": ("why", "what_to_do", "examples"),
}

TASK_INLINE_SECTIONS: frozenset[str] = frozenset({"notes", "review_instructions"})
TASK_DOC_SECTIONS: frozenset[str] = frozenset({"spec", "plan", "design", "analysis", "roadmap"})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_canonical_sections.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_canonical_sections.py
git commit -m "feat(taskmaster): define canonical section names per entity type"
```

---

## Phase 2 — `tldr` field on entity writes

### Task 3: Require `tldr` on `backlog_add_task` / `backlog_update_task`

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py` — `backlog_add_task`, `backlog_update_task`
- Test: `plugins/taskmaster/tests/test_tldr_required_on_create.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# plugins/taskmaster/tests/test_tldr_required_on_create.py
import pytest
from plugins.taskmaster.backlog_server import backlog_add_task, backlog_get_task


def test_add_task_with_tldr_succeeds(tmp_taskmaster):  # fixture exists in conftest
    result = backlog_add_task(
        epic="test-epic",
        task_id="T-tldr-1",
        title="Test task",
        tldr="One-line essence of the task.",
    )
    assert "T-tldr-1" in result
    body = backlog_get_task("T-tldr-1", verbose=True)
    assert "One-line essence" in body


def test_add_task_without_tldr_autogenerates_from_body(tmp_taskmaster):
    result = backlog_add_task(
        epic="test-epic",
        task_id="T-tldr-2",
        title="Test task",
        notes="Fix the auth middleware. It breaks on Friday deploys.",
    )
    body = backlog_get_task("T-tldr-2", verbose=True)
    assert "Fix the auth middleware." in body
    assert "tldr_autogen: true" in body


def test_add_task_without_tldr_or_body_uses_title(tmp_taskmaster):
    backlog_add_task(epic="test-epic", task_id="T-tldr-3", title="Refactor auth")
    body = backlog_get_task("T-tldr-3", verbose=True)
    assert "Refactor auth" in body
    assert "tldr_autogen: true" in body
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_tldr_required_on_create.py -v`
Expected: FAIL — `backlog_add_task` doesn't accept `tldr` kwarg.

- [ ] **Step 3: Update `backlog_add_task` signature and body**

In `plugins/taskmaster/backlog_server.py`, locate `backlog_add_task` (search for `def backlog_add_task`). Add `tldr` kwarg, autogen fallback:

```python
@mcp.tool()
def backlog_add_task(
    epic: str,
    task_id: str,
    title: str,
    tldr: str = "",
    # ... existing kwargs unchanged ...
    notes: str = "",
    # ...
) -> str:
    # ... existing param validation ...
    task: dict[str, Any] = {"id": task_id, "title": title, ...}
    # NEW: tldr handling
    autogen = False
    if not tldr:
        body_source = notes or title
        tldr = tm.extract_tldr(body_source) or title[: tm.TLDR_MAX_CHARS]
        autogen = True
    task["tldr"] = tldr
    if autogen:
        task["tldr_autogen"] = True
    # ... rest of existing logic ...
```

Apply the same pattern to `backlog_update_task` — when `tldr=""` (default keep-existing), leave alone; when caller passes a non-empty value, write it and remove `tldr_autogen` flag.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_tldr_required_on_create.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_tldr_required_on_create.py
git commit -m "feat(taskmaster): require tldr on add_task/update_task, autogen with flag"
```

---

### Task 4: Require `tldr` on `backlog_issue_create`

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py` — `backlog_issue_create`
- Test: `plugins/taskmaster/tests/test_tldr_required_on_create.py` (extend)

- [ ] **Step 1: Add failing test**

Append to `tests/test_tldr_required_on_create.py`:

```python
from plugins.taskmaster.backlog_server import backlog_issue_create, backlog_issue_get


def test_issue_create_with_tldr(tmp_taskmaster):
    backlog_issue_create(
        title="Auth fails on Friday",
        severity="P1",
        tldr="Auth middleware crashes during Friday deploys.",
        impact="3 customers blocked",
    )
    body = backlog_issue_get("ISS-001", verbose=True)
    assert "Auth middleware crashes" in body


def test_issue_create_autogen_tldr_from_impact(tmp_taskmaster):
    backlog_issue_create(
        title="Auth fails",
        severity="P1",
        impact="Auth middleware crashes during Friday deploys.",
    )
    body = backlog_issue_get("ISS-002", verbose=True)
    assert "Auth middleware crashes" in body
    assert "tldr_autogen: true" in body
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_tldr_required_on_create.py::test_issue_create_with_tldr -v`
Expected: FAIL — `tldr` kwarg not accepted.

- [ ] **Step 3: Update `backlog_issue_create`**

Add `tldr` kwarg with autogen-from-impact-or-title fallback:

```python
@mcp.tool()
def backlog_issue_create(
    title: str,
    severity: str = "P3",
    tldr: str = "",
    impact: str = "",
    # ... existing kwargs ...
) -> str:
    # ... existing logic that builds frontmatter dict ...
    autogen = False
    if not tldr:
        tldr = tm.extract_tldr(impact) or title[: tm.TLDR_MAX_CHARS]
        autogen = True
    frontmatter["tldr"] = tldr
    if autogen:
        frontmatter["tldr_autogen"] = True
    # ... rest unchanged ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_tldr_required_on_create.py -v`
Expected: 5 passed total.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_tldr_required_on_create.py
git commit -m "feat(taskmaster): require tldr on issue_create with impact-autogen fallback"
```

---

### Task 5: Require `tldr` on `backlog_lesson_create` and `backlog_idea_create`

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py` — `backlog_lesson_create`, `backlog_idea_create`
- Test: `plugins/taskmaster/tests/test_tldr_required_on_create.py` (extend)

- [ ] **Step 1: Add failing tests**

Append:

```python
from plugins.taskmaster.backlog_server import (
    backlog_lesson_create, backlog_lesson_get,
    backlog_idea_create,
)


def test_lesson_create_with_tldr(tmp_taskmaster):
    backlog_lesson_create(
        title="Always use atomic writes",
        kind="pattern",
        tldr="Use atomic_write() for any file mutation; prevents corruption on crash.",
        why="...", what_to_do="...",
    )
    body = backlog_lesson_get("L-001", verbose=True)
    assert "Use atomic_write()" in body


def test_lesson_autogen_from_what_to_do(tmp_taskmaster):
    backlog_lesson_create(
        title="Atomic writes",
        kind="pattern",
        what_to_do="Use atomic_write() for every file mutation.",
    )
    body = backlog_lesson_get("L-002", verbose=True)
    assert "Use atomic_write()" in body
    assert "tldr_autogen: true" in body


def test_idea_create_with_tldr(tmp_taskmaster):
    result = backlog_idea_create(
        title="Add dark mode",
        tldr="Toggle dark mode in viewer settings.",
    )
    assert "IDEA-" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest plugins/taskmaster/tests/test_tldr_required_on_create.py -k lesson_create -v`
Expected: FAIL — `tldr` kwarg not accepted.

- [ ] **Step 3: Update `backlog_lesson_create` and `backlog_idea_create`**

For lessons (autogen source priority: `what_to_do` → `why` → `title`):
```python
autogen = False
if not tldr:
    tldr = tm.extract_tldr(what_to_do) or tm.extract_tldr(why) or title[: tm.TLDR_MAX_CHARS]
    autogen = True
frontmatter["tldr"] = tldr
if autogen:
    frontmatter["tldr_autogen"] = True
```

For ideas (autogen source priority: `body` → `title`):
```python
autogen = False
if not tldr:
    tldr = tm.extract_tldr(body) or title[: tm.TLDR_MAX_CHARS]
    autogen = True
frontmatter["tldr"] = tldr
if autogen:
    frontmatter["tldr_autogen"] = True
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest plugins/taskmaster/tests/test_tldr_required_on_create.py -v`
Expected: 8 passed total.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_tldr_required_on_create.py
git commit -m "feat(taskmaster): require tldr on lesson_create and idea_create"
```

---

## Phase 3 — Backfill migration

### Task 6: Add `backfill_tldr()` data-layer helper

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py`
- Test: `plugins/taskmaster/tests/test_tldr_backfill.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# plugins/taskmaster/tests/test_tldr_backfill.py
from plugins.taskmaster.taskmaster_v3 import backfill_tldr


def test_backfill_tldr_adds_when_missing():
    fm = {"id": "T-001", "title": "Refactor auth"}
    body = "Refactor auth middleware. Steps follow."
    new_fm, changed = backfill_tldr(fm, body)
    assert changed is True
    assert new_fm["tldr"] == "Refactor auth middleware."
    assert new_fm["tldr_autogen"] is True


def test_backfill_tldr_skips_when_present():
    fm = {"id": "T-001", "title": "Refactor auth", "tldr": "Existing tldr."}
    body = "Some body."
    new_fm, changed = backfill_tldr(fm, body)
    assert changed is False
    assert new_fm["tldr"] == "Existing tldr."
    assert "tldr_autogen" not in new_fm


def test_backfill_tldr_uses_title_when_body_empty():
    fm = {"id": "T-001", "title": "Refactor auth middleware"}
    new_fm, changed = backfill_tldr(fm, "")
    assert changed is True
    assert new_fm["tldr"] == "Refactor auth middleware"
    assert new_fm["tldr_autogen"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_tldr_backfill.py -v`
Expected: FAIL — `cannot import name 'backfill_tldr'`.

- [ ] **Step 3: Implement `backfill_tldr()`**

Add to `taskmaster_v3.py`:

```python
def backfill_tldr(frontmatter: dict[str, Any], body: str = "") -> tuple[dict[str, Any], bool]:
    """If frontmatter lacks a tldr, generate one and mark tldr_autogen=True.

    Returns (frontmatter, changed). Source priority: body → title. Never overwrites
    an existing tldr. Idempotent.
    """
    if frontmatter.get("tldr"):
        return frontmatter, False
    new_fm = dict(frontmatter)
    tldr = extract_tldr(body) or (frontmatter.get("title") or "")[:TLDR_MAX_CHARS]
    if not tldr:
        return frontmatter, False
    new_fm["tldr"] = tldr
    new_fm["tldr_autogen"] = True
    return new_fm, True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_tldr_backfill.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_tldr_backfill.py
git commit -m "feat(taskmaster): backfill_tldr() helper for migration"
```

---

### Task 7: Backfill migration CLI script

**Files:**
- Create: `plugins/taskmaster/scripts/backfill_tldr.py`
- Test: `plugins/taskmaster/tests/test_tldr_backfill.py` (extend)

- [ ] **Step 1: Add failing integration test**

Append to `tests/test_tldr_backfill.py`:

```python
import subprocess
from pathlib import Path


def test_backfill_script_processes_all_entities(tmp_taskmaster):
    # tmp_taskmaster fixture creates a .taskmaster dir with one task, one issue,
    # one lesson, all WITHOUT tldr (legacy data).
    result = subprocess.run(
        ["python", "-m", "plugins.taskmaster.scripts.backfill_tldr",
         "--root", str(tmp_taskmaster)],
        capture_output=True, text=True, check=True,
    )
    assert "backfilled" in result.stdout.lower()

    # Verify tldrs were added
    from plugins.taskmaster.taskmaster_v3 import read_task_file
    task_path = Path(tmp_taskmaster) / ".taskmaster" / "tasks" / "T-legacy-1.md"
    fm, _ = read_task_file(task_path)
    assert "tldr" in fm
    assert fm.get("tldr_autogen") is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_tldr_backfill.py::test_backfill_script_processes_all_entities -v`
Expected: FAIL — script does not exist.

- [ ] **Step 3: Create the script**

```python
# plugins/taskmaster/scripts/backfill_tldr.py
"""One-shot backfill: add tldr fields to legacy tasks/issues/lessons/ideas.

Idempotent — re-running only touches entities still missing a tldr. Skips
handovers (they already require tldr at write time).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from plugins.taskmaster import taskmaster_v3 as tm


def _backfill_dir(directory: Path) -> int:
    """Backfill all .md files under directory. Returns count of changes."""
    if not directory.exists():
        return 0
    changed = 0
    for path in sorted(directory.glob("*.md")):
        fm, body = tm.read_task_file(path)
        new_fm, did_change = tm.backfill_tldr(fm, body)
        if did_change:
            tm.write_task_file(path, new_fm, body)
            changed += 1
            print(f"  backfilled {path.name}: {new_fm['tldr']!r}")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, help="Project root containing .taskmaster/")
    args = parser.parse_args()

    base = Path(args.root) / ".taskmaster"
    if not base.exists():
        print(f"No .taskmaster/ at {args.root}", file=sys.stderr)
        return 2

    total = 0
    for subdir in ("tasks", "issues", "lessons", "ideas"):
        d = base / subdir
        print(f"Scanning {d}...")
        total += _backfill_dir(d)

    print(f"\nDone. {total} entities backfilled.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Also create `plugins/taskmaster/scripts/__init__.py` if it doesn't exist (empty file).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_tldr_backfill.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/scripts/backfill_tldr.py plugins/taskmaster/scripts/__init__.py plugins/taskmaster/tests/test_tldr_backfill.py
git commit -m "feat(taskmaster): backfill_tldr CLI for migrating legacy entities"
```

---

## Phase 4 — Slim view helpers

### Task 8: Implement `slim_entity()` extractor

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py`
- Test: `plugins/taskmaster/tests/test_slim_view.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# plugins/taskmaster/tests/test_slim_view.py
from plugins.taskmaster.taskmaster_v3 import slim_entity


def test_slim_task():
    full = {
        "id": "T-001", "title": "Refactor auth",
        "tldr": "Refactor the middleware.",
        "next_step": "Write failing test first",
        "status": "in-progress", "priority": "high",
        "depends_on": ["T-002"],
        "related_issues": ["ISS-007"],
        "related_lessons": ["L-003"],
        "docs": {"plan": "docs/plan.md", "spec": "docs/spec.md"},
        "notes": "long notes content here",                  # heavy — excluded
        "review_instructions": "lots of detail here",         # heavy — excluded
        "_body": "## Why\n\nLots of body text.",              # body — excluded
    }
    slim = slim_entity(full, kind="task")
    assert slim["id"] == "T-001"
    assert slim["tldr"] == "Refactor the middleware."
    assert slim["next_step"] == "Write failing test first"
    assert slim["status"] == "in-progress"
    assert slim["depends_on"] == ["T-002"]
    assert slim["docs_available"] == ["plan", "spec"]
    assert "notes" not in slim
    assert "review_instructions" not in slim
    assert "_body" not in slim


def test_slim_issue():
    full = {
        "id": "ISS-007", "title": "Auth fails",
        "tldr": "Auth crashes on Friday.",
        "severity": "P1", "status": "open",
        "impact": "3 customers blocked",
        "components": ["auth"],
        "related_tasks": ["T-001"],
        "_body": "Repro steps...",
    }
    slim = slim_entity(full, kind="issue")
    assert slim["severity"] == "P1"
    assert slim["tldr"] == "Auth crashes on Friday."
    assert "_body" not in slim


def test_slim_lesson():
    full = {
        "id": "L-001", "title": "Atomic writes",
        "tldr": "Use atomic_write() everywhere.",
        "kind": "pattern", "tier": "core",
        "reinforce_count": 3,
        "files": ["*.py"],
        "_body": "## Why\n\n...",
    }
    slim = slim_entity(full, kind="lesson")
    assert slim["kind"] == "pattern"
    assert slim["tier"] == "core"
    assert "_body" not in slim


def test_slim_handover():
    full = {
        "id": "HND-012",
        "tldr": "Auth refactor — next: backfill migration.",
        "next_action": "Run backfill on staging",
        "task_ids": ["T-001"],
        "session_kind": "context-handoff",
        "status": "open",
        "_body": "## Decisions\n\n...",
    }
    slim = slim_entity(full, kind="handover")
    assert slim["next_action"] == "Run backfill on staging"
    assert slim["status"] == "open"
    assert "_body" not in slim
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_slim_view.py -v`
Expected: FAIL — `cannot import name 'slim_entity'`.

- [ ] **Step 3: Implement `slim_entity()`**

Add to `taskmaster_v3.py`:

```python
# Fields kept in the slim view, per entity kind. Everything not listed is excluded.
SLIM_FIELDS: dict[str, tuple[str, ...]] = {
    "task": (
        "id", "title", "tldr", "next_step", "status", "priority",
        "estimate", "phase", "epic",
        "depends_on", "related_issues", "related_lessons",
        "started", "completed", "branch", "worktree",
        "blockers", "tldr_autogen",
    ),
    "issue": (
        "id", "title", "tldr", "severity", "status", "components",
        "impact", "location", "related_tasks", "fixed_in_task",
        "duplicate_of", "discovered", "resolved", "tldr_autogen",
    ),
    "lesson": (
        "id", "title", "tldr", "kind", "tier", "files",
        "reinforce_count", "last_reinforced",
        "task_titles_match", "task_kinds",
        "related_tasks", "related_issues", "tldr_autogen",
    ),
    "handover": (
        "id", "tldr", "next_action", "task_ids", "session_kind",
        "status", "status_changed", "status_reason",
        "created", "supersedes", "superseded_by", "flag_for_review",
        "tldr_autogen",
    ),
    "idea": (
        "id", "title", "tldr", "status", "tags",
        "created_by", "related_tasks", "related_issues", "related_lessons",
        "tldr_autogen",
    ),
}


def slim_entity(entity: dict[str, Any], kind: str) -> dict[str, Any]:
    """Return the slim view of an entity dict.

    Only fields in SLIM_FIELDS[kind] survive. For tasks, the `docs` dict is
    replaced with `docs_available` (a sorted list of section keys, no contents).
    """
    if kind not in SLIM_FIELDS:
        raise ValueError(f"Unknown entity kind: {kind!r}")
    out: dict[str, Any] = {}
    for key in SLIM_FIELDS[kind]:
        if key in entity and entity[key] not in (None, "", [], {}):
            out[key] = entity[key]
    if kind == "task":
        docs = entity.get("docs") or {}
        if docs:
            out["docs_available"] = sorted(docs.keys())
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_slim_view.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_slim_view.py
git commit -m "feat(taskmaster): slim_entity() extractor per entity kind"
```

---

### Task 9: Implement `resolve_sections()` helper

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py`
- Test: `plugins/taskmaster/tests/test_sections_parameter.py` (create — data-layer half)

- [ ] **Step 1: Write the failing test**

```python
# plugins/taskmaster/tests/test_sections_parameter.py
from plugins.taskmaster.taskmaster_v3 import resolve_sections


def test_resolve_task_inline_sections():
    entity = {"id": "T-001", "notes": "Some notes.", "review_instructions": "Run X."}
    out = resolve_sections(entity, kind="task", sections=["notes"], body="ignored")
    assert out == {"notes": "Some notes."}


def test_resolve_task_doc_section_returns_path_marker(tmp_path):
    entity = {"id": "T-001", "docs": {"plan": "docs/plan.md", "spec": "docs/spec.md"}}
    out = resolve_sections(entity, kind="task", sections=["plan"], body="", project_root=tmp_path)
    assert "plan" in out
    # Either path or "(unresolved: <path>)" if file missing
    assert "docs/plan.md" in out["plan"] or out["plan"] == "(unresolved: docs/plan.md)"


def test_resolve_handover_section_from_body():
    body = "## Decisions\n\nChose A over B.\n\n## Blockers\n\nNeed approval."
    out = resolve_sections({}, kind="handover", sections=["decisions"], body=body)
    assert "Chose A over B" in out["decisions"]
    assert "Blockers" not in out["decisions"]


def test_resolve_unknown_section_raises():
    import pytest
    with pytest.raises(ValueError, match="not a canonical section"):
        resolve_sections({}, kind="task", sections=["bogus"], body="")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_sections_parameter.py -v`
Expected: FAIL — `cannot import name 'resolve_sections'`.

- [ ] **Step 3: Implement `resolve_sections()`**

Add to `taskmaster_v3.py`:

```python
_SECTION_HEADING_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


def _split_body_by_heading(body: str) -> dict[str, str]:
    """Split a markdown body into sections keyed by lowercased heading text."""
    if not body:
        return {}
    matches = list(_SECTION_HEADING_RE.finditer(body))
    if not matches:
        return {}
    out: dict[str, str] = {}
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        key = m.group(1).strip().lower().replace(" ", "_")
        out[key] = body[start:end].strip()
    return out


def resolve_sections(
    entity: dict[str, Any],
    *,
    kind: str,
    sections: list[str],
    body: str,
    project_root: Path | None = None,
) -> dict[str, str]:
    """Return a dict mapping section name → content for requested sections.

    Validates section names against CANONICAL_SECTIONS[kind]. For tasks:
    - 'notes' and 'review_instructions' come from frontmatter.
    - 'spec'/'plan'/'design'/'analysis'/'roadmap' are resolved from `entity.docs.<name>`
      file paths (read and inlined; unresolved paths returned as a marker).
    For handovers/issues/lessons: split by '## Heading' in body.
    """
    canon = CANONICAL_SECTIONS.get(kind, ())
    for s in sections:
        if s not in canon:
            raise ValueError(f"{s!r} is not a canonical section for kind={kind!r}")

    out: dict[str, str] = {}

    if kind == "task":
        for s in sections:
            if s in TASK_INLINE_SECTIONS:
                v = entity.get(s)
                if v:
                    out[s] = v if isinstance(v, str) else str(v)
            elif s in TASK_DOC_SECTIONS:
                doc_path = (entity.get("docs") or {}).get(s)
                if not doc_path:
                    continue
                resolved = (project_root / doc_path) if project_root else Path(doc_path)
                if resolved.exists():
                    out[s] = resolved.read_text(encoding="utf-8")
                else:
                    out[s] = f"(unresolved: {doc_path})"
        return out

    # handover / issue / lesson: split body by ## headings
    body_sections = _split_body_by_heading(body)
    for s in sections:
        if s in body_sections:
            out[s] = body_sections[s]
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_sections_parameter.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_sections_parameter.py
git commit -m "feat(taskmaster): resolve_sections() for surgical section retrieval"
```

---

### Task 10: Implement `expand_link_ids()` helper

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py`
- Test: `plugins/taskmaster/tests/test_expand_links.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# plugins/taskmaster/tests/test_expand_links.py
from plugins.taskmaster.taskmaster_v3 import expand_link_ids


def test_expand_known_ids():
    tldr_index = {
        "T-001": "Refactor auth",
        "ISS-007": "Auth crashes on Friday",
        "L-003": "Use atomic_write everywhere",
    }
    ids = ["T-001", "ISS-007", "L-003"]
    out = expand_link_ids(ids, tldr_index)
    assert out == [
        {"id": "T-001", "tldr": "Refactor auth"},
        {"id": "ISS-007", "tldr": "Auth crashes on Friday"},
        {"id": "L-003", "tldr": "Use atomic_write everywhere"},
    ]


def test_expand_unknown_id_returns_none_tldr():
    out = expand_link_ids(["T-999"], {})
    assert out == [{"id": "T-999", "tldr": None}]


def test_expand_handles_grouped_dict():
    grouped = {"depends_on": ["T-002"], "fixes": ["ISS-007"]}
    tldr_index = {"T-002": "Auth helper", "ISS-007": "Auth crashes"}
    out = expand_link_ids(grouped, tldr_index)
    assert out["depends_on"] == [{"id": "T-002", "tldr": "Auth helper"}]
    assert out["fixes"] == [{"id": "ISS-007", "tldr": "Auth crashes"}]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_expand_links.py -v`
Expected: FAIL — `cannot import name 'expand_link_ids'`.

- [ ] **Step 3: Implement `expand_link_ids()`**

```python
def expand_link_ids(
    ids: list[str] | dict[str, list[str]],
    tldr_index: dict[str, str],
) -> list[dict[str, str | None]] | dict[str, list[dict[str, str | None]]]:
    """Expand bare ID arrays into {id, tldr} pills.

    Accepts either a flat list (returns list) or a grouped dict (returns dict).
    Unknown IDs get tldr=None.
    """
    if isinstance(ids, dict):
        return {key: expand_link_ids(vals, tldr_index) for key, vals in ids.items()}  # type: ignore[return-value]
    return [{"id": i, "tldr": tldr_index.get(i)} for i in ids]
```

Also add a helper that builds the tldr_index from a loaded backlog:

```python
def build_tldr_index(data: dict[str, Any]) -> dict[str, str]:
    """Build {entity_id → tldr} index across tasks/issues/lessons/handovers/ideas.

    Reads from the in-memory backlog dict (post-load_v3). Issues/lessons/handovers/ideas
    live in their own dirs but we only need the index for IDs the caller mentions in
    linkage arrays — so this loads ALL of them. For very large projects, consider
    on-demand caching in a future iteration.
    """
    idx: dict[str, str] = {}
    for epic in data.get("epics", []):
        for task in epic.get("tasks", []):
            tid = task.get("id")
            if tid and task.get("tldr"):
                idx[tid] = task["tldr"]
    # External (file-based) entities — caller passes them in for now.
    return idx
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_expand_links.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_expand_links.py
git commit -m "feat(taskmaster): expand_link_ids() + build_tldr_index() helpers"
```

---

## Phase 5 — Slim default on `_get` tools

### Task 11: `backlog_get_task` slim default + verbose/sections/expand_links

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py:900` (`backlog_get_task`)
- Test: `plugins/taskmaster/tests/test_slim_get_task.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# plugins/taskmaster/tests/test_slim_get_task.py
import yaml
from plugins.taskmaster.backlog_server import backlog_add_task, backlog_get_task


def _parse_yaml_block(text):
    # Tools return markdown with a YAML frontmatter block. Extract it.
    if text.startswith("---"):
        _, fm, _ = text.split("---", 2)
        return yaml.safe_load(fm)
    return yaml.safe_load(text)


def test_slim_default_excludes_body(tmp_taskmaster):
    backlog_add_task(epic="e", task_id="T-1", title="X", tldr="Short tldr.",
                     notes="Very long notes that should not appear in slim mode.")
    out = backlog_get_task("T-1")  # slim by default
    assert "Short tldr." in out
    assert "Very long notes" not in out


def test_verbose_includes_body(tmp_taskmaster):
    backlog_add_task(epic="e", task_id="T-2", title="X", tldr="Tldr.",
                     notes="Verbose-only content.")
    out = backlog_get_task("T-2", verbose=True)
    assert "Verbose-only content" in out


def test_slim_has_docs_available_not_docs(tmp_taskmaster):
    backlog_add_task(epic="e", task_id="T-3", title="X", tldr="T.",
                     docs={"plan": "p.md", "spec": "s.md"})
    out = backlog_get_task("T-3")
    assert "docs_available" in out
    assert "plan" in out and "spec" in out


def test_expand_links_swaps_ids_for_pills(tmp_taskmaster):
    backlog_add_task(epic="e", task_id="T-A", title="A", tldr="A-tldr.")
    backlog_add_task(epic="e", task_id="T-B", title="B", tldr="B-tldr.",
                     depends_on=["T-A"])
    out = backlog_get_task("T-B", expand_links=True)
    assert "A-tldr" in out  # pill includes target's tldr


def test_sections_returns_only_requested(tmp_taskmaster):
    backlog_add_task(epic="e", task_id="T-S", title="X", tldr="T.",
                     notes="My notes here.", review_instructions="Run X.")
    out = backlog_get_task("T-S", sections=["notes"])
    assert "My notes here" in out
    assert "Run X" not in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_slim_get_task.py -v`
Expected: FAIL — unknown kwargs `verbose`/`sections`/`expand_links`.

- [ ] **Step 3: Update `backlog_get_task` signature and body**

Locate the function at `backlog_server.py:900`. Refactor:

```python
@mcp.tool()
def backlog_get_task(
    task_id: str,
    verbose: bool = False,
    sections: list[str] | None = None,
    expand_links: bool = False,
) -> str:
    """Return a task. Slim by default (frontmatter + tldr + extras + bare-ID linkages).

    Args:
        task_id: Task ID.
        verbose: If True, include the full body and all heavy fields.
        sections: Subset of canonical sections to include (notes, review_instructions,
                  spec, plan, design, analysis, roadmap). Mutually exclusive with verbose.
        expand_links: If True, replace bare linkage IDs with {id, tldr} pills.
    """
    bp = _resolve_paths()[0]
    data = tm.load_v3(bp)
    task = _find_task(data, task_id)   # existing helper; rename if needed
    if task is None:
        return f"Task not found: {task_id}"

    if verbose:
        # Today's behavior: full frontmatter + body
        view = dict(task)
    else:
        view = tm.slim_entity(task, kind="task")
        if expand_links:
            tldr_index = tm.build_tldr_index(data)
            for fld in ("depends_on", "related_issues", "related_lessons"):
                if fld in view:
                    view[fld] = tm.expand_link_ids(view[fld], tldr_index)

    body_out = ""
    if sections:
        section_map = tm.resolve_sections(
            task, kind="task", sections=sections,
            body=task.get(tm.BODY_KEY, ""),
            project_root=bp.parent.parent,
        )
        body_out = "\n\n".join(f"## {k}\n\n{v}" for k, v in section_map.items())
    elif verbose:
        body_out = task.get(tm.BODY_KEY, "")

    return tm.render_frontmatter(view, body_out)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_slim_get_task.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_slim_get_task.py
git commit -m "feat(taskmaster): backlog_get_task slim default + verbose/sections/expand_links"
```

---

### Task 12: `backlog_handover_get` slim default

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py:1751` (`backlog_handover_get`)
- Test: `plugins/taskmaster/tests/test_slim_handover_get.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# plugins/taskmaster/tests/test_slim_handover_get.py
from plugins.taskmaster.backlog_server import (
    backlog_handover_create, backlog_handover_get,
)


def test_slim_handover_excludes_body(tmp_taskmaster):
    backlog_handover_create(
        task_ids=["T-1"],
        tldr="Auth refactor handoff.",
        next_action="Backfill staging.",
        body="## Decisions\n\nLots of detail here.\n",
    )
    out = backlog_handover_get("HND-001")  # slim default
    assert "Auth refactor handoff" in out
    assert "Lots of detail here" not in out


def test_verbose_handover_includes_body(tmp_taskmaster):
    backlog_handover_create(
        task_ids=["T-1"], tldr="T.", next_action="N.",
        body="## Decisions\n\nDetailed.",
    )
    out = backlog_handover_get("HND-001", verbose=True)
    assert "Detailed" in out


def test_handover_sections_returns_only_requested(tmp_taskmaster):
    backlog_handover_create(
        task_ids=["T-1"], tldr="T.", next_action="N.",
        body="## Decisions\n\nChose A.\n\n## Blockers\n\nNeed approval.\n",
    )
    out = backlog_handover_get("HND-001", sections=["blockers"])
    assert "Need approval" in out
    assert "Chose A" not in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_slim_handover_get.py -v`
Expected: FAIL — unknown kwargs.

- [ ] **Step 3: Update `backlog_handover_get`**

```python
@mcp.tool()
def backlog_handover_get(
    handover_id: str,
    verbose: bool = False,
    sections: list[str] | None = None,
    expand_links: bool = False,
) -> str:
    bp = _resolve_paths()[0]
    fm, body = tm.read_handover(bp, handover_id)
    if not fm:
        return f"Handover not found: {handover_id}"

    if verbose:
        view = dict(fm)
        body_out = body
    else:
        view = tm.slim_entity(fm, kind="handover")
        body_out = ""

    if sections:
        section_map = tm.resolve_sections(fm, kind="handover", sections=sections, body=body)
        body_out = "\n\n".join(f"## {k}\n\n{v}" for k, v in section_map.items())

    if expand_links and not verbose:
        data = tm.load_v3(bp)
        tldr_index = tm.build_tldr_index(data)
        if "task_ids" in view:
            view["task_ids"] = tm.expand_link_ids(view["task_ids"], tldr_index)

    return tm.render_frontmatter(view, body_out)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_slim_handover_get.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_slim_handover_get.py
git commit -m "feat(taskmaster): backlog_handover_get slim default + verbose/sections/expand_links"
```

---

### Task 13: `backlog_issue_get` slim default

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py:1966` (`backlog_issue_get`)
- Test: `plugins/taskmaster/tests/test_slim_issue_get.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# plugins/taskmaster/tests/test_slim_issue_get.py
from plugins.taskmaster.backlog_server import backlog_issue_create, backlog_issue_get


def test_slim_issue_excludes_body(tmp_taskmaster):
    backlog_issue_create(title="Bug", severity="P1", tldr="Auth bug.",
                         body="## Repro\n\nClick X then Y.")
    out = backlog_issue_get("ISS-001")
    assert "Auth bug" in out
    assert "Click X then Y" not in out


def test_verbose_issue_includes_body(tmp_taskmaster):
    backlog_issue_create(title="Bug", severity="P1", tldr="T.",
                         body="## Repro\n\nSteps follow.")
    out = backlog_issue_get("ISS-001", verbose=True)
    assert "Steps follow" in out


def test_issue_sections(tmp_taskmaster):
    backlog_issue_create(title="Bug", severity="P1", tldr="T.",
                         body="## Repro\n\nClick X.\n\n## Investigation\n\nFound Y.")
    out = backlog_issue_get("ISS-001", sections=["investigation"])
    assert "Found Y" in out
    assert "Click X" not in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_slim_issue_get.py -v`
Expected: FAIL — unknown kwargs.

- [ ] **Step 3: Update `backlog_issue_get`**

Mirror the pattern from Task 12, swapping `read_handover` for `tm.read_issue` and `kind="handover"` for `kind="issue"`. Expand links operate on `related_tasks` and `fixed_in_task` (single-ID — wrap in list before expand if non-empty).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_slim_issue_get.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_slim_issue_get.py
git commit -m "feat(taskmaster): backlog_issue_get slim default + verbose/sections/expand_links"
```

---

### Task 14: `backlog_lesson_get` slim default

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py:2351` (`backlog_lesson_get`)
- Test: `plugins/taskmaster/tests/test_slim_lesson_get.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# plugins/taskmaster/tests/test_slim_lesson_get.py
from plugins.taskmaster.backlog_server import backlog_lesson_create, backlog_lesson_get


def test_slim_lesson_excludes_body(tmp_taskmaster):
    backlog_lesson_create(title="Atomic", kind="pattern", tldr="Use atomic_write.",
                          why="Body content.", what_to_do="Do X.")
    out = backlog_lesson_get("L-001")
    assert "Use atomic_write" in out
    assert "Body content" not in out


def test_verbose_lesson_includes_body(tmp_taskmaster):
    backlog_lesson_create(title="Atomic", kind="pattern", tldr="T.",
                          why="Why text.", what_to_do="Do X.")
    out = backlog_lesson_get("L-001", verbose=True)
    assert "Why text" in out


def test_lesson_sections(tmp_taskmaster):
    backlog_lesson_create(title="Atomic", kind="pattern", tldr="T.",
                          why="W body.", what_to_do="WTD body.", examples="EX body.")
    out = backlog_lesson_get("L-001", sections=["what_to_do"])
    assert "WTD body" in out
    assert "W body" not in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_slim_lesson_get.py -v`
Expected: FAIL.

- [ ] **Step 3: Update `backlog_lesson_get`**

Mirror Task 12, `kind="lesson"`, `tm.read_lesson`. Expand links: `related_tasks`, `related_issues`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_slim_lesson_get.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_slim_lesson_get.py
git commit -m "feat(taskmaster): backlog_lesson_get slim default + verbose/sections/expand_links"
```

---

### Task 15: `backlog_idea_get` slim default

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py` (search `def backlog_idea_get`)
- Test: extend `test_slim_lesson_get.py` or new `test_slim_idea_get.py`

- [ ] **Step 1: Write the failing test**

```python
# plugins/taskmaster/tests/test_slim_idea_get.py
from plugins.taskmaster.backlog_server import backlog_idea_create, backlog_idea_get


def test_slim_idea_excludes_body(tmp_taskmaster):
    backlog_idea_create(title="Dark mode", tldr="Add dark toggle.",
                        body="Long rationale here.")
    # Idea IDs are like IDEA-001 — grab the actual ID from creation result or list
    out = backlog_idea_get("IDEA-001")
    assert "Add dark toggle" in out
    assert "Long rationale" not in out


def test_verbose_idea_includes_body(tmp_taskmaster):
    backlog_idea_create(title="Dark", tldr="T.", body="Long rationale.")
    out = backlog_idea_get("IDEA-001", verbose=True)
    assert "Long rationale" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_slim_idea_get.py -v`
Expected: FAIL.

- [ ] **Step 3: Update `backlog_idea_get`**

Mirror Task 12, `kind="idea"`. Ideas have no canonical body sections — accept `sections=` but raise if non-empty (ideas don't carry structured headings).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_slim_idea_get.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_slim_idea_get.py
git commit -m "feat(taskmaster): backlog_idea_get slim default + verbose"
```

---

## Phase 6 — `backlog_status` slim default

### Task 16: `backlog_status` slim/verbose split

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py:713` (`backlog_status`)
- Test: `plugins/taskmaster/tests/test_backlog_status_slim.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# plugins/taskmaster/tests/test_backlog_status_slim.py
from plugins.taskmaster.backlog_server import (
    backlog_add_task, backlog_complete_task, backlog_archive_task, backlog_status,
)


def test_slim_status_omits_archived_section(tmp_taskmaster):
    backlog_add_task(epic="e", task_id="T-1", title="X", tldr="T.")
    backlog_complete_task("T-1")
    backlog_archive_task("T-1", reason="done")
    out = backlog_status()  # slim default
    assert "T-1" not in out  # archived hidden in slim
    # slim shows: counts + in-progress + in-review + blocked + next-up + phase
    assert "in-progress" in out.lower() or "in_progress" in out.lower()


def test_verbose_status_includes_archived(tmp_taskmaster):
    backlog_add_task(epic="e", task_id="T-1", title="X", tldr="T.")
    backlog_complete_task("T-1")
    backlog_archive_task("T-1", reason="done")
    out = backlog_status(verbose=True)
    assert "archived" in out.lower()


def test_slim_status_under_400_tokens(tmp_taskmaster):
    # Add a realistic-ish set (5 epics × 5 tasks each), all in todo
    for ei in range(5):
        for ti in range(5):
            backlog_add_task(epic=f"e{ei}", task_id=f"T-{ei}-{ti}",
                             title=f"task {ei}.{ti}", tldr=f"tldr {ei}.{ti}")
    out = backlog_status()
    # ~4 chars per token; allow some slack
    assert len(out) < 1800, f"slim status too large: {len(out)} chars"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_backlog_status_slim.py -v`
Expected: FAIL — `verbose` kwarg unknown OR slim mode doesn't trim archived.

- [ ] **Step 3: Update `backlog_status`**

```python
@mcp.tool()
def backlog_status(verbose: bool = False) -> str:
    """Project dashboard. Slim by default (~400 tokens).

    Slim shows: counts, in-progress titles, in-review, blocked, top 5 next-up,
    active phase, stale count. Verbose adds full epic list, archived items,
    completed history.
    """
    bp = _resolve_paths()[0]
    data = tm.load_v3(bp)
    if verbose:
        return _render_full_dashboard(data)        # existing implementation extracted
    return _render_slim_dashboard(data)            # new function
```

Extract today's body into `_render_full_dashboard(data)`. Create `_render_slim_dashboard(data)` that omits the archived/completed-history sections and caps next-up at 5 and recent-completed at 3.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_backlog_status_slim.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_backlog_status_slim.py
git commit -m "feat(taskmaster): backlog_status slim default + verbose for archived/completed"
```

---

## Phase 7 — `_list` tools slim

### Task 17: `backlog_list_tasks` slim entries

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py:848` (`backlog_list_tasks`)
- Test: `plugins/taskmaster/tests/test_slim_list_tools.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# plugins/taskmaster/tests/test_slim_list_tools.py
from plugins.taskmaster.backlog_server import backlog_add_task, backlog_list_tasks


def test_list_tasks_returns_slim_entries(tmp_taskmaster):
    backlog_add_task(epic="e", task_id="T-1", title="X", tldr="Tldr 1.",
                     notes="Heavy notes content.")
    backlog_add_task(epic="e", task_id="T-2", title="Y", tldr="Tldr 2.",
                     review_instructions="Heavy review instructions.")
    out = backlog_list_tasks()
    # tldrs visible
    assert "Tldr 1" in out and "Tldr 2" in out
    # heavy fields excluded
    assert "Heavy notes content" not in out
    assert "Heavy review instructions" not in out


def test_list_tasks_verbose_includes_heavy(tmp_taskmaster):
    backlog_add_task(epic="e", task_id="T-1", title="X", tldr="T.",
                     notes="Heavy notes content.")
    out = backlog_list_tasks(verbose=True)
    assert "Heavy notes content" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_slim_list_tools.py -v`
Expected: FAIL — heavy fields leak into list output OR `verbose` unknown.

- [ ] **Step 3: Update `backlog_list_tasks`**

Add `verbose: bool = False`. In slim mode, render each task using `tm.slim_entity(task, kind="task")` before formatting. In verbose mode, keep today's behavior.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_slim_list_tools.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_slim_list_tools.py
git commit -m "feat(taskmaster): backlog_list_tasks slim entries + verbose flag"
```

---

### Task 18: `backlog_handover_list` slim entries

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py` (search `def backlog_handover_list`)
- Test: extend `test_slim_list_tools.py`

- [ ] **Step 1: Write the failing test**

Append:

```python
from plugins.taskmaster.backlog_server import (
    backlog_handover_create, backlog_handover_list,
)


def test_handover_list_returns_slim_entries(tmp_taskmaster):
    backlog_handover_create(task_ids=["T-1"], tldr="Tldr handover.",
                            next_action="Next.", body="## Decisions\n\nLong body.")
    out = backlog_handover_list()
    assert "Tldr handover" in out
    assert "Long body" not in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_slim_list_tools.py::test_handover_list_returns_slim_entries -v`
Expected: FAIL — list leaks body content.

- [ ] **Step 3: Update `backlog_handover_list`**

Render via `tm.slim_entity(fm, kind="handover")` per entry. Already mostly slim today (only frontmatter) — make sure body content never inlines. Add `verbose: bool = False` for completeness.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_slim_list_tools.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_slim_list_tools.py
git commit -m "feat(taskmaster): backlog_handover_list slim entries + verbose flag"
```

---

### Task 19: `backlog_issue_list` and `backlog_lesson_list` slim entries

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py` (search `def backlog_issue_list`, `def backlog_lesson_list`)
- Test: extend `test_slim_list_tools.py`

- [ ] **Step 1: Write the failing tests**

Append:

```python
from plugins.taskmaster.backlog_server import (
    backlog_issue_create, backlog_issue_list,
    backlog_lesson_create, backlog_lesson_list,
)


def test_issue_list_slim(tmp_taskmaster):
    backlog_issue_create(title="Bug", severity="P1", tldr="Issue tldr.",
                         body="## Repro\n\nLong repro steps.")
    out = backlog_issue_list()
    assert "Issue tldr" in out
    assert "Long repro steps" not in out


def test_lesson_list_slim(tmp_taskmaster):
    backlog_lesson_create(title="Atomic", kind="pattern", tldr="Lesson tldr.",
                          why="Long why body.", what_to_do="Long WTD body.")
    out = backlog_lesson_list()
    assert "Lesson tldr" in out
    assert "Long why body" not in out
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest plugins/taskmaster/tests/test_slim_list_tools.py::test_issue_list_slim plugins/taskmaster/tests/test_slim_list_tools.py::test_lesson_list_slim -v`
Expected: FAIL.

- [ ] **Step 3: Update both list functions**

Apply `tm.slim_entity` to each entry. Add `verbose: bool = False`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest plugins/taskmaster/tests/test_slim_list_tools.py -v`
Expected: 5 passed total.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_slim_list_tools.py
git commit -m "feat(taskmaster): backlog_issue_list + backlog_lesson_list slim entries"
```

---

## Phase 8 — Validation warnings

### Task 20: `backlog_validate` flags missing tldrs (warning only)

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py` (search `def backlog_validate`)
- Test: `plugins/taskmaster/tests/test_validate_tldr_warning.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# plugins/taskmaster/tests/test_validate_tldr_warning.py
from pathlib import Path
from plugins.taskmaster import taskmaster_v3 as tm
from plugins.taskmaster.backlog_server import backlog_validate


def test_validate_warns_on_missing_tldr(tmp_taskmaster):
    # Write a task file directly without tldr (simulating legacy data)
    bp = Path(tmp_taskmaster) / ".taskmaster" / "backlog.yaml"
    task_path = bp.parent / "tasks" / "T-legacy.md"
    task_path.parent.mkdir(parents=True, exist_ok=True)
    tm.write_task_file(task_path, {"id": "T-legacy", "title": "Legacy task"}, "")

    # Also need T-legacy in backlog.yaml — caller can do this via direct yaml edit
    # ... fixture setup omitted for brevity; conftest provides it ...

    out = backlog_validate()
    assert "tldr" in out.lower()
    assert "T-legacy" in out
    # Warning, not error — exit code or marker should indicate warning
    assert "warning" in out.lower() or "warn" in out.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_validate_tldr_warning.py -v`
Expected: FAIL — validate doesn't check tldr.

- [ ] **Step 3: Update `backlog_validate`**

Iterate over tasks/issues/lessons; for each entity missing `tldr`, append a warning line:

```python
# Inside backlog_validate, after existing checks:
warnings: list[str] = []
data = tm.load_v3(bp)
for epic in data.get("epics", []):
    for task in epic.get("tasks", []):
        if not task.get("tldr"):
            warnings.append(f"  warning: task {task['id']} missing tldr — run backfill_tldr.py")
# similar for issues, lessons (load each dir)
# ...
if warnings:
    output += "\n## Warnings\n" + "\n".join(warnings)
```

Keep these as warnings (not errors that fail validation) during the grace period.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_validate_tldr_warning.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_validate_tldr_warning.py
git commit -m "feat(taskmaster): validate warns on missing tldr (grace period)"
```

---

## Phase 9 — Integration smoke + changelog

### Task 21: End-to-end foundation smoke test

**Files:**
- Create: `plugins/taskmaster/tests/test_foundation_smoke.py`

- [ ] **Step 1: Write the smoke test**

```python
# plugins/taskmaster/tests/test_foundation_smoke.py
"""End-to-end check: every _get/_list returns slim by default; verbose preserves
today's behavior; sections+expand_links work across entity types.

This is the canary that ensures Plan A delivers the promise without regressing
existing flows.
"""
from plugins.taskmaster.backlog_server import (
    backlog_add_task, backlog_get_task, backlog_list_tasks, backlog_status,
    backlog_issue_create, backlog_issue_get, backlog_issue_list,
    backlog_lesson_create, backlog_lesson_get, backlog_lesson_list,
    backlog_handover_create, backlog_handover_get, backlog_handover_list,
)


def test_slim_defaults_across_all_entities(tmp_taskmaster):
    # Create one of each
    backlog_add_task(epic="e", task_id="T-1", title="Auth", tldr="Refactor auth.",
                     notes="Heavy notes content here.")
    backlog_issue_create(title="Bug", severity="P1", tldr="Auth bug.",
                         body="## Repro\n\nLong steps.")
    backlog_lesson_create(title="Atomic", kind="pattern", tldr="Use atomic.",
                          why="Long why.", what_to_do="Long WTD.")
    backlog_handover_create(task_ids=["T-1"], tldr="Auth handoff.",
                            next_action="Next.", body="## Decisions\n\nDetail.")

    # Slim _get returns tldrs, hides bodies
    for fn, eid, heavy in [
        (backlog_get_task,     "T-1",     "Heavy notes content"),
        (backlog_issue_get,    "ISS-001", "Long steps"),
        (backlog_lesson_get,   "L-001",   "Long why"),
        (backlog_handover_get, "HND-001", "Detail"),
    ]:
        slim = fn(eid)
        assert "tldr" in slim.lower() or "Refactor auth" in slim or "Auth bug" in slim \
               or "Use atomic" in slim or "Auth handoff" in slim
        assert heavy not in slim, f"{fn.__name__} leaked heavy content in slim mode"

    # Verbose _get includes bodies
    for fn, eid, heavy in [
        (backlog_get_task,     "T-1",     "Heavy notes content"),
        (backlog_issue_get,    "ISS-001", "Long steps"),
        (backlog_lesson_get,   "L-001",   "Long why"),
        (backlog_handover_get, "HND-001", "Detail"),
    ]:
        verbose = fn(eid, verbose=True)
        assert heavy in verbose, f"{fn.__name__} verbose missing body content"

    # List tools return slim
    for fn, heavy in [
        (backlog_list_tasks,    "Heavy notes content"),
        (backlog_issue_list,    "Long steps"),
        (backlog_lesson_list,   "Long why"),
        (backlog_handover_list, "Detail"),
    ]:
        out = fn()
        assert heavy not in out, f"{fn.__name__} leaked heavy content in list mode"

    # Dashboard slim
    status = backlog_status()
    assert len(status) < 4000, "slim status too large"


def test_token_budget_targets_met(tmp_taskmaster):
    """Hard budget check: confirm Plan A delivers the promised token reductions."""
    backlog_add_task(epic="e", task_id="T-1", title="Auth refactor",
                     tldr="Refactor middleware.",
                     notes="A" * 2000, review_instructions="B" * 2000)
    slim = backlog_get_task("T-1")
    # Slim should be well under 600 chars (~150 tokens)
    assert len(slim) < 600, f"slim get_task too large: {len(slim)} chars"
    # Verbose should include the 4000 chars of heavy fields
    verbose = backlog_get_task("T-1", verbose=True)
    assert len(verbose) > 3000
```

- [ ] **Step 2: Run the smoke test**

Run: `pytest plugins/taskmaster/tests/test_foundation_smoke.py -v`
Expected: 2 passed.

- [ ] **Step 3: Run the full Plan A test suite**

Run: `pytest plugins/taskmaster/tests/test_tldr_extraction.py plugins/taskmaster/tests/test_canonical_sections.py plugins/taskmaster/tests/test_tldr_required_on_create.py plugins/taskmaster/tests/test_tldr_backfill.py plugins/taskmaster/tests/test_slim_view.py plugins/taskmaster/tests/test_sections_parameter.py plugins/taskmaster/tests/test_expand_links.py plugins/taskmaster/tests/test_slim_get_task.py plugins/taskmaster/tests/test_slim_handover_get.py plugins/taskmaster/tests/test_slim_issue_get.py plugins/taskmaster/tests/test_slim_lesson_get.py plugins/taskmaster/tests/test_slim_idea_get.py plugins/taskmaster/tests/test_backlog_status_slim.py plugins/taskmaster/tests/test_slim_list_tools.py plugins/taskmaster/tests/test_validate_tldr_warning.py plugins/taskmaster/tests/test_foundation_smoke.py -v`
Expected: All passing.

- [ ] **Step 4: Run the full existing test suite for regressions**

Run: `pytest plugins/taskmaster/tests/ -v`
Expected: All previously-passing tests still pass. Pre-existing handover-status tests in particular must still pass.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/tests/test_foundation_smoke.py
git commit -m "test(taskmaster): foundation smoke test for slim defaults across all entities"
```

---

### Task 22: CHANGELOG entry

**Files:**
- Modify: `plugins/taskmaster/CHANGELOG.md`

- [ ] **Step 1: Add changelog entry**

Append to `plugins/taskmaster/CHANGELOG.md` under an unreleased v3.X section:

```markdown
## v3.X — Progressive Disclosure Foundation (2026-05-XX)

### Added
- Required `tldr` field on tasks, issues, lessons, ideas (handovers already had it). Auto-generated from body's first sentence when missing on create; flagged with `tldr_autogen: true`.
- Slim-by-default mode on every `_get` MCP tool: `backlog_get_task`, `backlog_handover_get`, `backlog_issue_get`, `backlog_lesson_get`, `backlog_idea_get`. Returns frontmatter + tldr + extras + bare-ID linkages (~150 tokens). Use `verbose=true` for full body.
- `sections=[...]` parameter on `_get` tools for surgical section retrieval. Canonical section names per entity defined in `taskmaster_v3.CANONICAL_SECTIONS`.
- `expand_links=true` parameter on `_get` tools — swaps bare linkage IDs for `{id, tldr}` pills.
- Slim-by-default on every `_list` MCP tool: `backlog_list_tasks`, `backlog_handover_list`, `backlog_issue_list`, `backlog_lesson_list`. Use `verbose=true` to restore today's output.
- `backlog_status` slim by default (~400 tokens); `verbose=true` adds full epic list + archived + completed history.
- `scripts/backfill_tldr.py` — one-shot CLI to backfill tldrs into legacy entities.
- `backlog_validate` now warns (does not fail) on entities missing `tldr`.

### Migration
1. Run `python -m plugins.taskmaster.scripts.backfill_tldr --root <project>` to backfill tldrs on existing tasks/issues/lessons/ideas.
2. Review auto-generated tldrs (look for `tldr_autogen: true` in frontmatter) and refine if needed.
3. Existing MCP callers that depend on today's verbose output should add `verbose=True` to their calls. Default behavior changes are documented in the spec.

Spec: `docs/superpowers/specs/2026-05-15-taskmaster-progressive-disclosure-design.md` §1–§2.
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/CHANGELOG.md
git commit -m "docs(taskmaster): changelog entry for v3.X progressive disclosure foundation"
```

---

## Self-Review

After implementing all 22 tasks, run this final pass:

- [ ] All tests in `plugins/taskmaster/tests/` pass: `pytest plugins/taskmaster/tests/ -v`
- [ ] `backlog_validate` on a project shows zero warnings after running backfill (other than pre-existing schema warnings)
- [ ] Manual sanity check: invoke `backlog_get_task("<some-id>")` in a real project — confirm output is ≤ 600 chars (~150 tokens)
- [ ] Manual sanity check: invoke `backlog_get_task("<some-id>", verbose=True)` — confirm output matches the pre-change behavior
- [ ] `git log --oneline` shows ~22 atomic commits, one per task
- [ ] No `TBD`, `TODO`, or `pass # implement later` markers anywhere in plugin code

---

## Out of scope (deferred to Plans B/C/D/E)

- **Parallel handover model + status formalization** → Plan B
- **Typed `links` schema + symmetric sync + auto-detect** → Plan C
- **`start-session` / `pick-task` glance redesign** → Plan D
- **Skill body slimming + description audit** → Plan E
- **Section-aware editing (`backlog_update_task_section`)** → separate spec
- **Auto-derived linkages (commit → issue, files → lesson)** → §6E in spec, deferred to future
- **`backlog_validate` failing on missing tldr** → after one release of grace-period warnings
