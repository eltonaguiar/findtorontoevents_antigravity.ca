# DEFINITIVE EDGE ANALYSIS REPORT

Generated: 2026-03-24 23:57 UTC

**BRUTAL HONEST ASSESSMENT - No inflated claims**

## OVERALL VERDICT

System-wide WR is 34.9% across 493 trades. This is NOT significantly above 50% (p=1.0). The system does NOT have a proven edge at the aggregate level. Total PnL: 570.6% raw, -16.2% capped at 10%. Found 9 statistically significant edge sources out of 29 tested. The edge, if any, is concentrated in specific strategies/symbols, not system-wide.

| Metric | Value |
|--------|-------|
| Total Trades | 493 |
| Wins / Losses | 172 / 321 |
| Win Rate | 34.89% |
| Binomial p-value (vs 50%) | 1.0 |
| Statistically Significant | NO |
| Raw Total PnL | 570.61% |
| Capped PnL (10% max) | -16.18% |

---
## PART 1: EDGE BY ASSET CLASS

| Asset Class | Trades | Wins | WR% | Raw PnL% | Capped PnL% | PF | p-value | Edge? |
|-------------|--------|------|-----|----------|-------------|-----|---------|-------|
| crypto | 385 | 160 | 41.56% | 599.84% | 13.06% | 1.558 | 0.999626 | NO |
| equity | 65 | 3 | 4.62% | -12.39% | -12.39% | 0.0 | 1.0 | NO |
| commodity | 21 | 3 | 14.29% | -9.3% | -9.3% | 0.0 | 0.999889 | NO |
| forex | 18 | 6 | 33.33% | -7.55% | -7.55% | 0.022 | 0.951874 | NO |
| bond | 4 | 0 | 0.0% | 0.0% | 0.0% | 0 | 1.0 | NO |

### CRYPTO
- Best strategy: **copy_hl_whale_123M_87roi** (4 trades, 100.0% WR, 11.79% PnL)
- Worst strategy: **momentum_catcher** (3 trades, 0.0% WR, -2.24% PnL)

### EQUITY
- Best strategy: **cta_tsmom_blend** (6 trades, 16.7% WR, 0.0% PnL)
- Worst strategy: **yahoo_analyst_consensus** (54 trades, 0.0% WR, -12.39% PnL)

### COMMODITY
- Best strategy: **futures_bb_mean_reversion** (3 trades, 33.3% WR, -1.55% PnL)
- Worst strategy: **futures_ema_stack_momentum** (4 trades, 0.0% WR, -3.1% PnL)

### FOREX
- Best strategy: **ig_contrarian_sentiment** (3 trades, 66.7% WR, 0.0% PnL)
- Worst strategy: **forex_carry_momentum** (4 trades, 0.0% WR, 0.0% PnL)

### BOND
- Best strategy: **none** (0 trades, 0% WR, 0% PnL)
- Worst strategy: **none** (0 trades, 0% WR, 0% PnL)

---
## PART 2: EDGE BY STRATEGY (Top 20 by trade count, min 10 trades)

| # | Strategy | Family | Cat | Trades | WR% | PF | Avg PnL% | Total PnL% | p-value | Edge? |
|---|----------|--------|-----|--------|-----|-----|----------|------------|---------|-------|
| 1 | ml_enhanced_BNBUSDT_15m_B_lightgbm | unknown | crypto | 17 | 94.12% | 470.463 | 6.0754% | 103.28% | 0.000137 | YES |
| 2 | ml_enhanced_FETUSDT_1d_B_lightgbm | unknown | crypto | 16 | 93.75% | 529.539 | 37.969% | 607.5% | 0.000259 | YES |
| 3 | ml_enhanced_RENDERUSDT_1h_D_ensemble_stack | unknown | crypto | 16 | 87.5% | 35.193 | 10.6588% | 170.54% | 0.00209 | YES |
| 4 | copy_hl_NMTD_25M | unknown | crypto | 16 | 81.25% | 6.09 | 2.0023% | 32.04% | 0.010635 | YES |
| 5 | binance_smart_money | trend | crypto | 24 | 45.83% | 0.683 | -0.8625% | -20.7% | 0.729372 | NO |
| 6 | hl_funding_fade | sentiment | crypto | 16 | 25.0% | 0.436 | -1.7856% | -28.57% | 0.989365 | NO |
| 7 | cta_tsmom_blend | momentum | forex | 18 | 16.67% | 0.0 | -0.1721% | -3.1% | 0.999344 | NO |
| 8 | winner_pattern_precursor | unknown | crypto | 96 | 17.71% | 0.379 | -0.9573% | -91.9% | 1.0 | NO |
| 9 | yahoo_analyst_consensus | unknown | equity | 55 | 0.0% | 0.0 | -0.2252% | -12.39% | 1.0 | NO |
| 10 | ml_enhanced_BTCUSDT_15m_D_ensemble_stack | unknown | crypto | 10 | 0.0% | 0.0 | -8.5275% | -85.27% | 1.0 | NO |
| 11 | ml_enhanced_ADAUSDT_15m_D_ensemble_stack | unknown | crypto | 10 | 0.0% | 0.0 | -11.6966% | -116.97% | 1.0 | NO |

