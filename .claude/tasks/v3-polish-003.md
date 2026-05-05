---
notes: 'polish-013 audit confirmed at depth — .td-rail-h (task-detail: always-visible,
  no close button) and .rr-h (sessions: overlay, dismiss-on-click + close + Escape)
  are two architecturally different rail systems sharing one source file. Naming makes
  them look like a typo or near-variant; they are not. Either rename to surface the
  distinction (e.g., .tm-rail-pinned-h vs .tm-rail-overlay-h) or unify on one rail
  pattern and pick which screens get pinned vs overlay. Worth one short brainstorm
  pass.'
id: v3-polish-003
title: Rename or unify rail systems (.td-rail-h vs .rr-h)
---
