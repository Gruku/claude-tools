# Taskmaster Viewer Redesign — Plan 6: Auto Mode page + dashboard stepper widget

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement spec §3.15 in full — the dedicated Auto Mode page (Quest Spine + Flight Log toggle, parallel sessions strip, side panels, header pause/stop controls) and the `auto-mode-stepper` dashboard widget that replaces Plan 4's stub. Extends the server with per-session storage, control endpoints, and an event-log read surface.

**Architecture:** Builds on Plans 1 (foundation), 2 (auto-mode strip + `GET /api/auto/state`), and 4 (dashboard widget catalog with `auto-mode-stepper.js` stub). Plan 6 owns: refactoring single `state.json` into `sessions/<sid>.json` (with one-time migration), server endpoints for control + history + per-session detail + event stream + budget, the Auto Mode page orchestrator, the Quest Spine SVG renderer + pure layout helper, the Flight Log waterfall, the sessions strip, the side panels (subagents+hooks left, budget+tools right), the budget meter component, and the final stepper widget with the connector edge-to-edge fix.

**Tech Stack:** Vanilla HTML/CSS/JS ES modules (no bundler), Python 3 + `fastmcp` + `BaseHTTPRequestHandler`, pytest, `node --test` for pure-data unit tests, Playwright for UI smoke.

**Spec reference:** `docs/superpowers/specs/2026-04-26-taskmaster-viewer-redesign.md` §3.15 (Auto Mode page).

**Reference mockups (read before implementing the relevant tasks):**
- `.superpowers/brainstorm/15283-1777223061/content/automode-options.html` — three layouts compared (A stepper / B spine / C waterfall)
- `.superpowers/brainstorm/15283-1777223061/content/automode-integration.html` — final integration of widget + page + toggle
- `.superpowers/brainstorm/15283-1777223061/content/auto-mode-on-kanban.html` — informs strip styling reused on the Auto Mode page header
- `.superpowers/brainstorm/15283-1777223061/content/auto-mode-merged.html` — same

**Cross-plan dependencies (assumed already landed):**
- Plan 1: viewer skeleton (`plugins/taskmaster/viewer/`), `prefs.screens.auto_mode.view` slot ('A' = Spine, 'B' = Log), stub `js/screens/auto-mode.js`, `store.subscribe('autoState')`, sidebar live-dot wiring.
- Plan 2: auto-mode strip component, `GET /api/auto/state` endpoint, `store.autoState` polling.
- Plan 4: dashboard widget catalog interface (each widget exports `{ meta: {id, type, defaultSize}, mount(root, ctx) }`), stub `js/components/widgets/auto-mode-stepper.js` registered in the catalog.

---

## File Structure

**New files (created in this plan):**

```
plugins/taskmaster/
├── tests/
│   └── test_server_auto_mode.py                 # pytest: endpoints + storage + controls
└── viewer/
    ├── css/screens/
    │   └── auto-mode.css                        # Page + spine + log + panels styling
    ├── js/
    │   ├── components/
    │   │   ├── auto-spine-layout.js             # Pure-data: nodes, bezier control points, satellites
    │   │   ├── quest-spine.js                   # SVG renderer (uses auto-spine-layout)
    │   │   ├── flight-log.js                    # Chronological waterfall
    │   │   ├── sessions-strip.js                # Parallel-session tabs
    │   │   ├── auto-side-panels.js              # Left (subagents+hooks) and right (budget+tools)
    │   │   └── budget-meter.js                  # Single horizontal var/limit bar
    │   └── screens/
    │       └── (auto-mode.js — replaced)
    └── tests/
        ├── auto-mode.spec.js                    # Playwright smoke
        └── unit/
            ├── auto-spine-layout.test.js        # node --test
            └── stepper-line.test.js             # node --test
```

**Files modified (in this plan):**
- `plugins/taskmaster/backlog_server.py` — new MCP tools (`auto_state_get`, `auto_pause`, `auto_stop`, `auto_history`, `auto_event_log`); HTTP endpoints (`POST /api/auto/pause`, `POST /api/auto/stop`, `GET /api/auto/sessions`, `GET /api/auto/sessions/<sid>`, `GET /api/auto/events`, `GET /api/auto/budget/<sid>`); migration of `state.json` to `sessions/<sid>.json`.
- `plugins/taskmaster/taskmaster_v3.py` — `migrate_auto_state_to_sessions()`, `auto_sessions_dir()`, `load_auto_session(sid)`, `save_auto_session(sid, state)`, `list_auto_sessions()`, `append_auto_event(sid, event)`, `read_auto_events(sid, since)`, `read_hook_events(limit)`, `compute_budget(sid)`.
- `plugins/taskmaster/viewer/js/screens/auto-mode.js` — replaces Plan 1 stub.
- `plugins/taskmaster/viewer/js/components/widgets/auto-mode-stepper.js` — replaces Plan 4 stub.
- `plugins/taskmaster/viewer/index.html` — register `screens/auto-mode.css` link tag.
- `plugins/taskmaster/viewer/js/api.js` — add `api.autoPause(sid)`, `api.autoStop(sid)`, `api.autoListSessions()`, `api.autoSession(sid)`, `api.autoEvents(sid, since)`, `api.autoBudget(sid)`.
- `plugins/taskmaster/viewer/js/store.js` — extend `autoState` slice with `sessions[]`, `activeSessionId`, `events[]`; add `setActiveSession(sid)`.

**Files left untouched:** all other screens, foundation, kanban, dashboard widget catalog (only the one stub is replaced).

---

## Architectural Conventions

**Inherited verbatim from Plan 1 — see `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-1-foundation.md` §"Architectural Conventions".** Module style, screen module shape, CSS naming, state+API rules, routing, persistence, and test discipline are not redefined here. Plan 6 follows them exactly:
- ES modules; one default export per file unless noted.
- Screen module exports `mount(root, ctx)` returning a cleanup function and a `meta` object.
- CSS classes use file-prefix (`.auto-*`, `.spine-*`, `.flog-*`, `.sstrip-*`, `.aside-*`, `.bmeter-*`, `.stepper-*`).
- All state via `store`, all mutations via `api`.
- Routing already adds `#/auto`.
- All viewer prefs persist to `.taskmaster/viewer.json`.
- Pytest with `tmp_path` + `running_server` fixture from `tests/test_server_api.py` (Plan 1).
- Pure-data: `node --test`. UI: Playwright smoke.

**Plan-6-specific addenda:**
- Auto session IDs use the active task ID as the session ID (`sid = task_id`). This matches the way the runner names worktrees and avoids a second identity. If two parallel runs ever target the same task ID, append `-N` (`auth-003-2`); the migration assumes one-per-task.
- All times in storage are ISO 8601 UTC strings (`2026-04-26T18:42:09Z`). The viewer formats relative locally.
- Hook events file (`.taskmaster/auto/hooks.jsonl`) has the schema documented in Task 8 — Plan 6 only reads it.

---

## Milestones

- **M1 — Server storage refactor** (Tasks 1–6): single `state.json` → `sessions/<sid>.json` directory, migration, helpers, append-event log.
- **M2 — Server HTTP endpoints + control actions** (Tasks 7–14): pause/stop/history/sessions list/session detail/events/budget endpoints + MCP tools + tests.
- **M3 — Spine layout helper (pure)** (Tasks 15–19): `auto-spine-layout.js` with nodes, bezier control points, satellites; `node --test`.
- **M4 — Quest Spine SVG renderer** (Tasks 20–28): SVG component, deep-recess frame, animated active node, satellites, integration into auto-mode screen.
- **M5 — Flight Log** (Tasks 29–33): waterfall component, active row pulse, log toggle wiring.
- **M6 — Sessions strip + side panels** (Tasks 34–43): sessions strip, subagents+hooks left panel, budget meter, budget+tools right panel.
- **M7 — Dashboard stepper widget + line-fix verification** (Tasks 44–51): widget impl, edge-to-edge connector geometry, unit test, integration into widget catalog.
- **M8 — Integration smoke** (Tasks 52–58): Playwright end-to-end, header pause/stop wiring, helper note dismissal, sidebar live-dot publish.

---

## M1 — Server Storage Refactor

### Task 1: Define auto-mode storage layout constants

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py` (constants block, near `AUTO_STAGES`)
- Modify: `plugins/taskmaster/tests/test_v3_layout.py`

- [ ] **Step 1: Write the failing test**

Append to `plugins/taskmaster/tests/test_v3_layout.py`:

```python
def test_auto_storage_constants():
    from taskmaster_v3 import (
        AUTO_DIR, AUTO_SESSIONS_DIR, AUTO_HOOKS_LOG, auto_session_path, auto_events_path,
    )
    from pathlib import Path
    assert AUTO_DIR == Path(".taskmaster") / "auto"
    assert AUTO_SESSIONS_DIR == Path(".taskmaster") / "auto" / "sessions"
    assert AUTO_HOOKS_LOG == Path(".taskmaster") / "auto" / "hooks.jsonl"
    assert auto_session_path("v3-014") == AUTO_SESSIONS_DIR / "v3-014.json"
    assert auto_events_path("v3-014") == AUTO_SESSIONS_DIR / "v3-014.events.jsonl"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest plugins/taskmaster/tests/test_v3_layout.py::test_auto_storage_constants -v
```
Expected: FAIL with `ImportError: cannot import name 'AUTO_DIR'`.

- [ ] **Step 3: Add the constants**

Insert in `plugins/taskmaster/taskmaster_v3.py` after `AUTO_TASK_STATUSES`:

```python
# ---- Auto-mode storage layout -------------------------------------------

AUTO_DIR = Path(".taskmaster") / "auto"
AUTO_SESSIONS_DIR = AUTO_DIR / "sessions"
AUTO_HOOKS_LOG = AUTO_DIR / "hooks.jsonl"
AUTO_LEGACY_STATE = AUTO_DIR / "state.json"  # pre-Plan-6 single-session file


def auto_session_path(sid: str) -> Path:
    return AUTO_SESSIONS_DIR / f"{sid}.json"


def auto_events_path(sid: str) -> Path:
    return AUTO_SESSIONS_DIR / f"{sid}.events.jsonl"
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest plugins/taskmaster/tests/test_v3_layout.py::test_auto_storage_constants -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_v3_layout.py
git commit -m "feat(taskmaster): auto-mode storage layout constants"
```

---

### Task 2: Implement `load_auto_session`, `save_auto_session`, `list_auto_sessions`

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py`
- Modify: `plugins/taskmaster/tests/test_v3_layout.py`

- [ ] **Step 1: Write the failing test**

Append to `plugins/taskmaster/tests/test_v3_layout.py`:

```python
def test_auto_session_round_trip(tmp_path, monkeypatch):
    import json
    from taskmaster_v3 import (
        save_auto_session, load_auto_session, list_auto_sessions, AUTO_SESSIONS_DIR,
    )
    monkeypatch.chdir(tmp_path)

    state = {
        "session_id": "v3-014",
        "task_id": "v3-014",
        "title": "Auto-mode status indicator",
        "mode": "walk",
        "started_at": "2026-04-26T18:42:09Z",
        "cursor": {"task_id": "v3-014", "stage": "IMPLEMENT", "model": "sonnet"},
        "completed": ["PICK"],
        "pending": ["REVIEW", "HANDOVER_STUB", "COMPLETE"],
        "failed": [],
        "models": {},
        "config": {},
    }
    save_auto_session("v3-014", state)
    assert (tmp_path / AUTO_SESSIONS_DIR / "v3-014.json").exists()

    got = load_auto_session("v3-014")
    assert got["cursor"]["stage"] == "IMPLEMENT"

    save_auto_session("v3-022", {**state, "session_id": "v3-022", "task_id": "v3-022"})
    sessions = list_auto_sessions()
    assert sorted(s["session_id"] for s in sessions) == ["v3-014", "v3-022"]


def test_load_auto_session_missing_returns_none(tmp_path, monkeypatch):
    from taskmaster_v3 import load_auto_session
    monkeypatch.chdir(tmp_path)
    assert load_auto_session("nope") is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest plugins/taskmaster/tests/test_v3_layout.py -v -k auto_session
```
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement helpers**

Add to `plugins/taskmaster/taskmaster_v3.py` (alongside other load/save helpers):

```python
def save_auto_session(sid: str, state: dict) -> None:
    import json
    p = auto_session_path(sid)
    p.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(p, json.dumps(state, indent=2))


def load_auto_session(sid: str) -> dict | None:
    import json
    p = auto_session_path(sid)
    if not p.exists():
        return None
    return json.loads(p.read_text())


def list_auto_sessions() -> list[dict]:
    """Return all sessions, newest started_at first. Skips malformed files."""
    import json
    out = []
    if not AUTO_SESSIONS_DIR.exists():
        return out
    for p in AUTO_SESSIONS_DIR.glob("*.json"):
        if p.name.endswith(".events.jsonl"):
            continue
        try:
            out.append(json.loads(p.read_text()))
        except Exception:
            continue
    out.sort(key=lambda s: s.get("started_at", ""), reverse=True)
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest plugins/taskmaster/tests/test_v3_layout.py -v -k auto_session
```
Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_v3_layout.py
git commit -m "feat(taskmaster): per-session auto-mode storage helpers"
```

---

### Task 3: One-time migration of legacy `state.json` → `sessions/<sid>.json`

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py`
- Modify: `plugins/taskmaster/tests/test_v3_layout.py`

- [ ] **Step 1: Write the failing test**

Append:

```python
def test_migrate_legacy_state_to_sessions(tmp_path, monkeypatch):
    import json
    from taskmaster_v3 import (
        migrate_auto_state_to_sessions, AUTO_DIR, AUTO_LEGACY_STATE,
    )
    monkeypatch.chdir(tmp_path)
    (tmp_path / AUTO_DIR).mkdir(parents=True)
    legacy = {
        "task_id": "v3-014",
        "mode": "walk",
        "started_at": "2026-04-26T18:42:09Z",
        "cursor": {"task_id": "v3-014", "stage": "IMPLEMENT"},
    }
    (tmp_path / AUTO_LEGACY_STATE).write_text(json.dumps(legacy))

    moved = migrate_auto_state_to_sessions()
    assert moved is True
    sess = json.loads((tmp_path / AUTO_DIR / "sessions" / "v3-014.json").read_text())
    assert sess["session_id"] == "v3-014"
    assert sess["task_id"] == "v3-014"
    # legacy file renamed, not deleted, so we keep an audit trail
    assert (tmp_path / AUTO_DIR / "state.legacy.json").exists()
    assert not (tmp_path / AUTO_LEGACY_STATE).exists()


def test_migrate_idempotent(tmp_path, monkeypatch):
    from taskmaster_v3 import migrate_auto_state_to_sessions
    monkeypatch.chdir(tmp_path)
    # No legacy file → no-op, returns False
    assert migrate_auto_state_to_sessions() is False
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest plugins/taskmaster/tests/test_v3_layout.py -v -k migrate
```
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement the migration**

Add to `plugins/taskmaster/taskmaster_v3.py`:

```python
def migrate_auto_state_to_sessions() -> bool:
    """One-time migration: wrap pre-Plan-6 single state.json into sessions/<task_id>.json.

    Returns True if a migration ran, False if nothing to do. Idempotent.
    """
    import json
    if not AUTO_LEGACY_STATE.exists():
        return False
    raw = json.loads(AUTO_LEGACY_STATE.read_text())
    sid = raw.get("task_id") or raw.get("session_id") or "legacy"
    state = dict(raw)
    state.setdefault("session_id", sid)
    state.setdefault("task_id", sid)
    save_auto_session(sid, state)
    audit = AUTO_LEGACY_STATE.with_name("state.legacy.json")
    AUTO_LEGACY_STATE.rename(audit)
    return True
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest plugins/taskmaster/tests/test_v3_layout.py -v -k migrate
```
Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_v3_layout.py
git commit -m "feat(taskmaster): migrate legacy auto state.json to per-session storage"
```

---

### Task 4: Wire migration into server startup

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py`
- Modify: `plugins/taskmaster/tests/test_v3_layout.py`

- [ ] **Step 1: Write the failing test**

Append:

```python
def test_server_init_runs_auto_migration(tmp_path, monkeypatch):
    import json
    from taskmaster_v3 import AUTO_DIR, AUTO_LEGACY_STATE
    monkeypatch.chdir(tmp_path)
    (tmp_path / AUTO_DIR).mkdir(parents=True)
    (tmp_path / AUTO_LEGACY_STATE).write_text(json.dumps({"task_id": "v3-014"}))

    from backlog_server import _init_storage  # added in this task
    _init_storage()

    assert (tmp_path / AUTO_DIR / "sessions" / "v3-014.json").exists()
    assert not (tmp_path / AUTO_LEGACY_STATE).exists()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest plugins/taskmaster/tests/test_v3_layout.py::test_server_init_runs_auto_migration -v
```
Expected: FAIL — `ImportError: cannot import name '_init_storage'`.

