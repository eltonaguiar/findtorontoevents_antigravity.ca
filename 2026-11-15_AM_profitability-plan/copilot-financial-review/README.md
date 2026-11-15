# Profitability research and parallel-agent package

**Date/time:** 2026-11-15 AM, UTC. **Owner/worktree:** copilot-financial-review.
**Status:** documented research proposals and prompts; no trading permission, production strategy change or guarantee.

## Read these first

1. [Per-class plans and holding styles](./01_PER_CLASS_PLAN_AND_STYLES.md)
2. [Parallel, cross-machine coding-agent prompts](./02_PARALLEL_AGENT_PROMPTS.md)
3. [Benchmark, risk and professional admission metrics](./03_BENCHMARKS_METRICS_AND_QA.md)
4. [Why copytrading failed; corrections and essential questions](./04_CLAIM_CORRECTIONS_AND_COPYTRADING.md)
5. [Famous strategies, contest evidence and institutional trust](./05_CONTESTS_AND_INSTITUTIONAL_TRUST.md)
6. [SubQ consultation and independent fact-check](./06_SUBQ_FACT_CHECK.md)
7. [Detailed reviewed framework](./PROFITABILITY_FRAMEWORK.md)
8. [Complete attempted-asset/source map](./ASSET_CLASS_COVERAGE.md)
9. [All 24 mapped historical money-maker documents](./HISTORICAL_MONEY_PLAN_REVIEW.md)
10. [Review of all ten published Grok documents](./07_GROK_PACKAGE_REVIEW.md)
11. [Frozen simulation plan](./08_SIMULATION_PLAN.md) and [actual executed backtests](./09_EXECUTED_SIMULATIONS.md)
12. [Easy forward tracking and fast elimination](./10_FORWARD_TRACKING_PROTOCOL.md)
13. [Independent review and corrected simulation costs](./11_INDEPENDENT_REVIEW_AND_CORRECTIONS.md)
14. [WIRED_IN per-class specifications, justification and elimination](../../WIRED_IN/2026-11-15_012638_UTC_copilot-financial-review-20261115/README.md)

## Central conclusion

There are three different objectives:

- **Make money:** positive after-cost return.
- **Beat alternatives:** beat the same-period S&P 500 total return, the appropriate buy-and-hold exposure and an investable cash benchmark.
- **Improve risk-adjusted performance:** beat an exposure/volatility-matched alternative, not merely achieve a smaller drawdown by holding less market risk.

Each is reported separately. A mutual fund that rises with the market is not automatically a winning prediction algorithm or an S&P 500 outperformer. Longer holding periods do not guarantee profit.

Prioritize **two research lanes**: transparent fund/ETF reference accounts and point-in-time diversified equity selection. The tested H-143 tactical challenger failed its alpha screen and is removed from that forward queue; a different tactical premise would need new preregistration and independent evidence. All other classes stay measurable and paper-only; promising crypto recency is a conditional investigation, not a deployment signal.

## Evidence and boundaries

- Frozen financial/source review: GitHub `1b3c7fe67a32f4d6f87e568641118f13fc61f0b5`.
- Current published snapshot at review: 2026-11-15 00:05 UTC, **zero money-ready classes**; recent and registry cohorts differ and are not blended.
- Reviewed all 1,695 lines of the strategy catalogue, four money-maker skills and all 24 mapped historical documents, with two focused reviewers.
- Completed **two successful SubQ Decisions API calls**, eight abstract methodology questions each. Only generic questions/public principles were included in the question payload; no repository code, portfolio data or credentials were included there or retained in the output. API authentication used an Authorization header.
- Recomputed seven passive risk curves from retained market histories; reproduced three TAA operational failures and earlier validator/portfolio counterexamples offline.
- Additional public research corroborated FINRA fund mechanics, official contest caveats, AQR trend research, CFA/GIPS and BlackRock's integrated risk/operations approach. Failed sources and unverified contest claims remain labeled.
- The executed H-142/H-143 backtests are documented below. No live paper trade, account access, DB mutation, workflow dispatch or production deployment is claimed.

The package is a research deliverable. Implementation agents must get their exact change scope approved, preserve shared peer work and pass the contracts in the prompts.

**Executed extension:** H-142/H-143 were preregistered on main before execution. Full-history FXAIX modeled net CAGR11.61%; fixed tactical CAGR9.34% versus same-window SPY18.09%. **Positive absolute return is not alpha**: tactical failed its screen and should not enter the alpha forward queue.13new tests passed and all28,120NAV rows reconciled. No real or forward paper position was opened.

Frozen evidence hashes are in [the manifest](./EVIDENCE_MANIFEST.json). The large registry is represented only by [its exact nine-class projection](./framework-pf_registry-excerpt.json), not another canonical registry.
