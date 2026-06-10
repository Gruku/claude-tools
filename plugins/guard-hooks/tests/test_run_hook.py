# -*- coding: utf-8 -*-
"""Tests for run_hook.sh — the resilient Python-hook launcher — and for the
legacy .sh shims kept so sessions that registered pre-port hook paths
(hook registrations are snapshotted at SessionStart) neither error out
nor lose their guards.

Failure policy under test: the launcher fails OPEN (exit 0 + loud stderr)
when the hook script or a usable Python interpreter is missing. A direct
`python missing.py` exits 2, and exit 2 from a PreToolUse hook is a hard
DENY — that failure mode blocked every Write/Edit/Bash call in a real
session (inbox msg 2026-06-10-1130).
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
RUN_HOOK = HOOKS_DIR / "run_hook.sh"


def find_bash():
    """Locate the bash that hooks actually run under. On Windows that is
    git-bash (MSYS) — system32 bash.EXE is WSL and cannot read C:/ paths."""
    if os.name != "nt":
        return shutil.which("bash")
    candidates = []
    git = shutil.which("git")
    if git:
        root = Path(git).resolve().parents[1]
        candidates += [root / "bin" / "bash.exe", root / "usr" / "bin" / "bash.exe"]
    candidates += [
        Path(r"C:\Program Files\Git\bin\bash.exe"),
        Path(r"C:\Program Files\Git\usr\bin\bash.exe"),
    ]
    for cand in candidates:
        if cand.is_file():
            return str(cand)
    return None


BASH = find_bash()

pytestmark = pytest.mark.skipif(BASH is None, reason="git-bash not available")

DELEGATING_SHIMS = {
    "guard-destructive.sh": "guard_bash.py",
    "guard-edits.sh": "guard_edits.py",
    "guard-approve.sh": "guard_approve.py",
    "ask-question-approval.sh": "ask_question_approval.py",
    "consume-approval.sh": "consume_approval.py",
}
NOOP_SHIMS = [
    # Consolidated into guard_bash.py; guard-destructive.sh delegates for all
    # four, so these stay silent instead of re-running the same guard.
    "guard-database.sh",
    "guard-system-paths.sh",
    "guard-git-internals.sh",
]


def run_bash(args, stdin="", env_extra=None, cwd=None):
    env = os.environ.copy()
    env.update(env_extra or {})
    return subprocess.run(
        [BASH] + args,
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        cwd=cwd,
    )


def launcher_env(tmp_path, **extra):
    """Isolated HOME + TMPDIR (interpreter cache) for launcher runs."""
    env = {
        "HOME": str(tmp_path),
        "USERPROFILE": str(tmp_path),
        "TMPDIR": (tmp_path / "tmp").as_posix(),
    }
    (tmp_path / "tmp").mkdir(exist_ok=True)
    env.update(extra)
    return env


def cache_file(tmp_path):
    return tmp_path / "tmp" / "claude-hooks-python.cache"


# ---------------------------------------------------------------------------
# Launcher: fail-open behaviors
# ---------------------------------------------------------------------------

def test_missing_script_fails_open(tmp_path):
    r = run_bash([RUN_HOOK.as_posix(), "no_such_hook.py"], stdin="{}",
                 env_extra=launcher_env(tmp_path))
    assert r.returncode == 0
    assert "INACTIVE" in r.stderr
    assert "no_such_hook.py" in r.stderr


def test_no_argument_fails_open(tmp_path):
    r = run_bash([RUN_HOOK.as_posix()], stdin="{}",
                 env_extra=launcher_env(tmp_path))
    assert r.returncode == 0
    assert r.stderr.strip()


def test_no_usable_python_fails_open(tmp_path):
    bash_dir = str(Path(BASH).parent)
    if any(shutil.which(c, path=bash_dir) for c in ("python", "python3", "py")):
        pytest.skip("a python lives next to bash; cannot simulate no-python PATH")
    r = run_bash([RUN_HOOK.as_posix(), "guard_bash.py"], stdin="{}",
                 env_extra=launcher_env(tmp_path, PATH=bash_dir))
    assert r.returncode == 0
    assert "no usable Python" in r.stderr
    assert "INACTIVE" in r.stderr


# ---------------------------------------------------------------------------
# Launcher: pass-through semantics (an intentional block must stay a block)
# ---------------------------------------------------------------------------

def _tmp_launcher(tmp_path):
    """Copy the launcher into an isolated hooks dir we can add scripts to."""
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    shutil.copy(RUN_HOOK, hooks / "run_hook.sh")
    return hooks


def test_exit_code_2_passes_through(tmp_path):
    hooks = _tmp_launcher(tmp_path)
    (hooks / "block2.py").write_text(
        "import sys; sys.stderr.write('DENY-MARKER'); sys.exit(2)\n"
    )
    r = run_bash([(hooks / "run_hook.sh").as_posix(), "block2.py"], stdin="{}",
                 env_extra=launcher_env(tmp_path))
    assert r.returncode == 2
    assert "DENY-MARKER" in r.stderr


def test_stdin_and_stdout_pass_through(tmp_path):
    hooks = _tmp_launcher(tmp_path)
    (hooks / "echo.py").write_text(
        "import json, sys; d = json.load(sys.stdin); print(d['marker'])\n"
    )
    r = run_bash([(hooks / "run_hook.sh").as_posix(), "echo.py"],
                 stdin='{"marker": "round-trip-ok"}',
                 env_extra=launcher_env(tmp_path))
    assert r.returncode == 0
    assert "round-trip-ok" in r.stdout


def test_sourced_env_prefix_form(tmp_path):
    """The exact invocation shape hooks.json registers: sourced into the
    wrapper shell (no extra process) with CLAUDE_HOOK_SCRIPT carrying the
    script name. exec must still replace the shell and the exit code must
    pass through."""
    hooks = _tmp_launcher(tmp_path)
    (hooks / "block2.py").write_text(
        "import sys; sys.stderr.write('DENY-MARKER'); sys.exit(2)\n"
    )
    cmd = 'CLAUDE_HOOK_SCRIPT=block2.py . "%s"' % (hooks / "run_hook.sh").as_posix()
    r = run_bash(["-c", cmd], stdin="{}", env_extra=launcher_env(tmp_path))
    assert r.returncode == 2
    assert "DENY-MARKER" in r.stderr


def test_sourced_form_missing_script_fails_open(tmp_path):
    cmd = ('CLAUDE_HOOK_SCRIPT=no_such_hook.py . "%s"' % RUN_HOOK.as_posix())
    r = run_bash(["-c", cmd], stdin="{}", env_extra=launcher_env(tmp_path))
    assert r.returncode == 0
    assert "INACTIVE" in r.stderr


def test_hooks_json_registers_sourced_launcher_form():
    """Every python hook registration must use the sourced env-prefix form —
    `bash run_hook.sh` would spawn a second MSYS bash (seconds under load),
    and a direct `python x.py` re-opens the exit-2-on-missing-file deny."""
    import json
    d = json.loads((HOOKS_DIR / "hooks.json").read_text())["hooks"]
    py_cmds = [
        h["command"]
        for event in d.values()
        for m in event
        for h in m["hooks"]
        if ".py" in h["command"]
    ]
    assert py_cmds, "expected python hook registrations"
    for cmd in py_cmds:
        script = cmd.split("=", 1)[1].split(" ", 1)[0]
        assert cmd == (
            'CLAUDE_HOOK_SCRIPT=%s . "${CLAUDE_PLUGIN_ROOT}/hooks/run_hook.sh"'
            % script), cmd
        assert (HOOKS_DIR / script).is_file(), f"registered {script} missing"


def test_interpreter_is_cached_and_stale_cache_recovers(tmp_path):
    hooks = _tmp_launcher(tmp_path)
    (hooks / "ok.py").write_text("print('ok')\n")
    env = launcher_env(tmp_path)

    r = run_bash([(hooks / "run_hook.sh").as_posix(), "ok.py"], stdin="{}",
                 env_extra=env)
    assert r.returncode == 0
    cache = cache_file(tmp_path)
    assert cache.is_file() and cache.read_text().strip()

    # A cached interpreter that no longer resolves must trigger a re-probe,
    # not an error.
    cache.write_text("definitely-not-a-real-binary-xyz\n")
    r = run_bash([(hooks / "run_hook.sh").as_posix(), "ok.py"], stdin="{}",
                 env_extra=env)
    assert r.returncode == 0
    assert "ok" in r.stdout
    assert "definitely-not" not in cache.read_text()


# ---------------------------------------------------------------------------
# Legacy shims: stale pre-port sessions keep their guards
# ---------------------------------------------------------------------------

def test_all_legacy_shims_exist():
    for name in list(DELEGATING_SHIMS) + NOOP_SHIMS:
        assert (HOOKS_DIR / name).is_file(), f"missing legacy shim {name}"


def test_legacy_destructive_shim_still_blocks(tmp_path):
    payload = '{"tool_input": {"command": "rm -rf /some/dir"}}'
    r = run_bash([(HOOKS_DIR / "guard-destructive.sh").as_posix()],
                 stdin=payload, env_extra=launcher_env(tmp_path),
                 cwd=str(tmp_path))
    assert r.returncode == 2


def test_legacy_delegating_shims_allow_benign_input(tmp_path):
    benign = {
        "guard-destructive.sh": '{"tool_input": {"command": "echo hi"}}',
        "guard-edits.sh":
            '{"tool_input": {"file_path": "%s"}}' % (tmp_path / "a.txt").as_posix(),
        "guard-approve.sh": '{"prompt": "hello"}',
        "ask-question-approval.sh": '{"tool_input": {}, "tool_response": {}}',
        "consume-approval.sh": '{"tool_name": "Bash", "tool_input": {}}',
    }
    for name, payload in benign.items():
        r = run_bash([(HOOKS_DIR / name).as_posix()], stdin=payload,
                     env_extra=launcher_env(tmp_path), cwd=str(tmp_path))
        assert r.returncode == 0, f"{name}: rc={r.returncode} stderr={r.stderr}"


def test_legacy_noop_shims_are_silent(tmp_path):
    for name in NOOP_SHIMS:
        r = run_bash([(HOOKS_DIR / name).as_posix()],
                     stdin='{"tool_input": {"command": "echo hi"}}',
                     env_extra=launcher_env(tmp_path), cwd=str(tmp_path))
        assert r.returncode == 0, f"{name}: rc={r.returncode} stderr={r.stderr}"
        assert r.stdout.strip() == ""


# ---------------------------------------------------------------------------
# Cross-plugin copy stays in sync (dev-repo layout only)
# ---------------------------------------------------------------------------

def test_taskmaster_launcher_copy_in_sync():
    sibling = HOOKS_DIR.parents[2] / "taskmaster" / "hooks" / "run_hook.sh"
    if not sibling.exists():
        pytest.skip("taskmaster sibling not present (distributed install)")
    assert sibling.read_bytes() == RUN_HOOK.read_bytes(), (
        "run_hook.sh diverged between guard-hooks and taskmaster — "
        "edit both copies together"
    )
