# White's Reality Check / SPA Test — 2026-05-18

**Strategies tested:** 37
**Bootstrap iterations:** 1000
**Significance level (α):** 0.05

**White's RC family-wise p-value:** 0.0
**Hansen's SPA family-wise p-value:** 0.0
**Family-wide edge survives:** YES
**Strategies passing SPA:** 16 / 37

**Summary:** 37 strategies tested, 16 pass SPA (p≤0.05). White's RC p=0.000, SPA p=0.000. Family-wide edge SURVIVES correction.

---

## Per-Strategy Results

Strategy                                           n   MeanRet%   p_marg    SPA
--------------------------------------------------------------------------------
ml_enhanced_FETUSDT_1d_B_lightgbm                 25    34.3689   0.0000 [PASS]
ml_enhanced_INJUSDT_1d_B_lightgbm                 27    15.7071   0.0000 [PASS]
ml_enhanced_RENDERUSDT_1h_D_ensemble_stack        34     5.0428   0.0000 [PASS]
ml_enhanced_BNBUSDT_15m_B_lightgbm                19     4.7693   0.0000 [PASS]
ml_enhanced_POLUSDT_1d_B_lightgbm                 13     3.8433   0.0000 [PASS]
ml_enhanced_RENDERUSDT_4h_D_ensemble_stack        27     3.6819   0.0000 [PASS]
ml_enhanced_XRPUSDT_1d_D_ensemble_stack           17     3.5284   0.0000 [PASS]
cot_positioning                                  134     3.2765   0.0000 [PASS]
cftc_cot_commercial_signal                       131     2.9709   0.0000 [PASS]
macd_crossover                                    10     2.7229   0.0000 [PASS]
ml_enhanced_DYDXUSDT_15m_D_ensemble_stack         31     1.8465   0.0000 [PASS]
ml_enhanced_HBARUSDT_1d_D_ensemble_stack          12     1.5356   0.0000 [PASS]
ml_enhanced_AVAXUSDT_1d_B_lightgbm                11     1.4677   0.0000 [PASS]
ml_enhanced_JTOUSDT_1d_B_lightgbm                 13     0.9104   0.0730 [FAIL]
ml_enhanced_STRKUSDT_15m_D_ensemble_stack         29     0.8217   0.0000 [PASS]
ml_enhanced_FETUSDT_15m_B_lightgbm                25     0.4622   0.0220 [PASS]
fx_smart_forex_rsi2_mean_reversion                11     0.1756   0.0000 [PASS]
ml_enhanced_ADAUSDT_15m_B_lightgbm                26     0.0814   0.2730 [FAIL]
ml_enhanced_TONUSDT_4h_D_ensemble_stack           19     0.0288   0.4170 [FAIL]
stocks_rsi2_pullback                              37     0.0271   0.4750 [FAIL]
ml_enhanced_DOGEUSDT_15m_D_ensemble_stack         23    -0.0184   0.5670 [FAIL]
fx_smart_carry_trade_momentum                     28    -0.0720   0.9910 [FAIL]
ig_contrarian_sentiment                          254    -0.1775   1.0000 [FAIL]
forex_rsi2_mean_reversion                        131    -0.3856   1.0000 [FAIL]
forex_carry_momentum                             178    -0.4065   1.0000 [FAIL]
myfxbook_retail_contrarian                       137    -0.4343   1.0000 [FAIL]
cta_cross_asset_tsmom                            248    -0.5705   1.0000 [FAIL]
ml_enhanced_AVAXUSDT_15m_D_ensemble_stack         23    -0.5861   1.0000 [FAIL]
ml_enhanced_INJUSDT_15m_D_ensemble_stack          26    -0.7564   1.0000 [FAIL]
combined_confidence                               19    -0.8585   1.0000 [FAIL]
ml_enhanced_ALGOUSDT_15m_B_lightgbm               21    -1.1400   1.0000 [FAIL]
futures_momentum                                 202    -2.8426   1.0000 [FAIL]
cta_commodity_momentum_term                       11    -3.5565   1.0000 [FAIL]
ml_enhanced_BTCUSDT_15m_D_ensemble_stack          12    -6.4941   1.0000 [FAIL]
ml_enhanced_ADAUSDT_15m_D_ensemble_stack          12    -9.7140   1.0000 [FAIL]
ml_enhanced_APEUSDT_1d_D_ensemble_stack           22   -40.3816   1.0000 [FAIL]
ml_enhanced_TRXUSDT_1d_B_lightgbm                 24   -70.5574   1.0000 [FAIL]

