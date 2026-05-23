# White's Reality Check / SPA Test — 2026-05-17

**Strategies tested:** 24
**Bootstrap iterations:** 500
**Significance level (α):** 0.05

**White's RC family-wise p-value:** 0.0
**Hansen's SPA family-wise p-value:** 0.0
**Family-wide edge survives:** YES
**Strategies passing SPA:** 9 / 24

**Summary:** 24 strategies tested, 9 pass SPA (p≤0.05). White's RC p=0.000, SPA p=0.000. Family-wide edge SURVIVES correction.

---

## Per-Strategy Results

Strategy                                           n   MeanRet%   p_marg    SPA
--------------------------------------------------------------------------------
ml_enhanced_FETUSDT_1d_B_lightgbm                 25    33.6628   0.0000 [PASS]
ml_enhanced_INJUSDT_1d_B_lightgbm                 27    15.6002   0.0000 [PASS]
ml_enhanced_RENDERUSDT_1h_D_ensemble_stack        34     4.7386   0.0000 [PASS]
ml_enhanced_RENDERUSDT_4h_D_ensemble_stack        27     3.4140   0.0000 [PASS]
cot_positioning                                  134     3.2765   0.0000 [PASS]
cftc_cot_commercial_signal                       131     2.9709   0.0000 [PASS]
ml_enhanced_DYDXUSDT_15m_D_ensemble_stack         31     1.7851   0.0000 [PASS]
ml_enhanced_STRKUSDT_15m_D_ensemble_stack         29     0.9673   0.0000 [PASS]
ml_enhanced_FETUSDT_15m_B_lightgbm                25     0.8609   0.0000 [PASS]
stocks_rsi2_pullback                              37     0.0840   0.3760 [FAIL]
ml_enhanced_ADAUSDT_15m_B_lightgbm                26    -0.0846   0.7640 [FAIL]
fx_smart_carry_trade_momentum                     28    -0.0890   1.0000 [FAIL]
ig_contrarian_sentiment                          254    -0.1775   1.0000 [FAIL]
ml_enhanced_DOGEUSDT_15m_D_ensemble_stack         23    -0.2229   0.9900 [FAIL]
forex_rsi2_mean_reversion                        131    -0.3525   1.0000 [FAIL]
forex_carry_momentum                             178    -0.4107   1.0000 [FAIL]
myfxbook_retail_contrarian                       137    -0.4367   1.0000 [FAIL]
cta_cross_asset_tsmom                            248    -0.4957   1.0000 [FAIL]
ml_enhanced_AVAXUSDT_15m_D_ensemble_stack         23    -0.5045   1.0000 [FAIL]
ml_enhanced_INJUSDT_15m_D_ensemble_stack          26    -0.7502   1.0000 [FAIL]
ml_enhanced_ALGOUSDT_15m_B_lightgbm               21    -0.8034   0.9960 [FAIL]
futures_momentum                                 202    -2.8026   1.0000 [FAIL]
ml_enhanced_APEUSDT_1d_D_ensemble_stack           22   -34.2349   1.0000 [FAIL]
ml_enhanced_TRXUSDT_1d_B_lightgbm                 24   -67.7245   1.0000 [FAIL]

## SPA-Passing Strategies (genuine edge, family-corrected)
- `ml_enhanced_FETUSDT_1d_B_lightgbm` — mean +33.6628%/pick, p=0.0000, n=25
- `ml_enhanced_INJUSDT_1d_B_lightgbm` — mean +15.6002%/pick, p=0.0000, n=27
- `ml_enhanced_RENDERUSDT_1h_D_ensemble_stack` — mean +4.7386%/pick, p=0.0000, n=34
- `ml_enhanced_RENDERUSDT_4h_D_ensemble_stack` — mean +3.4140%/pick, p=0.0000, n=27
- `cot_positioning` — mean +3.2765%/pick, p=0.0000, n=134
- `cftc_cot_commercial_signal` — mean +2.9709%/pick, p=0.0000, n=131
- `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack` — mean +1.7851%/pick, p=0.0000, n=31
- `ml_enhanced_STRKUSDT_15m_D_ensemble_stack` — mean +0.9673%/pick, p=0.0000, n=29
- `ml_enhanced_FETUSDT_15m_B_lightgbm` — mean +0.8609%/pick, p=0.0000, n=25


## Failed Strategies (edge not distinguishable from data snooping)
- `stocks_rsi2_pullback` — mean +0.0840%/pick, p=0.3760, n=37
- `ml_enhanced_ADAUSDT_15m_B_lightgbm` — mean -0.0846%/pick, p=0.7640, n=26
- `fx_smart_carry_trade_momentum` — mean -0.0890%/pick, p=1.0000, n=28
- `ig_contrarian_sentiment` — mean -0.1775%/pick, p=1.0000, n=254
- `ml_enhanced_DOGEUSDT_15m_D_ensemble_stack` — mean -0.2229%/pick, p=0.9900, n=23
- `forex_rsi2_mean_reversion` — mean -0.3525%/pick, p=1.0000, n=131
- `forex_carry_momentum` — mean -0.4107%/pick, p=1.0000, n=178
- `myfxbook_retail_contrarian` — mean -0.4367%/pick, p=1.0000, n=137
- `cta_cross_asset_tsmom` — mean -0.4957%/pick, p=1.0000, n=248
- `ml_enhanced_AVAXUSDT_15m_D_ensemble_stack` — mean -0.5045%/pick, p=1.0000, n=23
- `ml_enhanced_INJUSDT_15m_D_ensemble_stack` — mean -0.7502%/pick, p=1.0000, n=26
- `ml_enhanced_ALGOUSDT_15m_B_lightgbm` — mean -0.8034%/pick, p=0.9960, n=21
- `futures_momentum` — mean -2.8026%/pick, p=1.0000, n=202
- `ml_enhanced_APEUSDT_1d_D_ensemble_stack` — mean -34.2349%/pick, p=1.0000, n=22
- `ml_enhanced_TRXUSDT_1d_B_lightgbm` — mean -67.7245%/pick, p=1.0000, n=24


## Interpretation
- **SPA p-value ≤ α**: at least one strategy has genuine edge beyond data snooping.
- **Per-strategy p_marginal**: marginal evidence for that strategy's edge (not family-corrected).
- **Strategies with spa_passes=False but positive mean**: edge may be real but inflated by
  selection bias across the full strategy set. Require more data or independent OOS validation.
- This test does NOT replace per-strategy DSR (alpha_engine/deflated_sharpe.py) or
  PBO/CSCV (tools/pbo_cscv.py). It adds family-wise correction on top.
