# Regime feed adapters — 2026-11-18

## What was broken / missing

The copy-trader audit had no read-only adapter for the two external crypto regime feeds scouted on 2026-11-18 (`EtherSignals`, `AA Signals`), and no repeatable future-bias check for externally sourced signals. Prior notes referenced `copy_trader_intel/future_bias_check.py` and `copy_trader_intel/source_backtest.py`; neither file exists in this worktree (verified by filename listing and content grep).

## What changed

Added `copy_trader_intel/regime_feed_adapters.py`:

- `fetch_ethersignals(limit)` — normalises `https://ethersignals.com/api/signals` into records with `received_at` / `pushed_at` / `server_time`.
- `fetch_aa_signals(symbol)` — normalises `https://signals.brobotapp.com/v1/signal/{SYMBOL}` (free tier) with `generated_at`.
- `check_future_bias(records)` — flags any record whose timestamp is more than 10s ahead of the source server clock (or local fetch time when the source exposes no server clock), and flags missing/unparseable timestamps.
- CLI writes JSON snapshots to `copy_trader_intel/data/regime_feeds/`.

## Verification

```
python3 copy_trader_intel/regime_feed_adapters.py --source all --limit 50
[ethersignals] fetched=50 future_bias_violations=0
[aa_signals:BTC] fetched=1 future_bias_violations=0
[OK] 51 record(s), no future-bias violations
```

EtherSignals `received_at` values were in the past relative to `serverTime` (max skew ~80s). AA Signals `generated_at` is hour-rounded and in the past.

## Scope / caveats

- Read-only. No dashboard wiring, no `SYSTEM_SOURCES` registration.
- Neither feed publishes entry/SL/TP, so they are regime/confidence overlays, not pick sources. Do not register them as picks without deriving and backtesting synthetic picks first.
- AA Signals free tier is 3 calls/day; EtherSignals is ETHUSDT-only.
- Evidence: `reports/github_stock_crypto_prediction_sources_2026-11-18.md`.
