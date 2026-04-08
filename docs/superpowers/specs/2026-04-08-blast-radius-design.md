# Blast Radius Analysis for Backlog Tasks

**Date:** 2026-04-08
**Status:** Design

## Overview

Blast radius analysis surfaces the impact footprint of a task — both predicted (before work starts) and verified (after implementation). It operates in two modes integrated into existing taskmaster workflows, combining deterministic code analysis with LLM-driven judgment.

## Modes

### Predictive Mode (Pick-Task)

Runs when a task is picked. Lightweight, metadata-only — no code tracing.

**Inputs:** Task title, description, notes, anchors, epic context.

**Process:**
1. Read task metadata
2. Cross-reference task anchors against all other tasks' anchors to find overlap
3. Return overlapping tasks with shared paths

**Presentation scales by priority:**

**P0/P1 — full structured block:**
```
── Predicted Blast Radius ──────────────────────
Anchored areas:
  - src/auth/middleware.py
  - src/auth/session.py

Related active work:
  - AUTH-007 "Refresh token rotation" (in-progress) — shares src/auth/
  - SESS-002 "Session timeout config" (next-up) — shares src/auth/session.py

Considerations:
  - Task overlaps with 1 in-progress task in the same area
  - Coordinate with AUTH-007 to avoid conflicting changes to middleware
────────────────────────────────────────────────
```

The "Considerations" section is agent-generated — the LLM reasons about what the developer should keep in mind given the overlap and task context.

**P2/P3 — single line:**
```
Blast radius: No overlap with active tasks.
```
Or:
```
Blast radius: Overlaps with AUTH-007 (in-progress) on src/auth/
```

### Evidence Mode (Review Gate)

Runs as Gate 4 in the review gate. Heavy, code-based analysis using actual diff.

**Inputs:** Task ID, branch diff, optionally `depth_override`.

**Process:**
1. Diff the task branch against base branch to get changed files
2. For each changed file, compute fan-out (how many files import it)
3. Apply adaptive depth heuristic to determine hop count per file
4. Walk import graph to determined depth
5. Match all affected file paths against other tasks' anchors
6. Return structured data

**Presentation — two parts:**

**Part 1: Gate table row (always advisory, never blocking):**
```
Gate 1 (Spec/Plan):    PASS
Gate 2 (Code Review):  WARN — 2 important findings
Gate 3 (Tests/Build):  PASS
Gate 4 (Blast Radius): WARN — 12 dependents across 3 modules, 1 overlapping task
```

Verdict logic:
- **PASS** — low fan-out, changes well-contained, no overlapping active tasks
- **WARN** — moderate fan-out, overlapping tasks found, or changes touch shared modules
- **WARN (loud)** — another in-progress task is modifying the same files. Visually distinct, called out explicitly by the agent.

No FAIL verdict. Blast radius is a discovery tool, not a quality gate. Keeping it advisory preserves signal value — developers pay attention because they're not conditioned to dismiss it.

**Part 2: Detailed report:**
```
── Blast Radius Report ─────────────────────────
Changed files (4):
  src/auth/middleware.py     — 14 dependents (deep trace, 2 hops)
  src/auth/session.py       — 8 dependents (normal trace, 1 hop)
  src/auth/types.py         — 3 dependents (shallow trace, 1 hop)
  plugins/oauth/handler.py  — 0 dependents (leaf, no trace)

Affected modules:
  - src/api/routes/ (3 files depend on middleware)
  - src/dashboard/ (2 files depend on session)
  - tests/integration/ (6 test files reference changed modules)

Overlapping tasks:
  ! AUTH-007 "Refresh token rotation" (in-progress)
    Shared paths: src/auth/middleware.py, src/auth/session.py
    Risk: Both tasks modifying the same files concurrently

Suggested follow-ups:
  - Verify AUTH-007 branch doesn't conflict with these changes
  - Dashboard session display may need updating given session.py changes
  - Integration tests in tests/integration/auth/ should be re-run
────────────────────────────────────────────────
```

The "Suggested follow-ups" section is agent-generated — the LLM interprets the structured data and applies judgment about what needs attention, including broader architectural considerations like "what existing features should be updated because this change now exists."

## MCP Tool: `backlog_blast_radius`

A new tool in the backlog server. Does mechanical work only — no judgment.

### Predictive Mode

**Input:**
```json
{
  "task_id": "AUTH-005",
  "mode": "predictive"
}
```

**Output:**
```json
{
  "task_summary": "Add OAuth2 PKCE flow",
  "anchored_areas": ["src/auth/middleware.py", "src/auth/session.py"],
  "overlapping_tasks": [
    {
      "task_id": "AUTH-007",
      "title": "Refresh token rotation",
      "status": "in-progress",
      "shared_paths": ["src/auth/middleware.py", "src/auth/session.py"]
    }
  ]
}
```

### Evidence Mode