### Statistically Significant Strategies - Symbol Decomposition


**ml_enhanced_BNBUSDT_15m_B_lightgbm** (94.12% WR, p=0.000137)
  - BNBUSDT: 17 trades, 94.1% WR, 103.28% PnL

**ml_enhanced_FETUSDT_1d_B_lightgbm** (93.75% WR, p=0.000259)
  - FETUSDT: 16 trades, 93.8% WR, 607.5% PnL

**ml_enhanced_RENDERUSDT_1h_D_ensemble_stack** (87.5% WR, p=0.00209)
  - RENDERUSDT: 16 trades, 87.5% WR, 170.54% PnL

**copy_hl_NMTD_25M** (81.25% WR, p=0.010635)
  - FARTCOINUSDT: 5 trades, 100.0% WR, 14.74% PnL
  - ETHUSDT: 3 trades, 100.0% WR, 8.85% PnL
  - MONUSDT: 2 trades, 100.0% WR, 5.9% PnL
  - AAVEUSDT: 2 trades, 50.0% WR, 0.85% PnL
  - SKYUSDT: 2 trades, 0.0% WR, -4.2% PnL
  - CRVUSDT: 1 trades, 100.0% WR, 2.95% PnL
  - XPLUSDT: 1 trades, 100.0% WR, 2.95% PnL

---
## PART 3: WHERE IS THE REAL EDGE?

Ranked by statistical significance (lowest p-value = strongest evidence).

| # | Source | Type | Trades | WR% | p-value | PnL% | Verdict |
|---|--------|------|--------|-----|---------|------|---------|
| 1 | Strategy: ml_enhanced_BNBUSDT_15m_B_lightgbm (crypto) | strategy | 17 | 94.12% | 0.000137 | 103.28% | EDGE |
| 2 | Combo: ml_enhanced_BNBUSDT_15m_B_lightgbm::BNBUSDT | strategy_symbol_combo | 17 | 94.12% | 0.000137 | 103.28% | EDGE |
| 3 | Strategy: ml_enhanced_FETUSDT_1d_B_lightgbm (crypto) | strategy | 16 | 93.75% | 0.000259 | 607.5% | EDGE |
| 4 | Combo: ml_enhanced_FETUSDT_1d_B_lightgbm::FETUSDT | strategy_symbol_combo | 16 | 93.75% | 0.000259 | 607.5% | EDGE |
| 5 | Strategy: ml_enhanced_RENDERUSDT_1h_D_ensemble_stack (crypto) | strategy | 16 | 87.5% | 0.00209 | 170.54% | EDGE |
| 6 | Combo: ml_enhanced_RENDERUSDT_1h_D_ensemble_stack::RENDERUSDT | strategy_symbol_combo | 16 | 87.5% | 0.00209 | 170.54% | EDGE |
| 7 | Strategy: copy_hl_NMTD_25M (crypto) | strategy | 16 | 81.25% | 0.010635 | 32.04% | EDGE |
| 8 | Confidence: high_confidence_80+ | confidence | 120 | 59.17% | 0.02739 | 845.41% | EDGE |
| 9 | Combo: copy_hl_NMTD_25M::FARTCOINUSDT | strategy_symbol_combo | 5 | 100.0% | 0.03125 | 14.74% | EDGE |
| 10 | Combo: ml_enhanced_RENDERUSDT_4h_D_ensemble_stack::RENDERUSDT | strategy_symbol_combo | 7 | 85.71% | 0.0625 | 84.71% | MARGINAL |
| 11 | Regime: bear | regime | 13 | 46.15% | 0.709473 | 10.22% | NO EDGE |
| 12 | Strategy: binance_smart_money (crypto) | strategy | 24 | 45.83% | 0.729372 | -20.7% | NO EDGE |
| 13 | Direction: BUY_forex | direction | 15 | 40.0% | 0.849121 | -7.55% | NO EDGE |
| 14 | Direction: BUY_crypto | direction | 325 | 46.15% | 0.925436 | 1125.46% | NO EDGE |
| 15 | Direction: BUY_commodity | direction | 13 | 23.08% | 0.98877 | -9.3% | NO EDGE |
| 16 | Strategy: hl_funding_fade (crypto) | strategy | 16 | 25.0% | 0.989365 | -28.57% | NO EDGE |
| 17 | Strategy: cta_tsmom_blend (forex) | strategy | 18 | 16.67% | 0.999344 | -3.1% | NO EDGE |
| 18 | Asset class: crypto | asset_class | 385 | 41.56% | 0.999626 | 599.84% | NO EDGE |
| 19 | Asset class: commodity | asset_class | 21 | 14.29% | 0.999889 | -9.3% | NO EDGE |
| 20 | Asset class: equity | asset_class | 65 | 4.62% | 1.0 | -12.39% | NO EDGE |

