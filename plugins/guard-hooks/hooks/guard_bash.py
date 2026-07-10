#!/usr/bin/env python3
"""guard_bash.py — PreToolUse hook for Bash commands.

Python port (perf) of the four bash guards, run sequentially in this order:
  1. guard-destructive   — destructive file/git operations
  2. guard-database      — destructive DB operations (HARD/SOFT tiers)
  3. guard-system-paths  — destructive ops targeting OS system paths
  4. guard-git-internals — destructive ops targeting .git/ (no approval bypass)

First block wins (exit 2, stderr to the model) — equivalent to the previous
parallel-any-blocks registration of the four separate bash scripts. A guard
whose matched rule is satisfied by a fresh user approval ALLOWS (returns
None) and the remaining guards still run, preserving parallel semantics
(e.g. `rm -rf .git` with approval passes guard 1 but is still hard-blocked
by guard 4).

Exit 2 = block. Exit 0 = allow.

Approval flow (shared with the rest of guard-hooks, scoped as of v2.8.0):
  A block records its scope (guard + command hash) in the per-session
  guard-pending file. The AI calls AskUserQuestion with labels
  "Approve"/"Deny". On "Approve", the PostToolUse hook on AskUserQuestion
  arms the per-session approval file with that scope. The user can also
  type "approve" as a chat message (UserPromptSubmit hook). Approval is
  valid for 5 minutes and covers exactly the blocked command; PreToolUse
  only checks it — consume_approval.py (PostToolUse) burns it after the
  approved command actually runs.

Registered for both the Bash and PowerShell tools (ISS-026) — both carry
the command in tool_input.command.

Zero subprocess spawns on the hot path: the only subprocess is
`git branch --show-current`, run exclusively when a bare `git push` already
matched.
"""

import os
import re
import subprocess
import sys

import _guard_common as common

# ---------------------------------------------------------------------------
# Shared pattern: AI must not create/manipulate the user-only approval file.
# Detect actual mutations (touch / echo > / cp / mv / Set-Content / etc.)
# whose target ends with the guard-approve token name. A bare mention of
# the literal string in a commit message or an `ls` arg is fine.
# ---------------------------------------------------------------------------
RE_APPROVE_MUTATION = re.compile(
    r'(touch|echo[^|;&]*>|cat[^|;&]*>|cp|mv|Set-Content|Add-Content|Out-File|New-Item)'
    r'[^|;&]*guard-approve(-[A-Za-z0-9_-]+)?($|[\s"\'])'
)

# Commit/tag message arguments (-m "...", --message=..., -F "..."): inert
# text sinks. Stripped before the approve-mutation scan so a commit message
# that merely MENTIONS touch + guard-approve doesn't false-positive (B-009).
RE_MSG_ARG = re.compile(
    r'(?:^|\s)(?:-m|--message=?|-F)\s*("(?:[^"\\]|\\.)*"|\'[^\']*\')'
)


def _strip_message_args(command):
    return RE_MSG_ARG.sub(' ', command)


# git-fed heredocs (git commit -F - <<EOF, git tag -F - <<EOF, ...) are text
# sinks — git never executes the body. Their content triggered verb/token
# co-occurrence false positives (observed live: a commit message mentioning
# a PS cmdlet plus a .git/ path was hard-blocked). Only git-fed bodies are
# stripped: `bash <<EOF` and `psql <<EOF` bodies remain fully scanned, so
# true-positive coverage (destructive shell/SQL via heredoc) is unchanged.
RE_GIT_HEREDOC = re.compile(
    r'(\bgit\b[^|;&<>]*<<-?\s*([\'"]?)(\w+)\2)(.*?)(^\3[ \t\r]*$|\Z)',
    re.DOTALL | re.MULTILINE,
)


def _strip_git_heredocs(command):
    return RE_GIT_HEREDOC.sub(lambda m: m.group(1) + "\n" + m.group(5), command)


# Redirect TARGETS of a segment: the token following >/>> (optionally
# fd-prefixed like 2> or bash's &>). fd duplications (2>&1, >&2) yield no
# target. Used by the .git/ and system-path redirect rules so a target of
# /dev/null — or an unexpanded "$var" — is judged on the TARGET, not on
# whatever paths happen to co-occur in the segment (B-064).
RE_REDIRECT_TARGET = re.compile(
    r'(?:^|\s)(?:\d+|&)?>{1,2}\s*("[^"]*"|\'[^\']*\'|[^\s|;&<>]+)'
)


def _redirect_targets(seg):
    targets = []
    for match in RE_REDIRECT_TARGET.finditer(seg):
        t = match.group(1)
        if len(t) >= 2 and t[0] in ('"', "'") and t[-1] == t[0]:
            t = t[1:-1]
        targets.append(t)
    return targets


# ===========================================================================
# Guard 1 — destructive (port of guard-destructive.sh)
# ===========================================================================

