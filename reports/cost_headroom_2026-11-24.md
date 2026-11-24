# Per-class cost headroom (2026-11-24)

Provenance: `tools/class_cost_headroom.py` over [`docs/audit_review_2026-11-22/_raw/audit3_audit3_ledger.json`](docs/audit_review_2026-11-22/_raw/audit3_audit3_ledger.json), run 2026-11-24.

## Method

`headroom` is the distance from a class's 95% net-CI **lower bound** to zero. A class with a positive lower bound could absorb that much more cost and still have its edge statistically intact. A class whose lower bound is already at or below zero has no headroom: its measured edge is not distinguishable from break-even at the current cost.

Cost is the ledger's own `pf_cost_pct` — what was actually charged, not an assumption.

## Measured

```
CRYPTO      headroom=0.0      cost=0.0994 DIES
EQUITY      headroom=0.0      cost=0.0515 DIES
ETF         headroom=0.0      cost=0.0511 DIES
FOREX       headroom=0.0      cost=0.021  DIES
COMMODITY   headroom=0.0      cost=0.15   DIES
BOND        headroom=0.0      cost=0.0522 DIES
FUTURES     headroom=0.0      cost=0.15   DIES
```

## Reading it correctly

The important number is not the cost column but the headroom column: **it is 0.0 for all 7 classes.** That is not seven independent cost problems. It is one fact: no asset class in this ledger has a net-CI lower bound above zero. The cheapest class (FOREX, 2.1bp) fails for the same reason as the most expensive (COMMODITY and FUTURES, 15bp) — its confidence interval still reaches below break-even.

So cost is not what separates these classes today. None of them clears zero before cost is even considered. Lowering the spread on any class would not flip its verdict.

## Classes whose cost exceeds their headroom

All of them, trivially, since headroom is 0 and every cost is positive. Naming them individually would overstate the finding, so: `CRYPTO, EQUITY, ETF, FOREX, COMMODITY, BOND, FUTURES` all have `cost_exceeds_headroom: true`, and all for the single reason above.

## What would change this

A class needs a net-CI lower bound strictly above zero before cost sensitivity becomes a meaningful question. That requires enough forward rows to narrow the interval, not a cheaper broker. No backtest of the same rows can produce it.
