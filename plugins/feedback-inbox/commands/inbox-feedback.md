---
description: Log a message into the claude-tools feedback inbox.
argument-hint: "<freeform feedback text>"
---

Invoke the `feedback-inbox:feedback` skill with the user-dictated message in `$ARGUMENTS`.

- Set `source=user` (the user explicitly asked, not a proactive Claude observation).
- Choose `category` from `$ARGUMENTS` content; default to `friction` if unclear.
- Choose `component` from context if obvious (e.g. user is in a taskmaster command transcript); leave empty if unclear.
- `summary` = first line of `$ARGUMENTS` (≤ 120 chars).
- `body` = rest of `$ARGUMENTS` formatted as a `## What happened` section.

Then proceed with the skill procedure (resolve target → write → one-line confirmation).
