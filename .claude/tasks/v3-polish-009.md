---
notes: 'polish-013 audit confirmed the concept-delta scope and surfaced 3 hard bugs:
  (1) blocks chip is dead — store.getTasksIndex doesn''t exist, guard silently returns
  0 on every card; (2) "Kanban" view toggle is a no-op (button flips pressed state
  but layout is unchanged from Hybrid); (3) aging bar always shows "Fresh" — issues
  use a `created` field but computeAgingTier reads `discovered`, so percent is always
  0%. Concept deltas: severity chips missing colored dots + count badges + "All" reset;
  column headers use uppercase 12px instead of concept''s serif italic 14px + tagline
  + count; resolved shelf is single-column not 2-column grid. Estimate bumped M →
  L given total scope. Concept refs: see .superpowers/brainstorm/.../issues-hybrid.html
  and issues-v2-bugreport.html.'
id: v3-polish-009
title: Issues screen — align with design concept (concept deltas + 3 real bugs)
---
