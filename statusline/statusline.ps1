# Claude Code statusline — pastel, brightness squares, git+hosting, gradient limits
# Line 1: dir  model  ■■⬓□□ pct% Nk [◉◎○◌]  [$cost]  [agent]  [vim:MODE]  [↑ update]
# Line 2: ⎇ branch [✔ ~]  limit_bars [reset times]  [peak]  [⚡ extra usage]
#
# Official docs:
#   https://code.claude.com/docs/en/statusline
#
# Reference implementations:
#   https://github.com/NoobyGains/claude-pulse        — Python, rainbow animation, usage data, update notifications
#   https://github.com/sirmalloc/ccstatusline          — pre-built themes and configs
#   https://github.com/martinemde/starship-claude      — Starship prompt integration
#
# Rate limits: read from stdin rate_limits JSON (v2.1.80+, zero API calls).
#
# Installation (Windows/PowerShell):
#   1. Save this script, e.g. to ~/.claude/statusline.ps1
#   2. Add to ~/.claude/settings.json:
#        {
#          "statusLine": {
#            "command": "powershell -NoProfile -File \"%USERPROFILE%\\.claude\\statusline.ps1\""
#          }
#        }
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
$cTeal   = "$esc[38;2;115;195;195m"   # hosted repo indicator - soft cyan
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
    # Shorten: first\...\last when 3+ segments
    $relParts = $relPath -split '[/\\]'
    if ($relParts.Count -ge 3) {
        $relPath = "$($relParts[0])\...\$($relParts[-1])"
    }
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
$pct = 0; $currentTokens = [int64]0
if ($data.PSObject.Properties['context_window']) {
    $cw = $data.context_window
    $size = if ($cw.PSObject.Properties['context_window_size']) { [int]$cw.context_window_size } else { 0 }
    $autocompactBuffer = if ($autoCompactOn) { 33000 } else { 0 }

    if ($cw.PSObject.Properties['current_usage'] -and $null -ne $cw.current_usage) {
        $cu = $cw.current_usage
        $current = $cu.input_tokens + $cu.cache_creation_input_tokens + $cu.cache_read_input_tokens
        $currentTokens = [int64]$current
        $usable = [math]::Max(1, $size - $autocompactBuffer)
        $pct = [math]::Round($current * 100 / $usable)
    } elseif ($cw.PSObject.Properties['used_percentage'] -and $null -ne $cw.used_percentage -and $size -gt 0) {
        # Fallback: convert raw used_percentage to autocompact-adjusted
        $rawTokens = [math]::Floor($size * [double]$cw.used_percentage / 100)
        $currentTokens = [int64]$rawTokens
        $usable = [math]::Max(1, $size - $autocompactBuffer)
        $pct = [math]::Round($rawTokens * 100 / $usable)
    }
}
$pct = [math]::Max(0, [math]::Min(100, $pct))

# --- Context squares (5 squares, brightness + half-fills, leading = gradient) ---
$sq_full  = [char]0x25A0
$sq_half  = [char]0x2B13
$sq_empty = [char]0x25A1
$sqCount = 5
$sqW = 100.0 / $sqCount
$gradRGB = Get-GradRGB $pct

