# Semantic Limit Pips with Budget-Aware Coloring

**Date:** 2026-04-02
**Component:** StatusLine plugin (`statusline/statusline.ps1`, `statusline/statusline.sh`)

## Summary

Replace the hardcoded 5-pip limit bars with semantically meaningful pip counts — 5 pips for the 5-hour window (1 per hour) and 7 pips for the 7-day window (1 per day). Add budget-aware coloring that shifts filled pips toward warm/red when the user is consuming their limit faster than the elapsed time would suggest.

## Motivation

The current design uses 5 pips for both bars, which is arbitrary for the 7-day window. Making pip counts match time units gives each pip a concrete meaning ("I've used one day's worth") and makes the bars self-documenting. The overspend coloring adds a pace signal — at a glance, you know whether your consumption rate is sustainable or if you'll hit the cap before the window resets.

## Design

### Pip Counts

| Bar       | Pips | Each pip represents | Identity color        |
|-----------|------|---------------------|-----------------------|
| 5-hour    | 5    | 1 hour              | Sage (135, 180, 160)  |
| 7-day     | 7    | 1 day               | Mauve (185, 140, 160) |

The `$barW` variable becomes per-bar: `$fhBarW = 5`, `$sdBarW = 7`.

### Budget Line Calculation

The budget line is the expected usage position given how far into the current window we are.

```
elapsed = window_size - (resets_at - now)
```

A pip is "within budget" if its 0-based index is less than `floor(elapsed)`. In other words, the number of budget-earned pips equals `floor(elapsed)`.

For the 5-hour bar:
- `elapsed_hours = 5 - ((resets_at - now) in hours)`, clamped to 0..5
- Pips 0..`floor(elapsed_hours) - 1` are within budget
- Example: 1.5 hours elapsed → pip 0 is within budget, pips 1-4 past budget if filled

For the 7-day bar:
- `elapsed_days = 7 - ((resets_at - now) in days)`, clamped to 0..7
- Pips 0..`floor(elapsed_days) - 1` are within budget
- Example: 3.2 days elapsed → pips 0-2 within budget, pips 3-6 past budget if filled

If `resets_at` is unavailable or in the past, the budget line defaults to pip 0 (all filled pips are "past budget"), which is a safe fallback — it just means every pip could show overspend color, which is correct since we can't determine pace.

### Per-Pip Coloring

For each filled pip (where usage percentage >= pip's start threshold):

1. **Within budget** (`pip_index < floor(elapsed)`) — identity color (sage or mauve), unchanged from today.
2. **Past budget** (`pip_index >= floor(elapsed)`) — warm gradient based on distance past budget:
   - `budget_count = floor(elapsed)`
   - Interpolation factor: `t = (pip_index - budget_count) / (total_pips - budget_count)`
   - Color interpolation: identity → amber (235, 195, 80) → red (210, 95, 85)
     - `t` in 0.0–0.5: interpolate identity → amber
     - `t` in 0.5–1.0: interpolate amber → red

For the **leading pip** (partially filled), the existing brightness interpolation still applies. The base color for brightness calculation is chosen based on whether the pip is past the budget index or not.

For **empty pips**, dim color (50, 48, 45) is unchanged.

### Percentage Text Overlay

Behavior unchanged — activates at 80%+ usage or on session start.

- 5-hour bar: centered across 5 character slots (same as today)
- 7-day bar: centered across 7 character slots (wider canvas, more room)
- Text color: `Get-LimitGradColor` at current usage percentage
- Flanking pips (not covered by text characters) render with their normal coloring logic

### Reset Time Visibility

| Bar    | Usage threshold | Time proximity threshold |
|--------|----------------|--------------------------|
| 5-hour | >= 75%         | Within **30 minutes** (was 15) |
| 7-day  | >= 80%         | Within 4 hours (unchanged)     |

### Layout Impact

Line 2 grows by 2 characters due to the wider 7-day bar. No other layout changes. The existing line 2 structure accommodates this — git info + limit bars + reset times + optional extras have room.

## Build-LimitBar Function Changes

The function signature gains a `window_size` parameter (or the bar width is passed directly, which already encodes this):

```
Build-LimitBar(pct, barWidth, barRGB, budgetCount, forceShowPct)
```

Key changes:
1. `$barW` is now a parameter, not a global constant
2. `$budgetCount` (`floor(elapsed)`) is computed by the caller from `resets_at`
3. Pip coloring branch: if `pip_index >= budgetCount`, use warm gradient; else use `barRGB`
4. Warm gradient function: new helper or inline logic that interpolates identity → amber → red based on distance past budget

## Edge Cases

- **Budget index >= total pips** (e.g., elapsed 5+ hours in a 5-hour window): all filled pips are within budget. No overspend coloring. This is correct — you've "earned" all the pips by time alone.
- **`floor(elapsed) = 0`** (start of window or missing data): no pips are within budget, so all filled pips show overspend coloring. Correct — no time has elapsed, no budget earned.
- **Usage = 0%**: all pips empty, no coloring applies.
- **Usage = 100%**: all pips filled; pips past budget show maximum warm gradient.

## Files to Modify

1. `statusline/statusline.ps1` — primary implementation (Windows/active)
2. `statusline/statusline.sh` — bash mirror (macOS/Linux)
3. `~/.claude/statusline.ps1` — installed copy (synced from repo)
