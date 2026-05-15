# Continuity Dashboard — Design

**Date:** 2026-05-15
**Status:** Approved (brainstorming complete)
**Replaces:** v3-polish-011 (Dashboard second-pass design review)

## Problem

Handovers currently carry too many distinct purposes glued onto one artifact:

1. **Continuity markers** — "shipped X, next is Y, files of interest" (Shapes 1–3 from corpus analysis).
2. **Decision menus** — Claude writes 2–4 mutually exclusive options for the user to pick (Shape 5).
3. **AI-resume context** — frontmatter that controls how the next session loads body vs. headers.
4. **Auto-stage stubs** — machine-written per-task during auto-task loops (Shape 4).

Symptoms:

- The user falls back to writing short Telegram messages to themselves to remember "what was I doing yesterday." Telegram is *inconvenient* but the in-product surface fails to replace it.
- Decision menus die inside long handover bodies. The user must scroll to find unresolved choices.
- The current dashboard is a configurable widget bento (`prefs.dashboard.layout`) that doesn't cohere — the user explicitly asked to rebuild it from scratch.
- The 6 `session_kind` values × 3 tiers produce friction the user navigates rather than benefits from.

## Goal

A single home surface — the new dashboard — that answers "what's the next thing I should do?" within seconds of opening the viewer, by fusing continuity markers from handovers with three other live signals: open decisions, git state (unmerged/stale branches), and backlog drift (idle in-progress tasks, ideas stuck in brainstorm). Decisions become a first-class entity so they survive context death. Handovers shed the decision-menu burden and simplify.

## Design

### 1. Decisions as a first-class entity

#### 1.1 Schema

Stored at `.taskmaster/decisions/DEC-NNN.md`:

```yaml
---
id: DEC-001
title: "Land ue-plugin-086 fix"
status: open                # open | resolved | dropped
options:
  - "Push feature + open Draft MR against stage (hotfix flow)"
  - "Local --no-ff into develop, push on approval"
  - "Into 1.3.1/asset-studio-polishing (couples with active work)"
  - "Hold — user does merge"
recommendation: 2           # 1-indexed into options; null if Claude has no preference
task_id: ue-plugin-086      # nullable
related_issues: [ISS-018]
branch: feature/ue-plugin-086
resolved_with: null         # filled on resolve: integer index into options
resolved_rationale: null    # filled on resolve: short text
dropped_reason: null        # filled on drop
created_at: 2026-05-15T...
resolved_at: null
raised_in: 2026-05-15-...   # handover id, or null when raised mid-session outside a handover write
referenced_in: []           # back-references to handover ids; computed by MCP on each handover write
resolved_in: null           # handover id or commit:<sha> where resolved
---
<freeform body — context, constraints, links to other entities>
```

#### 1.2 MCP surface

```
backlog_decision_create(title, options, recommendation?, task_id?, related_issues?, branch?, body?)
backlog_decision_list(status?, task_id?, branch?)
backlog_decision_get(id)
backlog_decision_resolve(id, resolved_with, rationale?)
backlog_decision_drop(id, reason)
backlog_decision_update(id, fields...)        # title, options, recommendation, etc.
```

`backlog_decision_create` returns the new id and updates `referenced_in` on any related task/issue files.

#### 1.3 Skill

New skill: `taskmaster:decision`. Description triggers on Claude being about to write an inline option menu in chat (≥2 mutually exclusive paths it needs user input on). The skill:

1. Drafts the decision (title, options, recommendation, ties to current task/branch from auto state).
2. Calls `backlog_decision_create`.
3. Echoes a one-line confirmation in chat: `DEC-001 written — decide on dashboard or via /decide DEC-001`.

Hard rule baked into the skill: when ≥2 paths are being proposed, the option menu **does not** go inline in chat — it goes through `taskmaster:decision`. Chat scrollback is no longer the storage layer.

#### 1.4 Resolution UX

From the continuity dashboard hero (or from `/decide DEC-001`):

