# Spec C1a — Epics & Phases as Doc-Bearing Entities (backend) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Promote epics and phases to first-class doc-bearing entities (their own `epics/<id>.md` / `phases/<id>.md` body files), add an epic `components` block that tasks bind to via a `component` field, derive an epic rollup + risk surface, and add a `design_status` maturity lock with light teeth.

**Architecture:** Mirror the existing task two-tier storage. `taskmaster_v3.py` already has generic `read_task_file`/`write_task_file` (Path-based, reused by handovers); only `task_file_path` is task-specific. We add `epic_file_path`/`phase_file_path` + a generic `_split_entity_for_v3`/`_merge_entity_from_v3`, then hook epics/phases into `load_v3`/`save_v3` (which currently pass them through untouched). MCP tools in `backlog_server.py` follow the `@mcp.tool()` → `_load()` → mutate → `_mutate_and_save()` → return-`str` pattern. Rollup mirrors the existing `_phase_stats`/`backlog_phase_status`.

**Tech Stack:** Python 3, FastMCP (`@mcp.tool()`), PyYAML, pytest. Two files: `plugins/taskmaster/taskmaster_v3.py` (framework-free storage lib) and `plugins/taskmaster/backlog_server.py` (live MCP server, imports the lib). Tests in `plugins/taskmaster/tests/`.

**Scope guardrails:**
- This is the **backend** half of Spec C1. The viewer epic screen is **Plan C1b** (separate; Playwright + Reality Reprojection design system).
- Gate-completion in the rollup is **deferred to Spec A** (gates don't exist yet); the rollup ships with status counts + component + merge-ladder-less progress. Where the spec mentions gate-completion, this plan emits status-only and leaves a clearly-named extension point.
- Run all tests from the repo root: `python -m pytest plugins/taskmaster/tests/ -q`.
- Branch off a clean base **after** `fix/bughunt-2026-05-26` lands (Gate D blast-radius warning in the spec).

**Reference (verbatim ground truth used by this plan):**
- `taskmaster_v3.py`: `SLIM_FIELDS` (110), `HEAVY_FIELDS` (412), `CANONICAL_SECTIONS` (58), `BODY_KEY` (422), `task_file_path` (734), `_split_task_for_v3` (743), `_merge_task_from_v3` (769), `read_task_file` (398), `write_task_file` (403), `resolve_sections` (193), `load_v3` (780), `save_v3` (4289), `atomic_write` (42).
- `backlog_server.py`: import block (56–162), `VALID_DOC_KEYS` (5079), `backlog_update_task` chain (5082–5251, escape hatch at 5236), `VALID_STATUSES` (5077), `backlog_set_spec_review` (5257), `backlog_add_epic` (5435), `backlog_update_epic` (5339), `VALID_EPIC_STATUSES`/`ALLOWED_EPIC_FIELDS` (5335–5336), `backlog_phase_status` (5627) using `_phase_stats`, `backlog_add_phase` (5480), `ALLOWED_PHASE_FIELDS` (5477), `_find_epic`/`_find_phase`/`_find_task` helpers.

---

## Phase 1 — Body-file storage for epics & phases

### Task 1: Storage constants + path helpers

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py` (constants near lines 110/412/58; path helpers after line 740)
- Test: `plugins/taskmaster/tests/test_epic_phase_bodies.py` (new)

- [ ] **Step 1: Write the failing test**

```python
# plugins/taskmaster/tests/test_epic_phase_bodies.py
from pathlib import Path
import taskmaster_v3 as v3


def test_entity_constants_present():
    assert v3.EPIC_HEAVY_FIELDS == ("description", "docs", "components")
    assert v3.PHASE_HEAVY_FIELDS == ("description", "docs")
    assert "epic" in v3.SLIM_FIELDS and "phase" in v3.SLIM_FIELDS
    assert "epic" in v3.CANONICAL_SECTIONS and "phase" in v3.CANONICAL_SECTIONS


def test_entity_file_paths():
    bp = Path("/proj/.taskmaster/backlog.yaml")
    assert v3.epic_file_path(bp, "asset-engine") == Path("/proj/.taskmaster/epics/asset-engine.md")
    assert v3.phase_file_path(bp, "ship-v3") == Path("/proj/.taskmaster/phases/ship-v3.md")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest plugins/taskmaster/tests/test_epic_phase_bodies.py -q`
Expected: FAIL with `AttributeError: module 'taskmaster_v3' has no attribute 'EPIC_HEAVY_FIELDS'`.

- [ ] **Step 3: Add the constants**

In `taskmaster_v3.py`, immediately after `HEAVY_FIELDS` (ends line 417), add:

```python
EPIC_HEAVY_FIELDS: tuple[str, ...] = ("description", "docs", "components")
PHASE_HEAVY_FIELDS: tuple[str, ...] = ("description", "docs")
```

In the `SLIM_FIELDS` dict literal (line 110), add two entries (before the closing `}`):

```python
    "epic": ("id", "name", "status", "design_status", "created"),
    "phase": ("id", "name", "status", "order", "created",
              "target_date", "start_date", "completed", "deliverables"),
```

In the `CANONICAL_SECTIONS` dict literal (line 58), add two entries:

```python
    "epic": ("notes", "design", "spec", "roadmap", "analysis"),
    "phase": ("notes", "design", "roadmap"),
```

- [ ] **Step 4: Add the path helpers**

After `task_file_path` (ends line 740), add:

```python
def epic_file_path(backlog_path: Path, epic_id: str) -> Path:
    """Per-epic file path: .taskmaster/backlog.yaml -> .taskmaster/epics/<id>.md."""
    return backlog_path.parent / "epics" / f"{epic_id}.md"


