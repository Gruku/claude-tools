#!/usr/bin/env bash
# SessionStart hook for shader-nodes plugin

set -euo pipefail

# Determine plugin root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Read load-shader-nodes content
skill_content=$(cat "${PLUGIN_ROOT}/skills/load-shader-nodes/SKILL.md" 2>&1 || echo "Error reading load-shader-nodes skill")

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
    "additionalContext": "You have the Shader Nodes plugin available.\n\n**Below is the full content of your 'shader-nodes:load-shader-nodes' skill. For all other skills, use the 'Skill' tool:**\n\n${skill_escaped}"
  }
}
EOF

exit 0
