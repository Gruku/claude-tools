#!/bin/bash
# guard-system-paths.sh — PreToolUse hook for Bash commands.
# Blocks rename/move/delete/chmod/redirect operations targeting OS system paths
# on Windows (C:\Windows, Program Files, %SystemRoot%) and Unix-like systems
# (/bin, /sbin, /usr/bin, /usr/sbin, /usr/lib, /etc, /boot, /lib, /System/Library).
# Every denial is logged to ~/.claude/logs/guard-system-paths.log so escalation
# patterns are visible.
# Exit 2 = block (stderr to model). Exit 0 = allow.
#
# Approval flow (shared with the rest of guard-hooks):
#   The AI calls AskUserQuestion with labels "Approve"/"Deny"; the PostToolUse
#   ask-question-approval hook creates the approval file automatically when the
#   user picks "Approve". The user can also type "approve" as a chat message
#   (UserPromptSubmit hook). Approval is valid 60 seconds and consumed on use.

APPROVE_FILE="$HOME/.claude/guard-approve"
LOG_DIR="$HOME/.claude/logs"
LOG_FILE="$LOG_DIR/guard-system-paths.log"

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if [ -z "$COMMAND" ]; then
  exit 0
fi

# --- AI must not create the approval file ---
if echo "$COMMAND" | grep -qE 'guard-approve'; then
  cat >&2 <<'EOF'
GUARD HOOK BLOCKED THIS COMMAND.
Reason: You cannot create or manipulate the guard approval file. Only the user can do this manually.
EOF
  exit 2
fi

# Approval is NOT consumed here. The PostToolUse hook (consume-approval.sh)
# deletes the file after the tool actually runs, so a denial at the standard
# permission layer leaves the approval intact for a retry within the window.
check_approval() {
  if [ -f "$APPROVE_FILE" ]; then
    local mtime age
    mtime=$(stat -c %Y "$APPROVE_FILE" 2>/dev/null || stat -f %m "$APPROVE_FILE" 2>/dev/null)
    # If stat fails entirely we can't determine age — treat as no approval
    # and DO NOT consume the token, so the user's later attempt still works.
    if [ -z "$mtime" ]; then
      return 1
    fi
    age=$(( $(date +%s) - mtime ))
    if [ "$age" -le 60 ] 2>/dev/null; then
      return 0
    fi
    rm -f "$APPROVE_FILE"
  fi
  return 1
}

log_denied() {
  mkdir -p "$LOG_DIR" 2>/dev/null
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1 | CMD: $COMMAND" >> "$LOG_FILE" 2>/dev/null
}

block() {
  if check_approval; then
    exit 0
  fi
  log_denied "$1"
  cat >&2 <<EOF
GUARD HOOK BLOCKED THIS COMMAND.
Reason: $1
Command: $COMMAND

System OS paths (C:\\Windows, C:\\Program Files, /bin, /sbin, /usr/bin, /usr/sbin, /etc, /boot, /lib, /System/Library) cannot be modified, renamed, moved, or deleted by Claude under any circumstances.

ACTION REQUIRED: Use the AskUserQuestion tool with EXACTLY this shape:
  question: one short sentence describing the system-path action and why it is needed
  options (use these labels verbatim — do not rename, translate, or add more):
    - label: "Approve"  description: "Run the command as shown"
    - label: "Deny"     description: "Cancel; do not run the command"

After the user responds:
  - "Approve" → rerun the ORIGINAL command unchanged
  - "Deny" or no response → do NOT run the command

Only the exact label "Approve" is recognized as authorization. The PostToolUse
hook on AskUserQuestion creates the approval file automatically — you do NOT
need to ask the user to touch any file. Typing "approve" as a chat message is
also recognized as a fallback. Do NOT re-run automatically. Do NOT create the
approval file yourself.
EOF
  exit 2
}

# --- Path patterns ---
# Windows: C:\Windows, C:\Program Files [(x86)], Git Bash /c/Windows,
# cmd env vars %SystemRoot%/%WINDIR%, PowerShell $env:SystemRoot/$env:windir/$env:ProgramFiles.
# Also UNC / extended-length / device-namespace prefixes: \\?\C:\Windows..., \\.\C:\Windows...
# (in single-quoted shell, \\ is two literal backslashes; in ERE \\ matches one backslash —
# so \\\\ matches the two literal backslashes that start a UNC path.)
WIN_SYS_RE='([cC]:[\\/]+[wW]indows([\\/[:space:]]|$)|[cC]:[\\/]+[pP]rogram[[:space:]]+[fF]iles([[:space:]]+\(x86\))?([\\/[:space:]]|$)|\\\\(\?|\.)\\[cC]:[\\/]+[wW]indows([\\/[:space:]]|$)|\\\\(\?|\.)\\[cC]:[\\/]+[pP]rogram[[:space:]]+[fF]iles([[:space:]]+\(x86\))?([\\/[:space:]]|$)|/c/[wW]indows([/[:space:]]|$)|%SystemRoot%|%WINDIR%|\$env:SystemRoot|\$env:windir|\$env:ProgramFiles)'

