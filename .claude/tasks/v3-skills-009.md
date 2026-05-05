---
notes: 'Update end-session skill to: (1) auto-offer handover when any heavy-session
  signal fires (turns > 60, conversation tokens > 200k, task in flight at session
  end, or user said "for tomorrow" / "next time" / "remind future me"), (2) take a
  snapshot via taskmaster_v3.take_snapshot before logging, (3) run handover archive
  sweep (drop oldest from index past cap 30), (4) prompt for lesson-candidate extraction
  when a non-obvious decision was made this session. Existing structured Done/Decisions/Issues
  mode stays; handover is additive.'
id: v3-skills-009
title: Retrofit end-session — auto-offer handover + snapshot
---
