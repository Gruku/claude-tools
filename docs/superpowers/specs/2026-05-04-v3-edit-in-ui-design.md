# V3 Edit-in-UI — Design

**Status:** approved 2026-05-04
**Epic:** `v3-edit` (to be created)
**Authors:** brainstormed with @gruku 2026-05-04
**Depends on:** `v3-polish-029` (flat tasks API), `v3-polish-030` (task-detail loader), `v3-polish-033` (auto-stamp started/completed). The first two are patched on `feature/taskmaster-v3` but not committed; the third is the precondition for inline status edits.

## Motivation

The v3 viewer is read-only today. The `+ Task` button on kanban/table goes to `#/task/new`, which 404s. The `✎ Edit` button on Task Detail is rendered disabled with `title="Edit task — coming soon"`. All entity creation and editing currently flows through MCP tools and skill conversations.

The goal: make the v3 viewer a full editing surface for every entity in the v3 data model — tasks, issues, lessons, handovers, epics, phases. This is what "V3 from the ground up" implies: the viewer is co-equal with the skill/MCP authoring path, not a passive display.

## Locked decisions (from brainstorming)

| # | Decision | Rationale |
|---|---|---|
| 1 | **Scope:** all six v3 entities — tasks, issues, lessons, handovers, epics, phases | "V3 from ground up" — set the right scope from the beginning |
| 2 | **Architecture:** hybrid — shared shell + shared field components, per-entity composition files | Matches existing v3 viewer patterns (shared `right-rail.js`, `card.js`, `tmAction`); avoids both the schema-config sprawl and the per-entity rework cost |
| 3 | **Edit model:** inline click-to-edit per field on detail screens (autosave) + Modal for create + bulk-edit (explicit Save) | User direction; preserves context for fine edits, gives a focused space for creation |
| 4 | **Affordance:** visibly editable — dotted underline at all times + hover pencil ✎ | Avoids the "is this clickable?" question without screaming |
| 5 | **Relation pickers:** chip-input with autocomplete everywhere, plus one custom `AnchorEditor` for lesson glob anchors with live match-count feedback | Single mental model; only the genuinely-different case (globs) gets bespoke treatment |
| 6 | **Save UX:** autosave per field for inline edits, explicit Save button for modal flows | Matches the cognitive split — inline = small surgical change; modal = composing a coherent set |
| 7 | **Modal opening pattern:** centered overlay (NOT side drawer, NOT full-page route). The existing `#/task/new` route is removed | Preserves kanban/list context during creation; modal is what "modal" implies |

## Architecture

### Component layout

```
viewer/js/components/edit/
├── entity-modal.js          # overlay shell, dirty/save/error UX, Esc/backdrop, focus trap
├── inline-field.js          # read↔edit swap, autosave debounce, lifecycle (Enter/blur saves, Esc reverts)
├── conflict-banner.js       # surfaces 409 conflicts, "Show diff" component, per-field reload-vs-keep
├── fields/
│   ├── text-field.js
│   ├── md-field.js          # textarea + minimal toolbar; Cmd/Ctrl+Enter saves
│   ├── enum-select.js
│   ├── number-field.js
│   ├── date-field.js
│   ├── chip-input.js        # autocomplete chip pattern; source can be tasks/epics/phases/docs/free-text
│   └── anchor-editor.js     # bespoke; glob chips with live "matches N tasks" feedback
└── forms/
    ├── task-form.js         # exports { schema, layout(entity, mode) }
    ├── issue-form.js
    ├── lesson-form.js
    ├── handover-form.js
    ├── epic-form.js
    └── phase-form.js
```

### Shared shell vs per-entity composition

`entity-modal.js` and `inline-field.js` are entity-agnostic. They consume a `schema` object and a `layout(entity, mode)` function from a form composition file. The composition file is small (~100 lines) and declares which fields to render in what groups, plus the field renderer for each.

Schema is a plain JS object — no DSL, no JSON schema lib. Each field declares: type, required, validators, picker config, read-only conditions.

