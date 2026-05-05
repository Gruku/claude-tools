---
notes: 'User feedback 2026-05-02 — tokens and color palette want another pass. tokens.css
  currently exposes --ink/--ink-2/--ink-3/--ink-4, --accent, --accent-2, --accent-soft,
  --accent-blue, --accent-edit, --accent-green, --gold/--amber, plus surface stepping
  (--bg-shell/-panel/-card/-deep) and per-screen overrides. Audit for: (1) redundant
  or near-duplicate tokens (--accent vs --accent-blue vs --accent-edit), (2) semantic
  vs raw naming (e.g., --warn, --critical, --resolved) so callers express intent,
  (3) palette coherence across surfaces (pip-active blue vs auto-status pill blue
  vs edit-mode chrome blue should harmonize). Cross-reference per-screen CSS for phantom
  variables (history of c949b4c, 4704964 fixes).'
id: v3-polish-012
title: Design tokens and color palette audit
---