def phase_file_path(backlog_path: Path, phase_id: str) -> Path:
    """Per-phase file path: .taskmaster/backlog.yaml -> .taskmaster/phases/<id>.md."""
    return backlog_path.parent / "phases" / f"{phase_id}.md"
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest plugins/taskmaster/tests/test_epic_phase_bodies.py -q`
Expected: PASS (2 tests).

- [ ] **Step 6: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_epic_phase_bodies.py
git commit -m "feat(taskmaster): epic/phase storage constants + path helpers (C1a)"
```

---

### Task 2: Generic entity split/merge

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py` (after `_merge_task_from_v3`, line 777)
- Test: `plugins/taskmaster/tests/test_epic_phase_bodies.py`

- [ ] **Step 1: Write the failing test**

```python
def test_split_merge_epic_roundtrip():
    epic = {
        "id": "asset-engine", "name": "Asset Engine", "status": "active",
        "design_status": "locked", "created": "2026-05-27",
        "description": "Ingest + thumbnail + CDN.",
        "docs": {"design": "specs/asset-engine.md"},
        "components": {"ingest": {"title": "Ingest", "after": []}},
        "_body": "# Asset Engine\n\nWhat we are building.\n",
    }
    slim, heavy, body = v3._split_entity_for_v3(epic, v3.EPIC_HEAVY_FIELDS)
    # slim keeps glance fields, heavy holds the doc-bearing fields
    assert slim["id"] == "asset-engine" and slim["design_status"] == "locked"
    assert "description" not in slim and "components" not in slim
    assert heavy["description"].startswith("Ingest")
    assert heavy["components"]["ingest"]["title"] == "Ingest"
    assert body.startswith("# Asset Engine")
    # frontmatter mirrors id+title for human readability
    assert heavy["id"] == "asset-engine" and heavy["title"] == "Asset Engine"
    # merge restores everything except the readability-only title mirror
    merged = v3._merge_entity_from_v3(slim, heavy, body, v3.EPIC_HEAVY_FIELDS)
    assert merged["description"].startswith("Ingest")
    assert merged["components"]["ingest"]["title"] == "Ingest"
    assert merged["_body"].startswith("# Asset Engine")
    assert "title" not in merged  # epics use `name`, not `title`
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest plugins/taskmaster/tests/test_epic_phase_bodies.py::test_split_merge_epic_roundtrip -q`
Expected: FAIL with `AttributeError: ... has no attribute '_split_entity_for_v3'`.

- [ ] **Step 3: Implement the generic split/merge**

After `_merge_task_from_v3` (ends line 777), add:

```python
def _split_entity_for_v3(
    entity: dict[str, Any], heavy_fields: tuple[str, ...]
) -> tuple[dict[str, Any], dict[str, Any], str]:
    """Generic version of _split_task_for_v3 for any entity kind.

    Returns (slim, heavy_fm, body). Mirrors id + a display title into the
    frontmatter for human readability (epics/phases use `name`, tasks `title`).
    """
    slim: dict[str, Any] = {}
    heavy: dict[str, Any] = {}
    body = ""
    for key, value in entity.items():
        if key == BODY_KEY:
            body = value or ""
        elif key in heavy_fields:
            if value not in (None, "", [], {}):
                heavy[key] = value
        else:
            slim[key] = value
    if "id" in slim:
        heavy.setdefault("id", slim["id"])
    display = slim.get("name") or slim.get("title")
    if display:
        heavy.setdefault("title", display)
    return slim, heavy, body


def _merge_entity_from_v3(
    slim: dict[str, Any], heavy_fm: dict[str, Any], body: str, heavy_fields: tuple[str, ...]
) -> dict[str, Any]:
    """Reverse of _split_entity_for_v3. Only pulls declared heavy_fields back
    (the id/title frontmatter mirror is readability-only and ignored)."""
    merged = dict(slim)
    for key in heavy_fields:
        if key in heavy_fm:
            merged[key] = heavy_fm[key]
    if body:
        merged[BODY_KEY] = body
    return merged
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest plugins/taskmaster/tests/test_epic_phase_bodies.py::test_split_merge_epic_roundtrip -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_epic_phase_bodies.py
git commit -m "feat(taskmaster): generic entity split/merge for v3 storage (C1a)"
```

---

### Task 3: Hook epics & phases into `save_v3`

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py` (`save_v3`, lines 4289–4314)
- Test: `plugins/taskmaster/tests/test_epic_phase_bodies.py`

- [ ] **Step 1: Write the failing test**

```python
import yaml

def _seed_backlog(tmp_path):
    bp = tmp_path / ".taskmaster" / "backlog.yaml"
    bp.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "version": 3, "project": "t",
        "meta": {"updated": "", "schema_version": 3},
        "epics": [{
            "id": "asset-engine", "name": "Asset Engine", "status": "active",
            "description": "Ingest + thumbnail.", "created": "2026-05-27",
            "tasks": [{"id": "ae-1", "title": "Ingest task", "status": "todo"}],
        }],
        "phases": [{
            "id": "ship-v3", "name": "Ship V3", "status": "active", "order": 1,
            "description": "Wrap up.", "created": "2026-05-27",
        }],
        "context": {},
    }
    bp.write_text(yaml.safe_dump(data), encoding="utf-8")
    return bp

def test_save_v3_writes_epic_and_phase_bodies(tmp_path):
    bp = _seed_backlog(tmp_path)
    data = v3.load_v3(bp)
    v3.save_v3(bp, data)
    # heavy fields moved out to per-entity .md files
    epic_md = v3.epic_file_path(bp, "asset-engine")
    phase_md = v3.phase_file_path(bp, "ship-v3")
    assert epic_md.exists() and "Ingest + thumbnail." in epic_md.read_text(encoding="utf-8")
    assert phase_md.exists() and "Wrap up." in phase_md.read_text(encoding="utf-8")
    # backlog.yaml slim epic no longer carries description inline
    slim = yaml.safe_load(bp.read_text(encoding="utf-8"))
    assert "description" not in slim["epics"][0]
    assert slim["epics"][0]["id"] == "asset-engine"
    assert slim["epics"][0]["tasks"][0]["id"] == "ae-1"
    assert "description" not in slim["phases"][0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest plugins/taskmaster/tests/test_epic_phase_bodies.py::test_save_v3_writes_epic_and_phase_bodies -q`
