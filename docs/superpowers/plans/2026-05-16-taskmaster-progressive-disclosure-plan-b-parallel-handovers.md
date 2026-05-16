# Plan B — Parallel Handovers — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Formalize handover status to `open | closed | superseded`, implement a smart auto-close rule that keeps context-rich handovers alive after task completion, deprecate `backlog_handover_latest`, and expose flagged-but-open surfacing to start-session.

**Architecture:** Three-layer change. (1) Data layer in `taskmaster_v3.py` gains the new enum (`HANDOVER_STATUSES`), a `smart_auto_close_handovers()` function, a `flag_open_reason()` inspector, and a one-shot `migrate_handover_statuses()` script. (2) FastMCP wrapper layer in `backlog_server.py` wires smart-close into `backlog_complete_task` and `backlog_archive_task`, adds `flag_reason` to list output, and deprecates `backlog_handover_latest` as a thin alias. (3) Migration in `scripts/migrate_handover_statuses.py` handles the old `todo / in-progress / done` → `open / closed / superseded` rename for all on-disk files. All changes are backward-compatible: callers using the old status values get a clear error pointing to the new enum.

**Tech Stack:** Python 3.11+, FastMCP, PyYAML, pytest. No new deps.

**Spec:** `docs/superpowers/specs/2026-05-15-taskmaster-progressive-disclosure-design.md` §3.

**Depends on:** Plan A (foundation must be complete first — `extract_tldr`, slim defaults, `verbose=true` wiring must exist).

---

## File Structure

**Modify:**
- `plugins/taskmaster/taskmaster_v3.py` — replace `HANDOVER_STATUSES = ("todo", "in-progress", "done")` with `("open", "closed", "superseded")`; update `_default_handover_status()`; update `apply_supersession()` to set `superseded` (was `done`); update `backfill_handover_status()` to use new enum; update `update_handover_status()` validation; add `smart_auto_close_handovers()`, `flag_open_reason()`, `migrate_handover_statuses()`; update `mark_task_handovers_complete()` to delegate to smart-close logic.
- `plugins/taskmaster/backlog_server.py` — update `backlog_handover_list` status filter to accept new enum; update `backlog_complete_task` to call `smart_auto_close_handovers()`; update `backlog_archive_task` same; deprecate `backlog_handover_latest` as alias; add `flag_reason` field to list output lines.
- `plugins/taskmaster/CHANGELOG.md` — entry for v3.X parallel-handovers release.

**Create:**
- `plugins/taskmaster/tests/test_handover_status_enum_v2.py`
- `plugins/taskmaster/tests/test_handover_smart_close.py`
- `plugins/taskmaster/tests/test_handover_flag_open_reason.py`
- `plugins/taskmaster/tests/test_handover_status_migration.py`
- `plugins/taskmaster/tests/test_handover_latest_deprecated.py`
- `plugins/taskmaster/tests/test_handover_list_open_filter.py`
- `plugins/taskmaster/tests/test_handover_parallel_smoke.py`
- `plugins/taskmaster/scripts/migrate_handover_statuses.py`

---

## Phase 1 — Enum rename

### Task 1: Replace `HANDOVER_STATUSES` with `open | closed | superseded`

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py`
- Test: `plugins/taskmaster/tests/test_handover_status_enum_v2.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# plugins/taskmaster/tests/test_handover_status_enum_v2.py
import sys
from pathlib import Path
import yaml

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

from taskmaster_v3 import HANDOVER_STATUSES, write_handover, read_handover


def _setup(tmp_path):
    bp = tmp_path / "backlog.yaml"
    bp.write_text(yaml.safe_dump({"meta": {}, "epics": []}))
    (tmp_path / "handovers").mkdir()
    return bp


def test_handover_statuses_enum_has_new_values():
    assert "open" in HANDOVER_STATUSES
    assert "closed" in HANDOVER_STATUSES
    assert "superseded" in HANDOVER_STATUSES


def test_handover_statuses_enum_excludes_old_values():
    assert "todo" not in HANDOVER_STATUSES
    assert "in-progress" not in HANDOVER_STATUSES
    assert "done" not in HANDOVER_STATUSES


def test_write_handover_defaults_to_open(tmp_path):
    bp = _setup(tmp_path)
    hid, _ = write_handover(bp, tldr="test", session_kind="end-of-day")
    fm, _ = read_handover(bp, hid)
    assert fm["status"] == "open"


def test_write_handover_auto_stage_defaults_to_closed(tmp_path):
    """auto-stage bookkeeping checkpoints are born closed — not open."""
    bp = _setup(tmp_path)
    hid, _ = write_handover(bp, tldr="auto", session_kind="auto-stage")
    fm, _ = read_handover(bp, hid)
    assert fm["status"] == "closed"


def test_update_handover_status_rejects_old_enum(tmp_path):
    import pytest
    from taskmaster_v3 import update_handover_status
    bp = _setup(tmp_path)
    hid, _ = write_handover(bp, tldr="test", session_kind="end-of-day")
    with pytest.raises(ValueError, match="open"):
        update_handover_status(bp, handover_id=hid, status="todo")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_handover_status_enum_v2.py -v`
Expected: FAIL — `"todo" in HANDOVER_STATUSES` is True; `"open" in HANDOVER_STATUSES` is False.

- [ ] **Step 3: Replace the enum and update `_default_handover_status()`**

In `plugins/taskmaster/taskmaster_v3.py`, find and replace:

```python
# OLD (~line 708)
HANDOVER_STATUSES = ("todo", "in-progress", "done")


def _default_handover_status(session_kind: str) -> str:
    """auto-stage handovers are bookkeeping checkpoints — born done. All other
    kinds default to todo so the user explicitly clears their backlog."""
    return "done" if session_kind == "auto-stage" else "todo"
```

Replace with:

```python
# NEW
HANDOVER_STATUSES = ("open", "closed", "superseded")


def _default_handover_status(session_kind: str) -> str:
    """auto-stage handovers are bookkeeping checkpoints — born closed.
    All other kinds default to open so they surface in start-session glance."""
    return "closed" if session_kind == "auto-stage" else "open"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_handover_status_enum_v2.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_handover_status_enum_v2.py
git commit -m "feat(taskmaster): rename handover status enum to open/closed/superseded"
```

---

### Task 2: Update `apply_supersession()` and `backfill_handover_status()` for new enum

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py`
- Test: `plugins/taskmaster/tests/test_handover_status_enum_v2.py` (extend)

- [ ] **Step 1: Add failing tests**

Append to `plugins/taskmaster/tests/test_handover_status_enum_v2.py`:

```python
from taskmaster_v3 import (
    apply_supersession,
    backfill_handover_status,
    write_task_file,
)


def test_apply_supersession_sets_superseded_status(tmp_path):
    bp = _setup(tmp_path)
    old_id, _ = write_handover(bp, tldr="old", session_kind="end-of-day")
    new_id, _ = write_handover(bp, tldr="new", session_kind="end-of-day")
    apply_supersession(bp, old_id=old_id, new_id=new_id)
    fm, _ = read_handover(bp, old_id)
    assert fm["status"] == "superseded"
    assert fm["superseded_by"] == new_id


def test_backfill_legacy_handovers_get_open_not_done(tmp_path):
    """Legacy handovers without status get 'open', not 'done'."""
    bp, hd = tmp_path / "backlog.yaml", tmp_path / "handovers"
    bp.write_text(yaml.safe_dump({"meta": {}, "epics": []}))
    hd.mkdir()
    legacy_fm = {
        "id": "2025-01-01-legacy",
        "date": "2025-01-01",
        "created": "2025-01-01T00:00:00+00:00",
        "tldr": "old work",
        "task_ids": [],
        "session_kind": "end-of-day",
    }
    write_task_file(hd / "2025-01-01-legacy.md", legacy_fm, "body")
    data = yaml.safe_load(bp.read_text())
    backfill_handover_status(data, bp)
    fm, _ = read_handover(bp, "2025-01-01-legacy")
    assert fm["status"] == "open"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_handover_status_enum_v2.py::test_apply_supersession_sets_superseded_status plugins/taskmaster/tests/test_handover_status_enum_v2.py::test_backfill_legacy_handovers_get_open_not_done -v`
Expected: FAIL — `apply_supersession` sets `status = "done"` (old value); backfill sets `status = "done"` not `"open"`.

- [ ] **Step 3: Update `apply_supersession()` and `backfill_handover_status()`**

In `plugins/taskmaster/taskmaster_v3.py`, find in `apply_supersession()` (~line 919):

```python
    if not fm.get("status_user_set"):
        fm["status"] = "done"
        fm["status_changed"] = datetime.now(timezone.utc).isoformat(timespec="microseconds")
        fm["status_reason"] = f"superseded by {new_id}"
```

Replace `"done"` with `"superseded"`:

```python
    if not fm.get("status_user_set"):
        fm["status"] = "superseded"
        fm["status_changed"] = datetime.now(timezone.utc).isoformat(timespec="microseconds")
        fm["status_reason"] = f"superseded by {new_id}"
```

In `backfill_handover_status()` (~line 1073), replace:

```python
        fm["status"] = "done"
```

with:

```python
        fm["status"] = "open"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_handover_status_enum_v2.py -v`
Expected: All 7 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_handover_status_enum_v2.py
git commit -m "feat(taskmaster): update apply_supersession and backfill to use new status enum"
```

---

## Phase 2 — Smart auto-close rule

### Task 3: Add `smart_auto_close_handovers()` data-layer function

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py` (add after `mark_task_handovers_complete`)
- Test: `plugins/taskmaster/tests/test_handover_smart_close.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# plugins/taskmaster/tests/test_handover_smart_close.py
import sys
from pathlib import Path
import yaml

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

from taskmaster_v3 import (
    read_handover,
    smart_auto_close_handovers,
    write_handover,
)

_DONE_TASKS = {"T-1", "T-2", "T-archived"}
_ARCHIVED_TASKS = {"T-archived"}
_ALL_TERMINAL = _DONE_TASKS | _ARCHIVED_TASKS


def _setup(tmp_path):
    bp = tmp_path / "backlog.yaml"
    bp.write_text(yaml.safe_dump({"meta": {}, "epics": []}))
    (tmp_path / "handovers").mkdir()
    return bp


def test_smart_close_all_tasks_done_empty_next_action(tmp_path):
    bp = _setup(tmp_path)
    hid, _ = write_handover(
        bp,
        tldr="all wrapped",
        session_kind="task-complete",
        task_ids=["T-1"],
        next_action="",
    )
    result = smart_auto_close_handovers(bp, triggering_task_id="T-1",
                                        done_or_archived_ids=_ALL_TERMINAL)
    assert hid in result["closed"]
    fm, _ = read_handover(bp, hid)
    assert fm["status"] == "closed"


def test_smart_close_surviving_next_action_keeps_open(tmp_path):
    bp = _setup(tmp_path)
    hid, _ = write_handover(
        bp,
        tldr="next references live task",
        session_kind="task-complete",
        task_ids=["T-1"],
        next_action="Start T-99 after merging",
    )
    result = smart_auto_close_handovers(bp, triggering_task_id="T-1",
                                        done_or_archived_ids=_ALL_TERMINAL)
    assert hid in result["flagged"]
    assert hid not in result["closed"]
    fm, _ = read_handover(bp, hid)
    assert fm["status"] == "open"


def test_smart_close_context_handoff_kind_keeps_open(tmp_path):
    bp = _setup(tmp_path)
    hid, _ = write_handover(
        bp,
        tldr="context handoff",
        session_kind="context-handoff",
        task_ids=["T-1"],
        next_action="",
    )
    result = smart_auto_close_handovers(bp, triggering_task_id="T-1",
                                        done_or_archived_ids=_ALL_TERMINAL)
    assert hid in result["flagged"]
    assert hid not in result["closed"]
    fm, _ = read_handover(bp, hid)
    assert fm["status"] == "open"


def test_smart_close_partial_task_ids_keeps_open(tmp_path):
    bp = _setup(tmp_path)
    hid, _ = write_handover(
        bp,
        tldr="two tasks, one live",
        session_kind="task-complete",
        task_ids=["T-1", "T-live"],
        next_action="",
    )
    result = smart_auto_close_handovers(bp, triggering_task_id="T-1",
                                        done_or_archived_ids=_ALL_TERMINAL)
    assert hid in result["flagged"]
    assert hid not in result["closed"]


def test_smart_close_skips_already_closed(tmp_path):
    from taskmaster_v3 import update_handover_status
    bp = _setup(tmp_path)
    hid, _ = write_handover(
        bp,
        tldr="already closed",
        session_kind="task-complete",
        task_ids=["T-1"],
        next_action="",
    )
    update_handover_status(bp, handover_id=hid, status="closed")
    result = smart_auto_close_handovers(bp, triggering_task_id="T-1",
                                        done_or_archived_ids=_ALL_TERMINAL)
    assert hid not in result["closed"]
    assert hid not in result["flagged"]


def test_smart_close_skips_superseded(tmp_path):
    from taskmaster_v3 import update_handover_status
    bp = _setup(tmp_path)
    hid, _ = write_handover(
        bp,
        tldr="superseded",
        session_kind="task-complete",
        task_ids=["T-1"],
    )
    update_handover_status(bp, handover_id=hid, status="superseded")
    result = smart_auto_close_handovers(bp, triggering_task_id="T-1",
                                        done_or_archived_ids=_ALL_TERMINAL)
    assert hid not in result["closed"]
    assert hid not in result["flagged"]


def test_smart_close_next_action_only_references_done_tasks_closes(tmp_path):
    """next_action that mentions only done task IDs still qualifies for auto-close."""
    bp = _setup(tmp_path)
    hid, _ = write_handover(
        bp,
        tldr="all refs done",
        session_kind="task-complete",
        task_ids=["T-1"],
        next_action="Confirmed T-2 is done, no further work needed.",
    )
    result = smart_auto_close_handovers(bp, triggering_task_id="T-1",
                                        done_or_archived_ids=_ALL_TERMINAL)
    assert hid in result["closed"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_handover_smart_close.py -v`
Expected: FAIL with `ImportError: cannot import name 'smart_auto_close_handovers'`

- [ ] **Step 3: Implement `smart_auto_close_handovers()`**

