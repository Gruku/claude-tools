---
description: Uninstall gruku-tools statusline — removes the statusLine entry from settings.json and (optionally) deletes statusline.config.json
argument-hint: [--keep-config] [--force]
disable-model-invocation: true
---

Uninstall the gruku-tools statusline. The plugin itself is left in place — run `/plugin uninstall statusline@gruku-tools` to remove it.

## Decide the flow

If $ARGUMENTS is empty, ask the user what to keep via a single AskUserQuestion call:

- "Also delete `~/.claude/statusline.config.json`?" — header `Config`. Yes (default) / No. Description: "Removes the saved toggles (showGit / showUpdateCheck / showLimitBars). Choose No if you might reinstall and want your toggles back."

Map "No" to `--keep-config`. "Yes" means omit the flag.

If $ARGUMENTS contains `--keep-config` or `--force`, skip the AskUserQuestion call and pass those flags through.

## Flag translation

| User flag      | uninstall.ps1   | uninstall.sh        |
|----------------|-----------------|---------------------|
| `--keep-config`| `-KeepConfig`   | `--keep-config`     |
| `--force`      | `-Force`        | `--force`           |

Always pass `-NonInteractive` (PowerShell) or `--non-interactive` (bash) so the uninstaller skips its own prompts.

## Run the uninstaller

Detect the platform from the runtime ($PSVersionTable on Windows, `uname` on Unix). On Windows use `pwsh` (or `powershell.exe` if pwsh is missing) to run `${CLAUDE_PLUGIN_ROOT}/uninstall.ps1`. On macOS/Linux run `bash ${CLAUDE_PLUGIN_ROOT}/uninstall.sh`. Run via the Bash tool, capture stdout, and print the uninstaller's output verbatim.

After the uninstaller exits 0, print one final line: **"Restart Claude Code to apply."** Nothing else.

If the uninstaller exits non-zero, print its stderr verbatim and stop.
