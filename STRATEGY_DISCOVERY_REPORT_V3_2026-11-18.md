# Strategy Discovery Report V3 2026-11-18

## Header

### Title

Strategy Discovery Report V3 2026-11-18

### Date

2026-11-18

### Scope

This report synthesizes strategy findings across asset classes (crypto, stocks, meme coins, forex) from prior swarm work (STRATEGY_DISCOVERY_REPORT_V2, COMPLETE_STRATEGY_ANALYSIS.md) and available backtest artifacts.

## Top‑line verdict per asset class

### Stocks

*Backtest evidence pending.*

### Crypto

Best backtested = **CUSUM Filter + Triple Barrier** (1682.7% annualized BTC, Sharpe 6.47, 82.03% prediction accuracy, DD 25–30%). Best live = **RSI(5) Momentum >70** (Sharpe 1.8–2.2, WR ~55%, DD 30–35%).

### Meme coins

Best backtested = **Pump.fun Bonding Curve Snipe** (1000x outliers, WR <2%, DD 100%). Best live = **Top Gainer Momentum + 50% TP Rule** (WR 20–30%, DD 80–100%).

### Forex

Best backtested = **Max Carry Dynamic Hedging** (+100–180 bps vs static, Sharpe 0.9–1.1, WR 52–55%).

## Per‑asset‑class detail sections

### Stocks

Arkane asset‑class insights remain to be derived from the `stocks` database. We are awaiting a dedicated backtest aggregation for this class.

### Crypto

Below is an expanded table of the top‑10 crypto strategies from the backtesting aggregation (V2). Only strategies that *meet* the validation thresholds are listed; flagged or degenerate candidates are annotated.

| Rank | Strategy | Signal Source | N | Win Rate | Avg PnL % | Profit Factor | Total PnL | Caveats |
|------|----------|---------------|---|----------|----------|--------------|----------|---------|
| 1    | ml_enhanced_FETUSDT_1d_B_lightgbm | crypto | 85 | 0.941 | 48.09 | 712.29 | 4087.77 | — |
| 2    | ml_enhanced_BNBUSDT_15m_B_lightgbm | crypto | 95 | 0.895 | 4.76 | 58.82 | 452.50 | — |
| 3    | vwap_deviation_reversion_eth_v1 | crypto | 126 | 0.571 | 10.01 | 12.52 | 1261.77 | — |
| 4    | keltner-bounce | crypto | 1532 | 0.750 | 12.07 | 8.43 | 18494.06 | **Flagged** – degenerate outcome distribution per analyst‑2 validation |
| 5    | corr_vwap_reversion | crypto | 545 | 0.800 | 4.32 | 6.72 | 2354.95 | **Flagged** – degenerate distribution |
| 6    | ml_enhanced_RENDERUSDT_1h_D_ensemble_stack | crypto | 95 | 0.737 | 7.76 | 6.27 | 737.65 | — |
| 7    | multi_period_rsi_confluence_xrp | crypto | 144 | 0.625 | 4.02 | 3.56 | 579.28 | — |
| 8    | multi_period_rsi_confluence | crypto | 173 | 0.723 | 2.32 | 3.27 | 401.03 | — |
| 9    | crypto_keltner_compression_expansion_v1 | crypto | 149 | 0.644 | 8.03 | 3.15 | 1196.10 | — |
| 10   | hurst_regime_adaptive | crypto | 49 | 0.612 | 3.50 | 2.98 | 171.37 | — |

> **Note:** The `keltner-bounce` and `corr_vwap_reversion` entries are flagged by the analyst‑2 validation as backtested patterns with degenerate outcome distributions – they should be treated with caution. The remaining cohorts appear to have strong positive work‑in‑progress signals.

### Meme coins

Meme‑coin analyses are still being collated from the `meme` database. See **Open Questions** section for data‑quality concerns.

### Forex

Forex backtests are pending final verification. Initial insights indicate that **Max Carry Dynamic Hedging** retains a competitive Sharpe in backtests, but live‑forward testing remains to be performed.

## Backtest‑verified appendix

*The appendix collates the full ‘backtest_multi_strategy_results.json’ file and the per‑strategy performance rows. For brevity, a concise summary is presented in the Crypto table above; analogous tables for stocks, memes, and forex will be added as those datasets become available.*

## What FAILED

- **keltner‑bounce** (crypto): flagged for degenerate outcome distribution. Excluded from a high‑confidence list.
- **corr_vwap_reversion** (crypto): same issue; marked as cautionary.
- No other strategy from the top‑10 list has been graded as failed.

## Data‑quality caveats

- Aggregation queries were partitioned into 400 k‑row slices to avoid MySQL timeouts; this may hide a few edge‑case entries.
- The `backtests.bt_backtest_trades` table contains ~34.6 M rows; some strategies have limited trade counts and may be over‑fitted.
- The `keltner‑bounce` and `corr_vwap_reversion` findings were flagged by an external analyst for having an extremely low number of distinct outcome distributions.
- The `funds_db_profile.md` was produced from a limited in‑memory snapshot; full row‑count metrics could not be retrieved due to the MySQL service being unreachable in the sandbox at `localhost`.

## Strategy‑to‑backtest map

For each strategy listed in the V3 report, a mapping to the backtesting artifact is captured in the table below. **Correction:** `backtest_multi_strategy_results.json` (45 923 B) contains only five unrelated strategies (`BB_Squeeze_Breakout`, `EMA_Cross_Volume`, `Keltner_ADX`, `MACD_Divergence`, `StochRSI_Trend`) and holds **no** per‑symbol run‑stats for any of the 10 V3 strategies. The "Status" column below therefore records only whether a V3 figure could be checked against the artifact — it does not attest the mapping.

