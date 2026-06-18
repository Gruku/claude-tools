> ⚠ **Superseded (2026-06-11).** This design builds on taskmaster's auto-mode state machine,
> which has been removed (see docs/superpowers/specs/2026-06-11-remove-auto-mode-design.md).
> Autonomous execution now routes through goals + ultracode. The substrate assumed below no
> longer exists; treat this as historical until redesigned.

# Auto-Brainstorm + /goal — Design Spec

**Date:** 2026-05-10
**Status:** draft (brainstorming complete, pending user review before implementation plan)
**Project:** Taskmaster plugin (`plugins/taskmaster/`)

## Problem

Auto-mode (`auto-task` / `auto-epic` / `auto-phase`) currently has a vague drafting step at SPEC_REVIEW: *"If the task body has no `## Spec / Plan` section yet, draft one. Use `superpowers:writing-plans` if the task is non-trivial."* In practice this means an unsupervised run produces shallow specs — no structured research, no adversarial pressure, no exit-condition discipline. The `superpowers:brainstorming` skill that produces good specs depends on a live human conversation, which auto-mode by definition lacks.

Two consequences:

1. **Specs drift from intent.** The implementation often ends up technically correct but answering a slightly different question than the user had in mind, because the auto-task never had a forcing function to make the spec rigorous before code starts.
2. **No autonomous-from-zero entry point.** A user who wants "set this goal before bed, wake up to receipts" must first manually create a task, write its spec, write its plan, *then* invoke auto-task. The friction defeats the autonomy.

A separate problem motivates the same change: ChatGPT/Codex `/goal` and Hermes `persist ghost` ship an LLM-judged stop loop that prevents premature completion on long-horizon work — taskmaster's auto-mode has no such judge, so an auto-task ends when its tests pass even if the goal isn't actually satisfied.

This design folds three concerns into one feature: **opinionated unsupervised spec authoring (auto-brainstorm)**, **an autonomous-from-zero entry point (`/goal`)**, and **an LLM-judged completion gate (goal-judge)**.

## Goals

1. **Opinionated unsupervised spec generation.** Replace the handwave "draft one" substep with a structured pipeline that produces specs meeting a fixed rubric, without user interaction.
2. **`/goal` as autonomous entry point.** A single command takes a natural-language outcome, validates it, creates a tracked unit of work, and fires auto-mode through to completion.
3. **LLM-judged completion.** A read-only judging subagent decides whether the implementation actually satisfies the goal. Looping back is structured (in-task vs follow-up task) based on gap classification.
4. **First-class subagent in the plugin.** Ship `taskmaster:goal-judge` as the plugin's first dedicated subagent — demonstrating the pattern and validating prompt isolation as a primitive we'll reuse.
5. **Integrate with v3 narrative continuity.** Goals reuse Epic infrastructure (with `kind: goal` discriminator), feeding into the existing handover / lesson / issue / idea surfaces.
6. **Opinionated, not configurable.** Strong defaults; minimal flags. Iteration budgets, rubric contents, and judge behavior are baked in, not tunable per-run (with a deliberate exception for `--accept-vague` and `no_gate=true`).

## Non-goals

