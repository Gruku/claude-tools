# Handoff — 2026-05-01 — V3 polish pass #1 + Table & Task sidebar entries

**Branch:** `feature/taskmaster-v3` (worktree `.worktrees/taskmaster-v3`)
**Tip:** `03d0406`
**Ahead of master:** 18 commits, no push, no PR.
**Working tree:** clean except for pre-existing untracked (`start_server.py`, `test-results/`, `package-lock.json`, `plugins/taskmaster/.taskmaster/`) and the local `.taskmaster/` produced by serving from the fixture cwd.

## What this session was for

Side-by-side audit of every shipped v3 screen against the brainstorm concepts (`.superpowers/brainstorm/16245-1777231623/content/`), patch the obvious drift, fix the broken pieces we found along the way, and add two new sidebar entries the user asked for.

Methodology: Chrome MCP probes against `http://127.0.0.1:8765/v3/` (live) and `http://127.0.0.1:8766/16245-1777231623/content/` (concepts), pinned at viewport 1440×900.

## What landed (5 commits)

| Commit | What |
|--------|------|
| `a8be266` | Fixture expansion: 5 issues (P0–P3 mix), 5 lessons (active+passive), 3 recaps, 2 handovers, 5 rich tasks (anchors / codex_note / lock / patchnote / activity). v3-031 session set to running. Phase status updated so the kanban surfaces tasks. |
| `844837c` | **System-wide drift + backlog polling fix.** Tokens text-base 18→16, text-2xl 30→24 (etc). `.main` reads `--page-pad` instead of literal `27px 33px`. Backlog polling switched from `/backlog.yaml` + jsyaml-from-CDN to `/api/backlog` (JSON). Visibility check moved AFTER first poll so backgrounded tabs still hydrate. Sidebar `idle` footer hidden when no auto session. `backlogYaml` accessor dropped. |
| `0448fda` | Polish audit doc (`docs/superpowers/plans/2026-05-01-v3-polish-audit.md`) — full inventory of system-wide drift, per-screen findings, bugs, feature gaps, suggested fix order. **Some findings since proven wrong** (see below). |
| `4e64ff9` | **Table view + dashboard tighten.** New `#/table` screen — sortable columns (id/title/status/priority/phase/epic/size/branch/started), search, chip-rail filters (status/priority/epic), prefs-persisted, row-click → task detail. Sidebar entry under Frontdoor as `▭ Table`. Dashboard widget head padding `10px 12px 6px` → uniform `10px 12px`. Fixture: `verdict` added to `spec_review` on v3-050/v3-053 so the codex-note actually renders. |
| `03d0406` | **Task sidebar entry.** `◧ Task` under Frontdoor. Hash `#/task` (no id) redirects to `prefs.ui.last_task_id`; if nothing has been viewed, shows an empty state with links back to Kanban / Table. task-detail persists last-viewed id on each mount. |

## Status of the audit's §5 fix list

| # | Item | Status |
|---|------|--------|
| 1 | `--page-pad` consumer fix | ✅ |
| 2 | `--text-base` 18→16px | ✅ |
| 3 | Screen title H1 30→24px (via `--text-2xl`) | ✅ |
| 4 | Adopt concept's surface stepping (`--bg-shell` ladder) | ⏸ **deferred** — biggest risk vs reward, would touch every component |
| 5 | Remove rogue `idle` text | ✅ (sidebar footer hidden when idle) |
| 6 | Kanban data binding | ✅ (root cause was jsyaml CDN failure + visibility blocking first poll) |
| 7 | Compress lessons screen | ✅ (1557→754px, free with system-wide font/pad fix) |
| 8 | Issues severity glyph + aging bar | ✅ — **already implemented**; my probe used wrong selectors. `.sev-glyph`, `.aging-bar`, monospace location all present |
| 9 | Task detail Variant A 2-column | ✅ — already 2-col `1225px 280px`; only the codex-note fixture needed `verdict` |
| 10 | Dashboard widget head asymmetric padding | ✅ |
| 11 | Build Table view | ✅ |
| 12 | Decide what "dedicated Task view" means | ✅ — built as sidebar entry that resumes last-viewed task |

