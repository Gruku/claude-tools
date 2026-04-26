# Blast Radius Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add blast radius analysis to taskmaster — predictive impact analysis at pick-task time and evidence-based code tracing at review-gate time.

**Architecture:** A standalone `blast_radius.py` module handles all analysis logic (import parsing, graph tracing, depth heuristics, anchor matching). The backlog server exposes it via a `backlog_blast_radius` MCP tool. Skills (pick-task, review-gate) call the tool and layer on LLM-driven judgment.

**Tech Stack:** Python 3.11+, pathlib, subprocess (git), re (import parsing), ast (export detection). No new dependencies.

**Spec:** `docs/superpowers/specs/2026-04-08-blast-radius-design.md`

---

### Task 1: Create blast_radius.py with Config Helpers

**Files:**
- Create: `plugins/taskmaster/blast_radius.py`
- Create: `plugins/taskmaster/tests/test_blast_radius.py`

- [ ] **Step 1: Write test for config loading**

```python
# plugins/taskmaster/tests/test_blast_radius.py
import pytest
from pathlib import Path

# blast_radius.py is a pure utility — safe to import (no side effects)
from blast_radius import BlastRadiusConfig, load_config


def test_load_config_defaults():
    """When no blast_radius key in meta, use defaults."""
    meta = {"name": "test-project"}
    config = load_config(meta)
    assert config.fan_out_threshold == 5
    assert config.max_file_scan == 1000
    assert config.shared_dirs == []


def test_load_config_custom():
    """When blast_radius key exists, merge with defaults."""
    meta = {
        "blast_radius": {
            "fan_out_threshold": 10,
            "max_file_scan": 500,
            "shared_dirs": ["lib/", "core/"],
        }
    }
    config = load_config(meta)
    assert config.fan_out_threshold == 10
    assert config.max_file_scan == 500
    assert config.shared_dirs == ["lib/", "core/"]


def test_load_config_partial():
    """Partial config fills in defaults for missing keys."""
    meta = {"blast_radius": {"fan_out_threshold": 8}}
    config = load_config(meta)
    assert config.fan_out_threshold == 8
    assert config.max_file_scan == 1000
    assert config.shared_dirs == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd plugins/taskmaster && python -m pytest tests/test_blast_radius.py::test_load_config_defaults -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'blast_radius'`

- [ ] **Step 3: Write minimal implementation**

```python
# plugins/taskmaster/blast_radius.py
"""
Blast radius analysis for taskmaster tasks.

Provides two modes:
- Predictive: metadata-only analysis at pick-task time
- Evidence: code-level impact analysis at review-gate time

This module is a pure utility with no side effects — safe to import for testing.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


# ── Configuration ───────────────────────────────────────────


@dataclass
class BlastRadiusConfig:
    fan_out_threshold: int = 5
    max_file_scan: int = 1000
    shared_dirs: list[str] = field(default_factory=list)


def load_config(meta: dict) -> BlastRadiusConfig:
    """Load blast radius config from backlog meta, with defaults."""
    br = meta.get("blast_radius", {})
    return BlastRadiusConfig(
        fan_out_threshold=br.get("fan_out_threshold", 5),
        max_file_scan=br.get("max_file_scan", 1000),
        shared_dirs=br.get("shared_dirs", []),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd plugins/taskmaster && python -m pytest tests/test_blast_radius.py -v`
Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/blast_radius.py plugins/taskmaster/tests/test_blast_radius.py
git commit -m "feat(blast-radius): add config dataclass and loader"
```

---

### Task 2: Git Diff Helper

**Files:**
- Modify: `plugins/taskmaster/blast_radius.py`
- Modify: `plugins/taskmaster/tests/test_blast_radius.py`

- [ ] **Step 1: Write tests for git diff helper**

```python
# Add to tests/test_blast_radius.py
import subprocess
from unittest.mock import patch, MagicMock
from blast_radius import get_changed_files


def test_get_changed_files_basic(tmp_path):
    """Parse git diff --name-only output into list of relative paths."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "src/auth/middleware.py\nsrc/auth/session.py\n"

    with patch("blast_radius.subprocess.run", return_value=mock_result) as mock_run:
        files = get_changed_files("feature/auth", "main", tmp_path)

    assert files == ["src/auth/middleware.py", "src/auth/session.py"]
    mock_run.assert_called_once_with(
        ["git", "diff", "--name-only", "main...feature/auth"],
        capture_output=True, text=True, cwd=str(tmp_path), timeout=30,
    )


def test_get_changed_files_empty(tmp_path):
    """No changes returns empty list."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = ""

    with patch("blast_radius.subprocess.run", return_value=mock_result):
        files = get_changed_files("feature/x", "main", tmp_path)

    assert files == []


def test_get_changed_files_git_error(tmp_path):
    """Git failure returns empty list."""
    mock_result = MagicMock()
    mock_result.returncode = 128
    mock_result.stderr = "fatal: bad revision"

    with patch("blast_radius.subprocess.run", return_value=mock_result):
        files = get_changed_files("bad-branch", "main", tmp_path)

    assert files == []


def test_get_changed_files_timeout(tmp_path):
    """Timeout returns empty list."""
    with patch("blast_radius.subprocess.run", side_effect=subprocess.TimeoutExpired("git", 30)):
        files = get_changed_files("feature/x", "main", tmp_path)

    assert files == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd plugins/taskmaster && python -m pytest tests/test_blast_radius.py::test_get_changed_files_basic -v`
Expected: FAIL — `ImportError: cannot import name 'get_changed_files'`

- [ ] **Step 3: Write implementation**

```python
# Add to blast_radius.py

# ── Git Helpers ─────────────────────────────────────────────


def get_changed_files(branch: str, base: str, cwd: Path) -> list[str]:
    """Get list of files changed between base and branch via git diff."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{base}...{branch}"],
            capture_output=True, text=True, cwd=str(cwd), timeout=30,
        )
        if result.returncode != 0:
            return []
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []

    return [f for f in result.stdout.strip().splitlines() if f.strip()]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd plugins/taskmaster && python -m pytest tests/test_blast_radius.py -k "get_changed" -v`
Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/blast_radius.py plugins/taskmaster/tests/test_blast_radius.py
git commit -m "feat(blast-radius): add git diff helper"
```

---

### Task 3: Import Parsers

**Files:**
- Modify: `plugins/taskmaster/blast_radius.py`
- Modify: `plugins/taskmaster/tests/test_blast_radius.py`

- [ ] **Step 1: Write tests for Python import parser**

```python
# Add to tests/test_blast_radius.py
from blast_radius import parse_imports_python


def test_parse_imports_python_basic():
    source = """
import os
import sys
from pathlib import Path
from auth.middleware import AuthMiddleware
from . import utils
from ..core import base
"""
    imports = parse_imports_python(source)
    assert "os" in imports
    assert "sys" in imports
    assert "pathlib" in imports
    assert "auth.middleware" in imports
    assert "." in imports  # relative
    assert "..core" in imports  # relative


def test_parse_imports_python_multiline():
    source = """
from auth.middleware import (
    AuthMiddleware,
    SessionHandler,
)
"""
    imports = parse_imports_python(source)
    assert "auth.middleware" in imports


def test_parse_imports_python_comments_ignored():
    source = """
# import os
import sys
# from pathlib import Path
"""
    imports = parse_imports_python(source)
    assert "os" not in imports
    assert "sys" in imports
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd plugins/taskmaster && python -m pytest tests/test_blast_radius.py::test_parse_imports_python_basic -v`
Expected: FAIL — `ImportError: cannot import name 'parse_imports_python'`

- [ ] **Step 3: Write Python parser implementation**

```python
# Add to blast_radius.py

# ── Import Parsers ──────────────────────────────────────────

# Python: match `import X` and `from X import Y` (skipping comments)
_PY_IMPORT_RE = re.compile(
    r"^(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))",
    re.MULTILINE,
)


def parse_imports_python(source: str) -> set[str]:
    """Extract module names from Python import statements."""
    imports: set[str] = set()
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        for match in _PY_IMPORT_RE.finditer(line):
            module = match.group(1) or match.group(2)
            if module:
                imports.add(module)
    return imports
```

- [ ] **Step 4: Run Python parser tests**

Run: `cd plugins/taskmaster && python -m pytest tests/test_blast_radius.py -k "parse_imports_python" -v`
Expected: 3 tests PASS

- [ ] **Step 5: Write tests for JS/TS import parser**

```python
# Add to tests/test_blast_radius.py
from blast_radius import parse_imports_js


def test_parse_imports_js_esm():
    source = """
