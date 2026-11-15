# CRYPTO Asset Class — Algorithmic Trading Audit

**Worktree:** flaxen-hair_2026-11-15T0020 | **Date:** 2026-11-15T01:27Z
**Repo:** findtorontoevents_antigravity.ca
**Classification:** CRYPTO — Slot 2 Conditional (diagnosed, fixable defect; NOT deployable yet)
**Status:** NOT money-ready. Data integrity blocks all emission.

---

## Executive Summary

CRYPTO is the only asset class in this system with a **diagnosed, fixable defect**: entry price integrity (~29% clean) combined with ~90% of positions never resolving (stale fill data in the `kimi_riseoftheclaw` / `kimi_strategy_tracking` pipeline). All 700+ crypto strategies fail the clean-cohort screen. Backtest results for crypto are all negative or negative-adjacent (PF < 1.5, WR < 50% across every BTC-USD combination tested). CRYPTO is ranked **slot 2 (low-conditional)** in the asset class profitability plan: fix the entry_price integrity and fill bugs first, then forward-test on POSITION horizon with n≥100, PF≥1.3, WR≥55%. If the post-fix forward test does not show PF ≥ 1.3 at n=100, retire crypto direction trading entirely.

---

## 1. Crypto Strategies in the Codebase

### 1.1 alpha_engine/crypto_strategies.py — 16 Documented Signature Strategies

Located at `alpha_engine/crypto_strategies.py` (4405 lines). The file header describes 99+ signature-specific strategies organized into 16 waves, but the file itself implements 16 concrete strategies:

| # | Strategy | Symbols | Direction | Timeframe | Status |
|---|----------|---------|-----------|-----------|--------|
| 1 | `btc_ichimoku_cloud` | BTC-USD, ETH-USD | BUY only | 1d | Implemented, untested clean |
| 2 | `btc_200d_sma_bounce` | BTC-USD, ETH-USD, SOL-USD | BUY only | 1d | Implemented, untested clean |
| 3 | `crypto_fear_greed_contrarian` | 20 symbols (BTC, ETH, SOL, AVAX, LINK, LTC, DOGE, ADA, DOT, XRP, BNB, APT, NEAR, UNI, SUI, HYPE, RENDER, SEI, INJ, TON) | BUY only | 1d | Implemented, claims 88% WR (unverified) |
| 4 | `funding_rate_extreme` | All CRYPTO_SYMBOLS | BUY only | 1d | Implemented, untested clean |
| 5 | `wyckoff_accumulation` | All CRYPTO_SYMBOLS | BUY only | 1d | Implemented, untested clean |
| 6 | `smart_money_fvg` | All CRYPTO_SYMBOLS | BUY only | 1d | Implemented, untested clean |
| 7 | `rsi_hidden_divergence` | All CRYPTO_SYMBOLS | BUY only | 1d | Implemented, untested clean |
| 8 | `crypto_breakout_volume` | All CRYPTO_SYMBOLS | BUY only | 1d | Implemented, untested clean |
| 9 | `stochrsi_oversold_bounce` | All CRYPTO_SYMBOLS | BUY only | 1d | Implemented, untested clean |
| 10 | `hurst_mean_reversion` | All CRYPTO_SYMBOLS | BUY only | 1d | Implemented, untested clean |
| 11 | `entropy_adaptive_rsi` | All CRYPTO_SYMBOLS | BUY only | 1d | Implemented, untested clean |
| 12 | `coingecko_trending_volume` | All CRYPTO_SYMBOLS | BUY only | 1d | Implemented, untested clean |
| 13 | `altcoin_season_rotation` | ETH-USD, SOL-USD | BUY only | 1d | Implemented, untested clean |
| 14 | `ape_wisdom_social_momentum` | Top 20 ApeWisdom tickers | BUY only | 1d | Implemented, capped at 3 signals |
| 15 | `btc_dominance_reversal` | ETH-USD, SOL-USD, LINK-USD | BUY only | 1d | Implemented, capped at 2 signals |
| 16 | `crypto_weekend_drift` | BTC-USD, ETH-USD, SOL-USD, DOGE-USD | BUY only | 1d | Implemented, Thu/Fri only |

