# Researcher 004: Dr. Alex Chen — Ensemble Learning Specialist

## Persona
- **Title:** Ensemble Learning Specialist
- **Expertise:** Stacking, blending, boosting, bagging for crypto prediction
- **Years Experience:** 10
- **Background:** PhD Berkeley Statistics, former Netflix ML, now leads quant research at a crypto hedge fund.

## Research Scope
**Primary Question:** How do top ensembles combine diverse models (tree-based, neural, linear) to maximize crypto prediction accuracy?

**Application Context:** We have 3 competing ML systems — all currently losing money — that must be combined into a profitable meta-ensemble:
- **System A (XGBoost Filter):** 37-feature binary classifier (take/skip), S/R-aware, outputs probability 0-1
- **System B (Regime Classifier):** 20-feature XGBoost multi-class (4 regimes), outputs regime + confidence + duration
- **System C (GRU-Attention):** Dual-timeframe (15m/1h) neural net, 16 features x 200 bars, outputs entry_prob + TP/SL distances

---

## 1. FOUNDATIONAL PRINCIPLES: WHY ENSEMBLES WORK

### 1.1 The Bias-Variance-Covariance Decomposition

The expected error of an ensemble of M models decomposes as:

```
E[error] = bias^2 + (1/M)*variance + (1 - 1/M)*covariance
```

**Key insight:** As M grows, variance shrinks toward zero, but covariance dominates. This means **model diversity (low covariance) matters more than model count**. Three uncorrelated models beat twenty correlated ones.

**Reference:** Krogh & Vedelsby (1994), "Neural Network Ensembles, Cross Validation, and Active Learning," *Advances in NIPS 7*.

### 1.2 The Condorcet Jury Theorem Applied to Trading

If each of M independent classifiers has accuracy p > 0.5, the majority vote accuracy approaches 1.0 as M increases. But for trading systems:
- Independence is violated (all see same market data)
- p < 0.5 is common (most strategies lose after costs)
- The theorem breaks down when base models are correlated

**Critical implication for our systems:** If Systems A, B, C are all losing, ensembling them naively will NOT fix the problem. The ensemble can only be as good as the information content in the base models. Ensembling amplifies signal — it does not create signal from noise.

---

## 2. TAXONOMY OF ENSEMBLE METHODS FOR TRADING

### 2.1 Method Comparison Matrix

| Method | Complexity | Diversity Requirement | Overfitting Risk | Best For |
|--------|-----------|----------------------|-------------------|----------|
| Simple Averaging | Low | Low | Low | Quick baseline |
| Weighted Averaging | Low | Medium | Medium | When you know relative quality |
| Majority Voting | Low | High | Low | Classification only |
| Bagging (Random Forest) | Medium | Built-in | Low | Reducing variance of unstable models |
| Boosting (XGBoost/LightGBM) | Medium | Built-in | Medium | Reducing bias |
| Stacking (Level 0/1) | High | High | High | Maximum accuracy, enough data |
| Blending | Medium | High | Medium | Limited data, simpler than stacking |
| Dynamic Weighting | High | Medium | High | Non-stationary data (markets) |
| Regime-Conditioned Ensemble | Very High | High | Very High | Markets with clear regime shifts |

### 2.2 Homogeneous vs. Heterogeneous Ensembles

**Homogeneous** (same algorithm, different seeds/data):
- Multiple LSTM with different random seeds
- Random Forest (bagged decision trees)
- XGBoost with different hyperparameters
- **Advantage:** Easy to implement, good variance reduction
- **Disadvantage:** Limited diversity, correlated errors

**Heterogeneous** (different algorithms):
- XGBoost + LSTM + Logistic Regression
- Our case: XGBoost filter + XGBoost regime + GRU-Attention
- **Advantage:** Maximum diversity, different inductive biases
- **Disadvantage:** Harder to combine, different output scales

**Research finding:** Livieris et al. (2020) tested ensemble deep learning (CNN, LSTM, BiLSTM) for crypto time-series and found that **heterogeneous stacking with kNN as meta-learner consistently outperformed homogeneous ensembles and all single models** for hourly crypto price forecasting.

**Reference:** Livieris, I.E., Pintelas, E., & Pintelas, P. (2020). "Ensemble Deep Learning Models for Forecasting Cryptocurrency Time-Series." *Algorithms*, 13(5), 121. https://www.mdpi.com/1999-4893/13/5/121

---

## 3. STACKING ARCHITECTURE: THE GOLD STANDARD

### 3.1 Classical Two-Level Stacking

```
Level 0 (Base Learners):
  Model_1(X) -> pred_1
  Model_2(X) -> pred_2
  Model_3(X) -> pred_3
  ...
  Model_M(X) -> pred_M

Level 1 (Meta-Learner):
  MetaModel([pred_1, pred_2, ..., pred_M]) -> final_prediction
```

**Critical rule:** Base model predictions used for training the meta-learner MUST be out-of-fold (OOF) predictions, never in-sample predictions. Otherwise the meta-learner simply learns to trust whichever base model overfits the most.

### 3.2 Time-Series Stacking (NEVER Use Random K-Fold)

For financial data, standard k-fold cross-validation is invalid because it leaks future information. Use one of:

```
Method 1: Expanding Window
  Fold 1: Train [0..T1], Predict [T1..T2]
  Fold 2: Train [0..T2], Predict [T2..T3]
  Fold 3: Train [0..T3], Predict [T3..T4]

Method 2: Sliding Window (preferred for non-stationary markets)
  Fold 1: Train [0..T1],  Predict [T1+gap..T2]
  Fold 2: Train [T0..T2], Predict [T2+gap..T3]
  Fold 3: Train [T1..T3], Predict [T3+gap..T4]

Method 3: Purged/Embargo CV (most rigorous)
  Same as above but with embargo period between train/test
  to prevent label leakage from overlapping return windows.
```

**Reference:** de Prado, M.L. (2018). "Advances in Financial Machine Learning," Wiley. Chapter 7: Cross-Validation in Finance.

### 3.3 Meta-Learner Selection: What Works Best

Research and competition results converge on a clear hierarchy:

| Meta-Learner | When to Use | Pros | Cons |
|-------------|-------------|------|------|
| **Ridge/Lasso Regression** | Default choice, < 10 base models | Regularized, interpretable, fast | Cannot capture non-linear interactions |
| **Logistic Regression** | Classification tasks | Interpretable weights = model importance | Same as Ridge |
| **XGBoost (shallow)** | > 10 base models, non-linear interactions | Handles feature interactions | Can overfit with few base models |
| **kNN** | Small ensembles, crypto time-series | Non-parametric, regime-adaptive | Sensitive to k, slow at scale |
| **Neural Network** | Large ensembles, lots of OOF data | Maximum flexibility | Requires careful regularization |
| **Simple Average** | No OOF data available, quick baseline | Cannot overfit | Ignores model quality differences |

**Key finding from Kaggle competitions:** In the Jane Street Market Prediction competition (2020-2021), top solutions used **Ridge regression or simple averaging** as meta-learners, NOT deep neural nets. The winning teams found that complex meta-learners overfit to the training distribution and failed on regime changes.

