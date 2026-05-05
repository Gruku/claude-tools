---
notes: The auto-task SKILL.md was drafted to call backlog_handover_get and backlog_lesson_match
  before those skills had write counterparts. Now that v3-skills-002/003/004 land,
  walk the full state machine end-to-end (PICK → SPEC_REVIEW → IMPLEMENT → TEST →
  REVIEW_GATE → HANDOVER_STUB → END_SESSION) against the v3 worktree's own backlog
  as a smoke run. Verify cursor persistence across compaction (PreCompact hook flushes
  state.json), failure taxonomy (tests-failed / spec-rejected / blocked / crashed)
  handling, and that the handover stub is brief enough not to bloat the index.
id: v3-skills-010
title: Quality pass — auto-task skill (wire to real handover/lesson tools)
---
