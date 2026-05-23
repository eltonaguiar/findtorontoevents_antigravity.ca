# Hyro research — strong backtest combos (reference)

Hyro-style simulator on Binance **1h** candles; **0.75%** risk per trade unless noted. **PASS** = hit challenge-style targets within sim rules (not a live fill or perps guarantee).

**Full 6m passer table (23), 12m AVAX/BNB passes, and Batch 2 CLI keys:** [`HYRO_BATCH_PASSERS.md`](./HYRO_BATCH_PASSERS.md). Batch 2 runners: `tools/hyro_backtest_batch2.py`.

## Winning strategies (snapshot)

| Strategy      | Symbol   | WR    | PnL (sim) | Max DD | Status / window      |
|---------------|----------|-------|-----------|--------|----------------------|
| Volume        | BTCUSDT  | 46.6% | +$862.50  | $344   | PASS (3m)            |
| Heikin-Ashi   | ETHUSDT  | 42.0% | +$712.53  | $268   | PASS (3m)            |
| Heikin-Ashi   | SOLUSDT  | 41.6% | +$646.76  | $310   | PASS (3m)            |
| Donchian      | ETHUSDT  | 43.0% | +$862.54  | $305   | PASS (3m)            |
| Squeeze       | SOLUSDT  | 50.0% | +$450.58  | $207   | PASS (3m)            |
| Squeeze       | BNBUSDT  | 54.5% | +$615.20  | $199   | PASS (6m)            |

Re-run anytime:

```powershell
python tools/hyro_backtest_extended.py --months 3 --symbols BTCUSDT --strategy volume --risk 0.75
python tools/hyro_backtest.py --symbol BTCUSDT --strategy volume --months 3 --risk 0.75
```

(Use `heikin_ashi`, `donchian`, `squeeze_breakout` from `hyro_backtest_extended.py` for those keys.)

## Code map (Python ↔ JS)

| Strategy key       | Python backtest                    | JS last-bar evaluator (`hyro_live_signals.js`)   |
|--------------------|------------------------------------|--------------------------------------------------|
| `squeeze_breakout` | `tools/hyro_backtest_extended.py`  | `lastSignalSqueezeBreakout` (~line 637)          |
| `donchian`         | `tools/hyro_backtest_extended.py`  | `lastSignalDonchian` (~line 436)                 |
| `heikin_ashi`      | `tools/hyro_backtest_extended.py`  | `lastSignalHeikinAshi` (~line 481)               |
| `volume`           | `tools/hyro_backtest.py`           | `lastSignalVolume` (~line 272)                 |
| `bollinger`        | `tools/hyro_backtest.py`           | `lastSignalBollinger` (~line 162)                |
| `rsi2`             | `tools/hyro_backtest.py`           | `lastSignalRsi2` (~line 216)                     |

Line numbers drift with edits — search for `function lastSignal*` in the JS file.

## Live dashboard config

- Rows: `audit_dashboard/data/hyro_live_strategies.json` (per-row `symbols` when a combo is pair-specific).
- Page: `audit_dashboard/hyrotrader/index.html` (filters + refresh).
- Evaluators: `audit_dashboard/hyrotrader/hyro_live_signals.js` (`DISPATCH` keys must match JSON `strategy`).

## Caveats

- **Spot candles vs Hyro perps** — different liquidity, funding, gaps.
- **Shorter windows** (3m) can look better than 6–12m; always compare horizons.
- **Live “Valid”** = last **closed** 1h bar only; sparse rows are normal.
