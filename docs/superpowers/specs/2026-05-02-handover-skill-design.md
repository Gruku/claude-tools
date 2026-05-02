# `taskmaster:handover` — Skill Design

> **Status:** Draft, ready for user review
> **Date:** 2026-05-02
> **Tracks:** `v3-skills-002` (write skill), `v3-skills-015` (read MCP surface)
> **Parent design:** `plugins/taskmaster/docs/design-v3-narrative-continuity.md` §2
> **Mining input:** `plugins/taskmaster/docs/v3-skills-enrichment.md`

---

## 1. Purpose

A **Claude-drafted, user-approved** skill that captures full session state into a tracked, indexed artifact, so the next Claude session can resume without re-exploration. Handovers are a **context-injection optimisation** for the next AI session — not just a human-readable record.

PROGRESS.md remains the historic chronology (rolled-up project changelog). The handover is the per-session full record. They serve different consumers and don't overlap on responsibility:

| Artifact | Consumer | Time horizon | Content |
|---|---|---|---|
| `PROGRESS.md` | Project history scanners | All sessions, rolled up | Done · Decisions · Issues · Tasks touched (per session, append-only) |
| `.taskmaster/handovers/{date}-{slug}.md` | Next AI session resuming work | One session | Full state: what shipped, what's next, files of interest, gotchas, resume prompt |

## 2. Entry points and triggers

The skill is **standalone** (`taskmaster:handover`) but reachable from three trigger contexts. End-session and the auto-mode loop *call into* the skill rather than owning it.

### 2.1 Explicit user invocation

User trigger phrases (recognised by skill description):

- `"write a handover"`, `"capture state"`, `"save context"`
- `"wrap up"`, `"ending the day"`, `"done for today"`
- `"for tomorrow"`, `"next time"`, `"remind future me"`, `"future Claude"`
- `"i'm at 300k"`, `"before compaction"`, `"save before compact"`

### 2.2 Auto-offer from end-session

When end-session runs, it calls into the handover skill if **any** of:

- Session length > 60 turns
- Estimated conversation token count > 200k
- A task is in flight (`status: in-progress` or `stage > 1`) at session end
- User uttered a trigger phrase from §2.1 during the session

The user is asked: *"Write a handover for the next session?"* — confirmable, not forced.

### 2.3 Auto-offer mid-session

A lightweight token-watch signals the skill at 200k and 270k thresholds: *"You're approaching compaction. Write a handover now?"* — confirmable, not forced.

## 3. Authoring model — Claude-drafted, user-approved

The skill is a tool for Claude. The user role is **review and approve**, not write-from-scratch.

```
Trigger fires →
  Skill collects auto-extraction inputs (§7) →
  Skill picks tier from heuristics (§6) — user can override (--light / --standard / --full) →
  Claude drafts the full handover in tier shape →
  Claude presents draft as one document with section labels →
  User: "looks good" / "drop dispatch templates" / "add X to files of interest" →
  (If revision: Claude regenerates affected sections) →
  File written to .taskmaster/handovers/{date}-{slug}.md →
  Index updated in backlog.yaml (cap-30 enforced, see §10) →
  If supersedes: old handover edited (see §9) →
  Skill returns: "Handover written: {id}. Next session can resume from this."
```

The user types the minimum: a session topic (for slug generation if not auto-derivable) and approval / revision feedback. All body content, file extraction, and resume-prompt drafting is Claude's work.

## 4. Frontmatter contract

```yaml
---
id: 2026-05-02-handover-skill-design
date: "2026-05-02T18:00:00Z"
session_kind: milestone-complete   # see §5
tldr: "Handover skill design locked through brainstorming; spec drafted, plan next."
next_action: "Run spec self-review on the design doc, then invoke writing-plans."
task_ids: [v3-skills-002]          # may be [] for session_kind=exploration
branch: feature/taskmaster-v3
tip_commit: 8098893
context_size_at_write: "~180k"     # optional; flags pre-compaction handovers
supersedes: null                   # id of an older handover this replaces (chained handovers)
superseded_by: null                # filled in-place when a newer handover supersedes this one
---
```

**Mandatory:** `id`, `date`, `session_kind`, `tldr`, `next_action`, `task_ids` (may be empty array).

