# Archive Epic — Design Spec

**Date:** 2026-03-31
**Status:** Approved

## Overview

Add the ability to archive an entire epic, hiding it and all its tasks from the board and default listings. Mirrors the existing task archive pattern with cascade behavior.

## New MCP Tool: `backlog_archive_epic`

```
backlog_archive_epic(epic_id: str, reason: str = "done") -> str
```

**Parameters:**
- `epic_id` — the epic ID (e.g., "features", "infra")
- `reason` — one of: `done`, `deprecated`, `duplicate`, `wont-fix`, `superseded` (default: `done`)

**Behavior:**
1. Validate `reason` against `VALID_ARCHIVE_REASONS` (same set as task archiving)
2. Find the epic; error if not found
3. Error if epic is already archived
4. Set `epic.status = "archived"`, `epic.archive_reason = reason`, `epic.archived = <ISO timestamp>`
5. **Cascade:** for every task in the epic that is NOT already archived, set `task.status = "archived"`, `task.archive_reason = reason`, `task.archived = <same timestamp>`, remove `locked_by` if present
6. Save and return summary: `"Archived epic 'X' — N tasks cascaded (reason: {reason})"`

## Server Changes (`backlog_server.py`)

### Constants
- Add `"archived"` to `VALID_EPIC_STATUSES`

### `backlog_archive_epic` tool
- New tool as described above

### `backlog_status`
- Skip epics with `status == "archived"` from the dashboard epic table (mirroring how archived phases are skipped)

### `backlog_list_tasks`
- Skip tasks belonging to archived epics by default (unless `status="archived"` is explicitly passed)

### `backlog_next_available`
- No change needed — already filters to `epic.status == "active"` only

## Viewer Changes (`backlog-viewer.html`)

### `renderEpics()`
- Filter out epics with `status === "archived"` from the main epics grid

### Archived Epics Section
- New collapsible section below the epics grid, mirroring the archived tasks section pattern
- Chevron toggle, count badge, collapsible grid
- Epic cards in the archived section use dimmed opacity (0.65, 0.85 on hover)

### CSS
- `.status-archived` pill class for epic cards
- Archived epics section styles (reuse existing archived section patterns)

## What Stays Unchanged
- `backlog_next_available` — already excludes non-active epics
- Individual task archive/unarchive — still works independently
- Phase archiving — separate mechanism, unaffected
