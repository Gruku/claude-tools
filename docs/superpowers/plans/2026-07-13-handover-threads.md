# Handover Threads Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** First-class handover threads: stable resume token, `backlog_thread_*` MCP surface, thread-lane sessions view (board + diary), plus two viewer rot fixes.

**Architecture:** Threads are a rebuildable registry (`threads:` in backlog.yaml) derived from a new `thread:` frontmatter field on handover files — frontmatter is the source of truth; user-set thread statuses live in a small `thread_meta:` override map that auto-expires when a newer handover lands. The viewer's synthesized 30-min-gap sessions are replaced by one lane per thread.

**Tech Stack:** Python 3 (FastMCP server + core lib), vanilla-JS viewer, pytest, @playwright/test (route-mocked only).

**Repo:** ALL code changes land in `C:\Users\gruku\Files\Claude\taskmaster` (source of truth), on a feature branch `handover-threads` off `master`. Do NOT edit the `plugins/taskmaster` submodule in claude-tools.

**Spec:** `C:\Users\gruku\Files\Claude\claude-tools\docs\superpowers\specs\2026-07-13-handover-threads-design.md`

## Global Constraints

- Thread statuses: exactly `("open", "parked", "closed")`. Handover statuses stay `("open", "closed", "superseded")`.
- Thread names are slugs: `slugify(name, max_len=40)` — same slugify as handover ids.
- The registry must be 100% rebuildable from handover frontmatter (`backlog_handover_resync` proves it) — team-collab state-branch merges depend on this.
- No SessionStart-hook injection of threads/board — resume surfaces are on-demand only.
- Viewer design rules: no colored left rails, no motion on hover, no box-shadows (surface stepping only).
- Every `backlog_handover_create` / end-session confirmation ends with the copy-ready line: `Resume: <thread> — <next_action>`.
- Run tests with `python -m pytest tests/<file> -v` from the taskmaster repo root.
- Commit after each task; group code + tests in one commit.

---

### Task 1: Core `thread` field on handovers

**Files:**
- Modify: `taskmaster/taskmaster_v3.py` (write_handover ~1357-1426, `_HANDOVER_INDEX_FIELDS` ~1849)
- Test: `tests/test_threads.py` (new)

**Interfaces:**
- Produces: `normalize_thread_name(name: str) -> str`; `write_handover(..., thread: str | None = None)` writing `thread` frontmatter; `thread` included in backlog.yaml handover index entries.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_threads.py`:

```python
"""Thread entity: frontmatter field, registry rebuild, lifecycle, resolution."""
import sys
from pathlib import Path
import yaml

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

from taskmaster.taskmaster_v3 import (
    normalize_thread_name,
    read_handover,
    write_handover,
    _handover_index_entry,
)


def _setup(tmp_path):
    bp = tmp_path / "backlog.yaml"
    bp.write_text(yaml.safe_dump({"meta": {}, "epics": []}))
    (tmp_path / "handovers").mkdir()
    return bp


def test_normalize_thread_name():
    assert normalize_thread_name("Team Relayout!") == "team-relayout"
    assert normalize_thread_name("") == "untitled"
    assert normalize_thread_name("x" * 100) == "x" * 40


def test_write_handover_stamps_thread(tmp_path):
    bp = _setup(tmp_path)
    hid, _ = write_handover(
        bp, tldr="relayout M1 done", thread="Team Relayout", task_ids=["T-1"],
    )
    fm, _ = read_handover(bp, hid)
    assert fm["thread"] == "team-relayout"


def test_write_handover_without_thread_omits_field(tmp_path):
    bp = _setup(tmp_path)
    hid, _ = write_handover(bp, tldr="explored stuff")
    fm, _ = read_handover(bp, hid)
    assert "thread" not in fm


def test_index_entry_carries_thread():
    entry = _handover_index_entry({"id": "x", "tldr": "t", "thread": "team-relayout"})
    assert entry["thread"] == "team-relayout"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_threads.py -v`
Expected: FAIL — `ImportError: cannot import name 'normalize_thread_name'`

- [ ] **Step 3: Implement**

In `taskmaster/taskmaster_v3.py`, directly below `slugify` (~line 1341), add:

```python
def normalize_thread_name(name: str) -> str:
    """Canonical slug form for thread names — same rules as handover ids."""
    return slugify(name, max_len=40)
```

In `write_handover`: add `thread: str | None = None,` to the signature (after `session_kind`). After the `session_kind` validation block, add:

```python
    thread = normalize_thread_name(thread) if thread and thread.strip() else None
```

In the `fm` dict, after the `"session_kind": session_kind,` line add nothing inline; instead, after `fm["status_user_set"] = False`, add:

```python
    if thread:
        fm["thread"] = thread
```

Change `_HANDOVER_INDEX_FIELDS` to:

```python
_HANDOVER_INDEX_FIELDS = (
    "id", "date", "created", "tldr", "next_action",
    "task_ids", "session_kind", "status", "flag_reason", "thread",
)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_threads.py -v`
Expected: 4 PASS

- [ ] **Step 5: Run the full suite to catch regressions**

Run: `python -m pytest tests/ -x -q`
Expected: green (same pass count as on master; no new failures)

- [ ] **Step 6: Commit**

```bash
git add taskmaster/taskmaster_v3.py tests/test_threads.py
git commit -m "feat(threads): thread frontmatter field on handovers + index entry"
```

---

### Task 2: Thread registry — rebuild, lifecycle, overrides

**Files:**
- Modify: `taskmaster/taskmaster_v3.py` (below `sync_handover_index`, ~line 1910)
- Test: `tests/test_threads.py`

**Interfaces:**
- Consumes: `list_handover_ids`, `read_handover`, `normalize_thread_name` (Task 1).
- Produces: `THREAD_STATUSES = ("open", "parked", "closed")`; `sync_thread_registry(backlog_data: dict, backlog_path: Path) -> dict` (populates `backlog_data["threads"]` and prunes `backlog_data["thread_meta"]`); `update_thread_status(backlog_data, backlog_path, *, name, status, reason="") -> dict`. `sync_handover_index` calls `sync_thread_registry` before returning.
- Registry entry shape (dict keyed by thread name): `{status, handover_ids[asc], task_ids[], created, last_touched, tldr, next_action, branch}` — tldr/next_action/branch come from the newest member.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_threads.py`:

