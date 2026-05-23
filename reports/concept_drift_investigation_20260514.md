# Concept Drift Investigation — KS_D=0.313 (6.6× Critical)
**Date:** 2026-05-14 | **Trigger:** Money-Maker-Ready audit drift_alert flag

---

## 1. What the Numbers Mean

| Metric | Current (May 14) | April 6 (5 weeks ago) | Change |
|---|---|---|---|
| KS_D | 0.3126 | 0.1124 | **+178% worse** |
| Critical value (α=0.05) | 0.0473 | 0.0481 | — |
| **Severity** | **6.61× critical** | 2.34× critical | **2.8× worse** |
| Variance ratio | 1.07 (normal) | 0.29 (below 0.4) | Var stabilized but distribution worsened |
| Sample split | 1654 / 1654 | 1596 / 1597 | Growing |

**The drift is accelerating.** 5 weeks ago it was already 2.3× critical. Now it's 6.6× — the PnL distribution of the second half of trades is fundamentally different from the first half.

---

## 2. What Drifted: CRYPTO Broke Down

### Per-asset-class health snapshot

| Asset Class | Sharpe | PF | MDD | Win Rate | Verdict |
|---|---|---|---|---|---|
| **BOND** | 1.92 | 1.60 | 3.1% | — | ✅ Healthy |
| **EQUITY** | 2.23 | 1.44 | — | — | ✅ Healthy |
| **ETF** | 0.62 | 1.10 | — | — | 🟡 Stable |
| **COMMODITY** | 0.22 | 1.09 | — | — | 🟡 Marginal |
| **FOREX** | −0.04 | 0.97 | — | — | 🟠 Bleeding |
| **CRYPTO** | **−0.60** | **0.89** | **674.7%** | — | 🔴 Primary drift source |

**The KS_D=0.313 is overwhelmingly driven by CRYPTO.** EQUITY and BOND are performing well. The distribution shift isn't broad market — it's concentrated in the asset class with the most trades and models.

---

## 3. The Inflection Point: Mid-April 2026

Rolling window metrics show exactly when the drift crystallized:

| Window End | Sharpe | Sortino | Max DD | Win Rate |
|---|---|---|---|---|
| Apr 15 | +1.21 | +2.08 | 64.0% | ~50% |
| Apr 17 | **+1.38** | **+2.41** | 64.0% | ~50% |
| **Apr 19** | **−0.80** | −1.42 | **721.9%** | ~43% |
| Apr 20 | −0.56 | −1.01 | 721.9% | ~43% |
| Apr 22 | +0.17 | +0.26 | 721.9% | ~43% |

**Between April 17-19, 2026:**
- Sharpe flipped from +1.38 → −0.80 (a 2.2 Sharpe swing in 2 days)
- Max drawdown exploded from 64% → 722%
- Win rate dropped 7+ percentage points
- The damage was permanent — Sharpe never recovered above 0.2

**This is a regime change, not noise.** Something fundamentally shifted in crypto markets around April 18, 2026.

---

## 4. Model Health: Calibration Shattered

The ML gatekeeper model (`model_drift.json`, April 23):

| Metric | Baseline | Current | Change |
|---|---|---|---|
| Expected Calibration Error | 0.0019 | 0.2777 | **143× increase** |
| Recent Win Rate | — | 75.9% | |
| Recent Samples | — | 29 | Insufficient |
| Status | — | `needs_retraining` | 🔴 |

A 143× ECE increase means the model's probability estimates (e.g., "85% confidence this is a winner") are completely detached from reality. The model is producing confident wrong predictions.

**This is the mechanism:** The ML models were trained on pre-April data distribution. After the April 18 regime change, the same features map to different outcomes, but the models still output the old calibrated probabilities.

---

## 5. Strategy-Level Gini Impurity (April 3 — already stale)

Selected strategies and their Gini impurity (0=dead, 1=suspicious perfect separation):

