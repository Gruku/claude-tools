# Claude Tools

Plugin marketplace & standalone tools for [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

**[Browse Plugins](https://gruku.github.io/claude-tools/)** · Marketplace: `gruku-tools`

## Quick Start

```bash
# Add the marketplace
/plugin marketplace add Gruku/claude-tools

# Install a plugin
/plugin install taskmaster@gruku-tools
```

---

## Plugins

### Taskmaster `v1.0.0` ✨ NEW

Universal AI-powered task and backlog management. Drop into any project.

- **23 MCP tools** — tasks, epics, milestones, dependencies, search, validation, session locking
- **Kanban viewer** — dark/light theme board on port 6800 with filtering, search, and milestone progress
- **Session tracking** — auto-generated Done/Decisions/Issues changelog entries
- **Worktree isolation** — every task gets its own git worktree
- **Quality gates** — spec/plan check, code review, tests, build verification
- **TODO auditing** — scan codebase for TODO/FIXME/HACK, cross-reference with backlog
- **Milestones** — sequential blocks of work for focus, one active at a time
- **Configurable storage** — `.claude/` (hidden) or project root (git-tracked)

**Skills:** `/init-taskmaster` `/start-session` `/pick-task` `/review-gate` `/end-session` `/check-todos`

### Shader Nodes `v2.0.0`

UE5.5 shader development pipeline. HLSL design (Opus) + Material Graph generation (Sonnet) → paste into Material Editor.

**Skills:** `/shader-nodes:create` `/shader-nodes:yaml` `/shader-nodes:registry`

### Reality Reprojection `v1.3.0`

Web design system plugin. Generate components, convert existing code, review compliance.

**Skills:** `/reality-reprojection:apply` `/reality-reprojection:generate` `/reality-reprojection:convert`

### Image Gen `v1.0.0`

Multi-backend image generation with Google Gemini and OpenAI GPT Image 1.5. Transparent PNGs, multi-turn refinement, game assets.

**Skills:** `/image-gen` `/image-gen:generate` `/image-gen:edit` `/image-gen:refine`

### Codex Dispatch `v1.0.0`

Dispatch tasks to OpenAI Codex CLI for parallel execution with GPT/o-series models.

**Skills:** `/codex-dispatch`

---

## Standalone Tools

### Statusline

Pastel statusline for Claude Code with rate limit bars, git status, context usage, update notifications, and session cost tracking.

**[Live Preview](https://gruku.github.io/claude-tools/statusline/)** · Supports PowerShell and Bash

![Statusline Preview](statusline/screenshot.png)

---

## Marketplace Reference

### Structure

```
claude-tools/
├── .claude-plugin/
│   └── marketplace.json        # plugin catalog
├── plugins/
│   ├── taskmaster/             # AI task management
│   ├── shader-nodes/           # UE5 shader pipeline
│   ├── reality-reprojection/   # web design system
│   ├── image-gen/              # image generation
│   └── codex-dispatch/         # multi-model dispatch
└── statusline/                 # standalone tool
```

### Commands

| Command | Purpose |
|---------|---------|
| `/plugin marketplace add Gruku/claude-tools` | Add this marketplace |
| `/plugin install name@gruku-tools` | Install a plugin |
| `/plugin marketplace update gruku-tools` | Pull latest changes |
| `/plugin update name@gruku-tools` | Update a specific plugin |
| `/reload-plugins` | Apply changes without restarting |

### Creating Your Own Plugin

1. Create `plugins/my-plugin/.claude-plugin/plugin.json` with name, description, version, author
2. Add skills in `plugins/my-plugin/skills/<name>/SKILL.md`
3. Add entry to `.claude-plugin/marketplace.json`
4. Push to GitHub — users install via `/plugin marketplace add your/repo`

See [Plugin Marketplaces docs](https://code.claude.com/docs/en/plugin-marketplaces) for the full guide.
