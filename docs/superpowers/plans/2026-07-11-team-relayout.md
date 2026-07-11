# Team Relayout (Epic 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move every task field (light + heavy) into `tasks/<id>.md`, drop `epics[].tasks[]` from `backlog.yaml`, and make saves dirty-scoped + merge-aware so two writers (even two processes on one machine) never clobber each other's unrelated changes.

**Architecture:** Introduce `schema_version: 4` as an additive, version-gated storage layout in `taskmaster/taskmaster_v3.py`: `load_v4` enumerates tasks by globbing `tasks/*.md` (+ `tasks/archive/*.md`), groups by each task's `epic:` frontmatter, orders by `(order, id)`, and populates the *same* in-memory `epic["tasks"]` shape the v3 loader produced — so the ~50 read-path iterators over `epic["tasks"]` in `backlog_server.py` keep working unchanged. `save_v4` is dirty-scoped (diff vs a deep-copied load snapshot; write only touched entity files) and merge-aware (before writing a dirty task whose on-disk file changed since load, three-way field-merge with the disk). The v3 path stays live for the whole epic (read + write) so the existing suite is green after every task; the final task flips `backlog_init` to v4, migrates the test fixtures, and makes old-layout projects load read-only with a migrate prompt.

**Tech Stack:** Python 3.11+, `pyyaml`, `fastmcp`; `pytest` (via `tests/conftest.py`, which puts the plugin root on `sys.path`). No new dependencies.

## Global Constraints

- Python floor is `>=3.11` (`pyproject.toml:9`) — no syntax newer than 3.11.
- No new hard dependencies; deps stay `["fastmcp", "pyyaml"]`.
- All work happens in `C:\Users\gruku\Files\Claude\taskmaster` on a feature branch `feat/team-relayout` (create it in Task 0). The `plugins/taskmaster` submodule in claude-tools is advanced separately after this epic lands — do NOT edit the submodule in place.
- The single command `python -m pytest tests/ -q` (run from the repo root) must be green after every task.
- Reuse existing helpers: `atomic_write` (`taskmaster_v3.py:47`), `parse_frontmatter`/`render_frontmatter` (`:344`,`:399`), `read_task_file`/`write_task_file` (`:419`,`:424`), `task_file_path`/`epic_file_path`/`phase_file_path` (`:854`,`:863`,`:868`). Never hand-roll frontmatter serialization.
- SemVer: this is a schema break → **major** bump (`4.4.1` → `5.0.0`), done in the final task.
- Explicit-pathspec commits only. Never `git add -A`. Every commit lists the exact files.
- TDD: every task writes a failing test first, as its own commit, then the implementation as a second commit (mirrors the repo convention — see `tests/test_v3_layout.py`).

---

### Task 0: Feature branch

**Files:** none (git only).

- [ ] Create and switch to the feature branch:
  ```bash
  git -C "C:/Users/gruku/Files/Claude/taskmaster" checkout -b feat/team-relayout
  ```
- [ ] Confirm the suite is green on a clean base (baseline for "green after every task"):
  ```bash
  cd "C:/Users/gruku/Files/Claude/taskmaster" && python -m pytest tests/ -q
  ```
  Expected: all tests pass (a green summary line like `NNNN passed`). If anything fails on a clean checkout, STOP and report — do not start on a red base.

---

### Task 1: v4 schema constant + task↔file (de)serialization

Introduce `SCHEMA_V4` and the two pure functions that convert a whole task dict to/from a `tasks/<id>.md` file. In v4, *all* fields (including `id`, `title`, `status`, `epic`, `order`) live in frontmatter; only the prose body (`BODY_KEY`) is the markdown body.

**Files:**
- Modify `taskmaster/taskmaster_v3.py` — add `SCHEMA_V4` next to `SCHEMA_V3` (`:34`); add `task_v4_to_file` / `task_v4_from_file` just below the v3 split/merge helpers (after `_merge_task_from_v3`, ~`:916`).
- Create `tests/test_v4_layout.py`.

**Interfaces:**
- Produces `SCHEMA_V4: int = 4`.
- Produces `task_v4_to_file(task: dict[str, Any]) -> tuple[dict[str, Any], str]` — returns `(frontmatter, body)`. Every key except `BODY_KEY` goes to frontmatter verbatim; `BODY_KEY` → body (or `""`).
- Produces `task_v4_from_file(fm: dict[str, Any], body: str) -> dict[str, Any]` — inverse; copies `fm`, attaches `body` under `BODY_KEY` only when non-empty.

Steps:

- [ ] Write the failing test. Append to `tests/test_v4_layout.py`:
  ```python
  """Tests for the v4 sharded storage layout (team-relayout, epic 1)."""
  from __future__ import annotations

  import sys
  from pathlib import Path

  import pytest
  import yaml

  sys.path.insert(0, str(Path(__file__).parent.parent))

  from taskmaster import taskmaster_v3 as v3  # noqa: E402


  class TestV4Constants:
      def test_schema_v4_is_4(self):
          assert v3.SCHEMA_V4 == 4

      def test_v4_greater_than_v3(self):
          assert v3.SCHEMA_V4 > v3.SCHEMA_V3


  class TestTaskV4RoundTrip:
      def test_all_fields_go_to_frontmatter(self):
          task = {
              "id": "auth-014", "title": "Login", "status": "todo",
              "epic": "auth", "order": 2.0, "priority": "high",
              "gates": {"spec": "pass"}, v3.BODY_KEY: "## Spec\n\nbody text",
          }
          fm, body = v3.task_v4_to_file(task)
          assert fm["id"] == "auth-014"
          assert fm["epic"] == "auth"
          assert fm["order"] == 2.0
          assert fm["gates"] == {"spec": "pass"}
          assert v3.BODY_KEY not in fm
          assert body == "## Spec\n\nbody text"

      def test_from_file_reattaches_body(self):
          fm = {"id": "auth-014", "title": "Login", "epic": "auth", "order": 2.0}
          task = v3.task_v4_from_file(fm, "prose")
          assert task["id"] == "auth-014"
          assert task[v3.BODY_KEY] == "prose"

      def test_empty_body_omits_body_key(self):
          task = v3.task_v4_from_file({"id": "x", "epic": "e", "order": 1.0}, "")
          assert v3.BODY_KEY not in task

      def test_round_trip_identity(self):
          task = {
              "id": "auth-014", "title": "Login", "status": "todo",
              "epic": "auth", "order": 2.0, v3.BODY_KEY: "body",
          }
          fm, body = v3.task_v4_to_file(task)
          assert v3.task_v4_from_file(fm, body) == task
  ```
- [ ] Run it — expect failure (`AttributeError: module ... has no attribute 'SCHEMA_V4'`):
  ```bash
  cd "C:/Users/gruku/Files/Claude/taskmaster" && python -m pytest tests/test_v4_layout.py -q
  ```
- [ ] Commit the failing test:
  ```bash
  git -C "C:/Users/gruku/Files/Claude/taskmaster" add tests/test_v4_layout.py
  git -C "C:/Users/gruku/Files/Claude/taskmaster" commit -m "test(v4): task<->file serialization round-trip (failing)"
  ```
- [ ] Add the constant. In `taskmaster/taskmaster_v3.py`, find line 34 `SCHEMA_V3 = 3` and add below it:
  ```python
  SCHEMA_V4 = 4
  ```
- [ ] Add the serializers. In `taskmaster/taskmaster_v3.py`, immediately after `_merge_task_from_v3` (ends ~`:916`) insert:
  ```python
  def task_v4_to_file(task: dict[str, Any]) -> tuple[dict[str, Any], str]:
      """v4: split a whole task dict into (frontmatter, body).

      Unlike v3, NO field stays in backlog.yaml — every key except the prose
      body lives in the per-task file's frontmatter (id, title, status, epic,
      order, gates, ...). Body is the BODY_KEY value.
      """
      fm: dict[str, Any] = {}
      body = ""
      for key, value in task.items():
          if key == BODY_KEY:
              body = value or ""
          else:
              fm[key] = value
      return fm, body


  def task_v4_from_file(fm: dict[str, Any], body: str) -> dict[str, Any]:
      """v4: reverse of task_v4_to_file. Body attaches under BODY_KEY only when
      non-empty (keeps bodyless tasks free of an empty _body key)."""
      task = dict(fm)
      if body:
          task[BODY_KEY] = body
      return task
  ```
- [ ] Run the test — expect pass:
  ```bash
  cd "C:/Users/gruku/Files/Claude/taskmaster" && python -m pytest tests/test_v4_layout.py -q
  ```
- [ ] Commit:
  ```bash
  git -C "C:/Users/gruku/Files/Claude/taskmaster" add taskmaster/taskmaster_v3.py
  git -C "C:/Users/gruku/Files/Claude/taskmaster" commit -m "feat(v4): SCHEMA_V4 + whole-task file serializers"
  ```

---

### Task 2: `load_v4` — glob enumeration, epic grouping, `(order, id)` ordering

`load_v4` reads the slim `backlog.yaml` (meta + phases + epic definitions, no task lists), globs `tasks/*.md` and `tasks/archive/*.md`, groups tasks by their `epic:` frontmatter, orders each group by `(float(order), str(id))`, and assigns the result to `epic["tasks"]` — reproducing the exact in-memory shape the v3 loader produced. Tasks whose `epic:` names no known epic are collected as orphans under the private key `_orphan_tasks` (surfaced by `backlog_validate` in Task 11, stripped on save).

**Files:**
- Modify `taskmaster/taskmaster_v3.py` — add `iter_task_files` and `load_v4` after `load_v3` (ends `:1011`). Reuse the existing per-epic / per-phase body-merge blocks (copied from `load_v3:985-1010`).
- Modify `tests/test_v4_layout.py` — add `TestLoadV4`.

**Interfaces:**
- Produces `iter_task_files(backlog_path: Path) -> list[Path]` — sorted `tasks/*.md` then sorted `tasks/archive/*.md`.
- Produces `load_v4(backlog_path: Path) -> dict[str, Any]` — same dict shape as `load_v3` (`epics[].tasks[]` populated), plus `data["_orphan_tasks"]: list[str]`.

Steps:

- [ ] Write the failing test. Add to `tests/test_v4_layout.py`:
  ```python
  def _write_v4_project(tmp_path, epics, tasks):
      """epics: list of {id,name}. tasks: list of full task dicts (with epic+order).
      Writes a slim backlog.yaml (no task lists) + tasks/<id>.md files."""
      tm = tmp_path / ".taskmaster"
      (tm / "tasks").mkdir(parents=True, exist_ok=True)
      backlog = {"meta": {"project": "t", "schema_version": 4},
                 "epics": [dict(e) for e in epics], "phases": []}
      (tm / "backlog.yaml").write_text(yaml.dump(backlog), encoding="utf-8")
      for t in tasks:
          fm, body = v3.task_v4_to_file(t)
          v3.write_task_file(tm / "tasks" / f"{t['id']}.md", fm, body)
      return tm / "backlog.yaml"


  class TestLoadV4:
      def test_groups_tasks_by_epic(self, tmp_path):
          bp = _write_v4_project(
              tmp_path,
              epics=[{"id": "auth", "name": "Auth"}, {"id": "ui", "name": "UI"}],
              tasks=[
                  {"id": "auth-001", "title": "A", "epic": "auth", "order": 1.0},
                  {"id": "ui-001", "title": "U", "epic": "ui", "order": 1.0},
              ],
          )
          data = v3.load_v4(bp)
          by_id = {e["id"]: e for e in data["epics"]}
          assert [t["id"] for t in by_id["auth"]["tasks"]] == ["auth-001"]
          assert [t["id"] for t in by_id["ui"]["tasks"]] == ["ui-001"]

      def test_orders_by_order_then_id(self, tmp_path):
          bp = _write_v4_project(
              tmp_path,
              epics=[{"id": "e", "name": "E"}],
              tasks=[
                  {"id": "e-003", "title": "c", "epic": "e", "order": 2.0},
                  {"id": "e-001", "title": "a", "epic": "e", "order": 1.0},
                  {"id": "e-002", "title": "b", "epic": "e", "order": 1.0},
              ],
          )
          data = v3.load_v4(bp)
          # order 1.0 ties broken by id (e-001 before e-002), then 2.0
          assert [t["id"] for t in data["epics"][0]["tasks"]] == ["e-001", "e-002", "e-003"]

      def test_includes_archive_subdir(self, tmp_path):
          bp = _write_v4_project(
              tmp_path, epics=[{"id": "e", "name": "E"}],
              tasks=[{"id": "e-001", "title": "a", "epic": "e", "order": 1.0}],
          )
          arch = bp.parent / "tasks" / "archive"
          arch.mkdir()
          fm, body = v3.task_v4_to_file(
              {"id": "e-009", "title": "old", "epic": "e", "order": 9.0, "status": "archived"})
          v3.write_task_file(arch / "e-009.md", fm, body)
          data = v3.load_v4(bp)
          assert [t["id"] for t in data["epics"][0]["tasks"]] == ["e-001", "e-009"]

      def test_orphan_epic_collected(self, tmp_path):
          bp = _write_v4_project(
              tmp_path, epics=[{"id": "e", "name": "E"}],
              tasks=[
                  {"id": "e-001", "title": "a", "epic": "e", "order": 1.0},
                  {"id": "x-001", "title": "lost", "epic": "ghost", "order": 1.0},
              ],
          )
          data = v3.load_v4(bp)
          assert data["_orphan_tasks"] == ["x-001"]
          assert [t["id"] for t in data["epics"][0]["tasks"]] == ["e-001"]

      def test_body_survives_load(self, tmp_path):
          bp = _write_v4_project(
              tmp_path, epics=[{"id": "e", "name": "E"}],
              tasks=[{"id": "e-001", "title": "a", "epic": "e", "order": 1.0,
                      v3.BODY_KEY: "## Notes\n\nhello"}],
          )
          data = v3.load_v4(bp)
          assert data["epics"][0]["tasks"][0][v3.BODY_KEY] == "## Notes\n\nhello"
  ```
- [ ] Run — expect failure (`AttributeError: ... 'load_v4'`):
  ```bash
  cd "C:/Users/gruku/Files/Claude/taskmaster" && python -m pytest tests/test_v4_layout.py::TestLoadV4 -q
  ```
- [ ] Commit the failing test:
  ```bash
  git -C "C:/Users/gruku/Files/Claude/taskmaster" add tests/test_v4_layout.py
  git -C "C:/Users/gruku/Files/Claude/taskmaster" commit -m "test(v4): load_v4 glob/group/order/orphan (failing)"
  ```
- [ ] Implement. In `taskmaster/taskmaster_v3.py`, after `load_v3` (ends `:1011`) insert:
  ```python
  def iter_task_files(backlog_path: Path) -> list[Path]:
      """All v4 task files: tasks/*.md then tasks/archive/*.md, each sorted.

      Mirrors next_bug_id's directory-scan philosophy — the filesystem, not an
      in-memory index, is the enumeration source of truth.
      """
      tdir = backlog_path.parent / "tasks"
      files: list[Path] = []
      if tdir.is_dir():
          files.extend(sorted(tdir.glob("*.md")))
      adir = tdir / "archive"
      if adir.is_dir():
          files.extend(sorted(adir.glob("*.md")))
      return files


  def load_v4(backlog_path: Path) -> dict[str, Any]:
      """Load a v4 backlog: slim index (meta + phases + epic defs) + per-task
      files enumerated by glob and grouped by each task's `epic:` frontmatter.

      Produces the same in-memory shape as load_v3 (epics[].tasks[] populated,
      ordered by (order, id)), so existing read code keeps working unchanged.
      Tasks whose `epic:` names no known epic are collected under the private
      key `_orphan_tasks` (surfaced by backlog_validate, stripped on save).
      """
      data = yaml.safe_load(backlog_path.read_text(encoding="utf-8")) or {}
      epic_ids = {e.get("id") for e in data.get("epics", [])}
      tasks_by_epic: dict[str, list[dict[str, Any]]] = {}
      orphans: list[str] = []
      for tf in iter_task_files(backlog_path):
          fm, body = read_task_file(tf)
          task = task_v4_from_file(fm, body)
          eid = task.get("epic")
          if eid not in epic_ids:
              orphans.append(task.get("id") or tf.stem)
              continue
          tasks_by_epic.setdefault(eid, []).append(task)
      for tlist in tasks_by_epic.values():
          tlist.sort(key=lambda t: (float(t.get("order", 0.0)), str(t.get("id", ""))))
      for epic in data.get("epics", []):
          epic["tasks"] = tasks_by_epic.get(epic.get("id"), [])

      # Per-epic / per-phase heavy bodies (doc-bearing epics/phases) — same as v3.
      for epic in data.get("epics", []):
          eid = epic.get("id")
          if not eid:
              continue
          ef = epic_file_path(backlog_path, eid)
          if ef.exists():
              fm, body = read_task_file(ef)
              epic_meta = {k: v for k, v in epic.items() if k != "tasks"}
              merged = _merge_entity_from_v3(epic_meta, fm, body, EPIC_HEAVY_FIELDS)
              merged["tasks"] = epic.get("tasks", [])
              epic.clear()
              epic.update(merged)
      for phase in data.get("phases", []):
          pid = phase.get("id")
          if not pid:
              continue
          pf = phase_file_path(backlog_path, pid)
          if pf.exists():
              fm, body = read_task_file(pf)
              merged = _merge_entity_from_v3(phase, fm, body, PHASE_HEAVY_FIELDS)
              phase.clear()
              phase.update(merged)

      data["_orphan_tasks"] = orphans
      return data
  ```
- [ ] Run — expect pass:
  ```bash
  cd "C:/Users/gruku/Files/Claude/taskmaster" && python -m pytest tests/test_v4_layout.py -q
  ```
- [ ] Commit:
  ```bash
  git -C "C:/Users/gruku/Files/Claude/taskmaster" add taskmaster/taskmaster_v3.py
  git -C "C:/Users/gruku/Files/Claude/taskmaster" commit -m "feat(v4): load_v4 glob enumeration + epic grouping + (order,id) sort"
  ```

---

### Task 3: `save_v4` — full-write baseline + slim backlog.yaml

`save_v4` writes each task to `tasks/<id>.md` with all fields, writes epic/phase body files exactly as v3 does, and writes a slim `backlog.yaml` containing meta (minus `updated`) + phases + epic definitions with **no** `tasks` lists. This task implements the full-write (non-dirty) branch with a `snapshot` parameter already present (defaults to `None` = write everything); Task 6 fills the dirty branch. `meta.updated` is not written to the shared file (derived into `local/cache/` in Task 9); for now save_v4 simply drops it if present.

**Files:**
- Modify `taskmaster/taskmaster_v3.py` — add `save_v4` after `save_v3` (ends `:3630`).
- Modify `tests/test_v4_layout.py` — add `TestSaveV4`.

**Interfaces:**
- Produces `save_v4(backlog_path: Path, data: dict[str, Any], snapshot: dict[str, Any] | None = None) -> None`.
- Guarantees: `load_v4(save_v4(...)) == ` (task-set equality) the input; `backlog.yaml` on disk has no `tasks` key under any epic; private keys (leading `_`) never persisted.

Steps:

- [ ] Write the failing test. Add to `tests/test_v4_layout.py`:
  ```python
  class TestSaveV4:
      def test_writes_task_files_and_slim_backlog(self, tmp_path):
          tm = tmp_path / ".taskmaster"
          (tm / "tasks").mkdir(parents=True)
          bp = tm / "backlog.yaml"
          bp.write_text(yaml.dump({"meta": {"project": "t", "schema_version": 4},
                                   "epics": [{"id": "e", "name": "E"}], "phases": []}))
          data = {
              "meta": {"project": "t", "schema_version": 4},
              "epics": [{"id": "e", "name": "E", "tasks": [
                  {"id": "e-001", "title": "A", "epic": "e", "order": 1.0, "status": "todo"},
              ]}],
              "phases": [],
          }
          v3.save_v4(bp, data)
          # task file exists with all fields
          fm, _ = v3.read_task_file(tm / "tasks" / "e-001.md")
          assert fm["title"] == "A" and fm["epic"] == "e" and fm["status"] == "todo"
          # backlog.yaml carries NO task list
          on_disk = yaml.safe_load(bp.read_text())
          assert "tasks" not in on_disk["epics"][0]

      def test_round_trip_identity(self, tmp_path):
          tm = tmp_path / ".taskmaster"
          (tm / "tasks").mkdir(parents=True)
          bp = tm / "backlog.yaml"
          bp.write_text(yaml.dump({"meta": {"schema_version": 4}, "epics": [], "phases": []}))
          data = {
              "meta": {"schema_version": 4},
              "epics": [{"id": "e", "name": "E", "tasks": [
                  {"id": "e-001", "title": "A", "epic": "e", "order": 1.0},
                  {"id": "e-002", "title": "B", "epic": "e", "order": 2.0,
                   v3.BODY_KEY: "## Notes\n\nbody"},
              ]}],
              "phases": [],
          }
          v3.save_v4(bp, data)
          reloaded = v3.load_v4(bp)
          tasks = reloaded["epics"][0]["tasks"]
          assert [t["id"] for t in tasks] == ["e-001", "e-002"]
          assert tasks[1][v3.BODY_KEY] == "## Notes\n\nbody"

      def test_private_keys_not_persisted(self, tmp_path):
          tm = tmp_path / ".taskmaster"
          (tm / "tasks").mkdir(parents=True)
          bp = tm / "backlog.yaml"
          bp.write_text(yaml.dump({"meta": {"schema_version": 4}, "epics": [], "phases": []}))
          data = {"meta": {"schema_version": 4}, "epics": [], "phases": [],
                  "_orphan_tasks": ["x-001"]}
          v3.save_v4(bp, data)
          assert "_orphan_tasks" not in yaml.safe_load(bp.read_text())

      def test_meta_updated_not_written(self, tmp_path):
          tm = tmp_path / ".taskmaster"
          (tm / "tasks").mkdir(parents=True)
          bp = tm / "backlog.yaml"
          bp.write_text(yaml.dump({"meta": {"schema_version": 4}, "epics": [], "phases": []}))
          data = {"meta": {"schema_version": 4, "updated": "2026-07-11"},
                  "epics": [], "phases": []}
          v3.save_v4(bp, data)
          assert "updated" not in yaml.safe_load(bp.read_text())["meta"]
  ```
