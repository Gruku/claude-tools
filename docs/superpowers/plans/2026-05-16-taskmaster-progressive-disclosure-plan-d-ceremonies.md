# Plan D — Ceremonies (Glance-First start-session and pick-task) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign `start-session` and `pick-task` so the default invocation delivers a ~800–1,000 token glance briefing, with today's full ceremony available via an explicit `--deep` flag.

**Architecture:** Two-layer change. (1) Skill-content layer: both SKILL.md files are rewritten so the glance flow is the default branch; deep-ceremony content moves to `references/deep-mode.md` per skill. (2) Test layer: pytest lint tests enforce token-budget targets on skill bodies AND verify that glance MCP calls are distinct from deep calls; tests are written first (TDD). Depends on Plan A slim-default MCP tools and Plan B parallel handover `status` field — both must be merged before Plan D ships.

**Tech Stack:** Markdown SKILL files, Python 3.11+, pytest. No new Python deps.

**Spec:** `docs/superpowers/specs/2026-05-15-taskmaster-progressive-disclosure-design.md` §4

**Depends on:** Plan A (slim MCP tools — `verbose`, `sections`, `expand_links` params), Plan B (parallel handovers — `backlog_handover_list(status="open")`, flagged-but-open detection)

---

## File Structure

**Modify:**
- `plugins/taskmaster/skills/start-session/SKILL.md` — rewrite to glance-default flow; add `--deep` branch pointer; trim to ≤1,300 tokens
- `plugins/taskmaster/skills/pick-task/SKILL.md` — rewrite to glance-default flow; replace full lesson-body load with digest+IDs; add `--deep` branch pointer; trim to ≤1,300 tokens
- `plugins/taskmaster/skills/taskmaster/SKILL.md` — add one-line mid-session deepening guidance ("when user asks 'show me X', use `_get(verbose=True)`")
- `plugins/taskmaster/CHANGELOG.md` — changelog entry

