# EQUITY Asset Class — Research & Audit Documentation

**Worktree:** flaxen-hair
**Date:** 2026-11-15
**Purpose:** WIRED_IN documentation for EQUITY as an asset class in the algorithmic trading system audit.
**Status:** Research-in-progress — NOT money-ready, NOT proven profitable.

---

## 1. Executive Summary

EQUITY is the **#1 research priority** in this repository's asset-class roadmap, but it is **not yet proven profitable** and **not deployable** with real capital. It is the only asset class showing a positive cost margin (3.23x) and a positive mean PnL (+0.323% per trade on n=738 closed picks), but the statistical evidence is insufficient: t=1.52, p=0.12 (not statistically significant at p<0.05), n=6 on the cleanest backtest, and second-half profit factor decay (1.342 → 0.977) indicating regime risk.

A pre-registered benchmark test is required before any promotion to paper trading. Until that test passes (n≥500, PF≥1.15, OOS Sharpe ≥ SPY Sharpe, stability in both halves), equity remains a research candidate only.

---

## 2. Equity Strategies in the Codebase

### 2.1 alpha_engine/equity_strategies.py — Core Equity Scanner Strategies

This is the primary equity strategy module, imported by `scanner.py` line 289 (`from equity_strategies import EQUITY_STRATEGIES`). It contains 10+ named strategies plus community strategies and an optional regime-filtered momentum strategy. All signals pass through a factor model + PEAD earnings momentum wrapper (`_wrap_with_factor_model`).

| # | Strategy | Description | Status / Evidence |
|---|----------|-------------|-------------------|
| 1 | `momentum_factor_12m` | Top-decile 12-month momentum (skip last month), Jegadeesh & Titman (1993). Macro gate: SPY uptrend + VIX manageable. | Active, backtested |
| 2 | `penny_volume_breakout` | Penny stocks breaking 20d high on 4x+ volume. Wider stops for penny stocks. | Active |
| 3 | `meme_social_velocity` | Meme stocks on volume acceleration + 10d breakout. | Active |
| 4 | `optimized_stock_momentum` | RVOL + EMA confluence + ADX(14)>20. Claims GOOGL 100% WR / MSFT 66% WR (Mar 2026). | Active |
| 5 | `quality_value_composite` | Quality-minus-junk (Asness, Frazzini & Pedersen 2019). Stability + trend R² + value score. | Active |
| 6 | `intermarket_risk_on` | SPY+QQQ above 20d SMA + declining vol → buy high-beta tech (NVDA, TSLA, AMD, COIN, MSTR). | Active |
| 7 | `support_resistance_bounce` | Buy at support with volume confirmation (Edwards & Magee 1948). | Active |
| 8 | `connors_rsi2_scanner` | **PROVEN sleeve.** RSI(2)<5 + above 200d SMA → BUY. SPY 75.7% WR, p=6e-6 (5yr backtest). QQQ 75.3% WR, p=8e-6. | **Sole proven equity sleeve** |
| 9 | `connors_rsi2_short_scanner` | Mirror of #8 (SHORT side). Confidence capped at 0.65, n<50 forward-trade rule. | Shadow/n<50 |
| 10 | `equity_two_bar_rsi_reversal` | Two consecutive down bars + RSI(2)<25 + above EMA200. Backtest: PF=1.54–1.83, WR=51–57%, n≥173. | Opt-in shadow (EQUITY_RSI2_TWOBAR_ENABLED=1) |
| 11 | `triple_rsi_scanner` | RSI(2)<10 AND RSI(5)<20 AND RSI(10)<30 + above 200 SMA. Published 90% WR, PF=5.0 (20yr). SPY 75% WR (12 trades). | Active, small n |
| 12 | `vix_spike_reversal_scanner` | VIX>30 → BUY SPY (panic reversal). 10yr backtest: 72% WR, avg +2.24%, Sharpe 6.20, p=0.022. | **Secondary proven sleeve** |
| 13 | `turn_of_month_scanner` | Lakonishok & Smidt (1988) TOM effect: +0.23% avg, p<0.01 over 90yr. | Active |
| 14 | `earnings_gap_reversal_scanner` | Sector ETF gap down >4% on 2x volume → mean reversion (Ball & Brown 1968). | Active |
| 15 | `gap_reversal_tech_stocks` | Large-cap tech gap down >3% on 2x volume → reversal (~70% WR, 5d). Bremer & Sweeney (1991) JF. | Active |
| — | `regime_filtered_momentum` | Optional, opt-in registration via env flag. | Conditional |
| — | `COMMUNITY_EQUITY_STRATEGIES` | Community-contributed strategies merged into registry. | Variable |

