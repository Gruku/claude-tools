# taskmaster:lesson Skill — Design

**Status:** Approved
**Date:** 2026-05-03
**Task:** v3-skills-003
**Related design:** `plugins/taskmaster/docs/design-v3-narrative-continuity.md` §3
**Real-world patterns:** `plugins/taskmaster/docs/v3-skills-enrichment.md` §3 (8 lesson clusters mined from CodeMaestro v1)

## 1. Purpose

Project-scoped, structured knowledge that compounds. Where auto-memory captures *user* preferences globally, lessons capture *project* truths locally. Reinforcement makes the system *better* at the project the longer you use it.

Solves the user's stated pain: repetitive work and the same things breaking and being re-fixed across sessions.

The backend is already implemented in `plugins/taskmaster/taskmaster_v3.py` (`write_lesson`, `lesson_reinforce`, `lesson_eligible_for_promotion`, `lesson_eligible_for_decay`, `lesson_digest`, `lesson_match`) and the MCP layer in `plugins/taskmaster/backlog_server.py` (`backlog_lesson_create`/`list`/`get`/`update`/`reinforce`/`digest`/`match`). This skill is the **authoring + lifecycle** layer that wires them into a usable Claude flow.

## 2. Architecture overview

```
┌──────────────────────────────────────────────────────────┐
│ Mid-session                                              │
│   Claude detects recurring correction / near-mistake     │
│        ↓                                                  │
│   Emits inline:                                          │
│   <lesson-candidate kind="gotcha">…one-liner…</lesson-…> │
│   ↳ no tool call, just text                              │
└──────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────┐
│ End-session sweep (called from end-session skill)        │
│   1. Scan conversation context for <lesson-candidate/>   │
│   2. Read .taskmaster/lessons/_candidates.md (deferred)  │
│   3. Scan auto-memory feedback/* for 2+ similar in proj  │
│        ↓                                                  │
│   Show list: [Promote | Defer | Discard] per candidate   │
│   Then:    [Reinforce loaded lessons that applied]       │
│   Then:    [Suggest core promotion if eligible]          │
└──────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────┐
│ Write flow (taskmaster:lesson — full skill)              │
│   - 5 entry points (write/reinforce/sweep/retro)         │
│   - Full auto-extraction with user review                │
│   - Calls existing backlog_lesson_create on approve      │
└──────────────────────────────────────────────────────────┘
```

Three ambient flows compose around this:

- **Reinforce (immediate)**: when Claude cites `L-NNN` in a response, it calls `backlog_lesson_reinforce` right then.
- **Reinforce (sweep)**: end-session lists lessons cited or trigger-loaded this session and asks which applied.
- **Auto-promote suggestion**: when `reinforce_count >= 5` and `kind ∈ {gotcha, anti-pattern}`, end-session surfaces "L-NNN eligible for core — promote?" User-confirmed, never silent.

## 3. The `<lesson-candidate>` XML marker system

### 3.1 Tag schema

```xml
<lesson-candidate kind="gotcha" topic="multi-tab fanout" scope="point">
useEffect reading useLocation().state without active-tab guard.
Recurred on cb6927c0; fix is chatId === activeTabId early-return.
</lesson-candidate>
```

| Attr    | Required | Values                                    | Default     | Purpose                                                                       |
|---------|----------|-------------------------------------------|-------------|-------------------------------------------------------------------------------|
| `kind`  | optional | `pattern` \| `anti-pattern` \| `gotcha`   | none        | Lets sweep filter and pre-fill the lesson `kind` field.                       |
| `topic` | optional | one-line free string                      | none        | Grouping handle for the sweep UI; one-word handle preferred.                  |
| `scope` | optional | `point` \| `session`                      | `point`     | `session` flags the whole session for retro-extraction (see §3.6).            |

**Body:** 1–3 sentences — what it is and why it matters. No file paths or commits required (auto-extracted later if promoted).

### 3.2 Tag conventions (grep-optimized)

- **Stable opening anchor**: `<lesson-candidate ` (trailing space) — never abbreviated, never variant. One regex matches everywhere.
- **Tags on their own lines**: opening + closing tags get dedicated lines. Body can be multi-line.
- **No nesting**: candidates don't contain other candidates.
- **Attrs are double-quoted**: `kind="gotcha"`, never single-quoted, never unquoted.

These conventions exist so a literal `grep '<lesson-candidate '` over chat logs Just Works.

### 3.3 When Claude emits the tag (mid-session heuristics)

