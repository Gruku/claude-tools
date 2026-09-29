#!/usr/bin/env bash
# Installer for the gruku-tools statusline (macOS / Linux).
#
# - Points <claude dir>/settings.json statusLine at a version-resolving launcher
# - Merges feature toggles into <claude dir>/statusline.config.json (other keys, e.g. `accounts`, kept)
#
# <claude dir> = $CLAUDE_CONFIG_DIR if set, else ~/.claude.
#
# Usage:
#   ./install.sh                                  # interactive
#   ./install.sh --no-git                         # disable git section
#   ./install.sh --no-update-check                # disable update banner
#   ./install.sh --no-limit-bars                  # hide 5h/7d rate-limit bars
#   ./install.sh --force                          # replace a statusLine that isn't ours
#   ./install.sh --non-interactive [flags]        # scripted, no prompts
#
# Exit codes: 0 ok / nothing to do, 1 error (plugin missing, invalid JSON), 2 bad arg,
# 3 refused (foreign statusLine).

set -euo pipefail

# shellcheck source=lib/statusline-common.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/statusline-common.sh"

CLAUDE_DIR=$(claude_dir)
CACHE_DIR=$(plugin_cache_dir "$CLAUDE_DIR")
CONFIG_PATH="$CLAUDE_DIR/statusline.config.json"
SETTINGS_PATH="$CLAUDE_DIR/settings.json"

NO_GIT=false
NO_UPDATE=false
NO_LIMIT_BARS=false
FORCE=false
NON_INTERACTIVE=false
for arg in "$@"; do
    case $arg in
        --no-git)            NO_GIT=true ;;
        --no-update-check)   NO_UPDATE=true ;;
        --no-limit-bars)     NO_LIMIT_BARS=true ;;
        --force)             FORCE=true ;;
        --non-interactive)   NON_INTERACTIVE=true ;;
        -h|--help)
            sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *) echo "unknown arg: $arg" >&2; exit 2 ;;
    esac
done

if ! plugin_installed "$CACHE_DIR" statusline.sh; then
    echo "ERROR: no statusline.sh found under $CACHE_DIR/<version>/" >&2
    echo "Run '/plugin install statusline@gruku-tools' in Claude Code first." >&2
    exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
    echo "ERROR: 'jq' is required (brew install jq / sudo apt install jq)." >&2
    exit 1
fi

# --- Validate everything first; abort before any write if a file is unreadable ---
json_check "$SETTINGS_PATH" || exit 1
json_check "$CONFIG_PATH" || exit 1

DESIRED=$(launcher_command)
EXISTING=""
if [[ -f "$SETTINGS_PATH" ]]; then
    EXISTING=$(json_cat "$SETTINGS_PATH" | jq -r 'if (.statusLine | type) == "object" then (.statusLine.command // "") else "" end' 2>/dev/null || true)
fi

# A statusLine that isn't ours is never replaced silently.
if [[ -n "$EXISTING" ]] && ! is_ours_command "$EXISTING" && ! $FORCE; then
    echo "settings.json already has a statusLine.command that isn't the gruku-tools one:"
    echo "  $EXISTING"
    if $NON_INTERACTIVE; then
        echo "Refusing to replace it. Re-run with --force to overwrite. Nothing was changed." >&2
        exit 3
    fi
    if ! ask_yn "Overwrite it with the gruku-tools launcher?" n; then
        echo "Kept the existing command. Nothing was changed."
        exit 0
    fi
fi

echo "Claude config dir: $CLAUDE_DIR"
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
    echo "  - Update check : banner when npm has a newer Claude Code"
    echo "                   (version comes from the session; npm is queried in the background)"
    echo "  - Limit bars   : 5h / 7d rate-limit bars on line 2"
    echo
    SHOW_GIT=false; SHOW_UPDATE=false; SHOW_LIMIT_BARS=false
    $NO_GIT        || { ask_yn "Enable git info?"      y && SHOW_GIT=true; } || true
    $NO_UPDATE     || { ask_yn "Enable update check?"  y && SHOW_UPDATE=true; } || true
    $NO_LIMIT_BARS || { ask_yn "Show rate-limit bars?" y && SHOW_LIMIT_BARS=true; } || true
    echo
fi

# --- Toggle config: merge, keep every other key (accounts, ...) ---
TOGGLES_CURRENT=false
if [[ -f "$CONFIG_PATH" ]]; then
    TOGGLES_CURRENT=$(json_cat "$CONFIG_PATH" | jq --argjson g "$SHOW_GIT" --argjson u "$SHOW_UPDATE" --argjson b "$SHOW_LIMIT_BARS" \
        '(. // {}) | .showGit == $g and .showUpdateCheck == $u and .showLimitBars == $b' 2>/dev/null || echo false)
fi
if [[ "$TOGGLES_CURRENT" == "true" ]]; then
    echo "$CONFIG_PATH already up to date"
else
    json_update "$CONFIG_PATH" --argjson g "$SHOW_GIT" --argjson u "$SHOW_UPDATE" --argjson b "$SHOW_LIMIT_BARS" \
        '.showGit = $g | .showUpdateCheck = $u | .showLimitBars = $b'
    echo "Updated $CONFIG_PATH"
fi
echo "  showGit         = $SHOW_GIT"
echo "  showUpdateCheck = $SHOW_UPDATE"
echo "  showLimitBars   = $SHOW_LIMIT_BARS"

# --- settings.json statusLine ---
CURRENT_TYPE=""
[[ -f "$SETTINGS_PATH" ]] && CURRENT_TYPE=$(json_cat "$SETTINGS_PATH" | jq -r '.statusLine.type? // ""' 2>/dev/null || true)
if [[ "$EXISTING" == "$DESIRED" && "$CURRENT_TYPE" == "command" ]]; then
    echo "statusLine in $SETTINGS_PATH already current"
else
    if [[ -f "$SETTINGS_PATH" ]]; then
        echo "Backed up $SETTINGS_PATH -> $(backup_file "$SETTINGS_PATH")"
    fi
    json_update "$SETTINGS_PATH" --arg cmd "$DESIRED" '.statusLine = {type: "command", command: $cmd}'
    echo "Wrote statusLine entry to $SETTINGS_PATH"
fi

echo
echo "Restart Claude Code for changes to take effect."
