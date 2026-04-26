# Taskmaster v2 Features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 5 features from the design-v2 spec: task anchors, task budget per epic, staleness decay, auto-summary for lightweight sessions, and observe untracked work.

**Architecture:** All features are additive — new fields, new parameters, new behavior in existing tools. No breaking changes. Each feature is independent and can be implemented/tested in isolation. The server (`backlog_server.py`) gets the core logic; skills get behavioral changes; docs get updated.

**Tech Stack:** Python (MCP server), Markdown (skills/docs), HTML/JS (viewer for anchors display)

---

## File Map

| File | Changes |
|------|---------|
| `plugins/taskmaster/backlog_server.py` | Anchors field on tasks, budget warning in add_task, last_referenced tracking, auto-summary in complete_task, stale tasks in status output |
| `plugins/taskmaster/backlog-viewer.html` | Display anchors on task cards |
| `plugins/taskmaster/skills/pick-task/SKILL.md` | Display anchors prominently when picking |
| `plugins/taskmaster/skills/start-session/SKILL.md` | Show stale tasks, show untracked commits |
| `plugins/taskmaster/skills/end-session/SKILL.md` | Auto-summary mode for light sessions |
| `plugins/taskmaster/skills/init-taskmaster/SKILL.md` | Budget guidance in task creation |
| `plugins/taskmaster/docs/TASKMASTER.md` | Document new fields and behaviors |
| `plugins/taskmaster/references/task-lifecycle.md` | Document anchors and staleness |

---

### Task 1: Add anchors field to tasks

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py:1031-1048` (backlog_add_task signature + docstring)
- Modify: `plugins/taskmaster/backlog_server.py:1081-1097` (backlog_add_task optional fields)
- Modify: `plugins/taskmaster/backlog_server.py:1538` (ALLOWED_FIELDS)
- Modify: `plugins/taskmaster/backlog_server.py:1544-1560` (backlog_update_task docstring)
- Modify: `plugins/taskmaster/backlog_server.py:1623` (backlog_update_task field handling — add anchors case)
- Modify: `plugins/taskmaster/backlog_server.py:586-601` (backlog_get_task display)
- Modify: `plugins/taskmaster/backlog_server.py:390-411` (_task_context — show anchors on pick)

- [ ] **Step 1: Add "anchors" to ALLOWED_FIELDS**

In `backlog_server.py` at line 1538, add `"anchors"` to the set:
```python
ALLOWED_FIELDS = {"title", "status", "priority", "notes", "branch", "worktree", "blockers", "docs", "depends_on", "sub_repo", "stage", "estimate", "locked_by", "review_instructions", "phase", "anchors"}
```

- [ ] **Step 2: Add anchors parameter to backlog_add_task**

At line 1034, add the parameter:
```python
def backlog_add_task(
    title: str, epic: str, priority: str = "P2", notes: str = "",
    docs: str = "", depends_on: str = "", sub_repo: str = "",
    stage: int | None = None, estimate: str = "", phase: str = "",
    anchors: str = "",
) -> str:
```

Add to the docstring after the `phase` line:
```python
        anchors: Optional comma-separated glob patterns or URLs declaring target files/systems (e.g., "src/auth/**,localhost:3000/api/auth")
```

After the phase optional field block (after line 1097), add:
```python
    if anchors:
        anchor_list = [a.strip() for a in anchors.split(",") if a.strip()]
        new_task["anchors"] = anchor_list
```

- [ ] **Step 3: Add anchors handling to backlog_update_task**

In the field handling chain (after the `elif field == "phase":` block around line 1622), add before the `else:` clause:
```python
    elif field == "anchors":
        if value == "" or value.lower() == "none":
            task.pop("anchors", None)
        else:
            task["anchors"] = [a.strip() for a in value.split(",") if a.strip()]
```

Update the docstring at line 1558 to add:
```
            - anchors: comma-separated glob patterns/URLs, or "" to clear