- Click an option to resolve. Writes `resolved_with`, `resolved_at`, `status: resolved`.
- "Drop" button → asks for one-line reason, sets `status: dropped`.
- On resolve, the resolution is appended as a one-line trace to the linked task's body so the rationale lives where the work lives:
  > `2026-05-15 · DEC-001 resolved with option 2: "Local --no-ff into develop, push on approval"`

#### 1.5 Auto-resolution hooks

- Commit messages matching `Resolves: DEC-001 with option N` cause the MCP server to flip the decision on the next file scan.
- `auto-task` will not transition a task to `done` while a linked decision is `open` without explicit `--override-open-decisions`.
- `end-session` lists unresolved decisions linked to the in-progress task and asks "carry forward, resolve now, or drop?"

### 2. Continuity dashboard

#### 2.1 Visual direction

**Direction C v3 (Hero + spine).** Locked. Single page, two-column body:

- **Left column (hero, ~1.55fr)** — the most urgent single item. Default: the oldest open decision, recommendation pre-rendered, options as inline cards with a primary "Pick option N" action. Empty state when no decisions are open: the most recent `Resume` handover, fully expanded.
- **Right column (spine, ~1fr)** — three blocks stacked: `Where you left off` (Resume), `Review`, `Drifting`. Each block shows entries with type chip, title, when, next-step verbatim, and where-line.

Above the body: topbar (project name, view switcher, `+ Decision` / `+ Idea` quick capture) and auto-mode strip. Below the body: footer health line (in-progress count, failing tests, build status, open issues).

No bento. No edit mode. No widget catalog. Fixed layout, opinionated. The existing `prefs.dashboard.layout` storage is removed.

#### 2.2 ContinuityItem model

Every thing rendered on the dashboard is normalized to:

```
{
  id, type,                  // type ∈ decision | handover | task | branch | idea | issue
  title,
  where,                     // pointer string: file path / branch / task id / "DEC-NNN"
  next,                      // one-line: decision→recommendation; handover→next_action;
                             //          task→blocked-by/status; branch→unmerged-target; etc.
  action_class,              // decide | resume | review | clean-up | ambient
  timestamp,                 // last activity
  age_days,
  task_id, branch,           // for cross-linking
}
```

A new server-side adapter, `backlog_continuity_items(view, project?)`, returns a unified list by polling the underlying sources (decisions, handovers, tasks, branches, ideas, issues) and projecting them to ContinuityItems. The three views are just different groupings/sorts of the same array.

#### 2.3 Three views

| View | Grouping | When useful |
|---|---|---|
| **Action** (default) | `Decide` → `Resume` → `Review` → `Clean up` | "Open taskmaster, do the next thing." |
| **Time** | `Today` / `Yesterday` / `Earlier` / `Drifting` | "What was I doing on Tuesday?" |
| **Entity** | `Decisions` / `Handovers` / `Tasks` / `Branches` / `Ideas` / `Issues` | "Show me all open decisions" |

Switcher is a segmented control in the topbar. Persisted per project in `prefs.continuity.view`.

#### 2.4 Action-view item routing

Items land in rails by `action_class`, which the adapter computes:

| Source | → action_class |
|---|---|
| Decision `status=open` | `decide` |
| Handover `status=todo`, age ≤ 7d | `resume` |
| In-progress task touched in last 3d | `resume` |
| Task `status=in-review` | `review` |
| Branch ahead of integration target, not pushed | `review` |
| Branch with uncommitted work, no commits 3+ days | `clean-up` |
| In-progress task idle 7+ days | `clean-up` |
| Idea in `brainstorm` status, 7+ days untouched | `clean-up` |
| Issue `status=open`, priority P0/P1 | `review` |
| Issue `status=open`, priority P2/P3, 14+ days | `clean-up` |

`auto-stage` handovers are filtered out of the adapter before projection (default). A `?include=auto-stage` query flag opts them back in for debugging.