- **Mission-style scheduled multi-day iterations** (AI Jason's mission concept). Defer; current scope is single-session autonomous coding goals.
- **A separate goal-buddy interactive interview wizard.** Auto-brainstorm absorbs the interview role for both attended and unattended paths.
- **First-class `G-NNN` Goal entity.** Goal is an Epic with `kind: goal`. We can promote later if behavioral differences accumulate.
- **Dynamic configuration of iteration budgets / rubric / judge prompt.** Hard-coded opinionated defaults. We change them by editing the plugin, not by exposing a config surface.
- **A separate auto-brainstormer subagent.** v1 keeps it as a skill with in-context steps. Promote to subagent in v2 once the prompts have stabilized.
- **Replacing `superpowers:brainstorming` for interactive `pick-task`.** Auto-brainstorm exists for the unsupervised path only.

## Architecture

### State machine

```
/goal "<text>"
   │
   ▼
[VALIDATE]  ── rubric fails ──► one-shot pushback to user (or --accept-vague)
   │
   ▼
[CREATE_EPIC_TASK]  Epic E-NNN (kind: goal) + first child task T-MMM created
   │                Epic frontmatter holds rubric, judge_history; task body holds
   │                full goal text and rubric eval result
   ▼
┌──────────────────────────────────────────────────────────────┐
│ AUTO-TASK (per-task lifecycle, runs once per iteration)      │
│                                                              │
│   PICK ─► AUTO_BRAINSTORM ─► WRITE_TESTS ─► IMPLEMENT        │
│            │                                                 │
│            ├─ research (4 sources, parallel Explore agents)  │
│            ├─ draft spec (Opus, in-context)                  │
│            ├─ self-iterate vs /goal rubric (≤3 passes)       │
│            └─ challenger pass (taskmaster:spec-review)       │
│                                                              │
│   IMPLEMENT ─► TEST ─► REVIEW_GATE ─► HANDOVER ─► END_SESSION│
└──────────────────────────────────────────────────────────────┘
   │
   ▼
[GOAL_JUDGE]  ── dispatch taskmaster:goal-judge subagent
   │           ── reads: epic.rubric, goal text, commits, test output, diff,
   │              benchmark numbers, evidence files
   │
   ├── satisfied=true ──► [GOAL_DONE] write goal handover, mark epic done
   │
   └── satisfied=false
        │
        ├── gap_kind="small"      ──► loop back to IMPLEMENT (same task)
        │                              max 3 in-task loops, then escalate to structural
        │
        └── gap_kind="structural" ──► spawn next child task in same epic
                                       new task body = gap_description
                                       loop back to AUTO_BRAINSTORM on new task
                                       max 5 child tasks per goal, then halt
```

For pre-existing `auto T-001` runs (no `/goal`), `GOAL_JUDGE` is **skipped** — the existing terminal stage `END_SESSION` remains the end-of-task. The judge stage activates only when the auto run was started by `/goal` or when the parent epic has `kind: goal`.

### Goal as Epic with `kind: goal`

A `/goal` invocation creates exactly one Epic (kind=goal) and one initial child task. Subsequent judge-rejections of structural-gap kind spawn additional child tasks into the same epic.

Epic frontmatter additions (only meaningful when `kind == "goal"`):

```yaml
---
id: E-014
kind: goal                          # NEW — discriminator
title: Build confetti VFX demo
status: in-progress
created: 2026-05-10T09:14:00Z
goal:                               # NEW — only when kind: goal
  text: |                           # full original goal text
    build a web-based confetti VFX demo, 60fps minimum,
    tests verifying particle count + collision math, serve on localhost:5000
  rubric_eval:                      # auto-brainstorm's eval at /goal time
    concrete_outcome: pass
    bounded_scope: pass
    testable_criteria: pass
    constraints_stated: pass
    tests_planned: pass
    accept_vague: false
  judge_history:                    # appended on each GOAL_JUDGE run
    - iteration: 1
      after_task: T-101
      satisfied: false
      gap_kind: structural
      gap_description: tests pass but no localhost server is running
      ts: 2026-05-10T11:42:00Z
    - iteration: 2
      after_task: T-102
      satisfied: true
      evidence:
        - "60fps measured in T-102 commit a7f2d3"
        - "particle count test passes (commit 8b1e0c)"
        - "localhost:5000 reachable (T-102 README)"
  iteration_budget:
    in_task_loops_used: 0
    in_task_loops_max: 3
    child_tasks_used: 2
    child_tasks_max: 5
---
```

Existing Epic shape (kind=feature, the default) is unchanged — no new fields are required when `kind != "goal"`.

### The /goal rubric

The rubric is the same five checks at three different points in the pipeline:

| Check | At `/goal` boundary | In auto-brainstorm self-iterate | In goal-judge |
|---|---|---|---|
| **Concrete outcome** — single nameable thing being built/changed | Reject if missing | Rewrite if missing | N/A (already locked) |
| **Bounded scope** — specific files, components, or behavior | Reject if missing | Rewrite if missing | Confirm scope held |
| **Testable success criteria** — specific number / output / behavior | Reject if missing | Rewrite if missing | Verify met |
| **Constraints stated** — what NOT to change, libraries to use/avoid | Warn if missing | Add explicit assumptions | Verify not violated |
| **Tests planned** — what verifies done | Warn if missing (auto-task TDD default usually covers) | Generate if missing | Verify present and run |

Pass/warn/reject behavior at the `/goal` boundary:
- **All five pass** → proceed silently.
- **Any warn** → log warning to user, proceed.
- **Any reject** → return one-shot pushback message naming the missing piece. User either supplies it or passes `--accept-vague`.
- **`--accept-vague`** → auto-brainstorm fabricates explicit assumptions to fill rejected slots and surfaces them in the epic's `goal.rubric_eval.assumptions` field, plus inserts them into the goal-judge prompt.

### Auto-brainstorm pipeline (skill, in-context)

`taskmaster:auto-brainstorm` is invoked from `auto-task` Step 2 (SPEC_REVIEW). It returns a finalized spec text that gets written into `tasks/<id>.md` body's `## Spec` section. After this skill returns, `superpowers:writing-plans` runs unchanged to convert the spec into a `## Plan` section.

Phases:

1. **Research (parallel)** — dispatch four `Explore` subagents simultaneously, one per source:
   - **IDEA store**: `backlog_idea_list` filtered by tag/title fuzzy-match on task title; fetch top-N relevant.
   - **Lessons + handovers**: `backlog_lesson_match(task_title, touched_files=anchors)` + `backlog_handover_list(task_id, limit=5)`.
   - **Web search**: `WebSearch` for prior art on the task's surface area (e.g. *"how does Linear handle bulk archive"*). Prompt restricts to credible sources.
   - **Cross-domain inspiration**: WebSearch with a deliberately broadened framing (*"bulk operation patterns in non-software domains"*) — generates 1–3 metaphors to stretch the design space.
   Each subagent returns ≤500 words of distilled findings, not raw search results.

2. **Draft (Opus, in-context)** — single Opus pass synthesizes the research findings + task description + existing project conventions into a candidate spec.

3. **Self-iterate (≤3 passes)** — check the draft against the five-point rubric. For each failing check, regenerate that section. Stop when all five pass or after 3 iterations (escalate to challenger anyway).

4. **Challenger pass** — invoke `taskmaster:spec-review` as a subagent in unattended mode. It returns a list of findings (assumptions, scope drift, edge cases, blast radius). Apply non-controversial findings directly; surface controversial ones inline in the spec body as `> CHALLENGER FLAGGED:` callouts the implementation step can react to.

5. **Commit** — write final spec into `tasks/<id>.md` `## Spec` section. Hand off to `writing-plans` for `## Plan`.

### Goal-judge subagent

`taskmaster:goal-judge` is the plugin's **first dedicated subagent**. Lives at `plugins/taskmaster/agents/goal-judge.md`. Frontmatter and prompt highlights:

```yaml
---
name: goal-judge
description: |
  Adversarial completion-judge for /goal-driven auto-runs. Reads the epic's goal text,
  rubric, commits, test output, diff, and any evidence files; returns a structured
  verdict on whether the goal is satisfied. Read-only — never edits, never commits,
  never mutates backlog state. Use only at the GOAL_JUDGE stage of auto-task.
tools: [Read, Glob, Grep, Bash]   # Bash for running tests/benchmarks; no Edit/Write/MCP
model: opus                        # judgment quality matters more than cost here
---
```

Prompt rules (system prompt, hard-coded):

- **Refuse proxy signals.** "Tests passed once" / "build green" / "no errors logged" / "implementation looks complete" are never sufficient. The verdict requires evidence the *specific* success criterion stated in the goal was met.
- **Run things to verify.** If the goal says "60fps minimum," the judge runs the relevant benchmark itself; it does not accept "the spec said this would hit 60fps" as evidence.
- **Classify gaps deliberately.** A `small` gap is a tweakable miss within current scope (failing assertion, edge case, off-by-one in a number target). A `structural` gap is a missing subsystem, a new requirement that surfaces during implementation, or a scope expansion the current task can't absorb.
- **Cite evidence.** Every `satisfied=true` verdict must list at least one piece of concrete evidence (commit sha, test name + result, benchmark number, file path).

Return shape (the agent emits this as its final message):

```json
{
  "satisfied": false,
  "gap_kind": "structural",
  "gap_description": "Goal specifies serving on localhost:5000; implementation builds the demo but does not start a server. Need a separate task to add the server entrypoint.",
  "evidence_inspected": [
    "tasks/T-101.md (spec mentions server, plan does not)",
    "src/demo/index.html (no embedded server start)",
    "tests/test_demo.py (no test for server reachability)"
  ],
  "iteration": 1,
  "recommended_next_action": "spawn-follow-up-task"
}
```

The outer `auto-task` orchestrator parses this and routes accordingly per the state machine.

### /goal slash command + skill

`taskmaster:goal` is a new skill, invoked by:

- Slash form: `/goal <text>` (also `/goal-status`, `/goal-pause`, `/goal-stop` as aliases for `backlog_auto_*`)
- Natural language: "I want to autopilot building X", "set a goal to Y"

Skill behavior:

1. Parse flags: `--epic <id>` (attach to existing epic instead of creating one — only valid if existing epic is `kind: goal`), `--accept-vague`, `--no-run` (create epic+task but don't fire auto), `--in-task-loops <n>`, `--child-tasks <n>` (override iteration budgets).
2. Run `/goal` rubric validation on the goal text.
3. If validation rejects and no `--accept-vague`, return one-shot pushback to user. **Do not retry, do not improve the goal silently.**
4. Create Epic with `kind: goal`, populate `goal.text`, `goal.rubric_eval`, iteration budgets.
5. Create initial child task: title = first sentence of goal, body = full goal + "(see Epic E-NNN for rubric and judge history)", parent_epic = the new epic, status = todo.
6. Fire `taskmaster:auto-task` with the new task id (unless `--no-run`).
7. Announce: `Goal locked as E-NNN. First task T-MMM dispatched to auto-mode.`

### MCP surface changes

Minimal — most behavior is in skills and the agent. New / modified MCP tools:

| Tool | Change | Purpose |
|---|---|---|
| `backlog_add_epic` | Add `kind` parameter (default `"feature"`) and optional `goal` block | Allows `/goal` skill to create a goal-kind epic in one call |
| `backlog_update_epic` | Accept `goal.judge_history` patch (append-only list) | Goal-judge results write here |
| `backlog_auto_status` | Include `goal_judge_pending: bool` and current iteration counters when run is goal-driven | Lets `/goal-status` show goal-aware output without a separate tool |

No new MCP tools. The auto state machine's `GOAL_JUDGE` stage is internal — it dispatches the agent and writes results via the existing `backlog_update_epic`.

## File change list

```
plugins/taskmaster/
  agents/
    goal-judge.md                          # NEW — first plugin subagent
  skills/
    goal/                                  # NEW
      SKILL.md
      references/rubric.md                 # the /goal rubric, single source of truth
    auto-brainstorm/                       # NEW
      SKILL.md
      references/research-prompts.md       # one prompt template per source
    auto-task/SKILL.md                     # MODIFIED — Step 2 invokes auto-brainstorm;
                                           #            new Step 9 GOAL_JUDGE for goal-kind epics
    spec-review/SKILL.md                   # MODIFIED — add unattended-mode invocation contract
                                           #            (returns findings list, no user prompts)
    taskmaster/SKILL.md                    # MODIFIED — routing row for /goal intents
    start-session/SKILL.md                 # MODIFIED — surface running goals in dashboard

  taskmaster_v3.py                         # MODIFIED — backlog_add_epic kind+goal params;
                                           #            backlog_update_epic judge_history patch;
                                           #            backlog_auto_status goal-aware fields
  tests/
    test_goal_skill.py                     # NEW — rubric validation, epic+task creation
    test_auto_brainstorm.py                # NEW — pipeline integration
    test_goal_judge_agent.py               # NEW — agent prompt regression suite
    test_auto_task_goal_judge_stage.py     # NEW — state machine routing on judge verdict
    test_epic_kind_goal.py                 # NEW — frontmatter round-trip, validators

  viewer/js/screens/kanban.js              # MODIFIED — render goal-kind epics with rubric chip,
                                           #            judge-iteration counter, gap pill on
                                           #            judge-rejected child tasks
  viewer/css/                              # MODIFIED — goal-epic affordances, no left rails

docs/superpowers/specs/
  2026-05-10-auto-brainstorm-goal-design.md   # this file
```

## Validation strategy

- **Rubric validator unit tests.** Feed 20 goal strings (10 good, 5 reject-cases, 5 warn-cases) and assert correct verdict + missing-piece message.
- **Auto-brainstorm pipeline test.** Mock the 4 research subagents (return canned distilled findings); run pipeline against a fixture task; assert spec contains all five rubric sections and at least one cited research source per major decision.
- **Goal-judge prompt regression.** Maintain a fixture set of (epic, commits, test output, diff) → expected verdict pairs. CI runs the agent against each and asserts verdict matches. New fixtures added every time a real run produces a wrong verdict.
- **State machine routing test.** Stub goal-judge to return each verdict shape (`satisfied=true`, `small`, `structural`); assert auto-task transitions correctly (DONE / loop IMPLEMENT / spawn child task) and respects iteration budgets.
- **Iteration budget test.** Force judge to always return `satisfied=false`; assert run halts after max in-task loops + max child tasks; assert halt writes a recovery handover.
- **End-to-end smoke.** One real `/goal` against a tiny example task with a measurable success criterion; verify the goal completes with a non-trivial judge_history.
- **Viewer test.** Snapshot the kanban with one goal-kind epic and one feature-kind epic; assert different chips/pills render, no colored left rails.

## Open questions for the implementation plan

- **Exact rubric prompt wording.** The rubric is the most prompt-engineered surface in this design. Three sites need consistent wording: `/goal` validator, auto-brainstorm self-iteration, goal-judge. Single source: `skills/goal/references/rubric.md`, included in all three. Draft during plan-writing.
- **Auto-brainstorm cross-domain source.** "Cross-domain inspiration" is the most novel and most prone to producing useless output. Open question: does it run by default, or only when the task is flagged as exploratory / design-heavy? Default-off may be safer in v1; revisit after a few real goals run.
- **Goal-judge model selection.** Spec'd as Opus for judgment quality. Open question for the plan: do we want a fallback path (e.g., Sonnet for trivial goals) to control cost, or is "always Opus" the opinionated default? Lean: always Opus, since judge calls are infrequent (1–8 per goal).
- **Iteration budgets.** Spec'd 3 in-task / 5 child tasks. Picked by feel; first real goals will tell us if these are too tight or too loose.
- **Failure recovery.** When the budget is exhausted with `satisfied=false`, what's the recovery state? Probably: write a `context-handoff` handover with the latest gap_description as `next_action`, leave epic status `in-progress`, surface in the dashboard under "stalled goals." Resolve during plan.
- **Worktree behavior.** Auto-task already creates worktrees per task. Goal-driven runs that spawn follow-up tasks — does each child task get its own worktree, or does the entire goal share one? Lean: one worktree per goal, multiple commits per child task. Resolve during plan.
- **Naming.** "Goal-judge" vs "completion-judge" vs "outcome-judge." Sticking with `goal-judge` for now since it's specifically tied to /goal-driven runs.
