# Plan E — Skill Slimming — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce every taskmaster SKILL.md to its token budget (≤800–1,500 tokens depending on skill) by extracting deep-walkthrough content into `references/` files, and trim every skill description to ≤60 words, halving the eager catalog from ~4,000 to ~2,000 tokens.

**Architecture:** Two independent lint layers. (1) A shared `skill_budget_helper.py` provides a `count_tokens(path)` function (chars ÷ 4 proxy, fast, no dep) and a `SKILL_BUDGETS` table. (2) Per-skill lint tests (`test_<skill>_skill_lint.py`) assert both body budget and description word count. Each skill is then restructured one-at-a-time: decision-tree content stays in SKILL.md, deep-walkthrough content moves to `references/<topic>.md`. Plan D owns `start-session` and `pick-task` body rewrites; Plan E provides only the lint-check tasks for those two.

**Tech Stack:** Markdown, Python 3.11+, pytest. No new pip deps — token proxy uses `len(text) // 4`.

**Spec:** `docs/superpowers/specs/2026-05-15-taskmaster-progressive-disclosure-design.md` §5

**Depends on:** None (parallel with A/B/C/D). Coordination with D: Plan E does NOT rewrite `start-session` or `pick-task` SKILL.md bodies — those are owned by Plan D. Plan E adds lint tests that those two skills must eventually satisfy; Plan D merges before those lint tests become hard-failures.

---

## File Structure

**Create:**
- `plugins/taskmaster/tests/skill_budget_helper.py` — shared token-budget utility
- `plugins/taskmaster/tests/test_skill_body_budgets.py` — one parametrized test covering all skill body budgets
- `plugins/taskmaster/tests/test_skill_description_budgets.py` — one parametrized test covering all description word counts

Per-skill lint tests (body + references structure, one file per skill — excludes existing handover/issue/lesson/auto-task/pick-task lint files, which are extended in-place):
- `plugins/taskmaster/tests/test_taskmaster_skill_lint.py`
- `plugins/taskmaster/tests/test_end_session_skill_lint.py`
- `plugins/taskmaster/tests/test_auto_epic_skill_lint.py`
- `plugins/taskmaster/tests/test_auto_phase_skill_lint.py`
- `plugins/taskmaster/tests/test_review_gate_skill_lint.py`
- `plugins/taskmaster/tests/test_spec_review_skill_lint.py`
- `plugins/taskmaster/tests/test_init_taskmaster_skill_lint.py`
- `plugins/taskmaster/tests/test_migrate_v3_skill_lint.py`
- `plugins/taskmaster/tests/test_check_todos_skill_lint.py`
- `plugins/taskmaster/tests/test_add_idea_skill_lint.py` *(extend existing)*

Per-skill `references/` content created during body-slimming tasks:
- `plugins/taskmaster/skills/taskmaster/references/routing-table.md`
- `plugins/taskmaster/skills/taskmaster/references/disambiguation.md`
- `plugins/taskmaster/skills/end-session/references/v3-pre-steps.md`
- `plugins/taskmaster/skills/end-session/references/summary-modes.md`
- `plugins/taskmaster/skills/end-session/references/edge-cases.md` *(extend existing)*
- `plugins/taskmaster/skills/auto-epic/references/loop-protocol.md`
- `plugins/taskmaster/skills/auto-epic/references/failure-recovery.md`
- `plugins/taskmaster/skills/auto-phase/references/loop-protocol.md`
- `plugins/taskmaster/skills/auto-phase/references/failure-aggregation.md`
- `plugins/taskmaster/skills/review-gate/references/gate-details.md`
- `plugins/taskmaster/skills/review-gate/references/codex-integration.md`
- `plugins/taskmaster/skills/review-gate/references/task-lifecycle.md` *(move existing inline content)*
- `plugins/taskmaster/skills/spec-review/references/adversarial-steps.md`
- `plugins/taskmaster/skills/spec-review/references/codex-integration.md`
- `plugins/taskmaster/skills/init-taskmaster/references/analysis-mode.md`
- `plugins/taskmaster/skills/migrate-v3/references/migration-steps.md`
- `plugins/taskmaster/skills/check-todos/references/scan-flow.md`
- `plugins/taskmaster/skills/add-idea/references/slash-form.md`
- `plugins/taskmaster/skills/lesson/references/write-flows.md` *(split from existing)*
- `plugins/taskmaster/skills/handover/references/triage.md` *(already exists — verify)*

**Modify (extend existing lint tests):**
- `plugins/taskmaster/tests/test_handover_skill_lint.py` — add body budget + description word-count assertions
- `plugins/taskmaster/tests/test_issue_skill_lint.py` — same
- `plugins/taskmaster/tests/test_lesson_skill_lint.py` — same
- `plugins/taskmaster/tests/test_migrate_v3_skill_lint.py` — same
- `plugins/taskmaster/tests/test_add_idea_skill_lint.py` — same

**Modify (SKILL.md rewrites — body slim + description trim):**
- `plugins/taskmaster/skills/taskmaster/SKILL.md`
- `plugins/taskmaster/skills/end-session/SKILL.md`
- `plugins/taskmaster/skills/auto-epic/SKILL.md`
- `plugins/taskmaster/skills/auto-phase/SKILL.md`
- `plugins/taskmaster/skills/review-gate/SKILL.md`
- `plugins/taskmaster/skills/spec-review/SKILL.md`
- `plugins/taskmaster/skills/init-taskmaster/SKILL.md`
- `plugins/taskmaster/skills/migrate-v3/SKILL.md`
- `plugins/taskmaster/skills/check-todos/SKILL.md`
- `plugins/taskmaster/skills/add-idea/SKILL.md`
- `plugins/taskmaster/skills/handover/SKILL.md` (description trim only — body already slimmed)
- `plugins/taskmaster/skills/issue/SKILL.md` (description trim only)
- `plugins/taskmaster/skills/lesson/SKILL.md` (description trim + body slim)
- `plugins/taskmaster/skills/auto-task/SKILL.md` (description trim only — body already lean)

---

## Phase 1 — Lint Infrastructure

### Task 1: Create shared token-budget helper and parametrized body-budget test

**Files:**
- Create: `plugins/taskmaster/tests/skill_budget_helper.py`
- Create: `plugins/taskmaster/tests/test_skill_body_budgets.py`

**Context:** The proxy `len(text) // 4` gives token estimates within ±15%. It's good enough to enforce a budget; a skill at 1,400 chars won't accidentally slip past a 1,500-token limit. Real tiktoken is not required.

- [ ] **Step 1: Create `skill_budget_helper.py`**

```python
# plugins/taskmaster/tests/skill_budget_helper.py
"""Shared helpers for skill token-budget lint tests."""
from pathlib import Path
import re

# Approximate tokens = chars ÷ 4 (within ±15% of tiktoken cl100k).
CHARS_PER_TOKEN = 4

# Budget table: (skill_name, body_token_budget)
# start-session and pick-task bodies are owned by Plan D; budgets listed here
# but their tests are marked xfail until Plan D merges.
SKILL_BUDGETS: dict[str, int] = {
    "taskmaster":     800,
    "start-session":  1_300,   # Plan D owns body — lint-check only
    "pick-task":      1_300,   # Plan D owns body — lint-check only
    "end-session":    1_500,
    "handover":       1_300,
    "issue":          1_300,
    "lesson":         1_300,
    "auto-task":      1_500,
    "review-gate":    1_200,
    "spec-review":    1_300,
    "auto-epic":      1_200,
    "auto-phase":     1_200,
    "init-taskmaster":1_200,
    "migrate-v3":     1_200,
    "check-todos":    1_200,
    "add-idea":       1_200,
}

SKILLS_ROOT = Path(__file__).resolve().parents[1] / "skills"

# Skills whose body budget is owned by Plan D — lint runs but is xfail until D merges.
PLAN_D_OWNED = {"start-session", "pick-task"}


def skill_md_path(skill_name: str) -> Path:
    return SKILLS_ROOT / skill_name / "SKILL.md"


def body_token_count(skill_name: str) -> int:
    """Return approximate token count for a skill's SKILL.md (full file)."""
    path = skill_md_path(skill_name)
    text = path.read_text(encoding="utf-8")
    return len(text) // CHARS_PER_TOKEN


def description_word_count(skill_name: str) -> int:
    """Return word count of the `description` frontmatter field."""
    path = skill_md_path(skill_name)
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return 0
    import yaml
    fm = yaml.safe_load(m.group(1)) or {}
    desc = fm.get("description", "")
    return len(desc.split())
```

- [ ] **Step 2: Write the failing parametrized body-budget test**

```python
# plugins/taskmaster/tests/test_skill_body_budgets.py
"""Parametrized token-budget enforcement for every taskmaster skill body."""
import pytest
from skill_budget_helper import (
    SKILL_BUDGETS,
    PLAN_D_OWNED,
    body_token_count,
    skill_md_path,
)


@pytest.mark.parametrize("skill,budget", SKILL_BUDGETS.items())
def test_skill_body_within_budget(skill, budget):
    """SKILL.md must be within token budget after slimming."""
    if skill in PLAN_D_OWNED:
        pytest.xfail(f"{skill} body is owned by Plan D — budget check pending merge")
    path = skill_md_path(skill)
    assert path.exists(), f"SKILL.md missing for skill '{skill}'"
    actual = body_token_count(skill)
    assert actual <= budget, (
        f"skill '{skill}' body is {actual} tokens (budget: {budget}). "
        f"Move deep-walkthrough content to references/<topic>.md."
    )
```

- [ ] **Step 3: Run test to verify it fails for the right reason**

Run: `pytest plugins/taskmaster/tests/test_skill_body_budgets.py -v`

Expected: Multiple FAIL with "skill '...' body is N tokens (budget: M)". Skills already at or below budget should PASS (verify `auto-task` at ~620 tokens passes).

### Task 2: Create parametrized description word-count test

**Files:**
- Create: `plugins/taskmaster/tests/test_skill_description_budgets.py`

The description word budget is 60 words for all skills. Existing skills are well over this; the test will fail on all of them until descriptions are rewritten.

- [ ] **Step 1: Write the failing test**

```python
# plugins/taskmaster/tests/test_skill_description_budgets.py
"""Description word-count enforcement: every skill description ≤ 60 words."""
import pytest
from skill_budget_helper import SKILL_BUDGETS, description_word_count, skill_md_path

DESCRIPTION_WORD_BUDGET = 60


@pytest.mark.parametrize("skill", SKILL_BUDGETS.keys())
def test_skill_description_within_budget(skill):
    """frontmatter description must be ≤60 words."""
    path = skill_md_path(skill)
    assert path.exists(), f"SKILL.md missing for '{skill}'"
    count = description_word_count(skill)
    assert count <= DESCRIPTION_WORD_BUDGET, (
        f"skill '{skill}' description is {count} words (budget: {DESCRIPTION_WORD_BUDGET}). "
        f"Trim to: 1 sentence what-it-does, 1 sentence triggers, 1 sentence hard rule."
    )
```

- [ ] **Step 2: Run test to verify it fails for the right reason**

Run: `pytest plugins/taskmaster/tests/test_skill_description_budgets.py -v`

Expected: All 16 skills FAIL — current descriptions are 40–100 words each.

### Task 3: Add body-budget + description assertions to existing lint tests

