# Uninstaller for the gruku-tools statusline (Windows).
#
# - Removes `statusLine` from <claude dir>\settings.json, only if it is the gruku-tools
#   launcher (a custom command is left alone unless -Force)
# - Removes the toggle keys (showGit/showUpdateCheck/showLimitBars) from
#   <claude dir>\statusline.config.json unless -KeepConfig; other keys (e.g. `accounts`)
#   are kept, and the file is deleted only if nothing else is left in it
#
# <claude dir> = $env:CLAUDE_CONFIG_DIR if set, else %USERPROFILE%\.claude.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File uninstall.ps1   # interactive
#   ... -File uninstall.ps1 -KeepConfig        # leave statusline.config.json untouched
#   ... -File uninstall.ps1 -Force             # remove statusLine even if it isn't ours
#   ... -File uninstall.ps1 -NonInteractive    # no prompts
#
# Exit codes: 0 ok / nothing to do, 1 error (invalid JSON), 3 refused (foreign statusLine).

param(
    [switch]$KeepConfig,
    [switch]$Force,
    [switch]$NonInteractive
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'lib\statusline-common.ps1')

$claudeDir    = Get-ClaudeDir
$configPath   = Join-Path $claudeDir 'statusline.config.json'
$settingsPath = Join-Path $claudeDir 'settings.json'

Write-Host ""
Write-Host "gruku-tools statusline -- uninstaller" -ForegroundColor Cyan
Write-Host "====================================="
Write-Host "Claude config dir: $claudeDir"
Write-Host ""

try {
    $settingsFile = Read-JsonObjectFile $settingsPath
    $configFile   = if ($KeepConfig) { $null } else { Read-JsonObjectFile $configPath }
} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# --- Remove statusLine from settings.json ---
$settings = $settingsFile.Object
if (-not $settingsFile.Exists) {
    Write-Host "No $settingsPath found -- nothing to remove."
} elseif (-not $settings.PSObject.Properties['statusLine']) {
    Write-Host "No statusLine entry in $settingsPath -- nothing to remove."
} else {
    $existing = $null
    if ($settings.statusLine -and $settings.statusLine.PSObject.Properties['command']) {
        $existing = [string]$settings.statusLine.command
    }
    $remove = (Test-OurStatusLineCommand $existing) -or $Force
    if (-not $remove) {
        Write-Host "settings.json has a statusLine.command that isn't the gruku-tools one:" -ForegroundColor Yellow
        Write-Host "  $existing"
        if ($NonInteractive) {
            Write-Host "Refusing to remove it. Re-run with -Force to remove anyway. Nothing was changed." -ForegroundColor Red
            exit 3
        }
        $remove = Read-YesNo "Remove it anyway?" $false
    }
    if ($remove) {
        $newText = Remove-JsonTopMember $settingsFile.Text 'statusLine'
        $check = Assert-JsonObjectText $newText $settingsPath
        if ($check.PSObject.Properties['statusLine']) { throw "internal error: statusLine removal did not round-trip. Nothing was changed." }
        $bak = Backup-File $settingsPath
        Write-Host "Backed up $settingsPath -> $bak"
        Write-TextFile $settingsPath $newText
        Write-Host "Removed statusLine from $settingsPath" -ForegroundColor Green
    } else {
        Write-Host "Left statusLine in $settingsPath untouched." -ForegroundColor Yellow
    }
}

# --- Toggle config: drop our keys, keep the rest ---
if ($configFile -and $configFile.Exists) {
    $clean = $true
    if (-not $NonInteractive) {
        $clean = Read-YesNo "Remove the statusline toggles from $configPath too?" $true
    }
    if ($clean) {
        $configText = if ($configFile.Text.Trim()) { $configFile.Text } else { '{}' }
        foreach ($k in $script:ToggleKeys) { $configText = Remove-JsonTopMember $configText $k }
        $config = Assert-JsonObjectText $configText $configPath
        $isLink = [bool]((Get-Item -LiteralPath $configPath -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)
        if (@($config.PSObject.Properties).Count -eq 0 -and -not $isLink) {
            Remove-Item -LiteralPath $configPath -Force
            Write-Host "Deleted $configPath" -ForegroundColor Green
        } elseif ($configText -cne $configFile.Text) {
            Write-TextFile $configPath $configText
            Write-Host "Removed toggle keys from $configPath (other keys kept)" -ForegroundColor Green
        } else {
            Write-Host "No toggle keys in $configPath -- left untouched."
        }
    } else {
        Write-Host "Kept $configPath" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Restart Claude Code for changes to take effect." -ForegroundColor Cyan
Write-Host "The plugin itself is untouched -- run '/plugin uninstall statusline@gruku-tools' to remove it."
