# Taskmaster Ideas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a lightweight per-project "Ideas" surface to Taskmaster — file-based, AI-loggable via three capture paths (explicit `/add-idea`, fuzzy `<idea-candidate>` tag, sharp auto-log), with three MCP tools (create/list/update) and a dedicated viewer screen. Folds in the lesson-candidate emit-guidance fix (one shared file edit).

**Architecture:** One-file-per-idea (`IDEA-NNN.md`) with YAML frontmatter + freeform body, plus an append-only `IDEAS.md` index, both under `<backlog parent>/ideas/`. Data layer lives in `taskmaster_v3.py` next to issues/lessons. MCP wrappers live in `backlog_server.py`. Capture surfaces are prompt-driven (no python detection): heuristics live in `start-session/SKILL.md` so they're loaded for every conversation. Viewer screen mirrors `screens/issues.js`.

**Tech Stack:** Python 3.10+ (data layer + MCP server via FastMCP), pytest (tests), vanilla JS for the viewer (existing pattern), YAML + Markdown for on-disk format.

**Spec:** `docs/superpowers/specs/2026-05-09-taskmaster-ideas-design.md`

---

## File Structure

**New files:**
```
plugins/taskmaster/skills/add-idea/SKILL.md
plugins/taskmaster/skills/add-idea/templates/idea-body.md
plugins/taskmaster/viewer/js/screens/ideas.js
plugins/taskmaster/tests/test_v3_ideas.py
plugins/taskmaster/tests/test_server_ideas.py
plugins/taskmaster/tests/test_add_idea_skill_lint.py
plugins/taskmaster/viewer/tests/unit/ideas-screen.test.js
```

**Modified files:**
```
plugins/taskmaster/taskmaster_v3.py             # +Ideas data layer (constants, helpers, write/read/update/list, IDEAS.md regen)
plugins/taskmaster/backlog_server.py            # +backlog_idea_create / _list / _update + /api/ideas HTTP endpoint
plugins/taskmaster/skills/start-session/SKILL.md# +mid-session behavior section: lesson-emit + idea-emit heuristics
plugins/taskmaster/skills/end-session/SKILL.md  # +scan <idea-candidate>, commit-direct, report counts
plugins/taskmaster/skills/taskmaster/SKILL.md   # +routing row for idea intents
plugins/taskmaster/skills/lesson/references/marker-format.md   # +<idea-candidate> schema
plugins/taskmaster/viewer/js/screens/index.js   # +register ideas screen
plugins/taskmaster/viewer/backlog-viewer.html   # +nav entry
plugins/taskmaster/tests/test_mcp_v3_exposure.py# +backlog_idea_* expected names
```

**Auto-created at runtime:**
```
.taskmaster/ideas/                              # lazy on first idea
.taskmaster/ideas/IDEAS.md                      # lazy on first idea
.taskmaster/ideas/IDEA-NNN.md                   # one per idea
```

---

## Task 1: Idea constants, path helpers, ID allocator

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py` (add new section after lessons section, before any v3 layout helpers below it)
- Create: `plugins/taskmaster/tests/test_v3_ideas.py`

- [ ] **Step 1: Write the failing test**

Create `plugins/taskmaster/tests/test_v3_ideas.py`:

```python
"""Unit tests for the Ideas data layer in taskmaster_v3."""
from pathlib import Path


def test_idea_path_returns_expected_location(tmp_path):
    from taskmaster_v3 import idea_path
    bp = tmp_path / ".taskmaster" / "backlog.yaml"
    p = idea_path(bp, "IDEA-007")
    assert p == tmp_path / ".taskmaster" / "ideas" / "IDEA-007.md"


def test_idea_dir_returns_expected_location(tmp_path):
    from taskmaster_v3 import idea_dir
    bp = tmp_path / ".taskmaster" / "backlog.yaml"
    assert idea_dir(bp) == tmp_path / ".taskmaster" / "ideas"


def test_ideas_index_path_returns_expected_location(tmp_path):
    from taskmaster_v3 import ideas_index_path
    bp = tmp_path / ".taskmaster" / "backlog.yaml"
    assert ideas_index_path(bp) == tmp_path / ".taskmaster" / "ideas" / "IDEAS.md"


def test_list_idea_ids_empty_dir(tmp_path):
    from taskmaster_v3 import list_idea_ids
    bp = tmp_path / ".taskmaster" / "backlog.yaml"
    assert list_idea_ids(bp) == []


def test_list_idea_ids_sorted_numerically(tmp_path):
    from taskmaster_v3 import list_idea_ids, idea_dir
    bp = tmp_path / ".taskmaster" / "backlog.yaml"
    d = idea_dir(bp)
    d.mkdir(parents=True)
    (d / "IDEA-002.md").write_text("---\nid: IDEA-002\n---\n")
    (d / "IDEA-010.md").write_text("---\nid: IDEA-010\n---\n")
    (d / "IDEA-001.md").write_text("---\nid: IDEA-001\n---\n")
    (d / "IDEAS.md").write_text("# Ideas\n")  # index file must be ignored
    assert list_idea_ids(bp) == ["IDEA-001", "IDEA-002", "IDEA-010"]


def test_next_idea_id_first(tmp_path):
    from taskmaster_v3 import next_idea_id
    bp = tmp_path / ".taskmaster" / "backlog.yaml"
    assert next_idea_id(bp) == "IDEA-001"


def test_next_idea_id_after_existing(tmp_path):
    from taskmaster_v3 import next_idea_id, idea_dir
    bp = tmp_path / ".taskmaster" / "backlog.yaml"
    d = idea_dir(bp)
    d.mkdir(parents=True)
    (d / "IDEA-007.md").write_text("---\nid: IDEA-007\n---\n")
    (d / "IDEA-003.md").write_text("---\nid: IDEA-003\n---\n")
    assert next_idea_id(bp) == "IDEA-008"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_ideas.py -v`
Expected: 7 failures with `ImportError: cannot import name 'idea_path' from 'taskmaster_v3'`

- [ ] **Step 3: Add the constants and helpers to `taskmaster_v3.py`**

Find the end of the lessons section (after the last `lesson_*` function — search for `# ── Lessons ─` to locate the section header, then scroll to its end). Insert this new section *immediately after* the lessons section closes:

```python
# ── Ideas ────────────────────────────────────────────────────

# Required frontmatter fields validated on every write.
_IDEA_REQUIRED_FIELDS = ("id", "title", "created", "created_by")

# Fields surfaced in the IDEAS.md line + viewer summary list.
_IDEA_INDEX_LINE_STATUS_KEY = "status"


def idea_path(backlog_path: Path, idea_id: str) -> Path:
    return backlog_path.parent / "ideas" / f"{idea_id}.md"


def idea_dir(backlog_path: Path) -> Path:
    return backlog_path.parent / "ideas"


def ideas_index_path(backlog_path: Path) -> Path:
    return backlog_path.parent / "ideas" / "IDEAS.md"


def list_idea_ids(backlog_path: Path) -> list[str]:
    """List idea ids on disk, sorted numerically by trailing number."""
    d = idea_dir(backlog_path)
    if not d.exists():
        return []

    def _rank(p: Path) -> int:
        m = re.search(r"(\d+)$", p.stem)
        return int(m.group(1)) if m else -1

    files = sorted(d.glob("IDEA-*.md"), key=_rank)
    return [p.stem for p in files]


def next_idea_id(backlog_path: Path) -> str:
    """Allocate the next IDEA-NNN id (zero-padded, 3+ digits)."""
    existing = list_idea_ids(backlog_path)
    nums: list[int] = []
    for ident in existing:
        m = re.search(r"(\d+)$", ident)
        if m:
            nums.append(int(m.group(1)))
    n = (max(nums) + 1) if nums else 1
    return f"IDEA-{n:03d}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_ideas.py -v`
Expected: 7 passing.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_v3_ideas.py
git commit -m "feat(taskmaster): idea path helpers + ID allocator"
```

---

## Task 2: write_idea + read_idea + IDEAS.md index

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py` (extend Ideas section)
- Modify: `plugins/taskmaster/tests/test_v3_ideas.py` (extend)

- [ ] **Step 1: Add failing tests for write/read + index**

Append to `tests/test_v3_ideas.py`:

```python
def test_write_idea_minimal(tmp_path):
    from taskmaster_v3 import write_idea, read_idea
    bp = tmp_path / ".taskmaster" / "backlog.yaml"
    bp.parent.mkdir(parents=True)
    iid, path = write_idea(bp, title="Per-task spike budgets")
    assert iid == "IDEA-001"
    assert path.exists()
    fm, body = read_idea(bp, iid)
    assert fm["id"] == "IDEA-001"
    assert fm["title"] == "Per-task spike budgets"
    assert fm["created_by"] == "Claude"
    assert fm["status"] == ""
    assert fm["tags"] == []
    assert fm["related_tasks"] == []
    assert fm["archived"] is False
    assert fm["promoted_to"] is None
    assert "created" in fm  # ISO-8601 string
    assert body == ""


def test_write_idea_full_payload(tmp_path):
    from taskmaster_v3 import write_idea, read_idea
    bp = tmp_path / ".taskmaster" / "backlog.yaml"
    bp.parent.mkdir(parents=True)
    iid, _ = write_idea(
        bp,
        title="Auto-tag from git diff",
        body="## Why\n\nLink ideas to recent files.",
        tags=["automation", "perf"],
        status="exploring",
        related_tasks=["v3-release-007"],
        related_issues=["ISS-004"],
        related_lessons=["L-001"],
        created_by="user",
    )
    fm, body = read_idea(bp, iid)
    assert fm["tags"] == ["automation", "perf"]
    assert fm["status"] == "exploring"
    assert fm["related_tasks"] == ["v3-release-007"]
    assert fm["related_issues"] == ["ISS-004"]
    assert fm["related_lessons"] == ["L-001"]
    assert fm["created_by"] == "user"
    assert "Link ideas to recent files" in body


def test_write_idea_rejects_empty_title(tmp_path):
    import pytest as _pytest
    from taskmaster_v3 import write_idea
    bp = tmp_path / ".taskmaster" / "backlog.yaml"
    bp.parent.mkdir(parents=True)
    with _pytest.raises(ValueError, match="title"):
        write_idea(bp, title="   ")


def test_write_idea_appends_to_index(tmp_path):
    from taskmaster_v3 import write_idea, ideas_index_path
    bp = tmp_path / ".taskmaster" / "backlog.yaml"
    bp.parent.mkdir(parents=True)
    write_idea(bp, title="First idea")
    write_idea(bp, title="Second idea", status="exploring")
    idx = ideas_index_path(bp).read_text()
    assert idx.startswith("# Ideas\n")
    # Newest first within the file
    lines = [l for l in idx.splitlines() if l.startswith("- ")]
    assert len(lines) == 2
    assert "IDEA-002" in lines[0]
    assert "Second idea" in lines[0]
    assert "_(exploring)_" in lines[0]
    assert "IDEA-001" in lines[1]
    assert "First idea" in lines[1]
    # No status suffix when status is empty
    assert "_()_" not in lines[1]


def test_write_idea_sequential_ids(tmp_path):
    from taskmaster_v3 import write_idea
    bp = tmp_path / ".taskmaster" / "backlog.yaml"
    bp.parent.mkdir(parents=True)
    a, _ = write_idea(bp, title="a")
    b, _ = write_idea(bp, title="b")
    c, _ = write_idea(bp, title="c")
    assert (a, b, c) == ("IDEA-001", "IDEA-002", "IDEA-003")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_ideas.py -v`
