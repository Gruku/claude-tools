---
name: custom-statusline-install
description: Configure Claude Code to use the gruku-tools custom statusline (distinct from the native /statusline command which opens settings). Use when the user says "set up the custom statusline", "install the gruku statusline", "/statusline:custom-statusline-install", or right after installing the plugin. Also handles uninstall ("remove the statusline", "/statusline:custom-statusline-uninstall").
---

# Custom Statusline Install / Uninstall

Wires the gruku-tools statusline (`statusline.sh` / `statusline.ps1`) into `~/.claude/settings.json` via a self-healing version resolver, and writes a toggle config at `~/.claude/statusline.config.json`. Also tears it back down on request.

The skill name is deliberately verbose to distinguish it from Claude Code's built-in `/statusline` command, which opens a settings UI. This one is an installer.

## Toggles

`~/.claude/statusline.config.json` (hot-reloaded by the statusline on each refresh):

| Key               | Default | Effect when `false` |
|-------------------|---------|---------------------|
| `showGit`         | `true`  | Skip git branch + dirty markers (mitigates flashing console windows on Windows when a credential helper is misconfigured) |
| `showUpdateCheck` | `true`  | Skip the `↑ vX → vY` Claude Code update banner (skips `claude --version` + npm registry call) |
| `showLimitBars`   | `true`  | Hide the 5h / 7d rate-limit bars on line 2 |

## Install — interactive (recommended)

When the user asks to install (or runs `/statusline:custom-statusline-install` with no args), drive the questionnaire from Claude using a **single AskUserQuestion call** with three single-select Y/N questions covering the toggles above. Defaults are all "Yes" (full statusline).

Then call the installer in non-interactive mode, passing flags for any "No" answers:

| Toggle answer | install.ps1 flag | install.sh flag      |
|---------------|------------------|----------------------|
| Git = No      | `-NoGit`         | `--no-git`           |
| Update = No   | `-NoUpdateCheck` | `--no-update-check`  |
| Limits = No   | `-NoLimitBars`   | `--no-limit-bars`    |

Always also pass `-NonInteractive` / `--non-interactive` to suppress the installer's own y/N prompts.

- **Windows:** `pwsh -File ${CLAUDE_PLUGIN_ROOT}/install.ps1 -NonInteractive [flags]`
- **macOS / Linux:** `bash ${CLAUDE_PLUGIN_ROOT}/install.sh --non-interactive [flags]`

After exit 0, tell the user to restart Claude Code (`/reload-plugins` doesn't re-read `statusLine`).

## Install — direct script

If the user wants to run the installer themselves (or we're outside Claude), the scripts have their own y/N prompts:

```
pwsh -File install.ps1               # asks: git? update? limit bars?
bash install.sh                       # same, on macOS/Linux
```

Same flags work as above for fully-scripted runs.

## Uninstall

Trigger when the user says "uninstall the statusline", "remove the statusline", or runs `/statusline:custom-statusline-uninstall`.

Drive a **single AskUserQuestion** call asking whether to also delete `~/.claude/statusline.config.json` (default Yes). Then run:

- **Windows:** `pwsh -File ${CLAUDE_PLUGIN_ROOT}/uninstall.ps1 -NonInteractive [-KeepConfig]`
- **macOS / Linux:** `bash ${CLAUDE_PLUGIN_ROOT}/uninstall.sh --non-interactive [--keep-config]`

What it does:
1. Removes `statusLine` from `~/.claude/settings.json` — but only if the existing command points at the gruku-tools resolver (string contains `gruku-tools/statusline` or `gruku-tools\statusline`). If it points elsewhere, the uninstaller leaves it alone unless `-Force` / `--force` is passed.
2. Optionally deletes `~/.claude/statusline.config.json`.
3. Leaves the plugin itself installed. Run `/plugin uninstall statusline@gruku-tools` to remove the cached plugin files.

Tell the user to restart Claude Code afterward.

## Why a resolver

Claude Code installs marketplace plugins into `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`. The version path changes on every `/plugin update`. Claude Code does NOT expand `${CLAUDE_PLUGIN_ROOT}` inside `statusLine.command` (that token works only in hook commands). So the command has to resolve the latest version at runtime.

On plugin update — nothing to do. The resolver re-globs the cache dir on every refresh and picks the highest version.

## Manual fallback (no installer)

If the installer can't run (permissions, missing pwsh, etc.):

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

## Troubleshooting

- **Statusline blank after editing settings.json** — likely an unexpanded `${CLAUDE_PLUGIN_ROOT}` in the command. Re-run the installer.
- **Console window flashes per refresh** — git credential helper misconfigured (e.g., WSL-style path). Re-run the installer and answer "No" to git, or pass `--no-git` / `-NoGit`. Fix `git config credential.helper` for the root cause.
- **Don't want the rate-limit bars** — re-run the installer and answer "No" to limit bars (or `--no-limit-bars` / `-NoLimitBars`).
- **`sort -V` not available on stock macOS** — ships with macOS 10.14+. On older systems fall back to lexical `sort | tail -1`.
- **Raw escape codes visible** — terminal not interpreting ANSI. See README for tmux / terminal-specific fixes.
- **No rate-limit bars** — requires Claude Code v2.1.80+.
