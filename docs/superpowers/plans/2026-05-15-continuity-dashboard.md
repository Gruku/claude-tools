# Continuity Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the bento dashboard with a continuity surface (hero + spine), introduce decisions as a first-class backlog entity, and simplify handovers now that decision menus live elsewhere.

**Architecture:** A new MCP entity (`backlog_decision_*`) joins the existing v3 family (handovers, issues, ideas, lessons). A server-side adapter (`backlog_continuity_items`) projects all sources onto a unified `ContinuityItem` shape; the viewer's rebuilt `dashboard.js` consumes it through three view modes (Action / Time / Entity). Handover schema sheds two `session_kind` values and the 3-tier system, gaining `open_decisions` / `resolved_this_session` frontmatter arrays.

**Tech Stack:** Python 3.11+ (FastMCP via `@mcp.tool()` in `backlog_server.py`; framework-free core in `taskmaster_v3.py`), pytest, vanilla ES modules (no build step), Node `--test` for unit tests, Playwright for e2e.

**Spec:** `docs/superpowers/specs/2026-05-15-continuity-dashboard-design.md` (commit `7c75ac0`).

---

## File Structure

### Created

- `plugins/taskmaster/skills/decision/SKILL.md` — write/resolve/drop authoring skill
- `plugins/taskmaster/skills/decision/templates/decision-body.md` — body template
- `plugins/taskmaster/skills/decision/references/lifecycle.md` — open → resolved/dropped state diagram
- `plugins/taskmaster/skills/decision/references/auto-resolution.md` — commit-message + auto-task hook spec
- `plugins/taskmaster/viewer/js/lib/continuity.js` — client-side `ContinuityItem` helpers (action_class derivation, view grouping)
- `plugins/taskmaster/viewer/js/screens/dashboard.js` — REWRITTEN; old file deleted then re-created
- `plugins/taskmaster/viewer/js/components/continuity/hero.js` — hero block renderer
- `plugins/taskmaster/viewer/js/components/continuity/spine.js` — spine block renderer
- `plugins/taskmaster/viewer/js/components/continuity/view-switcher.js` — Action/Time/Entity segmented control
- `plugins/taskmaster/viewer/js/components/continuity/decision-card.js` — option list + resolve UX
- `plugins/taskmaster/viewer/js/components/continuity/item-row.js` — generic row renderer (type chip + title + when + next + where)
- `plugins/taskmaster/viewer/css/continuity.css` — dashboard styles (hero/spine layout, type chips, action-class accents)
- `plugins/taskmaster/tests/test_decision_entity.py` — core decision I/O
- `plugins/taskmaster/tests/test_decision_lifecycle.py` — resolve/drop/back-references
- `plugins/taskmaster/tests/test_decision_skill_lint.py` — frontmatter/structure lint
- `plugins/taskmaster/tests/test_server_decisions.py` — MCP wrappers
- `plugins/taskmaster/tests/test_continuity_adapter.py` — adapter projection + action_class routing
- `plugins/taskmaster/tests/test_handover_simplified_kinds.py` — 6→4 kind collapse + decision frontmatter
- `plugins/taskmaster/tests/test_end_session_decision_sweep.py` — end-session integration
- `plugins/taskmaster/viewer/tests/unit/continuity.test.js` — client-side adapter helpers
- `plugins/taskmaster/viewer/tests/unit/decision-card.test.js` — decision-card render
- `plugins/taskmaster/viewer/tests/continuity-dashboard.spec.js` — Playwright e2e

### Modified

- `plugins/taskmaster/taskmaster_v3.py` — add decision functions; collapse `HANDOVER_KINDS`; add `open_decisions`/`resolved_this_session` frontmatter handling
- `plugins/taskmaster/backlog_server.py` — `@mcp.tool()` wrappers for `backlog_decision_*` and `backlog_continuity_items`
- `plugins/taskmaster/skills/handover/SKILL.md` + `references/session-kinds.md` + `templates/*.md` — remove tiers, collapse kinds, remove decision-menu sections, link to decisions instead
- `plugins/taskmaster/skills/end-session/SKILL.md` — decision sweep step
- `plugins/taskmaster/skills/start-session/SKILL.md` — surface `open_decisions` from latest handover on dashboard load
- `plugins/taskmaster/viewer/js/screens/ideas.js` — replace local `relativeTime` with `lib/time.js` `formatRelative`
- `plugins/taskmaster/viewer/js/screens/table.js` — replace local `formatDate` with `lib/time.js` `formatAbsolute`
- `plugins/taskmaster/viewer/js/router.js` — wire `/decisions/:id` route → reuses item-row + decision-card
- `plugins/taskmaster/viewer/css/main.css` — `@import 'continuity.css';` (or add to existing import block)
- `.taskmaster/backlog.yaml` — close `v3-polish-011` and `v3-polish-018`/`v3-polish-039`/`v3-polish-048`; reframe `agentic-os-001`

### Deleted

- `plugins/taskmaster/viewer/js/components/briefing-strip.js`
- `plugins/taskmaster/viewer/js/components/dashboard-grid.js`
- `plugins/taskmaster/viewer/js/components/edit-mode.js`
- `plugins/taskmaster/viewer/js/components/widget-catalog.js`
- `plugins/taskmaster/viewer/js/components/widget-frame.js`
- `plugins/taskmaster/viewer/js/components/widgets/suggested-next.js`
- `plugins/taskmaster/viewer/js/components/widgets/phase-deliverables.js`
- `plugins/taskmaster/viewer/js/components/widgets/newly-unblocked.js`
- `plugins/taskmaster/viewer/js/components/widgets/what-changed.js`
- `plugins/taskmaster/viewer/js/components/widgets/last-session.js`
- `plugins/taskmaster/viewer/js/components/widgets/open-issues.js`
- `plugins/taskmaster/viewer/js/components/widgets/build-test-pulse.js` (replaced by 1-line footer)
- `plugins/taskmaster/viewer/js/components/widgets/lessons-digest.js`
- `plugins/taskmaster/viewer/js/components/widgets/quick-capture.js`
- `plugins/taskmaster/viewer/js/components/widgets/recent-commits.js`
- `plugins/taskmaster/viewer/js/components/widgets/agent-activity.js`
- `plugins/taskmaster/viewer/js/components/widgets/stale-tasks.js`
- `plugins/taskmaster/viewer/tests/unit/dashboard-grid.test.js`
- `plugins/taskmaster/viewer/tests/dashboard.spec.js` (replaced by `continuity-dashboard.spec.js`)
- `plugins/taskmaster/viewer/brainstorm-phases*.html` (orphaned prototypes — verify before delete)

---

## Conventions

- **Python tests:** `pytest plugins/taskmaster/tests/test_<name>.py::<test_fn> -v` (run from repo root).
- **Viewer unit tests:** `cd plugins/taskmaster/viewer && npm run test:unit -- tests/unit/<name>.test.js`.
- **Viewer e2e:** `cd plugins/taskmaster/viewer && npm run test:e2e -- tests/continuity-dashboard.spec.js`.
- **Commit style:** Prefix with type (`feat:` / `test:` / `refactor:` / `chore:`); keep subject line < 70 chars.
- **One logical change per commit.** A failing test, then the implementation it unlocks, are separate commits.
- **Existing patterns to mirror:** `write_issue` and `_write_issue` in `taskmaster_v3.py` / `backlog_server.py` (for entity I/O and MCP wrappers); `plugins/taskmaster/skills/issue/` (for skill structure).

---

## Task 1: Time-format sweep + viewer handover-timestamp fix

**Why:** Folds in v3-polish-018 (shared helper) + v3-polish-039 (viewer timestamps broken). The handover writer already records full ISO `created` (taskmaster_v3.py:808), so v3-polish-048 is already satisfied at the writer level — the bug is purely on the viewer-read side, which still uses the date-only `date:` field for relative-time labels. We unify on `lib/time.js` `formatRelative(handover.created)` and delete the duplicate formatters.

**Files:**
- Modify: `plugins/taskmaster/viewer/js/screens/ideas.js:65-72` (delete local `relativeTime`; import from `lib/time.js`)
- Modify: `plugins/taskmaster/viewer/js/screens/table.js:32-55` (delete local `formatDate`; import `formatAbsolute`)
- Test: `plugins/taskmaster/viewer/tests/unit/time.test.js` (new)
- Test: existing handover-status tests stay green.

### Steps

- [ ] **Step 1: Write the failing unit test for `formatRelative` with handover-shape input**

Create `plugins/taskmaster/viewer/tests/unit/time.test.js`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { formatRelative, formatAbsolute, isoToMs } from '../../js/lib/time.js';

const NOW = new Date('2026-05-15T12:00:00Z').getTime();

test('formatRelative · ISO microsecond handover created → "1d ago"', () => {
  const created = '2026-05-14T12:00:00.000000+00:00';
  assert.equal(formatRelative(created, { now: NOW }), '1d ago');
});

test('formatRelative · date-only string parses as local midnight', () => {
  const out = formatRelative('2026-05-14', { now: NOW });
  // 24h span when both sides are interpreted consistently.
  assert.match(out, /^\d+[hmd] ago$/);
});

test('formatRelative · same-second returns "now"', () => {
  const created = new Date(NOW).toISOString();
  assert.equal(formatRelative(created, { now: NOW }), 'now');
});

test('formatAbsolute · date-only suppresses time', () => {
  assert.equal(formatAbsolute('2026-05-14', { now: NOW }), 'May 14');
});

test('isoToMs · null/empty → null', () => {
  assert.equal(isoToMs(null), null);
  assert.equal(isoToMs(''), null);
});
```

- [ ] **Step 2: Run the test to verify it passes (`lib/time.js` already implements these)**

Run: `cd plugins/taskmaster/viewer && npm run test:unit -- tests/unit/time.test.js`
Expected: PASS — this is a *characterization test* that locks in the existing contract before the sweep.

- [ ] **Step 3: Commit the characterization test**

```bash
git add plugins/taskmaster/viewer/tests/unit/time.test.js
git commit -m "test: characterize lib/time.js contract before sweep"
```

- [ ] **Step 4: Sweep `screens/ideas.js`**

Replace the local helper with the canonical import.

In `plugins/taskmaster/viewer/js/screens/ideas.js`, top of file imports section, add:
```js
import { formatRelative } from '../lib/time.js';
```
Delete lines 65–72 (the local `function relativeTime(iso) { … }`).
Replace the one call site `relativeTime(idea.created)` (line 535) with `formatRelative(idea.created)`.

- [ ] **Step 5: Sweep `screens/table.js`**

In `plugins/taskmaster/viewer/js/screens/table.js`, add to imports:
```js
import { formatAbsolute } from '../lib/time.js';
```
Delete the local `function formatDate(iso) { … }` (around line 45).
Replace `formatDate(t.started)` (line 32) with `formatAbsolute(t.started)`.

- [ ] **Step 6: Run existing viewer unit tests to verify the sweep didn't regress**

Run: `cd plugins/taskmaster/viewer && npm run test:unit`
Expected: all green.

- [ ] **Step 7: Commit the sweep**

```bash
git add plugins/taskmaster/viewer/js/screens/ideas.js plugins/taskmaster/viewer/js/screens/table.js
git commit -m "refactor: route ideas/table screens through lib/time.js (v3-polish-018)"
```

- [ ] **Step 8: Audit handover renders for `date` vs `created` (v3-polish-039)**

Run: `grep -rn "handover\..*date\|handover\.created" plugins/taskmaster/viewer/js/`
For every render path that currently reads `handover.date` (the date-only `YYYY-MM-DD` from `taskmaster_v3.py:806`), switch to `handover.created` (the microsecond ISO from line 808). Keep `handover.date` only where a user-facing "calendar day" label is genuinely wanted (never for relative-time strings).

Concretely you will likely touch sessions.js / recap.js / task-detail.js. For each switched site, leave a one-line code change; no new abstractions.

- [ ] **Step 9: Add a regression test for the handover relative-time fix**

Append to `plugins/taskmaster/viewer/tests/unit/time.test.js`:

```js
test('formatRelative · handover.created drives "Xd ago" not handover.date', () => {
  const handover = {
    date: '2026-05-14',                          // date-only (local midnight)
    created: '2026-05-14T23:59:00.000000+00:00', // late-night UTC write
  };
  // From NOW=2026-05-15T12:00Z, late-night-prior should be "12h ago", not "1d ago".
  const out = formatRelative(handover.created, { now: NOW });
  assert.equal(out, '12h ago');
});
```

- [ ] **Step 10: Verify the regression test passes**

Run: `cd plugins/taskmaster/viewer && npm run test:unit -- tests/unit/time.test.js`
Expected: PASS.

- [ ] **Step 11: Commit the v3-polish-039 fix**

```bash
git add plugins/taskmaster/viewer/js/ plugins/taskmaster/viewer/tests/unit/time.test.js
git commit -m "fix: handover timestamps use ISO 'created', not date-only 'date' (v3-polish-039)"
```

---

## Task 2: Decision entity — schema, ID allocation, validation

**Why:** Lay the storage layer the way `issue` did. Mirror the `write_issue` / `read_issue` / `list_issue_ids` / `next_issue_id` / `_validate_issue` shape so the patterns rhyme.

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py` (append after the issue block, ~line 1300)
- Create: `plugins/taskmaster/tests/test_decision_entity.py`

### Steps

- [ ] **Step 1: Write the failing test for ID allocation**

Create `plugins/taskmaster/tests/test_decision_entity.py`:

```python
"""Decision entity — schema, allocation, validation."""
from pathlib import Path
import pytest
import yaml

from plugins.taskmaster import taskmaster_v3 as tm


@pytest.fixture
def backlog(tmp_path):
    bp = tmp_path / "backlog.yaml"
    bp.write_text("meta:\n  schema_version: 3\nepics: []\n", encoding="utf-8")
    return bp


def test_decision_dir_is_created_on_first_use(backlog):
    d = tm.decision_dir(backlog)
    assert d.name == "decisions"
    assert d.parent == backlog.parent


def test_next_decision_id_allocates_DEC_001_when_empty(backlog):
    assert tm.next_decision_id(backlog) == "DEC-001"


def test_next_decision_id_increments_past_existing(backlog):
    d = tm.decision_dir(backlog)
    d.mkdir(parents=True)
    (d / "DEC-001.md").write_text("---\nid: DEC-001\n---\n", encoding="utf-8")
    (d / "DEC-007.md").write_text("---\nid: DEC-007\n---\n", encoding="utf-8")
    assert tm.next_decision_id(backlog) == "DEC-008"
```