Expected: 5 new failures (ImportError on `write_idea` / `read_idea`).

- [ ] **Step 3: Implement write_idea, read_idea, and the index helper**

Append to the Ideas section in `taskmaster_v3.py` (right after `next_idea_id`):

```python
def _validate_idea(fm: dict[str, Any]) -> None:
    """Raise ValueError if frontmatter violates idea invariants.

    Idea schema is intentionally minimal — only id/title/created/created_by
    are required. Everything else is optional, freeform passthrough.
    """
    for key in _IDEA_REQUIRED_FIELDS:
        if key not in fm or fm[key] in (None, ""):
            raise ValueError(f"idea field {key!r} is required")
    if not isinstance(fm.get("title"), str) or not fm["title"].strip():
        raise ValueError("idea title must be a non-empty string")


def _idea_index_line(fm: dict[str, Any]) -> str:
    """Render one IDEAS.md line for an idea record."""
    iid = fm["id"]
    title = fm["title"]
    status = fm.get("status") or ""
    created = fm.get("created", "")
    # "2026-05-09T14:30:00Z" → "2026-05-09 14:30"
    short = created[:16].replace("T", " ") if isinstance(created, str) else ""
    suffix = f" _({status})_" if status else ""
    text = f"- {short} — [{iid}]({iid}.md) — {title}{suffix}"
    if fm.get("archived"):
        # Strike through title; keep status suffix readable
        text = f"- {short} — [{iid}]({iid}.md) — ~~{title}~~ _(archived)_"
    return text


def _read_ideas_index(backlog_path: Path) -> list[str]:
    """Return the data lines (non-header) of IDEAS.md, newest-first preserved."""
    p = ideas_index_path(backlog_path)
    if not p.exists():
        return []
    return [l for l in p.read_text(encoding="utf-8").splitlines() if l.startswith("- ")]


def _write_ideas_index(backlog_path: Path, lines: list[str]) -> None:
    """Write IDEAS.md with the canonical header + the supplied data lines."""
    p = ideas_index_path(backlog_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    body = "# Ideas\n\n" + "\n".join(lines) + ("\n" if lines else "")
    atomic_write(p, body)


def _index_upsert_line(lines: list[str], idea_id: str, new_line: str) -> list[str]:
    """Replace the line for `idea_id` if present; otherwise prepend (newest first)."""
    out: list[str] = []
    found = False
    for l in lines:
        if f"[{idea_id}]" in l:
            out.append(new_line)
            found = True
        else:
            out.append(l)
    if not found:
        out.insert(0, new_line)
    return out


def write_idea(
    backlog_path: Path,
    *,
    title: str,
    body: str = "",
    tags: list[str] | None = None,
    status: str = "",
    related_tasks: list[str] | None = None,
    related_issues: list[str] | None = None,
    related_lessons: list[str] | None = None,
    created_by: str = "Claude",
    idea_id: str | None = None,
) -> tuple[str, Path]:
    """Create a new idea file. Returns (id, path).

    All fields beyond `title` are optional. `created` is auto-stamped as
    ISO-8601 UTC. Side effect: appends/updates the IDEAS.md index line.
    """
    if not title or not title.strip():
        raise ValueError("idea title is required")
    iid = idea_id or next_idea_id(backlog_path)
    from datetime import datetime, timezone
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    fm: dict[str, Any] = {
        "id": iid,
        "title": title.strip(),
        "created": created,
        "created_by": created_by or "Claude",
        "status": status or "",
        "tags": list(tags or []),
        "related_tasks": list(related_tasks or []),
        "related_issues": list(related_issues or []),
        "related_lessons": list(related_lessons or []),
        "promoted_to": None,
        "archived": False,
    }
    _validate_idea(fm)
    target = idea_path(backlog_path, iid)
    target.parent.mkdir(parents=True, exist_ok=True)
    write_task_file(target, fm, body)
    lines = _index_upsert_line(_read_ideas_index(backlog_path), iid, _idea_index_line(fm))
    _write_ideas_index(backlog_path, lines)
    return iid, target


def read_idea(backlog_path: Path, idea_id: str) -> tuple[dict[str, Any], str]:
    return read_task_file(idea_path(backlog_path, idea_id))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_ideas.py -v`
Expected: all 12 passing (7 from Task 1 + 5 new).

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_v3_ideas.py
git commit -m "feat(taskmaster): write_idea + read_idea + IDEAS.md index"
```

---

## Task 3: update_idea (covers archive + promote)

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py` (extend Ideas section)
- Modify: `plugins/taskmaster/tests/test_v3_ideas.py` (extend)

- [ ] **Step 1: Add failing tests**

Append to `tests/test_v3_ideas.py`:

```python
def test_update_idea_status(tmp_path):
    from taskmaster_v3 import write_idea, update_idea, read_idea
    bp = tmp_path / ".taskmaster" / "backlog.yaml"
    bp.parent.mkdir(parents=True)
    iid, _ = write_idea(bp, title="An idea")
    update_idea(bp, iid, status="parking-lot")
    fm, _ = read_idea(bp, iid)
    assert fm["status"] == "parking-lot"


def test_update_idea_archive_sets_flag_and_strikes_index(tmp_path):
    from taskmaster_v3 import write_idea, update_idea, read_idea, ideas_index_path
    bp = tmp_path / ".taskmaster" / "backlog.yaml"
    bp.parent.mkdir(parents=True)
    iid, _ = write_idea(bp, title="Drop-this idea")
    update_idea(bp, iid, archived=True)
    fm, _ = read_idea(bp, iid)
    assert fm["archived"] is True
    idx = ideas_index_path(bp).read_text()
    assert "~~Drop-this idea~~" in idx
    assert "_(archived)_" in idx


def test_update_idea_promote_records_task_id(tmp_path):
    from taskmaster_v3 import write_idea, update_idea, read_idea
    bp = tmp_path / ".taskmaster" / "backlog.yaml"
    bp.parent.mkdir(parents=True)
    iid, _ = write_idea(bp, title="Becomes a task")
    update_idea(bp, iid, promoted_to="T-XYZ")
    fm, _ = read_idea(bp, iid)
    assert fm["promoted_to"] == "T-XYZ"


def test_update_idea_body_replacement(tmp_path):
    from taskmaster_v3 import write_idea, update_idea, read_idea
    bp = tmp_path / ".taskmaster" / "backlog.yaml"
    bp.parent.mkdir(parents=True)
    iid, _ = write_idea(bp, title="An idea", body="old body")
    update_idea(bp, iid, body="new body")
    _, body = read_idea(bp, iid)
    assert body == "new body"


def test_update_idea_preserves_body_when_not_passed(tmp_path):
    from taskmaster_v3 import write_idea, update_idea, read_idea
    bp = tmp_path / ".taskmaster" / "backlog.yaml"
    bp.parent.mkdir(parents=True)
    iid, _ = write_idea(bp, title="Keep me", body="original body")
    update_idea(bp, iid, status="exploring")
    _, body = read_idea(bp, iid)
    assert body == "original body"


def test_update_idea_unknown_id_raises(tmp_path):
    import pytest as _pytest
    from taskmaster_v3 import update_idea
    bp = tmp_path / ".taskmaster" / "backlog.yaml"
    bp.parent.mkdir(parents=True)
    with _pytest.raises(FileNotFoundError):
        update_idea(bp, "IDEA-999", status="exploring")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_ideas.py -v`
Expected: 6 new failures (ImportError on `update_idea`).

- [ ] **Step 3: Implement update_idea**

Append to the Ideas section in `taskmaster_v3.py`:

```python
def update_idea(
    backlog_path: Path,
    idea_id: str,
    **updates: Any,
) -> tuple[dict[str, Any], str]:
    """Patch an idea's frontmatter and/or body. Returns (fm, body) post-write.

    Body is preserved unchanged unless `body=` is passed. The IDEAS.md line
    for this idea is rewritten in place to reflect the new title / status /
    archived flag.
    """
    target = idea_path(backlog_path, idea_id)
    if not target.exists():
        raise FileNotFoundError(f"Idea not found: {idea_id}")
    fm, body = read_idea(backlog_path, idea_id)
    new_body = updates.pop("body", body)
    # Pass-through merge — accepts None values for promoted_to (un-promote).
    for k, v in updates.items():
        fm[k] = v
    _validate_idea(fm)
    write_task_file(target, fm, new_body)
    lines = _index_upsert_line(_read_ideas_index(backlog_path), idea_id, _idea_index_line(fm))
    _write_ideas_index(backlog_path, lines)
    return fm, new_body
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_ideas.py -v`
Expected: all 18 passing (12 + 6 new).

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_v3_ideas.py
git commit -m "feat(taskmaster): update_idea covers archive + promote + body edits"
```

---

## Task 4: list_ideas with filters

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py` (extend Ideas section)
- Modify: `plugins/taskmaster/tests/test_v3_ideas.py` (extend)

