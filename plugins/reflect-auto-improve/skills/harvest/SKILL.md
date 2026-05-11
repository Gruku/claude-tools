---
name: harvest
description: Pain-point → workflow codifier. Scans a project's session history for recurring friction patterns and emits draft workflow proposals — skill stubs, command outlines, or settings tweaks — ready to become real plugin components. Always uses an adversarial reviewer to filter one-off complaints from genuine repeating pain. Invoke when the user says 'harvest pain points', 'what should we automate', 'find workflows to codify', 'this keeps happening — make it a skill', 'this keeps coming up', 'what are we doing manually that should be automatic', 'what keeps going wrong', 'what should I turn into a skill', 'look at my session history for patterns', 'review my workflow for friction'. Accepts --project <path>; defaults to cwd. Output is advisory — no skill files are created automatically, only proposals routed through taskmaster:add-idea.
---

# harvest — Pain → Workflow

Goal: surface things you keep doing manually and propose how to bake them into commands or skills. Different from `retro` in that the output is **prescriptive** (here is a workflow stub) not descriptive (here is what happened).

**Why harvest does transcript grep in v1 (while retro doesn't):** harvest's job is pattern detection across sessions, which requires raw session signals (user corrections, repeated failures) that don't surface in handovers. Retro is descriptive synthesis — handovers + lessons + git log are sufficient. The cost guard is the `--window <days>` cap (default 14) on transcript scan.

## Parameters

| Param | Default | Values |
|---|---|---|
| `--project <path>` | cwd | Same resolution as `retro`. |
| `--window <days>` | 14 | Look-back window. |

## SCAN Phase

1. The same artifact sources retro reads at standard depth:
   - `<project>/.taskmaster/backlog.yaml`
   - `<project>/.taskmaster/handovers/*.md` (last 7 days)
   - `<project>/.taskmaster/lessons/*.md`
   - `<project>/.taskmaster/issues/*.md` (status changed in window)
   - `<project>/.taskmaster/ideas/*.md` (created in window)
   - `git log --since="<window> days ago" --oneline` and `--stat`
2. **Plus**: targeted transcript grep on `~/.claude/projects/<project-slug>/*.jsonl` for the window. Use `Glob` to enumerate, then `Grep` with these signal patterns (run in parallel):
   - `"^(\\s*)(no|stop|don't|actually)\\b"` — user corrections.
   - `"(error|failed|fail)\\b.*\\b(retry|again|try)"` — repeated failures.
   - `"manually"` and `"every time"` — explicit pain markers.
   - Tool-call sequences that repeat ≥3 times within a session (count via grep + post-processing).
3. Compress the grep hits into a digest: pattern → count → 1-line example. Cap at ≤2000 tokens.

## ANALYZE Phase (proposer sub-agent, Opus)

Dispatch via `Agent` tool with `model: "opus"`. Prompt template:

Before dispatching, substitute `<scan output>` in the template below with the token-capped digest produced in SCAN step 3.

```
You are the proposer for a pain-point harvest. Given the scan digest below, identify RECURRING friction patterns (≥2 occurrences across distinct sessions) and propose concrete workflow stubs to address them.

# Scan Digest
<scan output>

Return ONLY this structure:

## Recurring Pain Patterns
- pattern: <one line>
  occurrences: <count>
  sessions: <SHA / session-id refs>
  current_workaround: <how user currently handles it>

## Workflow Proposals
- title: <Verb-Noun>
  kind: skill|command|setting|hook
  pattern_addressed: <ref to one of the patterns above>
  draft: <~5 line outline of what the skill/command would do>
  blast_radius: small|medium|large
  effort: <S/M/L>

Filter out one-off complaints — patterns must repeat. Cap at 6 proposals.
```

## ADVERSARIAL Phase (always for harvest)

Dispatch a second sub-agent via `Agent` tool with `model: "opus"`. Pass ONLY the proposer's findings (not the scan digest). Prompt template:

Before dispatching, substitute `<proposer output>` in the template below with the proposer sub-agent's full structured response. Do NOT include the scan digest — adversarial blindness invariant.

```
You are an adversarial reviewer. The findings below claim to identify recurring pain patterns and propose workflow stubs. Challenge each one:

- Is this really recurring, or one bad session repeated in summary?
- Does the proposed workflow duplicate something that already exists (check by reading `plugins/*/skills/*/SKILL.md` and `plugins/*/commands/*.md` in claude-tools)?
- Is the proposal vague or actionable?
- Is the blast radius justified?

# Findings to Challenge
<proposer output>

Return ONLY this structure:

## Kept
- title: <as-is>
  reason: <one line>

## Rejected
- title: <as-is>
  reason: <one line — duplicate / one-off / vague / scope>

## New Proposals
- (same shape as proposer's Workflow Proposals — only if the adversarial sees patterns the proposer missed)
```

## SYNTHESIZE Phase

In main context (Opus):
- **Invariant**: do NOT dispatch the proposer sub-agent again after seeing adversarial output. If the kept set is too small, accept the smaller set. The blindness invariant is what makes the adversarial layer meaningful.
- Merge `Kept` + `New Proposals`. Drop `Rejected`.
- Cap final list at 6.
- Assign confidence: high if both agents endorsed, medium if proposer-only, low if adversarial-only.

## EMIT Phase

1. **Report**: write to `<project>/.taskmaster/harvests/YYYY-MM-DD-harvest-<slug>.md` if `<project>/.taskmaster/` exists. Otherwise fall back to `<project>/.reflect/harvests/YYYY-MM-DD-harvest-<slug>.md`. Create the directory if missing. Sections: Header → Recurring Patterns (with sessions/SHAs) → Workflow Proposals (with drafts, blast radius, confidence) → Adversarial Rejections (so the user can audit the filter) → Open Questions.

2. **Route proposals**: every kept proposal becomes `mcp__plugin_taskmaster_taskmaster__backlog_idea_create` tagged `reflect:harvest`. The draft outline goes in the idea body so a future task can pick it up.

3. **Final message**: one paragraph + report path + idea IDs.

## What this Skill Does NOT Do

- Does not create skill files, command files, or settings. Output is advisory.
- Does not modify TARGETS.md.
- Does not transcript-grep beyond the configured window (cost guard).
