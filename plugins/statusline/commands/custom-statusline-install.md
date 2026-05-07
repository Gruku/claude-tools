---
description: Install gruku-tools statusline — wires settings.json to the version resolver and writes the toggle config. Args: --nogit, --noupdate
argument-hint: [--nogit] [--noupdate]
disable-model-invocation: true
---

Run the gruku-tools statusline installer non-interactively.

1. Detect platform from the runtime ($PSVersionTable on Windows, `uname` on Unix). On Windows use `pwsh` (or `powershell.exe` if pwsh is missing) to run `${CLAUDE_PLUGIN_ROOT}/install.ps1`. On macOS/Linux run `bash ${CLAUDE_PLUGIN_ROOT}/install.sh`.
2. Translate user-supplied flags from $ARGUMENTS:
   - `--nogit` → PowerShell `-NoGit`, bash `--no-git`
   - `--noupdate` → PowerShell `-NoUpdateCheck`, bash `--no-update-check`
3. Always pass `-NonInteractive` (PowerShell) or `--non-interactive` (bash) so the installer skips its y/N prompts and uses defaults + the user's flags.
4. Run the installer via the Bash tool, capturing stdout. Print the installer's output verbatim — the user wants to see what it did.
5. After the installer exits 0, print one final line: **"Restart Claude Code to apply."** Nothing else — no preamble, no summary.

If the installer exits non-zero, print its stderr verbatim and stop.
