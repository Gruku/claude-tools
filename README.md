# Claude Tools

Custom tools for [Claude Code](https://claude.ai/claude-code).

**[Live Preview](https://gruku.github.io/claude-tools/)**

## Statusline

Pastel statusline for Claude Code with rate limit bars, git status, context usage, update notifications, and session cost tracking.

**[Live Preview](https://gruku.github.io/claude-tools/statusline/)**

![Statusline Preview](statusline/screenshot.png)

**Features:**
- Pastel color palette with gradient limit bars (green → red)
- Git branch, dirty/staged indicators (with nested repo fallback)
- 5-hour and 7-day rate limit bars via OAuth API
- Context window usage with brightness squares
- Per-session update notifications (no cross-session pollution)
- Session cost tracking
- Extra usage spend/limit display
- Vim mode indicator

**Supports:** PowerShell (Windows) and Bash (macOS/Linux)

## UE5 Custom Shader Nodes

Material graph node generator for Unreal Engine 5.5. Generates node structures for copy-paste into the Material Editor, including custom HLSL nodes, material functions, and wiring diagrams.

## Reality Reprojection

Design system plugin for web projects. Provides setup, generate, convert, review, and apply skills.

## Image Gen

Multi-backend image generation plugin. Generate, edit, and iteratively refine images using Gemini and OpenAI GPT Image 1.5. Supports native transparent PNGs (OpenAI) and two-pass alpha extraction (Gemini).

---

## Plugin & Marketplace Reference

### Local Marketplace Setup

This repo is a local plugin marketplace. Claude Code discovers plugins through a `marketplace.json` that lists available plugins.

**Required structure:**

```
claude-tools/                          # marketplace root
├── .claude-plugin/
│   └── marketplace.json               # lists all plugins
└── plugins/
    ├── my-plugin/
    │   ├── .claude-plugin/
    │   │   └── plugin.json            # plugin identity
    │   ├── skills/
    │   │   └── my-skill/
    │   │       └── SKILL.md
    │   └── src/                       # optional: scripts, assets
    └── another-plugin/
        └── ...
```

### Step 1: Create the Marketplace Manifest

`.claude-plugin/marketplace.json` at the repo root:

```json
{
  "name": "my-marketplace",
  "owner": { "name": "your-name" },
  "metadata": {
    "description": "Description of your marketplace",
    "pluginRoot": "./plugins"
  },
  "plugins": [
    {
      "name": "my-plugin",
      "source": "./plugins/my-plugin",
      "description": "What the plugin does",
      "version": "1.0.0"
    }
  ]
}
```

Every plugin you add must have an entry in the `plugins` array.

### Step 2: Create a Plugin

Each plugin needs `.claude-plugin/plugin.json`:

```json
{
  "name": "my-plugin",
  "description": "What the plugin does",
  "version": "1.0.0",
  "author": { "name": "your-name" }
}
```

The `name` field becomes the skill namespace (e.g., `/my-plugin:skill-name`).

### Step 3: Add Skills

Skills live in `skills/<skill-name>/SKILL.md`:

```markdown
---
name: skill-name
description: "When and why Claude should use this skill"
---

# Skill Title

Instructions for Claude when this skill is invoked.
```

- Folder name = skill name
- `name` in frontmatter must match folder name
- `description` helps Claude decide when to auto-invoke the skill

### Step 4: Register the Marketplace

```bash
# Add the marketplace (one-time)
/plugin marketplace add /path/to/claude-tools

# Or from GitHub
/plugin marketplace add owner/repo
```

After adding, run `/plugin` to browse and install plugins from the **Discover** tab.

### Step 5: Install a Plugin

```bash
# Via CLI
/plugin install my-plugin@my-marketplace

# Or use the interactive /plugin UI → Discover tab → select → choose scope
```

**Scopes:** User (all projects), Project (shared via .claude/settings.json), Local (just you, this repo)

### Adding a New Plugin (Checklist)

1. Create `plugins/new-plugin/.claude-plugin/plugin.json`
2. Create `plugins/new-plugin/skills/<name>/SKILL.md` for each skill
3. Add entry to `.claude-plugin/marketplace.json` `plugins` array
4. Run `/plugin marketplace update marketplace-name` to refresh
5. Install via `/plugin install new-plugin@marketplace-name`

### Testing During Development

```bash
# Load a plugin directly without marketplace (for dev/testing)
claude --plugin-dir ./plugins/my-plugin

# Load multiple
claude --plugin-dir ./plugins/plugin-one --plugin-dir ./plugins/plugin-two
```

### Useful Commands

| Command | Purpose |
|---------|---------|
| `/plugin` | Open plugin manager UI |
| `/plugin marketplace list` | List configured marketplaces |
| `/plugin marketplace update name` | Refresh plugin listings |
| `/plugin install name@marketplace` | Install a plugin |
| `/plugin disable name@marketplace` | Disable without uninstalling |
| `/plugin enable name@marketplace` | Re-enable |
| `/plugin uninstall name@marketplace` | Remove completely |
| `/reload-plugins` | Apply changes without restarting |

### Plugin Component Reference

| Directory | Location | Purpose |
|-----------|----------|---------|
| `.claude-plugin/` | Plugin root | `plugin.json` manifest only |
| `skills/` | Plugin root | Agent Skills (`SKILL.md` per folder) |
| `commands/` | Plugin root | User-invocable commands (`.md` files) |
| `agents/` | Plugin root | Custom agent definitions |
| `hooks/` | Plugin root | Event handlers (`hooks.json`) |
| `.mcp.json` | Plugin root | MCP server configs |
| `.lsp.json` | Plugin root | LSP server configs |
| `settings.json` | Plugin root | Default settings when plugin is enabled |

### How Skills Work

A `skills/<name>/SKILL.md` in a plugin automatically registers as `/plugin-name:<name>`. Both `commands/foo.md` and `skills/foo/SKILL.md` create the same namespaced command. If both exist with the same name, the skill takes precedence.

- `disable-model-invocation: true` — hides from Claude's auto-invocation (user must invoke manually)
- SessionStart hooks — optional, inject context into every session (not required for skills to load)

### Common Gotchas

- **Plugin not showing up?** Check that it's listed in `marketplace.json` AND has `.claude-plugin/plugin.json`
- **Skills not loading?** Each skill must be a directory with `SKILL.md` inside, not a flat `.md` file
- **Don't put skills inside `.claude-plugin/`** — only `plugin.json` goes there
- **After changes:** run `/plugin marketplace update` then `/reload-plugins`