Claude flags a candidate when ANY of:
1. **User correction repeats** — same correction made earlier this session, OR Claude detects a feedback-memory entry that matches a code pattern it just produced and got corrected on.
2. **Bug second-encounter** — Claude is debugging an issue and notices the resolution path matches an issue debugged earlier (same root cause shape).
3. **Architectural ground rule emerges** — user states a project rule conversationally ("we always X here", "never Y in this codebase") not yet captured as a lesson.

Heuristic for emit, not a hard rule. Silence is the default when uncertain.

### 3.4 Candidate-discovery scans

These scans are specifically for finding `<lesson-candidate>` tags. (Feedback-memory scanning for auto-suggestion is a separate input handled in §5 step 3 — not a candidate scan.)

End-session sweep walks the first two routinely; the third is on-demand only:

1. **In-context scan** (routine, current session): Claude greps its own conversation memory for `<lesson-candidate `. Fastest path; accurate while conversation hasn't compacted.
2. **Deferred-file read** (routine): read `.taskmaster/lessons/_candidates.md`. Anything persisted from prior end-sessions or PreCompact hook.
3. **Disk transcript scan** (on-demand only, not in routine sweep): `backlog_lesson_candidates_scan(days=7)` greps recent `.jsonl` files in this project's `~/.claude/projects/...` directory. Invoked when the user explicitly asks to scan history (e.g., "what did I flag this week?") or when end-session detects compaction happened mid-session and offers it as a recovery option. Catches:
   - Tags emitted in compacted-away turns
   - Tags emitted in earlier sessions never wrapped

### 3.5 Compaction handling

The risk: when Claude `/compact`s, the literal `<lesson-candidate>` tags in past turns get summarized away.

Three defenses, in order:

1. **PreCompact hook** (planned in v3-skills-006): hook scans the about-to-be-compacted transcript for `<lesson-candidate>` tags and writes any new ones to `_candidates.md` before compaction completes. The durable defense.
2. **Disk transcript fallback**: scan #3 above re-reads the raw `.jsonl` (which is uncompacted on disk). Tags are recoverable.
3. **Soft "important" defer**: when Claude emits a tag and considers it high-value (rare), it MAY also call `backlog_lesson_candidate_defer` immediately. Documented in `references/marker-format.md`. Most candidates skip this — text-only is the default.

### 3.6 Session-level scope (`scope="session"`)

When the sweep encounters a `scope="session"` candidate:

1. The candidate is treated specially — it does not propose a single lesson. Instead, it stamps the active handover with `flag_for_review: true` + `review_reason: <topic or body summary>`.
2. The user can later (days/weeks later) invoke the skill: *"scan handover 2026-05-03-autonomous-3hour for retro lessons"*. This is the **session-retro** entry point (§4.2). The skill walks the session's commits, auto state, and (if available) transcript jsonl, and proposes a batch of candidates.
3. The user reviews + approves the ones worth keeping. Same write subflow as point lessons.

Out of scope for this skill but tracked as future enrichment: richer session-retro analytics (productivity metrics, task ordering, tool-usage breakdown). See §11.

### 3.7 Cross-session search

User-facing affordances:

- **Same-session list** (no tool needed): user asks "what lesson candidates have I flagged so far?" — Claude scans its context and replies.
- **Cross-session grep** (new MCP tool, see §8): `backlog_lesson_candidates_scan(days=7, kind="")` scans `~/.claude/projects/<this-project>/*.jsonl` within a window. Returns matches with their source (session id + line number) for traceability.

## 4. Skill flow

### 4.1 Trigger phrases (SKILL.md description field)

```
Write/reinforce/promote a project-scoped lesson. Invoke when the user
says 'remember this', 'save as a lesson', 'learn this lesson',
'memorize this', 'this keeps happening', 'we always do X here',
'we got burned by this last time', 'promote candidate to lesson',
'review lesson candidates', 'flag this session for retro'.
Auto-offered by end-session when <lesson-candidate> tags or deferred
candidates exist. Mid-session, emits <lesson-candidate> XML tags to
flag knowledge to capture later.
```

### 4.2 Five entry points

The SKILL.md flow branches on which entry path triggered it:

