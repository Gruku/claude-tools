# Handoff — 2026-05-01 — V3 polish pass #2 + control-consistency audit

**Branch:** `feature/taskmaster-v3` (worktree `.worktrees/taskmaster-v3`)
**Tip:** `c949b4c`
**Ahead of master:** 23 commits, no push, no PR.

This continues from `2026-05-01-v3-polish-pass1-handoff.md` (tip was `4136248`). Five new commits this session, plus a control-consistency audit captured as a separate reference doc.

## What this session was for

Picking up from pass-1's handoff list, the user explicitly wanted "more Chrome testing and aligning things per our design" — so this was a Chrome-driven polish session focused on the highest-impact remaining items.

## What landed (5 commits)

| Commit | What |
|--------|------|
| `a75103b` | **Surface ladder + sidebar + sessions instant-time.** Tokens `--bg-canvas` `#181a20→#14151a`, `--bg-card` `#26262b→#1f2025`, `--bg-board-col` `#1c1d22→#0f131c`, `--bg-card-hover` `#2c2e34→#25262c` — concept-aligned palette. Sidebar 300→220px (concept uses 200; kept 20px buffer for the live sidebar's badge col + collapse toggle). Sessions/timeline render single timestamp when `start === end`. Fixture viewer.json default `collapsed_columns: []`. |
| `4ed8c7e` | **Auto-mode tool_log fixture fix.** v3-031 fixture's tool_log used `at/tool/target` field names; the renderer in `auto-side-panels.js:92` reads `ts/name/args`. Switched to the renderer's contract — Auto Mode side panel now displays the 3 tool entries instead of "none". |
| `d9d99db` | **Dashboard bento heterogeneity.** Rail width 280→220 (concept-aligned). `.dash-bottom` converted to a 4-col dense grid that respects size: `small/medium=1`, `wide=2`, `hero=4`. Size-aware density tuning: `widget--small` runs tighter padding (8/10) + smaller label, `widget--tall/hero` get real min-heights (320/360). Fixture: phase-deliverables and what-changed flagged `tall`. `phase-deliverables` widget caps at 8 items + "+N more →" link instead of dumping all 16 phase tasks. |
| `4704964` | **Phantom CSS variables in dashboard.css.** **The big one.** dashboard.css referenced `--line-1`, `--ink-0`, `--ink-1`, `--dash-gap`, `--dash-pad` — none of which exist in tokens.css. Result: widgets had **0px borders** (invisible separation), **0 gap between cards** (visual blob), and inconsistent text colors. Fixes: defined `--dash-gap`/`--dash-pad` inside `.dash` so they resolve cleanly; replaced `--line-1` → `--border-strong`, `--ink-0/--ink-1` → `--ink`; switched `--dash-card-bg` to `--bg-panel` (concept's actual widget bg, recessed so the border does the visual lift); set `--dash-card-border` to solid `#2c2d33` instead of the alpha `--border` token which renders nearly invisible against panel; widget radius 10→8. |
| `c949b4c` | **Phantom CSS variables in issues + lessons.** Same class of bug audit-driven. `.issues__sev-chip.is-active` and `.lessons__view-toggle button.is-active` used `--bg-active` (undefined) → active state was visually invisible. `.issues__column` used `--bg-pane` (typo for `--bg-panel`) → column backgrounds rendered transparent. Promoted `--accent-blue/edit/green` from per-call hardcoded fallbacks into proper tokens so they're discoverable + overridable. |

## Phantom-variable audit — full results

After fixing the dashboard, ran an exhaustive Python sweep across all CSS files comparing every `var(--…)` reference to every `--var:` definition.

- **119 variables defined across all CSS files** (most local to their screen — fine).
- **3 truly phantom** (no fallback, undefined): `--bg-active`, `--bg-pane`, `--name` (the last is just inside a comment in tokens.css). All real ones fixed.
- **32 phantom-primaries-with-fallback** (e.g. `var(--epic, var(--ink-3))`): most are runtime-injected by JS — `--epic`, `--ec`, `--card-w`, `--anim-dur` are *supposed* to be set inline by the renderer, fallback is the design. The 3 promoted to tokens this session (`--accent-blue/edit/green`) were working via fallback but now proper.

If you want to re-run the audit:
```bash
cd plugins/taskmaster/viewer/css && python -c "
import re, os
defined = {}
for root, _, files in os.walk('.'):
    for fn in files:
        if not fn.endswith('.css'): continue
        with open(os.path.join(root, fn), encoding='utf8') as f:
            for m in re.finditer(r'(--[a-zA-Z0-9_-]+)\s*:', f.read()):
                defined.setdefault(m.group(1), set()).add(os.path.join(root, fn))
for root, _, files in os.walk('.'):
    for fn in files:
        if not fn.endswith('.css'): continue
        path = os.path.join(root, fn)
        with open(path, encoding='utf8') as f:
            for ln, line in enumerate(f, 1):
                for m in re.finditer(r'var\(\s*(--[a-zA-Z0-9_-]+)\s*([,)])', line):
                    if m.group(1) not in defined and m.group(2) == ')':
                        print(f'  {os.path.basename(path)}:{ln}  {m.group(1)}')"
```

## Control-consistency audit — separate reference doc

The user asked for an audit of buttons / search fields / actions across screens, with Kanban as canon. Captured here:

**`docs/superpowers/plans/2026-05-01-v3-control-consistency.md`**

That doc contains: per-screen control inventory, six concrete inconsistencies, and a 3-layer plan (shared primitives → relocate to topbar → action consolidation). Future polish sessions should pick up from there — Layer 1 first (low risk, ~1hr, gives us the `.tm-search` / `.tm-segmented` / `.tm-action` / `.tm-subcount` vocabulary), then Layer 2 (relocate every screen's chrome to the global `#topbar-actions` slot), then Layer 3 (action button visual unification).

## Status of the pass-1 audit's §5 fix list

| # | Item | Status this session |
|---|------|--------|
| 1 | `--page-pad` consumer fix | ✅ done in pass 1 |
| 2 | `--text-base` 18→16px | ✅ done in pass 1 |
| 3 | Screen title H1 30→24px | ✅ done in pass 1 |
| 4 | Surface stepping ladder | ✅ **done this session** (`a75103b`) |
| 5 | Remove rogue `idle` text | ✅ done in pass 1 |
| 6 | Kanban data binding | ✅ done in pass 1 |
| 7 | Compress lessons screen | ✅ done in pass 1 |
| 8 | Issues severity glyph + aging bar | ✅ already implemented (probe error in pass 1) |
| 9 | Task detail Variant A 2-column | ✅ already implemented (probe error in pass 1) |
| 10 | Dashboard widget head asymmetric padding | ✅ done in pass 1 |
| 11 | Build Table view | ✅ done in pass 1 |
| 12 | Decide what "dedicated Task view" means | ✅ done in pass 1 |

Pass 1's §3 next-session targets — status:

| # | Item | Status |
|---|------|--------|
| 1 | Surface-stepping palette | ✅ done (`a75103b`) |
| 2 | Sidebar 300→260 | ✅ done — went to 220 (`a75103b`) |
| 3 | Kanban auto-collapse default | ✅ done (`a75103b`) |
| 4 | Sessions instant-time | ✅ done (`a75103b`) |
| 5 | Auto Mode side panel verification | ✅ done (`4ed8c7e`) |
| 6 | Lessons sparkline / Reinforce hover | ✅ verified — already shipped |
| 7 | Issues bug-report visual contract | ✅ verified — already shipped (and picked up phantom-var bugs in `c949b4c`) |
| 8 | Dashboard bento heterogeneity | ✅ done (`d9d99db` + `4704964`) |

All eight pass-1 next-session targets are now closed.

## What's still off — next-session targets

The control-consistency audit doc is the new primary punch list. In addition:

1. **Right rail height imbalance on dashboard.** Left rail with the tall `phase-deliverables` widget extends ~931px while right rail is ~480px, leaving ~450px of empty canvas below the right rail. Could be solved by `flex: 1 1 auto` on the last widget per rail, or by redistributing widgets across rails. Cosmetic.
2. **Board surface "Phase board" widget.** Currently shows 2 thin columns (Up next + In progress, max 4 cards). Concept's center board is the visual centerpiece — could be richer (live pulses on auto-running cards, more cards visible, tabular numerals). Not broken, just under-leveraged.
3. **Briefing strip on dashboard reads "0 tasks closed, 0 new issues, 0 lessons promoted."** Because the fixture's `last_seen_at` is recent, no events are returned. To demo this convincingly, set `dashboard.last_seen_at` to an older timestamp in the fixture.
4. **Edit-mode chrome on dashboard.** The `data-edit='1'` styling exists but isn't tested visually. Toggle "Edit layout" → confirm dashed borders, drag handles, remove buttons, `+ Add widget` tiles all render correctly with the new tokens.
5. **Auto-mode + Recap + Task Detail visual passes** were not re-probed this session after the surface-stepping change. Quick Chrome sweep to confirm nothing regressed.

## Servers (still running on `:8765` and `:8766`)

If they died, restart:

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
- Concepts: `http://127.0.0.1:8766/`

Routes (note the singular/plural gotchas from pass 1):
- `#/dashboard`, `#/kanban`, `#/table`, `#/auto`, `#/lessons`, `#/issues`, `#/sessions`, `#/recap` (singular), `#/task` (no id → resumes last viewed), `#/task/<id>`

## Browser MCP gotchas (carried over from pass 1)

- The MCP-controlled tab is *backgrounded* by default. Visibility-aware polling now handles this; don't be surprised by `document.visibilityState === 'hidden'`.
- `mcp__claude-in-chrome__javascript_tool` blocks some return values with `[BLOCKED: Cookie/query string data]`. When that happens, return a plain concatenated string instead of nested JSON.
- Use `cache: 'no-store'` on `fetch()` calls when probing API endpoints — `main.js` can otherwise serve stale.
- `ToolSearch` to load Chrome tools at session start; they're deferred. Specific names: `mcp__claude-in-chrome__tabs_context_mcp`, `tabs_create_mcp`, `navigate`, `javascript_tool`, `read_console_messages`, `resize_window`.

## Fixture notes

- `viewer.json` mutates under any UI interaction (theme/density/dashboard layout/kanban filters/last_seen_at). If a test/probe leaves it in a bad state, revert with `git checkout -- .fixture-kanban/.taskmaster/viewer.json`.
- This session's fixture diff includes the dashboard layout sizes (tall variants) and an updated `last_seen_at`.

## Key file locations for next session

- **Control-consistency audit + plan:** `docs/superpowers/plans/2026-05-01-v3-control-consistency.md` ← start here
- **Pass-1 polish audit:** `docs/superpowers/plans/2026-05-01-v3-polish-audit.md` (with corrections noted in pass-1 handoff)
- Tokens: `plugins/taskmaster/viewer/css/tokens.css`
- Shell: `plugins/taskmaster/viewer/css/shell.css`
- Dashboard CSS: `plugins/taskmaster/viewer/css/screens/dashboard.css`
- Dashboard renderer: `plugins/taskmaster/viewer/js/screens/dashboard.js`
- Widget catalog: `plugins/taskmaster/viewer/js/components/widget-catalog.js`
- Widget frame: `plugins/taskmaster/viewer/js/components/widget-frame.js`
- Brainstorm concepts root: `C:/Users/gruku/Files/Claude/claude-tools/.superpowers/brainstorm/16245-1777231623/content/`
- Curated concepts index: `C:/Users/gruku/Files/Claude/claude-tools/.superpowers/brainstorm/index.html`

## Integration decision still pending

Per autonomous-mode policy, branch has not been pushed and no PR opened. **23 commits ahead of master** since the redesign began. User decides when (or whether) to push or merge — do not push without explicit approval.

## One-liner cheat sheet for next session

```
git -C C:/Users/gruku/Files/Claude/claude-tools/.worktrees/taskmaster-v3 log --oneline -10
ls C:/Users/gruku/Files/Claude/claude-tools/.worktrees/taskmaster-v3/docs/superpowers/plans/2026-05-01-*
# Read 2026-05-01-v3-control-consistency.md and start at Layer 1
# Servers should already be running on :8765 and :8766; if not, see "Servers" above
# Open http://127.0.0.1:8765/v3/ and http://127.0.0.1:8766/ side-by-side
```
