# Viewer Redesign — Resume Handoff (M2 done, M3 next)

> **SUPERSEDED 2026-04-27 (post-M3).** M3 is complete. The next session should read `2026-04-27-viewer-redesign-m3-complete-resume-m4.md` instead. This file is kept as a checkpoint reference — it carries hygiene-sweep inventory items 1–22 which the M3→M4 handoff appends to (not duplicates).

**Date opened:** 2026-04-27 (post-M2)
**Status:** Plan 1 Milestone 2 complete (static skeleton). Ready to start Milestone 3.
**Branch:** `feature/taskmaster-v3` at `C:\Users\gruku\Files\Claude\claude-tools\.worktrees\taskmaster-v3` (NOT the master checkout)
**Tip commit:** `957f1c2` (T1.12 tick — orchestrator smoke for `/v3` + `/static/v3/*`)
**Tests:** 205 passing (`python -m pytest plugins/taskmaster/tests/ -q` from worktree root)

---

## Resume prompt (paste into next session)

> "Resuming the Taskmaster viewer redesign. M1 + M2 complete; start M3 (Plan 1 Tasks 13–21). Read `docs/superpowers/plans/2026-04-27-viewer-redesign-m2-complete-resume-m3.md` for current state, dispatch templates, and known open nits. Then read `PROGRESS.md` to confirm the next unchecked task is T1.13. All work happens on branch `feature/taskmaster-v3` in the worktree `.worktrees/taskmaster-v3` — NOT on master. Use `superpowers:subagent-driven-development`: per-task loop is implementer subagent → spec reviewer subagent → code quality reviewer subagent → tick PROGRESS.md + plan-file checkboxes → next task. Pause for human checkpoint at the end of M3 (after T1.21)."

---

## What M2 delivered

Plan 1 Milestone 2 — Static skeleton (Tasks 7–12).

| Task | Subject | Impl SHA | Spec | Code |
|---|---|---|---|---|
| T1.7 | viewer/ tree + tokens.css | `5ad5f22` | ✅ | ✅ (4 plan-level nits) |
| T1.8 | shell.css + _placeholders.css | `1b4dd43` | ✅ | ✅ (5 plan-level nits) |
| T1.9 | components.css | `121a746` | ✅ | ✅ (4 plan-level nits) |
| T1.10 | index.html shell | `a0f2def` | ✅ | ✅ (1 plan-level nit) |
| T1.11 | `/v3` + `/static/v3/*` routes | `3ba92fc` + `1bd41fc` (fix) | ✅ | ✅ after fix |
| T1.12 | manual smoke (orchestrator-run via curl) | `957f1c2` (tick) | — | — |

### T1.11 bounce-back

Code reviewer flagged 2 BLOCKING issues; bounced once and resolved in `1bd41fc`:

1. **URL-encoded traversal bypass** — added `urllib.parse.unquote(rel)` before applying the resolve-and-startswith guard. `%2e%2e` now correctly returns `400`.
2. **`Cache-Control` header missing** — added `no-cache, no-store, must-revalidate` to both `/v3` and `/static/v3/*` (matches `_serve_file` pattern; `_send_json` JSON path intentionally remains uncached).
3. **Tightened test** — `test_static_v3_path_traversal_blocked` now asserts `== 400` (not `in (400, 404)`); new `test_static_v3_path_traversal_url_encoded_blocked` covers the encoded form.

Smoke (curl, port 0 ephemeral): `/v3` 200 with rewritten asset paths and Cache-Control; all 4 CSS files 200 with `text/css`; raw `..` → 404 (HTTP layer normalizes); encoded `%2e%2e` → 400; `/static/v3/js/main.js` → 404 (expected — file lands in M3 T1.17).

---

## What M3 covers

Plan 1 Milestone 3 — Routing + Sidebar (Tasks 13–21). This is the JS layer.

| Task | Subject |
|---|---|
| T1.13 | `js/api.js` — thin HTTP client |
| T1.14 | `js/store.js` — in-memory state + subscriptions |
| T1.15 | `js/router.js` — hash-based screen routing |
| T1.16 | `js/components/sidebar.js` — sidebar render |
| T1.17 | `js/main.js` — entry, boot, polling |
| T1.18 | `screens/dashboard.js` stub |
| T1.19 | `screens/kanban.js`, `task-detail.js`, `sessions.js` stubs |
| T1.20 | `screens/lessons.js`, `issues.js`, `auto-mode.js`, `recap.js` stubs |
| T1.21 | Manual smoke — every nav item resolves (orchestrator/human run) |

T1.21 is the M3 endpoint and a human/orchestrator check (parallel to T1.12). Plan it the same way.

---

## Per-task dispatch loop (use this verbatim)

Same protocol as M2. The implementer prompt below is the canonical template — adapt the task ID and "state coming in" line per task.

### Step 1 — Implementer (Sonnet, subagent_type `general-purpose`)