# Unix: /bin, /sbin, /etc, /boot, /lib, /lib64, /usr/{bin,sbin,lib,lib64,local/bin,local/sbin}, /System/Library.
# Anchored with a non-path-char boundary so user paths like ~/etc/ or /home/x/etc/
# don't false-positive on the /etc/ prefix.
UNIX_SYS_RE='(^|[^a-zA-Z0-9_/.~-])(/(bin|sbin|etc|boot|lib|lib64)([/[:space:]]|$)|/usr/(bin|sbin|lib|lib64|local/bin|local/sbin)([/[:space:]]|$)|/System/Library([/[:space:]]|$))'

# --- Verb patterns ---
# Unix-style destructive verbs (rm, mv, cp, chmod, chown, ln -s, tee, dd, truncate)
UNIX_VERB_RE='(^|[[:space:]&|;`(])(rm|rmdir|unlink|shred|mv|cp|chmod|chown|chgrp|ln|tee|dd|truncate)([[:space:]]|$)'

# Windows cmd verbs (del, erase, move, ren/rename, rd/rmdir, copy, xcopy, robocopy)
CMD_VERB_RE='(^|[[:space:]&|;`(])(del|erase|move|ren|rename|rd|rmdir|copy|xcopy|robocopy)([[:space:]]|/|$)'

# PowerShell destructive cmdlets and ACL tools.
# PowerShell is case-INsensitive, so the grep below uses -qiE.
PS_VERB_RE='(Remove-Item|Move-Item|Rename-Item|Copy-Item|Set-Item|New-Item|Set-ItemProperty|Out-File|Set-Content|Add-Content|Clear-Content|Set-Acl|takeown|icacls)'

# `find ... -delete` / `find ... -exec rm` / `find ... -exec unlink` etc.
# These are real destructive forms that don't fit the simple verb list above.
FIND_DESTRUCTIVE_RE='(^|[[:space:]&|;`(])find([[:space:]]+[^|;&]*)?[[:space:]](-delete|-exec[[:space:]]+(rm|unlink|shred|chmod|chown|mv))'

# Output redirection (cmd, bash, PowerShell all use > / >>)
REDIRECT_RE='(>|>>)'

