#!/usr/bin/env bash
# Claude Code statusline — pastel, brightness squares, git+hosting, gradient limits
# Line 1: ◆ account  ■■⬓□□ pct% Nk [◉◎○◌] [cold]  dir  model [effort] [↯]  [⚙ agent]  [vim]  [↑ update]
# Line 2: [↳] ⎇ branch [⋔ worktree] [⬡] [#PR] [✔] [~]  5h-bar [reset]  7d-bar [reset]  [$ spend-bar]  [peak]
#
# Bash port of statusline.ps1 (macOS/Linux/Git Bash) — keep the two in behavior parity.
# Stdin schema (every field name used here): https://code.claude.com/docs/en/statusline
# Install / uninstall: /statusline:custom-statusline-install
# Requires: jq, git (curl for the update check). Runs on bash 3.2+; bash 4.2+/5 avoids extra forks.
#
# Perf note: Git Bash forks are expensive (~20-50ms each), so this script does one jq call for
# stdin + settings + config, builtin-only arithmetic/formatting, and caches git state per session.

# Exit 0 so Claude Code still shows the hint instead of a blank line
command -v jq >/dev/null 2>&1 || { printf 'statusline: jq required'; exit 0; }

LC_TIME=C   # English day names for printf %()T

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
cTeal="${E}[38;2;115;195;195m"
cAmber="${E}[38;2;235;195;80m"
cDim="${E}[38;2;80;75;70m"
cDimmer="${E}[38;2;60;58;55m"
R="${E}[0m"

dimR=50 dimG=48 dimB=45
neuR=195 neuG=180 neuB=165

# Amber/red waypoints for overspend gradient
amberR=235 amberG=195 amberB=80
warnRedR=210 warnRedG=95 warnRedB=85

TMPD="${TMPDIR:-/tmp}"; TMPD="${TMPD%/}"

HAS_PRINTF_T=false
(( BASH_VERSINFO[0] > 4 || (BASH_VERSINFO[0] == 4 && BASH_VERSINFO[1] >= 2) )) && HAS_PRINTF_T=true
if [[ -n "${EPOCHSECONDS:-}" ]]; then NOW=$EPOCHSECONDS
elif $HAS_PRINTF_T; then printf -v NOW '%(%s)T' -1
else NOW=$(date +%s); fi