All strategies are gated by `equity_macro_gate()` (SPY trend + VIX regime) and `vix_confidence_adj()` — except `connors_rsi2_scanner` which is VIX-exempt (benefits from high VIX).

### 2.2 alpha_engine/connors_rsi2.py — Standalone Connors RSI-2

Standalone scanner + backtester for Connors RSI-2 (Connors & Alvarez 2008). Scans SPY, QQQ, IWM, GLD, SLV, VDE, COPX, TLT, BTC-USD, ETH-USD, SOL-USD, BNB-USD, AVAX-USD, DOGE-USD, LINK-USD, XRP-USD, ADA-USD, AAPL, MSFT, NVDA, AMD, TSLA, META, AMZN, GOOGL.

- Entry: RSI-2 < 5 AND price > 200-day SMA
- Exit: RSI-2 crosses above 65 OR 10-day max hold
- Includes full backtest function with binomial p-value calculation
- Results saved to `alpha_engine/data/connors_rsi2_signals.json` and `connors_rsi2_backtest.json`

### 2.3 alpha_engine/antigravity_strategies.py — Antigravity (Gemini) Baby Strategy Adapters

19 strategies wrapped from `baby_strategies/`. Equity-relevant entries:

| Strategy | Symbols | Evidence |
|----------|---------|----------|
| `ag_vt_adx_rsi2_etf` | SPY, QQQ, XLK | 5yr: 179 trades, Sharpe 0.250, PF 1.14, WR 55%, MaxDD -10.2% (~36 picks/yr) |
| `ag_vt_adx_rsi2_equity` | AAPL, MSFT, NVDA | 5yr: 216 trades, Sharpe 0.328, PF 1.16, WR 53%, MaxDD -20.5% (~43 picks/yr) |
| `ag_vt_pattern_sweep` | 13 mega-caps + sector ETFs | 5yr: 245 trades, Sharpe 0.747, PF 1.48, WR 50%, MaxDD -18% (~49 picks/yr) |
| `ag_vt_thematic_etf_momentum` | 9 thematic ETFs (XBI, ARKK, SMH, SOXX, XHB, IBB, XRT, XOP, XME) | 6.3yr: 178 trades, Sharpe 1.02, PF 2.14, WR 51%, CAGR +26%, MaxDD -32.9%. DD warning: exceeds -25% baby gate. |
| `ag_vt_restatement_short` | SEC 8-K Item 4.02 tickers | HIGH severity 51.3% short hit rate vs SPY 28.2% baseline (+23.1pp). ~80 picks/yr after $5 price filter. |
| `ag_etf_dual_momentum_rotation` | 50+ ETFs | DIA WR 58.8%, PF 2.64 — strongest ETF baby-strat edge. |
| `ag_equity_sector_rotation_momentum` | 11 sector ETFs + SPY regime | Monthly dual momentum (1M+3M). |

### 2.4 multi_asset/equity_strategies.py — Multi-Asset Equity/ETF Strategies

Seven standalone equity/ETF strategies, each with signature `(df, symbol, info, **kwargs) -> list[dict]`:

1. `earnings_momentum_pead` — PEAD: gap up >3% on 2x+ volume, earnings calendar gate
2. `sector_rotation` — Buy lagging sector ETFs showing RSI reversal (bottom 30%)
3. `blue_chip_mean_reversion` — RSI(2)<10 on blue chips above 200d SMA (Connors 2009)
4. `vix_market_timing` — VIX-based timing for SPY/QQQ/IWM/DIA (3 regimes)
5. `dividend_aristocrat_defense` — Bear regime: aristocrats; Bull regime: growth pullbacks
6. `gap_fill_reversion` — Gap down 2-5% on normal volume → fill target
7. `etf_relative_strength` — Top 30% 1-month momentum ETFs on pullback

Universes: BLUE_CHIPS (22 names), SECTOR_ETFS (11), INDEX_ETFS (SPY/QQQ/IWM/DIA), LEVERAGED_ETFS_3X (~40 names), DIVIDEND_ARISTOCRATS (20), GROWTH_BASKET (12).

### 2.5 scanner.py — Equity Strategy-Regime Mapping

