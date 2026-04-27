# Viewer Redesign — Resume Handoff (M3 done, M4 next — closes Plan 1)

**Date opened:** 2026-04-27 (post-M3)
**Status:** Plan 1 Milestone 3 complete (JS layer + screen stubs). Ready to start Milestone 4 — the **final milestone of Plan 1**.
**Branch:** `feature/taskmaster-v3` at `C:\Users\gruku\Files\Claude\claude-tools\.worktrees\taskmaster-v3` (NOT the master checkout)
**Tip commit:** `9c876b8` (T1.21 tick — orchestrator curl smoke for /v3 + JS modules)
**Tests:** 205 passing (`python -m pytest plugins/taskmaster/tests/ -q` from worktree root)

---

## Resume prompt (paste into next session)

> "Resuming the Taskmaster viewer redesign. M1 + M2 + M3 complete; start M4 (Plan 1 Tasks 22–28) — the **last milestone of Plan 1**. Read `docs/superpowers/plans/2026-04-27-viewer-redesign-m3-complete-resume-m4.md` for current state, dispatch templates, hygiene-sweep proposal, and known open nits. Then read `PROGRESS.md` to confirm the next unchecked task is T1.22. All work happens on branch `feature/taskmaster-v3` in the worktree `.worktrees/taskmaster-v3` — NOT on master. Use `superpowers:subagent-driven-development`: per-task loop is implementer subagent → spec reviewer subagent → code quality reviewer subagent → tick PROGRESS.md + plan-file checkboxes → next task. After T1.28, run the **Plan 1 hygiene sweep** as a single batched task before moving to Plan 2. Pause for human checkpoint at the end of M4."

---

## What M3 delivered

Plan 1 Milestone 3 — JS layer + 8 screen stubs (Tasks 13–21).

| Task | Subject | Impl SHA | Tick SHA | Spec | Code |
|---|---|---|---|---|---|
| T1.13 | js/api.js | `48f60a0` | `ad676c9` | ✅ | ✅ (1 sweep) |
| T1.14 | js/store.js | `1731eb9` | `0096384` | ✅ | ✅ |
| T1.15 | js/router.js | `20ead41` | `1c61fd7` | ✅ | ✅ (3 sweep) |
| T1.16 | js/components/sidebar.js | `66db8c0` | `3392e30` | ✅ | ✅ (2 sweep) |
| T1.17 | js/main.js | `35da5e5` | `d47112a` | ✅ | ✅ (4 sweep) |
| T1.18 | screens/dashboard.js stub | `7f84e67` | `463fb85` | ✅ | ✅ |
| T1.19 | kanban + task-detail + sessions stubs | `d5182b8` | `9f8cbf4` | ✅ | ✅ (1 sweep) |
| T1.20 | lessons + issues + auto-mode + recap stubs | `94ed912` | `b1ea50c` | ✅ | ✅ |
| T1.21 | manual smoke (orchestrator curl) | — | `9c876b8` | curl ✅ | — |

T1.21 smoke covered: `/v3` 200 with rewritten asset paths, all 13 JS modules 200 with `application/javascript`, `/backlog.yaml` 200 with `text/yaml`, `/api/identity` and `/api/viewer/prefs` 200. Browser eyeball check for hash routing / screen-mount swap / `.active` class is the M3 human checkpoint — same pattern as M2.

No bounce-backs in M3.

---

## What M4 covers (closes Plan 1)

Plan 1 Milestone 4 — `viewer.use_v3` flag, Playwright, dev docs, plan handoff (Tasks 22–28).

| Task | Subject | Shape |
|---|---|---|
| T1.22 | `viewer.use_v3` flag — root serves v3 when enabled | TDD (real Python test) |
| T1.23 | Set up Playwright (package.json + config) | npm install dance |
| T1.24 | Write `smoke.spec.js` (11 routes + fallback) | JS test file |
| T1.25 | Prefs round-trip end-to-end test | Append to smoke.spec.js |
| T1.26 | Write `viewer/README.md` | Pure docs |
| T1.27 | Full test suite + no push | Orchestrator runs both suites |
| T1.28 | Plan-1 spec coverage walk + plan handoff | Orchestrator audit |

