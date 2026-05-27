# Task & Epic Protocol — Enforced Pipeline, Merge Ladder, and Living Epics

**Date:** 2026-05-27
**Status:** Approved (design, rev 2 — post spec-review) — decomposes into implementation specs; build order **C → A → B**
**Related specs:**
- [2026-05-21 Review-Gate-Before-Merge](2026-05-21-review-gate-before-merge-design.md) — becomes Spec B (merge ladder); its unbuilt `merge_targets` manifest field is implemented here
- [2026-05-15 Progressive Disclosure](2026-05-15-taskmaster-progressive-disclosure-design.md) — slim/heavy two-tier storage, `tldr` glance pattern, typed links
- [2026-05-19 Project Structure Visibility](2026-05-19-project-structure-visibility-design.md) — `project.yaml` manifest
**Depends on:** `project.yaml` manifest for the merge ladder (Spec B only)

> **Rev 2 changelog (spec-review fixes):** lane is now an **explicit field with a default**, not inferred from a nonexistent `kind` (C1). Merge rungs come from a **new `merge_targets` manifest field**, not `ship_order` — which is unrelated monorepo repo-ordering (C2). The epic **components block is the single source of truth** and the diagram is *generated* from it and rendered by the existing SVG graph engine — no Mermaid, no node-id coupling (C3). Added an explicit **rollout / backward-compat** rule so enforcement never retroactively blocks in-flight tasks (C4). Added **Target modules**, **Enforcement philosophy**, and rollout sections; Spec C split into C1/C2 for YAGNI.

---

## Background

Taskmaster tracks task progress with a single coarse field — `status` ∈ {todo, in-progress, in-review, done, archived, blocked} (`backlog_server.py:5077`). That is the only progress signal, and it has three problems:

1. **No enforced per-task rigor.** A rich pipeline exists *only* in auto-mode, and even there the ordering is enforced by the skill following steps, not the data layer — `backlog_auto_advance` will set any stage. Manual work has no pipeline. `spec_review` is recorded but advisory; nothing blocks picking or completing a task whose spec review failed. `update_task(field="status")` accepts `todo → done` directly (the only real guard, added in `14520c7`, lives in `complete_task` at `backlog_server.py:4785`).

2. **No git-landing visibility.** A task carries `branch` and `worktree` strings and nothing else. Nothing records whether the branch merged, into which environment, or how far up a promotion ladder it travelled. The user distinguishes "merged into stage" from "merged into a branch" — they think in terms of a *ladder*, and the model can't express it.

3. **Epics are invisible at the level that matters.** Epics are metadata-only in `backlog.yaml` with a `docs` path-pointer dict but **no body file**; phases can't even hold `docs`. There is nowhere for a design narrative or architecture diagram to live. The user gets lost in large epics (the CodeMaestro **Asset Engine** is the canonical case): no full picture, no sense of how locked the design is, no rollup of where work stands.

The bar: **make the pipeline real and enforced for both manual and autonomous work, give tasks a promotion ladder, and turn epics into a living command center where completing a task visibly advances the architecture diagram.**

## Core model: status splits into two layers

`status` stays the **coarse, human-facing** lifecycle. Underneath lives a **fine-grained, enforced pipeline** of gates:

```
status:   todo ──pick──▶ in-progress ───────────────────────▶ in-review ──user──▶ done
                          └ pipeline (lane-determined):                  │
                            spec→spec-review→plan→plan-review            │
                                 →tests→impl→review-gate ────────────────┘
                                                          merge ladder continues AFTER done
                                                          done✓ · develop✓ · stage✓ · master○
```

- `in-review` is reached when the **review-gate** verdict is `pass` (Claude is done; the user verifies).
- `done` is the user's confirmation. **Enforced:** a task with a lane cannot reach `done` unless every *required* gate for its lane is `pass` or explicitly `skipped`.
- The **merge ladder** tracks landing and continues *after* `done`: a task can be `done` and merged to `stage` but not yet `master`. "Shipped" = reached the terminal ladder rung.

One pipeline, one source of truth — so manual work and auto-mode walk identical gates. Auto-mode stops being a parallel ladder and becomes the agent that walks this pipeline (see "Auto-mode convergence").

## Goals