- [ ] Run — expect failure (`AttributeError: ... 'save_v4'`):
  ```bash
  cd "C:/Users/gruku/Files/Claude/taskmaster" && python -m pytest tests/test_v4_layout.py::TestSaveV4 -q
  ```
- [ ] Commit the failing test:
  ```bash
  git -C "C:/Users/gruku/Files/Claude/taskmaster" add tests/test_v4_layout.py
  git -C "C:/Users/gruku/Files/Claude/taskmaster" commit -m "test(v4): save_v4 slim backlog + round-trip (failing)"
  ```
- [ ] Implement. In `taskmaster/taskmaster_v3.py`, after `save_v3` (ends `:3630`) insert:
  ```python
  def save_v4(
      backlog_path: Path,
      data: dict[str, Any],
      snapshot: dict[str, Any] | None = None,
  ) -> None:
      """Save a v4 backlog: every task field → tasks/<id>.md; backlog.yaml holds
      only meta (minus `updated`) + phases + epic definitions (no task lists).

      `snapshot` (a deep copy of the dict returned by the matching load) enables
      dirty-scoped writes: only tasks that differ from the snapshot are written
      (see _v4_write_task, filled in Task 6). snapshot=None writes every task —
      the baseline used by migration and by tests.
      """
      # 1. Task files.
      for epic in data.get("epics", []):
          for task in epic.get("tasks", []):
              tid = task.get("id")
              if not tid:
                  continue
              _v4_write_task(backlog_path, task, snapshot)

      # 2. Epic / phase body files (identical policy to save_v3).
      slim_data: dict[str, Any] = {k: v for k, v in data.items() if not k.startswith("_")}
      slim_data["epics"] = []
      for epic in data.get("epics", []):
          epic_meta = {k: v for k, v in epic.items() if k != "tasks"}
          slim_meta, epic_heavy, epic_body = _split_entity_for_v3(epic_meta, EPIC_HEAVY_FIELDS)
          eid = slim_meta.get("id")
          if eid and (any(k in epic_heavy for k in EPIC_HEAVY_FIELDS) or epic_body):
              write_task_file(epic_file_path(backlog_path, eid), epic_heavy, epic_body)
              slim_data["epics"].append(slim_meta)
          else:
              if eid:
                  _remove_entity_file(epic_file_path(backlog_path, eid))
              slim_data["epics"].append(epic_meta)

      if "phases" in slim_data:
          slim_phases: list[dict[str, Any]] = []
          for phase in data.get("phases", []):
              slim_phase, phase_heavy, phase_body = _split_entity_for_v3(phase, PHASE_HEAVY_FIELDS)
              pid = slim_phase.get("id")
              if pid and (any(k in phase_heavy for k in PHASE_HEAVY_FIELDS) or phase_body):
                  write_task_file(phase_file_path(backlog_path, pid), phase_heavy, phase_body)
                  slim_phases.append(slim_phase)
              else:
                  if pid:
                      _remove_entity_file(phase_file_path(backlog_path, pid))
                  slim_phases.append(phase)
          slim_data["phases"] = slim_phases

      # 3. Slim backlog.yaml — never carries task lists or `meta.updated`.
      if isinstance(slim_data.get("meta"), dict):
          slim_data["meta"] = {k: v for k, v in slim_data["meta"].items() if k != "updated"}
      atomic_write(
          backlog_path,
          yaml.dump(slim_data, default_flow_style=False, sort_keys=False, allow_unicode=True),
      )


  def _v4_write_task(
      backlog_path: Path, task: dict[str, Any], snapshot: dict[str, Any] | None
  ) -> None:
      """Write one task file. Task 6 replaces this with the dirty-scoped,
      merge-aware version; this baseline always writes (snapshot ignored)."""
      fm, body = task_v4_to_file(task)
      write_task_file(task_file_path(backlog_path, task["id"]), fm, body)
  ```
- [ ] Run — expect pass:
  ```bash
  cd "C:/Users/gruku/Files/Claude/taskmaster" && python -m pytest tests/test_v4_layout.py -q
  ```
- [ ] Commit:
  ```bash
  git -C "C:/Users/gruku/Files/Claude/taskmaster" add taskmaster/taskmaster_v3.py
  git -C "C:/Users/gruku/Files/Claude/taskmaster" commit -m "feat(v4): save_v4 full-write baseline + slim backlog.yaml"
  ```

---

### Task 4: Wire v4 into the server load/save dispatch

Make `backlog_server._load` / `_save` route `schema_version >= 4` to `load_v4` / `save_v4`, and stash a deep-copied load snapshot in a module global so Task 6 can diff against it. v3 and v2 paths are untouched. This makes an on-disk v4 project fully usable through the MCP server.

**Files:**
- Modify `taskmaster/backlog_server.py` — imports (`:76-79`); `_load` (`:374-388`); `_save` (`:391-401`); add module global `_LOAD_SNAPSHOT` near `_backlog_lock` (`:306`).
- Create `tests/test_v4_server.py`.

**Interfaces:**
- Consumes `load_v4`, `save_v4`, `SCHEMA_V4` from `taskmaster.taskmaster_v3`.
- Produces module global `backlog_server._LOAD_SNAPSHOT: dict | None` (deep copy of the last v4 `_load()` result; `None` for v2/v3).

Steps:

- [ ] Write the failing test. Create `tests/test_v4_server.py`:
  ```python
  """Server-level v4 dispatch: mutate through the MCP server, land in task files."""
  from __future__ import annotations

  import sys
  from pathlib import Path

  import pytest
  import yaml

  sys.path.insert(0, str(Path(__file__).parent.parent))


  @pytest.fixture()
  def v4_project(tmp_path, monkeypatch):
      tm = tmp_path / ".taskmaster"
      (tm / "tasks").mkdir(parents=True)
      (tm / "PROGRESS.md").write_text("## Changelog\n", encoding="utf-8")
      backlog = {"meta": {"project": "t", "updated": "", "schema_version": 4},
                 "epics": [{"id": "e", "name": "E", "status": "active", "tasks": [
                     {"id": "e-001", "title": "First", "epic": "e", "order": 1.0,
                      "status": "todo", "priority": "medium"},
                 ]}],
                 "phases": [{"id": "p1", "name": "P1", "status": "active"}]}
      (tm / "backlog.yaml").write_text(yaml.dump(backlog), encoding="utf-8")
      fm, body = _mk_task_file(
          {"id": "e-001", "title": "First", "epic": "e", "order": 1.0,
           "status": "todo", "priority": "medium"})
      _write(tm / "tasks" / "e-001.md", fm, body)
      from taskmaster import backlog_server
      monkeypatch.setattr(backlog_server, "ROOT", tmp_path)
      monkeypatch.setattr(backlog_server, "CONFIG_PATH", tmp_path / ".taskmaster" / "taskmaster.json")
      monkeypatch.setattr(backlog_server, "LEGACY_CONFIG_PATH", tmp_path / ".claude" / "taskmaster.json")
      monkeypatch.chdir(tmp_path)
      return tmp_path


  def _mk_task_file(task):
      from taskmaster import taskmaster_v3 as v3
      return v3.task_v4_to_file(task)


  def _write(path, fm, body):
      from taskmaster import taskmaster_v3 as v3
      v3.write_task_file(path, fm, body)


  def test_load_returns_globbed_tasks(v4_project):
      from taskmaster import backlog_server
      data = backlog_server._load()
      assert data["epics"][0]["tasks"][0]["id"] == "e-001"


  def test_update_task_writes_to_task_file_not_backlog(v4_project):
      from taskmaster import backlog_server
      from taskmaster.taskmaster_v3 import update_task
      update_task("e-001", {"title": "Renamed"}, backlog_path=backlog_server._backlog_path())
      # task file has the new title
      fm, _ = _read(v4_project / ".taskmaster" / "tasks" / "e-001.md")
      assert fm["title"] == "Renamed"
      # backlog.yaml still carries no task list
      on_disk = yaml.safe_load((v4_project / ".taskmaster" / "backlog.yaml").read_text())
      assert "tasks" not in on_disk["epics"][0]


  def test_load_snapshot_is_deep_copy(v4_project):
      from taskmaster import backlog_server
      data = backlog_server._load()
      data["epics"][0]["tasks"][0]["title"] = "mutated in memory"
      assert backlog_server._LOAD_SNAPSHOT["epics"][0]["tasks"][0]["title"] == "First"


  def _read(path):
      from taskmaster import taskmaster_v3 as v3
      return v3.read_task_file(path)
  ```
  Note: this test assumes `taskmaster_v3.update_task` routes through v4 save. If `update_task` is a thin wrapper over `load_v3`/`save_v3` directly (not `_load`/`_save`), it must dispatch on schema version too — verify and, if needed, point its internal load/save at the version-dispatching helpers. Confirm by reading `update_task` in `taskmaster_v3.py` before implementing; if it hard-calls `load_v3`/`save_v3`, add the same `SCHEMA_V4` dispatch there and cover it with the test above.
- [ ] Run — expect failure (`AttributeError: ... '_LOAD_SNAPSHOT'` or task written into backlog.yaml):
  ```bash
  cd "C:/Users/gruku/Files/Claude/taskmaster" && python -m pytest tests/test_v4_server.py -q
  ```
- [ ] Commit the failing test:
  ```bash
  git -C "C:/Users/gruku/Files/Claude/taskmaster" add tests/test_v4_server.py
  git -C "C:/Users/gruku/Files/Claude/taskmaster" commit -m "test(v4): server load/save dispatch + snapshot (failing)"
  ```
- [ ] Add the import. In `taskmaster/backlog_server.py`, the existing import block around `:76-79` is:
  ```python
      detect_schema_version as _detect_schema_version,
      ...
      load_v3 as _load_v3,
      save_v3 as _save_v3,
  ```
  Add alongside them:
  ```python
      load_v4 as _load_v4,
      save_v4 as _save_v4,
  ```
  and ensure `SCHEMA_V4` is imported wherever `SCHEMA_V3` is (grep the import list for `SCHEMA_V3` and add `SCHEMA_V4` next to it).
- [ ] Add the snapshot global. In `taskmaster/backlog_server.py`, right after `_backlog_lock = threading.Lock()` (`:306`) add:
  ```python
  import copy as _copy

  # Deep copy of the last v4 _load() result, used as the diff baseline for
  # dirty-scoped save_v4 (None for v2/v3, which write whole-file).
  _LOAD_SNAPSHOT: dict | None = None
  ```
- [ ] Update `_load`. Replace the body of `_load` (`:374-388`) with:
  ```python
  def _load() -> dict:
      global _LOAD_SNAPSHOT
      bp = _backlog_path()
      # Peek at version without per-file enrichment so we can dispatch.
      raw = yaml.safe_load(bp.read_text(encoding="utf-8")) or {}
      version = _detect_schema_version(raw)
      if version >= SCHEMA_V4:
          data = _load_v4(bp)
      elif version >= SCHEMA_V3:
          data = _load_v3(bp)
      else:
          data = raw
      # Backfill missing 'created' on tasks + normalize legacy priorities.
      for epic in data.get("epics", []):
          for t in epic.get("tasks", []):
              if not t.get("created"):
                  t["created"] = t.get("started") or t.get("completed") or "2025-01-01T00:00"
              pri = t.get("priority", "")
              if pri in _LEGACY_TO_NAME:
                  t["priority"] = _LEGACY_TO_NAME[pri]
      _LOAD_SNAPSHOT = _copy.deepcopy(data) if version >= SCHEMA_V4 else None
      return data
  ```