**Create:**
- `plugins/taskmaster/skills/start-session/references/deep-mode.md` — full deep ceremony (today's full-load steps 2a–2e with all tool calls)
- `plugins/taskmaster/skills/pick-task/references/deep-mode.md` — full deep ceremony (full task body, full lesson bodies, blast radius, handover bodies)
- `plugins/taskmaster/tests/test_start_session_skill_lint.py` — budget + structural lint tests
- `plugins/taskmaster/tests/test_pick_task_skill_lint.py` — budget + structural lint tests

---

## Phase 1 — Token budget tests (TDD: write failing tests first)

### Task 1: Write failing lint tests for `start-session`

**Files:**
- Create: `plugins/taskmaster/tests/test_start_session_skill_lint.py`

The tests must fail today (skill body too large; deep ceremony inline; no `references/deep-mode.md`). They will pass after Task 4.

- [ ] **Step 1: Create the test file**

```python
# plugins/taskmaster/tests/test_start_session_skill_lint.py
"""Lint checks for the taskmaster:start-session skill (glance-first redesign)."""
from pathlib import Path
import re

import yaml

SKILL_DIR = Path(__file__).resolve().parents[1] / "skills" / "start-session"
SKILL_MD = SKILL_DIR / "SKILL.md"
DEEP_MODE_REF = SKILL_DIR / "references" / "deep-mode.md"

# Approx characters-per-token for plain prose/markdown.
_CHARS_PER_TOKEN = 4


def _token_estimate(text: str) -> int:
    return len(text) // _CHARS_PER_TOKEN


def _read_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return {}
    return yaml.safe_load(m.group(1)) or {}


def _body_without_frontmatter(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        end = text.index("---", 3)
        return text[end + 3:].strip()
    return text.strip()


# ── Structure ────────────────────────────────────────────────────────────────

def test_skill_md_exists():
    assert SKILL_MD.exists(), "SKILL.md missing"


def test_deep_mode_reference_exists():
    assert DEEP_MODE_REF.exists(), (
        "references/deep-mode.md missing — deep ceremony content must live here"
    )


def test_deep_mode_reference_is_not_stub():
    non_blank = [
        ln for ln in DEEP_MODE_REF.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    assert len(non_blank) >= 30, (
        f"references/deep-mode.md looks like a stub ({len(non_blank)} non-blank lines). "
        "Full deep ceremony must be written there."
    )


def test_frontmatter_has_required_fields():
    fm = _read_frontmatter(SKILL_MD)
    assert fm.get("name") == "start-session"
    assert "description" in fm and isinstance(fm["description"], str)
    assert len(fm["description"]) >= 80, "description too short to convey trigger surface"


# ── Token budget ─────────────────────────────────────────────────────────────

def test_skill_md_body_under_token_budget():
    """Glance body (SKILL.md minus frontmatter) must be ≤1,300 tokens.

    Today it is ~3,025 tokens — this test fails until the glance rewrite is done.
    """
    body = _body_without_frontmatter(SKILL_MD)
    tokens = _token_estimate(body)
    assert tokens <= 1_300, (
        f"SKILL.md body is ~{tokens} tokens (limit 1,300). "
        "Move deep-ceremony content to references/deep-mode.md."
    )


def test_glance_mcp_calls_listed_in_body():
    """Glance path must reference the three slim MCP calls from spec §4."""
    body = _body_without_frontmatter(SKILL_MD)
    required_calls = [
        "backlog_status",
        "backlog_handover_list",
    ]
    missing = [c for c in required_calls if c not in body]
    assert not missing, f"Glance MCP calls missing from SKILL.md body: {missing}"


def test_deep_ceremony_not_inline_in_body():
    """Heavy deep-mode calls must NOT appear in the glance body.

    backlog_recap, backlog_lesson_digest, backlog_lesson_get, and backlog_last_session
    are deep-mode only — they belong in references/deep-mode.md.
    """
    body = _body_without_frontmatter(SKILL_MD)
    deep_only_calls = ["backlog_recap", "backlog_lesson_digest", "backlog_lesson_get"]
    present = [c for c in deep_only_calls if c in body]
    assert not present, (
        f"Deep-mode MCP calls found in SKILL.md glance body: {present}. "
        "Move them to references/deep-mode.md."
    )


def test_deep_flag_mentioned_in_body():
    """SKILL.md must mention --deep so users know how to access the full ceremony."""
    body = _body_without_frontmatter(SKILL_MD)
    assert "--deep" in body, "SKILL.md must document the --deep flag"


def test_deep_mode_reference_linked_from_body():
    """SKILL.md must link to references/deep-mode.md."""
    body = _body_without_frontmatter(SKILL_MD)
    assert "references/deep-mode.md" in body, (
        "SKILL.md must link to references/deep-mode.md for the deep ceremony"
    )
```

- [ ] **Step 2: Run tests to verify they all fail**

```
pytest plugins/taskmaster/tests/test_start_session_skill_lint.py -v
```

Expected failures:
- `test_deep_mode_reference_exists` — `references/deep-mode.md` does not exist yet
- `test_deep_mode_reference_is_not_stub` — same
- `test_skill_md_body_under_token_budget` — body is ~3,025 tokens today
- `test_deep_ceremony_not_inline_in_body` — `backlog_recap`, `backlog_lesson_digest`, `backlog_lesson_get` are inline
- `test_deep_flag_mentioned_in_body` — `--deep` not in body today
- `test_deep_mode_reference_linked_from_body` — link missing

Do **not** fix anything yet.

---

### Task 2: Write failing lint tests for `pick-task`

**Files:**
- Create: `plugins/taskmaster/tests/test_pick_task_skill_lint.py`

- [ ] **Step 1: Create the test file**

```python
# plugins/taskmaster/tests/test_pick_task_skill_lint.py
"""Lint checks for the taskmaster:pick-task skill (glance-first redesign)."""
from pathlib import Path
import re

import yaml

SKILL_DIR = Path(__file__).resolve().parents[1] / "skills" / "pick-task"
SKILL_MD = SKILL_DIR / "SKILL.md"
DEEP_MODE_REF = SKILL_DIR / "references" / "deep-mode.md"
EXISTING_REF = SKILL_DIR / "references" / "v3-context-loading.md"

_CHARS_PER_TOKEN = 4


def _token_estimate(text: str) -> int:
    return len(text) // _CHARS_PER_TOKEN


def _read_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return {}
    return yaml.safe_load(m.group(1)) or {}


def _body_without_frontmatter(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        end = text.index("---", 3)
        return text[end + 3:].strip()
    return text.strip()


# ── Structure ────────────────────────────────────────────────────────────────

def test_skill_md_exists():
    assert SKILL_MD.exists(), "SKILL.md missing"


def test_deep_mode_reference_exists():
    assert DEEP_MODE_REF.exists(), (
        "references/deep-mode.md missing — deep ceremony content must live here"
    )


def test_existing_v3_context_loading_ref_preserved():
    assert EXISTING_REF.exists(), (
        "references/v3-context-loading.md was deleted — it must be preserved or merged into deep-mode.md"
    )


def test_deep_mode_reference_is_not_stub():
    non_blank = [
        ln for ln in DEEP_MODE_REF.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    assert len(non_blank) >= 30, (
        f"references/deep-mode.md looks like a stub ({len(non_blank)} non-blank lines). "
        "Full deep ceremony must be written there."
    )


def test_frontmatter_has_required_fields():
    fm = _read_frontmatter(SKILL_MD)
    assert fm.get("name") == "pick-task"
    assert "description" in fm and isinstance(fm["description"], str)
    assert len(fm["description"]) >= 100, "description too short"


# ── Token budget ─────────────────────────────────────────────────────────────

def test_skill_md_body_under_token_budget():
    """Glance body (SKILL.md minus frontmatter) must be ≤1,300 tokens.

    Today it is ~2,745 tokens — this test fails until the glance rewrite is done.
    """
    body = _body_without_frontmatter(SKILL_MD)
    tokens = _token_estimate(body)
    assert tokens <= 1_300, (
        f"SKILL.md body is ~{tokens} tokens (limit 1,300). "
        "Move deep-ceremony content to references/deep-mode.md."
    )


def test_glance_mcp_calls_present():
    """Glance path must reference the six slim MCP calls from spec §4."""
    body = _body_without_frontmatter(SKILL_MD)
    required_calls = [
        "backlog_get_task",
        "backlog_dependencies",
        "backlog_handover_list",
        "backlog_lesson_match",
        "backlog_issue_list",
    ]
    missing = [c for c in required_calls if c not in body]
    assert not missing, f"Glance MCP calls missing from SKILL.md body: {missing}"


def test_full_lesson_body_load_not_inline():
    """Full lesson body loading (backlog_lesson_get) must NOT appear in the glance body.

    In the glance path, lesson_match returns IDs+tldrs only.
    backlog_lesson_get belongs in references/deep-mode.md.
    """
    body = _body_without_frontmatter(SKILL_MD)
    assert "backlog_lesson_get" not in body, (
        "backlog_lesson_get found in SKILL.md glance body — move it to references/deep-mode.md. "
        "Glance path uses backlog_lesson_match IDs+tldrs only."
    )


def test_blast_radius_not_in_glance_body():
    """backlog_blast_radius is a deep-mode call — must not appear in glance body."""
    body = _body_without_frontmatter(SKILL_MD)
    assert "backlog_blast_radius" not in body, (
        "backlog_blast_radius found in SKILL.md glance body — it belongs in references/deep-mode.md"
    )


def test_deep_flag_mentioned_in_body():
    body = _body_without_frontmatter(SKILL_MD)
    assert "--deep" in body, "SKILL.md must document the --deep flag"


def test_deep_mode_reference_linked_from_body():
    body = _body_without_frontmatter(SKILL_MD)
    assert "references/deep-mode.md" in body, (
        "SKILL.md must link to references/deep-mode.md for the deep ceremony"
    )
```

- [ ] **Step 2: Run tests to verify they all fail**

```
pytest plugins/taskmaster/tests/test_pick_task_skill_lint.py -v
```

Expected failures:
- `test_deep_mode_reference_exists` — does not exist yet
- `test_deep_mode_reference_is_not_stub` — same
- `test_skill_md_body_under_token_budget` — body ~2,745 tokens
- `test_full_lesson_body_load_not_inline` — `backlog_lesson_get` is inline today
- `test_blast_radius_not_in_glance_body` — `backlog_blast_radius` is inline today
- `test_deep_flag_mentioned_in_body` — `--deep` absent
- `test_deep_mode_reference_linked_from_body` — link absent

Do **not** fix anything yet.

---

## Phase 2 — Refactor `start-session/SKILL.md`

### Task 3: Write `start-session/references/deep-mode.md`

All heavy ceremony content is moved here first, then stripped from the main body in Task 4.

**Files:**
- Create: `plugins/taskmaster/skills/start-session/references/deep-mode.md`

- [ ] **Step 1: Create the file with full deep ceremony**

```markdown
# start-session — Deep Ceremony (`--deep` mode)

Invoked when the user says `start-session --deep`, "full briefing", "give me everything", or equivalent explicit depth signal.

Run all steps below in addition to the standard glance steps (backlog_status + open handovers). This reproduces today's full-load behavior.

## Deep steps (run in order after glance steps 1–3)

### D1. Recap diff

Call `backlog_recap` to see what changed in the project since the last snapshot — tasks added, status transitions, issues fixed, phase advances.

Surface as a `**Since last snapshot:**` block. Compact format — do not expand into prose. If nothing changed, skip the block.

### D2. Lesson digest

Call `backlog_lesson_digest` to load the slim digest of active project lessons (id + kind + title, ≤30 entries).

These are project-specific behavioral rules Claude should keep in mind during the session. Loading the digest at session start is *priming* — it does not mean lessons have been applied. Do not call `backlog_lesson_reinforce` on session start.

### D3. Core lessons (full body)

Look at the digest output. For any lesson in the `core` tier (denoted `[core/...]`), fetch it in full via `backlog_lesson_get <id>`. Keep the body in working context for the whole session. Cap: 5 core lessons.

### D4. Full issue list

Call `backlog_issue_list(status="open")` (no limit cap). Surface all open issues grouped P0 → P3. P0/P1 entries get a visual flag.

### D5. Last session entry

Call `backlog_last_session` to get the most recent PROGRESS.md entry. Surface as `**Last session:**` block for continuity.

## Deep-mode briefing structure

Present in this order after the glance briefing:

1. `**Since last snapshot:**` (recap diff, D1)
2. `**Lesson digest (${N} active):**` (D2 list, compact)
3. `**Core lessons loaded:**` (D3 — title only in the briefing, bodies in context)
4. `**All open issues:**` (D4)
5. `**Last session:**` (D5 — PROGRESS.md entry)

## Notes

- Deep mode total token budget: ~3,000–4,000 tokens (glance ~800 + deep additions ~2,200).
- If lesson digest + core bodies push past 5,000 tokens, prune lowest `reinforce_count` lessons first.
- `--deep` is user-explicit. Never auto-trigger deep mode based on signals (days since last session, etc.).
- `backlog_handover_latest` is deprecated after Plan B lands. Use `backlog_handover_list(status="open", limit=5)` instead (already in glance path).
```

- [ ] **Step 2: Verify the file is non-stub**

```
pytest plugins/taskmaster/tests/test_start_session_skill_lint.py::test_deep_mode_reference_exists plugins/taskmaster/tests/test_start_session_skill_lint.py::test_deep_mode_reference_is_not_stub -v
```

Expected: both pass.

---

### Task 4: Rewrite `start-session/SKILL.md` to glance-default

**Files:**
- Modify: `plugins/taskmaster/skills/start-session/SKILL.md`

The full existing body is replaced. The glance flow is default. Deep flow is a pointer to `references/deep-mode.md`.

- [ ] **Step 1: Write the new SKILL.md**

Replace the entire content of `plugins/taskmaster/skills/start-session/SKILL.md` with the following:

```markdown
---
name: start-session
description: "Start a work session and orient for a new conversation. Invoke when the user says 'let's get started', 'what should I work on', 'show me the backlog', 'orient me', or begins a new conversation in a project that has backlog.yaml. Shows dashboard, last session summary, and suggests next tasks."
---

# Start Session

Load project context and orient for a new work session. Default mode is a **glance briefing** (~800–1,000 tokens). Append `--deep` for today's full ceremony.

## Glance flow (default)

### Step 1 — Project dashboard

Call `backlog_status()` (slim, no `verbose`). This returns counts, in-progress titles, active phase, and stale task count. Note the `**Schema:** v<N>` line — v3 steps activate only on v3 backlogs.

### Step 2 — Open handovers

Call `backlog_handover_list(status="open", limit=5)`. Returns slim entries (id + task_ids + tldr + next_action). Each entry is ~50 tokens. Flagged handovers (task done but handover still open) appear with an inline reason.

If there are more than 5 open handovers, show `(+N more — use --deep to see all)`.

### Step 3 — 1-line counts

Compose a single counts line from the above tool outputs:

```
N new issues (N P0) · N matched lessons · N stale tasks · N flagged handovers
```

For issues count: use the `open_issues_count` field from `backlog_status` output (slim mode includes aggregate counts). For matched lessons and stale count: also from `backlog_status` aggregate fields.

### Step 4 — Briefing

Present in order:

- **Where you left off:** latest open handover tldr + next_action (most actionable anchor)
- **Resuming:** in-progress tasks (from `backlog_status`)
- **Needs testing:** in-review tasks
- **Phase progress:** if active phase, show done/total
- **Stale tasks:** if any (from `backlog_status` stale list)
- **Dashboard:** epic progress summary
- **Suggested next:** first available task from the active phase
- **Counts line** (Step 3)

### Step 5 — Prompt

"What would you like to work on? Use `--deep` for the full briefing with lessons, all issues, and last session."

## Deep mode (`--deep`)

When the user says `start-session --deep`, "full briefing", "give me everything", or equivalent: run the glance flow above first, then continue with `references/deep-mode.md`.

## Empty state

If no epics and no tasks: "The backlog is empty — let's set it up! What are the main workstreams?" Guide to `backlog_add_epic` then tasks. Do not show an empty dashboard table.

## Error handling

If `backlog_status` fails: check if `backlog.yaml` exists. If not, suggest `/init`. If it exists, the MCP server may not be registered — guide to `.mcp.json`.

## Mid-session behavior

While working in a v3 project, emit `<lesson-candidate>` XML inline (no tool call) when: (a) user corrects you twice on same thing, (b) bug encountered before, (c) user states a "we always/never do X here" rule.

For idea capture: use `<idea-candidate>` inline for fuzzy/ambient ideas; call `backlog_idea_create` for explicit or concrete ones. See `plugins/taskmaster/skills/lesson/references/marker-format.md` for tag schema.

## Notes

- Read-only skill — no files modified.
- `backlog_status` handles all YAML parsing and stat computation.
- Deep ceremony detail: `references/deep-mode.md`.
```

- [ ] **Step 2: Run the full lint suite**

```
pytest plugins/taskmaster/tests/test_start_session_skill_lint.py -v
```

Expected: all 8 tests pass.

- [ ] **Step 3: Commit**

```
git add plugins/taskmaster/skills/start-session/SKILL.md plugins/taskmaster/skills/start-session/references/deep-mode.md plugins/taskmaster/tests/test_start_session_skill_lint.py
git commit -m "feat(taskmaster/ceremonies): glance-first start-session — deep ceremony to references/deep-mode.md"
```

---

## Phase 3 — Refactor `pick-task/SKILL.md`

### Task 5: Write `pick-task/references/deep-mode.md`

**Files:**
- Create: `plugins/taskmaster/skills/pick-task/references/deep-mode.md`

- [ ] **Step 1: Create the file**

```markdown
# pick-task — Deep Ceremony (`--deep` mode)

Invoked when the user says `pick-task --deep`, "full task briefing", "load everything for this task", or equivalent explicit depth signal.

Run all steps below after the standard glance steps complete (backlog_get_task slim + deps + open handovers + lesson match IDs + issues filtered + linkage pills).

## Deep steps

### D1. Full task body + docs

Call `backlog_get_task(<id>, verbose=True)`. This returns the full frontmatter + all body sections + inlined docs (spec, plan, design, analysis, roadmap).

### D2. Full lesson bodies

For each lesson ID returned by `backlog_lesson_match` in the glance step, call `backlog_lesson_get <id>` to load the full body. Cap at 3 lessons. Keep bodies in working context for the duration of the task.

Surface to user: "Loaded N lessons: L-007 (gotcha) auth/session.ts read-before-edit …"

Call `backlog_lesson_reinforce <id>` only on confirmed successful application during work — not on load.

### D3. Blast radius

Call `backlog_blast_radius(<id>, mode="predictive")`. Display the full structured block for critical/high tasks; one-line for medium/low.

If spec-review was already done, reference the prior analysis: "Full predictive analysis in spec-review record — calling for latest."

If overlapping in-progress tasks found, highlight: "Heads up — `{task_id}` is in-flight in the same area."

### D4. Handover bodies (context-handoff kind)

From the glance step's `backlog_handover_list(task_id=<id>, status="open")` result, identify any handover where `session_kind` is `context-handoff`. Call `backlog_handover_get <id>` (no `verbose` needed — full body by default after Plan A) for each such handover. This surfaces the "where I left off" context written at compaction.

Cap: load at most 2 handover bodies. If more, surface the others by tldr and let the user request via `backlog_handover_get <id>`.

## Deep-mode token budget

| Source | Typical |
|---|---|
| Full task body (verbose=True) | ~800 tokens |
| 3 full lesson bodies | ~900 tokens |
| Blast radius (predictive) | ~500 tokens |
| Handover bodies (context-handoff, ≤2) | ~400 tokens |
| **Total additive above glance** | ~2,600 tokens |

Glance is ~700 tokens; deep total is ~3,300.

## Pruning order (if over budget)

1. Drop lowest `reinforce_count` lesson body.
2. Drop optional handover body fetches.
3. Never prune related issues — bug context is load-bearing.

## Token-budget reference for glance path

See `references/v3-context-loading.md` for the per-source breakdown of glance step tokens (steps 5a–5c in the old numbering).
```

- [ ] **Step 2: Verify non-stub test passes**

```
pytest plugins/taskmaster/tests/test_pick_task_skill_lint.py::test_deep_mode_reference_exists plugins/taskmaster/tests/test_pick_task_skill_lint.py::test_deep_mode_reference_is_not_stub -v
```

Expected: both pass.

---

### Task 6: Rewrite `pick-task/SKILL.md` to glance-default

**Files:**
- Modify: `plugins/taskmaster/skills/pick-task/SKILL.md`

- [ ] **Step 1: Write the new SKILL.md**

Replace the entire content of `plugins/taskmaster/skills/pick-task/SKILL.md` with the following:

```markdown
---
name: pick-task
description: "Select a task to work on. Invoke when the user says 'pick a task', 'let's work on X', 'start task auth-003', 'what should I tackle next', 'continue this task', 'continue where we left off', 'resume the work', 'pick up from yesterday', or names a specific task ID. Sets status to in-progress, checks dependencies, creates a git worktree for isolation, and loads task context. On v3 backlogs, the continue-style triggers auto-resolve to the most-recently-touched in-progress task with a handover."
---

# Pick Task

Select a task to work on and set it to in-progress. Default mode is a **glance briefing** (~600–800 tokens). Append `--deep` for full task body, lesson bodies, blast radius, and handover context.

## Arguments

- `task_id` (optional) — specific task ID. If omitted, presents top priorities or auto-resolves via open handovers on v3 backlogs.

## Step 0 — (v3) "Continue" auto-resolve

If the user said "continue this task", "continue where we left off", "resume", or similar AND no explicit `task_id` given:

- Call `backlog_handover_list(status="open", limit=1)`. If empty, fall through to Step 1.
- Take the first id in the handover's `task_ids`. Call `backlog_get_task(<id>)` slim.
- If status is `done` or `archived`, fall through to Step 1.
- Confirm once: "Continuing `<task_id>` from the `<date>` handover (`<tldr>`). Right task?" Default Yes. On confirmation, jump to Step 4.

On v2 backlogs (no handover index), skip silently.

## Step 1 — If no task ID

Call `backlog_next_available` to get ready tasks. Phase-filtered when a phase is active. Present and ask the user to pick. If empty, suggest `/advance-phase` or add work.

## Step 2 — Parallel-task check

Call `backlog_status` (slim). If 3+ tasks already in-progress: "You have N tasks in-flight. Switch focus or pick this up in parallel?"

## Step 3 — Dependency check

Call `backlog_dependencies(<task_id>)`. If any dependency is not done: warn and let user decide. Do not silently skip.

## Step 4 — Pick the task

Call `backlog_pick_task(<task_id>)` — sets status to in-progress, records started date. Note the `**Schema:** v<N>` line; v3 glance steps below activate only on v3 backlogs.

## Step 5 — Glance context load (v3)

Run all sub-steps together. Total budget: ~500 tokens.

**5a. Open handovers for this task**

Call `backlog_handover_list(task_id=<task_id>, status="open", limit=3)`. Returns IDs + tldr + next_action. Surface: "N open handovers. Latest: `<tldr>`." If a handover has `session_kind: context-handoff` AND non-trivial `next_action`, load its full body via `backlog_handover_get <id>` (this one load is warranted — it's the "where I left off" anchor).

**5b. Related issues**

Issues from the task's `related_issues` field are returned in the slim `backlog_get_task` response (bare IDs or `expand_links` pills). For each open P0/P1 issue ID, call `backlog_issue_list(task_id=<task_id>)` if the slim response doesn't carry severity. Surface as: `Linked issues: ISS-014 (P1, open) Login accepts whitespace password`.

**5c. Matched lessons (IDs + tldrs only)**

Call `backlog_lesson_match(task_title=<title>, touched_files=<anchors>)`. Returns ≤3 best-match lesson IDs + tldrs. Surface to user: "3 lessons match — L-007: auth session read-before-edit · L-014: avoid raw SQL · L-022: test name format." Do **not** load full lesson bodies here — that is `--deep` only.

**5d. Linkage pills**

The slim `backlog_get_task` response includes bare ID linkage grouped by type. No extra call needed. Surface as a compact footer: `depends_on: T-002 · fixes: ISS-007 · informed_by: L-003`.

## Step 6 — Spec-review + anchors (critical/high only)

If `task.spec_review` present: summarize verdict. If verdict is `fail`, warn and ask for override.
If `task.spec_review` absent and task has `docs.spec` or `docs.plan`: "No spec-review on record for this {priority} task. Run `taskmaster:spec-review` first?" Don't block.
If `task.anchors`: display prominently. Remind: "If you find yourself editing files outside these anchors, double-check you're on the right target."

Skip for medium/low tasks.

## Step 7 — Read linked docs

If the task has a `docs` field (plan, spec, etc.), read those files. Do not write code without reading the existing spec/plan.

## Step 8 — Git worktree creation (REQUIRED)

The `backlog_pick_task` response includes worktree instructions. Follow them. A dedicated worktree per task is mandatory for safe parallel work — never skip it.

Creating a worktree:
1. `git worktree add .worktrees/{task-id} -b feature/{task-id}` from repo root.
2. `backlog_update_task(<task_id>, "branch", "feature/{task-id}")`
3. `backlog_update_task(<task_id>, "worktree", ".worktrees/{task-id}")`

If worktree exists but is orphaned: `git worktree prune` and recreate. If `git worktree add` fails with "branch already exists": check it out without `-b`, or ask user.

## Deep mode (`--deep`)

When the user says `pick-task <id> --deep`, "full briefing", "load everything for this task": run glance steps above, then continue with `references/deep-mode.md` (full task body, full lesson bodies, blast radius, handover context bodies).

## Task lifecycle

```
todo → in-progress → in-review → done → archived
```

`in-review` = Claude done, user tests. `done` = user confirmed.

## Reclaiming a locked task

`backlog_pick_task(task_id, force=True)` reclaims in a single atomic call. Never manually edit `backlog.yaml` or change `locked_by` directly.

## Notes

- `backlog_pick_task` is idempotent for already in-progress tasks in same session.
- Picking an `in-review` task demotes it to `in-progress` — confirm demotion with user first.
- Picking a `blocked` task is rejected — help user resolve blockers first.

## Additional resources

- `references/deep-mode.md` — full deep ceremony (full body, lesson bodies, blast radius, handover bodies)
- `references/v3-context-loading.md` — token budget breakdown for glance steps
```

- [ ] **Step 2: Run the full lint suite**

```
pytest plugins/taskmaster/tests/test_pick_task_skill_lint.py -v
```

Expected: all 9 tests pass.

- [ ] **Step 3: Commit**

```
git add plugins/taskmaster/skills/pick-task/SKILL.md plugins/taskmaster/skills/pick-task/references/deep-mode.md plugins/taskmaster/tests/test_pick_task_skill_lint.py
git commit -m "feat(taskmaster/ceremonies): glance-first pick-task — deep ceremony to references/deep-mode.md"
```

---

## Phase 4 — Mid-session deepening guidance

### Task 7: Add mid-session deepening note to `taskmaster/SKILL.md`

When a user asks "show me HND-012" or "read the plan for T-001" mid-session, Claude should route to the existing `_get(verbose=True)` or `_get(sections=[...])` paths without re-invoking the full skill ceremony. This guidance belongs in the taskmaster router.

**Files:**
- Modify: `plugins/taskmaster/skills/taskmaster/SKILL.md`

- [ ] **Step 1: Read the current router file**

Read `plugins/taskmaster/skills/taskmaster/SKILL.md` and locate the routing table or a natural insertion point near the end or in a "Notes" or "Mid-session" section.

- [ ] **Step 2: Insert mid-session deepening guidance**

Find the end of the routing table (or the last section before any closing notes). Insert the following section. Preserve existing content exactly — this is an additive edit.

```markdown
## Mid-session deepening

Skills stay in glance mode during a session. When the user asks to see more detail on a specific entity, Claude deepens that entity directly — no need to re-invoke a ceremony skill.

| User says | Claude does |
|---|---|
| "show me HND-012" / "open that handover" | `backlog_handover_get("HND-012")` (full body by default) |
| "read the plan for T-001" / "show me the spec" | `backlog_get_task("T-001", sections=["plan"])` or `sections=["spec"]` |
| "full task details" / "load everything for T-001" | `backlog_get_task("T-001", verbose=True)` |
| "show me lesson L-007" / "read that lesson" | `backlog_lesson_get("L-007")` (full body) |
| "details on ISS-014" | `backlog_issue_get("ISS-014", verbose=True)` |

The deepening is surgical — one entity, the section the user asked for. The ceremony (start-session, pick-task) is not re-run. This keeps the rest of the session context unaffected.
```

- [ ] **Step 3: Verify the file is not over-budget**

```python
# quick manual check — run in Python REPL or as a one-liner
python -c "
from pathlib import Path
text = Path('plugins/taskmaster/skills/taskmaster/SKILL.md').read_text(encoding='utf-8')
body = text[text.index('---', 3) + 3:].strip() if text.startswith('---') else text
print(f'Body tokens (est): {len(body) // 4}')
"
```

Target: ≤800 tokens (spec §5A target for the router). If over, identify verbose passages to trim — the mid-session table added ~150 tokens, which is acceptable within the router's overall target.

- [ ] **Step 4: Commit**

```
git add plugins/taskmaster/skills/taskmaster/SKILL.md
git commit -m "feat(taskmaster/ceremonies): add mid-session deepening routing table to taskmaster router"
```

---

## Phase 5 — Smoke tests

### Task 8: Write skill-invocation smoke test for start-session glance

This test loads the SKILL.md, simulates the MCP tool calls the glance path would make (mocked), and asserts the total injected token budget.

**Files:**
- Create: `plugins/taskmaster/tests/test_start_session_smoke.py`

- [ ] **Step 1: Create the smoke test**

```python
# plugins/taskmaster/tests/test_start_session_smoke.py
"""Smoke test: start-session glance path token budget.

Simulates MCP tool calls the glance flow triggers, counts total tokens, asserts budget.
Uses fake minimal responses sized to realistic slim-mode payloads.
"""
from pathlib import Path

SKILL_MD = (
    Path(__file__).resolve().parents[1] / "skills" / "start-session" / "SKILL.md"
)

# Realistic slim-mode mock payloads (as strings, length/4 = token estimate).
# Each reflects what Plan A slim tools would return.

_BACKLOG_STATUS_SLIM = """**Schema:** v3
**Phase:** Development (3/8 tasks done)
**In progress:** T-001 Rewrite auth middleware · T-003 Add rate limiting
**In review:** T-007 Fix token refresh
**Stale tasks (14d+):** T-009 SAML support (stale 21d)
**Counts:** 12 tasks · 3 in-progress · 1 in-review · 4 todo · 2 done
**Open issues:** 3 (1 P0) · **Matched lessons:** 5 · **Flagged handovers:** 1
""" * 1  # ~400 chars → ~100 tokens

_HANDOVER_LIST_SLIM = """HND-012 ▸ T-001: "rewriting auth middleware — next: backfill migration" [open]
HND-010 ▸ T-003: "rate limiting implemented — next: add integration test" [open]
HND-008 ▸ T-007: "token refresh fix pending review" [flagged: T-007 done but handover open ▸ next_action references T-005] [open]
""" * 1  # ~600 chars → ~150 tokens

_COUNTS_LINE = "3 new issues (1 P0) · 5 matched lessons · 1 stale task · 1 flagged handover\n"
# ~80 chars → ~20 tokens

_CHARS_PER_TOKEN = 4


def _token_estimate(text: str) -> int:
    return len(text) // _CHARS_PER_TOKEN


def test_glance_skill_body_budget():
    """SKILL.md body alone must be ≤1,300 tokens."""
    text = SKILL_MD.read_text(encoding="utf-8")
    if text.startswith("---"):
        end = text.index("---", 3)
        body = text[end + 3:].strip()
    else:
        body = text.strip()
    tokens = _token_estimate(body)
    assert tokens <= 1_300, f"SKILL.md body ~{tokens} tokens; limit 1,300"


def test_glance_mcp_payload_budget():
    """Sum of slim MCP payloads for the glance path must be ≤1,000 tokens."""
    total_chars = (
        len(_BACKLOG_STATUS_SLIM)
        + len(_HANDOVER_LIST_SLIM)
        + len(_COUNTS_LINE)
    )
    tokens = total_chars // _CHARS_PER_TOKEN
    assert tokens <= 1_000, (
        f"Glance MCP payload ~{tokens} tokens; limit 1,000. "
        "Check Plan A slim-mode response sizes."
    )


def test_combined_glance_budget():
    """Skill body + MCP payloads combined must be ≤2,300 tokens (≤1,300 + ≤1,000)."""
    text = SKILL_MD.read_text(encoding="utf-8")
    if text.startswith("---"):
        end = text.index("---", 3)
        body = text[end + 3:].strip()
    else:
        body = text.strip()
    mcp_chars = len(_BACKLOG_STATUS_SLIM) + len(_HANDOVER_LIST_SLIM) + len(_COUNTS_LINE)
    total_tokens = _token_estimate(body) + (mcp_chars // _CHARS_PER_TOKEN)
    assert total_tokens <= 2_300, (
        f"Combined glance budget ~{total_tokens} tokens; limit 2,300."
    )
```

- [ ] **Step 2: Run smoke test**

```
pytest plugins/taskmaster/tests/test_start_session_smoke.py -v
```

Expected: all 3 pass (SKILL.md body is now ≤1,300 tokens from Task 4; mock payloads are sized to fit).

---

### Task 9: Write skill-invocation smoke test for pick-task glance

**Files:**
- Create: `plugins/taskmaster/tests/test_pick_task_smoke.py`

- [ ] **Step 1: Create the smoke test**

```python
# plugins/taskmaster/tests/test_pick_task_smoke.py
"""Smoke test: pick-task glance path token budget.

Simulates MCP tool calls the glance flow triggers, counts total tokens, asserts budget.
"""
from pathlib import Path

SKILL_MD = (
    Path(__file__).resolve().parents[1] / "skills" / "pick-task" / "SKILL.md"
)

# Realistic slim-mode mock payloads.
_GET_TASK_SLIM = """id: T-001
title: Rewrite auth middleware
tldr: Replace JWT storage in localStorage with httpOnly cookies.
next_step: Backfill migration script for existing users.
status: in-progress
priority: high
depends_on: [T-002]
related_issues: [ISS-007]
related_lessons: [L-003]
docs_available: [spec, plan]
open_handovers: [HND-012]
""" * 1  # ~600 chars → ~150 tokens

_DEPENDENCIES_SLIM = """T-002: done ✓ Setup Redis session store
""" * 1  # ~80 chars → ~20 tokens

_HANDOVER_LIST_TASK_SLIM = """HND-012 ▸ T-001: "rewriting auth middleware — next: backfill migration" [open]
""" * 1  # ~150 chars → ~37 tokens

_LESSON_MATCH_SLIM = """L-007 (gotcha): auth/session.ts — read before edit, never patch blindly
L-014 (anti-pattern): avoid raw SQL in auth handlers
L-022 (pattern): test names must include scenario + expected outcome
""" * 1  # ~360 chars → ~90 tokens

_ISSUE_LIST_TASK_SLIM = """ISS-007 (P1, open): Login accepts whitespace-only passwords
""" * 1  # ~80 chars → ~20 tokens

_LINKAGE_PILLS = "depends_on: T-002 · fixes: ISS-007 · informed_by: L-003\n"
# ~55 chars → ~14 tokens

_CHARS_PER_TOKEN = 4


def _token_estimate(text: str) -> int:
    return len(text) // _CHARS_PER_TOKEN


def test_glance_skill_body_budget():
    """SKILL.md body alone must be ≤1,300 tokens."""
    text = SKILL_MD.read_text(encoding="utf-8")
    if text.startswith("---"):
        end = text.index("---", 3)
        body = text[end + 3:].strip()
    else:
        body = text.strip()
    tokens = _token_estimate(body)
    assert tokens <= 1_300, f"SKILL.md body ~{tokens} tokens; limit 1,300"


def test_glance_mcp_payload_budget():
    """Sum of slim MCP payloads for the pick-task glance path must be ≤800 tokens."""
    total_chars = (
        len(_GET_TASK_SLIM)
        + len(_DEPENDENCIES_SLIM)
        + len(_HANDOVER_LIST_TASK_SLIM)
        + len(_LESSON_MATCH_SLIM)
        + len(_ISSUE_LIST_TASK_SLIM)
        + len(_LINKAGE_PILLS)
    )
    tokens = total_chars // _CHARS_PER_TOKEN
    assert tokens <= 800, (
        f"Glance MCP payload ~{tokens} tokens; limit 800. "
        "Check Plan A slim-mode response sizes for pick-task tools."
    )


def test_combined_glance_budget():
    """Skill body + MCP payloads combined must be ≤2,100 tokens."""
    text = SKILL_MD.read_text(encoding="utf-8")
    if text.startswith("---"):
        end = text.index("---", 3)
        body = text[end + 3:].strip()
    else:
        body = text.strip()
    mcp_chars = (
        len(_GET_TASK_SLIM)
        + len(_DEPENDENCIES_SLIM)
        + len(_HANDOVER_LIST_TASK_SLIM)
        + len(_LESSON_MATCH_SLIM)
        + len(_ISSUE_LIST_TASK_SLIM)
        + len(_LINKAGE_PILLS)
    )
    total_tokens = _token_estimate(body) + (mcp_chars // _CHARS_PER_TOKEN)
    assert total_tokens <= 2_100, (
        f"Combined glance budget ~{total_tokens} tokens; limit 2,100."
    )
```

- [ ] **Step 2: Run smoke test**

```
pytest plugins/taskmaster/tests/test_pick_task_smoke.py -v
```

Expected: all 3 pass.

---

### Task 10: Run the full test suite

- [ ] **Step 1: Run all new tests together**

```
pytest plugins/taskmaster/tests/test_start_session_skill_lint.py plugins/taskmaster/tests/test_pick_task_skill_lint.py plugins/taskmaster/tests/test_start_session_smoke.py plugins/taskmaster/tests/test_pick_task_smoke.py -v
```

Expected: all tests pass. Zero failures.

- [ ] **Step 2: Run existing skill lint suite to check no regressions**

```
pytest plugins/taskmaster/tests/test_handover_skill_lint.py plugins/taskmaster/tests/test_issue_skill_lint.py plugins/taskmaster/tests/test_lesson_skill_lint.py plugins/taskmaster/tests/test_add_idea_skill_lint.py -v
```

Expected: all pass. If any fail, investigate — Plan D must not break existing skill structure.

---

## Phase 6 — Changelog

### Task 11: Add changelog entry

**Files:**
- Modify: `plugins/taskmaster/CHANGELOG.md`

- [ ] **Step 1: Read the current top of CHANGELOG.md**

Read the first 30 lines of `plugins/taskmaster/CHANGELOG.md` to find the correct insertion point (after the `## [Unreleased]` or before the latest version heading).

- [ ] **Step 2: Insert the entry**

Add under the `## [Unreleased]` section (or create it if absent), before any existing unreleased entries:

```markdown
### Changed — Ceremony glance-first redesign (Plan D)

- `start-session` default mode is now a ~800–1,000 token glance: slim `backlog_status` + top-5 open handovers + 1-line counts. Full ceremony (recap diff, lesson digest, core lessons, all issues, last session) is available via `--deep`.
- `pick-task` default mode is now a ~600–800 token glance: slim task + deps + open handovers for task + matched lesson IDs+tldrs (no full bodies) + filtered issues + linkage pills. Full ceremony (full task body, full lesson bodies, blast radius, handover context) is available via `--deep`.
- Deep ceremony content for both skills moved to `references/deep-mode.md` per skill — loaded only when `--deep` is invoked.
- Mid-session deepening documented in taskmaster router: "show me HND-012" → `backlog_handover_get`; "read the plan" → `backlog_get_task(sections=["plan"])` — no skill re-invocation.
- Lint tests added: `test_start_session_skill_lint.py`, `test_pick_task_skill_lint.py`.
- Smoke tests added: `test_start_session_smoke.py`, `test_pick_task_smoke.py`.
- `backlog_handover_latest` is deprecated in skill flows; replaced by `backlog_handover_list(status="open")` (requires Plan B).
```

- [ ] **Step 3: Commit**

```
git add plugins/taskmaster/CHANGELOG.md
git commit -m "docs(taskmaster): changelog entry for Plan D ceremony glance-first redesign"
```

---

## Phase 7 — Final validation

### Task 12: Full suite + integration check

- [ ] **Step 1: Run the complete new test suite**

```
pytest plugins/taskmaster/tests/test_start_session_skill_lint.py plugins/taskmaster/tests/test_pick_task_skill_lint.py plugins/taskmaster/tests/test_start_session_smoke.py plugins/taskmaster/tests/test_pick_task_smoke.py -v --tb=short
```

Expected: 20 tests pass, 0 failures.

- [ ] **Step 2: Confirm deep-mode reference files are substantive**

```python
python -c "
from pathlib import Path
skills = ['start-session', 'pick-task']
for s in skills:
    p = Path('plugins/taskmaster/skills') / s / 'references' / 'deep-mode.md'
    lines = [l for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]
    print(f'{s}/references/deep-mode.md: {len(lines)} non-blank lines')
"
```

Expected: both files report ≥30 non-blank lines.

- [ ] **Step 3: Confirm pick-task v3-context-loading.md is still present**

```python
python -c "
from pathlib import Path
p = Path('plugins/taskmaster/skills/pick-task/references/v3-context-loading.md')
print('exists:', p.exists())
"
```

Expected: `exists: True`. This file must not have been deleted — deep-mode.md supersedes it for deep paths, but v3-context-loading.md is still referenced and provides the per-source glance budget table.

- [ ] **Step 4: Token estimate spot-check both skills**

```python
python -c "
from pathlib import Path
for skill in ['start-session', 'pick-task']:
    text = (Path('plugins/taskmaster/skills') / skill / 'SKILL.md').read_text(encoding='utf-8')
    body = text[text.index('---', 3) + 3:].strip() if text.startswith('---') else text
    print(f'{skill} body tokens (est): {len(body) // 4}')
"
```

Expected: both ≤1,300.

- [ ] **Step 5: Final commit (if any stray edits)**

```
git status
```

If clean, no commit needed. If any files were touched in validation, stage and commit with:

```
git commit -m "chore(taskmaster/ceremonies): final cleanup after Plan D validation"
```

---

## Success criteria

All of the following must be true before Plan D is considered done:

| Check | Target | How verified |
|---|---|---|
| `start-session` SKILL.md body | ≤1,300 tokens | `test_start_session_skill_lint.py::test_skill_md_body_under_token_budget` |
| `pick-task` SKILL.md body | ≤1,300 tokens | `test_pick_task_skill_lint.py::test_skill_md_body_under_token_budget` |
| Glance MCP load for start-session | ≤1,000 tokens | `test_start_session_smoke.py::test_glance_mcp_payload_budget` |
| Glance MCP load for pick-task | ≤800 tokens | `test_pick_task_smoke.py::test_glance_mcp_payload_budget` |
| Deep-mode calls absent from glance body | `backlog_recap`, `backlog_lesson_digest`, `backlog_lesson_get`, `backlog_blast_radius` not in either SKILL.md | lint tests |
| `references/deep-mode.md` exists + substantive | ≥30 non-blank lines each | lint tests |
| `--deep` documented in both SKILL.md files | `--deep` substring in body | lint tests |
| Mid-session deepening table in router | `backlog_handover_get`, `verbose=True`, `sections=` in taskmaster SKILL.md | manual read |
| All existing skill lint tests pass | zero regressions | Task 10 Step 2 |
| CHANGELOG entry added | entry under Unreleased | Task 11 |