#### 2.5 Time-view bucketing

| Bucket | Threshold |
|---|---|
| Today | activity within last 24h |
| Yesterday | 24–48h ago |
| Earlier | 2–7 days |
| Drifting | 7+ days, regardless of type |

#### 2.6 Widget migration

The current `plugins/taskmaster/viewer/js/components/widgets/*.js` family is reduced:

| Widget | Verdict | Notes |
|---|---|---|
| `briefing-strip` | **Remove** | The dashboard *is* the briefing. |
| `auto-mode-strip` | **Keep** | Lives above the body, full width. |
| `suggested-next` | **Remove** | `Resume` rail covers it. |
| `phase-deliverables` | **Move** | Goes to project/phase detail screens. |
| `newly-unblocked` | **Fold** | Surfaces inside `Resume`. |
| `what-changed` | **Remove** | The dashboard is what changed. |
| `last-session` | **Remove** | It's the top of `Resume`. |
| `open-issues` | **Fold** | Folds into `Review` (P0/P1) and `Clean up` (P2/P3, 14d+). |
| `build-test-pulse` | **Demote** | One-line footer health strip. |
| `lessons-digest` | **Move** | Already has its own `/lessons` shelf. |
| `quick-capture` | **Repurpose** | Becomes the `+ Decision / + Idea / + Issue` buttons in the topbar. |
| `recent-commits` | **Remove** | Drives `Resume` items; not its own rail. |
| `agent-activity` | **Fold** | Folds into auto-mode-strip. |
| `stale-tasks` | **Fold** | Folds into `Clean up`. |
| `auto-mode-stepper` | **Keep** | Renders inside auto-mode-strip when running. |
| `dashboard-grid` | **Remove** | No more bento computation. |
| `edit-mode` (dashboard) | **Remove** | No more user-configurable layout. |

`prefs.dashboard.layout` is removed from the store; migrate by ignoring on read.

#### 2.7 Scope: single-project for v1

Multi-project view (open two projects side by side, or a single combined feed) waits on `v3-release-007` (single-app + project switcher). The dashboard view-modes are unaffected — Action/Time/Entity work the same per project; a project chip in the topbar filters scope.

### 3. Handover simplification

Decisions extracted, the handover artifact contracts.

#### 3.1 Collapse session_kind from 6 → 4

| New kind | Replaces | Resume-load | Archive |
|---|---|---|---|
| `continuity` | end-of-day + exploration | frontmatter only | FIFO past cap-30 |
| `deep-context` | context-handoff | full body | FIFO past cap-30 |
| `milestone` | milestone-complete + pivot | full body, supersedes prior | chained supersession |
| `auto-stage` | unchanged | frontmatter only | bulk-archived on epic/phase completion |

`pivot` collapses into `milestone` — both rewrite history with chained supersession; the body explains whether it was a chunk completion or a direction change. The distinction was vibe-only in practice.

#### 3.2 Tier kill

Drop `light` / `standard` / `full`. One shape: what's there gets written, no length knob. Reduces decision fatigue in the handover skill and matches the project's opinionated-design philosophy (`feedback_taskmaster_opinionated_design.md`).

#### 3.3 Decision-menu extraction

Remove `Open options for next session` / `Pending decisions` style sections from all templates. Frontmatter gains:

```yaml
open_decisions: [DEC-001, DEC-003]
resolved_this_session: [DEC-002]
```

In the body, reference decisions inline with `[[DEC-001]]`; the viewer renders these as expandable cards via the existing `anchor-pills` component (reuse). Handover bodies shrink an estimated 20–40%.

#### 3.4 End-session integration

Before `end-session` writes its handover:

1. Call `backlog_decision_list(status=open, task_id=<current>)`.
2. If results exist, ask the user via `AskUserQuestion` per decision: `Carry forward · Resolve now · Drop`.
3. Update each decision per answer.
4. Pass the resulting `open_decisions` and `resolved_this_session` arrays to the handover write.

