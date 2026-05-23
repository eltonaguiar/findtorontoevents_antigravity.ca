# Adaptive Scoring System — Auto-Detecting Proven Winners

## Problem Statement

The current scoring system (elite_scorer → quality_gates → smart_score) uses **static weights** calibrated from point-in-time correlation analysis. When market conditions shift, what worked for crypto in a bull run stops working in a bear regime, but the weights don't adjust. The score thresholds and component weights are the same regardless of whether the pick is BTCUSDT in a trending regime or a forex pair in a choppy range.

**Current PF: 0.97 (losing money).** Score >60 band: 61% WR, 213% PnL. Score <30 band: ~19-35% WR. The scoring system *does* discriminate, but static weights leave significant alpha on the table.

## Design: Bayesian Adaptive Weight Optimizer (BAWO)

### Core Idea

Replace static component weights with **per-cohort adaptive weights** that are continuously updated using a sliding-window Bayesian approach. A "cohort" is defined as a (asset_class, regime, symbol_tier) tuple, so crypto-altcoins in a bearish regime have different optimal weights than forex-majors in a trending regime.

### Architecture

```
                    ┌──────────────────────────┐
                    │   Closed Pick Stream      │
                    │ (resolved trades w/ PnL)  │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │   Cohort Router           │
                    │ (asset_class × regime ×   │
                    │  symbol_tier)             │
                    └────────────┬─────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                   │
    ┌─────────▼────────┐ ┌──────▼───────┐ ┌────────▼────────┐
    │ Crypto-Bear-Alt  │ │ Forex-Trend  │ │ Equity-Bull-LC  │
    │ Weight Optimizer │ │ Wt Optimizer │ │ Weight Optimizer │
    │ (Thompson/Bayes) │ │              │ │                  │
    └─────────┬────────┘ └──────┬───────┘ └────────┬────────┘
              │                  │                   │
              └──────────────────┼──────────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │   Weight Registry         │
                    │ adaptive_weights.json     │
                    │ (one row per cohort)      │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │   Score Computation       │
                    │ (elite_scorer uses        │
                    │  cohort-specific weights) │
                    └──────────────────────────┘
```

### Cohort Definition

```python
COHORT_DIMENSIONS = {
    "asset_class": ["CRYPTO", "FOREX", "EQUITY", "COMMODITY", "ETF", "FUTURES", "BOND"],
    "regime":      ["BULL", "BEAR", "CHOPPY", "TRENDING", "UNKNOWN"],
    "symbol_tier": ["MAJOR", "MID", "SMALL", "MEME"]  # crypto-specific; others → "DEFAULT"
}
```

Not all combinations will have enough data. Cohorts with <30 closed trades fall back to their parent (e.g., `CRYPTO-BEAR-MEME` → `CRYPTO-BEAR-DEFAULT` → `CRYPTO-DEFAULT-DEFAULT` → `GLOBAL`).

### Scorable Components (What Gets Weighted)

These are the existing score factors from `elite_scorer.py` and `quality_gates.py`:

| Component | Current Max Pts | Description |
|-----------|----------------|-------------|
| `forward_wr` | 40 | Forward test win rate of source strategy |
| `ml_score` | 25 (halved from 50) | ML win probability from ml_ranker |
| `confidence` | 15 | Source system confidence (sweet spot 0.7-0.8) |
| `regime_match` | 10 | Regime alignment with direction |
| `technical_alignment` | 10 | RSI/MACD multi-timeframe agreement |
| `forward_pnl` | 10 | Forward test cumulative PnL |
| `market_cap_tier` | 5 | Crypto market cap tier bonus |
| `risk_reward` | 15 (smart_score) | R:R quality (2.0-3.0 optimal) |
| `trust_score` | 12 (smart_score) | Composite trust (freshness, edge, etc.) |
| `consensus` | 8 (smart_score) | Multi-source agreement |

### Adaptive Weight Update Algorithm

Use **Thompson Sampling with Bayesian Linear Regression** — this naturally handles exploration/exploitation and works with continuous rewards (PnL).

