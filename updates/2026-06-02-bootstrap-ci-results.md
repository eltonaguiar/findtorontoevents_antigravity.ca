# 2026-06-02 — EAGLE-6 v2 Bootstrap CI gate: 9 PASS, 6 BORDERLINE, 4 FAIL

## TL;DR
For each of the 19 WF OOS survivors (PR #473), computed a 5000-resample bootstrap 95% CI for Profit Factor. **9 PASS** the EAGLE-6 v2 bootstrap CI gate (lower 95% > 1.0), **6 BORDERLINE, 4 FAIL**. This is the strictest of the 3 EAGLE-6 v2 gates. Top 3 forward-test candidates: `crypto_liquidity_wick_reversal_v1`, `prediction_market_consensus`, `drawdown_recovery_rsi_xrp`.

## What was generated
- `tools/build_bootstrap_ci_results.py` (new, ~140 lines) — standalone, consumes the WF OOS survivors, runs bootstrap, computes (pf_lo_95, pf_med_95, pf_hi_95)
- `tools/bootstrap_ci_results.json` (new, 401 lines) — per-strategy IS_PF, pf_lo_95, pf_med_95, pf_hi_95, verdict
- **PR #481** opened: `docs/bootstrap-ci-results-2026-06-02` branch, 2 files, all mine

## Method
- Input: 19 candidates from `tools/walkforward_oos_results.json` (18 WF OOS PASS + 1 BORDERLINE)
- Per strategy: load full `pnl_pct` series from `at_signal_outcomes` (closed outcomes only, NULL excluded, `unknown` strategy excluded)
- Bootstrap: 5000 resamples, `np.random.RandomState(seed=42)`, each resample computes `gross_profit / abs(gross_loss)` with no-losses → 0.0 sentinel (post-PR-#464)
- Verdict: **PASS if pf_lo_95 > 1.0** (the strictest of the 3 EAGLE-6 v2 gates)

## Result
**EAGLE-6 v2 Bootstrap CI gate: PASS=9, BORDERLINE=6, FAIL=4, INSUFFICIENT=0 (total=19)**

### High-conviction PASSes (high n, narrow CI, IS_PF>1)
| Strategy | Class | n | IS_PF | CI low | CI high |
|---|---|---|---|---|---|
| `crypto_liquidity_wick_reversal_v1` | CRYPTO | 4675 | 2.717 | 2.493 | 2.954 |
| `prediction_market_consensus` | CRYPTO | 619 | 2.076 | 1.699 | 2.573 |
| `drawdown_recovery_rsi_xrp` | CRYPTO | 438 | 1.886 | 1.446 | 2.504 |
| `rsi_overbought` | CRYPTO | 290 | 2.250 | 1.756 | 2.913 |
| `fx_smart_carry_trade_momentum` | FOREX | 133 | 10.696 | 6.890 | 18.755 |
| `ml_crypto_pred` | CRYPTO | 79 | 1.929 | 1.058 | 3.415 |

### Suspicious PASSes (extreme IS_PF, small n)
| Strategy | n | IS_PF | CI low | CI high |
|---|---|---|---|---|
| `B_flip_PriceRocMeanReversion` | 157 | 35.914 | 21.212 | 73.406 |
| `claude_ml_moderate_mut` | 67 | 310.772 | 1.313 | 1177.173 |
| `inverse_ml_enhanced_BTCUSDT_15m_D` | 64 | 34.459 | 15.974 | 128.757 |

These have IS_PF in [30, 310] which is implausibly high — either lucky regime, look-ahead bias, or PnL accounting artifact.

### BORDERLINE (median > 1.0, but worst-case CI ≤ 1.0)
- `ensemble` (CRYPTO + MEMECOIN), `luxalgo_confluence` (CRYPTO), `regime_mild_bull` (ETF), `quan_engine_swing`, `cvd_divergence`

### FAIL
- `macd_crossover` (CRYPTO + MEMECOIN, IS_PF=0.797) — actually unprofitable
- `reddit:Gr33nHatt3R`, `rsi_vwap_contrarian`

## Three-gate summary
| Gate | Result | Threshold | PR |
|---|---|---|---|
| PBO (portfolio-level) | PBO=1.0 FAIL | < 0.5 | #471 |
| WF OOS (per-strategy robustness) | 18 PASS | OOS_PF ≥ 0.8 × IS_PF, n_folds≥3 | #473 |
| Bootstrap CI (per-strat statistical) | 9 PASS | pf_lo_95 > 1.0 | #481 |

## Forward-test recommendation
**Top 3 forward-test candidates** (PF CI > 1.0 with high n, IS_PF reasonable):
1. `crypto_liquidity_wick_reversal_v1` — n=4675, IS_PF=2.72, CI=[2.49, 2.95] ← **best**
2. `prediction_market_consensus` — n=619, IS_PF=2.08, CI=[1.70, 2.57]
3. `drawdown_recovery_rsi_xrp` — n=438, IS_PF=1.89, CI=[1.45, 2.50]

## Refs
- `ENHANCEMENT_OVERALL #85` (EAGLE-6 v2 PBO + WF OOS + bootstrap CI gate)
- PR #456 (EAGLE-6 v1 plan), PR #471 (PBO=1.0), PR #473 (WF OOS 18 PASS), this PR (#481)

## Reproduce
```bash
DB_PASS_STOCKS=stocks1234560 python3 tools/build_walkforward_oos_results.py  # first, populates WF OOS
DB_PASS_STOCKS=stocks1234560 python3 tools/build_bootstrap_ci_results.py     # then this
# -> PASS=9 BORDERLINE=6 FAIL=4 INSUFFICIENT=0 -> tools/bootstrap_ci_results.json
```

## Action items
- [ ] Update `ENHANCEMENT_OVERALL #85` with bootstrap CI result: 9 PASS, including the strict 3-gate intersection.
- [ ] Forward-test top 3 candidates (`crypto_liquidity_wick_reversal_v1`, `prediction_market_consensus`, `drawdown_recovery_rsi_xrp`) for 2 weeks.
- [ ] Investigate the 3 suspicious PASSes (IS_PF > 30): look-ahead bias or PnL accounting bug?
- [ ] Re-examine ensemble (CRYPTO + MEMECOIN) — same strategy, two asset classes with same numbers means the rows are duplicated.
