# Claude Tools

Plugin marketplace for [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

**[Browse Plugins](https://gruku.github.io/claude-tools/)** · Marketplace: `gruku-tools`

> Versions are not listed in this README — they live in [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json) as the single source of truth. The [GitHub Pages site](https://gruku.github.io/claude-tools/) reads that file at load time, so the browsable catalog is always current without a docs build step.

## Quick Start

```bash
# 1. Add the marketplace
/plugin marketplace add Gruku/claude-tools

# 2. Install a plugin
/plugin install taskmaster@gruku-tools

# 3. Reload
/reload-plugins
```

---

## Plugins

### Taskmaster

Universal AI-powered task and backlog management. Drop into any project.

- **23 MCP tools** — tasks, epics, phases, dependencies, search, validation, session locking
- **Kanban viewer** — dark/light theme board on port 6800 with filtering, search, blocked-column toggle, and dynamic version badge
- **Session tracking** — auto-generated Done/Decisions/Issues changelog entries
- **Worktree isolation** — every task gets its own git worktree
- **Quality gates** — spec/plan check, code review, tests, build verification
- **TODO auditing** — scan codebase for TODO/FIXME/HACK, cross-reference with backlog
- **Phases** — sequential blocks of work for focus, one active at a time
- **Configurable storage** — `.claude/` (hidden) or project root (git-tracked)

**Requires:** [uv](https://docs.astral.sh/uv/)

**Skills:** `/init-taskmaster` `/start-session` `/pick-task` `/review-gate` `/end-session` `/check-todos`

### Guard Hooks

Safety guard hooks that block destructive CLI commands and sensitive file edits, with in-flow user approval.

- **Destructive command blocking** — prevents `rm -rf`, `git push --force`, `git reset --hard`, etc.
- **Sensitive file protection** — guards `.env`, credentials, and config files from accidental edits
- **User approval flow** — prompts for confirmation via `AskUserQuestion` before allowing risky actions

**Requires:** [jq](https://jqlang.github.io/jq/)

**Skills:** `/guard-hooks:install`

### UE5 Materials

Author Unreal Engine 5 materials from YAML specs. Two execution modes:

- **Live mode** — drives the Material Editor via MCPBridge at `localhost:13580` (`create_material` + `add_material_expressions` + `connect_material_pins`)
- **Clipboard mode** — emits T3D paste text for manual Ctrl+V into the Material Editor
- **HLSL Architect (Opus) + Node Generator (Sonnet)** agent chain for complex shader designs
- **Direct YAML path** for simple wiring of known nodes
- **Named Reroutes + column positioning** replace crash-prone Comment boxes

**Requires:** `pyyaml`

**Skills:** `/ue5-materials:author` `/ue5-materials:registry`

### Statusline

Pastel statusline for Claude Code with rate-limit bars, git status, context usage, update notifications, and session cost tracking. Bash + PowerShell.

**[Live Preview](https://gruku.github.io/claude-tools/statusline/)**

![Statusline Preview](statusline/screenshot.png)

#### Install

```bash
/plugin marketplace add Gruku/claude-tools
/plugin install statusline@gruku-tools
/statusline:setup
/reload-plugins
```

Then restart Claude Code so the new `statusLine` config is picked up.

The `/statusline:setup` skill detects your OS (Windows → PS1, macOS/Linux → Bash), checks prerequisites, and writes the `statusLine` block into `~/.claude/settings.json` pointing at the bundled script via `${CLAUDE_PLUGIN_ROOT}`. Marketplace updates ship new versions automatically — no re-install needed.

**Requires:** `jq` + `git` on Bash; nothing on Windows (PowerShell built-in, `git` recommended).

<details>
<summary>Manual install (standalone, without the plugin system)</summary>

##### macOS / Linux (Bash)

```bash
curl -o ~/.claude/statusline.sh https://raw.githubusercontent.com/Gruku/claude-tools/master/statusline/statusline.sh
chmod +x ~/.claude/statusline.sh
```

Add to `~/.claude/settings.json`:

```json
{ "statusLine": { "type": "command", "command": "~/.claude/statusline.sh" } }
```

##### Windows (PowerShell)

```powershell
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/Gruku/claude-tools/master/statusline/statusline.ps1" -OutFile "$env:USERPROFILE\.claude\statusline.ps1"
```

Add to `%USERPROFILE%\.claude\settings.json`:

```json
{ "statusLine": { "type": "command", "command": "powershell -NoProfile -File \"%USERPROFILE%\\.claude\\statusline.ps1\"" } }
```

Restart Claude Code.

</details>

#### Troubleshooting

**Raw escape codes visible** (e.g. `\033[0;33m` printed literally) — something between the script and the terminal is re-encoding ANSI. Don't paste the output into `PS1`/`PROMPT` manually. tmux/screen users: `set -g default-terminal "xterm-256color"` in `.tmux.conf`. Check that your terminal supports 24-bit truecolor (iTerm2, Windows Terminal, Ghostty, Alacritty, Kitty, WezTerm all do).

**"statusline: jq required"** — install jq: `brew install jq` / `sudo apt install jq` / `winget install jqlang.jq`.

**No rate-limit bars** — requires Claude Code v2.1.80 or later. Bars only appear when usage crosses display thresholds (80%+ for 5h, 80%+ for 7d) or on the first render of a new session.

---

## Marketplace Reference

### Structure

```
claude-tools/
├── .claude-plugin/
│   └── marketplace.json        # plugin catalog
├── plugins/
│   ├── taskmaster/             # AI task management
│   ├── guard-hooks/            # safety guard hooks
│   ├── ue5-materials/          # UE5 material authoring
│   └── statusline/             # pastel statusline (was standalone, now a plugin)
└── statusline/                 # legacy standalone source (preview + manual install)
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