`scanner.py` line 1113-1129 maps equity strategies to market regimes:

| Strategy | Regime(s) |
|----------|-----------|
| `momentum_factor_12m` | trending |
| `penny_volume_breakout` | trending |
| `meme_social_velocity` | trending, ranging, transitional |
| `quality_value_composite` | trending, ranging, transitional |
| `intermarket_risk_on` | trending |
| `support_resistance_bounce` | ranging |
| `connors_rsi2_scanner` | ranging |
| `triple_rsi_scanner` | ranging |
| `vix_spike_reversal_scanner` | trending, ranging, transitional |
| `turn_of_month_scanner` | trending, ranging, transitional |
| `earnings_gap_reversal_scanner` | ranging, transitional |
| `gap_reversal_tech_stocks` | ranging, transitional |
| `community_orb_equity` | trending |
| `community_penny_volume_surge` | trending |

### 2.6 production_scanner.py — Equity-Specific Gates

- **EAGLE-4 admissibility gate** (`apply_eagle4_admissibility`): Kills EQUITY SHORT/SELL picks (tournament data: EQUITY SHORT 39% WR / +0.10% avg PnL). Only LONG equity picks pass.
- **Volatility filter**: Equity thresholds — HIGH_ATR >1% 24h change, DEAD <0.3%. Dead equity markets are blocked.
- **Portfolio cap**: 50% diversity quota for non-crypto (equity, forex, futures, commodity, etf, bond). Equity picks compete for diversity slots.
- **Symbol overrides**: TSLA, AAPL, MSFT, NVDA, SPY, QQQ, etc. are explicitly categorized as stock/etf (not crypto).
- **Stale pick resolution**: SPY pick `cta_golden_cross_200` shows `forward_status: "insufficient_data (6/50 trades)"`.

---

## 3. Backtest Results for Equity Strategies

### 3.1 Holding Period Analysis Backtest Results

File: `2026-11-15_12AM_plan/flaxen-hair/02_holding_period_analysis/backtest_results.json`

**Equity/ETF results (SPY, QQQ, sector ETFs):**

| Symbol | Strategy | Trades | WR | PF | Sharpe | MaxDD | PnL% | p-value |
|--------|----------|--------|-----|-----|--------|-------|------|---------|
| SPY | connors_rsi2 | 6 | 83.33% | 76.92 | 1.142 | -0.18 | +13.56 | 0.109 |
| SPY | keltner_compression_v2 | 4 | 75.0% | 40.02 | 1.402 | -0.24 | +9.18 | 1.000 |
| SPY | ema_stack | 12 | 50.0% | 1.031 | 0.012 | -8.27 | +0.61 | 0.613 |
| SPY | funding_sentiment | 6 | 83.33% | 3.092 | 0.432 | 0.0 | +19.49 | 0.109 |
| QQQ | connors_rsi2 | 5 | 80.0% | 2.086 | 0.288 | -8.84 | +9.60 | 0.188 |
| QQQ | keltner_compression_v2 | 5 | 60.0% | 1.197 | 0.081 | -11.40 | +2.25 | 0.500 |
| QQQ | ema_stack | 11 | 63.64% | 1.317 | 0.104 | -11.91 | +7.42 | 0.274 |
| QQQ | funding_sentiment | 9 | 66.67% | 2.289 | 0.346 | -8.84 | +27.02 | 0.254 |
| XLE | connors_rsi2 | 3 | 100.0% | 10.00 | 1.708 | 0.0 | +27.20 | 1.000 |
| XLF | connors_rsi2 | 3 | 33.33% | 0.172 | -0.712 | -3.20 | -3.42 | 1.000 |
| XLV | connors_rsi2 | 1 | 0.0% | 0.00 | 0.0 | 0.0 | -2.92 | 1.000 |
| XLI | connors_rsi2 | 4 | 75.0% | 4.419 | 0.656 | -3.46 | +11.83 | 1.000 |

**Key observation:** SPY connors_rsi2 shows PF=76.92, WR=83.3%, Sharpe=1.14 — but **n=6 trades**, p=0.109 (not statistically significant). This is the single most-cited equity backtest in the codebase, and it fails on sample size alone.

Crypto (BTC-USD, ETH-USD) and commodity (GLD, TLT) results are also present but are not equity-class results.

### 3.2 Research Profitability Protocol (research/profitability/)

