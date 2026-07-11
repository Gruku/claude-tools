# Changelog

## 0.3.0

- Add persistent user-level broker configuration discovered automatically by the CLI and MCP adapter.
- Add `setup`, one-time `pair`, `status`, and `doctor` workflows as the shared operational surface for the future TUI.
- Start the broker in the background during setup and advertise reachable pairing endpoints.

## 0.2.0

- Add an authenticated HTTP broker so Windows, WSL, and other hosts share one authoritative relay.
- Keep SQLite private to the broker process and retain direct SQLite mode for same-host development.
- Add broker diagnostics through `agent_relay_status` and document cross-OS setup.

## 0.1.0

- Scaffold the dual-host Codex and Claude Code plugin.
- Define the local relay core for explicitly joined sessions.
- Add marketplace installation metadata, pinned FastMCP startup, and release documentation.
- Resolve the Codex MCP server from a plugin-relative working directory while retaining Claude Code's native plugin-root configuration.