import { AuthMiddleware } from './auth/middleware';
import * as session from "../auth/session";
import defaultExport from '@/core/base';
"""
    imports = parse_imports_js(source)
    assert "./auth/middleware" in imports
    assert "../auth/session" in imports
    assert "@/core/base" in imports


def test_parse_imports_js_require():
    source = """
const auth = require('./auth/middleware');
const { session } = require("../auth/session");
"""
    imports = parse_imports_js(source)
    assert "./auth/middleware" in imports
    assert "../auth/session" in imports


def test_parse_imports_js_dynamic():
    source = """
const mod = await import('./lazy/module');
"""
    imports = parse_imports_js(source)
    assert "./lazy/module" in imports
```

- [ ] **Step 6: Write JS/TS parser implementation**

```python
# Add to blast_radius.py

# JS/TS: import ... from 'path', require('path'), import('path')
_JS_IMPORT_FROM_RE = re.compile(r"""(?:from|require|import)\s*\(\s*['"]([^'"]+)['"]\s*\)|from\s+['"]([^'"]+)['"]""")


def parse_imports_js(source: str) -> set[str]:
    """Extract import paths from JS/TS source."""
    imports: set[str] = set()
    for match in _JS_IMPORT_FROM_RE.finditer(source):
        path = match.group(1) or match.group(2)
        if path:
            imports.add(path)
    return imports
```

- [ ] **Step 7: Run JS/TS parser tests**

Run: `cd plugins/taskmaster && python -m pytest tests/test_blast_radius.py -k "parse_imports_js" -v`
Expected: 3 tests PASS

- [ ] **Step 8: Write tests for Go import parser**

```python
# Add to tests/test_blast_radius.py
from blast_radius import parse_imports_go


def test_parse_imports_go_single():
    source = """
package main

import "fmt"
import "github.com/user/repo/auth"
"""
    imports = parse_imports_go(source)
    assert "fmt" in imports
    assert "github.com/user/repo/auth" in imports


def test_parse_imports_go_block():
    source = """
package main

import (
    "fmt"
    "os"
    "github.com/user/repo/session"
)
"""
    imports = parse_imports_go(source)
    assert "fmt" in imports
    assert "os" in imports
    assert "github.com/user/repo/session" in imports
```

- [ ] **Step 9: Write Go parser implementation**

```python
# Add to blast_radius.py

# Go: import "path" and import (...) blocks
_GO_IMPORT_SINGLE_RE = re.compile(r'^import\s+"([^"]+)"', re.MULTILINE)
_GO_IMPORT_BLOCK_RE = re.compile(r'import\s*\((.*?)\)', re.DOTALL)
_GO_IMPORT_LINE_RE = re.compile(r'"([^"]+)"')


def parse_imports_go(source: str) -> set[str]:
    """Extract import paths from Go source."""
    imports: set[str] = set()
    for match in _GO_IMPORT_SINGLE_RE.finditer(source):
        imports.add(match.group(1))
    for block_match in _GO_IMPORT_BLOCK_RE.finditer(source):
        for line_match in _GO_IMPORT_LINE_RE.finditer(block_match.group(1)):
            imports.add(line_match.group(1))
    return imports
```

- [ ] **Step 10: Run all parser tests**

Run: `cd plugins/taskmaster && python -m pytest tests/test_blast_radius.py -k "parse_imports" -v`
Expected: 8 tests PASS

- [ ] **Step 11: Write parser dispatcher and test**

```python
# Add to tests/test_blast_radius.py
from blast_radius import parse_imports


def test_parse_imports_dispatches_by_extension():
    py_source = "import os"
    js_source = "import x from './y';"
    go_source = 'import "fmt"'

    assert "os" in parse_imports(py_source, ".py")
    assert "./y" in parse_imports(js_source, ".js")
    assert "./y" in parse_imports(js_source, ".ts")
    assert "./y" in parse_imports(js_source, ".tsx")
    assert "fmt" in parse_imports(go_source, ".go")
    assert parse_imports("anything", ".rs") == set()  # unsupported
```

```python
# Add to blast_radius.py

# Extension to parser mapping
_PARSER_MAP = {
    ".py": parse_imports_python,
    ".js": parse_imports_js,
    ".ts": parse_imports_js,
    ".tsx": parse_imports_js,
    ".jsx": parse_imports_js,
    ".mjs": parse_imports_js,
    ".go": parse_imports_go,
}

SUPPORTED_EXTENSIONS = set(_PARSER_MAP.keys())


def parse_imports(source: str, extension: str) -> set[str]:
    """Dispatch to the appropriate import parser based on file extension."""
    parser = _PARSER_MAP.get(extension)
    if parser is None:
        return set()
    return parser(source)
```

- [ ] **Step 12: Run all tests**

Run: `cd plugins/taskmaster && python -m pytest tests/test_blast_radius.py -v`
Expected: All tests PASS

- [ ] **Step 13: Commit**

```bash
git add plugins/taskmaster/blast_radius.py plugins/taskmaster/tests/test_blast_radius.py
git commit -m "feat(blast-radius): add import parsers for Python, JS/TS, Go"
```

---

### Task 4: Import Graph Tracing

**Files:**
- Modify: `plugins/taskmaster/blast_radius.py`
- Modify: `plugins/taskmaster/tests/test_blast_radius.py`

- [ ] **Step 1: Write tests for find_importers**

```python
# Add to tests/test_blast_radius.py
from blast_radius import find_importers, BlastRadiusConfig


def test_find_importers(tmp_path):
    """Find files that import a given target file."""
    # Create a mini project
    (tmp_path / "auth").mkdir()
    (tmp_path / "auth" / "middleware.py").write_text("# auth middleware")
    (tmp_path / "api").mkdir()
    (tmp_path / "api" / "routes.py").write_text("from auth.middleware import check\n")
    (tmp_path / "api" / "admin.py").write_text("from auth.middleware import admin_check\n")
    (tmp_path / "api" / "health.py").write_text("import os\n")  # doesn't import target

    config = BlastRadiusConfig(max_file_scan=100)
    importers = find_importers("auth/middleware.py", tmp_path, config)

    importer_strs = {str(p) for p in importers}
    assert "api/routes.py" in importer_strs
    assert "api/admin.py" in importer_strs
    assert "api/health.py" not in importer_strs


def test_find_importers_respects_max_scan(tmp_path):
    """Stop scanning after max_file_scan files."""
    (tmp_path / "target.py").write_text("# target")
    # Create many files
    for i in range(20):
        (tmp_path / f"file_{i}.py").write_text(f"from target import x{i}\n")

    config = BlastRadiusConfig(max_file_scan=5)
    importers, truncated = find_importers_with_limit("target.py", tmp_path, config)

    assert truncated is True
    assert len(importers) <= 5
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd plugins/taskmaster && python -m pytest tests/test_blast_radius.py::test_find_importers -v`
Expected: FAIL — `ImportError: cannot import name 'find_importers'`

- [ ] **Step 3: Write find_importers implementation**

```python
# Add to blast_radius.py

# ── Import Graph Tracing ────────────────────────────────────


def _resolve_import_to_file(import_name: str, target_rel: str) -> bool:
    """Check if an import name could refer to the target file.

    Uses heuristic matching: converts file path to module path and checks
    if the import matches any suffix of the module path.
    E.g., target "auth/middleware.py" matches imports "auth.middleware",
    "middleware", "auth/middleware".
    """
    # Normalize target to module-style dotted path (without extension)
    target_module = target_rel.replace("/", ".").replace("\\", ".")
    for ext in SUPPORTED_EXTENSIONS:
        if target_module.endswith(ext):
            target_module = target_module[: -len(ext)]
            break
    # Also handle __init__.py → package name
    if target_module.endswith(".__init__"):
        target_module = target_module[: -len(".__init__")]

    # Normalize import (handle path-style imports in JS)
    import_normalized = import_name.replace("/", ".").replace("\\", ".")
    # Strip leading dots (relative imports)
    import_clean = import_normalized.lstrip(".")
    # Strip leading ./ for JS relative imports
    if import_clean.startswith("."):
        import_clean = import_clean[1:]

    # Check suffix match: "auth.middleware" matches import "middleware" or "auth.middleware"
    return (
        target_module == import_clean
        or target_module.endswith("." + import_clean)
        or import_clean.endswith("." + target_module.split(".")[-1])
    )


def find_importers(
    target_rel: str,
    project_root: Path,
    config: BlastRadiusConfig,
    sub_repo: str | None = None,
) -> list[str]:
    """Find files in the project that import the target file.

    Returns list of relative file paths (strings) that import the target.
    """
    importers, _ = find_importers_with_limit(target_rel, project_root, config, sub_repo)
    return importers


def find_importers_with_limit(
    target_rel: str,
    project_root: Path,
    config: BlastRadiusConfig,
    sub_repo: str | None = None,
) -> tuple[list[str], bool]:
    """Find importers with truncation info. Returns (importers, truncated)."""
    scan_root = project_root / sub_repo if sub_repo else project_root
    importers: list[str] = []
    files_scanned = 0
    truncated = False

    for ext in SUPPORTED_EXTENSIONS:
        for filepath in scan_root.rglob(f"*{ext}"):
            if files_scanned >= config.max_file_scan:
                truncated = True
                break

            rel = str(filepath.relative_to(project_root))
            if rel == target_rel:
                continue  # skip self

            files_scanned += 1
            try:
                source = filepath.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

            parsed = parse_imports(source, ext)
            for imp in parsed:
                if _resolve_import_to_file(imp, target_rel):
                    importers.append(rel)
                    break  # one match is enough, move to next file

        if truncated:
            break

    return importers, truncated
```

- [ ] **Step 4: Run find_importers tests**

Run: `cd plugins/taskmaster && python -m pytest tests/test_blast_radius.py -k "find_importers" -v`
Expected: 2 tests PASS

- [ ] **Step 5: Write test for trace_dependency_graph**

```python
# Add to tests/test_blast_radius.py
from blast_radius import trace_dependency_graph


def test_trace_dependency_graph_one_hop(tmp_path):
    """Trace one level of dependencies."""
    (tmp_path / "core.py").write_text("# core module")
    (tmp_path / "api.py").write_text("from core import Base\n")
    (tmp_path / "cli.py").write_text("from core import run\n")
    (tmp_path / "unrelated.py").write_text("import os\n")

    config = BlastRadiusConfig(max_file_scan=100)
    graph = trace_dependency_graph(
        changed_files=["core.py"],
        depths={"core.py": 1},
        project_root=tmp_path,
        config=config,
    )

    assert "core.py" in graph
    deps = set(graph["core.py"])
    assert "api.py" in deps
    assert "cli.py" in deps
    assert "unrelated.py" not in deps


def test_trace_dependency_graph_two_hops(tmp_path):
    """Trace two levels deep."""
    (tmp_path / "core.py").write_text("# core module")
    (tmp_path / "api.py").write_text("from core import Base\n")
    (tmp_path / "handler.py").write_text("from api import route\n")

    config = BlastRadiusConfig(max_file_scan=100)
    graph = trace_dependency_graph(
        changed_files=["core.py"],
        depths={"core.py": 2},
        project_root=tmp_path,
        config=config,
    )

    assert "api.py" in graph["core.py"]
    assert "handler.py" in graph.get("api.py", [])
```

- [ ] **Step 6: Write trace_dependency_graph implementation**

```python
# Add to blast_radius.py


def trace_dependency_graph(
    changed_files: list[str],
    depths: dict[str, int],
    project_root: Path,
    config: BlastRadiusConfig,
    sub_repo: str | None = None,
) -> dict[str, list[str]]:
    """Build dependency graph for changed files up to specified depths.

    Args:
        changed_files: List of relative file paths that changed.
        depths: Map of file -> max hops to trace.
        project_root: Root directory of the project.
        config: Blast radius configuration.
        sub_repo: Optional sub-repo scope.

    Returns:
        Dict mapping each file to its list of direct dependents (importers).
    """
    graph: dict[str, list[str]] = {}

    # BFS: process each changed file up to its specified depth
    for start_file in changed_files:
        max_depth = depths.get(start_file, 1)
        queue: list[tuple[str, int]] = [(start_file, 0)]
        visited: set[str] = {start_file}

        while queue:
            current_file, current_depth = queue.pop(0)
            if current_depth >= max_depth:
                continue

            importers = find_importers(current_file, project_root, config, sub_repo)
            if importers:
                graph[current_file] = importers

            # Queue next hop (only newly discovered files)
            for imp in importers:
                if imp not in visited:
                    visited.add(imp)
                    queue.append((imp, current_depth + 1))

    return graph
```

- [ ] **Step 7: Run all graph tracing tests**

Run: `cd plugins/taskmaster && python -m pytest tests/test_blast_radius.py -k "trace_dependency" -v`
Expected: 2 tests PASS

- [ ] **Step 8: Commit**

```bash
git add plugins/taskmaster/blast_radius.py plugins/taskmaster/tests/test_blast_radius.py
git commit -m "feat(blast-radius): add import graph tracing with configurable depth"
```

---

### Task 5: Export Change Detection

**Files:**
- Modify: `plugins/taskmaster/blast_radius.py`
- Modify: `plugins/taskmaster/tests/test_blast_radius.py`

- [ ] **Step 1: Write tests for export change detection**

```python
# Add to tests/test_blast_radius.py
from blast_radius import detect_export_changes


def test_detect_export_changes_python():
    """Detect changes to public function/class definitions."""
    old = """
