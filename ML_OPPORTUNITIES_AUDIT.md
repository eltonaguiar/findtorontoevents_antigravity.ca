# Machine Learning Opportunities Audit

**Date:** March 2, 2026  
**Auditor:** KIMI Code  
**Purpose:** Identify systems without ML that could benefit, and dormant ML systems

---

## Executive Summary

| Category | Count | Status |
|----------|-------|--------|
| **Active ML Systems** | 7 | Running daily/weekly |
| **Dormant ML Systems** | 3 | Need attention |
| **Non-ML Systems (opportunities)** | 12 | Could benefit from ML |
| **Total Trading Systems** | 22 | - |

---

## Active ML Systems (Performing Well)

### 1. Crypto ML Predictor (ml_crypto_predictor/)
- **Workflow:** `train_crypto_models.yml` (Daily at midnight UTC)
- **Status:** Active, v3.1 with XGB ensemble + calibration
- **Performance:** Walk-forward validated on 41 pairs
- **Last Update:** Recently active (in recent commits)
- **Assessment:** Healthy

### 2. Mercury 2 (mercury2/)
- **Workflow:** `mercury2-retrain.yml` (Weekly, Sundays 2AM UTC)
- **Status:** Active, weekly retraining
- **Features:** XGBoost + LightGBM ensemble
- **Assessment:** Healthy

### 3. Enhanced ML Crypto (enhanced-ml-crypto.yml)
- **Status:** Active workflow
- **Features:** Advanced ML with regime detection
- **Assessment:** Healthy

### 4. Claude Gainer ML (claude-gainer-ml-live.yml)
- **Status:** Active
- **Features:** Live ML-based gainer predictions
- **Assessment:** Healthy

### 5. Crypto ML Edge (crypto-ml-edge.yml)
- **Status:** Active
- **Features:** Edge detection with ML
- **Assessment:** Healthy

### 6. ML Battleground Ensemble (ml-battleground-ensemble.yml)
- **Status:** Active
- **Features:** Multi-model ensemble for battleground
- **Assessment:** Healthy

### 7. ML Hourly Picks (ml_hourly_picks.yml)
- **Status:** Active
- **Features:** Hourly ML-generated signals
- **Assessment:** Healthy

---

## Dormant/Potentially Stalled ML Systems