Four protocol versions (v1–v4) have been run. **All 23 candidates across all versions returned NOT_PROVED.**

- v4 (2026-11-14): Crypto funding carry (H21/H22/H23) — 0/3 passed. Closest to real but capital-inefficient.
- v3: 8 crypto/ETF candidates — 0/8 passed (SPA p=0.488).
- v2: H10 RSI2+cash contaminated OOS; effective N=38.
- v1: H7 RSI2: OOS 1.50 Sharpe, 17.6% CAGR vs 18.6% B&H — beat by buy-and-hold.

The scorecard (SCORECARD.md) gives the process 7.7/10 but **actual profitability proof: 0/10**.

### 3.3 Other Backtest JSON Files

- `backtest_results.json` (root) — general backtest results
- `backtest_rsi2_results.json` — RSI-2 specific
- `backtest_kimi_claw_results.json` — Kimi Claw results
- `mega_strategies_backtest_results.json` — mega strategies
- `copy_trader_intel/data/backtest_results.json` — copy trader backtests
- `quan_engine/data/backtest_results/backtest_summary.json` — quan engine summary
- `audit_dashboard/data/equity_momentum_yc_regime_backtest.json` — equity momentum backtest

None of these contain a clean, statistically significant equity strategy result meeting n≥500, PF≥1.15, OOS Sharpe ≥ benchmark.

---

## 4. Current Status of Equity Picks

### 4.1 dashboard/live_picks.json

Timestamp: 2026-11-15T00:45:51.748744

- **13 total active picks**, total unrealized PnL +0.025949 (+2.59%)
- **Only 1 equity pick:** `cta_golden_cross_200::SPY` — LONG SPY, entry $735.29, current $754.37, unrealized +2.59%, forward status: `insufficient_data (6/50 trades)`, forward WR 0.75 on 6 trades, antigravity_safe=false (REJECTED for Real Money)
- **All other 12 picks are crypto** (BTCUSDT, RENDERUSDT, LTCUSDT, ARBUSDT, LINKUSDT, TRXUSDT, BNBUSDT) or bond (JNK)
- **Zero equity picks are forward-validated** (forward_validated=false on all)
- The SPY pick has `asset_class: "CRYPTO"` (misclassified — a known data quality issue flagged for fixing via `alpha_engine/asset_class.py`)

### 4.2 multi_asset/data/multi_asset_picks.json

All picks are `forward_test_only: true`, `forward_validated: false`, `forward_trades: 0`, `forward_wr: 0.0`.

**Equity picks (3 total):**

| ID | Symbol | Strategy | Asset Class | Status | Forward Validated |
|----|--------|----------|-------------|--------|-------------------|
| multi_asset_stocks_rsi2_pullback::PFE | PFE | stocks_rsi2_pullback | EQUITY | OPEN | false |
| multi_asset_stocks_rsi2_pullback::TMO | TMO | stocks_rsi2_pullback | EQUITY | OPEN | false |
| multi_asset_stocks_ema_golden_cross::AVGO | AVGO | stocks_ema_golden_cross | EQUITY | OPEN | false |

All three have zero forward trades, zero forward WR, null PnL, null exit. They are forward-test-only paper placements with no resolved outcomes.

**Remaining picks are FOREX (8), FUTURES (1), COMMODITY (1).**

---

## 5. Key Metrics for EQUITY

### 5.1 From ASSET_CLASS_PROFITABILITY_PLANS.md (EQUITY section)

| Metric | Value | Notes |
|--------|-------|-------|
| Priority rank | #2 (after passive ETF/MF allocation) | #1 active prediction class |
| Cumulative n | 447 closed equity trades | Likely inflated |
| Cumulative WR | 53.2% | Degrading |
| Cumulative PF | 1.55 | Likely inflated |
| Recent WR | 52.9% | Recent window |
| Recent PF | 1.44 | Recent window |
| connors_rsi2_scanner (SPY/QQQ) WR | 75.7% | **Sole proven sleeve** |
| vix_spike_reversal_scanner (SPX) WR | 72% | Secondary proven sleeve |
| t-statistic | t=1.52 | Not statistically significant |
| p-value | p=0.12 | Fails p<0.05 threshold |
| Second-half PF | 1.342 → 0.977 | Regime risk — decay in second half |
| Cost margin | 3.23x | **Only class with positive cost margin** |
| Mean PnL per trade | +0.323% | Positive expectancy |
| Closed picks (n) | 738 | Largest clean cohort among classes |

