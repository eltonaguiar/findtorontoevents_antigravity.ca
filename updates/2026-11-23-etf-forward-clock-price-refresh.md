# R4b follow-through — the clock was also missing a price feed

**Date:** 2026-11-23 · **Owner:** buffy (freebuff) · **Paper only, zero capital, not advice**

## What was still broken after the month-end trigger

Wiring `--month-end-check` (previous block) made the recorder run itself, but the clock reads
`data/cache/asset_class_review/<SYM>_5y.csv`, and **nothing in the repo kept those files
current**. The cache's newest bar is 2026-11-19. A month-end trigger that never sees a new bar
is not a trigger — it would have re-read the same stale CSV every evening and reported "up to
date" forever, and because the ledger is append-only the missing months could never be
recovered.

I found no existing refresher for this cache: `tools/refresh_daily_prices_yf.py` writes MySQL
`daily_prices`, and `tools/asset_class_edge_review.py:load_bars()` only downloads when a file is
absent, never when it is stale.

## What I added

**`tools/etf_trend_price_refresh.py`** — append-only refresh for the 20 frozen tickers.

- **Takes the universe from `etf_trend_forward_clock.UNIVERSE`.** One list, not two, so a refresh
  can never quietly widen the trial.
- **Appends only dates strictly later than the cache's last date.** An existing row is never
  rewritten, and a stale download cannot roll the cache backwards. This matters beyond
  tidiness: the hash-chained ledger already committed to signals computed from those bars, so
  revising one would make previously-recorded decisions unverifiable against the data.
- **Fails loudly.** Any ticker that cannot be refreshed exits non-zero with `::error::` rather
  than leaving a partial universe for the clock to rank.
- `--dry-run` reports what would be appended and writes nothing.

**Workflow wiring** — `.github/workflows/etf-trend-forward-month-end.yml` now installs
`yfinance`/`pandas` and runs the refresher before the month-end check. The refreshed CSVs are
deliberately **not** committed: this is a research cron, and pushing daily cache churn into files
the other desks' tools read is not its job.

## Verification

- `python3 -m pytest tests/test_etf_trend_price_refresh.py -q` → **8 passed**, offline:
  revisions and duplicates dropped, existing bytes preserved exactly (`after.startswith(before)`),
  second run appends 0 and leaves the file byte-identical, dry-run writes nothing, a stale
  download cannot roll the cache back, and a download failure propagates instead of appending
  partial data.
- `test_universe_is_taken_from_the_clock_not_duplicated` pins the single-source-of-truth claim.
- `python3 -m pytest tests/test_etf_trend_forward_clock.py -q` → 15 passed (unchanged).
- Workflow YAML parses; `grep` confirms steps run in order: install → refresh → guard → stats →
  check → stats → commit.

## Known limitation

The live `--dry-run` fetch depends on Yahoo reachability from the runner, which I cannot verify
from here; the offline tests cover the merge logic, not the network. If Yahoo is unavailable on a
given night the job fails loudly (by design) instead of drifting — a missed run is recoverable,
a silent one is not.