- [ ] Update `_save`. Replace the body of `_save` (`:391-401`) with:
  ```python
  def _save(data: dict) -> None:
      with _backlog_lock:
          bp = _backlog_path()
          version = _detect_schema_version(data)
          if version >= SCHEMA_V4:
              _save_v4(bp, data, snapshot=_LOAD_SNAPSHOT)
          elif version >= SCHEMA_V3:
              data["meta"]["updated"] = _today()
              _save_v3(bp, data)
          else:
              data["meta"]["updated"] = _today()
              _atomic_write(
                  bp,
                  yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True),
              )
  ```
- [ ] Run the new test and the full suite — expect pass:
  ```bash
  cd "C:/Users/gruku/Files/Claude/taskmaster" && python -m pytest tests/test_v4_server.py -q && python -m pytest tests/ -q
  ```
- [ ] Commit:
  ```bash
  git -C "C:/Users/gruku/Files/Claude/taskmaster" add taskmaster/backlog_server.py
  git -C "C:/Users/gruku/Files/Claude/taskmaster" commit -m "feat(v4): route server load/save to v4 + stash load snapshot"
  ```

---

### Task 5: Fractional `order:` + dir-scan task-ID allocator, wired into `backlog_add_task`

Replace the in-memory `epic_obj["tasks"]` ID scan (`backlog_server.py:4052-4064`) and the implicit list-position order with (a) a directory-scan ID allocator mirroring `next_bug_id`, and (b) a fractional `order:` = current max order + 1.0. Both are gated so v3 projects (no globbed files) keep their existing behavior.

**Files:**
- Modify `taskmaster/taskmaster_v3.py` — add `next_task_id`, `next_task_order`, `order_between` after `iter_task_files` (Task 2).
- Modify `taskmaster/backlog_server.py` — `backlog_add_task` ID + order block (`:4046-4064`, `:4073-4084`).
- Modify `tests/test_v4_layout.py` (allocator/order units) and `tests/test_v4_server.py` (add-task integration).

**Interfaces:**
- Produces `next_task_id(backlog_path: Path, epic: str) -> str` — scans `iter_task_files` filenames for the `{epic}-NNN` prefix, returns `{epic}-{max+1:03d}`.
- Produces `next_task_order(backlog_path: Path, epic: str) -> float` — max existing `order` in that epic + 1.0 (1.0 when empty).
- Produces `order_between(a: float, b: float) -> float` — midpoint `(a + b) / 2`.

Steps:

- [ ] Write the failing tests. Add to `tests/test_v4_layout.py`:
  ```python
  class TestV4Allocators:
      def test_next_task_id_scans_dir_incl_archive(self, tmp_path):
          bp = _write_v4_project(
              tmp_path, epics=[{"id": "e", "name": "E"}],
              tasks=[{"id": "e-001", "title": "a", "epic": "e", "order": 1.0},
                     {"id": "e-002", "title": "b", "epic": "e", "order": 2.0}],
          )
          arch = bp.parent / "tasks" / "archive"
          arch.mkdir()
          fm, body = v3.task_v4_to_file({"id": "e-005", "title": "old", "epic": "e", "order": 5.0})
          v3.write_task_file(arch / "e-005.md", fm, body)
          assert v3.next_task_id(bp, "e") == "e-006"

      def test_next_task_id_empty_epic(self, tmp_path):
          bp = _write_v4_project(tmp_path, epics=[{"id": "e", "name": "E"}], tasks=[])
          assert v3.next_task_id(bp, "e") == "e-001"

      def test_next_task_id_ignores_other_epics(self, tmp_path):
          bp = _write_v4_project(
              tmp_path, epics=[{"id": "e", "name": "E"}, {"id": "auth", "name": "A"}],
              tasks=[{"id": "auth-009", "title": "x", "epic": "auth", "order": 1.0}],
          )
          assert v3.next_task_id(bp, "e") == "e-001"

      def test_next_task_order_is_max_plus_one(self, tmp_path):
          bp = _write_v4_project(
              tmp_path, epics=[{"id": "e", "name": "E"}],
              tasks=[{"id": "e-001", "title": "a", "epic": "e", "order": 1.0},
                     {"id": "e-002", "title": "b", "epic": "e", "order": 2.0}],
          )
          assert v3.next_task_order(bp, "e") == 3.0

      def test_next_task_order_empty_epic_is_one(self, tmp_path):
          bp = _write_v4_project(tmp_path, epics=[{"id": "e", "name": "E"}], tasks=[])
          assert v3.next_task_order(bp, "e") == 1.0

      def test_order_between_is_midpoint(self):
          assert v3.order_between(1.0, 2.0) == 1.5
  ```
- [ ] Run — expect failure:
  ```bash
  cd "C:/Users/gruku/Files/Claude/taskmaster" && python -m pytest tests/test_v4_layout.py::TestV4Allocators -q
  ```
- [ ] Commit failing test:
  ```bash
  git -C "C:/Users/gruku/Files/Claude/taskmaster" add tests/test_v4_layout.py
  git -C "C:/Users/gruku/Files/Claude/taskmaster" commit -m "test(v4): dir-scan id allocator + fractional order (failing)"
  ```
- [ ] Implement the allocators. In `taskmaster/taskmaster_v3.py`, after `iter_task_files` insert:
  ```python
  def next_task_id(backlog_path: Path, epic: str) -> str:
      """Allocate the next {epic}-NNN id by scanning task filenames on disk
      (active + archive) — mirrors next_bug_id. The filesystem, not an in-memory
      list, is the allocation source of truth so a concurrent process's just-
      created file is honored."""
      prefix = f"{epic}-"
      nums: list[int] = []
      for tf in iter_task_files(backlog_path):
          stem = tf.stem
          if stem.startswith(prefix):
              m = re.search(r"(\d+)$", stem)
              if m:
                  nums.append(int(m.group(1)))
      n = (max(nums) + 1) if nums else 1
      return f"{epic}-{n:03d}"


  def next_task_order(backlog_path: Path, epic: str) -> float:
      """Next fractional order for a new task appended to `epic`: max existing
      order + 1.0 (1.0 when the epic is empty)."""
      orders: list[float] = []
      for tf in iter_task_files(backlog_path):
          fm, _ = read_task_file(tf)
          if fm.get("epic") == epic and "order" in fm:
              try:
                  orders.append(float(fm["order"]))
              except (TypeError, ValueError):
                  pass
      return (max(orders) + 1.0) if orders else 1.0


  def order_between(a: float, b: float) -> float:
      """Midpoint order for inserting between two tasks (fractional indexing)."""
      return (a + b) / 2
  ```
- [ ] Run the unit tests — expect pass:
  ```bash
  cd "C:/Users/gruku/Files/Claude/taskmaster" && python -m pytest tests/test_v4_layout.py::TestV4Allocators -q
  ```
- [ ] Wire into `backlog_add_task`. In `taskmaster/backlog_server.py`, the ID block (`:4046-4064`) currently scans `epic_obj.get("tasks", [])`. Replace the `else:` auto-generate branch (`:4051-4064`) with a version-gated dir-scan:
  ```python
      else:
          # v4: allocate by directory scan (honors concurrent creates); v3: legacy
          # in-memory scan (per-task files aren't the enumeration source there).
          if _detect_schema_version(data) >= SCHEMA_V4:
              new_id = next_task_id(_backlog_path(), epic)
          else:
              tasks = epic_obj.get("tasks", [])
              max_suffix = 0
              prefix = f"{epic}-"
              for t in tasks:
                  tid = t["id"]
                  if tid.startswith(prefix):
                      suffix_str = tid[len(prefix):]
                      try:
                          max_suffix = max(max_suffix, int(suffix_str))
                      except ValueError:
                          pass
              new_id = f"{epic}-{max_suffix + 1:03d}"
  ```
  Add `next_task_id`, `next_task_order` to the `from taskmaster.taskmaster_v3 import (...)` block if not already imported.
- [ ] Stamp `epic` + `order` on the new task. In `backlog_add_task`, the `new_task` dict is built at `:4073-4084`. After `new_task["merge_gate_state"] = ""` (`:4136`) and before the `epic_obj["tasks"].append(new_task)` block (`:4138`), add:
  ```python
      if _detect_schema_version(data) >= SCHEMA_V4:
          new_task["epic"] = epic
          new_task["order"] = next_task_order(_backlog_path(), epic)
  ```
- [ ] Add the add-task integration test to `tests/test_v4_server.py`:
  ```python
  def test_add_task_allocates_id_and_order(v4_project):
      from taskmaster import backlog_server
      out = backlog_server.backlog_add_task(
          epic="e", title="Second", phase="p1", priority="medium")
      assert "e-002" in out
      fm, _ = _read(v4_project / ".taskmaster" / "tasks" / "e-002.md")
      assert fm["epic"] == "e"
      assert fm["order"] == 2.0
  ```
- [ ] Run the new tests and full suite — expect pass:
  ```bash
  cd "C:/Users/gruku/Files/Claude/taskmaster" && python -m pytest tests/test_v4_server.py tests/test_v4_layout.py -q && python -m pytest tests/ -q
  ```
- [ ] Commit:
  ```bash
  git -C "C:/Users/gruku/Files/Claude/taskmaster" add taskmaster/taskmaster_v3.py taskmaster/backlog_server.py tests/test_v4_layout.py tests/test_v4_server.py
  git -C "C:/Users/gruku/Files/Claude/taskmaster" commit -m "feat(v4): dir-scan task-id allocator + fractional order in add_task"
  ```

---

### Task 6: Dirty-scoped save — write only touched task files

Replace `_v4_write_task` (the baseline from Task 3) with a dirty-scoped version: given the load snapshot, a task is written only if it is new or differs from its snapshot counterpart; unchanged tasks are never rewritten. Tasks present in the snapshot but absent from `data` are removed from disk. This is the mechanism that fixes the two-process clobber — a process that only touched task B never rewrites task A's file.

**Files:**
- Modify `taskmaster/taskmaster_v3.py` — replace `_v4_write_task`; add `_v4_snapshot_tasks` + deletion sweep in `save_v4`.
- Modify `tests/test_v4_layout.py` — add `TestDirtyScopedSave`.

**Interfaces:**
- `_v4_write_task(backlog_path, task, snapshot)` now no-ops when `task` equals its snapshot counterpart.
- `save_v4` additionally removes task files for ids in the snapshot but not in `data` (unless the file is under `tasks/archive/`).

Steps:

- [ ] Write the failing test. Add to `tests/test_v4_layout.py`:
  ```python
  import os

  class TestDirtyScopedSave:
      def _project(self, tmp_path):
          tm = tmp_path / ".taskmaster"
          (tm / "tasks").mkdir(parents=True)
          bp = tm / "backlog.yaml"
          bp.write_text(yaml.dump({"meta": {"schema_version": 4}, "epics": [], "phases": []}))
          data = {"meta": {"schema_version": 4}, "phases": [],
                  "epics": [{"id": "e", "name": "E", "tasks": [
                      {"id": "e-001", "title": "A", "epic": "e", "order": 1.0},
                      {"id": "e-002", "title": "B", "epic": "e", "order": 2.0},
                  ]}]}
          v3.save_v4(bp, data)   # baseline write of both files
          return bp, data

      def test_unchanged_task_file_not_rewritten(self, tmp_path):
          import copy
          bp, data = self._project(tmp_path)
          snapshot = copy.deepcopy(data)
          f1 = bp.parent / "tasks" / "e-001.md"
          f2 = bp.parent / "tasks" / "e-002.md"
          m1_before, m2_before = f1.stat().st_mtime_ns, f2.stat().st_mtime_ns
          # Touch only e-002 in memory.
          data["epics"][0]["tasks"][1]["title"] = "B-renamed"
          # Make mtime resolution observable.
          os.utime(f1, ns=(m1_before, m1_before))
          os.utime(f2, ns=(m2_before, m2_before))
          v3.save_v4(bp, data, snapshot=snapshot)
          assert f1.stat().st_mtime_ns == m1_before  # unchanged task not rewritten
          fm2, _ = v3.read_task_file(f2)
          assert fm2["title"] == "B-renamed"

      def test_new_task_written(self, tmp_path):
          import copy
          bp, data = self._project(tmp_path)
          snapshot = copy.deepcopy(data)
          data["epics"][0]["tasks"].append(
              {"id": "e-003", "title": "C", "epic": "e", "order": 3.0})
          v3.save_v4(bp, data, snapshot=snapshot)
          assert (bp.parent / "tasks" / "e-003.md").exists()

      def test_removed_task_file_deleted(self, tmp_path):
          import copy
          bp, data = self._project(tmp_path)
          snapshot = copy.deepcopy(data)
          data["epics"][0]["tasks"] = [t for t in data["epics"][0]["tasks"] if t["id"] != "e-002"]
          v3.save_v4(bp, data, snapshot=snapshot)
          assert not (bp.parent / "tasks" / "e-002.md").exists()
          assert (bp.parent / "tasks" / "e-001.md").exists()
  ```
- [ ] Run — expect failure (baseline rewrites everything, so `test_unchanged_task_file_not_rewritten` fails on mtime; deletion test fails):
  ```bash
  cd "C:/Users/gruku/Files/Claude/taskmaster" && python -m pytest tests/test_v4_layout.py::TestDirtyScopedSave -q
  ```
- [ ] Commit failing test:
  ```bash
  git -C "C:/Users/gruku/Files/Claude/taskmaster" add tests/test_v4_layout.py
  git -C "C:/Users/gruku/Files/Claude/taskmaster" commit -m "test(v4): dirty-scoped save writes only touched files (failing)"
  ```
- [ ] Implement. In `taskmaster/taskmaster_v3.py`, replace `_v4_write_task` (added in Task 3) with:
  ```python
  def _v4_snapshot_tasks(snapshot: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
      """Flatten a load snapshot into {task_id: task_dict} for dirty diffing."""
      index: dict[str, dict[str, Any]] = {}
      if not snapshot:
          return index
      for epic in snapshot.get("epics", []):
          for task in epic.get("tasks", []):
              tid = task.get("id")
              if tid:
                  index[tid] = task
      return index


  def _v4_write_task(
      backlog_path: Path, task: dict[str, Any], snapshot: dict[str, Any] | None
  ) -> None:
      """Write one task file, dirty-scoped: skip when the task is byte-identical
      to its snapshot counterpart (so a save that touched other tasks never
      rewrites this one — the two-process clobber fix)."""
      snap_index = _v4_snapshot_tasks(snapshot)
      prior = snap_index.get(task["id"])
      if prior is not None and prior == task:
          return  # unchanged since load — do not touch the file
      fm, body = task_v4_to_file(task)
      write_task_file(task_file_path(backlog_path, task["id"]), fm, body)
  ```
  Note: recomputing `_v4_snapshot_tasks` per task is O(n²); acceptable at backlog scale, and Task 7 hoists it. If you prefer, compute the index once in `save_v4` and pass it down — but keep the public `save_v4` signature unchanged.
- [ ] Add the deletion sweep to `save_v4`. In `save_v4`, after the task-writing loop (step 1) and before the epic/phase block (step 2), add:
  ```python
      # Delete task files for ids removed since load (never touch archived files —
      # archival is a move into tasks/archive/, handled by the archive tool).
      live_ids = {t.get("id") for epic in data.get("epics", []) for t in epic.get("tasks", [])}
      for tid in _v4_snapshot_tasks(snapshot):
          if tid not in live_ids:
              _remove_entity_file(task_file_path(backlog_path, tid))
  ```
- [ ] Run the dirty-scope tests and full suite — expect pass:
  ```bash
  cd "C:/Users/gruku/Files/Claude/taskmaster" && python -m pytest tests/test_v4_layout.py -q && python -m pytest tests/ -q
  ```
- [ ] Commit:
  ```bash
  git -C "C:/Users/gruku/Files/Claude/taskmaster" add taskmaster/taskmaster_v3.py
  git -C "C:/Users/gruku/Files/Claude/taskmaster" commit -m "feat(v4): dirty-scoped save (write only touched task files)"
  ```

---

### Task 7: Merge-aware save — three-way field-merge on concurrent disk change

Before writing a dirty task, if its on-disk file changed since load (its current content differs from what the snapshot would have serialized), do a three-way field-merge: base = snapshot, ours = in-memory, theirs = disk. Disjoint fields both land; a field changed only on disk is preserved; a field changed in memory (including this-epic same-field conflicts) wins; body: in-memory wins when this process edited it, else disk's body is kept. This is the single-machine, two-process safety net; the full cross-branch conflict policy (sync notes, preserved bodies) is epic 3.

**Files:**
- Modify `taskmaster/taskmaster_v3.py` — add `_three_way_merge_fields`, `_merge_task_with_disk`; call from `_v4_write_task`.
- Modify `tests/test_v4_layout.py` — add `TestConcurrentDiskMerge`.

**Interfaces:**
- Produces `_three_way_merge_fields(base, ours, theirs) -> dict` — per-key three-way merge; local (`ours`) wins when both sides changed.
- `_v4_write_task` re-reads the on-disk file when it differs from the snapshot serialization and writes the merged result.

Steps:

- [ ] Write the failing test. Add to `tests/test_v4_layout.py`:
  ```python
  class TestConcurrentDiskMerge:
      def _project(self, tmp_path):
          import copy
          tm = tmp_path / ".taskmaster"
          (tm / "tasks").mkdir(parents=True)
          bp = tm / "backlog.yaml"
          bp.write_text(yaml.dump({"meta": {"schema_version": 4}, "epics": [], "phases": []}))
          data = {"meta": {"schema_version": 4}, "phases": [],
                  "epics": [{"id": "e", "name": "E", "tasks": [
                      {"id": "e-001", "title": "A", "epic": "e", "order": 1.0,
                       "status": "todo", "priority": "medium"},
                  ]}]}
          v3.save_v4(bp, data)
          return bp, data, copy.deepcopy(data)

      def test_disjoint_disk_field_preserved(self, tmp_path):
          bp, data, snapshot = self._project(tmp_path)
          # Another process adds `assignee` on disk (a field we never touched).
          f = bp.parent / "tasks" / "e-001.md"
          fm, body = v3.read_task_file(f)
          fm["assignee"] = "jdoe"
          v3.write_task_file(f, fm, body)
          # We change only `status` in memory.
          data["epics"][0]["tasks"][0]["status"] = "in-progress"
          v3.save_v4(bp, data, snapshot=snapshot)
          fm2, _ = v3.read_task_file(f)
          assert fm2["status"] == "in-progress"   # our change
          assert fm2["assignee"] == "jdoe"          # disk-only change preserved

      def test_same_field_in_memory_wins(self, tmp_path):
          bp, data, snapshot = self._project(tmp_path)
          f = bp.parent / "tasks" / "e-001.md"
          fm, body = v3.read_task_file(f)
          fm["title"] = "disk title"
          v3.write_task_file(f, fm, body)
          data["epics"][0]["tasks"][0]["title"] = "memory title"
          v3.save_v4(bp, data, snapshot=snapshot)
          fm2, _ = v3.read_task_file(f)
          assert fm2["title"] == "memory title"

      def test_disk_only_change_kept_when_field_untouched(self, tmp_path):
          bp, data, snapshot = self._project(tmp_path)
          f = bp.parent / "tasks" / "e-001.md"
          fm, body = v3.read_task_file(f)
          fm["title"] = "disk title"
          v3.write_task_file(f, fm, body)
          # We change a DIFFERENT field, leaving title at its snapshot value.
          data["epics"][0]["tasks"][0]["status"] = "done"
          v3.save_v4(bp, data, snapshot=snapshot)
          fm2, _ = v3.read_task_file(f)
          assert fm2["title"] == "disk title"   # remote change survives
          assert fm2["status"] == "done"
  ```
- [ ] Run — expect failure (blind dirty write overwrites disk-only fields):
  ```bash
  cd "C:/Users/gruku/Files/Claude/taskmaster" && python -m pytest tests/test_v4_layout.py::TestConcurrentDiskMerge -q
  ```
- [ ] Commit failing test:
  ```bash
  git -C "C:/Users/gruku/Files/Claude/taskmaster" add tests/test_v4_layout.py
  git -C "C:/Users/gruku/Files/Claude/taskmaster" commit -m "test(v4): three-way merge on concurrent disk change (failing)"
  ```
- [ ] Implement. In `taskmaster/taskmaster_v3.py`, add near the other v4 helpers:
  ```python
  _MISSING = object()


  def _three_way_merge_fields(
      base: dict[str, Any], ours: dict[str, Any], theirs: dict[str, Any]
  ) -> dict[str, Any]:
      """Per-key three-way merge. base = value at load, ours = in-memory,
      theirs = current disk. Rules (epic 1 — full sync policy is epic 3):
        - both sides equal            -> that value
        - only ours changed vs base   -> ours (includes deletion)
        - only theirs changed vs base -> theirs (disjoint remote edit lands)
        - both changed (conflict)     -> ours wins (in-memory truth this epic)
      A key deleted on one side (present in base, absent that side) is treated
      as that side's change.
      """
      result: dict[str, Any] = {}
      for key in set(base) | set(ours) | set(theirs):
          b = base.get(key, _MISSING)
          o = ours.get(key, _MISSING)
          t = theirs.get(key, _MISSING)
          if o == t:
              chosen = o
          elif o != b:          # local changed (or deleted) -> local wins
              chosen = o
          elif t != b:          # only remote changed -> remote lands
              chosen = t
          else:                 # unreachable (o==b and t==b implies o==t)
              chosen = o
          if chosen is not _MISSING:
              result[key] = chosen
      return result


  def _merge_task_with_disk(
      base_task: dict[str, Any], mem_task: dict[str, Any], disk_path: Path
  ) -> tuple[dict[str, Any], str]:
      """Three-way merge an in-memory task against its current on-disk file.
      Returns (merged_frontmatter, merged_body)."""
      base_fm, base_body = task_v4_to_file(base_task)
      mem_fm, mem_body = task_v4_to_file(mem_task)
      disk_fm, disk_body = read_task_file(disk_path)
      merged_fm = _three_way_merge_fields(base_fm, mem_fm, disk_fm)
      # Body: in-memory wins when this process edited it vs base, else keep disk.
      merged_body = mem_body if mem_body != base_body else disk_body
      return merged_fm, merged_body
  ```
