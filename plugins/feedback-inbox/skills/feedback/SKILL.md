---
name: feedback
description: Drop a feedback message into the claude-tools feedback inbox. Use when the user explicitly requests it ('/feedback', 'log this as feedback', 'send this to claude-tools', 'report this back', 'feedback to the toolmaker') AND proactively, on your own initiative, when you observe friction with a claude-tools-shipped component during a session — a taskmaster skill that errored, a guard-hook that blocked the wrong command, an MCP tool that returned a confusing shape, a skill description that didn't match its behaviour, a slash command that did the wrong thing. Do not fire for generic project friction or external-tool friction; only for claude-tools components (taskmaster, reflect-auto-improve, guard-hooks, statusline, feedback-inbox itself, ue5-materials, etc.). Silent on success — no user confirmation needed; the user reviews during /inbox triage.
---

# feedback — Producer

You drop one feedback message into the configured inbox. One invocation = one message. Never bundle multiple unrelated complaints into one message.

## Scope guard (read before deciding to invoke proactively)

Fire ONLY for friction with components shipped from `claude-tools`:
- taskmaster (any skill, command, MCP tool, hook)
- reflect-auto-improve
- guard-hooks
- statusline
- feedback-inbox itself
- ue5-materials, image-gen, codex-dispatch, reality-reprojection, shader-nodes

DO NOT fire for:
- Bugs in the user's project code.
- Friction with external tools (git, pytest, Node, language servers).
- General confusion that isn't tied to a specific claude-tools component.

If in doubt, don't fire. The user can always invoke `/feedback` explicitly.

## Procedure

1. **Resolve the target.** The plugin is installed at `${CLAUDE_PLUGIN_ROOT}` in every session that has it enabled, regardless of cwd. Probe the config with:

   ```bash
   python -c "import sys, json; sys.path.insert(0, r'${CLAUDE_PLUGIN_ROOT}'); from scripts.resolve_target import resolve_target; r = resolve_target(); print(json.dumps({'enabled': r.enabled, 'inbox': str(r.inbox) if r.inbox else None, 'reason': r.reason}))"
   ```

   If `enabled: false`, emit ONE line to the conversation: `feedback-inbox: <reason> — skipping.` Then stop. Do not raise, do not retry.

2. **Compose the message.** Pick:
   - `source`: `claude` if you're invoking proactively; `user` if the user explicitly dictated text.
   - `category`: `bug` (something is broken) | `friction` (works, but awkward) | `idea` (improvement suggestion) | `praise` (something worked well) | `question` (you want the toolmaker to clarify something).
   - `summary`: one-line, ≤ 120 chars. Lead with the component name (e.g. "taskmaster:pick-task hangs on long worktree paths").
   - `component`: the specific claude-tools subsystem, e.g. `taskmaster/pick-task`, `guard-hooks`, `reflect-auto-improve/harvest`. Required when `source=claude`.
   - `project` + `project_path`: derive from the current working directory — `Path.cwd().name` and the absolute cwd. Leave empty if you can't determine them; do not block.
   - `body`: freeform markdown. Two sections is the convention:
     - `## What happened` — concrete observation, with exact tool calls or error messages if available.
     - `## Suggested fix` — your best guess at what would help. Optional but valued.

3. **Write the message.** Run:

   ```bash
   python -c "
   import sys, json
   from datetime import datetime, timezone
   from pathlib import Path
   sys.path.insert(0, r'${CLAUDE_PLUGIN_ROOT}')
   from scripts.resolve_target import resolve_target
   from scripts.write_message import MessagePayload, write_message
   r = resolve_target()
   if not r.enabled:
       print(f'feedback-inbox: {r.reason} — skipping.'); sys.exit(0)
   payload = MessagePayload(
       source='<claude|user>',
       category='<bug|friction|idea|praise|question>',
       summary='<your one-line summary>',
       body='''<your multi-line body>''',
       project=Path.cwd().name,
       project_path=str(Path.cwd()),
       component='<claude-tools/component>',
       created=datetime.now(tz=timezone.utc),
   )
   path = write_message(r.inbox, payload)
   print(f'feedback-inbox: logged \"{payload.summary}\" → {path.name}')
   "
   ```

   Substitute the angle-bracketed placeholders with your composed values. Be careful to escape any single quotes inside the body, or use a heredoc / temp file if the body is long.

4. **Emit one line to the conversation.** Whatever the write script prints. Do not say more. The user reviews during `/inbox` triage, not now.

## Failure handling

- If the write script errors (permissions, disk full, malformed input), emit one line: `feedback-inbox: write failed — <error>`. Do not retry. Do not raise.
- If you can't determine `component` for a `source=claude` message, don't fire. The whole point of the scope guard is to tie observations to specific subsystems; an untagged message is noise.

## Anti-patterns

- Bundling multiple unrelated observations into one message. One issue per message.
- Firing for friction with the user's project code (not a claude-tools component).
- Asking the user "should I log this as feedback?" — proactive invocation is silent by design.
- Re-logging the same observation a second time in the same session. If you already wrote one, you're done.
