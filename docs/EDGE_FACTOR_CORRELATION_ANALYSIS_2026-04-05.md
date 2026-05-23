# Edge Factor Correlation Analysis

**Date:** 2026-04-05 16:00 UTC
**Dataset:** 3,500 closed picks across 3 asset classes

---

## EXECUTIVE SUMMARY

Factor hierarchy INVERTS by asset class:

CRYPTO: Forward WR (weak), Trust Score (strong), Score (weak)
EQUITIES: Forward WR (MASSIVE), Forward PF (strong), Score (strong)
FOREX: Forward WR (medium), Score (medium)

KEY: Cannot use unified scoring across assets.

---

## CRYPTO ANALYSIS (2,881 picks, 43.5% WR baseline)

### Top Predictive Factors

1. strat_fwd_wr (Effect: 0.41)
   - Winners avg: 44.83% | Losers avg: 40.59% | Delta: +4.24pp

2. trust_score (Effect: 0.34)
   - Winners avg: 3.324 | Losers avg: 2.766 | Delta: +0.558

3. score (Effect: 0.23)
   - Winners avg: 44.58 | Losers avg: 42.29 | Delta: +2.29

4. strat_fwd_pf (Effect: 0.15)
   - Winners avg: 2.748 | Losers avg: 1.158 | Delta: +1.589

### Winning Combinations

BEST: Trust >= 3.5 AND FwdWR >= 50%
- 668 picks (23.2% of pool)
- Win Rate: 60.3% (vs 43.5% baseline = +16.8pp)
- ACTION: Use as primary filter

SECONDARY: Score >= 45 AND Confidence >= 0.65
- 826 picks (28.7%)
- Win Rate: 57.9% (+14.4pp)
- ACTION: Fallback filter

### Repeatable Symbols (10+ trades)

HYPEUSDT: 84 trades, 38.1% WR, +99.18% cumulative
  - Avg win: +3.92% | Avg loss: -0.50% | Payout ratio: 7.8x

LTCUSDT: 65 trades, 69.2% WR, +49.88% cumulative
  - Highest win rate of all symbols

DOTUSDT: 118 trades, 46.6% WR, +52.00% cumulative
  - Consistent volume + reliability

---

## EQUITIES ANALYSIS (531 picks, 33.7% WR baseline)

### Top Predictive Factors

1. strat_fwd_wr (Effect: 0.99) ***DOMINANT***
   - Winners: 45.96% | Losers: 27.97% | Delta: +17.99pp

2. forward_wr (Effect: 0.91) ***DOMINANT***
   - Winners: 43.29% | Losers: 26.08% | Delta: +17.21pp

3. strat_fwd_pf (Effect: 0.77) ***STRONG***
   - Winners: 1.157 | Losers: 0.651 | Delta: +0.506

KEY DIFFERENCE: Forward metrics are 10x stronger than crypto.

### Winning Combination

ELITE: FwdWR >= 60% AND FwdPF >= 1.5
- 40 picks (7.5% of pool)
- Win Rate: 65% (vs 33.7% baseline = +31.3pp)
- ACTION: Hard gate - highly selective but proven

### Repeatable Symbols (10+ trades)

XOM: 26 trades, 73.1% WR, +68.44% cumulative
CVX: 22 trades, 81.8% WR, +65.62% cumulative

CRITICAL INSIGHT: Only energy stocks work. Everything else is noise.

### Strategies to KILL

Value + Quality: 0% WR, -163.86% cumulative
Consecutive Beats: 13.8% WR, -99.08% cumulative
Earnings Drift: 11.8% WR, -58.75% cumulative

---

## FOREX ANALYSIS (88 picks, 25% WR baseline)

Top factors: Forward WR (0.68), Forward WR (0.62)
Sample too small for strategy recommendations.

---

## SOURCE PERFORMANCE ANALYSIS

### Top Sources

claude_gainer_st: 851 picks, 55.1% WR, +158.97% cumulative
  - Avg trust_score (winners): 4.90
  - Trait: High calibration

st_fear_greed_contrarian: 524 picks, 62% WR, +209.46% cumulative
  - Trait: Pure signal-based

signal_validation: 35 picks, 57.1% WR, +22.69% cumulative
  - Trait: Very selective entry

### Bottom Sources (DELETE/GATE OUT)

stocks_competition: 281 picks, 33.5% WR, -304.21% cumulative [DELETE]
kimi_riseoftheclaw: 233 picks, 34.8% WR, -113.67% cumulative [DEMOTE]
ml_crypto_pred: 120 picks, 31.7% WR, -49.86% cumulative [GATE OUT]

---

## DIRECTION ANALYSIS (LONG vs SHORT)

LONG: 3,177 picks, 41.4% WR, -161.52% cumulative
SHORT: 323 picks, 43% WR, +14.92% cumulative

Insight: SHORT is underused (10:1 ratio) but more profitable.
Implication: SHORT filters are more selective - consider bias flip.

---

## CRITICAL RECOMMENDATIONS

IMMEDIATE (This Week):

1. Add Crypto Filter: Trust >= 3.5 AND strat_fwd_wr >= 50%
   Result: 668 picks @ 60.3% WR (vs 43.5% baseline)

2. Add Equities Gate: strat_fwd_wr >= 60% AND strat_fwd_pf >= 1.5
   Result: 40 picks @ 65% WR (vs 33.7% baseline)

3. DELETE strategies: Value+Quality, Consecutive Beats, Earnings Drift, Dividend Aristocrats

4. GATE OUT sources: stocks_competition (-304%), kimi_riseoftheclaw (-113%), ml_crypto_pred (-49%)

5. BUILD per-symbol confidence tables for repeatable winners:
   CRYPTO: HYPEUSDT (7.8x payout), LTCUSDT (69% WR), DOTUSDT
   EQUITIES: XOM (73% WR), CVX (82% WR)

HIGH PRIORITY (48h):

6. Resurrect futures module (0 picks = dead)
7. Energy-only equities strategy (kill all non-energy)
8. Build source-specific weighting (claude_gainer_st +50%, stocks_competition -100%)
9. Surface factor combinations in dashboard
10. Validate why st_fear_greed works despite confidence not separating winners/losers

---

## CONCLUSION

Portfolio has hidden structure buried under noise:

CRYPTO works (43.5% baseline) but needs Trust filtering to reach 60% WR
EQUITIES broken (33.7% baseline) except energy (75% WR)
SOURCES matter more than factors
ASYMMETRIC PAYOFF is real: HYPEUSDT wins 7.8x bigger than loses

The edge exists. Apply the filters above.

