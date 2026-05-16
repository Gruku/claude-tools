# Plan C — Programmatic Linking — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the proliferation of one-directional linkage fields (`related_issues`, `related_lessons`, `depends_on`, `fixed_in_task`, `duplicate_of`, `supersedes`, `superseded_by`) with one typed `links: [{type, target}]` array per entity, kept symmetric by the server, with inline-reference auto-detection on save and a full MCP CRUD surface (`backlog_link_*`).

**Architecture:** Three layers. (1) **Data layer** in `plugins/taskmaster/taskmaster_v3.py` gains a `LINK_TYPES` registry, a `REVERSE_TYPE` map, link CRUD helpers operating on in-memory entity dicts, an inverse-sync engine that writes both sides via existing read/write helpers (`read_task_file`/`write_task_file`/`read_issue`/`write_issue`/`read_lesson`/`write_lesson`/`read_handover`/`write_handover`/`read_idea`/`write_idea` plus `load_v3`/`save_v3`), cycle detection over `depends_on`, and an inline-ref extractor that runs on every write. (2) **MCP layer** in `plugins/taskmaster/backlog_server.py` exposes `backlog_link_create`, `backlog_link_remove`, `backlog_link_query`, `backlog_link_validate`, `backlog_link_reconcile`, and updates the slim `_get` views to emit `links` grouped by type. (3) **Viewer layer** in `plugins/taskmaster/viewer/js/screens/*.js` reads the new `links` array and renders typed link pills. A one-shot migration script translates the old fields and runs reconcile. Old fields are kept readable for one release as a fallback.

**Tech Stack:** Python 3.11+, FastMCP, PyYAML, pytest, JavaScript (viewer).

**Spec:** `docs/superpowers/specs/2026-05-15-taskmaster-progressive-disclosure-design.md` §6 (subsections 6A–6G).

**Depends on:** Plan A optional. Plan C is architecturally independent — it can ship standalone. When both are present, Plan A's slim `_get` view incorporates the grouped `links` block defined here.

**Out of scope — §6E (computed/derived suggestions):** Spec §6E (surfacing commit→issue, file→lesson suggestions at end-session) is explicitly deferred from Plan C. Auto-detection in Plan C materializes only inline ID mentions already written by the user; it does not infer links from git history, file paths, or semantic similarity. §6E is a separate feature requiring confidence-tuning and its own spec.

---

## File Structure

**Modify:**

- `plugins/taskmaster/taskmaster_v3.py` — add `LINK_TYPES`, `REVERSE_TYPE`, `ENTITY_KIND_BY_PREFIX`, `LINK_TYPE_DOMAIN`, `INLINE_REF_RE`, helpers `entity_links()`, `set_entity_links()`, `add_link()`, `remove_link()`, `find_cycle()`, `extract_inline_refs()`, `auto_link_on_save()`, `sync_inverse()`, `read_entity_links_anywhere()`, `legacy_links_to_typed()`, `links_grouped_by_type()`.
- `plugins/taskmaster/backlog_server.py` — add `backlog_link_create`, `backlog_link_remove`, `backlog_link_query`, `backlog_link_validate`, `backlog_link_reconcile` MCP tools. Update `backlog_get_task` / `backlog_handover_get` / `backlog_issue_get` / `backlog_lesson_get` / `backlog_idea_get` to emit the grouped `links` block and accept `expand_links=true`. Hook `auto_link_on_save()` into every entity write path that ends in `write_task_file`/`write_issue`/`write_lesson`/`write_handover`/`write_idea` (and `save_v3` for task writes that route through it).
- `plugins/taskmaster/CHANGELOG.md` — v3.X entry covering schema change, migration, deprecation window.
- `plugins/taskmaster/viewer/js/screens/task-detail.js` — render `links` grouped by type.
- `plugins/taskmaster/viewer/js/screens/issue-detail.js` — render `links` grouped by type.
- `plugins/taskmaster/viewer/js/screens/lesson-detail.js` — render `links` grouped by type.
- `plugins/taskmaster/viewer/js/screens/issues.js` — read `links` for badge counts.
- `plugins/taskmaster/viewer/js/screens/ideas.js` — read `links` for badge counts.

**Depends on (from Plan A Task 0 — create if absent):**

- `plugins/__init__.py` — package marker
- `plugins/taskmaster/__init__.py` — package marker
- `plugins/taskmaster/tests/conftest.py` — `sys.path` shim so bare `import backlog_server` resolves in tests

**Create:**

- `plugins/taskmaster/tests/test_link_types.py`
- `plugins/taskmaster/tests/test_link_helpers.py`
- `plugins/taskmaster/tests/test_link_cycle_detection.py`
- `plugins/taskmaster/tests/test_link_inverse_sync.py`
- `plugins/taskmaster/tests/test_inline_ref_extraction.py`
- `plugins/taskmaster/tests/test_auto_link_on_save.py`
- `plugins/taskmaster/tests/test_backlog_link_create.py`
- `plugins/taskmaster/tests/test_backlog_link_remove.py`
- `plugins/taskmaster/tests/test_backlog_link_query.py`
- `plugins/taskmaster/tests/test_backlog_link_validate.py`
- `plugins/taskmaster/tests/test_backlog_link_reconcile.py`
- `plugins/taskmaster/tests/test_slim_links_grouped.py`
- `plugins/taskmaster/tests/test_link_migration.py`
- `plugins/taskmaster/tests/test_links_smoke.py`
- `plugins/taskmaster/scripts/migrate_links.py` — one-shot migration CLI.
- `plugins/taskmaster/viewer/js/components/link-pills.js` — shared renderer.

---

## Phase 0 — Prerequisite: Verify test infrastructure

### Task 0: Verify test infrastructure from Plan A

**Prerequisite:** Plan A Task 0 must have already created `plugins/taskmaster/tests/conftest.py` with the `tmp_taskmaster` fixture and the `sys.path` shim that inserts `PLUGIN_ROOT` so bare `import backlog_server` and `from taskmaster_v3 import ...` resolve correctly. It also creates `plugins/__init__.py` and `plugins/taskmaster/__init__.py`.

**All Plan C test files rely on this — they use bare imports (`import backlog_server as bs`, `from taskmaster_v3 import ...`) without local `sys.path.insert` calls, trusting conftest to set up the path once.**

- [ ] **Step 1: Confirm conftest exists**

```bash
ls plugins/taskmaster/tests/conftest.py
```

Expected: file exists. If missing, create it now (copy the spec from Plan A Task 0):

```python
# plugins/taskmaster/tests/conftest.py
import sys
from pathlib import Path

# Make `backlog_server` and `taskmaster_v3` importable as bare modules.
PLUGIN_ROOT = Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))
```

- [ ] **Step 2: Confirm package markers exist**

```bash
ls plugins/__init__.py
ls plugins/taskmaster/__init__.py
```

Expected: both exist (Plan A Task 0 creates them). If missing, create empty marker files:

```bash
touch plugins/__init__.py
touch plugins/taskmaster/__init__.py
```

- [ ] **Step 3: Sanity-check import resolution**

```bash
cd plugins/taskmaster/tests && python -c "import backlog_server; from taskmaster_v3 import LINK_TYPES; print('ok')"
```

