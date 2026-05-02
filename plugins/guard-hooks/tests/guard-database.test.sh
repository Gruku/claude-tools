#!/bin/bash
# Tests for guard-database.sh. Run from anywhere; resolves paths relative to itself.
set -u
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HOOK="$SCRIPT_DIR/../hooks/guard-database.sh"

# Use an isolated HOME so the hook's approval/ack files don't touch the real ~/.claude
TMP_HOME=$(mktemp -d)
export HOME="$TMP_HOME"
mkdir -p "$HOME/.claude"
trap 'rm -rf "$TMP_HOME"' EXIT

FAILS=0

# run_hook <command>  -> echoes exit code
run_hook() {
  local cmd="$1"
  local payload
  payload=$(jq -n --arg c "$cmd" '{tool_input: {command: $c}}')
  echo "$payload" | bash "$HOOK" >/dev/null 2>/tmp/guard-db-stderr
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
    echo "  [x] $desc — expected allow (0), got $rc (stderr: $(cat /tmp/guard-db-stderr))"
    FAILS=$((FAILS + 1))
  else
    echo "  [v] $desc"
  fi
}

echo "-- skeleton --"
assert_allowed "empty command" ""
assert_allowed "harmless command" "ls -la"
assert_blocked "AI cannot create guard-approve" "touch ~/.claude/guard-approve"
assert_blocked "AI cannot create guard-approve via echo" "echo x > $HOME/.claude/guard-approve"
assert_allowed "AI may create guard-ack" "touch $HOME/.claude/guard-ack"

echo "-- sql schema --"
assert_blocked "psql DROP DATABASE"      'psql -c "DROP DATABASE foo"'
assert_blocked "psql DROP SCHEMA"        'psql -c "DROP SCHEMA public CASCADE"'
assert_blocked "mysql DROP TABLE"        'mysql -e "DROP TABLE users"'
assert_blocked "sqlite TRUNCATE"         'sqlite3 my.db "TRUNCATE TABLE logs"'
assert_blocked "psql heredoc DROP TABLE" 'psql <<EOF
DROP TABLE foo;
EOF'
assert_allowed "select with drop in name" 'psql -c "SELECT * FROM table_with_drop_in_name"'
assert_allowed "create table"            'psql -c "CREATE TABLE foo (id int)"'

exit "$FAILS"