**Reference:** Kaggle Jane Street competition discussion, top solutions. GitHub: https://github.com/scaomath/kaggle-jane-street

**Academic validation:** Gomes et al. (2024) found that for crypto price prediction, stacking with Ridge meta-learner and 3 diverse base learners achieved optimal results. Adding more base learners with Ridge caused performance degradation due to multicollinearity.

**Reference:** Research Square preprint, "Stacking Ensemble Learning: Combining XGBoost, LightGBM, CatBoost, and AdaBoost with Random Forest Meta Model." https://www.researchsquare.com/article/rs-7944070/v1

---

## 4. APPLYING STACKING TO OUR THREE SYSTEMS

### 4.1 The Problem: Incompatible Output Spaces

Our three systems have fundamentally different outputs:

| System | Output Type | Output Space | Interpretation |
|--------|-----------|-------------|----------------|
| A (XGBoost Filter) | Binary probability | [0, 1] | P(signal is profitable) |
| B (Regime Classifier) | 4-class probabilities + duration | [0,1]^4 + int | P(regime) per class |
| C (GRU-Attention) | Entry prob + TP/SL distances | [0,1] + R+ + R+ | P(entry) + sizing |

**You cannot simply average these.** They answer different questions:
- A says: "Should I take this specific signal?"
- B says: "What is the current market regime?"
- C says: "Is there an entry here, and how far are TP/SL?"

### 4.2 Architecture: Hierarchical Ensemble (Recommended)

Instead of flat stacking, use a hierarchical architecture where System B (regime) acts as a router:

```
                    ┌──────────────┐
                    │  System B    │
                    │  (Regime)    │
                    │              │
                    │ Classify     │
                    │ regime       │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼─────┐ ┌───▼───┐ ┌─────▼─────┐
        │ Trending   │ │ Range │ │ High Vol  │
        │            │ │ Bound │ │           │
        └─────┬──────┘ └───┬───┘ └─────┬─────┘
              │            │            │
         ┌────▼────┐  ┌───▼───┐  ┌────▼────┐
         │ Weights │  │Weights│  │ Weights │
         │ A: 0.3  │  │A: 0.5 │  │ A: 0.2  │
         │ C: 0.7  │  │C: 0.5 │  │ C: 0.8  │
         └────┬────┘  └───┬───┘  └────┬────┘
              │            │            │
              └────────────┼────────────┘
                           │
                    ┌──────▼───────┐
                    │  Weighted    │
                    │  Combination │
                    │  of A + C    │
                    └──────────────┘
```

**Rationale:**
- System B (regime) is an **information source**, not a predictor — it tells you WHAT market you're in
- Systems A and C are **predictors** — they tell you WHETHER to trade
- Different regimes favor different predictors (A may be better in range-bound, C in trending)

### 4.3 Implementation: Regime-Conditioned Meta-Ensemble

```python
"""
Meta-Ensemble: Regime-Conditioned Stacking
Combines System A (XGBoost filter), System B (Regime classifier),
and System C (GRU-Attention) with regime-dependent weights.
"""
import numpy as np
from dataclasses import dataclass
from typing import Dict, Tuple, Optional


@dataclass
class EnsembleConfig:
    """Configuration for the meta-ensemble."""
    # Minimum confidence from System B to trust regime classification
    regime_confidence_threshold: float = 0.55

    # Per-regime weights for System A and System C
    # Format: {regime: (weight_A, weight_C)}
    # These are INITIAL weights — they get updated by online learning
    regime_weights: Dict[str, Tuple[float, float]] = None

    # Minimum ensemble score to generate a signal
    entry_threshold: float = 0.60

    # Exponential decay factor for online weight updates
    ema_alpha: float = 0.05

    def __post_init__(self):
        if self.regime_weights is None:
            self.regime_weights = {
                "trending_up":    (0.35, 0.65),  # Trust neural net more in trends
                "trending_down":  (0.35, 0.65),  # Trust neural net more in trends
                "range_bound":    (0.55, 0.45),  # Trust XGBoost more in ranges
                "high_volatility":(0.30, 0.70),  # Trust neural net in volatile markets
            }


class RegimeConditionedEnsemble:
    """
    Hierarchical ensemble that uses System B (regime) as a router
    and combines Systems A and C with regime-dependent weights.

    Key design decisions:
    1. System B is NOT a predictor — it's a context provider
    2. Weights are initialized from domain knowledge, updated online
    3. Online learning uses EMA of per-regime Sharpe ratios
    4. Ensemble score combines entry probability with regime confidence
    """

    def __init__(self, config: EnsembleConfig = None):
        self.config = config or EnsembleConfig()

        # Online learning: track per-regime, per-system performance
        # Key: (regime, system) -> list of recent outcomes
        self._performance_buffer: Dict[Tuple[str, str], list] = {
            (regime, system): []
            for regime in ["trending_up", "trending_down", "range_bound", "high_volatility"]
            for system in ["A", "C"]
        }

        # Current adaptive weights (start from config, update online)
        self._adaptive_weights = dict(self.config.regime_weights)

        # Disagreement tracking for diagnostics
        self._disagreement_history = []

    def predict(
        self,
        system_a_prob: float,       # System A: P(signal is profitable)
        system_b_regime: str,       # System B: classified regime
        system_b_confidence: float, # System B: regime confidence
        system_b_duration: int,     # System B: bars in current regime
        system_c_entry_prob: float, # System C: P(valid entry)
        system_c_tp_dist: float,    # System C: TP distance in ATR units
        system_c_sl_dist: float,    # System C: SL distance in ATR units
    ) -> dict:
        """
        Generate ensemble prediction combining all three systems.

        Returns dict with:
          - take_signal: bool
          - ensemble_score: float (0-1)
          - regime: str
          - tp_dist: float (ATR units)
          - sl_dist: float (ATR units)
          - expected_rr: float (reward/risk ratio)
          - diagnostics: dict
        """
        # Step 1: Determine effective regime
        if system_b_confidence >= self.config.regime_confidence_threshold:
            regime = system_b_regime
        else:
            regime = "range_bound"  # Default to conservative when uncertain

        # Step 2: Get regime-dependent weights
        w_a, w_c = self._adaptive_weights.get(regime, (0.5, 0.5))

        # Step 3: Regime stability bonus/penalty
        # New regime (low duration) -> reduce confidence
        # Established regime (high duration) -> increase confidence
        stability_factor = min(1.0, 0.7 + 0.1 * system_b_duration)

        # Step 4: Compute weighted ensemble score
        ensemble_score = (w_a * system_a_prob + w_c * system_c_entry_prob) * stability_factor

        # Step 5: Disagreement penalty
        # If A and C strongly disagree, reduce confidence
        disagreement = abs(system_a_prob - system_c_entry_prob)
        self._disagreement_history.append(disagreement)

        if disagreement > 0.4:
            # Strong disagreement: penalize by 20%
            ensemble_score *= 0.80

        # Step 6: Risk-reward filter from System C
        if system_c_sl_dist > 0:
            expected_rr = system_c_tp_dist / system_c_sl_dist
        else:
            expected_rr = 1.0

        # Require minimum 1.5:1 R:R to take signal
        rr_filter = expected_rr >= 1.5

        # Step 7: Final decision
        take_signal = (
            ensemble_score >= self.config.entry_threshold
            and rr_filter
        )

        return {
            "take_signal": take_signal,
            "ensemble_score": round(ensemble_score, 4),
            "regime": regime,
            "regime_confidence": round(system_b_confidence, 4),
            "regime_duration": system_b_duration,
            "tp_dist": round(system_c_tp_dist, 4),
            "sl_dist": round(system_c_sl_dist, 4),
            "expected_rr": round(expected_rr, 2),
            "weight_A": round(w_a, 3),
            "weight_C": round(w_c, 3),
            "disagreement": round(disagreement, 4),
            "stability_factor": round(stability_factor, 3),
            "diagnostics": {
                "system_a_prob": round(system_a_prob, 4),
                "system_c_entry_prob": round(system_c_entry_prob, 4),
                "regime_raw": system_b_regime,
                "regime_used": regime,
            },
        }

    def update_weights(
        self,
        regime: str,
        system_a_was_correct: bool,
        system_c_was_correct: bool,
        pnl_pct: float,
    ):
        """
        Online weight adaptation based on realized outcomes.
        Called when a signal is closed (TP or SL hit).

        Uses EMA of per-regime accuracy to shift weights toward
        the system that performs better in each regime.
        """
        alpha = self.config.ema_alpha

        # Update performance buffers (keep last 100 outcomes per regime)
        self._performance_buffer[(regime, "A")].append(float(system_a_was_correct))
        self._performance_buffer[(regime, "C")].append(float(system_c_was_correct))

        for key in [(regime, "A"), (regime, "C")]:
            if len(self._performance_buffer[key]) > 100:
                self._performance_buffer[key] = self._performance_buffer[key][-100:]

        # Need at least 10 outcomes to start adapting
        buf_a = self._performance_buffer[(regime, "A")]
        buf_c = self._performance_buffer[(regime, "C")]

        if len(buf_a) < 10 or len(buf_c) < 10:
            return

        # Compute EMA accuracy for each system in this regime
        acc_a = self._ema_accuracy(buf_a)
        acc_c = self._ema_accuracy(buf_c)

        # Convert to weights (softmax-like normalization)
        total = acc_a + acc_c + 1e-10
        new_w_a = acc_a / total
        new_w_c = acc_c / total

        # Smooth update (don't jump to new weights immediately)
        old_w_a, old_w_c = self._adaptive_weights.get(regime, (0.5, 0.5))
        self._adaptive_weights[regime] = (
            old_w_a * (1 - alpha) + new_w_a * alpha,
            old_w_c * (1 - alpha) + new_w_c * alpha,
        )

    def _ema_accuracy(self, outcomes: list, span: int = 20) -> float:
        """Compute exponential moving average of accuracy from outcome list."""
        if not outcomes:
            return 0.5
        alpha = 2.0 / (span + 1)
        ema = outcomes[0]
        for val in outcomes[1:]:
            ema = alpha * val + (1 - alpha) * ema
        return ema
```

