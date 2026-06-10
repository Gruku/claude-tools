# Interactive HTML Diagrams + the Epic Architecture Map — Design

**Date:** 2026-06-02
**Status:** approved (brainstorm), pending implementation plan
**Supersedes:** the SVG-rendering approach of Pillar C2 in `2026-05-27-task-epic-protocol-design.md` (§205–207, §224–230). The C2 *intent* (a live, generated, status-colored diagram on the epic detail screen, driven by the `components` block + `component_rollup`) is unchanged; the *rendering medium and scope* are revised here.
**Builds on (kept as-is):** `docs/superpowers/plans/2026-06-01-c2-live-component-diagram.md` Task 1 — the pure layout engine `component-graph-layout.js` (`computeComponentLayout`), already implemented and committed (`1440119`). Its DAG-ranking logic is reused; see "Layout engine reuse" below.

---

## 1. The principle (general — applies beyond C2)

> **Taskmaster viewer diagrams are authored as data-driven, interactive HTML pages.**
> A diagram is a composed DOM — divs, text, badges, reused card components, with SVG or CSS connectors as needed — styled with the viewer's CSS tokens, laid out by a pure data engine, **bound to live backlog data**, and navigable by click / hover / keyboard. Use whichever primitive renders cleanest (HTML, CSS, or SVG); the constraint is that the structure is **authored, interactive, data-bound HTML**, never an opaque static image or a hand-drawn SVG that authors content.

**Why:** HTML structure is far more reliably LLM-authored than SVG coordinate math; it is accessible, keyboard-navigable, trivially interactive, and binds directly to live data. SVG remains welcome as a *drawing primitive* (e.g. curved connectors) layered behind or within the HTML — it just never becomes the authoring surface for the meaningful content.

**Scope of the principle:** it governs **new** diagram surfaces and guides future refactors of the existing SVG graphs (`dependency-graph.js`, `task-detail-graph.js`). Those two are **not** refactored as part of this work — out of scope. This design is the principle's first concrete instance.

---

## 2. What we are building: the Epic Architecture Map

A new surface on the epic detail screen that is simultaneously:

- **architecture documentation** — the epic's components laid out in dependency order (the `after` DAG), the blocks carrying the visual weight; and
- **a live progress tracker** — each component block holds the actual tasks linked to it, rendered as compact cards colored by status, so you see real work and stay oriented on what is in flight, blocked, or done.

