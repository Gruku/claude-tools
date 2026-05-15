# Taskmaster Progressive Disclosure — Design

**Date:** 2026-05-15
**Status:** Draft — pending user review
**Scope:** Plugin-wide token reduction via progressive disclosure across schema, MCP tools, ceremonies, and skill content.

## Problem

Taskmaster currently surfaces too much information for "glance" operations. Concrete measurements:

| Surface | Tokens today |
|---|---|
| Eager skill catalog (taskmaster only) | ~4,000 |
| `start-session` invocation (body + MCP) | ~6,000 |
| `pick-task` invocation (body + MCP) | ~6,200 |
| `backlog_get_task` typical | ~800 |
| `backlog_handover_get` typical | ~1,000–2,000 |
| `pick-task` lesson auto-load (step 5c) | ~1,500 (3 full lesson bodies) |

The system has no notion of "give me a glance" vs "give me everything". Every read returns the maximal payload. Skills load their full bodies on invocation even when the user only needs a quick lookup. Ceremonies (`start-session`, `pick-task`) eagerly inject 3–6k of state regardless of need.

The user often only wants to glance at a task, handover, or backlog status. The current design has no progressive disclosure — it's all-or-nothing.

## Goals

1. **Glance-first defaults.** Every read returns a compact summary unless the caller opts into depth.
2. **One uniform deepening flag.** `verbose=true` for full body; `sections=[...]` for surgical retrieval.
3. **Schema carries the glance representation.** A required `tldr` field on every entity makes summaries deterministic and authored, not extracted.
4. **Parallel handovers replace `latest`.** State of in-flight work is a list of open handovers across tracks, not a single pointer.
5. **Skill bodies and descriptions are slim.** Push detail into `references/`; eager catalog stays under 2k tokens.

## Non-goals

- Changing storage backend (still YAML + per-entity markdown).
- Reverse linkage denormalization (links stay one-directional with on-demand reverse traversal).
- New entity types or workflows.
- Breaking today's behavior — `verbose=true` reproduces current full-load semantics.

---

## Section 1 — Schema additions

### Universal field

Every entity gains a **required** `tldr` field at write time:

- Length: ≤200 characters
- Style: one to two sentences, present tense, action-oriented
- Enforcement: skills enforce on write; MCP create/update tools require it or auto-generate from first sentence of body and flag for user review

### Type-specific extras

```yaml
# tasks/<id>.md frontmatter
id: T-001
title: ...
tldr: "≤200 char essence"                 # NEW, required
next_step: "concrete next action"         # NEW, optional
# existing: status, priority, depends_on, related_issues, related_lessons,
#          docs: {plan, spec, design, analysis, roadmap}, notes, review_instructions

# issues/<id>.md frontmatter
id: ISS-007
title: ...
tldr: "≤200 char summary"                 # NEW, required
# existing: severity, status, impact, location, components,
#          related_tasks, fixed_in_task, duplicate_of

# lessons/<id>.md frontmatter
id: L-001
title: ...
tldr: "what to do, in one line"           # NEW, required
# existing: kind, tier, files, reinforce_count, task_titles_match, task_kinds

# handovers/<id>.md frontmatter — UNCHANGED on tldr/next_action
# But status semantics formalize → "open" | "closed" | "superseded"
```

### Linkage fields

No change. Linkages remain as ID arrays (`related_issues: [ISS-007, ISS-012]`). Resolution to ID+tldr happens at read time via the `expand_links` flag.

---

## Section 2 — MCP tool defaults

### Three uniform read modes on every `_get` and `_list` tool