Expected: FAIL — `description` still present inline in `slim["epics"][0]` (current `save_v3` copies epic metadata verbatim).

- [ ] **Step 3: Rewrite `save_v3`**

Replace the body of `save_v3` (lines 4296–4314, from `slim_data: dict... = {**data}` through the final `atomic_write(...)`) with:

```python
    slim_data: dict[str, Any] = {**data}
    slim_data["epics"] = []
    for epic in data.get("epics", []):
        tasks = epic.get("tasks", [])
        epic_meta = {k: v for k, v in epic.items() if k != "tasks"}
        slim_meta, epic_heavy, epic_body = _split_entity_for_v3(epic_meta, EPIC_HEAVY_FIELDS)
        eid = slim_meta.get("id")
        if eid and (any(k in epic_heavy for k in EPIC_HEAVY_FIELDS) or epic_body):
            write_task_file(epic_file_path(backlog_path, eid), epic_heavy, epic_body)
        slim_epic = {**slim_meta, "tasks": []}
        for task in tasks:
            slim_task, heavy_fm, body = _split_task_for_v3(task)
            slim_epic["tasks"].append(slim_task)
            tid = slim_task.get("id")
            if not tid:
                continue
            if any(k in heavy_fm for k in HEAVY_FIELDS) or bool(body):
                write_task_file(task_file_path(backlog_path, tid), heavy_fm, body)
        slim_data["epics"].append(slim_epic)

    if "phases" in slim_data:
        slim_phases: list[dict[str, Any]] = []
        for phase in data.get("phases", []):
            slim_phase, phase_heavy, phase_body = _split_entity_for_v3(phase, PHASE_HEAVY_FIELDS)
            pid = slim_phase.get("id")
            if pid and (any(k in phase_heavy for k in PHASE_HEAVY_FIELDS) or phase_body):
                write_task_file(phase_file_path(backlog_path, pid), phase_heavy, phase_body)
            slim_phases.append(slim_phase)
        slim_data["phases"] = slim_phases

    atomic_write(
        backlog_path,
        yaml.dump(slim_data, default_flow_style=False, sort_keys=False, allow_unicode=True),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest plugins/taskmaster/tests/test_epic_phase_bodies.py::test_save_v3_writes_epic_and_phase_bodies -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_epic_phase_bodies.py
git commit -m "feat(taskmaster): split epic/phase heavy fields into body files on save (C1a)"
```

---

### Task 4: Hook epics & phases into `load_v3`

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py` (`load_v3`, lines 780–804)
- Test: `plugins/taskmaster/tests/test_epic_phase_bodies.py`

- [ ] **Step 1: Write the failing test**

```python
def test_load_v3_merges_epic_and_phase_bodies(tmp_path):
    bp = _seed_backlog(tmp_path)
    # round-trip: save splits to .md, then a fresh load must recombine
    v3.save_v3(bp, v3.load_v3(bp))
    data = v3.load_v3(bp)
    epic = data["epics"][0]
    assert epic["description"].startswith("Ingest + thumbnail.")
    assert epic["tasks"][0]["id"] == "ae-1"           # tasks still merged
    phase = data["phases"][0]
    assert phase["description"].startswith("Wrap up.")

def test_load_v3_backward_compat_inline_description(tmp_path):
    # An old backlog with inline epic description and NO .md file must still load.
    bp = _seed_backlog(tmp_path)
    data = v3.load_v3(bp)
    assert data["epics"][0]["description"].startswith("Ingest + thumbnail.")
    assert not v3.epic_file_path(bp, "asset-engine").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest plugins/taskmaster/tests/test_epic_phase_bodies.py::test_load_v3_merges_epic_and_phase_bodies -q`
Expected: FAIL — after save splits `description` out to `epics/asset-engine.md`, the current `load_v3` never reads it back, so `epic["description"]` is missing → `KeyError`.

- [ ] **Step 3: Extend `load_v3`**

In `load_v3`, the current body ends with the epics-tasks loop then `return data` (line 803). Replace the final `return data` with the epic/phase merge passes:

```python
    # Merge per-epic heavy bodies (doc-bearing epics)
    for epic in data.get("epics", []):
        eid = epic.get("id")
        if not eid:
            continue
        ef = epic_file_path(backlog_path, eid)
        if ef.exists():
            fm, body = read_task_file(ef)
            epic_meta = {k: v for k, v in epic.items() if k != "tasks"}
            merged = _merge_entity_from_v3(epic_meta, fm, body, EPIC_HEAVY_FIELDS)
            merged["tasks"] = epic.get("tasks", [])
            epic.clear()
            epic.update(merged)

    # Merge per-phase heavy bodies
    for phase in data.get("phases", []):
        pid = phase.get("id")
        if not pid:
            continue
        pf = phase_file_path(backlog_path, pid)
        if pf.exists():
            fm, body = read_task_file(pf)
            merged = _merge_entity_from_v3(phase, fm, body, PHASE_HEAVY_FIELDS)
            phase.clear()
            phase.update(merged)

    return data
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest plugins/taskmaster/tests/test_epic_phase_bodies.py -q`
Expected: PASS (all tests, including backward-compat).

- [ ] **Step 5: Run the full suite to check for regressions**

Run: `python -m pytest plugins/taskmaster/tests/ -q`
Expected: PASS (existing task/handover tests unaffected — they go through the same round-trip).

- [ ] **Step 6: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_epic_phase_bodies.py
git commit -m "feat(taskmaster): merge epic/phase body files on load; backward-compat (C1a)"
```