```

- [ ] **Step 4: Display anchors in backlog_get_task**

At line 592 (the fields list in `backlog_get_task`), add after the Phase line:
```python
        ("Anchors", ", ".join(task["anchors"]) if task.get("anchors") else "—"),
```

- [ ] **Step 5: Display anchors prominently in _task_context (shown on pick)**

In `_task_context` (line 390-411), add after the blockers line (around line 401):
```python
    if task.get("anchors"):
        lines.append(f"**Anchors:** {', '.join(f'`{a}`' for a in task['anchors'])}")
        # Separate file globs from URLs
        file_anchors = [a for a in task["anchors"] if not a.startswith(("http", "localhost"))]
        url_anchors = [a for a in task["anchors"] if a.startswith(("http", "localhost"))]
        if file_anchors:
            lines.append(f"  Files: {', '.join(f'`{a}`' for a in file_anchors)}")
        if url_anchors:
            lines.append(f"  URLs: {', '.join(url_anchors)}")
```

- [ ] **Step 6: Verify**

Run: `python -c "import ast; ast.parse(open('plugins/taskmaster/backlog_server.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 7: Commit**

```bash
git add plugins/taskmaster/backlog_server.py
git commit -m "feat(taskmaster): add anchors field for task target declarations"
```

---

### Task 2: Add task budget warning per epic

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py:1112-1120` (backlog_add_task — after task is appended)

- [ ] **Step 1: Add budget warning after task creation**

In `backlog_add_task`, after the task is appended to the epic (line 1114: `epic_obj["tasks"].append(new_task)`), and after `_mutate_and_save(data)` (line 1116), add a budget check before the return:

```python
    # Budget warning
    budget_warning = ""
    active_count = sum(1 for t in epic_obj.get("tasks", []) if t.get("status") not in ("archived", "done"))
    max_tasks = epic_obj.get("max_tasks", 8)
    if active_count > max_tasks:
        budget_warning = (
            f"\n\n**Warning:** Epic `{epic}` now has {active_count} active tasks (soft cap: {max_tasks}). "
            f"Consider grouping related work into fewer, coarser tasks — tasks should be things you "
            f"might pick up in different sessions, not steps within one session. "
            f"Link a plan document (`docs.plan`) for detailed steps instead."
        )
```

Then append `budget_warning` to the return value. Find the return statement (around line 1126) and append it. The current return looks like:
```python
    return f"Created `{new_id}` — {title} ({priority}, {epic})" + notes_warning
```
Change to:
```python
    return f"Created `{new_id}` — {title} ({priority}, {epic})" + notes_warning + budget_warning
```

- [ ] **Step 2: Add max_tasks to epic schema in backlog_add_epic**

Find `backlog_add_epic` and look at the epic creation dict. No changes needed to the function signature — `max_tasks` is an optional field that can be set via `backlog_update_epic`. The budget check reads it with a default of 8, which is correct.

- [ ] **Step 3: Verify**

Run: `python -c "import ast; ast.parse(open('plugins/taskmaster/backlog_server.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add plugins/taskmaster/backlog_server.py
git commit -m "feat(taskmaster): add task budget warning per epic (soft cap)"
```

---

### Task 3: Add last_referenced staleness tracking

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py:121-127` (_find_task — no change needed, but note this is the lookup)
- Modify: `plugins/taskmaster/backlog_server.py:571-605` (backlog_get_task — update last_referenced)
- Modify: `plugins/taskmaster/backlog_server.py:1155-1213` (backlog_pick_task — update last_referenced)
- Modify: `plugins/taskmaster/backlog_server.py:1288-1359` (backlog_complete_task — update last_referenced)
- Modify: `plugins/taskmaster/backlog_server.py:1544-1627` (backlog_update_task — update last_referenced)
- Modify: `plugins/taskmaster/backlog_server.py:1072-1078` (backlog_add_task — set last_referenced on creation)
- Modify: `plugins/taskmaster/backlog_server.py:415-519` (backlog_status — show stale tasks)

- [ ] **Step 1: Create a helper to touch last_referenced**

