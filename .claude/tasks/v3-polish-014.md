---
notes: 'Self-XSS confirmed live on lesson-detail and issue-detail (polish-013): crafted
  URL like /v3/#/issue/<img src=x onerror=...> injects real HTML elements via root.innerHTML
  template. Same class likely exists on task-detail, recap-by-id, and any other detail
  screen using template-literal innerHTML for missing-resource paths. Fix: sweep all
  error-state renders for user-supplied identifiers and switch to textContent (or
  proper escaping). Must land before any release work.'
id: v3-polish-014
title: Sanitize ${id} in not-found innerHTML across detail screens (security)
---