Add to `plugins/taskmaster/taskmaster_v3.py` after `mark_task_handovers_complete` (~line 1014):

```python
# ── Parallel-handover smart-close ─────────────────────────────────────────────

_TASK_ID_RE = re.compile(r"\bT-\d+\b")

# session_kinds that are eligible for auto-close when all criteria met.
_AUTO_CLOSE_ELIGIBLE_KINDS: frozenset[str] = frozenset({"task-complete", ""})


def _next_action_references_live_tasks(
    next_action: str, done_or_archived_ids: set[str]
) -> bool:
    """Return True if `next_action` mentions any task ID not in
    `done_or_archived_ids`. Empty string → no live references → False."""
    if not next_action or not next_action.strip():
        return False
    mentioned = set(_TASK_ID_RE.findall(next_action))
    live = mentioned - done_or_archived_ids
    return bool(live)


def smart_auto_close_handovers(
    backlog_path: Path,
    *,
    triggering_task_id: str,
    done_or_archived_ids: set[str],
) -> dict[str, list[str]]:
    """Apply the smart auto-close rule to open handovers that include
    `triggering_task_id` in their task_ids.

    Auto-close only when ALL true:
      1. All task_ids in the handover are in done_or_archived_ids.
      2. next_action is empty OR mentions only done/archived task IDs.
      3. session_kind is "task-complete" or null/absent.

    Otherwise: leave open and flag with a reason.

    Returns:
        {"closed": [...list of ids auto-closed...],
         "flagged": [...list of ids kept open with flag_reason stamped...]}
    """
    closed: list[str] = []
    flagged: list[str] = []

    for hid in list_handover_ids(backlog_path):
        try:
            fm, body = read_handover(backlog_path, hid)
        except (OSError, ValueError):
            continue

        # Only consider open handovers that include the triggering task.
        if fm.get("status") != "open":
            continue
        task_ids: list[str] = fm.get("task_ids") or []
        if triggering_task_id not in task_ids:
            continue
        if fm.get("status_user_set"):
            continue

        # Evaluate the three criteria.
        all_tasks_terminal = all(t in done_or_archived_ids for t in task_ids)
        next_action: str = (fm.get("next_action") or "").strip()
        next_action_live = _next_action_references_live_tasks(next_action, done_or_archived_ids)
        session_kind: str = fm.get("session_kind") or ""
        kind_eligible = session_kind in _AUTO_CLOSE_ELIGIBLE_KINDS

        if all_tasks_terminal and not next_action_live and kind_eligible:
            # All criteria met — auto-close.
            fm["status"] = "closed"
            fm["status_changed"] = datetime.now(timezone.utc).isoformat(timespec="microseconds")
            fm["status_reason"] = f"auto-closed: all task_ids done, triggering task {triggering_task_id}"
            fm.pop("flag_reason", None)
            write_task_file(handover_path(backlog_path, hid), fm, body)
            closed.append(hid)
        else:
            # Build a human-readable flag reason for start-session surfacing.
            reasons: list[str] = []
            if not all_tasks_terminal:
                live_ids = [t for t in task_ids if t not in done_or_archived_ids]
                reasons.append(f"task_ids still open: {', '.join(live_ids)}")
            if next_action_live:
                live_refs = set(_TASK_ID_RE.findall(next_action)) - done_or_archived_ids
                reasons.append(f"next_action references {', '.join(sorted(live_refs))}")
            if not kind_eligible:
                reasons.append(f"session_kind={session_kind!r} preserved for context")
            flag_reason = "; ".join(reasons)
            fm["flag_reason"] = flag_reason
            write_task_file(handover_path(backlog_path, hid), fm, body)
            flagged.append(hid)

    return {"closed": closed, "flagged": flagged}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_handover_smart_close.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_handover_smart_close.py
git commit -m "feat(taskmaster): add smart_auto_close_handovers() with three-criteria rule"
```

---

### Task 4: Add `flag_open_reason()` inspector and wire into `backlog_complete_task`

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py` (add `flag_open_reason()`)
- Modify: `plugins/taskmaster/backlog_server.py` (wire `backlog_complete_task`, `backlog_archive_task`)
- Test: `plugins/taskmaster/tests/test_handover_flag_open_reason.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# plugins/taskmaster/tests/test_handover_flag_open_reason.py
import sys
from pathlib import Path
import yaml

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

from taskmaster_v3 import (
    flag_open_reason,
    read_handover,
    smart_auto_close_handovers,
    write_handover,
)


def _setup(tmp_path):
    bp = tmp_path / "backlog.yaml"
    bp.write_text(yaml.safe_dump({"meta": {}, "epics": []}))
    (tmp_path / "handovers").mkdir()
    return bp


def test_flag_open_reason_returns_none_when_no_flag(tmp_path):
    bp = _setup(tmp_path)
    hid, _ = write_handover(bp, tldr="clean", session_kind="end-of-day")
    assert flag_open_reason(bp, hid) is None


def test_flag_open_reason_returns_reason_after_smart_close_flags(tmp_path):
    bp = _setup(tmp_path)
    hid, _ = write_handover(
        bp,
        tldr="has live ref",
        session_kind="context-handoff",
        task_ids=["T-1"],
        next_action="",
    )
    smart_auto_close_handovers(
        bp,
        triggering_task_id="T-1",
        done_or_archived_ids={"T-1"},
    )
    reason = flag_open_reason(bp, hid)
    assert reason is not None
    assert "context-handoff" in reason or "session_kind" in reason


def test_flag_open_reason_returns_none_after_close(tmp_path):
    from taskmaster_v3 import update_handover_status
    bp = _setup(tmp_path)
    hid, _ = write_handover(
        bp,
        tldr="will close",
        session_kind="task-complete",
        task_ids=["T-1"],
    )
    update_handover_status(bp, handover_id=hid, status="closed")
    assert flag_open_reason(bp, hid) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_handover_flag_open_reason.py -v`
Expected: FAIL with `ImportError: cannot import name 'flag_open_reason'`

- [ ] **Step 3: Implement `flag_open_reason()` and wire server calls**

Add to `plugins/taskmaster/taskmaster_v3.py` immediately after `smart_auto_close_handovers()`:

```python
def flag_open_reason(backlog_path: Path, handover_id: str) -> str | None:
    """Return the `flag_reason` string for an open handover, or None if absent.

    Returns None for closed/superseded handovers — those are not flagged.
    """
    try:
        fm, _ = read_handover(backlog_path, handover_id)
    except (OSError, ValueError):
        return None
    if fm.get("status") != "open":
        return None
    return fm.get("flag_reason") or None
```

In `plugins/taskmaster/backlog_server.py`, find `backlog_complete_task` (~line 3223). Locate the block that calls `mark_task_handovers_complete`:

```python
    if target_status == "done":
        try:
            from taskmaster_v3 import mark_task_handovers_complete as _mark_complete
            flipped_handovers = _mark_complete(_backlog_path(), task_id)
        except Exception:
            flipped_handovers = []
        if flipped_handovers:
            data2 = _load()
            _sync_handover_index(data2, _backlog_path())
            _save(data2)