| Strategy | Gini | Status |
|---|---|---|
| `quick_engine` | 1.00 | ⚠️ Perfect separation — overfit |
| `crypto_adx_pullback` | 1.00 | ⚠️ Perfect separation — overfit |
| `vwap_dev_reversion_sol` | 1.00 | ⚠️ Perfect separation — overfit |
| `vwap_dev_reversion_eth` | 1.00 | ⚠️ Perfect separation — overfit |
| `drawdown_recovery_rsi_sol` | 1.00 | ⚠️ Perfect separation — overfit |
| `crypto_kalman_trend` | 1.00 | ⚠️ Perfect separation — overfit |
| `crypto_rsi_whale` | 1.00 | ⚠️ Perfect separation — overfit |
| `ml_crypto_predictor` | 0.389 | 🔴 Weak — below 0.5 threshold |
| `funding_momentum` | 0.00 | 💀 Dead strategy |
| `keltner_compression` | 0.00 | 💀 Dead strategy |
| `vwap_dev_reversion_xrp` | 0.00 | 💀 Dead strategy |
| `drawdown_recovery_rsi_eth` | 0.00 | 💀 Dead strategy |
| `st_fear_greed_contrarian` | 0.105 | 🔴 Near-dead |

**7 strategies show Gini=1.0** (perfect train-set separation, virtually guaranteed overfit). **4 strategies are dead** (Gini=0.0 — random noise). Only a handful in the 0.5-0.9 range are plausibly real.

---

## 6. What Already Exists: Defense Layers

The system already has drift-defense mechanisms, but their effectiveness is limited:

| Defense | What It Does | Limitation |
|---|---|---|
| `drift_aware_scoring.py` | Drops score multiplier 0.5–1.0 based on WR decline | **Reactive** — only applies AFTER drift is measured. Can't prevent the initial damage. |
| `charter_drift_circuit_breaker.py` | Flips position sizing to 0 when WR >2σ below baseline | **Good** but needs n≥30 to fire. Thin-sample strategies slip through. |
| `model_calibration.py` | Detects ECE drift, flags `needs_retraining` | Flags correctly but **retraining doesn't auto-trigger**. |
| `feature_stability_monitor.py` | Tracks feature importance CV across cycles | **Only 1 training cycle** — no stability data. |
| `ml_drift_repair_workflow.py` | Repair workflow for drifted models | Exists but unclear if it runs on schedule. |

---

## 7. Verdict & Recommendations

### 🔴 CRYPTO models need retraining NOW.

The drift is 6.6× critical, concentrated in crypto, and the ML model's calibration is 143× worse than baseline. The mid-April regime change broke the feature→outcome mapping.

### P0 — Immediate (today)

1. **Retrain all CRYPTO ML models** on post-April-18 data. The pre-April distribution is obsolete.
2. **Raise the circuit breaker sensitivity** for crypto: lower n-guard from 30 → 15 for crypto asset class (thin-sample strategies are the most dangerous).
3. **Add `drift_alert_hot` gate** to Smart Picks → temporarily exclude ALL crypto picks until retraining completes.

### P1 — This week

4. **Investigate the April 18 regime change:** What happened in crypto markets that day? (BTC/ETH price action, funding rate spike, volatility regime shift, exchange liquidity event?)
5. **Run feature importance drift** across pre/post-April split to identify which features broke.
6. **Mark the 7 Gini=1.0 strategies** as overfit and gate them from Smart Picks / High Conviction.

### P2 — Next sprint

7. **Auto-retraining pipeline:** Wire `model_calibration.needs_retraining=TRUE` to trigger automated retraining with notification, not just flagging.
8. **Increase feature_stability_monitor frequency** — 1 training cycle is useless for stability detection. Need ≥5.
9. **Add per-asset-class drift tracking** to `hf_stats.py` — current KS_D is aggregate, masking that BOND and EQUITY are fine.

---

## 8. What NOT to Do

- ❌ Don't retrain EQUITY/BOND models — they're performing well, retraining on drifted crypto data would poison them
- ❌ Don't disable the drift_aware_scoring penalty — it's the last line of defense right now
- ❌ Don't increase position sizes on crypto to "recover" the drawdown
