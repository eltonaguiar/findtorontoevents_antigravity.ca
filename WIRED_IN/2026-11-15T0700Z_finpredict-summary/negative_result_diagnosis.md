# Negative Result Diagnosis — Candidate Failure Classification

Decision: dead if fails shuffle/walk-forward/temporal. near-miss if passes those+friction but fails significance/MC on sample size. actionable if passes all 10. Near-misses re-tested with more data only; dead archived, no parameter re-runs.

## Failure-signature → pivot map
| Failed hurdle | Meaning | Pivot |
|---|---|---|
| Significance (CI incl zero) | noise | different signal family (carry/vol/cross-sectional), not param tweak |
| Friction | edge too small | lower turnover, maker orders, futures vs ETF |
| Walk-forward drift | overfit | simplify signal, cut params ≥50% |
| Shuffle | pipeline leak | fix bug (best failure) |
| Monte Carlo | few trades | extend history / lower frequency |
| Regime | conditional | pre-register regime trigger, stand aside otherwise |

## Near-miss handling
- Extend backtest window first (only if genuine count problem); then longer pre-registered paper test; never param-hunt. Worth paper-trading if passes temporal+shuffle+WFO+friction and only gap is N<60 trades.

## Passive allocation pivot (if no edge)
- Pivot dashboard to rule-based allocation (e.g. 60/30/10 or volatility-targeted) with explicit buy-and-hold multi-asset benchmark, quarterly rebalance, full proof standard applied. Publish active-sweep negative result separately for credibility.
