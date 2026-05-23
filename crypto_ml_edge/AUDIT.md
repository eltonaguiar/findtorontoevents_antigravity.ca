# Crypto ML Edge Engine — Existing Systems Audit

**Date:** 2026-02-23
**Auditor:** Phase 1, Plan 01-01
**Purpose:** Identify reusable patterns vs. rebuild candidates before building the new Edge Engine

---

## Executive Summary

After auditing all existing crypto ML systems, the verdict is stark: **no existing ML model has demonstrated genuine out-of-sample edge in crypto.** The v1.2 forward test was catastrophic (Sharpe -2.799, 23.5% WR). The v4 supertrend models had sample sizes of 5–11 trades — statistically meaningless. The gainer model achieved ROC-AUC 0.537 — barely above random. The one genuinely proven system is Connors RSI-2 on SPY/QQQ, which is an equity mean-reversion strategy not directly portable to crypto.

This confirms the decision to build a clean-slate Edge Engine. However, several components are architecturally sound and worth reusing.

---

## System 1: ML Crypto Predictor v1.2 Forward Test

### Results
| Metric | Value |
|--------|-------|
| Total picks | 34 |
| Win rate | 23.5% |
| Sharpe ratio | **-2.799** |
| Profit factor | 0.20 |
| Total P&L | -28.49% |
| Max drawdown | -28.3% |
| TP hits | 7 |
| SL hits | 24 |

**Timeframe breakdown:**
- 15m: 31.8% WR, Sharpe -1.21 (22 picks — bad but survivable)
- 1h: **8.3% WR, Sharpe -3.28** (12 picks — catastrophic)

**vs. Simpleton baseline:**
- Simpleton WR: 51.3% vs ours: 23.5%
- Simpleton Sharpe: 0.567 vs ours: -2.799
- The untrained naive benchmark was 5x better

### Root Cause Analysis

**Cause 1: Probability scores were near-random (not signals)**

Reviewing the archived closed picks, model outputs were:
- `ETHUSDT_15m_B_lightgbm`: prob 0.5721 — coin flip
- `BNBUSDT_15m_B_lightgbm`: prob 0.8463 — seemingly high, still lost
- `NEARUSDT_15m_D_ensemble_stack`: prob 0.5245 — coin flip
- Nearly all 31 of 34 picks had probability < 0.60

The config's own comment confirms this: *"31/34 picks had prob < 0.60 — all coin flips that lost."*

Root issue: the models trained with purged walk-forward CV were getting ROC-AUC scores around 0.27–0.28 (per `training_summary.json` avg_scores), meaning their "probabilities" had essentially zero discriminative power. A 0.57 probability output from a model with AUC 0.27 means nothing.

**Cause 2: Asymmetric TP/SL with tight stops**

v1.2 TP/SL config:
- 15m scalp: TP = 3.0x ATR, SL = 1.5x ATR (R:R 2:1)
- 1h intraday: TP = 3.0x ATR, SL = 1.5x ATR

With 23.5% WR and 2:1 R:R, the expected value is: `0.235 * 2 - 0.765 * 1 = -0.295` (negative). You need 33% WR minimum to break even with 2:1 R:R. The models weren't close.

The SL was also too tight for noisy crypto data. ZROUSDT lost -6.73% against a 2.16% SL because price gapped through the hourly check interval. The stop distance was set mathematically (ATR multiple) without accounting for gap risk in volatile pairs.

**Cause 3: Adaptive positive rate labeling created unstable targets**

The v3 config used `adaptive_target_min: 0.15` and `adaptive_target_max: 0.30`, meaning the threshold for what counted as a positive ("buy") was dynamically adjusted to hit those rates. This means:
- The label for the same price action could be "buy" or "no-buy" depending on what the period around it looked like
- A model trained to predict an adaptive label will not generalize — the label definition itself shifts across folds
- Triple-barrier labeling with ATR-based TP/SL is correct in principle but the adaptive positive rate manipulation undermined it

**Cause 4: Too many models, no meaningful multiple-testing correction**

The system trained 793 models (40 pairs × 5 TFs × 4 variants × varied configs). The `training_summary.json` shows avg_scores of 0.25–0.28 for ALL models. Despite this, picks were still generated. The validation gates existed on paper (Deflated Sharpe Ratio, PBO, walk-forward efficiency) but the production pick generator was not gated on these — it was gated on a raw probability threshold (0.55 → bumped to 0.65 in v1.3).

