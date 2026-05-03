# Lesson Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `taskmaster:lesson` — write/reinforce/promote project-scoped lessons with mid-session `<lesson-candidate>` XML markers, end-session sweep, and full auto-extraction write flow.

**Architecture:** Backend additions in `taskmaster_v3.py` for lesson candidates (defer/read/clear/scan), 4 new MCP tools in `backlog_server.py`, new skill directory at `plugins/taskmaster/skills/lesson/` (SKILL.md + 5 reference docs + 1 template), retrofits to end-session and handover skills, plus tests + dogfood.

**Tech Stack:** Python 3.11+, FastMCP, pytest, YAML frontmatter parsing.

---

## Spec & Reference Material

- **Spec:** `docs/superpowers/specs/2026-05-03-lesson-skill-design.md`
- **Reference plan (proven template):** `docs/superpowers/plans/2026-05-02-v3-skills-002-handover.md`
- **Existing backend:** `plugins/taskmaster/taskmaster_v3.py` lines 862–1200 (lesson functions), lines 505–646 (handover write + supersession reference pattern).
- **Existing MCP tools:** `plugins/taskmaster/backlog_server.py` lines 1389–1590 (handovers), 1786–2204 (lessons).
- **Existing skill files to mirror:** `plugins/taskmaster/skills/handover/SKILL.md`, `references/*.md`, `templates/*.md`.
- **Existing test patterns:** `plugins/taskmaster/tests/test_v3_handover.py`, `plugins/taskmaster/tests/test_handover_skill_lint.py`.

## Spec coverage cross-check

| Spec section | Mapped task(s) |
|---|---|
| §1 Purpose | Skill body (Task 6) — preamble |
| §2 Architecture overview | Skill body (Task 6) — preamble |
| §3.1 Tag schema | Task 7a (`marker-format.md`) |
| §3.2 Tag conventions | Task 7a (`marker-format.md`); Task 2 (regex) |
| §3.3 When Claude emits | Task 7a (`marker-format.md`) |
| §3.4 Candidate-discovery scans | Task 6 (SKILL.md flow); Task 9 (end-session retrofit) |
| §3.5 Compaction handling | Task 7a; Task 7e (`session-retro.md`) |
| §3.6 Session-level scope | Task 7e (`session-retro.md`); Task 4 (handover flag wiring); Task 9 (buffer logic) |
| §3.7 Cross-session search | Task 2 (`scan_transcripts_for_candidates`); Task 4 (`backlog_lesson_candidates_scan`) |
| §4.1 Trigger phrases | Task 5 (frontmatter); Task 11 (lint test) |
| §4.2 Five entry points | Task 6 (SKILL.md flow) |
| §4.3 Write subflow | Task 6 (SKILL.md flow); Task 7b (`auto-extraction.md`) |
| §4.4 Reinforce immediate | Task 7c (`reinforce-flows.md`) |
| §4.5 Reinforce sweep | Task 7c (`reinforce-flows.md`); Task 9 (end-session) |
| §5 End-session retrofit | Task 9 |
| §6 Promotion UX | Task 7d (`promotion-decay.md`); Task 9 (sweep step 7) |
| §7 Decay UX | Task 7d (`promotion-decay.md`); Task 9 (decay info line) |
| §8.1 Backend additions | Tasks 1, 2, 3 |
| §8.2 MCP tools | Task 4 |
| §8.3 Existing tools used as-is | Task 6 (SKILL.md references them) |
| §9 Skill file structure | Tasks 5, 6, 7, 8 |
| §10 Lesson frontmatter | Task 8 (`lesson-body.md` template) |
| §11 Out of scope / future | Task 7e (`session-retro.md` — points to future) |
| §12 Trade-offs / rejected | Task 7a (`marker-format.md` — explains XML-not-tool) |
| §13 Test coverage targets | Tasks 1, 2, 3, 4 (backend/MCP), Task 11 (skill lint), Task 9 (retrofit lint) |
| §14 Dependencies | Implicit; task 12 dogfood notes the v3-skills-006 hook gap |

No spec sections unmapped.

---

## Task 1: Backend — `lesson_candidates_path` / `_read` / `_defer` / `_clear`

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py` (add after `sync_lesson_index` near line 1200)
- Test: `plugins/taskmaster/tests/test_v3_lesson_candidates.py` (new file)

The deferred-candidates store is a single markdown file `_candidates.md` inside the lesson directory. Format per spec §8.1: a markdown header + a fenced YAML block with a `candidates:` list. The file is auto-managed; the index of an entry is its 0-based position in the list.

- [ ] **Step 1: Write the failing test**

Create `plugins/taskmaster/tests/test_v3_lesson_candidates.py`:

```python
"""Tests for v3 lesson-candidate persistence (defer/read/clear)."""
from pathlib import Path

import pytest
import yaml

from taskmaster_v3 import (
    LESSON_CANDIDATE_KINDS,
    LESSON_CANDIDATE_SCOPES,
    lesson_candidates_clear,
    lesson_candidates_defer,
    lesson_candidates_path,
    lesson_candidates_read,
)


def _make_backlog(tmp_path: Path) -> Path:
    bp = tmp_path / "backlog.yaml"
    bp.write_text(yaml.safe_dump({"meta": {"updated": "2026-05-03"}, "epics": []}))
    (tmp_path / "lessons").mkdir()
    return bp


def test_candidate_constants_match_spec():
    assert set(LESSON_CANDIDATE_KINDS) == {"pattern", "anti-pattern", "gotcha"}
    assert set(LESSON_CANDIDATE_SCOPES) == {"point", "session"}


def test_candidates_path_resolves_under_lessons_dir(tmp_path):
    bp = _make_backlog(tmp_path)
    p = lesson_candidates_path(bp)
    assert p == bp.parent / "lessons" / "_candidates.md"


def test_candidates_read_returns_empty_when_file_missing(tmp_path):
    bp = _make_backlog(tmp_path)
    assert lesson_candidates_read(bp) == []


def test_defer_creates_file_and_returns_index(tmp_path):
    bp = _make_backlog(tmp_path)
    idx = lesson_candidates_defer(
        bp,
        title="useEffect reads useLocation().state without active-tab guard",
        kind="gotcha",
        topic="multi-tab fanout",
        scope="point",
        context="session 2026-05-03; commit cb6927c0",
    )
    assert idx == 0
    p = lesson_candidates_path(bp)
    assert p.exists()
    raw = p.read_text(encoding="utf-8")
    assert "# Lesson Candidates" in raw
    assert "```yaml" in raw
    assert "useEffect reads useLocation" in raw


def test_defer_appends_subsequent_entries(tmp_path):
    bp = _make_backlog(tmp_path)
    a = lesson_candidates_defer(bp, title="first")
    b = lesson_candidates_defer(bp, title="second", kind="pattern")
    c = lesson_candidates_defer(bp, title="third", scope="session")
    assert (a, b, c) == (0, 1, 2)
    items = lesson_candidates_read(bp)
    assert [i["title"] for i in items] == ["first", "second", "third"]
    assert items[1]["kind"] == "pattern"
    assert items[2]["scope"] == "session"


def test_defer_round_trip_preserves_fields(tmp_path):
    bp = _make_backlog(tmp_path)
    lesson_candidates_defer(
        bp,
        title="round-trip me",
        kind="anti-pattern",
        topic="bare exception",
        scope="point",
        context="discovered in PR review",
    )
    items = lesson_candidates_read(bp)
    assert items[0]["title"] == "round-trip me"
    assert items[0]["kind"] == "anti-pattern"
    assert items[0]["topic"] == "bare exception"
    assert items[0]["scope"] == "point"
    assert items[0]["context"] == "discovered in PR review"
    assert "deferred_at" in items[0]


def test_defer_rejects_invalid_kind(tmp_path):
    bp = _make_backlog(tmp_path)
    with pytest.raises(ValueError, match="kind"):
        lesson_candidates_defer(bp, title="bad", kind="not-a-kind")


def test_defer_rejects_invalid_scope(tmp_path):
    bp = _make_backlog(tmp_path)
    with pytest.raises(ValueError, match="scope"):
        lesson_candidates_defer(bp, title="bad", scope="forever")


def test_defer_rejects_empty_title(tmp_path):
    bp = _make_backlog(tmp_path)
    with pytest.raises(ValueError, match="title"):
        lesson_candidates_defer(bp, title="   ")


def test_clear_removes_specified_indices(tmp_path):
    bp = _make_backlog(tmp_path)
    lesson_candidates_defer(bp, title="a")
    lesson_candidates_defer(bp, title="b")
    lesson_candidates_defer(bp, title="c")
    n = lesson_candidates_clear(bp, indices=[0, 2])
    assert n == 2
    remaining = lesson_candidates_read(bp)
    assert [i["title"] for i in remaining] == ["b"]


def test_clear_tolerates_out_of_range_indices(tmp_path):
    bp = _make_backlog(tmp_path)
    lesson_candidates_defer(bp, title="only one")
    n = lesson_candidates_clear(bp, indices=[0, 5, 99])
    assert n == 1
    assert lesson_candidates_read(bp) == []


def test_clear_on_empty_file_is_noop(tmp_path):
    bp = _make_backlog(tmp_path)
    n = lesson_candidates_clear(bp, indices=[0])
    assert n == 0
    assert lesson_candidates_read(bp) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_v3_lesson_candidates.py -v`
Expected: FAIL — none of the new symbols are defined yet.

- [ ] **Step 3: Add constants and functions to `taskmaster_v3.py`**

Append to `plugins/taskmaster/taskmaster_v3.py` directly after `sync_lesson_index` (around line 1200, before the `# ── Auto mode (state machine) ──` divider):

```python
# ── Lesson candidates (deferred + scanning) ───────────────────

LESSON_CANDIDATE_KINDS = ("pattern", "anti-pattern", "gotcha")
LESSON_CANDIDATE_SCOPES = ("point", "session")

_LESSON_CANDIDATES_HEADER = (
    "# Lesson Candidates (deferred)\n\n"
    "> Auto-managed by `taskmaster:lesson`. "
    "Edit by hand only if the file is corrupt.\n\n"
)
_LESSON_CANDIDATES_FENCE_OPEN = "```yaml\n"
_LESSON_CANDIDATES_FENCE_CLOSE = "```\n"


def lesson_candidates_path(backlog_path: Path) -> Path:
    """Path to the `_candidates.md` file under the lessons directory."""
    return backlog_path.parent / "lessons" / "_candidates.md"


def lesson_candidates_read(backlog_path: Path) -> list[dict[str, Any]]:
    """Return the deferred candidates list, or [] if the file is missing/empty.

    The file format is a markdown header followed by a fenced YAML block with
    a `candidates:` list. Anything outside the fenced block is ignored.
    Tolerates a missing or malformed file by returning [].
    """
    p = lesson_candidates_path(backlog_path)
    if not p.exists():
        return []
    raw = p.read_text(encoding="utf-8")
    # Extract the YAML fenced block.
    m = re.search(r"```yaml\n(.*?)```", raw, re.DOTALL)
    if not m:
        return []
    try:
        doc = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return []
    items = doc.get("candidates") if isinstance(doc, dict) else None
    if not isinstance(items, list):
        return []
    return [i for i in items if isinstance(i, dict)]


