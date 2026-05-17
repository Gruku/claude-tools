# `.taskmaster/project.yaml` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `.taskmaster/project.yaml` as taskmaster's Project manifest — a Pydantic-free, PyYAML-based, mostly-optional structured truth for repos, submodules, branch protocols, error-trace ladders, and conventions. Foundation for harvest-2026-05 consumers (IDEA-004, IDEA-006, IDEA-008).

**Architecture:** New module `plugins/taskmaster/project.py` holding dataclasses + validator + `ProjectManifest` loader. `taskmaster_v3.py` adds six `backlog_project_*` MCP tool wrappers. No new dependencies — uses stdlib `dataclasses` and existing PyYAML. Soft validation on read (never crashes taskmaster), strict on write.

**Tech Stack:** Python 3.10+, PyYAML, stdlib `dataclasses`, pytest with the existing `tmp_taskmaster` fixture in `plugins/taskmaster/tests/conftest.py`.

**Spec:** `docs/superpowers/specs/2026-05-17-taskmaster-project-yaml-design.md`

**Resolved open questions:**
- *Pydantic v1 vs v2* → neither. Use `@dataclass` + hand validation to match existing taskmaster convention (zero new dependencies).
- *Path resolution* → relative paths resolve against project root (the directory containing `.taskmaster/`). Absolute paths pass through. No `~` expansion.
- *YAML round-trip fidelity* → PyYAML with `sort_keys=False`, `default_flow_style=False`, `allow_unicode=True`. Comments are not preserved on programmatic writes; the `extensions:` dict round-trips faithfully. Documented limitation.

**Backlog task:** `project-manifest-001`

---

## File Structure

**New:**
- `plugins/taskmaster/project.py` — dataclasses, validator, `ProjectManifest` class, six MCP-callable helper functions
- `plugins/taskmaster/tests/test_project_dataclasses.py` — dataclass + validator unit tests
- `plugins/taskmaster/tests/test_project_loader.py` — load / load_or_default / round-trip tests
- `plugins/taskmaster/tests/test_project_helpers.py` — ship_order, error_trace_ladder, policy lookup tests
- `plugins/taskmaster/tests/test_project_mcp_tools.py` — MCP tool surface tests

**Modified:**
- `plugins/taskmaster/taskmaster_v3.py` — add six `backlog_project_*` MCP tool wrappers near existing `backlog_*` tools
- `CLAUDE.md` — add section pointing tooling consumers at `.taskmaster/project.yaml`
- `C:\Users\gruku\.claude\projects\C--Users-gruku-Files-Claude-claude-tools\memory\project_taskmaster_project_yaml.md` — flip status from "designed" to "implemented"

**Out-of-repo authored content (Task 8):**
- `C:\Users\gruku\Files\Work\CodeMaestro\.taskmaster\project.yaml` — canonical example, committed in the CodeMaestro repo

---

## Task 1: Path resolution + manifest discovery

**Files:**
- Create: `plugins/taskmaster/project.py` (initial scaffold)
- Test: `plugins/taskmaster/tests/test_project_loader.py`

- [ ] **Step 1: Write the failing test for path resolution**

Create `plugins/taskmaster/tests/test_project_loader.py`:

```python
from __future__ import annotations

from pathlib import Path

import pytest

from project import (
    PROJECT_YAML_RELATIVE,
    project_yaml_path,
    resolve_project_root,
)


def test_project_yaml_relative_path():
    assert PROJECT_YAML_RELATIVE == Path(".taskmaster") / "project.yaml"


def test_project_yaml_path_joins(tmp_path):
    assert project_yaml_path(tmp_path) == tmp_path / ".taskmaster" / "project.yaml"


def test_resolve_project_root_returns_dir_containing_taskmaster(tmp_path):
    (tmp_path / ".taskmaster").mkdir()
    nested = tmp_path / "src" / "deep"
    nested.mkdir(parents=True)
    assert resolve_project_root(nested) == tmp_path


def test_resolve_project_root_returns_none_when_not_found(tmp_path):
    nested = tmp_path / "src" / "deep"
    nested.mkdir(parents=True)
    assert resolve_project_root(nested) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_project_loader.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'project'`

- [ ] **Step 3: Create the minimal module**

Create `plugins/taskmaster/project.py`:

```python
"""`.taskmaster/project.yaml` — Project manifest loader.

Spec: docs/superpowers/specs/2026-05-17-taskmaster-project-yaml-design.md
"""
from __future__ import annotations

from pathlib import Path

PROJECT_YAML_RELATIVE = Path(".taskmaster") / "project.yaml"


def project_yaml_path(project_root: Path) -> Path:
    """Return the absolute path to .taskmaster/project.yaml for a project root."""
    return project_root / PROJECT_YAML_RELATIVE


def resolve_project_root(start: Path) -> Path | None:
    """Walk up from `start` looking for a directory containing `.taskmaster/`.

    Returns the directory containing `.taskmaster/`, or None if not found.
    """
    current = start.resolve()
    while True:
        if (current / ".taskmaster").is_dir():
            return current
        if current.parent == current:
            return None
        current = current.parent
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_project_loader.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/project.py plugins/taskmaster/tests/test_project_loader.py
git commit -m "feat(taskmaster): scaffold project.py with path resolution

First foundation for .taskmaster/project.yaml manifest.
Refs: project-manifest-001"
```

---

## Task 2: Dataclasses for the schema

**Files:**
- Modify: `plugins/taskmaster/project.py` (add dataclasses)
- Test: `plugins/taskmaster/tests/test_project_dataclasses.py` (new)

- [ ] **Step 1: Write the failing tests for dataclass shapes**

Create `plugins/taskmaster/tests/test_project_dataclasses.py`:

```python
from __future__ import annotations

from project import (
    Branches,
    DeployTarget,
    ErrorTraceEntry,
    ExternalIntegration,
    Knowledge,
    KnowledgeLink,
    Meta,
    Policies,
    ProjectIdentity,
    ProjectManifest,
    Repo,
    Submodule,
)


def test_repo_defaults():
    r = Repo(name="api", path="./api")
    assert r.name == "api"
    assert r.path == "./api"
    assert r.description == ""
    assert r.stack == []
    assert r.depends_on == []
    assert r.branches == Branches()
    assert r.push_policy == "always-ask"


def test_branches_defaults():
    b = Branches()
    assert b.default == ""
    assert b.protected == []
    assert b.naming == ""


def test_submodule_defaults():
    s = Submodule(name="mcp-host", parent_repo="app-desktop", path="mcp-host")
    assert s.pointer_policy == "separate-chore-commit"
    assert s.upstream == ""


def test_error_trace_entry_minimal():
    e = ErrorTraceEntry(layer="ui", kind="devtools-network")
    assert e.path == ""
    assert e.url == ""
    assert e.provider == ""


def test_policies_defaults():
    p = Policies()
    assert p.tdd == "preferred"
    assert p.commit_style == "freeform"
    assert p.spec_to_task_ratio_warn == 3


def test_project_manifest_empty():
    m = ProjectManifest(schema_version=1, meta=Meta(name="x", slug="x"))
    assert m.repos == []
    assert m.submodules == []
    assert m.extensions == {}
    assert m.conventions.policies.spec_to_task_ratio_warn == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_project_dataclasses.py -v`
