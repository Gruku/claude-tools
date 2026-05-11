---
name: reflect
description: Universal entry point for reflecting on past work. Invoke when the user says 'reflect on', 'do a retro', 'let's audit our work', 'how have we been working', 'what should we automate', 'find dead skills', 'review last week', 'pain-point harvest', 'how are we doing', 'process check-in', 'are we improving', 'check our process', 'team health check', or otherwise asks to look back and improve. Routes to the correct lens skill (retro / harvest / plugin-audit) based on intent.
---

# reflect — Router

Map the user's request to one of the three lens skills. If intent is unclear, ask one clarifying question (use AskUserQuestion) before routing.

## Intent Routing

| Signal phrases | Route to |
|---|---|
| "retro", "review the week", "how did we work in X", "look back at sessions", "what worked and what didn't" | `reflect-auto-improve:retro` |
| "harvest pain points", "what should we automate", "find workflows to codify", "this keeps coming up — let's bake it in" | `reflect-auto-improve:harvest` |
| "audit the plugins", "find dead skills", "token costs", "prune commands", "what's eating our tokens", "claude-tools self-audit" | `reflect-auto-improve:plugin-audit` |
| Generic "reflect on our work" with no obvious lens | Ask: which lens? present retro / harvest / plugin-audit as options |

## Depth Hint

If the user mentions speed/depth ("quick", "deep", "thorough", "fast"), pass that through as the `depth` argument to `retro` (`shallow` | `standard` | `deep`). v1 supports `shallow` and `standard` for retro. If the user asks for `deep`, defer to the retro skill itself — it owns the unsupported-depth error message.

## Target Resolution

If the user names a project (e.g. "reflect on CodeMaestro"), look up its path in `plugins/reflect-auto-improve/TARGETS.md` and pass via `--project <path>` to the lens skill. Otherwise default to cwd.

## What this Skill Does NOT Do

- Do not call `reflect-auto-improve:retro`, `harvest`, or `plugin-audit` directly when the user's intent is ambiguous — route through here.
- It does not scan, analyze, or write reports itself. All real work happens in the lens skill it routes to.
- It does not modify TARGETS.md. Adding a target is a manual edit.