```

Replace with:

```python
    if target_status == "done":
        try:
            from taskmaster_v3 import smart_auto_close_handovers as _smart_close
            # Collect done/archived task IDs from backlog for smart-close evaluation.
            _all_terminal: set[str] = set()
            for _epic in data.get("epics", []):
                for _t in _epic.get("tasks", []):
                    if _t.get("status") in ("done", "archived"):
                        _all_terminal.add(_t["id"])
            _all_terminal.add(task_id)  # the one we just transitioned
            smart_close_result = _smart_close(
                _backlog_path(),
                triggering_task_id=task_id,
                done_or_archived_ids=_all_terminal,
            )
            flipped_handovers = smart_close_result["closed"] + smart_close_result["flagged"]
        except Exception:
            flipped_handovers = []
        if flipped_handovers:
            data2 = _load()
            _sync_handover_index(data2, _backlog_path())
            _save(data2)
```

Apply the same replacement to `backlog_archive_task` (find `mark_task_handovers_complete` call inside `backlog_archive_task`, same pattern).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_handover_flag_open_reason.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_handover_flag_open_reason.py
git commit -m "feat(taskmaster): add flag_open_reason() and wire smart-close into complete/archive"
```

---

## Phase 3 — Migration

### Task 5: Add `migrate_handover_statuses()` data-layer function

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py` (add after `backfill_handover_status`)
- Test: `plugins/taskmaster/tests/test_handover_status_migration.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# plugins/taskmaster/tests/test_handover_status_migration.py
import sys
from pathlib import Path
import yaml

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

from taskmaster_v3 import (
    migrate_handover_statuses,
    read_handover,
    write_task_file,
)


def _setup(tmp_path):
    bp = tmp_path / "backlog.yaml"
    bp.write_text(yaml.safe_dump({"meta": {}, "epics": []}))
    hd = tmp_path / "handovers"
    hd.mkdir()
    return bp, hd


def _legacy(hd: Path, hid: str, status: str, superseded_by: str = "") -> None:
    fm: dict = {
        "id": hid, "date": "2025-01-01",
        "created": "2025-01-01T00:00:00+00:00",
        "tldr": "test",
        "task_ids": [], "session_kind": "end-of-day",
        "status": status,
        "status_changed": "2025-01-01T00:00:00+00:00",
        "status_user_set": False,
    }
    if superseded_by:
        fm["superseded_by"] = superseded_by
    write_task_file(hd / f"{hid}.md", fm, "body")


def test_migrate_todo_becomes_open(tmp_path):
    bp, hd = _setup(tmp_path)
    _legacy(hd, "2025-01-01-a", "todo")
    data = yaml.safe_load(bp.read_text())
    report = migrate_handover_statuses(data, bp, done_or_archived_ids=set())
    fm, _ = read_handover(bp, "2025-01-01-a")
    assert fm["status"] == "open"
    assert "2025-01-01-a" in report["migrated"]


def test_migrate_in_progress_becomes_open(tmp_path):
    bp, hd = _setup(tmp_path)
    _legacy(hd, "2025-01-01-b", "in-progress")
    data = yaml.safe_load(bp.read_text())
    migrate_handover_statuses(data, bp, done_or_archived_ids=set())
    fm, _ = read_handover(bp, "2025-01-01-b")
    assert fm["status"] == "open"


def test_migrate_done_with_superseded_by_becomes_superseded(tmp_path):
    bp, hd = _setup(tmp_path)
    _legacy(hd, "2025-01-01-old", "done", superseded_by="2025-01-02-new")
    data = yaml.safe_load(bp.read_text())
    migrate_handover_statuses(data, bp, done_or_archived_ids=set())
    fm, _ = read_handover(bp, "2025-01-01-old")
    assert fm["status"] == "superseded"


def test_migrate_done_eligible_for_smart_close_becomes_closed(tmp_path):
    """done handover whose task_ids are all terminal, no next_action, eligible kind → closed."""
    bp, hd = _setup(tmp_path)
    fm_data = {
        "id": "2025-01-01-eligible", "date": "2025-01-01",
        "created": "2025-01-01T00:00:00+00:00",
        "tldr": "finished",
        "task_ids": ["T-1"], "session_kind": "task-complete",
        "next_action": "",
        "status": "done",
        "status_changed": "2025-01-01T00:00:00+00:00",
        "status_user_set": False,
    }
    write_task_file(hd / "2025-01-01-eligible.md", fm_data, "body")
    data = yaml.safe_load(bp.read_text())
    migrate_handover_statuses(data, bp, done_or_archived_ids={"T-1"})
    fm, _ = read_handover(bp, "2025-01-01-eligible")
    assert fm["status"] == "closed"


def test_migrate_done_not_eligible_becomes_open(tmp_path):
    """done handover with next_action referencing live task → open (not closed)."""
    bp, hd = _setup(tmp_path)
    fm_data = {
        "id": "2025-01-01-live-ref", "date": "2025-01-01",
        "created": "2025-01-01T00:00:00+00:00",
        "tldr": "partial",
        "task_ids": ["T-1"], "session_kind": "task-complete",
        "next_action": "Start T-99",
        "status": "done",
        "status_changed": "2025-01-01T00:00:00+00:00",
        "status_user_set": False,
    }
    write_task_file(hd / "2025-01-01-live-ref.md", fm_data, "body")
    data = yaml.safe_load(bp.read_text())
    migrate_handover_statuses(data, bp, done_or_archived_ids={"T-1"})
    fm, _ = read_handover(bp, "2025-01-01-live-ref")
    assert fm["status"] == "open"


def test_migrate_idempotent(tmp_path):
    bp, hd = _setup(tmp_path)
    _legacy(hd, "2025-01-01-c", "todo")
    data = yaml.safe_load(bp.read_text())
    migrate_handover_statuses(data, bp, done_or_archived_ids=set())
    report2 = migrate_handover_statuses(data, bp, done_or_archived_ids=set())
    assert report2["migrated"] == []  # already migrated, no-op
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_handover_status_migration.py -v`
Expected: FAIL with `ImportError: cannot import name 'migrate_handover_statuses'`

- [ ] **Step 3: Implement `migrate_handover_statuses()`**

Add to `plugins/taskmaster/taskmaster_v3.py` after `backfill_handover_status()` (~line 1082):

```python
_LEGACY_TO_OPEN = frozenset({"todo", "in-progress"})

# Marker key in backlog.yaml root so migration is idempotent.
_MIGRATION_V2_KEY = "handover_status_v2_migrated"


