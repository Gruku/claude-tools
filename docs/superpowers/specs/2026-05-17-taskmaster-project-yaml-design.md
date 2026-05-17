---
title: .taskmaster/project.yaml — Project Manifest
date: 2026-05-17
status: draft
related_idea: IDEA-014
related_harvest: .taskmaster/harvests/2026-05-16-harvest-codemaestro-plugin-infra.md
unblocks: [IDEA-004, IDEA-006, IDEA-007, IDEA-008]
schema_version: 1
---

# `.taskmaster/project.yaml` — Project Manifest

## Background

The 2026-05-16 CodeMaestro harvest (Insight B) surfaced that taskmaster currently treats every project as a flat workspace. CodeMaestro's reality is the opposite: three sibling repos (`code-maestro-api`, `code-maestro-facade`, `code-maestro-app-desktop`) plus an `mcp-host` submodule inside `app-desktop`, each with its own protected branches, push protocols, tech stack, and observability layer.

Three harvest proposals all need the same structural data to operate:

- **IDEA-004** Multi-Repo-Ship-Choreographer — repo set, dependency order, protected branches per repo
- **IDEA-008** Submodule-Pointer-Drift-Check — submodule registry, parent repo, pointer policy
- **IDEA-006** Diagnose-Auth-Or-Not — error-trace ladder generalized beyond CodeMaestro hard-coding

Without a manifest, each component reinvents detection from `git remote`, file globs, and embedded conventions. The manifest gives them — and any future Agentic OS daemon — a single canonical source.

## Goals

1. **Capture structural and operational facts about a Project** in a machine-readable, version-controlled file.
2. **Pair with `backlog.yaml`** under `.taskmaster/`: `backlog.yaml` is *what's being done*, `project.yaml` is *what the Project is*.
3. **Forward-compatible with Agentic OS** — the same file becomes the Project definition the OS daemon reads.
4. **Reference, not replace, CLAUDE.md** — CLAUDE.md remains the always-on narrative for the agent; project.yaml is the structured truth that CLAUDE.md and tooling can reference.
5. **Mostly optional** — projects with one repo and no integrations write 5 lines. CodeMaestro writes 60.

## Non-Goals (v1)

- No viewer UI for project.yaml — authored in editor.
- No auto-migration from CLAUDE.md scraping — too unreliable; manual authoring.
- No multi-user/role support — `owners:` accepts a list, but only single-user is wired.
- No deploy execution — `deploy:` is declarative only.
- No cross-project queries (e.g., "list all my apps") — that ships with Agentic OS.

## Architecture

### Boundary with CLAUDE.md

**project.yaml = canonical structured truth that tooling reads programmatically.**
**CLAUDE.md = always-on narrative for the agent.**

When both can describe the same fact (e.g., branch protocols), project.yaml is the source of truth. CLAUDE.md prose can reference manifest fields (`see project.yaml#repos[*].branches`) but does not duplicate them.

Rationale: CLAUDE.md is the only file Claude reads every session. Removing it would break agent context. project.yaml lets *tooling* (hooks, skills, future daemons) operate on structured facts without scraping prose.

### Top-level shape

```yaml
schema_version: 1                       # required, integer
meta: { ... }                           # system-managed metadata
project: { ... }                        # user-authored identity
repos: [ ... ]                          # zero-or-more sibling repos
submodules: [ ... ]                     # zero-or-more registered submodules
integrations: { ... }                   # external systems (observability, third-party APIs)
deploy: [ ... ]                         # deploy targets
knowledge: { ... }                      # docs, dashboards, links
conventions: { ... }                    # CLAUDE.md reference + structured policies
extensions: {}                          # forward-compat escape hatch
```

Every section except `schema_version` and `meta.name` / `meta.slug` is optional. Missing sections are treated as empty.

## Schema (v1)

### `meta:` — system-managed

```yaml
meta:
  name: codemaestro                     # required, human-readable
  slug: codemaestro                     # required, used for cross-project references
  kind: app                             # app | library | research | platform | tool
  updated: 2026-05-17                   # ISO date; auto-managed by taskmaster on writes
```

`kind:` is a closed enum to keep cross-project queries tractable in the future Agentic OS daemon.

### `project:` — user-authored identity

```yaml
project:
  description: "AI-assisted code editor with multi-agent dispatch"
  goal: "Ship an opinionated agent-native IDE"
  owners: [gruku]
  tags: [ai, agent-platform]
```