#### 3.5 Skill changes (deferred to plan)

- `taskmaster:handover` — template updates (remove decision sections, simplify tier logic).
- `taskmaster:end-session` — add decision sweep step.
- `taskmaster:start-session` — read `open_decisions` from latest handover and surface them on the dashboard's `Decide` rail.
- New `taskmaster:decision` — write/resolve/drop decisions.

### 4. Backlog folding

#### 4.1 Absorbed (closed when this ships)

| Task | Reason |
|---|---|
| **v3-polish-011** (Dashboard second-pass design review) | This design *is* the second pass. |

#### 4.2 Prerequisite (rolls into Task 1 of the implementation plan)

| Task | Why load-bearing |
|---|---|
| **v3-polish-048** (Capture full ISO datetime at handover creation) | Spine labels (`yesterday`, `2d`, `4d cold`) require correct timestamps. |
| **v3-polish-039** (Timestamp display broken across viewer) | Same root cause family; bundle. |
| **v3-polish-018** (Shared time-format helper) | Foundation for relative-time labels across the dashboard. |

#### 4.3 Side-stream (parallel, design assumes)

| Task | Relationship |
|---|---|
| **v3-skills-002** (handover skill, in-review) | New design consumes its output; minor template edits in §3. |
| **v3-polish-041** (handover status lifecycle, in-review) | `Resume` rail reads `status=todo`; lifecycle work already wired. |
| **v3-polish-042** (list_handover_ids sort, in-review) | Independent. |
| **v3-release-007** (single-app + project switcher) | Cross-project view depends on this; out of scope here. |
| **agentic-os-001** (all-projects dashboard) | Reframe after v3-release-007: "wire continuity dashboard to project switcher." Don't start now. |
| **ISS-004**, **ISS-010** | Handover MCP path/sort bugs; fix in parallel. |

### 5. Out of scope (v1)

- Multi-project / cross-project continuity feed (waits on `v3-release-007`).
- Telegram / mobile bridge (the design's wager is that a good continuity dashboard makes Telegram unnecessary; revisit only if the wager fails after dogfood).
- Drag-to-resolve, keyboard shortcuts for decision resolution beyond `/decide`.
- Notifications (open-decision count badges in OS dock, etc.).
- Auto-extraction of decisions from old handover bodies (historical Shape-5 entries stay where they are; the cutover is forward-only).

### 6. Implementation sequencing (preview, not the plan)

A separate plan doc will sequence:

1. **Foundation** — datetime + time-format (absorbs v3-polish-018/039/048). Tests for relative-time labels.
2. **Decision entity** — schema, MCP surface, file format, validators, tests.
3. **`taskmaster:decision` skill** — write/resolve/drop flow.
4. **ContinuityItem adapter** — `backlog_continuity_items` MCP tool, reads all sources, projects to unified shape, action_class routing tested.
5. **Action view** — hero + spine layout, decision resolution UX, Resume/Review/Clean rails.
6. **Time view** — bucket rendering.
7. **Entity view** — collapsible per-entity rails.
8. **Handover template simplification** — 6→4 kinds, tier removal, decision-link extraction.
9. **end-session decision sweep** — `AskUserQuestion` loop.
10. **Widget removal sweep** — delete the unused widget files and the bento grid code path.
11. **Migration shim** — ignore legacy `prefs.dashboard.layout` on read; ship a one-time `backlog_migrate_continuity` if anything else needs schema motion.
12. **Close v3-polish-011, reframe agentic-os-001** in the backlog.

### 7. Non-goals (named so future you doesn't reopen them)

- Making handover bodies user-editable through the viewer (today's read-only model is fine).
- Surfacing lessons on the continuity dashboard (lessons have their own surface; cross-linking via `referenced_in` is sufficient).
- Replacing the kanban or task-detail screens (those continue to be the deep surfaces).
- Re-introducing user-configurable layout to the dashboard (the opinionated default is the feature).