**Files:**
- Modify: `plugins/taskmaster/tests/test_handover_skill_lint.py`
- Modify: `plugins/taskmaster/tests/test_issue_skill_lint.py`
- Modify: `plugins/taskmaster/tests/test_lesson_skill_lint.py`
- Modify: `plugins/taskmaster/tests/test_migrate_v3_skill_lint.py`
- Modify: `plugins/taskmaster/tests/test_add_idea_skill_lint.py`

Add these two functions to each existing lint file (replacing `SKILL_NAME` with the actual skill):

```python
from skill_budget_helper import body_token_count, description_word_count, SKILL_BUDGETS

def test_skill_body_within_budget():
    budget = SKILL_BUDGETS["SKILL_NAME"]
    actual = body_token_count("SKILL_NAME")
    assert actual <= budget, (
        f"body is {actual} tokens (budget: {budget}) — move deep content to references/"
    )

def test_description_within_word_budget():
    count = description_word_count("SKILL_NAME")
    assert count <= 60, f"description is {count} words (budget: 60)"
```

- [ ] **Step 1: Add assertions to `test_handover_skill_lint.py`** (budget: 1,300)
- [ ] **Step 2: Add assertions to `test_issue_skill_lint.py`** (budget: 1,300)
- [ ] **Step 3: Add assertions to `test_lesson_skill_lint.py`** (budget: 1,300)
- [ ] **Step 4: Add assertions to `test_migrate_v3_skill_lint.py`** (budget: 1,200)
- [ ] **Step 5: Add assertions to `test_add_idea_skill_lint.py`** (budget: 1,200)
- [ ] **Step 6: Run all five modified tests to confirm they now fail on the budget assertions**

Run: `pytest plugins/taskmaster/tests/test_handover_skill_lint.py plugins/taskmaster/tests/test_issue_skill_lint.py plugins/taskmaster/tests/test_lesson_skill_lint.py plugins/taskmaster/tests/test_migrate_v3_skill_lint.py plugins/taskmaster/tests/test_add_idea_skill_lint.py -v`

Expected: Previously-passing tests still pass; new budget/word-count assertions fail.

---

## Phase 2 — Skill Body Slimming (one task per skill)

> **Pattern for each task:** (1) Write or confirm the failing body-budget lint. (2) Identify "decision tree" content — keep in SKILL.md. (3) Identify "deep walkthrough" content — move to `references/<topic>.md`. (4) Replace moved content with a pointer line. (5) Verify the lint passes. (6) Commit.
>
> **Do NOT touch `start-session` or `pick-task` bodies** — those are owned by Plan D.

### Task 4: Slim `taskmaster` router (2,277 → 800 tokens)

**Files:**
- Modify: `plugins/taskmaster/skills/taskmaster/SKILL.md`
- Create: `plugins/taskmaster/skills/taskmaster/references/routing-table.md`
- Create: `plugins/taskmaster/skills/taskmaster/references/disambiguation.md`
- Create: `plugins/taskmaster/tests/test_taskmaster_skill_lint.py`

**What to keep in SKILL.md (~800 tokens):**
- Frontmatter
- One-paragraph purpose ("All work in a taskmaster-enabled project …")
- Condensed routing table — keep two columns (Intent Signal → Route To) but reduce to ~20 rows covering the highest-frequency intents only
- "Do NOT Route" section (2 bullets)
- "When Multiple Intents Match" (1 bullet)
- Pointer: "For the full routing table, disambiguation of similar intents, and implementation-without-a-task guidance, see `references/routing-table.md` and `references/disambiguation.md`."

**What moves to `references/routing-table.md`:**
- Full 30+ row routing table (all v3 routes, less-common intents)
- "Implementation Work Without a Task" decision tree

**What moves to `references/disambiguation.md`:**
- "v3 disambiguation" section (handover vs end-session, issue vs task, lesson vs note, recap vs last_session, auto-task vs pick-task)

- [ ] **Step 1: Write the failing lint test**

```python
# plugins/taskmaster/tests/test_taskmaster_skill_lint.py
"""Lint checks for the taskmaster:taskmaster router skill."""
from pathlib import Path
import re
import yaml
from skill_budget_helper import body_token_count, description_word_count

SKILL_DIR = Path(__file__).resolve().parents[1] / "skills" / "taskmaster"


def _read_frontmatter() -> dict:
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    return yaml.safe_load(m.group(1)) or {} if m else {}


def test_skill_md_exists():
    assert (SKILL_DIR / "SKILL.md").exists()


def test_frontmatter_required_fields():
    fm = _read_frontmatter()
    assert fm.get("name") == "taskmaster"
    assert "description" in fm and isinstance(fm["description"], str)


def test_body_within_budget():
    actual = body_token_count("taskmaster")
    assert actual <= 800, f"body is {actual} tokens (budget: 800)"


def test_description_within_word_budget():
    count = description_word_count("taskmaster")
    assert count <= 60, f"description is {count} words (budget: 60)"


def test_references_exist():
    for ref in ("routing-table.md", "disambiguation.md"):
        assert (SKILL_DIR / "references" / ref).exists(), f"missing references/{ref}"


def test_references_not_stubs():
    for ref in (SKILL_DIR / "references").iterdir():
        non_blank = [ln for ln in ref.read_text(encoding="utf-8").splitlines() if ln.strip()]
        assert len(non_blank) > 20, f"reference looks like stub: {ref}"


def test_skill_md_links_resolve():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    refs = re.findall(r"`(references/[A-Za-z0-9_-]+\.md)`", text)
    assert refs, "SKILL.md must reference at least one references/ file"
    missing = [r for r in refs if not (SKILL_DIR / r).exists()]
    assert not missing, f"unresolved links: {missing}"


def test_description_contains_key_trigger_phrases():
    fm = _read_frontmatter()
    desc = fm["description"].lower()
    must_have = ["backlog.yaml", "route", "taskmaster"]
    missing = [p for p in must_have if p not in desc]
    assert not missing, f"description missing trigger phrases: {missing}"
```

- [ ] **Step 2: Run lint to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_taskmaster_skill_lint.py -v`
Expected: `test_body_within_budget` FAIL (current: ~570 tokens, but let's confirm), `test_references_exist` FAIL, `test_skill_md_links_resolve` FAIL.

- [ ] **Step 3: Create `references/routing-table.md`**

Move the full 30+ row routing table from SKILL.md here. Format as a complete Markdown document:

```markdown
# Taskmaster Router — Full Routing Table

This file contains the complete intent→skill routing table for `taskmaster:taskmaster`.
The SKILL.md body carries only the ~20 highest-frequency rows.

## All Routes

| Intent Signal | Route To |
|---|---|
| Starting a new conversation, "what's going on", "orient me", "show the backlog", "let's get started" | `taskmaster:start-session` |
| "Pick task X", "let's work on X", "what should I tackle", names a task ID, "start task" | `taskmaster:pick-task` |
| Any implementation request when a task is in-progress | Work in the current task's worktree — no routing needed |
| Any implementation request when NO task is in-progress | `taskmaster:pick-task` first |
| "Review this spec", "challenge this design", "is this the right approach?", "spec review" | `taskmaster:spec-review` |
| "Is this ready?", "run the review", "check my work", "quality check" | `taskmaster:review-gate` |
| "End session", "I'm done", "wrap up", "log this", "mark task done", "save progress" | `taskmaster:end-session` |
| "Set up taskmaster", "initialize", "create backlog", first time without backlog.yaml | `taskmaster:init-taskmaster` |
| "Add a task", "create a task for X", "plan out this epic" | `backlog_add_task` / `backlog_add_epic` |
| "Show task X", "task details", "what's the status of X" | `backlog_get_task` / `backlog_status` |
| "Search for X", "find tasks about X" | `backlog_search` |
| "Create a phase", "plan the next phase" | `backlog_add_phase` |
| "Show phase progress", "where are we in the phase?" | `backlog_phase_status` |
| "Advance to next phase", "this phase is done" | `backlog_advance_phase` |
| "Check TODOs", "scan for TODOs", "todo audit" | `taskmaster:check-todos` |
| (v3) "Write a handover", "wrap up for tomorrow", "context handoff", "save where I left off", "for tomorrow", "remind future me", "before compaction" | `taskmaster:handover` |
| (v3) "Show last handover", "where did I leave off" | `backlog_handover_latest` |
| (v3) "List handovers", "recent handovers" | `backlog_handover_list` |
| (v3) "Log a bug", "found an issue", "this is broken", "track this defect" | `taskmaster:issue` |
| (v3) "List issues", "open bugs", "what's broken" | `backlog_issue_list(status=open)` |
| (v3) "Mark issue fixed", "close ISS-XX", "triage bugs" | `taskmaster:issue` |
| (v3) "Remember this", "save as a lesson", "memorize this", "we got burned by this" | `taskmaster:lesson` |
| (v3) "Show lessons", "lesson digest" | `backlog_lesson_digest` / `backlog_lesson_match` |
| (v3) "Save this as an idea", "/add-idea" | `taskmaster:add-idea` |
| (v3) "List ideas", "show parking lot" | `backlog_idea_list` |
| (v3) "Archive that idea", "promote idea to task" | `backlog_idea_update` |
| (v3) "What changed since last time", "recap", "project state delta" | `backlog_recap` |
| (v3) "Snapshot the backlog" | `backlog_snapshot` |
| (v3) "Auto this task", "autopilot T-001", "run task auto" | `taskmaster:auto-task` |
| (v3) "Auto-epic <id>", "run the whole epic" | `taskmaster:auto-epic` |
| (v3) "Auto-phase <id>", "run all of phase X" | `taskmaster:auto-phase` |
| (v3) "Upgrade to v3", "migrate to v3", "enable narrative continuity" | `taskmaster:migrate-v3` |

## Implementation Work Without a Task

If the user asks to implement something and there's no task for it yet:

1. Call `backlog_status` to check what's in-progress.
2. If the work fits an existing task, pick that task.
3. If not, suggest creating a new task: "This looks like new work. Want me to add a task for it under epic X?"
4. Once a task is picked, work proceeds in its worktree.

This ensures nothing falls through the cracks.
```

- [ ] **Step 4: Create `references/disambiguation.md`**

Move the "v3 disambiguation" section from SKILL.md here:

```markdown
# Taskmaster Router — Disambiguation Guide

When two routes could both fire, pick correctly:

## handover vs end-session

- **end-session** is a task transition — status → done/in-review with changelog. Route there when user says "wrap up" (end-session itself offers handover write).
- **handover** is a narrative continuity artifact — can be written without ending a task. Route directly to `taskmaster:handover` when user says "context handoff" or "for tomorrow".

## issue vs task

- **issue** = a bug record (`taskmaster:issue`). "Track this bug."
- **task** = a unit of work (`backlog_add_task`). "Add a task to fix this bug."
- Both can coexist for the same defect.

## lesson vs note

- **Task notes** — scratch space for one task. "Note this for the task."
- **Lesson** — project-wide guidance. "Remember this for next time you touch auth." → `taskmaster:lesson`.

## recap vs last_session

- **last_session** — what *you* did.
- **recap** — what changed in the *project state* (any source). At session start, both render — they're complementary.

## auto-task vs pick-task

- **pick-task** — interactive; user drives every step.
- **auto-task** — state-machine; hands-off / scripted batch work.
```

- [ ] **Step 5: Rewrite `plugins/taskmaster/skills/taskmaster/SKILL.md`**

```markdown
---
name: taskmaster
description: "Universal work router for any project with backlog.yaml. Invoke for implementing features, fixing bugs, writing tests, refactoring, planning epics, or any narrative-continuity operation (handovers, issues, lessons, auto-mode). The only exceptions are pure git commits and dedicated PR security reviews."
---