```python
class CohortWeightOptimizer:
    """
    Per-cohort Bayesian weight optimizer.
    
    For each cohort, maintains a posterior distribution over weight vectors.
    On each new resolved trade, updates the posterior using the trade's 
    component scores as features and PnL as the target.
    
    The "best" weights are sampled from the posterior (Thompson Sampling)
    to maintain exploration while converging on what works.
    """
    
    def __init__(self, n_components=10, prior_precision=1.0, noise_precision=1.0):
        # Bayesian linear regression parameters
        self.n = n_components
        self.prior_precision = prior_precision  # λ — regularization toward uniform
        self.noise_precision = noise_precision  # β — observation noise
        
        # Posterior: N(μ, Σ) over weight vector w
        self.Sigma = np.eye(n_components) / prior_precision  # prior covariance
        self.mu = np.ones(n_components) / n_components       # prior mean (uniform)
        self.sample_count = 0
    
    def update(self, component_scores: np.ndarray, realized_pnl: float):
        """
        Update posterior after observing a resolved trade.
        
        component_scores: [forward_wr_norm, ml_score_norm, ..., consensus_norm]
                          each in [0, 1]
        realized_pnl: the trade's PnL% (capped at ±500%)
        """
        x = component_scores.reshape(-1, 1)  # column vector
        
        # Bayesian update: Σ_new = (Σ^-1 + β * x @ x^T)^-1
        Sigma_inv = np.linalg.inv(self.Sigma) + self.noise_precision * (x @ x.T)
        self.Sigma = np.linalg.inv(Sigma_inv)
        
        # μ_new = Σ_new @ (Σ^-1_old @ μ_old + β * x * y)
        self.mu = self.Sigma @ (
            np.linalg.inv(self.Sigma) @ self.mu.reshape(-1, 1) 
            + self.noise_precision * x * realized_pnl
        ).flatten()
        
        self.sample_count += 1
    
    def sample_weights(self) -> np.ndarray:
        """
        Thompson Sampling: draw weights from current posterior.
        Softmax to ensure non-negative and sum-to-1.
        """
        if self.sample_count < 30:
            return np.ones(self.n) / self.n  # cold start: uniform
        
        raw = np.random.multivariate_normal(self.mu, self.Sigma)
        # Softmax to get valid weight distribution
        exp_w = np.exp(raw - raw.max())
        return exp_w / exp_w.sum()
    
    def best_weights(self) -> np.ndarray:
        """MAP estimate (posterior mean), softmax-normalized."""
        if self.sample_count < 30:
            return np.ones(self.n) / self.n
        exp_w = np.exp(self.mu - self.mu.max())
        return exp_w / exp_w.sum()
```

### Sliding Window with Exponential Decay

Instead of treating all historical trades equally, apply exponential time decay so recent performance is weighted more heavily:

```python
HALF_LIFE_DAYS = 30  # A trade from 30 days ago has half the weight of today's trade

def time_weight(trade_date: datetime, now: datetime) -> float:
    """Exponential decay weight for a trade based on recency."""
    age_days = (now - trade_date).total_seconds() / 86400
    return 2 ** (-age_days / HALF_LIFE_DAYS)
```

The Bayesian update loop becomes:

```python
for trade in sorted_by_date(closed_trades_in_cohort):
    w = time_weight(trade.closed_at, now)
    optimizer.update(
        component_scores=extract_components(trade),
        realized_pnl=trade.pnl_pct * w  # decay-weighted PnL
    )
```

### Per-Symbol Learning (Fine-Grained)

For high-frequency symbols (>50 closed trades), maintain a **symbol-specific weight delta** on top of the cohort weights:

```python
class SymbolWeightDelta:
    """
    Learns a small additive correction to cohort weights for a specific symbol.
    
    Uses online ridge regression with aggressive regularization (λ=10)
    to prevent overfitting on small samples. Only activates when 
    sample_count >= 50.
    """
    ACTIVATION_THRESHOLD = 50
    REGULARIZATION = 10.0  # strong pull toward zero delta
    MAX_DELTA = 0.15       # cap per-component adjustment at ±15%
```

The final score for a pick becomes:

```
score = Σ (cohort_weight_i + symbol_delta_i) × component_score_i × 100
```

### Integration with Existing Code

#### 1. Weight Registry File

