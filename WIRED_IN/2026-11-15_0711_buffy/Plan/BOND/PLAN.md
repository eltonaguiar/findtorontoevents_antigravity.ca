# PLAN — BOND (fresh start: duration timing vs IEF)

**Status:** plan only, and deliberately the slowest of the three. There is no bond track record
to build on (n=28), so this plan starts from a hypothesis and a forward test, not a backtest.

## Hypothesis

> When the 10-year yield's 3-month change is falling, holding long duration (TLT) beats holding
> intermediate duration (IEF) over the following month; when it is rising, the reverse.

This is a carry/duration-timing hypothesis, not a signal-mined one. It must be pre-registered in
`reports/hypothesis_registry.json` before the first month of recording.

## Gap it fills

- Inventory row: `ML:timeseries` (782 files) includes `arch` but no bond-specific timing model;
  `reports/h008_bond_2s10s_redesign` and `bond_duration_timing_backtest` are designs, not
  measurements on a fixed universe.
- BOND has **no benchmark** in `benchmark_prices.json`, so no bond row can currently be
  excess-scored at all. Fixing that is step 1.

## Method

1. Add IEF (and TLT, SHY) daily closes to the benchmark file via
   `tools/build_benchmark_prices.py` (the `BENCH` map needs an ETF entry — equity/ETF map to SPY
   today, so a bond-specific symbol requires a small, explicit change).
2. Record monthly decisions: long TLT vs long IEF, decided from FRED yield data available at the
   decision date only.
3. Pre-register: 24 monthly observations, one look at n=12 and one at n=24 (O'Brien-Fleming
   boundaries from `tools/forward_tracker.py`), kill rule at n=12 if mean excess < 0.
4. Measure excess of the chosen leg vs the other leg, plus vs a 50/50 blend.

## Data

FRED (`fredapi` is installed): DGS10, DGS2, DGS3MO. Prices: TLT/IEF/SHY daily closes.

## Universe / timeframe / parameters

Universe: TLT, IEF, SHY. Timeframe: monthly decision, monthly rebalance. Parameters: one
(3-month yield change threshold = 0), stated in advance; no sweep.

## Cost model

ETF expense ratios (TLT 0.15%, IEF 0.15%) + 2 bps/side commission proxy + spread. No leverage.

## Benchmark

IEF (intermediate duration) — the honest comparison for a duration-timing claim is the
lower-risk alternative, not SPY.

## Proof items this is designed to pass

G9 (pre-registered forward test with fixed sample and kill rule) is the primary item; G1 and G6
apply from the first observation. G3 is trivial here (one configuration), which is why this class
is attractive: **low multiplicity**.

## Honest expectation

24 monthly observations take two years. This is the only class in the repo where the correct plan
is slow — and the reason bonds should be attempted is precisely that nobody here has tried them
with patience.
