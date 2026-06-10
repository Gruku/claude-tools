# Dashboard Desk + Sticky Notes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the broken Continuity dashboard with "The Desk" — a sticky-notes-first dashboard with a pruned continuity band — plus a full notes entity (files, MCP tools, HTTP API), bundled viewer bug fixes, and skill integration. Target: taskmaster **3.15.0**.

**Architecture:** Notes are markdown files in `.taskmaster/notes/` mirroring the ideas entity (helpers in `taskmaster_v3.py`, MCP tools + HTTP routes in `backlog_server.py`). The viewer gets a new `desk.js` screen at `#/dashboard` that renders a paper-note board (new components) above a pruned continuity band (reusing `spine`/`item-row`/`decision-card`). Old continuity screen, hero, view-switcher, resume-rail, and bento leftovers are deleted.

**Tech Stack:** Python 3.11 (stdlib http.server + FastMCP), vanilla ES modules viewer, pytest, node --test, @playwright/test.

**Spec:** `docs/superpowers/specs/2026-06-10-dashboard-sticky-notes-design.md`

**Branch:** `feat/dashboard-sticky-notes` (already created, stacked on `feat/c2-live-component-diagram`).

**Working rules for every task:**
- Commit with explicit pathspecs only (`git add <file> <file>` — never `git add -A`). Stray working-tree files exist (screenshots, test pollution); do not sweep them in.
- Run commands from the repo root `C:\Users\gruku\Files\Claude\claude-tools` unless stated.
- Python tests: `python -m pytest plugins/taskmaster/tests/<file> -v` (bash tool).
- Viewer unit tests: `node --test "plugins/taskmaster/viewer/tests/unit/<file>"`.

---

## File structure (what gets created/modified/deleted)

| Action | Path | Responsibility |
|---|---|---|
| Modify | `plugins/taskmaster/taskmaster_v3.py` | note entity helpers (file CRUD) — append new section after ideas section (~line 3710) |
| Modify | `plugins/taskmaster/backlog_server.py` | 5 MCP tools (after `backlog_idea_update` ~line 3719); GET route (after `/api/handover/` ~line 8056); 3 POST routes (after `/api/ideas` block ~line 8191) |
| Create | `plugins/taskmaster/tests/test_notes_entity.py` | pytest: file helpers |
| Create | `plugins/taskmaster/tests/test_api_notes.py` | pytest: HTTP endpoints |
| Create | `plugins/taskmaster/viewer/vendor/marked.min.js` | vendored marked@12.0.2 (replaces broken-SRI CDN tag) |
| Modify | `plugins/taskmaster/viewer/index.html` | local marked, favicon, desk.css link, drop dashboard.css link |
| Delete | `plugins/taskmaster/viewer/js/components/board-surface.js` | orphaned bento leftover |
| Delete | `plugins/taskmaster/viewer/css/screens/dashboard.css` | orphaned bento styles |
| Modify | `plugins/taskmaster/viewer/js/components/sidebar.js` | identity replay fix (v? bug) |
| Modify | `plugins/taskmaster/viewer/css/shell.css` + `css/tokens.css` | brand clip fix |
| Modify | `plugins/taskmaster/viewer/js/api.js` | notes API methods |
| Create | `plugins/taskmaster/viewer/js/lib/desk.js` | pure logic: rail pruning, note sort, tilt hash, first line |
| Create | `plugins/taskmaster/viewer/js/components/desk/note-card.js` | paper note card (view/edit/pin/archive) |
| Create | `plugins/taskmaster/viewer/js/components/desk/composer.js` | quick-add paper composer |
| Create | `plugins/taskmaster/viewer/js/screens/desk.js` | dashboard screen: board + continuity band |
| Create | `plugins/taskmaster/viewer/css/screens/desk.css` | board grid, paper styles, band layout |
| Modify | `plugins/taskmaster/viewer/js/main.js` | `/dashboard` → desk.js |
| Delete | `plugins/taskmaster/viewer/js/screens/continuity.js`, `js/components/continuity/{view-switcher,hero,resume-rail}.js` | replaced by desk |
| Modify | `plugins/taskmaster/viewer/js/lib/continuity.js` | drop `groupByTime`/`groupByEntity`/`pickHero`; keep `groupByAction` |
| Modify | `plugins/taskmaster/viewer/css/screens/continuity.css` | delete dead blocks (hero, switcher, views, co-dash shell); keep co-row/co-spine/co-decision/co-chip/co-xblock |
| Create | `plugins/taskmaster/viewer/tests/unit/desk-lib.test.js` | unit: pruning/sort/tilt |
| Create | `plugins/taskmaster/viewer/tests/desk.spec.js` | e2e: board + composer + rails |
| Modify | `plugins/taskmaster/skills/start-session/SKILL.md` | "Your desk" notes section |
| Modify | `plugins/taskmaster/skills/end-session/SKILL.md` | at-most-one-claude-note rule |
| Modify | `plugins/taskmaster/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `plugins/taskmaster/CHANGELOG.md` | 3.15.0 |

Kept (reused by desk): `js/components/continuity/{spine,item-row,decision-card}.js`, `js/lib/xml-render.js`, `js/components/auto-mode-strip.js`.

---

### Task 1: Notes entity helpers in `taskmaster_v3.py`

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py` (append a `# ── Notes (sticky) ──` section right after `list_ideas`, ~line 3710)
- Test: `plugins/taskmaster/tests/test_notes_entity.py`

- [ ] **Step 1: Write the failing tests**

Create `plugins/taskmaster/tests/test_notes_entity.py`:

```python
"""Notes (sticky) entity — file helper tests."""
import pytest

from taskmaster_v3 import (
    archive_note,
    list_notes,
    next_note_id,
    note_path,
    read_note,
    update_note,
    write_note,
)


@pytest.fixture()
def bp(tmp_path):
    tm = tmp_path / ".taskmaster"
    tm.mkdir()
    p = tm / "backlog.yaml"
    p.write_text("meta:\n  project: test\nepics: []\nphases: []\n", encoding="utf-8")
    return p


def test_write_note_allocates_sequential_ids(bp):
    nid1, path1 = write_note(bp, text="first thought", author="user")
    nid2, _ = write_note(bp, text="second thought", author="claude")
    assert nid1 == "NOTE-001"
    assert nid2 == "NOTE-002"
    assert path1 == note_path(bp, "NOTE-001")
    assert path1.exists()


def test_write_note_frontmatter_and_body(bp):
    nid, _ = write_note(bp, text="remember the milk", author="user", pinned=True)
    fm, body = read_note(bp, nid)
    assert fm["id"] == nid
    assert fm["author"] == "user"
    assert fm["pinned"] is True
    assert fm["archived"] is False
    assert fm["archived_at"] is None
    assert fm["created"].endswith("Z")
    assert fm["updated"] == fm["created"]
    assert body == "remember the milk"


def test_write_note_rejects_empty_text(bp):
    with pytest.raises(ValueError):
        write_note(bp, text="   ", author="user")


def test_write_note_rejects_bad_author(bp):
    with pytest.raises(ValueError):
        write_note(bp, text="x", author="robot")


def test_update_note_text_and_pin(bp):
    nid, _ = write_note(bp, text="v1", author="user")
    fm, body = update_note(bp, nid, text="v2", pinned=True)
    assert body == "v2"
    assert fm["pinned"] is True
    assert fm["updated"] >= fm["created"]
    # author is immutable through update
    fm2, _ = read_note(bp, nid)
    assert fm2["author"] == "user"


def test_archive_note_moves_file(bp):
    nid, live_path = write_note(bp, text="done with this", author="claude")
    fm = archive_note(bp, nid)
    assert fm["archived"] is True
    assert fm["archived_at"] is not None
    assert not live_path.exists()
    archived_path = note_path(bp, nid, archived=True)
    assert archived_path.exists()
    # read_note still finds it in the archive
    fm2, body = read_note(bp, nid)
    assert fm2["archived"] is True
    assert body == "done with this"


def test_archive_note_missing_raises(bp):
    with pytest.raises(FileNotFoundError):
        archive_note(bp, "NOTE-999")


def test_next_note_id_skips_archived(bp):
    nid, _ = write_note(bp, text="a", author="user")
    archive_note(bp, nid)
    assert next_note_id(bp) == "NOTE-002"  # archive still counts


def test_list_notes_pinned_first_then_newest(bp):
    n1, _ = write_note(bp, text="oldest", author="user")
    n2, _ = write_note(bp, text="pinned one", author="user", pinned=True)
    n3, _ = write_note(bp, text="newest", author="claude")
    notes = list_notes(bp)
    assert [n["id"] for n in notes] == [n2, n3, n1]
    assert all("body" in n for n in notes)


def test_list_notes_excludes_archived_by_default(bp):
    n1, _ = write_note(bp, text="keep", author="user")
    n2, _ = write_note(bp, text="drop", author="user")
    archive_note(bp, n2)
    assert [n["id"] for n in list_notes(bp)] == [n1]
    assert {n["id"] for n in list_notes(bp, include_archived=True)} == {n1, n2}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest plugins/taskmaster/tests/test_notes_entity.py -v`