All 16 strategies are **BUY-only (LONG-only)**. None emit SHORT signals. All use `_atr_tp_sl()` for TP/SL calculation. None have been validated on clean-cohort data.

### 1.2 alpha_engine/antigravity_strategies.py — Scanner Adapters

Located at `alpha_engine/antigravity_strategies.py` (1023 lines). Wraps Google Antigravity (Gemini) `baby_strategies/` into the alpha_engine scanner convention. CRYPTO symbol universe:

```
BTC-USD, ETH-USD, SOL-USD, BNB-USD, XRP-USD,
DOGE-USD, ADA-USD, AVAX-USD, TRX-USD, DOT-USD,
LINK-USD, LTC-USD, BCH-USD, SHIB-USD, SUI-USD,
INJ-USD, NEAR-USD, HBAR-USD, ARB11841-USD, OP-USD,
FET-USD, TIA-USD, SEI-USD, AAVE-USD, ETC-USD
```

Strategies from `baby_strategies/`:
- `vwap_rsi_institutional` (claimed 65-72% WR — unverified)
- `liquidation_cascade_contrarian` (claimed 58-65% WR — unverified)
- `regime_sentinel_composite` (meta-filter, +10-15% WR boost — unverified)
- `rsi_pairs_arbitrage` (claimed 70-78% WR — unverified)

CRYPTO pairs for RSI pairs arbitrage: (BTC,ETH), (BTC,SOL), (ETH,SOL), (LINK,AVAX), (ADA,DOT).

### 1.3 KIMI_RISEOFTHECLAW/ — `kimi_strategy_tracking` (Fill Bug Source)

Located at `KIMI_RISEOFTHECLAW/` — 70+ files including `kimi_strategy_tracking` logic, `proven_crypto_forex_strategies.py`, `crypto_acceleration_engine.py`, `renaissance_killer.py`, `rigorous_backtest.py`, `backtest_engine.py`, `scanner.py`, `live_scanner.py`, `paper_trade.py`, `forward_signals.py`, `live_picks_tracker.py`, `consistency_validator.py`, `consistency_validator_v2.py`, `emergency_triage.py`, `spike_predictor.py`.

**Key finding:** This is the source of the `kimi_strategy_tracking` stale fill data bug. ~90% of crypto positions never resolve because fill data is stale/absent. The `kimi_riseoftheclaw` fill bug is the named blocker for CRYPTO in every asset-class plan.

### 1.4 ml_crypto_predictor/ — ML Crypto Prediction Pipeline

Located at `ml_crypto_predictor/` — ML training, inference, and pick generation for crypto:
- `train_swing_models.py`, `train_scalping_models.py`, `train_base_models.py`, `train_ensemble.py`
- `backtest_ml.py`, `optimize_tp_sl.py`, `production_engine.py`, `run_real_backtest.py`
- `enhanced_models/live_picks_tracker.py`, `enhanced_models/realistic_backtester.py`
- `enhanced_models/prove_edge.py`, `enhanced_models/export_picks.py`
- `models/scalping/scalp_results.json`, `models/training_results.json`
- Results: `enhanced_models/results/v4_proof_report.json`, `v4_comprehensive_report.json`, `validation_gauntlet.json`

Live picks tracker (`enhanced_models/live_picks_tracker.py:391-396`) emits 9 BTC/ETH/SOL/XRP/ADA/AVAX/DOT/LTC/BCH picks.

### 1.5 ml_battleground/ — Multi-System Crypto Battleground