Expected: `ok` (or `ImportError: cannot import name 'LINK_TYPES'` if Plan C hasn't shipped yet — either is fine, as long as the modules are *found*).

- [ ] **Step 4: Commit (if you created conftest or __init__.py files)**

```bash
git add plugins/__init__.py plugins/taskmaster/__init__.py plugins/taskmaster/tests/conftest.py
git commit -m "chore(taskmaster): test infrastructure — conftest path shim + package markers"
```

---

## Phase 1 — Link types and validation foundation

### Task 1: Add `LINK_TYPES` and `REVERSE_TYPE` registries

**Files:**

- Modify: `plugins/taskmaster/taskmaster_v3.py` (add near `HEAVY_FIELDS`, ~line 195)
- Test: `plugins/taskmaster/tests/test_link_types.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# plugins/taskmaster/tests/test_link_types.py
from taskmaster_v3 import (
    LINK_TYPES,
    REVERSE_TYPE,
    ENTITY_KIND_BY_PREFIX,
    LINK_TYPE_DOMAIN,
    entity_kind_of,
    is_valid_link,
)


def test_canonical_link_types_present():
    expected = {
        "depends_on", "blocks", "fixes", "fixed_in_task",
        "relates_to", "informed_by", "informs",
        "supersedes", "superseded_by",
        "duplicate_of", "duplicates",
        "references", "referenced_by",
    }
    assert set(LINK_TYPES) == expected


def test_reverse_type_is_symmetric_pair():
    # Each type's reverse-of-reverse must round-trip back to itself.
    for t in LINK_TYPES:
        assert REVERSE_TYPE[REVERSE_TYPE[t]] == t


def test_reverse_type_specific_pairs():
    assert REVERSE_TYPE["depends_on"] == "blocks"
    assert REVERSE_TYPE["blocks"] == "depends_on"
    assert REVERSE_TYPE["fixes"] == "fixed_in_task"
    assert REVERSE_TYPE["fixed_in_task"] == "fixes"
    assert REVERSE_TYPE["informed_by"] == "informs"
    assert REVERSE_TYPE["informs"] == "informed_by"
    assert REVERSE_TYPE["supersedes"] == "superseded_by"
    assert REVERSE_TYPE["superseded_by"] == "supersedes"
    assert REVERSE_TYPE["duplicate_of"] == "duplicates"
    assert REVERSE_TYPE["duplicates"] == "duplicate_of"
    assert REVERSE_TYPE["references"] == "referenced_by"
    assert REVERSE_TYPE["referenced_by"] == "references"
    # relates_to is its own inverse
    assert REVERSE_TYPE["relates_to"] == "relates_to"


def test_entity_kind_by_prefix():
    assert ENTITY_KIND_BY_PREFIX["T"] == "task"
    assert ENTITY_KIND_BY_PREFIX["ISS"] == "issue"
    assert ENTITY_KIND_BY_PREFIX["L"] == "lesson"
    assert ENTITY_KIND_BY_PREFIX["HND"] == "handover"
    assert ENTITY_KIND_BY_PREFIX["IDEA"] == "idea"


def test_entity_kind_of_dispatches_by_prefix():
    assert entity_kind_of("T-001") == "task"
    assert entity_kind_of("ISS-007") == "issue"
    assert entity_kind_of("L-003") == "lesson"
    assert entity_kind_of("HND-012") == "handover"
    assert entity_kind_of("IDEA-005") == "idea"


def test_entity_kind_of_unknown_returns_none():
    assert entity_kind_of("FOO-001") is None
    assert entity_kind_of("") is None
    assert entity_kind_of(None) is None


def test_link_type_domain_enforces_source_target_kinds():
    # depends_on / blocks are task→task
    assert is_valid_link("depends_on", "task", "task") is True
    assert is_valid_link("depends_on", "task", "issue") is False
    # fixes is task→issue
    assert is_valid_link("fixes", "task", "issue") is True
    assert is_valid_link("fixes", "task", "task") is False
    # fixed_in_task is issue→task
    assert is_valid_link("fixed_in_task", "issue", "task") is True
    # informed_by is task→lesson
    assert is_valid_link("informed_by", "task", "lesson") is True
    # informs is lesson→task
    assert is_valid_link("informs", "lesson", "task") is True
    # supersedes / superseded_by are handover→handover
    assert is_valid_link("supersedes", "handover", "handover") is True
    assert is_valid_link("supersedes", "task", "handover") is False
    # duplicate_of / duplicates are issue→issue
    assert is_valid_link("duplicate_of", "issue", "issue") is True
    # relates_to and references are any→any
    for src in ("task", "issue", "lesson", "handover", "idea"):
        for dst in ("task", "issue", "lesson", "handover", "idea"):
            assert is_valid_link("relates_to", src, dst) is True
            assert is_valid_link("references", src, dst) is True
            assert is_valid_link("referenced_by", src, dst) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_link_types.py -v`
Expected: FAIL with `ImportError: cannot import name 'LINK_TYPES'`.

- [ ] **Step 3: Add the registries**

Add to `plugins/taskmaster/taskmaster_v3.py` after `HEAVY_FIELDS` (~line 195):

```python
# ── Typed links (Plan C / spec §6) ────────────────────────────

# Canonical link types and their inverses. Every link written on the
# source side has a corresponding inverse written on the target side
# by sync_inverse(). relates_to is its own inverse.
REVERSE_TYPE: dict[str, str] = {
    "depends_on":    "blocks",
    "blocks":        "depends_on",
    "fixes":         "fixed_in_task",
    "fixed_in_task": "fixes",
    "relates_to":    "relates_to",
    "informed_by":   "informs",
    "informs":       "informed_by",
    "supersedes":    "superseded_by",
    "superseded_by": "supersedes",
    "duplicate_of":  "duplicates",
    "duplicates":    "duplicate_of",
    "references":    "referenced_by",
    "referenced_by": "references",
}
LINK_TYPES: tuple[str, ...] = tuple(REVERSE_TYPE.keys())

# Entity-kind dispatch by ID prefix. Longest prefix wins (IDEA before I-).
ENTITY_KIND_BY_PREFIX: dict[str, str] = {
    "T":    "task",
    "ISS":  "issue",
    "L":    "lesson",
    "HND":  "handover",
    "IDEA": "idea",
}
# Order longest-first for prefix matching.
_PREFIX_ORDER: tuple[str, ...] = ("IDEA", "ISS", "HND", "T", "L")

# (source_kind, target_kind) pairs allowed per link type. "*" = any.
LINK_TYPE_DOMAIN: dict[str, tuple[str, str]] = {
    "depends_on":    ("task",     "task"),
    "blocks":        ("task",     "task"),
    "fixes":         ("task",     "issue"),
    "fixed_in_task": ("issue",    "task"),
    "informed_by":   ("task",     "lesson"),
    "informs":       ("lesson",   "task"),
    "supersedes":    ("handover", "handover"),
    "superseded_by": ("handover", "handover"),
    "duplicate_of":  ("issue",    "issue"),
    "duplicates":    ("issue",    "issue"),
    "relates_to":    ("*",        "*"),
    "references":    ("*",        "*"),
    "referenced_by": ("*",        "*"),
}


def entity_kind_of(entity_id: str | None) -> str | None:
    """Map an entity ID (e.g. 'T-001', 'ISS-007') to its kind, or None if unknown."""
    if not entity_id or not isinstance(entity_id, str):
        return None
    for prefix in _PREFIX_ORDER:
        if entity_id.startswith(prefix + "-"):
            return ENTITY_KIND_BY_PREFIX[prefix]
    return None


def is_valid_link(link_type: str, source_kind: str, target_kind: str) -> bool:
    """Return True if a link of `link_type` may go from source_kind to target_kind."""
    if link_type not in LINK_TYPE_DOMAIN:
        return False
    expected_src, expected_dst = LINK_TYPE_DOMAIN[link_type]
    if expected_src != "*" and expected_src != source_kind:
        return False
    if expected_dst != "*" and expected_dst != target_kind:
        return False
    return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_link_types.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_link_types.py
git commit -m "feat(taskmaster): add typed link registry (LINK_TYPES, REVERSE_TYPE, domain validation)"
```

---

### Task 2: Add `LINK_FIELD` constant and entity-link accessor helpers

**Files:**

- Modify: `plugins/taskmaster/taskmaster_v3.py`
- Test: `plugins/taskmaster/tests/test_link_helpers.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# plugins/taskmaster/tests/test_link_helpers.py
from taskmaster_v3 import (
    LINK_FIELD,
    entity_links,
    set_entity_links,
    add_link,
    remove_link,
    links_grouped_by_type,
)


def test_link_field_constant():
    assert LINK_FIELD == "links"


def test_entity_links_returns_empty_list_when_absent():
    assert entity_links({"id": "T-001"}) == []


def test_entity_links_returns_list_copy():
    entity = {"id": "T-001", "links": [{"type": "depends_on", "target": "T-002"}]}
    result = entity_links(entity)
    assert result == [{"type": "depends_on", "target": "T-002"}]
    # Mutating the copy must not affect the entity.
    result.append({"type": "blocks", "target": "T-003"})
    assert entity["links"] == [{"type": "depends_on", "target": "T-002"}]


def test_set_entity_links_replaces_array():
    entity: dict = {"id": "T-001"}
    set_entity_links(entity, [{"type": "depends_on", "target": "T-002"}])
    assert entity["links"] == [{"type": "depends_on", "target": "T-002"}]


def test_set_entity_links_drops_field_when_empty():
    entity = {"id": "T-001", "links": [{"type": "depends_on", "target": "T-002"}]}
    set_entity_links(entity, [])
    assert "links" not in entity


def test_add_link_appends():
    entity: dict = {"id": "T-001"}
    add_link(entity, "depends_on", "T-002")
    assert entity["links"] == [{"type": "depends_on", "target": "T-002"}]


def test_add_link_is_idempotent():
    entity: dict = {"id": "T-001"}
    add_link(entity, "depends_on", "T-002")
    add_link(entity, "depends_on", "T-002")
    assert entity["links"] == [{"type": "depends_on", "target": "T-002"}]


def test_add_link_preserves_other_types_to_same_target():
    entity: dict = {"id": "T-001"}
    add_link(entity, "depends_on", "T-002")
    add_link(entity, "relates_to", "T-002")
    assert len(entity["links"]) == 2


def test_remove_link_drops_one_entry():
    entity = {"id": "T-001", "links": [
        {"type": "depends_on", "target": "T-002"},
        {"type": "relates_to", "target": "T-002"},
    ]}
    removed = remove_link(entity, "depends_on", "T-002")
    assert removed is True
    assert entity["links"] == [{"type": "relates_to", "target": "T-002"}]


def test_remove_link_missing_returns_false():
    entity = {"id": "T-001", "links": [{"type": "relates_to", "target": "T-002"}]}
    removed = remove_link(entity, "depends_on", "T-002")
    assert removed is False
    assert entity["links"] == [{"type": "relates_to", "target": "T-002"}]


def test_remove_link_drops_links_field_when_empty():
    entity = {"id": "T-001", "links": [{"type": "depends_on", "target": "T-002"}]}
    remove_link(entity, "depends_on", "T-002")
    assert "links" not in entity


def test_links_grouped_by_type():
    entity = {"id": "T-001", "links": [
        {"type": "depends_on", "target": "T-002"},
        {"type": "depends_on", "target": "T-003"},
        {"type": "fixes",      "target": "ISS-007"},
        {"type": "references", "target": "HND-012"},
    ]}
    grouped = links_grouped_by_type(entity)
    assert grouped == {
        "depends_on": ["T-002", "T-003"],
        "fixes":      ["ISS-007"],
        "references": ["HND-012"],
    }


def test_links_grouped_by_type_empty():
    assert links_grouped_by_type({"id": "T-001"}) == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_link_helpers.py -v`
Expected: FAIL — `ImportError: cannot import name 'LINK_FIELD'`.

- [ ] **Step 3: Implement helpers**

Append to `plugins/taskmaster/taskmaster_v3.py` (after Task 1's `is_valid_link`):

```python
LINK_FIELD: str = "links"


def entity_links(entity: dict) -> list[dict]:
    """Return a shallow copy of the entity's links array (empty list if absent)."""
    raw = entity.get(LINK_FIELD) or []
    return [dict(link) for link in raw]


def set_entity_links(entity: dict, links: list[dict]) -> None:
    """Replace the entity's links array, dropping the field when empty."""
    if not links:
        entity.pop(LINK_FIELD, None)
    else:
        entity[LINK_FIELD] = [dict(link) for link in links]


def add_link(entity: dict, link_type: str, target: str) -> bool:
    """Idempotently add a {type, target} entry. Returns True if added, False if dup."""
    current = entity_links(entity)
    needle = {"type": link_type, "target": target}
    if needle in current:
        return False
    current.append(needle)
    set_entity_links(entity, current)
    return True


def remove_link(entity: dict, link_type: str, target: str) -> bool:
    """Remove a single {type, target} entry. Returns True if removed, False if absent."""
    current = entity_links(entity)
    needle = {"type": link_type, "target": target}
    if needle not in current:
        return False
    current.remove(needle)
    set_entity_links(entity, current)
    return True


def links_grouped_by_type(entity: dict) -> dict[str, list[str]]:
    """Return {type: [target_id, ...]} grouped view. Used by slim-view rendering."""
    grouped: dict[str, list[str]] = {}
    for link in entity_links(entity):
        grouped.setdefault(link["type"], []).append(link["target"])
    return grouped
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_link_helpers.py -v`
Expected: 12 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_link_helpers.py
git commit -m "feat(taskmaster): add entity-link accessor helpers (add/remove/grouped)"
```

---

### Task 3: Cycle detection over `depends_on`

**Files:**

- Modify: `plugins/taskmaster/taskmaster_v3.py`
- Test: `plugins/taskmaster/tests/test_link_cycle_detection.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# plugins/taskmaster/tests/test_link_cycle_detection.py
from taskmaster_v3 import find_cycle, would_create_cycle


def test_find_cycle_self_edge():
    # T-001 depends_on T-001
    graph = {"T-001": ["T-001"]}
    assert find_cycle(graph) == ["T-001", "T-001"]


def test_find_cycle_two_node():
    # T-001 -> T-002 -> T-001
    graph = {"T-001": ["T-002"], "T-002": ["T-001"]}
    cycle = find_cycle(graph)
    assert cycle is not None
    # Must form a closed loop.
    assert cycle[0] == cycle[-1]
    assert set(cycle[:-1]) == {"T-001", "T-002"}


def test_find_cycle_three_node():
    # T-001 -> T-002 -> T-003 -> T-001
    graph = {"T-001": ["T-002"], "T-002": ["T-003"], "T-003": ["T-001"]}
    cycle = find_cycle(graph)
    assert cycle is not None
    assert cycle[0] == cycle[-1]
    assert {"T-001", "T-002", "T-003"}.issubset(set(cycle))


def test_find_cycle_dag_returns_none():
    graph = {"T-001": ["T-002"], "T-002": ["T-003"], "T-003": []}
    assert find_cycle(graph) is None


def test_find_cycle_disconnected_components():
    graph = {
        "T-001": ["T-002"],
        "T-002": [],
        "T-003": ["T-004"],
        "T-004": ["T-003"],   # cycle in second component
    }
    cycle = find_cycle(graph)
    assert cycle is not None
    assert set(cycle[:-1]) == {"T-003", "T-004"}


def test_would_create_cycle_blocks_self_edge():
    graph = {"T-001": []}
    assert would_create_cycle(graph, "T-001", "T-001") is True


def test_would_create_cycle_blocks_two_node_loop():
    # T-001 -> T-002 already; adding T-002 -> T-001 closes the loop.
    graph = {"T-001": ["T-002"], "T-002": []}
    assert would_create_cycle(graph, "T-002", "T-001") is True


def test_would_create_cycle_allows_chain_extension():
    graph = {"T-001": ["T-002"], "T-002": []}
    assert would_create_cycle(graph, "T-002", "T-003") is False


def test_would_create_cycle_blocks_three_node_loop():
    # T-001 -> T-002 -> T-003 already; adding T-003 -> T-001 closes.
    graph = {"T-001": ["T-002"], "T-002": ["T-003"], "T-003": []}
    assert would_create_cycle(graph, "T-003", "T-001") is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_link_cycle_detection.py -v`
Expected: FAIL — `ImportError: cannot import name 'find_cycle'`.

- [ ] **Step 3: Implement cycle detection**

Append to `plugins/taskmaster/taskmaster_v3.py`:

```python
def find_cycle(graph: dict[str, list[str]]) -> list[str] | None:
    """Return a closed-loop cycle (first node repeated at end) or None.

    `graph` is a dict {source_id: [target_id, ...]} representing depends_on
    edges. DFS-based detection: returns the first cycle found.
    """
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {node: WHITE for node in graph}
    parent: dict[str, str | None] = {node: None for node in graph}

    def dfs(start: str) -> list[str] | None:
        stack: list[tuple[str, int]] = [(start, 0)]
        color[start] = GRAY
        while stack:
            node, idx = stack[-1]
            neighbors = graph.get(node, [])
            if idx >= len(neighbors):
                color[node] = BLACK
                stack.pop()
                continue
            stack[-1] = (node, idx + 1)
            nxt = neighbors[idx]
            if color.get(nxt, WHITE) == GRAY:
                # Self-edge: nxt == node and nxt is GRAY.
                if nxt == node:
                    return [node, node]
                # Build cycle by walking parents from `node` back to `nxt`.
                cycle = [nxt]
                cur: str | None = node
                while cur is not None and cur != nxt:
                    cycle.append(cur)
                    cur = parent.get(cur)
                cycle.append(nxt)
                cycle.reverse()
                return cycle
            if color.get(nxt, WHITE) == WHITE:
                color[nxt] = GRAY
                parent[nxt] = node
                stack.append((nxt, 0))
        return None

    for node in list(graph.keys()):
        if color[node] == WHITE:
            found = dfs(node)
            if found:
                return found
    return None


def would_create_cycle(graph: dict[str, list[str]], source: str, target: str) -> bool:
    """Return True if adding `source -> target` to `graph` introduces a cycle."""
    if source == target:
        return True
    augmented = {node: list(targets) for node, targets in graph.items()}
    augmented.setdefault(source, []).append(target)
    augmented.setdefault(target, augmented.get(target, []))
    return find_cycle(augmented) is not None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_link_cycle_detection.py -v`
Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_link_cycle_detection.py
git commit -m "feat(taskmaster): add depends_on cycle detection (find_cycle, would_create_cycle)"
```

---

## Phase 2 — Symmetric sync engine

### Task 4: Implement `read_entity_anywhere()` / `write_entity_anywhere()` dispatchers

**Files:**

- Modify: `plugins/taskmaster/taskmaster_v3.py`
- Test: `plugins/taskmaster/tests/test_link_inverse_sync.py` (create — used here and in Task 5)

- [ ] **Step 1: Write the failing test**

```python
# plugins/taskmaster/tests/test_link_inverse_sync.py
from pathlib import Path
import pytest
import yaml

from taskmaster_v3 import (
    read_entity_anywhere,
    write_entity_anywhere,
    load_v3, save_v3,
    write_handover, write_issue, write_lesson, write_idea,
)


@pytest.fixture
def tm_dir(tmp_path: Path) -> Path:
    d = tmp_path / ".taskmaster"
    d.mkdir()
    backlog = d / "backlog.yaml"
    backlog.write_text(yaml.safe_dump({
        "meta": {"schema_version": 3},
        "epics": [{"id": "e1", "title": "E", "tasks": [
            {"id": "T-001", "title": "First", "status": "todo"},
        ]}],
    }), encoding="utf-8")
    (d / "handovers").mkdir()
    (d / "issues").mkdir()
    (d / "lessons").mkdir()
    (d / "ideas").mkdir()
    (d / "tasks").mkdir()
    return d


def test_read_entity_anywhere_task(tm_dir):
    entity = read_entity_anywhere(tm_dir / "backlog.yaml", "T-001")
    assert entity["id"] == "T-001"
    assert entity["title"] == "First"


def test_read_entity_anywhere_handover(tm_dir):
    write_handover(tm_dir / "backlog.yaml", "HND-001",
                   {"id": "HND-001", "title": "H1", "tldr": "x", "status": "open",
                    "task_ids": ["T-001"]},
                   "Body content.")
    entity = read_entity_anywhere(tm_dir / "backlog.yaml", "HND-001")
    assert entity["id"] == "HND-001"


def test_read_entity_anywhere_issue(tm_dir):
    write_issue(tm_dir / "backlog.yaml", "ISS-001",
                {"id": "ISS-001", "title": "I1", "tldr": "x", "severity": "P2",
                 "status": "open"}, "Body.")
    entity = read_entity_anywhere(tm_dir / "backlog.yaml", "ISS-001")
    assert entity["id"] == "ISS-001"


def test_read_entity_anywhere_unknown_returns_none(tm_dir):
    assert read_entity_anywhere(tm_dir / "backlog.yaml", "ZZZ-999") is None


def test_write_entity_anywhere_task_roundtrip(tm_dir):
    entity = read_entity_anywhere(tm_dir / "backlog.yaml", "T-001")
    entity["links"] = [{"type": "depends_on", "target": "T-002"}]
    write_entity_anywhere(tm_dir / "backlog.yaml", entity)
    again = read_entity_anywhere(tm_dir / "backlog.yaml", "T-001")
    assert again["links"] == [{"type": "depends_on", "target": "T-002"}]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_link_inverse_sync.py -v`
Expected: FAIL — `ImportError: cannot import name 'read_entity_anywhere'`.

- [ ] **Step 3: Implement dispatcher helpers**

Append to `plugins/taskmaster/taskmaster_v3.py` near the existing read/write helpers:

```python
def read_entity_anywhere(backlog_path: Path, entity_id: str) -> dict | None:
    """Read any entity (task/issue/lesson/handover/idea) by ID. Returns its
    in-memory dict (frontmatter for non-task entities; merged dict for tasks).

    Body content for non-task entities is stored under BODY_KEY for round-trip.
    Returns None when the entity is unknown.
    """
    kind = entity_kind_of(entity_id)
    if kind is None:
        return None
    if kind == "task":
        data = load_v3(backlog_path)
        for epic in data.get("epics", []):
            for task in epic.get("tasks", []):
                if task.get("id") == entity_id:
                    return task
        return None
    reader = {
        "handover": read_handover,
        "issue":    read_issue,
        "lesson":   read_lesson,
        "idea":     read_idea,
    }[kind]
    try:
        fm, body = reader(backlog_path, entity_id)
    except FileNotFoundError:
        return None
    fm = dict(fm)
    if body:
        fm[BODY_KEY] = body
    return fm


def write_entity_anywhere(backlog_path: Path, entity: dict) -> None:
    """Persist an entity's frontmatter + body via the right writer.

    For tasks: round-trips through load_v3/save_v3 so the slim index stays
    consistent. For other entities: writes the per-entity markdown file with
    the updated frontmatter, preserving the existing body unless `_body` is set.
    """
    entity_id = entity.get("id")
    kind = entity_kind_of(entity_id)
    if kind is None:
        raise ValueError(f"unknown entity kind for id={entity_id!r}")
    if kind == "task":
        data = load_v3(backlog_path)
        for epic in data.get("epics", []):
            tasks = epic.get("tasks", [])
            for i, task in enumerate(tasks):
                if task.get("id") == entity_id:
                    tasks[i] = entity
                    save_v3(backlog_path, data)
                    return
        raise KeyError(f"task {entity_id!r} not found")
    # Non-task: split frontmatter vs body, then route to writer.
    body = entity.pop(BODY_KEY, "") if BODY_KEY in entity else ""
    fm = dict(entity)
    writers = {
        "handover": write_handover,
        "issue":    write_issue,
        "lesson":   write_lesson,
        "idea":     write_idea,
    }
    writers[kind](backlog_path, entity_id, fm, body)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_link_inverse_sync.py -v`
Expected: 5 passed (test_sync_inverse_* tasks below add more — currently 5).

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_link_inverse_sync.py
git commit -m "feat(taskmaster): add read_entity_anywhere/write_entity_anywhere dispatchers"
```

---

### Task 5: Implement `sync_inverse()` engine

**Files:**

- Modify: `plugins/taskmaster/taskmaster_v3.py`
- Test: `plugins/taskmaster/tests/test_link_inverse_sync.py` (extend)

- [ ] **Step 1: Append the failing tests**

Append to `plugins/taskmaster/tests/test_link_inverse_sync.py`:

```python
from taskmaster_v3 import sync_inverse, entity_links


def test_sync_inverse_writes_inverse_on_target(tm_dir):
    # Seed T-002 (target of an upcoming depends_on).
    data = yaml.safe_load((tm_dir / "backlog.yaml").read_text())
    data["epics"][0]["tasks"].append({"id": "T-002", "title": "Second", "status": "todo"})
    (tm_dir / "backlog.yaml").write_text(yaml.safe_dump(data))

    sync_inverse(tm_dir / "backlog.yaml", source="T-001", target="T-002", type="depends_on")
    t2 = read_entity_anywhere(tm_dir / "backlog.yaml", "T-002")
    assert {"type": "blocks", "target": "T-001"} in entity_links(t2)


def test_sync_inverse_idempotent(tm_dir):
    data = yaml.safe_load((tm_dir / "backlog.yaml").read_text())
    data["epics"][0]["tasks"].append({"id": "T-002", "title": "Second", "status": "todo"})
    (tm_dir / "backlog.yaml").write_text(yaml.safe_dump(data))

    sync_inverse(tm_dir / "backlog.yaml", "T-001", "T-002", "depends_on")
    sync_inverse(tm_dir / "backlog.yaml", "T-001", "T-002", "depends_on")
    t2 = read_entity_anywhere(tm_dir / "backlog.yaml", "T-002")
    assert entity_links(t2).count({"type": "blocks", "target": "T-001"}) == 1


def test_sync_inverse_relates_to_is_symmetric(tm_dir):
    write_issue(tm_dir / "backlog.yaml", "ISS-001",
                {"id": "ISS-001", "title": "Bug", "tldr": "x", "severity": "P2",
                 "status": "open"}, "Body.")
    sync_inverse(tm_dir / "backlog.yaml", "T-001", "ISS-001", "relates_to")
    iss = read_entity_anywhere(tm_dir / "backlog.yaml", "ISS-001")
    assert {"type": "relates_to", "target": "T-001"} in entity_links(iss)


def test_sync_inverse_remove_drops_inverse(tm_dir):
    write_issue(tm_dir / "backlog.yaml", "ISS-001",
                {"id": "ISS-001", "title": "Bug", "tldr": "x", "severity": "P2",
                 "status": "open"}, "Body.")
    sync_inverse(tm_dir / "backlog.yaml", "T-001", "ISS-001", "fixes")
    iss = read_entity_anywhere(tm_dir / "backlog.yaml", "ISS-001")
    assert {"type": "fixed_in_task", "target": "T-001"} in entity_links(iss)

    sync_inverse(tm_dir / "backlog.yaml", "T-001", "ISS-001", "fixes", remove=True)
    iss = read_entity_anywhere(tm_dir / "backlog.yaml", "ISS-001")
    assert {"type": "fixed_in_task", "target": "T-001"} not in entity_links(iss)


def test_sync_inverse_missing_target_raises(tm_dir):
    with pytest.raises(KeyError):
        sync_inverse(tm_dir / "backlog.yaml", "T-001", "T-999", "depends_on")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_link_inverse_sync.py::test_sync_inverse_writes_inverse_on_target -v`
Expected: FAIL — `ImportError: cannot import name 'sync_inverse'`.

- [ ] **Step 3: Implement `sync_inverse`**

Append to `plugins/taskmaster/taskmaster_v3.py`:

```python
def sync_inverse(
    backlog_path: Path,
    source: str,
    target: str,
    type: str,
    *,
    remove: bool = False,
) -> None:
    """Write (or remove) the inverse link on the target entity.

    Used by `backlog_link_create`/`backlog_link_remove` to keep both sides in
    lockstep. Raises KeyError if the target entity does not exist (caller
    decides whether to surface the error or treat it as a soft warning).
    """
    if type not in REVERSE_TYPE:
        raise ValueError(f"unknown link type {type!r}")
    target_entity = read_entity_anywhere(backlog_path, target)
    if target_entity is None:
        raise KeyError(f"target entity {target!r} not found")
    inverse_type = REVERSE_TYPE[type]
    if remove:
        changed = remove_link(target_entity, inverse_type, source)
    else:
        changed = add_link(target_entity, inverse_type, source)
    if changed:
        write_entity_anywhere(backlog_path, target_entity)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_link_inverse_sync.py -v`
Expected: 10 passed (5 dispatch + 5 sync).

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_link_inverse_sync.py
git commit -m "feat(taskmaster): sync_inverse() writes inverse link on peer entity"
```

---

## Phase 3 — Auto-detection of inline references

### Task 6: `extract_inline_refs()` — body-text scanner

**Files:**

- Modify: `plugins/taskmaster/taskmaster_v3.py`
- Test: `plugins/taskmaster/tests/test_inline_ref_extraction.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# plugins/taskmaster/tests/test_inline_ref_extraction.py
from taskmaster_v3 import extract_inline_refs


def test_extract_bare_task_id():
    assert extract_inline_refs("Working on T-001 now.") == ["T-001"]


def test_extract_bare_issue_and_lesson_and_handover_and_idea():
    body = "Picked up T-001 to fix ISS-007 using L-003; see HND-012 and IDEA-005."
    assert set(extract_inline_refs(body)) == {"T-001", "ISS-007", "L-003", "HND-012", "IDEA-005"}


def test_extract_wiki_style():
    assert extract_inline_refs("Picked up [[T-001]] and [[ISS-007]].") == ["T-001", "ISS-007"]


def test_extract_mention_style():
    assert extract_inline_refs("Cc @T-001, blocked by @ISS-007.") == ["T-001", "ISS-007"]


def test_extract_dedupes():
    body = "T-001 is great. Again: T-001. Also [[T-001]] and @T-001."
    assert extract_inline_refs(body) == ["T-001"]


def test_extract_preserves_first_seen_order():
    body = "First ISS-007, then T-001, then L-003, then T-001 again."
    assert extract_inline_refs(body) == ["ISS-007", "T-001", "L-003"]


def test_extract_ignores_lowercase_and_partials():
    # Lowercase prefixes are not valid IDs.
    assert extract_inline_refs("t-001 and iss-7 should not match.") == []
    # Numbers without prefix don't match.
    assert extract_inline_refs("Refs 001 or 7.") == []


def test_extract_ignores_id_inside_word():
    # "noT-001" is not a valid ID mention — must be preceded by start/whitespace/punct.
    assert extract_inline_refs("This is noT-001 prefix.") == []


def test_extract_excludes_self_reference():
    assert extract_inline_refs("Self-ref to T-001 here.", self_id="T-001") == []


def test_extract_empty_body():
    assert extract_inline_refs("") == []
    assert extract_inline_refs(None) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_inline_ref_extraction.py -v`
Expected: FAIL — `ImportError: cannot import name 'extract_inline_refs'`.

- [ ] **Step 3: Implement the scanner**

Append to `plugins/taskmaster/taskmaster_v3.py`:

```python
# Match a known prefix (IDEA|ISS|HND|T|L) followed by '-' and 1+ digits,
# optionally wrapped in [[...]] or preceded by '@'. Anchored on a non-word
# boundary on the left so "noT-001" doesn't match.
_INLINE_REF_RE = re.compile(
    r"(?:(?<=^)|(?<=[^A-Za-z0-9_]))"               # left boundary
    r"(?:\[\[|@)?"                                  # optional [[ or @
    r"(IDEA-\d+|ISS-\d+|HND-\d+|T-\d+|L-\d+)"       # captured ID
    r"(?:\]\])?"                                    # optional ]]
)


def extract_inline_refs(body: str | None, *, self_id: str | None = None) -> list[str]:
    """Scan markdown body for entity ID mentions.

    Recognized patterns:
      - Bare: T-001, ISS-007, L-003, HND-012, IDEA-005
      - Wiki: [[T-001]]
      - Mention: @T-001

    Returns IDs in first-seen order, deduped. Excludes self_id when supplied.
    Case-sensitive — uppercase prefixes only.
    """
    if not body:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for match in _INLINE_REF_RE.finditer(body):
        eid = match.group(1)
        if eid in seen:
            continue
        if self_id and eid == self_id:
            continue
        seen.add(eid)
        out.append(eid)
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_inline_ref_extraction.py -v`
Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_inline_ref_extraction.py
git commit -m "feat(taskmaster): extract_inline_refs() scans entity bodies for ID mentions"
```

---

### Task 7: `auto_link_on_save()` — opt-out aware

**Files:**

- Modify: `plugins/taskmaster/taskmaster_v3.py`
- Test: `plugins/taskmaster/tests/test_auto_link_on_save.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# plugins/taskmaster/tests/test_auto_link_on_save.py
from pathlib import Path
import pytest
import yaml

from taskmaster_v3 import (
    auto_link_on_save,
    entity_links,
    write_handover, write_issue, read_entity_anywhere,
)


@pytest.fixture
def tm_dir(tmp_path: Path) -> Path:
    d = tmp_path / ".taskmaster"
    d.mkdir()
    (d / "backlog.yaml").write_text(yaml.safe_dump({
        "meta": {"schema_version": 3},
        "epics": [{"id": "e1", "title": "E", "tasks": [
            {"id": "T-001", "title": "First", "status": "todo"},
            {"id": "T-005", "title": "Fifth", "status": "todo"},
        ]}],
    }))
    for sub in ("handovers", "issues", "lessons", "ideas", "tasks"):
        (d / sub).mkdir()
    return d


def test_auto_link_adds_references_for_inline_mentions(tm_dir):
    write_handover(tm_dir / "backlog.yaml", "HND-001",
                   {"id": "HND-001", "tldr": "x", "status": "open", "task_ids": ["T-001"]},
                   "T-001 done, next start T-005.")
    auto_link_on_save(tm_dir / "backlog.yaml", "HND-001")

    hnd = read_entity_anywhere(tm_dir / "backlog.yaml", "HND-001")
    targets = {link["target"] for link in entity_links(hnd) if link["type"] == "references"}
    assert {"T-001", "T-005"}.issubset(targets)


def test_auto_link_writes_referenced_by_on_targets(tm_dir):
    write_handover(tm_dir / "backlog.yaml", "HND-001",
                   {"id": "HND-001", "tldr": "x", "status": "open", "task_ids": []},
                   "See T-005 for details.")
    auto_link_on_save(tm_dir / "backlog.yaml", "HND-001")

    t5 = read_entity_anywhere(tm_dir / "backlog.yaml", "T-005")
    assert {"type": "referenced_by", "target": "HND-001"} in entity_links(t5)


def test_auto_link_respects_auto_link_false(tm_dir):
    write_handover(tm_dir / "backlog.yaml", "HND-001",
                   {"id": "HND-001", "tldr": "x", "status": "open",
                    "task_ids": [], "auto_link": False},
                   "Mentions T-005 but should not link.")
    auto_link_on_save(tm_dir / "backlog.yaml", "HND-001")

    hnd = read_entity_anywhere(tm_dir / "backlog.yaml", "HND-001")
    assert entity_links(hnd) == []
    t5 = read_entity_anywhere(tm_dir / "backlog.yaml", "T-005")
    assert {"type": "referenced_by", "target": "HND-001"} not in entity_links(t5)


def test_auto_link_does_not_overwrite_stronger_explicit_link(tm_dir):
    # Pre-existing explicit fixes link.
    write_issue(tm_dir / "backlog.yaml", "ISS-001",
                {"id": "ISS-001", "tldr": "x", "severity": "P2", "status": "open"},
                "Body.")
    write_handover(tm_dir / "backlog.yaml", "HND-001",
                   {"id": "HND-001", "tldr": "x", "status": "open",
                    "task_ids": ["T-001"],
                    "links": [{"type": "relates_to", "target": "ISS-001"}]},
                   "Discussion of ISS-001 in body.")
    auto_link_on_save(tm_dir / "backlog.yaml", "HND-001")

    hnd = read_entity_anywhere(tm_dir / "backlog.yaml", "HND-001")
    types_to_iss = {link["type"] for link in entity_links(hnd) if link["target"] == "ISS-001"}
    # ISS-001 already has a link of any type; auto-detection skips it entirely.
    assert types_to_iss == {"relates_to"}


def test_auto_link_excludes_self_reference(tm_dir):
    write_handover(tm_dir / "backlog.yaml", "HND-001",
                   {"id": "HND-001", "tldr": "x", "status": "open", "task_ids": []},
                   "This handover is HND-001 — should not self-link.")
    auto_link_on_save(tm_dir / "backlog.yaml", "HND-001")

    hnd = read_entity_anywhere(tm_dir / "backlog.yaml", "HND-001")
    assert entity_links(hnd) == []


def test_auto_link_skips_missing_targets(tm_dir):
    write_handover(tm_dir / "backlog.yaml", "HND-001",
                   {"id": "HND-001", "tldr": "x", "status": "open", "task_ids": []},
                   "Mentions T-999 which doesn't exist.")
    auto_link_on_save(tm_dir / "backlog.yaml", "HND-001")
    hnd = read_entity_anywhere(tm_dir / "backlog.yaml", "HND-001")
    # Missing target → skipped, not a hard error.
    assert all(link["target"] != "T-999" for link in entity_links(hnd))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_auto_link_on_save.py -v`
Expected: FAIL — `ImportError: cannot import name 'auto_link_on_save'`.

- [ ] **Step 3: Implement `auto_link_on_save`**

Append to `plugins/taskmaster/taskmaster_v3.py`:

```python
def auto_link_on_save(backlog_path: Path, entity_id: str) -> list[str]:
    """Scan an entity's body and add `references` links for inline mentions.

    Rules (spec §6C):
      - Skip when entity frontmatter has `auto_link: false`.
      - Add a `references` link for each unique mention not already linked.
      - Existing explicit link types (anything stronger than `references`)
        are never overwritten.
      - Self-references are skipped.
      - Targets that don't exist are skipped (logged via return value).
      - Writes the inverse `referenced_by` on each target.

    Returns the list of newly-added target IDs.
    """
    entity = read_entity_anywhere(backlog_path, entity_id)
    if entity is None:
        return []
    if entity.get("auto_link") is False:
        return []

    body = entity.get(BODY_KEY, "") or ""
    refs = extract_inline_refs(body, self_id=entity_id)
    if not refs:
        return []

    existing_targets = {link["target"] for link in entity_links(entity)}
    added: list[str] = []
    for target_id in refs:
        if target_id in existing_targets:
            # Any link to this target already exists; auto-detection only adds new
            # targets, never modifies existing links (regardless of type strength).
            continue
        # Confirm target exists; skip silently if not.
        target_entity = read_entity_anywhere(backlog_path, target_id)
        if target_entity is None:
            continue
        add_link(entity, "references", target_id)
        added.append(target_id)

    if added:
        write_entity_anywhere(backlog_path, entity)
        for target_id in added:
            try:
                sync_inverse(backlog_path, source=entity_id,
                             target=target_id, type="references")
            except KeyError:
                pass
    return added
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_auto_link_on_save.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_auto_link_on_save.py
git commit -m "feat(taskmaster): auto_link_on_save() materializes inline references on save"
```

---

## Phase 4 — MCP tools

### Task 8: `backlog_link_create` MCP tool

**Files:**

- Modify: `plugins/taskmaster/backlog_server.py` (add near `backlog_handover_resync`, ~L1810)
- Test: `plugins/taskmaster/tests/test_backlog_link_create.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# plugins/taskmaster/tests/test_backlog_link_create.py
from pathlib import Path
import pytest
import yaml

import backlog_server as bs
from taskmaster_v3 import read_entity_anywhere, entity_links


@pytest.fixture
def tm_dir(tmp_path: Path, monkeypatch) -> Path:
    d = tmp_path / ".taskmaster"
    d.mkdir()
    (d / "backlog.yaml").write_text(yaml.safe_dump({
        "meta": {"schema_version": 3},
        "epics": [{"id": "e1", "title": "E", "tasks": [
            {"id": "T-001", "title": "First", "status": "todo"},
            {"id": "T-002", "title": "Second", "status": "todo"},
            {"id": "T-003", "title": "Third", "status": "todo"},
        ]}],
    }))
    for sub in ("handovers", "issues", "lessons", "ideas", "tasks"):
        (d / sub).mkdir()
    monkeypatch.setattr(bs, "_backlog_path", lambda: d / "backlog.yaml")
    return d


def test_link_create_writes_both_sides(tm_dir):
    out = bs.backlog_link_create(source="T-001", target="T-002", type="depends_on")
    assert "ok" in out.lower()
    t1 = read_entity_anywhere(tm_dir / "backlog.yaml", "T-001")
    t2 = read_entity_anywhere(tm_dir / "backlog.yaml", "T-002")
    assert {"type": "depends_on", "target": "T-002"} in entity_links(t1)
    assert {"type": "blocks", "target": "T-001"} in entity_links(t2)


def test_link_create_rejects_unknown_type(tm_dir):
    out = bs.backlog_link_create(source="T-001", target="T-002", type="nope")
    assert "invalid" in out.lower() or "unknown" in out.lower()


def test_link_create_rejects_domain_mismatch(tm_dir):
    # depends_on is task→task; T-001 → ISS-007 should fail.
    out = bs.backlog_link_create(source="T-001", target="ISS-007", type="depends_on")
    assert "invalid" in out.lower()


def test_link_create_rejects_missing_target(tm_dir):
    out = bs.backlog_link_create(source="T-001", target="T-999", type="depends_on")
    assert "not found" in out.lower() or "missing" in out.lower()


def test_link_create_rejects_self_cycle(tm_dir):
    out = bs.backlog_link_create(source="T-001", target="T-001", type="depends_on")
    assert "cycle" in out.lower()
    t1 = read_entity_anywhere(tm_dir / "backlog.yaml", "T-001")
    assert entity_links(t1) == []


def test_link_create_rejects_two_node_cycle(tm_dir):
    bs.backlog_link_create(source="T-001", target="T-002", type="depends_on")
    out = bs.backlog_link_create(source="T-002", target="T-001", type="depends_on")
    assert "cycle" in out.lower()


def test_link_create_rejects_three_node_cycle(tm_dir):
    bs.backlog_link_create(source="T-001", target="T-002", type="depends_on")
    bs.backlog_link_create(source="T-002", target="T-003", type="depends_on")
    out = bs.backlog_link_create(source="T-003", target="T-001", type="depends_on")
    assert "cycle" in out.lower()


def test_link_create_idempotent(tm_dir):
    bs.backlog_link_create(source="T-001", target="T-002", type="depends_on")
    bs.backlog_link_create(source="T-001", target="T-002", type="depends_on")
    t1 = read_entity_anywhere(tm_dir / "backlog.yaml", "T-001")
    count = sum(1 for link in entity_links(t1)
                if link == {"type": "depends_on", "target": "T-002"})
    assert count == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_backlog_link_create.py -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'backlog_link_create'`.

- [ ] **Step 3: Implement `backlog_link_create`**

Add to `plugins/taskmaster/backlog_server.py` (after `backlog_handover_resync`):

```python
@mcp.tool()
def backlog_link_create(source: str, target: str, type: str, note: str = "") -> str:
    """Create a typed link from `source` to `target`. Server writes the inverse
    on the target side automatically (see spec §6A/§6B).

    Validates: link type is canonical; source/target kinds match the type's
    domain; target entity exists; depends_on writes don't create cycles.
    Idempotent.
    """
    from taskmaster_v3 import (
        REVERSE_TYPE, LINK_TYPES, is_valid_link, entity_kind_of,
        read_entity_anywhere, write_entity_anywhere, add_link, entity_links,
        sync_inverse, would_create_cycle,
    )

    backlog_path = _backlog_path()

    if type not in LINK_TYPES:
        return f"error: invalid link type {type!r} (valid: {sorted(LINK_TYPES)})"

    src_kind = entity_kind_of(source)
    dst_kind = entity_kind_of(target)
    if src_kind is None:
        return f"error: invalid source ID {source!r}"
    if dst_kind is None:
        return f"error: invalid target ID {target!r}"
    if not is_valid_link(type, src_kind, dst_kind):
        return (f"error: invalid link — type {type!r} cannot go from "
                f"{src_kind} ({source}) to {dst_kind} ({target})")

    src_entity = read_entity_anywhere(backlog_path, source)
    if src_entity is None:
        return f"error: source {source!r} not found"
    dst_entity = read_entity_anywhere(backlog_path, target)
    if dst_entity is None:
        return f"error: target {target!r} not found"

    # Cycle check on depends_on / blocks (model both as forward edges
    # in a single task→task graph).
    if type in ("depends_on", "blocks"):
        # Normalize 'blocks' as a reversed depends_on for graph construction.
        graph: dict[str, list[str]] = {}
        data = load_v3(backlog_path)
        for epic in data.get("epics", []):
            for task in epic.get("tasks", []):
                tid = task.get("id")
                if not tid:
                    continue
                outs: list[str] = []
                for link in task.get("links", []) or []:
                    if link.get("type") == "depends_on":
                        outs.append(link["target"])
                    elif link.get("type") == "blocks":
                        # B blocks A == A depends_on B
                        graph.setdefault(link["target"], []).append(tid)
                graph.setdefault(tid, [])
                graph[tid].extend(outs)
        # Normalize the new edge to a depends_on direction.
        new_src, new_dst = (source, target) if type == "depends_on" else (target, source)
        if would_create_cycle(graph, new_src, new_dst):
            return (f"error: would create cycle in depends_on chain "
                    f"({new_src} → {new_dst})")

    added = add_link(src_entity, type, target)
    if added:
        write_entity_anywhere(backlog_path, src_entity)
    try:
        sync_inverse(backlog_path, source=source, target=target, type=type)
    except KeyError as e:
        return f"error: {e}"

    suffix = "" if added else " (no-op, link already present)"
    note_part = f" — {note}" if note else ""
    return f"ok: linked {source} —[{type}]→ {target}{suffix}{note_part}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_backlog_link_create.py -v`
Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_backlog_link_create.py
git commit -m "feat(taskmaster): backlog_link_create MCP tool with cycle detection"
```

---

### Task 9: `backlog_link_remove` MCP tool

**Files:**

- Modify: `plugins/taskmaster/backlog_server.py`
- Test: `plugins/taskmaster/tests/test_backlog_link_remove.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# plugins/taskmaster/tests/test_backlog_link_remove.py
from pathlib import Path
import pytest
import yaml

import backlog_server as bs
from taskmaster_v3 import read_entity_anywhere, entity_links


@pytest.fixture
def tm_dir(tmp_path: Path, monkeypatch) -> Path:
    d = tmp_path / ".taskmaster"
    d.mkdir()
    (d / "backlog.yaml").write_text(yaml.safe_dump({
        "meta": {"schema_version": 3},
        "epics": [{"id": "e1", "title": "E", "tasks": [
            {"id": "T-001", "title": "First", "status": "todo"},
            {"id": "T-002", "title": "Second", "status": "todo"},
        ]}],
    }))
    for sub in ("handovers", "issues", "lessons", "ideas", "tasks"):
        (d / sub).mkdir()
    monkeypatch.setattr(bs, "_backlog_path", lambda: d / "backlog.yaml")
    bs.backlog_link_create(source="T-001", target="T-002", type="depends_on")
    bs.backlog_link_create(source="T-001", target="T-002", type="relates_to")
    return d


def test_link_remove_drops_both_sides(tm_dir):
    out = bs.backlog_link_remove(source="T-001", target="T-002", type="depends_on")
    assert "ok" in out.lower()
    t1 = read_entity_anywhere(tm_dir / "backlog.yaml", "T-001")
    t2 = read_entity_anywhere(tm_dir / "backlog.yaml", "T-002")
    assert {"type": "depends_on", "target": "T-002"} not in entity_links(t1)
    assert {"type": "blocks",     "target": "T-001"} not in entity_links(t2)
    # The other link (relates_to) survives.
    assert {"type": "relates_to", "target": "T-002"} in entity_links(t1)


def test_link_remove_without_type_drops_all_between_pair(tm_dir):
    bs.backlog_link_remove(source="T-001", target="T-002")
    t1 = read_entity_anywhere(tm_dir / "backlog.yaml", "T-001")
    t2 = read_entity_anywhere(tm_dir / "backlog.yaml", "T-002")
    assert all(link["target"] != "T-002" for link in entity_links(t1))
    assert all(link["target"] != "T-001" for link in entity_links(t2))


def test_link_remove_missing_link_is_noop(tm_dir):
    bs.backlog_link_remove(source="T-001", target="T-002", type="depends_on")
    out = bs.backlog_link_remove(source="T-001", target="T-002", type="depends_on")
    assert "no-op" in out.lower() or "not present" in out.lower() or "ok" in out.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_backlog_link_remove.py -v`
Expected: FAIL — `AttributeError: ... backlog_link_remove`.

- [ ] **Step 3: Implement `backlog_link_remove`**

Add to `plugins/taskmaster/backlog_server.py`:

```python
@mcp.tool()
def backlog_link_remove(source: str, target: str, type: str = "") -> str:
    """Remove a link (and its inverse) between `source` and `target`.

    If `type` is omitted, removes all link types between the pair.
    """
    from taskmaster_v3 import (
        LINK_TYPES, entity_kind_of, read_entity_anywhere, write_entity_anywhere,
        remove_link, entity_links, sync_inverse,
    )

    backlog_path = _backlog_path()

    if entity_kind_of(source) is None:
        return f"error: invalid source ID {source!r}"
    if entity_kind_of(target) is None:
        return f"error: invalid target ID {target!r}"

    src_entity = read_entity_anywhere(backlog_path, source)
    if src_entity is None:
        return f"error: source {source!r} not found"

    types_to_remove: list[str]
    if type:
        if type not in LINK_TYPES:
            return f"error: invalid link type {type!r}"
        types_to_remove = [type]
    else:
        types_to_remove = sorted({link["type"] for link in entity_links(src_entity)
                                  if link["target"] == target})

    if not types_to_remove:
        return f"ok: no-op (no links from {source} to {target})"

    removed_any = False
    for t in types_to_remove:
        if remove_link(src_entity, t, target):
            removed_any = True
        try:
            sync_inverse(backlog_path, source=source, target=target, type=t, remove=True)
        except KeyError:
            pass
    if removed_any:
        write_entity_anywhere(backlog_path, src_entity)
        return f"ok: removed {len(types_to_remove)} link(s) between {source} and {target}"
    return f"ok: no-op (links not present between {source} and {target})"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_backlog_link_remove.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_backlog_link_remove.py
git commit -m "feat(taskmaster): backlog_link_remove MCP tool (removes both sides)"
```

---

### Task 10: `backlog_link_query` MCP tool

**Files:**

- Modify: `plugins/taskmaster/backlog_server.py`
- Test: `plugins/taskmaster/tests/test_backlog_link_query.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# plugins/taskmaster/tests/test_backlog_link_query.py
from pathlib import Path
import json
import pytest
import yaml

import backlog_server as bs


@pytest.fixture
def tm_dir(tmp_path: Path, monkeypatch) -> Path:
    d = tmp_path / ".taskmaster"
    d.mkdir()
    (d / "backlog.yaml").write_text(yaml.safe_dump({
        "meta": {"schema_version": 3},
        "epics": [{"id": "e1", "title": "E", "tasks": [
            {"id": "T-001", "title": "First", "status": "todo"},
            {"id": "T-002", "title": "Second", "status": "todo"},
            {"id": "T-003", "title": "Third", "status": "todo"},
        ]}],
    }))
    for sub in ("handovers", "issues", "lessons", "ideas", "tasks"):
        (d / sub).mkdir()
    monkeypatch.setattr(bs, "_backlog_path", lambda: d / "backlog.yaml")
    bs.backlog_link_create(source="T-001", target="T-002", type="depends_on")
    bs.backlog_link_create(source="T-002", target="T-003", type="depends_on")
    return d


def test_query_by_source(tm_dir):
    out = bs.backlog_link_query(source="T-001")
    data = json.loads(out)
    assert {"source": "T-001", "target": "T-002", "type": "depends_on"} in data


def test_query_by_target(tm_dir):
    out = bs.backlog_link_query(target="T-002")
    data = json.loads(out)
    # T-001 depends_on T-002 (forward); T-002 has 'blocks' to T-001 (inverse, source-side).
    sources = {entry["source"] for entry in data}
    assert "T-001" in sources


def test_query_by_type(tm_dir):
    out = bs.backlog_link_query(type="depends_on")
    data = json.loads(out)
    pairs = {(entry["source"], entry["target"]) for entry in data}
    assert ("T-001", "T-002") in pairs
    assert ("T-002", "T-003") in pairs


def test_query_depth_two_traverses(tm_dir):
    out = bs.backlog_link_query(source="T-001", type="depends_on", depth=2)
    data = json.loads(out)
    pairs = {(entry["source"], entry["target"]) for entry in data}
    # depth=2 surfaces T-001 → T-002 AND T-002 → T-003.
    assert ("T-001", "T-002") in pairs
    assert ("T-002", "T-003") in pairs


def test_query_depth_one_does_not_traverse(tm_dir):
    out = bs.backlog_link_query(source="T-001", type="depends_on", depth=1)
    data = json.loads(out)
    pairs = {(entry["source"], entry["target"]) for entry in data}
    assert ("T-001", "T-002") in pairs
    assert ("T-002", "T-003") not in pairs
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_backlog_link_query.py -v`
Expected: FAIL — `AttributeError: ... backlog_link_query`.

- [ ] **Step 3: Implement `backlog_link_query`**

Add to `plugins/taskmaster/backlog_server.py`:

```python
@mcp.tool()
def backlog_link_query(source: str = "", target: str = "", type: str = "",
                       depth: int = 1) -> str:
    """Return links matching the source/target/type filter.

    With depth>1, traverses transitively along the same `type`. Returns a JSON
    array of {source, target, type} entries.
    """
    import json as _json
    from taskmaster_v3 import (
        entity_kind_of, read_entity_anywhere, entity_links, load_v3,
    )

    backlog_path = _backlog_path()

    def edges_from(entity_id: str) -> list[dict]:
        entity = read_entity_anywhere(backlog_path, entity_id)
        if entity is None:
            return []
        return [{"source": entity_id, "target": link["target"], "type": link["type"]}
                for link in entity_links(entity)]

    def all_edges() -> list[dict]:
        out: list[dict] = []
        data = load_v3(backlog_path)
        for epic in data.get("epics", []):
            for task in epic.get("tasks", []):
                tid = task.get("id")
                if not tid:
                    continue
                for link in task.get("links", []) or []:
                    out.append({"source": tid, "target": link["target"], "type": link["type"]})
        for sub, prefix in (("handovers", "HND"), ("issues", "ISS"),
                            ("lessons", "L"), ("ideas", "IDEA")):
            sub_dir = backlog_path.parent / sub
            if not sub_dir.exists():
                continue
            for fp in sub_dir.glob(f"{prefix}-*.md"):
                eid = fp.stem
                entity = read_entity_anywhere(backlog_path, eid)
                if entity is None:
                    continue
                for link in entity_links(entity):
                    out.append({"source": eid, "target": link["target"], "type": link["type"]})
        return out

    if source and entity_kind_of(source) is None:
        return f"error: invalid source ID {source!r}"
    if target and entity_kind_of(target) is None:
        return f"error: invalid target ID {target!r}"

    if source:
        results = list(edges_from(source))
        if depth > 1 and type:
            seen = {(e["source"], e["target"]) for e in results}
            frontier = [e["target"] for e in results if e["type"] == type]
            for _ in range(depth - 1):
                next_frontier: list[str] = []
                for node in frontier:
                    for edge in edges_from(node):
                        if edge["type"] != type:
                            continue
                        key = (edge["source"], edge["target"])
                        if key in seen:
                            continue
                        seen.add(key)
                        results.append(edge)
                        next_frontier.append(edge["target"])
                frontier = next_frontier
    else:
        results = all_edges()

    if target:
        results = [e for e in results if e["target"] == target]
    if type:
        results = [e for e in results if e["type"] == type]
    return _json.dumps(results)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_backlog_link_query.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_backlog_link_query.py
git commit -m "feat(taskmaster): backlog_link_query MCP tool with depth traversal"
```

---

### Task 11: `backlog_link_validate` MCP tool

**Files:**

- Modify: `plugins/taskmaster/backlog_server.py`
- Test: `plugins/taskmaster/tests/test_backlog_link_validate.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# plugins/taskmaster/tests/test_backlog_link_validate.py
from pathlib import Path
import json
import pytest
import yaml

import backlog_server as bs
from taskmaster_v3 import (
    read_entity_anywhere, write_entity_anywhere, set_entity_links,
)


@pytest.fixture
def tm_dir(tmp_path: Path, monkeypatch) -> Path:
    d = tmp_path / ".taskmaster"
    d.mkdir()
    (d / "backlog.yaml").write_text(yaml.safe_dump({
        "meta": {"schema_version": 3},
        "epics": [{"id": "e1", "title": "E", "tasks": [
            {"id": "T-001", "title": "First", "status": "todo"},
            {"id": "T-002", "title": "Second", "status": "todo"},
        ]}],
    }))
    for sub in ("handovers", "issues", "lessons", "ideas", "tasks"):
        (d / sub).mkdir()
    monkeypatch.setattr(bs, "_backlog_path", lambda: d / "backlog.yaml")
    return d


def test_validate_reports_orphan_target(tm_dir):
    # Hand-edit T-001 to link to a missing target.
    t1 = read_entity_anywhere(tm_dir / "backlog.yaml", "T-001")
    set_entity_links(t1, [{"type": "depends_on", "target": "T-999"}])
    write_entity_anywhere(tm_dir / "backlog.yaml", t1)

    out = bs.backlog_link_validate()
    data = json.loads(out)
    assert any(o["source"] == "T-001" and o["target"] == "T-999"
               for o in data["orphans"])


def test_validate_reports_asymmetric_pair(tm_dir):
    # Add depends_on on T-001 without inverse on T-002.
    t1 = read_entity_anywhere(tm_dir / "backlog.yaml", "T-001")
    set_entity_links(t1, [{"type": "depends_on", "target": "T-002"}])
    write_entity_anywhere(tm_dir / "backlog.yaml", t1)

    out = bs.backlog_link_validate()
    data = json.loads(out)
    assert any(a["source"] == "T-001" and a["target"] == "T-002"
               and a["missing_inverse"] == "blocks"
               for a in data["asymmetric"])


def test_validate_reports_cycles(tm_dir):
    t1 = read_entity_anywhere(tm_dir / "backlog.yaml", "T-001")
    set_entity_links(t1, [{"type": "depends_on", "target": "T-002"}])
    write_entity_anywhere(tm_dir / "backlog.yaml", t1)
    t2 = read_entity_anywhere(tm_dir / "backlog.yaml", "T-002")
    set_entity_links(t2, [{"type": "depends_on", "target": "T-001"}])
    write_entity_anywhere(tm_dir / "backlog.yaml", t2)

    out = bs.backlog_link_validate()
    data = json.loads(out)
    assert len(data["cycles"]) >= 1
    cycle = data["cycles"][0]
    assert set(cycle) >= {"T-001", "T-002"}


def test_validate_clean_returns_empty_arrays(tm_dir):
    bs.backlog_link_create(source="T-001", target="T-002", type="depends_on")
    out = bs.backlog_link_validate()
    data = json.loads(out)
    assert data["orphans"] == []
    assert data["asymmetric"] == []
    assert data["cycles"] == []


def test_validate_reports_archived_target_as_warning(tm_dir):
    # Spec §6B: if a target entity is archived/deleted, links to it are flagged
    # in backlog_validate but NOT auto-removed.
    from taskmaster_v3 import write_issue, read_entity_anywhere, write_entity_anywhere
    write_issue(tm_dir / "backlog.yaml", "ISS-001",
                {"id": "ISS-001", "tldr": "x", "severity": "P2", "status": "open"}, "Body.")
    bs.backlog_link_create(source="T-001", target="ISS-001", type="fixes")

    # Archive the issue by mutating its status field in place.
    iss = read_entity_anywhere(tm_dir / "backlog.yaml", "ISS-001")
    iss["status"] = "archived"
    write_entity_anywhere(tm_dir / "backlog.yaml", iss)

    out = bs.backlog_link_validate()
    data = json.loads(out)

    # The fixes link from T-001 to ISS-001 must still exist (not auto-removed).
    t1 = read_entity_anywhere(tm_dir / "backlog.yaml", "T-001")
    from taskmaster_v3 import entity_links
    assert {"type": "fixes", "target": "ISS-001"} in entity_links(t1)

    # The archived target must be reported as a warning — it must appear in
    # orphans (or a dedicated "archived_targets" list if the implementation adds one).
    # Minimum requirement: validate does NOT silently pass (no empty result).
    flagged_targets = {o["target"] for o in data.get("orphans", [])}
    flagged_targets |= {o["target"] for o in data.get("archived_targets", [])}
    assert "ISS-001" in flagged_targets, (
        "backlog_link_validate must flag links to archived entities as a warning"
    )
```

> **Implementation note for Task 11:** If archived issues remain in the same `.taskmaster/issues/` directory with `status: archived` in their frontmatter (the current convention), `iter_all_entities` already yields them — add an `archived_targets` check after the orphan scan, or include them in `orphans` with a `"reason": "archived"` annotation. Either is acceptable; the test above handles both shapes.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_backlog_link_validate.py -v`
Expected: FAIL — `AttributeError: ... backlog_link_validate`.

- [ ] **Step 3: Implement `backlog_link_validate`**

Add to `plugins/taskmaster/backlog_server.py`:

```python
@mcp.tool()
def backlog_link_validate() -> str:
    """Report link drift: orphan links, asymmetric pairs, depends_on cycles.

    Returns a JSON object {orphans: [...], asymmetric: [...], cycles: [...]}.
    """
    import json as _json
    from taskmaster_v3 import (
        REVERSE_TYPE, read_entity_anywhere, entity_links, load_v3, find_cycle,
    )

    backlog_path = _backlog_path()

    def iter_all_entities():
        data = load_v3(backlog_path)
        for epic in data.get("epics", []):
            for task in epic.get("tasks", []):
                if task.get("id"):
                    yield task["id"], task
        for sub, prefix in (("handovers", "HND"), ("issues", "ISS"),
                            ("lessons", "L"), ("ideas", "IDEA")):
            sub_dir = backlog_path.parent / sub
            if not sub_dir.exists():
                continue
            for fp in sub_dir.glob(f"{prefix}-*.md"):
                eid = fp.stem
                entity = read_entity_anywhere(backlog_path, eid)
                if entity is not None:
                    yield eid, entity

    orphans: list[dict] = []
    asymmetric: list[dict] = []
    depends_graph: dict[str, list[str]] = {}

    entities_by_id: dict[str, dict] = {}
    for eid, ent in iter_all_entities():
        entities_by_id[eid] = ent

    for eid, ent in entities_by_id.items():
        for link in entity_links(ent):
            tgt = link["target"]
            ltype = link["type"]
            if tgt not in entities_by_id:
                orphans.append({"source": eid, "target": tgt, "type": ltype})
                continue
            inverse = REVERSE_TYPE.get(ltype)
            if inverse is None:
                continue
            peer_links = entity_links(entities_by_id[tgt])
            if {"type": inverse, "target": eid} not in peer_links:
                asymmetric.append({"source": eid, "target": tgt, "type": ltype,
                                   "missing_inverse": inverse})
            if ltype == "depends_on":
                depends_graph.setdefault(eid, []).append(tgt)
                depends_graph.setdefault(tgt, depends_graph.get(tgt, []))

    cycles: list[list[str]] = []
    # Find up to 5 cycles by iteratively excising one node.
    graph_copy = {k: list(v) for k, v in depends_graph.items()}
    for _ in range(5):
        cyc = find_cycle(graph_copy)
        if cyc is None:
            break
        cycles.append(cyc)
        # Excise the first edge of the cycle to find further independent ones.
        if len(cyc) >= 2:
            a, b = cyc[0], cyc[1]
            if b in graph_copy.get(a, []):
                graph_copy[a].remove(b)

    return _json.dumps({"orphans": orphans, "asymmetric": asymmetric, "cycles": cycles})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_backlog_link_validate.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_backlog_link_validate.py
git commit -m "feat(taskmaster): backlog_link_validate MCP tool (orphans, asymmetric, cycles)"
```

---

### Task 12: `backlog_link_reconcile` MCP tool

**Files:**

- Modify: `plugins/taskmaster/backlog_server.py`
- Test: `plugins/taskmaster/tests/test_backlog_link_reconcile.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# plugins/taskmaster/tests/test_backlog_link_reconcile.py
from pathlib import Path
import json
import pytest
import yaml

import backlog_server as bs
from taskmaster_v3 import (
    read_entity_anywhere, write_entity_anywhere, set_entity_links, entity_links,
)


@pytest.fixture
def tm_dir(tmp_path: Path, monkeypatch) -> Path:
    d = tmp_path / ".taskmaster"
    d.mkdir()
    (d / "backlog.yaml").write_text(yaml.safe_dump({
        "meta": {"schema_version": 3},
        "epics": [{"id": "e1", "title": "E", "tasks": [
            {"id": "T-001", "title": "First", "status": "todo"},
            {"id": "T-002", "title": "Second", "status": "todo"},
        ]}],
    }))
    for sub in ("handovers", "issues", "lessons", "ideas", "tasks"):
        (d / sub).mkdir()
    monkeypatch.setattr(bs, "_backlog_path", lambda: d / "backlog.yaml")
    return d


def test_reconcile_adds_missing_inverse(tm_dir):
    t1 = read_entity_anywhere(tm_dir / "backlog.yaml", "T-001")
    set_entity_links(t1, [{"type": "depends_on", "target": "T-002"}])
    write_entity_anywhere(tm_dir / "backlog.yaml", t1)

    out = bs.backlog_link_reconcile()
    data = json.loads(out)
    assert data["fixed"] >= 1

    t2 = read_entity_anywhere(tm_dir / "backlog.yaml", "T-002")
    assert {"type": "blocks", "target": "T-001"} in entity_links(t2)


def test_reconcile_reports_unfixable_orphan(tm_dir):
    t1 = read_entity_anywhere(tm_dir / "backlog.yaml", "T-001")
    set_entity_links(t1, [{"type": "depends_on", "target": "T-999"}])
    write_entity_anywhere(tm_dir / "backlog.yaml", t1)

    out = bs.backlog_link_reconcile()
    data = json.loads(out)
    assert any(o["target"] == "T-999" for o in data["unfixable"])


def test_reconcile_idempotent(tm_dir):
    bs.backlog_link_create(source="T-001", target="T-002", type="depends_on")
    out1 = bs.backlog_link_reconcile()
    out2 = bs.backlog_link_reconcile()
    d1, d2 = json.loads(out1), json.loads(out2)
    assert d1["fixed"] == 0
    assert d2["fixed"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_backlog_link_reconcile.py -v`
Expected: FAIL — `AttributeError: ... backlog_link_reconcile`.

- [ ] **Step 3: Implement `backlog_link_reconcile`**

Add to `plugins/taskmaster/backlog_server.py`:

```python
@mcp.tool()
def backlog_link_reconcile() -> str:
    """Add missing inverse links on peers. Reports unfixable drift.

    Returns JSON {fixed: N, unfixable: [...]}.
    """
    import json as _json
    from taskmaster_v3 import sync_inverse

    validation = _json.loads(backlog_link_validate())
    fixed = 0
    unfixable: list[dict] = list(validation.get("orphans", []))
    backlog_path = _backlog_path()

    for entry in validation.get("asymmetric", []):
        try:
            sync_inverse(backlog_path,
                         source=entry["source"],
                         target=entry["target"],
                         type=entry["type"])
            fixed += 1
        except (KeyError, ValueError) as e:
            unfixable.append({**entry, "reason": str(e)})

    return _json.dumps({"fixed": fixed, "unfixable": unfixable,
                        "cycles": validation.get("cycles", [])})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_backlog_link_reconcile.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_backlog_link_reconcile.py
git commit -m "feat(taskmaster): backlog_link_reconcile MCP tool fixes asymmetric pairs"
```

---

## Phase 5 — Slim view integration

### Task 13: Grouped `links` block in slim `_get` views

**Files:**

- Modify: `plugins/taskmaster/backlog_server.py` (`backlog_get_task`, `backlog_handover_get`, `backlog_issue_get`, `backlog_lesson_get`, `backlog_idea_get`)
- Test: `plugins/taskmaster/tests/test_slim_links_grouped.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# plugins/taskmaster/tests/test_slim_links_grouped.py
from pathlib import Path
import pytest
import yaml

import backlog_server as bs


@pytest.fixture
def tm_dir(tmp_path: Path, monkeypatch) -> Path:
    d = tmp_path / ".taskmaster"
    d.mkdir()
    (d / "backlog.yaml").write_text(yaml.safe_dump({
        "meta": {"schema_version": 3},
        "epics": [{"id": "e1", "title": "E", "tasks": [
            {"id": "T-001", "title": "First", "tldr": "First task.", "status": "todo"},
            {"id": "T-002", "title": "Second", "tldr": "Second task.", "status": "todo"},
        ]}],
    }))
    for sub in ("handovers", "issues", "lessons", "ideas", "tasks"):
        (d / sub).mkdir()
    monkeypatch.setattr(bs, "_backlog_path", lambda: d / "backlog.yaml")
    bs.backlog_issue_create(title="Bug", severity="P1", tldr="Auth bug.",
                            body="repro steps")
    bs.backlog_link_create(source="T-001", target="T-002", type="depends_on")
    bs.backlog_link_create(source="T-001", target="ISS-001", type="fixes")
    return d


def test_slim_get_task_groups_links_by_type(tm_dir):
    out = bs.backlog_get_task("T-001")
    # Grouped block must be present with both types.
    assert "depends_on" in out
    assert "T-002" in out
    assert "fixes" in out
    assert "ISS-001" in out


def test_slim_get_task_no_expanded_tldrs_by_default(tm_dir):
    out = bs.backlog_get_task("T-001")
    # Default mode shows bare IDs, not the target tldrs.
    assert "Second task." not in out
    assert "Auth bug." not in out


def test_expand_links_swaps_ids_for_pills(tm_dir):
    out = bs.backlog_get_task("T-001", expand_links=True)
    # Expanded mode includes target tldrs.
    assert "Second task." in out
    assert "Auth bug." in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_slim_links_grouped.py -v`
Expected: FAIL — either `expand_links` is not a kwarg, or links block missing.

- [ ] **Step 3: Update slim view emitters**

Locate `backlog_get_task` (~L900 in `backlog_server.py`) and add `expand_links: bool = False` to its signature. In the slim-output assembly, replace any per-field linkage rendering with a single grouped block driven by `links_grouped_by_type()`:

```python
# inside backlog_get_task, after computing slim frontmatter:
from taskmaster_v3 import links_grouped_by_type, read_entity_anywhere

grouped = links_grouped_by_type(task)
if grouped:
    lines.append("links:")
    for ltype in sorted(grouped):
        targets = grouped[ltype]
        if expand_links:
            pills = []
            for tgt in targets:
                peer = read_entity_anywhere(backlog_path, tgt)
                tldr = (peer or {}).get("tldr", "") if peer else ""
                pills.append(f"{tgt} ({tldr})" if tldr else tgt)
            lines.append(f"  {ltype}: [{', '.join(pills)}]")
        else:
            lines.append(f"  {ltype}: [{', '.join(targets)}]")
```

Apply the same pattern in `backlog_handover_get`, `backlog_issue_get`, `backlog_lesson_get`, `backlog_idea_get` — each takes a new `expand_links: bool = False` kwarg, emits the grouped block, and never emits the old `related_*` fields when `links` is present (the migration drops them).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_slim_links_grouped.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_slim_links_grouped.py
git commit -m "feat(taskmaster): slim _get views emit grouped links block (expand_links pills)"
```

---

### Task 14: Hook `auto_link_on_save` into entity write paths

**Files:**

- Modify: `plugins/taskmaster/backlog_server.py` (`backlog_handover_create`, `backlog_issue_create`, `backlog_issue_update`, `backlog_lesson_create`, `backlog_lesson_update`, `backlog_idea_create`, `backlog_idea_update`, `backlog_update_task`)
- Test: extend `plugins/taskmaster/tests/test_auto_link_on_save.py`

- [ ] **Step 1: Write the failing test**

Append to `plugins/taskmaster/tests/test_auto_link_on_save.py`:

```python
def test_handover_create_auto_links_on_save(tm_dir, monkeypatch):
    import backlog_server as bs
    monkeypatch.setattr(bs, "_backlog_path", lambda: tm_dir / "backlog.yaml")

    bs.backlog_handover_create(task_ids=["T-001"], tldr="x", next_action="",
                               body="Next: pick up T-005.")
    hnd = read_entity_anywhere(tm_dir / "backlog.yaml", "HND-001")
    assert {"type": "references", "target": "T-005"} in entity_links(hnd)
    t5 = read_entity_anywhere(tm_dir / "backlog.yaml", "T-005")
    assert {"type": "referenced_by", "target": "HND-001"} in entity_links(t5)


def test_issue_create_auto_links_on_save(tm_dir, monkeypatch):
    import backlog_server as bs
    monkeypatch.setattr(bs, "_backlog_path", lambda: tm_dir / "backlog.yaml")
    bs.backlog_issue_create(title="Bug", severity="P1", tldr="x",
                            body="Related: T-001 and T-005.")
    iss = read_entity_anywhere(tm_dir / "backlog.yaml", "ISS-001")
    targets = {link["target"] for link in entity_links(iss)
               if link["type"] == "references"}
    assert {"T-001", "T-005"}.issubset(targets)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_auto_link_on_save.py::test_handover_create_auto_links_on_save -v`
Expected: FAIL — writers don't yet call `auto_link_on_save`.

- [ ] **Step 3: Wire the hook**

In each entity-creating/updating MCP tool in `backlog_server.py`, immediately after the final write helper (`write_handover` / `write_issue` / `write_lesson` / `write_idea` / `save_v3` for tasks), add:

```python
from taskmaster_v3 import auto_link_on_save
auto_link_on_save(backlog_path, new_id)   # new_id = the entity's ID
```

For task updates (`backlog_update_task`, `backlog_add_task`), pass the task's `id`. Tasks have body content in `notes`/`review_instructions`/`docs.*` — `auto_link_on_save` reads `entity[BODY_KEY]`; for tasks, also concatenate any of those text fields into a synthetic body for scanning. Add a helper:

```python
def _task_scan_text(task: dict) -> str:
    parts: list[str] = []
    if task.get("notes"): parts.append(task["notes"])
    if task.get("review_instructions"): parts.append(task["review_instructions"])
    return "\n\n".join(parts)
```

Then update `auto_link_on_save` (in `taskmaster_v3.py`) to use this concatenation when `entity_kind_of(entity_id) == "task"`:

```python
# replace `body = entity.get(BODY_KEY, "") or ""` with:
if entity_kind_of(entity_id) == "task":
    body = "\n\n".join(filter(None, [
        entity.get("notes") or "", entity.get("review_instructions") or "",
    ]))
else:
    body = entity.get(BODY_KEY, "") or ""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_auto_link_on_save.py -v`
Expected: 8 passed (6 existing + 2 new).

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/backlog_server.py plugins/taskmaster/tests/test_auto_link_on_save.py
git commit -m "feat(taskmaster): hook auto_link_on_save into every entity write path"
```

---

## Phase 6 — Migration

### Task 15: `legacy_links_to_typed()` — field-by-field translator

**Files:**

- Modify: `plugins/taskmaster/taskmaster_v3.py`
- Test: `plugins/taskmaster/tests/test_link_migration.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# plugins/taskmaster/tests/test_link_migration.py
from taskmaster_v3 import legacy_links_to_typed


def test_task_legacy_fields_translate():
    task = {
        "id": "T-001",
        "depends_on": ["T-002", "T-003"],
        "related_issues": ["ISS-007"],
        "related_lessons": ["L-003"],
    }
    links = legacy_links_to_typed(task, kind="task")
    assert {"type": "depends_on",  "target": "T-002"} in links
    assert {"type": "depends_on",  "target": "T-003"} in links
    assert {"type": "relates_to",  "target": "ISS-007"} in links
    assert {"type": "informed_by", "target": "L-003"}  in links


def test_issue_legacy_fields_translate():
    issue = {
        "id": "ISS-001",
        "related_tasks": ["T-001"],
        "fixed_in_task": "T-005",
        "duplicate_of": "ISS-002",
    }
    links = legacy_links_to_typed(issue, kind="issue")
    assert {"type": "relates_to",    "target": "T-001"}   in links
    assert {"type": "fixed_in_task", "target": "T-005"}   in links
    assert {"type": "duplicate_of",  "target": "ISS-002"} in links


def test_lesson_legacy_fields_translate():
    lesson = {
        "id": "L-001",
        "related_tasks": ["T-001"],
        "related_issues": ["ISS-007"],
    }
    links = legacy_links_to_typed(lesson, kind="lesson")
    assert {"type": "informs",    "target": "T-001"}   in links
    assert {"type": "relates_to", "target": "ISS-007"} in links


def test_handover_legacy_fields_translate():
    handover = {
        "id": "HND-002",
        "supersedes": ["HND-001"],
        "superseded_by": ["HND-003"],
    }
    links = legacy_links_to_typed(handover, kind="handover")
    assert {"type": "supersedes",    "target": "HND-001"} in links
    assert {"type": "superseded_by", "target": "HND-003"} in links


def test_existing_links_are_preserved():
    task = {
        "id": "T-001",
        "depends_on": ["T-002"],
        "links": [{"type": "fixes", "target": "ISS-007"}],
    }
    links = legacy_links_to_typed(task, kind="task")
    assert {"type": "fixes",      "target": "ISS-007"} in links
    assert {"type": "depends_on", "target": "T-002"}   in links


def test_dedupes_when_legacy_and_links_overlap():
    task = {
        "id": "T-001",
        "depends_on": ["T-002"],
        "links": [{"type": "depends_on", "target": "T-002"}],
    }
    links = legacy_links_to_typed(task, kind="task")
    assert links.count({"type": "depends_on", "target": "T-002"}) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_link_migration.py -v`
Expected: FAIL — `ImportError: cannot import name 'legacy_links_to_typed'`.

- [ ] **Step 3: Implement the translator**

Append to `plugins/taskmaster/taskmaster_v3.py`:

```python
# Per-kind legacy field → typed link mapping.
# (field_name, link_type, value_is_list) tuples per entity kind.
_LEGACY_LINK_RULES: dict[str, tuple[tuple[str, str, bool], ...]] = {
    "task": (
        ("depends_on",      "depends_on",  True),
        ("related_issues",  "relates_to",  True),
        ("related_lessons", "informed_by", True),
    ),
    "issue": (
        ("related_tasks",  "relates_to",    True),
        ("fixed_in_task",  "fixed_in_task", False),
        ("duplicate_of",   "duplicate_of",  False),
    ),
    "lesson": (
        ("related_tasks",  "informs",    True),
        ("related_issues", "relates_to", True),
    ),
    "handover": (
        ("supersedes",     "supersedes",    True),
        ("superseded_by",  "superseded_by", True),
    ),
    "idea": (
        ("related_tasks", "relates_to", True),
    ),
}


def legacy_links_to_typed(entity: dict, kind: str) -> list[dict]:
    """Translate legacy linkage fields on `entity` into a typed `links` array.

    Existing `entity['links']` entries are preserved. The output is deduped.
    Does not mutate the entity in place — caller decides when to assign.
    """
    out: list[dict] = list(entity_links(entity))
    seen = {(link["type"], link["target"]) for link in out}
    rules = _LEGACY_LINK_RULES.get(kind, ())
    for field, link_type, is_list in rules:
        raw = entity.get(field)
        if raw is None or raw == [] or raw == "":
            continue
        targets = raw if is_list else [raw]
        for tgt in targets:
            if not tgt:
                continue
            key = (link_type, tgt)
            if key in seen:
                continue
            seen.add(key)
            out.append({"type": link_type, "target": tgt})
    return out


_LEGACY_FIELDS_TO_DROP: dict[str, tuple[str, ...]] = {
    "task":     ("depends_on", "related_issues", "related_lessons"),
    "issue":    ("related_tasks", "fixed_in_task", "duplicate_of"),
    "lesson":   ("related_tasks", "related_issues"),
    "handover": ("supersedes", "superseded_by"),
    "idea":     ("related_tasks",),
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_link_migration.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_link_migration.py
git commit -m "feat(taskmaster): legacy_links_to_typed() translates old linkage fields"
```

---

### Task 16: One-shot migration script `scripts/migrate_links.py`

**Prerequisite:** Requires `plugins/__init__.py` and `plugins/taskmaster/__init__.py` package markers (created by Plan A Task 0, or manually in Task 0 of this plan). The script runs via `python -m plugins.taskmaster.scripts.migrate_links` — Python resolves `plugins` as a package, which requires these markers. If shipping Plan C before Plan A, create the markers first (Task 0 handles this).

**Files:**

- Create: `plugins/taskmaster/scripts/migrate_links.py`
- Test: extend `plugins/taskmaster/tests/test_link_migration.py`

- [ ] **Step 1: Write the failing test**

Append to `plugins/taskmaster/tests/test_link_migration.py`:

```python
from pathlib import Path
import subprocess
import sys
import yaml

from taskmaster_v3 import (
    read_entity_anywhere, entity_links, write_issue, write_handover,
)


def _seed_project(tmp_path: Path) -> Path:
    d = tmp_path / ".taskmaster"
    d.mkdir()
    (d / "backlog.yaml").write_text(yaml.safe_dump({
        "meta": {"schema_version": 3},
        "epics": [{"id": "e1", "title": "E", "tasks": [
            {"id": "T-001", "title": "First", "status": "todo",
             "depends_on": ["T-002"], "related_issues": ["ISS-001"]},
            {"id": "T-002", "title": "Second", "status": "todo"},
        ]}],
    }))
    for sub in ("handovers", "issues", "lessons", "ideas", "tasks"):
        (d / sub).mkdir()
    write_issue(d / "backlog.yaml", "ISS-001",
                {"id": "ISS-001", "tldr": "x", "severity": "P2",
                 "status": "open", "fixed_in_task": "T-005"},
                "Body.")
    return d


def test_migrate_links_script_translates_legacy_fields(tmp_path):
    tm_dir = _seed_project(tmp_path)
    result = subprocess.run(
        [sys.executable, "-m", "plugins.taskmaster.scripts.migrate_links",
         "--root", str(tm_dir.parent)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr

    t1 = read_entity_anywhere(tm_dir / "backlog.yaml", "T-001")
    assert {"type": "depends_on", "target": "T-002"} in entity_links(t1)
    assert {"type": "relates_to", "target": "ISS-001"} in entity_links(t1)

    iss = read_entity_anywhere(tm_dir / "backlog.yaml", "ISS-001")
    assert {"type": "fixed_in_task", "target": "T-005"} in entity_links(iss)


def test_migrate_links_is_idempotent(tmp_path):
    tm_dir = _seed_project(tmp_path)
    for _ in range(2):
        result = subprocess.run(
            [sys.executable, "-m", "plugins.taskmaster.scripts.migrate_links",
             "--root", str(tm_dir.parent)],
            capture_output=True, text=True, check=False,
        )
        assert result.returncode == 0

    t1 = read_entity_anywhere(tm_dir / "backlog.yaml", "T-001")
    # Only one of each link type/target after re-runs.
    assert entity_links(t1).count({"type": "depends_on", "target": "T-002"}) == 1


def test_migrate_links_adds_inverses(tmp_path):
    tm_dir = _seed_project(tmp_path)
    subprocess.run(
        [sys.executable, "-m", "plugins.taskmaster.scripts.migrate_links",
         "--root", str(tm_dir.parent)],
        check=True,
    )
    t2 = read_entity_anywhere(tm_dir / "backlog.yaml", "T-002")
    assert {"type": "blocks", "target": "T-001"} in entity_links(t2)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_link_migration.py::test_migrate_links_script_translates_legacy_fields -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write the migration script**

Create `plugins/taskmaster/scripts/migrate_links.py`:

```python
"""Translate legacy linkage fields → typed `links` arrays.

One-shot, idempotent. Walks every entity (tasks, handovers, issues,
lessons, ideas) under <root>/.taskmaster/, calls legacy_links_to_typed
to produce the new array, writes it back, then runs
`backlog_link_reconcile` to fill in any missing inverses.

Usage:
    python -m plugins.taskmaster.scripts.migrate_links --root <project_root>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Invoked via `python -m plugins.taskmaster.scripts.migrate_links` from repo root;
# package imports are valid here. Requires plugins/__init__.py and
# plugins/taskmaster/__init__.py (created by Plan A Task 0).
from plugins.taskmaster.taskmaster_v3 import (
    load_v3, save_v3,
    read_entity_anywhere, write_entity_anywhere,
    legacy_links_to_typed, set_entity_links,
    _LEGACY_FIELDS_TO_DROP,
    entity_links,
)


def _migrate_one(entity: dict, kind: str, *, drop_legacy: bool) -> tuple[bool, int]:
    """Return (changed, added_count)."""
    before = entity_links(entity)
    after = legacy_links_to_typed(entity, kind=kind)
    if drop_legacy:
        for field in _LEGACY_FIELDS_TO_DROP.get(kind, ()):
            entity.pop(field, None)
    if after != before:
        set_entity_links(entity, after)
        return True, len(after) - len(before)
    return False, 0


def migrate(root: Path, *, drop_legacy: bool = True) -> dict:
    backlog_path = root / ".taskmaster" / "backlog.yaml"
    if not backlog_path.exists():
        raise SystemExit(f"no backlog.yaml at {backlog_path}")

    counts = {"tasks": 0, "issues": 0, "lessons": 0, "handovers": 0, "ideas": 0}

    # Tasks via load_v3/save_v3.
    data = load_v3(backlog_path)
    for epic in data.get("epics", []):
        for task in epic.get("tasks", []):
            changed, _ = _migrate_one(task, kind="task", drop_legacy=drop_legacy)
            if changed:
                counts["tasks"] += 1
    save_v3(backlog_path, data)

    for sub, prefix, kind in (
        ("handovers", "HND",  "handover"),
        ("issues",    "ISS",  "issue"),
        ("lessons",   "L",    "lesson"),
        ("ideas",     "IDEA", "idea"),
    ):
        sub_dir = backlog_path.parent / sub
        if not sub_dir.exists():
            continue
        for fp in sorted(sub_dir.glob(f"{prefix}-*.md")):
            eid = fp.stem
            entity = read_entity_anywhere(backlog_path, eid)
            if entity is None:
                continue
            changed, _ = _migrate_one(entity, kind=kind, drop_legacy=drop_legacy)
            if changed:
                write_entity_anywhere(backlog_path, entity)
                counts[sub] += 1

    # Reconcile inverses.
    from plugins.taskmaster import backlog_server as bs
    import contextlib

    original = bs._backlog_path
    try:
        bs._backlog_path = lambda: backlog_path  # type: ignore[assignment]
        report = json.loads(bs.backlog_link_reconcile())
    finally:
        bs._backlog_path = original

    return {"migrated": counts, "reconcile": report}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="Project root containing .taskmaster/")
    parser.add_argument("--keep-legacy", action="store_true",
                        help="Keep old linkage fields in addition to writing 'links'.")
    args = parser.parse_args(argv)

    summary = migrate(Path(args.root), drop_legacy=not args.keep_legacy)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Also create `plugins/taskmaster/scripts/__init__.py` if it doesn't exist:

```python
# Marker file.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_link_migration.py -v`
Expected: 9 passed (6 unit + 3 script).

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/scripts/migrate_links.py plugins/taskmaster/scripts/__init__.py plugins/taskmaster/tests/test_link_migration.py
git commit -m "feat(taskmaster): one-shot migrate_links.py — legacy fields → typed links + reconcile"
```

---

### Task 17: Read-fallback shim so legacy projects still load

**Files:**

- Modify: `plugins/taskmaster/taskmaster_v3.py` (extend `load_v3` post-merge, and per-entity readers)
- Test: extend `plugins/taskmaster/tests/test_link_migration.py`

- [ ] **Step 1: Write the failing test**

Append to `plugins/taskmaster/tests/test_link_migration.py`:

```python
def test_read_fallback_synthesizes_links_when_absent(tmp_path):
    # Project that has only legacy fields, no `links` array yet.
    d = tmp_path / ".taskmaster"
    d.mkdir()
    (d / "backlog.yaml").write_text(yaml.safe_dump({
        "meta": {"schema_version": 3},
        "epics": [{"id": "e1", "title": "E", "tasks": [
            {"id": "T-001", "title": "First", "status": "todo",
             "depends_on": ["T-002"]},
            {"id": "T-002", "title": "Second", "status": "todo"},
        ]}],
    }))
    for sub in ("handovers", "issues", "lessons", "ideas", "tasks"):
        (d / sub).mkdir()

    t1 = read_entity_anywhere(d / "backlog.yaml", "T-001")
    # The link should be visible via the new accessor even without migration.
    assert {"type": "depends_on", "target": "T-002"} in entity_links(t1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest plugins/taskmaster/tests/test_link_migration.py::test_read_fallback_synthesizes_links_when_absent -v`
Expected: FAIL — `entity_links` returns `[]` because legacy `depends_on` isn't normalized.

- [ ] **Step 3: Wire the shim**

Modify `read_entity_anywhere` in `plugins/taskmaster/taskmaster_v3.py` to populate a virtual `links` array when the field is missing but legacy fields are present. Add right before returning:

```python
def _fallback_links_if_absent(entity: dict, kind: str) -> None:
    if entity.get(LINK_FIELD):
        return
    synthesized = legacy_links_to_typed(entity, kind=kind)
    if synthesized:
        entity[LINK_FIELD] = synthesized
```

Then in `read_entity_anywhere`:

```python
# Before returning the loaded entity:
_fallback_links_if_absent(entity, kind)
return entity
```

For the task branch, populate the same way after finding the task. The fallback is read-only — it does not write back; the migration script is the only path that persists.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest plugins/taskmaster/tests/test_link_migration.py -v`
Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/taskmaster_v3.py plugins/taskmaster/tests/test_link_migration.py
git commit -m "feat(taskmaster): read-fallback synthesizes links from legacy fields when absent"
```

---

## Phase 7 — Viewer update

### Task 18: Shared `link-pills.js` renderer

**Files:**

- Create: `plugins/taskmaster/viewer/js/components/link-pills.js`

- [ ] **Step 1: Write the component**

Create `plugins/taskmaster/viewer/js/components/link-pills.js`:

```javascript
// Render a grouped links block from an entity's `links` array.
// Shape: entity.links = [{type, target}, ...]
// Renders one row per type, with pill chips for each target.

const TYPE_LABELS = {
  depends_on:    "Depends on",
  blocks:        "Blocks",
  fixes:         "Fixes",
  fixed_in_task: "Fixed in",
  relates_to:    "Related",
  informed_by:   "Informed by",
  informs:       "Informs",
  supersedes:    "Supersedes",
  superseded_by: "Superseded by",
  duplicate_of:  "Duplicate of",
  duplicates:    "Duplicates",
  references:    "References",
  referenced_by: "Referenced by",
};

function groupByType(links) {
  const out = {};
  for (const link of links || []) {
    if (!out[link.type]) out[link.type] = [];
    out[link.type].push(link.target);
  }
  return out;
}

export function renderLinkPills(entity, opts = {}) {
  const links = entity.links || [];
  if (links.length === 0) return "";
  const grouped = groupByType(links);
  const typeOrder = Object.keys(TYPE_LABELS).filter((t) => grouped[t]);

  const rows = typeOrder.map((type) => {
    const label = TYPE_LABELS[type] || type;
    const chips = grouped[type]
      .map((target) => `<a class="link-pill link-pill-${type}" href="#${target}">${target}</a>`)
      .join(" ");
    return `<div class="link-row"><span class="link-label">${label}</span>${chips}</div>`;
  });
  return `<div class="link-pills">${rows.join("")}</div>`;
}

export function legacyLinksToTyped(entity, kind) {
  // Mirror of the Python translator — used by the viewer when reading
  // pre-migration projects that haven't run migrate_links.py yet.
  const out = [...(entity.links || [])];
  const seen = new Set(out.map((l) => `${l.type}:${l.target}`));
  const push = (type, target) => {
    if (!target) return;
    const key = `${type}:${target}`;
    if (seen.has(key)) return;
    seen.add(key);
    out.push({ type, target });
  };
  const rules = {
    task: [
      ["depends_on", "depends_on", true],
      ["related_issues", "relates_to", true],
      ["related_lessons", "informed_by", true],
    ],
    issue: [
      ["related_tasks", "relates_to", true],
      ["fixed_in_task", "fixed_in_task", false],
      ["duplicate_of", "duplicate_of", false],
    ],
    lesson: [
      ["related_tasks", "informs", true],
      ["related_issues", "relates_to", true],
    ],
    handover: [
      ["supersedes", "supersedes", true],
      ["superseded_by", "superseded_by", true],
    ],
    idea: [["related_tasks", "relates_to", true]],
  };
  for (const [field, type, isList] of rules[kind] || []) {
    const raw = entity[field];
    if (raw == null || raw === "" || (Array.isArray(raw) && raw.length === 0)) continue;
    const targets = isList ? raw : [raw];
    for (const t of targets) push(type, t);
  }
  return out;
}
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/components/link-pills.js
git commit -m "feat(viewer): shared link-pills renderer with legacy field fallback"
```

---

### Task 19: Update `task-detail.js` to use `link-pills`

**Files:**

- Modify: `plugins/taskmaster/viewer/js/screens/task-detail.js`

- [ ] **Step 1: Locate the existing linkage rendering**

Open `plugins/taskmaster/viewer/js/screens/task-detail.js`. Find the block that renders `task.depends_on` / `task.related_issues` / `task.related_lessons` (likely as separate "Dependencies" / "Related" sections).

- [ ] **Step 2: Replace with `renderLinkPills`**

Replace those blocks with a single import and call:

```javascript
import { renderLinkPills, legacyLinksToTyped } from "../components/link-pills.js";

// In the render function, where linkages were previously emitted:
const links = task.links && task.links.length
  ? task.links
  : legacyLinksToTyped(task, "task");
const linkBlockHTML = renderLinkPills({ ...task, links });

// Insert linkBlockHTML where the legacy sections used to live.
```

Drop the old separate-section rendering for `depends_on` / `related_issues` / `related_lessons` — the grouped block replaces all three.

- [ ] **Step 3: Manual sanity check**

Start the viewer (`python plugins/taskmaster/viewer/server.py` or however it's launched locally) and open a task that has at least one `depends_on` and one `related_issue` set. Confirm:
- Both link types render as labeled rows.
- Each target is a clickable pill.
- No "Dependencies" + "Related" sections duplicate the same data.

- [ ] **Step 4: Commit**

```bash
git add plugins/taskmaster/viewer/js/screens/task-detail.js
git commit -m "feat(viewer): task-detail uses unified link-pills renderer"
```

---

### Task 20: Update `issue-detail.js` to use `link-pills`

**Files:**

- Modify: `plugins/taskmaster/viewer/js/screens/issue-detail.js`

- [ ] **Step 1: Locate the existing linkage rendering**

Find blocks rendering `issue.related_tasks` / `issue.fixed_in_task` / `issue.duplicate_of`.

- [ ] **Step 2: Replace with `renderLinkPills`**

```javascript
import { renderLinkPills, legacyLinksToTyped } from "../components/link-pills.js";

const links = issue.links && issue.links.length
  ? issue.links
  : legacyLinksToTyped(issue, "issue");
const linkBlockHTML = renderLinkPills({ ...issue, links });
```

Drop the legacy field-specific sections.

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/viewer/js/screens/issue-detail.js
git commit -m "feat(viewer): issue-detail uses unified link-pills renderer"
```

---

### Task 21: Update `lesson-detail.js` to use `link-pills`

**Files:**

- Modify: `plugins/taskmaster/viewer/js/screens/lesson-detail.js`

- [ ] **Step 1: Locate and replace**

Find blocks rendering `lesson.related_tasks` / `lesson.related_issues`. Replace with the same pattern as Tasks 19–20 (`kind: "lesson"`).

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/screens/lesson-detail.js
git commit -m "feat(viewer): lesson-detail uses unified link-pills renderer"
```

---

### Task 22: Update `issues.js` and `ideas.js` for badge counts

**Files:**

- Modify: `plugins/taskmaster/viewer/js/screens/issues.js`
- Modify: `plugins/taskmaster/viewer/js/screens/ideas.js`

- [ ] **Step 1: Replace badge-count helpers**

In each screen, find any reference to `related_issues` / `related_tasks` / `related_lessons` used for "X related items" badges. Replace with:

```javascript
import { legacyLinksToTyped } from "../components/link-pills.js";

function relatedCount(entity, kind) {
  const links = entity.links && entity.links.length
    ? entity.links
    : legacyLinksToTyped(entity, kind);
  return links.length;
}
```

Use `relatedCount(issue, "issue")` and `relatedCount(idea, "idea")` for the badge rendering.

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/viewer/js/screens/issues.js plugins/taskmaster/viewer/js/screens/ideas.js
git commit -m "feat(viewer): issues/ideas list screens count typed links for badges"
```

---

## Phase 8 — Smoke test and changelog

### Task 23: Full integration smoke test

**Files:**

- Create: `plugins/taskmaster/tests/test_links_smoke.py`

- [ ] **Step 1: Write the smoke test**

```python
# plugins/taskmaster/tests/test_links_smoke.py
"""End-to-end Plan C smoke test:
- create-link-query-remove across all entity kinds
- cycle prevention
- symmetric sync
- auto-detection on save
- migration from a fully-legacy project
"""
from pathlib import Path
import json
import subprocess
import sys
import pytest
import yaml

import backlog_server as bs
from taskmaster_v3 import (
    read_entity_anywhere, entity_links,
)


@pytest.fixture
def tm_dir(tmp_path: Path, monkeypatch) -> Path:
    d = tmp_path / ".taskmaster"
    d.mkdir()
    (d / "backlog.yaml").write_text(yaml.safe_dump({
        "meta": {"schema_version": 3},
        "epics": [{"id": "e1", "title": "E", "tasks": [
            {"id": "T-001", "title": "First",  "tldr": "x", "status": "todo"},
            {"id": "T-002", "title": "Second", "tldr": "x", "status": "todo"},
            {"id": "T-003", "title": "Third",  "tldr": "x", "status": "todo"},
        ]}],
    }))
    for sub in ("handovers", "issues", "lessons", "ideas", "tasks"):
        (d / sub).mkdir()
    monkeypatch.setattr(bs, "_backlog_path", lambda: d / "backlog.yaml")
    return d


def test_create_link_query_remove_round_trip(tm_dir):
    # Create one of each non-task entity.
    bs.backlog_issue_create(title="Bug", severity="P1", tldr="x", body="body")
    bs.backlog_lesson_create(title="L", kind="pattern", tldr="x",
                             why="w", what_to_do="d")
    bs.backlog_handover_create(task_ids=["T-001"], tldr="x", next_action="", body="b")
    bs.backlog_idea_create(title="I", tldr="x", body="b")

    # All link types we can validate.
    pairs = [
        ("T-001", "T-002",  "depends_on",  "blocks"),
        ("T-001", "ISS-001", "fixes",        "fixed_in_task"),
        ("T-001", "L-001",   "informed_by",  "informs"),
        ("T-001", "ISS-001", "relates_to",   "relates_to"),
        ("T-001", "HND-001", "references",   "referenced_by"),
        ("T-001", "IDEA-001","relates_to",   "relates_to"),
    ]
    for src, dst, t, inv in pairs:
        out = bs.backlog_link_create(source=src, target=dst, type=t)
        assert "ok" in out.lower(), out
        src_e = read_entity_anywhere(tm_dir / "backlog.yaml", src)
        dst_e = read_entity_anywhere(tm_dir / "backlog.yaml", dst)
        assert {"type": t,   "target": dst} in entity_links(src_e)
        assert {"type": inv, "target": src} in entity_links(dst_e)

    # Query and remove.
    q = json.loads(bs.backlog_link_query(source="T-001"))
    assert len(q) >= len(pairs)
    for src, dst, t, _ in pairs:
        bs.backlog_link_remove(source=src, target=dst, type=t)
        src_e = read_entity_anywhere(tm_dir / "backlog.yaml", src)
        assert {"type": t, "target": dst} not in entity_links(src_e)


def test_cycle_prevention_blocks_3_node(tm_dir):
    bs.backlog_link_create(source="T-001", target="T-002", type="depends_on")
    bs.backlog_link_create(source="T-002", target="T-003", type="depends_on")
    out = bs.backlog_link_create(source="T-003", target="T-001", type="depends_on")
    assert "cycle" in out.lower()


def test_auto_detection_e2e(tm_dir):
    bs.backlog_handover_create(task_ids=["T-001"], tldr="x", next_action="",
                               body="Picked up T-001, next start T-002, also see T-003.")
    hnd = read_entity_anywhere(tm_dir / "backlog.yaml", "HND-001")
    targets = {l["target"] for l in entity_links(hnd) if l["type"] == "references"}
    # T-001 is in task_ids and self-referenced from body but T-001 is the explicit anchor,
    # not the handover itself, so it materializes as a reference too.
    assert {"T-002", "T-003"}.issubset(targets)


def test_validate_clean_after_create(tm_dir):
    bs.backlog_link_create(source="T-001", target="T-002", type="depends_on")
    bs.backlog_link_create(source="T-001", target="T-003", type="depends_on")
    data = json.loads(bs.backlog_link_validate())
    assert data["orphans"] == []
    assert data["asymmetric"] == []
    assert data["cycles"] == []


def test_migration_from_legacy_project(tmp_path):
    # Build a project with ONLY legacy fields.
    d = tmp_path / ".taskmaster"
    d.mkdir()
    (d / "backlog.yaml").write_text(yaml.safe_dump({
        "meta": {"schema_version": 3},
        "epics": [{"id": "e1", "title": "E", "tasks": [
            {"id": "T-001", "title": "A", "status": "todo",
             "depends_on": ["T-002"], "related_issues": ["ISS-001"]},
            {"id": "T-002", "title": "B", "status": "todo"},
        ]}],
    }))
    for sub in ("handovers", "issues", "lessons", "ideas", "tasks"):
        (d / sub).mkdir()
    from taskmaster_v3 import write_issue
    write_issue(d / "backlog.yaml", "ISS-001",
                {"id": "ISS-001", "tldr": "x", "severity": "P2",
                 "status": "open", "fixed_in_task": "T-001"}, "body")

    result = subprocess.run(
        [sys.executable, "-m", "plugins.taskmaster.scripts.migrate_links",
         "--root", str(d.parent)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr

    t1 = read_entity_anywhere(d / "backlog.yaml", "T-001")
    assert {"type": "depends_on", "target": "T-002"} in entity_links(t1)
    assert {"type": "relates_to", "target": "ISS-001"} in entity_links(t1)
    assert "depends_on" not in t1  # legacy field dropped
    assert "related_issues" not in t1

    # Inverses materialized.
    t2 = read_entity_anywhere(d / "backlog.yaml", "T-002")
    assert {"type": "blocks", "target": "T-001"} in entity_links(t2)

    iss = read_entity_anywhere(d / "backlog.yaml", "ISS-001")
    assert {"type": "fixed_in_task", "target": "T-001"} in entity_links(iss)
    assert {"type": "fixes",         "target": "ISS-001"} in entity_links(t1)
    assert "fixed_in_task" not in iss  # legacy field dropped


def test_full_plan_c_test_suite_passes():
    # Sanity check: the dedicated Plan C test files all pass together.
    result = subprocess.run(
        [sys.executable, "-m", "pytest",
         "plugins/taskmaster/tests/test_link_types.py",
         "plugins/taskmaster/tests/test_link_helpers.py",
         "plugins/taskmaster/tests/test_link_cycle_detection.py",
         "plugins/taskmaster/tests/test_link_inverse_sync.py",
         "plugins/taskmaster/tests/test_inline_ref_extraction.py",
         "plugins/taskmaster/tests/test_auto_link_on_save.py",
         "plugins/taskmaster/tests/test_backlog_link_create.py",
         "plugins/taskmaster/tests/test_backlog_link_remove.py",
         "plugins/taskmaster/tests/test_backlog_link_query.py",
         "plugins/taskmaster/tests/test_backlog_link_validate.py",
         "plugins/taskmaster/tests/test_backlog_link_reconcile.py",
         "plugins/taskmaster/tests/test_slim_links_grouped.py",
         "plugins/taskmaster/tests/test_link_migration.py",
         "-q"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
```

- [ ] **Step 2: Run smoke test**

Run: `pytest plugins/taskmaster/tests/test_links_smoke.py -v`
Expected: 6 passed.

- [ ] **Step 3: Run the entire test suite for regressions**

Run: `pytest plugins/taskmaster/tests/ -v`
Expected: All passing. Pre-existing tests that referenced legacy field names (`related_issues`, etc.) on a freshly-created entity will still pass because the read-fallback shim (Task 17) synthesizes the typed `links` view without dropping the legacy fields until migration runs.

- [ ] **Step 4: Commit**

```bash
git add plugins/taskmaster/tests/test_links_smoke.py
git commit -m "test(taskmaster): end-to-end Plan C smoke test (all entity kinds + migration)"
```

---

### Task 24: Changelog entry

**Files:**

- Modify: `plugins/taskmaster/CHANGELOG.md`

- [ ] **Step 1: Add changelog entry**

Append to `plugins/taskmaster/CHANGELOG.md` under an unreleased v3.X section (or extend an existing one if Plan A landed first):

```markdown
## v3.X — Programmatic Linking (2026-05-XX)

### Added
- Typed unified `links: [{type, target}]` schema on every entity (tasks, issues, lessons, handovers, ideas). Replaces `related_issues`, `related_lessons`, `depends_on`, `fixed_in_task`, `duplicate_of`, `supersedes`, `superseded_by`.
- 13 canonical link types with full reverse-pair table — see `plugins/taskmaster/taskmaster_v3.py::REVERSE_TYPE`.
- Server-managed symmetric sync: writing a link on one side auto-writes the inverse on the peer.
- Auto-detection of inline ID mentions (`T-001`, `[[T-001]]`, `@T-001`) on every entity save — materializes as `references` links. Opt out per entity via `auto_link: false` frontmatter.
- Cycle detection on `depends_on` chains — `backlog_link_create` rejects writes that would form self-cycles, 2-node, or N-node cycles.
- New MCP tools:
  - `backlog_link_create(source, target, type, note="")`
  - `backlog_link_remove(source, target, type="")`
  - `backlog_link_query(source="", target="", type="", depth=1)`
  - `backlog_link_validate()` — reports orphans, asymmetric pairs, depends_on cycles
  - `backlog_link_reconcile()` — adds missing inverses on peers
- Slim `_get` views (`backlog_get_task`, `backlog_handover_get`, `backlog_issue_get`, `backlog_lesson_get`, `backlog_idea_get`) emit one grouped `links:` block instead of per-field linkage. `expand_links=true` swaps bare IDs for `{id, tldr}` pills.
- Viewer: shared `link-pills.js` renderer replaces per-field linkage sections in `task-detail`, `issue-detail`, `lesson-detail`. Legacy-field fallback for unmigrated projects.
- `scripts/migrate_links.py` — one-shot, idempotent migration: translates legacy fields to typed `links`, drops the old fields, runs `backlog_link_reconcile` to fill inverses.

### Migration
1. Run `python -m plugins.taskmaster.scripts.migrate_links --root <project>` (use `--keep-legacy` if you want to keep old fields readable in addition to writing `links`).
2. Inspect the JSON summary — `reconcile.unfixable` lists orphan links pointing at deleted entities (manual cleanup).
3. Run `backlog_link_validate` after the migration; expect `orphans == []`, `asymmetric == []`, `cycles == []`.
4. Old `related_*` / `depends_on` / `fixed_in_task` / `duplicate_of` / `supersedes` / `superseded_by` fields are read as a fallback when `links` is absent. They are dropped by `migrate_links` and will be removed entirely from read-fallback in the next minor release.

### Breaking changes
- After migration, entities no longer carry the legacy linkage fields. Callers that read `task["depends_on"]` directly must switch to `entity_links(task)` or filter `task["links"]`.
- `backlog_get_task` slim mode no longer emits per-field linkages; downstream consumers must read the grouped `links:` block. `verbose=true` still includes both for one release.

Spec: `docs/superpowers/specs/2026-05-15-taskmaster-progressive-disclosure-design.md` §6.
```

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/CHANGELOG.md
git commit -m "docs(taskmaster): changelog entry for v3.X programmatic linking"
```

---

## Self-Review

After implementing all 25 tasks (Task 0 + Tasks 1–24), run this final pass:

- [ ] Task 0 complete: `plugins/taskmaster/tests/conftest.py`, `plugins/__init__.py`, `plugins/taskmaster/__init__.py` all exist.
- [ ] All tests pass: `pytest plugins/taskmaster/tests/ -v`
- [ ] Smoke test passes specifically: `pytest plugins/taskmaster/tests/test_links_smoke.py -v`
- [ ] Archived-target test passes: `pytest plugins/taskmaster/tests/test_backlog_link_validate.py::test_validate_reports_archived_target_as_warning -v`
- [ ] Migration is idempotent: run `python -m plugins.taskmaster.scripts.migrate_links --root <real project>` twice; second run reports `migrated.tasks == 0` etc.
- [ ] `backlog_link_validate` on a real project returns `{"orphans": [], "asymmetric": [], "cycles": []}` after running reconcile.
- [ ] Manual sanity: open a migrated project in the viewer — `task-detail`, `issue-detail`, `lesson-detail` render the grouped link pills with correct labels. No orphan "Dependencies" or "Related" sections duplicate the same data.
- [ ] Cycle detection: try `backlog_link_create T-001 T-001 depends_on` → rejected; try a 3-node loop → rejected.
- [ ] Auto-detection: create a handover whose body says "Next: T-005"; confirm `references` link to T-005 appears and `referenced_by` materializes on T-005.
- [ ] `git log --oneline` shows ~25 atomic commits, one per task.
- [ ] No `TBD`, `TODO`, or `pass # implement later` markers in plugin code added by this plan.

---

## Out of scope (covered elsewhere or deferred)

- **`tldr` field + slim-default `_get` view** → Plan A. Plan C's grouped `links` block plugs into Plan A's slim renderer when both ship together.
- **Parallel handover status model** → Plan B. Plan C's auto-detection materializes `references` links on handovers regardless of their status semantics.
- **`start-session` / `pick-task` glance redesign** → Plan D.
- **Skill body slimming** → Plan E.
- **Computed/derived linkages (commit → issue, files → lesson)** — Spec §6E surfaces these as suggestions at end-session, not as auto-write. Out of scope for Plan C; revisit after confidence-tuning spec.
- **Transitive graph algorithms** beyond `backlog_link_query(depth=N)` — shortest-path, connected-components, etc. — deferred.
- **Section-aware editing of entity bodies** — deferred to its own spec.