**Important shape changes vs. M2/M3:**
- **T1.22 is real TDD**, not pure file creation. The implementer must (1) write the failing test, (2) confirm it fails, (3) implement, (4) confirm it passes, then commit. Don't let the implementer skip the failing-test confirmation.
- **T1.23 may not be runnable** if npm/node isn't installed. The plan has an escape hatch ("If `npm` is unavailable, document the manual install in a `README.md` and skip"). Orchestrator should probe `node --version && npm --version` first and decide whether T1.23/T1.24/T1.25 run or get marked with a `[~]` partial (config + test files committed; install + run deferred). Don't silently fail.
- **T1.27 is orchestrator-run** like T1.12/T1.21. Just runs both suites, fixes any straggler issues, ticks.
- **T1.28 is a written audit** — orchestrator walks the spec checklist (§3.10, §3.11, §5) and confirms architectural conventions hand-off contract for Plans 2–6.

### Pre-M4 environment check (run at session start)

```bash
git -C "C:/Users/gruku/Files/Claude/claude-tools/.worktrees/taskmaster-v3" status   # must be clean, tip 9c876b8
python -m pytest plugins/taskmaster/tests/ -q                                       # 205 passing
node --version 2>/dev/null && npm --version 2>/dev/null || echo "NO_NODE"           # decides T1.23 path
```

If `NO_NODE`, plan: T1.22 ✅, T1.23 partial (commit config files + add a "manual install" note in T1.26 README, mark `[~]` and tick `T1.23 (config only)`), T1.24/T1.25 partial (commit specs but skip running), T1.26–T1.28 normal.

---

## Per-task dispatch loop (use this verbatim)

Same protocol as M3. Implementer template below — adapt the task ID and "state coming in" line per task.

### Step 1 — Implementer (Sonnet, subagent_type `general-purpose`)

```
You are implementing one task in the Taskmaster Viewer Redesign — Plan 1.

Working directory (use this exact path for ALL ops including git):
C:\Users\gruku\Files\Claude\claude-tools\.worktrees\taskmaster-v3
Branch: feature/taskmaster-v3.

Plan file: docs/superpowers/plans/2026-04-26-viewer-redesign-plan-1-foundation.md
Task: <T1.X — task title>

State coming in: Tasks 1–<N-1> already merged. <One-sentence summary.>

What to do:
1. Read the plan's "Architectural Conventions" + Task <X> in full.
2. Execute Task <X> step-by-step verbatim. **For T1.22, follow strict TDD: failing test → confirm fail → impl → confirm pass → commit.** For pure file-creation tasks (T1.23, T1.26), match the plan exactly without inventing tests.
3. Tick step checkboxes under Task <X> in the plan file + tick T1.<X> in docs/superpowers/plans/PROGRESS.md.

Hard rules:
- Use the worktree path for ALL git ops: `git -C "C:/Users/gruku/Files/Claude/claude-tools/.worktrees/taskmaster-v3" ...`
- Don't push.
- Don't modify files outside Task <X>'s "Files" block + the two checkbox-tracking files.
- `docs/superpowers/` is gitignored — `git add -f` is REQUIRED for both plan-file and PROGRESS.md ticks.
- STOP and report on any divergence.
- Don't regress test count (currently 205 passing).

Pytest: `python -m pytest plugins/taskmaster/tests/ -q` from worktree root.

Report under 250 words: Status (DONE/DONE_WITH_CONCERNS/NEEDS_CONTEXT/BLOCKED), commit SHA(s), last 15 lines pytest, one sanity-check sentence, divergences, concerns.
```

### Step 2 — Spec reviewer (Sonnet, subagent_type `general-purpose`)

Same template structure as M3.

### Step 3 — Code quality reviewer (Sonnet, subagent_type `superpowers:code-reviewer`)