Add after the `_phase_stats` function (around line 172):
```python
def _touch_task(task: dict) -> None:
    """Update last_referenced timestamp on a task."""
    task["last_referenced"] = _now()
```

- [ ] **Step 2: Set last_referenced on task creation**

In `backlog_add_task`, after the `new_task` dict is created (line 1078), add:
```python
    new_task["last_referenced"] = _now()
```

Actually, better: just remove the `"notes": notes` from the initial dict and set it after, or simply add after `"notes": notes`:
Add this line after `"notes": notes,` in the new_task dict:
```python
        "last_referenced": _now(),
```

- [ ] **Step 3: Touch task in backlog_get_task**

In `backlog_get_task` (line 578-583), after `task, epic = result`, add:
```python
    _touch_task(task)
    _mutate_and_save(data)
```

Wait — `backlog_get_task` is currently read-only and doesn't save. Making it save on every read would be expensive. Instead, only touch on mutating operations:

Actually, the spec says "Any MCP tool that reads or modifies a task updates last_referenced." Let's follow the spec. But `backlog_get_task` currently doesn't save. We need to add a save. This is a small overhead.

Actually, let's be pragmatic: touch on `backlog_get_task`, `backlog_pick_task`, `backlog_update_task`, `backlog_complete_task`. Skip `backlog_list_tasks` and `backlog_next_available` since those are bulk queries. For `backlog_get_task`, add the save.

In `backlog_get_task` after `task, epic = result` (line 583):
```python
    # Update staleness tracking
    task["last_referenced"] = _now()
    _save(data)  # lightweight save — no full context regen needed for staleness touch
```

Note: use `_save(data)` not `_mutate_and_save(data)` to avoid the overhead of regenerating context/PROGRESS.md for a simple staleness touch.

- [ ] **Step 4: Touch task in backlog_pick_task**

In `backlog_pick_task`, after `task, epic = result` (line 1168), add:
```python
    _touch_task(task)
```

The function already calls `_mutate_and_save` later, so no extra save needed.

- [ ] **Step 5: Touch task in backlog_update_task**

In `backlog_update_task`, after `task, epic = result` (line 1568), add:
```python
    _touch_task(task)
```

The function already calls `_mutate_and_save` later.

- [ ] **Step 6: Touch task in backlog_complete_task**

In `backlog_complete_task`, after `task, epic = result` (line 1325), add:
```python
    _touch_task(task)
```

The function already calls `_mutate_and_save` later.

- [ ] **Step 7: Add stale tasks to backlog_status output**

In `backlog_status` (the function that outputs the dashboard), after the phases section and before the return, add stale task detection:

```python
    # Stale tasks (todo tasks not referenced in 14+ days)
    stale_tasks = []
    for ep in data["epics"]:
        for t in ep.get("tasks", []):
            if t.get("status") != "todo":
                continue
            last_ref = t.get("last_referenced")
            if not last_ref:
                continue
            try:
                ref_str = str(last_ref)
                if "T" in ref_str:
                    ref_date = datetime.fromisoformat(ref_str).date()
                else:
                    ref_date = datetime.strptime(ref_str, "%Y-%m-%d").date()
                days_ago = (date.today() - ref_date).days
                if days_ago >= 14:
                    stale_tasks.append((t, ep, days_ago))
            except (ValueError, TypeError):
                pass
    if stale_tasks:
        stale_tasks.sort(key=lambda x: x[2], reverse=True)
        lines.append(f"\n**Stale tasks** (not referenced in 14+ days):")
        for t, ep, days in stale_tasks[:10]:
            lines.append(f"- `{t['id']}` — {t['title']} — stale {days}d ({ep['id']})")
        lines.append("*Still relevant? Archive with `backlog_archive_task` or touch to refresh.*")
```

- [ ] **Step 8: Add stale tasks to context regeneration**

In `regenerate_context` (the function at line ~232 that builds `data["context"]`), add a `stale` list. Find where `next_up` is built and add after it:

```python
    # Stale tasks
    stale = []
    for ep in data["epics"]:
        for t in ep.get("tasks", []):
            if t.get("status") != "todo":
                continue
            last_ref = t.get("last_referenced")
            if not last_ref:
                continue
            try:
                ref_str = str(last_ref)
                if "T" in ref_str:
                    ref_date = datetime.fromisoformat(ref_str).date()
                else:
                    ref_date = datetime.strptime(ref_str, "%Y-%m-%d").date()
                days_ago = (date.today() - ref_date).days
                if days_ago >= 14:
                    stale.append({"id": t["id"], "title": t["title"], "last_referenced": ref_str, "days_stale": days_ago})
            except (ValueError, TypeError):
                pass
    stale.sort(key=lambda x: x["days_stale"], reverse=True)
    data["context"]["stale"] = stale[:10]
```

- [ ] **Step 9: Verify**

Run: `python -c "import ast; ast.parse(open('plugins/taskmaster/backlog_server.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 10: Commit**

```bash
git add plugins/taskmaster/backlog_server.py
git commit -m "feat(taskmaster): add last_referenced staleness tracking for tasks"
```

---

### Task 4: Add auto-summary for lightweight sessions

**Files:**
- Modify: `plugins/taskmaster/backlog_server.py:1216-1260` (_append_changelog — add auto mode)
- Modify: `plugins/taskmaster/backlog_server.py:1288-1359` (backlog_complete_task — add auto_summary param)
- Modify: `plugins/taskmaster/skills/end-session/SKILL.md` (add auto-summary logic)

- [ ] **Step 1: Add auto-summary format to _append_changelog**

In `_append_changelog` (line 1216), add an `auto` parameter:

```python
def _append_changelog(
    session_title: str,
    done: str,
    decisions: str,
    issues: str,
    tasks_touched: str,
    auto: bool = False,
    auto_stats: str = "",
) -> str:
```

At the top of the function body, add an early return for auto mode:

```python
    title = session_title or "Work session"

    if auto:
        heading = f"### {_today()} — auto"
        entry = f"{heading}\n{auto_stats}\nTasks touched: {tasks_touched}\n"
        # Insert into PROGRESS.md
        try:
            text = _progress_path().read_text(encoding="utf-8")
        except FileNotFoundError:
            return "No PROGRESS.md found."
        marker = "## Changelog"
        idx = text.find(marker)
        if idx == -1:
            return "No changelog section found."
        insert_pos = idx + len(marker)
        new_text = text[:insert_pos] + "\n\n" + entry + text[insert_pos:]
        _progress_path().write_text(new_text, encoding="utf-8")
        return f"\nSession auto-logged to PROGRESS.md."

    heading = f"### {_today()} — {title}"
```

- [ ] **Step 2: Add auto_summary parameter to backlog_complete_task**

Add parameter `auto_summary: bool = False` to the function signature:

```python
def backlog_complete_task(
    task_id: str,
    session_title: str = "",
    done: str = "",
    decisions: str = "",
    issues: str = "",
    tasks_touched: str = "",
    target_status: str = "done",
    auto_summary: bool = False,
) -> str:
```

Add to docstring:
```
        auto_summary: If true, generates a lightweight auto-summary instead of the structured format. Pass auto_stats for the summary content.
```

Actually, let's keep it simpler. The auto_summary just changes how the changelog is written. In the existing changelog append call:

```python
    # Append changelog entry if session summary provided
    changelog_msg = ""
    if auto_summary:
        changelog_msg = _append_changelog(session_title, done, decisions, issues, tasks_touched, auto=True, auto_stats=done)
    elif session_title or done:
        changelog_msg = _append_changelog(session_title, done, decisions, issues, tasks_touched)
