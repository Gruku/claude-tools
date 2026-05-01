# V3 viewer polish audit — 2026-05-01

**Scope:** systematic side-by-side review of every shipped v3 screen against the finalized brainstorm concepts. Captured at viewport 1440×900 via Chrome MCP probes against `http://127.0.0.1:8765/v3/` (live) and `http://127.0.0.1:8766/16245-1777231623/content/` (concepts).

**TL;DR:** the live build has clean structure but has drifted from the concepts in three big ways: **everything is ~12% larger**, **page rhythm is asymmetric and ignores the design tokens**, and **two screens (Kanban, single-recap) don't render their primary content with the current fixture**. Auto Mode also depends on a fixture-state bug that masked the running-session experience until we patched it just now.

This document is organized in the order to fix things — system-wide first (fixes ripple to every screen), then per-screen, then bugs, then feature gaps.

---

## 1. System-wide drift — fix these first

### 1.1 `--page-pad` declared but not actually applied
- Tokens at `:root`: `--page-pad: 20px`, `--page-gap: 16px`.
- Computed `padding` on every screen's main container: **`27px 33px`** (asymmetric, hard-coded).
- This means the design pass that introduced `--page-pad` is half-landed: the token exists, but the consumer that should read it (`main` / `.screen-mount`) is using literal CSS instead.
- **Fix:** find the rule that sets `27px 33px` (likely `shell.css` or `screen-mount`), replace with `padding: var(--page-pad) calc(var(--page-pad) + 4px)` or simply `padding: var(--page-pad)`. Remove the asymmetric horizontal extension unless there's a deliberate reason — concepts are symmetric.

### 1.2 Body font is 18px in live, 16px in concepts
- Live `body` computed `font-size: 18px`; `--text-base: 18px`.
- Concept body `font-size: 16px`.
- This makes every card, pill, label and column ~12% larger than designed. The concept rhythm assumes 16px base — chip widths, line-heights, gaps were all sized against that.
- **Fix:** drop `--text-base` to 16px. Will require sweep of any per-component overrides that compensated for the larger base.

### 1.3 Heading hierarchy diverges — H1 30px live vs H2 24px concept
| Screen | Live | Concept |
|---|---|---|
| Issues | `H1` "Issues" 30px | `H2` "Issues — v2" 24px |
| Auto Mode | `H1` "Auto Mode" 30px | `H2` "Auto Mode — final integration" 24px |
| Lessons | `H1` "Lessons" — | `H2` 24px |
- Concepts use `H2` at 24px because the concept page wraps everything in a parent `H1`. In production the screen heading IS the page H1, so semantic mismatch is fine — but the **size** should still be 24px, not 30px. The concepts were calibrated for 24px section titles.
- **Fix:** drop the screen-title size from 30px → 24px (and reduce weight slightly if it now reads heavy at the smaller size).

### 1.4 Color palette: live has fewer tokens, concepts have a richer scale
Concepts define `--bg-canvas`, `--bg-shell`, `--bg-panel`, `--bg-card`, `--bg-board`, `--bg-board-col` plus `--ink`, `--ink-2`, `--ink-3` and severity tokens `--p0`/`--p1`. Live appears to use a flatter palette derived from `--surface`, `--surface2`, `--bg`. The concept's deliberate shell→panel→card→board ladder is what gives the brainstorm pages their depth without shadows. Live looks flatter as a result.

**Fix:** import the concept's surface stepping verbatim. Add `--bg-canvas`, `--bg-shell`, `--bg-panel`, `--bg-card`, `--bg-board`, `--bg-board-col` to `tokens.css` and route the screens through them (background of body = `--bg-shell`, sidebar = `--bg-panel`, cards = `--bg-card`, board column = `--bg-board-col`). This is what the L-007 lesson is asking for — "surface stepping over box-shadow for elevation".

### 1.5 Sidebar width 300px — wider than concept's nav rail
Concept dashboards render with a tighter nav rail (~240–260px). 300px makes screens feel narrower; on lessons/issues the inner pane is only 660px wide despite a 1440px viewport because the sidebar + main_pad + screen-mount internal padding all add up. Concepts give the main content visibly more room.
**Fix:** drop sidebar to 260px (or split the difference, 280). Verify `--sidebar-w` token exists; if not, add one.

