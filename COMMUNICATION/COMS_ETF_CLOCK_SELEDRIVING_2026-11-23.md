R4b is now self-driving: month-end trigger + append-only price feed (freebuff, 2026-11-23)
Commits 0266a3067ed (trigger) and the refresh commit on pr/h201-pit-universe-2026-11-23.

WHY I TOUCHED THIS AT ALL. R4b (the ETF trend forward clock) is the only row in the programme
that can still produce a result that means anything, because it was tested once and forward. It
had two holes that would have made it produce nothing:

1. NOTHING INVOKED THE RECORDER. The script could write a position; no scheduler called it. A
   human had to remember to run it on the right evening. A missed month-end is UNREPAIRABLE here
   - backfilling it converts trial count 1 into many and inherits the 146-trial deflation debt the
   design exists to avoid. So the clock would have died of a missed Tuesday, not of a bad edge.

2. NOTHING REFRESHED THE PRICE CACHE. The clock reads data/cache/asset_class_review/<SYM>_5y.csv.
   Those files are committed and were last touched at 2026-11-19. tools/refresh_daily_prices_yf.py
   writes MySQL, not this cache; asset_class_edge_review.load_bars() only downloads when a file is
   ABSENT, never when it is stale. So even a working trigger would have re-read the same stale CSV
   every night and reported "up to date" forever.

WHAT I BUILT
* provable_month_end(dates): last session of the most recent COMPLETED month. A month is complete
  only once the cache holds a date in a LATER month, so it cannot fire early; it nominates the
  final date observed within its own month, so it cannot look ahead. Calendar-free on purpose -
  no exchange-holiday table to rot. Pinned by a test on 2026-10-31-is-a-Saturday.
* --month-end-check: records that date, or exits 0 writing nothing (no completed month / candidate
  predates CLOCK_START / month already recorded). Safe for a daily cron.
* tools/etf_trend_price_refresh.py: append-only refresh of the 20 frozen tickers. Never rewrites a
  cached row - the hash-chained ledger already committed to signals computed from those bars, so
  revising one would make past decisions unverifiable. Takes its universe FROM the clock module,
  so one list, not two, and a refresh cannot widen the trial. Any ticker that fails exits non-zero
  via ::error:: rather than handing the clock a partial universe to rank.
* .github/workflows/etf-trend-forward-month-end.yml: Tue-Sat 22:40 UTC + dispatch. install ->
  refresh -> guard (all 20 series present) -> stats -> check -> stats -> commit the ledger only.
  NO push trigger: a push trigger would let a code change re-invoke the recorder on a month
  already recorded.

VERIFIED: 23 tests pass offline (15 clock + 8 refresh). The refresh tests prove existing bytes are
preserved exactly (after.startswith(before)), a second run appends 0 and is byte-identical, a dry
run writes nothing, a stale download cannot roll the cache backwards, and a download failure
propagates instead of appending partial data. YAML parses and step order is confirmed.

STATE RIGHT NOW: ledger has 0 records; live check correctly refuses with "latest provable
month-end 2026-10-30 precedes CLOCK_START 2026-11-23". First legitimate record: 2026-11-30
(Monday). Earliest possible CONFIRM: ~60 monthly records, i.e. roughly 2031.

CAVEAT I WANT ON THE RECORD: the live Yahoo fetch from a runner is the one thing I cannot verify
from this box - the offline tests cover the merge logic, not the network. That is why the workflow
fails LOUDLY on a bad fetch. A missed month-end is recoverable within the month; a silent one is
not.

Adjacent status, unchanged: H-201 remains NOT_PROVEN (3-4 trials short, 137-327 forward days short
per the corrected DSR), and the H-201 pod is 15/20 on its gate, excess -836 bp, data-bound at
2026-11-20. The pod's 20-day gate is a clock sanity check, not a significance test.
