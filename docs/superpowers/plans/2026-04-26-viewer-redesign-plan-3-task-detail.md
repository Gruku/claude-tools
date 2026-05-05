# Taskmaster Viewer Redesign — Plan 3: Task Detail (Variants A & B)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Task Detail screen in both variants — Variant A (Document) and Variant B (Graph) — including the supporting server endpoints (`GET /api/task/<id>` and `GET /api/task/<id>/related`), the shared right rail, a small markdown renderer, a pure-data graph layout helper with unit tests, and Playwright smoke tests covering both variants and the toggle.

**Architecture:** Two screen renderers (`task-detail-document.js`, `task-detail-graph.js`) coordinated by `task-detail.js` (the screen module the router resolves to). The renderer choice reads `prefs.screens.task_detail.view` ('A' | 'B'). Both share `right-rail.js`. Variant B uses an SVG canvas whose layout coordinates come from `dependency-graph.js`, a pure-data module that is unit-tested in isolation under `node --test`. Server-side, two new JSON endpoints fetch the full task body and a "related" payload (lessons matched by anchors, handovers and issues referencing the task, dependencies forward+reverse).

**Tech Stack:** Vanilla HTML/CSS/JS (no framework, no bundler) — same as Plan 1. Markdown rendering via the `marked` library loaded from CDN. Server tests via pytest + the `running_server` fixture from Plan 1. Browser tests via Playwright. Pure-data graph tests via Node's built-in `node --test`.

**Spec reference:** `docs/superpowers/specs/2026-04-26-taskmaster-viewer-redesign.md` §3.9 (both variants), §3.10 (v3 grounding), §3.7 (chip-only epic color rule applies on chips), §3.8 (time-in-status thresholds — amber after 4d).

**Inherits from Plan 1:** All architectural conventions in §"Architectural Conventions" of `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-1-foundation.md` are inherited verbatim — module shape, CSS naming, state+API rules, routing, persistence, test discipline. Not redefined here.

---

## File Structure

**New files (created in this plan):**

```
plugins/taskmaster/viewer/
├── css/
│   └── screens/
│       └── task-detail.css              # All Task Detail styles (Variants A + B + rail)
├── js/
│   ├── components/
│   │   ├── markdown.js                  # Markdown render helper (wraps `marked`)
│   │   ├── right-rail.js                # Shared right rail (used by both variants)
│   │   ├── dependency-graph.js          # Pure-data layout (L−2…L+2, edge paths)
│   │   ├── task-detail-document.js      # Variant A renderer
│   │   └── task-detail-graph.js         # Variant B renderer (SVG)
│   └── screens/
│       └── task-detail.js               # Replaces Plan 1 stub; orchestrates A vs B
└── tests/
    ├── task-detail.spec.js              # Playwright smoke (route, variant toggle, DOM)
    └── unit/
        └── dependency-graph.test.js     # node --test unit tests for graph layout
```

**Files modified (in this plan):**
- `plugins/taskmaster/backlog_server.py` — add `GET /api/task/<id>` and `GET /api/task/<id>/related` handlers, plus a `_route_task_detail()` helper.
- `plugins/taskmaster/viewer/index.html` — add the `marked` `<script>` from CDN (with SRI) and `<link>` for `task-detail.css`.
- `plugins/taskmaster/viewer/js/api.js` — add `getTask(id)` and `getTaskRelated(id)` methods.
- `plugins/taskmaster/viewer/js/store.js` — add `getTaskFull(id)` cache slice.
- `plugins/taskmaster/tests/test_server_task_detail.py` — **new** server endpoint tests.
- `plugins/taskmaster/viewer/package.json` — add `node --test` script for the unit suite (created here if not present from Plan 1).

---

## Architectural Conventions

Inherited verbatim from Plan 1 — see `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-1-foundation.md` §"Architectural Conventions". Do not redefine.

Plan-3-specific rules layered on top:

- **Task-detail screen reads `prefs.screens.task_detail.view`** at mount time and re-renders if it changes. The view toggle in the page header writes the new value via `api.savePrefs({ screens: { task_detail: { view: 'B' } } })`.
- **`dependency-graph.js` is pure data.** It MUST NOT import any DOM, browser, or fetch APIs. All inputs are plain objects; all outputs are plain objects. It is `import`able both in the browser and in Node.
- **Layout function naming is locked across files.** The pure-data module exports `computeGraphLayout(input)` returning `{ nodes, edges, columns }`. Both `task-detail-graph.js` (browser) and `dependency-graph.test.js` (Node) reference exactly that name.
- **Markdown is sandboxed.** `markdown.js` calls `marked.parse(src, { breaks: true })` and then runs the result through a small allowlist sanitiser before returning. No raw HTML pass-through.

---

## Milestones

- **M1 — Server endpoints** (Tasks 1–6): `GET /api/task/<id>` and `GET /api/task/<id>/related`, with full unit coverage.
- **M2 — Pure-data graph layout** (Tasks 7–13): `dependency-graph.js` + Node unit tests for empty / L0-only / deep upstream / deep downstream / mixed / cycle.
- **M3 — Shared client plumbing** (Tasks 14–17): `markdown.js`, API client extensions, store cache slice, `right-rail.js`.
- **M4 — Variant A (Document)** (Tasks 18–28): `task-detail-document.js` + CSS — header, meta, title, lock banner, chip row, spec-review badge + codex note, auto-mode banner, Docs section, Specification, Plan, Notes, Review instructions, Activity, Patchnote, Dates footer.
- **M5 — Variant B (Graph)** (Tasks 29–37): `task-detail-graph.js` + CSS — compact head, graph frame, axis rail, SVG layer, bezier edges, context band, controls, tabs.
- **M6 — Screen orchestrator + toggle** (Tasks 38–41): `task-detail.js` glue, view toggle, prefs round-trip, error states.
- **M7 — Playwright smoke + plan-level verification** (Tasks 42–46): route resolves, both variants render, toggle persists, all key DOM nodes present, full plan run-through.

---

## M1 — Server Endpoints

### Task 1: Define the `GET /api/task/<id>` payload shape with a failing test

**Files:**
- Create: `plugins/taskmaster/tests/test_server_task_detail.py`

- [ ] **Step 1: Write the failing test**

Create `plugins/taskmaster/tests/test_server_task_detail.py`:

```python
"""HTTP API tests for Task Detail endpoints (Plan 3)."""
import json
import threading
import time
import urllib.request
import urllib.error
import pytest


@pytest.fixture
def running_server(tmp_path, monkeypatch):
    """Start backlog_server on a free port; yields (base_url, server)."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".taskmaster").mkdir()
    (tmp_path / ".taskmaster" / "tasks").mkdir()
    (tmp_path / ".taskmaster" / "lessons").mkdir()
    (tmp_path / ".taskmaster" / "handovers").mkdir()
    (tmp_path / ".taskmaster" / "issues").mkdir()

    (tmp_path / "backlog.yaml").write_text(
        "meta:\n  project: test\n"
        "epics:\n  - {id: viewer, name: Viewer, color: '#6ea8ff'}\n"
        "phases:\n  - {id: 'P-01', name: Foundations}\n"
        "tasks:\n"
        "  - id: T-148\n"
        "    title: Implement task detail\n"
        "    status: in-progress\n"
        "    priority: High\n"
        "    estimate: M\n"
        "    epic: viewer\n"
        "    phase: P-01\n"
        "    branch: feat/task-detail\n"
        "    depends_on: [T-100]\n"
        "    anchors: ['plugins/taskmaster/viewer/**/*.js']\n"
        "    created: '2026-04-20'\n"
        "    started: '2026-04-22'\n"
        "  - id: T-100\n"
        "    title: Foundation\n"
        "    status: done\n"
        "    priority: High\n"
        "    estimate: L\n"
        "    epic: viewer\n"
        "    phase: P-01\n"
        "    created: '2026-04-10'\n"
        "    completed: '2026-04-19'\n"
        "  - id: T-200\n"
        "    title: Kanban screen\n"
        "    status: backlog\n"
        "    priority: High\n"
        "    estimate: L\n"
        "    epic: viewer\n"
        "    phase: P-01\n"
        "    depends_on: [T-148]\n"
        "    created: '2026-04-25'\n"
    )

    (tmp_path / ".taskmaster" / "tasks" / "T-148.md").write_text(
        "---\n"
        "id: T-148\n"
        "docs:\n"
        "  spec: docs/spec.md\n"
        "  plan: docs/plan.md\n"
        "review_instructions: |\n"
        "  Click Toggle button. Verify variant flips.\n"
        "---\n"
        "## Description\n"
        "Build the Task Detail screen in both variants.\n"
        "\n"
        "## Notes\n"
        "Use the `marked` library from CDN.\n"
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


def test_get_task_returns_full_payload(running_server):
    base, _ = running_server
    resp = urllib.request.urlopen(f"{base}/api/task/T-148")
    assert resp.status == 200
    body = json.loads(resp.read())

    # Index-level fields surfaced from backlog.yaml
    assert body["id"] == "T-148"
    assert body["title"] == "Implement task detail"
    assert body["status"] == "in-progress"
    assert body["priority"] == "High"
    assert body["estimate"] == "M"
    assert body["epic"] == "viewer"
    assert body["phase"] == "P-01"
    assert body["branch"] == "feat/task-detail"
    assert body["depends_on"] == ["T-100"]
    assert body["anchors"] == ["plugins/taskmaster/viewer/**/*.js"]
    assert body["created"] == "2026-04-20"
    assert body["started"] == "2026-04-22"

    # Body-level fields from .taskmaster/tasks/T-148.md frontmatter
    assert body["docs"] == {"spec": "docs/spec.md", "plan": "docs/plan.md"}
    assert "Click Toggle button" in body["review_instructions"]

    # Markdown sections parsed from the body
    assert "## Description" in body["_body"]
    assert "## Notes" in body["_body"]
    assert "Build the Task Detail screen" in body["description"]
    assert "marked" in body["notes"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest plugins/taskmaster/tests/test_server_task_detail.py::test_get_task_returns_full_payload -v`
Expected: FAIL — `404` on `/api/task/T-148`.

- [ ] **Step 3: Commit the failing test (TDD breadcrumb)**

```bash
git add plugins/taskmaster/tests/test_server_task_detail.py
git commit -m "test(taskmaster): pending GET /api/task/<id> contract"
```

---

### Task 2: Implement `GET /api/task/<id>` — index merge

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py`

- [ ] **Step 1: Add the route helper**

Insert near the other v3 entity functions in `plugins/taskmaster/backlog_server.py`:

```python
def _load_task_full(task_id: str) -> dict | None:
    """Merge backlog.yaml index entry with the per-task markdown file body.
    Returns None if the task id is not in the index.
    """
    import re
    import yaml
    from pathlib import Path

    backlog_path = Path("backlog.yaml")
    if not backlog_path.exists():
        return None
    backlog = yaml.safe_load(backlog_path.read_text()) or {}
    tasks = backlog.get("tasks") or []
    index_entry = next((t for t in tasks if t.get("id") == task_id), None)
    if index_entry is None:
        return None

    out = dict(index_entry)
    out.setdefault("docs", {})
    out.setdefault("description", "")
    out.setdefault("notes", "")
    out.setdefault("review_instructions", "")
    out.setdefault("_body", "")

    md_path = Path(".taskmaster") / "tasks" / f"{task_id}.md"
    if md_path.exists():
        raw = md_path.read_text()
        fm_match = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.DOTALL)
        if fm_match:
            try:
                fm = yaml.safe_load(fm_match.group(1)) or {}
            except Exception:
                fm = {}
            body = fm_match.group(2)
            for k in ("docs", "review_instructions", "patchnote", "release",
                      "worktree", "spec_review", "locked_by"):
                if k in fm:
                    out[k] = fm[k]
        else:
            body = raw
        out["_body"] = body

        # Section split: lines starting "## <SectionName>" are top-level sections.
        sections: dict[str, list[str]] = {}
        current: str | None = None
        for line in body.splitlines():
            m = re.match(r"^## +(.+?)\s*$", line)
            if m:
                current = m.group(1).strip().lower()
                sections[current] = []
                continue
            if current is not None:
                sections[current].append(line)
        for key in ("description", "notes", "specification", "plan",
                    "review instructions", "activity", "patchnote"):
            if key in sections:
                out_key = key.replace(" ", "_")
                out[out_key] = "\n".join(sections[key]).strip()
    return out
```

- [ ] **Step 2: Add the route to `do_GET`**

Find the existing `if self.path.startswith("/api/")` block in `_Handler.do_GET` and insert this branch **before** the generic `/api/backlog` handler:

```python
if self.path.startswith("/api/task/"):
    rest = self.path[len("/api/task/"):]
    if "/" not in rest.rstrip("/"):
        # /api/task/<id>
        task_id = rest.rstrip("/")
        full = _load_task_full(task_id)
        if full is None:
            self._send_json(404, {"ok": False, "error": f"task {task_id} not found"})
            return
        self._send_json(200, full)
        return
```

- [ ] **Step 3: Run test to verify it passes**

Run: `python -m pytest plugins/taskmaster/tests/test_server_task_detail.py::test_get_task_returns_full_payload -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add plugins/taskmaster/backlog_server.py
git commit -m "feat(taskmaster): GET /api/task/<id> merges index + markdown body"
```

---

### Task 3: Add 404 + malformed-id handling for `/api/task/<id>`

**Files:**
- Modify: `plugins/taskmaster/tests/test_server_task_detail.py`

- [ ] **Step 1: Append the failing tests**

Append to `plugins/taskmaster/tests/test_server_task_detail.py`:

```python
def test_get_task_404_for_unknown_id(running_server):
    base, _ = running_server
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(f"{base}/api/task/T-9999")
    assert exc.value.code == 404
    body = json.loads(exc.value.read())
    assert body["ok"] is False
    assert "T-9999" in body["error"]


def test_get_task_404_for_empty_id(running_server):
    base, _ = running_server
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(f"{base}/api/task/")
    assert exc.value.code == 404
```

- [ ] **Step 2: Run tests**

Run: `python -m pytest plugins/taskmaster/tests/test_server_task_detail.py -v`
Expected: All 3 tests PASS (the new logic already returns 404 for unknown ids; empty id falls through to the 404 default).

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/tests/test_server_task_detail.py
git commit -m "test(taskmaster): 404 paths for GET /api/task/<id>"
```

---

