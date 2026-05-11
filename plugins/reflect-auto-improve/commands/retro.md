---
description: Run a time-windowed retrospective on a project (shallow|standard depth in v1)
argument-hint: "[shallow|standard] [--project <path>]"
---

Parse `$ARGUMENTS` and invoke the `reflect-auto-improve:retro` skill.

- If the first non-flag arg is `shallow` or `standard`, pass it as `depth`.
- If `--project <path>` is present, pass it through; otherwise default to cwd.
- If no args, use defaults (`depth=standard`, project=cwd).
- If the user passes `deep`: tell them deep depth is v1.1 and offer `standard` instead — do NOT silently downgrade.

Then call the skill.