### 1. Alpha Engine ML Ranker
- **Location:** `alpha_engine/strategies/ml_ranker.py` (31 ML references)
- **Status:** Code exists but workflow may be outdated
- **Issue:** Uses older ML approach, may need modernization
- **Recommendation:** 
  - Integrate with new forward testing system
  - Add ROC-AUC validation (Fix #3 pattern)
  - Connect to adaptive TP/SL (Fix #1)

### 2. Baby Strategies ML Ensemble
- **Location:** `baby_strategies/ml_ensemble_strategy.py` (32 ML references)
- **Status:** Code exists in baby_strategies folder
- **Issue:** Unclear if actively used in SUPERPOWERS ARENA
- **Recommendation:**
  - Verify integration with battleground dashboard
  - Add to forward testing database
  - Enable ML-based strategy graduation

### 3. HMM Regime Detector (Alpha Engine)
- **Location:** `alpha_engine/scripts/hmm_regime_detector.py`
- **Status:** Code exists, may be underutilized
- **Issue:** Regime detection not integrated across all systems
- **Recommendation:**
  - Connect to new regime-specific genomes
  - Use for all signal generation
  - Feed into circuit breaker system

---

## Non-ML Systems (High ML Opportunity)

### HIGH PRIORITY - Would Benefit Most from ML

#### 1. Signal Aggregator (signal_aggregator/)
- **Current:** Rule-based Bayesian voting
- **ML Opportunity:** 
  - Learn optimal weight combinations from forward test results
  - Neural network for signal consensus
  - Meta-learning across systems
- **Impact:** HIGH - Core system used by all signals
- **Implementation:** Add `signal_aggregator/ml_consensus.py`

#### 2. DNA Genome Evolution (genome/dna_engine.py)
- **Current:** Genetic algorithm with fixed fitness function
- **ML Opportunity:**
  - Reinforcement learning for strategy evolution
  - Learn from forward test performance
  - Predict which chromosome combinations work best
- **Impact:** HIGH - Could accelerate strategy discovery
- **Implementation:** Add RL component to `dna_engine_enhanced.py`

#### 3. Risk Management (risk_management/)
- **Current:** Kelly Criterion + static circuit breakers
- **ML Opportunity:**
  - ML-based risk prediction
  - Dynamic position sizing based on market conditions
  - Predict correlation breakdowns
- **Impact:** HIGH - Could reduce drawdowns significantly
- **Implementation:** Add `risk_management/ml_risk_predictor.py`

#### 4. Forward Testing Analytics (forward_testing/)
- **Current:** SQLite tracking, basic stats
- **ML Opportunity:**
  - Predict which signals will resolve successfully
  - ML-based signal quality scoring
  - Early warning system for bad signals
- **Impact:** MEDIUM-HIGH - Could filter bad signals before execution
- **Implementation:** Add `forward_testing/signal_quality_ml.py`

### MEDIUM PRIORITY - Would Benefit from ML

#### 5. Portfolio Tracker (portfolio_tracker/)
- **Current:** Basic P&L tracking
- **ML Opportunity:**
  - Predict portfolio risk
  - ML-based rebalancing recommendations
  - Detect abnormal patterns
- **Impact:** MEDIUM
- **Implementation:** Add `portfolio_tracker/ml_analytics.py`

#### 6. Battleground Strategy Scoring (battleground/)
- **Current:** Fixed metrics (Sharpe, win rate, etc.)
- **ML Opportunity:**
  - Learn which metrics predict forward success
  - ML-based strategy ranking
  - Predict strategy decay
- **Impact:** MEDIUM
- **Implementation:** Add to battleground quality filter

#### 7. Data Pipeline (data_fetcher_enhanced.py)
- **Current:** Retry logic with failover
- **ML Opportunity:**
  - Predict API failures before they happen
  - Optimize data source selection
  - Detect data quality issues
- **Impact:** MEDIUM
- **Implementation:** Add anomaly detection to data fetching

#### 8. Predictions Dashboard (predictions/)
- **Current:** Rule-based tier system
- **ML Opportunity:**
  - ML-based analyst ranking
  - Predict prediction accuracy
  - Detect fake/anomalous predictions
- **Impact:** MEDIUM
- **Implementation:** Add ML tier system alongside rule-based

### LOWER PRIORITY - Nice to Have ML

#### 9. Social Trader Database (social_trader_database.py)
- **ML Opportunity:** Sentiment analysis, trader ranking
- **Impact:** LOW-MEDIUM

#### 10. On-Chain Metrics (onchain_metrics_agent.py)
- **ML Opportunity:** Pattern detection in blockchain data
- **Impact:** LOW-MEDIUM

#### 11. L2 Orderbook Analysis (l2_orderbook_agent.py)
- **ML Opportunity:** Microstructure prediction
- **Impact:** LOW (specialized use case)

#### 12. Funding Arbitrage (funding_arb_analysis.py)
- **ML Opportunity:** Predict funding rate changes
- **Impact:** LOW (specialized use case)

---

## Recommended ML Implementation Priority

### Phase 1 (Immediate - Next 2 Weeks)

1. **Signal Aggregator ML Consensus**
   - **Why:** Core system, affects all signals
   - **Approach:** Train model on forward test results to predict signal success
   - **Data:** Use forward_testing.db outcomes as labels
   - **Expected Impact:** +5-10% win rate improvement

2. **Forward Test Quality Predictor**
   - **Why:** Can filter bad signals immediately
   - **Approach:** Binary classifier for signal quality
   - **Data:** Historical signals + outcomes
   - **Expected Impact:** Reduce bad trades by 20%

### Phase 2 (Short Term - Next Month)

3. **Risk Management ML**
   - **Why:** Protect capital during drawdowns
   - **Approach:** Predict volatility spikes, correlation breakdowns
   - **Data:** Market data + portfolio state
   - **Expected Impact:** Reduce max drawdown by 5%

4. **DNA Genome RL Enhancement**
   - **Why:** Accelerate strategy discovery
   - **Approach:** Reinforcement learning for evolution
   - **Data:** Strategy performance history
   - **Expected Impact:** 2x faster strategy optimization

### Phase 3 (Medium Term - Next Quarter)

5. **Portfolio ML Analytics**
6. **Battleground ML Scoring**
7. **Data Pipeline Anomaly Detection**

---

## ML Architecture Recommendations

### Shared ML Infrastructure

Create a shared ML module that all systems can use:

```
ml_core/
├── __init__.py
├── base_model.py          # Base class for all ML models
├── feature_store.py       # Shared feature storage
├── model_registry.py      # Track all trained models
├── training_pipeline.py   # Standardized training
├── evaluation.py          # Model evaluation utilities
└── inference.py           # Fast inference engine
```

### Model Standards

All new ML models should:
1. Use train/test split (Fix #3 pattern)
2. Report ROC-AUC, not just accuracy
3. Include probability calibration
4. Have automated retraining workflows
5. Log predictions for forward validation
6. Include SHAP/feature importance

---

## Dormant System Reactivation Plan

### Alpha Engine ML Ranker

```bash
# Steps to reactivate:
1. Update to use ml_core/base_model.py
2. Add train/test split validation
3. Connect to forward_testing.db for labels
4. Create/Update GitHub Actions workflow
5. Integrate with signal_aggregator
```

### Baby Strategies ML Ensemble

```bash
# Steps to integrate:
1. Verify ML ensemble in baby_strategies/
2. Connect to battleground dashboard
3. Add to forward tracking database
4. Enable ML-based graduation criteria
```

---

## Success Metrics

After implementing ML opportunities:

| Metric | Target | Measurement |
|--------|--------|-------------|
| Signal Aggregator Accuracy | >75% consensus accuracy | Forward test results |
| Quality Predictor Precision | >70% precision | Predicted vs actual |
| Risk Predictor Recall | >80% for major drawdowns | Backtest + forward |
| DNA Evolution Speed | 2x faster convergence | Generations to target |

---

## Conclusion

**Key Findings:**
- 7 ML systems are active and healthy
- 3 ML systems are dormant but can be reactivated
- 12 non-ML systems could benefit from ML
- Signal Aggregator and Risk Management are highest priority

**Immediate Action:**
Implement Signal Aggregator ML Consensus using existing forward test data. This alone could improve win rates by 5-10%.

**Resources Needed:**
- 1-2 weeks for Phase 1 implementations
- GPU optional (XGBoost/ LightGBM work well on CPU)
- Existing forward_testing.db provides labeled data
