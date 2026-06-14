# Task Bundles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `bundle` execution slug so same-surface tasks execute together in one worktree with one merged lifecycle while staying discrete in the backlog (own ID/status/gates/completion).

**Architecture:** Additive feature, TDD throughout. A new slim `bundle` field + slug validation, a find-by-bundle helper, a bundle-aware `backlog_pick_task` that binds all members and records a `_session_bundle` context, a structured detection-fallback from blast-radius, a viewer badge, and three skill updates (pick / review-gate / end-session) for one-sweep execution with per-member verify, merge fan-out, and descope. No new entity, no new viewer screen.

**Tech Stack:** Python (FastMCP server), pytest (`tmp_taskmaster` / `tm_epic_phase` fixtures in `tests/conftest.py`), vanilla ES-module viewer JS with `node --test` + jsdom.

**Spec:** `docs/superpowers/specs/2026-06-11-task-bundle-design.md` (design-review PASS, revised 2026-06-14 — see its "Design-review resolutions").

**Conventions:**
- All `pytest` commands run from `plugins/taskmaster/`; viewer `npm` from `plugins/taskmaster/viewer/`.
- Tests call `backlog_server` functions directly under the `tmp_taskmaster` / `tm_epic_phase` fixtures; pass explicit `task_id=` for determinism.
- Line numbers are drift-prone hints; relocate by symbol.

**Sequencing:** Land this **after** the auto-mode removal (`remove-auto-mode-001`) — the bundle pickup replaces the per-task worktree mandate in `skills/pick-task/SKILL.md`, and merging both against that file at once invites conflicts.

---

## Task 1: `bundle` field plumbing + slug-format validation

**Files:**
- Modify: `taskmaster_v3.py` (`SLIM_FIELDS["task"]`, hint :112-122)
- Modify: `backlog_server.py` (`ALLOWED_FIELDS` hint :5368; `backlog_add_task` hint :4637-4778; new `_valid_bundle_slug`)
- Test: `tests/test_bundle_field.py` (new)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_bundle_field.py`:

```python
"""Task bundle: slug field plumbing + validation."""
import backlog_server


def test_add_task_accepts_bundle(tm_epic_phase):
    backlog_server.backlog_add_task(
        title="A", epic="test-epic", phase="dev", task_id="b-1", bundle="asset-ux")
    out = backlog_server.backlog_get_task("b-1", verbose=True)
    assert "asset-ux" in out


def test_bundle_present_in_slim_read(tm_epic_phase):
    backlog_server.backlog_add_task(
        title="A", epic="test-epic", phase="dev", task_id="b-1", bundle="asset-ux")
    slim = backlog_server.backlog_get_task("b-1")  # slim default
    assert "asset-ux" in slim


def test_bad_slug_rejected_on_add(tm_epic_phase):
    out = backlog_server.backlog_add_task(
        title="A", epic="test-epic", phase="dev", task_id="b-1", bundle="Bad Slug!")
    assert out.lower().startswith("error")


def test_update_sets_and_clears_bundle(tm_epic_phase):
    backlog_server.backlog_add_task(title="A", epic="test-epic", phase="dev", task_id="b-1")
    assert "error" not in backlog_server.backlog_update_task("b-1", "bundle", "asset-ux").lower()
    # empty value clears (descope) and must be allowed
    assert "error" not in backlog_server.backlog_update_task("b-1", "bundle", "").lower()


def test_update_bad_slug_rejected(tm_epic_phase):
    backlog_server.backlog_add_task(title="A", epic="test-epic", phase="dev", task_id="b-1")
    assert backlog_server.backlog_update_task("b-1", "bundle", "Bad!").lower().startswith("error")
```

- [ ] **Step 2: Run to confirm failure**

Run: `python -m pytest tests/test_bundle_field.py -q`
Expected: FAIL — `backlog_add_task` has no `bundle` param / field not allowed.

- [ ] **Step 3: Add the slug validator + `SLIM_FIELDS`**

In `taskmaster_v3.py`, add `"bundle"` to the `SLIM_FIELDS["task"]` tuple (after `"epic"` is a natural slot).

In `backlog_server.py`, near `ALLOWED_FIELDS`, add:
```python
import re as _re_bundle  # if `re` not already imported at module top; otherwise reuse `re`