- Per-task pipeline of gates, **tiered by lane**, with required gates **enforced by the MCP layer** and a **recorded-override** escape hatch (`skip_gate`), surfaced loudly on the dashboard.
- Generalize the advisory `spec_review` record into a uniform **per-gate record** covering spec-review, plan-review, review-gate.
- **Close** the `update_task(status=…)` escape hatch via a full forward-transition table; `skip_gate` becomes the only bypass past a gate.
- A **merge ladder** per task, rungs ordered by a new `merge_targets` manifest field, each stamped with merge commit + timestamp; auto-recorded by a hook, manually stampable.
- **Epics and Phases become first-class, doc-bearing entities** with their own body file, mirroring task two-tier storage.
- **Live components:** the epic's `components` block is the single source of truth for "what we're building"; each task binds to a component; the diagram is *generated* from components and auto-colors by rollup, so completing a task visibly advances the picture.
- **Design-maturity lock** on epics (`exploring → proposed → locked → revising`) with light teeth via an explicit `design-change` task flag.
- **Derived rollups + risk surface** on epics, computed on read.

## Non-goals

- Replacing the `taskmaster:review-gate` / `taskmaster:spec-review` skills. This adds a *recording* + *enforcement* layer; the skills still do the reviewing.
- Re-running gates from hooks. The merge-gate hook checks for a recorded pass; it does not invoke a skill.
- PR-level / remote-branch gating. The merge ladder is local-`git merge` only.
- Retroactive enforcement on tasks created before the protocol (see Rollout).
- Configurable per-knob pipelines beyond the three lanes (opinionated default; `skip_gate` covers exceptions).

---

## Target modules

| Module | Role | Changes |
|---|---|---|
| `backlog_server.py` | live FastMCP server: tool decorators, `VALID_STATUSES`/`ALLOWED_FIELDS`, transition guards (`complete_task`), `set_spec_review`, epic/phase add/update | new gate/lane/merge tools; extended guards; epic/phase doc fields |
| `taskmaster_v3.py` | framework-free storage library (imported by the server): `SLIM_FIELDS`/`HEAVY_FIELDS`, `resolve_sections`, `.md` read/write, `load_v3`/`save_v3` | extend slim/heavy split + `.md` files to **epics & phases**; new task fields (`lane`, `gates`, `component`, `merge_status`) |
| `project.py` | `project.yaml` manifest schema + loader | new `meta.policies.merge_targets` (ordered env→branches); component-render reads nothing here |
| `viewer/` | vanilla ES-module local UI (no build step; `marked@12` + bespoke SVG graph in `dependency-graph.js`) | new epic screen; extend SVG graph engine to render the component diagram with status coloring; gate + merge-ladder badges |
| `hooks/` | plugin hooks | `merge-gate.sh` (PreToolUse), `merge-recorder.sh` (PostToolUse) — Spec B |
| skills | `pick-task`, `auto-task`, `spec-review`, `review-gate`, new `plan-review` | record gates via the generalized tool; lane-aware auto-mode |

**Note (I1):** guards/validation live in `backlog_server.py`; storage primitives in `taskmaster_v3.py`. Every gate/lane/epic-storage change touches **both**.

---

## Pillar 1 — Lanes & enforced gates (Spec A)

### Lane (explicit field, sane default)

`lane` is a new **explicit** task field — *not* inferred from `kind` (which does not exist in the data model). Default and override:

- Default on creation: **`standard`**.
- Auto-bumped to **`full`** when `priority` ∈ {`critical`, `high`} (high-stakes work earns full ceremony). These are the canonical `VALID_PRIORITIES` (`backlog_server.py:5078`), and `priority in ("critical","high")` is already used as the high-stakes grouping at `backlog_server.py:6231`.
- **`express`** is opt-in: set explicitly for chores/docs/hotfixes.
- Override any time: `backlog_update_task(id, "lane", "full|standard|express")`.

| Lane | Required pipeline |
|---|---|
| **full** | spec → spec-review → plan → plan-review → tests → impl → review-gate → merge |
| **standard** | spec(+plan merged) → design-review → tests → impl → review-gate → merge |
| **express** | impl → review-gate → merge |

The lane → required-gate-set mapping is an opinionated default in the loader. Per-project tuning (`meta.policies.lanes`) is deferred (YAGNI).

### Gate record

Today's `spec_review` dict generalizes into a uniform per-gate record under a `gates` map on the task:

```yaml
gates:
  spec:        { status: done, at: … }
  plan:        { status: done, at: … }
  tests:       { status: done, at: …, commit_sha: aaa111 }
  impl:        { status: done, at: … }
  spec-review:  { verdict: pass, at: …, codex_used: true, critical_count: 0, important_count: 1, doc: specs/… }
  plan-review:  { verdict: pass, at: …, critical_count: 0, important_count: 0 }
  review-gate:  { verdict: pass, at: …, commit_sha: bbb222, critical_count: 0 }
  # a skipped gate carries the override paper trail:
  # plan-review: { skipped: true, reason: "trivial config change", at: …, by: claude|user }
```

`verdict` ∈ {pass, warn, fail}; `status` ∈ {pending, done}. Storage: a compact glance mirror in the slim tier (`lane`, a one-line `gate_state` like `"review-gate:pass"` / `"blocked@plan-review"`); the full `gates` map in the heavy tier (`tasks/<id>.md` frontmatter). Exact slim-mirror fields pinned in the Spec A plan.

### Enforcement philosophy (I3 — stated, not accidental)

Two deliberately different stances:

- **Gates (Pillar 1): fail-closed.** The MCP layer *rejects* illegal moves; the only bypass is `skip_gate(reason)`, which always succeeds and is flagged red on the dashboard. Rationale: gate enforcement is the user's explicit ask, and a recorded override is the pressure-release valve — so being "blocked" is always escapable in one call with a paper trail.
- **Merge hook (Pillar 2a): fail-open.** Inherited unchanged from the 2026-05-21 spec ("a buggy hook must never block legitimate work"). Rationale: a hook runs on every `git merge` and a bug there must never wedge the user out of git; the worst case is a missing audit stamp, not a blocked merge.

### Enforcement rules (MCP / data layer)

Guards extend the existing `14520c7` lifecycle guard in `backlog_server.py`:

1. **`complete_task` (→ done):** already rejects `todo → done`. Extend: for a task **with a lane**, require every required gate to be `pass`/`done`/`skipped`; else reject with the outstanding-gate list. **Laneless tasks are exempt** (see Rollout).
2. **`update_task(field="status")` — full transition table (I2).** Legal *forward* moves (`todo→in-progress→in-review→done`) pass the same checks as their dedicated tools; arbitrary jumps/regressions are rejected. Internal callers that set `in-progress` via `update_task` (pick-task; auto-task Step 1) keep working because that forward move stays legal.
3. **Out-of-order gate recording rejected:** recording a gate pass/done is rejected if an earlier required gate is neither pass nor skipped.
4. **`skip_gate(task_id, gate, reason)` — sole recorded override.** Writes `{skipped, reason, by, at}`; always succeeds; flagged red. No silent skips anywhere.

New / changed MCP surface (names indicative):
- `backlog_record_gate(task_id, gate, verdict|status, **meta)` — generalizes `backlog_set_spec_review` (kept as a thin alias). Enforces rule 3.
- `backlog_skip_gate`, `backlog_clear_gate` (generalizes `backlog_clear_spec_review`), `backlog_task_pipeline` (read).
- Extended guards in `complete_task` / `update_task` (rules 1, 2).

### Auto-mode convergence

The auto state machine (`AUTO_STAGES`) becomes **lane-aware**: it walks exactly the required gates for the task's lane (full adds PLAN + PLAN_REVIEW; express skips SPEC/PLAN), and each `backlog_auto_advance` records the corresponding gate via `backlog_record_gate` — so the auto cursor and the enforced pipeline are one object, not two ladders. Manual = the human walks the gates; auto = the agent walks them; identical enforcement. A small one-time migration updates any in-flight auto-cursor to the lane-aware shape (Minor).

---

## Pillar 2a — Merge ladder (Spec B)

The [2026-05-21 Review-Gate-Before-Merge](2026-05-21-review-gate-before-merge-design.md) design, with two corrections from spec-review:

1. **Rungs come from a NEW `merge_targets` manifest field — not `ship_order` (C2).** Verified: `ship_order()` (`project.py:206`) is a topological sort of *sub-repos by `depends_on`* (monorepo deploy order) and is unrelated to branch promotion. The branch-promotion ladder needs its own field. Implement the 2026-05-21 spec's `meta.policies.merge_targets`, but as an **ordered list** so it renders as a ladder:

```yaml
meta:
  policies:
    review_gate_required_for_merge: false   # opt-in
    merge_targets:                           # ordered rungs; defaults applied if absent
      - { label: develop, branches: [develop, dev] }
      - { label: stage,   branches: [stage, staging] }
      - { label: master,  branches: [master, main] }
```
A single-`master` repo gets a one-rung ladder. `Policies` (`project.py:144`) gains this key.

2. **Key off the generalized gate (C-of-Pillar1).** The merge-gate hook reads `gates["review-gate"].verdict`, not a standalone `review_gate` block. `merge_status` frontmatter shape unchanged:

```yaml
merge_status:
  develop: { merged_at: …, merge_commit: a1b2c3d }
  stage:   { merged_at: …, merge_commit: e4f5g6h }
  master:  null
skip_merge_gate: false
merge_gate_freshness: strict   # strict | any
```

Mechanism (unchanged): **PreToolUse `merge-gate.sh`** blocks merging a task's branch into a rung unless `review-gate` = pass (and fresh); fail-open on uncertainty; one-shot Approve/Deny. **PostToolUse `merge-recorder.sh`** stamps the rung from the merge commit; `backlog_record_merge(id, rung, sha)` is the manual fallback. `backlog_record_review_gate` from the 2026-05-21 spec is subsumed by `backlog_record_gate(id, "review-gate", …)`. Phasing inherited: recording layer ships independently; hooks depend on `project.yaml`.

---

## Pillar 2b — Living Epics & Phases (Spec C, built first)

Built **first** because defining the epic picture reveals what tasks hook into (the `component` binding), which informs Spec A. Split into **C1 (ship first)** and **C2 (fast-follow)** per YAGNI (I6).

### C1 — Body files + rollup + lock + risk (the "I get lost" relief)

**Body files.** Epics and Phases get `epics/<id>.md` and `phases/<id>.md`, mirroring `tasks/<id>.md` two-tier storage (slim metadata in `backlog.yaml`; heavy design narrative + `docs` + `components` block in the `.md`). The `resolve_sections`/slim-heavy machinery in `taskmaster_v3.py` is extended from tasks to these two entity types. **Migration (I5):** a one-time pass seeds each existing epic/phase body from its current `description`/`docs`.

**Components block** — the single source of truth for "what we're building" (C3 — no hand-authored diagram, no Mermaid node-id coupling):

```yaml
# epics/asset-engine.md frontmatter
components:
  ingest: { title: "Ingest",      after: [] }
  thumb:  { title: "Thumbnailer", after: [ingest] }
  cdn:    { title: "CDN delivery", after: [thumb] }
design_status: locked
docs: { design: specs/asset-engine.md }
```

Each task carries a `component` field (`backlog_update_task(id, "component", "thumb")`). A component's status is the **rollup of its tasks**, computed **on read** (never cached — Minor). A task with no `component` rolls into an "unassigned" bucket shown separately.