def internal_helper():
    pass

def public_api():
    return 42

class AuthMiddleware:
    pass
"""
    new = """
def internal_helper():
    pass

def public_api(extra_arg):
    return 42

class AuthMiddleware:
    pass

def new_function():
    pass
"""
    result = detect_export_changes(old, new, ".py")
    assert result is True  # signatures changed


def test_detect_export_changes_no_change():
    """Internal-only changes don't count as export changes."""
    old = """
def public_api():
    return 42
"""
    new = """
def public_api():
    return 99
"""
    result = detect_export_changes(old, new, ".py")
    assert result is False  # same signature, different body


def test_detect_export_changes_js():
    """Detect export statement changes in JS."""
    old = "export function handler() {}\nexport const VERSION = 1;"
    new = "export function handler(req) {}\nexport const VERSION = 2;\nexport function newFn() {}"
    result = detect_export_changes(old, new, ".js")
    assert result is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd plugins/taskmaster && python -m pytest tests/test_blast_radius.py::test_detect_export_changes_python -v`
Expected: FAIL — `ImportError: cannot import name 'detect_export_changes'`

- [ ] **Step 3: Write implementation**

```python
# Add to blast_radius.py

# ── Export Change Detection ─────────────────────────────────

# Python: extract function/class signatures (public = no leading underscore)
_PY_EXPORT_RE = re.compile(r"^(def\s+[a-zA-Z]\w*\s*\([^)]*\)|class\s+[a-zA-Z]\w*(?:\([^)]*\))?)\s*:", re.MULTILINE)

# JS/TS: extract export declarations
_JS_EXPORT_RE = re.compile(r"^export\s+((?:default\s+)?(?:function|class|const|let|var|type|interface)\s+\w+[^{;]*)", re.MULTILINE)

# Go: extract public function signatures (capitalized)
_GO_EXPORT_RE = re.compile(r"^func\s+(?:\([^)]+\)\s+)?([A-Z]\w*)\s*\([^)]*\)", re.MULTILINE)


def _extract_exports(source: str, extension: str) -> set[str]:
    """Extract exported symbol signatures from source."""
    if extension == ".py":
        return {m.group(1) for m in _PY_EXPORT_RE.finditer(source)}
    elif extension in (".js", ".ts", ".tsx", ".jsx", ".mjs"):
        return {m.group(1).strip() for m in _JS_EXPORT_RE.finditer(source)}
    elif extension == ".go":
        return {m.group(0) for m in _GO_EXPORT_RE.finditer(source)}
    return set()


def detect_export_changes(old_source: str, new_source: str, extension: str) -> bool:
    """Detect whether exported API symbols changed between two versions of a file.

    Returns True if exports were added, removed, or had their signatures modified.
    """
    old_exports = _extract_exports(old_source, extension)
    new_exports = _extract_exports(new_source, extension)
    return old_exports != new_exports
```

- [ ] **Step 4: Run export detection tests**

Run: `cd plugins/taskmaster && python -m pytest tests/test_blast_radius.py -k "detect_export" -v`
Expected: 3 tests PASS

- [ ] **Step 5: Write git-based export detection helper and test**

```python
# Add to tests/test_blast_radius.py
from blast_radius import has_export_changes