---

### Task 5: Migration via existing mutation path (verification)

**Files:**
- Test: `plugins/taskmaster/tests/test_epic_phase_bodies.py`

No new code — migration is emergent: any `_mutate_and_save` (which calls `save_v3`) now splits epic/phase heavy fields to `.md`. This task proves an existing inline-description backlog migrates on the next mutation and that nothing is lost.

- [ ] **Step 1: Write the failing/guard test**

```python
def test_existing_backlog_migrates_on_first_save(tmp_path):
    bp = _seed_backlog(tmp_path)                 # inline description, no .md
    assert not v3.epic_file_path(bp, "asset-engine").exists()
    # simulate any field mutation going through load -> save
    data = v3.load_v3(bp)
    data["epics"][0]["status"] = "done"
    v3.save_v3(bp, data)
    assert v3.epic_file_path(bp, "asset-engine").exists()
    reloaded = v3.load_v3(bp)
    assert reloaded["epics"][0]["status"] == "done"
    assert reloaded["epics"][0]["description"].startswith("Ingest")
```

- [ ] **Step 2: Run to verify it passes immediately (behavior already implemented in Tasks 3–4)**

Run: `python -m pytest plugins/taskmaster/tests/test_epic_phase_bodies.py::test_existing_backlog_migrates_on_first_save -q`
Expected: PASS. (If it fails, Tasks 3–4 are incomplete — fix there, not here.)

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/tests/test_epic_phase_bodies.py
git commit -m "test(taskmaster): verify epic/phase auto-migrate to body files on mutation (C1a)"
```

---

## Phase 2 — Components block + `component` task field

### Task 6: Epic `components` + `design_status` fields in `backlog_update_epic`

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py` (`ALLOWED_EPIC_FIELDS` line 5336; add `VALID_DESIGN_STATUSES`; `backlog_update_epic` body 5339–5393; add `_validate_components` helper)
- Test: `plugins/taskmaster/tests/test_components.py` (new)

- [ ] **Step 1: Write the failing test**

```python
# plugins/taskmaster/tests/test_components.py
import json
import yaml
from backlog_server import backlog_add_epic, backlog_update_epic, _load

def _epic(data, eid):
    return next(e for e in data["epics"] if e["id"] == eid)

def test_set_components_block(tmp_taskmaster):
    backlog_add_epic("asset-engine", "Asset Engine")
    val = json.dumps({"ingest": {"title": "Ingest", "after": []},
                      "thumb": {"title": "Thumbnailer", "after": ["ingest"]}})
    out = backlog_update_epic("asset-engine", "components", val)
    assert "Error" not in out
    data = _load()
    comps = _epic(data, "asset-engine")["components"]
    assert comps["thumb"]["after"] == ["ingest"]

def test_components_reject_unknown_after(tmp_taskmaster):
    backlog_add_epic("asset-engine", "Asset Engine")
    val = json.dumps({"thumb": {"title": "T", "after": ["nope"]}})
    out = backlog_update_epic("asset-engine", "components", val)
    assert "Error" in out and "nope" in out

def test_design_status_field(tmp_taskmaster):
    backlog_add_epic("asset-engine", "Asset Engine")
    assert "Error" not in backlog_update_epic("asset-engine", "design_status", "locked")
    assert _epic(_load(), "asset-engine")["design_status"] == "locked"
    assert "Error" in backlog_update_epic("asset-engine", "design_status", "bogus")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest plugins/taskmaster/tests/test_components.py -q`
Expected: FAIL — `components`/`design_status` not in `ALLOWED_EPIC_FIELDS` → "field not allowed".

- [ ] **Step 3: Add constants + validator**

In `backlog_server.py`, change `ALLOWED_EPIC_FIELDS` (line 5336) and add `VALID_DESIGN_STATUSES` just below it:

```python
ALLOWED_EPIC_FIELDS = {"name", "status", "description", "docs", "components", "design_status"}
VALID_DESIGN_STATUSES = {"exploring", "proposed", "locked", "revising"}
```

Add a module-level validator near the other epic helpers (e.g. just above `backlog_update_epic`, line 5339):

```python
def _validate_components(components: dict) -> str:
    """Return '' if the components block is well-formed, else an error string.

    Shape: { <key>: { "title": str, "after": [<other keys>] } }.
    `after` edges must reference declared component keys (DAG not enforced here).
    """
    if not isinstance(components, dict):
        return "Error: components must be a JSON object {key: {title, after}}"
    keys = set(components)
    for key, spec in components.items():
        if not isinstance(spec, dict):
            return f"Error: component `{key}` must be an object with title/after"
        if "title" in spec and not isinstance(spec["title"], str):
            return f"Error: component `{key}` title must be a string"
        after = spec.get("after", [])
        if not isinstance(after, list):
            return f"Error: component `{key}` after must be a list of component keys"
        for ref in after:
            if ref not in keys:
                return f"Error: component `{key}` after references unknown component `{ref}`"
    return ""
```

- [ ] **Step 4: Handle the new fields in `backlog_update_epic`**