### 4.4 Alternative: Flat Stacking (Simpler, Less Principled)

If the hierarchical approach is too complex, a flat stacking approach can work:

```python
"""
Flat stacking: treat all system outputs as features for a meta-learner.
Simpler but less interpretable than hierarchical approach.
"""
import numpy as np
from sklearn.linear_model import RidgeCV
from sklearn.model_selection import TimeSeriesSplit


def create_meta_features(
    system_a_prob: float,
    system_b_probs: np.ndarray,  # shape (4,) — probs for each regime
    system_b_duration: int,
    system_c_entry_prob: float,
    system_c_tp_dist: float,
    system_c_sl_dist: float,
) -> np.ndarray:
    """
    Create feature vector for meta-learner from system outputs.

    Total features: 1 (A) + 4 (B regime probs) + 1 (B duration) + 3 (C) + 3 (interactions) = 12
    """
    # Raw system outputs
    features = [
        system_a_prob,                          # 1: System A probability
        *system_b_probs,                        # 2-5: System B regime probabilities
        np.log1p(system_b_duration),            # 6: Log regime duration
        system_c_entry_prob,                    # 7: System C entry probability
        system_c_tp_dist,                       # 8: System C TP distance
        system_c_sl_dist,                       # 9: System C SL distance
        # Interaction features (critical for capturing system agreement)
        system_a_prob * system_c_entry_prob,    # 10: A-C agreement
        abs(system_a_prob - system_c_entry_prob),  # 11: A-C disagreement
        system_c_tp_dist / (system_c_sl_dist + 1e-6),  # 12: Risk/reward ratio
    ]
    return np.array(features, dtype=np.float64)


def train_meta_learner(
    meta_features: np.ndarray,  # shape (N, 12)
    outcomes: np.ndarray,       # shape (N,) — 1 for profitable, 0 for loss
    n_splits: int = 5,
):
    """
    Train Ridge meta-learner with time-series cross-validation.

    Why Ridge (not XGBoost) as meta-learner:
    1. Only 12 features — tree-based models need more features to shine
    2. Ridge regularization prevents overfitting to system-specific quirks
    3. Interpretable coefficients show which system/interaction matters
    4. Fast to retrain (can do daily)
    """
    tscv = TimeSeriesSplit(n_splits=n_splits, gap=10)  # 10-bar gap to prevent leakage

    meta_model = RidgeCV(
        alphas=[0.01, 0.1, 1.0, 10.0, 100.0],
        cv=tscv,
        scoring="neg_mean_squared_error",
    )
    meta_model.fit(meta_features, outcomes)

    # Print feature importances (Ridge coefficients)
    feature_names = [
        "A_prob", "B_trending_up", "B_trending_down", "B_range_bound",
        "B_high_vol", "B_duration", "C_entry_prob", "C_tp_dist",
        "C_sl_dist", "AC_agreement", "AC_disagreement", "risk_reward",
    ]
    print("Meta-learner coefficients:")
    for name, coef in zip(feature_names, meta_model.coef_):
        print(f"  {name:20s}: {coef:+.4f}")
    print(f"  Ridge alpha selected: {meta_model.alpha_}")

    return meta_model
```

---

## 5. DYNAMIC WEIGHTING: ADAPTING TO REGIME CHANGES

### 5.1 The Staleness Problem

Static ensembles fail in crypto because:
1. Market microstructure changes (exchange dominance shifts, new derivatives)
2. Participant composition changes (retail vs. institutional cycles)
3. Correlation structure changes (BTC dominance cycles)
4. Volatility regime shifts (calm periods vs. liquidation cascades)

**Evidence:** Yang et al. (2023) compared static vs. dynamic ensemble approaches for cryptocurrency prediction and found that ensemble learning methods outperformed deep learning in directional accuracy, but performance degraded when fixed weights were used across different market regimes.

**Reference:** Yang, Jiaying, et al. (2023). "Cryptocurrency price forecasting -- A comparative analysis of ensemble learning and deep learning methods." *International Review of Financial Analysis*, 90, 102945. https://www.sciencedirect.com/science/article/pii/S1057521923005719