def test_has_export_changes_calls_git(tmp_path):
    """Delegates to git show for old version, reads file for new version."""
    (tmp_path / "api.py").write_text("def handler(req):\n    pass\n")

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "def handler():\n    pass\n"

    with patch("blast_radius.subprocess.run", return_value=mock_result):
        result = has_export_changes("api.py", "main", tmp_path)

    assert result is True  # signature changed (added req param)
```

```python
# Add to blast_radius.py


def has_export_changes(file_rel: str, base_branch: str, project_root: Path) -> bool:
    """Check if a file's exports changed compared to the base branch."""
    ext = Path(file_rel).suffix
    if ext not in _PARSER_MAP:
        return False  # can't analyze unsupported files, assume no change

    # Get old version from base branch
    try:
        result = subprocess.run(
            ["git", "show", f"{base_branch}:{file_rel}"],
            capture_output=True, text=True, cwd=str(project_root), timeout=10,
        )
        if result.returncode != 0:
            return True  # new file — all exports are new
        old_source = result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

    # Get new version from disk
    filepath = project_root / file_rel
    if not filepath.exists():
        return True  # file deleted — exports removed
    try:
        new_source = filepath.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False

    return detect_export_changes(old_source, new_source, ext)
```

- [ ] **Step 6: Run all export tests**

Run: `cd plugins/taskmaster && python -m pytest tests/test_blast_radius.py -k "export" -v`
Expected: 4 tests PASS

- [ ] **Step 7: Commit**

```bash
git add plugins/taskmaster/blast_radius.py plugins/taskmaster/tests/test_blast_radius.py
git commit -m "feat(blast-radius): add export change detection"
```

---

### Task 6: Adaptive Depth Heuristic

**Files:**
- Modify: `plugins/taskmaster/blast_radius.py`
- Modify: `plugins/taskmaster/tests/test_blast_radius.py`

- [ ] **Step 1: Write tests for depth heuristic**

```python
# Add to tests/test_blast_radius.py
from blast_radius import compute_blast_depth


def test_depth_leaf_file_low_fanout():
    """Leaf file with low fan-out gets shallow depth."""
    depth = compute_blast_depth(
        file_rel="plugins/oauth/handler.py",
        fan_out=1,
        has_export_change=False,
        priority="P3",
        config=BlastRadiusConfig(),
        depth_override=None,
    )
    assert depth <= 1


def test_depth_core_file_high_fanout():
    """Core file with high fan-out gets deep depth."""
    depth = compute_blast_depth(
        file_rel="lib/core/base.py",
        fan_out=15,
        has_export_change=True,
        priority="P0",
        config=BlastRadiusConfig(),
        depth_override=None,
    )
    assert depth == 2


def test_depth_shared_dir_explicit():
    """Explicit shared_dirs in config are treated as deep."""
    config = BlastRadiusConfig(shared_dirs=["src/common/"])
    depth = compute_blast_depth(
        file_rel="src/common/utils.py",
        fan_out=2,
        has_export_change=False,
        priority="P3",
        config=config,
        depth_override=None,
    )
    assert depth >= 1  # shared dir bumps it


def test_depth_manual_override():
    """Manual override wins unconditionally."""
    depth = compute_blast_depth(
        file_rel="plugins/leaf/thing.py",
        fan_out=0,
        has_export_change=False,
        priority="P3",
        config=BlastRadiusConfig(),
        depth_override="deep",
    )
    assert depth == 2


def test_depth_manual_override_shallow():
    depth = compute_blast_depth(
        file_rel="lib/core/base.py",
        fan_out=50,
        has_export_change=True,
        priority="P0",
        config=BlastRadiusConfig(),
        depth_override="shallow",
    )
    assert depth <= 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd plugins/taskmaster && python -m pytest tests/test_blast_radius.py::test_depth_leaf_file_low_fanout -v`
Expected: FAIL — `ImportError: cannot import name 'compute_blast_depth'`

- [ ] **Step 3: Write implementation**

```python
# Add to blast_radius.py

# ── Adaptive Depth Heuristic ────────────────────────────────

# Directories that heuristically indicate shared/core code
_SHARED_DIR_PATTERNS = {"lib", "core", "utils", "shared", "common", "internal", "pkg"}


def _is_shared_dir(file_rel: str, config: BlastRadiusConfig) -> bool:
    """Check if a file is in a shared/core directory."""
    parts = Path(file_rel).parts
    # Check explicit shared_dirs from config
    for sd in config.shared_dirs:
        if file_rel.startswith(sd):
            return True
    # Check heuristic patterns
    return any(p.lower() in _SHARED_DIR_PATTERNS for p in parts[:-1])


def _is_leaf_dir(file_rel: str) -> bool:
    """Check if a file is in a leaf directory (plugins, components, etc.)."""
    parts = Path(file_rel).parts
    leaf_patterns = {"plugins", "components", "pages", "views", "handlers", "commands"}
    return any(p.lower() in leaf_patterns for p in parts[:-1])


def compute_blast_depth(
    file_rel: str,
    fan_out: int,
    has_export_change: bool,
    priority: str,
    config: BlastRadiusConfig,
    depth_override: str | None,
) -> int:
    """Compute how many hops to trace for a changed file.

    Each signal votes: 0 (shallow), 1 (normal), 2 (deep).
    Result is the maximum vote. Manual override wins unconditionally.
    """
    # Manual override
    if depth_override == "deep":
        return 2
    if depth_override == "shallow":
        return 1

    votes: list[int] = []

    # File location signal
    if _is_shared_dir(file_rel, config):
        votes.append(2)
    elif _is_leaf_dir(file_rel):
        votes.append(0)
    else:
        votes.append(1)

    # Fan-out signal
    if fan_out >= 11:
        votes.append(2)
    elif fan_out >= 4:
        votes.append(1)
    else:
        votes.append(0)

    # Export change signal
    if has_export_change:
        votes.append(2)
    else:
        votes.append(0)

    # Priority signal
    if priority in ("P0", "P1"):
        votes.append(2)
    elif priority == "P2":
        votes.append(1)
    else:
        votes.append(0)

    return max(votes) if votes else 1
```

- [ ] **Step 4: Run depth heuristic tests**

Run: `cd plugins/taskmaster && python -m pytest tests/test_blast_radius.py -k "depth" -v`
Expected: 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/blast_radius.py plugins/taskmaster/tests/test_blast_radius.py
git commit -m "feat(blast-radius): add adaptive depth heuristic"
```

---

### Task 7: Anchor Cross-Referencing

**Files:**
- Modify: `plugins/taskmaster/blast_radius.py`
- Modify: `plugins/taskmaster/tests/test_blast_radius.py`

- [ ] **Step 1: Write tests for anchor matching**

```python
# Add to tests/test_blast_radius.py
from blast_radius import find_overlapping_tasks


def test_find_overlapping_tasks_basic():
    """Find tasks whose anchors overlap with affected paths."""
    all_tasks = [
        {"id": "AUTH-005", "status": "in-progress", "title": "Current task",
         "anchors": ["src/auth/**"]},
        {"id": "AUTH-007", "status": "in-progress", "title": "Refresh tokens",
         "anchors": ["src/auth/middleware.py", "src/auth/session.py"]},
        {"id": "SESS-002", "status": "todo", "title": "Session timeout",
         "anchors": ["src/auth/session.py"]},
        {"id": "UI-001", "status": "in-progress", "title": "Dashboard",
         "anchors": ["src/dashboard/**"]},
    ]
    affected_paths = ["src/auth/middleware.py", "src/auth/session.py", "src/auth/types.py"]

    overlaps = find_overlapping_tasks(
        affected_paths=affected_paths,
        all_tasks=all_tasks,
        exclude_task_id="AUTH-005",
    )

    ids = {o["task_id"] for o in overlaps}
    assert "AUTH-007" in ids
    assert "SESS-002" in ids
    assert "AUTH-005" not in ids  # excluded (self)
    assert "UI-001" not in ids  # different area


def test_find_overlapping_tasks_glob_matching():
    """Glob anchors match against file paths."""
    all_tasks = [
        {"id": "AUTH-007", "status": "in-progress", "title": "Auth work",
         "anchors": ["src/auth/**"]},
    ]
    affected_paths = ["src/auth/deep/nested/file.py"]

    overlaps = find_overlapping_tasks(
        affected_paths=affected_paths,
        all_tasks=all_tasks,
        exclude_task_id="OTHER-001",
    )

    assert len(overlaps) == 1
    assert overlaps[0]["task_id"] == "AUTH-007"


def test_find_overlapping_tasks_no_anchors():
    """Tasks without anchors are skipped."""
    all_tasks = [
        {"id": "AUTH-007", "status": "in-progress", "title": "No anchors"},
    ]
    affected_paths = ["src/auth/middleware.py"]

    overlaps = find_overlapping_tasks(
        affected_paths=affected_paths,
        all_tasks=all_tasks,
        exclude_task_id="OTHER",
    )

    assert len(overlaps) == 0


def test_find_overlapping_tasks_skips_archived():
    """Archived tasks are ignored."""
    all_tasks = [
        {"id": "OLD-001", "status": "archived", "title": "Old task",
         "anchors": ["src/auth/**"]},
    ]
    affected_paths = ["src/auth/middleware.py"]

    overlaps = find_overlapping_tasks(
        affected_paths=affected_paths,
        all_tasks=all_tasks,
        exclude_task_id="OTHER",
    )

    assert len(overlaps) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd plugins/taskmaster && python -m pytest tests/test_blast_radius.py::test_find_overlapping_tasks_basic -v`
