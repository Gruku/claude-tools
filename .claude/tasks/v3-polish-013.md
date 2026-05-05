---
notes: 'DONE 2026-05-02. Walkthrough of all 11 screens at runtime produced 169 findings,
  captured per-screen at plugins/taskmaster/docs/v3-polish-013/<screen>.md with synthesis
  at synthesis.md. Surfaced 13 new polish tasks (014-026) and re-prioritized the existing
  12. Top headline findings: self-XSS via unsanitized ${id} on detail screens (014,
  critical), recap routing contract broken (015), dead/stub buttons across 5+ screens
  (016), single-threaded HTTPServer dies under parallel agent load (022, blocks reliable
  local testing). Process note: first parallel-agent pass crashed the server; 6 screens
  were re-audited sequentially on a fresh server.'
id: v3-polish-013
title: End-to-end UI/UX review of the whole viewer experience
---
