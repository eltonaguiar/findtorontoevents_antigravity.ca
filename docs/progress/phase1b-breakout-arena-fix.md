# Phase 1B: Breakout Arena Fix - Progress

## Task 2: Unfreeze Breakout Arena C (Stale Picks)

### Status: COMPLETE

### Findings

Upon reading `breakout_arena/approach_c_spike_reverse/scanner.py`, the situation is different from what the task description assumed:

1. **`validate_active_picks()` IS already called** on line 1055 of `scan()` -- it was NOT missing
2. **`MAX_HOLD_HOURS` already exists** at line 56, set to 96 (4 days)
3. The existing validation is comprehensive: TP/SL checks, trailing stops, HWM tracking, multi-exchange price fallback (Binance + OKX + OHLCV)

### Action Taken

- **Changed `MAX_HOLD_HOURS` from 96 to 48** -- tighter time exit prevents picks from going stale for 4 days
- **Did NOT add duplicate inline validation** -- the existing `validate_active_picks()` function (lines 824-916) is MORE comprehensive than the proposed code (it includes trailing stops, HWM, multi-exchange fallback). Adding inferior duplicate logic would be a regression.

### Deviation: [Rule 1 - Bug Prevention] Avoided adding duplicate validation

The task assumed `validate_picks` was not imported/called, but `validate_active_picks()` is called on line 1055. Adding the proposed inline code would create duplicate TP/SL checking without the trailing stop logic, potentially closing picks differently than the primary validator. Instead, only the `MAX_HOLD_HOURS` reduction (96 -> 48) was applied, which achieves the goal of preventing stale picks.

### Syntax Check: PASSED
