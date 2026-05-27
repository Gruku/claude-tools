---
description: One-shot setup for feedback-inbox — writes ~/.claude/inbox-target.json and creates the inbox dir.
argument-hint: "[--inbox <path>] [--disable]"
---

Run the feedback-inbox setup.

## Procedure

1. **Parse `$ARGUMENTS`:**
   - `--inbox <path>` → explicit inbox path. If absent, ask the user with `AskUserQuestion`, offering two options:
     - **Inside this repo:** `<absolute path to claude-tools repo>/inbox`
     - **Outside any repo:** `~/.claude/inbox`
   - `--disable` → write `{"inbox": "<existing-or-default>", "enabled": false}` and stop.

2. **Resolve the path.** Expand `~` to the user home. Convert to absolute. Make sure no trailing slash.

3. **Write the config** at `~/.claude/inbox-target.json`:

   ```bash
   python -c "
   import json, os
   from pathlib import Path
   home = Path(os.environ.get('USERPROFILE') or os.environ.get('HOME') or Path.home())
   cfg = home / '.claude' / 'inbox-target.json'
   cfg.parent.mkdir(parents=True, exist_ok=True)
   cfg.write_text(json.dumps({'inbox': r'<resolved path>', 'enabled': True}, indent=2), encoding='utf-8')
   print(f'wrote {cfg}')
   "
   ```

4. **Create the inbox dir** (`mkdir -p <resolved path>`).

5. **Gitignore step (conditional).** If the inbox path sits inside a git working tree, append `inbox/` to that repo's `.gitignore` if and only if no existing line starts with `inbox/`. Skip silently otherwise.

   ```bash
   python -c "
   import subprocess, sys
   from pathlib import Path
   inbox = Path(r'<resolved path>')
   try:
       repo_root = subprocess.check_output(
           ['git', '-C', str(inbox.parent), 'rev-parse', '--show-toplevel'],
           stderr=subprocess.DEVNULL, text=True).strip()
   except subprocess.CalledProcessError:
       print('inbox is outside any git repo — no .gitignore edit needed'); sys.exit(0)
   repo_root = Path(repo_root)
   gi = repo_root / '.gitignore'
   existing = gi.read_text(encoding='utf-8') if gi.exists() else ''
   # Compute the path relative to the repo root; use forward slashes.
   rel = inbox.relative_to(repo_root).as_posix().rstrip('/') + '/'
   if any(line.strip() == rel for line in existing.splitlines()):
       print(f'.gitignore already has {rel}'); sys.exit(0)
   with gi.open('a', encoding='utf-8') as f:
       if existing and not existing.endswith('\n'):
           f.write('\n')
       f.write(f'\n# feedback-inbox\n{rel}\n')
   print(f'appended {rel} to {gi}')
   "
   ```

6. **Verify.** Run `python -c "import sys; sys.path.insert(0, r'${CLAUDE_PLUGIN_ROOT}'); from scripts.resolve_target import resolve_target; r = resolve_target(); print('ok' if r.enabled else f'fail: {r.reason}')"`. If it prints `ok`, emit:

   ```
   feedback-inbox set up. Inbox: <resolved path>. Use /inbox-feedback to log a message, /inbox to triage.
   ```

   Otherwise emit the failure reason.
