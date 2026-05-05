# `taskmaster:handover` Skill — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `taskmaster:handover` skill that lets Claude draft a session handover (Claude-authored, user-approved) into `.taskmaster/handovers/{date}-{slug}.md`, with adaptive tier selection, six session kinds, auto-extraction of files-of-interest, and chained supersession — backed by the existing `write_handover`/`sync_handover_index` plumbing in `taskmaster_v3.py`.

**Architecture:** The skill is a markdown file at `plugins/taskmaster/skills/handover/SKILL.md` plus four reference docs and three body templates. All Claude-side decision logic (trigger detection, tier selection, auto-extraction, draft authoring) is prose; all file/frontmatter manipulation is delegated to `backlog_handover_create` (existing MCP tool) and a new `backlog_handover_supersede` tool. Backend changes are minimal: align `HANDOVER_KINDS` with the spec's 6-value set, validate `session_kind`, support `supersedes`/`superseded_by` frontmatter, and add an `apply_supersession()` helper that edits the old handover in-place.

**Tech Stack:** Python 3.11+ (FastMCP, PyYAML), pytest for backend tests, markdown/YAML frontmatter for the skill artifacts. No new dependencies.

---

## Spec & Reference Material

- **Spec:** `docs/superpowers/specs/2026-05-02-handover-skill-design.md`
- **Parent design:** `plugins/taskmaster/docs/design-v3-narrative-continuity.md` §2
- **Mining report:** `plugins/taskmaster/docs/v3-skills-enrichment.md`
- **Existing backend:** `plugins/taskmaster/taskmaster_v3.py` lines 450–627
- **Existing MCP tools:** `plugins/taskmaster/backlog_server.py` lines 1388–1527 (`backlog_handover_create`, `_list`, `_get`, `_latest`, `_resync`)
- **Real handover examples** (used as fixtures for tier validation):
  - `.fixture-kanban/.taskmaster/handovers/2026-04-29-plan3-graph-variant-shipped.md` (light)
  - `docs/superpowers/plans/2026-04-27-viewer-redesign-m1-complete-resume-m2.md` (standard / milestone-complete)
  - `docs/superpowers/plans/2026-04-27-viewer-redesign-execution-handoff.md` (full)
  - `docs/superpowers/plans/2026-05-02-v3-polish-013-handoff.md` (full)

## File Structure

**Created files:**
- `plugins/taskmaster/skills/handover/SKILL.md` — main skill (Claude-facing entry point)
- `plugins/taskmaster/skills/handover/references/session-kinds.md`
- `plugins/taskmaster/skills/handover/references/tier-selection.md`
- `plugins/taskmaster/skills/handover/references/auto-extraction.md`
- `plugins/taskmaster/skills/handover/references/supersession.md`
- `plugins/taskmaster/skills/handover/templates/light.md`
- `plugins/taskmaster/skills/handover/templates/standard.md`
- `plugins/taskmaster/skills/handover/templates/full.md`
- `plugins/taskmaster/tests/test_v3_handover.py`
- `plugins/taskmaster/tests/test_handover_skill_lint.py`

**Modified files:**
- `plugins/taskmaster/taskmaster_v3.py` — `HANDOVER_KINDS`, `HANDOVER_KIND_TO_VIEWER_KIND`, `write_handover`, new `_validate_session_kind`, new `apply_supersession`
- `plugins/taskmaster/backlog_server.py` — `backlog_handover_create` adds `supersedes` arg, new `backlog_handover_supersede` tool
- `plugins/taskmaster/skills/taskmaster/SKILL.md` — router row swapped to skill route
- `plugins/taskmaster/skills/end-session/SKILL.md` — v3-pre-2 step replaced with skill invocation

---

## Task 1: Backend — align `HANDOVER_KINDS` with spec 6-value set

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py:454` (`HANDOVER_KINDS`), `:466` (`HANDOVER_KIND_TO_VIEWER_KIND`)
- Test: `plugins/taskmaster/tests/test_v3_handover.py`

The spec defines six values: `end-of-day`, `context-handoff`, `milestone-complete`, `pivot`, `exploration`, `auto-stage`. The current code has four: `end-of-day`, `context-handoff`, `crash-recovery`, `auto-stage`. We're dropping `crash-recovery` (it never shipped to the docs and isn't referenced from any skill or test), and adding `milestone-complete`, `pivot`, `exploration`.

- [ ] **Step 1: Write the failing test**

Create `plugins/taskmaster/tests/test_v3_handover.py`:

```python
"""Tests for v3 handover write/validate/supersession plumbing."""
import pytest

from taskmaster_v3 import (
    HANDOVER_KINDS,
    HANDOVER_KIND_TO_VIEWER_KIND,
)


def test_handover_kinds_match_spec():
    assert set(HANDOVER_KINDS) == {
        "end-of-day",
        "context-handoff",
        "milestone-complete",
        "pivot",
        "exploration",
        "auto-stage",
    }
    # crash-recovery was removed — it never shipped to skills.
    assert "crash-recovery" not in HANDOVER_KINDS


def test_viewer_kind_mapping_covers_all_storage_kinds():
    for kind in HANDOVER_KINDS:
        assert kind in HANDOVER_KIND_TO_VIEWER_KIND, f"missing mapping for {kind}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_v3_handover.py -v`
Expected: FAIL — `set(HANDOVER_KINDS)` will contain `crash-recovery` and miss `milestone-complete`, `pivot`, `exploration`.

- [ ] **Step 3: Update `HANDOVER_KINDS` and the viewer mapping**

In `plugins/taskmaster/taskmaster_v3.py`, replace lines 454 and 466–471:

```python
HANDOVER_KINDS = (
    "end-of-day",
    "context-handoff",
    "milestone-complete",
    "pivot",
    "exploration",
    "auto-stage",
)

# Map storage-side handover kinds to viewer-side display kinds (spec §3.12).
HANDOVER_KIND_TO_VIEWER_KIND = {
    "end-of-day":         "wrap",
    "context-handoff":    "mid-task",
    "milestone-complete": "checkpoint",
    "pivot":              "mid-task",
    "exploration":        "standalone",
    "auto-stage":         "standalone",
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_v3_handover.py -v`
Expected: both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_v3_handover.py
git commit -m "feat(taskmaster): align HANDOVER_KINDS with spec 6-value set (v3-skills-002)"
```

---

## Task 2: Backend — validate `session_kind` in `write_handover`

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py:505` (`write_handover`)
- Test: `plugins/taskmaster/tests/test_v3_handover.py`

`write_handover` currently accepts any string for `session_kind`. The spec contract requires it be one of `HANDOVER_KINDS`. Reject silently-wrong values up front.

- [ ] **Step 1: Write the failing test**

Append to `plugins/taskmaster/tests/test_v3_handover.py`:

```python
from pathlib import Path
import yaml

from taskmaster_v3 import write_handover


def _make_backlog(tmp_path: Path) -> Path:
    bp = tmp_path / "backlog.yaml"
    bp.write_text(yaml.safe_dump({"epics": []}))
    (tmp_path / "handovers").mkdir()
    return bp


def test_write_handover_rejects_unknown_session_kind(tmp_path):
    bp = _make_backlog(tmp_path)
    with pytest.raises(ValueError, match="session_kind"):
        write_handover(bp, tldr="test", session_kind="not-a-real-kind")


def test_write_handover_accepts_each_known_kind(tmp_path):
    bp = _make_backlog(tmp_path)
    for kind in HANDOVER_KINDS:
        hid, _ = write_handover(
            bp, tldr=f"test {kind}", session_kind=kind,
        )
        assert hid.endswith(f"test-{kind}".lower().replace(" ", "-")[:40].rstrip("-")) or kind in hid
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_v3_handover.py::test_write_handover_rejects_unknown_session_kind -v`
Expected: FAIL — currently no validation, so `ValueError` is never raised.