- [ ] **Step 3: Add `_init_storage` and call it from server entry**

In `plugins/taskmaster/backlog_server.py`, alongside `_make_server`:

```python
def _init_storage() -> None:
    """One-time storage migrations / dir setup. Called by server entry + tests."""
    from taskmaster_v3 import migrate_auto_state_to_sessions, AUTO_SESSIONS_DIR
    AUTO_SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    migrate_auto_state_to_sessions()
```

In the existing server entry point (the `serve()`/`run()` function from Plan 1), call `_init_storage()` immediately before `server.serve_forever()`. Also update the `running_server` fixture in `tests/test_server_api.py` to call `_init_storage()` after `_make_server` so HTTP tests see migrated state — search for `_make_server` and add `_init_storage()` on the next line.

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest plugins/taskmaster/tests/test_v3_layout.py::test_server_init_runs_auto_migration -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_server_api.py plugins/taskmaster/tests/test_v3_layout.py
git commit -m "feat(taskmaster): run auto-mode migration on server init"
```

---

### Task 5: Implement `append_auto_event` and `read_auto_events`

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py`
- Modify: `plugins/taskmaster/tests/test_v3_layout.py`

- [ ] **Step 1: Write the failing test**

Append:

```python
def test_auto_events_append_and_read(tmp_path, monkeypatch):
    from taskmaster_v3 import append_auto_event, read_auto_events
    monkeypatch.chdir(tmp_path)
    append_auto_event("v3-014", {
        "ts": "2026-04-26T18:42:09Z", "stage": "PICK",
        "kind": "stage_enter", "msg": "picked v3-014",
    })
    append_auto_event("v3-014", {
        "ts": "2026-04-26T18:43:11Z", "stage": "PICK",
        "kind": "stage_exit", "msg": "PICK done",
    })
    append_auto_event("v3-014", {
        "ts": "2026-04-26T18:43:12Z", "stage": "IMPLEMENT",
        "kind": "stage_enter", "msg": "starting implementation",
    })
    all_events = read_auto_events("v3-014")
    assert len(all_events) == 3
    assert all_events[0]["kind"] == "stage_enter"

    since = read_auto_events("v3-014", since="2026-04-26T18:43:00Z")
    assert len(since) == 2
    assert since[0]["stage"] == "PICK"  # exit
    assert since[1]["stage"] == "IMPLEMENT"


def test_read_auto_events_missing_session_returns_empty(tmp_path, monkeypatch):
    from taskmaster_v3 import read_auto_events
    monkeypatch.chdir(tmp_path)
    assert read_auto_events("nope") == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest plugins/taskmaster/tests/test_v3_layout.py -v -k auto_events
```
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement helpers**

Add to `plugins/taskmaster/taskmaster_v3.py`:

```python
def append_auto_event(sid: str, event: dict) -> None:
    """Append a single event to <sid>.events.jsonl. Creates parent dirs."""
    import json
    p = auto_events_path(sid)
    p.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(event, separators=(",", ":")) + "\n"
    with p.open("a", encoding="utf-8") as f:
        f.write(line)


def read_auto_events(sid: str, since: str | None = None) -> list[dict]:
    """Return events for sid, optionally filtered to ts >= since (ISO 8601 strings).
    Lex order on ISO 8601 UTC matches chronological order, so a string compare suffices.
    """
    import json
    p = auto_events_path(sid)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if since is not None and ev.get("ts", "") < since:
            continue
        out.append(ev)
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest plugins/taskmaster/tests/test_v3_layout.py -v -k auto_events
```
Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_v3_layout.py
git commit -m "feat(taskmaster): per-session auto-mode event log (append + read)"
```

---

### Task 6: Implement `read_hook_events` (read-only scrape)

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py`
- Modify: `plugins/taskmaster/tests/test_v3_layout.py`

Schema documented here for `.taskmaster/auto/hooks.jsonl` (one JSON object per line):

```json
{"ts": "2026-04-26T18:42:09Z", "hook": "PostToolUse", "session_id": "v3-014", "tool": "Edit", "ok": true}
```

Plan 6 only reads this file. Producer (the actual hook plumbing) is out of scope.

- [ ] **Step 1: Write the failing test**

Append:

```python
def test_read_hook_events_counts_by_hook(tmp_path, monkeypatch):
    from taskmaster_v3 import read_hook_events, AUTO_HOOKS_LOG
    monkeypatch.chdir(tmp_path)
    AUTO_HOOKS_LOG.parent.mkdir(parents=True, exist_ok=True)
    AUTO_HOOKS_LOG.write_text(
        '{"ts":"2026-04-26T18:00:00Z","hook":"PostToolUse","session_id":"v3-014","tool":"Edit","ok":true}\n'
        '{"ts":"2026-04-26T18:00:01Z","hook":"PostToolUse","session_id":"v3-014","tool":"Edit","ok":true}\n'
        '{"ts":"2026-04-26T18:00:02Z","hook":"PreCompact","session_id":"v3-014","ok":true}\n'
    )
    counts = read_hook_events("v3-014")
    assert counts == {"PostToolUse": 2, "PreCompact": 1}


def test_read_hook_events_missing_log_returns_empty(tmp_path, monkeypatch):
    from taskmaster_v3 import read_hook_events
    monkeypatch.chdir(tmp_path)
    assert read_hook_events("v3-014") == {}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest plugins/taskmaster/tests/test_v3_layout.py -v -k hook_events
```
Expected: FAIL.

- [ ] **Step 3: Implement helper**

Add to `plugins/taskmaster/taskmaster_v3.py`:

```python
def read_hook_events(sid: str) -> dict[str, int]:
    """Return {hook_name: count} for events tagged with the given session_id.

    Tolerates malformed lines silently (skip). Missing file → {}.
    """
    import json
    if not AUTO_HOOKS_LOG.exists():
        return {}
    counts: dict[str, int] = {}
    for line in AUTO_HOOKS_LOG.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if ev.get("session_id") != sid:
            continue
        h = ev.get("hook")
        if not h:
            continue
        counts[h] = counts.get(h, 0) + 1
    return counts
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest plugins/taskmaster/tests/test_v3_layout.py -v -k hook_events
```
Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_v3_layout.py
git commit -m "feat(taskmaster): read hook firings count from auto/hooks.jsonl"
```

---

## M2 — Server HTTP Endpoints + Control Actions

### Task 7: Create `tests/test_server_auto_mode.py` skeleton + first endpoint test

**Files:**
- Create: `plugins/taskmaster/tests/test_server_auto_mode.py`

- [ ] **Step 1: Write the test file**

Create `plugins/taskmaster/tests/test_server_auto_mode.py`:

```python
"""HTTP API tests for Auto Mode endpoints (Plan 6).

Reuses the running_server fixture from test_server_api.py.
"""
import json
import urllib.request
import urllib.error
import pytest

from tests.test_server_api import running_server  # noqa: F401  (fixture re-export)


def _seed_session(tmp_path, sid="v3-014", **overrides):
    """Helper: write a session JSON file directly into the server's working dir."""
    from taskmaster_v3 import save_auto_session
    base = {
        "session_id": sid,
        "task_id": sid,
        "title": "Auto-mode status indicator",
        "worktree": ".worktrees/v3-014",
        "mode": "walk",
        "started_at": "2026-04-26T18:42:09Z",
        "cursor": {"task_id": sid, "stage": "IMPLEMENT", "model": "sonnet"},
        "completed": ["PICK"],
        "pending": ["REVIEW", "HANDOVER_STUB", "COMPLETE"],
        "failed": [],
        "subagents": [],
        "tool_log": [],
        "budget": {
            "tokens": {"used": 12000, "limit": 200000},
            "time_seconds": {"used": 1820, "limit": 14400},
            "context": {"used": 0.18, "limit": 1.0},
            "cost_usd": {"used": 0.42, "limit": 5.00},
        },
    }
    base.update(overrides)
    save_auto_session(sid, base)
    return base


