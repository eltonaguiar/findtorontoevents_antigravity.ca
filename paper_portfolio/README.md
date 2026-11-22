# Paper Portfolio Tracker

> **ZERO strategies in this repo have passed the promotion gates. This book is a demonstration of tracking machinery, not evidence of an edge. Its P&L means nothing about future returns.**

This directory holds a paper book maintained by [`tools/paper_portfolio.py`](../tools/paper_portfolio.py):
open positions marked to market with real quotes, a cash balance, an equity curve, and a
dated snapshot per day. The book itself is stamped
`"purpose": "plumbing_demo_not_validated_edge"` in [`book.json`](book.json).

## What it does

- **Mark-to-market** every run: one real quote per open symbol, unrealized P&L, and
  `equity = cash + market value of positions`.
- **Pessimistic TP/SL**: if a bar straddles both levels, it resolves to the **stop**, not the
  target. The intrabar check is reused from
  [`audit_trail/universal_pick_resolver.py`](../audit_trail/universal_pick_resolver.py) (`_check_tp_sl_intrabar`),
  which is already SL-first.
- **Costs**: configurable per-side cost (default **10 bp**), with gross and net P&L recorded
  separately.
- **Honest failure**: a symbol with no price is marked `STALE` and **excluded from equity**.
  It is never valued at entry price, zero, or a guess.

## Price sources (in order)

1. `data/forex_rate_cache/` - on-disk ECB daily closes for FX pairs (not live).
2. `ccxt` - crypto spot tickers (the reliable path in this environment).
3. `yfinance` - last resort; Yahoo has returned HTTP 429 in this repo before.

## Files

| File | Contents |
|------|----------|
| `book.json` | Book state: `starting_cash`, `cash`, open `positions[]`, `closed[]`, `schema_version`, `created_utc`, `purpose` |
| `equity_curve.jsonl` | One JSON object per mark: `ts_utc, cash, positions_value, equity, realized_pnl, unrealized_pnl, n_open, n_closed, prices{sym:{px,ts,source}}` |
| `snapshots/YYYY-MM-DD.json` | Same payload plus the full position list; same-day re-marks replace the snapshot, while the jsonl keeps every point |

## Usage

```bash
python3 tools/paper_portfolio.py --init --cash 10000
python3 tools/paper_portfolio.py --add BTC/USDT LONG 0.05 --entry 60000 --tp 66000 --sl 57000 --strategy demo
python3 tools/paper_portfolio.py --mark          # fetch, resolve, append equity + snapshot
python3 tools/paper_portfolio.py --status        # no network
python3 tools/paper_portfolio.py --mark --json
```

`--init` refuses to overwrite an existing book unless `--force` is passed.

## Tests

```bash
python3 -m pytest tests/test_paper_portfolio.py -q
```

Deterministic, synthetic prices, no network. Includes the straddle-bar-resolves-SL case.
