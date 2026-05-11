---
name: harvest
description: Pain-point → workflow codifier. Scans a project's session history for recurring friction patterns and emits draft workflow proposals — skill stubs, command outlines, or settings tweaks — ready to become real plugin components. Always uses an adversarial reviewer to filter one-off complaints from genuine repeating pain. Invoke when the user says 'harvest pain points', 'what should we automate', 'find workflows to codify', 'this keeps happening — make it a skill', 'what are we doing manually that should be automatic'. Accepts --project <path>; defaults to cwd. Output is advisory — no skill files are created automatically, only proposals routed through taskmaster:add-idea.
---

# harvest — Pain → Workflow

Goal: surface things you keep doing manually and propose how to bake them into commands or skills. Different from `retro` in that the output is **prescriptive** (here is a workflow stub) not descriptive (here is what happened).

## Parameters

| Param | Default | Values |
|---|---|---|
| `--project <path>` | cwd | Same resolution as `retro`. |
| `--window <days>` | 14 | Look-back window. |

## SCAN Phase

1. All sources from `retro:standard` SCAN.
2. **Plus**: targeted transcript grep on `~/.claude/projects/<project-slug>/*.jsonl` for the window. Use `Glob` to enumerate, then `Grep` with these signal patterns (run in parallel):
   - `"^(\\s*)(no|stop|don't|actually)\\b"` — user corrections.
   - `"(error|failed|fail)\\b.*\\b(retry|again|try)"` — repeated failures.
   - `"manually"` and `"every time"` — explicit pain markers.
   - Tool-call sequences that repeat ≥3 times within a session (count via grep + post-processing).
3. Compress the grep hits into a digest: pattern → count → 1-line example. Cap at ≤2000 tokens.

## ANALYZE Phase (proposer sub-agent, Opus)

Dispatch via `Agent` tool with `model: "opus"`. Prompt template:

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
- Merge `Kept` + `New Proposals`. Drop `Rejected`.
- Cap final list at 6.
- Assign confidence: high if both agents endorsed, medium if proposer-only, low if adversarial-only.

## EMIT Phase

1. **Report**: `<project>/.taskmaster/retros/YYYY-MM-DD-harvest-<slug>.md` (or `.reflect/retros/` fallback). Sections: Header → Recurring Patterns (with sessions/SHAs) → Workflow Proposals (with drafts, blast radius, confidence) → Adversarial Rejections (so the user can audit the filter) → Open Questions.

2. **Route proposals**: every kept proposal becomes `mcp__plugin_taskmaster_taskmaster__backlog_idea_create` tagged `reflect:harvest`. The draft outline goes in the idea body so a future task can pick it up.

3. **Final message**: one paragraph + report path + idea IDs.

## What this Skill Does NOT Do

- Does not create skill files, command files, or settings. Output is advisory.
- Does not modify TARGETS.md.
- Does not transcript-grep beyond the configured window (cost guard).
