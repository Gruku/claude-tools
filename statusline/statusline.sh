#!/usr/bin/env bash
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
# Installation (macOS/Linux):
#   1. Save this script to ~/.claude/statusline.sh
#   2. Make executable: chmod +x ~/.claude/statusline.sh
#   3. Add to ~/.claude/settings.json:
#        {
#          "statusLine": {
#            "command": "~/.claude/statusline.sh"
#          }
#        }
#   4. Rate limit bars require OAuth login — run `claude` and sign in.
#      Credentials are read from ~/.claude/.credentials.json automatically.
#   5. Requires: jq, curl, git

command -v jq >/dev/null 2>&1 || { echo "statusline: jq required"; exit 1; }

# --- Pastel palette ---
E=$'\e'
BEL=$'\a'
cSand="${E}[38;2;205;185;165m"
cPeach="${E}[38;2;195;160;155m"
cLav="${E}[38;2;165;150;200m"
cSage="${E}[38;2;135;180;160m"
cMauve="${E}[38;2;185;140;160m"
cSalmon="${E}[38;2;205;140;125m"
cSlate="${E}[38;2;140;160;185m"
cAmber="${E}[38;2;235;195;80m"
cDim="${E}[38;2;80;75;70m"
cDimmer="${E}[38;2;60;58;55m"
R="${E}[0m"

dimR=50 dimG=48 dimB=45
neuR=195 neuG=180 neuB=165

barW=5
TMPD="${TMPDIR:-/tmp}"

# --- OS-aware helpers ---
IS_MAC=false
[[ "$(uname)" == "Darwin" ]] && IS_MAC=true

file_age() {
    if $IS_MAC; then
        echo $(( $(date +%s) - $(stat -f "%m" "$1") ))
    else
        echo $(( $(date +%s) - $(stat -c "%Y" "$1") ))
    fi
}

# Parse ISO 8601 → epoch (try GNU date, fall back to python3)
iso_to_epoch() {
    date -d "$1" +%s 2>/dev/null ||
    python3 -c "from datetime import datetime; print(int(datetime.fromisoformat('$1').timestamp()))" 2>/dev/null ||
    echo 0
}

# Format epoch → "3:45pm"
fmt_time() {
    local raw
    if $IS_MAC; then
        raw=$(date -r "$1" "+%-I:%M%p" 2>/dev/null)
    else
        raw=$(date -d "@$1" "+%-I:%M%p" 2>/dev/null)
    fi
    echo "$raw" | tr '[:upper:]' '[:lower:]'
}

# Format epoch → "Wed"
fmt_day() {
    if $IS_MAC; then
        date -r "$1" "+%a" 2>/dev/null
    else
        date -d "@$1" "+%a" 2>/dev/null
    fi
}

# --- Gradient RGB (green → amber → red) ---
# Sets globals: GR GG GB
grad_rgb() {
    local p=$1
    (( p < 0 )) && p=0; (( p > 100 )) && p=100
    if (( p <= 60 )); then
        local t=$((p * 1000 / 60))
        GR=$((130 + 50 * t / 1000))
        GG=$((190 + 5 * t / 1000))
        GB=$((150 - 30 * t / 1000))
    elif (( p <= 80 )); then
        local t=$(((p - 60) * 1000 / 20))
        GR=$((180 + 30 * t / 1000))
        GG=$((195 - 20 * t / 1000))
        GB=$((120 - 20 * t / 1000))
    else
        local t=$(((p - 80) * 1000 / 20))
        GR=210
        GG=$((175 - 80 * t / 1000))
        GB=$((100 - 15 * t / 1000))
    fi
}

grad_color() {
    grad_rgb "$1"
    printf '%s' "${E}[38;2;${GR};${GG};${GB}m"
}

