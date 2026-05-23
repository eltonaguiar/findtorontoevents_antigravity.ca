# White's Reality Check / SPA Test — 2026-05-18

**Strategies tested:** 36
**Bootstrap iterations:** 1000
**Significance level (α):** 0.05

**White's RC family-wise p-value:** 0.0
**Hansen's SPA family-wise p-value:** 0.0
**Family-wide edge survives:** YES
**Strategies passing SPA:** 16 / 36

**Summary:** 36 strategies tested, 16 pass SPA (p≤0.05). White's RC p=0.000, SPA p=0.000. Family-wide edge SURVIVES correction.

---

## Per-Strategy Results

Strategy                                           n   MeanRet%   p_marg    SPA
--------------------------------------------------------------------------------
ml_enhanced_FETUSDT_1d_B_lightgbm                 25    32.4954   0.0000 [PASS]
ml_enhanced_INJUSDT_1d_B_lightgbm                 27    15.8464   0.0000 [PASS]
ml_enhanced_RENDERUSDT_1h_D_ensemble_stack        34     5.5521   0.0000 [PASS]
ml_enhanced_BNBUSDT_15m_B_lightgbm                19     4.9575   0.0000 [PASS]
ml_enhanced_POLUSDT_1d_B_lightgbm                 13     3.8684   0.0000 [PASS]
ml_enhanced_XRPUSDT_1d_D_ensemble_stack           17     3.5546   0.0000 [PASS]
macd_crossover                                    10     2.6366   0.0000 [PASS]
ml_enhanced_RENDERUSDT_4h_D_ensemble_stack        27     2.6169   0.0000 [PASS]
cftc_cot_commercial_signal                        48     2.4327   0.0000 [PASS]
ml_enhanced_DYDXUSDT_15m_D_ensemble_stack         31     1.8114   0.0000 [PASS]
ml_enhanced_HBARUSDT_1d_D_ensemble_stack          12     1.5041   0.0000 [PASS]
cot_positioning                                   54     1.4404   0.0000 [PASS]
ml_enhanced_AVAXUSDT_1d_B_lightgbm                11     1.4399   0.0000 [PASS]
ml_enhanced_JTOUSDT_1d_B_lightgbm                 13     1.0153   0.1180 [FAIL]
ml_enhanced_STRKUSDT_15m_D_ensemble_stack         29     0.9770   0.0000 [PASS]
ml_enhanced_FETUSDT_15m_B_lightgbm                25     0.7848   0.0000 [PASS]
fx_smart_forex_rsi2_mean_reversion                11     0.2281   0.0000 [PASS]
ml_enhanced_TONUSDT_4h_D_ensemble_stack           19     0.2159   0.2430 [FAIL]
fx_smart_carry_trade_momentum                     28    -0.1062   0.9980 [FAIL]
ml_enhanced_DOGEUSDT_15m_D_ensemble_stack         23    -0.1250   0.8150 [FAIL]
ml_enhanced_ADAUSDT_15m_B_lightgbm                26    -0.1506   0.8140 [FAIL]
forex_rsi2_mean_reversion                        106    -0.3309   1.0000 [FAIL]
ig_contrarian_sentiment                          158    -0.3360   1.0000 [FAIL]
ml_enhanced_AVAXUSDT_15m_D_ensemble_stack         23    -0.4383   0.9970 [FAIL]
myfxbook_retail_contrarian                       100    -0.4550   1.0000 [FAIL]
forex_carry_momentum                             117    -0.5000   1.0000 [FAIL]
combined_confidence                               17    -0.6231   1.0000 [FAIL]
cta_cross_asset_tsmom                            160    -0.6263   1.0000 [FAIL]
stocks_rsi2_pullback                              27    -0.7199   0.9970 [FAIL]
ml_enhanced_INJUSDT_15m_D_ensemble_stack          26    -0.7289   1.0000 [FAIL]
ml_enhanced_ALGOUSDT_15m_B_lightgbm               21    -1.8965   1.0000 [FAIL]
futures_momentum                                 114    -2.6161   1.0000 [FAIL]
ml_enhanced_BTCUSDT_15m_D_ensemble_stack          12    -6.4201   1.0000 [FAIL]
ml_enhanced_ADAUSDT_15m_D_ensemble_stack          12    -9.0171   1.0000 [FAIL]
ml_enhanced_APEUSDT_1d_D_ensemble_stack           22   -38.6181   1.0000 [FAIL]
ml_enhanced_TRXUSDT_1d_B_lightgbm                 24   -70.8346   1.0000 [FAIL]

