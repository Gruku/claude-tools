#!/bin/bash
# session-start.sh — SessionStart hook for guard-hooks plugin
#  - Checks that required dependency (python) is available (user-facing stderr).
#  - Emits a model-facing awareness banner via stdout describing the most
#    catastrophic-but-easy-to-miss rules (worktree-removal cascade, .git/
#    writes, force-push, rm -rf). Stdout from SessionStart hooks is appended
#    to the model's context as "SessionStart hook additional context".

# Probe for a usable Python >= 3.9 the same way run_hook.sh resolves one
# (a bare `command -v python` false-passes on the Windows Store stub).
PY_FOUND=""
for cand in "${CLAUDE_HOOKS_PYTHON:-}" python3 python "py -3"; do
  [ -n "$cand" ] || continue
  if $cand -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' </dev/null >/dev/null 2>&1; then
    PY_FOUND="$cand"
    break
  fi
done
if [ -z "$PY_FOUND" ]; then
  cat >&2 <<'WARN'
⚠️ guard-hooks plugin: no usable Python >= 3.9 found (tried $CLAUDE_HOOKS_PYTHON,
python3, python, py -3). The guard hooks are Python scripts as of v2.7.1 and
will be INACTIVE this session — they fail OPEN, so tool calls still work but
nothing is guarded.
Install: https://www.python.org/downloads/ (3.9+)
  - macOS:       brew install python
  - Linux (apt): sudo apt install python3
  - Windows:     winget install Python.Python.3.12
or set CLAUDE_HOOKS_PYTHON to an interpreter command.
WARN
fi

if [ -n "$PY_FOUND" ]; then
  cat <<'HEADER'
guard-hooks active. The following Bash patterns are BLOCKED (approval-gated
unless noted), with rationale you should know BEFORE attempting them:
HEADER
else
  cat <<'HEADER'
guard-hooks INACTIVE this session: no usable Python >= 3.9 on this machine,
so the guards cannot run (they fail open — tool calls are allowed but
unguarded). The following Bash patterns would normally be BLOCKED; treat
these rules as YOUR responsibility to follow manually:
HEADER
fi

cat <<'BANNER'

  • `git worktree remove --force` / `-f`  — DANGEROUS ON WINDOWS.
    Observed in a 2026-05-19 incident: with submodules or near-MAX_PATH paths,
    --force does not just delete the worktree. It cascade-deletes top-level
    dot-prefixed entries in the PARENT checkout: .git/, .gitignore,
    .gitmodules, .dockerignore, .env*, .github/, .vscode/, .ai/design/, and
    contents of .config/. All branches/reflogs/stashes go with it.
    Recovery path when `git worktree remove <path>` fails with "working trees
    containing submodules cannot be moved or removed":
      git -C <worktree-path> submodule deinit -f <submodule>
      git worktree remove <worktree-path>      # no --force
    Never escalate to --force. Never fall back to `rm -rf`.

  • `git worktree remove <path>` (no --force) is APPROVAL-GATED when <path>
    contains a .gitmodules file. Same recovery: deinit submodules first.

  • Destructive git ops piped into a line filter (| tail / | head / | grep /
    | awk / | sed / | wc / | cut) are APPROVAL-GATED. The filter overwrites
    the upstream exit code, so '&&' chains do not short-circuit on failure —
    a partial-failure cascade can run silently. Re-run without the filter.

  • `rm -rf` / `rmdir` / `shred` / `unlink`  (approval-gated)
  • PowerShell `Remove-Item -Recurse` (approval-gated) — the PowerShell tool
    is guarded the same as Bash; switching tools does not bypass any rule.
  • `git reset --hard`, `git clean -f`, `git branch -D`, `git checkout .`
  • `git stash clear` / `git stash drop --all`
  • `git push --force` and pushing to main/master (approval-gated)
  • Any write/delete touching `.git/` (HARD-blocked — no approval bypass)
  • Windows `del /s`, `rd /s`, `format`, `diskpart`

When a guard fires, it prints the rationale and recovery hint. Read those
before retrying. The approval flow is AskUserQuestion with labels exactly
"Approve" / "Deny"; only the user can authorize. An approval covers exactly
the blocked command, lasts 5 minutes, and is consumed when that command
runs — intermediate commands do not use it up, and it does not authorize
any other guarded action.
BANNER

exit 0
