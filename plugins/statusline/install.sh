#!/usr/bin/env bash
# Interactive installer for the gruku-tools statusline (macOS / Linux).
#
# - Wires ~/.claude/settings.json -> the version-resolver command
# - Writes ~/.claude/statusline.config.json with feature toggles
#
# Usage:
#   ./install.sh                                                              # interactive
#   ./install.sh --no-git                                                     # disable git section
#   ./install.sh --no-update-check                                            # disable update banner
#   ./install.sh --no-limit-bars                                              # hide 5h/7d rate-limit bars
#   ./install.sh --no-git --no-update-check --no-limit-bars --non-interactive # scripted

set -euo pipefail

CACHE_DIR="$HOME/.claude/plugins/cache/gruku-tools/statusline"
CONFIG_PATH="$HOME/.claude/statusline.config.json"
SETTINGS_PATH="$HOME/.claude/settings.json"

NO_GIT=false
NO_UPDATE=false
NO_LIMIT_BARS=false
NON_INTERACTIVE=false
for arg in "$@"; do
    case $arg in
        --no-git)            NO_GIT=true ;;
        --no-update-check)   NO_UPDATE=true ;;
        --no-limit-bars)     NO_LIMIT_BARS=true ;;
        --non-interactive)   NON_INTERACTIVE=true ;;
        -h|--help)
            sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *) echo "unknown arg: $arg" >&2; exit 2 ;;
    esac
done

if [[ ! -d "$CACHE_DIR" ]]; then
    echo "ERROR: statusline plugin not found at $CACHE_DIR" >&2
    echo "Run '/plugin install statusline@gruku-tools' in Claude Code first." >&2
    exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
    echo "ERROR: 'jq' is required (brew install jq / sudo apt install jq)." >&2
    exit 1
fi

ask_yn() {
    local question=$1 default=$2 hint resp
    if [[ "$default" == "y" ]]; then hint="[Y/n]"; else hint="[y/N]"; fi
    read -r -p "$question $hint " resp
    resp=${resp:-$default}
    [[ "$resp" =~ ^[Yy] ]]
}

if $NON_INTERACTIVE; then
    if $NO_GIT;        then SHOW_GIT=false;        else SHOW_GIT=true;        fi
    if $NO_UPDATE;     then SHOW_UPDATE=false;     else SHOW_UPDATE=true;     fi
    if $NO_LIMIT_BARS; then SHOW_LIMIT_BARS=false; else SHOW_LIMIT_BARS=true; fi
else
    echo
    echo "gruku-tools statusline -- installer"
    echo "==================================="
    echo
    echo "Optional features can be disabled if you see flashing console"
    echo "windows, hangs, or you just don't want them:"
    echo
    echo "  - Git info     : branch + dirty markers (runs 'git' per refresh,"
    echo "                   may flash if a credential helper is misconfigured)"
    echo "  - Update check : checks npm for a new Claude Code version"
    echo "                   (runs 'claude --version' once per session/hour)"
    echo "  - Limit bars   : 5h / 7d rate-limit bars on line 2"
    echo
    if ask_yn "Enable git info?"      y; then SHOW_GIT=true;        else SHOW_GIT=false;        fi
    if ask_yn "Enable update check?"  y; then SHOW_UPDATE=true;     else SHOW_UPDATE=false;     fi
    if ask_yn "Show rate-limit bars?" y; then SHOW_LIMIT_BARS=true; else SHOW_LIMIT_BARS=false; fi
    echo
fi

mkdir -p "$(dirname "$CONFIG_PATH")"
jq -n --argjson g "$SHOW_GIT" --argjson u "$SHOW_UPDATE" --argjson b "$SHOW_LIMIT_BARS" \
    '{showGit: $g, showUpdateCheck: $u, showLimitBars: $b}' > "$CONFIG_PATH"

echo "Wrote $CONFIG_PATH"
echo "  showGit         = $SHOW_GIT"
echo "  showUpdateCheck = $SHOW_UPDATE"
echo "  showLimitBars   = $SHOW_LIMIT_BARS"

DESIRED='bash -c '"'"'latest=$(ls -1 "$HOME/.claude/plugins/cache/gruku-tools/statusline" | sort -V | tail -1); exec bash "$HOME/.claude/plugins/cache/gruku-tools/statusline/$latest/statusline.sh"'"'"''

mkdir -p "$(dirname "$SETTINGS_PATH")"
[[ -f "$SETTINGS_PATH" ]] || echo '{}' > "$SETTINGS_PATH"

if ! jq empty "$SETTINGS_PATH" 2>/dev/null; then
    echo "WARN: $SETTINGS_PATH is not valid JSON. Backing up to $SETTINGS_PATH.bak" >&2
    cp "$SETTINGS_PATH" "$SETTINGS_PATH.bak"
    echo '{}' > "$SETTINGS_PATH"
fi

EXISTING=$(jq -r '.statusLine.command // ""' "$SETTINGS_PATH")
if [[ -n "$EXISTING" && "$EXISTING" != "$DESIRED" ]] && ! $NON_INTERACTIVE; then
    echo
    echo "settings.json already has a different statusLine.command:"
    echo "  $EXISTING"
    if ! ask_yn "Overwrite with the gruku-tools resolver?" y; then
        echo "Kept existing command. Toggle config was still written."
        exit 0
    fi
fi

tmp=$(mktemp)
jq --arg cmd "$DESIRED" '.statusLine = {type: "command", command: $cmd}' "$SETTINGS_PATH" > "$tmp"
mv "$tmp" "$SETTINGS_PATH"

echo "Wrote statusLine entry to $SETTINGS_PATH"
echo
echo "Restart Claude Code for changes to take effect."
