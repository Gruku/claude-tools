---
notes: 'polish-013 surfaced time-format chaos. On kanban v3-031 alone, four formats
  visible at once: 48h31m / 2d / 48:31:15 / 48:30:45. Dashboard auto-strip uses raw
  toLocaleString ("4/30/2026, 5:30:00 PM"). Sessions timeline shows HH:MM with no
  date context. Build one canonical relative-time helper (e.g. "2d ago" / "48h31m
  running") and one canonical absolute-time helper, then sweep call sites.'
id: v3-polish-018
title: Shared time-format helper + unify formats across viewer
---
