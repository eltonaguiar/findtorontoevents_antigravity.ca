# Monte Carlo Validation Report

**Generated:** 2026-03-25T00:18:05Z
**Total trades analyzed:** 2,239
**Simulations per test:** 10,000
**Random seed:** 42

## VERDICT: EDGE_WEAK [MARGINAL]

**Score:** 6/9

- 8/32 strategies show edge (mediocre)
- Portfolio robust: 100% profitable across all tests
- Partial edge across regimes
- 71% chance of profit after 90 days

---
## Test 1: Strategy-Level Monte Carlo

**8 EDGE** | 8 WEAK | 16 NO_EDGE

| Strategy | Trades | WR% | Sharpe | %Profitable Sims | %Ruin | p-value | Verdict |
|----------|--------|-----|--------|-------------------|-------|---------|---------|
| st_obv_support_divergence | 81 | 51.9% | 7.426 | 100.0% | 0.1% | 0.0 | EDGE |
| unknown | 77 | 57.1% | 4.55 | 100.0% | 0.0% | 0.0001 | EDGE |
| ml_enhanced_BNBUSDT_15m_B_lightgbm | 19 | 94.7% | 22.095 | 100.0% | 0.0% | 0.0 | EDGE |
| ml_enhanced_RENDERUSDT_1h_D_ensemble_stack | 19 | 84.2% | 11.789 | 100.0% | 0.0% | 0.0001 | EDGE |
| ml_enhanced_FETUSDT_1d_B_lightgbm | 18 | 94.4% | 41.954 | 100.0% | 0.0% | 0.0 | EDGE |
| copy_hl_NMTD_25M | 17 | 82.4% | 16.473 | 100.0% | 0.0% | 0.0 | EDGE |
| crypto_bayesian_regime_transition_momentum_v1 | 21 | 81.0% | 11.657 | 99.9% | 0.0% | 0.0076 | EDGE |
| st_rsi_momentum_confluence | 78 | 52.6% | 3.116 | 96.0% | 13.3% | 0.0246 | EDGE |
| st_fear_greed_contrarian | 486 | 30.0% | 1.095 | 89.7% | 97.5% | 0.0555 | WEAK |
| crypto_soc_orderflow_absorption_a01_v1 | 14 | 57.1% | 2.539 | 72.0% | 0.0% | 0.2856 | WEAK |
| luxalgo_confluence | 76 | 38.2% | 1.134 | 69.3% | 40.2% | 0.2628 | WEAK |
| crypto_soc_orderflow_absorption_a06_v1 | 10 | 60.0% | 2.221 | 66.8% | 0.0% | 0.3271 | WEAK |
| crypto_soc_orderflow_absorption_a10_v1 | 10 | 60.0% | 2.197 | 66.8% | 0.0% | 0.3381 | WEAK |
| crypto_soc_orderflow_absorption_a04_v1 | 15 | 46.7% | 1.73 | 65.0% | 0.0% | 0.3339 | WEAK |
| funding_momentum | 104 | 56.7% | 0.688 | 64.0% | 25.0% | 0.3495 | WEAK |
| crypto_soc_orderflow_absorption_a03_v1 | 13 | 53.8% | 1.52 | 63.0% | 0.0% | 0.3673 | WEAK |
| multi_period_rsi_confluence | 11 | 45.5% | 0.373 | 49.2% | 0.0% | 0.4537 | NO_EDGE |
| crypto_soc_orderflow_absorption_a08_v1 | 16 | 43.8% | -0.116 | 47.6% | 0.0% | 0.512 | NO_EDGE |
| claude_gainer_ml | 10 | 40.0% | -1.848 | 31.3% | 75.7% | 0.6335 | NO_EDGE |
| crypto_soc_orderflow_absorption_a07_v1 | 17 | 35.3% | -4.306 | 12.5% | 0.0% | 0.8419 | NO_EDGE |
| cta_tsmom_blend | 36 | 5.6% | -3.8 | 10.8% | 0.1% | 0.9876 | NO_EDGE |
| crypto_mtf_ema_slope_alignment_v1 | 11 | 27.3% | -5.778 | 10.8% | 0.0% | 0.8365 | NO_EDGE |
| binance_smart_money | 35 | 45.7% | -3.123 | 9.1% | 97.9% | 0.8936 | NO_EDGE |
| crypto_soc_orderflow_absorption_a02_v1 | 14 | 28.6% | -7.508 | 3.6% | 0.0% | 0.9138 | NO_EDGE |
| hl_funding_fade | 27 | 18.5% | -4.829 | 2.8% | 95.4% | 0.9728 | NO_EDGE |
| atr_regime_rsi | 26 | 19.2% | -8.591 | 0.6% | 0.0% | 0.966 | NO_EDGE |
| crypto_rsi_whaleconfirmed_v1 | 21 | 23.8% | -6.241 | 0.4% | 31.1% | 0.9945 | NO_EDGE |
| winner_pattern_precursor | 96 | 17.7% | -5.539 | 0.0% | 100.0% | 0.9978 | NO_EDGE |
| yahoo_analyst_consensus | 96 | 0.0% | -4.432 | 0.0% | 40.4% | 1.0 | NO_EDGE |
| futures_bb_mean_reversion | 10 | 0.0% | -7.534 | 0.0% | 0.0% | 0.9669 | NO_EDGE |
| ml_enhanced_BTCUSDT_15m_D_ensemble_stack | 10 | 0.0% | -63.081 | 0.0% | 100.0% | 0.994 | NO_EDGE |
| ml_enhanced_ADAUSDT_15m_D_ensemble_stack | 10 | 0.0% | -62.215 | 0.0% | 100.0% | 1.0 | NO_EDGE |