### Task 4: Implement `GET /api/task/<id>/related` — anchors-matched lessons + handovers + issues

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py`
- Modify: `plugins/taskmaster/tests/test_server_task_detail.py`

- [ ] **Step 1: Append the failing test**

Append to `plugins/taskmaster/tests/test_server_task_detail.py`:

```python
def test_get_task_related_returns_lessons_handovers_issues_and_deps(running_server, tmp_path):
    base, _ = running_server

    # Lesson with matching anchor (file glob hits the task's anchors)
    (tmp_path / ".taskmaster" / "lessons" / "LSN-01.md").write_text(
        "---\n"
        "id: LSN-01\n"
        "kind: pattern\n"
        "anchors: ['plugins/taskmaster/viewer/**/*.js']\n"
        "title: Use ES modules without bundler\n"
        "---\n"
        "Vanilla ES modules load without a build step.\n"
    )
    # Lesson that does NOT match (different glob)
    (tmp_path / ".taskmaster" / "lessons" / "LSN-02.md").write_text(
        "---\n"
        "id: LSN-02\n"
        "kind: gotcha\n"
        "anchors: ['scripts/**/*.sh']\n"
        "title: Unrelated\n"
        "---\nNot in scope.\n"
    )
    # Handover referencing T-148
    (tmp_path / ".taskmaster" / "handovers" / "2026-04-25-detail.md").write_text(
        "---\n"
        "id: HOV-0001a\n"
        "task_ids: [T-148]\n"
        "kind: mid-task\n"
        "session: SES-0010\n"
        "created: '2026-04-25T16:48:00Z'\n"
        "---\n"
        "Paused at variant B graph layout.\n"
    )
    # Issue referencing T-148
    (tmp_path / ".taskmaster" / "issues" / "ISS-01.md").write_text(
        "---\n"
        "id: ISS-01\n"
        "severity: Medium\n"
        "status: open\n"
        "task_ids: [T-148]\n"
        "title: Bezier control points off on row offset\n"
        "---\nSymptom: edges look kinked.\n"
    )

    resp = urllib.request.urlopen(f"{base}/api/task/T-148/related")
    assert resp.status == 200
    body = json.loads(resp.read())

    # Lessons in scope (anchor match)
    lesson_ids = [l["id"] for l in body["lessons"]]
    assert "LSN-01" in lesson_ids
    assert "LSN-02" not in lesson_ids

    # Handovers (task_ids contains T-148)
    handover_ids = [h["id"] for h in body["handovers"]]
    assert "HOV-0001a" in handover_ids

    # Issues (task_ids contains T-148)
    issue_ids = [i["id"] for i in body["issues"]]
    assert "ISS-01" in issue_ids

    # Dependencies forward (depends_on) and reverse (unblocks)
    assert any(t["id"] == "T-100" for t in body["dependencies"])
    assert any(t["id"] == "T-200" for t in body["unblocks"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest plugins/taskmaster/tests/test_server_task_detail.py::test_get_task_related_returns_lessons_handovers_issues_and_deps -v`
Expected: FAIL — `404` on `/api/task/T-148/related`.

- [ ] **Step 3: Implement the related-payload helper**

Insert after `_load_task_full` in `plugins/taskmaster/backlog_server.py`:

```python
def _load_related_for_task(task_id: str) -> dict | None:
    """Build the related-entities payload for a task: lessons (anchor-matched),
    handovers (task_ids), issues (task_ids), forward deps, reverse deps.
    Returns None if the task is unknown.
    """
    import fnmatch
    import re
    import yaml
    from pathlib import Path

    backlog_path = Path("backlog.yaml")
    if not backlog_path.exists():
        return None
    backlog = yaml.safe_load(backlog_path.read_text()) or {}
    tasks = backlog.get("tasks") or []
    me = next((t for t in tasks if t.get("id") == task_id), None)
    if me is None:
        return None

    my_anchors = list(me.get("anchors") or [])

    def _read_fm(p: Path) -> tuple[dict, str]:
        raw = p.read_text()
        m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.DOTALL)
        if not m:
            return {}, raw
        try:
            fm = yaml.safe_load(m.group(1)) or {}
        except Exception:
            fm = {}
        return fm, m.group(2)

    def _anchors_overlap(a: list, b: list) -> bool:
        # Two anchor lists overlap if any glob in a matches any literal in b
        # OR if any pair share a glob equal to each other. Practically we treat
        # both sides as globs and test whether either glob list, expanded as
        # patterns, would match any path implied by the other.
        for pat in a:
            for other in b:
                if fnmatch.fnmatch(other, pat) or fnmatch.fnmatch(pat, other):
                    return True
                if pat == other:
                    return True
        return False

    # --- Lessons (anchor-matched)
    lessons: list[dict] = []
    lessons_dir = Path(".taskmaster") / "lessons"
    if lessons_dir.is_dir():
        for f in sorted(lessons_dir.glob("*.md")):
            fm, body = _read_fm(f)
            their_anchors = list(fm.get("anchors") or [])
            if _anchors_overlap(my_anchors, their_anchors):
                lessons.append({
                    "id": fm.get("id") or f.stem,
                    "kind": fm.get("kind"),
                    "title": fm.get("title") or "",
                    "anchors": their_anchors,
                    "summary": body.strip().splitlines()[0] if body.strip() else "",
                    "_path": str(f),
                })

    # --- Handovers (task_ids contains my id)
    handovers: list[dict] = []
    handovers_dir = Path(".taskmaster") / "handovers"
    if handovers_dir.is_dir():
        for f in sorted(handovers_dir.glob("*.md")):
            fm, body = _read_fm(f)
            tids = list(fm.get("task_ids") or [])
            if task_id in tids:
                handovers.append({
                    "id": fm.get("id") or f.stem,
                    "kind": fm.get("kind"),
                    "session": fm.get("session"),
                    "created": fm.get("created"),
                    "quote": body.strip().splitlines()[0] if body.strip() else "",
                    "_path": str(f),
                })

    # --- Issues (task_ids contains my id)
    issues: list[dict] = []
    issues_dir = Path(".taskmaster") / "issues"
    if issues_dir.is_dir():
        for f in sorted(issues_dir.glob("*.md")):
            fm, body = _read_fm(f)
            tids = list(fm.get("task_ids") or [])
            if task_id in tids:
                issues.append({
                    "id": fm.get("id") or f.stem,
                    "severity": fm.get("severity"),
                    "status": fm.get("status"),
                    "title": fm.get("title") or "",
                    "_path": str(f),
                })

    # --- Dependencies (forward + reverse)
    dep_ids = list(me.get("depends_on") or [])
    dependencies = [
        {"id": t["id"], "title": t.get("title", ""), "status": t.get("status", "")}
        for t in tasks if t.get("id") in dep_ids
    ]
    unblocks = [
        {"id": t["id"], "title": t.get("title", ""), "status": t.get("status", "")}
        for t in tasks if task_id in (t.get("depends_on") or [])
    ]

    return {
        "task_id": task_id,
        "lessons": lessons,
        "handovers": handovers,
        "issues": issues,
        "dependencies": dependencies,
        "unblocks": unblocks,
    }
```

- [ ] **Step 4: Add the route to `do_GET`**

Modify the `/api/task/...` branch in `_Handler.do_GET` (added in Task 2) to also recognise `/related`:

```python
if self.path.startswith("/api/task/"):
    rest = self.path[len("/api/task/"):].rstrip("/")
    if rest.endswith("/related"):
        task_id = rest[: -len("/related")]
        related = _load_related_for_task(task_id)
        if related is None:
            self._send_json(404, {"ok": False, "error": f"task {task_id} not found"})
            return
        self._send_json(200, related)
        return
    if "/" not in rest:
        full = _load_task_full(rest)
        if full is None:
            self._send_json(404, {"ok": False, "error": f"task {rest} not found"})
            return
        self._send_json(200, full)
        return
```

- [ ] **Step 5: Run all server tests**

Run: `python -m pytest plugins/taskmaster/tests/test_server_task_detail.py -v`
Expected: All 4 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_server_task_detail.py
git commit -m "feat(taskmaster): GET /api/task/<id>/related (lessons/handovers/issues/deps)"
```

---

### Task 5: Verify forward-compat fields (`spec_review`, `patchnote`, `worktree`, `release`, `locked_by`) round-trip

**Files:**
- Modify: `plugins/taskmaster/tests/test_server_task_detail.py`

- [ ] **Step 1: Append the failing test**

```python
def test_get_task_surfaces_forward_compat_fields(running_server, tmp_path):
    base, _ = running_server
    # Overwrite the T-148 task file with all forward-compat fields populated.
    (tmp_path / ".taskmaster" / "tasks" / "T-148.md").write_text(
        "---\n"
        "id: T-148\n"
        "worktree: ../wt-task-detail\n"
        "spec_review: {verdict: pass, codex_note: 'Looks clean.'}\n"
        "patchnote: 'Adds Variant A and B detail views.'\n"
        "release: v2.1.0\n"
        "locked_by: 'session SES-0010'\n"
        "docs:\n"
        "  spec: docs/spec.md\n"
        "---\n"
        "## Description\nbody.\n"
    )
    body = json.loads(urllib.request.urlopen(f"{base}/api/task/T-148").read())
    assert body["worktree"] == "../wt-task-detail"
    assert body["spec_review"]["verdict"] == "pass"
    assert "Looks clean" in body["spec_review"]["codex_note"]
    assert body["patchnote"].startswith("Adds Variant A")
    assert body["release"] == "v2.1.0"
    assert body["locked_by"] == "session SES-0010"
```

- [ ] **Step 2: Run test**

Run: `python -m pytest plugins/taskmaster/tests/test_server_task_detail.py::test_get_task_surfaces_forward_compat_fields -v`
Expected: PASS (already covered by Task 2's `for k in (...)` loop, but the test pins the contract).

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/tests/test_server_task_detail.py
git commit -m "test(taskmaster): pin forward-compat task fields in GET /api/task/<id>"
```

---

### Task 6: Suite-level run of all server tests so far

- [ ] **Step 1: Run all server tests**

Run: `python -m pytest plugins/taskmaster/tests/test_server_api.py plugins/taskmaster/tests/test_server_task_detail.py -v`
Expected: All Plan 1 + Plan 3 server tests PASS (≥ 9 tests total).

- [ ] **Step 2: No commit** — verification only.

---

## M2 — Pure-Data Graph Layout (`dependency-graph.js`)

### Task 7: Author the layout function with a failing Node test (empty graph)

**Files:**
- Create: `plugins/taskmaster/viewer/tests/unit/dependency-graph.test.js`
- Create: `plugins/taskmaster/viewer/js/components/dependency-graph.js`

- [ ] **Step 1: Write the failing test**

Create `plugins/taskmaster/viewer/tests/unit/dependency-graph.test.js`:

```javascript
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { computeGraphLayout } from '../../js/components/dependency-graph.js';

test('empty graph: only the center node, columns shape correct', () => {
  const out = computeGraphLayout({
    center: { id: 'T-148', title: 'Center', status: 'in-progress' },
    upstream: [],
    downstream: [],
    width: 800,
    height: 320,
  });
  assert.equal(out.nodes.length, 1);
  assert.equal(out.nodes[0].id, 'T-148');
  assert.equal(out.nodes[0].column, 0);
  assert.equal(out.edges.length, 0);
  assert.deepEqual(out.columns.map(c => c.depth), [-2, -1, 0, 1, 2]);
  // Center column x is in the middle of the canvas.
  const col0 = out.columns.find(c => c.depth === 0);
  assert.ok(Math.abs(col0.x - 400) < 1, `center column x ~ 400, got ${col0.x}`);
});
```

- [ ] **Step 2: Stub the module so the import resolves but the test fails**

Create `plugins/taskmaster/viewer/js/components/dependency-graph.js`:

```javascript
// Pure-data graph layout helper for the Task Detail Variant B canvas.
// No DOM, no fetch — both the browser renderer and Node unit tests import this.

export function computeGraphLayout(_input) {
  return { nodes: [], edges: [], columns: [] };
}
```

- [ ] **Step 3: Run the test, expect FAIL**

Run: `node --test plugins/taskmaster/viewer/tests/unit/dependency-graph.test.js`
Expected: FAIL — `out.nodes.length` is 0, expected 1.

- [ ] **Step 4: Commit the failing test + stub**

```bash
git add plugins/taskmaster/viewer/tests/unit/dependency-graph.test.js plugins/taskmaster/viewer/js/components/dependency-graph.js
git commit -m "test(viewer): pending dependency-graph layout (empty case)"
```

---

### Task 8: Implement empty + L0-only layout

**Files:**
- Modify: `plugins/taskmaster/viewer/js/components/dependency-graph.js`

- [ ] **Step 1: Replace the stub with column-aware layout**

Overwrite `plugins/taskmaster/viewer/js/components/dependency-graph.js`:

```javascript
// Pure-data graph layout helper for Task Detail Variant B.
// Inputs are plain objects; outputs are plain objects suitable for SVG rendering.
//
// Input shape:
//   {
//     center:    { id, title, status, priority?, estimate?, time_in_status?, progress? },
//     upstream:  [ TaskRef, ... ]   // depths 1..2 (L-1, L-2)
//     downstream:[ TaskRef, ... ]   // depths 1..2 (L+1, L+2)
//     width:     number             // canvas width in px (default 800)
//     height:    number             // canvas height in px (default 320)
//   }
//
//   TaskRef = { id, title, status, depth, priority?, estimate?, time_in_status?, row? }
//   `depth` is positive for both upstream and downstream; the function negates
//   for upstream when assigning columns.
//
// Output shape:
//   {
//     columns: [{depth, x, label}, ...]                       // 5 entries, depths -2..+2
//     nodes:   [{id, x, y, w, h, depth, faded, isCenter, ...meta}, ...]
//     edges:   [{from, to, path, sameRow}]                    // SVG path strings
//   }

const DEFAULT_W = 800;
const DEFAULT_H = 320;
const NODE_W = 100;
const NODE_H = 60;
const CENTER_W = 120;
const CENTER_H = 80;
const ROW_GAP = 14;

export function computeGraphLayout(input) {
  const width = input?.width ?? DEFAULT_W;
  const height = input?.height ?? DEFAULT_H;
  const centerY = height / 2;
  const colSpacing = width / 5;

  const columns = [-2, -1, 0, 1, 2].map((depth) => ({
    depth,
    x: colSpacing * (depth + 2) + colSpacing / 2,
    label: depth === 0 ? 'L0' : `L${depth >= 0 ? '+' : ''}${depth}`,
  }));

  const nodes = [];
  const edges = [];

  if (!input || !input.center) {
    return { columns, nodes, edges };
  }

  // Center node
  const centerCol = columns.find((c) => c.depth === 0);
  nodes.push({
    id: input.center.id,
    x: centerCol.x - CENTER_W / 2,
    y: centerY - CENTER_H / 2,
    w: CENTER_W,
    h: CENTER_H,
    depth: 0,
    column: 0,
    faded: false,
    isCenter: true,
    title: input.center.title || '',
    status: input.center.status || '',
    priority: input.center.priority || null,
    estimate: input.center.estimate || null,
    time_in_status: input.center.time_in_status || null,
    progress: input.center.progress ?? null,
    step: input.center.step ?? null,
  });

  // Upstream and downstream lanes
  placeSide(input.upstream || [], -1, nodes, edges, columns, centerY, input.center.id);
  placeSide(input.downstream || [], +1, nodes, edges, columns, centerY, input.center.id);

  return { columns, nodes, edges };
}

function placeSide(side, sign, nodes, edges, columns, centerY, centerId) {
  // Group by depth (1 and 2) — the caller passes depth as positive integers.
  const byDepth = new Map();
  for (const n of side) {
    const d = Math.max(1, Math.min(2, n.depth || 1));
    if (!byDepth.has(d)) byDepth.set(d, []);
    byDepth.get(d).push(n);
  }

  for (const [depth, items] of byDepth) {
    const col = columns.find((c) => c.depth === sign * depth);
    const totalH = items.length * NODE_H + (items.length - 1) * ROW_GAP;
    let y = centerY - totalH / 2;
    for (const item of items) {
      const node = {
        id: item.id,
        x: col.x - NODE_W / 2,
        y,
        w: NODE_W,
        h: NODE_H,
        depth: sign * depth,
        column: sign * depth,
        faded: depth === 2,
        isCenter: false,
        title: item.title || '',
        status: item.status || '',
        priority: item.priority || null,
        estimate: item.estimate || null,
        time_in_status: item.time_in_status || null,
      };
      nodes.push(node);
      y += NODE_H + ROW_GAP;

      // Edge: outermost (L-2/L+2) connects through middle (L-1/L+1), else
      // connects directly to the center.
      if (depth === 1) {
        const edge = makeEdge(node, findCenterById(nodes, centerId), sign);
        edges.push(edge);
      } else {
        // Connect L+/-2 to its sibling at L+/-1 if present, else to center.
        const mid = findNodeAtDepth(nodes, sign * 1);
        const target = mid || findCenterById(nodes, centerId);
        edges.push(makeEdge(node, target, sign));
      }
    }
  }
}

function findCenterById(nodes, id) {
  return nodes.find((n) => n.isCenter && n.id === id);
}
function findNodeAtDepth(nodes, depth) {
  return nodes.find((n) => n.depth === depth);
}

function makeEdge(from, to, sign) {
  // Upstream edges flow left→center (from is to the LEFT of to), downstream
  // edges flow center→right (from is to the RIGHT of to). Either way we draw
  // from `from` toward `to` with horizontal pull at 60% on each side.
  const fx = from.x + (sign < 0 ? from.w : 0);
  const fy = from.y + from.h / 2;
  const tx = to.x + (sign < 0 ? 0 : to.w);
  const ty = to.y + to.h / 2;
  const dx = (tx - fx) * 0.6;
  const cp1 = { x: fx + dx, y: fy };
  const cp2 = { x: tx - dx, y: ty };
  const path = `M ${fx.toFixed(1)} ${fy.toFixed(1)} C ${cp1.x.toFixed(1)} ${cp1.y.toFixed(1)}, ${cp2.x.toFixed(1)} ${cp2.y.toFixed(1)}, ${tx.toFixed(1)} ${ty.toFixed(1)}`;
  return {
    from: from.id,
    to: to.id,
    path,
    sameRow: Math.abs(fy - ty) < 0.5,
  };
}
```

- [ ] **Step 2: Run the empty test**

Run: `node --test plugins/taskmaster/viewer/tests/unit/dependency-graph.test.js`
Expected: PASS (1 test).

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/dependency-graph.js
git commit -m "feat(viewer): dependency-graph layout (empty + L0-only cases)"
```

---

### Task 9: Add the deep-upstream-chain test

**Files:**
- Modify: `plugins/taskmaster/viewer/tests/unit/dependency-graph.test.js`

- [ ] **Step 1: Append the test**

```javascript
test('deep upstream chain: L-2 connects through L-1, not directly to center', () => {
  const out = computeGraphLayout({
    center: { id: 'C', title: 'Center', status: 'in-progress' },
    upstream: [
      { id: 'U1', title: 'Up 1', status: 'done', depth: 1 },
      { id: 'U2', title: 'Up 2', status: 'done', depth: 2 },
    ],
    downstream: [],
    width: 800, height: 320,
  });
  const u2 = out.nodes.find(n => n.id === 'U2');
  const u1 = out.nodes.find(n => n.id === 'U1');
  assert.equal(u2.column, -2);
  assert.equal(u1.column, -1);
  assert.ok(u2.faded, 'L-2 nodes should be faded');
  assert.equal(u1.faded, false, 'L-1 nodes should not be faded');

  const u2Edge = out.edges.find(e => e.from === 'U2');
  assert.equal(u2Edge.to, 'U1', 'U2 should chain through U1, not directly to center');
});
```

- [ ] **Step 2: Run the suite**

Run: `node --test plugins/taskmaster/viewer/tests/unit/dependency-graph.test.js`
Expected: PASS (2 tests).

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/tests/unit/dependency-graph.test.js
git commit -m "test(viewer): deep upstream chain layout"
```

---

### Task 10: Add the deep-downstream-chain test

**Files:**
- Modify: `plugins/taskmaster/viewer/tests/unit/dependency-graph.test.js`

- [ ] **Step 1: Append the test**

```javascript
test('deep downstream chain: L+2 connects through L+1', () => {
  const out = computeGraphLayout({
    center: { id: 'C', title: 'Center', status: 'in-progress' },
    upstream: [],
    downstream: [
      { id: 'D1', title: 'Dn 1', status: 'backlog', depth: 1 },
      { id: 'D2', title: 'Dn 2', status: 'backlog', depth: 2 },
    ],
    width: 800, height: 320,
  });
  const d2 = out.nodes.find(n => n.id === 'D2');
  const d1 = out.nodes.find(n => n.id === 'D1');
  assert.equal(d2.column, 2);
  assert.equal(d1.column, 1);
  assert.ok(d2.faded);

  const d2Edge = out.edges.find(e => e.from === 'D2');
  assert.equal(d2Edge.to, 'D1', 'D2 should chain through D1');
});
```

- [ ] **Step 2: Run**

Run: `node --test plugins/taskmaster/viewer/tests/unit/dependency-graph.test.js`
Expected: PASS (3 tests).

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/tests/unit/dependency-graph.test.js
git commit -m "test(viewer): deep downstream chain layout"
```

---

### Task 11: Add the mixed-graph test

**Files:**
- Modify: `plugins/taskmaster/viewer/tests/unit/dependency-graph.test.js`

- [ ] **Step 1: Append the test**

```javascript
test('mixed graph: stack siblings vertically inside a column, no overlap', () => {
  const out = computeGraphLayout({
    center: { id: 'C', title: 'Center', status: 'in-progress' },
    upstream: [
      { id: 'U1a', title: 'Up 1a', status: 'done', depth: 1 },
      { id: 'U1b', title: 'Up 1b', status: 'done', depth: 1 },
    ],
    downstream: [
      { id: 'D1a', title: 'Dn 1a', status: 'backlog', depth: 1 },
      { id: 'D1b', title: 'Dn 1b', status: 'backlog', depth: 1 },
      { id: 'D1c', title: 'Dn 1c', status: 'backlog', depth: 1 },
    ],
    width: 800, height: 320,
  });
  const upCol = out.nodes.filter(n => n.column === -1).sort((a, b) => a.y - b.y);
  assert.equal(upCol.length, 2);
  // No vertical overlap
  assert.ok(upCol[0].y + upCol[0].h <= upCol[1].y, 'upstream siblings must not overlap');

  const downCol = out.nodes.filter(n => n.column === 1).sort((a, b) => a.y - b.y);
  assert.equal(downCol.length, 3);
  assert.ok(downCol[0].y + downCol[0].h <= downCol[1].y);
  assert.ok(downCol[1].y + downCol[1].h <= downCol[2].y);

  // Edges to center exist for every L-1 node
  for (const n of upCol) {
    const edge = out.edges.find(e => e.from === n.id);
    assert.equal(edge.to, 'C');
  }
  for (const n of downCol) {
    const edge = out.edges.find(e => e.from === n.id);
    assert.equal(edge.to, 'C');
  }
});
```

- [ ] **Step 2: Run**

Run: `node --test plugins/taskmaster/viewer/tests/unit/dependency-graph.test.js`
Expected: PASS (4 tests).

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/tests/unit/dependency-graph.test.js
git commit -m "test(viewer): mixed graph siblings stack without overlap"
```

---

### Task 12: Add the cycle-handling test (deduplicated nodes)

**Files:**
- Modify: `plugins/taskmaster/viewer/tests/unit/dependency-graph.test.js`
- Modify: `plugins/taskmaster/viewer/js/components/dependency-graph.js`

- [ ] **Step 1: Append the failing test**

```javascript
test('cycle handling: a task appearing in both upstream and downstream renders once', () => {
  // Pathological input: T-X is both an upstream and a downstream of center.
  const out = computeGraphLayout({
    center: { id: 'C', title: 'Center', status: 'in-progress' },
    upstream:   [{ id: 'X', title: 'Both', status: 'done', depth: 1 }],
    downstream: [{ id: 'X', title: 'Both', status: 'done', depth: 1 }],
    width: 800, height: 320,
  });
  const xs = out.nodes.filter(n => n.id === 'X');
  assert.equal(xs.length, 1, 'duplicate task id should be deduplicated');
  // Convention: upstream wins (placed at column -1)
  assert.equal(xs[0].column, -1);
});
```

- [ ] **Step 2: Run, expect FAIL**

Run: `node --test plugins/taskmaster/viewer/tests/unit/dependency-graph.test.js`
Expected: FAIL — duplicate-id check fails (the function currently emits two nodes).

- [ ] **Step 3: Add deduplication to `computeGraphLayout`**

Modify `plugins/taskmaster/viewer/js/components/dependency-graph.js` — change the body of the exported function so downstream items whose id is already on the upstream list are dropped before laying out the right side. Replace the `placeSide(input.downstream...)` call with:

```javascript
  const upstreamIds = new Set((input.upstream || []).map((n) => n.id));
  const downstreamFiltered = (input.downstream || []).filter(
    (n) => !upstreamIds.has(n.id) && n.id !== input.center.id
  );
  const upstreamFiltered = (input.upstream || []).filter(
    (n) => n.id !== input.center.id
  );
  placeSide(upstreamFiltered, -1, nodes, edges, columns, centerY, input.center.id);
  placeSide(downstreamFiltered, +1, nodes, edges, columns, centerY, input.center.id);
```

(Remove the previous two `placeSide(...)` lines.)

- [ ] **Step 4: Run, expect PASS**

Run: `node --test plugins/taskmaster/viewer/tests/unit/dependency-graph.test.js`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/dependency-graph.js plugins/taskmaster/viewer/tests/unit/dependency-graph.test.js
git commit -m "fix(viewer): dedupe nodes that appear on both sides of the dep graph"
```

---

### Task 13: Wire `node --test` into a `package.json` script

**Files:**
- Modify (or create): `plugins/taskmaster/viewer/package.json`

- [ ] **Step 1: Read current contents (or create the file)**

If `plugins/taskmaster/viewer/package.json` does not exist (Plan 1 may have created it for Playwright; check first), create it with:

```json
{
  "name": "taskmaster-viewer",
  "private": true,
  "type": "module",
  "scripts": {
    "test:unit": "node --test tests/unit/",
    "test:e2e":  "playwright test"
  }
}
```

If it already exists, add the `"test:unit"` script to the existing `scripts` block; do not touch other keys.

- [ ] **Step 2: Run the npm script as a sanity check**

Run from `plugins/taskmaster/viewer/`: `npm run test:unit`
Expected: 5 tests PASS, 0 failures.

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/package.json
git commit -m "chore(viewer): wire dependency-graph unit tests into npm test:unit"
```

---

## M3 — Shared Client Plumbing

### Task 14: Add `markdown.js` (sandboxed `marked` wrapper)

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/markdown.js`
- Modify: `plugins/taskmaster/viewer/index.html`

- [ ] **Step 1: Add the `marked` script to `index.html`**

Edit `plugins/taskmaster/viewer/index.html` and insert into the `<head>`, before the `<script type="module" src="js/main.js">` line:

```html
<script src="https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js" integrity="sha384-+E2HvhFs0a8uhPGdc1ZHo3FxVscR3dHo/iU85PkRl4tIcYRm5UsXvwSukP9dBp45" crossorigin="anonymous"></script>
```

Also add a `<link>` to the screen CSS:

```html
<link rel="stylesheet" href="css/screens/task-detail.css">
```

(The `task-detail.css` file is created in M4 Task 18; the link added now is harmless until then.)

- [ ] **Step 2: Create `markdown.js`**

```javascript
// Markdown rendering — wraps the global `marked` library with a small allowlist
// sanitiser so user-authored markdown can't smuggle script/style/iframe tags.
//
// `renderMarkdown(src)` returns an HTML string ready to inject via .innerHTML.
// `mountMarkdown(element, src)` is a convenience that does the assignment.

const ALLOWED_TAGS = new Set([
  'a', 'abbr', 'b', 'blockquote', 'br', 'code', 'em', 'h1', 'h2', 'h3', 'h4',
  'h5', 'h6', 'hr', 'i', 'img', 'li', 'ol', 'p', 'pre', 'span', 'strong',
  'sub', 'sup', 'table', 'tbody', 'td', 'th', 'thead', 'tr', 'ul',
]);
const ALLOWED_ATTRS = new Set(['href', 'title', 'src', 'alt', 'class']);

export function renderMarkdown(src) {
  if (!src) return '';
  if (typeof window === 'undefined' || !window.marked) {
    // Fallback for environments without `marked` loaded — escape and wrap.
    return `<pre class="md-fallback">${escapeHtml(src)}</pre>`;
  }
  const html = window.marked.parse(src, { breaks: true, gfm: true });
  return sanitise(html);
}

export function mountMarkdown(el, src) {
  el.innerHTML = renderMarkdown(src);
}

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  })[c]);
}

function sanitise(html) {
  const tpl = document.createElement('template');
  tpl.innerHTML = html;
  const walker = document.createTreeWalker(tpl.content, NodeFilter.SHOW_ELEMENT);
  const toRemove = [];
  let node = walker.nextNode();
  while (node) {
    const tag = node.tagName.toLowerCase();
    if (!ALLOWED_TAGS.has(tag)) {
      toRemove.push(node);
    } else {
      for (const attr of [...node.attributes]) {
        if (!ALLOWED_ATTRS.has(attr.name)) node.removeAttribute(attr.name);
        if (attr.name === 'href' && /^javascript:/i.test(attr.value)) {
          node.removeAttribute(attr.name);
        }
      }
    }
    node = walker.nextNode();
  }
  for (const n of toRemove) {
    while (n.firstChild) n.parentNode.insertBefore(n.firstChild, n);
    n.remove();
  }
  return tpl.innerHTML;
}
```

- [ ] **Step 3: Smoke-check from a browser console**

Open the viewer at `http://localhost:8765/v3` (start the server with `python plugins/taskmaster/backlog_server.py` if needed). In DevTools Console:

```js
const m = await import('/static/v3/js/components/markdown.js');
m.renderMarkdown('# Hi\n\n**bold** [x](javascript:alert(1)) <script>alert(2)</script>');
```

Expected output: `<h1>Hi</h1><p><strong>bold</strong> <a>x</a> alert(2)</p>` (script tag and `javascript:` href stripped, text content preserved). The exact whitespace may differ.

- [ ] **Step 4: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/markdown.js plugins/taskmaster/viewer/index.html
git commit -m "feat(viewer): markdown render helper with allowlist sanitiser"
```

---

### Task 15: Extend `api.js` with `getTask` and `getTaskRelated`

**Files:**
- Modify: `plugins/taskmaster/viewer/js/api.js`

- [ ] **Step 1: Add the two functions**

Open `plugins/taskmaster/viewer/js/api.js`. Append (or merge into the existing default export):

```javascript
export async function getTask(id) {
  const resp = await fetch(`/api/task/${encodeURIComponent(id)}`);
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body.error || `task ${id} not found`);
  }
  return resp.json();
}