**Design-maturity lock.** Epic slim field `design_status` ∈ {exploring, proposed, locked, revising}. Teeth via an **explicit `design-change` task flag (I4 — not doc-edit detection, which MCP can't intercept):** creating/marking a `design-change` task under a `locked` epic requires a recorded `backlog_decision` to reopen, which flips the epic to `revising`. Implementation tasks are unaffected.

**Rollup + risk surface** (derived, computed on read): status counts, gate-completion (`spec-review 5/7`), merge-ladder rollup (`develop 5 · stage 3 · master 3`), % to terminal rung; plus a single attention list bubbling up failed gates, blocked tasks, and open decisions. Exposed via `backlog_phase_status` / new `backlog_epic_status`. (Gate-completion is coarse until Spec A lands, then richens automatically.)

### C2 — Live generated diagram (fast-follow)

Generate the diagram **from the `components` block** (nodes = components, edges = `after`), and render by **extending the existing bespoke SVG graph engine** (`viewer/js/components/dependency-graph.js` + `task-detail-graph.js`) — which already emits raw SVG with native per-node styling and respects the no-left-rails / no-shadow rules. Nodes auto-color by component rollup, so completing a task lights up its node. **No Mermaid dependency** (verified absent; viewer has no build step). Single source of truth means no node-id drift — the failure mode the "components" choice was meant to avoid. Blocked/skipped-heavy components get a distinct "attention" fill (Minor — semantics pinned in the C2 plan).

---

## Rollout & backward-compat (C4)

Enforcement keys on **"the task has a `lane`."**

- **New tasks** get `lane` by default → enforced.
- **Existing tasks** (created before the protocol) have **no lane → fully exempt**; they complete exactly as today. No retroactive blocking.
- **Optional backfill migration:** sets `lane` on existing tasks *and* marks their already-passed required gates `skipped(reason="grandfathered")` so a just-migrated `in-progress`/`in-review` task is never retroactively wedged.
- Epic/phase body files are seeded by the I5 migration; tasks without a `component` are valid (unassigned bucket).

This guarantees shipping the protocol never blocks the user's own in-flight work — the foot-gun the first draft left armed.

---

## Viewer surface

- **Epic detail screen (new):** the generated component diagram (C2; status-colored via the extended SVG engine), component list, progress rollup, risk/attention list, `design_status` lock badge, design narrative/docs. C1 ships this screen with rollup + list; C2 adds the diagram.
- **Task detail:** gate pipeline tracker (pass/fail/skip badges; skips red) + merge ladder (rung dots ordered by `merge_targets`).
- **Kanban cards:** lane badge, `gate_state` one-liner, merge-rung dots.

Hard visual rules (`CLAUDE.md`): no colored left rails; no hover motion; no box-shadows (surface stepping). Node coloring uses tinted fills.

---

## Decomposition & sequencing

| Spec | Scope | Depends on |
|---|---|---|
| **C1 — Living epics (core)** | epic/phase body files + migration; `components` block + `component` task field; derived rollup + risk surface; `design_status` lock via `design-change` flag; viewer epic screen (no diagram yet) | — (rollup rides on coarse status initially) |
| **A — Gates foundation** | explicit `lane` field + default rule; generalized gate records; enforcement rules 1–4; `skip_gate`; rollout/grandfather logic; skill updates; auto-mode convergence + cursor migration | C1 (knows the `component` hook); reuses existing `spec_review` |
| **B — Merge ladder** | `merge_targets` manifest field; `merge_status`; recording layer + both hooks; keyed off `review-gate` gate | A (review-gate verdict), `project.yaml` |
| **C2 — Live diagram** | generate diagram from `components`; extend SVG graph engine; status coloring | C1, A (gate rollup for coloring richness) |

**Build order: C1 → A → B → C2.** Rationale: C1 defines the component shape A must hook; A delivers the enforced rigor; B adds merge tracking; C2 is the visual payoff once the data underneath is real.

**Blast-radius note (Gate D, loud):** this work re-touches `complete_task`/guard code just rewritten on `fix/bughunt-2026-05-26` (commits `14520c7`, `d74dbcf`) with uncommitted `.taskmaster` changes still in the tree. **Land the bughunt branch first, then branch the protocol off a clean base.**

## Testing approach

- **C1:** epic/phase body-file round-trip (slim/heavy, atomic write, `sort_keys=False`); migration seeds bodies; component-rollup from task fixtures; rollup/risk derivation on read; `design_status` lock → decision-required path; viewer unit tests.
- **A:** lane default + critical/high bump + override; gate-record round-trip; each enforcement rule (gate-completeness on done, forward-transition table, out-of-order rejection, `skip_gate` override); **laneless-task exemption + grandfather migration**; auto-mode lane-aware advance recording the right gates.
- **B:** inherits the 2026-05-21 hook decision-table matrix, temp-repo integration, fail-open cases, Approve bypass; plus `merge_targets` ordered-ladder tests.
- **C2:** diagram generated from `components` (nodes/edges); status-coloring injection; no-Mermaid render path.

## Open questions (deferred, not blocking)

- **Slim-mirror fields** for gate glance reads — exact set pinned in the Spec A plan.
- **Lane policy override** in `project.yaml` (`meta.policies.lanes`) — deferred until a project needs to retune.
- **Phase-level components/diagram** — phases get body files + docs now; the component/diagram treatment is epics-only for v1.
- **Multi-component tasks** — v1 binds one `component`; multi-bind deferred.
- **Blocked/skipped component coloring** semantics — pinned in the C2 plan.
