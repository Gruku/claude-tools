# -*- coding: utf-8 -*-
"""Pytest suite for the guard-hooks Python hooks.

Port of the bash test suites (guard-destructive.test.sh, guard-database.test.sh,
guard-system-paths.test.sh, guard-git-internals.test.sh). Every bash test case
is preserved. Each test pipes a hook-JSON payload into the python script via
subprocess and asserts exit code (and, where it disambiguates, stderr content).

Consolidation notes (guard_bash.py runs all four guards sequentially,
first-block-wins — equivalent to the previous parallel-any-blocks bash setup):

* Cases that a SINGLE bash guard allowed but another guard blocks (e.g. the
  git-internals false-positive fixtures `rm -rf myrepo.git`) are now blocked
  by guard 1 (destructive). Those tests assert exit 2 AND that the stderr is
  NOT the git-internals message — preserving the original intent (no .git/
  false positive) under system semantics.
* The git-internals denial-logging test uses `mv .git foo` (a command only
  the git-internals guard blocks) so the log assertion still exercises that
  guard; the original `rm -rf .git` is blocked earlier by the destructive
  guard before git-internals runs.
* The approval-lifecycle tests use `~/.claude/guard-approve-default` — the
  per-session token the 2.7.x hooks actually check when the payload carries
  no session_id. (The old bash tests touched the unsuffixed `guard-approve`,
  which the 2.7.0 bash hooks never read — stale relative to the per-session
  keying.)
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
GUARD_BASH = HOOKS_DIR / "guard_bash.py"
GUARD_EDITS = HOOKS_DIR / "guard_edits.py"
GUARD_APPROVE = HOOKS_DIR / "guard_approve.py"
ASK_QUESTION_APPROVAL = HOOKS_DIR / "ask_question_approval.py"
CONSUME_APPROVAL = HOOKS_DIR / "consume_approval.py"

GITINT_MARKER = "targeting .git/"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_hook(script, payload, home, cwd=None):
    """Run a hook script with `payload` (dict -> JSON, str -> raw) on stdin,
    HOME/USERPROFILE pointed at the isolated `home` dir."""
    env = os.environ.copy()
    env["HOME"] = str(home)
    env["USERPROFILE"] = str(home)
    stdin = json.dumps(payload) if isinstance(payload, dict) else payload
    return subprocess.run(
        [sys.executable, str(script)],
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        cwd=str(cwd if cwd is not None else home),
    )


def run_bash_guard(command, home, cwd=None, payload_cwd=None):
    payload = {"tool_input": {"command": command}}
    if payload_cwd is not None:
        payload["cwd"] = str(payload_cwd)
    return run_hook(GUARD_BASH, payload, home, cwd=cwd)


def approve_path(home):
    return Path(home) / ".claude" / "guard-approve-default"


def ack_path(home):
    return Path(home) / ".claude" / "guard-ack-default"


@pytest.fixture
def home(tmp_path):
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    return h


def _check(proc, expect_blocked, desc):
    if expect_blocked:
        assert proc.returncode == 2, (
            "{} — expected block (2), got {} (stderr: {})".format(
                desc, proc.returncode, proc.stderr)
        )
    else:
        assert proc.returncode == 0, (
            "{} — expected allow (0), got {} (stderr: {})".format(
                desc, proc.returncode, proc.stderr)
        )


# ---------------------------------------------------------------------------
# guard_bash — destructive guard (port of guard-destructive.test.sh)
# ---------------------------------------------------------------------------

DESTRUCTIVE_CASES = [
    # -- push refspec destination check --
    # Pushing main/master directly is still blocked.
    ("git push origin master", "git push origin master", True),
    ("git push origin main", "git push origin main", True),
    ("git push origin HEAD:master", "git push origin HEAD:master", True),
    ("git push origin HEAD:main", "git push origin HEAD:main", True),
    ("git push origin feature:main", "git push origin feature:main", True),
    ("git push origin +feature:master", "git push origin +feature:master", True),
    ("git push origin :main (delete)", "git push origin :main", True),
    ("git push origin refs/heads/master", "git push origin refs/heads/master", True),
    # Pushing FROM master TO a feature branch is fine — master is the source side.
    ("push master:fix-branch", "git push origin master:fix-branch", False),
    ("push master:feature/foo", "git push origin master:feature/foo", False),
    ("push main:work-branch", "git push origin main:work-branch", False),
    ("push -u origin master:fix", "git push -u origin master:fix", False),
    ("push to feature ref", "git push origin feature-branch", False),
    ("push refs/heads/master:dst", "git push origin refs/heads/master:dst", False),
    # Force flag still blocks.
    ("force push to feature", "git push --force origin feature", True),
    ("force push -f", "git push -f origin feature", True),
    # Commit messages mentioning master should not false-positive (push
    # extraction stops at && | ;).
    ("commit msg with 'master'",
     "git commit -m 'rename master loop' && git push origin feature", False),
    # -- git worktree remove --force (Windows cascade hazard) --
    ("worktree remove --force", "git worktree remove --force .worktrees/foo", True),
    ("worktree remove -f", "git worktree remove -f .worktrees/foo", True),
    ("worktree remove -fq combined", "git worktree remove -fq .worktrees/foo", True),
    ("worktree remove --force after path", "git worktree remove .worktrees/foo --force", True),
    ("git -C <path> worktree remove --force",
     "git -C /repo worktree remove --force .worktrees/foo", True),
    # Non-force variants and unrelated worktree subcommands stay allowed.
    ("worktree remove (no force)", "git worktree remove .worktrees/foo", False),
    ("worktree prune", "git worktree prune", False),
    ("worktree list", "git worktree list", False),
    ("worktree add (out of scope)", "git worktree add /tmp/wt feature", False),
    # Path containing '-f' substring must NOT false-positive as the -f flag.
    ("remove path with -f in name", "git worktree remove .worktrees/desktop-app-258", False),
    ("remove path feature-foo", "git worktree remove .worktrees/feature-foo", False),
    # Sanity: a 'feature' branch named *-force is fine to push (no worktree verb).
    ("push feature/--force-named", "git push origin feature/force-disable", False),
    # -- destructive git ops piped through line filters (failure-masking) --
    ("worktree remove | tail", "git worktree remove .worktrees/foo 2>&1 | tail -2", True),
    ("worktree remove | head", "git worktree remove .worktrees/foo 2>&1 | head -3", True),
    ("worktree remove | grep", "git worktree remove .worktrees/foo 2>&1 | grep fatal", True),
    ("git push | tail", "git push origin feature 2>&1 | tail -5", True),
    ("git reset | head", "git reset HEAD~3 2>&1 | head", True),
    ("git clean | wc -l", "git clean -fd 2>&1 | wc -l", True),
    ("chained worktree remove | tail",
     "git worktree remove A 2>&1 | tail -2 && git worktree remove B 2>&1 | tail -2", True),
    # Read-only git commands piped through filters stay allowed.
    ("git log | head", "git log --oneline | head -10", False),
    ("git status | grep", "git status -s | grep modified", False),
    ("git branch | head", "git branch | head", False),
    ("git diff | wc -l", "git diff --stat | wc -l", False),
    # Destructive git WITHOUT a filter remains as governed by the other rules.
    ("git push feature (no filter)", "git push origin feature", False),
    # Destructive command, filter is BEFORE git (different segment).
    ("echo x | tee && git push", "echo x | tee log.txt && git push origin feature", False),
]


@pytest.mark.parametrize(
    "desc,command,blocked", DESTRUCTIVE_CASES, ids=[c[0] for c in DESTRUCTIVE_CASES]
)
def test_destructive(desc, command, blocked, home):
    _check(run_bash_guard(command, home), blocked, desc)


class TestWorktreePreflight:
    """-- git worktree remove pre-flight: submodule-containing target --"""

    @pytest.fixture
    def fixture_repo(self, tmp_path):
        repo = tmp_path / "fixture-repo"
        (repo / ".worktrees" / "wt-with-subs").mkdir(parents=True)
        (repo / ".worktrees" / "wt-with-subs" / ".gitmodules").write_text(
            '[submodule "foo"]\n'
        )
        (repo / ".worktrees" / "wt-no-subs").mkdir(parents=True)
        return repo

    def test_no_cwd_relative_path(self, home, fixture_repo):
        # Without cwd, relative path can't be resolved → hook can't pre-flight → allow.
        proc = run_bash_guard("git worktree remove .worktrees/wt-with-subs", home)
        _check(proc, False, "no cwd, relative path")

    def test_relative_path_submodule_target(self, home, fixture_repo):
        # With cwd pointing at the fixture repo, the relative path resolves and
        # .gitmodules is found → approval-gated.
        proc = run_bash_guard(
            "git worktree remove .worktrees/wt-with-subs", home,
            payload_cwd=fixture_repo,
        )
        _check(proc, True, "relative path, submodule target")

    def test_absolute_path_submodule_target(self, home, fixture_repo):
        target = (fixture_repo / ".worktrees" / "wt-with-subs").as_posix()
        proc = run_bash_guard(
            "git worktree remove {}".format(target), home, payload_cwd=fixture_repo
        )
        _check(proc, True, "absolute path, submodule target")

    def test_relative_path_no_submodules(self, home, fixture_repo):
        proc = run_bash_guard(
            "git worktree remove .worktrees/wt-no-subs", home,
            payload_cwd=fixture_repo,
        )
        _check(proc, False, "relative path, no submodules")

    def test_non_existent_target(self, home, fixture_repo):
        # Path that does not exist (typo, already-removed) → allowed.
        proc = run_bash_guard(
            "git worktree remove .worktrees/does-not-exist", home,
            payload_cwd=fixture_repo,
        )
        _check(proc, False, "non-existent target")

    def test_worktree_list_with_cwd(self, home, fixture_repo):
        proc = run_bash_guard("git worktree list", home, payload_cwd=fixture_repo)
        _check(proc, False, "worktree list with cwd")

    def test_worktree_prune_with_cwd(self, home, fixture_repo):
        proc = run_bash_guard("git worktree prune", home, payload_cwd=fixture_repo)
        _check(proc, False, "worktree prune with cwd")


class TestApprovalLifecycle:
    """-- approval lifecycle (PostToolUse consumer) --"""

    def test_lifecycle(self, home):
        # A fresh approval lets a blocked command through but the PreToolUse
        # hook does NOT delete the file — only the PostToolUse consumer does.
        approve_path(home).touch()
        proc = run_bash_guard("rm -rf /tmp/foo", home)
        assert proc.returncode == 0, (
            "approval allows blocked cmd — expected allow, got {} (stderr: {})".format(
                proc.returncode, proc.stderr)
        )
        assert approve_path(home).is_file(), (
            "approval file deleted by PreToolUse (should persist until PostToolUse)"
        )

        # Subsequent attempt within window still allowed (simulates: hook
        # approved, permission layer denied, no PostToolUse fired, AI retries).
        proc = run_bash_guard("rm -rf /tmp/foo", home)
        assert proc.returncode == 0, "retry within window — expected allow"

        # After PostToolUse consumer runs, the approval is gone.
        run_hook(CONSUME_APPROVAL, {}, home)
        assert not approve_path(home).exists(), (
            "PostToolUse consumer did not delete approval"
        )

        # Next attempt blocks again.
        proc = run_bash_guard("rm -rf /tmp/foo", home)
        assert proc.returncode == 2, "post-consume — expected block (2)"

    def test_expired_approval(self, home):
        # Expired approval (>60s) is cleaned up by PreToolUse and does not allow.
        approve_path(home).touch()
        expired = time.time() - 120
        os.utime(str(approve_path(home)), (expired, expired))
        proc = run_bash_guard("rm -rf /tmp/foo", home)
        assert proc.returncode == 2, "expired approval — expected block (2)"
        assert not approve_path(home).exists(), "expired approval not cleaned up"


# ---------------------------------------------------------------------------
# guard_bash — database guard (port of guard-database.test.sh)
# ---------------------------------------------------------------------------

DATABASE_CASES = [
    # -- skeleton --
    ("empty command", "", False),
    ("harmless command", "ls -la", False),
    ("AI cannot create guard-approve", "touch ~/.claude/guard-approve", True),
    # ("AI cannot create guard-approve via echo") built per-home below.
    # ("AI may create guard-ack") built per-home below.
    # -- sql schema --
    ("psql DROP DATABASE", 'psql -c "DROP DATABASE foo"', True),
    ("psql DROP SCHEMA", 'psql -c "DROP SCHEMA public CASCADE"', True),
    ("mysql DROP TABLE", 'mysql -e "DROP TABLE users"', True),
    ("sqlite TRUNCATE", 'sqlite3 my.db "TRUNCATE TABLE logs"', True),
    ("psql heredoc DROP TABLE", 'psql <<EOF\nDROP TABLE foo;\nEOF', True),
    ("select with drop in name", 'psql -c "SELECT * FROM table_with_drop_in_name"', False),
    ("create table", 'psql -c "CREATE TABLE foo (id int)"', False),
    # -- unbounded dml --
    ("DELETE FROM no WHERE", 'psql -c "DELETE FROM users;"', True),
    ("UPDATE no WHERE", 'mysql -e "UPDATE users SET active=0;"', True),
    ("DELETE WITH WHERE", 'psql -c "DELETE FROM users WHERE id=1;"', False),
    ("UPDATE WITH WHERE", 'psql -c "UPDATE users SET active=0 WHERE id=1;"', False),
    ("SELECT not affected", 'psql -c "SELECT * FROM users;"', False),
    # CTE-wrapped statements: closing paren is the terminator, and a WHERE
    # after the CTE belongs to the outer SELECT, not the inner DELETE/UPDATE.
    ("CTE DELETE no WHERE", 'psql -c "WITH x AS (DELETE FROM users) SELECT 1"', True),
    ("CTE UPDATE outer WHERE",
     'psql -c "WITH x AS (UPDATE users SET active=0) SELECT * FROM y WHERE id=1"', True),
    ("CTE DELETE WITH WHERE",
     'psql -c "WITH x AS (DELETE FROM users WHERE id=1) SELECT 1"', False),
    # -- mongo --
    ("mongosh dropDatabase", 'mongosh --eval "db.dropDatabase()"', True),
    ("mongo legacy dropDatabase", 'mongo mydb --eval "db.dropDatabase()"', True),
    ("mongosh collection.drop", 'mongosh --eval "db.users.drop()"', True),
    ("mongosh deleteMany empty", 'mongosh --eval "db.users.deleteMany({})"', True),
    ("mongosh find", 'mongosh --eval "db.users.find({})"', False),
    ("mongosh deleteMany scoped", 'mongosh --eval "db.users.deleteMany({status: \\"x\\"})"', False),
    # -- redis --
    ("redis-cli FLUSHALL", 'redis-cli FLUSHALL', True),
    ("redis-cli flushall lower", 'redis-cli flushall', True),
    ("redis-cli FLUSHDB", 'redis-cli FLUSHDB', True),
    ("redis-cli with host flushall", 'redis-cli -h prod.example.com FLUSHALL', True),
    ("redis-cli get", 'redis-cli GET mykey', False),
    ("redis-cli info", 'redis-cli INFO', False),
    # -- supabase --
    ("supabase db reset", 'supabase db reset', True),
    ("npx supabase db reset", 'npx supabase db reset', True),
    ("supabase projects delete", 'supabase projects delete abc123', True),
    ("supabase db push", 'supabase db push', True),
    ("supabase db diff", 'supabase db diff', False),
    ("supabase status", 'supabase status', False),
    # -- docker --
    # HARD
    ("compose down -v", 'docker compose down -v', True),
    ("compose down --volumes", 'docker compose down --volumes', True),
    ("docker-compose down -v", 'docker-compose down -v', True),
    ("volume rm", 'docker volume rm pgdata', True),
    ("volume prune", 'docker volume prune -f', True),
    ("system prune --volumes", 'docker system prune --volumes', True),
    ("system prune -a", 'docker system prune -a', True),
    ("system prune -af", 'docker system prune -af', True),
    ("system prune -fa", 'docker system prune -fa', True),
    # SOFT
    ("docker rm -v", 'docker rm -v old_container', True),
    ("docker stop pg container", 'docker stop my-postgres', True),
    ("docker kill mongo", 'docker kill mongo-dev', True),
    ("docker rm redis container", 'docker rm redis-cache', True),
    # ALLOW
    ("compose up", 'docker compose up -d', False),
    ("compose down (no -v)", 'docker compose down', False),
    ("docker stop unrelated", 'docker stop my-app', False),
    ("docker ps", 'docker ps -a', False),
]


@pytest.mark.parametrize(
    "desc,command,blocked", DATABASE_CASES, ids=[c[0] for c in DATABASE_CASES]
)
def test_database(desc, command, blocked, home):
    _check(run_bash_guard(command, home), blocked, desc)


def test_database_guard_approve_via_echo(home):
    proc = run_bash_guard("echo x > {}/.claude/guard-approve".format(home.as_posix()), home)
    _check(proc, True, "AI cannot create guard-approve via echo")


def test_database_guard_ack_allowed(home):
    proc = run_bash_guard("touch {}/.claude/guard-ack".format(home.as_posix()), home)
    _check(proc, False, "AI may create guard-ack")


class TestAckSentinel:
    """Soft-block self-ack flow: `: guard-ack-self` records a per-session ack."""

    def test_soft_block_then_ack_then_allow(self, home):
        soft_cmd = 'psql -c "DELETE FROM users;"'
        proc = run_bash_guard(soft_cmd, home)
        assert proc.returncode == 2
        assert "SOFT — AI self-ack permitted" in proc.stderr

        # The sentinel itself is allowed and creates the ack file.
        proc = run_bash_guard(": guard-ack-self", home)
        assert proc.returncode == 0
        assert ack_path(home).is_file(), "ack file not created by sentinel"

        # Re-run within the window — soft block bypassed.
        proc = run_bash_guard(soft_cmd, home)
        assert proc.returncode == 0

        # Consumer deletes the ack; next attempt blocks again.
        run_hook(CONSUME_APPROVAL, {}, home)
        assert not ack_path(home).exists()
        proc = run_bash_guard(soft_cmd, home)
        assert proc.returncode == 2

    def test_ack_does_not_bypass_hard_block(self, home):
        run_bash_guard(": guard-ack-self", home)
        assert ack_path(home).is_file()
        proc = run_bash_guard('psql -c "DROP DATABASE foo"', home)
        assert proc.returncode == 2, "ack must not bypass a HARD db block"


# ---------------------------------------------------------------------------
# guard_bash — system-paths guard (port of guard-system-paths.test.sh)
# ---------------------------------------------------------------------------

SYSPATH_CASES = [
    # -- baseline (no system path or no destructive verb) --
    ("empty command", "", False),
    ("ls -la", "ls -la", False),
    ("ls /bin (read-only)", "ls /bin", False),
    ("cat /etc/hostname", "cat /etc/hostname", False),
    ("find /usr/bin -name foo", "find /usr/bin -name foo", False),
    ("Get-ChildItem windows", 'Get-ChildItem C:\\Windows', False),
    ("Test-Path windows file", 'Test-Path C:\\Windows\\System32\\powershell.exe', False),
    ("rm against user file", "rm /tmp/foo.txt", False),
    ("mv user dirs", "mv ~/foo ~/bar", False),
    # -- AI cannot create approval file --
    ("AI touches guard-approve", "touch ~/.claude/guard-approve", True),
    ("AI echoes guard-approve", 'echo x > $HOME/.claude/guard-approve', True),
    # -- windows powershell --
    ("Rename-Item powershell.exe",
     'Rename-Item C:\\Windows\\System32\\powershell.exe powershell-old.exe', True),
    ("Remove-Item windows file", 'Remove-Item C:\\Windows\\System32\\foo.exe', True),
    ("Move-Item windows file", 'Move-Item C:\\Windows\\System32\\foo.exe C:\\Temp\\', True),
    ("Copy-Item -Force windows",
     'Copy-Item -Force C:\\Temp\\foo.exe C:\\Windows\\System32\\foo.exe', True),
    ("Set-Content into windows", 'Set-Content C:\\Windows\\System32\\foo.txt "hi"', True),
    ("icacls system32", 'icacls C:\\Windows\\System32 /grant Everyone:F', True),
    ("takeown system32", 'takeown /f C:\\Windows\\System32\\foo.exe', True),
    ("env:SystemRoot", 'Remove-Item $env:SystemRoot\\System32\\foo.exe', True),
    # -- powershell case insensitivity (PS is case-insensitive) --
    ("remove-item lowercase", 'remove-item C:\\Windows\\System32\\powershell.exe', True),
    ("REMOVE-ITEM uppercase", 'REMOVE-ITEM C:\\Windows\\System32\\powershell.exe', True),
    ("rename-Item mixed", 'rename-Item C:\\Windows\\System32\\foo.exe foo-old.exe', True),
    ("move-item lowercase", 'move-item C:\\Windows\\System32\\foo.exe C:\\Temp\\', True),
    # -- UNC / extended-length / device-namespace prefixes --
    ("UNC ext-length Remove-Item", 'Remove-Item \\\\?\\C:\\Windows\\System32\\powershell.exe', True),
    ("UNC device-ns del", 'del \\\\.\\C:\\Windows\\System32\\foo.exe', True),
    ("UNC ext-length program files", 'Remove-Item "\\\\?\\C:\\Program Files\\App\\foo.exe"', True),
    ("UNC ext-length lowercase", 'remove-item \\\\?\\c:\\windows\\system32\\foo.exe', True),
    # -- windows cmd --
    ("del system32", 'del C:\\Windows\\System32\\foo.exe', True),
    ("ren system32", 'ren C:\\Windows\\System32\\foo.exe foo-old.exe', True),
    ("rename system32", 'rename C:\\Windows\\System32\\foo.exe foo-old.exe', True),
    ("move system32", 'move C:\\Windows\\System32\\foo.exe D:\\', True),
    ("rd /s windows", 'rd /s /q C:\\Windows\\System32\\foo', True),
    ("program files", 'del "C:\\Program Files\\App\\foo.exe"', True),
    ("program files x86", 'del "C:\\Program Files (x86)\\App\\foo.exe"', True),
    ("%SystemRoot%", 'del %SystemRoot%\\System32\\foo.exe', True),
    ("%WINDIR%", 'del %WINDIR%\\System32\\foo.exe', True),
    # -- unix linux --
    ("rm /usr/bin/python", "rm /usr/bin/python", True),
    ("rm -rf /bin/sh", "rm -rf /bin/sh", True),
    ("rm /sbin/init", "rm /sbin/init", True),
    ("mv /etc/passwd", "mv /etc/passwd /tmp/passwd.old", True),
    ("chmod 777 /etc/passwd", "chmod 777 /etc/passwd", True),
    ("chown root /usr/bin", "chown root /usr/bin/python", True),
    ("ln -sf into /usr/bin", "ln -sf /tmp/foo /usr/bin/python", True),
    ("redirect into /etc/hosts", "echo x > /etc/hosts", True),
    ("tee into /etc", "echo x | tee /etc/hosts", True),
    ("rm /usr/lib/foo", "rm /usr/lib/foo.so", True),
    ("rm /lib64/foo", "rm /lib64/foo.so", True),
    ("rm /boot/grub.cfg", "rm /boot/grub.cfg", True),
    # -- unix macos --
    ("rm /System/Library/Foo", "rm -rf /System/Library/Foo", True),
    ("mv /System/Library/Foo", "mv /System/Library/Foo /tmp/", True),
    # -- find -delete / -exec rm --
    ("find -delete in /etc", "find /etc -name '*.old' -delete", True),
    ("find -exec rm in /usr/bin", "find /usr/bin -name 'python*' -exec rm {} \\;", True),
    ("find -exec unlink", "find /usr/sbin -exec unlink {} \\;", True),
    ("find user dir -delete", "find ~/tmp -name '*.bak' -delete", False),
    # -- segment isolation --
    # A destructive verb in a different segment from the system path must NOT block.
    ("ls /bin && rm tmp.txt", "ls /bin && rm tmp.txt", False),
    ("echo /etc reference", 'echo "/etc/passwd is sensitive"', False),
    ("cat /etc/hosts && ls", "cat /etc/hosts && ls", False),
    # A destructive verb in the SAME segment as a system path MUST block.
    ("compound delete via &&", "echo hi && rm /usr/bin/python", True),
    ("compound delete via ;", "echo hi ; rm /usr/bin/python", True),
    ("pipe to tee /etc", "echo hi | tee /etc/hosts", True),
    # -- false-positive guards --
    ("rm against /etcd-data", "rm /etcd-data/foo", False),
    ("rm under ~/etc", "rm ~/etc/foo.conf", False),
    ("mv into /usr/binary-name", "mv foo /usr/binary-name", False),
    ("sed unrelated", "sed -i 's/foo/bar/' ~/file.txt", False),
    # -- ssh/scp/rsync remote wrapper exemption --
    ("ssh remote rm /etc", 'ssh root@example.com "rm /etc/foo"', False),
    ("ssh remote redirect to /root", 'ssh root@host "cat > /root/foo"', False),
    ("ssh -i flag, remote redirect", 'ssh -i ~/.ssh/key root@1.2.3.4 "cat > /etc/nginx/foo"', False),
    ("ssh.exe full path remote",
     '/c/Windows/System32/OpenSSH/ssh.exe -i ~/.ssh/k root@host "ls /etc/nginx"', False),
    ("scp into remote /etc", 'scp file root@host:/etc/foo', False),
    ("rsync into remote /etc", 'rsync -av file root@host:/etc/', False),
    # But ssh to localhost CAN affect this machine, so destructive ops must
    # still block. (Unquoted form — the verb regex requires shell word
    # boundaries, so the quoted variant is a known gap out of scope.)
    ("ssh root@localhost rm /etc", 'ssh root@localhost rm /etc/passwd', True),
    ("ssh 127.0.0.1 rm /usr/bin", 'ssh root@127.0.0.1 rm /usr/bin/python', True),
    ("ssh ::1 rm /etc", 'ssh root@[::1] rm /etc/foo', True),
    # -- ssh quoted-payload quote-aware splitting --
    # Operators (; | && ||) and redirects (>) INSIDE the ssh quoted argument
    # must not be split into local segments. The whole quoted block is remote.
    ("ssh remote ; chain in quotes", 'ssh root@host "echo a; ls /etc/nginx; ls /var/foo"', False),
    ("ssh remote 2>/dev/null in quotes", 'ssh root@host "ls -la /etc/nginx/ 2>/dev/null"', False),
    ("ssh remote pipe in quotes", 'ssh root@host "ps aux | grep -i task | grep -v grep"', False),
    ("ssh.exe full repro from bug",
     '/c/Windows/System32/OpenSSH/ssh.exe -i ~/.ssh/key root@1.2.3.4 '
     '"echo === a ===; ls -la /var/www/foo; echo; head -100 /var/www/foo/index.html; '
     'ls -la /etc/nginx/conf.d/ 2>/dev/null; ps aux | grep -v grep"', False),
    # Quote-awareness must not break legitimate compound detection: an
    # unquoted destructive op chained AFTER a quoted ssh payload still blocks.
    ("ssh remote then local rm /etc", 'ssh root@host "ls /etc/foo" && rm /etc/passwd', True),
    # -- system-path executable as first token --
    ("ssh.exe just invoked", '/c/Windows/System32/OpenSSH/ssh.exe -V', False),
    ("/usr/bin/git status", '/usr/bin/git status', False),
    ("ssh.exe via pipe", 'echo hi | /c/Windows/System32/OpenSSH/ssh.exe root@host cat', False),
    # Destructive verb against a system-path target still blocks even if the
    # exe itself happens to live in a system path.
    ("/usr/bin/rm against /etc", '/usr/bin/rm /etc/passwd', True),
]


@pytest.mark.parametrize(
    "desc,command,blocked", SYSPATH_CASES, ids=[c[0] for c in SYSPATH_CASES]
)
def test_system_paths(desc, command, blocked, home):
    _check(run_bash_guard(command, home), blocked, desc)


class TestSyspathApprovalBypass:
    """-- approval bypass --"""

    def test_approval_bypass_and_consume(self, home):
        approve_path(home).touch()
        proc = run_bash_guard("rm /usr/bin/python", home)
        _check(proc, False, "approval allows blocked cmd")
        # PreToolUse does NOT consume the approval — that's the PostToolUse
        # consumer's job. So a retry within the 60s window is still allowed.
        proc = run_bash_guard("rm /usr/bin/python", home)
        _check(proc, False, "approval persists for retry")
        # Simulate the PostToolUse consumer after the tool actually executed.
        run_hook(CONSUME_APPROVAL, {}, home)
        proc = run_bash_guard("rm /usr/bin/python", home)
        _check(proc, True, "post-consume blocks again")


def test_syspath_denial_logging(home):
    """-- denial logging --"""
    log_file = home / ".claude" / "logs" / "guard-system-paths.log"
    run_bash_guard("rm /usr/bin/python", home)
    assert log_file.is_file(), "denial log file not created"
    assert "rm /usr/bin/python" in log_file.read_text(encoding="utf-8"), (
        "denial not recorded in log file"
    )


# ---------------------------------------------------------------------------
# guard_bash — git-internals guard (port of guard-git-internals.test.sh)
# ---------------------------------------------------------------------------

GITINT_CASES = [
    # -- baseline (no .git or no destructive verb) --
    ("empty command", "", False),
    ("ls .git (read-only)", "ls .git", False),
    ("cat .git/HEAD", "cat .git/HEAD", False),
    ("git status", "git status", False),
    ("git log", "git log --oneline", False),
    ("git worktree remove (allowed)", "git worktree remove ../wt-foo", False),
    ("rm against unrelated file", "rm /tmp/foo.txt", False),
    ("rm against ~/.gitignore", "rm ~/.gitignore", False),
    ("Get-ChildItem .git", 'Get-ChildItem .git', False),
    ("find .git read-only", "find .git -type f", False),
    # -- unix rm/mv/cp targeting .git --
    ("rm -rf .git", "rm -rf .git", True),
    ("rm -rf ./.git", "rm -rf ./.git", True),
    ("rm -rf path/.git", "rm -rf src/.git", True),
    ("rm -rf .git/HEAD", "rm -rf .git/HEAD", True),
    ("rm -rf .git/objects", "rm -rf .git/objects", True),
    ("rm -rf with quoted .git", "rm -rf '.git'", True),
    ("rm -rf with double-quoted", 'rm -rf ".git"', True),
    ("rmdir .git", "rmdir .git", True),
    ("unlink .git/HEAD", "unlink .git/HEAD", True),
    ("shred .git/index", "shred .git/index", True),
    ("mv .git foo", "mv .git foo", True),
    ("mv .git/HEAD elsewhere", "mv .git/HEAD /tmp/HEAD.bak", True),
    ("cp overwrite .git/config", "cp /tmp/config .git/config", True),
    ("chmod 000 .git/HEAD", "chmod 000 .git/HEAD", True),
    ("chown root .git", "chown root:root .git", True),
    ("ln replace .git", "ln -sf /tmp/foo .git", True),
    ("tee into .git/HEAD", "echo x | tee .git/HEAD", True),
    ("truncate .git/index", "truncate -s 0 .git/index", True),
    # -- absolute-path invocation --
    ("/usr/bin/rm .git", "/usr/bin/rm -rf .git", True),
    ("/bin/rm .git/HEAD", "/bin/rm .git/HEAD", True),
    # -- output redirection into .git --
    ("echo > .git/HEAD", 'echo "" > .git/HEAD', True),
    ("echo >> .git/config", 'echo x >> .git/config', True),
    ("redirect into nested", 'echo x > .git/refs/heads/main', True),
    ("fd-prefixed redirect 2> path", 'cmd 2> .git/log', True),
    ("bash &> path", 'cmd &> .git/log', True),
    ("no-space > .git", 'echo x >.git/HEAD', True),
    # Real path redirect alongside an fd-dup must still block.
    ("mixed fd dup + path redirect", 'echo x 2>&1 > .git/HEAD', True),
    # -- fd duplication does NOT trigger redirect block --
    # These all appeared as false positives in the 2026-05-19 incident.
    ("ls .git 2>&1 | head", 'ls -la .git 2>&1 | head -10', False),
    ("cat path/.git 2>&1", 'cat foo/.git 2>&1 | head -3', False),
    ("find -name .git 2>&1", 'find . -maxdepth 4 -name ".git" 2>&1 | head -20', False),
    ("ls .git 1>&2", 'ls .git 1>&2', False),
    ("git status 2>&1", 'git status .git 2>&1', False),
    # -- windows cmd verbs --
    ("del .git\\HEAD", 'del .git\\HEAD', True),
    ("del /s /q .git", 'del /s /q .git', True),
    ("rd /s /q .git", 'rd /s /q .git', True),
    ("rmdir /s .git", 'rmdir /s /q .git', True),
    ("move .git foo", 'move .git foo', True),
    ("ren .git old", 'ren .git .git-old', True),
    ("rename .git old", 'rename .git .git-old', True),
    # -- powershell cmdlets --
    ("Remove-Item .git", 'Remove-Item -Recurse -Force .git', True),
    ("Remove-Item .git/HEAD", 'Remove-Item .git/HEAD', True),
    ("Remove-Item .git\\HEAD", 'Remove-Item .git\\HEAD', True),
    ("Move-Item .git", 'Move-Item .git foo', True),
    ("Rename-Item .git", 'Rename-Item .git .git-old', True),
    ("Set-Content .git/HEAD", 'Set-Content .git/HEAD "ref: foo"', True),
    ("Clear-Content .git/index", 'Clear-Content .git/index', True),
    ("Out-File .git/HEAD", 'Out-File .git/HEAD', True),
    # -- powershell case insensitivity --
    ("remove-item lowercase", 'remove-item -recurse -force .git', True),
    ("REMOVE-ITEM uppercase", 'REMOVE-ITEM .git', True),
    ("Move-item mixed case", 'Move-item .git foo', True),
    # -- find -delete / -exec --
    ("find .git -delete", "find .git -delete", True),
    ("find . -name .git -delete", "find . -name .git -delete", True),
    ("find .git -exec rm", "find .git -type f -exec rm {} \\;", True),
    ("find -exec rm with .git arg", "find . -name HEAD -exec rm .git/HEAD \\;", True),
    # -- segment isolation --
    # Destructive verb in a different segment from .git must NOT block.
    ("ls .git && rm tmp.txt", "ls .git && rm tmp.txt", False),
    ("cat .git/HEAD && ls", "cat .git/HEAD && ls", False),
    ("echo .git mention", 'echo "do not touch .git here"', False),
    # Same segment still blocks.
    ("compound rm via &&", "echo hi && rm -rf .git", True),
    ("compound rm via ;", "echo hi ; rm -rf .git", True),
    ("pipe to tee .git/HEAD", "echo hi | tee .git/HEAD", True),
    # -- false-positive guards --
    # Strings that contain ".git" as a suffix or substring but aren't the
    # target. (The `rm -rf` variants are asserted separately below — the
    # destructive guard blocks any `rm -rf`, but the git-internals guard
    # must NOT be the one firing.)
    ("rm .gitignore", "rm .gitignore", False),
    ("rm .gitattributes", "rm .gitattributes", False),
    ("rm .gitmodules", "rm .gitmodules", False),
    ("echo .gitignore via tee", "echo x | tee .gitignore", False),
    ("Set-Content .gitignore", 'Set-Content .gitignore "node_modules"', False),
    ("echo .git in string", 'echo "the .git directory is special"', False),
    # -- ssh/scp/rsync remote exemption --
    # .git on a remote host is the remote's problem, not ours.
    ("ssh remote rm .git", 'ssh root@host "rm -rf .git"', False),
    ("scp into remote .git", 'scp file root@host:.git/HEAD', False),
    ("rsync into remote .git", 'rsync -av file root@host:.git/', False),
]


@pytest.mark.parametrize(
    "desc,command,blocked", GITINT_CASES, ids=[c[0] for c in GITINT_CASES]
)
def test_git_internals(desc, command, blocked, home):
    _check(run_bash_guard(command, home), blocked, desc)


GITINT_FALSE_POSITIVE_RM_RF = [
    # Original bash expectation: ALLOWED by guard-git-internals.sh alone.
    # In the consolidated script the destructive guard blocks any `rm -rf`
    # (matching the old parallel system behavior). Preserve the original
    # intent — no .git/ false positive — by asserting the git-internals
    # message is NOT the one emitted.
    ("rm repo.git (bare clone)", "rm -rf myrepo.git"),
    ("rm .git-old (renamed away)", "rm -rf .git-old"),
    ("rm path/foo.git/objects", "rm -rf path/foo.git/objects"),
]


@pytest.mark.parametrize(
    "desc,command", GITINT_FALSE_POSITIVE_RM_RF,
    ids=[c[0] for c in GITINT_FALSE_POSITIVE_RM_RF],
)
def test_git_internals_rm_rf_false_positives(desc, command, home):
    proc = run_bash_guard(command, home)
    assert proc.returncode == 2, "{} — destructive guard should block rm -rf".format(desc)
    assert GITINT_MARKER not in proc.stderr, (
        "{} — git-internals guard false-positived on a non-.git path".format(desc)
    )
    assert "Destructive file deletion" in proc.stderr


def test_git_internals_no_approval_bypass(home):
    """-- no approval bypass (hard block) --
    The user explicitly creates the approval file, but the .git/ rule must
    still block (the destructive guard passes via approval; git-internals
    hard-blocks)."""
    approve_path(home).touch()
    proc = run_bash_guard("rm -rf .git", home)
    assert proc.returncode == 2, "approval does NOT bypass"
    assert GITINT_MARKER in proc.stderr
    # Approval file should be untouched (this rule does not consume it).
    assert approve_path(home).is_file(), (
        "approval file was consumed (should not be — hook is hard-block)"
    )


def test_git_internals_denial_logging(home):
    """-- denial logging -- (uses `mv .git foo`: only the git-internals guard
    blocks it, so the log assertion exercises that guard — see module
    docstring)."""
    log_file = home / ".claude" / "logs" / "guard-git-internals.log"
    proc = run_bash_guard("mv .git foo", home)
    assert proc.returncode == 2
    assert log_file.is_file(), "denial log file not created"
    assert "mv .git foo" in log_file.read_text(encoding="utf-8"), (
        "denial not recorded in log file"
    )


def test_bless_marker_redirect_allowed(home):
    """Redirection into the review-gate blessing marker is permitted."""
    proc = run_bash_guard("git rev-parse HEAD > .git/CLAUDE_REVIEW_GATE_OK", home)
    _check(proc, False, "bless marker redirect")


# ---------------------------------------------------------------------------
# guard_bash — input handling and exact block-message wording
# ---------------------------------------------------------------------------

def test_empty_stdin_allows(home):
    proc = run_hook(GUARD_BASH, "", home)
    assert proc.returncode == 0


def test_malformed_stdin_allows(home):
    proc = run_hook(GUARD_BASH, "{not json", home)
    assert proc.returncode == 0


def test_no_command_allows(home):
    proc = run_hook(GUARD_BASH, {"tool_input": {}}, home)
    assert proc.returncode == 0


def test_session_keyed_approval(home):
    """Approval tokens are keyed by session_id."""
    (home / ".claude" / "guard-approve-sess42").touch()
    payload = {"tool_input": {"command": "rm -rf /tmp/foo"}, "session_id": "sess42"}
    proc = run_hook(GUARD_BASH, payload, home)
    assert proc.returncode == 0
    # A different session does not see that approval.
    payload["session_id"] = "other"
    proc = run_hook(GUARD_BASH, payload, home)
    assert proc.returncode == 2


EXPECTED_DESTRUCTIVE_MESSAGE = """⛔ GUARD HOOK BLOCKED THIS COMMAND.
Reason: Destructive file deletion ('rm -rf /tmp/x'). Use 'git worktree remove' for worktrees.
Command: rm -rf /tmp/x