def _write_lesson_candidates(backlog_path: Path, items: list[dict[str, Any]]) -> None:
    """Render the candidates list back to disk as the canonical markdown+YAML file."""
    p = lesson_candidates_path(backlog_path)
    if not items:
        # Drop the file entirely when empty — keeps the lessons/ directory clean.
        if p.exists():
            p.unlink()
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    yaml_text = yaml.safe_dump(
        {"candidates": items}, default_flow_style=False, sort_keys=False, allow_unicode=True
    )
    body = (
        _LESSON_CANDIDATES_HEADER
        + _LESSON_CANDIDATES_FENCE_OPEN
        + yaml_text
        + _LESSON_CANDIDATES_FENCE_CLOSE
    )
    atomic_write(p, body)


def lesson_candidates_defer(
    backlog_path: Path,
    *,
    title: str,
    kind: str = "",
    topic: str = "",
    scope: str = "point",
    context: str = "",
) -> int:
    """Append a new candidate. Returns the new entry's 0-based list index.

    Validates kind (if provided) and scope. Empty `kind` is allowed — it lets
    the user defer a candidate before classifying it.
    """
    if not title or not title.strip():
        raise ValueError("candidate title is required")
    if kind and kind not in LESSON_CANDIDATE_KINDS:
        raise ValueError(
            f"kind must be one of {LESSON_CANDIDATE_KINDS}, got {kind!r}"
        )
    if scope not in LESSON_CANDIDATE_SCOPES:
        raise ValueError(
            f"scope must be one of {LESSON_CANDIDATE_SCOPES}, got {scope!r}"
        )

    items = lesson_candidates_read(backlog_path)
    entry: dict[str, Any] = {
        "title": title.strip(),
        "kind": kind,
        "topic": topic,
        "scope": scope,
        "context": context,
        "deferred_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M"),
    }
    items.append(entry)
    _write_lesson_candidates(backlog_path, items)
    return len(items) - 1


def lesson_candidates_clear(backlog_path: Path, *, indices: list[int]) -> int:
    """Drop the entries at `indices` (0-based). Returns the number actually removed.

    Out-of-range indices are silently ignored. Re-writes the file with the
    remaining entries; deletes the file if the list is now empty.
    """
    items = lesson_candidates_read(backlog_path)
    if not items:
        return 0
    drop = {i for i in indices if 0 <= i < len(items)}
    if not drop:
        return 0
    remaining = [it for idx, it in enumerate(items) if idx not in drop]
    _write_lesson_candidates(backlog_path, remaining)
    return len(drop)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest plugins/taskmaster/tests/test_v3_lesson_candidates.py -v`
Expected: all eleven tests PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_v3_lesson_candidates.py
git commit -m "feat(taskmaster): lesson_candidates defer/read/clear with markdown+YAML store (v3-skills-003)"
```

---

## Task 2: Backend — `scan_transcripts_for_candidates`

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py` (add directly after `lesson_candidates_clear`)
- Test: `plugins/taskmaster/tests/test_v3_lesson_candidates.py` (append)

`scan_transcripts_for_candidates(project_dir, days=7, kind_filter="")` greps `.jsonl` transcript files under a Claude project directory and returns matched `<lesson-candidate ...>...</lesson-candidate>` blocks with traceability (source filename + line number). The opening anchor regex per spec §3.2 is the literal string `<lesson-candidate ` (one trailing space, never variant) so the regex is exact.

- [ ] **Step 1: Write the failing test**

Append to `plugins/taskmaster/tests/test_v3_lesson_candidates.py`:

```python
import json as _json
from datetime import datetime, timedelta, timezone

from taskmaster_v3 import scan_transcripts_for_candidates


def _write_jsonl(project_dir: Path, name: str, lines: list[dict]) -> Path:
    p = project_dir / name
    p.write_text(
        "\n".join(_json.dumps(li) for li in lines) + "\n", encoding="utf-8"
    )
    return p


def test_scan_returns_empty_when_no_jsonl(tmp_path):
    out = scan_transcripts_for_candidates(tmp_path, days=7)
    assert out == []


def test_scan_finds_inline_candidate_in_jsonl(tmp_path):
    project_dir = tmp_path / "projects" / "my-project"
    project_dir.mkdir(parents=True)
    _write_jsonl(
        project_dir,
        "session-aaa.jsonl",
        [
            {"role": "assistant", "content": "Working on auth..."},
            {
                "role": "assistant",
                "content": (
                    'I noticed a recurring issue.\n'
                    '<lesson-candidate kind="gotcha" topic="auth-session">\n'
                    'auth/session.ts must be read before edit; legacy globals leak.\n'
                    '</lesson-candidate>\nMoving on.'
                ),
            },
        ],
    )
    out = scan_transcripts_for_candidates(project_dir, days=7)
    assert len(out) == 1
    item = out[0]
    assert item["kind"] == "gotcha"
    assert item["topic"] == "auth-session"
    assert "auth/session.ts must be read" in item["body"]
    assert item["source_file"].endswith("session-aaa.jsonl")
    assert item["source_line"] >= 1


def test_scan_filters_by_kind(tmp_path):
    project_dir = tmp_path / "p"
    project_dir.mkdir()
    _write_jsonl(
        project_dir,
        "s1.jsonl",
        [
            {"role": "assistant", "content": '<lesson-candidate kind="gotcha">A</lesson-candidate>'},
            {"role": "assistant", "content": '<lesson-candidate kind="pattern">B</lesson-candidate>'},
        ],
    )
    out = scan_transcripts_for_candidates(project_dir, kind_filter="pattern")
    assert len(out) == 1
    assert out[0]["body"].strip() == "B"


def test_scan_respects_days_window(tmp_path):
    project_dir = tmp_path / "p"
    project_dir.mkdir()
    old = _write_jsonl(project_dir, "old.jsonl", [
        {"role": "assistant", "content": '<lesson-candidate>old</lesson-candidate>'}
    ])
    new = _write_jsonl(project_dir, "new.jsonl", [
        {"role": "assistant", "content": '<lesson-candidate>new</lesson-candidate>'}
    ])
    # Push old.jsonl mtime to 30 days ago.
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).timestamp()
    import os as _os
    _os.utime(old, (cutoff, cutoff))

    out = scan_transcripts_for_candidates(project_dir, days=7)
    titles = [i["body"].strip() for i in out]
    assert "new" in titles and "old" not in titles


def test_scan_skips_files_outside_jsonl_extension(tmp_path):
    project_dir = tmp_path / "p"
    project_dir.mkdir()
    (project_dir / "notes.txt").write_text(
        '<lesson-candidate>ignored</lesson-candidate>', encoding="utf-8"
    )
    assert scan_transcripts_for_candidates(project_dir, days=7) == []