```python
# Default — slim
backlog_get_task("T-001")
# → { id, title, tldr, next_step, status, priority,
#     depends_on: ["T-002"],
#     related_issues: ["ISS-007"],          # bare IDs
#     related_lessons: ["L-003"],           # bare IDs
#     docs_available: ["spec", "plan"],     # which sections exist, not contents
#     open_handovers: ["HND-012"] }
# ≈ 150 tokens

# Expanded linkages — ID + tldr pills
backlog_get_task("T-001", expand_links=true)
# ≈ 300 tokens

# Surgical section retrieval
backlog_get_task("T-001", sections=["spec"])
backlog_get_task("T-001", sections=["spec", "plan"])
# ≈ 500–1,000 tokens depending on section size

# Today's full-load behavior preserved behind flag
backlog_get_task("T-001", verbose=true)
# → full body + all docs.* inlined + frontmatter
# ≈ 1,500 tokens
```

### List tools symmetric

```python
backlog_list_tasks(status="todo")
# → array of slim entries (id, title, tldr, priority, status) ~30 tokens each

backlog_handover_list(status="open")
# → array of {id, task_ids, tldr, next_action, session_kind} ~50 tokens each
```

### Canonical section names per entity

| Entity | Sections | Source |
|---|---|---|
| Task | `notes`, `review_instructions` | inline in tasks/\<id\>.md |
| Task | `spec`, `plan`, `design`, `analysis`, `roadmap` | resolved from `task.docs.*` |
| Handover | `decisions`, `notes`, `blockers`, `where_id_start` | body sections in handovers/\<id\>.md |
| Issue | `repro`, `investigation`, `notes` | body sections in issues/\<id\>.md |
| Lesson | `why`, `what_to_do`, `examples` | body sections in lessons/\<id\>.md (already standardized) |

### Linkage rendering

Bare IDs by default. `expand_links=true` swaps IDs for `{id, tldr}` pills. Tldrs are cheap because `backlog.yaml` and per-entity files all carry them in frontmatter (read once into memory on `_load()`).

---

## Section 3 — Parallel handovers

### Status as source of truth

```yaml
# handovers/<id>.md frontmatter
status: open | closed | superseded
```

| Status | Meaning | When set |
|---|---|---|
| `open` | Active context, surface in start-session glance | On create (default) |
| `superseded` | Replaced by a newer handover for the same `task_ids` | Auto, when a new handover lists the same primary task |
| `closed` | Work finished or context stale | Auto (see smart-close rule); or user explicit |

### Grouping

By existing `task_ids` field. No new `track` field. Multiple handovers with disjoint task_ids = parallel tracks. Topic-level handovers not tied to a single task use the epic ID or a synthetic anchor task.

### Smart auto-close rule

When a task `T` transitions to `done`/`archived`:

For each open handover `H` where `T ∈ H.task_ids`:

**Auto-close only when ALL true:**
1. All `task_ids` in `H` are `done` or `archived`
2. `H.next_action` is empty OR refers only to done/archived items
3. `H.session_kind ∈ {"task-complete", null}`

**Otherwise:** stay open, but **flag** in start-session glance with reason:
```
HND-012  T-001 done but handover still open ▸ next_action references T-005
```

This preserves context-rich handovers (kind=context-handoff, exploration, blocker-noted) that outlive a single task.

### MCP surface changes

```python
# Deprecated (or aliased)
backlog_handover_latest()
# → equivalent to: backlog_handover_list(status="open", limit=1, sort="created_desc")

# Canonical
backlog_handover_list(status="open")
# → slim list of open handovers across all tracks

backlog_handover_list(task_id="T-001", status="open")
# → open handovers for one track
```

### start-session glance shows

- **Top 5 open handovers** by recency (cap at 5, `(+N more open — use --deep)` for overflow)
- Each entry: `HND-012 ▸ T-001: "rewriting auth middleware — next: backfill migration"` (~80 tokens)
- Flagged handovers (post-task-done with surviving forward-pointers) show inline

### Migration

- `status: "todo"` → `open`
- Handovers in supersession chains → `superseded`
- Handovers whose `task_ids` are all `done`/`archived` AND meet smart-close criteria → `closed`
- All others → `open`

---

## Section 4 — Ceremony redesign

### `start-session` glance (default, ~800–1,000 tokens)