$squares = ""
for ($i = 0; $i -lt $sqCount; $i++) {
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

# --- Format token count ---
$tokenStr = ""
if ($currentTokens -ge 1000000) {
    $tokenStr = "{0:F1}M" -f ($currentTokens / 1000000.0)
} elseif ($currentTokens -ge 1000) {
    $tokenStr = "{0}k" -f [math]::Round($currentTokens / 1000)
} elseif ($currentTokens -gt 0) {
    $tokenStr = "$currentTokens"
}

# --- Focus ring (attention quality — appears at 150k+, unfocuses with degradation) ---
$focusRing = ""
if ($currentTokens -ge 700000) {
    # ◌ dashed ring — dim red, barely there
    $fr = Get-GradRGB 95
    $rr = [math]::Round($dimR + ($fr[0] - $dimR) * 0.6)
    $rg = [math]::Round($dimG + ($fr[1] - $dimG) * 0.6)
    $rb = [math]::Round($dimB + ($fr[2] - $dimB) * 0.6)
    $focusRing = " $esc[38;2;${rr};${rg};${rb}m$([char]0x25CC)${R}"
} elseif ($currentTokens -ge 500000) {
    # ○ empty ring — salmon
    $fr = Get-GradRGB 82
    $focusRing = " $esc[38;2;$($fr[0]);$($fr[1]);$($fr[2])m$([char]0x25CB)${R}"
} elseif ($currentTokens -ge 300000) {
    # ◎ hollowing — amber
    $fr = Get-GradRGB 65
    $focusRing = " $esc[38;2;$($fr[0]);$($fr[1]);$($fr[2])m$([char]0x25CE)${R}"
} elseif ($currentTokens -ge 150000) {
    # ◉ solid — dim, just appeared
    $focusRing = " ${cDim}$([char]0x25C9)${R}"
}

$ctxColor = Get-GradColor $pct
if ($pct -ge 100) {
    $ctxText = "$squares ${ctxColor}COMPACT${R}"
} elseif ($tokenStr) {
    $ctxText = "$squares ${ctxColor}${pct}%${R} ${cDim}${tokenStr}${R}${focusRing}"
} else {
    $ctxText = "$squares ${ctxColor}${pct}%${R}"
}

# --- Git info (cached 30s, per-project) ---
$gitCache = Join-Path $env:TEMP "claude-sl-git.json"
$branch = ""; $gitStaged = 0; $gitModified = 0; $repoUrl = ""; $hasGit = $false; $gitNested = $false
$needGit = $true

if (Test-Path $gitCache) {
    $gitAge = ((Get-Date) - (Get-Item $gitCache).LastWriteTime).TotalSeconds
    if ($gitAge -lt 30) {
        try {
            $gc = Get-Content $gitCache -Raw | ConvertFrom-Json
            # Invalidate cache if project or cwd changed
            $cachedCur = if ($gc.PSObject.Properties['curDir']) { [string]$gc.curDir } else { "" }
            if ([string]$gc.projDir -eq $projDir -and $cachedCur -eq $curDir) {
                $needGit = $false
                $branch = [string]$gc.branch
                $gitStaged = [int]$gc.staged
                $gitModified = [int]$gc.modified
                $repoUrl = [string]$gc.repoUrl
                $hasGit = [bool]$gc.hasGit
                if ($gc.PSObject.Properties['nested']) { $gitNested = [bool]$gc.nested }
            }
        } catch {}
    }
}

if ($needGit) {
    try {
        # Check projDir first, fall back to curDir (nested repo support)
        $gitCheckDir = $projDir
        $null = git -C $projDir rev-parse --git-dir 2>$null
        if ($LASTEXITCODE -ne 0 -and $curDir -ne $projDir) {
            $null = git -C $curDir rev-parse --git-dir 2>$null
            if ($LASTEXITCODE -eq 0) { $gitCheckDir = $curDir; $gitNested = $true }
        }
        $null = git -C $gitCheckDir rev-parse --git-dir 2>$null
        if ($LASTEXITCODE -eq 0) {
            $hasGit = $true
            $branch = (git -C $gitCheckDir branch --show-current 2>$null)
            if ($branch) { $branch = $branch.Trim() }
            $stagedOut = @(git -C $gitCheckDir diff --cached --numstat 2>$null | Where-Object { $_ })
            $gitStaged = $stagedOut.Count
            $modOut = @(git -C $gitCheckDir diff --numstat 2>$null | Where-Object { $_ })
            $gitModified = $modOut.Count
            $remote = git -C $gitCheckDir remote get-url origin 2>$null
            if ($remote) {
                # Convert SSH → HTTPS for GitHub, GitLab, Bitbucket
                $repoUrl = ($remote.Trim() -replace '^git@([^:]+):', 'https://$1/' -replace '\.git$', '')
            }
        }
    } catch {}
    @{ projDir="$projDir"; curDir="$curDir"; branch="$branch"; staged=[int]$gitStaged; modified=[int]$gitModified; repoUrl="$repoUrl"; hasGit=$hasGit; nested=$gitNested } |
        ConvertTo-Json | Set-Content $gitCache -Encoding UTF8
}

# Build git display: icon + branch as clickable link + dot indicators for dirty state
$gitIcon = [char]0x2387   # ⎇ (branch icon)
$gitDisplay = ""
$nestedPrefix = ""
if ($hasGit -and $gitNested) {
    $nestedPrefix = "${cDim}$([char]0x21B3) "   # ↳ nested repo indicator
}
if ($hasGit -and $branch) {
    if ($repoUrl) {
        # OSC 8 clickable link (broken in Claude Code >=2.1.3, see github.com/anthropics/claude-code/issues/21586)
        # Keeping the code for when it's fixed — link just renders as plain text for now
        $linkOpen = "${esc}]8;;${repoUrl}${bel}"
        $linkClose = "${esc}]8;;${bel}"
        $gitDisplay = "${nestedPrefix}${linkOpen}${cSlate}${gitIcon} ${branch}${R}${linkClose}"
        $gitDisplay += " ${cTeal}$([char]0x2B21)${R}"   # ⬡ hosted repo indicator
    } else {
        $gitDisplay = "${nestedPrefix}${cSlate}${gitIcon} ${branch}${R}"
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

# --- Rate limits from stdin JSON (live every refresh, v2.1.80+, zero API calls) ---
$fhPct = 0; $fhReset = ""; $fhResetEpoch = 0; $sdPct = 0; $sdReset = ""; $sdResetEpoch = 0
$exEnabled = $false; $exUsed = 0.0; $exLimit = 0.0; $exPct = 0
$limitsOk = $false
$limitsFailed = $false

if ($data.PSObject.Properties['rate_limits'] -and $data.rate_limits) {
    $rl = $data.rate_limits
    if ($rl.PSObject.Properties['five_hour'] -and $rl.five_hour) {
        $fhPct = [math]::Round([double]$rl.five_hour.used_percentage)
        if ($rl.five_hour.PSObject.Properties['resets_at'] -and $rl.five_hour.resets_at) {
            $fhResetEpoch = [long]$rl.five_hour.resets_at
            $fhReset = ([DateTimeOffset]::FromUnixTimeSeconds($fhResetEpoch)).LocalDateTime.ToString("h:mmtt").ToLower()
        }
        $limitsOk = $true
    }
    if ($rl.PSObject.Properties['seven_day'] -and $rl.seven_day) {
        $sdPct = [math]::Round([double]$rl.seven_day.used_percentage)
        if ($rl.seven_day.PSObject.Properties['resets_at'] -and $rl.seven_day.resets_at) {
            $sdResetEpoch = [long]$rl.seven_day.resets_at
            $sdDt = ([DateTimeOffset]::FromUnixTimeSeconds($sdResetEpoch)).LocalDateTime
            $sdReset = $sdDt.ToString("ddd") + " " + $sdDt.ToString("h:mmtt").ToLower()
        }
        $limitsOk = $true
    }
    # Extra usage (may be present in rate_limits)
    if ($rl.PSObject.Properties['extra_usage'] -and $rl.extra_usage) {
        $ex = $rl.extra_usage
        if ($ex.PSObject.Properties['is_enabled']) { $exEnabled = [bool]$ex.is_enabled }
        if ($ex.PSObject.Properties['used_credits']) { $exUsed = [math]::Round([double]$ex.used_credits / 100, 2) }
        if ($ex.PSObject.Properties['monthly_limit']) { $exLimit = [math]::Round([double]$ex.monthly_limit / 100, 2) }
        if ($ex.PSObject.Properties['utilization']) { $exPct = [math]::Round([double]$ex.utilization) }
    }
} else {
    $limitsFailed = $true
}

# --- Build limit bars (brightness-based, gradient only on last pip) ---
$fc = [char]0x25B0  # ▰
$ec = [char]0x25B1  # ▱
# Amber/red waypoints for overspend gradient
$amberR = 235; $amberG = 195; $amberB = 80
$warnRedR = 210; $warnRedG = 95; $warnRedB = 85

function Build-LimitBar([int]$lpct, [int]$barWidth, [int[]]$barRGB, [int]$budgetCount, [bool]$forceShowPct) {
    $lpct = [math]::Max(0, [math]::Min(100, $lpct))
    $gradColor = Get-LimitGradColor $lpct
    $barColor = "$esc[38;2;$($barRGB[0]);$($barRGB[1]);$($barRGB[2])m"
    $displayPct = $forceShowPct -or ($lpct -ge 80)
    $pipW = 100.0 / $barWidth

    # Compute overspend color for a pip past budget
    # t: 0.0 (just past budget) → 1.0 (last pip), identity → amber → red
    function Get-OverspendRGB([double]$t) {
        $t = [math]::Max(0.0, [math]::Min(1.0, $t))
        if ($t -le 0.5) {
            $s = $t / 0.5
            $r = [int]($barRGB[0] + ($amberR - $barRGB[0]) * $s)
            $g = [int]($barRGB[1] + ($amberG - $barRGB[1]) * $s)
            $b = [int]($barRGB[2] + ($amberB - $barRGB[2]) * $s)
        } else {
            $s = ($t - 0.5) / 0.5
            $r = [int]($amberR + ($warnRedR - $amberR) * $s)
            $g = [int]($amberG + ($warnRedG - $amberG) * $s)
            $b = [int]($amberB + ($warnRedB - $amberB) * $s)
        }
        return @($r, $g, $b)
    }

    # Determine pip base color: identity if within budget, overspend gradient if past
    function Get-PipBaseRGB([int]$pipIdx) {
        if ($pipIdx -lt $budgetCount) {
            return $barRGB
        }
        $pastCount = $barWidth - $budgetCount
        if ($pastCount -le 0) { return $barRGB }
        $t = ($pipIdx - $budgetCount) / [double]$pastCount
        return (Get-OverspendRGB $t)
    }

    if ($displayPct) {
        if ($lpct -ge 100) { $pStr = "100" }
        else { $pStr = "${lpct}%" }
        $txtColor = Get-LimitGradColor $lpct
        $tStart = [math]::Ceiling(($barWidth - $pStr.Length) / 2)
        $result = ""
        for ($i = 0; $i -lt $barWidth; $i++) {
            $tIdx = $i - $tStart
            if ($tIdx -ge 0 -and $tIdx -lt $pStr.Length) {
                $result += "${txtColor}$($pStr[$tIdx])"
                continue
            }
            $pipStart = $i * $pipW
            $pipEnd = ($i + 1) * $pipW
            if ($lpct -ge $pipEnd) {
                $pRGB = Get-PipBaseRGB $i
                $result += "$esc[38;2;$($pRGB[0]);$($pRGB[1]);$($pRGB[2])m${fc}"
            } elseif ($lpct -gt $pipStart) {
                $fill = [math]::Min(1.0, ($lpct - $pipStart) / $pipW)
                $bri = 0.25 + 0.75 * $fill
                $pRGB = Get-PipBaseRGB $i
                $lr = [math]::Round($dimR + ($pRGB[0] - $dimR) * $bri)
                $lg = [math]::Round($dimG + ($pRGB[1] - $dimG) * $bri)
                $lb = [math]::Round($dimB + ($pRGB[2] - $dimB) * $bri)
                $result += "$esc[38;2;${lr};${lg};${lb}m${fc}"
            } else {
                $result += "${cDim}${ec}"
            }
        }
        return "${result}${R}"
    } else {
        $result = ""
        for ($i = 0; $i -lt $barWidth; $i++) {
            $pipStart = $i * $pipW
            $pipEnd = ($i + 1) * $pipW
            if ($lpct -ge $pipEnd) {
                $pRGB = Get-PipBaseRGB $i
                $result += "$esc[38;2;$($pRGB[0]);$($pRGB[1]);$($pRGB[2])m${fc}"
            } elseif ($lpct -gt $pipStart) {
                $fill = [math]::Min(1.0, ($lpct - $pipStart) / $pipW)
                $bri = 0.25 + 0.75 * $fill
                $pRGB = Get-PipBaseRGB $i
                $lr = [math]::Round($dimR + ($pRGB[0] - $dimR) * $bri)
                $lg = [math]::Round($dimG + ($pRGB[1] - $dimG) * $bri)
                $lb = [math]::Round($dimB + ($pRGB[2] - $dimB) * $bri)
                $result += "$esc[38;2;${lr};${lg};${lb}m${fc}"
            } else {
                $result += "${cDim}${ec}"
            }
        }
        return "${result}${R}"
    }
}

# Compute budget: how many pips' worth of time has elapsed in each window
$now = [DateTimeOffset]::Now
$fhBudget = 0; $sdBudget = 0
if ($fhResetEpoch -gt 0) {
    $fhResetDt = [DateTimeOffset]::FromUnixTimeSeconds($fhResetEpoch)
    $fhElapsed = 5.0 - ($fhResetDt - $now).TotalHours
    $fhElapsed = [math]::Max(0, [math]::Min(5, $fhElapsed))
    $fhBudget = [math]::Floor($fhElapsed)
}
if ($sdResetEpoch -gt 0) {
    $sdResetDt = [DateTimeOffset]::FromUnixTimeSeconds($sdResetEpoch)
    $sdElapsed = 7.0 - ($sdResetDt - $now).TotalDays
    $sdElapsed = [math]::Max(0, [math]::Min(7, $sdElapsed))
    $sdBudget = [math]::Floor($sdElapsed)
}

$fhBar = Build-LimitBar $fhPct 5 @(135, 180, 160) $fhBudget $showLimitPct   # 5 pips, sage
$sdBar = Build-LimitBar $sdPct 7 @(185, 140, 160) $sdBudget $showLimitPct   # 7 pips, mauve

# Show 5h reset time if usage >= 75% OR within 30 minutes of reset
$fhShowReset = ($fhPct -ge 75)
if (-not $fhShowReset -and $fhResetEpoch -gt 0) {
    $fhMinLeft = ([DateTimeOffset]::FromUnixTimeSeconds($fhResetEpoch).LocalDateTime - (Get-Date)).TotalMinutes
    if ($fhMinLeft -ge 0 -and $fhMinLeft -le 30) { $fhShowReset = $true }
}
$fhResetTxt = if ($fhShowReset -and $fhReset) { " ${cSage}${fhReset}${R}" } else { "" }
# Show 7d reset time if usage >= 80% OR within 4 hours of reset
$sdShowReset = ($sdPct -ge 80)
if (-not $sdShowReset -and $sdResetEpoch -gt 0) {
    $sdHoursLeft = ([DateTimeOffset]::FromUnixTimeSeconds($sdResetEpoch).LocalDateTime - (Get-Date)).TotalHours
    if ($sdHoursLeft -ge 0 -and $sdHoursLeft -le 4) { $sdShowReset = $true }
}
$sdResetTxt = if ($sdShowReset -and $sdReset) { " ${cMauve}${sdReset}${R}" } else { "" }

# --- Claude Code update check (per-session cache, checked once per session) ---
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

# --- Extra usage detection ---
# Active extra usage: enabled AND hit 100% on either limit (currently consuming extra credits)
$activeExtra = $limitsOk -and $exEnabled -and ($fhPct -ge 100 -or $sdPct -ge 100)
$nearExtra = $limitsOk -and ($fhPct -ge 90 -or $sdPct -ge 90)

# --- Peak hours indicator (1pm-7pm GMT, limits burn faster during peak) ---
$peakTxt = ""
$utcHour = [DateTimeOffset]::UtcNow.Hour
if ($utcHour -ge 13 -and $utcHour -lt 19) {
    $peakTxt = "${cDim}peak${R}"
}

# --- Extra usage indicator ---
$extraTxt = ""
$bolt = [char]0x26A1  # ⚡
if ($activeExtra) {
    # Actively consuming extra usage — show spend/limit
    $extraTxt = "${cAmber}${bolt} `$$exUsed/`$$exLimit${R}"
} elseif ($nearExtra -and $exEnabled) {
    # Approaching limit, extra usage will kick in
    $extraTxt = "${cDim}${bolt} Extra${R}"
} elseif ($nearExtra) {
    # No extra usage — dim warning
    $extraTxt = "${cDimmer}${bolt} No extra${R}"
}

# --- Output ---
# Line 1: dir  model  context  [cost]  [agent]  [vim]  [extra msg]  [update]
$line1 = "${ctxText}  ${cSand}${dirDisplay}${R}  ${cPeach}${model}${R}"
# Show session cost when approaching or on extra usage
if ($costTxt -and ($nearExtra -or $activeExtra)) { $line1 += "  ${costTxt}" }
if ($agentName) { $line1 += "  ${cLav}$([char]0x2699) ${agentName}${R}" }
if ($vimMode) { $line1 += "  ${cDim}${vimMode}${R}" }
# Show "Extra Usage" on line 1 when actively consuming
if ($activeExtra) {
    $line1 += "  ${cAmber}Extra Usage${R}"
}
if ($hasUpdate) {
    $line1 += "  ${cAmber}$([char]0x2191) ${updateLocal} $([char]0x2192) ${updateRemote}${R}"
}

# Line 2: git  limits  [extra]
$line2Parts = @()
$line2Parts += $gitDisplay
if ($limitsOk) {
    $line2Parts += "${fhBar}${fhResetTxt}"
    $line2Parts += "${sdBar}${sdResetTxt}"
    if ($peakTxt) { $line2Parts += $peakTxt }
} elseif ($limitsFailed) {
    $line2Parts += "${cDimmer}limits --${R}"
}
if ($extraTxt) { $line2Parts += $extraTxt }
$line2 = $line2Parts -join "  "

[Console]::Out.WriteLine($line1)
[Console]::Out.Write($line2)