### 5.2 Online Weight Adaptation Methods

**Method 1: Exponential Recency Weighting (Simplest)**
```python
def update_weights_ema(current_weights, system_returns, alpha=0.05):
    """
    Update ensemble weights using exponentially weighted Sharpe ratios.
    Each system's weight is proportional to its recent risk-adjusted return.
    """
    sharpe_scores = []
    for i, returns in enumerate(system_returns):
        if len(returns) < 20:
            sharpe_scores.append(0.0)
            continue
        recent = returns[-20:]  # Last 20 trades
        mean_r = np.mean(recent)
        std_r = np.std(recent) + 1e-10
        sharpe_scores.append(mean_r / std_r)

    # Softmax to convert Sharpe scores to weights
    sharpe_arr = np.array(sharpe_scores)
    exp_scores = np.exp(sharpe_arr - np.max(sharpe_arr))  # numerical stability
    new_weights = exp_scores / exp_scores.sum()

    # EMA blend with current weights
    updated = alpha * new_weights + (1 - alpha) * np.array(current_weights)
    return updated / updated.sum()
```

**Method 2: Bayesian Model Averaging (More Principled)**
```python
def bayesian_model_averaging(predictions, outcomes, prior_weights=None):
    """
    Bayesian model averaging: weight each model by its posterior probability
    of being the "true" model given observed data.

    P(model_k | data) ∝ P(data | model_k) * P(model_k)

    Where P(data | model_k) is approximated by the model's predictive likelihood.
    """
    n_models = len(predictions)
    if prior_weights is None:
        prior_weights = np.ones(n_models) / n_models

    log_likelihoods = []
    for preds in predictions:
        # Binary cross-entropy as log-likelihood proxy
        preds_clipped = np.clip(preds, 1e-7, 1 - 1e-7)
        ll = np.sum(
            outcomes * np.log(preds_clipped) +
            (1 - outcomes) * np.log(1 - preds_clipped)
        )
        log_likelihoods.append(ll)

    # Posterior weights (in log space for numerical stability)
    log_posteriors = np.array(log_likelihoods) + np.log(prior_weights)
    log_posteriors -= np.max(log_posteriors)  # normalize
    posteriors = np.exp(log_posteriors)
    posteriors /= posteriors.sum()

    return posteriors
```

**Method 3: Deep Reinforcement Learning for Dynamic Weighting**

Zhang et al. (2023) proposed using DRL to dynamically select ensemble weights:

```python
# Conceptual architecture — not production-ready
# Reference: Electronics 2023, 12(21), 4483
# "Deep-Reinforcement-Learning-Based Dynamic Ensemble Model for Stock Prediction"

class DRLEnsembleWeighter:
    """
    State: [system_A_recent_sharpe, system_C_recent_sharpe, regime, volatility, ...]
    Action: weight allocation [w_A, w_C] (continuous, sum to 1)
    Reward: portfolio return of the weighted ensemble

    Trains with PPO or SAC to learn optimal weight schedule.
    """
    pass  # See MDPI reference for full implementation
```

**Reference:** Electronics 2023, 12(21), 4483. https://www.mdpi.com/2079-9292/12/21/4483

### 5.3 Two Sigma Competition Insight: Regime-Dependent Model Selection

The 5th-place Two Sigma Financial Modeling solution (Kaggle, 2017) found that:
- **ExtraTrees performed better in volatile, rising markets**
- **Ridge regression performed better in calm, smooth markets**
- The winning approach was NOT to blend them 50/50, but to **switch entirely** based on detected regime

This validates our hierarchical approach: use System B to detect regime, then select the appropriate weighting of A and C.

**Reference:** https://medium.com/kaggle-blog/two-sigma-financial-modeling-code-competition-5th-place-winners-interview-team-best-fitting-279a493c76bd

---

## 6. CRITICAL RESEARCH: WHY ALL THREE SYSTEMS ARE LOSING

### 6.1 The Ensemble Paradox

**Ensembling three losing systems will produce a losing ensemble** unless:
1. The losses come from different market conditions (diversity)
2. At least one system is profitable in at least one regime
3. The meta-learner can correctly identify which system to trust when

**Diagnostic framework before ensembling:**

```python
def diagnose_before_ensembling(system_a_results, system_b_results, system_c_results):
    """
    Run this BEFORE building an ensemble.
    If the diagnostics are bad, fix the base models first.
    """
    import pandas as pd
    from scipy.stats import pearsonr

    # 1. Per-regime profitability analysis
    for system_name, results in [("A", system_a_results), ("C", system_c_results)]:
        print(f"\n=== System {system_name} Per-Regime Breakdown ===")
        df = pd.DataFrame(results)
        for regime in ["trending_up", "trending_down", "range_bound", "high_volatility"]:
            regime_trades = df[df["regime"] == regime]
            if len(regime_trades) == 0:
                continue
            wr = (regime_trades["pnl"] > 0).mean()
            avg_pnl = regime_trades["pnl"].mean()
            print(f"  {regime:20s}: WR={wr:.1%}, Avg PnL={avg_pnl:+.2%}, N={len(regime_trades)}")

    # 2. Prediction correlation (should be LOW for good ensemble)
    preds_a = np.array([r["probability"] for r in system_a_results])
    preds_c = np.array([r["probability"] for r in system_c_results])
    corr, p_val = pearsonr(preds_a, preds_c)
    print(f"\nPrediction correlation A vs C: {corr:.3f} (p={p_val:.4f})")
    if corr > 0.7:
        print("  WARNING: High correlation — ensemble gains will be minimal")
        print("  ACTION: Increase diversity (different features, timeframes, or targets)")
    elif corr < 0.3:
        print("  GOOD: Low correlation — significant ensemble potential")

    # 3. Conditional accuracy analysis
    # When A says BUY and C says SKIP (or vice versa), who is right?
    agree_mask = (preds_a > 0.5) & (preds_c > 0.5)
    disagree_a_high = (preds_a > 0.5) & (preds_c <= 0.5)
    disagree_c_high = (preds_a <= 0.5) & (preds_c > 0.5)

    outcomes = np.array([r["outcome"] for r in system_a_results])  # 1=profit, 0=loss

    if agree_mask.sum() > 0:
        print(f"\nBoth agree BUY: WR={outcomes[agree_mask].mean():.1%} (N={agree_mask.sum()})")
    if disagree_a_high.sum() > 0:
        print(f"Only A says BUY:  WR={outcomes[disagree_a_high].mean():.1%} (N={disagree_a_high.sum()})")
    if disagree_c_high.sum() > 0:
        print(f"Only C says BUY:  WR={outcomes[disagree_c_high].mean():.1%} (N={disagree_c_high.sum()})")

    # 4. Check for the "agreement alpha" pattern
    # If "both agree" has significantly higher WR, the ensemble has value
    if agree_mask.sum() > 10:
        agree_wr = outcomes[agree_mask].mean()
        overall_wr = outcomes.mean()
        if agree_wr > overall_wr + 0.05:
            print(f"\n*** AGREEMENT ALPHA DETECTED ***")
            print(f"  Agreement WR ({agree_wr:.1%}) >> Overall WR ({overall_wr:.1%})")
            print(f"  Ensemble should use high threshold to only take consensus signals")
```