### 5.2 From Backtest Results (SPY connors_rsi2)

| Metric | Value | Assessment |
|--------|-------|------------|
| Trades | 6 | **Critically small** |
| Win Rate | 83.33% | High but on n=6 |
| Profit Factor | 76.92 | Extremely high but n=6 |
| Sharpe | 1.142 | Above 1.0 but n=6 |
| p-value | 0.109375 | **Not statistically significant** (p>0.05) |
| Max Drawdown | -0.18 | 18% |
| PnL | +13.56% | Positive but n=6 |

### 5.3 Why These Metrics Matter

The combination of positive cost margin (3.23x) and positive mean PnL (+0.323%/trade) makes equity the **only asset class with a plausible path to profitability**. Every other class (crypto, forex, commodity, futures) has negative or near-zero cost margins and/or negative expectancy. However:

1. **n=6 on the cleanest backtest** is far below the n≥500 pre-registration requirement
2. **t=1.52, p=0.12** means we cannot reject the null hypothesis of zero edge
3. **Second-half PF decay (1.342 → 0.977)** indicates the edge does not survive regime changes
4. **All equity picks in live_picks.json are non-validated** (0 forward-validated equity picks)

---

## 6. Why EQUITY Is the #1 Research Priority

Despite not being proven, equity is ranked as the top active research candidate (after passive index allocation) for five reasons:

### Reason 1: Only Class with Positive Cost Margin
EQUITY is the **only asset class** with a cost margin above 1.0 (3.23x). This means after transaction costs, the gross edge is still positive — a necessary (though not sufficient) condition for profitability. Every other class has eroded or negative cost margins.

### Reason 2: Positive Mean PnL
Mean PnL of +0.323% per trade on n=738 closed picks is the largest clean cohort with positive expectancy in the system. This is a real signal, not zero.

### Reason 3: Sole Proven Sleeve — connors_rsi2_scanner
The Connors RSI-2 scanner on SPY/QQQ shows 75.7% WR with p=6e-6 in the backtest. This is the only equity strategy with any statistical backing, even though the live forward-test n is only 6.

### Reason 4: Secondary Proven Sleeve — vix_spike_reversal_scanner
72% WR on SPX with p=0.022 over a 10-year backtest. This provides a second, independent equity edge with academic backing (Connors 2010, Whaley 2009).

### Reason 5: Clear Benchmark Exists
SPY total return is an unambiguous, low-cost, widely available benchmark. Unlike crypto (no single benchmark) or forex (multiple pairs), equity has a clean buy-and-hold comparator for pre-registered testing.

---

## 7. Pre-Registered Test Required

From `ASSET_CLASS_PROFITABILITY_PLANS.md` (EQUITY section, lines 41-50):

| Parameter | Requirement |
|-----------|-------------|
| Sample | 24 months, n ≥ 500 closed equity trades |
| Benchmark | SPY total return, same window (NOT zero) |
| Gate 1 | OOS Sharpe ≥ SPY Sharpe |
| Gate 2 | PF ≥ 1.15 |
| Gate 3 | Stability: first-half PF ≥ 1.05 AND second-half PF ≥ 1.05 |
| Kill condition | Fails any line → EQUITY is beta, stop emitting, hold index |

### Implementation Steps (from the plan):
1. Fix PnL normalization (ratio vs percent, 100× bug) across all equity picks
2. Backfill `asset_class`='EQUITY' for UNK equity picks via `alpha_engine/asset_class.py`
3. Refresh `current_price`/`unrealized_pnl` for stale active picks
4. Run Connors RSI2 scanner against SPY benchmark with T-bill cash overlay
5. Validate on clean OOS data only (no data snooping)

### Success Criteria:
PF ≥ 1.15, WR ≥ 55%, Sharpe ≥ SPY Sharpe, stability both halves → promote to paper trading. Otherwise → hold SPY/QQQ index.

---

## 8. Why EQUITY Is NOT Yet Deployable

### 8.1 Statistical Significance Failure
- **t=1.52, p=0.12**: Cannot reject the null hypothesis at p<0.05. The observed edge could be luck.
- **n=6 on SPY connors_rsi2**: The most-cited backtest has only 6 trades. Bonferroni correction across the 683-strategy universe would make significance essentially impossible at this sample size.
- **n=738 closed picks**: While larger, the cumulative PF (1.55) is flagged as "likely inflated" and recent PF (1.44) is degrading.

