# Claude Code statusline — pastel, brightness squares, git+github, gradient limits
# Line 1: dir  model  ■⬓□ pct%  [$cost]  [agent]  [vim:MODE]  [↑ update]
# Line 2: ⎇ branch [✔ ~]  limit_bars [reset times]  [⚡ extra usage]
#
# Official docs:
#   https://code.claude.com/docs/en/statusline
#
# Reference implementations:
#   https://github.com/NoobyGains/claude-pulse        — Python, rainbow animation, OAuth usage API, update notifications
#   https://github.com/sirmalloc/ccstatusline          — pre-built themes and configs
#   https://github.com/martinemde/starship-claude      — Starship prompt integration
#
# Installation (Windows/PowerShell):
#   1. Save this script, e.g. to ~/.claude/statusline.ps1
#   2. Add to ~/.claude/settings.json:
#        {
#          "statusLine": {
#            "command": "powershell -NoProfile -File \"%USERPROFILE%\\.claude\\statusline.ps1\""
#          }
#        }
#   3. Rate limit bars require OAuth login — run `claude` and sign in.
#      Credentials are read from ~/.claude/.credentials.json automatically.
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$esc = [char]27
$bel = [char]7

# --- Pastel palette ---
$cSand   = "$esc[38;2;205;185;165m"
$cPeach  = "$esc[38;2;195;160;155m"
$cLav    = "$esc[38;2;165;150;200m"
$cSage   = "$esc[38;2;135;180;160m"
$cMauve  = "$esc[38;2;185;140;160m"
$cSalmon = "$esc[38;2;205;140;125m"
$cSlate  = "$esc[38;2;140;160;185m"   # git branch - dusty blue
$cAmber  = "$esc[38;2;235;195;80m"    # bright warm yellow - update alert
$cDim    = "$esc[38;2;80;75;70m"
$cDimmer = "$esc[38;2;60;58;55m"
$R       = "$esc[0m"

$dimR = 50; $dimG = 48; $dimB = 45
$neuR = 195; $neuG = 180; $neuB = 165

# --- Gradient RGB (green -> amber -> red) ---
function Get-GradRGB([int]$p) {
    $p = [math]::Max(0, [math]::Min(100, $p))
    if ($p -le 60) {
        $t = $p / 60.0
        return @([int](130+50*$t), [int](190+5*$t), [int](150-30*$t))
    } elseif ($p -le 80) {
        $t = ($p-60) / 20.0
        return @([int](180+30*$t), [int](195-20*$t), [int](120-20*$t))
    } else {
        $t = ($p-80) / 20.0
        return @(210, [int](175-80*$t), [int](100-15*$t))
    }
}

function Get-GradColor([int]$p) {
    $rgb = Get-GradRGB $p
    return "$esc[38;2;$($rgb[0]);$($rgb[1]);$($rgb[2])m"
}

# --- Limit-bar gradient (80%=green, 100%=red, saturation ramps at high %) ---
function Get-LimitGradRGB([int]$p) {
    $p = [math]::Max(0, [math]::Min(100, $p))
    if ($p -le 80) {
        $r = 130; $g = 190; $b = 150
    } elseif ($p -le 90) {
        $t = ($p - 80) / 10.0
        $r = [int](130 + 80*$t);  $g = [int](190 - 15*$t);  $b = [int](150 - 50*$t)
    } else {
        $t = ($p - 90) / 10.0
        $r = 210; $g = [int](175 - 80*$t); $b = [int](100 - 15*$t)
    }
    # Dynamic muting: muted at <=80%, increasingly saturated toward 100%
    if ($p -le 80) { $mf = 0.75 }
    else { $mf = 0.75 + 0.25 * (($p - 80) / 20.0) }
    return @([int]($dimR + ($r - $dimR) * $mf), [int]($dimG + ($g - $dimG) * $mf), [int]($dimB + ($b - $dimB) * $mf))
}

function Get-LimitGradColor([int]$p) {
    $rgb = Get-LimitGradRGB $p
    return "$esc[38;2;$($rgb[0]);$($rgb[1]);$($rgb[2])m"
}

