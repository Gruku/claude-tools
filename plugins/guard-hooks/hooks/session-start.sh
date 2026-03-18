#!/bin/bash
# session-start.sh — SessionStart hook for guard-hooks plugin
# Checks that required dependency (jq) is available.

if ! command -v jq &>/dev/null; then
  cat >&2 <<'WARN'
⚠️ guard-hooks plugin: 'jq' is not installed or not in PATH.
All guard hooks will fail silently without it (they use jq to parse hook input).
Install: https://jqlang.github.io/jq/download/
  - macOS:       brew install jq
  - Linux (apt): sudo apt install jq
  - Windows:     winget install jqlang.jq
WARN
fi

exit 0