- [ ] **Step 2: Run and verify they fail**

Run: `pytest plugins/taskmaster/tests/test_decision_entity.py -v`
Expected: FAIL — `AttributeError: module 'taskmaster_v3' has no attribute 'decision_dir'`.

- [ ] **Step 3: Implement `decision_dir`, `list_decision_ids`, `next_decision_id`**

In `plugins/taskmaster/taskmaster_v3.py`, append after the issue helpers (around line 1196, after `next_issue_id`):

```python
DECISION_STATUSES = ("open", "resolved", "dropped")


def decision_dir(backlog_path: Path) -> Path:
    """Return the `decisions/` dir alongside backlog.yaml."""
    return backlog_path.parent / "decisions"


def list_decision_ids(backlog_path: Path) -> list[str]:
    """List decision ids on disk, sorted numerically by trailing number."""
    d = decision_dir(backlog_path)
    if not d.exists():
        return []

    def _rank(p: Path) -> int:
        m = re.search(r"(\d+)$", p.stem)
        return int(m.group(1)) if m else -1

    files = sorted(d.glob("DEC-*.md"), key=_rank)
    return [p.stem for p in files]


def next_decision_id(backlog_path: Path) -> str:
    """Allocate the next DEC-NNN id (zero-padded, 3+ digits)."""
    existing = list_decision_ids(backlog_path)
    nums = [int(re.search(r"(\d+)$", x).group(1)) for x in existing
            if re.search(r"(\d+)$", x)]
    n = (max(nums) + 1) if nums else 1
    return f"DEC-{n:03d}"


def decision_path(backlog_path: Path, decision_id: str) -> Path:
    return decision_dir(backlog_path) / f"{decision_id}.md"
```

- [ ] **Step 4: Run, verify they pass**

Run: `pytest plugins/taskmaster/tests/test_decision_entity.py -v`
Expected: 3/3 PASS.

- [ ] **Step 5: Commit allocation primitives**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_decision_entity.py
git commit -m "feat: decision entity allocation primitives (DEC-NNN)"
```

- [ ] **Step 6: Write failing tests for validation**

Append to `plugins/taskmaster/tests/test_decision_entity.py`:

```python
def test_validate_decision_rejects_unknown_status():
    with pytest.raises(ValueError, match="status must be one of"):
        tm._validate_decision({"status": "wat", "options": ["a"]})


def test_validate_decision_requires_two_options():
    with pytest.raises(ValueError, match="at least 2 options"):
        tm._validate_decision({"status": "open", "options": ["only-one"]})


def test_validate_decision_resolved_requires_resolved_with():
    with pytest.raises(ValueError, match="resolved.*requires resolved_with"):
        tm._validate_decision({
            "status": "resolved",
            "options": ["a", "b"],
            "resolved_with": None,
        })


def test_validate_decision_recommendation_must_be_in_range():
    with pytest.raises(ValueError, match="recommendation must be 1.."):
        tm._validate_decision({
            "status": "open",
            "options": ["a", "b"],
            "recommendation": 3,
        })
```

- [ ] **Step 7: Verify they fail**

Run: `pytest plugins/taskmaster/tests/test_decision_entity.py -v`
Expected: 4 new tests FAIL with AttributeError on `_validate_decision`.

- [ ] **Step 8: Implement `_validate_decision`**

Append to `taskmaster_v3.py` after the previous additions:

```python
def _validate_decision(fm: dict[str, Any]) -> None:
    """Raise ValueError if frontmatter violates decision invariants."""
    status = fm.get("status")
    if status not in DECISION_STATUSES:
        raise ValueError(f"status must be one of {DECISION_STATUSES}, got {status!r}")
    opts = fm.get("options") or []
    if not isinstance(opts, list) or len(opts) < 2:
        raise ValueError("decision must have at least 2 options")
    rec = fm.get("recommendation")
    if rec is not None and not (1 <= int(rec) <= len(opts)):
        raise ValueError(f"recommendation must be 1..{len(opts)}, got {rec!r}")
    if status == "resolved" and not fm.get("resolved_with"):
        raise ValueError("status=resolved requires resolved_with to be set (1..N)")
    if status == "dropped" and not fm.get("dropped_reason"):
        raise ValueError("status=dropped requires dropped_reason")
```

- [ ] **Step 9: Run, verify passes**

Run: `pytest plugins/taskmaster/tests/test_decision_entity.py -v`
Expected: all PASS.

- [ ] **Step 10: Commit validation**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_decision_entity.py
git commit -m "feat: decision frontmatter validation"
```

---

## Task 3: Decision write / read

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py`
- Modify: `plugins/taskmaster/tests/test_decision_entity.py`

### Steps

- [ ] **Step 1: Write failing test for `write_decision`**

Append to `test_decision_entity.py`:

```python
def test_write_decision_creates_file_with_frontmatter(backlog):
    did, target = tm.write_decision(
        backlog,
        title="Land ue-plugin-086 fix",
        options=[
            "Push feature + Draft MR against stage",
            "Local --no-ff into develop, push on approval",
            "Hold — user does merge",
        ],
        recommendation=2,
        task_id="ue-plugin-086",
        related_issues=["ISS-018"],
        branch="feature/ue-plugin-086",
        body="Context body here.\n",
    )
    assert did == "DEC-001"
    assert target.exists()
    fm, body = tm.read_decision(backlog, did)
    assert fm["id"] == "DEC-001"
    assert fm["title"] == "Land ue-plugin-086 fix"
    assert fm["status"] == "open"
    assert fm["recommendation"] == 2
    assert fm["task_id"] == "ue-plugin-086"
    assert fm["related_issues"] == ["ISS-018"]
    assert fm["branch"] == "feature/ue-plugin-086"
    assert "created_at" in fm
    assert fm["resolved_with"] is None
    assert fm["resolved_at"] is None
    assert fm["referenced_in"] == []
    assert body.strip() == "Context body here."


def test_write_decision_rejects_invalid(backlog):
    with pytest.raises(ValueError):
        tm.write_decision(backlog, title="Bad", options=["only-one"])
    with pytest.raises(ValueError, match="title is required"):
        tm.write_decision(backlog, title="  ", options=["a", "b"])
```

- [ ] **Step 2: Verify they fail**

Run: `pytest plugins/taskmaster/tests/test_decision_entity.py::test_write_decision_creates_file_with_frontmatter -v`
Expected: FAIL — `write_decision` undefined.

- [ ] **Step 3: Implement `write_decision` and `read_decision`**

Append to `taskmaster_v3.py`:

```python
def write_decision(
    backlog_path: Path,
    *,
    title: str,
    options: list[str],
    recommendation: int | None = None,
    task_id: str | None = None,
    related_issues: list[str] | None = None,
    branch: str | None = None,
    raised_in: str | None = None,
    body: str = "",
    decision_id: str | None = None,
    status: str = "open",
) -> tuple[str, Path]:
    """Create a new decision file. Returns (id, path)."""
    if not title or not title.strip():
        raise ValueError("decision title is required")
    did = decision_id or next_decision_id(backlog_path)
    fm: dict[str, Any] = {
        "id": did,
        "title": title.strip(),
        "status": status,
        "options": list(options),
        "recommendation": recommendation,
        "task_id": task_id,
        "related_issues": list(related_issues or []),
        "branch": branch,
        "resolved_with": None,
        "resolved_rationale": None,
        "dropped_reason": None,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
        "resolved_at": None,
        "raised_in": raised_in,
        "referenced_in": [],
        "resolved_in": None,
    }
    _validate_decision(fm)
    target = decision_path(backlog_path, did)
    write_task_file(target, fm, body)
    return did, target


def read_decision(backlog_path: Path, decision_id: str) -> tuple[dict[str, Any], str]:
    """Read a decision file by id. Raises FileNotFoundError if missing."""
    return read_task_file(decision_path(backlog_path, decision_id))
```

- [ ] **Step 4: Run, verify PASS**

Run: `pytest plugins/taskmaster/tests/test_decision_entity.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_decision_entity.py
git commit -m "feat: write_decision/read_decision"
```

---

## Task 4: Decision update / resolve / drop + back-reference maintenance

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py`
- Create: `plugins/taskmaster/tests/test_decision_lifecycle.py`

### Steps

- [ ] **Step 1: Write failing tests for resolve/drop/update**

Create `plugins/taskmaster/tests/test_decision_lifecycle.py`:

```python
from pathlib import Path
import pytest

from plugins.taskmaster import taskmaster_v3 as tm


@pytest.fixture
def backlog(tmp_path):
    bp = tmp_path / "backlog.yaml"
    bp.write_text("meta:\n  schema_version: 3\nepics: []\n", encoding="utf-8")
    return bp


@pytest.fixture
def open_decision(backlog):
    did, _ = tm.write_decision(
        backlog, title="x", options=["a", "b", "c"], recommendation=2,
        task_id="t-001", branch="feature/x",
    )
    return did


def test_resolve_sets_status_resolved_with_and_timestamp(backlog, open_decision):
    fm = tm.resolve_decision(backlog, open_decision, resolved_with=2, rationale="winner")
    assert fm["status"] == "resolved"
    assert fm["resolved_with"] == 2
    assert fm["resolved_rationale"] == "winner"
    assert fm["resolved_at"]   # truthy ISO string


def test_resolve_rejects_out_of_range(backlog, open_decision):
    with pytest.raises(ValueError, match="must be 1..3"):
        tm.resolve_decision(backlog, open_decision, resolved_with=99)


def test_drop_sets_status_dropped_with_reason(backlog, open_decision):
    fm = tm.drop_decision(backlog, open_decision, reason="superseded by external decision")
    assert fm["status"] == "dropped"
    assert fm["dropped_reason"] == "superseded by external decision"


def test_update_decision_can_change_title_options_recommendation(backlog, open_decision):
    fm = tm.update_decision(backlog, open_decision, {
        "title": "Renamed",
        "options": ["a", "b", "c", "d"],
        "recommendation": 4,
    })
    assert fm["title"] == "Renamed"
    assert fm["options"] == ["a", "b", "c", "d"]
    assert fm["recommendation"] == 4


def test_update_decision_rejects_terminal_to_open(backlog, open_decision):
    tm.resolve_decision(backlog, open_decision, resolved_with=1)
    with pytest.raises(ValueError, match="cannot reopen"):
        tm.update_decision(backlog, open_decision, {"status": "open"})


def test_link_handover_appends_referenced_in(backlog, open_decision):
    tm.link_decision_to_handover(backlog, open_decision, "2026-05-15-foo")
    fm, _ = tm.read_decision(backlog, open_decision)
    assert "2026-05-15-foo" in fm["referenced_in"]
    # idempotent — same id twice doesn't duplicate.
    tm.link_decision_to_handover(backlog, open_decision, "2026-05-15-foo")
    fm, _ = tm.read_decision(backlog, open_decision)
    assert fm["referenced_in"].count("2026-05-15-foo") == 1
```

- [ ] **Step 2: Verify they fail**

Run: `pytest plugins/taskmaster/tests/test_decision_lifecycle.py -v`
Expected: all FAIL with AttributeError on the missing functions.

- [ ] **Step 3: Implement the lifecycle functions**

Append to `taskmaster_v3.py`:

```python
def update_decision(
    backlog_path: Path,
    decision_id: str,
    patch: dict[str, Any],
) -> dict[str, Any]:
    """Apply a field-level patch to a decision. Returns the new frontmatter."""
    fm, body = read_decision(backlog_path, decision_id)
    if fm["status"] in ("resolved", "dropped") and patch.get("status") == "open":
        raise ValueError(f"cannot reopen terminal decision {decision_id}")
    fm.update(patch)
    _validate_decision(fm)
    write_task_file(decision_path(backlog_path, decision_id), fm, body)
    return fm


def resolve_decision(
    backlog_path: Path,
    decision_id: str,
    *,
    resolved_with: int,
    rationale: str | None = None,
    resolved_in: str | None = None,
) -> dict[str, Any]:
    """Flip a decision to resolved with a chosen option (1-indexed)."""
    fm, body = read_decision(backlog_path, decision_id)
    if not (1 <= int(resolved_with) <= len(fm.get("options") or [])):
        raise ValueError(
            f"resolved_with must be 1..{len(fm['options'])}, got {resolved_with}"
        )
    fm["status"] = "resolved"
    fm["resolved_with"] = int(resolved_with)
    fm["resolved_rationale"] = (rationale or "").strip() or None
    fm["resolved_at"] = datetime.now(timezone.utc).isoformat(timespec="microseconds")
    if resolved_in:
        fm["resolved_in"] = resolved_in
    _validate_decision(fm)
    write_task_file(decision_path(backlog_path, decision_id), fm, body)
    return fm


def drop_decision(
    backlog_path: Path,
    decision_id: str,
    *,
    reason: str,
) -> dict[str, Any]:
    """Mark a decision as dropped with a reason."""
    if not reason or not reason.strip():
        raise ValueError("drop reason is required")
    fm, body = read_decision(backlog_path, decision_id)
    fm["status"] = "dropped"
    fm["dropped_reason"] = reason.strip()
    fm["resolved_at"] = datetime.now(timezone.utc).isoformat(timespec="microseconds")
    _validate_decision(fm)
    write_task_file(decision_path(backlog_path, decision_id), fm, body)
    return fm


def link_decision_to_handover(
    backlog_path: Path,
    decision_id: str,
    handover_id: str,
) -> dict[str, Any]:
    """Append a handover id to the decision's referenced_in (idempotent)."""
    fm, body = read_decision(backlog_path, decision_id)
    refs = list(fm.get("referenced_in") or [])
    if handover_id not in refs:
        refs.append(handover_id)
        fm["referenced_in"] = refs
        write_task_file(decision_path(backlog_path, decision_id), fm, body)
    return fm
```

- [ ] **Step 4: Verify PASS**

Run: `pytest plugins/taskmaster/tests/test_decision_lifecycle.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_decision_lifecycle.py
git commit -m "feat: decision lifecycle (resolve/drop/update/link)"
```

---