```python
from taskmaster.taskmaster_v3 import (
    THREAD_STATUSES,
    sync_handover_index,
    sync_thread_registry,
    update_handover_status,
    update_thread_status,
)


def _write3(bp):
    """Three handovers: two in thread A (older/newer), one in thread B.

    NOTE: written in the order a1, b1, a2 — registry recency (`last_touched`)
    keys off the real `created` timestamp, so a2 must be CREATED last for
    thread-a to be the most recently touched thread.
    """
    a1, _ = write_handover(bp, tldr="A first", thread="thread-a",
                           task_ids=["T-1"], when="2026-07-10")
    b1, _ = write_handover(bp, tldr="B only", thread="thread-b",
                           when="2026-07-11")
    a2, _ = write_handover(bp, tldr="A second", thread="thread-a",
                           task_ids=["T-2"], next_action="do T-2 tests",
                           branch="feat/a", when="2026-07-12")
    return a1, a2, b1


def test_registry_rebuild_groups_and_orders(tmp_path):
    bp = _setup(tmp_path)
    a1, a2, b1 = _write3(bp)
    data = {"meta": {}, "epics": []}
    sync_thread_registry(data, bp)
    threads = data["threads"]
    assert set(threads) == {"thread-a", "thread-b"}
    ta = threads["thread-a"]
    assert ta["handover_ids"] == [a1, a2]          # chronological
    assert ta["task_ids"] == ["T-1", "T-2"]
    assert ta["tldr"] == "A second"                # newest member wins
    assert ta["next_action"] == "do T-2 tests"
    assert ta["branch"] == "feat/a"
    assert ta["status"] == "open"


def test_registry_derived_closed_when_all_members_closed(tmp_path):
    bp = _setup(tmp_path)
    a1, a2, b1 = _write3(bp)
    for hid in (a1, a2):
        update_handover_status(bp, handover_id=hid, status="closed")
    data = {"meta": {}, "epics": []}
    sync_thread_registry(data, bp)
    assert data["threads"]["thread-a"]["status"] == "closed"
    assert data["threads"]["thread-b"]["status"] == "open"


def test_thread_status_override_and_auto_reopen(tmp_path):
    bp = _setup(tmp_path)
    _write3(bp)
    data = {"meta": {}, "epics": []}
    sync_thread_registry(data, bp)

    update_thread_status(data, bp, name="thread-a", status="parked")
    assert data["threads"]["thread-a"]["status"] == "parked"
    # Override survives a rebuild (no newer handover).
    sync_thread_registry(data, bp)
    assert data["threads"]["thread-a"]["status"] == "parked"

    # A newer handover auto-reopens: override pruned on rebuild.
    write_handover(bp, tldr="A resumed", thread="thread-a", when="2026-07-13")
    sync_thread_registry(data, bp)
    assert data["threads"]["thread-a"]["status"] == "open"
    assert "thread-a" not in (data.get("thread_meta") or {})


def test_thread_status_validation(tmp_path):
    bp = _setup(tmp_path)
    _write3(bp)
    data = {"meta": {}, "epics": []}
    sync_thread_registry(data, bp)
    import pytest
    with pytest.raises(ValueError):
        update_thread_status(data, bp, name="thread-a", status="bogus")
    with pytest.raises(KeyError):
        update_thread_status(data, bp, name="no-such-thread", status="parked")


def test_sync_handover_index_populates_threads(tmp_path):
    bp = _setup(tmp_path)
    _write3(bp)
    data = {"meta": {}, "epics": []}
    sync_handover_index(data, bp)
    assert "thread-a" in data["threads"]
    # Round-trips through YAML (registry must be plain data).
    yaml.safe_dump(data)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_threads.py -v`
Expected: new tests FAIL with ImportError on `THREAD_STATUSES`

- [ ] **Step 3: Implement**

In `taskmaster/taskmaster_v3.py`, directly after `sync_handover_index`, add:

```python
# ── Threads ─────────────────────────────────────────────────────
# A thread is a named chain of handovers — the stable resume token.
# `threads:` in backlog.yaml is a rebuildable projection of handover
# frontmatter; `thread_meta:` holds user-set status overrides that expire
# when a newer handover lands (auto-reopen). See
# specs/2026-07-13-handover-threads-design.md.

THREAD_STATUSES = ("open", "parked", "closed")


def sync_thread_registry(
    backlog_data: dict[str, Any],
    backlog_path: Path,
) -> dict[str, Any]:
    """Rebuild backlog_data['threads'] from non-archived handover files.

    Derived status: open if any member handover is open, else closed.
    A `thread_meta` override (parked/closed/open) is honoured only while no
    member handover is newer than the override's set_at; stale overrides and
    overrides for vanished threads are pruned. Mutates in place, returns
    backlog_data for chaining.
    """
    ids = list_handover_ids(backlog_path)  # newest-first
    threads: dict[str, dict[str, Any]] = {}
    for hid in reversed(ids):              # oldest-first → chronological chains
        try:
            fm, _ = read_handover(backlog_path, hid)
        except (OSError, ValueError):
            continue
        name = fm.get("thread")
        if not name:
            continue
        t = threads.setdefault(name, {
            "status": "closed",
            "handover_ids": [],
            "task_ids": [],
            "created": fm.get("created") or fm.get("date") or "",
            "last_touched": "",
            "tldr": "",
            "next_action": "",
            "branch": "",
            "_any_open": False,
        })
        t["handover_ids"].append(hid)
        for tid in fm.get("task_ids") or []:
            if tid not in t["task_ids"]:
                t["task_ids"].append(tid)
        touched = fm.get("created") or fm.get("date") or ""
        if touched >= t["last_touched"]:
            t["last_touched"] = touched
            t["tldr"] = fm.get("tldr", "")
            t["next_action"] = fm.get("next_action", "")
            if fm.get("branch"):
                t["branch"] = fm["branch"]
        if fm.get("status", "open") == "open":
            t["_any_open"] = True

    meta = dict(backlog_data.get("thread_meta") or {})
    for name, t in threads.items():
        derived = "open" if t.pop("_any_open") else "closed"
        override = meta.get(name)
        if override and str(override.get("set_at", "")) >= t["last_touched"]:
            t["status"] = override.get("status", derived)
        else:
            meta.pop(name, None)  # stale/absent — newer handover reopens
            t["status"] = derived
    meta = {k: v for k, v in meta.items() if k in threads}

    backlog_data["threads"] = threads
    backlog_data["thread_meta"] = meta
    return backlog_data


def update_thread_status(
    backlog_data: dict[str, Any],
    backlog_path: Path,
    *,
    name: str,
    status: str,
    reason: str = "",
) -> dict[str, Any]:
    """User-driven thread status override (parked/closed/open).

    Recorded in thread_meta with a set_at timestamp; a newer handover in the
    thread invalidates it (auto-reopen). Raises ValueError on bad enum,
    KeyError if the thread doesn't exist.
    """
    if status not in THREAD_STATUSES:
        raise ValueError(f"status must be one of {THREAD_STATUSES}, got {status!r}")
    name = normalize_thread_name(name)
    threads = backlog_data.get("threads") or {}
    if name not in threads:
        raise KeyError(name)
    meta = dict(backlog_data.get("thread_meta") or {})
    entry: dict[str, Any] = {
        "status": status,
        "set_at": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
    }
    if reason:
        entry["reason"] = reason
    meta[name] = entry
    backlog_data["thread_meta"] = meta
    threads[name]["status"] = status
    return backlog_data
```

In `sync_handover_index`, before `return backlog_data`, add:

```python
    sync_thread_registry(backlog_data, backlog_path)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_threads.py -v`
Expected: all PASS

- [ ] **Step 5: Full suite**

Run: `python -m pytest tests/ -x -q`
Expected: green. If any existing test asserts the exact key set of backlog.yaml after `sync_handover_index`, update it to include `threads`/`thread_meta`.

- [ ] **Step 6: Commit**

```bash
git add taskmaster/taskmaster_v3.py tests/test_threads.py
git commit -m "feat(threads): rebuildable thread registry with lifecycle overrides"
```

---

### Task 3: Thread resolution + thread-lane sessions (server side)

**Files:**
- Modify: `taskmaster/taskmaster_v3.py` (`list_sessions` ~3663-3765, `get_session_detail` ~3786-3801; add `resolve_thread` + `list_threads` near them)
- Test: `tests/test_threads.py`