Located at `ml_battleground/` — 6 systems (A-F) with shared infrastructure:
- `system_a_filter/` — ML-filtered scanner
- `system_b_*`, `system_c_deeplearn/`, `system_d_carry/`, `system_e_momentum/`, `system_f_clawsofdoom/`
- Shared: indicators, cost model, validator, risk manager, drift monitor, feedback loop
- Data: `dashboard.json`, `closed_picks.json`, `active_picks.json` per system
- `abc_forward_test/` — Approach A/B/C forward test pick data
- `drift_state/*.json` — per-system drift state

### 1.6 coinglass_strategies/ — Coinglass On-Chain/Futures Data Strategies

Located at `coinglass_strategies/` — 10 strategies in `strategies/`:
- `top_trader_divergence.py`, `sentiment_index.py`, `funding_confirmation.py`, `ratio_momentum.py`
- `roll_yield.py`, `risk_parity.py`, `news_sentiment.py`, `extreme_reversion.py`
- `calendar_spread.py`, `options_volatility.py`, `base.py`, `leverage_adjusted.py`
- `spike_detection.py`, `cross_exchange_spread.py`
- `scanner.py`, `signal_engine.py`, `data_fetcher.py`, `paper_portfolio.py`

### 1.7 Other Crypto-Related Files

| File | Purpose |
|------|---------|
| `alpha_engine/basis_carry.py` | Futures premium/discount (BTCUSDT, ETHUSDT, SOLUSDT) |
| `alpha_engine/funding_rate_arb.py` | Funding rate arbitrage scanner |
| `alpha_engine/btc_breakout_strategy.py` | BTC breakout strategy |
| `alpha_engine/trust_score.py` | References "1,879 closed crypto picks" (do not add back) |
| `alpha_engine/emergency_mutations.py` | Flags `ml_enhanced_BTCUSDT_15m_D_ensemble_stack` — 10 trades, 0% WR, SHORT-biased |
| `elite_scorer.py` | Crypto-specific scoring (BTCUSDT/ETHUSDT tier bonuses, micro-cap penalty for alts) |
| `tools/crypto_ml_edge/scanner.py` | Filters clean picks (`entry_price > 0`) |

---

## 2. Backtest Results for Crypto Strategies

### 2.1 Source: `2026-11-15_12AM_plan/flaxen-hair/02_holding_period_analysis/backtest_results.json`

42 combinations tested across 10 symbols, 6 strategies. **All crypto results below:**

| Symbol | Strategy | Trades | WR | Profit Factor | Sharpe | MaxDD | PnL % | p-value | Avg Hold Bars |
|--------|----------|--------|-----|---------------|--------|-------|-------|---------|---------------|
| BTC-USD | connors_rsi2 | 3 | 33.33% | 0.372 | -0.485 | -17.6 | -11.04% | 1.0 | 24.7 |
| BTC-USD | keltner_compression_v2 | 8 | 37.5% | 0.713 | -0.147 | -31.0 | -11.49% | 0.855 | 19.5 |
| BTC-USD | ema_stack | 11 | 45.45% | 1.045 | 0.019 | -15.7 | +1.66% | 0.726 | 24.5 |
| BTC-USD | funding_sentiment | 10 | 50.0% | 0.297 | -0.481 | -48.75 | -39.28% | 0.623 | 18.8 |
| ETH-USD | connors_rsi2 | 4 | 25.0% | 0.618 | -0.232 | -25.91 | -9.9% | 1.0 | 9.2 |
| ETH-USD | keltner_compression_v2 | 11 | 54.55% | 1.675 | 0.238 | -54.12 | +36.54% | 0.5 | 16.8 |
| ETH-USD | ema_stack | 12 | 58.33% | 1.855 | 0.270 | -27.63 | +40.13% | 0.387 | 16.7 |
| ETH-USD | funding_sentiment | 11 | 27.27% | 0.469 | -0.374 | -57.2 | -52.16% | 0.967 | 12.7 |

