#!/usr/bin/env bash
# SessionStart hook for ue5-materials plugin

set -euo pipefail

# Determine plugin root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Read using-ue5-materials content
skill_content=$(cat "${PLUGIN_ROOT}/skills/using-ue5-materials/SKILL.md" 2>&1 || echo "Error reading using-ue5-materials skill")

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
    "additionalContext": "You have the UE5 Materials plugin available.\n\n**Below is the full content of your 'ue5-materials:using-ue5-materials' skill. For all other skills, use the 'Skill' tool:**\n\n${skill_escaped}"
  }
}
EOF

exit 0
