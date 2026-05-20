#!/bin/bash
# Tests for guard-git-internals.sh.
set -u
export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL='*'
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HOOK="$SCRIPT_DIR/../hooks/guard-git-internals.sh"

TMP_HOME=$(mktemp -d)
export HOME="$TMP_HOME"
mkdir -p "$HOME/.claude"
trap 'rm -rf "$TMP_HOME"' EXIT

FAILS=0

run_hook() {
  local cmd="$1"
  local payload
  payload=$(jq -n --arg c "$cmd" '{tool_input: {command: $c}}')
  echo "$payload" | bash "$HOOK" >/dev/null 2>/tmp/guard-git-stderr
  echo $?
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
    echo "  [x] $desc — expected allow (0), got $rc (stderr: $(cat /tmp/guard-git-stderr))"
    FAILS=$((FAILS + 1))
  else
    echo "  [v] $desc"
  fi
}

echo "-- baseline (no .git or no destructive verb) --"
assert_allowed "empty command"                ""
assert_allowed "ls .git (read-only)"          "ls .git"
assert_allowed "cat .git/HEAD"                "cat .git/HEAD"
assert_allowed "git status"                   "git status"
assert_allowed "git log"                      "git log --oneline"
assert_allowed "git worktree remove (allowed)" "git worktree remove ../wt-foo"
assert_allowed "rm against unrelated file"    "rm /tmp/foo.txt"
assert_allowed "rm against ~/.gitignore"      "rm ~/.gitignore"
assert_allowed "Get-ChildItem .git"           'Get-ChildItem .git'
assert_allowed "find .git read-only"          "find .git -type f"

echo "-- unix rm/mv/cp targeting .git --"
assert_blocked "rm -rf .git"                  "rm -rf .git"
assert_blocked "rm -rf ./.git"                "rm -rf ./.git"
assert_blocked "rm -rf path/.git"             "rm -rf src/.git"
assert_blocked "rm -rf .git/HEAD"             "rm -rf .git/HEAD"
assert_blocked "rm -rf .git/objects"          "rm -rf .git/objects"
assert_blocked "rm -rf with quoted .git"      "rm -rf '.git'"
assert_blocked "rm -rf with double-quoted"    'rm -rf ".git"'
assert_blocked "rmdir .git"                   "rmdir .git"
assert_blocked "unlink .git/HEAD"             "unlink .git/HEAD"
assert_blocked "shred .git/index"             "shred .git/index"
assert_blocked "mv .git foo"                  "mv .git foo"
assert_blocked "mv .git/HEAD elsewhere"       "mv .git/HEAD /tmp/HEAD.bak"
assert_blocked "cp overwrite .git/config"     "cp /tmp/config .git/config"
assert_blocked "chmod 000 .git/HEAD"          "chmod 000 .git/HEAD"
assert_blocked "chown root .git"              "chown root:root .git"
assert_blocked "ln replace .git"              "ln -sf /tmp/foo .git"
assert_blocked "tee into .git/HEAD"           "echo x | tee .git/HEAD"
assert_blocked "truncate .git/index"          "truncate -s 0 .git/index"

echo "-- absolute-path invocation --"
assert_blocked "/usr/bin/rm .git"             "/usr/bin/rm -rf .git"
assert_blocked "/bin/rm .git/HEAD"            "/bin/rm .git/HEAD"

echo "-- output redirection into .git --"
assert_blocked "echo > .git/HEAD"             'echo "" > .git/HEAD'
assert_blocked "echo >> .git/config"          'echo x >> .git/config'
assert_blocked "redirect into nested"         'echo x > .git/refs/heads/main'
assert_blocked "fd-prefixed redirect 2> path" 'cmd 2> .git/log'
assert_blocked "bash &> path"                 'cmd &> .git/log'
assert_blocked "no-space > .git"              'echo x >.git/HEAD'
# Real path redirect alongside an fd-dup must still block.
assert_blocked "mixed fd dup + path redirect" 'echo x 2>&1 > .git/HEAD'

echo "-- fd duplication does NOT trigger redirect block --"
# These all appeared as false positives in the 2026-05-19 incident.
assert_allowed "ls .git 2>&1 | head"          'ls -la .git 2>&1 | head -10'
assert_allowed "cat path/.git 2>&1"           'cat foo/.git 2>&1 | head -3'
assert_allowed "find -name .git 2>&1"         'find . -maxdepth 4 -name ".git" 2>&1 | head -20'
assert_allowed "ls .git 1>&2"                 'ls .git 1>&2'
assert_allowed "git status 2>&1"              'git status .git 2>&1'