```

- [ ] **Step 3: Update end-session skill**

In `plugins/taskmaster/skills/end-session/SKILL.md`, add a section before step 1:

After the "## Steps" heading (line 17), add:

```markdown
0. **Determine summary mode.** Check the session weight:
   - Count commits this session and files changed
   - If the session was **light** (1-2 commits, single-topic work, or user says "quick wrap"):
     - Use **auto-summary mode**: skip the structured Done/Decisions/Issues template
     - Generate a one-line summary from git: `git diff --stat HEAD~N` and commit messages
     - Call `backlog_complete_task` with `auto_summary=true` and pass the git stats as the `done` field
     - Format: "Files changed: N | +X -Y\nCommits: \"msg1\", \"msg2\""
   - If the session was **substantial** (3+ commits, multiple topics, design decisions made):
     - Use **structured mode** (the existing flow below)
   - The user can always override: "give me the full summary" forces structured mode
```

- [ ] **Step 4: Verify**

Run: `python -c "import ast; ast.parse(open('plugins/taskmaster/backlog_server.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/backlog_server.py plugins/taskmaster/skills/end-session/SKILL.md
git commit -m "feat(taskmaster): add auto-summary mode for lightweight sessions"
```

---

### Task 5: Add untracked work observation to start-session

**Files:**
- Modify: `plugins/taskmaster/skills/start-session/SKILL.md` (add untracked commits section)

This is purely a skill-level change — the AI observes git history and reports. No server changes needed since the AI runs the git commands directly.

- [ ] **Step 1: Add untracked work observation to start-session skill**

In `plugins/taskmaster/skills/start-session/SKILL.md`, in the step 3 structured briefing section (around line 27), add after the "Suggested next" bullet:

```markdown
   - **Untracked work** — After showing the dashboard, check for commits since the last session that aren't associated with any tracked task branch:
     1. Get the last session date from `backlog_last_session` output (the `### YYYY-MM-DD` heading)
     2. Run `git log --oneline --since="{last_session_date}" --no-merges` on the main branch
     3. Get the list of tracked task branches from in-progress tasks (their `branch` field)
     4. Any commits on the main branch that aren't in a task branch are "untracked work"
     5. If found, show informatively (not judgmentally):
        ```
        Since last session: N commits outside tracked tasks
          - fix typo in README
          - bump dependencies
        ```
     6. If none found, skip this section silently
```

- [ ] **Step 2: Add stale tasks display to start-session skill**

In the same step 3 section, add after the phase progress bullet:

```markdown
   - **Stale tasks** — if the `backlog_status` output includes stale tasks (tasks not referenced in 14+ days), show them:
     ```
     Stale tasks (not referenced in 14+ days):
       auth-007  Add SAML support        — stale 21d
       api-012   GraphQL migration        — stale 18d
     Still relevant? Say "archive auth-007" or "keep it".
     ```
```

- [ ] **Step 3: Commit**

```bash
git add plugins/taskmaster/skills/start-session/SKILL.md
git commit -m "feat(taskmaster): add untracked work and stale tasks to start-session"
```

---

### Task 6: Display anchors in the viewer

**Files:**
- Modify: `plugins/taskmaster/backlog-viewer.html` (task card rendering to show anchors)

- [ ] **Step 1: Find the task card rendering in the viewer**

Search for where task cards are built in the HTML. Look for where `t.title` and `t.priority` are rendered into card HTML. Add anchors display.

In the task card template (the section that builds card innerHTML), add after the priority/status line:

```javascript
const anchorsHtml = (t.anchors && t.anchors.length)
  ? `<div class="task-anchors" style="font-size:var(--fs-xs);color:var(--text-dim);margin-top:2px">📌 ${t.anchors.map(a => esc(a)).join(', ')}</div>`
  : '';