- [ ] **Step 1: Add failing tests**

Append to `tests/test_v3_ideas.py`:

```python
def test_list_ideas_empty(tmp_path):
    from taskmaster_v3 import list_ideas
    bp = tmp_path / ".taskmaster" / "backlog.yaml"
    bp.parent.mkdir(parents=True)
    assert list_ideas(bp) == []


def test_list_ideas_returns_summaries_newest_first(tmp_path):
    from taskmaster_v3 import write_idea, list_ideas
    bp = tmp_path / ".taskmaster" / "backlog.yaml"
    bp.parent.mkdir(parents=True)
    write_idea(bp, title="oldest")
    write_idea(bp, title="middle")
    write_idea(bp, title="newest")
    out = list_ideas(bp)
    assert [e["title"] for e in out] == ["newest", "middle", "oldest"]
    assert out[0]["id"] == "IDEA-003"
    # Body is omitted in summaries
    assert "body" not in out[0]


def test_list_ideas_excludes_archived_by_default(tmp_path):
    from taskmaster_v3 import write_idea, update_idea, list_ideas
    bp = tmp_path / ".taskmaster" / "backlog.yaml"
    bp.parent.mkdir(parents=True)
    a, _ = write_idea(bp, title="active")
    b, _ = write_idea(bp, title="archived")
    update_idea(bp, b, archived=True)
    ids = [e["id"] for e in list_ideas(bp)]
    assert a in ids
    assert b not in ids


def test_list_ideas_includes_archived_when_requested(tmp_path):
    from taskmaster_v3 import write_idea, update_idea, list_ideas
    bp = tmp_path / ".taskmaster" / "backlog.yaml"
    bp.parent.mkdir(parents=True)
    write_idea(bp, title="active")
    b, _ = write_idea(bp, title="archived")
    update_idea(bp, b, archived=True)
    ids = [e["id"] for e in list_ideas(bp, archived=True)]
    assert "IDEA-001" in ids and "IDEA-002" in ids


def test_list_ideas_filter_by_status(tmp_path):
    from taskmaster_v3 import write_idea, list_ideas
    bp = tmp_path / ".taskmaster" / "backlog.yaml"
    bp.parent.mkdir(parents=True)
    write_idea(bp, title="exploring one", status="exploring")
    write_idea(bp, title="parked one", status="parking-lot")
    out = list_ideas(bp, status="exploring")
    assert [e["title"] for e in out] == ["exploring one"]


def test_list_ideas_filter_by_tag(tmp_path):
    from taskmaster_v3 import write_idea, list_ideas
    bp = tmp_path / ".taskmaster" / "backlog.yaml"
    bp.parent.mkdir(parents=True)
    write_idea(bp, title="perf", tags=["perf", "automation"])
    write_idea(bp, title="ux", tags=["ux"])
    out = list_ideas(bp, tag="perf")
    assert [e["title"] for e in out] == ["perf"]


def test_list_ideas_filter_by_related_task(tmp_path):
    from taskmaster_v3 import write_idea, list_ideas
    bp = tmp_path / ".taskmaster" / "backlog.yaml"
    bp.parent.mkdir(parents=True)
    write_idea(bp, title="linked", related_tasks=["v3-release-007"])
    write_idea(bp, title="unlinked")
    out = list_ideas(bp, related_task="v3-release-007")
    assert [e["title"] for e in out] == ["linked"]


def test_list_ideas_idea_id_returns_full_record(tmp_path):
    from taskmaster_v3 import write_idea, list_ideas
    bp = tmp_path / ".taskmaster" / "backlog.yaml"
    bp.parent.mkdir(parents=True)
    iid, _ = write_idea(bp, title="single", body="full body content")
    out = list_ideas(bp, idea_id=iid)
    assert len(out) == 1
    # Single-id returns body too
    assert out[0]["body"] == "full body content"


def test_list_ideas_limit(tmp_path):
    from taskmaster_v3 import write_idea, list_ideas
    bp = tmp_path / ".taskmaster" / "backlog.yaml"
    bp.parent.mkdir(parents=True)
    for i in range(5):
        write_idea(bp, title=f"idea {i}")
    out = list_ideas(bp, limit=3)
    assert len(out) == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_ideas.py -v`
Expected: 9 new failures (`list_ideas` not defined).

- [ ] **Step 3: Implement list_ideas**

Append to the Ideas section in `taskmaster_v3.py`:

```python
def list_ideas(
    backlog_path: Path,
    *,
    idea_id: str | None = None,
    status: str | None = None,
    tag: str | None = None,
    archived: bool = False,
    related_task: str | None = None,
    related_issue: str | None = None,
    related_lesson: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """List ideas with optional filters.

    Default sort is newest-first by `created`. Pass `idea_id` to fetch one
    record (body included). Without `idea_id`, results are summaries —
    the markdown body is omitted to keep payloads small.

    Filters compose as AND. `archived` defaults to False; pass True to
    include archived ideas in the result set.
    """
    if idea_id:
        target = idea_path(backlog_path, idea_id)
        if not target.exists():
            return []
        fm, body = read_idea(backlog_path, idea_id)
        return [{**fm, "body": body}]

    out: list[dict[str, Any]] = []
    for iid in list_idea_ids(backlog_path):
        try:
            fm, _ = read_idea(backlog_path, iid)
        except (OSError, ValueError):
            continue
        if not archived and fm.get("archived"):
            continue
        if status is not None and (fm.get("status") or "") != status:
            continue
        if tag is not None and tag not in (fm.get("tags") or []):
            continue
        if related_task is not None and related_task not in (fm.get("related_tasks") or []):
            continue
        if related_issue is not None and related_issue not in (fm.get("related_issues") or []):
            continue
        if related_lesson is not None and related_lesson not in (fm.get("related_lessons") or []):
            continue
        out.append(fm)

    out.sort(key=lambda e: e.get("created", ""), reverse=True)
    if limit is not None:
        out = out[: max(0, limit)]
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_ideas.py -v`
Expected: all 27 passing (18 + 9 new).

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_v3_ideas.py
git commit -m "feat(taskmaster): list_ideas with status/tag/archived/related filters"
```

---

## Task 5: MCP wrappers — `backlog_idea_create` / `_list` / `_update`

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py` (add three MCP tools next to `backlog_issue_*`)
- Modify: `plugins/taskmaster/tests/test_mcp_v3_exposure.py` (extend expected names)
- Create: `plugins/taskmaster/tests/test_server_ideas.py`

- [ ] **Step 1: Find import block + helper aliases for ideas**

Open `backlog_server.py` and locate the imports near the top of the file. Add idea helpers to the existing `from taskmaster_v3 import (...)` block — find the line that imports `_write_issue` / `_read_issue` / `_update_issue` (or their unaliased forms) and add the idea equivalents alongside.

For example, change:
```python
from taskmaster_v3 import (
    ...
    write_issue as _write_issue,
    read_issue as _read_issue,
    update_issue as _update_issue,
    ...
)
```
to also include:
```python
    write_idea as _write_idea,
    read_idea as _read_idea,
    update_idea as _update_idea,
    list_ideas as _list_ideas,
    idea_path as _idea_path,
```

If the file imports the unaliased names instead, mirror that style — match what's already there.

- [ ] **Step 2: Add the MCP exposure-test expectation first**

Open `plugins/taskmaster/tests/test_mcp_v3_exposure.py`. Find the list of expected tool names (search for `backlog_issue_create` to locate it). Add three entries next to the issue ones:

```python
        "backlog_idea_create",
        "backlog_idea_list",
        "backlog_idea_update",
```

Run: `python -m pytest plugins/taskmaster/tests/test_mcp_v3_exposure.py -v`
Expected: FAIL — the new names aren't registered yet.

- [ ] **Step 3: Write the failing test for the create wrapper**

Create `plugins/taskmaster/tests/test_server_ideas.py`:

