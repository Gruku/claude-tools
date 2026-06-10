#!/bin/sh
# Legacy shim — this hook was ported to Python (guard_bash.py) and sessions
# started before the port still invoke this path (hook registrations are
# snapshotted at SessionStart). Delegates to the port via the fail-open
# launcher. Safe to delete once no pre-port sessions remain.
# guard_bash.py consolidates all four legacy Bash guards (destructive,
# database, system-paths, git-internals); this one shim restores full
# coverage, the other three legacy names are intentional no-ops.
case "$0" in
  */*)   d=${0%/*} ;;
  *\\*)  d=${0%\\*} ;;
  *)     d=. ;;
esac
CLAUDE_HOOK_SCRIPT=guard_bash.py . "$d/run_hook.sh"