Expected: FAIL — `ImportError: cannot import name 'Branches' from 'project'`

- [ ] **Step 3: Add dataclasses to project.py**

Append to `plugins/taskmaster/project.py`:

```python
from dataclasses import dataclass, field
from typing import Any


# Opinionated defaults baked into the schema (spec section "Schema (v1)")
_DEFAULT_PUSH_POLICY = "always-ask"
_DEFAULT_POINTER_POLICY = "separate-chore-commit"
_DEFAULT_TDD = "preferred"
_DEFAULT_COMMIT_STYLE = "freeform"
_DEFAULT_SPEC_RATIO_WARN = 3


@dataclass
class Branches:
    default: str = ""
    protected: list[str] = field(default_factory=list)
    naming: str = ""


@dataclass
class Repo:
    name: str
    path: str
    description: str = ""
    stack: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    branches: Branches = field(default_factory=Branches)
    push_policy: str = _DEFAULT_PUSH_POLICY


@dataclass
class Submodule:
    name: str
    parent_repo: str
    path: str
    description: str = ""
    stack: list[str] = field(default_factory=list)
    pointer_policy: str = _DEFAULT_POINTER_POLICY
    upstream: str = ""


@dataclass
class ErrorTraceEntry:
    layer: str
    kind: str  # devtools-network | console | http-log | trace
    description: str = ""
    path: str = ""
    url: str = ""
    provider: str = ""


@dataclass
class Observability:
    error_trace_ladder: list[ErrorTraceEntry] = field(default_factory=list)


@dataclass
class ExternalIntegration:
    name: str
    kind: str = ""
    docs: str = ""


@dataclass
class Integrations:
    observability: Observability = field(default_factory=Observability)
    external: list[ExternalIntegration] = field(default_factory=list)


@dataclass
class DeployTarget:
    target: str
    repos: list[str] = field(default_factory=list)
    branch: str = ""


@dataclass
class KnowledgeLink:
    title: str = ""
    path: str = ""
    url: str = ""


@dataclass
class Knowledge:
    docs: list[KnowledgeLink] = field(default_factory=list)
    dashboards: list[KnowledgeLink] = field(default_factory=list)
    links: list[KnowledgeLink] = field(default_factory=list)


@dataclass
class Policies:
    tdd: str = _DEFAULT_TDD
    commit_style: str = _DEFAULT_COMMIT_STYLE
    spec_to_task_ratio_warn: int = _DEFAULT_SPEC_RATIO_WARN


@dataclass
class Conventions:
    narrative_ref: str = "./CLAUDE.md"
    policies: Policies = field(default_factory=Policies)


@dataclass
class Meta:
    name: str
    slug: str
    kind: str = "app"  # app | library | research | platform | tool
    updated: str = ""


@dataclass
class ProjectIdentity:
    description: str = ""
    goal: str = ""
    owners: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@dataclass
class ProjectManifest:
    schema_version: int
    meta: Meta
    project: ProjectIdentity = field(default_factory=ProjectIdentity)
    repos: list[Repo] = field(default_factory=list)
    submodules: list[Submodule] = field(default_factory=list)
    integrations: Integrations = field(default_factory=Integrations)
    deploy: list[DeployTarget] = field(default_factory=list)
    knowledge: Knowledge = field(default_factory=Knowledge)
    conventions: Conventions = field(default_factory=Conventions)
    extensions: dict[str, Any] = field(default_factory=dict)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_project_dataclasses.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/project.py plugins/taskmaster/tests/test_project_dataclasses.py
git commit -m "feat(taskmaster): project.yaml dataclasses

Schema mirrors spec sections 1:1: Meta, ProjectIdentity, Repo, Submodule,
Integrations (observability + external), DeployTarget, Knowledge, Conventions
with Policies, plus opaque extensions dict.

Refs: project-manifest-001"
```

---

## Task 3: Hand-written validator

**Files:**
- Modify: `plugins/taskmaster/project.py` (add `validate_manifest_dict`)
- Test: `plugins/taskmaster/tests/test_project_dataclasses.py` (extend)

- [ ] **Step 1: Write the failing validator tests**

Append to `plugins/taskmaster/tests/test_project_dataclasses.py`:

```python
import pytest

from project import (
    KIND_VALUES,
    PUSH_POLICY_VALUES,
    SCHEMA_VERSION,
    TDD_VALUES,
    TRACE_KIND_VALUES,
    ValidationError,
    validate_manifest_dict,
)


def _minimal() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "meta": {"name": "x", "slug": "x"},
    }


def test_validate_minimal_ok():
    ok, errs = validate_manifest_dict(_minimal())
    assert ok is True
    assert errs == []


def test_missing_schema_version():
    data = _minimal()
    del data["schema_version"]
    ok, errs = validate_manifest_dict(data)
    assert ok is False
    assert any("schema_version" in e for e in errs)


def test_unknown_schema_version_major():
    data = _minimal()
    data["schema_version"] = 99
    ok, errs = validate_manifest_dict(data)
    assert ok is False
    assert any("schema_version" in e for e in errs)


def test_missing_meta_name_or_slug():
    for missing in ("name", "slug"):
        data = _minimal()
        del data["meta"][missing]
        ok, errs = validate_manifest_dict(data)
        assert ok is False
        assert any(missing in e for e in errs)


def test_invalid_kind_enum():
    data = _minimal()
    data["meta"]["kind"] = "spaceship"
    ok, errs = validate_manifest_dict(data)
    assert ok is False
    assert any("kind" in e for e in errs)
    assert any(v in " ".join(errs) for v in KIND_VALUES)


def test_repo_requires_name_and_path():
    data = _minimal()
    data["repos"] = [{"name": "api"}]
    ok, errs = validate_manifest_dict(data)
    assert ok is False
    assert any("path" in e for e in errs)


def test_repo_push_policy_enum():
    data = _minimal()
    data["repos"] = [{"name": "api", "path": "./api", "push_policy": "yolo"}]
    ok, errs = validate_manifest_dict(data)
    assert ok is False
    assert any("push_policy" in e for e in errs)


def test_repo_depends_on_cycle_detected():
    data = _minimal()
    data["repos"] = [
        {"name": "a", "path": "./a", "depends_on": ["b"]},
        {"name": "b", "path": "./b", "depends_on": ["a"]},
    ]
    ok, errs = validate_manifest_dict(data)
    assert ok is False
    assert any("cycle" in e.lower() for e in errs)


def test_repo_depends_on_unknown_repo():
    data = _minimal()
    data["repos"] = [{"name": "a", "path": "./a", "depends_on": ["ghost"]}]
    ok, errs = validate_manifest_dict(data)
    assert ok is False
    assert any("ghost" in e for e in errs)


def test_submodule_orphan_parent_repo():
    data = _minimal()
    data["submodules"] = [
        {"name": "x", "parent_repo": "ghost", "path": "x"}
    ]
    ok, errs = validate_manifest_dict(data)
    assert ok is False
    assert any("parent_repo" in e and "ghost" in e for e in errs)


def test_error_trace_kind_enum():
    data = _minimal()
    data["integrations"] = {
        "observability": {
            "error_trace_ladder": [{"layer": "ui", "kind": "smoke-signals"}]
        }
    }
    ok, errs = validate_manifest_dict(data)
    assert ok is False
    assert any("kind" in e for e in errs)


def test_policies_tdd_enum():
    data = _minimal()
    data["conventions"] = {"policies": {"tdd": "maybe"}}
    ok, errs = validate_manifest_dict(data)
    assert ok is False
    assert any("tdd" in e for e in errs)


def test_extensions_passthrough_ok():
    data = _minimal()
    data["extensions"] = {"anything": {"goes": True}}
    ok, errs = validate_manifest_dict(data)
    assert ok is True
    assert errs == []


def test_validation_error_aggregates_messages():
    data = _minimal()
    del data["meta"]["slug"]
    data["repos"] = [{"name": "a"}]
    with pytest.raises(ValidationError) as exc:
        validate_manifest_dict(data, raise_on_error=True)
    msg = str(exc.value)
    assert "slug" in msg
    assert "path" in msg
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_project_dataclasses.py -v`
Expected: FAIL — `ImportError: cannot import name 'validate_manifest_dict'`

