---
title: feedback-inbox plugin design
date: 2026-05-21
status: draft
related:
  - plugins/reflect-auto-improve/    # retrospective companion
  - plugins/taskmaster/skills/add-idea/
  - plugins/taskmaster/skills/bug/
---

# feedback-inbox — design

## Problem

Claude instances working in *other* projects (CodeMaestro, ad-hoc repos, etc.) regularly trip over friction in the tools shipped from `claude-tools`: a taskmaster skill misbehaves, a guard-hook blocks the wrong command, an MCP tool returns an awkward shape, a skill description is confusing. That friction is invisible from inside `claude-tools` because by the time the user sits back down in this repo, the moment is gone.

`reflect-auto-improve` reads handovers and transcripts retrospectively, which is great for cross-cutting patterns but bad for fresh, specific complaints. We need a **live, write-anytime channel** that any Claude instance — or the user, via Claude — can use to drop a short note that eventually feeds back into the claude-tools backlog.

## Goals

- A foreign Claude instance can write a feedback message in one tool call, with zero per-machine setup beyond a one-time config file.
- The producer fires on both explicit user request (`/feedback ...`) and silent proactive detection of claude-tools friction.
- Messages land as one markdown file per message at a path the user controls (default: `claude-tools/inbox/`), gitignored, easy to skim.
- Triage routes accepted items into the existing taskmaster backlog as ideas or bugs. Nothing is deleted; processed messages move to `inbox/processed/<year>/` and become a harvestable corpus for `reflect-auto-improve`.
- A missing config or unreachable target must never crash the foreign session.

## Non-goals

- Cross-machine sync. The config file points at a local path; if the user wants the inbox in their Obsidian vault or a synced folder, they configure it that way.
- A web UI. Triage runs in the terminal via slash command + skill.
- Capturing feedback from non-Claude tooling. This is a Claude-to-Claude (and user-via-Claude) channel only.
- Auto-promotion of messages into taskmaster without user review. Every promotion runs through `taskmaster:add-idea` or `taskmaster:bug` with the user in the loop.

## Architecture overview

```
Foreign Claude in some project           claude-tools repo (this one)
─────────────────────────────────        ─────────────────────────────
  /feedback "X is broken"                 inbox/                  ← target
  or proactive: notices friction          ├── 2026-05-21-1430-….md
  with claude-tools component             ├── 2026-05-21-1612-….md
        │                                 └── processed/
        │ invoke feedback-inbox:feedback      └── 2026/
        │                                        └── 2026-05-19-….md
        ▼
  resolve_target.py
        │  reads ~/.claude/inbox-target.json
        ▼
  write_message.py                        /inbox
        │  writes YYYY-MM-DD-HHMM-slug.md feedback-inbox:triage
        │  with YAML frontmatter             ├ list pending by category
        │                                    ├ for each, choose:
        ▼                                    │    promote → taskmaster:add-idea
        done; caller resumes work            │    promote → taskmaster:bug
                                             │    archive → processed/<year>/
                                             │    drop    → processed/<year>/
```

## Plugin layout

```
plugins/feedback-inbox/
├── plugin.json
├── README.md
├── skills/
│   ├── feedback/SKILL.md           # producer
│   └── inbox-triage/SKILL.md       # reader
├── commands/
│   ├── feedback.md                 # /feedback shortcut → feedback skill
│   ├── inbox.md                    # /inbox shortcut    → inbox-triage skill
│   └── feedback-inbox-setup.md     # writes ~/.claude/inbox-target.json
└── scripts/
    ├── resolve_target.py           # reads config, validates inbox path exists
    ├── write_message.py            # creates the message file
    ├── list_pending.py             # lists inbox/*.md with category counts
    └── archive_message.py          # moves to processed/<year>/, updates frontmatter
```

## Components

### `skills/feedback/SKILL.md` — producer

Trigger surface (the `description` field):
- Explicit: "/feedback", "log this as inbox feedback", "send this to claude-tools", "report this back", "feedback to the toolmaker".
- Proactive (silent, no user confirmation): a claude-tools component just misbehaved or felt awkward — a taskmaster skill that errored, a guard-hook that blocked incorrectly, an MCP tool that returned a confusing shape, a skill whose description didn't match its behaviour, a slash command that did the wrong thing.