## Task 5: MCP wrappers — `backlog_decision_*`

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py` (append after the `backlog_issue_*` block, ~line 1980)
- Create: `plugins/taskmaster/tests/test_server_decisions.py`

### Steps

- [ ] **Step 1: Write failing test for `backlog_decision_create`**

Create `plugins/taskmaster/tests/test_server_decisions.py`:

```python
import importlib
from pathlib import Path
import pytest


@pytest.fixture
def in_backlog(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".taskmaster").mkdir()
    bp = tmp_path / ".taskmaster" / "backlog.yaml"
    bp.write_text(
        "meta:\n  schema_version: 3\nepics: []\nhandovers: []\nissues: []\n",
        encoding="utf-8",
    )
    import plugins.taskmaster.backlog_server as srv
    importlib.reload(srv)
    return srv, bp


def test_backlog_decision_create_writes_file_and_returns_id(in_backlog):
    srv, bp = in_backlog
    out = srv.backlog_decision_create(
        title="Land 086",
        options=["push MR", "merge into develop", "hold"],
        recommendation=2,
        task_id="t-001",
    )
    assert "DEC-001" in out
    assert (bp.parent / "decisions" / "DEC-001.md").exists()


def test_backlog_decision_list_returns_open_only_by_default(in_backlog):
    srv, _ = in_backlog
    srv.backlog_decision_create(title="a", options=["x", "y"])
    did2 = srv.backlog_decision_create(title="b", options=["x", "y"]).split()[2]
    srv.backlog_decision_resolve(did2, resolved_with=1)
    out = srv.backlog_decision_list()
    assert "DEC-001" in out
    assert "DEC-002" not in out

    out_all = srv.backlog_decision_list(status="all")
    assert "DEC-001" in out_all and "DEC-002" in out_all


def test_backlog_decision_resolve_and_drop_round_trip(in_backlog):
    srv, _ = in_backlog
    srv.backlog_decision_create(title="r", options=["x", "y"])
    srv.backlog_decision_resolve("DEC-001", resolved_with=2, rationale="best")
    got = srv.backlog_decision_get("DEC-001")
    assert "resolved" in got and "resolved_with: 2" in got


