# V3 Control-Consistency Handoff (after L1–L3)

**Captured:** 2026-05-01 · branch `feature/taskmaster-v3` · tip `b95f874`
**Replaces:** `2026-05-01-v3-polish-pass2-handoff.md` as the live entry point.

## What this session shipped

Closed all three layers of `2026-05-01-v3-control-consistency.md`. The viewer now has a unified topbar across every screen and a shared vocabulary of UI primitives.

| Layer | Commit | Summary |
|---|---|---|
| **L1** — shared primitives | `a4d5166` | `.tm-search`, `.tm-segmented` (+`--icon`), `.tm-action` (+`--primary`/`--ghost`/`--icon`), `.tm-subcount`, `.tm-chip-row` appended to `viewer/css/components.css`. No DOM changes. |
| **L2** — DOM relocation | `a510d61` | All 8 non-Kanban screens migrated to mount their top-level controls into `#topbar-actions` via shared helper `viewer/js/lib/topbar.js`. Auto-status pill restyled and pinned to the left of the cluster (`order:-1; margin-right:auto`). |
| **L3** — action consolidation | `a510d61` | Per-screen action classes dropped from JS. Icon-prefix vocabulary settled: ✎ edit · + add/new · ⧉ copy · ↑ reinforce · ↻ regenerate · ✕ archive · ‹ › prev/next · ↗ open · ⏸ pause · ■ stop. Aria/title coverage on every button. |
| **L1–3 follow-ups** | `b95f874` | Dead-CSS sweep (~100 lines), `aria-disabled` stub state for `+ Lesson` / `+ Issue`, run-state styling for Auto Mode Pause/Stop (amber/red icons; aria-disabled when no active session). |

Plan doc reflects final state: `docs/superpowers/plans/2026-05-01-v3-control-consistency.md`.

## Topbar contents per screen (verified live)

| Screen | Topbar |
|---|---|
| Dashboard | pill · `✎ Edit layout` |
| Kanban | pill · subcount · search · priority chips · density / group / sort / `+ Task` |
| Table | pill · subcount · search · `+ Task` |
| Lessons | pill · subcount · Shelves/Flat/By-Anchor segmented · `+ Lesson` (disabled) |
| Issues | pill · subcount · severity chip-row · Hybrid/Kanban/List · `+ Issue` (disabled) |
| Sessions | pill · subcount · search · Diary/Lanes/By-Task · `+ New note` |
| Auto Mode | pill · Spine/Log · `⏸ Pause` (amber) · `■ Stop` (red) |
| Recap | pill · `‹` `›` · `⧉ Copy resume` · `↗ Open in Sessions` · `✎ Edit recap` |
| Task Detail | pill · Document/Graph · `✎ Edit` · `✕ Archive` |

The auto-status pill survives every navigation pair. No overflow at 1500px. Verified via Chrome MCP probe at the end of the session.

## What's next — Visual polish pass

The plan with the user is to take the redesign from "structurally consistent" (now done) to "visually polished and on-spec." Three passes in this order:

### Pass A — Lessons screen (drifted from concept)

The Lessons screen is the most visually drifted from the concept. The card vocabulary (shelves, sparkline pill, dot meter, anchor pills, gold-gradient core variant) is partially implemented but doesn't match the concept's typography, spacing, or hierarchy. Specific deltas to investigate:

- Concept: shelf header is large italic-serif with a subtle gold rule; today's shelf header is small with a grey tagline
- Concept: card backgrounds step (core > active > retired); today they're flat with only the core gradient
- Concept: anchor pills sit inline with the title, not in a separate row
- Concept: reinforce action is a corner stamp, not a hovered button
- The "Flat" and "By Anchor" views are stubs visually — they reuse shelves chrome inappropriately

Start by re-reading the concept reference (probably `plugins/taskmaster/viewer/concept/lessons*.html` if present, otherwise the Plan 5 narrative) and writing a small delta doc before editing. Then iterate in `viewer/css/screens/lessons.css` and `viewer/js/components/lesson-card.js`.

### Pass B — Card overflow audit

Cards overflow inconsistently across screens — long titles wrap differently in Kanban vs Table-row vs Issues vs Lesson cards vs Recap receipts. Symptoms to look for:

- horizontal scrollbars at narrow widths (sidebar-collapsed, narrow viewport)
- title clipping with ellipsis in some places, wrapping to N lines in others, no clamp at all in others
- chip rows that break out of their container instead of wrapping
- file-path mono strings that push past card edges
- right-rail content that overflows when the rail is narrower than its longest line