```
You are implementing one task in the Taskmaster Viewer Redesign — Plan 1.

Working directory (use this exact path for ALL ops including git):
C:\Users\gruku\Files\Claude\claude-tools\.worktrees\taskmaster-v3
Branch: feature/taskmaster-v3.

Plan file: docs/superpowers/plans/2026-04-26-viewer-redesign-plan-1-foundation.md
Task: <T1.X — task title>

State coming in: Tasks 1–<N-1> already merged. <One-sentence summary of what now exists.>

What to do:
1. Read the plan's "Architectural Conventions" + Task <X> in full.
2. Execute Task <X> step-by-step verbatim. Follow TDD if the plan prescribes tests; otherwise (pure file creation) match the plan exactly without inventing tests.
3. Tick step checkboxes under Task <X> in the plan file + tick T1.<X> in docs/superpowers/plans/PROGRESS.md.

Hard rules:
- Use the worktree path for ALL git ops.
- Don't push.
- Don't modify files outside Task <X>'s "Files" block + the two checkbox-tracking files.
- `docs/superpowers/` is gitignored — `git add -f` is REQUIRED for both plan-file and PROGRESS.md ticks even though they're already tracked. Don't skip the tick commit on the false claim that they "can't be committed"; just use -f.
- STOP and report on any divergence from expected outputs.
- Don't regress the existing test count.

Pytest: python -m pytest plugins/taskmaster/tests/ -q from worktree root.

Report under 250 words: Status (DONE/DONE_WITH_CONCERNS/NEEDS_CONTEXT/BLOCKED), commit SHA(s), last 15 lines pytest (or "no new tests prescribed"), one sanity-check sentence, divergences, concerns.
```

### Step 2 — Spec reviewer (Sonnet, subagent_type `general-purpose`)

Same template structure as M2. Point at the plan task + impl commit, list 5–8 spec items to verify, end with "Verdict: SPEC COMPLIANT or ISSUES" + "skip code quality (separate pass)".

### Step 3 — Code quality reviewer (Sonnet, subagent_type `superpowers:code-reviewer`)

