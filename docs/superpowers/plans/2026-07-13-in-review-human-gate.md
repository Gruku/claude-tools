# in-review Human-Gate (tm 4.5.0) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `done` the default terminal status (Claude complete + gates passed) and turn `in-review` into an exception state meaning "blocked on a human-only action", recorded in a new `human_action` light field.

**Architecture:** Enforcement lives in the MCP server (`taskmaster/backlog_server.py`): every path that can set `in-review` requires `human_action`; every path that sets `done` clears it. Storage is free — non-heavy fields pass through to `backlog.yaml` automatically. Semantics prose lives only in `playbooks/` (skills/adapters are thin pointers); the viewer relabels one column and renders the field on cards.

**Tech Stack:** Python (FastMCP server, pytest), vanilla JS viewer (node:test + jsdom units), markdown playbooks.

**Spec:** `docs/superpowers/specs/2026-07-13-in-review-human-gate-design.md` (claude-tools repo).

## Global Constraints

- **Working repo:** `C:\Users\gruku\Files\Claude\taskmaster` (source of truth). Tasks 1–9 run there; Task 10 runs in `C:\Users\gruku\Files\Claude\claude-tools`.
- **Branch:** create `human-gate-4.5.0` off `master` in the taskmaster repo before Task 1 (`git checkout -b human-gate-4.5.0`). Never push; never merge to shared branches — local merge to master happens in Task 9 and stays local.
- **Target version:** `4.5.0` exactly, in `pyproject.toml`, `.claude-plugin/plugin.json` (taskmaster repo), and `.claude-plugin/marketplace.json` (claude-tools repo).
- **Status value string stays `in-review`** everywhere (keys, CSS classes, filters, Linear mapping). Only human-facing *labels* and *prose* change.
- **Field name:** `human_action` — short imperative string, light field (must NOT be added to `HEAVY_FIELDS`).
- **Error messages that reject in-review must contain the substring `human_action`** (tests assert on it).
- **Python tests:** `uv run pytest <file> -v` from the taskmaster repo root (plain `pytest` if uv is unavailable). **Viewer unit tests:** `npm run test:unit` from `viewer/` (runs `node --test "tests/unit/*.test.js"`). Do not use the live-data `.spec.js` e2e suite as a gate.
- **Viewer design rules:** no colored left rails, no box-shadows, no hover motion.
- **Commit per task** with explicit pathspecs (never `git add -A`); stash stray edits first.
- Editing `skills/*/SKILL.md` frontmatter (Task 6) requires invoking `plugin-dev:skill-development` first (project rule).

---

### Task 1: `human_action` storage + read surfaces

**Files:**
- Modify: `taskmaster/backlog_server.py` (`ALLOWED_FIELDS` ~line 4860; `backlog_list_tasks` ~lines 1177–1191; `backlog_get_task` verbose fields ~lines 1276–1294)
- Modify: `taskmaster/taskmaster_v3.py` (`SLIM_FIELDS["task"]` ~lines 116–126)
- Create: `tests/test_human_action.py`

**Interfaces:**
- Produces: task dict key `human_action` (plain string), settable via `backlog_update_task(task_id, "human_action", "<text>")`, visible in `backlog_get_task` (slim + verbose) and `backlog_list_tasks`.
- Storage note: fields not in `HEAVY_FIELDS` automatically stay in `backlog.yaml` (`_split_task_for_v3`) — no serialization change needed.

- [ ] **Step 1: Write failing tests**

Create `tests/test_human_action.py`:

```python
# tests/test_human_action.py
"""tm 4.5.0 human-gate: human_action field + in-review enforcement."""
import re
from taskmaster import backlog_server as _bs


def _t(lane="express"):
    tid = re.search(r"[a-z0-9-]+-\d{3}",
                    _bs.backlog_add_task("s", epic="test-epic", phase="dev", priority="medium")).group(0)
    _bs.backlog_update_task(tid, "lane", lane)
    return tid


def test_human_action_field_updatable_and_persisted(tm_epic_phase):
    tid = _t()
    out = _bs.backlog_update_task(tid, "human_action", "add OPENAI_API_KEY to .env")
    assert "Error" not in out
    task, _ = _bs._find_task(_bs._load(), tid)
    assert task["human_action"] == "add OPENAI_API_KEY to .env"


def test_human_action_visible_in_get_task(tm_epic_phase):
    tid = _t()
    _bs.backlog_update_task(tid, "human_action", "rotate the deploy token")
    out = _bs.backlog_get_task(tid)
    assert "rotate the deploy token" in out


def test_human_action_visible_in_list_tasks(tm_epic_phase):
    tid = _t()
    _bs.backlog_update_task(tid, "human_action", "install the CUDA driver")
    out = _bs.backlog_list_tasks()
    assert "install the CUDA driver" in out
```

