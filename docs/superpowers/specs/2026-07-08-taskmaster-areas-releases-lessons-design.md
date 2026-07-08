# Taskmaster: Areas, Release Trains, and Lessons Removal — Design

**Date:** 2026-07-08
**Status:** Approved (brainstorm complete)
**Target:** taskmaster 4.0.0 (standalone repo `C:\Users\gruku\Files\Claude\taskmaster`, consumed by claude-tools via submodule)

## Problem

Audit of CodeMaestro (the largest taskmaster consumer, 1479 tasks, 65 epics, 14 phases) on 2026-07-08:

1. **Phase membership lives on tasks, not epics.** The viewer's "Current phase" epic list is derived (any epic with ≥1 task in the active phase), so nearly every epic appears — the "60 epics in Current phase" wall.
2. **The active phase is a black hole.** `patch-1-3-5` holds 809/1479 tasks (55%). Two sibling patch phases were merged into it instead of shipping. Nothing forces a phase to close; sessions add tasks to the active phase by default, so it grows monotonically. LLMs do not maintain a time axis unprompted — the time arrow needs a mechanism, not intent.
3. **Epics conflate two roles.** Subsystems that never finish (`desktop-app` 316 tasks, `playable-simple` 366, `asset-engine` 144, `ue-plugin` 86, `infra`) sit beside genuine finite features (`video-player` 8, `workbench-annotate` 9). Area-epics never close, so the epic count only grows (30 active / 26 planned / 9 archived, ever).
4. **Status rot.** 536 tasks (36%) stuck `in-review` — transitions fire on entry, never on exit.
5. **Lessons duplicate assistant memory.** 12 lessons total after ~8 months, versus ~10 `backlog_lesson_*` MCP tools, a skill, a viewer screen, and start-session machinery. Assistants' built-in memory systems (Claude Code auto-memory, etc.) already carry this load.

**Diagnosis:** a missing axis. Phase (time) has no closure mechanism; Epic (scope) conflates long-lived component with shippable feature.

## Design

### 1. Data model: Area / Epic / Release

**Area** (new entity) — long-lived subsystem (`desktop-app`, `ue-plugin`, `asset-engine`, `infra`).
- Fields: `id`, `name`, `description`, optional code-path anchors (ties into `project.yaml` repos).
- **No status lifecycle.** Areas never finish; that is now legal instead of a rotting epic.
- Tasks carry `area`; epics carry `area`.

**Epic** — strictly finite feature.
- Creation **requires `done_when`** (completion criteria, 1–3 lines). The MCP tool rejects epics without it, with the message: *an epic that can't say when it's done is an area.*
- Optional `target_release`.
- When all tasks reach done, the epic surfaces as **"closeable"** in status calls, start-session, and the viewer until explicitly closed.

**Release** (replaces Phase) — a train, not a bucket.
- Lifecycle: `planned → active → frozen → shipped`.
- **Pull-based, not push-based.** New tasks default to *no release* (backlog). A task enters a release only by explicit decision. Silent landing in the active phase becomes structurally impossible.
- `frozen`: only tasks fixing the release's own regressions may enter.
- Shipping runs a **mandatory triage** of every unfinished train task: carry to next release / return to backlog / kill. No silent carry-over.
- Migration: existing phases become releases mechanically (same ids); task `phase` field renames to `release`.

### 2. Enforcement mechanics (mechanisms, not prose)

1. **`backlog_release_ship`** — the closure ritual. Refuses to ship while any train task lacks a disposition; presents the open set for batch triage (carry / backlog / kill). Emits a Release record (version, date, contents) as the durable artifact.
2. **Pull gate in the write path.** `backlog_add_task` accepts no silent phase/release inheritance; `release` is explicit or absent. `backlog_release_pull` is the only way into a train, and the only way at all once `frozen` (regression exception requires a `fixes` link to a task already in the train).
3. **Session-start health surface.** start-session playbook shows: release age, open/total counts, days since last ship, closeable epics.
4. **`backlog_validate` rules**, run inside start-session: active release older than 30 days without freeze → warn; legacy epic without `done_when` → warn; `in-review` tasks older than 14 days → listed for sweep. (Constants, not config.)
5. **Viewer.** Kanban groups by Release train; Areas are the filter axis (replacing the derived phase→epic listing). Epic cards show `done_when` and a closeable badge.

No new config knobs — thresholds are opinionated constants.

### 3. Lessons removal + memory migration

**Remove:** the ~10 `backlog_lesson_*` MCP tools, `taskmaster:lesson` skill/playbook, viewer Lessons screen, lesson-marker logic in start-session, `lessons_meta` schema key. `.taskmaster/lessons/` files stay on disk (plain markdown, no data loss).

**Replace with a two-tier rule encoded in the playbooks that used to write lessons:**
- Session-level insight → the assistant's **own memory system** (Claude Code auto-memory; other adapters map to their equivalent or no-op).
- Knowledge binding **all** assistants → repo instruction files (CLAUDE.md / AGENTS.md), which every assistant already loads. end-session playbook gains a lightweight "instruction-file candidate?" check where the lesson prompt was.

**`migrate-lessons` playbook:** reads existing `L-*.md`, proposes a destination per lesson (assistant memory / instruction file / drop), applies on approval.

### 4. Rollout

Removed surface + schema break → **taskmaster 4.0.0**, one major bump for everything.

Epic order:
- **C — lessons removal** (independent, ships first)
- **B — Area entity + finite-epic `done_when` gate**
- **A — Release trains: lifecycle, ship ritual, pull gate, validate rules, viewer regrouping**
- **D — CodeMaestro migration** using the new tooling: classify 65 epics into ~6–8 areas + real epics; run `backlog_release_ship` on `patch-1-3-5` (first triage is big — 300+ open tasks — the debt surfaces once, batch-triaged); sweep the 536 `in-review` tasks. Scripted where mechanical (phase→release rename), interactive where judgment is needed (epic classification).

## Out of scope

- Multi-assistant phases 3–5 (adapters) — this design only keeps the playbook layer assistant-agnostic.
- Any goals/auto-mode redesign.
- Milestones key in backlog.yaml (untouched; revisit when it next hurts).
