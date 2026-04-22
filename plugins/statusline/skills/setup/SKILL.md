---
name: setup
description: Configure Claude Code to use the gruku-tools statusline. Use when the user says "set up statusline", "install statusline", "/statusline:setup", or right after installing the statusline plugin.
---

# Statusline Setup

Wires the bundled `statusline.sh` / `statusline.ps1` into `~/.claude/settings.json` so Claude Code renders it on every turn.

## Why a setup step at all

Claude Code does NOT expand `${CLAUDE_PLUGIN_ROOT}` inside `statusLine.command` at runtime — that token only works in hook commands. So we must resolve the installed plugin path at setup time and bake an absolute path into settings.json. When the plugin updates to a new version, re-run `/statusline:setup` to repoint it.

## Steps

1. **Detect platform.** Windows → PowerShell script. macOS / Linux → Bash script.

2. **Check prerequisites.**
   - Bash: `jq --version` and `git --version`. Missing `jq` → tell the user to install it (`brew install jq` / `sudo apt install jq`) and stop.
   - PowerShell: no hard prerequisites. Recommend `git` on PATH for git status rendering.

3. **Resolve the installed plugin path.** Claude Code installs marketplace plugins into versioned cache directories:

   ```
   ~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/
   ```

   For this plugin the marketplace is `gruku-tools` and the plugin name is `statusline`. List the directory and pick the highest version (semver sort). Example on Windows:

   ```powershell
   Get-ChildItem "$env:USERPROFILE\.claude\plugins\cache\gruku-tools\statusline" -Directory |
     Sort-Object { [version]$_.Name } -Descending |
     Select-Object -First 1 |
     ForEach-Object { $_.FullName }
   ```

   Bash equivalent:

   ```bash
   ls -1 "$HOME/.claude/plugins/cache/gruku-tools/statusline" | sort -V | tail -1
   ```

   If the cache directory does not exist, tell the user to run `/plugin install statusline@gruku-tools` followed by `/reload-plugins` first.

4. **Build the `statusLine.command` string** using the resolved absolute path:
   - PowerShell: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File "<resolved>/statusline.ps1"`
   - Bash: `bash "<resolved>/statusline.sh"`

5. **Read `~/.claude/settings.json`** (create with `{}` if missing). If `statusLine.command` already exists and is not empty, show it and ask the user whether to overwrite before writing. Don't silently replace a custom script.

6. **Write the `statusLine` block**, preserving every other key:

   ```json
   {
     "statusLine": {
       "type": "command",
       "command": "<built in step 4>"
     }
   }
   ```

7. **Tell the user to restart Claude Code** so the new statusLine config is picked up on the next session. `/reload-plugins` alone does not re-read statusLine config.

## On plugin update

The absolute path includes a version number, so updating the plugin breaks the statusline. Users should re-run `/statusline:setup` after `/plugin update statusline@gruku-tools` — the skill resolves the new version path and rewrites settings.json.

## Troubleshooting

- **Statusline disappeared after editing settings.json** — likely `${CLAUDE_PLUGIN_ROOT}` or an unresolved path. Re-run this skill to write an absolute path.
- **Raw escape codes visible** — terminal not interpreting ANSI. See README for tmux / terminal-specific fixes.
- **No rate-limit bars** — requires Claude Code v2.1.80+.
- **`jq` errors on Bash** — install jq and restart the session.
