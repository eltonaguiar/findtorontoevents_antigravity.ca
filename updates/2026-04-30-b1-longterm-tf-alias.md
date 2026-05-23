# B1 — LONG-TERM Timeframe Dropdown Alias — 2026-04-30

**Queue item:** B1 from `reports/REMAINING_ACTION_ITEMS_2026_04_30.md`  
**Risk:** LOW (additive UI option; no logic change for existing filters)

## What changed

**`audit_dashboard/template.html`** — 2 locations:

1. Added `<option value="LONG_TERM">Long-Term (1y+)</option>` to `<select id="f-timeframe">` (line 1024).

2. Updated `matchFilter()` to treat `f.timeframe === 'LONG_TERM'` as a `pick_type` filter
   (matches picks where `pick_type === 'long_term_value'`) rather than a `trade_timeframe`
   enum filter.  All other timeframe values continue to filter on `trade_timeframe` as before.

## Behaviour

Selecting "Long-Term (1y+)" from the Timeframe dropdown on `/audit` now shows:
- All active picks whose `pick_type` is `long_term_value` (UEPS + long-term value screener picks)
- These are the picks emitted by PR #547 (UEPS active-picks sync) and the value screener

The option is additive — existing SCALP/INTRADAY/SWING/POSITION options are unchanged.

## Why not `trade_timeframe === 'POSITION'`?

`POSITION` is the existing enum for 7d+ holds.  Long-term value picks (1y+ horizon) use
`pick_type = long_term_value`, not a separate `trade_timeframe` value.  Aliasing to
`pick_type` avoids polluting the `trade_timeframe` enum while making UEPS picks
discoverable via the standard filter UI.
