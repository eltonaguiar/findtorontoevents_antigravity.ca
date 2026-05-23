# Asset Class Rehabilitation Plan

**Date:** 2026-04-14 7:47 AM EDT  
**Authors:** Claude (Antigravity bot) + Cursor Cloud Agent  
**Compliance:** MERCURYPROMPT.md, TESTING_PROTOCOL.md §7, STRATEGY_INVESTIGATION_BEFORE_KILL.md

> **RULE: No synthetic data.** All backtests MUST use real OHLCV from the same sources the live scanner uses (yfinance for equities/forex/commodities, Binance API for crypto). Any strategy validated only on synthetic data is rejected per MERCURYPROMPT.md:49-54.

---

## Current State (from Mercury's confirmed numbers + our audit)

| Asset | N | WR | PF | PF CI 95% | Status | Root Cause |
|-------|---|-----|-----|-----------|--------|-----------|
| CRYPTO | 1,876 | 46.9% | 1.43 | [1.21, 1.72] | ✅ Edge confirmed | Filter to Score≥50+Trust≥3 for PF 1.98 |
| EQUITY | 617 | 39.2% | 0.75 | [0.60, 0.92] | ❌ Losing (raw) | stocks_competition drag; filtered PF 2.62 |
| FOREX | 684 | 42.0% | 2.02 | [0.81, 4.04] | ⚠️ Wide CI, outlier-driven | FwdWR≥50 gate gives PF 1.62 — ALREADY FIXED |
| COMMODITY | 279 | 41.6% | 1.04 | [0.64, 1.73] | ⚠️ Breakeven | Single strategy, single source |
| ETF | 19 | 42.1% | 0.28 | [0.01, 1.39] | ❌ Dead | Wrong strategies (0% WR oversold bounce) |
| FUTURES | 17 | 5.9% | 0.06 | [0.00, 0.53] | ❌ Dead | Wrong strategies, same symbols work via commodity |
| BOND | 8 | 50.0% | 25.9 | [0.18, ∞] | 🟡 Too small | n=8, needs volume |

---

## Rehab Actions by Asset Class

### EQUITY — Filter + Inverse (PARTIALLY DONE)