**Summary:** 9 out of 29 tested edge sources are statistically significant (p<0.05).

**Significant edges found in:**
- Strategy: ml_enhanced_BNBUSDT_15m_B_lightgbm (crypto): 94.12% WR, p=0.000137
- Combo: ml_enhanced_BNBUSDT_15m_B_lightgbm::BNBUSDT: 94.12% WR, p=0.000137
- Strategy: ml_enhanced_FETUSDT_1d_B_lightgbm (crypto): 93.75% WR, p=0.000259
- Combo: ml_enhanced_FETUSDT_1d_B_lightgbm::FETUSDT: 93.75% WR, p=0.000259
- Strategy: ml_enhanced_RENDERUSDT_1h_D_ensemble_stack (crypto): 87.5% WR, p=0.00209
- Combo: ml_enhanced_RENDERUSDT_1h_D_ensemble_stack::RENDERUSDT: 87.5% WR, p=0.00209
- Strategy: copy_hl_NMTD_25M (crypto): 81.25% WR, p=0.010635
- Confidence: high_confidence_80+: 59.17% WR, p=0.02739
- Combo: copy_hl_NMTD_25M::FARTCOINUSDT: 100.0% WR, p=0.03125

---
## PART 4: LOW-SCORE WINNERS (Score <40, PnL >3%)

Found **97** picks that scored low but won big.

- Average PnL: 16.01%
- Average confidence: 0.6692

**Strategy distribution:**
  - ml_enhanced_FETUSDT_1d_B_lightgbm: 15 picks
  - ml_enhanced_BNBUSDT_15m_B_lightgbm: 14 picks
  - ml_enhanced_RENDERUSDT_1h_D_ensemble_stack: 10 picks
  - winner_pattern_precursor: 9 picks
  - ml_enhanced_RENDERUSDT_4h_D_ensemble_stack: 6 picks
  - binance_smart_money: 4 picks
  - hl_funding_fade: 2 picks
  - emergency_gainer_capture: 2 picks
  - hl_momentum_continuation: 1 picks
  - hl_mean_reversion: 1 picks

**Family distribution:**
  - unknown: 89 picks
  - trend: 4 picks
  - sentiment: 2 picks
  - momentum: 2 picks

**Category distribution:**
  - crypto: 97 picks

**Scoring recommendation:** Found 97 picks scoring <40 that returned >3%. Average PnL: 16.0%. Top families: unknown(89), trend(4), sentiment(2). The scoring system is overly penalizing these strategies. Consider: (1) Forward validation penalty is too harsh for new strategies, (2) ML confidence caps hurt heuristic strategies, (3) Some families outperform despite low technical scores.

### All Low-Score Winners:

| Strategy | Symbol | PnL% | Score | Confidence | Direction | Regime |
|----------|--------|------|-------|------------|-----------|--------|
| ml_enhanced_FETUSDT_1d_B_lightgbm | FETUSDT | 49.05% | 1.0 | 0.80 | BUY | None |
| ml_enhanced_FETUSDT_1d_B_lightgbm | FETUSDT | 47.92% | 1.0 | 0.80 | BUY | None |
| ml_enhanced_FETUSDT_1d_B_lightgbm | FETUSDT | 46.41% | 1.0 | 0.80 | BUY | None |
| ml_enhanced_FETUSDT_1d_B_lightgbm | FETUSDT | 46.03% | 1.0 | 0.80 | BUY | None |
| ml_enhanced_FETUSDT_1d_B_lightgbm | FETUSDT | 45.31% | 1.0 | 0.80 | BUY | None |
| ml_enhanced_FETUSDT_1d_B_lightgbm | FETUSDT | 44.11% | 1.0 | 0.80 | BUY | None |
| ml_enhanced_FETUSDT_1d_B_lightgbm | FETUSDT | 40.23% | 1.0 | 0.80 | BUY | None |
| ml_enhanced_FETUSDT_1d_B_lightgbm | FETUSDT | 38.52% | 1.0 | 0.80 | BUY | None |
| ml_enhanced_FETUSDT_1d_B_lightgbm | FETUSDT | 38.52% | 1.0 | 0.80 | BUY | None |
| ml_enhanced_FETUSDT_1d_B_lightgbm | FETUSDT | 38.52% | 1.0 | 0.80 | BUY | None |
| ml_enhanced_FETUSDT_1d_B_lightgbm | FETUSDT | 38.52% | 1.0 | 0.80 | BUY | None |
| ml_enhanced_NEARUSDT_1d_A_xgboost | NEARUSDT | 37.95% | 1.0 | 0.60 | BUY | None |
| ml_enhanced_NEARUSDT_1h_D_ensemble_stack | NEARUSDT | 37.82% | 1.0 | 0.40 | BUY | None |
| ml_enhanced_FETUSDT_1d_B_lightgbm | FETUSDT | 36.88% | 1.0 | 0.80 | BUY | None |
| ml_enhanced_FETUSDT_1d_B_lightgbm | FETUSDT | 34.95% | 1.0 | 0.80 | BUY | None |
| ml_enhanced_RENDERUSDT_1h_D_ensemble_stack | RENDERUSDT | 34.85% | 1.0 | 0.80 | BUY | None |
| ml_enhanced_RENDERUSDT_1h_D_ensemble_stack | RENDERUSDT | 34.07% | 1.0 | 0.80 | BUY | None |
| ml_enhanced_FETUSDT_1d_B_lightgbm | FETUSDT | 33.54% | 1.0 | 0.80 | BUY | None |
| ml_enhanced_RENDERUSDT_1h_D_ensemble_stack | RENDERUSDT | 32.55% | 1.0 | 0.80 | BUY | None |
| ml_enhanced_FETUSDT_1d_B_lightgbm | FETUSDT | 30.12% | 1.0 | 0.80 | BUY | None |
| ml_enhanced_FETUSDT_1h_A_xgboost | FETUSDT | 29.96% | 1.0 | 0.60 | BUY | None |
| ml_enhanced_RENDERUSDT_4h_D_ensemble_stack | RENDERUSDT | 29.8% | 1.0 | 0.60 | BUY | None |
| ml_enhanced_ZROUSDT_1d_D_ensemble_stack | ZROUSDT | 27.72% | 1.0 | 0.40 | BUY | None |
| ml_enhanced_ZROUSDT_1h_B_lightgbm | ZROUSDT | 26.97% | 1.0 | 0.60 | BUY | None |
| ml_enhanced_DOTUSDT_1d_D_ensemble_stack | DOTUSDT | 20.8% | 1.0 | 0.40 | BUY | None |
| ml_enhanced_APTUSDT_4h_A_xgboost | APTUSDT | 20.75% | 1.0 | 0.60 | BUY | None |
| ml_enhanced_RENDERUSDT_4h_D_ensemble_stack | RENDERUSDT | 20.45% | 1.0 | 0.60 | BUY | None |
| ml_enhanced_APTUSDT_1h_B_lightgbm | APTUSDT | 20.17% | 1.0 | 0.40 | BUY | None |
| ml_enhanced_RENDERUSDT_1h_D_ensemble_stack | RENDERUSDT | 19.91% | 1.0 | 0.80 | BUY | None |
| ml_enhanced_RENDERUSDT_1h_D_ensemble_stack | RENDERUSDT | 18.92% | 1.0 | 0.80 | BUY | None |
| ml_enhanced_RENDERUSDT_4h_D_ensemble_stack | RENDERUSDT | 18.62% | 1.0 | 0.60 | BUY | None |
| ml_enhanced_AVAXUSDT_1d_A_xgboost | AVAXUSDT | 18.25% | 1.0 | 0.60 | BUY | None |
| ml_enhanced_AVAXUSDT_4h_A_xgboost | AVAXUSDT | 17.32% | 1.0 | 0.40 | BUY | None |
| ml_enhanced_ETHUSDT_1d_D_ensemble_stack | ETHUSDT | 16.4% | 1.0 | 0.40 | BUY | None |
| ml_enhanced_ATOMUSDT_4h_D_ensemble_stack | ATOMUSDT | 15.89% | 1.0 | 0.40 | SELL | None |
| ml_enhanced_ARBUSDT_1d_A_xgboost | ARBUSDT | 15.83% | 1.0 | 0.80 | BUY | None |
| ml_enhanced_ARBUSDT_1h_D_ensemble_stack | ARBUSDT | 15.71% | 1.0 | 0.40 | BUY | None |
| ml_enhanced_SUIUSDT_1d_D_ensemble_stack | SUIUSDT | 15.54% | 1.0 | 0.40 | BUY | None |
| ml_enhanced_SUIUSDT_1h_A_xgboost | SUIUSDT | 15.41% | 1.0 | 0.60 | BUY | None |
| ml_enhanced_CHZUSDT_1d_A_xgboost | CHZUSDT | 14.63% | 1.0 | 0.60 | BUY | None |
| ml_enhanced_LINKUSDT_1d_D_ensemble_stack | LINKUSDT | 11.68% | 1.0 | 0.40 | BUY | None |
| ml_enhanced_LINKUSDT_4h_A_xgboost | LINKUSDT | 11.68% | 1.0 | 0.60 | BUY | None |
| ml_enhanced_BNBUSDT_15m_B_lightgbm | BNBUSDT | 10.83% | 1.0 | 0.80 | BUY | None |
| ml_enhanced_BNBUSDT_15m_B_lightgbm | BNBUSDT | 10.83% | 1.0 | 0.80 | BUY | None |
| ml_enhanced_BNBUSDT_15m_B_lightgbm | BNBUSDT | 10.83% | 1.0 | 0.80 | BUY | None |
| ml_enhanced_BNBUSDT_15m_B_lightgbm | BNBUSDT | 10.83% | 1.0 | 0.80 | BUY | None |
| ml_enhanced_BNBUSDT_15m_B_lightgbm | BNBUSDT | 9.51% | 1.0 | 0.80 | BUY | None |
| ml_enhanced_BNBUSDT_15m_B_lightgbm | BNBUSDT | 9.43% | 1.0 | 0.80 | BUY | None |
| ml_enhanced_BTCUSDT_1h_B_lightgbm | BTCUSDT | 9.22% | 1.0 | 0.60 | BUY | None |
| ml_enhanced_RENDERUSDT_1h_D_ensemble_stack | RENDERUSDT | 9.02% | 1.0 | 0.80 | BUY | None |
| ml_enhanced_BNBUSDT_15m_B_lightgbm | BNBUSDT | 8.88% | 1.0 | 0.80 | BUY | None |
| ml_enhanced_RENDERUSDT_4h_D_ensemble_stack | RENDERUSDT | 8.77% | 1.0 | 0.60 | BUY | None |
| ml_enhanced_ALGOUSDT_4h_A_xgboost | ALGOUSDT | 8.7% | 1.0 | 0.40 | BUY | None |
| ml_enhanced_OPUSDT_1d_A_xgboost | OPUSDT | 7.52% | 1.0 | 0.60 | BUY | None |
| ml_enhanced_OPUSDT_1h_B_lightgbm | OPUSDT | 7.43% | 1.0 | 0.40 | BUY | None |
| ml_enhanced_OPUSDT_4h_D_ensemble_stack | OPUSDT | 7.35% | 1.0 | 0.40 | BUY | None |
| hl_funding_fade | KAITOUSDT | 7.22% | N/A | 0.66 | BUY | None |
| ml_enhanced_LTCUSDT_1d_B_lightgbm | LTCUSDT | 7.03% | 1.0 | 0.60 | BUY | None |
| ml_enhanced_LTCUSDT_4h_A_xgboost | LTCUSDT | 6.99% | 1.0 | 0.60 | BUY | None |
| ml_enhanced_ADAUSDT_1d_A_xgboost | ADAUSDT | 6.99% | 1.0 | 0.80 | BUY | None |
| winner_pattern_precursor | SIGNUSDT | 6.89% | 23 | 0.67 | BUY | None |
| ml_enhanced_BNBUSDT_15m_B_lightgbm | BNBUSDT | 6.43% | 1.0 | 0.80 | BUY | None |
| winner_pattern_precursor | WLFIUSDT | 6.28% | 34 | 0.67 | BUY | None |
| ml_enhanced_DOGEUSDT_4h_A_xgboost | DOGEUSDT | 6.05% | 1.0 | 0.60 | BUY | None |
| winner_pattern_precursor | COSUSDT | 5.96% | 18 | 0.67 | BUY | None |
| winner_pattern_precursor | XPLUSDT | 5.95% | 26 | 0.67 | BUY | None |
| winner_pattern_precursor | DEGOUSDT | 5.95% | 11 | 0.67 | BUY | None |
| winner_pattern_precursor | ENJUSDT | 5.95% | 29 | 0.67 | BUY | None |
| hl_momentum_continuation | XAIUSDT | 5.95% | 31 | 0.74 | BUY | None |
| winner_pattern_precursor | ETHFIUSDT | 5.95% | 11 | 0.67 | BUY | None |
| winner_pattern_precursor | DEGOUSDT | 5.95% | 6 | 0.67 | BUY | None |
| winner_pattern_precursor | ANKRUSDT | 5.95% | 14 | 0.67 | BUY | None |
| ml_enhanced_XRPUSDT_1d_D_ensemble_stack | XRPUSDT | 5.95% | 1.0 | 0.60 | BUY | None |
| binance_smart_money | LYNUSDT | 5.45% | 31 | 0.73 | BUY | None |
| binance_smart_money | WAXPUSDT | 5.45% | 34 | 0.76 | BUY | None |
| binance_smart_money | PIPPINUSDT | 5.35% | 31 | 0.73 | BUY | None |
| ml_enhanced_RENDERUSDT_1h_D_ensemble_stack | RENDERUSDT | 5.28% | 1.0 | 0.80 | BUY | None |
| ml_enhanced_RENDERUSDT_1h_D_ensemble_stack | RENDERUSDT | 5.07% | 1.0 | 0.80 | BUY | None |
| ml_enhanced_RENDERUSDT_1h_D_ensemble_stack | RENDERUSDT | 5.02% | 1.0 | 0.80 | BUY | None |
| hl_funding_fade | IPUSDT | 4.95% | 32 | 0.66 | BUY | None |
| hl_mean_reversion | ZETAUSDT | 4.95% | 39 | 0.64 | BUY | None |
| emergency_gainer_capture | ONTUSDT | 4.95% | 21 | 0.78 | BUY | None |
| emergency_gainer_capture | JTOUSDT | 4.95% | 24 | 0.66 | BUY | None |
| ml_enhanced_BNBUSDT_15m_B_lightgbm | BNBUSDT | 4.6% | 1.0 | 0.80 | BUY | None |
| ml_enhanced_BNBUSDT_15m_B_lightgbm | BNBUSDT | 4.55% | 1.0 | 0.80 | BUY | None |
| ml_enhanced_BNBUSDT_15m_B_lightgbm | BNBUSDT | 4.51% | 1.0 | 0.80 | BUY | None |
| ml_enhanced_BNBUSDT_15m_B_lightgbm | BNBUSDT | 4.45% | 1.0 | 0.80 | BUY | None |
| ml_enhanced_BNBUSDT_15m_B_lightgbm | BNBUSDT | 4.45% | 1.0 | 0.80 | BUY | None |
| binance_smart_money | SAHARAUSDT | 4.29% | 31 | 0.78 | BUY | None |
| inverse_winner_pattern_precursor_tight | KITEUSDT | 4.27% | 39 | 0.57 | SHORT | None |
| ml_enhanced_ETCUSDT_1h_D_ensemble_stack | ETCUSDT | 4.03% | 1.0 | 0.40 | BUY | None |
| ml_enhanced_RENDERUSDT_4h_D_ensemble_stack | RENDERUSDT | 3.94% | 1.0 | 0.60 | BUY | None |
| ml_enhanced_ETCUSDT_1d_D_ensemble_stack | ETCUSDT | 3.91% | 1.0 | 0.40 | BUY | None |
| ml_enhanced_RENDERUSDT_4h_D_ensemble_stack | RENDERUSDT | 3.83% | 1.0 | 0.60 | BUY | None |
| ml_enhanced_RENDERUSDT_1h_D_ensemble_stack | RENDERUSDT | 3.65% | 1.0 | 0.80 | BUY | None |
| ml_enhanced_BNBUSDT_15m_B_lightgbm | BNBUSDT | 3.1% | 1.0 | 0.80 | BUY | None |
| ml_enhanced_TRXUSDT_1d_D_ensemble_stack | TRXUSDT | 3.01% | 1.0 | 0.40 | BUY | None |

