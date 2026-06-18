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

## Plugin versioning protocol

A plugin only registers as a new version downstream when **all relevant parts move together**. Bumping one and forgetting the others means the marketplace silently serves a stale or mismatched version. For every PR that changes a plugin's source, bump that plugin's version in all of these:

| # | Where | What |
|---|---|---|
| 1 | `plugins/<name>/.claude-plugin/plugin.json` | `"version"` |
| 2 | `.claude-plugin/marketplace.json` | the plugin's `version` entry (must equal #1) |
| 3 | `plugins/<name>/CHANGELOG.md` *(if the plugin ships one — taskmaster does)* | a new `## <version>` section describing the delta |

**SemVer rules** (the CHANGELOG header says it too): bug-fix-only delta → patch; any additive surface (new MCP tool, new field, new skill) → minor; schema break or removed surface → major. When a PR bundles bugfixes *and* features, the feature wins — bump minor.

**Enforcement (three layers, no CI in this repo):**
- **Pre-PR check** — run `python scripts/check_plugin_version_bump.py --base origin/master` before opening a PR. It verifies parts #1/#2 are in sync and that any plugin whose source changed since `<base>` was bumped and has a matching CHANGELOG entry. Exit 1 = fix before pushing.
- **Push-time guard hook** — `.claude/hooks/check-version-bump.sh` (wired in `.claude/settings.json`) fires on `git push` and blocks if a changed plugin wasn't bumped or its plugin.json/marketplace.json versions disagree. Override only via the AskUserQuestion Approve/Deny ritual.
- **This convention** — the durable record of why the three parts exist.

When creating a PR that touched plugin source, treat "bump the three parts + run the check script" as a required step, not an afterthought.

## Taskmaster architecture (quick orientation)

- **MCP server**: `plugins/taskmaster/taskmaster_v3.py` (FastMCP). Surface is the `backlog_*` family of tools. Read this before adding new tools.
- **Skills**: `plugins/taskmaster/skills/<name>/SKILL.md`. Universal entry points (`taskmaster:taskmaster`, `taskmaster:start-session`, `taskmaster:end-session`, `taskmaster:auto-task`, etc.). Skills are content-driven and progressive-disclosure — the `description` field is what Claude reads to decide whether to invoke.
- **Agents**: `plugins/taskmaster/agents/<name>.md`. Currently none ship; the `goal-judge` agent (designed in `docs/superpowers/specs/2026-05-10-auto-brainstorm-goal-design.md`, *pending*) will be the first — note: that design is superseded pending a goals+ultracode redesign (auto-mode removed).
- **Viewer**: `plugins/taskmaster/viewer/` — local-first kanban UI; `js/screens/<name>.js` per surface (kanban, issues, lessons, ideas, etc.). v3 is moving toward single-app + project switcher (see memory: `project_taskmaster_v3_single_app.md`).
- **On-disk backlog**: `.taskmaster/` per project — `backlog.yaml` (lightweight metadata), `tasks/<id>.md` (task body + spec/plan), `issues/`, `lessons/`, `ideas/`, `handovers/`, `auto/state.json`.

## Project manifest (`.taskmaster/project.yaml`)

Each project that uses taskmaster can declare its Project manifest at `.taskmaster/project.yaml` — the structured truth about repos, submodules, branch protocols, error-trace ladders, deploy targets, and conventions. Pairs with `backlog.yaml` (work in flight).

- **Schema, loader, helpers:** `plugins/taskmaster/project.py`
- **MCP surface:** `backlog_project_get`, `backlog_project_get_field`, `backlog_project_set`, `backlog_project_init`, `backlog_project_ship_order`, `backlog_project_error_trace_ladder`
- **Spec:** `docs/superpowers/specs/2026-05-17-taskmaster-project-yaml-design.md` (locally tracked; gitignored before push)
- **Forward-compatible** with the Agentic OS Projects-as-first-class direction; the same file becomes the Project definition the OS daemon reads.

When a downstream skill or hook needs to know about repos, branches, or observability layout, read the manifest — don't reinvent detection from `git remote` or hard-coded paths.

## UI testing & debugging (viewer and any web-rendered surface)

**Playbook:** `docs/playbooks/agent-driven-ui-testing.md` — the two-harness model. **Read it before writing or debugging any UI test infrastructure**, and use it inside workflows/subagents that build or verify viewer UI:

- **Harness 1 (deterministic E2E)** — `@playwright/test` specs are the regression gate. The viewer suite lives at `plugins/taskmaster/viewer/tests/` (`*.spec.js` e2e + `tests/unit/*.test.js` via `node --test`). Every new viewer surface ships with spec coverage.
- **Harness 2 (agent-driven exploratory)** — use `@playwright/cli` (`playwright-cli -s=qa open http://localhost:<port>`) to click through in-progress UI as a human-tester surrogate: `snapshot --boxes` → act → observe (`console`, `requests`, screenshots) → judge against the viewer's design rules → file findings as bugs/ideas in the backlog, **never silent fixes**. A clean run means "no friction found on driven paths," not "verified."
- **Claude-tools reading of the adaptation matrix (§5):** the viewer is a local dashboard — no auth seeding, no bridge shim, no paid/destructive guards needed; CLI launches directly (no CDP attach). Most Electron-weight sections drop away.
- Hard rules index (§6) applies verbatim — notably: verify selectors against the real rendered DOM, keep unit-runner globs away from `.spec.js` files, never `npm install` inside a worktree.

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
