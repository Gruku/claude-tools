---
name: install
description: Install guard hooks into user-scoped ~/.claude/settings.json. Use when the user says "install guard hooks", "set up guard hooks", or "enable guard hooks".
---

# Install Guard Hooks

This skill installs the guard-destructive and guard-edits hooks into the user's `~/.claude/settings.json`.

## Prerequisites

- `jq` must be installed and available in the user's PATH (the hooks use it to parse tool input)

## Steps

1. Check if `jq` is available by running `jq --version`. If not found, tell the user to install it first (`winget install jqlang.jq` on Windows, `brew install jq` on macOS, `apt install jq` on Linux).

2. Read `~/.claude/settings.json` to check if hooks are already configured.

3. If no `hooks` key exists, add the following to the top level of the settings JSON:

```json
"hooks": {
  "PreToolUse": [
    {
      "matcher": "Bash",
      "hooks": [
        {
          "type": "command",
          "command": "bash \"$HOME/.claude/hooks/guard-destructive.sh\""
        }
      ]
    },
    {
      "matcher": "Edit|Write",
      "hooks": [
        {
          "type": "command",
          "command": "bash \"$HOME/.claude/hooks/guard-edits.sh\""
        }
      ]
    }
  ]
}
```

4. Copy the hook scripts from the plugin to `~/.claude/hooks/`:
   - `guard-destructive.sh`
   - `guard-edits.sh`

5. Tell the user to restart their Claude Code session for the hooks to take effect.

## If hooks already exist

If `~/.claude/settings.json` already has a `hooks.PreToolUse` array, append the guard hook entries to the existing array rather than overwriting. Check for duplicates first — skip any matcher that already has a guard hook configured.