(`_t()` and the `tm_epic_phase` fixture mirror `tests/test_status_transitions.py:7-11` — same epic/phase names.)

- [ ] **Step 2: Run tests, verify they fail**

Run: `uv run pytest tests/test_human_action.py -v`
Expected: 3 FAIL — first on `field `human_action` not allowed`, the read ones on missing output.

- [ ] **Step 3: Implement**

1. `taskmaster/backlog_server.py` ~line 4860 — add `"human_action"` to `ALLOWED_FIELDS`. The generic `else: task[field] = value` passthrough in `backlog_update_task` handles the write; no new elif branch.
2. `taskmaster/taskmaster_v3.py` `SLIM_FIELDS["task"]` — add `"human_action"` after `"blockers"`:
```python
        "blockers", "human_action", "open_handovers",
```
3. `backlog_get_task` verbose mode (~lines 1276–1294) — add to the `fields` list of `(label, value)` tuples, after the Blockers entry, matching surrounding style:
```python
        ("Waiting on human", task.get("human_action", "")),
```
4. `backlog_list_tasks` — immediately after the existing `tldr` append (~lines 1188–1191), mirroring its style/indentation:
```python
        if t.get("human_action"):
            entry += f"\n    waiting-on-human: {t['human_action']}"
```
Match the actual indentation and line-building idiom of the tldr block you see there (both slim and verbose paths if the tldr append exists in both).

- [ ] **Step 4: Run tests, verify they pass**

Run: `uv run pytest tests/test_human_action.py -v` → 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_human_action.py taskmaster/backlog_server.py taskmaster/taskmaster_v3.py
git commit -m "feat: human_action light field — storage + read surfaces"
```

---

### Task 2: `backlog_complete_task` human-gate enforcement

**Files:**
- Modify: `taskmaster/backlog_server.py:4476-4556` (`backlog_complete_task`)
- Test: `tests/test_human_action.py`

**Interfaces:**
- Consumes: `human_action` field from Task 1.
- Produces: new keyword param `human_action: str = ""` on `backlog_complete_task`. Behavior: `target_status="in-review"` errors (message contains `human_action`) unless the param is non-empty or the task already carries the field; `target_status="done"` pops `human_action`. The old "skipping the in-review stage" nag is deleted.

- [ ] **Step 1: Write failing tests** (append to `tests/test_human_action.py`)

```python
def test_complete_to_in_review_requires_human_action(tm_epic_phase):
    tid = _t()
    _bs.backlog_update_task(tid, "status", "in-progress")
    out = _bs.backlog_complete_task(tid, target_status="in-review")
    assert "Error" in out and "human_action" in out
    task, _ = _bs._find_task(_bs._load(), tid)
    assert task["status"] == "in-progress"


def test_complete_to_in_review_with_human_action(tm_epic_phase):
    tid = _t()
    _bs.backlog_update_task(tid, "status", "in-progress")
    out = _bs.backlog_complete_task(tid, target_status="in-review",
                                    human_action="add OPENAI_API_KEY to .env")
    assert "Error" not in out
    task, _ = _bs._find_task(_bs._load(), tid)
    assert task["status"] == "in-review"
    assert task["human_action"] == "add OPENAI_API_KEY to .env"


def test_complete_to_in_review_accepts_preexisting_human_action(tm_epic_phase):
    tid = _t()
    _bs.backlog_update_task(tid, "status", "in-progress")
    _bs.backlog_update_task(tid, "human_action", "grant repo access")
    assert "Error" not in _bs.backlog_complete_task(tid, target_status="in-review")


def test_complete_to_done_clears_human_action(tm_epic_phase):
    tid = _t()
    _bs.backlog_update_task(tid, "status", "in-progress")
    _bs.backlog_record_gate(tid, "impl", status="done")
    _bs.backlog_record_gate(tid, "review-gate", verdict="pass")
    _bs.backlog_complete_task(tid, target_status="in-review", human_action="add key")
    out = _bs.backlog_complete_task(tid, target_status="done")
    assert "Error" not in out
    task, _ = _bs._find_task(_bs._load(), tid)
    assert task["status"] == "done"
    assert "human_action" not in task