Expected: FAIL — `ImportError: cannot import name 'write_note'`.

- [ ] **Step 3: Implement the helpers**

In `plugins/taskmaster/taskmaster_v3.py`, directly after the `list_ideas` function (after its closing `return`, ~line 3712 — search for `def list_ideas` and append after the function ends), add:

```python
# ── Notes (sticky) ────────────────────────────────────────────
# A note is the lightest entity: freeform markdown body + author + pin.
# No title, no status, no links. Viewer-created notes are author "user";
# MCP-created notes are author "claude". Archive = move to _archive/.

NOTE_AUTHORS = ("user", "claude")


def note_dir(backlog_path: Path) -> Path:
    return backlog_path.parent / "notes"


def note_archive_dir(backlog_path: Path) -> Path:
    return note_dir(backlog_path) / "_archive"


def note_path(backlog_path: Path, note_id: str, archived: bool = False) -> Path:
    base = note_archive_dir(backlog_path) if archived else note_dir(backlog_path)
    return base / f"{note_id}.md"


def _resolve_note_path(backlog_path: Path, note_id: str) -> Path:
    """Return the existing path for a note (live first, then archive)."""
    live = note_path(backlog_path, note_id)
    if live.exists():
        return live
    archived = note_path(backlog_path, note_id, archived=True)
    if archived.exists():
        return archived
    raise FileNotFoundError(f"Note not found: {note_id}")


def list_note_ids(backlog_path: Path, include_archived: bool = False) -> list[str]:
    """Note ids on disk, sorted numerically. Archived ids always counted by
    next_note_id; only returned here when include_archived=True."""
    def _rank(p: Path) -> int:
        m = re.search(r"(\d+)$", p.stem)
        return int(m.group(1)) if m else -1

    dirs = [note_dir(backlog_path)]
    if include_archived:
        dirs.append(note_archive_dir(backlog_path))
    out: list[Path] = []
    for d in dirs:
        if d.exists():
            out.extend(d.glob("NOTE-*.md"))
    return [p.stem for p in sorted(out, key=_rank)]


def next_note_id(backlog_path: Path) -> str:
    """Allocate the next NOTE-NNN id. Considers live AND archived notes so
    archiving never causes id reuse."""
    nums: list[int] = []
    for ident in list_note_ids(backlog_path, include_archived=True):
        m = re.search(r"(\d+)$", ident)
        if m:
            nums.append(int(m.group(1)))
    n = (max(nums) + 1) if nums else 1
    return f"NOTE-{n:03d}"


def _validate_note(fm: dict[str, Any], body: str) -> None:
    if not body or not body.strip():
        raise ValueError("note text is required")
    if fm.get("author") not in NOTE_AUTHORS:
        raise ValueError(f"note author must be one of {NOTE_AUTHORS}")


def write_note(
    backlog_path: Path,
    *,
    text: str,
    author: str = "claude",
    pinned: bool = False,
    note_id: str | None = None,
) -> tuple[str, Path]:
    """Create a sticky note. Returns (id, path). Body = the note text."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    fm: dict[str, Any] = {
        "id": "PENDING",
        "author": author,
        "created": now,
        "updated": now,
        "pinned": bool(pinned),
        "archived": False,
        "archived_at": None,
    }
    _validate_note(fm, text)
    if note_id:
        nid = note_id
        target = note_path(backlog_path, nid)
        target.parent.mkdir(parents=True, exist_ok=True)
    else:
        note_dir(backlog_path).mkdir(parents=True, exist_ok=True)
        for _ in range(64):
            candidate = next_note_id(backlog_path)
            candidate_target = note_path(backlog_path, candidate)
            try:
                candidate_target.touch(exist_ok=False)
                nid, target = candidate, candidate_target
                break
            except FileExistsError:
                continue
        else:
            raise RuntimeError("could not allocate NOTE-NNN id after 64 attempts")
    fm["id"] = nid
    write_task_file(target, fm, text.strip())
    return nid, target


def read_note(backlog_path: Path, note_id: str) -> tuple[dict[str, Any], str]:
    fm, body = read_task_file(_resolve_note_path(backlog_path, note_id))
    return fm, body.rstrip("\n")


def update_note(
    backlog_path: Path,
    note_id: str,
    *,
    text: str | None = None,
    pinned: bool | None = None,
) -> tuple[dict[str, Any], str]:
    """Patch a note's text and/or pin state. Bumps `updated`. Author and
    created are immutable."""
    target = _resolve_note_path(backlog_path, note_id)
    fm, body = read_task_file(target)
    body = body.rstrip("\n")
    new_body = body if text is None else text.strip()
    if pinned is not None:
        fm["pinned"] = bool(pinned)
    fm["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    _validate_note(fm, new_body)
    write_task_file(target, fm, new_body)
    return fm, new_body


def archive_note(backlog_path: Path, note_id: str) -> dict[str, Any]:
    """Archive a note: set flags and move the file to _archive/."""
    live = note_path(backlog_path, note_id)
    if not live.exists():
        raise FileNotFoundError(f"Note not found: {note_id}")
    fm, body = read_task_file(live)
    fm["archived"] = True
    fm["archived_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    dest = note_path(backlog_path, note_id, archived=True)
    dest.parent.mkdir(parents=True, exist_ok=True)
    write_task_file(dest, fm, body.rstrip("\n"))
    live.unlink()
    return fm


def list_notes(backlog_path: Path, include_archived: bool = False) -> list[dict[str, Any]]:
    """All notes with bodies, pinned first then created desc."""
    out: list[dict[str, Any]] = []
    for nid in list_note_ids(backlog_path, include_archived=include_archived):
        try:
            fm, body = read_note(backlog_path, nid)
        except (OSError, ValueError, FileNotFoundError):
            continue
        if not include_archived and fm.get("archived"):
            continue
        out.append({**fm, "body": body})
    out.sort(key=lambda n: (not n.get("pinned"), _note_sort_created(n)))
    return out


def _note_sort_created(n: dict[str, Any]) -> str:
    # Invert string for desc sort inside ascending tuple sort: use negative trick
    # via sorting twice instead — simpler: sort ascending then reverse within groups.
    return n.get("created", "")
```

**Important implementation note on sorting:** the lambda above sorts created ascending; the test requires created **desc** within each pin group. Use this implementation instead of the naive one:

```python
    pinned = [n for n in out if n.get("pinned")]
    unpinned = [n for n in out if not n.get("pinned")]
    pinned.sort(key=lambda n: n.get("created", ""), reverse=True)
    unpinned.sort(key=lambda n: n.get("created", ""), reverse=True)
    return pinned + unpinned
```

(replace the `out.sort(...)` line and `_note_sort_created` helper entirely — do not keep both.)

Check imports at the top of taskmaster_v3.py: `re`, `datetime`, `timezone`, `Path`, `Any`, `write_task_file`, `read_task_file` all already exist in this module (used by the ideas section directly above). Add nothing.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest plugins/taskmaster/tests/test_notes_entity.py -v`
Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_notes_entity.py
git commit -m "feat(taskmaster): sticky notes entity — file helpers + tests"
```

---

### Task 2: MCP tools `backlog_note_*` in `backlog_server.py`

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py` (insert after `backlog_idea_update`, before `viewer_prefs_get`, ~line 3720)
- Test: extend `plugins/taskmaster/tests/test_notes_entity.py` (the MCP wrappers are thin; test the two behaviors that are theirs: author forcing and message formatting) — note FastMCP-decorated functions are invoked via their `.fn` attribute in tests.

- [ ] **Step 1: Check how existing tests call MCP tools**

Run: `grep -rn "\.fn(" plugins/taskmaster/tests/ | head -5`

If the codebase calls tools as plain functions (e.g. `backlog_server.backlog_idea_create(...)`), follow that convention instead of `.fn`. Match whatever `test_decision_entity.py` or similar does. The test code below assumes plain-call works (FastMCP ≤2 returns the original fn); adjust to `.fn(...)` if grep shows that pattern.

- [ ] **Step 2: Write the failing tests**

Append to `plugins/taskmaster/tests/test_notes_entity.py`:

```python
# ── MCP tool wrappers ────────────────────────────────────────────────────────


def _tool(t):
    """Call a FastMCP tool object or plain function uniformly."""
    return getattr(t, "fn", t)


def test_mcp_note_create_forces_claude_author(bp, monkeypatch):
    import backlog_server
    monkeypatch.setattr(backlog_server, "ROOT", bp.parent.parent)
    out = _tool(backlog_server.backlog_note_create)(text="from the session")
    assert "NOTE-001" in out
    fm, _ = read_note(bp, "NOTE-001")
    assert fm["author"] == "claude"