## SPA-Passing Strategies (genuine edge, family-corrected)
- `ml_enhanced_FETUSDT_1d_B_lightgbm` — mean +32.4954%/pick, p=0.0000, n=25
- `ml_enhanced_INJUSDT_1d_B_lightgbm` — mean +15.8464%/pick, p=0.0000, n=27
- `ml_enhanced_RENDERUSDT_1h_D_ensemble_stack` — mean +5.5521%/pick, p=0.0000, n=34
- `ml_enhanced_BNBUSDT_15m_B_lightgbm` — mean +4.9575%/pick, p=0.0000, n=19
- `ml_enhanced_POLUSDT_1d_B_lightgbm` — mean +3.8684%/pick, p=0.0000, n=13
- `ml_enhanced_XRPUSDT_1d_D_ensemble_stack` — mean +3.5546%/pick, p=0.0000, n=17
- `macd_crossover` — mean +2.6366%/pick, p=0.0000, n=10
- `ml_enhanced_RENDERUSDT_4h_D_ensemble_stack` — mean +2.6169%/pick, p=0.0000, n=27
- `cftc_cot_commercial_signal` — mean +2.4327%/pick, p=0.0000, n=48
- `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack` — mean +1.8114%/pick, p=0.0000, n=31
- `ml_enhanced_HBARUSDT_1d_D_ensemble_stack` — mean +1.5041%/pick, p=0.0000, n=12
- `cot_positioning` — mean +1.4404%/pick, p=0.0000, n=54
- `ml_enhanced_AVAXUSDT_1d_B_lightgbm` — mean +1.4399%/pick, p=0.0000, n=11
- `ml_enhanced_STRKUSDT_15m_D_ensemble_stack` — mean +0.9770%/pick, p=0.0000, n=29
- `ml_enhanced_FETUSDT_15m_B_lightgbm` — mean +0.7848%/pick, p=0.0000, n=25
- `fx_smart_forex_rsi2_mean_reversion` — mean +0.2281%/pick, p=0.0000, n=11


## Failed Strategies (edge not distinguishable from data snooping)
- `ml_enhanced_JTOUSDT_1d_B_lightgbm` — mean +1.0153%/pick, p=0.1180, n=13
- `ml_enhanced_TONUSDT_4h_D_ensemble_stack` — mean +0.2159%/pick, p=0.2430, n=19
- `fx_smart_carry_trade_momentum` — mean -0.1062%/pick, p=0.9980, n=28
- `ml_enhanced_DOGEUSDT_15m_D_ensemble_stack` — mean -0.1250%/pick, p=0.8150, n=23
- `ml_enhanced_ADAUSDT_15m_B_lightgbm` — mean -0.1506%/pick, p=0.8140, n=26
- `forex_rsi2_mean_reversion` — mean -0.3309%/pick, p=1.0000, n=106
- `ig_contrarian_sentiment` — mean -0.3360%/pick, p=1.0000, n=158
- `ml_enhanced_AVAXUSDT_15m_D_ensemble_stack` — mean -0.4383%/pick, p=0.9970, n=23
- `myfxbook_retail_contrarian` — mean -0.4550%/pick, p=1.0000, n=100
- `forex_carry_momentum` — mean -0.5000%/pick, p=1.0000, n=117
- `combined_confidence` — mean -0.6231%/pick, p=1.0000, n=17
- `cta_cross_asset_tsmom` — mean -0.6263%/pick, p=1.0000, n=160
- `stocks_rsi2_pullback` — mean -0.7199%/pick, p=0.9970, n=27
- `ml_enhanced_INJUSDT_15m_D_ensemble_stack` — mean -0.7289%/pick, p=1.0000, n=26
- `ml_enhanced_ALGOUSDT_15m_B_lightgbm` — mean -1.8965%/pick, p=1.0000, n=21
- `futures_momentum` — mean -2.6161%/pick, p=1.0000, n=114
- `ml_enhanced_BTCUSDT_15m_D_ensemble_stack` — mean -6.4201%/pick, p=1.0000, n=12
- `ml_enhanced_ADAUSDT_15m_D_ensemble_stack` — mean -9.0171%/pick, p=1.0000, n=12
- `ml_enhanced_APEUSDT_1d_D_ensemble_stack` — mean -38.6181%/pick, p=1.0000, n=22
- `ml_enhanced_TRXUSDT_1d_B_lightgbm` — mean -70.8346%/pick, p=1.0000, n=24


## Interpretation
- **SPA p-value ≤ α**: at least one strategy has genuine edge beyond data snooping.
- **Per-strategy p_marginal**: marginal evidence for that strategy's edge (not family-corrected).
- **Strategies with spa_passes=False but positive mean**: edge may be real but inflated by
  selection bias across the full strategy set. Require more data or independent OOS validation.
- This test does NOT replace per-strategy DSR (alpha_engine/deflated_sharpe.py) or
  PBO/CSCV (tools/pbo_cscv.py). It adds family-wise correction on top.
