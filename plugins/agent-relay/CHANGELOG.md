# Changelog

## 0.2.0

- Add an authenticated HTTP broker so Windows, WSL, and other hosts share one authoritative relay.
- Keep SQLite private to the broker process and retain direct SQLite mode for same-host development.
- Add broker diagnostics through `agent_relay_status` and document cross-OS setup.

## 0.1.0

- Scaffold the dual-host Codex and Claude Code plugin.
- Define the local relay core for explicitly joined sessions.
- Add marketplace installation metadata, pinned FastMCP startup, and release documentation.
- Resolve the Codex MCP server from a plugin-relative working directory while retaining Claude Code's native plugin-root configuration.
