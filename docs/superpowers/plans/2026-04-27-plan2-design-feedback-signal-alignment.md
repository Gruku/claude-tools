# Plan 2 — Design Feedback Capture (Signal Alignment Pass)

**Date:** 2026-04-27
**Trigger:** T2.24 manual smoke (kanban fixture run, M6) surfaced visual divergence from canonical reference
**Reference:** `C:\Users\gruku\Files\Claude\claude-tools-design\Taskmaster-design\Taskmaster Signal.html` + `screens-signal.css` + `tokens-signal.css` + `screen-kanban.jsx`
**Status:** Captured — not yet executed. Block T2.25–T2.28 progress until signed off.

---

## Important: 150% zoom interpretation

The user views the Signal reference at **150% browser zoom**. Their visual targets (e.g. "more weight on column headers") are calibrated against Signal-at-150%. To match the *perceived* size on the user's screen at our viewer's default zoom (100%), Signal's CSS values should be treated as **multiply-by-~1.5x** when porting size/weight choices — unless we explicitly decide our base zoom should change.

Open question: do we want the v3 viewer to render at 100% with 1.5× upscaled values, or to inherit Signal's CSS verbatim and have the user view both at 150%? The cleaner answer is to upscale, since the v3 viewer should look right at 100%.

---

## A. User-flagged items (verbatim, ordered)

| # | Feedback | Scope | Action |
|---|---|---|---|
| A1 | Remove the word "Kanban" from the header first row — already in the row with search, redundant. Compacts the header. | header layout | Suppress outer topbar `<h1 id="page-title">` on kanban screen (or remove inner `.title`). |
| A2 | Span kanban all the way down, adaptive to height — like the existing kanban version. | board layout / responsiveness | Make `.kanban-page` viewport-tall with internal column scroll. |
| A3 | Should be able to collapse certain columns. | board interaction | New per-column collapse toggle. **Not in Signal**, user-requested. |
| A4 | Major deviation from the Signal reference — analyze + align colors and unity of header. | global tokens + header polish | Re-token surfaces and inks per Signal palette. |
| A5 | "I like our evolution with header and such" — keep our header structure but unify colors. | header | Don't redo our two-row stepper-and-chips layout; just align color/border tokens. |
| A6 | Preserve clear card-vs-background separation (Signal has subtle separation, we have stronger — keep ours). | surface tokens | Keep our card/column delta even if we shift the column shade lighter. |
| A7 | Column headers need more weight than current. | column-head typography | Bump font-size/weight on `.kanban-col-head .lbl`. |

---

## B. Signal-vs-current diff (compressed)

### B1. Header
- Signal: two-row block, `.k-bar-kicker` (mono uppercase 9.5–10px ink-4) + `h2` phase title (16–22px / 600 / -0.01em) + right-side stats (mono 11px ink-3). Boxed (`bg-1`, 1px border, 8px radius).
- Ours: outer `<h1>Kanban</h1>` topbar + inner `.kanban-head` flat row with another "Kanban" `.title` span. No phase context, no stats, no panel boxing.
- Action: drop one of the two "Kanban" titles per A1; defer the kicker+phase-name+stats redesign to a separate ticket — A5 says "keep our evolution".

### B2. Column header weight
- Signal: `font-size: 12px; font-weight: 600; color: var(--ink)` + a status-dot glow halo `box-shadow: 0 0 0 3px color-mix(...)`.
- Ours: `font-size: 11px; font-weight: 500` (inherits ink).
- Action with 150% upscale: target `font-size: 13px; font-weight: 600; color: var(--ink)` and add the dot halo.

### B3. Board height / responsiveness
- Signal: `.kanban-screen { display: flex; flex-direction: column; height: calc(100vh - 90px); }` + `.kanban-full { flex: 1; min-height: 0; overflow: auto; }` + `.board-col { min-height: 100%; }` — board fills viewport, internal scroll, columns stretch.
- Ours: `.kanban-page` flows with content; `.kanban-col { min-height: 340px; }` fixed; entire document scrolls.
- Action: adopt Signal's flex-tall pattern (with our header/strip block heights factored into the calc, or use a `flex-grow` chain so the board takes remaining space below the strip + page-head + stepper + epic-row).

### B4. Column collapse (NEW — not in Signal)
- Pattern proposal: each `.kanban-col-head` gets a small chevron button (right side). Click toggles `.kanban-col.collapsed`.
- Collapsed state: width shrinks to ~32px, label rotates 90° vertical, dot + count visible, body hidden.
- Persist collapse state in prefs as `kanban.collapsed_columns: [keys]`.
- Effort: 1 small task — CSS + JS + prefs round-trip. Plan-2-internal new task or fold into a hygiene-sweep batch.

