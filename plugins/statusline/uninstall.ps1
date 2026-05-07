# Uninstaller for the gruku-tools statusline (Windows).
#
# - Removes the `statusLine` key from ~/.claude/settings.json (only if it
#   points at the gruku-tools resolver — leaves a custom command alone)
# - Optionally deletes ~/.claude/statusline.config.json
#
# Usage:
#   pwsh -File uninstall.ps1                        # interactive
#   pwsh -File uninstall.ps1 -KeepConfig            # leave statusline.config.json in place
#   pwsh -File uninstall.ps1 -Force                 # remove statusLine even if it isn't ours
#   pwsh -File uninstall.ps1 -NonInteractive        # no prompts; default = remove config

param(
    [switch]$KeepConfig,
    [switch]$Force,
    [switch]$NonInteractive
)

$ErrorActionPreference = 'Stop'

$configPath   = Join-Path $env:USERPROFILE '.claude\statusline.config.json'
$settingsPath = Join-Path $env:USERPROFILE '.claude\settings.json'

function Read-YesNo([string]$question, [bool]$default) {
    $hint = if ($default) { '[Y/n]' } else { '[y/N]' }
    $resp = Read-Host "$question $hint"
    if (-not $resp) { return $default }
    return ($resp -match '^\s*[Yy]')
}

Write-Host ""
Write-Host "gruku-tools statusline -- uninstaller" -ForegroundColor Cyan
Write-Host "====================================="
Write-Host ""

# --- Remove statusLine from settings.json ---
if (Test-Path $settingsPath) {
    try {
        $settings = Get-Content $settingsPath -Raw | ConvertFrom-Json
    } catch {
        Write-Host "WARN: $settingsPath is not valid JSON. Backing up to $settingsPath.bak" -ForegroundColor Yellow
        Copy-Item $settingsPath "$settingsPath.bak"
        $settings = $null
    }

    if ($settings -and $settings.PSObject.Properties['statusLine']) {
        $existing = $null
        if ($settings.statusLine -and $settings.statusLine.PSObject.Properties['command']) {
            $existing = $settings.statusLine.command
        }

        # Detect "ours": either the resolver path is visible (older installs / direct paths)
        # or the EncodedCommand prefix matches our base64 resolver. The current installer
        # encodes the path into UTF-16-LE base64 starting with "JABwACAAPQAg" ("$p = ...").
        $isOurs = $existing -and (
            ($existing -match 'gruku-tools[\\/]+statusline') -or
            ($existing -match 'EncodedCommand\s+JABwACAAPQAg')
        )
        $remove = $isOurs -or $Force

        if (-not $remove -and -not $NonInteractive) {
            Write-Host "settings.json has a statusLine.command that doesn't look like ours:" -ForegroundColor Yellow
            Write-Host "  $existing"
            $remove = Read-YesNo "Remove anyway?" $false
        }

        if ($remove) {
            $settings.PSObject.Properties.Remove('statusLine')
            $settings | ConvertTo-Json -Depth 20 | Set-Content $settingsPath -Encoding UTF8
            Write-Host "Removed statusLine from $settingsPath" -ForegroundColor Green
        } else {
            Write-Host "Left statusLine in $settingsPath untouched." -ForegroundColor Yellow
        }
    } else {
        Write-Host "No statusLine entry in $settingsPath -- nothing to remove."
    }
} else {
    Write-Host "No $settingsPath found -- nothing to remove."
}

# --- Optionally delete the toggle config ---
if (Test-Path $configPath) {
    $deleteConfig = -not $KeepConfig
    if (-not $NonInteractive -and -not $KeepConfig) {
        $deleteConfig = Read-YesNo "Delete $configPath too?" $true
    }
    if ($deleteConfig) {
        Remove-Item $configPath -Force
        Write-Host "Deleted $configPath" -ForegroundColor Green
    } else {
        Write-Host "Kept $configPath" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Restart Claude Code for changes to take effect." -ForegroundColor Cyan
Write-Host "The plugin itself is untouched -- run '/plugin uninstall statusline@gruku-tools' to remove it."