def test_no_skip_review_nag_on_direct_done(tm_epic_phase):
    tid = _t()
    _bs.backlog_update_task(tid, "status", "in-progress")
    _bs.backlog_record_gate(tid, "impl", status="done")
    _bs.backlog_record_gate(tid, "review-gate", verdict="pass")
    out = _bs.backlog_complete_task(tid)
    assert "skipping the in-review stage" not in out
```

- [ ] **Step 2: Run, verify the new 5 fail**

Run: `uv run pytest tests/test_human_action.py -v`
Expected: Task 1's 3 pass; these 5 FAIL (first two on `unexpected keyword argument 'human_action'`).

- [ ] **Step 3: Implement**

In `backlog_complete_task`:

1. Signature — add after `target_status`:
```python
    target_status: str = "done",
    human_action: str = "",
```
2. Immediately after the current-status check (`if status not in ("in-progress", "in-review", "blocked"): ...`, ~line 4523), insert:
```python
    if target_status == "in-review":
        human_action = human_action.strip() or task.get("human_action", "")
        if not human_action:
            return ("Error: target_status='in-review' requires human_action — the human-only "
                    "step that blocks this task (e.g. 'add OPENAI_API_KEY to .env'). "
                    "If nothing blocks it, target 'done'.")
```
3. Delete the review-warning block (~lines 4548–4551, `review_warning = ""` through the `review_warning = "\n\n**Note:** Task went directly from in-progress → done..."` assignment) AND the `{review_warning}` interpolation later in the function's return string (grep `review_warning` within the function — remove every occurrence).
4. Replace the status-assignment block (~lines 4553–4555):
```python
    task["status"] = target_status
    if target_status == "done":
        task["completed"] = _now()
        task.pop("human_action", None)
    else:  # in-review — allowlist above guarantees it
        task["human_action"] = human_action
```
5. Docstring — replace the third paragraph (`Use target_status="in-review" when implementation is complete but the user needs to manually test...`) with:
```
    Use target_status="done" (default) when Claude's work is complete and gates passed.
    Use target_status="in-review" ONLY when an action that only the human can perform
    blocks the task (API key, LLM config, account access) — pass it as human_action.
```
and update the Args entries:
```
        target_status: Target status — "done" (default) or "in-review" (blocked on a human-only action)
        human_action: Required with target_status="in-review" (unless already set on the task): short imperative describing the human-only blocker, e.g. "add OPENAI_API_KEY to .env". Cleared automatically when the task reaches done.
```

- [ ] **Step 4: Run tests** → all 8 pass.

- [ ] **Step 5: Commit**

```bash
git add tests/test_human_action.py taskmaster/backlog_server.py
git commit -m "feat: complete_task requires human_action for in-review, clears it on done"
```

---

### Task 3: `backlog_update_task` + `backlog_batch_update` enforcement

**Files:**
- Modify: `taskmaster/backlog_server.py` (`backlog_update_task` status branch ~lines 4930–4970; `backlog_batch_update` `op == "status"` ~line 6236 and `op == "complete"` ~line 6274)
- Modify: `tests/test_status_transitions.py:37-47` (two existing tests assume free entry to in-review)
- Test: `tests/test_human_action.py`

**Interfaces:**
- Consumes: `human_action` field from Task 1.
- Produces: `update_task`/`batch_update` reject `status → in-review` when the task has no `human_action` (message contains `human_action`; the single-field API means it must be set in a prior call); both clear `human_action` on `→ done`. Applies to ALL tasks, lane'd or not (the lane exemption covers only the transition table, not this rule).

- [ ] **Step 1: Write failing tests** (append to `tests/test_human_action.py`)

Before writing the two batch tests, read `backlog_batch_update`'s docstring/signature in `backlog_server.py` (~line 6100s) to confirm the ops format — it parses lines into `parts` as `op task_id value...`; adjust the call strings below to the actual parameter name and separator if they differ.

```python
def test_update_status_in_review_requires_human_action(tm_epic_phase):
    tid = _t()
    _bs.backlog_update_task(tid, "status", "in-progress")
    out = _bs.backlog_update_task(tid, "status", "in-review")
    assert "Error" in out and "human_action" in out
    task, _ = _bs._find_task(_bs._load(), tid)
    assert task["status"] == "in-progress"


