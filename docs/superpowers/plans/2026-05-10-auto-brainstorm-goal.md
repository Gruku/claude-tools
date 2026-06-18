> ⚠ **Superseded (2026-06-11).** This design builds on taskmaster's auto-mode state machine,
> which has been removed (see docs/superpowers/specs/2026-06-11-remove-auto-mode-design.md).
> Autonomous execution now routes through goals + ultracode. The substrate assumed below no
> longer exists; treat this as historical until redesigned.

# Auto-Brainstorm + /goal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `taskmaster:auto-brainstorm` (opinionated unsupervised spec authoring), `/goal` (autonomous-from-zero entry point), and `taskmaster:goal-judge` (the plugin's first dedicated subagent — an LLM-judged completion gate) as one integrated feature.

**Architecture:** Reuse the existing Epic surface with a new `kind: goal` discriminator (no new on-disk entity). Auto-brainstorm runs as an in-context skill invoked from `auto-task` Step 2, dispatching parallel `Explore` subagents for research. `goal-judge` runs as an isolated read-only subagent at a new `GOAL_JUDGE` stage between `END_SESSION` and finish, classifying gaps as small (in-task loop) or structural (spawn follow-up child task). All three artifacts share a single rubric reference doc.

**Tech Stack:** Python 3.11+, FastMCP, PyYAML, pytest. Skills are markdown-with-frontmatter under `plugins/taskmaster/skills/`. Agents are markdown-with-frontmatter under `plugins/taskmaster/agents/` (new directory).

**Source spec:** `docs/superpowers/specs/2026-05-10-auto-brainstorm-goal-design.md`

---

## File structure (locked before tasks)

| Path | Responsibility |
|---|---|
| `plugins/taskmaster/skills/goal/references/rubric.md` | Single source of truth for the 5-point /goal rubric (concrete outcome, bounded scope, testable criteria, constraints, tests planned). Loaded by all three sites. |
| `plugins/taskmaster/skills/goal/SKILL.md` | `/goal` slash command and natural-language entry point. Validates rubric, creates kind:goal Epic + first task, fires `auto-task`. |
| `plugins/taskmaster/skills/auto-brainstorm/SKILL.md` | Research → draft → self-iterate → challenger pipeline. Returns finalized spec text written into `tasks/<id>.md` `## Spec` section. |
| `plugins/taskmaster/skills/auto-brainstorm/references/research-prompts.md` | One prompt template per research source (IDEA store, lessons+handovers, web search, cross-domain). |
| `plugins/taskmaster/agents/goal-judge.md` | First plugin subagent. Read-only completion judge with strict "no proxy signals" prompt. Returns structured JSON verdict. |
| `plugins/taskmaster/skills/auto-task/SKILL.md` | **Modified.** Step 2 invokes `auto-brainstorm`. New Step 9 `GOAL_JUDGE` stage for goal-kind epics. |
| `plugins/taskmaster/skills/spec-review/SKILL.md` | **Modified.** Add `unattended_mode` invocation contract — returns findings list, suppresses user-facing prompts. |
| `plugins/taskmaster/skills/taskmaster/SKILL.md` | **Modified.** Routing row for `/goal` intents and "autopilot from zero" phrasings. |
| `plugins/taskmaster/skills/start-session/SKILL.md` | **Modified.** Surface running goals in dashboard. |
| `plugins/taskmaster/backlog_server.py` | **Modified.** Extend `backlog_add_epic` (kind, goal block), `backlog_update_epic` (judge_history append), `backlog_auto_status` (goal-aware fields). |
| `plugins/taskmaster/viewer/js/screens/kanban.js` | **Modified.** Render goal-kind epics with rubric chip, iteration counter, gap pill on judge-rejected children. |
| `plugins/taskmaster/tests/test_epic_kind_goal.py` | New — frontmatter round-trip + validators for kind/goal block. |
| `plugins/taskmaster/tests/test_goal_skill.py` | New — rubric validation, epic+task creation. |
| `plugins/taskmaster/tests/test_auto_brainstorm.py` | New — pipeline integration with mocked research subagents. |
| `plugins/taskmaster/tests/test_goal_judge_agent.py` | New — agent prompt regression suite (fixture-driven). |
| `plugins/taskmaster/tests/test_auto_task_goal_judge_stage.py` | New — state machine routing on judge verdicts. |

---

## Task 1: Rubric reference doc (single source of truth)

**Files:**
- Create: `plugins/taskmaster/skills/goal/references/rubric.md`

This is reference data used by Tasks 2, 5, and 7. Write it first so all three load identical wording.

- [ ] **Step 1: Write the rubric reference doc**

Create `plugins/taskmaster/skills/goal/references/rubric.md`:

```markdown
# /goal Rubric — Single Source of Truth

The five checks every goal must pass. Used at three sites:

1. `/goal` boundary validator — accepts, warns, or rejects user input.
2. `auto-brainstorm` self-iteration — rewrites failing sections of a draft spec.
3. `goal-judge` agent — verifies the implementation actually meets the criteria.

All three sites load this file. Do not duplicate the wording elsewhere.

---

## R1. Concrete outcome

A single nameable thing being built, optimized, ported, or fixed. Phrased as a noun + verb.

- PASS: "build a multi-file particle physics demo", "port triton kernel to CUDA C++", "add bulk-archive button to issues screen"
- WARN: phrasing names the outcome but is missing the artifact ("fix the bug" — which?)
- REJECT: "make my code better", "explore pytorch", "improve performance"

## R2. Bounded scope

Specific files, components, modules, or behaviors named. The judge can tell when work has spilled past the boundary.

- PASS: scope explicitly names paths/components ("modify `viewer/js/screens/issues.js`", "the chip-rail in IssuesScreen", "the `_load_v3` codepath")
- WARN: scope is implied but not named ("the issues screen" — the whole thing? a specific control?)
- REJECT: no scope at all ("the codebase", "wherever needed")

## R3. Testable success criteria

A specific number, output, or observable behavior the model can self-verify.

- PASS: "60fps minimum", "eval reaches 0.85", "all 30 imports updated", "playwright sees the chip rendered"
- WARN: criterion is observable but not quantified ("UI looks correct")
- REJECT: no criterion ("until it works", "until everything is fixed", "looks good")

## R4. Constraints stated

What NOT to change, libraries to use or avoid, file size limits, API stability requirements.

- PASS: "don't break the public MCP API", "use only PyYAML, no new deps", "keep `auto-task` SKILL.md under 250 lines"
- WARN: no constraints stated but the change is small and self-contained — auto-brainstorm fills assumptions explicitly
- REJECT: never; this never blocks /goal, only warns

## R5. Tests planned

What will verify done. Auto-task's TDD default usually covers this; goal text can override.

- PASS: tests are named, even loosely ("write a benchmark for fps", "playwright test for chip render")
- WARN: no test plan but auto-task TDD default applies — proceed, auto-brainstorm authors the test list
- REJECT: never; this never blocks /goal, only warns

---

## Severity at the /goal boundary

| Outcome | Action |
|---|---|
| All five PASS | Proceed silently. |
| Any WARN | Log warning to user, proceed. |
| Any REJECT | One-shot pushback naming missing piece. User supplies it or passes `--accept-vague`. |
| `--accept-vague` | Auto-brainstorm fabricates explicit assumptions; surfaces them in `epic.goal.rubric_eval.assumptions`. |
```

- [ ] **Step 2: Commit the rubric**

```bash
git add plugins/taskmaster/skills/goal/references/rubric.md
git commit -m "docs(taskmaster): /goal rubric reference doc"
```

---