**Input:**
```json
{
  "task_id": "AUTH-005",
  "mode": "evidence",
  "depth_override": null
}
```

**Output:**
```json
{
  "changed_files": ["src/auth/middleware.py", "src/auth/session.py", "src/auth/types.py", "plugins/oauth/handler.py"],
  "dependency_graph": {
    "src/auth/middleware.py": ["src/api/routes/auth.py", "src/api/routes/admin.py", "src/api/routes/user.py"],
    "src/auth/session.py": ["src/dashboard/session_view.py", "src/dashboard/user_panel.py"]
  },
  "fan_out_scores": {
    "src/auth/middleware.py": 14,
    "src/auth/session.py": 8,
    "src/auth/types.py": 3,
    "plugins/oauth/handler.py": 0
  },
  "depth_used": {
    "src/auth/middleware.py": 2,
    "src/auth/session.py": 1,
    "src/auth/types.py": 1,
    "plugins/oauth/handler.py": 0
  },
  "overlapping_tasks": [
    {
      "task_id": "AUTH-007",
      "title": "Refresh token rotation",
      "status": "in-progress",
      "shared_paths": ["src/auth/middleware.py", "src/auth/session.py"]
    }
  ],
  "summary_stats": {
    "files_changed": 4,
    "total_dependents": 25,
    "overlap_count": 1
  },
  "truncated": false
}
```

## Adaptive Depth Heuristic

Determines how many hops to trace per changed file. Lives inside the MCP tool.

### Inputs Per File

- File path (shared vs. leaf location)
- Fan-out score (number of direct importers)
- Change type (exported API change vs. internal-only)
- Task priority
- Manual override (from task field, if set)

### Decision Matrix

| Signal | Shallow (0-1 hop) | Normal (1 hop) | Deep (2 hops) |
|---|---|---|---|
| File location | `plugins/*/`, leaf components | `src/`, feature dirs | `lib/`, `core/`, `utils/`, shared dirs |
| Fan-out | 0-3 importers | 4-10 importers | 11+ importers |
| Change type | Internal only | Mixed | Exported API changes |
| Task priority | P3 | P2 | P0/P1 |

Each signal votes for a depth. The tool takes the **maximum** across all signals. Manual override wins unconditionally.

### Shared Directory Detection

Directories whose files have an average fan-out above a configurable threshold are treated as shared. The threshold defaults to 5. An explicit `shared_dirs` list in config supplements auto-detection.

## Import Graph Parsing

Regex-based parsing per language. No AST, no persistent index.

### Supported Languages (Initial Set)

- **Python** — `import X`, `from X import Y`
- **JavaScript/TypeScript** — `import ... from`, `require()`, dynamic `import()`
- **Go** — `import` blocks

### Execution Strategy

On each evidence mode call:
1. Get changed files from git diff
2. For each changed file, scan project files (scoped by extension) for import references
3. If depth > 1, repeat for dependents found
4. Scope search to `sub_repo` if set on the task
5. Cap total file scan at configurable limit (default 1000 files)
6. If cap hit, return `truncated: true`

### Export Change Detection

To determine if exported APIs changed (for depth heuristic input), diff exported symbols between base and current branch. Regex-based detection of `export`, `def`, `class`, `func` declarations at module scope. Heuristic — not perfect, but sufficient for depth voting.

## Schema Extensions

### Task Field

```yaml
blast_radius_depth: shallow | deep   # optional, overrides adaptive heuristic
```

Added alongside existing fields like `review_instructions`. Only used in evidence mode.

### Backlog Meta Config

```yaml
meta:
  blast_radius:
    fan_out_threshold: 5        # avg fan-out above this = "shared" directory
    max_file_scan: 1000         # cap for import search
    shared_dirs: []             # optional explicit list, supplements auto-detection
```

All optional with sensible defaults. If `blast_radius` key is absent, defaults apply.

## Overlap Detection

Anchor-based only. When blast radius identifies affected file paths (from anchors in predictive mode, from diff + dependency graph in evidence mode), it matches those paths against anchors of all other non-archived tasks.

In-progress tasks with overlapping paths receive a louder visual warning than next-up or backlog tasks, since concurrent modification is the highest-risk scenario.

## Design Decisions

1. **Always advisory, never blocking** — blast radius is a discovery tool. Blocking creates override fatigue and degrades signal value.
2. **Predictive mode is metadata-only** — keeps pick-task fast and cheap on tokens. The conceptual reasoning comes from the LLM interpreting overlap data.
3. **Evidence mode is hybrid** — deterministic tool provides structured data, LLM provides judgment and suggested follow-ups. Clean separation of concerns.
4. **Regex over AST** — simpler to implement and maintain across multiple languages. Good enough for import detection.
5. **No persistent index** — stateless per-call scanning. Simpler architecture, acceptable performance with file cap.
6. **Anchor-based overlap only** — anchors are the designed mechanism for task-to-code mapping. Branch diff comparison adds complexity and noise.
