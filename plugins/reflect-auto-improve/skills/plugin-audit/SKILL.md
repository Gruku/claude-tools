---
name: plugin-audit
description: Self-audit of claude-tools plugins. Operates on plugin source files (not project artifacts). Finds dead skills (never invoked across transcripts), oversized skill descriptions (token cost), command pruning candidates, and recurring transcript patterns that should become new skills. Always uses an adversarial reviewer. Invoke when the user says 'audit the plugins', 'find dead skills', 'what's eating our tokens', 'prune commands', 'claude-tools self-audit', 'plugin health check', 'which skills are we actually using', 'are our skills still healthy', or after major plugin changes. Output is advisory — routes proposals through taskmaster:add-idea in claude-tools' own backlog.
---

# plugin-audit — Claude-tools self-audit

Different from `retro` and `harvest` in input domain: this audits **plugin source code** (skill/command/agent markdown files) rather than project artifacts.

## Parameters

| Param | Default | Values |
|---|---|---|
| `--plugin <name>` | all | Scope to one plugin under `plugins/` (e.g. `taskmaster`). |
| `--include-transcripts` | true | Scan `~/.claude/projects/*/*.jsonl` for skill invocations to detect dead skills. Set false for a fast structural-only audit. |
| `--window <days>` | 90 | Look-back window for transcript invocation counting. Default 90 — long enough to avoid false-positive dead-skill flagging for recently-added skills, short enough to bound cost. |

## SCAN Phase

1. **Enumerate plugin assets** via Glob (run all in parallel):
   - `plugins/*/skills/**/SKILL.md`
   - `plugins/*/commands/*.md`
   - `plugins/*/agents/*.md` (may be empty)
   - `plugins/*/.claude-plugin/plugin.json`

2. **Per skill**, extract: name, description, body char count, body word count. Compute description char count separately (it's the trigger surface and the biggest token spend).

3. **Per command**: frontmatter description, body (usually 1-3 lines).

4. **Invocation counts** (if `--include-transcripts`):
   - Enumerate `~/.claude/projects/*/*.jsonl`.
   - Grep each for skill invocation markers. The reliable patterns:
     - `"Skill"` tool calls naming the skill in tool_use blocks. Match BOTH the qualified form (`"reflect-auto-improve:plugin-audit"`) and the bare form (`"name":"plugin-audit"`) — transcripts use both, and missing one causes false zero-invocation counts.
   - Aggregate counts per skill across all transcripts. Skills with 0 invocations across the user's full history are prime dead-skill candidates.

5. **Pattern surface across plugins** (cross-plugin overlap detection):
   - For each pair of skill descriptions, compute a quick token-overlap heuristic (shared trigger phrases).
   - Flag pairs with high overlap — potential consolidation candidates.

Digest output ≤3000 tokens (this scan is bigger than retro/harvest).

## ANALYZE Phase (proposer sub-agent, Opus)

Dispatch via `Agent` tool with `model: "opus"`. Prompt template:

```
You are the proposer for a claude-tools plugin self-audit. Given the scan digest below, identify:

1. Dead skills (0 invocations across user's transcripts)
2. Oversized skill descriptions (>800 chars where the trigger surface could be tighter)
3. Command pruning candidates (commands invoking skills that themselves are dead, or trivial passthroughs that add nothing)
4. Cross-plugin overlap (two skills with overlapping trigger phrases — consolidation candidate)
5. Missing skills — patterns in transcripts that appear frequently but no skill handles them

# Scan Digest
<scan output>

Return ONLY this structure:

## Dead Skills
- skill: <plugin>:<name>
  invocations: 0
  rationale: <one line — why prune>

## Oversized Descriptions
- skill: <plugin>:<name>
  current_chars: <n>
  suggested_chars: <n>
  what_to_trim: <one line>

## Command Prune Candidates
- command: /<name>
  rationale: <one line>

## Consolidation Candidates
- skills: [<a>, <b>]
  rationale: <one line>

## Missing Skills (proposed creates)
- title: <Verb-Noun>
  pattern_addressed: <transcript pattern summary>
  draft: <~5 line outline>

Cap each category at 8 items.
```

## ADVERSARIAL Phase (always)

Same shape as `harvest` adversarial. Prompt:

```
Adversarial review of plugin audit findings. Challenge each item:

- Dead skill: was it created within the last 30 days? (new skills should not be pruned based on zero invocations alone)
- Oversized description: does trimming risk losing trigger coverage?
- Prune command: is it referenced by any documentation, README, or other skill?
- Consolidation: do the two skills actually have different jobs that share trigger words?
- Missing skill: is there an existing skill that already covers this with non-obvious trigger phrases?

For "is referenced by" checks, you may use Grep against `plugins/**/*.md` and `**/CLAUDE.md` and `**/README.md`.

# Findings
<proposer output>

Return ONLY:

## Kept
- item: <as in proposer output>
  reason: <one line>

## Rejected
- item: <as in proposer>
  reason: <one line>

## New Findings
- (proposer-shaped entries, only if adversarial sees something the proposer missed)
```

## SYNTHESIZE Phase

In main context (Opus).
- **Invariant**: do NOT dispatch the proposer sub-agent again after seeing adversarial output. If the kept set is too small, accept the smaller set. The blindness invariant is what makes the adversarial layer meaningful.
- Merge Kept + New. Cap each category at 6.

## EMIT Phase

1. **Report**: `docs/reflect/audits/YYYY-MM-DD-<scope>.md` where `<scope>` is the `--plugin` value or `all`. Create `docs/reflect/audits/` if missing. This path is intentionally repo-level (not per-target-project) — the audit subject IS claude-tools, so the report belongs to claude-tools itself, not to any external taskmaster project.

2. **Route proposals**: into claude-tools' own taskmaster backlog (cwd should already be in claude-tools when this runs). Each finding becomes a direct call to `mcp__plugin_taskmaster_taskmaster__backlog_idea_create` with `created_by="Claude"`. Do NOT invoke the `taskmaster:add-idea` skill — `add-idea`'s SKILL.md documents this carve-out for Claude-initiated auto-log paths, but the carve-out IS the direct call, not skill invocation. Tag each idea `reflect:plugin-audit` with category suffix (`reflect:plugin-audit:dead-skill`, `reflect:plugin-audit:oversized-description`, etc.).

3. **Final message**: one paragraph + report path + idea IDs.

## What this Skill Does NOT Do

- Does NOT delete, edit, or rename any plugin file. Output is advisory.
- Does NOT modify CLAUDE.md or settings.
- Does NOT push findings to remote.