## Important corrections to the audit doc

The audit doc (`2026-05-01-v3-polish-audit.md`) was written before some root causes were known. Three findings turned out to be wrong:

1. **Issues "missing severity glyph / aging bar"** — they're there. The probe used `[class*="severity-glyph"]` (full word); actual class is `.sev-glyph`. Audit §2.8 should be marked "implemented, verify visual treatment matches concept".
2. **Task detail "single column"** — it IS 2-col (`grid 1225.73px 280px`). Audit §2.4 should be marked "implemented, verify codex-note placement now that fixture has `verdict`".
3. **Auto Mode "spine pulse stutter"** — the design pass already fixed this with `transform: scale`; the original brainstorm `r` attribute was the comparison reference. Verify smoothness in browser, but the code is already correct.

When picking up the polish list, treat the audit as a snapshot from before the system-wide fixes. Re-probe before assuming a finding still holds.

## What's still off — concrete next-session targets

The system-wide font/padding fix tightened things up significantly, but there's more drift to chase. Likely-next items, ordered by how much they'd improve perceived polish:

1. **Surface-stepping palette** (audit §1.4). The concept palette has a deliberate ladder: `--bg-canvas` < `--bg-shell` (sidebar) < `--bg-panel` < `--bg-card` < `--bg-board-col`. Live appears to use a flatter `--surface` / `--surface2` derivation. Adopting the ladder gives the brainstorm pages their depth without shadows. Touches every component bg, so do it as a focused pass.
2. **Sidebar width 300 → 260px**. Concept dashboards have a tighter rail; the wider sidebar leaves less room for content. Confirm token name (likely `--sidebar-w` already declared in `tokens.css`).
3. **Kanban column auto-collapse**. With 5 statuses the live board still narrows two columns to 66px ("In Review" / "Done" collapsed by default in `prefs.kanban.collapsed_columns`). Consider whether that default helps; maybe expand all columns by default and let the user collapse.
4. **Sessions row time-range**. `12:00 → 12:00` shows when start ≈ end. Render "instant" or hide the arrow.
5. **Auto Mode side panels**. Verify subagent chip + tool log render correctly with the populated v3-031 fixture (running session, queued reviewer, 3 tool entries). Compare against `automode-integration.html`.
6. **Lessons sparkline / Reinforce hover**. Concept shows a small SVG sparkline next to each lesson and a "Reinforce" button on hover. Verify the live screen has both — the data (`reinforce_events`, `reinforce_count`) is present.
7. **Issues bug-report visual contract**. Per §2.8 the structure is implemented — eyeball it side-by-side to verify symptom-leads, the aging bar fills proportionally to issue age, location is console-styled.
8. **Dashboard bento heterogeneity**. Concept v5 mixes widget sizes (small / medium / large / wide) into a true bento grid. Live appears more uniform. Worth a careful side-by-side pass.

The user explicitly wants more Chrome-based testing in the next session — focus on browser-driven polish, not code archeology.

## Servers (still running on ports `:8765` and `:8766` until the next reboot)

If you need to restart:

```powershell
# v3 viewer (cwd MUST be the fixture so /api/lessons /api/issues find data)
cd C:/Users/gruku/Files/Claude/claude-tools/.worktrees/taskmaster-v3/.fixture-kanban
$env:TASKMASTER_ROOT = "C:/Users/gruku/Files/Claude/claude-tools/.worktrees/taskmaster-v3/.fixture-kanban"
python C:/Users/gruku/Files/Claude/claude-tools/.worktrees/taskmaster-v3/start_server.py

# Concept reference (curated index at `/`)
cd C:/Users/gruku/Files/Claude/claude-tools/.superpowers/brainstorm
python -m http.server 8766 --bind 127.0.0.1
```

URLs:
- Live v3:  `http://127.0.0.1:8765/v3/`
- Concepts: `http://127.0.0.1:8766/` (curated finalized concepts only — `index.html` filters out rejected variants)