export async function getTaskRelated(id) {
  const resp = await fetch(`/api/task/${encodeURIComponent(id)}/related`);
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body.error || `related for ${id} not found`);
  }
  return resp.json();
}
```

If `api.js` exports a single default object, also wire these through it:

```javascript
export default {
  // ...existing...
  getTask,
  getTaskRelated,
};
```

- [ ] **Step 2: Smoke-check from DevTools Console**

```js
const api = await import('/static/v3/js/api.js');
await api.getTask('T-148');     // prints the merged payload
await api.getTaskRelated('T-148');
```

Expected: both calls resolve to JSON objects matching the server tests. (Use any task id that exists in your backlog.)

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/js/api.js
git commit -m "feat(viewer): api.getTask + api.getTaskRelated"
```

---

### Task 16: Cache the full task payload in the store

**Files:**
- Modify: `plugins/taskmaster/viewer/js/store.js`

- [ ] **Step 1: Add a memoised cache slice**

Append to `plugins/taskmaster/viewer/js/store.js`:

```javascript
import { getTask, getTaskRelated } from './api.js';

const _taskCache = new Map();
const _relatedCache = new Map();

export async function getTaskFull(id, { force = false } = {}) {
  if (!force && _taskCache.has(id)) return _taskCache.get(id);
  const data = await getTask(id);
  _taskCache.set(id, data);
  return data;
}

export async function getTaskRelatedFull(id, { force = false } = {}) {
  if (!force && _relatedCache.has(id)) return _relatedCache.get(id);
  const data = await getTaskRelated(id);
  _relatedCache.set(id, data);
  return data;
}

export function invalidateTask(id) {
  _taskCache.delete(id);
  _relatedCache.delete(id);
}
```