**Key observations:**
- Every BTC-USD strategy has **PF < 1.5** and **WR < 50%** (ema_stack at 45.45% is closest but still below).
- Every BTC-USD strategy has **negative PnL** except ema_stack (+1.66%, n=11 — statistically insignificant).
- Sharpe is negative for connors_rsi2 (-0.485), keltner_compression_v2 (-0.147), funding_sentiment (-0.481).
- p-values are all ≥ 0.5 (except 1.0 for tiny samples) — no statistical significance.
- Sample sizes are tiny (3-12 trades) — statistically meaningless.
- ETH-USD shows superficially positive numbers (ema_stack PF 1.855, WR 58.33%, +40.13%) but n=12 and MaxDD -27.63% — still not money-ready.
- Funding sentiment on ETH-USD lost -52.16% with 57.2% max drawdown.

### 2.2 Source: `research/profitability/` — Hypothesis Registry (v1-v4)

CRYPTO hypotheses all **NOT_PROVED**:

| ID | Hypothesis | Universe | Status | Final OOS Evidence |
|----|-----------|----------|--------|-------------------|
| H1 | BTC 200d TSMOM, long/flat | BTCUSDT | NOT_PROVED | Sharpe 0.60, CAGR 16.5%, n=29; no edge over B&H |
| H2 | ETH 200d TSMOM, long/flat | ETHUSDT | NOT_PROVED | Sharpe 0.47, CAGR 11.5%, n=21 |
| H3 | XS crypto momentum, weekly top-3 | 10 majors | NOT_PROVED | Sharpe −0.00, CAGR −19.2% |
| H4 | Crypto RSI(2) | BTC/ETH/SOL | NOT_PROVED | Sharpe 0.06, CAGR −4.6% |
| H13 | Crypto XS momentum, top quintile | 30 pairs | NOT_PROVED | Sharpe −0.18, CAGR −31.9%, SPA 0.488 |
| H14 | Crypto short-term reversal, long losers | 30 pairs | NOT_PROVED | Sharpe −0.36, CAGR −44.3% |
| H15 | Crypto TSMOM breadth, vol-targeted | 20 pairs | NOT_PROVED | Sharpe 0.20, CAGR −2.9% |
| H20 | Crypto momentum + BTC trend filter | 30 pairs | NOT_PROVED | Sharpe −0.08, CAGR −21.3% |
| H21 | Funding carry, top 5 positive | 30 perps | NOT_PROVED | Capital-adjusted CAGR 3.7% < cash 4.5% |
| H22 | Funding carry, BTC only | BTC perp | NOT_PROVED | n=10 < 30 minimum |
| H23 | Funding carry, top 10 positive | 30 perps | NOT_PROVED | Capital-adjusted CAGR 4.1% < cash 4.5% |

### 2.3 Peer Review Consolidated Findings (01-crypto.md)

CRYPTO has **no statistically distinguishable edge**; do not size:
- V4 RSI5070: Net PF 1.113, CI-LB 0.916 → gate FAIL below promotion bar
- V2: CRYPTO `NOT_READY`, policy-clean n=21,988, WR 42.35%, PF 0.2595, z=−22.69, single_source_pct=0.9895 → single-source artifact
- V3 cites v1: PF 0.93, z=−7.1 (worse than random)
- V4 QW: raw DB PF 0.37, WR 35.9%
- All 3 active picks: `forward_validated=false`, `forward_trades=0`, trust ≤4 WATCH

### 2.4 Policy-Clean Registry Numbers (from pf_registry / money_ready_verdict)

CRYPTO is `NOT_READY`:
- policy-clean n=21,988, WR 42.35%, PF 0.2595, z=−22.69
- single_source_pct=0.9895, is_single_source_artifact=True
- Intrabar cohort: n=3,705, WR 35.87%, PF 0.920

**Dashboard PF inflation:** V4 dashboard shows PF 1.80 vs raw DB PF 0.37 (~5× inflation). Smart Picks PF 9.69 on 3 rows (91.7% `claude_gainer_st` — tiny sample, meaningless).

---

## 3. Current Status of Crypto Picks

### 3.1 dashboard/live_picks.json — Active Crypto Picks

