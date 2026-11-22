# Portfolio tracker: one book, three backends, measured

**Date:** 2026-11-22 · **Branch:** `fix/portfolio-tracking-2026-11-22`
**Files:** `tools/portfolio_tracker.py`, `tests/test_portfolio_tracker.py`,
`.github/workflows/portfolio-tracker.yml`,
`reports/2026-11-22-portfolio-tracking-options.md`,
`reports/portfolio_tracking_comparison.json`, `data/portfolio_tracker/*`

## What was missing

The repo could tell you the P&L of one book at a time — `tools/realtime_challenge.py`
for the challenge books, `tools/forward_book.py` for the pre-registered forward
pod, `tools/portfolio_manager.py` for the legacy 10-algorithm KIMI books — but
there was no single view of "what do we hold, what is it worth now, and what does
the record prove". Each of those files is also a *snapshot* store: rewrite the
state file and the history is gone.

## What was built

`tools/portfolio_tracker.py` implements three candidate storage designs and a
comparison that runs the same events through all three:

- **EventLedger** — append-only JSONL (`FUND`/`OPEN`/`CLOSE`/`MARK`); state is
  `replay(events)`. Skips a torn tail line and reports the count instead of
  corrupting the book.
- **SnapshotStore** — materialised JSON state, regenerated from the ledger,
  never hand-edited.
- **RoundTripBook** — closed trades only; `equity()` raises on purpose, which is
  how the capability gap gets measured rather than hidden.

Plus importers for the two live sources (`data/realtime_challenge/*.json`,
`audit_dashboard/data/forward_book.json`), a live quote path (Binance ticker for
crypto, yfinance for equities), `status`, `mark`, `sync` and `compare` commands,
and `verify_against_sources` which re-derives realised P&L straight from the raw
state files.

CLI:

```
python3 tools/portfolio_tracker.py sync     # import new positions/closes
python3 tools/portfolio_tracker.py mark     # append live quotes
python3 tools/portfolio_tracker.py status   # human view
python3 tools/portfolio_tracker.py compare  # run the three-way comparison
```

## Measured result

21 events across 3 books, $28,000 funded: ledger 5,325 B / 253.6 B per event,
0.22 ms to append, 0.15 ms to replay, **agreement with the snapshot at $0.00**,
a deliberate torn tail write recovered with state identical, and both books
reconciling to their own sources at $0.02 (sprint1, 3 trades) and −$0.03 (buffy,
2 trades) — each bounded by trades × $0.005 because the source rounds `pnl_usd`
to cents. Round-trip log: 402 B, correct realised −$6.20, and unable to price
open risk.

Decision: ledger canonical, snapshot derived cache, round-trip log for reporting.
Detail in `reports/2026-11-22-portfolio-tracking-options.md`.

## Verification

```
$ python3 -m pytest tests/test_portfolio_tracker.py -q
9 passed

$ python3 tools/portfolio_tracker.py sync
sync: 21 source events, 1 new lines
book: fund $28,000.00 equity $28,074.33 realized $-6.19 unrealized $87.02 (8 open / 5 closed)

$ python3 tools/portfolio_tracker.py compare --out reports/portfolio_tracking_comparison.json
agreement: max_abs_diff_usd 0.0, ledger_equals_snapshot true
ledger: torn_write_recovered true, corrupt_lines_after_torn_write 1
reconciliation: sprint1 diff 0.02, buffy diff -0.03
```

The live run also closed two real positions: `buffy` BTC and ETH each hit their
take-profit at 09:41Z/09:42Z, +0.360 % net / +$11.97 apiece, recorded through the
tracker and in the challenge document. Those are paper fills on live market
data, not real-money orders.

## Limits

Marks are last-traded quotes, not executable fills. Equities mark to the last
daily close while the US session is shut. The event log is not compacted
(~2 KB/day at current position count). All three backends share the arithmetic
in `_apply`, so their agreement tests storage, not independent calculation; the
independent check is the source reconciliation above.