- [ ] **Step 3: Add validation to `write_handover`**

In `plugins/taskmaster/taskmaster_v3.py`, modify `write_handover` (after the `if not tldr.strip()` check around line 522):

```python
    if session_kind not in HANDOVER_KINDS:
        raise ValueError(
            f"session_kind must be one of {HANDOVER_KINDS}, got {session_kind!r}"
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest plugins/taskmaster/tests/test_v3_handover.py -v`
Expected: both new tests PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_v3_handover.py
git commit -m "feat(taskmaster): validate session_kind in write_handover (v3-skills-002)"
```

---

## Task 3: Backend — `supersedes` / `superseded_by` / `branch` / `tip_commit` frontmatter + `apply_supersession` helper

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py:505` (`write_handover`)
- Test: `plugins/taskmaster/tests/test_v3_handover.py`

`write_handover` needs four new optional kwargs: `supersedes` (str | None), `branch` (str), `tip_commit` (str). When set, each lands in the new handover's frontmatter (spec §4). A new `apply_supersession(backlog_path, old_id, new_id)` helper edits the old handover in-place: prepends a callout block, sets `superseded_by` in its frontmatter.

- [ ] **Step 1: Write the failing test**

Append to `plugins/taskmaster/tests/test_v3_handover.py`:

```python
from taskmaster_v3 import apply_supersession, read_handover


def test_write_handover_records_supersedes_in_frontmatter(tmp_path):
    bp = _make_backlog(tmp_path)
    old_id, _ = write_handover(bp, tldr="old work", session_kind="milestone-complete")
    new_id, _ = write_handover(
        bp, tldr="newer work",
        session_kind="milestone-complete",
        supersedes=old_id,
    )
    fm, _ = read_handover(bp, new_id)
    assert fm["supersedes"] == old_id
    assert fm.get("superseded_by") is None


def test_write_handover_records_branch_and_tip_commit(tmp_path):
    bp = _make_backlog(tmp_path)
    hid, _ = write_handover(
        bp, tldr="branch test",
        branch="feature/taskmaster-v3",
        tip_commit="abc1234",
    )
    fm, _ = read_handover(bp, hid)
    assert fm["branch"] == "feature/taskmaster-v3"
    assert fm["tip_commit"] == "abc1234"


def test_write_handover_omits_optional_fields_when_unset(tmp_path):
    bp = _make_backlog(tmp_path)
    hid, _ = write_handover(bp, tldr="minimal")
    fm, _ = read_handover(bp, hid)
    # Optional fields should not appear in frontmatter when not passed.
    assert "branch" not in fm
    assert "tip_commit" not in fm
    assert "supersedes" not in fm
    assert "superseded_by" not in fm


def test_apply_supersession_edits_old_file(tmp_path):
    bp = _make_backlog(tmp_path)
    old_id, _ = write_handover(bp, tldr="old work", session_kind="milestone-complete",
                               body="Original body content.")
    new_id, _ = write_handover(bp, tldr="newer work", session_kind="milestone-complete")

    apply_supersession(bp, old_id=old_id, new_id=new_id)

    fm, body = read_handover(bp, old_id)
    assert fm["superseded_by"] == new_id
    assert body.startswith("> **SUPERSEDED")
    assert new_id in body
    # Original body must be preserved after the callout.
    assert "Original body content." in body


def test_apply_supersession_idempotent_on_already_superseded(tmp_path):
    bp = _make_backlog(tmp_path)
    old_id, _ = write_handover(bp, tldr="old", session_kind="milestone-complete")
    mid_id, _ = write_handover(bp, tldr="mid", session_kind="milestone-complete")
    new_id, _ = write_handover(bp, tldr="new", session_kind="milestone-complete")

    apply_supersession(bp, old_id=old_id, new_id=mid_id)
    # Re-applying with a newer id should update the pointer, not stack callouts.
    apply_supersession(bp, old_id=old_id, new_id=new_id)

    fm, body = read_handover(bp, old_id)
    assert fm["superseded_by"] == new_id
    assert body.count("> **SUPERSEDED") == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest plugins/taskmaster/tests/test_v3_handover.py -v`
Expected: FAIL — `write_handover` lacks `supersedes` kwarg, `apply_supersession` is undefined.

- [ ] **Step 3: Add `supersedes` / `branch` / `tip_commit` support to `write_handover`**

In `plugins/taskmaster/taskmaster_v3.py`, update `write_handover` signature and body:

```python
def write_handover(
    backlog_path: Path,
    *,
    tldr: str,
    next_action: str = "",
    body: str = "",
    task_ids: list[str] | None = None,
    session_kind: str = "end-of-day",
    when: str | None = None,
    context_size_at_write: str | None = None,
    supersedes: str | None = None,
    branch: str | None = None,
    tip_commit: str | None = None,
) -> tuple[str, Path]:
    # ... existing tldr / kind validation ...

    fm: dict[str, Any] = {
        "id": final_id,
        "date": when,
        "tldr": tldr.strip(),
        "next_action": (next_action or "").strip(),
        "task_ids": list(task_ids or []),
        "session_kind": session_kind,
    }
    if context_size_at_write:
        fm["context_size_at_write"] = context_size_at_write
    if supersedes:
        fm["supersedes"] = supersedes
    if branch:
        fm["branch"] = branch
    if tip_commit:
        fm["tip_commit"] = tip_commit

    write_task_file(target, fm, body)
    return final_id, target
```

- [ ] **Step 4: Add `apply_supersession` helper**

Add after `latest_handover_id` (around line 567 in `taskmaster_v3.py`):

```python
_SUPERSESSION_CALLOUT_PREFIX = "> **SUPERSEDED"


def apply_supersession(backlog_path: Path, *, old_id: str, new_id: str) -> Path:
    """Mark `old_id` as superseded by `new_id`.

    Edits the old handover in place:
      1. Sets `superseded_by: new_id` in the frontmatter.
      2. Prepends a callout block at the top of the body, OR rewrites the
         existing callout if one is already present (idempotent for a
         single old → many-newer chain).

    Returns the old handover's path. Raises FileNotFoundError if either id
    is missing on disk.
    """
    # Verify both files exist on disk.
    new_path = handover_path(backlog_path, new_id)
    if not new_path.exists():
        raise FileNotFoundError(new_id)
    old_path = handover_path(backlog_path, old_id)
    if not old_path.exists():
        raise FileNotFoundError(old_id)

    fm, body = read_handover(backlog_path, old_id)
    fm["superseded_by"] = new_id

    today = date.today().isoformat()
    callout = (
        f"> **SUPERSEDED {today} by [{new_id}](./{new_id}.md).**\n"
        f"> The next session should read the newer handover instead. "
        f"This file kept as a checkpoint reference.\n\n"
    )

    # Idempotent: if a SUPERSEDED callout already starts the body, replace it.
    body_lines = body.splitlines(keepends=True) if body else []
    if body_lines and body_lines[0].startswith(_SUPERSESSION_CALLOUT_PREFIX):
        # Drop the existing callout (callout block is two lines + a blank line).
        end = 0
        while end < len(body_lines) and body_lines[end].startswith(">"):
            end += 1
        # Skip the trailing blank line if present.
        if end < len(body_lines) and body_lines[end].strip() == "":
            end += 1
        body_after = "".join(body_lines[end:])
    else:
        body_after = body

    write_task_file(old_path, fm, callout + body_after)
    return old_path
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest plugins/taskmaster/tests/test_v3_handover.py -v`
Expected: all four supersession tests PASS.

