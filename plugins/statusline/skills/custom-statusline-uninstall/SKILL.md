---
name: custom-statusline-uninstall
description: This skill should be used when the user asks to "uninstall the statusline", "remove the custom statusline", "remove the gruku statusline", "turn off the statusline", or runs "/statusline:custom-statusline-uninstall". Runs the bundled uninstaller that removes the gruku-tools statusLine entry from settings.json and cleans its toggles. Leaves the plugin itself installed.
argument-hint: "[--keep-config] [--force]"
allowed-tools: Bash(powershell.exe:*), Bash(pwsh:*), Bash(bash:*), PowerShell, AskUserQuestion
---

<!-- User intent: undo the custom statusline install for the current account without touching foreign statusLine commands or shared config such as the accounts map. -->

# Custom Statusline Uninstall

The uninstaller works on `<claude dir>`, which is `$CLAUDE_CONFIG_DIR` when set and `~/.claude` otherwise. It makes two changes:

1. It removes `statusLine` from `<claude dir>/settings.json`, but only when the command is the gruku-tools launcher. That covers the plain-path form and the Windows `-EncodedCommand` form. Before changing the file, it writes a timestamped `settings.json.bak-*` backup.
2. Unless `--keep-config` is passed, it removes the toggle keys (`showGit`, `showUpdateCheck`, `showLimitBars`) from `<claude dir>/statusline.config.json`. Other keys, such as `accounts`, stay. The file is deleted only if nothing else is left in it and it is not a symlink.

The plugin itself stays installed. To remove the cached plugin files, run `/plugin uninstall statusline@gruku-tools`.

| Flag | uninstall.ps1 | Effect |
|---|---|---|
| `--keep-config` | `-KeepConfig` | Leave `statusline.config.json` untouched |
| `--force` | `-Force` | Remove `statusLine` even when it is not the gruku-tools one |

## Procedure

1. **Choose the flags.** If `$ARGUMENTS` contains either flag, use exactly what it contains. If it is empty, ask one AskUserQuestion: "Also remove the statusline toggles from statusline.config.json?" Use header `Config`, with Yes (default) or No. "No" becomes `--keep-config`.

2. **Run the uninstaller non-interactively.**
   - Windows: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File "${CLAUDE_PLUGIN_ROOT}/uninstall.ps1" -NonInteractive [-KeepConfig] [-Force]`
   - macOS / Linux: `bash "${CLAUDE_PLUGIN_ROOT}/uninstall.sh" --non-interactive [--keep-config] [--force]` (requires `jq`)

3. **Report.** Print the output verbatim.
   - Exit 0: add one final line, **"Restart Claude Code to apply."**
   - Exit 3: the configured statusLine is not the gruku-tools one, so nothing was changed. Ask before rerunning with `--force` / `-Force`.
   - Exit 1: a JSON file is invalid, so nothing was changed. Relay the message.

When accounts share `settings.json` through a symlink, one uninstall removes the statusline for every account that uses that file.