```
1. backlog_status()                              # slim by default, ~400 tokens
   → counts + in-progress titles + 1-line phase + stale count
   (verbose=true adds full epic list + archived + completed history)
2. backlog_handover_list(status="open", limit=5) # ~400 tokens
   → open handovers grid; flagged ones surfaced
3. 1-line counts                                 # ~50 tokens
   → "3 new issues (1 P0) · 5 matched lessons · 2 stale tasks · 1 flagged handover"
```

Convention: every MCP tool follows the same default-slim / `verbose=true`-for-full pattern. Aggregate tools (`backlog_status`, `backlog_recap`) interpret slim/verbose as "compact dashboard" vs "full history". Single-entity tools interpret it as "frontmatter+tldr" vs "frontmatter+body".

### `start-session --deep` (everything today does)

- Full `backlog_status` (all epics + completed + archived)
- `backlog_recap` snapshot diff
- `backlog_lesson_digest` (≤30 entries)
- Core lessons in full (≤5)
- `backlog_issue_list(status="open")` full
- `backlog_last_session` PROGRESS.md entry

### `pick-task` glance (default, ~600–800 tokens)

```
1. backlog_get_task(id)                                  # slim, ~150 tokens
2. backlog_dependencies(id)                              # short, ~100 tokens
3. backlog_handover_list(task_id=id, status="open")      # ~150 tokens
4. backlog_lesson_match(title, files)                    # IDs + tldrs, ~100 tokens
5. backlog_issue_list(task_id=id)                        # filtered slim, ~100 tokens
6. Linkage pills (bare IDs)                              # ~50 tokens
```

### `pick-task --deep`

- Full task body + all `docs.*` inlined
- Full lesson bodies for matched lessons (~1,500 tokens)
- `backlog_blast_radius(predictive)` (~500 tokens)
- Handover bodies for context-handoff kinds

### Mid-session deepening

The user can ask Claude `show me HND-012` or `read the plan for T-001`, which routes to the existing `_get(verbose=true)` or `_get(sections=[...])` paths. The skill stays in glance mode; Claude chooses when to deepen a specific entity based on the actual question.

### `--deep` is explicit, not auto

User must type `--deep` (or equivalent phrase like "full briefing"). No auto-deepen on signals like "last session >7 days ago" — that hides the lever and surprises the user.

---

## Section 5 — Skill content slimming

### 5A. Skill bodies — push detail into `references/`

Target shape for every SKILL.md:

```
SKILL.md (≤1,500 tokens):
  - One-paragraph purpose
  - Decision tree (when to do what)
  - Tool invocations with brief rationale
  - Key rules / red flags
  - Pointers: "for edge case X, read references/x.md"

references/canonical-flow.md  (detailed walkthrough)
references/edge-cases.md      (exceptional paths)
references/examples.md        (worked examples)
```

The `references/` pattern already exists in 5 skills (handover, issue, lesson, auto-task, pick-task) — generalize to all of them.

### Per-skill targets

| Skill | Today | Target |
|---|---|---|
| `taskmaster` (router) | 2,277 | **800** (dense routing table only) |
| `start-session` | 3,025 | **1,300** |
| `pick-task` | 2,745 | **1,300** |
| `end-session` | 3,788 | **1,500** |
| `handover` | 2,487 | **1,300** |
| `issue` | 2,510 | **1,300** |
| `lesson` | 2,799 | **1,300** |
| `auto-task` | 2,478 | **1,500** |
| `review-gate` | 2,281 | **1,200** |
| `spec-review` | 2,553 | **1,300** |
| `auto-epic`, `auto-phase`, others | ~2,000 each | **≤1,200** |

Savings per invocation: ~40–60% on the skill body. When a deep path is taken, references/ load is paid — but only the relevant slice (~800 tokens), not all paths.

### 5B. Skill descriptions — audit the eager catalog

Target shape per description (≤60 words):

```
Sentence 1: what it does
Sentence 2: trigger phrases ("user says X, Y, Z")
Sentence 3: the hard rule ("only correct way to ...")
```