RE_FILE_DELETION = re.compile(
    r'(^|\s|&&|\|)(rm\s+-rf|rm\s+-r\s|rm\s+--recursive|rmdir|shred|unlink)\s',
    re.IGNORECASE,
)
RE_PUSH_CMD = re.compile(r'git\s+((-[a-zA-Z]+\s+\S+|--[a-z-]+)\s+)*push(\s+[^;&|]+)?')
# PowerShell recursive delete — the `rm -rf` analog (ISS-026). `-Force`
# alone (single item, no recursion) stays allowed, matching `rm -f` parity.
RE_PS_RECURSIVE_DELETE = re.compile(
    r'\bRemove-Item\b[^|;&]*\s-(Recurse|r)\b', re.IGNORECASE
)
RE_RESET_HARD = re.compile(r'git\s+reset\s+--hard')
RE_GIT_CLEAN = re.compile(r'git\s+clean\s+-[a-zA-Z]*f')
RE_WORKTREE_REMOVE = re.compile(r'git\s+([^|;&]*\s)?worktree\s+remove')
RE_WORKTREE_REMOVE_SEG = re.compile(r'worktree\s+remove[^;&|]*')
# Match --force or short -f / -fq / -qf style flags. Flag-token boundary
# (whitespace or start) prevents matching '-f' embedded in a path like
# '.worktrees/desktop-app-258'.
RE_WORKTREE_FORCE = re.compile(r'(^|\s)(--force|-[a-zA-Z]*f[a-zA-Z]*)(\s|=|$)')
RE_BRANCH_FORCE_DELETE = re.compile(r'git\s+branch\s+-D\s')
RE_CHECKOUT_DOT = re.compile(r'git\s+(checkout|restore)\s+\.\s*$')
RE_STASH_CLEAR = re.compile(r'git\s+stash\s+(clear|drop\s+--all)')
RE_WINDOWS_DESTRUCTIVE = re.compile(
    r'(^|\s|&&|\|)(del\s+/[sfq]|rd\s+/s|format\s|diskpart)', re.IGNORECASE
)
# Failure-masking pattern: destructive git op piped through tail/head/grep —
# the line filter overwrites the upstream exit code so '&&' chains do NOT
# short-circuit on failure.
RE_DESTRUCTIVE_GIT = re.compile(
    r'git\s+([^|;&]*\s)?(worktree\s+remove|push|reset|clean|branch\s+-D'
    r'|stash\s+(clear|drop)|rebase|merge|submodule\s+deinit)'
)
RE_LINE_FILTER = re.compile(r'\|\s*(tail|head|grep|awk|sed|wc|cut)(\s|$)')

DESTRUCTIVE_ASK_RITUAL = """
ACTION REQUIRED: Use the AskUserQuestion tool with EXACTLY this shape:
  question: one short sentence describing the destructive action
  options (use these labels verbatim — do not rename, translate, or add more):
    - label: "Approve"  description: "Run the command as shown"
    - label: "Deny"     description: "Cancel; do not run the command"

After the user responds:
  - "Approve" → rerun the ORIGINAL command unchanged
  - "Deny" or no response → do NOT run the command

The approval covers exactly this command for 5 minutes and is consumed when
it runs — intermediate commands do not use it up, and it does not authorize
any other guarded action.
Only the exact label "Approve" is recognized as authorization.
Do NOT re-run automatically. Do NOT create the approval file yourself.
"""


