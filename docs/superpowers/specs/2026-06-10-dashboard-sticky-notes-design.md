# Dashboard Redesign + Sticky Notes — Design Spec

**Date:** 2026-06-10
**Status:** approved (user delegated remaining decisions: "proceed with making everything by yourself, I trust you")
**Target:** taskmaster 3.15.0
**Branch:** feat/dashboard-sticky-notes (stacked on feat/c2-live-component-diagram viewer state)

## Problem

1. The Dashboard (`#/dashboard` → Continuity screen) is broken in practice:
   - The hero shows stale "do this next" content (8-day-old handover for already-shipped work). No freshness awareness.
   - Rails are dominated by noise: 21 month-old `in-review` tasks, 15 clean-up items including test fixtures, "Recent" handovers 20–24 days old, "Open — Nothing here".
   - Titles truncate at ~15 chars while ~25% of the viewport is dead space.
   - Topbar glitches: brand renders "Taskmaste" (clipped), version chip shows "v?".
   - `marked.js` is loaded from CDN with a **wrong SRI hash** — the browser blocks it, so markdown rendering is silently broken. Console also shows favicon 404.
   - Dead code: `css/screens/dashboard.css` widget classes + `js/components/board-surface.js` are orphaned remnants of the removed bento dashboard.
2. The user routes "message to future self" around taskmaster entirely (self-sent chat messages), because end-of-day thoughts are **situational** — they don't match a handover's task-attached shape. There is no freeform, persistent, personal surface in the system.

## Decisions (locked with user)

| Decision | Choice |
|---|---|
| Dashboard's first job | **Notes first** — sticky board is the hero; continuity is a compact band below |
| Claude access to notes | **Read AND write** via MCP; start-session surfaces notes; end-session may write one |
| Author differentiation | **Required** — user-written vs claude-written notes must be visibly distinct |
| Note structure | **Light** — freeform text + author + created + pin; archive lifecycle; no statuses/tags/colors-as-categories |
| Visual treatment | **Real paper notes** — skeuomorphic post-its on the dark desk |

Decisions delegated to Claude (rationale inline below): layout = Desk (Option A), staleness policy, view-switcher retirement, storage/API shape.

## 1. Sticky Notes — entity

### Storage

- Directory: `.taskmaster/notes/NOTE-NNN.md` (zero-padded 3, same pattern as ideas/issues).
- Archived notes move to `.taskmaster/notes/_archive/NOTE-NNN.md` (file move, never delete).
- Frontmatter:

```yaml
id: NOTE-001
author: user          # "user" | "claude" — who typed it into the system
created: '2026-06-10T09:30:00Z'
updated: '2026-06-10T09:30:00Z'
pinned: false
archived: false
archived_at: null
```

- Body = the note text, freeform markdown. No title field — a sticky note has no title; lists render the first line.
- Author semantics: viewer-created → `user`; MCP-created → `claude`. No override parameter — the channel defines the author. (If the user dictates a note to Claude, it is still claude-authored: the visual distinction answers "did I write this with my own hands?")

### MCP surface (taskmaster_v3.py — FastMCP tools)

| Tool | Args | Behavior |
|---|---|---|
| `backlog_note_create` | `text`, `pinned=False` | Creates note with `author: claude`. Returns slim note. |
| `backlog_note_list` | `include_archived=False` | Pinned first, then created desc. Slim: id, author, pinned, created, first_line, archived. |
| `backlog_note_get` | `id` | Full note incl. body. |
| `backlog_note_update` | `id`, `text=None`, `pinned=None` | Partial update; bumps `updated`. |
| `backlog_note_archive` | `id` | Sets archived + moves file to `_archive/`. |

Notes are **not** continuity items — they never appear in `/api/continuity`. They have their own surface and API.

### HTTP API (backlog_server.py)

- `GET  /api/notes?include_archived=0` → `{"notes":[...]}` (full bodies — board renders them; counts are small)
- `POST /api/notes` `{text, pinned?}` → creates with `author: user`
- `POST /api/notes/<id>/update` `{text?, pinned?}`
- `POST /api/notes/<id>/archive`

(POST-verb subroutes match the existing `/api/decisions/<id>/resolve` pattern.)

### Skill integration

- **taskmaster:start-session** — after the dashboard summary, a "Your desk" section lists unarchived notes (pinned first, first lines). Notes are *read as orientation context*, never auto-closed or auto-archived by Claude.
- **taskmaster:end-session** — if the session leaves a genuinely loose, situational thought that fits no entity (not a task/idea/issue/handover), Claude may write **at most one** consolidated claude-authored note. Never duplicate handover content into a note. Default is to write none.
- `plugin-dev:skill-development` must be invoked before editing either SKILL.md; `plugin-dev:mcp-integration` before touching taskmaster_v3.py.

## 2. Dashboard redesign — "The Desk"

Route stays `#/dashboard`; screen title becomes **"Dashboard"**. `continuity.js` is replaced by `desk.js` (new screen) to keep the diff honest; reusable continuity components are kept.