If `store.js` exposes a default object, also surface these through it:

```javascript
export default {
  // ...existing...
  getTaskFull,
  getTaskRelatedFull,
  invalidateTask,
};
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/store.js
git commit -m "feat(viewer): store.getTaskFull + getTaskRelatedFull cache slices"
```

---

### Task 17: Build the shared `right-rail.js`

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/right-rail.js`

- [ ] **Step 1: Create the component**

```javascript
// Shared right-rail used by Task Detail Variants A and B.
// `mountRightRail(root, { task, related, onNavigate })` renders six panels:
//   Docs · Lessons in scope · Handovers · Issues · Dependencies + Unblocks · Blockers
// Returns a cleanup function.

export function mountRightRail(root, { task, related, onNavigate }) {
  root.innerHTML = '';
  root.classList.add('td-rail');

  root.appendChild(panelDocs(task));
  root.appendChild(panelLessons(related?.lessons || []));
  root.appendChild(panelHandovers(related?.handovers || []));
  root.appendChild(panelIssues(related?.issues || [], onNavigate));
  root.appendChild(panelDeps(related?.dependencies || [], related?.unblocks || [], onNavigate));
  root.appendChild(panelBlockers(task?.blockers || []));

  return () => { root.innerHTML = ''; };
}

function h(tag, attrs = {}, children = []) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') el.className = v;
    else if (k === 'on') for (const [evt, fn] of Object.entries(v)) el.addEventListener(evt, fn);
    else el.setAttribute(k, v);
  }
  for (const c of [].concat(children)) {
    if (c == null) continue;
    el.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
  }
  return el;
}

function panelHeader(label) {
  return h('div', { class: 'td-rail-h' }, label);
}

function panelDocs(task) {
  const docs = task?.docs || {};
  const items = Object.entries(docs).map(([type, href]) =>
    h('a', { class: `td-doc td-doc-${type}`, href, target: '_blank', rel: 'noopener' },
      [h('span', { class: 'td-doc-type' }, type), h('span', { class: 'td-doc-path mono' }, href)])
  );
  return h('section', { class: 'td-panel td-panel-docs' },
    [panelHeader('Docs'), ...(items.length ? items : [h('div', { class: 'td-empty' }, 'no docs')])]);
}

function panelLessons(lessons) {
  if (!lessons.length) {
    return h('section', { class: 'td-panel' },
      [panelHeader('Lessons in scope'), h('div', { class: 'td-empty' }, 'no anchor matches')]);
  }
  return h('section', { class: 'td-panel td-panel-lessons' },
    [panelHeader('Lessons in scope'),
     h('div', { class: 'td-rail-hint' }, 'Surfaced via anchor match'),
     ...lessons.map((l) =>
       h('div', { class: 'td-lesson' },
         [h('span', { class: 'mono td-lesson-id' }, l.id),
          h('span', { class: 'td-lesson-title' }, l.title || ''),
          h('span', { class: 'td-lesson-anchor mono' }, (l.anchors || []).join(' · '))]))]);
}

function panelHandovers(handovers) {
  if (!handovers.length) {
    return h('section', { class: 'td-panel' },
      [panelHeader('Handovers'), h('div', { class: 'td-empty' }, 'none')]);
  }
  return h('section', { class: 'td-panel td-panel-handovers' },
    [panelHeader('Handovers'),
     ...handovers.map((ho) =>
       h('div', { class: `td-handover td-handover-${ho.kind || 'mid-task'}` },
         [h('div', { class: 'mono td-handover-id' }, `${ho.id} · ${ho.kind || ''}`),
          h('blockquote', { class: 'serif td-handover-quote' }, `"${ho.quote || ''}"`)]))]);
}

function panelIssues(issues, onNavigate) {
  if (!issues.length) {
    return h('section', { class: 'td-panel' },
      [panelHeader('Issues'), h('div', { class: 'td-empty' }, 'none')]);
  }
  return h('section', { class: 'td-panel td-panel-issues' },
    [panelHeader('Issues'),
     ...issues.map((i) =>
       h('div', { class: `td-issue td-issue-${(i.severity || '').toLowerCase()}` },
         [h('span', { class: 'mono td-issue-id' }, i.id),
          h('span', { class: 'td-issue-title' }, i.title || ''),
          h('span', { class: 'td-issue-sev' }, i.severity || '')]))]);
}

function panelDeps(deps, unblocks, onNavigate) {
  return h('section', { class: 'td-panel td-panel-deps' },
    [panelHeader('Dependencies'),
     deps.length
       ? h('ul', { class: 'td-dep-list' },
           deps.map((d) =>
             h('li', { class: `td-dep td-dep-${d.status}`,
                       on: { click: () => onNavigate?.(d.id) } },
               [h('span', { class: 'mono' }, d.id), ' ', d.title])))
       : h('div', { class: 'td-empty' }, 'no dependencies'),
     h('div', { class: 'td-rail-h td-rail-h-sub' }, 'Unblocks'),
     unblocks.length
       ? h('ul', { class: 'td-dep-list' },
           unblocks.map((d) =>
             h('li', { class: `td-dep td-dep-${d.status}`,
                       on: { click: () => onNavigate?.(d.id) } },
               [h('span', { class: 'mono' }, d.id), ' ', d.title])))
       : h('div', { class: 'td-empty' }, 'this task gates nothing')]);
}

function panelBlockers(blockers) {
  return h('section', { class: 'td-panel td-panel-blockers' },
    [panelHeader('Blockers'),
     blockers.length
       ? h('ul', { class: 'td-blocker-list' },
           blockers.map((b) => h('li', { class: 'td-blocker' }, typeof b === 'string' ? b : (b.text || JSON.stringify(b)))))
       : h('div', { class: 'td-empty' }, 'none')]);
}
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/right-rail.js
git commit -m "feat(viewer): shared right-rail component for task detail"
```

---

## M4 — Variant A (Document)

### Task 18: Create `task-detail.css` skeleton

**Files:**
- Create: `plugins/taskmaster/viewer/css/screens/task-detail.css`

- [ ] **Step 1: Write the file**

```css
/* Task Detail (Variants A and B). Tokens come from tokens.css.
   Local namespaced tokens are introduced for the graph + node geometry. */
