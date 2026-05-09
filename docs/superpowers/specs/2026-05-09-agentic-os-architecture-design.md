# Agentic OS Architecture — Project Entity + Wiki Layer

**Date:** 2026-05-09
**Status:** Approved (design only — implementation deferred)
**Scope:** Future
**Companion spec:** `2026-05-09-kanban-header-improvements-design.md` (header polish, this session)

---

## Background

Today, a single `.taskmaster/backlog.yaml` mixes phases (intended as time-scale), epics (intended as features), and ad-hoc contextual buckets that have leaked into the phase axis (e.g. "Playable Ads Studio — Productionise the Pipeline" is currently a phase, but is really a separate sub-project). The user runs CodeMaestro as a "monorepo of work" that spans multiple repositories — Desktop App, API, UE Plugin, Playable Ads Studio research, and other research subprojects — without first-class support for that structure.

The user's stated direction is an **Agentic OS**: a layered scaffolding (architecture → memory → observability) where Taskmaster is one citizen alongside a knowledge wiki and (eventually) a dashboard of skills/automations. The unit of context inside that OS is the **Project**.

This spec defines the schema and viewer behavior for two related additions:

1. **Project as a first-class entity**, with sub-projects, replacing the current "phase as contextual bucket" anti-pattern.
2. **Wiki as a two-tiered knowledge layer** (general + per-project), coexisting with the existing Lessons system.

The OS root directory name is deferred and referenced as `~/.{TBD}/` throughout this document.

## Goals

- Each project gets its own Kanban and identity; sub-projects nest under parents.
- Phases stop being misused as contextual buckets — they become per-project time-scale only.
- Per-repo `.taskmaster/` continues to live next to its code (no central store imposed).
- Wiki content is persisted, surfaced in the viewer, and linkable to/from tasks and lessons.
- Migration is non-destructive and incremental.

## Non-goals

- Auto-detecting sub-projects from filesystem layout. Carve-out is manual.
- Rewriting Lessons. They stay tactical/trigger-based.
- Editing wiki content from inside the viewer. Edits happen in Obsidian or any editor; viewer is read-only.
- Picking the OS root name. (Deferred.)

---

## Architecture — Federation + OS Registry

```
~/.{TBD}/                          ← OS root (name deferred)
├── projects.yaml                  ← Registry: enumerates all known projects
└── wiki/                          ← General/cross-project wiki notes
    ├── claude-code-ecosystem.md
    └── ...

C:/Users/gruku/Files/Work/CodeMaestro/         ← A project repo
└── .taskmaster/
    ├── project.yaml                ← Identity (durable)
    ├── backlog.yaml                ← Phases, epics, tasks
    ├── lessons/                    ← Existing — unchanged
    ├── handovers/                  ← Existing — unchanged
    ├── issues/                     ← Existing — unchanged
    └── wiki/                       ← NEW — project-scoped wiki

C:/Users/gruku/Files/Work/CodeMaestro/desktop-app/   ← A sub-project repo
└── .taskmaster/
    ├── project.yaml                ← parent: codemaestro
    ├── backlog.yaml
    ├── ...
    └── wiki/
```

The viewer is a single instance ("v3 single-app + project switcher" already on the roadmap as `v3-release-007`) that reads `~/.{TBD}/projects.yaml`, lets the user pick an active project, and loads that project's `.taskmaster/` contents.

### `~/.{TBD}/projects.yaml` (registry)

```yaml
projects:
  - id: codemaestro
    path: C:/Users/gruku/Files/Work/CodeMaestro
    parent: null
    # Optional overlays — registry can override fields from project.yaml per-machine
    # display_name: "CodeMaestro (laptop)"
    # color: "#7c4dff"
  - id: codemaestro-desktop
    path: C:/Users/gruku/Files/Work/CodeMaestro/desktop-app
    parent: codemaestro
  - id: codemaestro-api
    path: C:/Users/gruku/Files/Work/CodeMaestro/api
    parent: codemaestro
  - id: codemaestro-ueplugin
    path: C:/Users/gruku/Files/Work/CodeMaestro/ue-plugin
    parent: codemaestro
  - id: claude-tools
    path: C:/Users/gruku/Files/Claude/claude-tools
    parent: null
```

Schema:
- `id` (required, slug, globally unique).
- `path` (required, absolute filesystem path to the project root — the directory containing `.taskmaster/`).
- `parent` (id or null) — single-parent tree; DAGs not supported.
- Any field present on `project.yaml` may be overlaid here (display_name, color, description, default_phase). Overlay wins on read.

### `<project>/.taskmaster/project.yaml` (identity)

```yaml
id: codemaestro
display_name: "CodeMaestro"
description: "Productivity OS for game developers"
color: "#7c4dff"
default_phase: "ship-v3"
```

Fields:
- `id` — must match the registry id.
- `display_name` — human-readable name shown in switcher and headers.
- `description` — optional, longer.
- `color` — hex color used in switcher badges, parent-of-child indicators, etc.
- `default_phase` — optional id of the phase to land on when the project is opened.

### Domain rules

