---
notes: 'polish-013 audit found .spine-node--active .spine-node-circle uses animation:
  spine-active-pulse 1.6s ease-in-out infinite with transform: scale(1.11) — continuous
  geometric scale on a live element, an explicit project rule violation (CLAUDE.md
  "no motion on hover" extended to "no transform-based motion on solid surfaces").
  Replace with opacity or stroke-color pulse. Pairs with v3-polish-008.'
id: v3-polish-025
title: Fix spine-active-pulse — replace transform scale with opacity/stroke
---
