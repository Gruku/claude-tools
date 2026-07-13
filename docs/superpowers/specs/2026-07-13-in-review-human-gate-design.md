# in-review as Human-Blocked Exception State — Design

**Date:** 2026-07-13
**Status:** Approved (brainstorm dialogue)
**Target version:** taskmaster 4.5.0 (minor — additive field + default-behavior change)
**Repos:** `C:\Users\gruku\Files\Claude\taskmaster` (source of truth); claude-tools consumes via submodule bump.

## Problem

The current ladder treats `in-review` as a mandatory stage: end-session defaults to it, and `done` means "user confirmed testing." In practice the user tests informally and never formally closes, so tasks pile up in in-review forever. The human-confirmation stage doesn't happen — the model should stop pretending it does.

## Decision

`in-review` flips from a pipeline stage to an **exception state**: "AI work complete, blocked on an action only a human can do" (add an API key, LLM config, account access, physical-world step). `done` becomes the default terminal state: **Claude finished + review-gate passed**. Human eyeballing of done work moves downstream to a CodeMaestro sweep skill — explicitly out of scope for taskmaster.

Ladder unchanged on disk: `todo → in-progress → in-review → done → archived`. The status *value* `in-review` is kept (no schema break, no cross-project status-string migration, Linear mapping untouched); UI relabels it.

## Schema: `human_action`

- New **light field** on tasks, in `backlog.yaml` (viewer must show it without reading the task body file).
- Short free-text imperative: `human_action: "add OPENAI_API_KEY to .env"`.
- Present ⇒ the task belongs in in-review. Absent ⇒ it doesn't.
- Set at task creation when known upfront, or by Claude at end-session when it hits a blocker it can't clear.
- Closing an in-review task to done clears `human_action` atomically (same write).

## Enforcement (opinionated, no toggles)

1. `backlog_complete_task(target_status="in-review")` **requires** a `human_action` argument — parking a task in in-review without stating what the human must do is rejected.
2. `backlog_update_task` setting `status: in-review` has the same requirement (field must be present or supplied in the same call).
3. End-session default target status flips from `in-review` to **`done`**. in-review is chosen only when a human_action exists.
4. Gates model (Spec A) unchanged: `done` still requires the lane's review-gate. This design removes the human-testing stage, not the quality gate.

## Session-skill changes

- **start-session:** new "Waiting on you" section — every in-review task with its `human_action` string. Exit path is verify-and-close: when the user says it's handled, or Claude can verify it directly (e.g. env var now exists), close via the normal complete flow (changelog entry, human_action cleared). No new tooling.
- **end-session / pick-task / review-gate playbooks + summary-modes reference:** reword the status-semantics blurb to: *"In-review = blocked on human action (human_action says what). Done = Claude complete + gates passed."* Remove "user confirmed testing" language.
- **Adapters/playbooks mirror:** the same wording lands in the multi-assistant playbooks (`playbooks/…`), which are the source the adapters consume.

## Viewer

- Kanban column for status `in-review` relabels to **"Waiting on human"**.
- Cards in that column render the `human_action` string.
- No other screens change. Chip filters keep the `in-review` key. Linear sync status mapping untouched.

## Migration: one-time bulk close

On first start-session after the upgrade (per project): if in-review tasks exist without `human_action`, present the list once and batch-close to done — except any the user flags as genuinely blocked, which get a `human_action` written instead of closing. Marker to not re-prompt: the sweep only fires when human_action-less in-review tasks exist, so it self-extinguishes.

## Out of scope

- Grouping done tasks for manual review sweeps — a CodeMaestro skill; taskmaster adds **no** `user_reviewed` marker. The sweep skill queries by `completed_at` / changelog since its last run.
- Auto-verification machinery for human_actions (checking env vars is opportunistic skill behavior, not a subsystem).
- Renaming the status value.

## Versioning

Bump the three parts together per repo protocol: `plugin.json`, `marketplace.json`, `CHANGELOG.md` → **4.5.0**.

## Rejected alternatives

- **Gate-based modeling** (human-action as a new gate type): heavier machinery for what is a flag + reason.
- **End-session judgment only** (no field): records nothing about *why* a task is parked.
- **`user_reviewed` flag on done tasks:** single-consumer schema field; done is done.
- **Status rename to `needs-human`:** honest name, but breaks every backlog.yaml, filter, adapter, and Linear mapping for a label.
- **Silent auto-close migration:** risks closing a genuinely human-blocked task without capturing its human_action.