# Taskmaster Router

All work in a taskmaster-enabled project flows through the task system. This skill detects what the user wants and routes to the right sub-skill or MCP tool.

## Intent Detection

| Intent Signal | Route To |
|---|---|
| "Let's get started", "orient me", "show the backlog" | `taskmaster:start-session` |
| "Pick task X", names a task ID, "what should I work on" | `taskmaster:pick-task` |
| Implementation request, in-progress task exists | Work in current task's worktree |
| Implementation request, no in-progress task | `taskmaster:pick-task` first |
| "Review this spec", "challenge this design" | `taskmaster:spec-review` |
| "Is this ready?", "check my work", "review gate" | `taskmaster:review-gate` |
| "End session", "wrap up", "mark task done" | `taskmaster:end-session` |
| "Set up taskmaster", "initialize backlog" | `taskmaster:init-taskmaster` |
| "Write a handover", "context handoff", "for tomorrow" | `taskmaster:handover` |
| "Log a bug", "this is broken", "track this defect" | `taskmaster:issue` |
| "Remember this", "save as a lesson" | `taskmaster:lesson` |
| "Save this as an idea", "/add-idea" | `taskmaster:add-idea` |
| "Auto this task", "autopilot T-001" | `taskmaster:auto-task` |
| "Auto-epic <id>", "auto-phase <id>" | `taskmaster:auto-epic` / `taskmaster:auto-phase` |
| "Upgrade to v3", "migrate to v3" | `taskmaster:migrate-v3` |
| "Check TODOs", "todo audit" | `taskmaster:check-todos` |
| Status, search, phase, recap, snapshot | Direct `backlog_*` tool call |

For the full 30-row routing table, all v3 routes, and implementation-without-a-task guidance, read `references/routing-table.md`.

## Do NOT Route Through Taskmaster

- Pure git operations (commit, push, branch) — git directly
- PR security reviews — dedicated review tools

## When Multiple Intents Match

Handle sequentially — complete the first action before starting the second.

## When to Deepen

When routes are ambiguous (handover vs end-session, issue vs task, lesson vs note, auto-task vs pick-task), read `references/disambiguation.md`.
```

- [ ] **Step 6: Run lint test — verify all assertions pass**

Run: `pytest plugins/taskmaster/tests/test_taskmaster_skill_lint.py -v`
Expected: All pass.

- [ ] **Step 7: Commit**

```
git add plugins/taskmaster/skills/taskmaster/ plugins/taskmaster/tests/test_taskmaster_skill_lint.py
git commit -m "refactor(skill): slim taskmaster router to 800-token budget"
```

### Task 5: Slim `end-session` (3,788 → 1,500 tokens)

**Files:**
- Modify: `plugins/taskmaster/skills/end-session/SKILL.md`
- Create: `plugins/taskmaster/skills/end-session/references/v3-pre-steps.md`
- Create: `plugins/taskmaster/skills/end-session/references/summary-modes.md`
- Create: `plugins/taskmaster/tests/test_end_session_skill_lint.py`

**What to keep in SKILL.md (~1,500 tokens):**
- Frontmatter
- "Why This Skill Exists" (2 sentences)
- v3 pre-steps — **headlines only** with pointer to `references/v3-pre-steps.md`:
  - v3-pre-1: Snapshot (1 line)
  - v3-pre-2a: Lesson candidate sweep (2 lines + pointer)
  - v3-pre-2: Handover auto-write (2 lines + pointer)
  - v3-pre-2b: Handover archive sweep (1 line)
  - v3-pre-2c: Idea-candidate sweep (1 line)
- Existing flow (condensed to ~8 steps, each 1-2 lines)
- "Task Lifecycle" (2 lines)
- "Additional Resources" (2 bullets)

**What moves to `references/v3-pre-steps.md`:**
- Full v3-pre-2a prose (lesson candidate sweep — auto-offer conditions, input sources, per-candidate options, multi-select flow, retirement signal)
- Full v3-pre-2 handover auto-write prose (trigger conditions, session_kind inference table, invoke pattern, opt-out rule)
- Full v3-pre-2c idea-candidate sweep prose (parse-and-commit loop, tally, report format)

**What moves to `references/summary-modes.md`:**
- Full Step 0 "Determine summary mode" prose (session weight logic, light vs substantial criteria, auto vs structured decision)
- Step 2 patchnote draft instructions and examples
- Step 4 target-status decision rules and override conditions

- [ ] **Step 1: Write the failing lint test**

```python
# plugins/taskmaster/tests/test_end_session_skill_lint.py
"""Lint checks for the taskmaster:end-session skill."""
from pathlib import Path
import re
import yaml
from skill_budget_helper import body_token_count, description_word_count

SKILL_DIR = Path(__file__).resolve().parents[1] / "skills" / "end-session"


def _read_frontmatter() -> dict:
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    return yaml.safe_load(m.group(1)) or {} if m else {}


def test_skill_md_exists():
    assert (SKILL_DIR / "SKILL.md").exists()


def test_frontmatter_required_fields():
    fm = _read_frontmatter()
    assert fm.get("name") == "end-session"
    assert "description" in fm


def test_body_within_budget():
    actual = body_token_count("end-session")
    assert actual <= 1_500, f"body is {actual} tokens (budget: 1500)"


def test_description_within_word_budget():
    count = description_word_count("end-session")
    assert count <= 60, f"description is {count} words (budget: 60)"


def test_description_contains_key_trigger_phrases():
    fm = _read_frontmatter()
    desc = fm["description"].lower()
    must_have = ["end session", "wrap up", "mark this task done", "save progress"]
    missing = [p for p in must_have if p not in desc]
    assert not missing, f"description missing: {missing}"


def test_references_exist():
    for ref in ("v3-pre-steps.md", "summary-modes.md"):
        assert (SKILL_DIR / "references" / ref).exists(), f"missing references/{ref}"


def test_references_not_stubs():
    for ref in (SKILL_DIR / "references").iterdir():
        non_blank = [ln for ln in ref.read_text(encoding="utf-8").splitlines() if ln.strip()]
        assert len(non_blank) > 20, f"reference stub: {ref}"


def test_skill_md_links_resolve():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    refs = re.findall(r"`(references/[A-Za-z0-9_-]+\.md)`", text)
    assert refs, "SKILL.md must reference at least one references/ file"
    missing = [r for r in refs if not (SKILL_DIR / r).exists()]
    assert not missing, f"unresolved: {missing}"


def test_skill_md_contains_canonical_sentence():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    assert "ONLY" in text and "backlog_complete_task" in text, (
        "Missing canonical 'ONLY correct way' sentence"
    )
```

- [ ] **Step 2: Run to confirm failure**

Run: `pytest plugins/taskmaster/tests/test_end_session_skill_lint.py -v`
Expected: `test_body_within_budget` FAIL (~947 tokens), `test_references_exist` FAIL, `test_description_within_word_budget` FAIL.

- [ ] **Step 3: Create `references/v3-pre-steps.md`**

Move the full v3-pre-2a, v3-pre-2, and v3-pre-2c prose blocks from SKILL.md here (verbatim — do not trim the detail, only relocate it). Add a header:

```markdown
# End-Session — v3 Pre-Steps Detail

Read this file when any v3 pre-step condition fires. The SKILL.md body carries
only the headline and condition; the full flow is here.

## v3-pre-2a: Lesson Candidate Sweep

[... full prose from SKILL.md ...]

## v3-pre-2: Handover Auto-Write

[... full prose including trigger conditions, session_kind table, invoke pattern ...]

## v3-pre-2c: Idea-Candidate Sweep

[... full prose including parse loop, tally format, commit rule ...]
```

- [ ] **Step 4: Create `references/summary-modes.md`**

Move Step 0 ("Determine summary mode"), Step 2 (patchnote draft), and Step 4 (target status decision) prose blocks here:

```markdown
# End-Session — Summary Modes and Status Decision

## Step 0: Determine Summary Mode

[... full prose on light vs substantial, auto vs structured ...]

## Step 2: Draft Patchnote

[... full prose with examples ...]

## Step 4: Target Status Decision

[... full decision rules and override conditions ...]
```

- [ ] **Step 5: Rewrite `end-session/SKILL.md`** to ≤1,500 tokens

Keep: Why section, v3-pre-step headlines with pointers, condensed 9-step existing flow, Task Lifecycle, Additional Resources. Example body shape:

```markdown
---
name: end-session
description: "Close out a work session. Invoke when the user says 'end session', 'I'm done for today', 'let's wrap up', 'mark this task done', or 'save progress'. Transitions task status, commits tracking files. This is the ONLY correct way to mark tasks done or in-review with a session record."
---

# End Session

Log the current work session, transition tasks, and commit tracking files.

## Why This Skill Exists

`backlog_complete_task` atomically writes the changelog entry AND transitions the task status. Calling `backlog_update_task` directly to set status to "done" leaves PROGRESS.md silent. This is the ONLY correct way to mark tasks done or in-review with backlog_complete_task.

## Steps

### v3 Pre-Steps (skip on v2)

Check schema: `backlog_status` → first line shows `Schema: v<N>`.

**v3-pre-1: Snapshot.** `backlog_snapshot(quiet=true)`.

**v3-pre-2a: Lesson candidate sweep.** Auto-offer when: `<lesson-candidate>` tags visible, or `backlog_lesson_candidates_list` returns entries, or 2+ feedback-memory entries for this project. Full flow: `references/v3-pre-steps.md`.

**v3-pre-2: Handover auto-write.** Write automatically (no prompt) when: session >60 turns, context >200k tokens, task still in-flight, or user said "for tomorrow" / "context handoff". Infer `session_kind` and invoke `taskmaster:handover`. Full flow: `references/v3-pre-steps.md`.

**v3-pre-2b: Handover archive sweep.** `backlog_handover_resync()` quietly.

**v3-pre-2c: Idea-candidate sweep.** Scan for `<idea-candidate>` tags; commit each via `backlog_idea_create`. Full flow: `references/v3-pre-steps.md`.

### Existing Flow

**0. Summary mode.** Light session (1-2 commits, single-topic) → auto-summary. Substantial (3+ commits) → structured. See `references/summary-modes.md`.

**1. Auto-generate summary.** Done / Decisions / Issues / Tasks touched from conversation context.

**2. Patchnote (optional).** 1-2 sentences for user-visible changes. Skip for internal tasks. See `references/summary-modes.md`.

**3. Session title.** `{Topic}: {Brief Description}`.

**4. Target status.** Default `in-review`. Override to `done` when: user confirmed testing, pure infra task, or user says "mark done". See `references/summary-modes.md`.

**5. Skip review gate.** Call `backlog_complete_task` directly. Only ask on genuine ambiguity.

**6. Call `backlog_complete_task`** with all session fields (task_id, session_title, done, decisions, issues, tasks_touched, target_status, patchnote, release).

**v3-post-complete-1.** For each `related_issues` that is open/investigating: ask user "Close as fixed or leave for follow-up?"

**7. Worktree cleanup (done tasks only).** Offer `git worktree remove .worktrees/{task_id}`. Skip for in-review.

**8. Commit tracking files.** Stage backlog.yaml, PROGRESS.md, .taskmaster/handovers/, issues/, lessons/, tasks/. Commit with `chore: log session — {topic}`.