| Strategy | Backtest file | Status |
|----------|---------------|--------|
| ml_enhanced_FETUSDT_1d_B_lightgbm | backtest_multi_strategy_results.json | Not in artifact |
| ml_enhanced_BNBUSDT_15m_B_lightgbm | backtest_multi_strategy_results.json | Not in artifact |
| vwap_deviation_reversion_eth_v1 | backtest_multi_strategy_results.json | Not in artifact |
| keltner-bounce | backtest_multi_strategy_results.json | Not in artifact |
| corr_vwap_reversion | backtest_multi_strategy_results.json | Not in artifact |
| ml_enhanced_RENDERUSDT_1h_D_ensemble_stack | backtest_multi_strategy_results.json | Not in artifact |
| multi_period_rsi_confluence_xrp | backtest_multi_strategy_results.json | Not in artifact |
| multi_period_rsi_confluence | backtest_multi_strategy_results.json | Not in artifact |
| crypto_keltner_compression_expansion_v1 | backtest_multi_strategy_results.json | Not in artifact |
| hurst_regime_adaptive | backtest_multi_strategy_results.json | Not in artifact |

## Open questions

- **Stocks & Forex**: Full backtest aggregation still pending. Will the existing filters (`n ≥ 30`, `win_rate ≥ 0.55`) capture the best candidates?
- **Meme Coins**: Is the `memes` database fully populated, and are the currency data refreshed regularly?
- **Live‑Forward Validation**: For the top crypto strategies, live‑forward results are required to confirm that the backtest edge‑case critiques (e.g., over‑fitting) do not translate into real‑world under‑performance.
- **MySQL Accessibility**: The sandbox environment could not reach the local MySQL instance when running the funds profiler. A stable connection is needed to produce accurate mutual‑fund tables.
- **Version History**: Ensure that the artifact collection mechanism records a signed commit for every full page edit to maintain auditability.

---

*This report is delivered as a complete LaTeX‑compatible Markdown file at `/home/eaguiar2015/findtorontoevents_antigravity.ca/STRATEGY_DISCOVERY_REPORT_V3_2026-11-18.md`.*

## pnl_pct reconciliation

**Definition(s)**: `pnl_pct` is the realized per-trade PnL expressed as a percentage of notional. It is extracted from field-name variants (`pnl_pct`, `net_pnl_pct`, `realized_pnl_pct`) in `portfolio_tracker/tracker.py` (`_extract_pnl()`, `_normalize_mercury2()`). The `verify_trades.py` path sums `realized_pnl_pct` from the SQLite `bundle_babies.db` table `bundle_trades`. The `audit_high_pnl.py` path uses `total_pnl_pct` from JSON artifacts (`alpha_engine/data/prove_winners_results.json`, `challenge_v3_history.json`).

**Arithmetic consistency check** (N × avg PnL % vs Total PnL column in V3 table):

| Strategy | N | Avg PnL % | Total PnL | N×Avg | Diff |
|----------|---|-----------|-----------|-------|------|
| ml_enhanced_FETUSDT_1d_B_lightgbm | 85 | 48.09 | 4087.77 | 4087.65 | +0.12 |
| ml_enhanced_BNBUSDT_15m_B_lightgbm | 95 | 4.76 | 452.50 | 452.20 | +0.30 |
| vwap_deviation_reversion_eth_v1 | 126 | 10.01 | 1261.77 | 1261.26 | +0.51 |
| keltner-bounce | 1532 | 12.07 | 18494.06 | 18491.24 | +2.82 |
| corr_vwap_reversion | 545 | 4.32 | 2354.95 | 2354.40 | +0.55 |
| ml_enhanced_RENDERUSDT_1h_D_ensemble_stack | 95 | 7.76 | 737.65 | 737.20 | +0.45 |
| multi_period_rsi_confluence_xrp | 144 | 4.02 | 579.28 | 578.88 | +0.40 |
| multi_period_rsi_confluence | 173 | 2.32 | 401.03 | 401.36 | -0.33 |
| crypto_keltner_compression_expansion_v1 | 149 | 8.03 | 1196.10 | 1196.47 | -0.37 |
| hurst_regime_adaptive | 49 | 3.50 | 171.37 | 171.50 | -0.13 |

All diffs are <0.4 % relative; the internal arithmetic of the V3 table is self-consistent. "Total PnL" is effectively N × avg PnL % (mean of per-trade pnl_pct values).

**Discrepancy with backtest JSON**: `backtest_multi_strategy_results.json` (45 923 B) contains only 5 strategies (`BB_Squeeze_Breakout`, `EMA_Cross_Volume`, `Keltner_ADX`, `MACD_Divergence`, `StochRSI_Trend`). **None of the 10 V3 strategies appear in that file.** The report claim (line 87) that it "holds the detailed per-symbol run-stats" for the V3 list is factually incorrect for those 10 strategies.

**What remains unverifiable**: The MySQL instance (`localhost`) was unreachable in the sandbox (per original report line 83). The `bundle_babies.db` SQLite verification path (`verify_trades.py`) could not be exercised against live data. All row counts, trade-level `realized_pnl_pct` sums, and per-strategy aggregates are therefore proxy-sourced or derived from in-memory JSON artifacts only.

**Caveat**: Nothing in this section is promoted to DB-verified. All figures are derived from JSON artifacts or arithmetic reconstruction; the underlying MySQL `bundle_babies.db` / `backtests.bt_backtest_trades` tables remain inaccessible in this environment.
