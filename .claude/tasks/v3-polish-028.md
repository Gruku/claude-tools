---
notes: 'Repro: with no auto-mode session active, the kanban top still shows "Auto-mode
  · 1 running" with a session timer ("running 3d") and a task pill. Visible whenever
  an auto-state document persists from a prior run.


  Root cause: auto-mode-strip.js:64 hide condition is `!autoState || !autoState.mode
  || !runs.length`. It never inspects autoState.stopped, autoState.completed_at, or
  any "is actively running" predicate. Any persisted auto-state document with a populated
  cursor passes the gate forever — even after the session is stopped or crashed.


  Observed shape on /api/auto/state for the .fixture-kanban seed: includes `stopped:
  false`, `pending: [...]`, no `completed_at`, mode: "walk", started_at much earlier.
  The shape lets us define what "running" means; the strip just doesn''t check it.


  Fix: define a single `isRunning(autoState)` predicate (e.g. `mode && !stopped &&
  !completed_at && pending.length > 0`, optionally with a heartbeat-freshness check
  so a crashed session doesn''t appear live forever). Use it everywhere the strip
  / live-dot / sidebar pill decides whether to show "running" UI.


  Note: side dev server runs against .fixture-kanban which deliberately seeds a "walk"
  auto-state for visual fixture coverage. That''s correct for fixtures — the bug is
  the strip''s logic, not the fixture.


  Possible overlap with v3-polish-006 (slim down auto-mode header) — but 006 targets
  the auto-mode page header, this is the kanban-top strip. Worth a quick check whether
  both share the same isRunning predicate after fix.</notes>

  </invoke>'
review_instructions: With the bundled .fixture-kanban (which seeds a "walk" session)
  the strip should still appear — that's intentional fixture behavior, called out
  in the bug notes. To verify the fix, run a real auto-mode session, stop it, and
  confirm the kanban-top strip + topbar auto-status pill + sidebar live-dot all hide.
  Per-card live highlight on the cursor task should also disappear. Predicate `isAutoRunning(autoState)`
  (mode && !stopped && !completed_at && pending.length > 0) is now applied uniformly
  across all four sites.
id: v3-polish-028
title: Auto-mode strip shows "Auto-mode · N running" for stopped/abandoned sessions
---