def test_mcp_note_list_and_archive_roundtrip(bp, monkeypatch):
    import backlog_server
    monkeypatch.setattr(backlog_server, "ROOT", bp.parent.parent)
    _tool(backlog_server.backlog_note_create)(text="alpha")
    _tool(backlog_server.backlog_note_create)(text="beta", pinned=True)
    listing = _tool(backlog_server.backlog_note_list)()
    assert "NOTE-001" in listing and "NOTE-002" in listing
    assert listing.index("NOTE-002") < listing.index("NOTE-001")  # pinned first
    out = _tool(backlog_server.backlog_note_archive)("NOTE-001")
    assert "archived" in out.lower()
    listing2 = _tool(backlog_server.backlog_note_list)()
    assert "NOTE-001" not in listing2
```

**Fixture note:** `_backlog_path()` in backlog_server derives from module-level `ROOT`; the existing pattern (see `test_api_handover_status.py`) is `monkeypatch.setattr(backlog_server, "ROOT", tmp_path)`. Here `bp` is `<tmp>/.taskmaster/backlog.yaml`, so ROOT is `bp.parent.parent`. If `_backlog_path()` resolves through `_resolve_artifact_root()` instead of plain ROOT, mirror whatever `test_api_handover_status.py` patches.

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest plugins/taskmaster/tests/test_notes_entity.py -v -k mcp`
Expected: FAIL — `AttributeError: module 'backlog_server' has no attribute 'backlog_note_create'`.

- [ ] **Step 4: Implement the MCP tools**

In `plugins/taskmaster/backlog_server.py`, after `backlog_idea_update` (ends ~line 3719) and before `@mcp.tool()\ndef viewer_prefs_get`, insert:

```python
@mcp.tool()
def backlog_note_create(text: str, pinned: bool = False) -> str:
    """Write a sticky note onto the user's Desk (dashboard).

    Notes are the lightest continuity surface: freeform, situational,
    NOT attached to tasks. Claude-created notes are stamped author
    "claude" and render visually distinct from the user's own notes.
    Write at most one consolidated note per session, and only for loose
    thoughts that fit no other entity (task/idea/issue/handover).
    """
    bp = _backlog_path()
    if not bp.exists():
        return f"Error: no backlog found at {bp}. Run `backlog_init` first."
    from taskmaster_v3 import write_note as _write_note
    try:
        nid, target = _write_note(bp, text=text, author="claude", pinned=pinned)
    except ValueError as exc:
        return f"Error: {exc}"
    try:
        rel = target.relative_to(ROOT)
    except ValueError:
        rel = target
    return f"Note created: {nid}\nFile: {rel}"


@mcp.tool()
def backlog_note_list(include_archived: bool = False) -> str:
    """List sticky notes from the user's Desk — pinned first, newest first.

    Returns one line per note: id, author, pin marker, created date, first
    line of text. Use during session start to surface the user's desk."""
    bp = _backlog_path()
    if not bp.exists():
        return "No backlog found."
    from taskmaster_v3 import list_notes as _list_notes
    notes = _list_notes(bp, include_archived=include_archived)
    if not notes:
        return "Desk is clear — no notes."
    lines = []
    for n in notes:
        first = (n.get("body") or "").strip().splitlines()[0] if n.get("body") else ""
        pin = "📌 " if n.get("pinned") else ""
        arch = " [archived]" if n.get("archived") else ""
        created = str(n.get("created", ""))[:10]
        lines.append(f"- {n['id']} ({n.get('author')}, {created}){arch} — {pin}{first}")
    return "\n".join(lines)


@mcp.tool()
def backlog_note_get(note_id: str) -> str:
    """Read one sticky note in full (frontmatter + complete text)."""
    bp = _backlog_path()
    if not bp.exists():
        return "No backlog found."
    from taskmaster_v3 import read_note as _read_note
    try:
        fm, body = _read_note(bp, note_id)
    except FileNotFoundError:
        return f"Note not found: {note_id}"
    fm_lines = [f"  {k}: {v}" for k, v in fm.items()]
    return "---\n" + "\n".join(fm_lines) + "\n---\n" + body


@mcp.tool()
def backlog_note_update(note_id: str, text: str = "", pinned: bool | None = None) -> str:
    """Edit a sticky note's text and/or pin state. Author is immutable —
    a user-authored note stays user-authored even if Claude edits it
    (avoid editing user notes unless explicitly asked)."""
    bp = _backlog_path()
    if not bp.exists():
        return "No backlog found."
    from taskmaster_v3 import update_note as _update_note
    try:
        _update_note(bp, note_id, text=text or None, pinned=pinned)
    except FileNotFoundError:
        return f"Note not found: {note_id}"
    except ValueError as exc:
        return f"Error: {exc}"
    return f"Note updated: {note_id}"


@mcp.tool()
def backlog_note_archive(note_id: str) -> str:
    """Archive a sticky note (moves it off the Desk into notes/_archive/).
    Never archive user-authored notes unless the user explicitly asks."""
    bp = _backlog_path()
    if not bp.exists():
        return "No backlog found."
    from taskmaster_v3 import archive_note as _archive_note
    try:
        _archive_note(bp, note_id)
    except FileNotFoundError:
        return f"Note not found: {note_id}"
    return f"Note archived: {note_id}"
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest plugins/taskmaster/tests/test_notes_entity.py -v`
Expected: 11 passed.

- [ ] **Step 6: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_notes_entity.py
git commit -m "feat(taskmaster): backlog_note_* MCP tools (create/list/get/update/archive)"
```

---

### Task 3: HTTP API for notes

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py` — GET route (insert after the `/api/handover/<id>` GET block, ~line 8056) and POST routes (insert after the `/api/ideas` POST block, ~line 8191)
- Test: `plugins/taskmaster/tests/test_api_notes.py`

- [ ] **Step 1: Write the failing tests**

Create `plugins/taskmaster/tests/test_api_notes.py` — copy the `server_with_root` fixture verbatim from `tests/test_api_handover_status.py` (it starts an in-process server on an ephemeral port with ROOT patched), then:

```python
"""HTTP-layer tests for /api/notes endpoints."""
import json
import urllib.request

# (server_with_root fixture copied from test_api_handover_status.py — keep
#  the import set and fixture body identical, including _init_storage())


def _post(base, path, payload):
    req = urllib.request.Request(
        f"{base}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=2) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def _get(base, path):
    with urllib.request.urlopen(f"{base}{path}", timeout=2) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def test_post_creates_user_note(server_with_root):
    base, _server, bp = server_with_root
    status, out = _post(base, "/api/notes", {"text": "hello desk"})
    assert status == 201
    assert out["ok"] is True
    assert out["id"] == "NOTE-001"
    status, listing = _get(base, "/api/notes")
    assert status == 200
    assert len(listing["notes"]) == 1
    note = listing["notes"][0]
    assert note["author"] == "user"          # HTTP channel stamps user
    assert note["body"] == "hello desk"


def test_post_empty_text_400(server_with_root):
    base, _s, _bp = server_with_root
    try:
        _post(base, "/api/notes", {"text": "  "})
        assert False, "expected 400"
    except urllib.error.HTTPError as e:
        assert e.code == 400


def test_update_and_archive_roundtrip(server_with_root):
    base, _s, _bp = server_with_root
    _post(base, "/api/notes", {"text": "v1"})
    status, out = _post(base, "/api/notes/NOTE-001/update", {"text": "v2", "pinned": True})
    assert status == 200 and out["ok"] is True
    _, listing = _get(base, "/api/notes")
    assert listing["notes"][0]["body"] == "v2"
    assert listing["notes"][0]["pinned"] is True
    status, out = _post(base, "/api/notes/NOTE-001/archive", {})
    assert status == 200
    _, listing = _get(base, "/api/notes")
    assert listing["notes"] == []
    _, listing = _get(base, "/api/notes?include_archived=1")
    assert len(listing["notes"]) == 1


def test_archive_missing_404(server_with_root):
    base, _s, _bp = server_with_root
    try:
        _post(base, "/api/notes/NOTE-999/archive", {})
        assert False, "expected 404"
    except urllib.error.HTTPError as e:
        assert e.code == 404
```