**Optional:** `branch`, `tip_commit`, `context_size_at_write`, `supersedes`, `superseded_by`.

`tldr` and `next_action` are the only fields a future Claude session reads by default (~200 tokens). All other fields are loaded on demand by `backlog_handover_get`.

## 5. Session kinds

Six values, each driving different consumer behaviour in start-session and pick-task retrofits.

| Kind | When | Body load on resume | Archive policy |
|---|---|---|---|
| `end-of-day` | Explicit wrap-up; default kind | Frontmatter only | FIFO past cap-30 |
| `context-handoff` | Pre-compaction safety capture (>200k tokens) | **Body loaded** — next session needs everything before context died | FIFO past cap-30 |
| `milestone-complete` | Chunk done, next chunk ready to dispatch (e.g., m1→m2, plan3→plan4) | **Body loaded** — dispatch templates and resume prompts are load-bearing | Chained: newer milestone-complete supersedes older for same `task_ids` |
| `pivot` | Direction change mid-flight (detour, plan switch) | **Body loaded** — captures *why* the change | FIFO past cap-30 |
| `exploration` | Investigation / infra / memory session, no task in flight (`task_ids: []`) | Frontmatter only | FIFO past cap-30 |
| `auto-stage` | Written by `auto-task` during the loop (per-stage stub) | Frontmatter only — orchestrator already has state | Bulk-archived to `_archive/auto/` on epic/phase completion, replaced by epic-level handover |

The "body in full" kinds get a hint in start-session: *"Latest handover is `context-handoff` — recommend reading body."* The light kinds get only frontmatter.

## 6. Body template — adaptive tiers

Three tiers picked from auto-offer heuristics; user can override (`--light` / `--standard` / `--full`).

### 6.1 Light tier

Selection: ≤30 turns, no in-flight task, kind in {`end-of-day`, `exploration`}.

```markdown
{tldr — one paragraph, freeform}

{2-3 bullets of what shipped or what was investigated}

{1-2 bullets — next action / open question}
```

Target: ~10-30 lines. Matches the existing fixture style (`2026-04-29-plan3-graph-variant-shipped.md`).

### 6.2 Standard tier

Selection: default for `milestone-complete` and `context-handoff`; or any session with 30-100 turns and an in-flight task.

```markdown
## Resume prompt

> {Verbatim text the next session can paste — explicit cd, branch, where to start, hard rules.}

## Where execution stands

{Status snapshot: branch, tip commit, what just landed, test counts, server state if relevant.}

## What shipped this session

| # | What | Where |
|---|------|-------|
| 1 | {accomplishment} | {commit / file / docs path} |

## What's next

{Numbered list of next-session actions — auto-parsed from `^\d+\.\s+` patterns in conversation if found, then user-edited.}

## Files of interest

| Group | Path | What | Why next session needs it |
|---|---|---|---|
| Touched | {path} | {what changed} | {why next session reads this} |
| Read | {path} | (referenced for understanding) | {why} |
| Relevant | {path} | (not touched but next-session-relevant) | {why} |

## Important non-obvious things

{Numbered gotchas, hidden invariants, environment quirks the next session WILL hit.}
```

Target: ~60-130 lines. Matches `2026-04-27-viewer-redesign-m1-complete-resume-m2.md` and `2026-05-02-v3-polish-013-handoff.md`.

### 6.3 Full tier

Selection: `pivot`, complex multi-pass sessions, audit handovers, or any session with >100 turns OR >200k tokens.

Standard tier plus:

```markdown
## Pending commits

{Bash commands ready to run, in code blocks. Auto-generated from `git status` if uncommitted state exists.}

## Per-task dispatch templates

{Verbatim subagent prompts for the next session to use. Only emitted when orchestration was the work.}
```

Target: ~150-200 lines. Matches `2026-04-27-viewer-redesign-execution-handoff.md`.

### 6.4 Tier override

User can force a tier with `--light`, `--standard`, `--full`. The skill respects the override but still auto-extracts; a `--light` override on a heavy session just trims output, not the inputs.

## 7. Auto-extraction sources

Claude assembles the draft using six sources, in order of precedence:

1. **`git status` + `git diff --stat`** — uncommitted state, line-count deltas. Drives "Pending commits" section in full tier.
2. **`git log {branch}..HEAD --name-only`** — files committed this session, commit messages, SHAs. Drives "What shipped this session" table.
3. **Conversation tool-call history** — Read / Edit / Write paths from this session. **Passed in by the orchestrator** at skill invocation; the skill does not scrape its own context.
4. **Task body anchors** — `task.anchors`, `task.docs.spec`, `task.docs.plan`, `task.related_handovers`, `task.related_lessons`, `task.related_issues`. Drives "Relevant" group in Files of interest.
5. **Conversation text regex** — extract paths matching `[a-zA-Z_][a-zA-Z0-9_/.-]*\.(md|py|js|css|html|yaml|json|ts|tsx|jsx)` mentioned in the conversation.
6. **Conversation numbered-step regex** — extract `^\d+\.\s+` lines that read like next-session actions (verb-led: "Run X", "Read Y", "Continue with Z"). Drives "What's next" section.

Sources are deduplicated and grouped:

- **Touched** = sources 1, 2, 3 ∩ written/edited
- **Read** = source 3 ∩ read-only
- **Relevant** = sources 4, 5 ∖ (Touched ∪ Read)

Each path is annotated by Claude with a one-line "what changed" + "why next session needs it" before being presented to the user.

## 8. On-disk layout

```
.taskmaster/
└── handovers/
    ├── 2026-05-02-handover-skill-design.md
    ├── 2026-05-02-v3-pass-bcd.md
    ├── 2026-05-01-plan6-design-pass-handoff.md
    └── _archive/
        ├── 2026-Q1/
        └── auto/                  # bulk-archived auto-stage stubs
```

Tracked normally in git (no force-add, no archive-before-push). Tracked the same way specs and plans are tracked.

**Slug generation:** `{date}-{slug}.md` where `slug` is `kebab-case(tldr)` truncated to 40 chars, with a `-N` suffix on collision.

## 9. Supersession (chained handovers)

When a new handover is written and **all** of:

- The new handover's `task_ids` overlap with the prior latest handover for the same task
- The prior latest handover's `session_kind` is `milestone-complete` or `pivot`

…then the skill performs a chained-supersession edit:

1. Sets `frontmatter.supersedes: {old_id}` on the new file.
2. **Edits the old file in-place**, prepending a callout block:
   ```
   > **SUPERSEDED {YYYY-MM-DD} by [{new_id}](./{new_filename}).**
   > The next session should read the newer handover instead. This file kept as a checkpoint reference.
   ```
3. Sets `frontmatter.superseded_by: {new_id}` on the old file.

This automates what your real `m1-complete-resume-m2.md` does manually at the top of the file.

## 10. Index in `backlog.yaml`

```yaml
handovers:
  - id: 2026-05-02-handover-skill-design
    date: "2026-05-02"
    session_kind: milestone-complete
    tldr: "Handover skill design locked..."
    next_action: "Run spec self-review..."
    task_ids: [v3-skills-002]
    superseded_by: null
```

**Cap: 30 entries.** Older entries move to `_archive/{YYYY-Q#}/` and are dropped from the index. Auto-stage handovers archive to `_archive/auto/` on epic/phase completion.

**Archive sweep** is the operation that enforces the cap: scan the index, find the oldest entries past 30, move their files into `_archive/{YYYY-Q#}/`, and drop them from `backlog.yaml`. Runs at end-session and as a side effect of every new handover write.

`backlog_handover_list` (added in `v3-skills-015`) supports filtering by `task_id`, `session_kind`, `since`, `limit` for the retrofits.

## 11. End-session integration

End-session **calls into** this skill — does not duplicate logic.

```
end-session flow:
  1. Generate Done/Decisions/Issues for PROGRESS.md (existing behavior).
  2. Check auto-offer heuristics (§2.2).
  3. If any heuristic fires: invoke taskmaster:handover skill.
  4. Continue end-session flow regardless of handover outcome.
```

Handover is additive — declining the offer leaves end-session running normally.

## 12. Token budget

| Surface | Tokens | Watch threshold |
|---|---|---|
| Index (30 entries × ~30 tokens) | ~900 | hard cap 30 |
| Latest handover frontmatter at session start | ~200 | — |
| Per-task `related_handovers` tldrs (≤3) | ~150 | cap 3 per task |
| Full body on demand | varies | uncapped, user-requested |