_BUNDLE_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,40}$")

def _valid_bundle_slug(value: str) -> bool:
    """Empty string clears the bundle (descope); otherwise must be lowercase kebab."""
    return value == "" or bool(_BUNDLE_SLUG_RE.match(value))
```
Add `"bundle"` to the `ALLOWED_FIELDS` set.

- [ ] **Step 4: Validate in `backlog_update_task` and add the `backlog_add_task` param**

In `backlog_update_task`, where the field write happens (after the `ALLOWED_FIELDS` check, hint :5443), add a bundle-specific guard before the generic `task[field] = value`:
```python
if field == "bundle" and not _valid_bundle_slug(value):
    return f"Error: invalid bundle slug `{value}` (lowercase kebab, 2-41 chars)."
```

In `backlog_add_task` (hint :4637), add `bundle: str = ""` to the signature, and after the explicit-field construction (hint :4698-4752):
```python
if bundle:
    if not _valid_bundle_slug(bundle):
        return f"Error: invalid bundle slug `{bundle}` (lowercase kebab, 2-41 chars)."
    new_task["bundle"] = bundle
```
Also surface the param in the MCP docstring's Args.

- [ ] **Step 5: Run tests to confirm pass**

Run: `python -m pytest tests/test_bundle_field.py -q`
Expected: PASS (5 tests).

- [ ] **Step 6: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_bundle_field.py
git commit -m "feat(taskmaster): bundle slug field + validation (task-bundle-001)"
```

---

## Task 2: `_find_tasks_by_bundle` helper + birth-time `sub_repo` validation

**Files:**
- Modify: `backlog_server.py` (new `_find_tasks_by_bundle`; cross-check in `backlog_add_task` + `backlog_update_task`)
- Test: `tests/test_bundle_members.py` (new)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_bundle_members.py`:

```python
"""Task bundle: member lookup + birth-time sub_repo validation."""
import backlog_server
from backlog_server import _find_tasks_by_bundle, _load_backlog


def _add(task_id, bundle="", sub_repo=""):
    backlog_server.backlog_add_task(
        title=task_id, epic="test-epic", phase="dev",
        task_id=task_id, bundle=bundle, sub_repo=sub_repo)


def test_find_returns_only_members(tm_epic_phase):
    _add("b-1", bundle="ux"); _add("b-2", bundle="ux"); _add("b-3", bundle="other")
    data = _load_backlog()
    ids = {t["id"] for t in _find_tasks_by_bundle(data, "ux")}
    assert ids == {"b-1", "b-2"}


def test_birth_sub_repo_mismatch_rejected_on_add(tm_epic_phase):
    _add("b-1", bundle="ux", sub_repo="api")
    out = backlog_server.backlog_add_task(
        title="b-2", epic="test-epic", phase="dev",
        task_id="b-2", bundle="ux", sub_repo="web")
    assert "sub_repo" in out.lower() and out.lower().startswith("error")


def test_birth_sub_repo_match_allowed(tm_epic_phase):
    _add("b-1", bundle="ux", sub_repo="api")
    out = backlog_server.backlog_add_task(
        title="b-2", epic="test-epic", phase="dev",
        task_id="b-2", bundle="ux", sub_repo="api")
    assert not out.lower().startswith("error")


def test_update_into_bundle_sub_repo_mismatch_rejected(tm_epic_phase):
    _add("b-1", bundle="ux", sub_repo="api")
    _add("b-2", sub_repo="web")
    out = backlog_server.backlog_update_task("b-2", "bundle", "ux")
    assert "sub_repo" in out.lower() and out.lower().startswith("error")
