---
name: custom-statusline-install
description: This skill should be used when the user asks to "set up the custom statusline", "install the gruku statusline", "reinstall the statusline", "turn off git in the statusline", "hide the rate-limit bars", "disable the update check", runs "/statusline:custom-statusline-install", or has just installed the statusline@gruku-tools plugin. It runs the bundled installer that points settings.json at the gruku-tools statusline. Distinct from Claude Code's built-in /statusline settings command. For removal, use custom-statusline-uninstall.
argument-hint: "[--no-git] [--no-update-check] [--no-limit-bars] [--force]"
allowed-tools: Bash(powershell.exe:*), Bash(pwsh:*), Bash(bash:*), PowerShell, AskUserQuestion
---

<!-- User intent: one entry point that installs the statusline safely for whichever account (CLAUDE_CONFIG_DIR) the session runs under, never clobbering foreign config. -->

# Custom Statusline Install

Run the bundled installer. It points `statusLine` in `<claude dir>/settings.json` at a launcher that resolves the newest cached plugin version on every refresh, and merges the toggles below into `<claude dir>/statusline.config.json`.

`<claude dir>` is `$CLAUDE_CONFIG_DIR` when set, else `~/.claude`. The installer targets the account of the current session; to cover another account, rerun it with that `CLAUDE_CONFIG_DIR`. If the accounts share `settings.json` through a symlink, one run covers both. Other keys in `statusline.config.json` (for example `accounts`) are kept.

## Toggles

| Key | Default | When `false` | Flag |
|---|---|---|---|
| `showGit` | `true` | No git branch or dirty markers. Use this if console windows flash on Windows. | `--no-git` |
| `showUpdateCheck` | `true` | No Claude Code update banner (skips the background npm version lookup) | `--no-update-check` |
| `showLimitBars` | `true` | No 5h / 7d rate-limit bars | `--no-limit-bars` |

`--force` replaces a `statusLine` that is not the gruku-tools one. Without it, the installer refuses and changes nothing.

## Procedure

1. **Choose the flags.** If `$ARGUMENTS` contains any of the flags above, use exactly those. If it is empty, ask one AskUserQuestion call with three single-select Yes/No questions: Git (header `Git`), update check (header `Updates`), and rate-limit bars (header `Limits`). All default to Yes. Each "No" becomes its `--no-*` flag. Add `--force` only if the user asked for it.

2. **Run the installer non-interactively.** On Windows, map the flags to the PowerShell names:

   | Flag | install.ps1 |
   |---|---|
   | `--no-git` | `-NoGit` |
   | `--no-update-check` | `-NoUpdateCheck` |
   | `--no-limit-bars` | `-NoLimitBars` |
   | `--force` | `-Force` |

   - Windows: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File "${CLAUDE_PLUGIN_ROOT}/install.ps1" -NonInteractive [mapped flags]`
   - macOS / Linux: `bash "${CLAUDE_PLUGIN_ROOT}/install.sh" --non-interactive [flags]` (requires `jq`)

3. **Report.** Print the installer's output verbatim.
   - Exit 0: add one final line, **"Restart Claude Code to apply."** (`/reload-plugins` does not re-read `statusLine`.)
   - Exit 3: another statusline is configured. Show the command the installer printed, then ask whether to replace it. If the user says yes, rerun with `--force` / `-Force`.
   - Exit 1: a JSON file is invalid or the plugin cache is missing. The installer changed nothing. Relay its message and stop.

## Behavior worth knowing

- Reruns are idempotent. If nothing changed, nothing is written.
- Before `settings.json` changes, a timestamped backup is made: `settings.json.bak-YYYYMMDD-HHMMSS`.
- A symlinked `settings.json` or `statusline.config.json` is written through its link, and the link stays in place.
- On Windows, only the `statusLine` entry and the toggle keys are edited in place, so every other byte stays the same. On macOS and Linux, `jq` re-serializes the file using its detected indentation.
- Files are written as UTF-8 without a BOM, and their existing newline style is kept.
- Running a plugin update needs no reinstall, because the launcher selects the newest version at runtime.

## Additional Resources

- **`references/manual-install.md`**: launcher sources, a manual install without the scripts, and troubleshooting.
