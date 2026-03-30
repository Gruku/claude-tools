# Backlog Viewer: Compact Header & Enriched Cards

**Date:** 2026-03-30
**File:** `plugins/taskmaster/backlog-viewer.html`

## Goal

Reduce the viewer's header area from 7 visual rows to 3, and enrich task cards with a proper header section that surfaces status and context information previously shown in page-level banners.

## Current State

The viewer has 7 rows above the board:

1. Header (logo, title, subtitle, read-only badge, stat chips, search, theme/color toggles)
2. Load bar (collapses after load)
3. Toolbar (epic dropdown, phase dropdown, priority toggles, sort, archive toggle)
4. Active session banner (API-driven, pulsing green dot)
5. "Now working on" banner (in-progress task chips)
6. Phase pills + progress bar
7. Epic progress cards

## New Layout

### Row 1 — Header + Controls (single flex row)

**Left side:**
- Logo (clickable, emoji picker — unchanged)
- Project name (bold) + subtitle (muted)
- Read-only badge

**Right side (controls, right-aligned):**
- Search input (wider, placeholder "Search tasks... /")
- Priority toggle buttons: P0 (red), P1 (amber), P2 (blue), P3 (muted) — same toggle behavior as current
- Sort dropdown + direction toggle button
- Settings gear button (⚙) with dropdown containing:
  - Theme toggle (dark/light)
  - Color overlay toggle (project accent on/off)
  - Future settings can go here

### Row 2 — Phase Pills

- Phase step pills connected by horizontal lines (same rendering as current `renderPhases()`)
- Active phase highlighted, clickable to filter
- Phase history toggle ("History (N)") remains
- Active phase progress bar and stats shown in the active pill or adjacent to it
- Hidden if no phases in data

### Row 3 — Epic Cards

- Horizontal wrapping row of epic progress cards (same rendering as current `renderEpics()`)
- Clickable to filter by epic
- Hidden if no epics in data

### Removed from Header

| Element | Disposition |
|---|---|
| Stat chips (total, done, in-progress, todo, blocked) | **Removed** — column headers already show counts |
| Active session banner | **Removed entirely** — redundant with in-progress status |
| "Now working on" banner | **Removed** — replaced by enriched card headers |
| Load bar | Stays but collapses after load (unchanged) |
| Archive toggle | **Moved to bottom** near the archived section |
| Theme toggle | **Moved to settings dropdown** |
| Color overlay toggle | **Moved to settings dropdown** |
| Search input | **Moved from header-right to controls area** in row 1 |
| Epic dropdown (toolbar) | **Removed** — epic cards in row 3 serve as the filter |
| Phase dropdown (toolbar) | **Removed** — phase pills in row 2 serve as the filter |

## Enriched Card Header

Each task card gets a distinct header zone separated from the card body by a visual divider.

### Card Structure

```
┌─────────────────────────────┐
│ auth-003                 P1 │  ← Line 1: task ID (monospace) + priority badge
│ In Progress · 3d · feat/... │  ← Line 2: status + time-in-status + branch
├─────────────────────────────┤  ← Visual separator
│ Implement OAuth flow        │  ← Title
│ Anchors, tags, footer...    │  ← Rest of card body (unchanged)
└─────────────────────────────┘
```

### Card Header — Line 1

- **Task ID** (left): monospace, muted color — same as current
- **Priority badge** (right): colored pill (P0/P1/P2/P3) — same as current

### Card Header — Line 2

- **Status label**: text with status-appropriate color (e.g., "In Progress" in accent blue, "Blocked" in red, "Todo" in muted, "Review" in amber, "Done" in green)
- **Time in status**: calculated from timestamps — e.g., "3d" meaning 3 days since the task entered its current status. Calculated as:
  - Done: days since `completed`
  - In Progress / Review: days since `started`
  - Todo: days since `created`
  - Show nothing if no relevant timestamp
- **Branch name**: shown if `task.branch` exists, truncated with ellipsis if long. Include "(wt)" suffix if worktree is active (same as current footer behavior)

### Card Header Styling

- The header zone gets a subtle background tint (slightly different from the card body) to visually separate it
- A 1px border or subtle line separates header from body
- No left-colored borders (per user preference)
- The "recently moved" highlight (currently a left border) should use an alternative indicator — e.g., a subtle glow, background tint, or a small "new" badge

### Card Body Changes

- **Remove from footer**: branch name tag and worktree tag (moved to header line 2)
- Everything else in the card body remains unchanged (title, anchors, tags, epic tag, deps, docs, date)

## Settings Dropdown

A simple popover/dropdown anchored to the ⚙ gear button:

- **Theme**: "Dark" / "Light" toggle or switch
- **Project color**: "Color overlay" toggle or switch
- Dropdown closes on click outside or Escape
- Settings state persists in localStorage (same as current)

## Behavior Changes

- **Toolbar row**: removed entirely (its contents redistributed to row 1, row 2, row 3, or bottom)
- **Session polling**: `/api/session` polling removed (active session banner removed)
- **Stat chip updates**: removed from render cycle
- **Card render**: `makeCard()` updated to include header zone with status, time-in-status, and branch
- **Filter pipeline**: unchanged — search, priority, epic, phase, sort all work the same way, just triggered from different UI locations

## Out of Scope

- Card modal (detail view) — unchanged
- Keyboard shortcuts — unchanged
- YAML parsing / data model — unchanged
- Auto-refresh / polling for YAML changes — unchanged
- Archived section — unchanged (archive toggle just moves to bottom)
