---
description: Install gruku-tools statusline — wires settings.json to the version resolver and writes the toggle config. Args (optional): --nogit, --noupdate, --nobars
argument-hint: [--nogit] [--noupdate] [--nobars]
disable-model-invocation: true
---

Install the gruku-tools statusline. Detect whether the user passed any toggle flags in $ARGUMENTS:

- If $ARGUMENTS contains any of `--nogit`, `--noupdate`, `--nobars` → run **non-interactively** with the matching installer flags.
- If $ARGUMENTS is empty → ask the user about each toggle via the **AskUserQuestion** tool, then run non-interactively with the chosen flags.

## Interactive path (no $ARGUMENTS)

Use a single AskUserQuestion call with three questions, all single-select Yes/No:

1. "Enable git info on the statusline?" — header `Git`. Yes (default) / No. Description: "Branch + dirty markers on line 2. Disable if `git` flashes a console window or hangs (usually a misconfigured credential helper)."
2. "Enable Claude Code update check?" — header `Updates`. Yes (default) / No. Description: "Shows ↑ banner when a newer Claude Code is on npm. Runs `claude --version` once per session/hour."
3. "Show 5h / 7d rate-limit bars?" — header `Limits`. Yes (default) / No. Description: "Pip bars on line 2 with usage percentage and reset times."

Map each "No" answer to the corresponding installer flag (see below). "Yes" means omit the flag.

## Flag translation

| User flag (this command) | install.ps1     | install.sh           |
|--------------------------|-----------------|----------------------|
| `--nogit`                | `-NoGit`        | `--no-git`           |
| `--noupdate`             | `-NoUpdateCheck`| `--no-update-check`  |
| `--nobars`               | `-NoLimitBars`  | `--no-limit-bars`    |

Always pass `-NonInteractive` (PowerShell) or `--non-interactive` (bash) so the installer skips its own y/N prompts.

## Run the installer

Detect the platform from the runtime ($PSVersionTable on Windows, `uname` on Unix). On Windows use `pwsh` (or `powershell.exe` if pwsh is missing) to run `${CLAUDE_PLUGIN_ROOT}/install.ps1`. On macOS/Linux run `bash ${CLAUDE_PLUGIN_ROOT}/install.sh`. Run via the Bash tool, capture stdout, and print the installer's output verbatim — the user wants to see what it did.

After the installer exits 0, print one final line: **"Restart Claude Code to apply."** Nothing else — no preamble, no summary.

If the installer exits non-zero, print its stderr verbatim and stop.