- [ ] Update `_v4_write_task` to detect on-disk change and merge. Replace its write tail so it reads:
  ```python
  def _v4_write_task(
      backlog_path: Path, task: dict[str, Any], snapshot: dict[str, Any] | None
  ) -> None:
      """Write one task file, dirty-scoped and merge-aware. Skips unchanged
      tasks; three-way merges when the on-disk file diverged from the snapshot
      since load (concurrent writer)."""
      snap_index = _v4_snapshot_tasks(snapshot)
      prior = snap_index.get(task["id"])
      if prior is not None and prior == task:
          return  # unchanged since load
      path = task_file_path(backlog_path, task["id"])
      if prior is not None and path.exists():
          disk_fm, disk_body = read_task_file(path)
          base_fm, base_body = task_v4_to_file(prior)
          if (disk_fm, disk_body) != (base_fm, base_body):
              # File changed on disk since we loaded it — merge instead of clobber.
              merged_fm, merged_body = _merge_task_with_disk(prior, task, path)
              write_task_file(path, merged_fm, merged_body)
              return
      fm, body = task_v4_to_file(task)
      write_task_file(path, fm, body)
  ```
- [ ] Run the merge tests and full suite — expect pass:
  ```bash
  cd "C:/Users/gruku/Files/Claude/taskmaster" && python -m pytest tests/test_v4_layout.py -q && python -m pytest tests/ -q
  ```
- [ ] Commit:
  ```bash
  git -C "C:/Users/gruku/Files/Claude/taskmaster" add taskmaster/taskmaster_v3.py
  git -C "C:/Users/gruku/Files/Claude/taskmaster" commit -m "feat(v4): merge-aware save (three-way field merge on disk divergence)"
  ```

---

### Task 8: Two-process, one-machine clobber test

The gate test from the spec (§11): two independent `_load` → mutate-different-task → `_save` cycles against one `.taskmaster/` dir, interleaved so the second saves against a stale snapshot, must not lose the first writer's change. `threading.Lock` never covered this; dirty-scoping + merge do. This task adds no production code — it is the integration proof that Tasks 6-7 hold.

**Files:**
- Create `tests/test_v4_two_process.py`.

**Interfaces:** consumes `backlog_server._load` / `_save` and the v4 fixture shape from Task 4.

Steps:

- [ ] Write the test (it should PASS immediately if Tasks 6-7 are correct; if it fails, the merge/dirty logic has a gap — fix that, not the test):
  ```python
  """Two interleaved load/save cycles on one machine must not clobber."""
  from __future__ import annotations

  import copy
  import sys
  from pathlib import Path

  import pytest
  import yaml

  sys.path.insert(0, str(Path(__file__).parent.parent))


  @pytest.fixture()
  def v4_two_task_project(tmp_path, monkeypatch):
      from taskmaster import backlog_server, taskmaster_v3 as v3
      tm = tmp_path / ".taskmaster"
      (tm / "tasks").mkdir(parents=True)
      (tm / "PROGRESS.md").write_text("## Changelog\n", encoding="utf-8")
      backlog = {"meta": {"project": "t", "updated": "", "schema_version": 4},
                 "epics": [{"id": "e", "name": "E", "status": "active"}],
                 "phases": [{"id": "p1", "name": "P1", "status": "active"}]}
      (tm / "backlog.yaml").write_text(yaml.dump(backlog), encoding="utf-8")
      for i in (1, 2):
          t = {"id": f"e-00{i}", "title": f"T{i}", "epic": "e", "order": float(i),
               "status": "todo", "priority": "medium"}
          fm, body = v3.task_v4_to_file(t)
          v3.write_task_file(tm / "tasks" / f"e-00{i}.md", fm, body)
      monkeypatch.setattr(backlog_server, "ROOT", tmp_path)
      monkeypatch.setattr(backlog_server, "CONFIG_PATH", tm / "taskmaster.json")
      monkeypatch.setattr(backlog_server, "LEGACY_CONFIG_PATH", tmp_path / ".claude" / "taskmaster.json")
      monkeypatch.chdir(tmp_path)
      return tmp_path


  def test_interleaved_saves_no_clobber(v4_two_task_project):
      from taskmaster import backlog_server

      # Process A loads.
      data_a = backlog_server._load()
      snap_a = copy.deepcopy(backlog_server._LOAD_SNAPSHOT)

      # Process B loads (same starting state), edits e-002, saves.
      data_b = backlog_server._load()
      snap_b = copy.deepcopy(backlog_server._LOAD_SNAPSHOT)
      backlog_server._find_task(data_b, "e-002")[0]["title"] = "B-edited-2"
      backlog_server._LOAD_SNAPSHOT = snap_b
      backlog_server._save(data_b)

      # Process A (stale snapshot) edits e-001, saves — must NOT revert e-002.
      backlog_server._find_task(data_a, "e-001")[0]["title"] = "A-edited-1"
      backlog_server._LOAD_SNAPSHOT = snap_a
      backlog_server._save(data_a)

      # Reload fresh: both edits survive.
      final = backlog_server._load()
      titles = {t["id"]: t["title"] for e in final["epics"] for t in e["tasks"]}
      assert titles["e-001"] == "A-edited-1"
      assert titles["e-002"] == "B-edited-2"
  ```
- [ ] Run — expect pass:
  ```bash
  cd "C:/Users/gruku/Files/Claude/taskmaster" && python -m pytest tests/test_v4_two_process.py -q
  ```
- [ ] Commit:
  ```bash
  git -C "C:/Users/gruku/Files/Claude/taskmaster" add tests/test_v4_two_process.py
  git -C "C:/Users/gruku/Files/Claude/taskmaster" commit -m "test(v4): two-process interleaved save no-clobber gate"
  ```

---

### Task 9: Relocate `viewer.json`, `auto/`, `PROGRESS.md`, `meta.updated` into `local/`

Machine-local, non-shared state moves under `.taskmaster/local/` so it never travels on the state branch (epic 3) and never participates in dirty-scoped merges. For v4 projects: `viewer.json` → `local/viewer.json`; `auto/` → `local/auto/`; `PROGRESS.md` → `local/PROGRESS.md`; derived `meta.updated` → `local/cache/meta.json`. v3 projects keep the old paths (version-gated). Viewer read paths (server-side handlers) follow.

**Files:**
- Modify `taskmaster/taskmaster_v3.py` — `_resolve_artifact_root` stays the parent; add `_local_dir(backlog_path_or_root)` helper; `viewer_prefs_path` (`:3516`) and any `auto/` / `state.json` path builders route through `local/` when the project is v4.
- Modify `taskmaster/backlog_server.py` — `_progress_path` (`:298`) and `_mutate_and_save` (`:835`) / `regenerate_progress_dashboard` (`:745`) write PROGRESS.md into `local/` for v4; `meta.updated` cached to `local/cache/meta.json`.
- Modify `tests/test_v4_layout.py` / `tests/test_v4_server.py` — add `TestLocalRelocation`.

**Interfaces:**
- Produces `local_dir(backlog_path: Path) -> Path` = `backlog_path.parent / "local"` (created on demand).
- v4 `viewer_prefs_path()` returns `<artifact_root>/local/viewer.json`; v3 unchanged.

Steps:

- [ ] Confirm the current auto/state paths. Grep first so you route every one:
  ```bash
  cd "C:/Users/gruku/Files/Claude/taskmaster" && grep -rn '"auto"\|auto/\|state.json\|viewer.json\|PROGRESS.md' taskmaster/taskmaster_v3.py taskmaster/backlog_server.py
  ```
  Route each hit that builds a machine-local path through `local/` under the v4 branch; leave the v3 branch as-is.
- [ ] Write the failing test. Add to `tests/test_v4_server.py`:
  ```python
  class TestLocalRelocation:
      def test_progress_written_under_local(self, v4_project):
          from taskmaster import backlog_server
          data = backlog_server._load()
          backlog_server._mutate_and_save(data)
          assert (v4_project / ".taskmaster" / "local" / "PROGRESS.md").exists()
          # legacy location not (re)created by a v4 save
          # (a pre-existing .taskmaster/PROGRESS.md from the fixture may remain,
          #  but the freshly written dashboard lives under local/)

      def test_viewer_prefs_under_local(self, v4_project):
          from taskmaster import taskmaster_v3 as v3
          p = v3.viewer_prefs_path()
          assert p.parent.name == "local"

      def test_meta_updated_cached_locally(self, v4_project):
          import json
          from taskmaster import backlog_server
          data = backlog_server._load()
          backlog_server._save(data)
          cache = v4_project / ".taskmaster" / "local" / "cache" / "meta.json"
          assert cache.exists()
          assert "updated" in json.loads(cache.read_text())
  ```
  Note: the `v4_project` fixture writes `.taskmaster/PROGRESS.md` for the v3-style `regenerate_progress_dashboard` precondition; the assertion checks the *new* `local/PROGRESS.md` is produced. Do not require the legacy file's absence.
- [ ] Run — expect failure:
  ```bash
  cd "C:/Users/gruku/Files/Claude/taskmaster" && python -m pytest tests/test_v4_server.py::TestLocalRelocation -q
  ```
- [ ] Commit failing test:
  ```bash
  git -C "C:/Users/gruku/Files/Claude/taskmaster" add tests/test_v4_server.py
  git -C "C:/Users/gruku/Files/Claude/taskmaster" commit -m "test(v4): local/ relocation for viewer/auto/progress/meta (failing)"
  ```
- [ ] Add `local_dir` + version detection helper. In `taskmaster/taskmaster_v3.py`, near `_resolve_artifact_root` (`:299`):
  ```python
  def local_dir(backlog_path: Path) -> Path:
      """Machine-local, never-synced state dir: .taskmaster/local/."""
      return backlog_path.parent / "local"


  def _is_v4_project(artifact_root: Path) -> bool:
      """True when the backlog at `artifact_root` declares schema_version >= 4."""
      bp = artifact_root / "backlog.yaml"
      if not bp.exists():
          return False
      try:
          raw = yaml.safe_load(bp.read_text(encoding="utf-8")) or {}
      except Exception:
          return False
      return detect_schema_version(raw) >= SCHEMA_V4
  ```
- [ ] Route `viewer_prefs_path`. Replace `viewer_prefs_path` (`:3516-3517`) with:
  ```python
  def viewer_prefs_path() -> Path:
      root = _resolve_artifact_root()
      if _is_v4_project(root):
          return root / "local" / "viewer.json"
      return root / "viewer.json"
  ```
