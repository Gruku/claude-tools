#!/bin/bash
# guard-git-internals.sh — PreToolUse hook for Bash commands.
# HARD-BLOCKS any destructive operation that targets a .git directory or its
# contents. Mirrors the .git/ rule in guard-edits.sh for the Bash tool.
# No approval bypass — destroying a repo's git internals is never legitimate
# from Claude.
#
# Covers:
#   - Unix verbs (rm, mv, cp, chmod, chown, ln, tee, dd, truncate, find -delete)
#   - Windows cmd verbs (del, erase, move, ren/rename, rd/rmdir)
#   - PowerShell cmdlets (Remove-Item, Move-Item, Rename-Item, Set-Content,
#     Add-Content, Clear-Content, Out-File)
#   - Output redirection into .git/ (echo > .git/HEAD, etc.)
#
# Exit 2 = block (stderr to model). Exit 0 = allow.

LOG_DIR="$HOME/.claude/logs"
LOG_FILE="$LOG_DIR/guard-git-internals.log"

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if [ -z "$COMMAND" ]; then
  exit 0
fi

log_denied() {
  mkdir -p "$LOG_DIR" 2>/dev/null
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1 | CMD: $COMMAND" >> "$LOG_FILE" 2>/dev/null
}

block() {
  log_denied "$1"
  cat >&2 <<EOF
GUARD HOOK BLOCKED THIS COMMAND.
Reason: $1
Command: $COMMAND

Destroying or modifying .git/ directories from the Bash tool is never permitted
by Claude. There is no approval bypass — this rule is hard-blocked, mirroring
the .git/ rule already enforced on the Edit/Write tools.

If you genuinely need to remove a repository, the user must do it manually in
their own terminal. If you were trying to remove a git worktree, use
'git worktree remove <path>' (run from OUTSIDE the worktree being removed).
EOF
  exit 2
}

# --- Path patterns ---
# `.git` as a path token. Boundaries:
#   left:  start-of-string OR whitespace, '=', '/', '\', quote
#   right: '/', '\', whitespace, quote, OR end-of-string
# This matches `.git`, `.git/HEAD`, `./.git`, `path/.git`, `path\.git\...`,
# `'./.git'`, `"path/.git/HEAD"`. It does NOT match `repo.git`,
# `.gitignore`, `.gitattributes`, or `something.gitfoo`.
#
# In ERE, `\\\\` matches one literal backslash (single-quoted shell -> two
# backslashes -> one in regex). Inside a bracket class, a literal backslash
# is `\\\\` for the same reason.
#
# `>` and `<` are included as left-boundary chars so that no-space redirect
# forms like `echo x >.git/HEAD` and `cmd <.git/log` are detected.
GIT_TOKEN_RE='(^|[[:space:]=/<>'"'"'"\\])\.git([/\\[:space:]'"'"'"]|$)'

# --- Verb patterns ---
# Unix-style destructive verbs.
UNIX_VERB_RE='(^|[[:space:]&|;`(])(rm|rmdir|unlink|shred|mv|cp|chmod|chown|chgrp|ln|tee|dd|truncate)([[:space:]]|$)'

# Windows cmd verbs.
CMD_VERB_RE='(^|[[:space:]&|;`(])(del|erase|move|ren|rename|rd|rmdir)([[:space:]]|/|$)'

# PowerShell destructive cmdlets (case-insensitive — PS is case-insensitive).
PS_VERB_RE='(Remove-Item|Move-Item|Rename-Item|Copy-Item|Set-Item|Set-ItemProperty|Out-File|Set-Content|Add-Content|Clear-Content|New-Item)'

# `find ... -delete` / `find ... -exec rm` etc.
FIND_DESTRUCTIVE_RE='(^|[[:space:]&|;`(])find([[:space:]]+[^|;&]*)?[[:space:]](-delete|-exec[[:space:]]+(rm|unlink|shred|chmod|chown|mv))'

# Output redirection to a PATH (cmd, bash, PS all use > / >>).
#
# The original regex was '(>|>>)' which false-positives on file-descriptor
# duplications like '2>&1', '1>&2', '&>&N'. These are NOT path writes — the
# stream after the redirect points to another fd, not a filename — so a command
# like 'ls .git 2>&1 | head' was incorrectly blocked as a .git/ write during
# the 2026-05-19 forensic recovery.
#
# Path-targeted match: optional leading fd digit OR '&' (for bash '&>'), then
# '>' or '>>', optional whitespace, then a target byte that is NOT '&', '>',
# or whitespace. That target byte is the start of a filename. Examples:
#   ✓ '> file', '>> file', '1> file', '2>> file', '&> file'
#   ✗ '2>&1', '1>&2', '>&1' (target after > is '&')
PATH_REDIRECT_RE='(^|[[:space:]])[0-9&]?>>?[[:space:]]*[^&[:space:]>]'