## Task 2: Epic frontmatter — kind discriminator

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py:3733-3768` (`backlog_add_epic`)
- Test: `plugins/taskmaster/tests/test_epic_kind_goal.py`

- [ ] **Step 1: Write the failing test**

Create `plugins/taskmaster/tests/test_epic_kind_goal.py`:

```python
"""Epic kind=goal: frontmatter round-trip and validators."""
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def fresh_backlog(tmp_path, monkeypatch):
    """Initialize an empty .taskmaster/ in a tmp dir, chdir there."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".taskmaster").mkdir()
    (tmp_path / ".taskmaster" / "backlog.yaml").write_text(
        "meta:\n  schema_version: 3\nphases: []\nepics: []\ntasks: []\n",
        encoding="utf-8",
    )
    return tmp_path


def test_add_epic_default_kind_is_feature(fresh_backlog):
    from plugins.taskmaster.backlog_server import backlog_add_epic, _load
    out = backlog_add_epic("demo-feature", "Demo Feature")
    assert "Created epic" in out
    data = _load()
    epic = next(e for e in data["epics"] if e["id"] == "demo-feature")
    assert epic["kind"] == "feature"


def test_add_epic_kind_goal_with_goal_block(fresh_backlog):
    from plugins.taskmaster.backlog_server import backlog_add_epic, _load
    goal_block = {
        "text": "build a confetti VFX demo, 60fps min, served on localhost:5000",
        "rubric_eval": {
            "concrete_outcome": "pass",
            "bounded_scope": "pass",
            "testable_criteria": "pass",
            "constraints_stated": "warn",
            "tests_planned": "pass",
            "accept_vague": False,
        },
        "judge_history": [],
        "iteration_budget": {
            "in_task_loops_used": 0,
            "in_task_loops_max": 3,
            "child_tasks_used": 0,
            "child_tasks_max": 5,
        },
    }
    out = backlog_add_epic(
        "confetti-demo", "Confetti Demo",
        kind="goal", goal=goal_block,
    )
    assert "Created epic" in out
    data = _load()
    epic = next(e for e in data["epics"] if e["id"] == "confetti-demo")
    assert epic["kind"] == "goal"
    assert epic["goal"]["text"].startswith("build a confetti")
    assert epic["goal"]["iteration_budget"]["child_tasks_max"] == 5


def test_add_epic_invalid_kind_rejected(fresh_backlog):
    from plugins.taskmaster.backlog_server import backlog_add_epic
    out = backlog_add_epic("bad", "Bad", kind="random-flavor")
    assert "Error" in out
    assert "kind" in out.lower()


def test_add_epic_kind_goal_requires_goal_block(fresh_backlog):
    from plugins.taskmaster.backlog_server import backlog_add_epic
    out = backlog_add_epic("missing-goal", "Missing", kind="goal")
    assert "Error" in out
    assert "goal block" in out.lower() or "goal=" in out.lower()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd plugins/taskmaster && python -m pytest tests/test_epic_kind_goal.py -v
```

Expected: FAIL with `TypeError: backlog_add_epic() got an unexpected keyword argument 'kind'`

- [ ] **Step 3: Modify `backlog_add_epic` to accept `kind` and `goal`**

In `plugins/taskmaster/backlog_server.py`, replace the `backlog_add_epic` function (currently at line 3733) with:

```python
VALID_EPIC_KINDS = {"feature", "goal"}

def backlog_add_epic(
    epic_id: str, name: str, description: str = "", status: str = "planned",
    kind: str = "feature", goal: dict | None = None,
) -> str:
    """Create a new epic. Epics group related tasks into workstreams.

    Args:
        epic_id: Short kebab-case identifier. Must be unique.
        name: Human-readable name.
        description: Brief description.
        status: One of: active, planned (default planned).
        kind: One of: feature (default), goal. `goal` enables LLM-judged
              completion semantics — required when /goal creates an epic.
        goal: Required when kind=goal. Dict with keys: text, rubric_eval,
              judge_history (list, may be empty), iteration_budget.
    """
    if status not in VALID_EPIC_STATUSES:
        return f"Error: invalid status `{status}`. Valid: {', '.join(sorted(VALID_EPIC_STATUSES))}"

    if kind not in VALID_EPIC_KINDS:
        return f"Error: invalid kind `{kind}`. Valid: {', '.join(sorted(VALID_EPIC_KINDS))}"

    if kind == "goal" and not goal:
        return "Error: kind=goal epics require a goal block (text, rubric_eval, judge_history, iteration_budget)"

    if kind == "goal":
        required = {"text", "rubric_eval", "judge_history", "iteration_budget"}
        missing = required - set(goal.keys())
        if missing:
            return f"Error: goal block missing keys: {', '.join(sorted(missing))}"

    if not epic_id or not all(c.isalnum() or c == "-" for c in epic_id) or epic_id != epic_id.lower():
        return f"Error: epic_id must be lowercase kebab-case, got `{epic_id}`"

    data = _load()
    if _find_epic(data, epic_id):
        return f"Error: epic `{epic_id}` already exists"

    new_epic = {
        "id": epic_id,
        "name": name,
        "kind": kind,
        "status": status,
        "description": description,
        "created": _now(),
        "tasks": [],
    }
    if kind == "goal":
        new_epic["goal"] = goal

    data["epics"].append(new_epic)
    _mutate_and_save(data)
    return f"Created epic `{epic_id}` — {name} ({status}, kind={kind})"
```

- [ ] **Step 4: Run tests to verify pass**

```bash
cd plugins/taskmaster && python -m pytest tests/test_epic_kind_goal.py -v
```

Expected: 4 passing.

- [ ] **Step 5: Run full test suite to confirm no regressions**

```bash
cd plugins/taskmaster && python -m pytest -x
```

Expected: all green. If any existing test asserts `epic["kind"]` doesn't exist, update that test to expect `"feature"`.

- [ ] **Step 6: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_epic_kind_goal.py
git commit -m "feat(taskmaster): epic kind discriminator + goal block (kind=feature default, kind=goal enables /goal flow)"
```

---

## Task 3: Epic update — judge_history append

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py:3638` (`backlog_update_epic`)
- Test: `plugins/taskmaster/tests/test_epic_kind_goal.py` (extend)

- [ ] **Step 1: Write the failing test**

Append to `plugins/taskmaster/tests/test_epic_kind_goal.py`:

```python
def test_append_judge_history(fresh_backlog):
    from plugins.taskmaster.backlog_server import backlog_add_epic, backlog_update_epic, _load

    backlog_add_epic("g1", "G1", kind="goal", goal={
        "text": "build x", "rubric_eval": {}, "judge_history": [],
        "iteration_budget": {"in_task_loops_used": 0, "in_task_loops_max": 3,
                             "child_tasks_used": 0, "child_tasks_max": 5},
    })

    entry = {
        "iteration": 1, "after_task": "g1-001", "satisfied": False,
        "gap_kind": "structural",
        "gap_description": "no server entrypoint",
        "ts": "2026-05-10T12:00:00Z",
    }
    out = backlog_update_epic("g1", "judge_history_append", entry)
    assert "Updated" in out

    data = _load()
    epic = next(e for e in data["epics"] if e["id"] == "g1")
    assert len(epic["goal"]["judge_history"]) == 1
    assert epic["goal"]["judge_history"][0]["gap_kind"] == "structural"


def test_judge_history_append_rejects_non_goal_epic(fresh_backlog):
    from plugins.taskmaster.backlog_server import backlog_add_epic, backlog_update_epic
    backlog_add_epic("f1", "F1")  # default kind=feature
    out = backlog_update_epic("f1", "judge_history_append", {"iteration": 1})
    assert "Error" in out
    assert "kind=goal" in out.lower() or "not a goal" in out.lower()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd plugins/taskmaster && python -m pytest tests/test_epic_kind_goal.py::test_append_judge_history tests/test_epic_kind_goal.py::test_judge_history_append_rejects_non_goal_epic -v
```

Expected: FAIL — `judge_history_append` is not in `ALLOWED_EPIC_FIELDS`.

- [ ] **Step 3: Modify `backlog_update_epic` to support `judge_history_append`**

Locate `backlog_update_epic` in `backlog_server.py`. Add the special-case handling at the top of its body (before the standard field-update path):

```python
def backlog_update_epic(epic_id: str, field: str, value) -> str:
    """Update an epic field. Special fields: judge_history_append (kind=goal only)."""
    data = _load()
    epic = _find_epic(data, epic_id)
    if not epic:
        return f"Error: epic `{epic_id}` not found"

    if field == "judge_history_append":
        if epic.get("kind") != "goal":
            return f"Error: judge_history_append only valid on kind=goal epics; `{epic_id}` is kind={epic.get('kind', 'feature')}"
        if not isinstance(value, dict):
            return "Error: judge_history_append value must be a dict"
        epic.setdefault("goal", {}).setdefault("judge_history", []).append(value)
        _mutate_and_save(data)
        return f"Updated epic `{epic_id}` — appended judge_history entry (now {len(epic['goal']['judge_history'])} total)"

    # ... existing field-update path unchanged below ...
```

- [ ] **Step 4: Run tests to verify pass**

```bash
cd plugins/taskmaster && python -m pytest tests/test_epic_kind_goal.py -v
```

Expected: all 6 passing.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_epic_kind_goal.py
git commit -m "feat(taskmaster): backlog_update_epic supports judge_history_append for kind=goal epics"
```

---

## Task 4: `backlog_auto_status` — goal-aware fields

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py:2681` (`backlog_auto_status`)
- Test: `plugins/taskmaster/tests/test_epic_kind_goal.py` (extend)

- [ ] **Step 1: Write the failing test**

Append:

```python
def test_auto_status_includes_goal_fields_when_run_is_goal_driven(fresh_backlog, monkeypatch):
    from plugins.taskmaster import backlog_server as bs

    bs.backlog_add_epic("g2", "G2", kind="goal", goal={
        "text": "x", "rubric_eval": {},
        "judge_history": [{"iteration": 1, "satisfied": False, "gap_kind": "small"}],
        "iteration_budget": {"in_task_loops_used": 1, "in_task_loops_max": 3,
                             "child_tasks_used": 0, "child_tasks_max": 5},
    })
    # Stub auto state to a goal-driven run on this epic
    monkeypatch.setattr(bs, "_auto_load_state", lambda: {
        "mode": "task", "target": "g2-001", "epic_id": "g2",
        "cursor": {"task_id": "g2-001", "stage": "IMPLEMENT"},
        "config": {"no_gate": True},
    })
    status = bs.backlog_auto_status()
    assert "kind=goal" in status or "goal-driven" in status
    assert "iteration 1" in status or "in_task_loops_used: 1" in status
    assert "in_task_loops_max" in status
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd plugins/taskmaster && python -m pytest tests/test_epic_kind_goal.py::test_auto_status_includes_goal_fields_when_run_is_goal_driven -v
```

Expected: FAIL — current `backlog_auto_status` has no goal awareness.

- [ ] **Step 3: Extend `backlog_auto_status`**

In the existing `backlog_auto_status` body, after the existing status-line composition, add a goal-awareness block:

```python
# Goal-driven run: surface rubric/iteration counters
state = _auto_load_state()
if state and state.get("epic_id"):
    epic = _find_epic(_load(), state["epic_id"])
    if epic and epic.get("kind") == "goal":
        budget = epic["goal"]["iteration_budget"]
        history_len = len(epic["goal"].get("judge_history", []))
        lines.append("")
        lines.append(f"Goal-driven run on epic `{epic['id']}` (kind=goal)")
        lines.append(f"  Judge iterations: {history_len}")
        lines.append(f"  in_task_loops_used: {budget['in_task_loops_used']} / {budget['in_task_loops_max']}")
        lines.append(f"  child_tasks_used: {budget['child_tasks_used']} / {budget['child_tasks_max']}")
```

(`lines` is the existing list the function builds — verify the variable name in the current implementation and adapt.)

- [ ] **Step 4: Run test**

```bash
cd plugins/taskmaster && python -m pytest tests/test_epic_kind_goal.py -v
```

Expected: all 7 passing.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_epic_kind_goal.py
git commit -m "feat(taskmaster): backlog_auto_status surfaces goal-driven run metadata (kind, iteration counters)"
```

---

## Task 5: `validate_goal_text` — rubric validator function

**Files:**
- Create: `plugins/taskmaster/goal_rubric.py`
- Test: `plugins/taskmaster/tests/test_goal_rubric.py`

This module is intentionally framework-free (no fastmcp/mcp imports) so it can be tested in isolation, mirroring the `taskmaster_v3.py` pattern.

- [ ] **Step 1: Write the failing test**

Create `plugins/taskmaster/tests/test_goal_rubric.py`:

```python
"""Rubric validator: 5-point /goal scoring."""
import pytest


def test_good_goal_passes_all_five():
    from plugins.taskmaster.goal_rubric import validate_goal_text
    text = (
        "Build a multi-file particle physics demo, 60fps minimum, "
        "constrained to plain HTML+canvas (no frameworks), "
        "write tests verifying particle count and collision math, "
        "modify only files under src/demo/."
    )
    eval_ = validate_goal_text(text)
    assert eval_.concrete_outcome == "pass"
    assert eval_.bounded_scope == "pass"
    assert eval_.testable_criteria == "pass"
    assert eval_.constraints_stated == "pass"
    assert eval_.tests_planned == "pass"
    assert eval_.severity() == "pass"


def test_make_it_faster_rejected():
    from plugins.taskmaster.goal_rubric import validate_goal_text
    eval_ = validate_goal_text("make my code faster")
    assert eval_.concrete_outcome == "reject"
    assert eval_.severity() == "reject"
    assert "concrete outcome" in eval_.reject_reason().lower()


def test_explore_pytorch_rejected():
    from plugins.taskmaster.goal_rubric import validate_goal_text
    eval_ = validate_goal_text("explore pytorch")
    assert eval_.severity() == "reject"


def test_no_constraints_warns_not_rejects():
    from plugins.taskmaster.goal_rubric import validate_goal_text
    text = "Add a chip rail to viewer/js/screens/ideas.js, snapshot test verifies it renders."
    eval_ = validate_goal_text(text)
    assert eval_.constraints_stated == "warn"
    assert eval_.severity() in {"warn", "pass"}  # depends on other checks
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd plugins/taskmaster && python -m pytest tests/test_goal_rubric.py -v
```

Expected: FAIL — module does not exist.

- [ ] **Step 3: Implement `goal_rubric.py`**

Create `plugins/taskmaster/goal_rubric.py`:

```python
"""/goal rubric — five-point validator. Framework-free for isolated testing.