- [ ] **Step 3: Add validator to project.py**

Append to `plugins/taskmaster/project.py`:

```python
SCHEMA_VERSION = 1

KIND_VALUES = ("app", "library", "research", "platform", "tool")
PUSH_POLICY_VALUES = ("always-ask", "gated", "open")
POINTER_POLICY_VALUES = ("separate-chore-commit", "allow-mixed")
TRACE_KIND_VALUES = ("devtools-network", "console", "http-log", "trace")
TDD_VALUES = ("required", "preferred", "optional")
COMMIT_STYLE_VALUES = ("conventional", "freeform")


class ValidationError(ValueError):
    """Raised when manifest validation fails in strict mode."""


def _check_enum(value: Any, allowed: tuple[str, ...], field: str, errors: list[str]) -> None:
    if value not in allowed:
        errors.append(f"{field}: {value!r} is not one of {list(allowed)}")


def _has_cycle(repos: list[dict]) -> bool:
    """DFS cycle detection over depends_on edges."""
    graph: dict[str, list[str]] = {r.get("name", ""): list(r.get("depends_on") or []) for r in repos}
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {name: WHITE for name in graph}

    def dfs(node: str) -> bool:
        color[node] = GRAY
        for nxt in graph.get(node, []):
            if nxt not in color:
                continue  # unknown repo — caught by separate validation
            if color[nxt] == GRAY:
                return True
            if color[nxt] == WHITE and dfs(nxt):
                return True
        color[node] = BLACK
        return False

    return any(color.get(n, WHITE) == WHITE and dfs(n) for n in graph)


def validate_manifest_dict(
    data: dict, *, raise_on_error: bool = False
) -> tuple[bool, list[str]]:
    """Validate a manifest dict against the v1 schema.

    Returns (ok, errors). If raise_on_error and not ok, raises ValidationError.
    """
    errors: list[str] = []

    sv = data.get("schema_version")
    if sv is None:
        errors.append("schema_version: required")
    elif sv != SCHEMA_VERSION:
        errors.append(f"schema_version: {sv!r} is unknown (expected {SCHEMA_VERSION})")

    meta = data.get("meta") or {}
    for required in ("name", "slug"):
        if not meta.get(required):
            errors.append(f"meta.{required}: required")
    if "kind" in meta:
        _check_enum(meta["kind"], KIND_VALUES, "meta.kind", errors)

    repos = data.get("repos") or []
    repo_names: set[str] = set()
    for i, r in enumerate(repos):
        name = r.get("name")
        if not name:
            errors.append(f"repos[{i}].name: required")
        else:
            repo_names.add(name)
        if not r.get("path"):
            errors.append(f"repos[{i}].path: required")
        if "push_policy" in r:
            _check_enum(r["push_policy"], PUSH_POLICY_VALUES, f"repos[{i}].push_policy", errors)

    for i, r in enumerate(repos):
        for dep in r.get("depends_on") or []:
            if dep not in repo_names:
                errors.append(f"repos[{i}].depends_on: unknown repo {dep!r}")
    if _has_cycle(repos):
        errors.append("repos: depends_on cycle detected")

    for i, s in enumerate(data.get("submodules") or []):
        for required in ("name", "parent_repo", "path"):
            if not s.get(required):
                errors.append(f"submodules[{i}].{required}: required")
        if s.get("parent_repo") and s["parent_repo"] not in repo_names:
            errors.append(
                f"submodules[{i}].parent_repo: unknown repo {s['parent_repo']!r}"
            )
        if "pointer_policy" in s:
            _check_enum(
                s["pointer_policy"], POINTER_POLICY_VALUES,
                f"submodules[{i}].pointer_policy", errors,
            )

    obs = (data.get("integrations") or {}).get("observability") or {}
    for i, e in enumerate(obs.get("error_trace_ladder") or []):
        for required in ("layer", "kind"):
            if not e.get(required):
                errors.append(f"integrations.observability.error_trace_ladder[{i}].{required}: required")
        if "kind" in e and e.get("kind"):
            _check_enum(
                e["kind"], TRACE_KIND_VALUES,
                f"integrations.observability.error_trace_ladder[{i}].kind", errors,
            )

    policies = (data.get("conventions") or {}).get("policies") or {}
    if "tdd" in policies:
        _check_enum(policies["tdd"], TDD_VALUES, "conventions.policies.tdd", errors)
    if "commit_style" in policies:
        _check_enum(
            policies["commit_style"], COMMIT_STYLE_VALUES,
            "conventions.policies.commit_style", errors,
        )

    ok = not errors
    if raise_on_error and not ok:
        raise ValidationError("\n".join(errors))
    return ok, errors
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_project_dataclasses.py -v`
Expected: PASS (all 14 dataclass tests + all 14 validator tests = 20 total)

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/project.py plugins/taskmaster/tests/test_project_dataclasses.py
git commit -m "feat(taskmaster): project.yaml validator

Per-section schema checks + topological cycle detection over
repos.depends_on. Enum sets are module constants so consumers (and
this plan) can introspect allowed values.

Refs: project-manifest-001"
```

---

## Task 4: `ProjectManifest.load` and `load_or_default`

**Files:**
- Modify: `plugins/taskmaster/project.py` (add load methods + dict↔dataclass converters)
- Test: `plugins/taskmaster/tests/test_project_loader.py` (extend)

- [ ] **Step 1: Write the failing load tests**

Append to `plugins/taskmaster/tests/test_project_loader.py`:

```python
import yaml