## SPA-Passing Strategies (genuine edge, family-corrected)
- `ml_enhanced_FETUSDT_1d_B_lightgbm` — mean +34.3689%/pick, p=0.0000, n=25
- `ml_enhanced_INJUSDT_1d_B_lightgbm` — mean +15.7071%/pick, p=0.0000, n=27
- `ml_enhanced_RENDERUSDT_1h_D_ensemble_stack` — mean +5.0428%/pick, p=0.0000, n=34
- `ml_enhanced_BNBUSDT_15m_B_lightgbm` — mean +4.7693%/pick, p=0.0000, n=19
- `ml_enhanced_POLUSDT_1d_B_lightgbm` — mean +3.8433%/pick, p=0.0000, n=13
- `ml_enhanced_RENDERUSDT_4h_D_ensemble_stack` — mean +3.6819%/pick, p=0.0000, n=27
- `ml_enhanced_XRPUSDT_1d_D_ensemble_stack` — mean +3.5284%/pick, p=0.0000, n=17
- `cot_positioning` — mean +3.2765%/pick, p=0.0000, n=134
- `cftc_cot_commercial_signal` — mean +2.9709%/pick, p=0.0000, n=131
- `macd_crossover` — mean +2.7229%/pick, p=0.0000, n=10
- `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack` — mean +1.8465%/pick, p=0.0000, n=31
- `ml_enhanced_HBARUSDT_1d_D_ensemble_stack` — mean +1.5356%/pick, p=0.0000, n=12
- `ml_enhanced_AVAXUSDT_1d_B_lightgbm` — mean +1.4677%/pick, p=0.0000, n=11
- `ml_enhanced_STRKUSDT_15m_D_ensemble_stack` — mean +0.8217%/pick, p=0.0000, n=29
- `ml_enhanced_FETUSDT_15m_B_lightgbm` — mean +0.4622%/pick, p=0.0220, n=25
- `fx_smart_forex_rsi2_mean_reversion` — mean +0.1756%/pick, p=0.0000, n=11


## Failed Strategies (edge not distinguishable from data snooping)
- `ml_enhanced_JTOUSDT_1d_B_lightgbm` — mean +0.9104%/pick, p=0.0730, n=13
- `ml_enhanced_ADAUSDT_15m_B_lightgbm` — mean +0.0814%/pick, p=0.2730, n=26
- `ml_enhanced_TONUSDT_4h_D_ensemble_stack` — mean +0.0288%/pick, p=0.4170, n=19
- `stocks_rsi2_pullback` — mean +0.0271%/pick, p=0.4750, n=37
- `ml_enhanced_DOGEUSDT_15m_D_ensemble_stack` — mean -0.0184%/pick, p=0.5670, n=23
- `fx_smart_carry_trade_momentum` — mean -0.0720%/pick, p=0.9910, n=28
- `ig_contrarian_sentiment` — mean -0.1775%/pick, p=1.0000, n=254
- `forex_rsi2_mean_reversion` — mean -0.3856%/pick, p=1.0000, n=131
- `forex_carry_momentum` — mean -0.4065%/pick, p=1.0000, n=178
- `myfxbook_retail_contrarian` — mean -0.4343%/pick, p=1.0000, n=137
- `cta_cross_asset_tsmom` — mean -0.5705%/pick, p=1.0000, n=248
- `ml_enhanced_AVAXUSDT_15m_D_ensemble_stack` — mean -0.5861%/pick, p=1.0000, n=23
- `ml_enhanced_INJUSDT_15m_D_ensemble_stack` — mean -0.7564%/pick, p=1.0000, n=26
- `combined_confidence` — mean -0.8585%/pick, p=1.0000, n=19
- `ml_enhanced_ALGOUSDT_15m_B_lightgbm` — mean -1.1400%/pick, p=1.0000, n=21
- `futures_momentum` — mean -2.8426%/pick, p=1.0000, n=202
- `cta_commodity_momentum_term` — mean -3.5565%/pick, p=1.0000, n=11
- `ml_enhanced_BTCUSDT_15m_D_ensemble_stack` — mean -6.4941%/pick, p=1.0000, n=12
- `ml_enhanced_ADAUSDT_15m_D_ensemble_stack` — mean -9.7140%/pick, p=1.0000, n=12
- `ml_enhanced_APEUSDT_1d_D_ensemble_stack` — mean -40.3816%/pick, p=1.0000, n=22
  ... and 1 more

## Interpretation
- **SPA p-value ≤ α**: at least one strategy has genuine edge beyond data snooping.
- **Per-strategy p_marginal**: marginal evidence for that strategy's edge (not family-corrected).
- **Strategies with spa_passes=False but positive mean**: edge may be real but inflated by
  selection bias across the full strategy set. Require more data or independent OOS validation.
- This test does NOT replace per-strategy DSR (alpha_engine/deflated_sharpe.py) or
  PBO/CSCV (tools/pbo_cscv.py). It adds family-wise correction on top.