Detail screens (`task-detail-document.js`, `lesson-detail.js`, `issue-detail.js`) get a thin retrofit — they wrap their existing rendered fields with `inline-field.js`. New detail screens are added for `handover` only; epics and phases stay managed from the dashboard / phase stepper without a dedicated route.

### Modal entry points

- `+ Task`, `+ Issue`, `+ Lesson`, `+ Handover` buttons on the respective list screens open `entity-modal.js` in `mode: 'create'`.
- `✎ Edit` button on detail screens opens it in `mode: 'edit'`, prefilled.
- Epic and Phase modals open from the dashboard / phase stepper (no list screen for those).

## HTTP API & concurrency

### Endpoint shape — REST-ish, mirroring existing GET surface

| Operation | Verb + path |
|---|---|
| Create | `POST /api/{tasks\|issues\|lessons\|handovers\|epics\|phases}` |
| Full replace (modal save) | `PUT /api/{...}/{id}` |
| Partial update (inline autosave) | `PATCH /api/{...}/{id}` |
| Archive (soft delete) | `POST /api/{...}/{id}/archive` |
| Pre-save validate | `POST /api/{...}/validate` |

`PATCH` body is `{ field: value }` for one or a few fields — small wire payload, fast for autosave. `PUT` body is the full entity (modal Save).

### Single source of write logic

Write primitives live in `taskmaster_v3.py` (e.g. `update_task(id, patch)`, `create_issue(payload)`, `update_lesson(id, patch)`). Both the MCP tools and the HTTP handlers call into them. Already the pattern: `lesson_reinforce` lives in `taskmaster_v3.py` and is called from both `backlog_server.py` (HTTP) and the MCP tool wrapper.

This implies the long-tail v3-skills-XXX tasks (issue skill `v3-skills-004`, lesson skill `v3-skills-003`) coordinate with this epic — whoever lands the underlying primitive first, the other consumes. The skills become thin wrappers over the same functions the viewer uses.

### Concurrency — optimistic ETag

- Each entity GET response includes an `ETag` header derived from the file's `mtime` + `sha1` (cheap, stable).
- Each PATCH/PUT requires `If-Match: <etag>`.
- **Match → write proceeds.** Server returns the new entity + new ETag.
- **Mismatch → 409 Conflict.** Response body includes the current server version and the ETag. Client renders `conflict-banner.js`: *"Updated by claude (session a3f2) 12s ago. [Reload] [Show diff]"*. "Show diff" lets the user pick fields to keep individually before reloading the rest. No silent overwrites.
- **Per-file write lock** (server-side mutex). The existing `backlog.yaml` file lock generalizes — every entity file (`<root>/tasks/<id>.md`, `<root>/issues/<id>.md`, etc.) gets the same lock pattern via a `with file_lock(path):` helper.

### Identity tagging

The server is `localhost`-only; no auth needed. But each write records `last_modified_by` from `/api/identity` so the conflict banner can distinguish *"modified by claude (session abc)"* from *"modified by you in another tab"*. Useful when Claude and the user are simultaneously active on the same project.

### Validation — three layers

1. **Field renderer constraints** (client). E.g. `<TextField required maxLength=140>`. Inline visual feedback as user types.
2. **Schema rules** (client, before save). E.g. "depends_on must be an existing task ID", "anchors must be valid glob patterns". Driven by the same `schema` object that drives the form. Surfaces in the modal footer / inline-field error icon.
3. **Server validation** (authoritative). Wraps existing `backlog_validate` for cross-entity rules (no orphan dependencies, no cycles, epic/phase existence). Server can refuse a PATCH even if the client thought it was valid — never trust the client.

## UX patterns

### Inline edit affordance

Editable fields render with a 1px dotted underline (`var(--border-soft)`) at all times — a low-key signal that this is editable. On hover, the underline solidifies and a pencil ✎ icon fades in at the right edge. Click anywhere on the field enters edit mode.

Read-only fields (`id`, `created`, `last_referenced`, computed `auto_mode`, etc.) get NO underline and don't respond to hover/click — visually distinguishable.