def migrate_handover_statuses(
    backlog_data: dict[str, Any],
    backlog_path: Path,
    *,
    done_or_archived_ids: set[str],
) -> dict[str, list[str]]:
    """One-shot migration: translate old three-state enum to new three-state enum.

    Mapping:
      - "todo" | "in-progress"  →  "open"
      - "done" + superseded_by  →  "superseded"
      - "done" + smart-close eligible  →  "closed"
      - "done" + NOT eligible  →  "open"  (context still relevant)

    Idempotent: no-op if `_MIGRATION_V2_KEY` is truthy in backlog_data.
    Returns {"migrated": [list of ids changed]}.
    """
    if backlog_data.get(_MIGRATION_V2_KEY):
        return {"migrated": []}

    migrated: list[str] = []
    handovers_root = handover_dir(backlog_path)
    archive_root = handovers_root / "_archive"
    candidates: list[Path] = []
    if handovers_root.exists():
        candidates.extend(p for p in handovers_root.glob("*.md"))
    if archive_root.exists():
        candidates.extend(archive_root.rglob("*.md"))

    for path in candidates:
        try:
            fm, body = read_task_file(path)
        except (OSError, ValueError):
            continue

        old_status = fm.get("status", "")
        # Skip handovers already on the new enum.
        if old_status in HANDOVER_STATUSES:
            continue

        now = datetime.now(timezone.utc).isoformat(timespec="microseconds")

        if old_status in _LEGACY_TO_OPEN:
            fm["status"] = "open"
            fm["status_changed"] = now
            fm["status_reason"] = "migrated from legacy enum"
        elif old_status == "done":
            if fm.get("superseded_by"):
                fm["status"] = "superseded"
                fm["status_changed"] = now
                fm["status_reason"] = "migrated: had superseded_by"
            else:
                # Check smart-close eligibility inline (no file writes during check).
                task_ids: list[str] = fm.get("task_ids") or []
                next_action: str = (fm.get("next_action") or "").strip()
                session_kind: str = fm.get("session_kind") or ""
                all_terminal = all(t in done_or_archived_ids for t in task_ids)
                next_action_live = _next_action_references_live_tasks(
                    next_action, done_or_archived_ids
                )
                kind_eligible = session_kind in _AUTO_CLOSE_ELIGIBLE_KINDS
                if all_terminal and not next_action_live and kind_eligible:
                    fm["status"] = "closed"
                    fm["status_reason"] = "migrated: smart-close eligible"
                else:
                    fm["status"] = "open"
                    fm["status_reason"] = "migrated: context still relevant"
                fm["status_changed"] = now
        else:
            # Unknown status — default to open and flag.
            fm["status"] = "open"
            fm["status_changed"] = now
            fm["status_reason"] = f"migrated from unknown status {old_status!r}"

        write_task_file(path, fm, body)
        migrated.append(path.stem)

    backlog_data[_MIGRATION_V2_KEY] = True
    return {"migrated": migrated}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_handover_status_migration.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_handover_status_migration.py
git commit -m "feat(taskmaster): add migrate_handover_statuses() for todo/done → open/closed/superseded"
```

---

### Task 6: Write `scripts/migrate_handover_statuses.py` CLI

**Files:**
- Create: `plugins/taskmaster/scripts/migrate_handover_statuses.py`
- Test: run the script against a temp directory (manual verification step)

- [ ] **Step 1: Write the migration CLI script**

```python
#!/usr/bin/env python3
"""One-shot CLI: migrate handover status enum from v1 (todo/in-progress/done)
to v2 (open/closed/superseded).

Usage:
    python scripts/migrate_handover_statuses.py /path/to/project/.taskmaster/backlog.yaml

Dry-run (no writes):
    python scripts/migrate_handover_statuses.py /path/to/project/.taskmaster/backlog.yaml --dry-run
"""
import argparse
import sys
from pathlib import Path

# Allow running from the repo root or from within the plugin dir.
_PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PLUGIN_ROOT))

import yaml
from taskmaster_v3 import migrate_handover_statuses


def _collect_terminal_task_ids(backlog_data: dict) -> set[str]:
    terminal: set[str] = set()
    for epic in backlog_data.get("epics", []):
        for task in epic.get("tasks", []):
            if task.get("status") in ("done", "archived"):
                terminal.add(task["id"])
    return terminal


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate handover statuses to v2 enum.")
    parser.add_argument("backlog_yaml", help="Path to .taskmaster/backlog.yaml")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would change without writing files.")
    args = parser.parse_args()

    bp = Path(args.backlog_yaml).resolve()
    if not bp.exists():
        print(f"Error: backlog.yaml not found at {bp}", file=sys.stderr)
        sys.exit(1)

    data = yaml.safe_load(bp.read_text(encoding="utf-8")) or {}
    terminal_ids = _collect_terminal_task_ids(data)

    if args.dry_run:
        # Shallow clone to avoid mutating the marker; pass a copy of data.
        import copy
        data_copy = copy.deepcopy(data)
        report = migrate_handover_statuses(data_copy, bp, done_or_archived_ids=terminal_ids)
        print(f"[dry-run] Would migrate {len(report['migrated'])} handover(s):")
        for hid in report["migrated"]:
            print(f"  {hid}")
        return

    report = migrate_handover_statuses(data, bp, done_or_archived_ids=terminal_ids)
    # Persist the idempotency marker back to backlog.yaml.
    bp.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"Migrated {len(report['migrated'])} handover(s):")
    for hid in report["migrated"]:
        print(f"  {hid}")
    print("Done. Run `backlog_handover_resync` to rebuild the index.")


if __name__ == "__main__":
    main()
```

Save to: `plugins/taskmaster/scripts/migrate_handover_statuses.py`

- [ ] **Step 2: Verify the script is syntactically valid**

Run: `python -c "import ast; ast.parse(open('plugins/taskmaster/scripts/migrate_handover_statuses.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/scripts/migrate_handover_statuses.py
git commit -m "feat(taskmaster): add migrate_handover_statuses.py CLI script"
```

---

## Phase 4 — MCP surface changes

### Task 7: Update `backlog_handover_list` — accept new enum, add `flag_reason` in output

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py` — `backlog_handover_list`
- Test: `plugins/taskmaster/tests/test_handover_list_open_filter.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# plugins/taskmaster/tests/test_handover_list_open_filter.py
import sys
from pathlib import Path
import yaml

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

# Tests call the data layer directly to avoid the MCP tool's backlog-path lookup.
from taskmaster_v3 import (
    list_handover_ids,
    read_handover,
    update_handover_status,
    write_handover,
)
from taskmaster_v3 import HANDOVER_STATUSES


def _setup(tmp_path):
    bp = tmp_path / "backlog.yaml"
    bp.write_text(yaml.safe_dump({"meta": {}, "epics": []}))
    (tmp_path / "handovers").mkdir()
    return bp


def test_handover_statuses_used_in_list_filter_are_new_enum(tmp_path):
    """Verify the enum is new before testing filters."""
    assert "open" in HANDOVER_STATUSES
    assert "closed" in HANDOVER_STATUSES


def test_list_filter_status_open_returns_only_open(tmp_path):
    bp = _setup(tmp_path)
    open_id, _ = write_handover(bp, tldr="open one", session_kind="end-of-day")
    closed_id, _ = write_handover(bp, tldr="closed one", session_kind="end-of-day")
    update_handover_status(bp, handover_id=closed_id, status="closed")

    ids = list_handover_ids(bp)
    open_ids = [
        hid for hid in ids
        if read_handover(bp, hid)[0].get("status") == "open"
    ]
    assert open_id in open_ids
    assert closed_id not in open_ids


def test_list_filter_status_closed_returns_only_closed(tmp_path):
    bp = _setup(tmp_path)
    open_id, _ = write_handover(bp, tldr="open one", session_kind="end-of-day")
    closed_id, _ = write_handover(bp, tldr="closed one", session_kind="end-of-day")
    update_handover_status(bp, handover_id=closed_id, status="closed")

    ids = list_handover_ids(bp)
    closed_ids = [
        hid for hid in ids
        if read_handover(bp, hid)[0].get("status") == "closed"
    ]
    assert closed_id in closed_ids
    assert open_id not in closed_ids


def test_flag_reason_present_in_frontmatter_after_flag(tmp_path):
    from taskmaster_v3 import smart_auto_close_handovers
    bp = _setup(tmp_path)
    hid, _ = write_handover(
        bp,
        tldr="context handoff",
        session_kind="context-handoff",
        task_ids=["T-1"],
    )
    smart_auto_close_handovers(
        bp, triggering_task_id="T-1", done_or_archived_ids={"T-1"}
    )
    fm, _ = read_handover(bp, hid)
    assert fm.get("flag_reason"), "flag_reason should be set for flagged handovers"
    assert "context" in fm["flag_reason"].lower() or "session_kind" in fm["flag_reason"].lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_handover_list_open_filter.py -v`