The fix is *not* a screen-by-screen patch — it should land as a shared `.cmp-card` (or extend `.tm-action`-style primitive system to cards) so behaviour is consistent. The user explicitly called this out as the next unification step after L3.

### Pass C — Unified card component

Once overflow is fixed, the card primitive becomes the next member of the `.tm-*` vocabulary. Rough shape:

- `.tm-card` — base (surface, border, radius, padding)
- `.tm-card__head`, `.tm-card__body`, `.tm-card__foot` — slots
- `.tm-card__title` — wrap/clamp behaviour built-in
- `.tm-card__chip-row` — uses existing `.tm-chip-row`
- variants: `--ghost` (deep bg), `--accent` (left tint), `--issue`, `--lesson`, `--recap`

The kanban card (`.card-task`) is the canonical implementation today, same as how `.kanban-search` was canon for L1. Audit it, factor out `.tm-card`, then migrate other screens onto it.

## Out-of-scope for next session (flagged but deferred)

- Wire real click handlers for `+ Lesson` and `+ Issue` (modals don't exist yet; design lives in Plan 5b).
- Rich `+ New note` flow on Sessions (currently navigates to `#/sessions?new=1` which is a stub).
- Right-rail height balancing on Dashboard — the left rail is taller than the right rail when phase-deliverables expands. Cosmetic.
- Briefing strip demo data (set older `last_seen_at` in `.fixture-kanban/.taskmaster/viewer.json` to make the strip light up).

## How to resume

1. **Branch state:** `feature/taskmaster-v3`, tip `b95f874`, 30 commits ahead of master, **no push** (per repo rule). All commits are on local branch only.
2. **Server:** `python -m plugins.taskmaster.backlog_server --port 8765 --root .fixture-kanban` (or whatever wrapper is set up). Confirm port 8765 is listening; the viewer is at `http://127.0.0.1:8765/v3/`.
3. **Chrome MCP:** there's an open Taskmaster tab (id seen this session: `2039539982`). On a new session, call `tabs_context_mcp` first to find the live tab. Don't reuse stale tab ids.
4. **First read:**
   - `docs/superpowers/plans/2026-05-01-v3-control-consistency.md` — final state of the structural pass.
   - This file — the live entry point.
   - `plugins/taskmaster/viewer/css/components.css` — see what `.tm-*` primitives already exist before extending them.
   - `plugins/taskmaster/viewer/js/lib/topbar.js` — same shape works fine for a card factory, if useful.
5. **Concept reference:** if there's a `plugins/taskmaster/viewer/concept/` dir or equivalent, that's the visual source-of-truth for Pass A. Otherwise the Plan 5 narrative (in `docs/superpowers/plans/`) drives Lessons.

## Key code locations

| Concern | File |
|---|---|
| Topbar helper (used by every screen) | `viewer/js/lib/topbar.js` |
| Shared primitives (CSS) | `viewer/css/components.css` (`.tm-*` block at the bottom) |
| Auto-status pill style | `viewer/css/shell.css` (`.auto-status-pill`) |
| Lessons screen | `viewer/js/screens/lessons.js` + `viewer/components/lesson-card.js` + `viewer/css/screens/lessons.css` |
| Kanban canon (card) | `viewer/js/components/card.js` + `viewer/css/screens/kanban.css` (search for `.card-task`) |
| Right-rail (shared with task-detail) | `viewer/js/components/right-rail.js` + `.right-rail` block in `components.css` |

## Gotchas to avoid

1. **Don't wipe `#topbar-actions` on screen cleanup.** Kanban used to do this and it dropped the global auto-status pill. The contract is: each screen's `mount()` calls `claimTopbar()` which preserves the pill while wiping the rest. Cleanup runs *before* the next screen mounts; the next screen's `claimTopbar()` re-establishes its own controls.
2. **Phantom CSS variables.** The `--undefined-token` pattern silently resolves to nothing. When extending `.tm-*` or adding `.tm-card`, every `var(--something)` must either resolve in `tokens.css` or carry an inline fallback. Last session's audit doc has a Python recipe for re-running the check.
3. **`prefs` is the patch helper, not data.** Read state from `store.getPrefs()`, write via `prefs.patch({...})`. Same pattern in every screen that persists state (lessons.js, issues.js, sessions.js, auto-mode.js, task-detail.js).
4. **`docs/superpowers/` is gitignored locally.** Use `git add -f` to commit handoff/plan files. Don't push these — they archive locally only.
5. **No emojis in user output.** Tool result probes can use them freely; don't echo them in prose.