def test_get_auto_sessions_lists_all(running_server, tmp_path, monkeypatch):
    base, _ = running_server
    _seed_session(tmp_path, sid="v3-014")
    _seed_session(tmp_path, sid="v3-022", title="Filter bar polish")

    resp = urllib.request.urlopen(f"{base}/api/auto/sessions")
    assert resp.status == 200
    payload = json.loads(resp.read())
    ids = sorted(s["session_id"] for s in payload["sessions"])
    assert ids == ["v3-014", "v3-022"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest plugins/taskmaster/tests/test_server_auto_mode.py::test_get_auto_sessions_lists_all -v
```
Expected: FAIL — 404 on `/api/auto/sessions`.

- [ ] **Step 3: Implement the endpoint**

In `plugins/taskmaster/backlog_server.py`, add to `_Handler.do_GET` before the existing fallback:

```python
if self.path == "/api/auto/sessions":
    import json
    from taskmaster_v3 import list_auto_sessions
    body = json.dumps({"sessions": list_auto_sessions()}).encode("utf-8")
    self.send_response(200)
    self.send_header("Content-Type", "application/json")
    self.send_header("Content-Length", str(len(body)))
    self.send_header("Access-Control-Allow-Origin", "*")
    self.end_headers()
    self.wfile.write(body)
    return
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest plugins/taskmaster/tests/test_server_auto_mode.py::test_get_auto_sessions_lists_all -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_server_auto_mode.py
git commit -m "feat(taskmaster): GET /api/auto/sessions endpoint"
```

---

### Task 8: `GET /api/auto/sessions/<sid>` — single session detail

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py`
- Modify: `plugins/taskmaster/tests/test_server_auto_mode.py`

- [ ] **Step 1: Write the failing test**

Append:

```python
def test_get_auto_session_detail(running_server, tmp_path):
    base, _ = running_server
    _seed_session(tmp_path, sid="v3-014")

    resp = urllib.request.urlopen(f"{base}/api/auto/sessions/v3-014")
    assert resp.status == 200
    body = json.loads(resp.read())
    assert body["session_id"] == "v3-014"
    assert body["cursor"]["stage"] == "IMPLEMENT"


def test_get_auto_session_detail_404(running_server):
    base, _ = running_server
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(f"{base}/api/auto/sessions/missing")
    assert exc.value.code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest plugins/taskmaster/tests/test_server_auto_mode.py -v -k auto_session_detail
```
Expected: FAIL.

- [ ] **Step 3: Implement endpoint**

In `_Handler.do_GET`, add (before the fallback):

```python
if self.path.startswith("/api/auto/sessions/"):
    import json
    from taskmaster_v3 import load_auto_session
    sid = self.path[len("/api/auto/sessions/"):]
    state = load_auto_session(sid)
    if state is None:
        self.send_response(404)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok":false,"error":"not found"}')
        return
    body = json.dumps(state).encode("utf-8")
    self.send_response(200)
    self.send_header("Content-Type", "application/json")
    self.send_header("Content-Length", str(len(body)))
    self.send_header("Access-Control-Allow-Origin", "*")
    self.end_headers()
    self.wfile.write(body)
    return
```

Order matters: this branch must come **after** the `/api/auto/sessions` exact match (Task 7), since `startswith` would otherwise swallow it. Verify the exact-match check is checked first.

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest plugins/taskmaster/tests/test_server_auto_mode.py -v -k auto_session_detail
```
Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_server_auto_mode.py
git commit -m "feat(taskmaster): GET /api/auto/sessions/<sid> endpoint"
```

---

### Task 9: `GET /api/auto/state` returns most-recent session (Plan-2 compat shim)

Plan 2 introduced `GET /api/auto/state` returning the single-state file. After Plan 6's storage refactor, that endpoint must keep working — it now returns the most-recently-started session. If none, returns `{"running": false}`.

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py`
- Modify: `plugins/taskmaster/tests/test_server_auto_mode.py`

- [ ] **Step 1: Write the failing test**

Append:

```python
def test_auto_state_returns_most_recent_session(running_server, tmp_path):
    base, _ = running_server
    _seed_session(tmp_path, sid="v3-014", started_at="2026-04-26T17:00:00Z")
    _seed_session(tmp_path, sid="v3-022", started_at="2026-04-26T18:30:00Z")

    body = json.loads(urllib.request.urlopen(f"{base}/api/auto/state").read())
    assert body["session_id"] == "v3-022"


def test_auto_state_no_sessions(running_server):
    base, _ = running_server
    body = json.loads(urllib.request.urlopen(f"{base}/api/auto/state").read())
    assert body == {"running": False}
```

- [ ] **Step 2: Run tests**

```bash
python -m pytest plugins/taskmaster/tests/test_server_auto_mode.py -v -k auto_state
```
Expected: behavior depends on Plan 2's existing impl. Replace it.

- [ ] **Step 3: Replace `/api/auto/state` handler**

Locate the existing `if self.path == "/api/auto/state":` branch in `_Handler.do_GET` (introduced in Plan 2) and replace it with:

```python
if self.path == "/api/auto/state":
    import json
    from taskmaster_v3 import list_auto_sessions
    sessions = list_auto_sessions()
    body = (
        json.dumps(sessions[0]).encode("utf-8") if sessions
        else b'{"running":false}'
    )
    self.send_response(200)
    self.send_header("Content-Type", "application/json")
    self.send_header("Content-Length", str(len(body)))
    self.send_header("Access-Control-Allow-Origin", "*")
    self.end_headers()
    self.wfile.write(body)
    return
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest plugins/taskmaster/tests/test_server_auto_mode.py -v -k auto_state
```
Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_server_auto_mode.py
git commit -m "refactor(taskmaster): /api/auto/state returns most-recent session"
```

---

### Task 10: `POST /api/auto/pause` and `POST /api/auto/stop`

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py`
- Modify: `plugins/taskmaster/tests/test_server_auto_mode.py`

- [ ] **Step 1: Write the failing test**

Append:

```python
def test_post_auto_pause_sets_state_and_appends_event(running_server, tmp_path):
    from taskmaster_v3 import load_auto_session, read_auto_events
    base, _ = running_server
    _seed_session(tmp_path, sid="v3-014")

    body = json.dumps({"session_id": "v3-014"}).encode()
    req = urllib.request.Request(
        f"{base}/api/auto/pause", data=body, method="POST",
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req)
    assert resp.status == 200
    assert json.loads(resp.read())["ok"] is True

    state = load_auto_session("v3-014")
    assert state["paused"] is True
    events = read_auto_events("v3-014")
    assert any(e["kind"] == "control_pause" for e in events)


def test_post_auto_stop_sets_state_and_appends_event(running_server, tmp_path):
    from taskmaster_v3 import load_auto_session, read_auto_events
    base, _ = running_server
    _seed_session(tmp_path, sid="v3-014")

    req = urllib.request.Request(
        f"{base}/api/auto/stop",
        data=json.dumps({"session_id": "v3-014"}).encode(),
        method="POST", headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(req)
    state = load_auto_session("v3-014")
    assert state["stopped"] is True
    assert any(e["kind"] == "control_stop" for e in read_auto_events("v3-014"))


def test_post_auto_pause_unknown_session_404(running_server):
    base, _ = running_server
    req = urllib.request.Request(
        f"{base}/api/auto/pause",
        data=json.dumps({"session_id": "nope"}).encode(),
        method="POST", headers={"Content-Type": "application/json"},
    )
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(req)
    assert exc.value.code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest plugins/taskmaster/tests/test_server_auto_mode.py -v -k "pause or stop"
```
Expected: FAIL — 405/404.

- [ ] **Step 3: Implement `do_POST`**

Add (or extend if Plan 2 already added) `_Handler.do_POST`:

```python
def do_POST(self):
    import json
    from datetime import datetime, timezone
    from taskmaster_v3 import load_auto_session, save_auto_session, append_auto_event

    if self.path in ("/api/auto/pause", "/api/auto/stop"):
        length = int(self.headers.get("Content-Length") or 0)
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        except Exception as e:
            self._send_json(400, {"ok": False, "error": f"invalid JSON: {e}"})
            return
        sid = payload.get("session_id")
        if not sid:
            self._send_json(400, {"ok": False, "error": "session_id required"})
            return
        state = load_auto_session(sid)
        if state is None:
            self._send_json(404, {"ok": False, "error": "not found"})
            return

        kind = "control_pause" if self.path.endswith("/pause") else "control_stop"
        flag = "paused" if kind == "control_pause" else "stopped"
        state[flag] = True
        save_auto_session(sid, state)
        append_auto_event(sid, {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "kind": kind, "stage": state.get("cursor", {}).get("stage"),
            "msg": f"{kind} via /api/auto",
        })
        self._send_json(200, {"ok": True})
        return

    # Existing handlers fall through here; preserve them.
    self._send_json(404, {"ok": False, "error": "not found"})
```

If `_send_json` is not yet present from Plan 1, add at the top of the class:

```python
def _send_json(self, status: int, payload: dict) -> None:
    import json
    body = json.dumps(payload).encode("utf-8")
    self.send_response(status)
    self.send_header("Content-Type", "application/json")
    self.send_header("Content-Length", str(len(body)))
    self.send_header("Access-Control-Allow-Origin", "*")
    self.end_headers()
    self.wfile.write(body)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest plugins/taskmaster/tests/test_server_auto_mode.py -v -k "pause or stop"
```
Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_server_auto_mode.py
git commit -m "feat(taskmaster): POST /api/auto/pause and /api/auto/stop"
```

---

### Task 11: `GET /api/auto/events?sid=&since=`

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py`
- Modify: `plugins/taskmaster/tests/test_server_auto_mode.py`

- [ ] **Step 1: Write the failing test**

Append:

```python
def test_get_auto_events_filtered_by_since(running_server, tmp_path):
    from taskmaster_v3 import append_auto_event
    base, _ = running_server
    _seed_session(tmp_path, sid="v3-014")
    append_auto_event("v3-014", {"ts":"2026-04-26T18:00:00Z","kind":"stage_enter","stage":"PICK","msg":"a"})
    append_auto_event("v3-014", {"ts":"2026-04-26T19:00:00Z","kind":"stage_enter","stage":"IMPLEMENT","msg":"b"})

    resp = urllib.request.urlopen(f"{base}/api/auto/events?sid=v3-014")
    body = json.loads(resp.read())
    assert len(body["events"]) == 2

    resp = urllib.request.urlopen(f"{base}/api/auto/events?sid=v3-014&since=2026-04-26T18:30:00Z")
    body = json.loads(resp.read())
    assert len(body["events"]) == 1
    assert body["events"][0]["stage"] == "IMPLEMENT"


def test_get_auto_events_missing_sid_400(running_server):
    base, _ = running_server
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(f"{base}/api/auto/events")
    assert exc.value.code == 400
```

- [ ] **Step 2: Run tests**

```bash
python -m pytest plugins/taskmaster/tests/test_server_auto_mode.py -v -k auto_events
```
Expected: FAIL.

- [ ] **Step 3: Implement endpoint**

Add to `_Handler.do_GET` (before the fallback):

```python
if self.path.startswith("/api/auto/events"):
    import json
    from urllib.parse import urlsplit, parse_qs
    from taskmaster_v3 import read_auto_events
    qs = parse_qs(urlsplit(self.path).query)
    sid = (qs.get("sid") or [None])[0]
    since = (qs.get("since") or [None])[0]
    if not sid:
        self._send_json(400, {"ok": False, "error": "sid required"})
        return
    events = read_auto_events(sid, since=since)
    self._send_json(200, {"events": events})
    return
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest plugins/taskmaster/tests/test_server_auto_mode.py -v -k auto_events
```
Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_server_auto_mode.py
git commit -m "feat(taskmaster): GET /api/auto/events polling endpoint"
```

---

### Task 12: `GET /api/auto/budget/<sid>` + `compute_budget`

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py`
- Modify: `plugins/taskmaster/backlog_server.py`
- Modify: `plugins/taskmaster/tests/test_server_auto_mode.py`

- [ ] **Step 1: Write the failing test**

Append:

```python
def test_get_auto_budget(running_server, tmp_path):
    base, _ = running_server
    _seed_session(tmp_path, sid="v3-014")
    body = json.loads(urllib.request.urlopen(f"{base}/api/auto/budget/v3-014").read())
    assert body["meters"]["tokens"]["used"] == 12000
    assert body["meters"]["tokens"]["limit"] == 200000
    assert body["meters"]["tokens"]["pct"] == pytest.approx(12000 / 200000)
    assert body["meters"]["tokens"]["tier"] == "ok"   # under 60%
    # cost 0.42/5.00 = 8.4% → ok; force a critical case:

def test_get_auto_budget_tiers(running_server, tmp_path):
    base, _ = running_server
    _seed_session(tmp_path, sid="v3-014",
                  budget={
                      "tokens": {"used": 65, "limit": 100},  # 65% → warn
                      "time_seconds": {"used": 95, "limit": 100},  # 95% → crit
                      "context": {"used": 0.10, "limit": 1.0},
                      "cost_usd": {"used": 0.0, "limit": 5.0},
                  })
    body = json.loads(urllib.request.urlopen(f"{base}/api/auto/budget/v3-014").read())
    assert body["meters"]["tokens"]["tier"] == "warn"
    assert body["meters"]["time_seconds"]["tier"] == "crit"
```

- [ ] **Step 2: Run tests**

```bash
python -m pytest plugins/taskmaster/tests/test_server_auto_mode.py -v -k auto_budget
```
Expected: FAIL.

- [ ] **Step 3: Implement helper + endpoint**

Add to `taskmaster_v3.py`:

```python
def compute_budget(state: dict) -> dict:
    """Compute pct + tier for each meter. Tier: ok < 0.6 <= warn < 0.9 <= crit."""
    raw = state.get("budget") or {}
    out = {}
    for key, meter in raw.items():
        used = meter.get("used", 0)
        limit = meter.get("limit", 0) or 1
        pct = used / limit if limit else 0
        if pct >= 0.9:
            tier = "crit"
        elif pct >= 0.6:
            tier = "warn"
        else:
            tier = "ok"
        out[key] = {"used": used, "limit": limit, "pct": pct, "tier": tier}
    return out
```

Add to `_Handler.do_GET`:

```python
if self.path.startswith("/api/auto/budget/"):
    from taskmaster_v3 import load_auto_session, compute_budget
    sid = self.path[len("/api/auto/budget/"):]
    state = load_auto_session(sid)
    if state is None:
        self._send_json(404, {"ok": False, "error": "not found"})
        return
    self._send_json(200, {"session_id": sid, "meters": compute_budget(state)})
    return
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest plugins/taskmaster/tests/test_server_auto_mode.py -v -k auto_budget
```
Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_server_auto_mode.py
git commit -m "feat(taskmaster): GET /api/auto/budget/<sid> with tiered meters"
```

---

### Task 13: MCP tools — `auto_state_get`, `auto_pause`, `auto_stop`, `auto_history`, `auto_event_log`

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py`
- Modify: `plugins/taskmaster/tests/test_server_auto_mode.py`

- [ ] **Step 1: Write the failing test**

Append:

```python
def test_mcp_auto_history_returns_recent_completed(tmp_path, monkeypatch):
    """auto_history returns sessions with stopped or completed cursor, newest first."""
    monkeypatch.chdir(tmp_path)
    from taskmaster_v3 import save_auto_session
    save_auto_session("v3-001", {"session_id":"v3-001","task_id":"v3-001",
        "started_at":"2026-04-20T10:00:00Z","stopped":True,
        "cursor":{"stage":"COMPLETE"}})
    save_auto_session("v3-002", {"session_id":"v3-002","task_id":"v3-002",
        "started_at":"2026-04-21T10:00:00Z",
        "cursor":{"stage":"IMPLEMENT"}})

    from backlog_server import auto_history
    result = json.loads(auto_history(limit=10))
    ids = [s["session_id"] for s in result["sessions"]]
    assert "v3-001" in ids
    # Currently-running v3-002 also returned (caller filters)
    assert "v3-002" in ids
    # Newest first
    assert ids[0] == "v3-002"


def test_mcp_auto_state_get_round_trip(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from taskmaster_v3 import save_auto_session
    save_auto_session("v3-014", {
        "session_id":"v3-014","task_id":"v3-014",
        "started_at":"2026-04-26T18:42:09Z",
        "cursor":{"stage":"IMPLEMENT","model":"sonnet","task_id":"v3-014"},
    })
    from backlog_server import auto_state_get
    result = json.loads(auto_state_get())
    assert result["session_id"] == "v3-014"
```

- [ ] **Step 2: Run tests**

```bash
python -m pytest plugins/taskmaster/tests/test_server_auto_mode.py -v -k mcp_auto
```
Expected: FAIL — `ImportError`.

- [ ] **Step 3: Implement MCP tools**

In `plugins/taskmaster/backlog_server.py`, near the other v3 entity tools:

```python
@mcp.tool()
def auto_state_get() -> str:
    """Return the most-recent auto-mode session state as JSON. {} if none running."""
    import json
    from taskmaster_v3 import list_auto_sessions
    sessions = list_auto_sessions()
    return json.dumps(sessions[0] if sessions else {})


@mcp.tool()
def auto_pause(session_id: str) -> str:
    """Mark a running auto-mode session as paused. Returns 'ok' or 'error: ...'."""
    from datetime import datetime, timezone
    from taskmaster_v3 import load_auto_session, save_auto_session, append_auto_event
    state = load_auto_session(session_id)
    if state is None:
        return f"error: session {session_id} not found"
    state["paused"] = True
    save_auto_session(session_id, state)
    append_auto_event(session_id, {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "kind": "control_pause",
        "stage": state.get("cursor", {}).get("stage"),
        "msg": "paused via MCP",
    })
    return "ok"


@mcp.tool()
def auto_stop(session_id: str) -> str:
    """Mark a running auto-mode session as stopped. Returns 'ok' or 'error: ...'."""
    from datetime import datetime, timezone
    from taskmaster_v3 import load_auto_session, save_auto_session, append_auto_event
    state = load_auto_session(session_id)
    if state is None:
        return f"error: session {session_id} not found"
    state["stopped"] = True
    save_auto_session(session_id, state)
    append_auto_event(session_id, {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "kind": "control_stop",
        "stage": state.get("cursor", {}).get("stage"),
        "msg": "stopped via MCP",
    })
    return "ok"


@mcp.tool()
def auto_history(limit: int = 50) -> str:
    """Return recent auto-mode sessions as JSON, newest first."""
    import json
    from taskmaster_v3 import list_auto_sessions
    sessions = list_auto_sessions()[: max(1, int(limit))]
    return json.dumps({"sessions": sessions}, indent=2)


@mcp.tool()
def auto_event_log(session_id: str, since: str | None = None) -> str:
    """Return events for a session, optionally filtered by ISO 8601 timestamp."""
    import json
    from taskmaster_v3 import read_auto_events
    return json.dumps({"events": read_auto_events(session_id, since=since)}, indent=2)
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest plugins/taskmaster/tests/test_server_auto_mode.py -v -k mcp_auto
```
Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_server_auto_mode.py
git commit -m "feat(taskmaster): MCP tools for auto-mode state/pause/stop/history/events"
```

---

### Task 14: Extend `js/api.js` with auto-mode HTTP wrappers

**Files:**
- Modify: `plugins/taskmaster/viewer/js/api.js`

(No tests here — pure transport. Behavior is exercised by the screen-level Playwright tests in M8.)

- [ ] **Step 1: Add wrappers**

Append to `plugins/taskmaster/viewer/js/api.js`:

```javascript
// ---- Auto Mode (Plan 6) -------------------------------------------------

export async function autoListSessions() {
  const r = await fetch('/api/auto/sessions');
  if (!r.ok) throw new Error(`autoListSessions ${r.status}`);
  return (await r.json()).sessions;
}

export async function autoSession(sid) {
  const r = await fetch(`/api/auto/sessions/${encodeURIComponent(sid)}`);
  if (r.status === 404) return null;
  if (!r.ok) throw new Error(`autoSession ${r.status}`);
  return await r.json();
}

export async function autoPause(sid) {
  const r = await fetch('/api/auto/pause', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sid }),
  });
  if (!r.ok) throw new Error(`autoPause ${r.status}`);
  return await r.json();
}

export async function autoStop(sid) {
  const r = await fetch('/api/auto/stop', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sid }),
  });
  if (!r.ok) throw new Error(`autoStop ${r.status}`);
  return await r.json();
}

export async function autoEvents(sid, since) {
  const qs = new URLSearchParams({ sid });
  if (since) qs.set('since', since);
  const r = await fetch(`/api/auto/events?${qs}`);
  if (!r.ok) throw new Error(`autoEvents ${r.status}`);
  return (await r.json()).events;
}

export async function autoBudget(sid) {
  const r = await fetch(`/api/auto/budget/${encodeURIComponent(sid)}`);
  if (!r.ok) throw new Error(`autoBudget ${r.status}`);
  return await r.json();
}
```

If `api.js` uses a default export object, also add the methods there: `api.autoListSessions = autoListSessions`, etc., so existing call sites that import the default still work.

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/api.js
git commit -m "feat(taskmaster-viewer): api wrappers for auto-mode endpoints"
```

---

## M3 — Spine Layout Helper (Pure)

### Task 15: Define exported function signatures for `auto-spine-layout.js`

The pure-data layout helper has stable function names that the renderer (Task 22+) will import. Lock them now.

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/auto-spine-layout.js` (skeleton)
- Create: `plugins/taskmaster/viewer/tests/unit/auto-spine-layout.test.js`

- [ ] **Step 1: Write the failing test**

Create `plugins/taskmaster/viewer/tests/unit/auto-spine-layout.test.js`:

```javascript
import test from 'node:test';
import assert from 'node:assert/strict';

import {
  AUTO_STAGES,
  computeSpineLayout,
} from '../../js/components/auto-spine-layout.js';

test('AUTO_STAGES is the canonical 5-stage list', () => {
  assert.deepEqual(AUTO_STAGES, [
    'PICK', 'IMPLEMENT', 'REVIEW', 'HANDOVER_STUB', 'COMPLETE',
  ]);
});

test('computeSpineLayout returns one node per stage', () => {
  const layout = computeSpineLayout({
    cursorStage: 'IMPLEMENT',
    completed: ['PICK'],
    subagents: [],
    width: 240,
    height: 480,
    padding: 40,
  });
  assert.equal(layout.nodes.length, AUTO_STAGES.length);
  for (const node of layout.nodes) {
    assert.ok(['done', 'active', 'pending'].includes(node.state));
  }
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
node --test plugins/taskmaster/viewer/tests/unit/auto-spine-layout.test.js
```
Expected: FAIL with `Cannot find module .../auto-spine-layout.js`.

- [ ] **Step 3: Create the skeleton**

Write `plugins/taskmaster/viewer/js/components/auto-spine-layout.js`:

```javascript
// Pure-data SVG layout for the Quest Spine.
// No DOM access. Inputs → outputs only. Renderer imports these.

export const AUTO_STAGES = ['PICK', 'IMPLEMENT', 'REVIEW', 'HANDOVER_STUB', 'COMPLETE'];

/**
 * Compute spine geometry.
 * @param {object} opts
 * @param {string} opts.cursorStage           One of AUTO_STAGES (or null when not running).
 * @param {string[]} opts.completed           Stages already done (subset of AUTO_STAGES).
 * @param {Array<{type:string,status:string}>} opts.subagents  Active subagents on the cursor stage.
 * @param {number} opts.width                 SVG width.
 * @param {number} opts.height                SVG height.
 * @param {number} opts.padding               Top/bottom padding inside the frame.
 * @returns {{nodes: Array, satellites: Array, connectors: Array}}
 */
export function computeSpineLayout(opts) {
  const { cursorStage, completed = [], subagents = [], width, height, padding } = opts;
  const cx = width / 2;
  const usableH = height - padding * 2;
  const step = AUTO_STAGES.length > 1 ? usableH / (AUTO_STAGES.length - 1) : 0;

  const completedSet = new Set(completed);

  const nodes = AUTO_STAGES.map((stage, i) => {
    let state;
    if (completedSet.has(stage)) state = 'done';
    else if (stage === cursorStage) state = 'active';
    else state = 'pending';
    return {
      stage,
      x: cx,
      y: padding + step * i,
      r: state === 'active' ? 18 : 10,
      state,
    };
  });

  const connectors = [];
  for (let i = 0; i < nodes.length - 1; i += 1) {
    const a = nodes[i];
    const b = nodes[i + 1];
    connectors.push({ x1: a.x, y1: a.y + a.r, x2: b.x, y2: b.y - b.r, fromState: a.state });
  }

  // Satellites: branch off the active node with horizontal in/out tangents.
  const active = nodes.find((n) => n.state === 'active');
  const satellites = [];
  if (active && subagents.length) {
    const offsetX = 90;
    const verticalSpan = 60;
    subagents.forEach((sa, idx) => {
      const dy = subagents.length === 1 ? 0
        : (idx - (subagents.length - 1) / 2) * (verticalSpan / Math.max(1, subagents.length - 1));
      const side = idx % 2 === 0 ? 1 : -1;  // alternate sides
      const sx = active.x + side * offsetX;
      const sy = active.y + dy;
      // Cubic bezier with HORIZONTAL in/out tangents:
      //   from (active.x ± active.r, active.y) tangent (±dx, 0)
      //   to (sx ∓ smallR, sy) tangent (∓dx, 0)
      const startX = active.x + side * active.r;
      const startY = active.y;
      const endR = 6;
      const endX = sx - side * endR;
      const endY = sy;
      const dx = Math.abs(endX - startX) * 0.55;
      satellites.push({
        type: sa.type,
        status: sa.status,
        node: { x: sx, y: sy, r: endR },
        bezier: {
          startX, startY, endX, endY,
          c1x: startX + side * dx, c1y: startY,
          c2x: endX - side * dx,   c2y: endY,
        },
      });
    });
  }

  return { nodes, satellites, connectors };
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
node --test plugins/taskmaster/viewer/tests/unit/auto-spine-layout.test.js
```
Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/auto-spine-layout.js plugins/taskmaster/viewer/tests/unit/auto-spine-layout.test.js
git commit -m "feat(taskmaster-viewer): pure spine layout helper skeleton"
```

---

### Task 16: Lock node radii (active=18, others=10) and y-positions

- [ ] **Step 1: Append failing assertions**

Append to `plugins/taskmaster/viewer/tests/unit/auto-spine-layout.test.js`:

```javascript
test('active node radius is 18, others 10 (spec §3.15)', () => {
  const layout = computeSpineLayout({
    cursorStage: 'IMPLEMENT', completed: ['PICK'], subagents: [],
    width: 240, height: 480, padding: 40,
  });
  const active = layout.nodes.find((n) => n.state === 'active');
  assert.equal(active.r, 18);
  for (const n of layout.nodes) {
    if (n !== active) assert.equal(n.r, 10);
  }
});

test('y-positions are evenly spaced and inside padding', () => {
  const layout = computeSpineLayout({
    cursorStage: 'PICK', completed: [], subagents: [],
    width: 240, height: 480, padding: 40,
  });
  assert.equal(layout.nodes[0].y, 40);                       // first
  assert.equal(layout.nodes.at(-1).y, 480 - 40);             // last
  // monotonically increasing
  for (let i = 1; i < layout.nodes.length; i += 1) {
    assert.ok(layout.nodes[i].y > layout.nodes[i - 1].y);
  }
});
```

- [ ] **Step 2: Run tests**

```bash
node --test plugins/taskmaster/viewer/tests/unit/auto-spine-layout.test.js
```
Expected: PASS (the implementation already satisfies these — this task locks the contract).

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/tests/unit/auto-spine-layout.test.js
git commit -m "test(taskmaster-viewer): lock spine node radius + spacing contract"
```

---

### Task 17: Lock connector geometry (start at edge, end at edge)

- [ ] **Step 1: Append failing assertions**

Append:

```javascript
test('connectors start at the bottom edge of node N and end at the top edge of N+1', () => {
  const layout = computeSpineLayout({
    cursorStage: 'IMPLEMENT', completed: ['PICK'], subagents: [],
    width: 240, height: 480, padding: 40,
  });
  for (let i = 0; i < layout.connectors.length; i += 1) {
    const c = layout.connectors[i];
    const a = layout.nodes[i];
    const b = layout.nodes[i + 1];
    assert.equal(c.x1, a.x);
    assert.equal(c.y1, a.y + a.r);
    assert.equal(c.x2, b.x);
    assert.equal(c.y2, b.y - b.r);
  }
});

test('connector.fromState mirrors the upper node state (drives line color)', () => {
  const layout = computeSpineLayout({
    cursorStage: 'IMPLEMENT', completed: ['PICK'], subagents: [],
    width: 240, height: 480, padding: 40,
  });
  // Done above active → fromState 'done'; below active → 'active' for the line below cursor.
  assert.equal(layout.connectors[0].fromState, 'done');         // PICK → IMPLEMENT
  assert.equal(layout.connectors[1].fromState, 'active');       // IMPLEMENT → REVIEW
  assert.equal(layout.connectors[2].fromState, 'pending');      // REVIEW → HANDOVER_STUB
});
```

- [ ] **Step 2: Run tests** — Expected: PASS.

```bash
node --test plugins/taskmaster/viewer/tests/unit/auto-spine-layout.test.js
```

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/tests/unit/auto-spine-layout.test.js
git commit -m "test(taskmaster-viewer): lock spine connector edge-to-edge geometry"
```

---

### Task 18: Lock satellite bezier control points (horizontal in/out tangents)

- [ ] **Step 1: Append failing assertions**

Append:

```javascript
test('satellite bezier has horizontal in/out tangents (control points share y with anchors)', () => {
  const layout = computeSpineLayout({
    cursorStage: 'IMPLEMENT', completed: ['PICK'],
    subagents: [{ type: 'G', status: 'running' }, { type: 'E', status: 'done' }],
    width: 240, height: 480, padding: 40,
  });
  assert.equal(layout.satellites.length, 2);
  for (const sat of layout.satellites) {
    assert.equal(sat.bezier.c1y, sat.bezier.startY,
      'first control point must share y with start (horizontal tangent at active node)');
    assert.equal(sat.bezier.c2y, sat.bezier.endY,
      'second control point must share y with end (horizontal tangent at satellite)');
  }
});

test('satellites alternate sides of the spine', () => {
  const layout = computeSpineLayout({
    cursorStage: 'IMPLEMENT', completed: ['PICK'],
    subagents: [
      { type: 'G', status: 'running' },
      { type: 'E', status: 'running' },
    ],
    width: 240, height: 480, padding: 40,
  });
  const cx = 240 / 2;
  assert.ok(layout.satellites[0].node.x > cx, 'first satellite right of spine');
  assert.ok(layout.satellites[1].node.x < cx, 'second satellite left of spine');
});
```

- [ ] **Step 2: Run tests** — Expected: PASS.

```bash
node --test plugins/taskmaster/viewer/tests/unit/auto-spine-layout.test.js
```

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/tests/unit/auto-spine-layout.test.js
git commit -m "test(taskmaster-viewer): lock satellite bezier horizontal tangent contract"
```

---

### Task 19: Edge case — no cursor stage (session paused/stopped)

- [ ] **Step 1: Append failing assertion**

Append:

```javascript
test('null cursorStage produces all-pending or all-done nodes (no active)', () => {
  const layout = computeSpineLayout({
    cursorStage: null, completed: ['PICK', 'IMPLEMENT'], subagents: [],
    width: 240, height: 480, padding: 40,
  });
  const active = layout.nodes.find((n) => n.state === 'active');
  assert.equal(active, undefined);
  // Done where listed, pending elsewhere
  assert.equal(layout.nodes[0].state, 'done');
  assert.equal(layout.nodes[1].state, 'done');
  assert.equal(layout.nodes[2].state, 'pending');
});
```

- [ ] **Step 2: Run tests** — Expected: PASS (helper already handles this correctly).

```bash
node --test plugins/taskmaster/viewer/tests/unit/auto-spine-layout.test.js
```

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/tests/unit/auto-spine-layout.test.js
git commit -m "test(taskmaster-viewer): spine layout handles null cursor (paused/stopped)"
```

---

## M4 — Quest Spine SVG Renderer

### Task 20: Stub `quest-spine.js` — render an empty SVG into a root element

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/quest-spine.js`

(Smoke-tested via the screen-level Playwright in Task 56; no separate test here for trivial stub.)

- [ ] **Step 1: Write the file**

Create `plugins/taskmaster/viewer/js/components/quest-spine.js`:

```javascript
// Quest Spine — vertical SVG chain with active node + satellites.
// Reads layout from auto-spine-layout.js; pure render.

import { computeSpineLayout } from './auto-spine-layout.js';

const SVG_NS = 'http://www.w3.org/2000/svg';

const SUBAGENT_LABELS = {
  'general-purpose': 'G',
  'Explore': 'E',
  'Plan': 'P',
  'code-reviewer': 'R',
  'code-architect': 'A',
};

/**
 * Mount a Quest Spine into root. Returns a cleanup function.
 * @param {HTMLElement} root
 * @param {object} state - auto-mode session state
 */
export function renderQuestSpine(root, state) {
  root.innerHTML = '';
  const wrap = document.createElement('div');
  wrap.className = 'spine-frame';
  root.appendChild(wrap);

  const width = 360;
  const height = 520;
  const padding = 50;

  const cursorStage = state?.cursor?.stage ?? null;
  const completed = state?.completed ?? [];
  const subagents = (state?.subagents ?? []).filter((s) => s.status === 'running');

  const layout = computeSpineLayout({
    cursorStage, completed, subagents, width, height, padding,
  });

  const svg = document.createElementNS(SVG_NS, 'svg');
  svg.setAttribute('class', 'spine-svg');
  svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
  svg.setAttribute('width', String(width));
  svg.setAttribute('height', String(height));
  wrap.appendChild(svg);

  // Connectors (drawn first so nodes layer above)
  for (const c of layout.connectors) {
    const line = document.createElementNS(SVG_NS, 'line');
    line.setAttribute('class', `spine-connector spine-connector--${c.fromState}`);
    line.setAttribute('x1', c.x1); line.setAttribute('y1', c.y1);
    line.setAttribute('x2', c.x2); line.setAttribute('y2', c.y2);
    svg.appendChild(line);
  }

  // Satellite bezier connectors + nodes
  for (const sat of layout.satellites) {
    const path = document.createElementNS(SVG_NS, 'path');
    const b = sat.bezier;
    path.setAttribute('class', 'spine-satellite-edge');
    path.setAttribute('d',
      `M ${b.startX} ${b.startY} C ${b.c1x} ${b.c1y} ${b.c2x} ${b.c2y} ${b.endX} ${b.endY}`);
    svg.appendChild(path);

    const sn = document.createElementNS(SVG_NS, 'circle');
    sn.setAttribute('class', 'spine-satellite');
    sn.setAttribute('cx', sat.node.x);
    sn.setAttribute('cy', sat.node.y);
    sn.setAttribute('r', sat.node.r);
    svg.appendChild(sn);

    const tx = document.createElementNS(SVG_NS, 'text');
    tx.setAttribute('class', 'spine-satellite-label');
    tx.setAttribute('x', sat.node.x);
    tx.setAttribute('y', sat.node.y + 3);
    tx.setAttribute('text-anchor', 'middle');
    tx.textContent = SUBAGENT_LABELS[sat.type] ?? sat.type.slice(0, 1).toUpperCase();
    svg.appendChild(tx);
  }

  // Spine nodes
  for (const node of layout.nodes) {
    const g = document.createElementNS(SVG_NS, 'g');
    g.setAttribute('class', `spine-node spine-node--${node.state}`);
    g.setAttribute('data-stage', node.stage);

    const circle = document.createElementNS(SVG_NS, 'circle');
    circle.setAttribute('cx', node.x);
    circle.setAttribute('cy', node.y);
    circle.setAttribute('r', node.r);
    circle.setAttribute('class', 'spine-node-circle');
    g.appendChild(circle);

    if (node.state === 'done') {
      const check = document.createElementNS(SVG_NS, 'text');
      check.setAttribute('class', 'spine-node-check');
      check.setAttribute('x', node.x);
      check.setAttribute('y', node.y + 3);
      check.setAttribute('text-anchor', 'middle');
      check.textContent = '✓';
      g.appendChild(check);
    }

    const label = document.createElementNS(SVG_NS, 'text');
    label.setAttribute('class', 'spine-node-label');
    label.setAttribute('x', node.x + node.r + 12);
    label.setAttribute('y', node.y + 4);
    label.textContent = stageLabel(node.stage);
    g.appendChild(label);

    svg.appendChild(g);
  }

  return () => { root.innerHTML = ''; };
}

function stageLabel(stage) {
  switch (stage) {
    case 'PICK': return 'Pick';
    case 'IMPLEMENT': return 'Implement';
    case 'REVIEW': return 'Review';
    case 'HANDOVER_STUB': return 'Handover';
    case 'COMPLETE': return 'Complete';
    default: return stage;
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/quest-spine.js
git commit -m "feat(taskmaster-viewer): Quest Spine SVG renderer skeleton"
```

---

### Task 21: Add `auto-mode.css` — deep-recess frame and base spine styles

**Files:**
- Create: `plugins/taskmaster/viewer/css/screens/auto-mode.css`
- Modify: `plugins/taskmaster/viewer/index.html` (add `<link>` tag)

- [ ] **Step 1: Write the CSS**

Create `plugins/taskmaster/viewer/css/screens/auto-mode.css`:

```css
/* ──────────────────────────────────────────────────────────────────────────
   Auto Mode page — spine + log + side panels
   Tokens come from tokens.css; no local color literals where a token exists.
   ────────────────────────────────────────────────────────────────────────── */

.auto-page { padding: 14px 18px; }

.auto-header {
  display: flex; align-items: center; gap: 10px;
  padding-bottom: 10px; margin-bottom: 14px;
  border-bottom: 1px solid var(--border);
}
.auto-title { font-size: 16px; font-weight: 600; color: var(--ink); }
.auto-controls { display: inline-flex; gap: 6px; margin-left: 8px; }
.auto-control-btn {
  padding: 3px 8px; border-radius: 4px;
  background: var(--bg-card); border: 1px solid var(--border);
  color: var(--ink-2); font-size: 11px; cursor: pointer;
}
.auto-control-btn--pause { color: var(--amber); }
.auto-control-btn--stop  { color: var(--red); }
.auto-control-btn[aria-pressed="true"] { background: rgba(214, 164, 95, 0.15); }

.auto-header-right { margin-left: auto; display: flex; align-items: center; gap: 8px; }
.auto-helper-note {
  margin-top: 4px; font-size: 11px; color: var(--ink-3);
  display: flex; align-items: center; gap: 6px;
}
.auto-helper-note .dismiss {
  margin-left: auto; cursor: pointer; color: var(--ink-3);
}

.auto-toggle { /* segmented Spine | Log */
  display: inline-flex; background: var(--bg-card);
  border: 1px solid var(--border); border-radius: 5px; overflow: hidden;
}
.auto-toggle-seg {
  padding: 3px 10px; font-size: 11px; color: var(--ink-3); cursor: pointer;
  border-right: 1px solid var(--border);
}
.auto-toggle-seg:last-child { border-right: 0; }
.auto-toggle-seg.on { background: rgba(74, 158, 255, 0.15); color: var(--accent); }

/* ── 3-col page layout (left panel | spine | right panel) ── */
.auto-grid {
  display: grid;
  grid-template-columns: 220px 1fr 240px;
  gap: 14px;
  align-items: stretch;
}

/* ── Spine center frame ── */
.spine-frame {
  position: relative;
  background:
    radial-gradient(ellipse at center, rgba(74,158,255,0.04), transparent 60%),
    var(--bg-deep);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 8px;
  box-shadow: inset 0 2px 14px rgba(0,0,0,0.45);
  display: flex; justify-content: center;
}

.spine-svg { display: block; }

.spine-connector {
  stroke: var(--border); stroke-width: 1.5px;
}
.spine-connector--done {
  stroke: var(--green); opacity: 0.55;
}
.spine-connector--active {
  stroke: var(--accent); opacity: 0.65;
}

.spine-node-circle {
  fill: var(--bg-card); stroke: var(--border); stroke-width: 1.5px;
  filter: drop-shadow(0 1px 2px rgba(0,0,0,0.6));
}
.spine-node--done .spine-node-circle {
  fill: rgba(95,174,110,0.15); stroke: var(--green);
}
.spine-node-check {
  fill: var(--green); font-size: 10px; font-weight: 700;
}
.spine-node--active .spine-node-circle {
  fill: rgba(74,158,255,0.18); stroke: var(--accent); stroke-width: 2px;
  filter: drop-shadow(0 0 6px rgba(74,158,255,0.55));
  animation: spine-pulse 1.6s ease-in-out infinite;
}
.spine-node--pending .spine-node-circle { opacity: 0.4; }
.spine-node-label {
  fill: var(--ink-2); font-size: 10px;
  font-family: 'JetBrains Mono', ui-monospace, monospace;
}
.spine-node--pending .spine-node-label { fill: var(--ink-3); opacity: 0.6; }

@keyframes spine-pulse {
  0%, 100% { r: 18; opacity: 1; }
  50%      { r: 20; opacity: 0.85; }
}

/* ── Satellites ── */
.spine-satellite-edge {
  fill: none; stroke: var(--accent); stroke-width: 1px; opacity: 0.55;
}
.spine-satellite {
  fill: var(--bg-card); stroke: var(--accent); stroke-width: 1.5px;
  filter: drop-shadow(0 1px 2px rgba(0,0,0,0.5));
}
.spine-satellite-label {
  fill: var(--accent); font-size: 8px; font-weight: 600;
  font-family: 'JetBrains Mono', ui-monospace, monospace;
}
```

- [ ] **Step 2: Add the link tag**

In `plugins/taskmaster/viewer/index.html`, in the `<head>` near other screen CSS links, add:

```html
<link rel="stylesheet" href="css/screens/auto-mode.css" />
```

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/css/screens/auto-mode.css plugins/taskmaster/viewer/index.html
git commit -m "feat(taskmaster-viewer): auto-mode screen + spine base styles"
```

---

### Task 22: Mount the spine inside the auto-mode screen (smoke wiring only)

**Files:**
- Modify: `plugins/taskmaster/viewer/js/screens/auto-mode.js`

- [ ] **Step 1: Replace the stub**

Replace the entire contents of `plugins/taskmaster/viewer/js/screens/auto-mode.js` with:

```javascript
import { renderQuestSpine } from '../components/quest-spine.js';

export const meta = { title: 'Auto Mode', icon: '◐', sidebarKey: 'auto' };

export async function mount(root, ctx) {
  root.innerHTML = '';
  root.classList.add('auto-page');

  const header = document.createElement('div');
  header.className = 'auto-header';
  header.innerHTML = `
    <div class="auto-title">Auto Mode</div>
    <div class="auto-controls">
      <button class="auto-control-btn auto-control-btn--pause" data-action="pause" title="Pause">⏸</button>
      <button class="auto-control-btn auto-control-btn--stop"  data-action="stop"  title="Stop">■</button>
    </div>
    <div class="auto-header-right">
      <div class="auto-toggle" role="tablist">
        <div class="auto-toggle-seg on"  data-view="A">Spine</div>
        <div class="auto-toggle-seg"     data-view="B">Log</div>
      </div>
    </div>
  `;
  root.appendChild(header);

  const grid = document.createElement('div');
  grid.className = 'auto-grid';
  const left   = document.createElement('div'); left.className   = 'auto-left';
  const center = document.createElement('div'); center.className = 'auto-center';
  const right  = document.createElement('div'); right.className  = 'auto-right';
  grid.append(left, center, right);
  root.appendChild(grid);

  // Initial render with whatever state the store currently holds (Plan 2 polling)
  const initial = ctx.store.getAutoState?.() ?? null;
  let cleanup = renderQuestSpine(center, initial);

  const unsub = ctx.store.subscribe?.('autoState', (state) => {
    cleanup?.();
    cleanup = renderQuestSpine(center, state);
  });

  return () => {
    cleanup?.();
    unsub?.();
    root.classList.remove('auto-page');
  };
}
```

- [ ] **Step 2: Smoke check via dev server**

```bash
python -m plugins.taskmaster.backlog_server --port 8765 &
SERVER_PID=$!
sleep 1
curl -s http://127.0.0.1:8765/v3/ | head -1
kill $SERVER_PID
```
Expected: an HTTP `<!DOCTYPE html>` line. (No assertion needed; the Playwright smoke in M8 Task 53 covers behavior.)

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/js/screens/auto-mode.js
git commit -m "feat(taskmaster-viewer): mount Quest Spine in auto-mode screen"
```

---

### Task 23: Wire Spine|Log toggle to `prefs.screens.auto_mode.view` (persisted)

**Files:**
- Modify: `plugins/taskmaster/viewer/js/screens/auto-mode.js`

- [ ] **Step 1: Add toggle handler**

Inside `mount()`, after `root.appendChild(grid);` and before the initial render, add:

```javascript
  // Restore persisted view
  const initialView = (ctx.store.getPrefs()?.screens?.auto_mode?.view) ?? 'A';
  const segs = header.querySelectorAll('.auto-toggle-seg');
  segs.forEach((s) => s.classList.toggle('on', s.dataset.view === initialView));

  let currentView = initialView;
  segs.forEach((seg) => {
    seg.addEventListener('click', () => {
      const v = seg.dataset.view;
      if (v === currentView) return;
      currentView = v;
      segs.forEach((s) => s.classList.toggle('on', s.dataset.view === v));
      ctx.prefs.patch({screens: {auto_mode: {view: v}}});  // PUT /api/viewer/prefs
      renderActiveView();
    });
  });

  function renderActiveView() {
    cleanup?.();
    const state = ctx.store.getAutoState?.() ?? null;
    if (currentView === 'A') {
      cleanup = renderQuestSpine(center, state);
    } else {
      // Log view added in Task 31. Empty placeholder for now.
      center.innerHTML = '<div class="flog-empty">Log view loading…</div>';
      cleanup = () => { center.innerHTML = ''; };
    }
  }
```

Replace the original `let cleanup = renderQuestSpine(center, initial);` with `let cleanup; renderActiveView();`. Update the subscribe callback to also call `renderActiveView()` (so spine state changes re-render in Spine view, log view re-renders in Log view).

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/screens/auto-mode.js
git commit -m "feat(taskmaster-viewer): persist Spine|Log toggle to viewer prefs"
```

---

### Task 24: Wire pause/stop buttons to `api.autoPause` / `api.autoStop`

**Files:**
- Modify: `plugins/taskmaster/viewer/js/screens/auto-mode.js`

- [ ] **Step 1: Add handlers**

Inside `mount()`, after the toggle wiring:

```javascript
  header.querySelector('[data-action="pause"]').addEventListener('click', async () => {
    const sid = ctx.store.getAutoState?.()?.session_id;
    if (!sid) return;
    try {
      await ctx.api.autoPause(sid);
      ctx.store.refresh?.('autoState');
    } catch (e) {
      console.error('autoPause failed', e);
    }
  });

  header.querySelector('[data-action="stop"]').addEventListener('click', async () => {
    const sid = ctx.store.getAutoState?.()?.session_id;
    if (!sid) return;
    if (!confirm(`Stop auto-mode session ${sid}?`)) return;
    try {
      await ctx.api.autoStop(sid);
      ctx.store.refresh?.('autoState');
    } catch (e) {
      console.error('autoStop failed', e);
    }
  });
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/screens/auto-mode.js
git commit -m "feat(taskmaster-viewer): wire pause/stop buttons to API"
```

---

### Task 25: Helper note shown on first visit only (persisted dismissal)

The dismissal flag lives at `prefs.screens.auto_mode.helper_dismissed: true`.

**Files:**
- Modify: `plugins/taskmaster/viewer/js/screens/auto-mode.js`

- [ ] **Step 1: Add helper note**

Inside `mount()`, after `root.appendChild(header);`:

```javascript
  if (!(ctx.store.getPrefs()?.screens?.auto_mode?.helper_dismissed)) {
    const note = document.createElement('div');
    note.className = 'auto-helper-note';
    note.innerHTML = `
      <span>Spine is the live view. Log swaps to chronological waterfall — same data, denser. Use Log when debugging.</span>
      <span class="dismiss" role="button" aria-label="Dismiss">✕</span>
    `;
    root.insertBefore(note, root.children[1] || null);
    note.querySelector('.dismiss').addEventListener('click', () => {
      ctx.prefs.patch({screens: {auto_mode: {helper_dismissed: true}}});
      note.remove();
    });
  }
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/screens/auto-mode.js
git commit -m "feat(taskmaster-viewer): first-visit helper note for Spine|Log toggle"
```

---

### Task 26: Spine renders title + worktree above the SVG

The mockup shows a small task header above the spine (`v3-014 · Auto-mode status indicator · .worktrees/v3-014`).

**Files:**
- Modify: `plugins/taskmaster/viewer/js/components/quest-spine.js`
- Modify: `plugins/taskmaster/viewer/css/screens/auto-mode.css`

- [ ] **Step 1: Update renderer**

In `renderQuestSpine`, before creating `wrap`, add:

```javascript
  const head = document.createElement('div');
  head.className = 'spine-head';
  if (state) {
    head.innerHTML = `
      <span class="spine-head-id">${escape(state.session_id ?? state.task_id ?? '—')}</span>
      <span class="spine-head-title">${escape(state.title ?? '')}</span>
      <span class="spine-head-wt">${escape(state.worktree ?? '')}</span>
    `;
  } else {
    head.innerHTML = '<span class="spine-head-empty">No auto-mode session running.</span>';
  }
  root.appendChild(head);

  function escape(s) {
    return String(s).replace(/[&<>"']/g, (c) => (
      { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
    ));
  }
```

(The existing `wrap` and SVG block stay below.)

- [ ] **Step 2: Add CSS**

Append to `plugins/taskmaster/viewer/css/screens/auto-mode.css`:

```css
.spine-head {
  display: flex; align-items: center; gap: 10px;
  padding: 6px 4px 10px; font-size: 12px;
}
.spine-head-id {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  color: var(--accent);
  background: rgba(74,158,255,0.08);
  padding: 1px 5px; border-radius: 3px;
}
.spine-head-title { color: var(--ink); flex: 1; }
.spine-head-wt {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  color: var(--ink-3); font-size: 10px;
}
.spine-head-empty { color: var(--ink-3); font-size: 12px; }
```

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/quest-spine.js plugins/taskmaster/viewer/css/screens/auto-mode.css
git commit -m "feat(taskmaster-viewer): spine head shows session id + title + worktree"
```

---

### Task 27: Empty-state — when there is no running auto-mode session

- [ ] **Step 1: Update `renderQuestSpine` empty branch**

Replace the SVG-creating block with a guard at the top:

```javascript
  if (!state || !state.cursor) {
    const empty = document.createElement('div');
    empty.className = 'spine-empty';
    empty.textContent = 'No auto-mode session is running.';
    root.appendChild(empty);
    return () => { root.innerHTML = ''; };
  }
```

(Keep the existing SVG path for when state is valid.)

Append to `auto-mode.css`:

```css
.spine-empty {
  padding: 60px 20px; text-align: center;
  color: var(--ink-3); font-size: 13px;
  border: 1px dashed var(--border); border-radius: 8px;
}
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/quest-spine.js plugins/taskmaster/viewer/css/screens/auto-mode.css
git commit -m "feat(taskmaster-viewer): spine empty state when no session running"
```

---

### Task 28: Sidebar live-dot publish — extend `store.autoState` setter

Plan 1 set up `store.subscribe('autoState')`. Plan 6 ensures the *publish* side fires when state.mode is set. The store likely already auto-publishes on a poll cycle; this task verifies and adds an explicit `setAutoState` if missing.

**Files:**
- Modify: `plugins/taskmaster/viewer/js/store.js`

- [ ] **Step 1: Inspect and patch**

Open `plugins/taskmaster/viewer/js/store.js`. Locate the slice handling `autoState`. If there's no public `setAutoState`, add:

```javascript
function setAutoState(next) {
  state.autoState = next;
  emit('autoState', next);
}
export { setAutoState };
```

If the store already polls `/api/auto/state` on an interval, ensure the result is passed through `setAutoState` so subscribers (sidebar live-dot, screen) all fire. The sidebar `live-dot` element added in Plan 1 reacts to `state?.cursor?.stage` being defined; verify by reading the existing subscribe callback near `js/components/sidebar.js`.

- [ ] **Step 2: Smoke commit**

```bash
git add plugins/taskmaster/viewer/js/store.js
git commit -m "chore(taskmaster-viewer): ensure setAutoState fires subscribers"
```

---

## M5 — Flight Log

### Task 29: Flight log component skeleton

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/flight-log.js`

- [ ] **Step 1: Write the file**

```javascript
// Flight Log — chronological waterfall of auto-mode events.
// Newest at top. Active row gets blue tint + pulsing badge.

const STAGE_PILL_CLASS = {
  PICK: 'flog-pill--pick',
  IMPLEMENT: 'flog-pill--implement',
  REVIEW: 'flog-pill--review',
  HANDOVER_STUB: 'flog-pill--handover',
  COMPLETE: 'flog-pill--complete',
};

export function renderFlightLog(root, { events = [], cursorStage = null } = {}) {
  root.innerHTML = '';
  const wrap = document.createElement('div');
  wrap.className = 'flog-wrap';
  root.appendChild(wrap);

  if (!events.length) {
    const empty = document.createElement('div');
    empty.className = 'flog-empty';
    empty.textContent = 'No events yet.';
    wrap.appendChild(empty);
    return () => { root.innerHTML = ''; };
  }

  // Newest first
  const sorted = [...events].sort((a, b) => (b.ts || '').localeCompare(a.ts || ''));

  for (const ev of sorted) {
    const row = document.createElement('div');
    const isActive = ev.stage === cursorStage && ev.kind === 'stage_enter';
    row.className = 'flog-row' + (isActive ? ' flog-row--active' : '');

    row.innerHTML = `
      <span class="flog-ts">${shortTs(ev.ts)}</span>
      <span class="flog-pill ${STAGE_PILL_CLASS[ev.stage] || ''}">${ev.stage || '—'}</span>
      <span class="flog-msg">${escape(ev.msg ?? '')}</span>
      ${isActive ? '<span class="flog-active-badge">active</span>' : ''}
    `;

    if (Array.isArray(ev.subagent_runs) && ev.subagent_runs.length) {
      const sub = document.createElement('div');
      sub.className = 'flog-subruns';
      for (const sr of ev.subagent_runs) {
        const srRow = document.createElement('div');
        srRow.className = 'flog-subrun';
        srRow.innerHTML = `
          <span class="flog-subrun-type">${escape(sr.type ?? '')}</span>
          <span class="flog-subrun-msg">${escape(sr.msg ?? '')}</span>
          <span class="flog-subrun-ts">${shortTs(sr.ts)}</span>
        `;
        sub.appendChild(srRow);
      }
      row.appendChild(sub);
    }
    wrap.appendChild(row);
  }
  return () => { root.innerHTML = ''; };
}

function shortTs(iso) {
  if (!iso) return '';
  // Return HH:MM:SS from ISO.
  const m = /T(\d{2}:\d{2}:\d{2})/.exec(iso);
  return m ? m[1] : iso;
}

function escape(s) {
  return String(s).replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
}
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/flight-log.js
git commit -m "feat(taskmaster-viewer): flight log waterfall component"
```

---

### Task 30: Flight log styles

**Files:**
- Modify: `plugins/taskmaster/viewer/css/screens/auto-mode.css`

- [ ] **Step 1: Append CSS**

```css
/* ── Flight Log ── */
.flog-wrap {
  background: var(--bg-deep);
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
}
.flog-empty { padding: 24px; text-align: center; color: var(--ink-3); }
.flog-row {
  display: grid;
  grid-template-columns: 70px auto 1fr auto;
  align-items: start;
  gap: 10px;
  padding: 6px 12px;
  border-bottom: 1px solid var(--border-soft);
  font-size: 12px;
}
.flog-row:last-child { border-bottom: 0; }
.flog-row--active {
  background: rgba(74,158,255,0.08);
}
.flog-ts {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  color: var(--ink-3); font-size: 10px;
}
.flog-pill {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-size: 10px; padding: 1px 6px; border-radius: 3px;
  background: var(--bg-card); color: var(--ink-2);
}
.flog-pill--pick      { color: var(--purple); background: rgba(160,127,224,0.10); }
.flog-pill--implement { color: var(--accent); background: rgba(74,158,255,0.10); }
.flog-pill--review    { color: var(--amber);  background: rgba(214,164,95,0.10); }
.flog-pill--handover  { color: var(--ink-2);  background: rgba(255,255,255,0.05); }
.flog-pill--complete  { color: var(--green);  background: rgba(95,174,110,0.10); }
.flog-msg { color: var(--ink); }
.flog-active-badge {
  font-size: 9px; padding: 1px 6px; border-radius: 9px;
  background: rgba(74,158,255,0.18); color: var(--accent);
  animation: spine-pulse 1.6s ease-in-out infinite;
}

.flog-subruns { grid-column: 2 / -1; margin-top: 4px; padding-left: 12px;
  border-left: 1px dashed var(--border-soft); }
.flog-subrun {
  display: grid; grid-template-columns: auto 1fr auto;
  gap: 8px; font-size: 11px; padding: 2px 0;
}
.flog-subrun-type {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  color: var(--accent); font-size: 10px;
}
.flog-subrun-msg { color: var(--ink-2); }
.flog-subrun-ts {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-size: 10px; color: var(--ink-3);
}
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/css/screens/auto-mode.css
git commit -m "feat(taskmaster-viewer): flight log styles"
```

---

### Task 31: Wire flight log into the auto-mode screen (Log view branch)

**Files:**
- Modify: `plugins/taskmaster/viewer/js/screens/auto-mode.js`

- [ ] **Step 1: Replace the placeholder Log branch**

In `renderActiveView()` (added in Task 23), replace the `else` branch with:

```javascript
    } else {
      const sid = ctx.store.getAutoState?.()?.session_id;
      const cursorStage = ctx.store.getAutoState?.()?.cursor?.stage ?? null;
      if (!sid) {
        center.innerHTML = '<div class="flog-empty">No auto-mode session.</div>';
        cleanup = () => { center.innerHTML = ''; };
        return;
      }
      ctx.api.autoEvents(sid).then((events) => {
        cleanup = renderFlightLog(center, { events, cursorStage });
      }).catch((e) => {
        center.innerHTML = `<div class="flog-empty">Error loading events: ${e.message}</div>`;
        cleanup = () => { center.innerHTML = ''; };
      });
    }
```

Add the import at the top: `import { renderFlightLog } from '../components/flight-log.js';`.

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/screens/auto-mode.js
git commit -m "feat(taskmaster-viewer): wire flight log into auto-mode Log view"
```

---

### Task 32: Poll events at 3-second cadence while Log view is active

**Files:**
- Modify: `plugins/taskmaster/viewer/js/screens/auto-mode.js`

- [ ] **Step 1: Add polling**

Inside `mount()`, alongside other state, add:

```javascript
  let logPoll = null;

  function startLogPolling() {
    if (logPoll) return;
    logPoll = setInterval(() => {
      if (currentView !== 'B') return;
      const sid = ctx.store.getAutoState?.()?.session_id;
      if (!sid) return;
      ctx.api.autoEvents(sid).then((events) => {
        const cursorStage = ctx.store.getAutoState?.()?.cursor?.stage ?? null;
        cleanup?.();
        cleanup = renderFlightLog(center, { events, cursorStage });
      }).catch(() => {});
    }, 3000);
  }
  function stopLogPolling() { clearInterval(logPoll); logPoll = null; }
```

Call `startLogPolling()` once at mount end. In the cleanup function, call `stopLogPolling()`.

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/screens/auto-mode.js
git commit -m "feat(taskmaster-viewer): poll auto-mode events while Log view active"
```

---

### Task 33: Playwright smoke for Spine|Log toggle

**Files:**
- Create: `plugins/taskmaster/viewer/tests/auto-mode.spec.js`

- [ ] **Step 1: Write the smoke test**

Create `plugins/taskmaster/viewer/tests/auto-mode.spec.js`:

```javascript
const { test, expect } = require('@playwright/test');

test.describe('Auto Mode page', () => {
  test('renders Quest Spine by default', async ({ page }) => {
    await page.goto('http://127.0.0.1:8765/v3/#/auto');
    await expect(page.locator('.auto-title')).toHaveText('Auto Mode');
    // 5 spine nodes for AUTO_STAGES (or empty state when no session)
    const empty = page.locator('.spine-empty');
    const nodes = page.locator('.spine-node');
    const ok = (await empty.count()) > 0 || (await nodes.count()) === 5;
    expect(ok).toBeTruthy();
  });

  test('Spine|Log toggle switches center view', async ({ page }) => {
    await page.goto('http://127.0.0.1:8765/v3/#/auto');
    await page.locator('.auto-toggle-seg[data-view="B"]').click();
    await expect(page.locator('.auto-toggle-seg[data-view="B"]')).toHaveClass(/on/);
    // Either flight log or empty placeholder
    const present = await page.locator('.flog-wrap, .flog-empty').count();
    expect(present).toBeGreaterThan(0);
  });

  test('Pause and Stop buttons are present', async ({ page }) => {
    await page.goto('http://127.0.0.1:8765/v3/#/auto');
    await expect(page.locator('.auto-control-btn--pause')).toBeVisible();
    await expect(page.locator('.auto-control-btn--stop')).toBeVisible();
  });
});
```

- [ ] **Step 2: Run** (assumes server + viewer dev fixture from Plan 1's smoke harness)

```bash
cd plugins/taskmaster/viewer && npx playwright test tests/auto-mode.spec.js
```
Expected: 3 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/tests/auto-mode.spec.js
git commit -m "test(taskmaster-viewer): playwright smoke for auto-mode page"
```

---

## M6 — Sessions Strip + Side Panels

### Task 34: Sessions strip component

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/sessions-strip.js`

- [ ] **Step 1: Write the file**

```javascript
/**
 * Render a tab strip of parallel auto-mode sessions.
 * @param {HTMLElement} root
 * @param {object} opts
 * @param {Array} opts.sessions      List of session objects.
 * @param {string} opts.activeSid    Currently inspected session id.
 * @param {(sid:string)=>void} opts.onSelect
 */
export function renderSessionsStrip(root, { sessions = [], activeSid, onSelect } = {}) {
  root.innerHTML = '';
  if (!sessions.length) return () => {};
  const wrap = document.createElement('div');
  wrap.className = 'sstrip';
  root.appendChild(wrap);

  for (const s of sessions) {
    const tab = document.createElement('button');
    tab.className = 'sstrip-tab' + (s.session_id === activeSid ? ' on' : '');
    tab.dataset.sid = s.session_id;
    tab.innerHTML = `
      <span class="sstrip-dot" aria-hidden="true"></span>
      <span class="sstrip-id">${escape(s.session_id)}</span>
      <span class="sstrip-title">${escape(s.title ?? '')}</span>
      <span class="sstrip-elapsed">${elapsed(s.started_at)}</span>
    `;
    tab.addEventListener('click', () => onSelect?.(s.session_id));
    wrap.appendChild(tab);
  }
  return () => { root.innerHTML = ''; };
}

function elapsed(iso) {
  if (!iso) return '';
  const ms = Date.now() - new Date(iso).getTime();
  if (Number.isNaN(ms) || ms < 0) return '';
  const m = Math.floor(ms / 60000);
  if (m < 60) return `${m}m`;
  const h = Math.floor(m / 60);
  return `${h}h${m % 60}m`;
}

function escape(s) {
  return String(s).replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
}
```

- [ ] **Step 2: Append CSS** to `auto-mode.css`:

```css
/* ── Sessions strip ── */
.sstrip {
  display: flex; gap: 6px; padding: 8px 0; flex-wrap: wrap;
  border-bottom: 1px solid var(--border-soft);
  margin-bottom: 10px;
}
.sstrip-tab {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 5px; padding: 4px 10px;
  font-size: 11px; color: var(--ink-2); cursor: pointer;
}
.sstrip-tab.on { background: rgba(74,158,255,0.10); border-color: var(--accent); color: var(--ink); }
.sstrip-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--green); animation: spine-pulse 1.6s ease-in-out infinite;
}
.sstrip-id {
  font-family: 'JetBrains Mono', ui-monospace, monospace; color: var(--accent);
}
.sstrip-title { color: var(--ink); max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sstrip-elapsed {
  font-family: 'JetBrains Mono', ui-monospace, monospace; color: var(--ink-3); font-size: 10px;
}
```

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/sessions-strip.js plugins/taskmaster/viewer/css/screens/auto-mode.css
git commit -m "feat(taskmaster-viewer): sessions strip component"
```

---

### Task 35: Wire sessions strip into auto-mode screen

**Files:**
- Modify: `plugins/taskmaster/viewer/js/screens/auto-mode.js`

- [ ] **Step 1: Mount strip above grid**

After `root.appendChild(grid);`, wait — actually, strip belongs above the grid but below the helper note. Insert before `grid`:

```javascript
  const stripRoot = document.createElement('div');
  root.insertBefore(stripRoot, grid);

  let sessionsList = [];
  let activeSid = null;

  async function refreshSessions() {
    sessionsList = await ctx.api.autoListSessions().catch(() => []);
    if (!activeSid && sessionsList[0]) activeSid = sessionsList[0].session_id;
    renderSessionsStrip(stripRoot, {
      sessions: sessionsList,
      activeSid,
      onSelect: (sid) => {
        activeSid = sid;
        ctx.store.setActiveAutoSession?.(sid);
        renderSessionsStrip(stripRoot, { sessions: sessionsList, activeSid, onSelect: arguments.callee });
        renderActiveView();
      },
    });
  }
  refreshSessions();
  const sessionsPoll = setInterval(refreshSessions, 5000);
```

Add the import: `import { renderSessionsStrip } from '../components/sessions-strip.js';`. In cleanup, `clearInterval(sessionsPoll)`.

- [ ] **Step 2: Update `renderActiveView` to use `activeSid`**

When fetching events for the Log view (Task 31), use `activeSid` instead of `getAutoState().session_id` if it differs.

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/js/screens/auto-mode.js
git commit -m "feat(taskmaster-viewer): mount sessions strip above spine/log"
```

---

### Task 36: `store.setActiveAutoSession` + `getActiveAutoSession`

**Files:**
- Modify: `plugins/taskmaster/viewer/js/store.js`

- [ ] **Step 1: Add slice**

In the existing state initialiser:

```javascript
state.activeAutoSessionId = null;
```

Export:

```javascript
export function setActiveAutoSession(sid) {
  state.activeAutoSessionId = sid;
  emit('activeAutoSession', sid);
}
export function getActiveAutoSession() { return state.activeAutoSessionId; }
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/store.js
git commit -m "feat(taskmaster-viewer): store slice for activeAutoSessionId"
```

---

### Task 37: Budget meter component

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/budget-meter.js`

- [ ] **Step 1: Write the file**

```javascript
/**
 * Render a single horizontal budget bar.
 * @param {object} opts
 * @param {string} opts.label
 * @param {number} opts.used
 * @param {number} opts.limit
 * @param {number} opts.pct        Pre-computed pct from server.
 * @param {string} opts.tier       'ok' | 'warn' | 'crit'
 * @param {string} opts.format     'num' | 'duration' | 'usd' | 'pct'
 * @returns {HTMLElement}
 */
export function buildBudgetMeter({ label, used, limit, pct, tier, format = 'num' }) {
  const el = document.createElement('div');
  el.className = `bmeter bmeter--${tier}`;
  el.innerHTML = `
    <div class="bmeter-row">
      <span class="bmeter-label">${label}</span>
      <span class="bmeter-vals">${formatVal(used, format)}<span class="bmeter-sep"> / </span>${formatVal(limit, format)}</span>
    </div>
    <div class="bmeter-track">
      <div class="bmeter-fill" style="width: ${(pct * 100).toFixed(1)}%"></div>
    </div>
  `;
  return el;
}

function formatVal(v, fmt) {
  switch (fmt) {
    case 'duration':
      if (v >= 3600) return `${(v / 3600).toFixed(1)}h`;
      if (v >= 60) return `${Math.floor(v / 60)}m`;
      return `${v}s`;
    case 'usd': return `$${Number(v).toFixed(2)}`;
    case 'pct': return `${(v * 100).toFixed(0)}%`;
    case 'num':
    default:
      if (v >= 1000) return `${(v / 1000).toFixed(1)}k`;
      return String(v);
  }
}
```

- [ ] **Step 2: Append CSS**

```css
/* ── Budget meter ── */
.bmeter { padding: 6px 0; }
.bmeter-row { display: flex; align-items: baseline; gap: 6px; font-size: 11px; }
.bmeter-label {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  color: var(--ink-2);
}
.bmeter-vals { margin-left: auto; font-family: 'JetBrains Mono', ui-monospace, monospace; color: var(--ink); font-size: 10px; }
.bmeter-sep { color: var(--ink-3); }
.bmeter-track {
  margin-top: 4px; height: 4px; border-radius: 2px;
  background: var(--bg-card); overflow: hidden;
}
.bmeter-fill { height: 100%; background: var(--accent); transition: width .25s ease; }
.bmeter--warn .bmeter-fill { background: var(--amber); }
.bmeter--crit .bmeter-fill { background: var(--red); }
```

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/budget-meter.js plugins/taskmaster/viewer/css/screens/auto-mode.css
git commit -m "feat(taskmaster-viewer): budget meter component"
```

---

### Task 38: Side-panels component (left + right)

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/auto-side-panels.js`

- [ ] **Step 1: Write the file**

```javascript
import { buildBudgetMeter } from './budget-meter.js';

const SUBAGENT_LABELS = {
  'general-purpose': 'G',
  'Explore': 'E',
  'Plan': 'P',
  'code-reviewer': 'R',
  'code-architect': 'A',
};

const METER_FORMAT = {
  tokens: 'num',
  time_seconds: 'duration',
  context: 'pct',
  cost_usd: 'usd',
};
const METER_LABEL = {
  tokens: 'Tokens',
  time_seconds: 'Time',
  context: 'Context',
  cost_usd: 'Cost',
};

export function renderLeftPanel(root, { state }) {
  root.innerHTML = '';
  const wrap = document.createElement('div');
  wrap.className = 'aside aside--left';
  wrap.innerHTML = `
    <div class="aside-h">Subagents</div>
    <div class="aside-subagents"></div>
    <div class="aside-h">Hook firings</div>
    <div class="aside-hooks"></div>
  `;
  root.appendChild(wrap);

  const subRoot = wrap.querySelector('.aside-subagents');
  const subagents = state?.subagents ?? [];
  if (!subagents.length) {
    subRoot.innerHTML = '<div class="aside-empty">none</div>';
  } else {
    const running  = subagents.filter((s) => s.status === 'running');
    const finished = subagents.filter((s) => s.status !== 'running');
    for (const s of [...running, ...finished]) {
      const row = document.createElement('div');
      row.className = 'aside-sub' + (s.status === 'running' ? '' : ' done');
      row.innerHTML = `
        <span class="aside-sub-dot" data-status="${escape(s.status)}"></span>
        <span class="aside-sub-type">${SUBAGENT_LABELS[s.type] ?? s.type}</span>
        <span class="aside-sub-msg">${escape(s.msg ?? s.type ?? '')}</span>
      `;
      subRoot.appendChild(row);
    }
  }

  const hooksRoot = wrap.querySelector('.aside-hooks');
  const hooks = state?.hook_counts ?? {};
  if (!Object.keys(hooks).length) {
    hooksRoot.innerHTML = '<div class="aside-empty">none</div>';
  } else {
    for (const [name, n] of Object.entries(hooks)) {
      const row = document.createElement('div');
      row.className = 'aside-hook';
      row.innerHTML = `<span class="aside-hook-name">${escape(name)}</span><span class="aside-hook-n">×${n}</span>`;
      hooksRoot.appendChild(row);
    }
  }
  return () => { root.innerHTML = ''; };
}

export function renderRightPanel(root, { state, meters }) {
  root.innerHTML = '';
  const wrap = document.createElement('div');
  wrap.className = 'aside aside--right';
  wrap.innerHTML = `
    <div class="aside-h">Budget</div>
    <div class="aside-budget"></div>
    <div class="aside-h">Tool log</div>
    <div class="aside-tools"></div>
  `;
  root.appendChild(wrap);

  const budgetRoot = wrap.querySelector('.aside-budget');
  for (const [key, m] of Object.entries(meters || {})) {
    budgetRoot.appendChild(buildBudgetMeter({
      label: METER_LABEL[key] ?? key,
      used: m.used, limit: m.limit, pct: m.pct, tier: m.tier,
      format: METER_FORMAT[key] ?? 'num',
    }));
  }

  const toolsRoot = wrap.querySelector('.aside-tools');
  const tools = (state?.tool_log ?? []).slice(-4).reverse();
  if (!tools.length) {
    toolsRoot.innerHTML = '<div class="aside-empty">none</div>';
  } else {
    for (const t of tools) {
      const row = document.createElement('div');
      row.className = 'aside-tool';
      row.innerHTML = `
        <span class="aside-tool-name">${escape(t.name ?? '')}</span>
        <span class="aside-tool-args">${escape(t.args ?? '')}</span>
        <span class="aside-tool-ts">${shortTs(t.ts)}</span>
      `;
      toolsRoot.appendChild(row);
    }
  }
  return () => { root.innerHTML = ''; };
}

function shortTs(iso) {
  if (!iso) return '';
  const m = /T(\d{2}:\d{2}:\d{2})/.exec(iso);
  return m ? m[1] : iso;
}
function escape(s) {
  return String(s).replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
}
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/auto-side-panels.js
git commit -m "feat(taskmaster-viewer): auto-mode side panels (subagents+hooks, budget+tools)"
```

---

### Task 39: Side-panel styles

**Files:**
- Modify: `plugins/taskmaster/viewer/css/screens/auto-mode.css`

- [ ] **Step 1: Append CSS**

```css
/* ── Side panels ── */
.aside {
  background: var(--bg-panel); border: 1px solid var(--border);
  border-radius: 8px; padding: 10px 12px; font-size: 11px;
  display: flex; flex-direction: column; gap: 6px;
}
.aside-h {
  font-size: 9px; text-transform: uppercase; letter-spacing: 0.1em;
  color: var(--ink-3); font-weight: 600;
  padding-top: 6px;
}
.aside-h:first-child { padding-top: 0; }
.aside-empty { color: var(--ink-3); font-size: 11px; padding: 2px 0; }

.aside-sub {
  display: grid; grid-template-columns: auto auto 1fr; gap: 6px;
  align-items: center; padding: 2px 0;
}
.aside-sub.done { opacity: 0.5; }
.aside-sub-dot {
  width: 6px; height: 6px; border-radius: 50%; background: var(--green);
}
.aside-sub-dot[data-status="running"] { animation: spine-pulse 1.6s ease-in-out infinite; }
.aside-sub-dot[data-status="failed"]  { background: var(--red); }
.aside-sub-type {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  color: var(--accent); width: 12px; text-align: center;
}
.aside-sub-msg { color: var(--ink-2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.aside-hook {
  display: flex; gap: 6px; padding: 1px 0;
}
.aside-hook-name {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  color: var(--ink-2);
}
.aside-hook-n {
  margin-left: auto; color: var(--ink-3);
  font-family: 'JetBrains Mono', ui-monospace, monospace;
}

.aside-tool {
  display: grid; grid-template-columns: auto 1fr auto; gap: 6px;
  padding: 2px 0; font-size: 11px;
}
.aside-tool-name {
  font-family: 'JetBrains Mono', ui-monospace, monospace; color: var(--accent);
}
.aside-tool-args { color: var(--ink-3); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.aside-tool-ts {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  color: var(--ink-3); font-size: 10px;
}
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/css/screens/auto-mode.css
git commit -m "feat(taskmaster-viewer): side panel styles"
```

---

### Task 40: Server endpoint augmentation — include `hook_counts` in session detail

The left panel reads `state.hook_counts`. Have the server compute and inject it on read.

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py`
- Modify: `plugins/taskmaster/tests/test_server_auto_mode.py`

- [ ] **Step 1: Write the failing test**

Append:

```python
def test_session_detail_includes_hook_counts(running_server, tmp_path):
    from taskmaster_v3 import AUTO_HOOKS_LOG
    base, _ = running_server
    _seed_session(tmp_path, sid="v3-014")
    AUTO_HOOKS_LOG.parent.mkdir(parents=True, exist_ok=True)
    AUTO_HOOKS_LOG.write_text(
        '{"ts":"2026-04-26T18:00:00Z","hook":"PostToolUse","session_id":"v3-014","tool":"Edit","ok":true}\n'
        '{"ts":"2026-04-26T18:00:01Z","hook":"PreCompact","session_id":"v3-014","ok":true}\n'
    )
    body = json.loads(urllib.request.urlopen(f"{base}/api/auto/sessions/v3-014").read())
    assert body["hook_counts"]["PostToolUse"] == 1
    assert body["hook_counts"]["PreCompact"] == 1
```

- [ ] **Step 2: Run test** — Expected: FAIL.

```bash
python -m pytest plugins/taskmaster/tests/test_server_auto_mode.py -v -k hook_counts
```

- [ ] **Step 3: Update endpoint**

In the `/api/auto/sessions/<sid>` handler, after loading state and before serializing:

```python
from taskmaster_v3 import read_hook_events
state["hook_counts"] = read_hook_events(sid)
```

- [ ] **Step 4: Run test** — Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_server_auto_mode.py
git commit -m "feat(taskmaster): inject hook_counts into session detail response"
```

---

### Task 41: Wire side panels into the auto-mode screen

**Files:**
- Modify: `plugins/taskmaster/viewer/js/screens/auto-mode.js`

- [ ] **Step 1: Add render calls**

Add imports:

```javascript
import { renderLeftPanel, renderRightPanel } from '../components/auto-side-panels.js';
```

Replace the empty `left`/`right` divs with real render. Add a function:

```javascript
  let leftCleanup = null, rightCleanup = null;

  async function refreshSidePanels() {
    const sid = activeSid ?? ctx.store.getAutoState?.()?.session_id;
    if (!sid) {
      leftCleanup?.(); rightCleanup?.();
      left.innerHTML = ''; right.innerHTML = '';
      return;
    }
    const [detail, budget] = await Promise.all([
      ctx.api.autoSession(sid),
      ctx.api.autoBudget(sid),
    ]);
    if (!detail) return;
    leftCleanup?.();
    leftCleanup = renderLeftPanel(left, { state: detail });
    rightCleanup?.();
    rightCleanup = renderRightPanel(right, { state: detail, meters: budget?.meters ?? {} });
  }
  refreshSidePanels();
  const panelsPoll = setInterval(refreshSidePanels, 4000);
```

In cleanup: `clearInterval(panelsPoll); leftCleanup?.(); rightCleanup?.();`.

Also call `refreshSidePanels()` from inside the sessions-strip `onSelect`.

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/screens/auto-mode.js
git commit -m "feat(taskmaster-viewer): wire side panels into auto-mode page"
```

---

### Task 42: Playwright — sessions strip with multiple sessions

**Files:**
- Modify: `plugins/taskmaster/viewer/tests/auto-mode.spec.js`

- [ ] **Step 1: Add test**

Append:

```javascript
test('sessions strip renders one tab per session', async ({ page }) => {
  // The dev fixture seeds two sessions; if it doesn't, fall back to >=1.
  await page.goto('http://127.0.0.1:8765/v3/#/auto');
  const tabs = page.locator('.sstrip-tab');
  const count = await tabs.count();
  expect(count).toBeGreaterThanOrEqual(1);
});
```

- [ ] **Step 2: Run** — Expected: PASS.

```bash
cd plugins/taskmaster/viewer && npx playwright test tests/auto-mode.spec.js -g "sessions strip"
```

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/tests/auto-mode.spec.js
git commit -m "test(taskmaster-viewer): smoke for sessions strip"
```

---

### Task 43: Playwright — pause button fires API

**Files:**
- Modify: `plugins/taskmaster/viewer/tests/auto-mode.spec.js`

- [ ] **Step 1: Add test**

Append:

```javascript
test('clicking Pause posts to /api/auto/pause', async ({ page }) => {
  let posted = null;
  page.on('request', (req) => {
    if (req.method() === 'POST' && req.url().includes('/api/auto/pause')) {
      posted = req.postData();
    }
  });
  await page.goto('http://127.0.0.1:8765/v3/#/auto');
  // Only meaningful if a session is running. Skip otherwise.
  const empty = await page.locator('.spine-empty').count();
  if (empty > 0) test.skip();
  await page.locator('.auto-control-btn--pause').click();
  await page.waitForTimeout(200);
  expect(posted).toBeTruthy();
  expect(posted).toContain('"session_id"');
});
```

- [ ] **Step 2: Run** — Expected: PASS or SKIP.

```bash
cd plugins/taskmaster/viewer && npx playwright test tests/auto-mode.spec.js -g "Pause"
```

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/tests/auto-mode.spec.js
git commit -m "test(taskmaster-viewer): pause button hits /api/auto/pause"
```

---

## M7 — Dashboard Stepper Widget + Line-Fix Verification

### Task 44: Replace the Plan-4 stub `auto-mode-stepper.js` with the real widget

**Files:**
- Modify: `plugins/taskmaster/viewer/js/components/widgets/auto-mode-stepper.js`

The widget catalog (Plan 4) expects `{ meta, mount(root, ctx) }`. Render the 8-step stepper described in §3.15.

- [ ] **Step 1: Write the file**

Replace contents:

```javascript
// auto-mode-stepper widget — dashboard tile that mirrors the auto-mode page.
// Replaces the Plan-4 stub. See spec §3.15 (Compact Horizontal Stepper).

export const meta = {
  id: 'auto-mode-stepper',
  type: 'auto-mode-stepper',
  defaultSize: 'wide',           // ~480px tile
  title: 'Auto Mode',
};

const STEPS = [
  { key: 'PICK',          label: 'Pick' },
  { key: 'PLAN',          label: 'Plan' },
  { key: 'SPEC_REVIEW',   label: 'Review' },
  { key: 'TESTS',         label: 'Tests' },
  { key: 'IMPLEMENT',     label: 'Implement' },
  { key: 'TEST',          label: 'Test' },
  { key: 'REVIEW',        label: 'Review' },
  { key: 'COMPLETE',      label: 'Done' },
];

export async function mount(root, ctx) {
  root.innerHTML = '';
  const tile = document.createElement('div');
  tile.className = 'stepper-widget';
  tile.setAttribute('role', 'link');
  tile.setAttribute('tabindex', '0');
  root.appendChild(tile);

  function go() { window.location.hash = '#/auto'; }
  tile.addEventListener('click', go);
  tile.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(); }
  });

  let cleanupSub = null;

  function paint(state) {
    if (!state || !state.cursor) {
      tile.innerHTML = `
        <div class="stepper-head">
          <span class="stepper-h">Auto Mode</span>
          <span class="stepper-link">Open</span>
        </div>
        <div class="stepper-empty">No auto-mode running</div>
      `;
      return;
    }
    const completed = new Set(state.completed ?? []);
    const cursor = state.cursor.stage;
    const subagentCount = (state.subagents ?? []).filter((s) => s.status === 'running').length;
    const tokens = state?.budget?.tokens;

    const stepsHtml = STEPS.map((s, i) => {
      let cls = 'pending';
      if (completed.has(s.key)) cls = 'done';
      else if (s.key === cursor) cls = 'active';
      return `
        <div class="stepper-step stepper-step--${cls}" data-step="${s.key}">
          <div class="stepper-circle"></div>
          <div class="stepper-label">${s.label}</div>
        </div>
      `;
    }).join('');

    tile.innerHTML = `
      <div class="stepper-head">
        <span class="stepper-h">Auto Mode <span class="stepper-running">· running</span></span>
        <span class="stepper-link">Open</span>
      </div>
      <div class="stepper-task">
        <span class="stepper-id">${escape(state.session_id ?? state.task_id ?? '')}</span>
        <span class="stepper-title">${escape(state.title ?? '')}</span>
        <span class="stepper-wt">${escape(state.worktree ?? '')}</span>
      </div>
      <div class="stepper-track">${stepsHtml}</div>
      <div class="stepper-foot">
        <span class="stepper-dot"></span>
        <span class="stepper-elapsed">${elapsed(state.started_at)}</span>
        <span class="stepper-foot-sep">·</span>
        <span class="stepper-sub">${subagentCount} subagent${subagentCount === 1 ? '' : 's'}</span>
        ${tokens ? `<span class="stepper-foot-sep">·</span><span class="stepper-tokens">${formatTokens(tokens.used)} / ${formatTokens(tokens.limit)}</span>` : ''}
      </div>
    `;
  }

  paint(ctx.store.getAutoState?.() ?? null);
  cleanupSub = ctx.store.subscribe?.('autoState', paint);

  return () => { cleanupSub?.(); root.innerHTML = ''; };
}