### Inline edit lifecycle

| Event | Behavior |
|---|---|
| Click field | Swap renderer to edit-mode (input/textarea/select gets focus, value preselected for text) |
| Type | Debounced PATCH starts after 600ms idle. Pulsing dot ● beside the field while in flight; ✓ on success; ✕ + tooltip on error |
| Blur or Enter | Flush pending PATCH immediately, exit edit mode |
| Esc | Revert to last-saved value, exit edit mode without saving |
| Cmd/Ctrl+Enter (md fields) | Save and exit (Enter alone inserts newline) |

### Modal lifecycle

- Open → fade + scale-in (200ms), centered overlay, body scroll locked, focus first input.
- Fields are NOT autosaved inside the modal — they live in a local draft buffer.
- Save button enabled iff (dirty AND valid).
- Save → spinner state, PUT goes out, on success modal fades out and underlying screen refreshes the entity in place.
- Cancel/close while dirty → confirm dialog "Discard changes?" with Discard / Keep editing.

### Chip-input details (workhorse for relations)

- Existing relations render as chips with the relation's display id (e.g. `v3-polish-029`). Hover shows ✕ for removal.
- Input area shows placeholder *"add task…"* / *"add doc…"*. Typing opens dropdown of matches (max 8), arrow-keys highlight, Enter adds, Tab adds top match.
- Comma/space NOT used as separators — explicit Enter only. Avoids premature commits while typing.
- Task-id pickers: each dropdown row shows `id · title (status badge)`.
- Doc pickers: `type:` is pre-filled (e.g. `plan:`), URL/path is the chip's value.

### AnchorEditor (only bespoke field)

- Chips of glob patterns + a small "matches N tasks" line below each chip.
- Live recomputation as patterns change. Click `N tasks` to expand a popover listing matched tasks.
- Backed by a small `/api/anchors/match?pattern=...` endpoint that returns matching task IDs.

### Empty-state consistency

When a field has no value and isn't being edited, render the placeholder in `var(--ink-3)` italics — *"no notes yet"*, *"no dependencies"*. Click on the placeholder enters edit mode the same as a populated field.

## Per-entity field maps

Every editable field is editable in BOTH inline and modal — same field renderer, same schema. The split is just **editable** vs **system-managed (read-only)**.

| Entity | Editable | System-managed (read-only) |
|---|---|---|
| **Task** | title (text), status (enum), priority (enum), epic (enum from epics list), phase (enum from phases list), stage (number), estimate (text), sub_repo (text), branch (text), worktree (text), release (text), anchors (chip-input/glob), depends_on (chip-input/task-id), docs (chip-input/typed key:value), description (md), notes (md), specification (md), plan (md), review_instructions (md), patchnote (md) | id, created, started, completed, last_referenced, activity, spec_review, auto_mode, locked_by |
| **Issue** | title, severity (enum: critical/high/medium/low), status (enum: open/in-progress/closed), components (chip-input free-text), task_ids (chip-input/task-id), repro (md), notes (md) | id, created, closed (auto-stamped on status→closed) |
| **Lesson** | title, kind (enum), anchors (custom AnchorEditor), summary (text), body (md) | id, reinforcement_count, last_reinforced, created |
| **Handover** | kind (enum: mid-task/end-session/manual), task_ids (chip-input/task-id), body (md) | id, session, created |
| **Epic** | name, status (enum: active/planned/done/archived), description (md) | id, created |
| **Phase** | name, status (enum), order (number), started (date), completed (date), description (md) | id |

### Why these are system-managed

- `started`/`completed` on tasks: auto-stamped on status transitions (precondition: `v3-polish-033`).
- `last_referenced`: bumped on every read by the loader, not user-driven.
- `activity`: appended by session-end / spec-review / commit hooks.
- `spec_review`: written by the `spec-review` skill, displayed but not editable.
- `auto_mode`: written by the auto-mode runner.
- `locked_by`: written by `pick-task` (worktree owner).
- `reinforcement_count` / `last_reinforced` on lessons: written by `lesson_reinforce`.
- `closed` on issues: auto-stamped server-side when status transitions to `closed`.

