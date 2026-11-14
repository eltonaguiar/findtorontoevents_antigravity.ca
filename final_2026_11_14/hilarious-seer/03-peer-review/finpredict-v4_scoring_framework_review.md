# Peer Review: finpredict-v4 — PROFITABLE_SCORING_FRAMEWORK + statistical_scoring_framework.py

**Date:** 2026-11-14
**Reviewer:** hilarious-seer
**Source:** `finpredict-v4/research/PROFITABLE_SCORING_FRAMEWORK.md`, `finpredict-v4/alpha_engine/statistical_scoring_framework.py`

---

## Summary

finpredict-v4 produced a comprehensive 6-gate scoring framework and a full Python implementation (`StrategyCertifier`). The framework addresses the core problem identified across all audits: **no single combined gate exists that requires z>1.96 AND PF>1.5 net-of-cost simultaneously**. This work directly closes that gap.

---

## Strengths

1. **Complete 6-gate pipeline from discovery to money-ready certification.**
   - Gate 0: Data Quality (n≥30, no NaN, no zero variance)
   - Gate 1: Statistical Significance (bootstrap CI, p-value < α_corrected)
   - Gate 2: Walk-Forward Robustness (≥60% profitable folds, mean OOS PF > 1.2)
   - Gate 3: Gross Profitability (PF>1.5, Sharpe>1.0, WR>50%, Sortino>1.5)
   - Gate 4: Money-Ready Net (PF>1.2, Sharpe>0.5, WR>45%, Sortino>0.8, DSR>0.95)
   - Gate 5: Direction Validation (both sides pass, or single-direction certified)

2. **Rigorous cost model.**
   - Commission 10 bps, spread 5 bps, base slippage 5 bps + volatility penalty
   - Intrabar replay adjustment: +10 bps penalty on winning trades (accounts for 23-24% win-to-SL flip)
   - Net metrics recalculated from net returns

3. **Multiple-testing correction wired in.**
   - Bonferroni for final certification (α/m)
   - BH-FDR for discovery screening (α=0.10)
   - Batch-level FDR applied in `certify_all()`

4. **Direction bias scoring.**
   - Separate LONG/SHORT metrics with bias flags (BALANCED, DIRECTIONAL, INSUFFICIENT_DATA)
   - Per-direction certification possible

5. **Deflated Sharpe Ratio (DSR) implemented.**
   - Lopez de Prado (2018) approximation with Sidak correction for multiple trials
   - Threshold >0.95 for money-ready

6. **Bootstrap confidence intervals on PF and Sharpe.**
   - 10,000 resamples with replacement
   - Percentile-based 95% CI

---

## Weaknesses / Gaps

1. **DSR implementation is an approximation, not full numerical integration.** The comment at L177-178 admits this: "This is a practical implementation; for production, use full numerical integration." The approximation may understate or overstate true DSR for highly skewed return distributions.

2. **Walk-forward folds are non-overlapping and fixed-size.** The simple contiguous fold approach (L292-320) does not implement purged cross-validation or embargo periods, which Lopez de Prado recommends for financial time series. Adjacent folds share data, creating information leakage.

3. **Daily returns approximation is crude.** `certify()` builds daily returns by grouping trades by date and summing (L652-653). If multiple trades occur on the same day, this inflates variance and distorts Sharpe/Sortino. A proper approach would use actual daily portfolio returns.

4. **No random-entry Monte-Carlo timing test.** The framework has bootstrap CI and WFA but lacks the same-asset, direction-aware, window-matched random-entry null that `benchmark_closed_ledger.py` implements. This is the single most powerful test for proving timing edge.

5. **No paired-bootstrap vs benchmark.** `benchmark_closed_ledger.py` compares each trade to a same-window benchmark (SPY for equity, BTC-USD for crypto). The scoring framework does not compare against buy-and-hold, so a strategy that simply rides a bull market could pass all gates.

6. **Calmar ratio requires 1 year of history.** The framework computes Calmar regardless (L152-166), but the threshold comment says "requires at least 1 year of history." For strategies with <1 year, Calmar should be flagged as unreliable, not computed.

7. **No regime robustness test.** The framework mentions "regime coverage: 2022 bear market must appear in at least one test fold" in the research doc, but `statistical_scoring_framework.py` does not implement regime-aware folds or regime-stratified metrics.

---

## Recommendations

1. **Upgrade DSR to full numerical integration.** Use `scipy.integrate.quad` or `mpmath` for the exact Lopez de Prado formula. The approximation is acceptable for discovery but insufficient for money-ready certification.

2. **Add purged k-fold cross-validation.** Replace the simple contiguous fold approach with purged CV (train/test gaps = maximum autocorrelation lag) and embargo (no test data within N bars of train data). This is in `alpha_engine/admissibility_pipeline.py` already — extract and reuse.

3. **Add random-entry MC timing test.** Port `benchmark_closed_ledger.py::random_entry_mc` into `StrategyCertifier` as Gate 2b or integrate into Gate 1. Require MC percentile ≥0.90 for money-ready.

4. **Add paired-bootstrap vs benchmark.** Port `benchmark_closed_ledger.py::paired_bootstrap` into the framework. Require `pass_95` (frac_positive ≥0.95) for money-ready.

5. **Add regime stratification.** Split WFA folds by regime (bull/bear/chop) and require at least one profitable fold in each regime. Use `alpha_engine/regime_flip_detector.py` or `system_trend_detector.py` for regime labels.

6. **Fix daily returns grouping.** Use actual daily portfolio equity curve (cumulative PnL per day) rather than summing same-day trades. This requires linking trades to portfolio snapshots from `audit_sync.py`.

---

## Verdict

**ACCEPT with high priority upgrades.** The framework is the most complete edge-proof pipeline in the repo and should become the canonical certifier. The missing pieces (purged CV, MC timing, benchmark comparison, regime stratification) are all available in other repo modules and should be integrated before declaring any strategy "money-ready."