def guard_destructive(command, approve_path, ack_path, hook_cwd,
                      pending_path=None, action_hash=""):
    """Returns the stderr block message, or None to allow."""

    # --- Block LLM from creating the approval file ---
    # Commit-message bodies are inert text — strip them first (B-009).
    if RE_APPROVE_MUTATION.search(_strip_message_args(command)):
        return (
            "⛔ GUARD HOOK BLOCKED THIS COMMAND.\n"
            "Reason: You cannot create or manipulate the guard approval file. "
            "Only the user can do this manually.\n"
        )

    def block(reason):
        # Check for a valid user approval covering THIS action before
        # blocking. Approval is NOT consumed here — consume_approval.py
        # (PostToolUse) does that after the approved command actually runs.
        if common.approval_grants(approve_path, "destructive", action_hash):
            return None
        if pending_path is not None:
            common.write_scope(
                pending_path, {"guard": "destructive", "hash": action_hash}
            )
        return (
            "⛔ GUARD HOOK BLOCKED THIS COMMAND.\n"
            "Reason: {}\n"
            "Command: {}\n".format(reason, command)
            + DESTRUCTIVE_ASK_RITUAL
        )

    # --- File deletion ---
    if RE_FILE_DELETION.search(command):
        return block(
            "Destructive file deletion ('{}'). "
            "Use 'git worktree remove' for worktrees.".format(command)
        )

    # --- PowerShell recursive delete (rm -rf analog) ---
    if RE_PS_RECURSIVE_DELETE.search(command):
        return block(
            "Remove-Item -Recurse deletes a directory tree (the PowerShell "
            "'rm -rf'). Use 'git worktree remove' for worktrees."
        )

    # --- Git push guards (force push, push to main/master, bare push) ---
    # Extract the git push portion, accounting for global flags like -C <path>
    # between 'git' and 'push'. Stops at && | or ; to avoid false positives
    # from words like "main/master" appearing in commit messages.
    push_match = RE_PUSH_CMD.search(command)
    if push_match:
        push_cmd = push_match.group(0)
        # Extract just the args after "push" (greedy, like `sed 's/.*push//'`).
        push_args = re.sub(r'.*push', '', push_cmd, count=1)

        # Force detection walks flag TOKENS only — a substring scan flagged
        # branch names containing "-f" (e.g. asset-engine-foundation, B-062).
        force_hit = False
        for token in push_args.split():
            if token == '--':
                break  # everything after is positional
            if not token.startswith('-'):
                continue
            if (
                token in ('-f', '--force')
                or token.startswith('--force-with-lease')
                or token.startswith('--force-if-includes')
                # short-flag cluster containing f (e.g. -uf)
                or (re.match(r'^-[a-zA-Z]+$', token) and 'f' in token)
            ):
                force_hit = True
                break
        if force_hit:
            return block("Force push detected. This can overwrite remote history.")

        # Protected-branch detection: walk the positional args, drop flags and
        # the remote name, and check only the DESTINATION side of each refspec
        # (`[+]<src>[:<dst>]` -> dst is right of colon, or the whole ref if no
        # colon). Bare deletes (`:dst`) still flag if dst is protected. `+`
        # force-prefix is stripped before checking. This avoids the old
        # false-positive on `git push origin master:feature-branch` (master is
        # the SOURCE; feature-branch is the destination).
        protected_dst_hit = False
        saw_remote = False
        for token in push_args.split():
            if token.startswith('-'):
                continue  # flag — skip
            if not saw_remote:
                saw_remote = True  # first non-flag positional is the remote
                continue
            refspec = token[1:] if token.startswith('+') else token
            dst = refspec.rsplit(':', 1)[1] if ':' in refspec else refspec
            if dst.startswith('refs/heads/'):
                dst = dst[len('refs/heads/'):]
            if dst in ('main', 'master'):
                protected_dst_hit = True
                break
        if protected_dst_hit:
            return block("Pushing to main/master. Create a PR instead.")

        # Bare push (no args after "push") — check current branch.
        # Subprocess only runs here, after the push pattern already matched.
        if not push_args.strip():
            try:
                proc = subprocess.run(
                    ["git", "branch", "--show-current"],
                    capture_output=True, text=True,
                )
                current_branch = proc.stdout.strip() if proc.returncode == 0 else ""
            except OSError:
                current_branch = ""
            if current_branch in ("main", "master"):
                return block(
                    "Bare 'git push' on {}. Create a PR instead.".format(current_branch)
                )

    # --- Git reset --hard ---
    if RE_RESET_HARD.search(command):
        return block("'git reset --hard' discards uncommitted work. Commit or stash first.")

    # --- Git clean (deletes untracked files) ---
    if RE_GIT_CLEAN.search(command):
        return block("'git clean -f' permanently deletes untracked files.")

    # --- Git worktree remove --force (Windows cascade hazard) ---
    # Observed 2026-05-19: '--force' on a worktree containing submodules with
    # long paths cascade-deleted top-level dotfiles in the PARENT checkout.
    if RE_WORKTREE_REMOVE.search(command):
        # Isolate the portion from 'worktree remove' to the next chain operator
        # so a later '--force' flag in an unrelated chained command doesn't
        # false-positive.
        seg_match = RE_WORKTREE_REMOVE_SEG.search(command)
        remove_seg = seg_match.group(0) if seg_match else ""
        if RE_WORKTREE_FORCE.search(remove_seg):
            return block(
                "'git worktree remove --force' can cascade-delete top-level dotfiles "
                "in the PARENT checkout (.git/, .gitignore, .gitmodules, .env*, "
                ".github/, .vscode/, …) when the worktree contains submodules or has "
                "long paths on Windows. Confirmed in a 2026-05-19 incident. Try "
                "'git -C <worktree> submodule deinit -f <submodule>' first, then "
                "'git worktree remove' without --force."
            )

        # --- Submodule pre-flight ---
        # Even without --force, a worktree containing submodules fails partway
        # through removal. Approval-gate (not hard-block) — there are
        # legitimate cases on non-Windows or after the user has deinit'd.
        target = ""
        post_remove = re.sub(r'^worktree\s+remove\s+', '', remove_seg)
        for token in post_remove.split():
            if token.startswith('-'):
                continue
            target = token
            break
        if target:
            # Strip surrounding quotes if any.
            if target.startswith('"'):
                target = target[1:]
            if target.endswith('"'):
                target = target[:-1]
            if target.startswith("'"):
                target = target[1:]
            if target.endswith("'"):
                target = target[:-1]
            abs_target = target
            is_absolute = target.startswith('/') or re.match(r'^.:[/\\]', target)
            if not is_absolute and hook_cwd:
                abs_target = hook_cwd + "/" + target
            if os.path.isdir(abs_target) and os.path.exists(
                os.path.join(abs_target, ".gitmodules")
            ):
                return block(
                    "Worktree '{0}' contains submodules ('.gitmodules' present). "
                    "Even without --force, removal will fail partway and can leave "
                    "the parent in a fragile state. Run 'git -C \"{0}\" submodule "
                    "deinit -f --all' first, then retry "
                    "'git worktree remove {0}'.".format(target)
                )

    # --- Git branch -D (force delete) ---
    if RE_BRANCH_FORCE_DELETE.search(command):
        return block("'git branch -D' force-deletes a branch. Use 'git branch -d' (safe delete).")

    # --- Git checkout/restore that discards all changes ---
    if RE_CHECKOUT_DOT.search(command):
        return block("This discards all uncommitted changes. Commit or stash first.")

    # --- Git stash clear / drop all ---
    if RE_STASH_CLEAR.search(command):
        return block("This destroys stash entries permanently.")

    # --- Windows destructive commands ---
    if RE_WINDOWS_DESTRUCTIVE.search(command):
        return block("Destructive Windows command detected.")

    # --- Failure-masking pattern: destructive git op piped through filters ---
    if RE_DESTRUCTIVE_GIT.search(command) and RE_LINE_FILTER.search(command):
        return block(
            "Destructive git operation piped into a line filter "
            "(tail/head/grep/awk/sed/wc/cut). This masks the upstream exit code so "
            "'&&' chains do not short-circuit on failure — a partial-failure cascade "
            "can run silently. Re-run without the filter so the real output is visible."
        )

    return None


# ===========================================================================
# Guard 2 — database (port of guard-database.sh)
# ===========================================================================

