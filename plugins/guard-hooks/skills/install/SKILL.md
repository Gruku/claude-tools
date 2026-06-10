---
name: install
description: Install guard hooks into user-scoped ~/.claude/settings.json. Use when the user says "install guard hooks", "set up guard hooks", or "enable guard hooks".
---

# Install Guard Hooks

As of v2.7.x the guard hooks are **Python scripts auto-registered by the
plugin's own `hooks/hooks.json`** — enabling the plugin is the installation.
Do NOT copy hook scripts into `~/.claude/hooks/`; detached copies go stale
and stop matching the plugin's behavior (jq is no longer required either).

## Steps

1. Confirm the plugin is enabled (it is, if this skill is available). The
   hooks register automatically at session start; there is nothing to write
   into `~/.claude/settings.json`.

2. Check that a usable Python is available — run:

   ```bash
   python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' \
     || python -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' \
     || py -3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)'
   ```

   If none succeeds, tell the user the hooks will be INACTIVE (they fail
   open — tool calls work but nothing is guarded) and how to fix it:
   - Windows: `winget install Python.Python.3.12`
   - macOS: `brew install python`
   - Linux: `sudo apt install python3`
   - Or set `CLAUDE_HOOKS_PYTHON` to an interpreter command if Python is
     installed somewhere unusual.

3. Tell the user to restart their Claude Code session for the hooks to take
   effect (hook registrations are snapshotted at SessionStart).

## Migrating from a pre-plugin manual install

If `~/.claude/settings.json` contains old user-scoped guard entries
(commands referencing `~/.claude/hooks/guard-destructive.sh` or
`guard-edits.sh`), offer to remove those entries and delete the copied
scripts from `~/.claude/hooks/` — the plugin's auto-registered hooks
replace them, and leaving both active runs every guard twice.