Same template structure as M3. Tell the reviewer NOT to re-flag the catalogued ~32 hygiene-sweep items — only NEW issues.

### Step 4 — Orchestrator decision

- Both reviews ✅ → tick is in the impl commit chain. Verify with `grep "T1.<X>" PROGRESS.md` shows `[x]`.
- Spec ❌ blocking → re-dispatch. Bounce limit: 2.
- Code ❌ blocking on a NEW issue → bounce. T1.11 is the precedent: surgical follow-up commit, then proceed.
- Plan-prescribed nits → log under hygiene sweep (do NOT bounce).

---

## Plan 1 Hygiene Sweep — RUN IT AFTER T1.28

The catalogue grew M2 → M3: **~32 items now** across `backlog_server.py`, `tokens.css`, `shell.css`, `_placeholders.css`, `components.css`, `index.html`, `api.js`, `router.js`, `sidebar.js`, `main.js`, and `sessions.js` stub. Full inventory is in the M2→M3 handoff (`2026-04-27-viewer-redesign-m2-complete-resume-m3.md`, "Proposed Plan 1 Hygiene Sweep mini-task" section, items 1–22) plus M3 additions:

**M3 additions (catalogued via TaskCreate during execution):**
- **api.js** — `resp.json()` SyntaxError loses method/path/status context; wrap with the same error-message pattern as the non-2xx branch.
- **router.js** — async `go()` race on rapid hashchange (add monotonic `navSeq` guard); dynamic-import failure leaves blank `mountEl` silently (try/catch + error state); topbar `querySelector('#page-title')` hardcodes DOM id (pass `titleEl` via `init({})`); `navigate()` no-init guard.
- **sidebar.js** — `mountSidebar` returns no teardown (leaks `route:changed` document listener + 2 store subs on remount); active link missing `aria-current="page"` on route change.
- **main.js** — visibility-aware poll pause; exponential backoff on poll errors; dedupe `loadJsYaml` with module-level promise guard; surface boot errors instead of blank sidebar.
- **sessions.js stub** — interpolates `subpath[0]` into `innerHTML` without `escapeHtml` (task-detail.js escapes the same pattern, so this is a copy-paste inconsistency that propagates if not fixed before Plan 5); also extract `escapeHtml` to a shared util once 2+ screens need it.

### Suggested mini-task spec (open after T1.28)

