---
notes: polish-013 audit found "â€"" instead of "—" on codex review notes and handover
  quotes on task-detail (verified on v3-050 spec-review and v3-031 handover quote).
  UTF-8 file decoded as Latin-1 somewhere in the data path. Confirmed NOT viewer-wide
  — lesson-detail and issue-detail render em-dashes correctly. Likely the response
  Content-Type or the file-read encoding for the specific subtree feeding quoted human
  text on task-detail. Probably one backlog_server.py line (charset on response, or
  encoding on the read).
id: v3-polish-021
title: Fix mojibake on task-detail quoted text (UTF-8 / Latin-1)
---
