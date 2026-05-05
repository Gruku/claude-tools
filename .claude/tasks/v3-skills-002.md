---
notes: 'Author the dedicated handover skill. Triggers: "wrap up", "ending the day",
  "write a handover", "I am at 300k tokens". Generates the four-section body (Decisions
  / Blockers / Where I''d start / Open threads), prompts for tldr + next_action +
  session_kind, writes .taskmaster/handovers/YYYY-MM-DD-<slug>.md, syncs the backlog.yaml
  handovers index (cap 30, archive older). Pairs with read flow via backlog_handover_get.
  Backend exists in taskmaster_v3.py (write_handover/read_handover/sync_handover_index).
  User''s #1 stated pain — every other v3 surface that mentions handovers depends
  on this.'
id: v3-skills-002
title: taskmaster:handover skill — write/read flow
---
