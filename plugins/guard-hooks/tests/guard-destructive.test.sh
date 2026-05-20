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

# Variant that passes a cwd to the hook payload, for P3 pre-flight tests
# that need to resolve relative worktree paths against a real directory.
run_hook_cwd() {
  local cmd="$1" cwd="$2"
  local payload
  payload=$(jq -n --arg c "$cmd" --arg w "$cwd" '{tool_input: {command: $c}, cwd: $w}')
  echo "$payload" | bash "$HOOK" >/dev/null 2>/tmp/guard-destructive-stderr
  echo $?
}

assert_blocked_cwd() {
  local desc="$1" cmd="$2" cwd="$3"
  local rc
  rc=$(run_hook_cwd "$cmd" "$cwd")
  if [ "$rc" != "2" ]; then
    echo "  [x] $desc — expected block (2), got $rc"
    FAILS=$((FAILS + 1))
  else
    echo "  [v] $desc"
  fi
}

assert_allowed_cwd() {
  local desc="$1" cmd="$2" cwd="$3"
  local rc
  rc=$(run_hook_cwd "$cmd" "$cwd")
  if [ "$rc" != "0" ]; then
    echo "  [x] $desc — expected allow (0), got $rc (stderr: $(cat /tmp/guard-destructive-stderr))"
    FAILS=$((FAILS + 1))
  else
    echo "  [v] $desc"
  fi
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

echo "-- git worktree remove --force (Windows cascade hazard) --"
# All --force forms are blocked; the user must approve.
assert_blocked "worktree remove --force"      "git worktree remove --force .worktrees/foo"
assert_blocked "worktree remove -f"           "git worktree remove -f .worktrees/foo"
assert_blocked "worktree remove -fq combined" "git worktree remove -fq .worktrees/foo"
assert_blocked "worktree remove --force after path" "git worktree remove .worktrees/foo --force"
assert_blocked "git -C <path> worktree remove --force" "git -C /repo worktree remove --force .worktrees/foo"
# Non-force variants and unrelated worktree subcommands stay allowed.
assert_allowed "worktree remove (no force)"   "git worktree remove .worktrees/foo"
assert_allowed "worktree prune"               "git worktree prune"
assert_allowed "worktree list"                "git worktree list"
assert_allowed "worktree add (out of scope)"  "git worktree add /tmp/wt feature"
# Path containing '-f' substring must NOT false-positive as the -f flag.
assert_allowed "remove path with -f in name"  "git worktree remove .worktrees/desktop-app-258"
assert_allowed "remove path feature-foo"      "git worktree remove .worktrees/feature-foo"
# Sanity: a 'feature' branch named *-force is fine to push (no worktree verb).
assert_allowed "push feature/--force-named"   "git push origin feature/force-disable"

echo "-- git worktree remove pre-flight: submodule-containing target --"
# Build a fixture: a repo with a worktree dir that has a .gitmodules file.
FIXTURE_REPO=$(mktemp -d)
mkdir -p "$FIXTURE_REPO/.worktrees/wt-with-subs"
echo "[submodule \"foo\"]" > "$FIXTURE_REPO/.worktrees/wt-with-subs/.gitmodules"
mkdir -p "$FIXTURE_REPO/.worktrees/wt-no-subs"
trap 'rm -rf "$TMP_HOME" "$FIXTURE_REPO"' EXIT
# Without cwd, relative path can't be resolved → hook can't pre-flight → allow.
assert_allowed "no cwd, relative path"        "git worktree remove .worktrees/wt-with-subs"
# With cwd pointing at the fixture repo, the relative path resolves and
# .gitmodules is found → approval-gated.
assert_blocked_cwd "relative path, submodule target" \
  "git worktree remove .worktrees/wt-with-subs" "$FIXTURE_REPO"
# Same fixture, absolute path → also blocked.
assert_blocked_cwd "absolute path, submodule target" \
  "git worktree remove $FIXTURE_REPO/.worktrees/wt-with-subs" "$FIXTURE_REPO"
# Sibling worktree with no submodules → allowed.
assert_allowed_cwd "relative path, no submodules" \
  "git worktree remove .worktrees/wt-no-subs" "$FIXTURE_REPO"
# Path that does not exist (typo, already-removed) → allowed (no file to check).
assert_allowed_cwd "non-existent target" \
  "git worktree remove .worktrees/does-not-exist" "$FIXTURE_REPO"
# Non-remove subcommands unaffected.
assert_allowed_cwd "worktree list with cwd"    "git worktree list" "$FIXTURE_REPO"
assert_allowed_cwd "worktree prune with cwd"   "git worktree prune" "$FIXTURE_REPO"

echo "-- destructive git ops piped through line filters (failure-masking) --"
# These all mask the upstream exit code so '&&' chains run regardless of failure.
assert_blocked "worktree remove | tail"        "git worktree remove .worktrees/foo 2>&1 | tail -2"
assert_blocked "worktree remove | head"        "git worktree remove .worktrees/foo 2>&1 | head -3"
assert_blocked "worktree remove | grep"        "git worktree remove .worktrees/foo 2>&1 | grep fatal"
assert_blocked "git push | tail"               "git push origin feature 2>&1 | tail -5"
assert_blocked "git reset | head"              "git reset HEAD~3 2>&1 | head"
assert_blocked "git clean | wc -l"             "git clean -fd 2>&1 | wc -l"
assert_blocked "chained worktree remove | tail" "git worktree remove A 2>&1 | tail -2 && git worktree remove B 2>&1 | tail -2"
# Read-only git commands piped through filters stay allowed.
assert_allowed "git log | head"                "git log --oneline | head -10"
assert_allowed "git status | grep"             "git status -s | grep modified"
assert_allowed "git branch | head"             "git branch | head"
assert_allowed "git diff | wc -l"              "git diff --stat | wc -l"
# Destructive git WITHOUT a filter remains as governed by the other rules.
assert_allowed "git push feature (no filter)"  "git push origin feature"
# Destructive command, filter is BEFORE git (different segment) — not the masking pattern.
assert_allowed "echo x | tee && git push"      "echo x | tee log.txt && git push origin feature"

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
