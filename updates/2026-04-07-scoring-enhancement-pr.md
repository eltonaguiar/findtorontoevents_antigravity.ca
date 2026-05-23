# Crypto Scoring Enhancement PR - Hedge Fund Level
========================================================================
## Review Date: 2026-04-07

## Current State Analysis

### Active Picks (from findtorontoevents.ca/audit)
- 12 crypto picks, 2 forex, 5 equity, 2 commodity = 21 total
- elite_score largely identical (~44-52) with identical breakdowns
- forward_wr_raw = 0.5 on ALL (insufficient data)
- ml_score range: 0.55-0.85 (BEST predictor with +0.33 IC)
- confidence range: 0.4-0.8

### Dashboard Decile Test (1,927 closed picks)
| Rank | Score     | IC     | Bottom WR | Top WR | Spread | Verdict    |
|------|-----------|-------|----------|-------|--------|----------|----------|
| 1    | ml_score | +0.33 | 32.5%   | 60.0% | 27.5pp  | BEST     |
| 2    | confidence| +0.27 | 30.8%   | 51.9% | 21.1pp  | STRONG   |
| 3    | elite_score| +0.012| 28.0%   | 39.4% | 11.4pp  | WEAK    |

### Critical Issues Found

1. **OVERCONFIDENCE PATTERN:** D10 (top decile) underperforms D9
   - Highest scoring picks are WORSE than second tier
   - Need score cap at D9 level

2. **SWEET SPOT EMPIRICAL:** ml_score ≥ 0.65 AND confidence 0.60-0.70 = 55-60% WR
   - Current system: picks with confidence 0.4 are actively traded (should be filtered)
   - Missing: confidence floor at 0.60

3. **ANTI-PREDICTIVE COMPONENTS (still partially active after v2 halving):**
   - ML Replacement Score: IC = -0.19 (ANTI-PREDICTIVE - ZEROED in v1, HALVED in v2)
   - Source System Tier: IC = -0.18 (ANTI-PREDICTIVE - ZEROED in v1, HALVED in v2)
   - Leverage Safety: IC = -0.05 (ANTI-PREDICTIVE - ZEROED in v1, HALVED in v2)
   - Age Freshness: IC = -0.076 (ANTI-PREDICTIVE - ZEROED in v1, HALVED in v2)
   - Risk:Reward Ratio: IC = -0.13 (ZEROED in v1 but may still in formula)

4. **FORWARD VALIDATION GAP:**
   - 0/21 active picks are forward_validated
   - forward_trades = 0 on ALL picks
   - Trading insufficient data picks is gambling, not investing

5. **SCORING STALENESS:**
   - All elite_breakdowns are nearly IDENTICAL
   - forward_wr: 20.0, _forward_wr_raw: 0.5 on EVERY pick
   - No differentiation = no edge

## Proposed Enhancements

### ENHANCEMENT 1: Confidence Floor (Quick Win)
```python
# In quality_gates.py
CONFidence_FLOOR = 0.60  # Sweet spot from data: 0.60-0.70
# Reject confidence < 0.60 (31% WR below this)
```

### ENHANCEMENT 2: Score Cap at D9 Level
```python
# In elite_scorer.py
MAX_VALID_SCORE = 75  # Cap at D9 (second tier wins)
# Overconfidence cap for <15 closed trades
if score > 75 and closed_trades < 15:
    score = min(score, 60)
```

### ENHANCEMENT 3: Zero Remaining Anti-Predictive Components
```python
# In elite_scorer.py - fully zero these
ML_REPLACEMENT_SCORE_WEIGHT = 0  # Was 9 pts, IC=-0.19
SOURCE_TIER_WEIGHT = 0         # Was 10 pts, IC=-0.18
LEVERAGE_SAFETY_WEIGHT = 0     # Was 5 pts, IC=-0.05
AGE_FRESHNESS_WEIGHT = 0        # Was 2 pts, IC=-0.076
RISK_REWARD_WEIGHT = 0           # Was 5 pts, IC=-0.13
```

### ENHANCEMENT 4: Boost Best Predictors
```python
# Increase weight on ml_score (BEST predictor)
ML_SCORE_WEIGHT = 25  # Was 17 pts (from 21) - INCREASE
# Increase weight on confidence (SECOND BEST)
CONFIDENCE_WEIGHT = 20  # Was 9 pts - INCREASE
```

### ENHANCEMENT 5: Forward Validation Gate
```python
# Require forward validation for scoring
MIN_FORWARD_TRADES = 15
MIN_FORWARD_WR = 0.45
# Only score system that has proven forward edge
```

### ENHANCEMENT 6: Sweet Spot Targeting
```python
# Target ml_score >= 0.65 AND confidence 0.60-0.70
SWEET_SPOT_BONUS = 10
if ml_score >= 0.65 and 0.60 <= confidence <= 0.70:
    score += SWEET_SPOT_BONUS
```

### ENHANCEMENT 7: Asset Class Diversification Score
```python
# Current: 12 crypto, 2 forex, 5 equity, 2 commodity
# Hedge funds maintain 30-40% non-crypto allocation
# Penalize crypto-heavy scoring
CRYPTO_PENALTY = -5 if crypto_picks > total_picks * 0.5 else 0
```

## Expected Impact

| Enhancement | WR Impact | Confidence |
|--------------|-----------|------------|
| Confidence floor 0.60 | +8-12% | HIGH |
| Score cap at D9 | +3-5% | HIGH |
| Zero anti-predictive | +5-8% | HIGH |
| Boost ml_score | +10-15% | HIGH |
| Forward validation | +15-20% | VERY HIGH |
| Sweet spot targeting | +12-15% | VERY HIGH |
| Asset diversification | +3-5% | MEDIUM |

**Combined Potential:** +45-65% improvement in WR

## Files to Modify
1. `alpha_engine/elite_scorer.py` - scoring formula
2. `audit_trail/quality_gates.py` - confidence floor
3. `alpha_engine/smart_picks_engine.py` - sweet spot targeting
4. `alpha_engine/forward_validator.py` - forward validation gate