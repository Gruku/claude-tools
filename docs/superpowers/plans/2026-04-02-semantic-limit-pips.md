# Semantic Limit Pips Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace hardcoded 5-pip limit bars with semantic pip counts (5 for 5h, 7 for 7d) and add budget-aware overspend coloring.

**Architecture:** Modify `Build-LimitBar`/`build_limit_bar` to accept per-bar width and budget count. Add an overspend color interpolation function. Compute budget from `resets_at` timestamps at the call site. Both `.ps1` and `.sh` files get identical logic changes.

**Tech Stack:** PowerShell, Bash (integer math scaled ×1000 in bash)

**Spec:** `docs/superpowers/specs/2026-04-02-semantic-limit-pips-design.md`

---

### Task 1: Add overspend color helper and update Build-LimitBar in statusline.ps1

**Files:**
- Modify: `statusline/statusline.ps1:379-464` (limit bar section)

- [ ] **Step 1: Remove global `$barW` and add overspend color helper**

Replace line 382:
```powershell
$barW = 5
```

With:
```powershell
# Amber/red waypoints for overspend gradient
$amberR = 235; $amberG = 195; $amberB = 80
$warnRedR = 210; $warnRedG = 95; $warnRedB = 85
```

- [ ] **Step 2: Rewrite `Build-LimitBar` function signature and pip coloring logic**

Replace the entire `Build-LimitBar` function (lines 384–461) with:

```powershell
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
```

- [ ] **Step 3: Compute budget counts and update call sites**

Replace lines 463-464:
```powershell
$fhBar = Build-LimitBar $fhPct @(135, 180, 160) $showLimitPct   # sage RGB
$sdBar = Build-LimitBar $sdPct @(185, 140, 160) $showLimitPct   # mauve RGB
```

With:
```powershell
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
```

- [ ] **Step 4: Update 5h reset time threshold from 15 to 30 minutes**

Replace lines 466-471:
```powershell
# Show 5h reset time if usage >= 75% OR within 15 minutes of reset
$fhShowReset = ($fhPct -ge 75)
if (-not $fhShowReset -and $fhResetEpoch -gt 0) {
    $fhMinLeft = ([DateTimeOffset]::FromUnixTimeSeconds($fhResetEpoch).LocalDateTime - (Get-Date)).TotalMinutes
    if ($fhMinLeft -ge 0 -and $fhMinLeft -le 15) { $fhShowReset = $true }
}
```

With:
```powershell
# Show 5h reset time if usage >= 75% OR within 30 minutes of reset
$fhShowReset = ($fhPct -ge 75)
if (-not $fhShowReset -and $fhResetEpoch -gt 0) {
    $fhMinLeft = ([DateTimeOffset]::FromUnixTimeSeconds($fhResetEpoch).LocalDateTime - (Get-Date)).TotalMinutes
    if ($fhMinLeft -ge 0 -and $fhMinLeft -le 30) { $fhShowReset = $true }
}
```

- [ ] **Step 5: Commit PowerShell changes**

```bash
git add statusline/statusline.ps1
git commit -m "feat(statusline): semantic limit pips with budget-aware coloring (ps1)"
```

---

### Task 2: Mirror changes to statusline.sh

**Files:**
- Modify: `statusline/statusline.sh:48,418-515`

- [ ] **Step 1: Remove global `barW` and add overspend color constants**

Replace line 48:
```bash
barW=5
```

With:
```bash
# Amber/red waypoints for overspend gradient
amberR=235 amberG=195 amberB=80
warnRedR=210 warnRedG=95 warnRedB=85
```

- [ ] **Step 2: Rewrite `build_limit_bar` function**

Replace the entire `build_limit_bar` function (lines 421–501) with:

```bash
# Compute overspend color for pip past budget
# Args: $1=t_x1000 (0-1000), $2=barR, $3=barG, $4=barB
# Sets: OSR OSG OSB
overspend_rgb() {
    local t=$1 bR=$2 bG=$3 bB=$4
    (( t < 0 )) && t=0; (( t > 1000 )) && t=1000
    if (( t <= 500 )); then
        local s=$((t * 1000 / 500))
        OSR=$((bR + (amberR - bR) * s / 1000))
        OSG=$((bG + (amberG - bG) * s / 1000))
        OSB=$((bB + (amberB - bB) * s / 1000))
    else
        local s=$(((t - 500) * 1000 / 500))
        OSR=$((amberR + (warnRedR - amberR) * s / 1000))
        OSG=$((amberG + (warnRedG - amberG) * s / 1000))
        OSB=$((amberB + (warnRedB - amberB) * s / 1000))
    fi
}

# Args: $1=lpct, $2=barWidth, $3=barR, $4=barG, $5=barB, $6=budgetCount, $7=forceShowPct
build_limit_bar() {
    local lpct=$1 bW=$2 barR=$3 barG=$4 barB=$5 budgetCount=$6 forceShow=$7
    (( lpct < 0 )) && lpct=0; (( lpct > 100 )) && lpct=100
    local barC="${E}[38;2;${barR};${barG};${barB}m"
    local displayPct=false
    $forceShow && displayPct=true
    (( lpct >= 80 )) && displayPct=true
    local pipW=$((10000 / bW))
    local result=""

    # Get pip base color: identity if within budget, overspend if past
    # Sets: PBR PBG PBB
    pip_base_rgb() {
        local idx=$1
        if (( idx < budgetCount )); then
            PBR=$barR; PBG=$barG; PBB=$barB
        else
            local pastCount=$((bW - budgetCount))
            if (( pastCount <= 0 )); then
                PBR=$barR; PBG=$barG; PBB=$barB
                return
            fi
            local t=$(( (idx - budgetCount) * 1000 / pastCount ))
            overspend_rgb "$t" "$barR" "$barG" "$barB"
            PBR=$OSR; PBG=$OSG; PBB=$OSB
        fi
    }

    if $displayPct; then
        local pStr
        if (( lpct >= 100 )); then pStr="100"
        else pStr="${lpct}%"; fi
        local txtC=$(limit_grad_color "$lpct")
        local tLen=${#pStr}
        local tStart=$(( (bW - tLen + 1) / 2 ))

        for (( i=0; i<bW; i++ )); do
            local tIdx=$((i - tStart))
            if (( tIdx >= 0 && tIdx < tLen )); then
                result+="${txtC}${pStr:$tIdx:1}"
                continue
            fi
            local pipStart=$((i * pipW))
            local pipEnd=$(((i + 1) * pipW))
            local lpct100=$((lpct * 100))
            if (( lpct100 >= pipEnd )); then
                pip_base_rgb "$i"
                result+="${E}[38;2;${PBR};${PBG};${PBB}m▰"
            elif (( lpct100 > pipStart )); then
                local fill=$(( (lpct100 - pipStart) * 1000 / pipW ))
                local bri=$((250 + 750 * fill / 1000))
                pip_base_rgb "$i"
                local lr=$((dimR + (PBR - dimR) * bri / 1000))
                local lg=$((dimG + (PBG - dimG) * bri / 1000))
                local lb=$((dimB + (PBB - dimB) * bri / 1000))
                result+="${E}[38;2;${lr};${lg};${lb}m▰"
            else
                result+="${cDim}▱"
            fi
        done
    else
        for (( i=0; i<bW; i++ )); do
            local pipStart=$((i * pipW))
            local pipEnd=$(((i + 1) * pipW))
            local lpct100=$((lpct * 100))
            if (( lpct100 >= pipEnd )); then
                pip_base_rgb "$i"
                result+="${E}[38;2;${PBR};${PBG};${PBB}m▰"
            elif (( lpct100 > pipStart )); then
                local fill=$(( (lpct100 - pipStart) * 1000 / pipW ))
                local bri=$((250 + 750 * fill / 1000))
                pip_base_rgb "$i"
                local lr=$((dimR + (PBR - dimR) * bri / 1000))
                local lg=$((dimG + (PBG - dimG) * bri / 1000))
                local lb=$((dimB + (PBB - dimB) * bri / 1000))
                result+="${E}[38;2;${lr};${lg};${lb}m▰"
            else
                result+="${cDim}▱"
            fi
        done
    fi
    printf '%s' "${result}${R}"
}
```