### Field renderer dispatch

| Schema type | Renderer |
|---|---|
| `text` | `<TextField>` |
| `md` | `<MdField>` (textarea + minimal markdown toolbar; Cmd/Ctrl+Enter saves) |
| `enum` | `<EnumSelect>` |
| `number` | `<NumberField>` |
| `date` | `<DateField>` (ISO-8601 + small calendar popover) |
| `chip-input` | `<ChipInput source={...}>` where source resolves to `tasks` / `epics` / `phases` / `docs` (free) / `components` (free) |
| `glob-anchors` | `<AnchorEditor>` (only used by Lesson.anchors) |

### Validation rules — sample, to prove the schema covers the requirements

- **Task:** `title` required, ≤140 chars; `priority` ∈ {critical,high,medium,low}; `epic` must exist; `phase` must exist if set; `depends_on` items must exist and not include self / cycles (uses `backlog_validate`); `docs` keys are free strings, values look like URLs or repo paths.
- **Issue:** `severity` required; `task_ids` items must exist; `status=closed` auto-stamps `closed` server-side.
- **Lesson:** `anchors` non-empty; each pattern is a valid glob.
- **Handover:** `task_ids` items must exist.
- **Epic:** `name` required; status transition `active→done` warns (not blocks) if any child task is not done.
- **Phase:** `order` unique within project.

## Phasing & build order

One epic — `v3-edit` — broken into 3 phases. Each phase is independently shippable and demoable.

### Phase A — Foundation & Tasks

The smallest end-to-end vertical. Builds every shared primitive (modal shell, inline-field wrapper, all field renderers, chip-input, conflict banner) by using them for ONE entity — Task. Once Phase A ships, the remaining entities are mostly composition.

- `v3-edit-001` Field renderer primitives — TextField, MdField, EnumSelect, NumberField, DateField, ChipInput, RelationPicker. Schema definition format. Dev-only Storybook-style demo page wiring each renderer with sample data.
- `v3-edit-002` `entity-modal.js` shell — open/close, dirty tracking, Cancel/Save, error toast, focus trap, Esc/backdrop handling.
- `v3-edit-003` `inline-field.js` wrapper — read↔edit swap, autosave debounce, in-flight indicator, blur/Enter/Esc lifecycle.
- `v3-edit-004` HTTP write surface in `backlog_server.py` + write primitives in `taskmaster_v3.py` (task slice only). PATCH/PUT/POST/POST-archive for tasks. Wraps existing MCP write logic so MCP and HTTP share the same code path.
- `v3-edit-005` ETag/If-Match concurrency layer — server emits ETag headers on entity GETs and validates `If-Match` on PATCH/PUT. Conflict response shape. Per-file write lock helper.
- `v3-edit-006` Conflict banner + Show-diff component — surfaces 409 responses; per-field reload-vs-keep choices.
- `v3-edit-007` Task form composition + Task Modal create + Task Modal full-edit. Wire `+ Task` button on kanban/table. Replace disabled `✎ Edit` button on Task Detail.
- `v3-edit-008` Inline-edit retrofit on `task-detail-document.js`. Editable fields gain dotted underline, hover pencil, click-to-edit. (Folds in `v3-polish-033` — auto-stamping `started`/`completed` on status transitions.)
- `v3-edit-009` Validation pipeline — client-side schema validation + server-side `backlog_validate` integration (cycle detection, orphan dep checks, epic/phase existence).

End of Phase A: Tasks are fully createable, editable inline, editable in modal, with conflict handling.

### Phase B — Issues + Lessons (parallelizable)