Routes (note plural-vs-singular gotchas):
- `#/dashboard`, `#/kanban`, `#/table` (new), `#/auto`, `#/lessons`, `#/issues`, `#/sessions`, `#/recap` (singular, not `recaps`), `#/task` (no id → resumes last viewed), `#/task/<id>`

## Browser MCP setup for next session

The MCP-controlled tab is *backgrounded* by default — that's exactly what exposed the visibility-check bug. Don't be surprised if `document.visibilityState === 'hidden'`. The fix in this commit handles it; if you're auditing newly added polling loops, re-check that they don't block on visibility before the first fetch.

When using `mcp__claude-in-chrome__javascript_tool`:
- Returns containing certain strings get blocked with `[BLOCKED: Cookie/query string data]`. When that happens, return a simple concatenated string instead of nested JSON.
- Use `cache: 'no-store'` on `fetch()` calls when probing API endpoints — the static main.js can otherwise serve stale.
- `ToolSearch` to load chrome tools at session start; they're deferred.

## Fixture data summary (29 tasks · 8 issues · 9 lessons · 4 recaps · 3 handovers · 2 auto sessions)

| Surface | Count | Notes |
|---------|-------|-------|
| tasks | 29 | 12 todo / 4 in_progress / 4 in_review / 3 blocked / 6 done; all priorities; v3-050 has anchors/docs/codex_note/verdict (richest demo); v3-051 is `locked_by: agent-codex-2`; v3-052 is `done` with `patchnote` + activity log; v3-053 has codex `verdict: ok` |
| issues | 8 | P0×2, P1×2, P2×2, P3×2; statuses open/investigating/resolved |
| lessons | 9 | 7 active + 2 passive; gotcha/principle/pattern kinds; reinforce histories |
| recaps | 4 | SES-0001..0004 spanning Plan 2 → Plan 6 + design pass; SES-0004 may not surface in sessions list — needs handover linkage |
| handovers | 3 | Original + Plan-3 + Plan-6 |
| auto sessions | 2 | v3-030 stopped, v3-031 running with subagents/tool_log |

## Known fixture quirks

- `viewer.json` mutates under any UI interaction (theme/density/dashboard layout/kanban filters). Revert with `git checkout -- .fixture-kanban/.taskmaster/viewer.json` after any session.
- Playwright runs may leave `.events.jsonl` files in `.fixture-kanban/.taskmaster/auto/sessions/` — `rm` them.
- The full revert recipe: `git -C <worktree> checkout -- .fixture-kanban/`

## Key file locations for next session

- Polish audit: `docs/superpowers/plans/2026-05-01-v3-polish-audit.md` (with corrections noted above)
- Tokens: `plugins/taskmaster/viewer/css/tokens.css`
- Shell: `plugins/taskmaster/viewer/css/shell.css`
- New Table view: `plugins/taskmaster/viewer/js/screens/table.js`, `plugins/taskmaster/viewer/css/screens/table.css`
- Sidebar: `plugins/taskmaster/viewer/js/components/sidebar.js`
- Brainstorm concepts root: `C:/Users/gruku/Files/Claude/claude-tools/.superpowers/brainstorm/16245-1777231623/content/`
- Curated concepts index: `C:/Users/gruku/Files/Claude/claude-tools/.superpowers/brainstorm/index.html`

## Integration decision still pending

Per autonomous-mode policy, branch has not been pushed and no PR opened. 18 commits ahead of master since this whole redesign began. User decides when (or whether) to push or merge — do not push without explicit approval.

## One-liner cheat sheet for next session

```
git -C C:/Users/gruku/Files/Claude/claude-tools/.worktrees/taskmaster-v3 log --oneline -10
ls C:/Users/gruku/Files/Claude/claude-tools/.worktrees/taskmaster-v3/docs/superpowers/plans/2026-05-01-*
# Servers should already be running on :8765 and :8766; if not, see "Servers" above
# Open http://127.0.0.1:8765/v3/ and http://127.0.0.1:8766/ side-by-side
# Pick up at next-session targets §3 above; surface-stepping pass is the highest-impact remaining item
```