---
## Test 2: Portfolio-Level Monte Carlo

**Actual:** 2239 trades, Final $1,902,322.14, Return 18923.22%, Sharpe 1.062, MaxDD 99.6%

### Shuffle
- Profitable simulations: **100.0%**
- Median final equity: $1,902,322.14
- 5th percentile: $1,902,322.14
- 95th percentile: $1,902,322.14

### Subset 80Pct
- Profitable simulations: **100.0%**
- Median final equity: $655,507.82
- 5th percentile: $120,586.78
- 95th percentile: $3,524,208.71

### Noise 1Pct
- Profitable simulations: **100.0%**
- Median final equity: $1,692,113.36
- 5th percentile: $775,231.43
- 95th percentile: $3,634,630.35

---
## Test 3: Regime-Conditional Monte Carlo

**Regime Verdict:** PARTIAL_EDGE

| Regime | Trades | WR% | Mean PnL | Sharpe | %Profitable Sims | Edge? |
|--------|--------|-----|----------|--------|-------------------|-------|
| BEAR | 13 | 46.2% | 0.786% | 3.549 | 77.7% | YES |
| BULL | 6 | 0.0% | -10.71% | -32.35 | 0.0% | NO |
| CHOPPY | 5 | 20.0% | -1.136% | -10.588 | 7.3% | NO |
| UNKNOWN | 2215 | 36.4% | 0.417% | 1.15 | 99.1% | YES |

---
## Test 4: Filter Combination Stress Test

| Rank | Filter | Trades | WR% | Mean PnL | Sharpe | %Profitable Sims | %Ruin |
|------|--------|--------|-----|----------|--------|-------------------|-------|
| 1 | Golden | 77 | 70.1% | 1.461% | 8.576 | 100.0% | 0.0% |
| 2 | ML_enhanced | 83 | 68.7% | 9.916% | 8.451 | 100.0% | 95.7% |
| 3 | High_confidence_80 | 262 | 54.6% | 3.783% | 5.186 | 100.0% | 90.1% |
| 4 | High_ML_score | 300 | 41.7% | 3.398% | 4.462 | 100.0% | 100.0% |
| 5 | Crypto_only | 2019 | 39.7% | 0.47% | 1.234 | 99.7% | 100.0% |
| 6 | Low_RR_safe | 197 | 50.8% | 1.14% | 2.733 | 98.4% | 98.6% |
| 7 | Copy_trader | 34 | 58.8% | 0.738% | 4.307 | 91.3% | 2.5% |
| 8 | Forex_only | 34 | 8.8% | -0.222% | -2.663 | 36.7% | 7.5% |
| 9 | GAMMA_proxy | 279 | 31.5% | -0.129% | -0.453 | 19.0% | 99.9% |
| 10 | Large_cap_TIER1 | 1257 | 38.1% | -0.096% | -0.483 | 5.9% | 100.0% |

---
## Test 5: Worst-Case Scenario Analysis

### Worst outcomes by trade horizon

| Trades | Worst 1% | Worst 5% | Median |
|--------|----------|----------|--------|
| 50 | $4,728.57 | $6,220.68 | $10,969.09 |
| 100 | $3,788.76 | $5,368.30 | $12,488.93 |
| 200 | $2,876.96 | $4,619.91 | $15,558.57 |

### Consecutive Loss Expectations (over 200 trades)
- Median max consecutive losses: **10**
- 95th percentile: **15**
- 99th percentile: **19**

### $10,000 Account Probability Scenarios

| Timeframe | Profitable | Lose 10% | Lose 20% | Lose 50% | Double |
|-----------|------------|----------|----------|----------|--------|
| 50 trades | 61.8% | 27.2% | 17.4% | 1.2% | 7.5% |
| 150 trades | 70.8% | 24.0% | 18.7% | 4.9% | 30.9% |
| 300 trades | 76.9% | 19.8% | 16.3% | 6.2% | 49.5% |

---
*Report generated 2026-03-25T00:18:05Z | 2,239 trades | 10,000 simulations per test*