from project import (
    SCHEMA_VERSION,
    ProjectManifest,
    load_project_manifest,
    load_project_manifest_or_default,
    manifest_to_dict,
)


def _write_manifest(tmp_path, data: dict) -> None:
    (tmp_path / ".taskmaster").mkdir(exist_ok=True)
    (tmp_path / ".taskmaster" / "project.yaml").write_text(
        yaml.safe_dump(data, sort_keys=False), encoding="utf-8"
    )


def test_load_returns_none_when_file_missing(tmp_path):
    (tmp_path / ".taskmaster").mkdir()
    assert load_project_manifest(tmp_path) is None


def test_load_or_default_returns_empty_manifest_when_missing(tmp_path):
    (tmp_path / ".taskmaster").mkdir()
    m = load_project_manifest_or_default(tmp_path)
    assert isinstance(m, ProjectManifest)
    assert m.schema_version == SCHEMA_VERSION
    assert m.repos == []
    assert m.meta.name == ""  # synthetic placeholder
    assert m.meta.slug == ""


def test_load_minimal_manifest(tmp_path):
    _write_manifest(tmp_path, {
        "schema_version": SCHEMA_VERSION,
        "meta": {"name": "demo", "slug": "demo"},
    })
    m = load_project_manifest(tmp_path)
    assert m is not None
    assert m.meta.name == "demo"


def test_load_full_manifest_round_trips(tmp_path):
    data = {
        "schema_version": SCHEMA_VERSION,
        "meta": {"name": "cm", "slug": "cm", "kind": "app"},
        "project": {"goal": "ship it", "owners": ["gruku"]},
        "repos": [
            {"name": "api", "path": "./api", "branches": {"default": "develop"}},
            {"name": "ui", "path": "./ui", "depends_on": ["api"]},
        ],
        "submodules": [
            {"name": "mcp", "parent_repo": "ui", "path": "mcp"}
        ],
        "extensions": {"foo": "bar"},
    }
    _write_manifest(tmp_path, data)
    m = load_project_manifest(tmp_path)
    assert m is not None
    assert len(m.repos) == 2
    assert m.repos[1].depends_on == ["api"]
    assert m.submodules[0].parent_repo == "ui"
    assert m.extensions == {"foo": "bar"}
    # Round-trip
    assert manifest_to_dict(m)["extensions"] == {"foo": "bar"}


def test_load_invalid_manifest_returns_none_and_warns(tmp_path, caplog):
    _write_manifest(tmp_path, {"schema_version": 99, "meta": {}})
    m = load_project_manifest(tmp_path)
    assert m is None
    assert any("project.yaml" in rec.message for rec in caplog.records)


def test_load_malformed_yaml_returns_none(tmp_path, caplog):
    (tmp_path / ".taskmaster").mkdir()
    (tmp_path / ".taskmaster" / "project.yaml").write_text(
        "not: valid: yaml: [\n", encoding="utf-8"
    )
    assert load_project_manifest(tmp_path) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_project_loader.py -v`
Expected: FAIL — `ImportError: cannot import name 'load_project_manifest'`

- [ ] **Step 3: Add load methods + converters to project.py**

Append to `plugins/taskmaster/project.py`:

```python
import logging
from dataclasses import asdict, fields, is_dataclass

import yaml

_log = logging.getLogger(__name__)


def _dict_to_dataclass(cls, data: Any):
    """Recursively coerce a dict into a dataclass instance, ignoring unknown keys."""
    if data is None:
        return cls() if _has_all_defaults(cls) else None
    if not is_dataclass(cls):
        return data
    kwargs: dict[str, Any] = {}
    type_hints = {f.name: f.type for f in fields(cls)}
    for f in fields(cls):
        if f.name not in data:
            continue
        raw = data[f.name]
        kwargs[f.name] = _coerce_field(type_hints[f.name], raw)
    return cls(**kwargs)


def _coerce_field(type_hint: Any, raw: Any) -> Any:
    """Handle list[X], dict[...], dataclass, and primitive types."""
    origin = getattr(type_hint, "__origin__", None)
    if origin is list:
        (inner,) = type_hint.__args__
        if is_dataclass(inner):
            return [_dict_to_dataclass(inner, item) for item in (raw or [])]
        return list(raw or [])
    if origin is dict:
        return dict(raw or {})
    # Forward references resolve via typing.get_type_hints in practice; for our
    # closed schema, direct dataclass references work because we don't use strings.
    if is_dataclass(type_hint):
        return _dict_to_dataclass(type_hint, raw or {})
    return raw


def _has_all_defaults(cls) -> bool:
    """True if every field has a default or default_factory."""
    return all(
        f.default is not f.default or f.default_factory is not f.default_factory  # noqa: PLR0124
        for f in fields(cls)
    ) or all(
        (f.default is not __import__("dataclasses").MISSING)
        or (f.default_factory is not __import__("dataclasses").MISSING)
        for f in fields(cls)
    )


def load_project_manifest(project_root: Path) -> ProjectManifest | None:
    """Soft load: returns None if file missing, malformed, or invalid.

    Never raises. Validation failures and YAML errors are logged at WARNING.
    """
    path = project_yaml_path(project_root)
    if not path.is_file():
        return None
    try:
        raw_text = path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw_text) or {}
    except (OSError, yaml.YAMLError) as exc:
        _log.warning("Failed to read %s: %s", path, exc)
        return None
    if not isinstance(data, dict):
        _log.warning("%s: top-level value is not a mapping", path)
        return None
    ok, errors = validate_manifest_dict(data)
    if not ok:
        _log.warning("%s validation failed: %s", path, "; ".join(errors))
        return None
    return _dict_to_dataclass(ProjectManifest, data)


def load_project_manifest_or_default(project_root: Path) -> ProjectManifest:
    """Always returns a manifest. Missing/invalid files yield an empty one."""
    m = load_project_manifest(project_root)
    if m is not None:
        return m
    return ProjectManifest(schema_version=SCHEMA_VERSION, meta=Meta(name="", slug=""))


def manifest_to_dict(manifest: ProjectManifest) -> dict:
    """Convert a ProjectManifest back to a plain dict, suitable for YAML dump."""
    return asdict(manifest)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_project_loader.py -v`
Expected: PASS (10 tests: 4 from Task 1 + 6 new)

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/project.py plugins/taskmaster/tests/test_project_loader.py
git commit -m "feat(taskmaster): ProjectManifest load + load_or_default

Soft load returns None on missing/malformed/invalid (logged WARNING).
load_or_default returns an empty-but-valid manifest. Recursive dict-to-
dataclass coercion ignores unknown keys (forward-compat with future
schema_versions that add fields).

Refs: project-manifest-001"
```

---

## Task 5: Helper API methods