### 1.6 The `idle` text in the topbar looks like a leftover
On every screen `body.innerText` still contains the literal word **"idle"** before the page title. It's the topbar status pill's empty-state placeholder leaking into the layout when no session is active. The new `auto-status-pill` (green) was meant to replace that. Either the old `idle` indicator is still present, or the empty-state of the new pill is rendering the word "idle".
**Fix:** locate the `idle` text emitter (likely a pre-existing topbar status component, separate from the new auto-status-pill) and remove or hide it when there's no running session. There should be exactly **one** indicator: the new green pill, hidden when nothing is running.

---

## 2. Per-screen findings

### 2.1 Dashboard — `/v3/#/dashboard` vs `dashboard-v5.html`

| Aspect | Live | Concept | Comment |
|---|---|---|---|
| Outer pad | `27px 33px` | `40px 24px` (container) | mismatch |
| Card pad | `10px 12px 6px` (asymmetric) | `10px` (uniform) | concept is square-ish |
| Body font | 18px | 16px | universal |
| Total widget DOM nodes | **77** | 20 | live overdraws |
| Bento grid feel | column-of-tiles | true bento with mixed sizes | drift |

**Findings:**
- Concept `dashboard-v5` is a **bento** — mixed widget sizes (small/medium/large) snapped into a CSS grid that fills the viewport edge-to-edge. Live appears to be widget rows with `widget--medium` 280px tiles repeating, no bento heterogeneity.
- Widget header pad `10px 12px 6px` is asymmetric (less bottom). Concept widgets use uniform 10px. This is almost certainly the source of the "doesn't quite line up" feeling.
- Live widgets are 280px wide; concept cards are 330px. Combined with body font 18px, every chip and label visibly oversizes the widget.
- Empty state: dashboard widgets that have no data show nothing (silent). Concept v5 shows lightweight empty-state copy (e.g. "No active session") — explicit, not silent.

### 2.2 Kanban — `/v3/#/kanban` vs `kanban-filters-v2.html`

**Critical issue:** the kanban renders **zero cards** in our fixture. Phase stepper shows `0` for every phase ("‹0›0‹0›0⚲Orphans"). All 5 status columns show 0 tasks. Two columns (`In Review`, `Done`) auto-collapse to 66px because they have no content.

**Diagnosis:** the v3 phase-stepper component does not appear to count tasks per phase from `/api/backlog`. Even with 29 tasks distributed across P-01..P-04, the stepper's badges all read 0. This is either (a) a phase-status filter (only counts tasks in `active`/`in_progress` phases?) that excludes done-phase tasks, or (b) a wiring bug where the stepper never receives the phases array. Needs viewer-side investigation — the API serves the data correctly.

| Aspect | Live | Concept | Comment |
|---|---|---|---|
| Column width | 173/173/173/66/66 (collapsed) | 193 × 4 (uniform) | live narrows + collapses |
| Column pad | 12px | 8px | live looser |
| Card pad | n/a (no cards rendered) | 7px 9px | — |
| Card width | n/a | 167px | — |
| Card height | n/a | 134px | — |
| Headings | H1 "Kanban" 30px | H2 24px | drift |
| Filter bar | `Find by title…` input + epic chips + phase stepper | same elements | structurally aligned |

**Findings beyond the empty-board bug:**
- Concept uses **4 columns** (Todo, In-progress, Review, Done) at uniform width. Live adds a 5th "Blocked" column upfront and then collapses two on the right. Concept folds blocked into a chip on the card, not a separate column. This is a fundamental layout decision worth re-deciding.
- "Orphans" pill is an addition not in concept — fine to keep, but it should be visually de-emphasized (live shows it the same prominence as the phase chevrons).
- Cards weren't observable, but text says class `task-card`; concept uses `task-card` (167×134) — class names align, so once data wires up the comparison can resume.
- Empty-column placeholder is `kanban-col-empty` 122×141 with 45px vertical padding — very tall. Concept doesn't show an explicit empty placeholder per column.

### 2.3 Cards — `full-card-polish.html` + `card-experiments.html`
Couldn't observe live cards because kanban is empty. Once that's resolved, eyeball:
- Per-epic color: concept uses **chip-only (variant E)** — colored chip on the card, no left rail, no background tint. Verify live matches (this is the rejected-variant trap from the spec table).
- Click-to-copy on task-id chip — concept has a subtle pulse-on-copy. Verify live behavior.
- Card header reorganization: ID + epic chip + priority pill + title. Concept stacks them with title as the visual anchor.

### 2.4 Task detail — `/v3/#/task/v3-050` vs `task-detail-v2.html`