- `v3-edit-010` Issue write primitives in `taskmaster_v3.py` + HTTP endpoints. Coordinates with `v3-skills-004` (issue skill).
- `v3-edit-011` Issue form composition + `+ Issue` modal + `issue-detail.js` inline retrofit. Auto-stamp `closed` on status→closed.
- `v3-edit-012` `AnchorEditor` custom field — chip-input variant with live "matches N tasks" feedback. Backs `/api/anchors/match`.
- `v3-edit-013` Lesson write primitives + HTTP endpoints. Coordinates with `v3-skills-003` (lesson skill, currently in-review).
- `v3-edit-014` Lesson form composition + `+ Lesson` modal + `lesson-detail.js` inline retrofit. Uses `AnchorEditor`.

### Phase C — Remaining entities + polish

- `v3-edit-015` Handover write primitives + HTTP endpoints (coordinates with `v3-skills-002`, currently in-review).
- `v3-edit-016` Handover form + `handover-detail.js` (new screen) + creation modal entry from session-detail / task-detail.
- `v3-edit-017` Epic and Phase forms + creation/edit modals. (No new detail screens — managed from dashboard / phase stepper.)
- `v3-edit-018` Accessibility & keyboard audit — focus management in modal, ARIA labels for inline-field state, screen-reader announcements for autosave/error.
- `v3-edit-019` E2E test sweep — Playwright tests for create-task, inline-edit, modal-edit, conflict handling, validation rejections.

### Dependencies summary

- Phase A is sequential within itself.
- Phase B is parallelizable across the issue and lesson tracks.
- Phase C is mostly leaf work.
- Whole epic depends on `v3-polish-029` and `v3-polish-030` being committed (already patched on this branch).
- `v3-edit-008` depends on `v3-polish-033`.
- Underlying-primitive tasks (`v3-edit-010`, `v3-edit-013`, `v3-edit-015`) coordinate with the respective entity-skill tasks (`v3-skills-004`, `v3-skills-003`, `v3-skills-002`) to share write code.

## Out of scope (explicit)

To prevent scope creep:

- **Bulk operations** (multi-select on kanban → batch edit). Could be a follow-up epic.
- **Comments / discussion threads** on entities.
- **File-attachment uploads.**
- **Undo/redo** across the session — rely on conflict-banner + git history.
- **Permissions / roles** — localhost-only, no auth model.
- **Real-time collaboration** (live cursors, presence). The 409-banner pattern handles the multi-actor case acceptably.
- **Custom field definitions** (user-defined schema). The schema is hardcoded in form composition files.

## Risks & open questions

- **Concurrency under heavy Claude activity.** If a Claude session is rapidly writing to a task file (e.g. during an auto-mode run), the user may see frequent 409 banners. Mitigation: the conflict banner's "Show diff" lets the user merge field-by-field rather than blanket-reload; auto-mode writes are typically in narrow fields (status, activity) that the user is unlikely to be editing simultaneously.
- **Schema drift.** Six entity types × ~10-15 fields each = surface area for type/validator definitions to diverge. Mitigation: forms compose from shared field renderers, and validation is centralized in the schema. Server-side `backlog_validate` is the authoritative gate.
- **AnchorEditor cost.** Live "matches N tasks" feedback means the `/api/anchors/match` endpoint runs on every keystroke (debounced). For 50-100 task projects this is trivial; for very large backlogs may need server-side caching. Defer optimization.
- **Md-field editor depth.** The minimal toolbar covers basic markdown but not, e.g., embedded images, tables. If users want richer authoring, scope creep. Hold the line: textarea + simple toolbar.

## Acceptance criteria (for the epic as a whole)

- All six entity types can be created from the v3 viewer via a centered overlay modal with explicit Save.
- All editable fields on detail screens (`task`, `issue`, `lesson`, `handover` once that screen exists) support click-to-edit with autosave.
- Editable fields are visually distinguishable from read-only fields.
- Concurrent writes from MCP/Claude and the viewer surface a conflict banner with field-level diff resolution; no silent data loss.
- Server-side validation catches every constraint listed in §"Validation rules"; client UX prevents most invalid states from being saveable.
- A11y: tab-navigable through all fields; modal focus-trapped; screen reader announces save/error state.
- Existing `+ Task` button works (today it 404s); existing `✎ Edit` button works (today it's disabled).