The full rubric is documented in skills/goal/references/rubric.md. This module
is the executable contract: regex / keyword heuristics that approximate the
human judgments described there. It is deliberately tunable — first-pass
heuristics are picked for high precision on rejects (no false-pass), and we
expect to widen the keyword lists as real /goal traffic surfaces edge cases.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Reject patterns — vague intentions with no concrete artifact.
_VAGUE_PATTERNS = [
    r"\bmake\s+(?:my|the|this)\s+code\s+(?:better|faster|cleaner|nicer)\b",
    r"\bimprove\s+(?:performance|the\s+code|things)\b",
    r"\bexplore\s+\w+\s*$",  # "explore pytorch" with no further constraint
    r"\bclean\s+up\s+the\s+codebase\b",
    r"\bfix\s+(?:bugs|issues)\b\s*$",
]

# Quantifiable / observable signals — a number, a unit, a named output.
_QUANTIFIABLE_PATTERNS = [
    r"\b\d+(?:\.\d+)?\s*(?:fps|ms|s|sec|seconds|hz|MB|GB|KB|%|tokens?/sec|requests?/sec)\b",
    r"\b\d+(?:\.\d+)?\s+(?:minimum|maximum|min|max|or\s+(?:less|more|better))\b",
    r"\beval(?:uation)?\s+(?:reaches|hits|score)\s+\d",
    r"\ball\s+\d+\s+\w+",  # "all 30 imports", "all 12 tests"
    r"\b(?:passes?|matches?|equals?)\s+\w+",
    r"\bplaywright\s+(?:sees|verifies|asserts)",
]

# Scope signals — paths, file references, named components.
_SCOPE_PATTERNS = [
    r"[a-zA-Z_][\w/.-]*\.(py|js|ts|tsx|jsx|md|yaml|yml|html|css|sh)\b",
    r"\b(?:src|plugins|viewer|tests|docs)/[\w./-]+",
    r"\bunder\s+\w+/",
]

# Constraint signals — what NOT to do, library restrictions, size limits.
_CONSTRAINT_PATTERNS = [
    r"\bdon'?t\s+(?:break|change|modify|touch)\b",
    r"\bonly\s+(?:use|with|inside)\s+\w+",
    r"\bno\s+new\s+(?:deps|dependencies|libraries)\b",
    r"\bunder\s+\d+\s+(?:lines|kb|tokens)\b",
    r"\bconstrained\s+to\b",
    r"\bwithout\s+(?:adding|introducing)\b",
]

# Test-plan signals.
_TEST_PATTERNS = [
    r"\b(?:write|add|run)\s+(?:a\s+)?(?:tests?|benchmark|playwright|snapshot)",
    r"\btests?\s+(?:verify|verifies|ensure|confirm)\b",
    r"\b(?:pytest|playwright|jest|vitest)\b",
]


@dataclass
class RubricEval:
    concrete_outcome: str = "reject"   # pass | warn | reject
    bounded_scope: str = "reject"
    testable_criteria: str = "reject"
    constraints_stated: str = "warn"   # never reject — only warns
    tests_planned: str = "warn"        # never reject — only warns
    accept_vague: bool = False

    def severity(self) -> str:
        verdicts = [
            self.concrete_outcome, self.bounded_scope, self.testable_criteria,
            self.constraints_stated, self.tests_planned,
        ]
        if "reject" in verdicts:
            return "reject"
        if "warn" in verdicts:
            return "warn"
        return "pass"

    def reject_reason(self) -> str:
        bits = []
        if self.concrete_outcome == "reject":
            bits.append("concrete outcome — name what's being built/changed/optimized")
        if self.bounded_scope == "reject":
            bits.append("bounded scope — name files, components, or behaviors")
        if self.testable_criteria == "reject":
            bits.append("testable criteria — give a number, output, or observable behavior")
        return "; ".join(bits) or ""

    def to_dict(self) -> dict:
        return {
            "concrete_outcome": self.concrete_outcome,
            "bounded_scope": self.bounded_scope,
            "testable_criteria": self.testable_criteria,
            "constraints_stated": self.constraints_stated,
            "tests_planned": self.tests_planned,
            "accept_vague": self.accept_vague,
        }


def _matches_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def validate_goal_text(text: str, accept_vague: bool = False) -> RubricEval:
    """Score a goal string against the 5-point rubric.

    Heuristic, regex-based. Conservative on rejects (no false-pass), generous
    on warns. Iterate keyword lists as real traffic surfaces edge cases.
    """
    eval_ = RubricEval(accept_vague=accept_vague)

    # R1. Concrete outcome
    if _matches_any(text, _VAGUE_PATTERNS):
        eval_.concrete_outcome = "reject"
    elif re.search(r"\b(?:build|add|port|implement|refactor|fix|optimize|create|wire)\s+\w+", text, re.IGNORECASE):
        eval_.concrete_outcome = "pass"
    else:
        eval_.concrete_outcome = "warn"

    # R2. Bounded scope
    if _matches_any(text, _SCOPE_PATTERNS):
        eval_.bounded_scope = "pass"
    elif re.search(r"\bthe\s+(?:codebase|project|repo|app)\b", text, re.IGNORECASE):
        eval_.bounded_scope = "reject"
    else:
        eval_.bounded_scope = "warn"

    # R3. Testable criteria
    if _matches_any(text, _QUANTIFIABLE_PATTERNS):
        eval_.testable_criteria = "pass"
    elif re.search(r"\buntil\s+(?:everything|all)\s+(?:works|is\s+fixed|is\s+done)\b", text, re.IGNORECASE):
        eval_.testable_criteria = "reject"
    else:
        eval_.testable_criteria = "warn"

    # R4. Constraints (warn-only)
    eval_.constraints_stated = "pass" if _matches_any(text, _CONSTRAINT_PATTERNS) else "warn"

    # R5. Tests planned (warn-only)
    eval_.tests_planned = "pass" if _matches_any(text, _TEST_PATTERNS) else "warn"

    return eval_
```

- [ ] **Step 4: Run tests**

```bash
cd plugins/taskmaster && python -m pytest tests/test_goal_rubric.py -v
```

Expected: 4 passing. If a heuristic misses, tighten the regex or expand the keyword list — do not relax the test.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/goal_rubric.py plugins/taskmaster/tests/test_goal_rubric.py
git commit -m "feat(taskmaster): /goal rubric validator (5-point heuristic, framework-free)"
```

---

## Task 6: `taskmaster:goal-judge` agent (the first plugin subagent)

**Files:**
- Create: `plugins/taskmaster/agents/goal-judge.md`
- Test: `plugins/taskmaster/tests/test_goal_judge_agent.py`

**Important:** Before writing this file, invoke `plugin-dev:agent-development` per project CLAUDE.md. That skill governs frontmatter rules (description field is the trigger surface), tool scoping, and when-to-use conventions.

- [ ] **Step 1: Write the agent definition file**

Create `plugins/taskmaster/agents/goal-judge.md`:

```markdown
---
name: goal-judge
description: |
  Adversarial completion-judge for /goal-driven taskmaster auto-runs. Reads the
  parent epic's goal text, rubric, recent commits, test output, diff, and any
  evidence files — then returns a structured JSON verdict on whether the goal
  is satisfied. Read-only by contract: never edits, never commits, never mutates
  backlog state. Use ONLY at the GOAL_JUDGE stage of taskmaster:auto-task.
tools: [Read, Glob, Grep, Bash]
model: opus
---

# goal-judge — completion judge for /goal-driven runs

You are the completion judge for a taskmaster /goal run. Your only job is to
decide whether the goal stated in the parent Epic has actually been satisfied
by the work done so far. You return one structured JSON object and stop.

## Inputs the orchestrator gives you

The orchestrator includes in its prompt:
- `epic.goal.text` — the original goal text
- `epic.goal.rubric_eval` — the 5-point eval at /goal time
- `epic.goal.judge_history` — your prior verdicts on this goal (for follow-up iterations)
- `epic.goal.iteration_budget` — current usage vs max
- `current_task_id` — the most recently completed child task
- `commits` — list of commit shas in this iteration
- `test_output` — stdout of the most recent test run
- `diff` — the cumulative diff produced this iteration

## Hard rules

1. **Refuse proxy signals.** "Tests passed once" / "build green" / "no errors logged"
   / "the implementation looks complete" are NEVER sufficient. The verdict requires
   evidence that the SPECIFIC success criterion stated in `epic.goal.text` was met.
2. **Run things to verify.** If the goal says "60fps minimum," run the relevant
   benchmark yourself with Bash. Do not accept the spec or plan as evidence.
3. **Cite evidence.** Every `satisfied=true` verdict must list at least one piece
   of concrete evidence (commit sha, test name + result, benchmark number, file
   path). No evidence ⇒ `satisfied=false`.
4. **Classify gaps deliberately.**
   - `gap_kind="small"` — tweakable miss within current scope: failing assertion,
     missed edge case, off-by-one in a number target, performance number close
     but not at target ("got 55fps, target 60").
   - `gap_kind="structural"` — missing subsystem, new requirement that surfaced
     during implementation, scope expansion the current task can't absorb.
5. **Stay read-only.** You have Read / Glob / Grep / Bash. Never use Edit, Write,
   or any backlog mutation. Bash is for running tests and benchmarks only — not
   for git commits or file modifications.

## Return shape (your final message must be exactly this JSON, no commentary)

```json
{
  "satisfied": false,
  "gap_kind": "structural",
  "gap_description": "Goal specifies serving on localhost:5000; implementation builds the demo but does not start a server. Need a follow-up task to add the server entrypoint.",
  "evidence_inspected": [
    "tasks/T-101.md (spec mentions server, plan does not)",
    "src/demo/index.html (no embedded server start)",
    "tests/test_demo.py (no test for server reachability)"
  ],
  "iteration": 1,
  "recommended_next_action": "spawn-follow-up-task"
}
```

`recommended_next_action` is one of: `done`, `loop-in-task`, `spawn-follow-up-task`, `halt-budget-exhausted`.
```

- [ ] **Step 2: Write the prompt regression test fixture and runner**

Create `plugins/taskmaster/tests/test_goal_judge_agent.py`:

```python
"""goal-judge agent: prompt regression suite.

Each fixture is a (epic, current_task_id, commits, test_output, diff) tuple
with an expected verdict shape. Real LLM dispatch happens behind a feature
flag (env: TASKMASTER_RUN_AGENT_TESTS=1) so default test runs stay offline.
"""
import json
import os
from pathlib import Path

import pytest

AGENT_FIXTURES_DIR = Path(__file__).parent / "fixtures" / "goal_judge"


def _fixtures():
    if not AGENT_FIXTURES_DIR.exists():
        return []
    return sorted(AGENT_FIXTURES_DIR.glob("*.json"))


@pytest.mark.parametrize("fixture_path", _fixtures(), ids=lambda p: p.name)
@pytest.mark.skipif(
    os.environ.get("TASKMASTER_RUN_AGENT_TESTS") != "1",
    reason="agent prompt regression requires TASKMASTER_RUN_AGENT_TESTS=1",
)
def test_goal_judge_verdict_matches_expected(fixture_path):
    """Run the goal-judge agent against a frozen scenario, assert verdict shape."""
    fixture = json.loads(fixture_path.read_text())
    # Real implementation dispatches via the Agent tool — beyond unit-test scope.
    # This test stays as scaffolding; the body is filled in once a runner harness
    # is wired (likely via the Claude Code SDK in a follow-up task).
    pytest.skip("agent runner harness pending")


def test_agent_file_has_required_frontmatter():
    """Sanity check: the agent file is well-formed."""
    agent_path = Path(__file__).parents[1] / "agents" / "goal-judge.md"
    assert agent_path.exists(), "goal-judge.md must exist in plugins/taskmaster/agents/"
    text = agent_path.read_text()
    assert text.startswith("---"), "agent file must start with YAML frontmatter"
    assert "name: goal-judge" in text
    assert "tools: [Read, Glob, Grep, Bash]" in text
    assert "model: opus" in text
    assert "Refuse proxy signals" in text, "system prompt must include the no-proxy rule"


def test_agent_return_shape_documented():
    """The agent prompt documents the JSON return shape with all required keys."""
    agent_path = Path(__file__).parents[1] / "agents" / "goal-judge.md"
    text = agent_path.read_text()
    for key in ["satisfied", "gap_kind", "gap_description", "evidence_inspected", "iteration", "recommended_next_action"]:
        assert f'"{key}"' in text, f"return shape missing key: {key}"
```

Create the fixtures directory placeholder:

```bash
mkdir -p plugins/taskmaster/tests/fixtures/goal_judge
```

(No fixture files yet — they accumulate as real runs surface mis-judgments.)

- [ ] **Step 3: Run tests**

```bash
cd plugins/taskmaster && python -m pytest tests/test_goal_judge_agent.py -v
```

Expected: 2 passing (the static-scaffolding tests), agent-runner test skipped.

- [ ] **Step 4: Commit**

```bash
git add plugins/taskmaster/agents/goal-judge.md plugins/taskmaster/tests/test_goal_judge_agent.py plugins/taskmaster/tests/fixtures/goal_judge
git commit -m "feat(taskmaster): goal-judge subagent (read-only completion judge with no-proxy rule)"
```

---

## Task 7: `taskmaster:goal` skill (the /goal entry point)

**Files:**
- Create: `plugins/taskmaster/skills/goal/SKILL.md`
- Test: `plugins/taskmaster/tests/test_goal_skill.py`

**Important:** Before writing the skill, invoke `plugin-dev:skill-development`. The `description` field is the trigger surface — getting it wrong means /goal never fires.

- [ ] **Step 1: Write the failing test for the skill's helper**

Create `plugins/taskmaster/tests/test_goal_skill.py`:

```python
"""Helpers used by taskmaster:goal skill — epic+task creation, defaults."""
import pytest


@pytest.fixture
def fresh_backlog(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".taskmaster").mkdir()
    (tmp_path / ".taskmaster" / "backlog.yaml").write_text(
        "meta:\n  schema_version: 3\nphases: []\nepics: []\ntasks: []\n",
        encoding="utf-8",
    )
    return tmp_path


def test_goal_helper_creates_epic_and_first_task(fresh_backlog):
    from plugins.taskmaster.goal_helpers import create_goal_epic_and_task
    result = create_goal_epic_and_task(
        goal_text=(
            "Build a web-based confetti VFX demo, 60fps minimum, "
            "tests verify particle count and collision math, "
            "modify only files under src/demo/."
        ),
        epic_id_hint="confetti-demo",
        accept_vague=False,
    )
    assert result.severity == "pass"
    assert result.epic_id == "confetti-demo"
    assert result.task_id == "confetti-demo-001"

    from plugins.taskmaster.backlog_server import _load
    data = _load()
    epic = next(e for e in data["epics"] if e["id"] == "confetti-demo")
    assert epic["kind"] == "goal"
    assert epic["goal"]["iteration_budget"]["in_task_loops_max"] == 3
    task = next(t for t in data["tasks"] if t["id"] == "confetti-demo-001")
    assert task["epic"] == "confetti-demo"


def test_goal_helper_rejects_vague_without_flag(fresh_backlog):
    from plugins.taskmaster.goal_helpers import create_goal_epic_and_task
    result = create_goal_epic_and_task(
        goal_text="make my code faster",
        epic_id_hint="vague",
        accept_vague=False,
    )
    assert result.severity == "reject"
    assert result.epic_id is None
    assert "concrete outcome" in result.message.lower()


def test_goal_helper_accepts_vague_with_flag(fresh_backlog):
    from plugins.taskmaster.goal_helpers import create_goal_epic_and_task
    result = create_goal_epic_and_task(
        goal_text="make my code faster",
        epic_id_hint="vague-allowed",
        accept_vague=True,
    )
    assert result.severity == "warn"  # downgraded from reject
    assert result.epic_id == "vague-allowed"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd plugins/taskmaster && python -m pytest tests/test_goal_skill.py -v
```

Expected: FAIL — `goal_helpers` module does not exist.

- [ ] **Step 3: Implement `goal_helpers.py`**

Create `plugins/taskmaster/goal_helpers.py`:

```python
"""Helpers for taskmaster:goal skill. Framework-free for isolated testing."""
from __future__ import annotations

from dataclasses import dataclass

from plugins.taskmaster.backlog_server import (
    backlog_add_epic, backlog_add_task,
)
from plugins.taskmaster.goal_rubric import validate_goal_text


@dataclass
class GoalCreateResult:
    severity: str            # pass | warn | reject
    message: str
    epic_id: str | None
    task_id: str | None


def _first_sentence(text: str) -> str:
    """Cheap first-sentence extractor for task title."""
    for delim in [". ", "\n", "; "]:
        if delim in text:
            return text.split(delim, 1)[0].strip().rstrip(".")
    return text.strip().rstrip(".")[:120]


def create_goal_epic_and_task(
    goal_text: str,
    epic_id_hint: str,
    accept_vague: bool = False,
    in_task_loops_max: int = 3,
    child_tasks_max: int = 5,
) -> GoalCreateResult:
    """Validate goal, create kind=goal epic + first child task. Returns result with severity."""
    eval_ = validate_goal_text(goal_text, accept_vague=accept_vague)
    sev = eval_.severity()

    if sev == "reject" and not accept_vague:
        return GoalCreateResult(
            severity="reject",
            message=f"Goal rejected: {eval_.reject_reason()}. Reply with the missing piece, or pass --accept-vague.",
            epic_id=None, task_id=None,
        )

    # accept_vague downgrades reject → warn (auto-brainstorm fills assumptions)
    effective_sev = "warn" if (sev == "reject" and accept_vague) else sev

    goal_block = {
        "text": goal_text,
        "rubric_eval": eval_.to_dict(),
        "judge_history": [],
        "iteration_budget": {
            "in_task_loops_used": 0,
            "in_task_loops_max": in_task_loops_max,
            "child_tasks_used": 0,
            "child_tasks_max": child_tasks_max,
        },
    }
    epic_out = backlog_add_epic(epic_id_hint, _first_sentence(goal_text), kind="goal", goal=goal_block)
    if epic_out.startswith("Error"):
        return GoalCreateResult(severity="reject", message=epic_out, epic_id=None, task_id=None)

    task_id = f"{epic_id_hint}-001"
    task_title = _first_sentence(goal_text)
    task_body = f"{goal_text}\n\n(See epic `{epic_id_hint}` for rubric and judge history.)"
    task_out = backlog_add_task(
        task_id=task_id, title=task_title, epic=epic_id_hint,
        description=task_body, status="todo", priority="medium",
    )
    if task_out.startswith("Error"):
        return GoalCreateResult(severity="reject", message=task_out, epic_id=epic_id_hint, task_id=None)

    msg = f"Goal locked as `{epic_id_hint}` (severity={effective_sev}). First task `{task_id}` ready for auto-mode."
    return GoalCreateResult(severity=effective_sev, message=msg, epic_id=epic_id_hint, task_id=task_id)
```

