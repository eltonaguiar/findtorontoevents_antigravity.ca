# Deep Trade Analysis: Day-of-Week & Asset Class Edge Report

*Generated: 2026-04-06 | Corpus: 3223 closed picks*

> Scientific basis: Weekday effect documented in Bouman & Jacobsen (2002) "The Halloween Indicator", 
> Lakonishok & Smidt (1988) "Are Seasonal Anomalies Real?", and FX market microstructure literature
> (Osler 2000, 2003) showing Monday/Friday edge decay from institutional rebalancing and weekend gap risk.

## 1. Day-of-Week Analysis


### 1.1 Overall DoW Performance

| Day | n | WR % | Avg PnL % | Median PnL % | Total PnL % | Stdev |
| --- | --- | --- | --- | --- | --- | --- |
| Monday | 430 | 26.3% | -0.217% | -0.150% | -93.3% | 0.743 |
| Tuesday | 210 | 34.3% | +0.317% | -0.150% | +66.5% | 1.568 |
| Wednesday | 374 | 35.8% | -0.050% | -0.150% | -18.9% | 1.200 |
| Thursday | 294 | 27.9% | -0.299% | -0.561% | -87.8% | 1.221 |
| Friday | 403 | 32.8% | +0.034% | -0.150% | +13.8% | 1.097 |
| Saturday | 760 | 31.2% | -0.167% | -0.150% | -126.7% | 0.557 |
| Sunday | 661 | 28.0% | -0.198% | -0.150% | -130.7% | 0.533 |

### 1.2 DoW Breakdown by Asset Class


**CRYPTO**

| Day | n | WR % | Avg PnL % |
| --- | --- | --- | --- |
| Monday | 430 | 26.3% | -0.217% |
| Tuesday | 210 | 34.3% | +0.317% |
| Wednesday | 374 | 35.8% | -0.050% |
| Thursday | 294 | 27.9% | -0.299% |
| Friday | 403 | 32.8% | +0.034% |
| Saturday | 760 | 31.2% | -0.167% |
| Sunday | 661 | 28.0% | -0.198% |

### 1.3 Hour-of-Day (UTC) — Top/Bottom 5 Hours

| Hour (UTC) | n | WR % | Avg PnL % | Notes |
| --- | --- | --- | --- | --- |
| 07:00 | 132 | 44.7% | -0.010% | TOP |
| 20:00 | 121 | 42.1% | -0.010% | TOP |
| 08:00 | 104 | 38.5% | -0.015% | TOP |
| 16:00 | 112 | 37.5% | -0.027% | TOP |
| 05:00 | 118 | 34.7% | +0.066% | TOP |
| 22:00 | 160 | 21.9% | -0.264% | BOTTOM |
| 09:00 | 141 | 22.0% | -0.434% | BOTTOM |
| 18:00 | 133 | 22.6% | -0.308% | BOTTOM |
| 12:00 | 124 | 22.6% | -0.164% | BOTTOM |
| 15:00 | 116 | 23.3% | -0.359% | BOTTOM |

**Scientific context:** Literature consistently documents a *Monday effect* (lower returns)
and *Friday effect* (higher volatility/gap risk). FX volume peaks Tue–Thu 08:00–16:00 UTC
(London/NY overlap). Crypto has 24/7 activity but weekend liquidity thins by ~40%, widening
spreads and increasing SL trigger noise (Lo et al., 2000; Amihud, 2002).

## 2. Asset Class Deep Analysis


### 2.1 Overall AC Performance

| Asset Class | n | WR % | Avg PnL % | Total PnL % | Mean R:R | Median R:R |
| --- | --- | --- | --- | --- | --- | --- |
| CRYPTO | 3214 | 30.5% | -0.140% | -449.8% | 1.67 | 1.67 |
| FOREX | 5 | 60.0% | +0.000% | +0.0% | 1.36 | 1.22 |
| FUTURES | 4 | 0.0% | -0.004% | -0.0% | 1.67 | 1.67 |

### 2.2 Direction Bias by Asset Class

| Asset Class | Direction | n | WR % | Avg PnL % |
| --- | --- | --- | --- | --- |
| CRYPTO | BUY | 2703 | 27.6% | -0.141% |
| CRYPTO | LONG | 321 | 45.5% | -0.252% |
| CRYPTO | SHORT | 176 | 47.7% | +0.022% |
| CRYPTO | SELL | 14 | 42.9% | +0.629% |

### 2.3 Exit Reason by Asset Class

| Asset Class | Exit Reason | n | WR % | Avg PnL % |
| --- | --- | --- | --- | --- |
| CRYPTO | SL | 1296 | 0.0% | -0.749% |
| CRYPTO | TIME_EXIT | 803 | 16.6% | -0.084% |
| CRYPTO | TP | 618 | 100.0% | +1.077% |
| CRYPTO | SL_HIT | 176 | 0.0% | -0.844% |
| CRYPTO | EXPIRED | 155 | 61.9% | +0.006% |
| CRYPTO | TP_HIT | 112 | 100.0% | +0.628% |
| CRYPTO | SL_HIT_RESOLVED | 24 | 0.0% | -0.011% |
| CRYPTO | TP_HIT_RESOLVED | 17 | 100.0% | +0.023% |
| CRYPTO | PRICE_RESOLVED | 13 | 38.5% | -0.006% |
| FOREX | PRICE_RESOLVED | 5 | 60.0% | +0.000% |

