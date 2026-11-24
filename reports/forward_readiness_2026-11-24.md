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

```
rows measured    : 430
mean net pct     : -0.0252
CI net           : (-0.3099, 0.2687)
mean net 2x cost : -0.1852
CI net 2x cost   : (-0.4699, 0.1087)
positive mean?   : False | CI lo > 0? False
```

CRYPTO's forward mean is **negative**, and its 95% CI straddles zero both at 1x and at 2x cost. It therefore fails the INVESTABLE bar on evidence quality, not on sample size.

## Bottom line

- Classes with >=100 forward rows: **1** (CRYPTO).
- Classes that pass the forward CI test (lower bound > 0 after 2x cost): **0**.
- Classes that can be INVESTABLE on 2026-11-24: **0**.

Since the backtest ladder caps out at CANDIDATE (see [`plans/2026-11-24-class-profitability-programme.md`](plans/2026-11-24-class-profitability-programme.md)) and no forward CI clears zero, the count of INVESTABLE classes is structurally 0 regardless of how many backtests are run. The remedy is more forward observations that narrow the interval above zero, not another backtest.

## Caveat

The 2 UNKNOWN rows are a different schema (`observation_month`, `signal`, `members`, `realised_return_pct`) — a monthly portfolio observation, not a trade. They are counted but not pooled into the per-trade CI.
