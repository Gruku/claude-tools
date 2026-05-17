---
id: IDEA-014
title: .taskmaster/project.yaml — Project manifest (foundation for harvest proposals)
created: '2026-05-17T06:01:35Z'
created_by: user
status: promoted
tags:
- reflect:harvest
- plugin:taskmaster
- kind:foundation
- confidence:high
related_tasks: []
related_issues: []
related_lessons: []
promoted_to: project-manifest-001
archived: false
---
## What
Introduce `.taskmaster/project.yaml` — the Project manifest that captures everything *structural and conventional* about a Project: sub-repos with dependency order, submodules, protected branches per repo, tech stacks per layer, error-trace config (Langfuse URLs, log paths), deploy targets, owners, branch protocols.

Pairs with existing `backlog.yaml`:
- `backlog.yaml` = what's being done
- `project.yaml` = what the Project is

## Why
Came out of 2026-05-16 CodeMaestro harvest (Insight B). Three harvest proposals all need the same Project shape data:
- IDEA-004 (Multi-Repo-Ship-Choreographer) — needs repo set, dependency order, protected branches per repo
- IDEA-008 (Submodule-Pointer-Drift-Check) — needs submodule registry
- IDEA-006 (Diagnose-Auth-Or-Not) — needs error-trace config (Langfuse URL, log paths per layer) to generalize beyond CodeMaestro hard-coding

Without the manifest, each component reinvents detection and Diagnose-Auth stays CodeMaestro-specific.

## Forward compatibility
Agentic OS is the evolution of taskmaster where Projects become the top-level container. `project.yaml` becomes the Project definition the OS daemon reads — same shape, different consumer. Designing it now under taskmaster avoids a future re-cut.

## Naming rationale
- `project.yaml` not `project-map.yaml`/`repo-map.yaml` — the file *is* the Project definition, not a map of it. "Map" framing under-sells the non-structural config (error-trace, conventions).
- Lives inside `.taskmaster/` for now. Hoist to repo-root `PROJECT.yaml` only if a second non-taskmaster consumer appears.

## Dependency
**Prereq for IDEA-004, IDEA-006, IDEA-008.** Should be picked and promoted to a task before those three.

## Effort
M — schema design + loader/validator in `taskmaster_v3.py` + docs. Schema evolves incrementally; start with `repos:`, `submodules:`, `error_trace:` sections.

## Source
Harvest 2026-05-16 + design decision (see memory: project_taskmaster_project_yaml.md).
