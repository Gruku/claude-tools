# Taskmaster Viewer Redesign — Plan 5b: Lessons + Issues Screens

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the **Lessons** screen (three-shelf library with Core/Active/Retired progressive de-emphasis, active+passive signals separated, hover-Reinforce button) and the **Issues** screen (Hybrid: Investigating + Open columns, Resolved shelf below; severity hexagon glyph, console-style location, italic-serif symptom, Repro block, Impact paragraph, severity-tiered aging bar, ⊘ blocks N chip). Extends the v3 lesson schema with `reinforce_events[]` and adds the server-side reinforcement endpoint.

**Architecture:** ES-module screens + components living under `plugins/taskmaster/viewer/`. Server side adds two MCP tools (`lesson_reinforce`, `lesson_list_extended`, `issue_list_extended`) and three HTTP endpoints (`POST /api/lessons/<id>/reinforce`, `GET /api/lessons`, `GET /api/issues`). All view preferences read from the existing `viewer.json` (`prefs.lessons.thresholds`, `prefs.issues.aging`, `prefs.screens.lessons.view`, `prefs.screens.issues.view`). Plan 5a owns shared timeline / right-rail / recap-grid / diff-row components — Plan 5b imports those it needs and does not redefine them.

**Tech Stack:** Vanilla HTML/CSS/JS (ES modules, no bundler), Python 3 + `fastmcp` + `BaseHTTPRequestHandler`, `pytest`, `node --test` for pure-data unit tests, Playwright for UI smoke.

**Spec reference:** `docs/superpowers/specs/2026-04-26-taskmaster-viewer-redesign.md` §3.13 (Lessons) and §3.14 (Issues).

> **Architectural Conventions inherited from Plan 1.** Module style, screen module shape (`mount(root, { params, store, api, prefs })` + `meta`), CSS naming (prefix-per-file, no global `.card`), state via `store.js`, mutations via `api.js`, hash routing, `.taskmaster/viewer.json` persistence, pytest with `tmp_path`, Playwright smoke. Do not redefine.

> **Plan 5a owns shared components.** `js/components/right-rail.js`, `js/components/timeline.js`, `js/components/recap-receipts-grid.js`, `js/components/diff-row.js` are authored in Plan 5a. Plan 5b imports `diff-row.js` if useful inside the recap path; otherwise it does not touch 5a's files.

---

## File Structure

**Server (Python — modify):**

```
plugins/taskmaster/
├── taskmaster_v3.py         # + lesson_reinforce(), _ensure_reinforce_events() migration
├── backlog_server.py        # + lesson_reinforce / lesson_list_extended / issue_list_extended MCP tools
│                            # + POST /api/lessons/<id>/reinforce
│                            # + GET /api/lessons
│                            # + GET /api/issues
└── tests/
    ├── test_v3_lesson_reinforce.py     # NEW — unit tests for migration + reinforce helper
    ├── test_server_lessons.py          # NEW — HTTP + tool tests for lessons
    └── test_server_issues.py           # NEW — HTTP + tool tests for issues
```

**Client — Lessons screen (NEW):**

```
plugins/taskmaster/viewer/
├── css/screens/lessons.css
├── js/screens/lessons.js                       # replaces stub from Plan 1
└── js/components/
    ├── lesson-card.js                          # all three shelves
    ├── sparkline.js                            # active-signal gold line + count + last-fired
    ├── dot-meter.js                            # passive-signal 5-dot meter
    └── anchor-pills.js                         # mono pills with "When:" label
```

**Client — Issues screen (NEW):**

```
plugins/taskmaster/viewer/
├── css/screens/issues.css
├── js/screens/issues.js                        # replaces stub from Plan 1
└── js/components/
    ├── issue-card.js                           # bug-report flavor
    ├── severity-glyph.js                       # SVG hexagon <symbol> defs + <use>
    └── aging-bar.js                            # severity-tiered Fresh/Aging/Stale
```

**Tests — pure-data + UI:**

```
plugins/taskmaster/viewer/tests/
├── unit/
│   ├── lesson-shelf-placement.test.js          # (lesson, thresholds) → 'core' | 'active' | 'retired'
│   ├── issue-aging.test.js                     # (issue, severity_base) → { percent, tier }
│   └── issue-blocks-count.test.js              # (issue, tasks_index) → integer
├── lessons.spec.js                             # Playwright smoke
└── issues.spec.js                              # Playwright smoke
```

---

## Milestones

- **M1 — Server lesson reinforce + migration** (Tasks 1–4): schema extension, `_ensure_reinforce_events`, `lesson_reinforce()` helper, MCP tool, HTTP `POST /api/lessons/<id>/reinforce`.
- **M2 — Extended list endpoints** (Tasks 5–8): pure-Python shelf-placement and aging computers, `lesson_list_extended` / `issue_list_extended` MCP tools, `GET /api/lessons`, `GET /api/issues`.
- **M3 — Shared components** (Tasks 9–17): `severity-glyph.js`, `aging-bar.js`, `sparkline.js`, `dot-meter.js`, `anchor-pills.js` plus their pure-data tests.
- **M4 — Lessons screen + lesson-card** (Tasks 18–32): JS-side `computeShelfPlacement`, `lesson-card.js`, `lessons.js` with three shelves, view toggle, Reinforce flow, Playwright smoke.
- **M5 — Issues screen + issue-card** (Tasks 33–48): JS-side `computeAgingTier`, `computeBlocksCount`, `severity_label`, `issue-card.js`, `issues.js` with hybrid layout + Resolved shelf, Playwright smoke.
- **M6 — Integration smoke + spec coverage** (Tasks 49–55): cross-screen routing, prefs round-trip, full-spec walk against §3.13 / §3.14, conventional commit gate.

---

## M1 — Server Lesson Reinforce + Migration

### Task 1: Extend the lesson schema with `reinforce_events`

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py` (lesson load path)
- Create: `plugins/taskmaster/tests/test_v3_lesson_reinforce.py`

- [x] **Step 1: Write the failing test**

Create `plugins/taskmaster/tests/test_v3_lesson_reinforce.py`:

```python
"""Tests for lesson reinforce_events extension and _ensure_reinforce_events migration."""
import json
from pathlib import Path

import pytest


def _write_lesson(root: Path, lesson_id: str, body_extra: str = "") -> Path:
    p = root / ".taskmaster" / "lessons" / f"{lesson_id}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "---\n"
        f"id: {lesson_id}\n"
        f"title: Sample lesson\n"
        "kind: gotcha\n"
        "tier: active\n"
        "triggers:\n"
        "  files: ['**/*.css']\n"
        "  task_titles_match: []\n"
        "  task_kinds: []\n"
        "reinforce_count: 3\n"
        "last_reinforced: 2026-04-20T10:00:00Z\n"
        "created: 2026-03-18T10:00:00Z\n"
        "related_tasks: []\n"
        "related_issues: []\n"
        f"{body_extra}"
        "---\n"
        "Lesson body.\n"
    )
    return p