# --- Read JSON ---
$inputData = [System.Console]::In.ReadToEnd()
$data = $inputData | ConvertFrom-Json

# --- Directory (project_dir:relative when cwd differs) ---
$projDir = $data.workspace.current_dir
if ($data.workspace.PSObject.Properties['project_dir'] -and $data.workspace.project_dir) {
    $projDir = $data.workspace.project_dir
}
$curDir = $data.workspace.current_dir
$projName = Split-Path -Leaf $projDir

if ($curDir -ne $projDir -and $curDir.StartsWith($projDir)) {
    $relPath = $curDir.Substring($projDir.Length).TrimStart('\', '/')
    $dirDisplay = "${projName}${cDim}:${cSand}${relPath}"
} elseif ($curDir -ne $projDir) {
    $dirDisplay = "${projName}${cDim}:${cSand}$(Split-Path -Leaf $curDir)"
} else {
    $dirDisplay = $projName
}

# --- Basic info ---
$model = $data.model.display_name
$agentName = ""
if ($data.PSObject.Properties['agent'] -and $data.agent -and
    $data.agent.PSObject.Properties['name'] -and $data.agent.name) {
    $agentName = $data.agent.name
}

# --- Vim mode (only when active) ---
$vimMode = ""
if ($data.PSObject.Properties['vim'] -and $data.vim -and
    $data.vim.PSObject.Properties['mode'] -and $data.vim.mode) {
    $vimMode = $data.vim.mode
}


# --- Read Claude Code config (autoCompact) ---
$autoCompactOn = $true   # default when absent
$configPath = Join-Path ([System.Environment]::GetFolderPath('UserProfile')) ".claude\settings.json"
if (Test-Path $configPath) {
    try {
        $ccConfig = Get-Content $configPath -Raw | ConvertFrom-Json
        if ($ccConfig.PSObject.Properties['autoCompact'] -and $ccConfig.autoCompact -eq $false) {
            $autoCompactOn = $false
        }
    } catch {}
}

# --- Context percentage (adjusted for autocompact buffer) ---
# When autocompact is on, it reserves ~33000 tokens (20000 max_output + 13000 buffer).
# used_percentage is raw % of total window — we recalculate against usable space.
$pct = 0
if ($data.PSObject.Properties['context_window']) {
    $cw = $data.context_window
    $size = if ($cw.PSObject.Properties['context_window_size']) { [int]$cw.context_window_size } else { 0 }
    $autocompactBuffer = if ($autoCompactOn) { 33000 } else { 0 }

    if ($cw.PSObject.Properties['current_usage'] -and $null -ne $cw.current_usage) {
        $cu = $cw.current_usage
        $current = $cu.input_tokens + $cu.cache_creation_input_tokens + $cu.cache_read_input_tokens
        $usable = [math]::Max(1, $size - $autocompactBuffer)
        $pct = [math]::Round($current * 100 / $usable)
    } elseif ($cw.PSObject.Properties['used_percentage'] -and $null -ne $cw.used_percentage -and $size -gt 0) {
        # Fallback: convert raw used_percentage to autocompact-adjusted
        $rawTokens = [math]::Floor($size * [double]$cw.used_percentage / 100)
        $usable = [math]::Max(1, $size - $autocompactBuffer)
        $pct = [math]::Round($rawTokens * 100 / $usable)
    }
}
$pct = [math]::Max(0, [math]::Min(100, $pct))

# --- Context squares (brightness + half-fills, leading = gradient) ---
$sq_full  = [char]0x25A0
$sq_half  = [char]0x2B13
$sq_empty = [char]0x25A1
$sqW = 100.0 / 3
$gradRGB = Get-GradRGB $pct

$squares = ""
for ($i = 0; $i -lt 3; $i++) {
    $rangeStart = $i * $sqW
    $rangeEnd = ($i + 1) * $sqW

    if ($pct -ge $rangeEnd) {
        $squares += "$esc[38;2;${neuR};${neuG};${neuB}m${sq_full}"
    } elseif ($pct -gt $rangeStart) {
        $fill = [math]::Min(1.0, ($pct - $rangeStart) / $sqW)
        $bri = 0.25 + 0.75 * $fill
        $sr = [math]::Round($dimR + ($gradRGB[0] - $dimR) * $bri)
        $sg = [math]::Round($dimG + ($gradRGB[1] - $dimG) * $bri)
        $sb = [math]::Round($dimB + ($gradRGB[2] - $dimB) * $bri)
        $sqC = "$esc[38;2;${sr};${sg};${sb}m"
        if ($fill -ge 0.75) { $squares += "${sqC}${sq_full}" }
        elseif ($fill -ge 0.25) { $squares += "${sqC}${sq_half}" }
        else { $squares += "${sqC}${sq_empty}" }
    } else {
        $squares += "$esc[38;2;${dimR};${dimG};${dimB}m${sq_empty}"
    }
}
$squares += $R

$ctxColor = Get-GradColor $pct
if ($pct -ge 100) {
    $ctxText = "$squares ${ctxColor}COMPACT${R}"
} else {
    $ctxText = "$squares ${ctxColor}${pct}%${R}"
}

# --- Git info (cached 30s, per-project) ---
$gitCache = Join-Path $env:TEMP "claude-sl-git.json"
$branch = ""; $gitStaged = 0; $gitModified = 0; $repoUrl = ""; $hasGit = $false
$needGit = $true

if (Test-Path $gitCache) {
    $gitAge = ((Get-Date) - (Get-Item $gitCache).LastWriteTime).TotalSeconds
    if ($gitAge -lt 30) {
        try {
            $gc = Get-Content $gitCache -Raw | ConvertFrom-Json
            # Invalidate cache if project changed
            if ([string]$gc.projDir -eq $projDir) {
                $needGit = $false
                $branch = [string]$gc.branch
                $gitStaged = [int]$gc.staged
                $gitModified = [int]$gc.modified
                $repoUrl = [string]$gc.repoUrl
                $hasGit = [bool]$gc.hasGit
            }
        } catch {}
    }
}

if ($needGit) {
    try {
        $gitDir = git -C $projDir rev-parse --git-dir 2>$null
        if ($LASTEXITCODE -eq 0) {
            $hasGit = $true
            $branch = (git -C $projDir branch --show-current 2>$null)
            if ($branch) { $branch = $branch.Trim() }
            $stagedOut = @(git -C $projDir diff --cached --numstat 2>$null | Where-Object { $_ })
            $gitStaged = $stagedOut.Count
            $modOut = @(git -C $projDir diff --numstat 2>$null | Where-Object { $_ })
            $gitModified = $modOut.Count
            $remote = git -C $projDir remote get-url origin 2>$null
            if ($remote) {
                # Convert SSH → HTTPS for GitHub, GitLab, Bitbucket
                $repoUrl = ($remote.Trim() -replace '^git@([^:]+):', 'https://$1/' -replace '\.git$', '')
            }
        }
    } catch {}
    @{ projDir="$projDir"; branch="$branch"; staged=[int]$gitStaged; modified=[int]$gitModified; repoUrl="$repoUrl"; hasGit=$hasGit } |
        ConvertTo-Json | Set-Content $gitCache -Encoding UTF8
}

# Build git display: icon + branch as clickable link + dot indicators for dirty state
$gitIcon = [char]0x2387   # ⎇ (branch icon)
$gitDisplay = ""
if ($hasGit -and $branch) {
    if ($repoUrl) {
        # OSC 8 clickable link (broken in Claude Code >=2.1.3, see github.com/anthropics/claude-code/issues/21586)
        # Keeping the code for when it's fixed — link just renders as plain text for now
        $linkOpen = "${esc}]8;;${repoUrl}${bel}"
        $linkClose = "${esc}]8;;${bel}"
        $gitDisplay = "${linkOpen}${cSlate}${gitIcon} ${branch}${R}${linkClose}"
    } else {
        $gitDisplay = "${cSlate}${gitIcon} ${branch}${R}"
    }
    # Presence-based: sage ✔ = staged, salmon ~ = modified
    if ($gitStaged -gt 0) { $gitDisplay += " ${cSage}$([char]0x2714)${R}" }
    if ($gitModified -gt 0) { $gitDisplay += " ${cSalmon}~${R}" }
} elseif ($hasGit) {
    # Git repo but no branch (detached HEAD or empty repo)
    $gitDisplay = "${cDimmer}${gitIcon} ${cDim}detached${R}"
} else {
    # No git initialized
    $gitDisplay = "${cDimmer}${gitIcon} no git${R}"
}

# --- Session start detection (show limit % on first render only) ---
$sessionMarker = Join-Path $env:TEMP "claude-sl-session.json"
$showLimitPct = $false
$sid = ""
if ($data.PSObject.Properties['session_id'] -and $data.session_id) {
    $sid = $data.session_id
}
if ($sid) {
    $isFirstRender = $true
    if (Test-Path $sessionMarker) {
        try {
            $sm = Get-Content $sessionMarker -Raw | ConvertFrom-Json
            if ($sm.sid -eq $sid) { $isFirstRender = $false }
        } catch {}
    }
    if ($isFirstRender) {
        @{ sid=$sid } | ConvertTo-Json | Set-Content $sessionMarker -Encoding UTF8
        $showLimitPct = $true
    }
}

# --- Rate limits via OAuth API (cached 60s) ---
$cacheFile = Join-Path $env:TEMP "claude-sl-usage.json"
$fhPct = 0; $fhReset = ""; $fhResetRaw = ""; $sdPct = 0; $sdReset = ""; $sdResetRaw = ""
$exEnabled = $false; $exUsed = 0.0; $exLimit = 0.0; $exPct = 0
$limitsOk = $false
$needFetch = $true

if (Test-Path $cacheFile) {
    $age = ((Get-Date) - (Get-Item $cacheFile).LastWriteTime).TotalSeconds
    if ($age -lt 60) {
        $needFetch = $false
        try {
            $c = Get-Content $cacheFile -Raw | ConvertFrom-Json
            $fhPct = [int]$c.fhPct; $fhReset = [string]$c.fhReset
            $fhResetRaw = if ($c.PSObject.Properties['fhResetRaw']) { [string]$c.fhResetRaw } else { "" }
            $sdPct = [int]$c.sdPct; $sdReset = [string]$c.sdReset
            $sdResetRaw = if ($c.PSObject.Properties['sdResetRaw']) { [string]$c.sdResetRaw } else { "" }
            if ($c.PSObject.Properties['exEnabled']) { $exEnabled = [bool]$c.exEnabled }
            if ($c.PSObject.Properties['exUsed']) { $exUsed = [double]$c.exUsed }
            if ($c.PSObject.Properties['exLimit']) { $exLimit = [double]$c.exLimit }
            if ($c.PSObject.Properties['exPct']) { $exPct = [int]$c.exPct }
            $limitsOk = $true
        } catch {}
    }
}

if ($needFetch) {
    try {
        $credPath = Join-Path ([System.Environment]::GetFolderPath('UserProfile')) ".claude\.credentials.json"
        if (Test-Path $credPath) {
            $creds = Get-Content $credPath -Raw | ConvertFrom-Json
            $tok = $null
            if ($creds.PSObject.Properties['claudeAiOauth'] -and $creds.claudeAiOauth.accessToken) {
                $tok = $creds.claudeAiOauth.accessToken
            } elseif ($creds.PSObject.Properties['accessToken']) {
                $tok = $creds.accessToken
            }
            if ($tok) {
                $resp = Invoke-RestMethod -Uri "https://api.anthropic.com/api/oauth/usage" `
                    -Headers @{ "Authorization"="Bearer $tok"; "anthropic-beta"="oauth-2025-04-20" } `
                    -Method Get -TimeoutSec 5

                if ($resp.PSObject.Properties['five_hour'] -and $resp.five_hour) {
                    $fhPct = [math]::Round([double]$resp.five_hour.utilization)
                    if ($resp.five_hour.PSObject.Properties['resets_at'] -and $resp.five_hour.resets_at) {
                        $fhResetRaw = [string]$resp.five_hour.resets_at
                        $fhReset = ([DateTimeOffset]::Parse($fhResetRaw)).LocalDateTime.ToString("h:mmtt").ToLower()
                    }
                }
                if ($resp.PSObject.Properties['seven_day'] -and $resp.seven_day) {
                    $sdPct = [math]::Round([double]$resp.seven_day.utilization)
                    if ($resp.seven_day.PSObject.Properties['resets_at'] -and $resp.seven_day.resets_at) {
                        $sdResetRaw = [string]$resp.seven_day.resets_at
                        $sdDt = ([DateTimeOffset]::Parse($sdResetRaw)).LocalDateTime
                        $sdReset = $sdDt.ToString("ddd") + " " + $sdDt.ToString("h:mmtt").ToLower()
                    }
                }

                # Extra usage (may not exist if never configured)
                if ($resp.PSObject.Properties['extra_usage'] -and $resp.extra_usage) {
                    $ex = $resp.extra_usage
                    if ($ex.PSObject.Properties['is_enabled']) { $exEnabled = [bool]$ex.is_enabled }
                    if ($ex.PSObject.Properties['used_credits']) { $exUsed = [math]::Round([double]$ex.used_credits / 100, 2) }
                    if ($ex.PSObject.Properties['monthly_limit']) { $exLimit = [math]::Round([double]$ex.monthly_limit / 100, 2) }
                    if ($ex.PSObject.Properties['utilization']) { $exPct = [math]::Round([double]$ex.utilization) }
                }

                @{ fhPct=$fhPct; fhReset="$fhReset"; fhResetRaw="$fhResetRaw";
                   sdPct=$sdPct; sdReset="$sdReset"; sdResetRaw="$sdResetRaw";
                   exEnabled=$exEnabled; exUsed=$exUsed; exLimit=$exLimit; exPct=$exPct } |
                    ConvertTo-Json | Set-Content $cacheFile -Encoding UTF8
                $limitsOk = $true
            }
        }
    } catch {}
}

# --- Build limit bars (brightness-based, gradient only on last pip) ---
$fc = [char]0x25B0  # ▰
$ec = [char]0x25B1  # ▱
$barW = 5

function Build-LimitBar([int]$lpct, [int[]]$barRGB, [bool]$forceShowPct) {
    $lpct = [math]::Max(0, [math]::Min(100, $lpct))
    $gradColor = Get-LimitGradColor $lpct
    $barColor = "$esc[38;2;$($barRGB[0]);$($barRGB[1]);$($barRGB[2])m"
    $displayPct = $forceShowPct -or ($lpct -ge 80)
    $pipW = 100.0 / $barW

    if ($displayPct) {
        # Percentage text centered; flanking pips render naturally
        if ($lpct -ge 100) { $pStr = "100" }
        else { $pStr = "${lpct}%" }
        $txtColor = Get-LimitGradColor $lpct
        $tStart = [math]::Ceiling(($barW - $pStr.Length) / 2)
        $result = ""
        for ($i = 0; $i -lt $barW; $i++) {
            $tIdx = $i - $tStart
            if ($tIdx -ge 0 -and $tIdx -lt $pStr.Length) {
                $result += "${txtColor}$($pStr[$tIdx])"
                continue
            }
            $pipStart = $i * $pipW
            $pipEnd = ($i + 1) * $pipW
            $isLastPip = ($i -eq ($barW - 1))
            if ($lpct -ge $pipEnd) {
                if ($isLastPip) { $result += "${gradColor}${fc}" }
                else { $result += "${barColor}${fc}" }
            } elseif ($lpct -gt $pipStart) {
                $fill = [math]::Min(1.0, ($lpct - $pipStart) / $pipW)
                $bri = 0.25 + 0.75 * $fill
                if ($isLastPip) {
                    $gRGB = Get-LimitGradRGB $lpct
                    $lr = [math]::Round($dimR + ($gRGB[0] - $dimR) * $bri)
                    $lg = [math]::Round($dimG + ($gRGB[1] - $dimG) * $bri)
                    $lb = [math]::Round($dimB + ($gRGB[2] - $dimB) * $bri)
                } else {
                    $lr = [math]::Round($dimR + ($barRGB[0] - $dimR) * $bri)
                    $lg = [math]::Round($dimG + ($barRGB[1] - $dimG) * $bri)
                    $lb = [math]::Round($dimB + ($barRGB[2] - $dimB) * $bri)
                }
                $result += "$esc[38;2;${lr};${lg};${lb}m${fc}"
            } else {
                $result += "${cDim}${ec}"
            }
        }
        return "${result}${R}"
    } else {
        # 5 pips: identity color, last pip = limit gradient
        $result = ""
        for ($i = 0; $i -lt $barW; $i++) {
            $pipStart = $i * $pipW
            $pipEnd = ($i + 1) * $pipW
            $isLastPip = ($i -eq ($barW - 1))

            if ($lpct -ge $pipEnd) {
                if ($isLastPip) { $result += "${gradColor}${fc}" }
                else { $result += "${barColor}${fc}" }
            } elseif ($lpct -gt $pipStart) {
                # Leading pip — brightness interpolation
                $fill = [math]::Min(1.0, ($lpct - $pipStart) / $pipW)
                $bri = 0.25 + 0.75 * $fill
                if ($isLastPip) {
                    $gRGB = Get-LimitGradRGB $lpct
                    $lr = [math]::Round($dimR + ($gRGB[0] - $dimR) * $bri)
                    $lg = [math]::Round($dimG + ($gRGB[1] - $dimG) * $bri)
                    $lb = [math]::Round($dimB + ($gRGB[2] - $dimB) * $bri)
                } else {
                    $lr = [math]::Round($dimR + ($barRGB[0] - $dimR) * $bri)
                    $lg = [math]::Round($dimG + ($barRGB[1] - $dimG) * $bri)
                    $lb = [math]::Round($dimB + ($barRGB[2] - $dimB) * $bri)
                }
                $result += "$esc[38;2;${lr};${lg};${lb}m${fc}"
            } else {
                $result += "${cDim}${ec}"
            }
        }
        return "${result}${R}"
    }
}

$fhBar = Build-LimitBar $fhPct @(135, 180, 160) $showLimitPct   # sage RGB
$sdBar = Build-LimitBar $sdPct @(185, 140, 160) $showLimitPct   # mauve RGB

# Show 5h reset time if usage >= 75% OR within 15 minutes of reset
$fhShowReset = ($fhPct -ge 75)
if (-not $fhShowReset -and $fhResetRaw) {
    try {
        $fhMinLeft = (([DateTimeOffset]::Parse($fhResetRaw)).LocalDateTime - (Get-Date)).TotalMinutes
        if ($fhMinLeft -ge 0 -and $fhMinLeft -le 15) { $fhShowReset = $true }
    } catch {}
}
$fhResetTxt = if ($fhShowReset -and $fhReset) { " ${cSage}${fhReset}${R}" } else { "" }
# Show 7d reset time if usage >= 80% OR within 4 hours of reset
$sdShowReset = ($sdPct -ge 80)
if (-not $sdShowReset -and $sdResetRaw) {
    try {
        $sdHoursLeft = (([DateTimeOffset]::Parse($sdResetRaw)).LocalDateTime - (Get-Date)).TotalHours
        if ($sdHoursLeft -ge 0 -and $sdHoursLeft -le 4) { $sdShowReset = $true }
    } catch {}
}
$sdResetTxt = if ($sdShowReset -and $sdReset) { " ${cMauve}${sdReset}${R}" } else { "" }

# --- Claude Code update check (per-session cache, refreshed hourly) ---
$hasUpdate = $false; $updateLocal = ""; $updateRemote = ""
$needUpdateCheck = $true

# Per-session cache: each session gets its own file, no cross-session pollution
$updateCacheTag = if ($sid) { $sid.Substring(0, [Math]::Min(12, $sid.Length)) } else { "nosid" }
$updateCache = Join-Path $env:TEMP "claude-sl-update-$updateCacheTag.json"

if (Test-Path $updateCache) {
    $updateAge = ((Get-Date) - (Get-Item $updateCache).LastWriteTime).TotalSeconds
    if ($updateAge -lt 3600) {
        try {
            $uc = Get-Content $updateCache -Raw | ConvertFrom-Json
            $updateLocal = (([string]$uc.local) -split '\s+')[0]
            $updateRemote = (([string]$uc.remote) -split '\s+')[0]
            $hasUpdate = ($updateLocal -and $updateRemote -and $updateLocal -ne $updateRemote)
            $needUpdateCheck = $false
        } catch {}
    }
}

if ($needUpdateCheck) {
    try {
        # Get local version — first token of "2.1.37 (Claude Code)"
        $rawVer = ((claude --version 2>$null) -join ' ').Trim()
        if ($rawVer) { $updateLocal = ($rawVer -split '\s+')[0] }
        # Get latest from npm registry
        $npmResp = Invoke-RestMethod -Uri "https://registry.npmjs.org/@anthropic-ai/claude-code/latest" `
            -Method Get -TimeoutSec 3
        $updateRemote = "$($npmResp.version)".Trim()
        if ($updateLocal -and $updateRemote -and $updateLocal -ne $updateRemote) {
            $hasUpdate = $true
        }
        @{ hasUpdate=$hasUpdate; local="$updateLocal"; remote="$updateRemote" } |
            ConvertTo-Json | Set-Content $updateCache -Encoding UTF8
    } catch {
        @{ hasUpdate=$false; local=""; remote="" } |
            ConvertTo-Json | Set-Content $updateCache -Encoding UTF8
    }
}

# --- Session cost (from statusline JSON) ---
$costTxt = ""
if ($data.PSObject.Properties['cost'] -and $data.cost -and
    $data.cost.PSObject.Properties['total_cost_usd'] -and $data.cost.total_cost_usd -gt 0) {
    $costVal = [math]::Round([double]$data.cost.total_cost_usd, 2)
    $costTxt = "${cDim}`$$costVal${R}"
}

# --- Extra usage indicator (show at 95%+ on either limit) ---
$extraTxt = ""
if ($limitsOk -and ($fhPct -ge 95 -or $sdPct -ge 95)) {
    $bolt = [char]0x26A1  # ⚡
    if ($exEnabled -and ($fhPct -gt 100 -or $sdPct -gt 100)) {
        # Actively consuming extra usage — show spend/limit
        $extraTxt = "${cAmber}${bolt} `$$exUsed/`$$exLimit${R}"
    } elseif ($exEnabled) {
        # Approaching limit, extra usage will kick in
        $extraTxt = "${cDim}${bolt} Extra${R}"
    } else {
        # No extra usage — dim warning
        $extraTxt = "${cDimmer}${bolt} No extra${R}"
    }
}

# --- Output ---
# Line 1: dir  model  context  [cost]  [agent]  [vim]  [update]
$line1 = "${cSand}${dirDisplay}${R}  ${cPeach}${model}${R}  ${ctxText}"
if ($costTxt) { $line1 += "  ${costTxt}" }
if ($agentName) { $line1 += "  ${cLav}$([char]0x2699) ${agentName}${R}" }
if ($vimMode) { $line1 += "  ${cDim}${vimMode}${R}" }
if ($hasUpdate) {
    $line1 += "  ${cAmber}$([char]0x2191) ${updateLocal} $([char]0x2192) ${updateRemote}${R}"
}

# Line 2: git  limits  [extra]
$line2Parts = @()
$line2Parts += $gitDisplay
if ($limitsOk) {
    $line2Parts += "${fhBar}${fhResetTxt}"
    $line2Parts += "${sdBar}${sdResetTxt}"
}
if ($extraTxt) { $line2Parts += $extraTxt }
$line2 = $line2Parts -join "  "

[Console]::Out.WriteLine($line1)
[Console]::Out.Write($line2)
