#!/usr/bin/env bash
# Uninstaller for the gruku-tools statusline (macOS / Linux).
#
# - Removes `statusLine` from <claude dir>/settings.json, only if it is the gruku-tools
#   launcher (a custom command is left alone unless --force)
# - Removes the toggle keys (showGit/showUpdateCheck/showLimitBars) from
#   <claude dir>/statusline.config.json unless --keep-config; other keys (e.g. `accounts`)
#   are kept, and the file is deleted only if nothing else is left in it
#
# <claude dir> = $CLAUDE_CONFIG_DIR if set, else ~/.claude.
#
# Usage:
#   ./uninstall.sh                       # interactive
#   ./uninstall.sh --keep-config         # leave statusline.config.json untouched
#   ./uninstall.sh --force               # remove statusLine even if it isn't ours
#   ./uninstall.sh --non-interactive     # no prompts
#
# Exit codes: 0 ok / nothing to do, 1 error (invalid JSON), 2 bad arg, 3 refused (foreign statusLine).

set -euo pipefail

# shellcheck source=lib/statusline-common.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/statusline-common.sh"

CLAUDE_DIR=$(claude_dir)
CONFIG_PATH="$CLAUDE_DIR/statusline.config.json"
SETTINGS_PATH="$CLAUDE_DIR/settings.json"

KEEP_CONFIG=false
FORCE=false
NON_INTERACTIVE=false
for arg in "$@"; do
    case $arg in
        --keep-config)      KEEP_CONFIG=true ;;
        --force)            FORCE=true ;;
        --non-interactive)  NON_INTERACTIVE=true ;;
        -h|--help)
            sed -n '2,19p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *) echo "unknown arg: $arg" >&2; exit 2 ;;
    esac
done

if ! command -v jq >/dev/null 2>&1; then
    echo "ERROR: 'jq' is required (brew install jq / sudo apt install jq)." >&2
    exit 1
fi

echo
echo "gruku-tools statusline -- uninstaller"
echo "====================================="
echo "Claude config dir: $CLAUDE_DIR"
echo

json_check "$SETTINGS_PATH" || exit 1
$KEEP_CONFIG || json_check "$CONFIG_PATH" || exit 1

# --- Remove statusLine from settings.json ---
if [[ ! -f "$SETTINGS_PATH" ]]; then
    echo "No $SETTINGS_PATH found -- nothing to remove."
elif [[ "$(json_cat "$SETTINGS_PATH" | jq '(. // {}) | has("statusLine")')" != "true" ]]; then
    echo "No statusLine entry in $SETTINGS_PATH -- nothing to remove."
else
    EXISTING=$(json_cat "$SETTINGS_PATH" | jq -r 'if (.statusLine | type) == "object" then (.statusLine.command // "") else "" end')
    REMOVE=false
    if $FORCE || is_ours_command "$EXISTING"; then
        REMOVE=true
    else
        echo "settings.json has a statusLine.command that isn't the gruku-tools one:"
        echo "  $EXISTING"
        if $NON_INTERACTIVE; then
            echo "Refusing to remove it. Re-run with --force to remove anyway. Nothing was changed." >&2
            exit 3
        fi
        if ask_yn "Remove it anyway?" n; then REMOVE=true; fi
    fi

    if $REMOVE; then
        echo "Backed up $SETTINGS_PATH -> $(backup_file "$SETTINGS_PATH")"
        json_update "$SETTINGS_PATH" 'del(.statusLine)'
        echo "Removed statusLine from $SETTINGS_PATH"
    else
        echo "Left statusLine in $SETTINGS_PATH untouched."
    fi
fi

# --- Toggle config: drop our keys, keep the rest ---
if ! $KEEP_CONFIG && [[ -f "$CONFIG_PATH" ]]; then
    CLEAN=true
    if ! $NON_INTERACTIVE; then
        if ask_yn "Remove the statusline toggles from $CONFIG_PATH too?" y; then CLEAN=true; else CLEAN=false; fi
    fi
    if $CLEAN; then
        json_update "$CONFIG_PATH" '(. // {}) | del(.showGit, .showUpdateCheck, .showLimitBars)'
        if [[ ! -L "$CONFIG_PATH" && "$(json_cat "$CONFIG_PATH" | jq 'length')" == "0" ]]; then
            rm -f "$CONFIG_PATH"
            echo "Deleted $CONFIG_PATH"
        else
            echo "Removed toggle keys from $CONFIG_PATH (other keys kept)"
        fi
    else
        echo "Kept $CONFIG_PATH"
    fi
fi

echo
echo "Restart Claude Code for changes to take effect."
echo "The plugin itself is untouched -- run '/plugin uninstall statusline@gruku-tools' to remove it."
