# FOREX

**Scan footprint:** 498 flagged files (smallest researched class).

**Closed-ledger measurement:**

| n | mean | median | WR | PF |
|---:|---:|---:|---:|---:|
| 199 | −0.13% | 0.00% | 32.2% | **0.66** |

**Verdict: REJECT — stop allocating.** 199 trades at 32% WR and PF 0.66 is not a tuning problem.
A 32% win rate with a zero median says the exits are systematically wrong (winners cut, losers
held), which is a *different* defect from a missing edge — and it is visible without a benchmark.

**What has been tried:** FX carry build (`reports/strategy_build_fx_carry`), trend
(`fx_trend_backtest_2026-06-03`), ATR mutations, copy-trader FX, regime deep dives, CILB cost
sensitivity, per-symbol mutations.

**Note on the benchmark problem:** FOREX has no benchmark in
`audit_dashboard/data/benchmark_prices.json`, so all 199 rows are recorded as
`no_benchmark_for_class:FOREX` and cannot be excess-adjusted at all. Adding a benchmark (e.g.
DXY or a carry basket) is a prerequisite for ever evaluating this class again.

**What would reopen it:** nothing currently in the tree. Only a *new* mechanism (e.g. carry with
funding/interest differentials from FRED) with a pre-registered forward test would qualify —
not a mutation of the strategies that produced PF 0.66.
