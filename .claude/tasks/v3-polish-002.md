---
notes: .tm-card primitive is published in components.css but no component uses it.
  issue-card, lesson-card, kanban card, and side-rail blocks each have local definitions
  using specific tokens (--issues-card-bg, --bg-panel, etc.). Audit per-variant first
  to avoid visual regressions, then retrofit.
id: v3-polish-002
title: C′ tm-card retrofit audit and rollout
---