### B5. Card/background separation
- Signal palette (dark): `--bg #1a1a1e`, `--bg-1 #222226` (column), `--bg-card #26262b` — only ~4 hex steps from column to card.
- Ours: column `#0f131c` is far too dark (16-step delta to card `#1f2025`). The user accepts our stronger separation but wants the *column* surface to be lighter so the whole board feels less heavy.
- Action: raise `--bg-board-col` from `#0f131c` to ≈`#1e2028`. Raise `--bg-card` from `#1f2025` to ≈`#26262b`. Net effect: stronger card-vs-column delta preserved against a graphite (not near-black) board.

### B6. Color unity / global tokens
| Concept | Signal | Ours | Decision |
|---|---|---|---|
| Page canvas `--bg` | `#1a1a1e` | `--bg-canvas #14151a` | raise to `#181a20` (graphite, not coal) |
| Column well | `#222226` | `#0f131c` | **change to `#1e2028`** (per B5) |
| Card body | `#26262b` | `#1f2025` | **change to `#26262b`** (per B5) |
| Card hover | `#2a2a2f` | hard-coded `#23252b` | unify to a token `--bg-card-hover: #2c2e34` |
| Border / hairline | `rgba(230,230,233,0.07)` | solid `#2c2d33` | switch `--border` to alpha rgba; keep `--border-strong` solid for emphasis |
| `--ink-2` | `#a8a8ae` | `#bfc4cc` | **darken to `#a8a8ae`** — secondary text is too prominent today |
| `--ink-4` | `#4d4d54` | absent | **add** for faint/disabled |
| Accent blue | `#5b9dff` | `#4a9eff` | minor; defer (cosmetic) |

---

## C. Action plan — proposed task block (Plan-2 internal)

Branch off the M6 manual-smoke pause (T2.24 was where the deviation surfaced). Add a numbered task list to the plan file as **M6.1 — Signal Alignment Pass**, executed before T2.25 resumes.

| Task | Files | Effort |
|---|---|---|
| **T2.24a** Header compaction (A1) | `index.html` (`<h1 id="page-title">` conditional) OR `kanban.js` (drop inner `.title`) — pick one. Single CSS line tweak in `shell.css` if needed. | 5 lines |
| **T2.24b** Token re-base (A4, A6, B5, B6) | `tokens.css` — adjust `--bg-canvas`, `--bg-board-col`, `--bg-card`, add `--bg-card-hover`, `--ink-4`, soften `--border`, darken `--ink-2`. | ~15 token edits |
| **T2.24c** Column-header weight (A7, B2) | `kanban.css` `.kanban-col-head .lbl` + add dot halo. | 4 lines |
| **T2.24d** Viewport-fill board (A2, B3) | `kanban.css` `.kanban-page` + `.kanban-board` + `.kanban-col` height/flex chain. May need `index.html` shell adjustment if topbar height isn't a known constant. | 6–8 lines + verification |
| **T2.24e** Collapsible columns (A3, B4) | `kanban.css` (collapsed-column CSS), `kanban.js` (toggle + persist), `taskmaster_v3.py` `VIEWER_PREFS_DEFAULTS` (`kanban.collapsed_columns: []`). | ~40 lines |
| **T2.24f** Visual re-smoke | manual; user eyeball at 100% zoom (Signal at 150%) | n/a |

**Order:** b → c → d → a → e → f. Tokens first so the rest land on the new palette. Header compaction last so it doesn't interact with token shifts.

**Branch impact:** all on `feature/taskmaster-v3`; no schema/server changes except T2.24e prefs default.

**Tests to update:**
- T2.24e prefs schema: bump `VIEWER_PREFS_DEFAULTS` test snapshot if one exists in `tests/test_server_api.py`.
- No Playwright impact (those run in M7).

---

## D. What this means for the overall plan

- **Plan 2 size grows from 33 → 39 tasks** if we keep T2.24a–f as new line items. Alternative: bundle into ONE chore-style sub-task `T2.24-design-alignment` with internal checkboxes — cleaner reporting, same content.
- **M6 reorders:** T2.24 (smoke) → T2.24α (alignment pass, this doc) → T2.25 (density round-trip smoke) → T2.26–T2.28 visual smokes — alignment must land before the density-toggle smoke since toggling will look wrong on the old palette.
- **Hygiene sweep at end of Plan 2** absorbs leftover micro-nits from this pass (e.g. card-hover token rename, accent-blue cosmetic shift).

---

## E. Recommended next conversation move

Ask the user to confirm:
1. Bundle as one task `T2.24α — Signal alignment pass` vs split into 6? (Recommended: bundle.)
2. The 150%-zoom interpretation — port Signal sizes upscaled 1.5×, or 1:1 with the assumption the v3 viewer also runs at 150%? (Recommended: upscale.)
3. Column-collapse persistence in prefs (yes), or session-only (no)? (Recommended: persist.)

Once confirmed, dispatch a Sonnet implementer for the bundle + a combined spec/code review.

---

## F. Files captured for reference

- This doc → `docs/superpowers/plans/2026-04-27-plan2-design-feedback-signal-alignment.md`
- Updated handoff (Plan 2 M6) deferred until alignment lands.
