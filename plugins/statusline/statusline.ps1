# Claude Code statusline — pastel, brightness squares, git+hosting, gradient limits
# Line 1: ◆ account  ■■⬓□□ pct% Nk [◉◎○◌] [cold]  dir  model [effort] [↯]  [⚙ agent]  [vim]  [↑ update]
# Line 2: [↳] ⎇ branch [⋔ worktree] [⬡] [#PR] [✔] [~]  5h-bar [reset]  7d-bar [reset]  [$ spend-bar]  [peak]
#
# Windows PowerShell 5.1 compatible. statusline.sh is the bash port — keep the two in behavior parity
# (color math uses truncating integer arithmetic on purpose so both emit identical bytes).
# Stdin schema (every field name used here): https://code.claude.com/docs/en/statusline
# Install / uninstall: /statusline:custom-statusline-install
#
# Reference implementations:
#   https://github.com/NoobyGains/claude-pulse        — Python, rainbow animation, usage data, update notifications
#   https://github.com/sirmalloc/ccstatusline          — pre-built themes and configs
#   https://github.com/martinemde/starship-claude      — Starship prompt integration
$ErrorActionPreference = 'SilentlyContinue'
try { [Console]::InputEncoding = New-Object System.Text.UTF8Encoding $false } catch {}
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false
$esc = [char]27
$bel = [char]7
$inv = [System.Globalization.CultureInfo]::InvariantCulture
$NOW = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()

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
# Amber/red waypoints for overspend gradient
$amberR = 235; $amberG = 195; $amberB = 80
$warnRedR = 210; $warnRedG = 95; $warnRedB = 85

# Integer division truncating toward zero (bash $(( a / b )) semantics)
function Q([double]$a, [double]$b) { return [long][math]::Truncate($a / $b) }
function IsNum($v) { return ($v -is [int] -or $v -is [long] -or $v -is [double] -or $v -is [decimal]) }
function IsFalse($v) { return ($v -is [bool] -and -not $v) }
function IsTrue($v) { return ($v -is [bool] -and $v) }
function Test-Truthy([string]$v) { return @('1','true','yes','on') -contains $v.ToLowerInvariant() }

# --- Gradient RGB (green -> amber -> red) ---
function Get-GradRGB([int]$p) {
    $p = [math]::Max(0, [math]::Min(100, $p))
    if ($p -le 60) {
        $t = Q ($p * 1000) 60
        return @((130 + (Q (50 * $t) 1000)), (190 + (Q (5 * $t) 1000)), (150 - (Q (30 * $t) 1000)))
    } elseif ($p -le 80) {
        $t = Q (($p - 60) * 1000) 20
        return @((180 + (Q (30 * $t) 1000)), (195 - (Q (20 * $t) 1000)), (120 - (Q (20 * $t) 1000)))
    } else {
        $t = Q (($p - 80) * 1000) 20
        return @(210, (175 - (Q (80 * $t) 1000)), (100 - (Q (15 * $t) 1000)))
    }
}

# --- Limit-bar gradient (80%=green, 100%=red, saturation ramps at high %) ---
function Get-LimitGradRGB([int]$p) {
    $p = [math]::Max(0, [math]::Min(100, $p))
    if ($p -le 80) {
        $r = 130; $g = 190; $b = 150
    } elseif ($p -le 90) {
        $t = Q (($p - 80) * 1000) 10
        $r = 130 + (Q (80 * $t) 1000); $g = 190 - (Q (15 * $t) 1000); $b = 150 - (Q (50 * $t) 1000)
    } else {
        $t = Q (($p - 90) * 1000) 10
        $r = 210; $g = 175 - (Q (80 * $t) 1000); $b = 100 - (Q (15 * $t) 1000)
    }
    # Dynamic muting: muted at <=80%, increasingly saturated toward 100%
    $mf = 750
    if ($p -gt 80) { $mf = 750 + (Q (250 * ($p - 80)) 20) }
    return @(($dimR + (Q (($r - $dimR) * $mf) 1000)), ($dimG + (Q (($g - $dimG) * $mf) 1000)), ($dimB + (Q (($b - $dimB) * $mf) 1000)))
}

# --- Read JSON ---
$data = [System.Console]::In.ReadToEnd() | ConvertFrom-Json
if ($null -eq $data) { $data = New-Object PSObject }

