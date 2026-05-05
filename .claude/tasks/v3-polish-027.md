---
notes: 'Repro: open the kanban screen, scroll a column down, wait ~3 seconds. The
  column scroll position resets to the top. Scrollbar visibly flickers on/off at the
  same cadence.


  Root cause chain:

  1. main.js:128 `pollAutoStateForever` polls /api/auto/state every 3000ms unconditionally.

  2. store.js:47 `setAutoState` always calls `emit(''autoState'')` — no equality check
  against the previous value.

  3. kanban.js:363 subscribes to ''autoState'' and calls `paint()` on every emit.

  4. paint() does `boardGrid.replaceChildren()` (kanban.js:249) — wipes ALL column
  DOM (including .kanban-col-body scroll containers) and rebuilds them.


  Result: scroll position is destroyed every 3s; the rebuild also causes the scrollbar
  flicker the user sees.


  Fix candidates (need design call):

  - Skip emit when the autoState payload deep-equals the previous one (cheapest).

  - Decouple the autoState subscription from a full kanban paint — only the strip
  needs to repaint when autoState changes; cards don''t need a full re-render unless
  cursor.task_id changes.

  - If a full repaint is necessary, preserve scrollTop per column across paint() (capture
  before replaceChildren, restore after).


  Same root cause likely affects other screens that subscribe to ''autoState'' or
  ''backlog'' and replaceChildren().</notes>

  </invoke>'
review_instructions: 'Open #/kanban. Scroll a column down. Wait 10+ seconds. Verify
  scroll position holds and there''s no scrollbar flicker every 3s. Browser-verified:
  scrollTop stayed at 200 for 83s (many poll cycles).'
id: v3-polish-027
title: Kanban columns scroll-reset to top + scrollbar flicker every 3s
---
