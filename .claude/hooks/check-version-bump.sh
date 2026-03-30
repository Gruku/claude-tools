#!/usr/bin/env bash
# check-version-bump.sh — PreToolUse hook for git push
# Checks if any plugin files changed since remote HEAD without a version bump.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# Get the remote tracking branch
REMOTE_REF=$(git -C "$REPO_ROOT" rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null) || {
  # No upstream set — skip check
  exit 0
}
REMOTE_SHA=$(git -C "$REPO_ROOT" rev-parse "$REMOTE_REF" 2>/dev/null) || exit 0

# Find all plugin directories that have changes since the remote
warnings=""
for plugin_json in "$REPO_ROOT"/plugins/*/. ; do
  plugin_dir="$(dirname "$plugin_json")"
  plugin_name="$(basename "$plugin_dir")"

  # Skip _archive
  [[ "$plugin_name" == _* ]] && continue

  # Check if any files in this plugin changed
  changed=$(git -C "$REPO_ROOT" diff --name-only "$REMOTE_SHA"..HEAD -- "plugins/$plugin_name/" 2>/dev/null)
  [ -z "$changed" ] && continue

  # Check if plugin.json version was bumped
  pjson="plugins/$plugin_name/.claude-plugin/plugin.json"
  version_changed=$(git -C "$REPO_ROOT" diff "$REMOTE_SHA"..HEAD -- "$pjson" 2>/dev/null | grep '"version"' || true)
  if [ -z "$version_changed" ]; then
    current_ver=$(grep '"version"' "$REPO_ROOT/$pjson" 2>/dev/null | head -1 | sed 's/.*"version".*"\(.*\)".*/\1/')
    file_count=$(echo "$changed" | wc -l | tr -d ' ')
    warnings="$warnings\n  - $plugin_name (v$current_ver) — $file_count files changed, version NOT bumped"
  fi
done

if [ -n "$warnings" ]; then
  cat <<EOF
{
  "decision": "block",
  "reason": "Plugin version bump check: The following plugins have changes but their version in plugin.json was not bumped:\\n$warnings\\n\\nBump the version in each plugin's .claude-plugin/plugin.json before pushing. Use 'approve' to push anyway."
}
EOF
  exit 0
fi

# All good — no output needed
exit 0
