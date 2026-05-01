# V3 Control-Consistency Audit & 3-Layer Plan

**Captured:** 2026-05-01 · branch `feature/taskmaster-v3` · tip `c949b4c`

## Why this exists

Across the v3 viewer, every screen ships its own version of the same UI primitives — search inputs, view toggles, primary action buttons, subcounts. The result is no two screens feel like the same product. Kanban is the most-finished implementation, so we're treating it as **canon** and aligning the rest to it.

This document is the durable reference. The 3-layer plan at the bottom is the work order; check items off as we ship them.

---

## Per-screen control inventory

Probed live via Chrome MCP at `http://127.0.0.1:8765/v3/`. Each row is what a user actually sees today.

| Screen | `#topbar-actions` slot | View toggle location | Search location | Primary actions | Class naming |
|---|---|---|---|---|---|
| **Kanban (canon)** | subcount · search (⌘K) · priority chips · view-toggle (▤▦) · group-by | ✅ topbar | ✅ topbar (`.kanban-search`) | — | `kanban-*` |
| Dashboard | empty | "Edit layout" floats top-right of body | — | "✎ Edit layout", "+ Add widget" (in body) | `dash-*` |
| Table | empty | — | ✅ in body (`.tbl-search`) | filter chips in body | `tbl-*` |
| Lessons | empty | "Shelves / Flat / By Anchor" segmented in body header | — | per-card "↑ Reinforce" / "↑ Revive" | `lessons__*` (BEM) |
| Issues | empty | "Hybrid / Kanban / List" segmented in body header | — | — | mixed |
| Sessions | empty | — | ✅ in body (`Search sessions…`) | "+ New note" in body | `sessions-*` |
| Auto Mode | empty | "Spine / Log" toggle in body | — | ⏸ ■ control buttons | `auto-*` |
| Recap | empty | — | — | "‹ / ›" prev/next, "⧉ copy resume", "Open in Sessions", "✎ edit recap" — all in body | `recap-*`, `recap-action`, `recap-nav-arrow` |
| Task Detail | empty | "Document / Graph" segmented in body | — | "Edit", "Archive" in body | `td-*`, `td-seg-btn`, `td-action` |

Single point of contact for the topbar slot today: `kanban.js:52` (`document.getElementById('topbar-actions')`). `main.js:75` also drops the auto-status pill into the same slot — that's the only piece running on every screen.

---

## Six concrete inconsistencies

1. **The global topbar slot is dead space everywhere except Kanban.** The `#topbar-actions` element is empty on Dashboard, Table, Lessons, Issues, Sessions, Auto Mode, Recap, and Task Detail. Every screen invents its own header bar instead.

2. **View toggles appear in five different places.**
   - Kanban → topbar
   - Dashboard → floating top-right of body
   - Lessons / Issues → in body header (segmented)
   - Task Detail → in body (segmented)
   - Auto Mode → in body (segmented)

3. **Search inputs in three placements.**
   - Kanban → topbar, with `⌘K` kbd hint
   - Table → body, no kbd hint, different placeholder shape
   - Sessions → body, different placeholder shape again

4. **Per-screen primary actions float wherever there's space.** "Edit", "Archive", "+ New note", "✎ edit recap", "Open in Sessions", "⧉ copy resume" — each its own visual treatment, none aligned. Some use icon prefix (✎ ⧉ +), some don't.

5. **Subcounts only on Kanban.** Kanban shows "29 tasks · 29 visible". Table doesn't show row count, Lessons doesn't show 9 lessons, Issues doesn't show 8 issues, Sessions doesn't show 2 sessions + 3 handovers. Useful information, missing everywhere except canon.

6. **Class-naming chaos.**
   - `kanban-*` (kebab)
   - `tbl-*` (kebab abbreviated)
   - `td-*` (kebab abbreviated)
   - `dash-*` (kebab)
   - `lessons__*` (BEM)
   - `sessions-*` (kebab)
   - `recap-*` (kebab)
   - `auto-*` (kebab)
   No shared `.tm-search`, `.tm-segmented`, `.tm-action`, `.tm-subcount` primitives.

---

## 3-layer plan

Three layers, each independently shippable. Do them in order — Layer 1 unblocks Layer 2 by giving us the shared primitives to relocate into.

### Layer 1 — shared primitives (low risk, ~1hr)

**Goal:** create the canonical CSS vocabulary by extracting Kanban's existing styles into `components.css`. Doesn't move any DOM yet; just gives us reusable classes.

- [x] `.tm-search` — pulls from `.kanban-search`. Includes `⌘K` kbd hint variant. `<input>` shell with icon slot.
- [x] `.tm-segmented` — pulls from `.kanban-density` (the `▤ ▦` group). Supports `.on` / `.is-active` / `aria-pressed="true"` for selected state, and a `--icon` modifier for fixed-square glyph buttons.
- [x] `.tm-action` — primary in-context button. Variants: default (bare `.tm-action`), `--primary` (accent fill), `--ghost` (transparent), `--icon` (square). Replaces `.recap-action`, `.td-action`, `.dash-edit-toggle`, `.sessions-newnote`.
- [x] `.tm-subcount` — the muted "X items · Y visible" line. Pulls from `.kanban-head-subcount`.
- [x] `.tm-chip-row` — wraps the priority/category chip row. Pulls from `.kanban-pri-row`.