- [ ] **Step 4: Run tests**

```bash
cd plugins/taskmaster && python -m pytest tests/test_goal_skill.py -v
```

Expected: 3 passing.

- [ ] **Step 5: Write the SKILL.md file**

Create `plugins/taskmaster/skills/goal/SKILL.md`:

```markdown
---
name: goal
description: |
  Autonomous-from-zero entry point: take a natural-language outcome, validate it
  against the /goal rubric (concrete outcome, bounded scope, testable criteria,
  constraints, tests planned), create a kind=goal Epic and first child Task,
  then fire taskmaster:auto-task to drive the work to LLM-judged completion.

  Invoke when the user says: "/goal <text>", "set a goal to X", "I want to autopilot
  building X", "autopilot from zero", or pastes a goal-shaped outcome they want
  Claude to execute unsupervised. Aliases: /goal-status, /goal-pause, /goal-stop
  map to backlog_auto_status / _pause / _stop with goal-aware output.

  Requires backlog.yaml at v3. The goal must pass the 5-point rubric (loaded from
  references/rubric.md) — vague goals get a one-shot pushback unless --accept-vague.
---

# goal — /goal entry point

This skill turns an outcome statement into an autonomous work run.

## Step 1: Parse input

Accept either:
- Slash form: `/goal <text>` (with optional flags `--accept-vague`, `--no-run`,
  `--epic-id <kebab-id>`, `--in-task-loops <n>`, `--child-tasks <n>`)
- Natural language: "I want to autopilot building X", "set a goal to Y"

Default `epic-id` is derived from the first sentence (kebab-case, max 40 chars).

## Step 2: Validate against the rubric

Load `references/rubric.md` for the canonical criteria. Call:

```python
from plugins.taskmaster.goal_helpers import create_goal_epic_and_task
result = create_goal_epic_and_task(
    goal_text=<text>,
    epic_id_hint=<derived-or-flag>,
    accept_vague=<flag>,
    in_task_loops_max=<flag-or-3>,
    child_tasks_max=<flag-or-5>,
)
```

If `result.severity == "reject"`, print `result.message` and STOP. Do not retry,
do not improve the goal silently. The user supplies the missing piece or passes
`--accept-vague`.

## Step 3: Announce

Print `result.message` (e.g. `Goal locked as \`confetti-demo\` (severity=pass).
First task \`confetti-demo-001\` ready for auto-mode.`).

## Step 4: Fire auto-task (unless --no-run)

```
backlog_auto_start(mode="task", target=result.task_id, no_gate=True)
```

Then invoke `taskmaster:auto-task`. The auto run picks up at PICK and proceeds
through the full lifecycle including the new GOAL_JUDGE stage.

## Step 5: Hand back

Once auto-task returns, print the final goal-judge verdict from
`epic.goal.judge_history[-1]` and the iteration counters from
`epic.goal.iteration_budget`. The user wakes up to receipts.

## What this skill does NOT do

- Does not write the spec or plan — auto-brainstorm does that inside auto-task.
- Does not run the judge — goal-judge subagent does, dispatched from auto-task.
- Does not interactively brainstorm with the user — by design. /goal is the
  unsupervised path. For interactive work, use taskmaster:pick-task.

## See also

- `references/rubric.md` — canonical 5-point rubric (also loaded by
  auto-brainstorm and goal-judge).
- `docs/superpowers/specs/2026-05-10-auto-brainstorm-goal-design.md` —
  design rationale.
```

- [ ] **Step 6: Run all tests**

```bash
cd plugins/taskmaster && python -m pytest -x
```

Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add plugins/taskmaster/goal_helpers.py plugins/taskmaster/skills/goal/SKILL.md plugins/taskmaster/tests/test_goal_skill.py
git commit -m "feat(taskmaster): /goal skill — validate against rubric, create kind=goal epic + first task, fire auto-task"
```

---

## Task 8: `taskmaster:auto-brainstorm` skill (research → draft → iterate → challenger)

**Files:**
- Create: `plugins/taskmaster/skills/auto-brainstorm/SKILL.md`
- Create: `plugins/taskmaster/skills/auto-brainstorm/references/research-prompts.md`

**Important:** Invoke `plugin-dev:skill-development` first.

- [ ] **Step 1: Write `research-prompts.md`**

Create `plugins/taskmaster/skills/auto-brainstorm/references/research-prompts.md`:

```markdown
# Research source prompts

One prompt template per research source. Each is dispatched to a fresh `Explore`
subagent and must return ≤500 words of distilled findings — not raw search results.

## Source 1: IDEA store

> The current task is `{task_id}` titled "{task_title}". Search the project's
> IDEA store via `backlog_idea_list` for ideas whose title, tags, or
> related_tasks intersect this task. Filter to top 5 by relevance. Return a
> distilled summary: for each idea, give one sentence on its content and one
> sentence on how it relates to the current task. If no ideas match, say so.

## Source 2: Lessons + handovers

> The current task is `{task_id}` titled "{task_title}", touching files
> {anchors}. Run `backlog_lesson_match(task_title="{task_title}",
> touched_files={anchors})` and `backlog_handover_list(task_id="{task_id}",
> limit=5)`. Pull full lesson bodies for top 3 matches and full handover bodies
> only for context-handoff session_kind. Return a distilled summary: lessons
> first (rule + reason), then handovers (one sentence per item on what was
> decided or learned).

## Source 3: Web search for prior art

> The current task is "{task_title}". Search the web for how comparable
> projects/products handle this surface area. Prefer credible sources (project
> docs, github discussions, engineering blogs). Three queries max. Return a
> distilled summary: 3–5 prior-art datapoints, each with one sentence of what
> they do + one sentence of what's borrowable for our design.

## Source 4: Cross-domain inspiration (optional, default OFF)

> The current task is "{task_title}". Generate 2–3 metaphors from
> deliberately-unrelated domains (e.g. biology, board games, physical-world
> design) that map onto this problem's structure. For each metaphor, name the
> domain, the parallel structure, and the ONE specific design idea it suggests.
> Skip if the task is mechanical / scope-bound (CRUD endpoints, refactors).
```

- [ ] **Step 2: Write `SKILL.md`**

Create `plugins/taskmaster/skills/auto-brainstorm/SKILL.md`:

```markdown
---
name: auto-brainstorm
description: |
  Unsupervised opinionated spec authoring for taskmaster auto-mode. Replaces
  the handwave "draft a plan" substep at auto-task SPEC_REVIEW. Runs a fixed
  4-phase pipeline: research (parallel Explore subagents over 4 sources)
  → draft spec (Opus) → self-iterate against the /goal rubric (≤3 passes)
  → challenger pass (taskmaster:spec-review unattended). Returns finalized
  spec text written into tasks/<id>.md ## Spec section.

  Invoked from taskmaster:auto-task Step 2. Do NOT invoke from interactive
  pick-task — for human-attended spec authoring, use superpowers:brainstorming.
---

# auto-brainstorm — opinionated unsupervised spec authoring

## When this fires

Only from `taskmaster:auto-task` Step 2 (SPEC_REVIEW). Interactive spec authoring
uses `superpowers:brainstorming` instead. Auto-brainstorm has no human-in-the-loop
gates by design.

## Inputs

- `task_id` — the task being specced.
- `task` — full task body from `backlog_get_task(task_id)`.
- `parent_epic` — full epic record. If `epic.kind == "goal"`, the goal text and
  rubric_eval take precedence over rubric inferred from the task body.

## Phase 1: Research (parallel)

Dispatch 4 `Explore` subagents simultaneously, one per source, using the prompt
templates in `references/research-prompts.md`:

1. IDEA store — `backlog_idea_list` filtered by title/tag/related_task fuzzy match
2. Lessons + handovers — `backlog_lesson_match` + `backlog_handover_list`
3. Web search — credible-source prior art on the task surface
4. Cross-domain inspiration — DEFAULT OFF; enable only when task body or epic
   goal text contains keywords {design, novel, explore, prototype, inspiration}.

Each subagent returns ≤500 words. Aggregate into a `research_brief` (markdown
sections, one per source).

## Phase 2: Draft (Opus, in-context)

Single Opus call. Prompt template:

```
You are drafting a spec for taskmaster auto-mode. The task is:
{task_body}

Parent epic context:
{epic_summary}

Research findings:
{research_brief}

Produce a spec with these exact sections:
- Concrete outcome — one sentence naming what's being built/changed
- Bounded scope — paths/components/behaviors in scope
- Testable success criteria — number, output, or behavior
- Constraints — what NOT to do, library / size / API limits
- Test plan — what verifies done

Each section must be 2–6 sentences. Cite at least one research finding per
major design decision (inline as `> source: lessons L-003` etc.).
```

## Phase 3: Self-iterate (≤3 passes)

Load `plugins/taskmaster/skills/goal/references/rubric.md` and check the draft
against each of the 5 checks (R1–R5). For any check at `warn` or `reject`,
regenerate that section only — do not rewrite the whole spec. Stop when all 5
pass or after 3 iterations.

If 3 iterations don't reach all-pass, hand off to challenger anyway with the
remaining warnings noted in the spec body as `> RUBRIC WARN:` callouts.

## Phase 4: Challenger pass

Invoke `taskmaster:spec-review` as a subagent in unattended mode (see
`spec-review/SKILL.md` for the unattended contract). It returns a list of
findings — assumptions, scope drift, edge cases, blast radius.

- Apply non-controversial findings directly (e.g. clarifying ambiguous wording).
- Surface controversial findings inline as `> CHALLENGER FLAGGED: <text>`
  callouts the IMPLEMENT step can react to.

## Output

Write the final spec into `tasks/<task_id>.md` body's `## Spec` section using
Edit. Then return control to auto-task — the next substep is
`superpowers:writing-plans` for the `## Plan` section.