# Local time of epoch $1 -> FT_TIME ("3:45pm"), FT_DAY ("Wed")
fmt_local() {
    local s
    if $HAS_PRINTF_T; then printf -v s '%(%H %M %a)T' "$1"
    elif [[ "$OSTYPE" == darwin* ]]; then s=$(LC_ALL=C date -r "$1" '+%H %M %a' 2>/dev/null)
    else s=$(LC_ALL=C date -d "@$1" '+%H %M %a' 2>/dev/null); fi
    local h=${s%% *} rest=${s#* }
    local m=${rest%% *}
    FT_DAY=${rest#* }
    h=$((10#${h:-0}))
    local ap=am
    (( h >= 12 )) && ap=pm
    h=$((h % 12)); (( h == 0 )) && h=12
    FT_TIME="${h}:${m}${ap}"
}

is_truthy() {
    case "$1" in 1|true|TRUE|True|yes|YES|on|ON) return 0 ;; *) return 1 ;; esac
}

# Semver-ish "a > b" on major.minor.patch (pre-release/build suffixes ignored)
ver_gt() {
    local a=${1%%[-+ ]*} b=${2%%[-+ ]*} i x y
    local IFS=.
    local -a A=($a) B=($b)
    for i in 0 1 2; do
        x=${A[i]:-0}; y=${B[i]:-0}
        x=${x%%[!0-9]*}; y=${y%%[!0-9]*}
        x=$((10#${x:-0})); y=$((10#${y:-0}))
        (( x > y )) && return 0
        (( x < y )) && return 1
    done
    return 1
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

# --- Paths: active account's config dir ($CLAUDE_CONFIG_DIR, else ~/.claude) ---
cfgDir="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
cfgDir="${cfgDir%[/\\]}"
settingsPath="$cfgDir/settings.json"
slConfigPath="$cfgDir/statusline.config.json"
[[ -f "$slConfigPath" ]] || slConfigPath="$HOME/.claude/statusline.config.json"

# --- Account (which CLAUDE_CONFIG_DIR this session runs under) ---
# ~/.claude (or unset) -> "personal"; ~/.claude-<name> -> "<name>".
# Override per dir in statusline.config.json, as a label string or {label, color}:
#   "accounts": { ".claude-work": { "label": "work", "color": "orange" } }
# color = palette name (sage amber orange teal mauve lavender salmon slate peach sand) or "#RRGGBB"
accountDir=".claude"
if [[ -n "${CLAUDE_CONFIG_DIR:-}" ]]; then
    accountDir="${CLAUDE_CONFIG_DIR//\\//}"; accountDir="${accountDir%/}"
    accountDir="${accountDir##*/}"
fi

# --- Read stdin + settings + statusline config in ONE jq call ---
IFS= read -r -d '' INPUT || true

JQ_PROG='
def obj: if type == "object" then . else {} end;
# Settings/config arrive raw: strip a UTF-8 BOM and parse each on its own, so a bad file only loses its own values
def parsefile: (ltrimstr("﻿") | try fromjson catch {}) | obj;
def s: $s | parsefile;
def c: $c | parsefile;
def num: if type == "number" then . else null end;
def rnd: if type == "number" then (. + 0.5 | floor) else null end;
def v(n; x): n + "=" + ((x // "") | tostring | @sh);
def win(x): if (x | type) == "number" then (x | floor)
    elif (x | type) == "string" then
        ((x | ascii_downcase | capture("^\\s*(?<n>[0-9]+(\\.[0-9]+)?)\\s*(?<u>[km]?)")) // null)
        | if . == null then 0
          else ((.n | tonumber) * (if .u == "m" then 1000000 elif .u == "k" then 1000 else 1 end) | floor) end
    else 0 end;
def pctOf(w): if w == null then -1 else ((w.used_percentage | rnd) // 0) end;
. as $d
| ($d.context_window // {} | obj) as $cw
| (($cw.context_window_size | num) // 0 | floor) as $size
| (if ($cw.current_usage | type) == "object" then
      (($cw.current_usage.input_tokens // 0) + ($cw.current_usage.cache_creation_input_tokens // 0)
       + ($cw.current_usage.cache_read_input_tokens // 0))
   elif ($cw.used_percentage | type) == "number" and $size > 0 then ($size * $cw.used_percentage / 100)
   else 0 end | floor) as $tok
| ($d.rate_limits // null) as $rl
| ($d.prompt_cache // null) as $pc
| ($d.workspace.repo // null) as $repo
| (c.accounts // {} | obj | [to_entries[] | select((.key | ascii_downcase) == ($acct | ascii_downcase))]
   | first.value?) as $a
| v("J_MODEL"; $d.model.display_name // $d.model.id),
  v("J_CWD"; $d.workspace.current_dir // $d.cwd),
  v("J_PROJ"; $d.workspace.project_dir),
  v("J_AGENT"; $d.agent.name),
  v("J_VIM"; $d.vim.mode),
  v("J_SID"; $d.session_id),
  v("J_VER"; $d.version),
  v("J_SIZE"; $size),
  v("J_TOK"; $tok),
  v("J_EFFORT"; $d.effort.level),
  v("J_FAST"; if $d.fast_mode == true then 1 else 0 end),
  v("J_COLD"; if $pc == null or $pc.caching_observed != true then 0
              elif $pc.warm == false then 1
              elif ($pc.expires_at | type) == "number" and $pc.expires_at <= now then 1
              else 0 end),
  v("J_RL"; if $rl == null then 0 else 1 end),
  v("J_FH"; pctOf($rl.five_hour)),
  v("J_FHR"; ($rl.five_hour.resets_at | num) // 0 | floor),
  v("J_SD"; pctOf($rl.seven_day)),
  v("J_SDR"; ($rl.seven_day.resets_at | num) // 0 | floor),
  v("J_SP"; pctOf($rl.spend_limit)),
  v("J_PRN"; $d.pr.number),
  v("J_PRU"; $d.pr.url),
  v("J_PRS"; $d.pr.review_state),
  v("J_PRK"; $d.pr.kind),
  v("J_WT"; $d.workspace.git_worktree // $d.worktree.name),
  v("J_REPO"; if $repo.host and $repo.owner and $repo.name
              then "https://\($repo.host)/\($repo.owner)/\($repo.name)" else "" end),
  v("S_ACE"; if s.autoCompactEnabled == false then 0 else 1 end),
  v("S_ACW"; win(s.autoCompactWindow)),
  v("C_GIT"; if c.showGit == false then 0 else 1 end),
  v("C_UPD"; if c.showUpdateCheck == false then 0 else 1 end),
  v("C_BARS"; if c.showLimitBars == false then 0 else 1 end),
  v("C_ALBL"; if ($a | type) == "string" then $a elif ($a | type) == "object" then ($a.label // "") else "" end),
  v("C_ASTR"; if ($a | type) == "string" then 1 else 0 end),
  v("C_ACOL"; if ($a | type) == "object" then ($a.color // "" | tostring | ascii_downcase) else "" end),
  "J_OK=1"
'

jqArgs=(--arg acct "$accountDir")
if [[ -r "$settingsPath" ]]; then jqArgs+=(--rawfile s "$settingsPath"); else jqArgs+=(--arg s ''); fi
if [[ -r "$slConfigPath" ]]; then jqArgs+=(--rawfile c "$slConfigPath"); else jqArgs+=(--arg c ''); fi
J_OK=0
eval "$(jq -r "${jqArgs[@]}" "$JQ_PROG" <<< "$INPUT" 2>/dev/null)"
: "${J_SIZE:=0}" "${J_TOK:=0}" "${J_FAST:=0}" "${J_COLD:=0}" "${J_RL:=0}" "${J_FH:=-1}" "${J_SD:=-1}" "${J_SP:=-1}"
: "${J_FHR:=0}" "${J_SDR:=0}" "${S_ACE:=1}" "${S_ACW:=0}" "${C_GIT:=1}" "${C_UPD:=1}" "${C_BARS:=1}" "${C_ASTR:=0}"

sidTag="${J_SID//[^A-Za-z0-9_-]/}"; sidTag="${sidTag:0:40}"

# --- Directory (project_dir:relative when cwd differs) ---
projDir="${J_PROJ:-$J_CWD}"
curDir="$J_CWD"
_p="${projDir%[/\\]}"; projName="${_p##*[/\\]}"
_c="${curDir%[/\\]}"; curName="${_c##*[/\\]}"
dsep=/; [[ "$curDir" == *\\* ]] && dsep=\\
# Compare with normalized separators; case-insensitive on Windows (like the PS version)
cmpP="${_p//\\//}"; cmpC="${_c//\\//}"
if [[ "$OSTYPE" == msys* || "$OSTYPE" == cygwin* ]]; then cmpP="${cmpP,,}"; cmpC="${cmpC,,}"; fi
sameDir=false; [[ "$cmpC" == "$cmpP" ]] && sameDir=true

if ! $sameDir && [[ "$cmpC" == "$cmpP"/* ]]; then
    relPath="${_c:${#_p}+1}"
    # Shorten: first/.../last when 3+ segments
    IFS='/\' read -ra _rparts <<< "$relPath"
    if (( ${#_rparts[@]} >= 3 )); then
        relPath="${_rparts[0]}${dsep}...${dsep}${_rparts[${#_rparts[@]}-1]}"
    fi
    dirDisplay="${projName}${cDim}:${cSand}${relPath}"
elif ! $sameDir; then
    dirDisplay="${projName}${cDim}:${cSand}${curName}"
else
    dirDisplay="$projName"
fi

# --- Context percentage: 100% = the point where auto-compaction fires ---
# Documented (code.claude.com/docs/en/settings-reference, env-vars, model-config):
#   autoCompactEnabled (settings.json, default true); DISABLE_AUTO_COMPACT=1 / DISABLE_COMPACT=1 turn it off.
#   Window precedence: CLAUDE_CODE_AUTO_COMPACT_WINDOW (plain int; "500k" reads as 500) > autoCompactWindow
#   > model default; clamped to 100K..1M and capped at the model's context window.
#   CLAUDE_AUTOCOMPACT_PCT_OVERRIDE (1-100) can only lower the trigger.
# An explicit window is documented as the compaction point itself, so it is used as-is.
# Heuristic (unverified) for the model default only: trigger = context size - 33000 (20k output reserve
#   + 13k buffer), which matches the documented ~967K default for 1M windows.
# (--autocompact CLI flag isn't visible to a statusline process and is ignored.)
acOn=true
(( S_ACE == 0 )) && acOn=false
is_truthy "${DISABLE_AUTO_COMPACT:-}" && acOn=false
is_truthy "${DISABLE_COMPACT:-}" && acOn=false

size=$J_SIZE; currentTokens=$J_TOK; pct=0
if (( size > 0 )); then
    if $acOn; then
        win=$size; explicitWin=false
        envW="${CLAUDE_CODE_AUTO_COMPACT_WINDOW:-}"; envW="${envW%%[!0-9]*}"
        if [[ -n "$envW" ]]; then win=$((10#$envW)); explicitWin=true
        elif (( S_ACW > 0 )); then win=$S_ACW; explicitWin=true; fi
        if $explicitWin; then (( win < 100000 )) && win=100000; (( win > 1000000 )) && win=1000000; fi
        (( win > size )) && win=$size
        # Explicit window = the compaction point itself; reserve only applies to the model default
        if $explicitWin; then threshold=$win; else threshold=$((win - 33000)); fi
        pctO="${CLAUDE_AUTOCOMPACT_PCT_OVERRIDE:-}"; pctO="${pctO%%[!0-9]*}"
        if [[ -n "$pctO" ]]; then
            pctO=$((10#$pctO))
            if (( pctO >= 1 && pctO <= 100 )); then
                t2=$((win * pctO / 100)); (( t2 < threshold )) && threshold=$t2
            fi
        fi
    else
        threshold=$size
    fi
    (( threshold < 1 )) && threshold=1
    pct=$(( (currentTokens * 100 + threshold / 2) / threshold ))  # round half up
    # COMPACT (100) only once the threshold is actually reached, not at 99.5% via rounding
    (( currentTokens < threshold && pct >= 100 )) && pct=99
fi
(( pct < 0 )) && pct=0; (( pct > 100 )) && pct=100

# --- Context squares (5 squares, brightness + half-fills, leading = gradient) ---
sqCount=5
grad_rgb "$pct"
gradR=$GR gradG=$GG gradB=$GB
pctScaled=$((pct * sqCount))

squares=""
for (( i=0; i<sqCount; i++ )); do
    rangeStart=$((i * 100))
    rangeEnd=$(((i + 1) * 100))

    if (( pctScaled >= rangeEnd )); then
        squares+="${E}[38;2;${neuR};${neuG};${neuB}m■"
    elif (( pctScaled > rangeStart )); then
        fill=$(( (pctScaled - rangeStart) * 10 ))   # 0–1000 scale
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

# --- Format token count (round half up; 999.5k+ reads as 1.0M) ---
tokenStr=""
if (( currentTokens >= 999500 )); then
    tM=$(( (currentTokens + 50000) / 100000 ))
    tokenStr="$((tM / 10)).$((tM % 10))M"
elif (( currentTokens >= 1000 )); then
    tokenStr="$(( (currentTokens + 500) / 1000 ))k"
elif (( currentTokens > 0 )); then
    tokenStr="$currentTokens"
fi

# --- Focus ring (attention quality — appears at 150k+, unfocuses with degradation) ---
focusRing=""
if (( currentTokens >= 700000 )); then
    # ◌ dashed ring — dim red, barely there
    grad_rgb 95
    fr=$((dimR + (GR - dimR) * 600 / 1000))
    fg=$((dimG + (GG - dimG) * 600 / 1000))
    fb=$((dimB + (GB - dimB) * 600 / 1000))
    focusRing=" ${E}[38;2;${fr};${fg};${fb}m◌${R}"
elif (( currentTokens >= 500000 )); then
    # ○ empty ring — salmon
    grad_rgb 82
    focusRing=" ${E}[38;2;${GR};${GG};${GB}m○${R}"
elif (( currentTokens >= 300000 )); then
    # ◎ hollowing — amber
    grad_rgb 65
    focusRing=" ${E}[38;2;${GR};${GG};${GB}m◎${R}"
elif (( currentTokens >= 150000 )); then
    # ◉ solid — dim, just appeared
    focusRing=" ${cDim}◉${R}"
fi

ctxColor="${E}[38;2;${gradR};${gradG};${gradB}m"
if (( pct >= 100 )); then
    ctxText="$squares ${ctxColor}COMPACT${R}"
elif [[ -n "$tokenStr" ]]; then
    ctxText="$squares ${ctxColor}${pct}%${R} ${cDim}${tokenStr}${R}${focusRing}"
else
    ctxText="$squares ${ctxColor}${pct}%${R}"
fi
# Prompt cache went cold (TTL expired / last response had no cache hits): next turn re-caches
(( J_COLD )) && ctxText+=" ${cDim}cold${R}"

# --- Git info (cached 5s per session; one `git status` call) ---
gitDisplay=""
if (( C_GIT )); then
gitCache="${TMPD}/claude-sl-git-${sidTag:-nosid}.cache"
needGit=true
if [[ -f "$gitCache" ]]; then
    { read -r g_ts; read -r g_proj; read -r g_cur; read -r hasGit; read -r gitNested
      read -r branch; read -r gitStaged; read -r gitModified; read -r gitRemote; } < "$gitCache"
    if [[ "$g_ts" =~ ^[0-9]+$ && "$g_proj" == "$projDir" && "$g_cur" == "$curDir" ]] &&
       (( NOW >= g_ts && NOW - g_ts < 5 )); then
        needGit=false
    fi
fi

if $needGit; then
    hasGit=0 gitNested=0 branch="" gitStaged=0 gitModified=0 gitRemote=""
    # Check projDir first, fall back to curDir (nested repo support)
    gitDir="$projDir"
    if gitOut=$(git --no-optional-locks -C "$projDir" status --porcelain=v2 --branch -uno 2>/dev/null); then
        hasGit=1
    elif ! $sameDir && gitOut=$(git --no-optional-locks -C "$curDir" status --porcelain=v2 --branch -uno 2>/dev/null); then
        hasGit=1; gitNested=1; gitDir="$curDir"
    fi
    if (( hasGit )); then
        while IFS= read -r _l; do
            case "$_l" in
                '# branch.head '*) branch="${_l#\# branch.head }"; [[ "$branch" == "(detached)" ]] && branch="" ;;
                [12u]' '*) [[ "${_l:2:1}" != "." ]] && gitStaged=1; [[ "${_l:3:1}" != "." ]] && gitModified=1 ;;
            esac
        done <<< "$gitOut"
        # Repo URL comes from stdin workspace.repo when it describes the repo we show (see below);
        # otherwise ask git once per cache refresh.
        if [[ -z "$J_REPO" ]] || ! { (( gitNested )) || $sameDir; }; then
            gitRemote=$(git -C "$gitDir" remote get-url origin 2>/dev/null)
            gitRemote="${gitRemote%$'\r'}"
            if [[ "$gitRemote" =~ ^git@([^:]+):(.*)$ ]]; then
                gitRemote="https://${BASH_REMATCH[1]}/${BASH_REMATCH[2]}"
            fi
            gitRemote="${gitRemote%.git}"
            # Drop any user:token@ so credentials never reach the OSC 8 link
            if [[ "$gitRemote" =~ ^([A-Za-z][A-Za-z0-9+.-]*://)[^/@]*@(.*)$ ]]; then
                gitRemote="${BASH_REMATCH[1]}${BASH_REMATCH[2]}"
            fi
        fi
    fi
    printf '%s\n' "$NOW" "$projDir" "$curDir" "$hasGit" "$gitNested" "$branch" "$gitStaged" "$gitModified" "$gitRemote" \
        > "$gitCache" 2>/dev/null
fi

# workspace.repo is parsed from cwd's origin, so it only matches the displayed repo when that repo is cwd's
repoUrl="$gitRemote"
if [[ -n "$J_REPO" ]] && { (( gitNested )) || $sameDir; }; then repoUrl="$J_REPO"; fi

# Build git display: branch (OSC 8 link to repo) [worktree] [⬡ hosted] [#PR] [✔ staged] [~ modified]
nestedPrefix=""
(( hasGit && gitNested )) && nestedPrefix="${cDim}↳ "
if (( hasGit )) && [[ -n "$branch" ]]; then
    if [[ -n "$repoUrl" ]]; then
        gitDisplay="${nestedPrefix}${E}]8;;${repoUrl}${BEL}${cSlate}⎇ ${branch}${R}${E}]8;;${BEL}"
    else
        gitDisplay="${nestedPrefix}${cSlate}⎇ ${branch}${R}"
    fi
    [[ -n "$J_WT" && "$J_WT" != "$branch" ]] && gitDisplay+=" ${cDim}⋔ ${J_WT}${R}"
    [[ -n "$repoUrl" ]] && gitDisplay+=" ${cTeal}⬡${R}"   # hosted repo indicator
    if [[ -n "$J_PRN" ]]; then
        case "$J_PRS" in
            approved)          prC="$cSage" ;;
            changes_requested) prC="$cSalmon" ;;
            draft)             prC="$cDimmer" ;;
            *)                 prC="$cDim" ;;
        esac
        prSig='#'; [[ "$J_PRK" == "mr" ]] && prSig='!'
        if [[ -n "$J_PRU" ]]; then
            gitDisplay+=" ${E}]8;;${J_PRU}${BEL}${prC}${prSig}${J_PRN}${R}${E}]8;;${BEL}"
        else
            gitDisplay+=" ${prC}${prSig}${J_PRN}${R}"
        fi
    fi
    (( gitStaged ))   && gitDisplay+=" ${cSage}✔${R}"
    (( gitModified )) && gitDisplay+=" ${cSalmon}~${R}"
elif (( hasGit )); then
    gitDisplay="${cDimmer}⎇ ${cDim}detached${R}"
else
    gitDisplay="${cDimmer}⎇ no git${R}"
fi
fi  # end if C_GIT

# --- Session start detection (show limit % on first render only) ---
showLimitPct=false
if [[ -n "$sidTag" ]]; then
    sessionMarker="${TMPD}/claude-sl-seen-${sidTag}"
    # Marker holds its last-touch epoch; refreshed hourly so the 24h sweep never hits a live session
    if [[ -e "$sessionMarker" ]]; then
        seenTs=""; read -r seenTs < "$sessionMarker" 2>/dev/null
        if [[ ! "$seenTs" =~ ^[0-9]+$ ]] || (( NOW - seenTs >= 3600 )); then
            printf '%s\n' "$NOW" > "$sessionMarker" 2>/dev/null
        fi
    else
        printf '%s\n' "$NOW" > "$sessionMarker" 2>/dev/null
        showLimitPct=true
        # Once per new session: sweep claude-sl-* temp files untouched for a day
        find "$TMPD" -maxdepth 1 -type f -name 'claude-sl-*' -mmin +1440 -delete >/dev/null 2>&1 </dev/null &
    fi
fi

# --- Limit bars (brightness-based, gradient only on last pip) ---
# Pip base color -> PBR PBG PBB: identity within time budget, identity → amber → red past it
pip_base_rgb() {  # $1=idx $2=barW $3=budget $4..6=bar rgb
    local idx=$1 bW=$2 budget=$3
    PBR=$4; PBG=$5; PBB=$6
    (( idx < budget )) && return
    local pastCount=$((bW - budget))
    (( pastCount <= 0 )) && return
    local t=$(( (idx - budget) * 1000 / pastCount )) s
    if (( t <= 500 )); then
        s=$((t * 1000 / 500))
        PBR=$(($4 + (amberR - $4) * s / 1000))
        PBG=$(($5 + (amberG - $5) * s / 1000))
        PBB=$(($6 + (amberB - $6) * s / 1000))
    else
        s=$(((t - 500) * 1000 / 500))
        PBR=$((amberR + (warnRedR - amberR) * s / 1000))
        PBG=$((amberG + (warnRedG - amberG) * s / 1000))
        PBB=$((amberB + (warnRedB - amberB) * s / 1000))
    fi
}

# Sets BAR. Args: $1=lpct $2=barWidth $3..5=bar rgb $6=budgetCount $7=forceShowPct(true/false)
build_limit_bar() {
    local lpct=$1 bW=$2 barR=$3 barG=$4 barB=$5 budget=$6 forceShow=$7
    (( lpct < 0 )) && lpct=0; (( lpct > 100 )) && lpct=100
    local displayPct=$forceShow
    (( lpct >= 80 )) && displayPct=true
    local pipW=$((10000 / bW)) lpct100=$((lpct * 100))
    local pStr="" txtC="" tLen=0 tStart=-99 i tIdx pipStart pipEnd fill bri
    if $displayPct; then
        if (( lpct >= 100 )); then pStr="100"; else pStr="${lpct}%"; fi
        limit_grad_rgb "$lpct"
        txtC="${E}[38;2;${LR};${LG};${LB}m"
        tLen=${#pStr}
        tStart=$(( (bW - tLen + 1) / 2 ))
    fi
    BAR=""
    for (( i=0; i<bW; i++ )); do
        tIdx=$((i - tStart))
        if (( tIdx >= 0 && tIdx < tLen )); then
            BAR+="${txtC}${pStr:$tIdx:1}"
            continue
        fi
        pipStart=$((i * pipW))
        pipEnd=$(((i + 1) * pipW))
        if (( lpct100 >= pipEnd )); then
            pip_base_rgb "$i" "$bW" "$budget" "$barR" "$barG" "$barB"
            BAR+="${E}[38;2;${PBR};${PBG};${PBB}m▰"
        elif (( lpct100 > pipStart )); then
            fill=$(( (lpct100 - pipStart) * 1000 / pipW ))
            bri=$((250 + 750 * fill / 1000))
            pip_base_rgb "$i" "$bW" "$budget" "$barR" "$barG" "$barB"
            BAR+="${E}[38;2;$((dimR + (PBR - dimR) * bri / 1000));$((dimG + (PBG - dimG) * bri / 1000));$((dimB + (PBB - dimB) * bri / 1000))m▰"
        else
            BAR+="${cDim}▱"
        fi
    done
    BAR+="$R"
}

# --- Rate limits (stdin rate_limits: five_hour / seven_day for subscribers, spend_limit behind a gateway) ---
limitParts=()
if (( C_BARS )); then
    if (( J_RL )); then
        if (( J_FH >= 0 )); then
            fhBudget=0 fhTxt=""
            if (( J_FHR > 0 )); then
                secsLeft=$((J_FHR - NOW)); (( secsLeft < 0 )) && secsLeft=0
                elapsed=$((5 * 3600 - secsLeft)); (( elapsed < 0 )) && elapsed=0
                fhBudget=$((elapsed / 3600)); (( fhBudget > 5 )) && fhBudget=5
            fi
            build_limit_bar "$J_FH" 5 135 180 160 "$fhBudget" "$showLimitPct"   # 5 pips, sage
            # Reset time: >=75% or within 30 min of reset
            if (( J_FHR > 0 )) && (( J_FH >= 75 || (J_FHR - NOW >= 0 && J_FHR - NOW <= 1800) )); then
                fmt_local "$J_FHR"; fhTxt=" ${cSage}${FT_TIME}${R}"
            fi
            limitParts+=("${BAR}${fhTxt}")
        fi
        if (( J_SD >= 0 )); then
            sdBudget=0 sdTxt=""
            if (( J_SDR > 0 )); then
                secsLeft=$((J_SDR - NOW)); (( secsLeft < 0 )) && secsLeft=0
                elapsed=$((7 * 86400 - secsLeft)); (( elapsed < 0 )) && elapsed=0
                sdBudget=$((elapsed / 86400)); (( sdBudget > 7 )) && sdBudget=7
            fi
            build_limit_bar "$J_SD" 7 185 140 160 "$sdBudget" "$showLimitPct"   # 7 pips, mauve
            # Reset time: >=80% or within 4 hours of reset
            if (( J_SDR > 0 )) && (( J_SD >= 80 || (J_SDR - NOW >= 0 && J_SDR - NOW <= 14400) )); then
                fmt_local "$J_SDR"; sdTxt=" ${cMauve}${FT_DAY} ${FT_TIME}${R}"
            fi
            limitParts+=("${BAR}${sdTxt}")
        fi
        if (( J_SP >= 0 )); then
            # Gateway spend limit: period length unknown, so no time-budget overspend tint
            build_limit_bar "$J_SP" 5 205 185 165 5 "$showLimitPct"   # 5 pips, sand
            limitParts+=("${cDim}\$${BAR}")
        fi
        # Peak hours (13-19 UTC on weekdays): limits reportedly burn faster. Source unverified —
        # community observation, not an official Anthropic statement.
        if (( J_FH >= 0 || J_SD >= 0 )); then
            utcHour=$(( (NOW / 3600) % 24 )); utcDow=$(( (NOW / 86400 + 4) % 7 ))   # 0 = Sunday
            (( utcDow >= 1 && utcDow <= 5 && utcHour >= 13 && utcHour < 19 )) && limitParts+=("${cDim}peak${R}")
        fi
    else
        limitParts+=("${cDimmer}limits --${R}")
    fi
fi

# --- Claude Code update check: stdin version vs one global npm cache (1h TTL, fetched in background) ---
updTxt=""
if (( C_UPD )) && [[ -n "$J_VER" ]]; then
    updCache="${TMPD}/claude-sl-update.cache"
    u_ts=0 u_remote=""
    [[ -f "$updCache" ]] && { read -r u_ts; read -r u_remote; } < "$updCache"
    [[ "$u_ts" =~ ^[0-9]+$ ]] || u_ts=0
    if (( NOW - u_ts >= 3600 || u_ts > NOW + 300 )); then
        # Claim the slot (bump the timestamp) so concurrent renders don't all fetch; worker overwrites on success
        printf '%s\n%s\n' "$NOW" "$u_remote" > "$updCache" 2>/dev/null
        (
            v=$(curl -sf --max-time 10 "https://registry.npmjs.org/@anthropic-ai/claude-code/latest" | jq -r '.version // empty')
            if [[ "$v" =~ ^[0-9]+\.[0-9]+ ]]; then
                printf '%s\n%s\n' "$NOW" "$v" > "${updCache}.$$.tmp" && mv -f "${updCache}.$$.tmp" "$updCache"
            fi
        ) >/dev/null 2>&1 </dev/null &
    fi
    if [[ -n "$u_remote" ]] && ver_gt "$u_remote" "$J_VER"; then
        updTxt="  ${cAmber}↑ ${J_VER} → ${u_remote}${R}"
    fi
fi

# --- Account badge color ---
accountLabel="$accountDir"
if [[ "$accountDir" == ".claude" ]]; then accountLabel="personal"
elif [[ "$accountDir" == .claude-* ]]; then accountLabel="${accountDir#.claude-}"
else accountLabel="${accountDir#.}"
fi
if (( C_ASTR )) || [[ -n "${C_ALBL:-}" ]]; then accountLabel="$C_ALBL"; fi
accountColorName="${C_ACOL:-}"
case "$accountColorName" in
    sage)     accountColor="$cSage" ;;
    amber)    accountColor="$cAmber" ;;
    orange)   accountColor="${E}[38;2;230;145;70m" ;;
    teal)     accountColor="$cTeal" ;;
    mauve)    accountColor="$cMauve" ;;
    lavender) accountColor="$cLav" ;;
    salmon)   accountColor="$cSalmon" ;;
    slate)    accountColor="$cSlate" ;;
    peach)    accountColor="$cPeach" ;;
    sand)     accountColor="$cSand" ;;
    *)        accountColor="" ;;
esac
if [[ -z "$accountColor" && "$accountColorName" =~ ^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$ ]]; then
    accountColor="${E}[38;2;$((16#${BASH_REMATCH[1]}));$((16#${BASH_REMATCH[2]}));$((16#${BASH_REMATCH[3]}))m"
fi
if [[ -z "$accountColor" ]]; then
    # No configured color: stable color per label so each account always reads the same
    accountPalette=("$cSage" "$cAmber" "$cTeal" "$cMauve" "$cLav" "$cSalmon")
    accountHash=0
    for (( i=0; i<${#accountLabel}; i++ )); do
        printf -v _c '%d' "'${accountLabel:$i:1}"; accountHash=$((accountHash + _c))
    done
    if [[ "$accountLabel" == "personal" ]]; then accountColor="$cSage"
    else accountColor="${accountPalette[$((1 + accountHash % 5))]}"
    fi
fi

# --- Output ---
# Line 1: [account]  context [cold]  dir  model [effort] [fast]  [agent]  [vim]  [update]
line1="${ctxText}  ${cSand}${dirDisplay}${R}  ${cPeach}${J_MODEL}${R}"
[[ -n "${J_EFFORT:-}" ]] && line1+=" ${cDim}${J_EFFORT}${R}"
(( J_FAST )) && line1+=" ${cPeach}↯${R}"
[[ -n "$accountLabel" ]] && line1="${accountColor}◆ ${accountLabel}${R}  ${line1}"
[[ -n "${J_AGENT:-}" ]] && line1+="  ${cLav}⚙ ${J_AGENT}${R}"
[[ -n "${J_VIM:-}" ]]   && line1+="  ${cDim}${J_VIM}${R}"
line1+="$updTxt"

# Line 2: git  limits
line2="$gitDisplay"
for _part in "${limitParts[@]}"; do
    if [[ -n "$line2" ]]; then line2+="  ${_part}"; else line2="$_part"; fi
done

printf '%s\n%s' "$line1" "$line2"