```python
"""HTTP + MCP wrapper tests for ideas."""
from pathlib import Path


def test_backlog_idea_create_writes_file_and_returns_id(tmp_path, monkeypatch):
    import backlog_server
    bp = tmp_path / ".taskmaster" / "backlog.yaml"
    bp.parent.mkdir(parents=True)
    bp.write_text("schema_version: 3\nphases: []\n")
    monkeypatch.setattr(backlog_server, "_backlog_path", lambda: bp)

    out = backlog_server.backlog_idea_create(
        title="Per-task spike budgets",
        body="why and how",
        tags=["perf"],
        status="exploring",
    )
    assert "IDEA-001" in out
    assert (tmp_path / ".taskmaster" / "ideas" / "IDEA-001.md").exists()
    assert (tmp_path / ".taskmaster" / "ideas" / "IDEAS.md").exists()


def test_backlog_idea_create_no_backlog_returns_error(tmp_path, monkeypatch):
    import backlog_server
    bp = tmp_path / ".taskmaster" / "backlog.yaml"  # does not exist
    monkeypatch.setattr(backlog_server, "_backlog_path", lambda: bp)
    out = backlog_server.backlog_idea_create(title="anything")
    assert out.startswith("Error:")


def test_backlog_idea_list_filters(tmp_path, monkeypatch):
    import backlog_server
    bp = tmp_path / ".taskmaster" / "backlog.yaml"
    bp.parent.mkdir(parents=True)
    bp.write_text("schema_version: 3\nphases: []\n")
    monkeypatch.setattr(backlog_server, "_backlog_path", lambda: bp)
    backlog_server.backlog_idea_create(title="A", status="exploring")
    backlog_server.backlog_idea_create(title="B", status="parking-lot")
    out = backlog_server.backlog_idea_list(status="exploring")
    assert "IDEA-001" in out
    assert "IDEA-002" not in out


def test_backlog_idea_list_idea_id_returns_full(tmp_path, monkeypatch):
    import backlog_server
    bp = tmp_path / ".taskmaster" / "backlog.yaml"
    bp.parent.mkdir(parents=True)
    bp.write_text("schema_version: 3\nphases: []\n")
    monkeypatch.setattr(backlog_server, "_backlog_path", lambda: bp)
    backlog_server.backlog_idea_create(title="solo", body="full body here")
    out = backlog_server.backlog_idea_list(idea_id="IDEA-001")
    assert "IDEA-001" in out
    assert "full body here" in out


def test_backlog_idea_update_archive(tmp_path, monkeypatch):
    import backlog_server
    bp = tmp_path / ".taskmaster" / "backlog.yaml"
    bp.parent.mkdir(parents=True)
    bp.write_text("schema_version: 3\nphases: []\n")
    monkeypatch.setattr(backlog_server, "_backlog_path", lambda: bp)
    backlog_server.backlog_idea_create(title="archive me")
    out = backlog_server.backlog_idea_update(idea_id="IDEA-001", archived=True)
    assert "IDEA-001" in out
    idx = (tmp_path / ".taskmaster" / "ideas" / "IDEAS.md").read_text()
    assert "~~archive me~~" in idx


def test_backlog_idea_update_unknown_id_returns_error(tmp_path, monkeypatch):
    import backlog_server
    bp = tmp_path / ".taskmaster" / "backlog.yaml"
    bp.parent.mkdir(parents=True)
    bp.write_text("schema_version: 3\nphases: []\n")
    monkeypatch.setattr(backlog_server, "_backlog_path", lambda: bp)
    out = backlog_server.backlog_idea_update(idea_id="IDEA-999", status="x")
    assert out.startswith("Idea not found")
```

Run: `python -m pytest plugins/taskmaster/tests/test_server_ideas.py -v`
Expected: 6 failures — the wrappers don't exist.

- [ ] **Step 4: Implement the three MCP wrappers**

In `backlog_server.py`, find the end of the issue MCP wrappers (search for the line `def backlog_issue_update(` and scroll past it to find where the issue block ends). Insert the three idea wrappers immediately after, before the next major section (typically lessons or another `# ──` divider):

```python
@mcp.tool()
def backlog_idea_create(
    title: str,
    body: str = "",
    tags: list[str] | None = None,
    status: str = "",
    related_tasks: list[str] | None = None,
    related_issues: list[str] | None = None,
    related_lessons: list[str] | None = None,
    created_by: str = "Claude",
) -> str:
    """Log an idea — a lightweight, unvalidated thought. Lighter than a task.

    An *idea* is a parking lot for things you might want to do, explore, or
    revisit. It can grow into a task / lesson / issue later via linkage.
    Title is required; everything else is optional. Status is freeform.

    Args:
        title: Required. Short summary.
        body: Markdown body — anything goes (sketches, code blocks, prose).
        tags: Freeform tag strings.
        status: Freeform status ("exploring", "parking-lot", "candidate", "").
        related_tasks: Task ids this idea relates to.
        related_issues: Issue ids this idea relates to.
        related_lessons: Lesson ids this idea relates to.
        created_by: Who logged it ("Claude" by default; "user" when
            invoked via /add-idea).
    """
    bp = _backlog_path()
    if not bp.exists():
        return f"Error: no backlog found at {bp}. Run `backlog_init` first."
    try:
        iid, target = _write_idea(
            bp,
            title=title,
            body=body,
            tags=tags or [],
            status=status,
            related_tasks=related_tasks or [],
            related_issues=related_issues or [],
            related_lessons=related_lessons or [],
            created_by=created_by,
        )
    except ValueError as exc:
        return f"Error: {exc}"
    return f"Idea created: {iid} — {title}\nFile: {target.relative_to(ROOT)}"


@mcp.tool()
def backlog_idea_list(
    idea_id: str = "",
    status: str = "",
    tag: str = "",
    archived: bool = False,
    related_task: str = "",
    related_issue: str = "",
    related_lesson: str = "",
    limit: int = 50,
) -> str:
    """List ideas, optionally filtered. With `idea_id`, returns one full record.

    Without `idea_id`, returns summary lines (no body) — newest first.
    Filters compose as AND. By default archived ideas are excluded.
    """
    bp = _backlog_path()
    if not bp.exists():
        return "No backlog found."
    if idea_id:
        out = _list_ideas(bp, idea_id=idea_id)
        if not out:
            return f"Idea not found: {idea_id}"
        rec = out[0]
        body = rec.pop("body", "")
        fm_lines = [f"  {k}: {v}" for k, v in rec.items()]
        return "---\n" + "\n".join(fm_lines) + "\n---\n" + body

    entries = _list_ideas(
        bp,
        status=status or None,
        tag=tag or None,
        archived=archived,
        related_task=related_task or None,
        related_issue=related_issue or None,
        related_lesson=related_lesson or None,
        limit=max(1, limit),
    )
    if not entries:
        return "No ideas match."
    lines = []
    for e in entries:
        st = e.get("status") or ""
        st_tag = f" [{st}]" if st else ""
        lines.append(f"- {e['id']} — {e.get('title', '')}{st_tag}")
    return "\n".join(lines)


@mcp.tool()
def backlog_idea_update(
    idea_id: str,
    title: str = "",
    body: str = "",
    status: str = "",
    tags: list[str] | None = None,
    related_tasks: list[str] | None = None,
    related_issues: list[str] | None = None,
    related_lessons: list[str] | None = None,
    promoted_to: str = "",
    archived: bool | None = None,
) -> str:
    """Patch an idea's frontmatter and/or body.

    Pass empty strings / None to skip a field. To promote an idea into a
    task, pass `promoted_to="T-XYZ"` and optionally `archived=True`. To
    archive without promotion, pass `archived=True`.
    """
    bp = _backlog_path()
    if not bp.exists():
        return "No backlog found."
    updates: dict[str, Any] = {}
    if title:
        updates["title"] = title
    if body:
        updates["body"] = body
    if status:
        updates["status"] = status
    if tags is not None:
        updates["tags"] = tags
    if related_tasks is not None:
        updates["related_tasks"] = related_tasks
    if related_issues is not None:
        updates["related_issues"] = related_issues
    if related_lessons is not None:
        updates["related_lessons"] = related_lessons
    if promoted_to:
        updates["promoted_to"] = promoted_to
    if archived is not None:
        updates["archived"] = archived

    try:
        fm, _ = _update_idea(bp, idea_id, **updates)
    except FileNotFoundError:
        return f"Idea not found: {idea_id}"
    except ValueError as exc:
        return f"Error: {exc}"
    return f"Idea updated: {idea_id} — {fm.get('title', '')}"
```

Note: if `Any` is not already imported in `backlog_server.py`, add `from typing import Any` near the top imports.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest plugins/taskmaster/tests/test_server_ideas.py plugins/taskmaster/tests/test_mcp_v3_exposure.py -v`
Expected: all green (6 idea wrapper tests + the exposure test now satisfied).

- [ ] **Step 6: Commit**

```bash
git add plugins/taskmaster/backlog_server.py \
        plugins/taskmaster/tests/test_server_ideas.py \
        plugins/taskmaster/tests/test_mcp_v3_exposure.py
git commit -m "feat(taskmaster): backlog_idea_create/_list/_update MCP tools"
```

---

## Task 6: `taskmaster:add-idea` skill

**Files:**
- Create: `plugins/taskmaster/skills/add-idea/SKILL.md`
- Create: `plugins/taskmaster/skills/add-idea/templates/idea-body.md`
- Create: `plugins/taskmaster/tests/test_add_idea_skill_lint.py`

- [ ] **Step 1: Write the lint test**

Create `plugins/taskmaster/tests/test_add_idea_skill_lint.py`:

```python
"""Structural lint for the taskmaster:add-idea skill."""
from pathlib import Path

SKILL_PATH = Path(__file__).parent.parent / "skills" / "add-idea" / "SKILL.md"


def test_skill_file_exists():
    assert SKILL_PATH.exists()


def test_skill_has_frontmatter():
    text = SKILL_PATH.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "name: add-idea" in text
    assert "description:" in text


def test_skill_calls_backlog_idea_create():
    text = SKILL_PATH.read_text(encoding="utf-8")
    assert "backlog_idea_create" in text


def test_skill_documents_slash_form():
    text = SKILL_PATH.read_text(encoding="utf-8")
    assert "/add-idea" in text


def test_skill_documents_optional_flags():
    text = SKILL_PATH.read_text(encoding="utf-8")
    for flag in ("--tags", "--status", "--related-task"):
        assert flag in text


def test_skill_announces_id_on_commit():
    text = SKILL_PATH.read_text(encoding="utf-8")
    # Skill must instruct the model to report the IDEA-NNN id back to the user
    assert "Logged as IDEA" in text or "IDEA-NNN" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest plugins/taskmaster/tests/test_add_idea_skill_lint.py -v`
Expected: 6 failures — the file doesn't exist.

- [ ] **Step 3: Create the skill body**

Create `plugins/taskmaster/skills/add-idea/SKILL.md`:

```markdown
---
name: add-idea
description: Log a lightweight idea (parking-lot thought) into .taskmaster/ideas/ as IDEA-NNN.md. Invoke when the user says "/add-idea …", "save this as an idea", "remember this idea", "log this idea", "that's a good idea, save it", or describes something worth keeping but not yet ready to be a task. Lighter than a task — just a freeform note with optional tags, status, and links to tasks/issues/lessons. The only correct way to write an idea — do not call backlog_idea_create directly.
---

# Add Idea

