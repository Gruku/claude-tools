#!/usr/bin/env bash
# check-version-bump.sh — PreToolUse hook for Bash commands.
# Only acts on git push commands. Blocks if any plugin under plugins/* has
# changes against the upstream branch but its plugin.json version was not
# bumped in the same range.
#
# Approval flow (shared with the rest of guard-hooks):
#   The AI calls AskUserQuestion with labels "Approve"/"Deny". On "Approve",
#   the PostToolUse hook on AskUserQuestion creates ~/.claude/guard-approve
#   automatically. The user can also type "approve" as a chat message
#   (UserPromptSubmit hook). Approval is valid for 60 seconds and is consumed
#   by consume-approval.sh after the tool actually runs.
#
# Exit 2 = block (stderr to model). Exit 0 = allow.
# Fail-open: any internal error falls through to allow — a broken guard hook
# must not block legitimate pushes.

# --- Only run on git push commands ---
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)

# Per-session approval token: keyed by harness session_id so concurrent
# Claude Code sessions on the same host don't trample each other's approvals.
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)
[ -z "$SESSION_ID" ] && SESSION_ID="default"
APPROVE_FILE="$HOME/.claude/guard-approve-$SESSION_ID"

if [ -z "$COMMAND" ]; then
  exit 0
fi
if ! echo "$COMMAND" | grep -qE 'git\s+.*push'; then
  exit 0
fi

# --- Resolve the working directory the push actually targets ---
# Claude often issues pushes from inside a worktree but targets the main
# checkout via `git -C <path> push`. We honor that:
#   1. If the command contains `git -C <path>` (single token, no quotes,
#      shell-substitution OK), use that path.
#   2. Else fall back to $CLAUDE_PROJECT_DIR.
TARGET_DIR=""
if echo "$COMMAND" | grep -qE 'git[[:space:]]+-C[[:space:]]'; then
  # Capture the first arg after `-C`. Tolerates `$VAR` substitutions —
  # we expand via env in the user's shell context. Tokens with quoted
  # spaces aren't supported here (rare for $REPO_ROOT-style usage).
  RAW_DIR=$(echo "$COMMAND" | sed -nE 's/.*git[[:space:]]+-C[[:space:]]+([^[:space:]]+).*/\1/p' | head -1)
  if [ -n "$RAW_DIR" ]; then
    # Try to expand env vars (e.g. $MAIN, ${REPO_ROOT}). If expansion
    # fails or yields a non-directory, fall back below.
    EXPANDED=$(eval echo "$RAW_DIR" 2>/dev/null)
    if [ -d "$EXPANDED" ]; then
      TARGET_DIR="$EXPANDED"
    fi
  fi
fi

if [ -z "$TARGET_DIR" ]; then
  TARGET_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
fi

# Drive both diff-walk and the upstream resolve from the SAME root, otherwise
# we ask one repo about another's branch and silent-skip on every push.
REPO_ROOT="$TARGET_DIR"

# Get the remote tracking branch (of whatever HEAD the target dir is on)
REMOTE_REF=$(git -C "$REPO_ROOT" rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null) || exit 0
REMOTE_SHA=$(git -C "$REPO_ROOT" rev-parse "$REMOTE_REF" 2>/dev/null) || exit 0

# --- Time-limited user approval (shared with guard-hooks) ---
check_approval() {
  if [ -f "$APPROVE_FILE" ]; then
    if [ "$(uname)" = "Linux" ] || [ "$(uname)" = "Darwin" ]; then
      FILE_AGE=$(( $(date +%s) - $(stat -c %Y "$APPROVE_FILE" 2>/dev/null || stat -f %m "$APPROVE_FILE" 2>/dev/null) ))
    else
      FILE_AGE=$(( $(date +%s) - $(stat -c %Y "$APPROVE_FILE" 2>/dev/null || echo 0) ))
    fi
    if [ "$FILE_AGE" -le 60 ] 2>/dev/null; then
      return 0
    fi
    rm -f "$APPROVE_FILE"
  fi
  return 1
}

# --- Walk plugins/* and find ones with code changes but no version bump ---
warnings=""
for plugin_dir in "$REPO_ROOT"/plugins/*/ ; do
  [ -d "$plugin_dir" ] || continue
  plugin_name="$(basename "$plugin_dir")"

  # Skip _archive and dotdirs
  case "$plugin_name" in _*|.*) continue ;; esac

  changed=$(git -C "$REPO_ROOT" diff --name-only "$REMOTE_SHA"..HEAD -- "plugins/$plugin_name/" 2>/dev/null)
  [ -z "$changed" ] && continue

  pjson="plugins/$plugin_name/.claude-plugin/plugin.json"
  version_changed=$(git -C "$REPO_ROOT" diff "$REMOTE_SHA"..HEAD -- "$pjson" 2>/dev/null | grep '"version"' || true)
  if [ -z "$version_changed" ]; then
    current_ver=$(grep '"version"' "$REPO_ROOT/$pjson" 2>/dev/null | head -1 | sed 's/.*"version".*"\(.*\)".*/\1/')
    file_count=$(echo "$changed" | wc -l | tr -d ' ')
    warnings="$warnings\n  - $plugin_name (v$current_ver) — $file_count files changed, version NOT bumped"
  fi
done

if [ -z "$warnings" ]; then
  exit 0
fi

# Honor a fresh user approval, same as the other guards.
if check_approval; then
  exit 0
fi

# Block with the AskUserQuestion-style instruction the other guards use, so
# the AI knows the actual approval ritual instead of guessing what "approve"
# means.
{
  printf '⛔ GUARD HOOK BLOCKED THIS COMMAND.\n'
  printf 'Reason: Plugin version bump check — the following plugins have changes but their version in plugin.json was not bumped:'
  printf '%b\n\n' "$warnings"
  printf 'Recommended: bump the version in each plugin'\''s .claude-plugin/plugin.json (and matching .claude-plugin/marketplace.json entry) before pushing.\n\n'
  printf 'If a bump is genuinely not appropriate, ACTION REQUIRED: use the AskUserQuestion tool with EXACTLY this shape:\n'
  printf '  question: one short sentence describing why the push should proceed without a version bump\n'
  printf '  options (use these labels verbatim — do not rename, translate, or add more):\n'
  printf '    - label: "Approve"  description: "Push without bumping versions"\n'
  printf '    - label: "Deny"     description: "Cancel; do not push"\n\n'
  printf 'After the user responds:\n'
  printf '  - "Approve" → rerun the ORIGINAL push command unchanged within 60 seconds\n'
  printf '  - "Deny" or no response → do NOT push\n\n'
  printf 'Only the exact label "Approve" is recognized as authorization.\n'
  printf 'Do NOT re-run automatically. Do NOT create the approval file yourself.\n'
} >&2
exit 2