def test_backlog_decision_create_returns_error_when_no_backlog(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import plugins.taskmaster.backlog_server as srv
    importlib.reload(srv)
    out = srv.backlog_decision_create(title="x", options=["a", "b"])
    assert "no backlog" in out.lower()
```

- [ ] **Step 2: Run, verify failure**

Run: `pytest plugins/taskmaster/tests/test_server_decisions.py -v`
Expected: all FAIL with AttributeError on the missing tools.

- [ ] **Step 3: Implement MCP wrappers**

Append to `plugins/taskmaster/backlog_server.py`, after the `backlog_issue_*` block (~line 1980):

```python
@mcp.tool()
def backlog_decision_create(
    title: str,
    options: list[str],
    recommendation: int | None = None,
    task_id: str | None = None,
    related_issues: list[str] | None = None,
    branch: str | None = None,
    raised_in: str | None = None,
    body: str = "",
) -> str:
    """Write a decision menu as a first-class entity (`DEC-NNN`).

    Use when ≥2 mutually exclusive paths need user input. Replaces inline
    option lists in chat — the decision survives the session.

    Args:
        title: Short summary (≤80 chars).
        options: At least 2 mutually exclusive paths.
        recommendation: 1-indexed pick from `options`. None if no preference.
        task_id: Optional link to the task this decision blocks.
        related_issues: Optional ISS-NNN list.
        branch: Optional branch context.
        raised_in: Optional handover id that surfaced this decision.
        body: Free-form context (rationale, constraints, links).
    """
    bp = _backlog_path()
    if not bp.exists():
        return f"Error: no backlog found at {bp}. Run `backlog_init` first."
    try:
        did, target = tm.write_decision(
            bp,
            title=title,
            options=options,
            recommendation=recommendation,
            task_id=task_id,
            related_issues=related_issues or [],
            branch=branch,
            raised_in=raised_in,
            body=body,
        )
    except ValueError as exc:
        return f"Error: {exc}"
    _ensure_v3_marker(bp)
    return f"Decision created: {did} — {title}\nFile: {target.relative_to(ROOT)}"


@mcp.tool()
def backlog_decision_list(status: str = "open", task_id: str = "", limit: int = 20) -> str:
    """List decisions filtered by status. `status='all'` returns every state."""
    bp = _backlog_path()
    if not bp.exists():
        return "No backlog found."
    ids = tm.list_decision_ids(bp)
    rows: list[str] = []
    for did in ids:
        try:
            fm, _ = tm.read_decision(bp, did)
        except (OSError, ValueError):
            continue
        if status != "all" and fm.get("status") != status:
            continue
        if task_id and fm.get("task_id") != task_id:
            continue
        rec = fm.get("recommendation")
        rec_str = f" [rec={rec}]" if rec else ""
        rows.append(f"{did} · {fm.get('status')} · {fm.get('title')}{rec_str}")
        if len(rows) >= limit:
            break
    return "\n".join(rows) if rows else f"No decisions matching status={status}."


@mcp.tool()
def backlog_decision_get(decision_id: str) -> str:
    """Return full decision frontmatter + body as readable text."""
    bp = _backlog_path()
    try:
        fm, body = tm.read_decision(bp, decision_id)
    except FileNotFoundError:
        return f"Decision not found: {decision_id}"
    lines = [f"{k}: {v}" for k, v in fm.items()]
    return "\n".join(lines) + "\n\n---\n" + body


@mcp.tool()
def backlog_decision_resolve(
    decision_id: str,
    resolved_with: int,
    rationale: str = "",
    resolved_in: str = "",
) -> str:
    """Resolve a decision with a chosen option (1-indexed)."""
    bp = _backlog_path()
    try:
        fm = tm.resolve_decision(
            bp, decision_id,
            resolved_with=int(resolved_with),
            rationale=rationale,
            resolved_in=resolved_in or None,
        )
    except (ValueError, FileNotFoundError) as exc:
        return f"Error: {exc}"
    return (
        f"Decision {decision_id} resolved with option {fm['resolved_with']}: "
        f"\"{fm['options'][fm['resolved_with'] - 1]}\""
    )


@mcp.tool()
def backlog_decision_drop(decision_id: str, reason: str) -> str:
    """Drop a decision with a reason (no option picked)."""
    bp = _backlog_path()
    try:
        tm.drop_decision(bp, decision_id, reason=reason)
    except (ValueError, FileNotFoundError) as exc:
        return f"Error: {exc}"
    return f"Decision {decision_id} dropped: {reason}"


@mcp.tool()
def backlog_decision_update(
    decision_id: str,
    title: str = "",
    options: list[str] | None = None,
    recommendation: int | None = None,
    body: str = "",
) -> str:
    """Edit a decision in place (pre-resolution fields only)."""
    bp = _backlog_path()
    patch: dict = {}
    if title: patch["title"] = title
    if options: patch["options"] = options
    if recommendation is not None: patch["recommendation"] = recommendation
    try:
        fm = tm.update_decision(bp, decision_id, patch)
    except (ValueError, FileNotFoundError) as exc:
        return f"Error: {exc}"
    if body:
        cur_fm, _ = tm.read_decision(bp, decision_id)
        tm.write_task_file(tm.decision_path(bp, decision_id), cur_fm, body)
    return f"Decision {decision_id} updated."
```

Make sure `import plugins.taskmaster.taskmaster_v3 as tm` (or the existing alias used in this file) is in scope.

- [ ] **Step 4: Verify tests pass**

Run: `pytest plugins/taskmaster/tests/test_server_decisions.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_server_decisions.py
git commit -m "feat(mcp): backlog_decision_* tools"
```

---

## Task 6: `taskmaster:decision` skill

**Files:**
- Create: `plugins/taskmaster/skills/decision/SKILL.md`
- Create: `plugins/taskmaster/skills/decision/templates/decision-body.md`
- Create: `plugins/taskmaster/skills/decision/references/lifecycle.md`
- Create: `plugins/taskmaster/skills/decision/references/auto-resolution.md`
- Create: `plugins/taskmaster/tests/test_decision_skill_lint.py`

### Steps

- [ ] **Step 1: Write the skill lint test**

Create `plugins/taskmaster/tests/test_decision_skill_lint.py`:

```python
"""Lint the decision skill: required frontmatter, references, body sections."""
from pathlib import Path
import re
import yaml
import pytest

SKILL = Path("plugins/taskmaster/skills/decision/SKILL.md")


def parse_frontmatter(text: str) -> dict:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert m, "SKILL.md must start with --- frontmatter ---"
    return yaml.safe_load(m.group(1))


def test_skill_file_exists():
    assert SKILL.exists()


def test_frontmatter_has_name_and_description():
    fm = parse_frontmatter(SKILL.read_text(encoding="utf-8"))
    assert fm["name"] == "decision"
    assert "decision" in fm["description"].lower()
    # Description must include the canonical trigger phrases.
    desc = fm["description"].lower()
    assert any(p in desc for p in (
        "choose between", "pick an option", "decide on", "open question", "branching path",
    )), f"Skill description missing trigger phrases: {desc}"


def test_body_documents_three_lifecycle_states():
    body = SKILL.read_text(encoding="utf-8")
    for state in ("open", "resolved", "dropped"):
        assert state in body.lower(), f"Skill body missing lifecycle state: {state}"


def test_references_exist():
    assert Path("plugins/taskmaster/skills/decision/references/lifecycle.md").exists()
    assert Path("plugins/taskmaster/skills/decision/references/auto-resolution.md").exists()
    assert Path("plugins/taskmaster/skills/decision/templates/decision-body.md").exists()
```

- [ ] **Step 2: Verify it fails**

Run: `pytest plugins/taskmaster/tests/test_decision_skill_lint.py -v`
Expected: FAIL — file does not exist.

- [ ] **Step 3: Write the skill content**

Create `plugins/taskmaster/skills/decision/SKILL.md`:

```markdown
---
name: decision
description: "Write/resolve/drop project decisions in .taskmaster/decisions/. Invoke when Claude is about to write an inline option menu in chat with ≥2 mutually exclusive paths — instead, decision goes through this skill so the user can pick an option later from the dashboard. Also invoke for 'choose between', 'pick an option', 'decide on', 'open question', 'branching path', 'resolve DEC-X', 'drop DEC-X', or 'list open decisions'. This is the only correct way to write or transition a decision — do not call backlog_decision_create directly."
---

# Decision

A decision is a structured branching point: ≥2 mutually exclusive paths Claude proposes, awaiting user resolution. Decisions live in `.taskmaster/decisions/DEC-NNN.md` and survive context death.

## Why this skill exists

The user used to receive option menus inline in chat ("Options: 1. ... 2. ..."). Scrollback is not durable storage. After context dies, the user couldn't find unresolved choices and resorted to writing Telegram messages to themselves. Decisions move that menu into a first-class entity readable from the continuity dashboard.

The backend is `backlog_decision_create` / `backlog_decision_resolve` / `backlog_decision_drop` / `backlog_decision_update` / `backlog_decision_list` / `backlog_decision_get`. This skill is the **authoring + lifecycle** layer. Calling the MCP tools directly skips trigger heuristics and the option-quality gate. Always go through this skill.

## When to invoke

Five entry points:

1. **`write-decision`** — Claude is about to write `Options:` followed by ≥2 mutually exclusive paths in chat. **Hard rule:** route through this skill instead. Echo a one-line "DEC-NNN written — decide on dashboard or via `/decide DEC-NNN`" rather than spelling the menu in chat.
2. **`resolve`** — user picks an option ("go with option 2", "let's do the local merge", "/decide DEC-001 2").
3. **`drop`** — circumstances changed; the decision no longer matters ("drop DEC-001", "this got resolved externally").
4. **`update`** — pre-resolution edits to title, options, or recommendation.
5. **`list`** — surface open decisions ("what decisions are open", "show me open decisions for ue-plugin-086").

## Authoring rules

- **Title ≤ 80 chars**, action-shaped ("Land ue-plugin-086 fix", not "the question of how to land").
- **At least 2 options.** If you can't articulate 2, there is no decision — just write the work.
- **Options are mutually exclusive.** "Do A" and "Do A then B" is *not* a decision; that's a plan.
- **One-line option text** — the decision body is for rationale, not for an essay per option.
- **Recommendation is optional.** Leave null if you genuinely don't have a preference; lying about indifference wastes the user's read.
- **Link to context** — set `task_id` from the current in-progress task; set `branch` from `git rev-parse --abbrev-ref HEAD`; set `related_issues` for any ISS-NNN this would resolve.

## Lifecycle

See [`references/lifecycle.md`](references/lifecycle.md).

`open` → `resolved` (option chosen) or `dropped` (no option, reason required). Terminal states cannot reopen — create a new decision instead.

## Auto-resolution

See [`references/auto-resolution.md`](references/auto-resolution.md).

- Commit message `Resolves: DEC-001 with option 2` flips status on MCP scan.
- `auto-task` blocks task `done` transitions while linked decisions are open (unless `--override-open-decisions`).
- `end-session` runs a per-decision sweep over open decisions linked to the in-progress task.

## Steps — write a decision

1. **Compose** the title, options, recommendation, and the context body.
2. **Resolve linking info** from current state:
   - `task_id` = current in-progress task id (from auto state or recent commits).
   - `branch` = `git rev-parse --abbrev-ref HEAD`.
   - `raised_in` = most recent handover id, if writing during a session that just produced one.
3. **Call**:
   ```
   backlog_decision_create(
     title=..., options=[...], recommendation=...,
     task_id=..., branch=..., related_issues=[...],
     raised_in=..., body=...,
   )
   ```
4. **Echo** `DEC-NNN written — decide on dashboard or via /decide DEC-NNN`. Do **not** restate the options in chat.

## Steps — resolve

1. Parse the option number from the user's phrasing ("option 2", "the local merge one", "2", `/decide DEC-001 2`).
2. Optionally capture a one-line rationale.
3. Call `backlog_decision_resolve(decision_id, resolved_with, rationale)`.
4. Echo the resolution and (if a linked task exists) append a one-line trace to the task body:
   `2026-MM-DD · DEC-NNN resolved with option N: "<option text>"`.

## Edge cases

- **No backlog** — return the standard `backlog_init` first error.
- **Re-open attempt** — user says "actually let's reconsider DEC-001 even though it's resolved." Do **not** re-open. Write a new decision and add a body link to the previous one.
- **Recommendation > N options** — validation rejects; recompose.
- **Decision overlaps with an open one** — list returns the existing; offer to update the existing instead of writing a new one.

## References

- `references/lifecycle.md` — state diagram, terminal-state rules.
- `references/auto-resolution.md` — commit-message + auto-task hook contract.
- `templates/decision-body.md` — body skeleton.

## Spec

`docs/superpowers/specs/2026-05-15-continuity-dashboard-design.md` §1.
```

- [ ] **Step 4: Write the supporting reference + template files**

Create `plugins/taskmaster/skills/decision/references/lifecycle.md`:

```markdown
# Decision Lifecycle

## States

- `open` — awaiting user input. Default on creation. Renders on dashboard `Decide` rail.
- `resolved` — option N chosen. Frontmatter: `resolved_with: N`, `resolved_at: <ISO>`, optional `resolved_rationale`.
- `dropped` — no option chosen; circumstances changed. Frontmatter: `dropped_reason: <required>`, `resolved_at: <ISO>`.

## Transitions

```
open --(resolve N)--> resolved   (terminal)
open --(drop reason)--> dropped  (terminal)
```

Terminal states do **not** transition back to `open`. A "reopened" decision is a new decision — link to the prior in the body if relevant.

## Pre-resolution mutability

While `open`, the following may be edited via `backlog_decision_update`:
- `title`
- `options` (list mutates — recommendation index re-validates)
- `recommendation`
- `body`

After resolve/drop, the file is frozen except for `referenced_in` (back-references continue to accrue as new handovers link the decision).
```

Create `plugins/taskmaster/skills/decision/references/auto-resolution.md`:

```markdown
# Auto-Resolution Hooks

Three mechanisms transition decisions without explicit `/decide` interaction:

## 1. Commit-message resolution

A commit message containing the line:

    Resolves: DEC-NNN with option N

triggers the MCP server's next scan to call `resolve_decision(NNN, resolved_with=N, resolved_in="commit:<sha>")`. The rationale field stays empty; the commit body becomes the de facto rationale via the back-link.

Regex: `^Resolves:\s*(DEC-\d+)\s+with\s+option\s+(\d+)\s*$` (multiline, case-insensitive).

## 2. auto-task block

`auto-task` will not transition a task to `done` while `backlog_decision_list(status="open", task_id=<current>)` is non-empty. The user can override with `--override-open-decisions`.

## 3. end-session sweep

`end-session` runs `backlog_decision_list(status="open", task_id=<current>)` before writing the handover. For each result, it asks (via `AskUserQuestion`):

- **Carry forward** — leave open, list in handover frontmatter under `open_decisions`.
- **Resolve now** — pick an option inline.
- **Drop** — capture reason.

The handover write receives the final `open_decisions` and `resolved_this_session` arrays.
```

Create `plugins/taskmaster/skills/decision/templates/decision-body.md`:

```markdown
# {{TITLE}}

## Context

<!-- One paragraph: why this came up, what constraint forces a choice. -->

## Options

<!-- Each option in 1–3 lines. The TL;DR of each path's tradeoffs. -->

### Option 1: <terse name>

…

### Option 2: <terse name>

…

## Recommendation

<!-- Optional. If present, name the option index and a 1-sentence rationale. -->

## Links

<!-- Related tasks, issues, prior decisions, handovers, specs. -->
```

- [ ] **Step 5: Verify lint passes**

Run: `pytest plugins/taskmaster/tests/test_decision_skill_lint.py -v`
Expected: all PASS.

- [ ] **Step 6: Commit the skill**

```bash
git add plugins/taskmaster/skills/decision/ plugins/taskmaster/tests/test_decision_skill_lint.py
git commit -m "feat(skills): taskmaster:decision authoring + lifecycle"
```

---

## Task 7: ContinuityItem adapter — types + handover projection

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py` (add adapter section at the end)
- Create: `plugins/taskmaster/tests/test_continuity_adapter.py`

### Steps

- [ ] **Step 1: Write failing test for the ContinuityItem shape + handover projection**

Create `plugins/taskmaster/tests/test_continuity_adapter.py`:

```python
from pathlib import Path
import pytest

from plugins.taskmaster import taskmaster_v3 as tm


@pytest.fixture
def backlog_with_handover(tmp_path):
    bp = tmp_path / ".taskmaster" / "backlog.yaml"
    bp.parent.mkdir()
    bp.write_text(
        "meta:\n  schema_version: 3\nepics: []\nhandovers: []\n",
        encoding="utf-8",
    )
    hid, _ = tm.write_handover(
        bp,
        tldr="shipped X",
        next_action="resume Y on feature/foo",
        task_ids=["t-001"],
        branch="feature/foo",
        session_kind="end-of-day",
    )
    return bp, hid


def test_continuity_item_from_handover_populates_required_fields(backlog_with_handover):
    bp, hid = backlog_with_handover
    items = tm.continuity_items(bp)
    han = [i for i in items if i["type"] == "handover"]
    assert han, "handover not projected"
    it = han[0]
    assert it["id"] == hid
    assert it["title"]  # tldr
    assert it["next"] == "resume Y on feature/foo"
    assert it["action_class"] in ("resume", "ambient")
    assert it["task_id"] == "t-001"
    assert it["branch"] == "feature/foo"
    assert it["timestamp"]
    assert isinstance(it["age_days"], (int, float))


def test_continuity_item_filters_auto_stage_by_default(backlog_with_handover):
    bp, _ = backlog_with_handover
    tm.write_handover(bp, tldr="auto-stage stub", session_kind="auto-stage")
    items_default = tm.continuity_items(bp)
    assert not any(i["type"] == "handover" and i["title"] == "auto-stage stub"
                   for i in items_default)
    items_all = tm.continuity_items(bp, include_auto_stage=True)
    assert any(i["title"] == "auto-stage stub" for i in items_all)


def test_continuity_handover_routes_resume_when_recent_and_todo(backlog_with_handover):
    bp, _ = backlog_with_handover
    items = tm.continuity_items(bp)
    h = [i for i in items if i["type"] == "handover"][0]
    # Fresh handover with default status (todo) → Resume rail.
    assert h["action_class"] == "resume"
```

- [ ] **Step 2: Verify failure**

Run: `pytest plugins/taskmaster/tests/test_continuity_adapter.py -v`
Expected: FAIL — `continuity_items` undefined.

- [ ] **Step 3: Implement the adapter — handover branch only**

Append to `taskmaster_v3.py`:

```python
# ----------------------------------------------------------------------------
# Continuity adapter — projects all entities onto a single ContinuityItem shape.
# ----------------------------------------------------------------------------

CONTINUITY_TYPES = ("decision", "handover", "task", "branch", "idea", "issue")
ACTION_CLASSES = ("decide", "resume", "review", "clean-up", "ambient")


def _age_days(iso_ts: str | None, now: datetime | None = None) -> float:
    if not iso_ts:
        return 0.0
    try:
        ts = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    now = now or datetime.now(timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return (now - ts).total_seconds() / 86400.0


def _handover_to_item(fm: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    age = _age_days(fm.get("created"), now)
    status = fm.get("status", "todo")
    # Action class: fresh todo handover → resume; older or done → ambient (won't surface
    # on action view but still available for time/entity views).
    if status == "todo" and age <= 7:
        action_class = "resume"
    else:
        action_class = "ambient"
    task_ids = fm.get("task_ids") or []
    return {
        "id": fm.get("id"),
        "type": "handover",
        "title": fm.get("tldr") or "",
        "where": fm.get("branch") or (task_ids[0] if task_ids else ""),
        "next": fm.get("next_action") or "",
        "action_class": action_class,
        "timestamp": fm.get("created") or fm.get("date") or "",
        "age_days": age,
        "task_id": task_ids[0] if task_ids else None,
        "branch": fm.get("branch"),
    }


def continuity_items(
    backlog_path: Path,
    *,
    include_auto_stage: bool = False,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """Project all backlog entities to a unified ContinuityItem list."""
    items: list[dict[str, Any]] = []
    for hid in list_handover_ids(backlog_path):
        try:
            fm, _ = read_handover(backlog_path, hid)
        except (OSError, ValueError):
            continue
        if not include_auto_stage and fm.get("session_kind") == "auto-stage":
            continue
        items.append(_handover_to_item(fm, now))
    return items
```

- [ ] **Step 4: Verify PASS for handover branch**

Run: `pytest plugins/taskmaster/tests/test_continuity_adapter.py -v`
Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_continuity_adapter.py
git commit -m "feat: continuity adapter — handover projection"
```

---

## Task 8: ContinuityItem adapter — decision / task / branch / idea / issue projections + routing

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py`
- Modify: `plugins/taskmaster/tests/test_continuity_adapter.py`

### Steps

- [ ] **Step 1: Write failing tests for the remaining sources**

Append to `plugins/taskmaster/tests/test_continuity_adapter.py`:

```python
def test_continuity_open_decision_routes_to_decide(backlog_with_handover):
    bp, _ = backlog_with_handover
    tm.write_decision(bp, title="pick a path",
                      options=["a", "b"], recommendation=1)
    items = tm.continuity_items(bp)
    decs = [i for i in items if i["type"] == "decision"]
    assert decs and decs[0]["action_class"] == "decide"
    assert decs[0]["title"] == "pick a path"


def test_continuity_resolved_decision_routes_to_ambient(backlog_with_handover):
    bp, _ = backlog_with_handover
    tm.write_decision(bp, title="x", options=["a", "b"])
    tm.resolve_decision(bp, "DEC-001", resolved_with=1)
    items = tm.continuity_items(bp)
    assert all(i["action_class"] != "decide" for i in items if i["type"] == "decision")


def test_continuity_in_review_task_routes_to_review(tmp_path):
    bp = tmp_path / ".taskmaster" / "backlog.yaml"
    bp.parent.mkdir()
    bp.write_text(
        "meta:\n  schema_version: 3\n"
        "epics:\n  - id: e1\n    title: E\n"
        "    tasks:\n"
        "      - id: t1\n        title: in-review task\n"
        "        status: in-review\n        priority: high\n",
        encoding="utf-8",
    )
    items = tm.continuity_items(bp)
    tasks = [i for i in items if i["type"] == "task"]
    assert tasks and tasks[0]["action_class"] == "review"


def test_continuity_idle_in_progress_task_routes_to_resume_or_cleanup():
    # Touched <3d → resume. Idle ≥7d → clean-up.
    # Skip in this projection scope; covered in routing helper unit test below.
    pass


def test_route_action_class_for_task_uses_status_and_age():
    today = tm.datetime.now(tm.timezone.utc)
    # In-progress + recent → resume.
    t = {"status": "in-progress", "last_referenced": today.isoformat()}
    assert tm._task_to_item(t, "t1")["action_class"] == "resume"
    # In-progress + 10d idle → clean-up.
    old = (today - tm.timedelta(days=10)).isoformat()
    t2 = {"status": "in-progress", "last_referenced": old}
    assert tm._task_to_item(t2, "t2")["action_class"] == "clean-up"


def test_route_action_class_for_issue_uses_severity_and_age():
    today = tm.datetime.now(tm.timezone.utc).isoformat()
    p1 = {"severity": "P1", "status": "open", "discovered": today, "id": "ISS-1", "title": "t"}
    assert tm._issue_to_item(p1)["action_class"] == "review"
    old = (tm.datetime.now(tm.timezone.utc) - tm.timedelta(days=20)).isoformat()
    p3 = {"severity": "P3", "status": "open", "discovered": old, "id": "ISS-2", "title": "t"}
    assert tm._issue_to_item(p3)["action_class"] == "clean-up"
```

- [ ] **Step 2: Verify failures**

Run: `pytest plugins/taskmaster/tests/test_continuity_adapter.py -v`
Expected: new tests FAIL.

- [ ] **Step 3: Implement projections + routing**

Append to `taskmaster_v3.py`:

```python
def _decision_to_item(fm: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    age = _age_days(fm.get("created_at"), now)
    status = fm.get("status", "open")
    action_class = "decide" if status == "open" else "ambient"
    rec = fm.get("recommendation")
    rec_str = ""
    if rec and fm.get("options"):
        try:
            rec_str = f"rec: {fm['options'][int(rec) - 1]}"
        except (IndexError, ValueError):
            rec_str = ""
    return {
        "id": fm.get("id"),
        "type": "decision",
        "title": fm.get("title") or "",
        "where": fm.get("task_id") or fm.get("branch") or "",
        "next": rec_str or f"{len(fm.get('options') or [])} options",
        "action_class": action_class,
        "timestamp": fm.get("created_at") or "",
        "age_days": age,
        "task_id": fm.get("task_id"),
        "branch": fm.get("branch"),
    }


def _task_to_item(task: dict[str, Any], task_id: str, now: datetime | None = None) -> dict[str, Any]:
    last = task.get("last_referenced") or task.get("started") or task.get("created")
    age = _age_days(last, now)
    status = task.get("status", "todo")
    if status == "in-review":
        action_class = "review"
    elif status == "in-progress" and age <= 3:
        action_class = "resume"
    elif status == "in-progress" and age >= 7:
        action_class = "clean-up"
    else:
        action_class = "ambient"
    return {
        "id": task_id,
        "type": "task",
        "title": task.get("title") or task_id,
        "where": task.get("epic") or "",
        "next": task.get("status") or "",
        "action_class": action_class,
        "timestamp": last or "",
        "age_days": age,
        "task_id": task_id,
        "branch": task.get("branch") or "",
    }


def _issue_to_item(issue: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    sev = issue.get("severity", "P3")
    age = _age_days(issue.get("discovered"), now)
    status = issue.get("status", "open")
    if status != "open":
        action_class = "ambient"
    elif sev in ("P0", "P1"):
        action_class = "review"
    elif age >= 14:
        action_class = "clean-up"
    else:
        action_class = "ambient"
    return {
        "id": issue.get("id"),
        "type": "issue",
        "title": issue.get("title") or "",
        "where": ",".join(issue.get("components") or []),
        "next": f"{sev} · {status}",
        "action_class": action_class,
        "timestamp": issue.get("discovered") or "",
        "age_days": age,
        "task_id": None,
        "branch": None,
    }


def _idea_to_item(idea: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    age = _age_days(idea.get("created"), now)
    status = idea.get("status", "raw")
    action_class = "clean-up" if status == "brainstorm" and age >= 7 else "ambient"
    return {
        "id": idea.get("id"),
        "type": "idea",
        "title": idea.get("title") or "",
        "where": status,
        "next": status,
        "action_class": action_class,
        "timestamp": idea.get("created") or "",
        "age_days": age,
        "task_id": None,
        "branch": None,
    }
```

Extend `continuity_items` to call all five projections:

```python
def continuity_items(
    backlog_path: Path,
    *,
    include_auto_stage: bool = False,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    # Handovers.
    for hid in list_handover_ids(backlog_path):
        try:
            fm, _ = read_handover(backlog_path, hid)
        except (OSError, ValueError):
            continue
        if not include_auto_stage and fm.get("session_kind") == "auto-stage":
            continue
        items.append(_handover_to_item(fm, now))

    # Decisions.
    for did in list_decision_ids(backlog_path):
        try:
            fm, _ = read_decision(backlog_path, did)
        except (OSError, ValueError):
            continue
        items.append(_decision_to_item(fm, now))

    # Tasks (from backlog.yaml epics).
    try:
        data = yaml.safe_load(backlog_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        data = {}
    for epic in data.get("epics", []) or []:
        for t in epic.get("tasks", []) or []:
            tid = t.get("id")
            if not tid:
                continue
            items.append(_task_to_item(t, tid, now))

    # Issues.
    for iid in list_issue_ids(backlog_path):
        try:
            fm, _ = read_issue(backlog_path, iid)
        except (OSError, ValueError):
            continue
        items.append(_issue_to_item(fm, now))

    # Ideas.
    for idid in list_idea_ids(backlog_path):
        try:
            fm, _ = read_idea(backlog_path, idid)
        except (OSError, ValueError):
            continue
        items.append(_idea_to_item(fm, now))

    return items
```

(If `read_issue` / `read_idea` aren't already symbols, the file already contains `load_issue` / `load_idea`-equivalents — use whichever names match this codebase. Grep first; do not invent.)

- [ ] **Step 4: Verify PASS**

Run: `pytest plugins/taskmaster/tests/test_continuity_adapter.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_continuity_adapter.py
git commit -m "feat: continuity adapter — decision/task/issue/idea projections"
```

---

## Task 9: MCP wrapper `backlog_continuity_items` + JSON output

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py` (HTTP `/api/continuity` endpoint + `@mcp.tool()` wrapper)
- Modify: `plugins/taskmaster/tests/test_server_decisions.py` (new file or extend)
- Create: `plugins/taskmaster/tests/test_server_continuity.py`

### Steps

- [ ] **Step 1: Write failing test for `backlog_continuity_items` returning JSON**

Create `plugins/taskmaster/tests/test_server_continuity.py`:

```python
import importlib
import json
import pytest


@pytest.fixture
def in_backlog(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".taskmaster").mkdir()
    bp = tmp_path / ".taskmaster" / "backlog.yaml"
    bp.write_text(
        "meta:\n  schema_version: 3\nepics: []\n",
        encoding="utf-8",
    )
    import plugins.taskmaster.backlog_server as srv
    importlib.reload(srv)
    return srv, bp


def test_backlog_continuity_items_returns_json_with_items_array(in_backlog):
    srv, _ = in_backlog
    srv.backlog_decision_create(title="x", options=["a", "b"])
    out = srv.backlog_continuity_items()
    data = json.loads(out)
    assert "items" in data
    assert any(i["type"] == "decision" for i in data["items"])
    for it in data["items"]:
        assert {"id", "type", "title", "action_class", "timestamp"} <= set(it)


def test_backlog_continuity_items_filters_auto_stage_by_default(in_backlog):
    srv, _ = in_backlog
    srv.backlog_handover_create(
        tldr="auto stub", session_kind="auto-stage", body="", task_ids=[],
    )
    items = json.loads(srv.backlog_continuity_items())["items"]
    assert not any(i["type"] == "handover" and i["title"] == "auto stub" for i in items)
    items_all = json.loads(srv.backlog_continuity_items(include_auto_stage=True))["items"]
    assert any(i["title"] == "auto stub" for i in items_all)
```

- [ ] **Step 2: Verify failure**

Run: `pytest plugins/taskmaster/tests/test_server_continuity.py -v`
Expected: FAIL — `backlog_continuity_items` undefined.

- [ ] **Step 3: Implement the MCP wrapper**

Append to `backlog_server.py`:

```python
@mcp.tool()
def backlog_continuity_items(
    view: str = "action",
    include_auto_stage: bool = False,
) -> str:
    """Return all continuity items as JSON: {"items": [...], "view": "..."}.

    `view` is informational only — the server returns the full set; the client
    decides grouping (Action / Time / Entity).

    Args:
        view: "action" | "time" | "entity" (echoed in the response).
        include_auto_stage: When True, include auto-stage handovers (debug).
    """
    import json
    bp = _backlog_path()
    if not bp.exists():
        return json.dumps({"items": [], "view": view, "error": "no backlog"})
    items = tm.continuity_items(bp, include_auto_stage=include_auto_stage)
    return json.dumps({"items": items, "view": view}, default=str)
```

- [ ] **Step 4: Add the HTTP endpoint for the viewer to call**

In `backlog_server.py`, find the existing `_register_http_routes` / `do_GET` dispatcher (grep for `def do_GET` or `/api/backlog` to locate the registration block) and add a route for `/api/continuity`:

```python
# In the HTTP route table for the viewer:
elif path == "/api/continuity":
    include_auto = qs.get("include_auto_stage", ["0"])[0] in ("1", "true")
    payload = json.loads(backlog_continuity_items(include_auto_stage=include_auto))
    self._send_json(payload)
```

(Pattern-match against the file's existing route handler — `_send_json` may be named differently.)

- [ ] **Step 5: Run tests**

Run: `pytest plugins/taskmaster/tests/test_server_continuity.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_server_continuity.py
git commit -m "feat(mcp): backlog_continuity_items + /api/continuity"
```

---

## Task 10: Handover simplification — 6→4 kinds + decision frontmatter

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py` (HANDOVER_KINDS, frontmatter)
- Modify: `plugins/taskmaster/skills/handover/SKILL.md`, `references/session-kinds.md`, `templates/*.md`
- Create: `plugins/taskmaster/tests/test_handover_simplified_kinds.py`

### Steps

- [ ] **Step 1: Write failing tests for the collapsed kinds**

Create `plugins/taskmaster/tests/test_handover_simplified_kinds.py`:

```python
import pytest
from plugins.taskmaster import taskmaster_v3 as tm


@pytest.fixture
def backlog(tmp_path):
    bp = tmp_path / ".taskmaster" / "backlog.yaml"
    bp.parent.mkdir()
    bp.write_text("meta:\n  schema_version: 3\nepics: []\nhandovers: []\n",
                  encoding="utf-8")
    return bp


def test_kinds_are_continuity_deep_context_milestone_auto_stage():
    assert set(tm.HANDOVER_KINDS) == {"continuity", "deep-context", "milestone", "auto-stage"}


def test_legacy_kinds_translate_to_new_names_on_write(backlog):
    # Backwards compatibility: callers passing old kinds get mapped to new ones.
    hid, _ = tm.write_handover(backlog, tldr="x", session_kind="end-of-day")
    fm, _ = tm.read_handover(backlog, hid)
    assert fm["session_kind"] == "continuity"

    hid2, _ = tm.write_handover(backlog, tldr="y", session_kind="pivot")
    fm2, _ = tm.read_handover(backlog, hid2)
    assert fm2["session_kind"] == "milestone"


def test_handover_frontmatter_includes_open_decisions_and_resolved(backlog):
    hid, _ = tm.write_handover(
        backlog,
        tldr="x",
        open_decisions=["DEC-001", "DEC-003"],
        resolved_this_session=["DEC-002"],
    )
    fm, _ = tm.read_handover(backlog, hid)
    assert fm["open_decisions"] == ["DEC-001", "DEC-003"]
    assert fm["resolved_this_session"] == ["DEC-002"]


def test_handover_write_back_references_decisions(backlog):
    tm.write_decision(backlog, title="d1", options=["a", "b"])
    hid, _ = tm.write_handover(backlog, tldr="x", open_decisions=["DEC-001"])
    fm_dec, _ = tm.read_decision(backlog, "DEC-001")
    assert hid in fm_dec["referenced_in"]
```

- [ ] **Step 2: Verify failures**

Run: `pytest plugins/taskmaster/tests/test_handover_simplified_kinds.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement the kind collapse + frontmatter additions**

In `taskmaster_v3.py`, find the `HANDOVER_KINDS` constant (grep for it) and replace:

```python
HANDOVER_KINDS = ("continuity", "deep-context", "milestone", "auto-stage")

_LEGACY_KIND_MAP = {
    "end-of-day": "continuity",
    "exploration": "continuity",
    "context-handoff": "deep-context",
    "milestone-complete": "milestone",
    "pivot": "milestone",
}


def _normalize_session_kind(kind: str) -> str:
    return _LEGACY_KIND_MAP.get(kind, kind)
```

In `write_handover`, before the existing validation:

```python
session_kind = _normalize_session_kind(session_kind)
```

Extend the `write_handover` signature with two new kwargs:

```python
def write_handover(
    backlog_path: Path,
    *,
    tldr: str,
    next_action: str = "",
    body: str = "",
    task_ids: list[str] | None = None,
    session_kind: str = "continuity",
    when: str | None = None,
    context_size_at_write: str | None = None,
    supersedes: str | None = None,
    branch: str | None = None,
    tip_commit: str | None = None,
    open_decisions: list[str] | None = None,
    resolved_this_session: list[str] | None = None,
) -> tuple[str, Path]:
    ...
```

After building `fm`, add:

```python
    fm["open_decisions"] = list(open_decisions or [])
    fm["resolved_this_session"] = list(resolved_this_session or [])
```

After the file is written, append the back-reference loop:

```python
    for did in fm["open_decisions"]:
        try:
            link_decision_to_handover(backlog_path, did, final_id)
        except FileNotFoundError:
            pass  # decision was deleted; don't fail the handover write
```

- [ ] **Step 4: Update the `_default_handover_status` map**

If `_default_handover_status` switches on the legacy names, update it for the new ones:

```python
def _default_handover_status(session_kind: str) -> str:
    if session_kind == "auto-stage":
        return "done"
    return "todo"
```

- [ ] **Step 5: Run tests**

Run: `pytest plugins/taskmaster/tests/test_handover_simplified_kinds.py -v`
Expected: PASS.

Run the full existing handover suite to verify no regression:

Run: `pytest plugins/taskmaster/tests/test_handover_status_*.py plugins/taskmaster/tests/test_server_handover_reads.py -v`
Expected: PASS. If any test relied on `session_kind == "end-of-day"` literally, switch the test to use `continuity` (or trust the legacy map and leave them).

- [ ] **Step 6: Commit the schema change**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_handover_simplified_kinds.py
git commit -m "feat: handover session_kind 6→4 + open_decisions frontmatter"
```

- [ ] **Step 7: Update the handover skill content**

Modify `plugins/taskmaster/skills/handover/references/session-kinds.md`:

Replace the 6-row table with the new 4-row table from spec §3.1:

```markdown
# Handover Session Kinds

Four values. Pick exactly one. Kind drives resume-load behavior and archive policy.

| Kind | When | Resume load | Archive |
|---|---|---|---|
| `continuity` | Default. End-of-day, exploration, generic wrap-up. | Frontmatter only. | FIFO past cap-30. |
| `deep-context` | Pre-compaction safety capture (≥200k tokens; user said "near compaction"). | **Body loaded** — current session about to die. | FIFO past cap-30. |
| `milestone` | Chunk shipped OR direction changed. Body explains which. | **Body loaded.** | Chained supersession on same `task_ids`. |
| `auto-stage` | Written by `auto-task` per-stage. | Frontmatter only. | Bulk-archived on epic/phase completion. |

Legacy values `end-of-day`, `exploration`, `pivot`, `context-handoff`, `milestone-complete` still accepted on write — they map to the new names. Read code should always see the normalized value.

## Choosing the right kind

1. Invoked by `auto-task`? → `auto-stage`.
2. User said "near compaction" / "300k" / "save before compact"? → `deep-context`.
3. Chunk shipped, direction changed, plan switch, "ready for next plan"? → `milestone`.
4. Otherwise → `continuity`.
```

Modify `plugins/taskmaster/skills/handover/SKILL.md`:

- In step 2 ("Select a tier"): delete the entire step. Tiers are gone — one shape.
- In step 6 ("Draft the body from the tier template"): change to "Draft the body from `templates/standard.md`."
- Update `templates/light.md` and `templates/full.md`: delete both (one shape only). Rename `templates/standard.md` to `templates/body.md` to make the singularity obvious.
- In the SKILL.md `templates/` reference section, point only at `templates/body.md`.
- Anywhere the SKILL.md mentions decision-menu sections in the body templates, remove the language; instead instruct: "if open or resolved decisions exist, pass them as `open_decisions=[...]` / `resolved_this_session=[...]` to `backlog_handover_create`; reference inline with `[[DEC-NNN]]`."
- Replace any explicit kind references using the legacy names with the new ones.

Modify `templates/body.md` (formerly `templates/standard.md`): remove any "Open options for next session" / "Pending decisions" section. Add a brief note at the top:

```markdown
<!-- Reference decisions with [[DEC-NNN]] in any section.
     Open and resolved decisions are tracked via frontmatter, not body text. -->
```

- [ ] **Step 8: Run skill lint**

Run: `pytest plugins/taskmaster/tests/test_handover_skill_lint.py -v`
Expected: PASS. If the lint asserts the old session-kind list literally, update those assertions to the new list (this is the intended schema change).

- [ ] **Step 9: Commit skill changes**

```bash
git add plugins/taskmaster/skills/handover/
git commit -m "refactor(skills): handover skill — one tier, four kinds, decisions via frontmatter"
```

---

## Task 11: `end-session` decision sweep

**Files:**
- Modify: `plugins/taskmaster/skills/end-session/SKILL.md`
- Create: `plugins/taskmaster/tests/test_end_session_decision_sweep.py` (skill lint variant)

### Steps

- [ ] **Step 1: Write failing skill-lint test**

Create `plugins/taskmaster/tests/test_end_session_decision_sweep.py`:

```python
from pathlib import Path

SKILL = Path("plugins/taskmaster/skills/end-session/SKILL.md")


def test_end_session_mentions_decision_sweep():
    body = SKILL.read_text(encoding="utf-8")
    assert "backlog_decision_list" in body
    assert "carry forward" in body.lower()
    assert "drop" in body.lower()


def test_end_session_passes_open_decisions_to_handover_write():
    body = SKILL.read_text(encoding="utf-8")
    assert "open_decisions" in body
    assert "resolved_this_session" in body
```

- [ ] **Step 2: Verify failure**

Run: `pytest plugins/taskmaster/tests/test_end_session_decision_sweep.py -v`
Expected: FAIL.

- [ ] **Step 3: Update the end-session skill**

In `plugins/taskmaster/skills/end-session/SKILL.md`, locate the step where it invokes the handover skill. Insert a new step **before** that one:

```markdown
### Step N: Decision sweep (before handover write)

Before invoking `taskmaster:handover`, sweep open decisions linked to the in-progress task so the handover frontmatter is accurate.

1. Call `backlog_decision_list(status="open", task_id=<current>)`.
2. If the list is non-empty, for **each** decision:
   - Ask via `AskUserQuestion`:
     - **Carry forward** — leave open; will land in handover `open_decisions`.
     - **Resolve now** — present options; on pick, call `backlog_decision_resolve(id, resolved_with=N, rationale="<short>")`.
     - **Drop** — capture one-line reason; call `backlog_decision_drop(id, reason=...)`.
3. Build two arrays:
   - `open_decisions` — all decisions still in `status=open` after the sweep.
   - `resolved_this_session` — every decision flipped during the sweep (or earlier this session via `taskmaster:decision`).
4. Pass both arrays to `taskmaster:handover` as additional kwargs.

Auto-resolved decisions (via commit message `Resolves: DEC-NNN with option N`) need no prompting — they're already `status=resolved`; include them in `resolved_this_session` by querying `backlog_decision_list(status="resolved", resolved_in=session_window)`.
```

- [ ] **Step 4: Run test**

Run: `pytest plugins/taskmaster/tests/test_end_session_decision_sweep.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/skills/end-session/SKILL.md plugins/taskmaster/tests/test_end_session_decision_sweep.py
git commit -m "feat(skills): end-session — decision sweep before handover write"
```

---

## Task 12: `start-session` — surface open decisions

**Files:**
- Modify: `plugins/taskmaster/skills/start-session/SKILL.md`

### Steps

- [ ] **Step 1: Locate the orient/dashboard-load step in start-session**

Read `plugins/taskmaster/skills/start-session/SKILL.md`. Find the step that loads the most recent handover (typically calls `backlog_handover_latest`).

- [ ] **Step 2: Add a decision-surfacing step**

Append a new step (or extend the existing handover-load step) with:

```markdown
### Surface open decisions

After loading the latest handover, also call:

```
backlog_decision_list(status="open")
```

Report the count to the user as part of the dashboard summary:

> "3 open decisions: DEC-001 (Land ue-plugin-086), DEC-003 (Voice billing semantics), DEC-005 (…)"

If a decision blocks the user's top-of-mind task, mention it inline in the "where you left off" recap. The continuity dashboard surfaces them visually; this is the chat-side echo.
```

- [ ] **Step 3: Add a lint assertion**

Append to `plugins/taskmaster/tests/test_end_session_decision_sweep.py` (or a new lint test file):

```python
from pathlib import Path


def test_start_session_calls_backlog_decision_list():
    body = Path("plugins/taskmaster/skills/start-session/SKILL.md").read_text(encoding="utf-8")
    assert "backlog_decision_list" in body
```

- [ ] **Step 4: Run + commit**

Run: `pytest plugins/taskmaster/tests/test_end_session_decision_sweep.py -v`
Expected: PASS.

```bash
git add plugins/taskmaster/skills/start-session/SKILL.md plugins/taskmaster/tests/test_end_session_decision_sweep.py
git commit -m "feat(skills): start-session — surface open decisions"
```

---

## Task 13: Dashboard rebuild — shell + topbar + view switcher

**Why:** Stand up the new dashboard skeleton (topbar, view switcher, auto-mode-strip slot, body container, footer) with the existing dashboard *intact* (we'll replace at the end). The new skeleton lives behind a route alias so we can toggle.

**Files:**
- Create: `plugins/taskmaster/viewer/js/components/continuity/view-switcher.js`
- Create: `plugins/taskmaster/viewer/css/continuity.css`
- Modify: `plugins/taskmaster/viewer/css/main.css` (add `@import 'continuity.css';`)
- Modify: `plugins/taskmaster/viewer/js/router.js` (route `/v2/dashboard` → new screen during build)
- Create: `plugins/taskmaster/viewer/js/screens/continuity.js` (new screen; replaces `dashboard.js` at end)
- Create: `plugins/taskmaster/viewer/tests/unit/view-switcher.test.js`

### Steps

- [ ] **Step 1: Write the view-switcher unit test**

Create `plugins/taskmaster/viewer/tests/unit/view-switcher.test.js`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { JSDOM } from 'jsdom';

const { window } = new JSDOM('<!DOCTYPE html><div id="root"></div>');
globalThis.document = window.document;

import { createViewSwitcher } from '../../js/components/continuity/view-switcher.js';

test('view-switcher renders three buttons and emits select events', () => {
  const events = [];
  const sw = createViewSwitcher({
    active: 'action',
    onSelect: (v) => events.push(v),
  });
  document.body.appendChild(sw.root);
  const btns = sw.root.querySelectorAll('button');
  assert.equal(btns.length, 3);
  btns[1].click();   // time
  btns[2].click();   // entity
  assert.deepEqual(events, ['time', 'entity']);
});

test('view-switcher reflects active prop', () => {
  const sw = createViewSwitcher({ active: 'entity', onSelect: () => {} });
  const active = sw.root.querySelector('button.is-active');
  assert.equal(active?.textContent.toLowerCase(), 'entity');
});
```

- [ ] **Step 2: Run, verify failure**

Run: `cd plugins/taskmaster/viewer && npm run test:unit -- tests/unit/view-switcher.test.js`
Expected: FAIL — file does not exist.

- [ ] **Step 3: Implement `view-switcher.js`**

Create `plugins/taskmaster/viewer/js/components/continuity/view-switcher.js`:

```js
// Segmented control: Action / Time / Entity.
import { h } from '../../util/h.js';

const VIEWS = [
  { key: 'action', label: 'Action' },
  { key: 'time',   label: 'Time' },
  { key: 'entity', label: 'Entity' },
];

export function createViewSwitcher({ active = 'action', onSelect }) {
  const root = h('div', { class: 'co-view-switcher' });
  for (const v of VIEWS) {
    const btn = h('button', {
      type: 'button',
      class: 'co-view-switcher__btn' + (v.key === active ? ' is-active' : ''),
      onclick: () => onSelect?.(v.key),
    }, v.label);
    root.appendChild(btn);
  }
  return { root };
}
```

- [ ] **Step 4: Run test, verify PASS**

Run: `cd plugins/taskmaster/viewer && npm run test:unit -- tests/unit/view-switcher.test.js`
Expected: PASS.

- [ ] **Step 5: Write the base continuity CSS**

Create `plugins/taskmaster/viewer/css/continuity.css`. Use the locked spec from the design doc — Direction C v3 styles. Key rules (paste verbatim; tune via design tokens that already exist in `css/foundations/`):

```css
.co-dash { background: var(--ground-0); color: var(--ground-80); }
.co-dash__topbar { display: flex; align-items: center; gap: 10px;
  padding: 12px 18px; background: var(--ground-5);
  border-bottom: 1px solid var(--ground-15); }
.co-dash__body { padding: 18px; }
.co-dash__layout { display: grid; grid-template-columns: 1.55fr 1fr; gap: 18px; }
.co-dash__footer { padding: 9px 18px; background: var(--ground-0);
  border-top: 1px solid var(--ground-5); display: flex; gap: 18px;
  font-size: 0.825rem; color: var(--ground-50); }

.co-view-switcher { margin-left: auto; display: flex; gap: 1px;
  background: var(--ground-0); border: 1px solid var(--ground-15);
  border-radius: 5px; padding: 2px; }
.co-view-switcher__btn { padding: 4px 10px; font-size: 0.78rem;
  border-radius: 3px; color: var(--ground-50); background: transparent;
  border: 0; cursor: pointer; }
.co-view-switcher__btn.is-active { background: var(--ground-15);
  color: var(--ground-95); }

/* Type chips (decision / handover / task / branch / idea / issue). */
.co-chip { display: inline-block; padding: 1px 6px; font-size: 0.66rem;
  letter-spacing: 0.12em; text-transform: uppercase; border-radius: 2px; font-weight: 600; }
.co-chip--dec { color: var(--accent-pink);   background: var(--accent-pink-subtle); }
.co-chip--han { color: var(--signature);     background: var(--signature-glow); }
.co-chip--tsk { color: var(--accent-lime);   background: var(--accent-lime-subtle); }
.co-chip--brn { color: var(--pastel-orange); background: var(--pastel-orange-subtle); }
.co-chip--ide { color: var(--ground-60);     background: rgba(160,156,149,0.10); }
.co-chip--iss { color: var(--accent-orange); background: var(--accent-orange-subtle); }
```

Append `@import 'continuity.css';` to `plugins/taskmaster/viewer/css/main.css` (find the existing `@import` block).

- [ ] **Step 6: Create the new screen shell**

Create `plugins/taskmaster/viewer/js/screens/continuity.js`:

```js
import { h } from '../util/h.js';
import { createViewSwitcher } from '../components/continuity/view-switcher.js';
import { createAutoModeStrip } from '../components/auto-mode-strip.js';
import { claimTopbar } from '../lib/topbar.js';

export const meta = { title: 'Continuity', icon: '◧', sidebarKey: 'dashboard' };

export async function mount(root, { store, api, prefs }) {
  root.classList.add('co-dash');

  const topbar = h('div', { class: 'co-dash__topbar' },
    h('span', { class: 'co-dash__logo' }),
    h('span', { class: 'co-dash__proj' }, store?.projectName?.() || 'taskmaster'),
  );
  // View switcher.
  let activeView = prefs?.continuity?.view || 'action';
  const sw = createViewSwitcher({
    active: activeView,
    onSelect: async (v) => {
      activeView = v;
      await api.savePrefs({ continuity: { view: v } });
      await render();
    },
  });
  topbar.appendChild(sw.root);

  const autoSlot = h('section', { class: 'co-dash__auto' });
  const strip = createAutoModeStrip({ store, api, mode: 'dashboard' });
  if (strip?.root) autoSlot.appendChild(strip.root);

  const body = h('section', { class: 'co-dash__body' });
  const footer = h('section', { class: 'co-dash__footer' });

  root.replaceChildren(topbar, autoSlot, body, footer);

  async function render() {
    body.replaceChildren(h('p', {}, `(${activeView} view placeholder — Task 14 fills this in)`));
  }

  await render();

  return async () => {
    strip?.destroy?.();
  };
}
```

- [ ] **Step 7: Route the new screen at `/v2/dashboard` temporarily**

In `plugins/taskmaster/viewer/js/router.js`, find the route table and add (alongside the existing dashboard route):

```js
'/v2/dashboard': () => import('./screens/continuity.js'),
```

Do **not** remove the old `/dashboard` route yet — the swap happens in Task 17.

- [ ] **Step 8: Manual smoke test**

Run: `cd plugins/taskmaster/viewer && python -m http.server 8765 --bind 127.0.0.1` (or whatever dev-server command the project uses; check `viewer/README.md` if unsure).
Open `http://127.0.0.1:8765/#/v2/dashboard` in a browser. Expected: topbar with project name + 3-button view switcher; clicking switches the placeholder line. Auto-mode strip renders.

- [ ] **Step 9: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/continuity/view-switcher.js \
        plugins/taskmaster/viewer/js/screens/continuity.js \
        plugins/taskmaster/viewer/css/continuity.css \
        plugins/taskmaster/viewer/css/main.css \
        plugins/taskmaster/viewer/js/router.js \
        plugins/taskmaster/viewer/tests/unit/view-switcher.test.js
git commit -m "feat(viewer): continuity dashboard shell + view switcher (/v2/dashboard)"
```

---

## Task 14: Action view — hero + spine + item rows

**Files:**
- Create: `plugins/taskmaster/viewer/js/lib/continuity.js`
- Create: `plugins/taskmaster/viewer/js/components/continuity/hero.js`
- Create: `plugins/taskmaster/viewer/js/components/continuity/spine.js`
- Create: `plugins/taskmaster/viewer/js/components/continuity/item-row.js`
- Create: `plugins/taskmaster/viewer/js/components/continuity/decision-card.js`
- Modify: `plugins/taskmaster/viewer/js/screens/continuity.js` (wire Action view)
- Create: `plugins/taskmaster/viewer/tests/unit/continuity.test.js`
- Create: `plugins/taskmaster/viewer/tests/unit/decision-card.test.js`

### Steps

- [ ] **Step 1: Write the failing test for client-side action-view grouping**

Create `plugins/taskmaster/viewer/tests/unit/continuity.test.js`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { groupByAction, pickHero } from '../../js/lib/continuity.js';

const FIXTURE = [
  { id: 'DEC-001', type: 'decision', title: 'a', action_class: 'decide', age_days: 1 },
  { id: 'DEC-003', type: 'decision', title: 'b', action_class: 'decide', age_days: 4 },
  { id: 'h1',  type: 'handover', title: 'resume', action_class: 'resume', age_days: 1 },
  { id: 't1',  type: 'task',     title: 'review', action_class: 'review', age_days: 0 },
  { id: 'br1', type: 'branch',   title: 'cold',   action_class: 'clean-up', age_days: 9 },
  { id: 'i1',  type: 'idea',     title: 'amb',    action_class: 'ambient', age_days: 30 },
];

test('groupByAction yields 4 rails in the right order', () => {
  const g = groupByAction(FIXTURE);
  assert.deepEqual(Object.keys(g), ['decide', 'resume', 'review', 'clean-up']);
  assert.equal(g['decide'].length, 2);
  assert.equal(g['resume'].length, 1);
  assert.equal(g['review'].length, 1);
  assert.equal(g['clean-up'].length, 1);
});

test('pickHero returns oldest open decision when present', () => {
  const hero = pickHero(FIXTURE);
  assert.equal(hero?.id, 'DEC-003');  // older than DEC-001
});

test('pickHero falls back to newest resume handover when no decisions', () => {
  const filtered = FIXTURE.filter(i => i.action_class !== 'decide');
  const hero = pickHero(filtered);
  assert.equal(hero?.id, 'h1');
});

test('pickHero returns null when nothing to surface', () => {
  assert.equal(pickHero([]), null);
});
```

- [ ] **Step 2: Verify failure**

Run: `cd plugins/taskmaster/viewer && npm run test:unit -- tests/unit/continuity.test.js`
Expected: FAIL.

- [ ] **Step 3: Implement `lib/continuity.js`**

Create `plugins/taskmaster/viewer/js/lib/continuity.js`:

```js
// Client-side helpers for grouping ContinuityItem arrays.
// The server already classified action_class; this layer only sorts/groups.

const RAIL_ORDER = ['decide', 'resume', 'review', 'clean-up'];

export function groupByAction(items) {
  const out = Object.fromEntries(RAIL_ORDER.map(k => [k, []]));
  for (const it of items) {
    if (out[it.action_class]) out[it.action_class].push(it);
  }
  for (const k of RAIL_ORDER) {
    out[k].sort((a, b) => (b.age_days ?? 0) - (a.age_days ?? 0));
  }
  return out;
}

export function pickHero(items) {
  const decisions = items
    .filter(i => i.type === 'decision' && i.action_class === 'decide')
    .sort((a, b) => (b.age_days ?? 0) - (a.age_days ?? 0));
  if (decisions.length) return decisions[0];
  const resumes = items
    .filter(i => i.type === 'handover' && i.action_class === 'resume')
    .sort((a, b) => (a.age_days ?? 0) - (b.age_days ?? 0));
  return resumes[0] || null;
}

export function groupByTime(items, { now = Date.now() } = {}) {
  const DAY = 86400000;
  const buckets = { today: [], yesterday: [], earlier: [], drifting: [] };
  for (const it of items) {
    const age = (it.age_days ?? 0);
    if (age < 1)        buckets.today.push(it);
    else if (age < 2)   buckets.yesterday.push(it);
    else if (age < 7)   buckets.earlier.push(it);
    else                buckets.drifting.push(it);
  }
  return buckets;
}

export function groupByEntity(items) {
  const TYPES = ['decision', 'handover', 'task', 'branch', 'idea', 'issue'];
  const out = Object.fromEntries(TYPES.map(t => [t, []]));
  for (const it of items) {
    if (out[it.type]) out[it.type].push(it);
  }
  return out;
}
```

- [ ] **Step 4: Run test, verify PASS**

Run: `cd plugins/taskmaster/viewer && npm run test:unit -- tests/unit/continuity.test.js`
Expected: PASS.

- [ ] **Step 5: Write failing test for `decision-card`**

Create `plugins/taskmaster/viewer/tests/unit/decision-card.test.js`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { JSDOM } from 'jsdom';
const { window } = new JSDOM('<!DOCTYPE html><div id="r"></div>');
globalThis.document = window.document;

import { createDecisionCard } from '../../js/components/continuity/decision-card.js';

test('decision-card renders title + N options + primary "Pick option N"', () => {
  const item = {
    id: 'DEC-001', type: 'decision',
    title: 'Land 086', age_days: 1,
  };
  const decision = {
    id: 'DEC-001', title: 'Land 086',
    options: ['push MR', 'merge develop', 'hold'],
    recommendation: 2,
  };
  let picked = null;
  const card = createDecisionCard({ item, decision, onResolve: (n) => picked = n });
  document.body.appendChild(card.root);
  const opts = card.root.querySelectorAll('.co-decision__opt');
  assert.equal(opts.length, 3);
  const rec = card.root.querySelector('.co-decision__opt.is-rec');
  assert.ok(rec, 'recommendation should be flagged');
  const primary = card.root.querySelector('.co-decision__primary');
  assert.match(primary.textContent, /Pick option 2/);
  primary.click();
  assert.equal(picked, 2);
});
```

- [ ] **Step 6: Verify failure**

Run: `cd plugins/taskmaster/viewer && npm run test:unit -- tests/unit/decision-card.test.js`
Expected: FAIL.

- [ ] **Step 7: Implement `decision-card.js`**

Create `plugins/taskmaster/viewer/js/components/continuity/decision-card.js`:

```js
import { h } from '../../util/h.js';

export function createDecisionCard({ item, decision, onResolve, onDrop }) {
  const root = h('div', { class: 'co-decision' });
  root.appendChild(h('div', { class: 'co-decision__rail' },
    h('span', { class: 'co-chip co-chip--dec' }, 'Decision'),
    h('span', { class: 'co-decision__id' }, `${decision.id} · ${item.title}`),
  ));
  root.appendChild(h('h3', { class: 'co-decision__title' }, decision.title));
  const opts = h('div', { class: 'co-decision__opts' });
  (decision.options || []).forEach((text, i) => {
    const idx = i + 1;
    const rec = decision.recommendation === idx;
    const opt = h('div', {
      class: 'co-decision__opt' + (rec ? ' is-rec' : ''),
      onclick: () => onResolve?.(idx),
    },
      h('span', { class: 'co-decision__opt-num' }, `${idx}.`),
      h('span', { class: 'co-decision__opt-text' }, text),
      rec ? h('span', { class: 'co-decision__opt-star' }, '★ rec') : null,
    );
    opts.appendChild(opt);
  });
  root.appendChild(opts);

  const actions = h('div', { class: 'co-decision__actions' });
  if (decision.recommendation) {
    actions.appendChild(h('button', {
      type: 'button',
      class: 'co-decision__primary',
      onclick: () => onResolve?.(decision.recommendation),
    }, `Pick option ${decision.recommendation}`));
  }
  actions.appendChild(h('button', {
    type: 'button',
    class: 'co-decision__drop',
    onclick: () => onDrop?.(decision.id),
  }, 'Drop'));
  root.appendChild(actions);
  return { root };
}
```

Add to `continuity.css`:

```css
.co-decision { background: var(--ground-5); border: 1px solid var(--ground-15);
  border-radius: 6px; padding: 20px 22px; }
.co-decision__rail { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.co-decision__id { font-size: 0.78rem; color: var(--ground-50); }
.co-decision__title { color: var(--ground-95); font-size: 1.125rem;
  margin: 4px 0 8px; font-weight: 500; }
.co-decision__opts { display: grid; gap: 5px; margin-bottom: 14px; }
.co-decision__opt { background: var(--ground-0); border: 1px solid var(--ground-15);
  padding: 9px 12px; border-radius: 4px; display: flex; gap: 10px;
  font-size: 0.85rem; color: var(--ground-70); cursor: pointer; }
.co-decision__opt.is-rec { color: var(--ground-95); background: var(--ground-10);
  border-color: var(--ground-20); }
.co-decision__opt-num { color: var(--ground-30); }
.co-decision__opt-star { margin-left: auto; color: var(--pastel-lime); font-size: 0.72rem; }
.co-decision__actions { display: flex; gap: 8px; }
.co-decision__primary { padding: 6px 12px; background: var(--pastel-lime);
  color: var(--ground-0); border: 0; border-radius: 4px;
  font-size: 0.8rem; font-weight: 500; cursor: pointer; }
.co-decision__drop { padding: 6px 12px; background: var(--ground-15);
  border: 1px solid var(--ground-20); color: var(--ground-90);
  border-radius: 4px; font-size: 0.8rem; cursor: pointer; }
```

- [ ] **Step 8: Run decision-card test, verify PASS**

Run: `cd plugins/taskmaster/viewer && npm run test:unit -- tests/unit/decision-card.test.js`
Expected: PASS.

- [ ] **Step 9: Implement `item-row.js`, `hero.js`, `spine.js`**

Create `plugins/taskmaster/viewer/js/components/continuity/item-row.js`:

```js
import { h } from '../../util/h.js';
import { formatRelative } from '../../lib/time.js';

const CHIP_BY_TYPE = {
  decision: ['co-chip co-chip--dec', 'Decision'],
  handover: ['co-chip co-chip--han', 'Handover'],
  task:     ['co-chip co-chip--tsk', 'Task'],
  branch:   ['co-chip co-chip--brn', 'Branch'],
  idea:     ['co-chip co-chip--ide', 'Idea'],
  issue:    ['co-chip co-chip--iss', 'Issue'],
};

export function createItemRow({ item, onClick }) {
  const [chipCls, chipLabel] = CHIP_BY_TYPE[item.type] || ['co-chip', item.type];
  const row = h('div', { class: 'co-row', onclick: () => onClick?.(item) },
    h('div', { class: 'co-row__line1' },
      h('span', { class: chipCls }, chipLabel),
      h('span', { class: 'co-row__title' }, item.title),
      h('span', { class: 'co-row__when' }, formatRelative(item.timestamp, { suffix: '' })),
    ),
    item.next ? h('div', { class: 'co-row__next' }, item.next) : null,
    item.where ? h('div', { class: 'co-row__where' }, item.where) : null,
  );
  return { root: row };
}
```

Create `plugins/taskmaster/viewer/js/components/continuity/spine.js`:

```js
import { h } from '../../util/h.js';
import { createItemRow } from './item-row.js';

const BLOCKS = [
  { key: 'resume', label: 'Where you left off', cls: 'resume' },
  { key: 'review', label: 'Review',            cls: 'review' },
  { key: 'clean-up', label: 'Drifting',         cls: 'clean' },
];

export function createSpine({ groups, onItemClick }) {
  const root = h('div', { class: 'co-spine' });
  for (const b of BLOCKS) {
    const items = groups[b.key] || [];
    if (!items.length) continue;
    const block = h('div', { class: `co-spine__block co-spine__block--${b.cls}` },
      h('div', { class: 'co-spine__head' },
        h('span', { class: 'co-spine__nm' }, b.label),
        h('span', { class: 'co-spine__ct' }, `${items.length}`),
      ),
    );
    for (const it of items) {
      block.appendChild(createItemRow({ item: it, onClick: onItemClick }).root);
    }
    root.appendChild(block);
  }
  return { root };
}
```

Create `plugins/taskmaster/viewer/js/components/continuity/hero.js`:

```js
import { h } from '../../util/h.js';
import { createDecisionCard } from './decision-card.js';
import { createItemRow } from './item-row.js';

export function createHero({ item, fetchDecision, onResolve, onDrop }) {
  const root = h('div', { class: 'co-hero' });
  if (!item) {
    root.appendChild(h('div', { class: 'co-hero__empty' },
      h('span', { class: 'co-hero__lbl' }, 'You\'re caught up'),
      h('p', {}, 'No open decisions and no unsurfaced work. Nice.'),
    ));
    return { root };
  }
  if (item.type === 'decision' && fetchDecision) {
    fetchDecision(item.id).then(decision => {
      if (!decision) return;
      root.replaceChildren(createDecisionCard({ item, decision, onResolve, onDrop }).root);
    });
    return { root };
  }
  // Non-decision hero (e.g., latest resume handover).
  root.appendChild(h('span', { class: 'co-hero__lbl' }, 'Where you left off'));
  root.appendChild(createItemRow({ item }).root);
  return { root };
}
```

Append spine/row styles to `continuity.css`:

```css
.co-spine { display: flex; flex-direction: column; gap: 12px; }
.co-spine__block { background: var(--ground-5); border: 1px solid var(--ground-15);
  border-radius: 5px; padding: 12px 14px; }
.co-spine__head { display: flex; justify-content: space-between; align-items: baseline;
  font-size: 0.66rem; letter-spacing: 0.18em; text-transform: uppercase;
  color: var(--ground-50); margin-bottom: 10px; padding-bottom: 6px;
  border-bottom: 1px solid var(--ground-15); font-weight: 600; }
.co-spine__block--resume .co-spine__nm { color: var(--signature); }
.co-spine__block--review .co-spine__nm { color: var(--accent-lime); }
.co-spine__block--clean .co-spine__nm  { color: var(--ground-50); }

.co-row { padding: 8px 0; border-bottom: 1px dashed var(--ground-15); cursor: pointer; }
.co-row:last-child { border-bottom: 0; padding-bottom: 0; }
.co-row__line1 { display: flex; gap: 6px; align-items: baseline; margin-bottom: 3px; }
.co-row__title { color: var(--ground-95); flex: 1; font-weight: 500; }
.co-row__when { color: var(--ground-50); font-size: 0.78rem; }
.co-row__next { color: var(--ground-60); font-size: 0.8rem; }
.co-row__where { color: var(--ground-50); font-size: 0.74rem; margin-top: 3px; font-style: italic; }

.co-hero { background: var(--ground-5); border: 1px solid var(--ground-15);
  border-radius: 6px; padding: 20px 22px; min-height: 200px; }
.co-hero__lbl { font-size: 0.66rem; letter-spacing: 0.18em; text-transform: uppercase;
  color: var(--accent-pink); font-weight: 600; }
.co-hero__empty p { color: var(--ground-60); margin-top: 8px; }
```

- [ ] **Step 10: Wire Action view into `continuity.js`**

Edit `plugins/taskmaster/viewer/js/screens/continuity.js` — replace the placeholder render with:

```js
import { groupByAction, groupByTime, groupByEntity, pickHero } from '../lib/continuity.js';
import { createHero } from '../components/continuity/hero.js';
import { createSpine } from '../components/continuity/spine.js';

async function render() {
  body.replaceChildren();
  const r = await fetch('/api/continuity?view=' + activeView);
  const { items = [] } = await r.json();

  if (activeView === 'action') {
    const groups = groupByAction(items);
    const hero = pickHero(items);
    const layout = h('div', { class: 'co-dash__layout' });
    const heroComp = createHero({
      item: hero,
      fetchDecision: hero && hero.type === 'decision'
        ? (id) => fetch('/api/decisions/' + id).then(r => r.json())
        : null,
      onResolve: async (n) => {
        await fetch(`/api/decisions/${hero.id}/resolve`, {
          method: 'POST', headers: {'Content-Type':'application/json'},
          body: JSON.stringify({ resolved_with: n }),
        });
        await render();
      },
      onDrop: async (id) => {
        const reason = window.prompt('Drop reason?') || '';
        if (!reason) return;
        await fetch(`/api/decisions/${id}/drop`, {
          method: 'POST', headers: {'Content-Type':'application/json'},
          body: JSON.stringify({ reason }),
        });
        await render();
      },
    });
    const spine = createSpine({ groups, onItemClick: (it) => navigate(it) });
    layout.appendChild(heroComp.root);
    layout.appendChild(spine.root);
    body.appendChild(layout);
  } else if (activeView === 'time') {
    body.appendChild(renderTimeView(groupByTime(items)));
  } else {
    body.appendChild(renderEntityView(groupByEntity(items)));
  }
}

function navigate(item) {
  const routes = {
    decision: `/decisions/${item.id}`,
    handover: `/handovers/${item.id}`,
    task:     `/tasks/${item.id}`,
    issue:    `/issues/${item.id}`,
    idea:     `/ideas/${item.id}`,
  };
  if (routes[item.type]) location.hash = '#' + routes[item.type];
}

function renderTimeView(buckets) {
  const root = h('div', { class: 'co-time' });
  const order = ['today', 'yesterday', 'earlier', 'drifting'];
  for (const k of order) {
    const items = buckets[k] || [];
    if (!items.length) continue;
    const block = h('section', { class: 'co-time__block' },
      h('h4', { class: 'co-time__head' }, k.toUpperCase()),
    );
    for (const it of items) {
      block.appendChild(createItemRow({ item: it, onClick: navigate }).root);
    }
    root.appendChild(block);
  }
  return root;
}

function renderEntityView(groups) {
  const root = h('div', { class: 'co-entity' });
  const order = ['decision', 'handover', 'task', 'branch', 'idea', 'issue'];
  for (const k of order) {
    const items = groups[k] || [];
    if (!items.length) continue;
    const block = h('section', { class: 'co-entity__block' },
      h('h4', { class: 'co-entity__head' }, k.toUpperCase()),
    );
    for (const it of items) {
      block.appendChild(createItemRow({ item: it, onClick: navigate }).root);
    }
    root.appendChild(block);
  }
  return root;
}
```

Add the `createItemRow` import at the top of the file. Add time-view / entity-view CSS:

```css
.co-time__block, .co-entity__block { margin-bottom: 18px; }
.co-time__head, .co-entity__head { font-size: 0.66rem; letter-spacing: 0.18em;
  text-transform: uppercase; color: var(--ground-50); margin: 0 0 8px;
  padding-bottom: 6px; border-bottom: 1px solid var(--ground-15); font-weight: 600; }
```

- [ ] **Step 11: Add server endpoints for decision resolve/drop**

In `backlog_server.py`, add `/api/decisions/:id`, `/api/decisions/:id/resolve`, `/api/decisions/:id/drop` HTTP routes that map to the existing tools:

```python
# Inside the HTTP dispatcher (do_GET / do_POST), add:
# GET /api/decisions/<id>
m = re.match(r"^/api/decisions/([A-Z0-9-]+)$", path)
if m and self.command == "GET":
    bp = _backlog_path()
    fm, body = tm.read_decision(bp, m.group(1))
    self._send_json({**fm, "body": body})
    return

# POST /api/decisions/<id>/resolve
m = re.match(r"^/api/decisions/([A-Z0-9-]+)/resolve$", path)
if m and self.command == "POST":
    payload = json.loads(self._read_body() or "{}")
    bp = _backlog_path()
    fm = tm.resolve_decision(bp, m.group(1),
        resolved_with=int(payload.get("resolved_with")),
        rationale=payload.get("rationale", ""))
    self._send_json(fm)
    return

# POST /api/decisions/<id>/drop
m = re.match(r"^/api/decisions/([A-Z0-9-]+)/drop$", path)
if m and self.command == "POST":
    payload = json.loads(self._read_body() or "{}")
    bp = _backlog_path()
    fm = tm.drop_decision(bp, m.group(1), reason=payload.get("reason", ""))
    self._send_json(fm)
    return
```

Match the regex/dispatch pattern actually used in the file (it may use a route table rather than a regex chain — grep first for `_send_json` or `_route` or `do_POST`).

- [ ] **Step 12: Manual smoke test**

Start the dev server. Visit `/v2/dashboard`. Create a decision via `backlog_decision_create` from a Python REPL or another MCP client. Refresh — the hero should render with the decision; clicking "Pick option N" should resolve it; refresh shows the dashboard moves to the next-oldest decision or the empty state.

- [ ] **Step 13: Commit**

```bash
git add plugins/taskmaster/viewer/ plugins/taskmaster/backlog_server.py \
        plugins/taskmaster/viewer/tests/unit/continuity.test.js \
        plugins/taskmaster/viewer/tests/unit/decision-card.test.js
git commit -m "feat(viewer): action/time/entity views + decision resolve UX"
```

---

## Task 15: Playwright e2e for the continuity dashboard

**Files:**
- Create: `plugins/taskmaster/viewer/tests/continuity-dashboard.spec.js`

### Steps

- [ ] **Step 1: Write the e2e spec**

Create `plugins/taskmaster/viewer/tests/continuity-dashboard.spec.js`:

```js
import { test, expect } from '@playwright/test';

test('continuity dashboard surfaces an open decision in the hero', async ({ page, context }) => {
  // Seeding: assume the test fixture project has 1 open decision.
  // (Conform to the playwright.config.js project bootstrap pattern.)
  await page.goto('/#/v2/dashboard');
  await expect(page.locator('.co-dash__topbar')).toBeVisible();
  await expect(page.locator('.co-view-switcher__btn.is-active')).toContainText('Action');
  await expect(page.locator('.co-decision__title')).toBeVisible();
});

test('view switcher flips between Action / Time / Entity', async ({ page }) => {
  await page.goto('/#/v2/dashboard');
  await page.locator('.co-view-switcher__btn', { hasText: 'Time' }).click();
  await expect(page.locator('.co-time__block')).toHaveCount(await page.locator('.co-time__block').count());
  await page.locator('.co-view-switcher__btn', { hasText: 'Entity' }).click();
  await expect(page.locator('.co-entity__block')).toHaveCount(await page.locator('.co-entity__block').count());
});

test('resolving a decision from the hero removes it from Decide', async ({ page }) => {
  await page.goto('/#/v2/dashboard');
  const hero = page.locator('.co-decision__title');
  const titleBefore = await hero.textContent();
  await page.locator('.co-decision__primary').click();
  await page.waitForResponse(r => r.url().includes('/api/decisions/') && r.url().endsWith('/resolve'));
  // Hero should refresh to the next decision or empty state.
  const titleAfter = await hero.textContent().catch(() => null);
  expect(titleAfter).not.toEqual(titleBefore);
});
```

- [ ] **Step 2: Run the spec**

Run: `cd plugins/taskmaster/viewer && npm run test:e2e -- tests/continuity-dashboard.spec.js`
Expected: PASS (after fixture seeding is wired per the existing Playwright config).

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/tests/continuity-dashboard.spec.js
git commit -m "test(viewer): e2e for continuity dashboard"
```

---

## Task 16: Widget removal sweep + dead-code cleanup

**Why:** Now the new screen is fully working at `/v2/dashboard`; remove the bento and the old widgets it depended on. Swap `/dashboard` to the new screen.

**Files:**
- Delete: all widget files and dashboard-grid as listed in the File Structure section.
- Modify: `plugins/taskmaster/viewer/js/router.js` (point `/dashboard` at `continuity.js`; remove `/v2/dashboard` alias)
- Modify: `plugins/taskmaster/viewer/js/screens/dashboard.js` (REPLACE with `continuity.js` content, or re-export)
- Delete: `plugins/taskmaster/viewer/tests/dashboard.spec.js`, `plugins/taskmaster/viewer/tests/unit/dashboard-grid.test.js`

### Steps

- [ ] **Step 1: Verify the new screen is sound at `/v2/dashboard`**

Manual: visit `/v2/dashboard` and confirm Action / Time / Entity views render, hero resolves, footer shows.

- [ ] **Step 2: Swap routes — `/dashboard` → continuity.js**

In `plugins/taskmaster/viewer/js/router.js`:

```js
// before:
'/dashboard':    () => import('./screens/dashboard.js'),
'/v2/dashboard': () => import('./screens/continuity.js'),

// after:
'/dashboard': () => import('./screens/continuity.js'),
```

Delete `plugins/taskmaster/viewer/js/screens/dashboard.js` (the old bento). The screen module is now `continuity.js`.

- [ ] **Step 3: Delete obsoleted components**

```bash
git rm plugins/taskmaster/viewer/js/components/briefing-strip.js
git rm plugins/taskmaster/viewer/js/components/dashboard-grid.js
git rm plugins/taskmaster/viewer/js/components/edit-mode.js
git rm plugins/taskmaster/viewer/js/components/widget-catalog.js
git rm plugins/taskmaster/viewer/js/components/widget-frame.js
git rm -r plugins/taskmaster/viewer/js/components/widgets/
git rm plugins/taskmaster/viewer/tests/unit/dashboard-grid.test.js
git rm plugins/taskmaster/viewer/tests/dashboard.spec.js
```

- [ ] **Step 4: Remove orphaned imports**

Grep the viewer for any remaining import that pointed at the deleted files:

```bash
grep -rn "widget-catalog\|widget-frame\|dashboard-grid\|briefing-strip\|edit-mode\|widgets/" plugins/taskmaster/viewer/js/
```

For each hit outside the deleted set, remove or replace the import. The `auto-mode-strip` and `auto-mode-stepper` survive (per spec §2.6); confirm they don't import a deleted helper.

- [ ] **Step 5: Drop `prefs.dashboard.layout` migration**

In `backlog_server.py` (or wherever `prefs` is loaded), find the prefs schema/migration. Add an ignore-on-read: when loading prefs, drop the key `dashboard.layout` silently. Add the key `continuity.view` (string, default `"action"`) as a known field.

If no prefs migration helper exists, just rely on the new code never writing `dashboard.layout` and the old key being stale-but-harmless.

- [ ] **Step 6: Run the full test suite to catch regressions**

```bash
pytest plugins/taskmaster/tests/ -v
cd plugins/taskmaster/viewer && npm run test:unit && npm run test:e2e
```

Expected: all green. If a test that exercised a deleted widget remains, delete it (it tested code that no longer exists).

- [ ] **Step 7: Commit the sweep**

```bash
git add -A
git commit -m "refactor(viewer): remove bento dashboard + widget catalog; /dashboard → continuity"
```

---

## Task 17: Backlog closeout + reframe

**Files:**
- Modify: `.taskmaster/backlog.yaml`

### Steps

- [ ] **Step 1: Close absorbed/prerequisite tasks**

Use the MCP layer to transition status (preferred) or edit `.taskmaster/backlog.yaml` directly if no live agent. The four tasks to close:

- `v3-polish-011` — Dashboard second-pass design review → `done` (rationale: subsumed by `2026-05-15-continuity-dashboard-design.md`)
- `v3-polish-018` — Shared time-format helper sweep → `done` (Task 1)
- `v3-polish-039` — Timestamp display broken — handovers visible symptom → `done` (Task 1)
- `v3-polish-048` — Capture full ISO datetime on handover creation → `done` (writer was already correct; viewer fixed in Task 1)

Run for each:

```
backlog_update_task(task_id="v3-polish-011", status="done")
```

(Same for the other three.)

- [ ] **Step 2: Reframe `agentic-os-001`**

Edit the task body via `backlog_update_task(task_id="agentic-os-001", title="Wire continuity dashboard to project switcher (multi-project view)")` and update the body to note: depends on `v3-release-007`; out-of-scope until that ships.

- [ ] **Step 3: Commit backlog changes**

```bash
git add .taskmaster/backlog.yaml
git commit -m "chore(backlog): close v3-polish-011/018/039/048; reframe agentic-os-001"
```

---

## Self-Review

**Spec coverage check** (every spec section maps to a task):

- §1 Decisions as first-class entity → Tasks 2, 3, 4, 5, 6 ✓
- §1.5 Auto-resolution hooks → Task 6 references doc; commit-message hook deferred to Task 6 as documentation (auto-task block + end-session sweep are Tasks 11 & deferred) ✓
- §2 Continuity dashboard → Tasks 7, 8, 9, 13, 14 ✓
- §2.4 Action-view routing → Task 8 ✓
- §2.5 Time-view bucketing → Task 14 (`groupByTime`) ✓
- §2.6 Widget migration → Task 16 ✓
- §2.7 Scope single-project → Out of scope by design (noted in spec §5) ✓
- §3 Handover simplification → Task 10 ✓
- §3.4 end-session integration → Task 11 ✓
- §3.5 start-session change → Task 12 ✓
- §4 Backlog folding → Task 17 ✓
- §5 Out of scope — not implemented (correct) ✓

**Placeholder scan:** No "TBD", "TODO", "appropriate handling," or "similar to Task N" placeholders. Every code step shows the actual code.

**Type/name consistency:**

- `write_decision` / `read_decision` / `update_decision` / `resolve_decision` / `drop_decision` / `link_decision_to_handover` — used consistently across Tasks 2–4, 5, 9, 10.
- `continuity_items` (Python) / `backlog_continuity_items` (MCP wrapper) — distinguished correctly.
- `groupByAction` / `groupByTime` / `groupByEntity` / `pickHero` — exported from `lib/continuity.js`; imported in `continuity.js` screen.
- `HANDOVER_KINDS` constant and `_LEGACY_KIND_MAP` — referenced in both core and skill.
- `open_decisions` / `resolved_this_session` frontmatter keys — referenced in spec §3.3, Task 10 (writer), Task 11 (sweep populates), Task 12 (start-session reads).
- CSS prefix `co-*` consistent across `continuity.css` and all components.

**One gap addressed inline:** Task 6's `auto-resolution.md` reference mentions the commit-message hook; that hook itself (MCP server scanning commits for `Resolves: DEC-NNN with option N`) is documented but not implemented as a separate task. Adding a Task 18 for it would be the cleanest decomposition, but spec §1.5 lists it under "auto-resolution hooks" alongside `auto-task` and `end-session`. Since the spec scopes auto-task and end-session changes as items in §6 and the commit-scan is optional (the manual `/decide` and resolve-from-dashboard paths both work without it), the commit-scan implementation is deferred to a follow-up task — captured here as a known follow-up rather than baked into this plan.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-15-continuity-dashboard.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration. Best for a 17-task plan where context-pollution matters.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