RE_ACK_SENTINEL = re.compile(r'^[ \t\r]*:[ \t\r]+guard-ack-self[ \t\r]*$', re.MULTILINE)
RE_DROP_DB_SCHEMA = re.compile(r'DROP\s+(DATABASE|SCHEMA)\b', re.IGNORECASE)
RE_DROP_TABLE = re.compile(r'DROP\s+TABLE\b', re.IGNORECASE)
RE_TRUNCATE = re.compile(r'\bTRUNCATE\b', re.IGNORECASE)
# Unbounded DELETE / UPDATE (no WHERE before terminator). Terminator includes
# ) so CTE-wrapped statements like WITH x AS (DELETE FROM users) SELECT 1 are
# caught; the negative WHERE check also stops at ) so a WHERE outside the CTE
# doesn't get attributed to the inner DELETE/UPDATE.
RE_DELETE_FROM = re.compile(
    r'DELETE\s+FROM\s+[a-zA-Z_][a-zA-Z0-9_."]*\s*(;|"|\)|$)', re.IGNORECASE
)
RE_DELETE_WHERE = re.compile(r'DELETE\s+FROM\s+[^;")]*\bWHERE\b', re.IGNORECASE)
RE_UPDATE_SET = re.compile(r'UPDATE\s+[a-zA-Z_][a-zA-Z0-9_."]*\s+SET\b', re.IGNORECASE)
RE_UPDATE_WHERE = re.compile(r'UPDATE\s+[^;")]*\bWHERE\b', re.IGNORECASE)
RE_MONGO_DROP_DB = re.compile(r'\bdropDatabase\s*\(')
RE_MONGO_DROP_COLLECTION = re.compile(r'\.drop\s*\(\s*\)')
RE_MONGO_DELETE_MANY = re.compile(r'deleteMany\s*\(\s*\{\s*\}\s*\)')
RE_REDIS_FLUSHALL = re.compile(r'\bredis-cli\b[^|;&]*\bflushall\b', re.IGNORECASE)
RE_REDIS_FLUSHDB = re.compile(r'\bredis-cli\b[^|;&]*\bflushdb\b', re.IGNORECASE)
RE_SUPABASE_DB_RESET = re.compile(r'(^|\s)(npx\s+)?supabase\s+db\s+reset\b')
RE_SUPABASE_PROJECT_DELETE = re.compile(r'(^|\s)(npx\s+)?supabase\s+projects\s+delete\b')
RE_SUPABASE_DB_PUSH = re.compile(r'(^|\s)(npx\s+)?supabase\s+db\s+push\b')
RE_DOCKER_DOWN_VOLUMES = re.compile(
    r'\bdocker(-compose)?\s+(compose\s+)?down\b[^|;&]*(\s(-v|--volumes))\b'
)
RE_DOCKER_VOLUME_RM = re.compile(r'\bdocker\s+volume\s+(rm|prune)\b')
RE_DOCKER_SYSTEM_PRUNE = re.compile(
    r'\bdocker\s+system\s+prune\b[^|;&]*(--volumes|\s-[a-zA-Z]*a[a-zA-Z]*\b)'
)
RE_DOCKER_RM_V = re.compile(r'\bdocker\s+rm\b[^|;&]*\s-v\b')
RE_DOCKER_DB_CONTAINER = re.compile(
    r'\bdocker\s+(stop|rm|kill)\b[^|;&]*\b(postgres|mysql|mariadb|mongo|redis|supabase)'
    r'[a-zA-Z0-9_-]*\b'
)

DB_HARD_RITUAL = """
ACTION REQUIRED: Use the AskUserQuestion tool with EXACTLY this shape:
  question: one short sentence describing the destructive database action
  options (use these labels verbatim — do not rename, translate, or add more):
    - label: "Approve"  description: "Run the command as shown"
    - label: "Deny"     description: "Cancel; do not run the command"

After the user responds:
  - "Approve" → rerun the ORIGINAL command unchanged
  - "Deny" or no response → do NOT run the command

The approval covers exactly this command for 5 minutes and is consumed when
it runs — intermediate commands do not use it up, and it does not authorize
any other guarded action.
Only the exact label "Approve" is recognized as authorization. The PostToolUse
hook on AskUserQuestion creates the approval file automatically — you do NOT
need to ask the user to touch any file. Typing "approve" as a chat message is
also recognized as a fallback. Do NOT re-run automatically. Do NOT create the
approval file yourself.
"""

DB_SOFT_RITUAL = """
DESTRUCTIVE DB OPERATION REMINDER:
  - Data loss from this command is scoped but real.
  - Verify you intend exactly this scope (table, collection, container, volume).
  - If a backup matters here, take one before proceeding.

This is a SOFT block. If you (Claude) have read this warning and verified the
scope is intended, you may self-acknowledge by running this literal Bash
command:
    : guard-ack-self
The hook recognizes the sentinel, records a per-session ack, and lets the
no-op proceed. Then re-run the ORIGINAL command unchanged. The ack is
one-shot and expires in 5 minutes.

Do NOT ask the user to run the touch command — this ack is AI-driven by design.
If you are uncertain whether the scope is intended, defer to the user with the
AskUserQuestion tool (labels "Approve" / "Deny") instead of self-acking.
"""