In `backlog_update_epic`, after the `if field == "docs":` block (ends line 5388, before the final `old_value = epic.get(field, "")` at 5390), insert:

```python
    if field == "components":
        try:
            parsed = json.loads(value)
        except (ValueError, TypeError):
            return "Error: components value must be a JSON object {key: {title, after}}"
        err = _validate_components(parsed)
        if err:
            return err
        epic["components"] = parsed
        _mutate_and_save(data)
        return f"Updated epic `{epic_id}` components ({len(parsed)} declared)"

    if field == "design_status":
        if value not in VALID_DESIGN_STATUSES:
            return f"Error: invalid design_status `{value}`. Valid: {', '.join(sorted(VALID_DESIGN_STATUSES))}"
        epic["design_status"] = value
        _mutate_and_save(data)
        return f"Updated epic `{epic_id}` design_status → `{value}`"
```

(`json` is already imported in `backlog_server.py` — it's used by `backlog_update_phase`'s deliverables branch.)

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest plugins/taskmaster/tests/test_components.py -q`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_components.py
git commit -m "feat(taskmaster): epic components block + design_status field (C1a)"
```

---

### Task 7: `component` task field

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py` (`ALLOWED_FIELDS` line 5076; `backlog_update_task` chain, add branch before the `else` escape hatch at line 5235)
- Modify: `plugins/taskmaster/taskmaster_v3.py` (`SLIM_FIELDS["task"]`, line 111 — add `"component"`)
- Test: `plugins/taskmaster/tests/test_components.py`

- [ ] **Step 1: Write the failing test**

```python
from backlog_server import backlog_add_task, backlog_update_task, backlog_get_task

def test_bind_task_to_component(tm_epic_phase):
    # tm_epic_phase pre-creates epic "test-epic" + phase "dev"
    val = json.dumps({"core": {"title": "Core", "after": []}})
    backlog_update_epic("test-epic", "components", val)
    backlog_add_task(epic="test-epic", task_id="T-1", title="X", phase="dev")
    assert "Error" not in backlog_update_task("T-1", "component", "core")
    data = _load()
    t = next(t for e in data["epics"] for t in e.get("tasks", []) if t["id"] == "T-1")
    assert t["component"] == "core"

def test_bind_unknown_component_rejected(tm_epic_phase):
    backlog_update_epic("test-epic", "components", json.dumps({"core": {"title": "Core"}}))
    backlog_add_task(epic="test-epic", task_id="T-2", title="Y", phase="dev")
    out = backlog_update_task("T-2", "component", "ghost")
    assert "Error" in out and "ghost" in out

def test_clear_component(tm_epic_phase):
    backlog_update_epic("test-epic", "components", json.dumps({"core": {"title": "Core"}}))
    backlog_add_task(epic="test-epic", task_id="T-3", title="Z", phase="dev")
    backlog_update_task("T-3", "component", "core")
    assert "Error" not in backlog_update_task("T-3", "component", "")
    t = next(t for e in _load()["epics"] for t in e.get("tasks", []) if t["id"] == "T-3")
    assert "component" not in t
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest plugins/taskmaster/tests/test_components.py -q`
Expected: FAIL — `component` not in `ALLOWED_FIELDS` → "field not allowed".

- [ ] **Step 3: Add `component` to allowed/slim fields**

In `backlog_server.py`, add `"component"` to `ALLOWED_FIELDS` (line 5076 set literal).

In `taskmaster_v3.py`, add `"component"` to the `"task"` tuple in `SLIM_FIELDS` (line 111) — e.g. after `"epic",`:

```python
        "estimate", "phase", "epic", "component",
```

- [ ] **Step 4: Add the validation branch in `backlog_update_task`**

In `backlog_update_task`, the field chain ends with `else: task[field] = value` at line 5235–5236. Insert a `component` branch immediately before that `else`:

```python
    elif field == "component":
        if value == "" or value.lower() == "none":
            task.pop("component", None)
        else:
            comps = (epic.get("components") or {})
            if value not in comps:
                declared = ", ".join(sorted(comps)) or "(none declared)"
                return (f"Error: component `{value}` not declared on epic `{epic['id']}`. "
                        f"Declared: {declared}. Add it via backlog_update_epic(<epic>, 'components', ...).")
            task["component"] = value
```

(`epic` is already in scope — `task, epic = result` at line 5148.)

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest plugins/taskmaster/tests/test_components.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_components.py
git commit -m "feat(taskmaster): component task field bound to epic components (C1a)"
```

---

### Task 8: Component rollup helper

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py` (add `_component_rollup` near `_phase_stats`)
- Test: `plugins/taskmaster/tests/test_components.py`

- [ ] **Step 1: Write the failing test**

```python
from backlog_server import _component_rollup