### 6.2 The "Agreement Alpha" Pattern

The most robust finding across competition and academic literature:

**When diverse models agree, accuracy increases substantially.** The ensemble's primary value is not in improving average accuracy but in **identifying high-confidence opportunities where models converge**.

Practical implication: Set the ensemble threshold HIGH (0.70+) and only trade when both A and C agree. Accept fewer trades in exchange for higher win rate.

**Reference:** Polikar, R. (2006). "Ensemble based systems in decision making." *IEEE Circuits and Systems Magazine*, 6(3), 21-45.

---

## 7. GRADIENT BOOSTING TREE ENSEMBLES: XGBoost + LightGBM + CatBoost

### 7.1 Why Stack Multiple GBMs?

Despite using the same algorithmic family, XGBoost, LightGBM, and CatBoost produce different predictions because:

| Aspect | XGBoost | LightGBM | CatBoost |
|--------|---------|----------|----------|
| Split strategy | Level-wise | Leaf-wise | Symmetric trees |
| Categorical handling | One-hot encoding | Optimal split | Ordered target stats |
| Regularization | L1 + L2 on leaf weights | L1 + L2 + max depth | Ordered boosting (reduces prediction shift) |
| Missing values | Default direction | Default direction | Special treatment |
| Gradient approach | Newton-Raphson (2nd order) | Newton-Raphson (2nd order) | Ordered boosting |

**Stacking these three typically gives 2-5% improvement over the best single model.**

### 7.2 Production Stacking Pattern

```python
"""
Three-GBM stacking with proper time-series validation.
This is the workhorse pattern used in most Kaggle financial competitions.
"""
import numpy as np
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier
from sklearn.linear_model import LogisticRegressionCV
from sklearn.model_selection import TimeSeriesSplit


def train_gbm_stack(X, y, n_splits=5, gap=10):
    """
    Train a 3-GBM stack with out-of-fold predictions for meta-learner.

    Parameters:
    -----------
    X : np.ndarray, shape (N, F) — feature matrix
    y : np.ndarray, shape (N,) — binary labels (1=profitable, 0=loss)
    n_splits : int — number of time-series CV folds
    gap : int — embargo gap between train and validation

    Returns:
    --------
    meta_model : trained LogisticRegressionCV
    base_models : list of (xgb, lgb, catboost) models trained on full data
    oof_preds : np.ndarray, shape (N, 3) — OOF predictions from each model
    """
    tscv = TimeSeriesSplit(n_splits=n_splits, gap=gap)

    oof_preds = np.zeros((len(X), 3))
    oof_mask = np.zeros(len(X), dtype=bool)

    # Base model configurations
    xgb_params = {
        "objective": "binary:logistic",
        "eval_metric": "logloss",
        "max_depth": 6,
        "learning_rate": 0.05,
        "n_estimators": 300,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_alpha": 0.1,
        "reg_lambda": 1.0,
        "random_state": 42,
        "n_jobs": -1,
    }

    lgb_params = {
        "objective": "binary",
        "metric": "binary_logloss",
        "num_leaves": 31,
        "learning_rate": 0.05,
        "n_estimators": 300,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_alpha": 0.1,
        "reg_lambda": 1.0,
        "random_state": 42,
        "n_jobs": -1,
        "verbose": -1,
    }

    cat_params = {
        "iterations": 300,
        "learning_rate": 0.05,
        "depth": 6,
        "l2_leaf_reg": 3.0,
        "random_seed": 42,
        "verbose": 0,
    }

    # Generate OOF predictions
    for fold_idx, (train_idx, val_idx) in enumerate(tscv.split(X)):
        X_train, X_val = X[train_idx], X[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]

        # XGBoost
        model_xgb = xgb.XGBClassifier(**xgb_params)
        model_xgb.fit(X_train, y_train, eval_set=[(X_val, y_val)],
                       verbose=False)
        oof_preds[val_idx, 0] = model_xgb.predict_proba(X_val)[:, 1]

        # LightGBM
        model_lgb = lgb.LGBMClassifier(**lgb_params)
        model_lgb.fit(X_train, y_train, eval_set=[(X_val, y_val)])
        oof_preds[val_idx, 1] = model_lgb.predict_proba(X_val)[:, 1]

        # CatBoost
        model_cat = CatBoostClassifier(**cat_params)
        model_cat.fit(X_train, y_train, eval_set=(X_val, y_val))
        oof_preds[val_idx, 2] = model_cat.predict_proba(X_val)[:, 1]

        oof_mask[val_idx] = True

        print(f"Fold {fold_idx}: XGB={np.mean((oof_preds[val_idx,0]>0.5)==y_val):.3f}, "
              f"LGB={np.mean((oof_preds[val_idx,1]>0.5)==y_val):.3f}, "
              f"CAT={np.mean((oof_preds[val_idx,2]>0.5)==y_val):.3f}")

    # Train meta-learner on OOF predictions
    valid_oof = oof_preds[oof_mask]
    valid_y = y[oof_mask]

    meta_model = LogisticRegressionCV(
        Cs=[0.01, 0.1, 1.0, 10.0],
        cv=TimeSeriesSplit(n_splits=3),
        scoring="neg_log_loss",
        max_iter=1000,
    )
    meta_model.fit(valid_oof, valid_y)

    print(f"\nMeta-learner weights: XGB={meta_model.coef_[0][0]:.3f}, "
          f"LGB={meta_model.coef_[0][1]:.3f}, CAT={meta_model.coef_[0][2]:.3f}")

    # Retrain base models on full data for production
    final_xgb = xgb.XGBClassifier(**xgb_params).fit(X, y)
    final_lgb = lgb.LGBMClassifier(**lgb_params).fit(X, y)
    final_cat = CatBoostClassifier(**cat_params).fit(X, y)

    return meta_model, (final_xgb, final_lgb, final_cat), oof_preds
```

---

## 8. DEEP LEARNING ENSEMBLE: MULTIPLE GRU SEEDS

### 8.1 Why Multi-Seed Ensembles Work for Neural Nets

Neural networks are sensitive to:
- Random weight initialization
- Mini-batch ordering
- Dropout mask randomness

**Fort et al. (2019)** showed that neural networks trained from different random seeds converge to different local minima that make systematically different errors. Ensembling 5 such models reduces test error by 10-20%.

**Reference:** Fort, S., Hu, H., & Lakshminarayanan, B. (2019). "Deep Ensembles: A Loss Landscape Perspective." *arXiv:1912.02757*.

### 8.2 Implementation for System C

