# V3 Pass B — Interaction Backbone Handoff

**Captured:** 2026-05-02 · branch `feature/taskmaster-v3` · tip `803cc4b`
**Replaces:** `2026-05-01-v3-control-consistency-handoff.md` as the live entry point.
**Companion docs:** `2026-05-01-pass-a-lessons-delta.md` · `2026-05-01-ux-audit.md`

## Why this handoff exists

The L1–L3 control-consistency work and Pass A made screens *structurally consistent*. The UX audit (`docs/superpowers/plans/2026-05-01-ux-audit.md`) then reframed the remaining polish into 3 sequenced passes — **B′ interaction backbone**, **C′ card unification**, **D visual nits**. We're partway through B′.

## What this session shipped

| Commit | Scope |
|---|---|
| `bda0837` | Pass A follow-ups: XSS fix in lessons.js By-Anchor view (innerHTML→DOM API for file-path key); lesson-card surface `--bg-card` → `--bg-panel` (matches concept); `--epic-viewer` → `--accent-blue`; dropped dead `Object.assign` after re-render. **Plus** the UX audit doc itself. |
| `bf404d6` | **B1b — Lesson detail screen + drill-in.** New screen at `#/lesson/:id`, lesson cards click through (`cursor:pointer`, role=link, keyboard activation), reinforce button click is suppressed from card-click. Topbar gets `↑ Reinforce`; back link starts in topbar. |
| `803cc4b` | Lesson detail polish: back link moved out of topbar into a page-local crumb (`‹ Lessons / Core`) per user feedback; drops `max-width: 1200px` so the crumb pins to the actual content-edge. |

Branch is **34 commits ahead of master**, no push (per repo rule).

## What works now

The Lessons screen is **functionally complete** for the first time:

- **Drill-in** — click any lesson card → `#/lesson/:id` (full-screen detail)
- **Detail layout** — italic-serif title · meta row (kind/id/shelf/created) · summary (the markdown body) · anchor pills · timestamped reinforcement history (8 events for L-001 in fixture) · side block with signals + related tasks/issues
- **Reinforce action** — `↑ Reinforce` (or `↑ Revive` for retired) in topbar; rebuilds detail from fresh server data after success
- **Card surface** — corrected to `--bg-panel` per concept
- **Server** — `/api/lessons` and `lesson_list_extended()` MCP tool now surface the markdown body as a `summary` field (was loaded as `_body` and dropped)

## What's next — Pass B′ remainder

Per the audit, B′ has 4 work units; we did B1b (lesson detail) and B4 (lessons surface fix) this session. **B1a turned out to be a false positive — Dashboard task cards already drill in via `renderMinimalCard` → `renderCard` in `card.js:46-49`.** The audit agent missed that link.

### B1c — Issue detail + clickable card body

**Pattern:** mirror `lesson-detail.js`. New screen at `#/issue/:id`, register in `main.js`, wire click on `issue-card` body (excluding the existing nested task-pill handler at `issue-card.js:118`), add `cursor:pointer` styling.

