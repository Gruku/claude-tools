# Taskmaster Ideas — Design Spec

**Date:** 2026-05-09
**Status:** approved (brainstorming complete, ready for implementation plan)
**Project:** Taskmaster plugin (`plugins/taskmaster/`)

## Problem

Tasks are heavyweight: they have status, priority, epic placement, dependencies, viewer real estate, session linkage. The user has accumulated many tasks that started life as "things I might want to do someday" — those tasks now create noise in the actionable backlog instead of helping. They want a lighter surface for *unvalidated thoughts*: things to maybe explore, jokes that might become features, half-baked observations worth recording, parking-lot items. Light enough that logging one feels free; structured enough that an idea can later grow into a task / lesson / issue without retyping.

A second, related concern: the user has not seen the existing `<lesson-candidate>` flow fire in practice. Before cloning that pattern for Ideas, we audit it and address the root cause in the same change.

## Goals

1. **Per-project surface** for ideas, lighter than tasks.
2. **AI-loggable**: Claude logs ideas mid-session via three paths (explicit slash, fuzzy candidate tag, sharp auto-log).
3. **Linkable**: an idea can reference tasks / issues / lessons, and can be promoted into a task with one call.
4. **Extensible without schema breaks**: most fields optional/freeform.
5. **Symmetric viewer experience**: dedicated Ideas screen alongside Issues / Lessons.
6. **Fix the lesson-candidate flow** (folded in — root cause is one shared file).

## Non-goals

- Bulk operations on ideas. Per-item is fine until volume warrants more.
- A user-tunable capture-mode setting. Heuristic lives in the prompt; revisit if v1 is noisy.
- A separate Ideas dashboard widget. Defer until the dedicated screen proves itself.
- Cross-project idea browsing. Wait for the v3 single-app rework.
- Cutting the existing MCP tool surface. Captured separately as the user's meta-idea (file an `IDEA-NNN` for it once Ideas ship).

## Lesson-candidate audit (folded in)

**Root cause.** The lesson-candidate emit guidance lives in `plugins/taskmaster/skills/lesson/SKILL.md` (lines 27–39) and its `references/marker-format.md`. Claude only loads these when the lesson skill is explicitly invoked. During ordinary coding sessions the lesson skill is not loaded, so Claude never sees the "emit `<lesson-candidate>` when X happens" instruction and never emits tags. End-session's scan logic is correct — it finds nothing because there is nothing to find. The disk-transcript fallback (`backlog_lesson_candidates_scan`) is restricted to the compaction-recovery path and is never run in normal sessions.

**Fix recommendation.** Add a compact "mid-session behavior" section to `plugins/taskmaster/skills/start-session/SKILL.md`. start-session is loaded at the top of every session in a v3 project, so its content stays in working context throughout. The new section enumerates the three lesson-emit heuristics (repeated correction, bug second-encounter, architectural ground rule) and points at `references/marker-format.md` for the tag schema. Same surface gets idea-emit heuristics added (see below). No changes to end-session, MCP tools, or the candidate-storage layer — they already work correctly given populated input.

**Implications for Ideas.** Diverge from the lesson-candidate storage pattern: we do **not** introduce an `idea_candidates.md` deferred-storage file or `_candidates_defer/list/clear` MCP machinery. Idea-candidates commit directly via `backlog_idea_create(status="candidate")` at end-session — that gives us the same "review-later" affordance via the viewer's status chip without parallel storage. We do copy the end-session in-context tag-grep approach, and we do put the emit guidance in start-session (not in the Ideas skill alone) — that is the one fix that actually makes both flows fire.

## Architecture

### On-disk shape

Lives at `<backlog parent>/ideas/`, mirroring `issues/` and `lessons/`:

```
.taskmaster/
  ideas/
    IDEAS.md             # append-only chronological index
    IDEA-001.md          # one file per idea
    IDEA-002.md
    ...
```

ID allocation: `next_idea_id()` helper, `IDEA-{n:03d}` zero-padded, sequential — same pattern as `next_issue_id()` / `next_lesson_id()`.

### `IDEA-NNN.md` shape

```yaml
---
id: IDEA-007                          # required, allocated
title: Per-task spike budgets         # required
created: 2026-05-09T14:30:00Z         # required, auto (ISO-8601 UTC)
created_by: Claude | user             # required
status: ""                            # optional, freeform string
tags: []                              # optional, freeform strings
related_tasks: []                     # optional, e.g. ["v3-release-007"]
related_issues: []                    # optional
related_lessons: []                   # optional
promoted_to: null                     # optional, set when idea becomes a task
archived: false                       # optional, soft-delete flag
---
freeform markdown body — anything goes, including HTML, code blocks, sketches
```

