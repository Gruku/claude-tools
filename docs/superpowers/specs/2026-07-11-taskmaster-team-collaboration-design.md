# Taskmaster Team Collaboration — Design

- **Date:** 2026-07-11 (rev 2, same day — amended after adversarial spec review)
- **Status:** Approved design, revised. Rev 1 FAILED the spec-review gate (two independent adversarial reviews, 29 findings, 7 blockers); this revision resolves them. Key reversal: state syncs on a **dedicated orphan branch**, not the code integration branch (user re-decided with review evidence).
- **Owner:** Gruku
- **Repos:** `C:\Users\gruku\Files\Claude\taskmaster` (source of truth); claude-tools consumes via submodule
- **Version impact:** schema/layout break → next **major** taskmaster release

## 1. Problem

Taskmaster is single-user by construction. Sharing a `.taskmaster/` directory across a team fails several ways:

1. **Whole-tree writes.** `save_v3` (`taskmaster_v3.py:3568`) rewrites `backlog.yaml` *and* iterates every epic/task, rewriting or deleting each per-entity file on every save. Two writers — even two processes on one machine (`_backlog_lock` is a `threading.Lock`, per-process only) — clobber each other's unrelated changes.
2. **Monolithic index.** All tasks' light fields live in `backlog.yaml`'s `epics[].tasks[]`; any two mutations collide at git-merge time.
3. **No per-user/shared separation.** `viewer.json` (UI prefs), `auto/` (machine-local run state), and `PROGRESS.md` (derived, regenerated every save) sit in the shared dir. No identity concept exists — only `user|claude` enums; no `assignee` on tasks/bugs.
4. **ID corruption.** Bug/issue/idea/decision/note IDs are directory-scan max+1; task IDs scan the in-memory `epic_obj["tasks"]` list (`backlog_server.py:4052-4064`). Two divergent replicas mint the same ID and merge silently.
5. **Nothing is shared today anyway:** consumer repos (claude-tools confirmed, `.gitignore:44-46`) blanket-ignore `.taskmaster/` by design ("ships taskmaster as a tool, not a record of one user's work").

## 2. Requirements (settled with user)

| Question | Decision |
|---|---|
| Sync transport | Git, same repo — local-first preserved |
| Sync lane | **Dedicated orphan state branch** (`taskmaster-state`). *Rev 1 chose "fast lane on the integration branch"; adversarial review showed that to be structurally broken (see §14) and the user re-decided.* |
| Identity | Derived from git config on first use; interactive fixes live in skills, never the server |
| Per-user state visibility | Namespaced but visible — committed to the state branch under a per-user dir |
| Assignment | Yes — assignee + claim; pick-task steers away from claimed work |
| Viewer scope | Team surfaces included |
| Layout | **A: per-entity sharding** (over event-journal and merge-driver) |
| ID scheme | Sequential + sync-time self-heal, made safe by canonical refs + alias files |

## 3. On-disk layout

```
.taskmaster/                # STAYS GITIGNORED on all code branches (no reversal of
                            # shipped philosophy). The local tree is the working copy;
                            # the taskmaster-state branch is the shared truth (§6).
  backlog.yaml              # SHRUNK: meta (static), phases[], epic definitions
                            #   (id, title, status, done_when). No epics[].tasks[] lists.
  project.yaml              # unchanged; gains team: block (§7)
  aliases/<old-id>.yaml     # one file per ID rename (old -> new, ts, reason) — one-writer
  tasks/<id>.md             # ALL task fields in frontmatter (light + heavy + NEW: epic:,
                            #   order:, assignee:, updated_by:) + body
  epics/<id>.md phases/<id>.md bugs/ issues/ ideas/ decisions/ notes/  # shapes unchanged;
                            #   author fields upgraded (§4); bugs gain assignee:
  handovers/                # shared pool (written to be read by others); gains author:
  harvests/                 # shared, write-once
  users/<handle>/           # per-user, synced, team-visible; only the owner writes here
    profile.yaml            # display name, git email list, created
    sessions/*.md           # session logs / activity
  local/                    # NEVER leaves the machine (excluded from the state tree)
    viewer.json             # moved here
    PROGRESS.md             # regenerated on demand
    identity.yaml           # this machine's handle pointer (sticky, §4)
    auto/                   # moved here (machine-local run state)
    cache/                  # derived: meta.updated replacement, load index (optional)
    sync/                   # engine state: last-sync ref, conflicts/, notes queue (§6)
```

Removed from the shared tree: `meta.updated` (derived lazily into `local/cache/`), `PROGRESS.md`, `viewer.json`, `auto/`, `snapshots/` (dead subsystem — migration deletes).

### Rules