12 entries with `asset_class: "CRYPTO"`:

| ID | Symbol | Strategy | Side | Entry Price | Status | Entry Time | Notes |
|----|--------|----------|------|-------------|--------|------------|-------|
| JNK_ | JNK | bond_yield_momentum | SELL | 92.42 | ACTIVE | 2026-11-15 | Category says "bond" but asset_class=CRYPTO (misclassification) |
| ... | CTA pick (QQQ?) | regime_strong_bull | LONG | ... | ACTIVE | ... | asset_class=CRYPTO |
| inverse_ml_enhanced_RENDERUSDT_1h_D | RENDERUSDT | inverse_ml_enhanced_RENDERUSDT_1h_D | SELL | 1.581 | ACTIVE | 2026-07-11 | Inverse of 0% WR strategy; historical_wr_original=0.2 |
| inverse_ml_enhanced_RENDERUSDT_4h_D | RENDERUSDT | inverse_ml_enhanced_RENDERUSDT_4h_D | SELL | 1.581 | ACTIVE | 2026-07-11 | Inverse of 0% WR strategy; historical_wr_original=0.0 |
| inverse_ml_enhanced_BTCUSDT_15m_D | BTCUSDT | inverse_ml_enhanced_BTCUSDT_15m_D | SELL | 64,179.0 | ACTIVE | 2026-07-11 | Inverse of 0% WR on 10 trades; TP=1.10%/SL=0.88% |
| ml_enhanced_LTCUSDT_4h_A_xgboost | LTCUSDT | ml_enhanced_LTCUSDT_4h_A_xgboost | BUY | 44.75 | ACTIVE | 2026-07-11 | historical_wr=0.667; TP=5.32%/SL=2.28% |
| ml_enhanced_ARBUSDT_1h_D_ensemble_stack | ARBUSDT | ml_enhanced_ARBUSDT_1h_D_ensemble_stack | BUY | 0.091 | ACTIVE | 2026-07-11 | historical_wr=0.667; TP=2.50%/SL=1.00% |
| ml_enhanced_LINKUSDT_4h_A_xgboost | LINKUSDT | ml_enhanced_LINKUSDT_4h_A_xgboost | BUY | 8.0 | ACTIVE | 2026-07-11 | historical_wr=0.75; TP=5.90%/SL=2.53% |
| ml_enhanced_TRXUSDT_4h_D_ensemble_stack | TRXUSDT | ml_enhanced_TRXUSDT_4h_D_ensemble_stack | BUY | 0.3301 | ACTIVE | 2026-07-11 | historical_wr=1.0; TP=2.00%/SL=1.00% |
| ml_enhanced_BNBUSDT_15m_B_lightgbm | BNBUSDT | ml_enhanced_BNBUSDT_15m_B_lightgbm | BUY | 575.69 | ACTIVE | 2026-07-11 | historical_wr=0.60; TP=3.00%/SL=2.00% |

**Summary of active crypto picks:**
- Total active: 12 crypto-classified picks (some misclassified — JNK is a bond ETF)
- Most crypto picks entered 2026-07-11 (stale, >4 months old)
- All `forward_validated: false`
- Most have `historical_wr` claimed but unverified on clean data
- Inverse strategies are inverses of proven-losing strategies (0% WR originals)
- `ml_score: 0.0` on all crypto picks (ML gatekeeper not scoring them)

### 3.2 multi_asset/data/multi_asset_picks.json — No Crypto Picks

All entries in `multi_asset_picks.json` are `asset_class: "FOREX"` (EURUSD, USDJPY, GBPUSD, AUDUSD, NZDUSD — all `forex_rsi2_mean_reversion` strategy). **Zero crypto picks** in the multi_asset pipeline. All are `forward_test_only: true` with `forward_validated: false`.

---

## 4. Key Metrics for Crypto — All Negative or Negative-Adjacent

### 4.1 From Backtests (BTC-USD)