| Entry point            | Trigger                                                  | Subflow                                                          |
|------------------------|----------------------------------------------------------|------------------------------------------------------------------|
| `write-from-context`   | User says "save as lesson" / "learn this lesson"         | Write subflow with intake = current session context              |
| `write-from-candidate` | end-session sweep "Promote" action                       | Write subflow with intake = candidate body + session context     |
| `reinforce-immediate`  | Claude cited an L-id in its response                     | Call `backlog_lesson_reinforce(L-NNN)`                           |
| `reinforce-sweep`      | end-session "which lessons applied?" sub-step            | For each picked id, `backlog_lesson_reinforce`                   |
| `session-retro`        | User: "scan handover X for retro lessons"                | Batch candidate proposal from one flagged handover               |

Each shares the same **write subflow** but feeds it different intake.

### 4.3 Write subflow (the heart)

1. **Determine intake source**: candidate XML body, deferred-file entry, raw user request, or session-scoped handover.
2. **Auto-extract** every field:
   - `kind` — from candidate `kind` attr OR inferred from session tone (corrections → anti-pattern; "we always" → pattern; "watch out" → gotcha).
   - `triggers.files` — from `git diff --name-only HEAD~N` collapsed to globs (e.g., `src/auth/login.ts` + `src/auth/session.ts` → `src/auth/**`).
   - `triggers.task_titles_match` — keyword extraction from current/recent task titles.
   - `why` — drafted from candidate body + bug/correction context Claude has.
   - `what to do` — drafted from the resolution path, as numbered steps.
   - `examples` — task ids of session-touched tasks + commit shas (`git log --oneline HEAD~N`).
3. **Apply user hint** if the invocation included one (e.g., "focus on multi-tab" → weights extraction toward that topic).
4. **Present the full draft** to the user for review/edit.
5. **On approve**: `backlog_lesson_create(title, kind, body, files=[...], task_titles_match=[...], related_tasks=[...])`. Echo back the new `L-<NNN>`.
6. **If candidate had `scope="session"`**: do NOT modify any existing handover. Instead, buffer the flag for the next handover write this session: when end-session invokes the handover skill (v3-pre-2 step in `end-session/SKILL.md`), it passes `flag_for_review=true` + `review_reason=<topic or first-line of candidate body>` to `backlog_handover_create`. If end-session is skipped (user wraps without writing a handover), the flag is dropped — `scope="session"` semantics require an associated handover artifact to flag.

### 4.4 Reinforce subflow (immediate)

When Claude proactively cites a lesson in a response (e.g., "Per L-007, you should…"), it calls `backlog_lesson_reinforce("L-007")` after the citation. The user pushing back later does NOT decrement automatically (over-counting is acceptable; user can `backlog_lesson_update` to correct).

The MCP tool's existing return already includes the eligibility hint when `reinforce_count` crosses the promotion threshold — the skill surfaces this inline.

### 4.5 Reinforce subflow (sweep)

end-session sub-step:
1. Show lessons that were trigger-loaded at start-session OR cited mid-session.
2. Multi-select: which actually applied?
3. For each: `backlog_lesson_reinforce(L-NNN, source="end-session")`.
4. After reinforcement, if any cross the eligibility threshold, surface "L-NNN eligible for core. Promote?" → user confirms → `backlog_lesson_update(L-NNN, tier="core")`.

## 5. End-session retrofit

A new sub-step is inserted into `plugins/taskmaster/skills/end-session/SKILL.md` **before** the existing v3-pre-2 (handover offer):

> **v3-pre-2a: Lesson candidate sweep.**
>
> Inputs (gathered in this order, then merged for review):
> 1. **Candidate-discovery scans** (see §3.4): in-context scan + deferred-file read.
> 2. **Auto-suggestion source**: scan auto-memory `feedback/*.md` for 2+ similar entries this project. (Separate from candidate scans — these are *promotion suggestions*, not pre-flagged candidates.)
>
> Then:
> 3. If any candidates or suggestions exist, ask: *"Found N lesson candidates. Review now?"* (user-confirmed; default skip)
> 4. For each candidate: `Promote` (invokes `taskmaster:lesson` write subflow) | `Defer` (calls `backlog_lesson_candidate_defer`) | `Discard` (just drop).
> 5. Buffer any `scope="session"` candidates for the upcoming handover write (see §4.3 step 6).
> 6. Then: list lessons that were trigger-loaded or cited this session, ask "which applied?" → `backlog_lesson_reinforce` for picks.
> 7. If any reinforced lesson now has `reinforce_count >= 5` + eligible kind, ask: *"L-NNN eligible for core tier. Promote?"* → `backlog_lesson_update(L-NNN, tier="core")`.