# --- Limit-bar gradient (80%=green, 100%=red, saturation ramps at high %) ---
# Sets globals: LR LG LB
limit_grad_rgb() {
    local p=$1
    (( p < 0 )) && p=0; (( p > 100 )) && p=100
    local r g b
    if (( p <= 80 )); then
        r=130 g=190 b=150
    elif (( p <= 90 )); then
        local t=$(((p - 80) * 1000 / 10))
        r=$((130 + 80 * t / 1000));  g=$((190 - 15 * t / 1000));  b=$((150 - 50 * t / 1000))
    else
        local t=$(((p - 90) * 1000 / 10))
        r=210; g=$((175 - 80 * t / 1000)); b=$((100 - 15 * t / 1000))
    fi
    # Dynamic muting: muted at <=80%, increasingly saturated toward 100%
    local mf=750  # ×1000 scale
    if (( p > 80 )); then
        mf=$((750 + 250 * (p - 80) / 20))
    fi
    LR=$((dimR + (r - dimR) * mf / 1000))
    LG=$((dimG + (g - dimG) * mf / 1000))
    LB=$((dimB + (b - dimB) * mf / 1000))
}

limit_grad_color() {
    limit_grad_rgb "$1"
    printf '%s' "${E}[38;2;${LR};${LG};${LB}m"
}

# --- Read JSON from stdin ---
INPUT=$(cat)