# Allowlist: redirection into the review-gate blessing marker is permitted.
# Pairs with ~/.claude/hooks/push-review-gate-guard.py, which requires
# `.git/CLAUDE_REVIEW_GATE_OK` to contain the current HEAD sha before a push
# to a protected branch is allowed. Without this exception the marker can only
# be written by the user pasting `! git rev-parse HEAD > .git/...` into chat.
# Narrow scope: only the redirect rule below honors it; destructive verbs
# (rm/mv/Remove-Item/etc.) targeting this path remain hard-blocked.
BLESS_REDIRECT_RE='(>|>>)[[:space:]]*[^[:space:]&|;<>]*\.git[/\\]CLAUDE_REVIEW_GATE_OK'

# Verb basenames used for absolute-path invocations (e.g. /usr/bin/rm .git).
UNIX_VERB_BASENAMES_RE='^(rm|rmdir|unlink|shred|mv|cp|chmod|chown|chgrp|ln|tee|dd|truncate)$'

# --- Split command into segments by &&, ||, ;, | ---
SENT=$'\x01'
TMP="$COMMAND"
TMP="${TMP//&&/$SENT}"
TMP="${TMP//||/$SENT}"
TMP="${TMP//;/$SENT}"
TMP="${TMP//|/$SENT}"

OLD_IFS="$IFS"
IFS="$SENT"
read -ra SEGMENTS_ARR <<< "$TMP"
IFS="$OLD_IFS"

for SEG in "${SEGMENTS_ARR[@]}"; do
  [ -z "$SEG" ] && continue

  # --- Split first token (the executable) from the rest ---
  SEG_TRIM="${SEG#"${SEG%%[![:space:]]*}"}"
  FIRST="${SEG_TRIM%%[[:space:]]*}"
  REST="${SEG_TRIM#"$FIRST"}"

  FIRST_UNQ="${FIRST#\"}"; FIRST_UNQ="${FIRST_UNQ%\"}"
  FIRST_UNQ="${FIRST_UNQ#\'}"; FIRST_UNQ="${FIRST_UNQ%\'}"
  FIRST_BASE="${FIRST_UNQ##*/}"
  FIRST_BASE="${FIRST_BASE##*\\}"
  FIRST_BASE_LOWER="$(echo "$FIRST_BASE" | tr '[:upper:]' '[:lower:]')"
  FIRST_BASE_NOEXT="${FIRST_BASE_LOWER%.exe}"

  # Skip ssh/scp/rsync — those target a remote host, not local .git.
  case "$FIRST_BASE_NOEXT" in
    ssh|scp|rsync) continue ;;
  esac

  # --- Does this segment reference .git as a target? ---
  # Scan REST only — the executable's own path doesn't count (e.g. running
  # `/path/to/.git/hooks/pre-commit` would otherwise false-positive).
  if ! echo "$REST" | grep -qE "$GIT_TOKEN_RE"; then
    continue
  fi

  # --- Verb / redirect checks ---
  # Absolute-path invocation of a destructive verb (e.g. /usr/bin/rm .git).
  if echo "$FIRST_BASE_NOEXT" | grep -qE "$UNIX_VERB_BASENAMES_RE"; then
    block "Destructive Unix command (rm/mv/cp/chmod/chown/ln/tee/dd) targeting .git/"
  fi
  if echo "$SEG" | grep -qiE "$UNIX_VERB_RE"; then
    block "Destructive Unix command (rm/mv/cp/chmod/chown/ln/tee/dd) targeting .git/"
  fi
  if echo "$SEG" | grep -qiE "$CMD_VERB_RE"; then
    block "Destructive Windows cmd command (del/move/ren/rd) targeting .git/"
  fi
  if echo "$SEG" | grep -qiE "$PS_VERB_RE"; then
    block "Destructive PowerShell cmdlet (Remove-Item/Move-Item/Rename-Item/Set-Content) targeting .git/"
  fi
  if echo "$SEG" | grep -qiE "$FIND_DESTRUCTIVE_RE"; then
    block "Destructive find (-delete or -exec rm/unlink/shred/chmod/chown/mv) targeting .git/"
  fi
  if echo "$SEG" | grep -qE "$PATH_REDIRECT_RE"; then
    if echo "$SEG" | grep -qE "$BLESS_REDIRECT_RE"; then
      : # allowed: writing the review-gate blessing marker
    else
      block "Output redirection (> or >>) into .git/"
    fi
  fi
done

exit 0
