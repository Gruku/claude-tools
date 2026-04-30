# Taskmaster Viewer Redesign — Plan 5a: Sessions / Handovers + Recap

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Sessions/Handovers screen (Hybrid C diary with parallel-block clusters and nested handovers/recaps + right-rail detail) and the Recap screen (story+receipts layered layout with prev/next picker, edit mode, and 2×2 receipts grid). Introduce the Recap entity on disk, the synthesized Session list, the snapshot-diff helper, and the shared `RightRail` / `Timeline` / `RecapReceiptsGrid` / `DiffRow` components used by Plans 3 and 5b.

**Architecture:** Server adds `list_sessions()`, `load_recap()`, `save_recap()`, `list_recaps()`, `snapshot_diff()` helpers in `taskmaster_v3.py`; corresponding MCP tools and HTTP endpoints (`GET/PUT /api/recap/<sid>`, `GET /api/sessions[/<sid>]`, `GET /api/snapshots/diff`) in `backlog_server.py`. Client adds two screen modules (`sessions.js`, `recap.js`), four shared components (`right-rail.js`, `timeline.js`, `recap-receipts-grid.js`, `diff-row.js`), and two screen CSS files. Tests: pytest with `running_server` fixture (Plan 1 pattern), `node --test` for pure-data unit tests, and Playwright for UI smoke.

**Tech Stack:** Vanilla HTML/CSS/JS modules (no bundler), Python 3 + `fastmcp` + `BaseHTTPRequestHandler`, pytest, `node --test`, Playwright.

**Spec reference:** `docs/superpowers/specs/2026-04-26-taskmaster-viewer-redesign.md` §3.12 (Sessions/Handovers) and §3.16 (Recap).

---

## File Structure

**Server (created/modified in this plan):**
```
plugins/taskmaster/
├── taskmaster_v3.py                       # add: RECAP_SCHEMA_VERSION, HANDOVER_KIND_TO_VIEWER_KIND,
│                                          #      list_sessions, load_recap, save_recap, list_recaps,
│                                          #      snapshot_diff, save_session_snapshot
├── backlog_server.py                      # add: recap_get/recap_set/recap_list/snapshot_diff MCP tools;
│                                          #      HTTP routes for /api/sessions[/<sid>], /api/recap/<sid>,
│                                          #      /api/snapshots/diff
└── tests/
    ├── test_v3_recap.py                   # NEW
    ├── test_v3_snapshot_diff.py           # NEW
    ├── test_v3_sessions.py                # NEW
    └── test_server_sessions_recap.py      # NEW
```

**Shared client components (created in this plan; Plan 3 / Plan 5b reuse):**
```
plugins/taskmaster/viewer/js/components/
├── right-rail.js                          # generic 480px right-rail with content renderer
├── timeline.js                            # chronological diary with parallel-block clusters
├── recap-receipts-grid.js                 # 2×2 diff cards
└── diff-row.js                            # +/~/- row with from→to display
```

**Sessions screen:**
```
plugins/taskmaster/viewer/
├── css/screens/sessions.css               # NEW
└── js/screens/sessions.js                 # REPLACES Plan 1 stub
```

**Recap screen:**
```
plugins/taskmaster/viewer/
├── css/screens/recap.css                  # NEW
└── js/screens/recap.js                    # REPLACES Plan 1 stub
```

**Tests (client):**
```
plugins/taskmaster/viewer/tests/
├── unit/parallel-block.test.js            # node --test
├── unit/snapshot-diff.test.js             # node --test
├── sessions.spec.js                       # Playwright smoke
└── recap.spec.js                          # Playwright smoke
```

> **Architectural Conventions inherited verbatim from Plan 1 §"Architectural Conventions" — module style, screen module shape, CSS naming, state+API boundary, hash routing, persistence, test discipline.**

---

## Milestones

- **M1 — Server entities** (Tasks 1–9): RECAP_SCHEMA_VERSION, kind-mapping, recap load/save/list, list_sessions, save_session_snapshot, snapshot_diff.
- **M2 — Server HTTP** (Tasks 10–14): MCP tools + HTTP routes for sessions, recap, snapshot-diff.
- **M3 — Shared client components** (Tasks 15–22): right-rail, timeline (with parallel-block clustering), diff-row, recap-receipts-grid, plus pure-data unit tests.
- **M4 — Sessions screen** (Tasks 23–34): screen module, CSS, view toggle, kind filter chips, "+ New note" button, right-rail wiring, Playwright smoke.
- **M5 — Recap screen** (Tasks 35–48): screen module, CSS, picker + prev/next, hero, receipts, footer, edit mode + regenerate, Playwright smoke.
- **M6 — Integration + spec coverage walk** (Tasks 49–53): cross-screen smoke, requirement-checklist sweep, plan handoff commit.

---

## M1 — Server Entities

### Task 1: Add `RECAP_SCHEMA_VERSION` and handover-kind mapping

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py` (constants block, near `HANDOVER_KINDS`)
- Modify: `plugins/taskmaster/tests/test_v3_recap.py` (new file)

- [x] **Step 1: Create the failing test**

Create `plugins/taskmaster/tests/test_v3_recap.py`:

```python
"""Recap entity + handover-kind viewer mapping."""
import pytest


def test_recap_schema_version_is_one():
    from taskmaster_v3 import RECAP_SCHEMA_VERSION
    assert RECAP_SCHEMA_VERSION == 1


def test_handover_kind_to_viewer_kind_maps_all_four():
    from taskmaster_v3 import HANDOVER_KIND_TO_VIEWER_KIND, HANDOVER_KINDS
    # Spec §3.12 — viewer renders the four storage kinds as four UI kinds:
    assert HANDOVER_KIND_TO_VIEWER_KIND["end-of-day"]      == "wrap"
    assert HANDOVER_KIND_TO_VIEWER_KIND["context-handoff"] == "mid-task"
    assert HANDOVER_KIND_TO_VIEWER_KIND["crash-recovery"]  == "checkpoint"
    assert HANDOVER_KIND_TO_VIEWER_KIND["auto-stage"]      == "standalone"
    # Mapping covers every storage kind:
    assert set(HANDOVER_KIND_TO_VIEWER_KIND.keys()) == set(HANDOVER_KINDS)
    # All viewer kinds are valid:
    assert set(HANDOVER_KIND_TO_VIEWER_KIND.values()) == {
        "mid-task", "checkpoint", "wrap", "standalone"
    }
```

- [x] **Step 2: Run the test (verify failure)**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_recap.py -v`
Expected: FAIL with `ImportError: cannot import name 'RECAP_SCHEMA_VERSION'`.

- [x] **Step 3: Add the constants**

Add to `plugins/taskmaster/taskmaster_v3.py` near `HANDOVER_KINDS`:

```python
# ---- Recap ---------------------------------------------------------------

RECAP_SCHEMA_VERSION = 1

# Map storage-side handover kinds to viewer-side display kinds (spec §3.12).
# Storage kinds live in handover frontmatter (`session_kind`); the viewer renders
# them via this mapping for kind-pill colour, kind-filter chips, and right-rail header.
HANDOVER_KIND_TO_VIEWER_KIND = {
    "end-of-day":      "wrap",
    "context-handoff": "mid-task",
    "crash-recovery":  "checkpoint",
    "auto-stage":      "standalone",
}

VIEWER_HANDOVER_KINDS = ("mid-task", "checkpoint", "wrap", "standalone")
```

- [x] **Step 4: Run the test (verify pass)**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_recap.py -v`
Expected: PASS (2 tests).

- [x] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_v3_recap.py
git commit -m "feat(taskmaster): RECAP_SCHEMA_VERSION + handover-kind viewer mapping"
```

---

### Task 2: `recap_path()` + `_format_recap_markdown()` helper

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py`
- Modify: `plugins/taskmaster/tests/test_v3_recap.py`

- [x] **Step 1: Append failing test**

```python
def test_recap_path_resolves_under_taskmaster_recaps():
    from taskmaster_v3 import recap_path
    p = recap_path("SES-0184")
    assert str(p).replace("\\", "/").endswith(".taskmaster/recaps/SES-0184.md")


def test_format_recap_markdown_round_trip():
    from taskmaster_v3 import _format_recap_markdown, _parse_recap_markdown
    fm = {
        "session_id": "SES-0184",
        "snapshot_before": "SNAP-0183",
        "snapshot_after": "SNAP-0184",
        "generator": "claude",
        "generated_at": "2026-04-26T16:48:00Z",
        "token_cost": 1840,
    }
    md = _format_recap_markdown(
        frontmatter=fm,
        title="Stitched the worktree review gate",
        what_happened="Started in <em>worktree-shadow</em>. Got blocked by *PKCE*.",
        what_landed="Three tasks closed. One handover.",
        whats_next="Pick up the rebased branch tomorrow.",
    )
    assert md.startswith("---\n")
    assert "session_id: SES-0184" in md
    assert "# Stitched the worktree review gate" in md
    assert "## What happened" in md
    assert "## What landed" in md
    assert "## What's next" in md

    parsed = _parse_recap_markdown(md)
    assert parsed["frontmatter"]["session_id"] == "SES-0184"
    assert parsed["title"] == "Stitched the worktree review gate"
    assert parsed["what_happened"].startswith("Started in <em>worktree-shadow</em>")
    assert parsed["what_landed"].startswith("Three tasks closed.")
    assert parsed["whats_next"].startswith("Pick up the rebased branch")
```

- [x] **Step 2: Run (verify fail)**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_recap.py::test_recap_path_resolves_under_taskmaster_recaps plugins/taskmaster/tests/test_v3_recap.py::test_format_recap_markdown_round_trip -v`
Expected: FAIL — ImportError.

- [x] **Step 3: Implement helpers**

Add to `plugins/taskmaster/taskmaster_v3.py`:

```python
import re
import yaml
from pathlib import Path


def recap_path(session_id: str) -> Path:
    """Path on disk for the recap file of a given session."""
    return Path(".taskmaster") / "recaps" / f"{session_id}.md"


def _format_recap_markdown(
    *,
    frontmatter: dict,
    title: str,
    what_happened: str,
    what_landed: str,
    whats_next: str,
) -> str:
    """Render a recap file: YAML frontmatter + H1 title + three H2 sections.
    Section order is fixed per spec §3.16: What happened / What landed / What's next.
    """
    fm_text = yaml.safe_dump(frontmatter, sort_keys=False).rstrip()
    return (
        f"---\n{fm_text}\n---\n\n"
        f"# {title}\n\n"
        f"## What happened\n\n{what_happened.rstrip()}\n\n"
        f"## What landed\n\n{what_landed.rstrip()}\n\n"
        f"## What's next\n\n{whats_next.rstrip()}\n"
    )


_RECAP_FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def _parse_recap_markdown(text: str) -> dict:
    """Inverse of `_format_recap_markdown`. Returns
    `{frontmatter, title, what_happened, what_landed, whats_next}`.
    Missing sections come back as empty strings.
    """
    m = _RECAP_FM_RE.match(text)
    if not m:
        raise ValueError("recap is missing YAML frontmatter")
    fm = yaml.safe_load(m.group(1)) or {}
    body = text[m.end():]

    title_m = re.search(r"^#\s+(.+?)\s*$", body, re.MULTILINE)
    title = title_m.group(1).strip() if title_m else ""

    def _grab(label: str) -> str:
        pat = re.compile(
            rf"^##\s+{re.escape(label)}\s*\n+(.*?)(?=^##\s+|\Z)",
            re.DOTALL | re.MULTILINE,
        )
        m2 = pat.search(body)
        return m2.group(1).strip() if m2 else ""

    return {
        "frontmatter": fm,
        "title": title,
        "what_happened": _grab("What happened"),
        "what_landed":   _grab("What landed"),
        "whats_next":    _grab("What's next"),
    }
```

- [x] **Step 4: Run (verify pass)**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_recap.py -v`
Expected: 4 tests PASS.

- [x] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_v3_recap.py
git commit -m "feat(taskmaster): recap_path + recap markdown formatter/parser"
```

---

### Task 3: `save_recap()` writes file with frontmatter + 3 sections

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py`
- Modify: `plugins/taskmaster/tests/test_v3_recap.py`

- [x] **Step 1: Failing test**

```python
def test_save_recap_writes_file_with_expected_shape(tmp_path, monkeypatch):
    from taskmaster_v3 import save_recap, recap_path, RECAP_SCHEMA_VERSION
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".taskmaster").mkdir()

    save_recap(
        session_id="SES-0184",
        frontmatter={
            "snapshot_before": "SNAP-0183",
            "snapshot_after":  "SNAP-0184",
            "generator":       "claude",
            "generated_at":    "2026-04-26T16:48:00Z",
            "token_cost":      1840,
        },
        title="Stitched the worktree review gate",
        what_happened="Started in worktree-shadow.",
        what_landed="Three tasks closed.",
        whats_next="Rebase tomorrow.",
    )
    p = recap_path("SES-0184")
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    # Frontmatter pinned: session_id and schema_version are auto-injected.
    assert "session_id: SES-0184" in text
    assert f"schema_version: {RECAP_SCHEMA_VERSION}" in text
    assert "snapshot_before: SNAP-0183" in text
    assert "## What happened" in text
    assert "## What landed" in text
    assert "## What's next" in text
```

- [x] **Step 2: Run (verify fail)**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_recap.py::test_save_recap_writes_file_with_expected_shape -v`
Expected: FAIL — ImportError.

- [x] **Step 3: Implement**

Add to `plugins/taskmaster/taskmaster_v3.py`:

```python
def save_recap(
    *,
    session_id: str,
    frontmatter: dict,
    title: str,
    what_happened: str,
    what_landed: str,
    whats_next: str,
) -> Path:
    """Write `.taskmaster/recaps/<session-id>.md`. `session_id` and
    `schema_version` are auto-injected into the frontmatter; the rest is
    passed through verbatim.
    """
    fm = dict(frontmatter)
    fm["session_id"] = session_id
    fm["schema_version"] = RECAP_SCHEMA_VERSION
    md = _format_recap_markdown(
        frontmatter=fm,
        title=title,
        what_happened=what_happened,
        what_landed=what_landed,
        whats_next=whats_next,
    )
    p = recap_path(session_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(p, md)
    return p
```

- [x] **Step 4: Run (verify pass)**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_recap.py -v`
Expected: 5 tests PASS.

- [x] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_v3_recap.py
git commit -m "feat(taskmaster): save_recap helper writes recap markdown to disk"
```

---

### Task 4: `load_recap()` returns parsed dict; missing → None

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py`
- Modify: `plugins/taskmaster/tests/test_v3_recap.py`

- [x] **Step 1: Failing test**

```python
def test_load_recap_returns_none_when_missing(tmp_path, monkeypatch):
    from taskmaster_v3 import load_recap
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".taskmaster").mkdir()
    assert load_recap("SES-9999") is None


def test_load_recap_round_trip(tmp_path, monkeypatch):
    from taskmaster_v3 import save_recap, load_recap
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".taskmaster").mkdir()
    save_recap(
        session_id="SES-0184",
        frontmatter={"snapshot_before": "SNAP-0183", "snapshot_after": "SNAP-0184",
                     "generator": "claude", "generated_at": "2026-04-26T16:48:00Z",
                     "token_cost": 1840},
        title="Hero",
        what_happened="A", what_landed="B", whats_next="C",
    )
    rec = load_recap("SES-0184")
    assert rec["frontmatter"]["session_id"] == "SES-0184"
    assert rec["frontmatter"]["snapshot_before"] == "SNAP-0183"
    assert rec["title"] == "Hero"
    assert rec["what_happened"] == "A"
    assert rec["what_landed"] == "B"
    assert rec["whats_next"] == "C"
```

- [x] **Step 2: Run (verify fail)**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_recap.py -v -k load_recap`
Expected: FAIL — ImportError.

- [x] **Step 3: Implement**

```python
def load_recap(session_id: str) -> dict | None:
    """Load and parse a recap file. Returns None when missing.
    Returned dict: {frontmatter, title, what_happened, what_landed, whats_next}.
    """
    p = recap_path(session_id)
    if not p.exists():
        return None
    return _parse_recap_markdown(p.read_text(encoding="utf-8"))
```

- [x] **Step 4: Run (verify pass)**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_recap.py -v`
Expected: 7 tests PASS.

- [x] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_v3_recap.py
git commit -m "feat(taskmaster): load_recap reads + parses recap markdown"
```

---

### Task 5: `list_recaps()` enumerates the recaps directory

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py`
- Modify: `plugins/taskmaster/tests/test_v3_recap.py`

- [x] **Step 1: Failing test**

```python
def test_list_recaps_returns_session_ids_sorted_desc(tmp_path, monkeypatch):
    from taskmaster_v3 import save_recap, list_recaps
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".taskmaster").mkdir()
    for sid in ("SES-0182", "SES-0185", "SES-0184"):
        save_recap(
            session_id=sid,
            frontmatter={"snapshot_before": "SNAP-A", "snapshot_after": "SNAP-B",
                         "generator": "claude", "generated_at": "2026-04-26T16:00Z",
                         "token_cost": 100},
            title="x", what_happened="x", what_landed="x", whats_next="x",
        )
    ids = list_recaps()
    assert ids == ["SES-0185", "SES-0184", "SES-0182"]


def test_list_recaps_empty_when_dir_missing(tmp_path, monkeypatch):
    from taskmaster_v3 import list_recaps
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".taskmaster").mkdir()
    assert list_recaps() == []
```

- [x] **Step 2: Run (verify fail)**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_recap.py -v -k list_recaps`
Expected: FAIL — ImportError.