# Extract fields (single jq call)
J_MODEL="" J_CWD="" J_PROJ_DIR="" J_AGENT="" J_VIM="" J_SID="" J_COST="0"
J_CW_SIZE=0 J_CW_USED_PCT=0 J_CW_INPUT=-1 J_CW_CACHE_CREATE=0 J_CW_CACHE_READ=0
eval "$(echo "$INPUT" | jq -r '
    "J_MODEL=" + (.model.display_name // "" | @sh),
    "J_CWD=" + (.workspace.current_dir // .cwd // "" | @sh),
    "J_PROJ_DIR=" + (.workspace.project_dir // "" | @sh),
    "J_AGENT=" + ((.agent.name // "") | @sh),
    "J_VIM=" + ((.vim.mode // "") | @sh),
    "J_SID=" + (.session_id // "" | @sh),
    "J_COST=" + (.cost.total_cost_usd // 0 | tostring | @sh),
    "J_CW_SIZE=" + (.context_window.context_window_size // 0 | tostring | @sh),
    "J_CW_USED_PCT=" + (.context_window.used_percentage // 0 | tostring | @sh),
    "J_CW_INPUT=" + (.context_window.current_usage.input_tokens // -1 | tostring | @sh),
    "J_CW_CACHE_CREATE=" + (.context_window.current_usage.cache_creation_input_tokens // 0 | tostring | @sh),
    "J_CW_CACHE_READ=" + (.context_window.current_usage.cache_read_input_tokens // 0 | tostring | @sh)
' 2>/dev/null)" || true

# --- Directory (project_dir:relative when cwd differs) ---
projDir="${J_PROJ_DIR:-$J_CWD}"
curDir="$J_CWD"
projName=$(basename "$projDir")

if [[ "$curDir" != "$projDir" && "$curDir" == "$projDir"/* ]]; then
    relPath="${curDir#"$projDir"/}"
    dirDisplay="${projName}${cDim}:${cSand}${relPath}"
elif [[ "$curDir" != "$projDir" ]]; then
    dirDisplay="${projName}${cDim}:${cSand}$(basename "$curDir")"
else
    dirDisplay="$projName"
fi

# --- Read Claude Code config (autoCompact) ---
autoCompactOn=true
configPath="$HOME/.claude/settings.json"
if [[ -f "$configPath" ]]; then
    acVal=$(jq -r '.autoCompact // true' "$configPath" 2>/dev/null || echo "true")
    [[ "$acVal" == "false" ]] && autoCompactOn=false
fi

# --- Context percentage (adjusted for autocompact buffer) ---
if $autoCompactOn; then autocompactBuffer=33000; else autocompactBuffer=0; fi
pct=0
cwSize=${J_CW_SIZE%%.*}   # truncate decimal
cwInput=${J_CW_INPUT%%.*}

if (( cwInput >= 0 && cwSize > 0 )); then
    ccCreate=${J_CW_CACHE_CREATE%%.*}
    ccRead=${J_CW_CACHE_READ%%.*}
    current=$((cwInput + ccCreate + ccRead))
    usable=$((cwSize - autocompactBuffer))
    (( usable < 1 )) && usable=1
    pct=$(( (current * 100 + usable / 2) / usable ))  # rounded
elif (( cwSize > 0 )); then
    rawPctInt=${J_CW_USED_PCT%%.*}
    rawTokens=$((cwSize * rawPctInt / 100))
    usable=$((cwSize - autocompactBuffer))
    (( usable < 1 )) && usable=1
    pct=$(( (rawTokens * 100 + usable / 2) / usable ))  # rounded
fi
(( pct < 0 )) && pct=0; (( pct > 100 )) && pct=100

# --- Context squares (brightness + half-fills, leading = gradient) ---
# Use pct*3 scale: each square spans 100 units (total 300 = 100%)
grad_rgb "$pct"
gradR=$GR gradG=$GG gradB=$GB
pct3=$((pct * 3))

squares=""
for i in 0 1 2; do
    rangeStart=$((i * 100))
    rangeEnd=$(((i + 1) * 100))

    if (( pct3 >= rangeEnd )); then
        squares+="${E}[38;2;${neuR};${neuG};${neuB}m■"
    elif (( pct3 > rangeStart )); then
        fill=$(( (pct3 - rangeStart) * 10 ))   # 0–1000 scale
        bri=$((250 + 750 * fill / 1000))
        sr=$((dimR + (gradR - dimR) * bri / 1000))
        sg=$((dimG + (gradG - dimG) * bri / 1000))
        sb=$((dimB + (gradB - dimB) * bri / 1000))
        sqC="${E}[38;2;${sr};${sg};${sb}m"
        if (( fill >= 750 )); then   squares+="${sqC}■"
        elif (( fill >= 250 )); then squares+="${sqC}⬓"
        else                         squares+="${sqC}□"
        fi
    else
        squares+="${E}[38;2;${dimR};${dimG};${dimB}m□"
    fi
done
squares+="$R"

ctxColor=$(grad_color "$pct")
if (( pct >= 100 )); then
    ctxText="$squares ${ctxColor}COMPACT${R}"
else
    ctxText="$squares ${ctxColor}${pct}%${R}"
fi

# --- Git info (cached 30s, per-project) ---
gitCache="${TMPD}/claude-sl-git.json"
branch="" gitStaged=0 gitModified=0 repoUrl="" hasGit=false
needGit=true

if [[ -f "$gitCache" ]]; then
    age=$(file_age "$gitCache")
    if (( age < 30 )); then
        cachedProj=$(jq -r '.projDir // ""' "$gitCache" 2>/dev/null || echo "")
        if [[ "$cachedProj" == "$projDir" ]]; then
            needGit=false
            branch=$(jq -r '.branch // ""' "$gitCache")
            gitStaged=$(jq -r '.staged // 0' "$gitCache")
            gitModified=$(jq -r '.modified // 0' "$gitCache")
            repoUrl=$(jq -r '.repoUrl // ""' "$gitCache")
            hasGitStr=$(jq -r '.hasGit // false' "$gitCache")
            [[ "$hasGitStr" == "true" ]] && hasGit=true
        fi
    fi
fi

if $needGit; then
    if git -C "$projDir" rev-parse --git-dir >/dev/null 2>&1; then
        hasGit=true
        branch=$(git -C "$projDir" branch --show-current 2>/dev/null || echo "")
        gitStaged=$(git -C "$projDir" diff --cached --numstat 2>/dev/null | wc -l | tr -d ' ')
        gitModified=$(git -C "$projDir" diff --numstat 2>/dev/null | wc -l | tr -d ' ')
        remote=$(git -C "$projDir" remote get-url origin 2>/dev/null || echo "")
        if [[ -n "$remote" ]]; then
            repoUrl=$(echo "$remote" | sed -E 's|^git@([^:]+):|https://\1/|; s|\.git$||')
        fi
    fi
    jq -n --arg p "$projDir" --arg b "$branch" --argjson s "$gitStaged" \
        --argjson m "$gitModified" --arg r "$repoUrl" --argjson h "$hasGit" \
        '{projDir:$p,branch:$b,staged:$s,modified:$m,repoUrl:$r,hasGit:$h}' \
        > "$gitCache" 2>/dev/null
fi

# Build git display
gitDisplay=""
if $hasGit && [[ -n "$branch" ]]; then
    if [[ -n "$repoUrl" ]]; then
        gitDisplay="${E}]8;;${repoUrl}${BEL}${cSlate}⎇ ${branch}${R}${E}]8;;${BEL}"
    else
        gitDisplay="${cSlate}⎇ ${branch}${R}"
    fi
    (( gitStaged > 0 ))  && gitDisplay+=" ${cSage}✔${R}"
    (( gitModified > 0 )) && gitDisplay+=" ${cSalmon}~${R}"
elif $hasGit; then
    gitDisplay="${cDimmer}⎇ ${cDim}detached${R}"
else
    gitDisplay="${cDimmer}⎇ no git${R}"
fi

# --- Session start detection (show limit % on first render only) ---
sessionMarker="${TMPD}/claude-sl-session.json"
showLimitPct=false

if [[ -n "${J_SID:-}" ]]; then
    isFirstRender=true
    if [[ -f "$sessionMarker" ]]; then
        cachedSid=$(jq -r '.sid // ""' "$sessionMarker" 2>/dev/null || echo "")
        [[ "$cachedSid" == "$J_SID" ]] && isFirstRender=false
    fi
    if $isFirstRender; then
        jq -n --arg s "$J_SID" '{sid:$s}' > "$sessionMarker" 2>/dev/null
        showLimitPct=true
    fi
fi

# --- Rate limits via OAuth API (cached 60s) ---
cacheFile="${TMPD}/claude-sl-usage.json"
fhPct=0 fhReset="" fhResetRaw="" sdPct=0 sdReset="" sdResetRaw=""
exEnabled=false exUsed="0" exLimit="0" exPct=0
limitsOk=false
needFetch=true

if [[ -f "$cacheFile" ]]; then
    age=$(file_age "$cacheFile")
    if (( age < 60 )); then
        needFetch=false
        fhPct=$(jq -r '.fhPct // 0' "$cacheFile" 2>/dev/null || echo 0)
        fhReset=$(jq -r '.fhReset // ""' "$cacheFile" 2>/dev/null || echo "")
        fhResetRaw=$(jq -r '.fhResetRaw // ""' "$cacheFile" 2>/dev/null || echo "")
        sdPct=$(jq -r '.sdPct // 0' "$cacheFile" 2>/dev/null || echo 0)
        sdReset=$(jq -r '.sdReset // ""' "$cacheFile" 2>/dev/null || echo "")
        sdResetRaw=$(jq -r '.sdResetRaw // ""' "$cacheFile" 2>/dev/null || echo "")
        exEnabledStr=$(jq -r '.exEnabled // false' "$cacheFile" 2>/dev/null || echo "false")
        [[ "$exEnabledStr" == "true" ]] && exEnabled=true
        exUsed=$(jq -r '.exUsed // 0' "$cacheFile" 2>/dev/null || echo "0")
        exLimit=$(jq -r '.exLimit // 0' "$cacheFile" 2>/dev/null || echo "0")
        exPct=$(jq -r '.exPct // 0' "$cacheFile" 2>/dev/null || echo 0)
        limitsOk=true
    fi
fi

if $needFetch; then
    credPath="$HOME/.claude/.credentials.json"
    if [[ -f "$credPath" ]]; then
        tok=$(jq -r '.claudeAiOauth.accessToken // .accessToken // empty' "$credPath" 2>/dev/null || echo "")
        if [[ -n "$tok" ]]; then
            resp=$(curl -sf --max-time 5 \
                -H "Authorization: Bearer $tok" \
                -H "anthropic-beta: oauth-2025-04-20" \
                "https://api.anthropic.com/api/oauth/usage" 2>/dev/null || echo "")
            if [[ -n "$resp" ]]; then
                fhPct=$(echo "$resp" | jq -r '.five_hour.utilization // 0' | awk '{printf "%d", $1+0.5}')
                fhResetRaw=$(echo "$resp" | jq -r '.five_hour.resets_at // ""' 2>/dev/null || echo "")
                if [[ -n "$fhResetRaw" && "$fhResetRaw" != "null" ]]; then
                    epoch=$(iso_to_epoch "$fhResetRaw")
                    (( epoch > 0 )) && fhReset=$(fmt_time "$epoch")
                fi
                sdPct=$(echo "$resp" | jq -r '.seven_day.utilization // 0' | awk '{printf "%d", $1+0.5}')
                sdResetRaw=$(echo "$resp" | jq -r '.seven_day.resets_at // ""' 2>/dev/null || echo "")
                if [[ -n "$sdResetRaw" && "$sdResetRaw" != "null" ]]; then
                    epoch=$(iso_to_epoch "$sdResetRaw")
                    if (( epoch > 0 )); then
                        sdReset="$(fmt_day "$epoch") $(fmt_time "$epoch")"
                    fi
                fi

                # Extra usage (may not exist if never configured)
                exEnabledStr=$(echo "$resp" | jq -r '.extra_usage.is_enabled // false' 2>/dev/null || echo "false")
                [[ "$exEnabledStr" == "true" ]] && exEnabled=true
                exUsedCents=$(echo "$resp" | jq -r '.extra_usage.used_credits // 0' 2>/dev/null || echo "0")
                exLimitCents=$(echo "$resp" | jq -r '.extra_usage.monthly_limit // 0' 2>/dev/null || echo "0")
                exUsed=$(awk "BEGIN{printf \"%.2f\", $exUsedCents/100}")
                exLimit=$(awk "BEGIN{printf \"%.2f\", $exLimitCents/100}")
                exPct=$(echo "$resp" | jq -r '.extra_usage.utilization // 0' 2>/dev/null | awk '{printf "%d", $1+0.5}')

                jq -n --argjson fh "$fhPct" --arg fr "$fhReset" --arg frr "$fhResetRaw" \
                    --argjson sd "$sdPct" --arg sr "$sdReset" --arg srr "$sdResetRaw" \
                    --argjson exE "$exEnabled" --arg exU "$exUsed" --arg exL "$exLimit" --argjson exP "$exPct" \
                    '{fhPct:$fh,fhReset:$fr,fhResetRaw:$frr,sdPct:$sd,sdReset:$sr,sdResetRaw:$srr,exEnabled:$exE,exUsed:$exU,exLimit:$exL,exPct:$exP}' \
                    > "$cacheFile" 2>/dev/null
                limitsOk=true
            fi
        fi
    fi
fi

# --- Build limit bars (brightness-based, gradient only on last pip) ---
# Renders pip at each position: text overlay when showing %, natural pips otherwise
# Uses integer math scaled ×100 (pipW=2000 for 5 pips over 10000)
build_limit_bar() {
    local lpct=$1 barR=$2 barG=$3 barB=$4 forceShow=$5
    (( lpct < 0 )) && lpct=0; (( lpct > 100 )) && lpct=100
    local gradC=$(limit_grad_color "$lpct")
    local barC="${E}[38;2;${barR};${barG};${barB}m"
    local displayPct=false
    $forceShow && displayPct=true
    (( lpct >= 80 )) && displayPct=true
    local pipW=$((10000 / barW))
    local result=""

    if $displayPct; then
        # Percentage text centered; flanking pips render naturally
        local pStr
        if (( lpct >= 100 )); then pStr="100"
        else pStr="${lpct}%"; fi
        local txtC=$(limit_grad_color "$lpct")
        local tLen=${#pStr}
        local tStart=$(( (barW - tLen + 1) / 2 ))   # Ceiling division

        for (( i=0; i<barW; i++ )); do
            local tIdx=$((i - tStart))
            if (( tIdx >= 0 && tIdx < tLen )); then
                result+="${txtC}${pStr:$tIdx:1}"
                continue
            fi
            local pipStart=$((i * pipW))
            local pipEnd=$(((i + 1) * pipW))
            local lpct100=$((lpct * 100))
            if (( lpct100 >= pipEnd )); then
                if (( i == barW - 1 )); then result+="${gradC}▰"
                else result+="${barC}▰"; fi
            elif (( lpct100 > pipStart )); then
                local fill=$(( (lpct100 - pipStart) * 1000 / pipW ))
                local bri=$((250 + 750 * fill / 1000))
                local lr lg lb
                if (( i == barW - 1 )); then
                    limit_grad_rgb "$lpct"
                    lr=$((dimR + (LR - dimR) * bri / 1000))
                    lg=$((dimG + (LG - dimG) * bri / 1000))
                    lb=$((dimB + (LB - dimB) * bri / 1000))
                else
                    lr=$((dimR + (barR - dimR) * bri / 1000))
                    lg=$((dimG + (barG - dimG) * bri / 1000))
                    lb=$((dimB + (barB - dimB) * bri / 1000))
                fi
                result+="${E}[38;2;${lr};${lg};${lb}m▰"
            else
                result+="${cDim}▱"
            fi
        done
    else
        # 5 pips: identity color, last pip = limit gradient
        for (( i=0; i<barW; i++ )); do
            local pipStart=$((i * pipW))
            local pipEnd=$(((i + 1) * pipW))
            local lpct100=$((lpct * 100))
            if (( lpct100 >= pipEnd )); then
                if (( i == barW - 1 )); then result+="${gradC}▰"
                else result+="${barC}▰"; fi
            elif (( lpct100 > pipStart )); then
                local fill=$(( (lpct100 - pipStart) * 1000 / pipW ))
                local bri=$((250 + 750 * fill / 1000))
                local lr lg lb
                if (( i == barW - 1 )); then
                    limit_grad_rgb "$lpct"
                    lr=$((dimR + (LR - dimR) * bri / 1000))
                    lg=$((dimG + (LG - dimG) * bri / 1000))
                    lb=$((dimB + (LB - dimB) * bri / 1000))
                else
                    lr=$((dimR + (barR - dimR) * bri / 1000))
                    lg=$((dimG + (barG - dimG) * bri / 1000))
                    lb=$((dimB + (barB - dimB) * bri / 1000))
                fi
                result+="${E}[38;2;${lr};${lg};${lb}m▰"
            else
                result+="${cDim}▱"
            fi
        done
    fi
    printf '%s' "${result}${R}"
}

fhBar=$(build_limit_bar "$fhPct" 135 180 160 "$showLimitPct")
sdBar=$(build_limit_bar "$sdPct" 185 140 160 "$showLimitPct")

# 5h reset: show if >=75% or within 15 min of reset
fhShowReset=false fhResetTxt=""
(( fhPct >= 75 )) && fhShowReset=true
if ! $fhShowReset && [[ -n "$fhResetRaw" && "$fhResetRaw" != "null" ]]; then
    epoch=$(iso_to_epoch "$fhResetRaw")
    now=$(date +%s)
    if (( epoch > 0 )); then
        minLeft=$(( (epoch - now) / 60 ))
        (( minLeft >= 0 && minLeft <= 15 )) && fhShowReset=true
    fi
fi
$fhShowReset && [[ -n "$fhReset" ]] && fhResetTxt=" ${cSage}${fhReset}${R}"

# 7d reset: show if >=80% or within 4 hours of reset
sdShowReset=false sdResetTxt=""
(( sdPct >= 80 )) && sdShowReset=true
if ! $sdShowReset && [[ -n "$sdResetRaw" && "$sdResetRaw" != "null" ]]; then
    epoch=$(iso_to_epoch "$sdResetRaw")
    now=$(date +%s)
    if (( epoch > 0 )); then
        hoursLeft=$(( (epoch - now) / 3600 ))
        (( hoursLeft >= 0 && hoursLeft <= 4 )) && sdShowReset=true
    fi
fi
$sdShowReset && [[ -n "$sdReset" ]] && sdResetTxt=" ${cMauve}${sdReset}${R}"

# --- Claude Code update check (per-session cache, refreshed hourly) ---
updateCacheTag="${J_SID:0:12}"
updateCacheTag="${updateCacheTag:-nosid}"
updateCache="${TMPD}/claude-sl-update-${updateCacheTag}.json"
hasUpdate=false updateLocal="" updateRemote=""
needUpdateCheck=true

if [[ -f "$updateCache" ]]; then
    age=$(file_age "$updateCache")
    if (( age < 3600 )); then
        updateLocal=$(jq -r '.local // ""' "$updateCache" 2>/dev/null | awk '{print $1}')
        updateRemote=$(jq -r '.remote // ""' "$updateCache" 2>/dev/null | awk '{print $1}')
        [[ -n "$updateLocal" && -n "$updateRemote" && "$updateLocal" != "$updateRemote" ]] && hasUpdate=true
        needUpdateCheck=false
    fi
fi

if $needUpdateCheck; then
    rawVer=$(claude --version 2>/dev/null || echo "")
    [[ -n "$rawVer" ]] && updateLocal=$(echo "$rawVer" | awk '{print $1}')
    updateRemote=$(curl -sf --max-time 3 "https://registry.npmjs.org/@anthropic-ai/claude-code/latest" 2>/dev/null \
        | jq -r '.version // ""' || echo "")
    if [[ -n "$updateLocal" && -n "$updateRemote" && "$updateLocal" != "$updateRemote" ]]; then
        hasUpdate=true
    fi
    jq -n --argjson h "$hasUpdate" --arg l "$updateLocal" --arg r "$updateRemote" \
        '{hasUpdate:$h,local:$l,remote:$r}' > "$updateCache" 2>/dev/null
fi

# --- Session cost (from statusline JSON) ---
costTxt=""
costCheck=$(awk "BEGIN{print ($J_COST > 0) ? 1 : 0}")
if [[ "$costCheck" == "1" ]]; then
    costVal=$(awk "BEGIN{printf \"%.2f\", $J_COST}")
    costTxt="${cDim}\$${costVal}${R}"
fi

# --- Extra usage detection ---
# Active extra usage: enabled AND hit 100% on either limit (currently consuming extra credits)
activeExtra=false
$limitsOk && $exEnabled && (( fhPct >= 100 || sdPct >= 100 )) && activeExtra=true
nearExtra=false
$limitsOk && (( fhPct >= 90 || sdPct >= 90 )) && nearExtra=true

# --- Extra usage indicator ---
extraTxt=""
if $activeExtra; then
    # Actively consuming extra usage — show spend/limit
    extraTxt="${cAmber}⚡ \$${exUsed}/\$${exLimit}${R}"
elif $nearExtra && $exEnabled; then
    # Approaching limit, extra usage will kick in
    extraTxt="${cDim}⚡ Extra${R}"
elif $nearExtra; then
    # No extra usage — dim warning
    extraTxt="${cDimmer}⚡ No extra${R}"
fi

# --- Output ---
# Line 1: dir  model  context  [cost]  [agent]  [vim]  [extra msg]  [update]
line1="${cSand}${dirDisplay}${R}  ${cPeach}${J_MODEL}${R}  ${ctxText}"
# Show session cost when approaching or on extra usage
if [[ -n "$costTxt" ]] && ($nearExtra || $activeExtra); then line1+="  ${costTxt}"; fi
[[ -n "${J_AGENT:-}" ]] && line1+="  ${cLav}⚙ ${J_AGENT}${R}"
[[ -n "${J_VIM:-}" ]]   && line1+="  ${cDim}${J_VIM}${R}"
# Show "Extra Usage" on line 1 when actively consuming
$activeExtra && line1+="  ${cAmber}Extra Usage${R}"
if $hasUpdate; then
    line1+="  ${cAmber}↑ ${updateLocal} → ${updateRemote}${R}"
fi

# Line 2: git  limits  [extra]
line2="$gitDisplay"
if $limitsOk; then
    line2+="  ${fhBar}${fhResetTxt}  ${sdBar}${sdResetTxt}"
fi
[[ -n "$extraTxt" ]] && line2+="  ${extraTxt}"

printf '%s\n' "$line1"
printf '%s' "$line2"