| Strategy | Trades | WR | PF | Sharpe | PnL % | Assessment |
|----------|--------|-----|-----|--------|-------|------------|
| connors_rsi2 | 3 | 33.33% | 0.372 | -0.485 | -11.04% | Fail — negative edge |
| keltner_compression_v2 | 8 | 37.5% | 0.713 | -0.147 | -11.49% | Fail — negative edge |
| ema_stack | 11 | 45.45% | 1.045 | 0.019 | +1.66% | Fail — PF < 1.5, WR < 50%, n too small |
| funding_sentiment | 10 | 50.0% | 0.297 | -0.481 | -39.28% | Fail — catastrophic |

### 4.2 From Clean-Cohort Research

| Metric | Value | Threshold | Pass? |
|--------|-------|-----------|-------|
| Closed picks (clean) | n=1,154 | n≥100 | Yes (size) |
| Win Rate | 32.4% | ≥55% | **Fail** |
| Profit Factor | 0.73 | ≥1.3 | **Fail** |
| Policy-clean PF (registry) | 0.2595 | ≥1.3 | **Fail** |
| Policy-clean WR | 42.35% | ≥55% | **Fail** |
| z-score | −22.69 | >0 | **Fail (worse than random)** |

### 4.3 Universal Statement

**All crypto strategies have PF < 1.5 and WR < 50%.** No crypto strategy in this system has ever passed the clean-cohort screen (700+ strategies tested, ALL fail).

---

## 5. Key Finding: Entry Price Integrity Defect

### 5.1 The Defect

`at_signal_outcomes.entry_price` is **~29% clean**:
- 37% of entries are >10% off the bar
- 7% of entries are >50% off the bar
- Systematic bias: **~+1.3%** (inflates SHORT returns, deflates LONG returns)
- `intrabar_pnl_pct` rides the broken entry_price (derives from it)

Source: `reports/DATA_INTEGRITY_entry_price_2026-07-03.md`, referenced by multiple SKILL.md files (money-maker-ready, money-maker-ready-June112026edition, money-maker-readyv2).

### 5.2 Consequences

- ~90% of positions **never resolve** (stale fill data in `kimi_riseoftheclaw` / `kimi_strategy_tracking`)
- `fetch_current_price()` returns `None` when Binance geo-blocked (HTTP 451) → TP/SL/TIMEOUT checks skipped → positions never resolve
- 88.6% of crypto rows have `current_price = null`; 92.9% have `pnl_pct == 0.0`
- 485/691 OPEN raw rows are unpriced
- Raw `at_pick_outcomes` WR/PF are **inflated artifacts**, not edge

### 5.3 The Fix Required

| Fix | File | Priority |
|-----|------|----------|
| Fix entry_price integrity | `alpha_engine/risk_controls.py` | P0 |
| Re-resolve from bar-aligned NEXT-bar entries | `tools/reresolve_intrabar.py` | P0 |
| Deepen OHLCV history (≥180d 1h bars) | `crypto_ohlcv` ingest | BLOCKED (~30d today) |
| Kill crypto SWING emission | `multi_asset/scanner.py` | P0 |
| Resolve stale open positions (>72h) | `audit_trail/universal_pick_resolver.py` | P0 |

The entry_price must be validated against OHLCV bar integrity. Entries should be re-resolved from bar-aligned NEXT-bar entries (not signal-bar entries, which are look-ahead biased). Signal-bar entry collapsed macd_rsi from 2.47 → 0.37 and every apparent LONG "edge".

---

## 6. Why CRYPTO is Slot 2 Conditional

CRYPTO is the **only asset class with a diagnosed, fixable defect**. Every other asset class either:
- Has no edge at all (FOREX — zero DSR survivors; FUTURES — retired, WR 5.9%, PnL -96%; MEMECOIN/PENNY — quarantined, PF 0.50)
- Is market beta, not alpha (Passive ETF/MF allocation — buy-and-hold index funds)
- Has insufficient data (COMMODITY/BOND — n too small)
- Is degrading (EQUITY — second-half PF fell 1.342 → 0.977)