```json
// alpha_engine/data/adaptive_weights.json
{
  "version": 2,
  "updated_at": "2026-04-13T03:00:00Z",
  "cohorts": {
    "CRYPTO-BEAR-MAJOR": {
      "weights": [0.18, 0.12, 0.08, 0.22, 0.15, 0.05, 0.02, 0.08, 0.05, 0.05],
      "sample_count": 847,
      "posterior_mean": [...],
      "posterior_cov_diag": [...],
      "last_30d_wr": 0.54,
      "last_30d_pf": 1.32
    },
    "FOREX-TRENDING-DEFAULT": {
      "weights": [0.25, 0.05, 0.20, 0.15, 0.10, 0.05, 0.00, 0.10, 0.05, 0.05],
      "sample_count": 213,
      ...
    }
  },
  "symbol_deltas": {
    "BTCUSDT": {"delta": [0.02, -0.01, ...], "n": 156},
    "ETHUSDT": {"delta": [0.01, 0.03, ...], "n": 134}
  },
  "global_fallback": {
    "weights": [0.15, 0.10, 0.10, 0.10, 0.10, 0.10, 0.05, 0.10, 0.10, 0.10]
  }
}
```

#### 2. Modify `elite_scorer.py`

Replace the static point allocations with adaptive weights:

```python
# In compute_elite_score(), replace:
#   fwr_pts = min(40, int(fwr * 40))
#   ml_pts  = min(25, int(ml * 25))
#   ...
# With:

from alpha_engine.adaptive_weights import get_cohort_weights

def compute_elite_score(pick, ...):
    cohort_key = _build_cohort_key(pick)  # e.g. "CRYPTO-BEAR-MAJOR"
    weights = get_cohort_weights(cohort_key, pick.get("symbol"))
    
    # Normalize each component to [0, 1]
    components = {
        "forward_wr":          min(1.0, fwr),
        "ml_score":            ml,
        "confidence":          _conf_curve(conf),  # 0.7-0.8 → 1.0
        "regime_match":        1.0 if regime_aligned else 0.0,
        "technical_alignment": tech_align_score,
        "forward_pnl":         min(1.0, max(0, fw_pnl / 50)),
        "market_cap_tier":     mkt_cap_norm,
        "risk_reward":         _rr_curve(rr),       # 2.0-3.0 → 1.0
        "trust_score":         trust / 10.0,
        "consensus":           min(1.0, n_sources / 5),
    }
    
    # Weighted sum using adaptive weights
    raw = sum(weights[k] * components[k] for k in components)
    score = round(raw * 100, 1)  # scale to 0-100
    
    # Keep backward compatibility
    pick["elite_score"] = score
    pick["_adaptive_weights_used"] = cohort_key
    pick["_component_scores"] = components
    return {"elite_score": score, ...}
```

#### 3. Weight Update Pipeline (GitHub Actions)

Add a step to the existing `audit-dashboard.yml` workflow:

```yaml
- name: Update adaptive weights
  run: |
    python -m alpha_engine.adaptive_weight_updater \
      --closed-picks audit_trail/data/dashboard_payload.json \
      --output alpha_engine/data/adaptive_weights.json \
      --half-life 30 \
      --min-cohort-size 30
  continue-on-error: true
```

This runs after dashboard generation (which resolves all picks) and before the next scoring cycle.

#### 4. Dashboard Visualization

Add a "Weight Explorer" tab to `template.html` showing:

- **Heatmap**: component weights by cohort (rows = cohorts, columns = components)
- **Time series**: how weights have shifted over the last 90 days per cohort
- **Performance attribution**: "If we had used adaptive weights 90 days ago, PF would be X vs actual Y"
- **Anomaly flags**: cohorts where weights have drifted >2σ from global baseline

### Safeguards Against Overfitting

1. **Minimum sample threshold**: 30 trades per cohort before adaptive weights activate; below that, use parent cohort or global fallback.

2. **Regularization toward uniform**: The Bayesian prior pulls weights toward equal (uninformative). Strong evidence is needed to move weights far from uniform.

3. **Weight change rate limit**: Maximum 5% shift per component per update cycle. Prevents catastrophic weight flips from a small batch of outlier trades.

4. **Holdout validation**: Every 7 days, run a walk-forward backtest comparing adaptive vs static weights on the last 30 days of data. If adaptive underperforms by >3 PF points, revert to static for that cohort (with alert).

