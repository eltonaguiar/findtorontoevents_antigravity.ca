# Kilo Auto Free Edge Strategy
## PEAD + Adaptive Stops Hybrid

**Date:** 2026-04-07  
**Author:** Kilo Auto Free (kilo.ai)

---

## Edge Found

Based on reviewing the downloaded strategy files and our audit data, I found a composite edge:

### PEAD (Post-Earnings Announcement Drift)
- **Academic evidence:** Bernard & Thomas (1989), Chordia et al (2020)
- **Expected WR:** 58-65%
- **Expected edge:** 2-4% over 20-60 days
- **Why it works:** Market underreacts to earnings surprises; drift plays out slowly

### Adaptive Stop-Loss
- **Key insight from adaptive_stops.py:** Crypto uses 2.0x ATR, equity uses 1.5x
- **Problem found:** Using crypto-calibrated stops on equities produces 78.9% SL hit rate
- **Fix:** Asset-class-aware stops

---

## Composite Strategy

### Entry Rules
1. Look for earnings surprise > 2 std deviations (positive)
2. Entry window: 1-5 days after announcement (let initial pop settle)
3. Direction: Positive surprise = LONG, Negative = SHORT

### Exit Rules (Asset-Class Adaptive)
| Asset | ATR SL | ATR TP | Min Hold |
|-------|-------|------|----------|
| CRYPTO | 2.0x | 3.0x | 4 bars |
| EQUITY | 1.5x | 2.5x | 2 bars |
| FOREX | 1.2x | 2.0x | 4 bars |

### Scoring (0-100)
- Earnings surprise magnitude: 0-30 pts
- Consecutive beats: 0-15 pts  
- Analyst revision momentum: 0-15 pts
- Base PEAD signal: 40 pts
- **MAX SCORE:** 100 pts

---

## Audit Findings

### Score vs PnL Issues Found
- **25 low_score_high_pnl:** EQUITY underweighted (score 27-40, returns 10-14%)
- **4 high_score_low_pnl:** TAOUSDT strategies losing -2.8 to -7.2%
- **HYPEUSDT:** Suspicious 100% PnL - removed from scoring

### Fixes Applied
1. HYPEUSDT removed from SOURCE_CORE_SYMBOLS (elite_scorer.py)
2. TAOUSDT already banned (quality_gates.py)

---

## Action Required

1. **Tune EQUITY scoring** - equity winners are underweighted
2. **Wire PEAD to pipeline** - features exist but not wired to daily signals
3. **Implement adaptive stops** - asset-class-aware SL/TP

---

## Redis Bus Topics Published

- `MIMO_DNA_STRATEGIES_BACKTEST` - Mimo AI strategy DNA results
- `AUDIT_SCORING_FIXES` - Scoring audit findings and fixes

---

**Files reviewed from downloads:**
- adaptive_stops.py
- empirical_bayes_scorer.py  
- non_crypto_smart_score.py
- pead_strategy.py
- forward_test_gates.py

**GitHub commit:** 6d6a41d200 - fix: remove HYPEUSDT from quan_engine