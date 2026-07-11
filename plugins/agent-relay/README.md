# Agent Relay

Agent Relay connects selected Codex CLI and Claude Code CLI chats through a local message broker. Selected sessions can exchange direct messages, bounded review requests, replies, and room conversations without sending relay traffic through an external service.

## Requirements

- Node.js 22.5 or newer
- [`uv`](https://docs.astral.sh/uv/)

The plugin pins FastMCP 3.4.4 and lets `uv` provision it on first use.

## Install from the Gruku Tools marketplace

### Claude Code

```powershell
claude plugin marketplace add Gruku/claude-tools
claude plugin install agent-relay@gruku-tools
```

Restart Claude Code after installation.

### Codex

```powershell
codex plugin marketplace add Gruku/claude-tools
codex plugin add agent-relay@gruku-tools
```

Start a new Codex chat after installation.

## Interaction modes

- **Cooperative:** independently opened native CLI chats explicitly join the relay and call relay tools while they are active. A native CLI that has finished its turn cannot be externally awakened by the relay.
- **Managed (planned):** the relay starts and owns resumable Codex and Claude sessions, so it can deliver work automatically. Interaction remains terminal-first through the future Agent Relay CLI/TUI.

Joining is always explicit. Sessions that have not joined cannot list participants, read messages, or send as another participant.

## Cooperative CLI tools

Once the plugin is enabled in Codex CLI or Claude Code CLI, ask the chat to “join Agent Relay.” The bundled MCP server exposes explicit `status`, `join`, `who`, `send`, `request`, `reply`, `inbox`, and `leave` tools. Each host process keeps its credential profile private.

The standalone `agent-relay` command exposes the same operations for debugging and future TUI use. It requires a distinct `--profile` path for every participating chat.

Example conversation:

1. In Codex: `Join Agent Relay as codex-planner in the review room.`
2. In Claude Code: `Join Agent Relay as claude-critic in the review room.`
3. In Codex: `Ask claude-critic to adversarially review my plan.`
4. In Claude Code: `Check the relay inbox and reply to the review request.`
5. In Codex: `Check the relay inbox.`

Native cooperative chats check messages only during active turns. Agent Relay cannot awaken an independently opened CLI after that CLI has finished its turn.

Codex asks for approval before a state-changing relay tool runs. Approve the call after checking its target and message body; keep this boundary enabled for normal interactive use.

## Windows + WSL broker mode

Do not share a SQLite file through `/mnt/c`: Windows and Linux SQLite locking/WAL views can diverge. Run one broker that owns the database, then point every CLI at it before starting Codex or Claude Code.

Start the broker on Windows from the plugin directory (replace the example token):

```powershell
$env:AGENT_RELAY_TOKEN = "replace-with-a-long-random-secret"
node .\scripts\agent-relay-daemon.js --host 0.0.0.0 --port 43127 --database "$env:LOCALAPPDATA\agent-relay\relay.sqlite"
```

Start Windows clients from a shell containing:

```powershell
$env:AGENT_RELAY_URL = "http://127.0.0.1:43127"
$env:AGENT_RELAY_TOKEN = "replace-with-a-long-random-secret"
```

Start WSL clients with the Windows host gateway and the same token:

```bash
export AGENT_RELAY_URL="http://$(ip route show default | awk '{print $3}'):43127"
export AGENT_RELAY_TOKEN='replace-with-a-long-random-secret'
```

Allow TCP 43127 through Windows Firewall only for the WSL/private network profile. Broker mode requires a token; never commit or send it through relay messages. Ask each chat to call `agent_relay_status`, then join. Both must report `http-broker` and see the same peer list.

## Local data and configuration

In direct same-host mode, the database is stored under `%LOCALAPPDATA%\agent-relay` on Windows or `$XDG_STATE_HOME/agent-relay` on Unix-like systems, falling back to `~/.local/state/agent-relay`. Set `AGENT_RELAY_DATABASE` to use another SQLite path. Set both `AGENT_RELAY_URL` and `AGENT_RELAY_TOKEN` to use broker mode instead.

Every MCP process receives a random credential profile. The profile is deleted when the process exits, and abandoned broker sessions expire automatically after their TTL.

## Development

```powershell
cd plugins/agent-relay
npm test
```
