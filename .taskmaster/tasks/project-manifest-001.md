---
notes: 'Foundation work: Pydantic models for every section, ProjectManifest loader
  (soft on read, strict on write), 6 backlog_project_* MCP tools (get / get_field
  / set / init / ship_order / error_trace_ladder), helper API (ship_order topo-sort,
  protected_branches, policy lookup, orphan submodule detection). Author CodeMaestro''s
  project.yaml as canonical example. Update claude-tools CLAUDE.md to reference manifest.
  Update memory project_taskmaster_project_yaml.md to reflect implementation status.
  Three open questions to resolve at plan time: Pydantic v1 vs v2 (taskmaster uses
  v2), path resolution semantics (lean: no ~ expansion), and YAML loader fidelity
  for extensions round-trip (ruamel.yaml vs PyYAML). Downstream consumers (IDEA-004,
  IDEA-006, IDEA-008) wire up in separate tasks under this epic after foundation lands.'
docs:
  spec: docs/superpowers/specs/2026-05-17-taskmaster-project-yaml-design.md
id: project-manifest-001
title: Implement .taskmaster/project.yaml manifest — schema + loader + 6 MCP tools
---