Detail content for issues (from API shape — verify against `/api/issues`):
- Header: severity glyph · id · status · component · created
- Summary / body
- Symptom + repro (if those fields exist; concept shows them as console-style blocks)
- Aging bar / aging meter (existing component)
- Reproduction history (if it's a thing in the schema — check `issue.reproduces`/similar)
- Side block: signals + related tasks/lessons

Issue body text — same gotcha as lessons. Check whether `/api/issues` surfaces the markdown body. If not, repeat the one-line pattern from `bda0837` in `backlog_server.py` (drop `_body` filter, add `summary` field).

### B2 — Search wiring (3 screens)

| Screen | Current | Action |
|---|---|---|
| **Lessons** | no search | Add `tmSearch` to topbar, filter on title + summary + anchors |
| **Issues** | no search | Add `tmSearch`, filter on title + symptom + component |
| **Sessions** | search input mounted but **fires no filter** (worst-of-both — looks interactive, isn't) | Wire the existing `viewer:sessions-search` event to actually filter `renderTimeline` |

`tmSearch` from `lib/topbar.js` is already used on Kanban + Table + Sessions — copy that pattern. Default debounce 180ms.

### B3 — Filter chips + lesson `category` schema

User signed off on "yes add" for the Lessons scope filter row (concept: All / CSS / Git / Plugins / Schema / Workflow). This requires:

1. **Schema migration:** add `category` field to lesson frontmatter. Update `taskmaster_v3.py` `load_lesson` to handle missing field gracefully (default to `null` or `'general'`)
2. **Fixture migration:** populate `category` on all 9 fixture lessons. Categories: CSS / Git / Plugins / Schema / Workflow / General — pick best fit per lesson
3. **Server:** include `category` in `/api/lessons` response (additive — already happens since the dict spread includes new fields)
4. **UI:** scope chip-row in Lessons topbar (use existing `tm-chip-row` pattern from Issues severity row)
5. **Server tests:** update `test_server_lessons.py` to assert category surfaces

For Issues, the audit flagged a similar component-chip row (All / viewer / cli / plugins). Issues already have a `component` field per the existing schema — check `issue-card.js` to confirm. If yes, just add the chip-row UI; no schema migration needed.

## Pass B′ sequence (recommended order)

1. **B1c — issue detail + drill-in** (matches B1b, ~similar size)
2. **B2 — search wiring** (3 screens, mostly mechanical, fast)
3. **B3 — filter chips** (lessons schema is the slow part; issues should be quick)

Then the audit's Pass C′ (card unification) and Pass D (visual nits) become the final polish passes.

## Pre-existing follow-ups (Pass E in audit)

These are minor; fold into the next convenient commit rather than batching:

- `lessons.spec.js:39,43` — `toHaveClass(/on|is-active/)` is too loose; tighten to `/\bon\b/`
- Add empty-summary negative-case test for `lesson-card` (the `if (summaryText)` branch)
- Lesson detail: 8 events in fixture but only 8 render — fixture has 8 events, was confusing because earlier git diffs showed 9. **Not a bug.** No action needed.

## How to resume

1. **Branch state:** `feature/taskmaster-v3`, tip `803cc4b`. 34 commits ahead of master, **no push.**
2. **Server:** running locally via `cd .fixture-kanban && python ../start_server.py` (background task on port 8765). Confirm `/api/lessons` returns objects with both `summary` and `shelf` fields.
3. **Brainstorm server:** running on port 8766 serving concept HTML at `127.0.0.1:8766/16245-1777231623/content/`. Concepts to consult for B1c: `issues-v2-bugreport.html`, `issues-hybrid.html`.
4. **Chrome MCP tabs in last session:**
   - `2039539982` — Taskmaster viewer (`#/lesson/L-001`)
   - `2039539983` — brainstorm concepts
5. **First reads:**
   - This file
   - `docs/superpowers/plans/2026-05-01-ux-audit.md` — the audit that reframed the passes
   - `plugins/taskmaster/viewer/js/screens/lesson-detail.js` — the canonical pattern for B1c
   - `plugins/taskmaster/viewer/css/screens/lessons.css` lines 230+ — the detail-screen styles to mirror in `issues.css`

## Code locations

| Concern | File |
|---|---|
| Lesson detail screen | `viewer/js/screens/lesson-detail.js` |
| Lesson card click wiring | `viewer/js/components/lesson-card.js:21-33` |
| Lesson detail CSS | `viewer/css/screens/lessons.css` (`.lesson-detail` block + `.ld-*` rules) |
| Route registration | `viewer/js/main.js:11-20` |
| Topbar primitives | `viewer/js/lib/topbar.js` (`claimTopbar`, `tmSubcount`, `tmSearch`, `tmSegmented`, `tmAction`) |
| Server lesson endpoint | `plugins/taskmaster/backlog_server.py:4330-4347` (and MCP tool at line 4806) |
| Issue card | `viewer/js/components/issue-card.js` |
| Issue screen | `viewer/js/screens/issues.js` |

## Gotchas inherited from prior sessions

1. **Don't wipe `#topbar-actions` on screen cleanup** — `claimTopbar()` preserves the auto-status pill, raw `replaceChildren()` does not.
2. **`prefs` is the patch helper, not data** — read state from `store.getPrefs()`, write via `prefs.patch({...})`.
3. **`docs/superpowers/` is gitignored locally** — use `git add -f` to commit handoff/plan files.
4. **Hard-reload the viewer after editing JS modules** — `location.reload(true)` in chrome MCP, or Ctrl+Shift+R. Module imports cache aggressively.
5. **Fixture playwright drift** — running the reinforce test mutates `.fixture-kanban/.taskmaster/lessons/*.md`. Always `git checkout -- .fixture-kanban/` before committing.
6. **`docs/superpowers/plans/2026-05-01-ux-audit.md` audit table claims Dashboard cards don't drill in. This is wrong** — `renderMinimalCard` is just `renderCard` with `density:'minimal'`, and `renderCard` wires the click. Don't burn time on B1a.