**9. Confirm.** "Session logged. Task is now `{target_status}`."

## Task Lifecycle

`todo → in-progress → in-review → done → archived`. In-review = Claude done, user tests. Done = user confirmed.

## Additional Resources

- `references/v3-pre-steps.md` — full v3 pre-step flows (lesson sweep, handover auto-write, idea sweep).
- `references/summary-modes.md` — light vs structured mode, patchnote format, status decision rules.
- `references/edge-cases.md` — no in-progress task, not in git repo, multiple tasks changed.
- `references/auto-mode.md` — behavior when `backlog_auto_status` reports an active run.
```

- [ ] **Step 6: Run lint — verify all pass**

Run: `pytest plugins/taskmaster/tests/test_end_session_skill_lint.py -v`

- [ ] **Step 7: Commit**

```
git add plugins/taskmaster/skills/end-session/ plugins/taskmaster/tests/test_end_session_skill_lint.py
git commit -m "refactor(skill): slim end-session to 1500-token budget"
```

### Task 6: Slim `lesson` (2,799 → 1,300 tokens)

**Files:**
- Modify: `plugins/taskmaster/skills/lesson/SKILL.md`
- Create: `plugins/taskmaster/skills/lesson/references/write-flows.md`
- Modify: `plugins/taskmaster/tests/test_lesson_skill_lint.py` (ensure `test_references_exist` checks new file)

**What to keep in SKILL.md (~1,300 tokens):**
- Frontmatter + purpose paragraph
- "Why this skill exists" (3 sentences)
- "When to invoke" — five entry points as 5 bullets (1 line each)
- Decision tree (which entry point → which subflow, ~8 rows)
- Key rules (mid-session emit `<lesson-candidate>` tags; never call `backlog_lesson_create` directly)
- "Additional Resources" with pointer to `references/write-flows.md`

**What moves to `references/write-flows.md`:**
- Full per-entry-point subflows (write-from-context, write-from-candidate, reinforce-immediate, promote-candidate, session-sweep)
- Tier selection logic (currently in `references/` already — keep there)
- Mid-session candidate buffering protocol details

- [ ] **Step 1: Confirm body-budget assertion in `test_lesson_skill_lint.py` already fails** (from Task 3)

Run: `pytest plugins/taskmaster/tests/test_lesson_skill_lint.py::test_skill_body_within_budget -v`
Expected: FAIL.

- [ ] **Step 2: Create `references/write-flows.md`**

Extract the full subflow prose for all five entry points from SKILL.md body and write here. Keep the existing `references/reinforce-flows.md`, `references/promotion-decay.md`, etc. untouched.

- [ ] **Step 3: Rewrite `lesson/SKILL.md`** to ≤1,300 tokens with pointers to `references/write-flows.md` and existing reference files.

- [ ] **Step 4: Verify `test_lesson_skill_lint.py` — all pass**

Run: `pytest plugins/taskmaster/tests/test_lesson_skill_lint.py -v`

- [ ] **Step 5: Commit**

```
git add plugins/taskmaster/skills/lesson/ plugins/taskmaster/tests/test_lesson_skill_lint.py
git commit -m "refactor(skill): slim lesson to 1300-token budget"
```

### Task 7: Slim `handover` (2,487 → 1,300 tokens)

**Files:**
- Modify: `plugins/taskmaster/skills/handover/SKILL.md`
- Existing `references/` files: session-kinds.md, tier-selection.md, auto-extraction.md, supersession.md, triage.md — all stay; no new ones needed.
- Modify: `plugins/taskmaster/tests/test_handover_skill_lint.py` (body budget now fails)

**What to keep in SKILL.md (~1,300 tokens):**
- Frontmatter
- "Why this skill exists" (3 lines)
- "When to invoke" — three trigger contexts (1 line each)
- Steps 1–5 condensed to ~2 lines each with pointers to `references/` for detail
- "Notes" / hard rules

**What stays in existing references:**
- `references/session-kinds.md` — session_kind values (already there)
- `references/tier-selection.md` — tier selection (already there)
- `references/auto-extraction.md` — auto-extraction (already there)
- `references/supersession.md` — supersession protocol (already there)

The body slim here is mostly compressing the step prose — each step currently runs 4-8 lines; reduce to 1-2 lines with an explicit pointer to the relevant reference file.

- [ ] **Step 1: Confirm body-budget assertion already fails** (from Task 3)
- [ ] **Step 2: Rewrite `handover/SKILL.md`** condensing each step to 1-2 lines + pointers.
- [ ] **Step 3: Verify `test_handover_skill_lint.py` — all pass**
- [ ] **Step 4: Commit**

```
git add plugins/taskmaster/skills/handover/SKILL.md plugins/taskmaster/tests/test_handover_skill_lint.py
git commit -m "refactor(skill): slim handover to 1300-token budget"
```

### Task 8: Slim `issue` (2,510 → 1,300 tokens)

**Files:**
- Modify: `plugins/taskmaster/skills/issue/SKILL.md`
- Existing `references/severity-heuristics.md`, `references/lifecycle.md`, `references/auto-extraction.md`, `templates/issue-body.md` — stay.
- Create: `plugins/taskmaster/skills/issue/references/entry-point-flows.md`
- Modify: `plugins/taskmaster/tests/test_issue_skill_lint.py` (add `entry-point-flows.md` to `test_all_referenced_files_exist`)

**What to keep in SKILL.md (~1,300 tokens):**
- Frontmatter + "Why this skill exists"
- "When to invoke" — five entry points (1 line each)
- Severity quick-reference table (already compact)
- Entry-point decision tree (~5 rows)
- Pointer: "Full per-entry-point flows in `references/entry-point-flows.md`."

**What moves to `references/entry-point-flows.md`:**
- Full log-issue subflow prose
- Full flag-from-conversation subflow
- Full update-status subflow
- Full close-on-task-complete subflow
- Full triage-review subflow

- [ ] **Step 1: Confirm body-budget assertion already fails**
- [ ] **Step 2: Create `references/entry-point-flows.md`** with all five subflows moved from SKILL.md
- [ ] **Step 3: Rewrite `issue/SKILL.md`** to ≤1,300 tokens
- [ ] **Step 4: Update `test_issue_skill_lint.py`** to include `entry-point-flows.md` in `test_all_referenced_files_exist`
- [ ] **Step 5: Verify all pass**
- [ ] **Step 6: Commit**

```
git add plugins/taskmaster/skills/issue/ plugins/taskmaster/tests/test_issue_skill_lint.py
git commit -m "refactor(skill): slim issue to 1300-token budget"
```

### Task 9: Slim `review-gate` (2,281 → 1,200 tokens)

**Files:**
- Modify: `plugins/taskmaster/skills/review-gate/SKILL.md`
- Create: `plugins/taskmaster/skills/review-gate/references/gate-details.md`
- Create: `plugins/taskmaster/skills/review-gate/references/codex-integration.md`
- Create: `plugins/taskmaster/tests/test_review_gate_skill_lint.py`

**What to keep in SKILL.md (~1,200 tokens):**
- Frontmatter
- One-paragraph purpose (lead-with-verdict, code vs spec distinction)
- Arguments section (2 bullets: task_id, --codex flag)
- Condensed steps table:

  | Step | What |
  |---|---|
  | 1 | `backlog_get_task` — priority, branch, docs, review_instructions |
  | 2 | Gate 1: Spec/Plan Check (critical/high only) |
  | 3 | Gate 2a: Claude code review |
  | 4 | Gate 2b: Codex pass (opt-in) — see `references/codex-integration.md` |
  | 5 | Gate 2c: Spec adherence (critical/high with spec) |
  | 6 | Gate 3: Tests + Build (auto-detect runner) |
  | 7 | Present results — lead with verdict, gate matrix |
  | 8 | Add review_instructions if absent |
  | 9 | Transition to `in-review` |

- Blocking rules (3 bullets: critical/important/minor)
- Pointer: "Test runner detection, build detection, Codex Case A/B framing, and result format in `references/gate-details.md`."
- "Related Reviewers" (3 bullets — keep, they prevent misrouting)

**What moves to `references/gate-details.md`:**
- Full test-runner auto-detection list (Node/Python/.NET/Rust/Go)
- Full build-command auto-detection list
- Gate 2a review dispatch detail (worktree path resolution, branch determination, fallback)
- Gate 2c spec-adherence prose (3-sentence check format)
- Gate 3 review_instructions display format
- Full gate-matrix display format

**What moves to `references/codex-integration.md`:**
- Gate 2b full prose: Codex detection, Case A (standard precision) and Case B (repeated-bug verification), focus-arg construction, tagging `(codex)` findings

- [ ] **Step 1: Write the failing lint test**

```python
# plugins/taskmaster/tests/test_review_gate_skill_lint.py
"""Lint checks for the taskmaster:review-gate skill."""
from pathlib import Path
import re
import yaml
from skill_budget_helper import body_token_count, description_word_count

SKILL_DIR = Path(__file__).resolve().parents[1] / "skills" / "review-gate"


def _read_frontmatter() -> dict:
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    return yaml.safe_load(m.group(1)) or {} if m else {}


def test_skill_md_exists():
    assert (SKILL_DIR / "SKILL.md").exists()


def test_frontmatter_required_fields():
    fm = _read_frontmatter()
    assert fm.get("name") == "review-gate"
    assert "description" in fm


def test_body_within_budget():
    actual = body_token_count("review-gate")
    assert actual <= 1_200, f"body is {actual} tokens (budget: 1200)"


def test_description_within_word_budget():
    count = description_word_count("review-gate")
    assert count <= 60, f"description is {count} words (budget: 60)"


def test_description_contains_key_trigger_phrases():
    fm = _read_frontmatter()
    desc = fm["description"].lower()
    must_have = ["is this ready", "check my work", "review gate"]
    missing = [p for p in must_have if p not in desc]
    assert not missing, f"description missing: {missing}"


def test_description_distinguishes_from_spec_review():
    fm = _read_frontmatter()
    desc = fm["description"].lower()
    # Must distinguish this skill from spec-review
    assert "implementation" in desc or "code" in desc, (
        "description must clarify this reviews implementation, not spec"
    )


def test_references_exist():
    for ref in ("gate-details.md", "codex-integration.md"):
        assert (SKILL_DIR / "references" / ref).exists(), f"missing references/{ref}"


def test_references_not_stubs():
    for ref in (SKILL_DIR / "references").iterdir():
        non_blank = [ln for ln in ref.read_text(encoding="utf-8").splitlines() if ln.strip()]
        assert len(non_blank) > 20, f"reference stub: {ref}"


def test_skill_md_links_resolve():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    refs = re.findall(r"`(references/[A-Za-z0-9_-]+\.md)`", text)
    assert refs, "SKILL.md must reference at least one references/ file"
    missing = [r for r in refs if not (SKILL_DIR / r).exists()]
    assert not missing, f"unresolved: {missing}"
