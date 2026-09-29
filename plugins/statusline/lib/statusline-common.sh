# shellcheck shell=bash
# User intent: one shared toolkit for install.sh / uninstall.sh (mirrors statusline-common.ps1) so
# both agree on where Claude's config lives (CLAUDE_CONFIG_DIR-aware), what "our" statusLine looks
# like, and how to rewrite user JSON safely (no BOM, CRLF kept, symlinks written through, abort on bad JSON).

claude_dir() {
    local d="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
    printf '%s' "${d%/}"
}

plugin_cache_dir() { printf '%s/plugins/cache/gruku-tools/statusline' "$1"; }

# True when at least one cached version dir actually contains the script.
plugin_installed() {
    local f
    for f in "$1"/*/"$2"; do
        [[ -f "$f" ]] && return 0
    done
    return 1
}

# Runtime launcher run by Claude Code on every refresh (statusLine.command does not expand
# ${CLAUDE_PLUGIN_ROOT}). Runs with the session's env, so CLAUDE_CONFIG_DIR selects the right
# plugin cache. Picks the highest version-named dir holding statusline.sh (sort -V), ignoring
# junk dirs; falls back to the newest such dir. `exec` hands Claude's stdin JSON straight through.
launcher_command() {
    # shellcheck disable=SC2016
    printf '%s' 'bash -c '"'"'c="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/plugins/cache/gruku-tools/statusline"; v=$(ls -1 "$c" 2>/dev/null | grep -E "^[0-9]+(\.[0-9]+)*$" | while read -r d; do [ -f "$c/$d/statusline.sh" ] && echo "$d"; done | sort -V | tail -1); [ -n "$v" ] || v=$(ls -1t "$c" 2>/dev/null | while read -r d; do [ -f "$c/$d/statusline.sh" ] && echo "$d"; done | head -1); if [ -n "$v" ]; then exec bash "$c/$v/statusline.sh"; fi; echo "statusline: gruku-tools plugin not found in $c"'"'"
}

# Shared "is this statusLine ours?" rule (mirrors Test-OurStatusLineCommand in the .ps1):
# the command names the gruku-tools/statusline cache path, in plain text or inside a
# UTF-16LE base64 -EncodedCommand payload.
is_ours_command() {
    local cmd=$1 path_re='gruku-tools[\/]+statusline' enc_re='-([Ee][Nn][Cc][Oo][Dd][Ee][Dd][Cc][Oo][Mm][Mm][Aa][Nn][Dd]|[Ee][Nn][Cc]|[Ee][Cc]|[Ee])[[:space:]]+([A-Za-z0-9+/=]+)' dec
    [[ -n "$cmd" ]] || return 1
    [[ "$cmd" =~ $path_re ]] && return 0
    [[ "$cmd" =~ $enc_re ]] || return 1
    dec=$(printf '%s' "${BASH_REMATCH[2]}" | base64 -d 2>/dev/null | tr -d '\000') || return 1
    [[ "$dec" =~ $path_re ]]
}

# Prints the file with any UTF-8 BOM stripped (jq rejects a BOM).
json_cat() { LC_ALL=C sed $'1s/^\xef\xbb\xbf//' "$1"; }

# Validates a JSON object file (missing or empty = ok). On failure prints why and returns 1.
json_check() {
    local path=$1
    [[ -f "$path" ]] || return 0
    [[ -n "$(tr -d '[:space:]' < "$path")" ]] || return 0
    if ! json_cat "$path" | jq -e 'type == "object"' >/dev/null 2>&1; then
        echo "ERROR: $path is not a valid JSON object. Fix or move it, then re-run. Nothing was changed." >&2
        return 1
    fi
}

# Runs `jq <filter> <args...>` against the file (missing/empty file = {}) and writes the
# result back in place: through a symlink (content replaced, link kept), CRLF kept if present.
json_update() {
    local path=$1; shift
    local tmp crlf=false fmt=() ind
    tmp=$(mktemp)
    if [[ -f "$path" && -n "$(tr -d '[:space:]' < "$path")" ]]; then
        # tr, not grep: MSYS grep strips CR before matching.
        [[ -n "$(tr -cd '\r' < "$path" | head -c1)" ]] && crlf=true
        # jq always re-serializes; mimic the file's layout (minified / tab / N-space indent)
        # so a jq-formatted file round-trips byte-identical outside the edited member.
        if [[ $(json_cat "$path" | tr -d '\r' | sed '/^[[:space:]]*$/d' | wc -l) -le 1 ]]; then
            fmt=(-c)
        else
            ind=$(json_cat "$path" | tr -d '\r' | grep -m1 -E '^[[:space:]]+"' | sed -E 's/^([[:space:]]*).*/\1/' || true)
            if [[ "$ind" == *$'\t'* ]]; then fmt=(--tab)
            elif (( ${#ind} >= 1 && ${#ind} <= 7 )); then fmt=(--indent "${#ind}")
            fi
        fi
        json_cat "$path" | jq ${fmt[@]+"${fmt[@]}"} "$@" > "$tmp"
    else
        jq -n '{}' | jq "$@" > "$tmp"
    fi
    mkdir -p "$(dirname "$path")"
    if $crlf; then
        tr -d '\r' < "$tmp" | awk '{ printf "%s\r\n", $0 }' > "$path"
    else
        tr -d '\r' < "$tmp" > "$path"
    fi
    rm -f "$tmp"
}

# Timestamped copy (never overwrites an earlier backup). Prints the backup path.
backup_file() {
    local path=$1 stamp bak n=1
    stamp=$(date +%Y%m%d-%H%M%S)
    bak="$path.bak-$stamp"
    while [[ -e "$bak" ]]; do bak="$path.bak-$stamp-$n"; n=$((n + 1)); done
    cp "$path" "$bak"
    printf '%s' "$bak"
}

ask_yn() {
    local question=$1 default=$2 hint resp
    if [[ "$default" == "y" ]]; then hint="[Y/n]"; else hint="[y/N]"; fi
    read -r -p "$question $hint " resp
    resp=${resp:-$default}
    [[ "$resp" =~ ^[Yy] ]]
}