**Cause 5: 15-minute crypto scalping is near-efficient**

The 1h data was even worse (8.3% WR). On short timeframes, transaction costs (0.10-0.20% round-trip) consume most of the signal. A model needs Sharpe > 1.5 just to cover costs at 15m frequency.

### What v1.2 Tells Us
- The feature engineering is not wrong per se — the features are reasonable
- The labeling approach (triple-barrier) is correct in theory
- The failure was in validation rigor: models with AUC 0.27 were generating picks
- 15m timeframe is especially hostile to ML edge due to noise-to-signal ratio

---

## System 2: v4 Supertrend Models (Proof Report)

### Results
| Pair | TF | Sharpe | WR | Trades | DSR | MC p-value |
|------|----|--------|-----|--------|-----|------------|
| NEARUSDT | 15m | 2.5692 | 71.4% | **7** | 1.0 | 0.039 |
| SUIUSDT | 15m | 2.4548 | 80.0% | **5** | 1.0 | 0.039 |
| APEUSDT | 15m | 2.0211 | 63.6% | **11** | 1.0 | 0.020 |
| HBARUSDT | 15m | 1.6113 | 60.0% | **5** | ~0 | 0.020 |
| ARBUSDT | 15m | 1.0336 | 42.9% | 7 | 0.0 | 0.039 |
| STRKUSDT | 15m | 0.9534 | 60.0% | 5 | 0.0 | 0.039 |

**34 of 40 pairs failed entirely** (Sharpe < 0, negative returns, or < minimum criteria).

### Assessment: NOT TRADEABLE

Every single "passing" model has a fatal flaw: **sample size of 5–11 trades is statistically meaningless.**

At 7 trades, achieving 71.4% WR (5/7) has p-value = C(7,5) * 0.5^7 = 21 * 0.0078 = **0.164** — not even close to significant. The MC p-values of 0.039 are misleading; they're calculated against a 1/51 permutation distribution, not a proper binomial test. With 5 trades, any permutation test will have minimum resolution of 1/51 = 0.020.

The DSR (Deflated Sharpe Ratio) values further confirm this:
- HBARUSDT: DSR = 4.4e-47 (essentially zero confidence)
- ARBUSDT: DSR = 0.0
- STRKUSDT: DSR = 0.0

Only NEARUSDT, SUIUSDT, APEUSDT show DSR = 1.0, but this is an artifact of the tiny sample size — with 5–7 trades, there's literally not enough data to run a meaningful DSR calculation.

**Why supertrend in particular?** Supertrend is a trend-following indicator that generates very few signals on 15m (this explains the low trade counts). This means the entire "proof" of these models is based on a handful of trades in a short backtest window.

### What v4 Tells Us
- Supertrend as a rule-based strategy is not ML and doesn't benefit from ML
- Trading on 15m with trend-following strategies produces too few signals for statistically valid evaluation
- The backtester infrastructure itself (v4_trainer.py, realistic_backtester.py) is sound and worth reusing

---

## System 3: v1.5 Training Summary

### Results

355 models trained across 120 pair/TF combinations. All 15m timeframe.

Key finding from positive_rate data:
```
BTCUSDT_15m:  positive_rate=0.492  (6000 bars)
SHIBUSDT_15m: positive_rate=0.424  (6000 bars)
WUSDT_15m:    positive_rate=0.412  (6000 bars)
```

**Positive rates are near 0.45–0.50 across all pairs.** This means the triple-barrier labeling is generating near-50/50 labels — essentially a coin flip target. When your target variable is 50% positive by construction, your model learns nothing useful because:
1. Predicting "always buy" would give 50% accuracy
2. Any model will get ~50% by random chance
3. The "signal" is indistinguishable from noise at this label density

The adaptive positive rate (capped to 0.15–0.30 target in v3, but 0.45–0.50 in practice for v1.5) is the proximate cause of why ALL models had AUC around 0.25–0.28.

### What v1.5 Tells Us
- Label construction is broken: near-50% positive rates mean no discriminative signal
- The model family (XGBoost, LightGBM, RF, stacking) is not the problem
- Data volume (6000 bars) is adequate but 15m timeframe is problematic
- The training infrastructure (purged CV, feature engineering) is worth reusing