**What's done:**
- ✅ `stocks_competition` blocked (quality_gates.py)
- ✅ Score≥50+Trust≥3 filter validated (PF 2.62 on n=119)
- ✅ 4 losing sub-strategies blocked (PR #192: Value+Quality, Consecutive Beats, Earnings Drift, Dividend Aristocrats)
- ✅ Earnings Drift inverse confirmed at PF 2.07 (PR #189)
- ✅ 5 inverse baby_strategy configs created (PR #194)

**What's NOT done:**
- [ ] Wire inverse strategies to forward test pipeline (`alpha_engine/forward_test.py`)
- [ ] Run `Bollinger MR` cross-asset test on EQUITY symbols not yet covered
- [ ] Expand `stocks_rsi2_pullback` symbol universe (90% WR on n=10, needs n≥30)
- [ ] XLE symbol unblock investigation (64% WR, PF 1.75 on n=11 via `quality-minus-junk`)

### FOREX — Already Fixed, Monitor

**What's done:**
- ✅ FwdWR≥50 gate added (PR #191)
- ✅ Score floor lowered 75→40 (PR #192)
- ✅ LOST exit contamination documented (Issue #186)

**What's NOT done:**
- [ ] Decouple `forex_rsi2_mean_reversion` from copy_trader to run independently
- [ ] Fix LOST exit labeling in copy_trader pipeline (Issue #186 — needs design discussion)
- [ ] Test `MeanReversionBB` on FOREX pairs (already works on CRYPTO/EQUITY)

### COMMODITY — Diversify Strategies

**What's done:**
- ✅ Identified single-strategy/single-source dependency
- ✅ Trust≥3 filter gives marginal lift (PF 1.06→1.28)

**What's NOT done:**
- [ ] Add `Bollinger MR` to commodity futures (GC=F, SI=F, PL=F, HG=F) — it works on equity (PF 1.71) and forex (PF 4.18), mean-reversion is asset-agnostic
- [ ] Add `cta_cross_asset_tsmom` as secondary strategy (currently 6.9% of picks, 42% WR)
- [ ] Expand commodity symbol universe to include: NG=F (natural gas), ZW=F (wheat), ZC=F (corn), KC=F (coffee has 6 picks already)
- [ ] Run real-data backtest via `alpha_engine/incubator/run_incubator.py` on commodity symbols

### ETF — Needs New Strategies (Real Data Only)

**What's done:**
- ✅ Losing strategies blocked (`extreme_oversold_bounce`, `vix_reversal`) in PR #192
- ✅ `proven_vwap_mean_reversion` (4 picks, 100% WR) left running for forward test

**What's NOT done:**
- [ ] Test `Bollinger MR` on ETF symbols (SPY, QQQ, IWM, XLF, GLD, TLT) — real data backtest via incubator
- [ ] Test `forex_rsi2_mean_reversion` on ETF symbols (RSI-2 pullback works on equities at 90% WR)
- [ ] If either passes Layer 1-2 on real data, create baby_strategy config with `wired_in_scanner: false`
- [ ] Target: n≥50 closed picks before declaring edge

### FUTURES — Redirect to Commodity Pipeline

**What's done:**
- ✅ Already in BLOCKED_ASSET_CLASSES
- ✅ Identified that same symbols (GC=F, SI=F) work via commodity pipeline at 40%+ WR

**What's NOT done:**
- [ ] Formally reclassify: GC=F, SI=F, CL=F, HG=F futures picks → COMMODITY asset class
- [ ] ZN=F (bond futures) → BOND asset class
- [ ] Update `alpha_engine/config.py` asset class mapping if needed
- [ ] Remove FUTURES from dashboard performance panels (it's misleading to show 6% WR when the same instruments work as COMMODITY)

### BOND — Grow Volume

**What's done:**
- ✅ 8 picks running via `futures_momentum` / `multi_asset_copytrader`

**What's NOT done:**
- [ ] Add TLT, IEF, AGG as ETF-proxied bond instruments
- [ ] Test `futures_momentum` specifically on ZN=F with extended history
- [ ] Target: n≥50 before any conclusions

---

## Baby Strategy Pipeline — Accurate Status

**From actual `baby_strategies/*.meta.json` files (not fabricated):**

| Status | Count | Strategies |
|--------|-------|-----------|
| `ready_for_forward_test` | 4 | moving_average_slope_momentum, multi_timeframe_ema_cloud, regime_sentinel_composite, vol_scaled_keltner |
| `awaiting_forward_test` (inverse) | 5 | inverse_value_quality, inverse_earnings_drift, inverse_enhanced_ml_xgboost, inverse_extreme_oversold_bounce, inverse_consecutive_beats |
| `awaiting_backtest` | 28 | Various — pipeline bottleneck |
| `backtest_failed` | 8 | adaptive_bollinger_momentum, championship_strategies, kama_volatility_adaptive, keltner_rsi_confluence, logistic_microstructure, rsi_pairs_arbitrage, strategy_framework_wrappers_v2, volatility_regime_breakout |
| `draft` | 2 | ait_manus_composite, inverse_wrapper |
| **TOTAL** | **47** | |

**NONE are wired to live scanner.** All have `wired_in_scanner: false`.

**Note:** The following strategies referenced by the reverted Antigravity plan do NOT exist in `baby_strategies/`: `commodity_momentum_collector`, `forex_london_breakout_v3`, `hyrotrader_short_term_scanner`. Those were fabricated.

---

## Backtesting Rules (Per MERCURYPROMPT.md)

1. **Real data ONLY** — yfinance, Binance API, or cached OHLCV from the scanner
2. **Walk-forward** — 70% train / 15% validation / 15% holdout
3. **Bootstrap CI** on PF — lower bound must exceed 1.0 at 95%
4. **Permutation test** — must beat random direction baseline
5. **Minimum n≥30** definitive exits before declaring edge
6. **Always state data source** in the first line of any analysis output

---

## Priority Actions (Ordered)

| # | Action | Asset | Effort | Impact |
|---|--------|-------|--------|--------|
| 1 | Wire 4 `ready_for_forward_test` strategies to forward_test.py | ALL | Medium | Unblocks pipeline |
| 2 | Wire 5 inverse strategies to forward_test.py | EQUITY/CRYPTO | Medium | Tests inverse hypothesis on real data |
| 3 | Run `Bollinger MR` real-data backtest on COMMODITY/ETF symbols | COMMODITY/ETF | Low | Cross-asset expansion of proven winner |
| 4 | Decouple `forex_rsi2_mean_reversion` from copy_trader | FOREX | Medium | 3-5× forex volume |
| 5 | Reclassify FUTURES symbols to COMMODITY/BOND | FUTURES | Low | Fixes misleading dashboard |
| 6 | Run incubator on 28 `awaiting_backtest` strategies | ALL | High | Clears pipeline bottleneck |

---

*Compliant with MERCURYPROMPT.md, TESTING_PROTOCOL.md §7, and STRATEGY_INVESTIGATION_BEFORE_KILL.md. No synthetic data. No fabricated claims.*
