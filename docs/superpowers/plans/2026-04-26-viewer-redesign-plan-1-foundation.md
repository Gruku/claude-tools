# Taskmaster Viewer Redesign — Plan 1: Foundation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish the modular viewer skeleton, design-token system, sidebar + hash routing, viewer-prefs storage, and server JSON API that all other plans build on.

**Architecture:** Full rebuild of `plugins/taskmaster/backlog-viewer.html` into a modular `plugins/taskmaster/viewer/` directory tree (HTML shell + CSS modules + JS modules). Server-side, extend `backlog_server.py` with a JSON API for viewer-prefs and entity mutations. Original viewer stays in place as `backlog-viewer.html` until the new one reaches parity; the new viewer is served at `/v3` (and at `/` once a `viewer.use_v3` flag flips).

**Tech Stack:** Vanilla HTML/CSS/JS (no framework — keep parity with existing viewer's zero-build approach), Python 3 + `fastmcp` + `BaseHTTPRequestHandler` (existing server), pytest, Playwright for UI smoke tests.

**Spec reference:** `docs/superpowers/specs/2026-04-26-taskmaster-viewer-redesign.md` §3.10–§3.11 (sidebar, v3 grounding) and §5 (impl notes / prefs persistence).

---

## File Structure

**New files (created in this plan):**

```
plugins/taskmaster/viewer/
├── index.html                          # Shell: sidebar + main + screen mount points
├── css/
│   ├── tokens.css                      # All design tokens (colors, spacing, type, motion)
│   ├── shell.css                       # Shell grid, sidebar, topbar, page frame
│   ├── components.css                  # Shared chips, pills, buttons, kbd
│   └── screens/
│       ├── _placeholders.css           # Stub styling for unimplemented screens
│       └── (per-screen .css added in Plans 2–6)
├── js/
│   ├── main.js                         # Entry: boot, mount, kick off router
│   ├── router.js                       # Hash routing + screen registry
│   ├── api.js                          # HTTP client for /api/* endpoints
│   ├── store.js                        # In-memory state (backlog, prefs, polls)
│   ├── prefs.js                        # ViewerPrefs read/write helpers
│   ├── components/
│   │   └── sidebar.js                  # Sidebar render + active-state sync
│   └── screens/
│       ├── dashboard.js                # Stub (Plan 4 fills in)
│       ├── kanban.js                   # Stub (Plan 2 fills in)
│       ├── task-detail.js              # Stub (Plan 3 fills in)
│       ├── sessions.js                 # Stub (Plan 5 fills in)
│       ├── lessons.js                  # Stub (Plan 5 fills in)
│       ├── issues.js                   # Stub (Plan 5 fills in)
│       ├── auto-mode.js                # Stub (Plan 6 fills in)
│       └── recap.js                    # Stub (Plan 5 fills in)
└── tests/
    └── smoke.spec.js                   # Playwright smoke tests
```

**Files modified (in this plan):**
- `plugins/taskmaster/backlog_server.py` — add `/v3` route, `/api/viewer/prefs` GET/PUT, `/static/v3/*` serve
- `plugins/taskmaster/taskmaster_v3.py` — add `ViewerPrefs` entity (load/save helpers, defaults)
- `plugins/taskmaster/tests/test_v3_layout.py` — add ViewerPrefs round-trip tests
- `plugins/taskmaster/tests/test_server_api.py` — **new** test file for HTTP endpoint behavior

**Files left untouched (in this plan):** the existing `plugins/taskmaster/backlog-viewer.html` continues to serve at `/` until later plans reach parity.

---

## Architectural Conventions (locked for Plans 2–6)

All later plans MUST follow these conventions. They're stated here once.

### Module style
- Every JS file is an **ES module** (`<script type="module">` in `index.html`). No bundler. Browsers resolve relative imports natively.
- One default export per file unless otherwise stated. Named exports for utilities.

### Screen module shape
Every screen module exports the same two functions:

```js
// js/screens/<name>.js
export async function mount(root, { params, store, api, prefs }) {
  // Render initial DOM into `root` element. Return a cleanup function.
}
export const meta = { title: 'Kanban', icon: '▦', sidebarKey: 'kanban' };
```

The router calls `mount()` when the hash changes to that screen, awaits the cleanup function (if returned), and calls it on next navigation.

### CSS naming
- Component classes use the prefix that matches the file: `.shell-*`, `.sidebar-*`, `.chip-*`, `.kanban-*`, etc. No global `.card` — always `.<screen>-card` or `.cmp-card` if shared.
- Design tokens live exclusively in `tokens.css` as CSS custom properties (`--ink`, `--bg-card`, etc.). Plans 2–6 do **not** add new tokens to `tokens.css` without explicit need; they can add tokens to their own screen CSS file under `--<screen>-*` namespace.

### State + API
- All state goes through `store.js`. Screens read via `store.getBacklog()`, `store.getPrefs()`, etc., never `fetch` directly.
- All mutations go through `api.js` (`api.savePrefs(patch)`, `api.reinforceLesson(id)`, etc.). `api.js` returns Promises; on success it triggers a store re-poll.
- `store.js` exposes `subscribe(key, cb)` for screens to listen to specific slice changes.

### Routing
- Hashes: `#/dashboard`, `#/kanban`, `#/kanban?epic=foo&phase=2`, `#/task/T-148`, `#/sessions`, `#/sessions/SES-0184`, `#/lessons`, `#/issues`, `#/auto`, `#/recap/SES-0184`
- The router parses `path` and `params` (search-style) and passes both to `mount()`.
- An unknown hash falls back to `#/dashboard`.

### Persistence
- All viewer prefs persist to `.taskmaster/viewer.json` (atomic write, schema-versioned).
- All other entity mutations route through existing v3 entity files (lessons, recaps, etc. — added in later plans).

### Tests
- Server-side: pytest with `tmp_path` fixture (no `~/.taskmaster` pollution).
- UI: Playwright smoke tests assert the screen mounts and key DOM nodes exist. **No visual-regression tests in this plan** — fidelity is human-reviewed against mockups.

---

## Milestones

- **M1 — Server foundation** (Tasks 1–6): ViewerPrefs entity + load/save + tool + HTTP endpoint
- **M2 — Static skeleton** (Tasks 7–12): viewer/ dir, tokens.css, shell.css, index.html, /v3 route, /static/v3 serving
- **M3 — Routing + sidebar** (Tasks 13–17): router.js, sidebar.js, screen registry, hash navigation
- **M4 — Stub screens** (Tasks 18–22): one stub per screen so all routes resolve cleanly
- **M5 — Polling + smoke tests** (Tasks 23–27): backlog polling, prefs sync, Playwright smoke
- **M6 — Cleanup + commit** (Task 28): final integration test, plan handoff

---

## M1 — Server Foundation

### Task 1: Define ViewerPrefs schema constants and defaults

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py:60-110` (constants block, near the existing `LESSON_KINDS` etc.)
- Modify: `plugins/taskmaster/tests/test_v3_layout.py` (add test)

- [x] **Step 1: Write the failing test**

Append to `plugins/taskmaster/tests/test_v3_layout.py`:

```python
def test_viewer_prefs_defaults_have_all_expected_keys():
    from taskmaster_v3 import VIEWER_PREFS_DEFAULTS
    expected_top_keys = {
        "schema_version",
        "theme",
        "card_density",
        "zoom",
        "screens",
        "dashboard",
        "kanban",
        "lessons",
        "issues",
    }
    assert set(VIEWER_PREFS_DEFAULTS.keys()) == expected_top_keys
    assert VIEWER_PREFS_DEFAULTS["schema_version"] == 1
    assert VIEWER_PREFS_DEFAULTS["theme"] == "dark"
    assert VIEWER_PREFS_DEFAULTS["card_density"] == "full"
    assert VIEWER_PREFS_DEFAULTS["zoom"] == 1.5
    # screens.<name>.view holds A/B toggle per screen
    assert "task_detail" in VIEWER_PREFS_DEFAULTS["screens"]
    assert VIEWER_PREFS_DEFAULTS["screens"]["task_detail"]["view"] == "A"
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_layout.py::test_viewer_prefs_defaults_have_all_expected_keys -v`
Expected: FAIL with `ImportError: cannot import name 'VIEWER_PREFS_DEFAULTS'`

- [x] **Step 3: Add the defaults constant**

Insert after the `AUTO_TASK_STATUSES` constant in `plugins/taskmaster/taskmaster_v3.py`:

```python
# ---- ViewerPrefs ---------------------------------------------------------

VIEWER_PREFS_SCHEMA_VERSION = 1

VIEWER_PREFS_DEFAULTS = {
    "schema_version": VIEWER_PREFS_SCHEMA_VERSION,
    "theme": "dark",          # dark | light
    "card_density": "full",   # full | minimal
    "zoom": 1.5,              # baked-in 150% per spec §3.4
    "screens": {
        # Per-screen view toggles (Variant A / B). Default A everywhere except dashboard which has no B.
        "task_detail": {"view": "A"},
        "kanban":      {"view": "A"},
        "sessions":    {"view": "A"},   # diary | lanes | by_task; "A" maps to diary
        "lessons":     {"view": "A"},   # shelves | flat | by_anchor
        "issues":      {"view": "A"},   # hybrid | kanban | list
        "auto_mode":   {"view": "A"},   # spine | log
    },
    "dashboard": {
        # Widget catalog. Each entry: {id, type, size: small|medium|wide, rail: left|right|bottom, index: int}
        "layout": [],
    },
    "kanban": {
        "filters": {           # last applied; restored on viewer open
            "priorities": [],
            "epics": [],
            "phase": None,
            "group_by": "status",
            "sort": {"by": "priority", "dir": "desc"},
            "search": "",
        },
    },
    "lessons": {
        "thresholds": {
            "core_count": 7,
            "core_window_days": 60,
            "core_recency_days": 14,
            "retired_after_days": 30,
        },
    },
    "issues": {
        "aging": {             # base period in days, severity-tiered
            "Critical": 14,
            "High": 30,
            "Medium": 60,
            "Low": 120,
        },
    },
}
```

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_layout.py::test_viewer_prefs_defaults_have_all_expected_keys -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_v3_layout.py
git commit -m "feat(taskmaster): add ViewerPrefs defaults + schema version"
```

---

### Task 2: Implement load_viewer_prefs() and save_viewer_prefs()

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py` (add helpers near other load/save funcs)
- Modify: `plugins/taskmaster/tests/test_v3_layout.py` (round-trip test)

- [x] **Step 1: Write the failing test**

Append to `plugins/taskmaster/tests/test_v3_layout.py`:

```python
def test_viewer_prefs_round_trip(tmp_path, monkeypatch):
    from taskmaster_v3 import (
        load_viewer_prefs, save_viewer_prefs, VIEWER_PREFS_DEFAULTS,
    )
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".taskmaster").mkdir()

    # Empty first read returns defaults (and creates the file)
    p1 = load_viewer_prefs()
    assert p1 == VIEWER_PREFS_DEFAULTS
    assert (tmp_path / ".taskmaster" / "viewer.json").exists()

    # Mutate, save, re-read
    p1["theme"] = "light"
    p1["kanban"]["filters"]["search"] = "auth"
    save_viewer_prefs(p1)

    p2 = load_viewer_prefs()
    assert p2["theme"] == "light"
    assert p2["kanban"]["filters"]["search"] == "auth"

