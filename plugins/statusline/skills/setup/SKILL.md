---
name: setup
description: Configure Claude Code to use the gruku-tools statusline. Use when the user says "set up statusline", "install statusline", "/statusline:setup", or right after installing the statusline plugin.
---

# Statusline Setup

Wires the bundled `statusline.sh` / `statusline.ps1` into `~/.claude/settings.json` with a **self-healing resolver** that finds the latest installed plugin version at every invocation. Plugin updates don't break the statusline — no re-run of `/statusline:setup` needed.

## Why a resolver (and not a plain file path)

Claude Code installs marketplace plugins into `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`. The version in the path changes on every `/plugin update`. Claude Code does NOT expand `${CLAUDE_PLUGIN_ROOT}` inside `statusLine.command` (that token works only in hook commands — verified live, the statusline goes blank). So the command string must resolve the latest version at runtime.

## Steps

1. **Detect platform.** Windows → PowerShell + `-EncodedCommand`. macOS / Linux → Bash with `ls | sort -V | tail -1`.

2. **Check prerequisites.**
   - Bash: `jq --version` and `git --version`. Missing `jq` → tell the user to install it (`brew install jq` / `sudo apt install jq`) and stop.
   - PowerShell: no hard prerequisites. Recommend `git` on PATH for git status rendering.

3. **Verify the plugin is installed.** Confirm the cache directory exists:
   - Windows: `Test-Path "$env:USERPROFILE\.claude\plugins\cache\gruku-tools\statusline"`
   - Bash: `test -d "$HOME/.claude/plugins/cache/gruku-tools/statusline"`

   If missing, tell the user to run `/plugin install statusline@gruku-tools` and `/reload-plugins` first.

4. **Read `~/.claude/settings.json`** (create with `{}` if missing). If `statusLine.command` already exists and points at something other than the value below, show it and ask the user whether to overwrite.

5. **Write the platform-specific `statusLine` block**, preserving every other key in settings.json:

### Windows (PowerShell, `-EncodedCommand`)

The resolver source code (for reference — base64 below is this exact string, UTF-16-LE encoded):

```powershell
$p = (Get-ChildItem "$env:USERPROFILE\.claude\plugins\cache\gruku-tools\statusline" -Directory | Sort-Object { [version]$_.Name } -Descending | Select-Object -First 1).FullName; & "$p\statusline.ps1"
```

Write this exact value into `settings.json.statusLine.command`:

```
powershell.exe -NoProfile -ExecutionPolicy Bypass -EncodedCommand JABwACAAPQAgACgARwBlAHQALQBDAGgAaQBsAGQASQB0AGUAbQAgACIAJABlAG4AdgA6AFUAUwBFAFIAUABSAE8ARgBJAEwARQBcAC4AYwBsAGEAdQBkAGUAXABwAGwAdQBnAGkAbgBzAFwAYwBhAGMAaABlAFwAZwByAHUAawB1AC0AdABvAG8AbABzAFwAcwB0AGEAdAB1AHMAbABpAG4AZQAiACAALQBEAGkAcgBlAGMAdABvAHIAeQAgAHwAIABTAG8AcgB0AC0ATwBiAGoAZQBjAHQAIAB7ACAAWwB2AGUAcgBzAGkAbwBuAF0AJABfAC4ATgBhAG0AZQAgAH0AIAAtAEQAZQBzAGMAZQBuAGQAaQBuAGcAIAB8ACAAUwBlAGwAZQBjAHQALQBPAGIAagBlAGMAdAAgAC0ARgBpAHIAcwB0ACAAMQApAC4ARgB1AGwAbABOAGEAbQBlADsAIAAmACAAIgAkAHAAXABzAHQAYQB0AHUAcwBsAGkAbgBlAC4AcABzADEAIgA=
```

`-EncodedCommand` takes a UTF-16-LE base64 string and avoids all nested-quote hell. If you need to regenerate it (e.g., to tweak the resolver logic), run:

```powershell
[Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes('<resolver-source>'))
```

### macOS / Linux (Bash)

Write this into `settings.json.statusLine.command`:

```
bash -c 'latest=$(ls -1 "$HOME/.claude/plugins/cache/gruku-tools/statusline" | sort -V | tail -1); exec bash "$HOME/.claude/plugins/cache/gruku-tools/statusline/$latest/statusline.sh"'
```

JSON-escaped inside settings.json (outer `"` → `\"`):

```json
{
  "statusLine": {
    "type": "command",
    "command": "bash -c 'latest=$(ls -1 \"$HOME/.claude/plugins/cache/gruku-tools/statusline\" | sort -V | tail -1); exec bash \"$HOME/.claude/plugins/cache/gruku-tools/statusline/$latest/statusline.sh\"'"
  }
}
```

`exec` replaces the wrapper shell with the statusline process so stdin is inherited directly — the status JSON Claude Code pipes in reaches the script untouched.

6. **Sanity-test before writing** (optional but nice). Pipe a minimal JSON payload through the command string and confirm it emits ANSI output:

   ```bash
   echo '{"workspace":{"current_dir":"/tmp"},"model":{"display_name":"Opus"},"session_id":"t"}' | bash -c '...'
   ```

7. **Tell the user to restart Claude Code.** `/reload-plugins` alone doesn't re-read `statusLine`.

## On plugin update

Do nothing — the resolver re-globs the cache dir every invocation and picks the highest version. Users can run `/plugin update statusline@gruku-tools` and the statusline keeps working.

## Troubleshooting

- **Statusline blank after editing settings.json** — `${CLAUDE_PLUGIN_ROOT}` or an unresolved variable in the command. Re-run this skill.
- **`sort -V` not available on stock macOS** — it ships with `sort` from coreutils on Linux; macOS `sort` has had `-V` since 10.14. On very old macOS fall back to plain lexical sort (`sort | tail -1`) — works for v0-v9 releases.
- **Raw escape codes visible** — terminal not interpreting ANSI. See README for tmux / terminal-specific fixes.
- **No rate-limit bars** — requires Claude Code v2.1.80+.