```

- [ ] **Step 2: Run to confirm failure**

Run: `python -m pytest tests/test_bundle_members.py -q`
Expected: FAIL — `_find_tasks_by_bundle` does not exist; no sub_repo cross-check.

- [ ] **Step 3: Add the helper**

In `backlog_server.py` near the other `_find_*` helpers:
```python
def _find_tasks_by_bundle(data: dict, slug: str) -> list[dict]:
    """All non-archived tasks sharing bundle `slug` (across all epics)."""
    return [t for t in data.get("tasks", [])
            if t.get("bundle") == slug and t.get("status") != "archived"]
```
(If tasks are nested under epics rather than a flat `tasks` list in this backlog shape, iterate the same structure `_find_task` uses — match its traversal.)

- [ ] **Step 4: Add the birth-time cross-check**

Factor a small validator and call it from both `backlog_add_task` (when `bundle` is set) and `backlog_update_task` (when `field == "bundle"` and value non-empty):
```python
def _bundle_sub_repo_conflict(data, slug, sub_repo, exclude_id=""):
    for m in _find_tasks_by_bundle(data, slug):
        if m["id"] == exclude_id:
            continue
        if (m.get("sub_repo") or "") != (sub_repo or ""):
            return m["id"]
    return None
```
In `backlog_add_task`, before writing `new_task["bundle"]`:
```python
conflict = _bundle_sub_repo_conflict(data, bundle, sub_repo)
if conflict:
    return f"Error: bundle `{bundle}` sub_repo mismatch with member `{conflict}` (one worktree = one repo)."
```
In `backlog_update_task` bundle branch, use the task's own `sub_repo` and `exclude_id=task_id`.

- [ ] **Step 5: Run tests to confirm pass**

Run: `python -m pytest tests/test_bundle_members.py tests/test_bundle_field.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_bundle_members.py
git commit -m "feat(taskmaster): find-by-bundle helper + birth-time sub_repo validation (task-bundle-001)"
```

---

## Task 3: Bundle-aware `backlog_pick_task` + `_session_bundle`

**Files:**
- Modify: `backlog_server.py` (`_session_bundle` global hint near :317; `_get_session_bundle`; `backlog_pick_task` hint :4808; `_build_worktree_instruction` hint :4781)
- Test: `tests/test_bundle_pick.py` (new)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_bundle_pick.py`:

```python
"""Task bundle: pick binds the whole bundle into one worktree."""
import backlog_server


def _add(task_id, bundle="ux", sub_repo="", lane=""):
    backlog_server.backlog_add_task(
        title=task_id, epic="test-epic", phase="dev",
        task_id=task_id, bundle=bundle, sub_repo=sub_repo)
    if lane:
        backlog_server.backlog_update_task(task_id, "lane", lane)


def test_pick_member_binds_all_members(tm_epic_phase):
    _add("b-1"); _add("b-2")
    out = backlog_server.backlog_pick_task("b-1")
    assert "b-1" in out and "b-2" in out                      # announces membership
    t1 = backlog_server.backlog_get_task("b-1")
    t2 = backlog_server.backlog_get_task("b-2")
    assert "in-progress" in t1 and "in-progress" in t2        # both bound
    assert "feature/ux" in out and ".worktrees/ux" in out     # shared, slug-based


def test_pick_records_session_bundle(tm_epic_phase):
    _add("b-1"); _add("b-2")
    backlog_server.backlog_pick_task("b-1")
    sb = backlog_server._get_session_bundle()
    assert sb and sb["slug"] == "ux" and set(sb["members"]) == {"b-1", "b-2"}


def test_pick_uses_strictest_lane(tm_epic_phase):
    _add("b-1", lane="express"); _add("b-2", lane="full")
    out = backlog_server.backlog_pick_task("b-1")
    assert "full" in out.lower()                              # bundle execution lane


def test_repick_bound_bundle_idempotent(tm_epic_phase):
    _add("b-1"); _add("b-2")
    backlog_server.backlog_pick_task("b-1")
    out = backlog_server.backlog_pick_task("b-2")             # re-pick another member
    assert "feature/ux" in out and "error" not in out.lower()


def test_non_bundle_pick_unchanged(tm_epic_phase):
    backlog_server.backlog_add_task(title="solo", epic="test-epic", phase="dev", task_id="s-1")
    out = backlog_server.backlog_pick_task("s-1")
    assert "feature/s-1" in out                               # per-task path preserved
```

