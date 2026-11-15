# PLAN — Multi-Asset (Core + Satellite)

**Status:** Allocation framework (the actual money vehicle). **Gap filled:** F8 (risk parity fails at real-capital scale), F28 (5-signal combo deflated).

## Hypothesis
A **core-satellite** portfolio — 70–80% low-cost broad index (beta capture, see `Plan/mf_etf/PLAN.md`) + 20–30% satellite of validated near-miss signals (vol-targeted, equal-risk-parity) — can produce a measurable, defensible expected return with controlled drawdown, even while active alpha remains unproven.

## Gap it fills
The repo has only ever attempted *alpha*. This is the first *allocation* plan, and it can pass a proof standard because its benchmark is explicit and its edge is cost + discipline, not prediction.

## Method
- **Core:** 60% global equity ETF, 30% aggregate bond ETF, 10% T-bills; quarterly rebalance; vol-target 12%
- **Satellite (only after a signal clears proof):** up to 20%, equal-risk-parity across validated near-misses
- **Regime overlay:** deterministic, lagged (e.g. 10-month SMA on equity → shift 10% to bonds when below)
- **Benchmark:** static 60/40 buy-and-hold index
- **Cost model:** ETF expense ratios + 0.05% rebalance cost + tax drag where relevant

## Proof tests
1. ✅ Temporal (2010-2018 / 2019-2026)
2. ✅ WFO on overlay parameters
3. ✅ Multiple testing (1 config)
4. ✅ Monte Carlo (bootstrap returns)
5. ✅ Friction (ER + rebalance + tax)
6. ✅ Significance (excess vs static 60/40)
7. ✅ Regime (bull/bear/sideways)
8. ✅ Shuffle control (overlay on shuffled data must not add value)
9. ✅ Forward (12-month paper)
10. ✅ Reproducibility

## Expected outcome
This is the **highest-probability product**. It will not "beat the market" by large margins, but it can deliver a defensible, measurable expected outcome — which is exactly what the audit dashboard currently lacks. Pair it with the published negative result so investors see the active sweep was rigorously killed, not quietly abandoned.