A lightweight place to record thoughts, parking-lot items, half-baked observations, and "future work" ideas without spawning a task and adding noise to the backlog.

## When to invoke

- User typed `/add-idea ...` (slash form)
- User said: "save this as an idea", "remember this idea", "log this idea", "let's note this", "park this for later"
- User described an idea explicitly: "I want to try X", "we should explore Y", "future work: Z"
- You auto-detected a sharp idea mid-conversation per the heuristics in `taskmaster:start-session` (path C — confidence-threshold auto-log)

## Slash form

```
/add-idea Per-task spike budgets — track effort vs estimate to flag scope drift early
/add-idea Auto-tag from git diff --tags automation,perf --status exploring --related-task v3-release-007
```

Optional flags (any subset):
- `--tags <comma-separated>` — freeform tag strings
- `--status <freeform-string>` — e.g. `exploring`, `parking-lot`, `candidate`
- `--related-task <task-id>` — repeat for multiple
- `--related-issue <issue-id>` — repeat for multiple
- `--related-lesson <lesson-id>` — repeat for multiple

## Natural-language form

The user can also say "save this as an idea: <text>" and you should treat it the same as a slash call with the text as the body.

## Procedure

1. **Parse the input.** Title is the first sentence/clause if not separately specified. Body is the full text. Pull any optional flags out of the input.
2. **Search for duplicates.** Call `backlog_idea_list(limit=20)` and check the returned summaries for an existing idea covering the same ground. If you find one, don't create a duplicate — tell the user and offer to update the existing idea via `backlog_idea_update` instead.
3. **Commit.** Call:
   ```
   backlog_idea_create(
       title="<derived or given>",
       body="<full text minus flags>",
       tags=[...],
       status="<freeform>",
       related_tasks=[...],
       related_issues=[...],
       related_lessons=[...],
       created_by="user",   # this skill is user-initiated
   )
   ```
4. **Announce.** Reply with the format:
   > _Logged as IDEA-NNN — "<title>"_

   Optionally include the file path. Do NOT also include a long summary — the announcement is one line.

## Auto-log path (Claude-initiated)

When you detect a sharp idea mid-conversation (heuristics in `start-session/SKILL.md`), don't invoke this skill — call `backlog_idea_create` directly with `created_by="Claude"`. Then announce inline:

> _Logged as IDEA-NNN — "<title>"_

This skill is the user-driven write path; the auto-log direct call is the Claude-driven path. Both go through the same MCP tool.

## What NOT to do

- Don't ask the user to confirm before logging — log it, announce, move on. The whole point is low friction.
- Don't make ideas into tasks. If the user wants a task, they'll ask.
- Don't add detail beyond what the user said. The body is freeform; resist the urge to expand it.
- Don't link `promoted_to`. That field is set when an idea is promoted to a task (via `backlog_idea_update(promoted_to="T-XYZ")`), not at creation.
```

- [ ] **Step 4: Create the body template**

Create `plugins/taskmaster/skills/add-idea/templates/idea-body.md`:

```markdown
<!--
Optional template for the body of an IDEA-NNN.md file. The skill does NOT
require this template — bodies are freeform. Use it only when the user
gives you nothing but a one-line title and you want a starting structure.
-->

## Why

<!-- what motivated this idea — a frustration, a missed opportunity, a pattern noticed -->

## What

<!-- the actual idea, as concretely as you can express it -->

## Open questions

<!-- things to figure out before this could become a task -->
```

- [ ] **Step 5: Run lint test to verify it passes**

Run: `python -m pytest plugins/taskmaster/tests/test_add_idea_skill_lint.py -v`
Expected: all 6 passing.

- [ ] **Step 6: Commit**

```bash
git add plugins/taskmaster/skills/add-idea/ plugins/taskmaster/tests/test_add_idea_skill_lint.py
git commit -m "feat(taskmaster): taskmaster:add-idea skill for explicit idea capture"
```

---

## Task 7: start-session mid-session behavior — lesson-emit fix + idea-emit heuristics

**Files:**
- Modify: `plugins/taskmaster/skills/start-session/SKILL.md`
- Modify: `plugins/taskmaster/skills/lesson/references/marker-format.md`

This task ships the lesson-candidate fix folded into the same edit as the new idea-emit guidance. start-session is loaded for every conversation, so heuristics added here are in working context throughout.

- [ ] **Step 1: Read the current marker-format.md to understand the schema convention**

Run: `cat plugins/taskmaster/skills/lesson/references/marker-format.md` (or use the Read tool).

Note the existing `<lesson-candidate>` schema, attribute conventions (e.g. `title="…"`, `kind="…"`, `tags="…"`), and how the body content is described.

- [ ] **Step 2: Append the `<idea-candidate>` schema**

At the end of `plugins/taskmaster/skills/lesson/references/marker-format.md`, append:

```markdown

## `<idea-candidate>` (sister tag)

Mirrors `<lesson-candidate>` but for ideas — lightweight thoughts, parking-lot items, future-work observations not yet ready to be a task.

### Schema

```xml
<idea-candidate title="<short title>" tags="<comma-separated>" status="<freeform>" related-task="<task-id>">
Optional one-paragraph context. Keep it short — the body of the resulting IDEA-NNN.md will be roughly this paragraph plus any quoted user phrasing that triggered the tag.
</idea-candidate>
```

### Attributes

- `title` (required) — short title for the idea (becomes IDEA-NNN.md title field)
- `tags` (optional) — comma-separated freeform tags
- `status` (optional) — freeform status. End-session sets `status="candidate"` automatically when committing tags it found, so don't pre-fill it unless you have a specific value in mind ("parking-lot", "exploring", etc.)
- `related-task` (optional) — task id this idea attaches to (e.g. the active task at the moment of emission)
- `related-issue`, `related-lesson` — same pattern, optional

### When to emit

When the user expresses an *ambient* idea — hedged ("hmm could be cool…"), tangential to the current task, low confidence. End-session sweeps these tags and commits each as IDEA-NNN.md with `status="candidate"`.

If the idea is *sharp* (explicit framing, direct request, concrete-and-named), do NOT emit a tag — call `backlog_idea_create` directly and announce inline. See the start-session skill's "Mid-session behavior" section for the heuristic.
```

- [ ] **Step 3: Locate the right insertion point in start-session/SKILL.md**

Open `plugins/taskmaster/skills/start-session/SKILL.md`. Find a structural anchor near the end of the skill body — common anchor points: the "After the briefing" section, the closing notes, or just before the file's last `---` separator. Insert the new section *as a peer* to the briefing/post-briefing sections (i.e. as another top-level `##` heading), so it isn't visually nested under an unrelated heading.

If unsure of placement, append the section to the very end of the file (before any trailing whitespace or final separator).

- [ ] **Step 4: Insert the mid-session behavior section**

Add this section to `plugins/taskmaster/skills/start-session/SKILL.md`:

```markdown
## Mid-session behavior

While working in a v3 project, watch for two kinds of moments and respond inline — no separate tool call required for the candidate paths.

### Lesson-candidate emission

Emit a `<lesson-candidate>` XML tag inline in your reply (not a tool call) when ANY of these fire:

- **Repeated correction** — the user has corrected you on the same thing twice or more in this session, OR you notice you've corrected yourself on the same pattern multiple times.
- **Bug second-encounter** — you (or the user) hit a bug, gotcha, or surprising behavior that you've already encountered before in this codebase.
- **Architectural ground rule** — the user states a non-obvious "we always do X here" / "we never do Y here" / "in this codebase we…" rule.

Schema: see `plugins/taskmaster/skills/lesson/references/marker-format.md` for the `<lesson-candidate>` tag.

End-session sweeps these tags and either offers them for triage (default behavior) or commits them per the user's preferred flow.

### Idea-candidate emission and idea auto-log

When you detect an *idea* in the user's message — a thought, parking-lot item, future-work observation, or "we could try X" — pick ONE of three paths:

**Path A — Skip entirely.** When:
- User is thinking out loud about the immediate task (not a separable idea).
- Idea is already covered by an existing task or idea (when in doubt, call `backlog_idea_list(limit=20)` first).
- User explicitly said not to capture.

**Path B — Emit `<idea-candidate>` tag (fuzzy capture).** When:
- Hedged / ambient framing: "hmm could be cool…", "maybe at some point", "we could think about", "interesting thought".
- Tangential to the current task — user is mid-flow on something else.
- Concept is fuzzy or speculative.

Don't make a tool call. Inline-emit:
```xml
<idea-candidate title="Auto-tag from git diff" tags="automation,viewer">
User mentioned in passing that linking ideas to recent files would be useful — flagging for end-session.
</idea-candidate>
```

End-session will commit these with `status="candidate"` for later triage in the viewer.

**Path C — Auto-log via `backlog_idea_create` (sharp capture).** When ANY fire:
- Explicit framing: "idea:", "future work:", "for later:", "I want to try", "we should explore", "let's eventually".
- Direct request: "remember this idea", "save this idea", "that's a good idea, log it".
- Concrete-and-named: a specific feature/change with a clear noun and verb that's separable from the current task.

Call `backlog_idea_create(title=..., body=..., created_by="Claude")` and announce inline (single line, no summary):

> _Logged as IDEA-NNN — "<title>"_

Schema for the `<idea-candidate>` tag: see `plugins/taskmaster/skills/lesson/references/marker-format.md`.

### One-line decision tree

```
User said something that might be an idea/lesson?
├─ Lesson trigger fires (correction / bug-twice / ground rule)? → emit <lesson-candidate>
├─ Sharp idea? (explicit framing OR direct request OR concrete-and-named) → call backlog_idea_create + announce
├─ Fuzzy/ambient idea? → emit <idea-candidate>
└─ Otherwise → skip
```
```

- [ ] **Step 5: Manual sanity check — read both files end-to-end**

Read both modified files in full and verify:
- start-session's new section is at top-level (not nested under an unrelated heading)
- marker-format.md's new section is at the end and references the start-session heuristic
- Heuristic wording is concrete, not hand-wavy