Expected: FAIL — `ImportError: cannot import name 'find_overlapping_tasks'`

- [ ] **Step 3: Write implementation**

```python
# Add to blast_radius.py
from fnmatch import fnmatch

# ── Anchor Cross-Referencing ────────────────────────────────


def _anchor_matches_path(anchor: str, file_path: str) -> bool:
    """Check if an anchor pattern matches a file path.

    Supports glob patterns (fnmatch) and exact prefix matching.
    URL anchors (http/localhost) are skipped.
    """
    if anchor.startswith(("http", "localhost")):
        return False
    # Try glob match
    if fnmatch(file_path, anchor):
        return True
    # Try prefix match (for directory-style anchors like "src/auth/")
    if file_path.startswith(anchor.rstrip("*").rstrip("/")):
        return True
    return False


def find_overlapping_tasks(
    affected_paths: list[str],
    all_tasks: list[dict],
    exclude_task_id: str,
) -> list[dict]:
    """Find tasks whose anchors overlap with the affected file paths.

    Returns list of dicts with keys: task_id, title, status, shared_paths.
    Skips archived tasks and the excluded task (typically the current task).
    """
    overlaps: list[dict] = []

    for task in all_tasks:
        if task["id"] == exclude_task_id:
            continue
        if task.get("status") == "archived":
            continue

        anchors = task.get("anchors", [])
        if not anchors:
            continue

        shared: list[str] = []
        for path in affected_paths:
            for anchor in anchors:
                if _anchor_matches_path(anchor, path):
                    shared.append(path)
                    break  # one anchor match per path is enough

        if shared:
            overlaps.append({
                "task_id": task["id"],
                "title": task.get("title", ""),
                "status": task.get("status", ""),
                "shared_paths": shared,
            })

    return overlaps
```

- [ ] **Step 4: Run anchor tests**

Run: `cd plugins/taskmaster && python -m pytest tests/test_blast_radius.py -k "overlapping" -v`
Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/blast_radius.py plugins/taskmaster/tests/test_blast_radius.py
git commit -m "feat(blast-radius): add anchor-based overlap detection"
```

---

### Task 8: Fan-Out Computation Helper

**Files:**
- Modify: `plugins/taskmaster/blast_radius.py`
- Modify: `plugins/taskmaster/tests/test_blast_radius.py`

- [ ] **Step 1: Write test for compute_fan_out_scores**

```python
# Add to tests/test_blast_radius.py
from blast_radius import compute_fan_out_scores


def test_compute_fan_out_scores(tmp_path):
    """Count how many files import each changed file."""
    (tmp_path / "core.py").write_text("# core")
    (tmp_path / "utils.py").write_text("# utils")
    (tmp_path / "a.py").write_text("from core import x\n")
    (tmp_path / "b.py").write_text("from core import y\nfrom utils import z\n")
    (tmp_path / "c.py").write_text("from core import w\n")

    config = BlastRadiusConfig(max_file_scan=100)
    scores = compute_fan_out_scores(["core.py", "utils.py"], tmp_path, config)

    assert scores["core.py"] == 3  # a.py, b.py, c.py
    assert scores["utils.py"] == 1  # b.py only
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd plugins/taskmaster && python -m pytest tests/test_blast_radius.py::test_compute_fan_out_scores -v`
Expected: FAIL — `ImportError: cannot import name 'compute_fan_out_scores'`

- [ ] **Step 3: Write implementation**

```python
# Add to blast_radius.py


def compute_fan_out_scores(
    changed_files: list[str],
    project_root: Path,
    config: BlastRadiusConfig,
    sub_repo: str | None = None,
) -> dict[str, int]:
    """Count direct importers for each changed file. Returns {file: count}."""
    scores: dict[str, int] = {}
    for f in changed_files:
        importers = find_importers(f, project_root, config, sub_repo)
        scores[f] = len(importers)
    return scores
```

- [ ] **Step 4: Run test**

Run: `cd plugins/taskmaster && python -m pytest tests/test_blast_radius.py::test_compute_fan_out_scores -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/blast_radius.py plugins/taskmaster/tests/test_blast_radius.py
git commit -m "feat(blast-radius): add fan-out score computation"
```

---

### Task 9: Predictive Analysis (Top-Level Function)

**Files:**
- Modify: `plugins/taskmaster/blast_radius.py`
- Modify: `plugins/taskmaster/tests/test_blast_radius.py`

- [ ] **Step 1: Write test for analyze_predictive**

```python
# Add to tests/test_blast_radius.py
from blast_radius import analyze_predictive


def test_analyze_predictive_with_overlap():
    task = {
        "id": "AUTH-005",
        "title": "Add OAuth2 PKCE flow",
        "notes": "Implement PKCE for public clients",
        "anchors": ["src/auth/middleware.py", "src/auth/session.py"],
    }
    all_tasks = [
        {"id": "AUTH-005", "status": "in-progress", "title": "Add OAuth2 PKCE flow",
         "anchors": ["src/auth/middleware.py", "src/auth/session.py"]},
        {"id": "AUTH-007", "status": "in-progress", "title": "Refresh token rotation",
         "anchors": ["src/auth/middleware.py"]},
        {"id": "UI-001", "status": "todo", "title": "Dashboard",
         "anchors": ["src/dashboard/**"]},
    ]

    result = analyze_predictive(task, all_tasks)

    assert result["task_summary"] == "Add OAuth2 PKCE flow"
    assert "src/auth/middleware.py" in result["anchored_areas"]
    assert len(result["overlapping_tasks"]) == 1
    assert result["overlapping_tasks"][0]["task_id"] == "AUTH-007"


def test_analyze_predictive_no_anchors():
    task = {"id": "X-001", "title": "No anchors task"}
    result = analyze_predictive(task, [])
    assert result["anchored_areas"] == []
    assert result["overlapping_tasks"] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd plugins/taskmaster && python -m pytest tests/test_blast_radius.py::test_analyze_predictive_with_overlap -v`
Expected: FAIL — `ImportError: cannot import name 'analyze_predictive'`

- [ ] **Step 3: Write implementation**

```python
# Add to blast_radius.py

# ── Top-Level Analysis Functions ────────────────────────────


def analyze_predictive(task: dict, all_tasks: list[dict]) -> dict:
    """Predictive blast radius analysis — metadata only, no code tracing.

    Called at pick-task time. Returns structured data for LLM interpretation.
    """
    anchors = task.get("anchors", [])
    file_anchors = [a for a in anchors if not a.startswith(("http", "localhost"))]

    overlapping = find_overlapping_tasks(
        affected_paths=file_anchors,
        all_tasks=all_tasks,
        exclude_task_id=task["id"],
    ) if file_anchors else []

    return {
        "task_summary": task.get("title", ""),
        "anchored_areas": file_anchors,
        "overlapping_tasks": overlapping,
    }
```

- [ ] **Step 4: Run tests**

Run: `cd plugins/taskmaster && python -m pytest tests/test_blast_radius.py -k "analyze_predictive" -v`
Expected: 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/blast_radius.py plugins/taskmaster/tests/test_blast_radius.py
git commit -m "feat(blast-radius): add predictive analysis function"
```