| Aspect | Live | Concept |
|---|---|---|
| Layout | single column | **2-column grid 393px main + 280px rail** |
| Sections | sec-docs, sec-spec, sec-plan, sec-notes, sec-activity | doc-section ×6 with right-rail meta |
| Section width | full main width | 590px |
| `td-grid` display | flex/grid? | `grid-template-columns: 393.333px 280px` |

**Critical drift:** the concept's task-detail Variant A is a **two-column layout** — main document content on the left, a meta rail on the right with quick facts (status pills, dates, dependency chips, lock indicator, codex note). Live appears single-column (`td-grid` exists but I couldn't confirm it's actually 2-col without taking a screenshot). The feature-rich `td-doc-meta` block exists in DOM but its placement may be inline rather than rail.

**Other findings:**
- Variant toggle `Document | Graph` is present (`td-seg-btn on` for Document is active). Good.
- Anchors I added (`PR #142`, `viewer/js/api.js`, spec link) — they appear in body text but I couldn't confirm a dedicated anchors panel like the concept's. May be folded into Docs section instead.
- Codex note (`spec_review.codex_note`) renders somewhere — body text contains "discriminator" — but its visual treatment vs the concept's "serif quote in a box" needs verification.
- `td-doc-meta` exists; its layout in the rail vs inline is the key visual difference.
- Lock indicator (v3-051) — live has `[class*="lock"]` present. Concept renders this as a 🔒 chip in the meta rail next to the status pills.
- Section accordion behavior: concept shows all sections expanded inline; live behavior unverified — make sure they don't auto-collapse.

**The "missing dedicated Task view" question:**
The user mentioned "we're missing a dedicated Task view". Task detail does exist at `#/task/<id>`, but possibly the user means:
- A **distraction-free reading mode** for a single task (no sidebar, no topbar) — for sharing or focusing.
- A **dedicated tab in the sidebar** for "open task" that swaps to the most-recently-viewed task.
- A **multi-task split view** (open two tasks side-by-side).

Needs a clarifying question — the data and detail screen are wired; whatever "dedicated view" is, it's a layout shell on top.

### 2.5 Sessions — `/v3/#/sessions` vs `sessions-nested.html` / `sessions-detail-rail.html`

| Aspect | Live | Notes |
|---|---|---|
| Layout modes | `Diary | Lanes | By Task` toggle | matches concept's hybrid |
| Counts | `3 sessions · 3 handovers · 3 recaps` | accurate for fixture |
| Session row | `12:00 → 12:00 SES-0001 VIEWER-001 STANDALONE …` | **duration shows 0:00 → 0:00 when start ≈ end** (broken display) |
| Heading | "Sessions / Handovers" subtitle | concept says "Sessions" |

**Findings:**
- Time-range display: when a session has `start == end` (likely the case for our quick fixture data), it displays as `12:00 → 12:00`. That's confusing — should show "instant" or hide the arrow.
- Plurality / count: SES-0004 (latest recap I added) does not appear in the sessions list. The session derivation logic likely requires a matching handover with the recap's session_id — confirm whether SES-0004 needs an explicit handover entry to surface, or whether this is a bug.
- The Diary/Lanes/By-Task toggle maps to the spec's Hybrid C concept — good.
- Right-rail detail view (`sessions-detail-rail.html`) — couldn't verify it triggers on row-click. Manual test pending.

### 2.6 Recap — `/v3/#/recap` (singular) vs `recap-detail.html`

**Route note:** sidebar links to `#/recap` (singular). My earlier handoff used `#/recaps` — that route 404s/redirects to dashboard. Update any docs referring to `#/recaps`.

The recap-detail concept has a **two-tier layout**: narrative on top (story prose), structured diff below (what landed, snapshots, token cost). Verify live matches:
- Token cost prominently displayed
- snapshot_before / snapshot_after pair visible
- task_ids rendered as chips with click-through

### 2.7 Lessons — `/v3/#/lessons` vs `lessons-active-passive.html` ★ priority focus

| Aspect | Live | Concept |
|---|---|---|
| Outer pad | `24px 28px` | shelf-level 0px (parent handles) |
| Total page height | **1557px** | 836px |
| Shelf gap | 28px | varies, smaller |
| Shelf grid gap | 12px | 8px |
| Shelf header | `lessons-shelf__header` 24px tall | `shelf-head` 40px (richer) |
| Tagline width | 196px (truncates aggressively) | 478px (fits) |
| Heading | H1 30px | H2 24px |
| Active/Passive split | yes, has shelves | yes, separates active+passive |
| Reinforce button | TBD (interactive, requires hover) | exists |