```

- [ ] **Step 2: Run to confirm failure**
- [ ] **Step 3: Create `references/gate-details.md`** with runner detection, gate formats
- [ ] **Step 4: Create `references/codex-integration.md`** with Gate 2b full prose
- [ ] **Step 5: Rewrite `review-gate/SKILL.md`** to ≤1,200 tokens using condensed step table
- [ ] **Step 6: Verify all pass**
- [ ] **Step 7: Commit**

```
git add plugins/taskmaster/skills/review-gate/ plugins/taskmaster/tests/test_review_gate_skill_lint.py
git commit -m "refactor(skill): slim review-gate to 1200-token budget"
```

### Task 10: Slim `spec-review` (2,553 → 1,300 tokens)

**Files:**
- Modify: `plugins/taskmaster/skills/spec-review/SKILL.md`
- Create: `plugins/taskmaster/skills/spec-review/references/adversarial-steps.md`
- Create: `plugins/taskmaster/skills/spec-review/references/codex-integration.md`
- Create: `plugins/taskmaster/tests/test_spec_review_skill_lint.py`

**What to keep in SKILL.md (~1,300 tokens):**
- Frontmatter
- Purpose (adversarial, pre-impl, not code)
- Arguments (task_id, --codex)
- "When This Should Run" — lifecycle position + 3 conditions (compact)
- Condensed steps 1–8 (~1-2 lines each) with pointers
- "Additional Resources" pointing to `references/adversarial-steps.md`

**What moves to `references/adversarial-steps.md`:**
- Steps 2–6 full prose (spec path resolution, adversarial dimension checklist, blast-radius calculation, failure modes, Codex adversarial pass)
- Step 7a (persist spec to task file) and 7b (set spec_review record) detail

**What moves to `references/codex-integration.md`:**
- Codex adversarial pass detection, focus-arg construction, output format

- [ ] **Step 1: Write the failing lint test** (same structure as review-gate lint test, adapted for spec-review)

```python
# plugins/taskmaster/tests/test_spec_review_skill_lint.py
"""Lint checks for the taskmaster:spec-review skill."""
from pathlib import Path
import re
import yaml
from skill_budget_helper import body_token_count, description_word_count

SKILL_DIR = Path(__file__).resolve().parents[1] / "skills" / "spec-review"


def _read_frontmatter() -> dict:
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    return yaml.safe_load(m.group(1)) or {} if m else {}


def test_skill_md_exists():
    assert (SKILL_DIR / "SKILL.md").exists()


def test_frontmatter_required_fields():
    fm = _read_frontmatter()
    assert fm.get("name") == "spec-review"
    assert "description" in fm


def test_body_within_budget():
    actual = body_token_count("spec-review")
    assert actual <= 1_300, f"body is {actual} tokens (budget: 1300)"


def test_description_within_word_budget():
    count = description_word_count("spec-review")
    assert count <= 60, f"description is {count} words (budget: 60)"


def test_description_contains_key_trigger_phrases():
    fm = _read_frontmatter()
    desc = fm["description"].lower()
    must_have = ["review this spec", "spec review", "is this the right approach"]
    missing = [p for p in must_have if p not in desc]
    assert not missing, f"description missing: {missing}"


def test_description_distinguishes_from_review_gate():
    fm = _read_frontmatter()
    desc = fm["description"].lower()
    assert "not review code" in desc or "does not review code" in desc or "pre-implementation" in desc, (
        "description must distinguish from review-gate (code review)"
    )


def test_references_exist():
    for ref in ("adversarial-steps.md", "codex-integration.md"):
        assert (SKILL_DIR / "references" / ref).exists(), f"missing references/{ref}"


def test_references_not_stubs():
    for ref in (SKILL_DIR / "references").iterdir():
        non_blank = [ln for ln in ref.read_text(encoding="utf-8").splitlines() if ln.strip()]
        assert len(non_blank) > 20, f"reference stub: {ref}"


def test_skill_md_links_resolve():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    refs = re.findall(r"`(references/[A-Za-z0-9_-]+\.md)`", text)
    assert refs, "SKILL.md must reference at least one references/ file"
    missing = [r for r in refs if not (SKILL_DIR / r).exists()]
    assert not missing, f"unresolved: {missing}"
```

- [ ] **Step 2: Run to confirm failure**
- [ ] **Step 3: Create `references/adversarial-steps.md`** with full steps 2–7b detail
- [ ] **Step 4: Create `references/codex-integration.md`** with Codex adversarial pass detail
- [ ] **Step 5: Rewrite `spec-review/SKILL.md`** to ≤1,300 tokens
- [ ] **Step 6: Verify all pass**
- [ ] **Step 7: Commit**

```
git add plugins/taskmaster/skills/spec-review/ plugins/taskmaster/tests/test_spec_review_skill_lint.py
git commit -m "refactor(skill): slim spec-review to 1300-token budget"
```

### Task 11: Slim `auto-epic` (~2,211 → 1,200 tokens)

**Files:**
- Modify: `plugins/taskmaster/skills/auto-epic/SKILL.md`
- Create: `plugins/taskmaster/skills/auto-epic/references/loop-protocol.md`
- Create: `plugins/taskmaster/skills/auto-epic/references/failure-recovery.md`
- Create: `plugins/taskmaster/tests/test_auto_epic_skill_lint.py`

**What to keep in SKILL.md (~1,200 tokens):**
- Frontmatter
- "Why subagents" (2 sentences)
- Step 0: Confirm — `AskUserQuestion` with options (keep — needed for correct invocation)
- Step 1: Seed the run — `backlog_auto_start` call (keep — exact call matters)
- Step 2: Loop header + "Repeat until cursor None or failure" + subagent dispatch (condensed — keep the Agent() call shape but drop the prose explaining each sub-step)
- Step 3: Run-level handover — `backlog_handover_create` call (keep — exact call matters)
- Step 4: Finish + `backlog_auto_finish` + one-liner output
- Pointer: "Loop sub-steps (cursor read, verify cursor advanced, token discipline, continue/halt) in `references/loop-protocol.md`. Failure recovery in `references/failure-recovery.md`."
- Per-task model selection (keep — 6 lines, needed)
- Token-cost estimate (keep — 8 lines, needed for budget awareness)

**What moves to `references/loop-protocol.md`:**
- 2a (Read cursor detail), 2c (Verify cursor advanced prose), 2d (Token discipline check prose), 2e (Continue or halt prose)

**What moves to `references/failure-recovery.md`:**
- "Failure recovery" section (halt semantics, what to tell user, resume instructions)
- "What this skill does NOT do" (4 bullets)

- [ ] **Step 1: Write the failing lint test**

```python
# plugins/taskmaster/tests/test_auto_epic_skill_lint.py
"""Lint checks for the taskmaster:auto-epic skill."""
from pathlib import Path
import re
import yaml
from skill_budget_helper import body_token_count, description_word_count

SKILL_DIR = Path(__file__).resolve().parents[1] / "skills" / "auto-epic"


def _read_frontmatter() -> dict:
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    return yaml.safe_load(m.group(1)) or {} if m else {}


def test_skill_md_exists():
    assert (SKILL_DIR / "SKILL.md").exists()


def test_frontmatter_required_fields():
    fm = _read_frontmatter()
    assert fm.get("name") == "auto-epic"
    assert "description" in fm


def test_body_within_budget():
    actual = body_token_count("auto-epic")
    assert actual <= 1_200, f"body is {actual} tokens (budget: 1200)"


def test_description_within_word_budget():
    count = description_word_count("auto-epic")
    assert count <= 60, f"description is {count} words (budget: 60)"


def test_skill_md_contains_confirm_step():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    assert "AskUserQuestion" in text, "confirm step with AskUserQuestion must be present"


def test_skill_md_contains_auto_start_call():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    assert "backlog_auto_start" in text, "seed call must be present"


def test_references_exist():
    for ref in ("loop-protocol.md", "failure-recovery.md"):
        assert (SKILL_DIR / "references" / ref).exists(), f"missing references/{ref}"


def test_references_not_stubs():
    for ref in (SKILL_DIR / "references").iterdir():
        non_blank = [ln for ln in ref.read_text(encoding="utf-8").splitlines() if ln.strip()]
        assert len(non_blank) > 20, f"reference stub: {ref}"


def test_skill_md_links_resolve():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    refs = re.findall(r"`(references/[A-Za-z0-9_-]+\.md)`", text)
    assert refs, "SKILL.md must reference at least one references/ file"
    missing = [r for r in refs if not (SKILL_DIR / r).exists()]
    assert not missing, f"unresolved: {missing}"
```

- [ ] **Step 2: Run to confirm failure**
- [ ] **Step 3: Create `references/loop-protocol.md`** — move 2a, 2c, 2d, 2e detail here
- [ ] **Step 4: Create `references/failure-recovery.md`** — move failure recovery + "does NOT do" section
- [ ] **Step 5: Rewrite `auto-epic/SKILL.md`** to ≤1,200 tokens
- [ ] **Step 6: Verify all pass**
- [ ] **Step 7: Commit**

```
git add plugins/taskmaster/skills/auto-epic/ plugins/taskmaster/tests/test_auto_epic_skill_lint.py
git commit -m "refactor(skill): slim auto-epic to 1200-token budget"
```

### Task 12: Slim `auto-phase` (~1,833 → 1,200 tokens)

**Files:**
- Modify: `plugins/taskmaster/skills/auto-phase/SKILL.md`
- Create: `plugins/taskmaster/skills/auto-phase/references/loop-protocol.md`
- Create: `plugins/taskmaster/skills/auto-phase/references/failure-aggregation.md`
- Create: `plugins/taskmaster/tests/test_auto_phase_skill_lint.py`

**What to keep in SKILL.md (~1,200 tokens):**
- Frontmatter + "Scope check" warning
- Step 0: Strong confirmation + task-count surface (keep `AskUserQuestion` + `backlog_status` call)
- Step 1: Seed run — `backlog_auto_start` call (keep)
- Step 2: Epic-by-epic loop — loop header + Agent() dispatch call (condensed — keep call shape)
- Step 3: Phase-level handover — `backlog_handover_create` call (condensed — keep call shape)
- Step 4: Phase advance suggestion (3 lines)
- Step 5: Finish + one-liner output
- Token-cost estimate (4 lines)
- Pointer: "Loop sub-steps and epic-boundary semantics in `references/loop-protocol.md`. Failure aggregation policy in `references/failure-aggregation.md`."

**What moves to `references/loop-protocol.md`:**
- Step 2 sub-steps 1–5 detail (read cursor, lookup epic, dispatch, capture result, after-epic status check)
- "Why this is not yet auto-roadmap" explanation

**What moves to `references/failure-aggregation.md`:**
- "Failure aggregation policy" section (continue_on_fail=false vs true semantics, no-per-epic-boundary note)
- "What this skill does NOT do" (3 bullets)

- [ ] **Step 1: Write the failing lint test** (same structure as auto-epic test, adapted)
- [ ] **Step 2: Run to confirm failure**
- [ ] **Step 3: Create `references/loop-protocol.md`**
- [ ] **Step 4: Create `references/failure-aggregation.md`**
- [ ] **Step 5: Rewrite `auto-phase/SKILL.md`** to ≤1,200 tokens
- [ ] **Step 6: Verify all pass**
- [ ] **Step 7: Commit**

```
git add plugins/taskmaster/skills/auto-phase/ plugins/taskmaster/tests/test_auto_phase_skill_lint.py
git commit -m "refactor(skill): slim auto-phase to 1200-token budget"
```

### Task 13: Slim `init-taskmaster` → 1,200 tokens

**Files:**
- Read `plugins/taskmaster/skills/init-taskmaster/SKILL.md` first (not yet read in this plan)
- Modify: `plugins/taskmaster/skills/init-taskmaster/SKILL.md`
- Create: `plugins/taskmaster/skills/init-taskmaster/references/analysis-mode.md`
- Create: `plugins/taskmaster/tests/test_init_taskmaster_skill_lint.py`

**Before starting:** Read the full SKILL.md, identify deep-walkthrough content (likely: "analyze existing TODOs" mode, phase scaffold logic, epic layout suggestions, post-init checklist). Keep: CRITICAL note, Step 1 (check initialized), routing to clean vs analysis mode, final confirm.

- [ ] **Step 1: Read `init-taskmaster/SKILL.md`** to understand current content
- [ ] **Step 2: Write the failing lint test**

```python
# plugins/taskmaster/tests/test_init_taskmaster_skill_lint.py
"""Lint checks for the taskmaster:init-taskmaster skill."""
from pathlib import Path
import re
import yaml
from skill_budget_helper import body_token_count, description_word_count