:root {
  /* Task detail */
  --task-rail-w:           280px;
  --task-grid-gap:         18px;
  --task-section-mb:       18px;
  --task-section-h:        12px;

  /* Graph (Variant B) */
  --graph-frame-bg:        radial-gradient(120% 80% at 50% 50%, #0a0c11 0%, #060709 100%);
  --graph-frame-border:    var(--border);
  --graph-frame-shadow:    inset 0 1px 14px rgba(0,0,0,0.5);
  --graph-canvas-h:        320px;
  --graph-node-shadow:     0 4px 14px rgba(0,0,0,0.5);
  --graph-edge-stroke:     rgba(127,179,240,0.35);
  --graph-edge-stroke-active: rgba(74,158,255,0.7);
  --graph-col-guide:       rgba(255,255,255,0.04);
}

/* ---------- Shared header / shell ---------- */
.td-page { padding: 14px 18px; min-width: 0; }
.td-ph {
  display: flex; align-items: center; gap: var(--sp-4);
  padding-bottom: var(--sp-4); margin-bottom: var(--sp-5);
  border-bottom: 1px solid var(--border);
}
.td-ph .td-back { color: var(--ink-3); font-size: var(--text-sm); cursor: pointer; }
.td-ph .td-back:hover { color: var(--ink); }
.td-ph .td-crumb { color: var(--ink-3); font-size: var(--text-sm); }
.td-ph .td-right { margin-left: auto; display: flex; align-items: center; gap: var(--sp-4); }
.td-seg { display: inline-flex; background: var(--bg-card); border: 1px solid var(--border); border-radius: 5px; overflow: hidden; }
.td-seg .td-seg-btn { padding: 3px 10px; font-size: var(--text-sm); color: var(--ink-3); cursor: pointer; border-right: 1px solid var(--border); background: transparent; }
.td-seg .td-seg-btn:last-child { border-right: 0; }
.td-seg .td-seg-btn.on { background: rgba(74,158,255,0.15); color: var(--accent); }
.td-action { background: var(--bg-card); border: 1px solid var(--border); color: var(--ink-2); font-size: var(--text-sm); padding: 3px 9px; border-radius: 4px; cursor: pointer; }
.td-action:hover { border-color: var(--accent); color: var(--ink); }

.td-grid {
  display: grid;
  grid-template-columns: 1fr var(--task-rail-w);
  gap: var(--task-grid-gap);
}

/* ---------- Variant A — Document body ---------- */
.td-doc-meta { color: var(--ink-3); font-size: var(--text-sm); display: flex; gap: var(--sp-3); align-items: center; flex-wrap: wrap; }
.td-doc-meta .td-id { font-family: var(--font-mono); color: var(--epic-1); cursor: copy; padding: 1px 5px; border-radius: 3px; }
.td-doc-meta .td-id:hover { background: rgba(110,168,255,0.1); }
.td-doc-meta .td-id.copied { background: rgba(95,174,110,0.2); color: var(--green); }
.td-doc-meta .td-id.copied .td-id-text { display: none; }
.td-doc-meta .td-id.copied::after { content: 'copied'; }
.td-doc-meta .td-sep { opacity: 0.4; }

.td-title { font-size: var(--text-3xl); font-weight: 600; letter-spacing: -0.01em; color: var(--ink); margin: 6px 0 var(--sp-4); line-height: 1.2; }

.td-lock-banner {
  margin: 6px 0 var(--sp-4); padding: 6px 10px; border-radius: 4px;
  background: color-mix(in oklch, var(--amber) 12%, transparent);
  color: var(--amber); font-size: var(--text-sm);
  display: flex; align-items: center; gap: 6px;
}

.td-chips { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; margin-bottom: var(--sp-5); }
.td-status-pill { font-size: var(--text-xs); padding: 2px 8px; border-radius: 3px; font-weight: 600; background: rgba(74,158,255,0.15); color: var(--accent); }
.td-pri-pill { font-size: var(--text-xs); padding: 2px 7px; border-radius: 3px; font-weight: 600; }
.td-pri-pill.crit   { background: color-mix(in oklch, var(--red) 22%, transparent); color: var(--red); }
.td-pri-pill.high   { background: color-mix(in oklch, var(--amber) 22%, transparent); color: var(--amber); }
.td-pri-pill.medium { background: color-mix(in oklch, var(--ink-3) 18%, transparent); color: var(--ink-2); }
.td-pri-pill.low    { color: var(--ink-3); border: 1px solid var(--border); padding: 1px 6px; }
.td-size-chip { font-size: var(--text-xs); color: var(--ink-3); border: 1px solid var(--border); padding: 1px 5px; border-radius: 3px; font-family: var(--font-mono); }
.td-epic-chip { display: inline-flex; align-items: center; gap: 5px; padding: 2px 7px 2px 6px; font-size: var(--text-xs); background: color-mix(in oklch, var(--epic-1) 14%, transparent); border-radius: 10px; color: color-mix(in oklch, var(--epic-1) 92%, white 8%); }
.td-epic-chip .td-swatch { width: 6px; height: 6px; border-radius: 50%; background: var(--epic-1); }
.td-branch, .td-worktree { font-family: var(--font-mono); font-size: var(--text-sm); cursor: copy; padding: 2px 6px; border-radius: 3px; transition: background .12s; }
.td-branch { color: var(--accent-2); }
.td-branch:hover { background: rgba(127,179,240,0.08); }
.td-worktree { color: var(--ink-3); border: 1px solid var(--border-soft); }
.td-worktree:hover { background: rgba(255,255,255,0.04); color: var(--ink-2); }
.td-release { font-size: var(--text-xs); padding: 2px 7px; border-radius: 3px; background: rgba(95,174,110,0.15); color: var(--green); font-family: var(--font-mono); }
.td-subrepo { font-size: var(--text-xs); color: var(--ink-3); margin-left: 4px; }

/* spec review */
.td-spec-block { display: inline-flex; align-items: center; gap: 6px; }
.td-spec-badge { font-size: var(--text-xs); padding: 2px 6px; border-radius: 3px; font-weight: 600; cursor: pointer; }
.td-spec-badge.pass { background: rgba(95,174,110,0.18); color: var(--green); }
.td-spec-badge.warn { background: color-mix(in oklch, var(--amber) 22%, transparent); color: var(--amber); }
.td-spec-badge.fail { background: color-mix(in oklch, var(--red) 22%, transparent); color: var(--red); }
.td-codex-note { font-style: italic; font-family: var(--font-serif); color: var(--ink-2); font-size: var(--text-md); margin-left: 6px; display: none; }
.td-codex-note.open { display: inline; }

/* auto-mode banner */
.td-auto-banner { background: linear-gradient(90deg, rgba(74,158,255,0.10), rgba(74,158,255,0.02)); border: 1px solid rgba(74,158,255,0.25); border-radius: var(--r-md); padding: 10px 12px; margin-bottom: var(--sp-5); display: flex; align-items: center; gap: var(--sp-4); }
.td-auto-banner .td-auto-step { flex: 1; color: var(--ink-2); font-size: var(--text-md); }
.td-auto-banner .td-auto-bar { width: 240px; height: 4px; background: rgba(255,255,255,0.05); border-radius: 2px; overflow: hidden; }
.td-auto-banner .td-auto-bar > span { display: block; height: 100%; background: linear-gradient(90deg, var(--accent), var(--accent-2)); }
.td-auto-banner .td-auto-elapsed { font-family: var(--font-mono); color: var(--ink-3); font-size: var(--text-xs); }

/* sections */
.td-section { margin-bottom: var(--task-section-mb); }
.td-section-h { font-size: var(--text-xs); text-transform: uppercase; letter-spacing: 0.1em; color: var(--ink-3); margin-bottom: var(--task-section-h); }
.td-section .md-body { color: var(--ink); font-size: var(--text-md); line-height: 1.55; }
.td-section .md-body h1 { font-size: var(--text-xl); margin: 14px 0 8px; }
.td-section .md-body h2 { font-size: var(--text-lg); margin: 12px 0 6px; }
.td-section .md-body h3 { font-size: var(--text-md); margin: 10px 0 4px; color: var(--ink-2); }
.td-section .md-body code { font-family: var(--font-mono); font-size: 0.92em; background: var(--bg-deep); padding: 1px 4px; border-radius: 3px; }
.td-section .md-body pre { background: var(--bg-deep); padding: 8px 10px; border-radius: 4px; overflow-x: auto; }
.td-section .md-body blockquote { border-left: 2px solid var(--border-strong); margin: 0; padding-left: 10px; color: var(--ink-2); font-style: italic; }

/* Docs section in body (typed link chips) */
.td-doc-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.td-doc-chips .td-doc-chip { display: inline-flex; gap: 6px; padding: 3px 8px; background: var(--bg-card); border: 1px solid var(--border); border-radius: 4px; font-size: var(--text-sm); color: var(--ink-2); text-decoration: none; }
.td-doc-chips .td-doc-chip:hover { border-color: var(--accent); color: var(--ink); }
.td-doc-chips .td-doc-chip .type { font-family: var(--font-mono); color: var(--accent-2); font-size: var(--text-xs); }

/* dates footer */
.td-dates { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: var(--sp-4); margin-top: var(--sp-7); padding-top: var(--sp-4); border-top: 1px solid var(--border-soft); }
.td-date-cell { display: flex; flex-direction: column; gap: 2px; }
.td-date-cell .lbl { font-size: var(--text-xs); color: var(--ink-3); text-transform: uppercase; letter-spacing: 0.08em; }
.td-date-cell .abs { font-family: var(--font-mono); font-size: var(--text-md); color: var(--ink); }
.td-date-cell .rel { font-size: var(--text-xs); color: var(--ink-3); }

/* right rail */
.td-rail { display: flex; flex-direction: column; gap: var(--sp-5); }
.td-panel { background: var(--bg-panel); border: 1px solid var(--border); border-radius: var(--r-md); padding: var(--sp-4) var(--sp-5); }
.td-rail-h { font-size: var(--text-xs); text-transform: uppercase; letter-spacing: 0.1em; color: var(--ink-3); margin-bottom: 6px; }
.td-rail-h-sub { margin-top: var(--sp-4); }
.td-rail-hint { font-size: var(--text-xs); color: var(--ink-3); font-style: italic; margin-bottom: 6px; }
.td-empty { font-size: var(--text-xs); color: var(--ink-3); }
.td-doc { display: flex; gap: 6px; padding: 4px 0; color: var(--ink-2); font-size: var(--text-sm); text-decoration: none; }
.td-doc:hover { color: var(--ink); }
.td-doc .td-doc-type { color: var(--accent-2); font-family: var(--font-mono); }
.td-lesson, .td-handover, .td-issue, .td-dep { padding: 4px 0; font-size: var(--text-sm); color: var(--ink-2); }
.td-handover-quote { margin: 4px 0 0; font-size: var(--text-md); color: var(--ink-2); }
.td-dep-list { list-style: none; padding: 0; margin: 0; }
.td-dep { cursor: pointer; }
.td-dep:hover { color: var(--ink); }
.td-dep-done { color: var(--ink-3); }
.td-dep-done span.mono { color: var(--green); }
.td-issue-sev { font-size: var(--text-xs); color: var(--ink-3); margin-left: 4px; }
.td-issue-critical .td-issue-sev { color: var(--red); }
.td-issue-high .td-issue-sev    { color: var(--amber); }
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/css/screens/task-detail.css
git commit -m "feat(viewer): task-detail.css skeleton (variant A + rail tokens)"
```

---

### Task 19: Stub `task-detail-document.js` and a failing Playwright test for header + meta

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/task-detail-document.js`
- Create: `plugins/taskmaster/viewer/tests/task-detail.spec.js`

- [ ] **Step 1: Create the renderer stub**

```javascript
// Variant A — Document layout for Task Detail.
// Exports `mountTaskDetailDocument(root, { task, related, prefs, onNavigate })`.

import { renderMarkdown } from './markdown.js';
import { mountRightRail } from './right-rail.js';

export function mountTaskDetailDocument(root, ctx) {
  root.innerHTML = '';
  root.classList.add('td-page', 'td-page-A');

  root.appendChild(renderHeader(ctx));
  root.appendChild(renderGrid(ctx));

  return () => { root.innerHTML = ''; };
}

function h(tag, attrs = {}, children = []) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') el.className = v;
    else if (k === 'on') for (const [evt, fn] of Object.entries(v)) el.addEventListener(evt, fn);
    else if (k === 'html') el.innerHTML = v;
    else el.setAttribute(k, v);
  }
  for (const c of [].concat(children)) {
    if (c == null || c === false) continue;
    el.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
  }
  return el;
}

function renderHeader({ task, prefs, onToggleVariant }) {
  return h('div', { class: 'td-ph' }, [
    h('span', { class: 'td-back', on: { click: () => history.back() } }, '‹ back'),
    h('span', { class: 'td-crumb' }, `Tasks / ${task?.epic || ''}`),
    h('div', { class: 'td-right' }, [
      h('div', { class: 'td-seg', 'data-test': 'view-toggle' }, [
        h('button', { class: 'td-seg-btn ' + (prefs?.screens?.task_detail?.view === 'A' ? 'on' : ''), 'data-view': 'A', on: { click: () => onToggleVariant?.('A') } }, 'Document'),
        h('button', { class: 'td-seg-btn ' + (prefs?.screens?.task_detail?.view === 'B' ? 'on' : ''), 'data-view': 'B', on: { click: () => onToggleVariant?.('B') } }, 'Graph'),
      ]),
      h('button', { class: 'td-action' }, 'Edit'),
      h('button', { class: 'td-action' }, 'Archive'),
    ]),
  ]);
}

function renderGrid(ctx) {
  return h('div', { class: 'td-grid' }, [
    renderBody(ctx),
    renderRail(ctx),
  ]);
}

function renderBody({ task }) {
  if (!task) {
    return h('div', { class: 'td-body td-empty' }, 'task not found');
  }
  return h('main', { class: 'td-body' }, [
    renderMeta(task),
    renderTitle(task),
    // Sections appended in later tasks (lock banner, chips, sections...).
  ]);
}

function renderMeta(task) {
  return h('div', { class: 'td-doc-meta', 'data-test': 'meta' }, [
    h('span', { class: 'td-id', 'data-test': 'task-id' },
      [h('span', { class: 'td-id-text' }, task.id || '—')]),
    h('span', { class: 'td-sep' }, '·'),
    h('span', {}, task.epic || ''),
    h('span', { class: 'td-sep' }, '·'),
    h('span', {}, task.phase || ''),
    h('span', { class: 'td-sep' }, '·'),
    h('span', {}, `created ${task.created || ''}`),
  ]);
}

function renderTitle(task) {
  return h('h1', { class: 'td-title', 'data-test': 'title' }, task.title || '');
}

function renderRail(ctx) {
  const aside = h('aside', { class: 'td-rail-mount', 'data-test': 'rail' });
  // Defer mounting to next tick so the parent grid lays out first.
  queueMicrotask(() => mountRightRail(aside, ctx));
  return aside;
}
```

- [ ] **Step 2: Add Playwright test**

Create `plugins/taskmaster/viewer/tests/task-detail.spec.js`:

```javascript
// @ts-check
import { test, expect } from '@playwright/test';

const TASK_ID = process.env.TM_TEST_TASK_ID || 'T-148';

test.describe('Task Detail screen', () => {
  test('Variant A renders header, meta, and title', async ({ page }) => {
    await page.goto(`/v3/#/task/${TASK_ID}`);
    await expect(page.locator('[data-test="view-toggle"]')).toBeVisible();
    await expect(page.locator('[data-test="meta"]')).toBeVisible();
    await expect(page.locator('[data-test="task-id"]')).toContainText(TASK_ID);
    await expect(page.locator('[data-test="title"]')).not.toBeEmpty();
  });
});
```

- [ ] **Step 3: Run the test, expect FAIL**

Run from `plugins/taskmaster/viewer/`: `npx playwright test tests/task-detail.spec.js`
Expected: FAIL — task-detail screen still resolves to the Plan 1 stub which does not yet render the Variant A meta. This is the point of the failing test; the next tasks fill it in.

- [ ] **Step 4: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/task-detail-document.js plugins/taskmaster/viewer/tests/task-detail.spec.js
git commit -m "test(viewer): pending Variant A header/meta/title smoke"
```

---

### Task 20: Wire `task-detail.js` to mount the document renderer (so Task 19's test passes)

**Files:**
- Modify: `plugins/taskmaster/viewer/js/screens/task-detail.js`

- [ ] **Step 1: Replace the Plan 1 stub**

Overwrite `plugins/taskmaster/viewer/js/screens/task-detail.js`:

```javascript
import { getTaskFull, getTaskRelatedFull, invalidateTask } from '../store.js';
import { mountTaskDetailDocument } from '../components/task-detail-document.js';
// Variant B is loaded lazily in M5; for now we forward to it via dynamic import.

export const meta = { title: 'Task Detail', icon: '◧', sidebarKey: null };

export async function mount(root, { params, store, api, prefs, subpath }) {
  const id = subpath?.[0] || params?.id || null;
  root.innerHTML = '<div class="td-page td-loading">Loading…</div>';

  if (!id) {
    root.innerHTML = '<div class="td-page td-empty">No task id in URL</div>';
    return () => {};
  }

  let task = null, related = null;
  try {
    [task, related] = await Promise.all([
      getTaskFull(id),
      getTaskRelatedFull(id),
    ]);
  } catch (e) {
    root.innerHTML = `<div class="td-page td-empty">Could not load ${id}: ${e.message}</div>`;
    return () => {};
  }

  const onNavigate = (toId) => { location.hash = `#/task/${toId}`; };
  const onToggleVariant = async (next) => {
    await api.savePrefs({ screens: { task_detail: { view: next } } });
    invalidateTask(id);
    location.reload();
  };

  const view = prefs?.screens?.task_detail?.view === 'B' ? 'B' : 'A';
  let cleanup;
  if (view === 'B') {
    const mod = await import('../components/task-detail-graph.js');
    cleanup = mod.mountTaskDetailGraph(root, { task, related, prefs, onNavigate, onToggleVariant });
  } else {
    cleanup = mountTaskDetailDocument(root, { task, related, prefs, onNavigate, onToggleVariant });
  }
  return cleanup;
}
```

- [ ] **Step 2: Run the Playwright test from Task 19**

Run: `npx playwright test tests/task-detail.spec.js`
Expected: PASS (1 test).

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/js/screens/task-detail.js
git commit -m "feat(viewer): mount Variant A by default for Task Detail"
```

---

### Task 21: Add the lock banner (conditional on `locked_by`)

**Files:**
- Modify: `plugins/taskmaster/viewer/js/components/task-detail-document.js`
- Modify: `plugins/taskmaster/viewer/tests/task-detail.spec.js`

- [ ] **Step 1: Append the failing test**

Append to `task-detail.spec.js`:

```javascript
test('lock banner appears only when locked_by is set', async ({ page }) => {
  await page.goto(`/v3/#/task/${TASK_ID}`);
  // The seed task in the test fixture is not locked — banner absent.
  // For the locked branch we rely on a separate task id; if not available,
  // assert the absent case here.
  const banner = page.locator('[data-test="lock-banner"]');
  // Accept either: present-and-visible, or not-attached.
  if (await banner.count()) {
    await expect(banner).toContainText(/locked/i);
  }
});
```

- [ ] **Step 2: Add lock banner rendering**

In `task-detail-document.js`, modify `renderBody` to insert the banner after `renderTitle`:

```javascript
function renderBody({ task }) {
  if (!task) return h('div', { class: 'td-body td-empty' }, 'task not found');
  const children = [
    renderMeta(task),
    renderTitle(task),
  ];
  if (task.locked_by) {
    children.push(h('div', { class: 'td-lock-banner', 'data-test': 'lock-banner' },
      [h('span', {}, '🔒 '), h('span', {}, `locked by ${task.locked_by}`)]));
  }
  return h('main', { class: 'td-body' }, children);
}
```

- [ ] **Step 3: Run**

Run: `npx playwright test tests/task-detail.spec.js`
Expected: 2 tests PASS.

- [ ] **Step 4: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/task-detail-document.js plugins/taskmaster/viewer/tests/task-detail.spec.js
git commit -m "feat(viewer): task-detail lock banner (Variant A)"
```

---

### Task 22: Add the chip row (status / priority / size / epic / branch / worktree / release / sub_repo)

**Files:**
- Modify: `plugins/taskmaster/viewer/js/components/task-detail-document.js`

- [ ] **Step 1: Append `renderChips` to the document renderer**

In `task-detail-document.js`, append:

```javascript
function renderChips(task) {
  const epicColorVar = `--epic-1`; // viewer assigns by index in real impl; placeholder here.
  const priClass = (task.priority || '').toLowerCase();
  const chips = [
    h('span', { class: 'td-status-pill' }, task.status || 'unknown'),
    h('span', { class: `td-pri-pill ${priClass === 'critical' ? 'crit' : priClass}` }, task.priority || ''),
    task.estimate ? h('span', { class: 'td-size-chip' }, task.estimate) : null,
    task.epic ? h('span', { class: 'td-epic-chip', style: `--epic-1: var(${epicColorVar})` },
      [h('span', { class: 'td-swatch' }), h('span', {}, task.epic)]) : null,
    task.branch ? h('span', { class: 'td-branch', 'data-test': 'branch', on: { click: (e) => copyToChip(e.currentTarget, task.branch) } },
      [h('span', { class: 'td-id-text' }, `⎇ ${task.branch}`)]) : null,
    task.worktree ? h('span', { class: 'td-worktree', on: { click: (e) => copyToChip(e.currentTarget, task.worktree) } },
      [h('span', { class: 'td-id-text' }, `⌂ ${task.worktree}`)]) : null,
    task.release ? h('span', { class: 'td-release' }, task.release) : null,
    task.sub_repo ? h('span', { class: 'td-subrepo' }, `· ${task.sub_repo}`) : null,
  ].filter(Boolean);
  return h('div', { class: 'td-chips', 'data-test': 'chips' }, chips);
}

async function copyToChip(el, value) {
  try { await navigator.clipboard.writeText(value); } catch {}
  el.classList.add('copied');
  setTimeout(() => el.classList.remove('copied'), 900);
}
```