```

Include `${anchorsHtml}` in the card template.

- [ ] **Step 2: Commit**

```bash
git add plugins/taskmaster/backlog-viewer.html
git commit -m "feat(taskmaster): display task anchors in viewer cards"
```

---

### Task 7: Update documentation

**Files:**
- Modify: `plugins/taskmaster/docs/TASKMASTER.md`
- Modify: `plugins/taskmaster/references/task-lifecycle.md`
- Modify: `plugins/taskmaster/skills/pick-task/SKILL.md`
- Modify: `plugins/taskmaster/skills/init-taskmaster/SKILL.md`

- [ ] **Step 1: Update TASKMASTER.md with new fields**

In the schema section, add to the task fields table:
```markdown
| `anchors` | list[string] | Glob patterns or URLs declaring target files/systems |
| `last_referenced` | string | ISO timestamp, auto-updated when any tool touches this task |
```

In the tool reference table, add note to `backlog_add_task`:
```
New params: `anchors` (comma-separated globs/URLs), tasks get `last_referenced` auto-set
```

Add note to `backlog_complete_task`:
```
New param: `auto_summary` (bool) — lightweight session log for small sessions
```

Add a "### Task Budget" subsection under the Epics section:
```markdown
### Task Budget

Each epic has a soft cap of 8 active (non-archived, non-done) tasks. When `backlog_add_task` pushes an epic past this cap, a warning is returned. The cap is configurable per epic via the `max_tasks` field. Tasks should represent work you'd pick up in different sessions — use plan documents for detailed step breakdowns.
```

Add a "### Staleness" subsection:
```markdown
### Staleness

Tasks track when they were last referenced (`last_referenced` field). Todo tasks not referenced in 14+ days are flagged as stale during `start-session` and in `backlog_status` output. Archive stale tasks or interact with them to refresh the timestamp.
```

- [ ] **Step 2: Update task-lifecycle.md**

Add an "Anchors" row to the concepts table:
```markdown
| **Anchors** | Tasks can declare `anchors` — glob patterns or URLs — to say what files/systems they touch. Displayed prominently on pick. |
```

Add a "Staleness" row:
```markdown
| **Staleness** | `last_referenced` is auto-updated by get/pick/update/complete. Todo tasks stale for 14+ days are flagged in dashboards. |
```

- [ ] **Step 3: Update pick-task skill to mention anchors**

In `plugins/taskmaster/skills/pick-task/SKILL.md`, in step 3 or after the dependency check, add:

```markdown
4. **Show anchors (if present):**
   - If the task has `anchors`, display them prominently:
     "This task is anchored to `src/auth/**`. Expected at `localhost:3000/api/auth`."
   - Remind: "If you find yourself editing files outside these anchors, double-check you're working on the right target."
```

- [ ] **Step 4: Update init-taskmaster skill with budget guidance**

In `plugins/taskmaster/skills/init-taskmaster/SKILL.md`, in step 3a (clean start, around line 55), add after "Help them add tasks under those epics":

```markdown
5. **Budget guidance:** Remind the user: "Aim for 5-8 tasks per epic. Tasks should be things you'd pick up in different sessions. If a task has many steps, create a plan document and link it with `docs.plan` instead of splitting into micro-tasks."
```

- [ ] **Step 5: Commit**

```bash
git add plugins/taskmaster/docs/TASKMASTER.md plugins/taskmaster/references/task-lifecycle.md plugins/taskmaster/skills/pick-task/SKILL.md plugins/taskmaster/skills/init-taskmaster/SKILL.md
git commit -m "docs(taskmaster): document anchors, budget, staleness, auto-summary features"
```

---

### Task 8: Final verification

- [ ] **Step 1: Verify Python parses**

Run: `python -c "import ast; ast.parse(open('plugins/taskmaster/backlog_server.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 2: Grep for consistency**

Run: `grep -n "anchors\|last_referenced\|auto_summary\|budget\|stale" plugins/taskmaster/backlog_server.py | head -30`
Expected: References in the correct locations.

- [ ] **Step 3: Verify no broken references in skills**

Run: `grep -rn "backlog_add_milestone\|backlog_milestone" plugins/taskmaster/skills/`
Expected: Zero results (no leftover milestone references from the previous rename).

- [ ] **Step 4: Final commit if fixups needed**

```bash
git add -A plugins/taskmaster/
git commit -m "chore(taskmaster): final verification and cleanup for v2 features"
```