- [ ] **Step 6: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_v3_handover.py
git commit -m "feat(taskmaster): add handover supersession (apply_supersession + supersedes/superseded_by) (v3-skills-002)"
```

---

## Task 4: MCP — wire `supersedes` / `branch` / `tip_commit` through `backlog_handover_create` + add `backlog_handover_supersede` tool

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py:1389` (`backlog_handover_create`)
- Modify: same file, add new tool after `backlog_handover_resync` (around line 1527)
- Test: `plugins/taskmaster/tests/test_v3_handover.py`

The skill drafts → calls `backlog_handover_create(supersedes=old_id)` → server does the supersession edit and the index sync. Splitting the supersession off as a standalone tool also lets users repair chains manually.

- [ ] **Step 1: Write the failing test**

Append to `plugins/taskmaster/tests/test_v3_handover.py`:

```python
import os
import sys

# Import the MCP server module the same way other tests do.
PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

import backlog_server  # noqa: E402


def _set_backlog_root(monkeypatch, bp: Path):
    monkeypatch.setattr(backlog_server, "ROOT", bp.parent)
    monkeypatch.setattr(backlog_server, "_backlog_path", lambda: bp)


def test_backlog_handover_create_with_supersedes(tmp_path, monkeypatch):
    bp = _make_backlog(tmp_path)
    _set_backlog_root(monkeypatch, bp)

    out_old = backlog_server.backlog_handover_create(
        tldr="old milestone", session_kind="milestone-complete",
    )
    old_id = out_old.splitlines()[0].split(": ", 1)[1].strip()

    out_new = backlog_server.backlog_handover_create(
        tldr="new milestone",
        session_kind="milestone-complete",
        supersedes=old_id,
    )
    assert "Handover written" in out_new

    # Old file should now have superseded_by + callout in body.
    fm, body = read_handover(bp, old_id)
    assert fm.get("superseded_by")  # set by the create call
    assert body.startswith("> **SUPERSEDED")


def test_backlog_handover_supersede_tool(tmp_path, monkeypatch):
    bp = _make_backlog(tmp_path)
    _set_backlog_root(monkeypatch, bp)

    out_old = backlog_server.backlog_handover_create(
        tldr="A", session_kind="milestone-complete",
    )
    old_id = out_old.splitlines()[0].split(": ", 1)[1].strip()
    out_new = backlog_server.backlog_handover_create(
        tldr="B", session_kind="milestone-complete",
    )
    new_id = out_new.splitlines()[0].split(": ", 1)[1].strip()

    msg = backlog_server.backlog_handover_supersede(old_id=old_id, new_id=new_id)
    assert old_id in msg and new_id in msg

    fm, _ = read_handover(bp, old_id)
    assert fm["superseded_by"] == new_id
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest plugins/taskmaster/tests/test_v3_handover.py -v`
Expected: FAIL — `supersedes` kwarg unknown to `backlog_handover_create`; `backlog_handover_supersede` undefined.

- [ ] **Step 3: Wire `supersedes` through `backlog_handover_create`**

In `plugins/taskmaster/backlog_server.py`, update the import (line 55-area) to also import `apply_supersession`:

```python
from taskmaster_v3 import (
    HANDOVER_KINDS,
    apply_supersession as _apply_supersession,
    # ... existing imports ...
)
```