- [ ] **Step 2: Run to confirm failure**

Run: `python -m pytest tests/test_bundle_pick.py -q`
Expected: FAIL — pick is single-task; no `_get_session_bundle`; no shared slug path.

- [ ] **Step 3: Add `_session_bundle` state + accessor**

In `backlog_server.py` near `_session_task` (hint :317):
```python
_session_bundle = None  # {"slug","sub_repo","branch","worktree","members":[id], "lane"}

def _get_session_bundle():
    return _session_bundle

def _set_session_bundle(b):
    global _session_bundle
    _session_bundle = b
```

- [ ] **Step 4: Make `backlog_pick_task` bundle-aware**

At the top of `backlog_pick_task`, after loading the task, branch on `task.get("bundle")`:
```python
slug = task.get("bundle")
if slug:
    members = _find_tasks_by_bundle(data, slug)
    # validate shared sub_repo
    sub_repos = {(m.get("sub_repo") or "") for m in members}
    if len(sub_repos) > 1:
        return f"Error: bundle `{slug}` spans multiple sub_repos {sub_repos}; cannot pick."
    sub_repo = next(iter(sub_repos))
    branch = f"feature/{slug}"
    worktree = (f"{sub_repo}/.worktrees/{slug}" if sub_repo else f".worktrees/{slug}")
    lane = _strictest_lane([m.get("lane") for m in members])
    for m in members:
        # bundle-aware lock conflict
        if m.get("locked_by") and m["locked_by"] != SESSION_ID and not force:
            return (f"Error: `{m['id']}` is a member of bundle `{slug}` "
                    f"locked by another session ({m['locked_by']}). Use force=True to steal.")
    for m in members:
        m["status"] = "in-progress"
        m["locked_by"] = SESSION_ID
        m["branch"] = branch
        m["worktree"] = worktree
    _set_session_task(task, epic)                # picked member stays "current task"
    _set_session_bundle({"slug": slug, "sub_repo": sub_repo, "branch": branch,
                         "worktree": worktree, "members": [m["id"] for m in members],
                         "lane": lane})
    _save_backlog(data)
    member_ids = ", ".join(m["id"] for m in members)
    instr = _build_worktree_instruction(slug, sub_repo, branch, worktree)
    return (f"Picking bundle `{slug}`: {member_ids}.\nExecution lane: {lane}.\n{instr}")
```
Add the lane helper near `VALID_LANES`:
```python
def _strictest_lane(lanes):
    order = {"express": 0, "standard": 1, "full": 2}
    present = [l for l in lanes if l in order] or ["standard"]
    return max(present, key=lambda l: order[l])
```
`_build_worktree_instruction(slug, sub_repo, branch, worktree)` already accepts an id-or-slug first arg and derives the path from it — pass the slug so the instruction reads `.worktrees/<slug>` / `feature/<slug>`. (Verify its body uses the passed `worktree`/`branch` when provided rather than re-deriving from the first arg; if it hard-derives, parametrize it to accept the explicit `worktree`/`branch`.)

- [ ] **Step 5: Run tests to confirm pass**

Run: `python -m pytest tests/test_bundle_pick.py -q`
Expected: PASS (5 tests).

- [ ] **Step 6: Run the full Python suite (regression)**

Run: `python -m pytest tests/ -q`
Expected: PASS — non-bundle pick path unchanged; `_session_task` semantics intact.