CRYPTO's path to potential profitability is:
1. **Fix entry_price integrity** (~29% clean → 100% clean)
2. **Fix the fill bug** (`kimi_riseoftheclaw` stale fill data → ~90% positions never resolve)
3. **Forward-test on POSITION horizon only** (not entry-bar), frozen rules, n≥100
4. **Meet gates:** PF ≥ 1.3, WR ≥ 55%
5. **Regime filter:** BTC > 200-EMA (bull regime only)
6. **Correlation limit:** max 1 position per correlated group

**Kill condition:** If post-fix forward test does not show PF ≥ 1.3 at n=100, retire crypto direction trading entirely.

---

## 7. Forward Test Requirement

Before any capital allocation, CRYPTO must pass a clean forward test:

| Parameter | Requirement |
|-----------|-------------|
| Horizon | POSITION horizon only (not entry-bar / signal-bar) |
| Rules | Frozen (no post-hoc optimization) |
| Sample size | n ≥ 100 forward picks |
| Profit Factor | PF ≥ 1.3 |
| Win Rate | WR ≥ 55% |
| Regime filter | BTC > 200-EMA (bull regime only) |
| Correlation limit | Max 1 position per correlated group |
| Data integrity | entry_price 100% clean, OHLCV-bar validated |
| Fill resolution | All positions resolve (no stale fills) |

Current state: **Not met.** n=1,154 clean but WR=32.4%, PF=0.73, entry_price ~29% clean, ~90% positions never resolve.

---

## 8. Why CRYPTO is NOT Deployable Yet

1. **Entry price integrity issue:** entry_price is only ~29% clean (37% >10% off bar, 7% >50%), with systematic +1.3% bias that inflates SHORT and deflates LONG returns. All PnL/WR/PF metrics derived from it are unreliable.

2. **~90% of positions never resolve:** The `kimi_riseoftheclaw` / `kimi_strategy_tracking` pipeline has stale fill data. `fetch_current_price()` returns `None` when Binance is geo-blocked (HTTP 451), causing TP/SL/TIMEOUT checks to be skipped.

3. **All backtest results are negative or negative-adjacent:** Every BTC-USD strategy has PF < 1.5 and WR < 50%. ETH-USD shows superficially positive numbers but with n=10-12 and large drawdowns (up to -57.2%).

4. **700+ strategies tested, ALL fail clean-cohort screen:** No crypto strategy has demonstrated edge on clean data.

5. **Dashboard PF inflation:** V4 dashboard shows PF 1.80 vs raw DB PF 0.37 (~5× inflation). Smart Picks PF 9.69 on 3 rows (tiny sample, meaningless).

6. **No forward validation:** All 3 active crypto picks have `forward_validated=false`, `forward_trades=0`.

---

## 9. Conclusion

CRYPTO is **slot 2 conditional** — the only asset class with a diagnosed, fixable defect. The path forward is clear but unexecuted:

1. Fix `entry_price` integrity in `alpha_engine/risk_controls.py` (P0)
2. Re-resolve from bar-aligned NEXT-bar entries in `tools/reresolve_intrabar.py` (P0)
3. Fix the `kimi_riseoftheclaw` fill bug so positions resolve (P0)
4. Deepen OHLCV history to ≥180d 1h bars (currently ~30d — BLOCKED)
5. Forward-test on POSITION horizon, frozen rules, n≥100, PF≥1.3, WR≥55%
6. If PF ≥ 1.3 at n=100 is not achieved, retire crypto direction trading entirely

**Until the entry_price integrity and fill bugs are fixed, CRYPTO must not emit any signals or receive any capital allocation.**

---

**Document location:** `WIRED_IN/CRYPTO_ASSET_CLASS_AUDIT.md`
**Intended for inclusion in:** WIRED_IN documentation folder (per-asset-class algorithm spec, pick justification, backtest/research evidence, elimination reasoning)