def test_component_rollup(tm_epic_phase):
    backlog_update_epic("test-epic", "components",
                        json.dumps({"core": {"title": "Core"}, "ui": {"title": "UI"}}))
    for tid, comp, status in [("R-1", "core", "done"), ("R-2", "core", "in-progress"),
                              ("R-3", "ui", "todo"), ("R-4", None, "todo")]:
        backlog_add_task(epic="test-epic", task_id=tid, title=tid, phase="dev")
        if comp:
            backlog_update_task(tid, "component", comp)
        backlog_update_task(tid, "status", status)
    roll = _component_rollup(_load(), "test-epic")
    assert roll["core"]["total"] == 2 and roll["core"]["done"] == 1
    assert roll["core"]["status"] == "in-progress"   # mixed -> in-progress
    assert roll["ui"]["status"] == "todo"            # nothing started
    assert roll["_unassigned"]["total"] == 1         # R-4 has no component
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest plugins/taskmaster/tests/test_components.py::test_component_rollup -q`
Expected: FAIL — `ImportError: cannot import name '_component_rollup'`.

- [ ] **Step 3: Implement `_component_rollup`**

In `backlog_server.py`, near `_phase_stats` (search for `def _phase_stats`), add:

```python
def _component_rollup(data: dict, epic_id: str) -> dict:
    """Per-component status rollup for an epic, computed on read.

    Returns { <component_key>: {total, done, in-progress, in-review, todo,
    blocked, status}, ..., "_unassigned": {...} }. Components with no tasks
    still appear (status "todo"). `status` is the node color:
      - "done"        : >0 tasks and all done/archived
      - "todo"        : no task started (all todo)
      - "blocked"     : any blocked and none in-progress/in-review
      - "in-progress" : otherwise (work underway)
    """
    epic = _find_epic(data, epic_id)
    declared = list((epic.get("components") or {}) if epic else [])
    buckets: dict[str, dict] = {}

    def _blank() -> dict:
        return {"total": 0, "done": 0, "in-progress": 0, "in-review": 0,
                "todo": 0, "blocked": 0, "archived": 0}

    for key in declared:
        buckets[key] = _blank()
    buckets["_unassigned"] = _blank()

    for t in (epic.get("tasks", []) if epic else []):
        comp = t.get("component")
        key = comp if comp in buckets else "_unassigned"
        st = t.get("status", "todo")
        b = buckets[key]
        b["total"] += 1
        if st in b:
            b[st] += 1

    for b in buckets.values():
        done = b["done"] + b["archived"]
        if b["total"] == 0:
            b["status"] = "todo"
        elif done == b["total"]:
            b["status"] = "done"
        elif b["in-progress"] == 0 and b["in-review"] == 0 and b["blocked"] > 0:
            b["status"] = "blocked"
        elif b["in-progress"] == 0 and b["in-review"] == 0 and done == 0:
            b["status"] = "todo"
        else:
            b["status"] = "in-progress"
    return buckets
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest plugins/taskmaster/tests/test_components.py::test_component_rollup -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_components.py
git commit -m "feat(taskmaster): per-component status rollup helper (C1a)"
```

---

## Phase 3 — Epic rollup + risk surface

### Task 9: `backlog_epic_status` tool

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py` (add `_epic_stats` + `@mcp.tool() backlog_epic_status`, near the phase tools ~line 5627)
- Test: `plugins/taskmaster/tests/test_epic_status.py` (new)

- [ ] **Step 1: Write the failing test**

```python
# plugins/taskmaster/tests/test_epic_status.py
import json
from backlog_server import (backlog_add_epic, backlog_add_task, backlog_update_task,
                            backlog_update_epic, backlog_epic_status)

def _setup(tm_epic_phase):
    backlog_update_epic("test-epic", "components",
                        json.dumps({"core": {"title": "Core"}}))
    for tid, status in [("E-1", "done"), ("E-2", "in-progress"), ("E-3", "todo")]:
        backlog_add_task(epic="test-epic", task_id=tid, title=tid, phase="dev")
        backlog_update_task(tid, "component", "core")
        backlog_update_task(tid, "status", status)

def test_epic_status_shows_counts_and_components(tm_epic_phase):
    _setup(tm_epic_phase)
    out = backlog_epic_status("test-epic")
    assert "test-epic" in out
    assert "1/3" in out                      # done/total progress
    assert "Core" in out or "core" in out    # component line
    assert "Components" in out

def test_epic_status_unknown(tm_epic_phase):
    out = backlog_epic_status("ghost")
    assert "Error" in out and "ghost" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest plugins/taskmaster/tests/test_epic_status.py -q`
Expected: FAIL — `ImportError: cannot import name 'backlog_epic_status'`.

- [ ] **Step 3: Implement `_epic_stats` and the tool**

In `backlog_server.py`, near `backlog_phase_status` (~5627), add:

```python
def _epic_stats(data: dict, epic_id: str) -> dict:
    """Status counts for an epic's tasks (mirrors _phase_stats)."""
    stats = {"total": 0, "done": 0, "in-progress": 0, "in-review": 0,
             "todo": 0, "blocked": 0, "archived": 0}
    epic = _find_epic(data, epic_id)
    for t in (epic.get("tasks", []) if epic else []):
        st = t.get("status", "todo")
        stats["total"] += 1
        if st in stats:
            stats[st] += 1
    return stats


@mcp.tool()
def backlog_epic_status(epic_id: str) -> str:
    """Show progress for an epic: status counts, per-component rollup, and the
    design-maturity lock. Derived on read from the epic's tasks — no stored rollup.

    Args:
        epic_id: The epic ID (e.g. "asset-engine").
    """
    data = _load()
    epic = _find_epic(data, epic_id)
    if not epic:
        return f"Error: epic `{epic_id}` not found"

    stats = _epic_stats(data, epic_id)
    roll = _component_rollup(data, epic_id)
    lines = [f"## Epic `{epic_id}` — {epic.get('name', '')}\n"]

    design = epic.get("design_status", "exploring")
    lock = " (locked)" if design == "locked" else ""
    lines.append(f"**Design:** {design}{lock}")
    lines.append(f"**Status:** {epic.get('status', 'active')}")

    done = stats["done"] + stats["archived"]
    if stats["total"]:
        pct = int(done / stats["total"] * 100)
        bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
        lines.append(f"**Progress:** {done}/{stats['total']} done")
        lines.append(f"[{bar}] {pct}%")
    lines.append(
        f"Done: {stats['done']} | In Progress: {stats['in-progress']} | "
        f"In Review: {stats['in-review']} | Todo: {stats['todo']} | Blocked: {stats['blocked']}"
    )

    glyph = {"done": "█", "in-progress": "▨", "blocked": "✗", "todo": "□"}
    lines.append("\n**Components:**")
    for key, spec in (epic.get("components") or {}).items():
        b = roll.get(key, {})
        title = (spec or {}).get("title", key)
        lines.append(f"- {glyph.get(b.get('status'), '□')} {title} "
                     f"({b.get('done', 0)}/{b.get('total', 0)})")
    if roll.get("_unassigned", {}).get("total"):
        u = roll["_unassigned"]
        lines.append(f"- · unassigned ({u['done']}/{u['total']})")

    # gate-completion rollup is appended here once Spec A lands (extension point).
    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest plugins/taskmaster/tests/test_epic_status.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_epic_status.py
git commit -m "feat(taskmaster): backlog_epic_status rollup tool (C1a)"
```