def guard_database(command, approve_path, ack_path, hook_cwd,
                   pending_path=None, action_hash=""):
    """Returns the stderr block message, or None to allow."""

    # --- AI must not create the user-only approval file ---
    # (Unreachable in the consolidated flow — guard_destructive's identical
    # pattern fires first — kept for structural fidelity with the bash script.)
    if RE_APPROVE_MUTATION.search(_strip_message_args(command)):
        return (
            "GUARD HOOK BLOCKED THIS COMMAND.\n"
            "Reason: You cannot create or manipulate the user-only approval file. "
            "Only the user may do this manually.\n"
        )

    # --- AI self-ack sentinel ---
    # The block_soft path tells the AI to acknowledge a soft warning by running
    # `: guard-ack-self` (a literal no-op colon command). We catch it here,
    # create the per-session ack file, and allow so the no-op runs cleanly.
    if RE_ACK_SENTINEL.search(command):
        common.touch(ack_path)
        return None

    def _note_pending():
        if pending_path is not None:
            common.write_scope(
                pending_path, {"guard": "database", "hash": action_hash}
            )

    def block_hard(reason, recovery):
        if common.approval_grants(approve_path, "database", action_hash):
            return None
        _note_pending()
        return (
            "GUARD HOOK BLOCKED THIS COMMAND (HARD).\n"
            "Reason: {}\n"
            "Recovery: {}\n"
            "Command: {}\n".format(reason, recovery, command)
            + DB_HARD_RITUAL
        )

    def block_soft(reason, recovery):
        if (common.approval_grants(approve_path, "database", action_hash)
                or common.file_recent(ack_path)):
            return None
        _note_pending()
        return (
            "GUARD HOOK BLOCKED THIS COMMAND (SOFT — AI self-ack permitted).\n"
            "Reason: {}\n"
            "Recovery: {}\n"
            "Command: {}\n".format(reason, recovery, command)
            + DB_SOFT_RITUAL
        )

    # --- SQL schema destruction ---
    if RE_DROP_DB_SCHEMA.search(command):
        return block_hard(
            "DROP DATABASE/SCHEMA detected — entire database/schema removal.",
            "Restore from a recent dump: pg_dump / mysqldump / .dump for SQLite.",
        )
    if RE_DROP_TABLE.search(command):
        return block_soft(
            "DROP TABLE detected — table and all its data will be removed.",
            "If you have a recent dump, restore via psql -f / mysql < / sqlite3 .read.",
        )
    if RE_TRUNCATE.search(command):
        return block_soft(
            "TRUNCATE detected — all rows in the table will be removed.",
            "Wrap in BEGIN; ... ROLLBACK; first to test, or take a dump.",
        )

    # --- Unbounded DELETE / UPDATE (no WHERE before terminator) ---
    if RE_DELETE_FROM.search(command) and not RE_DELETE_WHERE.search(command):
        return block_soft(
            "Unbounded DELETE detected — every row in the table will be removed.",
            "Add a WHERE clause, or wrap in BEGIN; ... ROLLBACK; to verify scope.",
        )
    if RE_UPDATE_SET.search(command) and not RE_UPDATE_WHERE.search(command):
        return block_soft(
            "Unbounded UPDATE detected — every row in the table will be modified.",
            "Add a WHERE clause, or wrap in BEGIN; ... ROLLBACK; to verify scope.",
        )

    # --- Mongo destructive ops ---
    if RE_MONGO_DROP_DB.search(command):
        return block_hard(
            "Mongo dropDatabase() — entire database removed.",
            "Restore from a mongodump (mongorestore --drop).",
        )
    if RE_MONGO_DROP_COLLECTION.search(command):
        return block_soft(
            "Mongo collection .drop() — collection and all its documents removed.",
            "Restore the collection from mongodump if needed.",
        )
    if RE_MONGO_DELETE_MANY.search(command):
        return block_soft(
            "Mongo deleteMany({}) — every document in the collection removed.",
            "Use a non-empty filter, or take a mongodump first.",
        )

    # --- Redis nukes ---
    if RE_REDIS_FLUSHALL.search(command):
        return block_hard(
            "Redis FLUSHALL — every key in every database wiped, cluster-wide.",
            "If a snapshot exists, restore via SAVE/BGSAVE artifacts and a restart.",
        )
    if RE_REDIS_FLUSHDB.search(command):
        return block_soft(
            "Redis FLUSHDB — every key in the selected database wiped.",
            "If a snapshot exists, restore via SAVE/BGSAVE artifacts.",
        )

    # --- Supabase CLI ---
    if RE_SUPABASE_DB_RESET.search(command):
        return block_hard(
            "supabase db reset — wipes the local DB and re-runs migrations.",
            "Take a pg_dump of the local DB first if its state matters.",
        )
    if RE_SUPABASE_PROJECT_DELETE.search(command):
        return block_hard(
            "supabase projects delete — destroys a remote Supabase project.",
            "There is no recovery. Confirm the project ID before proceeding.",
        )
    if RE_SUPABASE_DB_PUSH.search(command):
        return block_soft(
            "supabase db push — applies local migrations to the linked remote.",
            "Run `supabase db diff` first to confirm what will change.",
        )

    # --- Docker DB lifecycle ---
    # HARD: anything that destroys volumes
    if RE_DOCKER_DOWN_VOLUMES.search(command):
        return block_hard(
            "docker compose down -v — removes named volumes; DB data is lost.",
            "Dump the DB first: docker exec <container> pg_dump|mysqldump|mongodump > backup.",
        )
    if RE_DOCKER_VOLUME_RM.search(command):
        return block_hard(
            "docker volume rm/prune — removes Docker volumes; any DB data inside is lost.",
            "List volumes (docker volume ls) and back up before removal.",
        )
    if RE_DOCKER_SYSTEM_PRUNE.search(command):
        return block_hard(
            "docker system prune --volumes/-a — removes unused volumes and images.",
            "Run `docker volume ls` first; back up any DB volumes before pruning.",
        )

    # SOFT: container removal with -v, or stop/rm/kill of a DB-named container
    if RE_DOCKER_RM_V.search(command):
        return block_soft(
            "docker rm -v — removes the container AND its anonymous volumes.",
            "Drop the -v flag if the volume should persist.",
        )
    if RE_DOCKER_DB_CONTAINER.search(command):
        return block_soft(
            "Stopping/removing a database container — running connections will drop.",
            "Dump the DB first if it holds state you care about: "
            "docker exec <container> pg_dump > backup.",
        )

    return None


# ===========================================================================
# Guard 3 — system paths (port of guard-system-paths.sh)
# ===========================================================================

# Windows: C:\Windows, C:\Program Files [(x86)], Git Bash /c/Windows,
# cmd env vars %SystemRoot%/%WINDIR%, PowerShell $env:SystemRoot/$env:windir/
# $env:ProgramFiles. Also UNC / extended-length / device-namespace prefixes:
# \\?\C:\Windows..., \\.\C:\Windows...
RE_WIN_SYS = re.compile(
    r'([cC]:[\\/]+[wW]indows([\\/\s]|$)'
    r'|[cC]:[\\/]+[pP]rogram\s+[fF]iles(\s+\(x86\))?([\\/\s]|$)'
    r'|\\\\(\?|\.)\\[cC]:[\\/]+[wW]indows([\\/\s]|$)'
    r'|\\\\(\?|\.)\\[cC]:[\\/]+[pP]rogram\s+[fF]iles(\s+\(x86\))?([\\/\s]|$)'
    r'|/c/[wW]indows([/\s]|$)'
    r'|%SystemRoot%|%WINDIR%|\$env:SystemRoot|\$env:windir|\$env:ProgramFiles)'
)