def test_ensure_reinforce_events_backfills_empty_array(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_lesson(tmp_path, "L-001")

    from taskmaster_v3 import load_lesson, _ensure_reinforce_events

    lesson = load_lesson("L-001")
    assert "reinforce_events" in lesson
    assert lesson["reinforce_events"] == []

    # Direct call is idempotent on already-migrated data
    populated = {"id": "L-002", "reinforce_events": [{"at": "2026-04-25T00:00:00Z", "source": "user", "note": ""}]}
    _ensure_reinforce_events(populated)
    assert len(populated["reinforce_events"]) == 1


def test_load_lesson_preserves_existing_reinforce_events(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_lesson(
        tmp_path,
        "L-003",
        body_extra=(
            "reinforce_events:\n"
            "  - at: 2026-04-22T09:00:00Z\n"
            "    source: user\n"
            "    note: 'paid attention this time'\n"
        ),
    )

    from taskmaster_v3 import load_lesson

    lesson = load_lesson("L-003")
    assert len(lesson["reinforce_events"]) == 1
    assert lesson["reinforce_events"][0]["source"] == "user"
    assert lesson["reinforce_events"][0]["note"] == "paid attention this time"
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_lesson_reinforce.py -v`
Expected: FAIL with `ImportError: cannot import name '_ensure_reinforce_events'` (or KeyError on `reinforce_events`).

- [x] **Step 3: Implement `_ensure_reinforce_events` and wire it into `load_lesson`**

In `plugins/taskmaster/taskmaster_v3.py`, locate the existing `load_lesson(lesson_id)` function. Add the migration helper above it and call it at the end of `load_lesson`:

```python
def _ensure_reinforce_events(lesson: dict) -> dict:
    """One-time migration: legacy lesson files don't carry reinforce_events.
    Backfill an empty list so downstream code can append unconditionally.
    Idempotent: if the key is already present, it's left untouched.
    """
    if "reinforce_events" not in lesson or lesson["reinforce_events"] is None:
        lesson["reinforce_events"] = []
    return lesson


def load_lesson(lesson_id: str) -> dict:
    p = Path(".taskmaster") / "lessons" / f"{lesson_id}.md"
    raw = p.read_text(encoding="utf-8")
    fm, body = _split_frontmatter(raw)
    lesson = yaml.safe_load(fm) or {}
    lesson["_body"] = body
    _ensure_reinforce_events(lesson)
    return lesson
```

(If `load_lesson` already exists with a different shape, keep its signature — only add the `_ensure_reinforce_events(lesson)` call before returning, and define the helper at module scope.)

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_lesson_reinforce.py -v`
Expected: 2 tests PASS.

- [x] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_v3_lesson_reinforce.py
git commit -m "feat(taskmaster): backfill lesson reinforce_events on load"
```

---

### Task 2: Implement `lesson_reinforce()` helper

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py`
- Modify: `plugins/taskmaster/tests/test_v3_lesson_reinforce.py`

- [x] **Step 1: Write the failing test**

Append to `plugins/taskmaster/tests/test_v3_lesson_reinforce.py`:

```python
def test_lesson_reinforce_appends_event_and_bumps_counters(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_lesson(tmp_path, "L-010")

    from taskmaster_v3 import lesson_reinforce, load_lesson

    summary = lesson_reinforce("L-010", source="user", note="caught the bug")
    assert summary["id"] == "L-010"
    assert summary["reinforce_count"] == 4  # was 3
    assert summary["reinforce_events"][-1]["source"] == "user"
    assert summary["reinforce_events"][-1]["note"] == "caught the bug"
    assert summary["last_reinforced"]  # ISO string

    # Reload from disk and confirm persistence
    lesson = load_lesson("L-010")
    assert lesson["reinforce_count"] == 4
    assert lesson["reinforce_events"][-1]["source"] == "user"


def test_lesson_reinforce_rejects_bad_source(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_lesson(tmp_path, "L-011")

    from taskmaster_v3 import lesson_reinforce

    with pytest.raises(ValueError):
        lesson_reinforce("L-011", source="other-thing")


def test_lesson_reinforce_unknown_id_raises(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".taskmaster" / "lessons").mkdir(parents=True, exist_ok=True)

    from taskmaster_v3 import lesson_reinforce

    with pytest.raises(FileNotFoundError):
        lesson_reinforce("L-999", source="user")
```

- [x] **Step 2: Run tests to verify they fail**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_lesson_reinforce.py -v -k reinforce`
Expected: FAIL with `ImportError: cannot import name 'lesson_reinforce'`.

- [x] **Step 3: Implement `lesson_reinforce`**

Add to `plugins/taskmaster/taskmaster_v3.py` (near `load_lesson`):

```python
LESSON_REINFORCE_SOURCES = {"user", "claude", "skill"}


def lesson_reinforce(lesson_id: str, source: str = "user", note: str = "") -> dict:
    """Append a reinforcement event to a lesson and persist.

    Returns the updated lesson summary (frontmatter dict, including
    reinforce_count, last_reinforced, and the appended reinforce_events list).

    Raises:
        FileNotFoundError: if the lesson file doesn't exist.
        ValueError: if `source` is not in LESSON_REINFORCE_SOURCES.
    """
    if source not in LESSON_REINFORCE_SOURCES:
        raise ValueError(
            f"source must be one of {sorted(LESSON_REINFORCE_SOURCES)}, got {source!r}"
        )

    from datetime import datetime, timezone

    p = Path(".taskmaster") / "lessons" / f"{lesson_id}.md"
    if not p.exists():
        raise FileNotFoundError(p)

    lesson = load_lesson(lesson_id)
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    event = {"at": now_iso, "source": source, "note": note or ""}
    lesson.setdefault("reinforce_events", []).append(event)
    lesson["reinforce_count"] = int(lesson.get("reinforce_count") or 0) + 1
    lesson["last_reinforced"] = now_iso

    save_lesson(lesson)
    # Strip body from the returned summary
    summary = {k: v for k, v in lesson.items() if k != "_body"}
    return summary
```

(If a `save_lesson(lesson)` helper does not exist alongside `load_lesson`, add it: serialize the frontmatter dict back to YAML, preserve `_body`, atomic-write via `atomic_write`.)

- [x] **Step 4: Run tests to verify they pass**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_lesson_reinforce.py -v`
Expected: 5 tests PASS.

- [x] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_v3_lesson_reinforce.py
git commit -m "feat(taskmaster): lesson_reinforce() appends event + bumps counters"
```

---

### Task 3: Add `lesson_reinforce` MCP tool

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py`
- Modify: `plugins/taskmaster/tests/test_v3_lesson_reinforce.py`

- [x] **Step 1: Write the failing test**

Append to `plugins/taskmaster/tests/test_v3_lesson_reinforce.py`:

```python
def test_lesson_reinforce_mcp_tool_returns_json_summary(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_lesson(tmp_path, "L-020")

    from backlog_server import lesson_reinforce as tool

    out = tool("L-020", source="user", note="")
    assert "L-020" in out
    payload = json.loads(out)
    assert payload["reinforce_count"] == 4
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_lesson_reinforce.py::test_lesson_reinforce_mcp_tool_returns_json_summary -v`
Expected: FAIL with `ImportError: cannot import name 'lesson_reinforce' from 'backlog_server'`.

- [x] **Step 3: Add the MCP tool**

In `plugins/taskmaster/backlog_server.py`, near other lesson tools, add:

```python
@mcp.tool()
def lesson_reinforce(lesson_id: str, source: str = "user", note: str = "") -> str:
    """Record a reinforcement event for a lesson.

    Args:
        lesson_id: e.g. "L-014"
        source: one of "user" | "claude" | "skill"
        note: optional free-text annotation

    Returns the updated lesson summary as a JSON string.
    """
    import json as _json
    from taskmaster_v3 import lesson_reinforce as _impl

    try:
        summary = _impl(lesson_id, source=source, note=note)
    except FileNotFoundError:
        return _json.dumps({"ok": False, "error": f"lesson {lesson_id} not found"})
    except ValueError as e:
        return _json.dumps({"ok": False, "error": str(e)})
    return _json.dumps(summary, indent=2, default=str)
```

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_lesson_reinforce.py -v -k mcp_tool`
Expected: PASS.

- [x] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_v3_lesson_reinforce.py
git commit -m "feat(taskmaster): lesson_reinforce MCP tool"
```

---

### Task 4: Add `POST /api/lessons/<id>/reinforce` HTTP endpoint

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py` (`_Handler` request handler)
- Create: `plugins/taskmaster/tests/test_server_lessons.py`

- [x] **Step 1: Write the failing test**

Create `plugins/taskmaster/tests/test_server_lessons.py`:

```python
"""HTTP tests for /api/lessons routes. Reuses the running_server fixture from test_server_api."""
import json
import urllib.request
from pathlib import Path

import pytest

from tests.test_server_api import running_server  # noqa: F401  (re-export fixture)


def _write_lesson(root: Path, lesson_id: str, **overrides):
    base = {
        "id": lesson_id,
        "title": "Sample",
        "kind": "gotcha",
        "tier": "active",
        "triggers": {"files": ["**/*.css"], "task_titles_match": [], "task_kinds": []},
        "reinforce_count": 2,
        "last_reinforced": "2026-04-15T00:00:00Z",
        "created": "2026-03-01T00:00:00Z",
        "related_tasks": [],
        "related_issues": [],
        "reinforce_events": [],
    }
    base.update(overrides)
    p = root / ".taskmaster" / "lessons" / f"{lesson_id}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    fm_lines = []
    import yaml
    fm_lines.append("---")
    fm_lines.append(yaml.safe_dump(base, sort_keys=False).rstrip())
    fm_lines.append("---")
    fm_lines.append("Body.")
    p.write_text("\n".join(fm_lines))


def test_post_reinforce_bumps_counter_and_returns_summary(running_server, tmp_path):
    base, _ = running_server
    _write_lesson(tmp_path, "L-100")

    body = json.dumps({"source": "user", "note": "deliberate apply"}).encode()
    req = urllib.request.Request(
        f"{base}/api/lessons/L-100/reinforce",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req)
    assert resp.status == 200
    payload = json.loads(resp.read())
    assert payload["id"] == "L-100"
    assert payload["reinforce_count"] == 3


def test_post_reinforce_unknown_id_returns_404(running_server):
    base, _ = running_server
    body = json.dumps({"source": "user"}).encode()
    req = urllib.request.Request(
        f"{base}/api/lessons/L-NOPE/reinforce",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(req)
    assert exc.value.code == 404


def test_post_reinforce_rejects_bad_source(running_server, tmp_path):
    base, _ = running_server
    _write_lesson(tmp_path, "L-101")
    body = json.dumps({"source": "alien"}).encode()
    req = urllib.request.Request(
        f"{base}/api/lessons/L-101/reinforce",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(req)
    assert exc.value.code == 400
```

- [x] **Step 2: Run tests to verify they fail**

Run: `python -m pytest plugins/taskmaster/tests/test_server_lessons.py -v`
Expected: FAIL — 404/405 on POST.

- [x] **Step 3: Add `do_POST` route handler**

In `plugins/taskmaster/backlog_server.py`, inside `_Handler`, add (or extend) `do_POST`:

```python
def do_POST(self):
    import json
    import re
    from taskmaster_v3 import lesson_reinforce as _reinforce

    m = re.fullmatch(r"/api/lessons/([A-Za-z0-9_\-]+)/reinforce", self.path)
    if m:
        lesson_id = m.group(1)
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode("utf-8") if length else ""
        try:
            data = json.loads(raw) if raw else {}
        except Exception as e:
            self._send_json(400, {"ok": False, "error": f"invalid JSON: {e}"})
            return
        source = data.get("source", "user")
        note = data.get("note", "")
        try:
            summary = _reinforce(lesson_id, source=source, note=note)
        except FileNotFoundError:
            self._send_json(404, {"ok": False, "error": f"lesson {lesson_id} not found"})
            return
        except ValueError as e:
            self._send_json(400, {"ok": False, "error": str(e)})
            return
        self._send_json(200, summary)
        return

    self.send_response(404)
    self.end_headers()
```

- [x] **Step 4: Run tests to verify they pass**

Run: `python -m pytest plugins/taskmaster/tests/test_server_lessons.py -v`
Expected: 3 tests PASS.

- [x] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_server_lessons.py
git commit -m "feat(taskmaster): POST /api/lessons/<id>/reinforce"
```

---

## M2 — Extended List Endpoints

### Task 5: Pure-Python `compute_lesson_shelf` helper

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py`
- Modify: `plugins/taskmaster/tests/test_v3_lesson_reinforce.py`

- [x] **Step 1: Write the failing test**

Append to `plugins/taskmaster/tests/test_v3_lesson_reinforce.py`:

```python
def test_compute_lesson_shelf_core_when_recent_and_volume(tmp_path):
    from datetime import datetime, timedelta, timezone
    from taskmaster_v3 import compute_lesson_shelf

    now = datetime(2026, 4, 26, tzinfo=timezone.utc)
    events = [
        {"at": (now - timedelta(days=d)).strftime("%Y-%m-%dT%H:%M:%SZ"), "source": "user", "note": ""}
        for d in [1, 3, 5, 10, 20, 35, 45]
    ]
    thresholds = {
        "core_count": 7, "core_window_days": 60,
        "core_recency_days": 14, "retired_after_days": 30,
    }
    assert compute_lesson_shelf({"reinforce_events": events}, thresholds, now=now) == "core"


def test_compute_lesson_shelf_active_when_recent_but_low_volume(tmp_path):
    from datetime import datetime, timedelta, timezone
    from taskmaster_v3 import compute_lesson_shelf

    now = datetime(2026, 4, 26, tzinfo=timezone.utc)
    events = [
        {"at": (now - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ"), "source": "user", "note": ""}
    ]
    thresholds = {"core_count": 7, "core_window_days": 60, "core_recency_days": 14, "retired_after_days": 30}
    assert compute_lesson_shelf({"reinforce_events": events}, thresholds, now=now) == "active"


def test_compute_lesson_shelf_retired_when_no_recent(tmp_path):
    from datetime import datetime, timedelta, timezone
    from taskmaster_v3 import compute_lesson_shelf

    now = datetime(2026, 4, 26, tzinfo=timezone.utc)
    events = [
        {"at": (now - timedelta(days=45)).strftime("%Y-%m-%dT%H:%M:%SZ"), "source": "user", "note": ""}
    ]
    thresholds = {"core_count": 7, "core_window_days": 60, "core_recency_days": 14, "retired_after_days": 30}
    assert compute_lesson_shelf({"reinforce_events": events}, thresholds, now=now) == "retired"


def test_compute_lesson_shelf_active_when_high_volume_but_no_recent_fire(tmp_path):
    """High volume in window but nothing in last 14d → active, not core."""
    from datetime import datetime, timedelta, timezone
    from taskmaster_v3 import compute_lesson_shelf

    now = datetime(2026, 4, 26, tzinfo=timezone.utc)
    events = [
        {"at": (now - timedelta(days=d)).strftime("%Y-%m-%dT%H:%M:%SZ"), "source": "user", "note": ""}
        for d in [16, 18, 20, 22, 24, 26, 28, 29]
    ]
    thresholds = {"core_count": 7, "core_window_days": 60, "core_recency_days": 14, "retired_after_days": 30}
    assert compute_lesson_shelf({"reinforce_events": events}, thresholds, now=now) == "active"
```

- [x] **Step 2: Run tests to verify they fail**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_lesson_reinforce.py -v -k shelf`
Expected: FAIL — `ImportError`.

- [x] **Step 3: Implement `compute_lesson_shelf`**

Add to `plugins/taskmaster/taskmaster_v3.py`:

```python
def compute_lesson_shelf(lesson: dict, thresholds: dict, now=None) -> str:
    """Compute shelf placement: 'core' | 'active' | 'retired'.

    Rules (driven by reinforce_events only — passive anchor matches are ignored):
        core      — count(events within core_window_days) >= core_count
                    AND at least one event within core_recency_days
        retired   — no events within retired_after_days
        active    — otherwise (any event within retired_after_days that
                    doesn't qualify as core)
    """
    from datetime import datetime, timedelta, timezone

    if now is None:
        now = datetime.now(timezone.utc)

    events = lesson.get("reinforce_events") or []

    def _parse(e):
        return datetime.strptime(e["at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)

    parsed = [_parse(e) for e in events]

    core_count = int(thresholds.get("core_count", 7))
    core_window = timedelta(days=int(thresholds.get("core_window_days", 60)))
    core_recency = timedelta(days=int(thresholds.get("core_recency_days", 14)))
    retired_after = timedelta(days=int(thresholds.get("retired_after_days", 30)))

    in_window = [t for t in parsed if (now - t) <= core_window]
    in_recency = [t for t in parsed if (now - t) <= core_recency]
    in_active = [t for t in parsed if (now - t) <= retired_after]

    if len(in_window) >= core_count and len(in_recency) >= 1:
        return "core"
    if not in_active:
        return "retired"
    return "active"
```

- [x] **Step 4: Run tests to verify they pass**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_lesson_reinforce.py -v -k shelf`
Expected: 4 tests PASS.

- [x] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_v3_lesson_reinforce.py
git commit -m "feat(taskmaster): compute_lesson_shelf core/active/retired classifier"
```

---

### Task 6: `lesson_list_extended` MCP tool + `GET /api/lessons` endpoint

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py`
- Modify: `plugins/taskmaster/tests/test_server_lessons.py`

- [x] **Step 1: Write the failing test**

Append to `plugins/taskmaster/tests/test_server_lessons.py`:

```python
def test_get_lessons_returns_list_with_shelf_placement(running_server, tmp_path):
    from datetime import datetime, timedelta, timezone
    base, _ = running_server
    now = datetime.now(timezone.utc)
    fresh_events = [
        {"at": (now - timedelta(days=d)).strftime("%Y-%m-%dT%H:%M:%SZ"), "source": "user", "note": ""}
        for d in [1, 2, 3, 4, 5, 6, 7, 8]
    ]
    cold_events = [
        {"at": (now - timedelta(days=60)).strftime("%Y-%m-%dT%H:%M:%SZ"), "source": "user", "note": ""}
    ]

    _write_lesson(tmp_path, "L-CORE", reinforce_count=8, reinforce_events=fresh_events)
    _write_lesson(tmp_path, "L-COLD", reinforce_count=1, reinforce_events=cold_events)

    resp = urllib.request.urlopen(f"{base}/api/lessons")
    assert resp.status == 200
    payload = json.loads(resp.read())
    assert "lessons" in payload
    by_id = {l["id"]: l for l in payload["lessons"]}
    assert by_id["L-CORE"]["shelf"] == "core"
    assert by_id["L-COLD"]["shelf"] == "retired"
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest plugins/taskmaster/tests/test_server_lessons.py -v -k get_lessons`
Expected: FAIL — 404.

- [x] **Step 3: Implement the tool + route**

In `plugins/taskmaster/backlog_server.py`:

```python
@mcp.tool()
def lesson_list_extended() -> str:
    """List all lessons with computed shelf placement using current viewer thresholds."""
    import json as _json
    from taskmaster_v3 import (
        list_lesson_ids, load_lesson, compute_lesson_shelf, load_viewer_prefs,
    )

    prefs = load_viewer_prefs()
    thresholds = prefs.get("lessons", {}).get("thresholds", {})
    out = []
    for lid in list_lesson_ids():
        try:
            lesson = load_lesson(lid)
        except Exception:
            continue
        summary = {k: v for k, v in lesson.items() if k != "_body"}
        summary["shelf"] = compute_lesson_shelf(lesson, thresholds)
        out.append(summary)
    return _json.dumps({"lessons": out}, indent=2, default=str)
```

In `_Handler.do_GET`, add (before the catch-all):

```python
if self.path == "/api/lessons":
    import json
    from taskmaster_v3 import (
        list_lesson_ids, load_lesson, compute_lesson_shelf, load_viewer_prefs,
    )
    prefs = load_viewer_prefs()
    thresholds = prefs.get("lessons", {}).get("thresholds", {})
    lessons = []
    for lid in list_lesson_ids():
        try:
            lesson = load_lesson(lid)
        except Exception:
            continue
        summary = {k: v for k, v in lesson.items() if k != "_body"}
        summary["shelf"] = compute_lesson_shelf(lesson, thresholds)
        lessons.append(summary)
    self._send_json(200, {"lessons": lessons})
    return
```

(If `list_lesson_ids()` does not yet exist in `taskmaster_v3.py`, add a small helper that scans `.taskmaster/lessons/*.md` and returns the stem strings sorted.)

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest plugins/taskmaster/tests/test_server_lessons.py -v`
Expected: All PASS.

- [x] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_server_lessons.py
git commit -m "feat(taskmaster): GET /api/lessons + lesson_list_extended"
```

---

### Task 7: Pure-Python `compute_issue_aging` helper

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py`
- Create: `plugins/taskmaster/tests/test_server_issues.py`

- [x] **Step 1: Write the failing test**

Create `plugins/taskmaster/tests/test_server_issues.py`:

```python
"""HTTP tests for /api/issues + compute_issue_aging unit tests."""
import json
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from tests.test_server_api import running_server  # noqa: F401


def _write_issue(root: Path, issue_id: str, **overrides):
    import yaml
    base = {
        "id": issue_id,
        "title": "Sample defect",
        "status": "open",
        "severity": "P1",
        "components": ["viewer"],
        "impact": "Users cannot save filters.",
        "location": ["viewer/cards.css:206"],
        "discovered": "2026-04-10T00:00:00Z",
        "discovered_by": "user",
        "resolved": None,
        "related_tasks": [],
        "fixed_in_task": None,
        "duplicate_of": None,
        "symptom": "The filter clears on reload.",
        "repro": ["open kanban", "set epic filter", "reload page"],
    }
    base.update(overrides)
    p = root / ".taskmaster" / "issues" / f"{issue_id}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    fm = "---\n" + yaml.safe_dump(base, sort_keys=False).rstrip() + "\n---\nBody.\n"
    p.write_text(fm)


def test_compute_issue_aging_fresh_band():
    from taskmaster_v3 import compute_issue_aging
    now = datetime(2026, 4, 26, tzinfo=timezone.utc)
    issue = {"discovered": (now - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ"), "severity": "P1"}
    aging_cfg = {"Critical": 14, "High": 30, "Medium": 60, "Low": 120}
    out = compute_issue_aging(issue, aging_cfg, now=now)
    assert out["tier"] == "Fresh"
    assert 0 <= out["percent"] < 25


def test_compute_issue_aging_aging_band():
    from taskmaster_v3 import compute_issue_aging
    now = datetime(2026, 4, 26, tzinfo=timezone.utc)
    issue = {"discovered": (now - timedelta(days=12)).strftime("%Y-%m-%dT%H:%M:%SZ"), "severity": "P1"}
    out = compute_issue_aging(issue, {"Critical": 14, "High": 30, "Medium": 60, "Low": 120}, now=now)
    assert out["tier"] == "Aging"
    assert 25 <= out["percent"] < 60


def test_compute_issue_aging_stale_band():
    from taskmaster_v3 import compute_issue_aging
    now = datetime(2026, 4, 26, tzinfo=timezone.utc)
    issue = {"discovered": (now - timedelta(days=25)).strftime("%Y-%m-%dT%H:%M:%SZ"), "severity": "P1"}
    out = compute_issue_aging(issue, {"Critical": 14, "High": 30, "Medium": 60, "Low": 120}, now=now)
    assert out["tier"] == "Stale"
    assert out["percent"] >= 60


def test_compute_issue_aging_critical_decays_faster_than_low():
    from taskmaster_v3 import compute_issue_aging
    now = datetime(2026, 4, 26, tzinfo=timezone.utc)
    discovered = (now - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
    crit = compute_issue_aging({"discovered": discovered, "severity": "P0"}, {"Critical": 14, "High": 30, "Medium": 60, "Low": 120}, now=now)
    low = compute_issue_aging({"discovered": discovered, "severity": "P3"}, {"Critical": 14, "High": 30, "Medium": 60, "Low": 120}, now=now)
    assert crit["percent"] > low["percent"]
```

- [x] **Step 2: Run tests to verify they fail**

Run: `python -m pytest plugins/taskmaster/tests/test_server_issues.py -v -k aging`
Expected: FAIL — `ImportError`.

- [x] **Step 3: Implement `compute_issue_aging`**

Add to `plugins/taskmaster/taskmaster_v3.py`:

```python
SEVERITY_LABEL = {"P0": "Critical", "P1": "High", "P2": "Medium", "P3": "Low"}


def severity_label(p: str) -> str:
    """Map raw severity code to user-facing word."""
    return SEVERITY_LABEL.get(p, p)


def compute_issue_aging(issue: dict, aging_cfg: dict, now=None) -> dict:
    """Return {'percent': float, 'tier': 'Fresh'|'Aging'|'Stale'} given issue + cfg.

    Tier rules (per spec §3.14):
        Fresh:  0 <= pct < 25
        Aging: 25 <= pct < 60
        Stale: pct >= 60

    `percent` may exceed 100 for very stale issues; clamp at 200 for display.
    """
    from datetime import datetime, timezone

    if now is None:
        now = datetime.now(timezone.utc)

    label = severity_label(issue.get("severity", "P2"))
    base_days = float(aging_cfg.get(label, 60))
    discovered_raw = issue.get("discovered")
    if not discovered_raw:
        return {"percent": 0.0, "tier": "Fresh"}
    discovered = datetime.strptime(discovered_raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    age_days = (now - discovered).total_seconds() / 86400.0

    pct = (age_days / base_days) * 100.0 if base_days > 0 else 0.0
    pct = max(0.0, min(pct, 200.0))
    if pct < 25:
        tier = "Fresh"
    elif pct < 60:
        tier = "Aging"
    else:
        tier = "Stale"
    return {"percent": pct, "tier": tier}
```

- [x] **Step 4: Run tests to verify they pass**

Run: `python -m pytest plugins/taskmaster/tests/test_server_issues.py -v -k aging`
Expected: 4 tests PASS.

- [x] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_server_issues.py
git commit -m "feat(taskmaster): compute_issue_aging + severity_label"
```

---

### Task 8: `issue_list_extended` MCP tool + `GET /api/issues` endpoint

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py`
- Modify: `plugins/taskmaster/tests/test_server_issues.py`

- [x] **Step 1: Write the failing test**

Append to `plugins/taskmaster/tests/test_server_issues.py`:

```python
def test_get_issues_returns_list_with_aging_and_label(running_server, tmp_path):
    base, _ = running_server
    _write_issue(tmp_path, "ISS-001", severity="P0", discovered=(datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ"))
    _write_issue(tmp_path, "ISS-002", severity="P3", status="fixed", resolved=(datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ"))

    resp = urllib.request.urlopen(f"{base}/api/issues")
    payload = json.loads(resp.read())
    by_id = {i["id"]: i for i in payload["issues"]}
    assert by_id["ISS-001"]["severity_label"] == "Critical"
    assert by_id["ISS-001"]["aging"]["tier"] in {"Fresh", "Aging", "Stale"}
    assert by_id["ISS-002"]["severity_label"] == "Low"


def test_get_issues_excludes_resolved_when_query_param_set(running_server, tmp_path):
    base, _ = running_server
    _write_issue(tmp_path, "ISS-010", status="open")
    _write_issue(tmp_path, "ISS-011", status="fixed", resolved="2026-04-20T00:00:00Z")

    resp = urllib.request.urlopen(f"{base}/api/issues?include_resolved=false")
    payload = json.loads(resp.read())
    ids = [i["id"] for i in payload["issues"]]
    assert "ISS-010" in ids
    assert "ISS-011" not in ids
```

- [x] **Step 2: Run tests to verify they fail**

Run: `python -m pytest plugins/taskmaster/tests/test_server_issues.py -v -k get_issues`
Expected: FAIL — 404.

- [x] **Step 3: Implement the tool + route**

Add to `plugins/taskmaster/backlog_server.py`:

```python
@mcp.tool()
def issue_list_extended(include_resolved: bool = True) -> str:
    """List all issues with computed aging tier per severity base."""
    import json as _json
    from taskmaster_v3 import (
        list_issue_ids, load_issue, compute_issue_aging, severity_label, load_viewer_prefs,
    )

    prefs = load_viewer_prefs()
    aging_cfg = prefs.get("issues", {}).get("aging", {})
    out = []
    for iid in list_issue_ids():
        try:
            issue = load_issue(iid)
        except Exception:
            continue
        if not include_resolved and issue.get("status") in ("fixed", "wontfix"):
            continue
        summary = {k: v for k, v in issue.items() if k != "_body"}
        summary["severity_label"] = severity_label(summary.get("severity", "P2"))
        summary["aging"] = compute_issue_aging(issue, aging_cfg)
        out.append(summary)
    return _json.dumps({"issues": out}, indent=2, default=str)
```

In `_Handler.do_GET`:

```python
if self.path.startswith("/api/issues"):
    import json
    from urllib.parse import urlparse, parse_qs
    from taskmaster_v3 import (
        list_issue_ids, load_issue, compute_issue_aging, severity_label, load_viewer_prefs,
    )
    qs = parse_qs(urlparse(self.path).query)
    include_resolved = qs.get("include_resolved", ["true"])[0].lower() != "false"
    prefs = load_viewer_prefs()
    aging_cfg = prefs.get("issues", {}).get("aging", {})
    issues = []
    for iid in list_issue_ids():
        try:
            issue = load_issue(iid)
        except Exception:
            continue
        if not include_resolved and issue.get("status") in ("fixed", "wontfix"):
            continue
        summary = {k: v for k, v in issue.items() if k != "_body"}
        summary["severity_label"] = severity_label(summary.get("severity", "P2"))
        summary["aging"] = compute_issue_aging(issue, aging_cfg)
        issues.append(summary)
    self._send_json(200, {"issues": issues})
    return
```

(Add `list_issue_ids()` to `taskmaster_v3.py` if absent — same shape as `list_lesson_ids()`, scanning `.taskmaster/issues/*.md`.)

- [x] **Step 4: Run tests to verify they pass**

Run: `python -m pytest plugins/taskmaster/tests/test_server_issues.py -v`
Expected: All PASS (6 tests).

- [x] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_server_issues.py
git commit -m "feat(taskmaster): GET /api/issues + issue_list_extended"
```

---

## M3 — Shared Components

### Task 9: `severity-glyph.js` — SVG hexagon symbol defs

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/severity-glyph.js`

- [ ] **Step 1: Write the file**

Create `plugins/taskmaster/viewer/js/components/severity-glyph.js`:

```js
// SVG hexagon glyph for severity. One <symbol> def block goes once into the page;
// individual cards reference via <svg><use href="#sev-hex"/></svg>.
//
// Sizes per severity (px width/height of the rendered SVG):
//   Critical: 18, High: 16, Medium: 14, Low: 12

const SIZE_BY_LABEL = { Critical: 18, High: 16, Medium: 14, Low: 12 };
const COLOR_BY_LABEL = {
  Critical: 'var(--sev-critical, #e87a85)',
  High:     'var(--sev-high, #e8a34d)',
  Medium:   'var(--sev-medium, #c8b75a)',
  Low:      'var(--sev-low, #888c95)',
};

let _defsInjected = false;

export function injectSeverityDefs(doc = document) {
  if (_defsInjected) return;
  _defsInjected = true;
  const svg = doc.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('width', '0');
  svg.setAttribute('height', '0');
  svg.setAttribute('aria-hidden', 'true');
  svg.style.position = 'absolute';
  svg.innerHTML = `
    <defs>
      <symbol id="sev-hex" viewBox="0 0 20 20">
        <polygon points="10,2 17,6 17,14 10,18 3,14 3,6"
                 fill="currentColor" fill-opacity="0.18"
                 stroke="currentColor" stroke-width="1.4"
                 stroke-linejoin="round"/>
      </symbol>
    </defs>`;
  doc.body.appendChild(svg);
}

export function severityGlyph(label) {
  injectSeverityDefs();
  const size = SIZE_BY_LABEL[label] || 14;
  const color = COLOR_BY_LABEL[label] || COLOR_BY_LABEL.Medium;
  const el = document.createElement('span');
  el.className = 'sev-glyph';
  el.setAttribute('data-severity', label);
  el.style.color = color;
  el.style.display = 'inline-flex';
  el.style.width = `${size}px`;
  el.style.height = `${size}px`;
  el.innerHTML = `<svg width="${size}" height="${size}" aria-label="${label} severity"><use href="#sev-hex"/></svg>`;
  return el;
}

export default severityGlyph;
```

- [ ] **Step 2: Smoke-import (no test yet — verified end-to-end via Playwright in M5)**

Run: `node -e "import('./plugins/taskmaster/viewer/js/components/severity-glyph.js').then(m => console.log(Object.keys(m)))"`
Expected: `[ 'injectSeverityDefs', 'severityGlyph', 'default' ]`

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/severity-glyph.js
git commit -m "feat(viewer): severity hexagon SVG glyph component"
```

---

### Task 10: `aging-bar.js` + JS-side `computeAgingTier` + unit test

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/aging-bar.js`
- Create: `plugins/taskmaster/viewer/tests/unit/issue-aging.test.js`

- [ ] **Step 1: Write the failing unit test**

Create `plugins/taskmaster/viewer/tests/unit/issue-aging.test.js`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { computeAgingTier } from '../../js/components/aging-bar.js';

const cfg = { Critical: 14, High: 30, Medium: 60, Low: 120 };

test('computeAgingTier: Fresh band 0-25%', () => {
  const now = new Date('2026-04-26T00:00:00Z');
  const discovered = new Date('2026-04-23T00:00:00Z').toISOString();
  const out = computeAgingTier({ discovered, severity_label: 'High' }, cfg, now);
  assert.equal(out.tier, 'Fresh');
  assert.ok(out.percent >= 0 && out.percent < 25, `percent=${out.percent}`);
});

test('computeAgingTier: Aging band 25-60%', () => {
  const now = new Date('2026-04-26T00:00:00Z');
  const discovered = new Date('2026-04-14T00:00:00Z').toISOString();
  const out = computeAgingTier({ discovered, severity_label: 'High' }, cfg, now);
  assert.equal(out.tier, 'Aging');
  assert.ok(out.percent >= 25 && out.percent < 60, `percent=${out.percent}`);
});

test('computeAgingTier: Stale band 60+%', () => {
  const now = new Date('2026-04-26T00:00:00Z');
  const discovered = new Date('2026-04-01T00:00:00Z').toISOString();
  const out = computeAgingTier({ discovered, severity_label: 'High' }, cfg, now);
  assert.equal(out.tier, 'Stale');
  assert.ok(out.percent >= 60, `percent=${out.percent}`);
});

test('computeAgingTier: Critical decays faster than Low at same age', () => {
  const now = new Date('2026-04-26T00:00:00Z');
  const discovered = new Date('2026-04-16T00:00:00Z').toISOString();
  const crit = computeAgingTier({ discovered, severity_label: 'Critical' }, cfg, now);
  const low  = computeAgingTier({ discovered, severity_label: 'Low' }, cfg, now);
  assert.ok(crit.percent > low.percent, `crit=${crit.percent} low=${low.percent}`);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test plugins/taskmaster/viewer/tests/unit/issue-aging.test.js`
Expected: FAIL — `Cannot find module`.

- [ ] **Step 3: Implement `aging-bar.js`**

Create `plugins/taskmaster/viewer/js/components/aging-bar.js`:

```js
// Severity-tiered aging bar. Two responsibilities:
//   1) Pure-data: computeAgingTier(issue, cfg, now?) → { percent, tier }
//   2) DOM: agingBar(issue, cfg) returns a styled <div class="aging-bar">

export function computeAgingTier(issue, cfg, now = new Date()) {
  const label = issue.severity_label || 'Medium';
  const baseDays = Number(cfg[label] ?? 60);
  if (!issue.discovered) return { percent: 0, tier: 'Fresh' };
  const discovered = new Date(issue.discovered);
  const ageDays = (now.getTime() - discovered.getTime()) / 86_400_000;
  let percent = baseDays > 0 ? (ageDays / baseDays) * 100 : 0;
  percent = Math.max(0, Math.min(percent, 200));
  let tier;
  if (percent < 25) tier = 'Fresh';
  else if (percent < 60) tier = 'Aging';
  else tier = 'Stale';
  return { percent, tier };
}

export function agingBar(issue, cfg) {
  const { percent, tier } = computeAgingTier(issue, cfg);
  const wrap = document.createElement('div');
  wrap.className = `aging-bar aging-bar--${tier.toLowerCase()}`;
  wrap.setAttribute('data-tier', tier);

  const track = document.createElement('div');
  track.className = 'aging-bar__track';
  const fill = document.createElement('div');
  fill.className = 'aging-bar__fill';
  fill.style.width = `${Math.min(percent, 100)}%`;
  track.appendChild(fill);

  const chip = document.createElement('span');
  chip.className = `aging-bar__chip aging-bar__chip--${tier.toLowerCase()}`;
  chip.textContent = tier;

  wrap.appendChild(track);
  wrap.appendChild(chip);
  return wrap;
}

export default agingBar;
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test plugins/taskmaster/viewer/tests/unit/issue-aging.test.js`
Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/aging-bar.js plugins/taskmaster/viewer/tests/unit/issue-aging.test.js
git commit -m "feat(viewer): aging-bar with severity-tiered Fresh/Aging/Stale"
```

---

### Task 11: `sparkline.js` — gold active-signal sparkline

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/sparkline.js`

- [ ] **Step 1: Write the file**

Create `plugins/taskmaster/viewer/js/components/sparkline.js`:

```js
// Active-signal sparkline. Renders a small inline SVG line summarizing
// reinforce_events over the last N days, plus the lifetime count and
// the relative "last fired" timestamp.

const DEFAULT_DAYS = 30;
const W = 64;
const H = 16;

function _bucket(events, days, now) {
  const buckets = new Array(days).fill(0);
  for (const e of events) {
    const t = new Date(e.at).getTime();
    const ageDays = Math.floor((now.getTime() - t) / 86_400_000);
    if (ageDays < 0 || ageDays >= days) continue;
    buckets[days - 1 - ageDays] += 1;
  }
  return buckets;
}

function _relTime(iso, now) {
  if (!iso) return '—';
  const ms = now.getTime() - new Date(iso).getTime();
  const d = Math.floor(ms / 86_400_000);
  if (d <= 0) {
    const h = Math.floor(ms / 3_600_000);
    return h <= 0 ? 'now' : `${h}h`;
  }
  return `${d}d`;
}

export function sparkline(lesson, { days = DEFAULT_DAYS, now = new Date() } = {}) {
  const events = lesson.reinforce_events || [];
  const buckets = _bucket(events, days, now);
  const max = Math.max(1, ...buckets);
  const stepX = W / Math.max(1, days - 1);
  const points = buckets.map((v, i) => {
    const x = i * stepX;
    const y = H - (v / max) * (H - 2) - 1;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');

  const wrap = document.createElement('span');
  wrap.className = 'sparkline-pill';
  wrap.innerHTML = `
    <svg class="sparkline-svg" width="${W}" height="${H}" aria-hidden="true">
      <polyline points="${points}" fill="none" stroke="var(--gold, #d9b35a)" stroke-width="1.4" stroke-linejoin="round"/>
    </svg>
    <span class="sparkline-count">${(lesson.reinforce_count || 0)}×</span>
    <span class="sparkline-last">${_relTime(lesson.last_reinforced, now)}</span>
  `;
  return wrap;
}

export default sparkline;
```

- [ ] **Step 2: Smoke-import**

Run: `node -e "import('./plugins/taskmaster/viewer/js/components/sparkline.js').then(m => console.log(typeof m.sparkline))"`
Expected: `function`

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/sparkline.js
git commit -m "feat(viewer): gold sparkline for lesson active signal"
```

---

### Task 12: `dot-meter.js` — passive-signal anchor-match meter

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/dot-meter.js`

- [ ] **Step 1: Write the file**

Create `plugins/taskmaster/viewer/js/components/dot-meter.js`:

```js
// Passive-signal 5-dot meter for anchor-match intensity over the last 7 days.
// Ambient only — does NOT participate in shelf placement.
// Input: matches7d (number) → dots filled from left to right.

const DOTS = 5;

function _dotsFilledFor(count) {
  if (count <= 0) return 0;
  if (count < 5) return 1;
  if (count < 15) return 2;
  if (count < 30) return 3;
  if (count < 60) return 4;
  return 5;
}

export function dotMeter(matches7d) {
  const filled = _dotsFilledFor(matches7d);
  const wrap = document.createElement('span');
  wrap.className = 'dot-meter';
  wrap.setAttribute('aria-label', `${matches7d} anchor matches in last 7 days`);
  for (let i = 0; i < DOTS; i++) {
    const d = document.createElement('span');
    d.className = `dot-meter__dot ${i < filled ? 'is-on' : 'is-off'}`;
    wrap.appendChild(d);
  }
  const cap = document.createElement('span');
  cap.className = 'dot-meter__caption';
  cap.textContent = `${matches7d} matches · 7d`;
  wrap.appendChild(cap);
  return wrap;
}

export { _dotsFilledFor };
export default dotMeter;
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/dot-meter.js
git commit -m "feat(viewer): 5-dot passive anchor-match meter"
```

---

### Task 13: `anchor-pills.js` — mono pills with "When:" label

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/anchor-pills.js`

- [ ] **Step 1: Write the file**

Create `plugins/taskmaster/viewer/js/components/anchor-pills.js`:

```js
// Mono pills showing lesson anchor file patterns, prefixed with a small "When:" label.
// Reads from lesson.triggers.files. Empty triggers render "When: (any file)" in muted ink.

export function anchorPills(lesson) {
  const triggers = (lesson.triggers && lesson.triggers.files) || [];
  const wrap = document.createElement('div');
  wrap.className = 'anchor-pills';

  const label = document.createElement('span');
  label.className = 'anchor-pills__label';
  label.textContent = 'When:';
  wrap.appendChild(label);

  if (triggers.length === 0) {
    const empty = document.createElement('span');
    empty.className = 'anchor-pills__empty';
    empty.textContent = '(any file)';
    wrap.appendChild(empty);
    return wrap;
  }
  for (const pat of triggers) {
    const pill = document.createElement('code');
    pill.className = 'anchor-pills__pill';
    pill.textContent = pat;
    wrap.appendChild(pill);
  }
  return wrap;
}

export default anchorPills;
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/anchor-pills.js
git commit -m "feat(viewer): anchor pills with When: label"
```

---

### Task 14: `lesson-shelf-placement.test.js` — JS-side `computeShelfPlacement`

**Files:**
- Create: `plugins/taskmaster/viewer/js/util/lesson-shelf.js`
- Create: `plugins/taskmaster/viewer/tests/unit/lesson-shelf-placement.test.js`

- [ ] **Step 1: Write the failing unit test**

Create `plugins/taskmaster/viewer/tests/unit/lesson-shelf-placement.test.js`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { computeShelfPlacement } from '../../js/util/lesson-shelf.js';

const T = { core_count: 7, core_window_days: 60, core_recency_days: 14, retired_after_days: 30 };

function ev(daysAgo, now) {
  return { at: new Date(now.getTime() - daysAgo * 86_400_000).toISOString(), source: 'user', note: '' };
}

test('core: ≥7 in 60d AND fire in 14d', () => {
  const now = new Date('2026-04-26T00:00:00Z');
  const events = [1, 3, 5, 10, 18, 25, 40].map(d => ev(d, now));
  assert.equal(computeShelfPlacement({ reinforce_events: events }, T, now), 'core');
});

test('active: high volume but no recent fire → active, not core', () => {
  const now = new Date('2026-04-26T00:00:00Z');
  const events = [16, 18, 20, 22, 24, 26, 28, 29].map(d => ev(d, now));
  assert.equal(computeShelfPlacement({ reinforce_events: events }, T, now), 'active');
});

test('active: any fire within retired_after_days but below core volume', () => {
  const now = new Date('2026-04-26T00:00:00Z');
  const events = [ev(2, now)];
  assert.equal(computeShelfPlacement({ reinforce_events: events }, T, now), 'active');
});

test('retired: no fire in retired_after_days', () => {
  const now = new Date('2026-04-26T00:00:00Z');
  const events = [ev(45, now)];
  assert.equal(computeShelfPlacement({ reinforce_events: events }, T, now), 'retired');
});

test('retired: empty events list', () => {
  const now = new Date('2026-04-26T00:00:00Z');
  assert.equal(computeShelfPlacement({ reinforce_events: [] }, T, now), 'retired');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test plugins/taskmaster/viewer/tests/unit/lesson-shelf-placement.test.js`
Expected: FAIL — `Cannot find module`.

- [ ] **Step 3: Implement `computeShelfPlacement`**

Create `plugins/taskmaster/viewer/js/util/lesson-shelf.js`:

```js
// Mirror of taskmaster_v3.compute_lesson_shelf for client-side fallback +
// any in-page recompute (e.g. after a Reinforce click before re-poll).

export function computeShelfPlacement(lesson, thresholds, now = new Date()) {
  const events = (lesson.reinforce_events || []).map(e => new Date(e.at));
  const day = 86_400_000;
  const coreCount   = Number(thresholds.core_count ?? 7);
  const coreWindow  = Number(thresholds.core_window_days ?? 60) * day;
  const coreRecency = Number(thresholds.core_recency_days ?? 14) * day;
  const retiredAfter = Number(thresholds.retired_after_days ?? 30) * day;

  const inWindow  = events.filter(t => (now - t) <= coreWindow);
  const inRecency = events.filter(t => (now - t) <= coreRecency);
  const inActive  = events.filter(t => (now - t) <= retiredAfter);

  if (inWindow.length >= coreCount && inRecency.length >= 1) return 'core';
  if (inActive.length === 0) return 'retired';
  return 'active';
}

export default computeShelfPlacement;
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test plugins/taskmaster/viewer/tests/unit/lesson-shelf-placement.test.js`
Expected: 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/viewer/js/util/lesson-shelf.js plugins/taskmaster/viewer/tests/unit/lesson-shelf-placement.test.js
git commit -m "feat(viewer): client-side computeShelfPlacement matching server"
```

---

### Task 15: `issue-blocks-count.test.js` — JS-side `computeBlocksCount`

**Files:**
- Create: `plugins/taskmaster/viewer/js/util/issue-blocks.js`
- Create: `plugins/taskmaster/viewer/tests/unit/issue-blocks-count.test.js`

- [ ] **Step 1: Write the failing unit test**

Create `plugins/taskmaster/viewer/tests/unit/issue-blocks-count.test.js`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { computeBlocksCount } from '../../js/util/issue-blocks.js';

const tasks = {
  'T-1': { id: 'T-1', status: 'in-progress' },
  'T-2': { id: 'T-2', status: 'done' },
  'T-3': { id: 'T-3', status: 'todo' },
};

test('issue blocks 2 non-done tasks via related_tasks', () => {
  const issue = { id: 'I-1', related_tasks: ['T-1', 'T-2', 'T-3'] };
  assert.equal(computeBlocksCount(issue, tasks), 2);
});

test('issue blocks via discovered_in_task too', () => {
  const issue = { id: 'I-2', related_tasks: ['T-2'], discovered_in_task: 'T-1' };
  assert.equal(computeBlocksCount(issue, tasks), 1);
});

test('zero blocks when all referenced tasks are done', () => {
  const issue = { id: 'I-3', related_tasks: ['T-2'] };
  assert.equal(computeBlocksCount(issue, tasks), 0);
});

test('zero blocks when no task refs', () => {
  assert.equal(computeBlocksCount({ id: 'I-4' }, tasks), 0);
});

test('unknown task IDs are ignored', () => {
  const issue = { id: 'I-5', related_tasks: ['T-1', 'T-NOPE'] };
  assert.equal(computeBlocksCount(issue, tasks), 1);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test plugins/taskmaster/viewer/tests/unit/issue-blocks-count.test.js`
Expected: FAIL — `Cannot find module`.

- [ ] **Step 3: Implement `computeBlocksCount`**

Create `plugins/taskmaster/viewer/js/util/issue-blocks.js`:

```js
// Compute how many tasks an issue blocks: any referenced task with status != 'done'.

export function computeBlocksCount(issue, tasksIndex) {
  const refs = new Set();
  for (const t of issue.related_tasks || []) refs.add(t);
  if (issue.discovered_in_task) refs.add(issue.discovered_in_task);
  if (issue.fixed_in_task) refs.add(issue.fixed_in_task);

  let count = 0;
  for (const id of refs) {
    const task = tasksIndex[id];
    if (!task) continue;
    if (task.status !== 'done') count += 1;
  }
  return count;
}

export default computeBlocksCount;
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test plugins/taskmaster/viewer/tests/unit/issue-blocks-count.test.js`
Expected: 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/viewer/js/util/issue-blocks.js plugins/taskmaster/viewer/tests/unit/issue-blocks-count.test.js
git commit -m "feat(viewer): computeBlocksCount for ⊘ blocks N chip"
```

---

### Task 16: `severity-label.js` JS helper

**Files:**
- Create: `plugins/taskmaster/viewer/js/util/severity-label.js`

- [ ] **Step 1: Write the file**

Create `plugins/taskmaster/viewer/js/util/severity-label.js`:

```js
// Map raw severity codes to user-facing words.
// Words only — never P0/P1 in the UI.

const MAP = { P0: 'Critical', P1: 'High', P2: 'Medium', P3: 'Low' };

export function severityLabel(code) {
  return MAP[code] || code || 'Medium';
}

export default severityLabel;
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/util/severity-label.js
git commit -m "feat(viewer): severityLabel maps P0-P3 to words"
```

---

### Task 17: Extend `api.js` with `reinforceLesson`, `getLessons`, `getIssues`

**Files:**
- Modify: `plugins/taskmaster/viewer/js/api.js`

- [ ] **Step 1: Append to api.js**

Append to `plugins/taskmaster/viewer/js/api.js`:

```js
// --- Lessons ---------------------------------------------------------------
export async function getLessons() {
  const r = await fetch('/api/lessons');
  if (!r.ok) throw new Error(`getLessons failed: ${r.status}`);
  return r.json();
}

export async function reinforceLesson(lessonId, { source = 'user', note = '' } = {}) {
  const r = await fetch(`/api/lessons/${encodeURIComponent(lessonId)}/reinforce`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source, note }),
  });
  if (!r.ok) throw new Error(`reinforceLesson failed: ${r.status}`);
  return r.json();
}

// --- Issues ----------------------------------------------------------------
export async function getIssues({ includeResolved = true } = {}) {
  const qs = includeResolved ? '' : '?include_resolved=false';
  const r = await fetch(`/api/issues${qs}`);
  if (!r.ok) throw new Error(`getIssues failed: ${r.status}`);
  return r.json();
}
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/api.js
git commit -m "feat(viewer): api.getLessons / api.getIssues / api.reinforceLesson"
```

---

## M4 — Lessons Screen + lesson-card

### Task 18: `css/screens/lessons.css` — three shelves + tokens

**Files:**
- Create: `plugins/taskmaster/viewer/css/screens/lessons.css`
- Modify: `plugins/taskmaster/viewer/index.html` (link the new CSS)

- [ ] **Step 1: Write the CSS**

Create `plugins/taskmaster/viewer/css/screens/lessons.css`:

```css
/* Lessons screen — three shelves: Core / Active / Retired.
   Tokens scoped under --lessons-* live here; global tokens come from tokens.css. */

.lessons {
  --lessons-shelf-gap: 28px;
  --lessons-card-gap: 12px;
  --lessons-gold: #d9b35a;
  --lessons-gold-soft: rgba(217, 179, 90, 0.18);
  --lessons-retired-rest: 0.55;
  --lessons-retired-hover: 0.85;

  display: flex;
  flex-direction: column;
  gap: var(--lessons-shelf-gap);
  padding: 24px 28px;
}

.lessons__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}

.lessons__view-toggle {
  display: inline-flex;
  gap: 4px;
}
.lessons__view-toggle button {
  padding: 4px 10px;
  background: var(--bg-card);
  color: var(--ink-2);
  border: 1px solid var(--border);
  border-radius: 4px;
  cursor: pointer;
  font: inherit;
}
.lessons__view-toggle button.is-active {
  background: var(--bg-active);
  color: var(--ink);
}

/* ---- shelves ---- */

.lessons-shelf { display: flex; flex-direction: column; gap: 10px; }
.lessons-shelf__header {
  display: flex; align-items: baseline; gap: 12px;
  font-family: 'Source Serif Pro', Georgia, serif;
  font-style: italic;
  font-size: 16px;
}
.lessons-shelf--core    .lessons-shelf__header { color: var(--lessons-gold); }
.lessons-shelf--active  .lessons-shelf__header { color: var(--ink); }
.lessons-shelf--retired .lessons-shelf__header { color: var(--ink-3); }
.lessons-shelf__tagline { font-size: 12px; color: var(--ink-3); font-style: italic; }
.lessons-shelf__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: var(--lessons-card-gap);
}

/* ---- card ---- */

.lesson-card {
  position: relative;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 14px 14px 12px;
  display: flex; flex-direction: column; gap: 10px;
  transition: background 120ms ease;
}
.lesson-card:hover { background: var(--bg-card-hover); }

/* core: subtle gold gradient at top, NO edge ribbon */
.lesson-card--core {
  background:
    linear-gradient(to bottom, var(--lessons-gold-soft) 0%, transparent 56px),
    var(--bg-card);
}
.lesson-card--core .lesson-card__id { color: var(--lessons-gold); }

/* retired: faded at rest, brightens on hover */
.lesson-card--retired { opacity: var(--lessons-retired-rest); }
.lesson-card--retired:hover { opacity: var(--lessons-retired-hover); }
.lesson-card--retired .lesson-card__title { color: var(--ink-2); }
.lesson-card--retired .lesson-card__summary { color: var(--ink-3); }

/* head row */
.lesson-card__head {
  display: flex; align-items: center; gap: 8px;
}
.lesson-card__kind {
  font-size: 13px;
  color: var(--ink-2);
  opacity: 0.6;
}
.lesson-card__id {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  color: var(--ink-2);
}
.lesson-card__title {
  font-size: 14px;
  font-weight: 500;
  color: var(--ink);
  flex: 1;
}

.lesson-card__since {
  font-size: 11px;
  color: var(--ink-3);
}

/* signals: gold pill (active) on right; dot meter (passive) on anchors row */
.lesson-card__signals {
  display: flex; align-items: center; justify-content: space-between;
  gap: 8px;
}
.sparkline-pill {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--lessons-gold-soft);
  font-size: 11px;
  color: var(--lessons-gold);
}
.sparkline-count { font-weight: 600; }
.sparkline-last { color: var(--ink-3); }

.dot-meter { display: inline-flex; align-items: center; gap: 4px; }
.dot-meter__dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--ink-3); opacity: 0.3;
}
.dot-meter__dot.is-on { background: var(--ink-2); opacity: 1; }
.dot-meter__caption { font-size: 10px; color: var(--ink-3); margin-left: 4px; }

.anchor-pills { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.anchor-pills__label { font-size: 11px; color: var(--ink-3); }
.anchor-pills__pill {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  background: var(--bg-deep);
  color: var(--ink-2);
  padding: 1px 6px;
  border-radius: 3px;
}
.anchor-pills__empty { font-size: 11px; color: var(--ink-3); font-style: italic; }

/* reinforce button — bottom-right on hover */
.lesson-card__reinforce {
  position: absolute; right: 10px; bottom: 10px;
  opacity: 0;
  transition: opacity 100ms ease;
  background: transparent;
  border: 1px solid var(--lessons-gold);
  color: var(--lessons-gold);
  padding: 3px 10px;
  border-radius: 4px;
  font: 600 11px/1 inherit;
  cursor: pointer;
}
.lesson-card:hover .lesson-card__reinforce { opacity: 1; }
.lesson-card__reinforce.is-fired {
  opacity: 1;
  color: var(--accent-green, #5fcdb8);
  border-color: var(--accent-green, #5fcdb8);
}
```

- [ ] **Step 2: Add the link tag**

In `plugins/taskmaster/viewer/index.html`, inside `<head>` after the existing screen CSS links:

```html
<link rel="stylesheet" href="/static/v3/css/screens/lessons.css">
```

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/css/screens/lessons.css plugins/taskmaster/viewer/index.html
git commit -m "feat(viewer): lessons screen CSS — three shelves + card"
```

---

### Task 19: `lesson-card.js` — full card with all signals

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/lesson-card.js`

- [ ] **Step 1: Write the file**

Create `plugins/taskmaster/viewer/js/components/lesson-card.js`:

```js
import { sparkline } from './sparkline.js';
import { dotMeter } from './dot-meter.js';
import { anchorPills } from './anchor-pills.js';

const KIND_ICON = { gotcha: '⚠', pattern: '◇', 'anti-pattern': '⊘' };
const KIND_TOOLTIP = { gotcha: 'gotcha', pattern: 'pattern', 'anti-pattern': 'anti-pattern' };

function _fmtSince(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function _matches7d(lesson) {
  // Best-effort passive count if the server provides it; fall back to 0.
  return Number(lesson.anchor_matches_7d || 0);
}

export function lessonCard(lesson, { onReinforce } = {}) {
  const shelf = lesson.shelf || 'active';
  const card = document.createElement('article');
  card.className = `lesson-card lesson-card--${shelf}`;
  card.setAttribute('data-lesson-id', lesson.id);

  // ---- head: kind icon · id · title · since
  const head = document.createElement('div');
  head.className = 'lesson-card__head';

  const kind = document.createElement('span');
  kind.className = 'lesson-card__kind';
  kind.textContent = KIND_ICON[lesson.kind] || '◇';
  kind.title = KIND_TOOLTIP[lesson.kind] || lesson.kind || 'pattern';
  head.appendChild(kind);

  const id = document.createElement('span');
  id.className = 'lesson-card__id';
  id.textContent = lesson.id;
  head.appendChild(id);

  const title = document.createElement('span');
  title.className = 'lesson-card__title';
  title.textContent = lesson.title || '(untitled)';
  head.appendChild(title);

  card.appendChild(head);

  // first_seen caption
  const since = document.createElement('div');
  since.className = 'lesson-card__since';
  since.textContent = lesson.created ? `since ${_fmtSince(lesson.created)}` : '';
  card.appendChild(since);

  // ---- signals row: passive (left, dot meter) · active (right, sparkline pill)
  const signals = document.createElement('div');
  signals.className = 'lesson-card__signals';
  signals.appendChild(dotMeter(_matches7d(lesson)));
  signals.appendChild(sparkline(lesson));
  card.appendChild(signals);

  // ---- anchors row
  card.appendChild(anchorPills(lesson));

  // ---- reinforce button
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'lesson-card__reinforce';
  btn.textContent = shelf === 'retired' ? '↑ Revive' : '↑ Reinforce';
  btn.addEventListener('click', async (ev) => {
    ev.stopPropagation();
    if (btn.classList.contains('is-fired')) return;
    btn.disabled = true;
    try {
      const summary = await onReinforce?.(lesson.id);
      btn.classList.add('is-fired');
      btn.textContent = '✓ Reinforced now';
      if (summary) {
        // Update local lesson view in-place
        Object.assign(lesson, summary);
      }
    } catch (e) {
      btn.disabled = false;
      btn.textContent = 'Failed — retry';
      console.error(e);
    }
  });
  card.appendChild(btn);

  return card;
}

export default lessonCard;
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/lesson-card.js
git commit -m "feat(viewer): lesson-card with all three shelf flavors + reinforce"
```

---

### Task 20: `js/screens/lessons.js` — Shelves view (default)

**Files:**
- Modify: `plugins/taskmaster/viewer/js/screens/lessons.js` (replace stub)

- [ ] **Step 1: Replace the stub**

Replace `plugins/taskmaster/viewer/js/screens/lessons.js` with:

```js
import { lessonCard } from '../components/lesson-card.js';
import * as api from '../api.js';

export const meta = { title: 'Lessons', icon: '✦', sidebarKey: 'lessons' };

const SHELVES = [
  { key: 'core',    title: 'Core',    tagline: 'Frequently reinforced. Apply by default.' },
  { key: 'active',  title: 'Active',  tagline: 'Recent. Apply when anchor matches.' },
  { key: 'retired', title: 'Retired', tagline: 'No reinforcement in 30+ days. Click to revive.' },
];

export async function mount(root, { store, prefs }) {
  root.innerHTML = '';
  const screen = document.createElement('section');
  screen.className = 'lessons';

  // ---- header
  const header = document.createElement('header');
  header.className = 'lessons__header';
  header.innerHTML = `<h1 class="lessons__title">Lessons</h1>`;
  const toggle = document.createElement('div');
  toggle.className = 'lessons__view-toggle';
  for (const v of [['A', 'Shelves'], ['B', 'Flat'], ['C', 'By Anchor']]) {
    const b = document.createElement('button');
    b.dataset.view = v[0]; b.textContent = v[1];
    b.addEventListener('click', () => setView(v[0]));
    toggle.appendChild(b);
  }
  header.appendChild(toggle);
  screen.appendChild(header);

  // ---- shelves container
  const shelvesEl = document.createElement('div');
  shelvesEl.className = 'lessons__shelves';
  screen.appendChild(shelvesEl);

  root.appendChild(screen);

  let currentView = (prefs.getPrefs().screens?.lessons?.view) || 'A';
  function setView(v) {
    currentView = v;
    prefs.patch({ screens: { lessons: { view: v } } });
    render();
  }

  async function reinforce(id) {
    const summary = await api.reinforceLesson(id, { source: 'user', note: '' });
    // Refetch to get the updated shelf placement from server
    const fresh = await api.getLessons();
    store.setLessons(fresh.lessons);
    render();
    return summary;
  }

  function render() {
    // Highlight the active toggle button
    for (const b of toggle.querySelectorAll('button')) {
      b.classList.toggle('is-active', b.dataset.view === currentView);
    }
    shelvesEl.innerHTML = '';
    const lessons = store.getLessons() || [];

    if (currentView === 'A') {
      renderShelves(shelvesEl, lessons);
    } else if (currentView === 'B') {
      renderFlat(shelvesEl, lessons);
    } else {
      renderByAnchor(shelvesEl, lessons);
    }
  }

  function renderShelves(parent, lessons) {
    for (const shelf of SHELVES) {
      const items = lessons.filter(l => (l.shelf || 'active') === shelf.key);
      const sec = document.createElement('section');
      sec.className = `lessons-shelf lessons-shelf--${shelf.key}`;
      sec.innerHTML = `
        <header class="lessons-shelf__header">
          <span>${shelf.title} · ${items.length}</span>
          <span class="lessons-shelf__tagline">${shelf.tagline}</span>
        </header>`;
      const grid = document.createElement('div');
      grid.className = 'lessons-shelf__grid';
      for (const lesson of items) {
        grid.appendChild(lessonCard(lesson, { onReinforce: reinforce }));
      }
      sec.appendChild(grid);
      parent.appendChild(sec);
    }
  }

  function renderFlat(parent, lessons) {
    const sec = document.createElement('section');
    sec.className = 'lessons-shelf lessons-shelf--flat';
    sec.innerHTML = `
      <header class="lessons-shelf__header">
        <span>All lessons · ${lessons.length}</span>
      </header>`;
    const grid = document.createElement('div');
    grid.className = 'lessons-shelf__grid';
    const sorted = [...lessons].sort((a, b) => (b.reinforce_count || 0) - (a.reinforce_count || 0));
    for (const l of sorted) grid.appendChild(lessonCard(l, { onReinforce: reinforce }));
    sec.appendChild(grid);
    parent.appendChild(sec);
  }

  function renderByAnchor(parent, lessons) {
    const groups = new Map();
    for (const l of lessons) {
      const files = (l.triggers && l.triggers.files) || ['(any)'];
      for (const f of files) {
        if (!groups.has(f)) groups.set(f, []);
        groups.get(f).push(l);
      }
    }
    const sortedKeys = [...groups.keys()].sort();
    for (const key of sortedKeys) {
      const sec = document.createElement('section');
      sec.className = 'lessons-shelf';
      sec.innerHTML = `
        <header class="lessons-shelf__header">
          <code>${key}</code><span class="lessons-shelf__tagline">${groups.get(key).length} lessons</span>
        </header>`;
      const grid = document.createElement('div');
      grid.className = 'lessons-shelf__grid';
      for (const l of groups.get(key)) grid.appendChild(lessonCard(l, { onReinforce: reinforce }));
      sec.appendChild(grid);
      parent.appendChild(sec);
    }
  }

  // First fetch (store may already have data)
  if (!store.getLessons() || store.getLessons().length === 0) {
    const data = await api.getLessons();
    store.setLessons(data.lessons);
  }
  render();

  // Cleanup function
  return () => {};
}
```

- [ ] **Step 2: Add `getLessons` / `setLessons` to `store.js`**

In `plugins/taskmaster/viewer/js/store.js`, inside the store factory, add (alongside existing slices):

```js
let _lessons = null;
export function getLessons()  { return _lessons; }
export function setLessons(v) { _lessons = v || []; _emit('lessons'); }
```

(Adapt to whatever shape `store.js` already uses — if it's a single object, add `_lessons` to that object instead.)

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/js/screens/lessons.js plugins/taskmaster/viewer/js/store.js
git commit -m "feat(viewer): lessons screen with shelves/flat/by-anchor views"
```

---

### Task 21: Playwright smoke — Lessons screen mounts and Reinforce works

**Files:**
- Create: `plugins/taskmaster/viewer/tests/lessons.spec.js`

- [ ] **Step 1: Write the test**

Create `plugins/taskmaster/viewer/tests/lessons.spec.js`:

```js
import { test, expect } from '@playwright/test';

test('lessons screen renders three shelves', async ({ page }) => {
  await page.goto('/v3/#/lessons');
  await expect(page.locator('.lessons')).toBeVisible();
  await expect(page.locator('.lessons-shelf--core')).toBeVisible();
  await expect(page.locator('.lessons-shelf--active')).toBeVisible();
  await expect(page.locator('.lessons-shelf--retired')).toBeVisible();
});

test('reinforce button bumps count via API', async ({ page }) => {
  await page.goto('/v3/#/lessons');
  const card = page.locator('.lesson-card').first();
  await card.hover();
  const initialCount = await card.locator('.sparkline-count').textContent();
  await card.locator('.lesson-card__reinforce').click();
  await expect(card.locator('.lesson-card__reinforce.is-fired')).toBeVisible();
  await expect(card.locator('.lesson-card__reinforce')).toHaveText(/Reinforced now/);
  // Count should have increased on next render
  await page.waitForTimeout(200);
  const newCount = await card.locator('.sparkline-count').textContent();
  expect(parseInt(newCount, 10)).toBeGreaterThan(parseInt(initialCount, 10));
});

test('view toggle persists to prefs', async ({ page }) => {
  await page.goto('/v3/#/lessons');
  await page.locator('.lessons__view-toggle button[data-view="B"]').click();
  await expect(page.locator('.lessons__view-toggle button[data-view="B"]')).toHaveClass(/is-active/);
  await page.reload();
  await expect(page.locator('.lessons__view-toggle button[data-view="B"]')).toHaveClass(/is-active/);
});
```

- [ ] **Step 2: Run the test**

Run: `npx playwright test plugins/taskmaster/viewer/tests/lessons.spec.js`
Expected: 3 tests PASS (assumes the dev server has at least one lesson seeded; the test fixture or existing repo lessons satisfy this — see Task 49 for a fixture seed if missing).

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/tests/lessons.spec.js
git commit -m "test(viewer): playwright smoke for lessons screen"
```

---

## M5 — Issues Screen + issue-card

### Task 22: `css/screens/issues.css` — hybrid layout + card

**Files:**
- Create: `plugins/taskmaster/viewer/css/screens/issues.css`
- Modify: `plugins/taskmaster/viewer/index.html` (link)

- [ ] **Step 1: Write the CSS**

Create `plugins/taskmaster/viewer/css/screens/issues.css`:

```css
/* Issues screen — Hybrid:
   Top: Investigating + Open as live columns (1fr / 1.6fr).
   Bottom: Resolved shelf (Fixed + Wontfix), faded, collapsible. */

.issues {
  --issues-card-bg: #181a20;          /* slightly cooler than other cards */
  --issues-card-border: var(--border);
  --issues-investigating: #6ea8ff;
  --sev-critical: #e87a85;
  --sev-high:     #e8a34d;
  --sev-medium:   #c8b75a;
  --sev-low:      #888c95;

  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 24px 28px;
}

.issues__header {
  display: flex; align-items: center; justify-content: space-between;
}
.issues__filters { display: flex; gap: 8px; flex-wrap: wrap; }
.issues__sev-chip {
  padding: 3px 10px;
  border-radius: 999px;
  border: 1px solid var(--border);
  font-size: 12px;
  cursor: pointer;
}
.issues__sev-chip[data-sev="Critical"] { color: var(--sev-critical); }
.issues__sev-chip[data-sev="High"]     { color: var(--sev-high); }
.issues__sev-chip[data-sev="Medium"]   { color: var(--sev-medium); }
.issues__sev-chip[data-sev="Low"]      { color: var(--sev-low); }
.issues__sev-chip.is-active { background: var(--bg-active); }

.issues__columns {
  display: grid;
  grid-template-columns: 1fr 1.6fr;
  gap: 16px;
}
.issues__column {
  background: var(--bg-pane);
  border-radius: 6px;
  padding: 12px;
  display: flex; flex-direction: column; gap: 10px;
}
.issues__column-header {
  display: flex; align-items: center; gap: 8px;
  font-size: 12px; color: var(--ink-2);
  text-transform: uppercase; letter-spacing: 0.5px;
}

/* ---- card (live columns) ---- */

.issue-card {
  background: var(--issues-card-bg);
  border: 1px solid var(--issues-card-border);
  border-radius: 6px;
  padding: 12px;
  display: flex; flex-direction: column; gap: 10px;
}
.issue-card__head {
  display: flex; align-items: center; gap: 8px;
}
.issue-card__id {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
}
.issue-card__id[data-sev="Critical"] { color: var(--sev-critical); }
.issue-card__id[data-sev="High"]     { color: var(--sev-high); }
.issue-card__id[data-sev="Medium"]   { color: var(--sev-medium); }
.issue-card__id[data-sev="Low"]      { color: var(--sev-low); }

.issue-card__title { font-size: 14px; flex: 1; color: var(--ink); }

.issue-card__sev-chip {
  padding: 2px 8px; border-radius: 999px; font-size: 11px;
  background: rgba(255,255,255,0.04);
}
.issue-card__sev-chip[data-sev="Critical"] { color: var(--sev-critical); }
.issue-card__sev-chip[data-sev="High"]     { color: var(--sev-high); }
.issue-card__sev-chip[data-sev="Medium"]   { color: var(--sev-medium); }
.issue-card__sev-chip[data-sev="Low"]      { color: var(--sev-low); }

.issue-card__blocks {
  font-size: 11px;
  color: var(--sev-critical);
  padding: 1px 6px;
  border: 1px solid var(--sev-critical);
  border-radius: 3px;
  background: rgba(232, 122, 133, 0.08);
}

/* console-style location: bg-deep + inset shadow + mono */
.issue-card__location {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: var(--ink-2);
  background: var(--bg-deep);
  padding: 6px 8px;
  border-radius: 3px;
  box-shadow: inset 0 1px 0 rgba(0,0,0,0.4);
}
.issue-card__location-num { color: var(--accent-blue, #6ea8ff); }

/* italic-serif symptom with quote-mark left border (decorative typography) */
.issue-card__symptom {
  font-family: 'Source Serif Pro', Georgia, serif;
  font-style: italic;
  color: var(--ink);
  padding-left: 12px;
  border-left: 2px solid var(--ink-3);    /* decorative quote, not a status ribbon */
  font-size: 13.5px;
  line-height: 1.5;
}

/* repro block: numbered, mono, deep bg, collapsible */
.issue-card__repro { font-size: 12px; color: var(--ink-2); }
.issue-card__repro-summary {
  cursor: pointer;
  font-family: 'JetBrains Mono', monospace;
  color: var(--ink-3);
}
.issue-card__repro[open] .issue-card__repro-summary { color: var(--ink-2); }
.issue-card__repro-list {
  background: var(--bg-deep);
  border-radius: 3px;
  padding: 8px 10px 8px 28px;
  margin: 6px 0 0;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11.5px;
  color: var(--ink-2);
}

.issue-card__impact { font-size: 12px; color: var(--ink-2); line-height: 1.5; }
.issue-card__impact code {
  font-family: 'JetBrains Mono', monospace;
  background: var(--bg-deep);
  padding: 1px 4px;
  border-radius: 2px;
}

/* aging bar */
.aging-bar { display: flex; align-items: center; gap: 8px; }
.aging-bar__track {
  flex: 1; height: 4px; background: var(--bg-deep); border-radius: 2px; overflow: hidden;
}
.aging-bar__fill { height: 100%; transition: width 200ms ease; }
.aging-bar--fresh .aging-bar__fill { background: var(--accent-green, #5fcdb8); }
.aging-bar--aging .aging-bar__fill { background: var(--sev-high); }
.aging-bar--stale .aging-bar__fill { background: var(--sev-critical); }
.aging-bar__chip { font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; }
.aging-bar__chip--fresh { color: var(--accent-green, #5fcdb8); }
.aging-bar__chip--aging { color: var(--sev-high); }
.aging-bar__chip--stale { color: var(--sev-critical); }

/* footer: task pills + investigating tag */
.issue-card__footer {
  display: flex; align-items: center; justify-content: space-between;
  padding-top: 4px; border-top: 1px solid var(--border);
}
.issue-card__task-pills { display: flex; gap: 4px; flex-wrap: wrap; }
.issue-card__task-pill {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  padding: 1px 6px;
  background: var(--bg-deep);
  color: var(--ink-2);
  border-radius: 3px;
  cursor: pointer;
}
.issue-card__investigating {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 11px; color: var(--issues-investigating);
}
.issue-card__investigating::before {
  content: ''; width: 6px; height: 6px; border-radius: 50%;
  background: var(--issues-investigating);
  animation: issue-pulse 1.6s ease-in-out infinite;
}
@keyframes issue-pulse { 0%,100% { opacity: 0.4; } 50% { opacity: 1; } }

/* ---- resolved shelf (one-line cards) ---- */

.issues__resolved-shelf {
  display: flex; flex-direction: column; gap: 6px;
  opacity: 0.7;
}
.issues__resolved-header {
  display: flex; align-items: center; gap: 10px;
  font-size: 12px; color: var(--ink-3); text-transform: uppercase;
  cursor: pointer;
}
.issues__resolved-list { display: flex; flex-direction: column; gap: 4px; }
.issues__resolved-list[hidden] { display: none; }

.issue-row {
  display: grid;
  grid-template-columns: 16px 90px 60px 1fr 110px 80px;
  align-items: center; gap: 10px;
  font-size: 12px;
  padding: 4px 8px;
  background: var(--issues-card-bg);
  border-radius: 4px;
  color: var(--ink-2);
}
.issue-row__mark {
  text-align: center; font-size: 10px;
  padding: 1px 6px; border-radius: 999px;
}
.issue-row__mark--fixed   { color: var(--accent-green, #5fcdb8); border: 1px solid var(--accent-green, #5fcdb8); }
.issue-row__mark--wontfix { color: var(--ink-3); border: 1px solid var(--ink-3); }
.issue-row__title { color: var(--ink); }
.issue-row__when { font-size: 11px; color: var(--ink-3); text-align: right; }
```

- [ ] **Step 2: Link the CSS**

Append to `<head>` in `plugins/taskmaster/viewer/index.html`:

```html
<link rel="stylesheet" href="/static/v3/css/screens/issues.css">
```

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/css/screens/issues.css plugins/taskmaster/viewer/index.html
git commit -m "feat(viewer): issues screen CSS — hybrid + bug-report card"
```

---

### Task 23: `issue-card.js` — bug-report flavor

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/issue-card.js`

- [ ] **Step 1: Write the file**

Create `plugins/taskmaster/viewer/js/components/issue-card.js`:

```js
import { severityGlyph, injectSeverityDefs } from './severity-glyph.js';
import { agingBar } from './aging-bar.js';
import { severityLabel } from '../util/severity-label.js';
import { computeBlocksCount } from '../util/issue-blocks.js';

const LOCATION_RE = /^(.*?):(\d+)(?::\d+)?$/;

function _renderLocation(loc) {
  const el = document.createElement('div');
  el.className = 'issue-card__location';
  el.textContent = 'at ';
  for (const item of loc) {
    const m = LOCATION_RE.exec(item);
    if (m) {
      el.appendChild(document.createTextNode(`${m[1]}:`));
      const num = document.createElement('span');
      num.className = 'issue-card__location-num';
      num.textContent = m[2];
      el.appendChild(num);
    } else {
      el.appendChild(document.createTextNode(item));
    }
    el.appendChild(document.createTextNode('  '));
  }
  return el;
}

export function issueCard(issue, { tasksIndex = {}, agingCfg, onTaskClick } = {}) {
  injectSeverityDefs();
  const label = issue.severity_label || severityLabel(issue.severity);
  const card = document.createElement('article');
  card.className = 'issue-card';
  card.setAttribute('data-issue-id', issue.id);
  card.setAttribute('data-status', issue.status || 'open');

  // ---- head: glyph · id · title · sev chip · blocks chip
  const head = document.createElement('div');
  head.className = 'issue-card__head';
  head.appendChild(severityGlyph(label));
  const id = document.createElement('span');
  id.className = 'issue-card__id';
  id.dataset.sev = label;
  id.textContent = issue.id;
  head.appendChild(id);
  const title = document.createElement('span');
  title.className = 'issue-card__title';
  title.textContent = issue.title;
  head.appendChild(title);
  const sev = document.createElement('span');
  sev.className = 'issue-card__sev-chip';
  sev.dataset.sev = label;
  sev.textContent = label;
  head.appendChild(sev);

  const blocks = computeBlocksCount(issue, tasksIndex);
  if (blocks > 0) {
    const chip = document.createElement('span');
    chip.className = 'issue-card__blocks';
    chip.textContent = `⊘ blocks ${blocks}`;
    head.appendChild(chip);
  }
  card.appendChild(head);

  // ---- console-style location
  if (issue.location && issue.location.length) {
    card.appendChild(_renderLocation(issue.location));
  }

  // ---- italic-serif symptom
  if (issue.symptom) {
    const sym = document.createElement('div');
    sym.className = 'issue-card__symptom';
    sym.textContent = issue.symptom;
    card.appendChild(sym);
  }

  // ---- repro block (collapsed by default in live columns)
  if (issue.repro && issue.repro.length) {
    const det = document.createElement('details');
    det.className = 'issue-card__repro';
    const sum = document.createElement('summary');
    sum.className = 'issue-card__repro-summary';
    sum.textContent = `Repro · ${issue.repro.length} steps · click to expand`;
    det.appendChild(sum);
    const ol = document.createElement('ol');
    ol.className = 'issue-card__repro-list';
    for (const step of issue.repro) {
      const li = document.createElement('li');
      li.textContent = step;
      ol.appendChild(li);
    }
    det.appendChild(ol);
    card.appendChild(det);
  }

  // ---- impact paragraph
  if (issue.impact) {
    const imp = document.createElement('div');
    imp.className = 'issue-card__impact';
    imp.innerHTML = issue.impact.replace(/`([^`]+)`/g, '<code>$1</code>');
    card.appendChild(imp);
  }

  // ---- aging bar
  if (agingCfg) {
    card.appendChild(agingBar({ ...issue, severity_label: label }, agingCfg));
  }

  // ---- footer: task pills + investigating tag
  const footer = document.createElement('div');
  footer.className = 'issue-card__footer';
  const pills = document.createElement('div');
  pills.className = 'issue-card__task-pills';
  for (const tid of (issue.related_tasks || [])) {
    const p = document.createElement('span');
    p.className = 'issue-card__task-pill';
    p.textContent = tid;
    p.addEventListener('click', () => onTaskClick?.(tid));
    pills.appendChild(p);
  }
  footer.appendChild(pills);
  if (issue.status === 'investigating') {
    const tag = document.createElement('span');
    tag.className = 'issue-card__investigating';
    tag.textContent = 'looking at it';
    footer.appendChild(tag);
  }
  card.appendChild(footer);

  return card;
}

export function issueRow(issue) {
  const label = issue.severity_label || severityLabel(issue.severity);
  const row = document.createElement('div');
  row.className = 'issue-row';
  row.setAttribute('data-issue-id', issue.id);

  const glyph = severityGlyph(label);
  glyph.classList.add('issue-row__glyph');
  row.appendChild(glyph);

  const id = document.createElement('span');
  id.className = 'issue-card__id';
  id.dataset.sev = label;
  id.textContent = issue.id;
  row.appendChild(id);

  const mark = document.createElement('span');
  mark.className = `issue-row__mark issue-row__mark--${issue.status}`;
  mark.textContent = issue.status === 'fixed' ? 'Fixed' : 'Wontfix';
  row.appendChild(mark);

  const title = document.createElement('span');
  title.className = 'issue-row__title';
  title.textContent = issue.title;
  row.appendChild(title);

  const tp = document.createElement('span');
  tp.className = 'issue-card__task-pill';
  tp.textContent = (issue.related_tasks && issue.related_tasks[0]) || '';
  row.appendChild(tp);

  const when = document.createElement('span');
  when.className = 'issue-row__when';
  if (issue.resolved) {
    const days = Math.max(0, Math.floor((Date.now() - new Date(issue.resolved).getTime()) / 86_400_000));
    when.textContent = issue.status === 'fixed' ? `fixed ${days}d ago` : `closed ${days}d ago`;
  }
  row.appendChild(when);

  return row;
}

export default issueCard;
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/issue-card.js
git commit -m "feat(viewer): issue-card bug-report flavor + one-line issue-row"
```

---

### Task 24: `js/screens/issues.js` — Hybrid view (default)

**Files:**
- Modify: `plugins/taskmaster/viewer/js/screens/issues.js` (replace stub)

- [ ] **Step 1: Replace the stub**

Replace `plugins/taskmaster/viewer/js/screens/issues.js` with:

```js
import { issueCard, issueRow } from '../components/issue-card.js';
import { severityLabel } from '../util/severity-label.js';
import * as api from '../api.js';

export const meta = { title: 'Issues', icon: '!', sidebarKey: 'issues' };

const SEVERITIES = ['Critical', 'High', 'Medium', 'Low'];

export async function mount(root, { store, prefs }) {
  root.innerHTML = '';
  const screen = document.createElement('section');
  screen.className = 'issues';

  // ---- header
  const header = document.createElement('header');
  header.className = 'issues__header';
  header.innerHTML = '<h1>Issues</h1>';
  const filters = document.createElement('div');
  filters.className = 'issues__filters';
  for (const sev of SEVERITIES) {
    const c = document.createElement('span');
    c.className = 'issues__sev-chip';
    c.dataset.sev = sev;
    c.textContent = sev;
    c.addEventListener('click', () => {
      c.classList.toggle('is-active');
      render();
    });
    filters.appendChild(c);
  }
  header.appendChild(filters);

  const toggle = document.createElement('div');
  toggle.className = 'lessons__view-toggle';     // reuse same toggle style
  for (const v of [['A', 'Hybrid'], ['B', 'Kanban'], ['C', 'List']]) {
    const b = document.createElement('button');
    b.dataset.view = v[0]; b.textContent = v[1];
    b.addEventListener('click', () => setView(v[0]));
    toggle.appendChild(b);
  }
  header.appendChild(toggle);
  screen.appendChild(header);

  // ---- columns + resolved shelf
  const columns = document.createElement('div');
  columns.className = 'issues__columns';
  const investigatingCol = document.createElement('div');
  investigatingCol.className = 'issues__column';
  investigatingCol.innerHTML = '<header class="issues__column-header">Investigating</header>';
  const investigatingList = document.createElement('div');
  investigatingCol.appendChild(investigatingList);

  const openCol = document.createElement('div');
  openCol.className = 'issues__column';
  openCol.innerHTML = '<header class="issues__column-header">Open</header>';
  const openList = document.createElement('div');
  openCol.appendChild(openList);

  columns.appendChild(investigatingCol);
  columns.appendChild(openCol);
  screen.appendChild(columns);

  const resolvedShelf = document.createElement('section');
  resolvedShelf.className = 'issues__resolved-shelf';
  const resolvedHeader = document.createElement('header');
  resolvedHeader.className = 'issues__resolved-header';
  const resolvedList = document.createElement('div');
  resolvedList.className = 'issues__resolved-list';
  resolvedList.hidden = true;
  resolvedHeader.addEventListener('click', () => {
    resolvedList.hidden = !resolvedList.hidden;
    resolvedHeader.querySelector('.caret').textContent = resolvedList.hidden ? '▾' : '▴';
  });
  resolvedShelf.appendChild(resolvedHeader);
  resolvedShelf.appendChild(resolvedList);
  screen.appendChild(resolvedShelf);

  root.appendChild(screen);

  let currentView = (prefs.getPrefs().screens?.issues?.view) || 'A';
  function setView(v) {
    currentView = v;
    prefs.patch({ screens: { issues: { view: v } } });
    render();
  }

  function activeFilters() {
    return [...filters.querySelectorAll('.is-active')].map(el => el.dataset.sev);
  }

  function render() {
    for (const b of toggle.querySelectorAll('button')) {
      b.classList.toggle('is-active', b.dataset.view === currentView);
    }
    const issues = (store.getIssues() || []).filter(i => {
      const sevs = activeFilters();
      if (sevs.length === 0) return true;
      return sevs.includes(i.severity_label || severityLabel(i.severity));
    });

    const tasksIndex = store.getTasksIndex ? store.getTasksIndex() : {};
    const agingCfg = prefs.getPrefs().issues?.aging || {};

    investigatingList.innerHTML = '';
    openList.innerHTML = '';
    resolvedList.innerHTML = '';

    const investigating = issues.filter(i => i.status === 'investigating');
    const open          = issues.filter(i => i.status === 'open');
    const resolved      = issues.filter(i => i.status === 'fixed' || i.status === 'wontfix');

    for (const i of investigating) {
      investigatingList.appendChild(issueCard(i, { tasksIndex, agingCfg, onTaskClick: id => location.hash = `#/task/${id}` }));
    }
    for (const i of open) {
      openList.appendChild(issueCard(i, { tasksIndex, agingCfg, onTaskClick: id => location.hash = `#/task/${id}` }));
    }
    for (const i of resolved) {
      resolvedList.appendChild(issueRow(i));
    }
    resolvedHeader.innerHTML = `<span class="caret">▾</span> Resolved · ${resolved.length} issues`;

    // View B/C: just collapse columns into a single list (lightweight pass)
    if (currentView === 'C') {
      columns.style.gridTemplateColumns = '1fr';
      openCol.querySelector('.issues__column-header').textContent = 'All open';
      investigatingCol.style.display = 'none';
      // append investigating + open to a single list visually via openList
      for (const i of investigating) {
        openList.insertBefore(
          issueCard(i, { tasksIndex, agingCfg, onTaskClick: id => location.hash = `#/task/${id}` }),
          openList.firstChild,
        );
      }
    } else {
      columns.style.gridTemplateColumns = '1fr 1.6fr';
      investigatingCol.style.display = '';
      openCol.querySelector('.issues__column-header').textContent = 'Open';
    }
  }

  if (!store.getIssues() || store.getIssues().length === 0) {
    const data = await api.getIssues({ includeResolved: true });
    store.setIssues(data.issues);
  }
  render();
  return () => {};
}
```

- [ ] **Step 2: Add `getIssues` / `setIssues` to `store.js`**

In `plugins/taskmaster/viewer/js/store.js`, add (alongside `getLessons` / `setLessons`):

```js
let _issues = null;
export function getIssues()  { return _issues; }
export function setIssues(v) { _issues = v || []; _emit('issues'); }
```

(Same caveat as Task 20 — adapt to existing store shape.)

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/js/screens/issues.js plugins/taskmaster/viewer/js/store.js
git commit -m "feat(viewer): issues screen with hybrid layout + resolved shelf"
```

---

### Task 25: Playwright smoke — Issues screen renders + repro expands

**Files:**
- Create: `plugins/taskmaster/viewer/tests/issues.spec.js`

- [ ] **Step 1: Write the test**

Create `plugins/taskmaster/viewer/tests/issues.spec.js`:

```js
import { test, expect } from '@playwright/test';

test('issues screen renders Investigating + Open columns', async ({ page }) => {
  await page.goto('/v3/#/issues');
  await expect(page.locator('.issues')).toBeVisible();
  await expect(page.locator('.issues__column-header').filter({ hasText: 'Investigating' })).toBeVisible();
  await expect(page.locator('.issues__column-header').filter({ hasText: 'Open' })).toBeVisible();
});

test('issue card shows severity word, not P0/P1', async ({ page }) => {
  await page.goto('/v3/#/issues');
  const sevChips = page.locator('.issue-card__sev-chip');
  const count = await sevChips.count();
  for (let i = 0; i < count; i++) {
    const text = await sevChips.nth(i).textContent();
    expect(text.trim()).toMatch(/^(Critical|High|Medium|Low)$/);
  }
});

test('repro block expands on click', async ({ page }) => {
  await page.goto('/v3/#/issues');
  const repro = page.locator('.issue-card__repro').first();
  await expect(repro).toBeVisible();
  await expect(repro).not.toHaveAttribute('open', '');
  await repro.locator('summary').click();
  await expect(repro).toHaveAttribute('open', '');
});

test('resolved shelf collapsed by default and expandable', async ({ page }) => {
  await page.goto('/v3/#/issues');
  const list = page.locator('.issues__resolved-list');
  await expect(list).toBeHidden();
  await page.locator('.issues__resolved-header').click();
  await expect(list).toBeVisible();
});
```

- [ ] **Step 2: Run the test**

Run: `npx playwright test plugins/taskmaster/viewer/tests/issues.spec.js`
Expected: 4 tests PASS (assumes at least one issue with `repro` is seeded — Task 49 covers fixture seeding if absent).

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/tests/issues.spec.js
git commit -m "test(viewer): playwright smoke for issues screen"
```

---

## M6 — Integration Smoke + Spec Coverage

### Task 26: Lessons screen — anchor-pills, since-caption, kind-icon assertions

**Files:**
- Modify: `plugins/taskmaster/viewer/tests/lessons.spec.js`

- [ ] **Step 1: Append spec-coverage assertions**

Append to `plugins/taskmaster/viewer/tests/lessons.spec.js`:

```js
test('lesson card surfaces all §3.13 elements', async ({ page }) => {
  await page.goto('/v3/#/lessons');
  const card = page.locator('.lesson-card').first();
  // kind icon
  await expect(card.locator('.lesson-card__kind')).toBeVisible();
  await expect(card.locator('.lesson-card__kind')).toHaveText(/^(⚠|◇|⊘)$/);
  // anchor pills with When: label
  await expect(card.locator('.anchor-pills__label')).toHaveText('When:');
  // first_seen caption
  await expect(card.locator('.lesson-card__since')).toBeVisible();
  // active signal: sparkline pill with count
  await expect(card.locator('.sparkline-pill .sparkline-count')).toBeVisible();
  // passive signal: dot meter
  await expect(card.locator('.dot-meter')).toBeVisible();
});

test('core shelf shows gold styling on ID', async ({ page }) => {
  await page.goto('/v3/#/lessons');
  const coreCard = page.locator('.lesson-card--core').first();
  if (await coreCard.count() === 0) test.skip(); // no core lessons in fixture
  const idColor = await coreCard.locator('.lesson-card__id').evaluate(el => getComputedStyle(el).color);
  // Gold-ish: high red, medium green, low blue
  const m = idColor.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
  expect(Number(m[1])).toBeGreaterThan(150);
});
```

- [ ] **Step 2: Run**

Run: `npx playwright test plugins/taskmaster/viewer/tests/lessons.spec.js`
Expected: All PASS.

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/tests/lessons.spec.js
git commit -m "test(viewer): lesson card spec-coverage assertions"
```

---

### Task 27: Issues screen — location, symptom, blocks-chip assertions

**Files:**
- Modify: `plugins/taskmaster/viewer/tests/issues.spec.js`

- [ ] **Step 1: Append spec-coverage assertions**

Append to `plugins/taskmaster/viewer/tests/issues.spec.js`:

```js
test('issue card surfaces all §3.14 elements', async ({ page }) => {
  await page.goto('/v3/#/issues');
  const card = page.locator('.issue-card').first();
  // severity hexagon glyph
  await expect(card.locator('.sev-glyph svg')).toBeVisible();
  // console-style location
  await expect(card.locator('.issue-card__location')).toBeVisible();
  await expect(card.locator('.issue-card__location-num')).toBeVisible();
  // italic-serif symptom
  const symptomFont = await card.locator('.issue-card__symptom').evaluate(el => getComputedStyle(el).fontStyle);
  expect(symptomFont).toBe('italic');
  // aging bar
  await expect(card.locator('.aging-bar')).toBeVisible();
  await expect(card.locator('.aging-bar__chip')).toHaveText(/^(Fresh|Aging|Stale)$/);
});

test('blocks chip appears when issue blocks non-done tasks', async ({ page }) => {
  await page.goto('/v3/#/issues');
  const chip = page.locator('.issue-card__blocks').first();
  if (await chip.count() === 0) test.skip();
  await expect(chip).toHaveText(/⊘ blocks \d+/);
});
```

- [ ] **Step 2: Run**

Run: `npx playwright test plugins/taskmaster/viewer/tests/issues.spec.js`
Expected: All PASS.

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/tests/issues.spec.js
git commit -m "test(viewer): issue card spec-coverage assertions"
```

---

### Task 28: Cross-screen routing smoke

**Files:**
- Create: `plugins/taskmaster/viewer/tests/lessons-issues-routing.spec.js`

- [ ] **Step 1: Write the test**

Create `plugins/taskmaster/viewer/tests/lessons-issues-routing.spec.js`:

```js
import { test, expect } from '@playwright/test';

test('navigating lessons → issues → lessons via hash works', async ({ page }) => {
  await page.goto('/v3/#/lessons');
  await expect(page.locator('.lessons')).toBeVisible();

  await page.evaluate(() => location.hash = '#/issues');
  await expect(page.locator('.issues')).toBeVisible();

  await page.evaluate(() => location.hash = '#/lessons');
  await expect(page.locator('.lessons')).toBeVisible();
});

test('clicking an issue task pill navigates to task detail', async ({ page }) => {
  await page.goto('/v3/#/issues');
  const pill = page.locator('.issue-card__task-pill').first();
  if (await pill.count() === 0) test.skip();
  const id = (await pill.textContent()).trim();
  await pill.click();
  await expect(page).toHaveURL(new RegExp(`#/task/${id}`));
});
```

- [ ] **Step 2: Run**

Run: `npx playwright test plugins/taskmaster/viewer/tests/lessons-issues-routing.spec.js`
Expected: 2 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/tests/lessons-issues-routing.spec.js
git commit -m "test(viewer): lessons↔issues routing smoke"
```

---

### Task 29: Threshold override — `viewer.lessons.thresholds` end-to-end

**Files:**
- Modify: `plugins/taskmaster/tests/test_server_lessons.py`

- [ ] **Step 1: Write the failing test**

Append to `plugins/taskmaster/tests/test_server_lessons.py`:

```python
def test_thresholds_override_changes_shelf_placement(running_server, tmp_path):
    """If user lowers core_count to 2, lessons with 3 events go to 'core'."""
    base, _ = running_server
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    events = [
        {"at": (now - timedelta(days=d)).strftime("%Y-%m-%dT%H:%M:%SZ"), "source": "user", "note": ""}
        for d in [1, 5, 10]
    ]
    _write_lesson(tmp_path, "L-T1", reinforce_count=3, reinforce_events=events)

    # Default thresholds → 3 events is below core_count=7 → 'active'
    payload = json.loads(urllib.request.urlopen(f"{base}/api/lessons").read())
    by_id = {l["id"]: l for l in payload["lessons"]}
    assert by_id["L-T1"]["shelf"] == "active"

    # Lower the threshold via PUT /api/viewer/prefs
    body = json.dumps({"lessons": {"thresholds": {"core_count": 2}}}).encode()
    req = urllib.request.Request(
        f"{base}/api/viewer/prefs", data=body, method="PUT",
        headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(req)

    # Now the same lesson should be 'core'
    payload = json.loads(urllib.request.urlopen(f"{base}/api/lessons").read())
    by_id = {l["id"]: l for l in payload["lessons"]}
    assert by_id["L-T1"]["shelf"] == "core"
```

- [ ] **Step 2: Run**

Run: `python -m pytest plugins/taskmaster/tests/test_server_lessons.py::test_thresholds_override_changes_shelf_placement -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/tests/test_server_lessons.py
git commit -m "test(taskmaster): viewer.lessons.thresholds override end-to-end"
```

---

### Task 30: Aging override — `viewer.issues.aging` end-to-end

**Files:**
- Modify: `plugins/taskmaster/tests/test_server_issues.py`

- [ ] **Step 1: Write the failing test**

Append to `plugins/taskmaster/tests/test_server_issues.py`:

```python
def test_aging_override_changes_tier(running_server, tmp_path):
    base, _ = running_server
    discovered = (datetime.now(timezone.utc) - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    _write_issue(tmp_path, "ISS-AG1", severity="P1", discovered=discovered)

    # Default High base = 30d → 5d ≈ 17% → Fresh
    payload = json.loads(urllib.request.urlopen(f"{base}/api/issues").read())
    by_id = {i["id"]: i for i in payload["issues"]}
    assert by_id["ISS-AG1"]["aging"]["tier"] == "Fresh"

    # Override High base to 5 days → 5d == 100% → Stale
    body = json.dumps({"issues": {"aging": {"High": 5}}}).encode()
    req = urllib.request.Request(
        f"{base}/api/viewer/prefs", data=body, method="PUT",
        headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(req)

    payload = json.loads(urllib.request.urlopen(f"{base}/api/issues").read())
    by_id = {i["id"]: i for i in payload["issues"]}
    assert by_id["ISS-AG1"]["aging"]["tier"] == "Stale"
```

- [ ] **Step 2: Run**

Run: `python -m pytest plugins/taskmaster/tests/test_server_issues.py::test_aging_override_changes_tier -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/tests/test_server_issues.py
git commit -m "test(taskmaster): viewer.issues.aging override end-to-end"
```

---

### Task 31: Reinforce-event source enforcement (viewer must send valid source)

**Files:**
- Modify: `plugins/taskmaster/tests/test_server_lessons.py`

- [ ] **Step 1: Write the failing test**

Append to `plugins/taskmaster/tests/test_server_lessons.py`:

```python
def test_reinforce_records_event_with_correct_source_and_note(running_server, tmp_path):
    base, _ = running_server
    _write_lesson(tmp_path, "L-300")
    body = json.dumps({"source": "claude", "note": "applied during refactor"}).encode()
    req = urllib.request.Request(
        f"{base}/api/lessons/L-300/reinforce", data=body, method="POST",
        headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(req)

    # Read back via API
    payload = json.loads(urllib.request.urlopen(f"{base}/api/lessons").read())
    by_id = {l["id"]: l for l in payload["lessons"]}
    events = by_id["L-300"]["reinforce_events"]
    assert events[-1]["source"] == "claude"
    assert events[-1]["note"] == "applied during refactor"
```

- [ ] **Step 2: Run**

Run: `python -m pytest plugins/taskmaster/tests/test_server_lessons.py::test_reinforce_records_event_with_correct_source_and_note -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/tests/test_server_lessons.py
git commit -m "test(taskmaster): reinforce stores source + note correctly"
```

---

### Task 32: Final spec-coverage walk + plan handoff

**Files:**
- Modify: `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-5b-lessons-issues.md` (this file — append Done section)

- [ ] **Step 1: Run the full server test suite**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_lesson_reinforce.py plugins/taskmaster/tests/test_server_lessons.py plugins/taskmaster/tests/test_server_issues.py -v`
Expected: All PASS (~25 tests).

- [ ] **Step 2: Run all pure-data unit tests**

Run: `node --test plugins/taskmaster/viewer/tests/unit/`
Expected: All PASS (3 files, ~14 tests).

- [ ] **Step 3: Run all Playwright smoke tests for 5b**

Run: `npx playwright test plugins/taskmaster/viewer/tests/lessons.spec.js plugins/taskmaster/viewer/tests/issues.spec.js plugins/taskmaster/viewer/tests/lessons-issues-routing.spec.js`
Expected: All PASS.

- [ ] **Step 4: Manual spec coverage walk**

Open the spec at `docs/superpowers/specs/2026-04-26-taskmaster-viewer-redesign.md` and tick each requirement:

§3.13 Lessons:
- [ ] Three shelves: Core / Active / Retired with progressive de-emphasis
- [ ] Core: gold gradient at top (no edge ribbon), gold ID
- [ ] Active: white italic-serif header, normal weight
- [ ] Retired: 55% opacity at rest, 85% on hover
- [ ] Threshold rule: ≥7 in 60d AND fire in 14d → Core
- [ ] `prefs.lessons.thresholds` overridable
- [ ] Active signal (sparkline + count + last-fired) in gold pill
- [ ] Passive signal (5-dot meter) ambient only
- [ ] Lesson kind icons: ⚠ gotcha / ◇ pattern / ⊘ anti-pattern (60% ink, tooltip on hover)
- [ ] Anchor pills with "When:" label, mono
- [ ] First-seen caption "since DATE" in `--ink-3`
- [ ] Reinforce button on hover, gold ↑, becomes ✓ "Reinforced now" green
- [ ] On Retired cards label is "Revive"

§3.14 Issues:
- [ ] Hybrid: Investigating + Open as live columns (1fr / 1.6fr)
- [ ] Resolved shelf below, faded, collapsible
- [ ] Severity hexagon glyph (SVG, scaled by severity)
- [ ] Console-style location with bg-deep + inset shadow + accent-blue line number
- [ ] Italic-serif symptom with quote-mark left border (decorative typography)
- [ ] Repro block: numbered, mono, collapsible, "N steps" summary
- [ ] Impact paragraph, sans, smaller, with `<code>` snippets
- [ ] Severity-tiered aging bar (Fresh/Aging/Stale chips, base periods 14/30/60/120)
- [ ] `prefs.issues.aging` overridable
- [ ] ⊘ blocks N chip computed at render time
- [ ] Severity words: Critical / High / Medium / Low — never P0/P1
- [ ] Bidirectional task ↔ issue link (task pills click to task detail)
- [ ] Card surface slightly cooler (#181a20)
- [ ] Resolved shelf one-line cards with severity glyph + Fixed/Wontfix mark + linked task pill + "fixed Nd ago"

- [ ] **Step 5: Final commit (plan complete)**

```bash
git commit --allow-empty -m "feat(taskmaster): plan-5b complete — lessons + issues screens"
```

---

## Done

All §3.13 and §3.14 requirements implemented. Server side: 3 new HTTP endpoints, 3 new MCP tools, schema migration. Client side: 2 screens, 7 new components, 4 utility modules, 3 pure-data test files, 3 Playwright spec files. Total tests added: ~25 server + 14 pure-data + 11 Playwright.
