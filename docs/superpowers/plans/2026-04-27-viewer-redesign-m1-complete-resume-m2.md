# Viewer Redesign — Resume Handoff (M1 done, M2 next)

**Date opened:** 2026-04-27 (post-M1)
**Status:** Plan 1 Milestone 1 complete (server foundation). Ready to start Milestone 2.
**Branch:** `feature/taskmaster-v3` at `C:\Users\gruku\Files\Claude\claude-tools\.worktrees\taskmaster-v3` (NOT the master checkout)
**Tip commit:** `a656212` (T1.6 _send_json unification)

---

## Resume prompt (paste into next session)

> "Resuming the Taskmaster viewer redesign. M1 is complete; start M2 (Plan 1 Tasks 7–12). Read `docs/superpowers/plans/2026-04-27-viewer-redesign-m1-complete-resume-m2.md` for current state, dispatch templates, and known open nits. Then read `PROGRESS.md` to confirm the next unchecked task is T1.7. All work happens on branch `feature/taskmaster-v3` in the worktree `.worktrees/taskmaster-v3` — NOT on master. Use `superpowers:subagent-driven-development`: per-task loop is implementer subagent → spec reviewer subagent → code quality reviewer subagent → tick PROGRESS.md + plan-file checkboxes → next task. Pause for human checkpoint at the end of M2 (after T1.12)."

---

## Where execution stands

### Plans + progress tracking
- **Source of truth:** `docs/superpowers/plans/PROGRESS.md` on `feature/taskmaster-v3`. T1.1–T1.6 are `[x]`; T1.7 is the first unchecked.
- **Two-place truth:** every checkbox lives in the plan file (`2026-04-26-viewer-redesign-plan-1-foundation.md`) AND in PROGRESS.md. Both must be ticked when a task closes.
- **Repo policy:** `docs/superpowers/` is gitignored at the project root, but its contents have been force-tracked locally on this branch. Continue committing tick changes normally — `git add` works without `-f` once a file is tracked. **Before any push to remote**, archive `docs/superpowers/` content to a gitignored path (per user policy in memory `project_superpowers_local_tracking.md`).

### Branch state
- Tip: `a656212` (clean tree).
- 8 commits since `master`:
  ```
  a656212 feat(taskmaster): unify JSON response sending in HTTP handler
  57a0dac feat(taskmaster): PUT /api/viewer/prefs endpoint
  a2160b8 feat(taskmaster): GET /api/viewer/prefs endpoint
  e7b8e3c feat(taskmaster): viewer_prefs_get/set MCP tools
  5dd9e50 feat(taskmaster): viewer prefs load/save with deep-merge defaults
  ac6ce10 style(taskmaster): match ViewerPrefs section header to file convention
  6af3768 feat(taskmaster): add ViewerPrefs defaults + schema version
  14e6ea1 chore(plans): cross-plan reconciliation pre-execution
  ```
- Tests: 201 passing (`python -m pytest plugins/taskmaster/tests/ -q` from worktree root).

### Environment
- Global pip: `mcp` upgraded **1.9.0 → 1.27.0** (resolves `Icon` import in fastmcp 3.1). `dive-mcp-host 0.2.0` emits a soft pip resolver warning since it pins `mcp==1.9.0`; benign, both packages still load. See memory `reference_python_env_quirks.md`.
- Plan 1 Architectural Conventions are in force across all M2+ tasks. Re-read the "Architectural Conventions" section of `2026-04-26-viewer-redesign-plan-1-foundation.md` before each implementer dispatch.

---

## What M2 covers

Plan 1 Milestone 2 — Static skeleton (Tasks 7–12). No Python logic; mostly file creation under `plugins/taskmaster/viewer/`.

| Task | Subject |
|---|---|
| T1.7 | Scaffold `viewer/` dir + `tokens.css` |
| T1.8 | `shell.css` + `_placeholders.css` |
| T1.9 | `components.css` (chips, pills, buttons, kbd) |
| T1.10 | `index.html` shell (sidebar + main mount points) |
| T1.11 | `/v3` route + `/static/v3/*` static serve in `backlog_server.py` |
| T1.12 | Manual smoke `/v3` (orchestrator runs, no impl) |

T1.12 is a human/orchestrator check, not a normal implementer dispatch. Read its block in the plan file before deciding how to handle it (probably: orchestrator boots the server, navigates to `/v3`, confirms it loads, then ticks).

---

## Per-task dispatch loop (use this verbatim)

### Step 1 — Implementer (Sonnet, subagent_type `general-purpose`)

```
You are implementing one task in the Taskmaster Viewer Redesign — Plan 1.

Working directory (use this exact path for ALL ops including git):
C:\Users\gruku\Files\Claude\claude-tools\.worktrees\taskmaster-v3
Branch: feature/taskmaster-v3.

Plan file: docs/superpowers/plans/2026-04-26-viewer-redesign-plan-1-foundation.md
Task: <T1.X — task title>

State coming in: Tasks 1–<N-1> already merged. <One-sentence summary of what now exists from prior tasks.>

What to do:
1. Read the plan's "Architectural Conventions" + Task <X> in full.
2. Execute Task <X> step-by-step verbatim. Follow TDD: failing test → confirm fail → impl → confirm pass → commit. (For pure file-creation tasks like CSS scaffolding, the plan may not prescribe a test — match the plan, don't invent tests.)
3. Tick all step checkboxes under Task <X> in the plan file + tick T1.<X> in docs/superpowers/plans/PROGRESS.md.

Hard rules:
- Use the worktree path for ALL git ops (git -C "C:/Users/gruku/Files/Claude/claude-tools/.worktrees/taskmaster-v3" ...).
- Don't push.
- Don't modify files outside Task <X>'s "Files" block + the two checkbox-tracking files.
- Don't touch unrelated M files in git status.
- If a step's expected output diverges from observed, STOP and report.

Pytest: python -m pytest plugins/taskmaster/tests/ -v from worktree root. Should remain at 201+ passing.

Report back (under 250 words):
- Status: DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED
- Commit SHA(s)
- Last 15 lines of pytest output (or "no new tests prescribed by this task")
- One sanity-check sentence for spec reviewer
- Divergences and why
- Concerns
```

