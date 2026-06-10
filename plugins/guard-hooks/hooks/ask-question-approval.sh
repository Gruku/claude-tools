#!/bin/sh
# Legacy shim — this hook was ported to Python (ask_question_approval.py) and
# sessions started before the port still invoke this path (hook registrations
# are snapshotted at SessionStart). Delegates to the port via the fail-open
# launcher. Safe to delete once no pre-port sessions remain.
case "$0" in
  */*)   d=${0%/*} ;;
  *\\*)  d=${0%\\*} ;;
  *)     d=. ;;
esac
CLAUDE_HOOK_SCRIPT=ask_question_approval.py . "$d/run_hook.sh"