Auto-offer triggers (end-session decides whether to invoke v3-pre-2a):
- Any `<lesson-candidate>` tag present in current conversation context.
- Any entries in `.taskmaster/lessons/_candidates.md`.
- Any feedback memory cluster with 2+ entries this project.

If none of these apply, the sweep is skipped silently — no prompt.

## 6. Promotion UX

- **Auto-suggest**, never silent. Server-side `lesson_eligible_for_promotion()` already exists.
- Surfaces during the sweep step (§5 step 7) and also on the immediate-reinforce response (the existing `backlog_lesson_reinforce` MCP tool already includes "Eligible for promotion to core tier" in its return).
- User confirms; `backlog_lesson_update(L-NNN, tier="core")` does the flip.
- **Core cap handling**: if core tier would exceed 5 entries, the lesson with lowest `reinforce_count` in core is offered for demotion: *"Core tier full (5/5). Demote L-002 (count 7) back to active to make room?"* User-confirmed. If declined, the new lesson stays active and the eligibility prompt is suppressed for the rest of the session.

## 7. Decay UX

- **Silent auto-retire** server-side. Already implemented (`lesson_eligible_for_decay`): 180d unreinforced + `reinforce_count < 2` → `tier: retired`.
- end-session sweep optionally emits **one info line** if any lessons retired this session: *"Retired N stale lessons (review with `backlog_lesson_list --tier retired`)."* No prompt, no action — signal only.

## 8. Backend / MCP additions

### 8.1 Backend (`plugins/taskmaster/taskmaster_v3.py`)

```python
LESSON_CANDIDATE_KINDS = ("pattern", "anti-pattern", "gotcha")
LESSON_CANDIDATE_SCOPES = ("point", "session")

def lesson_candidates_path(backlog_path: Path) -> Path: ...
def lesson_candidates_read(backlog_path: Path) -> list[dict[str, Any]]: ...
def lesson_candidates_defer(
    backlog_path: Path,
    *,
    title: str,
    kind: str = "",
    topic: str = "",
    scope: str = "point",
    context: str = "",
) -> int: ...        # returns the new entry's index
def lesson_candidates_clear(backlog_path: Path, *, indices: list[int]) -> int: ...

def scan_transcripts_for_candidates(
    project_dir: Path,
    *,
    days: int = 7,
    kind_filter: str = "",
) -> list[dict[str, Any]]: ...

# Handover frontmatter flag (small, mirrors apply_supersession)
def apply_handover_review_flag(
    backlog_path: Path,
    *,
    handover_id: str,
    review_reason: str,
) -> Path: ...
```

`_candidates.md` file format — a YAML document with a `candidates` list, wrapped in a fenced block so the file remains markdown-readable:

```markdown
# Lesson Candidates (deferred)

> Auto-managed by `taskmaster:lesson`. Edit by hand only if the file is corrupt.

```yaml
candidates:
  - title: "Multi-tab fanout: useEffect reading useLocation().state"
    kind: gotcha
    topic: multi-tab fanout
    scope: point
    context: "session 2026-05-03; commit cb6927c0"
    deferred_at: "2026-05-03T14:22"
  - title: "..."
    kind: pattern
    topic: ...
    scope: point
    context: "..."
    deferred_at: "..."
```
```

Each entry's `index` (used by `backlog_lesson_candidate_drop`) is its 0-based position in the list.

### 8.2 MCP tools (`plugins/taskmaster/backlog_server.py`)

Four new tools:

```python
@mcp.tool()
def backlog_lesson_candidate_defer(
    title: str,
    kind: str = "",
    topic: str = "",
    scope: str = "point",
    context: str = "",
) -> str: ...   # "Deferred candidate #N: <title>"

@mcp.tool()
def backlog_lesson_candidates_list() -> str: ...   # markdown bullet list

@mcp.tool()
def backlog_lesson_candidate_drop(index: int) -> str: ...   # "Dropped candidate #N"

@mcp.tool()
def backlog_lesson_candidates_scan(
    days: int = 7,
    kind: str = "",
) -> str: ...   # markdown grouped by source session
```

Plus integration with the existing handover writer to support the new optional frontmatter:

```python
# backlog_handover_create gains two new optional kwargs:
def backlog_handover_create(
    ...,
    flag_for_review: bool = False,
    review_reason: str = "",
) -> str: ...
```

### 8.3 Existing tools used as-is

- `backlog_lesson_create` — write side after sweep promotes
- `backlog_lesson_reinforce` — immediate + sweep + user-initiated
- `backlog_lesson_update` — manual `tier=core` promotion
- `backlog_lesson_list`, `backlog_lesson_get`, `backlog_lesson_match`, `backlog_lesson_digest` — read flows used by start-session and pick-task