# Unix: /bin, /sbin, /etc, /boot, /lib, /lib64, /usr/{bin,sbin,lib,lib64,
# local/bin,local/sbin}, /System/Library. Anchored with a non-path-char
# boundary so user paths like ~/etc/ or /home/x/etc/ don't false-positive.
RE_UNIX_SYS = re.compile(
    r'(^|[^a-zA-Z0-9_/.~-])(/(bin|sbin|etc|boot|lib|lib64)([/\s]|$)'
    r'|/usr/(bin|sbin|lib|lib64|local/bin|local/sbin)([/\s]|$)'
    r'|/System/Library([/\s]|$))'
)

# Unix-style destructive verbs (rm, mv, cp, chmod, chown, ln -s, tee, dd, truncate)
RE_UNIX_VERB = re.compile(
    r'(^|[\s&|;`(])(rm|rmdir|unlink|shred|mv|cp|chmod|chown|chgrp|ln|tee|dd|truncate)(\s|$)',
    re.IGNORECASE,
)
# Windows cmd verbs (del, erase, move, ren/rename, rd/rmdir, copy, xcopy, robocopy)
RE_SYSPATH_CMD_VERB = re.compile(
    r'(^|[\s&|;`(])(del|erase|move|ren|rename|rd|rmdir|copy|xcopy|robocopy)(\s|/|$)',
    re.IGNORECASE,
)
# PowerShell destructive cmdlets and ACL tools (PS is case-insensitive).
RE_SYSPATH_PS_VERB = re.compile(
    r'(Remove-Item|Move-Item|Rename-Item|Copy-Item|Set-Item|New-Item|Set-ItemProperty'
    r'|Out-File|Set-Content|Add-Content|Clear-Content|Set-Acl|takeown|icacls)',
    re.IGNORECASE,
)
# `find ... -delete` / `find ... -exec rm` etc.
RE_FIND_DESTRUCTIVE = re.compile(
    r'(^|[\s&|;`(])find(\s+[^|;&]*)?\s(-delete|-exec\s+(rm|unlink|shred|chmod|chown|mv))',
    re.IGNORECASE,
)
# Destructive verbs reduced to a basename allowlist — used to detect when an
# absolute-path invocation like `/usr/bin/rm /etc/passwd` is destructive.
RE_UNIX_VERB_BASENAME = re.compile(
    r'^(rm|rmdir|unlink|shred|mv|cp|chmod|chown|chgrp|ln|tee|dd|truncate)$'
)
# Hosts that mean "this machine" — if an ssh/scp/rsync target points here the
# segment is NOT exempted, because the operation actually runs locally.
RE_LOCALHOST = re.compile(
    r'(@(localhost|127\.0\.0\.1)([\s:]|$)|@\[?::1\]?([\s:]|$))', re.IGNORECASE
)

SYSPATH_RITUAL = """
System OS paths (C:\\Windows, C:\\Program Files, /bin, /sbin, /usr/bin, /usr/sbin, /etc, /boot, /lib, /System/Library) cannot be modified, renamed, moved, or deleted by Claude under any circumstances.

ACTION REQUIRED: Use the AskUserQuestion tool with EXACTLY this shape:
  question: one short sentence describing the system-path action and why it is needed
  options (use these labels verbatim — do not rename, translate, or add more):
    - label: "Approve"  description: "Run the command as shown"
    - label: "Deny"     description: "Cancel; do not run the command"

After the user responds:
  - "Approve" → rerun the ORIGINAL command unchanged
  - "Deny" or no response → do NOT run the command

The approval covers exactly this command for 5 minutes and is consumed when
it runs — intermediate commands do not use it up, and it does not authorize
any other guarded action.
Only the exact label "Approve" is recognized as authorization. The PostToolUse
hook on AskUserQuestion creates the approval file automatically — you do NOT
need to ask the user to touch any file. Typing "approve" as a chat message is
also recognized as a fallback. Do NOT re-run automatically. Do NOT create the
approval file yourself.
"""


def _split_segments_quote_aware(command):
    """Split a command into segments by &&, ||, ;, | — quote-aware: operators
    inside single or double quotes do NOT split. Without this, an
    `ssh remote "cmd1; cmd2 > /etc/foo"` payload would shred into local
    segments and false-positive on the inner `;` and `>` even though the
    whole thing runs remotely."""
    segments = []
    current = []
    in_single = False
    in_double = False
    i = 0
    n = len(command)
    while i < n:
        ch = command[i]
        # Inside double quotes, backslash escapes the next char (notably \") —
        # keep both verbatim and advance past them.
        if in_double and ch == '\\' and i + 1 < n:
            current.append(command[i:i + 2])
            i += 2
            continue
        if not in_single and ch == '"':
            in_double = not in_double
            current.append(ch)
            i += 1
            continue
        if not in_double and ch == "'":
            in_single = not in_single
            current.append(ch)
            i += 1
            continue
        if not in_single and not in_double:
            if command[i:i + 2] in ('&&', '||'):
                segments.append(''.join(current))
                current = []
                i += 2
                continue
            if ch in (';', '|'):
                segments.append(''.join(current))
                current = []
                i += 1
                continue
        current.append(ch)
        i += 1
    segments.append(''.join(current))
    return segments