### 8.2 Regime Risk
- **Second-half PF fell 1.342 → 0.977**: The edge decays in the second half of the sample, indicating it is regime-dependent, not robust.
- **Recent WR 52.9%, PF 1.44**: Degrading from cumulative 53.2% / 1.55.

### 8.3 No Forward-Validated Equity Picks
- `dashboard/live_picks.json`: 0 equity picks are forward-validated. The single SPY pick has `forward_status: "insufficient_data (6/50 trades)"`.
- `multi_asset/data/multi_asset_picks.json`: 3 equity picks, all `forward_test_only: true`, `forward_validated: false`, `forward_trades: 0`.

### 8.4 Data Quality Issues
- SPY pick misclassified as `asset_class: "CRYPTO"` in live_picks.json (needs `alpha_engine/asset_class.py` backfill)
- PnL normalization bugs (ratio vs percent, 100×) across equity picks
- Stale active picks with missing `current_price`/`unrealized_pnl`
- `slippage_pct=0` on closed rows (unverified; breakeven buffer 0.416%/trade)

### 8.5 EAGLE-4 Directional Kill
- EQUITY SHORT/SELL picks are killed by the EAGLE-4 admissibility gate (tournament data: EQUITY SHORT 39% WR / +0.10% avg PnL). Only LONG equity can pass, halving the strategy universe.

---

## 9. Conclusion

EQUITY is the **#1 active research priority** because it is the only asset class with a positive cost margin (3.23x), positive mean PnL (+0.323%/trade), and at least one backtest-validated sleeve (connors_rsi2_scanner, SPY 75.7% WR). However, it is **not proven profitable** and **not deployable**:

| Blocking Condition | Status |
|--------------------|--------|
| t=1.52, p=0.12 (not significant) | **BLOCKING** |
| n=6 on cleanest backtest (need n≥500) | **BLOCKING** |
| Second-half PF decay 1.342 → 0.977 | **BLOCKING** (regime risk) |
| 0 forward-validated equity picks | **BLOCKING** |
| Data quality issues (misclassification, PnL normalization) | **BLOCKING** |

**Required next step:** Execute the pre-registered benchmark test (24 months, n≥500, SPY total return benchmark, PF≥1.15, OOS Sharpe ≥ SPY Sharpe, stability in both halves). If it passes → promote to paper trading at ¼ Kelly. If it fails → EQUITY is beta; stop emitting equity picks and hold SPY/QQQ index.

Until then, equity remains a research candidate only — not money-ready.

---

## 10. File References

| File | Relevance |
|------|-----------|
| `alpha_engine/equity_strategies.py` | Core equity strategies (15+ named) |
| `alpha_engine/connors_rsi2.py` | Standalone Connors RSI-2 scanner + backtester |
| `alpha_engine/antigravity_strategies.py` | 19 baby-strategy adapters, 7 equity-relevant |
| `alpha_engine/scanner.py` | Equity strategy-regime mapping (line 1113-1129) |
| `alpha_engine/production_scanner.py` | EAGLE-4 gate, volatility filter, portfolio cap for equity |
| `multi_asset/equity_strategies.py` | 7 standalone multi-asset equity/ETF strategies |
| `2026-11-15_12AM_plan/flaxen-hair/02_holding_period_analysis/backtest_results.json` | Equity backtest results (SPY connors_rsi2 PF=76.92, n=6) |
| `research/profitability/` | v1-v4 protocol results (all NOT_PROVED) |
| `research/profitability/SCORECARD.md` | Process scorecard (0/10 profitability proof) |
| `dashboard/live_picks.json` | Live picks — 1 equity (SPY), 0 forward-validated |
| `multi_asset/data/multi_asset_picks.json` | Multi-asset picks — 3 equity, all forward-test-only |
| `2026-11-15_12AM_plan/flaxen-hair/01_asset_class_plans/ASSET_CLASS_PROFITABILITY_PLANS.md` | Pre-registered test protocol & priority ranking |
| `2026-11-15_12AM_plan/flaxen-hair/01_asset_class_plans/ASSET_CLASS_PLANS.md` | Shared rules + per-class roadmap |
| `final_v2/inspect-wt/02_profitability_per_asset_class/equity_etf.md` | Variant C walk-forward decomposition (n=112 PF 1.30 EQUITY) |
