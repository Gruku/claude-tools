---
name: inbox-triage
description: List and walk pending messages in the claude-tools feedback inbox, routing accepted items to taskmaster:add-idea or taskmaster:bug and archiving the rest. Invoke when the user says '/inbox', 'triage the inbox', 'process feedback', 'what's in the inbox', 'any feedback to look at', or sits down in the claude-tools repo and asks what's new. Reads messages written by the feedback-inbox:feedback producer. Non-destructive — processed messages move to inbox/processed/<year>/, never deleted.
---

# inbox-triage — Reader

You walk pending feedback messages in the configured inbox, present each one, and let the user pick an action.

## Procedure

1. **List pending.** Run:

   ```bash
   python -c "
   import sys, json
   sys.path.insert(0, r'${CLAUDE_PLUGIN_ROOT}')
   from scripts.resolve_target import resolve_target
   from scripts.list_pending import list_pending
   r = resolve_target()
   if not r.enabled:
       print(f'feedback-inbox: {r.reason}'); sys.exit(0)
   res = list_pending(r.inbox)
   print(json.dumps({
       'count': len(res.messages),
       'counts': res.counts,
       'warnings': res.warnings,
       'messages': [{'path': str(m.path), 'id': m.id, 'category': m.category,
                     'component': m.component, 'summary': m.summary, 'source': m.source,
                     'project': m.project, 'created': m.created} for m in res.messages],
   }, indent=2))
   "
   ```

   Empty inbox → emit `feedback-inbox: inbox is empty.` and stop.

2. **Show the dashboard.** Print a one-screen summary:

   ```
   feedback-inbox: 7 pending  (friction: 3, bug: 2, idea: 1, praise: 1)
   ```

   Plus any warnings on a separate line (corrupt frontmatter, etc.).

3. **Walk messages one by one.** For each message, in order:
   1. Read the file with `Read` and show frontmatter + body to the user.
   2. Use `AskUserQuestion` with four options:
      - **Promote → idea** — invokes the `taskmaster:add-idea` skill with the message body prefilled as the idea body and `summary` as the title. After the idea is created, archive the message: status `promoted`, `promoted_to: IDEA-NNN`.
      - **Promote → bug** — invokes the `taskmaster:bug` skill similarly. Archive with status `promoted`, `promoted_to: B-NNN`.
      - **Archive** — non-actionable but worth keeping. Archive with status `processed`.
      - **Drop** — noise. Archive with status `dropped`.
   3. Perform the chosen action.

4. **Archive via the script:**

   ```bash
   python -c "
   import sys
   from pathlib import Path
   sys.path.insert(0, r'${CLAUDE_PLUGIN_ROOT}')
   from scripts.archive_message import archive
   new_path = archive(Path(r'<message path>'), status='<processed|promoted|dropped>', promoted_to='<id or None>')
   print(f'archived → {new_path}')
   "
   ```

5. **Summarize.** After the walk, emit one line:

   ```
   inbox triage: <N> promoted, <M> archived, <K> dropped.
   ```

## Fallback when taskmaster isn't available

If you can't invoke `taskmaster:add-idea` or `taskmaster:bug` (e.g. user is running triage outside a taskmaster project), the **Promote** options fall back to archive-only with status `processed`. Emit one line explaining the fallback: `taskmaster not available here — archiving as processed instead of promoting.`

## Anti-patterns

- Skipping the per-message walk and bulk-archiving everything. Each message gets a decision.
- Deleting messages. Never. Archive only.
- Re-creating ideas/bugs from messages you've already archived in this session. If a message is moved out of `inbox/*.md`, it's done.