**Findings:**
- The page is **almost twice as tall** as the concept (1557px vs 836px). Single column → everything stacks → endless scroll. Concept uses a denser shelf grid that fits on a single fold. Re-examine grid dimensions and column count.
- Shelf header is shrunken (24px vs concept's 40px). This compresses the shelf branding (active/passive identifier, sparkline). Worth bringing back.
- Tagline width 196px causes ellipsis truncation on most shelves. Concept allocates 478px. Allow more room or move tagline below the title row.
- Sparklines: concept page has subtle inline SVG sparkline showing reinforce-history. Live: didn't observe SVG/canvas — may not be implemented or rendered inline differently.
- Reinforce button: concept reveals on hover with a "Reinforce" affordance. Live has the data (`reinforce_count`, `reinforce_events`) but the affordance presentation is unverified.

### 2.8 Issues — `/v3/#/issues` vs `issues-v2-bugreport.html` ★ priority focus

| Aspect | Live | Concept |
|---|---|---|
| Outer pad | `24px 28px` | — |
| Total page height | **1368px** | ~700px |
| Heading | H1 "Issues" 30px | H2 24px |
| Severity chips | `issues__sev-chip` 62×26, 3px 10px pad | severity glyph + label, ~20–24px wide |
| Severity glyph | `[class*="severity-glyph"]` not found | concept has visual glyphs (●▲■▼) |
| Aging bar | `[class*="aging"]` not found | concept has explicit aging bar per row |
| Console-style location | `code` element not found | concept has monospace location chips |

**Findings:**
- The "bug-report flavor" of the concept (severity glyph + console location + symptom lead + aging bar) is **only partially landed**. The `issues__sev-chip` is a flat label "P0/P1/P2/P3" — concept uses a glyph + tier-color combination. Severity feels less scannable.
- Aging bar is missing. Concept renders a horizontal bar per row showing how stale the issue is — gives "what should I look at first" at a glance.
- Location chip should be monospace and console-styled (e.g. `viewer/js/main.js:87` formatted distinctively). Live wraps it as plain text.
- Symptom is meant to be the lead text on each row, with title secondary. Verify priority of these in the live row layout.
- The `Resolved` shelf at the bottom (collapsed by default) — live has `issues__resolved-shelf` 18px tall, suggesting it's there. Verify expand/collapse state persistence.

### 2.9 Auto Mode — `/v3/#/auto` vs `automode-integration.html` ★ priority focus

**Critical (now fixed):** the v3-031 fixture had `stopped: true` baked in. As a result, the spine showed "No auto-mode session running", the topbar pill was hidden, and the entire Auto Mode demo experience was broken. Fixed locally — set to `false`, populated subagents and tool_log so the page now demos the running state. **This change is uncommitted; revert if intent was to demo the empty state.**

After the fix:

| Aspect | Live | Concept |
|---|---|---|
| Layout | 3-col (subagents left · spine center · budget right) | 3-col matching |
| Spine | central column, vertical, with active-node pulse | matches |
| Spine pulse | 1.6s, transform: scale (post-fix) | matches |
| Heading | H1 "Auto Mode" 30px | H2 24px |
| Topbar pill | green, hidden when no session | matches when session.stopped=false |
| Main pad | `27px 33px` | concept uses tighter 16-20px |

**Findings:**
- Spine shows correct shape (fixed). Active-node pulse should now be smooth (the design pass landed `transform: scale` for this — verify in browser).
- Subagents column: I added one queued subagent in fixture (`code-reviewer-1`). Verify it renders with the correct chip style.
- Tool log: I added 3 tool entries. Verify they render in chronological order with timestamps.
- Budget column: shows `tokens used/limit`, `time used/limit`, `context`, `cost_usd`. Concept renders these as compact progress bars. Verify the live version matches the concept's vertical bar arrangement.
- Toggle "Spine | Log" — present in concept and live (segmented control). Verify Log mode actually swaps to chronological event waterfall.
- Stop / Pause buttons: live shows "⏸ ■" — concept shows them with text labels and clearer affordance (e.g. inverse pill). Verify accessibility (aria-labels, keyboard focus).

---

## 3. Bugs & data drift caught during the audit

| # | Where | Issue | Severity |
|---|---|---|---|
| B1 | `.fixture-kanban/.taskmaster/auto/sessions/v3-031.json` | `stopped: true` masks the running-session demo on Auto Mode page | **fixed locally, uncommitted** |
| B2 | Kanban screen | Phase stepper shows 0 for all phases; cards never render | **High** — needs viewer investigation |
| B3 | Sessions row | `12:00 → 12:00` appears when start ≈ end; should show "instant" | Low |
| B4 | Sessions list | Recap SES-0004 not surfacing | Low (likely needs handover linkage) |
| B5 | Topbar | Word `idle` leaks into every screen | Low — visual noise |
| B6 | Page padding | `--page-pad` token defined but consumer ignores it | Medium — system-wide |
| B7 | Body font | `--text-base: 18px` makes everything 12% larger than designed | Medium — system-wide |

---

## 4. Feature gaps requested

### 4.1 Table view (Obsidian-Bases-style) — **new feature**

What it is: an alternative to Kanban for the same task data — a sortable, filterable table with column controls, group-by, and pinning. Useful for triage, batch updates, and comparing fields across many tasks.

**Plan in broad strokes:**
- Add a sidebar entry (in **FRONTDOOR** group, next to Kanban) — `▭ Table` at `#/table`.
- Reuse the existing backlog data flow (`/api/backlog`).
- Library option: vanilla `<table>` with custom sort/filter (consistent with the rest of the codebase, no react/grid library).
- Columns (all sortable, toggleable): ID, Title, Status, Priority, Phase, Epic, Estimate, Branch, Started, Updated, Anchors-count, Dependencies-count.
- Top toolbar: search (reuse kanban's), per-column filter, group-by (Phase / Epic / Status / Priority), density toggle, columns popover.
- Row click → opens task detail (same as kanban).
- Persist column order, visible columns, sort, filters in `viewer.json` prefs (`table` key).
- Empty state with "no results" + clear-filters affordance.
- Optional: row-level inline edit on Status / Priority (like Bases). Defer until v1 is solid.

**Suggested execution path:** spec → plan (single milestone, ~5 tasks) → implement → wire to sidebar → tests.

### 4.2 "Dedicated Task view" (clarification needed)

Task detail exists at `#/task/<id>`. Need to know which of these you mean:
- **A.** A distraction-free reading mode (no sidebar, no topbar) for sharing / focus / printing.
- **B.** A dedicated sidebar entry that always opens "the current task" (most-recently-viewed or pinned).
- **C.** A multi-task split view (compare two tasks side-by-side).
- **D.** Something else — you tell me.

Most likely interpretation given context is **A** (a clean, focus mode) — would pair well with the Table view as the entry point.

---

## 5. Suggested fix order

Doing these in order minimizes rework — system-wide changes ripple to every screen.

1. **Fix `--page-pad` consumer** so the token is honored on every screen (`27px 33px` → `var(--page-pad)`). System-wide.
2. **Drop `--text-base` to 16px** and verify nothing breaks at smaller base. System-wide.
3. **Drop screen-title H1 size to 24px** (or 22px if 24px reads heavy at 16px base). System-wide.
4. **Adopt concept's surface stepping** (`--bg-shell`, `--bg-panel`, `--bg-card`, `--bg-board-col`). Touches every component bg.
5. **Remove the rogue `idle` text from the topbar** — leave the new green pill as the single auto-status indicator.
6. **Investigate kanban phase-stepper data binding (B2)**. This is blocking proper kanban testing.
7. **Compress lessons screen height** — denser shelf grid, taller shelf headers, wider taglines.
8. **Add severity glyph + aging bar to issues** to bring the bug-report flavor in line with concept.
9. **Verify task-detail Variant A is 2-column with right-rail meta**, not single column.
10. **Audit dashboard widget header padding** — replace `10px 12px 6px` with uniform `10px 12px`.
11. **Build Table view (4.1)** as a new sidebar entry — separate plan needed.
12. **Decide what "dedicated Task view" means (4.2)** and sketch.

---

## 6. Probe inventory (so this is reproducible)

Probes used: `mcp__claude-in-chrome__navigate`, `mcp__claude-in-chrome__javascript_tool`, `mcp__claude-in-chrome__resize_window`. Viewport pinned at 1440×900. Live URL set: `http://127.0.0.1:8765/v3/#/<route>`. Concept URL set: `http://127.0.0.1:8766/16245-1777231623/content/<concept>.html`.

For any future re-audit: reload the live tab after a viewer change; the brainstorm tab is static. The fixture can pollute under Playwright runs — revert with `git -C <worktree> checkout -- .fixture-kanban/`.
