# Forward-evidence readiness (2026-11-24)

Provenance: [`reports/forward_observations.jsonl`](reports/forward_observations.jsonl) (432 lines, dated Nov 22), measured 2026-11-24.

## Row counts vs the 100-row threshold

```
$ python3 tools/forward_evidence_gap.py
CRYPTO            430  READY
UNKNOWN             2  needs 98
```

Only CRYPTO clears the count threshold. Every other class has **zero** forward rows, so the per-class gap for EQUITY, ETF, FOREX, COMMODITY, BOND and FUTURES is the full 100.

## Row count is not evidence

Clearing 100 rows does not make a class INVESTABLE. The bar is a forward CI whose lower bound stays above zero after 2x cost. CRYPTO's 430 rows carry `entry_px`, `exit_px`, `side` and `slippage_bps` but no `pnl_pct`, so the net return was computed per row as `(exit/entry - 1) * 100` (sign-flipped for SHORT) minus `slippage_bps / 100`, then bootstrapped (4,000 resamples, seed 0):

**Correction (2026-11-24, later the same session):** the first run of this
section reported `mean net pct = -0.0252`. That was wrong: the per-row return
already had `slippage_bps` deducted, and the script then subtracted it a second
time. The figures below are recomputed with cost applied exactly once.

```
1x cost (measured)   n=430 mean=+0.1348 sd=3.1389 CI=(-0.1619,+0.4315)  rows for CI lo>0: 2083
2x cost              n=430 mean=-0.0252 sd=3.1389 CI=(-0.3219,+0.2715)  rows for CI lo>0: None
3x cost              n=430 mean=-0.1852 sd=3.1389 CI=(-0.4819,+0.1115)  rows for CI lo>0: None
```

Read this carefully:

- At the **measured** cost the forward mean is **positive** (+0.1348%) but the
  95% CI still straddles zero, so the edge is not yet distinguishable from none.
- At **2x** cost the mean goes **negative** (-0.0252%). The 1x result is
  therefore fragile: it survives only at today's measured spread.
- At **3x** cost it is clearly negative.

So CRYPTO fails the INVESTABLE bar on evidence quality today (CI contains zero),
and the sign of its forward edge depends on cost. Unlike the backtest, more rows
*could* help here, because the mean is positive at 1x: the CI half-width must
fall below 0.1348, which needs about **2,083 rows** at the same variance. At the
observed rate (430 rows accrued by 2026-11-22) that is roughly 24 days of the
same accrual.

## Bottom line

- Classes with >=100 forward rows: **1** (CRYPTO).
- Classes that pass the forward CI test (lower bound > 0 after 2x cost): **0**.
- Classes that can be INVESTABLE on 2026-11-24: **0**.

Since the backtest ladder caps out at CANDIDATE (see [`plans/2026-11-24-class-profitability-programme.md`](plans/2026-11-24-class-profitability-programme.md)) and no forward CI clears zero, the count of INVESTABLE classes is structurally 0 regardless of how many backtests are run. The remedy is more forward observations that narrow the interval above zero, not another backtest.

## Caveat

The 2 UNKNOWN rows are a different schema (`observation_month`, `signal`, `members`, `realised_return_pct`) — a monthly portfolio observation, not a trade. They are counted but not pooled into the per-trade CI.