**Landed:** commit `a4d5166` — primitives appended to `viewer/css/components.css`. No DOM changes, no regression. Layer 2 can now relocate per-screen markup into these classes.

After Layer 1: the new classes exist alongside the screen-specific ones. Nothing visually changes yet; we just have a vocabulary.

### Layer 2 — relocate to topbar (medium risk, ~2-3hr)

**Goal:** every screen uses `#topbar-actions` for its top-level controls.

For each screen, lift these into the topbar:
- The subcount line (if applicable)
- The search input
- The view toggle
- Primary "this screen" actions (Edit layout, + New note, edit recap, etc.)

Leave inside the screen body:
- Filter chips that depend on screen content (phase/epic on Kanban, status/priority on Table, kind on Sessions)
- Per-row actions (Reinforce, Open task)
- The right-rail / detail content

Per-screen task list:
- [ ] Dashboard — move "Edit layout" into topbar
- [ ] Table — move search + filter chips arrangement, add row count subcount
- [ ] Lessons — move "Shelves / Flat / By Anchor" segmented + lesson count subcount into topbar
- [ ] Issues — move "Hybrid / Kanban / List" segmented + issue count subcount into topbar
- [ ] Sessions — move search + "+ New note" + session count subcount into topbar
- [ ] Auto Mode — move "Spine / Log" segmented into topbar (control buttons stay in body — they target a specific spine node)
- [ ] Recap — move prev/next arrows + "⧉ copy resume" + "Open in Sessions" + "✎ edit recap" into topbar
- [ ] Task Detail — move "Document / Graph" segmented + "Edit" + "Archive" into topbar

When this lands: every screen has the same anatomy. Open any screen, your eye lands on the topbar to find search/toggle/actions; the body is for content + filters that depend on content.

### Layer 3 — action button consolidation (low risk, ~1-2hr)

**Goal:** every primary action across every screen uses the same icon-prefix convention and the same `.tm-action` shell.

- [ ] Settle the icon-prefix convention. Current usage: `✎ Edit layout`, `✎ edit recap`, `+ New note`, `+ Add widget`, `⧉ copy resume`, `↑ Reinforce`. Pick one icon per verb (✎ edit, + add/new, ⧉ copy, ↑ reinforce/promote, ↻ regenerate, ✕ archive/remove) and use it everywhere.
- [ ] Drop the per-screen action classes (`.recap-action`, `.td-action`, `.dash-edit-toggle`, `.sessions-newnote`, `.lesson-card__reinforce`) in favor of `.tm-action`.
- [ ] Audit empty/missing actions. Some screens are missing actions they should have:
  - Issues has no primary action (should have `+ New issue`?)
  - Lessons has no top-level action (should have `+ New lesson`?)
  - Table has no primary action (should have `+ New task`?)
  - Auto Mode has no `Open session log` link in topbar
- [ ] Tooltip + aria-label coverage on all icon-only action buttons.

When this lands: actions feel like a system, not a collection of one-offs. Verb language is consistent. Nothing is missing where the user expects it to be.

---

## Out-of-scope for this work

- Moving secondary content (filter chips, per-row actions) out of the body. Those belong in the body — this work is about top-level chrome only.
- Restyling the auto-mode pill (`mountAutoStatus` in `main.js:75`). It's the one thing that's already global and consistent.
- Visual treatment of the topbar itself. Layout-only relocation; we keep the existing topbar background/border/height.
- Mobile/responsive breakpoints. v3 is desktop-only at this stage; we'll layer responsive on after Layer 3.

---

## How to verify each layer

**Layer 1:** open `components.css` in DevTools, confirm `.tm-search`, `.tm-segmented`, `.tm-action`, `.tm-subcount`, `.tm-chip-row` rules exist and visually match Kanban's existing equivalents. No visual regression on any screen.

**Layer 2:** navigate every route via Chrome MCP at `http://127.0.0.1:8765/v3/`. Probe `#topbar-actions` — every screen should have content in it. Probe `.screen-mount > header, [class*="screen-header"]` — should be empty or contain only filter chips/per-row controls.

**Layer 3:** grep for `class="*action*"` and `class="*-btn"` in `viewer/`. Should resolve to a small set: `.tm-action`, plus auto-mode's hardware-control buttons (⏸ ■), plus per-card affordances (Reinforce, etc.). No more `recap-action`, `td-action`, `dash-edit-toggle`, `sessions-newnote`.

---

## File touch list

When the work happens, expect to edit:

**Layer 1**
- `viewer/css/components.css` — new primitives

**Layer 2** — every screen file
- `viewer/js/screens/kanban.js` (already canonical, may need minor adjustments)
- `viewer/js/screens/dashboard.js`
- `viewer/js/screens/table.js`
- `viewer/js/screens/lessons.js`
- `viewer/js/screens/issues.js`
- `viewer/js/screens/sessions.js`
- `viewer/js/screens/auto-mode.js`
- `viewer/js/screens/recap.js`
- `viewer/js/screens/task-detail.js` (or `viewer/js/components/task-detail-document.js` and `task-detail-graph.js`)

**Layer 3**
- Same screen files as Layer 2, plus their CSS files in `viewer/css/screens/*.css`.
