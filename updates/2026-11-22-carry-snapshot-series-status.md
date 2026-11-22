# Carry execution cost series — 2 of 20 snapshots (2026-11-22)

Todo **23** status: **PARTIALLY ADVANCED, TIME-GATED. Not fabricated to close.**

---

## Current state

| # | utc | median RT | worst RT | slippage | basis (BTC/ETH/BNB/SOL/XRP) |
|---|---|---:|---:|---:|---|
| 1 | 2026-11-22T11:20:57 | 42.69 bp | 43.55 bp | 2.69 bp | −5.24 / −5.03 / 0.00 / −5.65 / −4.29 |
| 2 | 2026-11-22T22:06:02 | 42.84 bp | 43.97 bp | 2.84 bp | −5.44 / −6.41 / −0.36 / −5.68 / −5.41 |

**n = 2.** Median of medians 42.76 bp, range 42.69–42.84 bp, **spread between
snapshots 0.15 bp**.

The two snapshots were taken 10h45m apart and agree to 0.15 bp. That is
reassuring for *stability over ten hours* and tells us almost nothing about
*dispersion across market conditions* — which is what 20 snapshots was meant to
establish.

## Why I stopped at 2

The target was 20 snapshots. Two hard constraints:

1. **The recorder enforces a 30-minute minimum gap** between samples. So the 20
   snapshots *could* be produced inside a single 10-hour session.
2. **But that would answer the wrong question.** Twenty samples taken within one
   day measure intraday order-book stability. The purpose of 20 snapshots is to
   capture the spread **across conditions**, because the caveat on every carry
   number in this programme is "spreads widen in stress, and stress is when you
   enter". Sampling one quiet Saturday twenty times does not test that.

So the honest position: the series accrues via the
`.github/workflows/carry-cost-series.yml` cron at **4 samples/day** (`23 */6 * * *`),
reaching 20 in roughly **5 days**. Producing 18 synthetic clicks of the recorder
tonight would inflate n without adding information, and would let the next agent
believe the dispersion question had been answered when it had not.

## What the 42.7 bp actually implies (unchanged by n=2)

| | |
|---|---|
| observed round trip | **42.76 bp** median (n=2) |
| 90-day cliff | 45 bp ⇒ **0.50 bp/day** |
| 42.76 bp over 90 days | **0.475 bp/day** — clears the cliff, by 5% |
| a 2× worse fill (85.5 bp) | **0.950 bp/day** — **FAILS**, and fails every shorter hold too |

The margin is 5%. A stress-window spread 2× wider kills the trade outright. This
is why the series exists and why 2 points is not enough: the parameter that
decides the verdict is the *tail* of the spread distribution, and n=2 has no tail.

## Next action

Nothing to code. The cron does it. Re-read this file when
`reports/carry_execution/round_trip_series.jsonl` reaches ≥20 rows and then:

```
python3 tools/carry_execution_cost.py --series
```

which reports the distribution rather than a point estimate. **Until then, every
carry number in this programme is quoted against a floor, not a mean** — as the
tool itself has warned on every run since it was written.