Expected: FAIL on `test_handover_statuses_used_in_list_filter_are_new_enum` — enum still has `todo` if Task 1 not yet merged. (After Task 1 is done, only `test_flag_reason_present_in_frontmatter_after_flag` should fail, since `smart_auto_close_handovers` is added in Task 3.)

- [ ] **Step 3: Update `backlog_handover_list` status docstring and error message**

In `plugins/taskmaster/backlog_server.py`, find `backlog_handover_list` (~line 1681). Update the `status` parameter docstring and the validation error to reference the new enum:

```python
    status: str = "all",
    ...
    # OLD docstring line:
    #     status: One of todo, in-progress, done, or "all" (default). Filters ...
    # NEW:
    """
        ...
        status: One of open, closed, superseded, or "all" (default). Filters
            against the index entry — does not read every file.
        ...
    """
```

Also update the output lines in `backlog_handover_list` to append `flag_reason` when present:

Locate (~line 1740):
```python
    lines = []
    for e in entries:
        kind = e.get("session_kind", "")
        tag = f" [{kind}]" if kind else ""
        when = e.get("created") or e.get("date") or ""
        when_tag = f" ({when})" if when else ""
        lines.append(f"- {e['id']}{when_tag}{tag} — {e.get('tldr', '')}")
    return "\n".join(lines)
```

Replace with:

```python
    lines = []
    for e in entries:
        kind = e.get("session_kind", "")
        tag = f" [{kind}]" if kind else ""
        when = e.get("created") or e.get("date") or ""
        when_tag = f" ({when})" if when else ""
        flag = e.get("flag_reason", "")
        flag_tag = f" ▸ FLAGGED: {flag}" if flag else ""
        lines.append(f"- {e['id']}{when_tag}{tag} — {e.get('tldr', '')}{flag_tag}")
    return "\n".join(lines)
```

Also add `"flag_reason"` to `_HANDOVER_INDEX_FIELDS` in `taskmaster_v3.py` so it propagates into the index:

Find in `taskmaster_v3.py` (~line 1084):
```python
_HANDOVER_INDEX_FIELDS = (
    "id", "date", "created", "tldr", "next_action",
    "task_ids", "session_kind", "status",
)
```

Replace with:
```python
_HANDOVER_INDEX_FIELDS = (
    "id", "date", "created", "tldr", "next_action",
    "task_ids", "session_kind", "status", "flag_reason",
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_handover_list_open_filter.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_handover_list_open_filter.py
git commit -m "feat(taskmaster): update handover list output with flag_reason and new status enum"
```

---

### Task 8: Deprecate `backlog_handover_latest` as a thin alias

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py` — `backlog_handover_latest`
- Test: `plugins/taskmaster/tests/test_handover_latest_deprecated.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# plugins/taskmaster/tests/test_handover_latest_deprecated.py
"""Verify backlog_handover_latest emits a deprecation warning and returns
the same content as backlog_handover_list(status="open", limit=1)."""
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))


def test_backlog_handover_latest_docstring_says_deprecated():
    """Cheap static check — the tool's docstring must mention deprecation."""
    from backlog_server import backlog_handover_latest
    doc = backlog_handover_latest.__doc__ or ""
    assert "deprecated" in doc.lower() or "alias" in doc.lower(), (
        "backlog_handover_latest docstring must declare it deprecated"
    )