---

### Task 10: Evidence Analysis (Top-Level Function)

**Files:**
- Modify: `plugins/taskmaster/blast_radius.py`
- Modify: `plugins/taskmaster/tests/test_blast_radius.py`

- [ ] **Step 1: Write test for analyze_evidence**

```python
# Add to tests/test_blast_radius.py
from blast_radius import analyze_evidence


def test_analyze_evidence_full(tmp_path):
    """Full evidence analysis with real files on disk."""
    # Set up mini project
    (tmp_path / "core.py").write_text("def public_api():\n    return 42\n")
    (tmp_path / "api.py").write_text("from core import public_api\n")
    (tmp_path / "unrelated.py").write_text("import os\n")

    task = {
        "id": "CORE-001",
        "title": "Update core API",
        "priority": "P1",
        "branch": "feature/core-update",
        "anchors": ["core.py"],
    }
    all_tasks = [
        {"id": "CORE-001", "status": "in-progress", "title": "Update core API",
         "anchors": ["core.py"]},
        {"id": "API-002", "status": "in-progress", "title": "API routes",
         "anchors": ["api.py"]},
    ]

    # Mock git diff to return core.py as changed
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "core.py\n"

    # Mock git show for export detection (old version had different signature)
    def mock_git(*args, **kwargs):
        cmd = args[0] if args else kwargs.get("args", [])
        if "diff" in cmd:
            r = MagicMock()
            r.returncode = 0
            r.stdout = "core.py\n"
            return r
        elif "show" in cmd:
            r = MagicMock()
            r.returncode = 0
            r.stdout = "def public_api(old_sig):\n    return 1\n"
            return r
        elif "merge-base" in cmd:
            r = MagicMock()
            r.returncode = 0
            r.stdout = "abc123\n"
            return r
        r = MagicMock()
        r.returncode = 1
        return r

    config = BlastRadiusConfig(max_file_scan=100)

    with patch("blast_radius.subprocess.run", side_effect=mock_git):
        result = analyze_evidence(
            task=task,
            all_tasks=all_tasks,
            project_root=tmp_path,
            config=config,
            base_branch="main",
        )

    assert "core.py" in result["changed_files"]
    assert result["fan_out_scores"]["core.py"] >= 1
    assert result["summary_stats"]["files_changed"] == 1
    # API-002 overlaps because it anchors to api.py which imports core.py
    # (the overlap is anchor-based against affected paths from dependency graph)


def test_analyze_evidence_no_changes(tmp_path):
    """When no files changed, return empty result."""
    task = {
        "id": "X-001",
        "title": "Nothing",
        "priority": "P3",
        "branch": "feature/x",
    }

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = ""

    config = BlastRadiusConfig()

    with patch("blast_radius.subprocess.run", return_value=mock_result):
        result = analyze_evidence(
            task=task,
            all_tasks=[],
            project_root=tmp_path,
            config=config,
            base_branch="main",
        )

    assert result["changed_files"] == []
    assert result["summary_stats"]["files_changed"] == 0
    assert result["truncated"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd plugins/taskmaster && python -m pytest tests/test_blast_radius.py::test_analyze_evidence_no_changes -v`
Expected: FAIL — `ImportError: cannot import name 'analyze_evidence'`

- [ ] **Step 3: Write implementation**

```python
# Add to blast_radius.py


def analyze_evidence(
    task: dict,
    all_tasks: list[dict],
    project_root: Path,
    config: BlastRadiusConfig,
    base_branch: str = "main",
    depth_override: str | None = None,
) -> dict:
    """Evidence-based blast radius analysis — code tracing from actual diff.

    Called at review-gate time. Returns structured data for LLM interpretation.
    """
    branch = task.get("branch", "")
    sub_repo = task.get("sub_repo")
    priority = task.get("priority", "P2")
    cwd = project_root / sub_repo if sub_repo else project_root

    # Task-level override takes precedence, then caller override
    task_depth_override = task.get("blast_radius_depth") or depth_override

    # 1. Get changed files
    changed_files = get_changed_files(branch, base_branch, cwd) if branch else []

    if not changed_files:
        return {
            "changed_files": [],
            "dependency_graph": {},
            "fan_out_scores": {},
            "depth_used": {},
            "overlapping_tasks": [],
            "summary_stats": {"files_changed": 0, "total_dependents": 0, "overlap_count": 0},
            "truncated": False,
        }

    # 2. Compute fan-out scores
    fan_out_scores = compute_fan_out_scores(changed_files, project_root, config, sub_repo)

    # 3. Detect export changes and compute depth per file
    depths: dict[str, int] = {}
    for f in changed_files:
        export_changed = has_export_changes(f, base_branch, cwd)
        depths[f] = compute_blast_depth(
            file_rel=f,
            fan_out=fan_out_scores.get(f, 0),
            has_export_change=export_changed,
            priority=priority,
            config=config,
            depth_override=task_depth_override,
        )

    # 4. Trace dependency graph
    graph = trace_dependency_graph(changed_files, depths, project_root, config, sub_repo)

    # 5. Collect all affected paths (changed files + all dependents)
    all_affected: set[str] = set(changed_files)
    for deps in graph.values():
        all_affected.update(deps)

    # 6. Find overlapping tasks
    overlapping = find_overlapping_tasks(
        affected_paths=list(all_affected),
        all_tasks=all_tasks,
        exclude_task_id=task["id"],
    )

    # 7. Compute summary stats
    total_dependents = sum(len(deps) for deps in graph.values())

    # Check truncation (any find_importers call may have truncated)
    truncated = False
    for f in changed_files:
        _, was_truncated = find_importers_with_limit(f, project_root, config, sub_repo)
        if was_truncated:
            truncated = True
            break

    return {
        "changed_files": changed_files,
        "dependency_graph": {k: v for k, v in graph.items()},
        "fan_out_scores": fan_out_scores,
        "depth_used": depths,
        "overlapping_tasks": overlapping,
        "summary_stats": {
            "files_changed": len(changed_files),
            "total_dependents": total_dependents,
            "overlap_count": len(overlapping),
        },
        "truncated": truncated,
    }
```

- [ ] **Step 4: Run evidence analysis tests**

Run: `cd plugins/taskmaster && python -m pytest tests/test_blast_radius.py -k "analyze_evidence" -v`
Expected: 2 tests PASS

- [ ] **Step 5: Run full test suite**

Run: `cd plugins/taskmaster && python -m pytest tests/test_blast_radius.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add plugins/taskmaster/blast_radius.py plugins/taskmaster/tests/test_blast_radius.py
git commit -m "feat(blast-radius): add evidence analysis with full code tracing pipeline"
```

---

### Task 11: MCP Tool Registration and Schema Extension

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py:1688` — add `blast_radius_depth` to ALLOWED_FIELDS
- Modify: `plugins/taskmaster/backlog_server.py` — add `backlog_blast_radius` tool (after `backlog_snapshot` around line 2497)
- Modify: `plugins/taskmaster/backlog_server.py:1775-1779` — handle `blast_radius_depth` in update_task

- [ ] **Step 1: Add blast_radius_depth to ALLOWED_FIELDS**

In `backlog_server.py` at line 1688, add `blast_radius_depth` to the set:

```python
ALLOWED_FIELDS = {"title", "status", "priority", "notes", "branch", "worktree", "blockers", "docs", "depends_on", "sub_repo", "stage", "estimate", "locked_by", "review_instructions", "phase", "anchors", "blast_radius_depth"}
```

- [ ] **Step 2: Add blast_radius_depth handling in backlog_update_task**

In `backlog_server.py`, after the `anchors` handling block (around line 1779), add handling for `blast_radius_depth`:

Find the section that handles field updates (the `elif` chain in `backlog_update_task`). After the anchors block, add:

```python
elif field == "blast_radius_depth":
    if value == "" or value.lower() == "none":
        task.pop("blast_radius_depth", None)
    elif value in ("shallow", "deep"):
        task["blast_radius_depth"] = value
    else:
        return f"Error: `blast_radius_depth` must be 'shallow', 'deep', or '' to clear. Got: `{value}`"
```

- [ ] **Step 3: Add the import at the top of backlog_server.py**

After the existing imports (around line 21-22), add:

```python
from blast_radius import (
    BlastRadiusConfig,
    load_config,
    analyze_predictive,
    analyze_evidence,
)
```

- [ ] **Step 4: Add the backlog_blast_radius MCP tool**

After the `backlog_snapshot` tool (around line 2550), add a new section:

```python
# ── Blast Radius Analysis ───────────────────────────────────


