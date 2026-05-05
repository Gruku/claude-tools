---
notes: 'polish-013 audit reframed this — the spine is fully implemented (quest-spine.js
  with SVG nodes/satellites/connectors/pulse), Spine|Log toggle works, controls render.
  The perceived "missing spine" is a data-absence: when store.getAutoState() returns
  null (no active auto session), the empty-state node should render but a render/clear
  race during async polling startup leaves the center column blank. Fix the race so
  the "No auto-mode session is running." node renders cleanly when idle. Pair with
  v3-polish-025 (scale-motion rule violation in spine-active-pulse).'
id: v3-polish-008
title: Auto-mode page — fix data-state empty render (spine works)
---
