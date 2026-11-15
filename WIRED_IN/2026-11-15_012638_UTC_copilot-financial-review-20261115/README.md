# Algorithm specifications, selections and elimination record

**Request timestamp:** 2026-11-15 01:26:38 UTC.
**Worktree:** copilot-financial-review-20261115.
**Owner:** copilot-financial-review.
**Purpose:** consolidate the algorithms, evidence and decisions from our already-published research.

**Important:** `WIRED_IN` is the requested documentation directory name. This package does **not** claim production wiring, a deployed selector, live paper positions, proven prediction alpha or permission to deploy capital.

## Specifications and decisions

- [Algorithm specification per asset class](./ALGORITHM_SPECIFICATIONS.md): exact tested rules, a conditional equity research specification, and explicit abstention where no algorithm is justified.
- [Pick justification, backtests and elimination](./EVIDENCE_AND_ELIMINATION.md): positive and negative results, benchmarks, uncertainty and why rejected differs from deferred.
- [Parallel-agent handoff and requirements](./AGENT_HANDOFF.md): ready-to-paste prompts and the full earlier per-class prompt set.

The prior dated package remains at [2026-11-15_AM_profitability-plan/copilot-financial-review](../../2026-11-15_AM_profitability-plan/copilot-financial-review/README.md). No existing peer directory under `WIRED_IN` was overwritten or merged blindly.

## What is selected

1. **Passive mutual-fund / ETF reference lane:** FXAIX and SPY as separately funded, comparable paper benchmarks. This is low-turnover market exposure, not a winning predictor or a personal investment recommendation.
2. **Conditional equity alpha research lane:** point-in-time fundamental profitability. It is a specification only, unregistered/unexecuted here; no performance claim.
3. **Rejected alpha candidate:** H-143's fixed 10-month SPY/SGOV trend rule made money but substantially underperformed SPY and the exposure-risk diagnostic.
4. **Remaining classes:** measurement/contract-specific research and abstention. They were not all backtested or proved incapable of profit.

## Complete answers to the requested research topics

| Requested topic | Existing deliverable |
|---|---|
| Per-class profitability plan and holding styles | [Per-class plans/style matrix](../../2026-11-15_AM_profitability-plan/copilot-financial-review/01_PER_CLASS_PLAN_AND_STYLES.md) |
| Cross-worktree/machine coding prompts | [Complete prompts](../../2026-11-15_AM_profitability-plan/copilot-financial-review/02_PARALLEL_AGENT_PROMPTS.md), plus [specific handoff](./AGENT_HANDOFF.md) |
| SPY/buy-and-hold, risk and professional metrics | [Benchmark/metrics/QA contract](../../2026-11-15_AM_profitability-plan/copilot-financial-review/03_BENCHMARKS_METRICS_AND_QA.md) |
| Pasted claims, Kalshi/Polymarket and essential questions | [Corrections and lifecycle diagnosis](../../2026-11-15_AM_profitability-plan/copilot-financial-review/04_CLAIM_CORRECTIONS_AND_COPYTRADING.md) |
| Hoffman/contest systems and institutional trust | [Verified facts and limits](../../2026-11-15_AM_profitability-plan/copilot-financial-review/05_CONTESTS_AND_INSTITUTIONAL_TRUST.md) |
| SubQ consultation and independent fact-check | [Two successful calls and checks](../../2026-11-15_AM_profitability-plan/copilot-financial-review/06_SUBQ_FACT_CHECK.md) |
| Actual executed simulations | [Backtests/results](../../2026-11-15_AM_profitability-plan/copilot-financial-review/09_EXECUTED_SIMULATIONS.md) |
| Fast elimination versus longer-held trades | [Forward protocol/templates](../../2026-11-15_AM_profitability-plan/copilot-financial-review/10_FORWARD_TRACKING_PROTOCOL.md) |

No repeated SubQ calls or new backtests were needed to document the same decisions. The prior calls and simulations are preserved, not presented as new experiments at this timestamp.