(Add `import urllib.error` to the imports.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest plugins/taskmaster/tests/test_api_notes.py -v`
Expected: FAIL — 404s from the missing routes (urllib raises HTTPError 404 on the first `_post`).

- [ ] **Step 3: Implement routes**

In `do_GET`, insert after the `/api/handover/<id>` elif block (after line ~8056, before the final `else:`):

```python
        elif clean_path == "/api/notes":
            from urllib.parse import urlparse, parse_qs
            from taskmaster_v3 import list_notes as _list_notes
            qs = parse_qs(urlparse(self.path).query)
            include_archived = qs.get("include_archived", ["0"])[0] in ("1", "true")
            bp = _backlog_path()
            notes = _list_notes(bp, include_archived=include_archived) if bp.exists() else []
            self._send_json(200, {"notes": notes})
            return
```

In `do_POST`, insert after the `/api/ideas` block's `return` (~line 8191):

```python
        if self.path == "/api/notes":
            from taskmaster_v3 import write_note as _write_note
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length).decode("utf-8") if length else ""
            try:
                payload = json.loads(raw) if raw else {}
            except Exception as e:
                self._send_json(400, {"ok": False, "error": f"invalid JSON: {e}"})
                return
            text = (payload.get("text") or "").strip()
            if not text:
                self._send_json(400, {"ok": False, "error": "text is required"})
                return
            bp = _backlog_path()
            if not bp.exists():
                self._send_json(400, {"ok": False, "error": f"no backlog at {bp}"})
                return
            try:
                nid, _target = _write_note(
                    bp, text=text, author="user",
                    pinned=bool(payload.get("pinned", False)),
                )
            except ValueError as e:
                self._send_json(400, {"ok": False, "error": str(e)})
                return
            self._send_json(201, {"ok": True, "id": nid})
            return

        m = re.fullmatch(r"/api/notes/([A-Za-z0-9_\-]+)/(update|archive)", self.path)
        if m:
            from taskmaster_v3 import update_note as _update_note, archive_note as _archive_note
            note_id, action = m.group(1), m.group(2)
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length).decode("utf-8") if length else ""
            try:
                payload = json.loads(raw) if raw else {}
            except Exception as e:
                self._send_json(400, {"ok": False, "error": f"invalid JSON: {e}"})
                return
            bp = _backlog_path()
            try:
                if action == "archive":
                    _archive_note(bp, note_id)
                else:
                    text = payload.get("text")
                    pinned = payload.get("pinned")
                    _update_note(
                        bp, note_id,
                        text=(text.strip() if isinstance(text, str) and text.strip() else None),
                        pinned=(bool(pinned) if pinned is not None else None),
                    )
            except FileNotFoundError:
                self._send_json(404, {"ok": False, "error": f"note {note_id} not found"})
                return
            except ValueError as e:
                self._send_json(400, {"ok": False, "error": str(e)})
                return
            self._send_json(200, {"ok": True, "id": note_id})
            return
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest plugins/taskmaster/tests/test_api_notes.py plugins/taskmaster/tests/test_notes_entity.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_api_notes.py
git commit -m "feat(taskmaster): /api/notes HTTP endpoints (list/create/update/archive)"
```

---

### Task 4: Vendor marked.js, favicon, drop bento dead code

**Files:**
- Create: `plugins/taskmaster/viewer/vendor/marked.min.js`
- Modify: `plugins/taskmaster/viewer/index.html`
- Delete: `plugins/taskmaster/viewer/js/components/board-surface.js`, `plugins/taskmaster/viewer/css/screens/dashboard.css`

- [ ] **Step 1: Vendor marked**

```bash
mkdir -p plugins/taskmaster/viewer/vendor
curl -sL https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js -o plugins/taskmaster/viewer/vendor/marked.min.js
head -c 200 plugins/taskmaster/viewer/vendor/marked.min.js
```

Expected: file starts with `/**\n * marked v12.0.2` or minified banner mentioning marked. Verify size > 30 KB: `wc -c plugins/taskmaster/viewer/vendor/marked.min.js`.

- [ ] **Step 2: Update index.html**

In `plugins/taskmaster/viewer/index.html`:

1. Replace line 32 (the CDN script tag with the broken `integrity` attribute):
```html
  <script src="vendor/marked.min.js"></script>
```
2. Add a favicon link in `<head>` (silences the 404):
```html
  <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'><rect width='16' height='16' rx='3' fill='%234a9eff'/></svg>">
```
3. Delete the line `<link rel="stylesheet" href="css/screens/dashboard.css">` (line 11).
4. Add `<link rel="stylesheet" href="css/screens/desk.css">` in its place (file created in Task 6 — a 404 on a stylesheet is harmless for one commit, or create an empty `desk.css` placeholder now with a `/* Desk — populated in Task 6 */` comment; do the latter).

- [ ] **Step 3: Verify the server serves /vendor/**

Check how static files are routed: `grep -n "css/\|/js/\|content_type" plugins/taskmaster/backlog_server.py | grep -i "serve\|static" | head`. The viewer serves files relative to the viewer dir — find the static handler in `do_GET` (the `/v3` branch) and confirm it maps arbitrary subpaths (it serves `js/` and `css/` already; `vendor/` should flow through the same branch). If the static handler whitelists extensions or dirs, add `vendor/` + `.js` accordingly.

Run: `python -m pytest plugins/taskmaster/tests/ -k "smoke or server" -x -q` (fast sanity) — or if no such tests, start the server and curl:
```bash
(PYTHONPATH=plugins/taskmaster python -c "from backlog_server import _make_server; s,p=_make_server(host='127.0.0.1', port=8799); import threading; threading.Thread(target=s.serve_forever,daemon=True).start(); import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8799/v3/vendor/marked.min.js').status)")
```
Expected: `200`.

- [ ] **Step 4: Delete dead bento files**

```bash
git rm plugins/taskmaster/viewer/js/components/board-surface.js plugins/taskmaster/viewer/css/screens/dashboard.css
grep -rn "board-surface\|dashboard.css" plugins/taskmaster/viewer/js plugins/taskmaster/viewer/index.html
```
Expected: grep returns nothing (no remaining references).

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/viewer/vendor/marked.min.js plugins/taskmaster/viewer/index.html plugins/taskmaster/viewer/css/screens/desk.css
git commit -m "fix(viewer): vendor marked.min.js (broken CDN SRI blocked markdown), favicon, drop bento dead code"
```

---

### Task 5: Sidebar fixes — "v?" version + clipped brand

**Files:**
- Modify: `plugins/taskmaster/viewer/js/components/sidebar.js:108-111`
- Modify: `plugins/taskmaster/viewer/css/shell.css:61` and `css/tokens.css:109`

- [ ] **Step 1: Fix the version replay bug**

Root cause: `main.js` calls `store.setIdentity(identity)` (boot line 73) **before** `mountSidebar` (line 82); `store.subscribe` does not replay the current value, so the subscriber never fires and the chip stays "v?".

In `sidebar.js`, replace lines 108-111:

```js
  // Identity → version
  const applyIdentity = (id) => {
    if (id?.version) el.querySelector('#sidebar-version').textContent = 'v' + id.version;
  };
  const unsubIdentity = store.subscribe('identity', applyIdentity);
  applyIdentity(store.getIdentity());   // replay — identity is set before sidebar mounts
```

- [ ] **Step 2: Fix the clipped brand**

In `css/tokens.css` line 109: `--sidebar-w: 220px;` → `--sidebar-w: 236px;`

In `css/shell.css` line 61, make the name shrink gracefully instead of hard-clipping mid-glyph:

```css
.sidebar-logo .name { font-weight: 600; font-size: var(--text-md); flex: 1; min-width: 0; text-overflow: ellipsis; }
```

(`.name` already has `white-space: nowrap; overflow: hidden;` from the collapse-transition block at shell.css:134.)

- [ ] **Step 3: Visual verify**

Start the server (repo root, `PYTHONPATH=plugins/taskmaster python -c "from backlog_server import _make_server; s,p=_make_server(host='127.0.0.1', port=8771); print(p); s.serve_forever()"` backgrounded), then `npx playwright-cli -s=qa open http://127.0.0.1:8771/v3` and screenshot. Expected: full "Taskmaster" brand, real version like "v3.15.0" (no "v?"), zero console errors (marked SRI error gone after Task 4).