@mcp.tool()
def backlog_blast_radius(task_id: str, mode: str = "predictive", depth_override: str = "") -> str:
    """Analyze the blast radius (impact footprint) of a task.

    Two modes:
    - predictive: metadata-only analysis for pick-task time. Fast, no code tracing.
    - evidence: code-level impact analysis for review-gate time. Traces imports, builds dependency graph.

    Args:
        task_id: The task ID to analyze (e.g., "auth-005")
        mode: Analysis mode — "predictive" or "evidence"
        depth_override: Optional depth override — "shallow" (0-1 hop) or "deep" (2 hops). Overrides the adaptive heuristic.
    """
    if mode not in ("predictive", "evidence"):
        return f"Error: mode must be 'predictive' or 'evidence', got '{mode}'"

    data = _load()
    result = _find_task(data, task_id)
    if not result:
        return f"Error: task `{task_id}` not found"
    task, epic = result

    # Collect all tasks for overlap detection
    all_tasks: list[dict] = []
    for e in data.get("epics", []):
        all_tasks.extend(e.get("tasks", []))

    config = load_config(data.get("meta", {}))
    override = depth_override if depth_override in ("shallow", "deep") else None

    if mode == "predictive":
        analysis = analyze_predictive(task, all_tasks)
        return _format_predictive(analysis, task.get("priority", "P2"))
    else:
        # Resolve project root for code analysis
        sub_repo = task.get("sub_repo")
        worktree = task.get("worktree")
        if worktree:
            project_root = Path(worktree).resolve() if Path(worktree).is_absolute() else (ROOT / worktree).resolve()
        else:
            project_root = ROOT

        analysis = analyze_evidence(
            task=task,
            all_tasks=all_tasks,
            project_root=project_root,
            config=config,
            base_branch="main",
            depth_override=override,
        )
        return _format_evidence(analysis)


def _format_predictive(analysis: dict, priority: str) -> str:
    """Format predictive analysis results as markdown."""
    lines: list[str] = []

    anchored = analysis["anchored_areas"]
    overlaps = analysis["overlapping_tasks"]

    if priority in ("P0", "P1"):
        # Full structured block
        lines.append("── Predicted Blast Radius ──────────────────────")
        if anchored:
            lines.append("**Anchored areas:**")
            for a in anchored:
                lines.append(f"  - `{a}`")
        else:
            lines.append("**Anchored areas:** None set")

        if overlaps:
            lines.append("\n**Related active work:**")
            for o in overlaps:
                paths = ", ".join(f"`{p}`" for p in o["shared_paths"][:3])
                lines.append(f"  - `{o['task_id']}` \"{o['title']}\" ({o['status']}) — shares {paths}")
        else:
            lines.append("\n**Related active work:** None detected")

        lines.append("────────────────────────────────────────────────")
    else:
        # Single line for P2/P3
        if overlaps:
            overlap_strs = [f"{o['task_id']} ({o['status']})" for o in overlaps[:3]]
            lines.append(f"Blast radius: Overlaps with {', '.join(overlap_strs)}")
        else:
            lines.append("Blast radius: No overlap with active tasks.")

    return "\n".join(lines)


def _format_evidence(analysis: dict) -> str:
    """Format evidence analysis results as markdown."""
    lines: list[str] = []
    stats = analysis["summary_stats"]

    # Summary line for gate table
    parts = []
    if stats["files_changed"]:
        parts.append(f"{stats['total_dependents']} dependents")
    if stats["overlap_count"]:
        parts.append(f"{stats['overlap_count']} overlapping task{'s' if stats['overlap_count'] != 1 else ''}")
    summary = ", ".join(parts) if parts else "no impact detected"
    lines.append(f"**Gate 4 summary:** {summary}")

    if not analysis["changed_files"]:
        lines.append("\nNo changed files detected — nothing to analyze.")
        return "\n".join(lines)

    # Detailed report
    lines.append("\n── Blast Radius Report ─────────────────────────")

    # Changed files with fan-out
    lines.append(f"**Changed files ({stats['files_changed']}):**")
    for f in analysis["changed_files"]:
        fan = analysis["fan_out_scores"].get(f, 0)
        depth = analysis["depth_used"].get(f, 0)
        depth_label = {0: "leaf, no trace", 1: "1 hop", 2: "2 hops"}.get(depth, f"{depth} hops")
        lines.append(f"  `{f}` — {fan} dependents ({depth_label})")

    # Dependency graph (affected modules)
    if analysis["dependency_graph"]:
        lines.append("\n**Affected modules:**")
        # Group dependents by directory
        dir_counts: dict[str, int] = {}
        for deps in analysis["dependency_graph"].values():
            for dep in deps:
                parent = str(Path(dep).parent)
                dir_counts[parent] = dir_counts.get(parent, 0) + 1
        for d, count in sorted(dir_counts.items(), key=lambda x: -x[1]):
            lines.append(f"  - `{d}/` ({count} file{'s' if count != 1 else ''})")

    # Overlapping tasks
    overlaps = analysis["overlapping_tasks"]
    if overlaps:
        lines.append("\n**Overlapping tasks:**")
        for o in overlaps:
            is_in_progress = o["status"] == "in-progress"
            marker = "!!" if is_in_progress else "-"
            paths = ", ".join(f"`{p}`" for p in o["shared_paths"][:5])
            lines.append(f"  {marker} `{o['task_id']}` \"{o['title']}\" ({o['status']})")
            lines.append(f"    Shared paths: {paths}")
            if is_in_progress:
                lines.append(f"    **Risk: Both tasks modifying the same files concurrently**")

    if analysis["truncated"]:
        lines.append("\n*Note: File scan was truncated — results may be incomplete.*")

    lines.append("────────────────────────────────────────────────")

    return "\n".join(lines)
```

- [ ] **Step 5: Run the backlog server to verify it starts**

Run: `cd plugins/taskmaster && python -c "from blast_radius import analyze_predictive, analyze_evidence; print('imports ok')"`
Expected: `imports ok`

- [ ] **Step 6: Commit**

```bash
git add plugins/taskmaster/backlog_server.py
git commit -m "feat(blast-radius): add backlog_blast_radius MCP tool with schema extension"
```

---

### Task 12: Update Pick-Task Skill

**Files:**
- Modify: `plugins/taskmaster/skills/pick-task/SKILL.md:30-33`

- [ ] **Step 1: Update step 4 to include blast radius**

Replace the current step 4 in `pick-task/SKILL.md` (lines 30-33) with an expanded version that includes blast radius analysis after displaying anchors:

```markdown
4. **Show anchors and predicted blast radius:**
   - If the task has `anchors`, display them prominently:
     "This task is anchored to `src/auth/**`. Expected at `localhost:3000/api/auth`."
   - Remind: "If you find yourself editing files outside these anchors, double-check you're working on the right target."
   - Call `backlog_blast_radius(task_id, mode="predictive")` to get predicted impact.
   - Display the result. For P0/P1 tasks, show the full structured block (anchored areas, related active work, considerations). For P2/P3 tasks, show the single-line summary.
   - If overlapping in-progress tasks are found, highlight them: "Heads up — `{task_id}` is actively being worked on in the same area. Coordinate to avoid conflicts."
```

- [ ] **Step 2: Verify the skill file reads correctly**

Read `plugins/taskmaster/skills/pick-task/SKILL.md` and confirm step 4 looks right and doesn't break the numbered flow.

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/skills/pick-task/SKILL.md
git commit -m "feat(blast-radius): add predictive blast radius to pick-task skill"
```

---

### Task 13: Update Review-Gate Skill

**Files:**
- Modify: `plugins/taskmaster/skills/review-gate/SKILL.md:38-87`

- [ ] **Step 1: Add Gate 4 between current step 4 and step 5**

Insert a new step after Gate 3 (Verification) and before the results presentation. The existing steps 5-7 become steps 6-8.

After step 4 (Gate 3: Verification), insert:

```markdown
5. **Gate 4: Blast Radius (always advisory)**

   Analyze the impact footprint of the task's changes. This gate never blocks — it surfaces what you might have missed.

   - Call `backlog_blast_radius(task_id, mode="evidence")` to get code-level impact analysis.
   - The tool returns: changed files with fan-out scores, dependency graph, depth used per file, overlapping tasks, and summary stats.
   - **Interpret the results** — this is where you add judgment:
     - Look at the dependency graph and identify which modules/subsystems are affected.
     - If overlapping in-progress tasks are found, assess the conflict risk.
     - Consider whether any existing features should be updated given these changes.
     - Draft 2-4 specific "Suggested follow-ups" based on the data.

   **Verdict logic (advisory only):**
   - **PASS** — low fan-out (< 5 total dependents), no overlapping active tasks, changes well-contained.
   - **WARN** — moderate fan-out (5-20 dependents), or overlapping tasks found, or changes touch shared modules.
   - **WARN (loud)** — another in-progress task is modifying the same files. Call this out explicitly: "⚠ `{task_id}` is in-progress and shares files with this task — verify no conflicts."
```

- [ ] **Step 2: Update step 5 (now step 6) results presentation**

Update the results table to include Gate 4:

```markdown
6. **Present Results — lead with the verdict:**

   Start with the overall outcome: "All gates passed — ready for your testing" or "Review gate found issues — see details below."

   Then show the breakdown:
   ```
   Gate 1 — Spec/Plan:      PASS / WARN / SKIP
   Gate 2 — Code Review:     PASS / FAIL (N issues)
   Gate 3 — Tests:           PASS / FAIL / SKIP
   Gate 3 — Build:           PASS / FAIL / SKIP
   Gate 4 — Blast Radius:    PASS / WARN (advisory)
   ```

   **Blocking rules:**
   - Critical code review findings block unconditionally.
   - Important findings require user acknowledgment before proceeding.
   - Minor findings, WARN/SKIP results, and Gate 4 results never block.

   If Gate 4 returned WARN, append the full Blast Radius Report (changed files, affected modules, overlapping tasks, suggested follow-ups) below the gate table.

   If gates failed, offer: "Stay in-progress and address issues" or "Move to in-review anyway (you'll need to justify the critical findings)."
```

- [ ] **Step 3: Renumber remaining steps**

Update the remaining steps:
- Old step 6 "Add review instructions" becomes step 7
- Old step 7 "Transition to in-review" becomes step 8

- [ ] **Step 4: Verify the skill file reads correctly**

Read `plugins/taskmaster/skills/review-gate/SKILL.md` and confirm all steps flow correctly and Gate 4 is properly integrated.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/skills/review-gate/SKILL.md
git commit -m "feat(blast-radius): add Gate 4 blast radius to review-gate skill"
```

---

### Task 14: Update TASKMASTER.md Schema Documentation

**Files:**
- Modify: `plugins/taskmaster/docs/TASKMASTER.md` — add `blast_radius_depth` field to task schema docs
- Modify: `plugins/taskmaster/docs/TASKMASTER.md` — add `blast_radius` meta config docs

- [ ] **Step 1: Find the task field documentation section**

Read `plugins/taskmaster/docs/TASKMASTER.md` and locate the task schema field list (around lines 288-310 based on exploration).

- [ ] **Step 2: Add blast_radius_depth to the field list**

Add after `anchors`:

```markdown
| `blast_radius_depth` | string | Optional depth override for blast radius analysis: `shallow` (0-1 hop) or `deep` (2 hops). Overrides the adaptive heuristic. |
```

- [ ] **Step 3: Find the meta configuration section**

Locate where `meta` block is documented in TASKMASTER.md.

- [ ] **Step 4: Add blast_radius meta config documentation**

Add a new subsection for blast radius configuration:

```markdown
### Blast Radius Configuration

Optional config under `meta.blast_radius`:

```yaml
meta:
  blast_radius:
    fan_out_threshold: 5    # avg fan-out above this = "shared" directory (default: 5)
    max_file_scan: 1000     # max files to scan for import tracing (default: 1000)
    shared_dirs: []         # explicit shared directories, supplements auto-detection
```

All keys are optional with sensible defaults. If the `blast_radius` key is absent, all defaults apply.
```

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/docs/TASKMASTER.md
git commit -m "docs(blast-radius): add schema and config documentation"
```

---

### Task 15: Integration Test and Final Verification

**Files:**
- Modify: `plugins/taskmaster/tests/test_blast_radius.py`

- [ ] **Step 1: Write an end-to-end integration test**

```python
# Add to tests/test_blast_radius.py

def test_end_to_end_predictive():
    """Full predictive flow: task with anchors, overlapping tasks."""
    task = {
        "id": "FEAT-001",
        "title": "Add user profile page",
        "priority": "P1",
        "notes": "Profile page with avatar, bio, settings",
        "anchors": ["src/user/profile.py", "src/user/avatar.py"],
    }
    all_tasks = [
        task,
        {"id": "FEAT-001", "status": "in-progress", "title": "Add user profile page",
         "anchors": ["src/user/profile.py", "src/user/avatar.py"]},
        {"id": "FEAT-002", "status": "in-progress", "title": "User settings",
         "anchors": ["src/user/settings.py", "src/user/profile.py"]},
        {"id": "FEAT-003", "status": "todo", "title": "Admin panel",
         "anchors": ["src/admin/**"]},
        {"id": "OLD-001", "status": "archived", "title": "Archived task",
         "anchors": ["src/user/**"]},
    ]

    result = analyze_predictive(task, all_tasks)

    assert result["task_summary"] == "Add user profile page"
    assert len(result["anchored_areas"]) == 2
    assert len(result["overlapping_tasks"]) == 1  # FEAT-002 only (self excluded, OLD archived, FEAT-003 different area)
    assert result["overlapping_tasks"][0]["task_id"] == "FEAT-002"


def test_end_to_end_evidence(tmp_path):
    """Full evidence flow: changed files → graph → overlaps."""
    # Mini project structure
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "auth.py").write_text("def check_token():\n    pass\n")
    (tmp_path / "api").mkdir()
    (tmp_path / "api" / "routes.py").write_text("from lib.auth import check_token\n")
    (tmp_path / "api" / "admin.py").write_text("from lib.auth import check_token\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_auth.py").write_text("from lib.auth import check_token\n")

    task = {
        "id": "SEC-001",
        "title": "Fix auth bypass",
        "priority": "P0",
        "branch": "fix/auth-bypass",
        "anchors": ["lib/auth.py"],
    }
    all_tasks = [
        {"id": "SEC-001", "status": "in-progress", "title": "Fix auth bypass",
         "anchors": ["lib/auth.py"]},
        {"id": "API-001", "status": "in-progress", "title": "API routes refactor",
         "anchors": ["api/**"]},
    ]

    def mock_git(*args, **kwargs):
        cmd = args[0]
        if "diff" in cmd and "--name-only" in cmd:
            r = MagicMock()
            r.returncode = 0
            r.stdout = "lib/auth.py\n"
            return r
        elif "show" in cmd:
            r = MagicMock()
            r.returncode = 0
            r.stdout = "def check_token(old):\n    pass\n"  # different signature
            return r
        r = MagicMock()
        r.returncode = 1
        return r

    config = BlastRadiusConfig(max_file_scan=100)

    with patch("blast_radius.subprocess.run", side_effect=mock_git):
        result = analyze_evidence(
            task=task,
            all_tasks=all_tasks,
            project_root=tmp_path,
            config=config,
            base_branch="main",
        )

    assert result["changed_files"] == ["lib/auth.py"]
    assert result["fan_out_scores"]["lib/auth.py"] >= 2  # routes.py, admin.py, test_auth.py
    assert result["depth_used"]["lib/auth.py"] == 2  # P0 + shared dir + export change → deep
    assert result["summary_stats"]["files_changed"] == 1
    assert result["summary_stats"]["total_dependents"] >= 2
    # API-001 should overlap because api/routes.py and api/admin.py are dependents
    # and API-001 anchors to "api/**"
    overlap_ids = {o["task_id"] for o in result["overlapping_tasks"]}
    assert "API-001" in overlap_ids
```

- [ ] **Step 2: Run full test suite**

Run: `cd plugins/taskmaster && python -m pytest tests/test_blast_radius.py -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/tests/test_blast_radius.py
git commit -m "test(blast-radius): add end-to-end integration tests"
```

- [ ] **Step 4: Run full test suite one more time to verify everything**

Run: `cd plugins/taskmaster && python -m pytest tests/test_blast_radius.py -v --tb=short`
Expected: All tests PASS, no warnings
