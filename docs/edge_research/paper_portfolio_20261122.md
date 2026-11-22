# Paper Portfolio Tracker - 2026-11-22

> **ZERO strategies in this repo have passed the promotion gates. This book is a demonstration of tracking machinery, not evidence of an edge. Its P&L means nothing about future returns.**

## What was built

[`tools/paper_portfolio.py`](../../tools/paper_portfolio.py) - a paper portfolio that:

1. keeps book state in `paper_portfolio/book.json` (`starting_cash`, `cash`, open `positions[]`
   with `symbol, direction, qty, entry_px, entry_ts, tp, sl, strategy, source`, plus
   `schema_version`, `created_utc` and `purpose: plumbing_demo_not_validated_edge`);
2. marks every open position to market with a real quote and computes
   `equity = cash + market value of positions`;
3. resolves TP/SL **pessimistically** (a bar straddling both levels resolves to SL);
4. appends one object per run to `paper_portfolio/equity_curve.jsonl`;
5. writes a dated `paper_portfolio/snapshots/YYYY-MM-DD.json`;
6. exposes `--init / --add / --mark / --status / --json`.

Reusable helpers live in [`tools/paper_portfolio.py`](../../tools/paper_portfolio.py):
`resolve_tp_sl`, `mark_book`, `fetch_price`, `open_position`, `close_position`.

## Reused vs new

| Piece | Status |
|-------|--------|
| TP/SL intrabar check | **Reused** - `audit_trail.universal_pick_resolver._check_tp_sl_intrabar` (already SL-first). A local SL-first fallback exists only if that import fails. |
| Crypto prices | **Reused path** - `ccxt` (already used across the repo). |
| FX prices | **Reused data** - `data/forex_rate_cache/` (on-disk ECB closes). |
| `yfinance` | **Reused as last resort** - Yahoo has 429'd in this repo before. |
| Mark-to-market, cash/equity accounting, equity curve, dated snapshot, book state, CLI | **New** - this was the gap. |

Not touched: `tools/live_daytrade_sim.py`, `audit_trail/universal_pick_resolver.py`,
`alpha_engine/active_picks_sync.py`, `reports/forward_observations.jsonl`. No GHA workflow added,
no git commits.

## Unit tests (verbatim)

Command:

```
python3 -m pytest tests/test_paper_portfolio.py -q
```

Output:

```
..........                                                               [100%]
10 passed in 0.12s
```

Coverage: buy-100@100-mark-110 equity; TP hit net of 2x cost (gross 100 -> net 97.9);
SL hit net of 2x cost (gross -100 -> net -101.9); **straddle bar resolves SL** for both LONG
and SHORT; one-winner-one-loser partial book; missing price -> STALE and excluded (not zeroed,
not valued at entry); equity append + dated snapshot; purpose stamp + short-side accounting;
`--init` refuses overwrite without `--force`. All use synthetic prices, no network.

## Live mark on real data

Book initialized at 10,000 with three crypto longs (opens charged at entry, 10 bp/side).
Two consecutive `--mark` runs:

| Symbol | Direction | Qty | Entry | Mark (run 2) | Quote timestamp | Source |
|--------|-----------|-----|-------|-------------|-----------------|--------|
| BTC/USDT | LONG | 0.05 | 60,000.0000 | 60,209.5400 | 2026-11-22T09:42:32Z | ccxt:binance:BTC/USDT |
| ETH/USDT | LONG | 2 | 1,690.0000 | 1,696.2800 | 2026-11-22T09:42:33Z | ccxt:binance:ETH/USDT |
| SOL/USDT | LONG | 30 | 70.0000 | 70.0800 | 2026-11-22T09:42:34Z | ccxt:binance:SOL/USDT |

Run 1 (09:42:15Z): BTC 60,170.14, ETH 1,693.52, SOL 70.02 - equity **10,007.667**.
Run 2 (09:42:30Z): BTC 60,209.54, ETH 1,696.28, SOL 70.08 - equity **10,016.957**.

Both points are in `paper_portfolio/equity_curve.jsonl` (2 points), so the append path is
proven. No TP/SL fired - the marks are far from the levels.

## What 429'd or failed

Nothing in the final run. `ccxt` (binance) served all three symbols. A one-off
`yfinance` probe during setup also succeeded (582 rows) - it was only a fallback and was not
needed. The known constraint stands: Yahoo has 429'd here before, so crypto via ccxt remains
the primary path.

## What this proves and does not prove

- **Does prove:** positions can be opened, marked to a real price, and valued into a cash +
  equity ledger; TP/SL resolves stop-first on an ambiguous bar; equity points append and a
  dated snapshot is written; a missing price is excluded rather than faked. The machinery works.
- **Does not prove:** anything about returns. The three positions are an arbitrary plumbing demo,
  not a strategy, and no strategy in this repo has reached CANDIDATE. The +16.96 equity is
  noise from two minutes of crypto price movement, not a result.