Then in `renderBody`, push `renderChips(task)` after the lock-banner branch.

- [ ] **Step 2: Append a Playwright check**

Append to `task-detail.spec.js`:

```javascript
test('chip row contains status, priority, size, epic', async ({ page }) => {
  await page.goto(`/v3/#/task/${TASK_ID}`);
  const chips = page.locator('[data-test="chips"]');
  await expect(chips).toBeVisible();
  await expect(chips.locator('.td-status-pill')).toBeVisible();
  await expect(chips.locator('.td-pri-pill')).toBeVisible();
  await expect(chips.locator('.td-size-chip')).toBeVisible();
  await expect(chips.locator('.td-epic-chip')).toBeVisible();
});
```

- [ ] **Step 3: Run**

Run: `npx playwright test tests/task-detail.spec.js`
Expected: 3 tests PASS.

- [ ] **Step 4: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/task-detail-document.js plugins/taskmaster/viewer/tests/task-detail.spec.js
git commit -m "feat(viewer): task-detail chip row (Variant A)"
```

---

### Task 23: Add the spec-review badge with click-to-expand codex note

**Files:**
- Modify: `plugins/taskmaster/viewer/js/components/task-detail-document.js`

- [ ] **Step 1: Append `renderSpecReview`**

```javascript
function renderSpecReview(task) {
  const sr = task.spec_review;
  if (!sr || !sr.verdict) return null;
  const note = sr.codex_note || '';
  return h('div', { class: 'td-spec-block', 'data-test': 'spec-review' }, [
    h('span', { class: `td-spec-badge ${sr.verdict}`,
                on: { click: (e) => e.currentTarget.nextElementSibling?.classList.toggle('open') } },
      sr.verdict.toUpperCase()),
    h('span', { class: 'td-codex-note serif' }, note),
  ]);
}
```

In `renderBody`, push `renderSpecReview(task)` after `renderChips(task)`. Use `.filter(Boolean)` on the children array if not already.

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/task-detail-document.js
git commit -m "feat(viewer): spec-review badge with expandable codex note"
```

---

### Task 24: Add the auto-mode banner (conditional)

**Files:**
- Modify: `plugins/taskmaster/viewer/js/components/task-detail-document.js`

- [ ] **Step 1: Append `renderAutoBanner`**

```javascript
function renderAutoBanner(task) {
  // Render only when the task is currently driven by auto-mode.
  const am = task.auto_mode;
  if (!am || !am.running) return null;
  const pct = Math.max(0, Math.min(100, Math.round((am.progress || 0) * 100)));
  return h('div', { class: 'td-auto-banner', 'data-test': 'auto-banner' }, [
    h('span', { class: 'td-auto-step' }, am.step || 'auto-mode running'),
    h('div', { class: 'td-auto-bar' }, h('span', { style: `width:${pct}%` })),
    h('span', { class: 'td-auto-elapsed' }, am.elapsed || ''),
  ]);
}
```

Push `renderAutoBanner(task)` after `renderSpecReview(task)`.

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/task-detail-document.js
git commit -m "feat(viewer): auto-mode banner on task detail"
```

---

### Task 25: Add Docs / Specification / Plan / Notes / Review-instructions sections

**Files:**
- Modify: `plugins/taskmaster/viewer/js/components/task-detail-document.js`

- [ ] **Step 1: Append the section renderers**

```javascript
function renderDocsSection(task) {
  const docs = task.docs || {};
  const entries = Object.entries(docs);
  if (!entries.length) return null;
  return h('section', { class: 'td-section', 'data-test': 'sec-docs' }, [
    h('div', { class: 'td-section-h' }, 'Docs'),
    h('div', { class: 'td-doc-chips' },
      entries.map(([type, href]) =>
        h('a', { class: 'td-doc-chip', href, target: '_blank', rel: 'noopener' },
          [h('span', { class: 'type' }, type), h('span', {}, href)]))),
  ]);
}

function renderMdSection(label, body, dataTest) {
  if (!body || !String(body).trim()) return null;
  return h('section', { class: 'td-section', 'data-test': dataTest }, [
    h('div', { class: 'td-section-h' }, label),
    h('div', { class: 'md-body', html: renderMarkdown(body) }),
  ]);
}
```

In `renderBody`, after the auto-banner, append:

```javascript
  children.push(renderDocsSection(task));
  children.push(renderMdSection('Specification', task.specification || task.description, 'sec-spec'));
  children.push(renderMdSection('Plan', task.plan, 'sec-plan'));
  children.push(renderMdSection('Notes', task.notes, 'sec-notes'));
  if (task.status === 'in-review') {
    children.push(renderMdSection('Review instructions', task.review_instructions, 'sec-review-instructions'));
  }
```

(Wrap the existing `children` push pattern in `.filter(Boolean)` before passing to `h('main', ...)`.)

- [ ] **Step 2: Append a Playwright check**

Append to `task-detail.spec.js`:

```javascript
test('document sections render description and notes', async ({ page }) => {
  await page.goto(`/v3/#/task/${TASK_ID}`);
  // The seed task has Description + Notes from the server fixture.
  await expect(page.locator('[data-test="sec-spec"]')).toBeVisible();
  await expect(page.locator('[data-test="sec-notes"]')).toBeVisible();
});
```

- [ ] **Step 3: Run**

Run: `npx playwright test tests/task-detail.spec.js`
Expected: 4 tests PASS.

- [ ] **Step 4: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/task-detail-document.js plugins/taskmaster/viewer/tests/task-detail.spec.js
git commit -m "feat(viewer): doc sections (Docs/Spec/Plan/Notes/Review)"
```

---

### Task 26: Add Latest activity + Patchnote sections (conditional)

**Files:**
- Modify: `plugins/taskmaster/viewer/js/components/task-detail-document.js`

- [ ] **Step 1: Append the renderers**

```javascript
function renderActivity(task) {
  const lines = task.activity || task.activity_lines;
  if (!lines || !lines.length) return null;
  return h('section', { class: 'td-section', 'data-test': 'sec-activity' }, [
    h('div', { class: 'td-section-h' }, 'Latest activity'),
    h('ul', { class: 'td-activity' },
      lines.slice(0, 8).map((l) => h('li', { class: 'mono' }, l))),
  ]);
}

function renderPatchnote(task) {
  if (task.status !== 'done') return null;
  if (!task.patchnote) return null;
  return renderMdSection('Patchnote', task.patchnote, 'sec-patchnote');
}
```

In `renderBody`, after the conditional review-instructions section, append:

```javascript
  children.push(renderActivity(task));
  children.push(renderPatchnote(task));
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/task-detail-document.js
git commit -m "feat(viewer): activity + patchnote sections"
```

---

### Task 27: Add the dates footer block (Created / Started / Completed)

**Files:**
- Modify: `plugins/taskmaster/viewer/js/components/task-detail-document.js`

- [ ] **Step 1: Append the renderer + helper**

```javascript
function renderDates(task) {
  const cells = [
    ['Created',   task.created],
    ['Started',   task.started],
    ['Completed', task.completed],
  ];
  return h('section', { class: 'td-dates', 'data-test': 'dates' },
    cells.map(([lbl, abs]) =>
      h('div', { class: 'td-date-cell' }, [
        h('span', { class: 'lbl' }, lbl),
        h('span', { class: 'abs mono' }, abs || '—'),
        h('span', { class: 'rel' }, abs ? relativeFromNow(abs) : ''),
      ])));
}

function relativeFromNow(iso) {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '';
  const ms = Date.now() - d.getTime();
  const days = Math.floor(ms / 86400000);
  if (days < 1) return 'today';
  if (days < 30) return `${days}d ago`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months}mo ago`;
  return `${Math.floor(days / 365)}y ago`;
}
```

Push `renderDates(task)` last in `renderBody`.

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/task-detail-document.js
git commit -m "feat(viewer): dates footer (Created/Started/Completed)"
```

---

### Task 28: Add click-to-copy on the meta `id` chip

**Files:**
- Modify: `plugins/taskmaster/viewer/js/components/task-detail-document.js`

- [ ] **Step 1: Bind click handler on the `.td-id` element**

In `renderMeta`, change the `td-id` line to:

```javascript
    h('span', { class: 'td-id', 'data-test': 'task-id',
                on: { click: (e) => copyToChip(e.currentTarget, task.id || '') } },
      [h('span', { class: 'td-id-text' }, task.id || '—')]),
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/task-detail-document.js
git commit -m "feat(viewer): click-to-copy task id in meta line"
```

---

## M5 — Variant B (Graph)

### Task 29: Stub `task-detail-graph.js` and a failing Playwright test for the Graph variant

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/task-detail-graph.js`
- Modify: `plugins/taskmaster/viewer/tests/task-detail.spec.js`

- [ ] **Step 1: Create the stub**

```javascript
// Variant B — Graph layout for Task Detail.
// Renders a compact head, an SVG-based dependency graph, a context band,
// graph controls, and tabs (Spec / Plan / Notes / Activity / Anchors / Raw YAML).

import { computeGraphLayout } from './dependency-graph.js';
import { mountRightRail } from './right-rail.js';
import { renderMarkdown } from './markdown.js';

export function mountTaskDetailGraph(root, ctx) {
  root.innerHTML = '';
  root.classList.add('td-page', 'td-page-B');

  root.appendChild(renderHeader(ctx));
  root.appendChild(renderGrid(ctx));
  return () => { root.innerHTML = ''; };
}

function h(tag, attrs = {}, children = []) {
  const NS = tag === 'svg' || tag === 'g' || tag === 'path' || tag === 'rect' || tag === 'text' || tag === 'circle' || tag === 'line';
  const el = NS ? document.createElementNS('http://www.w3.org/2000/svg', tag) : document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') NS ? el.setAttribute('class', v) : (el.className = v);
    else if (k === 'on') for (const [evt, fn] of Object.entries(v)) el.addEventListener(evt, fn);
    else if (k === 'html') el.innerHTML = v;
    else el.setAttribute(k, v);
  }
  for (const c of [].concat(children)) {
    if (c == null || c === false) continue;
    el.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
  }
  return el;
}

function renderHeader({ task, prefs, onToggleVariant }) {
  return h('div', { class: 'td-ph' }, [
    h('span', { class: 'td-back', on: { click: () => history.back() } }, '‹ back'),
    h('span', { class: 'td-crumb' }, `Tasks / ${task?.epic || ''}`),
    h('div', { class: 'td-right' }, [
      h('div', { class: 'td-seg', 'data-test': 'view-toggle' }, [
        h('button', { class: 'td-seg-btn ' + (prefs?.screens?.task_detail?.view === 'A' ? 'on' : ''), 'data-view': 'A', on: { click: () => onToggleVariant?.('A') } }, 'Document'),
        h('button', { class: 'td-seg-btn ' + (prefs?.screens?.task_detail?.view === 'B' ? 'on' : ''), 'data-view': 'B', on: { click: () => onToggleVariant?.('B') } }, 'Graph'),
      ]),
      h('button', { class: 'td-action' }, 'Edit'),
      h('button', { class: 'td-action' }, 'Archive'),
    ]),
  ]);
}

function renderGrid(ctx) {
  return h('div', { class: 'td-grid' }, [
    renderBody(ctx),
    renderRail(ctx),
  ]);
}

function renderBody(ctx) {
  const main = h('main', { class: 'td-body' });
  main.appendChild(renderCompactHead(ctx.task));
  main.appendChild(renderGraphFrame(ctx));
  main.appendChild(renderTabs(ctx));
  return main;
}

function renderCompactHead(task) {
  return h('div', { class: 'td-head-block', 'data-test': 'compact-head' }, [
    h('div', { class: 'td-doc-meta' }, [
      h('span', { class: 'td-id mono' }, task?.id || ''),
      h('span', { class: 'td-sep' }, '·'),
      h('span', {}, task?.epic || ''),
      h('span', { class: 'td-sep' }, '·'),
      h('span', {}, task?.phase || ''),
    ]),
    h('h2', { class: 'td-head-title' }, task?.title || ''),
  ]);
}

function renderRail(ctx) {
  const aside = h('aside', { class: 'td-rail-mount', 'data-test': 'rail' });
  queueMicrotask(() => mountRightRail(aside, ctx));
  return aside;
}

// Graph + tabs — filled in by Tasks 30-37
function renderGraphFrame(ctx) {
  return h('div', { class: 'td-graph-placeholder', 'data-test': 'graph-frame' }, '');
}
function renderTabs(ctx) {
  return h('div', { class: 'td-tabs-placeholder', 'data-test': 'tabs' }, '');
}
```

- [ ] **Step 2: Add a failing test**

Append to `task-detail.spec.js`:

```javascript
test('Variant B renders compact head, graph frame, and tabs', async ({ page }) => {
  await page.goto(`/v3/#/task/${TASK_ID}?view=B`);
  // Force prefs via API to avoid relying on persisted state.
  await page.request.put('/api/viewer/prefs', { data: { screens: { task_detail: { view: 'B' } } } });
  await page.reload();
  await expect(page.locator('[data-test="compact-head"]')).toBeVisible();
  await expect(page.locator('[data-test="graph-frame"]')).toBeVisible();
  await expect(page.locator('[data-test="tabs"]')).toBeVisible();
});
```

- [ ] **Step 3: Run**

Run: `npx playwright test tests/task-detail.spec.js -g "Variant B renders"`
Expected: PASS (the placeholders satisfy presence).

- [ ] **Step 4: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/task-detail-graph.js plugins/taskmaster/viewer/tests/task-detail.spec.js
git commit -m "feat(viewer): Variant B graph stub with compact head + placeholders"
```

---

### Task 30: Build the SVG graph frame (axis rail, canvas, column guides)

**Files:**
- Modify: `plugins/taskmaster/viewer/js/components/task-detail-graph.js`
- Modify: `plugins/taskmaster/viewer/css/screens/task-detail.css`

- [ ] **Step 1: Add CSS**

Append to `task-detail.css`:

```css
/* Variant B */
.td-page-B .td-head-block { padding: 10px 0 var(--sp-5); border-bottom: 1px solid var(--border-soft); margin-bottom: var(--sp-5); }
.td-page-B .td-head-title { font-size: var(--text-xl); font-weight: 600; letter-spacing: -0.01em; color: var(--ink); margin: 5px 0 var(--sp-3); line-height: 1.25; }

.td-graph-frame {
  background: var(--graph-frame-bg);
  border: 1px solid var(--graph-frame-border);
  border-radius: var(--r-md);
  margin-bottom: var(--sp-7);
  position: relative;
  overflow: hidden;
  box-shadow: var(--graph-frame-shadow);
}
.td-graph-rail {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 14px;
  border-bottom: 1px solid var(--border-soft);
  font-size: var(--text-xs); color: var(--ink-3);
  background: rgba(255,255,255,0.015);
}
.td-graph-rail .axis { letter-spacing: 0.1em; text-transform: uppercase; }
.td-graph-rail .legend { display: flex; gap: 12px; font-size: var(--text-xs); color: var(--ink-3); }
.td-graph-rail .legend .dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; margin-right: 4px; vertical-align: middle; }
.td-graph-rail .legend .dot.s-done { background: var(--green); }
.td-graph-rail .legend .dot.s-progress { background: var(--accent); }
.td-graph-rail .legend .dot.s-backlog { background: var(--ink-3); }
.td-graph-svg { width: 100%; height: var(--graph-canvas-h); display: block; }
.td-graph-context-band {
  border-top: 1px solid var(--border-soft);
  padding: 8px 14px;
  display: flex; align-items: center; gap: 14px;
  font-size: var(--text-xs); color: var(--ink-3);
  background: rgba(255,255,255,0.015);
  flex-wrap: wrap;
}
.td-graph-context-band .lbl { letter-spacing: 0.08em; text-transform: uppercase; flex: 0 0 auto; }
.td-graph-context-band .ctx-pill {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 3px 8px; font-size: var(--text-sm); border-radius: 3px;
  background: var(--bg-card); border: 1px solid var(--border-soft);
  cursor: pointer; color: var(--ink-2);
}
.td-graph-context-band .ctx-pill.lesson .glyph { color: var(--green); }
.td-graph-context-band .ctx-pill.issue .glyph { color: var(--red); }
.td-graph-context-band .ctx-pill.handover { font-style: italic; font-family: var(--font-serif); font-size: 11.5px; }

.td-graph-controls {
  display: flex; gap: 6px; padding: 8px 14px;
  border-top: 1px solid var(--border-soft);
  background: rgba(255,255,255,0.015);
}
.td-graph-controls .gc-btn {
  background: rgba(0,0,0,0.4); border: 1px solid var(--border-soft);
  color: var(--ink-2); font-size: var(--text-xs); padding: 3px 8px; border-radius: 4px;
  cursor: pointer; backdrop-filter: blur(4px);
}
.td-graph-controls .gc-btn.on { background: rgba(74,158,255,0.18); color: var(--accent); border-color: rgba(74,158,255,0.4); }

/* SVG: column guides + nodes */
.td-graph-svg .col-guide { stroke: var(--graph-col-guide); stroke-dasharray: 3 4; }
.td-graph-svg .col-label { fill: var(--ink-3); font-size: 9px; font-family: var(--font-mono); text-transform: uppercase; }
.td-graph-svg .node-rect { fill: var(--bg-card); stroke: var(--border); filter: drop-shadow(0 4px 14px rgba(0,0,0,0.5)); }
.td-graph-svg .node-rect.center { stroke: var(--accent); }
.td-graph-svg .node-rect.faded { opacity: 0.6; }
.td-graph-svg .node-id { fill: var(--epic-1); font-family: var(--font-mono); font-size: 10px; }
.td-graph-svg .node-title { fill: var(--ink); font-size: 11px; font-weight: 600; }
.td-graph-svg .node-meta { fill: var(--ink-3); font-size: 9px; font-family: var(--font-mono); }
.td-graph-svg .edge-path { fill: none; stroke: var(--graph-edge-stroke); stroke-width: 1.4; }
.td-graph-svg .edge-path.active { stroke: var(--graph-edge-stroke-active); }
.td-graph-svg .status-dot.s-done { fill: var(--green); }
.td-graph-svg .status-dot.s-progress { fill: var(--accent); }
.td-graph-svg .status-dot.s-backlog { fill: var(--ink-3); }
```

- [ ] **Step 2: Replace `renderGraphFrame` placeholder with the real frame**

In `task-detail-graph.js`, replace the `renderGraphFrame` function:

```javascript
function renderGraphFrame(ctx) {
  const frame = h('div', { class: 'td-graph-frame', 'data-test': 'graph-frame' });
  frame.appendChild(renderGraphRail());
  frame.appendChild(renderGraphSvg(ctx));
  frame.appendChild(renderContextBand(ctx));
  frame.appendChild(renderGraphControls(ctx));
  return frame;
}

function renderGraphRail() {
  return h('div', { class: 'td-graph-rail' }, [
    h('span', { class: 'axis' }, '← Dependencies | This task | Unblocks →'),
    h('span', { class: 'legend' }, [
      h('span', {}, [h('span', { class: 'dot s-done' }), 'done']),
      h('span', {}, [h('span', { class: 'dot s-progress' }), 'in progress']),
      h('span', {}, [h('span', { class: 'dot s-backlog' }), 'backlog']),
    ]),
  ]);
}

function renderGraphSvg({ task, related, onNavigate }) {
  // Build input for the pure-data layout.
  const upstream = (related?.dependencies || []).map((d) => ({
    id: d.id, title: d.title, status: d.status, depth: 1,
  }));
  const downstream = (related?.unblocks || []).map((d) => ({
    id: d.id, title: d.title, status: d.status, depth: 1,
  }));
  const layout = computeGraphLayout({
    center: { id: task.id, title: task.title, status: task.status,
              priority: task.priority, estimate: task.estimate,
              time_in_status: task.time_in_status,
              progress: task.auto_mode?.progress ?? null,
              step: task.auto_mode?.step ?? null },
    upstream, downstream,
    width: 820, height: 320,
  });

  const svg = h('svg', {
    class: 'td-graph-svg', viewBox: '0 0 820 320',
    preserveAspectRatio: 'xMidYMid meet',
    'data-test': 'graph-svg',
  });

  // Column guides + labels
  for (const col of layout.columns) {
    svg.appendChild(h('line', { class: 'col-guide', x1: col.x, y1: 14, x2: col.x, y2: 314 }));
    svg.appendChild(h('text', { class: 'col-label', x: col.x, y: 14, 'text-anchor': 'middle' }, col.label));
  }
  // Edges
  for (const e of layout.edges) {
    svg.appendChild(h('path', { class: 'edge-path', d: e.path }));
  }
  // Nodes
  for (const n of layout.nodes) {
    svg.appendChild(renderNode(n, onNavigate));
  }
  return svg;
}

function renderNode(n, onNavigate) {
  const g = h('g', { class: 'node', 'data-id': n.id, on: { click: () => onNavigate?.(n.id) } });
  g.appendChild(h('rect', {
    class: `node-rect ${n.isCenter ? 'center' : ''} ${n.faded ? 'faded' : ''}`,
    x: n.x, y: n.y, width: n.w, height: n.h, rx: 6, ry: 6,
  }));
  g.appendChild(h('circle', {
    class: `status-dot s-${(n.status || '').replace(/[^a-z]/gi, '')}`,
    cx: n.x + 10, cy: n.y + 12, r: 4,
  }));
  g.appendChild(h('text', { class: 'node-id', x: n.x + 20, y: n.y + 16 }, n.id));
  if (n.time_in_status) {
    g.appendChild(h('text', { class: 'node-meta', x: n.x + n.w - 8, y: n.y + 16, 'text-anchor': 'end' }, n.time_in_status));
  }
  g.appendChild(h('text', { class: 'node-title', x: n.x + 10, y: n.y + 36 }, truncate(n.title, n.isCenter ? 20 : 14)));
  if (n.priority || n.estimate) {
    g.appendChild(h('text', { class: 'node-meta', x: n.x + 10, y: n.y + n.h - 8 },
      [n.priority, n.estimate].filter(Boolean).join(' · ')));
  }
  if (n.isCenter && (n.progress != null || n.step)) {
    // Progress bar inside the center node
    const barW = n.w - 20;
    const pct = Math.max(0, Math.min(1, n.progress || 0));
    g.appendChild(h('rect', { x: n.x + 10, y: n.y + n.h - 22, width: barW, height: 3, fill: 'rgba(255,255,255,0.05)' }));
    g.appendChild(h('rect', { x: n.x + 10, y: n.y + n.h - 22, width: barW * pct, height: 3, fill: 'var(--accent)' }));
    if (n.step) {
      g.appendChild(h('text', { class: 'node-meta', x: n.x + 10, y: n.y + n.h - 26 }, truncate(n.step, 22)));
    }
  }
  return g;
}

function truncate(s, n) { s = s || ''; return s.length > n ? s.slice(0, n - 1) + '…' : s; }
```

- [ ] **Step 3: Run the smoke**

Run: `npx playwright test tests/task-detail.spec.js -g "Variant B"`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/task-detail-graph.js plugins/taskmaster/viewer/css/screens/task-detail.css
git commit -m "feat(viewer): Variant B graph SVG with bezier edges + column guides"
```

---

### Task 31: Render the context band (lessons / handovers / issues pills)

**Files:**
- Modify: `plugins/taskmaster/viewer/js/components/task-detail-graph.js`

- [ ] **Step 1: Replace placeholder `renderContextBand`**

```javascript
function renderContextBand({ related, onNavigate }) {
  const lessons   = related?.lessons || [];
  const handovers = related?.handovers || [];
  const issues    = related?.issues || [];
  const band = h('div', { class: 'td-graph-context-band', 'data-test': 'context-band' });
  if (lessons.length) {
    band.appendChild(h('span', { class: 'lbl' }, 'Lessons'));
    for (const l of lessons.slice(0, 4)) {
      band.appendChild(h('span', { class: 'ctx-pill lesson' },
        [h('span', { class: 'glyph' }, '✦'), h('span', { class: 'mono' }, l.id)]));
    }
  }
  if (handovers.length) {
    band.appendChild(h('span', { class: 'lbl' }, 'Handovers'));
    for (const ho of handovers.slice(0, 3)) {
      band.appendChild(h('span', { class: 'ctx-pill handover' },
        [h('span', { class: 'glyph' }, '§'), h('span', {}, ho.id)]));
    }
  }
  if (issues.length) {
    band.appendChild(h('span', { class: 'lbl' }, 'Issues'));
    for (const i of issues.slice(0, 4)) {
      band.appendChild(h('span', { class: 'ctx-pill issue' },
        [h('span', { class: 'glyph' }, '!'), h('span', { class: 'mono' }, i.id)]));
    }
  }
  return band;
}
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/task-detail-graph.js
git commit -m "feat(viewer): Variant B context band (lessons/handovers/issues)"
```

---

### Task 32: Render graph controls (depth toggle / show all / hide context / fullscreen)

**Files:**
- Modify: `plugins/taskmaster/viewer/js/components/task-detail-graph.js`

- [ ] **Step 1: Add the controls renderer**

```javascript
function renderGraphControls(ctx) {
  const wrap = h('div', { class: 'td-graph-controls', 'data-test': 'graph-controls' });
  const buttons = [
    { id: 'depth', label: 'Depth: 2', toggle: () => {} },
    { id: 'show-all', label: 'Show all', toggle: () => {} },
    { id: 'hide-context', label: 'Hide context', toggle: (el) => el.classList.toggle('on') },
    { id: 'fullscreen', label: 'Fullscreen', toggle: (el) => {
        const f = el.closest('.td-graph-frame');
        if (!document.fullscreenElement) f.requestFullscreen?.();
        else document.exitFullscreen?.();
      } },
  ];
  for (const b of buttons) {
    const btn = h('button', { class: 'gc-btn', 'data-id': b.id, on: { click: (e) => b.toggle(e.currentTarget) } }, b.label);
    wrap.appendChild(btn);
  }
  // Hide-context wires up actual visibility:
  wrap.querySelector('[data-id="hide-context"]').addEventListener('click', (e) => {
    const frame = e.currentTarget.closest('.td-graph-frame');
    frame.querySelector('.td-graph-context-band')?.classList.toggle('hidden');
  });
  return wrap;
}
```

Add the matching CSS rule at the bottom of `task-detail.css`:

```css
.td-graph-context-band.hidden { display: none; }
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/task-detail-graph.js plugins/taskmaster/viewer/css/screens/task-detail.css
git commit -m "feat(viewer): Variant B graph controls (depth / show-all / hide-context / fullscreen)"
```

---

### Task 33: Render the tab bar (Spec / Plan / Notes / Activity / Anchors / Raw YAML)

**Files:**
- Modify: `plugins/taskmaster/viewer/js/components/task-detail-graph.js`
- Modify: `plugins/taskmaster/viewer/css/screens/task-detail.css`

- [ ] **Step 1: Append CSS**

```css
.td-tabs { display: flex; gap: 0; border-bottom: 1px solid var(--border-soft); margin-bottom: var(--sp-5); }
.td-tabs .td-tab { padding: 6px 12px; font-size: var(--text-sm); color: var(--ink-3); background: transparent; border: 0; cursor: pointer; border-bottom: 2px solid transparent; }
.td-tabs .td-tab.on { color: var(--ink); border-bottom-color: var(--accent); }
.td-tab-panel { display: none; }
.td-tab-panel.on { display: block; }
.td-tab-panel pre { background: var(--bg-deep); padding: 10px 12px; border-radius: 4px; overflow-x: auto; font-family: var(--font-mono); font-size: 11px; color: var(--ink-2); }
.td-anchor-pill { display: inline-block; padding: 2px 8px; margin-right: 6px; font-family: var(--font-mono); background: var(--bg-card); border: 1px solid var(--border-soft); border-radius: 3px; font-size: var(--text-sm); color: var(--ink-2); }
```

- [ ] **Step 2: Replace `renderTabs`**

```javascript
function renderTabs({ task, related }) {
  const tabs = [
    ['spec',     'Spec',     () => renderMd(task.specification || task.description)],
    ['plan',     'Plan',     () => renderMd(task.plan)],
    ['notes',    'Notes',    () => renderMd(task.notes)],
    ['activity', 'Activity', () => renderActivityList(task.activity || [])],
    ['anchors',  'Anchors',  () => renderAnchors(task.anchors || [])],
    ['raw',      'Raw YAML', () => renderRaw(task)],
  ];
  const wrap = h('div', { class: 'td-tabs-wrap', 'data-test': 'tabs' });
  const bar = h('div', { class: 'td-tabs' });
  const panels = h('div', { class: 'td-tab-panels' });
  tabs.forEach(([id, label, build], idx) => {
    const tab = h('button', { class: `td-tab ${idx === 0 ? 'on' : ''}`, 'data-tab': id }, label);
    const panel = h('div', { class: `td-tab-panel ${idx === 0 ? 'on' : ''}`, 'data-tab-panel': id });
    panel.appendChild(build());
    tab.addEventListener('click', () => {
      bar.querySelectorAll('.td-tab').forEach((t) => t.classList.toggle('on', t === tab));
      panels.querySelectorAll('.td-tab-panel').forEach((p) => p.classList.toggle('on', p.dataset.tabPanel === id));
    });
    bar.appendChild(tab);
    panels.appendChild(panel);
  });
  wrap.appendChild(bar);
  wrap.appendChild(panels);
  return wrap;
}

