---
id: 2026-05-03-taskmaster-handover-skill-shipped-backen
date: '2026-05-03'
tldr: taskmaster:handover skill shipped — backend, MCP, skill, retrofits, lint tests
  all in place.
next_action: Move to v3-skills-007 (start-session retrofit) so handovers surface on
  session start.
task_ids:
- v3-skills-002
session_kind: milestone-complete
branch: feature/taskmaster-v3
tip_commit: 7a503e6
---
## Resume prompt

> Continue v3-skills work from `feature/taskmaster-v3` (tip `7a503e6`). Pick `v3-skills-007` (start-session retrofit) to surface this handover on session start, OR `v3-skills-008` (pick-task retrofit). Both unblock once v3-skills-015 lands the read-MCP filter args. Tests must stay green: `pytest plugins/taskmaster/tests/ --timeout=30`. Don't push.

## Where execution stands

- Branch: `feature/taskmaster-v3`, tip `7a503e6`. Not pushed.
- 14 commits land v3-skills-002 (the handover skill itself), interleaved with the user's parallel v3-polish work.
- Tests: 312/312 pass in the full taskmaster suite, of which 27 are new (12 in `test_v3_handover.py`, 6 in `test_handover_skill_lint.py`, 9 in updated `test_v3_recap.py`).
- Working tree: 5 viewer files + `.claude/backlog.yaml` still uncommitted (user's v3-polish work, not touched by this session). `.taskmaster/handovers/` does not exist yet — this is the first handover written via the new skill.

## What shipped this session

| # | What | Where |
|---|------|-------|
| 1 | `HANDOVER_KINDS` aligned to spec 6-value set; viewer-kind mapping updated | `taskmaster_v3.py` (95203ba, 1cd6854) |
| 2 | `write_handover` validates `session_kind`; rejects unknown values | `taskmaster_v3.py` (238e826, 5a534f3) |
| 3 | `write_handover` accepts `supersedes`/`branch`/`tip_commit`; `apply_supersession()` helper edits old file in place; idempotent via regex-pinned callout detection; `_strip_supersession_callout()` decomposed | `taskmaster_v3.py` (7b834d5, ca59db9) |
| 4 | MCP `backlog_handover_create` accepts new args; new `backlog_handover_supersede` tool for chain repair | `backlog_server.py` (4e85ac1, 50bf0e1) |
| 5 | Skill scaffold + main 10-step flow + 4 reference docs + 3 body templates | `skills/handover/` (f4baeeb, 06a28b1, a77e590, ec96cd8) |
| 6 | Router retrofit: handover-write intent → `taskmaster:handover` skill | `skills/taskmaster/SKILL.md` (fd90942) |
| 7 | end-session retrofit: delegates handover write to skill; `crash-recovery` purged from auto-task and design doc | `skills/end-session/SKILL.md`, `skills/auto-task/SKILL.md`, `docs/design-v3-narrative-continuity.md` (1b4999f) |
| 8 | Lint tests for skill structure (frontmatter, trigger phrases, link resolution, no stubs) | `tests/test_handover_skill_lint.py` (7a503e6) |

## What's next

1. Pick `v3-skills-007` (start-session retrofit) — surface latest handover via `backlog_handover_latest` on session start; load body when `session_kind` is `milestone-complete`/`context-handoff`/`pivot`.
2. Pick `v3-skills-008` (pick-task retrofit) — show task-relevant handovers when picking a task; recognize "continue this task" trigger.
3. `v3-skills-015` (read MCP filtering) — extend `backlog_handover_list` with `task_id`/`session_kind`/`since` filter args; needed by 007/008 for clean queries.
4. After 007 ships, dogfood-2: open a fresh session and verify it surfaces this handover on start.

## Files of interest

| Group | Path | What | Why next session needs it |
|---|---|---|---|
| Touched | `plugins/taskmaster/taskmaster_v3.py` | `HANDOVER_KINDS`, session_kind validation, `apply_supersession`, `_strip_supersession_callout`, `_SUPERSESSION_CALLOUT_RE` | Core handover plumbing — read before extending for 007/008 |
| Touched | `plugins/taskmaster/backlog_server.py` | `backlog_handover_create` (new args), `backlog_handover_supersede` (new tool) | MCP surface — 007/015 will add list filter args here |
| Touched | `plugins/taskmaster/skills/handover/SKILL.md` | 10-step flow, edge cases, references | Authoritative skill flow — the contract 007/008 retrofits hook into |
| Touched | `plugins/taskmaster/skills/handover/references/` | session-kinds, tier-selection, auto-extraction, supersession | Detail Claude reads on demand during a handover write |
| Touched | `plugins/taskmaster/skills/handover/templates/` | light/standard/full body skeletons | Filled by Claude when drafting; sections deleted when empty |
| Touched | `plugins/taskmaster/tests/test_v3_handover.py` | 12 tests covering validation, supersession, MCP wiring | Add tests for any future write-side change here |
| Touched | `plugins/taskmaster/tests/test_handover_skill_lint.py` | 6 structural lint tests | Will fail loudly if 007/008 retrofit breaks the skill scaffold |
| Read | `docs/superpowers/specs/2026-05-02-handover-skill-design.md` | The spec; 16 sections | The contract this skill implements — read for any clarification |
| Read | `plugins/taskmaster/docs/v3-skills-enrichment.md` | Mining report from CodeMaestro v1 (457 tasks, 255 sessions) | Real-world patterns the spec was built from; useful for 007/008 design |
| Read | `.fixture-kanban/.taskmaster/handovers/2026-04-29-plan3-graph-variant-shipped.md` | Light-tier example | Reference shape for 007's resume-load behavior on light handovers |
| Relevant | `.claude/backlog.yaml` | `v3-skills` epic (15 tasks); has v3-skills-007, 008, 015 details | Pick from here for next task; user's parallel polish-task edits also live in this file |
| Relevant | `plugins/taskmaster/docs/design-v3-narrative-continuity.md` | Parent design doc §2 (handovers) | Five-pillar v3 design context |

## Important non-obvious things

1. **`.taskmaster/handovers/` did not exist before this handover write.** This file's creation made the directory. Tests use `tmp_path` fixtures; the live directory is created lazily on first write.
2. **`backlog_handover_create` MCP tool was unavailable in the session that built this skill.** Task 4 added new kwargs to the tool; the running MCP server hadn't reloaded so the deferred-tool list didn't expose any handover tools. The dogfood fell back to invoking `write_handover` + `sync_handover_index` directly via Python. Future sessions should have the full MCP surface available.
3. **`crash-recovery` is purged from skill code/docs but lives on as a tombstone in `test_v3_handover.py:32-33`** (asserts the value is absent — that's intentional).
4. **The supersession callout is detected by a regex pinned to the exact generated format** (`r"^> \*\*SUPERSEDED \d{4}-\d{2}-\d{2} by \["`). Loose prefix matching was rejected during code review because real handover bodies could legitimately start with `> **SUPERSEDED ...` for unrelated reasons.
5. **The plan included `v3-skills-015` (read MCP filter args) as a sibling task, not a blocker for 002.** The current `backlog_handover_list` already exists; 015 just adds `task_id`/`session_kind`/`since` filters that 007/008 will rely on.
6. **The user has parallel uncommitted polish-task work** (5 viewer files + `.claude/backlog.yaml`). Every implementer subagent in this session was instructed to stage only its own files. Do NOT use `git add .` or `git add -A` in 007/008 either.
