---
notes: 'Author the lessons skill. Triggers: "remember this", "this keeps happening",
  "we always do X here", auto-suggestion from accumulated feedback memory. Captures
  kind (pattern/anti-pattern/gotcha), triggers (file globs + task-title substrings),
  why, what-to-do. Implements the reinforce loop (lesson_reinforce backend exists),
  auto-promotion to core at reinforce_count >= 5, auto-decay (180d unreinforced +
  count<2 → retired). Three-tier loading discipline (digest 30 / core 5 / trigger-matched
  3) is enforced by start-session and pick-task; this skill is the *write* side. Patterns
  to apply come from v3-skills-001.'
id: v3-skills-003
title: taskmaster:lesson skill — write/reinforce/promote
---
