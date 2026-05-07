#!/bin/bash
# Tests for guard-system-paths.sh. Run from anywhere; resolves paths relative to itself.
set -u
# Git Bash on Windows auto-rewrites Unix-looking arguments (e.g. /usr/bin/rm)
# to MSYS-translated Windows paths when invoking native .exe binaries like
# jq.exe. That breaks tests that use `jq --arg c '/usr/bin/rm ...'` because the
# command-under-test becomes 'C:/Program Files/Git/usr/bin/rm ...'. Disable the
# rewrite so payloads reach the hook verbatim.
export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL='*'
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HOOK="$SCRIPT_DIR/../hooks/guard-system-paths.sh"

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
  echo "$payload" | bash "$HOOK" >/dev/null 2>/tmp/guard-syspath-stderr
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
    echo "  [x] $desc — expected allow (0), got $rc (stderr: $(cat /tmp/guard-syspath-stderr))"
    FAILS=$((FAILS + 1))
  else
    echo "  [v] $desc"
  fi
}

echo "-- baseline (no system path or no destructive verb) --"
assert_allowed "empty command"                ""
assert_allowed "ls -la"                       "ls -la"
assert_allowed "ls /bin (read-only)"          "ls /bin"
assert_allowed "cat /etc/hostname"            "cat /etc/hostname"
assert_allowed "find /usr/bin -name foo"      "find /usr/bin -name foo"
assert_allowed "Get-ChildItem windows"        'Get-ChildItem C:\Windows'
assert_allowed "Test-Path windows file"       'Test-Path C:\Windows\System32\powershell.exe'
assert_allowed "rm against user file"         "rm /tmp/foo.txt"
assert_allowed "mv user dirs"                 "mv ~/foo ~/bar"

echo "-- AI cannot create approval file --"
assert_blocked "AI touches guard-approve"     "touch ~/.claude/guard-approve"
assert_blocked "AI echoes guard-approve"      'echo x > $HOME/.claude/guard-approve'

echo "-- windows powershell --"
assert_blocked "Rename-Item powershell.exe"   'Rename-Item C:\Windows\System32\powershell.exe powershell-old.exe'
assert_blocked "Remove-Item windows file"     'Remove-Item C:\Windows\System32\foo.exe'
assert_blocked "Move-Item windows file"       'Move-Item C:\Windows\System32\foo.exe C:\Temp\'
assert_blocked "Copy-Item -Force windows"     'Copy-Item -Force C:\Temp\foo.exe C:\Windows\System32\foo.exe'
assert_blocked "Set-Content into windows"     'Set-Content C:\Windows\System32\foo.txt "hi"'
assert_blocked "icacls system32"              'icacls C:\Windows\System32 /grant Everyone:F'
assert_blocked "takeown system32"             'takeown /f C:\Windows\System32\foo.exe'
assert_blocked "env:SystemRoot"               'Remove-Item $env:SystemRoot\System32\foo.exe'

echo "-- powershell case insensitivity (PS is case-insensitive) --"
assert_blocked "remove-item lowercase"        'remove-item C:\Windows\System32\powershell.exe'
assert_blocked "REMOVE-ITEM uppercase"        'REMOVE-ITEM C:\Windows\System32\powershell.exe'
assert_blocked "rename-Item mixed"            'rename-Item C:\Windows\System32\foo.exe foo-old.exe'
assert_blocked "move-item lowercase"          'move-item C:\Windows\System32\foo.exe C:\Temp\'

echo "-- UNC / extended-length / device-namespace prefixes --"
assert_blocked "UNC ext-length Remove-Item"   'Remove-Item \\?\C:\Windows\System32\powershell.exe'
assert_blocked "UNC device-ns del"            'del \\.\C:\Windows\System32\foo.exe'
assert_blocked "UNC ext-length program files" 'Remove-Item "\\?\C:\Program Files\App\foo.exe"'
assert_blocked "UNC ext-length lowercase"     'remove-item \\?\c:\windows\system32\foo.exe'

