---
notes: 'Write tests that estimate the per-surface token cost of start-session, pick-task,
  end-session, and review-gate against a seeded fixture, and warn (not fail) when
  above the soft target from design-v3-narrative-continuity.md §Token Budget Guidance.
  Hard caps stay enforced in code (≤30 active lessons, ≤5 core, ≤30 handover index
  entries, top 10 issues). Targets: start-session ~3k / warn 5k; pick-task additive
  ~1.5k / warn 3k; end-session additive ~800 / warn 1.5k; review-gate additive ~800.'
id: v3-skills-013
title: Token budget signal tests per surface
---
