# User intent: one shared toolkit for install.ps1 / uninstall.ps1 so both agree on where Claude's
# config lives (CLAUDE_CONFIG_DIR-aware), what "our" statusLine looks like, and how to rewrite
# user JSON safely (UTF-8 no BOM, newline style kept, symlinks written through, never clobber on bad JSON).

# Claude config root for the session this installer targets. Env-var based (not
# GetFolderPath) so it follows CLAUDE_CONFIG_DIR and is testable against scratch dirs.
function Get-ClaudeDir {
    if ($env:CLAUDE_CONFIG_DIR) { return $env:CLAUDE_CONFIG_DIR.TrimEnd('\', '/') }
    $homeDir = if ($env:USERPROFILE) { $env:USERPROFILE } else { $env:HOME }
    return (Join-Path $homeDir '.claude')
}

function Get-PluginCacheDir([string]$claudeDir) {
    return (Join-Path $claudeDir 'plugins\cache\gruku-tools\statusline')
}

# True when at least one cached version dir actually contains the script.
function Test-PluginInstalled([string]$cacheDir, [string]$scriptName) {
    if (-not (Test-Path -LiteralPath $cacheDir -PathType Container)) { return $false }
    $hit = Get-ChildItem -LiteralPath $cacheDir -Directory -ErrorAction SilentlyContinue |
        Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName $scriptName) -PathType Leaf } |
        Select-Object -First 1
    return [bool]$hit
}

# Runtime launcher run by Claude Code on every refresh (via -EncodedCommand, because
# statusLine.command does not expand ${CLAUDE_PLUGIN_ROOT}). It runs with the session's
# env, so CLAUDE_CONFIG_DIR picks the right plugin cache per account. Picks the highest
# [version]-named dir that contains statusline.ps1, ignoring junk dirs; falls back to the
# newest such dir if none parse as a version. Keep in sync with SKILL.md / references.
$script:LauncherSource = @'
$ProgressPreference = 'SilentlyContinue'
$r = if ($env:CLAUDE_CONFIG_DIR) { $env:CLAUDE_CONFIG_DIR } else { Join-Path $env:USERPROFILE '.claude' }
$c = Join-Path $r 'plugins\cache\gruku-tools\statusline'
$d = @(Get-ChildItem -LiteralPath $c -Directory -ErrorAction SilentlyContinue | Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'statusline.ps1') })
$p = $d | Where-Object { $_.Name -as [version] } | Sort-Object { $_.Name -as [version] } -Descending | Select-Object -First 1
if (-not $p) { $p = $d | Sort-Object LastWriteTime -Descending | Select-Object -First 1 }
if ($p) { & (Join-Path $p.FullName 'statusline.ps1') } else { 'statusline: gruku-tools plugin not found in ' + $c }
'@

function Get-LauncherSource { return ($script:LauncherSource -replace "`r`n", "`n").Trim() }

function Get-LauncherCommand {
    $b64 = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes((Get-LauncherSource)))
    return "powershell.exe -NoProfile -ExecutionPolicy Bypass -EncodedCommand $b64"
}

# Shared "is this statusLine ours?" rule (mirrored in statusline-common.sh):
# the command names the gruku-tools/statusline cache path, either in plain text or
# inside a UTF-16LE base64 -EncodedCommand payload (covers every launcher we ever wrote).
function Test-OurStatusLineCommand([string]$cmd) {
    if (-not $cmd) { return $false }
    $pathRe = 'gruku-tools[\\/]+statusline'
    if ($cmd -match $pathRe) { return $true }
    if ($cmd -match '(?i)-(?:EncodedCommand|enc|ec|e)\s+([A-Za-z0-9+/=]+)') {
        try {
            $decoded = [Text.Encoding]::Unicode.GetString([Convert]::FromBase64String($Matches[1]))
            return ($decoded -match $pathRe)
        } catch { return $false }
    }
    return $false
}

$script:Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

