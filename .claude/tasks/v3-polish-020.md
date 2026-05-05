---
notes: 'polish-013 surfaced systematic a11y gaps, not local ones. Filter chips (lessons,
  issues, kanban) lack role="button" + aria-pressed — not keyboard-reachable. Card
  link semantics (lessons, issues) use <article role="link"> with manual keydown instead
  of <a href> — fragile in AT, breaks right-click → open in new tab. Heading hierarchy
  broken throughout — widget banners / shelf headers / column headers as <span> inside
  <header>. Two <h1>s on lesson-detail. Table semantics destroyed by display: contents
  (strips columnheader/row roles). Hover-only affordances invisible to keyboard. Plan:
  pick one screen as audit-and-fix reference, then propagate corrections to siblings.'
id: v3-polish-020
title: Viewer-wide accessibility sweep (chips, links, headings, table ARIA)
---