SKILL_DIR = Path(__file__).resolve().parents[1] / "skills" / "init-taskmaster"


def _read_frontmatter() -> dict:
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    return yaml.safe_load(m.group(1)) or {} if m else {}


def test_skill_md_exists():
    assert (SKILL_DIR / "SKILL.md").exists()


def test_frontmatter_required_fields():
    fm = _read_frontmatter()
    assert fm.get("name") == "init-taskmaster"
    assert "description" in fm


def test_body_within_budget():
    actual = body_token_count("init-taskmaster")
    assert actual <= 1_200, f"body is {actual} tokens (budget: 1200)"


def test_description_within_word_budget():
    count = description_word_count("init-taskmaster")
    assert count <= 60, f"description is {count} words (budget: 60)"


def test_skill_md_contains_critical_note():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    assert "CRITICAL" in text and "backlog_init" in text, (
        "CRITICAL note about not writing backlog.yaml directly must be present"
    )


def test_references_exist():
    assert (SKILL_DIR / "references" / "analysis-mode.md").exists()


def test_references_not_stubs():
    for ref in (SKILL_DIR / "references").iterdir():
        non_blank = [ln for ln in ref.read_text(encoding="utf-8").splitlines() if ln.strip()]
        assert len(non_blank) > 20, f"reference stub: {ref}"


def test_skill_md_links_resolve():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    refs = re.findall(r"`(references/[A-Za-z0-9_-]+\.md)`", text)
    assert refs, "SKILL.md must reference at least one references/ file"
    missing = [r for r in refs if not (SKILL_DIR / r).exists()]
    assert not missing, f"unresolved: {missing}"
```

- [ ] **Step 3: Run to confirm failure**
- [ ] **Step 4: Create `references/analysis-mode.md`** — move the "analyze existing TODOs" subflow and related detail
- [ ] **Step 5: Rewrite `init-taskmaster/SKILL.md`** to ≤1,200 tokens
- [ ] **Step 6: Verify all pass**
- [ ] **Step 7: Commit**

```
git add plugins/taskmaster/skills/init-taskmaster/ plugins/taskmaster/tests/test_init_taskmaster_skill_lint.py
git commit -m "refactor(skill): slim init-taskmaster to 1200-token budget"
```

### Task 14: Slim `migrate-v3` → 1,200 tokens

**Files:**
- Read `plugins/taskmaster/skills/migrate-v3/SKILL.md` first
- Modify: `plugins/taskmaster/skills/migrate-v3/SKILL.md`
- Create: `plugins/taskmaster/skills/migrate-v3/references/migration-steps.md`

**Before starting:** Read the full SKILL.md. The description is already listed in `test_migrate_v3_skill_lint.py` — preserve all trigger phrases. Identify deep-walkthrough content (likely: the step-by-step migration prose, gitignore additions, post-flight tour of v3 surfaces). Keep: ONLY sentence, Step 1 (detect schema), routing to migrate vs already-on-v3, confirmation gate, `backlog_migrate_v3` call.

- [ ] **Step 1: Read `migrate-v3/SKILL.md`**
- [ ] **Step 2: Confirm body/description budget assertions in `test_migrate_v3_skill_lint.py` already fail** (from Task 3)
- [ ] **Step 3: Create `references/migration-steps.md`** — move pre-flight summary detail, explanation of schema break, post-flight tour, gitignore additions detail
- [ ] **Step 4: Update `test_migrate_v3_skill_lint.py`** to add `test_references_exist` checking `migration-steps.md` and `test_skill_md_links_resolve`
- [ ] **Step 5: Rewrite `migrate-v3/SKILL.md`** to ≤1,200 tokens
- [ ] **Step 6: Verify all pass**
- [ ] **Step 7: Commit**

```
git add plugins/taskmaster/skills/migrate-v3/ plugins/taskmaster/tests/test_migrate_v3_skill_lint.py
git commit -m "refactor(skill): slim migrate-v3 to 1200-token budget"
```

### Task 15: Slim `check-todos` → 1,200 tokens

**Files:**
- Read `plugins/taskmaster/skills/check-todos/SKILL.md` first
- Modify: `plugins/taskmaster/skills/check-todos/SKILL.md`
- Create: `plugins/taskmaster/skills/check-todos/references/scan-flow.md`
- Create: `plugins/taskmaster/tests/test_check_todos_skill_lint.py`

**Before starting:** Read the full SKILL.md. Identify what's a decision tree (keep) vs what's a step-by-step walkthrough of the scan logic (move to references). Keep: purpose, scan markers (TODO/FIXME/HACK/XXX), cross-reference with backlog, output format summary.

- [ ] **Step 1: Read `check-todos/SKILL.md`**
- [ ] **Step 2: Write the failing lint test**

```python
# plugins/taskmaster/tests/test_check_todos_skill_lint.py
"""Lint checks for the taskmaster:check-todos skill."""
from pathlib import Path
import re
import yaml
from skill_budget_helper import body_token_count, description_word_count

SKILL_DIR = Path(__file__).resolve().parents[1] / "skills" / "check-todos"


def _read_frontmatter() -> dict:
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    return yaml.safe_load(m.group(1)) or {} if m else {}


def test_skill_md_exists():
    assert (SKILL_DIR / "SKILL.md").exists()


def test_frontmatter_required_fields():
    fm = _read_frontmatter()
    assert fm.get("name") == "check-todos"
    assert "description" in fm


def test_body_within_budget():
    actual = body_token_count("check-todos")
    assert actual <= 1_200, f"body is {actual} tokens (budget: 1200)"


def test_description_within_word_budget():
    count = description_word_count("check-todos")
    assert count <= 60, f"description is {count} words (budget: 60)"


def test_description_contains_trigger_phrases():
    fm = _read_frontmatter()
    desc = fm["description"].lower()
    must_have = ["check todos", "scan for todos", "todo audit"]
    missing = [p for p in must_have if p not in desc]
    assert not missing, f"description missing: {missing}"


def test_references_exist():
    assert (SKILL_DIR / "references" / "scan-flow.md").exists()


def test_references_not_stubs():
    for ref in (SKILL_DIR / "references").iterdir():
        non_blank = [ln for ln in ref.read_text(encoding="utf-8").splitlines() if ln.strip()]
        assert len(non_blank) > 20, f"reference stub: {ref}"


def test_skill_md_links_resolve():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    refs = re.findall(r"`(references/[A-Za-z0-9_-]+\.md)`", text)
    assert refs, "SKILL.md must reference at least one references/ file"
    missing = [r for r in refs if not (SKILL_DIR / r).exists()]
    assert not missing, f"unresolved: {missing}"
```

- [ ] **Step 3: Run to confirm failure**
- [ ] **Step 4: Create `references/scan-flow.md`** — move detailed scan logic
- [ ] **Step 5: Rewrite `check-todos/SKILL.md`** to ≤1,200 tokens
- [ ] **Step 6: Verify all pass**
- [ ] **Step 7: Commit**

```
git add plugins/taskmaster/skills/check-todos/ plugins/taskmaster/tests/test_check_todos_skill_lint.py
git commit -m "refactor(skill): slim check-todos to 1200-token budget"
```

### Task 16: Slim `add-idea` → 1,200 tokens

**Files:**
- Modify: `plugins/taskmaster/skills/add-idea/SKILL.md`
- Create: `plugins/taskmaster/skills/add-idea/references/slash-form.md`
- Modify: `plugins/taskmaster/tests/test_add_idea_skill_lint.py` (add references check)

**Before starting:** Read the full SKILL.md. The slash-form invocation (field-by-field parse rules, YAML generation, commit flow) is the likely deep-walkthrough content. Keep: purpose, trigger phrases, `backlog_idea_create` call signature, body shape.

- [ ] **Step 1: Read `add-idea/SKILL.md`**
- [ ] **Step 2: Confirm body/description budget assertions already fail** (from Task 3)
- [ ] **Step 3: Create `references/slash-form.md`** — move slash-form parse rules and field-extraction detail
- [ ] **Step 4: Update `test_add_idea_skill_lint.py`** to add `test_references_exist` and `test_skill_md_links_resolve`
- [ ] **Step 5: Rewrite `add-idea/SKILL.md`** to ≤1,200 tokens
- [ ] **Step 6: Verify all pass**
- [ ] **Step 7: Commit**

```
git add plugins/taskmaster/skills/add-idea/ plugins/taskmaster/tests/test_add_idea_skill_lint.py
git commit -m "refactor(skill): slim add-idea to 1200-token budget"
```

### Task 17: Lint-check `auto-task` body (Plan E lint only, no body rewrite)

**Context:** `auto-task` is already lean (~620 tokens based on the SKILL.md read). Plan E does not restructure it — just confirms the budget lint passes as-is and extends the existing lint test with description check.

**Files:**
- Modify: `plugins/taskmaster/tests/test_auto_task_skill_lint.py` (if exists) or create it

- [ ] **Step 1: Check if `test_auto_task_skill_lint.py` exists**

Run: `ls plugins/taskmaster/tests/test_auto_task*`

- [ ] **Step 2a: If exists** — add budget assertions (body ≤1,500, description ≤60 words)
- [ ] **Step 2b: If not** — create minimal lint test:

```python
# plugins/taskmaster/tests/test_auto_task_skill_lint.py
"""Lint checks for the taskmaster:auto-task skill."""
from pathlib import Path
import re
import yaml
from skill_budget_helper import body_token_count, description_word_count

SKILL_DIR = Path(__file__).resolve().parents[1] / "skills" / "auto-task"


def _read_frontmatter() -> dict:
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    return yaml.safe_load(m.group(1)) or {} if m else {}


def test_skill_md_exists():
    assert (SKILL_DIR / "SKILL.md").exists()


def test_frontmatter_required_fields():
    fm = _read_frontmatter()
    assert fm.get("name") == "auto-task"
    assert "description" in fm


def test_body_within_budget():
    # auto-task is already lean; this confirms it stays within budget.
    actual = body_token_count("auto-task")
    assert actual <= 1_500, f"body is {actual} tokens (budget: 1500)"


def test_description_within_word_budget():
    count = description_word_count("auto-task")
    assert count <= 60, f"description is {count} words (budget: 60)"


def test_skill_md_links_resolve():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    refs = re.findall(r"`(references/[A-Za-z0-9_-]+\.md)`", text)
    missing = [r for r in refs if not (SKILL_DIR / r).exists()]
    assert not missing, f"unresolved: {missing}"
