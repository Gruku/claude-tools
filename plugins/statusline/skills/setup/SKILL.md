---
name: setup
description: Configure Claude Code to use the gruku-tools statusline. Use when the user says "set up statusline", "install statusline", "/statusline:setup", or right after installing the statusline plugin.
---

# Statusline Setup

This skill wires the bundled `statusline.sh` / `statusline.ps1` into the user's `~/.claude/settings.json` so Claude Code renders it on every turn.

## Steps

1. **Detect platform.** On Windows use the PowerShell script; on macOS / Linux use the Bash script.

2. **Check prerequisites.**
   - macOS / Linux: run `jq --version` and `git --version`. If `jq` is missing, tell the user to install it (`brew install jq` / `sudo apt install jq`) before continuing.
   - Windows: no prerequisites — PowerShell is built in. Warn the user that `git` should be on PATH for git status to render.

3. **Resolve the plugin script path.** The plugin installs at `${CLAUDE_PLUGIN_ROOT}` at runtime. The statusline command should reference the script inside the plugin so marketplace updates ship new versions automatically:
   - Bash: `bash "${CLAUDE_PLUGIN_ROOT}/statusline.sh"`
   - PowerShell: `powershell -NoProfile -File "%CLAUDE_PLUGIN_ROOT%\statusline.ps1"`

4. **Read `~/.claude/settings.json`.** Create it with `{}` if missing.

5. **Write the `statusLine` block.** Replace any existing `statusLine` key with:

   ```json
   {
     "statusLine": {
       "type": "command",
       "command": "bash \"${CLAUDE_PLUGIN_ROOT}/statusline.sh\""
     }
   }
   ```

   On Windows, the command becomes:

   ```json
   "command": "powershell -NoProfile -File \"%CLAUDE_PLUGIN_ROOT%\\statusline.ps1\""
   ```

   Preserve every other key in the settings file — only touch `statusLine`.

6. **Tell the user to reload.** Instruct them to run `/reload-plugins` and then restart Claude Code so the new statusLine config is picked up on the next session.

## If statusLine is already set

If `settings.json` already has a `statusLine.command`, show the current value and ask the user whether to overwrite it before writing. Don't silently replace a custom script.

## Troubleshooting

- **Raw escape codes visible** — terminal is not interpreting ANSI. See the project README for terminal-specific fixes (tmux `default-terminal`, macOS Terminal.app limits).
- **No rate-limit bars** — requires Claude Code v2.1.80 or later; bars also only render when usage crosses display thresholds.
- **`jq` errors on Bash** — install jq and restart the session.