**Scope guard:** only friction with components shipped from `claude-tools` (taskmaster, reflect-auto-improve, guard-hooks, statusline, etc.). Generic project work or external-tool friction does NOT trigger this. The skill body restates this scope guard explicitly.

Behaviour:
1. Call `resolve_target.py`. If the config is missing or disabled, emit one line to the conversation (`feedback-inbox not configured on this machine — skipping`) and exit. Never raise.
2. Compose the message: pick a category (`bug | friction | idea | praise | question`), write a one-line summary, build the body, fill frontmatter (see below).
3. Call `write_message.py` with the payload. It writes `inbox/YYYY-MM-DD-HHMM-<slug>.md`, handling filename collisions by appending `-2`, `-3`, etc.
4. Emit one line back to the user/caller: `feedback-inbox: logged "<summary>" → <filename>`.

### `skills/inbox-triage/SKILL.md` — reader

Runs in the `claude-tools` repo (or wherever the inbox lives). Triggers: "/inbox", "triage the inbox", "process feedback".

Behaviour:
1. Call `list_pending.py` to enumerate `inbox/*.md` (top-level only, excluding `processed/`). Present a one-screen summary grouped by category.
2. Walk pending messages one-by-one. For each, show frontmatter + body and offer four actions:
   - **Promote to idea** → invokes `taskmaster:add-idea` with the message body prefilled, then archives the message with `status: promoted`, `promoted_to: IDEA-NNN`.
   - **Promote to bug** → invokes `taskmaster:bug` similarly, archives with `status: promoted`, `promoted_to: B-NNN`.
   - **Archive** → not actionable, but worth keeping; moves to `processed/<year>/`, sets `status: processed`.
   - **Drop** → noise; moves to `processed/<year>/`, sets `status: dropped`.
3. After the walk, emit a one-line summary: `inbox triage: N promoted, M archived, K dropped`.

If `taskmaster:add-idea` or `taskmaster:bug` isn't available (e.g. user invokes triage outside a taskmaster project), promote actions fall back to archive-only with a one-line note explaining the fallback.

### `commands/feedback.md` and `commands/inbox.md`

Thin slash-command wrappers that invoke the respective skills. `/feedback <text>` passes `<text>` as the message summary/body. `/inbox` invokes the triage skill with no args.

### `commands/feedback-inbox-setup.md`

One-shot setup. Prompts the user for the inbox path (default: `<claude-tools repo>/inbox` if detected, else `~/.claude/inbox`), writes `~/.claude/inbox-target.json`, creates the inbox directory.

## Message format

```yaml
---
id: msg-2026-05-21-1430-pick-task-worktree-hang
source: claude                # claude | user
category: friction            # bug | friction | idea | praise | question
project: CodeMaestro          # origin repo name (cwd basename, best-effort)
project_path: C:/Users/gruku/Files/Work/CodeMaestro
component: taskmaster/pick-task   # which claude-tools component the feedback is about
summary: pick-task hangs on worktree creation when target path > 200 chars
status: pending               # pending | processed | dropped | promoted
created: 2026-05-21T14:30:00+02:00
# added during triage:
# promoted_to: T-042              # taskmaster id when status=promoted
# processed_at: 2026-05-22T09:15:00+02:00
---

## What happened
…freeform markdown…

## Suggested fix
…
```

**Filename:** `YYYY-MM-DD-HHMM-<kebab-slug>.md`. The slug is derived from the summary, truncated to ~40 chars. Collisions get `-2`, `-3`, etc.

**ID:** `msg-` + the filename stem. Stable across moves to `processed/`.

### Field rules

- `source`: `claude` when the producer skill autonomously decided to log; `user` when the user explicitly dictated the message (`/feedback ...`, "log this as feedback").
- `category`: one of `bug | friction | idea | praise | question`. The producer skill picks; user can override by saying so explicitly.
- `project`: best-effort origin identifier. Default to `cwd` basename. The producer skill should not block if it can't determine this — leave the field empty.
- `component`: which claude-tools subsystem the feedback is about (`taskmaster/<skill>`, `reflect-auto-improve`, `guard-hooks`, etc.). Required when `source=claude`; optional when `source=user`.
- `summary`: single line, ≤ 120 chars. This is what shows up in `/inbox` listings.
- `status`: lifecycle field. Triage updates it.

## Lifecycle