echo "-- windows cmd --"
assert_blocked "del system32"                 'del C:\Windows\System32\foo.exe'
assert_blocked "ren system32"                 'ren C:\Windows\System32\foo.exe foo-old.exe'
assert_blocked "rename system32"              'rename C:\Windows\System32\foo.exe foo-old.exe'
assert_blocked "move system32"                'move C:\Windows\System32\foo.exe D:\'
assert_blocked "rd /s windows"                'rd /s /q C:\Windows\System32\foo'
assert_blocked "program files"                'del "C:\Program Files\App\foo.exe"'
assert_blocked "program files x86"            'del "C:\Program Files (x86)\App\foo.exe"'
assert_blocked "%SystemRoot%"                 'del %SystemRoot%\System32\foo.exe'
assert_blocked "%WINDIR%"                     'del %WINDIR%\System32\foo.exe'

echo "-- unix linux --"
assert_blocked "rm /usr/bin/python"           "rm /usr/bin/python"
assert_blocked "rm -rf /bin/sh"               "rm -rf /bin/sh"
assert_blocked "rm /sbin/init"                "rm /sbin/init"
assert_blocked "mv /etc/passwd"               "mv /etc/passwd /tmp/passwd.old"
assert_blocked "chmod 777 /etc/passwd"        "chmod 777 /etc/passwd"
assert_blocked "chown root /usr/bin"          "chown root /usr/bin/python"
assert_blocked "ln -sf into /usr/bin"         "ln -sf /tmp/foo /usr/bin/python"
assert_blocked "redirect into /etc/hosts"     "echo x > /etc/hosts"
assert_blocked "tee into /etc"                "echo x | tee /etc/hosts"
assert_blocked "rm /usr/lib/foo"              "rm /usr/lib/foo.so"
assert_blocked "rm /lib64/foo"                "rm /lib64/foo.so"
assert_blocked "rm /boot/grub.cfg"            "rm /boot/grub.cfg"

echo "-- unix macos --"
assert_blocked "rm /System/Library/Foo"       "rm -rf /System/Library/Foo"
assert_blocked "mv /System/Library/Foo"       "mv /System/Library/Foo /tmp/"

echo "-- find -delete / -exec rm --"
assert_blocked "find -delete in /etc"         "find /etc -name '*.old' -delete"
assert_blocked "find -exec rm in /usr/bin"    "find /usr/bin -name 'python*' -exec rm {} \\;"
assert_blocked "find -exec unlink"            "find /usr/sbin -exec unlink {} \\;"
assert_allowed "find user dir -delete"        "find ~/tmp -name '*.bak' -delete"

echo "-- segment isolation --"
# A destructive verb in a different segment from the system path must NOT block.
assert_allowed "ls /bin && rm tmp.txt"        "ls /bin && rm tmp.txt"
assert_allowed "echo /etc reference"          'echo "/etc/passwd is sensitive"'
assert_allowed "cat /etc/hosts && ls"         "cat /etc/hosts && ls"
# A destructive verb in the SAME segment as a system path MUST block.
assert_blocked "compound delete via &&"       "echo hi && rm /usr/bin/python"
assert_blocked "compound delete via ;"        "echo hi ; rm /usr/bin/python"
assert_blocked "pipe to tee /etc"             "echo hi | tee /etc/hosts"

echo "-- false-positive guards --"
# Path-like strings that aren't actually system paths
assert_allowed "rm against /etcd-data"        "rm /etcd-data/foo"
assert_allowed "rm under ~/etc"               "rm ~/etc/foo.conf"
assert_allowed "mv into /usr/binary-name"     "mv foo /usr/binary-name"
assert_allowed "sed unrelated"                "sed -i 's/foo/bar/' ~/file.txt"

