---
notes: 'polish-013 audit confirmed task-detail-document.js and task-detail-graph.js
  add td-page / td-page-A / td-page-B classes to shared #screen-mount but never remove
  them on cleanup. Router does replaceChildren but does not reset classList, so classes
  leak — navigating from task-detail to /auto stacks task-detail padding on top of
  .auto-page padding and pollutes specificity for subsequent screens. Two fix paths:
  (a) add classList.remove in each cleanup closure, or (b) better, have router reset
  className to "screen-mount" before each mount.'
id: v3-polish-024
title: Cleanup td-page / td-page-A classes on task-detail unmount
---