echo "-- windows cmd verbs --"
assert_blocked "del .git\\HEAD"               'del .git\HEAD'
assert_blocked "del /s /q .git"               'del /s /q .git'
assert_blocked "rd /s /q .git"                'rd /s /q .git'
assert_blocked "rmdir /s .git"                'rmdir /s /q .git'
assert_blocked "move .git foo"                'move .git foo'
assert_blocked "ren .git old"                 'ren .git .git-old'
assert_blocked "rename .git old"              'rename .git .git-old'

echo "-- powershell cmdlets --"
assert_blocked "Remove-Item .git"             'Remove-Item -Recurse -Force .git'
assert_blocked "Remove-Item .git/HEAD"        'Remove-Item .git/HEAD'
assert_blocked "Remove-Item .git\\HEAD"       'Remove-Item .git\HEAD'
assert_blocked "Move-Item .git"               'Move-Item .git foo'
assert_blocked "Rename-Item .git"             'Rename-Item .git .git-old'
assert_blocked "Set-Content .git/HEAD"        'Set-Content .git/HEAD "ref: foo"'
assert_blocked "Clear-Content .git/index"     'Clear-Content .git/index'
assert_blocked "Out-File .git/HEAD"           'Out-File .git/HEAD'

echo "-- powershell case insensitivity --"
assert_blocked "remove-item lowercase"        'remove-item -recurse -force .git'
assert_blocked "REMOVE-ITEM uppercase"        'REMOVE-ITEM .git'
assert_blocked "Move-item mixed case"         'Move-item .git foo'

echo "-- find -delete / -exec --"
assert_blocked "find .git -delete"            "find .git -delete"
assert_blocked "find . -name .git -delete"    "find . -name .git -delete"
assert_blocked "find .git -exec rm"           "find .git -type f -exec rm {} \\;"
assert_blocked "find -exec rm with .git arg"  "find . -name HEAD -exec rm .git/HEAD \\;"

echo "-- segment isolation --"
# Destructive verb in a different segment from .git must NOT block.
assert_allowed "ls .git && rm tmp.txt"        "ls .git && rm tmp.txt"
assert_allowed "cat .git/HEAD && ls"          "cat .git/HEAD && ls"
assert_allowed "echo .git mention"            'echo "do not touch .git here"'
# Same segment still blocks.
assert_blocked "compound rm via &&"           "echo hi && rm -rf .git"
assert_blocked "compound rm via ;"            "echo hi ; rm -rf .git"
assert_blocked "pipe to tee .git/HEAD"        "echo hi | tee .git/HEAD"

echo "-- false-positive guards --"
# Strings that contain ".git" as a suffix or substring but aren't the target.
assert_allowed "rm repo.git (bare clone)"     "rm -rf myrepo.git"
assert_allowed "rm .gitignore"                "rm .gitignore"
assert_allowed "rm .gitattributes"            "rm .gitattributes"
assert_allowed "rm .gitmodules"               "rm .gitmodules"
assert_allowed "echo .gitignore via tee"      "echo x | tee .gitignore"
assert_allowed "rm .git-old (renamed away)"   "rm -rf .git-old"
assert_allowed "rm path/foo.git/objects"      "rm -rf path/foo.git/objects"
assert_allowed "Set-Content .gitignore"       'Set-Content .gitignore "node_modules"'
assert_allowed "echo .git in string"          'echo "the .git directory is special"'

echo "-- ssh/scp/rsync remote exemption --"
# .git on a remote host is the remote's problem, not ours.
assert_allowed "ssh remote rm .git"           'ssh root@host "rm -rf .git"'
assert_allowed "scp into remote .git"         'scp file root@host:.git/HEAD'
assert_allowed "rsync into remote .git"       'rsync -av file root@host:.git/'

echo "-- no approval bypass (hard block) --"
# The user explicitly creates the approval file, but this hook must still block.
touch "$HOME/.claude/guard-approve"
assert_blocked "approval does NOT bypass"     "rm -rf .git"
# Approval file should be untouched (this hook does not consume it).
if [ ! -f "$HOME/.claude/guard-approve" ]; then
  echo "  [x] approval file was consumed (should not be — hook is hard-block)"
  FAILS=$((FAILS + 1))
else
  echo "  [v] approval file preserved (hook did not touch it)"
fi
rm -f "$HOME/.claude/guard-approve"

echo "-- denial logging --"
LOG_FILE="$HOME/.claude/logs/guard-git-internals.log"
rm -f "$LOG_FILE"
run_hook "rm -rf .git" >/dev/null
if [ ! -f "$LOG_FILE" ]; then
  echo "  [x] denial log file not created"
  FAILS=$((FAILS + 1))
elif ! grep -q 'rm -rf .git' "$LOG_FILE"; then
  echo "  [x] denial not recorded in log file"
  FAILS=$((FAILS + 1))
else
  echo "  [v] denial logged to $LOG_FILE"
fi

exit "$FAILS"