**Interfaces:**
- Consumes: registry from Task 2; `_resolve_artifact_root()`, `_handover_time`, `_load_handover_full`, `HANDOVER_KIND_TO_VIEWER_KIND` (existing).
- Produces:
  - `resolve_thread(backlog_data, backlog_path, ref) -> tuple[str, str]` — `(thread_name, newest_handover_id)`; `ref` may be a thread name OR a handover id (live or archived; a threadless handover returns `("", ref)`); raises `KeyError` when unresolvable.
  - `list_threads(backlog_data) -> list[dict]` — board rows `{name, status, tldr, next_action, task_ids, branch, last_touched, staleness_days}`, open first then parked, newest-touched first.
  - `list_sessions()` REWRITTEN: one row per thread (CWD-based, reads files directly, no backlog_data): `{id: <thread name>, kind: "thread", status, start, end, duration, time_resolution, handover_ids[asc], handovers[], task_ids, tldr, next_action}` — newest-end first. Legacy threadless handovers each form a solo row with `id = <handover id>`. `SES-NNNN` ids and `parallel_with` are GONE.
  - `get_session_detail(session_id)` — unchanged shape, matches the new row ids.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_threads.py`:

```python
from taskmaster.taskmaster_v3 import (
    archive_handover,
    list_sessions,
    list_threads,
    resolve_thread,
)


def test_resolve_thread_by_name_and_by_handover_id(tmp_path):
    bp = _setup(tmp_path)
    a1, a2, b1 = _write3(bp)
    data = {"meta": {}, "epics": []}
    sync_thread_registry(data, bp)

    assert resolve_thread(data, bp, "thread-a") == ("thread-a", a2)
    assert resolve_thread(data, bp, "Thread A") == ("thread-a", a2)  # normalized
    # A stale dated slug still lands on the thread's NEWEST handover.
    assert resolve_thread(data, bp, a1) == ("thread-a", a2)
    import pytest
    with pytest.raises(KeyError):
        resolve_thread(data, bp, "nope-never")


def test_resolve_thread_archived_handover_id(tmp_path):
    bp = _setup(tmp_path)
    a1, a2, b1 = _write3(bp)
    data = {"meta": {}, "epics": []}
    sync_thread_registry(data, bp)
    archive_handover(bp, a1)
    assert resolve_thread(data, bp, a1) == ("thread-a", a2)


def test_list_threads_board_rows(tmp_path):
    bp = _setup(tmp_path)
    _write3(bp)
    data = {"meta": {}, "epics": []}
    sync_thread_registry(data, bp)
    rows = list_threads(data)
    assert [r["name"] for r in rows] == ["thread-a", "thread-b"]  # newest-touched first
    assert rows[0]["next_action"] == "do T-2 tests"
    assert "staleness_days" in rows[0]


def test_list_sessions_one_lane_per_thread(tmp_path, monkeypatch):
    bp = _setup(tmp_path)
    a1, a2, b1 = _write3(bp)
    solo, _ = write_handover(bp, tldr="threadless legacy", when="2026-07-09")
    monkeypatch.chdir(tmp_path)
    rows = list_sessions()
    by_id = {r["id"]: r for r in rows}
    assert set(by_id) == {"thread-a", "thread-b", solo}
    assert by_id["thread-a"]["handover_ids"] == [a1, a2]
    assert by_id["thread-a"]["kind"] == "thread"
    assert by_id["thread-a"]["status"] == "open"
    assert all("parallel_with" not in r for r in rows)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_threads.py -v`
Expected: ImportError on `list_threads` / `resolve_thread`; sessions test fails on old shape

- [ ] **Step 3: Implement**

Add after `update_thread_status` in `taskmaster/taskmaster_v3.py`:

```python
def resolve_thread(
    backlog_data: dict[str, Any],
    backlog_path: Path,
    ref: str,
) -> tuple[str, str]:
    """Resolve a resume token to (thread_name, newest_handover_id).

    `ref` may be a thread name (normalized) or a handover id — live or
    archived — whose `thread` field routes to the thread's newest handover.
    A threadless handover id resolves to ("", ref). Raises KeyError when
    nothing matches.
    """
    threads = backlog_data.get("threads") or {}
    name = normalize_thread_name(ref)
    if name in threads and threads[name]["handover_ids"]:
        return name, threads[name]["handover_ids"][-1]

    fm: dict[str, Any] | None = None
    p = handover_path(backlog_path, ref)
    if p.exists():
        fm, _ = read_task_file(p)
    else:
        archive_root = handover_dir(backlog_path) / "_archive"
        if archive_root.exists():
            hits = list(archive_root.rglob(f"{ref}.md"))
            if hits:
                fm, _ = read_task_file(hits[0])
    if fm is None:
        raise KeyError(ref)
    tname = fm.get("thread") or ""
    if tname and tname in threads and threads[tname]["handover_ids"]:
        return tname, threads[tname]["handover_ids"][-1]
    return tname, str(fm.get("id") or ref)


