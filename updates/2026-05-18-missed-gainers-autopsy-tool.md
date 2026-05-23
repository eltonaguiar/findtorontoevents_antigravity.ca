# Missed-Gainers Autopsy Tool — PR-2026-0518-5

## What

Created `tools/missed_gainers_autopsy.py` — a CLI tool symmetric to `pick_traceback.py` that answers "what did we miss?" by cross-referencing top market movers against our emitted picks.

## Why

The system had no way to detect blind spots in pick coverage. If a symbol moves big and we have no pick for it, there was no mechanism to find that out. This tool closes that feedback loop.

## How

- **Market data**: `api_failover.fetch_ticker_24h()` (multi-source failover: Binance → ByBit → CoinGecko → KuCoin), with a direct Binance stdlib fallback
- **Pick data**: Same `active_picks.json` + `closed_picks.json` loading pattern as `pick_traceback.py`
- **Classification**: Each top mover is classified as CAUGHT (had pick, direction matches), HARD_MISS (no pick ever), or DIRECTION_MISS (pick exists but wrong side)
- **Output**: Markdown report with recall@top-N, caught/missed detail tables, per-strategy capture rate, and auto-generated action items

## CLI

```
python tools/missed_gainers_autopsy.py [--days 7] [--top 50] [--out reports/missed_gainers.md]
```

## Files Changed

- `tools/missed_gainers_autopsy.py` — new file (210+ lines)

## Verification

- Python syntax check: ✅ PASS
- Test run `--top 10`: ✅ Correctly fetched Binance tickers, cross-referenced against active+closed picks, produced valid Markdown report with 0 errors

## AI Review (Codebuff code-reviewer-deepseek-flash)

- Removed dead `_ensure_symbol_format()` function after review flagged it
- Added `MIN_VOLUME_USDT` floor to filter out illiquid coins
- Added explicit `None` check on `fetch_ticker_24h` return value