def test_update_status_in_review_ok_when_field_set(tm_epic_phase):
    tid = _t()
    _bs.backlog_update_task(tid, "status", "in-progress")
    _bs.backlog_update_task(tid, "human_action", "add API key")
    assert "Error" not in _bs.backlog_update_task(tid, "status", "in-review")


def test_update_status_done_clears_human_action(tm_epic_phase):
    tid = _t()
    _bs.backlog_update_task(tid, "status", "in-progress")
    _bs.backlog_update_task(tid, "human_action", "add API key")
    _bs.backlog_record_gate(tid, "impl", status="done")
    _bs.backlog_record_gate(tid, "review-gate", verdict="pass")
    assert "Error" not in _bs.backlog_update_task(tid, "status", "done")
    task, _ = _bs._find_task(_bs._load(), tid)
    assert "human_action" not in task


def test_batch_status_in_review_requires_human_action(tm_epic_phase):
    tid = _t()
    _bs.backlog_update_task(tid, "status", "in-progress")
    out = _bs.backlog_batch_update(f"status {tid} in-review")
    assert "human_action" in out
    task, _ = _bs._find_task(_bs._load(), tid)
    assert task["status"] == "in-progress"


def test_batch_complete_clears_human_action(tm_epic_phase):
    tid = _t()
    _bs.backlog_update_task(tid, "status", "in-progress")
    _bs.backlog_update_task(tid, "human_action", "add API key")
    _bs.backlog_record_gate(tid, "impl", status="done")
    _bs.backlog_record_gate(tid, "review-gate", verdict="pass")
    _bs.backlog_batch_update(f"complete {tid}")
    task, _ = _bs._find_task(_bs._load(), tid)
    assert task["status"] == "done"
    assert "human_action" not in task
```

- [ ] **Step 2: Run, verify the new 5 fail** — `uv run pytest tests/test_human_action.py -v`

- [ ] **Step 3: Implement**

1. `backlog_update_task`, inside the `if field == "status":` branch, right after `cur = task.get("status", "todo")` (BEFORE the lane-only transition-table block, so it applies to laneless tasks too):
```python
        if value == "in-review" and value != cur and not task.get("human_action"):
            return (f"Error: `in-review` means blocked on a human-only action; set human_action first: "
                    f"backlog_update_task('{task_id}', 'human_action', '<what the human must do>')")
```
2. Same branch, immediately before `task["status"] = value` (after all validations):
```python
        if value == "done":
            task.pop("human_action", None)
```
3. `backlog_batch_update` `op == "status"` (~line 6236): after the `_find_task` resolution (`task, epic = result`, ~line 6245), insert:
```python
            if new_status == "in-review" and task.get("status") != "in-review" and not task.get("human_action"):
                errors.append(f"`{task_id}`: in-review requires human_action — set it first via backlog_update_task")
                continue
```
and inside the existing `elif new_status == "done":` timestamp block (~lines 6265–6268), add `task.pop("human_action", None)`.
4. `backlog_batch_update` `op == "complete"` (~line 6299): next to `task.pop("locked_by", None)` add `task.pop("human_action", None)`.

- [ ] **Step 4: Fix the two existing tests that now (correctly) fail**

In `tests/test_status_transitions.py`, `test_backward_jump_rejected` (line 37) and `test_in_review_allowed_with_outstanding_gates` (line 44) enter in-review freely. Insert before each in-review transition:
```python
    _bs.backlog_update_task(tid, "human_action", "test blocker")