echo "-- ssh/scp/rsync remote wrapper exemption --"
# Paths inside an ssh/scp/rsync command refer to a REMOTE host, not the local OS.
assert_allowed "ssh remote rm /etc"           'ssh root@example.com "rm /etc/foo"'
assert_allowed "ssh remote redirect to /root" 'ssh root@host "cat > /root/foo"'
assert_allowed "ssh -i flag, remote redirect" 'ssh -i ~/.ssh/key root@1.2.3.4 "cat > /etc/nginx/foo"'
assert_allowed "ssh.exe full path remote"     '/c/Windows/System32/OpenSSH/ssh.exe -i ~/.ssh/k root@host "ls /etc/nginx"'
assert_allowed "scp into remote /etc"         'scp file root@host:/etc/foo'
assert_allowed "rsync into remote /etc"       'rsync -av file root@host:/etc/'
# But ssh to localhost CAN affect this machine, so destructive ops must still block.
# (Unquoted form — current verb regex requires shell word boundaries, so the
# quoted variant is a known gap left out of this fix's scope.)
assert_blocked "ssh root@localhost rm /etc"   'ssh root@localhost rm /etc/passwd'
assert_blocked "ssh 127.0.0.1 rm /usr/bin"    'ssh root@127.0.0.1 rm /usr/bin/python'
assert_blocked "ssh ::1 rm /etc"              'ssh root@[::1] rm /etc/foo'

echo "-- ssh quoted-payload quote-aware splitting --"
# Operators (; | && ||) and redirects (>) INSIDE the ssh quoted argument must
# not be split into local segments. The whole quoted block is remote.
assert_allowed "ssh remote ; chain in quotes" \
  'ssh root@host "echo a; ls /etc/nginx; ls /var/foo"'
assert_allowed "ssh remote 2>/dev/null in quotes" \
  'ssh root@host "ls -la /etc/nginx/ 2>/dev/null"'
assert_allowed "ssh remote pipe in quotes" \
  'ssh root@host "ps aux | grep -i task | grep -v grep"'
assert_allowed "ssh.exe full repro from bug" \
  '/c/Windows/System32/OpenSSH/ssh.exe -i ~/.ssh/key root@1.2.3.4 "echo === a ===; ls -la /var/www/foo; echo; head -100 /var/www/foo/index.html; ls -la /etc/nginx/conf.d/ 2>/dev/null; ps aux | grep -v grep"'
# Quote-awareness must not break legitimate compound detection: an unquoted
# destructive op chained AFTER a quoted ssh payload still has to block locally.
assert_blocked "ssh remote then local rm /etc" \
  'ssh root@host "ls /etc/foo" && rm /etc/passwd'

echo "-- system-path executable as first token --"
# Invoking a binary that lives in a system path is read-only — the path is the
# program being run, not a destructive target. Only block when an *additional*
# system path appears as a target (or a destructive verb still applies).
assert_allowed "ssh.exe just invoked"         '/c/Windows/System32/OpenSSH/ssh.exe -V'
assert_allowed "/usr/bin/git status"          '/usr/bin/git status'
assert_allowed "ssh.exe via pipe"             'echo hi | /c/Windows/System32/OpenSSH/ssh.exe root@host cat'
# Destructive verb against a system-path target still blocks even if the exe
# itself happens to live in a system path.
assert_blocked "/usr/bin/rm against /etc"     '/usr/bin/rm /etc/passwd'

echo "-- approval bypass --"
touch "$HOME/.claude/guard-approve"
assert_allowed "approval allows blocked cmd"  "rm /usr/bin/python"
# PreToolUse does NOT consume the approval — that's the PostToolUse consumer's
# job. So a retry within the 60s window (e.g. after a permission-layer denial)
# is still allowed.
assert_allowed "approval persists for retry"  "rm /usr/bin/python"
# Simulate the PostToolUse consumer running after the tool actually executed.
echo '{}' | bash "$SCRIPT_DIR/../hooks/consume-approval.sh" >/dev/null 2>&1
# Now the approval is gone — next attempt blocks.
assert_blocked "post-consume blocks again"    "rm /usr/bin/python"

echo "-- denial logging --"
# Trigger a fresh denial and verify it was logged
LOG_FILE="$HOME/.claude/logs/guard-system-paths.log"
rm -f "$LOG_FILE"
run_hook "rm /usr/bin/python" >/dev/null
if [ ! -f "$LOG_FILE" ]; then
  echo "  [x] denial log file not created"
  FAILS=$((FAILS + 1))
elif ! grep -q 'rm /usr/bin/python' "$LOG_FILE"; then
  echo "  [x] denial not recorded in log file"
  FAILS=$((FAILS + 1))
else
  echo "  [v] denial logged to $LOG_FILE"
fi

exit "$FAILS"