- [ ] **Step 6: Commit**

```bash
git add plugins/taskmaster/skills/start-session/SKILL.md \
        plugins/taskmaster/skills/lesson/references/marker-format.md
git commit -m "feat(taskmaster): mid-session emit heuristics for ideas + lessons

Adds a 'Mid-session behavior' section to start-session/SKILL.md so the
emit heuristics for both <lesson-candidate> and <idea-candidate> tags
are loaded into every conversation context. Fixes the longstanding
silence in lesson-candidate flow (root cause: emit guidance lived only
in lesson/SKILL.md, which is not loaded by default). Adds the
<idea-candidate> schema to marker-format.md alongside the lesson tag."
```

---

## Task 8: end-session — extend `<idea-candidate>` scan, commit-direct, report counts

**Files:**
- Modify: `plugins/taskmaster/skills/end-session/SKILL.md`

- [ ] **Step 1: Read the existing lesson-candidate scan section in end-session**

Open `plugins/taskmaster/skills/end-session/SKILL.md` and locate the section that handles `<lesson-candidate>` tags (search for `lesson-candidate` or `lesson_candidates`). Note its structure — that's the pattern to mirror.

- [ ] **Step 2: Add a parallel `<idea-candidate>` scan section**

Right after (or alongside) the lesson-candidate section, add a new section. The exact location should be the same lifecycle phase — the wrap-up steps after task transition but before the final commit.

Insert this content:

```markdown
### Idea-candidate sweep

After completing the work-summary phase, scan the in-context transcript for `<idea-candidate>` XML tags emitted earlier in the session. For each tag found:

1. Parse the `title` attribute (required), `tags`, `status`, `related-task`, `related-issue`, `related-lesson` (all optional).
2. Use the tag's text content as the body. If empty, use the title as the body.
3. Call:
   ```
   backlog_idea_create(
       title=<title>,
       body=<tag-body-or-title>,
       tags=<parsed tags or []>,
       status=<parsed status or "candidate">,   # default to "candidate" so they're filterable in the viewer
       related_tasks=<[task] if related-task else []>,
       related_issues=<[issue] if related-issue else []>,
       related_lessons=<[lesson] if related-lesson else []>,
       created_by="Claude",
   )
   ```
4. Collect the returned IDEA-NNN ids.

**Commit directly — do NOT prompt the user per item.** The user's standing rule is no draft-and-approve gates in end-session.

After all candidates are committed, also tally the IDEA-NNNs that were auto-logged this session via path C (look at the IDEAS.md index for entries with `created` timestamps within the session window — alternatively, just call `backlog_idea_list(limit=10)` and filter to entries newer than the session start).

Report the result inline in the wrap-up summary as a separate bullet:

> **Ideas captured this session:** N total
> - From `<idea-candidate>` tags (committed as `status: "candidate"`): IDEA-009, IDEA-010
> - Auto-logged sharp ideas: IDEA-011

If both counts are zero, omit the bullet entirely.

The user can then review/edit/archive captured ideas at their leisure via the Ideas viewer screen.
```

- [ ] **Step 3: Manual sanity check — read end-session skill end-to-end**

Re-read the entire skill and verify:
- The new section sits in the wrap-up phase, not before task transition.
- It does NOT reintroduce a per-item approval prompt.
- It mentions the standing "no draft-and-approve gates" rule.

- [ ] **Step 4: Commit**

```bash
git add plugins/taskmaster/skills/end-session/SKILL.md
git commit -m "feat(taskmaster): end-session scans <idea-candidate> tags, commits directly

Mirrors the lesson-candidate sweep but commits each idea-candidate
straight to disk via backlog_idea_create with status='candidate'.
No per-item prompt (per user's no-draft-and-approve-gates rule).
Reports counts in the wrap-up summary."
```

---

## Task 9: taskmaster router — routing row for idea intents

**Files:**
- Modify: `plugins/taskmaster/skills/taskmaster/SKILL.md`

- [ ] **Step 1: Locate the routing table**

Open `plugins/taskmaster/skills/taskmaster/SKILL.md` and find the routing table (it has rows like `| (v3) "List issues", "open bugs", "what's broken" | Direct tool call — backlog_issue_list ... |`).

- [ ] **Step 2: Insert the idea routing rows**

Add these rows in the appropriate position (alongside the existing surface routing rows — likely near the issues / lessons rows):

```markdown
| User said "save this as an idea", "remember this idea", "/add-idea ...", or described an idea explicitly | Invoke `taskmaster:add-idea` |
| (v3) "List ideas", "what ideas have I logged", "show parking lot" | Direct tool call — `backlog_idea_list` (filter by `status` or `tag` as needed) |
| (v3) "Archive that idea", "promote IDEA-NNN to a task" | Direct tool call — `backlog_idea_update` (set `archived=True` and/or `promoted_to="<task-id>"`) |
```

If the file has a separate "Direct tool call" section that lists which surfaces can be hit directly, also add `backlog_idea_list` and `backlog_idea_update` to that list.

- [ ] **Step 3: Manual sanity check — read the router skill end-to-end**

Verify:
- Idea rows are placed near issues/lessons rows for symmetry.
- No conflicting/duplicate rows.

- [ ] **Step 4: Commit**

```bash
git add plugins/taskmaster/skills/taskmaster/SKILL.md
git commit -m "feat(taskmaster): router rows for idea intents (add-idea, list, archive/promote)"
```

---

## Task 10: `/api/ideas` HTTP endpoint for the viewer

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py` (add HTTP route alongside `/api/issues`)
- Create: tests inside `plugins/taskmaster/tests/test_server_ideas.py` (extend)

- [ ] **Step 1: Find the existing `/api/issues` HTTP handler to mirror**

Open `backlog_server.py` and search for `/api/issues`. Read the surrounding handler — note how it loads, filters, JSON-serializes, and returns.

- [ ] **Step 2: Write the failing test**

Append to `plugins/taskmaster/tests/test_server_ideas.py`:

```python
def test_get_ideas_returns_list(running_server, tmp_path):
    """Verify /api/ideas serves the JSON the viewer expects."""
    import json
    import urllib.request
    from tests.test_server_api import running_server  # noqa: F811
    base, _ = running_server
    # Seed a couple of ideas via the MCP wrapper so they hit disk.
    import backlog_server
    backlog_server.backlog_idea_create(title="A", status="exploring", tags=["perf"])
    backlog_server.backlog_idea_create(title="B")
    resp = urllib.request.urlopen(f"{base}/api/ideas")
    payload = json.loads(resp.read())
    assert "ideas" in payload
    titles = [i["title"] for i in payload["ideas"]]
    assert "A" in titles
    assert "B" in titles
    # Newest first
    assert payload["ideas"][0]["title"] == "B"


def test_get_ideas_filter_by_status(running_server, tmp_path):
    import json
    import urllib.request
    from tests.test_server_api import running_server  # noqa: F811
    base, _ = running_server
    import backlog_server
    backlog_server.backlog_idea_create(title="A", status="exploring")
    backlog_server.backlog_idea_create(title="B", status="parking-lot")
    resp = urllib.request.urlopen(f"{base}/api/ideas?status=exploring")
    payload = json.loads(resp.read())
    titles = [i["title"] for i in payload["ideas"]]
    assert "A" in titles
    assert "B" not in titles


def test_get_ideas_excludes_archived_by_default(running_server, tmp_path):
    import json
    import urllib.request
    from tests.test_server_api import running_server  # noqa: F811
    base, _ = running_server
    import backlog_server
    backlog_server.backlog_idea_create(title="active")
    backlog_server.backlog_idea_create(title="archived-one")
    backlog_server.backlog_idea_update(idea_id="IDEA-002", archived=True)
    resp = urllib.request.urlopen(f"{base}/api/ideas")
    titles = [i["title"] for i in json.loads(resp.read())["ideas"]]
    assert "active" in titles
    assert "archived-one" not in titles
    # Explicit opt-in returns archived
    resp2 = urllib.request.urlopen(f"{base}/api/ideas?archived=true")
    titles2 = [i["title"] for i in json.loads(resp2.read())["ideas"]]
    assert "archived-one" in titles2
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest plugins/taskmaster/tests/test_server_ideas.py -v -k api`
Expected: 3 failures with HTTP 404 / NotFoundError.

- [ ] **Step 4: Add the HTTP handler in `backlog_server.py`**

Find the `/api/issues` handler in `backlog_server.py` and add a parallel `/api/ideas` handler immediately after it. Match the existing routing convention (whether the project uses a router decorator, a dispatch dict, or a long if/elif chain). Implementation:

```python
def _handle_get_ideas(self, query):
    """GET /api/ideas — list ideas as JSON for the viewer.

    Query params: status, tag, archived (true/false), related_task, limit.
    """
    bp = _backlog_path()
    if not bp.exists():
        self._send_json({"ideas": []})
        return
    archived = (query.get("archived", ["false"])[0].lower() == "true")
    status = query.get("status", [""])[0] or None
    tag = query.get("tag", [""])[0] or None
    related_task = query.get("related_task", [""])[0] or None
    try:
        limit = int(query.get("limit", ["100"])[0])
    except (TypeError, ValueError):
        limit = 100
    entries = _list_ideas(
        bp,
        status=status,
        tag=tag,
        archived=archived,
        related_task=related_task,
        limit=max(1, limit),
    )
    self._send_json({"ideas": entries})
```

Wire it into the request dispatcher next to where `/api/issues` is dispatched. The exact wiring depends on the existing code shape — match it.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest plugins/taskmaster/tests/test_server_ideas.py -v`
Expected: all idea tests passing.