### Step 2 — Spec reviewer (Sonnet, subagent_type `general-purpose`)

Same prompt template as M1 — point at the plan task, the implementation commit, list 6–10 spec items to verify, end with "Verdict: SPEC COMPLIANT or ISSUES" + "skip code quality (separate pass)".

### Step 3 — Code quality reviewer (Sonnet, subagent_type `superpowers:code-reviewer`)

Same template as M1 — diff to review, focus on hygiene + test depth + architectural convention adherence (NOT spec). End with "Verdict: APPROVED or ISSUES" + blocking/non-blocking split.

### Step 4 — Orchestrator decision

- Both reviews ✅ → tick is already in the impl commit (the implementer ticks as part of their commit). Verify with `grep "T1.<X>" docs/superpowers/plans/PROGRESS.md` shows `[x]`. Move to next task.
- Spec reviewer ❌ blocking → re-dispatch implementer with the issues listed verbatim. Bounce limit: 2; on the third try escalate to user.
- Code reviewer ❌ blocking → same bounce-back loop.
- Non-blocking nits → orchestrator's call. Trivial 1-line fixes (style, header convention) can be done directly without a subagent. Anything bigger goes back to implementer or gets logged for a later cleanup task. Don't let non-blocking nits accumulate silently.

---

## Known open nits carried from M1 (NOT scope for M2)

These were flagged but non-blocking. Don't get sidetracked fixing them in M2 — log them and let a later cleanup task handle batching:

1. `_deep_merge` duplicated in `backlog_server.py` (~line 1690 inside `viewer_prefs_set` MCP tool, ~line 3978 inside `do_PUT`). Should consolidate before Plans 2–6 add a third callsite. Tracked here, not in PROGRESS.md.
2. Inline `import json` left in `do_PUT` after Task 6's refactor — module already imports at top.
3. `_send_json` lacks a docstring; `Cache-Control` drop in `_send_json` has no inline comment.
4. `load_viewer_prefs` doesn't guard malformed `viewer.json` (corrupt JSON / non-dict). Plan didn't ask for it; not regressed; flag remains.
5. `do_OPTIONS` is path-unscoped (responds 204 to `OPTIONS /anything`). Local-only dev server, low risk.

If these grow to >5 items by end of M2, propose a "Plan 1 hygiene sweep" mini-task to the user.

---

## Environment / repo gotchas the next session WILL hit

- **`docs/superpowers/` is gitignored.** Force-add was used historically. Now that PROGRESS.md and the plan files are tracked, normal `git add` works on them. New files in this directory still need `git add -f` to land.
- **The worktree is the only place this work happens.** `C:\Users\gruku\Files\Claude\claude-tools` (master) only has the reconciliation commit and not the v3 codebase. All implementer subagents must use the worktree path.
- **Implementer subagents have repeatedly mis-claimed that `docs/superpowers/` ticks "can't be committed".** This is wrong; the files are tracked. Don't let the implementer skip a tick commit on this premise — verify with `grep "T1\." PROGRESS.md` after each task.
- **MCP env upgraded mid-session.** If pytest is rerun on a clean shell, the upgrade persists (it's user-site, not venv). If you see a fresh `mcp.types.Icon` ImportError, run `pip install --upgrade mcp` again.

---

## Files of interest

| Purpose | Path (relative to worktree root) |
|---|---|
| Plan being executed | `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-1-foundation.md` |
| Progress index | `docs/superpowers/plans/PROGRESS.md` |
| Original execution handoff (full 271-task picture) | `docs/superpowers/plans/2026-04-27-viewer-redesign-execution-handoff.md` |
| This handoff | `docs/superpowers/plans/2026-04-27-viewer-redesign-m1-complete-resume-m2.md` |
| Server module under change | `plugins/taskmaster/backlog_server.py` |
| Core helpers module | `plugins/taskmaster/taskmaster_v3.py` |
| Tests | `plugins/taskmaster/tests/test_v3_layout.py`, `plugins/taskmaster/tests/test_server_api.py` |
| Future viewer dir (created in M2 T1.7) | `plugins/taskmaster/viewer/` |
| Memory pointers | `MEMORY.md` → `project_superpowers_local_tracking.md`, `reference_python_env_quirks.md` |

---

## Opening checklist for the next session

1. Read this file end-to-end.
2. `cd "C:\Users\gruku\Files\Claude\claude-tools\.worktrees\taskmaster-v3"` (or `git -C ...` everywhere — pick one and stick to it).
3. `git status` — must be clean. Tip should be `a656212`.
4. `python -m pytest plugins/taskmaster/tests/ -q` — must show 201 passing. If `mcp.types.Icon` ImportError reappears, `pip install --upgrade mcp`.
5. `head -20 docs/superpowers/plans/PROGRESS.md` — confirm T1.6 ticked, T1.7 unticked.
6. Dispatch the T1.7 implementer using the template above.
7. Run the loop through T1.12. Stop after T1.12 completes for the next human checkpoint.

---

**End of M1 → M2 handoff.**