def test_viewer_prefs_unknown_keys_preserved_on_save(tmp_path, monkeypatch):
    """Forward-compat: don't strip keys we don't know about."""
    import json
    from taskmaster_v3 import load_viewer_prefs, save_viewer_prefs
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".taskmaster").mkdir()
    (tmp_path / ".taskmaster" / "viewer.json").write_text(
        json.dumps({"schema_version": 1, "future_field": "preserve_me", "theme": "dark"})
    )
    prefs = load_viewer_prefs()
    save_viewer_prefs(prefs)
    saved = json.loads((tmp_path / ".taskmaster" / "viewer.json").read_text())
    assert saved["future_field"] == "preserve_me"
```

- [x] **Step 2: Run tests to verify they fail**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_layout.py::test_viewer_prefs_round_trip -v plugins/taskmaster/tests/test_v3_layout.py::test_viewer_prefs_unknown_keys_preserved_on_save -v`
Expected: FAIL with `ImportError`

- [x] **Step 3: Implement load + save**

Add to `plugins/taskmaster/taskmaster_v3.py` (alongside other load/save helpers):

```python
def viewer_prefs_path() -> Path:
    return Path(".taskmaster") / "viewer.json"

def load_viewer_prefs() -> dict:
    """Load viewer prefs, creating the file with defaults on first call.
    Unknown top-level keys are preserved across reads (forward-compat).
    Missing keys are filled from VIEWER_PREFS_DEFAULTS (deep-merged).
    """
    import json
    from copy import deepcopy
    p = viewer_prefs_path()
    if not p.exists():
        prefs = deepcopy(VIEWER_PREFS_DEFAULTS)
        atomic_write(p, json.dumps(prefs, indent=2))
        return prefs
    raw = json.loads(p.read_text())

    # Deep-merge defaults under the loaded data so missing nested keys appear.
    def _merge(default, loaded):
        if isinstance(default, dict) and isinstance(loaded, dict):
            out = dict(loaded)  # preserve unknown keys
            for k, v in default.items():
                if k not in out:
                    out[k] = deepcopy(v)
                else:
                    out[k] = _merge(v, out[k])
            return out
        return loaded

    return _merge(VIEWER_PREFS_DEFAULTS, raw)

def save_viewer_prefs(prefs: dict) -> None:
    import json
    p = viewer_prefs_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(p, json.dumps(prefs, indent=2))
```

- [x] **Step 4: Run tests to verify they pass**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_layout.py -v -k viewer_prefs`
Expected: 3 tests PASS

- [x] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_v3_layout.py
git commit -m "feat(taskmaster): viewer prefs load/save with deep-merge defaults"
```

---

### Task 3: Add `viewer_prefs_get` and `viewer_prefs_set` MCP tools

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py` (add tools near other entity tools)
- Modify: `plugins/taskmaster/tests/test_v3_layout.py`

- [x] **Step 1: Write the failing test**

Append to `plugins/taskmaster/tests/test_v3_layout.py`:

```python
def test_viewer_prefs_set_merges_patch(tmp_path, monkeypatch):
    """viewer_prefs_set accepts a partial patch; unspecified keys retain prior values."""
    import json
    from taskmaster_v3 import save_viewer_prefs, load_viewer_prefs, VIEWER_PREFS_DEFAULTS
    from copy import deepcopy
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".taskmaster").mkdir()
    save_viewer_prefs(deepcopy(VIEWER_PREFS_DEFAULTS))

    # The MCP tool import path:
    import importlib, sys
    sys.path.insert(0, str(tmp_path.parent))  # not relevant; we import directly
    from backlog_server import viewer_prefs_set  # type: ignore

    msg = viewer_prefs_set('{"theme": "light", "kanban": {"filters": {"search": "auth"}}}')
    assert "ok" in msg.lower()

    prefs = load_viewer_prefs()
    assert prefs["theme"] == "light"
    assert prefs["kanban"]["filters"]["search"] == "auth"
    # unspecified key retains default
    assert prefs["card_density"] == "full"
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_layout.py::test_viewer_prefs_set_merges_patch -v`
Expected: FAIL — `ImportError: cannot import name 'viewer_prefs_set'`

- [x] **Step 3: Implement the MCP tools**

Insert in `plugins/taskmaster/backlog_server.py` near the other v3 entity tools (e.g., after `backlog_issue_list`):

```python
@mcp.tool()
def viewer_prefs_get() -> str:
    """Return current viewer prefs as JSON."""
    import json
    prefs = load_viewer_prefs()
    return json.dumps(prefs, indent=2)

@mcp.tool()
def viewer_prefs_set(patch_json: str) -> str:
    """Deep-merge a JSON patch into the persisted viewer prefs.
    Patch is a JSON object; only the keys present are updated.
    """
    import json
    from copy import deepcopy
    try:
        patch = json.loads(patch_json)
    except Exception as e:
        return f"error: invalid JSON ({e})"
    if not isinstance(patch, dict):
        return "error: patch must be a JSON object"

    def _deep_merge(base, patch):
        for k, v in patch.items():
            if isinstance(v, dict) and isinstance(base.get(k), dict):
                _deep_merge(base[k], v)
            else:
                base[k] = deepcopy(v)
        return base

    prefs = load_viewer_prefs()
    _deep_merge(prefs, patch)
    save_viewer_prefs(prefs)
    return "ok"
```

If `load_viewer_prefs` / `save_viewer_prefs` aren't already re-exported at the top of `backlog_server.py`, add them to the existing taskmaster_v3 re-export block.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest plugins/taskmaster/tests/test_v3_layout.py::test_viewer_prefs_set_merges_patch -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_v3_layout.py
git commit -m "feat(taskmaster): viewer_prefs_get/set MCP tools"
```

---

### Task 4: Add HTTP endpoint `GET /api/viewer/prefs`

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py` (HTTP request handler)
- Create: `plugins/taskmaster/tests/test_server_api.py`

- [x] **Step 1: Write the failing test**

Create `plugins/taskmaster/tests/test_server_api.py`:

```python
"""HTTP API tests. Spin up the server in-process on an ephemeral port."""
import json
import threading
import time
import urllib.request
import pytest


