---
notes: "Concept: one running taskmaster daemon on one port serves all projects, with\n\
  a project selector in the UI to switch backlog views. Replaces today's model\nwhere\
  \ each project spawns its own instance/port.\n\nWhy: avoid port collisions and proliferation\
  \ as project count grows; single\nbookmark / single daemon UX; cross-project visibility\
  \ becomes possible.\n\nDesign notes:\n- Every API/data path needs project_id scoping\
  \ from day one — retrofitting\n  later is painful.\n- Need a project registry the\
  \ daemon reads (locations of each project's\n  backlog.yaml).\n- File watchers,\
  \ websockets, and any caching must be keyed by project.\n- Per-project isolation\
  \ guarantees of the current model are traded for a\n  shared backend — design to\
  \ avoid global mutable state that leaks across\n  projects.\n\nForward-looking architecture\
  \ — likely post-2.0. Filed under v3-release for\nvisibility; move to a new architecture\
  \ epic if/when this gets real planning.\n"
id: v3-release-007
title: Single-app + project switcher (replace per-project port spawning)
---
