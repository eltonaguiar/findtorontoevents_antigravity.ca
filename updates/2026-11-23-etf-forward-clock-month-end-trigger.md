# R4b next action 1 — the ETF forward clock now fires at month-end on its own

**Date:** 2026-11-23 · **Owner:** buffy (freebuff) · **Paper only, zero capital, not advice**

## What was broken

`tools/etf_trend_forward_clock.py` could record a position, but **nothing called it**. Next
action 1 of `updates/2026-11-23-r4b-etf-trend-forward-clock.md` was "wire a month-end trigger so
a record is written on the last trading day of each month". Until that existed, the only row the
programme can still prove depended on a human remembering to run a script on the right evening —
and a clock that misses a month cannot be repaired afterwards, because backfilling a missed
month-end turns trial count 1 into many and inherits the 146-trial deflation debt the whole
design exists to avoid.

## What I changed

1. **`provable_month_end(dates)` in `tools/etf_trend_forward_clock.py`.** Returns the last
   session of the most recent *completed* month, or `None`. A month counts as complete only once
   the price cache contains a date in a **later** month, so the function cannot fire early, and
   it nominates the final date observed *within* its own month, so it cannot look ahead.
   Calendar-free on purpose: no exchange-holiday table to go stale, and it agrees with the
   calendar whenever the daily closes are contiguous across the boundary.

2. **`--month-end-check` mode.** Computes that date and records it; returns 0 and writes nothing
   when no month has completed, when the candidate predates `CLOCK_START`, or when the month is
   already in the ledger. Safe to run every day.

3. **`.github/workflows/etf-trend-forward-month-end.yml`.** Tue–Sat 22:40 UTC plus
   `workflow_dispatch`. Fails loudly if any of the frozen 20 series is missing, prints ledger
   state before and after, and commits only `reports/etf_trend_forward/positions.jsonl` with
   `[skip ci]`. **No push trigger** — a push trigger would let a code change re-invoke the
   recorder on a month already recorded.

## Verification

- `python3 -m pytest tests/test_etf_trend_forward_clock.py -q` → **15 passed** (10 pre-existing
  + 5 new: two on `provable_month_end`, one proving it never nominates a date in the incomplete
  month, one proving a pre-clock month is refused, one proving the completed month is recorded
  exactly once and a second run is a byte-identical no-op).
- Live run against today's cache: `latest provable month-end 2026-10-30 precedes CLOCK_START
  2026-11-23 -- waiting for the first month-end on or after the clock start`, exit 0. Correct:
  the cache ends 2026-11-19 and 2026-10-30 is the last session of an October that the
  pre-registration forbids recording.
- The 2026-10-31-is-a-Saturday case is pinned by a test, so the "last trading day" semantics are
  checked against a real calendar irregularity rather than assumed.

## What this does not fix

The first legitimate record is **2026-11-30** (a Monday), and `reports/etf_trend_forward/` is
still empty — the ledger has 0 records and the chain starts at genesis. The earliest possible
CONFIRM is ~60 monthly records, i.e. roughly 2031. Today's change only guarantees that the
records will exist; it proves nothing about the edge.
