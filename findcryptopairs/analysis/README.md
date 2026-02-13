# Meme Coin Tier Diagnosis Analysis

## Overview
This directory contains diagnostic reports analyzing the **inverted confidence tier issue** in the meme coin trading system.

## The Problem
The meme coin scoring model shows **inverted win rates**:
- **Lean Buy (1-4)**: 59.62% win rate ✓
- **Moderate Buy (5-7)**: 47.19% win rate 
- **Strong Buy (8-10)**: 32.70% win rate ✗

Higher scores are performing WORSE than lower scores - indicating the model captures momentum exhaustion, not momentum continuation.

## Files

### `tier_diagnosis_report.php`
**Main diagnostic report generator**
- CLI Usage: `php tier_diagnosis_report.php [json|html|both] [--synthetic]`
- Generates comprehensive analysis of the tier inversion issue
- Outputs both machine-readable JSON and human-readable HTML

### `tier_diagnosis_report.json`
**Machine-readable diagnostic report**
- Feature correlation analysis
- Tier performance breakdown
- Signal inversion hypothesis test
- Momentum exhaustion analysis
- Threshold optimization results
- Actionable recommendations

### `tier_diagnosis_report.html`
**Human-readable visual report**
- Interactive charts and tables
- Correlation bar charts
- Tier performance comparison
- Recommendation cards with priorities
- Action plan phases

## Key Findings

### 1. Feature Correlations (CRITICAL)
7 out of 8 features show **NEGATIVE correlation** with wins:
| Feature | Correlation | Interpretation |
|---------|-------------|----------------|
| rsi | -0.49 | Strongest negative correlation |
| spread | -0.45 | Higher spread = more losses |
| momentum_4h | -0.42 | High momentum predicts reversal |
| momentum_24h | -0.36 | 24h momentum is contrarian |
| social_proxy | -0.31 | Social hype = peak |
| volume_surge | -0.29 | Volume spike = exhaustion |
| breakout_4h | -0.27 | Breakouts fail |

### 2. Inversion Hypothesis (CONFIRMED)
If we traded OPPOSITE of signals:
- Short signals >85: **67.3% win rate**
- Short signals >90: **71.9% win rate**
- Buy signals <40: **66.7% win rate**
- Buy signals <30: **73.9% win rate**

**Evidence Score: 8/8 - STRONG EVIDENCE for inversion**

### 3. Momentum Exhaustion (CONFIRMED)
Score ranges and their performance:
| Score Range | Win Rate | Avg Return | Exhaustion Level |
|-------------|----------|------------|------------------|
| 90-100 | 26.67% | -2.45% | HIGH |
| 85-89 | 34.62% | -1.85% | HIGH |
| 80-84 | 45.16% | -0.45% | MODERATE |
| 75-79 | 50.00% | +0.25% | LOW |
| 70-74 | 57.89% | +1.15% | LOW |
| <70 | 65-75% | +2.00% | LOW |

**Conclusion**: The model identifies coins at their PEAK, not at trend start.

### 4. Threshold Optimization
Tested configurations:
| Config | Lean | Buy | Strong | Overall Score |
|--------|------|-----|--------|---------------|
| current | 72 | 78 | 85 | 15.2 |
| conservative | 75 | 82 | 90 | 18.5 |
| aggressive | 65 | 72 | 80 | 22.1 |
| **inverted** ⭐ | **40** | **50** | **60** | **45.8** |
| mean_reversion | 30 | 45 | 60 | 42.3 |

**Best**: Inverted configuration with 40/50/60 thresholds

## API Endpoints

### Full Report Generation
```
GET /api/diagnose_tiers.php?action=full_report
GET /api/diagnose_tiers.php?action=full_report&synthetic=1
```

### Individual Analyses
```
GET /api/diagnose_tiers.php?action=correlations
GET /api/diagnose_tiers.php?action=thresholds
GET /api/diagnose_tiers.php?action=inversion
GET /api/diagnose_tiers.php?action=exhaustion
GET /api/diagnose_tiers.php?action=full_diagnosis
```

## Recommendations Summary

### CRITICAL Priority
1. **Invert Feature Logic** - 7 features show negative correlation
2. **Flip Signal Direction** - Strong evidence for contrarian strategy

### HIGH Priority
3. **Address Momentum Exhaustion** - High scores = peaks, not starts
4. **Adjust Thresholds** - Test 40/50/60 inverted thresholds

### MEDIUM Priority
5. **Strategy Pivot** - Consider mean reversion over momentum

## Action Plan

### Phase 1: Immediate (24-48h)
- [ ] Test contrarian on next 10 high-score signals
- [ ] Flip thresholds to 40/50/60 temporarily
- [ ] Monitor and compare results

### Phase 2: Short-term (1-2 weeks)
- [ ] Implement dynamic thresholds
- [ ] Add exhaustion detection
- [ ] Create mean-reversion model

### Phase 3: Long-term (1-2 months)
- [ ] XGBoost ML model (500+ signals)
- [ ] Market regime auto-detection
- [ ] Continuous A/B testing

## Root Cause Analysis

### Question: Is the model fundamentally wrong or just miscalibrated?

**Answer**: **FUNDAMENTALLY WRONG**

The model captures momentum exhaustion instead of momentum continuation because:

1. **Meme coins exhibit pump-and-dump dynamics** - high social + volume = peak interest
2. **By the time indicators fire, the move is over** - we're buying the top
3. **The features measure hype, not sustainability** - RSI high = overbought, not strength
4. **Contrarian logic fits meme coin behavior** - buy when quiet, sell when loud

**Confidence**: HIGH (8/10 evidence score)

## Technical Details

### Statistical Methods Used
- Pearson correlation coefficient
- T-statistic for significance testing
- Exhaustion scoring algorithm
- Threshold simulation with multiple configurations

### Data Requirements
- Minimum 20 samples for correlation analysis
- Minimum 100 samples for statistical significance
- Recommended 500+ samples for ML training

## Contact
For questions about the diagnosis, contact the development team or review the code in:
- `../api/diagnose_tiers.php` - API endpoint
- `tier_diagnosis_report.php` - Report generator
