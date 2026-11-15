# FOREX — plan to profitability (kill-or-cure)

**State:** the weakest class — historical PF 0.27 (sub-floor), recent ~0.85, high n
(so the sample is honest and the edge is absent), mutation-before-kill protocol active.
Spread cost is real and was historically modeled as ~0. SubQ: P(2y) = 10-25% (1.13),
style = position (0.53), obstacle = **costs (0.57)** — agrees with our diagnosis.

## The bounded experiment (at most TWO mutations, then decide)
**Mutation 1 — session-filtered carry-aware trend:** London/NY-session entries only
(when realized vol and liquidity cover spreads), daily-horizon trend filter, carry proxy
as a feature. Cost model from REAL broker spreads (per-pair, per-session — not 0).
**Mutation 2 (only if 1 shows life) — mean-reversion at session extremes:** RSI(2)-class
on EURUSD/GBPUSD/USDJPY only during high-liquidity hours.

**Gates (all):** net PF ≥ 1.3, n ≥ 150, both-halves PF > 1.0, dual data source, and
**benchmark = cash + a spot-futures carry proxy** (a forex strategy must beat simply
holding carry — otherwise the "edge" is just levered beta on rates).

## The kill decision (pre-registered — a documented kill is a deliverable)
If both mutations fail their gates at n: **recommend formal class kill** — stop emitting
forex picks entirely, mark the class `KILLED — no edge at retail cost structure` on the
dashboard. Rationale (grounded):
- Retail forex costs (1-2 pip spread + commission) eat the only statistically reachable
  horizons; institutional FX edge lives in execution/microstructure we cannot replicate.
- Keeping a dead class alive costs measurement budget and pollutes the multiple-testing
  count (every kept strategy is a trial that didn't get killed).
- SubQ: costs as top obstacle, P(2y) 10-25% — the class is not worth the trial count
  *unless* mutation 1's session filter changes the cost arithmetic materially.

## Why allow any trial at all
Because "kill FOREX" must be earned by a clean test, not vibes — the same honesty standard
that reported COT failing 4/4. One bounded round, gates fixed in advance, kill or cure.