### Layout (top → bottom)

1. **Auto-mode strip** — unchanged (existing component, only when active).
2. **Sticky board** (`.dk-board`) — the hero surface.
   - Quick-add composer always first: paper-styled input ("Write a note…"), Enter commits (Shift+Enter = newline), stays focused for rapid capture. Pin toggle in composer.
   - Notes in a CSS grid `repeat(auto-fill, minmax(220px, 1fr))`; pinned first (pushpin marker), then created desc.
   - Empty state: a single ghost note: "Your desk is clear."
3. **Continuity band** (`.dk-continuity`) — compact, pruned, four rails: **Resume · Review · Decide · Clean-up**, reusing `createItemRow` (compact variant) and rail/spine styling.

### Paper-note visual treatment (user rule-compliant skeuomorphism)

- Notes are **light paper on the dark desk** — the inversion is what makes them read as physical objects.
  - User notes: muted post-it yellow paper (`#e8d98a`-family), dark warm ink (`#2c2718`).
  - Claude notes: cool blue paper (`#9fc0e8`-family), dark cool ink (`#16202e`), plus a small `✦ claude` author mark.
- Square-ish presence: `aspect-ratio: 1 / 0.9` min on grid cells; long notes clamp (~10 lines) with inline expand on click.
- Deterministic tilt: `transform: rotate()` of −1.2° to +1.2° derived from note id hash (NOT on hover — static placement; hover changes paper brightness only; no motion, no shadows).
- Folded bottom-right corner via CSS gradient triangle. Pin = red pushpin dot at top edge when pinned.
- Author/date line in small caps at the note's top; archive (✕) and pin affordances appear on hover via opacity (no movement).
- Note body renders markdown via the (fixed, vendored) renderer; paper-dark ink overrides for code/links on paper.
- These notes are an intentional, scoped exception to the flat-surface language — justified because the user explicitly asked for "real notes". No box-shadows still holds; depth comes from paper contrast + fold.

### Continuity pruning (opinionated defaults, no toggles)

- Every rail caps at **5 items**, freshest first; overflow renders one quiet link-row: "+N older → " linking to the owning screen (kanban/table, issues, sessions).
- Items with `age_days > 30` never render as cards — they only count toward the "+N older" link.
- **Resume** = open/in-progress handovers + in-progress tasks (≤ 30d). The "Recent (closed handovers)" sublist is gone — Sessions screen owns history.
- **Review** = in-review tasks + open P0/P1 issues (≤ 30d).
- **Decide** = open decisions (decision card with Pick/Drop preserved, rendered inside the rail at full rail width — the old full-width hero is removed).
- **Clean-up** = stale in-progress (≥7d) tasks + old open issues (≤ 30d window still applies).
- A rail with zero fresh items renders nothing (no "Nothing here" placeholders).
- **View switcher retired**: Time and Entity views are removed (`groupByTime`/`groupByEntity` and view-switcher component deleted). Kanban/Table/Sessions already provide those framings. Prefs key `continuity.view` ignored/dropped.

### Bundled fixes

| Fix | Detail |
|---|---|
| marked.js SRI failure | Vendor `marked.min.js` into `viewer/vendor/` and load locally. Local-first tool; no CDN, no SRI. |
| Brand clip + "v?" | Diagnose sidebar brand CSS (clipping at narrow width) and version fetch; fix both. Version comes from `/api/identity`. |
| favicon 404 | Inline `<link rel="icon">` data-URI (16×16). |
| Dead code | Delete `js/components/board-surface.js` and the orphaned `.dash*/.widget*` rules in `css/screens/dashboard.css`; repurpose/rename the file for desk styles or remove if empty. |

## 3. Out of scope

- Project switcher / single-app v3 work (separate epic).
- Notes sync to Linear/anything external.
- Re-theming other screens; only the dashboard surface changes.
- Reworking continuity item *generation* (taskmaster_v3 classification) beyond the rail-side pruning above — except: no new types added.

## 4. Testing

- **Python (pytest)**: note CRUD round-trip (create/list/get/update/archive, file moves, numbering), API endpoints (GET/POST/update/archive, author stamping user vs claude), continuity unaffected by notes.
- **Viewer unit (node --test)**: pruning logic (cap 5, >30d exclusion, overflow counts), note ordering (pinned first), tilt determinism hash.
- **Playwright e2e**: dashboard mounts with board + composer; add note via composer → paper card appears (user paper); pin → reorders first; archive → leaves board; continuity rails capped with "+N older" link; no console errors (SRI fix verified by `marked` presence).
- Two-harness playbook applies; e2e specs live in `viewer/tests/`.

## 5. Versioning

- `plugins/taskmaster/.claude-plugin/plugin.json` → **3.15.0**
- `.claude-plugin/marketplace.json` → 3.15.0
- `plugins/taskmaster/CHANGELOG.md` → new `## 3.15.0` section (minor: new MCP tools + new viewer surface + fixes)
- Run `python scripts/check_plugin_version_bump.py --base origin/master` before any PR.