- [ ] **Step 7: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_bundle_pick.py
git commit -m "feat(taskmaster): bundle-aware pick + _session_bundle + strictest lane (task-bundle-001)"
```

---

## Task 4: Structured predictive blast-radius (detection fallback)

**Files:**
- Modify: `backlog_server.py` (`backlog_blast_radius` — add `structured` flag) and/or `blast_radius.py` (`analyze_predictive` hint :530)
- Test: `tests/test_bundle_detection.py` (new)

- [ ] **Step 1: Write the failing test**

Create `tests/test_bundle_detection.py`:

```python
"""Task bundle: structured predictive blast-radius for detection-fallback."""
import json
import backlog_server


def test_structured_predictive_returns_overlap_list(tm_epic_phase):
    backlog_server.backlog_add_task(
        title="a", epic="test-epic", phase="dev", task_id="t-1",
        anchors="plugins/x/foo.py")
    backlog_server.backlog_add_task(
        title="b", epic="test-epic", phase="dev", task_id="t-2",
        anchors="plugins/x/foo.py")
    out = backlog_server.backlog_blast_radius("t-1", mode="predictive", structured=True)
    data = out if isinstance(out, (list, dict)) else json.loads(out)
    overlaps = data["overlapping_tasks"] if isinstance(data, dict) else data
    ids = {o["task_id"] for o in overlaps}
    assert "t-2" in ids
    assert all({"task_id", "status", "shared_paths"} <= set(o) for o in overlaps)