# Reads a JSON object file. Returns @{ Exists; Text; Object; Newline; TrailingNewline }.
# Throws with a clear message if the file exists but is not a JSON object.
function Read-JsonObjectFile([string]$path) {
    $info = @{ Exists = $false; Text = ''; Object = [pscustomobject]@{}; Newline = "`n"; TrailingNewline = $true }
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { return $info }
    $info.Exists = $true
    # ReadAllText(UTF8) strips a BOM if present and decodes non-ASCII correctly on PS 5.1.
    $text = [IO.File]::ReadAllText($path, [Text.Encoding]::UTF8)
    $info.Text = $text
    if ($text.Contains("`r`n")) { $info.Newline = "`r`n" }
    $info.TrailingNewline = ($text.Length -eq 0) -or $text.EndsWith("`n")
    if ($text.Trim().Length -eq 0) { return $info }
    try {
        $obj = $text | ConvertFrom-Json -ErrorAction Stop
    } catch {
        throw "$path is not valid JSON ($($_.Exception.Message.Split("`n")[0].Trim())). Fix or move it, then re-run. Nothing was changed."
    }
    if ($obj -isnot [System.Management.Automation.PSCustomObject]) {
        throw "$path does not contain a JSON object. Fix or move it, then re-run. Nothing was changed."
    }
    $info.Object = $obj
    return $info
}

# --- Minimal-diff JSON editing -------------------------------------------------------
# ConvertTo-Json (esp. PS 5.1) reformats the whole document, so edits are applied to the
# original text instead: only the targeted top-level member changes, every other byte stays.

function Skip-JsonString([string]$t, [int]$i) {
    $j = $i + 1
    while ($j -lt $t.Length) {
        $c = $t[$j]
        if ($c -eq '\') { $j += 2; continue }
        if ($c -eq '"') { return $j + 1 }
        $j++
    }
    throw 'unterminated JSON string'
}

function Skip-JsonWs([string]$t, [int]$i) {
    while ($i -lt $t.Length -and [char]::IsWhiteSpace($t[$i])) { $i++ }
    return $i
}

function Skip-JsonValue([string]$t, [int]$i) {
    $c = $t[$i]
    if ($c -eq '"') { return (Skip-JsonString $t $i) }
    if ($c -eq '{' -or $c -eq '[') {
        $depth = 0
        while ($i -lt $t.Length) {
            $c = $t[$i]
            if ($c -eq '"') { $i = Skip-JsonString $t $i; continue }
            if ($c -eq '{' -or $c -eq '[') { $depth++ }
            elseif ($c -eq '}' -or $c -eq ']') { $depth--; if ($depth -eq 0) { return $i + 1 } }
            $i++
        }
        throw 'unterminated JSON container'
    }
    while ($i -lt $t.Length -and (',}]').IndexOf($t[$i]) -lt 0 -and -not [char]::IsWhiteSpace($t[$i])) { $i++ }
    return $i
}

# Locates the top-level members: @{ Open; Close; Members = @(@{ Key; KeyStart; KeyEnd; ValueStart; ValueEnd }) }.
function Get-JsonTopMembers([string]$t) {
    $i = Skip-JsonWs $t 0
    if ($i -ge $t.Length -or $t[$i] -ne '{') { throw 'top-level JSON value is not an object' }
    $res = @{ Open = $i; Close = -1; Members = New-Object System.Collections.ArrayList }
    $i++
    while ($true) {
        $i = Skip-JsonWs $t $i
        if ($i -ge $t.Length) { throw 'unterminated JSON object' }
        $c = $t[$i]
        if ($c -eq '}') { $res.Close = $i; break }
        if ($c -eq ',') { $i++; continue }
        if ($c -ne '"') { throw "unexpected '$c' at offset $i" }
        $ks = $i; $ke = Skip-JsonString $t $i
        $i = Skip-JsonWs $t $ke
        if ($t[$i] -ne ':') { throw "expected ':' at offset $i" }
        $vs = Skip-JsonWs $t ($i + 1)
        $ve = Skip-JsonValue $t $vs
        $null = $res.Members.Add(@{ Key = $t.Substring($ks + 1, $ke - $ks - 2); KeyStart = $ks; KeyEnd = $ke; ValueStart = $vs; ValueEnd = $ve })
        $i = $ve
    }
    return $res
}

function ConvertTo-JsonStringLiteral([string]$s) {
    $sb = New-Object System.Text.StringBuilder
    $null = $sb.Append('"')
    foreach ($ch in $s.ToCharArray()) {
        switch ($ch) {
            '"'  { $null = $sb.Append('\"') }
            '\'  { $null = $sb.Append('\\') }
            "`n" { $null = $sb.Append('\n') }
            "`r" { $null = $sb.Append('\r') }
            "`t" { $null = $sb.Append('\t') }
            default {
                if ([int]$ch -lt 0x20) { $null = $sb.Append(('\u{0:x4}' -f [int]$ch)) } else { $null = $sb.Append($ch) }
            }
        }
    }
    $null = $sb.Append('"')
    return $sb.ToString()
}

# Serializes bool / string / ordered-dictionary values. $indent = indent of the member line.
function Format-JsonValue($v, [string]$indent, [string]$unit, [string]$nl, [bool]$pretty, [string]$sep) {
    if ($v -is [bool]) { if ($v) { return 'true' } else { return 'false' } }
    if ($v -is [string]) { return (ConvertTo-JsonStringLiteral $v) }
    if ($v -is [System.Collections.IDictionary]) {
        $parts = foreach ($k in $v.Keys) {
            $inner = Format-JsonValue $v[$k] ($indent + $unit) $unit $nl $pretty $sep
            if ($pretty) { $indent + $unit + (ConvertTo-JsonStringLiteral $k) + $sep + $inner }
            else { (ConvertTo-JsonStringLiteral $k) + $sep + $inner }
        }
        if ($pretty) { return '{' + $nl + ($parts -join (',' + $nl)) + $nl + $indent + '}' }
        return '{' + ($parts -join ',') + '}'
    }
    throw "unsupported value type $($v.GetType().FullName)"
}

