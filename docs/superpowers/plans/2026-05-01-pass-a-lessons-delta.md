# Pass A — Lessons Visual Delta

**Concept refs (in `.superpowers/brainstorm/15283-1777223061/content/`):**
- `lessons-shelves.html` — three-shelf grid + cards w/ summary + foot
- `lessons-active-passive.html` — same structure, makes active/passive signal split explicit

**Current implementation:** `viewer/css/screens/lessons.css` + `viewer/js/components/lesson-card.js` (matches Plan 5b spec).

The handoff's "concept deltas" notes were partially wrong — re-grounded against the actual mockups below.

## Concept structure (per card)

```
┌──────────────────────────────────────────────┐
│ LSN-08      ╭─[sparkline] 14× · 2d─╮          │  ← head: id + active-signal pill (right)
│ Title in 13px medium                          │  ← title row
│ Summary text in 11px ink-2, line-height 1.5  │  ← summary row (NEW)
│ WHEN: **/*.css  **/*.html  +3       │ 12 hits │  ← anchors row + passive meter on right
│ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─│  ← dashed divider
│ VIEW-12  VIEW-08  +3 more       14× fired    │  ← foot: task pills + reinforce count
└──────────────────────────────────────────────┘
```

## Deltas vs current

| # | Area | Concept | Current | Action |
|---|---|---|---|---|
| 1 | **Card body** | summary text under title (11px, ink-2, lh 1.5) | no summary rendered | Add `.lesson-card__summary` from `lesson.summary \|\| lesson.body` |
| 2 | **Card foot** | dashed top border, task pills (epic-blue) + "N× fired" right-aligned | no foot | New `.lesson-card__foot` row from `lesson.related_tasks` + `reinforce_count` |
| 3 | **Active signal placement** | sparkline + count pill in **head row** (margin-left:auto) — gold soft bg | sparkline in separate "signals" row beside dot-meter | Move sparkline-pill into head; keep dot-meter for passive (concept calls it `passive-meter`, on anchors row right) |
| 4 | **Anchors row** | "WHEN:" label uppercase 9px tracking; pills 9px mono; passive-meter right-aligned with left dashed border | label is "When:" (mixed case 11px); no passive meter on this row | Restyle label, move dot-meter onto this row as `.passive-meter` |
| 5 | **Shelf header** | dashed `border-bottom: 1px solid border-soft` + 8px padding-bottom; `shelf-count` mono on right ("5 lessons") | no border, count rendered inline as text in title span | Add divider; pull count into right-aligned mono span |
| 6 | **Card grid** | fixed 2-col (`1fr 1fr`, 10px gap) at viewer width | auto-fill minmax(360px, 1fr) | Switch to 2-col |
| 7 | **Core card** | gold-tinted **border** (`rgba(214,184,95,0.3)`) + gold gradient | gradient only, no border tint | Add border tint |
| 8 | **Reinforce action** | concept doesn't show a hover-revealed button — relies on click-card. (active-passive variant has one as positioned absolute overlay) | hover-revealed bottom-right button | Keep current button (concept is ambiguous; existing behaviour is fine) |
| 9 | **Filters row** | scope chip-row above shelves ("Scope: All · CSS / styling · Git / branches · …") | no scope filter | **Defer.** Requires server-side scope categorisation. Out-of-scope for visual polish; flag for backlog. |
| 10 | **Flat / By-Anchor views** | not in concept (concept only shows shelves) | stubs that reuse shelf chrome | **Defer.** Visual treatment for these is undefined; current "reuse chrome" is acceptable until concept arrives. |

## Scope for this pass

**Will do** (deltas 1–7):
- Add summary + foot DOM in `lesson-card.js`
- Restructure: spark in head, dot-meter on anchors row as passive-meter
- Restyle shelf header divider + right-aligned count
- 2-col grid + core border tint
- Update screen tests if any depend on DOM structure

**Won't do this pass:**
- 9 (scope filters) — needs data model
- 10 (Flat/By-Anchor polish) — needs concept
- Any change to the topbar — already settled in L1–L3

## Risks / open questions

- **Lesson schema** — does `lesson` carry `summary` and `related_tasks`? Need to verify or fall back gracefully.
- **`reinforce_count`** — already on lesson per Plan 5b. Confirm.
- **`passive_matches_7d`** — concept uses "12 hits" or pulse-dots; current code reads `lesson.anchor_matches_7d`. Verify field name.
- **Sparkline component** — already exists; just relocate. Same for dot-meter.

## Test plan

1. After CSS/JS changes: hard refresh viewer, visit `#/lessons`, confirm:
   - All three shelves render with divider + right-count
   - Cards show id · sparkline-in-head · title · summary · anchors+passive · foot
   - Core cards have gold border tint + gradient
   - Hover doesn't translate (per project rule)
2. Re-run any Lessons playwright test to catch DOM-structure regressions.
3. Chrome MCP: visual diff snapshot of `#/lessons` against this delta doc.

## Resume here

After sign-off, implement in this order:
1. Update `lesson-card.js` (DOM + bindings)
2. Update `lessons.css` (shelf header, foot, grid, core border, signal placement)
3. Verify against fixture data (`.fixture-kanban` lessons), patch fallbacks for missing fields
4. Run tests
5. Commit as `feat(viewer): pass A — lessons visual polish to match concept`