def _split_first_token(segment):
    """Split the first token (the executable) from the rest of a segment.
    Returns (first, rest, first_base_noext) where first_base_noext is the
    unquoted, lowercased basename with any .exe suffix stripped."""
    seg_trim = segment.lstrip(" \t\r\n\x0b\x0c")
    ws = re.search(r'\s', seg_trim)
    first = seg_trim if ws is None else seg_trim[:ws.start()]
    rest = seg_trim[len(first):]

    first_unq = first
    if first_unq.startswith('"'):
        first_unq = first_unq[1:]
    if first_unq.endswith('"'):
        first_unq = first_unq[:-1]
    if first_unq.startswith("'"):
        first_unq = first_unq[1:]
    if first_unq.endswith("'"):
        first_unq = first_unq[:-1]
    first_base = first_unq.rsplit('/', 1)[-1].rsplit('\\', 1)[-1]
    first_base_lower = first_base.lower()
    if first_base_lower.endswith('.exe'):
        first_base_lower = first_base_lower[:-len('.exe')]
    return first, rest, first_base_lower


def _target_is_syspath(target):
    """True if a redirect TARGET is an OS system path. Targets that start
    with an unexpanded variable reference cannot be resolved statically —
    treat as not-a-system-path rather than lying about what it is (B-064)."""
    if target.startswith('$'):
        return False
    return bool(RE_WIN_SYS.search(target) or RE_UNIX_SYS.search(target))


def guard_system_paths(command, approve_path, ack_path, hook_cwd,
                       pending_path=None, action_hash=""):
    """Returns the stderr block message, or None to allow. Every denial is
    logged to ~/.claude/logs/guard-system-paths.log."""

    # --- AI must not create the approval file ---
    # (Unreachable in the consolidated flow — guard_destructive fires first.)
    if RE_APPROVE_MUTATION.search(_strip_message_args(command)):
        return (
            "GUARD HOOK BLOCKED THIS COMMAND.\n"
            "Reason: You cannot create or manipulate the guard approval file. "
            "Only the user can do this manually.\n"
        )

    log_file = common.home_dir() / ".claude" / "logs" / "guard-system-paths.log"

    def block(reason):
        if common.approval_grants(approve_path, "system-paths", action_hash):
            return None
        if pending_path is not None:
            common.write_scope(
                pending_path, {"guard": "system-paths", "hash": action_hash}
            )
            common.log_denied(log_file, reason, command)
        return (
            "GUARD HOOK BLOCKED THIS COMMAND.\n"
            "Reason: {}\n"
            "Command: {}\n".format(reason, command)
            + SYSPATH_RITUAL
        )

    for seg in _split_segments_quote_aware(command):
        if not seg:
            continue

        first, rest, first_base_noext = _split_first_token(seg)

        # --- ssh/scp/rsync remote-wrapper exemption ---
        # Paths inside the args refer to a REMOTE host, not the local OS —
        # unless the target is localhost/127.0.0.1/::1.
        if first_base_noext in ('ssh', 'scp', 'rsync'):
            if not RE_LOCALHOST.search(rest):
                continue

        # --- Does this segment reference an OS system path as a TARGET? ---
        # Scan REST only; the executable's own path doesn't count.
        if not (RE_WIN_SYS.search(rest) or RE_UNIX_SYS.search(rest)):
            continue

        # --- Verb / redirect checks ---
        # Absolute-path invocations (e.g. /usr/bin/rm) — the leading `/`
        # defeats the word-boundary in RE_UNIX_VERB, so detect via basename.
        if RE_UNIX_VERB_BASENAME.match(first_base_noext):
            return block("Destructive Unix command (rm/mv/cp/chmod/chown/ln/tee/dd) targeting a system path.")
        if RE_UNIX_VERB.search(seg):
            return block("Destructive Unix command (rm/mv/cp/chmod/chown/ln/tee/dd) targeting a system path.")
        if RE_SYSPATH_CMD_VERB.search(seg):
            return block("Destructive Windows cmd command (del/move/ren/rd/copy) targeting a system path.")
        if RE_SYSPATH_PS_VERB.search(seg):
            return block("Destructive PowerShell cmdlet (Remove-Item/Move-Item/Rename-Item/Copy-Item/Set-Content/takeown/icacls) targeting a system path.")
        if RE_FIND_DESTRUCTIVE.search(seg):
            return block("Destructive find (-delete or -exec rm/unlink/shred/chmod/chown/mv) targeting a system path.")
        # Judge the redirect TARGET, not path co-occurrence in the segment:
        # `ls /etc/hosts 2>/dev/null` redirects into /dev/null, not /etc (B-064).
        if any(_target_is_syspath(t) for t in _redirect_targets(seg)):
            return block("Output redirection (> or >>) into a system path.")

    return None


# ===========================================================================
# Guard 4 — git internals (port of guard-git-internals.sh)
# ===========================================================================
# HARD-BLOCKS any destructive operation that targets a .git directory or its
# contents. No approval bypass — destroying a repo's git internals is never
# legitimate from Claude.

# `.git` as a path token. Boundaries:
#   left:  start-of-string OR whitespace, '=', '/', '<', '>', quote, backslash
#   right: '/', '\', whitespace, quote, OR end-of-string
# Matches `.git`, `.git/HEAD`, `./.git`, `path/.git`, `path\.git\...`. Does
# NOT match `repo.git`, `.gitignore`, `.gitattributes`, or `something.gitfoo`.
RE_GIT_TOKEN = re.compile(r'(^|[\s=/<>\'"\\])\.git([/\\\s\'"]|$)')

# Windows cmd verbs (no copy/xcopy/robocopy here — narrower than syspaths).
RE_GITINT_CMD_VERB = re.compile(
    r'(^|[\s&|;`(])(del|erase|move|ren|rename|rd|rmdir)(\s|/|$)', re.IGNORECASE
)
# PowerShell destructive cmdlets (case-insensitive).
RE_GITINT_PS_VERB = re.compile(
    r'(Remove-Item|Move-Item|Rename-Item|Copy-Item|Set-Item|Set-ItemProperty'
    r'|Out-File|Set-Content|Add-Content|Clear-Content|New-Item)',
    re.IGNORECASE,
)
# Allowlist: redirection into the review-gate blessing marker is permitted.
# Pairs with ~/.claude/hooks/push-review-gate-guard.py. Narrow scope: only
# the redirect rule honors it; destructive verbs remain hard-blocked.
RE_BLESS_TARGET = re.compile(r'\.git[/\\]CLAUDE_REVIEW_GATE_OK$')


