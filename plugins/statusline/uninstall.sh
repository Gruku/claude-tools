#!/usr/bin/env bash
# Uninstaller for the gruku-tools statusline (macOS / Linux).
#
# - Removes the `statusLine` key from ~/.claude/settings.json (only if it
#   points at the gruku-tools resolver — leaves a custom command alone)
# - Optionally deletes ~/.claude/statusline.config.json
#
# Usage:
#   ./uninstall.sh                       # interactive
#   ./uninstall.sh --keep-config         # leave statusline.config.json in place
#   ./uninstall.sh --force               # remove statusLine even if it isn't ours
#   ./uninstall.sh --non-interactive     # no prompts; default = remove config

set -euo pipefail

CONFIG_PATH="$HOME/.claude/statusline.config.json"
SETTINGS_PATH="$HOME/.claude/settings.json"

KEEP_CONFIG=false
FORCE=false
NON_INTERACTIVE=false
for arg in "$@"; do
    case $arg in
        --keep-config)      KEEP_CONFIG=true ;;
        --force)            FORCE=true ;;
        --non-interactive)  NON_INTERACTIVE=true ;;
        -h|--help)
            sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *) echo "unknown arg: $arg" >&2; exit 2 ;;
    esac
done

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

echo
echo "gruku-tools statusline -- uninstaller"
echo "====================================="
echo

# --- Remove statusLine from settings.json ---
if [[ -f "$SETTINGS_PATH" ]]; then
    if ! jq empty "$SETTINGS_PATH" 2>/dev/null; then
        echo "WARN: $SETTINGS_PATH is not valid JSON. Backing up to $SETTINGS_PATH.bak" >&2
        cp "$SETTINGS_PATH" "$SETTINGS_PATH.bak"
    elif jq -e '.statusLine' "$SETTINGS_PATH" >/dev/null 2>&1; then
        EXISTING=$(jq -r '.statusLine.command // ""' "$SETTINGS_PATH")
        IS_OURS=false
        [[ "$EXISTING" == *gruku-tools/statusline* || "$EXISTING" == *"gruku-tools\\statusline"* ]] && IS_OURS=true

        REMOVE=false
        if $IS_OURS || $FORCE; then
            REMOVE=true
        elif ! $NON_INTERACTIVE; then
            echo "settings.json has a statusLine.command that doesn't look like ours:"
            echo "  $EXISTING"
            if ask_yn "Remove anyway?" n; then REMOVE=true; fi
        fi

        if $REMOVE; then
            tmp=$(mktemp)
            jq 'del(.statusLine)' "$SETTINGS_PATH" > "$tmp"
            mv "$tmp" "$SETTINGS_PATH"
            echo "Removed statusLine from $SETTINGS_PATH"
        else
            echo "Left statusLine in $SETTINGS_PATH untouched."
        fi
    else
        echo "No statusLine entry in $SETTINGS_PATH -- nothing to remove."
    fi
else
    echo "No $SETTINGS_PATH found -- nothing to remove."
fi

# --- Optionally delete the toggle config ---
if [[ -f "$CONFIG_PATH" ]]; then
    DELETE_CONFIG=true
    $KEEP_CONFIG && DELETE_CONFIG=false
    if ! $NON_INTERACTIVE && ! $KEEP_CONFIG; then
        if ask_yn "Delete $CONFIG_PATH too?" y; then DELETE_CONFIG=true; else DELETE_CONFIG=false; fi
    fi
    if $DELETE_CONFIG; then
        rm -f "$CONFIG_PATH"
        echo "Deleted $CONFIG_PATH"
    else
        echo "Kept $CONFIG_PATH"
    fi
fi

echo
echo "Restart Claude Code for changes to take effect."
echo "The plugin itself is untouched -- run '/plugin uninstall statusline@gruku-tools' to remove it."
