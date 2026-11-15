# 2026-11-15 pick failure root cause

## What was broken

Open monitoring cards failed QA because exit fields were required before a close. The forward tracker mixed percent and fraction, restarted eliminated strategies, and could kill on a bogus cost ratio. Mutual-fund screening rejected Admiral share classes for a $1000 minimum. Trend cards were going to be TIME_EXIT'd by the resolver at 96h, which cannot test a 63-day signal. XLV/LLY/SHY also entered on the same bar as the signal.

## What changed

- `alpha_engine/pick_failure_root_cause.py` — per-class success criteria and labels. No price fetch.
- QA skips exit fields on OPEN picks and does not treat a later session's close as a same-bar error.
- Forward tracker recomputes from an append-only ledger and refuses to restart an eliminated id.
- MF minimum is $3000. Missing min/AUM is insufficient, not a zero.
- Resolver uses `max_hold_hours` when it is between 24h and 90 days.
- Wired cards stamped with horizon, same-bar leakage, and `promotable=false`.

## Verification

`tests/test_pick_failure_and_tracker.py`