- [ ] **Step 4: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/sidebar.js plugins/taskmaster/viewer/css/shell.css plugins/taskmaster/viewer/css/tokens.css
git commit -m "fix(viewer): sidebar version replay (v? bug) + brand clipping"
```

---

### Task 6: Desk pure logic + api.js methods (unit-tested)

**Files:**
- Create: `plugins/taskmaster/viewer/js/lib/desk.js`
- Modify: `plugins/taskmaster/viewer/js/api.js` (add methods to the exported `api` object — find `export const api = {` and append in kind)
- Test: `plugins/taskmaster/viewer/tests/unit/desk-lib.test.js`

- [ ] **Step 1: Write the failing unit tests**

Create `plugins/taskmaster/viewer/tests/unit/desk-lib.test.js` (match the import style of existing files in `tests/unit/` — check one first; they import ESM via relative paths):

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { buildRails, sortNotes, tiltFor, firstLine, RAIL_CAP, MAX_AGE_DAYS } from '../../js/lib/desk.js';

const item = (over = {}) => ({
  id: 'X', type: 'task', title: 't', action_class: 'resume',
  age_days: 1, timestamp: '2026-06-09T00:00:00Z', ...over,
});

test('buildRails groups by action_class and caps at RAIL_CAP', () => {
  const items = Array.from({ length: 9 }, (_, i) =>
    item({ id: `T-${i}`, age_days: i }));
  const rails = buildRails(items);
  assert.equal(rails.resume.items.length, RAIL_CAP);
  assert.equal(rails.resume.older, 9 - RAIL_CAP);
  // freshest first
  assert.equal(rails.resume.items[0].id, 'T-0');
});

test('buildRails excludes items older than MAX_AGE_DAYS from cards', () => {
  const rails = buildRails([
    item({ id: 'fresh', age_days: 2 }),
    item({ id: 'stale', age_days: MAX_AGE_DAYS + 5 }),
  ]);
  assert.deepEqual(rails.resume.items.map(i => i.id), ['fresh']);
  assert.equal(rails.resume.older, 1);
});

test('buildRails routes decide/review/clean-up and ignores ambient', () => {
  const rails = buildRails([
    item({ id: 'd', action_class: 'decide', type: 'decision' }),
    item({ id: 'r', action_class: 'review' }),
    item({ id: 'c', action_class: 'clean-up' }),
    item({ id: 'a', action_class: 'ambient' }),
  ]);
  assert.equal(rails.decide.items.length, 1);
  assert.equal(rails.review.items.length, 1);
  assert.equal(rails.cleanup.items.length, 1);
  assert.equal(rails.resume.items.length, 0);
});

test('sortNotes: pinned first, then created desc', () => {
  const notes = [
    { id: 'NOTE-001', pinned: false, created: '2026-06-01T00:00:00Z' },
    { id: 'NOTE-002', pinned: true,  created: '2026-05-01T00:00:00Z' },
    { id: 'NOTE-003', pinned: false, created: '2026-06-05T00:00:00Z' },
  ];
  assert.deepEqual(sortNotes(notes).map(n => n.id), ['NOTE-002', 'NOTE-003', 'NOTE-001']);
});

test('tiltFor is deterministic and bounded', () => {
  assert.equal(tiltFor('NOTE-001'), tiltFor('NOTE-001'));
  for (const id of ['NOTE-001', 'NOTE-002', 'NOTE-017', 'NOTE-123']) {
    const t = tiltFor(id);
    assert.ok(Math.abs(t) <= 1.2, `${id} tilt ${t} out of range`);
  }
  // not all identical
  const tilts = new Set(['NOTE-001','NOTE-002','NOTE-003','NOTE-004'].map(tiltFor));
  assert.ok(tilts.size > 1);
});

test('firstLine returns the first non-empty line, stripped of markdown heading', () => {
  assert.equal(firstLine('# Hello\nworld'), 'Hello');
  assert.equal(firstLine('\n\n  plain text  \nmore'), 'plain text');
  assert.equal(firstLine(''), '');
});
```

- [ ] **Step 2: Run to verify failure**

Run: `node --test "plugins/taskmaster/viewer/tests/unit/desk-lib.test.js"`
Expected: FAIL — cannot find module `../../js/lib/desk.js`.

- [ ] **Step 3: Implement `js/lib/desk.js`**

```js
// Pure logic for the Desk dashboard. No DOM.

export const RAIL_CAP = 5;       // max cards per continuity rail
export const MAX_AGE_DAYS = 30;  // older items collapse into the "+N older" link

// Continuity items → four rails. Items beyond cap or age window are counted
// in `older` instead of rendered; ambient items are not desk material.
export function buildRails(items) {
  const rails = {
    resume:  { items: [], older: 0 },
    review:  { items: [], older: 0 },
    decide:  { items: [], older: 0 },
    cleanup: { items: [], older: 0 },
  };
  const KEY = { resume: 'resume', review: 'review', decide: 'decide', 'clean-up': 'cleanup' };
  const sorted = [...(items || [])].sort((a, b) => (a.age_days ?? 0) - (b.age_days ?? 0));
  for (const it of sorted) {
    const key = KEY[it.action_class];
    if (!key) continue;
    const rail = rails[key];
    if ((it.age_days ?? 0) > MAX_AGE_DAYS || rail.items.length >= RAIL_CAP) {
      rail.older += 1;
    } else {
      rail.items.push(it);
    }
  }
  return rails;
}

export function sortNotes(notes) {
  const pinned = (notes || []).filter(n => n.pinned);
  const rest = (notes || []).filter(n => !n.pinned);
  const byCreatedDesc = (a, b) => (b.created || '').localeCompare(a.created || '');
  return [...pinned.sort(byCreatedDesc), ...rest.sort(byCreatedDesc)];
}

// Deterministic paper tilt in degrees, −1.2…+1.2, derived from the id so the
// board is stable across renders. Static placement — never animated.
export function tiltFor(id) {
  let h = 0;
  for (let i = 0; i < (id || '').length; i++) h = ((h << 5) - h + id.charCodeAt(i)) | 0;
  return Math.round(((Math.abs(h) % 241) / 240 * 2.4 - 1.2) * 100) / 100;
}

export function firstLine(text) {
  for (const line of (text || '').split('\n')) {
    const t = line.trim().replace(/^#+\s*/, '');
    if (t) return t;
  }
  return '';
}
```

- [ ] **Step 4: Run unit tests**

Run: `node --test "plugins/taskmaster/viewer/tests/unit/desk-lib.test.js"`
Expected: all pass. Also run the whole unit suite to check for regressions: `node --test "plugins/taskmaster/viewer/tests/unit/*.test.js"` (pre-existing failures from ISS-021 may exist — only ensure desk-lib passes and nothing NEW fails).

- [ ] **Step 5: Add api.js methods**

In `plugins/taskmaster/viewer/js/api.js`, find the exported `api` object (`grep -n "export const api" plugins/taskmaster/viewer/js/api.js`) and add:

```js
  // ── Notes (Desk) ──────────────────────────────────────────────
  notes: (includeArchived = false) =>
    http('GET', `/api/notes${includeArchived ? '?include_archived=1' : ''}`),
  createNote: (text, pinned = false) => http('POST', '/api/notes', { text, pinned }),
  updateNote: (id, patch) => http('POST', `/api/notes/${encodeURIComponent(id)}/update`, patch),
  archiveNote: (id) => http('POST', `/api/notes/${encodeURIComponent(id)}/archive`, {}),
```

(Adapt to the object's actual method style — it already has `get`/`post` style helpers used by continuity.js (`api.get('/api/continuity')`); if the object exposes generic `get`/`post`, these named wrappers still belong on it for discoverability.)

- [ ] **Step 6: Commit**

```bash
git add plugins/taskmaster/viewer/js/lib/desk.js plugins/taskmaster/viewer/js/api.js plugins/taskmaster/viewer/tests/unit/desk-lib.test.js
git commit -m "feat(viewer): desk pure logic (rails pruning, note sort, tilt) + notes api methods"
```

---

### Task 7: Paper note components — note-card + composer + desk.css

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/desk/note-card.js`
- Create: `plugins/taskmaster/viewer/js/components/desk/composer.js`
- Modify: `plugins/taskmaster/viewer/css/screens/desk.css` (replace the placeholder)

- [ ] **Step 1: note-card.js**

```js
import { h } from '../../util/h.js';
import { tiltFor } from '../../lib/desk.js';
import { renderMarkdown } from '../markdown.js';

// A paper sticky note. Light paper on the dark desk; user notes are warm
// yellow paper, claude notes cool blue paper. Static tilt from id hash.
// onPin(note), onArchive(note), onSave(note, newText) are async callbacks.
export function createNoteCard({ note, onPin, onArchive, onSave }) {
  const root = h('article', {
    class: `dk-note dk-note--${note.author === 'claude' ? 'claude' : 'user'}`
           + (note.pinned ? ' is-pinned' : ''),
    'data-note-id': note.id,
  });
  root.style.setProperty('--tilt', tiltFor(note.id) + 'deg');

  const when = relTime(note.created);
  const who = note.author === 'claude' ? '✦ claude' : 'you';

  const pinBtn = h('button', {
    class: 'dk-note__pin', type: 'button',
    title: note.pinned ? 'Unpin' : 'Pin',
    'aria-pressed': note.pinned ? 'true' : 'false',
    on: { click: (e) => { e.stopPropagation(); onPin?.(note); } },
  }, '📌');
  const archiveBtn = h('button', {
    class: 'dk-note__archive', type: 'button', title: 'Archive note',
    on: { click: (e) => { e.stopPropagation(); onArchive?.(note); } },
  }, '✕');

  const head = h('header', { class: 'dk-note__head' },
    h('span', { class: 'dk-note__who' }, who),
    h('span', { class: 'dk-note__when' }, when),
    pinBtn, archiveBtn);

  const body = h('div', { class: 'dk-note__body' });
  renderMarkdown(body, note.body || '');

  // Click body → inline edit (textarea swap). Esc cancels, Ctrl+Enter / blur saves.
  body.addEventListener('click', () => {
    if (root.classList.contains('is-editing')) return;
    root.classList.add('is-editing');
    const ta = h('textarea', { class: 'dk-note__edit' });
    ta.value = note.body || '';
    const done = async (save) => {
      root.classList.remove('is-editing');
      ta.replaceWith(body);
      if (save && ta.value.trim() && ta.value !== note.body) {
        await onSave?.(note, ta.value);
      }
    };
    ta.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') done(false);
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) done(true);
    });
    ta.addEventListener('blur', () => done(true));
    body.replaceWith(ta);
    ta.focus();
    ta.setSelectionRange(ta.value.length, ta.value.length);
  });

  root.append(head, body);
  return { root };
}

