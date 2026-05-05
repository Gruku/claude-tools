---
notes: 'polish-013 audit found the only recap nav control is silently broken. Topbar
  ‹ button updates URL to #/recap/SES-0002 (path-segment) but recap.js reads only
  ?id= (query-string), so params.id is undefined and the screen falls back to most-recent
  recap. Pick one form (recommend path-segment per /v3/#/task/<id> convention), update
  both the link target and the screen reader. Prerequisite for v3-polish-001 (build
  picker) — picker rebuild needs a working routing contract first.'
id: v3-polish-015
title: Fix recap routing contract (path-segment vs query-string mismatch)
---
