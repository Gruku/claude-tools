---
notes: Wrap the existing backlog_migrate_v3 MCP tool (verified to ship by v3-release-001)
  with a guided skill. Show pre-flight summary (N tasks, M with non-trivial bodies
  will be extracted), explain the schema break (heavy fields move from backlog.yaml
  to tasks/<id>.md), offer dry-run preview, run the migration, summarise outputs,
  suggest gitignore additions for snapshots/auto. Without this skill, real users can't
  adopt v3 cleanly even after the MCP tool ships.
id: v3-skills-005
title: taskmaster:migrate-v3 skill — guided opt-in migration
---