Drop: cross-references to other skills, multi-example trigger lists, explanatory rationale.

Eager catalog savings: ~4,000 → ~2,000 tokens (-50%) across the taskmaster skill set.

### 5C. Combined effect on a typical session

| Surface | Today | After |
|---|---|---|
| Eager skill catalog | ~4,000 | ~2,000 |
| `start-session` invocation | ~6,000 | ~2,100 |
| `pick-task` invocation | ~6,200 | ~2,000 |
| `backlog_get_task` typical | ~800 | ~150 |
| `backlog_handover_get` typical | ~1,500 | ~150 (slim) or ~1,500 (verbose) |

---

---

## Section 6 — Programmatic linking

Today linkages are manually-maintained ID arrays across multiple fields (`related_issues`, `related_lessons`, `depends_on`, `fixed_in_task`, etc.) and are asymmetric — writing the link on one side does not propagate to the other. This section makes linkage a first-class, server-maintained concern.

### 6A. Typed unified `links` schema

Replace the existing field proliferation with one `links` array per entity. Each link is a typed relation:

```yaml
# Old (multiple fields, asymmetric)
related_issues: [ISS-007, ISS-012]
related_lessons: [L-003]
depends_on: [T-002]
fixed_in_task: jira-001        # only on issues
duplicate_of: ISS-005           # only on issues

# New (one field, typed)
links:
  - {type: fixes,        target: ISS-007}
  - {type: relates_to,   target: ISS-012}
  - {type: informed_by,  target: L-003}
  - {type: depends_on,   target: T-002}
  - {type: blocks,       target: T-005}
  - {type: supersedes,   target: HND-008}
  - {type: duplicate_of, target: ISS-005}
```

**Canonical link types:**

| Type | Source | Target | Reverse type |
|---|---|---|---|
| `depends_on` | Task | Task | `blocks` |
| `blocks` | Task | Task | `depends_on` |
| `fixes` | Task | Issue | `fixed_in_task` |
| `fixed_in_task` | Issue | Task | `fixes` |
| `relates_to` | Any | Any | `relates_to` (symmetric) |
| `informed_by` | Task | Lesson | `informs` |
| `informs` | Lesson | Task | `informed_by` |
| `supersedes` | Handover | Handover | `superseded_by` |
| `superseded_by` | Handover | Handover | `supersedes` |
| `duplicate_of` | Issue | Issue | `duplicates` |
| `duplicates` | Issue | Issue | `duplicate_of` |
| `references` | Any | Any | `referenced_by` |

Each entity's `links` array can carry any subset. Validation in `backlog_validate` ensures targets exist and types are valid for the source/target entity pair.

### 6B. Symmetric link sync

When a link is written on one side, the server automatically writes the inverse link on the other side. The reverse type table above defines the inverse.

```python
backlog_link_create(source="T-001", target="ISS-007", type="fixes")
# Server writes:
#   T-001.links += [{type: fixes, target: ISS-007}]
#   ISS-007.links += [{type: fixed_in_task, target: T-001}]

backlog_link_remove(source="T-001", target="ISS-007", type="fixes")
# Server removes both sides.
```

**Rules:**
- Symmetric types (`relates_to`, `duplicates`/`duplicate_of`) sync both sides with the matching inverse.
- If a target entity is archived or deleted, links to it are flagged in `backlog_validate` but not auto-removed (preserves audit trail).
- Manual edits to `links` arrays still work; on save, the server reconciles inverses and reports drift.

### 6C. Auto-detection of inline references

The server scans entity body text on save for ID patterns and offers/auto-adds them as `references` links:

**Recognized patterns:**
- Bare IDs: `T-001`, `ISS-007`, `L-003`, `HND-012`, `IDEA-005`
- Wiki-style: `[[T-001]]` (preferred; renders as link in viewer)
- Mention-style: `@T-001`