```

- [ ] **Step 5: Run the FULL suite**

Run: `uv run pytest`
Expected: green. Any other failure caused by a test entering in-review without `human_action` gets the same one-line fixture fix (add the `human_action` update before the transition) — never weaken the rule. If a *non-test* code path (e.g. Linear inbound sync) programmatically writes `status = "in-review"`, leave it untouched and note it in the commit message — out of scope.

- [ ] **Step 6: Commit**

```bash
git add tests/test_human_action.py tests/test_status_transitions.py taskmaster/backlog_server.py
git commit -m "feat: update_task + batch_update enforce human_action gate on in-review"
```

---

### Task 4: Viewer — "Waiting on human" column + human_action on cards

**Files:**
- Modify: `viewer/js/lib/filters.js:129-135` (`STATUS_LABELS`)
- Modify: `viewer/js/components/card.js:20` (pill labels) and ~lines 219–225 (insertion point next to the blocked callout)
- Modify: `viewer/css/screens/kanban.css` (new `.card-human-action` rule near `.card-callout`, ~line 298)
- Test: `viewer/tests/unit/card-human-action.test.js` (create)

**Interfaces:**
- Consumes: `task.human_action` — arrives automatically: `/api/backlog` serves `backlog.yaml` task dicts unfiltered (`_serve_json`, `backlog_server.py:7201`), and `human_action` is a slim field. Zero server changes.
- Produces: `.card-human-action` element on full-density in-review cards. Table screen, task-form dropdown, relation-picker badges intentionally unchanged (spec: no other screens change).

- [ ] **Step 1: Write failing unit test**

Create `viewer/tests/unit/card-human-action.test.js` (mirrors `card-bundle.test.js`):

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { JSDOM } from 'jsdom';
const { window } = new JSDOM('<!DOCTYPE html><body></body>');
globalThis.document = window.document;

import { renderCard } from '../../js/components/card.js';
import { STATUS_LABELS } from '../../js/lib/filters.js';

test('in-review card renders its human_action', () => {
  const el = renderCard({ task: { id: 't-1', title: 'X', status: 'in-review', human_action: 'add API key to .env' } });
  assert.match(el.outerHTML, /card-human-action/);
  assert.match(el.outerHTML, /add API key to \.env/);
});

test('in-review card without human_action renders no line', () => {
  const el = renderCard({ task: { id: 't-2', title: 'Y', status: 'in-review' } });
  assert.doesNotMatch(el.outerHTML, /card-human-action/);
});

test('non-in-review card ignores a stale human_action', () => {
  const el = renderCard({ task: { id: 't-3', title: 'Z', status: 'done', human_action: 'leftover' } });
  assert.doesNotMatch(el.outerHTML, /card-human-action/);
});

test('in-review status label reads Waiting on human', () => {
  assert.equal(STATUS_LABELS['in-review'], 'Waiting on human');
});
```

