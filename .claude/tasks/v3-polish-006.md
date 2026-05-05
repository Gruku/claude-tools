---
notes: 'User feedback 2026-05-02 — auto-mode header chrome takes too much space. Two
  parts: (1) Remove the auto-mode strip from the dashboard header (currently rendered
  between briefing strip and bento via .dash-automode slot in dashboard.js:31-33;
  the strip itself is plugins/taskmaster/viewer/js/components/auto-mode-strip.js —
  full-width row showing "Auto-mode · N running · running Xd · per-run pills · view
  all"). (2) Minimize the always-visible auto-run status pill in the global topbar
  (added in commit 5974ea0 "header auto-mode status pill visible on every screen")
  so it consumes less horizontal real estate — likely shrink to icon + dot indicator
  with tooltip for details.'
id: v3-polish-006
title: Slim down auto-mode header — remove strip + minimize pill
---