## Token discipline

- Research subagent prompts cap returns at 500 words.
- Draft is ≤2000 tokens.
- Self-iteration regenerates one section at a time, not the full spec.
- Challenger findings are summarized, not pasted full.

## Failure modes

- All 4 research sources return empty: proceed to draft with `research_brief = "(no prior context found)"`. Auto-task may halt at TEST stage if assumptions are wrong.
- Draft consistently fails rubric after 3 iterations: ship with WARN callouts; auto-task TEST and goal-judge will catch downstream gaps.
- Challenger pass crashes: log the error, ship the post-iterate spec without challenger findings, surface in the handover stub.
```

- [ ] **Step 3: Write a smoke test for the skill structure**

Create `plugins/taskmaster/tests/test_auto_brainstorm.py`:

```python
"""auto-brainstorm: skill file structure + reference doc loading."""
from pathlib import Path


def test_auto_brainstorm_skill_exists():
    p = Path(__file__).parents[1] / "skills" / "auto-brainstorm" / "SKILL.md"
    assert p.exists()
    text = p.read_text()
    assert text.startswith("---")
    assert "name: auto-brainstorm" in text
    # Trigger surface keywords for the description
    assert "auto-task" in text
    assert "spec authoring" in text or "spec-authoring" in text


def test_research_prompts_reference_exists():
    p = Path(__file__).parents[1] / "skills" / "auto-brainstorm" / "references" / "research-prompts.md"
    assert p.exists()
    text = p.read_text()
    for source in ["IDEA store", "Lessons", "prior art", "Cross-domain"]:
        assert source in text


def test_skill_references_rubric_doc():
    p = Path(__file__).parents[1] / "skills" / "auto-brainstorm" / "SKILL.md"
    text = p.read_text()
    assert "skills/goal/references/rubric.md" in text
```

- [ ] **Step 4: Run tests**

```bash
cd plugins/taskmaster && python -m pytest tests/test_auto_brainstorm.py -v
```

Expected: 3 passing.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/skills/auto-brainstorm plugins/taskmaster/tests/test_auto_brainstorm.py
git commit -m "feat(taskmaster): auto-brainstorm skill (research → draft → iterate → challenger)"
```

---

## Task 9: `taskmaster:spec-review` — unattended-mode contract

**Files:**
- Modify: `plugins/taskmaster/skills/spec-review/SKILL.md`

- [ ] **Step 1: Write a test for the unattended contract documentation**

Create `plugins/taskmaster/tests/test_spec_review_unattended.py`:

```python
from pathlib import Path


def test_spec_review_documents_unattended_mode():
    p = Path(__file__).parents[1] / "skills" / "spec-review" / "SKILL.md"
    text = p.read_text()
    # The unattended contract MUST be documented and discoverable
    assert "unattended" in text.lower()
    assert "findings" in text.lower()
    # Auto-brainstorm calls this — the contract must specify return shape
    assert "auto-brainstorm" in text or "auto-task" in text
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd plugins/taskmaster && python -m pytest tests/test_spec_review_unattended.py -v
```

Expected: FAIL — current spec-review doesn't document unattended mode.

- [ ] **Step 3: Read existing spec-review/SKILL.md and add an "Unattended mode" section**

Read the current file:

```bash
# (use the Read tool — paste the result inline mentally; do not run cat)
```

Append the following section after the existing skill body (use Edit, not Write):

```markdown

## Unattended mode (called from auto-brainstorm)

When invoked from `taskmaster:auto-brainstorm` (or any other auto-mode caller),
spec-review runs in **unattended mode**:

- No `AskUserQuestion` calls — there is no human present.
- No editor invocations — return findings as data, do not modify the spec.
- Return a single JSON-shaped final message:

```json
{
  "findings": [
    {
      "kind": "assumption",
      "severity": "low",
      "text": "Spec assumes `viewer/js/screens/issues.js` uses chip-toggle helper; verify before relying on it."
    },
    {
      "kind": "scope-drift",
      "severity": "high",
      "text": "Spec mentions modifying kanban.js — that's outside the named scope."
    },
    {
      "kind": "edge-case",
      "severity": "medium",
      "text": "Spec doesn't address what happens when judge_history is empty on first iteration."
    }
  ]
}
```

`kind` ∈ {assumption, scope-drift, edge-case, blast-radius, missing-test}.
`severity` ∈ {low, medium, high}.

The caller (auto-brainstorm) decides which findings to apply and which to
surface as inline `> CHALLENGER FLAGGED:` callouts in the spec.
```

- [ ] **Step 4: Run test**

```bash
cd plugins/taskmaster && python -m pytest tests/test_spec_review_unattended.py -v
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/skills/spec-review/SKILL.md plugins/taskmaster/tests/test_spec_review_unattended.py
git commit -m "feat(taskmaster): spec-review unattended-mode contract (returns findings JSON for auto-brainstorm)"
```

---

## Task 10: `taskmaster:auto-task` — Step 2 invokes auto-brainstorm; new GOAL_JUDGE stage

**Files:**
- Modify: `plugins/taskmaster/skills/auto-task/SKILL.md`
- Test: `plugins/taskmaster/tests/test_auto_task_goal_judge_stage.py`

- [ ] **Step 1: Write the failing test for GOAL_JUDGE state-machine routing**

Create `plugins/taskmaster/tests/test_auto_task_goal_judge_stage.py`:

```python
"""auto-task: GOAL_JUDGE stage routing on judge verdicts.

These tests verify the state machine logic via the auto state helpers.
The real LLM judge dispatch is covered by test_goal_judge_agent.py.
"""
import pytest


@pytest.fixture
def fresh_backlog(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".taskmaster").mkdir()
    (tmp_path / ".taskmaster" / "backlog.yaml").write_text(
        "meta:\n  schema_version: 3\nphases: []\nepics: []\ntasks: []\n",
        encoding="utf-8",
    )
    return tmp_path


def test_goal_judge_stage_skipped_for_kind_feature(fresh_backlog):
    from plugins.taskmaster.auto_state import next_stage_after_end_session
    nxt = next_stage_after_end_session(epic_kind="feature", judge_verdict=None)
    assert nxt == "DONE"


def test_goal_judge_stage_runs_for_kind_goal(fresh_backlog):
    from plugins.taskmaster.auto_state import next_stage_after_end_session
    nxt = next_stage_after_end_session(epic_kind="goal", judge_verdict=None)
    assert nxt == "GOAL_JUDGE"


def test_judge_satisfied_advances_to_done(fresh_backlog):
    from plugins.taskmaster.auto_state import next_stage_after_judge
    verdict = {"satisfied": True, "recommended_next_action": "done"}
    epic_goal = {"iteration_budget": {"in_task_loops_used": 0, "in_task_loops_max": 3,
                                       "child_tasks_used": 0, "child_tasks_max": 5}}
    nxt = next_stage_after_judge(verdict, epic_goal)
    assert nxt == "GOAL_DONE"


def test_judge_small_gap_loops_back_to_implement(fresh_backlog):
    from plugins.taskmaster.auto_state import next_stage_after_judge
    verdict = {"satisfied": False, "gap_kind": "small",
               "recommended_next_action": "loop-in-task"}
    epic_goal = {"iteration_budget": {"in_task_loops_used": 0, "in_task_loops_max": 3,
                                       "child_tasks_used": 0, "child_tasks_max": 5}}
    nxt = next_stage_after_judge(verdict, epic_goal)
    assert nxt == "IMPLEMENT"


def test_judge_structural_gap_spawns_follow_up_task(fresh_backlog):
    from plugins.taskmaster.auto_state import next_stage_after_judge
    verdict = {"satisfied": False, "gap_kind": "structural",
               "recommended_next_action": "spawn-follow-up-task"}
    epic_goal = {"iteration_budget": {"in_task_loops_used": 0, "in_task_loops_max": 3,
                                       "child_tasks_used": 0, "child_tasks_max": 5}}
    nxt = next_stage_after_judge(verdict, epic_goal)
    assert nxt == "SPAWN_CHILD_TASK"


def test_in_task_budget_exhausted_escalates_to_structural(fresh_backlog):
    from plugins.taskmaster.auto_state import next_stage_after_judge
    verdict = {"satisfied": False, "gap_kind": "small"}
    epic_goal = {"iteration_budget": {"in_task_loops_used": 3, "in_task_loops_max": 3,
                                       "child_tasks_used": 0, "child_tasks_max": 5}}
    nxt = next_stage_after_judge(verdict, epic_goal)
    assert nxt == "SPAWN_CHILD_TASK"  # forced escalation


def test_child_task_budget_exhausted_halts(fresh_backlog):
    from plugins.taskmaster.auto_state import next_stage_after_judge
    verdict = {"satisfied": False, "gap_kind": "structural"}
    epic_goal = {"iteration_budget": {"in_task_loops_used": 0, "in_task_loops_max": 3,
                                       "child_tasks_used": 5, "child_tasks_max": 5}}
    nxt = next_stage_after_judge(verdict, epic_goal)
    assert nxt == "HALT_BUDGET_EXHAUSTED"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd plugins/taskmaster && python -m pytest tests/test_auto_task_goal_judge_stage.py -v
```

Expected: FAIL — `auto_state` module does not exist.

- [ ] **Step 3: Implement `auto_state.py` with the routing helpers**

Create `plugins/taskmaster/auto_state.py`:

