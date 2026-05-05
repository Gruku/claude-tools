---
notes: 'Update pick-task skill to: (1) accept "continue where we left off" / "continue
  this task" triggers (auto-resolve to the most-recently-touched in-progress task
  with a handover), (2) load related_handovers tldrs (not full bodies, ~50 tokens
  × cap 3), (3) load trigger-matched lessons in full (cap 3 hits, ~300 tokens worst
  case), (4) surface related_issues with severity. Watch additive ~1.5k token target
  (warn 3k). This is the user-facing behaviour they explicitly asked about in the
  v3-skills kickoff.'
id: v3-skills-008
title: Retrofit pick-task — "continue this task" trigger + v3 surfaces
---
