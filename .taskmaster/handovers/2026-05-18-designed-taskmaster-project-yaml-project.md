---
id: 2026-05-18-designed-taskmaster-project-yaml-project
date: '2026-05-18'
created: '2026-05-17T23:55:05.991008+00:00'
tldr: Designed .taskmaster/project.yaml (Project manifest) — full schema + 9-task
  TDD implementation plan ready; foundation for harvest consumers IDEA-004/006/008;
  awaiting user review of spec+plan, then execution choice on project-manifest-001.
next_action: 'User reviews docs/superpowers/specs/2026-05-17-taskmaster-project-yaml-design.md
  and plan 2026-05-17-taskmaster-project-yaml.md. Then choose execution mode for project-manifest-001
  — recommended: subagent-driven (fresh subagent per task, 2-stage review).'
task_ids:
- project-manifest-001
session_kind: end-of-day
status: todo
status_changed: '2026-05-17T23:55:05.991008+00:00'
status_user_set: false
branch: master
tip_commit: e21576f
---
## Decisions

**Naming: `.taskmaster/project.yaml`** (not `project-map.yaml`). The file *is* the Project definition, not a map of it; "map" framing under-sells the non-structural config (error-trace, conventions). Lives inside `.taskmaster/` for now — hoist to repo-root `PROJECT.yaml` only if a second non-taskmaster consumer appears. Memory: `project_taskmaster_project_yaml.md`.

**Scope: Full Agentic OS shape** (user pick). Includes identity, structure, operations, knowledge, conventions — not just structural facts. Forward-compatible with the Agentic OS Projects-as-first-class direction; same file gets read by the future OS daemon.

**Boundary with CLAUDE.md: project.yaml = structured truth; CLAUDE.md = always-on narrative.** CLAUDE.md is essential (only file Claude reads every session). project.yaml holds *programmatic* facts that tooling reads. They reference each other; project.yaml is the source of truth when they overlap.

**Repo model: two top-level lists** — `repos:` (sibling peers) + `submodules:` (with `parent_repo` anchor). Cleaner than hierarchical tree (CodeMaestro has no natural root) or single flat list with `kind:` (loses behavioral distinction). `depends_on` IS the ship order — no separate `order:` field; Multi-Repo-Choreographer topo-sorts.

**Validator approach: dataclasses + hand validation, NO Pydantic.** Taskmaster currently uses PyYAML + dict access, zero Pydantic. Introducing it for one module is excessive. Matches existing convention; zero new dependencies.

**YAML loader: PyYAML with `sort_keys=False`.** Comments are NOT preserved on programmatic writes; the `extensions: {}` dict round-trips faithfully. Documented limitation in spec — sufficient for v1.

**Path resolution: no `~` expansion.** Relative paths resolve against project root (directory containing `.taskmaster/`); absolute paths pass through. Deterministic.

**Opinionated defaults baked in:**
- `push_policy: always-ask` (matches CLAUDE.md hard rule)
- `pointer_policy: separate-chore-commit` (drives Submodule-Drift-Check)
- `conventions.policies.spec_to_task_ratio_warn: 3` (Spec-Plan-Backlog-Guard threshold — confirmed earlier in session)
- `meta.kind` is a closed 5-value enum (`app | library | research | platform | tool`) for cross-project queryability

## Blockers

None. Spec + plan complete. Awaiting user review.

## Where I'd start

1. **User reads `docs/superpowers/specs/2026-05-17-taskmaster-project-yaml-design.md`** — flag any schema changes; revise spec.
2. **User reads `docs/superpowers/plans/2026-05-17-taskmaster-project-yaml.md`** — 9 tasks, fully TDD, ~50 commits. Self-review noted one gap: `taskmaster:init-taskmaster` skill edit to prompt scaffolding was deferred to a separate follow-up task in the same epic.
3. **Pick execution mode for `project-manifest-001`:**
   - **Subagent-driven (recommended)** — fresh subagent per task, 2-stage review. Best for a 9-task foundation touching `taskmaster_v3.py` (heavily-used). Keeps main context lean.
   - **Inline** — execute in next session via `superpowers:executing-plans`. Faster but pollutes context.
   - **Auto-mode** — `/auto project-manifest-001` runs the full lifecycle (pick → spec-review → implement → review-gate → handover → end-session).
4. **After foundation lands**, file follow-up tasks under `project-manifest` epic for the three harvest consumers that read the manifest:
   - IDEA-006 Diagnose-Auth-Or-Not (small, high recurrence — 4 reinforcements of L-003 in 7 days)
   - IDEA-004 Multi-Repo-Ship-Choreographer (medium, biggest CodeMaestro impact)
   - IDEA-008 Submodule-Pointer-Drift-Check (small, narrow hook)

## Open threads

- **`init-taskmaster` scaffold prompt** — gap noted in plan self-review. Spec says it should be added; plan defers to a separate task. Worth filing as `project-manifest-002` after foundation lands.
- **CodeMaestro `project.yaml` authoring (plan Task 8)** — requires the foundation to be installed in CodeMaestro's taskmaster install first. Plan covers this but ordering matters: bump plugin version → reinstall in CodeMaestro → author manifest.
- **Other 5 harvest ideas not directly unblocked by project.yaml** — IDEA-005 (rebased-duplicates-merge-guard), IDEA-007 (spec-plan-backlog-guard hook), IDEA-009 (worktree-cwd-guard). These can be filed as tasks in parallel or after, independent of `project-manifest` epic.

## Artifacts created this session

- **Spec** (gitignored, locally tracked): `docs/superpowers/specs/2026-05-17-taskmaster-project-yaml-design.md`
- **Plan** (gitignored, locally tracked): `docs/superpowers/plans/2026-05-17-taskmaster-project-yaml.md`
- **Idea → promoted to task:** `IDEA-014` (`.taskmaster/ideas/IDEA-014.md`) → `project-manifest-001` (`.taskmaster/tasks/project-manifest-001.md`)
- **Epic:** `project-manifest` (active, in phase `post-v2-architecture`)
- **Memory:** `project_taskmaster_project_yaml.md` (with MEMORY.md index entry)

## Files of interest

- `plugins/taskmaster/project.py` — to be created (Task 1+)
- `plugins/taskmaster/tests/test_project_*.py` — to be created (Tasks 1–7)
- `plugins/taskmaster/taskmaster_v3.py` — to receive 6 new `backlog_project_*` MCP tools (Tasks 6–7)
- `CLAUDE.md` — to gain a "Project manifest" section (Task 9)
