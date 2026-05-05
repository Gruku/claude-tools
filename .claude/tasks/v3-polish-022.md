---
notes: No code change needed — premise was wrong. _make_server already uses ThreadingHTTPServer
  (since commit 107e6f3, "Fix viewer port collision on Windows with exclusive socket
  binding") and _ExclusiveServer subclasses it for the production path. The 6 false-positive
  "Failed to fetch" findings during the polish-013 audit were therefore not caused
  by single-threaded serving. The most likely real cause was Chrome MCP / browser-side
  resource pressure (10 agents each holding a deep accessibility tree + javascript_tool
  calls in flight) or transient socket exhaustion under burst load. If parallel-agent
  audits keep flaking, the next investigation should be a thread-pool / connection-pool
  cap, not the underlying server class. Closed as already-done.
id: v3-polish-022
title: Migrate dev server to ThreadingHTTPServer (test-infra blocker)
---