function Get-JsonLayout([string]$t, $info) {
    $nl = if ($t.Contains("`r`n")) { "`r`n" } else { "`n" }
    $layout = @{ Newline = $nl; Pretty = $true; Unit = '  '; Sep = ': ' }
    if ($info.Members.Count -gt 0) {
        $m = $info.Members[0]
        $between = $t.Substring($info.Open + 1, $m.KeyStart - $info.Open - 1)
        $lastNl = $between.LastIndexOf("`n")
        if ($lastNl -ge 0) { $layout.Unit = $between.Substring($lastNl + 1) } else { $layout.Pretty = $false }
        $layout.Sep = $t.Substring($m.KeyEnd, $m.ValueStart - $m.KeyEnd)
    }
    return $layout
}

# Sets top-level $key to $value, touching only that member's text (or appending it).
function Set-JsonTopMember([string]$t, [string]$key, $value) {
    if ($t.Trim().Length -eq 0) { $t = '{}' + "`n" }
    $info = Get-JsonTopMembers $t
    $L = Get-JsonLayout $t $info
    $existing = $info.Members | Where-Object { $_.Key -ceq $key } | Select-Object -First 1
    if ($existing) {
        $lineStart = $t.LastIndexOf("`n", $existing.KeyStart) + 1
        $indent = if ($L.Pretty) { $t.Substring($lineStart, $existing.KeyStart - $lineStart) } else { '' }
        $vt = Format-JsonValue $value $indent $L.Unit $L.Newline $L.Pretty $L.Sep
        return $t.Substring(0, $existing.ValueStart) + $vt + $t.Substring($existing.ValueEnd)
    }
    $indent = if ($L.Pretty) { $L.Unit } else { '' }
    $member = (ConvertTo-JsonStringLiteral $key) + $L.Sep + (Format-JsonValue $value $indent $L.Unit $L.Newline $L.Pretty $L.Sep)
    if ($info.Members.Count -eq 0) {
        $ins = $L.Newline + $L.Unit + $member + $L.Newline
        return $t.Substring(0, $info.Open + 1) + $ins + $t.Substring($info.Close)
    }
    $last = $info.Members[$info.Members.Count - 1]
    $ins = if ($L.Pretty) { ',' + $L.Newline + $L.Unit + $member } else { ',' + $member }
    return $t.Substring(0, $last.ValueEnd) + $ins + $t.Substring($last.ValueEnd)
}

# Removes every top-level $key member (with its separating comma), nothing else.
function Remove-JsonTopMember([string]$t, [string]$key) {
    while ($true) {
        $info = Get-JsonTopMembers $t
        $idx = -1
        for ($k = 0; $k -lt $info.Members.Count; $k++) { if ($info.Members[$k].Key -ceq $key) { $idx = $k; break } }
        if ($idx -lt 0) { return $t }
        $m = $info.Members[$idx]
        if ($info.Members.Count -eq 1) {
            $t = $t.Substring(0, $info.Open + 1) + $t.Substring($m.ValueEnd)
        } elseif ($idx -lt $info.Members.Count - 1) {
            $t = $t.Substring(0, $m.KeyStart) + $t.Substring($info.Members[$idx + 1].KeyStart)
        } else {
            $t = $t.Substring(0, $info.Members[$idx - 1].ValueEnd) + $t.Substring($m.ValueEnd)
        }
    }
}

# Parses edited text back; throws (so nothing is written) if the edit produced bad JSON.
function Assert-JsonObjectText([string]$t, [string]$path) {
    try { $o = $t | ConvertFrom-Json -ErrorAction Stop } catch { $o = $null }
    if ($o -isnot [System.Management.Automation.PSCustomObject]) {
        throw "internal error: edited $path would not be a valid JSON object. Nothing was changed."
    }
    return $o
}

# Writes UTF-8 without BOM. WriteAllText opens the path itself, so a symlinked file is
# written through to its target instead of being replaced by a regular file.
function Write-TextFile([string]$path, [string]$text) {
    $dir = Split-Path -Parent $path
    if ($dir -and -not (Test-Path -LiteralPath $dir)) { $null = New-Item -ItemType Directory -Force -Path $dir }
    [IO.File]::WriteAllText($path, $text, $script:Utf8NoBom)
}

# Timestamped copy (never overwrites an earlier backup). Returns the backup path.
function Backup-File([string]$path) {
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $bak = "$path.bak-$stamp"
    $n = 1
    while (Test-Path -LiteralPath $bak) { $bak = "$path.bak-$stamp-$n"; $n++ }
    [IO.File]::Copy($path, $bak)
    return $bak
}

function Read-YesNo([string]$question, [bool]$default) {
    $hint = if ($default) { '[Y/n]' } else { '[y/N]' }
    $resp = Read-Host "$question $hint"
    if (-not $resp) { return $default }
    return ($resp -match '^\s*[Yy]')
}

$script:ToggleKeys = @('showGit', 'showUpdateCheck', 'showLimitBars')