**Files:**
- Modify: `plugins/taskmaster/project.py` (add methods on ProjectManifest)
- Test: `plugins/taskmaster/tests/test_project_helpers.py` (new)

- [ ] **Step 1: Write the failing helper tests**

Create `plugins/taskmaster/tests/test_project_helpers.py`:

```python
from __future__ import annotations

import pytest

from project import (
    SCHEMA_VERSION,
    Branches,
    ErrorTraceEntry,
    Meta,
    Observability,
    Integrations,
    Policies,
    Conventions,
    ProjectManifest,
    Repo,
    Submodule,
)


def _manifest(**overrides) -> ProjectManifest:
    base = ProjectManifest(schema_version=SCHEMA_VERSION, meta=Meta(name="x", slug="x"))
    for k, v in overrides.items():
        setattr(base, k, v)
    return base


def test_repo_lookup_by_name():
    m = _manifest(repos=[Repo(name="api", path="./api"), Repo(name="ui", path="./ui")])
    assert m.repo("api").path == "./api"
    assert m.repo("missing") is None


def test_submodule_lookup_by_name():
    m = _manifest(
        repos=[Repo(name="ui", path="./ui")],
        submodules=[Submodule(name="mcp", parent_repo="ui", path="mcp")],
    )
    assert m.submodule("mcp").parent_repo == "ui"
    assert m.submodule("missing") is None


def test_ship_order_topological():
    m = _manifest(repos=[
        Repo(name="ui", path="./ui", depends_on=["api"]),
        Repo(name="api", path="./api"),
        Repo(name="app", path="./app", depends_on=["ui"]),
    ])
    assert m.ship_order() == ["api", "ui", "app"]


def test_ship_order_independent_repos_stable():
    m = _manifest(repos=[
        Repo(name="a", path="./a"),
        Repo(name="b", path="./b"),
    ])
    assert m.ship_order() == ["a", "b"]


def test_ship_order_raises_on_cycle():
    m = _manifest(repos=[
        Repo(name="a", path="./a", depends_on=["b"]),
        Repo(name="b", path="./b", depends_on=["a"]),
    ])
    with pytest.raises(ValueError, match="cycle"):
        m.ship_order()


def test_protected_branches():
    m = _manifest(repos=[
        Repo(name="api", path="./api",
             branches=Branches(default="develop", protected=["develop", "master"]))
    ])
    assert m.protected_branches("api") == ["develop", "master"]
    assert m.protected_branches("missing") == []


def test_policy_lookup_with_default():
    m = _manifest(conventions=Conventions(policies=Policies(spec_to_task_ratio_warn=5)))
    assert m.policy("spec_to_task_ratio_warn") == 5
    assert m.policy("unknown_key", default="fallback") == "fallback"


def test_error_trace_ladder_returns_ordered_list():
    m = _manifest(integrations=Integrations(
        observability=Observability(error_trace_ladder=[
            ErrorTraceEntry(layer="ui", kind="devtools-network"),
            ErrorTraceEntry(layer="api", kind="http-log"),
        ])
    ))
    ladder = m.error_trace_ladder()
    assert [e.layer for e in ladder] == ["ui", "api"]


def test_orphan_submodule_warning(caplog):
    # parent_repo "ghost" not in repos — loader should drop and warn.
    # Simulate post-load behavior by running the helper directly.
    m = ProjectManifest(
        schema_version=SCHEMA_VERSION,
        meta=Meta(name="x", slug="x"),
        repos=[Repo(name="ui", path="./ui")],
        submodules=[
            Submodule(name="mcp", parent_repo="ui", path="mcp"),
            Submodule(name="orphan", parent_repo="ghost", path="orphan"),
        ],
    )
    living = m.valid_submodules()
    assert [s.name for s in living] == ["mcp"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_project_helpers.py -v`
Expected: FAIL — `AttributeError: 'ProjectManifest' object has no attribute 'repo'`

- [ ] **Step 3: Add helpers to ProjectManifest**

In `plugins/taskmaster/project.py`, add the following methods to the `ProjectManifest` dataclass (insert before the closing of the class definition, or use `@dataclass` followed by methods — dataclasses support methods normally):

```python
@dataclass
class ProjectManifest:
    schema_version: int
    meta: Meta
    project: ProjectIdentity = field(default_factory=ProjectIdentity)
    repos: list[Repo] = field(default_factory=list)
    submodules: list[Submodule] = field(default_factory=list)
    integrations: Integrations = field(default_factory=Integrations)
    deploy: list[DeployTarget] = field(default_factory=list)
    knowledge: Knowledge = field(default_factory=Knowledge)
    conventions: Conventions = field(default_factory=Conventions)
    extensions: dict[str, Any] = field(default_factory=dict)

    def repo(self, name: str) -> Repo | None:
        return next((r for r in self.repos if r.name == name), None)

    def submodule(self, name: str) -> Submodule | None:
        return next((s for s in self.submodules if s.name == name), None)

    def protected_branches(self, repo_name: str) -> list[str]:
        r = self.repo(repo_name)
        return list(r.branches.protected) if r else []

    def policy(self, key: str, default: Any = None) -> Any:
        return getattr(self.conventions.policies, key, default)

    def error_trace_ladder(self) -> list[ErrorTraceEntry]:
        return list(self.integrations.observability.error_trace_ladder)

    def ship_order(self) -> list[str]:
        """Topological sort of repos by depends_on. Raises ValueError on cycle.

        Stable for independent repos: returns them in declaration order.
        """
        order: list[str] = []
        visited: dict[str, int] = {r.name: 0 for r in self.repos}  # 0=white,1=gray,2=black
        repo_by_name = {r.name: r for r in self.repos}

        def visit(name: str) -> None:
            state = visited.get(name, 0)
            if state == 2:
                return
            if state == 1:
                raise ValueError(f"repos: depends_on cycle involving {name!r}")
            visited[name] = 1
            for dep in repo_by_name[name].depends_on:
                if dep in repo_by_name:
                    visit(dep)
            visited[name] = 2
            order.append(name)

        for r in self.repos:
            visit(r.name)
        return order

    def valid_submodules(self) -> list[Submodule]:
        """Drop submodules whose parent_repo is not in repos. Warns on drop."""
        repo_names = {r.name for r in self.repos}
        living: list[Submodule] = []
        for s in self.submodules:
            if s.parent_repo in repo_names:
                living.append(s)
            else:
                _log.warning(
                    "submodule %r has unknown parent_repo %r — dropping",
                    s.name, s.parent_repo,
                )
        return living
```

Note: replace the existing `ProjectManifest` class definition in `project.py` with this expanded version that includes the methods.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_project_helpers.py plugins/taskmaster/tests/test_project_dataclasses.py plugins/taskmaster/tests/test_project_loader.py -v`
Expected: PASS (all previous tests still pass + 9 new helper tests)

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/project.py plugins/taskmaster/tests/test_project_helpers.py
git commit -m "feat(taskmaster): ProjectManifest helper API

repo/submodule lookup, ship_order topo-sort with cycle detection,
protected_branches, policy lookup with default, error_trace_ladder,
valid_submodules (drops orphans with warning).

Refs: project-manifest-001"
```