```

- [ ] **Step 3: Run to confirm body budget PASSES, description FAILS** (description is ~36 words — should already pass; body is already ≤1,500)
- [ ] **Step 4: Commit**

```
git add plugins/taskmaster/tests/test_auto_task_skill_lint.py
git commit -m "test(skill): add lint check for auto-task budget (already lean)"
```

---

## Phase 3 — Description Audit (one task per skill)

> **Pattern for each task:** (1) Read current description. (2) Identify trigger phrases — KEEP. (3) Rewrite as 3 sentences: what / triggers / hard rule. (4) Verify ≤60 words. (5) Verify the description still contains the required trigger phrases (existing lint tests check these). (6) Commit.
>
> **Do not break existing trigger-phrase assertions in any lint test.**

### Task 18: Rewrite `taskmaster` router description

**Current:** ~106 words, lists every implementation type, all v3 surfaces.

**Target:** ≤60 words, preserves: "backlog.yaml", route, and "any project" as triggers.

**New description:**
```
Universal work router for any project with backlog.yaml. Invoke for implementing features, fixing bugs, writing tests, refactoring, planning epics, or any narrative-continuity operation (handovers, issues, lessons, auto-mode). The only exceptions are pure git commits and dedicated PR security reviews.
```
Word count: 42 words. ✓

- [ ] **Step 1: Update frontmatter description in `taskmaster/SKILL.md`** (already done in Task 4 Step 5 — verify it was set correctly)
- [ ] **Step 2: Run description budget test** — `pytest plugins/taskmaster/tests/test_skill_description_budgets.py::test_skill_description_within_budget[taskmaster] -v`
- [ ] **Step 3: Commit if not already included in Task 4 commit**

### Task 19: Rewrite `end-session` description

**Current:** ~61 words. Slightly over budget with "Auto-generates Done/Decisions/Issues summary, transitions task status, commits tracking files."

**Target:** ≤60 words, preserves: "end session", "I'm done for today", "let's wrap up", "log this work", "mark this task done", "save progress".

**New description:**
```
Close out a work session. Invoke when the user says 'end session', 'I'm done for today', 'let's wrap up', 'mark this task done', or 'save progress'. This is the ONLY correct way to mark tasks done or in-review with a session record.
```
Word count: 44 words. ✓

- [ ] **Step 1: Update frontmatter in `end-session/SKILL.md`** (already done in Task 5 Step 5 — verify)
- [ ] **Step 2: Run description budget test**

### Task 20: Rewrite `handover` description

**Current:** ~80 words. Very long trigger list, lots of prose.

**Target:** ≤60 words, preserves: "write a handover", "wrap up", "for tomorrow", "context handoff", "before compaction".

**New description:**
```
Write a session handover into .taskmaster/handovers/. Invoke when the user says 'write a handover', 'wrap up', 'for tomorrow', 'before compaction', 'context handoff', or 'continue where we left off'. This is the only correct way to write a handover — do not call backlog_handover_create directly.
```
Word count: 47 words. ✓

- [ ] **Step 1: Update frontmatter in `handover/SKILL.md`**
- [ ] **Step 2: Verify existing trigger-phrase assertions still pass**

Run: `pytest plugins/taskmaster/tests/test_handover_skill_lint.py::test_description_contains_key_trigger_phrases -v`

- [ ] **Step 3: Run description budget test**
- [ ] **Step 4: Commit**

```
git add plugins/taskmaster/skills/handover/SKILL.md
git commit -m "refactor(skill): trim handover description to ≤60 words"
```

### Task 21: Rewrite `issue` description

**Current:** ~96 words. Very long trigger list + auto-offered detail.

**Target:** ≤60 words, preserves all 14 trigger phrases currently checked in `test_issue_skill_lint.py`.

**Challenge:** The existing lint test checks 14 specific trigger phrases. The 60-word budget cannot fit all 14 verbatim — but they're checked against the description. Review which ones the test actually checks (`must_have` list) and ensure they all appear in the new description.

**Strategy:** Use comma-list form for triggers.

**New description:**
```
Log, update, or close project issues in .taskmaster/issues/. Invoke when the user says 'log a bug', 'found an issue', 'this is broken', 'track this defect', 'log this defect', 'file a bug', 'report a bug', 'this is a bug', 'mark issue fixed', 'close ISS-XX', 'investigating ISS-XX', 'list open issues', 'what bugs are open', or 'triage issues'. Only correct way to write or transition an issue.
```
Word count: 70 words — over budget. Must trim further. Drop one introductory phrase.

**Revised:**
```
Log/update/close project issues in .taskmaster/issues/. Invoke when the user says 'log a bug', 'found an issue', 'this is broken', 'track this defect', 'log this defect', 'file a bug', 'report a bug', 'this is a bug', 'mark issue fixed', 'close ISS-XX', 'investigating ISS-XX', 'list open issues', 'what bugs are open', or 'triage issues'. This is the only correct way to write or transition an issue.
```
Word count: 66 words — still over. Consider relaxing to 65 or trimming "project" and "or".

**Note:** If the 14 trigger phrases cannot fit in 60 words, accept 65 words for this skill and update `DESCRIPTION_WORD_BUDGET` to 65 for `issue` only via a per-skill override in the test. Document this in the test.

- [ ] **Step 1: Count words in the tightest possible version of the description**
- [ ] **Step 2: If >60 words are truly required** — add a `DESCRIPTION_WORD_OVERRIDES` dict to `skill_budget_helper.py`:

```python
# Per-skill overrides for skills whose trigger phrases genuinely cannot fit in 60 words.
DESCRIPTION_WORD_OVERRIDES: dict[str, int] = {
    "issue": 70,  # 14 required trigger phrases enforced by test_issue_skill_lint.py
}
```

Update `test_skill_description_budgets.py` to use the override:

```python
def test_skill_description_within_budget(skill):
    from skill_budget_helper import DESCRIPTION_WORD_OVERRIDES
    budget = DESCRIPTION_WORD_OVERRIDES.get(skill, DESCRIPTION_WORD_BUDGET)
    count = description_word_count(skill)
    assert count <= budget, ...
```

- [ ] **Step 3: Update frontmatter in `issue/SKILL.md`**
- [ ] **Step 4: Verify existing trigger-phrase assertions still pass**

Run: `pytest plugins/taskmaster/tests/test_issue_skill_lint.py::test_description_contains_trigger_phrases -v`

- [ ] **Step 5: Run description budget test**
- [ ] **Step 6: Commit**

```
git add plugins/taskmaster/skills/issue/SKILL.md plugins/taskmaster/tests/skill_budget_helper.py plugins/taskmaster/tests/test_skill_description_budgets.py
git commit -m "refactor(skill): trim issue description to budget (override for 14 triggers)"
```

### Task 22: Rewrite `lesson` description

**Current:** ~81 words.

**Target:** ≤60 words, preserves: "remember this", "save as a lesson", "learn this lesson", "memorize this", "this keeps happening", "we always do X here", "we got burned by this last time", "promote candidate to lesson", "review lesson candidates", "flag this session for retro".

**New description:**
```
Write, reinforce, or promote a project-scoped lesson. Invoke when the user says 'remember this', 'save as a lesson', 'learn this lesson', 'memorize this', 'this keeps happening', 'we always do X here', 'we got burned by this last time', 'promote candidate to lesson', 'review lesson candidates', or 'flag this session for retro'. Only correct way to write or reinforce a lesson.
```
Word count: 62 words — close to 60; trim "Write, reinforce, or promote" to "Write or reinforce".

**Revised:** ~59 words. ✓

- [ ] **Step 1: Update frontmatter in `lesson/SKILL.md`** (coordinate with body slim in Task 6)
- [ ] **Step 2: Verify existing trigger-phrase assertions pass**
- [ ] **Step 3: Run description budget test**
- [ ] **Step 4: Commit** (include with Task 6 commit or separately)

### Task 23: Rewrite `auto-task` description

**Current:** ~40 words. Already near budget — just verify.

**Current text:** "Drive a single task through the full lifecycle (PICK → SPEC_REVIEW → IMPLEMENT → REVIEW_GATE → HANDOVER → END_SESSION) using the auto state machine. Invoke when the user says 'auto T-001', 'autopilot this task', 'run task auto', or when called by auto-epic/auto-phase orchestrator skills as a subagent recipe."

Word count: ~48 words. ✓ Already within budget.

- [ ] **Step 1: Confirm word count is ≤60** — no rewrite needed
- [ ] **Step 2: Run description budget test** — `pytest plugins/taskmaster/tests/test_skill_description_budgets.py::test_skill_description_within_budget[auto-task] -v`
  Expected: PASS (no change required)

### Task 24: Rewrite `review-gate` description

**Current:** ~64 words.

**Target:** ≤60 words, preserves: "is this ready?", "run the review gate", "check my work", "I think this is done".

**New description:**
```
Run quality checks on a task's implementation before marking it ready for user testing. Invoke when the user says 'is this ready?', 'run the review gate', 'check my work', or 'I think this is done'. Does not review code design — use taskmaster:spec-review for pre-implementation review.
```
Word count: 48 words. ✓

- [ ] **Step 1: Update frontmatter in `review-gate/SKILL.md`** (coordinate with Task 9)
- [ ] **Step 2: Run description budget test**

### Task 25: Rewrite `spec-review` description

**Current:** ~52 words. Already near budget.

**Current text:** "Adversarial design review of a task's spec or plan before implementation begins. Invoke when the user says 'review this spec', 'challenge this design', 'is this the right approach?', 'spec review', or after writing a new spec for a critical/high task. Reviews the proposed approach for assumptions, scope, edge cases, and predicted blast radius — does NOT review code."

Word count: 57 words. ✓ Already within budget.

- [ ] **Step 1: Confirm word count ≤60** — no rewrite needed
- [ ] **Step 2: Run description budget test** — Expected: PASS

### Task 26: Rewrite `auto-epic` description

**Current:** ~35 words. Already within budget.

- [ ] **Step 1: Confirm word count ≤60** — Expected: PASS (no rewrite needed)
- [ ] **Step 2: Run test** — `pytest plugins/taskmaster/tests/test_skill_description_budgets.py::test_skill_description_within_budget[auto-epic] -v`

### Task 27: Rewrite `auto-phase` description

**Current:** ~31 words. Already within budget.

- [ ] **Step 1: Confirm word count ≤60** — Expected: PASS (no rewrite needed)
- [ ] **Step 2: Run test**

### Task 28: Rewrite `init-taskmaster` description

**Current:** ~31 words. Already within budget.

- [ ] **Step 1: Confirm word count ≤60** — Expected: PASS
- [ ] **Step 2: Run test**

### Task 29: Rewrite `migrate-v3` description

**Current:** ~71 words. Over budget.

**Target:** ≤60 words, preserves trigger phrases checked in `test_migrate_v3_skill_lint.py` (check that file for exact must_have list before rewriting).

**New description (draft):**
```
Guided v2 → v3 backlog migration. Invoke when the user says 'upgrade to v3', 'migrate to v3', 'switch to v3', 'enable handovers and lessons', 'enable narrative continuity', 'turn on auto-mode', or 'I want recap'. Shows pre-flight summary, confirms opt-in, runs migration. Only correct way to migrate — do not call backlog_migrate_v3 directly.
```
Word count: 55 words. ✓

- [ ] **Step 1: Read `test_migrate_v3_skill_lint.py`** to confirm required trigger phrases
- [ ] **Step 2: Update frontmatter in `migrate-v3/SKILL.md`** (coordinate with Task 14)
- [ ] **Step 3: Verify existing trigger-phrase assertions pass**
- [ ] **Step 4: Run description budget test**

### Task 30: Rewrite `check-todos` description

**Current:** ~29 words. Already within budget.

- [ ] **Step 1: Confirm word count ≤60** — Expected: PASS (no rewrite needed)

### Task 31: Rewrite `add-idea` description

**Current:** ~57 words. Just within budget — verify.

- [ ] **Step 1: Confirm word count ≤60** — Expected: PASS or very close
- [ ] **Step 2: If over** — trim "Lighter than a task — just a freeform note with optional tags, status, and links to tasks/issues/lessons." to "Lighter than a task." (saves ~17 words)
- [ ] **Step 3: Verify trigger-phrase assertions in existing lint test still pass**
- [ ] **Step 4: Run description budget test**

---

## Phase 4 — Plan D Coordination: Lint-Check `start-session` and `pick-task`

> Plan D owns the body rewrites for these two skills. Plan E adds lint tests that they must eventually satisfy. These tasks are marked xfail until Plan D merges.

### Task 32: Add lint test for `start-session` (xfail until Plan D)

**Files:**
- Create: `plugins/taskmaster/tests/test_start_session_skill_lint.py`

```python
# plugins/taskmaster/tests/test_start_session_skill_lint.py
"""Lint checks for the taskmaster:start-session skill.

NOTE: Body budget (1300 tokens) is xfail until Plan D merges — Plan D owns the
start-session SKILL.md restructuring. Description budget check runs immediately.
"""
from pathlib import Path
import re
import yaml
import pytest
from skill_budget_helper import body_token_count, description_word_count