- [ ] **Step 2: Run, verify 4 fail** — from `viewer/`: `npm run test:unit` (new file's tests FAIL, existing suites stay green).

- [ ] **Step 3: Implement**

1. `filters.js:133` — `'in-review': 'Waiting on human',`
2. `card.js:20` — in the local `STATUS_LABELS` (status pill), same change: `'in-review': 'Waiting on human'`.
3. `card.js` — in the full-density section, directly ABOVE the blocked-callout block (~line 219; minimal density has already returned at ~line 96, which is intended):
```js
  // ── Human action: in-review cards show what the human must do ──
  if (task.status === 'in-review' && task.human_action) {
    const ha = document.createElement('div');
    ha.className = 'card-human-action';
    ha.textContent = task.human_action;
    body.appendChild(ha);
  }
```
4. `kanban.css`, next to the `.card-callout` rules (~line 298):
```css
.card-human-action {
  margin-top: var(--sp-2);
  font-size: var(--text-xs);
  color: var(--amber);
}
```
(Amber matches the existing in-review dot color. Full-perimeter/no-rail rules: this is plain text, no border.)

- [ ] **Step 4: Run tests** — `npm run test:unit` → all green.

- [ ] **Step 5: Commit**

```bash
git add viewer/js/lib/filters.js viewer/js/components/card.js viewer/css/screens/kanban.css viewer/tests/unit/card-human-action.test.js
git commit -m "feat(viewer): Waiting on human column label + human_action line on in-review cards"
```

---

### Task 5: end-session playbook — done becomes the default

**Files:**
- Modify: `playbooks/end-session/playbook.md` (lines 37, 63, 81)
- Modify: `playbooks/end-session/references/summary-modes.md` (lines 28–37)

**Interfaces:** prose only; must reference `human_action` exactly as implemented in Tasks 1–2.

- [ ] **Step 1: Edit `playbook.md`**

Line 37, replace the whole line with:
```
**4. Target status.** Default `done` — Claude complete + gates passed. Target `in-review` ONLY when an action that only the human can perform blocks the task (API key, LLM config, account access); pass it as `human_action` (short imperative, e.g. "add OPENAI_API_KEY to .env") — `backlog_complete_task` rejects in-review without it. See `references/summary-modes.md`.
```

Line 63, extend the listed signature to include the new param:
```
- **Single task (default):** `backlog_complete_task(task_id, session_title, done, decisions, issues, tasks_touched, target_status, patchnote, release, human_action)`.
```

Line 81, replace with:
```
`todo -> in-progress -> in-review -> done -> archived`. In-review = blocked on a human-only action (`human_action` says what). Done = Claude complete + gates passed. Human review of shipped work happens downstream, not on the board.
```

Lines 7 and 70 stay as-is (still true).

- [ ] **Step 2: Replace the Step 4 section of `summary-modes.md`** (lines 28–37) with:

```
## Step 4: Target Status Decision Rules

**Default:** silently target `done` — Claude finished and the lane's gates passed. Nothing to ask.

**Target `in-review` ONLY when a human-only action blocks the task** — something Claude cannot do itself: add an API key, set LLM config, grant account access, a physical-world step. Pass it as `human_action` (short imperative: "add OPENAI_API_KEY to .env"). `backlog_complete_task` rejects in-review without it.

Do not target in-review for "the user should look at this" — done work gets reviewed downstream, off the board. Do not ask "is this done?" — the default already handles it; the user can reopen with a one-liner if something's wrong.
```

- [ ] **Step 3: Verify** — `grep -n "user tests\|user confirmed\|Default \`in-review\`" playbooks/end-session/ -r` returns nothing.

- [ ] **Step 4: Commit**

```bash
git add playbooks/end-session/playbook.md playbooks/end-session/references/summary-modes.md
git commit -m "docs(playbooks): end-session defaults to done; in-review requires human_action"
```

---

### Task 6: review-gate — record only, no status transition

**Files:**
- Modify: `playbooks/review-gate/playbook.md:25`
- Modify: `playbooks/review-gate/references/gate-details.md:64`
- Modify: `playbooks/review-gate/references/bundle-gate.md:57,120`
- Modify: `skills/review-gate/SKILL.md:3` (frontmatter description)
- Modify: `commands/review-gate.md:2` (frontmatter description)

**Interfaces:** review-gate now records the gate and leaves status `in-progress`; end-session's `backlog_complete_task` performs the close to `done` (legal transition `in-progress → done`; complete_task accepts from in-progress).

- [ ] **Step 0: Invoke `plugin-dev:skill-development`** before touching SKILL.md frontmatter (project rule; the description field is the trigger surface).

- [ ] **Step 1: Edit the five passages**

`playbook.md` line 25 (steps-table row 9) → :
```
| 9 | Record the gate — the task stays `in-progress`; end-session closes it to `done` |
```

`gate-details.md` line 64 → :
```
If gates failed, offer: "Stay in-progress and address issues" or "Record a pass anyway (you'll need to justify the critical findings) — end-session will close it to done."
```

`bundle-gate.md` line 57 → :
```
- Record each member's gate. Members stay `in-progress`; end-session closes them to `done`.
```

`bundle-gate.md` line 120: in the partial-fix-up sentence, replace "record its gate and transition it to `in-review`" with "record its gate (it stays `in-progress` until end-session closes it)".

`skills/review-gate/SKILL.md` line 3, replace the description with:
```
description: "Run quality checks on a task's implementation before it closes to done. Triggers: 'is this ready?', 'run the review gate', 'check my work', 'I think this is done'. Reviews code + spec adherence, runs tests/build. Design review uses taskmaster:spec-review."
```

`commands/review-gate.md` line 2 → :
```
description: Run quality checks on a task before it closes to done
```

- [ ] **Step 2: Verify** — `grep -rn "in-review" playbooks/review-gate/ commands/review-gate.md skills/review-gate/` shows no remaining transition-to-in-review instructions (mentions of the state in explanatory prose are fine only if consistent with new semantics).

- [ ] **Step 3: Commit**

```bash
git add playbooks/review-gate/ skills/review-gate/SKILL.md commands/review-gate.md
git commit -m "docs(playbooks): review-gate records only — no in-review transition"
```

---

### Task 7: start-session — "Waiting on you" + legacy sweep

**Files:**
- Modify: `playbooks/start-session/playbook.md` (line 51 bullet; new Step 3e after line 43)

**Interfaces:** consumes `backlog_list_tasks` human_action display (Task 1), `backlog_complete_task` (Task 2), `backlog_batch_update` op `complete` (Task 3), `backlog_update_task` human_action writes.

- [ ] **Step 1: Replace the briefing bullet** (line 51 `- **Needs testing:** in-review tasks`) with:

```
- **Waiting on you:** in-review tasks, each with its `human_action`. If the user says one is handled — or you can verify it directly (e.g. the env var now exists) — close it with `backlog_complete_task(id, target_status="done", ...)`; that clears the human_action and logs the session record.
```

- [ ] **Step 2: Add Step 3e** after the Step 3d block (after line 43), mirroring 3d's quiet-conditional pattern:

```
### Step 3e — Legacy in-review sweep (only if in-review tasks lack `human_action`)

If any in-review task has no `human_action`, it predates the human-gate semantics (pre-4.5.0: in-review meant "user tests"). Once per project: present them as one table (id, title) and offer to bulk-close all to `done` via `backlog_batch_update` (op `complete`) — unless the user flags one as genuinely blocked, in which case write its blocker instead: `backlog_update_task(id, "human_action", "...")`. Apply on approval, one message. If a close is rejected by outstanding gates, report it and leave that task as-is. Self-extinguishing: once every in-review task carries a human_action, this step never fires again.
```

- [ ] **Step 3: Verify** — `grep -n "Needs testing" playbooks/start-session/playbook.md` returns nothing.

- [ ] **Step 4: Commit**

```bash
git add playbooks/start-session/playbook.md
git commit -m "docs(playbooks): start-session Waiting-on-you list + legacy in-review sweep"
```

---

### Task 8: Remaining semantics prose — pick-task, task-lifecycle, TASKMASTER.md

**Files:**
- Modify: `playbooks/pick-task/playbook.md` (lifecycle blurb ~lines 87–93, note line 101)
- Modify: `references/task-lifecycle.md` (rows 18–19, section lines 24–27, transitions table lines 33/36/37)
- Modify: `docs/TASKMASTER.md` (table lines 116–123, paragraph line 125)

- [ ] **Step 1: `pick-task/playbook.md`**

In the Task lifecycle section, replace `` `in-review` = Claude done, user tests.`` with:
```
`in-review` = blocked on a human-only action (the task's `human_action` says what).
```
Line 101, replace the sentence `Picking `in-review` demotes to `in-progress` — confirm first.` with:
```
Picking `in-review` demotes to `in-progress` (resume after the human action is handled) — confirm first.
```

- [ ] **Step 2: `references/task-lifecycle.md`**

Status table — replace the in-review and done rows (lines 18–19) with:
```
| **in-review** | The user | Exception state: AI work complete, but an action only the human can perform blocks it. The task's `human_action` states it. Entering in-review without one is rejected. |
| **done** | Nobody | Claude complete + required gates passed. Session summary logged to PROGRESS.md. |
```

Replace the "Why In-Review Exists" section (lines 24–27) with:
```
## Why In-Review Exists

`in-review` is an **exception state**, not a pipeline stage. It means the AI work is complete but an action only the human can perform blocks true completion — adding an API key, changing LLM config, granting access. The blocking action is recorded on the task as `human_action`; every write path rejects in-review without it.

Most tasks never touch in-review: they go `in-progress → done` once the lane's gates pass. Human review of done work happens downstream (review sweeps), not on the board.
```

Transitions table — update the three rows (lines 33, 36, 37) to:
```
| in-progress | done | `end-session` skill | Gates passed; session summary logged |
| in-progress | in-review | `end-session` skill | A human-only action blocks the task; `human_action` recorded |
| in-review | done | `start-session` / `end-session` | Human action handled (verified or user-confirmed); `human_action` cleared |
| in-review | in-progress | `pick-task` skill | Resume work after the human action is handled |
```
(Also update the header diagram at lines 6–10: the `(review-gate)` annotation under in-review becomes `(end-session, when human-blocked)`, and `(archive after user confirms)` becomes `(archive)`.)

- [ ] **Step 3: `docs/TASKMASTER.md`**

Table rows for in-review/done (lines 120–121) → :
```
| `in-review` | Exception state: blocked on an action only the human can do; recorded in `human_action`. Rare. |
| `done` | Claude complete + required gates passed. Session summary logged. |
```

Paragraph at line 125 (`**`in-review` is mandatory.** ...`) → :
```
**`in-review` is exceptional.** Most tasks go straight from `in-progress` to `done` once their gates pass. in-review is reserved for tasks blocked on an action only the human can perform — an API key, external config, account access — recorded on the task as `human_action`. start-session surfaces these as a "Waiting on you" list.
```
Update the diagram at lines 111–114 accordingly (drop the implication that review-gate feeds in-review).

- [ ] **Step 4: Repo-wide semantics sweep**

`grep -rn "user tests\|user confirmed\|ready for user testing\|user must manually test" --include="*.md" .` — every remaining hit tied to task-status semantics gets the new wording (hits in `docs/plans/`, `docs/specs/` history files and bug/issue-triage contexts are historical/unrelated — leave those).

- [ ] **Step 5: Commit**

```bash
git add playbooks/pick-task/playbook.md references/task-lifecycle.md docs/TASKMASTER.md
git commit -m "docs: in-review = human-blocked exception state across lifecycle docs"
```

---

### Task 9: Version 4.5.0, changelog, full verification, local merge

**Files:**
- Modify: `pyproject.toml:7` (`version = "4.5.0"`)
- Modify: `.claude-plugin/plugin.json` (`"version": "4.5.0"`)
- Modify: `CHANGELOG.md` (new top entry)

- [ ] **Step 1: Bump both version fields to `4.5.0`.**

- [ ] **Step 2: Add CHANGELOG entry** above the `## 4.4.1` header:

```markdown
## 4.5.0

**in-review becomes a human-blocked exception state.** `done` is now the default terminal status (Claude complete + gates passed); `in-review` is reserved for tasks blocked on an action only a human can perform, recorded in the new `human_action` light field. Every write path that reaches in-review (`backlog_complete_task`, `backlog_update_task`, `backlog_batch_update`) rejects the transition without a `human_action`; reaching `done` clears it. Review-gate no longer transitions status — it records the gate and end-session closes the task. start-session gains a "Waiting on you" list plus a one-time sweep offering to bulk-close pre-4.5.0 in-review tasks. Viewer: kanban column relabeled "Waiting on human"; in-review cards show their `human_action`.
```

- [ ] **Step 3: Full verification**

Run: `uv run pytest` (repo root) → green.
Run: `npm run test:unit` (from `viewer/`) → green.

- [ ] **Step 4: Commit, then merge to local master**

```bash
git add pyproject.toml .claude-plugin/plugin.json CHANGELOG.md
git commit -m "chore: bump to 4.5.0 — human-gate release"
git checkout master
git merge --no-ff human-gate-4.5.0 -m "merge: human-gate 4.5.0 — in-review as human-blocked exception state"
```
Do NOT push (gated — user decides).

---

### Task 10: claude-tools — submodule bump + marketplace version

**Files (claude-tools repo, `C:\Users\gruku\Files\Claude\claude-tools`):**
- Modify: `plugins/taskmaster` (submodule pointer → the Task 9 merge commit on taskmaster master)
- Modify: `.claude-plugin/marketplace.json` (taskmaster entry `version` → `4.5.0`)

- [ ] **Step 1: Check the submodule's current state first** — `git -C plugins/taskmaster status` and `git submodule status plugins/taskmaster`. The tree showed a modified submodule pointer before this work started; if it points at something other than the old master, surface that to the user before proceeding — do not sweep unrelated state into this commit.

- [ ] **Step 2: Advance the pointer**

```bash
git -C plugins/taskmaster fetch origin   # no-op locally; then:
git -C plugins/taskmaster checkout master
```
(master now contains the Task 9 merge; the outer repo sees a new pointer.)

- [ ] **Step 3: Update `.claude-plugin/marketplace.json`** — taskmaster `version` → `"4.5.0"` (must equal the submodule's plugin.json).

- [ ] **Step 4: Verify the three-part protocol**

Run: `python scripts/check_plugin_version_bump.py --base origin/master`
Expected: exit 0. (CHANGELOG lives inside the submodule and was bumped in Task 9.)

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster .claude-plugin/marketplace.json
git commit -m "feat: taskmaster 4.5.0 — in-review human-gate (submodule + marketplace bump)"
```
Do NOT push. Note for the user: the MCP server must be restarted to pick up 4.5.0 (known gotcha), and pushing taskmaster + claude-tools to origin stays gated on their say-so.
