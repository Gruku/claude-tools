# Taskmaster Team Collaboration — Design

- **Date:** 2026-07-11
- **Status:** Approved design (brainstorm complete; sections 1–4 user-approved, 5–6 completed in auto mode)
- **Owner:** Gruku
- **Repos:** `C:\Users\gruku\Files\Claude\taskmaster` (source of truth); claude-tools consumes via submodule
- **Version impact:** schema/layout break → next **major** taskmaster release

## 1. Problem

Taskmaster is single-user by construction. Sharing a `.taskmaster/` directory across a team via git fails two ways:

1. **Merge conflicts.** `save_v3` rewrites the monolithic `backlog.yaml` (all epics' `tasks[]` light fields in one YAML doc) on every mutation; `meta.updated` bumps every save; `PROGRESS.md` is fully regenerated every save; per-entity `.md` files are whole-file rewrites. Two people touching *different* tasks still collide.
2. **No per-user/shared separation.** `viewer.json` (pure UI prefs) sits in the shared dir; handovers/session state have no owner; the schema has no identity concept at all — only `user|claude` enums (`discovered_by`, notes `author`) and a free-text `created_by` on ideas. No `assignee` exists on tasks/bugs (only on external-tracker mirror entities).

Additional latent corruption: all ID allocation (`{epic}-{NNN}`, `B-{NNN}`, `ISS-{NNN}`, `IDEA-{NNN}`, `DEC-{NNN}`, `N-{NNN}`) is "directory-scan max+1" — two branches mint the **same ID** and merge silently, producing duplicates with no git conflict.

Locking today is in-process only (`threading.Lock` + optional `filelock` sidecar) — nothing addresses two machines.

## 2. Requirements (settled with user)

| Question | Decision |
|---|---|
| Sync transport | **Git-synced, same repo** — stays local-first; format must be merge-clean |
| Backlog sync lane | **Fast lane on the integration branch** — state-only auto-commits, minutes-level propagation; code follows normal PR flow |
| Identity | **Derived from git config** on first use; no roster ceremony |
| Per-user state visibility | **Namespaced but visible** — committed under a per-user dir; team can see who's doing what |
| Assignment | **Yes** — assignee + claim semantics; pick-task steers away from claimed work |
| Viewer scope | **Team surfaces included** — per-person workload, teammates' handovers/activity |
| Layout approach | **A: per-entity sharding** (over event-journal and merge-driver alternatives) |
| ID scheme | **Keep sequential + sync-time self-heal renumber**, made safe by canonical refs + alias map |

## 3. On-disk layout

```
.taskmaster/
  backlog.yaml            # SHRUNK: meta (static), phases[], epic definitions
                          #   (id, title, status, done_when). No epics[].tasks[] lists.
  project.yaml            # unchanged; gains team: block (see §7)
  aliases.yaml            # append-only old-id -> new-id map (see §5)
  tasks/<id>.md           # ALL task fields in frontmatter (light + heavy) + body;
                          #   task declares `epic:` — epic membership DERIVED at load
  epics/<id>.md           # unchanged (heavy fields)
  phases/<id>.md          # unchanged
  bugs/ issues/ ideas/ decisions/ notes/   # unchanged shapes; author fields upgraded (§4)
  handovers/              # unchanged location (shared pool); files gain author: frontmatter
  users/<handle>/         # PER-USER, committed, team-visible; only the owner writes here
    profile.yaml          # display name, git email(s), created — written once by owner
    sessions/*.md         # session logs / activity
  local/                  # gitignored entirely (added to .gitignore by migration)
    viewer.json           # moved here (was shared — pure UI prefs)
    PROGRESS.md           # regenerated on demand; never committed again
    identity.yaml         # machine-local pointer to my handle
    sync/                 # fast-lane queue + state (§6)
```

### Rules

- **One writer per file wherever possible.** Creating a task adds one file; editing a task touches one file. Adding a task to an epic touches zero shared files besides the new task file (membership derived from the task's `epic:` field).
- `meta.updated` is **removed** (derive from git/mtime when needed).
- Everything under `users/<handle>/` is written only by that handle — conflicts structurally impossible.
- Handovers stay in the shared `handovers/` pool (written to be read by others; existing tooling globs that dir) and carry `author:`.
- `PROGRESS.md` and `viewer.json` leave git entirely.
- **Single-user projects use the identical layout** — one entry in `users/`, sync lane off. One code path; no "team mode" fork.
- Epic/phase creation still edits `backlog.yaml` — accepted: low-churn, rare.

### Read path

`load_v3` already opens every per-entity file; deriving epic membership from task frontmatter adds no I/O class. An mtime-keyed index cache under `local/` is a **future optimization only if measured slow** (YAGNI).

## 4. Identity & attribution

- On first mutating call, the server derives `handle` from git `user.name` (slugified, e.g. `jdoe`), writes `users/<handle>/profile.yaml` (display name, `user.email` for disambiguation) and `local/identity.yaml`. Slug collision with a *different* email prompts once for an alternative handle.
- New light fields:
  - `assignee:` on **tasks** and **bugs** (not epics — epic ownership stays social).
  - `author:` on handovers, notes, ideas, decisions — value is `<handle>` or `<handle>/claude`, preserving today's human-vs-agent distinction (`user|claude` enums) while adding *whose* agent. Existing enums migrate: `user` → `<handle>`, `claude` → `<handle>/claude` using the migrating user's handle.
  - `updated_by:` stamped on the entity file a mutation touches.
- **No central activity log.** The fast lane's git history *is* the audit trail; sync commits are authored with the teammate's git identity.
- Multi-assistant safe: codex/opencode adapters derive the same handle from the same git config; the data layer is assistant-agnostic.

## 5. IDs: sequential + self-heal, canonical refs, alias map

IDs stay human (`auth-014`, `B-072`). Allocation stays optimistic scan-max+1. Safety comes from the sync lane:

- **Provisional until pushed.** Only unpushed IDs can renumber; the fast lane serializes truth, so collisions are detected at rebase within the debounce window (usually seconds–minutes).
- **Canonical reference syntax `[[auth-014]]`** for ID mentions in any prose (task bodies, handovers, notes, specs/plans). All taskmaster skills/tools write refs this way; the viewer renders them as links. (Inside AI prompt templates, XML-tag structure per user convention is fine — the alias map covers staleness there.)
- **Renumber = transactional rewrite.** On collision (`auth-014 → auth-015` locally): one pass rewrites structured fields (`depends_on`, typed `links`, `epic:`, bundle refs, gate/merge records) **plus** all `[[...]]` refs across `.taskmaster/` and configured doc roots (default `docs/superpowers/`; configurable in `project.yaml team.ref_roots`).
- **Alias map `aliases.yaml`** records `old: new` (append-only). Every ID lookup (`backlog_get_task`, link validation, viewer routes) resolves through aliases — anything the rewrite can't touch (commit messages, branch names, chat scrollback, external docs) resolves forever. If append-conflicts ever bite in practice, fall back to one-file-per-alias under `aliases/`; not expected (renames are rare and serialized by the lane).
- **Non-rewritables reported.** A provisional task's local branch/worktree gets renamed when unpushed; otherwise the sync engine reports the mapping and the alias covers it. Doc-root rewrites *outside* `.taskmaster/` stay in the working tree and travel with normal code commits (never on the fast lane).

## 6. Fast-lane sync engine

Lives in the MCP server. **Off by default**; enabled explicitly via `init-taskmaster` / new `init-team` step.

### Outbound

Each `_save()` enqueues changed paths; a debounced worker (default 30 s; **immediate** for claim/status changes) lands them on the integration branch:

1. **Hidden sync checkout** — a dedicated worktree of the integration branch under `local/sync/` (or `commit-tree` plumbing; implementation choice). The user's current branch, index, and working tree are never touched.
2. **Pathspec jail: commits contain only `.taskmaster/**` paths.** Nothing else can ride the fast lane, ever.
3. Fetch → rebase → push, retry with backoff.
4. **Conflict policy on the same entity file:**
   - Field-wise semantic merge of YAML frontmatter — disjoint-field edits merge cleanly (also fixes today's whole-file-rewrite collisions, e.g. `notes` vs `gates` on one task).
   - Genuine same-field conflict: **pushed-truth wins**; the losing local value is recorded as a **sync note** surfaced in the session and viewer ("your status change to [[auth-014]] lost to jd's") — never silently dropped.
5. **Offline-safe:** queue persists in `local/sync/`; backlog fully usable offline; syncs eventually.

### Inbound

Session start and viewer polling fetch the fast lane and three-way-apply into local `.taskmaster/` files through the same engine (local unpushed edits preserved via the same field-wise merge). Teammates' claims/status appear within minutes without pulling code.

### Policy interaction (explicit)

The engine auto-pushes to a shared branch — normally forbidden by the user's standing rules and guard-hooks. Treated as a **narrow, user-sanctioned machine lane**:

- Opt-in per project (`project.yaml team.sync.mode: auto`), set up interactively.
- Pathspec-jailed to `.taskmaster/**`.
- guard-hooks gets a matching carve-out that **verifies the pathspec jail** (inspects the commit's paths) rather than blanket-allowing pushes. All code-shaped pushes keep existing gates.

## 7. `project.yaml` additions

```yaml
team:
  sync:
    mode: auto          # off | manual | auto (default off)
    branch: master      # integration branch for the fast lane
    debounce_s: 30
  ref_roots:            # extra roots for [[id]] rewrite on renumber
    - docs/superpowers
```

## 8. Assignment & claiming

- **Claim = `assignee: <handle>` + `status: in-progress`** in the task file, pushed immediately. No locks, no separate claims file.
- **Race rule: first push wins.** The loser's rebase detects the existing claim, reverts locally, and tells the session: "already claimed by jd — pick another or coordinate."
- **Steering:** `pick-task` / `backlog_next_available` exclude tasks assigned to others by default; taking one anyway is an explicit reassignment with confirmation.
- **No auto-expiry** (opinionated default): a claim is assignment, not a lease. Stale claims (in-progress, no activity ≥ N days, default 5) are *flagged* in the viewer for humans to resolve.
- Bugs share the same `assignee` semantics; epics have none.

## 9. Viewer team surfaces

Per the standing design rules: no colored left rails, no hover motion, no box-shadows; surface stepping for elevation; chip rows via the shared `chipClickNext` helper.

1. **Assignee on cards** (kanban, table, bugs): small handle chip/avatar; unassigned shows nothing. Stale-claim flag renders as a tinted full-perimeter border + tooltip, not a rail.
2. **Assignee chip-row filter** on kanban/table/bugs — one chip per teammate + "unassigned", standard `chipClickNext` behavior (click = only, shift-click = multi-select pool).
3. **New Team screen** (`js/screens/team.js`):
   - Per-person workload columns: claimed / in-progress / in-review counts with task lists.
   - Latest handover per person (from `handovers/` by `author:`) and recent session activity (from `users/<handle>/sessions/`).
   - Stale-claim list.
   - **Sync health panel:** lane status (last push/pull, queue depth, offline), and the **sync-notes inbox** (conflict losses, renumber reports) with dismiss.
4. **`[[id]]` rendering:** anywhere prose renders (task body, handovers, notes), `[[id]]` becomes a link that resolves through the alias map.
5. Sync notes also surface at `start-session` in the terminal.

## 10. Migration & versioning

One-shot idempotent migration (extends the existing migrate machinery, gated like `migrate-v3`):

1. Move each task's light fields from `backlog.yaml` into `tasks/<id>.md` frontmatter; write `epic:` from current membership; shrink `backlog.yaml`.
2. Create `users/<handle>/` (migrating user), `local/`; move `viewer.json` → `local/`; delete tracked `PROGRESS.md`; create empty `aliases.yaml`.
3. Rewrite legacy `user|claude` author enums per §4.
4. Append `.taskmaster/local/` to the project `.gitignore`; `git rm --cached` the moved/derived files if tracked.
5. Stamp new `schema_version`.

- **Major version bump** (schema/layout break). Bump plugin.json + marketplace.json + CHANGELOG per repo protocol; MCP server restart required after upgrade.
- Old-layout projects load read-only with a "migrate to team layout" prompt (same UX as v2→v3).
- Downstream consumers (CodeMaestro, The Fold) migrate per-project on first use; single-user projects migrate too (same layout, sync off) so there is exactly one schema.

## 11. Testing

- **Unit:** field-wise frontmatter merge (disjoint, conflicting, nested); renumber rewrite (structured fields, `[[refs]]`, alias append, ref_roots); alias-resolving lookups; ID collision detection; derived epic membership (incl. orphan `epic:` values → validation error).
- **Integration (the real gate):** two temp clones + a bare origin, driven through the actual MCP server: concurrent disjoint task edits → both land clean; same-field conflict → pushed-wins + sync note emitted; claim race → first-push wins, loser notified; duplicate-ID mint → self-heal renumber + refs rewritten + alias resolves; offline queue drain; pathspec jail (attempt to sneak a non-`.taskmaster` path onto the lane must fail).
- **Viewer:** unit tests for team-screen data shaping; route-mocked Playwright specs for team screen, assignee chips/filter, sync-notes inbox (per the agent-driven UI testing playbook; avoid the live-data e2e patterns that rotted per ISS-025).
- **Migration:** golden-dir fixture of a v3/v4 project → migrate → assert layout, then load and compare entity-for-entity.
- Taskmaster has no CI — tests run locally; the integration suite must be `pytest`-runnable in one command.

## 12. Out of scope / future

- Event-journal **activity feed** under `users/<handle>/` (Approach B) — additive later; never the source of truth.
- Central server / hosted sync; explicit team roster & roles; @mentions.
- Per-person notification routing; claim leases.
- Epic assignment.

## 13. Rejected alternatives

- **B — append-only event journals as source of truth:** conflict-free by construction but rewrites the persistence layer and kills direct file editability/grep (core workflows, e.g. "edit `B-071.md` directly").
- **C — semantic YAML merge driver on the monolith:** per-clone installation burden, silent-corruption risk, fixes neither IDs nor the per-user split.
- **Handle-prefixed or random IDs:** collision-proof offline but permanently uglier IDs; rejected in favor of self-heal + aliases since the fast lane makes collision windows small.
- **Separate `claims.yaml`:** redundant — the claimed task file is already effectively single-writer.
