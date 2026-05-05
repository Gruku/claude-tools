---
notes: 'User-reported: tasks with no docs / no related lessons / no handovers / no
  issues / no deps / no unblocks / no blockers render with no visible right rail at
  all. Tasks with at least one populated relation render the rail correctly.


  Code review of `right-rail.js` says every panel always returns a `<section>` with
  an explicit empty-state placeholder ("no docs", "none", "no anchor matches", "no
  dependencies", "this task gates nothing"). So the rail SHOULD always be visually
  present. Either the empty-state CSS collapses panels to zero height/visibility,
  the rail mount aside is being hidden, or there''s a code path that skips rendering
  — needs investigation under the actual viewer.


  Acceptance:

  - Open a task with no docs/lessons/handovers/issues/deps/unblocks/blockers (pick
  a brand-new task) → right rail still occupies its 280px column with all 6 panel
  headers visible.

  - Empty-state placeholders styled consistently (color: var(--ink-3), italic, small).

  - No layout shift when navigating from a populated task to an empty one.


  Investigation hints: check `.td-empty` CSS for any `display:none`; check if `.td-rail-mount`
  has any `:has(:empty)` rule; verify panels mounted via `queueMicrotask` actually
  attach (test: assert `aside.children.length === 6` after mount).


  Discovered 2026-05-04 while dogfooding the v3 viewer; partner of v3-polish-031 (notes
  overflow).'
id: v3-polish-032
title: Task Detail right rail visually disappears when all 6 panels are empty
---