SKILL_DIR = Path(__file__).resolve().parents[1] / "skills" / "start-session"


def _read_frontmatter() -> dict:
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    return yaml.safe_load(m.group(1)) or {} if m else {}


def test_skill_md_exists():
    assert (SKILL_DIR / "SKILL.md").exists()


def test_frontmatter_required_fields():
    fm = _read_frontmatter()
    assert fm.get("name") == "start-session"
    assert "description" in fm


@pytest.mark.xfail(
    reason="Plan D owns start-session body slim — remove xfail marker when Plan D merges",
    strict=True,
)
def test_body_within_budget():
    actual = body_token_count("start-session")
    assert actual <= 1_300, f"body is {actual} tokens (budget: 1300)"


def test_description_within_word_budget():
    count = description_word_count("start-session")
    assert count <= 60, f"description is {count} words (budget: 60)"


def test_description_contains_key_trigger_phrases():
    fm = _read_frontmatter()
    desc = fm["description"].lower()
    must_have = ["let's get started", "what should i work on", "show me the backlog"]
    missing = [p for p in must_have if p not in desc]
    assert not missing, f"description missing: {missing}"
```

- [ ] **Step 1: Write the test file as above**
- [ ] **Step 2: Run to verify `test_body_within_budget` is xfail (not a real failure) and description check either passes or fails**
- [ ] **Step 3: If description is >60 words** — rewrite it now (Plan E can trim the description; only the body is Plan D's territory)
- [ ] **Step 4: Commit**

```
git add plugins/taskmaster/tests/test_start_session_skill_lint.py
git commit -m "test(skill): add start-session lint (body xfail — Plan D; description trimmed)"
```

### Task 33: Add lint test for `pick-task` (xfail until Plan D)

**Files:**
- Create: `plugins/taskmaster/tests/test_pick_task_skill_lint.py`

Same structure as Task 32, adapted for `pick-task` (name: "pick-task", budget: 1,300, triggers: "pick a task", "let's work on X", "start task auth-003", "what should I tackle next", "continue this task", "continue where we left off").

- [ ] **Step 1: Write the test file** (mirror Task 32 structure)
- [ ] **Step 2: Run — verify xfail on body, run description check**
- [ ] **Step 3: Trim `pick-task` description to ≤60 words if needed**
- [ ] **Step 4: Commit**

```
git add plugins/taskmaster/tests/test_pick_task_skill_lint.py
git commit -m "test(skill): add pick-task lint (body xfail — Plan D; description trimmed)"
```

---

## Phase 5 — Smoke Test: Full Catalog Token Sum

### Task 34: Catalog-sum smoke test

**Files:**
- Create: `plugins/taskmaster/tests/test_skill_catalog_smoke.py`

This test verifies the combined success criterion from the spec: eager skill catalog ≤ 2,500 tokens.

The "eager catalog" is the sum of all description word counts converted to tokens (descriptions are what Claude loads eagerly). A more actionable proxy: sum of all description char counts ÷ 4.

```python
# plugins/taskmaster/tests/test_skill_catalog_smoke.py
"""Smoke test: sum of all skill descriptions ≤ 2,500 tokens (eager catalog budget)."""
import re
import yaml
from pathlib import Path
from skill_budget_helper import SKILL_BUDGETS, CHARS_PER_TOKEN

SKILLS_ROOT = Path(__file__).resolve().parents[1] / "skills"
CATALOG_TOKEN_BUDGET = 2_500


def _description_tokens(skill_name: str) -> int:
    path = SKILLS_ROOT / skill_name / "SKILL.md"
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return 0
    fm = yaml.safe_load(m.group(1)) or {}
    return len(fm.get("description", "")) // CHARS_PER_TOKEN


def test_eager_catalog_within_budget():
    """Sum of all skill description token-counts must be ≤ 2,500 tokens."""
    total = sum(_description_tokens(skill) for skill in SKILL_BUDGETS)
    skill_breakdown = {s: _description_tokens(s) for s in SKILL_BUDGETS}
    top = sorted(skill_breakdown.items(), key=lambda x: x[1], reverse=True)[:5]
    assert total <= CATALOG_TOKEN_BUDGET, (
        f"Eager skill catalog is {total} tokens (budget: {CATALOG_TOKEN_BUDGET}). "
        f"Top 5 by size: {top}"
    )


def test_all_skill_bodies_exist():
    """Sanity: every skill in SKILL_BUDGETS has a SKILL.md on disk."""
    missing = [s for s in SKILL_BUDGETS if not (SKILLS_ROOT / s / "SKILL.md").exists()]
    assert not missing, f"SKILL.md missing for: {missing}"
```

- [ ] **Step 1: Run to confirm test fails initially** (catalog is ~1,000 tokens of descriptions before trimming)

Run: `pytest plugins/taskmaster/tests/test_skill_catalog_smoke.py -v`

- [ ] **Step 2: After all description tasks complete (Tasks 18–31), run again** — Expected: PASS

- [ ] **Step 3: Commit**

```
git add plugins/taskmaster/tests/test_skill_catalog_smoke.py
git commit -m "test(skill): add catalog-sum smoke test (eager descriptions ≤ 2500 tokens)"
```

---

## Phase 6 — Full Suite Run and Changelog

### Task 35: Run the full lint suite

- [ ] **Step 1: Run all skill lint tests together**

```
pytest plugins/taskmaster/tests/test_skill_body_budgets.py \
       plugins/taskmaster/tests/test_skill_description_budgets.py \
       plugins/taskmaster/tests/test_skill_catalog_smoke.py \
       plugins/taskmaster/tests/test_taskmaster_skill_lint.py \
       plugins/taskmaster/tests/test_end_session_skill_lint.py \
       plugins/taskmaster/tests/test_auto_epic_skill_lint.py \
       plugins/taskmaster/tests/test_auto_phase_skill_lint.py \
       plugins/taskmaster/tests/test_review_gate_skill_lint.py \
       plugins/taskmaster/tests/test_spec_review_skill_lint.py \
       plugins/taskmaster/tests/test_init_taskmaster_skill_lint.py \
       plugins/taskmaster/tests/test_migrate_v3_skill_lint.py \
       plugins/taskmaster/tests/test_check_todos_skill_lint.py \
       plugins/taskmaster/tests/test_add_idea_skill_lint.py \
       plugins/taskmaster/tests/test_auto_task_skill_lint.py \
       plugins/taskmaster/tests/test_handover_skill_lint.py \
       plugins/taskmaster/tests/test_issue_skill_lint.py \
       plugins/taskmaster/tests/test_lesson_skill_lint.py \
       plugins/taskmaster/tests/test_start_session_skill_lint.py \
       plugins/taskmaster/tests/test_pick_task_skill_lint.py \
       -v 2>&1 | tail -50
```

Expected: All PASS or XFAIL (start-session and pick-task body budget xfail). No unexpected failures.

- [ ] **Step 2: If any test is unexpectedly failing** — fix it before proceeding to changelog.

- [ ] **Step 3: Run the pre-existing test suite** to ensure nothing regressed

```
pytest plugins/taskmaster/tests/ -v --tb=short 2>&1 | tail -80
```

### Task 36: Add CHANGELOG entry

**Files:**
- Modify: `plugins/taskmaster/CHANGELOG.md`

Add at the top of the unreleased section:

```markdown
### Skill content slimming (Plan E)

- Every taskmaster SKILL.md is now within its token budget (800–1,500 tokens per skill).
- Deep-walkthrough content extracted to `references/<topic>.md` per skill — loaded on demand, not eagerly.
- All skill `description` fields trimmed to ≤60 words (exception: `issue` at ≤70 words to preserve 14 required trigger phrases).
- Eager skill catalog reduced from ~4,000 to ≤2,500 tokens.
- New lint infrastructure: `skill_budget_helper.py` + parametrized body and description tests for all 16 skills.
- `start-session` and `pick-task` body budgets lint-checked but marked xfail pending Plan D merge.
```

- [ ] **Step 1: Update CHANGELOG.md**
- [ ] **Step 2: Commit**

```
git add plugins/taskmaster/CHANGELOG.md
git commit -m "chore: changelog entry for Plan E skill slimming"
```

---

## Success Criteria

All of the following must be true before Plan E is considered complete:

- [ ] `pytest plugins/taskmaster/tests/test_skill_body_budgets.py -v` — all PASS or XFAIL (start-session, pick-task)
- [ ] `pytest plugins/taskmaster/tests/test_skill_description_budgets.py -v` — all PASS
- [ ] `pytest plugins/taskmaster/tests/test_skill_catalog_smoke.py -v` — PASS (catalog ≤ 2,500 tokens)
- [ ] Every SKILL.md body with a `references/` pointer has the referenced file on disk and non-stub (>20 non-blank lines)
- [ ] No existing lint test (handover, issue, lesson, add-idea, migrate-v3) regresses — all previously-passing assertions still pass
- [ ] `auto-task`, `review-gate`, `spec-review`, `auto-epic`, `auto-phase` trigger phrases still appear in their respective descriptions
- [ ] `start-session` and `pick-task` body budget tests are xfail (not skip, not hard fail)

## Task Count Summary

| Phase | Tasks | Description |
|---|---|---|
| 1 — Lint Infrastructure | 3 | Helper, body-budget parametrized test, description-budget parametrized test, extend existing tests |
| 2 — Body Slimming | 14 | One per skill (tasks 4–17): taskmaster, end-session, lesson, handover, issue, review-gate, spec-review, auto-epic, auto-phase, init-taskmaster, migrate-v3, check-todos, add-idea, auto-task (lint only) |
| 3 — Description Audit | 14 | One per skill (tasks 18–31): all descriptions audited; most trimmed, some already pass |
| 4 — Plan D Coordination | 2 | start-session + pick-task lint tests (xfail on body) |
| 5 — Smoke Test | 1 | Catalog token sum |
| 6 — Suite + Changelog | 2 | Full suite run + changelog |
| **Total** | **36** | |
