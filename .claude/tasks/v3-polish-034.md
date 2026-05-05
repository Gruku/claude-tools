---
notes: 'The demo page at http://127.0.0.1:8765/v3/dev/edit-demo only renders the `<h1>Edit
  components</h1>` heading — none of the per-renderer demo sections (TextField, MdField,
  EnumSelect, NumberField, DateField, ChipInput) appear despite their `*-demo.js`
  files being imported into `edit-demo.js`.


  Likely cause: timing or path issue in the registerDemo() pattern. `edit-demo.js`
  imports demo files, each demo file calls `registerDemo(name, fn)` to push into a
  `sections` array, then `edit-demo.js` iterates the array at module bottom. Worth
  checking:

  - Are demo file imports placed BEFORE the for-loop in `edit-demo.js`? (Plan comment
  says they should be.)

  - Do the demo files actually `import { registerDemo } from ''../../../dev/edit-demo.js''`
  and call it at module top level?

  - Browser console errors? (open devtools at /v3/dev/edit-demo)


  This is dev-only tooling — doesn''t block any feature delivery and isn''t in the
  user-facing v3 viewer. Discovered 2026-05-05 while smoke-testing v3-edit-004 (ChipInput).
  Renderer unit tests all pass for tasks 1-4 (4/4, 10/10, 19/19, 8/8) so the implementations
  themselves are sound; bug is in the demo wiring.'
id: v3-polish-034
title: Edit-components demo page renders only header — demo sections never mount
---