- [ ] Route PROGRESS.md + meta cache in `backlog_server.py`. Update `_progress_path` (`:298`) to return the v4 local path when the project is v4:
  ```python
  def _progress_path() -> Path:
      backlog, progress = _resolve_paths()
      if _detect_schema_version(yaml.safe_load(backlog.read_text(encoding="utf-8")) or {}) >= SCHEMA_V4:
          return backlog.parent / "local" / "PROGRESS.md"
      return progress
  ```
  In `_save`, in the v4 branch, cache `meta.updated` locally instead of writing it into `backlog.yaml`:
  ```python
          if version >= SCHEMA_V4:
              _write_local_meta_cache(bp, {"updated": _today()})
              _save_v4(bp, data, snapshot=_LOAD_SNAPSHOT)
  ```
  Add the helper near `_save`:
  ```python
  def _write_local_meta_cache(backlog_path: Path, payload: dict) -> None:
      import json
      cache_dir = backlog_path.parent / "local" / "cache"
      cache_dir.mkdir(parents=True, exist_ok=True)
      _atomic_write(cache_dir / "meta.json", json.dumps(payload, indent=2))
  ```
  Ensure `regenerate_progress_dashboard` (`:745`) reads/writes `_progress_path()` (it should already; if it hard-codes, point it at `_progress_path()`), and that it creates the parent dir (`local/`) before writing — add `path.parent.mkdir(parents=True, exist_ok=True)` guard if missing.
- [ ] For any `auto/` or `state.json` path builder found by the grep: add the v4 branch returning `<root>/local/auto/...`. (If none exist in these two files — auto-mode was removed per project memory — note that in the commit body and skip.)
- [ ] Run the relocation tests and full suite — expect pass:
  ```bash
  cd "C:/Users/gruku/Files/Claude/taskmaster" && python -m pytest tests/test_v4_server.py -q && python -m pytest tests/ -q
  ```
- [ ] Commit:
  ```bash
  git -C "C:/Users/gruku/Files/Claude/taskmaster" add taskmaster/taskmaster_v3.py taskmaster/backlog_server.py tests/test_v4_server.py
  git -C "C:/Users/gruku/Files/Claude/taskmaster" commit -m "feat(v4): relocate viewer.json/auto/PROGRESS/meta into local/"
  ```

---

### Task 10: One-shot v3→v4 migration + gated MCP tool

`migrate_v3_to_v4` converts a loaded v3 project to the v4 layout: light fields from `backlog.yaml` `epics[].tasks[]` merge into each `tasks/<id>.md` with new `epic:` + `order:` (order from current list position: 1.0, 2.0, …); `backlog.yaml` shrinks to meta+phases+epic-defs; `local/` is created and `viewer.json` + `auto/` move into it; `snapshots/` is deleted; `schema_version` stamps to 4. Idempotent (re-run on v4 = no-op). Exposed as `backlog_migrate_v4`, gated exactly like `backlog_migrate_v3` (`backlog_server.py:1863`).

**Files:**
- Modify `taskmaster/taskmaster_v3.py` — add `migrate_v3_to_v4` after `migrate_v2_to_v3` (ends ~`:1081`).
- Modify `taskmaster/backlog_server.py` — add `backlog_migrate_v4` MCP tool next to `backlog_migrate_v3` (`:1863`).
- Create `tests/test_v4_migration.py`.

**Interfaces:**
- Produces `migrate_v3_to_v4(backlog_path: Path) -> dict` — summary `{status: "migrated"|"already_v4", tasks_total, schema_before, schema_after}`.
- Produces MCP tool `backlog_migrate_v4() -> str`.

Steps:

- [ ] Write the failing golden-dir test. Create `tests/test_v4_migration.py`:
  ```python
  """v3 -> v4 migration: light fields into task files, slim backlog, local/ moves."""
  from __future__ import annotations

  import sys
  from pathlib import Path

  import pytest
  import yaml

  sys.path.insert(0, str(Path(__file__).parent.parent))

  from taskmaster import taskmaster_v3 as v3  # noqa: E402


  def _v3_project(tmp_path):
      """A v3 project: tasks live in backlog.yaml epics[].tasks[]; heavy fields
      already in tasks/<id>.md (the v3 invariant)."""
      tm = tmp_path / ".taskmaster"
      (tm / "tasks").mkdir(parents=True)
      backlog = {"meta": {"project": "t", "schema_version": 3, "updated": "2026-07-01"},
                 "epics": [{"id": "e", "name": "E", "status": "active", "tasks": [
                     {"id": "e-001", "title": "First", "status": "todo", "priority": "high"},
                     {"id": "e-002", "title": "Second", "status": "done", "priority": "low"},
                 ]}],
                 "phases": [{"id": "p1", "name": "P1"}]}
      bp = tm / "backlog.yaml"
      bp.write_text(yaml.dump(backlog), encoding="utf-8")
      # e-001 has a heavy body file (v3 shape).
      v3.write_task_file(tm / "tasks" / "e-001.md",
                         {"id": "e-001", "title": "First", "notes": "important"},
                         "## Spec\n\nbody")
      (tm / "viewer.json").write_text('{"use_v3": true}', encoding="utf-8")
      (tm / "snapshots").mkdir()
      (tm / "snapshots" / "old.json").write_text("{}", encoding="utf-8")
      return bp


  def test_migration_moves_all_fields_to_task_files(tmp_path):
      bp = _v3_project(tmp_path)
      summary = v3.migrate_v3_to_v4(bp)
      assert summary["status"] == "migrated"
      assert summary["schema_after"] == v3.SCHEMA_V4
      # backlog.yaml is slim: no task lists, schema 4.
      on_disk = yaml.safe_load(bp.read_text())
      assert on_disk["meta"]["schema_version"] == 4
      assert "tasks" not in on_disk["epics"][0]
      # every task now a file with epic + order + light fields.
      fm1, body1 = v3.read_task_file(bp.parent / "tasks" / "e-001.md")
      assert fm1["epic"] == "e" and fm1["order"] == 1.0
      assert fm1["priority"] == "high" and fm1["notes"] == "important"
      assert body1.strip() == "## Spec\n\nbody"
      fm2, _ = v3.read_task_file(bp.parent / "tasks" / "e-002.md")
      assert fm2["epic"] == "e" and fm2["order"] == 2.0 and fm2["status"] == "done"

  def test_migration_moves_local_and_deletes_snapshots(tmp_path):
      bp = _v3_project(tmp_path)
      v3.migrate_v3_to_v4(bp)
      assert (bp.parent / "local" / "viewer.json").exists()
      assert not (bp.parent / "viewer.json").exists()
      assert not (bp.parent / "snapshots").exists()

  def test_migration_idempotent(tmp_path):
      bp = _v3_project(tmp_path)
      v3.migrate_v3_to_v4(bp)
      again = v3.migrate_v3_to_v4(bp)
      assert again["status"] == "already_v4"

  def test_round_trip_after_migration(tmp_path):
      bp = _v3_project(tmp_path)
      v3.migrate_v3_to_v4(bp)
      data = v3.load_v4(bp)
      ids = [t["id"] for e in data["epics"] for t in e["tasks"]]
      assert ids == ["e-001", "e-002"]
  ```
- [ ] Run — expect failure (`AttributeError: ... 'migrate_v3_to_v4'`):
  ```bash
  cd "C:/Users/gruku/Files/Claude/taskmaster" && python -m pytest tests/test_v4_migration.py -q
  ```
- [ ] Commit failing test:
  ```bash
  git -C "C:/Users/gruku/Files/Claude/taskmaster" add tests/test_v4_migration.py
  git -C "C:/Users/gruku/Files/Claude/taskmaster" commit -m "test(v4): v3->v4 migration golden-dir (failing)"
  ```
- [ ] Implement. In `taskmaster/taskmaster_v3.py`, after `migrate_v2_to_v3` (ends ~`:1081`) insert:
  ```python
  def migrate_v3_to_v4(backlog_path: Path) -> dict[str, Any]:
      """Convert a v3 backlog (tasks in backlog.yaml epics[].tasks[]) to v4
      (every task field in tasks/<id>.md, backlog.yaml slim). Idempotent.

      Steps (spec §10):
        1. Load via load_v3 (merges heavy task files back in), then stamp each
           task with epic: + order: (order from list position: 1.0, 2.0, ...).
        2. save_v4 (snapshot=None -> writes every task file, slim backlog.yaml).
        3. Create local/; move viewer.json + auto/ into local/; delete snapshots/.
        4. schema_version -> 4.
      """
      raw = yaml.safe_load(backlog_path.read_text(encoding="utf-8")) or {}
      before = detect_schema_version(raw)
      if before >= SCHEMA_V4:
          return {"status": "already_v4",
                  "tasks_total": len(iter_task_files(backlog_path)),
                  "schema_before": before, "schema_after": before}

      data = load_v3(backlog_path)  # tasks[] populated, heavy fields merged in
      tasks_total = 0
      for epic in data.get("epics", []):
          eid = epic.get("id")
          for pos, task in enumerate(epic.get("tasks", []), start=1):
              task["epic"] = eid
              task.setdefault("order", float(pos))
              tasks_total += 1
      data.setdefault("meta", {})["schema_version"] = SCHEMA_V4

      save_v4(backlog_path, data, snapshot=None)

      # Move machine-local state under local/.
      parent = backlog_path.parent
      ldir = parent / "local"
      ldir.mkdir(parents=True, exist_ok=True)
      for name in ("viewer.json", "auto"):
          src = parent / name
          if src.exists():
              os.replace(src, ldir / name)
      snaps = parent / "snapshots"
      if snaps.is_dir():
          import shutil
          shutil.rmtree(snaps, ignore_errors=True)

      return {"status": "migrated", "tasks_total": tasks_total,
              "schema_before": before, "schema_after": SCHEMA_V4}
  ```
  Ensure `import os` is already present at module top (it is — `atomic_write` uses `os.replace`).
- [ ] Add the gated MCP tool. In `taskmaster/backlog_server.py`, after `backlog_migrate_v3` (ends ~`:1910`) add a sibling tool mirroring its gate and viewer flip:
  ```python
  @mcp.tool()
  def backlog_migrate_v4() -> str:
      """Migrate this project's backlog to v4 layout (sharded per-task storage).

      v4 moves EVERY task field into tasks/<id>.md (frontmatter + body); the
      slim backlog.yaml keeps only meta, phases, and epic definitions. This is
      the team-collaboration foundation: dirty-scoped, merge-aware saves so two
      writers never clobber each other. Idempotent — running on a v4 backlog is
      a no-op. Machine-local state (viewer.json, auto/) moves into local/;
      snapshots/ is deleted.
      """
      bp = _backlog_path()
      if not bp.exists():
          return f"Error: no backlog found at {bp}. Run `backlog_init` first."
      summary = _migrate_v3_to_v4(bp)
      if summary["status"] == "already_v4":
          return (f"Already on v4 — {summary['tasks_total']} tasks, no changes made.\n"
                  f"Backlog at: {bp.relative_to(ROOT)}")
      return (f"Migrated v3 -> v4.\n"
              f"- Tasks: {summary['tasks_total']} (all fields now in tasks/<id>.md)\n"
              f"- Index: {bp.relative_to(ROOT)} (slim — no task lists)\n"
              f"- Local state moved into local/; snapshots/ removed.\n"
              f"- Restart the MCP server to pick up the new schema.")
  ```
  Add `migrate_v3_to_v4 as _migrate_v3_to_v4` to the import block alongside `_migrate_v2_to_v3`.
- [ ] Run the migration tests and full suite — expect pass:
  ```bash
  cd "C:/Users/gruku/Files/Claude/taskmaster" && python -m pytest tests/test_v4_migration.py -q && python -m pytest tests/ -q
  ```