## 9. Skill file structure

```
plugins/taskmaster/skills/lesson/
├── SKILL.md                      # 5 entry points + write subflow
├── references/
│   ├── marker-format.md          # XML schema, attrs, emit heuristics
│   ├── auto-extraction.md        # per-field extraction sources
│   ├── reinforce-flows.md        # immediate + sweep + user-initiated
│   ├── promotion-decay.md        # core tier promotion + auto-retire
│   └── session-retro.md          # scope="session" + flagged-handover analysis
└── templates/
    └── lesson-body.md            # Why / What to do / Examples skeleton
```

`references/*.md` mirror handover's pattern: each one expands a single concern referenced from SKILL.md.

## 10. Lesson file frontmatter (existing — documented for completeness)

```yaml
---
id: L-007
title: "Always read auth/session.ts before editing auth flow"
kind: gotcha                        # pattern | anti-pattern | gotcha
triggers:
  files: ["src/auth/**"]
  task_titles_match: ["auth", "login", "session"]
  task_kinds: []
tier: active                         # active | core | retired
reinforce_count: 3
last_reinforced: "2026-04-25"
created: "2026-03-12"
related_tasks: [features-001, features-009]
related_issues: [ISS-014]
---
```

Body: `## Why` / `## What to do` / `## Examples` sections.

## 11. Out of scope / future enrichment

These items were considered and explicitly deferred to keep v3-skills-003 focused. Tracked here so the spec can be cross-referenced when scoping future work.

- **Deeper session retrospective analysis** (option B from the brainstorm). The simple version captures: flag during session → persist in handover → run retro analysis later. A richer product could add productivity metrics, task ordering analysis, tool-usage breakdown, and a dedicated review skill. If pursued, this becomes a future task (e.g., v3-skills-016) with its own spec and an enriched `backlog_handover_list` filter set ("show me autonomous runs that lasted >2h, sorted by commits/hour").
- **Cross-project lesson sharing**: lessons are project-local by design. A future enhancement could allow promoting a lesson to user-level (auto-memory) if it generalizes across projects.
- **Lesson collisions / dedup**: when a write proposes a near-duplicate of an existing lesson, the skill could surface "this looks like L-014 — reinforce that instead?" Currently the user manually checks; future work could add similarity scoring.
- **Lesson application telemetry**: track which lessons get cited vs. trigger-loaded but ignored. Surface as a "noisy lesson" report.

## 12. Trade-offs and rejected alternatives

- **Mid-session interrupt for auto-suggestion** (rejected): jarring; lessons take time to fill in; breaks flow. End-session sweep is the right place — user is already in wrap mode.
- **Asking kind/why/what-to-do field-by-field** (rejected): user preferred full auto-extraction with review. Quality risk on auto-summarized "why" is mitigated by the review step before commit.
- **Mid-session MCP tool for marker emission** (rejected): tool calls are heavier than typing XML. Inline tags are zero-cost and grep-able from chat logs directly.
- **Reusing lesson tier `candidate` for in-flight markers** (rejected): bloats `lessons/` directory and the lesson index. Separate `_candidates.md` keeps concerns clean.
- **Tracking in `auto/state.json`** (rejected): mixes session-ephemera with lesson lifecycle.

## 13. Test coverage targets

- Backend: candidates round-trip (defer → read → clear), scope handling, scan_transcripts regex, apply_handover_review_flag idempotency.
- MCP: each new tool's happy path + missing-args + error format consistency with siblings.
- Skill lint: SKILL.md frontmatter has all triggers from §4.1, all 5 references exist with non-trivial content, all 4 entry points are documented.
- End-session retrofit: v3-pre-2a sub-step exists, references invoked tools, doesn't break v2 flow.

## 14. Dependencies

- **v3-skills-001** (mining) — done; informs §3.3 heuristics and §11 future-work catalog.
- **v3-skills-002** (handover skill) — done; provides the same playbook + handover-frontmatter substrate the `flag_for_review` field rides on.
- **v3-skills-006** (PreCompact hook) — adjacent. Compaction defense (§3.5) works without it via the disk-transcript fallback, but the hook gives durable persistence. Skill ships before the hook; hook enriches it later.
- **v3-skills-007/008** (start-session/pick-task retrofit) — these consume the lesson digest + match flows. They depend on this skill landing first.