5. **Cross-validation on update**: Each weight update uses purged k-fold CV (k=5) with 3-day embargo to estimate out-of-sample PF before committing new weights.

6. **Symbol delta cap**: Per-symbol adjustments are hard-capped at ±15% of cohort weight per component.

### Expected Impact

Based on current data analysis:

| Scenario | Est. WR | Est. PF | Rationale |
|----------|---------|---------|-----------|
| Current (static) | 42.1% | 0.97 | Point-in-time calibration, one-size-fits-all |
| Score >50 filter only | 54.2% | ~1.3 | Simple threshold, already works |
| Adaptive weights (conservative) | 52-56% | 1.2-1.5 | Per-cohort optimal weights + symbol fine-tuning |
| Adaptive + score floor + C-tier disable | 58-62% | 1.5-2.0 | Combined with low-hanging-fruit fixes |

### Implementation Phases

**Phase 1: Data Collection & Offline Validation (low risk)**
- Extract component scores for all 3430 closed trades
- Run offline cohort analysis to validate the approach
- Produce walk-forward backtest comparing adaptive vs static
- New files: `alpha_engine/adaptive_weights.py`, `tools/adaptive_weight_backtest.py`
- No changes to live scoring

**Phase 2: Shadow Mode (zero risk to live)**
- Compute adaptive scores alongside current scores
- Add `_adaptive_score` field to payload (not used for filtering/sorting)
- Dashboard shows adaptive vs actual in a comparison panel
- Monitor for 2-4 weeks

**Phase 3: Gradual Rollout**
- Blend: `final_score = 0.7 * static + 0.3 * adaptive` (configurable)
- Monitor PF and WR on the blended score
- Increase adaptive weight if PF improves

**Phase 4: Full Adaptive**
- Switch to `1.0 * adaptive` when validation confirms improvement
- Keep static as emergency fallback
- Automate weekly holdout validation

### Quick Wins (Can Ship Immediately)

While building the full adaptive system, these changes to the existing code would improve PF right now:

1. **Fix the `validation_metrics.js` transaction cost bug** (`{ cost }` → `{ total: cost }`): makes net-PnL calculations accurate.

2. **Fix permutation win/loss zero-PnL inconsistency**: use `_outcome_bucket_from_pnl()` in `collect_cross_strategy_permutations` instead of raw `pnl > 0`.

3. **Add configurable score floor**: In `quality_gates.py`, add a `SMART_PICKS_GLOBAL_MIN_SCORE = 50` that gates all picks. The data shows score >50 has 54.2% WR vs 43.3% unfiltered — this alone would flip PF above 1.0.

4. **Disable C-Tier crypto**: PF 0.77, -113.51% PnL. Either hard-block the source systems or auto-quarantine any system with PF <0.8 over last 100 trades.

5. **Add asset-class PF circuit breaker**: If any asset class drops below PF 0.5 over 50 trades (like Futures at 0.13), auto-disable picks from that class and alert.

### File Inventory (New)

| File | Purpose |
|------|---------|
| `alpha_engine/adaptive_weights.py` | CohortWeightOptimizer, SymbolWeightDelta, registry I/O |
| `alpha_engine/adaptive_weight_updater.py` | CLI entrypoint for GH Actions: load closed picks, update all cohorts |
| `alpha_engine/data/adaptive_weights.json` | Weight registry (committed, updated by CI) |
| `tools/adaptive_weight_backtest.py` | Offline walk-forward validation of adaptive vs static |
| `docs/ADAPTIVE_SCORING_SYSTEM.md` | This document |

### File Inventory (Modified)

| File | Change |
|------|--------|
| `alpha_engine/elite_scorer.py` | `compute_elite_score` reads adaptive weights when available |
| `audit_trail/quality_gates.py` | Add global min score floor; asset-class PF circuit breaker |
| `audit_dashboard/validation_metrics.js` | Fix `{ cost }` → `{ total: cost }` bug |
| `audit_trail/dashboard_generator.py` | Fix permutation zero-PnL logic; add `_adaptive_score` to payload |
| `.github/workflows/audit-dashboard.yml` | Add adaptive weight update step |