@pytest.fixture
def running_server(tmp_path, monkeypatch):
    """Start backlog_server on a free port, yielding (base_url, server)."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".taskmaster").mkdir()
    # Minimal backlog.yaml so the server doesn't 404
    (tmp_path / "backlog.yaml").write_text(
        "meta:\n  project: test\nepics: []\nphases: []\n"
    )

    from backlog_server import _make_server  # added in this task
    server, port = _make_server(host="127.0.0.1", port=0)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    base = f"http://127.0.0.1:{port}"
    # Wait briefly for thread to be ready
    for _ in range(20):
        try:
            urllib.request.urlopen(f"{base}/api/identity", timeout=0.5).read()
            break
        except Exception:
            time.sleep(0.05)

    yield base, server

    server.shutdown()
    server.server_close()


def test_get_viewer_prefs_returns_defaults_on_first_call(running_server):
    base, _ = running_server
    resp = urllib.request.urlopen(f"{base}/api/viewer/prefs")
    assert resp.status == 200
    body = json.loads(resp.read())
    assert body["theme"] == "dark"
    assert body["card_density"] == "full"
    assert body["zoom"] == 1.5
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest plugins/taskmaster/tests/test_server_api.py::test_get_viewer_prefs_returns_defaults_on_first_call -v`
Expected: FAIL with `ImportError: cannot import name '_make_server'` OR 404 on `/api/viewer/prefs`

- [x] **Step 3: Refactor `backlog_server.py` to expose `_make_server` and handle the route**

In `plugins/taskmaster/backlog_server.py`, locate the existing `serve()`/`run()` entry point. Extract server construction into:

```python
def _make_server(host: str = "127.0.0.1", port: int = 0):
    """Build the HTTP server without starting it. Returns (server, bound_port)."""
    server = ThreadingHTTPServer((host, port), _Handler)
    return server, server.server_address[1]
```

In the `_Handler.do_GET` method, add the route handler **before** the existing `/api/backlog` handler:

```python
if self.path == "/api/viewer/prefs":
    import json
    body = json.dumps(load_viewer_prefs()).encode("utf-8")
    self.send_response(200)
    self.send_header("Content-Type", "application/json")
    self.send_header("Content-Length", str(len(body)))
    self.send_header("Access-Control-Allow-Origin", "*")
    self.end_headers()
    self.wfile.write(body)
    return
```

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest plugins/taskmaster/tests/test_server_api.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_server_api.py
git commit -m "feat(taskmaster): GET /api/viewer/prefs endpoint"
```

---

### Task 5: Add HTTP endpoint `PUT /api/viewer/prefs`

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py`
- Modify: `plugins/taskmaster/tests/test_server_api.py`

- [ ] **Step 1: Write the failing test**

Append to `plugins/taskmaster/tests/test_server_api.py`:

```python
def test_put_viewer_prefs_merges_patch(running_server):
    base, _ = running_server
    body = json.dumps({"theme": "light", "kanban": {"filters": {"search": "auth"}}}).encode()
    req = urllib.request.Request(
        f"{base}/api/viewer/prefs",
        data=body,
        method="PUT",
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req)
    assert resp.status == 200
    assert json.loads(resp.read())["ok"] is True

    # GET reflects the patch
    after = json.loads(urllib.request.urlopen(f"{base}/api/viewer/prefs").read())
    assert after["theme"] == "light"
    assert after["kanban"]["filters"]["search"] == "auth"
    assert after["card_density"] == "full"  # untouched

def test_put_viewer_prefs_rejects_non_object(running_server):
    base, _ = running_server
    req = urllib.request.Request(
        f"{base}/api/viewer/prefs",
        data=b'"not an object"',
        method="PUT",
        headers={"Content-Type": "application/json"},
    )
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(req)
    assert exc.value.code == 400
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest plugins/taskmaster/tests/test_server_api.py -v -k put_viewer_prefs`
Expected: FAIL (404/405 on PUT)

- [ ] **Step 3: Implement do_PUT in the handler**

Add to `_Handler` class in `backlog_server.py`:

```python
def do_PUT(self):
    if self.path == "/api/viewer/prefs":
        import json
        from copy import deepcopy
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode("utf-8") if length else ""
        try:
            patch = json.loads(raw)
        except Exception as e:
            self._send_json(400, {"ok": False, "error": f"invalid JSON: {e}"})
            return
        if not isinstance(patch, dict):
            self._send_json(400, {"ok": False, "error": "patch must be a JSON object"})
            return

        def _deep_merge(base, patch):
            for k, v in patch.items():
                if isinstance(v, dict) and isinstance(base.get(k), dict):
                    _deep_merge(base[k], v)
                else:
                    base[k] = deepcopy(v)
            return base

        prefs = load_viewer_prefs()
        _deep_merge(prefs, patch)
        save_viewer_prefs(prefs)
        self._send_json(200, {"ok": True})
        return

    self.send_response(404)
    self.end_headers()

def _send_json(self, status: int, payload: dict):
    import json
    body = json.dumps(payload).encode("utf-8")
    self.send_response(status)
    self.send_header("Content-Type", "application/json")
    self.send_header("Content-Length", str(len(body)))
    self.send_header("Access-Control-Allow-Origin", "*")
    self.end_headers()
    self.wfile.write(body)

def do_OPTIONS(self):
    """Allow PUT cross-origin."""
    self.send_response(204)
    self.send_header("Access-Control-Allow-Origin", "*")
    self.send_header("Access-Control-Allow-Methods", "GET, PUT, POST, OPTIONS")
    self.send_header("Access-Control-Allow-Headers", "Content-Type")
    self.end_headers()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest plugins/taskmaster/tests/test_server_api.py -v`
Expected: All PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_server_api.py
git commit -m "feat(taskmaster): PUT /api/viewer/prefs endpoint"
```

---

### Task 6: Wire `_send_json` helper into existing `/api/*` handlers

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py`

(Refactor pass — the existing `/api/backlog`, `/api/identity`, `/api/session` handlers each open-code response sending. Replace with `self._send_json(...)` for consistency.)

- [x] **Step 1: Write the failing test (regression guard)**

Append to `plugins/taskmaster/tests/test_server_api.py`:

```python
def test_api_endpoints_set_cors_header(running_server):
    base, _ = running_server
    for path in ["/api/identity", "/api/viewer/prefs"]:
        resp = urllib.request.urlopen(f"{base}{path}")
        assert resp.headers.get("Access-Control-Allow-Origin") == "*"
```

- [x] **Step 2: Run the test**

Run: `python -m pytest plugins/taskmaster/tests/test_server_api.py::test_api_endpoints_set_cors_header -v`
Expected: PASS or FAIL depending on existing `/api/identity` impl. If FAIL, proceed; if PASS, the existing handler already sets the header — still go through Step 3 to deduplicate.

- [x] **Step 3: Refactor the existing handlers**

Replace each `/api/identity`, `/api/backlog`, `/api/session` block in `_Handler.do_GET` with calls to `self._send_json(200, payload_dict)`. Drop the open-coded `send_response` / `send_header` triplets. Behavior should be identical; only the implementation tightens.

- [x] **Step 4: Run all server tests**

Run: `python -m pytest plugins/taskmaster/tests/test_server_api.py -v`
Expected: All PASS (4 tests)

- [x] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_server_api.py
git commit -m "refactor(taskmaster): unify JSON response sending in HTTP handler"
```

---

## M2 — Static Skeleton

### Task 7: Scaffold the viewer/ directory and tokens.css

**Files:**
- Create: `plugins/taskmaster/viewer/css/tokens.css`

- [x] **Step 1: Create the directory tree**

```bash
mkdir -p plugins/taskmaster/viewer/css/screens plugins/taskmaster/viewer/js/components plugins/taskmaster/viewer/js/screens plugins/taskmaster/viewer/tests
```

- [x] **Step 2: Write `tokens.css`**

Create `plugins/taskmaster/viewer/css/tokens.css` with the design tokens collected from the mockups (and inlined in the spec at §3.4 / §3.7). Exact contents:

```css
/* Design tokens — single source of truth.
   Subsequent CSS files reference these via var(--name).
   No new global tokens are added in screen-specific CSS files. */
:root {
  /* Surfaces (dark theme — only theme implemented at this stage) */
  --bg-canvas:        #14151a;
  --bg-shell:         #0f1014;
  --bg-panel:         #17181d;
  --bg-card:          #1f2025;
  --bg-board-col:     #0f131c;
  --bg-deep:          #0a0c11;          /* console / input recess */
  --bg-issue:         #181a20;          /* slightly cooler than bg-card, per spec §3.14 */

  /* Borders */
  --border:           #2c2d33;
  --border-soft:      rgba(255,255,255,0.05);
  --border-strong:    #3a3b42;

  /* Ink */
  --ink:              #e6e7eb;
  --ink-2:            #bfc4cc;
  --ink-3:            #7c8290;
  --ink-on-accent:    #0a1628;

  /* Accents */
  --accent:           #4a9eff;
  --accent-2:         #7fb3f0;
  --accent-soft:      rgba(74,158,255,0.10);

  /* Status */
  --green:            #5fae6e;
  --amber:            #d6a45f;
  --red:              #d66b5f;
  --purple:           #a07fe0;
  --gold:             #d6a45f;

  /* Diff colors (Recap, Sessions detail) */
  --diff-add:         #5fae6e;
  --diff-mod:         #d6a45f;
  --diff-del:         #d66b5f;

  /* Epic palette — auto-assigned in order; see spec §5 */
  --epic-1:           #6ea8ff;
  --epic-2:           #b585e8;
  --epic-3:           #5fcdb8;
  --epic-4:           #e8a34d;
  --epic-5:           #e87a85;
  --epic-6:           #a8c958;

  /* Type */
  --font-sans:        'Inter', -apple-system, system-ui, sans-serif;
  --font-mono:        'JetBrains Mono', ui-monospace, Menlo, monospace;
  --font-serif:       'Source Serif Pro', Georgia, serif;

  --text-xs:          10px;
  --text-sm:          11px;
  --text-base:        12px;
  --text-md:          13px;
  --text-lg:          14px;
  --text-xl:          16px;
  --text-2xl:         20px;
  --text-3xl:         22px;

  /* Spacing */
  --sp-1:             4px;
  --sp-2:             6px;
  --sp-3:             8px;
  --sp-4:             10px;
  --sp-5:             12px;
  --sp-6:             14px;
  --sp-7:             16px;
  --sp-8:             18px;
  --sp-9:             22px;

  /* Radius */
  --r-sm:             4px;
  --r-md:             6px;
  --r-lg:             8px;
  --r-xl:             10px;
  --r-2xl:            12px;

  /* Shadows + recess (graph frame language, Task Detail B / Auto Mode B) */
  --shadow-card:      0 1px 0 rgba(255,255,255,0.02) inset, 0 4px 12px rgba(0,0,0,0.18);
  --shadow-lifted:    0 4px 14px rgba(0,0,0,0.4);
  --recess-inset:     inset 0 0 36px rgba(0,0,0,0.4);
  --recess-bg:        radial-gradient(ellipse at 50% 50%, #181a22 0%, #0d0e13 100%);

  /* Motion */
  --t-fast:           120ms;
  --t-base:           180ms;
  --t-slow:           320ms;
  --ease:             cubic-bezier(0.3, 0.7, 0.4, 1);

  /* Layout */
  --shell-zoom:       1.5;             /* spec §3.4 — 150% baked in */
  --sidebar-w:        200px;
  --rail-w:           480px;            /* right-rail detail surface */
}
```

- [x] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/css/tokens.css
git commit -m "feat(viewer): scaffold viewer/ tree + tokens.css"
```

---

### Task 8: Write shell.css

**Files:**
- Create: `plugins/taskmaster/viewer/css/shell.css`

- [x] **Step 1: Write `shell.css`**

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&family=Source+Serif+Pro:ital,wght@1,400&display=swap');

html, body {
  margin: 0;
  padding: 0;
  height: 100%;
  font-family: var(--font-sans);
  background: var(--bg-canvas);
  color: var(--ink);
  font-size: var(--text-base);
  line-height: 1.5;
}

body {
  zoom: var(--shell-zoom);
}

.mono { font-family: var(--font-mono); }
.serif { font-family: var(--font-serif); font-style: italic; }

/* Shell grid: sidebar + main */
.shell {
  display: grid;
  grid-template-columns: var(--sidebar-w) 1fr;
  background: var(--bg-shell);
  min-height: 100vh;
  color: var(--ink);
}

/* Sidebar */
.sidebar {
  background: #101116;
  border-right: 1px solid var(--border);
  padding: var(--sp-6) 0;
  display: flex;
  flex-direction: column;
}
.sidebar-logo {
  padding: 0 var(--sp-6) var(--sp-6);
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  border-bottom: 1px solid var(--border-soft);
}
.sidebar-logo .mark {
  width: 18px; height: 18px; border-radius: var(--r-sm);
  background: linear-gradient(135deg, var(--accent), var(--accent-2));
}
.sidebar-logo .name { font-weight: 600; font-size: var(--text-md); }
.sidebar-logo .ver { color: var(--ink-3); font-size: var(--text-xs); margin-left: auto; font-family: var(--font-mono); }

.sidebar-section-h {
  padding: var(--sp-4) var(--sp-6) var(--sp-2);
  font-size: 9px; text-transform: uppercase; letter-spacing: 0.1em;
  color: var(--ink-3);
}
.sidebar-link {
  padding: var(--sp-2) var(--sp-6);
  display: flex; align-items: center; gap: var(--sp-3);
  color: var(--ink-2);
  cursor: pointer;
  text-decoration: none;
  font-size: var(--text-base);
}
.sidebar-link:hover { background: rgba(255,255,255,0.03); }
.sidebar-link.active {
  background: var(--accent-soft);
  color: var(--ink);
  /* inset shadow on left, NOT a left ribbon — distinct per spec §3.7 / §3.11 */
  box-shadow: inset 2px 0 0 var(--accent);
}
.sidebar-link .ic { width: 14px; height: 14px; opacity: 0.65; }
.sidebar-link .badge {
  margin-left: auto;
  font-size: var(--text-xs);
  color: var(--ink-3);
  font-family: var(--font-mono);
}
.sidebar-link.live .badge::before {
  content: '●';
  color: var(--accent);
  margin-right: 4px;
  animation: pulse 1.4s ease-in-out infinite;
}

.sidebar-footer {
  margin-top: auto;
  padding: var(--sp-4) var(--sp-6);
  border-top: 1px solid var(--border-soft);
  font-size: var(--text-xs);
  color: var(--ink-3);
  display: flex; align-items: center; gap: var(--sp-2);
}
.sidebar-footer .pulse {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--green);
  display: none;
  animation: pulse 1.4s ease-in-out infinite;
}
.sidebar-footer.auto-running .pulse { display: inline-block; }

/* Main */
.main {
  display: flex; flex-direction: column;
  min-height: 100vh;
  padding: var(--sp-8) var(--sp-9);
  overflow-x: auto;
}

.topbar {
  display: flex; align-items: center; gap: var(--sp-5);
  margin-bottom: var(--sp-8);
}
.topbar h2 {
  font-size: var(--text-2xl);
  margin: 0;
  font-weight: 600;
}

.screen-mount {
  flex: 1;
  min-height: 0;
}

@keyframes pulse {
  0%, 100% { opacity: 0.4; }
  50%      { opacity: 1; }
}

/* Stub screen — see _placeholders.css */
```

- [x] **Step 2: Write `_placeholders.css`**

Create `plugins/taskmaster/viewer/css/screens/_placeholders.css`:

```css
.stub {
  background: var(--bg-card);
  border: 1px dashed var(--border);
  border-radius: var(--r-2xl);
  padding: 40px;
  color: var(--ink-2);
  text-align: center;
  font-family: var(--font-serif);
  font-size: var(--text-lg);
}
.stub .stub-meta {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-3);
  margin-top: var(--sp-4);
  font-style: normal;
}
```

- [x] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/css/shell.css plugins/taskmaster/viewer/css/screens/_placeholders.css
git commit -m "feat(viewer): shell.css + placeholder screen styling"
```

---

### Task 9: Write components.css (shared chips, pills, buttons)

**Files:**
- Create: `plugins/taskmaster/viewer/css/components.css`

- [x] **Step 1: Write the file**

```css
/* Shared inline components used across screens.
   Pattern: .cmp-<name> for shared elements; screen-specific variants live in screens/<screen>.css. */

/* Chips — id, epic, priority, severity */
.cmp-chip {
  display: inline-flex; align-items: center; gap: var(--sp-1);
  padding: 2px var(--sp-2);
  border-radius: var(--r-sm);
  font-size: var(--text-xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-family: var(--font-sans);
}
.cmp-chip.id      { font-family: var(--font-mono); text-transform: none; letter-spacing: 0; color: var(--ink); background: rgba(255,255,255,0.04); }
.cmp-chip.high    { background: rgba(214,107,95,0.15); color: var(--red); }
.cmp-chip.med     { background: rgba(214,164,95,0.15); color: var(--amber); }
.cmp-chip.low     { background: rgba(124,130,144,0.15); color: var(--ink-3); }
.cmp-chip.crit    { background: rgba(214,107,95,0.22); color: var(--red); }

/* Pills — kind/status pills with leading dot */
.cmp-pill {
  display: inline-flex; align-items: center; gap: var(--sp-2);
  padding: 3px var(--sp-3);
  border-radius: 999px;
  font-size: var(--text-xs);
  background: rgba(255,255,255,0.03);
  border: 1px solid var(--border);
  color: var(--ink-2);
}
.cmp-pill .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--ink-3); }
.cmp-pill.live .dot { background: var(--accent); animation: pulse 1.4s ease-in-out infinite; }

/* Buttons */
.cmp-btn {
  appearance: none;
  padding: var(--sp-2) var(--sp-4);
  background: transparent;
  border: 1px solid var(--border);
  color: var(--ink-2);
  border-radius: var(--r-md);
  cursor: pointer;
  font-size: var(--text-sm);
  font-family: var(--font-sans);
  display: inline-flex; align-items: center; gap: var(--sp-2);
  transition: color var(--t-fast) var(--ease), border-color var(--t-fast) var(--ease);
}
.cmp-btn:hover { color: var(--ink); border-color: var(--border-strong); }
.cmp-btn.primary { background: var(--accent-soft); border-color: rgba(74,158,255,0.35); color: var(--accent); }
.cmp-btn.icon { width: 28px; height: 28px; padding: 0; justify-content: center; }

/* Kbd */
.cmp-kbd {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  padding: 1px var(--sp-2);
  background: rgba(255,255,255,0.06);
  border: 1px solid var(--border);
  border-radius: var(--r-sm);
  color: var(--ink-2);
}
```

- [x] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/css/components.css
git commit -m "feat(viewer): shared components.css (chips, pills, buttons, kbd)"
```

---

### Task 10: Write index.html shell

**Files:**
- Create: `plugins/taskmaster/viewer/index.html`

- [x] **Step 1: Write the shell**

```html
<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Taskmaster</title>
  <link rel="stylesheet" href="css/tokens.css">
  <link rel="stylesheet" href="css/shell.css">
  <link rel="stylesheet" href="css/components.css">
  <link rel="stylesheet" href="css/screens/_placeholders.css">
</head>
<body>
  <div class="shell">
    <aside class="sidebar" id="sidebar"></aside>
    <main class="main">
      <header class="topbar" id="topbar">
        <h2 id="page-title">Loading…</h2>
      </header>
      <section class="screen-mount" id="screen-mount"></section>
    </main>
  </div>
  <script type="module" src="js/main.js"></script>
</body>
</html>
```

- [x] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/index.html
git commit -m "feat(viewer): index.html shell"
```

---

### Task 11: Serve the new viewer at `/v3` and static assets at `/static/v3/*`

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py`
- Modify: `plugins/taskmaster/tests/test_server_api.py`

- [x] **Step 1: Write the failing test**

Append to `plugins/taskmaster/tests/test_server_api.py`:

```python
def test_get_v3_returns_index_html(running_server):
    base, _ = running_server
    resp = urllib.request.urlopen(f"{base}/v3")
    assert resp.status == 200
    assert resp.headers.get("Content-Type", "").startswith("text/html")
    body = resp.read().decode()
    assert "<title>Taskmaster</title>" in body
    assert 'src="js/main.js"' in body or "main.js" in body  # main JS referenced

def test_get_static_v3_tokens_css(running_server):
    base, _ = running_server
    resp = urllib.request.urlopen(f"{base}/static/v3/css/tokens.css")
    assert resp.status == 200
    assert resp.headers.get("Content-Type", "").startswith("text/css")
    assert "--bg-canvas" in resp.read().decode()

def test_static_v3_path_traversal_blocked(running_server):
    base, _ = running_server
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(f"{base}/static/v3/../../etc/passwd")
    assert exc.value.code in (400, 404)
```

- [x] **Step 2: Run tests**

Run: `python -m pytest plugins/taskmaster/tests/test_server_api.py -v -k v3`
Expected: FAIL (404)

- [x] **Step 3: Implement the routes**

Add at the start of `_Handler.do_GET` (before the existing `/api/*` block, but after `/api/viewer/prefs`):

```python
# /v3 → viewer/index.html, but rewrite asset hrefs to absolute /static/v3/* paths.
if self.path in ("/v3", "/v3/", "/v3/index.html"):
    viewer_root = Path(__file__).parent / "viewer"
    idx = viewer_root / "index.html"
    if not idx.exists():
        self.send_response(404); self.end_headers(); return
    html = idx.read_text(encoding="utf-8")
    # Make relative asset refs absolute under /static/v3/.
    html = html.replace('href="css/', 'href="/static/v3/css/')
    html = html.replace('src="js/', 'src="/static/v3/js/')
    body = html.encode("utf-8")
    self.send_response(200)
    self.send_header("Content-Type", "text/html; charset=utf-8")
    self.send_header("Content-Length", str(len(body)))
    self.send_header("Access-Control-Allow-Origin", "*")
    self.end_headers()
    self.wfile.write(body)
    return

# /static/v3/* → file under viewer/
if self.path.startswith("/static/v3/"):
    rel = self.path[len("/static/v3/"):]
    viewer_root = (Path(__file__).parent / "viewer").resolve()
    target = (viewer_root / rel).resolve()
    if not str(target).startswith(str(viewer_root) + os.sep) and target != viewer_root:
        self.send_response(400); self.end_headers(); return
    if not target.is_file():
        self.send_response(404); self.end_headers(); return
    ext = target.suffix.lower()
    ctype = {
        ".html": "text/html; charset=utf-8",
        ".css":  "text/css; charset=utf-8",
        ".js":   "application/javascript; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".svg":  "image/svg+xml",
    }.get(ext, "application/octet-stream")
    body = target.read_bytes()
    self.send_response(200)
    self.send_header("Content-Type", ctype)
    self.send_header("Content-Length", str(len(body)))
    self.send_header("Access-Control-Allow-Origin", "*")
    self.end_headers()
    self.wfile.write(body)
    return
```

Make sure `import os` and `from pathlib import Path` are present at the top of `backlog_server.py`.

- [x] **Step 4: Run tests**

Run: `python -m pytest plugins/taskmaster/tests/test_server_api.py -v -k v3`
Expected: All PASS (3 tests)

- [x] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_server_api.py
git commit -m "feat(taskmaster): /v3 + /static/v3/* routes"
```

---

### Task 12: Manual smoke — open `/v3` in a browser

- [x] **Step 1: Start the server**

Run from `plugins/taskmaster/`:

```bash
python -c "from backlog_server import _make_server; s, p = _make_server(host='127.0.0.1', port=0); print(f'http://127.0.0.1:{p}/v3'); s.serve_forever()"
```

- [x] **Step 2: Open the printed URL**

Expected: dark canvas, an empty sidebar (no entries yet — populated next milestone), an empty main area with "Loading…" page title. No console errors except possibly 404s for the not-yet-written `js/main.js`.

This step is informational; nothing to commit. If the page doesn't load, debug before proceeding.

---

## M3 — Routing + Sidebar

### Task 13: Implement `js/api.js`

**Files:**
- Create: `plugins/taskmaster/viewer/js/api.js`

- [x] **Step 1: Write the file**

```js
// Thin HTTP client for /api/* endpoints. All viewer mutations go through here.

const BASE = ''; // same-origin

async function http(method, path, body) {
  const init = { method, headers: {} };
  if (body !== undefined) {
    init.headers['Content-Type'] = 'application/json';
    init.body = JSON.stringify(body);
  }
  const resp = await fetch(BASE + path, init);
  if (!resp.ok) {
    const text = await resp.text().catch(() => '');
    throw new Error(`${method} ${path} → ${resp.status}: ${text}`);
  }
  const ctype = resp.headers.get('Content-Type') || '';
  if (ctype.includes('application/json')) return resp.json();
  if (ctype.includes('text/yaml') || path.endsWith('.yaml')) return resp.text();
  return resp.text();
}

export const api = {
  identity:        ()    => http('GET', '/api/identity'),
  backlog:         ()    => http('GET', '/api/backlog'),
  backlogYaml:     ()    => http('GET', '/backlog.yaml'),
  prefs:           ()    => http('GET', '/api/viewer/prefs'),
  savePrefs:       (p)   => http('PUT', '/api/viewer/prefs', p),
  // Plans 5/6 add: reinforceLesson, getRecap, putRecap, getAutoState, etc.
};
```

- [x] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/api.js
git commit -m "feat(viewer): api.js HTTP client"
```

---

### Task 14: Implement `js/store.js` (in-memory state + subscriptions)

**Files:**
- Create: `plugins/taskmaster/viewer/js/store.js`

- [x] **Step 1: Write the file**

```js
// In-memory store. Screens read via getters and subscribe to keys.
// Polling is initiated by main.js, not here.

const state = {
  backlog: null,    // parsed backlog YAML object
  prefs: null,      // viewer prefs
  identity: null,   // {root, version}
  autoState: null,  // populated by Plan 6
};

const subscribers = new Map(); // key → Set<callback>

function emit(key) {
  const subs = subscribers.get(key);
  if (!subs) return;
  for (const cb of subs) {
    try { cb(state[key]); } catch (e) { console.error('store sub error', key, e); }
  }
}

export const store = {
  getBacklog:  () => state.backlog,
  getPrefs:    () => state.prefs,
  getIdentity: () => state.identity,
  getAutoState:() => state.autoState,

  setBacklog:  (b) => { state.backlog = b;  emit('backlog'); },
  setPrefs:    (p) => { state.prefs = p;    emit('prefs'); },
  setIdentity: (i) => { state.identity = i; emit('identity'); },
  setAutoState:(a) => { state.autoState = a; emit('autoState'); },

  subscribe(key, cb) {
    if (!subscribers.has(key)) subscribers.set(key, new Set());
    subscribers.get(key).add(cb);
    return () => subscribers.get(key).delete(cb);
  },
};
```

- [x] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/store.js
git commit -m "feat(viewer): store.js (in-memory state + subscriptions)"
```

---

### Task 15: Implement `js/router.js`

**Files:**
- Create: `plugins/taskmaster/viewer/js/router.js`

- [x] **Step 1: Write the file**

```js
// Hash-based router. Hashes look like:
//   #/dashboard
//   #/kanban?epic=auth&phase=2
//   #/task/T-148
//   #/recap/SES-0184

const screens = new Map();   // path-prefix → loader (() => Promise<module>)
let currentCleanup = null;
let mountEl = null;
let topbarEl = null;
let injectDeps = null;       // { store, api, prefs }

export function registerScreen(prefix, loader) {
  screens.set(prefix, loader);
}

export function init({ mount, topbar, deps }) {
  mountEl = mount;
  topbarEl = topbar;
  injectDeps = deps;
  window.addEventListener('hashchange', go);
  if (!location.hash || location.hash === '#') location.hash = '#/dashboard';
  else go();
}

function parseHash() {
  const raw = (location.hash || '').replace(/^#\/?/, '');
  if (!raw) return { path: '', params: {}, segments: [] };
  const [pathPart, query] = raw.split('?', 2);
  const segments = pathPart.split('/').filter(Boolean);
  const path = '/' + segments.join('/');
  const params = {};
  if (query) {
    for (const pair of query.split('&')) {
      const [k, v=''] = pair.split('=');
      params[decodeURIComponent(k)] = decodeURIComponent(v);
    }
  }
  return { path, params, segments };
}

async function go() {
  const { path, params, segments } = parseHash();
  // Find the longest matching prefix.
  let match = null, matchPrefix = '';
  for (const prefix of screens.keys()) {
    if (path === prefix || path.startsWith(prefix + '/')) {
      if (prefix.length > matchPrefix.length) { matchPrefix = prefix; match = screens.get(prefix); }
    }
  }
  if (!match) {
    location.hash = '#/dashboard';
    return;
  }

  if (typeof currentCleanup === 'function') {
    try { await currentCleanup(); } catch (e) { console.error('cleanup error', e); }
    currentCleanup = null;
  }
  mountEl.replaceChildren();

  const mod = await match();
  topbarEl.querySelector('#page-title').textContent = mod.meta?.title || matchPrefix;
  // Pass remaining path segments after the prefix as `subpath` (e.g. /task/T-148 → ['T-148']).
  const subSegments = segments.slice(matchPrefix.split('/').filter(Boolean).length);
  const cleanup = await mod.mount(mountEl, {
    params,
    subpath: subSegments,
    ...injectDeps,
  });
  currentCleanup = cleanup;

  // Notify sidebar to update active state.
  document.dispatchEvent(new CustomEvent('route:changed', { detail: { path, params, sidebarKey: mod.meta?.sidebarKey } }));
}

export function navigate(hash) {
  if (!hash.startsWith('#')) hash = '#' + hash;
  if (location.hash === hash) go();
  else location.hash = hash;
}
```

- [x] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/router.js
git commit -m "feat(viewer): router.js (hash routing + screen registry)"
```

---

### Task 16: Implement `js/components/sidebar.js`

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/sidebar.js`

- [x] **Step 1: Write the file**

```js
// Sidebar renderer. Sections + entries are static here; live counts come from the store.

const SECTIONS = [
  { label: 'Frontdoor', items: [
    { key: 'dashboard', icon: '▤', label: 'Dashboard', hash: '#/dashboard' },
    { key: 'kanban',    icon: '▦', label: 'Kanban',    hash: '#/kanban' },
  ]},
  { label: 'Structural', items: [
    { key: 'auto_mode', icon: '⌬', label: 'Auto Mode', hash: '#/auto', live: true },
  ]},
  { label: 'Temporal', items: [
    { key: 'recap',    icon: '↻', label: 'Recap',    hash: '#/recap' },
    { key: 'sessions', icon: '⌕', label: 'Sessions', hash: '#/sessions' },
  ]},
  { label: 'Knowledge', items: [
    { key: 'lessons', icon: '✦', label: 'Lessons', hash: '#/lessons' },
    { key: 'issues',  icon: '⚠', label: 'Issues',  hash: '#/issues' },
  ]},
];

export function mountSidebar(el, { store }) {
  el.innerHTML = '';

  // Logo
  const logo = document.createElement('div');
  logo.className = 'sidebar-logo';
  logo.innerHTML = `
    <div class="mark"></div>
    <div class="name">Taskmaster</div>
    <div class="ver" id="sidebar-version">v?</div>
  `;
  el.appendChild(logo);

  // Sections
  for (const sect of SECTIONS) {
    const h = document.createElement('div');
    h.className = 'sidebar-section-h';
    h.textContent = sect.label;
    el.appendChild(h);

    for (const item of sect.items) {
      const a = document.createElement('a');
      a.className = 'sidebar-link' + (item.live ? ' live' : '');
      a.dataset.key = item.key;
      a.href = item.hash;
      a.innerHTML = `<span class="ic">${item.icon}</span><span>${item.label}</span><span class="badge"></span>`;
      el.appendChild(a);
    }
  }

  // Footer
  const footer = document.createElement('div');
  footer.className = 'sidebar-footer';
  footer.innerHTML = `<span class="pulse"></span><span>idle</span>`;
  el.appendChild(footer);

  // Active sync
  document.addEventListener('route:changed', (e) => {
    const key = e.detail.sidebarKey;
    el.querySelectorAll('.sidebar-link').forEach(a => {
      a.classList.toggle('active', a.dataset.key === key);
    });
  });

  // Identity → version
  store.subscribe('identity', (id) => {
    if (id?.version) el.querySelector('#sidebar-version').textContent = 'v' + id.version;
  });

  // Auto-mode live state → footer pulse + sidebar live-dot on auto_mode link
  store.subscribe('autoState', (auto) => {
    const running = !!(auto && auto.mode);
    footer.classList.toggle('auto-running', running);
    footer.querySelector('span:last-child').textContent = running ? 'auto-mode active' : 'idle';
    const link = el.querySelector('.sidebar-link[data-key="auto_mode"]');
    if (link) link.classList.toggle('live', running);
  });
}
```

- [x] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/sidebar.js
git commit -m "feat(viewer): sidebar component with route + identity sync"
```

---

### Task 17: Implement `js/main.js` (entry, boot, polling)

**Files:**
- Create: `plugins/taskmaster/viewer/js/main.js`

- [x] **Step 1: Write the file**

```js
import { api } from './api.js';
import { store } from './store.js';
import { init as routerInit, registerScreen } from './router.js';
import { mountSidebar } from './components/sidebar.js';

const BACKLOG_POLL_MS = 3000;
const PREFS_DEBOUNCE_MS = 400;

// Register screens (lazy-loaded modules).
registerScreen('/dashboard',  () => import('./screens/dashboard.js'));
registerScreen('/kanban',     () => import('./screens/kanban.js'));
registerScreen('/task',       () => import('./screens/task-detail.js'));
registerScreen('/sessions',   () => import('./screens/sessions.js'));
registerScreen('/lessons',    () => import('./screens/lessons.js'));
registerScreen('/issues',     () => import('./screens/issues.js'));
registerScreen('/auto',       () => import('./screens/auto-mode.js'));
registerScreen('/recap',      () => import('./screens/recap.js'));

// Prefs writer with debounce — screens call `prefs.patch({...})`.
let prefsDebounce = null;
const prefs = {
  patch(patchObj) {
    // Apply locally for instant UI feedback.
    const cur = store.getPrefs() || {};
    const merged = deepMerge(structuredClone(cur), patchObj);
    store.setPrefs(merged);
    // Persist with debounce.
    if (prefsDebounce) clearTimeout(prefsDebounce);
    prefsDebounce = setTimeout(() => {
      api.savePrefs(patchObj).catch(e => console.error('savePrefs failed', e));
    }, PREFS_DEBOUNCE_MS);
  },
};

function deepMerge(base, patch) {
  for (const [k, v] of Object.entries(patch)) {
    if (v && typeof v === 'object' && !Array.isArray(v) && base[k] && typeof base[k] === 'object') {
      deepMerge(base[k], v);
    } else {
      base[k] = v;
    }
  }
  return base;
}

async function boot() {
  // Initial fetches in parallel
  const [identity, prefsData] = await Promise.all([
    api.identity().catch(e => { console.error('identity fetch failed', e); return null; }),
    api.prefs().catch(e => { console.error('prefs fetch failed', e); return null; }),
  ]);
  store.setIdentity(identity);
  store.setPrefs(prefsData);

  // Mount sidebar
  mountSidebar(document.getElementById('sidebar'), { store });

  // Init router
  routerInit({
    mount: document.getElementById('screen-mount'),
    topbar: document.getElementById('topbar'),
    deps: { store, api, prefs },
  });

  // Backlog polling loop
  pollBacklogForever();
}

async function pollBacklogForever() {
  while (true) {
    try {
      const yaml = await api.backlogYaml();
      // Server already returns YAML text; parse client-side via a worker-free approach.
      // Use jsyaml from CDN (matches existing viewer).
      if (!window.jsyaml) await loadJsYaml();
      store.setBacklog(window.jsyaml.load(yaml));
    } catch (e) {
      console.error('backlog poll failed', e);
    }
    await sleep(BACKLOG_POLL_MS);
  }
}

function loadJsYaml() {
  return new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = 'https://cdn.jsdelivr.net/npm/js-yaml@4/dist/js-yaml.min.js';
    s.onload = resolve;
    s.onerror = reject;
    document.head.appendChild(s);
  });
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

boot();
```

- [x] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/main.js
git commit -m "feat(viewer): main.js boot + screen registry + backlog polling"
```

---

## M4 — Stub Screens

### Task 18: Stub `screens/dashboard.js`

**Files:**
- Create: `plugins/taskmaster/viewer/js/screens/dashboard.js`

- [x] **Step 1: Write the stub**

```js
export const meta = { title: 'Dashboard', icon: '▤', sidebarKey: 'dashboard' };

export async function mount(root, { store }) {
  const el = document.createElement('div');
  el.className = 'stub';
  el.innerHTML = `
    Dashboard placeholder.
    <div class="stub-meta">Plan 4 will fill in the bento layout, briefing strip, and customizable widgets.</div>
  `;
  root.appendChild(el);
  return () => {};
}
```

- [x] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/screens/dashboard.js
git commit -m "feat(viewer): dashboard stub screen"
```

---

### Task 19: Stub `screens/kanban.js`, `screens/task-detail.js`, `screens/sessions.js`

**Files:**
- Create: `plugins/taskmaster/viewer/js/screens/kanban.js`
- Create: `plugins/taskmaster/viewer/js/screens/task-detail.js`
- Create: `plugins/taskmaster/viewer/js/screens/sessions.js`

- [x] **Step 1: Write `kanban.js`**

```js
export const meta = { title: 'Kanban', icon: '▦', sidebarKey: 'kanban' };

export async function mount(root) {
  const el = document.createElement('div');
  el.className = 'stub';
  el.innerHTML = `
    Kanban placeholder.
    <div class="stub-meta">Plan 2 fills in phase stepper, epic chips, group-by toggle, cards (Minimal/Full), auto-mode strip.</div>
  `;
  root.appendChild(el);
  return () => {};
}
```

- [x] **Step 2: Write `task-detail.js`**

```js
export const meta = { title: 'Task Detail', icon: '▣', sidebarKey: null };

export async function mount(root, { subpath }) {
  const taskId = subpath[0] || '(no task)';
  const el = document.createElement('div');
  el.className = 'stub';
  el.innerHTML = `
    Task Detail placeholder.
    <div class="stub-meta">id=${escapeHtml(taskId)} — Plan 3 fills in Variant A (document) and Variant B (graph).</div>
  `;
  root.appendChild(el);
  return () => {};
}

function escapeHtml(s) { return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
```

- [x] **Step 3: Write `sessions.js`**

```js
export const meta = { title: 'Sessions / Handovers', icon: '⌕', sidebarKey: 'sessions' };

export async function mount(root, { subpath }) {
  const el = document.createElement('div');
  el.className = 'stub';
  el.innerHTML = `
    Sessions placeholder.
    <div class="stub-meta">${subpath[0] ? 'session=' + subpath[0] + ' — ' : ''}Plan 5 fills in the Hybrid C diary with parallel-block clusters, nested handovers/recaps, right-rail detail.</div>
  `;
  root.appendChild(el);
  return () => {};
}
```

- [x] **Step 4: Commit**

```bash
git add plugins/taskmaster/viewer/js/screens/kanban.js plugins/taskmaster/viewer/js/screens/task-detail.js plugins/taskmaster/viewer/js/screens/sessions.js
git commit -m "feat(viewer): kanban/task-detail/sessions stub screens"
```

---

### Task 20: Stub `screens/lessons.js`, `screens/issues.js`, `screens/auto-mode.js`, `screens/recap.js`

**Files:**
- Create: `plugins/taskmaster/viewer/js/screens/lessons.js`
- Create: `plugins/taskmaster/viewer/js/screens/issues.js`
- Create: `plugins/taskmaster/viewer/js/screens/auto-mode.js`
- Create: `plugins/taskmaster/viewer/js/screens/recap.js`

- [x] **Step 1: Write `lessons.js`**

```js
export const meta = { title: 'Lessons', icon: '✦', sidebarKey: 'lessons' };
export async function mount(root) {
  const el = document.createElement('div');
  el.className = 'stub';
  el.innerHTML = `Lessons placeholder.<div class="stub-meta">Plan 5 fills in Core/Active/Retired shelves, active+passive signals, Reinforce button.</div>`;
  root.appendChild(el);
  return () => {};
}
```

- [x] **Step 2: Write `issues.js`**

```js
export const meta = { title: 'Issues', icon: '⚠', sidebarKey: 'issues' };
export async function mount(root) {
  const el = document.createElement('div');
  el.className = 'stub';
  el.innerHTML = `Issues placeholder.<div class="stub-meta">Plan 5 fills in hybrid layout, severity glyph, console-style location, italic-serif symptom, repro block, aging bar.</div>`;
  root.appendChild(el);
  return () => {};
}
```

- [x] **Step 3: Write `auto-mode.js`**

```js
export const meta = { title: 'Auto Mode', icon: '⌬', sidebarKey: 'auto_mode' };
export async function mount(root) {
  const el = document.createElement('div');
  el.className = 'stub';
  el.innerHTML = `Auto Mode placeholder.<div class="stub-meta">Plan 6 fills in Quest Spine SVG, sessions strip, side panels, Spine|Log toggle.</div>`;
  root.appendChild(el);
  return () => {};
}
```

- [x] **Step 4: Write `recap.js`**

```js
export const meta = { title: 'Recap', icon: '↻', sidebarKey: 'recap' };
export async function mount(root, { subpath }) {
  const sid = subpath[0] || '(no session)';
  const el = document.createElement('div');
  el.className = 'stub';
  el.innerHTML = `Recap placeholder.<div class="stub-meta">session=${sid} — Plan 5 fills in story+receipts layered layout.</div>`;
  root.appendChild(el);
  return () => {};
}
```

- [x] **Step 5: Commit**

```bash
git add plugins/taskmaster/viewer/js/screens/lessons.js plugins/taskmaster/viewer/js/screens/issues.js plugins/taskmaster/viewer/js/screens/auto-mode.js plugins/taskmaster/viewer/js/screens/recap.js
git commit -m "feat(viewer): lessons/issues/auto-mode/recap stub screens"
```

---

### Task 21: Manual smoke — every nav item resolves

- [x] **Step 1: Restart the server**

```bash
python -c "from backlog_server import _make_server; s, p = _make_server(host='127.0.0.1', port=0); print(f'http://127.0.0.1:{p}/v3'); s.serve_forever()"
```

- [x] **Step 2: Navigate via the sidebar**

Open the printed URL. Click each sidebar entry. Each should:
- Update the URL hash
- Update the page title
- Render a "stub" card with the placeholder text
- Mark the corresponding sidebar entry as `.active`

Also test deep links manually:
- `#/task/T-148` → "id=T-148"
- `#/recap/SES-0184` → "session=SES-0184"
- `#/garbage/path` → falls back to `#/dashboard`

If anything fails, debug before continuing. Nothing to commit.

---

### Task 22: Add `viewer.use_v3` flag and switch root URL when set

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py`
- Modify: `plugins/taskmaster/tests/test_server_api.py`

- [x] **Step 1: Write the failing test**

```python
def test_root_serves_v3_when_use_v3_flag_set(running_server, tmp_path):
    base, _ = running_server
    # Flip the prefs flag
    body = json.dumps({"use_v3": True}).encode()
    req = urllib.request.Request(f"{base}/api/viewer/prefs", data=body, method="PUT",
                                 headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req)

    resp = urllib.request.urlopen(f"{base}/")
    assert resp.status == 200
    body = resp.read().decode()
    # When use_v3 is True, root serves the new shell, not the legacy file
    assert "<title>Taskmaster</title>" in body
    assert 'src="/static/v3/js/main.js"' in body or 'main.js' in body

def test_root_serves_legacy_by_default(running_server):
    base, _ = running_server
    resp = urllib.request.urlopen(f"{base}/")
    body = resp.read().decode()
    # The legacy viewer; whatever is in backlog-viewer.html (we just check it's NOT the v3 shell).
    # If the legacy file isn't present in the test fixture, this test should xfail rather than fail.
    # Heuristic: legacy file is much larger and includes 'jsyaml' inline.
    # If legacy isn't shipped to test fixture, accept either; but assert v3 marker is absent.
    assert 'src="/static/v3/js/main.js"' not in body
```

- [x] **Step 2: Run tests**

Run: `python -m pytest plugins/taskmaster/tests/test_server_api.py::test_root_serves_v3_when_use_v3_flag_set -v plugins/taskmaster/tests/test_server_api.py::test_root_serves_legacy_by_default -v`
Expected: FAIL (root currently serves legacy unconditionally)

- [x] **Step 3: Add `use_v3` to the prefs defaults and wire root**

In `taskmaster_v3.py`, add `"use_v3": False` to `VIEWER_PREFS_DEFAULTS` (top level).

In `backlog_server.py` `_Handler.do_GET`, replace the root handler so it consults the flag. Add at the start of the existing root branch:

```python
if self.path == "/" or self.path == "/index.html":
    try:
        prefs = load_viewer_prefs()
        if prefs.get("use_v3"):
            self.path = "/v3"
            return self.do_GET()
    except Exception:
        pass
    # ... fall through to existing legacy serving
```

- [x] **Step 4: Run tests**

Run: `python -m pytest plugins/taskmaster/tests/test_server_api.py -v -k root_serves`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_server_api.py
git commit -m "feat(taskmaster): viewer.use_v3 flag — root serves v3 when enabled"
```

---

## M5 — Polling + Smoke Tests

### Task 23: Set up Playwright

**Files:**
- Create: `plugins/taskmaster/viewer/tests/package.json`
- Create: `plugins/taskmaster/viewer/tests/playwright.config.js`

- [x] **Step 1: Write `package.json`**

```json
{
  "name": "taskmaster-viewer-tests",
  "private": true,
  "scripts": {
    "test": "playwright test"
  },
  "devDependencies": {
    "@playwright/test": "^1.45.0"
  }
}
```

- [x] **Step 2: Write `playwright.config.js`**

```js
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: '.',
  testMatch: /.*\.spec\.js/,
  timeout: 15_000,
  retries: 0,
  use: {
    baseURL: process.env.VIEWER_BASE_URL || 'http://127.0.0.1:8765',
    headless: true,
  },
});
```

- [x] **Step 3: Install Playwright**

```bash
cd plugins/taskmaster/viewer/tests && npm install
npx playwright install chromium
```

(If `npm` is unavailable, document the manual install in a `README.md` and skip. The Python tests still cover server behavior.)

- [x] **Step 4: Commit**

```bash
git add plugins/taskmaster/viewer/tests/package.json plugins/taskmaster/viewer/tests/playwright.config.js
git commit -m "test(viewer): playwright config + dependency manifest"
```

---

### Task 24: Write the smoke test

**Files:**
- Create: `plugins/taskmaster/viewer/tests/smoke.spec.js`

- [x] **Step 1: Write the test**

```js
import { test, expect } from '@playwright/test';

const ROUTES = [
  { hash: '#/dashboard',          title: 'Dashboard',           sidebarKey: 'dashboard' },
  { hash: '#/kanban',             title: 'Kanban',              sidebarKey: 'kanban' },
  { hash: '#/sessions',           title: 'Sessions / Handovers',sidebarKey: 'sessions' },
  { hash: '#/lessons',            title: 'Lessons',             sidebarKey: 'lessons' },
  { hash: '#/issues',             title: 'Issues',              sidebarKey: 'issues' },
  { hash: '#/auto',               title: 'Auto Mode',           sidebarKey: 'auto_mode' },
  { hash: '#/recap',              title: 'Recap',               sidebarKey: 'recap' },
  { hash: '#/recap/SES-0184',     title: 'Recap',               sidebarKey: 'recap' },
  { hash: '#/task/T-148',         title: 'Task Detail',         sidebarKey: null },
];

test.describe('Viewer v3 smoke', () => {
  test('boots and renders sidebar', async ({ page }) => {
    const errors = [];
    page.on('pageerror', e => errors.push(String(e)));

    await page.goto('/v3');
    await expect(page.locator('#sidebar .sidebar-link')).toHaveCount(7);
    await expect(page.locator('#page-title')).not.toHaveText('Loading…');
    expect(errors).toEqual([]);
  });

  for (const r of ROUTES) {
    test(`route ${r.hash} resolves`, async ({ page }) => {
      const errors = [];
      page.on('pageerror', e => errors.push(String(e)));

      await page.goto('/v3');
      await page.evaluate(h => location.hash = h, r.hash);
      await expect(page.locator('#page-title')).toHaveText(r.title);
      await expect(page.locator('.screen-mount .stub')).toBeVisible();
      if (r.sidebarKey) {
        await expect(page.locator(`.sidebar-link[data-key="${r.sidebarKey}"]`)).toHaveClass(/active/);
      }
      expect(errors).toEqual([]);
    });
  }

  test('unknown hash falls back to dashboard', async ({ page }) => {
    await page.goto('/v3');
    await page.evaluate(() => location.hash = '#/garbage');
    await expect(page.locator('#page-title')).toHaveText('Dashboard');
  });
});
```

- [x] **Step 2: Add a test runner that boots the server**

Create `plugins/taskmaster/viewer/tests/run_smoke.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."

# Boot the server in the background on a known port.
PORT=8765
python -c "
from backlog_server import _make_server
s, p = _make_server(host='127.0.0.1', port=$PORT)
import threading
threading.Thread(target=s.serve_forever, daemon=False).start()
" &
SERVER_PID=$!

# Wait for it to be up.
for i in {1..40}; do
  if curl -fsS "http://127.0.0.1:$PORT/api/identity" >/dev/null 2>&1; then break; fi
  sleep 0.1
done

# Run Playwright.
cd viewer/tests
VIEWER_BASE_URL="http://127.0.0.1:$PORT" npx playwright test
RESULT=$?

# Tear down.
kill $SERVER_PID 2>/dev/null || true
exit $RESULT
```

Make it executable: `chmod +x plugins/taskmaster/viewer/tests/run_smoke.sh`

- [x] **Step 3: Run the smoke**

```bash
bash plugins/taskmaster/viewer/tests/run_smoke.sh
```

Expected: 11 tests PASS (boot + 9 routes + fallback). If npm/playwright isn't installed, Python tests already cover the server side; skip and note in commit message.

- [x] **Step 4: Commit**

```bash
git add plugins/taskmaster/viewer/tests/smoke.spec.js plugins/taskmaster/viewer/tests/run_smoke.sh
git commit -m "test(viewer): playwright smoke covering all routes"
```

---

### Task 25: Verify prefs round-trip end-to-end

**Files:**
- Modify: `plugins/taskmaster/viewer/tests/smoke.spec.js`

- [ ] **Step 1: Add an integration test**

Append to `smoke.spec.js`:

```js
test('prefs persist via the API and are reflected in store', async ({ page }) => {
  await page.goto('/v3');

  // Mutate via the same path screens will use.
  await page.evaluate(async () => {
    const resp = await fetch('/api/viewer/prefs', {
      method: 'PUT',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ theme: 'light', kanban: { filters: { search: 'auth' } } }),
    });
    if (!resp.ok) throw new Error('PUT failed');
  });

  // Reload, then read prefs from /api/viewer/prefs.
  await page.reload();
  const prefs = await page.evaluate(async () => {
    const resp = await fetch('/api/viewer/prefs');
    return resp.json();
  });

  expect(prefs.theme).toBe('light');
  expect(prefs.kanban.filters.search).toBe('auth');
});
```

- [ ] **Step 2: Run it**

```bash
bash plugins/taskmaster/viewer/tests/run_smoke.sh
```

Expected: 12 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/tests/smoke.spec.js
git commit -m "test(viewer): prefs round-trip integration smoke"
```

---

### Task 26: Document how to develop against the new viewer

**Files:**
- Create: `plugins/taskmaster/viewer/README.md`

- [ ] **Step 1: Write README**

```markdown
# Taskmaster Viewer (v3)

Modular rebuild of the legacy `backlog-viewer.html`. Active development under Plans 1–6 of the redesign.

## Layout

- `index.html` — shell
- `css/tokens.css` — single source of truth for design tokens. Other CSS uses `var(--*)` only.
- `css/shell.css` — shell, sidebar, topbar
- `css/components.css` — shared chips/pills/buttons
- `css/screens/*.css` — per-screen styles (added in Plans 2–6)
- `js/main.js` — entry; boots store, sidebar, router, polling
- `js/router.js` — hash routing
- `js/store.js` — in-memory state + subscriptions
- `js/api.js` — HTTP client for `/api/*`
- `js/components/*.js` — shared UI helpers
- `js/screens/*.js` — one module per screen, exports `mount(root, deps)` and `meta`

## Run

```bash
# From the plugin dir, on any free port:
python -c "from backlog_server import _make_server; s, p = _make_server(host='127.0.0.1', port=0); print(f'http://127.0.0.1:{p}/v3'); s.serve_forever()"
```

The legacy viewer still serves at `/`. Set `viewer.use_v3 = true` in `.taskmaster/viewer.json` (or via `PUT /api/viewer/prefs`) to flip the root URL.

## Test

- Server: `python -m pytest plugins/taskmaster/tests/`
- UI smoke: `bash plugins/taskmaster/viewer/tests/run_smoke.sh`
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/README.md
git commit -m "docs(viewer): README"
```

---

### Task 27: Run full test suite + push status

- [ ] **Step 1: Run all tests**

```bash
python -m pytest plugins/taskmaster/tests/ -v
bash plugins/taskmaster/viewer/tests/run_smoke.sh
```

Expected: all green.

- [ ] **Step 2: Commit any straggling fixes**

If anything fails, fix it, then commit with `fix(viewer): <what was wrong>`.

- [ ] **Step 3: No push**

Per user policy, do not push to remote.

---

## M6 — Plan Handoff

### Task 28: Verify Plan 1 deliverables match spec scope

- [ ] **Step 1: Walk the spec checklist**

Confirm each of these spec sections has at least skeleton support:
- §3.10 v3 grounding — viewer reads existing v3 entity files via `/backlog.yaml` polling. ✓
- §3.11 Sidebar — implemented in `sidebar.js`. ✓
- §5 Implementation notes — `viewer.json` prefs file with all the keys mentioned (card_density, view per screen, dashboard.layout, kanban.filters, lessons.thresholds, issues.aging). ✓

- [ ] **Step 2: Confirm hand-off contract for Plans 2–6**

Each subsequent plan inherits the **architectural conventions** at the top of this plan (module style, screen module shape, CSS naming, state+API, routing, persistence, tests). When writing those plans, reference this section verbatim — do not redefine.

- [ ] **Step 3: Commit final state**

If any docs were updated:
```bash
git add docs/superpowers/plans/2026-04-26-viewer-redesign-plan-1-foundation.md
git commit -m "docs(plan): foundation plan written"
```

---

**End of Plan 1.** Total tasks: 28. Estimated execution time: 1–2 sessions for an engineer following each step.
