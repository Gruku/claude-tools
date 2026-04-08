#!/usr/bin/env bash
# SessionStart hook for reality-reprojection plugin

set -euo pipefail

# Determine plugin root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Read using-reality-reprojection content
skill_content=$(cat "${PLUGIN_ROOT}/skills/using-reality-reprojection/SKILL.md" 2>&1 || echo "Error reading using-reality-reprojection skill")

# Escape string for JSON embedding
escape_for_json() {
    local s="$1"
    s="${s//\\/\\\\}"
    s="${s//\"/\\\"}"
    s="${s//$'\n'/\\n}"
    s="${s//$'\r'/\\r}"
    s="${s//$'\t'/\\t}"
    printf '%s' "$s"
}

skill_escaped=$(escape_for_json "$skill_content")

# Output context injection as JSON
cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "You have the Reality Reprojection design system available.\n\n**Below is the full content of your 'reality-reprojection:using-reality-reprojection' skill. For all other skills, use the 'Skill' tool:**\n\n${skill_escaped}"
  }
}
EOF

exit 0
