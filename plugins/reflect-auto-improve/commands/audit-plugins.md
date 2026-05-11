---
description: Self-audit claude-tools plugins — find dead skills, oversized descriptions, prune candidates
argument-hint: "[--plugin <name>] [--include-transcripts true|false]"
---

Parse `$ARGUMENTS` and invoke the `reflect-auto-improve:plugin-audit` skill.

- `--plugin <name>` → scope to one plugin under `plugins/`. Default: all.
- `--include-transcripts true|false` → default true.
- No args → audit all plugins with transcript scanning.

Then call the skill.
