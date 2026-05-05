---
notes: 3 dashboard.spec.js tests fail because they query .dash-edit-toggle which no
  longer exists post-redesign (edit toggle is now in the topbar via createEditMode).
  Plus 3 sessions specs failing on [data-role=view-toggle] .seg from the v2 era. Update
  selectors.
id: v3-polish-005
title: Fix pre-existing dashboard test failures
---