# --- Paths: active account's config dir ($CLAUDE_CONFIG_DIR, else ~/.claude) ---
$homeDir = [System.Environment]::GetFolderPath('UserProfile')
$cfgDir = if ($env:CLAUDE_CONFIG_DIR) { $env:CLAUDE_CONFIG_DIR -replace '[/\\]$', '' } else { Join-Path $homeDir '.claude' }
$ccConfig = $null; $slConfig = $null
try { $ccConfig = [IO.File]::ReadAllText((Join-Path $cfgDir 'settings.json')) | ConvertFrom-Json } catch {}
$slConfigPath = Join-Path $cfgDir 'statusline.config.json'
if (-not (Test-Path -LiteralPath $slConfigPath)) { $slConfigPath = Join-Path $homeDir '.claude\statusline.config.json' }
try { $slConfig = [IO.File]::ReadAllText($slConfigPath) | ConvertFrom-Json } catch {}

$slShowGit       = -not (IsFalse $slConfig.showGit)
$slShowUpdate    = -not (IsFalse $slConfig.showUpdateCheck)
$slShowLimitBars = -not (IsFalse $slConfig.showLimitBars)

# --- Basic fields ---
$model = $data.model.display_name; if ($null -eq $model) { $model = $data.model.id }; $model = [string]$model
$agentName = [string]$data.agent.name
$vimMode = [string]$data.vim.mode
$sid = [string]$data.session_id
$sidTag = $sid -replace '[^A-Za-z0-9_-]', ''
if ($sidTag.Length -gt 40) { $sidTag = $sidTag.Substring(0, 40) }
$ccVersion = [string]$data.version
$effort = [string]$data.effort.level
$fastMode = IsTrue $data.fast_mode
$worktreeName = $data.workspace.git_worktree; if ($null -eq $worktreeName) { $worktreeName = $data.worktree.name }; $worktreeName = [string]$worktreeName
$stdinRepo = ""
$repo = $data.workspace.repo
if ($repo -and $repo.host -and $repo.owner -and $repo.name) { $stdinRepo = "https://$($repo.host)/$($repo.owner)/$($repo.name)" }