Validators run only on `id`, `title`, `created`, `created_by`. Every other field is freeform passthrough — extensible without schema breaks.

### `IDEAS.md` index

Append-on-create, rewrite-affected-line on update / archive / promote:

```markdown
# Ideas

- 2026-05-09 14:30 — [IDEA-007](IDEA-007.md) — Per-task spike budgets _(exploring)_
- 2026-05-09 11:02 — [IDEA-006](IDEA-006.md) — Auto-tag related_tasks from git diff
- 2026-05-08 22:40 — [IDEA-005](IDEA-005.md) — ~~Replace YAML with JSON~~ _(archived)_
```

The index is regenerable from per-idea files. Every `_create` / `_update` rewrites the affected line in place. No external resync tool — recovery, if ever needed, is a one-liner script.

## MCP tool surface

Three tools. Drops the get / archive / promote / resync convenience tools — `_list(idea_id=...)` covers get; archive and promote are one-arg `_update` calls; resync runs internally on every write.

| Tool | Args | Behavior |
|---|---|---|
| `backlog_idea_create` | `title, body="", tags=[], status="", related_tasks=[], related_issues=[], related_lessons=[], created_by="Claude"` | Creates IDEA-NNN.md, appends line to IDEAS.md, returns `{id, path}`. |
| `backlog_idea_list` | `idea_id=None, status=None, tag=None, archived=False, related_task=None, summary=False, limit=None` | Filtered list. With `idea_id` returns single full record (replaces `_get`). With `summary=True` returns frontmatter only, not body. |
| `backlog_idea_update` | `idea_id, **fields` | Patches frontmatter / body, rewrites IDEAS.md line. Covers archive (`archived=True`), promote (`promoted_to="T-XYZ"`), status changes, edits. |

Wired through the FastMCP server in `taskmaster_v3.py` next to `backlog_issue_*`.

## Capture surfaces

Three entry points; one heuristic decides which one Claude takes.

### A. `taskmaster:add-idea` skill (explicit, user-driven)

Slash form:
```
/add-idea per-task spike budgets — track effort vs estimate to flag scope drift early
/add-idea Auto-tag from git diff --tags automation,perf --status exploring --related-task v3-release-007
```

Natural-language form:
```
"save this as an idea: ..."
"remember this idea: ..."
```

Skill:
1. Parses optional flags (`--tags`, `--status`, `--related-task`, `--related-issue`, `--related-lesson`).
2. Title auto-derived from first sentence/clause if not provided; body = full text.
3. Calls `backlog_idea_create(...)`.
4. Announces `Logged as IDEA-NNN — "<title>"`.

This skill is the canonical write path. Mid-session auto-log and end-session candidate triage both call into the same MCP tool, not the skill.

### B. Inline `<idea-candidate>` tag (fuzzy, deferred)

When Claude detects an *ambient* idea — hedged phrasing, tangential to the current task, low confidence — it emits a tag inline, no tool call:

```xml
<idea-candidate title="Auto-tag ideas from git diff" tags="automation,viewer">
User mentioned in passing that linking ideas to recent files would be useful — flagging for end-session.
</idea-candidate>
```

End-session scans for these and commits them directly with `status: "candidate"`.

### C. Confidence-threshold auto-log (sharp, immediate)

When the user *explicitly* states an idea — "I want to try X", "we should explore Y", "future work: Z", "save this idea: ..." — Claude calls `backlog_idea_create` mid-conversation and announces inline:

> _Logged as IDEA-008 — "Per-task spike budgets"_

### Heuristic (for B vs C)

Lives in `start-session/SKILL.md` and `taskmaster:taskmaster` router so it's loaded throughout every session.

- **Auto-log (path C) when:**
  - Explicit framing: "idea:", "future work:", "for later:", "I want to try", "we should explore", "let's eventually"
  - Direct request: "remember this idea", "save this idea", "that's a good idea, log it"
  - Concrete-and-named: a specific feature/change with a clear noun and verb

- **Candidate (path B) when:**
  - Hedged / ambient: "hmm could be cool…", "maybe at some point", "we could think about"
  - Tangential to the current task — user is mid-flow on something else
  - Concept is fuzzy or speculative

- **Skip entirely when:**
  - User is thinking out loud about the immediate task
  - User explicitly says not to capture
  - Idea is already covered by an existing task/idea (search via `backlog_idea_list` before logging)

