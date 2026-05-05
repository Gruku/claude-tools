---
notes: 'Verify and complete the MCP tool surface for handover reads. Python helpers
  exist in taskmaster_v3.py (read_handover, list_handover_ids, latest_handover_id)
  but per v3-release-001 there is a known gap between Python helpers existing and
  MCP tools being exposed by the running server. Scope: (1) verify backlog_handover_get(id)
  is exposed and returns frontmatter + body, (2) add backlog_handover_list(task_id?,
  session_kind?, since?, limit?) thin wrapper if missing — needed by pick-task retrofit
  (filter by task_id) and start-session retrofit (filter by session_kind for context-handoff
  hint), (3) add backlog_handover_latest() convenience tool — needed by start-session
  retrofit. Smoke-test all three from a Claude session against the v3 fixture backlog.
  Pairs thematically with v3-release-001 (both are MCP exposure verifications). Blocks
  v3-skills-007 and v3-skills-008 retrofits.'
id: v3-skills-015
title: Handover read MCP tool surface (get/list/latest)
---