| Entity | Scope | Notes |
|---|---|---|
| **Project** | Top-level | Tree nesting (one `parent`). Can be promoted/demoted by editing the registry. |
| **Phase** | Per-project | Each project has its own timeline. Optional `aligns_with: <parent-project>:<phase-id>` for documentation only. |
| **Epic** | Per-project | Belongs to exactly one project. Cross-cutting work goes into the parent project's epics. |
| **Task** | Per-project | Belongs to one project, one epic, one phase (today's model). |
| **Lesson** | Per-project | Unchanged from today. Tactical, trigger-based, auto-matched to tasks. |
| **Wiki page** | Per-project OR general | Two tiers: `<project>/.taskmaster/wiki/*.md` and `~/.{TBD}/wiki/*.md`. |

---

## Wiki — Two-Tiered Knowledge Layer

Wiki and Lessons coexist with different purposes:

| | **Lessons** | **Wiki** |
|---|---|---|
| Length | Short, single rule | Longform, structured |
| Surface | Auto-matched to tasks at runtime | Browsed by humans, linked from tasks |
| Trigger | Pattern-matched on task content | Linked explicitly or by tag |
| Audience | Agent (during work) | Both (reference) |
| Examples | "Never use `rm -rf` on worktrees" | "Architecture of the export pipeline"; "Glossary of CodeMaestro internals"; "ADR-007: chose pgvector over Weaviate" |

### Storage

Per-project wiki: `<project>/.taskmaster/wiki/`
General wiki: `~/.{TBD}/wiki/`

Files are markdown with frontmatter:

```markdown
---
id: export-pipeline-architecture
title: Export Pipeline Architecture
tags: [architecture, export]
related_tasks: [feat-042, feat-051]
related_lessons: [no-mocks-for-export]
updated: 2026-05-09
---

## Overview

...
```

Frontmatter fields:
- `id` (required, slug, unique within the file's wiki tier).
- `title` (required).
- `tags` (optional, list of strings).
- `related_tasks` (optional, list of task ids in this project).
- `related_lessons` (optional, list of lesson ids).
- `updated` (optional, ISO date).

### Viewer integration

**1. Wiki screen (sidebar).**
New `Wiki` entry in the viewer sidebar. Screen tabs:
- `Project wiki` — pages from the active project's `wiki/`.
- `General wiki` — pages from `~/.{TBD}/wiki/`.

Layout: list pane (left) with title + tags + updated date; preview pane (right) renders the markdown. Read-only — clicking "Edit" opens the file in the user's preferred editor (Obsidian URL scheme if available, else system default).

Filter input on the list pane (substring match on title + tags).

**2. Task right-rail block.**
Task detail screen gains a `Related wiki pages` section. Sources:
- Pages whose frontmatter `related_tasks` includes the current task id.
- Pages whose `tags` overlap with the task's epic id, phase id, or any task tag (when tasks gain tags).

Each entry: title + small "Project" / "General" badge + click opens the wiki preview.

---

## Parent-project Kanban Toggle

For projects that have descendants in the registry, the kanban header gains a toggle:

- **`My level`** (default) — show only tasks defined directly in this project's `backlog.yaml`. This is the cross-cutting work that doesn't belong to a sub-project.
- **`Rolled up`** — show this project's tasks **plus all descendants'** tasks (recursive). Each task is annotated with its source project's color/badge so it's clear where it lives.

Roll-up is read-only at the parent level. Edits route to the originating project.

The toggle is hidden for projects with no descendants.

---

## Migration

When the viewer detects an existing `.taskmaster/backlog.yaml` without a sibling `project.yaml`, on first switch it:

1. Reads `meta.project` from `backlog.yaml` (e.g., `claude-tools`, `visual-polish-test`).
2. Generates a `project.yaml` next to it with `id`, `display_name`, default `color`.
3. Appends a registry entry in `~/.{TBD}/projects.yaml` with `parent: null` and the project's filesystem path.
4. No data is moved. All phases, epics, tasks remain in `backlog.yaml`.

Sub-project carve-out is manual and incremental:
- User clones or initializes a new project inside a sub-repo (e.g. `desktop-app/.taskmaster/`).
- User moves tasks between backlog files and updates phase ids.
- User registers the new project with `parent: <root-id>` in the registry.

A future helper (`taskmaster:carve-project`) can automate the move; out of scope for this spec.

---

## Files Touched (when implemented)

This spec is design-only. Likely files when implementation lands:

- `taskmaster_v3.py` — read/write `project.yaml`, registry; resolve project paths.
- `viewer/js/store.js` — track active project, load registry, switch backlog source.
- `viewer/js/components/sidebar.js` — project switcher + Wiki entry.
- `viewer/js/screens/wiki.js` (new) — wiki screen.
- `viewer/js/screens/kanban.js` — parent-level toggle.
- `viewer/js/components/task-detail-document.js` — related wiki block in right-rail.
- `commands/init.py` (or equivalent) — generate `project.yaml` on init / migrate.

## Out of scope

- OS root naming (deferred).
- DAG-style sub-projects with multiple parents.
- Editing wiki content inside the viewer.
- Auto-detection of sub-projects from filesystem layout.
- General observability dashboard (a separate Agentic OS layer).
- Cross-project `Rolled up` aggregations beyond direct descendants (e.g., grandparent rolling up grandchildren is in-scope; cross-tree rollups are not).