```python
"""auto-task state machine helpers — pure functions over verdicts and budgets."""
from __future__ import annotations


def next_stage_after_end_session(epic_kind: str, judge_verdict: dict | None) -> str:
    """After END_SESSION, decide whether to run goal-judge or finish."""
    if epic_kind == "goal":
        return "GOAL_JUDGE"
    return "DONE"


def next_stage_after_judge(verdict: dict, epic_goal: dict) -> str:
    """Given a goal-judge verdict and the parent epic's goal block, decide next stage."""
    budget = epic_goal["iteration_budget"]

    if verdict.get("satisfied"):
        return "GOAL_DONE"

    gap_kind = verdict.get("gap_kind", "structural")
    in_task_used = budget["in_task_loops_used"]
    in_task_max = budget["in_task_loops_max"]
    child_used = budget["child_tasks_used"]
    child_max = budget["child_tasks_max"]

    if child_used >= child_max:
        return "HALT_BUDGET_EXHAUSTED"

    if gap_kind == "small":
        if in_task_used >= in_task_max:
            return "SPAWN_CHILD_TASK"  # escalation
        return "IMPLEMENT"

    # gap_kind == "structural" (or anything not "small")
    return "SPAWN_CHILD_TASK"
```

- [ ] **Step 4: Run tests**

```bash
cd plugins/taskmaster && python -m pytest tests/test_auto_task_goal_judge_stage.py -v
```

Expected: 7 passing.

- [ ] **Step 5: Update `auto-task/SKILL.md` — Step 2 + new Step 9**

Edit `plugins/taskmaster/skills/auto-task/SKILL.md`:

**Replace** the existing Step 2 (SPEC_REVIEW) substep `1. If the task body has no \`## Spec / Plan\` section yet, draft one. Use \`superpowers:writing-plans\` if the task is non-trivial.` with:

```
1. If the task body has no `## Spec` section yet, invoke `taskmaster:auto-brainstorm`
   as a subagent. It returns the finalized spec text and writes it into
   `tasks/<task_id>.md` `## Spec`. Then invoke `superpowers:writing-plans` to
   convert the spec into a `## Plan` section.
```

**Insert** a new section after Step 8 (END_SESSION):

```markdown
## Step 9: GOAL_JUDGE (only when parent epic kind=goal)

When `cursor.stage == "GOAL_JUDGE"`:

1. Load the parent epic. If `epic.kind != "goal"`, skip directly to DONE.
2. Bump `epic.goal.iteration_budget.in_task_loops_used` (if this iteration was
   an in-task loop) or `child_tasks_used` (if a freshly-spawned child task).
3. Dispatch the `taskmaster:goal-judge` subagent (see
   `plugins/taskmaster/agents/goal-judge.md`). Pass it:
   - `epic.goal.text`, `epic.goal.rubric_eval`, `epic.goal.judge_history`,
     `epic.goal.iteration_budget`
   - `current_task_id`, the commit shas from this iteration, the test_output,
     the diff
4. Parse the agent's JSON return. Append it to `epic.goal.judge_history` via
   `backlog_update_epic(<epic_id>, "judge_history_append", verdict)`.
5. Compute next stage with `auto_state.next_stage_after_judge(verdict, epic.goal)`:
   - `GOAL_DONE` → write goal-level handover, mark epic status=done, finish.
   - `IMPLEMENT` → loop back to Step 4 IMPLEMENT on the same task (in-task gap).
   - `SPAWN_CHILD_TASK` → create a new task in the same epic with body =
     `verdict.gap_description`, advance cursor to PICK on the new task.
   - `HALT_BUDGET_EXHAUSTED` → write a context-handoff handover with
     `next_action = verdict.gap_description`, leave epic status=in-progress,
     stop. Surface in dashboard under "stalled goals."
```

- [ ] **Step 6: Run all tests**

```bash
cd plugins/taskmaster && python -m pytest -x
```

Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add plugins/taskmaster/auto_state.py plugins/taskmaster/skills/auto-task/SKILL.md plugins/taskmaster/tests/test_auto_task_goal_judge_stage.py
git commit -m "feat(taskmaster): auto-task GOAL_JUDGE stage + auto-brainstorm wiring at SPEC_REVIEW"
```

---

## Task 11: Router and start-session integration

**Files:**
- Modify: `plugins/taskmaster/skills/taskmaster/SKILL.md`
- Modify: `plugins/taskmaster/skills/start-session/SKILL.md`

- [ ] **Step 1: Write the routing test**

Create `plugins/taskmaster/tests/test_taskmaster_routing.py`:

```python
from pathlib import Path


def test_taskmaster_router_routes_goal_intents():
    p = Path(__file__).parents[1] / "skills" / "taskmaster" / "SKILL.md"
    text = p.read_text()
    assert "/goal" in text
    assert "taskmaster:goal" in text or "goal skill" in text.lower()


def test_start_session_surfaces_running_goals():
    p = Path(__file__).parents[1] / "skills" / "start-session" / "SKILL.md"
    text = p.read_text()
    assert "kind=goal" in text or "goal-driven" in text or "running goals" in text.lower()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd plugins/taskmaster && python -m pytest tests/test_taskmaster_routing.py -v
```

Expected: FAIL — neither file mentions /goal yet.

- [ ] **Step 3: Add routing rows**

Edit `plugins/taskmaster/skills/taskmaster/SKILL.md`. Find the routing table and add (use Edit, locate the existing table by its header):

```markdown
| `/goal <text>`, "autopilot from zero", "set a goal to X", "I want to autopilot building Y" | taskmaster:goal |
| `/goal-status`, `/goal-pause`, `/goal-stop` | aliases for backlog_auto_status / _pause / _stop, with goal-aware output |
```

Edit `plugins/taskmaster/skills/start-session/SKILL.md`. Add a section after the dashboard rendering instructions:

```markdown
## Surfacing running goals

If any epic has `kind == "goal"` and `status != "done"`, surface it in the
dashboard as a separate "Running goals" section (above the regular epic list).
For each, show:
- Epic id, name, status
- Iteration counters: `judge=N · in_task=A/B · children=C/D`
- The most recent `judge_history` entry's `gap_description` (truncated to 80 chars),
  or `(no judge yet)` if history is empty.

If a goal is `HALT_BUDGET_EXHAUSTED` (epic status=in-progress AND
child_tasks_used == child_tasks_max AND latest judge satisfied=false), tag it
"stalled" — these need user attention to resume.
```

- [ ] **Step 4: Run tests**

```bash
cd plugins/taskmaster && python -m pytest tests/test_taskmaster_routing.py -v
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/skills/taskmaster/SKILL.md plugins/taskmaster/skills/start-session/SKILL.md plugins/taskmaster/tests/test_taskmaster_routing.py
git commit -m "feat(taskmaster): router routes /goal intents; start-session surfaces running goals"
```

---

## Task 12: Viewer — kanban renders goal-kind epics with rubric chip + iteration counter

**Files:**
- Modify: `plugins/taskmaster/viewer/js/screens/kanban.js`
- Test: `plugins/taskmaster/viewer/tests/unit/kanban-goal-epic.test.js` (if jsdom test infra exists; otherwise snapshot test)

- [ ] **Step 1: Inspect existing kanban epic rendering**

```bash
# (Use Read tool on plugins/taskmaster/viewer/js/screens/kanban.js. Find the
# function that renders an epic header. Note its signature and where the chip
# rail is composed.)
```

- [ ] **Step 2: Write a snapshot test**

If the viewer has a jsdom-based test runner, write a unit test. If not, write a
DOM-fixture smoke test in plain JS (existing patterns under
`plugins/taskmaster/viewer/tests/`):

```javascript
// plugins/taskmaster/viewer/tests/unit/kanban-goal-epic.test.js
import { renderEpicHeader } from "../../js/screens/kanban.js";

test("goal-kind epic renders rubric chip + iteration counter, no left rail", () => {
  const epic = {
    id: "confetti-demo",
    name: "Confetti Demo",
    kind: "goal",
    status: "in-progress",
    goal: {
      rubric_eval: { concrete_outcome: "pass", bounded_scope: "pass",
                     testable_criteria: "pass", constraints_stated: "warn",
                     tests_planned: "pass", accept_vague: false },
      judge_history: [{ iteration: 1, satisfied: false, gap_kind: "small" }],
      iteration_budget: { in_task_loops_used: 1, in_task_loops_max: 3,
                          child_tasks_used: 0, child_tasks_max: 5 },
    },
  };
  const html = renderEpicHeader(epic);
  expect(html).toContain('data-kind="goal"');
  expect(html).toContain('chip--rubric');     // rubric chip rendered
  expect(html).toContain('1/3');              // in-task counter
  expect(html).toContain('0/5');              // child counter
  expect(html).not.toContain('border-left');  // no left rail (per project rule)
});
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd plugins/taskmaster/viewer && npm test -- kanban-goal-epic
```

Expected: FAIL — `renderEpicHeader` doesn't differentiate kind=goal.

- [ ] **Step 4: Modify `kanban.js`**

In the existing epic-header rendering function, add a kind-aware branch. Add
the `data-kind` attribute and, when `epic.kind === "goal"`, append the rubric
chip and iteration counter:

```javascript
function renderEpicHeader(epic) {
  const baseChips = renderBaseChips(epic);                // existing helper
  const goalChips = epic.kind === "goal" ? renderGoalChips(epic.goal) : "";
  return `
    <div class="epic-header" data-kind="${epic.kind || "feature"}">
      <span class="epic-title">${escape(epic.name)}</span>
      ${baseChips}
      ${goalChips}
    </div>
  `;
}

function renderGoalChips(goal) {
  const sev = goalSeverity(goal.rubric_eval);  // pass | warn | reject
  const b = goal.iteration_budget;
  const judgeIter = (goal.judge_history || []).length;
  return `
    <span class="chip chip--rubric chip--rubric-${sev}" title="Rubric: ${sev}">${sev}</span>
    <span class="chip chip--judge-iter" title="Judge iterations">judge ${judgeIter}</span>
    <span class="chip chip--in-task" title="In-task loops">in-task ${b.in_task_loops_used}/${b.in_task_loops_max}</span>
    <span class="chip chip--children" title="Child tasks">children ${b.child_tasks_used}/${b.child_tasks_max}</span>
  `;
}

function goalSeverity(eval_) {
  const verdicts = [eval_.concrete_outcome, eval_.bounded_scope,
                    eval_.testable_criteria, eval_.constraints_stated,
                    eval_.tests_planned];
  if (verdicts.includes("reject")) return "reject";
  if (verdicts.includes("warn")) return "warn";
  return "pass";
}
```