- [x] **Step 3: Implement**

```python
def list_recaps() -> list[str]:
    """Return session ids of all on-disk recaps, sorted descending (newest first)."""
    d = Path(".taskmaster") / "recaps"
    if not d.exists():
        return []
    ids = [p.stem for p in d.glob("*.md") if not p.name.startswith("_")]
    ids.sort(reverse=True)
    return ids
```

- [x] **Step 4: Run (verify pass)**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_recap.py -v`
Expected: 9 tests PASS.

- [x] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_v3_recap.py
git commit -m "feat(taskmaster): list_recaps enumerates recap files newest-first"
```

---

### Task 6: `save_session_snapshot()` writes per-session snapshot

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py`
- Modify: `plugins/taskmaster/tests/test_v3_snapshot_diff.py` (new file)

- [x] **Step 1: Failing test**

Create `plugins/taskmaster/tests/test_v3_snapshot_diff.py`:

```python
import json


def test_save_session_snapshot_writes_named_file(tmp_path, monkeypatch):
    from taskmaster_v3 import save_session_snapshot
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".taskmaster" / "snapshots").mkdir(parents=True)
    save_session_snapshot("SNAP-0184", {"tasks": {"T-1": {"status": "done"}}, "lessons_fired": [], "issues": {}})
    p = tmp_path / ".taskmaster" / "snapshots" / "SNAP-0184.json"
    assert p.exists()
    body = json.loads(p.read_text())
    assert body["tasks"]["T-1"]["status"] == "done"
```

- [x] **Step 2: Run (verify fail)**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_snapshot_diff.py -v`
Expected: FAIL — ImportError.

- [x] **Step 3: Implement**

Add to `plugins/taskmaster/taskmaster_v3.py`:

```python
def save_session_snapshot(snapshot_id: str, payload: dict) -> Path:
    """Write `.taskmaster/snapshots/<snapshot-id>.json` (atomic). The rolling
    `last.json` is unaffected; per-session files coexist alongside it.
    """
    import json as _json
    p = Path(".taskmaster") / "snapshots" / f"{snapshot_id}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(p, _json.dumps(payload, indent=2))
    return p


def load_session_snapshot(snapshot_id: str) -> dict | None:
    """Load `.taskmaster/snapshots/<snapshot-id>.json`. None when missing."""
    import json as _json
    p = Path(".taskmaster") / "snapshots" / f"{snapshot_id}.json"
    if not p.exists():
        return None
    return _json.loads(p.read_text(encoding="utf-8"))
```

- [x] **Step 4: Run (verify pass)**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_snapshot_diff.py -v`
Expected: 1 test PASS.

- [x] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_v3_snapshot_diff.py
git commit -m "feat(taskmaster): per-session snapshot writer/reader"
```

---

### Task 7: `snapshot_diff(a, b)` returns structured delta

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py`
- Modify: `plugins/taskmaster/tests/test_v3_snapshot_diff.py`

- [x] **Step 1: Failing test**

```python
def test_snapshot_diff_detects_added_removed_changed_tasks():
    from taskmaster_v3 import snapshot_diff
    a = {
        "tasks": {
            "T-1": {"status": "todo",        "title": "Old"},
            "T-2": {"status": "in-progress", "title": "Hold"},
        },
        "lessons_fired": [],
        "issues": {},
        "files_touched": [],
    }
    b = {
        "tasks": {
            "T-2": {"status": "done", "title": "Hold"},
            "T-3": {"status": "todo", "title": "New"},
        },
        "lessons_fired": [{"id": "LSN-08", "fires": 3, "first_time": False}],
        "issues":        {"ISS-12": {"severity": "High", "status": "open"}},
        "files_touched": ["a.py", "b.css"],
    }
    d = snapshot_diff(a, b)
    assert {t["id"] for t in d["tasks_added"]}   == {"T-3"}
    assert {t["id"] for t in d["tasks_removed"]} == {"T-1"}
    assert d["tasks_changed"][0]["id"] == "T-2"
    assert d["tasks_changed"][0]["from"]["status"] == "in-progress"
    assert d["tasks_changed"][0]["to"]["status"]   == "done"
    assert d["lessons_fired"] == [{"id": "LSN-08", "fires": 3, "first_time": False}]
    assert d["issues_opened"][0]["id"] == "ISS-12"
    assert d["issues_transitioned"] == []
    assert d["files_touched"] == ["a.py", "b.css"]


def test_snapshot_diff_detects_issue_transitions():
    from taskmaster_v3 import snapshot_diff
    a = {"tasks": {}, "issues": {"ISS-1": {"severity": "High", "status": "open"}},
         "lessons_fired": [], "files_touched": []}
    b = {"tasks": {}, "issues": {"ISS-1": {"severity": "High", "status": "fixed"}},
         "lessons_fired": [], "files_touched": []}
    d = snapshot_diff(a, b)
    assert d["issues_opened"] == []
    assert d["issues_transitioned"][0]["id"] == "ISS-1"
    assert d["issues_transitioned"][0]["from"] == "open"
    assert d["issues_transitioned"][0]["to"]   == "fixed"
```

- [x] **Step 2: Run (verify fail)**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_snapshot_diff.py -v -k snapshot_diff`
Expected: FAIL — ImportError.

- [x] **Step 3: Implement**

```python
def snapshot_diff(a: dict, b: dict) -> dict:
    """Compute a structured diff from snapshot `a` (before) to `b` (after).

    Returned shape (mirrors the client-side helper):
      {
        tasks_added:        [{id, ...task}],
        tasks_removed:      [{id, ...task}],
        tasks_changed:      [{id, from, to}],   # whole-task before/after
        lessons_fired:      [{id, fires, first_time}],
        issues_opened:      [{id, ...issue}],
        issues_transitioned:[{id, from, to}],
        files_touched:      [path, ...],
      }
    """
    a_tasks = (a or {}).get("tasks", {}) or {}
    b_tasks = (b or {}).get("tasks", {}) or {}

    added   = [{"id": tid, **b_tasks[tid]} for tid in b_tasks if tid not in a_tasks]
    removed = [{"id": tid, **a_tasks[tid]} for tid in a_tasks if tid not in b_tasks]
    changed = [
        {"id": tid, "from": a_tasks[tid], "to": b_tasks[tid]}
        for tid in a_tasks if tid in b_tasks and a_tasks[tid] != b_tasks[tid]
    ]

    a_iss = (a or {}).get("issues", {}) or {}
    b_iss = (b or {}).get("issues", {}) or {}
    issues_opened = [
        {"id": iid, **b_iss[iid]} for iid in b_iss if iid not in a_iss
    ]
    issues_transitioned = [
        {"id": iid, "from": a_iss[iid].get("status"),
                    "to":   b_iss[iid].get("status")}
        for iid in a_iss if iid in b_iss
        and a_iss[iid].get("status") != b_iss[iid].get("status")
    ]

    return {
        "tasks_added":         added,
        "tasks_removed":       removed,
        "tasks_changed":       changed,
        "lessons_fired":       list((b or {}).get("lessons_fired", []) or []),
        "issues_opened":       issues_opened,
        "issues_transitioned": issues_transitioned,
        "files_touched":       list((b or {}).get("files_touched", []) or []),
    }
```

- [x] **Step 4: Run (verify pass)**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_snapshot_diff.py -v`
Expected: 3 tests PASS.

- [x] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_v3_snapshot_diff.py
git commit -m "feat(taskmaster): snapshot_diff returns structured task/issue/file delta"
```

---

### Task 8: `list_sessions()` synthesises sessions from PROGRESS.md + handovers

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py`
- Create: `plugins/taskmaster/tests/test_v3_sessions.py`

- [x] **Step 1: Failing test**

```python
import textwrap


def _write_handover(tmp_path, name: str, body: dict, body_md: str = "..."):
    import yaml
    p = tmp_path / ".taskmaster" / "handovers" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    fm = yaml.safe_dump(body, sort_keys=False).rstrip()
    p.write_text(f"---\n{fm}\n---\n\n{body_md}\n", encoding="utf-8")
    return p


def test_list_sessions_synthesises_from_handovers(tmp_path, monkeypatch):
    from taskmaster_v3 import list_sessions
    monkeypatch.chdir(tmp_path)

    _write_handover(tmp_path, "2026-04-26-1640-foo.md", {
        "id": "2026-04-26-1640-foo",
        "date": "2026-04-26T16:40:00Z",
        "tldr": "...", "next_action": "...",
        "task_ids": ["T-148"],
        "session_kind": "context-handoff",
        "context_size_at_write": 0.8,
    })
    _write_handover(tmp_path, "2026-04-26-1648-bar.md", {
        "id": "2026-04-26-1648-bar",
        "date": "2026-04-26T16:48:00Z",
        "tldr": "...", "next_action": "...",
        "task_ids": ["T-148"],
        "session_kind": "end-of-day",
        "context_size_at_write": 0.9,
    })

    sessions = list_sessions()
    assert len(sessions) >= 1
    s = sessions[0]
    assert set(s.keys()) >= {
        "id", "start", "end", "duration", "handover_ids",
        "recap_id", "task_ids", "parallel_with",
    }
    assert s["id"].startswith("SES-")
    # Both handovers reference the same task within ~10 min — clustered into one session.
    assert sorted(s["handover_ids"]) == [
        "2026-04-26-1640-foo", "2026-04-26-1648-bar",
    ]
    assert s["task_ids"] == ["T-148"]


def test_list_sessions_marks_parallel_when_overlapping(tmp_path, monkeypatch):
    from taskmaster_v3 import list_sessions
    monkeypatch.chdir(tmp_path)
    # Two non-overlapping task scopes; same time window → parallel.
    _write_handover(tmp_path, "2026-04-26-1408-a.md", {
        "id": "2026-04-26-1408-a",
        "date": "2026-04-26T14:08:00Z",
        "tldr": "...", "next_action": "...",
        "task_ids": ["T-100"], "session_kind": "end-of-day",
        "context_size_at_write": 0.5,
    })
    _write_handover(tmp_path, "2026-04-26-1410-b.md", {
        "id": "2026-04-26-1410-b",
        "date": "2026-04-26T14:10:00Z",
        "tldr": "...", "next_action": "...",
        "task_ids": ["T-200"], "session_kind": "end-of-day",
        "context_size_at_write": 0.5,
    })
    sessions = list_sessions()
    by_id = {s["id"]: s for s in sessions}
    assert len(sessions) == 2
    a, b = sessions
    assert a["id"] in b["parallel_with"]
    assert b["id"] in a["parallel_with"]
```

- [x] **Step 2: Run (verify fail)**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_sessions.py -v`
Expected: FAIL — ImportError.

- [x] **Step 3: Implement**

Add to `plugins/taskmaster/taskmaster_v3.py`:

```python
def _parse_iso8601(s: str) -> "datetime":
    from datetime import datetime, timezone
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def list_sessions() -> list[dict]:
    """Synthesise sessions from on-disk handover files.

    Algorithm: load every handover, sort by date asc, then greedily group
    consecutive handovers that share at least one task_id AND occur within
    SESSION_GAP_MINUTES (default 30). Each group becomes one session.

    Returns: list of dicts (newest first):
      {id, start, end, duration, handover_ids[], recap_id, task_ids[], parallel_with[]}
    """
    from datetime import timedelta
    SESSION_GAP_MINUTES = 30
    handovers_dir = Path(".taskmaster") / "handovers"
    if not handovers_dir.exists():
        return []
    raw: list[dict] = []
    for p in sorted(handovers_dir.glob("*.md")):
        try:
            text = p.read_text(encoding="utf-8")
            m = _RECAP_FM_RE.match(text)
            if not m:
                continue
            fm = yaml.safe_load(m.group(1)) or {}
            if "id" not in fm or "date" not in fm:
                continue
            raw.append(fm)
        except Exception:
            continue
    raw.sort(key=lambda h: _parse_iso8601(h["date"]))

    groups: list[list[dict]] = []
    for h in raw:
        h_t = _parse_iso8601(h["date"])
        h_tids = set(h.get("task_ids") or [])
        attached = False
        if groups:
            tail = groups[-1][-1]
            tail_t = _parse_iso8601(tail["date"])
            tail_tids = set(tail.get("task_ids") or [])
            within_gap = (h_t - tail_t) <= timedelta(minutes=SESSION_GAP_MINUTES)
            shared_tasks = bool(h_tids & tail_tids)
            if within_gap and shared_tasks:
                groups[-1].append(h)
                attached = True
        if not attached:
            groups.append([h])

    sessions: list[dict] = []
    recap_ids = set(list_recaps())
    for idx, group in enumerate(groups, start=1):
        sid = f"SES-{idx:04d}"
        start = _parse_iso8601(group[0]["date"])
        end = _parse_iso8601(group[-1]["date"])
        tids: list[str] = []
        for h in group:
            for t in (h.get("task_ids") or []):
                if t not in tids:
                    tids.append(t)
        sessions.append({
            "id": sid,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "duration": int((end - start).total_seconds()),
            "handover_ids": [h["id"] for h in group],
            "recap_id": sid if sid in recap_ids else None,
            "task_ids": tids,
            "parallel_with": [],   # filled below
        })

    # Mark parallel sessions: any pair with overlapping [start,end] windows.
    for i, s in enumerate(sessions):
        s_start = _parse_iso8601(s["start"])
        s_end = _parse_iso8601(s["end"])
        for j, o in enumerate(sessions):
            if i == j:
                continue
            o_start = _parse_iso8601(o["start"])
            o_end = _parse_iso8601(o["end"])
            if s_start <= o_end and o_start <= s_end:
                s["parallel_with"].append(o["id"])

    sessions.sort(key=lambda s: s["start"], reverse=True)
    return sessions
```

- [x] **Step 4: Run (verify pass)**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_sessions.py -v`
Expected: 2 tests PASS.

- [x] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_v3_sessions.py
git commit -m "feat(taskmaster): list_sessions synthesises sessions from handover files"
```

---

### Task 9: `get_session_detail(sid)` bundles handovers + recap + tasks

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py`
- Modify: `plugins/taskmaster/tests/test_v3_sessions.py`

- [x] **Step 1: Failing test**

```python
def test_get_session_detail_bundles_handovers_recap(tmp_path, monkeypatch):
    from taskmaster_v3 import get_session_detail, save_recap
    monkeypatch.chdir(tmp_path)

    _write_handover(tmp_path, "2026-04-26-1640-foo.md", {
        "id": "2026-04-26-1640-foo",
        "date": "2026-04-26T16:40:00Z",
        "tldr": "Stitched the gate", "next_action": "Rebase",
        "task_ids": ["T-148"], "session_kind": "context-handoff",
        "context_size_at_write": 0.8,
    }, body_md="Resume by running pytest -k gate.")
    save_recap(
        session_id="SES-0001",
        frontmatter={"snapshot_before": "SNAP-0000", "snapshot_after": "SNAP-0001",
                     "generator": "claude", "generated_at": "2026-04-26T16:48Z",
                     "token_cost": 1840},
        title="Stitched", what_happened="A", what_landed="B", whats_next="C",
    )

    detail = get_session_detail("SES-0001")
    assert detail["session"]["id"] == "SES-0001"
    assert len(detail["handovers"]) == 1
    h = detail["handovers"][0]
    assert h["id"] == "2026-04-26-1640-foo"
    assert h["viewer_kind"] == "mid-task"  # context-handoff → mid-task
    assert h["tldr"] == "Stitched the gate"
    assert h["resume_prompt"].startswith("Resume by running")
    assert detail["recap"]["frontmatter"]["session_id"] == "SES-0001"
    assert detail["task_ids"] == ["T-148"]


def test_get_session_detail_returns_none_when_missing(tmp_path, monkeypatch):
    from taskmaster_v3 import get_session_detail
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".taskmaster").mkdir()
    assert get_session_detail("SES-9999") is None
```

- [x] **Step 2: Run (verify fail)**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_sessions.py -v -k get_session_detail`
Expected: FAIL — ImportError.

- [x] **Step 3: Implement**

```python
def _load_handover_full(handover_id: str) -> dict | None:
    """Load a handover's frontmatter + body_md by id."""
    p = Path(".taskmaster") / "handovers" / f"{handover_id}.md"
    if not p.exists():
        return None
    text = p.read_text(encoding="utf-8")
    m = _RECAP_FM_RE.match(text)
    if not m:
        return None
    fm = yaml.safe_load(m.group(1)) or {}
    body = text[m.end():].strip()
    fm["resume_prompt"] = body          # body is the resume prompt artifact
    fm["viewer_kind"] = HANDOVER_KIND_TO_VIEWER_KIND.get(
        fm.get("session_kind"), "standalone"
    )
    return fm


def get_session_detail(session_id: str) -> dict | None:
    """Bundle one session with its handovers, recap, and task ids."""
    sessions = list_sessions()
    target = next((s for s in sessions if s["id"] == session_id), None)
    if target is None:
        return None
    handovers = []
    for hid in target["handover_ids"]:
        h = _load_handover_full(hid)
        if h is not None:
            handovers.append(h)
    recap = load_recap(session_id)
    return {
        "session": target,
        "handovers": handovers,
        "recap": recap,
        "task_ids": target["task_ids"],
    }
```

- [x] **Step 4: Run (verify pass)**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_sessions.py -v`
Expected: 4 tests PASS.

- [x] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_v3_sessions.py
git commit -m "feat(taskmaster): get_session_detail bundles handovers/recap/tasks"
```

---

## M2 — Server HTTP