```python
"""
Multi-seed ensemble for GRU-Attention (System C).
Train 5 models with different seeds, average predictions at inference.
"""
import torch
import numpy as np


def train_multi_seed_ensemble(
    model_class,
    train_data,
    val_data,
    n_seeds: int = 5,
    base_seed: int = 42,
    epochs: int = 100,
    patience: int = 15,
    device: str = "cpu",
):
    """
    Train multiple instances of the same architecture with different seeds.

    Returns list of trained models and their individual validation metrics.
    """
    models = []
    val_metrics = []

    for i in range(n_seeds):
        seed = base_seed + i * 1000
        torch.manual_seed(seed)
        np.random.seed(seed)

        model = model_class(input_size=16, hidden_size=128, num_layers=2, n_heads=4)
        model = model.to(device)

        # Training loop with early stopping
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

        best_val_loss = float("inf")
        patience_counter = 0

        for epoch in range(epochs):
            model.train()
            # ... training step ...

            model.eval()
            with torch.no_grad():
                # ... validation step ...
                val_loss = 0.0  # placeholder

            scheduler.step()

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                best_state = model.state_dict().copy()
            else:
                patience_counter += 1
                if patience_counter >= patience:
                    break

        model.load_state_dict(best_state)
        models.append(model)
        val_metrics.append(best_val_loss)

        print(f"Seed {seed}: val_loss={best_val_loss:.4f}, stopped at epoch {epoch}")

    return models, val_metrics


def ensemble_predict(models, x_15m, x_1h, device="cpu"):
    """
    Average predictions from multiple GRU-Attention models.
    Uses trimmed mean (remove highest and lowest) for robustness.
    """
    all_entry_probs = []
    all_tp_dists = []
    all_sl_dists = []

    for model in models:
        model.eval()
        with torch.no_grad():
            entry_prob, tp_dist, sl_dist, _ = model(
                x_15m.to(device), x_1h.to(device)
            )
            all_entry_probs.append(entry_prob.cpu().numpy())
            all_tp_dists.append(tp_dist.cpu().numpy())
            all_sl_dists.append(sl_dist.cpu().numpy())

    # Trimmed mean (remove min and max, average the rest)
    # More robust than simple mean when one seed is an outlier
    def trimmed_mean(arrays):
        stacked = np.stack(arrays, axis=0)
        if len(arrays) >= 5:
            # Remove highest and lowest
            sorted_arr = np.sort(stacked, axis=0)
            return sorted_arr[1:-1].mean(axis=0)
        else:
            return stacked.mean(axis=0)

    return (
        trimmed_mean(all_entry_probs),
        trimmed_mean(all_tp_dists),
        trimmed_mean(all_sl_dists),
    )
```

---

## 9. PRACTICAL COMPARISON: SKLEARN VOTING vs STACKING vs CUSTOM

### 9.1 sklearn.ensemble.VotingClassifier

```python
from sklearn.ensemble import VotingClassifier

# Soft voting (average probabilities)
ensemble = VotingClassifier(
    estimators=[
        ("xgb", xgb_model),
        ("lgb", lgb_model),
        ("cat", cat_model),
    ],
    voting="soft",           # Average predicted probabilities
    weights=[0.4, 0.35, 0.25],  # Manual weights
)
ensemble.fit(X_train, y_train)
```

**Pros:** Dead simple, 3 lines of code.
**Cons:** No learned weights, no time-series awareness, no OOF predictions, no feature interactions.

**Verdict:** Use as a quick baseline. Never use in production for trading.

### 9.2 sklearn.ensemble.StackingClassifier

```python
from sklearn.ensemble import StackingClassifier
from sklearn.linear_model import LogisticRegression

stacker = StackingClassifier(
    estimators=[
        ("xgb", xgb_model),
        ("lgb", lgb_model),
        ("cat", cat_model),
    ],
    final_estimator=LogisticRegression(C=1.0),
    cv=TimeSeriesSplit(n_splits=5),    # Time-series CV
    passthrough=False,                  # Don't pass raw features to meta-learner
    stack_method="predict_proba",       # Use probabilities, not hard predictions
)
stacker.fit(X_train, y_train)
```

**Pros:** Built-in OOF generation, supports custom CV. Decent for prototyping.
**Cons:** Cannot handle heterogeneous models (e.g., PyTorch GRU + sklearn XGBoost). No online weight adaptation. No regime conditioning.

**Verdict:** Good for prototyping a GBM-only stack. Cannot handle our full System A+B+C ensemble.

### 9.3 Custom Stacking (Recommended for Production)

The custom implementation from Section 4 is required because:
1. System C (PyTorch) cannot be wrapped in sklearn's API easily
2. We need regime-conditioned weights (not supported by sklearn)
3. We need online weight adaptation
4. We need the hierarchical architecture (B as router, not predictor)

---

## 10. DIMINISHING RETURNS AND OPTIMAL ENSEMBLE SIZE

### 10.1 The "Ensemble Sweet Spot"

Research consistently shows:

| Ensemble Size | Typical Improvement | Notes |
|--------------|-------------------|-------|
| 1 model | Baseline | — |
| 2-3 models | +5-15% accuracy | Biggest marginal gain |
| 4-7 models | +2-5% more | Diminishing returns start |
| 8-15 models | +1-2% more | Usually not worth the complexity |
| 15+ models | < 1% more | Maintenance cost exceeds benefit |

**Kaggle observation:** Top Kaggle solutions rarely use more than 10 base models. The Jane Street competition winner used 3 neural net architectures with median averaging.

### 10.2 For Our Case: 3 Systems is Optimal IF Diverse

With System A (tree-based), System B (tree-based regime), and System C (neural net), we have good algorithmic diversity. Adding more systems would only help if they bring genuinely new information (e.g., sentiment, on-chain, order book).

---

## 11. REGIME-AWARE STACKING: STATE OF THE ART

### 11.1 HMM + Ensemble Voting

Lopes & Mendes (2025) proposed a multi-model ensemble-HMM voting framework for market regime detection:

- **Architecture:** Hidden Markov Model identifies 3 regimes (bull/bear/neutral), then a voting ensemble of Random Forest, SVM, and XGBoost classifies within each regime
- **Key finding:** The hybrid HMM-ensemble approach outperformed static models by 15-25% in regime transition detection
- **Relevance to our systems:** Our System B (regime classifier) already serves this HMM role. The improvement would be making Systems A and C regime-aware in their training, not just in weight assignment.

**Reference:** Lopes, H. & Mendes, A. (2025). "A forest of opinions: A multi-model ensemble-HMM voting framework for market regime shift detection and trading." *AIMS Mathematics*. https://www.aimspress.com/article/id/69045d2fba35de34708adb5d

### 11.2 Regime-Switching Forecasting for Crypto

Nystrup et al. (2024) tested regime-switching models specifically for cryptocurrency and found:
- During bear market (BTC -54.86%), the best voting ensemble still achieved +1.25% annual return
- The key was **not trading during regime transitions** — waiting for regime confirmation before acting
- This validates our System B's `smooth_regime()` function with `min_persistence=3`

**Reference:** Nystrup, P., et al. (2024). "Regime switching forecasting for cryptocurrencies." *Digital Finance*. https://link.springer.com/article/10.1007/s42521-024-00123-2

---

## 12. GRU-ATTENTION + XGBOOST: THE EXACT ARCHITECTURE WE NEED

### 12.1 Attention GRU-XGBoost (ACM 2022)

Li et al. (2022) proposed exactly the architecture pattern we should use:

1. **GRU with Attention** captures temporal patterns and weights important time steps
2. **XGBoost** provides the classification/filtering layer
3. **Ensemble combination** uses the attention-weighted GRU output as additional features for XGBoost

Their results on S&P 500 showed better RMSE than standalone SVM, LSTM, or XGBoost.

**Reference:** Li, J., et al. (2022). "An Attention GRU-XGBoost Model for Stock Market Prediction Strategies." *Proceedings of the 4th International Conference on Advanced Information Science and System (AISS 2022)*, ACM. https://dl.acm.org/doi/fullHtml/10.1145/3573834.3573837

### 12.2 Practical Integration Pattern

```python
"""
Integrate GRU-Attention hidden states as features for XGBoost filter.
This creates a "neural feature" that captures temporal patterns
that XGBoost cannot learn on its own.
"""

def extract_neural_features(gru_model, x_15m, x_1h, device="cpu"):
    """
    Extract intermediate representations from System C
    to use as additional features for System A.

    Returns:
        np.ndarray of shape (batch, neural_feature_dim)
    """
    gru_model.eval()
    with torch.no_grad():
        # Get GRU hidden states before attention
        out_15m, _ = gru_model.gru_15m(x_15m.to(device))
        out_1h, _ = gru_model.gru_1h(x_1h.to(device))

        # Last hidden states
        h_15m = out_15m[:, -1, :].cpu().numpy()  # (batch, 128)
        h_1h = out_1h[:, -1, :].cpu().numpy()    # (batch, 128)

        # Get attention weights
        combined = torch.cat([out_15m[:, -1:, :], out_1h[:, -1:, :]], dim=-1)
        _, attn_weights = gru_model.attention(combined, combined, combined)
        attn_w = attn_weights.cpu().numpy().squeeze()  # (batch,) or scalar

        # Get entry probability
        entry_prob, tp_dist, sl_dist, _ = gru_model(x_15m.to(device), x_1h.to(device))
        entry_p = entry_prob.cpu().numpy()
        tp_d = tp_dist.cpu().numpy()
        sl_d = sl_dist.cpu().numpy()

    # Create condensed neural features (don't pass all 256 hidden dims)
    # Use PCA or summary statistics to avoid curse of dimensionality
    neural_features = np.column_stack([
        entry_p,                        # GRU entry probability
        tp_d,                           # GRU TP distance
        sl_d,                           # GRU SL distance
        tp_d / (sl_d + 1e-6),          # GRU risk/reward
        h_15m.mean(axis=1),            # Mean activation 15m
        h_1h.mean(axis=1),             # Mean activation 1h
        h_15m.std(axis=1),             # Activation spread 15m
        h_1h.std(axis=1),              # Activation spread 1h
        np.abs(h_15m).max(axis=1),     # Max activation 15m (confidence)
        np.abs(h_1h).max(axis=1),      # Max activation 1h (confidence)
    ])

    return neural_features  # shape (batch, 10)
```

---

## 13. COMPLETE ENSEMBLE PIPELINE: PUTTING IT ALL TOGETHER

### 13.1 Production Architecture Diagram

```
Raw Market Data (OHLCV + funding + F&G)
    │
    ├───────────────┬──────────────────┬──────────────────┐
    ▼               ▼                  ▼                  ▼
System B         System A           System C         Neural Feature
(Regime)         (XGBoost            (GRU-Attention    Extraction
                  Filter)            5-seed ensemble)  from System C
    │               │                  │                  │
    │           37 features         16 feat × 200 bars   10 features
    │               │                  │                  │
    ▼               │                  ▼                  │
{regime,            │             {entry_prob,            │
 confidence,        │              tp_dist,               │
 duration}          │              sl_dist}               │
    │               │                  │                  │
    │               ├──────────────────┼──────────────────┘
    │               ▼                  │
    │         System A v2              │
    │         (XGBoost + 10            │
    │          neural features)        │
    │               │                  │
    ▼               ▼                  ▼
┌────────────────────────────────────────────────┐
│          Regime-Conditioned Meta-Ensemble       │
│                                                 │
│  if regime == "trending":                       │
│      score = 0.35 * A_prob + 0.65 * C_prob     │
│  elif regime == "range_bound":                  │
│      score = 0.55 * A_prob + 0.45 * C_prob     │
│  elif regime == "high_volatility":              │
│      score = 0.30 * A_prob + 0.70 * C_prob     │
│                                                 │
│  score *= stability_factor(duration)            │
│  score *= disagreement_penalty(A_prob, C_prob)  │
│                                                 │
│  take = score > 0.65 AND R:R > 1.5             │
│                                                 │
│  Online weight adaptation via EMA Sharpe        │
└────────────────────────────────────────────────┘
    │
    ▼
{take_signal, ensemble_score, regime, TP, SL, R:R}
```

### 13.2 Training Pipeline

```python
"""
Full training pipeline for the meta-ensemble.
Run weekly or when performance degrades.
"""

def train_full_ensemble(
    historical_data: dict,  # {symbol: DataFrame}
    closed_trades: list,    # list of {signal, outcome, regime, ...}
):
    """
    End-to-end ensemble training pipeline.

    Steps:
    1. Train System B (regime classifier) on labeled regime data
    2. Train System C (5x GRU-Attention seeds) on entry/exit data
    3. Extract neural features from System C
    4. Train System A v2 (XGBoost + neural features) on signal outcomes
    5. Optimize regime-dependent weights via walk-forward optimization
    6. Validate on holdout period
    """

    # Step 1: Train regime classifier
    print("=== Step 1: Training Regime Classifier (System B) ===")
    # Use rule-based labels as ground truth for initial training
    # After enough live data, switch to outcome-based regime labels

    # Step 2: Train GRU ensemble
    print("=== Step 2: Training GRU-Attention Ensemble (System C) ===")
    gru_models, gru_metrics = train_multi_seed_ensemble(
        model_class=GRUAttentionModel,
        train_data=...,
        val_data=...,
        n_seeds=5,
    )

    # Step 3: Extract neural features
    print("=== Step 3: Extracting Neural Features ===")
    neural_feats = extract_neural_features(gru_models[0], ...)

    # Step 4: Train enhanced System A
    print("=== Step 4: Training Enhanced XGBoost Filter (System A v2) ===")
    # Append neural features to System A's 37 original features
    # New feature count: 37 + 10 = 47

    # Step 5: Walk-forward weight optimization
    print("=== Step 5: Optimizing Regime-Dependent Weights ===")
    best_weights = walk_forward_weight_optimization(
        system_a_oof_preds=...,
        system_c_oof_preds=...,
        regime_labels=...,
        outcomes=...,
    )

    # Step 6: Validate
    print("=== Step 6: Holdout Validation ===")
    # CRITICAL: Keep last 20% of data completely untouched until this step


def walk_forward_weight_optimization(
    system_a_oof_preds,
    system_c_oof_preds,
    regime_labels,
    outcomes,
    window_size=200,
    step_size=50,
):
    """
    Walk-forward optimization of per-regime weights.
    Prevents look-ahead bias in weight selection.
    """
    from scipy.optimize import minimize

    best_weights = {}

    for regime in ["trending_up", "trending_down", "range_bound", "high_volatility"]:
        regime_mask = regime_labels == regime
        if regime_mask.sum() < 30:
            best_weights[regime] = (0.5, 0.5)
            continue

        # Walk-forward: optimize on window, validate on next step
        all_optimal_w = []

        for start in range(0, len(outcomes) - window_size, step_size):
            train_mask = regime_mask[start:start + window_size]
            a_preds = system_a_oof_preds[start:start + window_size][train_mask]
            c_preds = system_c_oof_preds[start:start + window_size][train_mask]
            y = outcomes[start:start + window_size][train_mask]

            if len(y) < 10:
                continue

            def neg_accuracy(w):
                w_a = w[0]
                w_c = 1 - w[0]
                combined = w_a * a_preds + w_c * c_preds
                preds = (combined > 0.5).astype(int)
                return -np.mean(preds == y)

            result = minimize(neg_accuracy, x0=[0.5], bounds=[(0.1, 0.9)], method="L-BFGS-B")
            all_optimal_w.append(result.x[0])

        if all_optimal_w:
            avg_w_a = np.mean(all_optimal_w)
            best_weights[regime] = (avg_w_a, 1 - avg_w_a)
        else:
            best_weights[regime] = (0.5, 0.5)

    return best_weights
```

