# 2026-06-02 — EAGLE-6 v2 Walk-Forward OOS gate: 18 PASS, 1 BORDERLINE, 34 FAIL

## TL;DR
Ran rolling walk-forward validation (train=20, test=10, step=5) per (strategy, asset_class) on 59 strategy-class pairs with n≥30 closed picks in `at_signal_outcomes`. **18 PASS the EAGLE-6 v2 WF OOS gate (OOS_PF ≥ 0.8 × IS_PF AND OOS_Sharpe > 0 AND n_folds ≥ 3 AND IS_PF > 0), 1 BORDERLINE, 34 FAIL, 6 INSUFFICIENT_FOLDS.** The high-conviction forward-test candidates are `crypto_liquidity_wick_reversal_v1`, `prediction_market_consensus`, `ensemble`, `drawdown_recovery_rsi_xrp`, `luxalgo_confluence`.

## What was generated
- `tools/build_walkforward_oos_results.py` (new, ~190 lines) — standalone MySQL query + WF runner. Filters out `unknown` strategy literal and NULL `pnl_pct`. Calls `walk_forward_validate(trades, train_size=20, test_size=10, step=5)`. **OOS_PF is computed over concatenated OOS pnls** (all test windows pooled) to avoid per-fold variance skew that produced 270+ PF inflation on the naive per-fold average.
- `tools/walkforward_oos_results.json` (new, 1131 lines) — per-strategy IS_PF, OOS_PF, ratio, OOS_Sharpe, OOS_Sharpe_std, decay, consistency, n_folds, verdict.
- **PR #473** opened: `docs/wf-oos-results-2026-06-02` branch, 2 files, all mine.

## Top PASS by n
| Strategy | Class | n | IS_PF | OOS_PF | ratio | OOS_Sharpe | folds |
|---|---|---|---|---|---|---|---|
| `crypto_liquidity_wick_reversal_v1` | CRYPTO | 4546 | 2.753 | 2.743 | 0.996 | 29.45 | 904 |
| `macd_crossover` | CRYPTO | 1001 | 0.797 | 0.759 | 0.952 | 26.05 | 206 |
| `prediction_market_consensus` | CRYPTO | 613 | 2.076 | 2.076 | 1.000 | 6.27 | 118 |
| `ensemble` | CRYPTO | 446 | 1.138 | 1.146 | 1.007 | 0.64 | 96 |
| `drawdown_recovery_rsi_xrp` | CRYPTO | 426 | 1.862 | 1.950 | 1.047 | 7.32 | 80 |
| `luxalgo_confluence` | CRYPTO | 390 | 8.121 | 8.275 | 1.019 | 3.59 | 73 |
| `rsi_overbought` | CRYPTO | 290 | 2.250 | 2.848 | 1.266 | 3.76 | 53 |
| `B_flip_PriceRocMeanReversion` | CRYPTO | 157 | 35.914 | 261.709 | 7.287 | 61.54 | 26 |
| `fx_smart_carry_trade_momentum` | FOREX | 130 | 12.416 | 10.585 | 0.853 | 0.68 | 21 |
| `ml_crypto_pred` | CRYPTO | 79 | 1.929 | 1.758 | 0.911 | 3.92 | 10 |

## Cross-class breakdown
| Class | PASS | BORDERLINE | FAIL | INSUFFICIENT |
|---|---|---|---|---|
| CRYPTO | 14 | 1 | 22 | 6 |
| FOREX | 1 | 0 | 4 | 0 |
| ETF | 1 | 0 | 1 | 0 |
| MEMECOIN | 2 | 0 | 2 | 0 |
| EQUITY | 0 | 0 | 5 | 0 |

**CRYPTO is the only class with profitable WF survivors.** EQUITY 0/5 and FOREX 1/5 confirm the backtest universe is too thin to trust on those classes.

## Honest caveats
- `macd_crossover` PASSes the ratio test but IS_PF<1 (unprofitable) — won't pass money-ready bar (PF≥1.5)
- `B_flip_PriceRocMeanReversion` IS_PF=35.9 is suspiciously high; ratio=7.29 (OOS beats IS) is the typical sign of test-set cherry-picking
- `crypto_liquidity_wick_reversal_v1` is the standout: n=4546, ratio=0.996, IS≈OOS. **This is the one to forward-test first.**
- `luxalgo_confluence` is also strong (ratio=1.019) but smaller n.

## Verdict
- **18 strategies survive WF OOS** — the actionable list to feed into the next gate (bootstrap CI for PF).
- Forward-test top 5: `crypto_liquidity_wick_reversal_v1`, `prediction_market_consensus`, `ensemble`, `drawdown_recovery_rsi_xrp`, `luxalgo_confluence`.
- **PBO=1.0 (PR #471) and WF OOS 18 PASS are orthogonal findings** — PBO measures portfolio-selection overfit; WF OOS measures per-strategy robustness. A strategy can pass WF OOS but be a losing component in a portfolio.

## Reproduce
```bash
DB_PASS_STOCKS=stocks1234560 python3 tools/build_walkforward_oos_results.py
# -> PASS=18 BORDERLINE=1 FAIL=34 INSUFFICIENT_FOLDS=6 -> tools/walkforward_oos_results.json
```

## Refs
- `ENHANCEMENT_OVERALL #85` (EAGLE-6 v2 PBO+WF OOS+bootstrap CI gate)
- PR #456 (EAGLE-6 v1 plan), PR #471 (PBO=1.0 FAIL), PR #473 (this)

## Action items
- [ ] Update `ENHANCEMENT_OVERALL #85` with WF OOS result: 18 PASS. Set `linked_pr` to include #473.
- [ ] Build `tools/build_bootstrap_ci_results.py` for the third EAGLE-6 v2 gate (bootstrap CI for PF — must not cross 1.0).
- [ ] Forward-test top 5 strategies: `crypto_liquidity_wick_reversal_v1`, `prediction_market_consensus`, `ensemble`, `drawdown_recovery_rsi_xrp`, `luxalgo_confluence` for 2 weeks.