- [ ] **Step 3: Compute budget counts and update call sites**

Replace lines 504-505:
```bash
fhBar=$(build_limit_bar "$fhPct" 135 180 160 "$showLimitPct")
sdBar=$(build_limit_bar "$sdPct" 185 140 160 "$showLimitPct")
```

With:
```bash
# Compute budget: how many pips' worth of time has elapsed in each window
nowEpoch=$(date +%s)
fhBudget=0; sdBudget=0
if (( fhResetEpoch > 0 )); then
    fhSecsLeft=$((fhResetEpoch - nowEpoch))
    (( fhSecsLeft < 0 )) && fhSecsLeft=0
    fhElapsedSecs=$((5 * 3600 - fhSecsLeft))
    (( fhElapsedSecs < 0 )) && fhElapsedSecs=0
    fhBudget=$((fhElapsedSecs / 3600))
    (( fhBudget > 5 )) && fhBudget=5
fi
if (( sdResetEpoch > 0 )); then
    sdSecsLeft=$((sdResetEpoch - nowEpoch))
    (( sdSecsLeft < 0 )) && sdSecsLeft=0
    sdElapsedSecs=$((7 * 86400 - sdSecsLeft))
    (( sdElapsedSecs < 0 )) && sdElapsedSecs=0
    sdBudget=$((sdElapsedSecs / 86400))
    (( sdBudget > 7 )) && sdBudget=7
fi

fhBar=$(build_limit_bar "$fhPct" 5 135 180 160 "$fhBudget" "$showLimitPct")
sdBar=$(build_limit_bar "$sdPct" 7 185 140 160 "$sdBudget" "$showLimitPct")
```

- [ ] **Step 4: Update 5h reset time threshold from 15 to 30 minutes**

Replace lines 507-514:
```bash
# 5h reset: show if >=75% or within 15 min of reset
fhShowReset=false fhResetTxt=""
(( fhPct >= 75 )) && fhShowReset=true
if ! $fhShowReset && (( fhResetEpoch > 0 )); then
    now=$(date +%s)
    minLeft=$(( (fhResetEpoch - now) / 60 ))
    (( minLeft >= 0 && minLeft <= 15 )) && fhShowReset=true
fi
```

With:
```bash
# 5h reset: show if >=75% or within 30 min of reset
fhShowReset=false fhResetTxt=""
(( fhPct >= 75 )) && fhShowReset=true
if ! $fhShowReset && (( fhResetEpoch > 0 )); then
    now=$(date +%s)
    minLeft=$(( (fhResetEpoch - now) / 60 ))
    (( minLeft >= 0 && minLeft <= 30 )) && fhShowReset=true
fi
```

- [ ] **Step 5: Commit bash changes**

```bash
git add statusline/statusline.sh
git commit -m "feat(statusline): semantic limit pips with budget-aware coloring (sh)"
```

---

### Task 3: Sync installed copy and verify

**Files:**
- Modify: `~/.claude/statusline.ps1` (copy from repo)

- [ ] **Step 1: Copy updated ps1 to installed location**

```bash
cp statusline/statusline.ps1 ~/.claude/statusline.ps1
```

- [ ] **Step 2: Verify the installed file matches the repo file**

```bash
diff statusline/statusline.ps1 ~/.claude/statusline.ps1
```

Expected: no output (files identical).

- [ ] **Step 3: Commit sync**

```bash
git add -A
git commit -m "chore(statusline): sync installed copy"
```