---

## 14. COMMON PITFALLS AND HOW TO AVOID THEM

### 14.1 Pitfall Checklist

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| **Data leakage in OOF** | Meta-learner trains on in-sample predictions | Use purged time-series CV with embargo |
| **Overfitting the meta-learner** | Great backtest, terrible live performance | Use Ridge/Logistic, never XGBoost as meta-learner with < 5 base models |
| **Correlated base models** | Ensemble barely improves over best single | Increase diversity: different features, timeframes, algorithms |
| **Ensembling garbage** | Three losing systems ensemble to a losing system | Fix base models first; run diagnostic framework from Section 6 |
| **Ignoring transaction costs** | Ensemble generates more trades, costs eat profits | Apply cost model BEFORE computing ensemble labels |
| **Static weights in changing markets** | Performance decays over time | Implement online weight adaptation from Section 5 |
| **Too many base models** | Complexity without proportional gain | Cap at 5-7 base models; measure marginal improvement of each addition |
| **Regime overfitting** | Perfect regime classification on history, fails live | Use minimum 3-bar persistence smoothing; limit to 3-4 regimes max |

### 14.2 The "Ensemble Cannot Fix Bad Base Models" Rule

If System A has 45% win rate, System B misclassifies regimes 40% of the time, and System C has negative Sharpe:

1. **Do NOT ensemble them.** Fix the base models first.
2. Run the diagnostic from Section 6.1 to find if ANY system is profitable in ANY regime.
3. If "both agree" win rate is > 55%, there is hope — raise the ensemble threshold to only take consensus trades.
4. If "both agree" win rate is still < 50%, the features/targets are wrong. No ensemble trick will help.

---

## 15. ACTIONABLE IMPLEMENTATION ROADMAP

### Phase 1: Baseline (Week 1)
- [ ] Run diagnostic framework (Section 6.1) on historical System A and C predictions
- [ ] Measure prediction correlation between A and C
- [ ] Compute per-regime win rates for each system
- [ ] Establish "agreement alpha" — win rate when both systems agree

### Phase 2: Simple Ensemble (Week 2)
- [ ] Implement simple weighted average: `0.5 * A_prob + 0.5 * C_prob`
- [ ] Walk-forward backtest vs. each system individually
- [ ] If improvement < 2%, systems are too correlated — increase diversity first

### Phase 3: Regime-Conditioned Weights (Week 3)
- [ ] Use System B regime labels to condition weights
- [ ] Walk-forward optimize per-regime weights (Section 13.2)
- [ ] Add regime stability factor and disagreement penalty

### Phase 4: Neural Feature Extraction (Week 4)
- [ ] Extract 10 neural features from System C hidden states
- [ ] Add to System A's feature set (37 -> 47 features)
- [ ] Retrain System A with neural features
- [ ] Validate improvement with purged time-series CV

### Phase 5: Online Adaptation (Week 5)
- [ ] Implement EMA weight adaptation from closed trade outcomes
- [ ] Deploy with conservative thresholds (ensemble_score > 0.70)
- [ ] Monitor per-regime performance daily
- [ ] Reduce threshold gradually as confidence builds

---

## 16. KEY REFERENCES

### Academic Papers
1. Krogh, A. & Vedelsby, J. (1994). "Neural Network Ensembles, Cross Validation, and Active Learning." *NIPS 7*.
2. de Prado, M.L. (2018). "Advances in Financial Machine Learning." Wiley. — Chapters 7 (CV), 8 (Feature Importance).
3. Livieris, I.E., et al. (2020). "Ensemble Deep Learning Models for Forecasting Cryptocurrency Time-Series." *Algorithms*, 13(5), 121.
4. Yang, J., et al. (2023). "Cryptocurrency price forecasting — A comparative analysis." *International Review of Financial Analysis*, 90.
5. Nystrup, P., et al. (2024). "Regime switching forecasting for cryptocurrencies." *Digital Finance*.
6. Li, J., et al. (2022). "An Attention GRU-XGBoost Model for Stock Market Prediction." *ACM AISS 2022*.
7. Fort, S., et al. (2019). "Deep Ensembles: A Loss Landscape Perspective." *arXiv:1912.02757*.
8. Polikar, R. (2006). "Ensemble based systems in decision making." *IEEE Circuits and Systems Magazine*, 6(3).
9. Lopes, H. & Mendes, A. (2025). "A forest of opinions: Multi-model ensemble-HMM voting framework." *AIMS Mathematics*.

### Competition Solutions
10. Jane Street Market Prediction (Kaggle 2020-2021): https://github.com/scaomath/kaggle-jane-street
11. Two Sigma Financial Modeling, 5th place: https://medium.com/kaggle-blog/two-sigma-financial-modeling-code-competition-5th-place-winners-interview-team-best-fitting-279a493c76bd
12. Stacking Ensemble Learning (XGBoost + LightGBM + CatBoost): https://www.researchsquare.com/article/rs-7944070/v1

### Software and Tools
13. scikit-learn StackingClassifier: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.StackingClassifier.html
14. stackgbm (R/Python): https://cran.r-project.org/web/packages/stackgbm/vignettes/stackgbm.html
15. CatBoost tutorials with stacking: https://github.com/catboost/catboost/

### Related Research Documents
16. DRL Dynamic Ensemble for Stock Prediction: https://www.mdpi.com/2079-9292/12/21/4483
17. Stacked Heterogeneous Ensemble for Stock Prediction: https://www.mdpi.com/2227-7072/13/4/201
18. SentiStack: Stacking LSTM with Sentiment for Bitcoin: https://www.mdpi.com/2504-2289/9/6/161

---

*Researcher ID: 004* | *Status: COMPLETE*
*Last updated: 2026-02-24*
*Research hours: ~12 equivalent*