---
## PART 5: FAMILY DIVERSITY ANALYSIS

### Win Rate by Family Diversity

| Diversity | Trades | Wins | WR% | Avg PnL% | Total PnL% | p-value (>50%) | Significant? |
|-----------|--------|------|-----|----------|------------|----------------|--------------|
| 1_family | 473 | 163 | 34.5% | 1.23% | 582.4% | 1.0 | NO |
| 2_families | 15 | 4 | 26.7% | -1.46% | -21.91% | 0.982422 | NO |

### Verdict

2-family trades have 26.7% WR vs 34.5% for 1-family. This is NOT statistically significant (p=0.8168) - could be noise. Sample: 15 trades in 2-family bucket. Small sample size makes this unreliable.

- 1-family WR: 34.5%
- 2-families WR: 26.7%
- Difference: -7.8 percentage points
- p-value (2-fam > 1-fam): 0.816846
- Is this a real edge? **NO - possibly noise**
- WARNING: 2-family bucket has only 15 trades

### Strategy Families in System

momentum, sentiment, trend, volatility

---
## FINAL CONCLUSION

This analysis tested every plausible edge source using binomial tests against the null hypothesis of 50% win rate (random trading).

### The Brutal Truth

1. **The system does NOT have an aggregate edge.** 34.9% overall win rate across 493 trades is WORSE than coin-flipping. The p-value is 1.0 (certainty that we are NOT above 50%).