In the corresponding CSS file (find it in `viewer/css/`), add tinted-background
chip styles **without left borders** (per project rule):

```css
.chip--rubric-pass    { background: var(--ok-tint); }
.chip--rubric-warn    { background: var(--warn-tint); }
.chip--rubric-reject  { background: var(--err-tint); }
.chip--judge-iter,
.chip--in-task,
.chip--children      { background: var(--neutral-tint); font-variant-numeric: tabular-nums; }
.epic-header[data-kind="goal"] {
  /* visual differentiation via background only — NO border-left, NO box-shadow */
  background: linear-gradient(to right, var(--neutral-tint-soft), transparent 40%);
}
```

- [ ] **Step 5: Run test**

```bash
cd plugins/taskmaster/viewer && npm test -- kanban-goal-epic
```

Expected: pass.

- [ ] **Step 6: Verify visually**

```bash
cd plugins/taskmaster/viewer && npm run dev
# Open http://localhost:<port>, navigate to kanban with at least one
# kind=goal epic. Confirm: rubric chip + iteration counters render, no left
# rail, no hover-motion, no box-shadow. Spot-check existing kind=feature
# epics still render as before.
```

- [ ] **Step 7: Commit**

```bash
git add plugins/taskmaster/viewer/js/screens/kanban.js plugins/taskmaster/viewer/css plugins/taskmaster/viewer/tests/unit/kanban-goal-epic.test.js
git commit -m "feat(taskmaster-viewer): kanban renders kind=goal epics with rubric + iteration chips"
```

---

## Task 13: End-to-end smoke test

**Files:**
- Create: `plugins/taskmaster/tests/test_e2e_goal_smoke.py`

- [ ] **Step 1: Write the e2e smoke test**

```python
"""End-to-end smoke: /goal creates kind=goal epic+task, fires auto-state stub,
and the state machine routing comes back DONE on a satisfied verdict."""
import pytest


@pytest.fixture
def fresh_backlog(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".taskmaster").mkdir()
    (tmp_path / ".taskmaster" / "backlog.yaml").write_text(
        "meta:\n  schema_version: 3\nphases: []\nepics: []\ntasks: []\n",
        encoding="utf-8",
    )
    return tmp_path


def test_goal_to_done_happy_path(fresh_backlog):
    from plugins.taskmaster.goal_helpers import create_goal_epic_and_task
    from plugins.taskmaster.auto_state import next_stage_after_end_session, next_stage_after_judge
    from plugins.taskmaster.backlog_server import _load, backlog_update_epic

    # 1. /goal creates epic + first task
    res = create_goal_epic_and_task(
        goal_text="Build src/demo/index.html serving on localhost:5000, "
                  "playwright test verifies localhost:5000 returns 200.",
        epic_id_hint="demo-smoke",
        accept_vague=False,
    )
    assert res.severity == "pass"

    # 2. After end_session for kind=goal epic, next stage is GOAL_JUDGE
    nxt = next_stage_after_end_session(epic_kind="goal", judge_verdict=None)
    assert nxt == "GOAL_JUDGE"

    # 3. Simulate goal-judge verdict: satisfied=true with evidence
    verdict = {
        "satisfied": True,
        "gap_kind": None,
        "gap_description": None,
        "evidence_inspected": ["src/demo/index.html exists", "playwright test PASS"],
        "iteration": 1,
        "recommended_next_action": "done",
    }
    backlog_update_epic("demo-smoke", "judge_history_append", verdict)

    # 4. State machine returns GOAL_DONE
    data = _load()
    epic = next(e for e in data["epics"] if e["id"] == "demo-smoke")
    nxt = next_stage_after_judge(verdict, epic["goal"])
    assert nxt == "GOAL_DONE"

    # 5. Judge history is persisted
    assert len(epic["goal"]["judge_history"]) == 1
    assert epic["goal"]["judge_history"][0]["satisfied"] is True


def test_goal_to_structural_loop(fresh_backlog):
    from plugins.taskmaster.goal_helpers import create_goal_epic_and_task
    from plugins.taskmaster.auto_state import next_stage_after_judge
    from plugins.taskmaster.backlog_server import _load

    res = create_goal_epic_and_task(
        goal_text="Build src/demo/index.html with a server entrypoint, "
                  "playwright test verifies localhost:5000 returns 200.",
        epic_id_hint="demo-loop",
        accept_vague=False,
    )
    assert res.epic_id == "demo-loop"

    verdict = {
        "satisfied": False, "gap_kind": "structural",
        "gap_description": "no server entrypoint exists",
        "iteration": 1, "recommended_next_action": "spawn-follow-up-task",
    }
    data = _load()
    epic = next(e for e in data["epics"] if e["id"] == "demo-loop")
    nxt = next_stage_after_judge(verdict, epic["goal"])
    assert nxt == "SPAWN_CHILD_TASK"
```

- [ ] **Step 2: Run**

```bash
cd plugins/taskmaster && python -m pytest tests/test_e2e_goal_smoke.py -v
```

Expected: 2 passing.

- [ ] **Step 3: Run the full test suite for the regression check**

```bash
cd plugins/taskmaster && python -m pytest -v
```

Expected: all green. If any pre-existing test is sensitive to the new `kind`
field or the modified `backlog_add_epic` signature, fix it (do not relax the
new tests).

- [ ] **Step 4: Commit**

```bash
git add plugins/taskmaster/tests/test_e2e_goal_smoke.py
git commit -m "test(taskmaster): e2e smoke for /goal happy path + structural-gap loop"
```

---

## Task 14: Track this work in the backlog (post-implementation hygiene)

**Files:**
- Modify: `.taskmaster/backlog.yaml`

- [ ] **Step 1: Add backlog tasks for follow-ups deferred during this work**

Use `backlog_add_task` for each, under a new epic `auto-brainstorm-goal`:

```python
# (Use the MCP tools, not raw YAML edits.)
backlog_add_epic("auto-brainstorm-goal", "Auto-brainstorm + /goal")

backlog_add_task(
    "auto-brainstorm-goal-001", "Wire goal-judge agent runner harness",
    epic="auto-brainstorm-goal",
    description="Currently test_goal_judge_agent.py skips agent dispatch — wire a runner using Claude Code SDK or similar so prompt regression actually executes.",
    priority="medium",
)

backlog_add_task(
    "auto-brainstorm-goal-002", "Tune /goal rubric heuristics from real traffic",
    epic="auto-brainstorm-goal",
    description="goal_rubric.py uses regex-based heuristics. After 5–10 real /goal runs, audit false-passes and false-rejects; expand keyword lists in goal_rubric.py.",
    priority="low",
)

backlog_add_task(
    "auto-brainstorm-goal-003", "Promote auto-brainstorm to dedicated subagent (v2)",
    epic="auto-brainstorm-goal",
    description="Currently auto-brainstorm runs as in-context skill. Once prompts stabilize (~10 real runs), extract to plugins/taskmaster/agents/auto-brainstormer.md.",
    priority="low",
)

backlog_add_task(
    "auto-brainstorm-goal-004", "Cross-domain research source default-on/off review",
    epic="auto-brainstorm-goal",
    description="Currently default-OFF except for design-heavy tasks. Review after 5+ real runs whether the default should flip.",
    priority="low",
)
```

- [ ] **Step 2: Verify**

```bash
# (use backlog_list_tasks or open the kanban viewer)
```

- [ ] **Step 3: No commit needed** — `.taskmaster/` is gitignored.

---

## Self-review (run after writing this plan)

**1. Spec coverage**
- ✅ Auto-brainstorm pipeline (research/draft/iterate/challenger) → Task 8
- ✅ /goal entry point + rubric validator → Tasks 1, 5, 7
- ✅ goal-judge subagent → Task 6
- ✅ Epic kind=goal + goal block → Tasks 2, 3
- ✅ GOAL_JUDGE state machine + iteration budgets → Task 10
- ✅ MCP changes (auto_status, update_epic) → Tasks 3, 4
- ✅ Viewer rendering → Task 12
- ✅ Router + start-session integration → Task 11
- ✅ End-to-end smoke → Task 13
- ✅ Backlog hygiene for known follow-ups → Task 14

**2. Placeholder scan**
- No "TBD" / "TODO" / "fill in" in the plan body.
- Code blocks are concrete; commands have expected outputs.
- `Task 9 Step 3` says "Read existing spec-review/SKILL.md" with intent rather than pasted diff — reasonable because the existing file content drives the exact diff. The Edit-based instruction is concrete enough.
- `Task 12 Step 1` says "find the function" — same shape, real diff depends on existing code structure.

**3. Type consistency**
- `RubricEval.severity()` returns `"pass" | "warn" | "reject"` — used consistently across `validate_goal_text`, `create_goal_epic_and_task`, and `auto_state.next_stage_after_judge` (which doesn't call severity directly but consumes the same vocabulary in `gap_kind`).
- `next_stage_after_judge` returns one of: `GOAL_DONE | IMPLEMENT | SPAWN_CHILD_TASK | HALT_BUDGET_EXHAUSTED`. These match the SKILL.md Step 9 routing (`GOAL_DONE`, `IMPLEMENT`, `SPAWN_CHILD_TASK`, `HALT_BUDGET_EXHAUSTED`).
- `verdict.recommended_next_action` enum (`done | loop-in-task | spawn-follow-up-task | halt-budget-exhausted`) — used as advisory, not as routing source-of-truth (auto_state recomputes from gap_kind + budgets, defensively).
- `epic["kind"]` value `"feature" | "goal"` — consistent across MCP, helpers, viewer, tests.

---

## Plan complete

Plan saved to `docs/superpowers/plans/2026-05-10-auto-brainstorm-goal.md`. Two execution options:

**1. Subagent-Driven (recommended)** — dispatch a fresh subagent per task with two-stage review between tasks. Each task is self-contained.

**2. Inline Execution** — run tasks in this session via `superpowers:executing-plans`, batched with checkpoints.

The user has asked to end the session before execution. Plan stays here for next time.