# --- Directory (project_dir:relative when cwd differs) ---
$curDir = $data.workspace.current_dir; if ($null -eq $curDir) { $curDir = $data.cwd }; $curDir = [string]$curDir
$projDir = [string]$data.workspace.project_dir; if (-not $projDir) { $projDir = $curDir }
$pT = $projDir -replace '[/\\]$', ''; $projName = $pT -replace '^.*[/\\]', ''
$cT = $curDir -replace '[/\\]$', ''; $curName = $cT -replace '^.*[/\\]', ''
$dsep = if ($curDir.Contains('\')) { '\' } else { '/' }
$cmpP = $pT.Replace('\', '/'); $cmpC = $cT.Replace('\', '/')
$ic = [System.StringComparison]::OrdinalIgnoreCase
$sameDir = [string]::Equals($cmpC, $cmpP, $ic)

if (-not $sameDir -and $cmpC.StartsWith($cmpP + '/', $ic)) {
    $relPath = $cT.Substring($pT.Length + 1)
    # Shorten: first\...\last when 3+ segments
    $relParts = $relPath -split '[/\\]'
    if ($relParts.Count -ge 3) { $relPath = "$($relParts[0])$dsep...$dsep$($relParts[-1])" }
    $dirDisplay = "${projName}${cDim}:${cSand}${relPath}"
} elseif (-not $sameDir) {
    $dirDisplay = "${projName}${cDim}:${cSand}${curName}"
} else {
    $dirDisplay = $projName
}

# --- Account (which CLAUDE_CONFIG_DIR this session runs under) ---
# ~/.claude (or unset) -> "personal"; ~/.claude-<name> -> "<name>".
# Override per dir in statusline.config.json, as a label string or {label, color}:
#   "accounts": { ".claude-work": { "label": "work", "color": "orange" } }
# color = palette name (sage amber orange teal mauve lavender salmon slate peach sand) or "#RRGGBB"
$accountDir = if ($env:CLAUDE_CONFIG_DIR) { Split-Path -Leaf ($env:CLAUDE_CONFIG_DIR.TrimEnd('\', '/')) } else { ".claude" }
if ($accountDir -eq ".claude") { $accountLabel = "personal" }
elseif ($accountDir -like ".claude-*") { $accountLabel = $accountDir.Substring(8) }
else { $accountLabel = $accountDir.TrimStart('.') }
$accountColorName = ""
# Account key match is case-insensitive (Windows dir names); first match in file order wins
$acctProp = $null
if ($slConfig -and $slConfig.accounts -is [System.Management.Automation.PSCustomObject]) {
    $acctProp = $slConfig.accounts.PSObject.Properties | Where-Object { $_.Name -ieq $accountDir } | Select-Object -First 1
}
if ($acctProp) {
    $acct = $acctProp.Value
    if ($acct -is [string]) { $accountLabel = $acct }
    else {
        if ($acct.PSObject.Properties['label'] -and $acct.label) { $accountLabel = [string]$acct.label }
        if ($acct.PSObject.Properties['color']) { $accountColorName = ([string]$acct.color).ToLower() }
    }
}
$accountNamedColors = @{
    sage = $cSage; amber = $cAmber; orange = "$esc[38;2;230;145;70m"; teal = $cTeal; mauve = $cMauve
    lavender = $cLav; salmon = $cSalmon; slate = $cSlate; peach = $cPeach; sand = $cSand
}
if ($accountNamedColors.ContainsKey($accountColorName)) { $accountColor = $accountNamedColors[$accountColorName] }
elseif ($accountColorName -match '^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$') {
    $accountColor = "$esc[38;2;$([Convert]::ToInt32($Matches[1],16));$([Convert]::ToInt32($Matches[2],16));$([Convert]::ToInt32($Matches[3],16))m"
} else {
    # No configured color: stable color per label so each account always reads the same
    $accountPalette = @($cSage, $cAmber, $cTeal, $cMauve, $cLav, $cSalmon)
    $accountHash = 0; foreach ($ch in $accountLabel.ToCharArray()) { $accountHash += [int]$ch }
    $accountColor = if ($accountLabel -eq "personal") { $cSage } else { $accountPalette[1 + ($accountHash % ($accountPalette.Count - 1))] }
}

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
$cw = $data.context_window
$size = [long]0
if (IsNum $cw.context_window_size) { $size = [long][math]::Floor([double]$cw.context_window_size) }
$currentTokens = [long]0
if ($cw.current_usage -is [System.Management.Automation.PSCustomObject]) {
    $cu = $cw.current_usage
    $currentTokens = [long][math]::Floor([double]$cu.input_tokens + [double]$cu.cache_creation_input_tokens + [double]$cu.cache_read_input_tokens)
} elseif ((IsNum $cw.used_percentage) -and $size -gt 0) {
    $currentTokens = [long][math]::Floor($size * [double]$cw.used_percentage / 100)
}

$autoCompactOn = -not (IsFalse $ccConfig.autoCompactEnabled)
if (Test-Truthy $env:DISABLE_AUTO_COMPACT) { $autoCompactOn = $false }
if (Test-Truthy $env:DISABLE_COMPACT) { $autoCompactOn = $false }
$settingWin = [long]0
$acw = $ccConfig.autoCompactWindow
if (IsNum $acw) { $settingWin = [long][math]::Floor([double]$acw) }
elseif ($acw -is [string] -and $acw.ToLowerInvariant() -match '^\s*([0-9]+(\.[0-9]+)?)\s*([km]?)') {
    $mult = switch ($Matches[3]) { 'm' { 1000000 } 'k' { 1000 } default { 1 } }
    $settingWin = [long][math]::Floor([double]::Parse($Matches[1], $inv) * $mult)
}

$pct = 0
if ($size -gt 0) {
    if ($autoCompactOn) {
        $win = $size; $explicitWin = $false
        if ("$env:CLAUDE_CODE_AUTO_COMPACT_WINDOW" -match '^[0-9]+') { $win = [long]$Matches[0]; $explicitWin = $true }
        elseif ($settingWin -gt 0) { $win = $settingWin; $explicitWin = $true }
        if ($explicitWin) { $win = [math]::Max(100000, [math]::Min(1000000, $win)) }
        if ($win -gt $size) { $win = $size }
        # Explicit window = the compaction point itself; reserve only applies to the model default
        $threshold = if ($explicitWin) { $win } else { $win - 33000 }
        if ("$env:CLAUDE_AUTOCOMPACT_PCT_OVERRIDE" -match '^[0-9]+') {
            $pctO = [long]$Matches[0]
            if ($pctO -ge 1 -and $pctO -le 100) { $threshold = [math]::Min($threshold, (Q ($win * $pctO) 100)) }
        }
    } else {
        $threshold = $size
    }
    if ($threshold -lt 1) { $threshold = 1 }
    $pct = Q ($currentTokens * 100 + (Q $threshold 2)) $threshold   # round half up
    # COMPACT (100) only once the threshold is actually reached, not at 99.5% via rounding
    if ($currentTokens -lt $threshold -and $pct -ge 100) { $pct = 99 }
}
$pct = [int][math]::Max(0, [math]::Min(100, $pct))

# --- Context squares (5 squares, brightness + half-fills, leading = gradient) ---
$sq_full  = [char]0x25A0
$sq_half  = [char]0x2B13
$sq_empty = [char]0x25A1
$sqCount = 5
$gradRGB = Get-GradRGB $pct
$pctScaled = $pct * $sqCount

$squares = ""
for ($i = 0; $i -lt $sqCount; $i++) {
    $rangeStart = $i * 100
    $rangeEnd = ($i + 1) * 100
    if ($pctScaled -ge $rangeEnd) {
        $squares += "$esc[38;2;${neuR};${neuG};${neuB}m${sq_full}"
    } elseif ($pctScaled -gt $rangeStart) {
        $fill = ($pctScaled - $rangeStart) * 10   # 0-1000 scale
        $bri = 250 + (Q (750 * $fill) 1000)
        $sr = $dimR + (Q (($gradRGB[0] - $dimR) * $bri) 1000)
        $sg = $dimG + (Q (($gradRGB[1] - $dimG) * $bri) 1000)
        $sb = $dimB + (Q (($gradRGB[2] - $dimB) * $bri) 1000)
        $sqC = "$esc[38;2;${sr};${sg};${sb}m"
        if ($fill -ge 750) { $squares += "${sqC}${sq_full}" }
        elseif ($fill -ge 250) { $squares += "${sqC}${sq_half}" }
        else { $squares += "${sqC}${sq_empty}" }
    } else {
        $squares += "$esc[38;2;${dimR};${dimG};${dimB}m${sq_empty}"
    }
}
$squares += $R

# --- Format token count (round half up; 999.5k+ reads as 1.0M) ---
$tokenStr = ""
if ($currentTokens -ge 999500) {
    $tM = Q ($currentTokens + 50000) 100000
    $tokenStr = "$(Q $tM 10).$($tM % 10)M"
} elseif ($currentTokens -ge 1000) {
    $tokenStr = "$(Q ($currentTokens + 500) 1000)k"
} elseif ($currentTokens -gt 0) {
    $tokenStr = "$currentTokens"
}

# --- Focus ring (attention quality — appears at 150k+, unfocuses with degradation) ---
$focusRing = ""
if ($currentTokens -ge 700000) {
    # ◌ dashed ring — dim red, barely there
    $fr = Get-GradRGB 95
    $rr = $dimR + (Q (($fr[0] - $dimR) * 600) 1000)
    $rg = $dimG + (Q (($fr[1] - $dimG) * 600) 1000)
    $rb = $dimB + (Q (($fr[2] - $dimB) * 600) 1000)
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

$ctxColor = "$esc[38;2;$($gradRGB[0]);$($gradRGB[1]);$($gradRGB[2])m"
if ($pct -ge 100) {
    $ctxText = "$squares ${ctxColor}COMPACT${R}"
} elseif ($tokenStr) {
    $ctxText = "$squares ${ctxColor}${pct}%${R} ${cDim}${tokenStr}${R}${focusRing}"
} else {
    $ctxText = "$squares ${ctxColor}${pct}%${R}"
}
# Prompt cache went cold (TTL expired / last response had no cache hits): next turn re-caches
$pc = $data.prompt_cache
if ($pc -and (IsTrue $pc.caching_observed)) {
    if ((IsFalse $pc.warm) -or ((IsNum $pc.expires_at) -and [double]$pc.expires_at -le $NOW)) { $ctxText += " ${cDim}cold${R}" }
}

# --- Git info (cached 5s per session; one `git status` call) ---
$tmpDir = $env:TEMP
$gitDisplay = ""
$hasGit = $false; $gitNested = $false
if ($slShowGit) {
    $gitCache = Join-Path $tmpDir ("claude-sl-git-" + $(if ($sidTag) { $sidTag } else { "nosid" }) + ".cache")
    $branch = ""; $gitStaged = $false; $gitModified = $false; $gitRemote = ""
    $needGit = $true
    try {
        $gl = [IO.File]::ReadAllLines($gitCache)
        if ($gl.Count -ge 9 -and $gl[0] -match '^[0-9]+$' -and $gl[1] -ceq $projDir -and $gl[2] -ceq $curDir) {
            $gTs = [long]$gl[0]
            if ($NOW -ge $gTs -and ($NOW - $gTs) -lt 5) {
                $needGit = $false
                $hasGit = $gl[3] -eq '1'; $gitNested = $gl[4] -eq '1'; $branch = $gl[5]
                $gitStaged = $gl[6] -eq '1'; $gitModified = $gl[7] -eq '1'; $gitRemote = $gl[8]
            }
        }
    } catch {}

    if ($needGit) {
        # Check projDir first, fall back to curDir (nested repo support)
        $gitDir = $projDir
        $gitOut = @(& git --no-optional-locks -C $projDir status --porcelain=v2 --branch -uno 2>$null)
        if ($LASTEXITCODE -eq 0) { $hasGit = $true }
        elseif (-not $sameDir) {
            $gitOut = @(& git --no-optional-locks -C $curDir status --porcelain=v2 --branch -uno 2>$null)
            if ($LASTEXITCODE -eq 0) { $hasGit = $true; $gitNested = $true; $gitDir = $curDir }
        }
        if ($hasGit) {
            foreach ($l in $gitOut) {
                if ($l.StartsWith('# branch.head ')) {
                    $branch = $l.Substring(14); if ($branch -eq '(detached)') { $branch = "" }
                } elseif ($l -match '^[12u] ') {
                    if ($l[2] -ne '.') { $gitStaged = $true }
                    if ($l[3] -ne '.') { $gitModified = $true }
                }
            }
            # Repo URL comes from stdin workspace.repo when it describes the repo we show (see below);
            # otherwise ask git once per cache refresh.
            if (-not $stdinRepo -or -not ($gitNested -or $sameDir)) {
                $remote = [string](& git -C $gitDir remote get-url origin 2>$null)
                # SSH -> HTTPS; drop any user:token@ so credentials never reach the OSC 8 link
                if ($remote) {
                    $gitRemote = ($remote.Trim() -replace '^git@([^:]+):', 'https://$1/' -replace '\.git$', '' `
                        -replace '^([A-Za-z][A-Za-z0-9+.-]*://)[^/@]*@', '$1')
                }
            }
        }
        $b2 = { param($x) if ($x) { '1' } else { '0' } }
        try {
            [IO.File]::WriteAllText($gitCache, ((@("$NOW", $projDir, $curDir, (& $b2 $hasGit), (& $b2 $gitNested), $branch,
                (& $b2 $gitStaged), (& $b2 $gitModified), $gitRemote) -join "`n") + "`n"))
        } catch {}
    }

    # workspace.repo is parsed from cwd's origin, so it only matches the displayed repo when that repo is cwd's
    $repoUrl = $gitRemote
    if ($stdinRepo -and ($gitNested -or $sameDir)) { $repoUrl = $stdinRepo }

    # Build git display: branch (OSC 8 link to repo) [worktree] [⬡ hosted] [#PR] [✔ staged] [~ modified]
    $gitIcon = [char]0x2387   # ⎇
    $nestedPrefix = if ($hasGit -and $gitNested) { "${cDim}$([char]0x21B3) " } else { "" }   # ↳ nested repo
    if ($hasGit -and $branch) {
        if ($repoUrl) {
            $gitDisplay = "${nestedPrefix}${esc}]8;;${repoUrl}${bel}${cSlate}${gitIcon} ${branch}${R}${esc}]8;;${bel}"
        } else {
            $gitDisplay = "${nestedPrefix}${cSlate}${gitIcon} ${branch}${R}"
        }
        if ($worktreeName -and $worktreeName -cne $branch) { $gitDisplay += " ${cDim}$([char]0x22D4) ${worktreeName}${R}" }
        if ($repoUrl) { $gitDisplay += " ${cTeal}$([char]0x2B21)${R}" }   # ⬡ hosted repo indicator
        $prNum = [string]$data.pr.number
        if ($prNum) {
            $prC = switch ([string]$data.pr.review_state) {
                'approved' { $cSage } 'changes_requested' { $cSalmon } 'draft' { $cDimmer } default { $cDim }
            }
            $prSig = if ([string]$data.pr.kind -eq 'mr') { '!' } else { '#' }
            $prUrl = [string]$data.pr.url
            if ($prUrl) { $gitDisplay += " ${esc}]8;;${prUrl}${bel}${prC}${prSig}${prNum}${R}${esc}]8;;${bel}" }
            else { $gitDisplay += " ${prC}${prSig}${prNum}${R}" }
        }
        if ($gitStaged) { $gitDisplay += " ${cSage}$([char]0x2714)${R}" }
        if ($gitModified) { $gitDisplay += " ${cSalmon}~${R}" }
    } elseif ($hasGit) {
        $gitDisplay = "${cDimmer}${gitIcon} ${cDim}detached${R}"
    } else {
        $gitDisplay = "${cDimmer}${gitIcon} no git${R}"
    }
}

# --- Session start detection (show limit % on first render only) ---
$showLimitPct = $false
if ($sidTag) {
    $sessionMarker = Join-Path $tmpDir "claude-sl-seen-$sidTag"
    # Marker holds its last-touch epoch; refreshed hourly so the 24h sweep never hits a live session
    $seenTs = $null
    try { $seenTs = [IO.File]::ReadAllText($sessionMarker).Trim() } catch {}
    if ($null -ne $seenTs) {
        if ($seenTs -notmatch '^[0-9]+$' -or ($NOW - [long]$seenTs) -ge 3600) {
            try { [IO.File]::WriteAllText($sessionMarker, "$NOW`n") } catch {}
        }
    } else {
        try { [IO.File]::WriteAllText($sessionMarker, "$NOW`n") } catch {}
        $showLimitPct = $true
        # Once per new session: sweep claude-sl-* temp files untouched for a day
        try {
            $cutoff = (Get-Date).AddDays(-1)
            Get-ChildItem -LiteralPath $tmpDir -Filter 'claude-sl-*' -File |
                Where-Object { $_.LastWriteTime -lt $cutoff } | Remove-Item -Force
        } catch {}
    }
}

# --- Limit bars (brightness-based, gradient only on last pip) ---
# Pip base color: identity within time budget, identity -> amber -> red past it
function Get-PipBaseRGB([int]$idx, [int]$bW, [int]$budget, [int[]]$barRGB) {
    if ($idx -lt $budget) { return $barRGB }
    $pastCount = $bW - $budget
    if ($pastCount -le 0) { return $barRGB }
    $t = Q (($idx - $budget) * 1000) $pastCount
    if ($t -le 500) {
        $s = Q ($t * 1000) 500
        return @(($barRGB[0] + (Q (($amberR - $barRGB[0]) * $s) 1000)), ($barRGB[1] + (Q (($amberG - $barRGB[1]) * $s) 1000)), ($barRGB[2] + (Q (($amberB - $barRGB[2]) * $s) 1000)))
    }
    $s = Q (($t - 500) * 1000) 500
    return @(($amberR + (Q (($warnRedR - $amberR) * $s) 1000)), ($amberG + (Q (($warnRedG - $amberG) * $s) 1000)), ($amberB + (Q (($warnRedB - $amberB) * $s) 1000)))
}

function Build-LimitBar([int]$lpct, [int]$bW, [int[]]$barRGB, [int]$budget, [bool]$forceShowPct) {
    $lpct = [math]::Max(0, [math]::Min(100, $lpct))
    $displayPct = $forceShowPct -or ($lpct -ge 80)
    $pipW = Q 10000 $bW
    $lpct100 = $lpct * 100
    $pStr = ""; $txtC = ""; $tStart = -99
    if ($displayPct) {
        $pStr = if ($lpct -ge 100) { "100" } else { "${lpct}%" }
        $lg = Get-LimitGradRGB $lpct
        $txtC = "$esc[38;2;$($lg[0]);$($lg[1]);$($lg[2])m"
        $tStart = Q ($bW - $pStr.Length + 1) 2
    }
    $result = ""
    for ($i = 0; $i -lt $bW; $i++) {
        $tIdx = $i - $tStart
        if ($tIdx -ge 0 -and $tIdx -lt $pStr.Length) { $result += "${txtC}$($pStr[$tIdx])"; continue }
        $pipStart = $i * $pipW
        $pipEnd = ($i + 1) * $pipW
        if ($lpct100 -ge $pipEnd) {
            $p = Get-PipBaseRGB $i $bW $budget $barRGB
            $result += "$esc[38;2;$($p[0]);$($p[1]);$($p[2])m$([char]0x25B0)"
        } elseif ($lpct100 -gt $pipStart) {
            $fill = Q (($lpct100 - $pipStart) * 1000) $pipW
            $bri = 250 + (Q (750 * $fill) 1000)
            $p = Get-PipBaseRGB $i $bW $budget $barRGB
            $result += "$esc[38;2;$($dimR + (Q (($p[0] - $dimR) * $bri) 1000));$($dimG + (Q (($p[1] - $dimG) * $bri) 1000));$($dimB + (Q (($p[2] - $dimB) * $bri) 1000))m$([char]0x25B0)"
        } else {
            $result += "${cDim}$([char]0x25B1)"
        }
    }
    return "${result}${R}"
}

function Get-PctOf($w) {
    if ($null -eq $w) { return -1 }
    if (IsNum $w.used_percentage) { return [long][math]::Floor([double]$w.used_percentage + 0.5) }
    return 0
}
function Get-ResetOf($w) { if (IsNum $w.resets_at) { return [long][math]::Floor([double]$w.resets_at) } return [long]0 }
function Format-LocalTime([long]$e) {
    $dt = [DateTimeOffset]::FromUnixTimeSeconds($e).LocalDateTime
    return @(($dt.ToString('h:mm', $inv) + $dt.ToString('tt', $inv).ToLowerInvariant()), $dt.ToString('ddd', $inv))
}

# --- Rate limits (stdin rate_limits: five_hour / seven_day for subscribers, spend_limit behind a gateway) ---
$limitParts = @()
if ($slShowLimitBars) {
    $rl = $data.rate_limits
    if ($null -ne $rl) {
        $fhPct = Get-PctOf $rl.five_hour; $fhReset = Get-ResetOf $rl.five_hour
        $sdPct = Get-PctOf $rl.seven_day; $sdReset = Get-ResetOf $rl.seven_day
        $spPct = Get-PctOf $rl.spend_limit
        if ($fhPct -ge 0) {
            $fhBudget = 0; $fhTxt = ""
            if ($fhReset -gt 0) {
                $secsLeft = [math]::Max(0, $fhReset - $NOW)
                $elapsed = [math]::Max(0, 5 * 3600 - $secsLeft)
                $fhBudget = [math]::Min(5, (Q $elapsed 3600))
            }
            $bar = Build-LimitBar $fhPct 5 @(135, 180, 160) $fhBudget $showLimitPct   # 5 pips, sage
            # Reset time: >=75% or within 30 min of reset
            if ($fhReset -gt 0 -and ($fhPct -ge 75 -or (($fhReset - $NOW) -ge 0 -and ($fhReset - $NOW) -le 1800))) {
                $ft = Format-LocalTime $fhReset; $fhTxt = " ${cSage}$($ft[0])${R}"
            }
            $limitParts += "${bar}${fhTxt}"
        }
        if ($sdPct -ge 0) {
            $sdBudget = 0; $sdTxt = ""
            if ($sdReset -gt 0) {
                $secsLeft = [math]::Max(0, $sdReset - $NOW)
                $elapsed = [math]::Max(0, 7 * 86400 - $secsLeft)
                $sdBudget = [math]::Min(7, (Q $elapsed 86400))
            }
            $bar = Build-LimitBar $sdPct 7 @(185, 140, 160) $sdBudget $showLimitPct   # 7 pips, mauve
            # Reset time: >=80% or within 4 hours of reset
            if ($sdReset -gt 0 -and ($sdPct -ge 80 -or (($sdReset - $NOW) -ge 0 -and ($sdReset - $NOW) -le 14400))) {
                $ft = Format-LocalTime $sdReset; $sdTxt = " ${cMauve}$($ft[1]) $($ft[0])${R}"
            }
            $limitParts += "${bar}${sdTxt}"
        }
        if ($spPct -ge 0) {
            # Gateway spend limit: period length unknown, so no time-budget overspend tint
            $bar = Build-LimitBar $spPct 5 @(205, 185, 165) 5 $showLimitPct   # 5 pips, sand
            $limitParts += "${cDim}`$${bar}"
        }
        # Peak hours (13-19 UTC on weekdays): limits reportedly burn faster. Source unverified —
        # community observation, not an official Anthropic statement.
        if ($fhPct -ge 0 -or $sdPct -ge 0) {
            $utcHour = (Q $NOW 3600) % 24; $utcDow = ((Q $NOW 86400) + 4) % 7   # 0 = Sunday
            if ($utcDow -ge 1 -and $utcDow -le 5 -and $utcHour -ge 13 -and $utcHour -lt 19) { $limitParts += "${cDim}peak${R}" }
        }
    } else {
        $limitParts += "${cDimmer}limits --${R}"
    }
}

# --- Claude Code update check: stdin version vs one global npm cache (1h TTL, fetched in background) ---
function Test-VerGt([string]$a, [string]$b) {
    $pa = ($a -split '[-+ ]')[0].Split('.'); $pb = ($b -split '[-+ ]')[0].Split('.')
    for ($i = 0; $i -lt 3; $i++) {
        $x = 0; $y = 0
        if ($i -lt $pa.Count -and $pa[$i] -match '^[0-9]+') { $x = [long]$Matches[0] }
        if ($i -lt $pb.Count -and $pb[$i] -match '^[0-9]+') { $y = [long]$Matches[0] }
        if ($x -gt $y) { return $true }
        if ($x -lt $y) { return $false }
    }
    return $false
}
$updTxt = ""
if ($slShowUpdate -and $ccVersion) {
    $updCache = Join-Path $tmpDir 'claude-sl-update.cache'
    $uTs = [long]0; $uRemote = ""
    try {
        $ul = [IO.File]::ReadAllLines($updCache)
        if ($ul.Count -ge 1 -and $ul[0] -match '^[0-9]+$') { $uTs = [long]$ul[0] }
        if ($ul.Count -ge 2) { $uRemote = $ul[1].Trim() }
    } catch {}
    if (($NOW - $uTs) -ge 3600 -or $uTs -gt ($NOW + 300)) {
        # Claim the slot (bump the timestamp) so concurrent renders don't all fetch; worker overwrites on success
        try { [IO.File]::WriteAllText($updCache, "$NOW`n$uRemote`n") } catch {}
        $worker = @'
try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $v = [string](Invoke-RestMethod -Uri 'https://registry.npmjs.org/@anthropic-ai/claude-code/latest' -TimeoutSec 10 -UseBasicParsing).version
    if ($v -match '^[0-9]+\.[0-9]+') {
        $dst = '__CACHE__'; $tmp = $dst + '.' + $PID + '.tmp'
        [IO.File]::WriteAllText($tmp, "__NOW__`n$v`n")
        if ([IO.File]::Exists($dst)) { [IO.File]::Replace($tmp, $dst, [NullString]::Value) } else { [IO.File]::Move($tmp, $dst) }
    }
} catch {}
'@
        $worker = $worker.Replace('__CACHE__', $updCache.Replace("'", "''")).Replace('__NOW__', [string]$NOW)
        $enc = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($worker))
        # Spawn via WMI (Win32_Process.Create, SW_HIDE): no console window, not our child, and no handle
        # inheritance. A ProcessStartInfo(UseShellExecute=$false) child inherits our stdout pipe, so Claude
        # Code would wait for the fetch to finish (measured: render blocked ~5s). CREATE_NO_WINDOW isn't an
        # accepted Win32_ProcessStartup CreateFlags value (the process silently never starts).
        try {
            $su = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ ShowWindow = [uint16]0 }
            [void](Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
                CommandLine = "powershell.exe -NoProfile -NonInteractive -WindowStyle Hidden -EncodedCommand $enc"
                ProcessStartupInformation = $su })
        } catch {}
    }
    if ($uRemote -and (Test-VerGt $uRemote $ccVersion)) {
        $updTxt = "  ${cAmber}$([char]0x2191) ${ccVersion} $([char]0x2192) ${uRemote}${R}"
    }
}

# --- Output ---
# Line 1: [account]  context [cold]  dir  model [effort] [fast]  [agent]  [vim]  [update]
$line1 = "${ctxText}  ${cSand}${dirDisplay}${R}  ${cPeach}${model}${R}"
if ($effort) { $line1 += " ${cDim}${effort}${R}" }
if ($fastMode) { $line1 += " ${cPeach}$([char]0x21AF)${R}" }
if ($accountLabel) { $line1 = "${accountColor}$([char]0x25C6) ${accountLabel}${R}  " + $line1 }
if ($agentName) { $line1 += "  ${cLav}$([char]0x2699) ${agentName}${R}" }
if ($vimMode) { $line1 += "  ${cDim}${vimMode}${R}" }
$line1 += $updTxt

# Line 2: git  limits
$line2Parts = @()
if ($gitDisplay) { $line2Parts += $gitDisplay }
$line2Parts += $limitParts
$line2 = $line2Parts -join "  "

[Console]::Out.Write($line1 + "`n" + $line2)