def test_scan_handles_malformed_jsonl_lines(tmp_path):
    project_dir = tmp_path / "p"
    project_dir.mkdir()
    p = project_dir / "broken.jsonl"
    p.write_text(
        "not-json-at-all\n"
        + _json.dumps({"role": "assistant",
                       "content": '<lesson-candidate>survivor</lesson-candidate>'})
        + "\n",
        encoding="utf-8",
    )
    out = scan_transcripts_for_candidates(project_dir, days=7)
    assert len(out) == 1
    assert "survivor" in out[0]["body"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest plugins/taskmaster/tests/test_v3_lesson_candidates.py::test_scan_finds_inline_candidate_in_jsonl -v`
Expected: FAIL — `scan_transcripts_for_candidates` is undefined.

- [ ] **Step 3: Add the scanner**

Append to `plugins/taskmaster/taskmaster_v3.py` directly after `lesson_candidates_clear`:

```python
# Stable opening anchor per spec §3.2 — `<lesson-candidate ` (trailing space)
# with double-quoted attrs. Multiline body, captured up to the matching close.
_LESSON_CANDIDATE_RE = re.compile(
    r"<lesson-candidate"                    # opening tag (no trailing space yet)
    r"(?P<attrs>(?:\s+\w+=\"[^\"]*\")*)"   # 0+ key="value" attribute pairs
    r"\s*>"                                  # > terminator (allow attrless)
    r"(?P<body>.*?)"                         # body, non-greedy
    r"</lesson-candidate>",                  # closing tag
    re.DOTALL,
)

_LESSON_CANDIDATE_ATTR_RE = re.compile(r'(\w+)="([^"]*)"')


def _parse_candidate_attrs(attr_text: str) -> dict[str, str]:
    return {k: v for k, v in _LESSON_CANDIDATE_ATTR_RE.findall(attr_text or "")}


def scan_transcripts_for_candidates(
    project_dir: Path,
    *,
    days: int = 7,
    kind_filter: str = "",
) -> list[dict[str, Any]]:
    """Grep all `*.jsonl` files in `project_dir` for `<lesson-candidate>` tags.

    Filters:
      - `days`: only files whose mtime is within the last N days.
      - `kind_filter`: only matches whose `kind` attr equals this string.

    Returns a list of dicts with keys: `kind`, `topic`, `scope`, `body`,
    `source_file`, `source_line`. Tolerates malformed JSONL lines (skipped).
    """
    if not project_dir.exists() or not project_dir.is_dir():
        return []
    cutoff_ts = (datetime.now(timezone.utc) - timedelta(days=days)).timestamp()
    out: list[dict[str, Any]] = []
    for jsonl in sorted(project_dir.glob("*.jsonl")):
        try:
            if jsonl.stat().st_mtime < cutoff_ts:
                continue
            text = jsonl.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        line_starts = [0]
        for i, ch in enumerate(text):
            if ch == "\n":
                line_starts.append(i + 1)
        for m in _LESSON_CANDIDATE_RE.finditer(text):
            attrs = _parse_candidate_attrs(m.group("attrs"))
            kind = attrs.get("kind", "")
            if kind_filter and kind != kind_filter:
                continue
            # Find the line number containing the start of this match.
            start = m.start()
            line_no = 1
            for ls in line_starts:
                if ls > start:
                    break
                line_no = line_starts.index(ls) + 1
            out.append({
                "kind": kind,
                "topic": attrs.get("topic", ""),
                "scope": attrs.get("scope", "point"),
                "body": m.group("body").strip(),
                "source_file": str(jsonl),
                "source_line": line_no,
            })
    return out
```

You will also need `from datetime import timedelta` — confirm `timedelta` is in the module-top imports. The current top-of-file import is `from datetime import date, datetime, timezone` (line 18). Update it to:

```python
from datetime import date, datetime, timedelta, timezone
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest plugins/taskmaster/tests/test_v3_lesson_candidates.py -v`
Expected: all six new tests PASS (plus the eleven from Task 1).

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_v3_lesson_candidates.py
git commit -m "feat(taskmaster): scan_transcripts_for_candidates regex+filters (v3-skills-003)"
```

---

## Task 3: Backend — `apply_handover_review_flag`

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py` (add directly after `apply_supersession`, around line 646)
- Test: `plugins/taskmaster/tests/test_v3_lesson_candidates.py` (append)

`apply_handover_review_flag(backlog_path, handover_id, review_reason)` mirrors `apply_supersession`: idempotent, raises `FileNotFoundError` if the handover is missing, and stamps `flag_for_review: true` + `review_reason: <text>` into the existing handover's frontmatter without touching the body. Used by the lesson skill's `scope="session"` flow when the user later wants a retro analysis on a flagged handover (spec §3.6, §4.3 step 6).

- [ ] **Step 1: Write the failing test**

Append to `plugins/taskmaster/tests/test_v3_lesson_candidates.py`:

```python
import pytest as _pytest

from taskmaster_v3 import (
    apply_handover_review_flag,
    read_handover,
    write_handover,
)


def test_apply_handover_review_flag_sets_fields(tmp_path):
    bp = _make_backlog(tmp_path)
    (tmp_path / "handovers").mkdir(exist_ok=True)
    hid, _ = write_handover(bp, tldr="some session", session_kind="end-of-day")
    apply_handover_review_flag(bp, handover_id=hid, review_reason="multi-tab fanout retro")
    fm, body = read_handover(bp, hid)
    assert fm["flag_for_review"] is True
    assert fm["review_reason"] == "multi-tab fanout retro"
    # Body must be unchanged.
    assert "SUPERSEDED" not in body


def test_apply_handover_review_flag_idempotent(tmp_path):
    bp = _make_backlog(tmp_path)
    (tmp_path / "handovers").mkdir(exist_ok=True)
    hid, _ = write_handover(bp, tldr="s", session_kind="end-of-day")
    apply_handover_review_flag(bp, handover_id=hid, review_reason="first")
    apply_handover_review_flag(bp, handover_id=hid, review_reason="updated")
    fm, _ = read_handover(bp, hid)
    assert fm["flag_for_review"] is True
    assert fm["review_reason"] == "updated"


def test_apply_handover_review_flag_raises_for_missing(tmp_path):
    bp = _make_backlog(tmp_path)
    (tmp_path / "handovers").mkdir(exist_ok=True)
    with _pytest.raises(FileNotFoundError):
        apply_handover_review_flag(
            bp, handover_id="2099-01-01-nope", review_reason="x"
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest plugins/taskmaster/tests/test_v3_lesson_candidates.py::test_apply_handover_review_flag_sets_fields -v`
Expected: FAIL — `apply_handover_review_flag` is undefined.

- [ ] **Step 3: Add the helper**

In `plugins/taskmaster/taskmaster_v3.py`, add directly after `apply_supersession` (the helper finishes around line 646, just before `# Fields kept in the backlog.yaml ...`):

```python
def apply_handover_review_flag(
    backlog_path: Path,
    *,
    handover_id: str,
    review_reason: str,
) -> Path:
    """Stamp `flag_for_review: true` + `review_reason` onto an existing handover.

    Used by `taskmaster:lesson` when a `<lesson-candidate scope="session">` is
    promoted: the active handover for the session gets flagged so a future
    invocation can retro-extract lessons against it. Idempotent — re-applying
    overwrites the `review_reason` and leaves the body untouched. Raises
    FileNotFoundError if the handover doesn't exist on disk.
    """
    target = handover_path(backlog_path, handover_id)
    if not target.exists():
        raise FileNotFoundError(handover_id)
    fm, body = read_handover(backlog_path, handover_id)
    fm["flag_for_review"] = True
    fm["review_reason"] = review_reason or ""
    write_task_file(target, fm, body)
    return target
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest plugins/taskmaster/tests/test_v3_lesson_candidates.py -v`
Expected: all three new tests PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_v3_lesson_candidates.py
git commit -m "feat(taskmaster): apply_handover_review_flag helper for session-scope candidates (v3-skills-003)"
```

---

## Task 4: MCP — 4 lesson-candidate tools + handover review-flag wiring

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py` (top-level imports + new tools after `backlog_lesson_digest`)
- Modify: `plugins/taskmaster/backlog_server.py:1390` (`backlog_handover_create` — add `flag_for_review` + `review_reason` kwargs)
- Test: `plugins/taskmaster/tests/test_v3_lesson_candidates.py` (append)

Four new tools sibling-consistent with existing handover/lesson tools (error format `f"Error: <thing> not found: {exc}."`):

- `backlog_lesson_candidate_defer(title, kind="", topic="", scope="point", context="") -> str`
- `backlog_lesson_candidates_list() -> str`
- `backlog_lesson_candidate_drop(index: int) -> str`
- `backlog_lesson_candidates_scan(days=7, kind="") -> str`

Plus `backlog_handover_create` gains `flag_for_review: bool = False, review_reason: str = ""` — only added to frontmatter when truthy.

- [ ] **Step 1: Write the failing test**

Append to `plugins/taskmaster/tests/test_v3_lesson_candidates.py`:

```python
import sys as _sys
from pathlib import Path as _Path

PLUGIN_ROOT = _Path(__file__).resolve().parents[1]
_sys.path.insert(0, str(PLUGIN_ROOT))

import backlog_server  # noqa: E402


def _set_backlog_root(monkeypatch, bp: Path):
    monkeypatch.setattr(backlog_server, "ROOT", bp.parent)
    monkeypatch.setattr(backlog_server, "_backlog_path", lambda: bp)


def test_mcp_candidate_defer_returns_index_and_title(tmp_path, monkeypatch):
    bp = _make_backlog(tmp_path)
    _set_backlog_root(monkeypatch, bp)
    out = backlog_server.backlog_lesson_candidate_defer(
        title="multi-tab fanout: useEffect reads useLocation()",
        kind="gotcha",
        topic="multi-tab fanout",
    )
    assert "Deferred candidate #0" in out
    assert "multi-tab fanout" in out


def test_mcp_candidates_list_renders_bullets(tmp_path, monkeypatch):
    bp = _make_backlog(tmp_path)
    _set_backlog_root(monkeypatch, bp)
    backlog_server.backlog_lesson_candidate_defer(title="A", kind="gotcha")
    backlog_server.backlog_lesson_candidate_defer(title="B", kind="pattern")
    out = backlog_server.backlog_lesson_candidates_list()
    assert "- [#0]" in out and "A" in out
    assert "- [#1]" in out and "B" in out


def test_mcp_candidates_list_empty(tmp_path, monkeypatch):
    bp = _make_backlog(tmp_path)
    _set_backlog_root(monkeypatch, bp)
    out = backlog_server.backlog_lesson_candidates_list()
    assert "No deferred candidates" in out


def test_mcp_candidate_drop_removes_entry(tmp_path, monkeypatch):
    bp = _make_backlog(tmp_path)
    _set_backlog_root(monkeypatch, bp)
    backlog_server.backlog_lesson_candidate_defer(title="A")
    backlog_server.backlog_lesson_candidate_defer(title="B")
    out = backlog_server.backlog_lesson_candidate_drop(index=0)
    assert "Dropped candidate #0" in out
    remaining = lesson_candidates_read(bp)
    assert [i["title"] for i in remaining] == ["B"]


def test_mcp_candidate_drop_out_of_range(tmp_path, monkeypatch):
    bp = _make_backlog(tmp_path)
    _set_backlog_root(monkeypatch, bp)
    out = backlog_server.backlog_lesson_candidate_drop(index=99)
    assert "Error" in out and "99" in out


def test_mcp_candidates_scan_groups_by_session(tmp_path, monkeypatch):
    bp = _make_backlog(tmp_path)
    _set_backlog_root(monkeypatch, bp)
    # Stage a fake project transcripts dir and point the scan at it via env override.
    project_dir = tmp_path / "projects" / "demo"
    project_dir.mkdir(parents=True)
    (project_dir / "session-1.jsonl").write_text(
        '{"role":"assistant","content":"<lesson-candidate kind=\\"gotcha\\">x</lesson-candidate>"}\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("TASKMASTER_TRANSCRIPTS_DIR", str(project_dir))
    out = backlog_server.backlog_lesson_candidates_scan(days=7)
    assert "session-1.jsonl" in out
    assert "gotcha" in out


def test_mcp_handover_create_with_review_flag(tmp_path, monkeypatch):
    bp = _make_backlog(tmp_path)
    _set_backlog_root(monkeypatch, bp)
    out = backlog_server.backlog_handover_create(
        tldr="flag-me",
        session_kind="end-of-day",
        flag_for_review=True,
        review_reason="multi-tab retro",
    )
    hid = out.splitlines()[0].split(": ", 1)[1].strip()
    fm, _ = read_handover(bp, hid)
    assert fm["flag_for_review"] is True
    assert fm["review_reason"] == "multi-tab retro"


def test_mcp_handover_create_without_review_flag_omits_fields(tmp_path, monkeypatch):
    bp = _make_backlog(tmp_path)
    _set_backlog_root(monkeypatch, bp)
    out = backlog_server.backlog_handover_create(
        tldr="no-flag", session_kind="end-of-day",
    )
    hid = out.splitlines()[0].split(": ", 1)[1].strip()
    fm, _ = read_handover(bp, hid)
    assert "flag_for_review" not in fm
    assert "review_reason" not in fm
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest plugins/taskmaster/tests/test_v3_lesson_candidates.py -v`
Expected: FAIL — none of the four MCP tools exist; `backlog_handover_create` rejects the new kwargs.

- [ ] **Step 3: Update top-of-file imports in `backlog_server.py`**

In `plugins/taskmaster/backlog_server.py`, find the `from taskmaster_v3 import (` block (around line 51) and add these names alongside the existing imports:

```python
    LESSON_CANDIDATE_KINDS,
    LESSON_CANDIDATE_SCOPES,
    apply_handover_review_flag as _apply_handover_review_flag,
    lesson_candidates_clear as _lesson_candidates_clear,
    lesson_candidates_defer as _lesson_candidates_defer,
    lesson_candidates_read as _lesson_candidates_read,
    scan_transcripts_for_candidates as _scan_transcripts_for_candidates,
```

- [ ] **Step 4: Add `flag_for_review` + `review_reason` to `backlog_handover_create`**

In `plugins/taskmaster/backlog_server.py:1390`, update the signature and the frontmatter assembly. Replace the existing `backlog_handover_create` definition with:

```python
@mcp.tool()
def backlog_handover_create(
    tldr: str,
    next_action: str = "",
    body: str = "",
    task_ids: list[str] | None = None,
    session_kind: str = "end-of-day",
    context_size_at_write: str = "",
    supersedes: str = "",
    branch: str = "",
    tip_commit: str = "",
    flag_for_review: bool = False,
    review_reason: str = "",
) -> str:
    """Write a session handover — committed markdown artifact for cross-session
    continuity.

    (existing docstring preserved — append:)

    Args:
        ...
        flag_for_review: When true, the handover frontmatter records
            `flag_for_review: true` + `review_reason`. Used by
            `taskmaster:lesson` to mark a session for later retro-extraction
            (scope="session" candidates). Omit (or leave false) to skip.
        review_reason: One-line annotation explaining why the session was
            flagged. Only written to frontmatter when `flag_for_review` is true.
    """
    bp = _backlog_path()
    if not bp.exists():
        return f"Error: no backlog found at {bp}. Run `backlog_init` first."
    try:
        hid, target = _write_handover(
            bp,
            tldr=tldr,
            next_action=next_action,
            body=body,
            task_ids=task_ids or [],
            session_kind=session_kind,
            context_size_at_write=context_size_at_write or None,
            supersedes=supersedes or None,
            branch=branch or None,
            tip_commit=tip_commit or None,
        )
    except ValueError as exc:
        return f"Error: {exc}"

    superseded_warning = None
    if supersedes:
        try:
            _apply_supersession(bp, old_id=supersedes, new_id=hid)
        except FileNotFoundError:
            superseded_warning = (
                f"WARNING: supersedes={supersedes} not found on disk; old "
                f"handover not updated."
            )

    if flag_for_review:
        try:
            _apply_handover_review_flag(
                bp, handover_id=hid, review_reason=review_reason or ""
            )
        except FileNotFoundError as exc:
            return f"Error: handover not found: {exc}."

    data = _load()
    _sync_handover_index(data, bp)
    _save(data)

    lines = [
        f"Handover written: {hid}",
        f"- File: {target.relative_to(ROOT)}",
        f"- Index entries: {len(data.get('handovers') or [])}",
    ]
    if supersedes and not superseded_warning:
        lines.append(f"- Superseded: {supersedes}")
    if superseded_warning:
        lines.append(f"- {superseded_warning}")
    if flag_for_review:
        lines.append(f"- Flagged for review: {review_reason}")
    return "\n".join(lines)
```

- [ ] **Step 5: Add the four candidate MCP tools**

Insert directly after `backlog_lesson_digest` (around line 1993) in `backlog_server.py`. Place the helper that resolves the project transcript directory at the top of the new section so all four tools can use it.

```python
def _transcripts_dir() -> Path:
    """Resolve the Claude project transcripts directory.

    Override with `TASKMASTER_TRANSCRIPTS_DIR` for tests. Default is
    `~/.claude/projects/<encoded-cwd>/` per Claude Code's storage layout.
    """
    override = os.environ.get("TASKMASTER_TRANSCRIPTS_DIR")
    if override:
        return Path(override)
    home = Path.home() / ".claude" / "projects"
    encoded = str(ROOT.resolve()).replace("\\", "-").replace("/", "-").replace(":", "")
    return home / encoded


@mcp.tool()
def backlog_lesson_candidate_defer(
    title: str,
    kind: str = "",
    topic: str = "",
    scope: str = "point",
    context: str = "",
) -> str:
    """Defer a lesson candidate to `.taskmaster/lessons/_candidates.md`.

    Use mid-session when Claude wants to flag a candidate but the user isn't
    ready to write a full lesson. End-session sweep reads this file.

    Args:
        title: One-line summary. Required.
        kind: pattern | anti-pattern | gotcha. Optional — leave empty to
            classify later during the sweep.
        topic: One-word handle for grouping in the sweep UI.
        scope: 'point' (default) or 'session' (flags the active handover for
            retro-extraction; see references/session-retro.md).
        context: Free text — session id, commit sha, anything traceable.
    """
    bp = _backlog_path()
    if not bp.exists():
        return f"Error: no backlog found at {bp}. Run `backlog_init` first."
    try:
        idx = _lesson_candidates_defer(
            bp,
            title=title,
            kind=kind,
            topic=topic,
            scope=scope,
            context=context,
        )
    except ValueError as exc:
        return f"Error: {exc}"
    return f"Deferred candidate #{idx}: {title.strip()}"


@mcp.tool()
def backlog_lesson_candidates_list() -> str:
    """List deferred lesson candidates (markdown bullet list, indexed)."""
    bp = _backlog_path()
    if not bp.exists():
        return f"Error: no backlog found at {bp}."
    items = _lesson_candidates_read(bp)
    if not items:
        return "No deferred candidates."
    lines = []
    for idx, it in enumerate(items):
        kind = it.get("kind") or "?"
        topic = it.get("topic") or ""
        scope = it.get("scope") or "point"
        head = f"- [#{idx}] [{kind}/{scope}]"
        if topic:
            head += f" ({topic})"
        head += f" — {it.get('title', '')}"
        lines.append(head)
    return "\n".join(lines)


@mcp.tool()
def backlog_lesson_candidate_drop(index: int) -> str:
    """Drop the deferred candidate at `index` (0-based)."""
    bp = _backlog_path()
    if not bp.exists():
        return f"Error: no backlog found at {bp}."
    items = _lesson_candidates_read(bp)
    if index < 0 or index >= len(items):
        return f"Error: candidate #{index} not found (have {len(items)} entries)."
    title = items[index].get("title", "")
    n = _lesson_candidates_clear(bp, indices=[index])
    if not n:
        return f"Error: candidate #{index} not found."
    return f"Dropped candidate #{index}: {title}"


@mcp.tool()
def backlog_lesson_candidates_scan(days: int = 7, kind: str = "") -> str:
    """Grep this project's transcript jsonl for `<lesson-candidate>` tags.

    Recovery path for tags lost to compaction (until the PreCompact hook in
    v3-skills-006 lands, this is the only such path). Reads
    `~/.claude/projects/<this-project>/*.jsonl` within the last `days` days.

    Args:
        days: Window in days (default 7).
        kind: Filter to a single kind (gotcha / pattern / anti-pattern).

    Returns markdown grouped by source jsonl filename.
    """
    transcripts = _transcripts_dir()
    if not transcripts.exists():
        return f"No transcripts directory at {transcripts}."
    matches = _scan_transcripts_for_candidates(
        transcripts, days=days, kind_filter=kind
    )
    if not matches:
        return f"No `<lesson-candidate>` tags found in last {days} days."
    by_file: dict[str, list[dict[str, Any]]] = {}
    for m in matches:
        by_file.setdefault(Path(m["source_file"]).name, []).append(m)
    lines: list[str] = []
    for fname, items in by_file.items():
        lines.append(f"## {fname}")
        for it in items:
            tag = f"[{it.get('kind') or '?'}]"
            topic = f" ({it['topic']})" if it.get("topic") else ""
            preview = (it.get("body") or "").splitlines()[0][:100]
            lines.append(
                f"- L{it['source_line']} {tag}{topic} — {preview}"
            )
        lines.append("")
    return "\n".join(lines).rstrip()
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest plugins/taskmaster/tests/test_v3_lesson_candidates.py -v`
Expected: all eight new tests PASS (plus the prior twenty).

- [ ] **Step 7: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_v3_lesson_candidates.py
git commit -m "feat(taskmaster): MCP lesson candidate tools + handover review-flag wiring (v3-skills-003)"
```

---

## Task 5: Skill scaffold — directory + frontmatter

**Files:**
- Create: `plugins/taskmaster/skills/lesson/SKILL.md`
- Create (stubs): `plugins/taskmaster/skills/lesson/references/{marker-format,auto-extraction,reinforce-flows,promotion-decay,session-retro}.md`
- Create (stub): `plugins/taskmaster/skills/lesson/templates/lesson-body.md`

This task lays down the directory tree and the SKILL.md frontmatter only. Body and references are filled in subsequent tasks.

- [ ] **Step 1: Create the directory tree**

Run:
```bash
mkdir -p plugins/taskmaster/skills/lesson/references plugins/taskmaster/skills/lesson/templates
```

- [ ] **Step 2: Write SKILL.md frontmatter + section stubs**

Create `plugins/taskmaster/skills/lesson/SKILL.md`:

```markdown
---
name: lesson
description: "Write/reinforce/promote a project-scoped lesson. Invoke when the user says 'remember this', 'save as a lesson', 'learn this lesson', 'memorize this', 'this keeps happening', 'we always do X here', 'we got burned by this last time', 'promote candidate to lesson', 'review lesson candidates', or 'flag this session for retro'. Auto-offered by end-session when <lesson-candidate> tags or deferred candidates exist. Mid-session, emits <lesson-candidate> XML tags inline (no tool call) to flag knowledge to capture later. This is the only correct way to write or reinforce a project lesson — do not call backlog_lesson_create or backlog_lesson_reinforce directly."
---

# Lesson

(Filled in Task 6.)
```

- [ ] **Step 3: Create stub reference + template files**

Run:
```bash
for f in references/marker-format references/auto-extraction references/reinforce-flows references/promotion-decay references/session-retro templates/lesson-body; do
  echo "# (stub — populated in later task)" > plugins/taskmaster/skills/lesson/$f.md
done
```

- [ ] **Step 4: Verify file structure exists**

Run: `ls plugins/taskmaster/skills/lesson/ plugins/taskmaster/skills/lesson/references/ plugins/taskmaster/skills/lesson/templates/`
Expected output: `SKILL.md`, five `references/*.md` stubs, one `templates/lesson-body.md` stub.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/skills/lesson/
git commit -m "scaffold(taskmaster): lesson skill directory + SKILL.md frontmatter (v3-skills-003)"
```

---

## Task 6: SKILL.md — main body (5 entry points + write subflow)

**Files:**
- Modify: `plugins/taskmaster/skills/lesson/SKILL.md`

The operational core. Branches on which of the five entry points triggered the skill (per spec §4.2), shares one write subflow (§4.3), and documents the edge cases for `scope="session"` buffering and the disk-transcript fallback.

- [ ] **Step 1: Replace the SKILL.md body**

Open `plugins/taskmaster/skills/lesson/SKILL.md` and replace everything **after** the closing `---` of the frontmatter with:

````markdown
# Lesson

Project-scoped, structured knowledge that compounds across sessions. Where auto-memory captures *user* preferences globally, lessons capture *project* truths locally. The longer you use a project, the better this system becomes at it.

## Why this skill exists

The backend (`backlog_lesson_create`, `_reinforce`, `_update`, `_match`, `_digest`) is the storage layer; this skill is the **authoring + lifecycle** layer. Calling `backlog_lesson_create` directly skips auto-extraction (kind / triggers / why / what-to-do / examples), the user-review gate, and the candidate buffer that ties the write to mid-session signals. Always go through this skill.

## When to invoke

Five entry points, listed in `references/reinforce-flows.md` and dispatched in step 1 below:

1. **`write-from-context`** — explicit user invocation (`save as lesson`, `remember this`, …).
2. **`write-from-candidate`** — end-session sweep "Promote" action against a deferred or in-context candidate.
3. **`reinforce-immediate`** — Claude cited an `L-NNN` in its own response.
4. **`reinforce-sweep`** — end-session "which lessons applied this session?" sub-step.
5. **`session-retro`** — user later asks "scan handover X for retro lessons" against a `flag_for_review:true` handover.

In all five cases the user reviews and approves before any file is written.

## Mid-session: the `<lesson-candidate>` XML marker

While a session is running, this skill is **not** invoked for every candidate moment. Instead, Claude emits an inline tag (no tool call):

```xml
<lesson-candidate kind="gotcha" topic="multi-tab fanout" scope="point">
useEffect reading useLocation().state without active-tab guard.
Recurred on cb6927c0; fix is chatId === activeTabId early-return.
</lesson-candidate>
```

Heuristic for emit (any one is enough): user correction repeats; bug second-encounter (same root cause shape); architectural ground rule emerges ("we always X here", "never Y in this codebase"). Silence is the default — do not flag unless one of those fires.

Format details and grep convention live in `references/marker-format.md`. Do not abbreviate the opening anchor — it must always be the literal `<lesson-candidate ` (with one trailing space) so a single regex can recover it from disk transcripts.

## Steps

### 1. Identify the entry point

Pick exactly one — they each pass a different `intake` into the shared write subflow (step 3 onward) or skip the subflow entirely.

| Trigger signal | Entry | What runs |
|---|---|---|
| User said "save as lesson" / "remember this" / "we always do X here" | `write-from-context` | Write subflow with intake = current session context |
| End-session sweep promoted a candidate | `write-from-candidate` | Write subflow with intake = candidate body + session context |
| Claude just wrote "Per L-NNN, ..." | `reinforce-immediate` | Step 6 only (immediate reinforce) |
| End-session sub-step "which lessons applied?" | `reinforce-sweep` | Step 7 only (sweep reinforce) |
| User said "scan handover X for retro lessons" | `session-retro` | Step 8 (batch propose, then write subflow per accepted candidate) |

### 2. (Reinforce-immediate path) Call `backlog_lesson_reinforce`

Only for `reinforce-immediate`:

```
backlog_lesson_reinforce(lesson_id="L-NNN")
```

If the response includes "Eligible for promotion to core tier", surface it inline to the user — do not auto-promote. Stop here.

### 3. Write subflow — determine intake

Pull the intake from the entry point:

- `write-from-context`: candidate-shaped record built from current session prose (Claude's own context).
- `write-from-candidate`: deferred-file entry (read from `backlog_lesson_candidates_list`) or in-context `<lesson-candidate>` body.
- `session-retro`: per-candidate intake produced by step 8.

### 4. Auto-extract every field

Walk `references/auto-extraction.md` for the per-field source rules:

- **`title`** — first line of the candidate body or user request, ≤80 chars, imperative tense.
- **`kind`** — candidate `kind` attr if set, else inferred (corrections → `anti-pattern`; "we always" / "always do" → `pattern`; "watch out" / "got burned" → `gotcha`).
- **`triggers.files`** — `git diff --name-only HEAD~5` collapsed to globs (e.g. `src/auth/login.ts` + `src/auth/session.ts` → `src/auth/**`).
- **`triggers.task_titles_match`** — keyword extraction (3–5 nouns/verbs) from current and recent task titles.
- **Body `## Why`** — drafted from candidate body + bug/correction context.
- **Body `## What to do`** — numbered steps drafted from the resolution path.
- **Body `## Examples`** — task ids of session-touched tasks + commit SHAs from `git log --oneline HEAD~5`.
- **`related_tasks`** — task_ids in flight this session (from current `backlog_status`).

If the invocation included a focus hint (e.g. "focus on multi-tab"), weight extraction toward that topic.

### 5. Present the full draft for review

Show the user the assembled draft as one document with section labels (frontmatter preview + body). Then ask:

> "Looks good? I can change kind, edit triggers, rewrite Why / What to do / Examples, or drop sections."

Iterate until the user approves. Do **not** write the file before approval.

### 6. On approve, write through `backlog_lesson_create`

Call:

```
backlog_lesson_create(
    title=...,
    kind="gotcha"|"anti-pattern"|"pattern",
    body=<approved markdown body, with ## Why / ## What to do / ## Examples>,
    files=[...],
    task_titles_match=[...],
    task_kinds=[...],
    related_tasks=[...],
    related_issues=[...],
    tier="active",
)
```

Echo back the new id: *"Lesson written: `L-NNN`. It will trigger-load on tasks matching its triggers."*

### 6a. If the candidate had `scope="session"`

Do **NOT** modify any existing handover. Instead, **buffer** the flag for the next handover write this session:

- Set an internal note `pending_review_flag = {reason: <topic or first line of candidate body>}`.
- When end-session invokes `taskmaster:handover` (its v3-pre-2 step), pass `flag_for_review=true` + `review_reason=<reason>` to `backlog_handover_create`.
- If end-session is skipped (user wraps without writing a handover), the flag is **dropped silently**. `scope="session"` semantics require an associated handover artifact to flag — if there is no handover, there is nothing to flag.

If the candidate came from `_candidates.md`, also call `backlog_lesson_candidate_drop(index=<idx>)` to remove it from the deferred list.

### 7. Reinforce-sweep path (end-session sub-step)

Only for `reinforce-sweep`:

1. List lessons that were trigger-loaded at start-session OR cited mid-session by Claude. Use `backlog_lesson_list(tier="active")` then filter to ones that appear in your context.
2. Multi-select: which actually applied?
3. For each picked id:

   ```
   backlog_lesson_reinforce(lesson_id="L-NNN")
   ```

4. After all reinforcements, if any return surfaces "Eligible for promotion to core tier", ask the user:

   > "L-NNN is eligible for core tier (auto-loaded every session). Promote?"

   On confirm:

   ```
   backlog_lesson_update(lesson_id="L-NNN", tier="core")
   ```

   See `references/promotion-decay.md` for the core-cap (≤5 entries) handling.

### 8. Session-retro path

Only for `session-retro`. The user invokes with a handover id; that handover should have `flag_for_review: true` in its frontmatter (set when a `scope="session"` candidate was promoted in a prior session).

1. Read the handover via `backlog_handover_get(handover_id=...)`. Note its `task_ids` and `review_reason`.
2. Walk session signals:
   - `git log --oneline {handover.tip_commit}~..{handover.tip_commit}` for commits.
   - `backlog_get_task` for each id in `task_ids` — read their `notes` and recent updates.
   - If a transcript jsonl is reachable, run `backlog_lesson_candidates_scan(days=30)` and filter to that session window.
3. Propose a batch of candidates (typically 2–5). Each one has the same shape as a `<lesson-candidate>`.
4. For each candidate the user accepts: run the write subflow (steps 3–6) with that candidate's body as intake.

`references/session-retro.md` walks the full algorithm.

## Edge cases

- **No backlog** — `backlog_lesson_create` returns `Error: no backlog found ...`. Tell the user to run `backlog_init` first.
- **Compaction recovery** — if mid-session compaction wiped earlier `<lesson-candidate>` tags, offer `backlog_lesson_candidates_scan(days=7)` to recover them from the on-disk transcript. This is the only recovery path until the PreCompact hook (v3-skills-006) ships.
- **Server sandbox at wrong cwd** — if `backlog_lesson_candidates_scan` returns "No transcripts directory" but you know the project has sessions, the MCP server is rooted at the wrong cwd. Tell the user to restart Claude Code from the project root and skip the recovery scan; the in-context tags Claude can still see are unaffected.
- **Auto-suggestion source vs. candidate scan** — auto-memory `feedback/*.md` clusters with 2+ entries this project are *promotion suggestions*, not pre-flagged `<lesson-candidate>` tags. End-session merges both inputs (see end-session SKILL.md v3-pre-2a) but they have different shapes — handle them via the regular write subflow (intake = the cluster's representative entry).
- **Duplicate detection** — when the proposed `title` looks like an existing lesson's title, ask the user "this looks like L-NNN — reinforce that instead?" and route to `reinforce-immediate` if they confirm. Out of scope to do similarity scoring automatically; the user's eye is the check.

## References

- `references/marker-format.md` — XML schema, attrs, emit heuristics, compaction defenses
- `references/auto-extraction.md` — per-field extraction sources and fallbacks
- `references/reinforce-flows.md` — immediate + sweep + user-initiated reinforcement
- `references/promotion-decay.md` — core-tier promotion thresholds, decay UX, core cap handling
- `references/session-retro.md` — `scope="session"` flow + flagged-handover analysis
- `templates/lesson-body.md` — Why / What to do / Examples skeleton

## Spec

`docs/superpowers/specs/2026-05-03-lesson-skill-design.md`
````

- [ ] **Step 2: Spot-check that all referenced files exist**

Run:
```bash
ls plugins/taskmaster/skills/lesson/references/{marker-format,auto-extraction,reinforce-flows,promotion-decay,session-retro}.md
ls plugins/taskmaster/skills/lesson/templates/lesson-body.md
```
Expected: all six files print without error (they're stubs from Task 5; populated next).

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/skills/lesson/SKILL.md
git commit -m "feat(taskmaster): lesson skill — main SKILL.md flow with 5 entry points (v3-skills-003)"
```

---

## Task 7: References — populate the five reference docs

**Files:**
- Modify (replace stub): `plugins/taskmaster/skills/lesson/references/marker-format.md`
- Modify (replace stub): `plugins/taskmaster/skills/lesson/references/auto-extraction.md`
- Modify (replace stub): `plugins/taskmaster/skills/lesson/references/reinforce-flows.md`
- Modify (replace stub): `plugins/taskmaster/skills/lesson/references/promotion-decay.md`
- Modify (replace stub): `plugins/taskmaster/skills/lesson/references/session-retro.md`

Each reference stands alone — read in isolation when SKILL.md links to it.

- [ ] **Step 1: Write `references/marker-format.md`**

Replace the stub at `plugins/taskmaster/skills/lesson/references/marker-format.md` with:

````markdown
# Lesson Candidate Marker — XML Format

Mid-session, Claude flags lesson candidates with an inline XML tag. **No tool call is made** — the tag is plain text in Claude's response. End-session and disk-transcript scans recover the tags later.

## Tag schema

```xml
<lesson-candidate kind="gotcha" topic="multi-tab fanout" scope="point">
useEffect reading useLocation().state without active-tab guard.
Recurred on cb6927c0; fix is chatId === activeTabId early-return.
</lesson-candidate>
```

| Attr | Required | Values | Default | Purpose |
|------|----------|--------|---------|---------|
| `kind` | optional | `pattern` \| `anti-pattern` \| `gotcha` | (none) | Pre-fills the lesson `kind`; lets the sweep filter. |
| `topic` | optional | one-line free string | (none) | Grouping handle; one-word handle preferred. |
| `scope` | optional | `point` \| `session` | `point` | `session` flags the active handover for retro-extraction (see session-retro.md). |

**Body:** 1–3 sentences — what it is and why it matters. No file paths or commits required at the time of emit; auto-extraction fills those later.

## Grep-optimized conventions

These conventions exist so a literal `grep '<lesson-candidate '` over chat logs Just Works. Follow them exactly:

- **Stable opening anchor**: `<lesson-candidate ` (one trailing space). Never abbreviated, never variant.
- **Tags on their own lines**: opening + closing tags get dedicated lines. Body can be multi-line.
- **No nesting**: a candidate never contains another candidate.
- **Attrs are double-quoted**: `kind="gotcha"`, never `kind='gotcha'`, never `kind=gotcha`.

The backend regex (`scan_transcripts_for_candidates` in `taskmaster_v3.py`) anchors on the literal opening string and parses attrs with `(\w+)="([^"]*)"`. Single-quoted or unquoted attrs are silently skipped.

## When to emit a tag

Heuristic for emit, not a hard rule. Silence is the default when uncertain. Flag a candidate when ANY of:

1. **User correction repeats** — same correction made earlier this session, OR a feedback-memory entry matches a code pattern Claude just produced and got corrected on.
2. **Bug second-encounter** — Claude is debugging an issue and notices the resolution path matches an issue debugged earlier (same root cause shape).
3. **Architectural ground rule emerges** — user states a project rule conversationally ("we always X here", "never Y in this codebase") not yet captured as a lesson.

When in doubt, do not emit. Over-flagging trains the user to ignore the tags.

## Compaction handling

The risk: when Claude `/compact`s, the literal `<lesson-candidate>` tags in past turns get summarized away. Three defenses, in order:

1. **PreCompact hook (v3-skills-006, future)** — hook scans the about-to-be-compacted transcript for tags and persists new ones to `_candidates.md` before compaction completes. Durable defense; not yet shipped.
2. **Disk-transcript fallback** — `backlog_lesson_candidates_scan(days=7)` re-reads the raw `.jsonl` (which is uncompacted on disk) and recovers tags. **This is the only recovery path until the PreCompact hook ships.** Invoke explicitly when end-session detects compaction happened mid-session.
3. **Soft "important" defer** — when Claude emits a high-value tag (rare), it MAY also call `backlog_lesson_candidate_defer` immediately. Most candidates skip this — text-only is the default and zero-cost.

## Choosing `scope`

- `scope="point"` (default): a single concrete lesson (a gotcha, a pattern, an anti-pattern). The sweep proposes one lesson from this tag.
- `scope="session"`: the *whole session* is interesting and worth retro-extracting later. The sweep does NOT propose a single lesson — instead, it stamps the next handover with `flag_for_review: true`. Days or weeks later, the user can run `taskmaster:lesson` with that handover id to batch-extract candidates from the session's commits + transcript.

If you can name one specific gotcha, use `point`. If the value is "this whole session was a learning experience and I'll want to come back to it", use `session`.
````

- [ ] **Step 2: Write `references/auto-extraction.md`**

Replace stub at `plugins/taskmaster/skills/lesson/references/auto-extraction.md` with:

````markdown
# Lesson Auto-Extraction

For each lesson the skill writes, every frontmatter and body field is auto-drafted from a specific source. The user reviews and edits before the file is written.

## Per-field sources

| Field | Source | Fallback |
|-------|--------|----------|
| `title` | First sentence of the candidate body OR user's request phrase. ≤80 chars. Imperative tense ("Always X before Y"). | Ask the user. |
| `kind` | Candidate `kind` attr if set; else infer from session tone: corrections → `anti-pattern`; "we always" / "always do" → `pattern`; "watch out" / "got burned" / "this keeps biting" → `gotcha`. | Ask the user. |
| `triggers.files` | `git diff --name-only HEAD~5` from this session, collapsed to globs (e.g. `src/auth/login.ts` + `src/auth/session.ts` → `src/auth/**`). | `[]` (lesson loads only via `task_titles_match`). |
| `triggers.task_titles_match` | 3–5 keyword nouns/verbs from current task title + last 3 task titles in `backlog_status`. | `[]`. |
| `triggers.task_kinds` | Currently-in-progress task's `kind` field if it has one; else `[]`. | `[]`. |
| Body `## Why` | Candidate body + correction/bug context Claude has. 2–4 sentences. | Ask the user. |
| Body `## What to do` | Numbered list. Steps drawn from the resolution path Claude observed. ≥2 steps. | Ask the user. |
| Body `## Examples` | Bullet list of `T-NNN`/`feature-NNN` task ids touched this session + 1–3 short commit SHAs from `git log --oneline -5`. | `(none)` — drop the section if empty. |
| `related_tasks` | Task ids in `backlog_status` with status `in-progress` or transitioned this session. | `[]`. |
| `related_issues` | `ISS-NNN` ids referenced in this session's prose (regex `\bISS-\d+\b` over conversation). | `[]`. |

## Glob collapsing rule

When two or more file paths share a common ancestor of depth ≥2, collapse to `<ancestor>/**`. When they don't, list each path explicitly. Examples:

- `src/auth/login.ts` + `src/auth/session.ts` → `src/auth/**`
- `src/auth/login.ts` + `tests/auth/test_login.py` → `["src/auth/**", "tests/auth/**"]` (separate glob each).
- A single file → keep the literal path; don't collapse to `**`.

## Focus-hint weighting

When the user invokes the skill with a hint (e.g. "save a lesson — focus on multi-tab fanout"), weight extraction toward that topic:

- `title` must include the hint word(s).
- `triggers.task_titles_match` must include the hint word as one of the first 3 keywords.
- Body `## Why` first sentence must explain why the hint topic causes the issue.

The hint never overrides explicit candidate attrs (`kind=`, `topic=`); it only steers the auto-fill where the candidate is silent.

## What gets dropped from extraction

- Paths under `node_modules/`, `__pycache__/`, `.venv/`, `.git/`, `dist/`, `build/`, `.snapshots/`, `.taskmaster/auto/`. Same exclusion list as the handover skill.
- Paths the regex caught from prose that are obviously not real (e.g. `example.com`, `foo.bar.baz`).
- Tasks the user said to ignore in this session.

When a path is dropped, do **not** silently swallow it — note in the draft preview "(dropped <path>: <reason>)" so the user can override.
````

- [ ] **Step 3: Write `references/reinforce-flows.md`**

Replace stub at `plugins/taskmaster/skills/lesson/references/reinforce-flows.md` with:

````markdown
# Lesson Reinforce Flows

Three reinforcement modes; same backend (`backlog_lesson_reinforce`), different orchestration.

## 1. Reinforce-immediate

When Claude proactively cites a lesson in a response (e.g. *"Per L-007, you should read auth/session.ts before editing the login flow"*), it calls `backlog_lesson_reinforce` immediately after the citation:

```
backlog_lesson_reinforce(lesson_id="L-007")
```

The MCP tool's return includes the eligibility hint when `reinforce_count` crosses the promotion threshold:

```
Reinforced L-007 → x5
→ Eligible for promotion to core tier (auto-load at session start). Use `backlog_lesson_update L-007 tier=core` to promote.
```

Surface the hint inline. Do **not** auto-promote — wait for the end-session sweep (or an explicit user request) to trigger the user-confirmed promotion.

User push-back later (e.g. "actually, that wasn't relevant") does **not** decrement `reinforce_count` automatically. Over-counting is acceptable; the user can `backlog_lesson_update` to correct if they care.

## 2. Reinforce-sweep (end-session)

Run during end-session's v3-pre-2a step:

1. List lessons that were trigger-loaded at start-session (use the `backlog_lesson_list(tier="active")` output and intersect with whatever start-session injected) OR cited mid-session by Claude.

2. Present a multi-select to the user:

   ```
   AskUserQuestion({
     questions: [{
       question: "Which lessons actually applied this session?",
       header: "Reinforce",
       multiSelect: true,
       options: [
         { label: "L-007 [gotcha] Always read auth/session.ts before editing auth flow", description: "trigger-loaded; appeared in this session" },
         { label: "L-014 [pattern] Use AskUserQuestion for ambiguous intents", description: "cited at turn 23" },
         { label: "Skip — none of these applied", description: "" }
       ]
     }]
   })
   ```

3. For each pick, call:

   ```
   backlog_lesson_reinforce(lesson_id="L-NNN")
   ```

4. After all reinforcements, if any return surfaces "Eligible for promotion to core tier", ask:

   > "L-NNN is eligible for core tier (auto-loaded every session). Promote?"

   On confirm: `backlog_lesson_update(lesson_id="L-NNN", tier="core")`. See `promotion-decay.md` for the core-cap (5/5) handling.

## 3. Reinforce — user-initiated

The user can invoke reinforce-immediate explicitly any time:

> "Reinforce L-014 — that just bit me again."

This is a single-step path: call `backlog_lesson_reinforce(lesson_id="L-014")` and surface the response. No sweep, no multi-select. Same eligibility-hint surfacing as path 1.

## What reinforcement actually does

`backlog_lesson_reinforce` (backend: `reinforce_lesson` in `taskmaster_v3.py`) increments `reinforce_count` by 1, sets `last_reinforced` to today's ISO date, and rewrites the lesson file. Side effect: the lesson moves up in the digest sort order (`backlog_lesson_digest` sorts by reinforce_count desc).

Eligibility for core promotion: `tier == "active"` AND `kind in {gotcha, anti-pattern}` AND `reinforce_count >= 5`. Patterns never auto-promote — they're the cheap, common case where applying the rule shouldn't push it to core.
````

- [ ] **Step 4: Write `references/promotion-decay.md`**

Replace stub at `plugins/taskmaster/skills/lesson/references/promotion-decay.md` with:

````markdown
# Lesson Promotion + Decay

Lessons compound through the `active → core` promotion (high-value, always loaded) and decay through `active → retired` (silent auto-retire when stale). Both flows are server-side primitives; this doc explains the surface UX.

## Promotion to core

**Eligibility (server-side, in `lesson_eligible_for_promotion`):**

```python
fm["tier"] == "active"
and fm["kind"] in ("gotcha", "anti-pattern")
and fm["reinforce_count"] >= 5    # LESSON_PROMOTE_REINFORCE
```

Patterns never auto-promote — they're cheap to re-derive. Only gotchas and anti-patterns earn the always-loaded slot.

**Surface:** never silent. Two surfaces:

1. **Inline reinforce response** — `backlog_lesson_reinforce` already includes "Eligible for promotion to core tier" in its return when threshold crosses. The skill surfaces this inline; it does **not** auto-promote.
2. **End-session sweep step** — after batch-reinforcing, the skill iterates eligible lessons and prompts:

   > "L-007 is eligible for core tier (auto-loaded every session). Promote?"

User-confirmed always. On yes:

```
backlog_lesson_update(lesson_id="L-007", tier="core")
```

## Core cap (5/5)

Hard cap: ≤5 lessons in `core` tier (constant `LESSON_CORE_CAP`). When promotion would exceed the cap, offer a swap:

> "Core tier is full (5/5). The lowest-count core lesson is L-002 (count 3). Demote L-002 back to active to make room?"

User-confirmed. On yes: `backlog_lesson_update(lesson_id="L-002", tier="active")` then `backlog_lesson_update(lesson_id="L-007", tier="core")`. On no: leave L-007 active and **suppress the eligibility prompt for the rest of the session** (don't pester the user every reinforcement).

## Decay (auto-retire)

**Eligibility (server-side, in `lesson_eligible_for_decay`):**

```python
fm["tier"] == "active"
and (today - last_reinforced).days >= 180   # LESSON_DECAY_DAYS
and fm["reinforce_count"] < 2               # LESSON_DECAY_REINFORCE
```

Lessons never reinforced fall back to `created` date as the proxy.

**Surface:** **silent**. The decay sweep happens server-side without user interaction. End-session may emit a single info line if any lessons retired this session:

> *"Retired N stale lessons (review with `backlog_lesson_list --tier retired`)."*

No prompt, no action — signal only. The user can list retired lessons and `backlog_lesson_update(lesson_id, tier="active")` to revive any false-positive retirements.

## Manual demotion

Either tier flip is just `backlog_lesson_update(lesson_id, tier=...)`. Use `backlog_lesson_update(lesson_id, tier="retired")` to permanently retire a lesson the user no longer wants surfaced; the file stays on disk for history.

## Where this surfaces

- Start-session: loads all `core` tier lessons in full + the digest of active tier (capped at 30 per `LESSON_DIGEST_CAP`).
- Pick-task: `match_lessons_for_task` injects up to 3 (`LESSON_TRIGGER_MATCH_CAP`) trigger-matched active+core lessons. Retired never matches.
- End-session: this skill's sweep step is where reinforcement and promotion prompts surface.
````

- [ ] **Step 5: Write `references/session-retro.md`**

Replace stub at `plugins/taskmaster/skills/lesson/references/session-retro.md` with:

````markdown
# Session-Retro Flow (`scope="session"`)

A `<lesson-candidate scope="session">` tag does **not** propose a single lesson immediately. Instead, it flags the *whole session* for later retro-extraction. This handles the "this whole session was a learning experience and I'll come back to it" case without forcing the user to summarize 100+ turns into one body at end-of-session.

## End-session: stamping the flag

When end-session's sweep encounters a `scope="session"` candidate (either in-context or in `_candidates.md`):

1. **Do NOT** modify any existing handover.
2. Buffer a `pending_review_flag` in the lesson skill's working memory:
   ```
   pending_review_flag = {
     reason: <topic attr OR first line of candidate body>,
   }
   ```
3. When end-session invokes `taskmaster:handover` (its v3-pre-2 step), the lesson skill passes the buffered flag through:
   ```
   backlog_handover_create(
       tldr=...,
       next_action=...,
       body=...,
       session_kind="end-of-day",  # or whatever the user picked
       flag_for_review=True,
       review_reason="<topic or summary>",
   )
   ```
4. The new handover lands with `flag_for_review: true` + `review_reason: <text>` in its frontmatter.
5. If end-session is skipped (user wraps without writing a handover), the flag is **dropped silently**. There is no orphan handover to attach a flag to.

If the user writes the handover *first* and then promotes a `scope="session"` candidate later in the same session, the candidate's promotion calls `apply_handover_review_flag(handover_id=<just-written-id>, review_reason=...)` directly — same effect, different ordering.

## Session-retro entry point — invocation

Days or weeks later, the user invokes:

> "scan handover 2026-05-03-autonomous-3hour for retro lessons"

The `taskmaster:lesson` skill's `session-retro` entry point fires.

## Session-retro algorithm

1. **Load the handover.** Call `backlog_handover_get(handover_id=...)`. Read its `task_ids`, `tip_commit`, `branch`, `review_reason`.

2. **Mine commits in the session window.** Run `git log --oneline {tip_commit}~10..{tip_commit}` (or `{tip_commit}~{n}..{tip_commit}` heuristically based on commit timestamps; if the previous milestone-complete handover exists, use its `tip_commit` as the lower bound). Capture commit SHAs and messages.

3. **Mine task notes.** For each id in `handover.task_ids`, call `backlog_get_task` and read `notes`. Recent notes added during the flagged session are likely lesson-shaped.

4. **Mine the transcript (if available).** Call `backlog_lesson_candidates_scan(days=<window>, kind="")` where `<window>` is the number of days since the handover's `date`. Filter results to entries whose `source_file` mtime is within ±1 day of the handover's date.

5. **Synthesize candidate proposals.** Cluster the signals (commits + notes + scanned tags) into 2–5 distinct lesson candidates. Each candidate has the same shape as a `<lesson-candidate>`: `kind`, `topic`, body summary.

6. **Present the batch.** Show the user the list, with provenance per candidate (which commit / note / scanned tag drove it). Multi-select: which to promote?

7. **Per accepted candidate, run the write subflow** (SKILL.md steps 3–6) using that candidate's body as intake.

## What `flag_for_review` does NOT do

- It does **not** auto-trigger session-retro at start-session. The user has to invoke it explicitly.
- It does **not** prevent the handover from being superseded — `apply_supersession` rewrites the body callout but leaves the flag intact in frontmatter.
- It does **not** mean the handover is broken or special — it's just a lookup hint for future retro work.

## Future enrichment (out of scope)

Per spec §11: a richer session-retro product could add productivity metrics, task ordering analysis, tool-usage breakdown, and a dedicated review skill. Tracked but not built — this skill ships with the simple "scan + propose" version.
````

- [ ] **Step 6: Commit**

```bash
git add plugins/taskmaster/skills/lesson/references/
git commit -m "feat(taskmaster): lesson skill reference docs (5 references) (v3-skills-003)"
```

---

## Task 8: Template — `lesson-body.md`

**Files:**
- Modify (replace stub): `plugins/taskmaster/skills/lesson/templates/lesson-body.md`

A skeleton matching spec §10: Why / What to do / Examples. Used by the auto-extractor as the body shape.

- [ ] **Step 1: Write `templates/lesson-body.md`**

Replace stub at `plugins/taskmaster/skills/lesson/templates/lesson-body.md` with:

````markdown
<!--
LESSON BODY TEMPLATE
Used by `taskmaster:lesson` write subflow. Auto-extractor fills each section
from session signals; user reviews before write.

Drop a section ONLY if there is genuinely no content (rare). Never leave
{placeholder} text in the final lesson.
-->

## Why

{2–4 sentences explaining the failure mode, the recurring pain, or the rule.
Concrete: name the specific bug shape, the specific correction, the specific
ground truth. Avoid abstractions like "be careful" — those are useless.}

## What to do

1. {First concrete step. Verb-led, specific, actionable.}
2. {Second concrete step.}
3. {Third concrete step (optional, but most lessons need at least 2 steps).}

## Examples

- {T-NNN or feature-NNN — task where this lesson applied this session.}
- {commit-SHA — short SHA + 1-line message of a commit demonstrating the rule.}
- {Optional second example for context.}
````

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/skills/lesson/templates/lesson-body.md
git commit -m "feat(taskmaster): lesson skill body template (v3-skills-003)"
```

---

## Task 9: Retrofit `taskmaster:end-session`

**Files:**
- Modify: `plugins/taskmaster/skills/end-session/SKILL.md` (insert v3-pre-2a step before existing v3-pre-2)

A new sub-step inserts before v3-pre-2 (handover offer). It runs the candidate sweep, the reinforce-applied loop, the promotion prompt, and the decay info line. Per spec §5, all six logical phases are documented but only the first two are routine; the disk scan is on-demand recovery only.

- [ ] **Step 1: Insert v3-pre-2a between v3-pre-1 and v3-pre-2**

In `plugins/taskmaster/skills/end-session/SKILL.md`, find the existing `**v3-pre-2: Handover offer.**` block (line 24). Insert immediately **before** it the new v3-pre-2a block. The result around lines 22–48 should read:

````markdown
**v3-pre-1: Snapshot.** Call `backlog_snapshot(quiet=true)` to capture pre-end-of-session state. ...

**v3-pre-2a: Lesson candidate sweep.** Decide whether to invoke `taskmaster:lesson` for an end-session sweep. Auto-offer when ANY of:
   - Any `<lesson-candidate>` tag visible in the current conversation context.
   - Any entries in `.taskmaster/lessons/_candidates.md` (check via `backlog_lesson_candidates_list`).
   - Any feedback-memory cluster with 2+ entries scoped to this project (auto-suggestion source — separate from candidate scans).

   Inputs (gathered in this order, then merged for review):

   1. **Candidate-discovery scans** (routine):
      - In-context scan: grep Claude's own conversation memory for `<lesson-candidate `.
      - Deferred-file read: `backlog_lesson_candidates_list`.
   2. **Auto-suggestion source** (routine, separate input — not a candidate scan):
      - Scan auto-memory `feedback/*.md` for 2+ similar entries this project. These are *promotion suggestions*, not pre-flagged candidates.
   3. **Disk-transcript scan** (on-demand only): if this session had a `/compact` event, offer `backlog_lesson_candidates_scan(days=7)` as a recovery option. Skip otherwise.

   If any candidates or suggestions exist, ask:

   > *"Found N lesson candidates from this session. Review now?"* (user-confirmed; default skip)

   If the user accepts, invoke `taskmaster:lesson` with each candidate. Per-candidate options:

   | Action | What runs |
   |---|---|
   | Promote | Lesson skill's write subflow (auto-extract + user review + `backlog_lesson_create`). |
   | Defer | `backlog_lesson_candidate_defer(...)` — the candidate stays in `_candidates.md` for next session. |
   | Discard | Drop without persisting (no tool call). |

   For any promoted candidate with `scope="session"`: the lesson skill **buffers** a `flag_for_review` for the upcoming handover write (next sub-step). Do not modify any existing handover here.

   Then: list lessons that were trigger-loaded at start-session OR cited mid-session by Claude. Multi-select prompt: "which actually applied this session?" For each pick:

   ```
   backlog_lesson_reinforce(lesson_id="L-NNN")
   ```

   After all reinforcements: if any return surfaces "Eligible for promotion to core tier", ask the user once:

   > *"L-NNN is eligible for core tier (auto-loaded every session). Promote?"* (yes → `backlog_lesson_update(lesson_id, tier="core")`; respect the core cap from references/promotion-decay.md)

   Finally: if any lessons auto-retired this session (server-side), emit one info line:

   > *"Retired N stale lessons (review with `backlog_lesson_list --tier retired`)."*

   No prompt, signal only.

   If none of the auto-offer conditions apply, skip this whole sub-step silently — no prompt.

**v3-pre-2: Handover offer.** Decide whether to offer a session handover. ...
````

(Preserve the existing v3-pre-2 content unchanged after the insertion.)

- [ ] **Step 2: Wire the buffered review flag through to handover write**

Inside the existing v3-pre-2 block, find the line:

```markdown
If user picks yes, **invoke the `taskmaster:handover` skill** with the chosen `session_kind`. End-session does NOT draft the body itself — the handover skill owns tier selection, auto-extraction, and supersession chaining. End-session continues regardless of the handover skill's outcome.
```

Add a sentence after it:

```markdown
If v3-pre-2a buffered a `pending_review_flag` (any `scope="session"` candidate was promoted in this session), pass `flag_for_review=true` and `review_reason=<buffered reason>` through to the handover skill's call. The handover skill forwards both kwargs to `backlog_handover_create`. If the user skipped the handover write, the flag is dropped silently.
```

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/skills/end-session/SKILL.md
git commit -m "feat(taskmaster): end-session v3-pre-2a lesson sweep + review-flag wiring (v3-skills-003)"
```

---

## Task 10: Retrofit `taskmaster:taskmaster` router

**Files:**
- Modify: `plugins/taskmaster/skills/taskmaster/SKILL.md` (line 39 — the existing lesson row)

The current router routes "Remember this", "this keeps happening", "we always do X here", "save a lesson" to `Direct tool call — backlog_lesson_create`. Replace that with a route to the new skill, plus add the trigger phrases the skill description introduces.

- [ ] **Step 1: Edit the router row**

In `plugins/taskmaster/skills/taskmaster/SKILL.md`, find:

```
| (v3) "Remember this", "this keeps happening", "we always do X here", "save a lesson" | Direct tool call — `backlog_lesson_create` (ask: pattern, anti-pattern, or gotcha?) |
```

Replace with:

```
| (v3) "Remember this", "save as a lesson", "learn this lesson", "memorize this", "this keeps happening", "we always do X here", "we got burned by this last time", "promote candidate to lesson", "review lesson candidates", "flag this session for retro" | `taskmaster:lesson` |
```

Leave the `backlog_lesson_digest` / `backlog_lesson_match` row (line 40) unchanged — those are read paths, not skill paths.

- [ ] **Step 2: Update the v3 disambiguation `lesson vs note` bullet**

In the same file, find the disambiguation bullet (around line 73):

```
- **lesson vs note:** task notes are scratch space for one task. A lesson is project-wide guidance that triggers across many future tasks. "Note this for the task" → task notes field. "Remember this for next time you touch auth" → `backlog_lesson_create`.
```

Replace the last sentence with:

```
"Remember this for next time you touch auth" → `taskmaster:lesson` (which writes the lesson + handles candidate review + reinforcement).
```

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/skills/taskmaster/SKILL.md
git commit -m "feat(taskmaster): route lesson-write intents to the lesson skill (v3-skills-003)"
```

---

## Task 11: Lint test for skill structure

**Files:**
- Create: `plugins/taskmaster/tests/test_lesson_skill_lint.py`

Black-box validation of the skill scaffolding: SKILL.md frontmatter, all trigger phrases in description, all 6 referenced files (5 references + 1 template) exist with non-trivial content, SKILL.md links resolve. Mirrors `test_handover_skill_lint.py`.

- [ ] **Step 1: Write the test**

Create `plugins/taskmaster/tests/test_lesson_skill_lint.py`:

```python
"""Lint checks for the taskmaster:lesson skill scaffolding."""
from pathlib import Path
import re

import yaml

SKILL_DIR = Path(__file__).resolve().parents[1] / "skills" / "lesson"


def _read_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return {}
    return yaml.safe_load(m.group(1)) or {}


def test_skill_md_exists():
    assert (SKILL_DIR / "SKILL.md").exists()


def test_frontmatter_has_required_fields():
    fm = _read_frontmatter(SKILL_DIR / "SKILL.md")
    assert fm.get("name") == "lesson"
    assert "description" in fm and isinstance(fm["description"], str)
    # Description must be >= 200 chars to actually convey the trigger surface.
    assert len(fm["description"]) >= 200


def test_description_contains_all_trigger_phrases():
    fm = _read_frontmatter(SKILL_DIR / "SKILL.md")
    desc = fm["description"].lower()
    must_have = [
        "remember this",
        "save as a lesson",
        "learn this lesson",
        "memorize this",
        "this keeps happening",
        "we always do x here",
        "we got burned by this last time",
        "promote candidate to lesson",
        "review lesson candidates",
        "flag this session for retro",
    ]
    missing = [p for p in must_have if p not in desc]
    assert not missing, f"description is missing trigger phrases: {missing}"


def test_all_referenced_files_exist():
    expected_refs = [
        SKILL_DIR / "references" / "marker-format.md",
        SKILL_DIR / "references" / "auto-extraction.md",
        SKILL_DIR / "references" / "reinforce-flows.md",
        SKILL_DIR / "references" / "promotion-decay.md",
        SKILL_DIR / "references" / "session-retro.md",
        SKILL_DIR / "templates" / "lesson-body.md",
    ]
    missing = [p for p in expected_refs if not p.exists()]
    assert not missing, f"missing referenced files: {missing}"


def test_references_are_not_stubs():
    # Each reference > 20 non-blank lines; template > 5 (per spec §13).
    for ref in (SKILL_DIR / "references").iterdir():
        non_blank = [ln for ln in ref.read_text(encoding="utf-8").splitlines() if ln.strip()]
        assert len(non_blank) > 20, f"reference looks like a stub: {ref}"
    for tpl in (SKILL_DIR / "templates").iterdir():
        non_blank = [ln for ln in tpl.read_text(encoding="utf-8").splitlines() if ln.strip()]
        assert len(non_blank) > 5, f"template looks like a stub: {tpl}"


def test_skill_md_links_resolve():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    refs = re.findall(r"`(references/[A-Za-z0-9_-]+\.md|templates/[A-Za-z0-9_-]+\.md)`", text)
    assert refs, "SKILL.md does not reference any references/ or templates/ files"
    missing = [r for r in refs if not (SKILL_DIR / r).exists()]
    assert not missing, f"SKILL.md links do not resolve: {missing}"


def test_skill_md_documents_all_five_entry_points():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8").lower()
    must_have = [
        "write-from-context",
        "write-from-candidate",
        "reinforce-immediate",
        "reinforce-sweep",
        "session-retro",
    ]
    missing = [p for p in must_have if p not in text]
    assert not missing, f"SKILL.md missing entry-point names: {missing}"
```

- [ ] **Step 2: Run the test**

Run: `pytest plugins/taskmaster/tests/test_lesson_skill_lint.py -v`
Expected: all seven tests PASS.

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/tests/test_lesson_skill_lint.py
git commit -m "test(taskmaster): lint checks for lesson skill scaffolding (v3-skills-003)"
```

---

## Task 12: Dogfood — defer a real candidate, promote it, write the lesson

**Files:**
- New (created by skill flow): `.taskmaster/lessons/L-NNN.md`
- Modified by sync: `backlog.yaml` (`lessons_meta` index)

The acceptance criterion: walk the full skill end-to-end against this v3 worktree, capturing a real lesson encountered during the v3-skills-002 work — specifically the "MCP server cwd mismatch breaks worktree-rooted backlog operations" gotcha.

- [ ] **Step 1: Run all backend + lint tests**

Run:
```bash
pytest plugins/taskmaster/tests/test_v3_lesson_candidates.py plugins/taskmaster/tests/test_lesson_skill_lint.py -v
```
Expected: all tests from Tasks 1–4 + Task 11 PASS. If anything fails, stop and fix before dogfooding.

- [ ] **Step 2: Emit a candidate inline (simulating a mid-session capture)**

In Claude Code, type the following exactly as a user prompt:

> "I want to capture a lesson — when running taskmaster MCP commands from a worktree, the MCP server may still be rooted at the main checkout's cwd, so backlog operations silently target the wrong .taskmaster/. We hit this end-sessioning v3-skills-002 from this worktree. Please defer it as a candidate first."

The skill should:
1. Recognise the `write-from-context` entry point (the user said "capture a lesson").
2. Notice the user wants to defer first (the "Please defer it as a candidate first" directive).
3. Call:

   ```
   backlog_lesson_candidate_defer(
       title="MCP server cwd mismatch breaks worktree-rooted backlog operations",
       kind="gotcha",
       topic="mcp-cwd-worktree",
       scope="point",
       context="end-sessioning v3-skills-002 from .worktrees/taskmaster-v3"
   )
   ```

4. Echo back: `Deferred candidate #0: MCP server cwd mismatch ...`

- [ ] **Step 3: Verify the candidate file landed**

Run:
```bash
cat .taskmaster/lessons/_candidates.md
```

Expected output (exact format may vary in whitespace, but these markers must be present):

```
# Lesson Candidates (deferred)

> Auto-managed by `taskmaster:lesson`. Edit by hand only if the file is corrupt.

```yaml
candidates:
- title: MCP server cwd mismatch breaks worktree-rooted backlog operations
  kind: gotcha
  topic: mcp-cwd-worktree
  scope: point
  context: end-sessioning v3-skills-002 from .worktrees/taskmaster-v3
  deferred_at: '2026-05-03T...'
```
```

- [ ] **Step 4: Promote via the lesson skill**

In Claude Code, type:

> "Promote candidate #0 to a lesson now."

The skill should:
1. Recognise the `write-from-candidate` entry point.
2. Read the candidate via `backlog_lesson_candidates_list` and pull entry #0.
3. Auto-extract the rest of the fields per `references/auto-extraction.md`:
   - `triggers.files` — `["plugins/taskmaster/**", ".taskmaster/**"]` (from this session's git diff).
   - `triggers.task_titles_match` — `["v3", "skills", "handover", "lesson"]`.
   - Body `## Why` — drafted from the candidate body explaining the cwd mismatch.
   - Body `## What to do` — a numbered list (e.g. "1. Always restart Claude Code from the project root before MCP backlog operations. 2. If MCP returns a cwd mismatch error, do not retry — surface to user immediately. 3. ...").
   - Body `## Examples` — `v3-skills-002` task id + the latest commit SHA.
4. Present the draft for review.

- [ ] **Step 5: Approve the draft**

When prompted "Looks good?", reply: *"Looks good."*

The skill should call:

```
backlog_lesson_create(
    title="MCP server cwd mismatch breaks worktree-rooted backlog operations",
    kind="gotcha",
    body="## Why\n...\n\n## What to do\n1. ...\n\n## Examples\n- ...",
    files=["plugins/taskmaster/**", ".taskmaster/**"],
    task_titles_match=["v3", "skills", "handover", "lesson"],
    related_tasks=["v3-skills-003"],
    tier="active",
)
```

Then call `backlog_lesson_candidate_drop(index=0)` to clear the deferred entry.

- [ ] **Step 6: Verify the lesson file landed and the index synced**

Run:
```bash
ls .taskmaster/lessons/
cat .taskmaster/lessons/L-001.md
```
Expected: `L-001.md` exists; frontmatter has `kind: gotcha`, `tier: active`, `reinforce_count: 0`; body has all three sections (`## Why`, `## What to do`, `## Examples`).

Run:
```bash
grep -A 5 "lessons_meta:" backlog.yaml
```
Expected: `lessons_meta` contains an entry with `id: L-001`, `kind: gotcha`, `tier: active`, `reinforce_count: 0`.

Run:
```bash
cat .taskmaster/lessons/_candidates.md 2>/dev/null || echo "(file deleted)"
```
Expected: `(file deleted)` — the candidates file is removed when the list goes empty.

- [ ] **Step 7: Verify reinforce-immediate works**

In Claude Code, type:

> "Per L-001, I should restart Claude Code from the project root."

The skill should recognise the citation and call `backlog_lesson_reinforce(lesson_id="L-001")`. Expected response: `Reinforced L-001 → x1`.

Run:
```bash
grep -A 1 "reinforce_count" .taskmaster/lessons/L-001.md
```
Expected: `reinforce_count: 1` and `last_reinforced: 2026-05-03`.

- [ ] **Step 8: Commit the dogfood lesson + index update**

```bash
git add .taskmaster/lessons/L-001.md backlog.yaml
git commit -m "chore(taskmaster): dogfood L-001 (mcp-cwd-worktree gotcha) for v3-skills-003 ship"
```

- [ ] **Step 9: Mark `v3-skills-003` as in-review**

In Claude Code, invoke `taskmaster:end-session` with `target_status=in-review`. The user manually validates the dogfooded lesson before flipping to `done`.

---

## Acceptance criteria (cross-check against spec §13)

- [ ] Backend: candidates round-trip (defer → read → clear) — Task 1.
- [ ] Backend: scope handling on defer — Task 1.
- [ ] Backend: `scan_transcripts_for_candidates` regex + filters — Task 2.
- [ ] Backend: `apply_handover_review_flag` idempotency + missing-id raise — Task 3.
- [ ] MCP: each new tool's happy path + missing-args + error format consistency — Task 4.
- [ ] MCP: `backlog_handover_create(flag_for_review=True, review_reason=...)` writes both fields, omits when false — Task 4.
- [ ] Skill lint: SKILL.md frontmatter has all triggers from spec §4.1 — Task 11.
- [ ] Skill lint: all 6 referenced files exist with non-trivial content (>20 lines refs, >5 lines template) — Task 11.
- [ ] Skill lint: all 5 entry points documented — Task 11.
- [ ] End-session retrofit: v3-pre-2a sub-step exists, references invoked tools, doesn't break v2 flow — Task 9.
- [ ] One end-to-end dogfood — Task 12.
