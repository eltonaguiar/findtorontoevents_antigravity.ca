# EQUITY — plan to profitability

**State (post-#773):** slot 1 **CLOSED as a source of edge** — `NO_ALPHA_BETA`
(t=1.05, median pick −0.57% vs SPY, 54% underperform). The class still has the only
positive *cost margin* measured (3.23× round-trip cost, mean +0.323%, n=738) — so it is
the right place for ONE new trial, not a reopen of the old one. SubQ: P(2y) = 10-25%,
style = swing (longterm 0.47 / position 0.43 close), obstacle = competition (0.68).

## The trial (pre-register with a trial ID; count it in the multiple-testing budget)
- **Hypothesis:** RSI(2)-style short mean reversion on S&P-500 constituents, held 1-5 days,
  entered at the close on the signal candle (never the next open — entry-basis discipline),
  0.10% round-trip cost, no look-ahead: point-in-time constituent list.
- **Why this family:** short-horizon reversal is one of the few retail-reachable effects
  with academic replication (SubQ evidence 3.45/5 "replicated academically") and it trades
  on the *cost margin* the class already showed.
- **Gate (all must pass, forward paper ≥24 months):**
  1. net PF ≥ 1.15 and expectancy > 0 after costs at stated size;
  2. **excess Sharpe vs SPY ≥ 0.2** OR equal return with ≥30% lower maxDD (the #773 test
     that failed must be re-run as a *gate*, not as an afterthought);
  3. both halves of the window PF > 1.0; ≥66% walk-forward windows positive;
  4. n ≥ 500 trades, Wilson CI on WR above 50%;
  5. capacity: impact ≤ 0.10% at $100k.
- **Kill:** fail gate 2 at n=500 → class returns to "measurement baseline only"; no re-run
  with different thresholds (that's the B8 multiple-testing trap).

## What NOT to do
- Do not re-test "does any of our equity strategies beat SPY" with new filters each month.
- Do not use today's index constituents on history (survivorship = fake alpha, guaranteed).
- Do not claim the historical PF ~1.41/WR 53% snapshots — those were measured before fill
  and cost modeling.

## Interim honest use
Equity rows remain the **measurement baseline** for QA Gate 1/3 (most liquid data, easiest
reconciliation) — that is real value even with zero alpha.