---

### Task 10: Risk / attention surface

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py` (`backlog_epic_status` — append an attention list)
- Test: `plugins/taskmaster/tests/test_epic_status.py`

Scope: bubble up **blocked tasks** and tasks carrying a `blockers` note. Open-decision and failed-gate bubbling are **deferred** (decisions have no epic link in the current schema; gates arrive in Spec A) — leave the named extension point.

- [ ] **Step 1: Write the failing test**

```python
def test_epic_status_attention_list(tm_epic_phase):
    backlog_add_task(epic="test-epic", task_id="A-1", title="blocked one", phase="dev")
    backlog_update_task("A-1", "status", "blocked")
    backlog_update_task("A-1", "blockers", "waiting on CDN creds")
    out = backlog_epic_status("test-epic")
    assert "Attention" in out
    assert "A-1" in out and "CDN creds" in out

def test_epic_status_no_attention_when_clean(tm_epic_phase):
    backlog_add_task(epic="test-epic", task_id="C-1", title="fine", phase="dev")
    out = backlog_epic_status("test-epic")
    assert "Attention" not in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest plugins/taskmaster/tests/test_epic_status.py -q`
Expected: FAIL — no "Attention" section emitted.

- [ ] **Step 3: Append the attention list**

In `backlog_epic_status`, replace the final block (the gate-completion comment + `return "\n".join(lines)`) with:

```python
    # Risk / attention surface (derived). Decision + failed-gate bubbling
    # is added in Spec A / when decisions gain an epic link (extension point).
    attention = []
    for t in epic.get("tasks", []):
        if t.get("status") == "blocked":
            why = t.get("blockers")
            attention.append(f"⏸ {t['id']} blocked" + (f": {why}" if why else ""))
        elif t.get("blockers"):
            attention.append(f"⚠ {t['id']}: {t['blockers']}")
    if attention:
        lines.append("\n**Attention:**")
        lines.extend(f"- {a}" for a in attention)

    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest plugins/taskmaster/tests/test_epic_status.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_epic_status.py
git commit -m "feat(taskmaster): epic risk/attention surface (blocked tasks) (C1a)"
```

---

## Phase 4 — Design-maturity lock (light teeth)

### Task 11: Phase docs field (parity) + epic body section resolution

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py` (`ALLOWED_PHASE_FIELDS` line 5477 — add `"docs"`; `backlog_update_phase` — add a `docs` branch)
- Test: `plugins/taskmaster/tests/test_epic_phase_bodies.py`

