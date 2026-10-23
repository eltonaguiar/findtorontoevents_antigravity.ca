# Copy-trader active lifecycle repair — 2026-10-22

## Broken behavior

The copy-trader dashboard generator combined current picks with closed-history
rows for reporting, then republished historical rows as `OPEN` clones and
highscore picks. A separate merge reintroduced stale clone files into the
scanner's active output, even after the scanner found no eligible picks.
Historical rows also inflated apparent trader agreement.

Live workflow 39844111014 showed zero eligible scanner picks followed by
50 merged clones, 16 highscore picks, and 100 clone-active picks. Current remote
artifacts contained March timestamps; none passed a 24-hour active lifecycle
check. These counts are artifact rows, not evidence of independent trades.

## Changes

- Added a shared active predicate inside the existing generator: reject terminal
  statuses, exit markers, missing/invalid timestamps, age over 24 hours, and
  timestamps more than five minutes in the future. Preserve legitimate open
  unrealized PnL.
- Applied it before clone merging, highscore selection, clone-active emission,
  variation-active emission and consensus counting. Historical files remain
  available to historical reporting and are not rewritten.
- Reject nonfinite/invalid TP-entry-SL geometry and already breached TP/SL levels
  from executable clone/highscore outputs.
- Do not invent a fresh observation timestamp for an untimestamped variation.
- Give terminal duplicate records precedence over open snapshots, including
  WON/LOST/EXPIRED/FLAT and exit markers. Persist only valid original scanner or
  merged-clone candidates; raw exchange reporting rows cannot bypass the scanner
  through this writeback.
- Added workflow regression checks and removed `continue-on-error` from the
  dashboard-data refresh step.

## Verification and limits

The regression reproduced the original problem (9 failures / 1 pass), then
46 tests passed after repair, covering closed statuses, stale clones,
fresh-open preservation, consensus inflation, exit markers, timestamp
boundaries and invalid/breached long/short geometry. Syntax and diff checks pass.
Tests use isolated fixture directories and mocked prices; no live ledger or
audit HTML was regenerated.

This is **not proof of a profitable strategy**. The live verdict still had zero
money-ready classes at the inspected snapshot. No gates were weakened, no
outcomes rewritten, and no newly discovered symbol was promoted.

Full evidence, per-class metrics with sample/window labels, exploratory symbol
leads, and remaining work: [investigation report](../reports/money_maker_ready_20261022T204827Z.md).

*Not financial advice. Research/educational only. Past performance does not guarantee future results.*
