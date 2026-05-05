---
notes: '`.td-section .md-body` had no `overflow-wrap`/`word-break`, so long unbroken
  strings (file paths, anchor patterns, URLs, command lines) extended past the body
  column and pushed the layout — visually overflowing the Notes/Specification/Plan
  sections.


  Compounding factor: `.td-body` (the left grid track in `.td-grid`) had no `min-width:
  0`. CSS Grid''s default `min-width: auto` means a track can''t shrink below its
  content''s intrinsic minimum size, so a long unbreakable token would grow the body
  column and squeeze (or push off-screen) the right rail.


  Hot-patch landed on feature/taskmaster-v3 in `task-detail.css`:

  - `.td-section .md-body { ...; min-width: 0; overflow-wrap: anywhere; word-break:
  break-word; }`

  - `.td-grid > .td-body { min-width: 0; }`


  Validate: open a task with long file paths in Notes (e.g. v3-polish-029 has paths
  like `plugins/taskmaster/viewer/js/screens/kanban.js` in its anchors) — Notes text
  wraps to body width, no horizontal scroll, right rail stays at its 280px column.


  Discovered 2026-05-04 while dogfooding the v3 viewer.'
id: v3-polish-031
title: 'Task Detail: Notes (and other md sections) overflow horizontally for long
  unbroken strings'
---
