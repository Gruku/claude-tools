<!-- User intent: reference for when the installer can't run, plus the readable source behind the encoded Windows launcher. -->

# Manual install, launcher sources, troubleshooting

## Why a launcher

Claude Code caches marketplace plugins at `<claude dir>/plugins/cache/<marketplace>/<plugin>/<version>/`, and that path changes with every `/plugin update`. It does not expand `${CLAUDE_PLUGIN_ROOT}` inside `statusLine.command`, because that works only in hooks. The command therefore has to find the newest version itself each time it runs. It runs with the session's environment, so under `CLAUDE_CONFIG_DIR` it reads that account's plugin cache.

## Windows launcher

The single source of truth is `$script:LauncherSource` in `lib/statusline-common.ps1`. `install.ps1` normalizes it to LF, then encodes it as UTF-16LE base64 and writes this command:

```
powershell.exe -NoProfile -ExecutionPolicy Bypass -EncodedCommand <base64>
```

The decoded source:

```powershell
$ProgressPreference = 'SilentlyContinue'
$r = if ($env:CLAUDE_CONFIG_DIR) { $env:CLAUDE_CONFIG_DIR } else { Join-Path $env:USERPROFILE '.claude' }
$c = Join-Path $r 'plugins\cache\gruku-tools\statusline'
$d = @(Get-ChildItem -LiteralPath $c -Directory -ErrorAction SilentlyContinue | Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'statusline.ps1') })
$p = $d | Where-Object { $_.Name -as [version] } | Sort-Object { $_.Name -as [version] } -Descending | Select-Object -First 1
if (-not $p) { $p = $d | Sort-Object LastWriteTime -Descending | Select-Object -First 1 }
if ($p) { & (Join-Path $p.FullName 'statusline.ps1') } else { 'statusline: gruku-tools plugin not found in ' + $c }
```

The launcher skips directories that do not contain `statusline.ps1`. It uses the highest name that parses as a `[version]`. If none parses, it uses the most recently modified directory. If none is left, it prints a message instead of throwing.

To print the exact command without installing anything:

```powershell
. "<plugin root>\lib\statusline-common.ps1"; Get-LauncherCommand
```

To decode an existing command:

```powershell
[Text.Encoding]::Unicode.GetString([Convert]::FromBase64String('<base64>'))
```

## macOS / Linux launcher

The source is `launcher_command` in `lib/statusline-common.sh`:

```bash
bash -c 'c="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/plugins/cache/gruku-tools/statusline"; v=$(ls -1 "$c" 2>/dev/null | grep -E "^[0-9]+(\.[0-9]+)*$" | while read -r d; do [ -f "$c/$d/statusline.sh" ] && echo "$d"; done | sort -V | tail -1); [ -n "$v" ] || v=$(ls -1t "$c" 2>/dev/null | while read -r d; do [ -f "$c/$d/statusline.sh" ] && echo "$d"; done | head -1); if [ -n "$v" ]; then exec bash "$c/$v/statusline.sh"; fi; echo "statusline: gruku-tools plugin not found in $c"'
```

`exec` replaces the wrapper shell, which passes the status JSON on stdin straight through to the script.

## Manual install (no scripts)

1. Check that `<claude dir>/plugins/cache/gruku-tools/statusline/<version>/statusline.ps1` (or `statusline.sh`) exists.
2. Back up `<claude dir>/settings.json`. Set `statusLine` to `{"type": "command", "command": "<launcher above>"}` and keep all other keys. When writing the bash form into JSON, escape each `"` as `\"` and each `\` as `\\`.
3. Optionally, set `showGit`, `showUpdateCheck`, and `showLimitBars` in `<claude dir>/statusline.config.json` and keep all other keys.
4. Restart Claude Code.

"Ours" test, which the installer and uninstaller on both platforms share: the command contains `gruku-tools/statusline` or `gruku-tools\statusline` either in plain text or inside a decoded `-EncodedCommand` payload.

## Troubleshooting

- **Installer exits 3.** A different `statusLine` is configured. Rerun with `--force` / `-Force` to replace it.
- **Installer exits 1 with "not valid JSON".** Fix the named file, or restore it from a `settings.json.bak-*` backup. The installer changed nothing.
- **Console window flashes on each refresh.** The git credential helper is misconfigured. Reinstall with `--no-git` / `-NoGit`, and fix `git config credential.helper` to address the root cause.
- **Statusline shows "plugin not found".** The launcher found no version directory containing the script under that account's cache. Run `/plugin install statusline@gruku-tools` in that account.
- **Hangs on Windows.** A stale `CLAUDE_CODE_GIT_BASH_PATH` is the likely cause. `install.ps1` preflight reports it.
- **No rate-limit bars.** They require Claude Code v2.1.80 or later.