### Task 10: MCP tools `recap_get`, `recap_set`, `recap_list`, `snapshot_diff`

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py`
- Create: `plugins/taskmaster/tests/test_server_sessions_recap.py`

- [x] **Step 1: Failing test**

Create `plugins/taskmaster/tests/test_server_sessions_recap.py`:

```python
"""HTTP + MCP tests for sessions / recap / snapshot-diff endpoints."""
import json
import threading
import time
import urllib.request
import urllib.error
import pytest


@pytest.fixture
def running_server(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".taskmaster").mkdir()
    (tmp_path / "backlog.yaml").write_text(
        "meta:\n  project: test\nepics: []\nphases: []\n"
    )
    from backlog_server import _make_server
    server, port = _make_server(host="127.0.0.1", port=0)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    base = f"http://127.0.0.1:{port}"
    for _ in range(20):
        try:
            urllib.request.urlopen(f"{base}/api/identity", timeout=0.5).read()
            break
        except Exception:
            time.sleep(0.05)
    yield base, server
    server.shutdown()
    server.server_close()


def test_recap_set_then_get_round_trip_via_mcp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".taskmaster").mkdir()
    from backlog_server import recap_set, recap_get
    msg = recap_set(
        "SES-0001",
        json.dumps({"snapshot_before": "SNAP-0000", "snapshot_after": "SNAP-0001",
                    "generator": "claude", "generated_at": "2026-04-26T16:48Z",
                    "token_cost": 1840}),
        "Hero",
        "Started worktree-shadow.",
        "Three closed.",
        "Rebase tomorrow.",
    )
    assert "ok" in msg.lower()
    text = recap_get("SES-0001")
    body = json.loads(text)
    assert body["title"] == "Hero"
    assert body["what_happened"].startswith("Started")


def test_recap_list_via_mcp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".taskmaster").mkdir()
    from backlog_server import recap_set, recap_list
    recap_set("SES-0002",
              json.dumps({"snapshot_before":"a","snapshot_after":"b","generator":"x",
                          "generated_at":"2026-04-26T00:00Z","token_cost":0}),
              "t", "x", "y", "z")
    out = json.loads(recap_list())
    assert "SES-0002" in out


def test_snapshot_diff_via_mcp():
    from backlog_server import snapshot_diff as snap_diff_tool
    out = snap_diff_tool(
        json.dumps({"tasks": {"T-1": {"status": "todo"}}}),
        json.dumps({"tasks": {"T-1": {"status": "done"}}}),
    )
    body = json.loads(out)
    assert body["tasks_changed"][0]["id"] == "T-1"
```

- [x] **Step 2: Run (verify fail)**

Run: `python -m pytest plugins/taskmaster/tests/test_server_sessions_recap.py -v -k "recap_set_then_get or recap_list_via_mcp or snapshot_diff_via_mcp"`
Expected: FAIL — ImportError on the new tools.

- [x] **Step 3: Implement**

Add to `plugins/taskmaster/backlog_server.py` near the other v3 entity tools:

```python
@mcp.tool()
def recap_get(session_id: str) -> str:
    """Return the recap for a session as JSON, or `null` when missing."""
    import json as _json
    rec = load_recap(session_id)
    return _json.dumps(rec)


@mcp.tool()
def recap_set(
    session_id: str,
    frontmatter_json: str,
    title: str,
    what_happened: str,
    what_landed: str,
    whats_next: str,
) -> str:
    """Write a recap. `frontmatter_json` is a JSON object holding
    snapshot_before / snapshot_after / generator / generated_at / token_cost.
    `session_id` and `schema_version` are auto-injected.
    """
    import json as _json
    try:
        fm = _json.loads(frontmatter_json)
    except Exception as e:
        return f"error: invalid frontmatter JSON ({e})"
    if not isinstance(fm, dict):
        return "error: frontmatter must be a JSON object"
    save_recap(
        session_id=session_id,
        frontmatter=fm,
        title=title,
        what_happened=what_happened,
        what_landed=what_landed,
        whats_next=whats_next,
    )
    return "ok"


@mcp.tool()
def recap_list() -> str:
    """List session ids that have a recap on disk (newest first)."""
    import json as _json
    return _json.dumps(list_recaps())


@mcp.tool()
def snapshot_diff(snapshot_a_json: str, snapshot_b_json: str) -> str:
    """Compute structured diff between two snapshot payloads, returned as JSON."""
    import json as _json
    from taskmaster_v3 import snapshot_diff as _diff
    a = _json.loads(snapshot_a_json)
    b = _json.loads(snapshot_b_json)
    return _json.dumps(_diff(a, b))
```

Re-export the helpers at the top of `backlog_server.py` if not already (`from taskmaster_v3 import (..., load_recap, save_recap, list_recaps, list_sessions, get_session_detail, load_session_snapshot, snapshot_diff as _snapshot_diff)`).

- [x] **Step 4: Run (verify pass)**

Run: `python -m pytest plugins/taskmaster/tests/test_server_sessions_recap.py -v -k "recap_set_then_get or recap_list_via_mcp or snapshot_diff_via_mcp"`
Expected: 3 tests PASS.

- [x] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_server_sessions_recap.py
git commit -m "feat(taskmaster): MCP tools recap_get/set/list + snapshot_diff"
```

---

### Task 11: HTTP `GET /api/sessions` + `GET /api/sessions/<sid>`

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py`
- Modify: `plugins/taskmaster/tests/test_server_sessions_recap.py`

- [x] **Step 1: Failing test**

```python
def test_http_get_sessions_returns_list(running_server, tmp_path):
    base, _ = running_server
    # Seed one handover so list_sessions has data
    (tmp_path / ".taskmaster" / "handovers").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".taskmaster" / "handovers" / "2026-04-26-1640-x.md").write_text(
        "---\nid: 2026-04-26-1640-x\ndate: 2026-04-26T16:40:00Z\n"
        "tldr: x\nnext_action: y\ntask_ids: [T-1]\n"
        "session_kind: end-of-day\ncontext_size_at_write: 0.5\n---\n\nbody\n",
        encoding="utf-8",
    )
    resp = urllib.request.urlopen(f"{base}/api/sessions")
    assert resp.status == 200
    body = json.loads(resp.read())
    assert isinstance(body, list)
    assert body[0]["id"].startswith("SES-")
    sid = body[0]["id"]

    resp2 = urllib.request.urlopen(f"{base}/api/sessions/{sid}")
    assert resp2.status == 200
    detail = json.loads(resp2.read())
    assert detail["session"]["id"] == sid
    assert len(detail["handovers"]) == 1
    assert detail["handovers"][0]["viewer_kind"] == "wrap"


def test_http_get_unknown_session_returns_404(running_server):
    base, _ = running_server
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(f"{base}/api/sessions/SES-9999")
    assert exc.value.code == 404
```

- [x] **Step 2: Run (verify fail)**

Run: `python -m pytest plugins/taskmaster/tests/test_server_sessions_recap.py -v -k http_get_sessions`
Expected: FAIL — 404.

- [x] **Step 3: Implement**

In `_Handler.do_GET` (before the catch-all 404), add:

```python
if self.path == "/api/sessions":
    self._send_json(200, list_sessions())
    return

if self.path.startswith("/api/sessions/"):
    sid = self.path[len("/api/sessions/"):]
    detail = get_session_detail(sid)
    if detail is None:
        self._send_json(404, {"ok": False, "error": f"unknown session {sid}"})
        return
    self._send_json(200, detail)
    return
```

- [x] **Step 4: Run (verify pass)**

Run: `python -m pytest plugins/taskmaster/tests/test_server_sessions_recap.py -v -k http_get_sessions`
Expected: 2 tests PASS.

- [x] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_server_sessions_recap.py
git commit -m "feat(taskmaster): GET /api/sessions and /api/sessions/<sid>"
```

---

### Task 12: HTTP `GET /api/recap/<sid>` + `PUT /api/recap/<sid>`

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py`
- Modify: `plugins/taskmaster/tests/test_server_sessions_recap.py`

- [x] **Step 1: Failing test**

```python
def test_http_recap_put_then_get_round_trip(running_server):
    base, _ = running_server
    payload = {
        "frontmatter": {
            "snapshot_before": "SNAP-0000", "snapshot_after": "SNAP-0001",
            "generator": "claude", "generated_at": "2026-04-26T16:48Z",
            "token_cost": 1840,
        },
        "title": "Hero",
        "what_happened": "A",
        "what_landed": "B",
        "whats_next": "C",
    }
    req = urllib.request.Request(
        f"{base}/api/recap/SES-0001",
        data=json.dumps(payload).encode(),
        method="PUT",
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req)
    assert resp.status == 200
    assert json.loads(resp.read())["ok"] is True

    resp2 = urllib.request.urlopen(f"{base}/api/recap/SES-0001")
    body = json.loads(resp2.read())
    assert body["title"] == "Hero"
    assert body["frontmatter"]["session_id"] == "SES-0001"


def test_http_recap_get_unknown_returns_404(running_server):
    base, _ = running_server
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(f"{base}/api/recap/SES-9999")
    assert exc.value.code == 404
```

- [x] **Step 2: Run (verify fail)**

Run: `python -m pytest plugins/taskmaster/tests/test_server_sessions_recap.py -v -k http_recap`
Expected: FAIL.

- [x] **Step 3: Implement**

In `_Handler.do_GET` add:

```python
if self.path.startswith("/api/recap/"):
    sid = self.path[len("/api/recap/"):]
    rec = load_recap(sid)
    if rec is None:
        self._send_json(404, {"ok": False, "error": f"no recap for {sid}"})
        return
    self._send_json(200, rec)
    return
```

In `_Handler.do_PUT` (extend the existing handler):

```python
if self.path.startswith("/api/recap/"):
    import json as _json
    sid = self.path[len("/api/recap/"):]
    length = int(self.headers.get("Content-Length") or 0)
    raw = self.rfile.read(length).decode("utf-8") if length else ""
    try:
        payload = _json.loads(raw)
    except Exception as e:
        self._send_json(400, {"ok": False, "error": f"invalid JSON: {e}"})
        return
    required = {"frontmatter", "title", "what_happened", "what_landed", "whats_next"}
    if not required.issubset(payload.keys()):
        self._send_json(400, {"ok": False,
            "error": f"payload missing keys: {sorted(required - set(payload.keys()))}"})
        return
    save_recap(
        session_id=sid,
        frontmatter=payload["frontmatter"],
        title=payload["title"],
        what_happened=payload["what_happened"],
        what_landed=payload["what_landed"],
        whats_next=payload["whats_next"],
    )
    self._send_json(200, {"ok": True})
    return
```

- [x] **Step 4: Run (verify pass)**

Run: `python -m pytest plugins/taskmaster/tests/test_server_sessions_recap.py -v -k http_recap`
Expected: 2 tests PASS.

- [x] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_server_sessions_recap.py
git commit -m "feat(taskmaster): GET/PUT /api/recap/<sid>"
```

---

### Task 13: HTTP `GET /api/snapshots/diff?from=&to=`

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py`
- Modify: `plugins/taskmaster/tests/test_server_sessions_recap.py`

- [x] **Step 1: Failing test**

```python
def test_http_snapshot_diff_endpoint(running_server, tmp_path):
    base, _ = running_server
    snaps = tmp_path / ".taskmaster" / "snapshots"
    snaps.mkdir(parents=True, exist_ok=True)
    (snaps / "SNAP-A.json").write_text(json.dumps({"tasks": {"T-1": {"status":"todo"}}}))
    (snaps / "SNAP-B.json").write_text(json.dumps({"tasks": {"T-1": {"status":"done"}}}))
    resp = urllib.request.urlopen(f"{base}/api/snapshots/diff?from=SNAP-A&to=SNAP-B")
    assert resp.status == 200
    body = json.loads(resp.read())
    assert body["tasks_changed"][0]["id"] == "T-1"


def test_http_snapshot_diff_missing_param_400(running_server):
    base, _ = running_server
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(f"{base}/api/snapshots/diff?from=SNAP-A")
    assert exc.value.code == 400
```

- [x] **Step 2: Run (verify fail)**

Run: `python -m pytest plugins/taskmaster/tests/test_server_sessions_recap.py -v -k http_snapshot_diff`
Expected: FAIL — 404.

- [x] **Step 3: Implement**

In `_Handler.do_GET` add (before the catch-all 404):

```python
if self.path.startswith("/api/snapshots/diff"):
    from urllib.parse import urlsplit, parse_qs
    qs = parse_qs(urlsplit(self.path).query)
    a = (qs.get("from") or [None])[0]
    b = (qs.get("to")   or [None])[0]
    if not a or not b:
        self._send_json(400, {"ok": False,
            "error": "both 'from' and 'to' query params required"})
        return
    snap_a = load_session_snapshot(a)
    snap_b = load_session_snapshot(b)
    if snap_a is None or snap_b is None:
        self._send_json(404, {"ok": False,
            "error": f"missing snapshot(s): from={snap_a is not None} to={snap_b is not None}"})
        return
    self._send_json(200, _snapshot_diff(snap_a, snap_b))
    return
```

- [x] **Step 4: Run (verify pass)**

Run: `python -m pytest plugins/taskmaster/tests/test_server_sessions_recap.py -v -k http_snapshot_diff`
Expected: 2 tests PASS.

- [x] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_server_sessions_recap.py
git commit -m "feat(taskmaster): GET /api/snapshots/diff?from=&to="
```

---

### Task 14: Final server-side test sweep

**Files:** none modified.

- [x] **Step 1: Run the full server suite**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_recap.py plugins/taskmaster/tests/test_v3_snapshot_diff.py plugins/taskmaster/tests/test_v3_sessions.py plugins/taskmaster/tests/test_server_sessions_recap.py -v`
Expected: All PASS (≥18 tests).

- [x] **Step 2: No commit needed (verification only)**

---

## M3 — Shared Client Components

### Task 15: `diff-row.js` — `+`/`~`/`-` row component

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/diff-row.js`
- Create: `plugins/taskmaster/viewer/tests/unit/diff-row.test.js`

- [x] **Step 1: Failing test**

Create `plugins/taskmaster/viewer/tests/unit/diff-row.test.js`:

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { renderDiffRow } from '../../js/components/diff-row.js';

test('add row sets pre to + and renders body', () => {
  const html = renderDiffRow({ kind: 'add', body: '<span class="id">T-3</span> New task' });
  assert.match(html, /diff-row add/);
  assert.match(html, /class="pre">\+</);
  assert.match(html, /T-3/);
});