---

## Task 6: MCP read tools — get, get_field, ship_order

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py` (add tool wrappers)
- Test: `plugins/taskmaster/tests/test_project_mcp_tools.py` (new)

Important: locate where existing `backlog_*` MCP tools are registered in `taskmaster_v3.py` (search for `@mcp.tool()` or similar decorator). The exact registration mechanism is established convention — match it. The tool functions themselves are below.

- [ ] **Step 1: Find the MCP tool registration pattern**

Run: `grep -n "@mcp.tool\|def backlog_get_task\|def backlog_status" plugins/taskmaster/taskmaster_v3.py | head -10`
Expected output: a series of `@mcp.tool()` decorators and adjacent `def backlog_*` function definitions. Note the line range — this is where new tools go.

- [ ] **Step 2: Write the failing MCP tool tests**

Create `plugins/taskmaster/tests/test_project_mcp_tools.py`:

```python
from __future__ import annotations

import yaml

# Import the underlying functions, not the @mcp.tool decorated versions.
# Match the existing test pattern (see test_backlog_status_slim.py for an example).
from taskmaster_v3 import (
    backlog_project_error_trace_ladder,
    backlog_project_get,
    backlog_project_get_field,
    backlog_project_init,
    backlog_project_set,
    backlog_project_ship_order,
)
from project import SCHEMA_VERSION


def _write(tmp_taskmaster, data: dict) -> None:
    (tmp_taskmaster / ".taskmaster" / "project.yaml").write_text(
        yaml.safe_dump(data, sort_keys=False), encoding="utf-8"
    )


def test_get_returns_none_when_missing(tmp_taskmaster):
    assert backlog_project_get() is None


def test_get_returns_dict_when_present(tmp_taskmaster):
    _write(tmp_taskmaster, {
        "schema_version": SCHEMA_VERSION,
        "meta": {"name": "x", "slug": "x"},
    })
    result = backlog_project_get()
    assert result["meta"]["name"] == "x"


def test_get_field_dotted_path(tmp_taskmaster):
    _write(tmp_taskmaster, {
        "schema_version": SCHEMA_VERSION,
        "meta": {"name": "x", "slug": "x"},
        "repos": [
            {"name": "api", "path": "./api",
             "branches": {"default": "develop", "protected": ["master"]}}
        ],
    })
    assert backlog_project_get_field("meta.name") == "x"
    assert backlog_project_get_field("repos[0].name") == "api"
    assert backlog_project_get_field("repos[0].branches.protected[0]") == "master"


def test_get_field_returns_none_on_missing_path(tmp_taskmaster):
    _write(tmp_taskmaster, {
        "schema_version": SCHEMA_VERSION, "meta": {"name": "x", "slug": "x"}
    })
    assert backlog_project_get_field("project.goal") is None
    assert backlog_project_get_field("repos[3].name") is None


def test_ship_order_returns_topo_sorted(tmp_taskmaster):
    _write(tmp_taskmaster, {
        "schema_version": SCHEMA_VERSION,
        "meta": {"name": "x", "slug": "x"},
        "repos": [
            {"name": "ui", "path": "./ui", "depends_on": ["api"]},
            {"name": "api", "path": "./api"},
        ],
    })
    assert backlog_project_ship_order() == ["api", "ui"]


def test_ship_order_returns_empty_when_no_manifest(tmp_taskmaster):
    assert backlog_project_ship_order() == []
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_project_mcp_tools.py -v`
Expected: FAIL — `ImportError: cannot import name 'backlog_project_get'`

- [ ] **Step 4: Add three tools to taskmaster_v3.py**

At the location identified in Step 1 (near other `@mcp.tool()` decorators), add:

```python
# --- .taskmaster/project.yaml (Project manifest) ---

from project import (
    ProjectManifest,
    load_project_manifest,
    manifest_to_dict,
    project_yaml_path,
    resolve_project_root,
    validate_manifest_dict,
)


def _project_root_or_cwd() -> Path:
    """Resolve a project root from ROOT (the module-level cwd anchor) or fall back."""
    root = resolve_project_root(ROOT)
    return root if root is not None else ROOT


@mcp.tool()
def backlog_project_get() -> dict | None:
    """Return the full .taskmaster/project.yaml as a dict, or None if missing/invalid."""
    m = load_project_manifest(_project_root_or_cwd())
    return manifest_to_dict(m) if m is not None else None


@mcp.tool()
def backlog_project_get_field(path: str) -> Any:
    """Read a single field via dotted/indexed path.

    Examples:
        "meta.name"
        "repos[0].name"
        "repos[0].branches.protected[0]"

    Returns None if any segment is missing or out of range.
    """
    m = load_project_manifest(_project_root_or_cwd())
    if m is None:
        return None
    return _dig(manifest_to_dict(m), path)


@mcp.tool()
def backlog_project_ship_order() -> list[str]:
    """Return repos in topological dependency order. Empty list if no manifest.

    Raises ValueError if depends_on contains a cycle (caught by validator on load).
    """
    m = load_project_manifest(_project_root_or_cwd())
    return m.ship_order() if m is not None else []


_PATH_TOKEN = re.compile(r"([^.\[\]]+)|\[(\d+)\]")


def _dig(data: Any, path: str) -> Any:
    cursor: Any = data
    for match in _PATH_TOKEN.finditer(path):
        key, idx = match.group(1), match.group(2)
        try:
            if key is not None:
                cursor = cursor[key]
            else:
                cursor = cursor[int(idx)]
        except (KeyError, IndexError, TypeError):
            return None
    return cursor
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_project_mcp_tools.py -v`
Expected: PASS (6 tests)

- [ ] **Step 6: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_project_mcp_tools.py
git commit -m "feat(taskmaster): MCP read tools for project.yaml

backlog_project_get, backlog_project_get_field (dotted+indexed paths),
backlog_project_ship_order. Reads .taskmaster/project.yaml relative to
ROOT (the existing cwd anchor) walking up to find the manifest.

Refs: project-manifest-001"
```

---

## Task 7: MCP write tools — set, init, error_trace_ladder

**Files:**
- Modify: `plugins/taskmaster/taskmaster_v3.py` (add three more tools)
- Test: `plugins/taskmaster/tests/test_project_mcp_tools.py` (extend)

- [ ] **Step 1: Write the failing write-side tests**

Append to `plugins/taskmaster/tests/test_project_mcp_tools.py`:

```python
import pytest


def test_set_writes_and_round_trips(tmp_taskmaster):
    yaml_text = """\
schema_version: 1
meta:
  name: demo
  slug: demo
"""
    backlog_project_set(yaml_text)
    written = (tmp_taskmaster / ".taskmaster" / "project.yaml").read_text(encoding="utf-8")
    assert "name: demo" in written
    assert backlog_project_get()["meta"]["name"] == "demo"


def test_set_rejects_invalid_yaml(tmp_taskmaster):
    with pytest.raises(ValueError, match="YAML"):
        backlog_project_set("not: valid: [\n")


def test_set_rejects_invalid_schema(tmp_taskmaster):
    bad = "schema_version: 99\nmeta:\n  name: x\n  slug: x\n"
    with pytest.raises(ValueError, match="schema_version"):
        backlog_project_set(bad)


def test_init_creates_scaffold_when_missing(tmp_taskmaster):
    result = backlog_project_init(name="demo", slug="demo")
    assert "created" in result.lower() or "wrote" in result.lower()
    data = backlog_project_get()
    assert data["meta"]["name"] == "demo"
    assert data["meta"]["slug"] == "demo"
    assert data["schema_version"] == SCHEMA_VERSION


def test_init_refuses_to_overwrite(tmp_taskmaster):
    backlog_project_init(name="demo", slug="demo")
    with pytest.raises(ValueError, match="exists"):
        backlog_project_init(name="other", slug="other")


def test_error_trace_ladder_returns_ladder(tmp_taskmaster):
    _write(tmp_taskmaster, {
        "schema_version": SCHEMA_VERSION,
        "meta": {"name": "x", "slug": "x"},
        "integrations": {"observability": {"error_trace_ladder": [
            {"layer": "ui", "kind": "devtools-network"},
            {"layer": "api", "kind": "http-log", "path": "/var/log/api"},
        ]}},
    })
    ladder = backlog_project_error_trace_ladder()
    assert [e["layer"] for e in ladder] == ["ui", "api"]
    assert ladder[1]["path"] == "/var/log/api"


def test_error_trace_ladder_empty_when_no_manifest(tmp_taskmaster):
    assert backlog_project_error_trace_ladder() == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_project_mcp_tools.py -v`
Expected: FAIL — `ImportError: cannot import name 'backlog_project_set'`

- [ ] **Step 3: Add three more tools to taskmaster_v3.py**

Below the read tools added in Task 6:

```python
@mcp.tool()
def backlog_project_set(yaml_content: str) -> str:
    """Write .taskmaster/project.yaml with strict validation.

    Raises ValueError if YAML is malformed or schema invalid. Atomic write
    using the existing atomic_write helper. Returns the absolute path written.
    """
    try:
        data = yaml.safe_load(yaml_content) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"YAML parse failed: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("project.yaml top-level must be a mapping")
    validate_manifest_dict(data, raise_on_error=True)

    root = _project_root_or_cwd()
    path = project_yaml_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Re-emit through PyYAML for canonical formatting.
    rendered = yaml.safe_dump(data, sort_keys=False, allow_unicode=True, default_flow_style=False)
    atomic_write(path, rendered)
    return str(path)


@mcp.tool()
def backlog_project_init(name: str, slug: str = "") -> str:
    """Scaffold a minimal valid project.yaml. Refuses to overwrite.

    Returns a confirmation message including the path written.
    """
    root = _project_root_or_cwd()
    path = project_yaml_path(root)
    if path.exists():
        raise ValueError(f"{path} exists — refusing to overwrite (edit it directly)")
    slug = slug or _slugify(name)
    scaffold = {
        "schema_version": SCHEMA_VERSION,
        "meta": {"name": name, "slug": slug, "kind": "app"},
        "project": {"description": "", "goal": "", "owners": [], "tags": []},
        "repos": [],
        "submodules": [],
        "integrations": {"observability": {"error_trace_ladder": []}, "external": []},
        "conventions": {"narrative_ref": "./CLAUDE.md", "policies": {}},
        "extensions": {},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(
        path,
        yaml.safe_dump(scaffold, sort_keys=False, allow_unicode=True, default_flow_style=False),
    )
    return f"Created {path}"


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", name.lower()).strip("-") or "project"


@mcp.tool()
def backlog_project_error_trace_ladder() -> list[dict]:
    """Return the observability error-trace ladder as a list of dicts.

    Empty list if no manifest. Consumed by IDEA-006 Diagnose-Auth-Or-Not.
    """
    m = load_project_manifest(_project_root_or_cwd())
    if m is None:
        return []
    return [asdict(e) for e in m.error_trace_ladder()]
```

Note: `atomic_write`, `ROOT`, and `mcp` are existing names in `taskmaster_v3.py`. The import `from dataclasses import asdict` may already be present; add it if not.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_project_mcp_tools.py -v`
Expected: PASS (13 tests: 6 from Task 6 + 7 new)

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_project_mcp_tools.py
git commit -m "feat(taskmaster): MCP write tools for project.yaml

backlog_project_set (strict validation, atomic write),
backlog_project_init (scaffolds minimal valid manifest, refuses to overwrite),
backlog_project_error_trace_ladder (consumed by Diagnose-Auth-Or-Not).
All six backlog_project_* tools now live.

Refs: project-manifest-001"
```

---

## Task 8: Author CodeMaestro's project.yaml as canonical example

This task is content authoring, not code. It lives in the CodeMaestro repo (`C:\Users\gruku\Files\Work\CodeMaestro`), not claude-tools. It validates the schema against a real multi-repo project and gives downstream harvest consumers a real file to read.

**Files (in CodeMaestro repo):**
- Create: `C:\Users\gruku\Files\Work\CodeMaestro\.taskmaster\project.yaml`

- [ ] **Step 1: Confirm the foundation is installed in CodeMaestro's taskmaster**

Run: `cd C:\Users\gruku\Files\Work\CodeMaestro && python -c "from plugins.taskmaster.project import SCHEMA_VERSION; print(SCHEMA_VERSION)"`
Expected: `1` (or via whichever taskmaster install CodeMaestro uses — adjust path).

If CodeMaestro pulls taskmaster via the plugin install, ensure the plugin version with `project.py` is installed first (e.g., bump plugin version in claude-tools, reinstall).

- [ ] **Step 2: Author the manifest**

Create `C:\Users\gruku\Files\Work\CodeMaestro\.taskmaster\project.yaml`:

```yaml
schema_version: 1
meta:
  name: CodeMaestro
  slug: codemaestro
  kind: app
project:
  description: "AI-assisted code editor with multi-agent dispatch"
  goal: "Ship an opinionated agent-native IDE"
  owners: [gruku]
  tags: [ai, agent-platform, ide]
repos:
  - name: api
    path: ./code-maestro-api
    description: "Backend API"
    stack: [python, fastapi, postgres]
    branches:
      default: develop
      protected: [develop, master]
      naming: feature/
    push_policy: always-ask
  - name: facade
    path: ./code-maestro-facade
    description: "Edge facade — API gateway + auth"
    stack: [python, fastapi]
    depends_on: [api]
    branches:
      default: develop
      protected: [develop, master]
      naming: feature/
    push_policy: always-ask
  - name: app-desktop
    path: ./code-maestro-app-desktop
    description: "Desktop client (Electron + React)"
    stack: [typescript, react, electron]
    depends_on: [facade]
    branches:
      default: develop
      protected: [develop, master]
      naming: feature/
    push_policy: always-ask
submodules:
  - name: mcp-host
    parent_repo: app-desktop
    path: mcp-host
    description: "MCP host runtime (vendored submodule)"
    stack: [typescript, node]
    pointer_policy: separate-chore-commit
integrations:
  observability:
    error_trace_ladder:
      - layer: ui
        kind: devtools-network
        description: "Browser network tab — fastest signal, but only request/response, no body"
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
  external:
    - name: openai
      kind: api
      docs: https://platform.openai.com/docs
    - name: anthropic
      kind: api
      docs: https://docs.anthropic.com
deploy:
  - target: staging
    repos: [api, facade, app-desktop]
    branch: develop
  - target: production
    repos: [api, facade, app-desktop]
    branch: master
knowledge:
  docs: []
  dashboards:
    - title: Langfuse production
      url: https://cloud.langfuse.com/project/cm-prod
  links: []
conventions:
  narrative_ref: ./CLAUDE.md
  policies:
    tdd: preferred
    commit_style: freeform
    spec_to_task_ratio_warn: 3
extensions: {}
```

- [ ] **Step 3: Validate the file by loading it**

Run: `cd C:\Users\gruku\Files\Work\CodeMaestro && python -c "from plugins.taskmaster.project import load_project_manifest; from pathlib import Path; m = load_project_manifest(Path('.')); print(m.ship_order())"`
Expected: `['api', 'facade', 'app-desktop']`

If the load returns `None`, check the warning log for the validation error and fix the manifest.

- [ ] **Step 4: Commit in the CodeMaestro repo**

```bash
cd C:\Users\gruku\Files\Work\CodeMaestro
git add .taskmaster/project.yaml
git commit -m "chore(taskmaster): add .taskmaster/project.yaml

Canonical Project manifest — repos, submodules, error-trace ladder,
deploy targets. Pairs with backlog.yaml. Consumed by harvest proposals
IDEA-004, IDEA-006, IDEA-008 once they land in claude-tools.

Schema: claude-tools docs/superpowers/specs/2026-05-17-taskmaster-project-yaml-design.md
Foundation: claude-tools project-manifest-001"
```

---

## Task 9: Docs/CLAUDE.md + memory updates

**Files:**
- Modify: `CLAUDE.md` (claude-tools root)
- Modify: `C:\Users\gruku\.claude\projects\C--Users-gruku-Files-Claude-claude-tools\memory\project_taskmaster_project_yaml.md`

- [ ] **Step 1: Update claude-tools CLAUDE.md to reference the manifest**

Add this section after the existing "Taskmaster architecture (quick orientation)" section in `C:\Users\gruku\Files\Claude\claude-tools\CLAUDE.md`:

```markdown
## Project manifest (`.taskmaster/project.yaml`)

Each project that uses taskmaster can declare its Project manifest at `.taskmaster/project.yaml` — the structured truth about repos, submodules, branch protocols, error-trace ladders, deploy targets, and conventions. Pairs with `backlog.yaml` (work in flight).

- **Schema, loader, helpers:** `plugins/taskmaster/project.py`
- **MCP surface:** `backlog_project_get`, `backlog_project_get_field`, `backlog_project_set`, `backlog_project_init`, `backlog_project_ship_order`, `backlog_project_error_trace_ladder`
- **Spec:** `docs/superpowers/specs/2026-05-17-taskmaster-project-yaml-design.md`
- **Forward-compatible** with the Agentic OS Projects-as-first-class direction; the same file becomes the Project definition the OS daemon reads.

When a downstream skill or hook needs to know about repos, branches, or observability layout, read the manifest — don't reinvent detection from `git remote` or hard-coded paths.
```

- [ ] **Step 2: Update the project memory file to reflect implementation status**

Edit `C:\Users\gruku\.claude\projects\C--Users-gruku-Files-Claude-claude-tools\memory\project_taskmaster_project_yaml.md` — append a status note at the end:

```markdown

## Implementation status (2026-05-17)

Landed under epic `project-manifest`, task `project-manifest-001`. The loader, validator, six MCP tools, and CodeMaestro's canonical manifest are all live. Downstream consumers (IDEA-004 Multi-Repo-Choreographer, IDEA-006 Diagnose-Auth-Or-Not, IDEA-008 Submodule-Drift-Check) now read `.taskmaster/project.yaml` directly.
```

- [ ] **Step 3: Commit (claude-tools)**

```bash
cd C:\Users\gruku\Files\Claude\claude-tools
git add CLAUDE.md
git commit -m "docs: reference .taskmaster/project.yaml from CLAUDE.md

Points downstream skills/hooks at the manifest as the source of truth
for repos, branches, observability layout. Avoids reinventing detection.

Refs: project-manifest-001"
```

Memory file updates aren't committed (the memory directory is outside the repo).

---

## Self-Review

**1. Spec coverage:**
- Top-level shape (spec §Top-level shape) → Task 2 dataclasses
- Each schema section (spec §Schema v1: meta, project, repos, submodules, integrations, deploy, knowledge, conventions, extensions) → Task 2 dataclasses
- Loader + validation strategy (spec §Loader and validation) → Tasks 3, 4
- Helper API (spec §Helper guarantees) → Task 5
- Six MCP tools (spec §MCP surface) → Tasks 6, 7
- Adoption sequence (spec §Adoption sequence) → Tasks 8 (CodeMaestro authoring), 9 (CLAUDE.md + memory). Wiring of downstream consumers IDEA-004/006/008 is explicitly out-of-scope for this task — each gets its own task under the same epic later.

Gap noted: spec mentions "`taskmaster:init-taskmaster` adds a scaffold project.yaml prompt for new projects". Not covered here — that's a skill edit, separate from this foundation task. Leave for a follow-up task in the same epic.

**2. Placeholder scan:** No TBD/TODO. All steps have concrete code or commands.

**3. Type consistency:**
- `ProjectManifest.ship_order()` returns `list[str]` everywhere (Tasks 5, 6).
- `backlog_project_error_trace_ladder()` returns `list[dict]` (asdict-converted from `ErrorTraceEntry`) — consistent across Task 7 def and tests.
- Validator function name is `validate_manifest_dict` everywhere (Tasks 3, 4, 7).
- Module name `project` (not `project_yaml` or `project_manifest`) — consistent across all imports.
- Field name `error_trace_ladder` consistent across spec, dataclasses, validator, helper, MCP tool.

No type drift detected.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-17-taskmaster-project-yaml.md`. Two execution options:

**1. Subagent-Driven (recommended)** — fresh subagent per task, two-stage review between tasks, fast iteration.

**2. Inline Execution** — execute tasks in this session using executing-plans, batch with checkpoints.

Which approach?
