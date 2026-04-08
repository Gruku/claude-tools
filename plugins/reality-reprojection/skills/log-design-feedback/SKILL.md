---
name: log-design-feedback
description: "Log design feedback and observations about Reality Reprojection — use whenever you have feedback, preferences, or decisions while working with the design system in any project. Saves verbatim input to the canonical RR feedback log with date, source project, and action items."
argument-hint: [your feedback or observations]
---

# Reality Reprojection — Design Feedback Logger

You are capturing design feedback or observations about the Reality Reprojection design system. This feedback may come from the main RR repo or from any project where the system is being applied (sim projects, client work, explorations, etc.).

## Canonical Feedback Location

**Always write to:** `C:\Users\gruku\Files\Claude\reality-reprojection-design\feedback\`

This is the fixed path regardless of which project you are in when you invoke this skill.

## Step 1 — Parse `$ARGUMENTS`

If `$ARGUMENTS` contains feedback, use it verbatim as the raw input.
If `$ARGUMENTS` is empty or unclear, ask: "What did you observe or want to log? Give me the raw feedback."

## Step 2 — Determine Context

Infer from session context (do NOT ask unless truly unclear):

| Field | How to determine | Examples |
|-------|-----------------|---------|
| **Source project** | Current working directory or session topic | `sim-dashboard`, `reality-reprojection-design`, `client-landing` |
| **Direction** | What the feedback targets | `design` / `component` / `css` / `plugin` / `demo` / `architecture` |
| **Topic** | 2–4 word kebab-case descriptor | `card-spacing`, `frost-on-dark`, `button-hierarchy` |

If session context doesn't reveal the source project, ask once: "Which project is this feedback from?"

## Step 3 — Generate Filename

Format: `YYYY-MM-DD-{direction}-{topic}.md`

- Use today's date from session context
- If a file with that name already exists, append `-2.md`, `-3.md`, etc.

## Step 4 — Write the Feedback File

Create the file at the canonical path. Use this template:

```markdown
# {YYYY-MM-DD} — {Direction} Feedback: {Topic Title Case}

## Source
**Project:** {source project}
**Session:** {brief 1-sentence description of what was being worked on}

## Raw Input (Verbatim)
> {User's exact words — do not paraphrase}

## Context
{What component, page, or situation produced this observation. 1–3 sentences.}

## Analysis

### What was observed
{Concrete observation — what looked wrong, what worked, what was decided, what pattern emerged}

### Implication for RR System
{How this informs the design system: which tokens, components, rules, or patterns are affected}

## Action Items
- [ ] **P{0|1|2}** — {actionable item} [scope: {css / plugin / reference / demo / guide}]
```

Priority levels: `P0` = blocking/broken, `P1` = important fix or rule, `P2` = polish or documentation.

## Step 5 — Propagation Check

Scan the feedback for **system-level patterns** — observations that would apply across projects, not just the current one. Signals: repeating pain points, new design rules, cross-project consistency issues.

If a pattern is found, append this section to the file:

```markdown
## Propagation Flag
**Pattern:** {One-sentence design rule or principle derived from this feedback}
**Target:** `feedback/DESIGN-SYSTEM-FEEDBACK-AND-PATTERNS.md`
**Section:** {which section of the patterns doc this belongs in}
```

Then tell the user: "Propagation flag set — this looks like a system-level rule. Consider a propagation session to update `DESIGN-SYSTEM-FEEDBACK-AND-PATTERNS.md`."

## Step 6 — Confirm

Report back concisely:

```
Logged → feedback/{filename}
Summary: {one sentence}
Source: {project name}
Propagation flag: {set / not set}
```

If there are existing open feedback files related to the same component or topic, mention them.