- `goal:` is the hook for Codex `/goal` integration (memory: `reference_codex_goal_clipping.md`). Freeform string in v1; may grow structured later.
- `owners:` accepts a list for future multi-user support; v1 wires single-user only.
- All fields optional.

### `repos:` — sibling repos

```yaml
repos:
  - name: api                           # required; used in cross-references (depends_on, deploy)
    path: ./code-maestro-api            # required; relative to project root or absolute
    description: "Backend API"
    stack: [python, fastapi, postgres]  # freeform tags
    depends_on: []                      # repo names; topological order = ship order
    branches:
      default: develop
      protected: [develop, master]
      naming: feature/                  # optional convention prefix
    push_policy: always-ask             # always-ask (default) | gated | open
```

**Design choices:**
- `depends_on` *is* the ship order. Multi-Repo-Choreographer topo-sorts on this field; no separate `order:` needed.
- `push_policy: always-ask` is opinionated default (CLAUDE.md hard rule: never push without explicit user approval).
- No `remotes:` field — `git remote -v` is the authoritative source; no point duplicating.

### `submodules:` — git submodules

```yaml
submodules:
  - name: mcp-host
    parent_repo: app-desktop            # required; must match a repos[].name
    path: mcp-host                      # relative to parent_repo's path
    description: "MCP host runtime"
    stack: [typescript, node]
    pointer_policy: separate-chore-commit  # opinion: pointer bumps always get their own chore commit
    upstream: github.com/...            # optional; context only
```

**`pointer_policy: separate-chore-commit`** is the opinionated default. Submodule-Drift-Check hook (IDEA-008) reads this to decide whether to block mixed commits.

### `integrations:` — external systems

```yaml
integrations:
  observability:
    error_trace_ladder:                 # ordered: closest to user → closest to root cause
      - layer: ui
        kind: devtools-network          # devtools-network | console | http-log | trace
        description: "Browser network tab"
      - layer: facade
        kind: http-log
        path: ./code-maestro-facade/logs/api.log
      - layer: mcp-host
        kind: trace
        path: ./code-maestro-app-desktop/mcp-host/logs
      - layer: backend
        kind: trace
        provider: langfuse
        url: https://cloud.langfuse.com/project/cm-prod
  external:                             # third-party services this project depends on
    - name: openai
      kind: api
      docs: https://platform.openai.com/...
    - name: stripe
      kind: api
```

**The `error_trace_ladder` is an ordered list, not a map.** Order is meaningful: it's the diagnostic ladder Diagnose-Auth-Or-Not (IDEA-006) walks top-to-bottom. CodeMaestro's L-003 lesson hard-codes its walk; this schema generalizes it.

### `deploy:` — deploy targets

```yaml
deploy:
  - target: staging
    repos: [api, facade, app-desktop]
    branch: develop
  - target: production
    repos: [api, facade, app-desktop]
    branch: master
```

Declarative only in v1. No skill runs deploys from this; consumers (hooks, future daemons) read it to understand what branches are deploy-relevant.

### `knowledge:` — resources

```yaml
knowledge:
  docs:
    - title: Architecture overview
      path: ./docs/architecture.md
  dashboards:
    - title: Langfuse production
      url: https://cloud.langfuse.com/...
  links:
    - title: Design vault
      url: obsidian://...
```

`dashboards` is the single home for monitoring/observability URLs. (Earlier draft had a duplicate under `integrations.observability`; cut to avoid drift.)

### `conventions:` — narrative reference + structured policies

```yaml
conventions:
  narrative_ref: ./CLAUDE.md            # human-readable conventions live here
  policies:                             # structured policies that tooling reads
    tdd: required                       # required | preferred | optional
    commit_style: conventional          # conventional | freeform
    spec_to_task_ratio_warn: 3          # Spec-Plan-Backlog-Guard threshold (IDEA-007)
```

- `narrative_ref:` makes the structured-facts-vs-narrative split explicit *in the file itself*.
- `policies:` holds structured knobs tooling reads. `spec_to_task_ratio_warn: 3` is the opinionated default for IDEA-007, overridable per-project.

### `extensions:` — forward-compat

```yaml
extensions: {}                          # any keys; preserved on round-trip; never validated
```

Sanctioned escape hatch for project-specific keys without schema changes. Loader passes through opaque; writers preserve.

## Loader and validation

### Module

New module (or section in `taskmaster_v3.py`): `project.py`, exposing:

```python
class ProjectManifest:
    @classmethod
    def load(cls, project_root: Path) -> "ProjectManifest | None":
        """Returns None if .taskmaster/project.yaml doesn't exist. Never raises on missing file."""

    @classmethod
    def load_or_default(cls, project_root: Path) -> "ProjectManifest":
        """Returns empty-but-valid manifest if file missing. For consumers that need a manifest unconditionally."""

    @property
    def repos(self) -> list[Repo]: ...
    @property
    def submodules(self) -> list[Submodule]: ...
    def repo(self, name: str) -> Repo | None: ...
    def submodule(self, name: str) -> Submodule | None: ...
    def ship_order(self) -> list[str]: ...
    def protected_branches(self, repo_name: str) -> list[str]: ...
    def error_trace_ladder(self) -> list[ErrorTraceEntry]: ...
    def policy(self, key: str, default=None): ...
```

### Validation strategy

- **Pydantic models** for every section. Reuses existing taskmaster Pydantic convention.
- **Soft validation on read** — malformed file logs a warning, returns `None` from `load()`. Never crashes taskmaster.
- **Strict validation on write** — `backlog_project_set()` refuses to persist malformed YAML.
- **`schema_version` mismatch** — unknown major version logs a warning; `set()` refuses to downgrade.
- **`extensions:` keys** — preserved on round-trip but never validated; opaque pass-through.

### Helper guarantees

- `ship_order()` performs a topological sort on `repos[].depends_on`. Cycles raise a validation error (no fallback).
- `submodules[].parent_repo` is validated against `repos[].name` on load — orphan submodules log a warning, are dropped from results.

## MCP surface (v1 additions)

Six new tools, prefix `backlog_project_*`:

| Tool | Purpose |
|---|---|
| `backlog_project_get()` | Read full manifest as dict (or null if missing). |
| `backlog_project_get_field(path)` | Dotted accessor: `"repos[0].branches.protected"`. |
| `backlog_project_set(yaml_content)` | Write with strict validation. |
| `backlog_project_init()` | Scaffold an empty manifest interactively (used by `taskmaster:init-taskmaster`). |
| `backlog_project_ship_order()` | Topo-sorted repo names — direct consumer of IDEA-004. |
| `backlog_project_error_trace_ladder()` | Returns ladder list — direct consumer of IDEA-006. |

All read-mostly. `set()` is the only mutator and validates strictly.

## Adoption sequence

1. **Spec + loader + Pydantic models** — no consumers wired yet, just the foundation. Land in `taskmaster_v3.py` (or split into `project.py`).
2. **Six MCP tools.** Now Claude can read/write the manifest from any session.
3. **`backlog_project_init` scaffold** — `taskmaster:init-taskmaster` adds a "scaffold project.yaml?" prompt for new projects; existing projects get a separate entry point (slash command or `taskmaster:init-project-manifest` skill).
4. **Wire harvest consumers** in dependency order:
   - IDEA-006 Diagnose-Auth-Or-Not reads `error_trace_ladder`.
   - IDEA-004 Multi-Repo-Choreographer reads `repos`, `submodules`, `ship_order()`.
   - IDEA-008 Submodule-Drift-Check reads `submodules`.
   - IDEA-007 Spec-Plan-Backlog-Guard reads `conventions.policies.spec_to_task_ratio_warn`.
5. **CodeMaestro is the first real population.** Author its `project.yaml` as the canonical example; commit alongside the harvest's downstream work.
6. **Memory + CLAUDE.md updates.** claude-tools' CLAUDE.md references the manifest; project memory `project_taskmaster_project_yaml.md` updated to reflect implementation status.

## Open questions for implementation

- **Pydantic v1 vs v2** — taskmaster_v3.py uses Pydantic v2; project.py should match. Confirm at plan time.
- **`path:` resolution semantics** — relative paths resolve against project root (the directory containing `.taskmaster/`). Absolute paths pass through. Decide if `~` expansion is in or out (lean: out, keep deterministic).
- **`extensions:` round-trip fidelity** — depends on YAML loader preserving key order and comments. PyYAML doesn't; ruamel.yaml does. Confirm taskmaster's current YAML strategy before committing.

## References

- Idea: `IDEA-014`
- Harvest: `.taskmaster/harvests/2026-05-16-harvest-codemaestro-plugin-infra.md` (Insight B)
- Memory: `project_taskmaster_project_yaml.md`
- Related memories: `project_taskmaster_v3_single_app.md`, `project_taskmaster_progressive_disclosure.md`, `reference_codex_goal_clipping.md`
