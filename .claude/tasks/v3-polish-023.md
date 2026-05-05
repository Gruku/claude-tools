---
notes: 'polish-013 audit found --sev-critical / --sev-high / --sev-medium / --sev-low
  defined inside .issues { ... } scope. Verified live: getComputedStyle("#issue-detail
  .id-sev").color is the same gray on Critical / High / Medium issues — the glyph
  (hardcoded inline) is colored, but the text label is flat gray on every severity,
  killing the prominence the design intended. Fix: hoist the four --sev-* vars to
  :root in tokens.css.'
id: v3-polish-023
title: Hoist --sev-* CSS vars to :root (issue-detail labels flatten to gray)
---
