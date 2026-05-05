---
notes: 'Auto-install the PreCompact hook that runs `taskmaster snapshot --quiet` before
  context compaction (so post-compact recap reflects pre-compact state). Update init-taskmaster
  skill to: (1) add the hook to settings.json non-destructively (merge with existing
  PreCompact entries), (2) add .taskmaster/snapshots/ and .taskmaster/auto/ to .gitignore,
  (3) verify the snapshot CLI command runs end-to-end. Settings snippet in design-v3-narrative-continuity.md
  §5.'
id: v3-skills-006
title: PreCompact hook + init-taskmaster v3 retrofit
---