**Behavior:**
- On save, find all ID mentions in the body
- For each unique ID, if no existing link to it, add `{type: references, target: <id>}`
- Symmetric sync (6B) adds `{type: referenced_by, target: <source>}` on the other side
- Auto-detection never removes links — it only proposes additions
- An entity's frontmatter flag `auto_link: false` opts out per entity

This means writing a handover that says "T-001 done, next start T-005" automatically materializes `references` links to both tasks. No separate frontmatter editing.

### 6D. Link-management MCP tools

New MCP surface:

```python
backlog_link_create(source, target, type, note=None)
# Creates link and its inverse. Validates target exists and type is valid.

backlog_link_remove(source, target, type=None)
# Removes link and its inverse. If type omitted, removes all link types between source and target.

backlog_link_query(source=None, target=None, type=None, depth=1)
# Returns matching links. depth>1 traverses transitively (e.g., depends_on chains).

backlog_link_validate()
# Returns drift report: orphan links (target missing), asymmetric pairs (one side has the link, peer doesn't),
# cycles in depends_on chains.

backlog_link_reconcile()
# Auto-fixes asymmetric pairs by writing the missing inverse. Reports unfixable drift.
```

**Slim view behavior:** `backlog_get_task(id)` slim mode returns `links` as bare ID array grouped by type:
```yaml
links:
  depends_on: [T-002]
  fixes: [ISS-007]
  informed_by: [L-003]
  references: [HND-012, T-005]
```
With `expand_links=true`, each entry expands to `{id, tldr}`.

### 6E. Computed/derived linkages (light touch)

Beyond explicit links, the server derives soft signals that skills can use without persisting:

- **Lesson match:** `backlog_lesson_match(task)` returns lessons whose `files` or `task_titles_match` patterns hit the task. Existing tool, kept.
- **Commit→Issue:** if a commit message in the task's branch mentions `ISS-007`, surface in pick-task/end-session as a *suggested* `fixes` link.
- **Files→Lesson:** if a task touched files matching a lesson's `files` glob, surface as suggested `informed_by`.

These are **suggestions**, not auto-writes — surfaced to the user/Claude during end-session for confirmation, then materialized via `backlog_link_create`.

### 6F. Migration

One-shot script during v3.X release:
1. For each entity, read existing fields (`related_issues`, `related_lessons`, `depends_on`, `fixed_in_task`, `duplicate_of`, `supersedes`).
2. Translate to typed `links` array entries.
3. Run `backlog_link_reconcile()` to add missing inverses.
4. Deprecate the old fields for one release (read-fallback if `links` is absent), then remove.

### 6G. Combined effect

| Concern | Before | After |
|---|---|---|
| Linkage fields per entity | 4–6 separate fields | One `links` array |
| Symmetric maintenance | Manual / error-prone | Server-managed |
| New link from prose mention | Separate edit | Auto-detected |
| Reverse traversal | Computed on demand | Free read (links are symmetric) |
| Slim-view linkage size | Spread across 4–6 fields | One grouped block, ~50 tokens |
| Validation (orphans, cycles) | None | `backlog_link_validate` + on-write checks |

---

## Migration plan

### Backfill tldr fields

For every existing task/issue/lesson without a `tldr`:
1. Auto-generate from the first sentence of body (≤200 chars, ellipsis if longer)
2. Set `tldr_autogen: true` in frontmatter as a flag
3. Next time the entity is read/edited, skill prompts: "Auto-generated tldr — review and confirm?"
4. On confirmation, drop the `tldr_autogen` flag

### Handover status migration

One-shot migration script:
- `status: "todo"` → `open`
- Supersession chains → mark `superseded`
- Apply smart-close criteria to inactive handovers → mark `closed` where eligible

### MCP tool backward compatibility

- `verbose=true` on every `_get` reproduces today's behavior bit-for-bit
- `backlog_handover_latest` aliased to `backlog_handover_list(status="open", limit=1, sort="created_desc")` for one release, then removed
- Existing callers that depend on full body keep working by adding `verbose=true`

### Skill body migration