# --- Split command into segments by &&, ||, ;, | ---
# Each subcommand is checked in isolation so that  `ls /bin && rm tmp.txt`  passes
# (system path and destructive verb live in different segments).
# Quote-aware: operators inside single or double quotes do NOT split. Without
# this, an `ssh remote "cmd1; cmd2 > /etc/foo"` payload would shred into local
# segments and false-positive on the inner `;` and `>` even though the whole
# thing runs remotely.
SEGMENTS_ARR=()
current=""
in_single=0
in_double=0
i=0
len=${#COMMAND}
while [ "$i" -lt "$len" ]; do
  ch="${COMMAND:$i:1}"
  # Inside double quotes, backslash escapes the next char (notably \") — keep
  # both verbatim and advance past them so the escaped quote doesn't toggle state.
  if [ "$in_double" -eq 1 ] && [ "$ch" = "\\" ] && [ $((i + 1)) -lt "$len" ]; then
    current+="${COMMAND:$i:2}"
    i=$((i + 2))
    continue
  fi
  if [ "$in_single" -eq 0 ] && [ "$ch" = '"' ]; then
    in_double=$((1 - in_double))
    current+="$ch"
    i=$((i + 1))
    continue
  fi
  if [ "$in_double" -eq 0 ] && [ "$ch" = "'" ]; then
    in_single=$((1 - in_single))
    current+="$ch"
    i=$((i + 1))
    continue
  fi
  if [ "$in_single" -eq 0 ] && [ "$in_double" -eq 0 ]; then
    two="${COMMAND:$i:2}"
    if [ "$two" = "&&" ] || [ "$two" = "||" ]; then
      SEGMENTS_ARR+=("$current")
      current=""
      i=$((i + 2))
      continue
    fi
    if [ "$ch" = ";" ] || [ "$ch" = "|" ]; then
      SEGMENTS_ARR+=("$current")
      current=""
      i=$((i + 1))
      continue
    fi
  fi
  current+="$ch"
  i=$((i + 1))
done
SEGMENTS_ARR+=("$current")

# Destructive verbs reduced to a basename allowlist — used to detect when an
# absolute-path invocation like `/usr/bin/rm /etc/passwd` is destructive even
# though the verb regex below won't match (the leading `/` isn't a word boundary).
UNIX_VERB_BASENAMES_RE='^(rm|rmdir|unlink|shred|mv|cp|chmod|chown|chgrp|ln|tee|dd|truncate)$'

# Hosts that mean "this machine" — if an ssh/scp/rsync target points here the
# segment is NOT exempted, because the operation actually runs locally.
LOCALHOST_RE='(@(localhost|127\.0\.0\.1)([[:space:]:]|$)|@\[?::1\]?([[:space:]:]|$))'

for SEG in "${SEGMENTS_ARR[@]}"; do
  [ -z "$SEG" ] && continue

  # --- Split first token (the executable) from the rest of the segment ---
  # Two reasons:
  #   1. A binary that lives in a system path (e.g. /c/Windows/System32/OpenSSH/ssh.exe,
  #      /usr/bin/git) is the program being RUN — not a destructive target. Path checks
  #      should consider arguments, not the executable itself.
  #   2. We need the basename to detect ssh/scp/rsync wrappers and absolute-path
  #      destructive verbs.
  SEG_TRIM="${SEG#"${SEG%%[![:space:]]*}"}"
  FIRST="${SEG_TRIM%%[[:space:]]*}"
  REST="${SEG_TRIM#"$FIRST"}"

  # Strip surrounding quotes from FIRST, then take the basename and drop a .exe suffix.
  FIRST_UNQ="${FIRST#\"}"; FIRST_UNQ="${FIRST_UNQ%\"}"
  FIRST_UNQ="${FIRST_UNQ#\'}"; FIRST_UNQ="${FIRST_UNQ%\'}"
  FIRST_BASE="${FIRST_UNQ##*/}"
  FIRST_BASE="${FIRST_BASE##*\\}"
  # Lowercase for case-insensitive .exe stripping (Windows is case-insensitive).
  FIRST_BASE_LOWER="$(echo "$FIRST_BASE" | tr '[:upper:]' '[:lower:]')"
  FIRST_BASE_NOEXT="${FIRST_BASE_LOWER%.exe}"

  # --- ssh/scp/rsync remote-wrapper exemption ---
  # Paths inside the args refer to a REMOTE host, not the local OS — unless the
  # target is localhost/127.0.0.1/::1, in which case the operation is local and
  # falls through to the normal checks below.
  case "$FIRST_BASE_NOEXT" in
    ssh|scp|rsync)
      if ! echo "$REST" | grep -qiE "$LOCALHOST_RE"; then
        continue
      fi
      ;;
  esac

  # --- Does this segment reference an OS system path as a TARGET? ---
  # Scan REST only; the executable's own path doesn't count.
  HIT_PATH=0
  if echo "$REST" | grep -qE "$WIN_SYS_RE"; then
    HIT_PATH=1
  fi
  if echo "$REST" | grep -qE "$UNIX_SYS_RE"; then
    HIT_PATH=1
  fi
  [ "$HIT_PATH" = "0" ] && continue

  # --- Verb / redirect checks ---
  # Absolute-path invocations (e.g. /usr/bin/rm) — the leading `/` defeats the
  # word-boundary in UNIX_VERB_RE, so detect them explicitly via basename.
  if echo "$FIRST_BASE_NOEXT" | grep -qE "$UNIX_VERB_BASENAMES_RE"; then
    block "Destructive Unix command (rm/mv/cp/chmod/chown/ln/tee/dd) targeting a system path."
  fi
  if echo "$SEG" | grep -qiE "$UNIX_VERB_RE"; then
    block "Destructive Unix command (rm/mv/cp/chmod/chown/ln/tee/dd) targeting a system path."
  fi
  if echo "$SEG" | grep -qiE "$CMD_VERB_RE"; then
    block "Destructive Windows cmd command (del/move/ren/rd/copy) targeting a system path."
  fi
  if echo "$SEG" | grep -qiE "$PS_VERB_RE"; then
    block "Destructive PowerShell cmdlet (Remove-Item/Move-Item/Rename-Item/Copy-Item/Set-Content/takeown/icacls) targeting a system path."
  fi
  if echo "$SEG" | grep -qiE "$FIND_DESTRUCTIVE_RE"; then
    block "Destructive find (-delete or -exec rm/unlink/shred/chmod/chown/mv) targeting a system path."
  fi
  if echo "$SEG" | grep -qE "$REDIRECT_RE"; then
    block "Output redirection (> or >>) into a system path."
  fi
done

exit 0