It **replaces** the existing plain component-list section on the epic detail screen (today's `compSec`, the `.ed-comp` blocks). It does **not** duplicate the kanban: tasks here are shown in **compact** form only (basic info), and the kanban remains the place for full task detail and full-board work. The map earns its place by being the *architectural lens* on the epic that the kanban and the flat list cannot give.

### Anatomy

```
Architecture
┌─ Ingest ──────────┐      ┌─ Thumbnailer ─────┐      ┌─ CDN delivery ────┐
│ ING-1 · High      │─────▶│ THM-1 · Med  ◐    │─────▶│ CDN-1 · Low   ○   │
│ done           ●  │  ╲   │ THM-2 · Low  ○    │      │ (no tasks yet)    │
│ ING-2 · Med    ●  │   ╲─▶│ THM-3 · High ⚠    │      └───────────────────┘
└───────────────────┘      └───────────────────┘
  done                       in-progress · 1 blocked     todo
```

- **Blocks** = components, placed left→right by dependency rank (rank 0 = no `after`). The block is the dominant visual element. Block chrome is status-tinted (full-perimeter border; "attention"/blocked emphasis is a **top** border, never a left rail; no hover motion; no box-shadow — surface stepping only). Each block header shows the component title and a one-line rollup summary (e.g. `done` / `in-progress · 1 blocked` / `todo`).
- **Tasks inside a block** = the tasks whose `component` field equals that block's key (via the existing `tasksForComponent(epic.tasks, key)` helper), rendered with the **existing compact card** `renderMinimalCard(task, opts)` from `js/components/card.js`. Compact card shows id · priority · size · time-in-status + title (+ status pill). Clicking a card opens task detail — already wired inside `renderCard`. No new task-rendering code.
- **`_unassigned`** tasks render in a visually-distinct trailing block (dashed border) only when present.
- **Empty component** (declared but no tasks yet) renders a stub block ("no tasks yet") so the architecture is visible before work is filed, and fills in as tasks are added.
- **Connectors** between blocks express the `after` dependency edges. Rendered with whatever reads cleanest (SVG curve overlay recommended for fidelity; CSS acceptable). Connectors are neutral, non-interactive, never status-colored.

### Interactions (v1)

| Trigger | Behavior | Mechanism |
|---|---|---|
| Click a **task card** | Open that task's detail (modal or full per `ui.detail_view_mode`) | Already wired inside `renderCard` (`open-detail.js`) — free |
| Click a **block header** | Navigate to the kanban filtered to that component: `#/kanban?component=<key>` | **New** kanban filter param (see §4) |
| **Live** data change | Diagram re-renders so task statuses recolor and newly-added tasks appear | Epic screen subscribes to the existing 3s backlog poll; re-fetch epic → re-render |
| Keyboard | Block headers and task cards are focusable/activatable | `tabindex` + Enter/Space on the block header; cards already focusable via existing card behavior |

**Explicitly NOT in v1** (YAGNI — kanban covers it, or deferred): a separate hover "rollup breakdown" popover (the tasks are visible inline, so it is redundant); collapsible ranks; a per-session "you are here" spotlight beyond the natural in-progress/blocked coloring; click-to-navigate to any per-component route other than the kanban filter.

---

## 3. Architecture & components

| Unit | Responsibility | Change |
|---|---|---|
| `js/components/component-graph-layout.js` | Pure DAG → dependency ranks/columns (no DOM). `computeComponentLayout`. | **Exists** (Task 1). Reused; see below. May expose rank-grouping more directly if the renderer needs it. |
| `js/components/component-diagram.js` | Mount the HTML architecture map: build blocks, place by rank-column, fill each with `renderMinimalCard`s, draw connectors, return cleanup fn. | **Create** (was the all-SVG module; now HTML-first). |
| `js/components/epic-detail-document.js` | Epic detail render. | Replace the `compSec` plain component list with the mounted map at the `.ed-diagram` point; subscribe to the backlog poll for live re-render. |
| `js/screens/kanban.js` (+ filter module / `router.js`) | Kanban filters. | **New** `component` filter param: parse `?component=`, add to `DEFAULT_FILTERS`, honor in `applyFilters`, deep-linkable. |
| `css/screens/epic-detail.css` | Epic screen styles. | Add `.ed-diagram` + map/block/connector classes (tinted fills, full borders, top-border attention, no left rails / shadows / hover motion). |
| Tests (unit + e2e) | Cover layout, render, mapping, kanban filter, live re-render, graceful degradation. | **Create / extend**. |

### Layout engine reuse (honest accounting)

`computeComponentLayout` already computes, per component: longest-path **rank** (dependency depth, with a cycle guard) and grouping by rank, plus fixed-size pixel coordinates + cubic-bezier edge path strings (sized for 132×56 SVG nodes).

- **Reused as-is:** the rank computation and rank-grouping — this is *which dependency column each block belongs to and the order within it*. This is the load-bearing, well-tested part.
- **Superseded / optional:** the fixed 132×56 pixel coordinates and bezier strings assumed uniform small nodes. The architecture map's blocks are **variable height** (they contain task cards), so the renderer lays blocks out in **dependency-ordered columns** (CSS) and computes connector geometry from the **rendered block rectangles** (`getBoundingClientRect`), reusing the same bezier formula for the curve. Whether to keep or trim the engine's pixel-coordinate output is a plan-level decision; the rank logic and its tests stay.

### Data flow

```
/api/epic/:id  ──▶  epic { components, component_rollup, tasks[ {id,title,status,component,priority,...} ] }
                         │
       computeComponentLayout(components, rollup) ──▶ ranks/columns
                         │
   mountComponentDiagram(container, { components, rollup, tasks, onNavigate })
                         │
        per component column → block (status from rollup[key].status)
                         │
        tasksForComponent(tasks, key) → renderMinimalCard(task) per task
                         │
   connectors drawn between block rects for each `after` edge
                         │
   epic screen subscribes store('backlog') (3s poll) → re-fetch epic → re-mount map
```

No server, MCP, or schema change for the map itself. The only backend-adjacent change is **none** — the kanban `component` filter is pure front-end (URL param + client-side filter over already-fetched tasks).

---

## 4. The kanban `component` filter

Block-header click targets `#/kanban?component=<key>`. Today the kanban supports `epic`, `phase`, `priority`, `search`, `group_by` but **not** `component`. Add it as a first-class, deep-linkable filter:

- `parseHash` already extracts arbitrary `?k=v` params; add `component` to the kanban's `DEFAULT_FILTERS` and to `applyFilters` (a task matches iff `task.component === filters.component`, when set).
- Surface it minimally in the kanban filter UI (a clearable chip/indicator showing the active component filter) so the user can see and dismiss it — consistent with how `epic`/`phase` filters already surface. Full filter-UI parity is not required for v1; deep-link + a clearable indicator is the bar.

---

## 5. Error handling & graceful degradation

- **No components declared** → render nothing (no empty "Architecture" section).
- **Empty `component_rollup`** (freshly declared epic, zero tasks) → all blocks render neutral/`todo`, no throw.
- **Coarse vs rich coloring** → the map operates on the C1 task-status rollup today; richer gate/merge signals are an additive future change, not a render-path change. No "coarse mode" banner.
- **Cycles** in `after` → handled by the layout engine's existing cycle guard (finite ranks, all blocks placed).
- **`after` references an unknown key** → ignored defensively (validator should prevent; never crash).
- **Live re-render** failure (epic re-fetch errors) → keep the last good render; do not blank the surface.

---

## 6. Testing strategy

- **Unit (`node --test`, jsdom):**
  - layout engine — already covered (Task 1, 8 tests).
  - `component-diagram.js` mount — blocks per component, correct rank/column placement, each block contains the right `renderMinimalCard`s (assert by `data-task-id`), status classes from rollup, `_unassigned` block, empty-component stub, cleanup empties the container, no `box-shadow` / `border-left` / `transform` in produced markup, empty-components → no mount.
  - node-state → visual-state mapping — exhaustive pinned contract (`nodeVisualState`).
- **Unit (kanban):** `applyFilters` honors `component`; `parseHash` round-trips `?component=`.
- **E2E (Playwright):** open an epic with components → map renders above/instead-of the plain list; block-header click lands on kanban filtered to that component; a task card click opens detail; (where feasible) a simulated backlog change re-colors a block (live). Graceful: epic with components but no tasks renders neutral stubs.

---

## 7. Revised task breakdown (supersedes the 6-task C2 plan)

| # | Task | State |
|---|---|---|
| 1 | Pure layout engine (`computeComponentLayout`) | ✅ done (`1440119`) — rank logic reused |
| 2 | HTML architecture-map mount (`component-diagram.js`): rank-column blocks + reused `renderMinimalCard` task cards + connectors | rewritten (HTML-first) |
| 3 | Node-state → visual-state mapping, tested contract | unchanged |
| 4 | Kanban `?component=X` filter (parse + `DEFAULT_FILTERS` + `applyFilters` + clearable indicator) | new |
| 5 | Block-header click → kanban-filter navigation + keyboard activation | new |
| 6 | Wire map into epic detail screen (replace `compSec`) + CSS | revised |
| 7 | Live re-render: epic screen subscribes to backlog poll, re-fetches + re-mounts map | new |
| 8 | E2E + graceful degradation (render, navigation, live, coarse/empty) | expanded |
| 9 | Version bump 3.13.0 → 3.14.0 (3-part protocol + check script) | unchanged |

---

## 8. Out of scope

- Refactoring the existing SVG graphs (`dependency-graph.js`, `task-detail-graph.js`) to the HTML principle.
- Phase-level architecture maps (epics-only for v1).
- Full task detail inside the map (kanban / task detail owns that).
- Server / MCP / schema changes (`components`, `component`, `component_rollup` already ship from C1).
- A hover rollup popover, collapsible ranks, per-session focus spotlight (deliberately dropped — see §2).
