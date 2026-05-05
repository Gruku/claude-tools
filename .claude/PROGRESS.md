# claude-tools Progress

> Auto-generated from backlog.yaml — do not edit manually

## Dashboard

| Workstream | Status | Progress | Current Focus |
|-----------|--------|----------|---------------|
| V3 Polish | Active | 19/35 | Kanban columns scroll-reset to top + scrollbar flicker every 3s |
| V3 Release (2.0) | Planned | 2/7 | Write 2.0.0 release notes |
| V3 Skills | Active | 9/16 | taskmaster:handover skill — write/read flow |
| V3 Agent Teams (Optional) | Planned | 0/5 | — |
| V3 Edit-in-UI | Active | 15/16 | — |

**Active Phase:** Ship V3 (45/78 done)
**Phases:** >> Ship V3

**In Progress:** v3-polish-027 Kanban columns scroll-reset to top + scrollbar flicker every 3s, v3-polish-028 Auto-mode strip shows "Auto-mode · N running" for stopped/abandoned sessions, v3-release-003 Write 2.0.0 release notes, v3-skills-002 taskmaster:handover skill — write/read flow, v3-skills-003 taskmaster:lesson skill — write/reinforce/promote, v3-skills-004 taskmaster:issue skill — log/track/close defects, v3-skills-005 taskmaster:migrate-v3 skill — guided opt-in migration
**Blocked:** —
**Next Up:** v3-polish-001 Build recap picker (was: D·5 rebuild — there is no picker) (high), v3-polish-009 Issues screen — align with design concept (concept deltas + 3 real bugs) (high), v3-polish-010 Lessons screen — usability refresh (concept deltas validated) (high)

---

## Changelog

### 2026-05-04 — v3-skills-003 lesson skill — implementation + final review
**Done:**
- Shipped full taskmaster:lesson skill in 14 commits (1465 insertions across 14 files, 349/349 tests pass with 29 new).
- Backend (taskmaster_v3.py): lesson_candidates defer/read/clear with markdown+YAML store, scan_transcripts_for_candidates regex+filters with real Claude Code JSONL message.content shape support, apply_handover_review_flag helper for session-scope candidates.
- MCP boundary (backlog_server.py): 4 new lesson-candidate tools + backlog_handover_create retrofit accepting flag_for_review/review_reason kwargs.
- Skill files: full skills/lesson/ tree — SKILL.md (5 entry points), 5 references (marker-format, auto-extraction, reinforce-flows, promotion-decay, session-retro), 1 lesson-body template.
- Retrofits: end-session/SKILL.md gained v3-pre-2a lesson sweep step + handover wiring; taskmaster/SKILL.md router routes lesson-write intents to the new skill.
- Final review pass caught and fixed 3 Important + 1 Minor doc seams in cab50cd: session-retro.md unrealizable "stamp existing handover" flow; handover/SKILL.md silent on forwarding new kwargs; SKILL.md step 4 missing task_kinds bullet; marker-format.md didn't mention attrless tags.</done>
- <parameter name="decisions">Transitioned to in-review (not done) because task 12 (dogfood walkthrough) cannot be completed from the current session — the running Claude Code instance loads the installed v1.11.1 plugin cache, not this worktree, so the new skill isn't loadable here.
- Filed v3-skills-016 to track the dogfood step rather than blocking this task indefinitely on it; v3-skills-016 depends on v3-skills-003 and only requires syncing the plugin install (or publishing v3) before it can run.
- Final-review fixes were collapsed into a single doc commit (cab50cd) rather than scattered per-finding commits, since they're all skill-doc clarifications with no behavior change.</decisions>
- <parameter name="issues">Dogfood blocker: new skill is not loadable from this session — see v3-skills-016 for the unblock path.
- Side-effect: untracked .taskmaster/ and plugins/taskmaster/.taskmaster/ directories appeared in the worktree (likely test-fixture artifacts from the lesson-candidate tests); need to verify whether these should be gitignored or cleaned up before the next commit.</issues>
- <parameter name="tasks_touched">v3-skills-003,v3-skills-016

**Decisions:**
- None

**Issues:**
- None

**Tasks touched:** N/A

---


### 2026-05-03 — v3-skills-001 close-out — enrichment mining transitioned
**Done:**
- High-level review of plugins/taskmaster/docs/v3-skills-enrichment.md confirmed it is load-bearing and complete. All 5 spec outputs covered (PROGRESS.md conventions, handover-language patterns A/B/C, 8 lesson-candidate clusters with kind classification, 3 hidden-bug examples with severity, end-session reality vs design, auto-loop stress signals at 457-task scale, plus actionable skill-authoring deltas). Doc was authored and committed in 8098893 ("feat(v3): add v3-skills + v3-teams epics + CodeMaestro enrichment mining") but task status was never transitioned. This session is a tracking close-out — no new code, just status accuracy.

**Decisions:**
- Accepted enrichment doc as-is — sufficient input for v3-skills-003 (lesson skill), v3-skills-004 (issue skill), v3-skills-005 (migrate skill). No additional mining needed.
- Picked task and immediately closed under the same session because work pre-existed; this is a status-reconciliation, not a fresh implementation.
- Recorded branch=feature/taskmaster-v3 and worktree=.worktrees/taskmaster-v3 since the v3-skills epic shares one worktree (no per-task worktree per handoff convention).

**Issues:**
- Minor: §2 Pattern A in v3-skills-enrichment.md has corrupted backslash-escape rendering ("\next_steps" / "\test_plan" lost a couple of field names). Cosmetic, fix opportunistically when authoring v3-skills-003.
- Side viewer at :8765 surfaced two new bugs filed during this session — v3-polish-027 (kanban scroll-reset every 3s) and v3-polish-028 (auto-mode strip shows "running" on stopped sessions). Unrelated to this task but worth noting.

**Tasks touched:** v3-skills-001,v3-polish-027,v3-polish-028

---

