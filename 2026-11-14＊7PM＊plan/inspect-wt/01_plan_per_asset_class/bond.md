# BOND — plan to profitability

**State:** very sparse (n=18-35 vs floor 100); "accumulating"; historical PF ~1.72/WR ~56%
on tiny n (not evidence); strategy defined loosely (`bond_strategies.py` + FRED). SubQ:
P(2y) = 10-25% (0.93, near the bottom), style = longterm (0.77), obstacle =
**infrastructure (0.64)** — correct diagnosis: coverage, not signal.

## Phase 1 — define what a "bond pick" even is (2 weeks, no alpha claims)
The class cannot be tested until its unit of prediction is unambiguous. Options (pick one,
pre-register):
1. **Duration/curve stance:** monthly direction of 10Y yield (or 2s10s slope) from FRED +
   trend rules — rate-direction bets, binary-ish, low n accrual.
2. **ETF/fund rotation:** AGG/TLT/IEF/SHY/TIP relative strength (monthly, momentum) —
   becomes a *sleeve* alongside the MF/ETF allocation engine (recommended: reuses the
   engine, honest clock, benchmarkable vs AGG and vs cash).
3. **Credit spread timing:** HY vs IG relative value (needs spread data — check FRED
   BAMLH0A0HYM2 etc., free, point-in-time).
Recommended: **(2)** — it inherits the allocation engine and its infrastructure, and its
benchmark (AGG or 60/40) is transparent.

## Phase 2 — accumulate n under QA gates
- Extend `bond_strategies.py` + FRED feeds (BAML series are free and point-in-time — the
  data problem is genuinely solvable, unlike FOREX's cost problem).
- Emit paper decisions monthly; n accrues 12/yr → **need ~3-5 years for trade-level n≥100**
  OR switch to decision-level evaluation (12/yr × multiple series) with bootstrap —
  pre-register which gate applies (this is a real constraint; state it honestly).

## Phase 3 — gates (benchmark-relative)
- Beat **AGG buy-and-hold AND cash (T-bill)** net — bonds' bar is lower than equities'
  because the alternative for this capital is exactly AGG/cash, not SPY.
- MDD ≤ 6% at sleeve level; excess return vs AGG > 0 with t-stat ≥ 1.6 over the window.
- SubQ: obstacle=infrastructure conf 0.53 — after Phase 1-2, the obstacle disappears and
  the signal question can finally be answered.

## Honest near-term answer
Until Phase 2 completes: **hold low-cost intermediate bonds as ballast** — the "bond
allocation" is already profitable as carry (yield > 0) without any prediction. The
prediction system's bond job is to beat *that*, which is a real but modest bar.
