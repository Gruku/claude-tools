---
name: custom-statusline-install
description: Configure Claude Code to use the gruku-tools custom statusline (distinct from the native /statusline command which opens settings). Use when the user says "set up the custom statusline", "install the gruku statusline", "/statusline:custom-statusline-install", or right after installing the plugin.
---

# Custom Statusline Install

Wires the gruku-tools statusline (`statusline.sh` / `statusline.ps1`) into `~/.claude/settings.json` with a self-healing version resolver, and writes a toggle config at `~/.claude/statusline.config.json`.

The skill name is deliberately verbose to distinguish it from Claude Code's built-in `/statusline` command, which opens a settings UI. This one is an installer.

The fast path is the bundled installer — it does everything below, plus prompts for two toggles (`git info` and `update check`) that mitigate flashing console windows on Windows when a credential helper is misconfigured or `claude --version` is slow.

Prefer running the installer. The manual steps are a fallback for users who want to inspect or customize the wiring.

## Run the installer

- **Windows:** `pwsh -File ${CLAUDE_PLUGIN_ROOT}/install.ps1`
- **macOS / Linux:** `bash ${CLAUDE_PLUGIN_ROOT}/install.sh`

Args (same names on both platforms unless noted):

| Arg | Effect |
|---|---|
| `--no-git` (PS: `-NoGit`)             | Skip git-info section |
| `--no-update-check` (PS: `-NoUpdateCheck`) | Skip Claude Code update banner |
| `--non-interactive` (PS: `-NonInteractive`) | No prompts; use defaults + flags |

The installer writes `~/.claude/statusline.config.json` (toggles, hot-reloaded) and `~/.claude/settings.json` (resolver wiring, requires Claude Code restart).

The slash command `/statusline:custom-statusline-install` runs the installer in `--non-interactive` mode and forwards `--nogit` / `--noupdate` flags. Use the slash command for quick reconfig; run the installer directly in a terminal if you want the y/N prompts.

## Manual fallback

If the installer can't run (permissions, missing pwsh, etc.):

### Why a resolver

Claude Code installs marketplace plugins into `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`. The version path changes on every `/plugin update`. Claude Code does NOT expand `${CLAUDE_PLUGIN_ROOT}` inside `statusLine.command` (that token works only in hook commands). So the command must resolve the latest version at runtime.

### Steps

1. Verify the plugin is installed:
   - Windows: `Test-Path "$env:USERPROFILE\.claude\plugins\cache\gruku-tools\statusline"`
   - Bash: `test -d "$HOME/.claude/plugins/cache/gruku-tools/statusline"`

2. Bash side needs `jq`. PowerShell has no hard dependencies (recommend `git` on PATH for git-status rendering).

3. Read `~/.claude/settings.json` (create with `{}` if missing). Preserve all other keys.

4. Write the platform-specific `statusLine` block:

**Windows** — write this exact string into `settings.json.statusLine.command`:

```
powershell.exe -NoProfile -ExecutionPolicy Bypass -EncodedCommand JABwACAAPQAgACgARwBlAHQALQBDAGgAaQBsAGQASQB0AGUAbQAgACIAJABlAG4AdgA6AFUAUwBFAFIAUABSAE8ARgBJAEwARQBcAC4AYwBsAGEAdQBkAGUAXABwAGwAdQBnAGkAbgBzAFwAYwBhAGMAaABlAFwAZwByAHUAawB1AC0AdABvAG8AbABzAFwAcwB0AGEAdAB1AHMAbABpAG4AZQAiACAALQBEAGkAcgBlAGMAdABvAHIAeQAgAHwAIABTAG8AcgB0AC0ATwBiAGoAZQBjAHQAIAB7ACAAWwB2AGUAcgBzAGkAbwBuAF0AJABfAC4ATgBhAG0AZQAgAH0AIAAtAEQAZQBzAGMAZQBuAGQAaQBuAGcAIAB8ACAAUwBlAGwAZQBjAHQALQBPAGIAagBlAGMAdAAgAC0ARgBpAHIAcwB0ACAAMQApAC4ARgB1AGwAbABOAGEAbQBlADsAIAAmACAAIgAkAHAAXABzAHQAYQB0AHUAcwBsAGkAbgBlAC4AcABzADEAIgA=
```

The base64 is UTF-16-LE encoding of:

```powershell
$p = (Get-ChildItem "$env:USERPROFILE\.claude\plugins\cache\gruku-tools\statusline" -Directory | Sort-Object { [version]$_.Name } -Descending | Select-Object -First 1).FullName; & "$p\statusline.ps1"
```

To regenerate after editing the source:

```powershell
[Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes('<resolver-source>'))
```

**macOS / Linux** — JSON-escaped form for `settings.json.statusLine.command`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "bash -c 'latest=$(ls -1 \"$HOME/.claude/plugins/cache/gruku-tools/statusline\" | sort -V | tail -1); exec bash \"$HOME/.claude/plugins/cache/gruku-tools/statusline/$latest/statusline.sh\"'"
  }
}
```

`exec` replaces the wrapper shell with the statusline so the status JSON piped in by Claude Code reaches the script untouched.

5. Tell the user to restart Claude Code. `/reload-plugins` alone doesn't re-read `statusLine`.

## On plugin update

Nothing to do — the resolver re-globs the cache dir on every refresh and picks the highest version. `/plugin update statusline@gruku-tools` keeps the statusline working.

## Troubleshooting

- **Statusline blank after editing settings.json** — likely an unexpanded `${CLAUDE_PLUGIN_ROOT}` in the command. Re-run the installer.
- **Console window flashes per refresh** — git credential helper misconfigured (e.g., WSL-style path). Run installer with `--no-git` to silence the symptom; fix `git config credential.helper` for the root cause.
- **`sort -V` not available on stock macOS** — ships with macOS 10.14+. On older systems fall back to lexical `sort | tail -1`.
- **Raw escape codes visible** — terminal not interpreting ANSI. See README for tmux / terminal-specific fixes.
- **No rate-limit bars** — requires Claude Code v2.1.80+.