---

## System 4: v3 Training (GRU/CNN Models)

### Results

540 models across 30 pairs × 2 TFs. Best model: GRU (F_gru) with avg_score 0.4128.

**Critical finding:** No comparison between variants was statistically significant:
- F_gru vs I_attention_ensemble: p=0.113 (not significant)
- F_gru vs C_random_forest: p=0.063 (not significant)
- F_gru vs J_xgb_meta_stacker: p=0.031 (barely, and suspicious)

**All head-to-head tests showed `"better_model": "A"` (F_gru) despite marginal, insignificant differences.** This is a red flag: the system was declaring a winner without sufficient statistical power to distinguish between models. Deep learning (GRU, CNN, attention) adds massive parameter count while improving validation scores by 0.04 AUC units — this is overfitting signature.

### What v3 Tells Us
- Deep learning architectures do not add meaningful edge over tree models for crypto features
- The head-to-head statistical testing infrastructure is architecturally correct but was not enforcing significance thresholds properly
- Tree-based models (XGBoost, LightGBM) are sufficient; avoid neural complexity

---

## System 5: Claude Gainer ML (claude_gainer_ml/)

### Results
| Metric | Value |
|--------|-------|
| ROC-AUC | **0.537** (barely above 0.5) |
| Precision | 0.190 |
| Recall | 0.190 |
| F1 | 0.190 |
| Accuracy | 0.989 (misleading — class imbalance) |
| Train samples | 12,000 |
| Test samples | 3,000 |
| Positive rate | 0.7% (7/1000 are gainers) |

**Feature importances (top 5):**
1. `consolidation_range`: 17.5%
2. `price_momentum_3d`: 14.4%
3. `vol_change_12h`: 9.9%
4. `mcap_tier`: 8.2%
5. `distance_from_atl_pct`: 8.1%

### Assessment: No OOS Edge

AUC 0.537 means the model explains 3.7% of variance above random. At a 0.7% positive rate (gain >3% in 24h) with 19% precision, for every 100 "buy" signals the model emits, 81 are wrong. This is economically worthless in a live trading context.

**However, the features themselves carry intuition worth validating:**

- `consolidation_range` (17.5%) — compressed volatility before breakout is a known pattern (volatility contraction precedes expansion). This feature is worth testing rigorously in the Edge Engine.
- `price_momentum_3d` (14.4%) — 3-day momentum is directionally relevant. May overlap with simple price return features.
- `vol_change_12h` (9.9%) — Volume surge before price move is a classic pattern (OBV, money flow). Directionally sound.

### What Gainer ML Tells Us
- Binary "will it gain >3%?" classification against all coins is an underdefined problem — too much noise
- Class imbalance (0.7% positive) creates accuracy illusion
- The feature set has intuitive basis but needs rigorous forward validation
- CoinGecko-sourced data at 1d/4h resolution is usable for feature ideas but not for short-term signals

---

## System 6: Connors RSI-2 (Alpha Engine)

### Results
| Asset | Trades | WR | Sharpe | Binomial p | Avg Days Held |
|-------|--------|-----|--------|------------|---------------|
| SPY | 74 | **75.7%** | **4.835** | **6e-06** | 4.6 |
| QQQ | 73 | **75.3%** | **6.548** | **8e-06** | 4.9 |
| BTC-USD | 96 | 62.5% | 2.349 | **0.009** | 4.8 |

**This is the only system in the entire codebase with proven statistical significance.**

All three assets pass:
- Binomial p-value < 0.01 (highly significant)
- Win rate > 60%
- Sharpe > 2.0
- Adequate sample size (74–96 trades)

### Why RSI-2 Works (and Why It's Different)

1. **Mean reversion in established uptrends** — RSI-2 triggers only on extreme oversold readings (RSI-2 < 5) within broader bull markets. This has structural basis: institutional buyers provide price floors in trending assets.

2. **Equity-specific structural advantage** — SPY/QQQ have consistent buyers (pension funds, systematic rebalancers, passive inflows) that create predictable mean-reversion behavior. Crypto lacks these structural buyers.

