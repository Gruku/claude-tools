# Kanban Header Improvements — Design

**Date:** 2026-05-09
**Status:** Approved for implementation
**Scope:** This session
**Companion spec:** `2026-05-09-agentic-os-architecture-design.md` (Project + Wiki — future)

---

## Problem

The Kanban header has accumulated friction as the backlog has grown:

1. **Archived phases leak into the future region.** `phase-stepper.js` only recognizes `done | active | future`. Phases with `status: archived` (e.g. CodeMaestro's "UE Polish + Pre-Dispatch Re-architecture (post-alpha)") fall through to the future carousel and look like upcoming work.
2. **Archived tasks have no surface.** They exist in the backlog (`status: archived`, with `archived_reason`) but the kanban shows nothing — no link, no count, no way to find them.
3. **Epic chips wrap to multiple rows.** The current `epic-chips.js` is a flat list; in CodeMaestro the row is two-deep and grows. There's no filter, no sort, no way to demote stale epics. Archived epics show in the same row as active ones.
4. **Phase carousel resets scroll on filter.** Selecting a far-away phase scrolls the carousel back to its initial home position, hiding the selected phase. The user loses their place.

## Goals

- Make archived phases discoverable but de-emphasized.
- Give archived tasks a single dedicated home, off the kanban.
- Replace the flat epic chip row with a single-row design that combines manual pinning, ranked auto-fill, and a dropdown for everything else.
- Preserve carousel scroll state across filter selections.

## Non-goals

- Introducing the Project entity (covered in companion spec, future).
- Changing how phases or epics are stored in `backlog.yaml`.
- Editing/managing wiki content from the viewer.
- Building the parent-project "rolled up" toggle (no Project entity yet).

---

## Design

### 1. Archived phases — `Archived` dropdown at left edge

**Trigger:** A pill labeled `Archived (N)` rendered as the leftmost element of `kanban-phase-stepper`, before the past-region carousel. Hidden when N=0. Style: smaller and dimmer than past chips; uses neutral border/background, not amber.

**Behavior:** Click opens a small popover anchored below the pill. Popover lists archived phases as selectable rows showing phase name, completion date if present, and `archived_reason` if present. Clicking a row sets the kanban phase filter to that phase id and closes the popover. The selected phase remains visible as a labeled archived pill (not as a past chip) so the user knows the filter is on an archived phase.

**Stepper logic update (`phase-stepper.js`):**
- Add `archivedPhases = phases.filter(p => p.status === 'archived')`.
- Exclude archived phases from `pastPhases` and `futurePhases` calculation.
- Render the archived pill+popover as a new region before the past carousel.

**Status mapping:** Anywhere code currently checks `status === 'done'` to bucket as "past", treat `archived` as a separate bucket. Anywhere it checks `status === 'future' || status === 'planned'`, ensure `archived` is excluded.

### 2. Archived tasks — separate screen

**Sidebar entry:** Add `Archived` link at the bottom of the sidebar (below existing kanban/dashboard links).

**Route:** `/archived` (handled by `viewer/js/router.js`).

**Screen (`viewer/js/screens/archived.js`, new):**
- Title: `Archived tasks (N total)`.
- Group by epic.
- For each task: id, title, phase, date archived (if available), `archived_reason`.
- Allow filtering by epic and search by title.
- Read-only — no transitions back to active here. (User can edit the task file or open task detail.)

**Source of data:** `store.getBacklog()` already returns full task list. Filter on `status === 'archived'` in the screen.

### 3. Epic dropdown — `epic-chips.js` rewrite

**Layout:** Single row, `flex-wrap: nowrap`, `overflow: visible` (the dropdown panel will overlay).

**Quick chips (up to 5):**
- Slot 0: `All` chip (clears selection — unchanged).
- Slots 1–5: filled by ordered list:
  1. Manually pinned epics (in pin order, capped at 5).
  2. If pin count < 5: top remaining epics ranked by `count(tasks where status ∈ {todo, in-progress, in-review} and epic == E)`, descending. Ties broken by `last_referenced` desc, then alphabetical.
- Archived and done epics never auto-fill quick slots — they only show via pinning or via the dropdown.

**`+N more` trigger:**
- Renders right of the last quick chip when the total visible epic count exceeds slot capacity. Label: `+ N more` where N = remaining count.
- Click toggles a dropdown panel.

**Dropdown panel:**
- Filter input at top — substring match on epic name (case-insensitive).
- Sort selector — options: `Task count` (default), `Status (active → done → archived)`, `Recent activity`, `Alphabetical`.
- Scrollable list of epics. Each row shows:
  - Multiselect checkbox (selecting toggles the epic in `state.filters.epics`)
  - Epic color swatch + name + status badge + task count
  - Pin/unpin icon (24px tap target). Pinned bubbles to quick-chip slots; unpinning frees the slot.
- Footer: `Clear all` and `Close` actions.

**Persistence:**
- Pin order: `store.getPrefs().kanban.pinnedEpics: string[]` (epic ids in pin order).
- Sort selector: `store.getPrefs().kanban.epicDropdown.sort: enum`.
- Both saved on change via existing `savePrefs` in `kanban.js`.

**Behavior with phase filter:**
- Existing pruning logic (`epicsForPhase` in `lib/filters.js`) continues to apply — selected epics that aren't in the active phase scope are pruned. Pin state is NOT pruned (pins survive phase changes).

### 4. Phase scroll preservation

**Current behavior (bug):** Each render of `phase-stepper.js` recomputes the past/future carousel `translateX` offsets from scratch (window starts at index 0), snapping back to home on every filter change.

**Fix:** Persist the per-region offset in module-scoped state keyed by phase set hash, and restore it on re-render.

- Maintain two offsets in closure-local state on the stepper module: `pastWindowStart` and `futureWindowStart` (integer indices into the phase list).
- On render:
  1. Compute the new past and future arrays.
  2. If the selected phase is in past or future region and falls **outside** the current window, slide the window so the selected phase is visible (e.g., place it in the middle slot when possible).
  3. Otherwise leave `pastWindowStart` / `futureWindowStart` untouched.
  4. Apply the corresponding `translateX` to the carousel strips.
- The two existing carousel arrows (`‹` and `›`) update the corresponding offset.

**Edge cases:**
- Selecting the `All` pill or `Orphans` pill: do not change carousel offsets.
- Selecting an archived phase from the new dropdown: do not change past/future offsets — that filter targets a different region.
- Backlog reload (SSE): if the past/future arrays' phase ids are unchanged, preserve offsets; if the arrays changed length or composition, clamp offsets to valid range and slide if necessary.
- Initial mount with no prior state: offsets default to 0 (existing behavior).
- Page refresh: state resets to 0 (not persisted).

---

## Files Touched

| File | Change |
|---|---|
| `viewer/js/components/phase-stepper.js` | Recognize `archived` status, render `Archived` pill+popover at left edge, preserve scroll state |
| `viewer/js/components/epic-chips.js` | Rewrite for single-row + dropdown + pinning |
| `viewer/js/screens/kanban.js` | Wire new pinning state, mount sidebar Archived link |
| `viewer/js/screens/archived.js` | NEW — archived tasks screen |
| `viewer/js/router.js` | Add `/archived` route |
| `viewer/js/components/sidebar.js` | Add `Archived` entry |
| `viewer/css/components/phase-stepper.css` | Style for archived pill + popover |
| `viewer/css/components/epic-chips.css` | Style for dropdown trigger + panel |
| `viewer/css/screens/archived.css` | NEW — archived screen styles |
| `viewer/js/lib/filters.js` | Confirm `archived` is excluded from default kanban view (likely already is) |

## Testing

- Phase stepper renders `Archived (N)` only when archived phases exist.
- Phase stepper bucket: archived not in past/future regions.
- Selecting an archived phase via the popover sets the filter and the carousel state is undisturbed.
- Epic chips: with 0 pinned, top 5 by task count are shown. With 3 pinned, those 3 + top 2 by count.
- Pinning an epic in the dropdown promotes it; unpinning demotes back to ranking.
- Filter input narrows dropdown list. Sort selector reorders correctly for each option.
- Archived tasks screen lists only `status: archived` tasks, grouped by epic.
- Phase scroll: select past phase 1 → scroll right → select past phase 5 → scroll preserved (phase 5 in view); clear filter → scroll restored.
- All existing kanban behavior (search, priority chips, status grouping, sort) unchanged.

## Style notes

- No left-rail accents on the archived pill or dropdown items (per user preference).
- No box-shadows; use surface stepping for popover/dropdown elevation.
- No transforms on hover (color/border only).

## Out of scope (handled in companion spec)

- Project entity, OS registry, parent-level "Rolled up" toggle, wiki integration. See `2026-05-09-agentic-os-architecture-design.md`.
