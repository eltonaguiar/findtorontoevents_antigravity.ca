# Sports Betting Date Bucketing Fix (Midnight EST)

## Issue
After midnight, picks for the current EST date (example: May 4) could appear as a plain date label instead of `TODAY`, which made them look like they belonged in a "Later" bucket.

## Root Cause
- Frontend timezone conversion in `live-monitor/sports-betting.html` used:
  - `new Date(d.toLocaleString('en-US', { timeZone: 'America/New_York' }))`
- That re-parses a locale-formatted string, which is browser-locale dependent and can misinterpret month/day.
- Backend fallback date in `live-monitor/api/sports_picks.php` used server-local `date('Y-m-d')`, which can drift around UTC/EST midnight boundaries.

## Fixes Applied
1. Frontend deterministic EST conversion:
   - Updated `_toEST()` to use `Intl.DateTimeFormat(...).formatToParts()` and reconstruct a `Date` from numeric components.
   - Kept a fallback path for older browsers.
2. Frontend simplification:
   - `_estDateStr()` now consistently routes through `_toEST(d)`.
3. Backend explicit EST day default:
   - Replaced `date('Y-m-d')` with `DateTime('now', new DateTimeZone('America/New_York'))->format('Y-m-d')`.

## Evidence / Verification
- Runtime logic check (local):
  - `node tmp/verify_sports_date_logic.js`
  - Results:
    - `fmtGameDate('2026-05-04') => TODAY`
    - `fmtGameDate('2026-05-05') => TOMORROW`
    - `fmtGameDate('2026-05-03') => YESTERDAY`
    - `fmtGameDate('', '2026-05-04T15:30:00Z') => TODAY`
  - Exit code: `0`
- Regression pass for changed area:
  - `npx playwright test tests/sports_betting_js_errors.spec.js --project="Desktop Chrome"`
  - `4 passed, 1 failed` (failure is existing Pick History API expectation; unrelated to date label bucketing logic changed here).

## Files Changed
- `live-monitor/sports-betting.html`
- `live-monitor/api/sports_picks.php`
- `updates/2026-05-04-sports-betting-date-bucketing-fix.md`