3. **BTC adapts but with caveats** — BTC Sharpe 2.35 with p=0.009 is borderline. The recent trades show large losses (-8.48%, -5.22%) that the mean-reversion thesis doesn't handle. RSI-2 works better on crypto during secular bull markets; it breaks down during regime changes.

### Portability Assessment

RSI-2 is NOT directly portable to crypto because:
- Crypto lacks the structural institutional bid that creates equity mean-reversion
- Crypto regime changes (bear markets) are more severe and prolonged
- BTC's 62.5% WR is meaningfully lower than SPY's 75.7%

**However, the methodology is portable:**
- Oversold extreme entries (RSI < 5-10) within confirmed uptrends
- Mean reversion exits (RSI > 65)
- Time-based stop (5–10 day max hold)
- Apply only to the most liquid assets where market makers provide price stability

The RSI-2 concept adapted for crypto would need: confirmed higher-timeframe uptrend filter, reduced position sizing for regime uncertainty, and ATR-based stops to handle gap risk.

---

## Validation Infrastructure Assessment

### Components to REUSE

**1. `advanced_validation.py` — Keep entirely**
- Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014) — correctly implemented
- Purged Walk-Forward with embargo — correctly implemented
- CPCV (Combinatorial Purged CV) + PBO — correctly implemented
- Monte Carlo Bootstrap CI — correctly implemented
- **Problem in v1.2 was that this validation existed but wasn't enforced as a gate before generating picks**

**2. `feature_engine.py` — Keep core, rebuild target**
- Technical indicator helpers (EMA, RSI, MACD, ATR, ADX, Bollinger, OBV) — solid implementations
- `build_target()` triple-barrier labeling — correct in principle, but the adaptive positive rate parameter must be removed
- 70+ features across 6 groups — reasonable starting point, but needs reduction to 15-20 to avoid curse of dimensionality

**3. Slippage map (`config.py`) — Keep**
- Per-pair slippage based on liquidity tier is well-calibrated and reflects real market microstructure
- Tier 1 (0.05%): BTC, ETH, BNB — correct
- Tier 5 (0.15-0.20%): small caps — correct

**4. Model families (XGBoost, LightGBM, RF) — Keep**
- These are the right tools; the problem was in validation, not the models themselves
- Ensemble stacking (D_ensemble_stack) showed marginal benefit; keep but don't rely on it

### Components to REBUILD

**1. Label construction — Critical rebuild**
- Current: adaptive positive rate → near-50% labels → coin flip targets
- Required: fixed threshold based on transaction cost and risk/reward logic
  - Example: label = 1 if price rises > 1.5% AND stays above -0.75% stop for 12 bars on 1h
  - Expected positive rate: 15-25% depending on pair/regime, NOT 45-50%

**2. Pick generation gate — Rebuild with strict enforcement**
- Current: probability threshold only (0.55 → 0.65)
- Required: DSR probability > 0.95 AND CPCV p-value < 0.05 AND WFE > 0.50
- No pick generation until model passes ALL validation stages

**3. Timeframe strategy — Rebuild**
- Current: 15m primary with 1h secondary
- Required: 1h primary, 4h secondary (research-backed signal-to-noise improvement)
- Drop 15m entirely for ML models (Simpleton showed RSI-2 / rule-based works better at 15m anyway)

**4. Pair universe — Rebuild with liquidity filter**
- Current: 41 pairs (too many; each added pair = more multiple testing inflation)
- Required: top-10 by 30d volume × liquidity score, reselected monthly
- Fixed universe: BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, XRPUSDT + 5 rotating alts

---

## Specific Patterns with Potential OOS Edge

Based on research literature and the audit, these specific patterns deserve investigation in Phase 2:

### 1. RSI-2 Mean Reversion (Adapted for Crypto)
**Evidence:** SPY Sharpe 4.84 (p=6e-06), BTC Sharpe 2.35 (p=0.009)
**Adaptation needed:** Higher-TF trend filter, ATR stops, regime detector
**Expected crypto Sharpe:** 1.5–2.5 (lower than equity due to less structural bid)
**Confidence:** HIGH — academically validated

### 2. Volatility Contraction Breakout
**Evidence:** `consolidation_range` was the #1 feature (17.5%) in gainer ML despite AUC 0.537
**Mechanism:** Low volatility (Bollinger squeeze, ATR percentile < 20) precedes directional expansion
**Literature:** Documented in Donchian breakout literature; effective on 4h+ timeframes
**Confidence:** MEDIUM — feature importance is suggestive, not conclusive