Same template structure as M2. **Important:** for M3, tell the reviewer NOT to re-flag known plan-prescribed nits (they've been catalogued — see hygiene-sweep section below). Only flag NEW issues introduced in the current diff.

### Step 4 — Orchestrator decision

- Both reviews ✅ → tick is in the impl commit chain. Verify with `grep "T1.<X>" PROGRESS.md` shows `[x]`.
- Spec reviewer ❌ blocking → re-dispatch implementer with issues verbatim. Bounce limit: 2.
- Code reviewer ❌ blocking on a NEW (non-plan-prescribed) issue → bounce. T1.11 is the precedent: surgical follow-up commit, then proceed.
- Plan-prescribed nits → log under hygiene sweep (do NOT bounce); don't let reviewer try to fix the plan via the implementer.

---

## Proposed Plan 1 Hygiene Sweep mini-task

Per the M2 handoff trigger (>5 carried-forward nits → propose a sweep), the inventory is now ~22 items. Recommend running this as a single batched task at the end of Plan 1 (after T1.28) — NOT mid-milestone. Doing it mid-flight forks the plan from the spec, which the spec reviewer will (correctly) flag.

### Inventory

**Server (M1):**
1. `_deep_merge` duplicated in `backlog_server.py` (`viewer_prefs_set` MCP tool ~L1690, `do_PUT` ~L3978) — consolidate before Plan 2/6 add a third call site.
2. Inline `import json` left in `do_PUT` (module already imports at top).
3. `_send_json` lacks docstring; `Cache-Control` deliberately dropped on JSON path with no inline comment explaining why.
4. `load_viewer_prefs` doesn't guard malformed `viewer.json` (corrupt JSON / non-dict).
5. `do_OPTIONS` is path-unscoped (responds 204 to `OPTIONS /anything`). Local-only dev server, low risk.

**tokens.css (T1.7):**
6. `--amber` and `--gold` identical (`#d6a45f`) — dedupe or document as semantic alias.
7. `--diff-add/mod/del` re-hardcode `--green/--amber/--red` values — change to `var()` references.
8. Spacing scale ends at `--sp-9: 22px` — add `--sp-10: 24px`, `--sp-12: 32px` before screen layouts need them.
9. `--shell-zoom: 1.5` is behavioral, not a design token — move to `shell.css` or set programmatically.

**shell.css + _placeholders.css (T1.8):**
10. `.sidebar` background hardcoded `#101116` — promote to `--bg-sidebar` (or `--shell-bg-sidebar`).
11. `.sidebar-section-h` `font-size: 9px` hardcoded — declare `--shell-label-size: 9px` or use a token.
12. `.sidebar-link:hover` raw `rgba(255,255,255,0.03)` — promote to `--shell-hover-overlay`.
13. `.sidebar-link.active` inline comment referencing spec sections (§3.7 / §3.11) — author noise, remove.
14. `_placeholders.css` uses raw `padding: 40px` — depends on missing `--sp-10`.

**components.css (T1.9):**
15. Chip severity variants (`.high/.med/.low/.crit`) use raw rgba — switch to `color-mix(in srgb, var(--red) 15%, transparent)` or add `--red-soft`/`--amber-soft`.
16. `.cmp-btn.primary` `border-color` hardcoded as rgba of `--accent` — add `--accent-mid` or use `color-mix`.
17. `.cmp-pill .dot` — unprefixed descendant selector. Rename to `.cmp-pill__dot` or `.cmp-pill-dot` to avoid Plan 2–6 collisions.
18. Sub-token paddings (`2px`/`3px`) on chips/pills are intentional but uncommented — add a one-line note so the next reviewer doesn't "fix" them.

**index.html (T1.10):**
19. First heading is `<h2 id="page-title">` — accessible heading hierarchy should start at `<h1>`. Promote or add a visually-hidden `<h1>`.

**Server (T1.11 follow-up code-review non-blockers, kept):**
20. `/v3` hand-rolls `send_response`/`send_header`/`wfile.write` instead of using `_serve_file` — extend `_serve_file` to accept pre-processed bytes, or add a comment explaining the divergence.
21. MIME map missing `.woff2`, `.woff`, `.png`, `.ico` — extend before any binary asset lands.
22. 400/404 inline error responses lack `Content-Length` — add for consistency.

### Suggested mini-task spec

Call it **Plan 1 hygiene sweep**, single task. Group fixes by file, one commit per logical group (tokens.css consolidation, shell.css token-promotion, components.css naming, server hygiene). Skip items that touch behavior (e.g., #4 malformed-json guard) — those should be standalone tickets with their own tests.

Park this proposal until end of Plan 1. Don't open it now.

---

## Known repo gotchas (carry-forward)

- **`docs/superpowers/` is gitignored.** `git add -f` is required for both plan-file and PROGRESS.md ticks. **The previous handoff's claim that plain `git add` works was wrong** — every M2 implementer correctly used `-f`. (Long-term fix per `project_superpowers_local_tracking.md`: archive-and-re-ignore before push, or move tracked plan files out of `docs/superpowers/` to a non-ignored location.)
- **The worktree is the only place this work happens.** `C:\Users\gruku\Files\Claude\claude-tools` (master) only has the reconciliation commit and not the v3 codebase. All implementer subagents must use the worktree path.
- **MCP env upgraded mid-M1.** If pytest is rerun on a clean shell, the `mcp 1.27.0` upgrade persists (it's user-site, not venv). If `mcp.types.Icon` ImportError reappears, run `pip install --upgrade mcp` again.
- **Server boot prints are buffered.** When orchestrator-running the server for smoke (T1.12 / T1.21 / future): use `python -u` and explicit `sys.stdout.flush()` after `print(f'PORT={p}')` — without `-u`, the port print can hang behind import warnings for many seconds.
- **Browser eyeball checks** for T1.21 will need real browser open — curl can verify routes and asset wiring, but "every nav item resolves" implies clicking each sidebar link and observing the screen-mount swap. Plan whether to do that via `claude-in-chrome` MCP tools, defer to user, or write a Playwright test (T1.23 sets up Playwright anyway).

---

## Files of interest

| Purpose | Path (relative to worktree root) |
|---|---|
| Plan being executed | `docs/superpowers/plans/2026-04-26-viewer-redesign-plan-1-foundation.md` |
| Progress index | `docs/superpowers/plans/PROGRESS.md` |
| Original execution handoff (full 271-task picture) | `docs/superpowers/plans/2026-04-27-viewer-redesign-execution-handoff.md` |
| M1 → M2 handoff (superseded) | `docs/superpowers/plans/2026-04-27-viewer-redesign-m1-complete-resume-m2.md` |
| **This handoff** | `docs/superpowers/plans/2026-04-27-viewer-redesign-m2-complete-resume-m3.md` |
| Server module under change | `plugins/taskmaster/backlog_server.py` |
| Static viewer | `plugins/taskmaster/viewer/` (index.html + css/) |
| Future JS layer (built in M3) | `plugins/taskmaster/viewer/js/` |
| Tests | `plugins/taskmaster/tests/test_v3_layout.py`, `tests/test_server_api.py` |
| Memory pointers | `MEMORY.md` → `project_superpowers_local_tracking.md`, `reference_python_env_quirks.md` |

---

## Opening checklist for the next session

1. Read this file end-to-end.
2. `git -C "C:/Users/gruku/Files/Claude/claude-tools/.worktrees/taskmaster-v3" status` — must be clean. Tip should be `957f1c2`.
3. `python -m pytest plugins/taskmaster/tests/ -q` from worktree root — must show 205 passing. If `mcp.types.Icon` ImportError reappears, `pip install --upgrade mcp`.
4. `head -30 docs/superpowers/plans/PROGRESS.md` — confirm T1.12 ticked, T1.13 unticked.
5. Skim `Architectural Conventions` of the plan file — JS conventions matter for M3 (ES modules, no bundler, `data-*` attributes for state, etc.).
6. Dispatch the T1.13 implementer using the template above.
7. Run the loop through T1.21. Stop after T1.21 completes for the next human checkpoint.

---

**End of M2 → M3 handoff.**