def test_backlog_handover_latest_returns_deprecation_warning_in_output(tmp_path, monkeypatch):
    """Integration check: returned string includes a deprecation notice."""
    import yaml
    from pathlib import Path as _Path

    bp = tmp_path / "backlog.yaml"
    bp.write_text(yaml.safe_dump({
        "meta": {}, "epics": [],
        "handovers": [
            {
                "id": "2026-01-01-test",
                "date": "2026-01-01",
                "created": "2026-01-01T00:00:00+00:00",
                "tldr": "latest test",
                "next_action": "",
                "task_ids": [],
                "session_kind": "end-of-day",
                "status": "open",
            }
        ],
    }))
    (tmp_path / "handovers").mkdir()

    # Patch the backlog path so the MCP tool finds our temp backlog.
    import backlog_server
    monkeypatch.setattr(backlog_server, "_backlog_path",
                        lambda: _Path(str(bp)))
    monkeypatch.setattr(backlog_server, "_ensure_handover_status_backfilled",
                        lambda: None)

    result = backlog_server.backlog_handover_latest()
    assert "deprecated" in result.lower() or "alias" in result.lower()
    assert "backlog_handover_list" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_handover_latest_deprecated.py -v`
Expected: FAIL — docstring has no deprecation mention, output has no deprecation notice.

- [ ] **Step 3: Rewrite `backlog_handover_latest` as a deprecation alias**

In `plugins/taskmaster/backlog_server.py`, replace the entire `backlog_handover_latest` function body (~line 1777):

```python
@mcp.tool()
def backlog_handover_latest() -> str:
    """[DEPRECATED] Alias for backlog_handover_list(status="open", limit=1, sort="created_desc").

    Use `backlog_handover_list(status="open")` instead — it returns all in-flight
    handover tracks, not just the newest one. This alias will be removed in the
    next major release.
    """
    bp = _backlog_path()
    if not bp.exists():
        return "No backlog found."
    _ensure_handover_status_backfilled()
    data = _load()
    entries = list(data.get("handovers") or [])
    open_entries = [e for e in entries if e.get("status") == "open"]
    # Sort by created descending; fall back to id for stable ordering.
    open_entries.sort(key=lambda e: (e.get("created") or e.get("id") or ""), reverse=True)

    deprecation_notice = (
        "[DEPRECATED] backlog_handover_latest is an alias — "
        "use backlog_handover_list(status=\"open\") for all open tracks.\n\n"
    )

    if not open_entries:
        return deprecation_notice + "No open handovers."

    e = open_entries[0]
    when_line = e.get("created") or e.get("date") or ""
    when_label = f" ({when_line})" if when_line else ""
    return (
        deprecation_notice
        + f"Latest open handover: {e['id']}{when_label}\n"
        + f"- TLDR: {e.get('tldr', '')}\n"
        + f"- Next: {e.get('next_action', '(none)')}\n"
        + f"- Tasks: {', '.join(e.get('task_ids') or []) or '(none)'}\n"
        + f"- Kind: {e.get('session_kind', 'end-of-day')}\n"
        + f"\nFetch body with `backlog_handover_get {e['id']}`.\n"
        + f"List all open tracks with `backlog_handover_list(status=\"open\")`."
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_handover_latest_deprecated.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_handover_latest_deprecated.py
git commit -m "feat(taskmaster): deprecate backlog_handover_latest as alias for handover_list(status=open)"
```

---

## Phase 5 — End-to-end smoke + changelog

### Task 9: End-to-end smoke test — full parallel-handover lifecycle

**Files:**
- Create: `plugins/taskmaster/tests/test_handover_parallel_smoke.py`

- [ ] **Step 1: Write the smoke test**

```python
# plugins/taskmaster/tests/test_handover_parallel_smoke.py
"""End-to-end smoke: create two parallel handovers, complete one task,
verify smart-close fires correctly, verify flagged reason surfaces."""
import sys
from pathlib import Path
import yaml

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

from taskmaster_v3 import (
    HANDOVER_STATUSES,
    flag_open_reason,
    list_handover_ids,
    migrate_handover_statuses,
    read_handover,
    smart_auto_close_handovers,
    update_handover_status,
    write_handover,
)


def _setup(tmp_path):
    bp = tmp_path / "backlog.yaml"
    bp.write_text(yaml.safe_dump({"meta": {}, "epics": []}))
    (tmp_path / "handovers").mkdir()
    return bp


def test_parallel_handover_full_lifecycle(tmp_path):
    bp = _setup(tmp_path)

    # 1. Two parallel tracks written.
    track_a_id, _ = write_handover(
        bp,
        tldr="Track A: rewriting auth middleware",
        session_kind="task-complete",
        task_ids=["T-1"],
        next_action="",
    )
    track_b_id, _ = write_handover(
        bp,
        tldr="Track B: exploring DB migration",
        session_kind="context-handoff",
        task_ids=["T-2"],
        next_action="Next: run T-3 migration script",
    )

    # Both start as open.
    fm_a, _ = read_handover(bp, track_a_id)
    fm_b, _ = read_handover(bp, track_b_id)
    assert fm_a["status"] == "open"
    assert fm_b["status"] == "open"

    # 2. T-1 completes — smart-close runs.
    done_ids = {"T-1"}
    result = smart_auto_close_handovers(
        bp,
        triggering_task_id="T-1",
        done_or_archived_ids=done_ids,
    )

    # Track A: all tasks done, no next_action, eligible kind → closed.
    assert track_a_id in result["closed"]
    fm_a_after, _ = read_handover(bp, track_a_id)
    assert fm_a_after["status"] == "closed"
    assert flag_open_reason(bp, track_a_id) is None  # closed → no flag

    # Track B: T-1 not in its task_ids → untouched.
    fm_b_after, _ = read_handover(bp, track_b_id)
    assert fm_b_after["status"] == "open"

    # 3. T-2 completes — Track B gets flagged (context-handoff + live T-3 ref).
    done_ids = {"T-1", "T-2"}
    result2 = smart_auto_close_handovers(
        bp,
        triggering_task_id="T-2",
        done_or_archived_ids=done_ids,
    )
    assert track_b_id in result2["flagged"]
    fm_b_flagged, _ = read_handover(bp, track_b_id)
    assert fm_b_flagged["status"] == "open"
    assert fm_b_flagged.get("flag_reason"), "flag_reason must be set"

    # 4. flag_open_reason surfaces the reason string.
    reason = flag_open_reason(bp, track_b_id)
    assert reason is not None

    # 5. Manually close Track B.
    update_handover_status(bp, handover_id=track_b_id, status="closed", reason="deferred T-3 to backlog")
    assert flag_open_reason(bp, track_b_id) is None  # closed now


def test_new_enum_values_are_valid_statuses():
    for s in ("open", "closed", "superseded"):
        assert s in HANDOVER_STATUSES


def test_migration_runs_on_legacy_data(tmp_path):
    bp = _setup(tmp_path)
    from taskmaster_v3 import write_task_file
    hd = tmp_path / "handovers"
    legacy_fm = {
        "id": "2025-06-01-legacy",
        "date": "2025-06-01",
        "created": "2025-06-01T00:00:00+00:00",
        "tldr": "old work",
        "task_ids": [],
        "session_kind": "end-of-day",
        "status": "todo",
        "status_changed": "2025-06-01T00:00:00+00:00",
        "status_user_set": False,
    }
    write_task_file(hd / "2025-06-01-legacy.md", legacy_fm, "body")
    data = yaml.safe_load(bp.read_text())
    report = migrate_handover_statuses(data, bp, done_or_archived_ids=set())
    assert "2025-06-01-legacy" in report["migrated"]
    fm, _ = read_handover(bp, "2025-06-01-legacy")
    assert fm["status"] == "open"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_handover_parallel_smoke.py -v`
Expected: FAIL — `smart_auto_close_handovers` and `flag_open_reason` don't exist yet. (After Tasks 3–4 are merged, re-run to confirm they now pass.) If running in sequence after all prior tasks: all 3 pass.

- [ ] **Step 3: Run full test suite for Plan B**

Run:
```bash
pytest plugins/taskmaster/tests/test_handover_status_enum_v2.py \
       plugins/taskmaster/tests/test_handover_smart_close.py \
       plugins/taskmaster/tests/test_handover_flag_open_reason.py \
       plugins/taskmaster/tests/test_handover_status_migration.py \
       plugins/taskmaster/tests/test_handover_latest_deprecated.py \
       plugins/taskmaster/tests/test_handover_list_open_filter.py \
       plugins/taskmaster/tests/test_handover_parallel_smoke.py \
       -v
```

Expected: All tests pass (no failures). If any fail, fix before committing.

- [ ] **Step 4: Commit**

```bash
git add plugins/taskmaster/tests/test_handover_parallel_smoke.py
git commit -m "test(taskmaster): end-to-end smoke for parallel handover lifecycle"
```

---

### Task 10: Update existing status-related tests for new enum

**Files:**
- Modify: `plugins/taskmaster/tests/test_handover_status_task_complete.py`
- Modify: `plugins/taskmaster/tests/test_handover_status_backfill.py`
- Modify: `plugins/taskmaster/tests/test_handover_status_update.py`
- Modify: `plugins/taskmaster/tests/test_handover_status_supersession.py`

- [ ] **Step 1: Check which existing tests use old enum values**

Run: `pytest plugins/taskmaster/tests/test_handover_status_task_complete.py plugins/taskmaster/tests/test_handover_status_backfill.py plugins/taskmaster/tests/test_handover_status_update.py plugins/taskmaster/tests/test_handover_status_supersession.py -v 2>&1 | head -60`

Expected: Several failures on assertions like `assert fm["status"] == "done"` or `assert fm["status"] == "todo"`.

- [ ] **Step 2: Update `test_handover_status_task_complete.py`**

In `plugins/taskmaster/tests/test_handover_status_task_complete.py`:

Replace every `assert fm["status"] == "done"` with `assert fm["status"] == "closed"`.

Replace `assert fm["status"] == "todo"` with `assert fm["status"] == "open"`.

Replace `assert fm["status"] == "in-progress"` with `assert fm["status"] == "open"`.

The `test_complete_respects_user_set_lock` test calls `update_handover_status(bp, handover_id=hid, status="in-progress")` — change that call to `update_handover_status(bp, handover_id=hid, status="open")`.

- [ ] **Step 3: Update `test_handover_status_backfill.py`**

In `plugins/taskmaster/tests/test_handover_status_backfill.py`:

In `test_backfill_sets_done_on_legacy_handovers`: replace `assert fm["status"] == "done"` with `assert fm["status"] == "open"`.

In `test_backfill_leaves_already_statused_handovers_alone`: the legacy fm has `"status": "todo"` — change to `"status": "open"` (the test is checking an already-statused handover is left alone, so it must already be on the new enum). Update the assertion from `assert fm_after["status"] == "todo"` to `assert fm_after["status"] == "open"`.

- [ ] **Step 4: Update `test_handover_status_supersession.py`**

In `plugins/taskmaster/tests/test_handover_status_supersession.py`:

Replace assertions `fm["status"] == "done"` on superseded handovers with `fm["status"] == "superseded"`.

Any setup code using `status="done"` in legacy fixtures should use `status="open"` if representing active handovers, or `status="superseded"` if representing superseded ones.

- [ ] **Step 5: Update `test_handover_status_update.py`**

In `plugins/taskmaster/tests/test_handover_status_update.py`:

Replace all status values in calls to `update_handover_status` and assertions:
- `"todo"` → `"open"`
- `"in-progress"` → `"open"` (both map to open now; choose `"closed"` when testing a terminal state)
- `"done"` → `"closed"`

Ensure any test that passes an invalid status to `update_handover_status` still expects a `ValueError` — the new enum is `("open", "closed", "superseded")` so invalid strings like `"todo"` trigger it.

- [ ] **Step 6: Run all status tests to verify they pass**

Run:
```bash
pytest plugins/taskmaster/tests/test_handover_status_task_complete.py \
       plugins/taskmaster/tests/test_handover_status_backfill.py \
       plugins/taskmaster/tests/test_handover_status_update.py \
       plugins/taskmaster/tests/test_handover_status_supersession.py \
       -v
```

Expected: All pass.

- [ ] **Step 7: Commit**

```bash
git add plugins/taskmaster/tests/test_handover_status_task_complete.py \
        plugins/taskmaster/tests/test_handover_status_backfill.py \
        plugins/taskmaster/tests/test_handover_status_update.py \
        plugins/taskmaster/tests/test_handover_status_supersession.py
git commit -m "test(taskmaster): update existing handover status tests for open/closed/superseded enum"
```

---

### Task 11: Verify no regressions in the full test suite

**Files:** No changes — run-only step.

- [ ] **Step 1: Run the full plugin test suite**

Run: `pytest plugins/taskmaster/tests/ -v --tb=short 2>&1 | tail -30`

Expected: All tests pass. Zero failures. If any test outside Plan B's scope fails, investigate before proceeding — do not commit with a red suite.

- [ ] **Step 2: If failures appear in unrelated tests**

Identify which tests reference old enum values (`todo`, `in-progress`, `done`) that weren't covered in Task 10:

Run: `grep -rn '"todo"\|"in-progress"\|== "done"' plugins/taskmaster/tests/ --include="*.py" -l`

For each file found, apply the same substitution logic as Task 10 (todo → open, in-progress → open, done as terminal → closed, done as superseded → superseded).

- [ ] **Step 3: Re-run full suite and confirm green**

Run: `pytest plugins/taskmaster/tests/ -v --tb=short 2>&1 | tail -10`
Expected: `X passed, 0 failed` where X ≥ the count before Plan B began.

---

### Task 12: Add changelog entry

**Files:**
- Modify: `plugins/taskmaster/CHANGELOG.md`

- [ ] **Step 1: Verify the CHANGELOG exists and read its current top**

Run: `head -20 plugins/taskmaster/CHANGELOG.md`

- [ ] **Step 2: Prepend the Plan B release entry**

Add at the top of `plugins/taskmaster/CHANGELOG.md` (after the `# Changelog` heading):

```markdown
## v3.X — Parallel Handovers (Plan B)

### Breaking changes

- `HANDOVER_STATUSES` enum renamed: `"todo"` → `"open"`, `"in-progress"` → `"open"`, `"done"` → `"closed"` or `"superseded"` depending on context. Run `scripts/migrate_handover_statuses.py` against any existing project before upgrading.

### New features

- **Smart auto-close rule:** When a task transitions to `done` or `archived`, open handovers that reference it are auto-closed only when all three criteria are met: (1) all `task_ids` are done/archived, (2) `next_action` is empty or references only done/archived tasks, (3) `session_kind` is `"task-complete"` or absent. Otherwise the handover stays open and is flagged with a human-readable `flag_reason`.
- **`flag_reason` field:** Flagged-but-open handovers carry a `flag_reason` string in frontmatter, surfaced in `backlog_handover_list` output with a `▸ FLAGGED:` prefix so start-session glance can show them inline.
- **`smart_auto_close_handovers()`:** New data-layer function in `taskmaster_v3.py`. Called automatically by `backlog_complete_task` and `backlog_archive_task`.
- **`flag_open_reason()`:** New data-layer helper. Returns the `flag_reason` string for a flagged open handover, or `None` if absent or already closed.
- **`migrate_handover_statuses()`:** New data-layer migration function. One-shot, idempotent. CLI at `scripts/migrate_handover_statuses.py`.

### Deprecations

- `backlog_handover_latest()` is deprecated. It now emits a deprecation notice in its output and delegates to `backlog_handover_list(status="open", limit=1)`. Use `backlog_handover_list(status="open")` for all in-flight tracks. Will be removed in the next major release.

### Internal

- `_HANDOVER_INDEX_FIELDS` now includes `"flag_reason"` so flagged entries propagate into `backlog.yaml` index.
- `apply_supersession()` sets `status = "superseded"` (was `"done"`).
- `backfill_handover_status()` stamps `status = "open"` (was `"done"`) on legacy handovers lacking the field.
- `_default_handover_status()` returns `"closed"` for `auto-stage` kind (was `"done"`), `"open"` for all others (was `"todo"`).
```

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/CHANGELOG.md
git commit -m "docs(taskmaster): changelog entry for Plan B parallel-handovers release"
```

---

## Completion checklist

Run this before declaring Plan B done:

```bash
pytest plugins/taskmaster/tests/test_handover_status_enum_v2.py \
       plugins/taskmaster/tests/test_handover_smart_close.py \
       plugins/taskmaster/tests/test_handover_flag_open_reason.py \
       plugins/taskmaster/tests/test_handover_status_migration.py \
       plugins/taskmaster/tests/test_handover_latest_deprecated.py \
       plugins/taskmaster/tests/test_handover_list_open_filter.py \
       plugins/taskmaster/tests/test_handover_parallel_smoke.py \
       plugins/taskmaster/tests/test_handover_status_task_complete.py \
       plugins/taskmaster/tests/test_handover_status_backfill.py \
       plugins/taskmaster/tests/test_handover_status_update.py \
       plugins/taskmaster/tests/test_handover_status_supersession.py \
       -v
```

Expected: All pass, zero failures.

Also verify the migration script syntax: `python -c "import ast; ast.parse(open('plugins/taskmaster/scripts/migrate_handover_statuses.py').read()); print('OK')"`