The spec says phases get `docs` now (today they can't). This brings phases to epic/task parity and exercises the `PHASE_HEAVY_FIELDS` `docs` storage.

- [ ] **Step 1: Write the failing test**

```python
from backlog_server import backlog_add_phase, backlog_update_phase, _load as _load_srv

def test_phase_docs_field(tmp_taskmaster):
    backlog_add_phase("ship", "Ship")
    out = backlog_update_phase("ship", "docs", "design:docs/design/ship.md")
    assert "Error" not in out
    ph = next(p for p in _load_srv()["phases"] if p["id"] == "ship")
    assert ph["docs"]["design"] == "docs/design/ship.md"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest plugins/taskmaster/tests/test_epic_phase_bodies.py::test_phase_docs_field -q`
Expected: FAIL — `docs` not in `ALLOWED_PHASE_FIELDS`.

- [ ] **Step 3: Add `docs` to phases**

In `backlog_server.py`, add `"docs"` to `ALLOWED_PHASE_FIELDS` (line 5477).

In `backlog_update_phase`, add a `docs` branch before the final `else: ph[field] = value` (line 5620–5621). Reuse the same `key:path` shape as epics/tasks:

```python
    elif field == "docs":
        if ":" not in value:
            return (f"Error: docs value must be `key:path` format "
                    f"(e.g. `design:docs/design/ship.md`). Valid keys: {', '.join(sorted(VALID_DOC_KEYS))}")
        doc_key, doc_path = (s.strip() for s in value.split(":", 1))
        if doc_key not in VALID_DOC_KEYS:
            return f"Error: invalid docs key `{doc_key}`. Valid: {', '.join(sorted(VALID_DOC_KEYS))}"
        if not isinstance(ph.get("docs"), dict):
            ph["docs"] = {}
        if doc_path == "":
            ph["docs"].pop(doc_key, None)
            if not ph["docs"]:
                ph.pop("docs", None)
        else:
            ph["docs"][doc_key] = doc_path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest plugins/taskmaster/tests/test_epic_phase_bodies.py::test_phase_docs_field -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_epic_phase_bodies.py
git commit -m "feat(taskmaster): phase docs field for epic/task parity (C1a)"
```

---

### Task 12: `design_change` flag with locked-epic teeth

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py` (`ALLOWED_FIELDS` line 5076 — add `"design_change"`; `backlog_update_task` — add branch)
- Modify: `plugins/taskmaster/taskmaster_v3.py` (`SLIM_FIELDS["task"]` — add `"design_change"`)
- Test: `plugins/taskmaster/tests/test_design_lock.py` (new)

Light teeth: flagging a task `design_change` under a `locked` epic is **rejected** with an instruction to reopen the design (set the epic to `revising`, recording a decision). Once the epic is `revising`/`exploring`/`proposed`, the flag is accepted.

- [ ] **Step 1: Write the failing test**

```python
# plugins/taskmaster/tests/test_design_lock.py
import json
from backlog_server import (backlog_add_epic, backlog_add_task, backlog_update_task,
                            backlog_update_epic, _load)

def test_design_change_blocked_when_locked(tm_epic_phase):
    backlog_update_epic("test-epic", "design_status", "locked")
    backlog_add_task(epic="test-epic", task_id="D-1", title="redesign cache", phase="dev")
    out = backlog_update_task("D-1", "design_change", "true")
    assert "Error" in out and "locked" in out.lower()
    assert "revising" in out.lower()                      # tells user how to reopen
    t = next(t for e in _load()["epics"] for t in e.get("tasks", []) if t["id"] == "D-1")
    assert "design_change" not in t                       # not set

def test_design_change_allowed_when_revising(tm_epic_phase):
    backlog_update_epic("test-epic", "design_status", "revising")
    backlog_add_task(epic="test-epic", task_id="D-2", title="redesign", phase="dev")
    assert "Error" not in backlog_update_task("D-2", "design_change", "true")
    t = next(t for e in _load()["epics"] for t in e.get("tasks", []) if t["id"] == "D-2")
    assert t["design_change"] is True

def test_design_change_clear(tm_epic_phase):
    backlog_add_task(epic="test-epic", task_id="D-3", title="x", phase="dev")
    backlog_update_task("D-3", "design_change", "true")
    backlog_update_task("D-3", "design_change", "false")
    t = next(t for e in _load()["epics"] for t in e.get("tasks", []) if t["id"] == "D-3")
    assert "design_change" not in t
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest plugins/taskmaster/tests/test_design_lock.py -q`
Expected: FAIL — `design_change` not in `ALLOWED_FIELDS`.

- [ ] **Step 3: Add the field + branch**

In `backlog_server.py`, add `"design_change"` to `ALLOWED_FIELDS` (line 5076).

In `taskmaster_v3.py`, add `"design_change"` to the `"task"` tuple in `SLIM_FIELDS` (after `"component"` from Task 7).

In `backlog_update_task`, add a branch before the `else` escape hatch (line 5235), after the `component` branch from Task 7:

```python
    elif field == "design_change":
        truthy = value.strip().lower() in ("true", "1", "yes")
        if truthy:
            design = epic.get("design_status", "exploring")
            if design == "locked":
                return (f"Error: epic `{epic['id']}` design is locked — cannot flag a "
                        f"design-change task. To reopen, set the epic to revising "
                        f"(backlog_update_epic('{epic['id']}', 'design_status', 'revising')) "
                        f"and record the reason as a decision (taskmaster:decision).")
            task["design_change"] = True
        else:
            task.pop("design_change", None)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest plugins/taskmaster/tests/test_design_lock.py -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest plugins/taskmaster/tests/ -q`
Expected: PASS (no regressions across storage, components, epic-status, design-lock).

- [ ] **Step 6: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_design_lock.py
git commit -m "feat(taskmaster): design_change flag with locked-epic teeth (C1a)"
```

---

## Self-Review

**Spec coverage (against `2026-05-27-task-epic-protocol-design.md`, Pillar 2b / Spec C1):**
- "Epics and Phases get their own body file mirroring task two-tier storage" → Tasks 1–4 (constants, split/merge, save, load).
- "Migration seeds bodies from existing description/docs" → Task 5 (emergent on first mutation; backward-compat covered in Task 4).
- "components block is the single source of truth … each task carries a `component` field" → Tasks 6–7.
- "component status is the rollup of its tasks, computed on read" → Task 8 (`_component_rollup`; on-read, never cached).
- "rollup + risk surface … status counts, % to terminal rung; attention list" → Tasks 9–10 (merge-ladder rollup is Spec B; gate-completion is Spec A — both left as named extension points, matching the spec's "coarse until Spec A lands").
- "design_status … exploring/proposed/locked/revising … explicit design-change task flag" → Tasks 6 (field) + 12 (teeth).
- "phases get body files + docs now" → Task 11.
- **Out of scope (correctly):** viewer epic screen (Plan C1b); gate-completion + merge-ladder rollup (Specs A/B).

**Placeholder scan:** none — every code step shows the full insertion with exact line anchors; every test step shows real assertions and the run command with expected output.

**Type consistency:** `_split_entity_for_v3`/`_merge_entity_from_v3` take `(entity, heavy_fields)` / `(slim, heavy_fm, body, heavy_fields)` consistently across Tasks 2–4. `_component_rollup(data, epic_id)` and `_epic_stats(data, epic_id)` share signature shape with the existing `_phase_stats(data, phase_id)`. `component` is added to both `ALLOWED_FIELDS` (server) and `SLIM_FIELDS["task"]` (lib) so it survives the slim round-trip. `design_status` values (`VALID_DESIGN_STATUSES`) are referenced identically in Tasks 6 and 12.

**Known follow-ups (named, not silent):** gate-completion rollup line in `backlog_epic_status` (Spec A); merge-ladder rollup (Spec B); decision/failed-gate bubbling in the attention list (Spec A + decision-epic link); viewer (Plan C1b).
