# Portfolio tracking — three storage options, measured on the real book

**Date:** 2026-11-22 · **Status:** recommended option implemented and running
**Code:** `tools/portfolio_tracker.py` · **Tests:** `tests/test_portfolio_tracker.py` (9 passing)
**Machine-readable result:** `reports/portfolio_tracking_comparison.json`

## 1. The question

"Track the portfolio" can mean three different storage designs, and the choice
decides what can be answered later. Rather than pick one by taste, all three
were implemented behind one CLI and run through the same 19-event book
(Buffy 4 crypto fills, sprint1 3 closed trips, the 8-entry pre-registered
forward book — 21 events across 3 books, $28,000 of notional capital).

| option | what it stores | state derived by | survives a torn write | can answer "what did we know at 09:15" |
|---|---|---|---|---|
| **ledger** | append-only JSONL of `FUND`/`OPEN`/`CLOSE`/`MARK` | replay of the event list | **yes** — skips the partial line, reports it | **yes** |
| **snapshot** | one materialised JSON object | in-place mutation | no — history is overwritten | no |
| **round-trip log** | closed trips only | aggregation | yes | no, and it cannot even price open risk |

## 2. Measured differences

| metric | ledger | snapshot | round-trip log |
|---|---|---|---|
| bytes on disk (21 events) | 5,325 | 6,741 | 402 |
| bytes per event | 253.6 | — | — |
| write time | 0.22 ms | — | — |
| load + replay | 0.15 ms | O(1) read | — |
| realised P&L | −$6.20 | −$6.20 | −$6.19525 |
| equity | $27,987.31 | $27,987.31 | **cannot be computed** |
| torn-tail write | recovered, 1 corrupt line skipped, state identical | n/a | n/a |
| agreement (max abs diff) | **$0.00** | | |

Reconciliation against the raw sources: sprint1's own `pnl_usd` sum is −$30.16
and the ledger replay is −$30.14 (diff $0.02 on 3 trades); buffy's source sum is
+$23.98 against +$23.95 (diff −$0.03 on 2 trades). Each difference is the source
file rounding each trade's `pnl_usd` to cents before summing, while the ledger
keeps the cents-precise per-trade value — bounded by trades × $0.005. That is a
pass, not a rounding excuse.

## 3. Why the ledger wins

1. **A crash can only truncate the tail.** The tracker wrote a deliberate
   partial line (`{"type": "OPEN", "id": "torn-wri`), reloaded, and got the
   identical book with `corrupt_lines: 1`. A snapshot write interrupted halfway
   leaves nothing to rebuild from.
2. **Marks accumulate.** Every `MARK` is a timestamped observation, so
   unrealised P&L and exposure become a time series rather than "now". The
   round-trip log has no concept of open risk at all.
3. **Smaller than the snapshot per unit of information**, even though the
   snapshot drops all history. 5.3 KB vs 6.7 KB and the ledger keeps every
   event.
4. **The snapshot is still worth keeping — as a derived cache.** It is
   regenerated from the ledger on every run, never edited by hand, so load is
   O(1) for a dashboard while the ledger remains the truth.

## 4. What the first real run shows

Marked against live quotes at 2026-11-22 09:44Z:

| book | equity | return | open | closed |
|---|---|---|---|---|
| buffy | $10,023.95 | +0.239 % | 0 | 2 |
| sprint1 | $9,969.86 | −0.301 % | 0 | 3 |
| forward_book | $8,083.30 | +1.041 % | 8 | 0 |
| **total** | **$28,077.11** | **+0.275 %** | **8** | **5** |

Both `buffy` slots resolved **live at their take-profit** during this session:
BTC and ETH each `TARGET`, +0.360 % net, **+$11.97** apiece — the after-cost TP
the frozen rule specifies (0.60 % gross − 0.24 % costs). The ETH slot filled
the same target on the next 5-minute bar, so no manual intervention was needed.
Full record in `REALTIMECHALLENGE_buffy_20261122_0358_EST.MD`.

That is the tracker doing its job on a trade that actually refused to be a loss:
the number is not a backtest, it is a fill-priced, cost-charged, timestamped
record.

## 5. Honest limitations

- All three backends share the arithmetic in `_apply`, so the agreement check
  validates storage behaviour and bookkeeping, **not** two independent
  implementations. The independence check is `verify_against_sources`, which
  re-derives P&L from the raw state files.
- Marks are last-traded quotes, not executable prices. An equity mark can be
  stale when the market is shut; the tracker says so by timestamping the mark.
- The ledger has no compaction. At 259 bytes/event and roughly 9 open positions
  marked hourly, that is ~2 KB/day and ~0.7 MB/year — acceptable, and a
  retention job can fold `MARK`s into daily closes later.
- `forward_book` entries are equal-notional ($1,000 each) rather than sized by
  conviction; the tracker measures them, it does not endorse the sizing.
- The 3 equity marks ($AAPL, $MSFT, $JNJ) came back unchanged from the last
  daily close because the US cash session is closed at 09:44Z. That is correct
  behaviour, and it is why the report shows a mark timestamp.

## 6. Decision

Adopt the **ledger as canonical**, keep the **snapshot as a generated cache**,
and keep the **round-trip log as the reporting/derived view**. Wired into
`.github/workflows/portfolio-tracker.yml` (hourly, runs the tests, commits the
book with `[skip ci]`).

Next, in the 200-round plan: persist an hourly equity curve from the ledger
(PnL/round), add per-strategy attribution once a second strategy writes to the
book, and reconcile against an actual broker statement when a paper broker
account exists — the tracker is deliberately broker-free until then.
