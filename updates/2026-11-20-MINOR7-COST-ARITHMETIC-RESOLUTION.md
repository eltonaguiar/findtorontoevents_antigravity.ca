# RESOLUTION — MINOR 7 cost arithmetic (copilot-cli-deepseek-flash, 2026-11-20)

Appended in reply to the MINOR 7 finding above. The inconsistency is **mine** and
is corrected here. No figure in this section is quoted from memory: each was
recomputed from `tools/residual_mean_reversion.py` at the time of writing.

## The correct base case

The module default is `COST_BPS = 5.0`, and `round_trip_cost_pct` charges **both
legs, in and out**:

```python
def round_trip_cost_pct(legs=2, bps_per_leg=COST_BPS):
    return legs * 2 * bps_per_leg / 100.0
```

Therefore:

| call | result | meaning |
|---|---|---|
| `round_trip_cost_pct(2, 5.0)` | **0.20%** | module default, 2-leg trade |
| `round_trip_cost_pct(2, 10.0)` | **0.40%** | the 10 bps stress case |
| `round_trip_cost_pct(1, 5.0)` | 0.10% | single-leg reference |

**The run I reported used 0.20% round-trip, not 0.4%.** The "0.4% round trip"
prose in the original update was carried over from the 10 bps sensitivity pass
and was never the base case. That is the defect MINOR 7 identifies, and it is
real.

## Does the verdict change? No — and the corrected figure is worse, not better

All four combinations were measured rather than argued:

| hedge | gross | @ 0.20% cost → net | @ 0.40% cost → net |
|---|---|---|---|
| unhedged | +0.1997% | **−0.0003%** | **−0.2003%** |
| hedged | +0.0716% | **−0.1284%** | **−0.3284%** |

Every cell is negative. The gate's sign does not flip with the cost assumption;
what the 10 bps case changes is the **magnitude** — at 0.40% the strategy loses
more than its entire gross edge rather than approximately breaking even. That is
a strictly worse finding, not a different one.

## Standing correction to the record

The hypothesis `H-2026-11-20-01` result block should be cited as:

- cost assumption: **0.20% round-trip** (5 bps/leg, 2 legs, in and out)
- net expectancy: **negative**, and negative at every tested cost level up to
  0.40%
- verdict: **NOT_PROVED**

The registry's own `config: "5 bps/leg"` field is therefore consistent with a
0.20% cost, not a 0.40% one. Where the two appear to conflict, 5 bps/leg (0.20%)
is authoritative.

## Related defect found while fixing this

While making the cost fields auditable, a second and more serious defect was
found in `paired_gate_compare`: the "paired" bootstrap zipped the gated and
ungated arms **by list position**. Because the gate removes trades, the gated arm
is a strict subset, so `base[i]` and `gated[i]` were different trades whenever an
earlier signal was dropped — the comparison was unpaired, which the function's own
docstring forbade.

Fixed by pairing on `entry_idx` (now persisted per trade, along with
`expected_pct`, `expected_minus_cost_pct`, `sigma_eq`, and `exit_idx`). A gated-out
signal contributes `0.0` to the gated arm — capital not deployed is neither a win
nor a loss. The property is locked by
`test_paired_delta_pairs_on_entry_idx_not_position`, which constructs a case where
positional pairing reports a **positive** delta and entry-bar pairing reports a
**non-positive** one, and asserts the two disagree. A test that both designs pass
would not have caught this.
