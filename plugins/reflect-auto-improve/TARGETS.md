# Reflect Targets

Known projects this plugin can reflect on. Used by `reflect-auto-improve:*` skills to validate `--project <path>` args and to suggest defaults.

| Project | Path | Notes |
|---|---|---|
| CodeMaestro | `C:\Users\gruku\Files\Work\CodeMaestro` | Primary Taskmaster consumer. Default target for `retro`. Houses CodeMaestro API, Desktop, UE, parsers, and concepts subprojects. |
| Playable Ad pipeline | _path TBD — fill in at first harvest run_ | Pipeline codification target. Pain-points → workflow drafts feed back as new skills/commands. |
| claude-tools | `C:\Users\gruku\Files\Claude\claude-tools` | This repo. Primary target for `plugin-audit`. |

## Adding a Target

1. Add a row above.
2. Optionally add a `.reflect/` directory in the target project if it lacks `.taskmaster/` — reports fall back to `.reflect/retros/` there.
3. Re-run `reflect-auto-improve:reflect` to confirm routing.
