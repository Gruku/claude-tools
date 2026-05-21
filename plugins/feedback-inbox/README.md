# feedback-inbox

Lightweight inbox so any Claude Code instance on this machine can drop a feedback message about claude-tools components (taskmaster skills, hooks, MCP tools, etc.), and the user can triage them in one place.

## One-time setup

In a session running anywhere on this machine:

```
/feedback-inbox-setup
```

This writes `~/.claude/inbox-target.json` and creates the inbox directory.

## Use

- `/inbox-feedback <text>` — log a message explicitly. (Named `/inbox-feedback` rather than `/feedback` to avoid colliding with Claude Code's built-in `/feedback`.)
- Claude may also invoke the `feedback` skill silently when it hits friction with a claude-tools-shipped component (no confirmation needed; the user can review during triage).
- `/inbox` — in this repo: list pending messages and walk them, promoting useful ones to `taskmaster:add-idea` or `taskmaster:bug`.

See `docs/superpowers/specs/2026-05-21-feedback-inbox-design.md` for the design.