Update `backlog_handover_create`:

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
) -> str:
    """Write a session handover — committed markdown artifact for cross-session
    continuity.

    ... (existing docstring) ...

    Args:
        ...
        supersedes: Optional id of an older handover this one supersedes. When
            set, the new handover records `supersedes:` in its frontmatter and
            the old handover gets a `superseded_by:` field plus a SUPERSEDED
            callout prepended to its body. Use for milestone-complete or pivot
            chains.
        branch: Optional git branch name. Lands in frontmatter when set.
        tip_commit: Optional tip commit SHA (short or long). Lands in
            frontmatter when set.
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

    if supersedes:
        try:
            _apply_supersession(bp, old_id=supersedes, new_id=hid)
        except FileNotFoundError:
            return (
                f"Handover written: {hid}\n"
                f"- File: {target.relative_to(ROOT)}\n"
                f"- WARNING: supersedes={supersedes} not found on disk; old "
                f"handover not updated."
            )

    data = _load()
    _sync_handover_index(data, bp)
    _save(data)

    return (
        f"Handover written: {hid}\n"
        f"- File: {target.relative_to(ROOT)}\n"
        f"- Index entries: {len(data.get('handovers') or [])}"
        + (f"\n- Superseded: {supersedes}" if supersedes else "")
    )
```

- [ ] **Step 4: Add `backlog_handover_supersede` tool**

After `backlog_handover_resync` (line 1527-area) in `backlog_server.py`:

```python
@mcp.tool()
def backlog_handover_supersede(old_id: str, new_id: str) -> str:
    """Mark an existing handover as superseded by another.

    Edits the old handover in place: prepends a SUPERSEDED callout, sets
    `superseded_by: <new_id>` in its frontmatter. Use this to repair a
    supersession chain after the fact (e.g., a handover was written without
    `supersedes=`, but should chain off a prior one).

    Both ids must exist on disk. Idempotent on the same `old_id` — calling it
    again with a newer `new_id` updates the pointer instead of stacking
    callouts.
    """
    bp = _backlog_path()
    if not bp.exists():
        return "No backlog found."
    try:
        old_path = _apply_supersession(bp, old_id=old_id, new_id=new_id)
    except FileNotFoundError as exc:
        return f"Error: handover not found ({exc})."
    return f"Superseded {old_id} → {new_id} ({old_path.name} updated)."
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest plugins/taskmaster/tests/test_v3_handover.py -v`
Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_v3_handover.py
git commit -m "feat(taskmaster): MCP supersession — handover_create supersedes arg + handover_supersede tool (v3-skills-002)"
```

---

## Task 5: Skill scaffold — directory + frontmatter

**Files:**
- Create: `plugins/taskmaster/skills/handover/SKILL.md`
- Create (empty placeholders to be filled in later tasks): `plugins/taskmaster/skills/handover/references/{session-kinds,tier-selection,auto-extraction,supersession}.md`
- Create: `plugins/taskmaster/skills/handover/templates/{light,standard,full}.md`

This task only puts down the SKILL.md frontmatter and the directory structure. Body and references are filled in subsequent tasks. The frontmatter `description:` field needs to be precise — the router and the auto-trigger heuristics both key off the description text.

- [ ] **Step 1: Create the directory tree**

Run:
```bash
mkdir -p plugins/taskmaster/skills/handover/references plugins/taskmaster/skills/handover/templates
```

- [ ] **Step 2: Write SKILL.md with frontmatter and section stubs**

Create `plugins/taskmaster/skills/handover/SKILL.md`:

```markdown
---
name: handover
description: "Write a Claude-drafted session handover into .taskmaster/handovers/. Invoke when the user says 'write a handover', 'save context', 'wrap up', 'for tomorrow', 'next time', 'remind future me', 'i'm at 300k', 'before compaction', 'context handoff', or 'continue where we left off' (writing context). Auto-extracts files of interest, what shipped, what's next; user reviews and approves; chained supersession for milestone-complete. This is the only correct way to write a handover — do not call backlog_handover_create directly."
---

# Handover

Capture a session into `.taskmaster/handovers/{date}-{slug}.md` so the next Claude session can resume without re-exploration.

## Why this skill exists

PROGRESS.md is the rolled-up project chronology. A handover is the **per-session full record** — context-injection optimisation for the next AI session. The skill drafts a tier-appropriate body (light / standard / full), auto-extracts files of interest, and writes through `backlog_handover_create`, which updates the index and (when `supersedes` is set) edits the prior handover in place. Calling `backlog_handover_create` directly skips tier selection, auto-extraction, and supersession chaining — always go through this skill.

## When to invoke

(Filled in Task 6.)

## Steps

(Filled in Task 6.)

## References

(Filled in Task 6.)
```

- [ ] **Step 3: Create empty reference and template stubs**

For each of these eight files, write a single-line stub so links resolve:

```bash
for f in references/session-kinds references/tier-selection references/auto-extraction references/supersession templates/light templates/standard templates/full; do
  echo "# (stub — populated in later task)" > plugins/taskmaster/skills/handover/$f.md
done
```

- [ ] **Step 4: Verify file structure exists**

Run: `ls plugins/taskmaster/skills/handover/ plugins/taskmaster/skills/handover/references/ plugins/taskmaster/skills/handover/templates/`
Expected output: `SKILL.md`, four reference `.md` files, three template `.md` files.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/skills/handover/
git commit -m "scaffold(taskmaster): handover skill directory + SKILL.md frontmatter (v3-skills-002)"
```

---

## Task 6: SKILL.md — main body

**Files:**
- Modify: `plugins/taskmaster/skills/handover/SKILL.md`

This is the operational core: trigger detection, decision tree, step-by-step flow, edge cases. Keep prose tight and lean on reference docs for detail.

- [ ] **Step 1: Replace the SKILL.md body**

Open `plugins/taskmaster/skills/handover/SKILL.md` and replace everything **after** the closing `---` of the frontmatter with:

````markdown
# Handover

Capture a session into `.taskmaster/handovers/{date}-{slug}.md` so the next Claude session can resume without re-exploration.

## Why this skill exists

PROGRESS.md is the rolled-up project chronology. A handover is the **per-session full record** — context-injection optimisation for the next AI session. The skill drafts a tier-appropriate body (light / standard / full), auto-extracts files of interest, and writes through `backlog_handover_create`, which updates the index and (when `supersedes` is set) edits the prior handover in place. Calling `backlog_handover_create` directly skips tier selection, auto-extraction, and supersession chaining — always go through this skill.

## When to invoke

Three trigger contexts:

1. **Explicit user invocation** — phrases listed in the skill description above.
2. **Auto-offer from end-session** — end-session calls into this skill when its v3-pre-2 heuristics fire (see end-session SKILL.md).
3. **Auto-offer mid-session** — when the orchestrator detects token-watch thresholds (≥200k or ≥270k), it offers this skill: *"You're approaching compaction. Write a handover now?"*

In all three cases the user is asked first. Never write a handover silently.

## Steps

### 1. Resolve session_kind

Pick exactly one value from `references/session-kinds.md`. The default is `end-of-day`. Override based on cues:

- User said "milestone done", "chunk complete", "ready for next plan" → `milestone-complete`
- User said "context handoff", "near compaction", "300k", "save before compact" → `context-handoff`
- User said "we changed direction", "pivoting", "new approach" → `pivot`
- Session had no in-flight task (no `in-progress` task touched, no commits to a feature) → `exploration`
- Auto-task or auto-epic invoked the skill mid-loop → `auto-stage`
- Otherwise → `end-of-day`

If unsure between two kinds, ask the user with `AskUserQuestion`.

### 2. Select a tier

Apply the heuristic table in `references/tier-selection.md`. The user can force a tier with `--light`, `--standard`, or `--full`; respect the override.

### 3. Auto-extract draft inputs

Walk the six sources in `references/auto-extraction.md` in order. Output a deduplicated, grouped list of paths under three buckets: **Touched** (sources 1, 2, 3 ∩ written), **Read** (source 3 ∩ read-only), **Relevant** (sources 4, 5 minus the first two).

For each path, write a one-line `what changed` and a one-line `why next session needs it`. **Never skip annotations** — bare paths defeat the optimisation.

### 4. Resolve `task_ids`

- `auto-stage`, `milestone-complete`, `pivot`, `context-handoff`: prefer the in-progress task's id; fall back to the task ids from any commits in this session.
- `end-of-day`: the in-progress task id (or last-touched task id).
- `exploration`: leave empty (`[]`). Do not invent a task id.

### 5. Determine `supersedes`

Set `supersedes = <prior_id>` when **all** of:

- `session_kind in {"milestone-complete", "pivot"}`
- The prior latest handover for the same `task_ids` exists
- That prior latest is also `milestone-complete` or `pivot`

Look up the prior with `backlog_handover_list(limit=10)` and pick the newest entry whose `task_ids` overlap. See `references/supersession.md` for the exact algorithm.

### 6. Draft the body from the tier template

Open the matching template under `templates/`:

- `templates/light.md` — light tier, ~10–30 lines
- `templates/standard.md` — standard tier, ~60–130 lines
- `templates/full.md` — full tier, ~150–200 lines

Fill it. Concrete content only — never leave a `{placeholder}`. If a section has no content (e.g., no pending commits, no dispatch templates), **delete the section** rather than leaving it empty.

### 7. Generate `tldr` and `next_action`

- `tldr`: one sentence, ≤ 100 chars, past-tense, what shipped.
- `next_action`: one sentence, ≤ 100 chars, imperative, what the next session should do first.

These two fields are the only thing the next session reads by default — they earn their tokens.

### 8. Present draft for user review

Show the user the assembled draft as one document with section labels. Then ask:

> "Looks good? I can drop sections, add files of interest, or rewrite the next-action."

Iterate until the user says it's good. Do **not** write the file before approval.

### 9. Write through `backlog_handover_create`

Call:

```
backlog_handover_create(
    tldr=...,
    next_action=...,
    body=<approved markdown body, no frontmatter>,
    task_ids=[...],
    session_kind="...",
    context_size_at_write="<optional, e.g. ~250k>",
    supersedes="<prior id or empty>",
    branch="<git branch from `git rev-parse --abbrev-ref HEAD`>",
    tip_commit="<git tip from `git rev-parse --short HEAD`>",
)
```

The server writes the file, syncs the index, and (if `supersedes` is set) edits the old handover in place.

### 10. Confirm

Echo back: *"Handover written: `<id>`. Next session can resume from this with `backlog_handover_latest`."*

If the response includes a `WARNING` line about `supersedes` not found, surface that to the user — do not hide it.

## Edge cases

- **Multiple in-progress tasks** — list them, ask the user which is the primary; use that as `task_ids[0]` and append the others.
- **No backlog** — `backlog_handover_create` returns `Error: no backlog found`. Tell the user to run `backlog_init` first.
- **Server sandbox at wrong cwd** — if the MCP tool error mentions a path mismatch, do not retry; tell the user to restart Claude Code from inside the project root and skip the write for this session (offer to print the draft instead so it isn't lost).
- **Auto-stage** — when invoked from `auto-task`, the orchestrator passes `session_kind="auto-stage"` and a stub-only body (frontmatter is the load-bearing part). Skip user review for this path.
- **`--light` override on a heavy session** — trim output to the light template, but still run auto-extraction; we don't want a `--light` flag to mask information the user wanted captured.

## References

- `references/session-kinds.md` — the six kinds, resume-load behavior, archive policy
- `references/tier-selection.md` — heuristic table, override flags
- `references/auto-extraction.md` — six sources, dedup grouping rules, regex specs
- `references/supersession.md` — chained-supersession algorithm
- `templates/light.md`, `templates/standard.md`, `templates/full.md` — body skeletons

## Spec

`docs/superpowers/specs/2026-05-02-handover-skill-design.md`
````

- [ ] **Step 2: Spot-check that all referenced files exist**

Run:
```bash
ls plugins/taskmaster/skills/handover/references/{session-kinds,tier-selection,auto-extraction,supersession}.md
ls plugins/taskmaster/skills/handover/templates/{light,standard,full}.md
```
Expected: all eight files print without error (they're stubs from Task 5; populated in 7–8).

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/skills/handover/SKILL.md
git commit -m "feat(taskmaster): handover skill — main SKILL.md flow (v3-skills-002)"
```

---

## Task 7: References — populate the four reference docs

**Files:**
- Modify (replace stub): `plugins/taskmaster/skills/handover/references/session-kinds.md`
- Modify (replace stub): `plugins/taskmaster/skills/handover/references/tier-selection.md`
- Modify (replace stub): `plugins/taskmaster/skills/handover/references/auto-extraction.md`
- Modify (replace stub): `plugins/taskmaster/skills/handover/references/supersession.md`

These are detail docs SKILL.md links to. Each one stands alone — read in isolation by Claude when the main flow says "see references/X.md".

- [ ] **Step 1: Write `references/session-kinds.md`**

Replace the stub at `plugins/taskmaster/skills/handover/references/session-kinds.md` with:

````markdown
# Handover Session Kinds

Six values, picked exactly once per handover. The kind drives both **what gets loaded on resume** and **how aggressively the file is archived**.

## The six kinds

| Kind | When to pick | Resume-load behaviour | Archive policy |
|---|---|---|---|
| `end-of-day` | Default. Wrap-up at the end of a working day. No special urgency. | Frontmatter only (`tldr`, `next_action`, `task_ids`). | FIFO past cap-30. |
| `context-handoff` | Pre-compaction safety capture (>200k tokens, or user said "near compaction"). | **Body loaded** — next session needs the full state because the current one is about to die. | FIFO past cap-30. |
| `milestone-complete` | A chunk shipped, a next chunk is ready (e.g., m1 → m2, plan3 → plan4). | **Body loaded** — dispatch templates and resume prompts are load-bearing. | Chained: a newer `milestone-complete` for the same `task_ids` supersedes the older one. |
| `pivot` | Direction change mid-flight (detour, plan switch). | **Body loaded** — captures *why* the change. | Chained: a newer `pivot` or `milestone-complete` for the same `task_ids` supersedes. |
| `exploration` | Investigation / infra / memory session, no task in flight (`task_ids: []`). | Frontmatter only. | FIFO past cap-30. |
| `auto-stage` | Written by `auto-task` during the loop (per-stage stub). | Frontmatter only — orchestrator already has state in `auto/state.json`. | Bulk-archived to `_archive/auto/` on epic/phase completion, replaced by an epic-level handover. |

## Choosing the right kind

The flowchart Claude follows:

1. Was the skill invoked by `auto-task`? → `auto-stage` and stop.
2. Did the user say "near compaction" / "300k" / "save before compact"? → `context-handoff` and stop.
3. Did the user say "milestone done" / "chunk complete" / "ready for next plan"? → `milestone-complete` and stop.
4. Did the user say "we changed direction" / "pivot" / "new approach"? → `pivot` and stop.
5. Was a task in flight this session (touched files, made commits)? → `end-of-day`.
6. No task in flight, no commits, just exploration / setup / memory work? → `exploration`.

If the user's words match more than one cue, ask via `AskUserQuestion` with the matching pair as options.

## Why this matters for the next session

Start-session and pick-task look at `session_kind` to decide whether to load only the frontmatter (cheap, ~200 tokens) or the full body (~2000 tokens). Picking the wrong kind costs tokens — `end-of-day` on a context-handoff hides critical context; `context-handoff` on a small wrap-up wastes load budget every session start.
````

- [ ] **Step 2: Write `references/tier-selection.md`**

Replace the stub at `plugins/taskmaster/skills/handover/references/tier-selection.md` with:

````markdown
# Handover Tier Selection

Three body-template tiers. Pick one based on the heuristic below. The user can force a tier with `--light`, `--standard`, or `--full`; respect the override.

## Tier sizes (rough targets)

| Tier | Lines | When to use |
|---|---|---|
| `light` | 10–30 | `end-of-day` or `exploration` with ≤ 30 turns and no in-flight task. |
| `standard` | 60–130 | Default for `milestone-complete` and `context-handoff`. Or any session 30–100 turns with an in-flight task. |
| `full` | 150–200 | `pivot`. Or any session > 100 turns. Or > 200k tokens. Or audit handovers that need full dispatch templates. |

## Selection flow

1. **User passed `--light` / `--standard` / `--full`** → use it. Stop.
2. **`session_kind == "auto-stage"`** → use `light` (frontmatter is the only thing that gets loaded anyway).
3. **`session_kind == "context-handoff"`** → use `standard` (body loaded; default detail level).
4. **`session_kind == "milestone-complete"`** → use `standard` unless the session has > 100 turns or > 200k tokens, then `full`.
5. **`session_kind == "pivot"`** → use `full` (the *why* is load-bearing).
6. **`session_kind == "exploration"`** → use `light`.
7. **`session_kind == "end-of-day"`**:
    - ≤ 30 turns, no in-flight task → `light`
    - 30–100 turns, in-flight task → `standard`
    - \> 100 turns or > 200k tokens → `full`

## Token-count and turn-count estimation

These are heuristics, not exact:

- **Turn count** — count user/assistant message pairs in the current conversation. The orchestrator passes this number in if it knows; otherwise estimate from the conversation length.
- **Token count** — `len(conversation_text) / 4` is a rough byte-to-token ratio. Good enough for the > 200k threshold; do not promise precision.

## What `--light` doesn't change

A `--light` override on a heavy session trims the **output**, not the **inputs**. Auto-extraction still runs, supersession still chains; we just write a shorter body. This avoids losing information the user explicitly opted out of writing down.
````

- [ ] **Step 3: Write `references/auto-extraction.md`**

Replace the stub at `plugins/taskmaster/skills/handover/references/auto-extraction.md` with:

````markdown
# Handover Auto-Extraction Sources

Six input sources, walked in order, deduplicated, grouped into three buckets.

## The six sources

1. **`git status` + `git diff --stat`** — uncommitted state, line-count deltas. Drives the "Pending commits" section in `full` tier.

2. **`git log {merge_base}..HEAD --name-only`** — files committed during this session, commit messages, SHAs. Use the branch's merge-base with the default branch (or `HEAD~N` for last N commits if no clear branch boundary). Drives the "What shipped this session" table in `standard` and `full` tiers.

3. **Conversation tool-call history** — Read / Edit / Write paths from this session. **The orchestrator passes this in** when invoking the skill — the skill itself does not scrape its own context. If the orchestrator can't pass it, sources 1, 2, 4, 5 still work; source 3 falls back to empty.

4. **Task body anchors** — `task.anchors`, `task.docs.spec`, `task.docs.plan`, `task.related_handovers`, `task.related_lessons`, `task.related_issues`. Pulled via `backlog_get_task(task_id)` for each task in `task_ids`. Drives the **Relevant** group.

5. **Conversation text regex** — paths matching the pattern `[a-zA-Z_][a-zA-Z0-9_/.-]*\.(md|py|js|css|html|yaml|json|ts|tsx|jsx)` mentioned anywhere in the conversation. Includes paths in code blocks and inline `code spans`.

6. **Conversation numbered-step regex** — lines matching `^\d+\.\s+` that read like next-session actions (verb-led: "Run X", "Read Y", "Continue with Z"). Drives the "What's next" section in `standard` and `full` tiers.

## Grouping into three buckets

After all six sources are collected, deduplicate paths and assign each one to exactly one of:

- **Touched** = (sources 1, 2, 3) ∩ written/edited
- **Read** = source 3 ∩ read-only (i.e., paths Claude `Read` but never `Edit`/`Write`)
- **Relevant** = (sources 4, 5) − (Touched ∪ Read)

A path that appears in source 5 but is also in source 3-edited goes to **Touched**, not **Relevant**. The grouping is mutually exclusive — every path lives in exactly one bucket.

## Annotation requirement

For every path written into the handover, Claude writes:

- A one-line **what changed** (Touched), **why we read it** (Read), or **what it is** (Relevant).
- A one-line **why next session needs it**.

A path with no annotation is worse than not including the path at all — it forces the next session to re-explore. **Never skip annotations.**

## What gets dropped

- Paths under `node_modules/`, `__pycache__/`, `.venv/`, `.git/`, `dist/`, `build/`, `.snapshots/`, `.taskmaster/auto/`.
- Paths the regex caught from prose that are obviously not real (e.g., `example.com`, `foo.bar.baz`).
- Paths the user said to ignore in this session.

When in doubt, keep the path and annotate why it might matter — over-inclusion is cheap, under-inclusion makes the next session re-explore.
````

- [ ] **Step 4: Write `references/supersession.md`**

Replace the stub at `plugins/taskmaster/skills/handover/references/supersession.md` with:

````markdown
# Chained Handover Supersession

When a new handover replaces an older one for the same task line of work, we **chain** them: the new one points back at the old (`supersedes:`); the old one is edited in place to point at the new (`superseded_by:`) and gets a `SUPERSEDED` callout prepended to its body.

This automates what real handovers like `2026-04-27-viewer-redesign-m1-complete-resume-m2.md` do manually at the top of the file.

## When to chain

Set `supersedes = <prior_id>` if **all** of:

1. The new handover's `session_kind` is `milestone-complete` or `pivot`.
2. There is a prior handover whose `task_ids` overlap with the new handover's `task_ids` (intersection non-empty).
3. That prior handover's `session_kind` is also `milestone-complete` or `pivot`.

If multiple priors qualify, pick the **newest** by `date`.

## How to find the prior

```
candidates = backlog_handover_list(limit=10)
prior = None
for entry in candidates:                     # newest-first
    if entry["session_kind"] not in {"milestone-complete", "pivot"}:
        continue
    if not (set(entry["task_ids"]) & set(new_task_ids)):
        continue
    prior = entry["id"]
    break
```

If no prior matches, do **not** set `supersedes`. The chain starts fresh.

## What the server does when `supersedes` is set

`backlog_handover_create(supersedes=old_id, ...)` calls `apply_supersession(old_id=..., new_id=...)` after writing the new file. That helper:

1. Reads the old handover.
2. Sets `superseded_by: <new_id>` in its frontmatter.
3. Prepends a callout block to the body:
   ```
   > **SUPERSEDED YYYY-MM-DD by [<new_id>](./<new_id>.md).**
   > The next session should read the newer handover instead. This file kept as a checkpoint reference.
   ```
4. Writes the old file back.

If a SUPERSEDED callout already starts the body (the file was previously superseded by an even older handover, and we're now superseding by a newer one), the helper **replaces** the callout in place rather than stacking. Idempotent on the same `old_id`.

## What to do if `supersedes` resolution fails

If `backlog_handover_list` returns nothing useful (e.g., this is the first handover in the project, or no prior matches the task), simply omit `supersedes` from the create call. The chain starts here.

If `backlog_handover_create` returns a `WARNING: supersedes=... not found on disk` line, surface it to the user. The new handover was still written; the old one just didn't get its callout. Offer to fix manually with `backlog_handover_supersede(old_id=..., new_id=...)` if the user wants to repair the chain.
````

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/skills/handover/references/
git commit -m "feat(taskmaster): handover skill reference docs (kinds, tiers, extraction, supersession) (v3-skills-002)"
```

---

## Task 8: Templates — light, standard, full

**Files:**
- Modify (replace stub): `plugins/taskmaster/skills/handover/templates/light.md`
- Modify (replace stub): `plugins/taskmaster/skills/handover/templates/standard.md`
- Modify (replace stub): `plugins/taskmaster/skills/handover/templates/full.md`

Body skeletons Claude fills in. Sections with no content get **deleted**, not left empty.

- [ ] **Step 1: Write `templates/light.md`**

Replace stub at `plugins/taskmaster/skills/handover/templates/light.md` with:

````markdown
<!--
LIGHT TIER TEMPLATE — target ~10–30 lines.
Used for end-of-day / exploration with ≤30 turns and no in-flight task.
Drop any section with no content. Never leave {placeholders}.
-->

{One-paragraph TLDR — what the session was, what shipped or what was learned. Past tense, freeform prose, ~3–6 sentences.}

**What shipped:**
- {Bullet — accomplishment or finding}
- {Bullet}
- {Bullet}

**Next:**
- {One bullet — concrete next-session action OR open question to resolve.}
````

- [ ] **Step 2: Write `templates/standard.md`**

Replace stub at `plugins/taskmaster/skills/handover/templates/standard.md` with:

````markdown
<!--
STANDARD TIER TEMPLATE — target ~60–130 lines.
Default for milestone-complete / context-handoff, or 30–100-turn sessions with an in-flight task.
Drop any section with no content. Never leave {placeholders}.
-->

## Resume prompt

> {Verbatim text the next session can paste. Include: cd command if a worktree, branch name, where to start (which file/section/task), and any hard rules ("don't push", "tests before commit").}

## Where execution stands

{Status snapshot: branch name, tip commit hash and message, what just landed, test counts (X/Y passing), server state if relevant. 4–10 lines.}

## What shipped this session

| # | What | Where |
|---|------|-------|
| 1 | {accomplishment} | {commit hash / file path / docs path} |
| 2 | {accomplishment} | {commit hash / file path / docs path} |

## What's next

1. {Numbered next-session action — verb-led, specific.}
2. {Numbered next-session action.}
3. {Numbered next-session action.}

## Files of interest

| Group | Path | What | Why next session needs it |
|---|---|---|---|
| Touched | {path} | {what changed this session} | {why next session reads this} |
| Read | {path} | (referenced for understanding) | {why} |
| Relevant | {path} | (not touched but next-session-relevant) | {why} |

## Important non-obvious things

1. {Numbered gotcha, hidden invariant, environment quirk the next session WILL hit.}
2. {Same.}
````

- [ ] **Step 3: Write `templates/full.md`**

Replace stub at `plugins/taskmaster/skills/handover/templates/full.md` with:

````markdown
<!--
FULL TIER TEMPLATE — target ~150–200 lines.
Used for pivot, audit, complex multi-pass, or sessions >100 turns / >200k tokens.
Drop any section with no content. Never leave {placeholders}.
-->

## Resume prompt

> {Verbatim text the next session can paste. cd, branch, where to start, hard rules. Be precise — this is the load-bearing field.}

## Where execution stands

{Branch, tip commit, last-landed commits, test counts, server state, environment state, blockers if any. 8–15 lines.}

## What shipped this session

| # | What | Where |
|---|------|-------|
| 1 | {accomplishment} | {commit hash / file / docs} |
| 2 | {accomplishment} | {commit hash / file / docs} |

## What's next

1. {Numbered next-session action.}
2. {Numbered next-session action.}
3. {Numbered next-session action.}

## Files of interest

| Group | Path | What | Why next session needs it |
|---|---|---|---|
| Touched | {path} | {what changed} | {why} |
| Read | {path} | (referenced) | {why} |
| Relevant | {path} | (not touched, relevant) | {why} |

## Important non-obvious things

1. {Numbered gotcha, hidden invariant, environment quirk.}
2. {Same.}

## Pending commits

{Bash commands ready to run, in code blocks. Auto-generated from `git status` if uncommitted state exists. Drop this section if working tree is clean.}

```bash
git add <files>
git commit -m "<message>"
```

## Per-task dispatch templates

{Verbatim subagent prompts the next session can use. Only emit when orchestration was the work (e.g., dispatching parallel subagents was the point of this session). Drop otherwise.}

### Dispatch template — {task_id}

```
{verbatim subagent prompt}
```
````

- [ ] **Step 4: Commit**

```bash
git add plugins/taskmaster/skills/handover/templates/
git commit -m "feat(taskmaster): handover skill body templates (light/standard/full) (v3-skills-002)"
```

---

## Task 9: Retrofit `taskmaster:taskmaster` router

**Files:**
- Modify: `plugins/taskmaster/skills/taskmaster/SKILL.md:33–35`

Three rows in the v3 section currently route handover intents to `Direct tool call — backlog_handover_create`. Update the **write** intent to route to the new skill; the **read** intents stay direct.

- [ ] **Step 1: Edit the router rows**

In `plugins/taskmaster/skills/taskmaster/SKILL.md`, find:

```
| (v3) "Write a handover", "wrap up for tomorrow", "context handoff", "save where I left off" | Direct tool call — `backlog_handover_create` (or include in `taskmaster:end-session`) |
```

Replace with:

```
| (v3) "Write a handover", "wrap up for tomorrow", "context handoff", "save where I left off", "for tomorrow", "remind future me", "before compaction" | `taskmaster:handover` |
```

Leave the `backlog_handover_latest` and `backlog_handover_list` rows unchanged — those are read paths, not skill paths.

- [ ] **Step 2: Update the v3 disambiguation note**

In the same file, find the `v3 disambiguation` section's `handover vs end-session` bullet:

```
- **handover vs end-session:** end-session is a *task transition* ... When the user says "wrap up", route to `taskmaster:end-session` which itself offers handover write. When they say "context handoff" or "for tomorrow", call `backlog_handover_create` directly without transitioning any task.
```

Replace the last sentence with:

```
When they say "context handoff" or "for tomorrow", invoke `taskmaster:handover` directly — it writes the handover without transitioning any task.
```

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/skills/taskmaster/SKILL.md
git commit -m "feat(taskmaster): route handover-write intents to the handover skill (v3-skills-002)"
```

---

## Task 10: Retrofit `taskmaster:end-session`

**Files:**
- Modify: `plugins/taskmaster/skills/end-session/SKILL.md:24–52` (the v3-pre-2 step)

Currently end-session inlines all the handover offer logic (the `AskUserQuestion` block + the four-section body draft + the `backlog_handover_create` call). Replace with an invocation of the new skill.

- [ ] **Step 1: Replace the v3-pre-2 step**

In `plugins/taskmaster/skills/end-session/SKILL.md`, find the entire `**v3-pre-2: Handover offer.**` block (approximately lines 24–52, ending at the line `   - The created handover id will surface at the next session start via \`backlog_handover_latest\`.`).

Replace it with:

```markdown
**v3-pre-2: Handover offer.** Decide whether to offer a session handover. Auto-offer when ANY of:
   - Session length > 60 turns of conversation.
   - Conversation context estimate > 200k tokens.
   - A task is still in flight (status `in-progress` or `auto/state.json` cursor non-null).
   - User said anything like "for tomorrow", "remind me next time", "context handoff", "pick this up later".

If offering, ask:

   ```
   AskUserQuestion({
     questions: [{
       question: "Write a session handover? It captures decisions, blockers, and where to start next session.",
       header: "Handover",
       multiSelect: false,
       options: [
         { label: "Yes, end-of-day handover", description: "Standard wrap-up" },
         { label: "Yes, context handoff", description: "Near compaction — flag this as such" },
         { label: "Yes, milestone-complete", description: "Chunk done, next chunk ready to dispatch" },
         { label: "Skip", description: "Lightweight session, no handover needed" }
       ]
     }]
   })
   ```

If user picks yes, **invoke the `taskmaster:handover` skill** with the chosen `session_kind`. End-session does NOT draft the body itself — the handover skill owns tier selection, auto-extraction, and supersession chaining. End-session continues regardless of the handover skill's outcome.
```

- [ ] **Step 2: Spot-check that `auto-mode interaction` reference still works**

The file's `Auto-mode interaction (v3)` section (around line 146) still mentions `backlog_handover_create(session_kind="crash-recovery")`. Since `crash-recovery` was dropped in Task 1, update that line.

Find:

```
- If the user invokes /end-session manually mid-auto-run, ask: "There's an active auto run on `<target>`. Pause and write a handover, or abort the run?" — `backlog_auto_abort` clears the state, `backlog_handover_create(session_kind="crash-recovery")` preserves it.
```

Replace with:

```
- If the user invokes /end-session manually mid-auto-run, ask: "There's an active auto run on `<target>`. Pause and write a handover, or abort the run?" — `backlog_auto_abort` clears the state, invoking `taskmaster:handover` with `session_kind="context-handoff"` preserves it.
```

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/skills/end-session/SKILL.md
git commit -m "feat(taskmaster): end-session delegates handover write to the skill (v3-skills-002)"
```

---

## Task 11: Lint test for skill structure

**Files:**
- Create: `plugins/taskmaster/tests/test_handover_skill_lint.py`

Black-box validation that the skill scaffolding is intact: SKILL.md has well-formed frontmatter, all `references/` and `templates/` files referenced by SKILL.md exist on disk, and the description contains the agreed trigger phrases so the router will pick it up.

- [ ] **Step 1: Write the test**

Create `plugins/taskmaster/tests/test_handover_skill_lint.py`:

```python
"""Lint checks for the taskmaster:handover skill scaffolding."""
from pathlib import Path
import re

import yaml

SKILL_DIR = Path(__file__).resolve().parents[1] / "skills" / "handover"


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
    assert fm.get("name") == "handover"
    assert "description" in fm and isinstance(fm["description"], str)
    # Description must be ≥ 100 chars to actually convey the trigger surface.
    assert len(fm["description"]) >= 100


def test_description_contains_key_trigger_phrases():
    fm = _read_frontmatter(SKILL_DIR / "SKILL.md")
    desc = fm["description"].lower()
    must_have = [
        "write a handover",
        "wrap up",
        "for tomorrow",
        "context handoff",
        "before compaction",
    ]
    missing = [p for p in must_have if p not in desc]
    assert not missing, f"description is missing trigger phrases: {missing}"


def test_all_referenced_files_exist():
    expected_refs = [
        SKILL_DIR / "references" / "session-kinds.md",
        SKILL_DIR / "references" / "tier-selection.md",
        SKILL_DIR / "references" / "auto-extraction.md",
        SKILL_DIR / "references" / "supersession.md",
        SKILL_DIR / "templates" / "light.md",
        SKILL_DIR / "templates" / "standard.md",
        SKILL_DIR / "templates" / "full.md",
    ]
    missing = [p for p in expected_refs if not p.exists()]
    assert not missing, f"missing referenced files: {missing}"


def test_references_are_not_stubs():
    # Each reference / template should be > 20 non-blank lines —
    # a one-line stub means Task 7/8 wasn't completed.
    for ref in (SKILL_DIR / "references").iterdir():
        non_blank = [ln for ln in ref.read_text(encoding="utf-8").splitlines() if ln.strip()]
        assert len(non_blank) > 20, f"reference looks like a stub: {ref}"
    for tpl in (SKILL_DIR / "templates").iterdir():
        non_blank = [ln for ln in tpl.read_text(encoding="utf-8").splitlines() if ln.strip()]
        assert len(non_blank) > 5, f"template looks like a stub: {tpl}"


def test_skill_md_links_resolve():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    # Find all relative references like `references/foo.md` or `templates/bar.md`.
    refs = re.findall(r"`(references/[A-Za-z0-9_-]+\.md|templates/[A-Za-z0-9_-]+\.md)`", text)
    assert refs, "SKILL.md does not reference any references/ or templates/ files"
    missing = [r for r in refs if not (SKILL_DIR / r).exists()]
    assert not missing, f"SKILL.md links do not resolve: {missing}"
```

- [ ] **Step 2: Run the test**

Run: `pytest plugins/taskmaster/tests/test_handover_skill_lint.py -v`
Expected: all six tests PASS.

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/tests/test_handover_skill_lint.py
git commit -m "test(taskmaster): lint checks for handover skill scaffolding (v3-skills-002)"
```

---

## Task 12: Dogfood — write a real handover with the skill

**Files:**
- No new files. Validates the full skill end-to-end against the v3 worktree's actual `.taskmaster/handovers/` directory.

The acceptance criterion in the spec is: *"One end-to-end dogfood: write a handover for the session that built this skill, into the v3 worktree, and confirm a fresh Claude session can resume from it without re-exploration."* This task is that dogfood.

- [ ] **Step 1: Run all backend + lint tests**

Run: `pytest plugins/taskmaster/tests/test_v3_handover.py plugins/taskmaster/tests/test_handover_skill_lint.py -v`
Expected: all tests PASS. If anything fails, stop and fix before dogfooding.

- [ ] **Step 2: Invoke the skill in this session**

In Claude Code:
1. Say: *"Write a handover for the v3-skills-002 work."*
2. The router should pick `taskmaster:handover`.
3. The skill should:
   - Pick `session_kind: milestone-complete` (the skill itself is shipping).
   - Pick `tier: standard` (~60–130 lines feels right for shipping a skill + tests).
   - Auto-extract files from this session's tool-call history.
   - Find the prior `2026-05-02-handover-skill-design` handover (if it exists) and chain via `supersedes`.
   - Draft the body and present for review.
4. Approve the draft.

- [ ] **Step 3: Verify the file landed**

Run:
```bash
ls .taskmaster/handovers/
```
Expected: a new `2026-05-02-*-v3-skills-002-*.md` file exists.

Run:
```bash
head -20 .taskmaster/handovers/<new_id>.md
```
Expected: frontmatter contains `session_kind: milestone-complete`, `task_ids: [v3-skills-002]`, and (if a prior chained) `supersedes: <prior_id>`.

- [ ] **Step 4: Verify the index updated**

Call `backlog_handover_latest` (in Claude Code).
Expected: the latest line names the new id.

Call `backlog_handover_list(limit=5)`.
Expected: the new id is the first entry, with `[milestone-complete]` tag.

- [ ] **Step 5: Verify supersession (if a prior was chained)**

Open the prior handover file (whatever `supersedes` resolved to). The body should now start with:

```
> **SUPERSEDED 2026-05-02 by [<new_id>](./<new_id>.md).**
> The next session should read the newer handover instead. ...
```

The frontmatter should contain `superseded_by: <new_id>`.

- [ ] **Step 6: Cold-start resume check**

Open a fresh Claude Code session in the same worktree. Say: *"continue where we left off."*

Expected: start-session calls `backlog_handover_latest`, surfaces the handover's tldr + next_action, and (because `session_kind == milestone-complete`) recommends loading the body. The next session can act on the resume prompt without reading anything else.

If start-session does NOT surface the handover, that's a separate retrofit task (`v3-skills-007`) — note the gap and stop. The skill itself shipped; the orchestrator wiring is the next sub-task.

- [ ] **Step 7: Commit the dogfood handover**

```bash
git add .taskmaster/handovers/
git commit -m "chore(taskmaster): dogfood handover for v3-skills-002 ship (v3-skills-002)"
```

- [ ] **Step 8: Mark `v3-skills-002` as in-review**

In Claude Code, invoke `taskmaster:end-session` with `target_status=in-review`. The user manually validates the dogfood handover before flipping to `done`.

---

## Acceptance criteria (cross-check against spec §15)

After all tasks complete, verify each spec acceptance criterion:

- [ ] `taskmaster:handover` skill exists at `plugins/taskmaster/skills/handover/SKILL.md`. **(Task 5–6)**
- [ ] Trigger phrases from spec §2.1 reliably invoke the skill. **(Task 6 description; Task 9 router; Task 12 dogfood)**
- [ ] Auto-offer heuristics from spec §2.2 fire correctly when end-session runs. **(Task 10 retrofit)**
- [ ] All six `session_kind` values produce correct body shapes. **(Task 1 + Task 7 session-kinds.md)**
- [ ] All three tiers (light / standard / full) produce bodies in the documented size ranges. **(Task 8 templates; Task 12 dogfood validates standard)**
- [ ] Auto-extraction sources 1, 2, 4 work reliably; sources 3, 5, 6 work end-to-end given an orchestrator that passes tool-call history. **(Task 7 auto-extraction.md + Task 12 dogfood)**
- [ ] Supersession chain edits the old file correctly and updates frontmatter on both sides. **(Tasks 3, 4)**
- [ ] Files land at `.taskmaster/handovers/{date}-{slug}.md`, indexed in `backlog.yaml` with cap-30 enforcement. **(Existing backend; Task 12 dogfood verifies)**
- [ ] One end-to-end dogfood. **(Task 12)**