2. **NO asset class has a statistically significant edge.** Crypto is the best at 41.6% WR, but even that fails the binomial test (p=0.9996). Equity (4.6% WR), commodity (14.3% WR), and forex (33.3% WR) are all underwater.

3. **The edge exists in EXACTLY 4 specific ML-enhanced strategies** -- all crypto, all on specific symbols:
   - `ml_enhanced_BNBUSDT_15m_B_lightgbm`: 94.1% WR, 17 trades, p=0.00014
   - `ml_enhanced_FETUSDT_1d_B_lightgbm`: 93.8% WR, 16 trades, p=0.00026
   - `ml_enhanced_RENDERUSDT_1h_D_ensemble_stack`: 87.5% WR, 16 trades, p=0.0021
   - `copy_hl_NMTD_25M`: 81.3% WR, 16 trades, p=0.011

4. **High confidence (80%+) picks show a real edge:** 59.2% WR across 120 trades (p=0.027). This is the only broad-based filter that works.

5. **The raw PnL of +570% is misleading.** It is driven entirely by uncapped outsized winners from the ML strategies above (FETUSDT alone contributed 607%). When PnL is capped at 10% per trade, the system is -16.2% -- a net loser.

6. **The "family diversity" finding is DEAD.** In our data, 2-family trades have 26.7% WR (WORSE than 1-family at 34.5%), with only 15 samples. This is not a real edge.

7. **97 low-score winners all come from ML-enhanced strategies** that score elite_score=1 (the floor). The scorer was calibrated for classic technical strategies and completely ignores ML model confidence. These strategies need their own scoring pathway.

### Actionable Recommendations

1. **Kill non-crypto strategies immediately.** Equity (4.6% WR), commodity (14.3% WR), bond (0% WR) are pure capital destroyers.
2. **Concentrate capital on the 4 proven ML strategies** -- they are the ONLY statistically significant edge.
3. **Add a confidence gate:** Only take trades with confidence >= 0.80. This alone brings WR to 59%.
4. **Fix the elite scorer** to properly score ML-enhanced strategies instead of flooring them at 1.
5. **Kill `winner_pattern_precursor`** -- 96 trades at 17.7% WR, -91.9% total PnL. It is the single biggest capital destroyer.
6. **Kill `yahoo_analyst_consensus`** -- 55 trades at 0% WR. Literally zero wins.
7. **Do NOT rely on family diversity or consensus count** as edge filters -- they have no statistical support in our data.