```

- [ ] **Step 2: Run to confirm failure**

Run: `python -m pytest tests/test_bundle_detection.py -q`
Expected: FAIL — `backlog_blast_radius` has no `structured` param (returns markdown).

- [ ] **Step 3: Add the structured path**

In `backlog_blast_radius`, add `structured: bool = False`. When `mode == "predictive"` and `structured`, return the raw `analyze_predictive(task, all_tasks)` dict (which already holds `overlapping_tasks` as `[{task_id, title, status, shared_paths}]`) as a JSON string instead of the formatted markdown. Leave the default markdown path unchanged.

- [ ] **Step 4: Run test to confirm pass**

Run: `python -m pytest tests/test_bundle_detection.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_bundle_detection.py
git commit -m "feat(taskmaster): structured predictive blast-radius for bundle detection (task-bundle-001)"
```

---

## Task 5: Viewer bundle badge

**Files:**
- Modify: `viewer/js/components/card.js` (chip row, hint :106)
- Test: `viewer/tests/unit/card-bundle.test.js` (new)

- [ ] **Step 1: Write the failing test**

Create `viewer/tests/unit/card-bundle.test.js` (mirror the import style of the existing `tests/unit/*.test.js`):

```javascript
import { test } from 'node:test';
import assert from 'node:assert';
import { JSDOM } from 'jsdom';
import { renderCard } from '../../js/components/card.js';

test('card renders a bundle badge when task.bundle is set', () => {
  const dom = new JSDOM('<!DOCTYPE html><body></body>');
  global.document = dom.window.document;
  const el = renderCard({ id: 't-1', title: 'X', status: 'todo', bundle: 'asset-ux' });
  assert.match(el.outerHTML, /asset-ux/);
});

test('card renders no bundle badge when task.bundle is absent', () => {
  const dom = new JSDOM('<!DOCTYPE html><body></body>');
  global.document = dom.window.document;
  const el = renderCard({ id: 't-2', title: 'Y', status: 'todo' });
  assert.doesNotMatch(el.outerHTML, /tm-bundle/);
});
```
(Confirm `renderCard`'s real export name + arity against `card.js`; adjust the call if it takes an options object.)

- [ ] **Step 2: Run to confirm failure**

Run (from `viewer/`): `node --test tests/unit/card-bundle.test.js`
Expected: FAIL — no bundle badge in output.

- [ ] **Step 3: Add the badge**

In `card.js`, in the chip row (hint :106, alongside the `task.sub_repo` chip at :154), add:
```javascript
if (task.bundle) {
  const b = document.createElement('span');
  b.className = 'tm-chip tm-bundle';
  b.textContent = `⬢ ${task.bundle}`;  // hexagon glyph + slug
  chipRow.appendChild(b);
}
```
(Match the existing chip-construction idiom in this file — reuse the same element/class helper the other chips use rather than raw `createElement` if one exists.)

- [ ] **Step 4: Run test to confirm pass**

Run (from `viewer/`): `node --test tests/unit/card-bundle.test.js`
Expected: PASS.

- [ ] **Step 5: Run the full viewer unit suite**

Run (from `viewer/`): `npm run test:unit`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/card.js plugins/taskmaster/viewer/tests/unit/card-bundle.test.js
git commit -m "feat(taskmaster): viewer bundle badge on kanban cards (task-bundle-001)"
```

---

## Task 6: `pick-task` skill — bundle pickup + detection fallback

**Files:**
- Modify: `skills/pick-task/SKILL.md` (Step 8 worktree mandate, hint :77-85)
- Possibly add: `skills/pick-task/references/bundles.md` (keep SKILL.md within its body budget)

- [ ] **Step 1: Replace the per-task worktree mandate with a bundle branch**

In Step 8, when the picked task has a `bundle` slug, the worktree/branch are slug-based and `backlog_pick_task` binds all members in one call — the skill announces membership and uses the returned shared instruction instead of `git worktree add .worktrees/{task-id}`. When no slug, the existing per-task flow is unchanged.

- [ ] **Step 2: Add the detection-fallback step**

Add a step: when a picked task has no slug, call `backlog_blast_radius(task_id, mode="predictive", structured=True)`, filter `overlapping_tasks` to `status == "todo"` with strong `shared_paths` overlap, and — on Claude's own authority — set the same `bundle` slug on them via `backlog_update_task`, announcing in one line ("also sweeping ps-177 in, same files"). The announcement is the veto window.

- [ ] **Step 3: Keep within the skill body budget**

If the additions push `skills/pick-task/SKILL.md` over its `SKILL_BUDGETS` entry, move the detailed bundle protocol into `skills/pick-task/references/bundles.md` and link it from SKILL.md (progressive disclosure — match how other references are linked).

- [ ] **Step 4: Verify skill lint**

Run: `python -m pytest tests/test_skill_body_budgets.py tests/test_skill_description_budgets.py tests/test_skill_catalog_smoke.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/skills/pick-task/
git commit -m "feat(taskmaster): pick-task bundle pickup + detection fallback (task-bundle-001)"
```

---

## Task 7: `review-gate` skill — per-member verdict + descope

**Files:**
- Modify: `skills/review-gate/SKILL.md`

- [ ] **Step 1: Add per-member verdict mode**

When `_get_session_bundle()` is set, the review gate runs once but verifies **each member's acceptance criteria separately**, emitting N verdicts in one report. Each member's verdict is recorded with `backlog_record_gate(member, "review-gate", verdict=..., spec_path=<shared spec>)` — loop over `members`, same shared `spec_path`.

- [ ] **Step 2: Add the descope path**

A failing member must be fixed (fix-up pass in the same worktree) or descoped. Descope steps (explicit, never silent): `backlog_update_task(member, "bundle", "")`, `backlog_update_task(member, "status", "todo")`, clear `branch`/`worktree`, and Claude edits the shared spec doc to excise that member's section (no document-mutation tool by design). The branch then merges atomically without it.

- [ ] **Step 3: Verify skill lint + commit**

Run: `python -m pytest tests/test_skill_body_budgets.py tests/test_skill_description_budgets.py -q`
Expected: PASS.
```bash
git add plugins/taskmaster/skills/review-gate/
git commit -m "feat(taskmaster): review-gate per-member verdict + descope path (task-bundle-001)"
```

---

## Task 8: `end-session` skill — per-member completion + merge fan-out + cleanup timing

**Files:**
- Modify: `skills/end-session/SKILL.md` (Step 7 worktree cleanup, hint :72), `skills/end-session/references/edge-cases.md` (Multiple-tasks-changed case, hint :17)

- [ ] **Step 1: Per-member completion records**

For a bundle, each passing member completes via `backlog_complete_task(member)` (its own completion record) — override the `edge-cases.md` "secondary = `backlog_update_task` status-only" shortcut for bundles, since the spec mandates own records.

- [ ] **Step 2: Merge fan-out loop**

On the single merge event, loop `backlog_record_merge(member, rung, sha)` over the bundle members from `_get_session_bundle()` (same rung + sha). No new batch tool — the skill owns the loop.

- [ ] **Step 3: Cleanup timing**

Offer `git worktree remove .worktrees/<slug>` (slug, not task-id) **only when the last member has left the bundle** (all members `done` or descoped) — check `_get_session_bundle()` membership before offering cleanup.

- [ ] **Step 4: Verify skill lint + commit**

Run: `python -m pytest tests/test_skill_body_budgets.py -q`
Expected: PASS.
```bash
git add plugins/taskmaster/skills/end-session/
git commit -m "feat(taskmaster): end-session bundle completion + merge fan-out + cleanup timing (task-bundle-001)"
```

---

## Task 9: Version bump + CHANGELOG + final verification

Additive surface (new `bundle` field/param, `structured` blast-radius flag) → **minor** bump.

**Files:**
- Modify: `plugins/taskmaster/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `plugins/taskmaster/CHANGELOG.md`

- [ ] **Step 1: Bump the three parts**

Bump the minor from whatever ships at implementation time: if auto-mode removal (`3.17.0`) has landed, this is `3.18.0`; otherwise `3.17.0` → set both `plugin.json` and `marketplace.json` taskmaster version to the same value. Add a CHANGELOG section describing the additive surface (the `bundle` field, bundle-aware pick, per-member review/descope, merge fan-out, viewer badge).

- [ ] **Step 2: Version check**

Run (repo root): `python scripts/check_plugin_version_bump.py --base origin/master`
Expected: exit 0.

- [ ] **Step 3: Final full-suite verification**

Run (from `plugins/taskmaster/`): `python -m pytest tests/ -q` → PASS.
Run (from `viewer/`): `npm run test:unit` → PASS.

- [ ] **Step 4: Commit**

```bash
git add plugins/taskmaster/.claude-plugin/plugin.json .claude-plugin/marketplace.json plugins/taskmaster/CHANGELOG.md
git commit -m "chore(taskmaster): bump version for task bundles (task-bundle-001)"
```

- [ ] **Step 5: Run review-gate**

`taskmaster:review-gate task-bundle-001` (standard lane: design-review already passed; review-gate is the post-impl gate).

---

## Self-Review (against spec)

**Spec coverage:** Data model (slug, SLIM_FIELDS, ALLOWED_FIELDS, add_task param, slug format, birth-time sub_repo) → Tasks 1-2. Resolutions C1 `_session_bundle` → Task 3; C2 merge fan-out → Task 8; C3 find helper → Task 2; I1 descope → Task 7 (legal `in-progress→todo` confirmed); I2 lane=strictest-computed → Task 3; I3 drop batch_preview claim → no task needed (spec corrected); I4 structured blast-radius → Task 4; I5 end-session timing/records → Task 8; I6 bundle-aware lock → Task 3. Viewer badge → Task 5. Skills (pick/review/end) → Tasks 6-8. Versioning → Task 9.

**Placeholder scan:** none — each step names exact file + symbol + test code or command.

**Type/name consistency:** `_find_tasks_by_bundle`, `_session_bundle`/`_get_session_bundle`/`_set_session_bundle`, `_strictest_lane`, `_valid_bundle_slug`, `_bundle_sub_repo_conflict`, `backlog_blast_radius(..., structured=True)` used consistently across Tasks 1-9.

**Known soft spots to verify during impl (flagged, not placeholders):** (a) the exact `renderCard` export signature in `card.js` (Task 5 Step 1 note); (b) whether `_build_worktree_instruction` re-derives paths from its first arg vs. uses the passed `branch`/`worktree` (Task 3 Step 4 note); (c) whether tasks are flat `data["tasks"]` or nested under epics — match `_find_task`'s traversal (Task 2 Step 3 note).