def list_threads(backlog_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Board rows from the registry — open first, then parked, then closed;
    newest-touched first within each status. staleness_days is whole days
    since last_touched (0 when unparseable)."""
    rows: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)
    for name, t in (backlog_data.get("threads") or {}).items():
        try:
            staleness = max(0, (now - _parse_iso8601(t["last_touched"])).days)
        except (ValueError, KeyError, TypeError):
            staleness = 0
        rows.append({
            "name": name,
            "status": t.get("status", "open"),
            "tldr": t.get("tldr", ""),
            "next_action": t.get("next_action", ""),
            "task_ids": list(t.get("task_ids") or []),
            "branch": t.get("branch", ""),
            "last_touched": t.get("last_touched", ""),
            "staleness_days": staleness,
        })
    order = {"open": 0, "parked": 1, "closed": 2}
    rows.sort(key=lambda r: (order.get(r["status"], 3), r["last_touched"]))
    # newest-touched first within status buckets:
    rows.sort(key=lambda r: r["last_touched"], reverse=True)
    rows.sort(key=lambda r: order.get(r["status"], 3))
    return rows
```

REPLACE the body of `list_sessions()` (keep the name; delete the gap-clustering algorithm and `parallel_with` block entirely):

```python
def list_sessions() -> list[dict]:
    """One diary lane per thread, synthesised from on-disk handover files.

    Groups handovers by their `thread` frontmatter; threadless (legacy)
    handovers each form a solo lane keyed by their own id. Rows are
    session-shaped for the viewer timeline: overlapping lanes render as
    parallel columns client-side. Newest end-time first.
    """
    handovers_dir = _resolve_artifact_root() / "handovers"
    if not handovers_dir.exists():
        return []
    raw: list[dict] = []
    for p in sorted(handovers_dir.glob("*.md")):
        try:
            text = p.read_text(encoding="utf-8")
            m = _MD_FRONTMATTER_RE.match(text)
            if not m:
                continue
            fm = yaml.safe_load(m.group(1)) or {}
            if "id" not in fm or ("date" not in fm and "created" not in fm):
                continue
            raw.append(fm)
        except Exception:
            continue
    raw.sort(key=lambda h: _handover_time(h))

    lanes: dict[str, list[dict]] = {}
    for h in raw:
        key = h.get("thread") or h["id"]
        lanes.setdefault(key, []).append(h)

    sessions: list[dict] = []
    for key, group in lanes.items():
        start = _handover_time(group[0])
        end = _handover_time(group[-1])
        tids: list[str] = []
        for h in group:
            for t in (h.get("task_ids") or []):
                if t not in tids:
                    tids.append(t)
        time_resolution = "full" if any(h.get("created") for h in group) else "date-only"
        any_open = any(h.get("status", "open") == "open" for h in group)
        newest = group[-1]
        sessions.append({
            "id": key,
            "kind": "thread",
            "status": "open" if any_open else "closed",
            "start": start.isoformat(),
            "end": end.isoformat(),
            "duration": int((end - start).total_seconds()),
            "time_resolution": time_resolution,
            "handover_ids": [h["id"] for h in group],
            "handovers": [
                {
                    "id": h["id"],
                    "status": h.get("status", "open"),
                    "viewer_kind": HANDOVER_KIND_TO_VIEWER_KIND.get(h.get("session_kind"), "standalone"),
                    "tldr": h.get("tldr", ""),
                }
                for h in group
            ],
            "task_ids": tids,
            "tldr": newest.get("tldr", ""),
            "next_action": newest.get("next_action", ""),
        })

    sessions.sort(key=lambda s: s["end"], reverse=True)
    return sessions
```

`get_session_detail` needs no code change (it matches rows by `id`), but verify it after the rewrite.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_threads.py -v`
Expected: all PASS

- [ ] **Step 5: Full suite — expect existing session tests to need updating**

Run: `python -m pytest tests/ -q`
Any test asserting `SES-` ids, `parallel_with`, or gap-clustering behavior in `list_sessions` output is asserting the removed design — rewrite those assertions to the new thread-lane shape (grep `tests/` for `SES-` and `parallel_with`).

- [ ] **Step 6: Commit**

```bash
git add taskmaster/taskmaster_v3.py tests/
git commit -m "feat(threads): resolve_thread + list_threads; sessions become thread lanes"
```

---

### Task 4: Legacy backfill — stamp `thread:` onto old handovers

**Files:**
- Modify: `taskmaster/taskmaster_v3.py` (after `resolve_thread`)
- Test: `tests/test_threads.py`

**Interfaces:**
- Consumes: `list_handover_ids`, `read_handover`, `write_task_file`, `normalize_thread_name`.
- Produces: `backfill_threads(backlog_path, backlog_data=None) -> dict` returning `{"stamped": [ids], "groups": N}`. Idempotent. Grouping: union-find over supersession links + shared task_ids. Group name precedence: epic id containing a member task → first task id → newest member's id minus the `YYYY-MM-DD-` prefix.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_threads.py`:

```python
from taskmaster.taskmaster_v3 import apply_supersession, backfill_threads


def test_backfill_groups_by_supersession_and_tasks(tmp_path):
    bp = _setup(tmp_path)
    # Chain: h1 superseded by h2 (no shared tasks) → one thread.
    h1, _ = write_handover(bp, tldr="old milestone", when="2026-07-01")
    h2, _ = write_handover(bp, tldr="new milestone", when="2026-07-02",
                           supersedes=None)
    apply_supersession(bp, old_id=h1, new_id=h2)
    # Shared task: h3 + h4 both on T-9 → one thread named T-9.
    h3, _ = write_handover(bp, tldr="T9 part one", task_ids=["T-9"], when="2026-07-03")
    h4, _ = write_handover(bp, tldr="T9 part two", task_ids=["T-9"], when="2026-07-04")
    # Singleton, no tasks → thread named from its own id slug.
    h5, _ = write_handover(bp, tldr="loose exploration", when="2026-07-05")

    result = backfill_threads(bp)
    assert result["groups"] == 3
    fm1, _ = read_handover(bp, h1)
    fm2, _ = read_handover(bp, h2)
    assert fm1["thread"] == fm2["thread"]
    fm3, _ = read_handover(bp, h3)
    fm4, _ = read_handover(bp, h4)
    assert fm3["thread"] == fm4["thread"] == "t-9"
    fm5, _ = read_handover(bp, h5)
    assert fm5["thread"] == "loose-exploration"

    # Idempotent: second run stamps nothing.
    assert backfill_threads(bp)["stamped"] == []


def test_backfill_prefers_epic_name(tmp_path):
    bp = _setup(tmp_path)
    h, _ = write_handover(bp, tldr="epic work", task_ids=["T-9"], when="2026-07-01")
    data = {"meta": {}, "epics": [
        {"id": "team-relayout", "name": "Team Relayout",
         "tasks": [{"id": "T-9", "title": "x", "status": "todo"}]},
    ]}
    backfill_threads(bp, backlog_data=data)
    fm, _ = read_handover(bp, h)
    assert fm["thread"] == "team-relayout"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_threads.py -v`
Expected: ImportError on `backfill_threads`

- [ ] **Step 3: Implement**

```python
def backfill_threads(
    backlog_path: Path,
    backlog_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Stamp `thread:` frontmatter onto non-archived handovers that lack it.

    Union-find grouping: an edge joins two handovers when one supersedes the
    other, or when they share a task id. Name precedence per group: epic id
    containing any member task → first member task id → newest member's id
    with the date prefix stripped. Idempotent; files already carrying
    `thread` are untouched. Returns {"stamped": [...], "groups": N}.
    """
    ids = list_handover_ids(backlog_path)
    fms: dict[str, dict[str, Any]] = {}
    bodies: dict[str, str] = {}
    for hid in ids:
        try:
            fm, body = read_handover(backlog_path, hid)
        except (OSError, ValueError):
            continue
        if fm.get("thread"):
            continue
        fms[hid] = fm
        bodies[hid] = body
    if not fms:
        return {"stamped": [], "groups": 0}

    parent: dict[str, str] = {hid: hid for hid in fms}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    by_task: dict[str, list[str]] = {}
    for hid, fm in fms.items():
        for link_key in ("supersedes", "superseded_by"):
            other = fm.get(link_key)
            if other in fms:
                union(hid, other)
        for tid in fm.get("task_ids") or []:
            by_task.setdefault(tid, []).append(hid)
    for members in by_task.values():
        for other in members[1:]:
            union(members[0], other)

    groups: dict[str, list[str]] = {}
    for hid in fms:
        groups.setdefault(find(hid), []).append(hid)

    task_to_epic: dict[str, str] = {}
    for epic in (backlog_data or {}).get("epics") or []:
        for t in epic.get("tasks") or []:
            if t.get("id") and epic.get("id"):
                task_to_epic[t["id"]] = epic["id"]

    stamped: list[str] = []
    for members in groups.values():
        members.sort(key=lambda h: str(fms[h].get("created") or fms[h].get("date") or ""))
        newest = members[-1]
        all_tasks: list[str] = []
        for hid in members:
            for tid in fms[hid].get("task_ids") or []:
                if tid not in all_tasks:
                    all_tasks.append(tid)
        epic_ids = [task_to_epic[t] for t in all_tasks if t in task_to_epic]
        if epic_ids:
            name = normalize_thread_name(epic_ids[0])
        elif all_tasks:
            name = normalize_thread_name(all_tasks[0])
        else:
            name = normalize_thread_name(re.sub(r"^\d{4}-\d{2}-\d{2}-", "", newest))
        for hid in members:
            fms[hid]["thread"] = name
            write_task_file(handover_path(backlog_path, hid), fms[hid], bodies[hid])
            stamped.append(hid)

    return {"stamped": stamped, "groups": len(groups)}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_threads.py -v` → all PASS

- [ ] **Step 5: Full suite + commit**

Run: `python -m pytest tests/ -x -q` → green

```bash
git add taskmaster/taskmaster_v3.py tests/test_threads.py
git commit -m "feat(threads): backfill_threads stamps legacy handovers via union-find"
```

---

### Task 5: MCP surface — thread tools, create-derivation, kill `handover_latest`, HTTP route

**Files:**
- Modify: `taskmaster/backlog_server.py` (`backlog_handover_create` ~2013-2107, `backlog_handover_latest` ~2267-2304 DELETE, `backlog_handover_resync` ~2308-2322, imports ~88, GET routes ~6998)
- Test: `tests/test_threads.py` (derivation helper only — MCP wrappers are thin)

**Interfaces:**
- Consumes: Tasks 1-4 (`sync_thread_registry`, `resolve_thread`, `list_threads`, `update_thread_status`, `backfill_threads`, `THREAD_STATUSES`).
- Produces MCP tools:
  - `backlog_handover_create(..., thread: str = "", ...)` — derives when empty: active bundle slug → epic of first task id → first task id → slugified tldr. Confirmation output's LAST line: `Resume: <thread> — <next_action or tldr>`.
  - `backlog_thread_list(include_closed: bool = False) -> str` — the board (open + parked; closed only when asked).
  - `backlog_thread_resume(ref: str) -> str` — thread header + newest handover frontmatter + full body.
  - `backlog_thread_update(name: str, status: str, reason: str = "") -> str`.
  - `backlog_handover_latest` REMOVED (already de-tooled; delete the function).
  - `backlog_handover_resync` also runs `backfill_threads` and reports stamped count.
  - HTTP `GET /api/threads` → JSON list from `list_threads`.
- Produces helper: `_derive_thread_name(task_ids: list[str], tldr: str, data: dict) -> str` in `taskmaster/taskmaster_v3.py` as `derive_thread_name(task_ids, tldr, data, bundle_slug="")` (core-testable; server passes the bundle slug).

- [ ] **Step 1: Write the failing test for the derivation helper**

Append to `tests/test_threads.py`:

```python
from taskmaster.taskmaster_v3 import derive_thread_name


def test_derive_thread_name_precedence():
    data = {"epics": [{"id": "team-relayout", "tasks": [{"id": "T-9"}]}]}
    assert derive_thread_name(["T-9"], "x", data, bundle_slug="my-bundle") == "my-bundle"
    assert derive_thread_name(["T-9"], "x", data) == "team-relayout"
    assert derive_thread_name(["T-77"], "x", data) == "t-77"
    assert derive_thread_name([], "Fix The Parser", data) == "fix-the-parser"
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_threads.py::test_derive_thread_name_precedence -v`
Expected: ImportError

- [ ] **Step 3: Implement `derive_thread_name` in `taskmaster/taskmaster_v3.py`** (after `backfill_threads`):

```python
def derive_thread_name(
    task_ids: list[str],
    tldr: str,
    data: dict[str, Any],
    bundle_slug: str = "",
) -> str:
    """Auto-name a thread: bundle slug → epic of first linked task →
    first task id → slugified tldr."""
    if bundle_slug:
        return normalize_thread_name(bundle_slug)
    if task_ids:
        for epic in data.get("epics") or []:
            if any(t.get("id") in task_ids for t in epic.get("tasks") or []):
                if epic.get("id"):
                    return normalize_thread_name(epic["id"])
        return normalize_thread_name(task_ids[0])
    return normalize_thread_name(tldr)
```

Run the test again → PASS.

- [ ] **Step 4: Wire the MCP server (`taskmaster/backlog_server.py`)**

4a. First READ `backlog_server.py:4828-4857` to confirm the in-memory bundle global's exact name (Explore reported `_session_bundle` dict with a `slug` key) and how it's accessed (`_get_session_bundle()` exists per the end-session playbook). Use whichever accessor the file actually defines.

4b. `backlog_handover_create`: add param `thread: str = ""` (after `session_kind`). Replace the body's data-load sequence so `data = _load()` happens BEFORE the write, then:

```python
    thread_name = (thread or "").strip()
    if not thread_name:
        bundle = _get_session_bundle() or {}
        thread_name = _derive_thread_name(
            task_ids or [], tldr, data, bundle_slug=bundle.get("slug", "") or ""
        )
```

(import `derive_thread_name as _derive_thread_name` alongside the existing `taskmaster_v3` imports at the top of the file). Pass `thread=thread_name` through to `_write_handover`. Extend the tool docstring's Args with: `thread: Thread this handover belongs to (stable resume token). Auto-derived from bundle/epic/task/tldr when empty.`

Replace the confirmation `lines` block's tail so the LAST line is always:

```python
    lines.append(f"Resume: {thread_name} — {next_action or tldr}")
```

4c. DELETE the whole `backlog_handover_latest` function (~2267-2304).

4d. `backlog_handover_resync`: before `_sync_handover_index(data, bp)`, add:

```python
    from taskmaster.taskmaster_v3 import backfill_threads as _backfill_threads
    backfill = _backfill_threads(bp, backlog_data=data)
```

and extend the return string:

```python
    extra = f" Backfilled thread on {len(backfill['stamped'])} legacy handover(s)." if backfill["stamped"] else ""
    return f"Handover index resynced — {n} entries in `backlog.yaml`.{extra}"
```

4e. Add the three thread tools next to the handover tools:

```python
@mcp.tool()
def backlog_thread_list(include_closed: bool = False) -> str:
    """The thread board — open (and parked) lines of work with their stable
    resume tokens. Resume one with `backlog_thread_resume(<name>)`.

    Args:
        include_closed: Also list closed threads (default False).
    """
    bp = _backlog_path()
    if not bp.exists():
        return "No backlog found."
    data = _load()
    if "threads" not in data:
        _sync_handover_index(data, bp)
        _save(data)
    from taskmaster.taskmaster_v3 import list_threads as _list_threads
    rows = _list_threads(data)
    if not include_closed:
        rows = [r for r in rows if r["status"] != "closed"]
    if not rows:
        return "No open threads. Write a handover to start one."
    lines = []
    for r in rows:
        stale = f" · {r['staleness_days']}d" if r["staleness_days"] else ""
        park = " [parked]" if r["status"] == "parked" else ""
        branch = f" · {r['branch']}" if r["branch"] else ""
        lines.append(f"- **{r['name']}**{park}{stale}{branch} — {r['tldr']}")
        if r["next_action"]:
            lines.append(f"  next: {r['next_action']}")
        if r["task_ids"]:
            lines.append(f"  tasks: {', '.join(r['task_ids'])}")
    lines.append("\nResume: `backlog_thread_resume(\"<name>\")`")
    return "\n".join(lines)


@mcp.tool()
def backlog_thread_resume(ref: str) -> str:
    """Resume a thread: returns its newest handover in full (frontmatter +
    body) in one call. `ref` is a thread name OR any handover id (stale dated
    slugs still land on the thread's newest handover).
    """
    bp = _backlog_path()
    if not bp.exists():
        return "No backlog found."
    data = _load()
    if "threads" not in data:
        _sync_handover_index(data, bp)
        _save(data)
    from taskmaster.taskmaster_v3 import resolve_thread as _resolve_thread
    try:
        tname, hid = _resolve_thread(data, bp, ref)
    except KeyError:
        return (f"No thread or handover matches {ref!r}. "
                f"See `backlog_thread_list()` for open threads.")
    try:
        fm, body = _read_handover(bp, hid)
    except FileNotFoundError:
        return f"Thread {tname!r} resolved to {hid}, but the file is missing — run `backlog_handover_resync`."
    t = (data.get("threads") or {}).get(tname) or {}
    header = [
        f"# Thread: {tname or '(none — standalone handover)'}",
        f"- status: {t.get('status', 'open')}" if tname else "",
        f"- handovers: {len(t.get('handover_ids') or []) or 1}",
        f"- newest: {hid}",
        "",
    ]
    fm_lines = [f"  {k}: {v}" for k, v in fm.items()]
    return "\n".join(x for x in header if x is not None) + "---\n" + "\n".join(fm_lines) + "\n---\n" + body


@mcp.tool()
def backlog_thread_update(name: str, status: str, reason: str = "") -> str:
    """Set a thread's status: open / parked / closed. Writing a new handover
    into the thread later auto-reopens it (override expires)."""
    bp = _backlog_path()
    if not bp.exists():
        return "No backlog found."
    data = _load()
    if "threads" not in data:
        _sync_handover_index(data, bp)
    from taskmaster.taskmaster_v3 import update_thread_status as _update_thread_status
    try:
        _update_thread_status(data, bp, name=name, status=status, reason=reason)
    except ValueError as exc:
        return f"Error: {exc}"
    except KeyError:
        return f"Error: no thread named {name!r}. See `backlog_thread_list()`."
    _save(data)
    return f"Thread {name} → {status}." + (f" ({reason})" if reason else "")
```

4f. HTTP route — in the GET handler, immediately before `elif clean_path == "/api/sessions":` (~line 6998), add:

```python
        elif clean_path == "/api/threads":
            from taskmaster.taskmaster_v3 import list_threads as _list_threads_http
            data = _load()
            if "threads" not in data:
                _sync_handover_index(data, _backlog_path())
                _save(data)
            self._send_json(200, _list_threads_http(data))
            return
```

- [ ] **Step 5: Verify server imports and full suite**

Run: `python -c "import taskmaster.backlog_server"` → no error
Run: `python -m pytest tests/ -q` → green. Grep `tests/` and `taskmaster/` for `backlog_handover_latest` — remove/update any remaining references.

- [ ] **Step 6: Commit**

```bash
git add taskmaster/backlog_server.py taskmaster/taskmaster_v3.py tests/
git commit -m "feat(threads): MCP thread_list/resume/update, create-time derivation, /api/threads; drop handover_latest"
```

---

### Task 6: Playbooks — resume flows use threads

**Files:**
- Modify: `playbooks/handover/playbook.md`, `playbooks/start-session/playbook.md`, `playbooks/end-session/playbook.md`
- Verify: `skills/handover/SKILL.md`, `skills/start-session/SKILL.md`, `playbooks/*/references/*.md`

**Interfaces:** Consumes the Task 5 tool names exactly: `backlog_thread_list`, `backlog_thread_resume`, `backlog_thread_update`, `backlog_handover_create(thread=...)`.

- [ ] **Step 1: `playbooks/handover/playbook.md`**

Insert a new step between steps 3 and 4 (renumber is unnecessary — use "3b"):

```markdown
**3b. Resolve `thread`.** The stable resume token. If this session resumed from a thread (via `backlog_thread_resume` or a pasted name), reuse that name. Otherwise leave `thread` empty — the server derives it (bundle slug → epic → task id → tldr). Only set it explicitly when the user names the line of work.
```

In step 8, add `thread` to the listed top-level fields.

Replace step 9 entirely:

```markdown
**9. Confirm.** Echo the server's final line verbatim — `Resume: <thread> — <next_action>` — as the last line of your reply. That line is the durable resume token: pasting the thread name into any future session resumes this work via `backlog_thread_resume`. Surface any WARNING line from the response.
```

Replace the "Manual status entry points" section (it references a dead todo/in-progress/done enum) with:

```markdown
## Manual status entry points

- `taskmaster:handover close <id>` — `backlog_handover_update_status(<id>, "closed", reason)`.
- `taskmaster:handover reopen <id>` — same with `"open"`.
- Thread level: `backlog_thread_update(<name>, "parked" | "closed" | "open", reason)` — park a line of work without touching individual handovers.
```

- [ ] **Step 2: `playbooks/start-session/playbook.md`**

Replace Step 2 ("Open handovers") with:

```markdown
### Step 2 — Thread board

Call `backlog_thread_list()`. Returns the open lines of work — one entry per thread: name (the resume token), staleness, branch, tldr, next action, tasks. This replaces per-handover listing; a thread's newest handover is fetched only when the user picks it (`backlog_thread_resume("<name>")`).
```

In Step 4 (Briefing), replace the "Where you left off" bullet with:

```markdown
- **Open threads:** the board from Step 2, one line each (`name — tldr → next_action`). If the user's prompt already names a thread or pastes a handover id, skip the board and call `backlog_thread_resume` with it directly.
```

- [ ] **Step 3: `playbooks/end-session/playbook.md`**

In step 9 (Confirm), replace with:

```markdown
**9. Confirm.** "Session logged. Task is now `{target_status}`." If a handover was written this session, end with its resume line verbatim: `Resume: <thread> — <next_action>`.
```

- [ ] **Step 4: Stale-reference sweep**

Run from repo root:

```bash
grep -rn "handover_latest\|status=\"open\", limit=1\|status='open', limit=1\|mark-done\|mark-in-progress\|mark-todo" playbooks/ skills/ taskmaster/ docs/ --include="*.md" --include="*.py"
```

Fix every hit that recommends the latest/limit=1 resume flow or the dead todo/in-progress/done handover enum (update `playbooks/handover/references/triage.md` if it speaks the old enum). Do NOT change historical spec documents under `docs/`.

- [ ] **Step 5: Commit**

```bash
git add playbooks/ skills/
git commit -m "feat(threads): playbooks resume via thread board + Resume line; drop latest/limit=1 flow"
```

---

### Task 7: Viewer rot fix — handover status enum

**Files:**
- Modify: `viewer/js/components/right-rail.js` (~90-140), `viewer/js/screens/sessions.js` (chips markup ~34-38, `refreshStatusChipCounts` ~152-164, defaults ~84, 213, 225), viewer CSS (find via `grep -rln "ho-status-pill-todo" viewer/`)
- Test: `viewer/tests/` route-mocked spec (Task 9 covers it — this task keeps unit-level only)

**Interfaces:** Status vocabulary everywhere in the viewer becomes `open / closed / superseded` (matching `HANDOVER_STATUSES`); default visible filter set `['open', 'closed']`.

- [ ] **Step 1: `right-rail.js`**

In `openStatusMenu` change the options loop:

```js
  for (const opt of ['open', 'closed', 'superseded']) {
```

and the class-patching lines:

```js
          pill.classList.remove('ho-status-pill-open', 'ho-status-pill-closed', 'ho-status-pill-superseded');
```

In `panelHandovers` and any other `|| 'todo'` default in this file: change to `|| 'open'`.

- [ ] **Step 2: `sessions.js`**

Chips markup:

```html
      <div class="handover-status-chips" data-role="ho-status">
        <span class="status-chip on" data-status="open">open <span class="ct">0</span></span>
        <span class="status-chip on" data-status="closed">closed <span class="ct">0</span></span>
        <span class="status-chip" data-status="superseded">superseded <span class="ct">0</span></span>
      </div>
```

`refreshStatusChipCounts`: `const counts = { open: 0, closed: 0, superseded: 0 };` and default `meta.status || 'open'`.
Persisted default: `const persistedStatus = (prefsData.screens?.sessions?.handoverStatus) || ['open', 'closed'];`
Every remaining `|| 'todo'` in this file → `|| 'open'`. The `openStatusMenu` call site passes `h.status || 'open'`.

- [ ] **Step 3: CSS**

`grep -rln "ho-status-pill-todo" viewer/` — in each hit, rename the three status variant classes: `-todo` → `-open`, `-in-progress` → `-closed`, `-superseded` stays/added. Keep the existing colour tokens (open = the old todo colour, closed = the old done colour); add a muted variant for superseded if none exists (tinted background + full border — no left rails).

- [ ] **Step 4: Manual smoke via server**

Start the viewer (`python -m taskmaster.backlog_server --viewer` — or the repo's documented viewer launch; check `viewer/README.md` if unsure), open `#/sessions`, click a handover, click the status pill, pick `closed`: the POST must return 200 (it 400ed before this fix).

- [ ] **Step 5: Commit**

```bash
git add viewer/
git commit -m "fix(viewer): handover status menu speaks open/closed/superseded (was dead todo/in-progress/done)"
```

---

### Task 8: Viewer — thread board + wired copy buttons

**Files:**
- Modify: `viewer/js/api.js` (~164), `viewer/js/screens/sessions.js`, viewer CSS file that owns `.sessions-page` (find via `grep -rln "sessions-page" viewer/`)

**Interfaces:**
- Consumes: `GET /api/threads` (Task 5), `bindCopy` from `viewer/js/lib/copy.js`.
- Produces: `listThreads()` in api.js; a board section above the timeline; resume-copy buttons copying `Resume: <name> — <next_action>`.

- [ ] **Step 1: `api.js`** — after `getSessionDetail`, add:

```js
export async function listThreads() {
  const r = await fetch('/api/threads');
  if (!r.ok) throw new Error(`listThreads: ${r.status}`);
  return r.json();
}
```

- [ ] **Step 2: `sessions.js` board section**

Imports: add `listThreads` to the api import; add `import { bindCopy } from '../lib/copy.js';`.

Markup — inside `.sessions-page`, ABOVE the kinds row:

```html
      <div class="thread-board" data-role="board"></div>
```

In `mount`, after `state.sessions = await listSessions();` add:

```js
  try {
    state.threads = await listThreads();
  } catch { state.threads = []; }
  renderBoard(root, state);
```

Add the functions:

```js
function renderBoard(root, state) {
  const host = root.querySelector('[data-role=board]');
  if (!host) return;
  const open = (state.threads || []).filter(t => t.status === 'open');
  const parked = (state.threads || []).filter(t => t.status === 'parked');
  host.innerHTML = '';
  if (!open.length && !parked.length) { host.style.display = 'none'; return; }
  host.style.display = '';
  const grid = document.createElement('div');
  grid.className = 'tb-grid';
  for (const t of open) grid.appendChild(threadCard(t));
  host.appendChild(grid);
  if (parked.length) {
    const fold = document.createElement('details');
    fold.className = 'tb-parked';
    fold.innerHTML = `<summary>${parked.length} parked</summary>`;
    const pgrid = document.createElement('div');
    pgrid.className = 'tb-grid';
    for (const t of parked) pgrid.appendChild(threadCard(t));
    fold.appendChild(pgrid);
    host.appendChild(fold);
  }
}

function threadCard(t) {
  const card = document.createElement('div');
  card.className = `thread-card thread-card-${t.status}`;
  const stale = t.staleness_days > 0 ? `${t.staleness_days}d` : 'today';
  card.innerHTML =
    `<div class="tc-head">`
    + `<span class="tc-name mono">${escapeHtml(t.name)}</span>`
    + `<span class="tc-stale mono">${escapeHtml(stale)}</span>`
    + `</div>`
    + `<div class="tc-tldr">${escapeHtml(t.tldr || '')}</div>`
    + (t.next_action ? `<div class="tc-next">→ ${escapeHtml(t.next_action)}</div>` : '')
    + `<div class="tc-foot">`
    + (t.task_ids || []).slice(0, 4).map(id => `<span class="pill task mono">${escapeHtml(id)}</span>`).join('')
    + (t.branch ? `<span class="tc-branch mono">${escapeHtml(t.branch)}</span>` : '')
    + `<button class="tc-copy" title="Copy resume line">⧉ resume</button>`
    + `</div>`;
  const btn = card.querySelector('.tc-copy');
  bindCopy(btn, `Resume: ${t.name} — ${t.next_action || t.tldr || ''}`);
  card.addEventListener('click', (ev) => {
    if (ev.target === btn) return;
    location.hash = `#/sessions/${encodeURIComponent(t.name)}`;
  });
  return card;
}
```

- [ ] **Step 3: Wire the dead rail copy button**

In `openHandoverDetail`'s `onMount`, after the status-pill wiring, add:

```js
      const copyBtn = el.querySelector('.rr-resume .copy');
      if (copyBtn) bindCopy(copyBtn, h.resume_prompt || h.next_action || '');
```

- [ ] **Step 4: CSS** — append to the stylesheet that owns `.sessions-page`:

```css
/* Thread board — open lines of work above the diary. */
.thread-board { margin-bottom: 16px; }
.tb-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 10px;
}
.thread-card {
  background: var(--s2);
  border: 1px solid var(--bl);
  border-radius: 6px;
  padding: 10px 12px;
  cursor: pointer;
}
.thread-card:hover { background: var(--s3); border-color: var(--bl-strong, var(--bl)); }
.tc-head { display: flex; justify-content: space-between; align-items: baseline; }
.tc-name { font-weight: 600; }
.tc-stale { opacity: 0.6; font-size: 0.85em; }
.tc-tldr { margin-top: 4px; }
.tc-next { margin-top: 4px; opacity: 0.8; font-size: 0.9em; }
.tc-foot { margin-top: 8px; display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
.tc-branch { opacity: 0.6; font-size: 0.85em; }
.tc-copy {
  margin-left: auto;
  background: var(--s3);
  border: 1px solid var(--bl);
  border-radius: 4px;
  padding: 2px 8px;
  cursor: copy;
}
.tc-copy:hover { background: var(--s4); }
.tb-parked { margin-top: 8px; }
.tb-parked summary { cursor: pointer; opacity: 0.7; }
```

Use the file's existing surface/border token names — if they differ from `--s2`/`--bl`, match the tokens used by neighbouring card rules in that file. No transforms, no box-shadows, no left rails.

- [ ] **Step 5: Manual smoke**

Viewer up, `#/sessions`: board renders open-thread cards; the ⧉ resume button flashes and puts `Resume: <name> — <next action>` on the clipboard; the rail's RESUME copy button now works too.

- [ ] **Step 6: Commit**

```bash
git add viewer/
git commit -m "feat(viewer): thread board with copy-resume; wire dead rail copy button"
```

---

### Task 9: Viewer — diary lanes as threads + route-mocked specs

**Files:**
- Modify: `viewer/js/screens/sessions.js` (view toggle removal, thread-row rendering), `viewer/js/components/timeline.js` (labels)
- Test: `viewer/tests/threads-board.spec.js` (new, route-mocked)

**Interfaces:** Consumes the new `/api/sessions` row shape from Task 3 (`{id: threadName, kind: 'thread', status, tldr, ...}`) and `/api/threads`.

- [ ] **Step 1: Remove the dead Lanes/By-Task stub views**

In `sessions.js`: delete the `tmSegmented` view toggle block (and its `topbar?.appendChild(viewToggle)`), delete `state.view` and the `prefs.screens.sessions.view` mirroring, and in `render()` delete the `if (state.view !== 'A') { ...stub... }` branch. The diary is the only timeline view.

- [ ] **Step 2: Thread-row labels**

In `timeline.js` `sessionHeadHtml`, change the kind label and title line:

```js
    `<span class="ho-kind session">THREAD</span>`
```

(the `id` shown in `.ho-title` is now the thread name — no other change needed). In `sessions.js` `renderSessionRail`, change `SESSION` pill text to `THREAD` and add the thread's tldr under the title:

```js
    + `<div class="rr-title">${escapeHtml(s.id)}</div>`
    + (s.tldr ? `<div class="rr-meta"><span>${escapeHtml(s.tldr)}</span></div>` : '')
```

Also extend `_filteredSessions`'s haystack — it already includes `s.tldr || ''`; verify and keep. Rename the kind-chip label in the mount markup from `Sessions` to `Threads` (the `data-kind="session"` attribute and `state.kinds.session` key stay as-is — display text only), and update `refreshKindCounts`'s subcount strings from 'session'/'sessions' to 'thread'/'threads'.

- [ ] **Step 3: Route-mocked spec**

First read one existing route-mocked spec in `viewer/tests/` (grep for `page.route(` there) and copy its server-bootstrap/fixture pattern exactly — port handling in this suite is a known landmine (ISS-025: never hardcode 8765; only route-mocked specs are trustworthy). Then create `viewer/tests/threads-board.spec.js` with this content, adapted to that bootstrap:

```js
// Route-mocked: thread board renders, copy button present, diary lanes keyed by thread.
const { test, expect } = require('@playwright/test');

const THREADS = [
  { name: 'team-relayout', status: 'open', tldr: 'M1 shipped', next_action: 'start M2',
    task_ids: ['T-1'], branch: 'feat/relayout', last_touched: '2026-07-13T10:00:00+00:00', staleness_days: 0 },
  { name: 'guard-hooks-polish', status: 'parked', tldr: 'awaiting review', next_action: '',
    task_ids: [], branch: '', last_touched: '2026-07-10T10:00:00+00:00', staleness_days: 3 },
];
const SESSIONS = [
  { id: 'team-relayout', kind: 'thread', status: 'open',
    start: '2026-07-12T09:00:00+00:00', end: '2026-07-13T10:00:00+00:00',
    duration: 90000, time_resolution: 'full',
    handover_ids: ['2026-07-13-m1-shipped'],
    handovers: [{ id: '2026-07-13-m1-shipped', status: 'open', viewer_kind: 'checkpoint', tldr: 'M1 shipped' }],
    task_ids: ['T-1'], tldr: 'M1 shipped', next_action: 'start M2' },
];

test.beforeEach(async ({ page }) => {
  await page.route('**/api/threads', r => r.fulfill({ json: THREADS }));
  await page.route('**/api/sessions', r => r.fulfill({ json: SESSIONS }));
});

test('board shows open thread cards with resume copy', async ({ page }) => {
  await page.goto('/#/sessions');
  const card = page.locator('.thread-card-open');
  await expect(card).toHaveCount(1);
  await expect(card).toContainText('team-relayout');
  await expect(card).toContainText('start M2');
  await expect(card.locator('.tc-copy')).toBeVisible();
});

test('parked threads sit under a fold', async ({ page }) => {
  await page.goto('/#/sessions');
  const fold = page.locator('.tb-parked');
  await expect(fold.locator('summary')).toContainText('1 parked');
});

test('diary lane is keyed by thread name with THREAD label', async ({ page }) => {
  await page.goto('/#/sessions');
  await expect(page.locator('.ho-title', { hasText: 'team-relayout' })).toBeVisible();
  await expect(page.locator('.ho-kind.session').first()).toHaveText('THREAD');
});

test('status chips speak open/closed/superseded', async ({ page }) => {
  await page.goto('/#/sessions');
  const chips = page.locator('[data-role=ho-status] .status-chip');
  await expect(chips).toHaveText([/open/, /closed/, /superseded/]);
});
```

- [ ] **Step 4: Run the specs**

Run (from `viewer/`): `npx playwright test tests/threads-board.spec.js`
Expected: 4 PASS. Also run the unit suite: `node --test tests/unit/` — green.

- [ ] **Step 5: Commit**

```bash
git add viewer/
git commit -m "feat(viewer): diary lanes keyed by threads; drop dead Lanes/By-Task stubs; route-mocked board specs"
```

---

### Task 10: Version bump + CHANGELOG + final sweep

**Files:**
- Modify: `pyproject.toml`, `.claude-plugin/plugin.json`, `CHANGELOG.md` (all in the taskmaster repo root)

- [ ] **Step 1: Bump minor**

Read the current `version` in `pyproject.toml`; increment the MINOR, reset patch (additive surface: new MCP tools + new field → minor per SemVer convention in CHANGELOG header). Set the SAME version string in `.claude-plugin/plugin.json`.

- [ ] **Step 2: CHANGELOG entry**

Add at the top of `CHANGELOG.md`:

```markdown
## <new-version>

Handover threads — stable resume tokens and a thread-lane sessions view.

- New: `thread` frontmatter on handovers; rebuildable `threads:` registry in backlog.yaml (`thread_meta:` holds user-set overrides; a newer handover auto-reopens).
- New MCP: `backlog_thread_list`, `backlog_thread_resume` (accepts thread name or any handover id), `backlog_thread_update`; `backlog_handover_create` gains `thread` (auto-derived bundle → epic → task → tldr) and always ends with a copy-ready `Resume:` line.
- Changed: `/api/sessions` now returns one lane per thread (SES-NNNN ids, 30-min gap clustering, and `parallel_with` removed); `backlog_handover_resync` backfills `thread` onto legacy handovers.
- Removed: `backlog_handover_latest`; start-session's latest/limit=1 resume flow; viewer Lanes/By-Task stub views.
- Fixed: viewer handover status menu spoke a dead todo/in-progress/done enum (POSTs 400ed) — now open/closed/superseded; the rail's RESUME copy button is wired.
- Viewer: thread board (open-thread cards with copy-resume) above the diary.
```

- [ ] **Step 3: Full verification**

```bash
python -m pytest tests/ -q
```
Expected: green.
From `viewer/`: `npx playwright test tests/threads-board.spec.js` and `node --test tests/unit/` — green.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml .claude-plugin/plugin.json CHANGELOG.md
git commit -m "chore: bump version + changelog for handover threads"
```

---

## Post-plan integration (orchestrator, NOT part of task execution)

Merging `handover-threads` into taskmaster `master`, advancing the `plugins/taskmaster` submodule in claude-tools, syncing `plugin.json`/`marketplace.json` versions there, and any push — all follow the claude-tools versioning protocol and the Merge & Push Policy (pushes are user-gated). MCP server restart required before the new tools are visible in a live session.
