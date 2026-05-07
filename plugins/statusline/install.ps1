# Interactive installer for the gruku-tools statusline (Windows).
#
# - Wires ~/.claude/settings.json -> the version-resolver command
# - Writes ~/.claude/statusline.config.json with feature toggles
#
# Usage:
#   pwsh -File install.ps1                                                  # interactive
#   pwsh -File install.ps1 -NoGit                                           # disable git section
#   pwsh -File install.ps1 -NoUpdateCheck                                   # disable update banner
#   pwsh -File install.ps1 -NoLimitBars                                     # hide 5h/7d rate-limit bars
#   pwsh -File install.ps1 -NoGit -NoUpdateCheck -NoLimitBars -NonInteractive  # scripted

param(
    [switch]$NoGit,
    [switch]$NoUpdateCheck,
    [switch]$NoLimitBars,
    [switch]$NonInteractive
)

$ErrorActionPreference = 'Stop'

$cacheDir     = Join-Path $env:USERPROFILE '.claude\plugins\cache\gruku-tools\statusline'
$configPath   = Join-Path $env:USERPROFILE '.claude\statusline.config.json'
$settingsPath = Join-Path $env:USERPROFILE '.claude\settings.json'

if (-not (Test-Path $cacheDir)) {
    Write-Host "ERROR: statusline plugin not found at $cacheDir" -ForegroundColor Red
    Write-Host "Run '/plugin install statusline@gruku-tools' in Claude Code first." -ForegroundColor Yellow
    exit 1
}

function Read-YesNo([string]$question, [bool]$default) {
    $hint = if ($default) { '[Y/n]' } else { '[y/N]' }
    $resp = Read-Host "$question $hint"
    if (-not $resp) { return $default }
    return ($resp -match '^\s*[Yy]')
}

if ($NonInteractive) {
    $showGit       = -not $NoGit
    $showUpdate    = -not $NoUpdateCheck
    $showLimitBars = -not $NoLimitBars
} else {
    Write-Host ""
    Write-Host "gruku-tools statusline -- installer" -ForegroundColor Cyan
    Write-Host "==================================="
    Write-Host ""
    Write-Host "Optional features can be disabled if you see flashing console"
    Write-Host "windows, hangs, or you just don't want them:"
    Write-Host ""
    Write-Host "  - Git info     : branch + dirty markers (runs 'git' per refresh,"
    Write-Host "                   may flash if a credential helper is misconfigured)"
    Write-Host "  - Update check : checks npm for a new Claude Code version"
    Write-Host "                   (runs 'claude --version' once per session/hour)"
    Write-Host "  - Limit bars   : 5h / 7d rate-limit bars on line 2"
    Write-Host ""
    $showGit       = Read-YesNo "Enable git info?"        $true
    $showUpdate    = Read-YesNo "Enable update check?"    $true
    $showLimitBars = Read-YesNo "Show rate-limit bars?"   $true
    Write-Host ""
}

# Write toggle config
$null = New-Item -ItemType Directory -Force -Path (Split-Path $configPath) -ErrorAction SilentlyContinue
[ordered]@{
    showGit         = $showGit
    showUpdateCheck = $showUpdate
    showLimitBars   = $showLimitBars
} | ConvertTo-Json | Set-Content $configPath -Encoding UTF8

Write-Host "Wrote $configPath" -ForegroundColor Green
Write-Host "  showGit         = $showGit"
Write-Host "  showUpdateCheck = $showUpdate"
Write-Host "  showLimitBars   = $showLimitBars"

# Ensure settings.json exists
if (-not (Test-Path $settingsPath)) {
    Set-Content $settingsPath '{}' -Encoding UTF8
}

# Load (preserves all other keys)
try {
    $settings = Get-Content $settingsPath -Raw | ConvertFrom-Json
} catch {
    Write-Host "WARN: $settingsPath is not valid JSON. Backing up to $settingsPath.bak" -ForegroundColor Yellow
    Copy-Item $settingsPath "$settingsPath.bak"
    $settings = [pscustomobject]@{}
}
if (-not $settings) { $settings = [pscustomobject]@{} }

# UTF-16-LE base64 of:
#   $p = (Get-ChildItem "$env:USERPROFILE\.claude\plugins\cache\gruku-tools\statusline" -Directory | Sort-Object { [version]$_.Name } -Descending | Select-Object -First 1).FullName; & "$p\statusline.ps1"
$encoded = 'JABwACAAPQAgACgARwBlAHQALQBDAGgAaQBsAGQASQB0AGUAbQAgACIAJABlAG4AdgA6AFUAUwBFAFIAUABSAE8ARgBJAEwARQBcAC4AYwBsAGEAdQBkAGUAXABwAGwAdQBnAGkAbgBzAFwAYwBhAGMAaABlAFwAZwByAHUAawB1AC0AdABvAG8AbABzAFwAcwB0AGEAdAB1AHMAbABpAG4AZQAiACAALQBEAGkAcgBlAGMAdABvAHIAeQAgAHwAIABTAG8AcgB0AC0ATwBiAGoAZQBjAHQAIAB7ACAAWwB2AGUAcgBzAGkAbwBuAF0AJABfAC4ATgBhAG0AZQAgAH0AIAAtAEQAZQBzAGMAZQBuAGQAaQBuAGcAIAB8ACAAUwBlAGwAZQBjAHQALQBPAGIAagBlAGMAdAAgAC0ARgBpAHIAcwB0ACAAMQApAC4ARgB1AGwAbABOAGEAbQBlADsAIAAmACAAIgAkAHAAXABzAHQAYQB0AHUAcwBsAGkAbgBlAC4AcABzADEAIgA='
$desired = "powershell.exe -NoProfile -ExecutionPolicy Bypass -EncodedCommand $encoded"

$existing = $null
if ($settings.PSObject.Properties['statusLine'] -and $settings.statusLine -and
    $settings.statusLine.PSObject.Properties['command']) {
    $existing = $settings.statusLine.command
}

if ($existing -and $existing -ne $desired -and -not $NonInteractive) {
    Write-Host ""
    Write-Host "settings.json already has a different statusLine.command:" -ForegroundColor Yellow
    Write-Host "  $existing"
    if (-not (Read-YesNo "Overwrite with the gruku-tools resolver?" $true)) {
        Write-Host "Kept existing command. Toggle config was still written." -ForegroundColor Yellow
        exit 0
    }
}

$newStatusLine = [pscustomobject]@{
    type    = 'command'
    command = $desired
}
if ($settings.PSObject.Properties['statusLine']) {
    $settings.statusLine = $newStatusLine
} else {
    $settings | Add-Member -NotePropertyName statusLine -NotePropertyValue $newStatusLine -Force
}

$settings | ConvertTo-Json -Depth 20 | Set-Content $settingsPath -Encoding UTF8
Write-Host "Wrote statusLine entry to $settingsPath" -ForegroundColor Green
Write-Host ""
Write-Host "Restart Claude Code for changes to take effect." -ForegroundColor Cyan