- [ ] Commit:
  ```bash
  git -C "C:/Users/gruku/Files/Claude/taskmaster" add taskmaster/taskmaster_v3.py taskmaster/backlog_server.py tests/test_v4_migration.py
  git -C "C:/Users/gruku/Files/Claude/taskmaster" commit -m "feat(v4): migrate_v3_to_v4 + gated backlog_migrate_v4 tool"
  ```

---

### Task 11: Validation surfacing + old-layout read-only + flip default to v4

The flip. `backlog_validate` reports orphan `epic:` values (from `data["_orphan_tasks"]`) as errors. Old-layout (v3) projects: reads still work, but the server surfaces a migrate prompt (like the v2→v3 UX) — writes on v3 remain permitted this epic (so nothing breaks), but a `backlog_status`/`start-session` banner nudges migration. `backlog_init` now stamps `schema_version: 4` and creates `tasks/` + `local/` so new projects are born v4. Finally, migrate the shared test fixtures (`conftest.py` `tmp_taskmaster`) to v4 and fix the handful of existing tests that assert raw `backlog.yaml` task lists.

**Files:**
- Modify `taskmaster/backlog_server.py` — `backlog_validate` (grep for its def); `backlog_init` (`:1758`) schema stamp + dir creation; a migrate-prompt banner in `backlog_status` or `_load` warning path.
- Modify `tests/conftest.py` — `tmp_taskmaster` fixture to schema 4 + write task files instead of inline tasks.
- Modify the specific existing tests that read raw `backlog.yaml` task structure (enumerate via grep below).
- Modify `tests/test_v4_layout.py` / a new `tests/test_v4_validate.py` — orphan-epic validation test.

**Interfaces:**
- `backlog_validate` includes an `orphan task` error per id in `_orphan_tasks`.
- `backlog_init` writes `meta.schema_version: 4`.

Steps:

- [ ] Enumerate the existing tests that will break under a v4 default fixture (they read `yaml.safe_load(backlog.yaml)` and index `["tasks"]`):
  ```bash
  cd "C:/Users/gruku/Files/Claude/taskmaster" && grep -rln 'epics"\]\[0\]\["tasks"\]\|\["tasks"\]\[0\]' tests/
  ```
  For each, decide: either (a) route the assertion through the loader (`backlog_server._load()` / `load_v4`) which still exposes `epic["tasks"]`, or (b) read the task file directly. Prefer (a) — it is layout-agnostic.
- [ ] Write the failing validation test. Create `tests/test_v4_validate.py`:
  ```python
  from __future__ import annotations
  import sys
  from pathlib import Path
  import pytest, yaml
  sys.path.insert(0, str(Path(__file__).parent.parent))
  from taskmaster import taskmaster_v3 as v3  # noqa: E402


  def test_validate_reports_orphan_epic(tmp_path):
      tm = tmp_path / ".taskmaster"
      (tm / "tasks").mkdir(parents=True)
      (tm / "backlog.yaml").write_text(yaml.dump(
          {"meta": {"schema_version": 4}, "epics": [{"id": "e", "name": "E"}], "phases": []}))
      fm, body = v3.task_v4_to_file({"id": "x-001", "title": "lost", "epic": "ghost", "order": 1.0})
      v3.write_task_file(tm / "tasks" / "x-001.md", fm, body)
      data = v3.load_v4(tm / "backlog.yaml")
      assert data["_orphan_tasks"] == ["x-001"]
  ```
  Then extend it to assert the server tool surfaces it (adapt once you read `backlog_validate`'s output shape):
  ```python
  def test_backlog_validate_surfaces_orphan(tmp_path, monkeypatch):
      from taskmaster import backlog_server
      tm = tmp_path / ".taskmaster"
      (tm / "tasks").mkdir(parents=True)
      (tm / "PROGRESS.md").write_text("## Changelog\n")
      (tm / "backlog.yaml").write_text(yaml.dump(
          {"meta": {"schema_version": 4}, "epics": [{"id": "e", "name": "E"}], "phases": []}))
      fm, body = v3.task_v4_to_file({"id": "x-001", "title": "lost", "epic": "ghost", "order": 1.0})
      v3.write_task_file(tm / "tasks" / "x-001.md", fm, body)
      monkeypatch.setattr(backlog_server, "ROOT", tmp_path)
      monkeypatch.setattr(backlog_server, "CONFIG_PATH", tm / "taskmaster.json")
      monkeypatch.setattr(backlog_server, "LEGACY_CONFIG_PATH", tmp_path / ".claude" / "taskmaster.json")
      monkeypatch.chdir(tmp_path)
      out = backlog_server.backlog_validate()
      assert "x-001" in out and ("orphan" in out.lower() or "ghost" in out.lower())
  ```
- [ ] Run — expect failure:
  ```bash
  cd "C:/Users/gruku/Files/Claude/taskmaster" && python -m pytest tests/test_v4_validate.py -q
  ```
- [ ] Commit failing test:
  ```bash
  git -C "C:/Users/gruku/Files/Claude/taskmaster" add tests/test_v4_validate.py
  git -C "C:/Users/gruku/Files/Claude/taskmaster" commit -m "test(v4): orphan-epic validation surfacing (failing)"
  ```
- [ ] Implement orphan surfacing in `backlog_validate`. Read the tool first (`grep -n "def backlog_validate" taskmaster/backlog_server.py`), then add to the error accumulation:
  ```python
      for orphan_id in data.get("_orphan_tasks", []):
          errors.append(
              f"Task `{orphan_id}` names an epic that does not exist "
              f"(orphaned `epic:` frontmatter) — fix the task's epic: field.")
  ```
  Match the tool's existing `errors`/return convention (adapt the variable name to what the function uses).
- [ ] Flip `backlog_init` to v4. In `backlog_init` (`:1758`), where the initial backlog dict and `schema_version` are written, stamp `4`, and ensure the created subdirs (`:1841`) include `tasks`, `local`, and `local/cache`:
  ```python
      for sub in ("tasks", "handovers", "issues", "areas", "local", "local/cache"):
  ```
  and set the new backlog's `meta.schema_version = SCHEMA_V4`. Also write PROGRESS.md to `local/PROGRESS.md` for fresh v4 projects (the `progress_rel` at `:1804`).
- [ ] Migrate the shared fixture. In `tests/conftest.py` `tmp_taskmaster` (`:55-74`): stamp `schema_version: 4`, drop `meta.updated` as a save precondition (v4 no longer requires it), create `local/`, and write `local/PROGRESS.md` (keep the legacy `.taskmaster/PROGRESS.md` too for any v3-path test still using it). Because existing tests create tasks via `backlog_add_task` (which now writes task files), the on-disk `backlog.yaml` no longer carries task lists — this is why the raw-yaml assertions in the enumerated tests must move to the loader.
- [ ] Update each enumerated existing test to read through the loader. Example transform for `tests/test_v3_task_writes.py:28-29` (do the analogous change in every file the grep found):
  ```python
  # before:
  #   data = yaml.safe_load(v2_backlog.read_text())
  #   assert data["epics"][0]["tasks"][0]["title"] == "Renamed"
  # after (layout-agnostic):
  from taskmaster.taskmaster_v3 import load_v4, detect_schema_version
  raw = yaml.safe_load(v2_backlog.read_text())
  if detect_schema_version(raw) >= 4:
      data = load_v4(v2_backlog)
  else:
      data = raw
  assert data["epics"][0]["tasks"][0]["title"] == "Renamed"
  ```
  (If a test's fixture is explicitly a v3/v2 backlog with inline tasks, it stays green unchanged — only touch tests whose fixture became v4 via the shared `tmp_taskmaster` change.)
- [ ] Run the FULL suite — this is the flip; expect green:
  ```bash
  cd "C:/Users/gruku/Files/Claude/taskmaster" && python -m pytest tests/ -q
  ```
  Fix any remaining raw-yaml task assertions until green. Do not weaken assertions — route them through the loader.
- [ ] Commit:
  ```bash
  git -C "C:/Users/gruku/Files/Claude/taskmaster" add taskmaster/backlog_server.py tests/conftest.py tests/test_v4_validate.py <each-updated-test-file>
  git -C "C:/Users/gruku/Files/Claude/taskmaster" commit -m "feat(v4): validate orphan epics, default new projects to v4, migrate fixtures"
  ```

---

### Task 12: Version bump + CHANGELOG (major)

Schema break → major bump. Bump `pyproject.toml` and add a `## 5.0.0` CHANGELOG section. The claude-tools `plugin.json` / `marketplace.json` bump is NOT done here — it happens when the submodule pointer is advanced in claude-tools (a separate step, noted below).

**Files:**
- Modify `pyproject.toml` (`:7`).
- Modify `CHANGELOG.md` (top, after the `---` at `:9`).

Steps:

- [ ] Bump the version. In `pyproject.toml`, change line 7:
  ```toml
  version = "5.0.0"
  ```
- [ ] Add the CHANGELOG section. In `CHANGELOG.md`, insert immediately after line 9 (`---`) and before `## 4.4.1`:
  ```markdown
  ## 5.0.0

  **Team relayout — sharded per-task storage (schema_version 4).** Every task
  field (light + heavy) now lives in `tasks/<id>.md` frontmatter + body; the
  slim `backlog.yaml` keeps only meta, phases, and epic definitions (no
  `epics[].tasks[]` lists). Task order within an epic is a new fractional
  `order:` field (ties break by id); epic membership is the task's `epic:`
  field. Saves are dirty-scoped and merge-aware — only touched task files are
  written, and a task whose file changed on disk since load is three-way
  field-merged instead of clobbered — which fixes the stale-in-memory and
  two-process-on-one-machine clobbers. Task IDs allocate by directory scan
  (like `B-NNN`). Machine-local state (`viewer.json`, `auto/`, `PROGRESS.md`,
  derived `meta.updated`) moved under `.taskmaster/local/`; `snapshots/` was
  removed. Migrate with `backlog_migrate_v4` (idempotent, gated); old-layout
  projects load with a migrate prompt. **MCP restart required.** This is epic 1
  of the team-collaboration design; identity, sync, IDs, and team viewer land
  in later releases.
  ```
- [ ] Verify nothing else regressed and the version reads back:
  ```bash
  cd "C:/Users/gruku/Files/Claude/taskmaster" && python -m pytest tests/ -q && grep '^version' pyproject.toml
  ```
  Expected: green suite; `version = "5.0.0"`.
- [ ] Commit:
  ```bash
  git -C "C:/Users/gruku/Files/Claude/taskmaster" add pyproject.toml CHANGELOG.md
  git -C "C:/Users/gruku/Files/Claude/taskmaster" commit -m "chore(release): taskmaster 5.0.0 — team relayout (schema v4)"
  ```

**Final note (out of scope for this plan — do when advancing the submodule in claude-tools):** after this epic merges in the taskmaster repo, advance the `plugins/taskmaster` submodule pointer in claude-tools and bump `plugins/taskmaster/.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json` to `5.0.0` in lockstep (per the claude-tools versioning protocol), then run `python scripts/check_plugin_version_bump.py --base origin/master`. That is a claude-tools change, not a taskmaster change, so it is not planned here.