## End-session integration

`taskmaster:end-session` already scans for `<lesson-candidate>` tags. We extend the scan:

1. Find both `<lesson-candidate>` and `<idea-candidate>` tags in the in-context transcript.
2. **Commit candidates directly** — no per-item prompt (per user's "no draft-and-approve gates" rule). Each idea-candidate becomes an `IDEA-NNN.md` with `status: "candidate"`.
3. Report counts in the wrap-up: `Logged 3 idea candidates this session: IDEA-009, IDEA-010, IDEA-011`.
4. Include a **session ideas digest** — list of all ideas auto-logged this session (paths B and C combined) so the user can spot-check / archive in the viewer at their leisure.

The `status: "candidate"` value is the only marker that distinguishes deferred from sharp ideas in the data. The viewer can filter on it (chip rail will surface "candidate" as one of the freeform statuses automatically).

## Viewer screen

New `plugins/taskmaster/viewer/js/screens/ideas.js`. Symmetric with `screens/issues.js`.

- **Top chip rail:** status (freeform values discovered from data, deduped), tags (top-N), archived toggle (off by default).
- **Chip behavior:** `chipClickNext` helper per `L-001`. Plain click → filter to one. Shift-click → multi-select toggle.
- **List view:** `IDEA-NNN`, title, status pill (tinted background), tags, created-ago. Sort: newest first.
- **Detail view:** full body markdown render; frontmatter sidebar with click-through links to related tasks (kanban), related issues (issues screen), related lessons (lessons screen), and `promoted_to` (linked task).
- **"New idea" button:** opens a modal that posts to `backlog_idea_create`.
- **No colored left rails on cards** (per user's standing preference). Status uses tinted background pills; archived uses strikethrough + reduced opacity.
- **Top-nav:** new "Ideas" entry next to Issues / Lessons.

## File change list

```
plugins/taskmaster/
  taskmaster_v3.py                          # +ideas data layer (path helpers, validate, write/read/update, list, IDEAS.md regen)
                                            # + register 3 MCP tools (backlog_idea_create / _list / _update)
                                            # (end-session <idea-candidate> scan is prompt-driven in the skill; no python-side scan tool needed)
  skills/
    add-idea/                               # NEW
      SKILL.md
      templates/idea-body.md
    taskmaster/SKILL.md                     # +routing row for idea intents
    start-session/SKILL.md                  # +mid-session behavior section: lesson-emit + idea-emit heuristics
                                            #   (this is the lesson-candidate fix folded in)
    end-session/SKILL.md                    # +scan <idea-candidate>, commit-direct with status:"candidate", report counts
    lesson/references/marker-format.md      # +schema for <idea-candidate> alongside <lesson-candidate>
  viewer/
    js/screens/ideas.js                     # NEW — symmetric with issues.js
    js/screens/index.js                     # +register screen
    backlog-viewer.html                     # +nav entry
  tests/
    test_ideas.py                           # NEW — data layer + MCP tool tests
  viewer/tests/unit/
    ideas-screen.test.js                    # NEW — chip filters, list/detail toggle

.taskmaster/
  ideas/                                    # auto-created lazily on first idea
```

## Validation strategy

- **Data layer:** unit tests in `tests/test_ideas.py` — id allocation, frontmatter round-trip, IDEAS.md append/rewrite, archive/promote via `_update`, list filters.
- **Capture flow:** end-to-end test with a fake transcript containing `<idea-candidate>` tags → verify each becomes an `IDEA-NNN.md` with `status: "candidate"` after end-session runs.
- **Heuristic prompt:** manual eval — write 10 representative phrasings, dispatch Claude with the start-session prompt loaded, confirm path B vs C vs skip lands correctly. Iterate the heuristic wording inline.
- **Viewer:** unit test for chip-filter behavior using existing `chip-toggle.test.js` patterns.
- **Lesson-candidate fix:** before/after — start a fresh session, plant a heuristic-trigger phrase ("we got burned by X again"), verify Claude emits a `<lesson-candidate>` tag mid-session and that end-session commits it.

## Open questions for the implementation plan

- Exact wording of the start-session "mid-session behavior" section — needs to be compact enough not to bloat the always-loaded prompt, explicit enough to trigger reliably. Draft during plan-writing.
- Whether `backlog_idea_list(idea_id=...)` should error on miss or return `null` — match existing `_get` conventions in issues / lessons.
- Whether the IDEAS.md line for an archived idea uses strikethrough only, or strikethrough + an `_(archived)_` suffix. Cosmetic; resolve during implementation.