ACTION REQUIRED: Use the AskUserQuestion tool with EXACTLY this shape:
  question: one short sentence describing the destructive action
  options (use these labels verbatim — do not rename, translate, or add more):
    - label: "Approve"  description: "Run the command as shown"
    - label: "Deny"     description: "Cancel; do not run the command"

After the user responds:
  - "Approve" → rerun the ORIGINAL command unchanged
  - "Deny" or no response → do NOT run the command

Only the exact label "Approve" is recognized as authorization.
Do NOT re-run automatically. Do NOT create the approval file yourself.
"""


def test_destructive_block_message_exact(home):
    """The block wording is referenced by other skills/docs — lock it
    character-for-character (mirrors the bash heredoc)."""
    proc = run_bash_guard("rm -rf /tmp/x", home)
    assert proc.returncode == 2
    assert proc.stderr == EXPECTED_DESTRUCTIVE_MESSAGE


def test_approve_mutation_block_message_exact(home):
    proc = run_bash_guard("touch ~/.claude/guard-approve", home)
    assert proc.returncode == 2
    assert proc.stderr == (
        "⛔ GUARD HOOK BLOCKED THIS COMMAND.\n"
        "Reason: You cannot create or manipulate the guard approval file. "
        "Only the user can do this manually.\n"
    )


# ---------------------------------------------------------------------------
# guard_edits (smoke coverage — the bash suite had no guard-edits tests)
# ---------------------------------------------------------------------------

def run_edits(file_path, home):
    return run_hook(GUARD_EDITS, {"tool_input": {"file_path": file_path}}, home)


EDITS_CASES = [
    ("normal source file", "/home/user/project/src/main.py", False),
    ("normal windows file", "C:/repo/src/component.tsx", False),
    ("guard-approve file (hard)", "/home/user/.claude/guard-approve", True),
    (".env file", "/project/.env", True),
    (".env.development", "/project/.env.development", True),
    (".env.example allowed", "/project/.env.example", False),
    ("credentials file", "/project/aws-credentials", True),
    ("pem file", "/project/server.pem", True),
    ("package-lock.json", "/project/package-lock.json", True),
    ("uv.lock", "/project/uv.lock", True),
    ("git internals (hard)", "/repo/.git/config", True),
    ("bless marker allowed", "/repo/.git/CLAUDE_REVIEW_GATE_OK", False),
    ("windows system path (hard)", "C:\\Windows\\System32\\drivers\\etc\\foo", True),
    ("program files (hard)", "C:\\Program Files\\App\\config.ini", True),
    ("unix system path (hard)", "/etc/hosts", True),
    ("usr bin (hard)", "/usr/bin/python", True),
    ("empty file_path", "", False),
]


@pytest.mark.parametrize(
    "desc,file_path,blocked", EDITS_CASES, ids=[c[0] for c in EDITS_CASES]
)
def test_guard_edits(desc, file_path, blocked, home):
    _check(run_edits(file_path, home), blocked, desc)


def test_guard_edits_approval_bypasses_soft_but_not_hard(home):
    approve_path(home).touch()
    # Approvable rule (.env) passes with a fresh approval...
    proc = run_edits("/project/.env", home)
    assert proc.returncode == 0
    # ...but hard rules (.git/) do not.
    proc = run_edits("/repo/.git/config", home)
    assert proc.returncode == 2


# ---------------------------------------------------------------------------
# guard_approve / ask_question_approval / consume_approval
# ---------------------------------------------------------------------------

def test_user_typed_approve_creates_token(home):
    proc = run_hook(GUARD_APPROVE, {"prompt": "approve"}, home)
    assert proc.returncode == 0
    assert "Guard approval granted" in proc.stdout
    assert approve_path(home).is_file()


def test_user_typed_approve_whitespace_and_case(home):
    proc = run_hook(GUARD_APPROVE, {"prompt": "  APPROVE  "}, home)
    assert proc.returncode == 0
    assert approve_path(home).is_file()


def test_user_prompt_not_approve(home):
    proc = run_hook(GUARD_APPROVE, {"prompt": "approve the plan please"}, home)
    assert proc.returncode == 0
    assert not approve_path(home).exists()


def test_user_approve_session_keyed(home):
    proc = run_hook(GUARD_APPROVE, {"prompt": "approve", "session_id": "s1"}, home)
    assert proc.returncode == 0
    assert (home / ".claude" / "guard-approve-s1").is_file()


def test_ask_question_approve_answer_creates_token(home):
    payload = {
        "tool_response": {
            "questions": [{"options": [{"label": "Approve"}, {"label": "Deny"}]}],
            "answers": {"Run the command?": "Approve"},
        }
    }
    proc = run_hook(ASK_QUESTION_APPROVAL, payload, home)
    assert proc.returncode == 0
    assert approve_path(home).is_file()


def test_ask_question_deny_answer_no_token(home):
    # "Approve" appears in the questions spec (it's a literal option label) —
    # only the .answers values may trigger the token.
    payload = {
        "tool_response": {
            "questions": [{"options": [{"label": "Approve"}, {"label": "Deny"}]}],
            "answers": {"Run the command?": "Deny"},
        }
    }
    proc = run_hook(ASK_QUESTION_APPROVAL, payload, home)
    assert proc.returncode == 0
    assert not approve_path(home).exists()


def test_ask_question_tool_output_fallback(home):
    payload = {"tool_output": {"answers": {"q": "Approve"}}}
    proc = run_hook(ASK_QUESTION_APPROVAL, payload, home)
    assert proc.returncode == 0
    assert approve_path(home).is_file()


def test_ask_question_string_answers(home):
    payload = {"tool_response": {"answers": "Approve"}}
    proc = run_hook(ASK_QUESTION_APPROVAL, payload, home)
    assert proc.returncode == 0
    assert approve_path(home).is_file()


def test_ask_question_no_answers(home):
    proc = run_hook(ASK_QUESTION_APPROVAL, {"tool_response": {}}, home)
    assert proc.returncode == 0
    assert not approve_path(home).exists()


def test_consume_deletes_both_tokens(home):
    approve_path(home).touch()
    ack_path(home).touch()
    proc = run_hook(CONSUME_APPROVAL, {}, home)
    assert proc.returncode == 0
    assert not approve_path(home).exists()
    assert not ack_path(home).exists()


def test_consume_session_keyed(home):
    """Consumer only deletes tokens for ITS session."""
    (home / ".claude" / "guard-approve-s1").touch()
    (home / ".claude" / "guard-approve-s2").touch()
    proc = run_hook(CONSUME_APPROVAL, {"session_id": "s1"}, home)
    assert proc.returncode == 0
    assert not (home / ".claude" / "guard-approve-s1").exists()
    assert (home / ".claude" / "guard-approve-s2").is_file()