### 2.4 Confidence Calibration by Asset Class

| Asset Class | Conf Band | n | WR % | Avg PnL % | Signal quality |
| --- | --- | --- | --- | --- | --- |
| CRYPTO | <0.55 | 246 | 39.8% | -0.058% | OK |
| CRYPTO | 0.55-0.60 | 754 | 38.5% | -0.091% | OK |
| CRYPTO | 0.60-0.65 | 934 | 32.3% | -0.194% | POOR |
| CRYPTO | 0.65-0.70 | 927 | 14.2% | -0.116% | POOR |
| CRYPTO | 0.70-0.75 | 164 | 33.5% | -0.088% | POOR |
| CRYPTO | 0.75-0.80 | 25 | 52.0% | -0.071% | GOOD |
| CRYPTO | 0.80-0.85 | 82 | 79.3% | +0.133% | GOOD |

### 2.5 Top & Worst Strategies by Asset Class


**CRYPTO**

| Strategy | n | WR % | Avg PnL % | Tier |
| --- | --- | --- | --- | --- |
| ml_enhanced_BNBUSDT_15m_B_lightgbm | 19 | 89.5% | +0.048% | TOP |
| ml_enhanced_FETUSDT_1d_B_lightgbm | 25 | 88.0% | +0.330% | TOP |
| ml_enhanced_RENDERUSDT_4h_D_ensemble_stack | 18 | 77.8% | +0.050% | TOP |
| ml_enhanced_RENDERUSDT_1h_D_ensemble_stack | 29 | 75.9% | +0.060% | TOP |
| ml_enhanced_DOGEUSDT_15m_D_ensemble_stack | 11 | 72.7% | +0.002% | TOP |
| ml_enhanced_TRXUSDT_1d_B_lightgbm | 12 | 0.0% | -0.787% | WORST |
| ml_enhanced_STRKUSDT_15m_D_ensemble_stack | 11 | 9.1% | -0.006% | WORST |
| volume_spike_breakout | 32 | 9.4% | -2.031% | WORST |
| quan_engine_scalp | 66 | 15.2% | -0.212% | WORST |
| ml_enhanced_BTCUSDT_15m_D_ensemble_stack | 12 | 16.7% | -0.069% | WORST |

## 3. Scoring Edge & Flaw Summary


### 3.1 EDGES (exploit these)


### 3.2 FLAWS (fix these)

1. CONF FLAW [CRYPTO] band 0.65-0.70: WR=14% n=927 — confidence miscalibrated

### 3.3 Confidence Miscalibration Evidence

Ideal: higher confidence → higher WR (monotone). Reality from our corpus:

| Conf Band | n | WR % |
| --- | --- | --- |
| <0.55 | 246 | 39.8% |
| 0.55-0.60 | 754 | 38.5% |
| 0.60-0.65 | 935 | 32.4% |
| 0.65-0.70 | 928 | 14.2% |
| 0.70-0.75 | 165 | 33.3% |
| 0.75-0.80 | 31 | 48.4% |
| 0.80-0.85 | 82 | 79.3% |

**Finding**: If the WR curve is not monotonically increasing with confidence, the confidence
score is miscalibrated (Platt 1999, Niculescu-Mizil & Caruana 2005 — calibration literature).

### 3.4 Suggested Scoring Adjustments

Based on empirical evidence from this corpus:

| Dimension | Current Behaviour | Recommendation |
| --- | --- | --- |
| DoW gate (crypto) | No day filter | Penalise Monday picks: WR=26% |
| DoW bonus (crypto) | No day bonus | Boost Wednesday picks: WR=36% |
| CRYPTO scoring | SCALP bias | CRYPTO WR=31% avg=-0.140% — need SWING preference |
| Confidence floor | Flat / mode-aware (recent P0 fix) | Monitor 0.65+ enforcement |

## 4. Statistical Significance Notes


All DoW findings should be treated as directional, not causal, unless sample sizes allow
proper chi-squared testing. Minimum 30 picks per cell recommended for WR inference.

| Test | Threshold | Notes |
| --- | --- | --- |
| Chi-squared WR difference | p < 0.05 requires n>30 per bucket | Use Fisher exact for small n |
| Sharpe ratio by DoW | SR > 0.5 actionable | Weekend crypto SR typically < 0 |
| Calibration (Brier score) | < 0.25 good | Our conf curve needs verification |
| Multiple comparisons | Bonferroni correction for 7 days × 4 ACs = 28 cells | α = 0.05/28 ≈ 0.0018 |

**Scientific references:**
- Bouman & Jacobsen (2002): Halloween indicator — Oct–Apr vs May–Sep seasonal effect
- Lakonishok & Smidt (1988): Holiday/weekend anomalies in equities
- Osler (2000, 2003): FX order clustering at round numbers — impacts SL hit rate
- Amihud (2002): Illiquidity premium — weekend crypto spread widening triggers noise SLs
- Lo et al. (2000): Foundation of technical trading rules persistence
- Jegadeesh & Titman (1993): Momentum — strategy half-life by asset class