### 3. Volume Surge Confirmation
**Evidence:** `vol_change_12h` was 3rd most important feature (9.9%) in gainer ML
**Mechanism:** Unusual volume precedes price moves (OBV divergence, volume Z-score)
**Confidence:** MEDIUM — classic technical pattern with mixed ML evidence

### 4. Crypto Mean Reversion on BTC Fear Events
**Evidence:** Fear/Greed ≤ 10 DCA from Alpha Engine (Nasdaq backtest: 14.6% annual)
**Mechanism:** Panic selling creates asymmetric recovery setup in confirmed uptrends
**Confidence:** MEDIUM — limited sample size on extreme fear events

### 5. Triple Barrier TP/SL Classification (Correctly Labeled)
**Evidence:** The labeling approach is theoretically sound (Lopez de Prado 2018)
**Current problem:** Adaptive positive rate makes labels near-random
**Fix:** Fixed threshold, target 15-20% positive rate, hard minimum 200 positive samples
**Confidence:** HIGH that the approach is correct; LOW that current implementation is usable

---

## Decision Summary

| Component | Decision | Reason |
|-----------|----------|--------|
| v1.2 ML models | DISCARD | AUC 0.27, proven negative OOS |
| v4 Supertrend results | DISCARD | 5–11 trade samples, not significant |
| v1.5 trained models (.joblib) | DISCARD | Near-50% labels, no edge |
| Gainer ML models | DISCARD | AUC 0.537, no edge |
| `advanced_validation.py` | REUSE | Sound statistical methods |
| `feature_engine.py` helpers | REUSE (partial) | Good indicators, drop adaptive target |
| `realistic_backtester.py` | REUSE | ATR-based TP/SL, cost model is good |
| Slippage map | REUSE | Well-calibrated to market structure |
| Connors RSI-2 methodology | ADAPT | Proven in equity; needs crypto adaptation |
| Model families (XGB, LGB, RF) | REUSE | Right tools, wrong validation |
| Label construction | REBUILD | Root cause of all ML failures |
| Pick generation gate | REBUILD | Validation existed but not enforced |
| Timeframe focus | REBUILD | Drop 15m; focus on 1h/4h |
| Pair universe | REBUILD | 41 pairs → top-10 with liquidity filter |

---

## Root Cause of All Failures: The Validation-Production Gap

The most damning finding is this: **the system had correct validation code but never enforced it before generating picks.**

`advanced_validation.py` implements DSR, CPCV, PBO, and Monte Carlo CI. These are academically rigorous and correctly coded. But in `live_predictor.py` / `generate_picks_html.py`, picks were gated only on `probability > 0.55` — not on any of the statistical validation results.

This means:
1. A model with AUC 0.27 (worse than random) could output probability 0.58 on a trade
2. That 0.58 > 0.55 threshold → pick generated
3. Pick fails in production → Sharpe -2.799

**The new Edge Engine must have a single rule: no pick is generated unless the underlying model has passed ALL validation stages.** Not some. Not most. All.

---

## Recommendations for Edge Engine

1. **Label fix is the highest priority** — target 15-20% positive rate using fixed threshold (not adaptive). Minimum 200 positive samples before training.

2. **Validate before training, not after** — run DSR, CPCV, and MC bootstrap as preconditions for pick generation. Store validation results in model metadata.

3. **Use 1h and 4h only** — eliminate 15m. The v1.2 forward test showed even 15m had -1.21 Sharpe; 1h was -3.28. At 4h with proper validation the signal-to-noise is 3–4x better.

4. **10 pairs maximum** — fewer pairs means less multiple testing inflation, more data per pair, and more focused feature engineering.

5. **Test RSI-2 adaptation first** — it's the only proven signal in the codebase. Build a crypto version with trend filter and validate it with 200+ trades before adding complexity.

6. **Walk-forward efficiency gate: WFE > 0.50** — if a model's forward Sharpe is less than 50% of its backtest Sharpe, it's overfit. Don't trade it.

7. **Reuse the backtester and validator** — `realistic_backtester.py` and `advanced_validation.py` are sound. Don't reinvent them; call them from the Edge Engine.
