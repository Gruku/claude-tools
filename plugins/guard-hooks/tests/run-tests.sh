#!/bin/bash
# Test runner for guard-hooks. Exits non-zero if any test fails.
set -u
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FAILED=0
for test_file in "$SCRIPT_DIR"/*.test.sh; do
  [ -f "$test_file" ] || continue
  echo "=== $(basename "$test_file") ==="
  if bash "$test_file"; then
    echo "PASS"
  else
    echo "FAIL"
    FAILED=$((FAILED + 1))
  fi
done
exit "$FAILED"
