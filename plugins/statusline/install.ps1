# Installer for the gruku-tools statusline (Windows).
#
# - Points <claude dir>\settings.json statusLine at a version-resolving launcher
# - Merges feature toggles into <claude dir>\statusline.config.json (other keys, e.g. `accounts`, kept)
#
# <claude dir> = $env:CLAUDE_CONFIG_DIR if set, else %USERPROFILE%\.claude.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File install.ps1                 # interactive
#   ... -File install.ps1 -NoGit                   # disable git section
#   ... -File install.ps1 -NoUpdateCheck           # disable update banner
#   ... -File install.ps1 -NoLimitBars             # hide 5h/7d rate-limit bars
#   ... -File install.ps1 -Force                   # replace a statusLine that isn't ours
#   ... -File install.ps1 -NonInteractive [flags]  # scripted, no prompts
#
# Exit codes: 0 ok / nothing to do, 1 error (plugin missing, invalid JSON), 3 refused (foreign statusLine).

param(
    [switch]$NoGit,
    [switch]$NoUpdateCheck,
    [switch]$NoLimitBars,
    [switch]$Force,
    [switch]$NonInteractive
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'lib\statusline-common.ps1')

$claudeDir    = Get-ClaudeDir
$cacheDir     = Get-PluginCacheDir $claudeDir
$configPath   = Join-Path $claudeDir 'statusline.config.json'
$settingsPath = Join-Path $claudeDir 'settings.json'

if (-not (Test-PluginInstalled $cacheDir 'statusline.ps1')) {
    Write-Host "ERROR: no statusline.ps1 found under $cacheDir\<version>\" -ForegroundColor Red
    Write-Host "Run '/plugin install statusline@gruku-tools' in Claude Code first." -ForegroundColor Yellow
    exit 1
}

function Invoke-PreflightChecks {
    Write-Host "Preflight checks:" -ForegroundColor Cyan
    $warnings = 0

    # A stale CLAUDE_CODE_GIT_BASH_PATH makes Claude Code hang silently on every shell
    # command, including statusLine.command.
    $scopes = @(
        @{ Name = 'User';    Value = [Environment]::GetEnvironmentVariable('CLAUDE_CODE_GIT_BASH_PATH','User') },
        @{ Name = 'Machine'; Value = [Environment]::GetEnvironmentVariable('CLAUDE_CODE_GIT_BASH_PATH','Machine') }
    )
    $sawAny = $false
    foreach ($s in $scopes) {
        if (-not $s.Value) { continue }
        $sawAny = $true
        if (Test-Path $s.Value) {
            Write-Host "  [OK]   CLAUDE_CODE_GIT_BASH_PATH ($($s.Name)) -> $($s.Value)" -ForegroundColor Green
        } else {
            Write-Host "  [WARN] CLAUDE_CODE_GIT_BASH_PATH ($($s.Name)) points at a missing file:" -ForegroundColor Yellow
            Write-Host "         $($s.Value)"
            Write-Host "         Claude Code will hang trying to run shell commands (including this statusline)."
            Write-Host "         Fix:" -ForegroundColor Yellow
            Write-Host "           [Environment]::SetEnvironmentVariable('CLAUDE_CODE_GIT_BASH_PATH', `$null, '$($s.Name)')"
            Write-Host "         Then FULLY kill every claude.exe / node.exe in Task Manager and relaunch from PowerShell."
            $warnings++
        }
    }
    if (-not $sawAny) {
        Write-Host "  [OK]   CLAUDE_CODE_GIT_BASH_PATH not set (Claude Code will auto-detect Git Bash)." -ForegroundColor Green
    }

    # WSL bash.exe stub on PATH -- informational breadcrumb if shell commands ever hang.
    $bashSrc = (Get-Command bash -ErrorAction SilentlyContinue).Source
    if ($bashSrc -eq 'C:\Windows\System32\bash.exe') {
        Write-Host "  [INFO] 'bash' on PATH resolves to the WSL launcher ($bashSrc)." -ForegroundColor DarkGray
        Write-Host "         Harmless on its own. If the statusline ever stops rendering and the popup's" -ForegroundColor DarkGray
        Write-Host "         title bar shows '/usr/bin/bash --login -i -c ...', re-run this installer." -ForegroundColor DarkGray
    }
    Write-Host "  [OK]   Claude config dir: $claudeDir" -ForegroundColor Green
    Write-Host ""
    return $warnings
}

# --- Read everything first; abort before any write if a file is unreadable ---
try {
    $settingsFile = Read-JsonObjectFile $settingsPath
    $configFile   = Read-JsonObjectFile $configPath
} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
$settings = $settingsFile.Object
$config   = $configFile.Object