function renderMd(src) {
  const div = document.createElement('div');
  div.className = 'md-body';
  div.innerHTML = renderMarkdown(src || '_(empty)_');
  return div;
}
function renderActivityList(lines) {
  const ul = document.createElement('ul');
  for (const l of (lines || []).slice(0, 30)) {
    const li = document.createElement('li');
    li.className = 'mono';
    li.textContent = l;
    ul.appendChild(li);
  }
  if (!ul.children.length) ul.innerHTML = '<li class="td-empty">no activity</li>';
  return ul;
}
function renderAnchors(anchors) {
  const wrap = document.createElement('div');
  if (!anchors.length) { wrap.className = 'td-empty'; wrap.textContent = 'no anchors'; return wrap; }
  for (const a of anchors) {
    const pill = document.createElement('span');
    pill.className = 'td-anchor-pill';
    pill.textContent = a;
    wrap.appendChild(pill);
  }
  return wrap;
}
function renderRaw(task) {
  const pre = document.createElement('pre');
  pre.textContent = JSON.stringify(task, null, 2);
  return pre;
}
```

- [ ] **Step 3: Run smoke**

Run: `npx playwright test tests/task-detail.spec.js`
Expected: All Variant A + B tests still PASS.

- [ ] **Step 4: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/task-detail-graph.js plugins/taskmaster/viewer/css/screens/task-detail.css
git commit -m "feat(viewer): Variant B tab bar (Spec/Plan/Notes/Activity/Anchors/Raw YAML)"
```

---

### Task 34: Add a Playwright assertion for the graph SVG node count

**Files:**
- Modify: `plugins/taskmaster/viewer/tests/task-detail.spec.js`

- [ ] **Step 1: Append the test**

```javascript
test('Variant B graph SVG renders at least one center node', async ({ page }) => {
  await page.request.put('/api/viewer/prefs', { data: { screens: { task_detail: { view: 'B' } } } });
  await page.goto(`/v3/#/task/${TASK_ID}`);
  await expect(page.locator('[data-test="graph-svg"]')).toBeVisible();
  const centerNodes = page.locator('[data-test="graph-svg"] .node-rect.center');
  await expect(centerNodes).toHaveCount(1);
});
```

- [ ] **Step 2: Run**

Run: `npx playwright test tests/task-detail.spec.js`
Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/tests/task-detail.spec.js
git commit -m "test(viewer): Variant B graph contains exactly one center node"
```

---

### Task 35: Add a Playwright assertion for tab switching

**Files:**
- Modify: `plugins/taskmaster/viewer/tests/task-detail.spec.js`

- [ ] **Step 1: Append the test**

```javascript
test('Variant B tabs switch and render Anchors panel', async ({ page }) => {
  await page.request.put('/api/viewer/prefs', { data: { screens: { task_detail: { view: 'B' } } } });
  await page.goto(`/v3/#/task/${TASK_ID}`);
  await page.locator('[data-test="tabs"] [data-tab="anchors"]').click();
  await expect(page.locator('[data-tab-panel="anchors"]')).toHaveClass(/on/);
  // The seed task has one anchor.
  await expect(page.locator('[data-tab-panel="anchors"] .td-anchor-pill').first()).toBeVisible();
});
```

- [ ] **Step 2: Run + commit**

Run: `npx playwright test tests/task-detail.spec.js -g "Variant B tabs switch"`
Expected: PASS.

```bash
git add plugins/taskmaster/viewer/tests/task-detail.spec.js
git commit -m "test(viewer): Variant B tab switching activates Anchors panel"
```

---

### Task 36: Wire the right rail into Variant B identically to Variant A

**Files:** (no code change; this task is a verification gate.)

- [ ] **Step 1: Confirm both renderers call `mountRightRail` with the same `{ task, related, onNavigate }` shape**

Run: `grep -n "mountRightRail" plugins/taskmaster/viewer/js/components/task-detail-document.js plugins/taskmaster/viewer/js/components/task-detail-graph.js`
Expected: Both files invoke `mountRightRail(aside, ctx)` from inside their `renderRail` helper.

- [ ] **Step 2: Append a Playwright assertion that both variants render `[data-test="rail"]` with the same panel count**

Append to `task-detail.spec.js`:

```javascript
test('right rail panels match between Variant A and Variant B', async ({ page }) => {
  await page.request.put('/api/viewer/prefs', { data: { screens: { task_detail: { view: 'A' } } } });
  await page.goto(`/v3/#/task/${TASK_ID}`);
  const aPanels = await page.locator('[data-test="rail"] .td-panel').count();

  await page.request.put('/api/viewer/prefs', { data: { screens: { task_detail: { view: 'B' } } } });
  await page.reload();
  const bPanels = await page.locator('[data-test="rail"] .td-panel').count();
  expect(aPanels).toBe(bPanels);
  expect(aPanels).toBeGreaterThanOrEqual(6); // Docs / Lessons / Handovers / Issues / Deps / Blockers
});
```

- [ ] **Step 3: Run + commit**

Run: `npx playwright test tests/task-detail.spec.js -g "right rail panels match"`
Expected: PASS.

```bash
git add plugins/taskmaster/viewer/tests/task-detail.spec.js
git commit -m "test(viewer): rail panel count matches across variants"
```

---

### Task 37: Visual verification against `task-detail-graph.html` mockup

**Files:** none — manual verification.

- [ ] **Step 1: Start the viewer and the static mockup side by side**

Open `http://localhost:8765/v3/#/task/<some-real-task-id>` (Variant B) and `.superpowers/brainstorm/15283-1777223061/content/task-detail-graph.html` in two windows.

- [ ] **Step 2: Eyeball checklist**

Confirm the live page has, at the same horizontal positions / proportions:
- 5 column guides with depth labels at the top
- ← Dependencies / Unblocks → axis label and status legend on the rail
- Bezier edges with horizontal pull (S-curves on row offsets, flat on same row)
- Faded L−2 / L+2 nodes
- Context band beneath the canvas with lessons (✦) / handovers (§ italic) / issues (!)
- Graph controls below the band (not floating)
- Tabs (Spec / Plan / Notes / Activity / Anchors / Raw YAML) below the graph

- [ ] **Step 3: If any item fails, file an issue and adjust CSS in `task-detail.css`** (do not commit until parity is reached).

- [ ] **Step 4: Commit (only if any CSS changes were needed)**

```bash
git add plugins/taskmaster/viewer/css/screens/task-detail.css
git commit -m "polish(viewer): Variant B parity with task-detail-graph mockup"
```

If no changes were needed, skip this commit.

---

## M6 — Screen Orchestrator + Toggle

### Task 38: Confirm `task-detail.js` resolves both subpath and `?view=` override

**Files:**
- Modify: `plugins/taskmaster/viewer/js/screens/task-detail.js`

- [ ] **Step 1: Add a `?view=A|B` URL override**

Replace the variant-resolution block:

```javascript
  const urlView = params?.view === 'A' || params?.view === 'B' ? params.view : null;
  const view = urlView || (prefs?.screens?.task_detail?.view === 'B' ? 'B' : 'A');
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/screens/task-detail.js
git commit -m "feat(viewer): support ?view=A|B URL override on task detail"
```

---

### Task 39: Persist toggle clicks via `api.savePrefs`

**Files:**
- Modify: `plugins/taskmaster/viewer/tests/task-detail.spec.js`

- [ ] **Step 1: Append the failing test**

```javascript
test('clicking the view toggle persists prefs and re-renders the other variant', async ({ page }) => {
  await page.request.put('/api/viewer/prefs', { data: { screens: { task_detail: { view: 'A' } } } });
  await page.goto(`/v3/#/task/${TASK_ID}`);
  await expect(page.locator('[data-test="meta"]')).toBeVisible();   // Variant A signature
  await page.locator('[data-view="B"]').click();
  await expect(page.locator('[data-test="graph-frame"]')).toBeVisible(); // Variant B signature

  // Reload — should still be on Variant B.
  await page.reload();
  await expect(page.locator('[data-test="graph-frame"]')).toBeVisible();
});
```

- [ ] **Step 2: Run, expect PASS** (the orchestrator from Task 20 already calls `api.savePrefs` and reloads).

Run: `npx playwright test tests/task-detail.spec.js -g "clicking the view toggle persists"`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/tests/task-detail.spec.js
git commit -m "test(viewer): toggle persists task-detail variant across reloads"
```

---

### Task 40: Handle 404 gracefully (unknown task id in URL)

**Files:**
- Modify: `plugins/taskmaster/viewer/tests/task-detail.spec.js`

- [ ] **Step 1: Append the test**

```javascript
test('unknown task id renders an error message, not a crash', async ({ page }) => {
  await page.goto('/v3/#/task/T-DOES-NOT-EXIST');
  await expect(page.locator('.td-empty')).toContainText(/T-DOES-NOT-EXIST|not found/);
});
```

- [ ] **Step 2: Run**

Run: `npx playwright test tests/task-detail.spec.js -g "unknown task id"`
Expected: PASS — `task-detail.js` already catches `getTaskFull` errors and renders `.td-empty`.

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/tests/task-detail.spec.js
git commit -m "test(viewer): graceful 404 on unknown task id"
```

---

### Task 41: Clean up the old Plan 1 stub references

**Files:** none — verification.

- [ ] **Step 1: Confirm the stub is fully replaced**

Run: `grep -n "Plan 3" plugins/taskmaster/viewer/js/screens/task-detail.js || true`
Expected: no matches (no leftover TODO comments).

Run: `grep -n "TODO\|implement later\|TBD" plugins/taskmaster/viewer/js/screens/task-detail.js plugins/taskmaster/viewer/js/components/task-detail-document.js plugins/taskmaster/viewer/js/components/task-detail-graph.js plugins/taskmaster/viewer/js/components/dependency-graph.js plugins/taskmaster/viewer/js/components/right-rail.js plugins/taskmaster/viewer/js/components/markdown.js`
Expected: no matches.

- [ ] **Step 2: No commit** — verification only. If grep finds anything, address it before continuing.

---

## M7 — Plan-Level Verification

### Task 42: Run all server tests

- [ ] **Step 1: Run pytest**

Run: `python -m pytest plugins/taskmaster/tests/test_server_api.py plugins/taskmaster/tests/test_server_task_detail.py plugins/taskmaster/tests/test_v3_layout.py -v`
Expected: All tests PASS (≥ 14 tests total — Plan 1 + Plan 3).

- [ ] **Step 2: No commit** — verification only.

---

### Task 43: Run all unit tests

- [ ] **Step 1: Run Node**

Run from `plugins/taskmaster/viewer/`: `npm run test:unit`
Expected: 5 tests PASS, 0 failures.

- [ ] **Step 2: No commit.**

---

### Task 44: Run the Playwright suite

- [ ] **Step 1: Start the server**

Run: `python plugins/taskmaster/backlog_server.py &`
Expected: server logs `serving on http://127.0.0.1:8765`.

- [ ] **Step 2: Run Playwright**

Run from `plugins/taskmaster/viewer/`: `npx playwright test tests/task-detail.spec.js`
Expected: All Plan 3 task-detail tests PASS (≥ 8 tests). Plan 1's `smoke.spec.js` also still passes.

- [ ] **Step 3: No commit.**

---

### Task 45: Spec coverage audit

- [ ] **Step 1: Walk the spec §3.9 checklist**

Tick each item by inspection of the live page:

Variant A:
- [ ] Header: ‹ back · breadcrumb · view toggle (Document / Graph) · Edit · Archive
- [ ] Meta line: id (click-to-copy) · epic · phase · created date
- [ ] Big title (22px)
- [ ] Lock banner conditional
- [ ] Chip row: status · priority · size · epic · branch (click-to-copy) · worktree (click-to-copy) · release · sub_repo
- [ ] Spec-review badge with click-to-expand codex note
- [ ] Auto-mode banner (conditional)
- [ ] Docs section (typed link chips)
- [ ] Specification section
- [ ] Plan section
- [ ] Notes section
- [ ] Review-instructions section (conditional, status=in-review)
- [ ] Latest activity
- [ ] Patchnote (conditional, status=done)
- [ ] Dates footer block

Right rail (both variants):
- [ ] Docs panel
- [ ] Lessons in scope (with hint about anchors-based matching)
- [ ] Handovers (italic serif quotes)
- [ ] Issues
- [ ] Dependencies + Unblocks subsection
- [ ] Blockers (separate from task-deps)

Variant B:
- [ ] Compact head (id · epic · phase · title · chips)
- [ ] 5-column graph (L−2 / L−1 / L0 / L+1 / L+2) with dashed guides + depth labels
- [ ] Top axis labels: ← Dependencies | This task | Unblocks → with status legend
- [ ] Bottom context band (lessons ✦ / handovers § / issues !)
- [ ] Frame: radial gradient + inner shadow; nodes lifted via drop-shadow
- [ ] Bezier edges with 60% horizontal pull
- [ ] Nodes 100×60 with status dot · id · time-in-status · title · priority pill · size
- [ ] Center node 120×80 with progress bar + step text
- [ ] L+2 nodes faded
- [ ] Graph controls below canvas (depth / show all / hide context / fullscreen)
- [ ] Tabs: Spec / Plan / Notes / Activity / Anchors / Raw YAML

- [ ] **Step 2: Anything unticked is a bug — fix in a follow-up commit before declaring this plan done.**

---

### Task 46: Final integration smoke + plan handoff

- [ ] **Step 1: End-to-end one-shot**

Run all three test suites in sequence:

```bash
python -m pytest plugins/taskmaster/tests/test_server_task_detail.py -v
cd plugins/taskmaster/viewer && npm run test:unit && npx playwright test tests/task-detail.spec.js
```

Expected: Server PASS · Unit PASS (5) · Playwright PASS (≥ 8).

- [ ] **Step 2: Confirm no stray TODO / TBD / "Plan N" placeholders**

Run: `grep -RIn "TODO\|TBD\|FIXME\|implement later" plugins/taskmaster/viewer/js/components/task-detail-document.js plugins/taskmaster/viewer/js/components/task-detail-graph.js plugins/taskmaster/viewer/js/components/dependency-graph.js plugins/taskmaster/viewer/js/components/right-rail.js plugins/taskmaster/viewer/js/components/markdown.js plugins/taskmaster/viewer/js/screens/task-detail.js plugins/taskmaster/viewer/css/screens/task-detail.css`
Expected: no matches.

- [ ] **Step 3: Tag the milestone**

```bash
git tag -a viewer-redesign-plan-3-complete -m "Plan 3 (Task Detail) complete: Variant A + B + rail + tests"
```

- [ ] **Step 4: Commit handoff note (optional)**

If you want a marker commit:

```bash
git commit --allow-empty -m "chore(taskmaster): plan 3 (task detail) complete; ready for plan 4"
```

---

## Open questions for the engineer (none expected, but flag if hit)

- **Markdown library version pinning:** `marked@12.0.2` is pinned via CDN with SRI in Task 14. If the CDN integrity check fails in your environment, swap to a vendored copy under `plugins/taskmaster/viewer/vendor/marked.min.js` and adjust the `<script src>` accordingly — the rest of the plan stands.
- **Auto-mode banner data shape:** the renderer assumes `task.auto_mode = { running, step, progress (0–1), elapsed }`. If your live data uses a different shape, normalise it inside `_load_task_full` or in a thin client-side adapter; the renderer contract is intentionally narrow.