The skill itself emits ~200-2000 tokens depending on tier; this is one-time write cost, not in-context cost.

## 13. Out of scope (explicitly NOT in v1 of this skill)

- **Reading handovers via skill** — covered by `backlog_handover_get` / `backlog_handover_list` / `backlog_handover_latest` MCP tools (`v3-skills-015`) plus start-session/pick-task retrofits (`v3-skills-007`/`008`).
- **Migrating the 22 prototypes** in `docs/superpowers/plans/*-handoff.md` and `*-resume-*.md` — they stay as historical reference. New handovers go to `.taskmaster/handovers/` only.
- **Lessons extraction from handover content** — separate skill (`v3-skills-003`).
- **Issues extraction from handover content** — separate skill (`v3-skills-004`).
- **Cross-handover analytics** (e.g., "show me all pivots in the last month") — viewer responsibility, not skill responsibility.
- **Multi-author handovers** — single author per session is assumed.

## 14. Open questions for implementation

These are intentional unknowns the implementation plan will need to resolve:

1. **Tool-call history passing** — How does the orchestrator (live Claude session) pass tool-call paths into the skill cleanly? Two options: (a) require the user to pass them explicitly via skill arg; (b) the skill reads from a session-local file that the orchestrator writes to. Lean (b), but the file-write contract needs design.
2. **Heuristic token-counting** — "estimated conversation token count > 200k" requires a token estimator. The simplest is `len(conversation_text) / 4` as a rough estimator; precise counts require a tokenizer. For v1, a rough estimator is sufficient.
3. **Turn counting** — "> 60 turns" needs a precise definition. Likely user/assistant message-pair count, but the implementation plan should pin this against the orchestrator's turn-counter API.
4. **Slug collision handling at high frequency** — if two handovers land in the same minute with similar tldrs, the slug `-N` suffix could collide. Plan needs to lock the suffix-generation algorithm against concurrent writes.
5. **`auto-stage` handover format** — design doc says "brief"; this spec doesn't enumerate the exact fields. Should be locked in `v3-skills-010` (auto-task quality pass).

## 15. Acceptance criteria

The skill is shippable when:

- [ ] `taskmaster:handover` skill exists at `plugins/taskmaster/skills/handover/SKILL.md`.
- [ ] Trigger phrases from §2.1 reliably invoke the skill.
- [ ] Auto-offer heuristics from §2.2 fire correctly when end-session runs.
- [ ] All six `session_kind` values produce correct body shapes.
- [ ] All three tiers (light / standard / full) produce bodies in the documented size ranges (verified against the v3 fixture backlog).
- [ ] Auto-extraction sources 1-2 (git) and 4 (anchors) work reliably; sources 3, 5, 6 work end-to-end given an orchestrator that passes tool-call history.
- [ ] Supersession chain (§9) edits the old file correctly and updates frontmatter on both sides.
- [ ] Files land at `.taskmaster/handovers/{date}-{slug}.md`, indexed in `backlog.yaml` with cap-30 enforcement.
- [ ] One end-to-end dogfood: write a handover for the session that built this skill, into the v3 worktree, and confirm a fresh Claude session can resume from it without re-exploration.

## 16. References

- **Parent design:** `plugins/taskmaster/docs/design-v3-narrative-continuity.md` §2
- **Mining report:** `plugins/taskmaster/docs/v3-skills-enrichment.md`
- **Existing real handovers** (prototypes, do not migrate):
  - `docs/superpowers/plans/2026-05-02-v3-polish-013-handoff.md` (full tier example)
  - `docs/superpowers/plans/2026-04-27-viewer-redesign-m1-complete-resume-m2.md` (standard milestone-complete example)
  - `docs/superpowers/plans/2026-05-02-v3-pass-bcd-handoff.md` (lean standard example)
- **Existing fixture handovers** (design-doc-style):
  - `.fixture-kanban/.taskmaster/handovers/2026-04-29-plan3-graph-variant-shipped.md` (light tier example)
- **Backend helpers** (already implemented in `taskmaster_v3.py`):
  - `write_handover`, `read_handover`, `archive_handover`, `sync_handover_index`, `list_handover_ids`, `latest_handover_id`
- **Backlog tracking:** `v3-skills-002` (write skill, this spec) · `v3-skills-015` (read MCP surface)