function relTime(iso) {
  if (!iso) return '';
  const ms = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(ms / 60000);
  if (mins < 60) return `${Math.max(mins, 0)}m`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h`;
  return `${Math.floor(hours / 24)}d`;
}
```

**Check before writing:** `renderMarkdown`'s real signature — `sed -n '1,30p' plugins/taskmaster/viewer/js/components/markdown.js`. If it *returns* a node instead of accepting a container, adapt (`body.appendChild(renderMarkdown(note.body))`). Use whatever the actual export is; the fallback when `window.marked` is absent must keep plain text visible.

- [ ] **Step 2: composer.js**

```js
import { h } from '../../util/h.js';

// Quick-add composer styled as a blank paper note. Enter commits,
// Shift+Enter inserts a newline. Stays focused after submit for rapid capture.
export function createComposer({ onCreate }) {
  const ta = h('textarea', {
    class: 'dk-composer__input',
    placeholder: 'Write a note…',
    rows: 1,
    'aria-label': 'Write a note',
  });
  const root = h('div', { class: 'dk-note dk-composer' }, ta);

  ta.addEventListener('keydown', async (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      const text = ta.value.trim();
      if (!text) return;
      ta.value = '';
      ta.rows = 1;
      await onCreate?.(text);
      ta.focus();
    }
  });
  // Grow with content (no scrollbars inside a "paper" note).
  ta.addEventListener('input', () => {
    ta.rows = Math.min(8, Math.max(1, ta.value.split('\n').length));
  });

  return { root, focus: () => ta.focus() };
}
```

- [ ] **Step 3: desk.css** (replace placeholder content entirely)

```css
/* Desk — sticky-notes-first dashboard.
   Paper notes are the ONE place light surfaces appear on the dark canvas:
   that contrast (plus static tilt + folded corner) is what makes them read
   as physical notes. No box-shadows, no hover motion — per design rules. */

.dk-desk { display: flex; flex-direction: column; gap: var(--sp-7); padding: var(--sp-6) var(--sp-8); }

/* ── Board ──────────────────────────────────────────────────────────────── */
.dk-board { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: var(--sp-5); align-items: start; }

.dk-note {
  --paper: #e8d98a;            /* user: post-it yellow */
  --paper-edge: #d8c66f;
  --paper-ink: #2c2718;
  --paper-ink-soft: rgba(44, 39, 24, 0.62);
  position: relative;
  background: var(--paper);
  color: var(--paper-ink);
  border: 1px solid var(--paper-edge);
  border-radius: 2px;            /* paper, not UI card */
  padding: var(--sp-4) var(--sp-5) var(--sp-6);
  min-height: 150px;
  transform: rotate(var(--tilt, 0deg));
  font-size: var(--text-sm);
  line-height: 1.45;
  overflow-wrap: break-word;
}
/* Folded bottom-right corner. */
.dk-note::after {
  content: '';
  position: absolute; right: 0; bottom: 0;
  width: 18px; height: 18px;
  background: linear-gradient(135deg, transparent 50%, var(--bg-canvas) 50%);
}
.dk-note::before {
  content: '';
  position: absolute; right: 18px; bottom: 0; left: 0; height: 0;
}
.dk-note--claude {
  --paper: #9fc0e8;            /* claude: cool blue paper */
  --paper-edge: #86abd6;
  --paper-ink: #16202e;
  --paper-ink-soft: rgba(22, 32, 46, 0.62);
}
.dk-note:hover { background: color-mix(in srgb, var(--paper) 94%, white); }

.dk-note__head {
  display: flex; align-items: baseline; gap: var(--sp-2);
  font-size: var(--text-xs); text-transform: uppercase; letter-spacing: 0.07em;
  color: var(--paper-ink-soft);
  margin-bottom: var(--sp-3);
}
.dk-note__who { font-weight: 600; }
.dk-note__when { margin-right: auto; }
.dk-note__pin, .dk-note__archive {
  background: none; border: none; cursor: pointer; padding: 0 2px;
  font-size: var(--text-xs); color: var(--paper-ink-soft);
  opacity: 0; transition: opacity var(--t-fast) var(--ease), color var(--t-fast) var(--ease);
}
.dk-note:hover .dk-note__pin, .dk-note:hover .dk-note__archive { opacity: 1; }
.dk-note.is-pinned .dk-note__pin { opacity: 1; filter: none; }
.dk-note__pin { filter: grayscale(1); }
.dk-note__archive:hover { color: var(--red); }

/* Pinned: red pushpin dot riding the top edge. */
.dk-note.is-pinned::before {
  content: ''; left: 50%; right: auto; top: -5px; bottom: auto;
  width: 10px; height: 10px; border-radius: 50%;
  background: var(--red); border: 1px solid rgba(0,0,0,0.25);
  transform: translateX(-50%);
}

.dk-note__body { cursor: text; max-height: 16em; overflow: hidden; }
.dk-note__body a { color: inherit; text-decoration: underline; }
.dk-note__body code { background: rgba(0,0,0,0.08); padding: 0 3px; border-radius: 2px; font-family: var(--font-mono); font-size: 0.92em; }
.dk-note__body p { margin: 0 0 var(--sp-2); }
.dk-note__edit {
  width: 100%; min-height: 8em; resize: vertical;
  background: transparent; color: var(--paper-ink);
  border: 1px dashed var(--paper-ink-soft); border-radius: 2px;
  font: inherit; padding: var(--sp-2);
}

/* Composer: a blank ghost paper waiting for ink. */
.dk-composer { background: transparent; border: 1.5px dashed var(--paper-edge); min-height: 150px; }
.dk-composer:hover { background: rgba(232, 217, 138, 0.06); }
.dk-composer__input {
  width: 100%; height: 100%; min-height: 110px; resize: none;
  background: transparent; border: none; outline: none;
  color: var(--ink); font: inherit;
}
.dk-composer__input::placeholder { color: var(--ink-4); }

/* ── Continuity band ────────────────────────────────────────────────────── */
.dk-continuity { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: var(--sp-6); }
.dk-continuity:empty { display: none; }
.dk-older {
  display: block; padding: var(--sp-2) var(--sp-3);
  color: var(--ink-4); font-size: var(--text-xs); text-decoration: none;
}
.dk-older:hover { color: var(--ink-2); }

.dk-empty { color: var(--ink-4); font-size: var(--text-sm); padding: var(--sp-4) 0; }

@media (max-width: 720px) {
  .dk-desk { padding: var(--sp-4); }
  .dk-board { grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); }
}
```

**Note:** `color-mix` requires Chrome 111+ — fine for a local-first dev tool. Verify `--border-soft`, `--ease`, `--font-mono`, `--text-*`, `--sp-*` exist in tokens.css (they do — used by shell.css).

- [ ] **Step 4: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/desk/note-card.js plugins/taskmaster/viewer/js/components/desk/composer.js plugins/taskmaster/viewer/css/screens/desk.css
git commit -m "feat(viewer): paper note card + composer components + desk styles"
```

---

### Task 8: Desk screen — board + continuity band; retire old dashboard

**Files:**
- Create: `plugins/taskmaster/viewer/js/screens/desk.js`
- Modify: `plugins/taskmaster/viewer/js/main.js:11`
- Delete: `plugins/taskmaster/viewer/js/screens/continuity.js`, `js/components/continuity/view-switcher.js`, `js/components/continuity/hero.js`, `js/components/continuity/resume-rail.js`
- Modify: `plugins/taskmaster/viewer/js/lib/continuity.js` (drop `groupByTime`, `groupByEntity`, `pickHero`)
- Modify: `plugins/taskmaster/viewer/css/screens/continuity.css` (delete `.co-hero*`, `.co-view-switcher*`, `.co-resume*`, `.co-time-view*`, `.co-entity-view*`, `.co-action-view*`, `.co-dash*` blocks; KEEP `.co-row*`, `.co-spine*`, `.co-decision*`, `.co-chip*`, `.co-xblock*`)

- [ ] **Step 1: desk.js**

```js
import { h } from '../util/h.js';
import { claimTopbar } from '../lib/topbar.js';
import { createAutoModeStrip } from '../components/auto-mode-strip.js';
import { createSpine } from '../components/continuity/spine.js';
import { createItemRow } from '../components/continuity/item-row.js';
import { createDecisionCard } from '../components/continuity/decision-card.js';
import { renderBlock } from '../lib/xml-render.js';
import { buildRails, sortNotes } from '../lib/desk.js';
import { createNoteCard } from '../components/desk/note-card.js';
import { createComposer } from '../components/desk/composer.js';

export const meta = { title: 'Dashboard', icon: '◧', sidebarKey: 'dashboard' };

const OLDER_TARGET = { resume: '#/sessions', review: '#/table', decide: '#/table', cleanup: '#/issues' };
const RAIL_LABEL = { resume: 'Resume', review: 'Review', decide: 'Decide', cleanup: 'Clean-up' };

export async function mount(root, { store, api }) {
  root.classList.add('dk-desk');

  const topbarSlot = claimTopbar();
  if (topbarSlot) {
    topbarSlot.appendChild(h('span', { class: 'dk-proj' }, store?.projectName?.() || ''));
  }

  const autoSlot = h('section', { class: 'dk-auto' });
  const strip = createAutoModeStrip({ store, api, mode: 'dashboard' });
  if (strip?.root) autoSlot.appendChild(strip.root);

  const boardEl = h('section', { class: 'dk-board', 'aria-label': 'Sticky notes' });
  const bandEl = h('section', { class: 'dk-continuity', 'aria-label': 'Continuity' });
  root.replaceChildren(autoSlot, boardEl, bandEl);

  let notes = [];
  let items = [];

  async function loadNotes() {
    try { notes = (await api.notes())?.notes || []; }
    catch (e) { console.error('[desk] notes fetch failed', e); notes = []; }
  }
  async function loadItems() {
    try { items = (await api.get('/api/continuity'))?.items || []; }
    catch (e) { console.error('[desk] continuity fetch failed', e); items = []; }
  }

  // ── Board ────────────────────────────────────────────────────────────────
  const composer = createComposer({
    onCreate: async (text) => {
      await api.createNote(text);
      await refreshBoard();
    },
  });

  function renderBoard() {
    boardEl.replaceChildren(composer.root);
    for (const note of sortNotes(notes)) {
      const card = createNoteCard({
        note,
        onPin: async (n) => { await api.updateNote(n.id, { pinned: !n.pinned }); await refreshBoard(); },
        onArchive: async (n) => { await api.archiveNote(n.id); await refreshBoard(); },
        onSave: async (n, text) => { await api.updateNote(n.id, { text }); await refreshBoard(); },
      });
      boardEl.appendChild(card.root);
    }
    if (notes.length === 0) {
      boardEl.appendChild(h('p', { class: 'dk-empty' }, 'Your desk is clear.'));
    }
  }

  async function refreshBoard() { await loadNotes(); renderBoard(); }

  // ── Continuity band ─────────────────────────────────────────────────────
  async function renderBand() {
    bandEl.replaceChildren();
    const rails = buildRails(items);
    for (const key of ['resume', 'review', 'decide', 'cleanup']) {
      const rail = rails[key];
      if (rail.items.length === 0 && rail.older === 0) continue;
      let railEl;
      if (key === 'decide' && rail.items.length > 0) {
        railEl = h('div', { class: 'co-spine' },
          h('div', { class: 'co-spine__head' },
            h('span', { class: 'co-spine__label' }, RAIL_LABEL[key]),
            h('span', { class: 'co-spine__count' }, String(rail.items.length))));
        for (const it of rail.items) {
          const decision = await fetchDecision(it.id);
          const card = createDecisionCard({
            decision: decision || { id: it.id, title: it.title, options: [] },
            onResolve: (idx) => resolveDecision(it.id, idx),
            onDrop: (id) => dropDecision(id),
          });
          if (card?.root) railEl.appendChild(card.root);
        }
      } else {
        railEl = createSpine({
          label: RAIL_LABEL[key],
          items: rail.items,
          empty: true,
          onItemClick: expandRow,
        }).root;
      }
      if (railEl && rail.older > 0) {
        railEl.appendChild(h('a', { class: 'dk-older', href: OLDER_TARGET[key] }, `+${rail.older} older`));
      }
      if (railEl) bandEl.appendChild(railEl);
    }
  }

  async function fetchDecision(id) {
    try { return await api.get(`/api/decisions/${encodeURIComponent(id)}`); }
    catch { return null; }
  }
  async function resolveDecision(id, optionIndex) {
    try {
      await api.post(`/api/decisions/${id}/resolve`, { resolved_with: optionIndex, rationale: '' });
      await loadItems(); await renderBand();
    } catch (e) { console.error('resolve decision failed', e); }
  }
  async function dropDecision(id) {
    try {
      await api.post(`/api/decisions/${id}/drop`, { reason: 'dropped via viewer' });
      await loadItems(); await renderBand();
    } catch (e) { console.error('drop decision failed', e); }
  }

  // Inline handover/decision body expansion — same contract as old screen.
  async function expandRow(item, controller) {
    if (!controller) return;
    if (controller.isExpanded()) { controller.clearExpanded(); return; }
    if (item.type !== 'handover' && item.type !== 'decision') return;
    controller.setLoading();
    let doc = null;
    try {
      doc = item.type === 'handover'
        ? await api.get(`/api/handover/${encodeURIComponent(item.id)}`)
        : await api.get(`/api/decisions/${encodeURIComponent(item.id)}`);
    } catch (e) { console.error('[desk] body fetch failed', e); }
    if (!controller.isExpanded()) return;
    if (!doc) { controller.setExpanded(h('p', { class: 'co-xblock__p' }, 'Failed to load body.')); return; }
    const text = item.type === 'decision'
      ? [doc.resolved_rationale || doc.dropped_reason || '', doc.body || ''].filter(Boolean).join('\n\n')
      : doc.body || '';
    controller.setExpanded(renderBlock(text || '(empty body)'));
  }

  await Promise.all([loadNotes(), loadItems()]);
  renderBoard();
  await renderBand();
  composer.focus();

  return async () => { strip?.destroy?.(); };
}
```

**Verify against real component APIs before wiring:** `createSpine` head markup class names (`co-spine__head` etc.) and `createDecisionCard`'s exact props — read `spine.js` and `decision-card.js` first and adapt the decide-rail markup to match (the decision-card was previously created by `hero.js`; copy its invocation shape from there BEFORE deleting hero.js). `claimTopbar` import path (`../lib/topbar.js`) is the one continuity.js used. `store.projectName?.()` — same call continuity.js used.

- [ ] **Step 2: Point the route at desk.js**

`plugins/taskmaster/viewer/js/main.js` line 11:

```js
registerScreen('/dashboard',  () => import('./screens/desk.js'));
```

- [ ] **Step 3: Delete retired modules + prune lib/continuity.js + continuity.css**

```bash
git rm plugins/taskmaster/viewer/js/screens/continuity.js plugins/taskmaster/viewer/js/components/continuity/view-switcher.js plugins/taskmaster/viewer/js/components/continuity/hero.js plugins/taskmaster/viewer/js/components/continuity/resume-rail.js
```

In `js/lib/continuity.js`: delete `groupByTime`, `groupByEntity`, `pickHero` exports (keep `groupByAction` ONLY if something still imports it — check `grep -rn "groupByAction" plugins/taskmaster/viewer/js`; desk.js uses `buildRails` instead, so if nothing imports it, delete the whole grouping trio and keep whatever else the file exports that is still referenced; if the file becomes empty, `git rm` it).

In `css/screens/continuity.css`: delete the rule blocks for `.co-dash`, `.co-view-switcher`, `.co-hero`, `.co-resume` (the Open/Recent split styles), `.co-action-view`, `.co-time-view`, `.co-entity-view`. Keep `.co-spine*`, `.co-row*`, `.co-decision*`, `.co-chip*`, `.co-xblock*` (used by desk band + other screens — verify with `grep -rn "co-decision\|co-spine\|co-row" plugins/taskmaster/viewer/js | grep -v continuity.css`).

Then verify no dangling imports:

```bash
grep -rn "view-switcher\|continuity/hero\|resume-rail\|screens/continuity" plugins/taskmaster/viewer/js plugins/taskmaster/viewer/index.html
```
Expected: no matches.

- [ ] **Step 4: Update stale test references (ISS-021/ISS-024 hygiene — only what this change breaks)**

```bash
grep -rln "Continuity\|continuity" plugins/taskmaster/viewer/tests/*.spec.js
```
For each hit that asserts the dashboard title/screen (e.g. `continuity-dashboard.spec.js`, `smoke.spec.js`): update title expectation `'Continuity'` → `'Dashboard'` and any `.co-dash`/hero/view-switcher selectors to the desk equivalents (`.dk-desk`, `.dk-board`). Do NOT attempt to fix unrelated pre-existing failures.

- [ ] **Step 5: Visual smoke**

Restart the test server (kill + relaunch the port-8771 command from Task 5 so Python picks up new routes), then `npx playwright-cli -s=qa goto http://127.0.0.1:8771/v3` and screenshot. Expected: composer ghost-paper + any existing notes as paper cards on top; below, up to four compact rails with at most 5 fresh cards each and "+N older" links; no full-width stale hero; zero console errors. Add a note through the composer in the driven session and confirm it appears as yellow paper ("you").

- [ ] **Step 6: Commit**

```bash
git add plugins/taskmaster/viewer/js/screens/desk.js plugins/taskmaster/viewer/js/main.js plugins/taskmaster/viewer/js/lib/continuity.js plugins/taskmaster/viewer/css/screens/continuity.css plugins/taskmaster/viewer/tests/
git commit -m "feat(viewer): Desk dashboard — sticky board + pruned continuity band; retire continuity screen"
```

(The `git rm`'d files are already staged by git rm.)

---

### Task 9: E2E specs for the Desk

**Files:**
- Create: `plugins/taskmaster/viewer/tests/desk.spec.js`

- [ ] **Step 1: Read an existing spec for harness conventions**

Read `plugins/taskmaster/viewer/tests/architecture-map.spec.js` (newest, hardened per recent commits) — copy its server/baseURL conventions, pageerror capture pattern, and mount-gate waits.

- [ ] **Step 2: Write the spec**

```js
import { test, expect } from '@playwright/test';

// Desk dashboard: sticky board + pruned continuity band.
// Server: VIEWER_BASE_URL (run_smoke.sh starts it on 8765).

const CREATED = [];

test.afterAll(async ({ request }) => {
  // Archive any notes this run created — keep the live .taskmaster clean.
  for (const id of CREATED) {
    await request.post(`/api/notes/${id}/archive`).catch(() => {});
  }
});

test.describe('desk dashboard', () => {
  test('mounts board + composer, no console errors', async ({ page }) => {
    const errors = [];
    page.on('pageerror', (e) => errors.push(e.message));
    page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
    await page.goto('/v3#/dashboard');
    await expect(page.locator('.dk-desk')).toBeVisible();
    await expect(page.locator('.dk-composer__input')).toBeVisible();
    expect(errors).toEqual([]);
  });

  test('marked is loaded locally (SRI fix)', async ({ page }) => {
    await page.goto('/v3#/dashboard');
    const hasMarked = await page.evaluate(() => typeof window.marked?.parse === 'function');
    expect(hasMarked).toBe(true);
  });

  test('composer creates a user paper note', async ({ page }) => {
    await page.goto('/v3#/dashboard');
    const text = `e2e desk note ${Date.now()}`;
    await page.locator('.dk-composer__input').fill(text);
    await page.locator('.dk-composer__input').press('Enter');
    const card = page.locator('.dk-note--user', { hasText: text });
    await expect(card).toBeVisible();
    const id = await card.getAttribute('data-note-id');
    CREATED.push(id);
    await expect(card.locator('.dk-note__who')).toHaveText('you');
  });

  test('pin reorders to front; archive removes', async ({ page, request }) => {
    const r = await request.post('/api/notes', { data: { text: `e2e pin target ${Date.now()}` } });
    const { id } = await r.json();
    CREATED.push(id);
    await page.goto('/v3#/dashboard');
    const card = page.locator(`[data-note-id="${id}"]`);
    await card.hover();
    await card.locator('.dk-note__pin').click();
    await expect(page.locator('.dk-note').nth(0)).toHaveAttribute('data-note-id', id);
    await card.hover();
    await card.locator('.dk-note__archive').click();
    await expect(page.locator(`[data-note-id="${id}"]`)).toHaveCount(0);
  });

  test('continuity rails cap at 5 with older link', async ({ page }) => {
    await page.goto('/v3#/dashboard');
    const rails = page.locator('.dk-continuity .co-spine');
    const n = await rails.count();
    for (let i = 0; i < n; i++) {
      const cards = rails.nth(i).locator('.co-row');
      expect(await cards.count()).toBeLessThanOrEqual(5);
    }
  });
});
```

**Adapt:** `.dk-note--user` class name must match note-card.js (`dk-note--user`); pinned reorder assertion — the composer occupies position 0 in `.dk-board` but `.dk-note` selector excludes it only if composer lacks `.dk-note` class; composer HAS `dk-note dk-composer` classes, so use `.dk-note:not(.dk-composer)` in the nth(0) assertion. Fix that in the spec: `page.locator('.dk-note:not(.dk-composer)').nth(0)`.

- [ ] **Step 3: Run the e2e suite**

From `plugins/taskmaster/viewer/tests/`: `bash run_smoke.sh` — or start the 8765 server manually and `VIEWER_BASE_URL=http://127.0.0.1:8765 npx playwright test desk.spec.js` from the tests dir.
Expected: desk.spec.js green. Pre-existing red specs (ISS-024) are out of scope — desk.spec.js and any spec updated in Task 8 must pass.

- [ ] **Step 4: Commit**

```bash
git add plugins/taskmaster/viewer/tests/desk.spec.js
git commit -m "test(viewer): e2e desk dashboard — composer, paper notes, pin/archive, rail caps"
```

---

### Task 10: Skill integration (start-session / end-session)

**Files:**
- Modify: `plugins/taskmaster/skills/start-session/SKILL.md`
- Modify: `plugins/taskmaster/skills/end-session/SKILL.md`

- [ ] **Step 1: REQUIRED — invoke `plugin-dev:skill-development` before editing** (frontmatter/trigger rules live there).

- [ ] **Step 2: start-session — add "Your desk" section**

Read the skill first. After the dashboard/last-session summary step, add a step:

```markdown
### Your desk (sticky notes)

Call `backlog_note_list()`. If any notes exist, render them under a **Your desk** heading — pinned first, one line each (`author · age · first line`). These are the user's situational notes-to-self: treat them as orientation context for "what was on my mind", alongside (not replacing) the last handover. Never archive, edit, or act on a note without the user asking.
```

Match the surrounding step style/numbering of the actual file.

- [ ] **Step 3: end-session — at-most-one-note rule**

Add to the end-session flow (near handover writing):

```markdown
### Loose thoughts → desk note (optional, max one)

If the session leaves a genuinely situational thought that fits no entity (not a task, idea, issue, or the handover's next_action) — e.g. "the e2e flake smells like port contention, look again if it recurs" — write at most ONE consolidated note via `backlog_note_create(text=...)`. Default is to write none. Never duplicate handover content into a note; the note is for what would otherwise be lost.
```

- [ ] **Step 4: Lint check**

Several skills have lint tests (`tests/test_*_skill_lint.py`). Run: `python -m pytest plugins/taskmaster/tests/ -k "skill_lint" -q`
Expected: all pass (budget helpers may enforce token limits — if a lint fails on length, trim the added sections).

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/skills/start-session/SKILL.md plugins/taskmaster/skills/end-session/SKILL.md
git commit -m "feat(taskmaster): surface sticky notes in start-session; end-session may leave one note"
```

---

### Task 11: Version bump + changelog + full verification

**Files:**
- Modify: `plugins/taskmaster/.claude-plugin/plugin.json` (`"version": "3.15.0"`)
- Modify: `.claude-plugin/marketplace.json` (taskmaster entry → `3.15.0`)
- Modify: `plugins/taskmaster/CHANGELOG.md`

- [ ] **Step 1: Bump versions** (both files must agree).

- [ ] **Step 2: CHANGELOG entry**

```markdown
## 3.15.0

Dashboard rebuilt as **The Desk** — sticky notes first.

- **Sticky notes entity**: `.taskmaster/notes/NOTE-NNN.md` — freeform, situational notes-to-self. New MCP tools: `backlog_note_create`, `backlog_note_list`, `backlog_note_get`, `backlog_note_update`, `backlog_note_archive`. New HTTP API: `/api/notes` (+ update/archive). Viewer-created notes are author `user`; MCP-created are `claude` — rendered as visually distinct paper (yellow vs blue).
- **Desk dashboard** (`#/dashboard`): paper-note board (quick-add composer, pin, inline edit, archive) above a pruned continuity band (4 rails, max 5 fresh cards each, >30d items collapse into "+N older" links). Time/Entity views and the stale full-width hero are retired.
- **start-session** surfaces the desk; **end-session** may leave at most one consolidated claude note.
- **Fixes**: marked.js vendored locally (CDN SRI hash mismatch silently blocked all markdown rendering); sidebar version chip stuck at "v?" (identity replay); clipped "Taskmaster" brand; favicon 404; removed orphaned bento dashboard code (board-surface.js, dashboard.css).
```

- [ ] **Step 3: Version-sync check**

Run: `python scripts/check_plugin_version_bump.py --base origin/master`
Expected: exit 0. (Base may need to be `master` if origin/master is stale locally — match what the script expects.)

- [ ] **Step 4: Full test sweep**

```bash
python -m pytest plugins/taskmaster/tests/ -q
node --test "plugins/taskmaster/viewer/tests/unit/*.test.js"
cd plugins/taskmaster/viewer/tests && bash run_smoke.sh
```
Expected: pytest green; unit green except pre-existing ISS-021 failures (none new); e2e — desk.spec.js + smoke green, pre-existing ISS-024 failures unchanged (record counts before/after Task 8 to prove no regression).

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/.claude-plugin/plugin.json .claude-plugin/marketplace.json plugins/taskmaster/CHANGELOG.md
git commit -m "chore(taskmaster): bump to 3.15.0 — Desk dashboard + sticky notes"
```

- [ ] **Step 6: Final visual review**

Serve, open `#/dashboard`, screenshot full page; verify against spec §2 (paper contrast, tilt, fold, pin dot, band pruning, no left rails / no hover motion / no shadows). Fix nits, amend nothing — new commits.

---

## Execution notes

- Tasks 1→3 are strictly sequential (entity → tools → API). Task 4 and 5 are independent of 1-3 and of each other. Task 6 depends on 3 (api methods hit real endpoints only at e2e time — unit tests don't need the server, so 6 can run parallel to 1-3 in a pinch, but keep it simple: sequential). 7 depends on 6; 8 depends on 4-7; 9 depends on 8; 10 depends on 2; 11 last.
- The repo has stray uncommitted dirs (`plugins/taskmaster/handovers/`, `issues/`, etc. — test pollution) and screenshots at repo root. NEVER stage them.
- Do not push. Merge decision belongs to the user.
