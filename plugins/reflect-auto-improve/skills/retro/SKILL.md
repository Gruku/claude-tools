---
name: retro
description: Time-windowed retrospective on a project's past work. Reads taskmaster artifacts (handovers, lessons, issues, ideas, recap) and git log to produce a markdown report plus concrete proposals routed back through taskmaster. Invoke when the user says 'retro the last week', 'how did we work in CodeMaestro', 'review our recent sessions', 'what worked and what didn't this sprint', 'look back at this project'. Accepts depth=shallow|standard (deep is v1.1) and --project <path> (defaults to cwd). Do not invoke `backlog_*_create` directly — emit proposals via this skill's pipeline so they're tagged consistently.
---

# retro — Time-windowed project retrospective

Run the SCAN → ANALYZE → SYNTHESIZE → EMIT pipeline. v1 supports `depth=shallow` and `depth=standard`. Deep depth (adversarial + transcript grep) is fast-follow.

(Note: retro intentionally skips the ADVERSARIAL phase that harvest and plugin-audit use, because retro's output is descriptive — "what happened" — not prescriptive. The proposer's self-praise risk is lower for retrospective synthesis than for forward-looking workflow design. If retro's standard depth ever produces ≥4 high-blast-radius proposals, consider promoting to deep depth in v1.1, which will include adversarial.)

## Parameters

| Param | Default | Values |
|---|---|---|
| `depth` | `standard` | `shallow` (last 1–3 sessions), `standard` (last 7 days) |
| `--project <path>` | cwd | Absolute path or relative-to-cwd. Walks up to find `.taskmaster/` or `.git`. |

If user asks for `depth=deep`: respond that deep ships in v1.1 (`docs/superpowers/specs/2026-05-11-reflect-auto-improve-design.md` §8 stretch) and offer `standard` instead.

## SCAN Phase

Read these in parallel using Glob/Read/Bash:

1. `<project>/.taskmaster/backlog.yaml` — overall state.
2. `<project>/.taskmaster/handovers/*.md` — pick last N for shallow (3), last week's worth for standard.
3. `<project>/.taskmaster/lessons/*.md` — all lessons; flag any reinforced in window.
4. `<project>/.taskmaster/issues/*.md` — filter by status=open or status changed in window.
5. `<project>/.taskmaster/ideas/*.md` — recent ideas (created in window).
6. (Skip recap_get — it requires an explicit session_id and handovers already carry equivalent context. To get recent recaps, optionally call `mcp__plugin_taskmaster_taskmaster__recap_list` and pick the most recent N entries.)
7. `git log --since=<window> --oneline` and `git log --since=<window> --stat` (use Bash).

For `depth=shallow`, just (1), last 3 of (2), and `git log -n 30 --oneline`.

Digest the scan output to ≤2000 tokens before passing to the proposer — bullet summaries, not raw file dumps.

## ANALYZE Phase (proposer sub-agent)

Dispatch via `Agent` tool. Model selection:

- `shallow`: do NOT dispatch a sub-agent. Synthesize directly in main context (Sonnet/Opus per session model).
- `standard`: dispatch sub-agent with `model: "sonnet"`.

Sub-agent prompt template:

```
You are the proposer for a project retrospective. Given the scan digest below, return findings as structured markdown.

# Scan Digest
<scan output here>

# Window
<dates>

# Project
<name and path>

Return ONLY this structure (no preamble, no commentary):

## Pain Points
- summary: <one line>
  evidence: <handover ID / commit SHA / lesson ID>
  severity: P0|P1|P2|P3

## Wins
- summary: <one line>
  evidence: <ref>

## Patterns
- summary: <one line>
  frequency: <occurrences in window>
  evidence: <refs>

## Proposals
- kind: issue|idea|lesson
  title: <concise>
  rationale: <2-3 sentences>
  blast_radius: small|medium|large

Cap proposals at 8 total.
```

## SYNTHESIZE Phase

(`standard` depth only — `shallow` skips and goes straight to EMIT with the proposer-free analysis.)

In main context:
- Trim to ≤10 proposals max.
- Assign confidence (high / medium / low) based on evidence count.
- Resolve duplicate ideas (e.g. multiple pain points naming the same workflow gap collapse to one proposal).

## EMIT Phase

1. **Write the report** at one of these paths (try in order):
   - `<project>/.taskmaster/retros/YYYY-MM-DD-retro-<slug>.md` if `.taskmaster/` exists.
   - `<project>/.reflect/retros/YYYY-MM-DD-retro-<slug>.md` otherwise (create dir if needed).

   Report sections: Header (date / project / window / depth) → Pain Points → Wins → Patterns → Proposals (with confidence) → Open Questions.

2. **Route each proposal** via the taskmaster gate skills into the target project's backlog. Always include a `reflect:retro` tag/label.

   - `kind: issue` → invoke `taskmaster:issue` skill (do NOT call `backlog_issue_create` directly — that bypasses the gate). Pass severity from proposer; map P0/P1 → high, P2 → medium, P3 → low.
   - `kind: idea` → call `mcp__plugin_taskmaster_taskmaster__backlog_idea_create` directly with `created_by="Claude"` (the sanctioned auto-log path documented in `taskmaster:add-idea`).
   - `kind: lesson` → invoke `taskmaster:lesson` skill (do NOT call `backlog_lesson_create` directly).

   If the target project lacks taskmaster initialization, skip routing and list proposals in the report only. Tell the user.

3. **Final message to user**: one short paragraph + path to report + bulleted list of created artifacts with IDs.

## What this Skill Does NOT Do

- Does not modify any task / lesson / issue beyond creating new ones. No status transitions.
- Does not touch transcripts in v1 (that's `depth=deep`, v1.1).
- Does not run when scan turns up zero artifacts — emits a "nothing to reflect on" message instead and exits.