| State | Location | `status` | Notes |
|---|---|---|---|
| Written | `inbox/<file>.md` | `pending` | Shows up in `/inbox` listings. |
| Promoted to idea/bug | `inbox/processed/<year>/<file>.md` | `promoted` | `promoted_to` set to the taskmaster id. |
| Reviewed, kept | `inbox/processed/<year>/<file>.md` | `processed` | Useful context but not actionable. |
| Dropped as noise | `inbox/processed/<year>/<file>.md` | `dropped` | Kept on disk for later `reflect-auto-improve:harvest` analysis. |

Nothing is deleted. The processed corpus is itself a research artifact.

## Config & failure handling

### Config file: `~/.claude/inbox-target.json`

```json
{
  "inbox": "C:/Users/gruku/Files/Claude/claude-tools/inbox",
  "enabled": true
}
```

- **Missing file** → producer no-ops with one-line message; triage prints a one-line error pointing at `/feedback-inbox-setup`.
- **`enabled: false`** → producer no-ops silently. Useful kill-switch when the user is doing sensitive work and doesn't want any cross-project leakage.
- **Path doesn't exist** → producer creates it (`mkdir -p`); triage creates `processed/<year>/` on demand.
- **Path unwritable** → producer logs the failure to stderr (visible to the foreign Claude as a tool error), does not raise. The foreign session continues. This is critical for the proactive path: a broken inbox must never break the host conversation.

### Producer failure modes

- Filename collision (same minute, same slug) → suffix `-2`, `-3`, …
- Frontmatter serialization error → write a fallback message body with the error inline, status=`pending`, category=`bug`. Better a noisy log than a lost one.
- Foreign Claude can't determine `project`/`project_path` → leave fields empty; do not block.

### Triage failure modes

- Empty inbox → "inbox is empty" one-liner; exit.
- Corrupt frontmatter on a single message → skip it with a note; continue with the rest.
- `taskmaster:add-idea` / `taskmaster:bug` unavailable → fall back to archive-only; explain the fallback.

## Git treatment

**When the inbox path is inside a git repo** (the default — `<claude-tools>/inbox/`), `inbox/` is **gitignored**. Rationale: messages can include paths, summaries, and details from arbitrary projects on this machine; committing them is rarely desired and can leak context. If a message contains a generally useful insight, the right path is to promote it via `taskmaster:add-idea`, which writes into the (committed) backlog.

`feedback-inbox-setup` is responsible for the gitignore. If the resolved inbox path sits inside a git working tree, it appends `inbox/` to that repo's `.gitignore` (idempotent — skip if already present). If the inbox is outside any repo (e.g. `~/.claude/inbox/`), no gitignore action is needed.

## Testing

- **Unit, `write_message.py`**: collision suffixing, slug truncation, frontmatter round-trip, mkdir on missing target.
- **Unit, `resolve_target.py`**: missing config, `enabled: false`, missing path (creates), unwritable path (graceful error).
- **Unit, `list_pending.py`**: empty inbox, mixed-category inbox, corrupt frontmatter on one file (skip + warn).
- **Unit, `archive_message.py`**: move to `processed/<year>/`, frontmatter update, idempotency if invoked twice.
- **Integration**: producer-from-foreign-cwd → triage-from-claude-tools-cwd round trip; verify the file lands at the expected path and the `project` field reflects the foreign cwd.
- **Manual smoke**: `/feedback-inbox-setup` first run; `/feedback "test"` writes a file; `/inbox` lists it; promote to idea writes a `taskmaster:add-idea` entry and moves the message.

## Out of scope (explicit non-decisions)

- **Per-project inboxes.** One global inbox; if needed later, add a `--inbox <path>` override to the producer.
- **De-duplication.** If Claude writes the same complaint twice, both messages land. Triage handles consolidation manually.
- **Notifications.** No "you have new feedback" surfacing in start-session for v1. Can be added later if the inbox gets neglected.
- **Editing messages post-write.** Treat messages as append-only writes. If wrong, drop in triage; if you want to re-log, write a fresh message.

## Open questions

None at design lock-in. All architectural forks were settled during brainstorming:
- Producer accepts both user and Claude sources, tagged in frontmatter.
- Path discovery via `~/.claude/inbox-target.json`.
- Per-message markdown files with YAML frontmatter.
- Distribution as a new plugin in claude-tools.
- Proactive fires silently without user confirmation (scope-guarded to claude-tools components).
- Triage via `/inbox` + skill + routing to taskmaster.