def guard_git_internals(command, approve_path, ack_path, hook_cwd,
                        pending_path=None, action_hash=""):
    """Returns the stderr block message, or None to allow. No approval bypass.
    Every denial is logged to ~/.claude/logs/guard-git-internals.log."""

    log_file = common.home_dir() / ".claude" / "logs" / "guard-git-internals.log"

    def block(reason):
        # No pending scope is written: this guard has no approval bypass,
        # so there is nothing to arm. Log only on the real PreToolUse pass
        # (pending_path set), not on consume-time re-evaluation.
        if pending_path is not None:
            common.log_denied(log_file, reason, command)
        return (
            "GUARD HOOK BLOCKED THIS COMMAND.\n"
            "Reason: {}\n"
            "Command: {}\n"
            "\n"
            "Destroying or modifying .git/ directories from the Bash tool is never permitted\n"
            "by Claude. There is no approval bypass — this rule is hard-blocked, mirroring\n"
            "the .git/ rule already enforced on the Edit/Write tools.\n"
            "\n"
            "If you genuinely need to remove a repository, the user must do it manually in\n"
            "their own terminal. If you were trying to remove a git worktree, use\n"
            "'git worktree remove <path>' (run from OUTSIDE the worktree being removed).\n"
            .format(reason, command)
        )

    # Split into segments by &&, ||, ;, | (simple split — not quote-aware,
    # matching the bash original).
    for seg in re.split(r'&&|\|\||;|\|', command):
        if not seg:
            continue

        first, rest, first_base_noext = _split_first_token(seg)

        # Skip ssh/scp/rsync — those target a remote host, not local .git.
        if first_base_noext in ('ssh', 'scp', 'rsync'):
            continue

        # --- Does this segment reference .git as a target? ---
        # Scan REST only — the executable's own path doesn't count (e.g.
        # running `/path/to/.git/hooks/pre-commit` would otherwise
        # false-positive).
        if not RE_GIT_TOKEN.search(rest):
            continue

        # --- Verb / redirect checks ---
        # Absolute-path invocation of a destructive verb (e.g. /usr/bin/rm .git).
        if RE_UNIX_VERB_BASENAME.match(first_base_noext):
            return block("Destructive Unix command (rm/mv/cp/chmod/chown/ln/tee/dd) targeting .git/")
        if RE_UNIX_VERB.search(seg):
            return block("Destructive Unix command (rm/mv/cp/chmod/chown/ln/tee/dd) targeting .git/")
        if RE_GITINT_CMD_VERB.search(seg):
            return block("Destructive Windows cmd command (del/move/ren/rd) targeting .git/")
        if RE_GITINT_PS_VERB.search(seg):
            return block("Destructive PowerShell cmdlet (Remove-Item/Move-Item/Rename-Item/Set-Content) targeting .git/")
        if RE_FIND_DESTRUCTIVE.search(seg):
            return block("Destructive find (-delete or -exec rm/unlink/shred/chmod/chown/mv) targeting .git/")
        # Judge the redirect TARGET, not path co-occurrence in the segment:
        # `ls .git/index.lock 2>/dev/null` redirects into /dev/null (B-064).
        for target in _redirect_targets(seg):
            if RE_BLESS_TARGET.search(target):
                continue  # allowed: writing the review-gate blessing marker
            if RE_GIT_TOKEN.search(target):
                return block("Output redirection (> or >>) into .git/")

    return None


# ===========================================================================
# Entry point
# ===========================================================================

GUARDS = (guard_destructive, guard_database, guard_system_paths, guard_git_internals)

# guard_database scans the RAW command (psql <<EOF bodies are live SQL);
# the other guards get git-fed heredoc bodies stripped (inert text sinks).
_STRIPS_GIT_HEREDOCS = {guard_destructive, guard_system_paths, guard_git_internals}


def _run_guards(command, approve_path, ack_path, hook_cwd,
                pending_path=None, action_hash=""):
    """Run all guards, first block wins. Returns the block message or None."""
    stripped = _strip_git_heredocs(command)
    for guard in GUARDS:
        text = stripped if guard in _STRIPS_GIT_HEREDOCS else command
        message = guard(text, approve_path, ack_path, hook_cwd,
                        pending_path, action_hash)
        if message is not None:
            return message
    return None


def would_block(command, hook_cwd=""):
    """True if `command` would trip any guard with no approvals present.
    Used by consume_approval.py to decide whether the command that just ran
    was a guarded action (only those burn approval/ack tokens)."""
    if not command:
        return False
    # The ack sentinel is the handshake itself, not a guarded action — and
    # evaluating it through guard_database would touch the ack file.
    if RE_ACK_SENTINEL.search(command):
        return False
    missing = common.claude_dir() / "guard-approve-never-exists"
    return _run_guards(command, missing, missing, hook_cwd) is not None


def main():
    data = common.read_hook_input()
    command = common.jq_str(data, "tool_input", "command")
    if not command:
        sys.exit(0)

    sid = common.session_id(data)
    approve_path = common.approve_file(sid)
    ack_path = common.ack_file(sid)
    pending_path = common.pending_file(sid)
    # Action identity: hash of the raw command. The Approve flow arms exactly
    # this hash; rerunning the ORIGINAL command unchanged matches it.
    action_hash = common.hash_text(command)
    # Hook's reported cwd of the calling shell, used to resolve relative paths
    # during the worktree-removal pre-flight. Optional — absent in older
    # hook payloads.
    hook_cwd = common.jq_str(data, "cwd")

    message = _run_guards(command, approve_path, ack_path, hook_cwd,
                          pending_path, action_hash)
    if message is not None:
        common.write_stderr(message)
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