Open a single new plan-1 task: **T1.29 — Plan 1 hygiene sweep** (or run as a non-numbered cleanup commit between Plan 1 and Plan 2 — the user's call). One commit per logical group:
1. `backlog_server.py` — consolidate `_deep_merge`, drop inline `import json`, document `_send_json` Cache-Control omission, scope `do_OPTIONS`, extend MIME map for `.woff2` etc., add `Content-Length` to error responses.
2. `tokens.css` — dedupe `--amber`/`--gold`, replace `--diff-*` raw values with `var()`, add `--sp-10`/`--sp-12`, move `--shell-zoom` out of tokens.
3. `shell.css` + `_placeholders.css` — promote hardcoded `#101116`, `9px`, hover overlays, raw paddings to tokens; remove §3.7/§3.11 author noise.
4. `components.css` — switch chip/pill rgba to `color-mix` or `*-soft` tokens; rename `.cmp-pill .dot` → `.cmp-pill__dot`; comment intentional sub-token paddings.
5. `index.html` — promote first heading to `<h1>` (or add visually-hidden `<h1>`).
6. `api.js` + `router.js` + `sidebar.js` + `main.js` + `sessions.js` — JS hygiene per M3 list above.

**Skip behavioral items in the sweep:** `load_viewer_prefs` malformed-json guard is a real ticket with its own test; do it standalone, not in the sweep.

---

## Known repo gotchas (carry-forward)

- **`docs/superpowers/` is gitignored.** `git add -f` is required for plan-file and PROGRESS.md ticks even though they're already tracked.
- **The worktree is the only place this work happens.** All implementer subagents must use the worktree path.
- **MCP env upgraded mid-M1.** If `mcp.types.Icon` ImportError reappears, run `pip install --upgrade mcp`.
- **Server boot prints are buffered** without `python -u`. T1.27 doesn't need to boot the server interactively, but if needed: use `python -u` + explicit `sys.stdout.flush()` after the port print.
- **Browser eyeball checks** for any future manual smoke (Plan 1 is essentially done after M4) need a real browser. Curl can verify routes and asset wiring; Playwright (T1.24) covers click + active-class + screen-mount automatically once it's installed.
- **Node/npm availability is not guaranteed** in this environment. T1.23 has an escape hatch — use it; don't fail the milestone over Playwright not being installable.

---

## Files of interest

| Purpose | Path (relative to worktree root) |
|---|---|
| Plan being executed | `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-1-foundation.md` |
| Progress index | `docs/superpowers/plans/PROGRESS.md` |
| Original execution handoff (full 271-task picture) | `docs/superpowers/plans/2026-04-27-viewer-redesign-execution-handoff.md` |
| M1 → M2 handoff (superseded) | `docs/superpowers/plans/2026-04-27-viewer-redesign-m1-complete-resume-m2.md` |
| M2 → M3 handoff (with hygiene-sweep inventory items 1–22) | `docs/superpowers/plans/2026-04-27-viewer-redesign-m2-complete-resume-m3.md` |
| **This handoff** | `docs/superpowers/plans/2026-04-27-viewer-redesign-m3-complete-resume-m4.md` |
| Server module | `plugins/taskmaster/backlog_server.py` |
| Core helpers | `plugins/taskmaster/taskmaster_v3.py` (T1.22 modifies this — adds `use_v3` to defaults) |
| Static viewer | `plugins/taskmaster/viewer/` (index.html + css/ + js/ + screens/) |
| Future Playwright dir (created in T1.23) | `plugins/taskmaster/viewer/tests/` |
| Server tests | `plugins/taskmaster/tests/test_v3_layout.py`, `tests/test_server_api.py` |
| Memory pointers | `MEMORY.md` → `project_superpowers_local_tracking.md`, `reference_python_env_quirks.md` |

---

## Big picture — what's left after M4

Closing M4 finishes Plan 1 (28/28). Remaining: **6 plans, 243 tasks**, plus 4 post-execution items:

| Plan | Tasks | Subject |
|---|---|---|
| Plan 2 | 33 | Kanban + Cards |
| Plan 3 | 46 | Task Detail (largest single screen) |
| Plan 4 | 36 | Dashboard |
| Plan 5a | 38 | Sessions + Recap |
| Plan 5b | 32 | Lessons + Issues |
| Plan 6 | 58 | Auto Mode (largest plan) |
| Post | 4 | Soak window, flag flip, legacy retirement |

After T1.28 + hygiene sweep, the natural break point is **Plan 2 (Kanban)**. Plans 2–6 share the architectural conventions defined at the top of Plan 1 — those should be re-read before each new plan begins.

---

## Opening checklist for the next session

1. Read this file end-to-end.
2. `git -C "C:/Users/gruku/Files/Claude/claude-tools/.worktrees/taskmaster-v3" status` — must be clean. Tip should be `9c876b8`.
3. `python -m pytest plugins/taskmaster/tests/ -q` from worktree root — must show 205 passing.
4. `node --version 2>/dev/null && npm --version 2>/dev/null || echo "NO_NODE"` — decides T1.23/T1.24/T1.25 path.
5. `head -40 docs/superpowers/plans/PROGRESS.md` — confirm T1.21 ticked, T1.22 unticked.
6. Skim `Architectural Conventions` of the plan file again — TDD discipline matters for T1.22.
7. Dispatch the T1.22 implementer using the template above.
8. Run the loop through T1.28. After T1.28 is ticked, **open and execute the Plan 1 hygiene sweep** before any human checkpoint or Plan 2 start.

---

**End of M3 → M4 handoff. M4 closes Plan 1.**