- One skill at a time; each gets its own PR
- Order: `taskmaster` router → `start-session` → `pick-task` → `end-session` → rest
- Each PR includes: SKILL.md slim version + references/ split + smoke test that the skill still triggers and completes

### Link schema migration

One-shot script during the v3.X release that introduces Section 6:
1. For each entity (tasks, issues, lessons, handovers, ideas), read existing linkage fields (`related_issues`, `related_lessons`, `depends_on`, `fixed_in_task`, `duplicate_of`, `supersedes`, `superseded_by`).
2. Translate to typed `links` array entries using the canonical type table (Section 6A).
3. Run `backlog_link_reconcile()` to add missing inverses on both sides.
4. Run `backlog_link_validate()` and report any cycles or orphans for manual review.
5. Old fields kept readable for one release as a fallback (server reads `links` first; falls back to old fields if absent); removed in the next release.
6. Viewer updated in the same PR to render the new `links` block.

---

## Risks & open questions

| Risk | Mitigation |
|---|---|
| Slim default hides info Claude would have used to make a better decision | `--deep` is one keystroke; Claude can also deepen specific entities mid-conversation when the user's question warrants |
| Auto-generated tldrs are low-quality | Flagged via `tldr_autogen: true`; skill prompts for review; user-authored override always wins |
| Skills that reference each other break after slimming | One-at-a-time migration with smoke tests; integration test runs full `start-session → pick-task → end-session` flow |
| Parallel handover model accumulates open handovers | Smart auto-close + start-session flagging surfaces stale ones; user can bulk-close via CLI |
| `sections=[...]` requires authors to use stable headings | Migration tool validates lesson/handover/issue files against canonical heading names; flags drift in `backlog_validate` |
| Backward-incompatible callers in the wild | `verbose=true` opt-in restores today's behavior; deprecate `handover_latest` over one release with warning |
| Symmetric link sync creates write amplification (one user edit → two file writes) | Acceptable cost; writes are local + fast. Server batches updates within a single MCP call to minimize disk churn |
| Auto-detected inline refs create noisy false-positive links | Type defaults to `references` (lowest-weight); user can per-entity opt out via `auto_link: false`; never overwrites stronger explicit link types |
| Typed `links` schema migration breaks viewer / external consumers | Migration script runs `backlog_link_reconcile`; old fields read-fallback for one release; viewer updated in same PR |
| Cycles introduced in `depends_on` chains | `backlog_link_create` rejects writes that would form cycles; `backlog_link_validate` detects pre-existing ones during migration |

## Success criteria

- Eager taskmaster skill catalog ≤ 2,500 tokens (today ~4,000)
- `start-session` default ≤ 1,200 tokens (today ~6,000)
- `pick-task` default ≤ 1,200 tokens (today ~6,200)
- `backlog_get_task` default ≤ 200 tokens (today ~800)
- Every entity has a `tldr` (≤200 chars, authored or flagged-autogen)
- `--deep` mode preserves today's full-load behavior
- No regression in `auto-task`/`auto-epic`/`auto-phase` flows
- `backlog_validate` rejects entities missing required `tldr` (after migration grace period)
- Every entity carries `links` array; old `related_*`/`depends_on`/`fixed_in_task` fields removed after one release
- `backlog_link_validate` reports zero asymmetric pairs and zero cycles post-migration
- Auto-detected inline references materialize as `references`-type links on save
- Slim view's grouped `links` block ≤ 100 tokens for typical entity

## Out of scope (deferred)

- Section-aware editing (`backlog_update_task_section(id, section, content)`) — useful but a separate spec
- Cross-project glance ("show me open handovers across all my projects") — depends on v3 single-app
- Smart auto-deepening based on session signals — explicit flag for now, revisit after we see usage patterns
- Transitive link traversal beyond `depth=1` in `backlog_link_query` — present in API surface but full graph algorithms (shortest path, connected components, etc.) deferred
- Auto-write of computed/derived linkages (commit→issue, files→lesson) — Section 6E keeps these as suggestions only; auto-write requires its own confidence-tuning spec
