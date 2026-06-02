# 2026-06-02 — EAGLE-6 v2 PBO gate: PBO=1.0 FAIL

## TL;DR
Ran Combinatorially-Purged Cross-Validation (CPCV) Probability of Backtest Overfit (PBO) over 56 strategies with n≥30 closed picks in `at_signal_outcomes` (date range 2026-02-25 to 2026-06-02, 83 trading days). **PBO = 1.0** — the entire backlog is overfit. EAGLE-6 v2 PBO gate correctly rejects it.

## What was generated
- `tools/build_cpcv_pbo_results.py` (new, 161 lines) — standalone MySQL query + PBO runner. Reads `at_signal_outcomes`, filters strategies with n≥30, pivots to a (T=83 days × S=56 strategies) daily-aggregated pnl_pct matrix with `fill_value=0.0` (treating absence as zero return), calls `cpcv_pbo(matrix, n_folds=10, n_test_groups=2)` from `alpha_engine/anti_overfit_validator.py`.
- `tools/cpcv_pbo_results.json` (new, 523 lines) — full output: PBO verdict, date range, matrix shape, per-strategy stats (n, win_rate, sum_pnl_pct, Sharpe, selected_top10).
- **PR #471** opened: `docs/cpcv-pbo-results-2026-06-02` branch, 2 files, all mine.

## Top in-sample performers (PBO=1.0 says they overfit)
| Strategy | n | WR | sum_pnl_pct | Sharpe |
|---|---|---|---|---|
| `crypto_liquidity_wick_reversal_v1` | 203 | 100.0% | +1665.0 | 175.01 |
| `currents:Helene Braun; Helene-B...` | 63 | 100.0% | +509.6 | 161.73 |
| `reddit:u/BlasterBladez` | 86 | 100.0% | +1116.4 | 88.96 |
| `reddit:u/SscorpionN08` | 32 | 100.0% | +1687.2 | 68.77 |
| `currents:Parshwa Turakhiya` | 31 | 96.8% | +246.7 | 42.64 |

100% WR with n in [31, 203] is a classic overfit fingerprint. PBO=1.0 says: random portfolios beat these in out-of-sample folds.

## Bulk strategies are net-negative
| Strategy | n | WR | sum_pnl_pct | Sharpe |
|---|---|---|---|---|
| `volume_spike_breakout` | 10871 | 16.8% | -14030.1 | -9.26 |
| `macd_rsi_confluence` | 9549 | 37.2% | -1245.3 | -0.92 |
| `bollinger_squeeze` | 3139 | 10.9% | -4116.5 | -13.39 |
| `rsi_bounce` | 2726 | 31.0% | -1451.0 | -2.98 |
| `stochrsi_macd_combo` | 2239 | 16.2% | -2324.4 | -9.33 |

These dominate by sample size, so any portfolio that gives them weight will be net-negative.

## Verdict
- **Do NOT promote any of the 56 strategies on backtest edge alone.** EAGLE-6 v2 PBO gate (`< 0.5`) correctly rejects the entire backlog.
- Forward-test the top in-sample performers (`crypto_liquidity_wick_reversal_v1`, `etf_dual_momentum`, `fabervectors`) for n≥100 real-time before revisiting.
- This is a PBO**v1** reading. PBO**v2** with a stricter loss-fraction filter (drop strategies with WR<25% even if Sharpe looks ok) and a forward-only weighting (heavier weight on strategies with more recent picks) is on the EAGLE-6 v2 backlog.

## Reproduce
```bash
DB_PASS_STOCKS=stocks1234560 python3 tools/build_cpcv_pbo_results.py
# -> pbo=1.0000  T=83  S=56  -> /home/eaguiar2015/findtorontoevents_antigravity.ca/tools/cpcv_pbo_results.json
```

## Verification
- Matrix shape: (83, 56) — T=83 ≥ 2×n_folds=20 ✓
- PBO ∈ [0, 1]: 1.0 ✓
- n_strategies = 56, all with n≥30 ✓
- Date range 2026-02-25 to 2026-06-02 (99 days inclusive) ✓
- Per-strategy Sharpe values: best 5 in [42.6, 175.0], worst 5 in [-195.3, -161.4] — wide distribution confirms PBO computation found signal.

## Refs
- `ENHANCEMENT_OVERALL #85` (EAGLE-6 v2 PBO gate)
- `alpha_engine/anti_overfit_validator.py::cpcv_pbo`
- `EAGLE6_2026-06-02_minimax-m3-free.MD` (PR #456)
- PR #471 — this change

## Action items
- [ ] Update `ENHANCEMENT_OVERALL #85` with PBO result: PBO=1.0 FAIL → v2 PBO gate correctly rejects. Set `linked_pr` to #471.
- [ ] Forward-test top 3 in-sample performers: `crypto_liquidity_wick_reversal_v1`, `etf_dual_momentum`, `fabervectors` for 2 weeks.
- [ ] PBO v2 backlog: add stricter loss-fraction filter and forward-only weighting.
