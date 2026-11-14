# ML Validation — Audit, Common Errors, and Rigorous Proof-of-Strategy (2026-11-14)

Auditor subtree: `finpredict-v3` · Archive stamp: `2026-11-14T174500Z`
Sub-agents executed: ML code review · prediction-quality QA per asset class · backtest/feed integrity. Then a custom horizon-validation harness was built and run.

---

## Part 1 — Is there any SOLID proven methodology? Per asset class.

Answer: **NO.** On honest (intrabar, execution-adjusted) numbers, no asset class or ML model shows a time-stable, statistically significant edge. Summary of the evidence:

| Class | closed n | honest intrabar WR | honest PF | 95% CI excludes 50%? | Verdict |
|---|---|---|---|---|---|
| CRYPTO | 4,907 | 35.9% | 0.92 | yes (below) | anti-skill |
| EQUITY | 8 (headline) / 250 (intrabar) | 59.2% | 0.94 | above but loses money | WR>50%, unprofitable |
| FOREX | 82 | 32.2% | 0.66 | yes (below) | anti-skill |
| COMMODITY | 0 | 40.2% | 1.03 | below | inconclusive (PF≈1) |
| ETF | 8 | 2.2% | 0.02 | — | insufficient |
| FUTURES | 0 | 42.3% | 1.09 | below | insufficient (n=52) |
| BOND | 3 | 0% | 0.0 | — | insufficient |
| MUTUAL FUNDS | — | — | — | — | unbuilt (no ranker/site) |

**Only 4 strategies even qualify as "candidates" for skill** (fwd_n ≥ 30, fwd_wr ≥ 55) — and all are **rule/TA-based forward feeds** (`multi_period_rsi_confluence_eth` 61% /118, `atr_percentile_gate` 57.4% /94, `crypto_liquidity_wick_reversal_v1` 60.9% /46, `drawdown_recovery_rsi_eth` 73.9% /46). None has a backtest baseline (fwd-only), so decay is undefined and they are unproven.

**Fundamental/earnings stock picking:** modules exist (`goldmine_stocks`, `growth_stock_screener`, `ueps`, `stocks_competition`, `stocksunify2`) but have zero/failed realized evidence. `goldmine_stocks`: n=270 closed, WR 50%, **PF 0.42, PnL −4.6**. `stocks_competition`: PF 1.33 on n=217 but is momentum/Bollinger, not fundamental. No earnings/PEAD/Piotroski signal is actually wired to a profitable result. **No fundamental methodology is proven.**

## Part 2 — Common ML errors found (file:line evidence)

| Error | Where | Severity |
|---|---|---|
| **Target leakage** in PRODUCTION gatekeeper model | `ml_gatekeeper/gatekeeper.py:170-186` includes `forward_wr`/`strat_fwd_wr`/`age_hours` as features; masking off by default. `ab_router.py:28-38` confirms leak; old (leaky) sleeve is the live `active_picks.json` emitter (gatekeeper.py:1002). | CRITICAL |
| **Look-ahead features** | `claude_gainer_ml/train_model.py:685-711` uses full-series tail `ohlcv_1h[-24:]` and current-snapshot metadata on historical rows. | CRITICAL |
| **Random shuffle split on time series** | `scripts/sports_ml.py:47` `train_test_split` without `shuffle=False`; plus `win_prob`/`ev_pct` features are outcome-target. | HIGH |
| **Train/test distribution shift + zero precision** | `claude_gainer_ml/models/training_meta.json`: positive rate train 13% vs test 1.5%; test precision/recall/F1 = 0.0 at threshold 0.75 (AUC 0.69 flatters). | HIGH |
| **Overfit magnitude** | `crypto_ml_edge/models/*edge_meta.json` net Sharpe ~16 / DSR 1.0 — implausible, even with good purged CV. | HIGH |
| **Stale / dead models** | `crypto_ml_edge` + `ml_crypto_predictor` models trained 2026-02 (~9 mo); Claude Gainer ML card 2026-05-25 (~173d); `ml_crypto_predictor` disabled ("36.8% WR, −32% PnL"). | HIGH |
| **Fake/placeholder ML** | `ml_gatekeeper/ab_router.py:143-158` returns constant placeholder `(0.5,0.5)` on empty features (A/B measures nothing). `scripts/ensemble_stacker.py` trains on synthetic random data. `ml_consensus/consensus.py` is a hand-weighted vote, no fit. | MED |
| **No OOS / threshold overfit** | gatekeeper prod model trained on all data after CV; per-class threshold overfit to OOF (per_class_trainer.py:227-236). | MED |

## Part 3 — Backtest ↔ forward disconnect (structural)

- `backtest_vs_forward` (255 rows): **0 rows have both bt_trades>0 and fwd_trades>0.** 100% of backtested strategies (bt>0) have zero forward trades; 100% of forward-traded strategies have zero backtest trades.
- 13 strategies have bt_wr ≥ 60 yet fwd_trades=0 (e.g. `connors_rsi2` bt 68.8%/906).
- So no strategy has ever been BOTH back-tested AND forward-validated: the two records don't connect. This is the core reason "solid" cannot be claimed.

## Part 4 — How I would prove a strategy is solid (methodology)

The harness I built (`tools/pi_horizon_validation.py`) implements the disciplined answer to "how to prove it over different points in time":

1. **Use realized trades only** (not backtest fills), drop phantoms (pnl=0 → exit==entry / UNKNOWN).
2. **Chronological walk-forward windows** (60-day) — each window is an independent out-of-sample period.
3. **Statistical gate:** binomial 95% CI lower bound of WR must *exclude* 50% on the profitable side (true skill vs coin flip).
4. **Economic gate:** PF > 1.05 and positive mean per-trade PnL.
5. **Stability gate:** strategy must show win-majority in ≥66% of windows (edge must persist across time, not one lucky window).
6. **Multiple-testing honesty:** report # groups tested vs # passed, so the look-elsewhere effect is visible.
7. **Survivorship caveat:** this uses the recorded closed ledger which the audit showed excludes ~51% of trades → any pass here is an UPPER bound, not proof.

## Part 5 — Horizon harness results (on recorded realized trades)

- n≥60: **6 groups tested, 0 passed all gates.**
- n≥30: **26 groups tested, 0 passed all gates.**

Best performers (still FAIL the rigor gate):
- `ETF rs-breakout-scout` n=78 WR 57.7% CI_lo 46.6% (<50%) PF 1.75 → fails CI (and only 3/5 windows).
- `EQUITY vol-contraction-scout` n=62 WR 46.8% PF 1.34 → CI_lo 34.9%.
- `CRYPTO luxalgo_confluence` n=1,290 WR 42.9% CI_lo 40.3% → reliably BELOW 50% (anti-skill), the largest-crypt strategy.
- Several TA scouts have PF 1.5-2.0 but all fail the CI gate (small n → wide CI).

**Conclusion: the harness proves NO strategy in the recorded ledger is solidly profitable across time. The honest answer is the negative result — which is the correct, non-fabricated output of a rigorous process.**

---

## Deliverables in this archive

```
ML_VALIDATION/
  tools/pi_horizon_validation.py   # the reusable proof harness (run: python tools/pi_horizon_validation.py --json <dashboard_data.json> --all)
  results/horizon_validation_n60.txt  # n>=60 run
  results/horizon_validation_n30.txt  # n>=30 run
  README.md (this file)
```

All numbers above are from the live payload `/tmp/kilo/dashboard_data_latest.json` (generated 2026-11-14T14:30Z) and repo model artifacts, read-only.