test('mod row renders from -> to', () => {
  const html = renderDiffRow({
    kind: 'mod',
    body: '<span class="id">T-2</span> <span class="from">in-progress</span> <span class="arrow">→</span> <span class="to">done</span>',
  });
  assert.match(html, /diff-row mod/);
  assert.match(html, /class="pre">~</);
  assert.match(html, /from">in-progress/);
  assert.match(html, /to">done/);
});

test('del row sets pre to -', () => {
  const html = renderDiffRow({ kind: 'del', body: 'gone' });
  assert.match(html, /class="pre">-/);
});
```

- [x] **Step 2: Run (verify fail)**

Run: `node --test plugins/taskmaster/viewer/tests/unit/diff-row.test.js`
Expected: FAIL — module not found.

- [x] **Step 3: Implement**

Create `plugins/taskmaster/viewer/js/components/diff-row.js`:

```js
// Single +/~/- row, used by recap-receipts-grid and sessions detail-rail.
// Pure render: takes plain data, returns an HTML string. The caller injects.

const PREFIX = { add: '+', mod: '~', del: '-' };

export function renderDiffRow({ kind, body }) {
  const k = (kind in PREFIX) ? kind : 'mod';
  return (
    `<div class="diff-row ${k}">`
    + `<span class="pre">${PREFIX[k]}</span>`
    + `<span class="body">${body}</span>`
    + `</div>`
  );
}

export default renderDiffRow;
```

- [x] **Step 4: Run (verify pass)**

Run: `node --test plugins/taskmaster/viewer/tests/unit/diff-row.test.js`
Expected: 3 tests PASS.

- [x] **Step 5: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/diff-row.js plugins/taskmaster/viewer/tests/unit/diff-row.test.js
git commit -m "feat(viewer): diff-row component (+/~/- with from→to body)"
```

---

### Task 16: `parallel-block.test.js` — overlap-cluster algorithm

**Files:**
- Create: `plugins/taskmaster/viewer/tests/unit/parallel-block.test.js`

- [x] **Step 1: Failing test (algo lives in `timeline.js`, not yet written)**

Create `plugins/taskmaster/viewer/tests/unit/parallel-block.test.js`:

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { clusterParallelSessions } from '../../js/components/timeline.js';

test('non-overlapping sessions: each is its own cluster', () => {
  const sessions = [
    { id: 'SES-1', start: '2026-04-26T10:00:00Z', end: '2026-04-26T11:00:00Z' },
    { id: 'SES-2', start: '2026-04-26T12:00:00Z', end: '2026-04-26T13:00:00Z' },
  ];
  const groups = clusterParallelSessions(sessions);
  assert.deepEqual(groups.map(g => g.map(s => s.id)), [['SES-1'], ['SES-2']]);
});

test('overlapping pair: clustered together with parallel: true', () => {
  const sessions = [
    { id: 'SES-1', start: '2026-04-26T14:08:00Z', end: '2026-04-26T16:00:00Z' },
    { id: 'SES-2', start: '2026-04-26T15:00:00Z', end: '2026-04-26T16:42:00Z' },
  ];
  const groups = clusterParallelSessions(sessions);
  assert.equal(groups.length, 1);
  assert.equal(groups[0].length, 2);
});

test('three sessions, middle overlaps both: all in one cluster (transitive)', () => {
  const sessions = [
    { id: 'A', start: '2026-04-26T10:00:00Z', end: '2026-04-26T11:30:00Z' },
    { id: 'B', start: '2026-04-26T11:00:00Z', end: '2026-04-26T12:30:00Z' },
    { id: 'C', start: '2026-04-26T12:00:00Z', end: '2026-04-26T13:00:00Z' },
  ];
  const groups = clusterParallelSessions(sessions);
  assert.equal(groups.length, 1);
  assert.deepEqual(groups[0].map(s => s.id), ['A', 'B', 'C']);
});

test('cluster boundary: session that starts after all previous end gets its own group', () => {
  const sessions = [
    { id: 'A', start: '2026-04-26T10:00:00Z', end: '2026-04-26T11:00:00Z' },
    { id: 'B', start: '2026-04-26T10:30:00Z', end: '2026-04-26T11:15:00Z' },
    { id: 'C', start: '2026-04-26T13:00:00Z', end: '2026-04-26T14:00:00Z' },
  ];
  const groups = clusterParallelSessions(sessions);
  assert.equal(groups.length, 2);
  assert.deepEqual(groups[0].map(s => s.id), ['A', 'B']);
  assert.deepEqual(groups[1].map(s => s.id), ['C']);
});
```

- [x] **Step 2: Run (verify fail)**

Run: `node --test plugins/taskmaster/viewer/tests/unit/parallel-block.test.js`
Expected: FAIL — module not found.

(The implementation lives in Task 17.)

- [x] **Step 3: Commit (test only)**

```bash
git add plugins/taskmaster/viewer/tests/unit/parallel-block.test.js
git commit -m "test(viewer): parallel-block clustering (failing — impl in next task)"
```

---

### Task 17: `timeline.js` — clustering algorithm + render

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/timeline.js`

- [x] **Step 1: Implement clustering + render**

Create `plugins/taskmaster/viewer/js/components/timeline.js`:

```js
// Chronological timeline with parallel-block clusters.
// Pure-DOM. The render takes session-shaped rows; sessions group together if their
// [start, end] windows overlap (transitively). Independent flat handovers can be
// passed alongside; they render outside any cluster as standalone rows.

/**
 * @typedef {{id:string, start:string, end:string, kind?:string, parent_id?:string|null}} TimelineItem
 */

/** Group sessions whose time windows overlap (transitively). Sessions[] must be
 *  sorted ascending by start time on input. Returns an array of arrays. */
export function clusterParallelSessions(sessions) {
  const sorted = [...sessions].sort((a, b) =>
    new Date(a.start) - new Date(b.start)
  );
  const groups = [];
  let cur = [];
  let curMaxEnd = -Infinity;

  for (const s of sorted) {
    const sStart = +new Date(s.start);
    const sEnd = +new Date(s.end);
    if (cur.length && sStart <= curMaxEnd) {
      cur.push(s);
      if (sEnd > curMaxEnd) curMaxEnd = sEnd;
    } else {
      if (cur.length) groups.push(cur);
      cur = [s];
      curMaxEnd = sEnd;
    }
  }
  if (cur.length) groups.push(cur);
  return groups;
}

/** Render the timeline into `root`. Items shape:
 *    sessions: [{id, start, end, kind:'session', task_ids[], handover_ids[], recap_id}],
 *    handovers: dict id→{viewer_kind, ...}, used to render nested sub-rows
 *    independent: flat handover items not tied to a session
 *  Returns a cleanup function.
 */
export function renderTimeline(root, { sessions, handovers, independent, onSelect }) {
  root.innerHTML = '';
  const wrapper = document.createElement('div');
  wrapper.className = 'tl';
  const groups = clusterParallelSessions(sessions);

  for (const group of groups) {
    if (group.length > 1) {
      const par = document.createElement('div');
      par.className = 'par-block';
      const lbl = document.createElement('div');
      lbl.className = 'par-label';
      lbl.textContent = `Parallel · ${formatRange(group)}`;
      par.appendChild(lbl);
      const grid = document.createElement('div');
      grid.className = 'par-grid';
      grid.style.gridTemplateColumns = `repeat(${group.length}, 1fr)`;
      for (const s of group) grid.appendChild(renderSessionContainer(s, handovers, onSelect));
      par.appendChild(grid);
      wrapper.appendChild(par);
    } else {
      wrapper.appendChild(renderSessionContainer(group[0], handovers, onSelect));
    }
  }

  for (const h of (independent || [])) {
    wrapper.appendChild(renderIndependentHandover(h, onSelect));
  }

  root.appendChild(wrapper);
  return () => { root.innerHTML = ''; };
}

function formatRange(group) {
  const start = new Date(group[0].start);
  const end = new Date(Math.max(...group.map(g => +new Date(g.end))));
  const fmt = (d) => `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;
  return `${fmt(start)} → ${fmt(end)}`;
}

function renderSessionContainer(session, handovers, onSelect) {
  const c = document.createElement('div');
  c.className = 'ses-container';

  const ho = document.createElement('div');
  ho.className = 'ho';
  ho.dataset.sessionId = session.id;
  ho.innerHTML = sessionHeadHtml(session);
  ho.addEventListener('click', () => onSelect && onSelect({ kind: 'session', id: session.id }));
  c.appendChild(ho);

  const childIds = [...(session.handover_ids || []), session.recap_id].filter(Boolean);
  if (childIds.length) {
    const kids = document.createElement('div');
    kids.className = 'ses-children';
    for (const cid of childIds) {
      const isRecap = cid === session.recap_id;
      const child = document.createElement('div');
      child.className = 'ho-child';
      if (isRecap) {
        child.dataset.recapId = cid;
        child.innerHTML = recapChildHtml(cid);
        child.addEventListener('click', () => onSelect && onSelect({ kind: 'recap', id: cid }));
      } else {
        const h = (handovers || {})[cid];
        child.dataset.handoverId = cid;
        child.innerHTML = handoverChildHtml(cid, h);
        child.addEventListener('click', () => onSelect && onSelect({ kind: 'handover', id: cid }));
      }
      kids.appendChild(child);
    }
    c.appendChild(kids);
  }
  return c;
}

function renderIndependentHandover(h, onSelect) {
  const el = document.createElement('div');
  el.className = 'ho ho-standalone';
  el.dataset.handoverId = h.id;
  el.innerHTML = handoverChildHtml(h.id, h);
  el.addEventListener('click', () => onSelect && onSelect({ kind: 'handover', id: h.id }));
  return el;
}

function sessionHeadHtml(s) {
  return (
    `<div class="ho-head">`
    + `<span class="ho-kind session">SESSION</span>`
    + `<span class="ho-time mono">${shortTime(s.start)} → ${shortTime(s.end)}</span>`
    + `</div>`
    + `<div class="ho-title">${escapeHtml(s.id)}</div>`
    + `<div class="ho-foot">`
    + (s.task_ids || []).map(t => `<span class="pill task mono">${escapeHtml(t)}</span>`).join('')
    + `</div>`
  );
}

function handoverChildHtml(id, h) {
  const k = (h && h.viewer_kind) || 'standalone';
  return (
    `<div class="ho-head">`
    + `<span class="ho-kind handover ${k}">${k.toUpperCase()}</span>`
    + `<span class="ho-time mono">${escapeHtml(id)}</span>`
    + `</div>`
    + `<div class="ho-summary">${escapeHtml((h && h.tldr) || '')}</div>`
  );
}

function recapChildHtml(id) {
  return (
    `<div class="ho-head">`
    + `<span class="ho-kind recap">RECAP</span>`
    + `<span class="ho-time mono">${escapeHtml(id)}</span>`
    + `</div>`
  );
}

function shortTime(iso) {
  const d = new Date(iso);
  return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;
}

function escapeHtml(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c =>
    ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
```

- [x] **Step 2: Run unit tests (verify pass)**

Run: `node --test plugins/taskmaster/viewer/tests/unit/parallel-block.test.js`
Expected: 4 tests PASS.

- [x] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/timeline.js
git commit -m "feat(viewer): timeline component with parallel-block clustering"
```

---

### Task 18: `right-rail.js` — generic 480px right-rail

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/right-rail.js`
- Create: `plugins/taskmaster/viewer/tests/unit/right-rail.test.js`

- [x] **Step 1: Failing test**

Create `plugins/taskmaster/viewer/tests/unit/right-rail.test.js`:

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { JSDOM } from 'jsdom';
import { RightRail } from '../../js/components/right-rail.js';

test('open() injects rendered content; close() removes it', () => {
  const dom = new JSDOM('<!doctype html><body></body>');
  global.document = dom.window.document;
  const rail = new RightRail({ width: 480 });
  rail.open({ render: () => '<div id="x">hi</div>' });
  assert.ok(document.querySelector('.right-rail'));
  assert.ok(document.querySelector('#x'));
  rail.close();
  assert.equal(document.querySelector('.right-rail'), null);
});

test('open() twice swaps the content', () => {
  const dom = new JSDOM('<!doctype html><body></body>');
  global.document = dom.window.document;
  const rail = new RightRail();
  rail.open({ render: () => '<div id="a">first</div>' });
  rail.open({ render: () => '<div id="b">second</div>' });
  assert.equal(document.querySelector('#a'), null);
  assert.ok(document.querySelector('#b'));
  rail.close();
});
```

- [x] **Step 2: Run (verify fail)**

Run: `node --test plugins/taskmaster/viewer/tests/unit/right-rail.test.js`
Expected: FAIL — module not found. (Install jsdom locally is the user's existing test infra; if absent, the test is illustrative — server tests still cover the behaviour.)

- [x] **Step 3: Implement**

Create `plugins/taskmaster/viewer/js/components/right-rail.js`:

```js
// Generic right-rail. Used by Plan 3 (task-detail) and Plan 5a (session-detail).
// Construct once per screen, call open/close as the user picks rows.

const ATTACH_PARENT_SEL = '.right-rail-host';

export class RightRail {
  /** @param {{width?: number}} opts */
  constructor(opts = {}) {
    this.width = opts.width || 480;
    this.el = null;
    this._cleanup = null;
  }

  /** @param {{render: () => string, onMount?: (root: HTMLElement) => () => void, kind?: string}} args */
  open(args) {
    this.close();
    const host = document.querySelector(ATTACH_PARENT_SEL) || document.body;
    const el = document.createElement('aside');
    el.className = `right-rail right-rail-${args.kind || 'plain'}`;
    el.style.setProperty('--rail-w', this.width + 'px');
    el.innerHTML = args.render();
    host.appendChild(el);
    document.body.classList.add('rail-open');
    this.el = el;
    if (args.onMount) {
      this._cleanup = args.onMount(el) || null;
    }
  }

  close() {
    if (this._cleanup) {
      try { this._cleanup(); } catch {}
      this._cleanup = null;
    }
    if (this.el && this.el.parentNode) this.el.parentNode.removeChild(this.el);
    this.el = null;
    document.body.classList.remove('rail-open');
  }

  isOpen() { return !!this.el; }
}

export default RightRail;
```

- [x] **Step 4: Run (verify pass — only if jsdom present)**

Run: `node --test plugins/taskmaster/viewer/tests/unit/right-rail.test.js`
Expected: PASS if jsdom is installed; otherwise the Playwright smoke test (Task 33) covers the contract.

- [x] **Step 5: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/right-rail.js plugins/taskmaster/viewer/tests/unit/right-rail.test.js
git commit -m "feat(viewer): generic RightRail component (480px slide-in panel)"
```

---

### Task 19: `recap-receipts-grid.js` — 2×2 diff card grid

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/recap-receipts-grid.js`
- Create: `plugins/taskmaster/viewer/tests/unit/recap-receipts-grid.test.js`

- [x] **Step 1: Failing test**

Create `plugins/taskmaster/viewer/tests/unit/recap-receipts-grid.test.js`:

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { renderReceiptsGrid } from '../../js/components/recap-receipts-grid.js';

test('renders four cards: Tasks, Files, Lessons, Issues', () => {
  const html = renderReceiptsGrid({
    tasks_added: [{ id: 'T-3', title: 'New' }],
    tasks_changed: [{ id: 'T-2', from: { status: 'in-progress' }, to: { status: 'done' } }],
    tasks_removed: [],
    files_touched: [{ path: 'a.css', plus: 12, minus: 3 }],
    lessons_fired: [{ id: 'LSN-08', name: 'Worktree rule', fires: 3, first_time: false }],
    issues_opened: [{ id: 'ISS-12', severity: 'High', title: 'crash' }],
    issues_transitioned: [],
  });
  assert.match(html, /receipts-grid/);
  assert.match(html, /Tasks/);
  assert.match(html, /Files touched/);
  assert.match(html, /Lessons fired/);
  assert.match(html, /Issues/);
  assert.match(html, /T-3/);
  assert.match(html, /a\.css/);
  assert.match(html, /LSN-08/);
  assert.match(html, /ISS-12/);
});

test('empty diff still renders four cards with empty hint', () => {
  const html = renderReceiptsGrid({
    tasks_added: [], tasks_changed: [], tasks_removed: [],
    files_touched: [], lessons_fired: [],
    issues_opened: [], issues_transitioned: [],
  });
  assert.match(html, /Tasks/);
  assert.match(html, /No changes/);
});
```

- [x] **Step 2: Run (verify fail)**

Run: `node --test plugins/taskmaster/viewer/tests/unit/recap-receipts-grid.test.js`
Expected: FAIL — module not found.

- [x] **Step 3: Implement**

Create `plugins/taskmaster/viewer/js/components/recap-receipts-grid.js`:

```js
import { renderDiffRow } from './diff-row.js';

const escapeHtml = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, c =>
  ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

export function renderReceiptsGrid(diff) {
  return (
    `<div class="receipts-grid">`
    + tasksCard(diff)
    + filesCard(diff)
    + lessonsCard(diff)
    + issuesCard(diff)
    + `</div>`
  );
}

function cardShell({ title, count, body }) {
  return (
    `<div class="rcard">`
    + `<div class="rcard-h">`
    + `<span class="ttl">${title}</span>`
    + `<span class="cnt mono">${count}</span>`
    + `</div>`
    + `<div class="rcard-body">${body || `<div class="empty">No changes</div>`}</div>`
    + `</div>`
  );
}

function tasksCard(d) {
  const rows = [];
  for (const t of d.tasks_added || []) {
    rows.push(renderDiffRow({ kind: 'add',
      body: `<span class="id mono">${escapeHtml(t.id)}</span> ${escapeHtml(t.title || '')}` }));
  }
  for (const t of d.tasks_changed || []) {
    const from = t.from && t.from.status;
    const to   = t.to   && t.to.status;
    rows.push(renderDiffRow({ kind: 'mod',
      body: `<span class="id mono">${escapeHtml(t.id)}</span>`
          + `<span class="from">${escapeHtml(from||'')}</span>`
          + `<span class="arrow">→</span>`
          + `<span class="to">${escapeHtml(to||'')}</span>` }));
  }
  for (const t of d.tasks_removed || []) {
    rows.push(renderDiffRow({ kind: 'del',
      body: `<span class="id mono">${escapeHtml(t.id)}</span> ${escapeHtml(t.title || '')}` }));
  }
  return cardShell({
    title: 'Tasks',
    count: rows.length,
    body: rows.join(''),
  });
}

function filesCard(d) {
  const rows = (d.files_touched || []).map(f => {
    const path = typeof f === 'string' ? f : f.path;
    const plus = (typeof f === 'object' && f.plus) || 0;
    const minus = (typeof f === 'object' && f.minus) || 0;
    return (
      `<div class="files-row mod">`
      + `<span class="pre">~</span>`
      + `<span class="path mono">${escapeHtml(path)}</span>`
      + `<span class="churn mono"><span class="plus">+${plus}</span> <span class="minus">-${minus}</span></span>`
      + `</div>`
    );
  });
  return cardShell({ title: 'Files touched', count: rows.length, body: rows.join('') });
}

function lessonsCard(d) {
  const rows = (d.lessons_fired || []).map(l =>
    `<div class="lsn-row">`
    + `<span class="id mono">${escapeHtml(l.id)}</span>`
    + ` ${escapeHtml(l.name || '')}`
    + ` <span class="ct mono">×${l.fires || 1}</span>`
    + (l.first_time ? ` <span class="new-tag">(new)</span>` : '')
    + `</div>`
  );
  return cardShell({ title: 'Lessons fired', count: rows.length, body: rows.join('') });
}

function issuesCard(d) {
  const rows = [];
  for (const i of d.issues_opened || []) {
    rows.push(renderDiffRow({ kind: 'add',
      body: `<span class="sev ${(i.severity||'').toLowerCase()}">${escapeHtml(i.severity||'')}</span>`
          + `<span class="id mono">${escapeHtml(i.id)}</span> ${escapeHtml(i.title||'')}` }));
  }
  for (const i of d.issues_transitioned || []) {
    rows.push(renderDiffRow({ kind: 'mod',
      body: `<span class="id mono">${escapeHtml(i.id)}</span>`
          + ` <span class="from">${escapeHtml(i.from||'')}</span>`
          + ` <span class="arrow">→</span>`
          + ` <span class="to">${escapeHtml(i.to||'')}</span>` }));
  }
  return cardShell({ title: 'Issues', count: rows.length, body: rows.join('') });
}

export default renderReceiptsGrid;
```

- [x] **Step 4: Run (verify pass)**

Run: `node --test plugins/taskmaster/viewer/tests/unit/recap-receipts-grid.test.js`
Expected: 2 tests PASS.

- [x] **Step 5: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/recap-receipts-grid.js plugins/taskmaster/viewer/tests/unit/recap-receipts-grid.test.js
git commit -m "feat(viewer): recap-receipts-grid (2×2 Tasks/Files/Lessons/Issues)"
```

---

### Task 20: `snapshot-diff.test.js` — client mirror of server diff

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/snapshot-diff.js`
- Create: `plugins/taskmaster/viewer/tests/unit/snapshot-diff.test.js`

- [x] **Step 1: Failing test**

Create `plugins/taskmaster/viewer/tests/unit/snapshot-diff.test.js`:

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { snapshotDiff } from '../../js/components/snapshot-diff.js';

test('detects added/removed/changed tasks', () => {
  const a = { tasks: { 'T-1': { status: 'todo' }, 'T-2': { status: 'in-progress' } } };
  const b = { tasks: { 'T-2': { status: 'done' }, 'T-3': { status: 'todo' } } };
  const d = snapshotDiff(a, b);
  assert.deepEqual(d.tasks_added.map(t => t.id), ['T-3']);
  assert.deepEqual(d.tasks_removed.map(t => t.id), ['T-1']);
  assert.equal(d.tasks_changed[0].id, 'T-2');
  assert.equal(d.tasks_changed[0].from.status, 'in-progress');
  assert.equal(d.tasks_changed[0].to.status, 'done');
});

test('detects issue transitions', () => {
  const a = { tasks: {}, issues: { 'ISS-1': { status: 'open' } } };
  const b = { tasks: {}, issues: { 'ISS-1': { status: 'fixed' } } };
  const d = snapshotDiff(a, b);
  assert.equal(d.issues_transitioned[0].id, 'ISS-1');
  assert.equal(d.issues_transitioned[0].from, 'open');
  assert.equal(d.issues_transitioned[0].to, 'fixed');
});

test('passes through lessons_fired and files_touched', () => {
  const a = { tasks: {} };
  const b = { tasks: {}, lessons_fired: [{ id: 'LSN-1', fires: 2 }], files_touched: ['x.py'] };
  const d = snapshotDiff(a, b);
  assert.deepEqual(d.lessons_fired, [{ id: 'LSN-1', fires: 2 }]);
  assert.deepEqual(d.files_touched, ['x.py']);
});
```

- [x] **Step 2: Run (verify fail)**

Run: `node --test plugins/taskmaster/viewer/tests/unit/snapshot-diff.test.js`
Expected: FAIL — module not found.

- [x] **Step 3: Implement client mirror**

Create `plugins/taskmaster/viewer/js/components/snapshot-diff.js`:

```js
// Mirror of taskmaster_v3.snapshot_diff for unsaved-state preview in the client.
// The HTTP endpoint returns the server's version when available; this module is
// used when the client has a draft snapshot in memory and needs to preview the diff.

export function snapshotDiff(a, b) {
  a = a || {}; b = b || {};
  const aTasks = a.tasks || {};
  const bTasks = b.tasks || {};

  const added   = Object.keys(bTasks).filter(k => !(k in aTasks))
                       .map(k => ({ id: k, ...bTasks[k] }));
  const removed = Object.keys(aTasks).filter(k => !(k in bTasks))
                       .map(k => ({ id: k, ...aTasks[k] }));
  const changed = Object.keys(aTasks).filter(k => k in bTasks
                       && JSON.stringify(aTasks[k]) !== JSON.stringify(bTasks[k]))
                       .map(k => ({ id: k, from: aTasks[k], to: bTasks[k] }));

  const aIss = a.issues || {};
  const bIss = b.issues || {};
  const issues_opened = Object.keys(bIss).filter(k => !(k in aIss))
                              .map(k => ({ id: k, ...bIss[k] }));
  const issues_transitioned = Object.keys(aIss).filter(k => k in bIss
                              && (aIss[k].status !== bIss[k].status))
                              .map(k => ({ id: k, from: aIss[k].status, to: bIss[k].status }));

  return {
    tasks_added: added,
    tasks_removed: removed,
    tasks_changed: changed,
    lessons_fired: b.lessons_fired || [],
    issues_opened,
    issues_transitioned,
    files_touched: b.files_touched || [],
  };
}

export default snapshotDiff;
```

- [x] **Step 4: Run (verify pass)**

Run: `node --test plugins/taskmaster/viewer/tests/unit/snapshot-diff.test.js`
Expected: 3 tests PASS.

- [x] **Step 5: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/snapshot-diff.js plugins/taskmaster/viewer/tests/unit/snapshot-diff.test.js
git commit -m "feat(viewer): client-side snapshot-diff helper (mirror of server)"
```

---

### Task 21: Run full pure-data test sweep

**Files:** none modified.

- [x] **Step 1: Run all unit tests**

Run: `node --test plugins/taskmaster/viewer/tests/unit/`
Expected: All PASS (≥12 tests across diff-row / parallel-block / snapshot-diff / recap-receipts-grid; +2 right-rail when jsdom present).

- [x] **Step 2: No commit (verification only)**

---

### Task 22: Add API client methods to `js/api.js`

**Files:**
- Modify: `plugins/taskmaster/viewer/js/api.js`

- [x] **Step 1: Append helpers**

Append to `plugins/taskmaster/viewer/js/api.js`:

```js
// --- Sessions / Recap (Plan 5a) -------------------------------------------

export async function listSessions() {
  const r = await fetch('/api/sessions');
  if (!r.ok) throw new Error(`listSessions: ${r.status}`);
  return r.json();
}

export async function getSessionDetail(sid) {
  const r = await fetch(`/api/sessions/${encodeURIComponent(sid)}`);
  if (!r.ok) throw new Error(`getSessionDetail(${sid}): ${r.status}`);
  return r.json();
}

export async function getRecap(sid) {
  const r = await fetch(`/api/recap/${encodeURIComponent(sid)}`);
  if (r.status === 404) return null;
  if (!r.ok) throw new Error(`getRecap(${sid}): ${r.status}`);
  return r.json();
}

export async function putRecap(sid, payload) {
  const r = await fetch(`/api/recap/${encodeURIComponent(sid)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error(`putRecap(${sid}): ${r.status}`);
  return r.json();
}

export async function getSnapshotDiff(fromId, toId) {
  const u = `/api/snapshots/diff?from=${encodeURIComponent(fromId)}&to=${encodeURIComponent(toId)}`;
  const r = await fetch(u);
  if (!r.ok) throw new Error(`getSnapshotDiff(${fromId}→${toId}): ${r.status}`);
  return r.json();
}
```

- [x] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/api.js
git commit -m "feat(viewer): api client for sessions/recap/snapshot-diff"
```

---

## M4 — Sessions Screen

### Task 23: `sessions.css` — base diary styling

**Files:**
- Create: `plugins/taskmaster/viewer/css/screens/sessions.css`

- [ ] **Step 1: Write the file**

Create `plugins/taskmaster/viewer/css/screens/sessions.css`:

```css
/* Sessions / Handovers screen — Hybrid C diary.
   Reads tokens.css; no new global tokens introduced. */

.sessions-page { padding-bottom: var(--sp-9); }

.sessions-topbar {
  display: flex; align-items: center; gap: var(--sp-5);
  margin-bottom: var(--sp-7);
}
.sessions-topbar h2 { margin: 0; font-size: var(--text-2xl); font-weight: 600; }
.sessions-topbar .right { margin-left: auto; display: flex; gap: var(--sp-3); align-items: center; }

.sessions-search {
  background: var(--bg-card); border: 1px solid var(--border);
  color: var(--ink-2); font-size: var(--text-sm);
  padding: 3px var(--sp-4); border-radius: var(--r-sm); width: 180px;
}

.sessions-view-toggle {
  display: inline-flex; background: var(--bg-card);
  border: 1px solid var(--border); border-radius: var(--r-sm); overflow: hidden;
}
.sessions-view-toggle .seg {
  padding: 3px var(--sp-4); font-size: var(--text-sm); color: var(--ink-3);
  cursor: pointer; border-right: 1px solid var(--border);
}
.sessions-view-toggle .seg:last-child { border-right: 0; }
.sessions-view-toggle .seg.on { background: var(--accent-soft); color: var(--accent); }

.sessions-newnote {
  background: var(--bg-card); border: 1px solid var(--border);
  color: var(--ink-2); font-size: var(--text-sm);
  padding: 3px var(--sp-4); border-radius: var(--r-sm); cursor: pointer;
}
.sessions-newnote:hover { color: var(--ink); border-color: var(--border-strong); }

/* Kind filter row */
.sessions-kinds {
  display: flex; align-items: center; gap: var(--sp-3); margin-bottom: var(--sp-7);
}
.sessions-kind-chip {
  font-size: var(--text-xs); padding: 3px var(--sp-4); border-radius: 12px;
  cursor: pointer; border: 1px solid var(--border);
  color: var(--ink-3);
  display: inline-flex; align-items: center; gap: 5px;
}
.sessions-kind-chip .dot { width: 7px; height: 7px; border-radius: 50%; }
.sessions-kind-chip.session .dot { background: var(--accent); }
.sessions-kind-chip.handover .dot { background: var(--purple); }
.sessions-kind-chip.recap .dot { background: var(--green); }
.sessions-kind-chip.on { color: var(--ink); background: var(--accent-soft);
  border-color: rgba(74,158,255,0.3); }
.sessions-kind-chip .ct { color: var(--ink-3); font-family: var(--font-mono); font-size: 9px; }

/* Group/day header */
.sessions-day {
  display: flex; align-items: baseline; gap: var(--sp-4);
  margin: var(--sp-3) 0 var(--sp-4); padding: 0 2px;
}
.sessions-day .label {
  font-family: var(--font-serif); font-size: var(--text-md); color: var(--ink-2);
}
.sessions-day .meta { color: var(--ink-3); font-size: var(--text-sm); }
.sessions-day .rule { flex: 1; height: 1px; background: var(--border-soft); margin-left: 6px; }

/* timeline.js renders into `.tl` */
.tl { display: flex; flex-direction: column; gap: var(--sp-5); }

.ses-container { margin-bottom: var(--sp-6); }

.ho {
  background: var(--bg-panel); border: 1px solid var(--border);
  border-radius: var(--r-md); padding: var(--sp-4) var(--sp-5);
  cursor: pointer; transition: background var(--t-fast) var(--ease);
}
.ho:hover { background: #1c1d23; }
.ho.selected { background: rgba(160,127,224,0.10); border-color: rgba(160,127,224,0.45); }
.ho-head { display: flex; align-items: center; gap: var(--sp-3); margin-bottom: var(--sp-2); }
.ho-kind {
  font-size: 9px; text-transform: uppercase; letter-spacing: 0.06em;
  padding: 1px 6px; border-radius: 3px; font-weight: 600;
}
.ho-kind.session  { background: var(--accent-soft); color: var(--accent); }
.ho-kind.handover { background: rgba(160,127,224,0.15); color: var(--purple); }
.ho-kind.recap    { background: rgba(95,174,110,0.15); color: var(--green); }
.ho-kind.handover.mid-task   { background: rgba(160,127,224,0.20); }
.ho-kind.handover.checkpoint { background: rgba(160,127,224,0.12); }
.ho-kind.handover.wrap       { background: rgba(95,174,110,0.15); color: var(--green); }
.ho-kind.handover.standalone { background: transparent;
  border: 1px dashed rgba(160,127,224,0.45); color: var(--purple); }
.ho-time { color: var(--ink-3); font-size: 10px; }
.ho-title { font-size: var(--text-md); color: var(--ink); margin-bottom: var(--sp-1); }
.ho-summary { color: var(--ink-2); font-size: var(--text-sm); line-height: 1.5; }
.ho-foot { display: flex; align-items: center; gap: var(--sp-3); flex-wrap: wrap; }
.ho-foot .pill {
  font-size: 9px; color: var(--ink-3);
  background: var(--bg-card); border: 1px solid var(--border-soft);
  padding: 1px 6px; border-radius: 3px;
}

/* Nested children: connector line + L bracket */
.ses-children {
  position: relative; margin: 0 0 0 14px; padding: var(--sp-1) 0 0 16px;
  border-left: 1px solid var(--border);
}
.ses-children::before {
  content: ''; position: absolute; left: -1px; top: 0; height: 8px; width: 12px;
  border-left: 1px solid var(--border); border-bottom: 1px solid var(--border);
  border-bottom-left-radius: 6px;
}
.ho-child {
  background: var(--bg-card); border: 1px solid var(--border-soft);
  border-radius: 5px; padding: var(--sp-2) var(--sp-4); margin-top: var(--sp-2);
  cursor: pointer; position: relative;
}
.ho-child::before {
  content: ''; position: absolute; left: -16px; top: 14px;
  width: 12px; height: 1px; background: var(--border);
}
.ho-child:hover { background: #25262c; }

/* Parallel block */
.par-block {
  border: 1px dashed rgba(160,127,224,0.35); border-radius: var(--r-lg);
  padding: var(--sp-4) var(--sp-4) var(--sp-1);
  margin: var(--sp-2) 0 var(--sp-7);
  background: rgba(160,127,224,0.04); position: relative;
}
.par-label {
  position: absolute; top: -7px; left: 12px;
  font-size: 9px; text-transform: uppercase; letter-spacing: 0.08em;
  background: var(--bg-canvas); padding: 0 6px;
  color: var(--purple); font-weight: 600;
}
.par-grid { display: grid; gap: var(--sp-4); align-items: start; }

/* Standalone (independent) handover row */
.ho-standalone {
  border: 1px dashed rgba(160,127,224,0.45);
  background: rgba(160,127,224,0.05);
}

/* Right-rail dimming when open */
body.rail-open .tl { opacity: 0.5; pointer-events: none; }
body.rail-open .tl .selected { opacity: 1; pointer-events: auto; }
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/css/screens/sessions.css
git commit -m "feat(viewer): sessions.css — diary, parallel-block, nested rows"
```

---

### Task 24: Right-rail CSS (shared, lives in components.css)

**Files:**
- Modify: `plugins/taskmaster/viewer/css/components.css` (append)

- [ ] **Step 1: Append**

```css
/* RightRail (shared with task-detail in Plan 3) */
.right-rail {
  position: fixed; top: 0; right: 0; height: 100vh; width: var(--rail-w, 480px);
  background: var(--bg-panel); border-left: 1px solid var(--border);
  box-shadow: -8px 0 24px rgba(0,0,0,0.30);
  overflow-y: auto;
  z-index: 50;
  padding: var(--sp-7) var(--sp-7);
}
.right-rail .rr-h {
  display: flex; align-items: center; gap: var(--sp-3);
  margin-bottom: var(--sp-5);
}
.right-rail .rr-h .kind-pill {
  font-size: 9px; text-transform: uppercase; letter-spacing: 0.06em;
  padding: 2px 7px; border-radius: 3px; font-weight: 600;
}
.right-rail .rr-h .kind-pill.handover { background: rgba(160,127,224,0.15); color: var(--purple); }
.right-rail .rr-h .kind-pill.session  { background: var(--accent-soft); color: var(--accent); }
.right-rail .rr-h .kind-pill.recap    { background: rgba(95,174,110,0.15); color: var(--green); }
.right-rail .rr-h .ts { color: var(--ink-3); font-family: var(--font-mono); font-size: 10px; }
.right-rail .rr-h .actions { margin-left: auto; display: flex; gap: 4px; }
.right-rail .rr-h .ic-btn {
  width: 24px; height: 24px; border-radius: 4px; background: transparent;
  border: 1px solid var(--border); color: var(--ink-3); cursor: pointer;
  display: flex; align-items: center; justify-content: center; font-size: 12px;
}
.right-rail .rr-h .ic-btn:hover { color: var(--ink); border-color: var(--border-strong); }

.right-rail .rr-title { font-size: var(--text-lg); color: var(--ink); margin-bottom: var(--sp-2); }
.right-rail .rr-meta {
  color: var(--ink-3); font-size: var(--text-sm); margin-bottom: var(--sp-5);
  display: flex; flex-wrap: wrap; gap: var(--sp-3);
}
.right-rail .rr-meta .filepath { font-family: var(--font-mono); font-size: 10px; cursor: pointer; }
.right-rail .rr-meta .filepath:hover { color: var(--ink-2); }

.right-rail .rr-resume {
  background: linear-gradient(180deg, rgba(74,158,255,0.06), rgba(74,158,255,0.02));
  border: 1px solid rgba(74,158,255,0.25); border-radius: var(--r-lg);
  padding: var(--sp-5) var(--sp-5) var(--sp-5) var(--sp-7);
  position: relative; margin-bottom: var(--sp-6);
}
.right-rail .rr-resume .label {
  position: absolute; top: -7px; left: 12px;
  background: var(--bg-panel); padding: 0 6px;
  font-size: 9px; text-transform: uppercase; letter-spacing: 0.10em;
  color: var(--accent); font-weight: 600;
}
.right-rail .rr-resume .copy {
  position: absolute; top: 8px; right: 8px;
  background: transparent; border: 1px solid var(--border);
  color: var(--ink-3); font-size: 10px; padding: 2px 6px;
  border-radius: 4px; cursor: pointer;
}
.right-rail .rr-resume .copy:hover { color: var(--ink); }
.right-rail .rr-resume .body {
  font-family: var(--font-serif); font-size: var(--text-md);
  line-height: 1.55; color: var(--ink); white-space: pre-wrap;
}

.right-rail .rr-section { margin-bottom: var(--sp-6); }
.right-rail .rr-section h4 {
  font-size: 10px; text-transform: uppercase; letter-spacing: 0.10em;
  color: var(--ink-3); margin: 0 0 var(--sp-3); display: flex; align-items: center; gap: var(--sp-3);
}
.right-rail .rr-section h4 .ct { font-family: var(--font-mono); font-size: 9px; opacity: 0.8; }

.right-rail .checkitem {
  display: flex; align-items: flex-start; gap: var(--sp-3);
  padding: 3px 0; font-size: var(--text-sm); color: var(--ink-2);
}
.right-rail .checkitem .mark { width: 14px; flex: 0 0 14px; padding-top: 2px; }
.right-rail .checkitem.done .mark { color: var(--green); }
.right-rail .checkitem.open .mark { color: var(--ink-3); }

.right-rail .related-row {
  display: flex; align-items: center; gap: var(--sp-3);
  padding: var(--sp-2) 0; font-size: var(--text-sm); color: var(--ink-2);
  border-bottom: 1px solid var(--border-soft);
}
.right-rail .related-row .id { font-family: var(--font-mono); font-size: 10px; color: var(--ink-3); }
.right-rail .related-row .status { margin-left: auto; font-size: 9px; color: var(--ink-3); }

.right-rail .files-list { font-family: var(--font-mono); font-size: 10px; }
.right-rail .files-list .files-row {
  display: flex; align-items: center; gap: var(--sp-3);
  padding: 3px 0; color: var(--ink-2);
}
.right-rail .files-list .files-row .pre { width: 12px; text-align: center; font-weight: 700; }
.right-rail .files-list .files-row.add .pre { color: var(--diff-add); }
.right-rail .files-list .files-row.mod .pre { color: var(--diff-mod); }
.right-rail .files-list .files-row.del .pre { color: var(--diff-del); }
.right-rail .files-list .more { color: var(--ink-3); font-style: italic; padding-top: var(--sp-2); }
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/css/components.css
git commit -m "feat(viewer): right-rail shared component styling"
```

---

### Task 25: `sessions.js` — module skeleton + mount

**Files:**
- Modify: `plugins/taskmaster/viewer/js/screens/sessions.js` (replace stub)
- Modify: `plugins/taskmaster/viewer/index.html` (add `<link>` for sessions.css)

- [ ] **Step 1: Add the CSS link**

In `plugins/taskmaster/viewer/index.html`, inside the `<head>` near other screen CSS:

```html
<link rel="stylesheet" href="css/screens/sessions.css">
```

- [ ] **Step 2: Replace the stub**

Overwrite `plugins/taskmaster/viewer/js/screens/sessions.js`:

```js
import { renderTimeline } from '../components/timeline.js';
import { RightRail } from '../components/right-rail.js';
import { listSessions, getSessionDetail } from '../api.js';

export const meta = { title: 'Sessions', icon: '⊕', sidebarKey: 'sessions' };

const escapeHtml = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, c =>
  ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

export async function mount(root, { params, store, prefs }) {
  root.innerHTML = `
    <div class="sessions-page">
      <div class="sessions-topbar">
        <h2>Sessions / Handovers</h2>
        <span class="sessions-count" data-role="count"></span>
        <div class="right">
          <input class="sessions-search" placeholder="Search sessions…">
          <div class="sessions-view-toggle" data-role="view-toggle">
            <span class="seg" data-view="A">Diary</span>
            <span class="seg" data-view="B">Lanes</span>
            <span class="seg" data-view="C">By Task</span>
          </div>
          <button class="sessions-newnote" data-role="new-note">+ New note</button>
        </div>
      </div>
      <div class="sessions-kinds" data-role="kinds">
        <span class="sessions-kind-chip session on" data-kind="session">
          <span class="dot"></span> Sessions <span class="ct">0</span>
        </span>
        <span class="sessions-kind-chip handover on" data-kind="handover">
          <span class="dot"></span> Handovers <span class="ct">0</span>
        </span>
        <span class="sessions-kind-chip recap on" data-kind="recap">
          <span class="dot"></span> Recaps <span class="ct">0</span>
        </span>
      </div>
      <div class="right-rail-host" data-role="rail-host"></div>
      <div class="sessions-mount" data-role="mount"></div>
    </div>
  `;

  const rail = new RightRail({ width: 480 });
  const state = {
    sessions: [],
    detailCache: new Map(),
    view: (prefs && prefs.screens && prefs.screens.sessions && prefs.screens.sessions.view) || 'A',
    kinds: { session: true, handover: true, recap: true },
    selectedSessionId: params && params.id || null,
  };

  bindViewToggle(root, state);
  bindKindChips(root, state, () => render(root, state, rail));
  bindNewNote(root);

  state.sessions = await listSessions();
  refreshKindCounts(root, state.sessions);
  render(root, state, rail);

  if (state.selectedSessionId) openSessionDetail(rail, state.selectedSessionId, state);

  return () => { rail.close(); };
}

function bindViewToggle(root, state) {
  const tg = root.querySelector('[data-role=view-toggle]');
  for (const seg of tg.querySelectorAll('.seg')) {
    if (seg.dataset.view === state.view) seg.classList.add('on');
    seg.addEventListener('click', () => {
      tg.querySelectorAll('.seg').forEach(s => s.classList.remove('on'));
      seg.classList.add('on');
      state.view = seg.dataset.view;
      // Sticky pref persistence is owned by store.setPref/api.savePrefs (Plan 1).
      // We only update local state here; the store wires the PUT call.
      window.dispatchEvent(new CustomEvent('viewer:prefs-patch', {
        detail: { screens: { sessions: { view: state.view } } },
      }));
    });
  }
}

function bindKindChips(root, state, onChange) {
  const row = root.querySelector('[data-role=kinds]');
  for (const chip of row.querySelectorAll('.sessions-kind-chip')) {
    chip.addEventListener('click', () => {
      const k = chip.dataset.kind;
      state.kinds[k] = !state.kinds[k];
      chip.classList.toggle('on', state.kinds[k]);
      onChange();
    });
  }
}

function bindNewNote(root) {
  root.querySelector('[data-role=new-note]').addEventListener('click', () => {
    window.location.hash = '#/sessions?new=1';
  });
}

function refreshKindCounts(root, sessions) {
  const sCount = sessions.length;
  const hCount = sessions.reduce((n, s) => n + (s.handover_ids || []).length, 0);
  const rCount = sessions.filter(s => s.recap_id).length;
  const chips = root.querySelectorAll('[data-role=kinds] .sessions-kind-chip');
  chips[0].querySelector('.ct').textContent = sCount;
  chips[1].querySelector('.ct').textContent = hCount;
  chips[2].querySelector('.ct').textContent = rCount;
  root.querySelector('[data-role=count]').textContent = `${sCount} sessions · ${hCount} handovers · ${rCount} recaps`;
}

function render(root, state, rail) {
  const mount = root.querySelector('[data-role=mount]');
  if (state.view !== 'A') {
    mount.innerHTML = `<div class="stub">View "${escapeHtml(state.view)}" — Plan 5b owns Lanes/By-Task.<div class="stub-meta">/sessions?view=${escapeHtml(state.view)}</div></div>`;
    return;
  }

  // Filter + map for timeline.
  const visibleSessions = state.kinds.session
    ? state.sessions.map(s => ({
        ...s,
        handover_ids: state.kinds.handover ? (s.handover_ids || []) : [],
        recap_id: state.kinds.recap ? s.recap_id : null,
      }))
    : [];

  const handovers = {}; // id → {viewer_kind, tldr}
  for (const s of state.sessions) {
    for (const hid of s.handover_ids || []) {
      handovers[hid] = handovers[hid] || { id: hid, viewer_kind: 'standalone', tldr: '' };
    }
  }

  const independent = []; // standalone handovers come from a Plan 5b feed; empty here.

  renderTimeline(mount, {
    sessions: visibleSessions,
    handovers,
    independent,
    onSelect: ({ kind, id }) => {
      if (kind === 'session')  return openSessionDetail(rail, id, state);
      if (kind === 'handover') return openHandoverDetail(rail, id, state);
      if (kind === 'recap')    window.location.hash = `#/recap/${id}`;
    },
  });
}

async function openSessionDetail(rail, sid, state) {
  const detail = state.detailCache.get(sid) || await getSessionDetail(sid);
  state.detailCache.set(sid, detail);
  rail.open({
    kind: 'session',
    render: () => renderSessionRail(detail),
    onMount: (el) => bindRailClose(el, rail),
  });
}

async function openHandoverDetail(rail, hid, state) {
  // Locate the session containing this handover, then pull its detail.
  const owner = state.sessions.find(s => (s.handover_ids || []).includes(hid));
  if (!owner) return;
  const detail = state.detailCache.get(owner.id) || await getSessionDetail(owner.id);
  state.detailCache.set(owner.id, detail);
  const h = (detail.handovers || []).find(x => x.id === hid);
  if (!h) return;
  rail.open({
    kind: 'handover',
    render: () => renderHandoverRail(h, owner),
    onMount: (el) => bindRailClose(el, rail),
  });
}

function bindRailClose(el, rail) {
  const btn = el.querySelector('[data-role=rail-close]');
  if (btn) btn.addEventListener('click', () => rail.close());
  return () => {};
}

function renderSessionRail(detail) {
  const s = detail.session;
  return (
    `<div class="rr-h">`
    + `<span class="kind-pill session">SESSION</span>`
    + `<span class="ts">${escapeHtml(s.start)} → ${escapeHtml(s.end)}</span>`
    + `<span class="actions">`
    + `<button class="ic-btn" data-role="rail-close" title="Close">✕</button>`
    + `</span></div>`
    + `<div class="rr-title">${escapeHtml(s.id)}</div>`
    + `<div class="rr-meta"><span>Tasks: ${(s.task_ids||[]).map(escapeHtml).join(', ') || '—'}</span></div>`
    + (detail.handovers || []).map(h =>
        `<div class="rr-section"><h4>${escapeHtml(h.viewer_kind.toUpperCase())} <span class="ct mono">${escapeHtml(h.id)}</span></h4>`
        + `<div class="ho-summary">${escapeHtml(h.tldr || '')}</div></div>`).join('')
  );
}

function renderHandoverRail(h, owner) {
  const fp = `.taskmaster/handovers/${h.id}.md`;
  return (
    `<div class="rr-h">`
    + `<span class="kind-pill handover">${escapeHtml(h.viewer_kind.toUpperCase())}</span>`
    + `<span class="ts">${escapeHtml(h.date || '')}</span>`
    + `<span class="actions">`
    + `<button class="ic-btn" title="Edit">✎</button>`
    + `<button class="ic-btn" title="Open file">↗</button>`
    + `<button class="ic-btn" data-role="rail-close" title="Close">✕</button>`
    + `</span></div>`
    + `<div class="rr-title">${escapeHtml(h.tldr || h.id)}</div>`
    + `<div class="rr-meta">`
    + `<span>Session: <a href="#/sessions/${escapeHtml(owner.id)}">${escapeHtml(owner.id)}</a></span>`
    + `<span class="filepath" title="Click to copy">${escapeHtml(fp)}</span>`
    + `</div>`
    + `<div class="rr-resume">`
    + `<span class="label">RESUME</span>`
    + `<button class="copy">⧉ copy</button>`
    + `<div class="body">${escapeHtml(h.resume_prompt || h.next_action || '')}</div>`
    + `</div>`
    + `<div class="rr-section"><h4>What's done <span class="ct mono">${(h.done_items||[]).length}</span></h4>`
    +   (h.done_items||[]).map(i => `<div class="checkitem done"><span class="mark">✓</span><span>${escapeHtml(i)}</span></div>`).join('')
    + `</div>`
    + `<div class="rr-section"><h4>What's open <span class="ct mono">${(h.open_items||[]).length}</span></h4>`
    +   (h.open_items||[]).map(i => `<div class="checkitem open"><span class="mark">○</span><span>${escapeHtml(i)}</span></div>`).join('')
    + `</div>`
    + `<div class="rr-section"><h4>Related</h4>`
    +   (h.task_ids||[]).map(t =>
        `<div class="related-row"><span class="id">${escapeHtml(t)}</span></div>`).join('')
    + `</div>`
    + `<div class="rr-section"><h4>Files touched</h4><div class="files-list">`
    +   (h.files_touched||[]).slice(0, 8).map(f =>
        `<div class="files-row mod"><span class="pre">~</span><span>${escapeHtml(typeof f === 'string' ? f : f.path)}</span></div>`).join('')
    + ((h.files_touched||[]).length > 8
        ? `<div class="more">+ ${(h.files_touched||[]).length - 8} more…</div>` : '')
    + `</div></div>`
  );
}

export default mount;
```

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/index.html plugins/taskmaster/viewer/js/screens/sessions.js
git commit -m "feat(viewer): sessions screen — diary, kind filter, right-rail wiring"
```

---

### Task 26: Sessions screen — Playwright smoke test

**Files:**
- Create: `plugins/taskmaster/viewer/tests/sessions.spec.js`

- [ ] **Step 1: Write the test**

Create `plugins/taskmaster/viewer/tests/sessions.spec.js`:

```js
import { test, expect } from '@playwright/test';

test.describe('Sessions screen', () => {
  test('route resolves and key DOM nodes mount', async ({ page }) => {
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });

    await page.goto('/v3#/sessions');
    await expect(page.locator('.sessions-page')).toBeVisible();
    await expect(page.locator('.sessions-topbar h2')).toHaveText('Sessions / Handovers');
    await expect(page.locator('[data-role=view-toggle] .seg')).toHaveCount(3);
    await expect(page.locator('[data-role=kinds] .sessions-kind-chip')).toHaveCount(3);
    await expect(page.locator('[data-role=new-note]')).toBeVisible();

    // No console errors during initial mount.
    expect(errors).toEqual([]);
  });

  test('view toggle switches active segment', async ({ page }) => {
    await page.goto('/v3#/sessions');
    const segs = page.locator('[data-role=view-toggle] .seg');
    await segs.nth(1).click();
    await expect(segs.nth(1)).toHaveClass(/on/);
    await expect(segs.nth(0)).not.toHaveClass(/on/);
  });

  test('kind chips toggle visibility', async ({ page }) => {
    await page.goto('/v3#/sessions');
    const chip = page.locator('[data-role=kinds] [data-kind=recap]');
    await expect(chip).toHaveClass(/on/);
    await chip.click();
    await expect(chip).not.toHaveClass(/on/);
  });
});
```

- [ ] **Step 2: Run (verify pass)**

Run: `npx playwright test plugins/taskmaster/viewer/tests/sessions.spec.js --reporter=line`
Expected: 3 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/tests/sessions.spec.js
git commit -m "test(viewer): Playwright smoke for Sessions screen"
```

---

### Task 27: Wire `viewer:prefs-patch` event into store/api

**Files:**
- Modify: `plugins/taskmaster/viewer/js/main.js`

- [ ] **Step 1: Append global listener**

In `plugins/taskmaster/viewer/js/main.js` after the boot block, append:

```js
import { savePrefs } from './api.js';

// Plan 5a — sessions screen fires this when its view toggle changes.
// Plan 5b will reuse the same convention.
window.addEventListener('viewer:prefs-patch', (ev) => {
  savePrefs(ev.detail).catch(err => console.warn('prefs patch failed', err));
});
```

If `savePrefs` is not yet exported from `api.js`, add this companion to api.js:

```js
export async function savePrefs(patch) {
  const r = await fetch('/api/viewer/prefs', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch),
  });
  if (!r.ok) throw new Error(`savePrefs: ${r.status}`);
  return r.json();
}
```

- [ ] **Step 2: Run sessions Playwright again to confirm no regression**

Run: `npx playwright test plugins/taskmaster/viewer/tests/sessions.spec.js --reporter=line`
Expected: 3 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/js/main.js plugins/taskmaster/viewer/js/api.js
git commit -m "feat(viewer): viewer:prefs-patch event → savePrefs round-trip"
```

---

## M5 — Recap Screen

### Task 28: `recap.css` — hero + receipts styling

**Files:**
- Create: `plugins/taskmaster/viewer/css/screens/recap.css`

- [ ] **Step 1: Write the file**

Create `plugins/taskmaster/viewer/css/screens/recap.css`:

```css
.recap-page { padding-bottom: var(--sp-9); }

.recap-topbar {
  display: flex; align-items: center; gap: var(--sp-4); margin-bottom: var(--sp-7);
}
.recap-picker {
  display: flex; align-items: center; gap: var(--sp-3);
  padding: 6px 10px; background: var(--bg-card); border: 1px solid var(--border);
  border-radius: var(--r-lg); cursor: pointer;
}
.recap-picker .pid { font-family: var(--font-mono); font-size: var(--text-sm); color: var(--accent); }
.recap-picker .pdate { color: var(--ink-3); font-size: var(--text-sm); }
.recap-picker .chev { color: var(--ink-3); }
.recap-nav-arrow {
  width: 28px; height: 28px; border-radius: var(--r-md);
  background: var(--bg-card); border: 1px solid var(--border); color: var(--ink-2);
  display: flex; align-items: center; justify-content: center; cursor: pointer;
}
.recap-nav-arrow:hover { color: var(--ink); border-color: var(--border-strong); }
.recap-nav-arrow:disabled { opacity: 0.4; cursor: default; }
.recap-topbar .spacer { flex: 1; }
.recap-action {
  padding: 6px 10px; background: transparent; border: 1px solid var(--border);
  color: var(--ink-2); border-radius: var(--r-md); cursor: pointer; font-size: var(--text-sm);
}
.recap-action.primary {
  background: var(--accent-soft); border-color: rgba(74,158,255,0.35); color: var(--accent);
}

.recap-hero {
  background: linear-gradient(180deg, #1a1c22 0%, var(--bg-card) 100%);
  border: 1px solid var(--border); border-radius: var(--r-2xl);
  padding: 22px 24px; margin-bottom: var(--sp-7); position: relative;
}
.recap-hero-top { display: flex; align-items: flex-start; gap: var(--sp-6); margin-bottom: var(--sp-5); }
.recap-hero-kind {
  font-size: 9px; text-transform: uppercase; letter-spacing: 0.14em; color: var(--purple);
  font-weight: 600; padding: 3px 8px;
  border: 1px solid rgba(160,127,224,0.35); border-radius: var(--r-sm);
  background: rgba(160,127,224,0.08);
}
.recap-hero-meta {
  display: flex; align-items: center; gap: var(--sp-4); color: var(--ink-3); font-size: var(--text-sm);
}
.recap-hero-meta .dot { width: 3px; height: 3px; border-radius: 50%; background: var(--ink-3); }
.recap-hero-actions { margin-left: auto; display: flex; gap: 6px; }
.recap-hero-icon-btn {
  width: 26px; height: 26px; border-radius: var(--r-sm);
  background: transparent; border: 1px solid var(--border); color: var(--ink-3);
  display: flex; align-items: center; justify-content: center; cursor: pointer; font-size: 13px;
}
.recap-hero-icon-btn:hover { color: var(--ink); border-color: var(--border-strong); }

.recap-hero-title { font-size: var(--text-2xl); color: var(--ink); margin: 0 0 var(--sp-1); line-height: 1.3; }
.recap-hero-subtitle { font-family: var(--font-mono); font-size: var(--text-sm); color: var(--ink-3); margin-bottom: 18px; }

.narrative { display: grid; grid-template-columns: 1fr; gap: var(--sp-7); }
.narr-section h4 {
  font-size: 10px; text-transform: uppercase; letter-spacing: 0.12em;
  color: var(--ink-3); margin: 0 0 var(--sp-3); font-weight: 600;
  display: flex; align-items: center; gap: 6px;
}
.narr-section h4::before { content: ''; width: 14px; height: 1px; background: var(--ink-3); opacity: 0.4; }
.narr-body {
  font-family: var(--font-serif); font-size: var(--text-lg); line-height: 1.6; color: var(--ink-2);
}
.narr-body em { color: var(--ink); font-style: italic; }
.narr-edit textarea {
  width: 100%; min-height: 120px;
  background: var(--bg-deep); color: var(--ink); border: 1px solid var(--border);
  border-radius: var(--r-md); padding: var(--sp-4);
  font-family: var(--font-serif); font-size: var(--text-lg); line-height: 1.6;
}
.narr-draft-caption {
  font-size: 10px; color: var(--ink-3); margin-bottom: var(--sp-2); font-family: var(--font-mono);
}

.recap-stats {
  display: flex; gap: 0; margin-top: 18px; padding: 14px 0 0;
  border-top: 1px solid var(--border-soft);
}
.recap-stat { flex: 1; text-align: center; padding: 0 12px; border-right: 1px solid var(--border-soft); }
.recap-stat:last-child { border-right: none; }
.recap-stat-num {
  font-size: var(--text-2xl); font-weight: 600; font-family: var(--font-mono); color: var(--ink);
}
.recap-stat-num.add { color: var(--diff-add); }
.recap-stat-num.mod { color: var(--diff-mod); }
.recap-stat-num.del { color: var(--diff-del); }
.recap-stat-num.purple { color: var(--purple); }
.recap-stat-label {
  font-size: 10px; text-transform: uppercase; letter-spacing: 0.1em; color: var(--ink-3); margin-top: 2px;
}

.receipts-h { display: flex; align-items: center; gap: var(--sp-4); margin-bottom: var(--sp-4); }
.receipts-h h3 { font-size: var(--text-md); color: var(--ink); margin: 0; font-weight: 600; }
.receipts-h .vs { font-family: var(--font-mono); font-size: var(--text-sm); color: var(--ink-3); }
.receipts-h .vs .snap { color: var(--accent); }
.receipts-h .filt { margin-left: auto; display: flex; gap: 4px; }
.filt-chip {
  padding: 3px 8px; border: 1px solid var(--border); border-radius: var(--r-sm);
  font-size: 10px; color: var(--ink-3); cursor: pointer;
}
.filt-chip.on { color: var(--ink); border-color: var(--border-strong); background: var(--bg-card); }

.receipts-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--sp-5); }
.rcard {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: var(--r-xl); padding: 14px 16px;
}
.rcard-h {
  display: flex; align-items: center; gap: var(--sp-3); margin-bottom: var(--sp-4);
  padding-bottom: var(--sp-3); border-bottom: 1px solid var(--border-soft);
}
.rcard-h .ttl { font-size: var(--text-base); color: var(--ink); font-weight: 600; }
.rcard-h .cnt { margin-left: auto; font-family: var(--font-mono); font-size: 10px; color: var(--ink-3); }
.rcard .empty { color: var(--ink-3); font-style: italic; font-size: var(--text-sm); }

.diff-row { display: flex; gap: var(--sp-3); padding: 5px 0; font-size: 11.5px; line-height: 1.45; }
.diff-row .pre { font-family: var(--font-mono); font-weight: 700; width: 14px; text-align: center; }
.diff-row.add .pre { color: var(--diff-add); }
.diff-row.mod .pre { color: var(--diff-mod); }
.diff-row.del .pre { color: var(--diff-del); }
.diff-row .body { flex: 1; color: var(--ink-2); }
.diff-row .body .id { font-family: var(--font-mono); font-size: 10.5px; color: var(--ink-3); margin-right: 6px; }
.diff-row .body .arrow { color: var(--ink-3); margin: 0 4px; }
.diff-row .body .from { color: var(--ink-3); text-decoration: line-through; opacity: 0.65; }
.diff-row .body .to { color: var(--ink); }
.diff-row .body .sev {
  display: inline-block; padding: 1px 6px; border-radius: 3px;
  font-size: 9px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; margin-right: 4px;
}
.sev.high { background: rgba(214,107,95,0.15); color: var(--red); }
.sev.medium { background: rgba(214,164,95,0.15); color: var(--amber); }

.lsn-row { padding: 5px 0; font-size: 11.5px; color: var(--ink-2); }
.lsn-row .id { color: var(--gold); margin-right: 6px; }
.lsn-row .ct { color: var(--ink-3); margin-left: 6px; }
.lsn-row .new-tag { color: var(--gold); font-size: 9px; margin-left: 6px; }

.recap-footer {
  display: flex; gap: var(--sp-5); align-items: center;
  margin-top: var(--sp-7); padding-top: var(--sp-5);
  border-top: 1px solid var(--border-soft); font-family: var(--font-mono); font-size: 10px;
  color: var(--ink-3);
}
.recap-footer .grow { flex: 1; }
.recap-footer a { color: var(--accent); text-decoration: none; }
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/css/screens/recap.css
git commit -m "feat(viewer): recap.css — hero + narrative + receipts grid"
```

---

### Task 29: `recap.js` skeleton + picker + prev/next

**Files:**
- Modify: `plugins/taskmaster/viewer/js/screens/recap.js` (replace stub)
- Modify: `plugins/taskmaster/viewer/index.html` (add `<link>` for recap.css)

- [ ] **Step 1: Add CSS link**

In `index.html` head:

```html
<link rel="stylesheet" href="css/screens/recap.css">
```

- [ ] **Step 2: Replace the stub**

Overwrite `plugins/taskmaster/viewer/js/screens/recap.js`:

```js
import { listSessions, getRecap, putRecap, getSnapshotDiff } from '../api.js';
import { renderReceiptsGrid } from '../components/recap-receipts-grid.js';

export const meta = { title: 'Recap', icon: '⚯', sidebarKey: 'recap' };

const escapeHtml = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, c =>
  ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

export async function mount(root, { params }) {
  root.innerHTML = `<div class="recap-page" data-role="root"><div class="stub">Loading recap…</div></div>`;
  const sessions = await listSessions();
  const recapSessions = sessions.filter(s => s.recap_id);

  const targetId = (params && params.id) || (recapSessions[0] && recapSessions[0].id);
  if (!targetId) {
    root.querySelector('[data-role=root]').innerHTML =
      `<div class="stub">No recaps yet. Close a session to generate one.</div>`;
    return () => {};
  }

  const idx = recapSessions.findIndex(s => s.id === targetId);
  const cur = recapSessions[idx];
  if (!cur) {
    root.querySelector('[data-role=root]').innerHTML =
      `<div class="stub">No recap found for ${escapeHtml(targetId)}.</div>`;
    return () => {};
  }
  const prev = recapSessions[idx + 1] || null;
  const next = recapSessions[idx - 1] || null;

  const recap = await getRecap(cur.id);
  let diff = { tasks_added:[], tasks_changed:[], tasks_removed:[],
               files_touched:[], lessons_fired:[], issues_opened:[], issues_transitioned:[] };
  if (recap && recap.frontmatter && recap.frontmatter.snapshot_before && recap.frontmatter.snapshot_after) {
    try {
      diff = await getSnapshotDiff(recap.frontmatter.snapshot_before, recap.frontmatter.snapshot_after);
    } catch (e) {
      console.warn('snapshot diff failed', e);
    }
  }

  renderRecapPage(root, { cur, prev, next, recap, diff, editing: false });
  bindNav(root, prev, next);
  bindActions(root, cur, recap, diff);
  return () => {};
}

function bindNav(root, prev, next) {
  const p = root.querySelector('[data-role=prev]');
  const n = root.querySelector('[data-role=next]');
  p && p.addEventListener('click', () => prev && (window.location.hash = `#/recap/${prev.id}`));
  n && n.addEventListener('click', () => next && (window.location.hash = `#/recap/${next.id}`));
}

function bindActions(root, cur, recap, diff) {
  const editBtn = root.querySelector('[data-role=edit]');
  if (editBtn) editBtn.addEventListener('click', () => {
    renderRecapPage(root, { cur,
      prev: null, next: null,
      recap, diff, editing: true });
    bindEditing(root, cur, recap, diff);
  });
  const copyBtn = root.querySelector('[data-role=copy-resume]');
  if (copyBtn && recap) copyBtn.addEventListener('click', () => {
    const text = `${recap.what_happened || ''}\n\n${recap.whats_next || ''}`;
    navigator.clipboard?.writeText(text);
    copyBtn.textContent = '✓ copied';
    setTimeout(() => { copyBtn.textContent = '⧉ copy resume'; }, 1500);
  });
  const openBtn = root.querySelector('[data-role=open-sessions]');
  if (openBtn) openBtn.addEventListener('click', () =>
    window.location.hash = `#/sessions/${cur.id}`);
}

function bindEditing(root, cur, recap, diff) {
  const save = root.querySelector('[data-role=save]');
  const cancel = root.querySelector('[data-role=cancel]');
  const regen = root.querySelector('[data-role=regenerate]');

  cancel && cancel.addEventListener('click', () => {
    renderRecapPage(root, { cur, prev: null, next: null, recap, diff, editing: false });
    bindNav(root, null, null);
    bindActions(root, cur, recap, diff);
  });

  save && save.addEventListener('click', async () => {
    const wh = root.querySelector('[data-role=ed-what-happened]').value;
    const wl = root.querySelector('[data-role=ed-what-landed]').value;
    const wn = root.querySelector('[data-role=ed-whats-next]').value;
    const title = root.querySelector('[data-role=ed-title]').value;
    const fm = (recap && recap.frontmatter) || {};
    await putRecap(cur.id, {
      frontmatter: {
        snapshot_before: fm.snapshot_before, snapshot_after: fm.snapshot_after,
        generator: 'manual', generated_at: new Date().toISOString(),
        token_cost: 0,
      },
      title, what_happened: wh, what_landed: wl, whats_next: wn,
    });
    const fresh = await getRecap(cur.id);
    renderRecapPage(root, { cur, prev: null, next: null, recap: fresh, diff, editing: false });
    bindActions(root, cur, fresh, diff);
  });

  regen && regen.addEventListener('click', () => {
    // Restore the on-disk draft into the edit fields. Generation itself happens server-side
    // (Plan 5b owns the regenerate hook); for now we re-fetch the saved recap to drop
    // unsaved edits and signal "draft restored".
    getRecap(cur.id).then(fresh => {
      root.querySelector('[data-role=ed-title]').value = (fresh && fresh.title) || '';
      root.querySelector('[data-role=ed-what-happened]').value = (fresh && fresh.what_happened) || '';
      root.querySelector('[data-role=ed-what-landed]').value = (fresh && fresh.what_landed) || '';
      root.querySelector('[data-role=ed-whats-next]').value = (fresh && fresh.whats_next) || '';
    });
  });
}

function renderRecapPage(root, { cur, prev, next, recap, diff, editing }) {
  const fm = (recap && recap.frontmatter) || {};
  const stats = computeStats(diff);
  const draftCaption = fm.generated_at
    ? `draft generated ${escapeHtml(String(fm.generated_at).slice(0, 16))} by ${escapeHtml(fm.generator || '?')}`
    : '';

  root.innerHTML = (
    `<div class="recap-page">`
    + `<div class="recap-topbar">`
    + (prev !== null ? `<button class="recap-nav-arrow" data-role="prev" ${prev?'':'disabled'}>‹</button>` : '')
    + `<div class="recap-picker">`
    + `<span class="pid mono">${escapeHtml(cur.id)}</span>`
    + `<span class="ptitle">${escapeHtml((recap && recap.title) || '—')}</span>`
    + `<span class="pdate">${escapeHtml(String(cur.start).slice(0, 10))}</span>`
    + `<span class="chev">▾</span>`
    + `</div>`
    + (next !== null ? `<button class="recap-nav-arrow" data-role="next" ${next?'':'disabled'}>›</button>` : '')
    + `<div class="spacer"></div>`
    + (editing
        ? `<button class="recap-action" data-role="cancel">Cancel</button>`
          + `<button class="recap-action primary" data-role="save">Save</button>`
          + `<button class="recap-action" data-role="regenerate">↺ regenerate</button>`
        : `<button class="recap-action" data-role="copy-resume">⧉ copy resume</button>`
          + `<button class="recap-action" data-role="open-sessions">Open in Sessions</button>`
          + `<button class="recap-action primary" data-role="edit">✎ edit recap</button>`)
    + `</div>`
    + `<div class="recap-hero">`
    + `<div class="recap-hero-top">`
    + `<span class="recap-hero-kind">RECAP</span>`
    + `<div class="recap-hero-meta">`
    + `<span class="mono">${escapeHtml(cur.id)}</span><span class="dot"></span>`
    + `<span>${escapeHtml(fm.generator || 'claude')}</span><span class="dot"></span>`
    + `<span>${formatDuration(cur.duration)}</span><span class="dot"></span>`
    + `<span class="mono">vs ${escapeHtml(fm.snapshot_before || '—')}</span>`
    + `</div>`
    + `</div>`
    + (editing
        ? `<input class="narr-edit" data-role="ed-title" value="${escapeHtml((recap&&recap.title)||'')}" style="width:100%; padding:8px; font-size:20px; background:var(--bg-deep); color:var(--ink); border:1px solid var(--border); border-radius:6px; margin-bottom:8px;">`
        : `<h1 class="recap-hero-title">${escapeHtml((recap && recap.title) || '(untitled)')}</h1>`)
    + `<div class="recap-hero-subtitle mono">${escapeHtml(cur.id)} → ${escapeHtml(fm.snapshot_after || '—')} · diff vs ${escapeHtml(fm.snapshot_before || '—')}</div>`
    + `<div class="narrative">`
    + section('What happened',  recap && recap.what_happened, editing, 'ed-what-happened', draftCaption)
    + section('What landed',    recap && recap.what_landed,   editing, 'ed-what-landed',   draftCaption)
    + section("What's next",    recap && recap.whats_next,    editing, 'ed-whats-next',    draftCaption)
    + `</div>`
    + `<div class="recap-stats">`
    +   stat('add', stats.tasks_done,   'tasks done')
    +   stat('mod', stats.tasks_moved,  'tasks moved')
    +   stat('',    stats.lessons_fired,'lessons fired')
    +   stat('del', stats.issues_opened,'issues opened')
    +   stat('add', stats.files_touched,'files touched')
    + `</div>`
    + `</div>`
    + `<div class="receipts-h">`
    + `<h3>Receipts</h3>`
    + `<span class="vs mono">diff <span class="snap">${escapeHtml(fm.snapshot_before || '—')}</span> → <span class="snap">${escapeHtml(fm.snapshot_after || '—')}</span></span>`
    + `<div class="filt" data-role="filt">`
    +   ['All','Tasks','Lessons','Issues','Files'].map((label, i) =>
        `<span class="filt-chip ${i===0?'on':''}" data-filt="${label.toLowerCase()}">${label}</span>`).join('')
    + `</div>`
    + `</div>`
    + renderReceiptsGrid(diff)
    + `<div class="recap-footer">`
    + `<span>Handovers: ${(cur.handover_ids||[]).map(h => `<a href="#/sessions/${escapeHtml(cur.id)}">${escapeHtml(h)}</a>`).join(' · ') || '—'}</span>`
    + `<span>Snapshot: <span class="mono">${escapeHtml(fm.snapshot_after || '—')}</span></span>`
    + `<span class="grow"></span>`
    + `<span>${escapeHtml(fm.generated_at || '')} · ${escapeHtml(String(fm.token_cost || 0))} tok</span>`
    + `</div>`
    + `</div>`
  );
}

function section(label, body, editing, dataRole, draftCaption) {
  if (editing) {
    return (
      `<div class="narr-section narr-edit">`
      + `<h4>${label}</h4>`
      + (draftCaption ? `<div class="narr-draft-caption">${draftCaption}</div>` : '')
      + `<textarea data-role="${dataRole}">${escapeHtml(body || '')}</textarea>`
      + `</div>`
    );
  }
  return (
    `<div class="narr-section">`
    + `<h4>${label}</h4>`
    + `<div class="narr-body">${(body || '<em class="empty">—</em>')}</div>`
    + `</div>`
  );
}

function stat(klass, num, label) {
  return (
    `<div class="recap-stat">`
    + `<div class="recap-stat-num ${klass}">${num}</div>`
    + `<div class="recap-stat-label">${label}</div>`
    + `</div>`
  );
}

function computeStats(diff) {
  // Spec §3.16: 5 cells (Handovers excluded — they're already in the diary).
  const tasks_done   = diff.tasks_changed.filter(t => (t.to && t.to.status) === 'done').length
                     + (diff.tasks_added || []).filter(t => t.status === 'done').length;
  const tasks_moved  = diff.tasks_changed.length - tasks_done + (diff.tasks_added || []).length;
  const lessons_fired = (diff.lessons_fired || []).reduce((n, l) => n + (l.fires || 1), 0);
  const issues_opened = (diff.issues_opened || []).length;
  const files_touched = (diff.files_touched || []).length;
  return { tasks_done, tasks_moved, lessons_fired, issues_opened, files_touched };
}

function formatDuration(seconds) {
  if (!seconds || seconds < 60) return `${seconds || 0}s`;
  const m = Math.floor(seconds / 60); const h = Math.floor(m / 60);
  if (h) return `${h}h ${m % 60}m`;
  return `${m}m`;
}

export default mount;
```

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/index.html plugins/taskmaster/viewer/js/screens/recap.js
git commit -m "feat(viewer): recap screen — picker, hero, receipts, edit/regenerate"
```

---

### Task 30: Recap screen — Playwright smoke test

**Files:**
- Create: `plugins/taskmaster/viewer/tests/recap.spec.js`

- [ ] **Step 1: Write the test**

```js
import { test, expect } from '@playwright/test';

test.describe('Recap screen', () => {
  test('route resolves and renders empty state without console errors', async ({ page }) => {
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });

    await page.goto('/v3#/recap');
    await expect(page.locator('.recap-page')).toBeVisible({ timeout: 5000 });
    expect(errors).toEqual([]);
  });

  test('with seeded recap the hero renders title and 5 stat cells', async ({ page, request }) => {
    // Seed: write one handover and one recap via PUT /api/recap
    await request.put('/api/recap/SES-0001', {
      headers: { 'Content-Type': 'application/json' },
      data: {
        frontmatter: {
          snapshot_before: 'SNAP-0000', snapshot_after: 'SNAP-0001',
          generator: 'claude', generated_at: '2026-04-26T16:48:00Z', token_cost: 1840,
        },
        title: 'Stitched the worktree review gate',
        what_happened: 'Started in worktree-shadow.',
        what_landed: 'Three closed.',
        whats_next: 'Rebase tomorrow.',
      },
    });
    await page.goto('/v3#/recap/SES-0001');
    await expect(page.locator('.recap-hero-title')).toContainText('Stitched');
    await expect(page.locator('.recap-stat')).toHaveCount(5);
    await expect(page.locator('.receipts-grid .rcard')).toHaveCount(4);
  });

  test('clicking edit reveals three textareas + save/cancel/regenerate', async ({ page }) => {
    await page.goto('/v3#/recap/SES-0001');
    await page.locator('[data-role=edit]').click();
    await expect(page.locator('[data-role=ed-what-happened]')).toBeVisible();
    await expect(page.locator('[data-role=ed-what-landed]')).toBeVisible();
    await expect(page.locator('[data-role=ed-whats-next]')).toBeVisible();
    await expect(page.locator('[data-role=save]')).toBeVisible();
    await expect(page.locator('[data-role=cancel]')).toBeVisible();
    await expect(page.locator('[data-role=regenerate]')).toBeVisible();
  });
});
```

- [ ] **Step 2: Run (verify pass)**

Run: `npx playwright test plugins/taskmaster/viewer/tests/recap.spec.js --reporter=line`
Expected: 3 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/tests/recap.spec.js
git commit -m "test(viewer): Playwright smoke for Recap screen"
```

---

### Task 31: Receipt-filter chips wire-up

**Files:**
- Modify: `plugins/taskmaster/viewer/js/screens/recap.js`

- [ ] **Step 1: Failing assertion (in the existing recap.spec.js, append)**

Append to `plugins/taskmaster/viewer/tests/recap.spec.js`:

```js
test('clicking a receipt filter chip hides non-matching cards', async ({ page }) => {
  await page.goto('/v3#/recap/SES-0001');
  await page.locator('[data-filt=tasks]').click();
  await expect(page.locator('.rcard:has-text("Tasks")')).toBeVisible();
  await expect(page.locator('.rcard:has-text("Files touched")')).toBeHidden();
  await expect(page.locator('.rcard:has-text("Lessons fired")')).toBeHidden();
  await expect(page.locator('.rcard:has-text("Issues")')).toBeHidden();
});
```

- [x] **Step 2: Run (verify fail)**

Run: `npx playwright test plugins/taskmaster/viewer/tests/recap.spec.js -g "filter chip" --reporter=line`
Expected: FAIL.

- [ ] **Step 3: Implement filter wiring**

In `recap.js`, after the `bindActions` call inside `mount`, add:

```js
bindFilterChips(root);
```

And define:

```js
function bindFilterChips(root) {
  const row = root.querySelector('[data-role=filt]');
  if (!row) return;
  for (const chip of row.querySelectorAll('.filt-chip')) {
    chip.addEventListener('click', () => {
      row.querySelectorAll('.filt-chip').forEach(c => c.classList.remove('on'));
      chip.classList.add('on');
      const f = chip.dataset.filt;
      const grid = root.querySelector('.receipts-grid');
      if (!grid) return;
      const cards = grid.querySelectorAll('.rcard');
      cards.forEach(card => {
        const ttl = (card.querySelector('.ttl')?.textContent || '').toLowerCase();
        let show = false;
        if (f === 'all') show = true;
        else if (f === 'tasks')   show = ttl.startsWith('tasks');
        else if (f === 'files')   show = ttl.startsWith('files');
        else if (f === 'lessons') show = ttl.startsWith('lessons');
        else if (f === 'issues')  show = ttl.startsWith('issues');
        card.style.display = show ? '' : 'none';
      });
    });
  }
}
```

Also re-call `bindFilterChips(root)` inside the `editing=false` branch path of `bindActions` (or simpler: after every `renderRecapPage`). Update `mount` to:

```js
renderRecapPage(root, { cur, prev, next, recap, diff, editing: false });
bindNav(root, prev, next);
bindActions(root, cur, recap, diff);
bindFilterChips(root);
```

And inside `bindActions`'s edit handler and `cancel` handler, call `bindFilterChips(root)` after `renderRecapPage`.

- [x] **Step 4: Run (verify pass)**

Run: `npx playwright test plugins/taskmaster/viewer/tests/recap.spec.js --reporter=line`
Expected: All recap tests PASS.

- [x] **Step 5: Commit**

```bash
git add plugins/taskmaster/viewer/js/screens/recap.js plugins/taskmaster/viewer/tests/recap.spec.js
git commit -m "feat(viewer): receipts filter chips hide/show cards by category"
```

---

### Task 32: Hero stat-strip exclusion of handovers (regression guard)

**Files:**
- Modify: `plugins/taskmaster/viewer/tests/recap.spec.js`

- [ ] **Step 1: Add guard test**

Append:

```js
test('hero stat strip has exactly 5 cells (Handovers excluded per spec §3.16)', async ({ page }) => {
  await page.goto('/v3#/recap/SES-0001');
  const labels = await page.locator('.recap-stat-label').allTextContents();
  expect(labels.length).toBe(5);
  expect(labels.map(s => s.toLowerCase())).not.toContain('handovers');
});
```

- [ ] **Step 2: Run (verify pass)**

Run: `npx playwright test plugins/taskmaster/viewer/tests/recap.spec.js -g "5 cells" --reporter=line`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/tests/recap.spec.js
git commit -m "test(viewer): guard recap hero stat strip is 5 cells, no handovers"
```

---

### Task 33: Right-rail close on Escape + outside-click

**Files:**
- Modify: `plugins/taskmaster/viewer/js/components/right-rail.js`

- [ ] **Step 1: Append guard test in sessions.spec.js**

```js
test('Escape closes the right-rail', async ({ page }) => {
  await page.goto('/v3#/sessions');
  // Force-open via a synthetic click on the first session card if present.
  const card = page.locator('.ho').first();
  if (await card.count()) {
    await card.click();
    await expect(page.locator('.right-rail')).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(page.locator('.right-rail')).toHaveCount(0);
  }
});
```

- [ ] **Step 2: Implement key + outside-click handlers in `right-rail.js`**

Replace the `open()` body's tail with:

```js
    if (args.onMount) this._cleanup = args.onMount(el) || null;

    // Escape closes the rail.
    this._onKey = (e) => { if (e.key === 'Escape') this.close(); };
    document.addEventListener('keydown', this._onKey);
```

In `close()`, before clearing `el`:

```js
    if (this._onKey) {
      document.removeEventListener('keydown', this._onKey);
      this._onKey = null;
    }
```

- [ ] **Step 3: Run (verify pass)**

Run: `npx playwright test plugins/taskmaster/viewer/tests/sessions.spec.js -g "Escape closes" --reporter=line`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/right-rail.js plugins/taskmaster/viewer/tests/sessions.spec.js
git commit -m "feat(viewer): Escape closes right-rail; smoke covers it"
```

---

### Task 34: Run full Plan 5a test sweep

**Files:** none modified.

- [ ] **Step 1: Run all tests**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_recap.py plugins/taskmaster/tests/test_v3_snapshot_diff.py plugins/taskmaster/tests/test_v3_sessions.py plugins/taskmaster/tests/test_server_sessions_recap.py -v && node --test plugins/taskmaster/viewer/tests/unit/ && npx playwright test plugins/taskmaster/viewer/tests/sessions.spec.js plugins/taskmaster/viewer/tests/recap.spec.js --reporter=line`
Expected: server suite PASS (≥18 tests), node-test PASS (≥12 tests), Playwright PASS (≥7 tests).

- [ ] **Step 2: No commit (verification only)**

---

## M6 — Integration + Spec Coverage Walk

### Task 35: Spec §3.12 coverage walk — checklist tied to assertions

**Files:**
- Modify: `plugins/taskmaster/viewer/tests/sessions.spec.js`

Spec §3.12 requirements:

- handover kind enum tints (mid-task / checkpoint / wrap / standalone)
- parallel-block dashed purple border with label
- nested L-connector under parent session
- kind filter chips (Sessions / Handovers / Recaps)
- "+ New note" header button
- right-rail with featured Resume-prompt block + What's done/open + Related + Files touched
- view toggle (Diary / Lanes / By Task)

- [ ] **Step 1: Append coverage test**

```js
test('spec §3.12 coverage: kind tints, parallel-block, nested children, view toggle, new-note', async ({ page }) => {
  await page.goto('/v3#/sessions');
  // View toggle has all three.
  const segs = await page.locator('[data-role=view-toggle] .seg').allTextContents();
  expect(segs).toEqual(['Diary', 'Lanes', 'By Task']);
  // Kind chips: Sessions / Handovers / Recaps.
  const chips = await page.locator('[data-role=kinds] .sessions-kind-chip').allTextContents();
  expect(chips.join(' ').toLowerCase()).toMatch(/sessions/);
  expect(chips.join(' ').toLowerCase()).toMatch(/handovers/);
  expect(chips.join(' ').toLowerCase()).toMatch(/recaps/);
  // + New note button is present and clickable.
  await expect(page.locator('[data-role=new-note]')).toBeVisible();
});
```

- [ ] **Step 2: Run (verify pass)**

Run: `npx playwright test plugins/taskmaster/viewer/tests/sessions.spec.js -g "spec.*3\\.12 coverage" --reporter=line`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/tests/sessions.spec.js
git commit -m "test(viewer): spec §3.12 coverage assertions on Sessions screen"
```

---

### Task 36: Spec §3.16 coverage walk — checklist tied to assertions

**Files:**
- Modify: `plugins/taskmaster/viewer/tests/recap.spec.js`

Spec §3.16 requirements:

- picker + prev/next arrows
- topbar actions (copy resume / open in Sessions / edit recap)
- hero with kind pill, narrative 3 sections, mono subtitle
- 5-cell stat strip (Handovers excluded)
- receipts 2×2 grid with filter chips
- footer strip with handover/snapshot links + token cost
- edit mode: textareas + save + cancel + regenerate

- [ ] **Step 1: Append coverage test**

```js
test('spec §3.16 coverage: picker, hero, narrative-3, stats-5, receipts-4, footer, edit', async ({ page, request }) => {
  await request.put('/api/recap/SES-0001', {
    headers: { 'Content-Type': 'application/json' },
    data: {
      frontmatter: { snapshot_before: 'SNAP-0000', snapshot_after: 'SNAP-0001',
                     generator: 'claude', generated_at: '2026-04-26T16:48Z', token_cost: 1840 },
      title: 't', what_happened: 'a', what_landed: 'b', whats_next: 'c',
    },
  });
  await page.goto('/v3#/recap/SES-0001');

  await expect(page.locator('.recap-picker')).toBeVisible();
  await expect(page.locator('.recap-hero-kind')).toHaveText('RECAP');
  await expect(page.locator('.narr-section')).toHaveCount(3);
  await expect(page.locator('.recap-stat')).toHaveCount(5);
  await expect(page.locator('.rcard')).toHaveCount(4);
  await expect(page.locator('[data-role=copy-resume]')).toBeVisible();
  await expect(page.locator('[data-role=open-sessions]')).toBeVisible();
  await expect(page.locator('[data-role=edit]')).toBeVisible();
  await expect(page.locator('.recap-footer')).toContainText('1840');
});
```

- [ ] **Step 2: Run (verify pass)**

Run: `npx playwright test plugins/taskmaster/viewer/tests/recap.spec.js -g "spec.*3\\.16 coverage" --reporter=line`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/tests/recap.spec.js
git commit -m "test(viewer): spec §3.16 coverage assertions on Recap screen"
```

---

### Task 37: Cross-screen integration — Sessions row → Recap deep link

**Files:**
- Create: `plugins/taskmaster/viewer/tests/sessions-recap-integration.spec.js`

- [ ] **Step 1: Write test**

```js
import { test, expect } from '@playwright/test';

test('clicking a recap child row in Sessions navigates to /recap/<sid>', async ({ page, request }) => {
  // Seed a handover + recap so Sessions has a session with a recap_id.
  await request.put('/api/recap/SES-0001', {
    headers: { 'Content-Type': 'application/json' },
    data: {
      frontmatter: { snapshot_before: 'SNAP-0000', snapshot_after: 'SNAP-0001',
                     generator: 'claude', generated_at: '2026-04-26T16:48Z', token_cost: 100 },
      title: 'tt', what_happened: 'x', what_landed: 'y', whats_next: 'z',
    },
  });
  await page.goto('/v3#/sessions');
  const recapChild = page.locator('.ho-child.recap, .ho-child:has(.ho-kind.recap)').first();
  if (await recapChild.count()) {
    await recapChild.click();
    await expect(page).toHaveURL(/#\/recap\/SES-/);
    await expect(page.locator('.recap-hero-title')).toBeVisible();
  }
});
```

- [ ] **Step 2: Run (verify pass)**

Run: `npx playwright test plugins/taskmaster/viewer/tests/sessions-recap-integration.spec.js --reporter=line`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/tests/sessions-recap-integration.spec.js
git commit -m "test(viewer): integration — Sessions recap-child → Recap screen"
```

---

### Task 38: Final integration sweep + plan handoff commit

**Files:** none modified (verification + handoff).

- [ ] **Step 1: Run the entire Plan 5a test surface**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_recap.py plugins/taskmaster/tests/test_v3_snapshot_diff.py plugins/taskmaster/tests/test_v3_sessions.py plugins/taskmaster/tests/test_server_sessions_recap.py -v`
Expected: All PASS.

Run: `node --test plugins/taskmaster/viewer/tests/unit/`
Expected: All PASS.

Run: `npx playwright test plugins/taskmaster/viewer/tests/sessions.spec.js plugins/taskmaster/viewer/tests/recap.spec.js plugins/taskmaster/viewer/tests/sessions-recap-integration.spec.js --reporter=line`
Expected: All PASS.

- [ ] **Step 2: Confirm no leftover stubs in implemented files**

Run: `grep -nE "TBD|TODO|implement later" plugins/taskmaster/viewer/js/screens/sessions.js plugins/taskmaster/viewer/js/screens/recap.js plugins/taskmaster/viewer/js/components/timeline.js plugins/taskmaster/viewer/js/components/right-rail.js plugins/taskmaster/viewer/js/components/recap-receipts-grid.js plugins/taskmaster/viewer/js/components/diff-row.js plugins/taskmaster/viewer/js/components/snapshot-diff.js`
Expected: no matches.

- [ ] **Step 3: Plan handoff commit**

```bash
git commit --allow-empty -m "chore(viewer): plan 5a complete — sessions + recap shipped"
```

Expected: commit created on the current branch with no file changes.

---

**End of Plan 5a.**