- [ ] **Step 6: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_server_ideas.py
git commit -m "feat(taskmaster): /api/ideas HTTP endpoint for viewer"
```

---

## Task 11: Viewer — `ideas.js` screen + nav entry + chip-filter unit test

**Files:**
- Create: `plugins/taskmaster/viewer/js/screens/ideas.js`
- Modify: `plugins/taskmaster/viewer/js/screens/index.js`
- Modify: `plugins/taskmaster/viewer/backlog-viewer.html`
- Create: `plugins/taskmaster/viewer/tests/unit/ideas-screen.test.js`

- [ ] **Step 1: Read the existing issues screen as the template**

Run: `cat plugins/taskmaster/viewer/js/screens/issues.js` (or use the Read tool).

Note:
- How it loads data (`fetch('/api/issues')`).
- How it builds chip filters (uses the `chipClickNext` helper from `js/util/chip-toggle.js` per L-001).
- How list view → detail view toggling works.
- How frontmatter sidebar links are rendered.

This is the file to mirror.

- [ ] **Step 2: Write the failing chip-filter unit test**

Create `plugins/taskmaster/viewer/tests/unit/ideas-screen.test.js`:

```javascript
// Unit tests for ideas screen chip filtering.
// Mirrors viewer/tests/unit/issues-screen.test.js shape — see that file
// for matching infrastructure setup if details below need adjusting.

import { describe, it, expect, beforeEach } from 'vitest';
import { applyIdeasFilters } from '../../js/screens/ideas.js';

const SAMPLE = [
  { id: 'IDEA-001', title: 'A', status: 'exploring', tags: ['perf'],     archived: false, created: '2026-05-01T00:00:00Z' },
  { id: 'IDEA-002', title: 'B', status: 'parking-lot', tags: ['ux'],      archived: false, created: '2026-05-02T00:00:00Z' },
  { id: 'IDEA-003', title: 'C', status: 'candidate',   tags: ['perf','ai'], archived: false, created: '2026-05-03T00:00:00Z' },
  { id: 'IDEA-004', title: 'D', status: 'parking-lot', tags: [],          archived: true,  created: '2026-05-04T00:00:00Z' },
];

describe('applyIdeasFilters', () => {
  it('returns all non-archived by default, newest first', () => {
    const out = applyIdeasFilters(SAMPLE, { statuses: [], tags: [], includeArchived: false });
    expect(out.map(i => i.id)).toEqual(['IDEA-003', 'IDEA-002', 'IDEA-001']);
  });

  it('filters to a single status', () => {
    const out = applyIdeasFilters(SAMPLE, { statuses: ['exploring'], tags: [], includeArchived: false });
    expect(out.map(i => i.id)).toEqual(['IDEA-001']);
  });

  it('filters to multiple statuses (OR)', () => {
    const out = applyIdeasFilters(SAMPLE, { statuses: ['exploring', 'candidate'], tags: [], includeArchived: false });
    expect(out.map(i => i.id)).toEqual(['IDEA-003', 'IDEA-001']);
  });

  it('filters to a single tag', () => {
    const out = applyIdeasFilters(SAMPLE, { statuses: [], tags: ['perf'], includeArchived: false });
    expect(out.map(i => i.id)).toEqual(['IDEA-003', 'IDEA-001']);
  });

  it('combines status + tag as AND', () => {
    const out = applyIdeasFilters(SAMPLE, { statuses: ['candidate'], tags: ['perf'], includeArchived: false });
    expect(out.map(i => i.id)).toEqual(['IDEA-003']);
  });

  it('includes archived when toggle is on', () => {
    const out = applyIdeasFilters(SAMPLE, { statuses: [], tags: [], includeArchived: true });
    expect(out.map(i => i.id)).toEqual(['IDEA-004', 'IDEA-003', 'IDEA-002', 'IDEA-001']);
  });
});
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd plugins/taskmaster/viewer/tests && npm test -- ideas-screen` (or whatever command the existing viewer tests use — see `package.json` in that dir).

Expected: failure — `ideas.js` does not export `applyIdeasFilters`.

- [ ] **Step 4: Create the screen**

Create `plugins/taskmaster/viewer/js/screens/ideas.js`. Mirror the structure of `issues.js`, with these specifics:

```javascript
// Ideas screen — symmetric with issues.js.
// Shows a list of IDEA-NNN records with chip filters by status + tag,
// list/detail toggle, and a "New idea" button that POSTs to backlog_idea_create.

import { chipClickNext, CHIP_CLICK_HINT } from '../util/chip-toggle.js';

// Pure helper: extracted so it can be unit-tested.
export function applyIdeasFilters(ideas, { statuses, tags, includeArchived }) {
  let out = ideas;
  if (!includeArchived) out = out.filter(i => !i.archived);
  if (statuses && statuses.length) {
    const set = new Set(statuses);
    out = out.filter(i => set.has(i.status || ''));
  }
  if (tags && tags.length) {
    const set = new Set(tags);
    out = out.filter(i => (i.tags || []).some(t => set.has(t)));
  }
  out = [...out].sort((a, b) => (b.created || '').localeCompare(a.created || ''));
  return out;
}

export async function renderIdeasScreen(rootEl) {
  // 1. Fetch data
  const resp = await fetch('/api/ideas?archived=true');  // we filter client-side via the toggle
  const { ideas } = await resp.json();

  // 2. Compute available status + tag chip values from the data
  const statusValues = [...new Set(ideas.map(i => i.status || '').filter(Boolean))].sort();
  const tagValues = [...new Set(ideas.flatMap(i => i.tags || []))].sort();

  // 3. UI state
  const state = { statuses: [], tags: [], includeArchived: false, selectedId: null };

  function rerender() {
    rootEl.innerHTML = '';
    rootEl.appendChild(buildChipRail(state, statusValues, tagValues, rerender));
    const filtered = applyIdeasFilters(ideas, state);
    if (state.selectedId) {
      rootEl.appendChild(buildDetailView(ideas.find(i => i.id === state.selectedId), state, rerender));
    } else {
      rootEl.appendChild(buildListView(filtered, state, rerender));
    }
  }

  rerender();
}

function buildChipRail(state, statusValues, tagValues, rerender) {
  const wrap = document.createElement('div');
  wrap.className = 'ideas-chips chip-rail';

  const statusGroup = document.createElement('div');
  statusGroup.className = 'chip-group';
  statusGroup.append(makeLabel('Status'));
  for (const s of statusValues) {
    statusGroup.appendChild(makeChip(s || '(none)', state.statuses.includes(s), (ev) => {
      state.statuses = chipClickNext(ev, state.statuses, s);
      rerender();
    }));
  }
  wrap.appendChild(statusGroup);

  const tagGroup = document.createElement('div');
  tagGroup.className = 'chip-group';
  tagGroup.append(makeLabel('Tag'));
  for (const t of tagValues) {
    tagGroup.appendChild(makeChip(t, state.tags.includes(t), (ev) => {
      state.tags = chipClickNext(ev, state.tags, t);
      rerender();
    }));
  }
  wrap.appendChild(tagGroup);

  // Archived toggle (single chip, plain click)
  const archChip = makeChip('archived', state.includeArchived, () => {
    state.includeArchived = !state.includeArchived;
    rerender();
  });
  wrap.appendChild(archChip);

  return wrap;
}

function makeLabel(text) {
  const el = document.createElement('span');
  el.className = 'chip-group-label';
  el.textContent = text;
  return el;
}

function makeChip(text, active, onClick) {
  const el = document.createElement('button');
  el.type = 'button';
  el.className = 'chip' + (active ? ' is-active' : '');
  el.textContent = text;
  el.title = CHIP_CLICK_HINT;
  el.addEventListener('click', onClick);
  return el;
}

function buildListView(filtered, state, rerender) {
  const list = document.createElement('ul');
  list.className = 'ideas-list';
  for (const i of filtered) {
    const li = document.createElement('li');
    li.className = 'idea-row' + (i.archived ? ' is-archived' : '');
    li.innerHTML = `
      <span class="idea-id">${i.id}</span>
      <span class="idea-title">${escapeHtml(i.title || '')}</span>
      ${i.status ? `<span class="idea-status-pill" data-status="${escapeHtml(i.status)}">${escapeHtml(i.status)}</span>` : ''}
      <span class="idea-tags">${(i.tags || []).map(t => `<span class="tag">${escapeHtml(t)}</span>`).join('')}</span>
      <span class="idea-created">${formatRelative(i.created)}</span>
    `;
    li.addEventListener('click', () => { state.selectedId = i.id; rerender(); });
    list.appendChild(li);
  }
  return list;
}

function buildDetailView(idea, state, rerender) {
  const wrap = document.createElement('div');
  wrap.className = 'idea-detail';
  // Back button
  const back = document.createElement('button');
  back.textContent = '← back to list';
  back.addEventListener('click', () => { state.selectedId = null; rerender(); });
  wrap.appendChild(back);
  // Body — render markdown via the project's existing helper if present;
  // otherwise inject as <pre>. The issues screen already does this — match it.
  const body = document.createElement('div');
  body.className = 'idea-body';
  body.textContent = idea.body || '(no body)';
  wrap.appendChild(body);
  // Frontmatter sidebar with click-through links
  const side = document.createElement('aside');
  side.className = 'idea-sidebar';
  side.innerHTML = renderSidebar(idea);
  wrap.appendChild(side);
  return wrap;
}