$desired = Get-LauncherCommand
$existing = $null
if ($settings.PSObject.Properties['statusLine'] -and $settings.statusLine -and
    $settings.statusLine.PSObject.Properties['command']) {
    $existing = [string]$settings.statusLine.command
}

$preflightWarnings = Invoke-PreflightChecks
if ($preflightWarnings -gt 0 -and -not $NonInteractive) {
    if (-not (Read-YesNo "Continue with install despite the warnings?" $true)) {
        Write-Host "Aborted. Resolve the warnings above and re-run." -ForegroundColor Yellow
        exit 0
    }
    Write-Host ""
}

# A statusLine that isn't ours is never replaced silently.
if ($existing -and -not (Test-OurStatusLineCommand $existing) -and -not $Force) {
    Write-Host "settings.json already has a statusLine.command that isn't the gruku-tools one:" -ForegroundColor Yellow
    Write-Host "  $existing"
    if ($NonInteractive) {
        Write-Host "Refusing to replace it. Re-run with -Force to overwrite. Nothing was changed." -ForegroundColor Red
        exit 3
    }
    if (-not (Read-YesNo "Overwrite it with the gruku-tools launcher?" $false)) {
        Write-Host "Kept the existing command. Nothing was changed." -ForegroundColor Yellow
        exit 0
    }
}

if ($NonInteractive) {
    $showGit       = -not $NoGit
    $showUpdate    = -not $NoUpdateCheck
    $showLimitBars = -not $NoLimitBars
} else {
    Write-Host "gruku-tools statusline -- installer" -ForegroundColor Cyan
    Write-Host "==================================="
    Write-Host ""
    Write-Host "Optional features can be disabled if you see flashing console"
    Write-Host "windows, hangs, or you just don't want them:"
    Write-Host ""
    Write-Host "  - Git info     : branch + dirty markers (runs 'git' per refresh,"
    Write-Host "                   may flash if a credential helper is misconfigured)"
    Write-Host "  - Update check : banner when npm has a newer Claude Code"
    Write-Host "                   (version comes from the session; npm is queried in the background)"
    Write-Host "  - Limit bars   : 5h / 7d rate-limit bars on line 2"
    Write-Host ""
    $showGit       = if ($NoGit)         { $false } else { Read-YesNo "Enable git info?"      $true }
    $showUpdate    = if ($NoUpdateCheck) { $false } else { Read-YesNo "Enable update check?"  $true }
    $showLimitBars = if ($NoLimitBars)   { $false } else { Read-YesNo "Show rate-limit bars?" $true }
    Write-Host ""
}

# --- Toggle config: merge, keep every other key (accounts, ...) ---
$toggles = [ordered]@{ showGit = [bool]$showGit; showUpdateCheck = [bool]$showUpdate; showLimitBars = [bool]$showLimitBars }
$configText = if ($configFile.Text.Trim()) { $configFile.Text } else { '{}' + "`n" }
$configChanged = $false
foreach ($k in $toggles.Keys) {
    $prop = $config.PSObject.Properties[$k]
    if (-not $prop -or $prop.Value -isnot [bool] -or $prop.Value -ne $toggles[$k]) {
        $configText = Set-JsonTopMember $configText $k $toggles[$k]
        $configChanged = $true
    }
}
if ($configChanged) {
    $null = Assert-JsonObjectText $configText $configPath
    Write-TextFile $configPath $configText
    Write-Host "Updated $configPath" -ForegroundColor Green
} else {
    Write-Host "$configPath already up to date" -ForegroundColor Green
}
Write-Host "  showGit         = $showGit"
Write-Host "  showUpdateCheck = $showUpdate"
Write-Host "  showLimitBars   = $showLimitBars"

# --- settings.json statusLine ---
if ($existing -ceq $desired -and $settings.statusLine.PSObject.Properties['type'] -and $settings.statusLine.type -eq 'command') {
    Write-Host "statusLine in $settingsPath already current" -ForegroundColor Green
} else {
    $settingsText = Set-JsonTopMember $settingsFile.Text 'statusLine' ([ordered]@{ type = 'command'; command = $desired })
    $check = Assert-JsonObjectText $settingsText $settingsPath
    if ($check.statusLine.command -cne $desired) { throw "internal error: statusLine edit did not round-trip. Nothing was changed." }
    if ($settingsFile.Exists) {
        $bak = Backup-File $settingsPath
        Write-Host "Backed up $settingsPath -> $bak"
    }
    Write-TextFile $settingsPath $settingsText
    Write-Host "Wrote statusLine entry to $settingsPath" -ForegroundColor Green
}
Write-Host ""
Write-Host "Restart Claude Code for changes to take effect." -ForegroundColor Cyan
