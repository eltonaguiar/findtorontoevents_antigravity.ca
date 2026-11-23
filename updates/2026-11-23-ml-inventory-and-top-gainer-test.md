# ML inventory + can we predict top gainers? (measured)

**Date:** 2026-11-23 · **Author:** Kilo · Paper only, zero capital.

## 1. What ML exists in the estate
LightGBM/sklearn models are present in: `mercury2/` (ensemble + top-gainer), `ml_gatekeeper/`,
`ml_consensus/`, `ml_crypto_predictor/`, `baby_strategies/ml_ensemble_strategy.py`,
`baby_strategies/logistic_microstructure.py`, `meta_strategy/ml_meta_learner.py`,
`signal_aggregator/ml_consensus.py`, `copy_trader_intel/ml_strategy_reverser.py`.
`lightgbm` is NOT installed in this worktree, so live training is unavailable here, but
**trained artefacts and out-of-sample reports exist**.

## 2. The existing top-gainer model already answers the question — and fails
`mercury2/top_gainer.py` is a LightGBM "daily top-gainer regressor" (12 causal features + funding_std,
trained on 815,633 rows / 50 symbols). Its own out-of-sample report (`mercury2/data/metrics_report.json`, 469 closed trades):

| metric | value |
|---|---|
| economic win rate | 40.09% |
| **hit_rate@top-3** | **0.0%** |
| **hit_rate@top-5** | **0.0%** |
| hit_rate@top-10 | 20.0% |
| Pearson IC (confidence vs pnl) | 0.039 |
| Spearman IC | 0.105 |

Quality flags emitted by the model's own harness: `low_linear_ic`, `weak_top5_hit_rate`.

**Metric defect flagged:** `training_summary.json` reports `dsr: 1.0, dsr_pass: true` while `psr_pass: false`,
and `validation_report.json` has `dsr_pvalue: 1.0`. A DSR passing at 1.0 with a p-value of 1.0 is internally
contradictory — that "PASSED" is degenerate and should not be trusted.

## 3. Independent cross-sectional retest (this session)
`tools/top_gainer_backtest.py` pools the two committed `crypto_daily_klines.csv` files
(8 symbols: AVAX, BNB, BTC, ETH, DOGE, LTC, SOL, XRP) over ~380 daily bars (~2025-02 to 2026-03).
For each day it ranks symbols by trailing momentum (7/30-day, and reversal) and checks whether the
predicted top-K are in the actual forward top-K over 1/7/30 days.

**Result (`reports/top_gainer_backtest.json`):** rank IC **0.00–0.07**, hit-rate@topK within **±0.03 of the
random baseline** across every lookback × horizon × K combination. Best edge +0.026 (~noise); most negative.

## 4. Conclusion
On both the in-house LightGBM model and an independent momentum retest, **the daily / weekly / monthly top
gainers are not predictable from price-based features.** This is the same verdict the deflation work reached:
a top-gainer strategy is a lottery ticket with 52 bp round-trip cost on alts. Do not fund it.

*Paper only. Zero capital. Not investment advice.*
