#!/bin/bash
# Test runner for guard-hooks. Thin wrapper over pytest — the suite lives in
# tests/test_guards.py (Python port of the former *.test.sh files).
# Exits non-zero if any test fails.
set -u
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec python -m pytest "$SCRIPT_DIR/test_guards.py" "$@"