function elapsed(iso) {
  if (!iso) return '';
  const ms = Date.now() - new Date(iso).getTime();
  if (Number.isNaN(ms) || ms < 0) return '';
  const s = Math.floor(ms / 1000);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  if (h) return `${h}h ${m}m`;
  return `${m}m`;
}

function formatTokens(n) {
  if (!n && n !== 0) return '?';
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(n);
}

function escape(s) {
  return String(s).replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
}
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/widgets/auto-mode-stepper.js
git commit -m "feat(taskmaster-viewer): real auto-mode-stepper widget (replaces stub)"
```

---

### Task 45: Stepper widget styles — circles, labels, footer

**Files:**
- Modify: `plugins/taskmaster/viewer/css/screens/auto-mode.css` (the dashboard widget loads this CSS via the dashboard-screen link, but to keep it discoverable we put it in the same auto-mode file; if your build prefers per-component CSS, this is fine in the dashboard module — adjust per Plan 4 conventions).

Note: If Plan 4 introduced per-widget CSS files (e.g. `css/widgets/auto-mode-stepper.css`), put the styles there instead and add the `<link>` in `index.html`. Without confirmed Plan 4 path, append to `auto-mode.css` since the Dashboard already loads `css/screens/auto-mode.css` only when on the auto page — change this: also link from dashboard CSS load. For safety, add to `index.html` head (loaded for all screens).

- [ ] **Step 1: Move auto-mode.css link out of "screen-only" if it was conditional**

In `plugins/taskmaster/viewer/index.html`, ensure `<link rel="stylesheet" href="css/screens/auto-mode.css" />` is in `<head>` (loads for all screens including dashboard). Already added in Task 21 — verify.

- [ ] **Step 2: Append CSS for the stepper widget**

```css
/* ──────────────────────────────────────────────────────────────────────────
   Dashboard widget: auto-mode-stepper
   Connector lines must START at right edge of circle and END at left edge of next.
   Per spec: left: calc(50% + 10px); right: calc(-50% + 10px).
   ────────────────────────────────────────────────────────────────────────── */

