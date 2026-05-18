# Claude Tools — Project Instructions

This repo is the home of the **taskmaster** plugin (and supporting tooling). It's a Claude Code plugin distribution: skills, slash commands, MCP servers, agents, hooks, and a viewer UI live under `plugins/`.

## Working on the taskmaster plugin

Most work in this repo touches `plugins/taskmaster/`. When adding or modifying any plugin component, **invoke the matching `plugin-dev:` skill BEFORE writing code** — these skills encode the frontmatter rules, structural conventions, and trigger-phrasing that make components actually work in Claude Code:

| Component touched | Required skill |
|---|---|
| New / modified **agent** under `plugins/*/agents/` | `plugin-dev:agent-development` |
| New / modified **skill** under `plugins/*/skills/` | `plugin-dev:skill-development` |
| New / modified **slash command** under `plugins/*/commands/` | `plugin-dev:command-development` |
| New / modified **hook** | `plugin-dev:hook-development` |
| New plugin scaffold or `plugin.json` | `plugin-dev:plugin-structure` |
| **MCP integration** (the FastMCP server in `taskmaster_v3.py`) | `plugin-dev:mcp-integration` |
| Plugin-local config under `.claude/plugin-name.local.md` | `plugin-dev:plugin-settings` |

This is non-negotiable for agents and skills specifically — those have subtle frontmatter rules (e.g. `description` field is the trigger surface; getting it wrong means the component never fires) that the skill content addresses directly.

## Taskmaster architecture (quick orientation)

- **MCP server**: `plugins/taskmaster/taskmaster_v3.py` (FastMCP). Surface is the `backlog_*` family of tools. Read this before adding new tools.
- **Skills**: `plugins/taskmaster/skills/<name>/SKILL.md`. Universal entry points (`taskmaster:taskmaster`, `taskmaster:start-session`, `taskmaster:end-session`, `taskmaster:auto-task`, etc.). Skills are content-driven and progressive-disclosure — the `description` field is what Claude reads to decide whether to invoke.
- **Agents**: `plugins/taskmaster/agents/<name>.md`. Currently none ship; the `goal-judge` agent (designed in `docs/superpowers/specs/2026-05-10-auto-brainstorm-goal-design.md`, *pending*) will be the first.
- **Viewer**: `plugins/taskmaster/viewer/` — local-first kanban UI; `js/screens/<name>.js` per surface (kanban, issues, lessons, ideas, etc.). v3 is moving toward single-app + project switcher (see memory: `project_taskmaster_v3_single_app.md`).
- **On-disk backlog**: `.taskmaster/` per project — `backlog.yaml` (lightweight metadata), `tasks/<id>.md` (task body + spec/plan), `issues/`, `lessons/`, `ideas/`, `handovers/`, `auto/state.json`.

## Project manifest (`.taskmaster/project.yaml`)

Each project that uses taskmaster can declare its Project manifest at `.taskmaster/project.yaml` — the structured truth about repos, submodules, branch protocols, error-trace ladders, deploy targets, and conventions. Pairs with `backlog.yaml` (work in flight).

- **Schema, loader, helpers:** `plugins/taskmaster/project.py`
- **MCP surface:** `backlog_project_get`, `backlog_project_get_field`, `backlog_project_set`, `backlog_project_init`, `backlog_project_ship_order`, `backlog_project_error_trace_ladder`
- **Spec:** `docs/superpowers/specs/2026-05-17-taskmaster-project-yaml-design.md` (locally tracked; gitignored before push)
- **Forward-compatible** with the Agentic OS Projects-as-first-class direction; the same file becomes the Project definition the OS daemon reads.

When a downstream skill or hook needs to know about repos, branches, or observability layout, read the manifest — don't reinvent detection from `git remote` or hard-coded paths.

## Design philosophy

**Harness engineering is opinionated.** When designing or modifying taskmaster features, bake strong opinions into defaults rather than offering toggles. The design dialogue with the user is where the opinion gets forged — fight for the right default, don't punt to a config flag. (See user-level memory `feedback_taskmaster_opinionated_design.md` for the full rule.)

## Specs and design docs

Living design specs live under `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`. Implementation plans live under `docs/superpowers/plans/`. Both directories are gitignored but tracked locally — see memory `project_superpowers_local_tracking.md` for the archive-before-push rule.

## Conventions

- **No colored left rails on cards** anywhere in the viewer (user preference, hard rule). Tinted backgrounds, full borders, or top borders only.
- **No motion on hover** — color/border/background changes only, no `transform` / `translate` / `scale`.
- **No box-shadows for elevation** — use surface stepping.
- **TDD is the default in `auto-task`** — write failing tests as their own commit before implementing. Skipping requires explicit rationale recorded in the handover.

## Reflect Targets

`plugins/reflect-auto-improve` reflects on past work across projects. Primary external target:

- **CodeMaestro** at `C:\Users\gruku\Files\Work\CodeMaestro` — main Taskmaster consumer; default subject of `reflect-auto-improve:retro`. Use this as the canonical "real project" for retros.
- Full target list lives at `plugins/reflect-auto-improve/TARGETS.md`.