- **One writer per file.** Task create/edit touches one file. Epic membership derives from the task's `epic:` field. `users/<handle>/` is owner-write-only. Aliases are one-file-per-rename.
- **Task order within an epic** — a data hole rev 1 missed (order was `tasks[]` list position): new `order:` frontmatter field using **fractional indexing** (float; insert-between mints a midpoint) so a reorder touches only the moved task's file. Ties break by ID.
- Single-user projects: identical layout, one `users/` entry, sync off. One schema; sync is the only optional part.

### Read/write path (code prerequisites, named explicitly)

Rev 1 hand-waved these; they are the foundation and must be built:

- **`load_v3` rewrite:** task enumeration by globbing `tasks/*.md` (+ archive) and grouping by `epic:` frontmatter — today it only walks the `tasks[]` index and never globs (`taskmaster_v3.py:970-983`). Orphan `epic:` values → validation error.
- **`save_v3` rewrite — dirty-scoped and merge-aware.** The server tracks which entities a mutation touched (diff vs the loaded snapshot) and writes **only those files**. Before writing a dirty entity, it re-reads the file if changed on disk since load (mtime/size check) and field-merges (§6 policy) instead of blind-overwriting. Non-dirty entities are never written. This alone fixes the stale-in-memory clobber and the two-local-processes clobber — it benefits single-user mode and ships first (§12).
- **Task ID allocator rewrite:** scan `tasks/*.md` filenames (incl. archive) filtered by epic prefix — same pattern as `next_bug_id`'s dir glob — since the in-memory list it scans today disappears. `_find_task` and every helper iterating `epic["tasks"]` moves to the derived index (implementation plan enumerates the audit of ~125 tools).

## 4. Identity & attribution

- **Bootstrap is mechanical in the server, interactive only in skills.** On first mutation with no `local/identity.yaml`: server slugs `git user.name` (`jdoe`); if `users/jdoe/profile.yaml` exists with a different email, it appends a numeric suffix (`jdoe2`) — no prompting, ever (a stdio MCP server has no interactive channel). It writes `profile.yaml` + `local/identity.yaml` and flags `confirmed: false`. `start-session` / `init-team` skills surface unconfirmed identities and fix handle choice via AskUserQuestion. Degenerate names (`Your Name`, empty) → server refuses attribution-bearing writes with an error directing to the bootstrap skill.
- **Handle stability:** `local/identity.yaml` is sticky — once set, the machine keeps its handle even if `git user.name` changes. Same person on a second machine with the same user.name → same slug; server appends the new email to the profile. Different user.name across machines → two handles; healed by an explicit `backlog_team_merge_handles` command that rewrites `assignee:`/`author:` across the tree and drops a handle-alias file under `aliases/`. Handles are otherwise immutable.
- **New light fields:** `assignee:` on tasks and bugs (not epics — epic ownership stays social); `author:` on handovers/notes/ideas/decisions as `<handle>` or `<handle>/claude` (preserves the human-vs-agent distinction, adds *whose* agent); `updated_by:` stamped on touched entities. Legacy `user|claude` enums migrate using the migrating user's handle.
- No central activity log — the state branch's history is the audit trail.
- Multi-assistant safe: codex/opencode adapters derive the same handle from the same git config.

## 5. IDs: sequential + self-heal, canonical refs, alias files

IDs stay human (`auth-014`, `B-072`); allocation stays scan-max+1 (now uniformly a *directory* scan, §3). Safety:

- **Provisional until synced.** Only IDs not yet on the state branch can renumber; the branch serializes truth, so collision windows are the debounce interval.
- **Renumber is synchronous, never mid-flight.** The sync worker only *detects* a collision (rebase sees the same ID minted remotely) and records a pending-renumber marker in `local/sync/`. The rename executes inside the server, under the save lock, at the next `_load()` boundary — never while a session is mid-mutation, and never touching git branches. A local task branch/worktree named after the old ID is *reported* in the sync note (alias covers it); never auto-renamed.
- **Canonical refs `[[auth-014]]`** in all prose written by taskmaster skills/tools; viewer renders them as alias-resolving links. Renumber transactionally rewrites structured fields (`depends_on`, typed `links`, `epic:`, bundle refs, gate/merge records) plus `[[...]]` refs across `.taskmaster/` and `team.ref_roots` (default `docs/superpowers/`; those files are working-tree only and travel with code commits, never the state branch).
- **Alias = one file per rename** under `aliases/` (rev 1's single `aliases.yaml` violated the one-writer rule at exactly the moment collisions cluster). All lookups resolve through aliases forever, covering bare-text mentions, commit messages, branch names.

## 6. Sync engine — dedicated state branch

**Transport:** an **orphan branch** `taskmaster-state` (configurable) whose tree is exactly `.taskmaster/**` minus `local/`. `.taskmaster/` remains gitignored on code branches. Consequences (this is why rev 1's fast-lane-on-main died): no un-ignore reversal; feature-branch commits can never sweep state into the code lane; no protected-branch rejection; zero pollution of code history/blame/bisect; and the guard-hooks story collapses to a trivial argv allow-rule for `git push origin taskmaster-state` — the orphan ref *is* the jail, by construction, with no commit-content inspection.

Lives in the MCP server; **off by default**, enabled via `init-team`.

### Outbound

1. **Plumbing, no checkout:** the engine builds the state tree from local files via `hash-object`/`mktree`/`commit-tree` and updates the ref — no worktree anywhere (kills the nested-worktree/Windows-prune hazard), user's branch/index/working tree untouched.
2. **State-based queue, not event-based:** outbound work = diff of local files vs the locally stored `last-sync` ref. Crash/failed-push reconciliation is therefore recomputation — replay is idempotent by construction; no persisted path list to double-apply.
3. Debounce 30 s; **claims only** push immediately (rev 1 made all status changes immediate — a retry amplifier under contention). One worker per machine (best-effort lockfile in `local/sync/`); a second worker is harmless — the ref push serializes.
4. Fetch → non-FF? → **semantic merge** (below) → commit with remote tip as parent → push, retry with backoff.

### Inbound

Session start and viewer polling fetch the ref and three-way-apply into local files with the same per-entity merge (local unpushed edits preserved). Windows editor file locks on a target `.md`: bounded retry, then skip with a sync note — never a crash, never a partial write.

### Conflict policy (expanded — rev 1 covered only frontmatter scalars)

| Case | Resolution |
|---|---|
| Disjoint frontmatter fields | Field-wise merge, both sides land |
| Same scalar field | Pushed-truth wins; losing value in a **sync note** — never silent |
| `status` | Pushed-truth wins for the status value, but `gates` / merge records **append-merge (union)** so a losing transition can never strip recorded gate evidence |
| Markdown body, both edited | Pushed body wins on the branch; the **full losing body is preserved** at `local/sync/conflicts/<id>-<ts>.md` and the sync note links it (a multi-KB body is not "a note" — it's a file) |
| Archive/delete vs edit | **Edit wins** — archive is reversible; the entity resurrects with a sync note ("[[auth-014]] was archived by jd while you edited — resurrected"). Archive vs archive merges trivially |
| Same ID minted twice | Pushed mint keeps the ID; local side gets pending-renumber (§5) |

Sync notes queue in `local/sync/` and surface at `start-session` and in the viewer (§9).

### Honest claim semantics under partition

A claim is authoritative **only once it's on the state branch**. Until acked, the task carries `sync: pending`, shown in pick-task output and the viewer. Two offline claimants both work in good faith; first-to-reconnect wins and the loser gets a sync note before merging anything. Steering (§8) is advisory at pick time (inbound is poll-based, minutes-stale) — the spec says so instead of overselling "first push wins."

## 7. `project.yaml` additions

```yaml
team:
  sync:
    mode: auto              # off | manual | auto (default off)
    state_branch: taskmaster-state
    debounce_s: 30
  ref_roots:                # extra roots for [[id]] rewrite on renumber
    - docs/superpowers
```

## 8. Assignment & claiming

- **Claim = `assignee: <handle>` + `status: in-progress`** in the task file, pushed immediately. No locks, no claims file.
- **Race rule: first to the state branch wins**; the loser's merge detects it, reverts locally, session told "already claimed by jd."
- **Steering:** `pick-task` / `backlog_next_available` exclude others' assignments; overriding is an explicit reassign with confirmation.
- **No auto-expiry**: claims are assignment, not leases. Stale claims (in-progress, no activity ≥ 5 days) flagged in the viewer for humans.
- Bugs share `assignee` semantics; epics have none.

## 9. Viewer team surfaces

Standing rules apply: no colored left rails, no hover motion, no box-shadows; surface stepping; chip rows via shared `chipClickNext`.

1. **Assignee on cards** (kanban/table/bugs): handle chip; `sync: pending` claims get a subtle pending indicator; stale claims a tinted full-perimeter border + tooltip.
2. **Assignee chip-row filter** — one chip per teammate + "unassigned", standard chip behavior.
3. **Team screen** (`js/screens/team.js`): per-person workload columns (claimed / in-progress / in-review); latest handover per person (by `author:`); recent activity from `users/<handle>/sessions/`; stale-claim list; **sync health panel** — lane status (last push/pull, pending count, offline) and the sync-notes inbox (conflict losses with links to preserved bodies, renumber reports) with dismiss.
4. **`[[id]]` rendering** as alias-resolving links wherever prose renders.
5. Sync notes also print at `start-session`.

## 10. Migration & versioning

Smaller than rev 1 because tracking never flips — `.taskmaster/` stays ignored; the state branch is created empty by `init-team` and seeded from the local tree of whoever enables it first (later joiners three-way-merge their local tree on first sync).

One-shot idempotent migration (gated like `migrate-v3`; if legacy `lessons/` exists, `migrate-lessons` runs first):

1. Light fields from `backlog.yaml` → `tasks/<id>.md` frontmatter; write `epic:` and `order:` (from current list positions); shrink `backlog.yaml`.
2. Create `users/<handle>/` (migrating user) and `local/`; move `viewer.json` and `auto/` into `local/`; delete `snapshots/`; stop writing `PROGRESS.md` outside `local/`; create `aliases/`.
3. Rewrite legacy `user|claude` author enums (§4).
4. Stamp new `schema_version`.

- **Major version bump**; plugin.json + marketplace.json + CHANGELOG per repo protocol; MCP restart required.
- Old-layout projects load read-only with a migrate prompt (v2→v3 UX).
- Single-user projects migrate to the same layout, sync off — exactly one schema. The relayout (with dirty-scoped save) is the mandatory part and is a win on its own; sync stays opt-in.

## 11. Testing

- **Unit:** dirty-scoped save (only touched entities written; concurrent-disk-change re-read + merge); field-wise merge (disjoint / conflicting / status+gates union / body / archive-vs-edit); renumber rewrite (structured, `[[refs]]`, alias file, ref_roots); alias-resolving lookups; glob enumeration + orphan `epic:`; fractional `order:`; allocator dir-scan (incl. archive).
- **Two-process, one machine:** two server instances mutate different tasks — no clobber (the rev 1 gap `threading.Lock` never covered).
- **Integration (the real gate):** two clones + bare origin through the actual MCP server: concurrent disjoint edits both land; same-field → pushed-wins + note; body conflict → losing body preserved on loser's machine; claim race → first-to-branch wins, loser notified; offline double-claim → reconnect resolution; duplicate mint → pending-renumber → synchronous rename + refs + alias; kill the worker mid-cycle → state-diff recomputation, no double-apply; orphan-ref jail (state push touches no code branch; guard allow-rule matches only `taskmaster-state`).
- **Viewer:** unit tests for team-screen shaping; route-mocked Playwright specs (team screen, assignee chips, sync inbox) per the UI-testing playbook — no live-data e2e (ISS-025).
- **Migration:** golden-dir fixture → migrate → assert layout → load → entity-for-entity compare.
- No CI — the suite must run locally as one `pytest` command.

## 12. Epic decomposition & sequencing

Rev 1 was fairly judged "4–5 epics in one spec's clothes." The split, with dependencies:

1. **`team-relayout`** — sharded storage, dirty-scoped/merge-aware save, glob read path, `order:`, allocator + `_find_task` rewrite, migration. **Minimal shippable slice** — fixes single-user whole-file collisions and two-process clobber with zero team features.
2. **`team-identity`** — handles, `assignee`/`author`/`updated_by`, bootstrap in skills, merge-handles command. Depends on 1.
3. **`team-sync`** — state-branch engine (plumbing, state-diff queue, conflict policy, sync notes), guard allow-rule, `init-team`. Depends on 1; wants 2 for attribution.
4. **`team-ids`** — collision detect + synchronous renumber, `[[refs]]` writing convention, aliases, resolver. Depends on 3.
5. **`team-viewer`** — team screen, assignee chips/filter, sync health inbox. Depends on 2 + 3.

Team-usable = 1+2+3. Each epic gets its own implementation plan.

## 13. Out of scope / future

Event-journal activity feed (additive, never source of truth); central server / hosted sync; roster & roles; @mentions; notification routing; claim leases; epic assignment; state-branch history squash/compaction (revisit if the ref grows hot).

## 14. Rejected alternatives

- **Fast lane on the code integration branch** *(rev 1's choice — rejected by adversarial review, user re-decided)*: requires reversing the shipped `.taskmaster/`-ignored philosophy on every consumer; feature-branch commits sweep state into the code lane where the semantic merge never runs (git text conflicts at PR time — the original problem, worse); protected master rejects the lane outright; 30 s bot commits pollute log/blame/bisect; guard-hooks would need commit-content inspection it structurally lacks.
- **B — event journals as source of truth:** conflict-free but rewrites persistence and kills direct file editability/grep.
- **C — semantic merge driver on the monolith:** per-clone install burden, silent-corruption risk, fixes neither IDs nor the split.
- **Handle-prefixed / random IDs:** collision-proof offline but permanently uglier; self-heal + aliases chosen since the sync lane keeps collision windows small.
- **Separate `claims.yaml`:** redundant — the claimed task file is single-writer in practice.
- **Single `aliases.yaml`** *(rev 1)*: a shared append file conflicts exactly when collisions cluster; one-file-per-alias restores one-writer.
- **Async renumber in the sync worker** *(rev 1)*: mutates files/branches under a live session; moved to a synchronous `_load()`-boundary operation.
