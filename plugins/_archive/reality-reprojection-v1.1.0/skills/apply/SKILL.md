---
name: apply
description: "Apply the Reality Reprojection design system — auto-detects whether to generate new components, convert existing code, or review compliance. Single entry point that routes to the correct sub-skill."
argument-hint: [describe what you need]
---

# Reality Reprojection — Router

You are the entry point for the Reality Reprojection design system plugin. Your job is to determine what the user needs and route to the correct skill.

## Intent Detection

Analyze `$ARGUMENTS` and classify the user's intent:

| Intent | Signal Words | Route To |
|--------|-------------|----------|
| **Setup** | "setup", "bootstrap", "install", "init", "add to project", "get started" | `reality-reprojection:setup` |
| **Generate** | "create", "build", "make", "add", "I need", "generate", "new", "component", "page", "form", "card", "button" | `reality-reprojection:generate` |
| **Convert** | "convert", "transform", "migrate", "apply to", "make it match", "rewrite", "update to", "refactor to" + file path references | `reality-reprojection:convert` |
| **Review** | "check", "audit", "review", "compliance", "does this follow", "validate", "inspect", "scan" | `reality-reprojection:review` |

## Routing Rules

1. If intent is clear: invoke the matching skill immediately using the Skill tool, passing `$ARGUMENTS` through
2. If the user provides a file path AND generation language: route to **convert** (they want to transform existing code)
3. If the user provides a file path AND audit language: route to **review**
4. If the user describes something that doesn't exist yet: route to **generate**
5. If ambiguous: ask the user which action they want

## Ambiguous Intent Resolution

When you cannot determine intent, ask:

> I can help you with the Reality Reprojection design system in four ways:
>
> 1. **Setup** — Bootstrap the design system into your project (CSS + fonts)
> 2. **Generate** — Create new components from a description
> 3. **Convert** — Transform existing code to use the design system
> 4. **Review** — Audit code for design system compliance
>
> Which would you like?

## Examples

- "Set up the design system in my project" → invoke `reality-reprojection:setup`
- "Create a login form with email and password" → invoke `reality-reprojection:generate`
- "Apply the design system to my index.html" → invoke `reality-reprojection:convert`
- "Does this CSS follow the design system rules?" → invoke `reality-reprojection:review`
- "I need a dashboard layout" → invoke `reality-reprojection:generate`
- "Convert src/styles.css to use proper tokens" → invoke `reality-reprojection:convert`
- "Check my components for compliance" → invoke `reality-reprojection:review`
- "Bootstrap Reality Reprojection into this project" → invoke `reality-reprojection:setup`

## Invocation

Use the Skill tool to invoke the target skill:

```
Skill: reality-reprojection:generate
Args: [pass through the user's original arguments]
```

Do NOT attempt to generate, convert, or review code yourself. Always route to the specialized skill.
