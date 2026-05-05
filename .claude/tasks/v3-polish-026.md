---
notes: 'polish-013 audit confirmed live — recap receipts cards always render "0 ·
  No changes" while the narrative reads e.g. "Plan 3 landed in 6 milestones..." Either
  getSnapshotDiff is buggy or the fixture snapshot IDs do not resolve, with no error
  or tell. Investigate the snapshot-diff data path (server side: snapshot ingest,
  diff computation; client side: how recap.js calls/reads the diff). Recap is unreliable
  until this is fixed. Pairs with v3-polish-001 (build picker) — a working picker
  showing broken receipts is still a broken recap.'
id: v3-polish-026
title: Recap snapshot/diff plumbing — receipts contradict narrative
---