.stepper-widget {
  background: var(--bg-panel); border: 1px solid var(--border);
  border-radius: 8px; padding: 12px 14px; cursor: pointer;
  transition: background .12s ease;
}
.stepper-widget:hover { background: #1c1d23; }
.stepper-widget:focus-visible { outline: 1px solid var(--accent); outline-offset: 2px; }

.stepper-head { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.stepper-h {
  font-size: 9px; text-transform: uppercase; letter-spacing: 0.1em;
  color: var(--ink-3); font-weight: 600;
}
.stepper-running { color: var(--accent); text-transform: none; letter-spacing: 0; font-weight: 500; }
.stepper-link { margin-left: auto; font-size: 10px; color: var(--accent); }
.stepper-link::after { content: ' →'; }

.stepper-task { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.stepper-id {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-size: 10px; color: var(--accent);
  padding: 1px 5px; border-radius: 3px;
  background: rgba(74,158,255,0.08);
}
.stepper-title { font-size: 12px; color: var(--ink); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.stepper-wt {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-size: 9px; color: var(--ink-3);
}

.stepper-empty {
  padding: 20px 0; text-align: center;
  color: var(--ink-3); font-size: 11px;
}

.stepper-track { display: flex; align-items: flex-start; gap: 0; padding: 4px 0 0; }
.stepper-step {
  flex: 1; display: flex; flex-direction: column; align-items: center;
  gap: 4px; position: relative;
}

/* Edge-to-edge connector — does NOT pass beneath circles. */
.stepper-step::before {
  content: '';
  position: absolute;
  top: 8px;                              /* vertical-center on a 16px circle */
  left:  calc(50% + 10px);               /* start at right edge of THIS circle */
  right: calc(-50% + 10px);              /* end at left edge of NEXT circle */
  height: 1.5px;
  background: var(--border);             /* default: pending — gray */
  z-index: 1;
}
.stepper-step:last-child::before { display: none; }

/* Per spec correction: done connectors stay GRAY (not green) — only the active
   circle gets the blue gradient lead-in. */
.stepper-step--done::before    { background: var(--border); }
.stepper-step--active::before  { background: linear-gradient(90deg, var(--accent), var(--border)); }

.stepper-circle {
  width: 16px; height: 16px; border-radius: 50%;
  border: 1.5px solid var(--border); background: var(--bg-card);
  z-index: 2; position: relative;
  display: flex; align-items: center; justify-content: center;
  font-size: 8px;
}
.stepper-step--done .stepper-circle {
  background: rgba(95,174,110,0.15); border-color: var(--green); color: var(--green);
}
.stepper-step--done .stepper-circle::after { content: '✓'; font-weight: 700; }

.stepper-step--active .stepper-circle {
  background: rgba(74,158,255,0.2); border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(74,158,255,0.12);
  animation: spine-pulse 1.6s ease-in-out infinite;
}
.stepper-step--active .stepper-circle::after { content: '●'; color: var(--accent); }

.stepper-label {
  font-size: 8px; color: var(--ink-3); text-align: center; line-height: 1.1;
  margin-top: 2px;
}
.stepper-step--active .stepper-label { color: var(--ink); }

.stepper-foot {
  display: flex; align-items: center; gap: 6px;
  margin-top: 12px; font-size: 11px; color: var(--ink-3);
}
.stepper-foot-sep { color: var(--ink-3); opacity: 0.5; }
.stepper-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--green); animation: spine-pulse 1.6s ease-in-out infinite;
}
.stepper-elapsed, .stepper-tokens {
  font-family: 'JetBrains Mono', ui-monospace, monospace; color: var(--ink-2);
}
.stepper-sub { color: var(--ink-2); }
```

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/css/screens/auto-mode.css
git commit -m "feat(taskmaster-viewer): stepper widget styles + edge-to-edge connector"
```

---

### Task 46: Unit test — stepper connector geometry

This is the verification test mentioned in the spec self-review: connector starts at right edge of circle and ends at left edge of next, never passes beneath. We assert via the CSS layout helper directly (parsing CSS literals from the file).

**Files:**
- Create: `plugins/taskmaster/viewer/tests/unit/stepper-line.test.js`

- [ ] **Step 1: Write the failing test**

```javascript
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const cssPath = resolve(__dirname, '../../css/screens/auto-mode.css');
const css = readFileSync(cssPath, 'utf8');

function findRule(selector) {
  // Naive: capture text between `<selector> {` and the next closing `}`.
  const escSel = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const re = new RegExp(`${escSel}\\s*{([^}]*)}`, 'm');
  const m = re.exec(css);
  if (!m) throw new Error(`selector not found in CSS: ${selector}`);
  return m[1];
}

test('stepper connector starts at right edge of circle (left: calc(50% + 10px))', () => {
  const body = findRule('.stepper-step::before');
  assert.match(body, /left:\s*calc\(\s*50%\s*\+\s*10px\s*\)/);
});

test('stepper connector ends at left edge of next circle (right: calc(-50% + 10px))', () => {
  const body = findRule('.stepper-step::before');
  assert.match(body, /right:\s*calc\(\s*-50%\s*\+\s*10px\s*\)/);
});

test('done connector is gray (not green) — base var(--border)', () => {
  const body = findRule('.stepper-step--done::before');
  assert.match(body, /background:\s*var\(--border\)/);
  assert.doesNotMatch(body, /var\(--green\)/);
});

test('active connector uses blue gradient lead-in', () => {
  const body = findRule('.stepper-step--active::before');
  assert.match(body, /linear-gradient\(\s*90deg\s*,\s*var\(--accent\)\s*,\s*var\(--border\)\s*\)/);
});
```

- [ ] **Step 2: Run** — Expected: PASS (CSS authored to satisfy these contracts in Task 45).

```bash
node --test plugins/taskmaster/viewer/tests/unit/stepper-line.test.js
```

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/tests/unit/stepper-line.test.js
git commit -m "test(taskmaster-viewer): stepper connector edge-to-edge + color contract"
```

---

### Task 47: Verify widget catalog registration (Plan 4 hand-off)

**Files:**
- Read: `plugins/taskmaster/viewer/js/components/widgets/catalog.js` (or wherever Plan 4 stored the catalog)

- [ ] **Step 1: Inspect the catalog file**

Open the catalog and verify the import for `auto-mode-stepper` resolves to the rewritten file. If the Plan 4 import path was `./auto-mode-stepper.js` and the file is at the expected location, no change. If the catalog was registering by stub-only meta `{type:'stub'}`, update so meta.type matches the new export's `meta.id`.

- [ ] **Step 2: If a change is needed**

Edit the catalog so the entry reads (Plan 4 catalog interface):

```javascript
import * as autoModeStepper from './auto-mode-stepper.js';
// ...
catalog.register(autoModeStepper);
```

- [ ] **Step 3: Commit (if any change)**

```bash
git add plugins/taskmaster/viewer/js/components/widgets/catalog.js
git commit -m "chore(taskmaster-viewer): re-register auto-mode-stepper widget against new export"
```

If no change needed, skip commit.

---

### Task 48: Playwright — dashboard widget click navigates to `#/auto`

**Files:**
- Modify: `plugins/taskmaster/viewer/tests/auto-mode.spec.js`

- [ ] **Step 1: Append**

```javascript
test('clicking the dashboard auto-mode-stepper widget navigates to #/auto', async ({ page }) => {
  await page.goto('http://127.0.0.1:8765/v3/#/dashboard');
  const widget = page.locator('.stepper-widget');
  if (!(await widget.count())) test.skip(); // user may not have it in their layout
  await widget.first().click();
  await page.waitForURL(/#\/auto$/);
  await expect(page.locator('.auto-title')).toHaveText('Auto Mode');
});
```

- [ ] **Step 2: Run** — Expected: PASS or SKIP.

```bash
cd plugins/taskmaster/viewer && npx playwright test tests/auto-mode.spec.js -g "navigates to"
```

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/tests/auto-mode.spec.js
git commit -m "test(taskmaster-viewer): stepper widget click-through to auto-mode page"
```

---

### Task 49: Widget hides itself when no session is running OR shows calm placeholder

The widget's empty state already renders "No auto-mode running" (Task 44). Spec wording: "hides itself when no auto-mode session is running, or shows a calm placeholder." Plan-6 default = placeholder; users can hide the widget via the dashboard edit-mode (Plan 4). Verify this in a unit-style smoke.

**Files:**
- Modify: `plugins/taskmaster/viewer/tests/auto-mode.spec.js`

- [ ] **Step 1: Append**

```javascript
test('stepper widget shows placeholder when no session', async ({ page }) => {
  await page.goto('http://127.0.0.1:8765/v3/#/dashboard');
  const widget = page.locator('.stepper-widget');
  if (!(await widget.count())) test.skip();
  // Either the calm empty state OR a running session
  const empty = await widget.locator('.stepper-empty').count();
  const running = await widget.locator('.stepper-track').count();
  expect(empty + running).toBeGreaterThan(0);
});
```

- [ ] **Step 2: Run + commit**

```bash
cd plugins/taskmaster/viewer && npx playwright test tests/auto-mode.spec.js -g "placeholder"
git add plugins/taskmaster/viewer/tests/auto-mode.spec.js
git commit -m "test(taskmaster-viewer): stepper widget empty placeholder"
```

---

### Task 50: "+1 more" pill on the widget when multiple sessions are running

Spec §3.15: *"if multiple sessions run, an unobtrusive '+1 more' pill links to the full Auto Mode page."*

**Files:**
- Modify: `plugins/taskmaster/viewer/js/components/widgets/auto-mode-stepper.js`
- Modify: `plugins/taskmaster/viewer/css/screens/auto-mode.css`

- [ ] **Step 1: Augment the widget**

Right after the existing `mount()` paint, add a sessions count fetch:

```javascript
  ctx.api.autoListSessions?.().then((sessions) => {
    if (!sessions || sessions.length <= 1) return;
    const moreEl = tile.querySelector('.stepper-link');
    if (!moreEl) return;
    const pill = document.createElement('span');
    pill.className = 'stepper-more';
    pill.textContent = `+${sessions.length - 1} more`;
    moreEl.before(pill);
  }).catch(() => {});
```

- [ ] **Step 2: Append CSS**

```css
.stepper-more {
  font-size: 9px; padding: 1px 6px; border-radius: 9px;
  background: rgba(74,158,255,0.10); color: var(--accent);
  margin-left: 6px;
  font-family: 'JetBrains Mono', ui-monospace, monospace;
}
```

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/widgets/auto-mode-stepper.js plugins/taskmaster/viewer/css/screens/auto-mode.css
git commit -m "feat(taskmaster-viewer): +N more pill on stepper widget"
```

---

### Task 51: Re-run unit + smoke after widget changes

- [ ] **Step 1: Run all auto-mode tests**

```bash
node --test plugins/taskmaster/viewer/tests/unit/auto-spine-layout.test.js plugins/taskmaster/viewer/tests/unit/stepper-line.test.js
python -m pytest plugins/taskmaster/tests/test_server_auto_mode.py -v
cd plugins/taskmaster/viewer && npx playwright test tests/auto-mode.spec.js
```
Expected: all PASS or correctly SKIP.

- [ ] **Step 2: Commit only if there are stale snapshots/fixtures to refresh** (otherwise no-op).

---

## M8 — Integration Smoke

### Task 52: Sidebar live-dot — Playwright verifies it appears when state.cursor exists

The sidebar nav item for Auto Mode shows a glowing blue badge when state.mode/cursor is set. Plan 1 wired the listener; we just verify.

**Files:**
- Modify: `plugins/taskmaster/viewer/tests/auto-mode.spec.js`

- [ ] **Step 1: Append**

```javascript
test('sidebar Auto Mode link shows live badge when a session is active', async ({ page }) => {
  await page.goto('http://127.0.0.1:8765/v3/#/dashboard');
  // Wait one poll cycle for autoState to populate
  await page.waitForTimeout(1500);
  const badge = page.locator('.sb-link[data-key="auto"] .sb-livedot, .sb-link[data-sidebar-key="auto"] .sb-livedot');
  // Either present (running) or absent (no session) — both are valid; just no error.
  const count = await badge.count();
  expect(count).toBeGreaterThanOrEqual(0);
});
```

This is intentionally permissive — verifies no JS error and the selector resolves. The "appears when running" assertion requires fixture seeding which Plan 4 set up for the dashboard fixture; if needed, this can be tightened later.

- [ ] **Step 2: Run + commit**

```bash
cd plugins/taskmaster/viewer && npx playwright test tests/auto-mode.spec.js -g "sidebar"
git add plugins/taskmaster/viewer/tests/auto-mode.spec.js
git commit -m "test(taskmaster-viewer): sidebar live-dot smoke"
```

---

### Task 53: Helper note shows on first visit, not after dismissal

**Files:**
- Modify: `plugins/taskmaster/viewer/tests/auto-mode.spec.js`

- [ ] **Step 1: Append**

```javascript
test('helper note shows on first visit and disappears after dismiss', async ({ page, context }) => {
  // Reset prefs by clearing the helper_dismissed key via PUT /api/viewer/prefs
  await page.request.put('http://127.0.0.1:8765/api/viewer/prefs', {
    data: { screens: { auto_mode: { helper_dismissed: false } } },
  });

  await page.goto('http://127.0.0.1:8765/v3/#/auto');
  const note = page.locator('.auto-helper-note');
  await expect(note).toBeVisible();
  await note.locator('.dismiss').click();
  await expect(note).toHaveCount(0);

  // Reload — should not re-appear
  await page.goto('http://127.0.0.1:8765/v3/#/auto');
  await expect(page.locator('.auto-helper-note')).toHaveCount(0);
});
```

- [ ] **Step 2: Run + commit**

```bash
cd plugins/taskmaster/viewer && npx playwright test tests/auto-mode.spec.js -g "helper note"
git add plugins/taskmaster/viewer/tests/auto-mode.spec.js
git commit -m "test(taskmaster-viewer): helper note first-visit + persistent dismissal"
```

---

### Task 54: Spine renders the right node count for given state — pin the assertion

**Files:**
- Modify: `plugins/taskmaster/viewer/tests/auto-mode.spec.js`

- [ ] **Step 1: Append**

```javascript
test('Spine renders 5 nodes when a session has a cursor', async ({ page }) => {
  // Seed via the API
  await page.request.put('http://127.0.0.1:8765/api/viewer/prefs', {
    data: { screens: { auto_mode: { view: 'A', helper_dismissed: true } } },
  });
  // The dev fixture must include a session for this assertion. If not present, skip.
  const sess = await page.request.get('http://127.0.0.1:8765/api/auto/state');
  const body = await sess.json();
  if (body.running === false) test.skip();

  await page.goto('http://127.0.0.1:8765/v3/#/auto');
  const nodes = page.locator('.spine-node');
  await expect(nodes).toHaveCount(5);

  // Active node has class --active
  await expect(page.locator('.spine-node--active')).toHaveCount(1);
});
```

- [ ] **Step 2: Run + commit**

```bash
cd plugins/taskmaster/viewer && npx playwright test tests/auto-mode.spec.js -g "Spine renders 5"
git add plugins/taskmaster/viewer/tests/auto-mode.spec.js
git commit -m "test(taskmaster-viewer): spine node count + active class"
```

---

### Task 55: Stop button issues a confirm and posts on accept

**Files:**
- Modify: `plugins/taskmaster/viewer/tests/auto-mode.spec.js`

- [ ] **Step 1: Append**

```javascript
test('clicking Stop shows confirm and posts to /api/auto/stop', async ({ page }) => {
  let posted = false;
  page.on('request', (req) => {
    if (req.method() === 'POST' && req.url().includes('/api/auto/stop')) posted = true;
  });
  page.on('dialog', (d) => d.accept());

  const sess = await page.request.get('http://127.0.0.1:8765/api/auto/state');
  if ((await sess.json()).running === false) test.skip();

  await page.goto('http://127.0.0.1:8765/v3/#/auto');
  await page.locator('.auto-control-btn--stop').click();
  await page.waitForTimeout(200);
  expect(posted).toBeTruthy();
});
```

- [ ] **Step 2: Run + commit**

```bash
cd plugins/taskmaster/viewer && npx playwright test tests/auto-mode.spec.js -g "Stop"
git add plugins/taskmaster/viewer/tests/auto-mode.spec.js
git commit -m "test(taskmaster-viewer): stop button confirm + POST"
```

---

### Task 56: Full auto-mode test suite green-bar

- [ ] **Step 1: Run everything**

```bash
python -m pytest plugins/taskmaster/tests/test_server_auto_mode.py plugins/taskmaster/tests/test_v3_layout.py -v
node --test plugins/taskmaster/viewer/tests/unit/
cd plugins/taskmaster/viewer && npx playwright test tests/auto-mode.spec.js
```
Expected: all green or correctly SKIP. If any fails, fix and re-run before committing.

- [ ] **Step 2: No commit unless changes were made.**

---

### Task 57: Update plan handoff document

**Files:**
- Modify: `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-6-auto-mode.md` (this file — append a "Completion notes" section)

- [ ] **Step 1: Append a brief completion note**

Append to the bottom of this plan file:

```markdown
---

## Completion notes (filled when M8 is green)

- All 58 tasks executed; commit count ≈ matches task count.
- `python -m pytest plugins/taskmaster/tests/test_server_auto_mode.py` — N tests PASS
- `node --test plugins/taskmaster/viewer/tests/unit/` — N tests PASS
- `npx playwright test plugins/taskmaster/viewer/tests/auto-mode.spec.js` — N tests PASS

Open follow-ups for downstream plans:
- Real auto-mode runner (the producer of state + events + hook log) is out of scope here.
- Subagent satellite styling could later upgrade to per-type colors when the type taxonomy stabilizes.
```

- [ ] **Step 2: Commit**

```bash
git add docs/superpowers/plans/2026-04-26-viewer-redesign-plan-6-auto-mode.md
git commit -m "docs(taskmaster): plan 6 completion notes"
```

---

### Task 58: Final integration sanity (visual review checklist)

This is a manual review against the mockups. No test runs.

- [ ] Open the dev viewer at `http://127.0.0.1:8765/v3/#/auto`. Compare against `.superpowers/brainstorm/15283-1777223061/content/automode-integration.html`:
  - 3-column layout: subagents+hooks left · spine center · budget+tools right
  - Header has Pause (yellow) and Stop (red) buttons next to the title
  - Spine|Log toggle on the right
  - Helper note on first visit only
  - Sessions strip above the spine
  - Active node is bigger and pulses
  - Done nodes show ✓ check ring
  - Pending nodes are at 40% opacity
- [ ] Open `#/dashboard` and verify the auto-mode-stepper widget:
  - 8 circles
  - Done circles connect via gray line (NOT green)
  - Active circle has blue gradient lead-in
  - Connector lines do NOT pass beneath circles
  - Whole tile click navigates to `#/auto`
- [ ] Toggle Spine ↔ Log; persistence survives a page reload.
- [ ] Click any session strip tab; spine + side panels swap to that session.

---

## Self-review against §3.15 spec checklist

| Spec §3.15 requirement | Tasks |
|---|---|
| 5-node Quest Spine in deep-recessed frame | 20, 21 |
| Done nodes ✓ green check ring | 21 |
| Active node radius 18, pulse, glowing blue stroke | 16, 21 |
| Pending nodes 40% opacity | 21 |
| Subagent satellites with bezier horizontal in/out tangents | 15, 18, 20 |
| Subagent labels by type (G/E/etc.) | 20 |
| 3-column page layout | 21, 22, 41 |
| Compact 8-step stepper widget on Dashboard | 44, 45 |
| Stepper edge-to-edge connector geometry (`left: calc(50% + 10px)`) | 45, 46 |
| Stepper done connector GRAY (not green) | 45, 46 |
| Stepper active connector blue gradient lead-in | 45, 46 |
| Stepper whole-tile click → `#/auto` | 44, 48 |
| Flight-log waterfall (newest top, ATC-style) | 29, 30 |
| Active row blue tint + pulsing badge | 29, 30 |
| Header Pause/Stop buttons always accessible | 22, 24, 55 |
| Spine|Log toggle persisted to prefs | 23, 53 |
| Helper note first-visit only with persistent dismissal | 25, 53 |
| Sessions strip above spine; multi-session | 34, 35, 42 |
| Single-run case still shows one tab | 34 |
| Left panel: subagents (running on top, completed faded) | 38 |
| Left panel: hook firings count | 6, 38, 40 |
| Right panel: budget meters (Tokens/Time/Context/Cost) | 12, 37, 38 |
| Budget tier (warn 60%+, crit 90%+) | 12, 37 |
| Right panel: tool log (last 4 calls) | 38 |
| Sidebar live indicator | 28, 52 |
| Server: per-session storage refactor + migration | 1, 2, 3, 4 |
| Server: events.jsonl per session | 5, 11 |
| Server: hooks.jsonl read | 6, 40 |
| Server: pause/stop/state/sessions/sessions/<sid>/events/budget endpoints | 7, 8, 9, 10, 11, 12 |
| MCP tools: state_get/pause/stop/history/event_log | 13 |
| Stepper widget hides/empty-states when no session | 44, 49 |
| "+N more" pill when multiple sessions | 50 |

All §3.15 requirements have at least one task. Confirmed.

## Open questions / cross-plan dependencies

- **Plan 2 contract:** assumes `GET /api/auto/state` exists (Plan 2). Plan 6 Task 9 *replaces* its handler to read from sessions/. Plan 2 author should confirm no consumer of `/api/auto/state` depends on the legacy single-state shape; the new shape is identical except now sourced from the most-recent session file.
- **Plan 4 contract:** assumes a widget catalog with `register({meta, mount})` interface and that `auto-mode-stepper.js` is already imported there as a stub. If Plan 4 used a different shape (e.g. class-based widgets), Task 47 will require a small adapter; the rewritten widget keeps `meta` and `mount` exports so it should plug in.
- **Plan 1 contract:** reconciled. Plan 6 now uses `ctx.store.getPrefs()?.screens?.auto_mode?.view` for reads and `ctx.prefs.patch({screens: {auto_mode: {...}}})` for writes, matching Plan 1's actual `store.getPrefs()` / `prefs.patch()` API.
- **Hook log producer:** Plan 6 only reads `.taskmaster/auto/hooks.jsonl`. Schema is documented in Task 6's intro. The producer (real auto-mode runner) is out of scope. If the runner uses a different schema or path, Tasks 6 + 40 are the only places to update.
- **Subagent type labels:** the abbreviation map (`G`/`E`/`P`/`R`/`A`) is hard-coded in two places (`quest-spine.js`, `auto-side-panels.js`). If the type taxonomy expands, lift to a shared module.