function renderSidebar(idea) {
  const fields = [];
  if (idea.status) fields.push(`<div><strong>Status:</strong> ${escapeHtml(idea.status)}</div>`);
  if ((idea.tags || []).length) fields.push(`<div><strong>Tags:</strong> ${idea.tags.map(escapeHtml).join(', ')}</div>`);
  if ((idea.related_tasks || []).length) {
    fields.push(`<div><strong>Related tasks:</strong> ${idea.related_tasks.map(t =>
      `<a href="#/kanban/${escapeHtml(t)}">${escapeHtml(t)}</a>`).join(', ')}</div>`);
  }
  if ((idea.related_issues || []).length) {
    fields.push(`<div><strong>Related issues:</strong> ${idea.related_issues.map(i =>
      `<a href="#/issues/${escapeHtml(i)}">${escapeHtml(i)}</a>`).join(', ')}</div>`);
  }
  if ((idea.related_lessons || []).length) {
    fields.push(`<div><strong>Related lessons:</strong> ${idea.related_lessons.map(l =>
      `<a href="#/lessons/${escapeHtml(l)}">${escapeHtml(l)}</a>`).join(', ')}</div>`);
  }
  if (idea.promoted_to) {
    fields.push(`<div><strong>Promoted to:</strong> <a href="#/kanban/${escapeHtml(idea.promoted_to)}">${escapeHtml(idea.promoted_to)}</a></div>`);
  }
  if (idea.created) fields.push(`<div><strong>Created:</strong> ${escapeHtml(idea.created)}</div>`);
  return fields.join('');
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

function formatRelative(iso) {
  if (!iso) return '';
  const then = new Date(iso);
  const ms = Date.now() - then.getTime();
  const days = Math.floor(ms / 86400000);
  if (days <= 0) return 'today';
  if (days === 1) return 'yesterday';
  if (days < 30) return `${days}d ago`;
  return then.toISOString().slice(0, 10);
}
```

- [ ] **Step 5: Register the screen + add nav entry**

In `plugins/taskmaster/viewer/js/screens/index.js`, find where `issues` is registered and add `ideas` next to it. Match the existing registration convention (likely an import + a route map entry). Example:

```javascript
import { renderIdeasScreen } from './ideas.js';
// ... in the screen registry / route map ...
'ideas': renderIdeasScreen,
```

In `plugins/taskmaster/viewer/backlog-viewer.html`, find the nav element (search for "Issues" link) and add an "Ideas" link next to it:

```html
<a href="#/ideas" class="nav-link" data-screen="ideas">Ideas</a>
```

Place it adjacent to the Issues / Lessons links to maintain symmetry.

- [ ] **Step 6: Run viewer unit tests**

Run: `cd plugins/taskmaster/viewer/tests && npm test`
Expected: all green, including the new ideas-screen tests.

- [ ] **Step 7: Smoke-test the viewer locally**

Run the backlog server (whatever the existing dev command is — check `plugins/taskmaster/CHANGELOG.md` or top-of-`backlog_server.py` docstring), navigate to `/#/ideas`. Verify:
- Empty state renders cleanly when there are no ideas.
- Creating an idea via `backlog_idea_create` from a separate terminal causes the idea to appear after refresh.
- Chip filtering by status / tag works.
- Click an idea → detail view renders with sidebar links.
- Archived toggle reveals/hides archived entries.
- **Visual check:** no colored left rails on cards (per user preference).

If anything renders broken, fix inline. If a fix changes the public-ish surface (`applyIdeasFilters` signature), update the test.

- [ ] **Step 8: Commit**

```bash
git add plugins/taskmaster/viewer/js/screens/ideas.js \
        plugins/taskmaster/viewer/js/screens/index.js \
        plugins/taskmaster/viewer/backlog-viewer.html \
        plugins/taskmaster/viewer/tests/unit/ideas-screen.test.js
git commit -m "feat(taskmaster): viewer Ideas screen with status/tag chip filters

Mirror of the Issues screen: list/detail toggle, status pill, tag chips,
archived toggle, frontmatter sidebar with click-through links to related
tasks/issues/lessons. Uses the chipClickNext helper per L-001."
```

---

## Task 12: end-to-end smoke test — capture flow

**Files:**
- Modify: `plugins/taskmaster/tests/test_e2e_v3_smoke.py` (add an ideas section)

- [ ] **Step 1: Read the existing e2e smoke test for the issues flow**

Open `plugins/taskmaster/tests/test_e2e_v3_smoke.py` and find the issue section (search for `backlog_issue_create`). That's the pattern to mirror.

- [ ] **Step 2: Add an ideas e2e test**

Append at the end of the file (or in the analogous spot to where issues are tested):

```python
def test_e2e_ideas_full_lifecycle(tmp_path, monkeypatch):
    """Capture → list → archive → promote round-trip via the MCP wrappers."""
    import backlog_server
    bp = tmp_path / ".taskmaster" / "backlog.yaml"
    bp.parent.mkdir(parents=True)
    bp.write_text("schema_version: 3\nphases: []\n")
    monkeypatch.setattr(backlog_server, "_backlog_path", lambda: bp)

    # Sharp capture (path C — auto-log style)
    out1 = backlog_server.backlog_idea_create(
        title="Per-task spike budgets",
        body="track effort vs estimate",
        status="exploring",
        tags=["perf"],
        created_by="Claude",
    )
    assert "IDEA-001" in out1

    # Fuzzy capture (simulating end-session committing an <idea-candidate>)
    out2 = backlog_server.backlog_idea_create(
        title="Auto-tag from git diff",
        body="link ideas to recent files",
        status="candidate",
        created_by="Claude",
    )
    assert "IDEA-002" in out2

    # Listing returns both, newest first
    listed = backlog_server.backlog_idea_list()
    assert "IDEA-002" in listed
    assert "IDEA-001" in listed

    # Filter by status
    only_candidate = backlog_server.backlog_idea_list(status="candidate")
    assert "IDEA-002" in only_candidate
    assert "IDEA-001" not in only_candidate

    # Archive idea 1
    arch = backlog_server.backlog_idea_update(idea_id="IDEA-001", archived=True)
    assert "IDEA-001" in arch
    listed_default = backlog_server.backlog_idea_list()
    assert "IDEA-001" not in listed_default  # archived excluded by default
    listed_with_arch = backlog_server.backlog_idea_list(archived=True)
    assert "IDEA-001" in listed_with_arch
    assert "IDEA-002" in listed_with_arch

    # Promote idea 2
    prom = backlog_server.backlog_idea_update(idea_id="IDEA-002", promoted_to="T-XYZ", archived=True)
    assert "IDEA-002" in prom

    # Verify on disk
    idea2_text = (tmp_path / ".taskmaster" / "ideas" / "IDEA-002.md").read_text()
    assert "promoted_to: T-XYZ" in idea2_text
    assert "archived: true" in idea2_text

    # IDEAS.md index reflects archive marks
    idx = (tmp_path / ".taskmaster" / "ideas" / "IDEAS.md").read_text()
    assert "~~Per-task spike budgets~~" in idx
    assert "~~Auto-tag from git diff~~" in idx
```

- [ ] **Step 3: Run the e2e suite**

Run: `python -m pytest plugins/taskmaster/tests/test_e2e_v3_smoke.py -v`
Expected: all passing — existing tests unaffected, new test green.

Also run the full plugin test suite as a regression check:

Run: `python -m pytest plugins/taskmaster/tests/ -v`
Expected: all green.

- [ ] **Step 4: Commit**

```bash
git add plugins/taskmaster/tests/test_e2e_v3_smoke.py
git commit -m "test(taskmaster): e2e smoke for ideas full lifecycle"
```

---

## Self-Review

After all 12 tasks land:

**Spec coverage check:**
- ✅ On-disk shape (Task 1, 2)
- ✅ Frontmatter schema with required + optional fields (Task 2)
- ✅ IDEAS.md append-only index with archive strikethrough (Task 2, 3)
- ✅ ID allocation sequential `IDEA-NNN` (Task 1)
- ✅ Three MCP tools (create / list / update) (Task 5)
- ✅ `taskmaster:add-idea` skill (Task 6)
- ✅ `<idea-candidate>` schema in marker-format.md (Task 7)
- ✅ Mid-session capture heuristic (paths A/B/C) in start-session (Task 7)
- ✅ Lesson-candidate fix folded into start-session (Task 7)
- ✅ End-session scan + commit-direct + count report (Task 8)
- ✅ Router routing rows (Task 9)
- ✅ `/api/ideas` HTTP endpoint (Task 10)
- ✅ Viewer screen with chip filters + nav entry (Task 11)
- ✅ E2E lifecycle smoke (Task 12)

**Out-of-scope items (verify NOT addressed in any task):**
- ❌ Bulk operations
- ❌ User-tunable capture-mode setting
- ❌ Ideas dashboard widget
- ❌ Cross-project idea browsing
- ❌ Cutting existing MCP tool surface

**Type-consistency check:**
- `applyIdeasFilters` signature: `(ideas, { statuses, tags, includeArchived })` — used identically in test (Task 11 step 2) and screen (Task 11 step 4). ✅
- `write_idea` signature with kwargs — same kwargs passed in `_write_idea` call inside `backlog_idea_create` (Task 5). ✅
- `update_idea` signature `(bp, idea_id, **updates)` — matched in MCP wrapper (Task 5). ✅
- `_idea_index_line` is the single function that owns the IDEAS.md line format; used in both `write_idea` and `update_idea` (Task 2, 3). ✅

**Open questions resolved during plan-time:**
- IDEAS.md archived line uses strikethrough + `_(archived)_` suffix (resolved in Task 2 / `_idea_index_line`).
- `list_ideas(idea_id=...)` returns empty list on miss (consistent with how `_get_issue` handles missing — see Task 4). The MCP wrapper layer translates empty-list to `Idea not found:` (Task 5).
- start-session "Mid-session behavior" wording: full draft included in Task 7 step 4.

---

## Risks / things to watch

- **Skill-prompt size.** Adding the mid-session behavior section to start-session enlarges the always-loaded prompt. Keep wording compact (the draft in Task 7 is ~600 words — acceptable, but resist later expansion).
- **`<idea-candidate>` regex parsing.** End-session's tag scan needs to be tolerant of attribute order, missing optionals, and HTML-escaped body content. Test with a few realistic tag examples in Task 8 if any of them cause issues during smoke testing.
- **Existing repo split context.** The user's project memory notes a pending taskmaster repo split (`gruku/taskmaster` standalone). New code lives in the same files as today; nothing here makes the future split harder.
- **Viewer dev-server smoke test.** Task 11 step 7 is a manual local check — if the implementer is running headlessly, they should mark this step as "deferred to user verification" and surface that explicitly in their handoff.
