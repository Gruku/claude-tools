#!/bin/bash
# Tests for guard-destructive.sh (push refspec + approval lifecycle).
set -u
export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL='*'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HOOK="$SCRIPT_DIR/../hooks/guard-destructive.sh"
CONSUME_HOOK="$SCRIPT_DIR/../hooks/consume-approval.sh"

# Isolated HOME so the hook's approval/log files don't touch the real ~/.claude
TMP_HOME=$(mktemp -d)
export HOME="$TMP_HOME"
mkdir -p "$HOME/.claude"
trap 'rm -rf "$TMP_HOME"' EXIT

FAILS=0

run_hook() {
  local cmd="$1"
  local payload
  payload=$(jq -n --arg c "$cmd" '{tool_input: {command: $c}}')
  echo "$payload" | bash "$HOOK" >/dev/null 2>/tmp/guard-destructive-stderr
  echo $?
}

run_consume() {
  echo '{}' | bash "$CONSUME_HOOK" >/dev/null 2>&1
}

assert_blocked() {
  local desc="$1" cmd="$2"
  local rc
  rc=$(run_hook "$cmd")
  if [ "$rc" != "2" ]; then
    echo "  [x] $desc — expected block (2), got $rc"
    FAILS=$((FAILS + 1))
  else
    echo "  [v] $desc"
  fi
}

assert_allowed() {
  local desc="$1" cmd="$2"
  local rc
  rc=$(run_hook "$cmd")
  if [ "$rc" != "0" ]; then
    echo "  [x] $desc — expected allow (0), got $rc (stderr: $(cat /tmp/guard-destructive-stderr))"
    FAILS=$((FAILS + 1))
  else
    echo "  [v] $desc"
  fi
}

echo "-- push refspec destination check --"
# Pushing main/master directly is still blocked.
assert_blocked "git push origin master"            "git push origin master"
assert_blocked "git push origin main"              "git push origin main"
assert_blocked "git push origin HEAD:master"       "git push origin HEAD:master"
assert_blocked "git push origin HEAD:main"         "git push origin HEAD:main"
assert_blocked "git push origin feature:main"      "git push origin feature:main"
assert_blocked "git push origin +feature:master"   "git push origin +feature:master"
assert_blocked "git push origin :main (delete)"    "git push origin :main"
assert_blocked "git push origin refs/heads/master" "git push origin refs/heads/master"
# Pushing FROM master TO a feature branch is fine — master is the source side.
assert_allowed "push master:fix-branch"            "git push origin master:fix-branch"
assert_allowed "push master:feature/foo"           "git push origin master:feature/foo"
assert_allowed "push main:work-branch"             "git push origin main:work-branch"
assert_allowed "push -u origin master:fix"         "git push -u origin master:fix"
assert_allowed "push to feature ref"               "git push origin feature-branch"
assert_allowed "push refs/heads/master:dst"        "git push origin refs/heads/master:dst"
# Force flag still blocks.
assert_blocked "force push to feature"             "git push --force origin feature"
assert_blocked "force push -f"                     "git push -f origin feature"
# Commit messages mentioning master should not false-positive (push extraction
# stops at && | ;).
assert_allowed "commit msg with 'master'"          "git commit -m 'rename master loop' && git push origin feature"

echo "-- approval lifecycle (PostToolUse consumer) --"
# A fresh approval lets a blocked command through but the PreToolUse hook
# does NOT delete the file — only the PostToolUse consumer does.
touch "$HOME/.claude/guard-approve"
rc=$(run_hook "rm -rf /tmp/foo")
if [ "$rc" != "0" ]; then
  echo "  [x] approval allows blocked cmd — expected allow, got $rc"
  FAILS=$((FAILS + 1))
elif [ ! -f "$HOME/.claude/guard-approve" ]; then
  echo "  [x] approval file deleted by PreToolUse (should persist until PostToolUse)"
  FAILS=$((FAILS + 1))
else
  echo "  [v] approval allows blocked cmd, file persists for PostToolUse"
fi

# Subsequent attempt within window still allowed (simulates: hook approved,
# permission layer denied, no PostToolUse fired, AI retries).
rc=$(run_hook "rm -rf /tmp/foo")
if [ "$rc" != "0" ]; then
  echo "  [x] retry within window — expected allow, got $rc"
  FAILS=$((FAILS + 1))
else
  echo "  [v] retry within window still allowed (denial-survives behavior)"
fi

# After PostToolUse consumer runs, the approval is gone.
run_consume
if [ -f "$HOME/.claude/guard-approve" ]; then
  echo "  [x] PostToolUse consumer did not delete approval"
  FAILS=$((FAILS + 1))
else
  echo "  [v] PostToolUse consumer deleted approval"
fi

# Next attempt blocks again.
rc=$(run_hook "rm -rf /tmp/foo")
if [ "$rc" != "2" ]; then
  echo "  [x] post-consume — expected block (2), got $rc"
  FAILS=$((FAILS + 1))
else
  echo "  [v] post-consume blocks again"
fi

# Expired approval (>60s) is cleaned up by PreToolUse and does not allow.
touch -d '2 minutes ago' "$HOME/.claude/guard-approve" 2>/dev/null || \
  touch -t "$(date -d '2 minutes ago' +%Y%m%d%H%M.%S 2>/dev/null || date -v-2M +%Y%m%d%H%M.%S)" "$HOME/.claude/guard-approve" 2>/dev/null
rc=$(run_hook "rm -rf /tmp/foo")
if [ "$rc" != "2" ]; then
  echo "  [x] expired approval — expected block (2), got $rc"
  FAILS=$((FAILS + 1))
elif [ -f "$HOME/.claude/guard-approve" ]; then
  echo "  [x] expired approval not cleaned up"
  FAILS=$((FAILS + 1))
else
  echo "  [v] expired approval blocks and is cleaned up"
fi

exit "$FAILS"
