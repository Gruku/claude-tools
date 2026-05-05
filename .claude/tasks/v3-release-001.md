---
notes: backlog_migrate_v3 exists in worktree backlog_server.py:1303 with @mcp.tool()
  decorator but is NOT exposed by running MCP server (1.11.1). Without this, users
  cannot upgrade their existing v2 backlogs to v3 — blocker for release. Verify the
  build/packaging picks it up and that ToolSearch surfaces it after a fresh install.
id: v3-release-001
title: Verify backlog_migrate_v3 MCP tool ships in 1.12 build
---
